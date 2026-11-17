"""`orqlet.review-result/v1`: one review round, `docs/design/<task>/reviews/<role>-P-<n>-r<k>.yaml`.

The record is evidence about the inputs it names, and it is attested: it proves that a record
states the digest of these inputs, not that a review took place (proposal 6.14.1).
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.common import (
    ClientId,
    Contract,
    RecordedModel,
    SHA256Hex,
    Slug,
    Text,
)
from orqlet.application.contracts.finding import AbsenceEvidence, Finding
from orqlet.application.contracts.review_input import ReviewInput
from orqlet.application.contracts.self_check import SelfCheck

REQUIRED_COVERS = frozenset(
    {
        "code_tests",
        "knowledge",
        "design",
        "plan",
        "standards",
        "reviewer_definition",
        "evidence_inputs",
    }
)


# Where a recorded model identity came from (ADR-007 decision 2). The agent that writes a record
# is on the coder's side, so all three values are attested; only an observed identity can ever
# establish a family difference, and a record that says nothing means `unknown`.
IdentitySource = Literal["client-reported", "person-observed", "unknown"]
SelectionSource = Literal[
    "task-override", "role-assignment", "profile-assignment", "automatic", "explicit-fallback"
]


class Context(Contract):
    """The reviewer's attestation of a fresh session that read the packet and nothing else."""

    fresh: Annotated[bool, Field(strict=True)]
    input: Literal["packet-only"]


class AgentBinding(Contract):
    binding_ref: str = Field(min_length=1)  # an id in role-bindings.yaml
    definition_sha256: SHA256Hex
    client: ClientId
    model_requested: RecordedModel | None = None
    model_observed: RecordedModel | None = None  # where the client reports it
    # The three below are optional, so every record written before them still loads (BC-16).
    identity_source: IdentitySource = "unknown"
    context: Context | None = None
    selection_source: SelectionSource | None = None


class CoderBinding(Contract):
    client: ClientId
    model_requested: RecordedModel | None = None
    model_observed: RecordedModel | None = None
    identity_source: IdentitySource = "unknown"


class Applicability(Contract):
    """A reviewer, never the developer, concludes that nothing in its field changed."""

    examined: tuple[str, ...] = ()
    conclusion: Literal["findings", "no-impact"]
    absence_record: AbsenceEvidence | None = None  # required for `no-impact`

    @model_validator(mode="after")
    def _no_impact_needs_an_absence_record(self) -> Self:
        if self.conclusion == "no-impact" and self.absence_record is None:
            raise ValueError("a no-impact conclusion needs an absence record")
        return self


class ReviewResult(Contract):
    schema_id: Literal["orqlet.review-result/v1"] = Field(alias="schema")
    task: Slug  # must equal the task in the path
    phase: str = Field(pattern=r"^P-[1-9]\d*$")
    role: Literal["architecture-reviewer", "security-reviewer", "code-reviewer"]
    round: int = Field(ge=1)
    verdict: Literal["PASS", "FAIL", "NOT_RUN"]  # errors, timeouts and unavailability are NOT_RUN
    assurance: Literal["advisory"]
    review_input: ReviewInput
    agent: AgentBinding
    coder_binding: CoderBinding
    independence: Literal["I0", "I1", "I2", "I3"]
    capability_limits: tuple[Text, ...] = ()
    applicability: Applicability
    findings: tuple[Finding, ...] = ()
    self_check: SelfCheck

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if set(self.review_input.covers) != REQUIRED_COVERS:
            raise ValueError(
                "a review covers code_tests, knowledge, design, plan, standards, "
                "reviewer_definition and evidence_inputs"
            )
        blocking = [f for f in self.findings if f.severity == "blocking"]
        if self.verdict == "PASS" and blocking:
            raise ValueError("a PASS cannot hold a blocking finding")
        if self.verdict == "FAIL" and not blocking:
            raise ValueError("a FAIL needs at least one blocking finding")
        if self.verdict == "PASS" and self.independence == "I0":
            raise ValueError("an I0 review is never a PASS: it is NOT_RUN")
        ids = [f.id for f in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("a finding id is used twice")
        return self
