"""An advisory file lock in the user's data directory (one per project)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock, Timeout

from orqlet.application.ports.lock import ApplyBusy


class FileApplyLock:
    def __init__(self, path: Path, *, timeout_seconds: float = 10.0) -> None:
        self._path = path
        self._timeout = timeout_seconds

    @contextmanager
    def hold(self) -> Iterator[None]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(self._path), timeout=self._timeout)
        try:
            lock.acquire()
        except Timeout as exc:
            raise ApplyBusy(
                "Another Orqlet process is changing this project. Wait for it to finish and "
                "run the command again."
            ) from exc
        try:
            yield
        finally:
            lock.release()
