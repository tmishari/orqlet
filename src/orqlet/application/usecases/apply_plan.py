"""Apply a change plan: verify, back up, journal, write in order, manifest last (ADR-004).

A crash at any point leaves the old state, the new state or a recorded partial state. Running
the same command again converges, because every file that was written already equals the render
and is classified as up to date.
"""

from __future__ import annotations

from dataclasses import dataclass

from orqlet.application.ports.change_journal import (
    BackupStore,
    ChangeJournal,
    JournalEntry,
    JournalRecord,
)
from orqlet.application.ports.clock import Clock
from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.application.ports.lock import ApplyLock
from orqlet.domain.changeplan import ChangePlan, PlannedWrite
from orqlet.domain.digest import sha256_hex
from orqlet.domain.errors import OrqletError


class PlanStale(OrqletError):
    """The tree changed between the preview and the apply. Nothing was written."""


@dataclass(frozen=True, slots=True)
class ApplyResult:
    change_id: str
    written: tuple[str, ...]
    deleted: tuple[str, ...]


def apply_plan(
    project: FileSystem,
    journal: ChangeJournal,
    backups: BackupStore,
    plan: ChangePlan,
    *,
    lock: ApplyLock,
    change_id: str,
    command: str,
    clock: Clock,
) -> ApplyResult:
    with lock.hold():
        ordered = sorted(plan.writes, key=lambda w: (w.last, w.path.sort_key()))
        _verify_unchanged(project, ordered)
        for write in ordered:
            if write.before_sha256 is not None:
                backups.save(change_id, write.path, project.read_bytes(write.path))
        for earlier in journal.open_changes():
            journal.finish(earlier, "superseded")
        journal.start(
            JournalRecord(
                change_id=change_id,
                command=command,
                plan_digest=plan.digest,
                created_at=clock.now().isoformat(),
                entries=tuple(_entry(write) for write in ordered),
            )
        )
        written: list[str] = []
        deleted: list[str] = []
        for write in ordered:
            if write.kind == "delete":
                project.delete(write.path)
                deleted.append(str(write.path))
            else:
                assert write.content is not None
                project.write_atomic(write.path, write.content)
                written.append(str(write.path))
            journal.mark_done(change_id, str(write.path))
        journal.finish(change_id)
        return ApplyResult(change_id, tuple(written), tuple(deleted))


def _verify_unchanged(project: FileSystem, writes: list[PlannedWrite]) -> None:
    """Preview-to-apply integrity: every file must still be what the plan was made from."""
    for write in writes:
        kind = project.kind(write.path)
        if write.before_sha256 is None:
            if kind is not None:
                raise PlanStale(f"{write.path} appeared after the preview")
            continue
        if (
            kind is not FileKind.FILE
            or sha256_hex(project.read_bytes(write.path)) != write.before_sha256
        ):
            raise PlanStale(f"{write.path} changed after the preview")


def _entry(write: PlannedWrite) -> JournalEntry:
    kind = write.kind if write.kind in {"create", "update", "delete"} else "update"
    return JournalEntry(
        path=str(write.path),
        kind=kind,  # type: ignore[arg-type]
        before_sha256=write.before_sha256,
        after_sha256=write.after_sha256,
        is_proposal=write.is_proposal,
    )
