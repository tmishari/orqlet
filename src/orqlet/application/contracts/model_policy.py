"""`orqlet.model-policy/v2` (ADR-002): the team's model catalog, profiles and assignments.

The file is `.orqlet/model-policy.yaml`. This module is the contract only: use cases such as
`models resolve`, `explain` and `upgrade` read the policy through it, and nothing here selects,
ranks or calls a model. Cross references (a candidate that names a
model of the catalog, an approved model that an exclusion matches) are the job of the validator,
not of the shape. Every string that names a model is a constrained string without a custom
message, so a refused value is never echoed (BC-32). The repository path fields (`evidence` and
`source`) are `RepoPath`, whose refusal text names the path: keeping a refused path out of a
finding is the job of the loader that reports it, not of this shape.
"""

from __future__ import annotations

import datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, StringConstraints, model_validator

from orqlet.application.contracts.common import (
    ClientId,
    Contract,
    ModelRef,
    PolicyText,
    RepoPath,
    Slug,
)

ProfileId = Literal["quality", "engineering", "economy"]
Mode = Literal["automatic", "manual", "automatic-with-fallbacks"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]

# An `fnmatch`-style pattern (ADR-005): the model-id alphabet plus `*` and `?`, never a regular
# expression, so none of `^ $ ( ) [ ] { } | \` can appear.
IdPattern = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9._:/@+*?-]+$", min_length=1, max_length=128)
]

# `major.minor.patch` with no leading zeros and ASCII digits only. That is stricter than the domain
# `Version`, whose `\d` also takes a non-ASCII digit after the first digit of a part.
ReleaseVersion = Annotated[
    str,
    StringConstraints(
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$", max_length=32
    ),
]

# A price per million tokens as text, such as `3` or `0.25`: a float would lose digits.
DecimalText = Annotated[str, StringConstraints(pattern=r"^[0-9]+(\.[0-9]+)?$", max_length=32)]


def _calendar_date(value: str) -> str:
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        # No value in the message: it is the one thing a refusal must not repeat.
        raise ValueError("not a calendar date") from None
    return value


# `YYYY-MM-DD`. A string and not a `date`, so a YAML number or time never becomes a date.
PolicyDate = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"),
    AfterValidator(_calendar_date),
]


class Approval(Contract):
    state: Literal["proposed", "approved", "disabled", "retired"]
    # An attested pointer (a pull request, a merge commit, an ADR); the validator checks format.
    approved_by: PolicyText | None = None
    approval_ref: PolicyText | None = None


class Documented(Contract):
    evidence: RepoPath
    date: PolicyDate


class Evaluated(Contract):
    state: Literal["none", "evidenced"]
    evidence: RepoPath | None = None

    @model_validator(mode="after")
    def _evidenced_needs_its_evidence(self) -> Self:
        if self.state == "evidenced" and self.evidence is None:
            raise ValueError("an evidenced evaluation needs its evidence file")
        return self


class ListPrice(Contract):
    input_per_million_usd: DecimalText
    output_per_million_usd: DecimalText
    source: RepoPath


class Route(Contract):
    client: ClientId
    kind: Literal["id", "alias"]
    name: ModelRef | None = None  # the client's exact identifier; none while it is unknown
    resolves_to: ModelRef | None = None
    also_known_as: Annotated[tuple[ModelRef, ...], Field(max_length=8)] = ()
    access: Literal["unknown", "confirmed", "blocked"] = "unknown"
    retires_on: PolicyDate | None = None

    @model_validator(mode="after")
    def _only_an_alias_resolves(self) -> Self:
        if self.kind == "alias" and self.resolves_to is None:
            raise ValueError("a route of kind alias must carry resolves_to")
        if self.kind == "id" and self.resolves_to is not None:
            raise ValueError("a route of kind id must not carry resolves_to")
        return self


class ModelEntry(Contract):
    id: ModelRef
    family: ModelRef
    approval: Approval
    documented: Documented
    # Attested labels that no tool checks (ADR-002 decision 4): the five states are separate.
    callable: Literal["not-run", "verified"]
    evaluated: Evaluated
    list_price: ListPrice | None = None
    routes: tuple[Route, ...] = ()


class Exclusion(Contract):
    id: ModelRef
    reason: PolicyText
    source: PolicyText
    aliases: tuple[ModelRef, ...] = ()
    id_patterns: tuple[IdPattern, ...] = ()
    family_tags: tuple[ModelRef, ...] = ()

    @model_validator(mode="after")
    def _something_to_match(self) -> Self:
        if not (self.aliases or self.id_patterns or self.family_tags):
            raise ValueError("an exclusion needs an alias, an id pattern or a family tag")
        return self


class ClientModels(Contract):
    """The ordered catalog ids a profile offers one client."""

    client: ClientId
    models: tuple[ModelRef, ...]


def _one_entry_per_client(entries: tuple[ClientModels, ...]) -> bool:
    clients = [entry.client for entry in entries]
    return len(clients) == len(set(clients))


class Profile(Contract):
    id: ProfileId
    capability: PolicyText
    mode: Mode
    candidates: tuple[ClientModels, ...] = ()
    fallbacks: tuple[ClientModels, ...] = ()
    escalation: ProfileId | None = None

    @model_validator(mode="after")
    def _one_list_per_client(self) -> Self:
        if not (_one_entry_per_client(self.candidates) and _one_entry_per_client(self.fallbacks)):
            raise ValueError("candidates and fallbacks hold one entry for each client")
        return self


class Target(Contract):
    kind: Literal["role", "skill"]
    name: Slug


class Assignment(Contract):
    target: Target
    task: Slug | None = None
    client: ClientId | None = None
    profile: ProfileId | None = None
    model: ModelRef | None = None
    mode: Mode
    effort: Effort | None = None

    @model_validator(mode="after")
    def _a_profile_or_a_model(self) -> Self:
        if (self.profile is None) == (self.model is None):
            raise ValueError("an assignment names exactly one of profile and model")
        return self


class ModelPolicy(Contract):
    schema_id: Literal["orqlet.model-policy/v2"] = Field(alias="schema")
    policy_version: Annotated[int, Field(strict=True, ge=1)]
    reviewed_for_release: ReleaseVersion
    models: tuple[ModelEntry, ...] = ()
    excluded: tuple[Exclusion, ...] = ()
    profiles: tuple[Profile, ...] = ()
    assignments: tuple[Assignment, ...] = ()

    @model_validator(mode="after")
    def _each_profile_once(self) -> Self:
        ids = [profile.id for profile in self.profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("a profile id is used twice")
        return self
