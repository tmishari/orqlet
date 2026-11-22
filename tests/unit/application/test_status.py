"""The read-only status use case (task one-command-setup, phase P-4, AC-1 to AC-4).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-4 in
docs/design/one-command-setup/plan.yaml; ADR-001 decision 3, ADR-002 decisions 2 and 8 and ADR-004
decisions 1a, 5 and 7 are in docs/design/one-command-setup/design/; "the answers" are the person's
answers to the P-4 status questions (2026-11-22): A1 the value sets, A2 the `next` rule (first
match wins), A3 the user manifest and the client states, A4 the host steps; "the interface" is the
one that the Coder gave for P-4 (`read_status(services)`, `read_project_status(sources, project)`,
`StatusServices`, `GlobalSources`, `StatusReport.to_data()`).

HOW THESE TESTS WERE WRITTEN. The Tester of P-4 wrote them from the acceptance criteria, the
answers and the interface, before the implementation existed. They use the in-memory file system
and the fake Vcs of tests/fakes, the strict loader of the adapters (no fake loader exists), and a
small locator stub and project opener written here.

Choices:
- The installed workflow version is 0.5.0. A client's state comes from one manifest entry that
  only that client owns, unless a test says otherwise.
- A `not_run` entry is checked as "present" or "absent", never by its wording.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import get_args

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.common import RENDER_CLIENT_IDS, ClientId, RenderClientId
from orqlet.application.contracts.user_scope import (
    USER_MANIFEST_PATH,
    USER_MANIFEST_SCHEMA,
    UserHome,
)
from orqlet.application.ports.executables import ExecutableLookup, OnPath
from orqlet.application.ports.filesystem import FileKind, FileSystemError, ReadOnlyFiles
from orqlet.application.ports.vcs import Worktree
from orqlet.application.usecases.status import (
    GIT_SKIPPED_NOT_RUN,
    LOCK_NOT_RUN,
    MANIFEST_NOT_RUN,
    GlobalSources,
    GlobalState,
    HostStep,
    Location,
    NextStep,
    StatusReport,
    StatusServices,
    read_project_status,
    read_status,
)
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.representable import PATH_NOT_REPRESENTABLE
from orqlet.domain.versions import Version
from tests.fakes.faulty_fs import FaultyFileSystem
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs

pytestmark = pytest.mark.unit

INSTALLED = Version.parse("0.5.0")
HOME = "/home/person"
TOP = "/work/repo"
SHA = "a" * 64
MIB = 1_048_576
LOCK = CanonicalPath.parse(".orqlet/workflow.lock")
ALL_CONFIGURED: dict[str, str] = dict.fromkeys(RENDER_CLIENT_IDS, "0.5.0")
SENTINEL = "SENTINEL-not-for-output"


# --- stubs ----------------------------------------------------------------------------------


class StubLocator:
    def __init__(self, lookup: ExecutableLookup | None = None, *, unsafe_git: bool = False) -> None:
        self.lookup = lookup or ExecutableLookup(OnPath.SAME, unsafe_element_searched=False)
        self.unsafe_git = unsafe_git
        self.names: list[str] = []

    def searches_unsafe(self, name: str) -> bool:
        assert name == "git"
        return self.unsafe_git

    def locate(self, name: str) -> ExecutableLookup:
        self.names.append(name)
        return self.lookup


class ProjectOpener:
    def __init__(
        self, project: ReadOnlyFiles | None = None, *, error: FileSystemError | None = None
    ) -> None:
        self.project = project if project is not None else MemoryFileSystem()
        self.error = error
        self.opened: list[str] = []

    def __call__(self, top_level: str) -> ReadOnlyFiles:
        self.opened.append(top_level)
        if self.error is not None:
            raise self.error
        return self.project


# --- builders -------------------------------------------------------------------------------


def _entry(owners: tuple[str, ...], version: str, path: str) -> dict[str, object]:
    return {"path": path, "sha256": SHA, "workflow_version": version, "owners": list(owners)}


def _manifest(entries: list[dict[str, object]], **overrides: object) -> bytes:
    document: dict[str, object] = {
        "schema": USER_MANIFEST_SCHEMA,
        "change_id": "change-1",
        "created_at": "2026-11-22T10:00:00Z",
        "roots": {"claude": f"{HOME}/.claude"},
        "entries": entries,
    }
    document.update(overrides)
    return json.dumps(document).encode("utf-8")


def _manifest_for(versions: Mapping[str, str]) -> bytes:
    return _manifest(
        [
            _entry((client,), version, f"{client}/skills/orqlet/SKILL.md")
            for client, version in versions.items()
        ]
    )


def _user_data(manifest: bytes | None) -> MemoryFileSystem:
    files = MemoryFileSystem()
    files.make_dir(CanonicalPath.parse("user"))
    if manifest is not None:
        files.write_atomic(USER_MANIFEST_PATH, manifest)
    return files


def _sources(user_data: ReadOnlyFiles | None) -> GlobalSources:
    return GlobalSources(user_data=user_data, loader=StrictYamlLoader(), installed=INSTALLED)


def _configured() -> GlobalSources:
    return _sources(_user_data(_manifest_for(ALL_CONFIGURED)))


def _lock(version_line: str) -> bytes:
    return f"workflow_id: orqlet\n{version_line}\n".encode()


def _initialized(lock: bytes | None = _lock('workflow_version: "0.5.0"')) -> MemoryFileSystem:
    project = MemoryFileSystem()
    project.make_dir(CanonicalPath.parse(".orqlet"))
    if lock is not None:
        project.write_atomic(LOCK, lock)
    return project


def _worktree(top_level: str = TOP) -> Worktree:
    git_dir = f"{top_level}/.git"
    return Worktree(top_level=top_level, git_dir=git_dir, common_dir=git_dir)


def _linked() -> Worktree:
    return Worktree(
        top_level="/work/wt", git_dir=f"{TOP}/.git/worktrees/wt", common_dir=f"{TOP}/.git"
    )


def _services(
    *,
    worktree: Worktree | None = None,
    worktree_error: str | None = None,
    sources: GlobalSources | None = None,
    opener: ProjectOpener | None = None,
    locator: StubLocator | None = None,
    home: str = HOME,
) -> StatusServices:
    return StatusServices(
        sources=sources or _configured(),
        vcs=FakeVcs(worktree=worktree, worktree_error=worktree_error),
        open_project=opener or ProjectOpener(),
        executables=locator or StubLocator(),
        home=UserHome(path=home),
    )


def _tree(files: MemoryFileSystem) -> tuple[dict[str, bytes], tuple[str, ...]]:
    """Every file's bytes and every path, folders included, to prove that nothing was written."""
    paths: list[str] = []

    def walk(folder: CanonicalPath | None) -> None:
        for name in files.list_dir(folder):
            child = CanonicalPath.parse(name if folder is None else f"{folder}/{name}")
            paths.append(str(child))
            if files.kind(child) is FileKind.DIRECTORY:
                walk(child)

    walk(None)
    return files.snapshot(), tuple(paths)


