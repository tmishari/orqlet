"""`orqlet.resources/v1`: `.orqlet/resources.yaml`, the links a team registers (ADR-002).

The contract is closed and bounded: at most 100 entries, in order of id, with text that passes the
rules of `orqlet.domain.resources`. Every validator raises a fixed text that names the rule and
never repeats the value (ORQLET-SEC-003), and the models hide the input in their errors. The
validators do not reuse the `Glob` and `RepoPath` types of `common.py`, whose errors repeat the
rejected value.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, StringConstraints, field_validator, model_validator

from orqlet.application.contracts.common import Contract, SHA256Hex
from orqlet.domain.resources import (
    glob_problems,
    host_of,
    resource_id_problems,
    text_problems,
    url_problems,
)

_Kind = Literal["api-guidelines", "tool-docs", "team-docs", "other"]
_Access = Literal["public", "login"]
_Form = Literal["copy", "summary"]
_Tool = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,39}$")]
_Version = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9._+-]{1,40}$")]
_MAX_RESOURCES = 100
_MAX_PATHS = 8
_INTERNAL_LABELS = frozenset({"internal", "corp", "lan", "home", "intranet"})
_FIRST_YEAR, _LAST_YEAR = 2000, 2200
_TIMESTAMP_SHAPE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})"
)


def _rules(field: str, problems: tuple[str, ...]) -> None:
    if problems:
        raise ValueError(f"{field} breaks the rules {', '.join(problems)}")


class AppliesTo(Contract):
    """The paths a resource applies to; the clients match them, Orqlet checks only the syntax."""

    model_config = ConfigDict(hide_input_in_errors=True)

    paths: tuple[str, ...] = ()

    @field_validator("paths")
    @classmethod
    def _checked_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) > _MAX_PATHS:
            raise ValueError(f"at most {_MAX_PATHS} globs are allowed")
        for glob in value:
            _rules("a glob", glob_problems(glob))
        return value


class StoredCopy(Contract):
    """A stored copy or summary of the page: its form, hash, retrieval time and time-to-live."""

    model_config = ConfigDict(hide_input_in_errors=True)

    form: _Form
    sha256: SHA256Hex
    retrieved_at: str
    ttl_days: int = Field(ge=1, le=365)

    @field_validator("retrieved_at")
    @classmethod
    def _timestamp_with_a_zone(cls, value: str) -> str:
        # `fromisoformat` accepts any character between date and time, so the shape is pinned
        # first: an ASCII-only value cannot carry a hidden code point into a generated file.
        if _TIMESTAMP_SHAPE.fullmatch(value) is None:
            raise ValueError("retrieved_at is not a timestamp")
        try:
            moment = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError("retrieved_at is not a timestamp") from None
        if moment.tzinfo is None:
            raise ValueError("retrieved_at has no zone")
        if not _FIRST_YEAR <= moment.year <= _LAST_YEAR:
            raise ValueError(f"retrieved_at is not in the years {_FIRST_YEAR} to {_LAST_YEAR}")
        return value


class Resource(Contract):
    """One registered link with the note that says why and when to use it."""

    model_config = ConfigDict(hide_input_in_errors=True)

    id: str
    title: str
    kind: _Kind
    url: str
    note: str
    access: _Access
    applies_to: AppliesTo | None = None
    tool: _Tool | None = None
    version: _Version | None = None
    stored_copy: StoredCopy | None = None

    @field_validator("id")
    @classmethod
    def _checked_id(cls, value: str) -> str:
        _rules("the id", resource_id_problems(value))
        return value

    @field_validator("title")
    @classmethod
    def _checked_title(cls, value: str) -> str:
        _rules("the title", text_problems(value, 80))
        return value

    @field_validator("note")
    @classmethod
    def _checked_note(cls, value: str) -> str:
        _rules("the note", text_problems(value, 200))
        return value

    @field_validator("url")
    @classmethod
    def _checked_url(cls, value: str) -> str:
        _rules("the address", url_problems(value))
        return value

    @model_validator(mode="after")
    def _cross_field_rules(self) -> Self:
        if self.tool is not None and self.kind != "tool-docs":
            raise ValueError("a tool is only for an entry of kind tool-docs")
        if self.access == "login" and self.stored_copy and self.stored_copy.form != "summary":
            raise ValueError("a login entry may only store a summary")
        if self.access == "public" and host_of(self.url).rsplit(".", 1)[-1] in _INTERNAL_LABELS:
            raise ValueError("a public entry cannot use an internal-looking host")
        return self


class Resources(Contract):
    """The registry: at most 100 entries, unique and in order of id."""

    model_config = ConfigDict(hide_input_in_errors=True)

    schema_id: Literal["orqlet.resources/v1"] = Field(alias="schema")
    resources: tuple[Resource, ...] = ()

    @field_validator("resources")
    @classmethod
    def _bounded_and_ordered(cls, value: tuple[Resource, ...]) -> tuple[Resource, ...]:
        if len(value) > _MAX_RESOURCES:
            raise ValueError(f"at most {_MAX_RESOURCES} resources are allowed")
        ids = [item.id for item in value]
        if ids != sorted(set(ids)):
            raise ValueError("the resources are not unique and in order of id")
        return value

    def covered_tools(self) -> tuple[str, ...]:
        """The tools that some entry documents, in order of entry."""
        return tuple(item.tool for item in self.resources if item.tool is not None)
