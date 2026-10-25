"""Only one process applies a change to a project at a time."""

from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path

import pytest
from typer.testing import CliRunner

from orqlet.adapters.fs.apply_lock import FileApplyLock
from orqlet.application.ports.lock import ApplyBusy
from orqlet.interface.cli.app import app
from tests.support.git import clean_environ, git, make_repo
from tests.support.real_env import snapshot
from tests.support.trees import FIXTURES

pytestmark = pytest.mark.integration


def test_a_second_holder_waits_a_bounded_time_and_then_gets_a_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "locks" / "apply.lock"
    first = FileApplyLock(path, timeout_seconds=5)
    second = FileApplyLock(path, timeout_seconds=0.2)

    with first.hold(), pytest.raises(ApplyBusy, match="Another Orqlet process"), second.hold():
        pass


def test_the_lock_is_released_when_the_holder_fails(tmp_path: Path) -> None:
    lock = FileApplyLock(tmp_path / "apply.lock", timeout_seconds=1)

    with pytest.raises(RuntimeError), lock.hold():
        raise RuntimeError("boom")

    with lock.hold():
        pass  # free again


def test_two_threads_never_hold_it_together(tmp_path: Path) -> None:
    path = tmp_path / "apply.lock"
    inside = 0
    peak = 0
    guard = threading.Lock()

    def work() -> None:
        nonlocal inside, peak
        with FileApplyLock(path, timeout_seconds=10).hold():
            with guard:
                inside += 1
                peak = max(peak, inside)
            threading.Event().wait(0.05)
            with guard:
                inside -= 1

    threads = [threading.Thread(target=work) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert peak == 1


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_init_refuses_and_writes_nothing_while_another_process_holds_the_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "userdata"
    monkeypatch.setenv("ORQLET_DATA_DIR", str(data))
    for name, value in clean_environ(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "w" / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "initial")
    before = snapshot(root)
    # The project id is not known before init runs, so hold every project lock that appears.
    monkeypatch.setattr("orqlet.adapters.fs.apply_lock.FileLock", _busy_lock)

    result = CliRunner().invoke(app, ["init", "--root", str(root), "--yes", "--json"])

    document = json.loads(result.stdout)
    assert result.exit_code == 3
    assert any(f["code"] == "ORQ-E137" for f in document["findings"])
    assert snapshot(root) == before


def _busy_lock(*_args: object, **_kwargs: object) -> _AlwaysBusy:
    return _AlwaysBusy()


class _AlwaysBusy:
    def acquire(self) -> None:
        from filelock import Timeout

        raise Timeout("busy")

    def release(self) -> None:  # pragma: no cover - never acquired
        raise AssertionError("released a lock that was never held")
