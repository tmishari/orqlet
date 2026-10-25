"""`orqlet.implementation-plan/v1`: `docs/design/<task>/plan.yaml` (proposal 17.5 and 17.11).

The plan is reviewable evidence and a structural check. It makes invented paths visible; it does
not prove the plan is right. `structural_changes` is derived by the validator from the operations
and is not a field here, so an author cannot supply it.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.artifact_header import ArtifactHeader
from orqlet.application.contracts.common import Contract, GitOid, Glob, RepoPath, Text
from orqlet.application.contracts.self_check import SelfCheck

REQUIRED_REVIEW_EVIDENCE = frozenset({"architecture-reviewer", "security-reviewer", "tester"})


class PlanFileOperation(Contract):
    op: Literal["create", "modify", "delete"]
    path: RepoPath
    why: Text
    moved_from: RepoPath | None = None  # only a `create` may carry it (validated with the plan)


class AcceptanceCriterion(Contract):
    id: str = Field(pattern=r"^AC-\d+$")
    text: Text  # a testable statement
    source: str = Field(min_length=1)  # a requirement or question reference
    check_ref: str = Field(min_length=1)  # a profile command id or a review item


class Phase(Contract):
    id: str = Field(pattern=r"^P-\d+$")
    objective: Text
    depends_on: tuple[str, ...] = ()
    implements: tuple[str, ...] = ()  # `EC-n` or `EC-n@S-n`
    expected_lock_packages: tuple[str, ...] = ()
    file_operations: tuple[PlanFileOperation, ...] = ()
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()
    checks: tuple[str, ...] = ()
    review_evidence: tuple[Literal["architecture-reviewer", "security-reviewer", "tester"], ...]
    knowledge_step: Literal["required"]  # there is no way to omit it
    completion: tuple[Text, ...] = ()
    expected_outputs: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _all_review_evidence(self) -> Self:
        if frozenset(self.review_evidence) != REQUIRED_REVIEW_EVIDENCE or len(
            self.review_evidence
        ) != len(REQUIRED_REVIEW_EVIDENCE):
            raise ValueError(
                f"{self.id}: review_evidence is always the architecture reviewer, the security "
                "reviewer and the tester, each once"
            )
        return self


class ReuseDecision(Contract):
    candidate: str = Field(min_length=1)  # a module card id
    decision: Literal["use", "not-applicable"]
    reason: Text


class ImplementationPlan(Contract):
    schema_id: Literal["orqlet.implementation-plan/v1"] = Field(alias="schema")
    header: ArtifactHeader
    design_ref: str = Field(min_length=1)  # design manifest path and hash, `path#sha256`
    base_revision: GitOid
    amends: str | None = None  # the hash of the plan this amendment revises
    knowledge_scope: tuple[Glob, ...] = ()
    phases: tuple[Phase, ...] = Field(min_length=1)
    reuse_decisions: tuple[ReuseDecision, ...] = ()
    self_check: SelfCheck