def _all(state: GlobalState) -> dict[RenderClientId, GlobalState]:
    return dict.fromkeys(RENDER_CLIENT_IDS, state)


# --- the closed value sets (AC-1, A1, A4) ----------------------------------------------------


def test_location_is_a_closed_set() -> None:
    """AC-1, A1: the five locations, with the plan's names."""
    assert {location.value for location in Location} == {
        "not-a-repository",
        "repository",
        "initialized-project",
        "linked-worktree",
        "home-is-work-tree",
    }


def test_next_is_a_closed_set() -> None:
    """AC-1, ADR-001 decision 3, A1: the seven next steps."""
    assert {step.value for step in NextStep} == {
        "install-global",
        "init",
        "upgrade",
        "none",
        "refuse-newer-global",
        "refuse-linked-worktree",
        "refuse-home-is-work-tree",
    }


def test_global_state_and_host_step_are_closed_sets() -> None:
    """AC-2, A3, A4: four client states; P-4 emits one host step."""
    assert {state.value for state in GlobalState} == {"missing", "configured", "outdated", "newer"}
    assert {step.value for step in HostStep} == {"unsafe-path-element"}


# --- locations (AC-1) -----------------------------------------------------------------------


@dataclass(frozen=True)
class LocationCase:
    id: str
    worktree: Worktree | None
    home: str
    project: ReadOnlyFiles | None
    location: Location
    top_level: str | None
    opens_project: bool


LOCATION_CASES = [
    LocationCase("outside a repository", None, HOME, None, Location.NOT_A_REPOSITORY, None, False),
    LocationCase(
        "repository without .orqlet",
        _worktree(),
        HOME,
        MemoryFileSystem(),
        Location.REPOSITORY,
        TOP,
        True,
    ),
    LocationCase(
        "initialized project",
        _worktree(),
        HOME,
        _initialized(),
        Location.INITIALIZED_PROJECT,
        TOP,
        True,
    ),
    LocationCase(
        "initialized, .orqlet without a lock",
        _worktree(),
        HOME,
        _initialized(lock=None),
        Location.INITIALIZED_PROJECT,
        TOP,
        True,
    ),
    LocationCase(
        "linked worktree", _linked(), HOME, None, Location.LINKED_WORKTREE, "/work/wt", False
    ),
    LocationCase(
        "home is the top level",
        _worktree(HOME),
        HOME,
        None,
        Location.HOME_IS_WORK_TREE,
        HOME,
        False,
    ),
    LocationCase(
        "home below the top level",
        _worktree("/home"),
        HOME,
        None,
        Location.HOME_IS_WORK_TREE,
        "/home",
        False,
    ),
    LocationCase(
        "home below the top level, Windows separator",
        _worktree("C:\\Users"),
        "C:\\Users\\person",
        None,
        Location.HOME_IS_WORK_TREE,
        "C:\\Users",
        False,
    ),
    LocationCase(
        "a repository below home",
        _worktree(f"{HOME}/repo"),
        HOME,
        MemoryFileSystem(),
        Location.REPOSITORY,
        f"{HOME}/repo",
        True,
    ),
    LocationCase(
        "a sibling folder whose name starts like home",
        _worktree(HOME),
        f"{HOME}2",
        MemoryFileSystem(),
        Location.REPOSITORY,
        HOME,
        True,
    ),
]


