"""`orqlet release <path>`: hand a generated file over to the team (proposal section 9.3).

The file leaves the manifest, a committed record under `.orqlet/` names the path and the reason,
and later upgrades no longer touch it. A protected file can never be released: weakening the
workflow is a change to the Orqlet release, not a local decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.workflow_package import Released, ReleasedFile
from orqlet.application.ports.filesystem import FileKind
from orqlet.application.ports.prompter import NoAnswerAvailable
from orqlet.application.usecases.apply_plan import apply_plan
from orqlet.application.usecases.init_files import contract_bytes, lock_from_recorded
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.render_all import LOCK_PATH, RELEASED_PATH, planned_write
from orqlet.application.usecases.services import Services
from orqlet.domain.changeplan import ChangePlan, Recorded, normalised_hash
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath

ReleaseStatus = Literal["applied", "previewed", "needs-input", "refused"]


@dataclass(frozen=True, slots=True)
class ReleaseOptions:
    path: str
    reason: str
    assume_yes: bool = False
    released_by: str | None = None


@dataclass(frozen=True, slots=True)
class ReleaseResult:
    status: ReleaseStatus
    findings: tuple[Finding, ...] = ()
    plan: ChangePlan | None = None
    change_id: str | None = None


def release_file(services: Services, options: ReleaseOptions) -> ReleaseResult:
    inst = load_installation(services)
    reason = options.reason.strip()
    if not reason:
        return _refused("ORQ-E143", "A reason is required: it is written to the divergence record.")
    path = CanonicalPath.parse(options.path)
    entries = [entry for entry in inst.recorded if entry.path == path]
    if not entries:
        return _refused(
            "ORQ-E140", f"{path} is not in the manifest, so there is nothing to release."
        )
    if any(entry.file_class is FileClass.PROTECTED for entry in entries):
        return _refused(
            "ORQ-E141",
            f"{path} is protected and cannot be released. Propose the change through a release "
            "of Orqlet instead.",
        )
    if all(entry.owner is OwnerMode.SEEDED for entry in entries):
        return _refused("ORQ-E142", f"{path} was seeded: it already belongs to the team.")

    record_bytes, remaining = _new_state(services, inst.recorded, path, options)
    lock = lock_from_recorded(
        remaining,
        orqlet_version=services.orqlet_version,
        standards_lock=inst.lock.standards_lock,
    )
    plan = ChangePlan(
        items=(),
        writes=(
            planned_write(services, RELEASED_PATH, record_bytes, last=False),
            planned_write(services, LOCK_PATH, contract_bytes(services.writer, lock), last=True),
        ),
        recorded_after=tuple(remaining),
    )
    if not (options.assume_yes or _confirmed(services, path)):
        if services.prompter.interactive:
            return ReleaseResult("previewed", (), plan)
        return ReleaseResult(
            "needs-input",
            (Finding("ORQ-E115", "Nothing was applied: run again with --yes.", Severity.ERROR),),
            plan,
        )
    stores = services.stores(inst.profile.project.uuid)
    change_id = services.ids.new_id()
    apply_plan(
        services.project,
        stores.journal,
        stores.backups,
        plan,
        lock=stores.lock,
        change_id=change_id,
        command="release",
        clock=services.clock,
    )
    return ReleaseResult("applied", (), plan, change_id)


def _new_state(
    services: Services,
    recorded: list[Recorded],
    path: CanonicalPath,
    options: ReleaseOptions,
) -> tuple[bytes, list[Recorded]]:
    existing = _existing_records(services)
    files = [item for item in existing if item.path != str(path)]
    files.append(
        ReleasedFile(path=str(path), reason=options.reason.strip(), released_by=options.released_by)
    )
    record = Released(
        schema_id="orqlet.released/v1", files=tuple(sorted(files, key=lambda item: item.path))
    )
    data = contract_bytes(services.writer, record)
    remaining = [entry for entry in recorded if entry.path != path]
    remaining = [entry for entry in remaining if entry.path != RELEASED_PATH]
    remaining.append(
        Recorded(
            path=RELEASED_PATH,
            owner=OwnerMode.ORQLET,
            file_class=FileClass.GENERATED,
            sha256=normalised_hash(data),
        )
    )
    return data, remaining


def _existing_records(services: Services) -> list[ReleasedFile]:
    if services.project.kind(RELEASED_PATH) is not FileKind.FILE:
        return []
    return list(
        load_contract(
            services.loader,
            Released,
            services.project.read_bytes(RELEASED_PATH),
            source=str(RELEASED_PATH),
        ).files
    )


def _refused(code: str, message: str) -> ReleaseResult:
    return ReleaseResult("refused", (Finding(code, message, Severity.ERROR),))


def _confirmed(services: Services, path: CanonicalPath) -> bool:
    if not services.prompter.interactive:
        return False
    try:
        return services.prompter.confirm(f"Release {path} to the team?", default=False)
    except NoAnswerAvailable:
        return False
