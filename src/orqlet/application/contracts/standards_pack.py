"""`orqlet.standards-pack/v1` and its rules (proposal sections 12.7 and 24.3)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract


class AppliesTo(Contract):
    languages: tuple[str, ...] = ()
    project_types: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    technologies: tuple[str, ...] = ()  # any technology by name: PostgreSQL, Kafka, Gin...
    python: str | None = None


class PackAsset(Contract):
    kind: Literal["pr-template", "prompts-scaffold"]
    id: str
    path: str
    owner: str
    version: str
    sha256: str


class Provenance(Contract):
    source_url: str
    applicable_version: str
    retrieved: str
    authored_by: str
    review_ref: str | None = None


class RuleFile(Contract):
    """`orqlet.rules/v1`: the rules of a pack, or the project's own additions."""

    schema_id: Literal["orqlet.rules/v1"] = Field(alias="schema")
    rules: tuple[Rule, ...] = ()


class PackManifest(Contract):
    schema_id: Literal["orqlet.standards-pack/v1"] = Field(alias="schema")
    id: str
    version: str
    owner: str
    reviewers: tuple[str, ...] = ()
    compatibility: dict[str, object] = Field(default_factory=dict)
    applies_to: AppliesTo = AppliesTo()
    baseline: str | None = None
    rules: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    assets: tuple[PackAsset, ...] = ()
    provenance: tuple[Provenance, ...] = ()


class RuleScope(Contract):
    paths: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    phases: tuple[str, ...] = ()


class Rule(Contract):
    id: str
    level: Literal["MUST", "SHOULD", "MAY"]
    waiver: Literal["none", "reviewed"] = "none"
    scope: RuleScope = RuleScope()
    enforcement: Literal["deterministic", "review", "guidance"] = "guidance"
    check_ref: str | None = None
    text: str
    override: Literal["stricter-only"] = "stricter-only"