@pytest.mark.parametrize("case", LOCATION_CASES, ids=[case.id for case in LOCATION_CASES])
def test_every_location(case: LocationCase) -> None:
    """AC-1, A1, ADR-001 decision 3; the interface: the location table with fakes."""
    opener = ProjectOpener(case.project)

    report = read_status(_services(worktree=case.worktree, opener=opener, home=case.home))

    assert report.location is case.location
    assert report.top_level == case.top_level
    assert report.top_level_reason is None
    assert report.not_run == ()
    assert opener.opened == ([case.top_level] if case.opens_project else [])


def test_a_vcs_failure_is_outside_a_repository_and_a_check_not_run() -> None:
    """AC-1, AC-6 (exit 5 comes from not_run); the interface: VcsError -> not-a-repository."""
    opener = ProjectOpener()

    report = read_status(_services(worktree_error="git cannot answer", opener=opener))

    assert report.location is Location.NOT_A_REPOSITORY
    assert report.top_level is None
    assert report.top_level_reason is None
    assert report.not_run
    assert opener.opened == []


def test_a_project_that_cannot_be_opened_is_a_repository_and_a_check_not_run() -> None:
    """The interface: open_project raising FileSystemError -> location repository, not_run."""
    opener = ProjectOpener(error=FileSystemError("cannot open"))

    report = read_status(_services(worktree=_worktree(), opener=opener))

    assert report.location is Location.REPOSITORY
    assert report.project is None
    assert report.not_run


def test_a_link_named_orqlet_is_initialized_but_gives_no_project_version() -> None:
    """AC-4, ADR-004 decision 5; the interface: anything at .orqlet initializes; links refused."""
    project = MemoryFileSystem()
    project.add_symlink(".orqlet")

    report = read_status(_services(worktree=_worktree(), opener=ProjectOpener(project)))

    assert report.location is Location.INITIALIZED_PROJECT
    assert report.project is None
    assert report.not_run


@pytest.mark.parametrize(
    "top_level",
    ["/work/re\u202epo", "/work/re\npo", "/work/re\u200bpo", "/" + "r" * 200],
    ids=["bidi", "control", "zero-width", "201-characters"],
)
def test_a_top_level_that_is_not_representable_is_null_with_the_reason(top_level: str) -> None:
    """AC-4, ADR-001 decision 3; the interface: null top level, reason, real path still opened."""
    opener = ProjectOpener(MemoryFileSystem())

    report = read_status(_services(worktree=_worktree(top_level), opener=opener))

    assert report.location is Location.REPOSITORY
    assert report.top_level is None
    assert report.top_level_reason == PATH_NOT_REPRESENTABLE
    assert opener.opened == [top_level]
    assert report.to_data()["top_level"] is None
    assert report.to_data()["top_level_reason"] == "path-not-representable"


def test_a_top_level_of_exactly_200_characters_is_printed() -> None:
    """AC-4, ADR-001 decision 3: 200 characters is still representable."""
    top_level = "/" + "r" * 199

    report = read_status(_services(worktree=_worktree(top_level)))

    assert report.top_level == top_level
    assert report.top_level_reason is None


# --- the next rule, first match wins (AC-1, AC-2, A2) ----------------------------------------


def _services_at(
    location: Location, *, sources: GlobalSources, project_lock: bytes | None
) -> StatusServices:
    """Services whose worktree, home and project put the use case at `location`."""
    if location is Location.NOT_A_REPOSITORY:
        return _services(sources=sources)
    if location is Location.LINKED_WORKTREE:
        return _services(sources=sources, worktree=_linked())
    if location is Location.HOME_IS_WORK_TREE:
        return _services(sources=sources, worktree=_worktree(HOME))
    project = MemoryFileSystem() if location is Location.REPOSITORY else _initialized(project_lock)
    return _services(sources=sources, worktree=_worktree(), opener=ProjectOpener(project))


def _with(**changes: str) -> dict[str, str]:
    return {**ALL_CONFIGURED, **changes}


