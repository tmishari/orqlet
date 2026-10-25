"""Evidence references: parsed from `a-b`, resolved against the bytes at a revision."""

from __future__ import annotations

import pytest

from orqlet.domain.digest import sha256_hex
from orqlet.domain.evidence import (
    EvidenceRef,
    EvidenceStatus,
    InvalidEvidence,
    check_reference,
)
from orqlet.domain.facts import line_range_hash

pytestmark = pytest.mark.unit

CONTENT = b"one\ntwo\nthree\nfour\n"


def ref(lines: str, sha256: str | None = None) -> EvidenceRef:
    cited = sha256 if sha256 is not None else line_range_hash(CONTENT, *_span(lines))
    return EvidenceRef.parse("src/a.py", lines, "a" * 40, cited)


def _span(lines: str) -> tuple[int, int]:
    first, _, last = lines.partition("-")
    return int(first), int(last or first)


def test_a_reference_to_unchanged_lines_resolves() -> None:
    assert check_reference(ref("2-3"), CONTENT) is EvidenceStatus.RESOLVED


def test_a_single_line_is_written_without_a_dash_and_read_back() -> None:
    single = ref("4")

    assert (single.start, single.end, single.lines) == (4, 4, "4")
    assert check_reference(single, CONTENT) is EvidenceStatus.RESOLVED


def test_changed_lines_are_reported_as_changed() -> None:
    assert check_reference(ref("1-2"), b"one\nTWO\nthree\n") is EvidenceStatus.CHANGED


def test_lines_beyond_the_end_of_the_file_are_out_of_range() -> None:
    assert check_reference(ref("3-4", sha256_hex(b"x")), b"one\ntwo\nthree\n") is (
        EvidenceStatus.OUT_OF_RANGE
    )


def test_a_file_missing_at_the_revision_is_missing() -> None:
    assert check_reference(ref("1"), None) is EvidenceStatus.MISSING


def test_line_endings_do_not_change_the_hash() -> None:
    assert check_reference(ref("1-2"), CONTENT.replace(b"\n", b"\r\n")) is EvidenceStatus.RESOLVED


@pytest.mark.parametrize("lines", ["", "0", "0-3", "3-1", "a-b", "1-", "-2", "1,2", "1 - 2"])
def test_malformed_line_ranges_are_refused(lines: str) -> None:
    with pytest.raises(InvalidEvidence):
        EvidenceRef.parse("src/a.py", lines, "a" * 40, "0" * 64)
