"""Claude Code: `AGENTS.md`, the bridge, rules, commands, skills and subagents."""

from __future__ import annotations

from orqlet.adapters.render.instructions import agents_block, claude_bridge, conventions_block
from orqlet.adapters.render.mcp import render_mcp_file
from orqlet.adapters.render.roles import claude_role
from orqlet.adapters.render.rules import claude_command, claude_rule
from orqlet.adapters.render.skills import claude_skill_files
from orqlet.application.ports.instruction_adapter import (
    CapabilityLimit,
    RenderedFile,
    RenderRequest,
    RenderResult,
)
from orqlet.domain.mcp_credentials import mcp_file_path
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath

DOCUMENTATION_LIMIT = CapabilityLimit(
    "ORQ-L001",
    "Claude Code behaviour follows its published documentation of 2026-10 and was not observed "
    "with a real client version.",
)


def _optional(file: RenderedFile | None) -> tuple[RenderedFile, ...]:
    return () if file is None else (file,)


def _mcp_file(request: RenderRequest) -> RenderedFile | None:
    """`.mcp.json`, seeded once and the team's afterwards, if a server is registered for Claude."""
    if request.integrations is None:
        return None
    servers = request.integrations.registered_for("claude-code")
    if not servers:
        return None
    return RenderedFile(
        path=CanonicalPath.parse(mcp_file_path("claude-code")),
        content=render_mcp_file(servers, "claude-code").encode("utf-8"),
        owner=OwnerMode.SEEDED,
        file_class=None,
    )


_WEB_LOOKUP_LIMIT = CapabilityLimit(
    "ORQ-L006",
    "Lookups on the web are requested by the baseline in every phase. A forked subagent "
    "ignores the `tools` of a role and the tester inherits the web and browser tools, "
    "so each role carries a sentence that forbids a lookup. To opt out, turn off the "
    "web tool in the settings of the client if it offers one; whether and how is not "
    "verified (check V-6) and not observed. The signed-in browser route is a separate "
    "tool that this does not turn off, and the role sentence and the rule to open "
    "registered addresses only are advice.",
)


class ClaudeCodeAdapter:
    client_id = "claude-code"

    def render(self, request: RenderRequest) -> RenderResult:
        files = (
            agents_block(request),
            *_optional(conventions_block(request)),
            claude_bridge(),
            *(claude_rule(rule) for rule in request.scoped_rules),
            *(claude_command(command) for command in request.commands),
            *(file for skill in request.skills for file in claude_skill_files(skill)),
            *(claude_role(role) for role in request.roles),
            *_optional(_mcp_file(request)),
        )
        return RenderResult(files=files, limits=(DOCUMENTATION_LIMIT, _WEB_LOOKUP_LIMIT))
