"""`orqlet rollback <change-id>`: undo one applied change from its journal (ADR-004, 9.5).

A file is restored only if it still equals what Orqlet applied. If anything changed since, the
rollback refuses and says which files, so no one's later work is lost. A rollback that would
lower the workflow below the floor, or lower its controls level, is refused like a downgrade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.workflow_package import WorkflowLock
from orqlet.application.ports.change_journal import BackupStore, JournalRecord
from orqlet.application.ports.filesystem import FileKind
from orqlet.application.ports.prompter import NoAnswerAvailable
from orqlet.application.usecases.apply_plan import apply_plan
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.render_all import LOCK_PATH, WORKFLOW_LOCK_PATH
from orqlet.application.usecases.services import Services
from orqlet.domain.changeplan import ChangePlan, PlannedWrite
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.versions import Version, WorkflowRelease, is_below_floor

RollbackStatus = Literal["applied", "previewed", "needs-input", "refused"]


@dataclass(frozen=True, slots=True)
class RollbackOptions:
    change_id: str
    assume_yes: bool = False
    dry_run: bool = False
    allow_weaker: bool = False
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class RollbackResult:
    status: RollbackStatus
    findings: tuple[Finding, ...] = ()
    plan: ChangePlan | None = None
    change_id: str | None = None


def rollback(services: Services, options: RollbackOptions) -> RollbackResult:
    project_id = options.project_id or _project_id(services)
    stores = services.stores(project_id)
    record = stores.journal.read(options.change_id)
    if record is None:
        return _refused("ORQ-E132", f"There is no journal for change {options.change_id}.")
    if record.status == "rolled-back":
        return _refused("ORQ-E133", f"Change {options.change_id} was already rolled back.")

    findings: list[Finding] = []
    writes, changed, missing = _reversals(services, stores.backups, record)
    if changed:
        return _refused(
            "ORQ-E133",
            "Refused: these files changed after the change was applied, so restoring them "
            "would lose later work: " + ", ".join(changed),
        )
    if missing:
        return _refused("ORQ-E134", "Refused: no backup is kept for " + ", ".join(missing) + ".")
    weaker = _weaker_workflow(services, writes)
    if weaker and not options.allow_weaker:
        return _refused("ORQ-E120", "Refused, this is a downgrade: " + weaker)
    if weaker:
        findings.append(
            Finding(
                "ORQ-W095",
                "Downgrade allowed with --allow-weaker: " + weaker + " It needs two approvals "
                "when it is merged.",
                Severity.WARNING,
            )
        )
    plan = ChangePlan(items=(), writes=tuple(writes), recorded_after=())
    if options.dry_run:
        return RollbackResult("previewed", tuple(findings), plan)
    if not (options.assume_yes or _confirmed(services, len(writes))):
        if services.prompter.interactive:
            return RollbackResult("previewed", tuple(findings), plan)
        findings.append(
            Finding(
                "ORQ-E115", "Nothing was applied: run again with --yes to approve.", Severity.ERROR
            )
        )
        return RollbackResult("needs-input", tuple(findings), plan)

    change_id = services.ids.new_id()
    apply_plan(
        services.project,
        stores.journal,
        stores.backups,
        plan,
        lock=stores.lock,
        change_id=change_id,
        command="rollback",
        clock=services.clock,
    )
    stores.journal.finish(options.change_id, "rolled-back")
    return RollbackResult("applied", tuple(findings), plan, change_id)


# --- internals ---------------------------------------------------------------------------------
def _project_id(services: Services) -> str:
    return load_installation(services).profile.project.uuid


def _refused(code: str, message: str) -> RollbackResult:
    return RollbackResult("refused", (Finding(code, message, Severity.ERROR),))


def _reversals(
    services: Services, backups: BackupStore, record: JournalRecord
) -> tuple[list[PlannedWrite], list[str], list[str]]:
    """The writes that undo `record`, the files that changed since, and the missing backups."""
    project = services.project
    writes: list[PlannedWrite] = []
    changed: list[str] = []
    missing: list[str] = []
    for entry in record.entries:
        if not entry.done:
            continue  # an interrupted change: files it never reached are as they were
        path = CanonicalPath.parse(entry.path)
        exists = project.kind(path) is FileKind.FILE
        current = sha256_hex(project.read_bytes(path)) if exists else None
        if current != entry.after_sha256:
            changed.append(entry.path)
            continue
        last = path == LOCK_PATH
        if entry.kind == "create":
            writes.append(
                PlannedWrite(path, "delete", current, None, None, entry.is_proposal, last)
            )
            continue
        before = backups.load(record.change_id, path)
        if before is None:
            missing.append(entry.path)
            continue
        kind = "update" if exists else "create"
        writes.append(
            PlannedWrite(path, kind, current, sha256_hex(before), before, entry.is_proposal, last)
        )
    return writes, changed, missing


def _weaker_workflow(services: Services, writes: list[PlannedWrite]) -> str:
    """Why restoring `.orqlet/workflow.lock` would weaken the setup, or an empty string."""
    restore = next(
        (w for w in writes if w.path == WORKFLOW_LOCK_PATH and w.content is not None), None
    )
    if restore is None:
        return ""  # nothing is restored, or the whole setup is being removed
    installation = load_installation(services)
    installed = installation.installed_release
    older = load_contract(services.loader, WorkflowLock, restore.content or b"", source="backup")
    candidate = WorkflowRelease(
        Version.parse(older.workflow_version), older.workflow_digest, older.controls_level
    )
    floor = installation.floor
    reasons = []
    if floor is not None and is_below_floor(candidate.version, floor):
        reasons.append(f"workflow {candidate.version} is below the floor {floor}.")
    if installed is not None and candidate.controls_level < installed.controls_level:
        reasons.append(
            f"controls level {candidate.controls_level} is lower than the installed "
            f"{installed.controls_level}."
        )
    return " ".join(reasons)


def _confirmed(services: Services, count: int) -> bool:
    if not services.prompter.interactive:
        return False
    try:
        return services.prompter.confirm(f"Restore {count} file(s)?", default=False)
    except NoAnswerAvailable:
        return False
