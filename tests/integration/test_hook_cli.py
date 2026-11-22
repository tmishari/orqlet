"""`orqlet hook` through the real CLI: exit statuses, output and the no-write rule (P-5).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-5 in
docs/design/one-command-setup/plan.yaml; BC-n, K-11 and the failures table are in
docs/design/one-command-setup/design/component.md; ADR-004 is
docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md; "the interface" is the one
that the Coder gave for P-5 (`orqlet hook EVENT --client CLIENT`, the payload on standard input,
one JSON line on standard output, `build_hook_services()` in the composition root).

HOW THESE TESTS WERE WRITTEN. The Tester of P-5 wrote them before the implementation existed. The
autouse fixture of tests/conftest.py gives every test a temporary HOME and ORQLET_DATA_DIR; the
hook compares paths with the real home path, so every temporary path is resolved first.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.foundation import compose_foundation
from orqlet.application.usecases.hook_event import HookServices
from orqlet.domain.strict_json import MAX_PAYLOAD_BYTES
from orqlet.interface.cli.app import app
from orqlet.interface.cli.commands import hook as hook_module

pytestmark = [pytest.mark.integration]

RUNNER = CliRunner()
GENERATED = ".claude/skills/orqlet/SKILL.md"
SHA = "0" * 64


def _home() -> Path:
    return Path(os.path.realpath(os.environ["HOME"]))


def _data() -> Path:
    return Path(os.environ["ORQLET_DATA_DIR"])


def _project() -> Path:
    """An initialized project below the temporary home, with a generated file in its lock."""
    project = _home() / "work" / "repo"
    (project / ".orqlet").mkdir(parents=True)
    (project / "src").mkdir()
    version = str(PackagedWorkflow().release.version)
    (project / ".orqlet" / "workflow.lock").write_text(
        f'workflow_id: orqlet\nworkflow_version: "{version}"\n', encoding="utf-8"
    )
    lock = {
        "schema": "orqlet.generated-lock/v1",
        "generator": {"orqlet": version},
        "files": [
            {"path": GENERATED, "owner": "orqlet", "class": "protected", "rendered_sha256": SHA}
        ],
    }
    (project / ".orqlet" / "generated.lock.yaml").write_text(json.dumps(lock), encoding="utf-8")
    generated = project / GENERATED
    generated.parent.mkdir(parents=True)
    generated.write_text("rendered\n", encoding="utf-8")
    return project


def _session(folder: Path) -> bytes:
    return json.dumps({"cwd": str(folder)}).encode()


def _edit(project: Path) -> bytes:
    return json.dumps(
        {"cwd": str(project), "tool_input": {"file_path": str(project / GENERATED)}}
    ).encode()


def run_hook(event: str, client: str, payload: bytes | None) -> tuple[int, str]:
    result = RUNNER.invoke(app, ["hook", event, "--client", client], input=payload)
    return result.exit_code, result.stdout


def _one_object(stdout: str) -> dict[str, object]:
    """The output is one JSON object on one line."""
    assert stdout.endswith("\n")
    assert stdout.count("\n") == 1
    parsed = json.loads(stdout)
    assert isinstance(parsed, dict)
    return parsed


def tree_state(folder: Path) -> set[tuple[str, int, int]]:
    """Every path below `folder` with its size and mode, links not followed."""
    found = set()
    for path in folder.rglob("*"):
        info = path.lstat()
        found.add((path.relative_to(folder).as_posix(), info.st_size, info.st_mode))
    return found


def test_hook_is_an_implemented_command() -> None:
    """AC-14, EC-1, Q-53: `IMPLEMENTED_COMMANDS` lists `hook` (the equality test is unchanged)."""
    assert "hook" in IMPLEMENTED_COMMANDS


def test_session_start_end_to_end() -> None:
    """AC-3, BC-14, ADR-004 decision 1: the status of the project, in the Claude Code shape."""
    project = _project()
    version = str(PackagedWorkflow().release.version)

    code, stdout = run_hook("session-start", "claude-code", _session(project))

    assert code == 0
    output = _one_object(stdout)
    specific = output["hookSpecificOutput"]
    assert isinstance(specific, dict)
    assert specific["hookEventName"] == "SessionStart"
    context = specific["additionalContext"]
    assert isinstance(context, str)
    assert context.splitlines() == [
        "Orqlet status for this project. It is advisory: the person starts every Orqlet command, "
        "and `orqlet status` gives the full report.",
        f"- Installed workflow version: {version}",
        f"- Project workflow version: {version}",
        "- Next step: `install-global`",
    ]


def test_session_start_from_cursor_end_to_end() -> None:
    """AC-2, AC-3, ADR-004 decision 5: Cursor's first workspace root, in Cursor's shape."""
    project = _project()
    payload = {"workspace_roots": [str(project / "src")], "cursor_version": "2.9.0"}

    code, stdout = run_hook("session-start", "cursor", json.dumps(payload).encode())

    assert code == 0
    output = _one_object(stdout)
    assert list(output) == ["additional_context"]
    assert "- Next step: `install-global`" in str(output["additional_context"])


def test_post_edit_end_to_end() -> None:
    """AC-7, BC-15, ADR-004 decisions 1 and 1a: one advisory line in the PostToolUse shape."""
    project = _project()

    code, stdout = run_hook("post-edit", "claude-code", _edit(project))

    assert code == 0
    assert _one_object(stdout) == {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"Generated file edited: `{GENERATED}`. Orqlet writes this file, so change its "
                "source and run `orqlet upgrade` instead of editing it by hand."
            ),
        }
    }


def test_copilot_outside_the_home_gets_the_packaged_foundation(tmp_path: Path) -> None:
    """AC-4, BC-14, ADR-004 decision 5: a working folder outside the home: the foundation only."""
    outside = Path(os.path.realpath(tmp_path)) / "elsewhere"
    outside.mkdir()
    (outside / "AGENTS.md").write_text("<!-- orqlet:begin baseline x -->\n", encoding="utf-8")

    code, stdout = run_hook("session-start", "copilot", _session(outside))

    assert code == 0
    assert _one_object(stdout) == {"additionalContext": compose_foundation(PackagedWorkflow())}


BAD_PAYLOADS: dict[str, bytes | None] = {
    "missing": None,
    "empty": b"",
    "not JSON": b"{",
    "a list": b"[]",
    "a duplicate key": b'{"cwd": "/a", "cwd": "/b"}',
    "NaN": b'{"cwd": "/a", "n": NaN}',
    "not UTF-8": b'{"cwd": "\xff"}',
    "over 1 MiB": b'{"cwd": "/a"}' + b" " * MAX_PAYLOAD_BYTES,
}


@pytest.mark.parametrize("payload", list(BAD_PAYLOADS.values()), ids=list(BAD_PAYLOADS))
@pytest.mark.parametrize("event", ["session-start", "post-edit"])
def test_a_bad_payload_exits_0_with_an_empty_object(payload: bytes | None, event: str) -> None:
    """AC-9, BC-14, ADR-004 decision 2: a malformed, oversized or missing payload: exit 0, `{}`."""
    _project()

    code, stdout = run_hook(event, "claude-code", payload)

    assert code == 0
    assert _one_object(stdout) == {}


def test_an_unexpected_error_exits_0_with_an_empty_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-9, ADR-004 decision 2: on its own error the hook returns no context and exits 0."""
    project = _project()

    def broken() -> HookServices:
        raise RuntimeError("unexpected")

    monkeypatch.setattr(hook_module, "build_hook_services", broken)

    code, stdout = run_hook("session-start", "claude-code", _session(project))

    assert code == 0
    assert _one_object(stdout) == {}


