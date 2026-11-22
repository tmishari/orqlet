"""The hook's time budget and its process-free services (task one-command-setup, P-5, AC-10).

Every test cites its `expected_behavior_source`: AC-10 is an acceptance criterion of phase P-5 in
docs/design/one-command-setup/plan.yaml; BC-17 and K-11 are in
docs/design/one-command-setup/design/component.md; ADR-004 decision 6 is in
docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md; Q-26 is in
docs/design/one-command-setup/questions.yaml; "the interface" is the one that the Coder gave for
P-5 (`build_hook_services()` in the composition root: no ProcessRunner or GitRunner, a home reader,
the data directory read-only, the 2-second deadline).

HOW THESE TESTS WERE WRITTEN. The Tester of P-5 wrote them before the implementation existed. The
tree is built under the temporary home of tests/conftest.py. Each hook is timed around the CLI
invocation with `time.monotonic`. The working folder sits at the bottom of the 64-level chain, and
the root is found from there: the search reads the start folder and 64 parents.
"""

from __future__ import annotations

import dataclasses
import json
import os
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.adapters.git.git_runner import GitRunner
from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.application.usecases.hook_event import HookServices
from orqlet.interface.cli.app import app
from orqlet.interface.cli.wiring import build_hook_services

pytestmark = [pytest.mark.integration]

RUNNER = CliRunner()
FILES = 10_000
DEPTH = 64
BUDGET_SECONDS = 2.0
GENERATED = ".claude/skills/orqlet/SKILL.md"
SHA = "0" * 64


def _large_project() -> tuple[Path, Path]:
    """10,000 files over a 64-level chain, `.orqlet/workflow.lock` at the top; (root, bottom)."""
    root = Path(os.path.realpath(os.environ["HOME"])) / "work" / "large"
    levels = [root]
    for level in range(DEPTH):
        levels.append(levels[-1] / f"level{level:02d}")
    levels[-1].mkdir(parents=True)
    (root / ".orqlet").mkdir()
    (root / ".orqlet" / "workflow.lock").write_text(
        'workflow_id: orqlet\nworkflow_version: "0.5.0"\n', encoding="utf-8"
    )
    lock = {
        "schema": "orqlet.generated-lock/v1",
        "generator": {"orqlet": "0.5.0"},
        "files": [
            {"path": GENERATED, "owner": "orqlet", "class": "protected", "rendered_sha256": SHA}
        ],
    }
    (root / ".orqlet" / "generated.lock.yaml").write_text(json.dumps(lock), encoding="utf-8")
    (root / GENERATED).parent.mkdir(parents=True)
    (root / GENERATED).write_text("rendered\n", encoding="utf-8")
    for index in range(FILES - 1):
        (levels[1 + index % DEPTH] / f"file{index:05d}.txt").write_bytes(b"x\n")
    return root, levels[-1]


def _timed(event: str, payload: dict[str, object]) -> tuple[float, int, str]:
    started = time.monotonic()
    result = RUNNER.invoke(
        app, ["hook", event, "--client", "claude-code"], input=json.dumps(payload).encode()
    )
    return time.monotonic() - started, result.exit_code, result.stdout


def test_the_tree_has_the_documented_size() -> None:
    """AC-10, BC-17: the fixture is 10,000 files and 64 levels deep."""
    root, bottom = _large_project()

    files = [path for path in root.rglob("*") if path.is_file()]

    assert len(files) >= FILES
    assert len(bottom.relative_to(root).parts) == DEPTH


def test_session_start_ends_within_two_seconds_on_a_large_tree() -> None:
    """AC-10, BC-17, Q-26, ADR-004 decision 6: session-start ends within 2 seconds."""
    _, bottom = _large_project()

    elapsed, code, stdout = _timed("session-start", {"cwd": str(bottom)})

    assert code == 0
    output = json.loads(stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "SessionStart"
    assert "Project workflow version: 0.5.0" in output["additionalContext"]
    assert elapsed < BUDGET_SECONDS


def test_post_edit_ends_within_two_seconds_on_a_large_tree() -> None:
    """AC-10, BC-17, Q-26, ADR-004 decision 6: post-edit ends within 2 seconds."""
    root, bottom = _large_project()
    payload: dict[str, object] = {
        "cwd": str(bottom),
        "tool_input": {"file_path": str(root / GENERATED)},
    }

    elapsed, code, stdout = _timed("post-edit", payload)

    assert code == 0
    output = json.loads(stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PostToolUse"
    assert f"`{GENERATED}`" in output["additionalContext"]
    assert elapsed < BUDGET_SECONDS


def _held(value: object) -> list[object]:
    """The value and, for a dataclass, every field value below it."""
    found = [value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            found += _held(getattr(value, field.name))
    return found


def test_the_hook_services_hold_no_process_runner_or_git() -> None:
    """AC-10, BC-17, ADR-004 decision 6: the hook services start no process and hold no Git."""
    services = build_hook_services()

    held = _held(services)

    assert isinstance(services, HookServices)
    assert not any(isinstance(item, SubprocessRunner | GitRunner | GitVcs) for item in held)
    for field in dataclasses.fields(HookServices):
        annotation = str(field.type)
        assert "ProcessRunner" not in annotation
        assert "GitRunner" not in annotation
        assert "Vcs" not in annotation


def test_the_hook_services_read_the_real_home_and_create_no_data_folder() -> None:
    """The interface, K-11: the home's real path, a reader of it, and no data directory made."""
    home = os.path.realpath(os.environ["HOME"])
    data = Path(os.environ["ORQLET_DATA_DIR"])

    services = build_hook_services()

    assert services.home.path == home
    assert isinstance(services.home_files, LocalFileSystem)
    assert services.home_files.root == Path(home)
    assert services.sources.user_data is None
    assert services.expired() is False
    assert not data.exists()


def test_the_hook_services_expire_two_seconds_after_they_are_built(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-10, ADR-004 decision 6: the internal deadline is 2 seconds from the start."""
    now = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])

    services = build_hook_services()

    now[0] = 100.0 + BUDGET_SECONDS
    assert services.expired() is False
    now[0] = 100.0 + BUDGET_SECONDS + 0.001
    assert services.expired() is True