NEWER = "0.6.0"
OLDER = "0.4.0"
NEXT_CASES = [
    # rule 1: any client newer
    ("1 newer beats linked worktree", _with(cursor=NEWER), Location.LINKED_WORKTREE, None,
     NextStep.REFUSE_NEWER_GLOBAL),
    ("1 newer beats home work tree", _with(codex=NEWER), Location.HOME_IS_WORK_TREE, None,
     NextStep.REFUSE_NEWER_GLOBAL),
    ("1 newer beats outdated", _with(codex=OLDER, cursor=NEWER), Location.REPOSITORY, None,
     NextStep.REFUSE_NEWER_GLOBAL),
    ("1 newer beats other clients missing", {"copilot": NEWER}, Location.NOT_A_REPOSITORY, None,
     NextStep.REFUSE_NEWER_GLOBAL),
    ("1 newer beats an up-to-date project", _with(**{"claude-code": NEWER}),
     Location.INITIALIZED_PROJECT, '"0.5.0"', NextStep.REFUSE_NEWER_GLOBAL),
    ("1 newer is numeric, not textual", _with(cursor="0.10.0"), Location.REPOSITORY, None,
     NextStep.REFUSE_NEWER_GLOBAL),
    # rule 2: linked worktree
    ("2 linked worktree", ALL_CONFIGURED, Location.LINKED_WORKTREE, None,
     NextStep.REFUSE_LINKED_WORKTREE),
    ("2 linked beats every client missing", {}, Location.LINKED_WORKTREE, None,
     NextStep.REFUSE_LINKED_WORKTREE),
    ("2 linked beats outdated", _with(codex=OLDER), Location.LINKED_WORKTREE, None,
     NextStep.REFUSE_LINKED_WORKTREE),
    # rule 3: home is a work tree
    ("3 home work tree", ALL_CONFIGURED, Location.HOME_IS_WORK_TREE, None,
     NextStep.REFUSE_HOME_IS_WORK_TREE),
    ("3 home beats every client missing", {}, Location.HOME_IS_WORK_TREE, None,
     NextStep.REFUSE_HOME_IS_WORK_TREE),
    # rule 4: every client missing, or any outdated
    ("4 every client missing in a repository", {}, Location.REPOSITORY, None,
     NextStep.INSTALL_GLOBAL),
    ("4 every client missing outside a repository", {}, Location.NOT_A_REPOSITORY, None,
     NextStep.INSTALL_GLOBAL),
    ("4 one outdated beats none", _with(codex=OLDER), Location.NOT_A_REPOSITORY, None,
     NextStep.INSTALL_GLOBAL),
    ("4 one outdated beats init", _with(copilot=OLDER), Location.REPOSITORY, None,
     NextStep.INSTALL_GLOBAL),
    ("4 one outdated beats upgrade", _with(cursor=OLDER), Location.INITIALIZED_PROJECT,
     '"0.4.0"', NextStep.INSTALL_GLOBAL),
    ("4 one outdated beats an up-to-date project", {"claude-code": OLDER},
     Location.INITIALIZED_PROJECT, '"0.5.0"', NextStep.INSTALL_GLOBAL),
    # rule 5: not a repository
    ("5 not a repository", ALL_CONFIGURED, Location.NOT_A_REPOSITORY, None, NextStep.NONE),
    ("5 some clients missing is not every client", {"claude-code": "0.5.0"},
     Location.NOT_A_REPOSITORY, None, NextStep.NONE),
    # rule 6: repository
    ("6 repository", ALL_CONFIGURED, Location.REPOSITORY, None, NextStep.INIT),
    ("6 repository with some clients missing", {"cursor": "0.5.0"}, Location.REPOSITORY, None,
     NextStep.INIT),
    # rule 7: initialized project
    ("7 no lock", ALL_CONFIGURED, Location.INITIALIZED_PROJECT, None, NextStep.UPGRADE),
    ("7 project below installed", ALL_CONFIGURED, Location.INITIALIZED_PROJECT, '"0.4.9"',
     NextStep.UPGRADE),
    ("7 project equal to installed", ALL_CONFIGURED, Location.INITIALIZED_PROJECT, '"0.5.0"',
     NextStep.NONE),
    ("7 project above installed", ALL_CONFIGURED, Location.INITIALIZED_PROJECT, '"0.6.0"',
     NextStep.NONE),
    ("7 project above installed, numerically", ALL_CONFIGURED, Location.INITIALIZED_PROJECT,
     '"0.10.0"', NextStep.NONE),
    ("7 project version not representable", ALL_CONFIGURED, Location.INITIALIZED_PROJECT,
     '"v0.5.0"', NextStep.UPGRADE),
]  # fmt: skip


@pytest.mark.parametrize(
    ("versions", "location", "project_version", "expected"),
    [case[1:] for case in NEXT_CASES],
    ids=[case[0] for case in NEXT_CASES],
)
def test_the_next_rule_first_match_wins(
    versions: dict[str, str],
    location: Location,
    project_version: str | None,
    expected: NextStep,
) -> None:
    """AC-1, AC-2, ADR-001 decision 3, ADR-002 decision 2, A2: the seven rules in their order."""
    lock = None if project_version is None else _lock(f"workflow_version: {project_version}")
    sources = _sources(_user_data(_manifest_for(versions)))

    report = read_status(_services_at(location, sources=sources, project_lock=lock))

    assert report.location is location
    assert report.next is expected


