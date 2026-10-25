"""`orqlet.versions/v1` (proposal section 24.11): accepted versions, read from the baseline."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract, SHA256Hex


class CliVersions(Contract):
    pinned: str
    sha256: SHA256Hex | None = None
    accepted: tuple[str, ...] = ()
    denied: tuple[str, ...] = ()


class WorkflowVersions(Contract):
    version: str
    digest: SHA256Hex
    floor: str
    controls_level_min: int


class ChangeControl(Contract):
    lowering_pin_or_floor_requires_approvals: int = 2


class Versions(Contract):
    schema_id: Literal["orqlet.versions/v1"] = Field(alias="schema")
    policy_role: Literal["enforcement-baseline"]
    cli: CliVersions
    workflow: WorkflowVersions
    change_control: ChangeControl = ChangeControl()
