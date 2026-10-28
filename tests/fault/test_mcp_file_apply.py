"""Kill `orqlet upgrade` after each write when a declaration is present, on real files (task
mcp-or-plugins, phase P-5; ORQLET-TEST-002, plan AC-8).

An upgrade with a declaration is one journalled plan: the files of a new release (when there is
one), the `.mcp.json` of the declaration (created, or, when the team's own file differs, the
proposal for it), and the lock last (ADR-003 decision 5, ORQLET-SAFE-001). The tests stop the write
after each of its steps, on the real file system under `tmp_path`, as `test_upgrade_resume.py` does
for a new release:

- after k writes every file is whole, no temporary file is left, the lock is still the old one and
  `.mcp.json` is the render or is not there; the team's own file is never touched;
- the interrupted case of ADR-003 decision 5, `.mcp.json` written and the lock not yet, classifies
  the file as up to date: a check plans no write for the file and no proposal, and it is still
  planned as a new file for a kill before its write;
- `upgrade --resume`, which `doctor` names for an interrupted change (ORQ-E170), finishes the
  change and gives the files of an uninterrupted run, and a further run and a check find nothing;
- `rollback` of the interrupted change gives the files as they were before, and the upgrade then
  runs again and gives the files of an uninterrupted run;
- for a team file that differs and holds a run-time sentinel, the sentinel is in no other file of
  the project and no file of the data directory (the journal, the backups) at any of these states.

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-00N-*.md`
under docs/design/mcp-or-plugins/design/, and AC-n are the criteria of phase P-5 in
docs/design/mcp-or-plugins/plan.yaml. The declaration is the text of the valid fixture with its one
server changed to the one pair that the closed table enables (id `atlassian`, address
https://mcp.atlassian.com/v2/mcp, client `claude-code`). Credential-shaped text is assembled from
parts at run time and never written as one literal (ORQLET-SEC-003).

These tests were written first, by the Tester of phase P-5, before the implementation existed.

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- what a plain `upgrade` (without `--resume`) does after a kill: it is refused with ORQ-E131 today
  and the design does not say otherwise, so "a re-run" is `--resume` (the tests do not pin the
  refusal);
- the order of the writes other than the two that the design fixes (the lock last; the files of a
  release and the file of the declaration in the order of the paths);
- what `doctor` says about a team file that lacks the declared entry after a proposal: it is an
  error of `validate integrations` (ADR-002 decision 6), so `doctor` is checked for new files only.
"""

from __future__ import annotations

import copy
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from orqlet.application.ports.filesystem import FileSystem
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.diagnose import doctor
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.rollback import RollbackOptions, rollback
from orqlet.application.usecases.upgrade import UpgradeOptions, UpgradeResult, upgrade
from orqlet.domain.changeplan import Action
from orqlet.domain.classify import FileState
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import SequentialIds
from tests.fakes.workflow import PINNED, ChangedWorkflow
from tests.support.git import make_repo
from tests.support.real_env import real_services, snapshot
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.fault,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"  # the one address of the closed table
EDITABLE = "client-enforced-editable"
DECLARATION = ".orqlet/integrations.yaml"
MCP = ".mcp.json"
LOCK = ".orqlet/generated.lock.yaml"
PROPOSAL = ".orqlet/proposals/.mcp.json.diff"
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
NEXT = ChangedWorkflow(PINNED, version="0.2.0")
# The text of AC-1 of the renderer for the one server `atlassian`, written out by hand.
ATLASSIAN_TEXT = (
    "{\n"
    '  "mcpServers": {\n'
    '    "orqlet-atlassian": {\n'
    '      "type": "http",\n'
    '      "url": "https://mcp.atlassian.com/v2/mcp"\n'
    "    }\n"
    "  }\n"
    "}\n"
)

# --- values assembled at run time (ORQLET-SEC-003) ------------------------------------------------

SENTINEL = "".join(("team-", "only-", "text-", "2b7f", "c0d8"))


def declaration() -> bytes:
    """A valid declaration with one server `atlassian` for Claude Code, as JSON text."""
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    base = copy.deepcopy(data["servers"][0])
    base.update(
        id="atlassian",
        identity={"kind": "remote", "url": ATLASSIAN},
        registration={"name": "orqlet-atlassian", "mode": "read-only", "enforced_by": EDITABLE},
        per_client={"claude-code": {"register": True, "enforced_by": EDITABLE}},
        clients=["claude-code"],
    )
    data["servers"] = [base]
    data["roles"] = {"architecture-reviewer": {"servers": ["atlassian"]}}
    return json.dumps(data, indent=2).encode()


