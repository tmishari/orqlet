"""Claude Code: `AGENTS.md`, the bridge, rules, commands, skills and subagents."""

from __future__ import annotations

from orqlet.adapters.render.instructions import agents_block, claude_bridge, conventions_block
from orqlet.adapters.render.roles import claude_role
from orqlet.adapters.render.rules import claude_command, claude_rule
from orqlet.adapters.render.skills import claude_skill_files
from orqlet.application.ports.instruction_adapter import (
    CapabilityLimit,
    RenderedFile,
    RenderRequest,
    RenderResult,
)

DOCUMENTATION_LIMIT = CapabilityLimit(
    "ORQ-L001",
    "Claude Code behaviour follows its published documentation of 2026-10 and was not observed "
    "with a real client version.",
)


def _optional(file: RenderedFile | None) -> tuple[RenderedFile, ...]:
    return () if file is None else (file,)


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
        )
        return RenderResult(files=files, limits=(DOCUMENTATION_LIMIT, _WEB_LOOKUP_LIMIT))
