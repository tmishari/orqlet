"""The composite user-scope file system against real temporary folders (one-command-setup, P-6).

Acceptance criteria AC-1 (prefixes, writable sub-paths and links), AC-7 (folder boundaries of
`remove_empty_dir`), the adapter part of AC-3 (a missing root reads as empty, the planning
composite writes nothing) and the write part of AC-13 (a client change without a hook entry).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-6 in
docs/design/one-command-setup/plan.yaml, BC-n a behaviour of design/component.md, "ADR-002
decision n" a decision of design/adr-002-user-scope-root-journal-and-manifest.md, and "the
interface" the interface of `UserScopeFileSystem` that the Coder of P-6 gave the Tester (the error
classes and the read and listing rules that the ADR leaves to the adapter).

These tests were written first, by the Tester of phase P-6, before the adapter existed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orqlet.adapters.fs.journal import FsBackupStore, FsChangeJournal
from orqlet.adapters.fs.user_scope import UserScopeFileSystem
from orqlet.application.ports.filesystem import (
    FileKind,
    FileSystemError,
    LinkRefused,
    PathNotFound,
)
from orqlet.application.ports.user_scope import (
    USER_PREFIXES,
    PathNotWritable,
    ReadOnlyUserScope,
    UserRootRefused,
)
from orqlet.application.usecases.apply_plan import apply_plan
from orqlet.domain.changeplan import ChangePlan, PlannedWrite
from orqlet.domain.digest import sha256_hex
from orqlet.domain.errors import OrqletError
from orqlet.domain.paths import CanonicalPath
from tests.fakes.clock import FixedClock
from tests.fakes.lock import NoLock

pytestmark = pytest.mark.integration


def p(text: str) -> CanonicalPath:
    return CanonicalPath.parse(text)


def make_link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot create symbolic links")


def snapshot(base: Path) -> dict[str, int]:
    """Every path below `base` with its mode, links not followed."""
    found: dict[str, int] = {}
    for folder, dirs, files in os.walk(base):
        for name in (*dirs, *files):
            path = Path(folder) / name
            found[path.relative_to(base).as_posix()] = os.lstat(path).st_mode
    return found


@pytest.fixture
def roots(tmp_path: Path) -> dict[str, Path]:
    made: dict[str, Path] = {}
    for prefix in USER_PREFIXES:
        folder = tmp_path / "roots" / prefix
        folder.mkdir(parents=True)
        made[prefix] = folder.resolve()
    return made


def on_disk(roots: dict[str, Path], path: str) -> Path:
    prefix, rest = path.split("/", 1)
    return roots[prefix] / rest


WRITABLE = [
    "claude/skills/orqlet/SKILL.md",
    "claude/skills/orqlet-plan/SKILL.md",
    "claude/skills/ponytail/SKILL.md",
    "claude/skills/ponytail-review/references/notes.md",
    "claude/agents/orqlet.md",
    "claude/agents/orqlet-tester.md",
    "claude/agents/ponytail-reviewer.md",
    "claude/rules/orqlet-foundation.md",
    "claude/settings.json",
    "cursor/agents/orqlet-tester.md",
    "cursor/hooks.json",
    "codex/agents/orqlet-tester.toml",
    "codex/agents/orqlet.toml",
    "codex/AGENTS.md",
    "codex/hooks.json",
    "agents/skills/orqlet/SKILL.md",
    "agents/skills/orqlet/agents/openai.yaml",
    "agents/skills/ponytail-lazy/SKILL.md",
    "copilot/skills/orqlet-design/SKILL.md",
    "copilot/hooks/orqlet.json",
    "data/manifest.json",
    "data/cursor-user-rules.md",
]

REFUSED = [
    "claude/skills/other/SKILL.md",
    "claude/skills/orqletx/SKILL.md",
    "claude/skills/SKILL.md",
    "claude/agents/notes.md",
    "claude/agents/orqlet.toml",
    "claude/agents/sub/orqlet.md",
    "claude/rules/other.md",
    "claude/CLAUDE.md",
    "claude/.credentials.json",
    "claude/settings.local.json",
    "cursor/agents/notes.md",
    "cursor/agents/orqlet.toml",
    "cursor/mcp.json",
    "cursor/skills/orqlet/SKILL.md",
    "codex/agents/orqlet",
    "codex/agents/notes.toml",
    "codex/config.toml",
    "codex/skills/orqlet/SKILL.md",
    "agents/skills/other/SKILL.md",
    "agents/agents/orqlet.md",
    "copilot/hooks/other.json",
    "copilot/agents/orqlet.md",
    "data/journal/c-1.json",
    "data/backups/c-1/claude/settings.json",
    "data/apply.lock",
    "data/other.txt",
    "home/notes.txt",
    "projects/p1/upgrade/c-1.json",
]


# --- AC-1: prefixes and writable sub-paths -------------------------------------------------------


def test_the_error_classes_are_file_system_errors_that_exit_3() -> None:
    """AC-1, AC-4. expected_behavior_source: the interface (PathNotWritable and
    ReadOnlyUserScope are FileSystemError, UserRootRefused an OrqletError); section 5 failures
    ("refused write; exit 3")."""
    assert issubclass(PathNotWritable, FileSystemError)
    assert issubclass(ReadOnlyUserScope, FileSystemError)
    assert issubclass(UserRootRefused, OrqletError)


def test_the_six_prefixes_are_listed_at_the_top(roots: dict[str, Path]) -> None:
    """AC-1. expected_behavior_source: AC-1; ADR-002 decision 1 (the six prefixes); the interface
    (`list_dir(None)` gives the sorted prefixes)."""
    fs = UserScopeFileSystem(roots, writable=True)

    assert fs.list_dir(None) == ("agents", "claude", "codex", "copilot", "cursor", "data")


@pytest.mark.parametrize("path", WRITABLE)
def test_every_writable_sub_path_is_written_inside_its_own_root(
    roots: dict[str, Path], path: str
) -> None:
    """AC-1. expected_behavior_source: AC-1; ADR-002 decision 1 (the table of writable sub-paths,
    `<owned>` is `orqlet`, `orqlet-*` or `ponytail*`)."""
    fs = UserScopeFileSystem(roots, writable=True)

    fs.write_atomic(p(path), b"content")

    assert on_disk(roots, path).read_bytes() == b"content"
    assert fs.kind(p(path)) is FileKind.FILE
    assert fs.read_bytes(p(path)) == b"content"
    assert fs.read_prefix(p(path), 3) == b"con"
    fs.delete(p(path))
    assert not on_disk(roots, path).exists()


@pytest.mark.parametrize("path", REFUSED)
def test_a_path_outside_the_writable_sub_paths_is_refused_and_nothing_is_written(
    roots: dict[str, Path], tmp_path: Path, path: str
) -> None:
    """AC-1. expected_behavior_source: AC-1; ADR-002 decision 1 ("Any other path ... is
    refused"); ORQLET-SAFE-001 (each root limited to its listed sub-paths); the interface (an
    unknown prefix raises PathNotWritable)."""
    fs = UserScopeFileSystem(roots, writable=True)
    before = snapshot(tmp_path)

    with pytest.raises(PathNotWritable):
        fs.write_atomic(p(path), b"x")
    with pytest.raises(PathNotWritable):
        fs.make_dir(p(path))
    with pytest.raises(PathNotWritable):
        fs.delete(p(path))

    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("prefix", USER_PREFIXES)
def test_a_bare_prefix_is_not_writable(roots: dict[str, Path], prefix: str) -> None:
    """AC-1. expected_behavior_source: AC-1; the interface (a path that is only a prefix raises
    PathNotWritable for writes)."""
    fs = UserScopeFileSystem(roots, writable=True)

    with pytest.raises(PathNotWritable):
        fs.write_atomic(p(prefix), b"x")
    with pytest.raises(PathNotWritable):
        fs.delete(p(prefix))
    assert roots[prefix].is_dir()


@pytest.mark.parametrize(
    "path", ["claude/.credentials.json", "claude/CLAUDE.md", "codex/config.toml", "cursor/mcp.json"]
)
def test_other_files_in_a_client_folder_are_neither_read_nor_deleted(
    roots: dict[str, Path], path: str
) -> None:
    """AC-1. expected_behavior_source: AC-1; ADR-002 decision 1; the interface (read_bytes,
    read_prefix and kind only on a writable sub-path; no reading of `claude/.credentials.json`)."""
    target = on_disk(roots, path)
    target.write_bytes(b"person's secret")
    fs = UserScopeFileSystem(roots, writable=True)

    with pytest.raises(PathNotWritable):
        fs.read_bytes(p(path))
    with pytest.raises(PathNotWritable):
        fs.read_prefix(p(path), 4)
    with pytest.raises(PathNotWritable):
        fs.kind(p(path))
    with pytest.raises(PathNotWritable):
        fs.delete(p(path))
    assert target.read_bytes() == b"person's secret"


def test_the_folders_that_lead_to_a_writable_sub_path_can_be_listed(
    roots: dict[str, Path],
) -> None:
    """AC-1. expected_behavior_source: AC-1; the interface (kind and list_dir on a root, on the
    folders at or above the first segment of a writable sub-path, and on writable sub-paths)."""
    (roots["claude"] / "skills" / "orqlet").mkdir(parents=True)
    (roots["claude"] / "skills" / "orqlet" / "SKILL.md").write_bytes(b"x")
    (roots["claude"] / "skills" / "other").mkdir()
    (roots["claude"] / "agents").mkdir()
    (roots["copilot"] / "hooks").mkdir()
    fs = UserScopeFileSystem(roots, writable=True)

    assert fs.kind(p("claude")) is FileKind.DIRECTORY
    assert fs.list_dir(p("claude")) == ("agents", "skills")
    assert fs.kind(p("claude/skills")) is FileKind.DIRECTORY
    assert fs.list_dir(p("claude/skills")) == ("orqlet", "other")
    assert fs.list_dir(p("claude/skills/orqlet")) == ("SKILL.md",)
    assert fs.kind(p("claude/agents")) is FileKind.DIRECTORY
    assert fs.kind(p("claude/rules")) is None
    assert fs.list_dir(p("copilot/hooks")) == ()
    assert fs.kind(p("claude/settings.json")) is None


def test_folders_that_lead_nowhere_writable_cannot_be_listed(roots: dict[str, Path]) -> None:
    """AC-1. expected_behavior_source: AC-1; the interface (kind and list_dir elsewhere raise
    PathNotWritable; an unknown prefix raises PathNotWritable)."""
    (roots["claude"] / "projects").mkdir()
    (roots["claude"] / "skills" / "other").mkdir(parents=True)
    fs = UserScopeFileSystem(roots, writable=True)

    with pytest.raises(PathNotWritable):
        fs.list_dir(p("claude/projects"))
    with pytest.raises(PathNotWritable):
        fs.kind(p("claude/projects"))
    with pytest.raises(PathNotWritable):
        fs.list_dir(p("claude/skills/other"))
    with pytest.raises(PathNotWritable):
        fs.kind(p("nope"))
    with pytest.raises(PathNotWritable):
        fs.list_dir(p("nope"))


# --- AC-1: links ---------------------------------------------------------------------------------


def test_a_link_below_a_root_is_refused(roots: dict[str, Path], tmp_path: Path) -> None:
    """AC-1. expected_behavior_source: AC-1; ADR-002 decision 1 ("every link, is refused");
    BC-6 (a link below a root); the interface (delegated to LocalFileSystem, LinkRefused)."""
    outside = tmp_path / "outside"
    outside.mkdir()
    make_link(roots["claude"] / "skills", outside)
    fs = UserScopeFileSystem(roots, writable=True)

    with pytest.raises(LinkRefused):
        fs.write_atomic(p("claude/skills/orqlet/SKILL.md"), b"x")
    with pytest.raises(LinkRefused):
        fs.read_bytes(p("claude/skills/orqlet/SKILL.md"))
    with pytest.raises(LinkRefused):
        fs.make_dir(p("claude/skills/orqlet"))
    assert list(outside.iterdir()) == []


def test_an_owned_skill_folder_that_is_a_link_is_refused(
    roots: dict[str, Path], tmp_path: Path
) -> None:
    """AC-1. expected_behavior_source: AC-1; ADR-002 decision 1; BC-6."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (roots["agents"] / "skills").mkdir()
    make_link(roots["agents"] / "skills" / "orqlet", outside)
    fs = UserScopeFileSystem(roots, writable=True)

    with pytest.raises(LinkRefused):
        fs.write_atomic(p("agents/skills/orqlet/SKILL.md"), b"x")
    assert list(outside.iterdir()) == []


