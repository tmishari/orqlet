"""The per-client hook payload contract (task one-command-setup, phase P-5, AC-2).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-5 in
docs/design/one-command-setup/plan.yaml; BC-14 to BC-16 are in
docs/design/one-command-setup/design/component.md; ADR-004 decisions 4 and 5 are in
docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md; "the interface" is the one
that the Coder gave for P-5 (`orqlet.application.contracts.hook_payload`: `HookPayloadError`,
`HookFields`, `read_hook_fields(client, document)`).

HOW THESE TESTS WERE WRITTEN. The Tester of P-5 wrote them from the acceptance criteria and the
interface, before the implementation existed. The contract reads fields and types only: whether a
folder is absolute or inside the home is judged by the use case (tests/unit/application/
test_hook_event.py), so a relative value is returned here as it is.
"""

from __future__ import annotations

import dataclasses

import pytest

from orqlet.application.contracts.common import RenderClientId
from orqlet.application.contracts.hook_payload import (
    HookFields,
    HookPayloadError,
    read_hook_fields,
)
from orqlet.domain.errors import OrqletError

pytestmark = pytest.mark.unit

ROOT = "/home/person/work/repo"
EDITED = f"{ROOT}/.claude/skills/orqlet/SKILL.md"
CWD_CLIENTS: tuple[RenderClientId, ...] = ("claude-code", "codex", "copilot")
ALL_CLIENTS: tuple[RenderClientId, ...] = ("claude-code", "codex", "copilot", "cursor")


def test_the_error_is_an_orqlet_error() -> None:
    """The interface: `HookPayloadError` derives from `OrqletError`."""
    assert issubclass(HookPayloadError, OrqletError)


def test_the_fields_are_frozen() -> None:
    """The interface: `HookFields` is a frozen dataclass."""
    fields = HookFields(working_folder=ROOT, edited_path=None, from_cursor=False)

    with pytest.raises(dataclasses.FrozenInstanceError):
        fields.working_folder = "/elsewhere"  # type: ignore[misc]


# --- the working folder (AC-2, ADR-004 decision 5) --------------------------------------------


@pytest.mark.parametrize("client", CWD_CLIENTS)
def test_the_working_folder_is_cwd_for_claude_codex_and_copilot(client: RenderClientId) -> None:
    """AC-2, ADR-004 decision 5, K-12: `cwd` for Claude Code, Codex and Copilot."""
    fields = read_hook_fields(client, {"cwd": ROOT, "workspace_roots": ["/elsewhere"]})

    assert fields.working_folder == ROOT


def test_the_working_folder_is_the_first_workspace_root_for_cursor() -> None:
    """AC-2, ADR-004 decision 5, K-12: the first `workspace_roots` element for Cursor."""
    fields = read_hook_fields("cursor", {"workspace_roots": [ROOT, "/elsewhere"], "cwd": "/x"})

    assert fields.working_folder == ROOT


@pytest.mark.parametrize(
    "document",
    [{}, {"workspace_roots": []}, {"cwd": ROOT}],
    ids=["missing", "empty list", "only cwd"],
)
def test_cursor_without_workspace_roots_has_no_working_folder(document: dict[str, object]) -> None:
    """AC-2, ADR-004 decision 5: Cursor's folder comes only from `workspace_roots`."""
    assert read_hook_fields("cursor", document).working_folder is None


@pytest.mark.parametrize("client", CWD_CLIENTS)
def test_a_missing_cwd_gives_no_working_folder(client: RenderClientId) -> None:
    """AC-2, ADR-004 decision 5: a missing value gives no folder (and so no context)."""
    assert read_hook_fields(client, {"session_id": "s-1"}).working_folder is None


@pytest.mark.parametrize("client", CWD_CLIENTS)
def test_a_relative_cwd_is_returned_as_it_is(client: RenderClientId) -> None:
    """The interface: relativeness is judged by the use case, not by the contract."""
    assert read_hook_fields(client, {"cwd": "work/repo"}).working_folder == "work/repo"


@pytest.mark.parametrize("client", CWD_CLIENTS)
@pytest.mark.parametrize(
    "value", [5, ["/a"], {"path": "/a"}, True], ids=["int", "list", "object", "bool"]
)
def test_a_cwd_that_is_not_a_string_is_refused(client: RenderClientId, value: object) -> None:
    """AC-2, BC-14; the interface: a known field with the wrong type is a payload error."""
    with pytest.raises(HookPayloadError):
        read_hook_fields(client, {"cwd": value})


