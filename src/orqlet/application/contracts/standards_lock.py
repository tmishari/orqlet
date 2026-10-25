"""`orqlet.standards-lock/v1`: pins the packs that apply (named in proposal section 13.2).

The proposal gives no example of this file, so its shape is defined here: one entry per pack
with its version and content hash, plus the hash of the applicable rule set.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract, SHA256Hex


class LockedPack(Contract):
    id: str
    version: str
    sha256: SHA256Hex
    source: str


class StandardsLock(Contract):
    schema_id: Literal["orqlet.standards-lock/v1"] = Field(alias="schema")
    packs: tuple[LockedPack, ...] = ()
    applicable_rules_hash: SHA256Hex | None = None
