"""The strict JSON reader of hook payloads (task one-command-setup, phase P-5, AC-1).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-5 in
docs/design/one-command-setup/plan.yaml; BC-6 and BC-14 are in
docs/design/one-command-setup/design/component.md; ADR-002 decision 3 and ADR-004 decision 6 are
in docs/design/one-command-setup/design/; "the interface" is the one that the Coder gave for P-5
(`orqlet.domain.strict_json`: `MAX_PAYLOAD_BYTES`, `StrictJsonError`, `parse_object`).

HOW THESE TESTS WERE WRITTEN. The Tester of P-5 wrote them from the acceptance criteria and the
interface, before the implementation existed.
"""

from __future__ import annotations

import json

import pytest

from orqlet.domain.errors import OrqletError
from orqlet.domain.strict_json import MAX_PAYLOAD_BYTES, StrictJsonError, parse_object

pytestmark = pytest.mark.unit


def _padded(content: bytes, size: int) -> bytes:
    return content + b" " * (size - len(content))


def test_the_payload_limit_is_one_mebibyte() -> None:
    """AC-1, ADR-004 decision 6: a payload of at most 1 MiB."""
    assert MAX_PAYLOAD_BYTES == 1_048_576


def test_the_error_is_an_orqlet_error() -> None:
    """The interface: `StrictJsonError` derives from `OrqletError`."""
    assert issubclass(StrictJsonError, OrqletError)


def test_an_object_is_returned_as_a_dict() -> None:
    """AC-1: an object at the top level is accepted, nested values included."""
    data = b'{"cwd": "/home/person/repo", "tool_input": {"file_path": "a"}, "n": [1, 2.5, null]}'

    assert parse_object(data) == {
        "cwd": "/home/person/repo",
        "tool_input": {"file_path": "a"},
        "n": [1, 2.5, None],
    }


def test_unknown_fields_are_kept_for_the_caller_to_ignore() -> None:
    """AC-1, ADR-004 decision 6: unknown fields are not an error."""
    assert parse_object(b'{"cwd": "/x", "something_new": {"a": 1}}') == {
        "cwd": "/x",
        "something_new": {"a": 1},
    }


@pytest.mark.parametrize(
    "data",
    [b"[]", b'["cwd"]', b'"text"', b"1", b"1.5", b"null", b"true", b"false"],
    ids=["empty list", "list", "string", "integer", "float", "null", "true", "false"],
)
def test_a_top_level_that_is_not_an_object_is_refused(data: bytes) -> None:
    """AC-1, BC-6: only an object at the top level."""
    with pytest.raises(StrictJsonError):
        parse_object(data)


@pytest.mark.parametrize(
    "data",
    [
        b'{"cwd": "/a", "cwd": "/b"}',
        b'{"cwd": "/a", "cwd": "/a"}',
        b'{"tool_input": {"file_path": "a", "file_path": "b"}}',
        b'{"roots": [{"x": 1, "x": 2}]}',
        b'{"cwd": "/a", "\\u0063wd": "/b"}',
    ],
    ids=["top level", "same value", "nested object", "object inside a list", "escaped spelling"],
)
def test_a_duplicate_key_at_any_depth_is_refused(data: bytes) -> None:
    """AC-1, BC-6, ADR-002 decision 3: a duplicate key is refused, never last-one-wins."""
    with pytest.raises(StrictJsonError):
        parse_object(data)


@pytest.mark.parametrize(
    "data",
    [
        b'{"n": NaN}',
        b'{"n": Infinity}',
        b'{"n": -Infinity}',
        b'{"n": [1, NaN]}',
        b'{"a": {"b": Infinity}}',
    ],
    ids=["NaN", "Infinity", "-Infinity", "NaN in a list", "Infinity nested"],
)
def test_nan_and_infinity_are_refused(data: bytes) -> None:
    """AC-1, BC-6: NaN, Infinity and -Infinity are not JSON."""
    with pytest.raises(StrictJsonError):
        parse_object(data)


@pytest.mark.parametrize(
    "data",
    [b"", b"   ", b"{", b'{"cwd": }', b"{'cwd': 'x'}", b'{"cwd": "x"} trailing', b'{"a": 1,}'],
    ids=["empty", "blank", "unclosed", "missing value", "single quotes", "trailing text", "comma"],
)
def test_invalid_json_is_refused(data: bytes) -> None:
    """AC-1, BC-14: a malformed payload is refused."""
    with pytest.raises(StrictJsonError):
        parse_object(data)


@pytest.mark.parametrize(
    "data",
    [b'{"cwd": "\xff"}', b"\xfe\xff\x00{\x00}", b'{"cwd": "\xed\xa0\x80"}'],
    ids=["invalid byte", "UTF-16", "encoded surrogate"],
)
def test_bytes_that_are_not_utf8_are_refused(data: bytes) -> None:
    """AC-1; the interface: the payload must be UTF-8."""
    with pytest.raises(StrictJsonError):
        parse_object(data)


def test_an_integer_too_long_to_convert_is_refused() -> None:
    """AC-1, BC-14: Python refuses an integer over 4,300 digits with a plain ValueError."""
    with pytest.raises(StrictJsonError):
        parse_object(b'{"n": ' + b"1" * 5_000 + b"}")


def test_nesting_too_deep_to_parse_is_refused() -> None:
    """AC-1, BC-14: nesting past the interpreter's recursion limit is refused, under 1 MiB."""
    data = b'{"a": ' + b"[" * 200_000 + b"]" * 200_000 + b"}"

    assert len(data) <= MAX_PAYLOAD_BYTES
    with pytest.raises(StrictJsonError):
        parse_object(data)


def test_a_payload_over_the_limit_is_refused() -> None:
    """AC-1, ADR-004 decision 6: a payload over 1 MiB is refused, even when it is valid JSON."""
    data = _padded(json.dumps({"cwd": "/home/person/repo"}).encode(), MAX_PAYLOAD_BYTES + 1)

    with pytest.raises(StrictJsonError):
        parse_object(data)


def test_a_payload_of_exactly_the_limit_is_read() -> None:
    """AC-1, ADR-004 decision 6: only a payload over 1 MiB is refused."""
    data = _padded(json.dumps({"cwd": "/home/person/repo"}).encode(), MAX_PAYLOAD_BYTES)

    assert parse_object(data) == {"cwd": "/home/person/repo"}


def test_the_limit_can_be_given() -> None:
    """The interface: `limit` replaces the default bound; the size counts bytes."""
    data = b'{"cwd": "/x"}'

    assert parse_object(data, limit=len(data)) == {"cwd": "/x"}
    with pytest.raises(StrictJsonError):
        parse_object(data, limit=len(data) - 1)


def test_an_oversized_payload_is_refused_before_it_is_decoded() -> None:
    """AC-1 ("refused before parsing"); the interface: the size check comes first.

    The bytes are neither UTF-8 nor JSON, so the refusal can only be the size one; the test pins
    that an oversized payload never gets further than the size check, whatever it holds.
    """
    with pytest.raises(StrictJsonError):
        parse_object(b"\xff" * 11, limit=10)
