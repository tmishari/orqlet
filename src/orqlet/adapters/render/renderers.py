"""The packaged implementation of `FileRenderers`."""

from __future__ import annotations

from orqlet.adapters.render import pr_template, prompts_seed
from orqlet.application.ports.instruction_adapter import RenderedFile
from orqlet.application.ports.renderers import BlockSpec, TeamTemplate
from orqlet.application.ports.workflow import WorkflowSource


class PackagedRenderers:
    def seed_files(self, workflow: WorkflowSource, *, base: str) -> tuple[RenderedFile, ...]:
        return prompts_seed.seed_files(workflow, base=base)

    def workflow_block(self, workflow: WorkflowSource) -> BlockSpec:
        return pr_template.workflow_block(workflow)

    def team_block(self, team: TeamTemplate) -> BlockSpec:
        return pr_template.team_block(team)
