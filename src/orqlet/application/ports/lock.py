"""One writer at a time: a lock around the apply step of a change."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from orqlet.domain.errors import OrqletError


class ApplyBusy(OrqletError):
    """Another Orqlet process is applying a change to this project right now."""


class ApplyLock(Protocol):
    def hold(self) -> AbstractContextManager[None]:
        """Wait a bounded time for the lock and keep it. Raises `ApplyBusy` when it is not free."""
        ...
