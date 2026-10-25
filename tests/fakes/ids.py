from __future__ import annotations

from uuid import UUID


class SequentialIds:
    """Predictable UUIDs: 00000000-0000-4000-8000-000000000001, then ...02, and so on."""

    def __init__(self, start: int = 0) -> None:
        self._counter = start

    def new_id(self) -> str:
        self._counter += 1
        return str(UUID(int=self._counter | (0x4000 << 64) | (0x8000 << 48)))


class ReplayIds:
    """The first id repeats an earlier run's first id; every later id starts at `later_from`.

    A rerun after a crash then gets the same project id as the first run and a fresh change id.
    """

    def __init__(self, first: str, later_from: int = 1000) -> None:
        self._first = first
        self._used_first = False
        self._counter = later_from - 1

    def new_id(self) -> str:
        if not self._used_first:
            self._used_first = True
            return self._first
        self._counter += 1
        return str(UUID(int=self._counter | (0x4000 << 64) | (0x8000 << 48)))