def test_a_missing_data_folder_gives_install_global() -> None:
    """AC-2, A2 rule 4, A3: a missing data folder is every client missing."""
    report = read_status(_services(worktree=_worktree(), sources=_sources(None)))

    assert report.next is NextStep.INSTALL_GLOBAL


# --- global state (AC-2, A3) -----------------------------------------------------------------


@pytest.mark.parametrize(
    "user_data",
    [None, MemoryFileSystem(), _user_data(None)],
    ids=["no data folder", "empty data folder", "no manifest"],
)
def test_no_manifest_is_every_client_missing_and_no_check_not_run(
    user_data: ReadOnlyFiles | None,
) -> None:
    """AC-2, ADR-002 decision 8, A3: missing folder or manifest -> missing, no not_run entry."""
    report = read_status(_services(sources=_sources(user_data)))

    assert dict(report.clients) == _all(GlobalState.MISSING)
    assert report.not_run == ()


def test_a_manifest_without_entries_is_every_client_missing() -> None:
    """A3: a client that owns no entry is missing."""
    report = read_status(_services(sources=_sources(_user_data(_manifest([])))))

    assert dict(report.clients) == _all(GlobalState.MISSING)
    assert report.not_run == ()


def test_each_client_takes_its_state_from_the_entries_it_owns() -> None:
    """AC-2, ADR-002 decision 2, A3: configured, outdated, newer and missing side by side."""
    manifest = _manifest_for({"claude-code": "0.5.0", "codex": OLDER, "cursor": NEWER})

    report = read_status(_services(sources=_sources(_user_data(manifest))))

    assert dict(report.clients) == {
        "claude-code": GlobalState.CONFIGURED,
        "codex": GlobalState.OUTDATED,
        "copilot": GlobalState.MISSING,
        "cursor": GlobalState.NEWER,
    }


def test_a_shared_entry_counts_for_every_owner() -> None:
    """ADR-002 decision 2, A3: the shared ~/.agents/skills render is owned by cursor and codex."""
    manifest = _manifest(
        [
            _entry(("codex", "cursor"), "0.5.0", "agents/skills/orqlet/SKILL.md"),
            _entry(("cursor", "codex"), "0.5.0", "agents/skills/orqlet/agents/openai.yaml"),
        ]
    )

    report = read_status(_services(sources=_sources(_user_data(manifest))))

    assert dict(report.clients) == {
        "claude-code": GlobalState.MISSING,
        "codex": GlobalState.CONFIGURED,
        "copilot": GlobalState.MISSING,
        "cursor": GlobalState.CONFIGURED,
    }


@pytest.mark.parametrize(
    ("versions", "expected"),
    [
        (("0.5.0", "0.5.0"), GlobalState.CONFIGURED),
        (("0.5.0", OLDER), GlobalState.OUTDATED),
        ((OLDER, NEWER), GlobalState.NEWER),
        (("0.5.0", NEWER), GlobalState.NEWER),
        (("0.10.0", "0.5.0"), GlobalState.NEWER),
        (("0.4.10", "0.5.0"), GlobalState.OUTDATED),
    ],
)
def test_a_client_with_several_entries(versions: tuple[str, str], expected: GlobalState) -> None:
    """A3: newer if any entry is above, else outdated if any is below, else configured."""
    manifest = _manifest(
        [
            _entry(("claude-code",), versions[0], "claude/skills/orqlet/SKILL.md"),
            _entry(("claude-code",), versions[1], "claude/agents/orqlet-tester.md"),
        ]
    )

    report = read_status(_services(sources=_sources(_user_data(manifest))))

    assert report.clients["claude-code"] is expected


VALID_ENTRY = _entry(("cursor",), "0.5.0", "cursor/agents/orqlet-tester.md")
BAD_MANIFESTS = {
    "not JSON": b"{" + SENTINEL.encode(),
    "not UTF-8": b"\xff\xfe" + SENTINEL.encode(),
    "a list": json.dumps([SENTINEL]).encode(),
    "duplicate key": b'{"schema": "orqlet.user-manifest/v1", "schema": "x"}',
    "another schema": _manifest([VALID_ENTRY], schema="orqlet.user-manifest/v2"),
    "an unknown field": _manifest([VALID_ENTRY], extra=SENTINEL),
    "a bad change id": _manifest([VALID_ENTRY], change_id="-" + SENTINEL),
    "an unknown owner": _manifest([_entry(("vim",), "0.5.0", "vim/x")]),
    "no owner": _manifest([_entry((), "0.5.0", "cursor/x")]),
    "a bad entry version": _manifest([_entry(("cursor",), "0.5", "cursor/x")]),
    "a bad hash": _manifest([{**VALID_ENTRY, "sha256": SENTINEL}]),
}


