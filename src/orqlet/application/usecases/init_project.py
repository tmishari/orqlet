"""`orqlet init`: existing, new and empty projects (proposal sections 9.1, 9.2, 12.8 and 13.7).

Read, ask, plan, show, apply. The use case reads the directory, drafts the profile from
evidence, asks what evidence cannot say, renders the files for the enabled clients, builds a
change plan and applies it only after approval. Nothing is guessed: an unknown is a question.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import (
    ProjectProfile,
    PullRequests,
    PullRequestTemplate,
    StandardsSourceRef,
    Technology,
)
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.filesystem import FileKind, FileSystemError
from orqlet.application.ports.prompter import NoAnswerAvailable, Question
from orqlet.application.usecases.apply_plan import apply_plan
from orqlet.application.usecases.discover import discover_technologies
from orqlet.application.usecases.draft_profile import (
    ALL_CLIENTS,
    Client,
    OpenQuestion,
    draft_profile,
    open_questions,
)
from orqlet.application.usecases.init_files import (
    choose_pr_targets,
    contract_bytes,
    discover_pr_templates,
)
from orqlet.application.usecases.init_questions import (
    NEW_PROJECT_ORIGINS,
    apply_answers,
    approve,
    collect_answers,
    questions_for,
)
from orqlet.application.usecases.init_state import InitRefused, RootState, detect_root_state
from orqlet.application.usecases.render_all import (
    LOCK_PATH,
    PROFILE_PATH,
    compose,
    environment_findings,
    ignored_findings,
    plan_changes,
    resolve_for,
)
from orqlet.application.usecases.resources_source import load_resources, resources_path
from orqlet.application.usecases.services import Services, Stores
from orqlet.application.usecases.standards_for import Resolution
from orqlet.domain.blocks import BlockError
from orqlet.domain.changeplan import ChangePlan, PlanError
from orqlet.domain.findings import Finding, Severity

InitServices = Services
InitStatus = Literal["applied", "previewed", "already-initialised", "needs-input", "refused"]


@dataclass(frozen=True, slots=True)
class InitOptions:
    clients: tuple[Client, ...] = ALL_CLIENTS
    answers: Mapping[str, str] = field(default_factory=dict)
    assume_yes: bool = False
    dry_run: bool = False
    git_init: bool = False
    new_project: bool = False
    project_name: str | None = None
    prompts_dir: str = ".prompts"
    packs_path: str | None = None  # where the packs live, if inside the repository
    packs_outside_repository: bool = False


@dataclass(frozen=True, slots=True)
class InitResult:
    status: InitStatus
    findings: tuple[Finding, ...] = ()
    plan: ChangePlan | None = None
    profile: ProjectProfile | None = None
    open_questions: tuple[OpenQuestion, ...] = ()
    change_id: str | None = None
    git_initialised: bool = False
    needs_git: bool = False


__all__ = ["InitOptions", "InitResult", "InitServices", "Stores", "init_project"]


def init_project(services: InitServices, options: InitOptions) -> InitResult:
    if services.project.kind(LOCK_PATH) is FileKind.FILE:
        message = "This project is already initialised. Use sync, doctor or upgrade."
        return InitResult(
            "already-initialised", findings=(Finding("ORQ-I010", message, Severity.INFO),)
        )
    try:
        return _run(services, options)
    except InitRefused as exc:
        return InitResult("refused", findings=(Finding(exc.code, str(exc), Severity.ERROR),))
    except (BlockError, FileSystemError, PlanError) as exc:
        return InitResult("refused", findings=(Finding("ORQ-E114", str(exc), Severity.ERROR),))


def _run(services: InitServices, options: InitOptions) -> InitResult:
    findings: list[Finding] = []
    discovery = discover_technologies(services.project, services.technology_scanners)
    findings += [Finding("ORQ-I051", note, Severity.INFO) for note in discovery.notes]
    root = detect_root_state(
        services.project,
        services.vcs,
        services.scanners,
        confirm_new_project=options.new_project,
        languages_found=bool(discovery.languages()),
    )
    resources, resources_bytes = _registry(services)
    profile = _load_existing_profile(services)
    if profile is None:
        profile = _draft_and_ask(services, options, root, findings, discovery.technologies)
    branch = profile.repository.target_branch.value
    if root.needs_git and options.git_init and branch is None:
        findings.append(
            Finding(
                "ORQ-E113",
                "Git setup needs a target branch. Answer repository.target_branch.",
                Severity.ERROR,
            )
        )
        return InitResult("needs-input", tuple(findings), profile=profile, needs_git=True)

    resolution = resolve_for(services, profile, prompts_dir=options.prompts_dir)
    targets, open_choice = _pr_targets(services, options)
    profile = _with_pr_template(profile, targets, resolution, findings, open_choice)
    profile = _with_sources(profile, options, resolution, findings)
    existing = (
        services.project.read_bytes(PROFILE_PATH)
        if services.project.kind(PROFILE_PATH) is FileKind.FILE
        else None
    )
    composition = compose(
        services,
        profile,
        resolution,
        resources,
        clients=options.clients,
        prompts_dir=options.prompts_dir,
        pr_targets=targets,
        profile_bytes=existing or contract_bytes(services.writer, profile),
        resources_bytes=resources_bytes,
    )
    findings += composition.findings
    findings += environment_findings(services, options.prompts_dir)

    plan = plan_changes(services, composition.desired, [])
    findings += ignored_findings(
        services, (w.path for w in plan.writes if w.kind != "delete" and not w.is_proposal)
    )
    findings += [
        Finding(
            "ORQ-W080",
            item.reason or f"{item.path} conflicts with what Orqlet would write",
            Severity.WARNING,
            str(item.path),
        )
        for item in plan.conflicts
    ]
    needs_git_blocked = root.needs_git and not options.git_init
    if needs_git_blocked:
        findings.append(
            Finding(
                "ORQ-E112",
                "This directory is not a Git repository. Orqlet needs one. Run init again with "
                "--git-init to create it; you choose the target branch.",
                Severity.ERROR,
            )
        )
    open_now = open_questions(profile)
    if options.dry_run or needs_git_blocked:
        return InitResult(
            "previewed", tuple(findings), plan, profile, open_now, needs_git=root.needs_git
        )
    if not _approved(services, options, plan):
        status: InitStatus = "previewed" if services.prompter.interactive else "needs-input"
        if status == "needs-input":
            findings.append(
                Finding(
                    "ORQ-E115",
                    "Nothing was applied: run again with --yes to approve the plan.",
                    Severity.ERROR,
                )
            )
        return InitResult(
            status, tuple(findings), plan, profile, open_now, needs_git=root.needs_git
        )

    git_done = False
    if root.needs_git and branch is not None:
        services.vcs.init_repository(branch)
        git_done = True
    stores = services.stores(profile.project.uuid)
    change_id = services.ids.new_id()
    apply_plan(
        services.project,
        stores.journal,
        stores.backups,
        plan,
        lock=stores.lock,
        change_id=change_id,
        command="init",
        clock=services.clock,
    )
    return InitResult(
        "applied", tuple(findings), plan, profile, open_now, change_id, git_done, root.needs_git
    )


# --- registry ----------------------------------------------------------------------------------
def _registry(services: InitServices) -> tuple[Resources, bytes]:
    """The registry that is on disk, or an empty one; an invalid one stops `init` (ADR-002 6).

    A run that follows an interruption reads what is on disk, as it does for the profile, so a
    registry the team wrote is kept as it is and an invalid one is never replaced by an empty one.
    """
    path = resources_path()
    resources, problems = load_resources(services.project, services.loader, str(path))
    if resources is None:
        detail = "; ".join(problem.message for problem in problems)
        raise InitRefused(
            "ORQ-E503",
            f"The registry {path} cannot be used: {detail}. Nothing was changed. Fix the file or "
            "restore it from Git, then run `orqlet init` again.",
        )
    if services.project.kind(path) is FileKind.FILE:
        return resources, services.project.read_bytes(path)
    return resources, contract_bytes(services.writer, resources)


# --- profile -----------------------------------------------------------------------------------
def _load_existing_profile(services: InitServices) -> ProjectProfile | None:
    """A profile left by an interrupted run is reused, so a rerun converges on the same files."""
    if services.project.kind(PROFILE_PATH) is not FileKind.FILE:
        return None
    return load_contract(
        services.loader,
        ProjectProfile,
        services.project.read_bytes(PROFILE_PATH),
        source=str(PROFILE_PATH),
    )


def _draft_and_ask(
    services: InitServices,
    options: InitOptions,
    root: RootState,
    findings: list[Finding],
    technologies: Sequence[Technology],
) -> ProjectProfile:
    name = options.project_name or services.project_label
    draft = draft_profile(
        services.project,
        services.scanners,
        project_id=services.ids.new_id(),
        name=name,
        origin=root.origin,
        orqlet_version=services.orqlet_version,
        clients=options.clients,
        technologies=technologies,
    )
    profile = draft.profile
    findings += [Finding("ORQ-I050", note, Severity.INFO) for note in draft.notes]
    asks_stack = root.has_code or root.origin in NEW_PROJECT_ORIGINS
    questions = questions_for(profile, asks_stack=asks_stack)
    answers = collect_answers(questions, options.answers, services.prompter)
    notes: list[str] = []
    profile = apply_answers(profile, answers, notes)
    findings += [Finding("ORQ-W060", note, Severity.WARNING) for note in notes]
    reviewer = _reviewer(services, options)
    if reviewer:
        profile = approve(profile, reviewer, services.clock.now())
    return profile


def _reviewer(services: InitServices, options: InitOptions) -> str:
    supplied = options.answers.get("reviewer", "").strip()
    if supplied or not services.prompter.interactive:
        return supplied
    question = Question(
        "reviewer",
        "Your name, to record that you approved this profile (leave empty to keep it a draft)",
    )
    try:
        return services.prompter.ask(question).strip()
    except NoAnswerAvailable:
        return ""


def _with_sources(
    profile: ProjectProfile, options: InitOptions, resolution: Resolution, findings: list[Finding]
) -> ProjectProfile:
    sources = list(profile.standards_sources)
    if not any(source.kind == "prompts-dir" for source in sources):
        sources.append(
            StandardsSourceRef(kind="prompts-dir", path=options.prompts_dir, scaffold="seeded")
        )
    if resolution.used and not any(source.kind == "standards-pack" for source in sources):
        if options.packs_path is not None:
            sources.append(StandardsSourceRef(kind="standards-pack", path=options.packs_path))
        elif options.packs_outside_repository:
            findings.append(
                Finding(
                    "ORQ-W070",
                    "The standards packs are outside the repository, so their location is not "
                    "recorded. Pass --packs-dir again when you upgrade.",
                    Severity.WARNING,
                )
            )
    return profile.model_copy(update={"standards_sources": tuple(sources)})


# --- pull-request template --------------------------------------------------------------------
def _pr_targets(services: InitServices, options: InitOptions) -> tuple[tuple[str, ...], bool]:
    candidates, has_folder = discover_pr_templates(services.project)
    return choose_pr_targets(candidates, has_folder, options.answers, services.prompter)


def _with_pr_template(
    profile: ProjectProfile,
    targets: tuple[str, ...],
    resolution: Resolution,
    findings: list[Finding],
    open_choice: bool,
) -> ProjectProfile:
    if open_choice:
        findings.append(
            Finding(
                "ORQ-W050",
                "Several pull-request templates exist. Choose which ones receive the Orqlet blocks "
                "with --answer repository.pull_requests.template.targets=<path[,path]>.",
                Severity.WARNING,
            )
        )
        return profile
    has_team = any(a.kind == "pr-template" for p in resolution.loaded for a in p.manifest.assets)
    template = PullRequestTemplate(
        targets=targets,
        source_id=None,
        status="provisioned" if has_team else "team-template-unknown",
    )
    pull_requests = PullRequests(
        template=template,
        reviewers=profile.repository.pull_requests.reviewers,
        merge_strategy=profile.repository.pull_requests.merge_strategy,
    )
    repository = profile.repository.model_copy(update={"pull_requests": pull_requests})
    return profile.model_copy(update={"repository": repository})


# --- plan, findings, approval --------------------------------------------------------------------
def _approved(services: InitServices, options: InitOptions, plan: ChangePlan) -> bool:
    if options.assume_yes:
        return True
    if not services.prompter.interactive:
        return False
    try:
        return services.prompter.confirm(f"Apply {len(plan.writes)} file change(s)?", default=False)
    except NoAnswerAvailable:
        return False
