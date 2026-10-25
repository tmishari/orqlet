"""`orqlet profile answer` and `orqlet profile approve`: change the profile after `init`.

`init` can ask questions only while it runs. These commands let a maintainer answer a fact that
was left unknown, or record that the profile was reviewed, later and with the same checks. The
profile is team-owned, so the change is a normal journalled apply that `rollback` can undo.
Changing any fact withdraws an earlier approval, because the content that was reviewed changed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from orqlet.application.contracts.profile import ProfileMeta, ProjectProfile, Technology
from orqlet.application.ports.prompter import NoAnswerAvailable
from orqlet.application.usecases.apply_plan import apply_plan
from orqlet.application.usecases.init_files import contract_bytes, lock_from_recorded
from orqlet.application.usecases.init_questions import ANSWER_KEYS, apply_answers
from orqlet.application.usecases.installation import Installation, load_installation
from orqlet.application.usecases.render_all import LOCK_PATH, PROFILE_PATH, planned_write
from orqlet.application.usecases.services import Services
from orqlet.domain.changeplan import ChangePlan, Recorded, normalised_hash
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import OwnerMode

ProfileEditStatus = Literal["applied", "previewed", "needs-input", "refused"]
_MAX_REVIEWER = 100


@dataclass(frozen=True, slots=True)
class ProfileEditResult:
    status: ProfileEditStatus
    findings: tuple[Finding, ...] = ()
    plan: ChangePlan | None = None
    change_id: str | None = None
    profile: ProjectProfile | None = None


def answer_profile(
    services: Services,
    answers: Mapping[str, str],
    *,
    assume_yes: bool = False,
    dry_run: bool = False,
) -> ProfileEditResult:
    inst = load_installation(services)
    unknown = sorted(set(answers) - ANSWER_KEYS)
    if unknown:
        return _refused(
            "ORQ-E160",
            f"Not a fact that can be answered: {', '.join(unknown)}. "
            f"Choose from: {', '.join(sorted(ANSWER_KEYS))}.",
        )
    evidenced = [
        key
        for key in ("facts.python", "facts.package_manager")
        if key in answers and _read_from_files(inst.profile, key)
    ]
    if evidenced:
        return _refused(
            "ORQ-E161",
            f"{', '.join(evidenced)} is read from the project's files, with evidence. "
            "Change the file instead; an answer here would hide what the file says.",
        )
    notes: list[str] = []
    changed = apply_answers(inst.profile, answers, notes)
    changed = _without_duplicate_technologies(changed)
    findings = [Finding("ORQ-W060", note, Severity.WARNING) for note in notes]
    if changed == inst.profile:
        findings.append(Finding("ORQ-E162", "These answers change nothing.", Severity.ERROR))
        return ProfileEditResult("refused", tuple(findings), profile=inst.profile)
    if inst.profile.profile.status == "approved":
        changed = _withdraw_approval(changed)
        findings.append(
            Finding(
                "ORQ-I070",
                "The profile changed, so the earlier approval is withdrawn. "
                "Approve it again with `orqlet profile approve`.",
                Severity.INFO,
            )
        )
    return _commit(services, inst, changed, findings, "profile", assume_yes, dry_run)


def approve_profile(
    services: Services,
    reviewer: str,
    *,
    assume_yes: bool = False,
    dry_run: bool = False,
) -> ProfileEditResult:
    inst = load_installation(services)
    name = reviewer.strip()
    if not name or len(name) > _MAX_REVIEWER or "\n" in name or "\r" in name:
        return _refused("ORQ-E163", "A reviewer name is required: one short line.")
    meta = inst.profile.profile
    if meta.status == "approved":
        return _refused(
            "ORQ-E164",
            f"The profile was already approved by {meta.reviewed_by} on {meta.reviewed_at}.",
        )
    approved = inst.profile.model_copy(
        update={
            "profile": ProfileMeta(
                version=meta.version,
                status="approved",
                reviewed_by=name,
                reviewed_at=services.clock.now().isoformat(),
            )
        }
    )
    return _commit(services, inst, approved, [], "profile", assume_yes, dry_run)


# --- internals ---------------------------------------------------------------------------------
def _read_from_files(profile: ProjectProfile, key: str) -> bool:
    fact = profile.facts.python if key == "facts.python" else profile.facts.package_manager
    return bool(fact.evidence)


def _withdraw_approval(profile: ProjectProfile) -> ProjectProfile:
    meta = ProfileMeta(version=profile.profile.version, status="draft")
    return profile.model_copy(update={"profile": meta})


def _without_duplicate_technologies(profile: ProjectProfile) -> ProjectProfile:
    seen: set[tuple[str, str, str | None, str]] = set()
    kept: list[Technology] = []
    for technology in profile.technologies:
        key = (technology.kind, technology.name, technology.version, technology.scope)
        if key not in seen:
            seen.add(key)
            kept.append(technology)
    return profile.model_copy(update={"technologies": tuple(kept)})


def _commit(
    services: Services,
    inst: Installation,
    profile: ProjectProfile,
    findings: list[Finding],
    command: str,
    assume_yes: bool,
    dry_run: bool,
) -> ProfileEditResult:
    content = contract_bytes(services.writer, profile)
    remaining = [entry for entry in inst.recorded if entry.path != PROFILE_PATH]
    remaining.append(
        Recorded(
            path=PROFILE_PATH,
            owner=OwnerMode.SEEDED,
            file_class=None,
            sha256=normalised_hash(content),
        )
    )
    lock = lock_from_recorded(
        remaining, orqlet_version=services.orqlet_version, standards_lock=inst.lock.standards_lock
    )
    plan = ChangePlan(
        items=(),
        writes=(
            planned_write(services, PROFILE_PATH, content),
            planned_write(services, LOCK_PATH, contract_bytes(services.writer, lock), last=True),
        ),
        recorded_after=tuple(remaining),
    )
    if dry_run:
        return ProfileEditResult("previewed", tuple(findings), plan, profile=profile)
    if not (assume_yes or _confirmed(services)):
        if services.prompter.interactive:
            return ProfileEditResult("previewed", tuple(findings), plan, profile=profile)
        findings.append(
            Finding("ORQ-E115", "Nothing was applied: run again with --yes.", Severity.ERROR)
        )
        return ProfileEditResult("needs-input", tuple(findings), plan, profile=profile)
    stores = services.stores(profile.project.uuid)
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
    return ProfileEditResult("applied", tuple(findings), plan, change_id, profile)


def _confirmed(services: Services) -> bool:
    if not services.prompter.interactive:
        return False
    try:
        return services.prompter.confirm("Change the project profile?", default=False)
    except NoAnswerAvailable:
        return False


def _refused(code: str, message: str) -> ProfileEditResult:
    return ProfileEditResult("refused", (Finding(code, message, Severity.ERROR),))