def test_a_target_that_is_a_link_is_refused(roots: dict[str, Path], tmp_path: Path) -> None:
    """AC-1. expected_behavior_source: AC-1; ADR-002 decision 1; the FileSystem port (a link as
    the last component is reported as SYMLINK)."""
    outside = tmp_path / "settings.json"
    outside.write_bytes(b"{}")
    make_link(roots["claude"] / "settings.json", outside)
    fs = UserScopeFileSystem(roots, writable=True)

    assert fs.kind(p("claude/settings.json")) is FileKind.SYMLINK
    with pytest.raises(LinkRefused):
        fs.read_bytes(p("claude/settings.json"))
    with pytest.raises(LinkRefused):
        fs.write_atomic(p("claude/settings.json"), b'{"a": 1}')
    with pytest.raises(LinkRefused):
        fs.delete(p("claude/settings.json"))
    assert outside.read_bytes() == b"{}"


# --- AC-3 (adapter part): a missing root and the read-only composite ----------------------------


def test_a_missing_root_reads_as_empty(roots: dict[str, Path]) -> None:
    """AC-3. expected_behavior_source: AC-3; ADR-002 decision 1a ("the composite file system
    reads a missing root ... as empty"); the interface (a None root)."""
    with_missing: dict[str, Path | None] = {**roots, "agents": None}
    fs = UserScopeFileSystem(with_missing, writable=False)

    assert fs.kind(p("agents")) is None
    assert fs.kind(p("agents/skills/orqlet/SKILL.md")) is None
    assert fs.list_dir(p("agents")) == ()
    with pytest.raises(PathNotFound):
        fs.read_bytes(p("agents/skills/orqlet/SKILL.md"))


