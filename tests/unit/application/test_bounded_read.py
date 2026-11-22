"""The size-bounded, link-refusing reader of lock files (task one-command-setup, phase P-4, AC-4).

Every test cites its `expected_behavior_source`: AC-4 is the acceptance criterion of phase P-4 in
docs/design/one-command-setup/plan.yaml; ADR-001 decision 3 and ADR-004 decisions 5 and 6 are in
docs/design/one-command-setup/design/; "the interface" is the one that the Coder gave for P-4
(`read_bounded(files, path, *, limit=MAX_LOCK_BYTES)`, `MAX_LOCK_BYTES` and `BoundedReadRefused`).

HOW THESE TESTS WERE WRITTEN. The Tester of P-4 wrote them from the acceptance criteria and the
interface, before the implementation existed, with the in-memory file system of tests/fakes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.application.usecases.bounded_read import (
    MAX_LOCK_BYTES,
    BoundedReadRefused,
    read_bounded,
)
from orqlet.domain.errors import OrqletError
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem

pytestmark = pytest.mark.unit

LOCK = CanonicalPath.parse(".orqlet/workflow.lock")


def _files_with_lock(content: bytes) -> MemoryFileSystem:
    files = MemoryFileSystem()
    files.write_atomic(LOCK, content)
    return files


def test_the_default_limit_is_one_mebibyte() -> None:
    """AC-4, ADR-004 decision 6: at most 1 MiB for each lock file."""
    assert MAX_LOCK_BYTES == 1_048_576


def test_a_refusal_is_an_orqlet_error() -> None:
    """The interface: `BoundedReadRefused` is an `OrqletError`."""
    assert issubclass(BoundedReadRefused, OrqletError)


def test_a_regular_file_is_read() -> None:
    """ADR-004 decision 5: one regular file is read as it is."""
    files = _files_with_lock(b"workflow_version: 0.5.0\n")

    assert read_bounded(files, LOCK) == b"workflow_version: 0.5.0\n"


def test_nothing_at_the_path_gives_none() -> None:
    """The interface: a missing file is `None`, not a refusal."""
    assert read_bounded(MemoryFileSystem(), LOCK) is None


def test_a_missing_parent_folder_gives_none() -> None:
    """The interface: nothing at the path, its folder missing too, is `None`."""
    files = MemoryFileSystem()
    files.make_dir(CanonicalPath.parse("other"))

    assert read_bounded(files, LOCK) is None


def test_a_link_at_the_path_is_refused() -> None:
    """AC-4, ADR-001 decision 3, ADR-004 decision 5: a link is never read."""
    files = MemoryFileSystem()
    files.add_symlink(str(LOCK))

    with pytest.raises(BoundedReadRefused):
        read_bounded(files, LOCK)


def test_a_link_above_the_path_is_refused() -> None:
    """AC-4, ADR-004 decision 5; the interface: a link above it (the port's LinkRefused) refuses."""
    files = MemoryFileSystem()
    files.add_symlink(".orqlet")

    with pytest.raises(BoundedReadRefused):
        read_bounded(files, LOCK)


def test_a_directory_at_the_path_is_refused() -> None:
    """ADR-004 decision 5; the interface: only a regular file is read."""
    files = MemoryFileSystem()
    files.make_dir(LOCK)

    with pytest.raises(BoundedReadRefused):
        read_bounded(files, LOCK)


def test_exactly_the_default_limit_is_read() -> None:
    """AC-4, ADR-004 decision 6; the interface: exactly `limit` bytes is accepted."""
    content = b"x" * MAX_LOCK_BYTES

    assert read_bounded(_files_with_lock(content), LOCK) == content


def test_one_byte_over_the_default_limit_is_refused() -> None:
    """AC-4: a lock file over 1 MiB gives no project version."""
    files = _files_with_lock(b"x" * (MAX_LOCK_BYTES + 1))

    with pytest.raises(BoundedReadRefused):
        read_bounded(files, LOCK)


def test_a_smaller_limit_is_honoured_at_its_boundary() -> None:
    """The interface: `limit` bounds the read; exactly `limit` passes, one more byte fails."""
    assert read_bounded(_files_with_lock(b"0123456789"), LOCK, limit=10) == b"0123456789"

    with pytest.raises(BoundedReadRefused):
        read_bounded(_files_with_lock(b"0123456789A"), LOCK, limit=10)


def test_reading_changes_nothing() -> None:
    """ADR-004 decision 6: no writes."""
    files = _files_with_lock(b"workflow_version: 0.5.0\n")
    before = files.snapshot()

    read_bounded(files, LOCK)

    assert files.snapshot() == before


class _PrefixSpy(MemoryFileSystem):
    def __init__(self) -> None:
        super().__init__()
        self.limits: list[int] = []

    def read_prefix(self, path: CanonicalPath, limit: int) -> bytes:
        self.limits.append(limit)
        return super().read_prefix(path, limit)


def test_an_oversized_file_is_not_read_past_the_limit() -> None:
    """Architecture review of P-4, ADR-004 decision 6: the size is bounded by the read itself."""
    files = _PrefixSpy()
    files.write_atomic(LOCK, b"x" * 100)

    with pytest.raises(BoundedReadRefused):
        read_bounded(files, LOCK, limit=10)

    assert files.limits == [11]


def test_the_local_file_system_reads_no_more_than_the_prefix(tmp_path: Path) -> None:
    """Code review of P-4, round 3: the adapter itself stops at the limit, not only the fake."""
    (tmp_path / "big").write_bytes(b"x" * 64)

    assert LocalFileSystem(tmp_path).read_prefix(CanonicalPath.parse("big"), 10) == b"x" * 10
