"""Behaviour every `FileSystem` implementation must share."""

from __future__ import annotations

from pathlib import Path

import pytest

from orqlet.application.ports.filesystem import (
    FileKind,
    FileSystem,
    FileSystemError,
    NotARegularFile,
    PathNotFound,
)
from orqlet.domain.paths import CanonicalPath
from tests.contract.factories import FILESYSTEMS

pytestmark = pytest.mark.contract


def p(text: str) -> CanonicalPath:
    return CanonicalPath.parse(text)


@pytest.fixture(params=sorted(FILESYSTEMS))
def fs(request: pytest.FixtureRequest, tmp_path: Path) -> FileSystem:
    return FILESYSTEMS[request.param](tmp_path)


def test_missing_path_has_no_kind(fs: FileSystem) -> None:
    assert fs.kind(p("nothing/here")) is None


def test_write_then_read_round_trips_and_creates_parents(fs: FileSystem) -> None:
    fs.write_atomic(p("a/b/c.txt"), b"hello")

    assert fs.read_bytes(p("a/b/c.txt")) == b"hello"
    assert fs.kind(p("a/b/c.txt")) is FileKind.FILE
    assert fs.kind(p("a/b")) is FileKind.DIRECTORY


def test_write_replaces_existing_content(fs: FileSystem) -> None:
    fs.write_atomic(p("f"), b"one")
    fs.write_atomic(p("f"), b"two")

    assert fs.read_bytes(p("f")) == b"two"


def test_bytes_are_stored_unchanged(fs: FileSystem) -> None:
    data = b"line1\r\nline2\n\x00\xff"
    fs.write_atomic(p("raw.bin"), data)

    assert fs.read_bytes(p("raw.bin")) == data


def test_read_missing_raises_path_not_found(fs: FileSystem) -> None:
    with pytest.raises(PathNotFound):
        fs.read_bytes(p("missing"))


def test_read_directory_raises_not_a_regular_file(fs: FileSystem) -> None:
    fs.make_dir(p("d"))

    with pytest.raises(NotARegularFile):
        fs.read_bytes(p("d"))


def test_write_onto_directory_is_refused(fs: FileSystem) -> None:
    fs.make_dir(p("d"))

    with pytest.raises(NotARegularFile):
        fs.write_atomic(p("d"), b"x")


def test_write_under_a_file_is_refused(fs: FileSystem) -> None:
    fs.write_atomic(p("f"), b"x")

    with pytest.raises(FileSystemError):
        fs.write_atomic(p("f/child"), b"y")


def test_delete_removes_a_file_and_ignores_a_missing_one(fs: FileSystem) -> None:
    fs.write_atomic(p("f"), b"x")

    fs.delete(p("f"))
    fs.delete(p("f"))

    assert fs.kind(p("f")) is None


def test_list_dir_is_sorted_and_names_only(fs: FileSystem) -> None:
    fs.write_atomic(p("d/b.txt"), b"")
    fs.write_atomic(p("d/a.txt"), b"")
    fs.write_atomic(p("d/sub/deep.txt"), b"")

    assert fs.list_dir(p("d")) == ("a.txt", "b.txt", "sub")


def test_list_dir_of_root_uses_none(fs: FileSystem) -> None:
    fs.write_atomic(p("z.txt"), b"")
    fs.write_atomic(p("a/x"), b"")

    assert fs.list_dir(None) == ("a", "z.txt")


def test_list_dir_of_missing_directory_raises(fs: FileSystem) -> None:
    with pytest.raises(PathNotFound):
        fs.list_dir(p("missing"))


def test_make_dir_is_idempotent(fs: FileSystem) -> None:
    fs.make_dir(p("x/y"))
    fs.make_dir(p("x/y"))

    assert fs.kind(p("x/y")) is FileKind.DIRECTORY


def test_remove_empty_dir_only_removes_empty_directories(fs: FileSystem) -> None:
    fs.make_dir(p("empty"))
    fs.write_atomic(p("full/f"), b"x")

    fs.remove_empty_dir(p("empty"))
    fs.remove_empty_dir(p("full"))
    fs.remove_empty_dir(p("absent"))

    assert fs.kind(p("empty")) is None
    assert fs.kind(p("full")) is FileKind.DIRECTORY