def test_the_read_only_composite_writes_nothing(roots: dict[str, Path], tmp_path: Path) -> None:
    """AC-3. expected_behavior_source: AC-3; ADR-002 decision 1a ("Nothing is created or changed
    before consent"); the interface (writable=False raises ReadOnlyUserScope before anything is
    touched)."""
    (roots["claude"] / "settings.json").write_bytes(b"{}")
    (roots["claude"] / "skills" / "orqlet").mkdir(parents=True)
    fs = UserScopeFileSystem(roots, writable=False)
    before = snapshot(tmp_path)

    with pytest.raises(ReadOnlyUserScope):
        fs.write_atomic(p("claude/settings.json"), b'{"a": 1}')
    with pytest.raises(ReadOnlyUserScope):
        fs.write_atomic(p("agents/skills/orqlet/SKILL.md"), b"x")
    with pytest.raises(ReadOnlyUserScope):
        fs.delete(p("claude/settings.json"))
    with pytest.raises(ReadOnlyUserScope):
        fs.make_dir(p("copilot/skills/orqlet"))
    with pytest.raises(ReadOnlyUserScope):
        fs.remove_empty_dir(p("claude/skills/orqlet"))

    assert snapshot(tmp_path) == before
    assert fs.read_bytes(p("claude/settings.json")) == b"{}"


