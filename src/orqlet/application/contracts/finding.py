"""`orqlet.finding/v1`: what a reviewer returns (proposal 6.8).

A claim without evidence is an observation and never blocks. A finding that blocks must rest on
evidence: a digest of a quoted line, or an absence record saying what was searched, where and how.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.common import (
    Contract,
    GitOid,
    Glob,
    LineSpan,
    RepoPath,
    SHA256Hex,
    Text,
)

Category = Literal[
    "correctness",
    "failure-handling",
    "compatibility",
    "standards",
    "security",
    "tests",
    "docs",
    "architecture",
]


class QuoteEvidence(Contract):
    kind: Literal["quote"]
    path: RepoPath
    lines: LineSpan
    revision: GitOid
    quote_sha256: SHA256Hex


class AbsenceEvidence(Contract):
    """What was searched, where and how, for something that is not there."""

    kind: Literal["absence"]
    searched: tuple[Glob, ...] = Field(min_length=1)
    method: Text
    revision: GitOid


FindingEvidence = Annotated[QuoteEvidence | AbsenceEvidence, Field(discriminator="kind")]


class Finding(Contract):
    schema_id: Literal["orqlet.finding/v1"] = Field(default="orqlet.finding/v1", alias="schema")
    id: str = Field(pattern=r"^F-\d+$")
    kind: Literal["finding", "observation"]
    severity: Literal["blocking", "non-blocking", "info"]
    category: Category
    rule_ref: str | None = None
    evidence: tuple[FindingEvidence, ...] = ()
    claim: Text
    suggested_action: Text
    confidence: Literal["low", "medium", "high"]

    @model_validator(mode="after")
    def _only_evidence_can_block(self) -> Self:
        if self.kind == "finding" and not self.evidence:
            raise ValueError(
                f"{self.id}: a finding needs evidence; without it, it is an observation"
            )
        if self.kind == "observation" and self.severity == "blocking":
            raise ValueError(f"{self.id}: an observation never blocks")
        return self
