"""`orqlet.generated-lock/v1` (proposal section 24.7): the ownership manifest."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.common import Contract, SHA256Hex
from orqlet.domain.ownership import FileClass, OwnerMode


class LockInput(Contract):
    id: str
    version: str
    sha256: SHA256Hex


class BlockMarkers(Contract):
    begin: str
    end: str


class LockedFile(Contract):
    path: str
    owner: OwnerMode
    file_class: FileClass | None = Field(default=None, alias="class")
    inputs: tuple[LockInput, ...] = ()
    rendered_sha256: SHA256Hex | None = None
    seeded_sha256: SHA256Hex | None = None
    block: BlockMarkers | None = None
    entry: str | None = None

    @model_validator(mode="after")
    def _owner_specific_fields(self) -> Self:
        if self.owner is OwnerMode.SEEDED:
            if self.seeded_sha256 is None:
                raise ValueError("a seeded file records seeded_sha256")
        elif self.rendered_sha256 is None:
            raise ValueError("a generated file records rendered_sha256")
        if self.owner is OwnerMode.SHARED_BLOCK and self.block is None:
            raise ValueError("a shared-block file names its block markers")
        if self.owner is OwnerMode.SHARED_ENTRY and self.entry is None:
            raise ValueError("a shared-entry file names its entry")
        if self.owner is OwnerMode.ORQLET and self.file_class is None:
            raise ValueError("an Orqlet-owned file has a class")
        return self


class GeneratorInfo(Contract):
    orqlet: str


class GeneratedLock(Contract):
    schema_id: Literal["orqlet.generated-lock/v1"] = Field(alias="schema")
    generator: GeneratorInfo
    standards_lock: SHA256Hex | None = None
    files: tuple[LockedFile, ...] = ()
