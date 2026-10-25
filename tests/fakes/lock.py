from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager


class NoLock:
    """A lock that is always free, for tests that run one process."""

    @contextmanager
    def hold(self) -> Iterator[None]:
        yield
