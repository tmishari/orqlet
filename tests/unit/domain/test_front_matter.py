"""Front matter: the line view and its comparison with the parsed view (harness2-fit, phase P-1).

Every test cites its `expected_behavior_source`. ADR-001 is
docs/design/harness2-fit/design/adr-001-client-visible-front-matter.md; AC-1 to AC-4 are the
acceptance criteria of phase P-1 and all of them rest on its decision 2.

Behaviour that the design leaves open is deliberately not pinned here: an empty value (`key:`),
duplicate keys, the characters allowed in a key, a colon without a following space, a value that
contains a colon, an unterminated quote, a key that is both missing from one view and non-scalar,
the order of the messages and their wording. Messages are therefore only checked for their number,
for the keys that they name and for the values that they must not show.
"""

from datetime import date

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from orqlet.domain.front_matter import front_matter_differences, simple_front_matter

pytestmark = pytest.mark.unit

LINE_MARKER = "SECRET-MARKER-12345"
PARSED_MARKER = "OTHER-MARKER-67890"
LIST_MARKER = "LIST-MARKER-11111"
MAPPING_MARKER = "MAPPING-MARKER-22222"

SKILL_LIKE_BLOCK = (
    'name: "orqlet-inventory"\n'
    "description: Maps one area of the repository\n"
    'model: "inherit"\n'
    "readonly: true\n"
    "disable-model-invocation: false\n"
)
SKILL_LIKE_VIEW = {
    "name": '"orqlet-inventory"',
    "description": "Maps one area of the repository",
    "model": '"inherit"',
    "readonly": "true",
    "disable-model-invocation": "false",
}

_text = st.text(alphabet=st.characters(exclude_categories=["Cs"]), max_size=20)
_key_names = st.from_regex(r"[a-z]+(-[a-z]+)*", fullmatch=True)
_any_keys = st.sampled_from(["name", "description", "model", "tools", "readonly"]) | _text
_newlines = st.sampled_from(["\n", "\r\n"])


def _is_str_mapping(result: object) -> bool:
    return isinstance(result, dict) and all(
        isinstance(key, str) and isinstance(value, str) for key, value in result.items()
    )


def _is_message_tuple(result: object) -> bool:
    return isinstance(result, tuple) and all(isinstance(message, str) for message in result)


def _names_key(key: str, messages: tuple[str, ...]) -> bool:
    return any(key in message for message in messages)


def _shows_any(messages: tuple[str, ...], *values: str) -> bool:
    return any(value in message for message in messages for value in values)


# --- AC-1: simple_front_matter reads one `key: value` line at a time -----------------------------


@pytest.mark.parametrize("ending", ["", "\n", "\r\n"])
def test_a_plain_value_is_returned_under_its_key(ending: str) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2."""
    assert simple_front_matter("name: orqlet-inventory" + ending) == {"name": "orqlet-inventory"}


@pytest.mark.parametrize("before", [" ", "  ", "     "])
@pytest.mark.parametrize("after", ["", " ", "    "])
def test_surrounding_blanks_of_the_value_are_removed_and_inner_blanks_stay(
    before: str, after: str
) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2."""
    block = f"description:{before}two  words{after}\n"

    assert simple_front_matter(block) == {"description": "two  words"}


@pytest.mark.parametrize("raw_value", ['"x"', "'x'", '"orqlet-inventory"', '"two words"'])
@pytest.mark.parametrize("padding", ["", "   "])
def test_quote_characters_are_kept_in_the_value(raw_value: str, padding: str) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2 (`name: "x"` gives `"x"` with quotes)."""
    block = f"name: {padding}{raw_value}{padding}\n"

    assert simple_front_matter(block) == {"name": raw_value}


def test_every_top_level_key_value_line_is_returned() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2 and decision 3 (every key is compared)."""
    assert simple_front_matter(SKILL_LIKE_BLOCK) == SKILL_LIKE_VIEW


def test_indented_lines_are_ignored() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2."""
    block = "  indented-first: no\nname: x\n  nested: y\n    deeper: z\nmodel: m\n"

    assert simple_front_matter(block) == {"name": "x", "model": "m"}


def test_lines_that_are_not_key_value_lines_are_ignored() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2."""
    block = "just some words\n- list item\n# a comment line\n\n   \n---\nname: kept\n"

    assert simple_front_matter(block) == {"name": "kept"}


@pytest.mark.parametrize(
    "block",
    ["", "\n", "just some words\n", "  indented: only\n", "---\n---\n", "---"],
)
def test_a_block_without_a_key_value_line_gives_an_empty_mapping(block: str) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2 (only such lines are returned)."""
    assert simple_front_matter(block) == {}


def test_crlf_line_ends_give_the_same_result_as_lf() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2."""
    result = simple_front_matter(SKILL_LIKE_BLOCK.replace("\n", "\r\n"))

    assert result == simple_front_matter(SKILL_LIKE_BLOCK)
    assert result == SKILL_LIKE_VIEW
    assert not any("\r" in value for value in result.values())


