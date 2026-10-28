"""The `conventions` block of `AGENTS.md` (task team-conventions-resources, phase P-6):
`conventions_block`, what the three client adapters do with it, and when it exists.

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-002-*.md`
and `adr-003-*.md` under docs/design/team-conventions-resources/design/, EC-n are the expected
changes of the manifest.yaml next to them, and AC-1 to AC-7 are the acceptance criteria of phase P-6
in docs/design/team-conventions-resources/plan.yaml. "The interface decision" is the reading of the
plan author that the Tester of phase P-6 was given: `conventions_block(request)` is None when
`request.conventions` is None, else a file for AGENTS.md with owner SHARED_BLOCK and class PROTECTED
whose block is named `conventions` and whose body is the lines joined by a line feed; the three
clients return it next to the baseline block and its bytes are the same for the three clients.

These tests were written first, by the Tester of phase P-6, before the implementation existed. The
golden file of the block is in tests/unit/render/test_resources_golden.py.

Behaviour that the design leaves open is deliberately not pinned here:
- the `info` text of the begin marker and the `inputs` of the block file (the baseline records the
  workflow version and a digest; the design does not say what the second block records);
- the position of the block among the files of an adapter (only that both blocks are returned);
- the text of the first line of the template (the stub gives it a text of its own).
"""

from __future__ import annotations

import pytest

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.instructions import agents_block, conventions_block
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.instruction_adapter import (
    ConventionsView,
    InstructionAdapter,
    RenderedFile,
    RenderRequest,
)
from orqlet.application.usecases.init_files import merge_rendered
from orqlet.application.usecases.render_request import build_render_request
from orqlet.application.usecases.resources_view import conventions_view
from orqlet.domain.blocks import parse_blocks
from orqlet.domain.ownership import FileClass, OwnerMode
from tests.support.render import (
    CONVENTION_TABLE,
    EMPTY_RESOURCES,
    HOSTILE_ANSWERS,
    HOSTILE_RESOURCES,
    SAMPLE_ANSWERS,
    SAMPLE_RESOURCES,
    SAMPLE_RULES,
    hostile_request,
    profile_with,
    registry_of,
    resources_request,
    templated_workflow,
)

pytestmark = pytest.mark.unit

ADAPTERS: list[InstructionAdapter] = [ClaudeCodeAdapter(), CodexAdapter(), CursorAdapter()]
REST = "The rest is in .orqlet/project-profile.yaml."
LOADER = StrictYamlLoader()
BARE = RenderRequest(workflow_version="1.2.3", baseline_body="Baseline text\n")
LINES = (
    "Conventions of the team",
    'Branch model: "trunk-based"',
    'Merge strategy: "squash"',
    "Not decided: Branch naming. Ask the person; do not invent one.",
)


def with_view(*lines: str, resources: int = 0) -> RenderRequest:
    return RenderRequest(
        workflow_version="1.2.3",
        baseline_body="Baseline text\n",
        conventions=ConventionsView(lines=tuple(lines), resources=resources),
    )


def agents_files(adapter: InstructionAdapter, request: RenderRequest) -> list[RenderedFile]:
    return [f for f in adapter.render(request).files if str(f.path) == "AGENTS.md"]


def block_named(files: list[RenderedFile], name: str) -> RenderedFile | None:
    found = [f for f in files if f.block is not None and f"orqlet:begin {name}" in f.block[0]]
    assert len(found) <= 1
    return found[0] if found else None


def request_for(resources: Resources, answers: dict[str, str]) -> RenderRequest:
    view, _ = conventions_view(profile_with(answers), resources)
    return build_render_request(templated_workflow(), LOADER, SAMPLE_RULES, resources, view)


# --- the function ---------------------------------------------------------------------------------


def test_without_conventions_there_is_no_block() -> None:
    """AC-4. expected_behavior_source: EC-46 (`-> RenderedFile | None`) and the interface decision
    ("None when request.conventions is None")."""
    assert conventions_block(BARE) is None


def test_the_block_is_the_protected_shared_block_named_conventions_of_agents_md() -> None:
    """AC-3, AC-4. expected_behavior_source: ADR-003 decision 3 ("a second shared block,
    conventions, in AGENTS.md next to the baseline block"; "The block's class is PROTECTED") and
    the interface decision (owner SHARED_BLOCK, a block named conventions)."""
    block = conventions_block(with_view(*LINES, resources=0))

    assert block is not None
    assert str(block.path) == "AGENTS.md"
    assert block.owner is OwnerMode.SHARED_BLOCK
    assert block.file_class is FileClass.PROTECTED
    text = block.content.decode("utf-8")
    assert text.endswith("\n")
    (parsed,) = parse_blocks(text)
    assert parsed.name == "conventions"


