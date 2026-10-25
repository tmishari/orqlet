"""`orqlet validate plan`: the implementation plan on a projected tree (proposal 17.5).

The plan is reviewable evidence and a structural check. It makes invented paths visible; it does
not prove the plan is right, and listing paths does not remove a hallucinated design.
"""

from __future__ import annotations

import re
from collections import Counter

from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.plan import ImplementationPlan, Phase
from orqlet.application.contracts.question_ledger import QuestionLedger
from orqlet.application.usecases.design_scope import change_policy, change_scope
from orqlet.application.usecases.validate_ledger import LEDGER_FILE, blocking_questions
from orqlet.application.usecases.validation import (
    Collector,
    ValidateServices,
    ValidationResult,
    content_hash,
    read_artifact,
    read_file,
    split_reference,
    task_of,
)
from orqlet.domain.change_class import ChangeClass, trigger_class
from orqlet.domain.errors import InvalidPath
from orqlet.domain.globs import glob_match
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.plan_projection import (
    EntryMode,
    FileOperation,
    Op,
    PlanPhase,
    TreeEntry,
    check_plan,
    structural_changes,
)

REVIEW_ITEMS = frozenset({"architecture-reviewer", "security-reviewer", "tester"})
DOCUMENTATION_EXTENSIONS = (".md", ".rst", ".txt", ".adoc")
# A knowledge scope is only a request: nothing on the agent-configuration surface, a workflow or
# Orqlet file, or source and test code may sit inside it (proposal 17.13.6).
FORBIDDEN_SCOPE_PREFIXES = (
    ".claude/",
    ".cursor/",
    ".agents/",
    ".codex/",
    ".orqlet/",
    ".github/",
    "src/orqlet/workflow/",
)
FORBIDDEN_SCOPE_FILES = frozenset({"AGENTS.md", "CLAUDE.md", ".mcp.json"})
_IMPLEMENTS = re.compile(r"^(?P<change>EC-\d+)(?:@(?P<stage>S-\d+))?$")
_MODES = {"120000": EntryMode.SYMLINK, "160000": EntryMode.GITLINK}


def validate_plan(
    services: ValidateServices, raw_path: str, ledger: str | None = None
) -> ValidationResult:
    out = Collector()
    plan, _, _ = read_artifact(services, raw_path, ImplementationPlan, out)
    if plan is None:
        return out.result()
    task = task_of(raw_path)
    if task is not None and plan.header.task != task:
        out.error(
            "ORQ-E370",
            f"the header names task {plan.header.task} but the file sits in {task}",
            raw_path,
        )
    _check_ids(plan, out, raw_path)
    _check_criteria(plan, out, raw_path)
    if plan.amends is not None and not re.fullmatch(r"[0-9a-f]{64}", plan.amends):
        out.error("ORQ-E379", "`amends` must be the sha256 of the plan it revises", raw_path)
    phases = [_phase(p) for p in plan.phases]
    tree = _base_tree(services, plan, out)
    if tree is not None:
        for finding in check_plan(tree, phases):
            out.findings.append(finding)
        _check_knowledge_scope(plan, tree, out, raw_path)
    design = _check_design(services, plan, raw_path, out)
    _check_ledger(services, raw_path, ledger, out)
    data: dict[str, object] = {
        "phases": len(plan.phases),
        "operations": sum(len(p.file_operations) for p in plan.phases),
        "structural_changes": list(structural_changes(phases)),
        "design_class": None if design is None else design.change_class.effective,
    }
    return out.result(data)


def _phase(phase: Phase) -> PlanPhase:
    return PlanPhase(
        phase.id,
        phase.depends_on,
        tuple(FileOperation(Op(o.op), o.path, o.moved_from) for o in phase.file_operations),
    )


def _base_tree(
    services: ValidateServices, plan: ImplementationPlan, out: Collector
) -> list[TreeEntry] | None:
    revision = plan.base_revision
    if not services.vcs.has_revision(revision):
        out.skip(f"the base revision {revision[:12]} is not in this repository")
        return None
    return [
        TreeEntry(file.path, _MODES.get(file.mode, EntryMode.FILE))
        for file in services.vcs.tree_at(revision)
    ]


def _check_ids(plan: ImplementationPlan, out: Collector, path: str) -> None:
    for duplicate, count in sorted(Counter(p.id for p in plan.phases).items()):
        if count > 1:
            out.error("ORQ-E373", f"the phase id {duplicate} is used {count} times", path)
    for phase in plan.phases:
        ids = Counter(c.id for c in phase.acceptance_criteria)
        for duplicate, count in sorted(ids.items()):
            if count > 1:
                out.error(
                    "ORQ-E373", f"{phase.id}: the criterion {duplicate} is used {count} times", path
                )


