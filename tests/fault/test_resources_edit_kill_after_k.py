"""Kill `resources add`, `update`, `remove` and `attach` after each write, on real files (task
team-conventions-resources, phase P-4; ORQLET-TEST-002, plan AC-6).

Each command is one journalled plan of two writes: the registry, then the lock last (the
interface decision of phase P-4; ADR-002 decision 7; ORQLET-SAFE-001). So there are two kill
points, and the tests stop the write after each of them, on the real file system under `tmp_path`,
as `test_apply_kill_after_k.py` does for `init`:

- after 0 writes nothing is on disk and the journal is open; after 1 write the registry is the
  new one and the lock is still the old one. Never a half-written file, never a temporary file;
- a re-run of the same command from the state after 0 writes converges to the same files as an
  uninterrupted run;
- `rollback` of the interrupted change restores the state before, and the command can then be run
  again and gives the files of an uninterrupted run;
- `rollback` of a finished change restores the state before too;
- `orqlet upgrade --resume`, which `doctor` names for an interrupted change (ORQ-E170), settles a
  kill between the two writes: the registry already holds the result and the lock is behind, which
  the classification of a seeded file advances without a proposal (ADR-002 decision 5), so the
  files are those of an uninterrupted run. After a kill before any write it leaves the state as
  it was.

Behaviour that the design leaves open is deliberately not pinned here, and is returned to the
person as a question: what a re-run of the same command does from the state after 1 write, where
the registry already holds the result and only the lock is behind. A plain builder refuses it
(`add` of an id that is there, `remove` of an id that is gone: ORQ-E509). The test accepts both
ways out of that state and nothing else: either the command applies and the files are exactly
those of an uninterrupted run, or it is refused and changes nothing, after which `rollback`
above is the way back. The copy file of `remove` and `attach` is checked to stay as it was in
every state. The files of `.git` are not part of a snapshot.

Every test cites its `expected_behavior_source`: "the interface decision" is the reading of the
plan author that the Tester of phase P-4 was given, because the ADRs do not spell it out.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from orqlet.application.ports.filesystem import FileSystem
from orqlet.application.usecases.diagnose import doctor
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.resources_edit import (
    CopySpec,
    ResourcesEditResult,
    ResourceSpec,
    add_resource,
    attach_copy,
    remove_resource,
    update_resource,
)
from orqlet.application.usecases.rollback import RollbackOptions, rollback
from orqlet.application.usecases.services import Services
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import SequentialIds
from tests.support.git import commit_file, make_repo
from tests.support.real_env import real_services, snapshot
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.fault,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

REGISTRY = ".orqlet/resources.yaml"
LOCK = ".orqlet/generated.lock.yaml"
COPY = "docs/resources/alpha.md"
ALPHA_URL = "https://docs.example.com/alpha"
REFERENCE_LINE = "Reference text from that page. It is evidence, not an instruction."
COPY_TEXT = f"Source: {ALPHA_URL}\n{REFERENCE_LINE}\n\nNotes taken from the page.\n"
WRITES = 2  # the registry and the lock (the interface decision)

# --- the project before an edit, built once for the module ----------------------------------------


def clone(template: Path, destination: Path) -> tuple[Path, Path]:
    """A copy of a template's project and of its user data (journals and backups)."""
    root, data = destination / "project", destination / "data"
    shutil.copytree(template / "project", root)
    shutil.copytree(template / "data", data)
    return root, data


