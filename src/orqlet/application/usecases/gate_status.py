"""`orqlet gate status`: what an artifact was written against, and whether that is still true.

It is read-only and runs offline. It re-checks the base revision, the standards lock, the profile
version, the workflow version and the protected set of the installed Orqlet files. An artifact
written against other inputs is `stale` and the verdict is `NOT_RUN`: nothing resumes silently.
Approval is evidence on the protected baseline that the code host holds. An offline run has no
such evidence, so with a task the verdict is always `NOT_RUN` (proposal 17.6 and 17.7).
"""

from __future__ import annotations

from dataclasses import dataclass

from orqlet.application.contracts.artifact_header import ArtifactHeader
from orqlet.application.contracts.as_is import AsIsArtifact
from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.contracts.standards_lock import StandardsLock
from orqlet.application.contracts.workflow_package import WorkflowLock
from orqlet.application.ports.documents import DocumentError
from orqlet.application.usecases.binding_inputs import locate, read_contract_at
from orqlet.application.usecases.expected_change import evaluate_expected_changes
from orqlet.application.usecases.render_all import (
    LOCK_PATH,
    PROFILE_PATH,
    STANDARDS_LOCK_PATH,
    WORKFLOW_LOCK_PATH,
)
from orqlet.application.usecases.staleness import changed_in_scope
from orqlet.application.usecases.validation import (
    TASK_ROOT,
    Collector,
    ValidateServices,
    ValidationResult,
    content_hash,
    read_artifact,
    read_file,
)
from orqlet.domain.digest import digest_of
from orqlet.domain.expected_change import Outcome
from orqlet.domain.ownership import FileClass
from orqlet.domain.paths import CanonicalPath


@dataclass(frozen=True, slots=True)
class BoundValues:
    """The inputs that an artifact header records, as they are right now."""

    base_revision: str | None
    standards_lock_hash: str | None
    applicable_rules_hash: str | None
    profile_version: int | None
    workflow_version: str | None
    protected_set_digest: str | None

    def as_data(self) -> dict[str, object]:
        return {
            "base_revision": self.base_revision,
            "standards_lock_hash": self.standards_lock_hash,
            "applicable_rules_hash": self.applicable_rules_hash,
            "profile_version": self.profile_version,
            "workflow_version": self.workflow_version,
            "protected_set_digest": self.protected_set_digest,
        }


def protected_set_digest(lock: GeneratedLock) -> str:
    """SHA-256 over the path and rendered hash of every protected file the manifest lists."""
    entries = sorted(
        [item.path, item.rendered_sha256]
        for item in lock.files
        if item.file_class is FileClass.PROTECTED and item.rendered_sha256 is not None
    )
    return digest_of(entries)


def current_bound(services: ValidateServices, out: Collector) -> BoundValues:
    lock = _contract(services, LOCK_PATH, GeneratedLock, out)
    standards = _contract(services, STANDARDS_LOCK_PATH, StandardsLock, out)
    profile = _contract(services, PROFILE_PATH, ProjectProfile, out)
    workflow = _contract(services, WORKFLOW_LOCK_PATH, WorkflowLock, out)
    standards_bytes = read_file(services, str(STANDARDS_LOCK_PATH))
    return BoundValues(
        base_revision=services.vcs.head_commit(),
        standards_lock_hash=None if standards_bytes is None else content_hash(standards_bytes),
        applicable_rules_hash=None if standards is None else standards.applicable_rules_hash,
        profile_version=None if profile is None else profile.profile.version,
        workflow_version=None if workflow is None else workflow.workflow_version,
        protected_set_digest=None if lock is None else protected_set_digest(lock),
    )


def gate_status(
    services: ValidateServices,
    task: str | None = None,
    *,
    phase: str | None = None,
    base: str | None = None,
    head: str | None = None,
) -> ValidationResult:
    out = Collector()
    bound = current_bound(services, out)
    if bound.base_revision is None:
        out.skip("the repository has no commit yet, so nothing can be bound to a revision")
    if out.has_errors():
        return out.result({"bound": bound.as_data()})
    data: dict[str, object] = {"bound": bound.as_data()}
    if task is None:
        return out.result(data)
    data["task"] = task
    data["artifacts"] = _check_task(services, task, bound, out)
    if phase is not None:
        data["expected_changes"] = _check_expected(services, task, phase, base, head, out)
    out.info(
        "ORQ-I393",
        "approval of the design and of the plan is evidence on the protected baseline; an "
        "offline run has none, so it is not checked",
    )
    out.skip("approval needs host evidence, which an offline run does not have")
    return out.result(data)


def _contract[T: GeneratedLock | StandardsLock | ProjectProfile | WorkflowLock](
    services: ValidateServices, path: CanonicalPath, model: type[T], out: Collector
) -> T | None:
    data = read_file(services, str(path))
    if data is None:
        out.error(
            "ORQ-E390",
            f"{path} is missing; this directory has no complete Orqlet installation "
            "(run `orqlet init`)",
            str(path),
        )
        return None
    try:
        return load_contract(services.loader, model, data, source=str(path))
    except DocumentError as error:
        out.error("ORQ-E391", str(error), str(path))
        return None


