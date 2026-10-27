"""Builders and commands that change the registry (ADR-002 decisions 7 and 9).

`resources_with` and `resources_without` are pure: they take the registry and what the person asked
for and return a new registry, or no registry and one finding ORQ-E509 that says what was refused.
`init` and the four commands (`add_resource`, `update_resource`, `remove_resource`, `attach_copy`)
call them, so an entry is always built and checked in one place.

A command reads the registry, builds a change plan of the registry and the lock and applies it as
one journalled change that `rollback` can undo, as `profile answer` does for the profile. It renders
nothing: the files that follow from a change are written by `orqlet upgrade`, so a link edit never
carries the changes of a workflow release with it.

A refusal names the rule and the field and never repeats a value that the person typed
(ORQLET-SEC-003): the result is checked by the `Resources` contract, whose errors hold no input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from orqlet.application.contracts.resources import Resource, Resources
from orqlet.application.ports.filesystem import FileKind, FileSystemError
from orqlet.application.ports.prompter import NoAnswerAvailable
from orqlet.application.usecases.apply_plan import apply_plan
from orqlet.application.usecases.init_files import contract_bytes, lock_from_recorded
from orqlet.application.usecases.installation import Installation, load_installation
from orqlet.application.usecases.render_all import LOCK_PATH, planned_write
from orqlet.application.usecases.resources_source import load_resources, resources_path
from orqlet.application.usecases.services import Services
from orqlet.application.usecases.validation import content_hash
from orqlet.domain.changeplan import ChangePlan, Recorded, normalised_hash
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resources import (
    copy_path,
    copy_problems,
    credential_problems,
    hidden_text_problems,
    host_of,
)

_REFUSED = "ORQ-E509"
_MAX_COPY_BYTES = 64 * 1024
_FORMS = ("copy", "summary")
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

    A success carries the notice ORQ-I500 when the entry is behind a login.

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
    built, problems = _checked(entries)
    return built, (*problems, *_login_notice(spec.access)) if built is not None else problems


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


# --- the commands -------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class CopySpec:
    """The stored copy of one entry that `attach_copy` records: its form and its time-to-live."""

    id: str
    form: str
    ttl_days: int


@dataclass(frozen=True, slots=True)
class ResourcesEditResult:
    status: Literal["applied", "previewed", "needs-input", "refused"]
    findings: tuple[Finding, ...] = ()
    plan: ChangePlan | None = None
    change_id: str | None = None
    resources: Resources | None = None
    notes: tuple[str, ...] = ()


def add_resource(
    services: Services, spec: ResourceSpec, assume_yes: bool, dry_run: bool
) -> ResourcesEditResult:
    """Add one entry. The files that follow from it are written by the next `upgrade`."""
    inst = load_installation(services)
    current = _current(services, inst)
    if isinstance(current, ResourcesEditResult):
        return current
    built, found = resources_with(current, spec, replace=False)
    if built is None:
        return _stopped(found)
    notes = ["Run `orqlet upgrade` to write the files that follow from this entry."]
    return _commit(services, inst, built, [*found], notes, "resources add", assume_yes, dry_run)


def update_resource(
    services: Services, spec: ResourceSpec, assume_yes: bool, dry_run: bool
) -> ResourcesEditResult:
    """Change the fields that are given. The id never changes; a stored copy keeps its record."""
    inst = load_installation(services)
    current = _current(services, inst)
    if isinstance(current, ResourcesEditResult):
        return current
    built, found = resources_with(current, spec, replace=True)
    if built is None:
        return _stopped(found)
    before = _entry(current, spec.id)
    notes: list[str] = []
    if spec.url is not None and before is not None and before.stored_copy is not None:
        notes.append(
            f"The Source line of {copy_path(spec.id)} no longer matches the new address, so "
            "`orqlet validate resources` fails until the copy is refreshed and attached again."
        )
    return _commit(services, inst, built, [*found], notes, "resources update", assume_yes, dry_run)


def remove_resource(
    services: Services, resource_id: str, assume_yes: bool, dry_run: bool
) -> ResourcesEditResult:
    """Remove one entry. Its stored copy is the team's file: the person deletes it."""
    inst = load_installation(services)
    current = _current(services, inst)
    if isinstance(current, ResourcesEditResult):
        return current
    built, problems = resources_without(current, resource_id)
    if built is None:
        return _stopped(problems)
    notes: list[str] = []
    path = copy_path(resource_id)
    if services.project.kind(CanonicalPath.parse(path)) is not None:
        notes.append(
            f"{path} is kept. Delete it yourself: `orqlet validate resources` fails for a copy "
            "that no entry names."
        )
    return _commit(services, inst, built, [], notes, "resources remove", assume_yes, dry_run)


