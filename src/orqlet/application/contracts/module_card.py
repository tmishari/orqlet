"""`orqlet.module-card/v1`: a module, package or service that is worth reusing (proposal 8.12).

Cards are knowledge, read by the deterministic impact analysis. They are read only here: this
module parses one card from a YAML file or from the front matter of a Markdown file.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.common import Contract, RepoPath, SHA256Hex, Text


class PythonInterface(Contract):
    import_path: str = Field(min_length=1)
    public_symbols: tuple[str, ...] = ()


class ServiceInterface(Contract):
    contract_ref: str = Field(min_length=1)
    environments: tuple[str, ...] = ()


class CardInterface(Contract):
    python: PythonInterface | None = None
    service: ServiceInterface | None = None


class CardVersion(Contract):
    since: str | None = None
    package: str | None = None
    constraint_hint: str | None = None
    index_ref: str | None = None


class Provenance(Contract):
    added_in: str | None = None
    reviewed_by: str | None = None


class ModuleCard(Contract):
    schema_id: Literal["orqlet.module-card/v1"] = Field(alias="schema")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    kind: Literal["same-repo-module", "released-package", "deployed-service"]
    summary: Text
    use_when: tuple[str, ...] = ()
    avoid_when: tuple[str, ...] = ()
    interface: CardInterface = CardInterface()
    interface_digest: SHA256Hex | None = None  # of the interface as last extracted
    examples: tuple[str, ...] = ()
    version: CardVersion | None = None
    status: Literal["active", "deprecated", "superseded"] = "active"
    replaced_by: str | None = None
    deprecated_in: str | None = None
    remove_after: str | None = None
    owner: str = Field(min_length=1)
    requirement_level: Literal["informational", "should", "must"] = "informational"
    must_consider: bool = False
    provenance: Provenance | None = None
    # References the impact analysis reads from the front matter of cards and ADRs (17.13.3).
    refs: tuple[RepoPath, ...] = ()
    paths: tuple[RepoPath, ...] = ()
    symbols: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _superseded_names_its_replacement(self) -> Self:
        if self.status == "superseded" and self.replaced_by is None:
            raise ValueError("a superseded card names the card that replaces it")
        return self