def team_file() -> bytes:
    """The team's own file: one server of its own, whose name and address hold the sentinel."""
    document = {
        "mcpServers": {
            f"team-{SENTINEL}": {"type": "http", "url": f"https://example.com/{SENTINEL}"}
        }
    }
    return (json.dumps(document, indent=2) + "\n").encode()


# --- the scenarios --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    label: str
    workflow: WorkflowSource  # the release that the upgrade installs
    team: bytes | None  # the team's own `.mcp.json` before the upgrade, if any

    @property
    def creates_the_file(self) -> bool:
        return self.team is None


SCENARIOS = (
    Scenario("new-file", PINNED, None),
    Scenario("new-file-and-new-release", NEXT, None),
    Scenario("differing-file-and-new-release", NEXT, team_file()),
)


@pytest.fixture(params=SCENARIOS, ids=[scenario.label for scenario in SCENARIOS])
def scenario(request: pytest.FixtureRequest) -> Scenario:
    found: Scenario = request.param
    return found


def clone(template: Path, destination: Path) -> tuple[Path, Path]:
    """A copy of a template's project and of its user data (journals and backups)."""
    root, data = destination / "project", destination / "data"
    shutil.copytree(template / "project", root)
    shutil.copytree(template / "data", data)
    return root, data


@pytest.fixture(scope="module")
def templates(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """One project for each scenario, after `init` with the pinned release and with the declaration
    and the team's file in place, as real folders that the tests copy."""
    found: dict[str, Path] = {}
    for item in SCENARIOS:
        parent = tmp_path_factory.mktemp(f"template-{item.label}")
        root = parent / "project"
        shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
        make_repo(root)
        result = init_project(real_services(root, parent / "data"), InitOptions(assume_yes=True))
        assert result.status == "applied", result.findings
        (root / DECLARATION).write_bytes(declaration())
        if item.team is not None:
            (root / MCP).write_bytes(item.team)
        found[item.label] = parent
    return found


def crash_after(writes: int) -> Callable[[FileSystem], FileSystem]:
    def wrap(fs: FileSystem) -> FileSystem:
        return FaultyFileSystem(fs, crash_after_writes=writes)

    return wrap


def run_upgrade(
    item: Scenario,
    root: Path,
    data: Path,
    *,
    crash: int | None = None,
    first_id: int = 100,
    resume: bool = False,
    check: bool = False,
) -> UpgradeResult:
    services = real_services(
        root,
        data,
        workflow=item.workflow,
        wrap_project=None if crash is None else crash_after(crash),
        ids=SequentialIds(start=first_id),
    )
    return upgrade(services, UpgradeOptions(assume_yes=True, resume=resume, check=check))


@dataclass(frozen=True)
class Outcome:
    """What an uninterrupted upgrade does: the files before and after, and the writes in order."""

    before: dict[str, bytes]
    expected: dict[str, bytes]
    order: tuple[str, ...]


@pytest.fixture(scope="module")
def outcomes(
    templates: dict[str, Path], tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Outcome]:
    found: dict[str, Outcome] = {}
    for item in SCENARIOS:
        root, data = clone(templates[item.label], tmp_path_factory.mktemp(f"clean-{item.label}"))
        result = run_upgrade(item, root, data)
        assert result.status == "applied", (item.label, result.findings)
        assert result.plan is not None
        ordered = sorted(result.plan.writes, key=lambda w: (w.last, w.path.sort_key()))
        found[item.label] = Outcome(
            before=snapshot(templates[item.label] / "project"),
            expected=snapshot(root),
            order=tuple(str(write.path) for write in ordered),
        )
    return found


def interrupted(
    item: Scenario, templates: dict[str, Path], tmp_path: Path, crash: int
) -> tuple[Path, Path]:
    """A project in which the upgrade was stopped after `crash` writes."""
    root, data = clone(templates[item.label], tmp_path)
    with pytest.raises(SimulatedCrash):
        run_upgrade(item, root, data, crash=crash)
    return root, data


def open_changes(item: Scenario, root: Path, data: Path) -> list[str]:
    services = real_services(root, data, workflow=item.workflow)
    project_id = load_installation(services).profile.project.uuid
    return list(services.stores(project_id).journal.open_changes())


def holders(root: Path, data: Path) -> list[str]:
    """The files below the project and the data directory that hold the sentinel.

    The team's own `.mcp.json` is left out: it is the one file that is allowed to hold it.
    """
    needle = SENTINEL.encode()
    found = [
        f"project:{name}"
        for name, content in snapshot(root).items()
        if name != MCP and needle in content
    ]
    for path in sorted(data.rglob("*")):
        if path.is_file() and needle in path.read_bytes():
            found.append(f"data:{path.relative_to(data).as_posix()}")
    return found


def kill_points(item: Scenario, outcomes: dict[str, Outcome]) -> range:
    return range(len(outcomes[item.label].order))


def error_codes(item: Scenario, root: Path, data: Path) -> set[str]:
    services = real_services(root, data, workflow=item.workflow)
    return {f.code for f in doctor(services).findings if f.severity.value == "error"}


# --- the plan -------------------------------------------------------------------------------------


def test_the_plan_with_a_declaration_has_the_lock_as_its_last_write(
    scenario: Scenario, outcomes: dict[str, Outcome]
) -> None:
    """AC-8. expected_behavior_source: ORQLET-SAFE-001 and ADR-003 decision 5 ("the manifest is
    replaced last"; the lock is written after the file, so a kill between them leaves the file up
    to date) and ADR-003 decision 5 ("a diff against nothing" is one write, a proposal): the lock
    is last, and a new file or a proposal is in the plan before it. This fixes the kill points
    that the other tests stop at."""
    order = outcomes[scenario.label].order

    assert order[-1] == LOCK
    assert len(order) >= 2
    if scenario.team is None:
        assert MCP in order
        assert order.index(MCP) < order.index(LOCK)
    else:
        assert PROPOSAL in order
        assert MCP not in order


# --- the state after a kill -----------------------------------------------------------------------


def test_a_kill_after_each_write_leaves_whole_files_and_the_lock_behind(
    scenario: Scenario,
    templates: dict[str, Path],
    outcomes: dict[str, Outcome],
    tmp_path: Path,
) -> None:
    """AC-8. expected_behavior_source: ORQLET-TEST-002 (stop after each step), ORQLET-SAFE-001 ("the
    manifest is written last so a re-run converges") and ADR-003 decision 5 (the file of the team
    is never written): after each kill point the lock is still the old one, no temporary file is
    left, `.mcp.json` is the render or the team's own file or absent, and the sentinel is nowhere
    else."""
    outcome = outcomes[scenario.label]

    for crash in kill_points(scenario, outcomes):
        root, data = interrupted(scenario, templates, tmp_path / f"k{crash}", crash)

        partial = snapshot(root)
        assert not any(".orqlet-tmp-" in name for name in partial), "a temporary file was left"
        assert partial[LOCK] == outcome.before[LOCK], crash
        if scenario.team is None:
            assert partial.get(MCP) in {None, ATLASSIAN_TEXT.encode("utf-8")}, crash
            assert (partial.get(MCP) is not None) == (MCP in outcome.order[:crash]), crash
        else:
            assert partial[MCP] == scenario.team, crash
        assert holders(root, data) == [], crash


def test_a_file_that_is_written_when_the_lock_is_not_yet_is_up_to_date(
    templates: dict[str, Path], outcomes: dict[str, Outcome], tmp_path: Path
) -> None:
    """AC-8. expected_behavior_source: AC-8 ("an interrupted run (file written, lock not yet)
    classifies the file as up to date") and ADR-003 decision 5 ("an interrupted run (file written,
    lock not yet) classifies the file as up to date"): at each kill point of the new-file
    scenarios a check plans no write for `.mcp.json`, makes no proposal for it and says up to date
    for it when it is there, and plans to create it when it is not there yet."""
    for item in (SCENARIOS[0], SCENARIOS[1]):
        for crash in kill_points(item, outcomes):
            root, data = interrupted(item, templates, tmp_path / f"{item.label}-k{crash}", crash)
            written = (root / MCP).exists()

            check = run_upgrade(item, root, data, check=True)

            assert check.plan is not None, (item.label, crash)
            (mcp_item,) = [i for i in check.plan.items if str(i.path) == MCP]
            if written:
                assert (mcp_item.state, mcp_item.action) == (FileState.UP_TO_DATE, Action.NOOP)
                planned = {str(w.path) for w in check.plan.writes}
                assert MCP not in planned
                assert PROPOSAL not in planned
                assert LOCK in planned
            else:
                assert (mcp_item.state, mcp_item.action) == (FileState.NEW, Action.CREATE)


# --- a re-run (--resume) --------------------------------------------------------------------------


def test_resume_after_each_kill_gives_the_files_of_an_uninterrupted_run(
    scenario: Scenario,
    templates: dict[str, Path],
    outcomes: dict[str, Outcome],
    tmp_path: Path,
) -> None:
    """AC-8. expected_behavior_source: ORQLET-TEST-002 ("a re-run, or a rollback, converges to the
    same state"), ORQLET-SAFE-001, ADR-003 decision 5 ("Classification is unchanged, so a re-run,
    `--resume` and `--check` converge") and ADR-004 (`doctor` names the interrupted change,
    ORQ-E170, and the way out, `upgrade --resume`): after a kill at any point `doctor` flags the
    gap, `--resume` applies, and the project equals the project of an uninterrupted run. A further
    run and a check find nothing to do. No part of the sentinel is anywhere else."""
    outcome = outcomes[scenario.label]

    for crash in kill_points(scenario, outcomes):
        root, data = interrupted(scenario, templates, tmp_path / f"k{crash}", crash)
        assert "ORQ-E170" in error_codes(scenario, root, data), crash

        resumed = run_upgrade(scenario, root, data, first_id=500, resume=True)

        assert resumed.status == "applied", (crash, resumed.findings)
        assert snapshot(root) == outcome.expected, f"kill after {crash} writes did not converge"
        assert holders(root, data) == [], crash
        again = run_upgrade(scenario, root, data, first_id=700)
        check = run_upgrade(scenario, root, data, first_id=900, check=True)
        assert (again.status, check.status) == ("up-to-date", "up-to-date"), crash
        if scenario.creates_the_file:
            assert not error_codes(scenario, root, data), crash


# --- a rollback -----------------------------------------------------------------------------------


def test_rollback_of_the_interrupted_upgrade_restores_the_state_before_and_the_upgrade_runs_again(
    scenario: Scenario,
    templates: dict[str, Path],
    outcomes: dict[str, Outcome],
    tmp_path: Path,
) -> None:
    """AC-8. expected_behavior_source: ORQLET-TEST-002 ("a re-run, or a rollback, converges to the
    same state") and the contract of `rollback` (a file is restored only if it still equals what
    the change applied; a file that the change did not reach is as it was): the interrupted change
    is the one that the journal still has open; after its rollback the project is the one before,
    the team's own file is as it was, and the upgrade runs again and gives the files of an
    uninterrupted run. No part of the sentinel is anywhere else."""
    outcome = outcomes[scenario.label]

    for crash in kill_points(scenario, outcomes):
        root, data = interrupted(scenario, templates, tmp_path / f"k{crash}", crash)
        (change_id,) = open_changes(scenario, root, data)

        undone = rollback(
            real_services(root, data, workflow=scenario.workflow, ids=SequentialIds(start=900)),
            RollbackOptions(change_id, assume_yes=True),
        )

        assert undone.status == "applied", (crash, undone.findings)
        assert snapshot(root) == outcome.before, crash
        assert open_changes(scenario, root, data) == [], crash
        assert holders(root, data) == [], crash
        again = run_upgrade(scenario, root, data, first_id=1100)
        assert again.status == "applied", (crash, again.findings)
        assert snapshot(root) == outcome.expected, crash
        assert holders(root, data) == [], crash


def test_rollback_of_the_finished_upgrade_restores_the_state_before_and_the_upgrade_runs_again(
    scenario: Scenario,
    templates: dict[str, Path],
    outcomes: dict[str, Outcome],
    tmp_path: Path,
) -> None:
    """AC-8. expected_behavior_source: ORQLET-TEST-002 and the contract of `rollback` (a finished
    change is undone from its journal and its backups): the file that the upgrade created is
    removed, the one that it left alone is as it was, and the upgrade runs again and gives the
    files of an uninterrupted run."""
    outcome = outcomes[scenario.label]
    root, data = clone(templates[scenario.label], tmp_path)
    first = run_upgrade(scenario, root, data)
    assert first.status == "applied", first.findings
    assert first.change_id is not None

    undone = rollback(
        real_services(root, data, workflow=scenario.workflow, ids=SequentialIds(start=900)),
        RollbackOptions(first.change_id, assume_yes=True),
    )

    assert undone.status == "applied", undone.findings
    assert snapshot(root) == outcome.before
    assert holders(root, data) == []
    again = run_upgrade(scenario, root, data, first_id=1100)
    assert again.status == "applied", again.findings
    assert snapshot(root) == outcome.expected