@pytest.mark.parametrize("content", list(BAD_MANIFESTS.values()), ids=list(BAD_MANIFESTS))
def test_a_manifest_that_does_not_parse_or_validate_is_every_client_missing(content: bytes) -> None:
    """AC-2, A3: a manifest that does not parse or validate -> missing, and a not_run entry."""
    report = read_status(_services(sources=_sources(_user_data(content))))

    assert dict(report.clients) == _all(GlobalState.MISSING)
    assert report.not_run
    assert all(SENTINEL not in sentence for sentence in report.not_run)


def test_a_manifest_that_is_a_link_is_every_client_missing() -> None:
    """AC-2, A3: a manifest that is a link is never read."""
    user_data = MemoryFileSystem()
    user_data.make_dir(CanonicalPath.parse("user"))
    user_data.add_symlink(str(USER_MANIFEST_PATH))

    report = read_status(_services(sources=_sources(user_data)))

    assert dict(report.clients) == _all(GlobalState.MISSING)
    assert report.not_run


def _padded(content: bytes, size: int) -> bytes:
    return content + b" " * (size - len(content))


def test_a_manifest_over_one_mebibyte_is_every_client_missing() -> None:
    """AC-2, A3: a manifest over 1 MiB -> missing, and a not_run entry."""
    content = _padded(_manifest_for(ALL_CONFIGURED), MIB + 1)

    report = read_status(_services(sources=_sources(_user_data(content))))

    assert dict(report.clients) == _all(GlobalState.MISSING)
    assert report.not_run


def test_a_manifest_of_exactly_one_mebibyte_is_read() -> None:
    """A3: only a manifest over 1 MiB is refused."""
    content = _padded(_manifest_for(ALL_CONFIGURED), MIB)

    report = read_status(_services(sources=_sources(_user_data(content))))

    assert dict(report.clients) == _all(GlobalState.CONFIGURED)
    assert report.not_run == ()


def test_a_newer_global_setup_refuses_even_where_init_would_follow() -> None:
    """AC-2, ADR-002 decision 2: a newer global version gives refuse-newer-global."""
    sources = _sources(_user_data(_manifest_for(_with(copilot=NEWER))))

    report = read_status(_services(worktree=_worktree(), sources=sources))

    assert report.clients["copilot"] is GlobalState.NEWER
    assert report.next is NextStep.REFUSE_NEWER_GLOBAL


# --- the PATH lookup and host steps (AC-3, A4) -----------------------------------------------


@pytest.mark.parametrize("on_path", list(OnPath))
def test_orqlet_on_path_comes_from_the_locator(on_path: OnPath) -> None:
    """AC-3, ADR-004 decision 7: same, different or absent, as the locator found it."""
    locator = StubLocator(ExecutableLookup(on_path, unsafe_element_searched=False))

    report = read_status(_services(locator=locator))

    assert report.orqlet_on_path is on_path
    assert report.host_steps == ()
    assert locator.names == ["orqlet"]


def test_an_unsafe_path_element_is_a_host_step() -> None:
    """AC-3, ADR-004 decision 7, A4: an unsafe element before orqlet is `unsafe-path-element`."""
    locator = StubLocator(ExecutableLookup(OnPath.DIFFERENT, unsafe_element_searched=True))

    report = read_status(_services(locator=locator))

    assert report.host_steps == (HostStep.UNSAFE_PATH_ELEMENT,)
    assert report.to_data()["global"] == {
        "clients": dict(_all(GlobalState.CONFIGURED)),
        "host_steps": ["unsafe-path-element"],
    }


# --- hostile project input (AC-4) ------------------------------------------------------------


@pytest.mark.parametrize(
    "version_line",
    [
        'workflow_version: "0.5"',
        'workflow_version: "v0.5.0"',
        'workflow_version: "0.5.0 "',
        'workflow_version: "0.5.0\\u202e"',
        "workflow_version: 5",
        "workflow_version: 0.5",
        "workflow_version: [0, 5, 0]",
        "workflow_version: null",
    ],
)
def test_a_lock_version_that_is_not_major_minor_patch_is_null(version_line: str) -> None:
    """AC-4, ADR-001 decision 3; the interface: a non-representable version is null, no not_run."""
    opener = ProjectOpener(_initialized(_lock(version_line)))

    report = read_status(_services(worktree=_worktree(), opener=opener))

    assert report.location is Location.INITIALIZED_PROJECT
    assert report.project is None
    assert report.not_run == ()
    assert report.next is NextStep.UPGRADE


def test_a_missing_lock_is_no_project_version_and_no_check_not_run() -> None:
    """The interface: a missing lock gives a null project version and no not_run entry."""
    report = read_status(_services(worktree=_worktree(), opener=ProjectOpener(_initialized(None))))

    assert report.project is None
    assert report.not_run == ()


def test_a_representable_lock_version_is_reported() -> None:
    """AC-4, ADR-001 decision 3: the project version, shown as it is."""
    project = _initialized(_lock('workflow_version: "0.4.9"'))

    report = read_status(_services(worktree=_worktree(), opener=ProjectOpener(project)))

    assert report.project == "0.4.9"
    assert report.installed == "0.5.0"


