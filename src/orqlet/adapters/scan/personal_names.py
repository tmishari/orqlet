"""Lists the names of personal skills and agents (proposal sections 4.4 and 8.13, FM-W03).

Names only: a directory listing, never a file read. The caller runs this only when the
maintainer opts in, and prints exactly what was listed.
"""

from __future__ import annotations

import os
from pathlib import Path

from orqlet.application.ports.personal import PersonalItem

# Personal locations according to each client's published documentation (unverified, spike S-21).
LOCATIONS = (
    ".claude/skills",
    ".claude/agents",
    ".codex/agents",
    ".agents/skills",
    ".cursor/agents",
)


class FsPersonalNames:
    def __init__(self, home: Path) -> None:
        self._home = home

    def list_names(self) -> tuple[PersonalItem, ...]:
        items: list[PersonalItem] = []
        for relative in LOCATIONS:
            directory = self._home / relative
            try:
                with os.scandir(directory) as entries:
                    names = sorted(entry.name for entry in entries)
            except (FileNotFoundError, NotADirectoryError, PermissionError):
                continue
            items += [PersonalItem(f"~/{relative}", name) for name in names]
        return tuple(items)
