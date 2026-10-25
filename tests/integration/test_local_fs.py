"""`LocalFileSystem` against a real temporary directory: links, atomicity and file modes."""

from __future__ import annotations

import os
import stat
import sys
import time
from pathlib import Path

import pytest

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.application.ports.filesystem import FileKind, LinkRefused
from orqlet.domain.paths import CanonicalPath

pytestmark = pytest.mark.integration


def p(text: str) -> CanonicalPath:
    return CanonicalPath.parse(text)


def make_link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot create symbolic links")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    directory = tmp_path / "project"
    directory.mkdir()
    return directory


def test_root_must_exist_and_be_a_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        LocalFileSystem(tmp_path / "absent")
    (tmp_path / "file").write_text("x")
    with pytest.raises(Exception, match="not a directory"):
        LocalFileSystem(tmp_path / "file")


def test_a_symlinked_file_is_reported_as_a_symlink_and_refused(root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    make_link(root / "link.txt", outside)
    fs = LocalFileSystem(root)

    assert fs.kind(p("link.txt")) is FileKind.SYMLINK
    with pytest.raises(LinkRefused):
        fs.read_bytes(p("link.txt"))
    with pytest.raises(LinkRefused):
        fs.write_atomic(p("link.txt"), b"overwrite")
    with pytest.raises(LinkRefused):
        fs.delete(p("link.txt"))
    assert outside.read_text() == "secret"


def test_nothing_is_read_or_written_below_a_symlinked_directory(root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "inside.txt").write_text("x")
    make_link(root / "dir", outside)
    fs = LocalFileSystem(root)

    with pytest.raises(LinkRefused):
        fs.kind(p("dir/inside.txt"))
    with pytest.raises(LinkRefused):
        fs.read_bytes(p("dir/inside.txt"))
    with pytest.raises(LinkRefused):
        fs.write_atomic(p("dir/new.txt"), b"x")
    with pytest.raises(LinkRefused):
        fs.make_dir(p("dir/sub"))
    assert not (outside / "new.txt").exists()


def test_a_failed_replace_leaves_the_old_content_and_no_temporary_file(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fs = LocalFileSystem(root)
    fs.write_atomic(p("f.txt"), b"old")

    def failing_replace(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(OSError, match="disk full"):
        fs.write_atomic(p("f.txt"), b"new")
    monkeypatch.undo()

    assert fs.read_bytes(p("f.txt")) == b"old"
    assert sorted(entry.name for entry in root.iterdir()) == ["f.txt"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_replacing_a_file_keeps_its_executable_bit(root: Path) -> None:
    fs = LocalFileSystem(root)
    fs.write_atomic(p("run.sh"), b"#!/bin/sh\n")
    (root / "run.sh").chmod(0o755)

    fs.write_atomic(p("run.sh"), b"#!/bin/sh\necho hi\n")

    assert stat.S_IMODE((root / "run.sh").stat().st_mode) == 0o755


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_new_files_are_readable_by_everyone_not_private_temp_files(root: Path) -> None:
    fs = LocalFileSystem(root)
    fs.write_atomic(p("new.txt"), b"x")

    assert stat.S_IMODE((root / "new.txt").stat().st_mode) == 0o644


def test_a_file_that_is_not_regular_is_refused(root: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("no named pipes on this platform")
    os.mkfifo(root / "pipe")
    fs = LocalFileSystem(root)

    assert fs.kind(p("pipe")) is FileKind.OTHER
    with pytest.raises(Exception, match="pipe"):
        fs.read_bytes(p("pipe"))


def test_replace_is_retried_on_windows_only_a_bounded_number_of_times(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from orqlet.adapters.fs import local_fs

    calls: list[int] = []
    real_replace = os.replace

    def flaky_replace(source: str, target: Path) -> None:
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("in use")
        real_replace(source, target)

    monkeypatch.setattr(local_fs, "_IS_WINDOWS", True)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(os, "replace", flaky_replace)

    LocalFileSystem(root).write_atomic(p("f.txt"), b"x")

    assert len(calls) == 3
    assert (root / "f.txt").read_bytes() == b"x"


def test_replace_gives_up_after_the_bounded_attempts(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from orqlet.adapters.fs import local_fs

    def always_busy(_source: str, _target: Path) -> None:
        raise PermissionError("in use")

    monkeypatch.setattr(local_fs, "_IS_WINDOWS", True)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(os, "replace", always_busy)

    with pytest.raises(PermissionError):
        LocalFileSystem(root).write_atomic(p("f.txt"), b"x")
    assert [e.name for e in root.iterdir()] == []  # no temporary file is left behind


def test_replace_is_not_retried_on_other_platforms(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from orqlet.adapters.fs import local_fs

    calls: list[int] = []

    def busy(_source: str, _target: Path) -> None:
        calls.append(1)
        raise PermissionError("denied")

    monkeypatch.setattr(local_fs, "_IS_WINDOWS", False)
    monkeypatch.setattr(os, "replace", busy)

    with pytest.raises(PermissionError):
        LocalFileSystem(root).write_atomic(p("f.txt"), b"x")
    assert len(calls) == 1
