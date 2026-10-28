"""`orqlet upgrade` with a declaration, on real folders and the real command line (task
mcp-or-plugins, phase P-5; the criteria AC-5, AC-7, AC-8 and AC-9 on a real tree).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-00N-*.md`
under docs/design/mcp-or-plugins/design/, EC-n are the expected changes of the manifest.yaml next
to them, and AC-n are the criteria of phase P-5 in docs/design/mcp-or-plugins/plan.yaml.

These tests were written first, by the Tester of phase P-5, before the implementation existed. A
project is a copy of tests/fixtures/repos/uv_fastapi in a temporary folder, set up by `init` with
the packaged workflow (the same one that the command uses), and the data directory of the command
(`ORQLET_DATA_DIR`, where the journal and the backups are written) is a folder of the test, so that
every file that Orqlet writes outside the repository can be read. The declaration is the text of
the valid fixture with its one server changed to the one pair that the closed table enables (id
`atlassian`, address https://mcp.atlassian.com/v2/mcp, client `claude-code`).

A sentinel is a text that exists only in the team's own `.mcp.json`. It is assembled at run time
from parts and never written as one literal (ORQLET-SEC-003). The test then looks for it in every
planned write, in the preview and the JSON output of the command, in every other file of the
project, and in every file of the data directory (the journal and the backups).

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- the wording of any message, the code that the command prints for the refusal of a link or a
  folder at `.mcp.json` (the command exits 3; `plan_changes` itself refuses with ORQ-E114), and
  whether the findings that follow an apply are printed in the human text or only in the JSON;
- whether the lock records an existing file that equals the render in the same run in which it is
  found up to date (only that the file is not written and no proposal is made);
- what `upgrade --check` prints for a team whose file differs (only that it finds nothing to
  write once the proposal exists, ADR-003 decision 5);
- whether `--check` and `--dry-run` refuse an invalid declaration (the tests require it, from
  "before any plan is built", ADR-003 decision 3; it is listed as a question).
"""

from __future__ import annotations

import copy
import difflib
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.generated_lock import GeneratedLock, LockedFile
from orqlet.application.contracts.loading import load_contract
from orqlet.application.usecases.init_project import InitOptions, InitServices, init_project
from orqlet.application.usecases.init_state import InitRefused
from orqlet.application.usecases.upgrade import UpgradeOptions, UpgradeResult, upgrade
from orqlet.domain.changeplan import Action, PlannedItem, proposal_path
from orqlet.domain.classify import FileState
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.interface.cli.app import app
from orqlet.interface.cli.wiring import DATA_DIR_VARIABLE
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import SequentialIds
from tests.support.git import clean_environ, make_repo
from tests.support.real_env import real_services, snapshot
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()
ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"  # the one address of the closed table
OTHER_ADDRESS = "https://docs.example.com/mcp"  # a good address for the contract, not on the table
EDITABLE = "client-enforced-editable"
DECLARATION = ".orqlet/integrations.yaml"
MCP = ".mcp.json"
LOCK = ".orqlet/generated.lock.yaml"
TAMPERED = ".claude/rules/orqlet-workflow.md"  # a protected file: an edit of it is restored
PROPOSAL = str(proposal_path(CanonicalPath.parse(MCP), None))  # .orqlet/proposals/.mcp.json.diff
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
REPORT = "ORQ-I534"  # plan P-5 and ADR-003 decision 5: the proposal shows only the wanted text
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

SENTINEL = "".join(("team-", "only-", "text-", "9d3e", "a5b1"))
TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0JxQz4M", "Ka8Ty2Vb"))


# --- the project ----------------------------------------------------------------------------------


