"""The user namespace of the change journal and the backup store (task one-command-setup, P-6).

Acceptance criteria AC-8 (one path under two prefixes), AC-9 (private modes, owner sets, JSON
entry keys and hashes, compatibility of a project journal, no reading of `projects/<id>`), AC-10
(the project journal is written as before) and the journal part of AC-13 (a client change without
a hook entry).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-6 in
docs/design/one-command-setup/plan.yaml, BC-n a behaviour of design/component.md, "ADR-002
decision n" a decision of design/adr-002-user-scope-root-journal-and-manifest.md, A-27 the AS-IS
fact on the journal layout, and "the interface" the `for_user` constructors and the `JournalEntry`
and `JournalRecord` fields that the Coder of P-6 gave the Tester.

The project journal bytes below are written literally, in the form that the encoder of the base
commit writes (`json.dumps(document, indent=2, sort_keys=True)` and a newline). These tests were
written first, by the Tester of phase P-6, before the user namespace existed.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

from orqlet.adapters.fs.journal import FsBackupStore, FsChangeJournal
from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.adapters.fs.user_scope import UserScopeFileSystem
from orqlet.application.ports.change_journal import JournalEntry, JournalRecord
from orqlet.application.ports.user_scope import USER_PREFIXES
from orqlet.application.usecases.apply_plan import apply_plan
from orqlet.domain.changeplan import ChangePlan, PlannedWrite
from orqlet.domain.digest import sha256_hex
from orqlet.domain.paths import CanonicalPath
from tests.fakes.clock import FixedClock
from tests.fakes.lock import NoLock

pytestmark = pytest.mark.integration

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")

A = "a" * 64
B = "b" * 64
C = "c" * 64
CREATED = "2026-10-20T12:00:00+00:00"

PROJECT_JOURNAL = """\
{
  "change_id": "c-old",
  "command": "upgrade",
  "created_at": "2026-10-20T12:00:00+00:00",
  "entries": [
    {
      "after_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "before_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "done": true,
      "is_proposal": false,
      "kind": "update",
      "path": "AGENTS.md"
    },
    {
      "after_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
      "before_sha256": null,
      "done": false,
      "is_proposal": true,
      "kind": "create",
      "path": ".orqlet/proposals/x.diff"
    }
  ],
  "plan_digest": "dddd",
  "status": "open"
}
"""

PROJECT_RECORD = JournalRecord(
    change_id="c-old",
    command="upgrade",
    plan_digest="dddd",
    created_at=CREATED,
    entries=(
        JournalEntry("AGENTS.md", "update", A, B, is_proposal=False, done=True),
        JournalEntry(".orqlet/proposals/x.diff", "create", None, C, is_proposal=True, done=False),
    ),
    status="open",
)


def p(text: str) -> CanonicalPath:
    return CanonicalPath.parse(text)


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "data"
    folder.mkdir()
    return folder.resolve()


@pytest.fixture
def roots(tmp_path: Path) -> dict[str, Path]:
    made: dict[str, Path] = {}
    for prefix in USER_PREFIXES:
        folder = tmp_path / "roots" / prefix
        folder.mkdir(parents=True)
        made[prefix] = folder.resolve()
    return made


def user_record(change_id: str = "c-1", *entries: JournalEntry) -> JournalRecord:
    return JournalRecord(
        change_id=change_id,
        command="install",
        plan_digest="eeee",
        created_at=CREATED,
        entries=entries or (JournalEntry("claude/skills/orqlet/SKILL.md", "create", None, A),),
    )


def write_project_journal(data_dir: Path, change_id: str, text: str) -> Path:
    target = data_dir / "projects" / "p1" / "upgrade" / f"{change_id}.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(text.encode("utf-8"))
    return target


# --- AC-8: one relative path under two prefixes --------------------------------------------------


def test_the_same_path_under_two_prefixes_gives_two_entries_and_two_backups(
    roots: dict[str, Path], data_dir: Path
) -> None:
    """AC-8. expected_behavior_source: AC-8; BC-32 ("distinct journal entries and backups");
    ADR-002 decision 1 (entries and backups keyed by the prefixed path)."""
    olds = {"claude": b"claude old", "cursor": b"cursor old"}
    news = {"claude": b"claude new", "cursor": b"cursor new"}
    for prefix, content in olds.items():
        (roots[prefix] / "agents").mkdir()
        (roots[prefix] / "agents" / "orqlet.md").write_bytes(content)
    writes = tuple(
        PlannedWrite(
            p(f"{prefix}/agents/orqlet.md"),
            "update",
            sha256_hex(olds[prefix]),
            sha256_hex(news[prefix]),
            news[prefix],
        )
        for prefix in ("claude", "cursor")
    )
    journal = FsChangeJournal.for_user(data_dir)
    backups = FsBackupStore.for_user(data_dir)

    apply_plan(
        UserScopeFileSystem(roots, writable=True),
        journal,
        backups,
        ChangePlan(items=(), writes=writes, recorded_after=()),
        lock=NoLock(),
        change_id="c-1",
        command="install",
        clock=FixedClock(),
    )

    record = journal.read("c-1")
    assert record is not None
    assert [(e.path, e.before_sha256) for e in record.entries] == [
        ("claude/agents/orqlet.md", sha256_hex(b"claude old")),
        ("cursor/agents/orqlet.md", sha256_hex(b"cursor old")),
    ]
    assert backups.load("c-1", p("claude/agents/orqlet.md")) == b"claude old"
    assert backups.load("c-1", p("cursor/agents/orqlet.md")) == b"cursor old"
    stored = data_dir / "user" / "backups" / "c-1"
    assert (stored / "claude" / "agents" / "orqlet.md").read_bytes() == b"claude old"
    assert (stored / "cursor" / "agents" / "orqlet.md").read_bytes() == b"cursor old"
    assert (roots["claude"] / "agents" / "orqlet.md").read_bytes() == b"claude new"
    assert (roots["cursor"] / "agents" / "orqlet.md").read_bytes() == b"cursor new"


# --- AC-9: layout and private modes --------------------------------------------------------------


def test_the_user_journal_lives_below_user_journal(data_dir: Path) -> None:
    """AC-9. expected_behavior_source: ADR-002 decision 4 (`user/journal/<change-id>.json` and
    `user/backups/<change-id>/<prefixed path>`); the interface (for_user)."""
    FsChangeJournal.for_user(data_dir).start(user_record())
    FsBackupStore.for_user(data_dir).save("c-1", p("claude/settings.json"), b"{}")

    assert (data_dir / "user" / "journal" / "c-1.json").is_file()
    assert (
        data_dir / "user" / "backups" / "c-1" / "claude" / "settings.json"
    ).read_bytes() == b"{}"
    assert not (data_dir / "projects").exists()


@posix_only
def test_user_journal_files_are_0600_and_its_folders_0700(data_dir: Path) -> None:
    """AC-9. expected_behavior_source: AC-9; BC-29 ("backups and journals ... have mode 0600 and
    <data directory>/user has mode 0700"); ADR-002 decision 4."""
    journal = FsChangeJournal.for_user(data_dir)
    target = data_dir / "user" / "journal" / "c-1.json"

    journal.start(user_record())
    assert mode(target) == 0o600
    journal.mark_done("c-1", "claude/skills/orqlet/SKILL.md")
    assert mode(target) == 0o600
    journal.finish("c-1")
    assert mode(target) == 0o600

    assert mode(data_dir / "user") == 0o700
    assert mode(data_dir / "user" / "journal") == 0o700


@posix_only
def test_user_backup_files_are_0600_and_their_folders_0700(data_dir: Path) -> None:
    """AC-9. expected_behavior_source: AC-9; BC-29 ("including a newly created backup file");
    ADR-002 decision 4."""
    backups = FsBackupStore.for_user(data_dir)

    backups.save("c-1", p("claude/settings.json"), b'{"secret": 1}')

    stored = data_dir / "user" / "backups" / "c-1" / "claude" / "settings.json"
    assert mode(stored) == 0o600
    for folder in (
        data_dir / "user",
        data_dir / "user" / "backups",
        data_dir / "user" / "backups" / "c-1",
        data_dir / "user" / "backups" / "c-1" / "claude",
    ):
        assert mode(folder) == 0o700, folder
    assert backups.load("c-1", p("claude/settings.json")) == b'{"secret": 1}'


# --- AC-9: owners, JSON entry keys and hashes, pinned roots --------------------------------------


def test_owners_keys_json_hashes_and_roots_round_trip(data_dir: Path) -> None:
    """AC-9. expected_behavior_source: AC-9 ("an entry records its owners and, for a JSON entry,
    its key and canonical hash"); ADR-002 decision 4 ("Journal content") and decision 1a ("Roots
    are pinned"); the interface (JournalEntry.owners, key, json_sha256; JournalRecord.roots)."""
    record = JournalRecord(
        change_id="c-1",
        command="install",
        plan_digest="eeee",
        created_at=CREATED,
        entries=(
            JournalEntry(
                "agents/skills/orqlet/SKILL.md", "create", None, A, owners=("codex", "cursor")
            ),
            JournalEntry(
                "claude/settings.json",
                "update",
                B,
                C,
                owners=("claude-code",),
                key="hooks/SessionStart/orqlet",
                json_sha256=A,
            ),
        ),
        roots={"agents": "/home/example/.agents", "claude": "/home/example/.claude"},
    )
    journal = FsChangeJournal.for_user(data_dir)

    journal.start(record)
    assert journal.read("c-1") == record

    journal.mark_done("c-1", "claude/settings.json")
    after = journal.read("c-1")
    assert after is not None
    shared = after.entries[1]
    assert shared.done is True
    assert shared.owners == ("claude-code",)
    assert shared.key == "hooks/SessionStart/orqlet"
    assert shared.json_sha256 == A
    assert after.entries[0].owners == ("codex", "cursor")
    assert after.roots == record.roots


def test_the_new_fields_are_written_only_when_set(data_dir: Path) -> None:
    """AC-9. expected_behavior_source: the interface ("the new fields ... are written only when
    set"); A-27."""
    record = user_record(
        "c-1",
        JournalEntry("claude/skills/orqlet/SKILL.md", "create", None, A),
        JournalEntry("claude/agents/orqlet.md", "create", None, B, owners=("claude-code",)),
    )
    FsChangeJournal.for_user(data_dir).start(record)

    document = json.loads((data_dir / "user" / "journal" / "c-1.json").read_text("utf-8"))
    plain, owned = document["entries"]
    assert {"owners", "key", "json_sha256"}.isdisjoint(plain)
    assert owned["owners"] == ["claude-code"]
    assert {"key", "json_sha256"}.isdisjoint(owned)
    assert "roots" not in document


# --- AC-9 and AC-10: the project journal is unchanged --------------------------------------------


def test_a_project_journal_without_the_new_fields_decodes_unchanged(data_dir: Path) -> None:
    """AC-9. expected_behavior_source: AC-9 ("a project journal without the new fields decodes
    unchanged"); A-27."""
    write_project_journal(data_dir, "c-old", PROJECT_JOURNAL)

    record = FsChangeJournal(LocalFileSystem(data_dir), "p1").read("c-old")

    assert record == PROJECT_RECORD
    assert record is not None
    assert record.roots == {}
    assert all(e.owners == () and e.key is None and e.json_sha256 is None for e in record.entries)


def test_a_project_journal_is_written_as_before(data_dir: Path) -> None:
    """AC-10. expected_behavior_source: AC-10 (regression: the project journal unchanged); A-27;
    the interface (the new fields are written only when set)."""
    FsChangeJournal(LocalFileSystem(data_dir), "p1").start(PROJECT_RECORD)

    target = data_dir / "projects" / "p1" / "upgrade" / "c-old.json"
    assert target.read_bytes() == PROJECT_JOURNAL.encode("utf-8")


def test_the_user_journal_never_reads_a_project_journal(data_dir: Path) -> None:
    """AC-9. expected_behavior_source: AC-9 ("the user namespace never reads projects/<id>");
    BC-31; ADR-002 decision 4 (a user namespace that never collides with projects/<id>)."""
    project = write_project_journal(data_dir, "c-old", PROJECT_JOURNAL)
    journal = FsChangeJournal.for_user(data_dir)

    assert journal.open_changes() == ()
    assert journal.read("c-old") is None

    journal.start(user_record("c-1"))
    journal.mark_done("c-1", "claude/skills/orqlet/SKILL.md")
    journal.finish("c-1")
    assert journal.open_changes() == ()
    assert project.read_bytes() == PROJECT_JOURNAL.encode("utf-8")
    assert FsChangeJournal(LocalFileSystem(data_dir), "p1").open_changes() == ("c-old",)


def test_the_user_backups_never_read_a_project_backup(data_dir: Path) -> None:
    """AC-9. expected_behavior_source: AC-9; BC-31; ADR-002 decision 4."""
    FsBackupStore(LocalFileSystem(data_dir), "p1").save("c-1", p("claude/settings.json"), b"{}")

    assert FsBackupStore.for_user(data_dir).load("c-1", p("claude/settings.json")) is None


# --- AC-13 (journal part): a client change without a hook entry ---------------------------------


def test_a_change_without_a_hook_entry_records_its_owners(
    roots: dict[str, Path], data_dir: Path
) -> None:
    """AC-13. expected_behavior_source: AC-13 ("its entries record their owners, and nothing in the
    user namespace requires a hook entry per client"); Q-82; BC-38; ADR-002 decision 4."""
    files: dict[str, tuple[bytes, tuple[str, ...]]] = {
        "agents/skills/orqlet/SKILL.md": (b"skill", ("codex", "cursor")),
        "claude/skills/orqlet/SKILL.md": (b"skill", ("claude-code",)),
        "claude/agents/orqlet-tester.md": (b"agent", ("claude-code",)),
        "claude/rules/orqlet-foundation.md": (b"foundation", ("claude-code",)),
        "codex/agents/orqlet-tester.toml": (b"agent", ("codex",)),
        "codex/AGENTS.md": (b"block", ("codex",)),
        "cursor/agents/orqlet-tester.md": (b"agent", ("cursor",)),
        "data/cursor-user-rules.md": (b"rules", ("cursor",)),
    }
    record = user_record(
        "c-1",
        *(
            JournalEntry(path, "create", None, sha256_hex(content), owners=owners)
            for path, (content, owners) in files.items()
        ),
    )
    fs = UserScopeFileSystem(roots, writable=True)
    journal = FsChangeJournal.for_user(data_dir)

    journal.start(record)
    for path, (content, _owners) in files.items():
        fs.write_atomic(p(path), content)
        journal.mark_done("c-1", path)
    journal.finish("c-1")

    stored = journal.read("c-1")
    assert stored is not None
    assert stored.status == "complete"
    assert {e.path: e.owners for e in stored.entries} == {
        path: owners for path, (_content, owners) in files.items()
    }
    assert all(e.done for e in stored.entries)
    assert not any(e.path.endswith(("settings.json", "hooks.json")) for e in stored.entries)
    assert journal.open_changes() == ()
