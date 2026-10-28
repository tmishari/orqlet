"""The registry seen by people and by agents (ADR-002 decisions 2 and 7, ADR-003 decision 3).

`list_resources` gives the registry as rows for `orqlet resources list`. Every string in a row is
passed through `printable` here, once, so the command line and a script that reads `--json` can
never print a hidden or escape character from the repository (component rule 5). The address is
not in a row: the host is shown on its own line, so that the host a reviewer sees is the host that
was checked.

The other functions derive where a resource reaches an agent and are the only code that quotes a
value for a generated file: a rule for an entry with paths, a skill for an entry with a tool, one
catalogue skill, and the lines of the conventions block. Each value is written with `json.dumps`
after a fixed label, one per line, so a value cannot start a line, forge a block marker or leave
its quotes. The fixed text around the lines is in the templates of the workflow package, which
`build_render_request` reads; nothing here reads a file, asks the clock or opens a connection.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.contracts.resources import Resource, Resources
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.filesystem import FileKind, FileSystemError
from orqlet.application.ports.instruction_adapter import ClientSkill, ConventionsView, ScopedRule
from orqlet.application.usecases.resources_source import load_resources, resources_path
from orqlet.application.usecases.validation import ValidateServices
from orqlet.domain.conventions import printable
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import FileClass
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resources import copy_path, host_of, text_problems, uncovered_names

_SHOWN = 200
_PROFILE_PATH = CanonicalPath.parse(".orqlet/project-profile.yaml")
_MAX_ANSWER = 200
_SHOWN_ANSWER = 160
_MAX_LINES = 11
_MAX_BYTES = 2800
_REST = "The rest is in .orqlet/project-profile.yaml."
_PROFILE_FACTS = (
    ("Branch model", "repository.branch_model"),
    ("Branch naming", "repository.branch_naming"),
    ("Branch patterns", "repository.branch_patterns"),
    ("Commit convention", "repository.commit_convention"),
    ("Pull request shape", "repository.pull_requests.shape"),
    ("Merge strategy", "repository.pull_requests.merge_strategy"),
    ("Required checks", "repository.pull_requests.required_checks"),
    ("Reviewers", "repository.pull_requests.reviewers"),
    ("Release flow", "repository.release_flow"),
)


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
        if services.project.kind(_PROFILE_PATH) is not FileKind.FILE:
            return []
        profile = load_contract(
            services.loader,
            ProjectProfile,
            services.project.read_bytes(_PROFILE_PATH),
            source=str(_PROFILE_PATH),
        )
    except (DocumentError, FileSystemError):
        return []
    return [item.name for item in profile.technologies] + [
        fact.name for fact in profile.facts.frameworks
    ]


# --- what an agent reads --------------------------------------------------------------------------
def resource_rules(resources: Resources) -> tuple[ScopedRule, ...]:
    """One rule for each entry that names paths. The body holds the data lines only."""
    return tuple(
        ScopedRule(
            name=f"resource-{item.id}",
            description=(
                f"Team resource {item.id} ({item.kind}): why and when to read the linked page."
            ),
            paths=item.applies_to.paths,
            body="\n".join(_entry_lines(item, with_tool=False)),
            file_class=FileClass.PROTECTED,
        )
        for item in _in_order(resources)
        if item.applies_to is not None and item.applies_to.paths
    )


def resource_skills(resources: Resources) -> tuple[ClientSkill, ...]:
    """One skill, that the agent may start, for each entry that names a tool."""
    return tuple(
        ClientSkill(
            name=f"orqlet-tool-{item.id}",
            description=_tool_description(item.tool, item.version),
            body="\n".join(_entry_lines(item, with_tool=True)),
            agent_may_start=True,
        )
        for item in _in_order(resources)
        if item.tool is not None
    )


def catalogue_skill(resources: Resources) -> ClientSkill | None:
    """The one skill that lists every entry, or `None` for an empty registry."""
    if not resources.resources:
        return None
    count = len(resources.resources)
    return ClientSkill(
        name="orqlet-resources",
        description=(
            f"Links to team resources ({count} registered): API guidelines, tool documentation "
            "and team pages. Use to find what to read before you change code."
        ),
        body="\n".join(_catalogue_line(item) for item in _in_order(resources)),
        agent_may_start=True,
    )


def conventions_view(
    profile: ProjectProfile, resources: Resources
) -> tuple[ConventionsView | None, tuple[Finding, ...]]:
    """The finished lines of the conventions block, or `None` when there is nothing to say.

    A value that is not plain one-line text is left out and reported by key, never by value.
    """
    findings: list[Finding] = []
    shown: list[str] = []
    unknown: list[str] = []
    for label, key in _PROFILE_FACTS:
        value = _answer(profile, key)
        if value is None:
            if key != "repository.branch_patterns":
                unknown.append(label)
        elif text_problems(value, _MAX_ANSWER):
            findings.append(
                Finding(
                    "ORQ-W060",
                    f"The answer for {key} is not used in the conventions block: it is not plain "
                    "one-line text.",
                    Severity.WARNING,
                )
            )
        else:
            shown.append(f"{label}: {json.dumps(value[:_SHOWN_ANSWER])}")
    count = len(resources.resources)
    if not shown and count == 0:
        return None, tuple(findings)
    lines = list(shown)
    if unknown:
        lines.append(f"Not decided: {', '.join(unknown)}. Ask the person; do not invent one.")
    if count:
        lines.append(
            f"Links to team resources: {count} registered. Use the skill orqlet-resources."
        )
    return ConventionsView(_capped(lines), count), tuple(findings)


# --- helpers ------------------------------------------------------------------------------------
def _in_order(resources: Resources) -> list[Resource]:
    return sorted(resources.resources, key=lambda item: item.id)


def _json(value: object) -> str:
    return json.dumps(value)


def _entry_lines(item: Resource, *, with_tool: bool) -> list[str]:
    lines = [
        f"Title: {_json(item.title)}",
        f"Note: {_json(item.note)}",
        f"Kind: {_json(item.kind)}",
        f"Access: {_json(item.access)}",
        f"Host: {_json(host_of(item.url))}",
        f"Address: {_json(item.url)}",
    ]
    if with_tool and item.tool is not None:
        lines.append(f"Tool: {_json(item.tool)}")
        if item.version is not None:
            lines.append(f"Version: {_json(item.version)}")
    record = item.stored_copy
    if record is not None:
        lines += [
            f"Copy: {_json(copy_path(item.id))}",
            f"Copy form: {_json(record.form)}",
            f"Retrieved: {_json(record.retrieved_at)}",
            f"Time to live in days: {_json(record.ttl_days)}",
        ]
    return lines


def _catalogue_line(item: Resource) -> str:
    record = {
        "id": item.id,
        "title": item.title,
        "kind": item.kind,
        "note": item.note,
        "host": host_of(item.url),
        "access": item.access,
        "paths": list(item.applies_to.paths) if item.applies_to else [],
        "copy": copy_path(item.id) if item.stored_copy is not None else None,
        "skill": f"orqlet-tool-{item.id}" if item.tool is not None else None,
    }
    return f"Resource: {_json(record)}"


def _tool_description(tool: str | None, version: str | None) -> str:
    name = tool if version is None else f"{tool} {version}"
    return f"How to read the documentation of {name}. Use when the task involves {tool}."


def _answer(profile: ProjectProfile, key: str) -> str | None:
    """The recorded answer for a profile key, or `None` while it is unknown."""
    repository = profile.repository
    requests = repository.pull_requests
    plain = {
        "repository.pull_requests.merge_strategy": requests.merge_strategy,
        "repository.pull_requests.reviewers": requests.reviewers,
    }
    if key in plain:
        return None if plain[key] == "unknown" else plain[key]
    facts = {
        "repository.branch_model": repository.branch_model,
        "repository.branch_naming": repository.branch_naming,
        "repository.branch_patterns": repository.branch_patterns,
        "repository.commit_convention": repository.commit_convention,
        "repository.pull_requests.shape": requests.shape,
        "repository.pull_requests.required_checks": requests.required_checks,
        "repository.release_flow": repository.release_flow,
    }
    return facts[key].value


def _capped(lines: list[str]) -> tuple[str, ...]:
    """At most 11 lines and 2800 bytes, so that the whole block stays within 12 lines and 3 KiB."""
    if len(lines) <= _MAX_LINES and sum(len(line.encode()) + 1 for line in lines) <= _MAX_BYTES:
        return tuple(lines)
    kept: list[str] = []
    used = len(_REST.encode()) + 1
    for line in lines:
        cost = len(line.encode()) + 1
        if len(kept) >= _MAX_LINES - 1 or used + cost > _MAX_BYTES:
            break
        kept.append(line)
        used += cost
    return (*kept, _REST)
