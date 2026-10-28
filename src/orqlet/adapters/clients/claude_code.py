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
        return RenderResult(files=files, limits=(DOCUMENTATION_LIMIT,))
