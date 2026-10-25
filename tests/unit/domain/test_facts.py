import re

import pytest

from orqlet.domain.digest import sha256_hex
from orqlet.domain.facts import EvidenceError, find_line, line_range_hash, split_lines

pytestmark = pytest.mark.unit


def test_split_lines_normalises_crlf_and_ignores_the_final_break() -> None:
    assert split_lines(b"a\r\nb\nc\n") == [b"a", b"b", b"c"]
    assert split_lines(b"a\nb") == [b"a", b"b"]
    assert split_lines(b"") == []


def test_the_hash_covers_only_the_cited_lines() -> None:
    content = b"one\ntwo\nthree\n"

    assert line_range_hash(content, 2, 2) == sha256_hex(b"two")
    assert line_range_hash(content, 1, 2) == sha256_hex(b"one\ntwo")


def test_a_windows_and_a_unix_checkout_cite_the_same_hash() -> None:
    assert line_range_hash(b"a\r\nb\r\n", 1, 2) == line_range_hash(b"a\nb\n", 1, 2)


@pytest.mark.parametrize(("start", "end"), [(0, 1), (2, 1), (1, 4), (-1, 1)])
def test_a_range_outside_the_file_is_an_error(start: int, end: int) -> None:
    with pytest.raises(EvidenceError):
        line_range_hash(b"a\nb\nc\n", start, end)


def test_find_line_returns_the_first_match_or_none() -> None:
    content = b"[project]\nname = 'x'\nrequires-python = '>=3.12'\n"

    assert find_line(content, re.compile(rb"^requires-python")) == 3
    assert find_line(content, re.compile(rb"nothing")) is None
