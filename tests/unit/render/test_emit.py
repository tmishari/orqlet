"""The emitters write the same bytes everywhere and survive awkward strings (ADR-005)."""

from __future__ import annotations

import inspect
import re
import tomllib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.emit import (
    Data,
    front_matter,
    normalise_text,
    quote,
    toml_table,
    yaml_document,
    yaml_scalar,
)
from orqlet.adapters.render.rules import claude_rule, cursor_rule
from orqlet.application.ports.instruction_adapter import ScopedRule
from orqlet.domain.ownership import FileClass

pytestmark = pytest.mark.unit

LOADER = StrictYamlLoader()
AWKWARD = [
    "plain",
    "has: colon",
    '"double"',
    "'single'",
    "- leading dash",
    "# hash",
    "line\nbreak",
    "tab\there",
    "back\\slash",
    "ünïcödé ✓",
    "emoji 🙂",
    "\x7f",
    "\u0085",
    "\u2028",
    "\ufeff",
    "\ufffe",
    "yes",
    "No",
    "null",
    "~",
    "1.10",
    "2026-10-20",
    "0x10",
    "",
    " ",
    "{not: a map}",
    "[not, a list]",
    "@at",
    "*star",
    "&anchor",
    "!tag",
    "%percent",
    "<<",
]


def test_normalise_text_uses_lf_and_one_final_newline() -> None:
    assert normalise_text("a\r\nb\r\n\r\n\r\n") == "a\nb\n"
    assert normalise_text("a\rb") == "a\nb\n"
    assert normalise_text("") == ""
    assert normalise_text("\n\n") == ""


@pytest.mark.parametrize("value", AWKWARD)
def test_every_awkward_string_round_trips_through_yaml_and_toml(value: str) -> None:
    assert LOADER.load(f"v: {quote(value)}\n".encode(), source="t") == {"v": value}
    assert tomllib.loads(f"v = {quote(value)}\n") == {"v": value}


def test_a_lone_surrogate_cannot_be_written() -> None:
    with pytest.raises(UnicodeEncodeError):
        quote("bad \ud800 text")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("word", "word"),
        ("a/b.c-d@1+2", "a/b.c-d@1+2"),
        ("true", '"true"'),
        ("Yes", '"Yes"'),
        ("1.0.0", '"1.0.0"'),
        ("two words", '"two words"'),
        ("", '""'),
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (42, "42"),
    ],
)
def test_scalars(value: str | int | bool | None, expected: str) -> None:
    assert yaml_scalar(value) == expected


def test_quote_all_quotes_even_simple_words() -> None:
    assert yaml_scalar("word", quote_all=True) == '"word"'


def test_a_nested_document_has_a_fixed_layout() -> None:
    data: dict[str, Data] = {
        "schema": "orqlet.versions/v1",
        "cli": {"pinned": "0.1.0", "accepted": ["0.1.0"], "denied": []},
        "files": [{"path": "a.md", "tags": ["x", "y"]}, {"path": "b.md"}],
        "empty": {},
        "matrix": [["a", "b"], []],
        "flag": True,
        "nothing": None,
    }

    assert yaml_document(data) == (
        "schema: orqlet.versions/v1\n"
        "cli:\n"
        '  pinned: "0.1.0"\n'
        "  accepted:\n"
        '    - "0.1.0"\n'
        "  denied: []\n"
        "files:\n"
        "  - path: a.md\n"
        "    tags:\n"
        "      - x\n"
        '      - "y"\n'
        "  - path: b.md\n"
        "empty: {}\n"
        "matrix:\n"
        "  - - a\n"
        "    - b\n"
        "  - []\n"
        "flag: true\n"
        "nothing: null\n"
    )


def test_an_empty_document_is_an_empty_mapping() -> None:
    assert yaml_document({}) == "{}\n"


def test_front_matter_quotes_every_value_and_keeps_the_given_order() -> None:
    text = front_matter([("paths", ["src/**", "docs/*.md"]), ("description", "Rules: for src")])

    assert text == (
        '---\npaths:\n  - "src/**"\n  - "docs/*.md"\ndescription: "Rules: for src"\n---\n'
    )
    assert LOADER.load(text.strip("-\n").encode(), source="t") == {
        "paths": ["src/**", "docs/*.md"],
        "description": "Rules: for src",
    }


def test_front_matter_with_no_fields_is_an_empty_block() -> None:
    assert front_matter([]) == "---\n---\n"


