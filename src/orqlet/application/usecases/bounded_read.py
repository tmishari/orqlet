"""Reading a lock or instruction file of a possibly hostile project: one regular file, bounded."""

from __future__ import annotations

from orqlet.application.ports.filesystem import FileKind, LinkRefused, PathNotFound, ReadOnlyFiles
from orqlet.domain.errors import OrqletError
from orqlet.domain.paths import CanonicalPath

MAX_LOCK_BYTES = 1_048_576


class BoundedReadRefused(OrqletError):
    """The file is a link, sits below a link, is not a regular file, or is too large."""


def read_bounded(
    files: ReadOnlyFiles, path: CanonicalPath, *, limit: int = MAX_LOCK_BYTES
) -> bytes | None:
    """The content of `path`, or `None` when nothing is there; reads at most `limit` + 1 bytes."""
    try:
        kind = files.kind(path)
        if kind is None:
            return None
        if kind is not FileKind.FILE:
            raise BoundedReadRefused(f"{path} is not a regular file")
        content = files.read_prefix(path, limit + 1)
    except LinkRefused:
        raise BoundedReadRefused(f"{path} sits below a link") from None
    except PathNotFound:
        return None
    if len(content) > limit:
        raise BoundedReadRefused(f"{path} is larger than {limit} bytes")
    return content