@pytest.mark.parametrize(
    "args",
    [
        ["hook", "pre-tool", "--client", "claude-code"],
        ["hook", "session-start", "--client", "vim"],
        ["hook", "post-edit", "--client", "vim"],
        ["hook", "session-start"],
        ["hook"],
    ],
    ids=["unknown event", "unknown client", "unknown client at post-edit", "no client", "no event"],
)
def test_a_usage_error_exits_2(args: list[str]) -> None:
    """AC-9, BC-40, ADR-004 decision 2: an unknown event or client is a usage error, exit 2."""
    result = RUNNER.invoke(app, args, input=b"{}")

    assert result.exit_code == 2


def test_neither_hook_creates_a_file_or_folder() -> None:
    """AC-11, BC-15, K-11: paths, sizes and modes under the home, project and data folder hold."""
    project = _project()
    data = _data()
    (data / "user").mkdir(parents=True)
    manifest = {
        "schema": "orqlet.user-manifest/v1",
        "change_id": "c-1",
        "created_at": "2026-11-22T10:00:00Z",
        "roots": {},
        "entries": [],
    }
    (data / "user" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    user = data.parent
    before = (tree_state(_home()), tree_state(project), tree_state(user))
    session = json.dumps({"cwd": str(project), "workspace_roots": [str(project)]}).encode()

    for client in ("claude-code", "codex", "cursor", "copilot"):
        assert run_hook("session-start", client, session)[0] == 0
        assert run_hook("post-edit", client, _edit(project))[0] == 0

    assert (tree_state(_home()), tree_state(project), tree_state(user)) == before


def test_neither_hook_creates_the_data_folder() -> None:
    """AC-11, K-11: a missing data directory stays missing."""
    project = _project()
    data = _data()
    assert not data.exists()

    for client in ("claude-code", "copilot"):
        assert run_hook("session-start", client, _session(project))[0] == 0
        assert run_hook("post-edit", client, _edit(project))[0] == 0

    assert not data.exists()
