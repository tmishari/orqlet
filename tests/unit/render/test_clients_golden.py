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
from orqlet.application.ports.instruction_adapter import (
    InstructionAdapter,
    RenderedFile,
    RenderRequest,
)
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


# --- the limits of each client (task team-conventions-resources, phase P-8) ----------------------
# Every case cites its `expected_behavior_source`: ADR-004 is `adr-004-*.md` under
# docs/design/team-conventions-resources/design/ and AC-5 is an acceptance criterion of phase P-8
# in the `plan.yaml` there. The Coder wrote the limits before the Tester, so these cases were run
# against them and then checked by changing a copy of the adapters. The wording of a message is not
# pinned beyond the words below, and the set of limits is pinned for two requests only: the
# packaged one and an empty one. A request with other parts may add limits that are not pinned.
REQUESTS: dict[str, Callable[[], RenderRequest]] = {
    "the packaged request": packaged_request,
    "an empty request": lambda: RenderRequest(workflow_version="1", baseline_body="b\n"),
}
REQUEST_FACTORIES = list(REQUESTS.values())
REQUEST_IDS = list(REQUESTS)
# The codes that each client reported before phase P-8: the characterization of the base revision
# (claude_code.py, codex.py and cursor.py as committed), for each request above.
LIMITS_BEFORE: dict[str, dict[str, set[str]]] = {
    "the packaged request": {
        "claude-code": {"ORQ-L001"},
        "codex": {"ORQ-L001", "ORQ-L002", "ORQ-L003", "ORQ-L005"},
        "cursor": {"ORQ-L001", "ORQ-L004"},
    },
    "an empty request": {
        "claude-code": {"ORQ-L001"},
        "codex": {"ORQ-L001"},
        "cursor": {"ORQ-L001"},
    },
}


def web_limit_message(adapter: InstructionAdapter, request: RenderRequest) -> str:
    """The message of the one limit ORQ-L006, in lower case (the letter case is not a rule)."""
    messages = [
        limit.message.lower()
        for limit in adapter.render(request).limits
        if limit.code == "ORQ-L006"
    ]
    assert len(messages) == 1, f"{adapter.client_id}: ORQ-L006 is reported exactly once"
    return messages[0]


@pytest.mark.parametrize("make_request", REQUEST_FACTORIES, ids=REQUEST_IDS)
@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_every_client_says_that_lookups_are_requested_and_how_to_opt_out(
    adapter: InstructionAdapter, make_request: Callable[[], RenderRequest]
) -> None:
    """AC-5. expected_behavior_source: plan P-8 AC-5 (each client reports one new limit that says
    lookups are requested and how to opt out, labelled documented and not observed); ADR-004
    decision 6; the interface decision (code ORQ-L006, `opt out`, `not observed`)."""
    message = web_limit_message(adapter, make_request())

    assert "requested" in message
    assert "opt out" in message
    assert "not observed" in message


@pytest.mark.parametrize("make_request", REQUEST_FACTORIES, ids=REQUEST_IDS)
@pytest.mark.parametrize(
    ("adapter", "words"),
    [
        (ClaudeCodeAdapter(), ("forked", "tester")),
        (CodexAdapter(), ("cached",)),
        (CursorAdapter(), ("not verified",)),
    ],
    ids=["claude-code", "codex", "cursor"],
)
def test_each_client_names_what_is_true_of_its_own_web_tool(
    adapter: InstructionAdapter,
    words: tuple[str, ...],
    make_request: Callable[[], RenderRequest],
) -> None:
    """AC-5. expected_behavior_source: ADR-004 decision 6 (Codex: `web_search` defaults to
    `cached`; Cursor: its web tools are not verified); plan P-8 file list (claude_code.py: a fork
    ignores a role's tools and the tester inherits the web tools); the interface decision
    (`cached` for Codex, `forked` for Claude Code)."""
    message = web_limit_message(adapter, make_request())

    for word in words:
        assert word in message


@pytest.mark.parametrize("request_name", REQUEST_IDS)
@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_each_client_reports_the_codes_it_reported_before_and_the_new_one(
    adapter: InstructionAdapter, request_name: str
) -> None:
    """AC-5. expected_behavior_source: plan P-8 AC-5 (one new capability limit; ORQ-L001 is still
    reported by every client); the interface decision (ORQ-L002 to ORQ-L005 are unchanged in
    code); the codes before are the base revision's, written out in LIMITS_BEFORE."""
    result = adapter.render(REQUESTS[request_name]())

    codes = [limit.code for limit in result.limits]
    assert len(codes) == len(set(codes))
    assert set(codes) == LIMITS_BEFORE[request_name][adapter.client_id] | {"ORQ-L006"}
