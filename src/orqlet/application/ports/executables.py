"""Which program a bare command name resolves to on `PATH`, found without starting it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class OnPath(StrEnum):
    SAME = "same"  # `PATH` resolves the name to the running executable
    DIFFERENT = "different"
    ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class ExecutableLookup:
    on_path: OnPath
    # An empty, `.` or relative element, or one writable by others, is searched before the match or
    # holds it, so a program in an untrusted folder could be found first (ADR-004 decision 7, Q-79).
    unsafe_element_searched: bool


class ExecutableLocator(Protocol):
    def locate(self, name: str) -> ExecutableLookup:
        """Look `name` up on `PATH` and compare the match with the running executable."""
        ...

    def searches_unsafe(self, name: str) -> bool:
        """Whether an unsafe element is searched before `name` is found, its own element included.

        A process started by the bare name in an untrusted working folder could then run a
        program from that folder.
        """
        ...
