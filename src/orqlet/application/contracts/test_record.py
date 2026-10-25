"""`orqlet.test-record/v1`: `docs/design/<task>/tests/P-<n>.yaml`.

The record is a developer-side summary and is `claimed`. The evidence that gates is the project's
own required checks concluding `success` on the head commit (proposal 6.14.1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract, SHA256Hex, Slug, Text
from orqlet.application.contracts.review_input import ReviewInput


class CommandRun(Contract):
    id: str = Field(min_length=1)  # a profile command id
    exit_code: int
    summary: Text  # size-capped
    result_digest: SHA256Hex  # of the captured output


class CriterionResult(Contract):
    ac: str = Field(pattern=r"^AC-\d+$")
    check_ref: str = Field(min_length=1)
    result: Literal["pass", "fail", "not-run"]


class TesterRecord(Contract):
    schema_id: Literal["orqlet.test-record/v1"] = Field(alias="schema")
    task: Slug
    phase: str = Field(pattern=r"^P-[1-9]\d*$")
    review_input: ReviewInput  # covers code_tests and plan
    verdict: Literal["PASS", "FAIL", "NOT_RUN"]
    evidence_kind: Literal["claimed"]
    commands: tuple[CommandRun, ...] = ()
    acceptance_coverage: tuple[CriterionResult, ...] = ()
