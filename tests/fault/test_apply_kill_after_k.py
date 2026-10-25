"""Kill the apply after k of n files, for every k, on the real file system: it converges."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from orqlet.application.ports.filesystem import FileSystem
from orqlet.application.usecases.init_project import InitOptions, init_project
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import ReplayIds, SequentialIds
from tests.support.git import commit_file, make_repo
from tests.support.real_env import real_services, snapshot
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.fault,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

OPTIONS = InitOptions(assume_yes=True)


def project(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    commit_file(root, "NOTES.md", "keep me\n")
    return root


def crash_after(writes: int) -> Callable[[FileSystem], FileSystem]:
    def wrap(fs: FileSystem) -> FileSystem:
        return FaultyFileSystem(fs, crash_after_writes=writes)

    return wrap


def test_every_kill_point_converges_on_real_files(tmp_path: Path) -> None:
    clean_root = project(tmp_path, "clean")
    before = snapshot(clean_root)
    init_project(real_services(clean_root, tmp_path / "clean-data"), OPTIONS)
    expected = snapshot(clean_root)
    writes = len(expected) - len(before)
    assert writes > 10

    for crash_point in range(writes):
        root = project(tmp_path, f"crash-{crash_point}")
        data = tmp_path / f"data-{crash_point}"
        with pytest.raises(SimulatedCrash):
            init_project(
                real_services(
                    root,
                    data,
                    wrap_project=crash_after(crash_point),
                ),
                OPTIONS,
            )
        partial = snapshot(root)
        assert ".orqlet/generated.lock.yaml" not in partial
        assert not any(".orqlet-tmp-" in name for name in partial), "a temporary file was left"

        rerun = init_project(
            real_services(root, data, ids=ReplayIds(SequentialIds().new_id())), OPTIONS
        )

        assert rerun.status == "applied", crash_point
        assert snapshot(root) == expected, f"kill after {crash_point} writes did not converge"