def test_toml_tables_are_valid_toml_in_the_given_order() -> None:
    text = toml_table([("name", "orqlet-reviewer"), ("tags", ["a", "b"]), ("n", 3), ("on", True)])

    assert text == 'name = "orqlet-reviewer"\ntags = ["a", "b"]\nn = 3\non = true\n'
    assert tomllib.loads(text) == {
        "name": "orqlet-reviewer",
        "tags": ["a", "b"],
        "n": 3,
        "on": True,
    }


def test_toml_keys_that_are_not_bare_are_quoted() -> None:
    text = toml_table([("odd key", 1)], name="section")

    assert text == '[section]\n"odd key" = 1\n'
    assert tomllib.loads(text) == {"section": {"odd key": 1}}


def test_toml_refuses_null_and_nested_tables() -> None:
    with pytest.raises(ValueError, match="null"):
        toml_table([("a", None)])
    with pytest.raises(ValueError, match="nested"):
        toml_table([("a", {"b": 1})])


texts = st.text(max_size=30)
scalars = st.one_of(texts, st.integers(-(2**53), 2**53), st.booleans(), st.none())
keys = texts.filter(lambda key: key != "<<")
data_values: st.SearchStrategy[Data] = st.recursive(
    scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=3), st.dictionaries(keys, children, max_size=3)
    ),
    max_leaves=12,
)


@given(st.dictionaries(keys, data_values, max_size=4), st.booleans())
def test_any_data_survives_a_round_trip_through_the_strict_loader(
    data: dict[str, Data], quote_all: bool
) -> None:
    text = yaml_document(data, quote_all=quote_all)

    assert LOADER.load(text.encode("utf-8"), source="t") == (data or {})


@given(st.dictionaries(keys, data_values, max_size=4))
def test_emitting_twice_gives_identical_bytes(data: dict[str, Data]) -> None:
    assert yaml_document(data) == yaml_document(data)


# --- harness2-fit, phase P-3: `front_matter(..., plain_when_safe=True)` --------------------------
# Every test cites its `expected_behavior_source`. ADR-001 is
# docs/design/harness2-fit/design/adr-001-client-visible-front-matter.md; AC-1 to AC-3 are the
# acceptance criteria of phase P-3 and all of them rest on its decision 1. AC-4 (`yaml_scalar` and
# `yaml_document` keep their signatures and behaviour) has no new test: the tests above pin them
# and are unchanged.
#
# Deliberately not pinned, because the design leaves it open: strings inside lists or mappings when
# the keyword is true, keys, and how the predicate is built. Only the bytes of `front_matter` are
# checked, through its public signature.

RESERVED_WORDS = ("true", "false", "null", "yes", "no", "on", "off", "y", "n")
RESERVED_SPELLINGS = sorted(
    {
        spelling
        for word in RESERVED_WORDS
        for spelling in (
            word,
            word.upper(),
            word.capitalize(),
            word.swapcase(),
            word[:-1] + word[-1].upper(),
        )
    }
)

# The allow-list of ADR-001 decision 1, written out from its words and not from the emitter.
_ALLOW_LIST = re.compile(r"[A-Za-z][A-Za-z0-9 ,.;()/_+='-]*")


def spec_is_plain_safe(value: str) -> bool:
    return (
        _ALLOW_LIST.fullmatch(value) is not None
        and not value.endswith((" ", "'"))
        and value.lower() not in RESERVED_WORDS
    )


def plain_block(value: str) -> str:
    return front_matter([("key", value)], plain_when_safe=True)


def block_with(value: str, *, plain: bool) -> str:
    """The block that the design says is written for one string value of `key`."""
    return f"---\nkey: {value if plain else quote(value)}\n---\n"


PLAIN_SAFE_STRINGS = [
    "plain",
    "orqlet-arch-reviewer",
    "inherit",
    "Read, Grep, Glob",
    "A sample skill",
    "Keep functions small",
    "Check this repository's Orqlet setup and explain what needs attention",
    "Use only when the person runs it.",
    "Fill in the open facts of the project profile; a person approves it",
    "Reads a/b files (all of them), a_b + c = d",
    "AS-IS file",
    "A - B",
    "a",
    "Z",
    "x1",
    "v1.0.0",
    "n/a",
    "Yes please",
    "no way",
    "nullable",
    "trueish",
    "offer",
    "online",
    "a  b",  # two spaces inside are allowed
    "it's",
    "don't stop",
    "ends.",
    "ends,",
    "ends;",
    "ends)",
    "ends/",
    "ends_",
    "ends+",
    "ends=",
    "ends-",
]

