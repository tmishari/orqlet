"""`orqlet validate ledger`: the question ledger, `docs/design/<task>/questions.yaml` (proposal 18).

The ledger is a file. Two open entries may not share a canonical key, so a question asked twice
is one entry, and an answered question is read as a confirmed requirement and not asked again.
"""

from __future__ import annotations

import re
from collections import Counter

from orqlet.application.contracts.question_ledger import Question, QuestionLedger
from orqlet.application.usecases.validation import (
    Collector,
    ValidateServices,
    ValidationResult,
    read_artifact,
    task_of,
)
from orqlet.domain.digest import digest_of

LEDGER_FILE = "questions.yaml"


def question_key(category: str, subject: str) -> str:
    """The stable hash of category and subject: case and spacing never make a new question."""
    normal = re.sub(r"\s+", " ", subject.strip()).casefold()
    return digest_of({"category": category, "subject": normal})


def validate_ledger(services: ValidateServices, raw_path: str) -> ValidationResult:
    out = Collector()
    ledger, _, _ = read_artifact(services, raw_path, QuestionLedger, out)
    if ledger is None:
        return out.result()
    expected_task = task_of(raw_path)
    if expected_task is not None and ledger.task != expected_task:
        out.error(
            "ORQ-E384",
            f"the ledger names task {ledger.task} but sits in the folder of {expected_task}",
            raw_path,
        )
    _check_ids(ledger, out, raw_path)
    _check_keys(ledger, out, raw_path)
    _check_references(ledger, out, raw_path)
    return out.result(
        {
            "questions": len(ledger.questions),
            "open": sum(1 for q in ledger.questions if q.status == "open"),
            "conflicts": len(ledger.conflicts),
            "unruled_conflicts": sum(1 for c in ledger.conflicts if c.ruling is None),
        }
    )


def blocking_questions(ledger: QuestionLedger, phase: str) -> tuple[Question, ...]:
    """Open questions that name `phase` in their blocking set: that phase has to wait."""
    return tuple(q for q in ledger.questions if q.status == "open" and phase in q.blocks)


def _check_ids(ledger: QuestionLedger, out: Collector, path: str) -> None:
    for kind, ids in (
        ("question", [q.id for q in ledger.questions]),
        ("conflict", [c.id for c in ledger.conflicts]),
    ):
        for duplicate, count in sorted(Counter(ids).items()):
            if count > 1:
                out.error("ORQ-E380", f"the {kind} id {duplicate} is used {count} times", path)


def _check_keys(ledger: QuestionLedger, out: Collector, path: str) -> None:
    open_by_key: dict[str, list[str]] = {}
    for question in ledger.questions:
        wanted = question_key(question.category, question.subject)
        if question.key != wanted:
            out.error(
                "ORQ-E382",
                f"{question.id} has the key {question.key[:12]}…; its category and subject "
                f"give {wanted[:12]}…",
                path,
            )
        if question.status == "open":
            open_by_key.setdefault(question.key, []).append(question.id)
    for ids in open_by_key.values():
        if len(ids) > 1:
            out.error(
                "ORQ-E381",
                f"{', '.join(ids)} are open and ask the same thing (they share one key)",
                path,
            )


def _check_references(ledger: QuestionLedger, out: Collector, path: str) -> None:
    known = {q.id for q in ledger.questions}
    for question in ledger.questions:
        for other in (*question.supersedes,):
            if other not in known:
                out.error("ORQ-E383", f"{question.id} supersedes unknown {other}", path)
            elif other == question.id:
                out.error("ORQ-E383", f"{question.id} supersedes itself", path)
