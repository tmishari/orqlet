"""Implementations of each port that the contract suites run against.

Later phases register the real adapters here, so one suite checks the fake and the real thing.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.application.ports.filesystem import FileSystem
from tests.fakes.memory_fs import MemoryFileSystem

FileSystemFactory = Callable[[Path], FileSystem]

FILESYSTEMS: dict[str, FileSystemFactory] = {
    "memory": lambda _tmp: MemoryFileSystem(),
    "local": lambda tmp: LocalFileSystem(tmp),
}
