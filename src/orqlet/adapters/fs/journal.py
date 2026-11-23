"""The change journal and the backup area as files below the user's data directory.

Both classes work on a `FileSystem` rooted at that directory, so tests can use memory and the
real tool uses a `LocalFileSystem`. A project change lives below `projects/<project-id>/`:

    upgrade/<change-id>.json        the journal of one change
    backups/<change-id>/<path>      the content a file had before the change

A user-scope change (`for_user`) lives below `user/` instead, as `journal/<change-id>.json` and
`backups/<change-id>/<prefixed path>`, written 0600 in folders created 0700. It never reads
`projects/`.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, cast

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.application.ports.change_journal import JournalEntry, JournalError, JournalRecord
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.domain.errors import InvalidPath
from orqlet.domain.paths import CanonicalPath

_USER_DIR = CanonicalPath.parse("user")


def _project_dir(project_id: str) -> CanonicalPath:
    try:
        return CanonicalPath.parse("projects").child(project_id)
    except InvalidPath as exc:
        raise JournalError(f"not a usable project id: {project_id!r}") from exc


def _private_fs(data_directory: Path) -> LocalFileSystem:
    return LocalFileSystem(data_directory, private=True)


class FsChangeJournal:
    def __init__(self, fs: FileSystem, project_id: str) -> None:
        self._fs = fs
        self._dir = _project_dir(project_id).child("upgrade")

    @classmethod
    def for_user(cls, data_directory: Path) -> FsChangeJournal:
        journal = cls.__new__(cls)
        journal._fs = _private_fs(data_directory)
        journal._dir = _USER_DIR.child("journal")
        return journal

    def start(self, record: JournalRecord) -> None:
        if self._fs.kind(self._path(record.change_id)) is not None:
            raise JournalError(f"change {record.change_id} already has a journal")
        self._write(record)

    def mark_done(self, change_id: str, path: str) -> None:
        record = self._require(change_id)
        entries = tuple(replace(e, done=True) if e.path == path else e for e in record.entries)
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

    @classmethod
    def for_user(cls, data_directory: Path) -> FsBackupStore:
        store = cls.__new__(cls)
        store._fs = _private_fs(data_directory)
        store._dir = _USER_DIR.child("backups")
        return store

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


def _encode_entry(entry: JournalEntry) -> dict[str, Any]:
    document: dict[str, Any] = {
        "path": entry.path,
        "kind": entry.kind,
        "before_sha256": entry.before_sha256,
        "after_sha256": entry.after_sha256,
        "is_proposal": entry.is_proposal,
        "done": entry.done,
    }
    # Written only when set, so a project journal keeps the bytes it had before the user scope.
    if entry.owners:
        document["owners"] = list(entry.owners)
    if entry.key is not None:
        document["key"] = entry.key
    if entry.json_sha256 is not None:
        document["json_sha256"] = entry.json_sha256
    return document


def _encode(record: JournalRecord) -> bytes:
    document: dict[str, Any] = {
        "change_id": record.change_id,
        "command": record.command,
        "plan_digest": record.plan_digest,
        "created_at": record.created_at,
        "status": record.status,
        "entries": [_encode_entry(e) for e in record.entries],
    }
    if record.roots:
        document["roots"] = dict(record.roots)
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _strings(value: object, what: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{what} is not a list of strings")
    return tuple(value)


def _optional_string(value: object, what: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{what} is not a string")
    return value


def _roots(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise TypeError("roots is not a map of strings")
    return dict(value)


def _decode_entry(e: dict[str, Any]) -> JournalEntry:
    return JournalEntry(
        path=e["path"],
        kind=cast(Any, e["kind"]),
        before_sha256=e["before_sha256"],
        after_sha256=e["after_sha256"],
        is_proposal=e["is_proposal"],
        done=e["done"],
        owners=_strings(e.get("owners", []), "owners"),
        key=_optional_string(e.get("key"), "key"),
        json_sha256=_optional_string(e.get("json_sha256"), "json_sha256"),
    )


def _decode(data: bytes) -> JournalRecord:
    document = json.loads(data.decode("utf-8"))
    return JournalRecord(
        change_id=document["change_id"],
        command=document["command"],
        plan_digest=document["plan_digest"],
        created_at=document["created_at"],
        status=cast(Any, document["status"]),
        entries=tuple(_decode_entry(e) for e in document["entries"]),
        roots=_roots(document.get("roots", {})),
    )