NOT_PLAIN_SAFE_STRINGS = [
    "",  # the allow-list requires a first letter
    *RESERVED_SPELLINGS,
    # starts with a digit
    "1.10",
    "2026-10-20",
    "0x10",
    "3 apples",
    "9",
    # starts with a symbol or a space
    "~",
    "<<",
    ".inf",
    ".5",
    "-x",
    "- leading dash",
    "_x",
    "@at",
    "*star",
    "&anchor",
    "!tag",
    "%percent",
    "# hash",
    "[not, a list]",
    "{not: a map}",
    '"double"',
    "'single'",
    " leading space",
    " ",
    "(paren",
    "/slash",
    "+1",
    "=eq",
    ";semi",
    ",comma",
    # non-ASCII text, wherever it stands
    "ünïcödé ✓",
    "emoji 🙂",
    "café",
    "éa",
    "a\u0661",  # an Arabic-Indic digit is not an ASCII digit
    "\uff21BC",  # a full-width letter is not an ASCII letter
    "\u212aeep",  # the Kelvin sign is not an ASCII letter
    "a\u2028b",
    "a\u0085b",
    "a\ufeffb",
    "a\x7fb",
    "a\u00a0b",
    # a character that has a meaning in YAML, inside a text that starts with a letter
    "has: colon",
    "a:b",
    "a:",
    "a #b",
    "a#b",
    'say "hi"',
    "a\\b",
    "a[b]",
    "a{b}",
    "a|b",
    "a>b",
    "a<b",
    "a&b",
    "a*b",
    "a!b",
    "a%b",
    "a@b",
    "a`b",
    "a?b",
    "a~b",
    "a^b",
    "a$b",
    "a\tb",
    "line\nbreak",
    "a\rb",
    "abc\n",
    # ends with a space or an apostrophe
    "abc ",
    "abc  ",
    "abc'",
    "it's a dog'",
]


def test_the_tables_agree_with_the_allow_list_as_the_design_words_it() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 (guards these tables, not the code)."""
    assert all(spec_is_plain_safe(value) for value in PLAIN_SAFE_STRINGS)
    assert not any(spec_is_plain_safe(value) for value in NOT_PLAIN_SAFE_STRINGS)


# AC-1: without the keyword nothing changes.
@pytest.mark.parametrize("value", [*AWKWARD, *PLAIN_SAFE_STRINGS])
def test_without_the_keyword_every_string_is_quoted_as_today(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 1 (the default is today's output)."""
    assert front_matter([("key", value)]) == f"---\nkey: {quote(value)}\n---\n"


