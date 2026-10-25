"""Codex: `AGENTS.md`, skills and custom agents. Codex has no per-path rule mechanism."""

from __future__ import annotations

from orqlet.adapters.render.instructions import agents_block
from orqlet.adapters.render.roles import codex_role
from orqlet.adapters.render.skills import agents_skill_files, codex_sidecar
from orqlet.application.ports.instruction_adapter import (
    CapabilityLimit,
    RenderRequest,
    RenderResult,
)

DOCUMENTATION_LIMIT = CapabilityLimit(
    "ORQ-L001",
    "Codex behaviour follows its published documentation of 2026-10 and was not observed with a "
    "real client version.",
)
NO_PATH_RULES_LIMIT = CapabilityLimit(
    "ORQ-L002",
    "Codex has no per-path rules. Scoped rules are not delivered as files; an agent reads them "
    "with `orqlet standards for`.",
)
NO_COMMANDS_LIMIT = CapabilityLimit(
    "ORQ-L003",
    "Orqlet does not write commands for Codex in this release. Run `orqlet` in a terminal.",
)
SKILL_FIELD_LIMIT = CapabilityLimit(
    "ORQ-L005",
    "Codex reads the same `SKILL.md` as Cursor, which carries the field "
    "`disable-model-invocation` that Codex does not document. A skill is kept from starting on "
    "its own by `agents/openai.yaml`, which is documented but not observed.",
)


class CodexAdapter:
    client_id = "codex"

    def render(self, request: RenderRequest) -> RenderResult:
        limits = [DOCUMENTATION_LIMIT]
        if request.scoped_rules:
            limits.append(NO_PATH_RULES_LIMIT)
        if request.commands:
            limits.append(NO_COMMANDS_LIMIT)
        files = [
            agents_block(request),
            *(file for skill in request.skills for file in agents_skill_files(skill)),
            *(codex_sidecar(skill) for skill in request.skills),
            *(codex_role(role) for role in request.roles),
        ]
        if request.skills:
            limits.append(SKILL_FIELD_LIMIT)
        return RenderResult(files=tuple(files), limits=tuple(limits))
