"""`validate ledger`: one entry per question, keys that cannot drift, answers kept."""

from __future__ import annotations

from typing import Any

import pytest

from orqlet.application.usecases.validate_ledger import question_key, validate_ledger
from orqlet.application.usecases.validation import ValidationResult
from orqlet.domain.findings import Verdict
from tests.support.artifacts import LEDGER, ledger, make_world, question

pytestmark = pytest.mark.unit


def run(document: dict[str, Any]) -> ValidationResult:
    world = make_world()
    world.put_yaml(LEDGER, document)
    return validate_ledger(world.services(), LEDGER)


def codes(result: ValidationResult) -> list[str]:
    return [finding.code for finding in result.findings]


def test_a_sound_ledger_passes_and_is_counted() -> None:
    result = run(ledger(questions=[question(1), question(2)]))

    assert result.verdict is Verdict.PASS
    assert (result.data["questions"], result.data["open"]) == (2, 2)


def test_the_key_ignores_case_and_spacing_and_depends_on_the_category() -> None:
    assert question_key("policy", "Release   Channel") == question_key(
        "policy", " release channel "
    )
    assert question_key("policy", "x") != question_key("requirement", "x")


def test_two_open_questions_with_one_key_are_one_question_asked_twice() -> None:
    first = question(1, subject="Release channel")
    second = question(2, subject="release  channel")

    result = run(ledger(questions=[first, second]))

    assert result.verdict is Verdict.FAIL
    assert codes(result) == ["ORQ-E381"]
    assert "Q-1, Q-2" in result.findings[0].message


def test_an_answered_question_may_share_its_key_with_a_new_open_one() -> None:
    answered = question(
        1,
        subject="Release channel",
        status="answered",
        answer={"value": "PyPI", "answerer": "m", "time": "2026-10-22", "scope": "project"},
    )
    again = question(2, subject="Release channel")

    assert run(ledger(questions=[answered, again])).verdict is Verdict.PASS


def test_a_key_that_is_not_the_hash_of_category_and_subject_is_refused() -> None:
    wrong = question(1)
    wrong["key"] = "0" * 64

    assert codes(run(ledger(questions=[wrong]))) == ["ORQ-E382"]


def test_ids_are_unique_and_supersession_points_at_a_real_question() -> None:
    duplicated = run(ledger(questions=[question(1), question(1, subject="Other")]))
    dangling = run(ledger(questions=[question(1, supersedes=["Q-9"])]))
    itself = run(ledger(questions=[question(1, supersedes=["Q-1"])]))

    assert "ORQ-E380" in codes(duplicated)
    assert codes(dangling) == ["ORQ-E383"]
    assert codes(itself) == ["ORQ-E383"]


def test_a_conflict_without_a_ruling_is_counted_not_failed() -> None:
    conflict = {
        "id": "C-1",
        "sources": [{"ref": "a.md", "claim": "one"}, {"ref": "b.md", "claim": "two"}],
        "scope": "project",
        "ruling_required_from": "maintainer",
    }

    result = run(ledger(conflicts=[conflict]))

    assert result.verdict is Verdict.PASS
    assert result.data["unruled_conflicts"] == 1


def test_the_ledger_names_the_task_of_its_folder() -> None:
    assert codes(run(ledger(task="other"))) == ["ORQ-E384"]
