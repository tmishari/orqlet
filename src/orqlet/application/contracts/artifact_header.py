"""`orqlet.artifact-header/v1`: what an agent read when it wrote an artifact (proposal 17.11).

Approval is decided by presence on the protected baseline, never by `status`. The header records
what the agent *read*, so an artifact written under an old session or an old workflow version is
detectable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, NonNegativeInt

from orqlet.application.contracts.common import (
    Contract,
    GitOid,
    RepoPath,
    SHA256Hex,
    Slug,
)


class Upstream(Contract):
    ref: RepoPath
    sha256: SHA256Hex


class Bound(Contract):
    base_revision: GitOid
    standards_lock_hash: SHA256Hex
    applicable_rules_hash: SHA256Hex
    profile_version: NonNegativeInt
    upstream: tuple[Upstream, ...] = ()


class Specialist(Contract):
    """Recorded and validated for shape, not for truth."""

    role: str = Field(min_length=1)
    client: str = Field(min_length=1)
    binding: str = Field(min_length=1)
    parallel: bool


class ArtifactHeader(Contract):
    schema_id: Literal["orqlet.artifact-header/v1"] = Field(alias="schema")
    task: Slug
    status: Literal["draft", "approved", "superseded"]  # informational
    workflow_version: str = Field(min_length=1)
    protected_set_digest: SHA256Hex
    bound: Bound
    specialists: tuple[Specialist, ...] = ()
