"""Looking above the repository for instruction files that other projects may share."""

from __future__ import annotations

from typing import Protocol


class AncestorFinder(Protocol):
    def find(self) -> tuple[str, ...]:
        """Paths of `CLAUDE.md`, `CLAUDE.local.md` or `AGENTS.md` above the root. Read-only."""
        ...
