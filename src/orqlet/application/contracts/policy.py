"""`orqlet.workflow-policy/v2` (proposal section 24.6): the enforcement baseline parameters."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract


class ApprovalRule(Contract):
    source: Literal["baseline-with-merge-evidence"]
    code_owners: str | None = None
    minimum_approvers: int | None = None


class Approvals(Contract):
    design: ApprovalRule
    plan: ApprovalRule


class IndependenceRaise(Contract):
    glob: str
    min_class: Literal["I1", "I2", "I3"]


class Triggers(Contract):
    d1_max_files: int | None = None
    security_sensitive_globs: tuple[str, ...] = ()
    d3_globs: tuple[str, ...] = ()
    independence_raise: tuple[IndependenceRaise, ...] = ()


class Limits(Contract):
    rework_rounds_per_phase: int | None = None
    max_excerpts: int | None = None
    max_chars_per_excerpt: int | None = None


class Events(Contract):
    sweep_cadence_minutes: int | None = None
    reevaluate_interval_minutes: int | None = None
    sweep_max_pull_requests: int | None = None


class KnowledgeLints(Contract):
    copy_max_lines: int | None = None
    near_duplicate_threshold: float | None = None


class PhaseClaims(Contract):
    extras: Literal["block"] = "block"


class WorkflowPolicy(Contract):
    schema_id: Literal["orqlet.workflow-policy/v2"] = Field(alias="schema")
    policy_role: Literal["enforcement-baseline"]
    approvals: Approvals
    triggers: Triggers = Triggers()
    limits: Limits = Limits()
    retrieval: dict[str, str] = Field(default_factory=dict)
    hooks: dict[str, str] = Field(default_factory=dict)
    required_checks: tuple[str, ...] = ()
    events: Events = Events()
    knowledge: KnowledgeLints = KnowledgeLints()
    phase_claims: PhaseClaims = PhaseClaims()
