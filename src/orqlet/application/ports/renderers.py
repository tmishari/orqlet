"""Renderers for files that belong to no single client: the seed and the PR-template blocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from orqlet.application.ports.instruction_adapter import RenderedFile
from orqlet.application.ports.workflow import WorkflowSource


@dataclass(frozen=True, slots=True)
class TeamTemplate:
    """The team's own template, supplied by a pack. Its text is distributed unchanged."""

    source_id: str
    version: str
    body: str
    content_sha256: str  # SHA-256 of the body without its final line break


@dataclass(frozen=True, slots=True)
class BlockSpec:
    name: str
    info: str
    body: str


class FileRenderers(Protocol):
    def seed_files(self, workflow: WorkflowSource, *, base: str) -> tuple[RenderedFile, ...]:
        """The seed of the standards folder, as seeded files below `base`."""
        ...

    def workflow_block(self, workflow: WorkflowSource) -> BlockSpec:
        """The `orqlet-workflow` section of the pull-request template."""
        ...

    def team_block(self, team: TeamTemplate) -> BlockSpec:
        """The team's template as a block. Raises if its text could break the markers."""
        ...
