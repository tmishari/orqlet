"""The fields `orqlet hook` reads from a client's payload, per client (ADR-004 decisions 4 and 5).

Only the fields the plan cites for each client are read (K-12); every other field is ignored, so a
client that adds one does not break the hook. A cited field with the wrong type makes the whole
payload an error. Whether a path is absolute, or inside the home, is judged by the use case.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from orqlet.application.contracts.common import RenderClientId
from orqlet.domain.errors import OrqletError


class HookPayloadError(OrqletError):
    """A cited field of the payload has the wrong type."""


@dataclass(frozen=True, slots=True)
class HookFields:
    working_folder: str | None
    edited_path: str | None  # the post-edit path; only Claude Code's is cited
    from_cursor: bool  # the payload carries `cursor_version`: Cursor sent it (ADR-004 decision 4)


def read_hook_fields(client: RenderClientId, document: Mapping[str, object]) -> HookFields:
    """The cited fields of `document` for `client`; a missing field is `None`."""
    if client == "cursor":
        roots = _string_list(document, "workspace_roots")
        folder = roots[0] if roots else None
    else:
        folder = _string(document, "cwd")
    edited = _edited_path(document) if client == "claude-code" else None
    return HookFields(folder, edited, "cursor_version" in document)


def _edited_path(document: Mapping[str, object]) -> str | None:
    tool_input = document.get("tool_input")
    if tool_input is None:
        return None
    if not isinstance(tool_input, Mapping):
        raise HookPayloadError("tool_input is not an object")
    return _string(tool_input, "file_path")


def _string(document: Mapping[str, object], key: str) -> str | None:
    value = document.get(key)
    if value is not None and not isinstance(value, str):
        raise HookPayloadError(f"{key} is not a string")
    return value


def _string_list(document: Mapping[str, object], key: str) -> list[str] | None:
    value = document.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise HookPayloadError(f"{key} is not a list of strings")
    return value
