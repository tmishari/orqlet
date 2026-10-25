"""Find every technology in a repository, including each service of a monorepo.

The root and its sub-directories (two levels deep) are handed to every scanner plug-in. Folders
that hold generated or third-party code are skipped, as are hidden folders and links. The walk is
bounded, and when a bound is hit the result says so rather than pretending to be complete.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orqlet.application.contracts.profile import Technology
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.ports.scanner import TechnologyScanner
from orqlet.domain.errors import InvalidPath
from orqlet.domain.paths import CanonicalPath

MAX_DEPTH = 2
MAX_DIRECTORIES = 1000
MAX_TECHNOLOGIES = 500
_SKIPPED = frozenset(
    {
        "node_modules",
        "vendor",
        "target",
        "dist",
        "build",
        "venv",
        "env",
        "site-packages",
        "__pycache__",
        "third_party",
    }
)


@dataclass(frozen=True, slots=True)
class Discovery:
    technologies: tuple[Technology, ...]
    notes: tuple[str, ...]

    def languages(self) -> frozenset[str]:
        return frozenset(t.name for t in self.technologies if t.kind == "language")


def discover_technologies(fs: FileSystem, scanners: Sequence[TechnologyScanner]) -> Discovery:
    notes: list[str] = []
    found: dict[tuple[str, str, str | None, str], Technology] = {}
    directories = _directories(fs, notes)
    for scope in directories:
        for scanner in scanners:
            for technology in scanner.scan(fs, scope):
                key = (technology.kind, technology.name, technology.version, technology.scope)
                found.setdefault(key, technology)
                if len(found) >= MAX_TECHNOLOGIES:
                    notes.append(f"Stopped after {MAX_TECHNOLOGIES} technologies.")
                    return Discovery(_ordered(found), tuple(notes))
    return Discovery(_ordered(found), tuple(notes))


def _ordered(found: dict[tuple[str, str, str | None, str], Technology]) -> tuple[Technology, ...]:
    return tuple(
        sorted(
            found.values(), key=lambda t: (t.scope != ".", t.scope, t.kind, t.name, t.version or "")
        )
    )


def _directories(fs: FileSystem, notes: list[str]) -> list[CanonicalPath | None]:
    """The root, then sub-directories breadth first, to `MAX_DEPTH` and `MAX_DIRECTORIES`."""
    result: list[CanonicalPath | None] = [None]
    level: list[CanonicalPath | None] = [None]
    for _ in range(MAX_DEPTH):
        following: list[CanonicalPath | None] = []
        for parent in level:
            for name in _children(fs, parent):
                path = CanonicalPath.parse(name) if parent is None else parent.child(name)
                if len(result) >= MAX_DIRECTORIES:
                    notes.append(f"Looked at {MAX_DIRECTORIES} directories and stopped.")
                    return result
                result.append(path)
                following.append(path)
        level = following
    return result


def _children(fs: FileSystem, parent: CanonicalPath | None) -> list[str]:
    try:
        names = fs.list_dir(parent)
    except FileSystemError:
        return []
    kept = []
    for name in names:
        if name.startswith(".") or name.lower() in _SKIPPED:
            continue
        try:
            child = CanonicalPath.parse(name) if parent is None else parent.child(name)
            if fs.kind(child) is FileKind.DIRECTORY:
                kept.append(name)
        except (FileSystemError, InvalidPath):
            continue
    return kept
