"""`orqlet.role-bindings/v1` (proposal section 24.12): approved agents for the review roles."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract, SHA256Hex


class MinimumCapability(Contract):
    context: Literal["fresh"]
    input: Literal["review-packet"]
    write_access: Literal["none-or-recorded-limit"]


class Binding(Contract):
    role: Literal["architecture-reviewer", "security-reviewer"]
    id: str
    clients: tuple[Literal["claude-code", "codex", "cursor"], ...]
    minimum_capability: MinimumCapability | None = None
    independence_capability: Literal["I1", "I2", "I3"]
    definition_sha256: SHA256Hex | None = None
    approved_by: str | None = None


class ModelFamily(Contract):
    match: str
    family: str


class RoleBindings(Contract):
    schema_id: Literal["orqlet.role-bindings/v1"] = Field(alias="schema")
    policy_role: Literal["enforcement-baseline"]
    bindings: tuple[Binding, ...] = ()
    model_families: tuple[ModelFamily, ...] = ()
    not_accepted_for_review_roles: tuple[str, ...] = ()
