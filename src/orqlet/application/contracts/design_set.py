"""`orqlet.design-set/v1`: the design manifest, `docs/design/<task>/design/manifest.yaml`.

It carries the approved expected change (proposal 17.4.1): a machine-comparable statement of what
the implementation may change on each watched surface, so an approved API addition can be
implemented without invalidating its own design.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.artifact_header import ArtifactHeader
from orqlet.application.contracts.common import (
    Contract,
    Glob,
    RepoPath,
    SHA256Hex,
    Text,
)
from orqlet.application.contracts.self_check import SelfCheck

ClassName = Literal["D1", "D2", "D3"]
Surface = Literal[
    "public-api", "http-contract", "persisted-schema", "dependency", "security", "trust-boundary"
]
ArtifactKind = Literal[
    "c4-context",
    "c4-container",
    "c4-component",
    "data-flow",
    "sequence",
    "adr",
    "adr-not-required",
]


class DesignChangeClass(Contract):
    trigger: ClassName
    declared: ClassName
    effective: ClassName  # the maximum; the validator recomputes the trigger and rejects lower


class DesignScope(Contract):
    paths: tuple[Glob, ...] = Field(min_length=1)
    trust_boundaries: tuple[str, ...] = ()


class PublicApiConfig(Contract):
    packages: tuple[str, ...] = Field(min_length=1)
    mode: Literal["ast"]


class ExtractorConfig(Contract):
    """Where the deterministic extractors look. Part of the approved design."""

    public_api: PublicApiConfig | None = None
    dependency_manifests: tuple[RepoPath, ...] = ()
    lockfiles: tuple[RepoPath, ...] = ()
    schema_language: str | None = None  # an unsupported language makes the surface `manual`
    contract_files: tuple[RepoPath, ...] = ()
    schema_files: tuple[RepoPath, ...] = ()
    migration_paths: tuple[Glob, ...] = ()
    security_globs: tuple[Glob, ...] = ()


class ExpectedAfter(Contract):
    kind: Literal[
        "signature", "contract-delta", "schema-fragment", "specifier", "paths", "declaration"
    ]
    value: Text  # canonical text; for a schema fragment the fragment itself, never a digest


class Stage(Contract):
    id: str = Field(pattern=r"^S-\d+$")
    expected_after: ExpectedAfter


class ExpectedChange(Contract):
    id: str = Field(pattern=r"^EC-\d+$")
    surface: Surface
    action: Literal["add", "change", "remove"]
    identity: Text
    expected_after: ExpectedAfter
    stages: tuple[Stage, ...] = ()
    verification: Literal["extractor", "manual"]


class DesignArtifact(Contract):
    id: str = Field(min_length=1)
    kind: ArtifactKind
    path: RepoPath | None = None  # an `adr-not-required` entry has no file
    covers: Text  # what it shows, or why an ADR is not required
    evidence_refs: tuple[str, ...] = ()
    sha256: SHA256Hex | None = None

    @model_validator(mode="after")
    def _file_and_hash_go_together(self) -> Self:
        if self.kind == "adr-not-required":
            if self.path is not None or self.sha256 is not None:
                raise ValueError(f"{self.id}: an ADR that is not required has no file")
        elif self.path is None or self.sha256 is None:
            raise ValueError(f"{self.id}: a {self.kind} artifact needs a path and a sha256")
        return self


class Consideration(Contract):
    state: Literal["affected", "not-affected"]
    evidence_refs: tuple[str, ...] = ()
    notes: Text

    @model_validator(mode="after")
    def _not_affected_needs_evidence(self) -> Self:
        if self.state == "not-affected" and not self.evidence_refs:
            raise ValueError("`not-affected` needs evidence references")
        return self


class Considerations(Contract):
    security: Consideration
    compatibility: Consideration
    operations: Consideration


class DesignReview(Contract):
    role: Literal["architecture-reviewer", "security-reviewer"]
    note: RepoPath


class DesignSet(Contract):
    schema_id: Literal["orqlet.design-set/v1"] = Field(alias="schema")
    header: ArtifactHeader
    as_is_ref: str = Field(min_length=1)  # artifact path and hash, `path#sha256`
    change_class: DesignChangeClass
    scope: DesignScope
    extractor_config: ExtractorConfig = ExtractorConfig()
    expected_changes: tuple[ExpectedChange, ...] = ()
    artifacts: tuple[DesignArtifact, ...] = ()
    considerations: Considerations
    standards_applied: tuple[str, ...] = ()
    reviews: tuple[DesignReview, ...] = ()  # required at D2 and above, checked by the validator
    self_check: SelfCheck
