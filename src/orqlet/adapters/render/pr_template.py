"""The two Orqlet-owned blocks of the pull-request template (proposal section 13.7)."""

from __future__ import annotations

from orqlet.adapters.render.emit import normalise_text
from orqlet.application.ports.renderers import BlockSpec, TeamTemplate
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.domain.blocks import BlockError, BlockItem, set_blocks, validate_asset_body
from orqlet.domain.digest import sha256_hex

TEAM_BLOCK = "team-template"
WORKFLOW_BLOCK = "orqlet-workflow"
DEFAULT_PATH = ".github/pull_request_template.md"
WORKFLOW_SECTION = "pr_template/workflow-section.md"


def workflow_block(workflow: WorkflowSource) -> BlockSpec:
    body = normalise_text(workflow.read_text(WORKFLOW_SECTION)).rstrip("\n")
    version = workflow.release.version
    return BlockSpec(WORKFLOW_BLOCK, f"workflow@{version}#{sha256_hex(body.encode())}", body)


def team_block(team: TeamTemplate) -> BlockSpec:
    """The supplied body as a block. A body that could break the markers is refused."""
    body = normalise_text(team.body).rstrip("\n")
    validate_asset_body(body)
    if sha256_hex(body.encode()) != team.content_sha256:
        raise BlockError("the template text does not match its recorded hash")
    return BlockSpec(TEAM_BLOCK, f"{team.source_id}@{team.version}#{team.content_sha256}", body)


def provision(existing: str | None, blocks: list[BlockSpec]) -> str:
    """Put the blocks into the template text and change nothing else.

    With no existing file the blocks are the file. With one, a block that is present is replaced
    in place and new blocks go together after the first heading (or at the top when there is
    none), in the order given. Raises `BlockError` for any structural problem, and nothing is
    written.
    """
    items = [BlockItem(spec.name, spec.info, spec.body) for spec in blocks]
    return set_blocks(existing or "", items, insert_after_heading=True)


def markers(spec: BlockSpec) -> tuple[str, str]:
    """The begin and end marker lines of a block."""
    return (f"<!-- orqlet:begin {spec.name} {spec.info} -->", f"<!-- orqlet:end {spec.name} -->")
