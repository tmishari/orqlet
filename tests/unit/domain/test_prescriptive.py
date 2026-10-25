"""The prescriptive-language lint finds advice that crept into a statement of fact."""

from __future__ import annotations

import pytest

from orqlet.domain.prescriptive import prescriptive_hits

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "statement",
    [
        "The parser should be rewritten.",
        "We recommend splitting the module.",
        "It would be better to cache the result.",
        "This needs to be refactored.",
        "Ideally the client retries.",
        "Consider moving the loader into an adapter.",
        "A future version could drop it.",
    ],
)
def test_advice_is_flagged(statement: str) -> None:
    assert prescriptive_hits(statement)


@pytest.mark.parametrize(
    "statement",
    [
        "The loader reads the file and returns a dict.",
        "`save()` raises `OSError` when the disk is full.",
        "The test suite has 12 tests for the parser.",
        "Shoulder-high walls are not a code concept.",  # `should` inside another word
    ],
)
def test_statements_of_fact_are_not_flagged(statement: str) -> None:
    assert prescriptive_hits(statement) == ()


def test_hits_are_reported_in_order_with_their_offset_and_lower_case() -> None:
    hits = prescriptive_hits("It Should be fixed. We Recommend a rewrite.")

    assert [(h.phrase, h.offset) for h in hits] == [("should", 3), ("recommend", 23)]
