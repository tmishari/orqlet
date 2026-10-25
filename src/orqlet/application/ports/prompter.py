"""Questions to the maintainer. The port is the only place a terminal is read."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    text: str
    options: tuple[str, ...] = ()
    default: str | None = None


class NoAnswerAvailable(Exception):
    """Raised when a question needs a person and none is there to answer."""


class Prompter(Protocol):
    @property
    def interactive(self) -> bool:
        """False when there is no terminal to ask, so a caller reports a question instead."""
        ...

    def ask(self, question: Question) -> str:
        """Return the maintainer's answer. Raises `NoAnswerAvailable` when not interactive."""
        ...

    def confirm(self, text: str, *, default: bool = False) -> bool:
        """Ask a yes or no question. Raises `NoAnswerAvailable` when not interactive."""
        ...
