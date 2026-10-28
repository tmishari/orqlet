"""The text of one client's MCP file (ADR-003 decision 4; ADR-002 decisions 5 and 7).

The file holds one entry for each server that the declaration registers for the client, and
nothing else: an address and no credential field. Every entry comes from `rendered_entry`, the
function that the validator compares a file with, so the output and the pin cannot drift apart.
The text is deterministic: no timestamp, absolute path or random value (ORQLET-DET-001).
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from orqlet.application.contracts.integrations import McpServer
from orqlet.domain.mcp_credentials import find_literal_credentials, rendered_entry


def render_mcp_file(servers: Sequence[McpServer], client: str) -> str:
    """The JSON text of `client`'s MCP file for `servers`, in the order given.

    A combination that the closed table does not enable is refused by `rendered_entry`. The text
    is scanned before it is returned: the entry has no field that could hold a credential, so a
    finding is a defect and raises, with a message that holds no value.
    """
    entries = {
        f"orqlet-{server.id}": rendered_entry(
            server.id, server.identity.url or "", _variable(server), client
        )
        for server in servers
    }
    text = json.dumps({"mcpServers": entries}, indent=2) + "\n"
    if find_literal_credentials(text):
        raise ValueError("the rendered MCP file holds credential-shaped text")
    return text


def _variable(server: McpServer) -> str | None:
    """The one variable of an `env-ref` server, or none for sign-in."""
    return server.auth.env_refs[0] if server.auth.mode == "env-ref" else None