def _linked_lock() -> MemoryFileSystem:
    project = _initialized(None)
    project.add_symlink(str(LOCK))
    return project


HOSTILE_LOCKS: dict[str, Callable[[], MemoryFileSystem]] = {
    "over 1 MiB": lambda: _initialized(_padded(_lock('workflow_version: "0.5.0"'), MIB + 1)),
    "a link": _linked_lock,
    "not YAML": lambda: _initialized(f"workflow_version: [{SENTINEL}".encode()),
    "an anchor (strict loader)": lambda: _initialized(b"workflow_version: &v 0.5.0\n"),
    "a duplicate key (strict loader)": lambda: _initialized(
        b"workflow_version: 0.5.0\nworkflow_version: 0.4.0\n"
    ),
    "a custom tag (strict loader)": lambda: _initialized(
        f"workflow_version: !!python/name:{SENTINEL} 0.5.0\n".encode()
    ),
    "not a mapping": lambda: _initialized(f"- {SENTINEL}\n- 0.5.0\n".encode()),
}


@pytest.mark.parametrize("make_project", list(HOSTILE_LOCKS.values()), ids=list(HOSTILE_LOCKS))
def test_a_hostile_lock_gives_no_project_version_and_a_check_not_run(
    make_project: Callable[[], MemoryFileSystem],
) -> None:
    """AC-4, ADR-004 decision 5; the interface: refused, unparsable or not a mapping -> null."""
    opener = ProjectOpener(make_project())

    report = read_status(_services(worktree=_worktree(), opener=opener))

    assert report.location is Location.INITIALIZED_PROJECT
    assert report.project is None
    assert report.not_run
    assert all(SENTINEL not in sentence for sentence in report.not_run)
    assert all(TOP not in sentence for sentence in report.not_run)


def test_a_not_run_sentence_never_repeats_a_path() -> None:
    """The interface: not_run holds fixed sentences; it never repeats file content or a path."""
    top_level = f"/work/{SENTINEL}"
    opener = ProjectOpener(error=FileSystemError(f"cannot open {top_level}"))

    report = read_status(
        _services(worktree=_worktree(top_level), opener=opener, home=f"/home/{SENTINEL}")
    )

    assert report.not_run
    assert all(SENTINEL not in sentence for sentence in report.not_run)


# --- read only (AC-2, AC-5 at unit level, ADR-002 decision 8) --------------------------------


def test_the_use_case_writes_nothing() -> None:
    """AC-2, ADR-002 decision 8, K-11: status reads only; no file, folder or link appears."""
    user_data = _user_data(_manifest_for(_with(codex=OLDER)))
    project = _initialized(_lock('workflow_version: "0.4.0"'))
    before = (_tree(user_data), _tree(project))
    sources = _sources(FaultyFileSystem(user_data, crash_after_writes=0))
    opener = ProjectOpener(FaultyFileSystem(project, crash_after_writes=0))

    read_status(_services(worktree=_worktree(), sources=sources, opener=opener))
    read_project_status(sources, FaultyFileSystem(project, crash_after_writes=0))

    assert (_tree(user_data), _tree(project)) == before


# --- the data shape --------------------------------------------------------------------------


def _only_plain_values(value: object) -> bool:
    if isinstance(value, dict):
        return all(type(key) is str and _only_plain_values(item) for key, item in value.items())
    if isinstance(value, list):
        return all(_only_plain_values(item) for item in value)
    return value is None or type(value) is str


def test_to_data_has_the_documented_shape() -> None:
    """AC-1 to AC-4, ADR-001 decision 3; the interface: the `to_data()` keys and values."""
    report = read_status(_services(worktree=_worktree(), opener=ProjectOpener(_initialized())))

    data = report.to_data()

    assert data == {
        "global": {
            "clients": {
                "claude-code": "configured",
                "codex": "configured",
                "copilot": "configured",
                "cursor": "configured",
            },
            "host_steps": [],
        },
        "orqlet_on_path": "same",
        "location": "initialized-project",
        "top_level": TOP,
        "top_level_reason": None,
        "versions": {"installed": "0.5.0", "project": "0.5.0"},
        "next": "none",
    }
    assert json.loads(json.dumps(data)) == data
    assert _only_plain_values(data)


def test_to_data_lists_the_clients_in_code_point_order() -> None:
    """AC-8, the interface: every client id, in RENDER_CLIENT_IDS order."""
    manifest = _manifest_for({"cursor": NEWER, "claude-code": OLDER})

    data = read_status(_services(sources=_sources(_user_data(manifest)))).to_data()

    global_data = data["global"]
    assert isinstance(global_data, dict)
    assert list(global_data["clients"]) == ["claude-code", "codex", "copilot", "cursor"]
    assert list(global_data["clients"]) == list(RENDER_CLIENT_IDS)


