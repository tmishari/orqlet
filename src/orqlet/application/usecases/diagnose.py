"""`doctor` and `sync`: read-only checks of an installed setup (proposal sections 9.4 and 9.6).

Nothing here writes. Every finding has a stable code, a severity and, where it is about a file,
a path. A check that could not run is listed in `not_run`; it is never reported as passed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.ports.personal import PersonalNames
from orqlet.application.usecases.draft_profile import open_questions
from orqlet.application.usecases.installation import Installation, load_installation
from orqlet.application.usecases.integrations_source import integrations_path
from orqlet.application.usecases.render_all import (
    STANDARDS_LOCK_PATH,
    environment_findings,
    ignored_findings,
)
from orqlet.application.usecases.resources_source import load_resources, resources_path
from orqlet.application.usecases.services import Services
from orqlet.application.usecases.validate_integrations import integration_findings
from orqlet.application.usecases.validation import content_hash
from orqlet.domain.blocks import BlockError, decode_utf8, parse_blocks
from orqlet.domain.changeplan import Recorded, normalised_hash
from orqlet.domain.digest import sha256_hex
from orqlet.domain.errors import InvalidPath
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resources import copy_path, is_stale, resource_id_problems
from orqlet.domain.versions import Version, is_below_floor

DriftState = Literal["up-to-date", "edited", "tampered", "missing", "unreadable"]
_MANAGED_DIRECTORIES = (
    ".claude/rules",
    ".claude/agents",
    ".claude/skills",
    ".cursor/rules",
    ".cursor/agents",
    ".agents/skills",
    ".codex/agents",
)
RESERVED_PREFIX = "orqlet-"
_MAX_FOLDERS_VISITED = 1000
# Left out of ORQ-I503: the patterns are checked by Orqlet, and the branch model is only told.
_NOT_HOST_ENFORCED = frozenset({"repository.branch_model", "repository.branch_patterns"})


@dataclass(frozen=True, slots=True)
class Drift:
    path: str
    block: str | None
    owner: OwnerMode
    file_class: FileClass | None
    state: DriftState


@dataclass(frozen=True, slots=True)
class Diagnosis:
    findings: tuple[Finding, ...]
    not_run: tuple[str, ...]
    drift: tuple[Drift, ...] = ()
    listed_names: tuple[tuple[str, str], ...] = field(default=())


def doctor(services: Services, *, personal: PersonalNames | None = None) -> Diagnosis:
    return _diagnose(services, personal, full=True)


def sync(services: Services, *, personal: PersonalNames | None = None) -> Diagnosis:
    return _diagnose(services, personal, full=False)


def measure_drift(project: FileSystem, recorded: list[Recorded]) -> tuple[Drift, ...]:
    """Compare every recorded file or block with what is on disk now."""
    found = []
    for entry in recorded:
        if entry.owner is OwnerMode.SEEDED:
            continue  # team-owned after the first write: never drift
        found.append(
            Drift(
                str(entry.path),
                entry.block_name,
                entry.owner,
                entry.file_class,
                _state_of(project, entry),
            )
        )
    return tuple(found)


def _state_of(project: FileSystem, entry: Recorded) -> DriftState:
    if project.kind(entry.path) is not FileKind.FILE:
        return "missing"
    data = project.read_bytes(entry.path)
    if entry.block_name is None:
        current: str | None = normalised_hash(data)
    else:
        try:
            block = next(
                (b for b in parse_blocks(decode_utf8(data)) if b.name == entry.block_name), None
            )
        except BlockError:
            return "unreadable"
        if block is None:
            return "missing"
        current = normalised_hash(decode_utf8(data)[block.start : block.end].encode("utf-8"))
    if current == entry.sha256:
        return "up-to-date"
    return "tampered" if entry.file_class is FileClass.PROTECTED else "edited"


# --- checks --------------------------------------------------------------------------------------
def _diagnose(services: Services, personal: PersonalNames | None, *, full: bool) -> Diagnosis:
    inst = load_installation(services)
    drift = measure_drift(services.project, inst.recorded)
    findings: list[Finding] = []
    findings += _drift_findings(drift)
    findings += ignored_findings(services, {entry.path for entry in inst.recorded})
    findings += _extra_reserved_files(services.project, inst)
    findings += _version_findings(services, inst)
    findings += _journal_findings(services, inst)
    findings += _standards_lock_findings(services, inst)
    findings += integration_findings(services.project, services.loader, str(integrations_path()))
    not_run = [
        "client versions: the installed versions of Claude Code, Codex and Cursor are not "
        "detected in this release, so declared minimum versions are not checked",
    ]
    listed: tuple[tuple[str, str], ...] = ()
    if full:
        findings += _profile_findings(inst)
        findings += _convention_findings(inst)
        findings += _resource_findings(services)
        findings += _released_findings(inst)
        findings.append(
            Finding(
                "ORQ-I200",
                "Local Git hooks are not part of this release. Checks that run in CI are "
                "authoritative; none runs locally.",
                Severity.INFO,
            )
        )
        findings += environment_findings(services, _prompts_dir(inst))
    else:
        findings.append(
            Finding(
                "ORQ-I201",
                "After an upgrade, start a new session in your IDE: a running session keeps "
                "the instructions it loaded.",
                Severity.INFO,
            )
        )
        findings += _first_run_notes(inst)
    if personal is not None:
        names = personal.list_names()
        listed = tuple((item.location, item.name) for item in names)
        findings += _reserved_name_findings(names)
    return Diagnosis(tuple(findings), tuple(not_run), drift, listed)


def _drift_findings(drift: tuple[Drift, ...]) -> list[Finding]:
    found = []
    for item in drift:
        if item.state == "up-to-date":
            continue
        name = item.path if item.block is None else f"{item.path} (block {item.block})"
        protected = item.file_class is FileClass.PROTECTED
        if protected and item.state in {"tampered", "missing", "unreadable"}:
            found.append(
                Finding(
                    "ORQ-E150",
                    f"{name} is protected and {item.state}. Restore it with `orqlet upgrade`; "
                    "CI fails until then.",
                    Severity.ERROR,
                    item.path,
                )
            )
        elif item.state == "unreadable":
            found.append(
                Finding("ORQ-W153", f"{name} cannot be read safely.", Severity.WARNING, item.path)
            )
        elif item.state == "missing":
            found.append(Finding("ORQ-W151", f"{name} is missing.", Severity.WARNING, item.path))
        else:
            found.append(
                Finding(
                    "ORQ-W152",
                    f"{name} was edited after Orqlet wrote it. `upgrade` will not overwrite it.",
                    Severity.WARNING,
                    item.path,
                )
            )
    return found


def _extra_reserved_files(project: FileSystem, inst: Installation) -> list[Finding]:
    """Names in the managed folders that use the reserved prefix but are not in the manifest.

    A skill is a folder, so a folder counts as listed when the manifest names a file below it.
    """
    listed = {str(entry.path) for entry in inst.recorded} | set(inst.released)
    found = []
    for directory in _MANAGED_DIRECTORIES:
        folder = CanonicalPath.parse(directory)
        if project.kind(folder) is not FileKind.DIRECTORY:
            continue
        for name in project.list_dir(folder):
            if not name.lower().startswith(RESERVED_PREFIX):
                continue
            path = f"{directory}/{name}"
            if path not in listed and not any(item.startswith(f"{path}/") for item in listed):
                if _holds_no_file(project, path):
                    continue  # left by a release whose `apply_plan` removed files and not folders
                found.append(
                    Finding(
                        "ORQ-E153",
                        f"{path} uses the reserved prefix `{RESERVED_PREFIX}` but is not in the "
                        "manifest. Rename it or run `orqlet upgrade`.",
                        Severity.ERROR,
                        path,
                    )
                )
    return found


def _holds_no_file(project: FileSystem, path: str) -> bool:
    """True for a folder that has no file anywhere below it. A name that cannot be checked counts as
    something that is there."""
    pending = [path]
    visited = 0
    while pending:
        visited += 1
        if visited > _MAX_FOLDERS_VISITED:
            return False
        current = pending.pop()
        try:
            target = CanonicalPath.parse(current)
            if project.kind(target) is not FileKind.DIRECTORY:
                return False
            pending += [f"{current}/{name}" for name in project.list_dir(target)]
        except (InvalidPath, FileSystemError):
            return False
    return True


def _resource_findings(services: Services) -> list[Finding]:
    """What `doctor` says about the registry of links and its stored copies (ADR-002 decision 9).

    A copy past its time-to-live is only advised: the record is the team's own hand edit away
    from looking fresh. A copy that differs from its hash is an error, as `validate resources`
    says. A copy whose entry is gone is named, never deleted.
    """
    project = services.project
    registry = str(resources_path())
    resources, problems = load_resources(project, services.loader, registry)
    if resources is None:
        return list(problems)
    found: list[Finding] = []
    now = services.clock.now()
    for item in resources.resources:
        record = item.stored_copy
        if record is None:
            continue
        path = copy_path(item.id)
        if is_stale(datetime.fromisoformat(record.retrieved_at), record.ttl_days, now):
            found.append(
                Finding(
                    "ORQ-W500",
                    f"The stored copy {path} was retrieved at {record.retrieved_at} and its "
                    f"time-to-live of {record.ttl_days} days has passed. Read the page again and "
                    "attach a new copy. Freshness is advisory: the record is a hand edit away from "
                    "looking fresh.",
                    Severity.WARNING,
                    path,
                )
            )
        data = _read_regular_file(project, path)
        if data is not None and content_hash(data) != record.sha256:
            found.append(
                Finding(
                    "ORQ-E505",
                    f"The stored copy {path} differs from the SHA-256 recorded in {registry}. "
                    "Attach it again if the change is wanted, or restore it from Git.",
                    Severity.ERROR,
                    path,
                )
            )
    return found + _copies_without_an_entry(project, {item.id for item in resources.resources})


def _read_regular_file(project: FileSystem, path: str) -> bytes | None:
    try:
        target = CanonicalPath.parse(path)
        if project.kind(target) is not FileKind.FILE:
            return None
        return project.read_bytes(target)
    except (InvalidPath, FileSystemError):
        return None


def _copies_without_an_entry(project: FileSystem, ids: set[str]) -> list[Finding]:
    folder = CanonicalPath.parse("docs/resources")
    try:
        if project.kind(folder) is not FileKind.DIRECTORY:
            return []
        names = project.list_dir(folder)
    except FileSystemError:
        return []
    found = []
    for name in names:
        stem = name.removesuffix(".md")
        if stem == name or stem in ids or resource_id_problems(stem):
            continue
        path = copy_path(stem)
        found.append(
            Finding(
                "ORQ-I501",
                f"{path} is a stored copy whose entry is gone. Orqlet never deletes a copy: "
                "remove the file yourself if it is no longer wanted.",
                Severity.INFO,
                path,
            )
        )
    return found


def _version_findings(services: Services, inst: Installation) -> list[Finding]:
    found: list[Finding] = []
    release = services.workflow.release
    if inst.versions is not None and inst.versions.cli.pinned != services.orqlet_version:
        found.append(
            Finding(
                "ORQ-W160",
                f"Version skew: this CLI is {services.orqlet_version} and the project pins "
                f"{inst.versions.cli.pinned}. Install the pinned version.",
                Severity.WARNING,
            )
        )
    installed = inst.installed_release
    if installed is None:
        found.append(Finding("ORQ-W164", ".orqlet/workflow.lock is missing.", Severity.WARNING))
        return found
    if installed.version == release.version and installed.digest != release.digest:
        found.append(
            Finding(
                "ORQ-E161",
                f"Workflow {installed.version} in this project and in this CLI have different "
                "digests. One of them was changed without a version change.",
                Severity.ERROR,
            )
        )
    elif installed.version < release.version:
        found.append(
            Finding(
                "ORQ-W162",
                f"An upgrade is available: workflow {installed.version} to {release.version}.",
                Severity.WARNING,
            )
        )
    elif installed.version > release.version:
        found.append(
            Finding(
                "ORQ-W165",
                f"This CLI carries workflow {release.version}, older than the project's "
                f"{installed.version}. Install a newer Orqlet.",
                Severity.WARNING,
            )
        )
    floor = inst.floor
    if floor is not None and is_below_floor(installed.version, floor):
        found.append(
            Finding(
                "ORQ-E163",
                f"The project's workflow {installed.version} is below the floor {floor}.",
                Severity.ERROR,
            )
        )
    if (
        inst.versions is not None
        and inst.versions.workflow.digest != installed.digest
        and Version.parse(inst.versions.workflow.version) == installed.version
    ):
        found.append(
            Finding(
                "ORQ-W166",
                ".orqlet/versions.yaml and .orqlet/workflow.lock name different digests for "
                f"workflow {installed.version}.",
                Severity.WARNING,
            )
        )
    return found


def _journal_findings(services: Services, inst: Installation) -> list[Finding]:
    stores = services.stores(inst.profile.project.uuid)
    open_changes = stores.journal.open_changes()
    return [
        Finding(
            "ORQ-E170",
            f"Change {change_id} did not finish. Run `orqlet upgrade --resume` or "
            f"`orqlet rollback {change_id}`. Until then the setup may mix two versions.",
            Severity.ERROR,
        )
        for change_id in open_changes
    ]


def _standards_lock_findings(services: Services, inst: Installation) -> list[Finding]:
    if inst.lock.standards_lock is None:
        return []
    if services.project.kind(STANDARDS_LOCK_PATH) is not FileKind.FILE:
        return [Finding("ORQ-W190", ".orqlet/standards.lock.yaml is missing.", Severity.WARNING)]
    actual = sha256_hex(services.project.read_bytes(STANDARDS_LOCK_PATH))
    if actual != inst.lock.standards_lock:
        return [
            Finding(
                "ORQ-W191",
                ".orqlet/standards.lock.yaml differs from what the manifest recorded.",
                Severity.WARNING,
            )
        ]
    return []


def _profile_findings(inst: Installation) -> list[Finding]:
    found = []
    if inst.profile.profile.status != "approved":
        found.append(
            Finding(
                "ORQ-W180",
                "The project profile is a draft: nobody has recorded approving it. "
                "Approve it with `orqlet profile approve --reviewer NAME`.",
                Severity.WARNING,
            )
        )
    open_now = open_questions(inst.profile)
    if open_now:
        found.append(
            Finding(
                "ORQ-W181",
                f"{len(open_now)} fact(s) are still unknown: "
                + ", ".join(question.id for question in open_now)
                + ". Answer with `orqlet profile answer KEY=VALUE`.",
                Severity.WARNING,
            )
        )
    return found


def _convention_findings(inst: Installation) -> list[Finding]:
    """Information only: the conventions that are not recorded, and the ones that a host enforces.

    No warning is added, so the exit code of `doctor` for an existing install does not change
    when it upgrades (ADR-003 decisions 2 and 6).
    """
    repository = inst.profile.repository
    requests = repository.pull_requests
    facts = {
        "repository.branch_model": repository.branch_model.value,
        "repository.branch_patterns": repository.branch_patterns.value,
        "repository.release_flow": repository.release_flow.value,
        "repository.pull_requests.shape": requests.shape.value,
        "repository.pull_requests.merge_strategy": _answer_of(requests.merge_strategy),
        "repository.pull_requests.reviewers": _answer_of(requests.reviewers),
        "repository.pull_requests.required_checks": requests.required_checks.value,
    }
    unknown = [key for key, value in facts.items() if value is None]
    told = [
        key for key, value in facts.items() if key not in _NOT_HOST_ENFORCED and _is_a_rule(value)
    ]
    found = []
    if unknown:
        found.append(
            Finding(
                "ORQ-I502",
                "These conventions are not recorded yet: "
                + ", ".join(unknown)
                + ". Answer with `orqlet profile answer KEY=VALUE`, or answer none if the team "
                "has no rule.",
                Severity.INFO,
            )
        )
    if told:
        found.append(
            Finding(
                "ORQ-I503",
                "Recorded, and not checked by Orqlet: "
                + ", ".join(told)
                + ". Orqlet cannot read your host, so confirm the branch protection settings "
                "there.",
                Severity.INFO,
            )
        )
    return found


def _answer_of(text: str) -> str | None:
    """A plain-text answer, or `None` while it is still the unanswered `unknown`."""
    return None if text == "unknown" else text


def _is_a_rule(answer: str | None) -> bool:
    return answer is not None and answer.strip().lower() != "none"


def _released_findings(inst: Installation) -> list[Finding]:
    return [
        Finding(
            "ORQ-I210",
            f"{path} was released to the team and is no longer managed.",
            Severity.INFO,
            path,
        )
        for path in sorted(inst.released)
    ]


def _first_run_notes(inst: Installation) -> list[Finding]:
    notes = {
        "claude-code": "Claude Code asks you to trust the folder and approve project settings.",
        "codex": "Codex applies project configuration only after you trust the project.",
        "cursor": "Cursor asks for workspace trust and approval of project servers.",
    }
    return [
        Finding("ORQ-I202", f"{client}: {notes[client]}", Severity.INFO)
        for client in inst.profile.clients.enabled
    ]


def _reserved_name_findings(names: tuple[object, ...]) -> list[Finding]:
    found = []
    for item in names:
        name = getattr(item, "name", "")
        if name.lower().startswith(RESERVED_PREFIX):
            found.append(
                Finding(
                    "ORQ-W100",
                    f"A personal item named {name!r} in {getattr(item, 'location', '')} uses the "
                    f"reserved prefix `{RESERVED_PREFIX}` and can shadow a required item. "
                    "Rename it.",
                    Severity.WARNING,
                )
            )
    return found


def _prompts_dir(inst: Installation) -> str:
    for source in inst.profile.standards_sources:
        if source.kind == "prompts-dir" and source.path:
            return source.path
    return ".prompts"
