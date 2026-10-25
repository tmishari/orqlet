"""File access rooted at one directory. Paths are always `CanonicalPath`, relative to that root."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from orqlet.domain.errors import OrqletError
from orqlet.domain.paths import CanonicalPath


class FileKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"


class FileSystemError(OrqletError):
    """Base class of every file-system port failure."""


class PathNotFound(FileSystemError):
    pass


class LinkRefused(FileSystemError):
    """A symbolic link, junction or reparse point sits on the path or is the target."""


class NotARegularFile(FileSystemError):
    pass


class FileSystem(Protocol):
    def kind(self, path: CanonicalPath) -> FileKind | None:
        """What `path` is, without following links; `None` when it does not exist.

        A link as the last component is reported as `SYMLINK`. A link above it raises
        `LinkRefused`, because nothing below a link may be trusted.
        """
        ...

    def read_bytes(self, path: CanonicalPath) -> bytes:
        """Read a regular file. Raises `PathNotFound`, `LinkRefused` or `NotARegularFile`."""
        ...

    def write_atomic(self, path: CanonicalPath, data: bytes) -> None:
        """Create or replace a regular file so that readers see the old or the new content."""
        ...

    def delete(self, path: CanonicalPath) -> None:
        """Remove a regular file. A missing file is not an error."""
        ...

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        """Names directly inside a directory (`None` is the root), sorted by code point."""
        ...

    def make_dir(self, path: CanonicalPath) -> None:
        """Create a directory and its parents. An existing directory is not an error."""
        ...

    def remove_empty_dir(self, path: CanonicalPath) -> None:
        """Remove an empty directory. A missing or non-empty directory is left alone."""
        ...