# The regex strategies below have a large smallest example, which Hypothesis reports as a health
# problem. The inputs are small and the tests are exact, so the check is switched off for them.
_SMALL_INPUTS = settings(suppress_health_check=[HealthCheck.large_base_example])

_plain_value = st.from_regex(r"[A-Za-z0-9]([A-Za-z0-9 ,.]*[A-Za-z0-9])?", fullmatch=True)
_pairs = st.dictionaries(_key_names, _plain_value, min_size=1, max_size=6)


@_SMALL_INPUTS
@given(_pairs, st.integers(1, 3), st.integers(0, 3), _newlines)
def test_generated_lines_are_read_back_as_their_keys_and_values(
    pairs: dict[str, str], before: int, after: int, newline: str
) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2."""
    gap, trail = " " * before, " " * after
    block = "".join(f"{key}:{gap}{value}{trail}{newline}" for key, value in pairs.items())

    assert simple_front_matter(block) == pairs


@_SMALL_INPUTS
@given(_pairs, st.sampled_from(['"', "'"]), _newlines)
def test_generated_quoted_values_keep_their_quote_characters(
    pairs: dict[str, str], quote: str, newline: str
) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2."""
    block = "".join(f"{key}: {quote}{value}{quote}{newline}" for key, value in pairs.items())

    expected = {key: f"{quote}{value}{quote}" for key, value in pairs.items()}
    assert simple_front_matter(block) == expected


_text_without_cr = st.text(
    alphabet=st.characters(exclude_categories=["Cs"], exclude_characters="\r"),
    max_size=200,
)


@given(_text_without_cr)
def test_crlf_and_lf_agree_for_any_text(text: str) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 2 (CRLF gives the same result as LF)."""
    assert simple_front_matter(text.replace("\n", "\r\n")) == simple_front_matter(text)


# --- AC-2: front_matter_differences compares by string form, per key -----------------------------


@pytest.mark.parametrize(
    ("line_text", "parsed_value"),
    [
        ("abc", "abc"),
        ("null", "null"),
        ("true", "true"),
        ('"x"', '"x"'),
        ("true", True),
        ("false", False),
        ("42", 42),
        ("0", 0),
        ("-7", -7),
        ("1" + "0" * 30, 10**30),
        ("null", None),
    ],
)
def test_a_parsed_value_equal_to_the_line_text_by_string_form_gives_no_difference(
    line_text: str, parsed_value: object
) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (string form of a parsed scalar)."""
    assert front_matter_differences({"zeta-field": line_text}, {"zeta-field": parsed_value}) == ()


def test_two_empty_views_give_no_difference() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (messages only for differences)."""
    assert front_matter_differences({}, {}) == ()


@pytest.mark.parametrize(
    ("line_text", "parsed_value"),
    [
        ('"x"', "x"),
        ("x", '"x"'),
        ("abc", "abd"),
        ("42", 43),
        ("42", "43"),
        ("true", False),
        ("false", True),
        ("True", True),
        ("true", 1),
        ("false", 0),
        ("None", None),
        ("x", None),
        ("7", None),
        ("null", "x"),
    ],
)
def test_values_that_differ_by_string_form_give_one_message_naming_the_key(
    line_text: str, parsed_value: object
) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (one message per differing key)."""
    messages = front_matter_differences({"zeta-field": line_text}, {"zeta-field": parsed_value})

    assert len(messages) == 1
    assert "zeta-field" in messages[0]


def test_true_and_false_are_read_as_words_and_never_as_one_and_zero() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (a boolean is decided before an int)."""
    key = "bool-field"

    assert front_matter_differences({key: "true"}, {key: True}) == ()
    assert front_matter_differences({key: "false"}, {key: False}) == ()
    assert _names_key(key, front_matter_differences({key: "1"}, {key: True}))
    assert _names_key(key, front_matter_differences({key: "0"}, {key: False}))


def test_a_key_in_the_line_view_only_gets_a_message() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (a key present in one view only)."""
    messages = front_matter_differences({"only-in-line": "x", "zq-match": "y"}, {"zq-match": "y"})

    assert len(messages) == 1
    assert "only-in-line" in messages[0]


