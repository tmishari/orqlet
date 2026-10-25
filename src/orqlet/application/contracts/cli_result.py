"""`orqlet.cli-result/v1`: the one envelope of every `--json` output (design section 5.4)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract


class FindingOut(Contract):
    code: str
    message: str
    severity: Literal["info", "warning", "error"]
    path: str | None = None


class CliResult(Contract):
    schema_id: Literal["orqlet.cli-result/v1"] = Field(alias="schema")
    ok: bool
    command: str
    orqlet_version: str
    data: dict[str, Any] = Field(default_factory=dict)
    findings: tuple[FindingOut, ...] = ()
    not_run: tuple[str, ...] = ()