# --- AC-7: folder boundaries ---------------------------------------------------------------------


BOUNDARIES = [
    "claude",
    "cursor",
    "codex",
    "agents",
    "copilot",
    "data",
    "claude/skills",
    "claude/agents",
    "claude/rules",
    "cursor/agents",
    "codex/agents",
    "agents/skills",
    "copilot/skills",
    "copilot/hooks",
]


@pytest.mark.parametrize("folder", BOUNDARIES)
def test_an_empty_root_or_boundary_folder_is_never_removed(
    roots: dict[str, Path], folder: str
) -> None:
    """AC-7. expected_behavior_source: AC-7; ADR-002 decision 1, "Folder boundaries" (a no-op for
    a root and for any folder at or above a writable sub-path's first segment); BC-33."""
    target = roots[folder] if "/" not in folder else on_disk(roots, folder)
    target.mkdir(parents=True, exist_ok=True)
    assert list(target.iterdir()) == []
    fs = UserScopeFileSystem(roots, writable=True)

    fs.remove_empty_dir(p(folder))

    assert target.is_dir()


@pytest.mark.parametrize(
    "folder",
    [
        "claude/skills/orqlet",
        "claude/skills/orqlet-plan/references",
        "agents/skills/ponytail/agents",
        "copilot/skills/orqlet",
    ],
)
def test_an_empty_owned_skill_folder_is_removed(roots: dict[str, Path], folder: str) -> None:
    """AC-7. expected_behavior_source: AC-7; ADR-002 decision 1, "Folder boundaries" ("it removes
    an owned skill folder"); BC-33."""
    target = on_disk(roots, folder)
    target.mkdir(parents=True)
    fs = UserScopeFileSystem(roots, writable=True)

    fs.remove_empty_dir(p(folder))

    assert not target.exists()
    assert target.parent.is_dir()


