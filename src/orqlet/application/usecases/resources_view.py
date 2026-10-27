"""`orqlet resources list`: the registry as rows, and the technologies that no entry covers.

Every string in a row is passed through `printable` here, once, so the command line and a script
that reads `--json` can never print a hidden or escape character from the repository (component
rule 5). The address itself is not in a row: the host is shown on its own line, so that the host a
reviewer sees is the host that was checked (ADR-002 decision 8).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.contracts.resources import Resource
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.filesystem import FileKind, FileSystemError
from orqlet.application.usecases.render_all import PROFILE_PATH
from orqlet.application.usecases.resources_source import load_resources, resources_path
from orqlet.application.usecases.validation import ValidateServices
from orqlet.domain.conventions import printable
from orqlet.domain.findings import Finding
from orqlet.domain.resources import host_of, uncovered_names

_SHOWN = 200


@dataclass(frozen=True, slots=True)
class ResourcesListing:
    resources: tuple[Mapping[str, object], ...]
    uncovered: tuple[str, ...]
    findings: tuple[Finding, ...]


def list_resources(services: ValidateServices, uncovered: bool) -> ResourcesListing:
    """The registry in order of id; with `uncovered`, the profile's technologies no entry names."""
    path = str(resources_path())
    registry, findings = load_resources(services.project, services.loader, path)
    if registry is None:
        return ResourcesListing((), (), findings)
    rows = tuple(_row(item) for item in registry.resources)
    if not uncovered:
        return ResourcesListing(rows, (), findings)
    technologies = _technologies(services)
    tools = [item.tool for item in registry.resources if item.tool is not None]
    return ResourcesListing(
        rows, tuple(printable(name, _SHOWN) for name in uncovered_names(technologies, tools)), ()
    )


def _row(item: Resource) -> dict[str, object]:
    record = item.stored_copy
    return {
        "id": _shown(item.id),
        "title": _shown(item.title),
        "kind": _shown(item.kind),
        "access": _shown(item.access),
        "host": _shown(host_of(item.url)),
        "tool": None if item.tool is None else _shown(item.tool),
        "version": None if item.version is None else _shown(item.version),
        "applies_to": [_shown(path) for path in item.applies_to.paths] if item.applies_to else [],
        "stored_copy": None
        if record is None
        else {
            "form": _shown(record.form),
            "sha256": _shown(record.sha256),
            "retrieved_at": _shown(record.retrieved_at),
            "ttl_days": record.ttl_days,
        },
    }


def _shown(text: str) -> str:
    return printable(text, _SHOWN)


def _technologies(services: ValidateServices) -> list[str]:
    """The names of the profile's technologies and frameworks; none when it cannot be read."""
    try:
        if services.project.kind(PROFILE_PATH) is not FileKind.FILE:
            return []
        profile = load_contract(
            services.loader,
            ProjectProfile,
            services.project.read_bytes(PROFILE_PATH),
            source=str(PROFILE_PATH),
        )
    except (DocumentError, FileSystemError):
        return []
    return [item.name for item in profile.technologies] + [
        fact.name for fact in profile.facts.frameworks
    ]
