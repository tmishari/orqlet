"""The user scope as `status` reads it: the home folder and `<data>/user/manifest.json` (ADR-002).

The manifest is written by `install` and read by `status` and the hooks. It names, for each file or
shared JSON entry Orqlet owns, its hash, the workflow version that wrote it and the owning clients.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, Field, StringConstraints

from orqlet.application.contracts.common import (
    Contract,
    RenderClientId,
    SHA256Hex,
    Timestamp,
)
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.representable import representable_version

USER_MANIFEST_SCHEMA = "orqlet.user-manifest/v1"
USER_MANIFEST_PATH = CanonicalPath.parse("user/manifest.json")


def _workflow_version(value: str) -> str:
    if representable_version(value) is None:
        raise ValueError("not a major.minor.patch version")
    return value


WorkflowVersionText = Annotated[str, AfterValidator(_workflow_version)]
ChangeId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,63}$")]
EntryText = Annotated[str, StringConstraints(min_length=1, max_length=512)]


class UserHome(Contract):
    """The real path of the home folder, injected once (ADR-002 decision 1a)."""

    path: str


class UserManifestEntry(Contract):
    path: EntryText  # the prefixed path, such as `claude/skills/orqlet/SKILL.md`
    key: EntryText | None = None  # the entry key inside a shared JSON file
    sha256: SHA256Hex
    workflow_version: WorkflowVersionText
    owners: tuple[RenderClientId, ...] = Field(min_length=1)


class UserManifest(Contract):
    schema_id: Literal["orqlet.user-manifest/v1"] = Field(alias="schema")
    change_id: ChangeId
    created_at: Timestamp
    roots: dict[str, str] = Field(default_factory=dict)  # prefix -> pinned real root
    entries: tuple[UserManifestEntry, ...] = ()