def test_a_key_in_the_parsed_view_only_gets_a_message() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (a key present in one view only)."""
    messages = front_matter_differences({"zq-match": "y"}, {"zq-match": "y", "only-parsed": "x"})

    assert len(messages) == 1
    assert "only-parsed" in messages[0]


NON_SCALARS = [
    pytest.param([], id="empty-list"),
    pytest.param(["Read", "Grep"], id="list"),
    pytest.param([["nested"]], id="nested-list"),
    pytest.param({}, id="empty-mapping"),
    pytest.param({"inner": "value"}, id="mapping"),
    pytest.param({"member"}, id="set"),
    pytest.param(("member",), id="tuple"),
]


@pytest.mark.parametrize("parsed_value", NON_SCALARS)
def test_a_non_scalar_parsed_value_gets_a_message_naming_its_key(parsed_value: object) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (a list, a mapping or a non-scalar).

    The line text is the Python text of the value, so a comparison by `str()` would see no
    difference; the criterion asks for a message anyway.
    """
    line_view = {"tool-list": str(parsed_value)}

    messages = front_matter_differences(line_view, {"tool-list": parsed_value})

    assert len(messages) == 1
    assert "tool-list" in messages[0]


def test_a_flow_sequence_in_the_line_view_is_a_difference_from_the_parsed_list() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (a parsed list is a difference)."""
    line_view = {"tool-list": "[Read, Grep]"}

    messages = front_matter_differences(line_view, {"tool-list": ["Read", "Grep"]})

    assert len(messages) == 1
    assert "tool-list" in messages[0]


@pytest.mark.parametrize(
    ("line_text", "parsed_value"),
    [("1.5", 1.5), ("2026-10-23", date(2026, 10, 23))],
)
def test_a_parsed_value_of_any_other_type_is_a_difference(
    line_text: str, parsed_value: object
) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 ("any other type is a difference")."""
    messages = front_matter_differences({"other-type": line_text}, {"other-type": parsed_value})

    assert len(messages) == 1
    assert "other-type" in messages[0]


def test_each_differing_key_gets_one_message_and_matching_keys_get_none() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (one message per key)."""
    line_view = {"alpha-key": "1", "zq-match": "same", "charlie-key": "x"}
    parsed: dict[str, object] = {"alpha-key": 2, "zq-match": "same", "delta-key": "y"}

    messages = front_matter_differences(line_view, parsed)

    assert len(messages) == 3
    for key in ("alpha-key", "charlie-key", "delta-key"):
        assert sum(key in message for message in messages) == 1
    assert not _names_key("zq-match", messages)


_plain_scalars = st.none() | st.booleans() | st.integers(-(2**64), 2**64) | _text


def _string_form(value: bool | int | str | None) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


@given(_any_keys, _plain_scalars)
def test_a_scalar_and_its_string_form_never_differ(
    key: str, value: bool | int | str | None
) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (string form of a parsed scalar)."""
    assert front_matter_differences({key: _string_form(value)}, {key: value}) == ()


@given(st.dictionaries(_any_keys, _text, max_size=6))
def test_a_view_compared_with_itself_gives_no_difference(view: dict[str, str]) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 2 (a string is its own string form)."""
    assert front_matter_differences(view, view) == ()


# --- AC-3: messages name keys and never show a value ---------------------------------------------


def test_differing_scalar_values_never_appear_in_a_message() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 2 (messages name keys, never values)."""
    line_view, parsed = {"title-field": LINE_MARKER}, {"title-field": PARSED_MARKER}

    messages = front_matter_differences(line_view, parsed)

    assert messages
    assert not _shows_any(messages, LINE_MARKER, PARSED_MARKER)


def test_values_of_a_key_present_in_the_line_view_only_never_appear() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 2 (messages name keys, never values)."""
    messages = front_matter_differences({"line-only": LINE_MARKER}, {})

    assert _names_key("line-only", messages)
    assert not _shows_any(messages, LINE_MARKER)


def test_values_of_a_key_present_in_the_parsed_view_only_never_appear() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 2 (messages name keys, never values)."""
    messages = front_matter_differences({}, {"parsed-only": PARSED_MARKER})

    assert _names_key("parsed-only", messages)
    assert not _shows_any(messages, PARSED_MARKER)


def test_values_of_a_non_scalar_never_appear_in_a_message() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 2 (messages name keys, never values)."""
    line_view = {"list-field": f"[{LIST_MARKER}]", "map-field": f"{{inner: {MAPPING_MARKER}}}"}
    parsed: dict[str, object] = {
        "list-field": [LIST_MARKER],
        "map-field": {"inner": MAPPING_MARKER},
    }

    messages = front_matter_differences(line_view, parsed)

    assert _names_key("list-field", messages)
    assert _names_key("map-field", messages)
    assert not _shows_any(messages, LIST_MARKER, MAPPING_MARKER)


def test_integer_text_never_appears_in_a_message() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 2 (messages name keys, never values)."""
    messages = front_matter_differences({"count-field": "987654321"}, {"count-field": 123456789})

    assert messages
    assert not _shows_any(messages, "987654321", "123456789")