def attach_copy(
    services: Services, spec: CopySpec, assume_yes: bool, dry_run: bool
) -> ResourcesEditResult:
    """Record the stored copy that a person or an agent wrote at `docs/resources/<id>.md`.

    The copy is checked as `validate resources` checks it. The record holds the SHA-256 of the
    text with line endings read as LF and the time from the clock. For an entry behind a login the
    person is asked at a terminal even with `assume_yes` (ADR-002 decision 9).
    """
    inst = load_installation(services)
    current = _current(services, inst)
    if isinstance(current, ResourcesEditResult):
        return current
    entry = _entry(current, spec.id)
    if entry is None:
        return _stopped(_refusal("there is no entry with that id to attach a copy to"))
    data = _copy_bytes(services, spec.id)
    if isinstance(data, ResourcesEditResult):
        return data
    flagged = _copy_refusal(data, entry.url)
    if flagged is not None:
        return flagged
    record = {
        "form": spec.form,
        "sha256": content_hash(data),
        "retrieved_at": services.clock.now().isoformat(),
        "ttl_days": spec.ttl_days,
    }
    entries = _entries_of(current)
    entries[spec.id]["stored_copy"] = record
    built, problems = _checked(entries)
    if built is None:
        return _stopped(problems)
    if entry.access == "login" and not dry_run:
        stopped = _login_gate(services, host_of(entry.url))
        if stopped is not None:
            return stopped
    return _commit(services, inst, built, [], [], "resources attach", assume_yes, dry_run)


def _current(services: Services, inst: Installation) -> Resources | ResourcesEditResult:
    """The registry on disk, or a refusal that writes nothing."""
    path = resources_path()
    resources, problems = load_resources(services.project, services.loader, str(path))
    if resources is None:
        return _stopped(problems)
    if services.project.kind(path) is None and any(item.path == path for item in inst.recorded):
        return _stopped(
            (
                Finding(
                    "ORQ-E503",
                    f"The registry {path} is missing, but the lock records it. Restore it from "
                    "Git, or write an empty valid one (`schema: orqlet.resources/v1` and "
                    "`resources: []`) first.",
                    Severity.ERROR,
                    str(path),
                ),
            )
        )
    return resources


def _entry(resources: Resources, resource_id: str) -> Resource | None:
    return next((item for item in resources.resources if item.id == resource_id), None)


def _login_notice(access: str | None) -> list[Finding]:
    if access != "login":
        return []
    return [
        Finding(
            "ORQ-I500",
            "This entry is behind a login. The text of its page is read by the client that you "
            "use and goes to that client's model vendor. Whether internal content may take this "
            "route is a decision of the owners of that content; keep a summary, not the page.",
            Severity.INFO,
        )
    ]


def _copy_bytes(services: Services, resource_id: str) -> bytes | ResourcesEditResult:
    path = copy_path(resource_id)
    try:
        target = CanonicalPath.parse(path)
        kind = services.project.kind(target)
        if kind is FileKind.FILE:
            return services.project.read_bytes(target)
    except FileSystemError:
        kind = FileKind.OTHER
    reason = "is missing" if kind is None else "is not a regular file that can be read safely"
    return _stopped((Finding("ORQ-E504", f"{path} {reason}.", Severity.ERROR, path),))


