"""How Orqlet owns a generated file and how strictly it is protected (proposal section 9.3)."""

from enum import StrEnum


class OwnerMode(StrEnum):
    ORQLET = "orqlet"
    SHARED_BLOCK = "shared-block"
    SHARED_ENTRY = "shared-entry"
    SEEDED = "seeded"
    USER = "user"


class FileClass(StrEnum):
    PROTECTED = "protected"
    GENERATED = "generated"
    OPTIONAL = "optional"
