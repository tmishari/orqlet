"""The strict YAML loader refuses everything outside its small, safe subset."""

from __future__ import annotations

import contextlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.documents import DocumentError

pytestmark = pytest.mark.unit

LOADER = StrictYamlLoader()


def load(text: str) -> object:
    return LOADER.load(text.encode("utf-8"), source="test.yaml")


def test_a_plain_document_loads_to_plain_data() -> None:
    assert load("a: 1\nb: [x, true, null]\nc: {d: 1.5}\n") == {
        "a": 1,
        "b": ["x", True, None],
        "c": {"d": 1.5},
    }


def test_an_empty_document_is_none() -> None:
    assert load("") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("v: no", "no"),
        ("v: yes", "yes"),
        ("v: on", "on"),
        ("v: off", "off"),
        ("v: 2026-10-20", "2026-10-20"),
        ("v: 0x10", "0x10"),
        ("v: 1_000", "1_000"),
        ("v: 1:30", "1:30"),
        ("v: '1.10'", "1.10"),
    ],
)
def test_yaml_one_one_surprises_stay_strings(text: str, expected: str) -> None:
    assert load(text) == {"v": expected}


def test_an_unquoted_version_like_1_10_is_a_number_not_a_string() -> None:
    assert load("v: 1.10") == {"v": 1.1}


@pytest.mark.parametrize(
    "text",
    [
        "a: &x 1\nb: *x\n",
        "a: &x 1\n",
        "base: &b {x: 1}\nother:\n  <<: *b\n",
        "<<: {x: 1}\n",
        "a: 1\na: 2\n",
        "1: x\n",
        "? [a, b]\n: x\n",
        "v: !!python/object/apply:os.system [echo hi]\n",
        "v: !!binary aGk=\n",
        "v: !!timestamp 2026-10-20\n",
        "v: !custom x\n",
        "---\na: 1\n---\nb: 2\n",
    ],
)
def test_forbidden_constructs_are_rejected(text: str) -> None:
    with pytest.raises(DocumentError):
        load(text)


def test_billion_laughs_is_refused_at_the_first_alias() -> None:
    text = (
        "a: &a [x, x, x, x, x, x, x, x, x]\n"
        "b: &b [*a, *a, *a, *a, *a, *a, *a, *a, *a]\n"
        "c: &c [*b, *b, *b, *b, *b, *b, *b, *b, *b]\n"
    )
    with pytest.raises(DocumentError):
        load(text)


def test_size_limit_applies_before_parsing() -> None:
    with pytest.raises(DocumentError, match="larger than"):
        StrictYamlLoader(max_bytes=10).load(b"a: " + b"x" * 20, source="t")


def test_depth_limit_is_enforced() -> None:
    with pytest.raises(DocumentError, match="deeper"):
        StrictYamlLoader(max_depth=5).load(b"[" * 10 + b"]" * 10, source="t")


def test_node_limit_is_enforced() -> None:
    with pytest.raises(DocumentError, match="nodes"):
        StrictYamlLoader(max_nodes=10).load(("[" + ",".join(["1"] * 50) + "]").encode(), source="t")


def test_invalid_utf8_is_rejected() -> None:
    with pytest.raises(DocumentError, match="UTF-8"):
        LOADER.load(b"a: \xff\xfe", source="t")


def test_a_huge_integer_is_an_error_not_a_crash() -> None:
    with pytest.raises(DocumentError):
        load("v: " + "9" * 5000)


def test_error_messages_name_the_source_and_line_but_not_the_content() -> None:
    with pytest.raises(DocumentError) as raised:
        load("a: 1\nb: [unclosed\nsecret-token-value: 1\n")

    message = str(raised.value)
    assert message.startswith("test.yaml:")
    assert "secret-token-value" not in message


@given(st.text(max_size=200))
def test_any_text_either_loads_or_raises_only_document_error(text: str) -> None:
    with contextlib.suppress(DocumentError):
        load(text)


def test_a_control_character_is_a_document_error() -> None:
    with pytest.raises(DocumentError):
        load("a: \x1f")
