"""Which paths are evidence records, and the three conditions for leaving the binding."""

from __future__ import annotations

import pytest

from orqlet.domain.binding import RecordKind
from orqlet.domain.evidence_artifacts import (
    EvidencePath,
    is_excluded,
    parse_evidence_path,
    rounds_are_contiguous,
)

pytestmark = pytest.mark.unit

REVIEW = "docs/design/demo/reviews/architecture-reviewer-P-1-r2.yaml"
TEST = "docs/design/demo/tests/P-3.yaml"
KNOWLEDGE = "docs/design/demo/knowledge/P-12.yaml"


def test_the_three_exact_patterns_give_the_identity_a_path_states() -> None:
    assert parse_evidence_path(REVIEW) == EvidencePath(
        RecordKind.REVIEW, "demo", "P-1", "architecture-reviewer", 2
    )
    assert parse_evidence_path(TEST) == EvidencePath(RecordKind.TEST, "demo", "P-3")
    assert parse_evidence_path(KNOWLEDGE) == EvidencePath(
        RecordKind.KNOWLEDGE_IMPACT, "demo", "P-12"
    )


@pytest.mark.parametrize(
    "path",
    [
        "docs/design/demo/reviews/helper.py",
        "docs/design/demo/reviews/architecture-reviewer-P-1-r0.yaml",
        "docs/design/demo/reviews/coder-P-1-r1.yaml",
        "docs/design/demo/reviews/sub/architecture-reviewer-P-1-r1.yaml",
        "docs/design/Demo/tests/P-1.yaml",
        "docs/design/demo/tests/P-0.yaml",
        "docs/design/demo/tests/P-1.yml",
        "docs/design/demo/tests/P-1.yaml.bak",
        "docs/design/demo/knowledge/notes.yaml",
        "docs/design/tests/P-1.yaml",
        "src/docs/design/demo/tests/P-1.yaml",
    ],
)
def test_anything_that_is_not_an_exact_match_is_an_ordinary_input(path: str) -> None:
    assert parse_evidence_path(path) is None


def excluded(**overrides: object) -> bool:
    arguments: dict[str, object] = {
        "mode": "100644",
        "task_exists": True,
        "schema_valid": True,
        "content_matches_path": True,
        **overrides,
    }
    return is_excluded(REVIEW, **arguments)  # type: ignore[arg-type]


def test_a_record_that_meets_all_three_conditions_is_excluded() -> None:
    assert excluded()


@pytest.mark.parametrize(
    "failing",
    [
        {"task_exists": False},
        {"mode": "120000"},
        {"mode": "100755"},
        {"schema_valid": False},
        {"content_matches_path": False},
    ],
)
def test_failing_any_one_condition_keeps_the_file_in_the_binding(
    failing: dict[str, object],
) -> None:
    assert not excluded(**failing)


def test_a_path_with_no_pattern_is_never_excluded() -> None:
    assert not is_excluded(
        "docs/design/demo/reviews/helper.py",
        mode="100644",
        task_exists=True,
        schema_valid=True,
        content_matches_path=True,
    )


@pytest.mark.parametrize(
    ("rounds", "expected"),
    [
        ([1], True),
        ([1, 2, 3], True),
        ([3, 1, 2], True),
        ([1, 1, 2], True),
        ([1, 3], False),
        ([2], False),
        ([], False),
    ],
)
def test_rounds_must_run_without_a_gap_from_one(rounds: list[int], expected: bool) -> None:
    assert rounds_are_contiguous(rounds) is expected