class Project:
    """A real project and its data directory, with the services and the command line to match."""

    def __init__(self, root: Path, data: Path) -> None:
        self.root = root
        self.data = data
        self._ids = count(1000, 100)

    def services(self, *, wrap: Callable[[Any], Any] | None = None) -> InitServices:
        return real_services(
            self.root,
            self.data,
            wrap_project=wrap,
            ids=SequentialIds(start=next(self._ids)),
            workflow=PackagedWorkflow(),
        )

    def upgrade(self, *, dry_run: bool = False, assume_yes: bool = False) -> UpgradeResult:
        options = UpgradeOptions(dry_run=dry_run, assume_yes=assume_yes)
        return upgrade(self.services(), options)

    def command(self, *args: str, json_output: bool = True) -> Run:
        """`orqlet upgrade --root <project> ...` with this project's data directory."""
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv(DATA_DIR_VARIABLE, str(self.data))
            for name, value in clean_environ(self.root.parent).items():
                patch.setenv(name, value)
            tail = ["--json"] if json_output else []
            result = RUNNER.invoke(app, ["upgrade", "--root", str(self.root), *args, *tail])
        document = json.loads(result.stdout) if json_output else None
        return Run(result.exit_code, result.output, document)

    def write(self, name: str, content: bytes) -> None:
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def read(self, name: str) -> bytes:
        return (self.root / name).read_bytes()

    def exists(self, name: str) -> bool:
        return (self.root / name).exists()

    def files(self) -> dict[str, bytes]:
        return snapshot(self.root)

    def data_files(self) -> dict[str, bytes]:
        return snapshot_all(self.data)

    def lock_entry(self, name: str) -> LockedFile | None:
        lock = load_contract(StrictYamlLoader(), GeneratedLock, self.read(LOCK), source=LOCK)
        return next((entry for entry in lock.files if entry.path == name), None)


@dataclass(frozen=True)
class Run:
    code: int
    output: str
    document: dict[str, Any] | None

    @property
    def data(self) -> dict[str, Any]:
        assert self.document is not None
        data: dict[str, Any] = self.document["data"]
        return data

    @property
    def findings(self) -> list[dict[str, Any]]:
        assert self.document is not None
        found: list[dict[str, Any]] = self.document["findings"]
        return found

    def written(self) -> set[tuple[str, str]]:
        return {(item["path"], item["kind"]) for item in self.data["writes"]}


def snapshot_all(folder: Path) -> dict[str, bytes]:
    """Every file below `folder`, by relative POSIX path, the journal and the backups included."""
    if not folder.exists():
        return {}
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def initialised(
    tmp_path: Path, name: str = "p", before: Callable[[Path], None] | None = None
) -> Project:
    """A project after `init`, with the real packaged workflow. `before` prepares the folder."""
    root = tmp_path / name / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    if before is not None:
        before(root)
    data = tmp_path / f"data-{name}"
    result = init_project(
        real_services(root, data, workflow=PackagedWorkflow()), InitOptions(assume_yes=True)
    )
    assert result.status == "applied", result.findings
    return Project(root, data)


# --- the declaration and the team's file ----------------------------------------------------------


def declaration(*, url: str = ATLASSIAN, **changes: Any) -> bytes:
    """A valid declaration with one server `atlassian` for Claude Code, as JSON text."""
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    base = copy.deepcopy(data["servers"][0])
    base.update(
        id="atlassian",
        identity={"kind": "remote", "url": url},
        registration={"name": "orqlet-atlassian", "mode": "read-only", "enforced_by": EDITABLE},
        per_client={"claude-code": {"register": True, "enforced_by": EDITABLE}},
        clients=["claude-code"],
    )
    base.update(changes)
    data["servers"] = [base]
    data["roles"] = {"architecture-reviewer": {"servers": ["atlassian"]}}
    return json.dumps(data, indent=2).encode()


def team_json() -> bytes:
    """The team's own file: one server of its own, whose name and address hold the sentinel."""
    document = {
        "mcpServers": {
            f"team-{SENTINEL}": {"type": "http", "url": f"https://example.com/{SENTINEL}"}
        }
    }
    return (json.dumps(document, indent=2) + "\n").encode()


# name -> the bytes of a team file that differs from the render and holds the sentinel
TEAM_FILES: dict[str, bytes] = {
    "json": team_json(),
    "json-with-windows-line-ends": team_json().replace(b"\n", b"\r\n"),
    "not-json": f"notes of the team: {SENTINEL}\n".encode(),
    "not-utf-8": b"\xff\xfe" + SENTINEL.encode() + b"\x00\x80\n",
    "empty-and-then-the-text": b"\n\n\n" + SENTINEL.encode(),
}


def holders(project: Project, secret: str = SENTINEL) -> list[str]:
    """The files of the project and of the data directory that hold `secret`, `.mcp.json` apart."""
    needle = secret.encode()
    found = [
        f"project:{name}"
        for name, content in project.files().items()
        if name != MCP and needle in content
    ]
    found += [f"data:{name}" for name, content in project.data_files().items() if needle in content]
    return found


