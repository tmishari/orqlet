"""Names of personal skills and agents, listed only when the maintainer asks for it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PersonalItem:
    location: str  # a directory in the user's home, for example `~/.claude/skills`
    name: str  # the entry's name only; its content is never read


class PersonalNames(Protocol):
    def list_names(self) -> tuple[PersonalItem, ...]:
        """Entry names in the personal locations of the supported clients. Nothing is read."""
        ...