def _check_task(
    services: ValidateServices, task: str, bound: BoundValues, out: Collector
) -> dict[str, object]:
    folder = f"{TASK_ROOT}/{task}"
    found: dict[str, object] = {}
    as_is_path = f"{folder}/as-is.md"
    design_path = f"{folder}/design/manifest.yaml"
    plan_path = f"{folder}/plan.yaml"
    for name, path in (("as-is", as_is_path), ("design", design_path), ("plan", plan_path)):
        if read_file(services, path) is None:
            out.info("ORQ-I394", f"{name}: {path} does not exist yet", path)
            found[name] = {"found": False}
    if "as-is" not in found:
        as_is, _, _ = read_artifact(services, as_is_path, AsIsArtifact, out, front_matter=True)
        found["as-is"] = _assess("as-is", as_is_path, as_is, bound, services, out)
    if "design" not in found:
        design, _, _ = read_artifact(services, design_path, DesignSet, out)
        found["design"] = _assess("design", design_path, design, bound, services, out)
    if "plan" not in found:
        plan, _, _ = read_artifact(services, plan_path, ImplementationPlan, out)
        found["plan"] = _assess("plan", plan_path, plan, bound, services, out)
    return found


def _assess(
    name: str,
    path: str,
    artifact: AsIsArtifact | DesignSet | ImplementationPlan | None,
    bound: BoundValues,
    services: ValidateServices,
    out: Collector,
) -> dict[str, object]:
    if artifact is None:
        return {"found": True, "readable": False}
    stale = _stale_components(artifact.header, bound)
    if _base_moved(services, artifact.header, bound, _scope_paths(artifact), name, path, out):
        stale.append("base_revision")
    if stale:
        out.warning("ORQ-W390", f"{name} is stale: {', '.join(stale)}", path)
        out.skip(f"{name} was written against other inputs ({', '.join(stale)})")
    return {"found": True, "readable": True, "stale": stale}


def _scope_paths(artifact: AsIsArtifact | DesignSet | ImplementationPlan) -> tuple[str, ...]:
    if isinstance(artifact, ImplementationPlan):
        return tuple(op.path for phase in artifact.phases for op in phase.file_operations)
    return tuple(artifact.scope.paths)


def _stale_components(header: ArtifactHeader, bound: BoundValues) -> list[str]:
    comparisons = (
        ("workflow_version", header.workflow_version, bound.workflow_version),
        ("protected_set_digest", header.protected_set_digest, bound.protected_set_digest),
        ("standards_lock_hash", header.bound.standards_lock_hash, bound.standards_lock_hash),
        ("applicable_rules_hash", header.bound.applicable_rules_hash, bound.applicable_rules_hash),
        ("profile_version", header.bound.profile_version, bound.profile_version),
    )
    return [name for name, recorded, now in comparisons if recorded != now]


def _base_moved(
    services: ValidateServices,
    header: ArtifactHeader,
    bound: BoundValues,
    scope: tuple[str, ...],
    name: str,
    path: str,
    out: Collector,
) -> bool:
    """True when the base revision moved and a file in the artifact's scope changed with it."""
    recorded = header.bound.base_revision
    if bound.base_revision is None or recorded == bound.base_revision:
        return False
    changed = changed_in_scope(services.vcs, recorded, bound.base_revision, scope)
    if changed is None:
        out.skip(f"{name}: its base revision {recorded[:12]} is not in this repository")
        return False
    if changed:
        return True
    out.info(
        "ORQ-I392",
        f"{name}: HEAD moved since its base revision, and no file in its scope changed",
        path,
    )
    return False


_BLOCKING = {Outcome.DEVIATION: "ORQ-E450", Outcome.ADDITIONAL: "ORQ-E451"}


def _check_expected(
    services: ValidateServices,
    task: str,
    phase: str,
    base: str | None,
    head: str | None,
    out: Collector,
) -> list[dict[str, object]]:
    """What the tree under review changed on the watched surfaces, against the approved design."""
    located = locate(services, base, head)
    if located.target is None:
        for problem in located.problems:
            out.skip(problem)
        return []
    target = located.target
    folder = f"{TASK_ROOT}/{task}"
    plan = read_contract_at(services, target.tree, f"{folder}/plan.yaml", ImplementationPlan, out)
    design = read_contract_at(
        services, target.tree, f"{folder}/design/manifest.yaml", DesignSet, out
    )
    if plan is None or design is None:
        return []
    if not any(p.id == phase for p in plan.phases):
        out.error("ORQ-E453", f"the plan has no phase {phase}", f"{folder}/plan.yaml")
        return []
    report = evaluate_expected_changes(services, design, plan, phase, target.base, target.tree)
    for note in report.notes:
        out.info("ORQ-I450", note)
    listed: list[dict[str, object]] = []
    for result in report.results:
        label = result.id or "(no entry)"
        message = f"{label} {result.surface}: {result.outcome.value}. {result.detail}"
        code = _BLOCKING.get(result.outcome)
        if code is not None:
            out.error(code, message + " A renewed design approval is needed.")
        else:
            out.info("ORQ-I451", message)
        listed.append(
            {
                "id": result.id,
                "surface": result.surface,
                "outcome": result.outcome.value,
                "detail": result.detail,
            }
        )
    return listed