def wanted_only_diff(text: str = ATLASSIAN_TEXT) -> str:
    """The proposal for `.mcp.json` as a diff against nothing: the wanted text and no other."""
    lines = difflib.unified_diff(
        [], text.splitlines(), fromfile=f"a/{MCP}", tofile=f"b/{MCP}", lineterm="", n=3
    )
    return "\n".join(lines) + "\n"


def mcp_item(result: UpgradeResult) -> PlannedItem:
    assert result.plan is not None
    (item,) = [i for i in result.plan.items if str(i.path) == MCP]
    return item


def reports(result: UpgradeResult) -> list[Finding]:
    return [finding for finding in result.findings if finding.code == REPORT]


def reports_in(run: Run) -> list[dict[str, Any]]:
    return [finding for finding in run.findings if finding["code"] == REPORT]


# --- AC-5: no declaration, an invalid one, a valid one --------------------------------------------


def test_ac5_without_a_declaration_the_command_writes_no_mcp_file(tmp_path: Path) -> None:
    """AC-5. expected_behavior_source: AC-5 ("upgrade with no declaration writes no MCP file") and
    ADR-003 decision 2 ("When it is absent, `upgrade` writes no MCP file")."""
    project = initialised(tmp_path)
    before = project.files()

    run = project.command("--yes")

    assert run.code == 0
    assert run.data["status"] == "up-to-date"
    assert project.files() == before
    assert not project.exists(MCP)
    assert not reports_in(run)


