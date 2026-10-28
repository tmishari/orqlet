"""`orqlet upgrade`: re-render an installation from the current release (proposal section 9.5).

The same composition as `init` is classified against what Orqlet recorded, so a file the team
edited is never overwritten, a tampered protected file is restored after the preview, seeded
files change only as proposals, and the manifest is replaced last. A downgrade is refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from orqlet.application.contracts.integrations import Integrations
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.filesystem import FileKind
from orqlet.application.ports.prompter import NoAnswerAvailable
from orqlet.application.usecases.apply_plan import apply_plan
from orqlet.application.usecases.init_files import contract_bytes
from orqlet.application.usecases.installation import Installation, load_installation
from orqlet.application.usecases.integrations_source import integrations_path, load_integrations
from orqlet.application.usecases.render_all import (
    PROFILE_PATH,
    RELEASED_PATH,
    compose,
    environment_findings,
    ignored_findings,
    plan_changes,
    resolve_for,
)
from orqlet.application.usecases.resources_source import load_resources, resources_path
from orqlet.application.usecases.services import Services
from orqlet.domain.changeplan import ChangePlan
from orqlet.domain.classify import FileState
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.mcp_credentials import mcp_file_path
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.versions import WorkflowRelease, is_below_floor, is_downgrade

UpgradeStatus = Literal["up-to-date", "available", "applied", "previewed", "needs-input", "refused"]


@dataclass(frozen=True, slots=True)
class UpgradeOptions:
    check: bool = False
    resume: bool = False
    assume_yes: bool = False
    dry_run: bool = False
    allow_weaker: bool = False
    packs_path: str | None = None


@dataclass(frozen=True, slots=True)
class UpgradeResult:
    status: UpgradeStatus
    findings: tuple[Finding, ...] = ()
    plan: ChangePlan | None = None
    change_id: str | None = None
    installed: WorkflowRelease | None = None
    candidate: WorkflowRelease | None = None
    resumed: tuple[str, ...] = field(default=())


def upgrade(services: Services, options: UpgradeOptions) -> UpgradeResult:
    inst = load_installation(services)
    release = services.workflow.release
    findings: list[Finding] = []
    stores = services.stores(inst.profile.project.uuid)

    unfinished = stores.journal.open_changes()
    if unfinished and not options.resume and not options.check:
        findings.append(
            Finding(
                "ORQ-E131",
                f"Change {unfinished[0]} did not finish. Run `orqlet upgrade --resume` to "
                f"finish it, or `orqlet rollback {unfinished[0]}` to undo it.",
                Severity.ERROR,
            )
        )
        return UpgradeResult(
            "refused", tuple(findings), installed=inst.installed_release, candidate=release
        )

    refusal = _downgrade_refusal(inst, release, options.allow_weaker, findings)
    if refusal:
        return UpgradeResult(
            "refused", tuple(findings), installed=inst.installed_release, candidate=release
        )

    wanted_packs = {pack.id for pack in (inst.standards_lock.packs if inst.standards_lock else ())}
    if wanted_packs and services.packs is None:
        findings.append(
            Finding(
                "ORQ-E121",
                "This project uses standards packs ("
                + ", ".join(sorted(wanted_packs))
                + "). Pass --packs-dir so their rules are rendered again; otherwise their files "
                "would be treated as no longer wanted.",
                Severity.ERROR,
            )
        )
        return UpgradeResult(
            "refused", tuple(findings), installed=inst.installed_release, candidate=release
        )

    registry = _registry(services, inst, findings)
    if registry is None:
        return UpgradeResult(
            "refused", tuple(findings), installed=inst.installed_release, candidate=release
        )
    resources, resources_bytes = registry
    integrations, refused = _integrations(services, findings)
    if refused:
        return UpgradeResult(
            "refused", tuple(findings), installed=inst.installed_release, candidate=release
        )
    resolution = resolve_for(services, inst.profile)
    profile_bytes = services.project.read_bytes(PROFILE_PATH)
    composition = compose(
        services,
        inst.profile,
        resolution,
        resources,
        clients=inst.profile.clients.enabled,
        prompts_dir=_prompts_dir(inst),
        pr_targets=inst.profile.repository.pull_requests.template.targets,
        profile_bytes=profile_bytes,
        resources_bytes=resources_bytes,
        integrations=integrations,
        orqlet_owned=frozenset(
            str(entry.path) for entry in inst.recorded if entry.owner is OwnerMode.ORQLET
        ),
        released=inst.released,
        released_record=_released_record(services, inst),
    )
    findings += composition.findings
    findings += environment_findings(services, _prompts_dir(inst))
    plan = plan_changes(services, composition.desired, inst.recorded)
    findings += _proposal_notes(services, plan)
    findings += [
        Finding(
            "ORQ-W080",
            item.reason or f"{item.path} conflicts with the new render; see the proposal file.",
            Severity.WARNING,
            str(item.path),
        )
        for item in plan.conflicts
    ]
    findings += ignored_findings(
        services, (w.path for w in plan.writes if w.kind != "delete" and not w.is_proposal)
    )
    findings += _tamper_notes(plan)
    if services.vcs.has_staged_changes():
        findings.append(
            Finding(
                "ORQ-W090",
                "There are staged changes. Upgrade on a clean tree or a new branch so the "
                "result is one reviewable change.",
                Severity.WARNING,
            )
        )
    if plan.is_empty:
        return UpgradeResult(
            "up-to-date", tuple(findings), plan, installed=inst.installed_release, candidate=release
        )
    if options.check:
        return UpgradeResult(
            "available", tuple(findings), plan, installed=inst.installed_release, candidate=release
        )
    if options.dry_run or not _approved(services, options, plan):
        status: UpgradeStatus = (
            "previewed" if options.dry_run or services.prompter.interactive else "needs-input"
        )
        if status == "needs-input":
            findings.append(
                Finding(
                    "ORQ-E115",
                    "Nothing was applied: run again with --yes to approve the plan.",
                    Severity.ERROR,
                )
            )
        return UpgradeResult(
            status, tuple(findings), plan, installed=inst.installed_release, candidate=release
        )

    change_id = services.ids.new_id()
    apply_plan(
        services.project,
        stores.journal,
        stores.backups,
        plan,
        lock=stores.lock,
        change_id=change_id,
        command="upgrade",
        clock=services.clock,
    )
    return UpgradeResult(
        "applied",
        tuple(findings),
        plan,
        change_id,
        inst.installed_release,
        release,
        resumed=tuple(unfinished),
    )


def _integrations(services: Services, findings: list[Finding]) -> tuple[Integrations | None, bool]:
    """The declaration as it is on disk, and whether it refuses the upgrade.

    An absent declaration is no declaration and writes no MCP file. A declaration that is present
    and cannot be used refuses the upgrade before any plan is built, so that a half-applied
    security setting never exists (ADR-003 decision 3).
    """
    declaration, problems = load_integrations(
        services.project, services.loader, str(integrations_path())
    )
    findings += problems
    refused = declaration is None and any(f.severity is Severity.ERROR for f in problems)
    return declaration, refused


def _proposal_notes(services: Services, plan: ChangePlan) -> list[Finding]:
    """One information finding for each proposal on an MCP file: it holds only the wanted text."""
    keys = set()
    for client in services.adapters:
        try:
            keys.add(CanonicalPath.parse(mcp_file_path(client)).key)
        except ValueError:
            continue  # a client without an MCP file
    return [
        Finding(
            "ORQ-I534",
            f"{item.path}: the proposal shows only the text that Orqlet wants and none of your "
            "file. Merge it by hand.",
            Severity.INFO,
            str(item.path),
        )
        for item in plan.items
        if item.state is FileState.SEEDED_PROPOSAL and item.path.key in keys
    ]


def _registry(
    services: Services, inst: Installation, findings: list[Finding]
) -> tuple[Resources, bytes] | None:
    """The registry as it is on disk, or `None` after a finding that refuses the upgrade.

    An invalid registry, or one that is missing while the lock records it, would turn into an
    empty one, and then every file rendered from it would be an orphan that the plan deletes. So
    both are refused before any plan is built (ADR-002 decision 6). A registry that is missing and
    not recorded is an empty one, and the upgrade writes it.
    """
    path = resources_path()
    resources, problems = load_resources(services.project, services.loader, str(path))
    if resources is None:
        detail = "; ".join(problem.message for problem in problems)
        findings.append(
            Finding(
                "ORQ-E503",
                f"The registry {path} cannot be used: {detail}. Nothing was changed. Fix the file "
                "or restore it from Git, then run `orqlet upgrade` again.",
                Severity.ERROR,
                str(path),
            )
        )
        return None
    if services.project.kind(path) is FileKind.FILE:
        return resources, services.project.read_bytes(path)
    if any(entry.path == path for entry in inst.recorded):
        findings.append(
            Finding(
                "ORQ-E503",
                f"The registry {path} is missing, but the lock records it. Nothing was changed, "
                "because the files that are rendered from it would be deleted. Restore it from "
                "Git, or write an empty valid one (`schema: orqlet.resources/v1` and "
                "`resources: []`) and remove entries with `orqlet resources remove`.",
                Severity.ERROR,
                str(path),
            )
        )
        return None
    return resources, contract_bytes(services.writer, resources)


def _downgrade_refusal(
    inst: Installation, release: WorkflowRelease, allow_weaker: bool, findings: list[Finding]
) -> bool:
    installed = inst.installed_release
    floor = inst.floor
    reasons = []
    if floor is not None and is_below_floor(release.version, floor):
        reasons.append(f"workflow {release.version} is below the floor {floor}")
    if installed is not None and is_downgrade(installed, release):
        reasons.append(
            f"workflow {release.version} (controls level {release.controls_level}) is older or "
            f"weaker than the installed {installed.version} (level {installed.controls_level})"
        )
    if not reasons:
        return False
    if allow_weaker:
        findings.append(
            Finding(
                "ORQ-W095",
                "Downgrade allowed with --allow-weaker: " + "; ".join(reasons) + ". Lowering the "
                "workflow needs two approvals when it is merged.",
                Severity.WARNING,
            )
        )
        return False
    findings.append(
        Finding(
            "ORQ-E120",
            "Refused, this is a downgrade: " + "; ".join(reasons) + ". Use --allow-weaker only "
            "with two approvals.",
            Severity.ERROR,
        )
    )
    return True


def _tamper_notes(plan: ChangePlan) -> list[Finding]:
    return [
        Finding(
            "ORQ-W096",
            f"{item.path} is protected and was changed. The upgrade restores it.",
            Severity.WARNING,
            str(item.path),
        )
        for item in plan.items
        if item.state.value == "tampered"
    ]


def _released_record(services: Services, inst: Installation) -> bytes | None:
    """The record of released files is kept as it is: upgrade never rewrites it."""
    if not inst.released:
        return None
    return services.project.read_bytes(RELEASED_PATH)


def _prompts_dir(inst: Installation) -> str:
    for source in inst.profile.standards_sources:
        if source.kind == "prompts-dir" and source.path:
            return source.path
    return ".prompts"


def _approved(services: Services, options: UpgradeOptions, plan: ChangePlan) -> bool:
    if options.assume_yes:
        return True
    if not services.prompter.interactive:
        return False
    try:
        return services.prompter.confirm(f"Apply {len(plan.writes)} file change(s)?", default=False)
    except NoAnswerAvailable:
        return False
