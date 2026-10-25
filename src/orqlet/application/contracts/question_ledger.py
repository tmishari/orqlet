"""`orqlet.question-ledger/v1`: `docs/design/<task>/questions.yaml` (proposal 18.2).

The ledger is a file committed with the task. A question has a canonical key, a stable hash of its
category and subject, so two agents asking the same thing produce one entry.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.common import Contract, SHA256Hex, Slug, Text, Timestamp

Category = Literal[
    "requirement",
    "access",
    "policy",
    "evidence-conflict",
    "missing-configuration",
    "test-expectation",
]
Phase = Literal["onboard", "research", "design", "plan", "implement", "review"]
Scope = Literal["task", "project", "company"]
Status = Literal["open", "answered", "withdrawn", "superseded"]


class Answer(Contract):
    value: Text
    answerer: str = Field(min_length=1)
    time: Timestamp
    scope: Scope


class Question(Contract):
    id: str = Field(pattern=r"^Q-\d+$")
    key: SHA256Hex  # sha256 of the canonical form of {category, subject}
    subject: Text
    raised_by: str = Field(min_length=1)
    phase: Phase
    category: Category
    text: Text
    why: Text
    options: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    blocks: tuple[str, ...] = ()  # phases or artifact sections that wait for the answer
    status: Status
    answer: Answer | None = None
    supersedes: tuple[str, ...] = ()
    invalidates: tuple[str, ...] = ()  # artifact paths made stale by a changed answer
    route_to: str | None = None  # for example `standards-owner`

    @model_validator(mode="after")
    def _answer_matches_status(self) -> Self:
        if self.status == "answered" and self.answer is None:
            raise ValueError(f"{self.id} is answered but has no answer")
        if self.status != "answered" and self.answer is not None:
            raise ValueError(f"{self.id} has an answer but its status is {self.status}")
        return self


class ConflictSource(Contract):
    ref: str = Field(min_length=1)
    claim: Text


class Ruling(Contract):
    governing_source: str = Field(min_length=1)
    rationale: Text
    who: str = Field(min_length=1)
    when: Timestamp
    expires: Timestamp | None = None


class Conflict(Contract):
    id: str = Field(pattern=r"^C-\d+$")
    sources: tuple[ConflictSource, ...] = Field(min_length=2)
    scope: Scope
    ruling_required_from: str = Field(min_length=1)
    ruling: Ruling | None = None


class QuestionLedger(Contract):
    schema_id: Literal["orqlet.question-ledger/v1"] = Field(alias="schema")
    task: Slug
    questions: tuple[Question, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
