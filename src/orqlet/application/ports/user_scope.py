"""The user scope's roots: inspected before any read, prepared only after consent (ADR-002 1a).

Each prefix of a user-scope path names one root: a client's folder under the home, or the data
directory's `user` folder. The inspector reports every root without creating or changing anything;
the use case plans through `planning_fs` and, after the person's yes, writes through the file system
that `prepare` returns.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from orqlet.application.contracts.user_scope import UserHome
from orqlet.application.ports.filesystem import FileSystem, FileSystemError
from orqlet.domain.errors import OrqletError

UserPrefix = Literal["claude", "cursor", "codex", "agents", "copilot", "data"]
USER_PREFIXES: tuple[UserPrefix, ...] = ("agents", "claude", "codex", "copilot", "cursor", "data")


class UserRootRefused(OrqletError):
    """A root failed validation; the text starts with the variable the person can correct."""

    def __init__(self, prefix: str, variable: str, reason: str) -> None:
        super().__init__(reason)
        self.prefix = prefix
        self.variable = variable
        self.reason = reason


class PathNotWritable(FileSystemError):
    """A user-scope path outside the allow-listed roots and sub-paths."""


class ReadOnlyUserScope(FileSystemError):
    """A write through the planning view, before the person consented."""


@dataclass(frozen=True, slots=True)
class RootState:
    prefix: UserPrefix
    variable: str  # HOME or USERPROFILE, CODEX_HOME, COPILOT_HOME or ORQLET_DATA_DIR
    path: str  # the resolved real root; for a missing root, below its nearest existing ancestor
    exists: bool
    refusal: str | None = None  # starts with `variable`, names the root and the reason
    creates: tuple[str, ...] = ()  # the folders `prepare` creates, outermost first
    tightens: tuple[str, ...] = ()  # Orqlet's own folders with group or world access
    warning: str | None = None  # a platform warning, such as unchecked access on Windows


class UserRootInspector(Protocol):
    def inspect(self, home: UserHome) -> Mapping[UserPrefix, RootState]:
        """Validate every root. Creates nothing, changes no mode and starts no process."""
        ...

    def planning_fs(self, states: Mapping[UserPrefix, RootState]) -> FileSystem:
        """A read-only view: a missing root reads as empty, a refused one raises on access."""
        ...

    def prepare(self, states: Mapping[UserPrefix, RootState]) -> FileSystem:
        """After consent: create and tighten, validate again, and open the writable composite.

        Raises `UserRootRefused` for a refused state, and for a root that no longer resolves to
        the path it was pinned to.
        """
        ...
