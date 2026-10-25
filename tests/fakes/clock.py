from __future__ import annotations

from datetime import UTC, datetime, timedelta


class FixedClock:
    """Returns the same instant until the test moves it."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)
