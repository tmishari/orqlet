"""`orqlet.self-check/v1`: the report every role returns (proposal 18.4).

Self-checking does not replace independent review. The contract rejects a `pass` entry that cites
no evidence, so a check cannot be claimed without saying how it was made.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.common import Contract, Text


class CheckedAgainst(Contract):
    role: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    confirmed_requirements: tuple[str, ...] = ()
    applicable_standards: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


class Check(Contract):
    what: Text
    how: str  # an evidence reference or a command; empty only when the result is not a pass
    result: Literal["pass", "fail", "not-run"]

    @model_validator(mode="after")
    def _a_pass_says_how(self) -> Self:
        if self.result == "pass" and not self.how.strip():
            raise ValueError(f"the check {self.what!r} passed without saying how it was made")
        return self


class SelfCheck(Contract):
    schema_id: Literal["orqlet.self-check/v1"] = Field(alias="schema")
    checked_against: CheckedAgainst
    checks: tuple[Check, ...] = ()
    failures: tuple[str, ...] = ()
    unverified: tuple[str, ...] = ()  # claims or items that could not be verified
    questions: tuple[str, ...] = ()  # items needing developer input (also filed in the ledger)
