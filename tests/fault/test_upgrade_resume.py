"""Kill an upgrade after k of n files on real files, for every k: `--resume` converges (FM-U03)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from orqlet.application.usecases.diagnose import doctor
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import SequentialIds
from tests.fakes.workflow import PINNED, ChangedWorkflow
from tests.support.git import make_repo
from tests.support.real_env import real_services, snapshot
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.fault,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

NEXT = ChangedWorkflow(PINNED, version="0.2.0")


def initialised(tmp_path: Path, name: str) -> tuple[Path, Path]:
    root = tmp_path / name / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    data = tmp_path / f"data-{name}"
    init_project(real_services(root, data), InitOptions(assume_yes=True))
    return root, data


def crash_after(writes: int):  # type: ignore[no-untyped-def]
    return lambda fs: FaultyFileSystem(fs, crash_after_writes=writes)


def test_every_kill_point_of_an_upgrade_converges_and_doctor_flags_the_gap(tmp_path: Path) -> None:
    clean, clean_data = initialised(tmp_path, "clean")
    result = upgrade(
        real_services(clean, clean_data, workflow=NEXT, ids=SequentialIds(start=100)),
        UpgradeOptions(assume_yes=True),
    )
    expected = snapshot(clean)
    assert result.plan is not None
    writes = len(result.plan.writes)
    assert writes >= 5

    for crash_point in range(writes):
        root, data = initialised(tmp_path, f"crash-{crash_point}")
        with pytest.raises(SimulatedCrash):
            upgrade(
                real_services(
                    root,
                    data,
                    workflow=NEXT,
                    wrap_project=crash_after(crash_point),
                    ids=SequentialIds(start=100),
                ),
                UpgradeOptions(assume_yes=True),
            )
        assert not any(".orqlet-tmp-" in name for name in snapshot(root))
        errors = {
            f.code
            for f in doctor(real_services(root, data, workflow=NEXT)).findings
            if f.severity.value == "error"
        }
        assert "ORQ-E170" in errors, "doctor must flag the interrupted change"

        resumed = upgrade(
            real_services(root, data, workflow=NEXT, ids=SequentialIds(start=500)),
            UpgradeOptions(assume_yes=True, resume=True),
        )

        assert resumed.status == "applied", crash_point
        assert snapshot(root) == expected, f"kill after {crash_point} writes did not converge"
        assert not [
            f
            for f in doctor(real_services(root, data, workflow=NEXT)).findings
            if f.severity.value == "error"
        ]
