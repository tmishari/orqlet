"""The only source of the current time."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time as a timezone-aware UTC value."""
        ...