def _check_criteria(plan: ImplementationPlan, out: Collector, path: str) -> None:
    for phase in plan.phases:
        if not phase.acceptance_criteria:
            out.error(
                "ORQ-E374",
                f"{phase.id} has no acceptance criterion; unknown behaviour is a question",
                path,
            )
        for criterion in phase.acceptance_criteria:
            mapped = (
                criterion.check_ref in phase.checks
                or criterion.check_ref in REVIEW_ITEMS
                or criterion.check_ref.startswith("review:")
            )
            if not mapped:
                out.error(
                    "ORQ-E375",
                    f"{phase.id}: {criterion.id} maps to {criterion.check_ref}, which is neither a "
                    "check of the phase nor a review item",
                    path,
                )


def _check_knowledge_scope(
    plan: ImplementationPlan, tree: list[TreeEntry], out: Collector, path: str
) -> None:
    for pattern in plan.knowledge_scope:
        literal = pattern.split("*", 1)[0]
        if literal.startswith(FORBIDDEN_SCOPE_PREFIXES) or pattern in FORBIDDEN_SCOPE_FILES:
            out.error(
                "ORQ-E386",
                f"knowledge_scope {pattern} reaches a path that is never knowledge",
                path,
            )
            continue
        for entry in tree:
            if not glob_match(pattern, entry.path):
                continue
            if (
                entry.path.startswith(FORBIDDEN_SCOPE_PREFIXES)
                or entry.path in FORBIDDEN_SCOPE_FILES
            ):
                out.error(
                    "ORQ-E386",
                    f"knowledge_scope {pattern} covers {entry.path}, which is never knowledge",
                    path,
                )
                break
            if not entry.path.lower().endswith(DOCUMENTATION_EXTENSIONS):
                out.error(
                    "ORQ-E386",
                    f"knowledge_scope {pattern} covers {entry.path}, which is not a "
                    "documentation file",
                    path,
                )
                break


def _check_design(
    services: ValidateServices, plan: ImplementationPlan, path: str, out: Collector
) -> DesignSet | None:
    parts = split_reference(plan.design_ref)
    if parts is None:
        out.error("ORQ-E371", "design_ref must be `<path>#<sha256>`", path)
        return None
    raw, digest = parts
    data = read_file(services, raw)
    if data is None:
        out.error("ORQ-E371", f"the design manifest {raw} does not exist", path)
        return None
    if content_hash(data) != digest:
        out.error("ORQ-E371", f"the design manifest {raw} changed after the plan cited it", path)
    design, _, _ = read_artifact(services, raw, DesignSet, out)
    if design is None:
        out.error(
            "ORQ-E372", f"the design manifest {raw} cannot be read, so it cannot be compared", path
        )
        return None
    _check_implements(plan, design, out, path)
    _check_class(plan, design, out, path)
    return design


def _check_implements(
    plan: ImplementationPlan, design: DesignSet, out: Collector, path: str
) -> None:
    stages = {c.id: {s.id for s in c.stages} for c in design.expected_changes}
    chosen: set[str] = set()
    for phase in plan.phases:
        for item in phase.implements:
            match = _IMPLEMENTS.match(item)
            if match is None or match["change"] not in stages:
                out.error(
                    "ORQ-E376",
                    f"{phase.id} implements {item}, which the design does not declare",
                    path,
                )
                continue
            chosen.add(match["change"])
            if match["stage"] is not None and match["stage"] not in stages[match["change"]]:
                out.error(
                    "ORQ-E376",
                    f"{phase.id} implements {item}, but that stage is not in the design",
                    path,
                )
    for missing in sorted(set(stages) - chosen):
        out.warning(
            "ORQ-W377",
            f"{missing} is not selected by any phase; this release has no way to defer it "
            "with a reason",
            path,
        )


def _check_class(plan: ImplementationPlan, design: DesignSet, out: Collector, path: str) -> None:
    chosen = {item.split("@")[0] for phase in plan.phases for item in phase.implements}
    changes = [c for c in design.expected_changes if c.id in chosen]
    paths = tuple(sorted({op.path for phase in plan.phases for op in phase.file_operations}))
    computed = trigger_class(change_scope(design, paths, changes), change_policy(design))
    approved = ChangeClass.parse(design.change_class.effective)
    if computed.change_class > approved:
        out.error(
            "ORQ-E378",
            f"the plan's operations trigger {computed.change_class.name}, above the approved "
            f"design's {approved.name}: a new design approval is needed",
            path,
        )


def _check_ledger(
    services: ValidateServices, raw_path: str, explicit: str | None, out: Collector
) -> None:
    candidate = explicit
    if candidate is None:
        try:
            parent = CanonicalPath.parse(raw_path).parent
        except InvalidPath:
            return
        if parent is None:
            return
        candidate = str(parent.child(LEDGER_FILE))
        if read_file(services, candidate) is None:
            return
    ledger, _, _ = read_artifact(services, candidate, QuestionLedger, out)
    if ledger is None:
        return
    for question in blocking_questions(ledger, "plan"):
        out.error(
            "ORQ-E387", f"{question.id} is open and blocks the plan: {question.text}", raw_path
        )
