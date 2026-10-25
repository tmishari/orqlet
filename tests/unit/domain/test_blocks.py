"""Managed blocks: marker rules, hostile bodies, line endings and idempotence (FM-P02 to FM-P04)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.domain.blocks import (
    BOM,
    Block,
    BlockError,
    decode_utf8,
    find_block,
    parse_blocks,
    remove_block,
    render_block,
    set_block,
    validate_asset_body,
)

pytestmark = pytest.mark.unit

BLOCK = render_block("orqlet-workflow", "1.0.0#abc", "line one\nline two")
BEGIN_A, END_A = "<!-- orqlet:begin a -->\n", "<!-- orqlet:end a -->\n"
BEGIN_B, END_B = "<!-- orqlet:begin b -->\n", "<!-- orqlet:end b -->\n"


def body_of(text: str, name: str) -> str:
    block = find_block(text, name)
    assert isinstance(block, Block)
    return block.body


def test_a_block_round_trips_through_render_and_parse() -> None:
    (block,) = parse_blocks("# Title\n\n" + BLOCK + "\ntail\n")

    assert block.name == "orqlet-workflow"
    assert block.info == "1.0.0#abc"
    assert block.body == "line one\nline two"


def test_a_block_without_info_is_allowed() -> None:
    (block,) = parse_blocks(render_block("baseline", "", "x"))

    assert (block.name, block.info) == ("baseline", "")


def test_offsets_cover_exactly_the_marker_lines_and_the_body() -> None:
    text = "before\n" + BLOCK + "after\n"
    (block,) = parse_blocks(text)

    assert text[block.start : block.end] == BLOCK


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (BEGIN_A + "x\n", "never closed"),
        ("x\n" + END_A, "no matching begin"),
        (BEGIN_A + BEGIN_B + END_B + END_A, "inside"),
        (BEGIN_A + END_A + BEGIN_A + END_A, "twice"),
        (BEGIN_A + END_B, "no matching begin"),
        ("text\n<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> branch\n", "merge-conflict"),
        ("```\nunclosed\n" + BEGIN_A + END_A, "unclosed code fence"),
    ],
)
def test_structural_problems_are_errors(text: str, message: str) -> None:
    with pytest.raises(BlockError, match=message):
        parse_blocks(text)


def test_a_lone_separator_line_is_ordinary_text_not_a_conflict() -> None:
    assert parse_blocks("a\n=======\nb\n") == ()


def test_markers_inside_a_code_fence_are_text_not_blocks() -> None:
    assert parse_blocks("```md\n" + BEGIN_A + END_A + "```\n") == ()


def test_markers_that_are_not_at_the_start_of_a_line_are_text() -> None:
    assert parse_blocks("  " + BEGIN_A + "  " + END_A) == ()


def test_a_marker_at_the_start_with_an_indented_partner_is_unbalanced() -> None:
    with pytest.raises(BlockError):
        parse_blocks("  " + BEGIN_A + END_A)


def test_a_tilde_fence_and_a_longer_fence_close_correctly() -> None:
    text = "~~~\ncode\n~~~\n````\ninner ```\n````\n" + BLOCK

    assert [b.name for b in parse_blocks(text)] == ["orqlet-workflow"]


def test_set_block_inserts_after_the_first_heading_and_keeps_the_rest() -> None:
    original = "# Pull request\n\nDescribe the change.\n"

    result = set_block(original, "orqlet-workflow", "1#h", "body", insert_after_heading=True)

    block = render_block("orqlet-workflow", "1#h", "body")
    assert result == "# Pull request\n\n" + block + "\nDescribe the change.\n"


def test_set_block_skips_a_heading_inside_a_code_fence() -> None:
    original = "```sh\n# not a heading\n```\n# Real\ntext\n"

    result = set_block(original, "b", "", "x", insert_after_heading=True)

    assert result.index("orqlet:begin") > result.index("# Real")


def test_set_block_appends_when_there_is_no_heading_or_when_asked() -> None:
    result = set_block("plain\n", "b", "", "x", insert_after_heading=False)

    assert result == "plain\n\n" + render_block("b", "", "x")


def test_set_block_on_an_empty_file_is_just_the_block() -> None:
    assert set_block("", "b", "", "x", insert_after_heading=True) == render_block("b", "", "x")


def test_set_block_replaces_in_place_and_is_idempotent() -> None:
    once = set_block("# T\n\ntext\n", "b", "1", "one", insert_after_heading=True)
    again = set_block(once, "b", "1", "one", insert_after_heading=True)
    updated = set_block(once, "b", "2", "two", insert_after_heading=True)

    assert again == once
    assert updated.count("orqlet:begin") == 1
    assert updated.startswith("# T\n\n")
    assert updated.endswith("\ntext\n")
    assert body_of(updated, "b") == "two"


def test_remove_block_leaves_everything_else() -> None:
    text = "# T\n\n" + BLOCK + "\ntail\n"

    assert remove_block(text, "orqlet-workflow") == "# T\n\n\ntail\n"
    assert remove_block("nothing\n", "orqlet-workflow") == "nothing\n"


def test_crlf_files_stay_crlf_and_the_text_outside_is_byte_identical() -> None:
    original = "# T\r\n\r\ntext\r\n"

    result = set_block(original, "b", "", "one\ntwo", insert_after_heading=True)

    assert "\n" not in result.replace("\r\n", "")
    assert result.endswith("text\r\n")
    assert body_of(result, "b") == "one\ntwo"
    assert set_block(result, "b", "", "one\ntwo", insert_after_heading=True) == result


def test_a_byte_order_mark_is_kept_and_does_not_hide_the_first_marker() -> None:
    original = BOM + render_block("b", "", "x")

    (block,) = parse_blocks(original)
    updated = set_block(original, "b", "", "y", insert_after_heading=True)

    assert block.start == len(BOM)
    assert updated.startswith(BOM)
    assert body_of(updated, "b") == "y"


def test_a_bom_file_without_the_block_keeps_its_bom_when_one_is_added() -> None:
    result = set_block(BOM + "# T\ntext\n", "b", "", "x", insert_after_heading=True)

    assert result.startswith(BOM + "# T\n")


def test_a_user_edit_inside_a_block_is_visible_as_a_different_body() -> None:
    edited = BLOCK.replace("line one", "line ONE")

    assert body_of(edited, "orqlet-workflow") != body_of(BLOCK, "orqlet-workflow")


def test_decode_rejects_other_encodings() -> None:
    assert decode_utf8("é".encode()) == "é"
    with pytest.raises(BlockError):
        decode_utf8("é".encode("latin-1"))
    with pytest.raises(BlockError):
        decode_utf8("x".encode("utf-16"))


@pytest.mark.parametrize(
    "body",
    [
        "<!-- orqlet:begin team-template x -->",
        "text with orqlet: inside",
        "```\nunclosed fence",
        "<!-- an unclosed comment",
    ],
)
def test_hostile_pack_assets_are_rejected(body: str) -> None:
    with pytest.raises(BlockError):
        validate_asset_body(body)


@pytest.mark.parametrize("body", ["plain text", "```\ncode\n```\n", "a <!-- c --> b", "======="])
def test_ordinary_pack_assets_are_accepted(body: str) -> None:
    validate_asset_body(body)


body_text = st.text(
    alphabet=st.characters(exclude_categories=["Cs"], exclude_characters="\r<>`~#"), max_size=60
)


@given(st.lists(body_text, max_size=4), body_text)
def test_setting_a_block_then_reading_it_back_returns_the_body(lines: list[str], body: str) -> None:
    original = "\n".join(lines)
    clean_body = body.replace("\n", " ").strip() or "x"
    try:
        result = set_block(original, "b", "1", clean_body, insert_after_heading=False)
    except BlockError:
        return
    assert body_of(result, "b") == clean_body
    assert set_block(result, "b", "1", clean_body, insert_after_heading=False) == result
