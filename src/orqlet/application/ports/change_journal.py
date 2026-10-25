"""The record of a change in progress, and the copies that let it be undone (ADR-004).

Both live outside the repository, in the user's data directory, so a repository cannot forge
or read them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from orqlet.domain.errors import OrqletError
from orqlet.domain.paths import CanonicalPath


class JournalError(OrqletError):
    """The journal or the backup area cannot be read or does not match the plan."""


@dataclass(frozen=True, slots=True)
class JournalEntry:
    path: str
    kind: Literal["create", "update", "delete"]
    before_sha256: str | None
    after_sha256: str | None
    is_proposal: bool = False
    done: bool = False


@dataclass(frozen=True, slots=True)
class JournalRecord:
    change_id: str
    command: str  # "init", "upgrade" or "rollback"
    plan_digest: str
    created_at: str  # UTC, ISO 8601
    entries: tuple[JournalEntry, ...]
    status: Literal["open", "complete", "superseded", "rolled-back"] = "open"


class ChangeJournal(Protocol):
    def start(self, record: JournalRecord) -> None:
        """Record the plan before the first write. Replaces nothing: a change id is used once."""
        ...

    def mark_done(self, change_id: str, path: str) -> None:
        """Record that one file of the plan has been written, atomically."""
        ...

    def finish(
        self,
        change_id: str,
        status: Literal["complete", "superseded", "rolled-back"] = "complete",
    ) -> None: ...

    def read(self, change_id: str) -> JournalRecord | None: ...

    def open_changes(self) -> tuple[str, ...]:
        """Ids of changes that were started and never finished, sorted."""
        ...


class BackupStore(Protocol):
    def save(self, change_id: str, path: CanonicalPath, content: bytes) -> None:
        """Keep the content a file had before the change."""
        ...

    def load(self, change_id: str, path: CanonicalPath) -> bytes | None: ...