_line_values = _text.map(lambda suffix: "SECRET-MARKER-" + suffix)
_parsed_marked = _text.map(lambda suffix: "OTHER-MARKER-" + suffix)
_marked_parsed_values = (
    _parsed_marked
    | st.lists(_parsed_marked, max_size=3)
    | st.dictionaries(_text, _parsed_marked, max_size=3)
)


@given(
    st.dictionaries(_key_names, _line_values, max_size=5),
    st.dictionaries(_key_names, _marked_parsed_values, max_size=5),
)
def test_no_message_shows_a_marked_value_of_either_view(
    line_view: dict[str, str], parsed: dict[str, object]
) -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 2 (messages name keys, never values).

    Every value starts with a marker and, by construction, every key differs between the views or
    is present in one view only: each key must be named and no marker may be shown.
    """
    messages = front_matter_differences(line_view, parsed)

    assert not _shows_any(messages, "SECRET-MARKER-", "OTHER-MARKER-")
    for key in line_view.keys() | parsed.keys():
        assert _names_key(key, messages)


# --- AC-4: neither function raises ---------------------------------------------------------------

_tokens = st.sampled_from(
    [
        "---",
        "\r",
        "\n",
        "\r\n",
        ":",
        ": ",
        " ",
        "  ",
        "\t",
        '"',
        "'",
        "key",
        "x",
        "\x00",
        "\x1b",
        "\u2028",
        "#",
        "-",
    ]
)
_structured_text = st.lists(_tokens, max_size=40).map("".join)


@given(st.text() | _structured_text)
def test_simple_front_matter_never_raises_and_returns_strings(block: str) -> None:
    """AC-4. expected_behavior_source: ADR-001 decision 2 (neither function raises)."""
    assert _is_str_mapping(simple_front_matter(block))


DEGENERATE_BLOCKS = [
    pytest.param("", id="empty"),
    pytest.param("---", id="separator-only"),
    pytest.param("---\n" * 10_000, id="many-separator-lines"),
    pytest.param("x" * 100_000, id="very-long-text-without-colon"),
    pytest.param("key: " + "x" * 100_000, id="very-long-value"),
    pytest.param("k" * 100_000 + ": value", id="very-long-key"),
    pytest.param(":" * 100_000, id="only-colons"),
    pytest.param("a: b\n" * 20_000, id="many-lines"),
    pytest.param("\n" * 100_000, id="only-lf"),
    pytest.param("\r\n" * 50_000, id="only-crlf"),
    pytest.param("\r" * 100_000, id="only-cr"),
    pytest.param("\r\n\r\r\n\n" * 10_000 + "a: b", id="mixed-line-ends"),
]


@pytest.mark.parametrize("block", DEGENERATE_BLOCKS)
def test_simple_front_matter_does_not_raise_for_degenerate_text(block: str) -> None:
    """AC-4. expected_behavior_source: ADR-001 decision 2 (neither function raises)."""
    assert _is_str_mapping(simple_front_matter(block))


_parsed_scalars: st.SearchStrategy[object] = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats()
    | _text
    | st.binary(max_size=8)
    | st.dates()
)
_parsed_values: st.SearchStrategy[object] = st.recursive(
    _parsed_scalars,
    lambda children: st.lists(children, max_size=4) | st.dictionaries(_text, children, max_size=4),
    max_leaves=12,
)


@given(
    st.dictionaries(_any_keys, _text, max_size=6),
    st.dictionaries(_any_keys, _parsed_values, max_size=6),
)
def test_front_matter_differences_never_raises_and_returns_strings(
    line_view: dict[str, str], parsed: dict[str, object]
) -> None:
    """AC-4. expected_behavior_source: ADR-001 decision 2 (neither function raises)."""
    assert _is_message_tuple(front_matter_differences(line_view, parsed))


EXOTIC_PARSED_VALUES = [
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="infinity"),
    pytest.param(b"bytes", id="bytes"),
    pytest.param(date(2026, 10, 23), id="date"),
    pytest.param(object(), id="plain-object"),
    pytest.param(10**5000, id="integer-too-long-to-print"),
    pytest.param(-(10**5000), id="negative-integer-too-long-to-print"),
    pytest.param([[[[[]]]]], id="deeply-nested-list"),
]


@pytest.mark.parametrize("parsed_value", EXOTIC_PARSED_VALUES)
def test_front_matter_differences_does_not_raise_for_exotic_values(parsed_value: object) -> None:
    """AC-4. expected_behavior_source: ADR-001 decision 2 (neither function raises for a mapping).

    Only the absence of an exception and the shape of the result are checked: the design does not
    say whether such a value is a difference.
    """
    result = front_matter_differences({"exotic-field": "x"}, {"exotic-field": parsed_value})

    assert _is_message_tuple(result)
