"""Computing the review-input binding from Git objects (proposal 6.14.1).

Every component is computed by Orqlet from the tree under review and from baseline files, never
from a value that a record or a pull request supplies. Offline, "the tree under review" is the
staged snapshot (what a commit would hold) or a commit, and "the baseline" is that same tree: the
host evidence that would take the design and plan from the protected branch is S11's.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from orqlet.application.contracts.common import Contract
from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.knowledge_config import KnowledgeConfig
from orqlet.application.contracts.knowledge_impact import KnowledgeImpact
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.contracts.review_result import ReviewResult
from orqlet.application.contracts.standards_lock import StandardsLock
from orqlet.application.contracts.test_record import TesterRecord
from orqlet.application.contracts.workflow_package import WorkflowLock
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.vcs import TreeChange
from orqlet.application.usecases.render_all import (
    KNOWLEDGE_PATH,
    PROFILE_PATH,
    STANDARDS_LOCK_PATH,
    WORKFLOW_LOCK_PATH,
)
from orqlet.application.usecases.validation import (
    TASK_ROOT,
    Collector,
    ValidateServices,
    content_hash,
    read_file,
)
from orqlet.domain.binding import (
    ChangedFile,
    Component,
    RecordKind,
    changed_files_digest,
    partition_changes,
)
from orqlet.domain.digest import digest_of, sha256_hex
from orqlet.domain.evidence_artifacts import (
    MAX_EVIDENCE_BYTES,
    EvidencePath,
    is_excluded,
    parse_evidence_path,
)
from orqlet.domain.globs import glob_match

DOCUMENTATION_EXTENSIONS = (".md", ".rst", ".txt", ".adoc")
FORBIDDEN_KNOWLEDGE_PREFIXES = (
    ".claude/",
    ".cursor/",
    ".agents/",
    ".codex/",
    ".orqlet/",
    ".github/",
    "src/orqlet/workflow/",
)
FORBIDDEN_KNOWLEDGE_FILES = frozenset({"AGENTS.md", "CLAUDE.md", ".mcp.json"})
AGENT_FILES = {
    "claude-code": ".claude/agents/{ref}.md",
    "cursor": ".cursor/agents/{ref}.md",
    "codex": ".codex/agents/{ref}.toml",
}


@dataclass(frozen=True, slots=True)
class Target:
    """The tree under review and the merge base it is compared with."""

    base: str  # a commit id
    tree: str  # a tree object id or a commit id
    label: str  # `staged`, `HEAD` or the start of a commit id


@dataclass(slots=True)
class Located:
    target: Target | None
    problems: list[str] = field(default_factory=list)


def locate(services: ValidateServices, base: str | None, head: str | None) -> Located:
    """Pick the tree under review and its merge base, or say why that cannot be done."""
    vcs = services.vcs
    head_commit = vcs.head_commit()
    if head_commit is None:
        return Located(None, ["the repository has no commit yet, so there is no merge base"])
    chosen = head or ("staged" if vcs.has_staged_changes() else "HEAD")
    if chosen == "staged":
        tree, label = vcs.staged_tree(), "staged"
    elif chosen == "HEAD":
        tree, label = head_commit, "HEAD"
    else:
        tree, label = chosen, chosen[:12]
    found = _merge_base(services, base, head_commit)
    if isinstance(found, str):
        return Located(Target(found, tree, label))
    return Located(None, list(found))


def _merge_base(
    services: ValidateServices, base: str | None, head_commit: str
) -> str | tuple[str, ...]:
    """The single merge base as an id, or a tuple holding the reason there is not exactly one."""
    vcs = services.vcs
    if base is not None:
        other = base if len(base) in {40, 64} or base == "HEAD" else vcs.resolve(base)
        if other is None or not vcs.has_revision(other):
            return (f"the base {base!r} does not name a commit in this repository",)
    else:
        other = _target_branch_commit(services)
        if other is None:
            return (
                "the target branch is not known to this clone; name the base with --base "
                "(a branch name or a full commit id)",
            )
    bases = vcs.merge_bases(head_commit, other)
    if len(bases) == 1:
        return bases[0]
    if not bases:
        return ("the commits share no history, so there is no merge base",)
    return ("the history has several merge bases (a criss-cross), so the binding is NOT_RUN",)


def _target_branch_commit(services: ValidateServices) -> str | None:
    data = read_file(services, str(PROFILE_PATH))
    if data is None:
        return None
    try:
        profile = load_contract(services.loader, ProjectProfile, data, source=str(PROFILE_PATH))
    except DocumentError:
        return None
    target = profile.repository.target_branch
    if target.value is None:
        return None
    for name in (f"{target.remote}/{target.value}", target.value):
        found = services.vcs.resolve(name)
        if found is not None:
            return found
    return None


# --- the knowledge scope and the evidence artifacts --------------
@dataclass(frozen=True, slots=True)
class KnowledgeScope:
    """A path is in scope when the plan asks for it AND the baseline configuration allows it."""

    requested: tuple[str, ...] = ()
    allowed: tuple[str, ...] = ()

    def contains(self, path: str) -> bool:
        if path in FORBIDDEN_KNOWLEDGE_FILES or path.startswith(FORBIDDEN_KNOWLEDGE_PREFIXES):
            return False
        if not path.lower().endswith(DOCUMENTATION_EXTENSIONS):
            return False
        return any(glob_match(g, path) for g in self.requested) and any(
            glob_match(g, path) for g in self.allowed
        )


def read_knowledge_config(
    services: ValidateServices, tree: str | None = None
) -> KnowledgeConfig | None:
    data = (
        services.vcs.read_at(tree, str(KNOWLEDGE_PATH))
        if tree is not None
        else read_file(services, str(KNOWLEDGE_PATH))
    )
    if data is None:
        return None
    try:
        return load_contract(services.loader, KnowledgeConfig, data, source=str(KNOWLEDGE_PATH))
    except DocumentError:
        return None


def knowledge_scope(
    services: ValidateServices, tree: str, plan: ImplementationPlan | None
) -> KnowledgeScope:
    config = read_knowledge_config(services, tree)
    allowed = tuple(g for scope in (config.write_scope if config else ()) for g in scope.globs)
    return KnowledgeScope(tuple(plan.knowledge_scope) if plan else (), allowed)


def evidence_file_ok(
    services: ValidateServices, tree: str, change: TreeChange, tree_paths: frozenset[str]
) -> bool:
    """The three conditions that take a record out of its own binding (proposal 6.14.1)."""
    parsed = parse_evidence_path(change.path)
    if parsed is None or change.status == "deleted":
        return False
    data = services.vcs.read_at(tree, change.path)
    if data is None or len(data) > MAX_EVIDENCE_BYTES:
        return False
    try:
        record = _load_record(services, parsed.kind, data, change.path)
    except DocumentError:
        return False
    return is_excluded(
        change.path,
        mode=change.new_mode,
        task_exists=any(p.startswith(f"{TASK_ROOT}/{parsed.task}/") for p in tree_paths),
        schema_valid=True,
        content_matches_path=_identity_matches(record, parsed),
    )


def _load_record(
    services: ValidateServices, kind: RecordKind, data: bytes, path: str
) -> ReviewResult | TesterRecord | KnowledgeImpact:
    if kind is RecordKind.REVIEW:
        return load_contract(services.loader, ReviewResult, data, source=path)
    if kind is RecordKind.TEST:
        return load_contract(services.loader, TesterRecord, data, source=path)
    return load_contract(services.loader, KnowledgeImpact, data, source=path)


def _identity_matches(
    record: ReviewResult | TesterRecord | KnowledgeImpact, path: EvidencePath
) -> bool:
    if record.task != path.task or record.phase != path.phase:
        return False
    if isinstance(record, ReviewResult):
        return record.role == path.role and record.round == path.round
    return True


@dataclass(frozen=True, slots=True)
class ChangeSet:
    code_tests: tuple[ChangedFile, ...]
    knowledge: tuple[ChangedFile, ...]
    evidence: tuple[str, ...]


def change_set(services: ValidateServices, target: Target, scope: KnowledgeScope) -> ChangeSet:
    """The paths that differ from the merge base, split the way the binding needs them."""
    vcs = services.vcs
    changes = vcs.diff_tree(target.base, target.tree)
    tree_paths = frozenset(file.path for file in vcs.tree_at(target.tree))
    evidence = {
        change.path
        for change in changes
        if evidence_file_ok(services, target.tree, change, tree_paths)
    }
    contents = services.vcs.read_many_at(
        target.tree,
        [c.path for c in changes if c.status != "deleted" and c.new_mode != "160000"],
    )
    files = [_changed_file(change, contents) for change in changes]
    code, knowledge = partition_changes(
        files, is_evidence=evidence.__contains__, in_knowledge_scope=scope.contains
    )
    return ChangeSet(tuple(code), tuple(knowledge), tuple(sorted(evidence)))


def _changed_file(change: TreeChange, contents: dict[str, bytes | None]) -> ChangedFile:
    if change.status == "deleted":
        return ChangedFile(change.path, change.status, change.new_mode, "0" * 64)
    if change.new_mode == "160000":  # a gitlink has no blob: its commit id is the content
        return ChangedFile(change.path, change.status, change.new_mode, change.new_oid)
    return ChangedFile(
        change.path, change.status, change.new_mode, sha256_hex(contents.get(change.path) or b"")
    )


# --- the components ----------------------------------------------
@dataclass(frozen=True, slots=True)
class BindingRequest:
    task: str
    phase: str
    target: Target
    changes: ChangeSet
    role: str | None = None  # `architecture-reviewer` or `security-reviewer`, for a review
    agent_ref: str | None = None
    agent_client: str | None = None
    candidates_digest: str | None = None


def compute_components(
    services: ValidateServices, request: BindingRequest, out: Collector
) -> dict[Component, str]:
    """Every component the request can name.

    A component that cannot be computed is skipped with a reason, so a record that covers it is
    `NOT_RUN` and is never silently bound.
    """
    tree = request.target.tree
    folder = f"{TASK_ROOT}/{request.task}"
    components: dict[Component, str] = {
        Component.CODE_TESTS: changed_files_digest(request.changes.code_tests),
        Component.KNOWLEDGE: changed_files_digest(request.changes.knowledge),
    }
    design = _design_digest(services, tree, f"{folder}/design/manifest.yaml", out)
    if design is not None:
        components[Component.DESIGN] = design
    plan = services.vcs.read_at(tree, f"{folder}/plan.yaml")
    if plan is None:
        out.skip(f"{folder}/plan.yaml is not in the tree under review")
    else:
        components[Component.PLAN] = content_hash(plan)
    standards = _standards_digest(services, tree, out)
    if standards is not None:
        components[Component.STANDARDS] = standards
    if request.role is not None and request.agent_ref and request.agent_client:
        definition = _definition_digest(services, request, out)
        if definition is not None:
            components[Component.REVIEWER_DEFINITION] = definition
    components[Component.EVIDENCE_INPUTS] = _evidence_inputs_digest(
        services, tree, folder, request.phase
    )
    if request.candidates_digest is not None:
        components[Component.CANDIDATES] = request.candidates_digest
    return components


def _design_digest(
    services: ValidateServices, tree: str, manifest_path: str, out: Collector
) -> str | None:
    data = services.vcs.read_at(tree, manifest_path)
    if data is None:
        out.skip(f"{manifest_path} is not in the tree under review")
        return None
    try:
        design = load_contract(services.loader, DesignSet, data, source=manifest_path)
    except DocumentError as error:
        out.error("ORQ-E325", str(error), manifest_path)
        return None
    listed = sorted(
        {a.path for a in design.artifacts if a.path is not None}
        | {design.as_is_ref.rpartition("#")[0]}
    )
    files = []
    for path in listed:
        body = services.vcs.read_at(tree, path)
        files.append([path, "missing" if body is None else content_hash(body)])
    return digest_of({"manifest": content_hash(data), "files": files})


def _standards_digest(services: ValidateServices, tree: str, out: Collector) -> str | None:
    lock = services.vcs.read_at(tree, str(STANDARDS_LOCK_PATH))
    workflow = services.vcs.read_at(tree, str(WORKFLOW_LOCK_PATH))
    if lock is None or workflow is None:
        out.skip("the standards lock or the workflow lock is not in the tree under review")
        return None
    try:
        rules = load_contract(
            services.loader, StandardsLock, lock, source=str(STANDARDS_LOCK_PATH)
        ).applicable_rules_hash
        digest = load_contract(
            services.loader, WorkflowLock, workflow, source=str(WORKFLOW_LOCK_PATH)
        ).workflow_digest
    except DocumentError as error:
        out.error("ORQ-E325", str(error))
        return None
    return digest_of({"applicable_rules_hash": rules, "workflow_digest": digest})


def _definition_digest(
    services: ValidateServices, request: BindingRequest, out: Collector
) -> str | None:
    pattern = AGENT_FILES.get(request.agent_client or "")
    if pattern is None:
        out.error("ORQ-E400", f"{request.agent_client!r} is not a client with agent definitions")
        return None
    path = pattern.format(ref=request.agent_ref)
    definition = services.vcs.read_at(request.target.tree, path)
    if definition is None:
        out.error("ORQ-E400", f"the agent definition {path} is not in the tree under review", path)
        return None
    role_source = f"roles/{request.agent_ref}.md"
    contract = (
        content_hash(services.workflow.read_text(role_source).encode("utf-8"))
        if role_source in services.workflow.paths()
        else "not-a-workflow-role"
    )
    return digest_of({"role_contract": contract, "definition": content_hash(definition)})


def _evidence_inputs_digest(services: ValidateServices, tree: str, folder: str, phase: str) -> str:
    found = []
    for path in (f"{folder}/tests/{phase}.yaml", f"{folder}/knowledge/{phase}.yaml"):
        data = services.vcs.read_at(tree, path)
        if data is not None:
            found.append([path, content_hash(data)])
    return digest_of(found)


def read_contract_at[T: Contract](
    services: ValidateServices,
    tree: str,
    path: str,
    model: type[T],
    out: Collector,
    *,
    missing: str | None = None,
) -> T | None:
    """A contract read from the tree under review. A missing file is a skipped check."""
    data = services.vcs.read_at(tree, path)
    if data is None:
        out.skip(missing or f"{path} is not in the tree under review")
        return None
    try:
        return load_contract(services.loader, model, data, source=path)
    except DocumentError as error:
        out.error("ORQ-E325", str(error), path)
        return None


def components_as_data(components: Mapping[Component, str]) -> dict[str, str]:
    return {component.value: digest for component, digest in components.items()}
