"""The local file system behind the `FileSystem` port.

Every operation is relative to one root and refuses to cross a symbolic link, a Windows junction
or any other reparse point, on any component of the path. Writes go to a temporary file in the
same directory and replace the target in one step.

Limit: the link check and the open are separate system calls, so a process that swaps a directory
for a link between them can still win a race. Reads and replaces use `O_NOFOLLOW` where the
platform has it, which closes the race for the final component. Orqlet is a single-user local
tool; it is not a defence against a hostile process on the same account.
"""

from __future__ import annotations

import contextlib
import errno
import os
import stat
import tempfile
import time
from pathlib import Path

from orqlet.application.ports.filesystem import (
    FileKind,
    FileSystemError,
    LinkRefused,
    NotARegularFile,
    PathNotFound,
)
from orqlet.domain.paths import CanonicalPath

_TEMP_PREFIX = ".orqlet-tmp-"
_IS_WINDOWS = os.name == "nt"
_REPLACE_ATTEMPTS = 5
_REPLACE_BACKOFF_SECONDS = 0.05
_DEFAULT_MODE = 0o644


def _replace_with_retry(source: str, target: Path) -> None:
    """`os.replace`, retried a few times on Windows, where it fails while the target is open."""
    attempts = _REPLACE_ATTEMPTS if _IS_WINDOWS else 1
    for attempt in range(1, attempts + 1):
        try:
            os.replace(source, target)
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(_REPLACE_BACKOFF_SECONDS * attempt)
        else:
            return


def _is_link(path: Path, info: os.stat_result) -> bool:
    if stat.S_ISLNK(info.st_mode):
        return True
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if getattr(info, "st_file_attributes", 0) & reparse:
        return True
    return os.path.isjunction(path)


def _classify(path: Path, info: os.stat_result) -> FileKind:
    if _is_link(path, info):
        return FileKind.SYMLINK
    if stat.S_ISREG(info.st_mode):
        return FileKind.FILE
    if stat.S_ISDIR(info.st_mode):
        return FileKind.DIRECTORY
    return FileKind.OTHER


class LocalFileSystem:
    def __init__(self, root: Path) -> None:
        resolved = root.resolve(strict=True)
        if not resolved.is_dir():
            raise FileSystemError(f"not a directory: {root}")
        self._root = resolved

    @property
    def root(self) -> Path:
        return self._root

    # --- port -------------------------------------------------------------------------
    def kind(self, path: CanonicalPath) -> FileKind | None:
        target = self._locate(path.parts[:-1]) / path.parts[-1]
        info = self._lstat(target)
        return None if info is None else _classify(target, info)

    def read_bytes(self, path: CanonicalPath) -> bytes:
        target = self._locate(path.parts)
        info = self._lstat(target)
        if info is None:
            raise PathNotFound(str(path))
        if _classify(target, info) is not FileKind.FILE:
            raise NotARegularFile(str(path))
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        try:
            descriptor = os.open(target, flags)
        except FileNotFoundError as exc:
            raise PathNotFound(str(path)) from exc
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise LinkRefused(str(path)) from exc
            raise FileSystemError(f"cannot read {path}: {exc.strerror}") from exc
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read()

    def write_atomic(self, path: CanonicalPath, data: bytes) -> None:
        if path.parent is not None:
            self._ensure_dirs(path.parent.parts)
        target = self._locate(path.parts)
        info = self._lstat(target)
        mode = _DEFAULT_MODE
        if info is not None:
            if _classify(target, info) is not FileKind.FILE:
                raise NotARegularFile(str(path))
            mode = stat.S_IMODE(info.st_mode)
        descriptor, temp_name = tempfile.mkstemp(prefix=_TEMP_PREFIX, dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, mode)
            _replace_with_retry(temp_name, target)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(temp_name)
            raise
        self._sync_directory(target.parent)

    def delete(self, path: CanonicalPath) -> None:
        target = self._locate(path.parts)
        info = self._lstat(target)
        if info is None:
            return
        if _classify(target, info) is not FileKind.FILE:
            raise NotARegularFile(str(path))
        os.unlink(target)

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        target = self._locate(() if path is None else path.parts)
        try:
            with os.scandir(target) as entries:
                return tuple(sorted(entry.name for entry in entries))
        except (FileNotFoundError, NotADirectoryError) as exc:
            raise PathNotFound(str(path)) from exc

    def make_dir(self, path: CanonicalPath) -> None:
        self._ensure_dirs(path.parts)

    def remove_empty_dir(self, path: CanonicalPath) -> None:
        target = self._locate(path.parts)
        info = self._lstat(target)
        if info is None or _classify(target, info) is not FileKind.DIRECTORY:
            return
        with contextlib.suppress(OSError):  # not empty, or in use: leave it
            os.rmdir(target)

    # --- internals -----------------------------------------------------------------------
    @staticmethod
    def _lstat(target: Path) -> os.stat_result | None:
        try:
            return os.lstat(target)
        except (FileNotFoundError, NotADirectoryError):
            return None

    def _locate(self, parts: tuple[str, ...]) -> Path:
        """Join `parts` below the root, refusing any existing link on the way."""
        current = self._root
        exists = True
        for part in parts:
            current = current / part
            if not exists:
                continue
            info = self._lstat(current)
            if info is None:
                exists = False
            elif _is_link(current, info):
                raise LinkRefused(str(current.relative_to(self._root).as_posix()))
        return current

    def _ensure_dirs(self, parts: tuple[str, ...]) -> None:
        current = self._root
        for index, part in enumerate(parts):
            current = current / part
            info = self._lstat(current)
            if info is None:
                with contextlib.suppress(
                    FileExistsError
                ):  # created a moment ago by another process
                    current.mkdir()
                continue
            kind = _classify(current, info)
            if kind is FileKind.DIRECTORY:
                continue
            if kind is FileKind.SYMLINK:
                raise LinkRefused("/".join(parts[: index + 1]))
            if index == len(parts) - 1:
                raise NotARegularFile("/".join(parts))
            raise FileSystemError(f"a file is in the way: {'/'.join(parts[: index + 1])}")

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        """Make the rename durable where the platform allows it; a no-op on Windows."""
        if os.name == "nt":
            return
        with contextlib.suppress(OSError):
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
