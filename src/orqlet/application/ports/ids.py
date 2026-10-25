"""The only source of new identifiers."""

from __future__ import annotations

from typing import Protocol


class IdGenerator(Protocol):
    def new_id(self) -> str:
        """A new random UUID in canonical lower-case text form."""
        ...