def _copy_refusal(data: bytes, address: str) -> ResourcesEditResult | None:
    """The refusal for a copy that `validate resources` would flag, or `None`."""
    if len(data) > _MAX_COPY_BYTES:
        return _stopped((Finding("ORQ-E506", "The copy is above 64 KiB.", Severity.ERROR),))
    try:
        text = data.replace(b"\r\n", b"\n").decode("utf-8")
    except UnicodeDecodeError:
        return _stopped((Finding("ORQ-E506", "The copy is not valid UTF-8.", Severity.ERROR),))
    problems = (
        *copy_problems(text, address),
        *hidden_text_problems(text),
        *credential_problems(text),
    )
    if not problems:
        return None
    return _stopped(
        (
            Finding(
                "ORQ-E506", f"The copy fails these checks: {', '.join(problems)}.", Severity.ERROR
            ),
        )
    )


def _login_gate(services: Services, host: str) -> ResourcesEditResult | None:
    """Ask at a terminal, also with `--yes`; without a terminal nothing is recorded."""
    if not services.prompter.interactive:
        return ResourcesEditResult(
            "needs-input",
            (
                Finding(
                    "ORQ-E510",
                    "This entry is behind a login, so a person must confirm at a terminal that "
                    "the repository may hold internal content of its host. Run the command again "
                    "in a terminal.",
                    Severity.ERROR,
                ),
            ),
        )
    try:
        confirmed = services.prompter.confirm(
            f"May this repository hold internal content of {host}?", default=False
        )
    except NoAnswerAvailable:
        confirmed = False
    if confirmed:
        return None
    return _stopped(_refusal("the copy of a login page was not confirmed, so nothing was recorded"))


def _commit(
    services: Services,
    inst: Installation,
    resources: Resources,
    findings: list[Finding],
    notes: list[str],
    command: str,
    assume_yes: bool,
    dry_run: bool,
) -> ResourcesEditResult:
    content = contract_bytes(services.writer, resources)
    path = resources_path()
    remaining = [entry for entry in inst.recorded if entry.path != path]
    remaining.append(
        Recorded(
            path=path, owner=OwnerMode.SEEDED, file_class=None, sha256=normalised_hash(content)
        )
    )
    lock = lock_from_recorded(
        remaining, orqlet_version=services.orqlet_version, standards_lock=inst.lock.standards_lock
    )
    plan = ChangePlan(
        items=(),
        writes=(
            planned_write(services, path, content),
            planned_write(services, LOCK_PATH, contract_bytes(services.writer, lock), last=True),
        ),
        recorded_after=tuple(remaining),
    )
    kept = tuple(notes)
    if dry_run:
        return ResourcesEditResult("previewed", tuple(findings), plan, None, resources, kept)
    if not (assume_yes or _confirmed(services)):
        if services.prompter.interactive:
            return ResourcesEditResult("previewed", tuple(findings), plan, None, resources, kept)
        findings.append(
            Finding("ORQ-E115", "Nothing was applied: run again with --yes.", Severity.ERROR)
        )
        return ResourcesEditResult("needs-input", tuple(findings), plan, None, resources, kept)
    stores = services.stores(inst.profile.project.uuid)
    change_id = services.ids.new_id()
    apply_plan(
        services.project,
        stores.journal,
        stores.backups,
        plan,
        lock=stores.lock,
        change_id=change_id,
        command=command,
        clock=services.clock,
    )
    return ResourcesEditResult("applied", tuple(findings), plan, change_id, resources, kept)


def _confirmed(services: Services) -> bool:
    if not services.prompter.interactive:
        return False
    try:
        return services.prompter.confirm("Change the registry of links?", default=False)
    except NoAnswerAvailable:
        return False


def _stopped(findings: tuple[Finding, ...]) -> ResourcesEditResult:
    return ResourcesEditResult("refused", findings)


def _refusal(reason: str) -> tuple[Finding, ...]:
    return (Finding(_REFUSED, f"The change was refused: {reason}.", Severity.ERROR),)
