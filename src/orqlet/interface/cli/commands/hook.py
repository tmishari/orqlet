"""`orqlet hook EVENT --client C`: what a client runs at session start and after an edit (ADR-004).

The client, not a person, starts it with a JSON payload on standard input. It prints the client's
output object on one line and exits 0 whatever happens, so a hook can never block a session; only
a wrong event or client is a usage error (exit 2), which a registration of `install` never makes.
"""

from __future__ import annotations

import json
import sys
from enum import StrEnum
from typing import Annotated

import typer

from orqlet.application.contracts.common import RenderClientId
from orqlet.application.usecases.hook_event import HookEvent, run_hook
from orqlet.domain.strict_json import MAX_PAYLOAD_BYTES
from orqlet.interface.cli.wiring import build_hook_services


class HookClient(StrEnum):
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    COPILOT = "copilot"
    CURSOR = "cursor"


_RENDER_CLIENT: dict[HookClient, RenderClientId] = {
    HookClient.CLAUDE_CODE: "claude-code",
    HookClient.CODEX: "codex",
    HookClient.COPILOT: "copilot",
    HookClient.CURSOR: "cursor",
}


def hook_command(
    event: Annotated[HookEvent, typer.Argument(help="session-start or post-edit.")],
    client: Annotated[HookClient, typer.Option("--client", help="The client that runs the hook.")],
) -> None:
    """Print advisory context for a client's hook. Reads the payload from standard input."""
    try:
        payload = sys.stdin.buffer.read(MAX_PAYLOAD_BYTES + 1)
        output = run_hook(event, _RENDER_CLIENT[client], payload, build_hook_services())
    except Exception:  # on its own error the hook gives no context (ADR-004 decision 2)
        output = {}
    typer.echo(json.dumps(output))
