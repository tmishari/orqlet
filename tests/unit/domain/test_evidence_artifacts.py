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


# --- the code reviewer role (task dynamic-model-profiles, phase P-9, AC-1) ----------------------
# Each test names its `expected_behavior_source`: AC-1 of phase P-9 in
# docs/design/dynamic-model-profiles/plan.yaml, BC-36 of design/component.md and ADR-006
# decision 6. The effects "left out of code_tests and knowledge" and "no ORQ-E400" happen in
# binding_inputs.py and validate_records.py: the first is shown through `review prepare` in
# test_review_prepare.py, the second is covered here at the predicate only.

CODE_REVIEW = "docs/design/demo/reviews/code-reviewer-P-4-r3.yaml"
REVIEWER_ROLES = ("architecture-reviewer", "security-reviewer", "code-reviewer")


def excluded_path(path: str, **overrides: object) -> bool:
    arguments: dict[str, object] = {
        "mode": "100644",
        "task_exists": True,
        "schema_valid": True,
        "content_matches_path": True,
        **overrides,
    }
    return is_excluded(path, **arguments)  # type: ignore[arg-type]


def test_a_code_reviewer_path_is_a_review_record_with_its_identity() -> None:
    """expected_behavior_source: P-9 AC-1 ("the record-path pattern admits `code-reviewer`, so
    `docs/design/<task>/reviews/code-reviewer-P-<n>-r<k>.yaml` is recognised as a review
    record"); ADR-006 decision 6 (the pattern admitted only two roles, so a `code-reviewer`
    record would be rejected)."""
    assert parse_evidence_path(CODE_REVIEW) == EvidencePath(
        RecordKind.REVIEW, "demo", "P-4", "code-reviewer", 3
    )


@pytest.mark.parametrize("role", REVIEWER_ROLES)
def test_each_of_the_three_reviewer_roles_gives_a_review_record(role: str) -> None:
    """expected_behavior_source: P-9 AC-1 ("admits `code-reviewer` in addition to" the roles of
    the other two records, "like the records of the other two roles"); ADR-006 decision 6."""
    path = f"docs/design/demo/reviews/{role}-P-12-r10.yaml"

    assert parse_evidence_path(path) == EvidencePath(RecordKind.REVIEW, "demo", "P-12", role, 10)


def test_a_code_reviewer_record_meets_the_three_conditions_and_is_excluded() -> None:
    """expected_behavior_source: P-9 AC-1 ("is left out of `code_tests` and `knowledge` like the
    records of the other two roles"); the module docstring (a path is excluded when all three
    conditions hold)."""
    assert excluded_path(CODE_REVIEW)


@pytest.mark.parametrize(
    "failing",
    [
        {"task_exists": False},
        {"mode": "120000"},
        {"mode": "100755"},
        {"schema_valid": False},
        {"content_matches_path": False},
    ],
    ids=["no-task", "symbolic-link", "executable", "invalid-schema", "content-names-another-role"],
)
def test_a_code_reviewer_path_is_not_excluded_when_any_one_condition_fails(
    failing: dict[str, object],
) -> None:
    """expected_behavior_source: P-9 AC-1 ("a path of the right shape whose content names another
    role is not excluded", which is `content_matches_path=False`); the module docstring (all
    three conditions must hold, else the file is an ordinary input)."""
    assert not excluded_path(CODE_REVIEW, **failing)


@pytest.mark.parametrize(
    "role",
    [
        "code-reviewers",
        "Code-Reviewer",
        "code-reviewer2",
        "xcode-reviewer",
        "architecture-code-reviewer",
        "code-reviewer-architecture-reviewer",
        "coder",
        "",
    ],
    ids=[
        "plural",
        "capitalised",
        "digit-suffix",
        "prefixed",
        "joined-with-another-role",
        "followed-by-another-role",
        "coder",
        "empty-role",
    ],
)
def test_a_path_with_any_other_role_name_stays_an_ordinary_input(role: str) -> None:
    """expected_behavior_source: P-9 AC-1 ("a path with any other role name stays an ordinary
    input"); ADR-006 decision 6 (only the third role is added)."""
    path = f"docs/design/demo/reviews/{role}-P-1-r1.yaml"

    assert parse_evidence_path(path) is None
    assert not excluded_path(path)  # every condition holds, yet no pattern names the path


@pytest.mark.parametrize(
    "path",
    [
        "docs/design/demo/reviews/code-reviewer-P-1-r0.yaml",
        "docs/design/demo/reviews/code-reviewer-P-0-r1.yaml",
        "docs/design/demo/reviews/code-reviewer-P-1-r1.yml",
        "docs/design/demo/reviews/code-reviewer-P-1-r1.yaml.bak",
        "docs/design/demo/reviews/code-reviewer-P-1.yaml",
        "docs/design/demo/reviews/sub/code-reviewer-P-1-r1.yaml",
        "docs/design/demo/extra/reviews/code-reviewer-P-1-r1.yaml",
        "docs/design/Demo/reviews/code-reviewer-P-1-r1.yaml",
        "docs/design/demo/tests/code-reviewer-P-1-r1.yaml",
        "src/docs/design/demo/reviews/code-reviewer-P-1-r1.yaml",
    ],
)
def test_the_code_reviewer_path_is_as_exact_as_the_other_two(path: str) -> None:
    """expected_behavior_source: P-9 AC-1 ("a path with any other ... stays an ordinary input");
    the module docstring (it matches exactly one of three patterns); the existing cases of
    `test_anything_that_is_not_an_exact_match_is_an_ordinary_input` for the other two roles."""
    assert parse_evidence_path(path) is None


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
