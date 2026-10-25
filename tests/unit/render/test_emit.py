"""The emitters write the same bytes everywhere and survive awkward strings (ADR-005)."""

from __future__ import annotations

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
