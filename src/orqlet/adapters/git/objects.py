"""Reading file contents as Git objects through one `cat-file --batch` process."""

from __future__ import annotations

import re
from collections.abc import Sequence

from orqlet.adapters.git.git_runner import GitRunner
from orqlet.application.ports.vcs import VcsError

_REVISION = re.compile(r"^(?:HEAD|[0-9a-f]{40}|[0-9a-f]{64})$")


def check_revision(revision: str) -> None:
    """Accept `HEAD` or a full object id only, never a name that could mean something else."""
    if not _REVISION.fullmatch(revision):
        raise VcsError(f"not an accepted revision: {revision!r}")


def read_blobs(git: GitRunner, revision: str, paths: Sequence[str]) -> dict[str, bytes | None]:
    """Contents of each path at `revision`; `None` for a path that is missing or not a file.

    `revision` is `HEAD` or a full object id, never a name that could mean something else. A path
    may not hold a line break because the batch protocol is line based.
    """
    check_revision(revision)
    if any("\n" in path or "\0" in path for path in paths):
        raise VcsError("a path with a line break cannot be read as a Git object")
    if not paths:
        return {}
    request = "".join(f"{revision}:{path}\n" for path in paths).encode("utf-8")
    result = git.run("cat-file", "--batch", stdin=request)
    return _parse_batch(result.stdout, paths)


def _parse_batch(output: bytes, paths: Sequence[str]) -> dict[str, bytes | None]:
    found: dict[str, bytes | None] = {}
    position = 0
    for path in paths:
        end = output.find(b"\n", position)
        if end < 0:
            raise VcsError("unexpected end of git cat-file output")
        header = output[position:end].decode("utf-8", errors="replace")
        position = end + 1
        parts = header.split(" ")
        if len(parts) == 2 and parts[1] in {"missing", "ambiguous"}:
            found[path] = None
            continue
        if len(parts) != 3 or not parts[2].isdigit():
            raise VcsError(f"unexpected git cat-file header: {header!r}")
        size = int(parts[2])
        body = output[position : position + size]
        if len(body) != size:
            raise VcsError("truncated git cat-file output")
        position += size + 1  # the newline that follows each object
        found[path] = body if parts[1] == "blob" else None
    return found
