"""Contracts for the files inside the protected workflow package (proposal section 17.12)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract, SHA256Hex


class WorkflowIdentity(Contract):
    """`identity.json`: the one place a release sets its workflow version and controls level."""

    schema_id: Literal["orqlet.workflow-identity/v1"] = Field(alias="schema")
    workflow_version: str
    controls_level: int = Field(ge=0)


class ManifestEntry(Contract):
    path: str
    sha256: SHA256Hex


class WorkflowManifest(Contract):
    """`MANIFEST.json`: every workflow file with its hash. Its digest identifies a release."""

    schema_id: Literal["orqlet.workflow-manifest/v1"] = Field(alias="schema")
    workflow_version: str
    controls_level: int = Field(ge=0)
    files: tuple[ManifestEntry, ...]


class ReleaseRecord(Contract):
    version: str
    digest: SHA256Hex
    controls_level: int = Field(ge=0)


class ReleaseHistory(Contract):
    """`releases.json`: what earlier releases were, so a silent change can be caught."""

    schema_id: Literal["orqlet.workflow-releases/v1"] = Field(alias="schema")
    releases: tuple[ReleaseRecord, ...] = ()


class ExemptClass(Contract):
    extensions: tuple[str, ...] = ()
    code_name_patterns: tuple[str, ...] = ()
    under: tuple[str, ...] = ()
    except_under: tuple[str, ...] = ()
    excludes_agent_configuration_surface: bool = False
    recognised_by: str | None = None
    paths: str | None = None


class ExemptClasses(Contract):
    schema_id: Literal["orqlet.exempt/v1"] = Field(alias="schema")
    precedence: tuple[str, ...]
    classes: dict[str, ExemptClass]


class ReleasedFile(Contract):
    path: str
    reason: str
    released_by: str | None = None


class Released(Contract):
    """`.orqlet/released.yaml`: files that left the manifest and now belong to the team."""

    schema_id: Literal["orqlet.released/v1"] = Field(alias="schema")
    files: tuple[ReleasedFile, ...] = ()


class WorkflowLock(Contract):
    """`.orqlet/workflow.lock`: which release of the workflow a project was rendered from."""

    schema_id: Literal["orqlet.workflow-lock/v1"] = Field(alias="schema")
    workflow_version: str
    workflow_digest: SHA256Hex
    controls_level: int = Field(ge=0)


class WorkflowRuleMeta(Contract):
    """Where a workflow rule text applies, kept beside the text (`rules/<name>.meta.yaml`)."""

    schema_id: Literal["orqlet.workflow-rule/v1"] = Field(alias="schema")
    name: str
    description: str
    paths: tuple[str, ...] = Field(min_length=1)
