"""Everything that turns a profile and the packaged workflow into the files of an installation.

`init` and `upgrade` both call `compose`, so they can never disagree about what a project
should contain.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from orqlet.application.contracts.knowledge_config import KnowledgeConfig
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.contracts.role_bindings import Binding, MinimumCapability, RoleBindings
from orqlet.application.contracts.standards_lock import LockedPack, StandardsLock
from orqlet.application.contracts.versions_file import CliVersions, Versions, WorkflowVersions
from orqlet.application.contracts.workflow_package import WorkflowLock
from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.application.ports.instruction_adapter import CapabilityLimit, RenderedFile
from orqlet.application.ports.renderers import BlockSpec, TeamTemplate
from orqlet.application.ports.standards import LoadedPack
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.init_files import (
    contract_bytes,
    lock_from_recorded,
    merge_rendered,
    to_desired,
)
from orqlet.application.usecases.init_state import InitRefused
from orqlet.application.usecases.render_request import build_render_request
from orqlet.application.usecases.services import Services
from orqlet.application.usecases.standards_for import (
    Resolution,
    Stack,
    own_layers,
    prompts_dir_of,
    resolve_standards,
)
from orqlet.domain.blocks import render_block
from orqlet.domain.changeplan import (
    ChangePlan,
    Desired,
    PlannedWrite,
    Recorded,
    build_plan,
    proposal_path,
)
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resolver import rules_hash

PROFILE_PATH = CanonicalPath.parse(".orqlet/project-profile.yaml")
LOCK_PATH = CanonicalPath.parse(".orqlet/generated.lock.yaml")
VERSIONS_PATH = CanonicalPath.parse(".orqlet/versions.yaml")
BINDINGS_PATH = CanonicalPath.parse(".orqlet/role-bindings.yaml")
STANDARDS_LOCK_PATH = CanonicalPath.parse(".orqlet/standards.lock.yaml")
WORKFLOW_LOCK_PATH = CanonicalPath.parse(".orqlet/workflow.lock")
RELEASED_PATH = CanonicalPath.parse(".orqlet/released.yaml")
KNOWLEDGE_PATH = CanonicalPath.parse(".orqlet/knowledge.yaml")
# The reviewers Orqlet generates. A team approves its own alternatives in role-bindings.yaml.
REVIEW_AGENTS: tuple[tuple[Literal["architecture-reviewer", "security-reviewer"], str], ...] = (
    ("architecture-reviewer", "orqlet-arch-reviewer"),
    ("security-reviewer", "orqlet-security-reviewer"),
)


@dataclass(frozen=True, slots=True)
class Composition:
    desired: list[Desired]
    findings: list[Finding]
    resolution: Resolution


def stack_of_profile(profile: ProjectProfile) -> Stack:
    """What the profile says the project is made of, for matching standards packs."""
    languages = {t.name.lower() for t in profile.technologies if t.kind == "language"}
    if profile.stack.support == "supported":
        languages.add("python")
    names = {t.name.lower() for t in profile.technologies}
    names |= {f.name.lower() for f in profile.facts.frameworks}
    return Stack(frozenset(languages), profile.project.kind, frozenset(names))


def resolve_for(
    services: Services, profile: ProjectProfile, *, prompts_dir: str | None = None
) -> Resolution:
    """The packs and rules that apply to what the profile says the project is."""
    stack = stack_of_profile(profile)
    folder = prompts_dir if prompts_dir is not None else prompts_dir_of(profile)
    layers = own_layers(services.project, services.loader, folder)
    return resolve_standards(services.packs, layers, stack)


def compose(
    services: Services,
    profile: ProjectProfile,
    resolution: Resolution,
    *,
    clients: Sequence[str],
    prompts_dir: str,
    pr_targets: tuple[str, ...],
    profile_bytes: bytes,
    orqlet_owned: frozenset[str] = frozenset(),
    released: frozenset[str] = frozenset(),
    released_record: bytes | None = None,
) -> Composition:
    """Every file the project should hold, as `Desired`, with the findings the render raised."""
    del profile  # the profile's effect is already in `resolution` and `profile_bytes`
    findings: list[Finding] = []
    request = build_render_request(
        services.workflow, services.loader, tuple(resolution.rules.values())
    )
    results = [services.adapters[client].render(request) for client in clients]
    findings += limit_findings(limit for result in results for limit in result.limits)
    files = claude_entry_points(
        merge_rendered([f for r in results for f in r.files]), services, orqlet_owned
    )
    desired = [to_desired(file) for file in files]
    team = team_template(resolution.loaded, findings)
    desired += pr_template_files(services, pr_targets, team)
    desired += seed_files(services, prompts_dir, findings)
    desired += data_files(services, profile_bytes, resolution)
    desired = [item for item in desired if str(item.path) not in released]
    if released_record is not None:
        desired.append(
            Desired(RELEASED_PATH, OwnerMode.ORQLET, FileClass.GENERATED, released_record)
        )
    return Composition(desired, findings, resolution)


def team_template(loaded: Sequence[LoadedPack], findings: list[Finding]) -> TeamTemplate | None:
    found: list[TeamTemplate] = []
    for pack in loaded:
        files = dict(pack.asset_files)
        for asset in pack.manifest.assets:
            if asset.kind != "pr-template":
                continue
            body = files[asset.path].decode("utf-8").replace("\r\n", "\n").rstrip("\n")
            found.append(
                TeamTemplate(asset.id, asset.version, body, sha256_hex(body.encode("utf-8")))
            )
    if len(found) > 1:
        findings.append(
            Finding(
                "ORQ-W051",
                "More than one team pull-request template was supplied. None was provisioned.",
                Severity.WARNING,
            )
        )
        return None
    return found[0] if found else None


def pr_template_files(
    services: Services, targets: tuple[str, ...], team: TeamTemplate | None
) -> list[Desired]:
    if not targets:
        return []
    specs: list[tuple[BlockSpec, FileClass]] = []
    if team is not None:
        specs.append((services.renderers.team_block(team), FileClass.OPTIONAL))
    specs.append((services.renderers.workflow_block(services.workflow), FileClass.GENERATED))
    desired = []
    for target in targets:
        for spec, file_class in specs:
            desired.append(
                Desired(
                    path=CanonicalPath.parse(target),
                    owner=OwnerMode.SHARED_BLOCK,
                    file_class=file_class,
                    content=render_block(spec.name, spec.info, spec.body).encode("utf-8"),
                    block_name=spec.name,
                    insert_after_heading=True,
                    inputs=(
                        (spec.name, spec.info.split("#")[0], sha256_hex(spec.body.encode("utf-8"))),
                    ),
                )
            )
    return desired


def seed_files(services: Services, prompts_dir: str, findings: list[Finding]) -> list[Desired]:
    base = CanonicalPath.parse(prompts_dir)
    if services.project.kind(base) is FileKind.DIRECTORY:
        findings.append(
            Finding(
                "ORQ-I031",
                f"{base} already exists. Only the seed files that are missing are added.",
                Severity.INFO,
            )
        )
    return [
        to_desired(file)
        for file in services.renderers.seed_files(services.workflow, base=prompts_dir)
    ]


def data_files(services: Services, profile_bytes: bytes, resolution: Resolution) -> list[Desired]:
    release = services.workflow.release
    version = str(release.version)
    versions = Versions(
        schema_id="orqlet.versions/v1",
        policy_role="enforcement-baseline",
        cli=CliVersions(pinned=services.orqlet_version, accepted=(services.orqlet_version,)),
        workflow=WorkflowVersions(
            version=version,
            digest=release.digest,
            floor=version,
            controls_level_min=release.controls_level,
        ),
    )
    bindings = RoleBindings(
        schema_id="orqlet.role-bindings/v1",
        policy_role="enforcement-baseline",
        bindings=tuple(
            Binding(
                role=role,
                id=agent,
                clients=("claude-code", "codex", "cursor"),
                minimum_capability=MinimumCapability(
                    context="fresh", input="review-packet", write_access="none-or-recorded-limit"
                ),
                independence_capability="I1",
            )
            for role, agent in REVIEW_AGENTS
        ),
    )
    # Empty on purpose: a team opts in by naming where its knowledge lives and where drafts may go.
    knowledge = KnowledgeConfig(schema_id="orqlet.knowledge/v2")
    pins = StandardsLock(
        schema_id="orqlet.standards-lock/v1",
        packs=tuple(
            LockedPack(
                id=use.id,
                version=use.version,
                sha256=use.sha256,
                source=source_of(use.id, resolution),
            )
            for use in resolution.used
        ),
        applicable_rules_hash=rules_hash(list(resolution.rules.values())),
    )
    workflow_lock = WorkflowLock(
        schema_id="orqlet.workflow-lock/v1",
        workflow_version=version,
        workflow_digest=release.digest,
        controls_level=release.controls_level,
    )
    writer = services.writer

    def seeded(path: CanonicalPath, content: bytes) -> Desired:
        return Desired(path, OwnerMode.SEEDED, None, content)

    return [
        seeded(PROFILE_PATH, profile_bytes),
        seeded(VERSIONS_PATH, contract_bytes(writer, versions)),
        seeded(BINDINGS_PATH, contract_bytes(writer, bindings)),
        seeded(KNOWLEDGE_PATH, contract_bytes(writer, knowledge)),
        Desired(
            STANDARDS_LOCK_PATH,
            OwnerMode.ORQLET,
            FileClass.GENERATED,
            contract_bytes(writer, pins),
        ),
        Desired(
            WORKFLOW_LOCK_PATH,
            OwnerMode.ORQLET,
            FileClass.PROTECTED,
            contract_bytes(writer, workflow_lock),
        ),
    ]


def source_of(pack_id: str, resolution: Resolution) -> str:
    return next(pack.source for pack in resolution.loaded if pack.manifest.id == pack_id)


def claude_entry_points(
    files: list[RenderedFile], services: Services, orqlet_owned: frozenset[str]
) -> list[RenderedFile]:
    """A `CLAUDE.md` the project already owns gets an import block; otherwise the bridge stays.

    `orqlet_owned` lists paths the manifest records as written by Orqlet (the bridge of an
    earlier run), which are never mistaken for the project's own file.
    """
    bridge = next((f for f in files if str(f.path) == ".claude/CLAUDE.md"), None)
    if bridge is None:
        return files
    owned = []
    for name, import_path in (("CLAUDE.md", "@AGENTS.md"), (".claude/CLAUDE.md", "@../AGENTS.md")):
        path = CanonicalPath.parse(name)
        if services.project.kind(path) is not FileKind.FILE or name in orqlet_owned:
            continue
        if name == ".claude/CLAUDE.md" and services.project.read_bytes(path) == bridge.content:
            continue  # the bridge from an interrupted run: it is ours
        text = render_block("claude-import", "", import_path)
        owned.append(
            RenderedFile(
                path=path,
                content=text.encode("utf-8"),
                owner=OwnerMode.SHARED_BLOCK,
                file_class=FileClass.PROTECTED,
                inputs=(("claude-import", import_path, sha256_hex(text.encode("utf-8"))),),
                block=(text.split("\n")[0], text.rstrip("\n").split("\n")[-1]),
            )
        )
    if not owned:
        return files
    return [f for f in files if f is not bridge] + owned


def limit_findings(limits: Iterable[CapabilityLimit]) -> list[Finding]:
    seen: dict[tuple[str, str], Finding] = {}
    for limit in limits:
        seen.setdefault(
            (limit.code, limit.message), Finding(limit.code, limit.message, Severity.INFO)
        )
    return list(seen.values())


_CODEOWNERS = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")


def plan_changes(
    services: Services, desired: list[Desired], recorded: Sequence[Recorded]
) -> ChangePlan:
    """Compare what is wanted with what is on disk and with what Orqlet recorded last time."""
    project = services.project
    wanted_paths = {item.path for item in desired}
    wanted_paths |= {proposal_path(item.path, item.block_name) for item in desired}
    wanted_paths |= {entry.path for entry in recorded}
    wanted_paths.add(LOCK_PATH)  # the manifest lists everything but itself
    current: dict[CanonicalPath, bytes] = {}
    for path in sorted(wanted_paths, key=lambda p: p.sort_key()):
        kind = project.kind(path)
        if kind is None:
            continue
        if kind is not FileKind.FILE:
            raise InitRefused("ORQ-E114", f"{path} exists and is not a regular file.")
        current[path] = project.read_bytes(path)
    plan = build_plan(desired, current, recorded)
    standards = next((d for d in desired if d.path == STANDARDS_LOCK_PATH), None)
    lock = lock_from_recorded(
        plan.recorded_after,
        orqlet_version=services.orqlet_version,
        standards_lock=None if standards is None else sha256_hex(standards.content),
    )
    return plan.with_manifest(
        LOCK_PATH, contract_bytes(services.writer, lock), current.get(LOCK_PATH)
    )


def environment_findings(services: Services, prompts_dir: str) -> list[Finding]:
    """Things around the repository that are worth saying, none of which Orqlet changes."""
    found: list[Finding] = []
    if services.ancestors is not None:
        for path in services.ancestors.find():
            found.append(
                Finding(
                    "ORQ-I020",
                    f"{path} is above this repository. It is present and was not modified.",
                    Severity.INFO,
                )
            )
    if not codeowners_mentions(services.project, prompts_dir):
        found.append(
            Finding(
                "ORQ-I030",
                f"Add `/{prompts_dir.strip('/')}/ <owners>` to CODEOWNERS so that "
                "changes to the standards are reviewed by their owners.",
                Severity.INFO,
            )
        )
    return found


def codeowners_mentions(project: FileSystem, prompts_dir: str) -> bool:
    for name in _CODEOWNERS:
        path = CanonicalPath.parse(name)
        if project.kind(path) is FileKind.FILE and prompts_dir.strip("/") in project.read_bytes(
            path
        ).decode("utf-8", errors="replace"):
            return True
    return False


def ignored_findings(services: Services, paths: Iterable[CanonicalPath]) -> list[Finding]:
    """A warning for each file that Git ignores: it is written but never reaches the team.

    Teams often ignore whole agent folders (`.claude/*`), which silently drops the generated
    bridge and rules from every commit. Skipped outside a repository, where nothing is ignored yet.
    """
    if services.vcs.state() is RepoState.NOT_A_REPOSITORY:
        return []
    names = sorted({str(path) for path in paths})
    return [
        Finding(
            "ORQ-W097",
            f"{name} is ignored by Git, so it will not be committed or shared with your team. "
            f"Add an exception to .gitignore, for example `!{name}` (un-ignore its folder first "
            "if the folder itself is ignored).",
            Severity.WARNING,
            name,
        )
        for name in sorted(services.vcs.ignored(names))
    ]


def planned_write(
    services: Services, path: CanonicalPath, content: bytes, *, last: bool = False
) -> PlannedWrite:
    """The write that turns the file at `path` into `content`, with the hashes apply verifies."""
    exists = services.project.kind(path) is FileKind.FILE
    before = sha256_hex(services.project.read_bytes(path)) if exists else None
    return PlannedWrite(
        path=path,
        kind="update" if exists else "create",
        before_sha256=before,
        after_sha256=sha256_hex(content),
        content=content,
        last=last,
    )