def test_without_the_keyword_a_block_is_byte_identical_to_today() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 1 (the default is today's output)."""
    text = front_matter(
        [
            ("name", "orqlet-sample"),
            ("description", "Keep functions small"),
            ("paths", ["docs", "src/**"]),
            ("model", "inherit"),
            ("readonly", True),
            ("count", 3),
            ("nothing", None),
        ]
    )

    assert text == (
        "---\n"
        'name: "orqlet-sample"\n'
        'description: "Keep functions small"\n'
        "paths:\n"
        '  - "docs"\n'
        '  - "src/**"\n'
        'model: "inherit"\n'
        "readonly: true\n"
        "count: 3\n"
        "nothing: null\n"
        "---\n"
    )


def test_an_explicit_false_gives_the_same_bytes_as_no_keyword() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 1 (`plain_when_safe: bool = False`)."""
    fields: list[tuple[str, Data]] = [
        ("name", "orqlet-sample"),
        ("paths", ["docs", "src/**"]),
        ("flag", True),
        ("count", 3),
    ]

    assert front_matter(fields, plain_when_safe=False) == front_matter(fields)


def test_the_keyword_is_keyword_only_and_false_by_default() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 1 (the signature that will exist)."""
    parameter = inspect.signature(front_matter).parameters["plain_when_safe"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is False


# AC-2: with the keyword a string is unquoted exactly when it is on the allow-list.
@pytest.mark.parametrize("value", PLAIN_SAFE_STRINGS)
def test_a_plain_safe_string_is_written_without_quotes(value: str) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 (the allow-list)."""
    assert plain_block(value) == block_with(value, plain=True)


@pytest.mark.parametrize("value", NOT_PLAIN_SAFE_STRINGS)
def test_any_other_string_is_quoted_exactly_as_today(value: str) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 (the allow-list excludes the rest)."""
    assert plain_block(value) == block_with(value, plain=False)


@pytest.mark.parametrize("value", AWKWARD)
def test_the_awkward_strings_are_unquoted_only_when_they_are_on_the_allow_list(
    value: str,
) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 (the allow-list)."""
    assert plain_block(value) == block_with(value, plain=spec_is_plain_safe(value))


def test_an_empty_string_stays_quoted() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 (plain-safe starts with a letter)."""
    assert plain_block("") == '---\nkey: ""\n---\n'


@pytest.mark.parametrize("word", RESERVED_SPELLINGS)
def test_a_reserved_word_stays_quoted_in_every_case(word: str) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 (reserved words, any case)."""
    assert plain_block(word) == f'---\nkey: "{word}"\n---\n'


def test_booleans_and_integers_are_written_as_today_with_the_keyword() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 (booleans and integers as today)."""
    fields: list[tuple[str, Data]] = [
        ("enabled", True),
        ("disabled", False),
        ("count", 42),
        ("below", -7),
        ("zero", 0),
    ]

    assert front_matter(fields, plain_when_safe=True) == (
        "---\nenabled: true\ndisabled: false\ncount: 42\nbelow: -7\nzero: 0\n---\n"
    )
    assert front_matter(fields, plain_when_safe=True) == front_matter(fields)


def test_each_string_of_a_block_is_decided_on_its_own_and_the_order_is_kept() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 (a string value is decided by itself)."""
    text = front_matter(
        [
            ("name", "orqlet-sample"),
            ("description", "A sample: with a colon"),
            ("model", "inherit"),
            ("note", "2026-10-23"),
            ("readonly", True),
        ],
        plain_when_safe=True,
    )

    assert text == (
        "---\n"
        "name: orqlet-sample\n"
        'description: "A sample: with a colon"\n'
        "model: inherit\n"
        'note: "2026-10-23"\n'
        "readonly: true\n"
        "---\n"
    )


_ALLOWED_TAIL = "aZ09 ,.;()/_+='-"
_OUTSIDE_THE_LIST = ':#"\\\t\n~<>[]{}*&!%@|?`^$\u00e9\u0661\u2028\u00a0'


def _joined(head: str, tail: str) -> str:
    return head + tail


def _with_inserted(text: str, char: str, at: int) -> str:
    return text[:at] + char + text[at:]


plain_like = st.builds(
    _joined, st.sampled_from("aZ"), st.text(alphabet=_ALLOWED_TAIL, max_size=10)
)  # mostly on the allow-list; some end in a space or an apostrophe, or are a reserved word
poisoned = st.builds(
    _with_inserted, plain_like, st.sampled_from(_OUTSIDE_THE_LIST), st.integers(0, 11)
)  # one character that is not on the allow-list, anywhere
allow_list_inputs = st.one_of(texts, plain_like, poisoned, st.sampled_from(RESERVED_SPELLINGS))


@given(allow_list_inputs)
def test_a_string_is_unquoted_exactly_when_it_is_on_the_allow_list(value: str) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 1 ("exactly when")."""
    assert plain_block(value) == block_with(value, plain=spec_is_plain_safe(value))


# AC-3, the rule-renderer part: rule files keep today's bytes. They carry project text, so their
# renderers do not pass the keyword.
def scoped(description: str, paths: tuple[str, ...] = ("docs", "tests/unit")) -> ScopedRule:
    return ScopedRule("plain", description, paths, "Body.\n", FileClass.GENERATED)


@pytest.mark.parametrize(
    "description",
    ["Keep functions small", "Public functions have type annotations", "Write tests"],
)
def test_a_cursor_rule_keeps_a_plain_safe_description_and_its_globs_quoted(
    description: str,
) -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (rule renderers do not pass it)."""
    text = cursor_rule(scoped(description)).content.decode()

    assert text.startswith(
        f'---\ndescription: "{description}"\n'
        'globs:\n  - "docs"\n  - "tests/unit"\n'
        "alwaysApply: false\n---\n"
    )


def test_a_claude_rule_keeps_plain_safe_paths_quoted() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (rule renderers do not pass it)."""
    text = claude_rule(scoped("Keep functions small")).content.decode()

    assert text.startswith('---\npaths:\n  - "docs"\n  - "tests/unit"\n---\n')


def test_rule_files_with_project_text_are_written_as_today() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (rule files keep today's bytes)."""
    odd = ScopedRule(
        "odd", 'Say "hi": now # ok', ("a: b/**", "- x", "#y"), "Body\n", FileClass.GENERATED
    )

    cursor = cursor_rule(odd).content.decode()
    claude = claude_rule(odd).content.decode()

    assert cursor.startswith(
        '---\ndescription: "Say \\"hi\\": now # ok"\n'
        'globs:\n  - "a: b/**"\n  - "- x"\n  - "#y"\n'
        "alwaysApply: false\n---\n"
    )
    assert claude.startswith('---\npaths:\n  - "a: b/**"\n  - "- x"\n  - "#y"\n---\n')
