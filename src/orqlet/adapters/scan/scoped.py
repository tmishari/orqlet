"""A read-only view of a sub-directory, so a scanner written for the root can scan a service."""

from __future__ import annotations

from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.domain.paths import CanonicalPath


class ScopedFileSystem:
    """Reads below `scope`. Writing is not offered, because scanners only read."""

    def __init__(self, inner: FileSystem, scope: CanonicalPath) -> None:
        self._inner = inner
        self._scope = scope

    def _full(self, path: CanonicalPath | None) -> CanonicalPath:
        return self._scope if path is None else CanonicalPath(self._scope.parts + path.parts)

    def kind(self, path: CanonicalPath) -> FileKind | None:
        return self._inner.kind(self._full(path))

    def read_bytes(self, path: CanonicalPath) -> bytes:
        return self._inner.read_bytes(self._full(path))

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        return self._inner.list_dir(self._full(path))
