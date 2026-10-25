"""Generated files compared byte for byte with committed golden files.

The golden files document what each client is *expected* to read, according to its published
documentation of 2026-10. No real client was run (spike S-21), so they are labelled as such by
their directory name `docs-2026-10`.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.application.ports.instruction_adapter import InstructionAdapter, RenderedFile
from orqlet.domain.ownership import FileClass, OwnerMode
from tests.support.render import (
    COMMAND_NAMES,
    ROLE_NAMES,
    SKILL_NAMES,
    packaged_request,
    skill_files,
)

pytestmark = pytest.mark.golden

FAMILY = "docs-2026-10"
ADAPTERS: list[InstructionAdapter] = [ClaudeCodeAdapter(), CodexAdapter(), CursorAdapter()]


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_every_generated_file_matches_its_golden_file(
    adapter: InstructionAdapter, golden: Callable[[str, bytes], None]
) -> None:
    result = adapter.render(packaged_request())

    for rendered in result.files:
        golden(f"{adapter.client_id}/{FAMILY}/{rendered.path}", rendered.content)


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_rendering_twice_gives_identical_bytes(adapter: InstructionAdapter) -> None:
    first = adapter.render(packaged_request())
    second = adapter.render(packaged_request())

    assert first == second


def agents_block(adapter: InstructionAdapter) -> RenderedFile:
    files = adapter.render(packaged_request()).files
    return next(f for f in files if str(f.path) == "AGENTS.md")


def test_the_shared_baseline_block_is_byte_identical_across_clients() -> None:
    blocks = [agents_block(adapter) for adapter in ADAPTERS]

    assert len({block.content for block in blocks}) == 1
    assert {block.owner for block in blocks} == {OwnerMode.SHARED_BLOCK}
    assert {block.file_class for block in blocks} == {FileClass.PROTECTED}


def test_each_client_gets_only_the_files_it_reads() -> None:
    paths = {
        adapter.client_id: sorted(str(f.path) for f in adapter.render(packaged_request()).files)
        for adapter in ADAPTERS
    }

    assert paths["claude-code"] == sorted(
        [
            ".claude/CLAUDE.md",
            *(f".claude/agents/{name}.md" for name in ROLE_NAMES),
            *(f".claude/commands/orqlet-{name}.md" for name in COMMAND_NAMES),
            ".claude/rules/orqlet-sample-001.md",
            ".claude/rules/orqlet-workflow.md",
            *skill_files(".claude/skills"),
            "AGENTS.md",
        ]
    )
    assert paths["cursor"] == sorted(
        [
            *skill_files(".agents/skills"),
            *(f".cursor/agents/{name}.md" for name in ROLE_NAMES),
            *(f".cursor/commands/orqlet-{name}.md" for name in COMMAND_NAMES),
            ".cursor/rules/orqlet-sample-001.mdc",
            ".cursor/rules/orqlet-workflow.mdc",
            "AGENTS.md",
        ]
    )
    assert paths["codex"] == sorted(
        [
            *skill_files(".agents/skills"),
            *(f".agents/skills/{name}/agents/openai.yaml" for name in SKILL_NAMES),
            *(f".codex/agents/{name}.toml" for name in ROLE_NAMES),
            "AGENTS.md",
        ]
    )


def test_only_must_rules_with_paths_become_files() -> None:
    names = [rule.name for rule in packaged_request().scoped_rules]

    assert names == ["workflow", "sample-001"]  # SHOULD and path-less MUST rules are not files


def test_codex_says_it_has_no_per_path_rules() -> None:
    result = CodexAdapter().render(packaged_request())

    assert "ORQ-L002" in {limit.code for limit in result.limits}


def test_every_client_labels_its_output_as_documentation_based() -> None:
    for adapter in ADAPTERS:
        assert "ORQ-L001" in {limit.code for limit in adapter.render(packaged_request()).limits}


def test_the_claude_bridge_is_generated_unconditionally_and_climbs_out_of_the_folder() -> None:
    bridge = next(
        f
        for f in ClaudeCodeAdapter().render(packaged_request()).files
        if str(f.path) == ".claude/CLAUDE.md"
    )

    assert b"@../AGENTS.md" in bridge.content
    assert bridge.owner is OwnerMode.ORQLET
    assert bridge.file_class is FileClass.PROTECTED


def test_the_codex_chain_budget_is_respected_by_the_baseline_block() -> None:
    block = CodexAdapter().render(packaged_request()).files[0]

    assert len(block.content) < 32 * 1024
