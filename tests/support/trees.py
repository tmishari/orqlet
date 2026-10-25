"""Load a fixture directory into an in-memory file system, so unit tests do no real I/O."""

from __future__ import annotations

from pathlib import Path

from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def memory_fs_from(directory: Path) -> MemoryFileSystem:
    fs = MemoryFileSystem()
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            relative = path.relative_to(directory).as_posix()
            fs.write_atomic(CanonicalPath.parse(relative), path.read_bytes())
    return fs


def repo(name: str) -> MemoryFileSystem:
    return memory_fs_from(FIXTURES / "repos" / name)


def pack_dir(name: str | None = None) -> MemoryFileSystem:
    base = FIXTURES / "packs"
    return memory_fs_from(base / name if name else base)


def tech_packs() -> MemoryFileSystem:
    """Packs that match on language and technology rather than on Python frameworks."""
    return memory_fs_from(FIXTURES / "packs_tech")


def with_files(files: dict[str, str]) -> MemoryFileSystem:
    """A tree built from a mapping of relative path to text."""
    fs = MemoryFileSystem()
    for name, text in files.items():
        fs.write_atomic(CanonicalPath.parse(name), text.encode())
    return fs
