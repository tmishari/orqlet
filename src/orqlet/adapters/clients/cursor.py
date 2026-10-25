"""Cursor: `AGENTS.md`, rules, commands, skills and subagents."""

from __future__ import annotations

from orqlet.adapters.render.instructions import agents_block
from orqlet.adapters.render.roles import cursor_role
from orqlet.adapters.render.rules import cursor_command, cursor_rule
from orqlet.adapters.render.skills import agents_skill_files
from orqlet.application.ports.instruction_adapter import (
    CapabilityLimit,
    RenderRequest,
    RenderResult,
)

DOCUMENTATION_LIMIT = CapabilityLimit(
    "ORQ-L001",
    "Cursor behaviour follows its published documentation of 2026-10 and was not observed with a "
    "real client version. The `globs` format of rule files is unverified.",
)
SKILL_PLACES_LIMIT = CapabilityLimit(
    "ORQ-L004",
    "Cursor reads skills from `.agents/skills` and also from `.claude/skills`. With Claude Code "
    "enabled too, a skill may be listed twice. This is documented but not observed.",
)


class CursorAdapter:
    client_id = "cursor"

    def render(self, request: RenderRequest) -> RenderResult:
        files = (
            agents_block(request),
            *(cursor_rule(rule) for rule in request.scoped_rules),
            *(cursor_command(command) for command in request.commands),
            *(file for skill in request.skills for file in agents_skill_files(skill)),
            *(cursor_role(role) for role in request.roles),
        )
        limits = (
            (DOCUMENTATION_LIMIT, SKILL_PLACES_LIMIT) if request.skills else (DOCUMENTATION_LIMIT,)
        )
        return RenderResult(files=files, limits=limits)
