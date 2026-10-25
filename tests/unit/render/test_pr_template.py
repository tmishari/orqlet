"""PR-template provisioning: two owned blocks, everything else kept (FM-P01 to FM-P04)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from orqlet.adapters.render.pr_template import markers, provision, team_block, workflow_block
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.ports.renderers import BlockSpec, TeamTemplate
from orqlet.domain.blocks import BOM, BlockError, parse_blocks
from orqlet.domain.digest import sha256_hex

pytestmark = pytest.mark.golden

TEAM_BODY = "## Summary\n\nWhat changed and why.\n\n## Testing\n\nHow it was tested.\n"
TEAM = TeamTemplate(
    source_id="team-standards/pr-template",
    version="1.2.0",
    body=TEAM_BODY,
    content_sha256=sha256_hex(TEAM_BODY.rstrip("\n").encode()),
)
NESTED = (
    "<!-- orqlet:begin a -->\n"
    "<!-- orqlet:begin b -->\n"
    "<!-- orqlet:end b -->\n"
    "<!-- orqlet:end a -->\n"
)
EXISTING = "# Pull request\n\nProject text that must survive.\n\n- [ ] project checklist\n"


def blocks(*, with_team: bool) -> list[BlockSpec]:
    workflow = workflow_block(PackagedWorkflow())
    return [team_block(TEAM), workflow] if with_team else [workflow]


def names(text: str) -> list[str]:
    return [block.name for block in parse_blocks(text)]


def test_no_template_and_no_team_text_gives_only_the_workflow_block(
    golden: Callable[[str, bytes], None],
) -> None:
    text = provision(None, blocks(with_team=False))

    assert names(text) == ["orqlet-workflow"]
    golden("common/pr_template/new-workflow-only.md", text.encode())


def test_no_template_with_team_text_gives_the_team_block_first(
    golden: Callable[[str, bytes], None],
) -> None:
    text = provision(None, blocks(with_team=True))

    assert names(text) == ["team-template", "orqlet-workflow"]
    golden("common/pr_template/new-with-team.md", text.encode())


def test_an_existing_template_gets_the_blocks_after_its_first_heading(
    golden: Callable[[str, bytes], None],
) -> None:
    text = provision(EXISTING, blocks(with_team=True))

    assert names(text) == ["team-template", "orqlet-workflow"]
    assert text.startswith("# Pull request\n")
    golden("common/pr_template/existing-reconciled.md", text.encode())


def test_text_outside_the_blocks_is_preserved_byte_for_byte() -> None:
    text = provision(EXISTING, blocks(with_team=True))

    heading, _, tail = EXISTING.partition("\n")
    assert text.startswith(heading + "\n")
    assert text.endswith(tail)  # everything after the heading line is untouched


@pytest.mark.parametrize("with_team", [True, False])
def test_a_second_provision_changes_nothing(with_team: bool) -> None:
    first = provision(EXISTING, blocks(with_team=with_team))

    assert provision(first, blocks(with_team=with_team)) == first


def test_a_new_workflow_version_updates_only_its_block() -> None:
    first = provision(EXISTING, blocks(with_team=True))
    newer = BlockSpec("orqlet-workflow", "workflow@0.2.0#new", "new workflow section")

    second = provision(first, [team_block(TEAM), newer])

    assert names(second) == ["team-template", "orqlet-workflow"]
    assert "new workflow section" in second
    assert "Project text that must survive." in second
    assert second.count("orqlet:begin") == 2


@pytest.mark.parametrize(
    "existing",
    [
        EXISTING.replace(
            "# Pull request", "<!-- orqlet:begin orqlet-workflow x -->\n# Pull request"
        ),
        EXISTING + "<!-- orqlet:end orqlet-workflow -->\n",
        "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> branch\n",
        EXISTING + "```\nunclosed fence\n",
        "# T\n" + NESTED,
    ],
)
def test_hostile_existing_files_are_a_conflict_and_nothing_is_written(existing: str) -> None:
    with pytest.raises(BlockError):
        provision(existing, blocks(with_team=True))


@pytest.mark.parametrize(
    "existing",
    [
        BOM + EXISTING,
        EXISTING.replace("\n", "\r\n"),
        BOM + EXISTING.replace("\n", "\r\n"),
        EXISTING + "\n=======\n",
        "no heading at all\n",
        "",
    ],
)
def test_bom_crlf_and_odd_but_legal_files_are_handled_and_stay_idempotent(existing: str) -> None:
    first = provision(existing, blocks(with_team=True))

    assert names(first) == ["team-template", "orqlet-workflow"]
    assert provision(first, blocks(with_team=True)) == first
    if existing.startswith(BOM):
        assert first.startswith(BOM)
    if "\r\n" in existing:
        assert "\r\n" in first
        assert "\n" not in first.replace("\r\n", "")


@pytest.mark.parametrize(
    "body",
    [
        "text <!-- orqlet:begin team-template x --> text",
        "mentions orqlet: anything",
        "```\nunclosed",
        "<!-- unclosed comment",
    ],
)
def test_a_hostile_team_template_is_refused_before_anything_is_built(body: str) -> None:
    team = TeamTemplate("id", "1.0.0", body, sha256_hex(body.rstrip("\n").encode()))

    with pytest.raises(BlockError):
        team_block(team)


def test_a_team_template_whose_text_does_not_match_its_hash_is_refused() -> None:
    tampered = TeamTemplate("id", "1.0.0", "changed text", TEAM.content_sha256)

    with pytest.raises(BlockError, match="hash"):
        team_block(tampered)


def test_the_block_markers_record_source_version_and_hash() -> None:
    spec = team_block(TEAM)

    assert spec.info == f"team-standards/pr-template@1.2.0#{TEAM.content_sha256}"
    assert markers(spec)[0] == f"<!-- orqlet:begin team-template {spec.info} -->"
    assert markers(spec)[1] == "<!-- orqlet:end team-template -->"
