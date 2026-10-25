"""`orqlet.review-input/v1`: the digest of what a reviewer, a tester or an assessment examined.

There is deliberately no field for a commit id, the digest of the final tree or the record's own
digest: committing the record must not change what it states (proposal 6.14.1).
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.common import Contract, GitOid, SHA256Hex

ComponentName = Literal[
    "code_tests",
    "knowledge",
    "design",
    "plan",
    "standards",
    "reviewer_definition",
    "evidence_inputs",
    "candidates",
]


class ReviewInput(Contract):
    schema_id: Literal["orqlet.review-input/v1"] = Field(
        default="orqlet.review-input/v1", alias="schema"
    )
    covers: tuple[ComponentName, ...] = Field(min_length=1)
    components: dict[ComponentName, SHA256Hex]  # one entry per covered component
    digest: SHA256Hex  # over the covered components only
    merge_base: GitOid  # informational: the code components come from blobs, not from this

    @model_validator(mode="after")
    def _components_are_exactly_the_covered_ones(self) -> Self:
        if len(set(self.covers)) != len(self.covers):
            raise ValueError("a component is covered twice")
        if set(self.components) != set(self.covers):
            raise ValueError("components must hold exactly one digest per covered component")
        return self