def test_the_body_is_the_lines_of_the_view_joined_by_a_line_feed() -> None:
    """AC-4. expected_behavior_source: the interface decision ("whose body is the view's lines
    joined by '\\n'") and ADR-003 decision 3 ("the adapter only writes the lines between the
    markers")."""
    block = conventions_block(with_view(*LINES))

    assert block is not None
    (parsed,) = parse_blocks(block.content.decode("utf-8"))
    assert parsed.body == "\n".join(LINES)


def test_the_marker_lines_of_the_file_are_the_ones_in_its_content() -> None:
    """AC-4. expected_behavior_source: the interface decision ("marker lines via
    domain.blocks.render_block like the baseline's") and the lock, which records the begin and end
    marker of every block (init_files.block_name_of reads the name from the first marker)."""
    block = conventions_block(with_view(*LINES))

    assert block is not None
    assert block.block is not None
    begin, end = block.block
    rows = block.content.decode("utf-8").rstrip("\n").split("\n")
    assert (rows[0], rows[-1]) == (begin, end)
    assert begin.startswith("<!-- orqlet:begin conventions")
    assert end == "<!-- orqlet:end conventions -->"


def test_a_line_that_looks_like_markup_stays_a_line_of_the_body() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 3 (the application checks and quotes each
    value; the adapter only writes the lines): the body is not changed, escaped or cut."""
    lines = ('Branch model: "a \\"b\\" \\\\ c"', 'Branch naming: "x. Not decided: y."')

    block = conventions_block(with_view(*lines))

    assert block is not None
    (parsed,) = parse_blocks(block.content.decode("utf-8"))
    assert parsed.body.split("\n") == list(lines)


def test_the_same_view_gives_the_same_bytes() -> None:
    """AC-5. expected_behavior_source: AC-5 ("rendering twice gives identical bytes"),
    ORQLET-DET-001."""
    first = conventions_block(with_view(*LINES))
    second = conventions_block(with_view(*LINES))

    assert first is not None
    assert first == second


# --- the three clients ----------------------------------------------------------------------------


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_each_client_returns_the_conventions_block_next_to_the_baseline_block(
    adapter: InstructionAdapter,
) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 3 ("Each client adapter writes it as a
    second shared block, conventions, in AGENTS.md next to the baseline block") and the interface
    decision ("the three clients return it next to the baseline block")."""
    request = resources_request()

    files = agents_files(adapter, request)

    assert len(files) == 2
    assert block_named(files, "baseline") == agents_block(request)
    block = block_named(files, "conventions")
    assert block is not None
    assert block == conventions_block(request)


def test_the_conventions_block_is_the_same_bytes_for_the_three_clients() -> None:
    """AC-4. expected_behavior_source: AC-4 ("is the same bytes for the three clients") and the
    interface decision ("its bytes are identical for the three clients")."""
    request = resources_request()

    contents = {
        adapter.client_id: block_named(agents_files(adapter, request), "conventions")
        for adapter in ADAPTERS
    }

    assert all(block is not None for block in contents.values())
    assert len({block.content for block in contents.values() if block is not None}) == 1