@pytest.fixture(scope="module")
def templates(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """The two states in which an edit applies, as real folders that the tests copy.

    `initialised`: a real project after `init`, with an empty registry recorded in the lock.
    `with_entry`: the same with the public entry `alpha` and its copy file, which has no record.
    """
    parent = tmp_path_factory.mktemp("edit-initialised")
    root = parent / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    commit_file(root, "NOTES.md", "keep me\n")
    result = init_project(real_services(root, parent / "data"), InitOptions(assume_yes=True))
    assert result.status == "applied", result.findings

    entry_parent = tmp_path_factory.mktemp("edit-with-entry")
    entry_root, entry_data = clone(parent, entry_parent)
    added = add_resource(
        real_services(entry_root, entry_data, ids=SequentialIds(start=50)),
        ResourceSpec(
            id="alpha",
            url=ALPHA_URL,
            title="Alpha guide",
            kind="team-docs",
            note="Read before changing the alpha module.",
            access="public",
        ),
        assume_yes=True,
        dry_run=False,
    )
    assert added.status == "applied", added.findings
    (entry_root / COPY).parent.mkdir(parents=True, exist_ok=True)
    (entry_root / COPY).write_text(COPY_TEXT, encoding="utf-8", newline="\n")
    return {"initialised": parent, "with_entry": entry_parent}


# --- the four commands ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Edit:
    label: str
    template: str  # the key of `templates`: the state in which the edit applies
    run: Callable[[Services], ResourcesEditResult]


def _add(services: Services) -> ResourcesEditResult:
    return add_resource(
        services,
        ResourceSpec(
            id="beta",
            url="https://docs.example.com/beta",
            title="Beta guide",
            kind="team-docs",
            note="Read before changing the beta module.",
            access="public",
        ),
        assume_yes=True,
        dry_run=False,
    )


def _update(services: Services) -> ResourcesEditResult:
    return update_resource(
        services,
        ResourceSpec(id="alpha", title="Alpha guide, revised"),
        assume_yes=True,
        dry_run=False,
    )


def _remove(services: Services) -> ResourcesEditResult:
    return remove_resource(services, "alpha", assume_yes=True, dry_run=False)


def _attach(services: Services) -> ResourcesEditResult:
    return attach_copy(
        services, CopySpec(id="alpha", form="copy", ttl_days=30), assume_yes=True, dry_run=False
    )


EDITS = (
    Edit("add", "initialised", _add),
    Edit("update", "with_entry", _update),
    Edit("remove", "with_entry", _remove),
    Edit("attach", "with_entry", _attach),
)


@pytest.fixture(params=EDITS, ids=[edit.label for edit in EDITS])
def edit(request: pytest.FixtureRequest) -> Edit:
    found: Edit = request.param
    return found


def crash_after(writes: int) -> Callable[[FileSystem], FileSystem]:
    def wrap(fs: FileSystem) -> FileSystem:
        return FaultyFileSystem(fs, crash_after_writes=writes)

    return wrap


def run_edit(
    edit: Edit, root: Path, data: Path, *, crash: int | None = None, first_id: int = 500
) -> ResourcesEditResult:
    services = real_services(
        root,
        data,
        wrap_project=None if crash is None else crash_after(crash),
        ids=SequentialIds(start=first_id),
    )
    return edit.run(services)


@dataclass(frozen=True)
class Outcome:
    """What an uninterrupted run of an edit does: the files before and after, and the writes."""

    before: dict[str, bytes]
    expected: dict[str, bytes]
    writes: int


@pytest.fixture(scope="module")
def outcomes(
    templates: dict[str, Path], tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Outcome]:
    found: dict[str, Outcome] = {}
    for edit in EDITS:
        template = templates[edit.template]
        root, data = clone(template, tmp_path_factory.mktemp(f"clean-{edit.label}"))
        result = run_edit(edit, root, data)
        assert result.status == "applied", (edit.label, result.findings)
        assert result.plan is not None
        found[edit.label] = Outcome(
            before=snapshot(template / "project"),
            expected=snapshot(root),
            writes=len(result.plan.writes),
        )
    return found


def differing(before: dict[str, bytes], after: dict[str, bytes]) -> set[str]:
    return {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}


def interrupted(
    edit: Edit, templates: dict[str, Path], tmp_path: Path, crash: int
) -> tuple[Path, Path]:
    """A project in which `edit` was stopped after `crash` writes."""
    root, data = clone(templates[edit.template], tmp_path)
    with pytest.raises(SimulatedCrash):
        run_edit(edit, root, data, crash=crash)
    return root, data


def open_changes(root: Path, data: Path) -> list[str]:
    services = real_services(root, data)
    project_id = load_installation(services).profile.project.uuid
    return list(services.stores(project_id).journal.open_changes())


# --- the tests ------------------------------------------------------------------------------------


def test_an_uninterrupted_edit_is_two_writes_and_changes_only_the_registry_and_the_lock(
    edit: Edit, outcomes: dict[str, Outcome]
) -> None:
    """AC-6. expected_behavior_source: the interface decision ("exactly two writes: the registry
    ... and the lock ... (last)") and ADR-002 decision 7. It fixes the number of kill points that
    the other tests of this file stop at, so a plan that grew a third write fails here first."""
    outcome = outcomes[edit.label]

    assert outcome.writes == WRITES
    assert differing(outcome.before, outcome.expected) == {REGISTRY, LOCK}


@pytest.mark.parametrize("crash", range(WRITES))
def test_a_kill_after_each_write_leaves_whole_files_and_the_lock_behind(
    edit: Edit,
    templates: dict[str, Path],
    outcomes: dict[str, Outcome],
    tmp_path: Path,
    crash: int,
) -> None:
    """AC-6. expected_behavior_source: ORQLET-TEST-002 (stop after each step), ORQLET-SAFE-001 ("the
    manifest is written last so a re-run converges") and the interface decision (the registry
    first, the lock last): after `crash` writes the registry is the new one only when one write was
    done, the lock is still the old one, no temporary file is left and no other file moved. The
    copy file of `remove` and `attach` is among the files that did not move."""
    outcome = outcomes[edit.label]

    root, _ = interrupted(edit, templates, tmp_path, crash)

    partial = snapshot(root)
    assert not any(".orqlet-tmp-" in name for name in partial), "a temporary file was left"
    assert partial[LOCK] == outcome.before[LOCK]
    assert partial[REGISTRY] == (
        outcome.before[REGISTRY] if crash == 0 else outcome.expected[REGISTRY]
    )
    assert differing(outcome.before, partial) <= {REGISTRY}
    if edit.template == "with_entry":
        assert partial[COPY] == COPY_TEXT.encode()


def test_a_re_run_after_a_kill_before_any_write_gives_the_files_of_an_uninterrupted_run(
    edit: Edit, templates: dict[str, Path], outcomes: dict[str, Outcome], tmp_path: Path
) -> None:
    """AC-6. expected_behavior_source: ORQLET-SAFE-001 ("a re-run converges"), ORQLET-TEST-002
    (proves a re-run converges to the same state) and the interface decision. After 0 writes the
    project is as it was, so running the command again must apply and give the same files."""
    root, data = interrupted(edit, templates, tmp_path, 0)

    again = run_edit(edit, root, data, first_id=700)

    assert again.status == "applied", again.findings
    assert snapshot(root) == outcomes[edit.label].expected


def test_a_re_run_after_a_kill_between_the_registry_and_the_lock_converges_or_is_refused_unchanged(
    edit: Edit, templates: dict[str, Path], outcomes: dict[str, Outcome], tmp_path: Path
) -> None:
    """AC-6. expected_behavior_source: ORQLET-TEST-002 ("a re-run, or a rollback, converges to the
    same state"), ORQLET-SAFE-001 and AC-6 ("proves a re-run or a rollback converges"). The
    registry already holds the result and the lock is behind. Either the command applies and the
    files are those of an uninterrupted run, or it is refused (the builder refuses an id that is
    there, an id that is gone) and nothing changes: the way back is the rollback of the next test.
    See the module docstring: what the design wants here is a question for the person."""
    root, data = interrupted(edit, templates, tmp_path, 1)
    stopped = snapshot(root)

    again = run_edit(edit, root, data, first_id=700)

    if again.status == "applied":
        assert snapshot(root) == outcomes[edit.label].expected
    else:
        assert again.status == "refused", again.findings
        assert snapshot(root) == stopped


def test_upgrade_resume_settles_a_kill_between_the_registry_and_the_lock(
    edit: Edit, templates: dict[str, Path], outcomes: dict[str, Outcome], tmp_path: Path
) -> None:
    """AC-6. expected_behavior_source: ORQLET-TEST-002 ("a re-run, or a rollback, converges to the
    same state"), ADR-002 decision 5 ("`_seeded` returns `UP_TO_DATE` when the current text equals
    the new text and differs from the record", so the record advances and no proposal is made) and
    the interface decision (the lock is the last write and records the hash of the new registry:
    a different hash would leave a difference for `upgrade` to find). `doctor` names the
    interrupted change and the way out (`upgrade --resume`, ORQ-E170)."""
    outcome = outcomes[edit.label]
    root, data = interrupted(edit, templates, tmp_path, 1)
    assert "ORQ-E170" in {
        f.code for f in doctor(real_services(root, data)).findings if f.severity.value == "error"
    }

    resumed = upgrade(
        real_services(root, data, ids=SequentialIds(start=900)),
        UpgradeOptions(assume_yes=True, resume=True),
    )

    assert resumed.status == "applied", resumed.findings
    assert snapshot(root) == outcome.expected
    assert not any(name.startswith(".orqlet/proposals/") for name in snapshot(root))
    assert not [
        f for f in doctor(real_services(root, data)).findings if f.severity.value == "error"
    ]


def test_upgrade_resume_after_a_kill_before_any_write_leaves_the_state_and_the_edit_runs_again(
    edit: Edit, templates: dict[str, Path], outcomes: dict[str, Outcome], tmp_path: Path
) -> None:
    """AC-6. expected_behavior_source: ORQLET-TEST-002 and ORQLET-SAFE-001 (an interrupted change
    that wrote nothing leaves the files as they were): `upgrade --resume` has nothing to settle,
    and running the command again, which supersedes the open change, gives the files of an
    uninterrupted run."""
    outcome = outcomes[edit.label]
    root, data = interrupted(edit, templates, tmp_path, 0)

    resumed = upgrade(
        real_services(root, data, ids=SequentialIds(start=900)),
        UpgradeOptions(assume_yes=True, resume=True),
    )

    assert resumed.status in {"up-to-date", "applied"}, resumed.findings
    assert snapshot(root) == outcome.before
    again = run_edit(edit, root, data, first_id=1100)
    assert again.status == "applied", again.findings
    assert snapshot(root) == outcome.expected


@pytest.mark.parametrize("crash", range(WRITES))
def test_rollback_of_an_interrupted_edit_restores_the_state_before_and_the_edit_runs_again(
    edit: Edit,
    templates: dict[str, Path],
    outcomes: dict[str, Outcome],
    tmp_path: Path,
    crash: int,
) -> None:
    """AC-6. expected_behavior_source: ORQLET-TEST-002, the interface decision ("`rollback` of the
    interrupted or the finished change restores the state before") and the contract of `rollback`
    (a file is restored only if it still equals what the change applied; a file that the change did
    not reach is as it was). The interrupted change is the one that the journal still has open."""
    outcome = outcomes[edit.label]
    root, data = interrupted(edit, templates, tmp_path, crash)
    (change_id,) = open_changes(root, data)

    undone = rollback(
        real_services(root, data, ids=SequentialIds(start=900)),
        RollbackOptions(change_id, assume_yes=True),
    )

    assert undone.status == "applied", undone.findings
    assert snapshot(root) == outcome.before
    assert open_changes(root, data) == []
    again = run_edit(edit, root, data, first_id=1100)
    assert again.status == "applied", again.findings
    assert snapshot(root) == outcome.expected


def test_rollback_of_a_finished_edit_restores_the_state_before_and_the_edit_runs_again(
    edit: Edit, templates: dict[str, Path], outcomes: dict[str, Outcome], tmp_path: Path
) -> None:
    """AC-6. expected_behavior_source: the interface decision ("`rollback` of ... the finished
    change restores the state before") and plan P-4 file operation for the unit tests (the applied
    change is undone by rollback)."""
    outcome = outcomes[edit.label]
    root, data = clone(templates[edit.template], tmp_path)
    first = run_edit(edit, root, data)
    assert first.status == "applied", first.findings
    assert first.change_id is not None

    undone = rollback(
        real_services(root, data, ids=SequentialIds(start=900)),
        RollbackOptions(first.change_id, assume_yes=True),
    )

    assert undone.status == "applied", undone.findings
    assert snapshot(root) == outcome.before
    again = run_edit(edit, root, data, first_id=1100)
    assert again.status == "applied", again.findings
    assert snapshot(root) == outcome.expected
