"""The change journal and the backup area as files below the user's data directory.

Both classes work on a `FileSystem` rooted at that directory, so tests can use memory and the
real tool uses a `LocalFileSystem`. Layout (all below `projects/<project-id>/`):

    upgrade/<change-id>.json        the journal of one change
    backups/<change-id>/<path>      the content a file had before the change
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Literal, cast

from orqlet.application.ports.change_journal import JournalEntry, JournalError, JournalRecord
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.domain.errors import InvalidPath
from orqlet.domain.paths import CanonicalPath


def _project_dir(project_id: str) -> CanonicalPath:
    try:
        return CanonicalPath.parse("projects").child(project_id)
    except InvalidPath as exc:
        raise JournalError(f"not a usable project id: {project_id!r}") from exc


class FsChangeJournal:
    def __init__(self, fs: FileSystem, project_id: str) -> None:
        self._fs = fs
        self._dir = _project_dir(project_id).child("upgrade")

    def start(self, record: JournalRecord) -> None:
        if self._fs.kind(self._path(record.change_id)) is not None:
            raise JournalError(f"change {record.change_id} already has a journal")
        self._write(record)

    def mark_done(self, change_id: str, path: str) -> None:
        record = self._require(change_id)
        entries = tuple(
            JournalEntry(e.path, e.kind, e.before_sha256, e.after_sha256, e.is_proposal, True)
            if e.path == path
            else e
            for e in record.entries
        )
        self._write(replace(record, entries=entries))

    def finish(
        self,
        change_id: str,
        status: Literal["complete", "superseded", "rolled-back"] = "complete",
    ) -> None:
        self._write(replace(self._require(change_id), status=status))

    def read(self, change_id: str) -> JournalRecord | None:
        path = self._path(change_id)
        if self._fs.kind(path) is None:
            return None
        try:
            return _decode(self._fs.read_bytes(path))
        except (FileSystemError, ValueError, KeyError, TypeError) as exc:
            raise JournalError(f"journal {change_id} is unreadable") from exc

    def open_changes(self) -> tuple[str, ...]:
        if self._fs.kind(self._dir) is not FileKind.DIRECTORY:
            return ()
        found = []
        for name in self._fs.list_dir(self._dir):
            if name.endswith(".json"):
                record = self.read(name.removesuffix(".json"))
                if record is not None and record.status == "open":
                    found.append(record.change_id)
        return tuple(sorted(found))

    def _path(self, change_id: str) -> CanonicalPath:
        try:
            return self._dir.child(f"{change_id}.json")
        except InvalidPath as exc:
            raise JournalError(f"not a usable change id: {change_id!r}") from exc

    def _require(self, change_id: str) -> JournalRecord:
        record = self.read(change_id)
        if record is None:
            raise JournalError(f"change {change_id} has no journal")
        return record

    def _write(self, record: JournalRecord) -> None:
        self._fs.write_atomic(self._path(record.change_id), _encode(record))


class FsBackupStore:
    def __init__(self, fs: FileSystem, project_id: str) -> None:
        self._fs = fs
        self._dir = _project_dir(project_id).child("backups")

    def save(self, change_id: str, path: CanonicalPath, content: bytes) -> None:
        self._fs.write_atomic(self._target(change_id, path), content)

    def load(self, change_id: str, path: CanonicalPath) -> bytes | None:
        target = self._target(change_id, path)
        return self._fs.read_bytes(target) if self._fs.kind(target) is FileKind.FILE else None

    def _target(self, change_id: str, path: CanonicalPath) -> CanonicalPath:
        try:
            target = self._dir.child(change_id)
        except InvalidPath as exc:
            raise JournalError(f"not a usable change id: {change_id!r}") from exc
        for part in path.parts:
            target = target.child(part)
        return target


def _encode(record: JournalRecord) -> bytes:
    document = {
        "change_id": record.change_id,
        "command": record.command,
        "plan_digest": record.plan_digest,
        "created_at": record.created_at,
        "status": record.status,
        "entries": [
            {
                "path": e.path,
                "kind": e.kind,
                "before_sha256": e.before_sha256,
                "after_sha256": e.after_sha256,
                "is_proposal": e.is_proposal,
                "done": e.done,
            }
            for e in record.entries
        ],
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _decode(data: bytes) -> JournalRecord:
    document = json.loads(data.decode("utf-8"))
    return JournalRecord(
        change_id=document["change_id"],
        command=document["command"],
        plan_digest=document["plan_digest"],
        created_at=document["created_at"],
        status=cast(Any, document["status"]),
        entries=tuple(
            JournalEntry(
                path=e["path"],
                kind=cast(Any, e["kind"]),
                before_sha256=e["before_sha256"],
                after_sha256=e["after_sha256"],
                is_proposal=e["is_proposal"],
                done=e["done"],
            )
            for e in document["entries"]
        ),
    )
