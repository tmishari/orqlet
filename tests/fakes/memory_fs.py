"""An in-memory `FileSystem` that follows the port contract, for fast and deterministic tests."""

from __future__ import annotations

from orqlet.application.ports.filesystem import (
    FileKind,
    FileSystemError,
    LinkRefused,
    NotARegularFile,
    PathNotFound,
)
from orqlet.domain.paths import CanonicalPath


class MemoryFileSystem:
    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}
        self._dirs: set[str] = set()
        self._links: set[str] = set()

    # --- test helpers -------------------------------------------------------------------
    def add_symlink(self, path: str) -> None:
        self._links.add(str(CanonicalPath.parse(path)))

    def add_dir(self, path: str) -> None:
        """Create a directory even where the port would refuse the name (such as `.git`)."""
        self._dirs.add(path)

    def snapshot(self) -> dict[str, bytes]:
        return dict(self._files)

    # --- port -------------------------------------------------------------------------
    def kind(self, path: CanonicalPath) -> FileKind | None:
        if path.parent is not None:
            self._refuse_links(path.parent)
        name = str(path)
        if name in self._links:
            return FileKind.SYMLINK
        if name in self._files:
            return FileKind.FILE
        if name in self._dirs:
            return FileKind.DIRECTORY
        return None

    def read_bytes(self, path: CanonicalPath) -> bytes:
        self._refuse_links(path)
        kind = self.kind(path)
        if kind is None:
            raise PathNotFound(str(path))
        if kind is not FileKind.FILE:
            raise NotARegularFile(str(path))
        return self._files[str(path)]

    def write_atomic(self, path: CanonicalPath, data: bytes) -> None:
        self._refuse_links(path)
        kind = self.kind(path)
        if kind is not None and kind is not FileKind.FILE:
            raise NotARegularFile(str(path))
        self._make_parents(path)
        self._files[str(path)] = data

    def delete(self, path: CanonicalPath) -> None:
        self._refuse_links(path)
        kind = self.kind(path)
        if kind is None:
            return
        if kind is not FileKind.FILE:
            raise NotARegularFile(str(path))
        del self._files[str(path)]

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        prefix = "" if path is None else f"{path}/"
        if path is not None:
            self._refuse_links(path)
            if self.kind(path) is not FileKind.DIRECTORY:
                raise PathNotFound(str(path))
        names: set[str] = set()
        for entry in (*self._files, *self._dirs):
            if entry.startswith(prefix) and entry != prefix.rstrip("/"):
                names.add(entry[len(prefix) :].split("/", 1)[0])
        return tuple(sorted(names))

    def make_dir(self, path: CanonicalPath) -> None:
        self._refuse_links(path)
        if self.kind(path) is FileKind.FILE:
            raise NotARegularFile(str(path))
        self._make_parents(path)
        self._dirs.add(str(path))

    def remove_empty_dir(self, path: CanonicalPath) -> None:
        self._refuse_links(path)
        if self.kind(path) is not FileKind.DIRECTORY:
            return
        if self.list_dir(path):
            return
        self._dirs.discard(str(path))

    # --- internals -----------------------------------------------------------------------
    def _make_parents(self, path: CanonicalPath) -> None:
        parent = path.parent
        while parent is not None:
            if self.kind(parent) is FileKind.FILE:
                raise FileSystemError(f"a file is in the way: {parent}")
            self._dirs.add(str(parent))
            parent = parent.parent

    def _refuse_links(self, path: CanonicalPath) -> None:
        current: CanonicalPath | None = path
        while current is not None:
            if str(current) in self._links:
                raise LinkRefused(str(current))
            current = current.parent
