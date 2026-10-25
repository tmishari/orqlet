"""`--update-golden` rewrites golden files locally and is refused in CI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
TARGET = "tests/unit/render/test_clients_golden.py::test_rendering_twice_gives_identical_bytes"


def run_pytest(*args: str, env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"CI", "GITHUB_ACTIONS"}}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_update_flag_is_refused_when_running_in_ci() -> None:
    result = run_pytest("--update-golden", TARGET, env_extra={"CI": "true"})

    assert result.returncode != 0
    assert "refused in CI" in result.stdout + result.stderr


def test_the_update_flag_is_refused_on_github_actions_too() -> None:
    result = run_pytest("--update-golden", TARGET, env_extra={"GITHUB_ACTIONS": "true"})

    assert result.returncode != 0