def test_the_report_always_names_all_four_clients() -> None:
    """The interface: `clients` holds all four ids, always."""
    report = read_status(_services(sources=_sources(None)))

    assert set(report.clients) == set(RENDER_CLIENT_IDS)
    assert isinstance(report, StatusReport)


# --- hook mode -------------------------------------------------------------------------------


def test_hook_mode_reports_an_initialized_project_without_path_or_location_lookups() -> None:
    """ADR-001 decision 3, ADR-004 decision 5; the interface: read_project_status's fixed fields."""
    report = read_project_status(_configured(), _initialized(_lock('workflow_version: "0.5.0"')))

    assert report.location is Location.INITIALIZED_PROJECT
    assert report.top_level is None
    assert report.top_level_reason is None
    assert report.orqlet_on_path is None
    assert report.host_steps == ()
    assert report.project == "0.5.0"
    assert report.installed == "0.5.0"
    assert dict(report.clients) == _all(GlobalState.CONFIGURED)
    assert report.next is NextStep.NONE
    assert report.not_run == ()
    assert report.to_data()["orqlet_on_path"] is None


@pytest.mark.parametrize(
    ("sources", "lock_version", "expected"),
    [
        (_configured, '"0.5.0"', NextStep.NONE),
        (_configured, '"0.4.0"', NextStep.UPGRADE),
        (_configured, None, NextStep.UPGRADE),
        (lambda: _sources(None), '"0.5.0"', NextStep.INSTALL_GLOBAL),
        (lambda: _sources(_user_data(_manifest_for(_with(codex=OLDER)))), '"0.5.0"',
         NextStep.INSTALL_GLOBAL),
        (lambda: _sources(_user_data(_manifest_for(_with(codex=NEWER)))), '"0.4.0"',
         NextStep.REFUSE_NEWER_GLOBAL),
    ],
    ids=["current", "project below", "no lock", "no data folder", "outdated", "newer"],
)  # fmt: skip
def test_hook_mode_takes_next_from_the_same_rule(
    sources: Callable[[], GlobalSources],
    lock_version: str | None,
    expected: NextStep,
) -> None:
    """A2 rules 1, 4 and 7; the interface: hook mode computes next as command mode does."""
    lock = None if lock_version is None else _lock(f"workflow_version: {lock_version}")

    report = read_project_status(sources(), _initialized(lock))

    assert report.next is expected


@pytest.mark.parametrize("make_project", list(HOSTILE_LOCKS.values()), ids=list(HOSTILE_LOCKS))
def test_hook_mode_treats_a_hostile_lock_as_command_mode_does(
    make_project: Callable[[], MemoryFileSystem],
) -> None:
    """AC-4, ADR-004 decision 5: a large, linked or unparsable lock gives no project version."""
    report = read_project_status(_configured(), make_project())

    assert report.project is None
    assert report.not_run
    assert all(SENTINEL not in sentence for sentence in report.not_run)


def test_render_client_ids_has_four_values_and_client_id_keeps_three() -> None:
    """AC-8: `RenderClientId` has claude-code, codex, cursor and copilot; `ClientId` keeps three."""
    assert set(get_args(RenderClientId)) == {"claude-code", "codex", "cursor", "copilot"}
    assert set(RENDER_CLIENT_IDS) == set(get_args(RenderClientId))
    assert set(get_args(ClientId)) == {"claude-code", "codex", "cursor"}


# --- review round 3 of P-4 (Q-73 to Q-75) ---------------------------------------------------


def test_git_is_not_run_when_path_searches_an_unsafe_element_first() -> None:
    """Q-73: a `git` in an untrusted work tree must not run; the location is a check not run."""
    services = _services(
        worktree_error="git must not be asked", locator=StubLocator(unsafe_git=True)
    )

    report = read_status(services)

    assert report.location is Location.NOT_A_REPOSITORY
    assert report.top_level is None
    assert report.not_run == (GIT_SKIPPED_NOT_RUN,)


def test_a_data_directory_that_could_not_be_checked_is_a_check_not_run() -> None:
    """Q-74: only a data directory that does not exist means every client is missing."""
    sources = GlobalSources(
        user_data=None, loader=StrictYamlLoader(), installed=INSTALLED, user_data_unreadable=True
    )

    report = read_status(_services(worktree=_worktree(), sources=sources))

    assert set(report.clients.values()) == {GlobalState.MISSING}
    assert MANIFEST_NOT_RUN in report.not_run


def test_a_regular_file_at_the_project_folder_is_a_check_not_run() -> None:
    """Q-75: a file named .orqlet is not a project whose lock can be read."""
    project = MemoryFileSystem()
    project.write_atomic(CanonicalPath.parse(".orqlet"), b"not a folder\n")

    report = read_status(_services(worktree=_worktree(), opener=ProjectOpener(project)))

    assert report.location is Location.INITIALIZED_PROJECT
    assert report.project is None
    assert report.not_run == (LOCK_NOT_RUN,)