@pytest.mark.parametrize(
    "value",
    [ROOT, {"0": ROOT}, [1], [ROOT, 2], [[ROOT]]],
    ids=["a string", "an object", "an int element", "a mixed list", "a nested list"],
)
def test_workspace_roots_that_are_not_a_list_of_strings_are_refused(value: object) -> None:
    """AC-2, BC-14; the interface: `workspace_roots` must be a list of strings."""
    with pytest.raises(HookPayloadError):
        read_hook_fields("cursor", {"workspace_roots": value})


# --- the edited path (AC-2, BC-15) ------------------------------------------------------------


def test_the_edited_path_is_claude_code_tool_input_file_path() -> None:
    """AC-2, BC-15, ADR-004 decision 5: the post-edit path is `tool_input.file_path`."""
    fields = read_hook_fields("claude-code", {"cwd": ROOT, "tool_input": {"file_path": EDITED}})

    assert fields == HookFields(working_folder=ROOT, edited_path=EDITED, from_cursor=False)


@pytest.mark.parametrize("client", ["codex", "copilot", "cursor"])
def test_no_other_client_has_an_edited_path(client: RenderClientId) -> None:
    """AC-2, ADR-004 decision 1: only Claude Code's post-tool path is cited; others give None."""
    document = {"cwd": ROOT, "workspace_roots": [ROOT], "tool_input": {"file_path": EDITED}}

    assert read_hook_fields(client, document).edited_path is None


@pytest.mark.parametrize(
    "document",
    [{"cwd": ROOT}, {"cwd": ROOT, "tool_input": {}}, {"cwd": ROOT, "tool_input": {"x": 1}}],
    ids=["no tool_input", "empty tool_input", "no file_path"],
)
def test_a_missing_file_path_gives_no_edited_path(document: dict[str, object]) -> None:
    """AC-2; the interface: a missing field gives None."""
    assert read_hook_fields("claude-code", document).edited_path is None


@pytest.mark.parametrize("tool_input", [EDITED, [EDITED], 5], ids=["a string", "a list", "an int"])
def test_a_tool_input_that_is_not_an_object_is_refused(tool_input: object) -> None:
    """AC-2, BC-14; the interface: `tool_input` must be an object."""
    with pytest.raises(HookPayloadError):
        read_hook_fields("claude-code", {"cwd": ROOT, "tool_input": tool_input})


@pytest.mark.parametrize("file_path", [5, [EDITED], {"p": EDITED}], ids=["int", "list", "object"])
def test_a_file_path_that_is_not_a_string_is_refused(file_path: object) -> None:
    """AC-2, BC-14; the interface: `file_path` must be a string."""
    with pytest.raises(HookPayloadError):
        read_hook_fields("claude-code", {"cwd": ROOT, "tool_input": {"file_path": file_path}})


def test_a_relative_file_path_is_returned_as_it_is() -> None:
    """The interface: relativeness is judged by the use case, not by the contract."""
    fields = read_hook_fields("claude-code", {"tool_input": {"file_path": "src/app.py"}})

    assert fields.edited_path == "src/app.py"


# --- the duplicate-run filter (AC-2, AC-8, BC-16) ---------------------------------------------


@pytest.mark.parametrize("client", ALL_CLIENTS)
@pytest.mark.parametrize("value", ["2.9.0", None, 3], ids=["a version", "null", "a number"])
def test_cursor_version_marks_a_payload_from_cursor(client: RenderClientId, value: object) -> None:
    """AC-2, BC-16, ADR-004 decision 4; the interface: the key's presence, for every client."""
    document = {"cwd": ROOT, "workspace_roots": [ROOT], "cursor_version": value}

    assert read_hook_fields(client, document).from_cursor is True


@pytest.mark.parametrize("client", ALL_CLIENTS)
def test_without_cursor_version_the_payload_is_not_from_cursor(client: RenderClientId) -> None:
    """AC-2, BC-16; the interface: no `cursor_version` key, no duplicate-run filter."""
    document = {"cwd": ROOT, "workspace_roots": [ROOT], "cursor_versions": "2.9.0"}

    assert read_hook_fields(client, document).from_cursor is False


# --- unknown fields (AC-1, ADR-004 decision 6) ------------------------------------------------


@pytest.mark.parametrize("client", ALL_CLIENTS)
def test_unknown_fields_are_ignored(client: RenderClientId) -> None:
    """AC-1, ADR-004 decision 6: unknown fields, of any type, are ignored."""
    document = {
        "cwd": ROOT,
        "workspace_roots": [ROOT],
        "hook_event_name": 5,
        "session_id": ["x"],
        "transcript_path": {"a": None},
    }

    fields = read_hook_fields(client, document)

    assert fields.working_folder == ROOT
    assert fields.from_cursor is False