def test_ac5_a_valid_declaration_makes_the_command_create_the_file_and_record_it(
    tmp_path: Path,
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("with a valid declaration it creates .mcp.json with
    the rendered text and records it in the lock with owner seeded") and ADR-003 decision 5
    ("owner `seeded` and no file class"), on a real tree."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())

    run = project.command("--yes")

    assert run.code == 0
    assert run.data["status"] == "applied"
    assert run.written() == {(MCP, "create"), (LOCK, "update")}
    assert project.read(MCP) == ATLASSIAN_TEXT.encode("utf-8")
    entry = project.lock_entry(MCP)
    assert entry is not None
    assert entry.owner is OwnerMode.SEEDED
    assert entry.file_class is None
    assert not reports_in(run)


@pytest.mark.parametrize(
    ("changes", "url", "code"),
    [
        (
            {
                "registration": {
                    "name": "orqlet-other",
                    "mode": "read-only",
                    "enforced_by": EDITABLE,
                }
            },
            ATLASSIAN,
            "ORQ-E531",
        ),
        ({}, OTHER_ADDRESS, "ORQ-E532"),
        ({"purpose": f"search with {TOKEN}"}, ATLASSIAN, "ORQ-E533"),
    ],
    ids=["fails-its-contract", "not-on-the-table", "holds-a-token"],
)
def test_ac5_an_invalid_declaration_exits_3_and_nothing_is_written(
    tmp_path: Path, changes: dict[str, Any], url: str, code: str
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("with an invalid declaration it refuses with exit 3
    and writes nothing, including the other generated files") and ADR-003 decision 3 ("`upgrade`
    refuse[s] with exit 3 and write[s] nothing"): the project and the data directory are as they
    were, and the output names a rule of the loader and shows no part of the token."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration(url=url, **changes))
    before, before_data = project.files(), project.data_files()

    run = project.command("--yes")

    assert run.code == 3
    assert run.document is not None
    assert run.document["ok"] is False
    assert code in {finding["code"] for finding in run.findings}
    assert project.files() == before
    assert project.data_files() == before_data
    assert TOKEN[:12] not in json.dumps(run.document)


@pytest.mark.parametrize("flags", [["--check"], ["--dry-run"]], ids=["check", "preview"])
def test_ac5_a_check_and_a_preview_refuse_an_invalid_declaration_too(
    tmp_path: Path, flags: list[str]
) -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 3 ("returns a refused result before any
    plan is built") and ORQLET-SAFE-001: `--check` and `--dry-run` exit 3 as the real run does."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration(url=OTHER_ADDRESS))
    before = project.files()

    run = project.command(*flags)

    assert run.code == 3
    assert project.files() == before


# --- AC-7: an existing file that equals the render ------------------------------------------------


@pytest.mark.parametrize("line_end", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_ac7_an_existing_file_that_equals_the_render_is_up_to_date_and_is_not_written(
    tmp_path: Path, line_end: str
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("An existing .mcp.json that equals the render is up to
    date and nothing is written") and ADR-003 decision 5 ("Classification is unchanged": a seeded
    file that equals the render is up to date, line ends read as LF): the file keeps its bytes, no
    proposal is made, no information finding is printed, and the next run finds nothing to do."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    team = ATLASSIAN_TEXT.replace("\n", line_end).encode("utf-8")
    project.write(MCP, team)

    first = project.upgrade(dry_run=True)

    assert mcp_item(first).state is FileState.UP_TO_DATE
    assert first.plan is not None
    assert MCP not in {str(w.path) for w in first.plan.writes}
    assert not [w for w in first.plan.writes if w.is_proposal]
    assert not reports(first)
    run = project.command("--yes")
    assert run.code == 0
    assert MCP not in {path for path, _ in run.written()}
    assert not [path for path, _ in run.written() if path.startswith(".orqlet/proposals/")]
    assert project.read(MCP) == team
    assert not reports_in(run)
    again = project.command("--yes")
    assert again.data["status"] == "up-to-date"
    assert again.data["writes"] == []
    assert project.read(MCP) == team


# --- AC-7: an existing file that differs ----------------------------------------------------------


@pytest.mark.parametrize("name", list(TEAM_FILES))
def test_ac7_a_differing_file_gets_a_proposal_that_holds_the_wanted_text_only(
    tmp_path: Path, name: str
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("one that differs gets a proposal item with the wanted
    text only") and ADR-003 decision 5 ("The proposal is then a diff against nothing: it shows the
    text that Orqlet wants and none of the team's file"; the file of the team is never changed):
    the item is a seeded proposal, the one proposal write is the diff of the specification, and the
    team's file keeps its bytes. The team's text is JSON, not JSON, not UTF-8, or line ends of
    Windows."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    project.write(MCP, TEAM_FILES[name])

    result = project.upgrade(dry_run=True)

    item = mcp_item(result)
    assert (item.state, item.action) == (FileState.SEEDED_PROPOSAL, Action.PROPOSE)
    assert result.plan is not None
    (proposal,) = [w for w in result.plan.writes if w.is_proposal]
    assert str(proposal.path) == PROPOSAL
    assert proposal.content == wanted_only_diff().encode("utf-8")
    assert MCP not in {str(w.path) for w in result.plan.writes}
    assert project.read(MCP) == TEAM_FILES[name]


def test_ac7_one_information_finding_names_the_proposal_and_holds_no_text_of_the_team(
    tmp_path: Path,
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("one information finding ORQ-I534 for each such
    item") and ADR-003 decision 5 ("`upgrade` prints one information finding for every plan item
    that is a seeded proposal on an MCP path"; the code is ORQ-I534 of the plan P-5): one item,
    one finding, severity information, and the finding shows nothing of the team's file. The
    wording is not pinned."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    project.write(MCP, team_json())

    result = project.upgrade(dry_run=True)

    (finding,) = reports(result)
    assert finding.severity is Severity.INFO
    assert finding.message
    assert SENTINEL not in f"{finding.message} {finding.path}"


def test_ac7_no_information_finding_when_the_file_is_absent_equal_or_not_wanted(
    tmp_path: Path,
) -> None:
    """AC-7. expected_behavior_source: ADR-003 decision 5 (the finding is for "every plan item that
    is a seeded proposal on an MCP path"): a new file, an equal file, and a project with no
    declaration give none, while a differing file next to a declaration gives one."""
    created = initialised(tmp_path, "created")
    created.write(DECLARATION, declaration())
    equal = initialised(tmp_path, "equal")
    equal.write(DECLARATION, declaration())
    equal.write(MCP, ATLASSIAN_TEXT.encode("utf-8"))
    undeclared = initialised(tmp_path, "undeclared")
    undeclared.write(MCP, team_json())
    differing = initialised(tmp_path, "differing")
    differing.write(DECLARATION, declaration())
    differing.write(MCP, team_json())

    assert reports(created.upgrade(dry_run=True)) == []
    assert reports(equal.upgrade(dry_run=True)) == []
    assert reports(undeclared.upgrade(dry_run=True)) == []
    assert len(reports(differing.upgrade(dry_run=True))) == 1


def test_ac7_a_seeded_proposal_on_another_path_gets_no_information_finding(tmp_path: Path) -> None:
    """AC-7. expected_behavior_source: ADR-003 decision 5 (ORQ-I534 is printed "for every plan item
    that is a seeded proposal on an MCP path"; the other seeded proposals keep what they had): a
    team file at a seed path (`.prompts/README.md`) that differs from the seed is a seeded proposal
    of `init`; with it in the project, the one differing `.mcp.json` still gives exactly one."""

    def team_prompts(root: Path) -> None:
        (root / ".prompts").mkdir()
        (root / ".prompts" / "README.md").write_text("The notes of our team.\n", encoding="utf-8")

    project = initialised(tmp_path, before=team_prompts)
    project.write(DECLARATION, declaration())
    project.write(MCP, team_json())

    result = project.upgrade(dry_run=True)

    proposals = [
        item
        for item in (result.plan.items if result.plan else ())
        if item.state is FileState.SEEDED_PROPOSAL
    ]
    assert {str(item.path) for item in proposals} == {".prompts/README.md", MCP}
    assert len(reports(result)) == 1


@pytest.mark.parametrize("name", list(TEAM_FILES))
def test_ac7_no_byte_of_the_team_file_reaches_a_plan_a_preview_an_output_the_journal_or_a_backup(
    tmp_path: Path, name: str
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("a sentinel placed at run time in the existing file is
    absent from every planned write, the preview, the JSON output, the journal and the backups"),
    ADR-003 decision 5 ("A test at the `upgrade` level puts a run-time sentinel in an existing
    `.mcp.json` and asserts that it is absent from every planned write, the preview, the JSON
    output, the journal and the backups") and ORQLET-SAFE-001, ORQLET-SEC-003: the planned
    writes and the findings of the use case, the human preview and the JSON preview of the
    command, the human output and the JSON output of the apply, every other file of the project,
    and every file of the data directory hold no part of the sentinel. The team's file is as it
    was. A protected file that the team edited is restored in the same run, so that the data
    directory holds a backup as well as a journal and the scan is not empty."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    project.write(MCP, TEAM_FILES[name])
    project.write(TAMPERED, b"weakened\n")
    needle = SENTINEL.encode()

    result = project.upgrade(dry_run=True)
    assert result.plan is not None
    assert result.plan.writes
    for write in result.plan.writes:
        assert needle not in (write.content or b""), write.path
        assert SENTINEL not in str(write.path)
    assert SENTINEL not in "\n".join(f"{f.code} {f.message} {f.path}" for f in result.findings)

    preview = project.command("--dry-run", json_output=False)
    preview_json = project.command("--dry-run")
    assert (preview.code, preview_json.code) == (0, 0)
    assert SENTINEL not in preview.output
    assert SENTINEL not in json.dumps(preview_json.document)
    assert project.read(MCP) == TEAM_FILES[name]
    assert holders(project) == []

    applied = project.command("--yes")
    assert applied.code == 0
    assert applied.data["status"] == "applied"
    assert SENTINEL not in json.dumps(applied.document)
    assert project.read(MCP) == TEAM_FILES[name]
    assert holders(project) == []
    assert [path for path in project.data_files() if "/upgrade/" in path]  # a journal
    assert [path for path in project.data_files() if "/backups/" in path]  # a backup
    assert project.exists(PROPOSAL)
    assert project.read(PROPOSAL) == wanted_only_diff().encode("utf-8")


def test_ac7_the_proposal_and_its_information_finding_come_back_on_every_run(
    tmp_path: Path,
) -> None:
    """AC-7. expected_behavior_source: ADR-003 decision 5 ("a team whose file holds its own servers
    never equals the render, so its proposal item and its information finding appear on every run
    until the team merges the wanted text; a proposal file that already holds the same text is not
    rewritten, so `upgrade --check` finds nothing to write"): after the first apply the next run
    and a check write nothing, find one proposal item and print one information finding each."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    project.write(MCP, team_json())
    project.command("--yes")
    settled, settled_data = project.files(), project.data_files()

    check = project.command("--check")
    again = project.command("--yes")
    third = project.upgrade(dry_run=True)

    assert (check.code, again.code) == (0, 0)
    assert check.data["status"] == again.data["status"] == "up-to-date"
    assert check.data["writes"] == again.data["writes"] == []
    assert len(reports_in(check)) == len(reports_in(again)) == 1
    assert mcp_item(third).state is FileState.SEEDED_PROPOSAL
    assert len(reports(third)) == 1
    assert project.files() == settled
    assert project.data_files() == settled_data
    assert project.lock_entry(MCP) is None


def test_ac7_a_team_that_merges_the_wanted_text_ends_the_proposal_and_the_finding(
    tmp_path: Path,
) -> None:
    """AC-7. expected_behavior_source: ADR-003 decision 5 ("until the team merges the wanted
    text"): once the team's file equals the render, the item is up to date and no finding is
    printed. The proposal file stays where it is: Orqlet deletes none."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    project.write(MCP, team_json())
    project.command("--yes")
    project.write(MCP, ATLASSIAN_TEXT.encode("utf-8"))

    run = project.command("--yes")

    assert run.code == 0
    assert not reports_in(run)
    assert not [kind for path, kind in run.written() if path == MCP]
    assert project.read(MCP) == ATLASSIAN_TEXT.encode("utf-8")
    assert holders(project) == []


# --- AC-7: a file that the team deleted -----------------------------------------------------------


def test_ac7_a_file_that_the_team_deleted_after_orqlet_wrote_it_is_not_restored(
    tmp_path: Path,
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("a file that the team deleted is not restored") and
    ADR-003 decision 5 ("A team that deletes the file does not get it back (`classify.py:73`);
    recreating it is the team's step"): after the file is written and recorded and then deleted,
    a run, a preview and a check write nothing and print no finding about it."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    project.command("--yes")
    assert project.exists(MCP)
    (project.root / MCP).unlink()
    settled = project.files()

    run = project.command("--yes")
    check = project.command("--check")

    assert run.code == 0
    assert run.data["status"] == "up-to-date"
    assert run.data["writes"] == []
    assert check.code == 0
    assert not project.exists(MCP)
    assert not reports_in(run)
    assert project.files() == settled


# --- AC-8: --check, --resume ----------------------------------------------------------------------


def test_ac8_a_check_reports_the_file_that_would_be_created_and_writes_nothing(
    tmp_path: Path,
) -> None:
    """AC-8. expected_behavior_source: AC-8 ("A re-run, --resume and --check converge") and
    ADR-003 decision 5 ("so a re-run, `--resume` and `--check` converge"): before the first run a
    check says that a change is available (exit 1) and lists the file, and writes nothing; after
    the run a check says that nothing is to do (exit 0)."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    before, before_data = project.files(), project.data_files()

    check = project.command("--check")

    assert check.code == 1
    assert check.data["status"] == "available"
    assert (MCP, "create") in check.written()
    assert project.files() == before
    assert project.data_files() == before_data
    project.command("--yes")
    after = project.command("--check")
    assert (after.code, after.data["status"], after.data["writes"]) == (0, "up-to-date", [])


def test_ac8_a_resume_with_nothing_to_finish_changes_nothing(tmp_path: Path) -> None:
    """AC-8. expected_behavior_source: AC-8 and ADR-003 decision 5 ("a re-run, `--resume` and
    `--check` converge"): `--resume` on a project whose change finished is the plain run."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    project.command("--yes")
    settled = project.files()

    run = project.command("--resume", "--yes")

    assert run.code == 0
    assert run.data["status"] == "up-to-date"
    assert project.files() == settled


def crash_after(writes: int) -> Callable[[Any], Any]:
    return lambda fs: FaultyFileSystem(fs, crash_after_writes=writes)


@pytest.mark.parametrize("writes_before_the_crash", [0, 1], ids=["before-any-write", "after-one"])
def test_ac8_an_interrupted_upgrade_is_finished_by_resume_and_the_journal_holds_no_team_text(
    tmp_path: Path, writes_before_the_crash: int
) -> None:
    """AC-7, AC-8. expected_behavior_source: AC-7 (the sentinel is absent from the journal), AC-8
    ("--resume ... converge") and ADR-003 decision 5 ("Classification is unchanged, so a re-run,
    `--resume` and `--check` converge"): an upgrade for a team file that differs (its plan holds
    the restore of an edited protected file and then the proposal) stops after no write or after
    one, a plain run is refused because of the unfinished change, `--resume` finishes it, and the
    project is the one of an uninterrupted run. The journal of the interrupted change and the
    finished one hold no part of the sentinel."""
    clean = initialised(tmp_path, "clean")
    project = initialised(tmp_path, "crashed")
    for each in (clean, project):
        each.write(DECLARATION, declaration())
        each.write(MCP, team_json())
        each.write(TAMPERED, b"weakened\n")
    assert clean.command("--yes").code == 0

    with pytest.raises(SimulatedCrash):
        upgrade(
            project.services(wrap=crash_after(writes_before_the_crash)),
            UpgradeOptions(assume_yes=True),
        )

    assert holders(project) == []
    assert [path for path in project.data_files() if "/upgrade/" in path]
    refused = project.command("--yes")
    assert refused.code == 3
    resumed = project.command("--resume", "--yes")
    assert resumed.code == 0
    assert resumed.data["status"] == "applied"
    assert project.files() == clean.files()
    assert holders(project) == []
    assert project.read(MCP) == team_json()


# --- AC-9: a link or a folder at .mcp.json --------------------------------------------------------


def make_link(project: Project, tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_bytes(team_json())
    try:
        (project.root / MCP).symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot create symbolic links")


def make_folder(project: Project, tmp_path: Path) -> None:
    (project.root / MCP).mkdir()
    (project.root / MCP / "inner.txt").write_text(f"{SENTINEL}\n", encoding="utf-8")


LINKS_AND_FOLDERS: dict[str, Callable[[Project, Path], None]] = {
    "a-symbolic-link": make_link,
    "a-folder": make_folder,
}


@pytest.mark.parametrize("name", list(LINKS_AND_FOLDERS))
def test_ac9_with_a_declaration_a_link_or_a_folder_at_the_mcp_file_exits_3_before_any_write(
    tmp_path: Path, name: str
) -> None:
    """AC-9. expected_behavior_source: AC-9 ("With a declaration that registers Claude Code, a
    symlinked or non-regular .mcp.json makes plan_changes refuse with ORQ-E114 and upgrade exit 3
    before anything is written") and ADR-002 decision 8: the command exits 3, the project and the
    data directory are as they were (so no journal), a preview and a check refuse too, and no
    part of the file behind the link or inside the folder is printed or written."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    LINKS_AND_FOLDERS[name](project, tmp_path)
    before, before_data = project.files(), project.data_files()

    runs = [project.command(*flags) for flags in (["--yes"], ["--dry-run"], ["--check"])]

    for run in runs:
        assert run.code == 3
        assert run.document is not None
        assert run.document["ok"] is False
        assert [f for f in run.findings if f["severity"] == "error"]
        assert SENTINEL not in json.dumps(run.document)
    assert project.files() == before
    assert project.data_files() == before_data


@pytest.mark.parametrize("name", list(LINKS_AND_FOLDERS))
def test_ac9_the_use_case_refuses_with_orq_e114(tmp_path: Path, name: str) -> None:
    """AC-9. expected_behavior_source: AC-9 and ADR-002 decision 8 ("`plan_changes` already refuses
    with `ORQ-E114`"): `upgrade` stops with the code ORQ-E114, raised by `plan_changes` or
    returned as a refusal, and writes nothing."""
    project = initialised(tmp_path)
    project.write(DECLARATION, declaration())
    LINKS_AND_FOLDERS[name](project, tmp_path)
    before, before_data = project.files(), project.data_files()
    refused_with: set[str] = set()

    try:
        result = project.upgrade(assume_yes=True)
    except InitRefused as error:
        refused_with = {error.code}
    else:
        assert result.status == "refused"
        refused_with = {finding.code for finding in result.findings}

    assert "ORQ-E114" in refused_with
    assert project.files() == before
    assert project.data_files() == before_data


@pytest.mark.parametrize("name", list(LINKS_AND_FOLDERS))
def test_ac9_without_a_declaration_the_same_link_or_folder_does_not_stop_the_command(
    tmp_path: Path, name: str
) -> None:
    """AC-9. expected_behavior_source: ADR-002 decision 8 ("a project without a declaration keeps
    its behaviour") and ADR-003 decision 2: with no declaration no `.mcp.json` is wanted, so the
    link or the folder is not read and the command finds nothing to do."""
    project = initialised(tmp_path)
    LINKS_AND_FOLDERS[name](project, tmp_path)

    run = project.command("--yes")

    assert run.code == 0
    assert run.data["status"] == "up-to-date"
