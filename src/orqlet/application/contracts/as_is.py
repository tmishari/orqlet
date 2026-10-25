"""`orqlet.as-is/v1` and its fragments: facts only (proposal 17.3 and 17.11).

There is no field for proposals, opinions, refactoring or future architecture. Every fact carries
evidence that resolves at the bound revision. Unknowns and contradictions are never counted
against the size budget and never dropped.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, PositiveInt, model_validator

from orqlet.application.contracts.artifact_header import ArtifactHeader
from orqlet.application.contracts.common import (
    Contract,
    GitOid,
    Glob,
    LineSpan,
    RepoPath,
    SHA256Hex,
    Slug,
    Text,
)
from orqlet.application.contracts.self_check import SelfCheck

FactKind = Literal["structure", "interface", "dependency", "flow", "test", "operation"]
ResearchMode = Literal["parallel-subagents", "sequential-subagents", "sequential"]


class FactEvidence(Contract):
    path: RepoPath
    lines: LineSpan
    revision: GitOid
    sha256: SHA256Hex


class Fact(Contract):
    id: str = Field(pattern=r"^A-\d+$")
    kind: FactKind
    statement: Text  # one factual sentence
    evidence: tuple[FactEvidence, ...] = Field(min_length=1)


class Unknown(Contract):
    id: str = Field(pattern=r"^U-\d+$")
    what: Text
    material: bool
    question_ref: str | None = Field(default=None, pattern=r"^Q-\d+$")
    merged_from: tuple[str, ...] = ()  # fragment ids this entry stands for


class Contradiction(Contract):
    id: str = Field(pattern=r"^C-\d+$")
    sources: tuple[str, ...] = Field(min_length=2)
    note: Text
    merged_from: tuple[str, ...] = ()


class AsIsScope(Contract):
    paths: tuple[Glob, ...] = Field(min_length=1)
    request_ref: Slug  # the task slug


class SizeBudget(Contract):
    max_words: PositiveInt


class AsIsArtifact(Contract):
    schema_id: Literal["orqlet.as-is/v1"] = Field(alias="schema")
    header: ArtifactHeader
    base_revision: GitOid
    scope: AsIsScope
    research_mode: ResearchMode
    limitation: Text | None = None
    size_budget: SizeBudget
    facts: tuple[Fact, ...] = ()
    unknowns: tuple[Unknown, ...] = ()
    contradictions: tuple[Contradiction, ...] = ()
    self_check: SelfCheck

    @model_validator(mode="after")
    def _limitation_matches_mode(self) -> Self:
        if self.research_mode == "parallel-subagents" and self.limitation is not None:
            raise ValueError("a limitation is recorded only when research was not parallel")
        if self.research_mode != "parallel-subagents" and self.limitation is None:
            raise ValueError(f"research_mode {self.research_mode} needs a limitation text")
        return self


class AsIsFragment(Contract):
    """What one researcher returns for one repository area. Fragments are merged, never dropped."""

    schema_id: Literal["orqlet.as-is-fragment/v1"] = Field(alias="schema")
    fragment_id: Slug
    base_revision: GitOid
    scope: AsIsScope
    facts: tuple[Fact, ...] = ()
    unknowns: tuple[Unknown, ...] = ()
    contradictions: tuple[Contradiction, ...] = ()
