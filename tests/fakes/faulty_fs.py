"""A file system that "crashes" after a chosen number of writes, to test that apply converges."""

from __future__ import annotations

from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.domain.paths import CanonicalPath


class SimulatedCrash(Exception):
    """Raised in place of the write that would have followed the crash point."""


class FaultyFileSystem:
    def __init__(self, inner: FileSystem, *, crash_after_writes: int | None) -> None:
        self._inner = inner
        self._limit = crash_after_writes
        self.mutations = 0

    def _mutate(self) -> None:
        if self._limit is not None and self.mutations >= self._limit:
            raise SimulatedCrash(f"crashed after {self.mutations} writes")
        self.mutations += 1

    def kind(self, path: CanonicalPath) -> FileKind | None:
        return self._inner.kind(path)

    def read_bytes(self, path: CanonicalPath) -> bytes:
        return self._inner.read_bytes(path)

    def write_atomic(self, path: CanonicalPath, data: bytes) -> None:
        self._mutate()
        self._inner.write_atomic(path, data)

    def delete(self, path: CanonicalPath) -> None:
        self._mutate()
        self._inner.delete(path)

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        return self._inner.list_dir(path)

    def make_dir(self, path: CanonicalPath) -> None:
        self._inner.make_dir(path)

    def remove_empty_dir(self, path: CanonicalPath) -> None:
        self._inner.remove_empty_dir(path)