def test_the_clients_still_merge_into_one_file_per_path_and_block() -> None:
    """AC-4, AC-6. expected_behavior_source: ADR-003 decision 3 ("the merge already keys files by
    path and block") and merge_rendered (identical files of several clients are one file, two
    that differ are a defect): AGENTS.md ends as two blocks, the baseline and the conventions."""
    request = resources_request()

    merged = merge_rendered([f for adapter in ADAPTERS for f in adapter.render(request).files])

    blocks = [f for f in merged if str(f.path) == "AGENTS.md"]
    assert len(blocks) == 2
    assert block_named(blocks, "baseline") is not None
    assert block_named(blocks, "conventions") is not None


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_a_request_without_conventions_leaves_the_baseline_block_alone(
    adapter: InstructionAdapter,
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("The existing golden files are byte-identical to the
    base") and the interface decision (no conventions block when the view is None)."""
    files = agents_files(adapter, BARE)

    assert files == [agents_block(BARE)]


# --- when the block exists ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("resources", "answers", "exists"),
    [
        (EMPTY_RESOURCES, {}, False),
        (SAMPLE_RESOURCES, {}, True),
        (EMPTY_RESOURCES, SAMPLE_ANSWERS, True),
        (SAMPLE_RESOURCES, SAMPLE_ANSWERS, True),
    ],
    ids=["nothing", "links-only", "answers-only", "both"],
)
@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_the_block_exists_only_when_a_convention_is_answered_or_the_registry_is_not_empty(
    adapter: InstructionAdapter, resources: Resources, answers: dict[str, str], exists: bool
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("The conventions block exists only when a convention
    is answered or the registry is not empty") and ADR-003 decision 3, from the profile and the
    registry to the file of each client."""
    files = agents_files(adapter, request_for(resources, answers))

    assert (block_named(files, "conventions") is not None) is exists
    assert len(files) == (2 if exists else 1)


def test_a_block_of_links_alone_names_the_skill_and_what_is_not_decided() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 3 ("one line 'Not decided ...' and, when the
    registry is not empty, one line that points to the skill orqlet-resources")."""
    request = request_for(SAMPLE_RESOURCES, {})

    block = conventions_block(request)

    assert block is not None
    (parsed,) = parse_blocks(block.content.decode("utf-8"))
    rows = parsed.body.split("\n")
    assert rows[0] == "CONVENTIONS FRAME"
    assert rows[-1] == "Links to team resources: 2 registered. Use the skill orqlet-resources."
    assert rows[-2].startswith("Not decided: ")
    assert len(rows) == 3


def test_the_answered_conventions_are_in_the_block_in_the_order_of_the_table() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 3 ("one line per answered convention") and
    the interface decision (table order), through the request and the adapter."""
    answers = {key: f"answer {n}" for n, (_, key) in enumerate(CONVENTION_TABLE)}

    block = conventions_block(request_for(EMPTY_RESOURCES, answers))

    assert block is not None
    (parsed,) = parse_blocks(block.content.decode("utf-8"))
    labels = [row.split(": ")[0] for row in parsed.body.split("\n")[1:]]
    assert labels == [label for label, _ in CONVENTION_TABLE]


# --- the size of the block ------------------------------------------------------------------------


def worst_case_answers() -> dict[str, str]:
    return {key: "\\" * 200 for _, key in CONVENTION_TABLE}


def test_the_whole_block_is_at_most_12_lines_and_3_kib_with_the_shipped_template() -> None:
    """AC-4. expected_behavior_source: AC-4 ("drops lines beyond twelve with a final line, is at
    most 3 KiB") and ADR-003 decision 3 ("the block is at most 12 lines and 3 KiB; lines beyond
    twelve are dropped and a final line says that the rest is in the profile"): nine answers that
    quote to 320 characters each and a registry of 100 entries, written by the shipped template."""
    many = registry_of(
        *(
            {
                "id": f"link-{n:03d}",
                "title": f"Link {n}",
                "kind": "team-docs",
                "note": "Read it.",
                "url": "https://docs.example.com/x",
                "access": "public",
            }
            for n in range(100)
        )
    )

    request = resources_request(resources=many, profile=profile_with(worst_case_answers()))

    assert request.conventions is not None
    assert len(request.conventions.lines) <= 12
    assert len("\n".join(request.conventions.lines).encode("utf-8")) <= 3 * 1024
    assert request.conventions.lines[-1] == REST
    block = conventions_block(request)
    assert block is not None
    (parsed,) = parse_blocks(block.content.decode("utf-8"))
    assert len(parsed.body.split("\n")) <= 12
    assert len(parsed.body.encode("utf-8")) <= 3 * 1024
    assert parsed.body.split("\n")[-1] == REST


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_the_hostile_profile_cannot_forge_a_marker_or_a_second_block(
    adapter: InstructionAdapter,
) -> None:
    """AC-4. expected_behavior_source: S-1 and ADR-002 decision 8 ("nothing in a value can start a
    line or forge a block marker"), with a profile whose values hold a marker, a link, a tag, a
    backtick and a line break: the file still has the one block and its body holds no markup."""
    request = hostile_request()

    block = block_named(agents_files(adapter, request), "conventions")

    assert block is not None
    (parsed,) = parse_blocks(block.content.decode("utf-8"))
    assert parsed.name == "conventions"
    from_values = "\n".join(parsed.body.split("\n")[1:])  # the first line is the template's
    assert "<!--" not in from_values
    assert "-->" not in from_values
    assert "://" not in from_values
    assert "`" not in from_values
    assert len(parsed.body.split("\n")) <= 12


def test_the_hostile_answers_that_pass_are_quoted_and_the_others_are_not_in_the_block() -> None:
    """AC-4. expected_behavior_source: AC-4 ("a value that fails text_problems is left out") and
    ADR-003 decision 3, through the request: of the six hostile answers one is written."""
    request = hostile_request(HOSTILE_RESOURCES, HOSTILE_ANSWERS)

    assert request.conventions is not None
    body = "\n".join(request.conventions.lines)
    assert 'Branch model: "trunk \\"based\\" \\\\ ok"' in body
    for hostile in ("hostile.example", "<ticket>", "rm -rf", "squash"):
        assert hostile not in body
