"""Helpers shared by the scanners: reading a manifest and citing a line of it as evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from orqlet.application.contracts.common import Evidence
from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.domain.facts import EvidenceError, find_line, line_range_hash
from orqlet.domain.paths import CanonicalPath

MAX_FILE_BYTES = 1_048_576


@dataclass(frozen=True, slots=True)
class Source:
    """One file that was read: its repository-relative path and its bytes."""

    path: str
    content: bytes


def at(scope: CanonicalPath | None, name: str) -> CanonicalPath:
    """`name` inside the directory `scope` (the repository root when `scope` is `None`)."""
    path = CanonicalPath.parse(name)
    if scope is None:
        return path
    return CanonicalPath(scope.parts + path.parts)


def read_source(
    fs: FileSystem, scope: CanonicalPath | None, name: str, notes: list[str] | None = None
) -> Source | None:
    """The file if it is a regular file of a readable size, else `None`."""
    path = at(scope, name)
    if fs.kind(path) is not FileKind.FILE:
        return None
    content = fs.read_bytes(path)
    if len(content) > MAX_FILE_BYTES:
        if notes is not None:
            notes.append(f"{path} is larger than {MAX_FILE_BYTES} bytes and was not read")
        return None
    return Source(str(path), content)


def evidence_at(source: Source, line: int | None) -> Evidence | None:
    if line is None:
        return None
    try:
        return Evidence(
            path=source.path,
            lines=f"{line}-{line}",
            sha256=line_range_hash(source.content, line, line),
        )
    except EvidenceError:
        return None


def evidence_matching(source: Source, pattern: str) -> Evidence | None:
    """Evidence for the first line that matches `pattern`, or `None`."""
    return evidence_at(source, find_line(source.content, re.compile(pattern.encode("utf-8"))))


def scope_text(scope: CanonicalPath | None) -> str:
    return "." if scope is None else str(scope)
