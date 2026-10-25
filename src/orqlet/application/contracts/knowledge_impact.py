"""`orqlet.knowledge-impact/v1`: `docs/design/<task>/knowledge/P-<n>.yaml` (proposal 17.13).

One record per phase. A justified no-impact outcome is a first-class, reviewable result: it is the
alternative to inventing a document. Evidence of kind `private` does not exist in this schema, so
it is always rejected.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, NonNegativeInt, model_validator

from orqlet.application.contracts.common import (
    Contract,
    GitOid,
    RepoPath,
    SHA256Hex,
    Slug,
    Text,
)
from orqlet.application.contracts.review_input import ReviewInput

Action = Literal["add", "correct", "supersede", "remove", "unaffected", "proposal"]
WRITING = frozenset({"add", "correct", "supersede", "remove"})
NoImpactCategory = Literal[
    "internal-refactor",
    "test-only",
    "mechanical-dependency-change",
    "already-documented",
    "behaviour-unchanged",
]


class KnowledgeEvidence(Contract):
    kind: Literal["code", "test", "design", "adr", "source", "developer-statement"]
    ref: str = Field(min_length=1)  # path:lines, a test id, an anchor or a source id
    sha256: SHA256Hex


class Claim(Contract):
    id: str = Field(pattern=r"^CL-\d+$")
    anchor: str = Field(min_length=1)  # a heading or marker inside the draft that carries it
    evidence: tuple[KnowledgeEvidence, ...] = Field(min_length=1)


class Analysis(Contract):
    command: Literal["orqlet knowledge impact"]
    orqlet_version: str = Field(min_length=1)
    candidates_digest: SHA256Hex
    candidate_count: NonNegativeInt
    input: Literal["pre-draft-tree"]
    views: tuple[str, ...] = Field(min_length=1)
    index_state: str = Field(min_length=1)  # `not-used` or a generation id


class Entry(Contract):
    id: str = Field(pattern=r"^K-\d+$")
    candidate_ref: str | None = None  # null for an item the agent found and the analysis did not
    action: Action
    scope: Literal["project", "team", "company"]
    path: RepoPath | None = None
    replaces: str | None = None
    claims: tuple[Claim, ...] = ()
    reason: Text | None = None
    evidence: tuple[KnowledgeEvidence, ...] = ()
    owner: str | None = None

    @model_validator(mode="after")
    def _what_each_action_needs(self) -> Self:
        need: list[str] = []
        if self.action in {"add", "correct", "supersede"}:
            if self.path is None:
                need.append("a path")
            if not self.claims:
                need.append("at least one claim with evidence")
        if self.action == "supersede" and self.replaces is None:
            need.append("`replaces`")
        if self.action == "remove" and self.path is None:
            need.append("a path")
        if self.action in {"remove", "unaffected", "proposal"} and self.reason is None:
            need.append("a reason")
        if self.action in {"remove", "unaffected"} and not self.evidence:
            need.append("evidence")
        if self.action == "proposal" and self.owner is None:
            need.append("an owner")
        if need:
            raise ValueError(f"{self.id}: {self.action} needs {', '.join(need)}")
        return self


class AbsenceRecord(Contract):
    scopes_searched: tuple[str, ...] = Field(min_length=1)
    views: tuple[str, ...] = Field(min_length=1)
    revision: GitOid
    method: Text
    index_state: str = Field(min_length=1)
    candidates_found: NonNegativeInt


class DocumentedRef(Contract):
    path: RepoPath
    sha256: SHA256Hex


class NoImpact(Contract):
    category: NoImpactCategory
    reason: Text
    absence_record: AbsenceRecord
    already_documented_refs: tuple[DocumentedRef, ...] = ()

    @model_validator(mode="after")
    def _already_documented_names_what_documents_it(self) -> Self:
        if self.category == "already-documented" and not self.already_documented_refs:
            raise ValueError("`already-documented` needs the references that already say it")
        return self


class KnowledgeImpact(Contract):
    schema_id: Literal["orqlet.knowledge-impact/v1"] = Field(alias="schema")
    task: Slug
    phase: str = Field(pattern=r"^P-[1-9]\d*$")
    review_input: ReviewInput  # covers code_tests, knowledge, plan, standards and candidates
    outcome: Literal["updated", "no-impact"]
    analysis: Analysis
    entries: tuple[Entry, ...] = ()
    no_impact: NoImpact | None = None

    @model_validator(mode="after")
    def _outcome_matches_what_it_holds(self) -> Self:
        ids = [entry.id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("an entry id is used twice")
        if self.outcome == "updated":
            if self.no_impact is not None:
                raise ValueError("an `updated` outcome has no no_impact block")
            if not any(entry.action in WRITING for entry in self.entries):
                raise ValueError(
                    "`updated` needs an add, correct, supersede or remove entry; "
                    "a proposal never satisfies it"
                )
        else:
            if self.no_impact is None:
                raise ValueError("a `no-impact` outcome needs its no_impact block")
            if any(entry.action in WRITING for entry in self.entries):
                raise ValueError("a `no-impact` outcome lists every candidate as unaffected")
        return self
