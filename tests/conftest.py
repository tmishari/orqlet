"""Shared pytest configuration and the golden-file fixture."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings

# Property tests set an explicit budget: Hypothesis's default per-example deadline is 200 ms,
# which is too tight for the slowest CI runner.
settings.register_profile(
    "orqlet",
    max_examples=100,
    deadline=1000,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("orqlet")

GOLDEN_ROOT = Path(__file__).resolve().parent / "golden"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Rewrite golden files from the current output. Refused in CI.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Refuse `--update-golden` in CI before any test runs, whichever tests were selected."""
    if config.getoption("--update-golden") and _running_in_ci():
        raise pytest.UsageError(
            "--update-golden is refused in CI; update golden files locally and commit them"
        )


def _running_in_ci() -> bool:
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


@pytest.fixture
def golden(request: pytest.FixtureRequest) -> Callable[[str, bytes], None]:
    """Compare bytes with a golden file, or rewrite it with `--update-golden` outside CI.

    Every change to generated output therefore shows up as a diff of a committed file that a
    reviewer reads. In CI the flag is refused, so a golden file can never be silently refreshed.
    """
    update = bool(request.config.getoption("--update-golden"))

    def check(relative: str, content: bytes) -> None:
        target = GOLDEN_ROOT / relative
        if update:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return
        if not target.exists():
            pytest.fail(f"missing golden file {relative}; run pytest --update-golden and review it")
        expected = target.read_bytes()
        assert content == expected, f"{relative} differs from its golden file"

    return check
