"""Pure builders of the registry: add, update and remove one entry (ADR-002 decision 7).

`init` and the edit commands call these functions, so an entry is always built and checked in one
place. A builder takes the registry and what the person asked for and returns a new registry, or
no registry and one finding ORQ-E509 that says what was refused. Nothing here reads a file, asks
the clock or writes: the commands do that around the builders.

A refusal names the rule and the field and never repeats a value that the person typed
(ORQLET-SEC-003): the result is checked by the `Resources` contract, whose errors hold no input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from orqlet.application.contracts.resources import Resources
from orqlet.domain.findings import Finding, Severity

_REFUSED = "ORQ-E509"
_SCHEMA = "orqlet.resources/v1"
_NEEDED_FOR_AN_ADD = ("url", "title", "kind", "note", "access")
_PLAIN_FIELDS = ("url", "title", "kind", "note", "access", "tool", "version")


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    """What the person gave for one entry; `None` means "not given", never "clear"."""

    id: str
    url: str | None = None
    title: str | None = None
    kind: str | None = None
    note: str | None = None
    access: str | None = None
    paths: tuple[str, ...] | None = None
    tool: str | None = None
    version: str | None = None


def resources_with(
    resources: Resources, spec: ResourceSpec, replace: bool
) -> tuple[Resources | None, tuple[Finding, ...]]:
    """The registry with one entry added, or with the entry of that id updated when `replace`.

    An add needs url, title, kind, note and access and refuses an id that is already there. An
    update needs the id to exist, changes only the fields that are given and keeps the record of
    the stored copy. Both refuse a result that fails the `Resources` contract.
    """
    entries = _entries_of(resources)
    if replace:
        if spec.id not in entries:
            return _refused("there is no entry with that id to update")
        entries[spec.id] = _updated(entries[spec.id], spec)
    else:
        if spec.id in entries:
            return _refused("an entry with that id exists: update it or choose another id")
        missing = [name for name in _NEEDED_FOR_AN_ADD if getattr(spec, name) is None]
        if missing:
            return _refused("a new entry needs " + ", ".join(missing))
        entries[spec.id] = _new_entry(spec)
    return _checked(entries)


def resources_without(
    resources: Resources, resource_id: str
) -> tuple[Resources | None, tuple[Finding, ...]]:
    """The registry without the entry of that id; the file of its stored copy is not touched."""
    entries = _entries_of(resources)
    if resource_id not in entries:
        return _refused("there is no entry with that id to remove")
    del entries[resource_id]
    return _checked(entries)


def _entries_of(resources: Resources) -> dict[str, dict[str, Any]]:
    return {
        item.id: item.model_dump(mode="json", by_alias=True, exclude_none=True)
        for item in resources.resources
    }


def _new_entry(spec: ResourceSpec) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": spec.id}
    for name in _PLAIN_FIELDS:
        value = getattr(spec, name)
        if value is not None:
            entry[name] = value
    if spec.paths:
        entry["applies_to"] = {"paths": list(spec.paths)}
    return entry


def _updated(entry: dict[str, Any], spec: ResourceSpec) -> dict[str, Any]:
    changed = dict(entry)
    for name in _PLAIN_FIELDS:
        value = getattr(spec, name)
        if value is not None:
            changed[name] = value
    if spec.paths is not None:
        if spec.paths:
            changed["applies_to"] = {"paths": list(spec.paths)}
        else:
            changed.pop("applies_to", None)
    return changed


def _checked(entries: dict[str, dict[str, Any]]) -> tuple[Resources | None, tuple[Finding, ...]]:
    """The contract decides: the entries go in order of id, as the file is written."""
    document = {"schema": _SCHEMA, "resources": [entries[key] for key in sorted(entries)]}
    try:
        return Resources.model_validate(document), ()
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors(include_input=False, include_url=False)
        )
        return _refused(f"the registry would break its rules: {problems}")


def _refused(reason: str) -> tuple[None, tuple[Finding, ...]]:
    return None, (Finding(_REFUSED, f"The change was refused: {reason}.", Severity.ERROR),)