@pytest.mark.parametrize("folder", ["claude/projects", "claude/skills/other", "cursor/rules"])
def test_removing_a_folder_outside_the_allow_list_is_refused(
    roots: dict[str, Path], folder: str
) -> None:
    """AC-7. expected_behavior_source: AC-7; ADR-002 decision 1; the interface (outside the
    allow-list remove_empty_dir raises PathNotWritable)."""
    target = on_disk(roots, folder)
    target.mkdir(parents=True)
    fs = UserScopeFileSystem(roots, writable=True)

    with pytest.raises(PathNotWritable):
        fs.remove_empty_dir(p(folder))
    assert target.is_dir()


def test_deleting_the_last_owned_skill_file_stops_at_the_skills_folder(
    roots: dict[str, Path], tmp_path: Path
) -> None:
    """AC-7. expected_behavior_source: AC-7; BC-33 ("removes its folder but never removes a root,
    ~/.claude/skills"); ADR-002 decision 1 (the empty-folder walk of apply_plan stops there)."""
    skill = roots["claude"] / "skills" / "orqlet" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"old")
    data_directory = tmp_path / "data-directory"
    data_directory.mkdir()
    journal = FsChangeJournal.for_user(data_directory)
    plan = ChangePlan(
        items=(),
        writes=(
            PlannedWrite(
                p("claude/skills/orqlet/SKILL.md"), "delete", sha256_hex(b"old"), None, None
            ),
        ),
        recorded_after=(),
    )

    apply_plan(
        UserScopeFileSystem(roots, writable=True),
        journal,
        FsBackupStore.for_user(data_directory),
        plan,
        lock=NoLock(),
        change_id="c-1",
        command="uninstall",
        clock=FixedClock(),
    )

    assert not (roots["claude"] / "skills" / "orqlet").exists()
    assert (roots["claude"] / "skills").is_dir()
    assert roots["claude"].is_dir()


# --- AC-13 (write part): a client with skills, agents and guidance and no hook entry ------------


def test_a_change_without_a_hook_entry_is_written_like_any_other(
    roots: dict[str, Path], tmp_path: Path
) -> None:
    """AC-13. expected_behavior_source: AC-13; Q-82 ("P-6 accepts a change with no hook entry for
    a client"); BC-38."""
    files = {
        "claude/skills/orqlet/SKILL.md": b"skill",
        "claude/agents/orqlet-tester.md": b"agent",
        "claude/rules/orqlet-foundation.md": b"foundation",
    }
    manifest = b'{"entries": []}\n'
    writes = tuple(
        PlannedWrite(p(path), "create", None, sha256_hex(content), content)
        for path, content in files.items()
    )
    last = PlannedWrite(
        p("data/manifest.json"), "create", None, sha256_hex(manifest), manifest, last=True
    )
    data_directory = tmp_path / "data-directory"
    data_directory.mkdir()
    journal = FsChangeJournal.for_user(data_directory)

    result = apply_plan(
        UserScopeFileSystem(roots, writable=True),
        journal,
        FsBackupStore.for_user(data_directory),
        ChangePlan(items=(), writes=(*writes, last), recorded_after=()),
        lock=NoLock(),
        change_id="c-1",
        command="install",
        clock=FixedClock(),
    )

    for path, content in files.items():
        assert on_disk(roots, path).read_bytes() == content
    assert (roots["data"] / "manifest.json").read_bytes() == manifest
    assert not (roots["claude"] / "settings.json").exists()
    assert set(result.written) == {*files, "data/manifest.json"}
    record = journal.read("c-1")
    assert record is not None
    assert record.status == "complete"
    assert all(entry.done for entry in record.entries)
