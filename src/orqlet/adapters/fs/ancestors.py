"""Instruction files above the repository, found by name only and never read or changed."""

from __future__ import annotations

from pathlib import Path

_NAMES = ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md")


class FsAncestorFinder:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve(strict=True)

    def find(self) -> tuple[str, ...]:
        found: list[str] = []
        for directory in self._root.parents:
            for name in _NAMES:
                candidate = directory / name
                if candidate.is_file() and not candidate.is_symlink():
                    found.append(str(candidate))
        return tuple(found)
