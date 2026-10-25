"""`orqlet validate review|test|knowledge`: the evidence records of a phase (6.14.1, 17.13).

A record is evidence about the inputs it names. Validation proves that the record is well formed,
sits at the exact path its content states, and names the digest of exactly the inputs that Orqlet
computes now from Git objects. It does not prove that a review took place: that rests on the human
approver, who accepts the record as `attested`. A stale record, or one that cannot be bound, is
`NOT_RUN`, never a pass.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.knowledge_impact import (
    WRITING,
    Claim,
    KnowledgeEvidence,
    KnowledgeImpact,
)
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.contracts.review_input import ReviewInput
from orqlet.application.contracts.review_result import ReviewResult
from orqlet.application.contracts.role_bindings import RoleBindings
from orqlet.application.contracts.test_record import TesterRecord
from orqlet.application.ports.filesystem import FileSystemError
from orqlet.application.usecases.binding_inputs import (
    AGENT_FILES,
    BindingRequest,
    Target,
    change_set,
    compute_components,
    knowledge_scope,
    locate,
    read_contract_at,
)
from orqlet.application.usecases.knowledge_impact import Analysis, analyse
from orqlet.application.usecases.validation import (
    TASK_ROOT,
    Collector,
    ValidateServices,
    ValidationResult,
    content_hash,
    read_artifact,
)
from orqlet.domain.binding import (
    COVERS,
    Component,
    RecordKind,
    input_digest,
    stale_components,
)
from orqlet.domain.change_class import ChangeClass
from orqlet.domain.evidence import EvidenceRef, EvidenceStatus, InvalidEvidence, check_reference
from orqlet.domain.evidence_artifacts import (
    MAX_EVIDENCE_BYTES,
    EvidencePath,
    parse_evidence_path,
    rounds_are_contiguous,
)
from orqlet.domain.independence import (
    Independence,
    derive_independence,
    family_of,
    minimum_independence,
)
from orqlet.domain.knowledge import longest_shared_run, markdown_references, near_duplicate
from orqlet.domain.paths import CanonicalPath

COPY_MAX_LINES = 10
NEAR_DUPLICATE_THRESHOLD = 0.8
_LINES_SUFFIX = re.compile(r"^(?P<path>.+):(?P<lines>[1-9]\d*(?:-[1-9]\d*)?)$")


@dataclass(frozen=True, slots=True)
class RecordOptions:
    base: str | None = None  # a branch name or a commit id; default: the target branch
    head: str | None = None  # `staged`, `HEAD` or a commit id; default: staged if there are changes


# --- the checks every record shares ---------------------------------------------------------
def _identity(
    raw_path: str,
    kind: RecordKind,
    out: Collector,
) -> EvidencePath | None:
    parsed = parse_evidence_path(raw_path)
    if parsed is None or parsed.kind is not kind:
        out.error(
            "ORQ-E400",
            f"{raw_path} is not at the exact path of a {kind.value} record "
            f"(docs/design/<task>/…); a file elsewhere is an ordinary input, not evidence",
            raw_path,
        )
        return None
    return parsed


def _size(data: bytes | None, raw_path: str, out: Collector) -> None:
    if data is not None and len(data) > MAX_EVIDENCE_BYTES:
        out.error(
            "ORQ-E402", f"{raw_path} is larger than {MAX_EVIDENCE_BYTES // 1024} KiB", raw_path
        )


def _matches_path(
    record_task: str, record_phase: str, path: EvidencePath, raw_path: str, out: Collector
) -> None:
    if (record_task, record_phase) != (path.task, path.phase):
        out.error(
            "ORQ-E401",
            f"the record says {record_task}/{record_phase} but its path says "
            f"{path.task}/{path.phase}",
            raw_path,
        )


def _verify_binding(
    services: ValidateServices,
    review_input: ReviewInput,
    covers: tuple[Component, ...],
    request: BindingRequest,
    out: Collector,
    raw_path: str,
) -> dict[Component, str]:
    """Recompute the covered components and say which of them the record no longer matches."""
    components = compute_components(services, request, out)
    missing = [c.value for c in covers if c not in components]
    if missing:
        out.skip(f"the binding cannot be recomputed: {', '.join(missing)} unavailable")
        return components
    if set(review_input.covers) != {c.value for c in covers}:
        out.error(
            "ORQ-E410",
            f"this kind of record covers {', '.join(c.value for c in covers)}, "
            f"not {', '.join(review_input.covers)}",
            raw_path,
        )
        return components
    recorded = {str(name): digest for name, digest in review_input.components.items()}
    stale = stale_components(recorded, components, covers)
    if stale:
        out.warning("ORQ-W410", f"stale: {', '.join(stale)} changed since the record", raw_path)
        out.skip(f"the record is stale ({', '.join(stale)}); examine the new inputs again")
    elif input_digest(components, covers) != review_input.digest:
        out.error("ORQ-E411", "the digest does not follow from the components it lists", raw_path)
    if review_input.merge_base != request.target.base:
        out.info(
            "ORQ-I411",
            f"the record names merge base {review_input.merge_base[:12]}; "
            f"this tree is compared with {request.target.base[:12]}",
            raw_path,
        )
    return components


# --- review ---------------------------------------------------------------------------------
def validate_review(
    services: ValidateServices, raw_path: str, options: RecordOptions | None = None
) -> ValidationResult:
    options = options or RecordOptions()
    out = Collector()
    identity = _identity(raw_path, RecordKind.REVIEW, out)
    if identity is None:
        return out.result()
    record, data, _ = read_artifact(services, raw_path, ReviewResult, out)
    _size(data, raw_path, out)
    if record is None:
        return out.result()
    _matches_path(record.task, record.phase, identity, raw_path, out)
    if (record.role, record.round) != (identity.role, identity.round):
        out.error(
            "ORQ-E401",
            f"the record is {record.role} round {record.round} but its path says "
            f"{identity.role} round {identity.round}",
            raw_path,
        )
    _check_rounds(services, identity, raw_path, out)
    _check_quotes(services, record, out, raw_path)
    located = locate(services, options.base, options.head)
    derived: Independence | None = None
    if located.target is None:
        for problem in located.problems:
            out.skip(problem)
    else:
        derived = _review_binding(services, record, located.target, out, raw_path)
    data_out: dict[str, object] = {
        "role": record.role,
        "round": record.round,
        "record_verdict": record.verdict,
        "findings": len(record.findings),
        "blocking": sum(1 for f in record.findings if f.severity == "blocking"),
        "independence_claimed": record.independence,
        "independence_derived": None if derived is None else derived.name,
    }
    return out.result(data_out)


def _check_rounds(
    services: ValidateServices, identity: EvidencePath, raw_path: str, out: Collector
) -> None:
    folder = f"{TASK_ROOT}/{identity.task}/reviews"
    try:
        names = services.project.list_dir(CanonicalPath.parse(folder))
    except FileSystemError:  # a missing folder only means there is nothing to compare
        return
    pattern = re.compile(rf"^{re.escape(str(identity.role))}-{identity.phase}-r([1-9]\d*)\.yaml$")
    rounds = [int(m.group(1)) for name in names if (m := pattern.match(name))]
    if rounds and not rounds_are_contiguous(rounds):
        out.error(
            "ORQ-E403",
            f"the rounds of {identity.role} for {identity.phase} are {sorted(rounds)}; "
            "rounds run r1, r2, … with no gap",
            raw_path,
        )
    if rounds and identity.round is not None and identity.round < max(rounds):
        out.info("ORQ-I403", f"round {max(rounds)} supersedes this one", raw_path)


def _check_quotes(
    services: ValidateServices, record: ReviewResult, out: Collector, raw_path: str
) -> None:
    for finding in record.findings:
        for item in finding.evidence:
            if item.kind != "quote":
                continue
            content = services.vcs.read_at(item.revision, item.path)
            try:
                reference = EvidenceRef.parse(
                    item.path, item.lines, item.revision, item.quote_sha256
                )
            except InvalidEvidence as error:
                out.error("ORQ-E414", f"{finding.id}: {error}", raw_path)
                continue
            if content is None and not services.vcs.has_revision(item.revision):
                out.skip(f"{finding.id}: revision {item.revision[:12]} is not in this repository")
                continue
            status = check_reference(reference, content)
            if status is not EvidenceStatus.RESOLVED:
                out.error(
                    "ORQ-E414",
                    f"{finding.id}: the quote at {item.path} lines {item.lines} is {status.value}",
                    raw_path,
                )


def _review_binding(
    services: ValidateServices,
    record: ReviewResult,
    target: Target,
    out: Collector,
    raw_path: str,
) -> Independence | None:
    plan = read_contract_at(
        services,
        target.tree,
        f"{TASK_ROOT}/{record.task}/plan.yaml",
        ImplementationPlan,
        out,
    )
    scope = knowledge_scope(services, target.tree, plan)
    changes = change_set(services, target, scope)
    request = BindingRequest(
        record.task,
        record.phase,
        target,
        changes,
        role=record.role,
        agent_ref=record.agent.binding_ref,
        agent_client=record.agent.client,
    )
    components = _verify_binding(
        services, record.review_input, COVERS[RecordKind.REVIEW], request, out, raw_path
    )
    derived = _independence(services, record, target, out, raw_path)
    if Component.REVIEWER_DEFINITION in components:
        _check_definition_hash(services, record, target, out, raw_path)
    _check_independence_gate(services, record, derived, target, out)
    return derived


def _check_definition_hash(
    services: ValidateServices, record: ReviewResult, target: Target, out: Collector, raw_path: str
) -> None:
    pattern = AGENT_FILES.get(record.agent.client)
    if pattern is None:
        return
    data = services.vcs.read_at(target.tree, pattern.format(ref=record.agent.binding_ref))
    if data is not None and content_hash(data) != record.agent.definition_sha256:
        out.error(
            "ORQ-E413",
            "agent.definition_sha256 is not the hash of the agent definition in the tree",
            raw_path,
        )


def _independence(
    services: ValidateServices,
    record: ReviewResult,
    target: Target,
    out: Collector,
    raw_path: str,
) -> Independence:
    bindings = read_contract_at(
        services, target.tree, ".orqlet/role-bindings.yaml", RoleBindings, out
    )
    approved = bindings is not None and any(
        b.id == record.agent.binding_ref
        and b.role == record.role
        and record.agent.client in b.clients
        for b in bindings.bindings
    )
    families = [(f.match, f.family) for f in (bindings.model_families if bindings else ())]
    derived = derive_independence(
        approved_binding=approved,
        agent_client=record.agent.client,
        agent_family=family_of(
            record.agent.model_observed or record.agent.model_requested, families
        ),
        coder_client=record.coder_binding.client,
        coder_family=family_of(
            record.coder_binding.model_observed or record.coder_binding.model_requested, families
        ),
    )
    if not approved:
        out.error(
            "ORQ-E415",
            f"{record.agent.binding_ref} is not an approved {record.role} binding for "
            f"{record.agent.client} in .orqlet/role-bindings.yaml",
            raw_path,
        )
    if Independence[record.independence] > derived:
        out.error(
            "ORQ-E412",
            f"the record claims {record.independence} but its identifiers give {derived.name}; "
            "no recorded identifier can show a human reviewer (I3)",
            raw_path,
        )
    return derived


def _check_independence_gate(
    services: ValidateServices,
    record: ReviewResult,
    derived: Independence,
    target: Target,
    out: Collector,
) -> None:
    design = read_contract_at(
        services,
        target.tree,
        f"{TASK_ROOT}/{record.task}/design/manifest.yaml",
        DesignSet,
        out,
    )
    if design is None:
        return
    needed = minimum_independence(ChangeClass.parse(design.change_class.effective))
    if derived < needed:
        out.skip(
            f"independence {derived.name} is below {needed.name}, which a "
            f"{design.change_class.effective} change requires of a review"
        )


# --- test record ----------------------------------------------------------------------------
def validate_test(
    services: ValidateServices, raw_path: str, options: RecordOptions | None = None
) -> ValidationResult:
    options = options or RecordOptions()
    out = Collector()
    identity = _identity(raw_path, RecordKind.TEST, out)
    if identity is None:
        return out.result()
    record, data, _ = read_artifact(services, raw_path, TesterRecord, out)
    _size(data, raw_path, out)
    if record is None:
        return out.result()
    _matches_path(record.task, record.phase, identity, raw_path, out)
    located = locate(services, options.base, options.head)
    if located.target is None:
        for problem in located.problems:
            out.skip(problem)
        return out.result()
    target = located.target
    plan = read_contract_at(
        services, target.tree, f"{TASK_ROOT}/{record.task}/plan.yaml", ImplementationPlan, out
    )
    changes = change_set(services, target, knowledge_scope(services, target.tree, plan))
    request = BindingRequest(record.task, record.phase, target, changes)
    _verify_binding(services, record.review_input, COVERS[RecordKind.TEST], request, out, raw_path)
    if plan is not None:
        _check_coverage(record, plan, out, raw_path)
    _check_commands(record, out, raw_path)
    return out.result(
        {
            "record_verdict": record.verdict,
            "commands": len(record.commands),
            "criteria": len(record.acceptance_coverage),
        }
    )


def _check_commands(record: TesterRecord, out: Collector, raw_path: str) -> None:
    if record.verdict != "PASS":
        return
    if not record.commands:
        out.error("ORQ-E416", "a PASS needs at least one command that ran", raw_path)
    for command in record.commands:
        if command.exit_code != 0:
            out.error(
                "ORQ-E417",
                f"{command.id} exited with {command.exit_code}, so the record cannot be a PASS",
                raw_path,
            )


def _check_coverage(
    record: TesterRecord, plan: ImplementationPlan, out: Collector, raw_path: str
) -> None:
    phase = next((p for p in plan.phases if p.id == record.phase), None)
    if phase is None:
        out.error("ORQ-E418", f"the plan has no phase {record.phase}", raw_path)
        return
    wanted = {c.id for c in phase.acceptance_criteria}
    covered = {c.ac: c.result for c in record.acceptance_coverage}
    for unknown in sorted(set(covered) - wanted):
        out.error("ORQ-E418", f"{unknown} is not an acceptance criterion of {phase.id}", raw_path)
    if record.verdict != "PASS":
        return
    for criterion in sorted(wanted):
        result = covered.get(criterion)
        if result is None:
            out.error("ORQ-E419", f"{criterion} has no result in a PASS record", raw_path)
        elif result != "pass":
            out.error("ORQ-E419", f"{criterion} is {result}, so the record is not a PASS", raw_path)


# --- knowledge-impact record ----------------------------------------------------------------
def validate_knowledge(
    services: ValidateServices, raw_path: str, options: RecordOptions | None = None
) -> ValidationResult:
    options = options or RecordOptions()
    out = Collector()
    identity = _identity(raw_path, RecordKind.KNOWLEDGE_IMPACT, out)
    if identity is None:
        return out.result()
    record, data, _ = read_artifact(services, raw_path, KnowledgeImpact, out)
    _size(data, raw_path, out)
    if record is None:
        return out.result()
    _matches_path(record.task, record.phase, identity, raw_path, out)
    analysis = analyse(services, record.task, options.base, options.head, out)
    if analysis is None:
        return out.result()
    _check_candidates(record, analysis, out, raw_path)
    _check_entries(services, record, analysis, out, raw_path)
    _check_lints(services, record, analysis, out, raw_path)
    request = BindingRequest(
        record.task,
        record.phase,
        analysis.target,
        analysis.changes,
        candidates_digest=analysis.digest,
    )
    _verify_binding(
        services, record.review_input, COVERS[RecordKind.KNOWLEDGE_IMPACT], request, out, raw_path
    )
    return out.result(
        {
            "outcome": record.outcome,
            "candidates": len(analysis.candidates),
            "entries": len(record.entries),
            "candidates_digest": analysis.digest,
        }
    )


def _check_candidates(
    record: KnowledgeImpact, analysis: Analysis, out: Collector, raw_path: str
) -> None:
    if (record.analysis.candidates_digest, record.analysis.candidate_count) != (
        analysis.digest,
        len(analysis.candidates),
    ):
        out.warning(
            "ORQ-W420",
            "stale: the candidate list of the pre-draft tree is not the one the record analysed",
            raw_path,
        )
        out.skip("the candidates changed since the record; run `orqlet knowledge impact` again")
    known = {c.id for c in analysis.candidates}
    seen: dict[str, int] = {}
    for entry in record.entries:
        if entry.candidate_ref is None:
            continue
        if entry.candidate_ref not in known:
            out.error(
                "ORQ-E421",
                f"{entry.id} resolves {entry.candidate_ref}, which is no candidate",
                raw_path,
            )
        seen[entry.candidate_ref] = seen.get(entry.candidate_ref, 0) + 1
    for ref, count in sorted(seen.items()):
        if count > 1:
            out.error("ORQ-E422", f"the candidate {ref} is resolved {count} times", raw_path)
    for candidate in analysis.candidates:
        if candidate.id not in seen:
            out.error(
                "ORQ-E423",
                f"the candidate {candidate.id} ({candidate.reason}) is not resolved",
                raw_path,
            )
    if record.no_impact is not None:
        _check_no_impact(record, analysis, out, raw_path)


def _check_no_impact(
    record: KnowledgeImpact, analysis: Analysis, out: Collector, raw_path: str
) -> None:
    assert record.no_impact is not None
    kinds = {c.kind for c in analysis.candidates}
    if record.no_impact.category in {"internal-refactor", "behaviour-unchanged"} and (
        kinds & {"public-symbol", "expected-change"}
    ):
        out.error(
            "ORQ-E424",
            f"`{record.no_impact.category}` is refused while a watched-surface change or a public "
            "symbol delta exists",
            raw_path,
        )
    if record.no_impact.absence_record.candidates_found != len(analysis.candidates):
        out.error(
            "ORQ-E425",
            "the absence record counts "
            f"{record.no_impact.absence_record.candidates_found} candidates; the analysis found "
            f"{len(analysis.candidates)}",
            raw_path,
        )
    for entry in record.entries:
        if entry.action not in {"unaffected", "proposal"}:
            out.error("ORQ-E424", f"{entry.id}: a no-impact record cannot {entry.action}", raw_path)


def _check_entries(
    services: ValidateServices,
    record: KnowledgeImpact,
    analysis: Analysis,
    out: Collector,
    raw_path: str,
) -> None:
    tree = analysis.target.tree
    named: set[str] = set()
    for entry in record.entries:
        if entry.path is None:
            continue
        named.add(entry.path)
        if (
            entry.action in WRITING
            and entry.scope == "project"
            and not analysis.scope.contains(entry.path)
        ):
            out.error(
                "ORQ-E426",
                f"{entry.id}: {entry.path} is outside the knowledge scope (the plan's "
                "knowledge_scope and the write_scope of .orqlet/knowledge.yaml)",
                raw_path,
            )
        if entry.action in {"add", "correct", "supersede"}:
            _check_draft(services, tree, entry.id, entry.path, entry.claims, out, raw_path)
        for evidence in (*entry.evidence, *(e for c in entry.claims for e in c.evidence)):
            _check_evidence(services, tree, entry.id, evidence, out, raw_path)
    for changed in analysis.changes.knowledge:
        if changed.path not in named:
            out.error(
                "ORQ-E429",
                f"{changed.path} changed inside the knowledge scope and no entry explains it",
                raw_path,
            )
    for entry in record.entries:
        if entry.action == "remove" and entry.path is not None:
            _check_no_dangling(services, analysis, entry.id, entry.path, out, raw_path)


def _check_draft(
    services: ValidateServices,
    tree: str,
    entry_id: str,
    path: str,
    claims: tuple[Claim, ...],
    out: Collector,
    raw_path: str,
) -> None:
    data = services.vcs.read_at(tree, path)
    if data is None:
        out.error(
            "ORQ-E427", f"{entry_id}: the draft {path} is not in the tree under review", raw_path
        )
        return
    text = data.decode("utf-8", errors="replace")
    for claim in claims:
        if claim.anchor not in text:
            out.error(
                "ORQ-E428",
                f"{entry_id}: the draft {path} has no anchor {claim.anchor!r} for {claim.id}",
                raw_path,
            )


def _check_evidence(
    services: ValidateServices,
    tree: str,
    entry_id: str,
    evidence: KnowledgeEvidence,
    out: Collector,
    raw_path: str,
) -> None:
    if evidence.kind == "developer-statement":
        out.warning(
            "ORQ-W432",
            f"{entry_id}: a developer statement is cited; the reviewer must confirm it",
            raw_path,
        )
        return
    if evidence.kind in {"test", "source"}:
        out.skip(
            f"{entry_id}: {evidence.kind} evidence needs a CI result or a documentation source, "
            "which an offline run cannot confirm"
        )
        return
    located = _LINES_SUFFIX.match(evidence.ref)
    path = located["path"] if located else evidence.ref.split("#", 1)[0]
    if parse_evidence_path(path) is not None:
        out.error(
            "ORQ-E435", f"{entry_id}: {path} is an evidence record and cannot be evidence", raw_path
        )
        return
    data = services.vcs.read_at(tree, path)
    if data is None:
        out.error("ORQ-E431", f"{entry_id}: the evidence {path} is not in the tree", raw_path)
        return
    if located is not None:
        status = check_reference(
            EvidenceRef.parse(path, located["lines"], tree, evidence.sha256), data
        )
        ok = status is EvidenceStatus.RESOLVED
    else:
        ok = content_hash(data) == evidence.sha256
    if not ok:
        out.error("ORQ-E431", f"{entry_id}: the evidence {evidence.ref} does not resolve", raw_path)


def _check_no_dangling(
    services: ValidateServices,
    analysis: Analysis,
    entry_id: str,
    removed: str,
    out: Collector,
    raw_path: str,
) -> None:
    for path in sorted(analysis.paths):
        if path == removed:
            continue
        data = services.vcs.read_at(analysis.target.tree, path)
        if data is not None and removed in markdown_references(
            path, data.decode("utf-8", errors="replace")
        ):
            out.error(
                "ORQ-E430",
                f"{entry_id}: {path} still refers to the removed {removed}",
                raw_path,
            )


def _check_lints(
    services: ValidateServices,
    record: KnowledgeImpact,
    analysis: Analysis,
    out: Collector,
    raw_path: str,
) -> None:
    tree = analysis.target.tree
    sources: Mapping[str, str] = {
        f.path: (services.vcs.read_at(tree, f.path) or b"").decode("utf-8", errors="replace")
        for f in analysis.changes.code_tests
        if f.status != "deleted"
    }
    existing = {
        path: (services.vcs.read_at(analysis.target.base, path) or b"").decode(
            "utf-8", errors="replace"
        )
        for path in analysis.paths
    }
    for entry in record.entries:
        if entry.action not in {"add", "correct", "supersede"} or entry.path is None:
            continue
        data = services.vcs.read_at(tree, entry.path)
        if data is None:
            continue
        draft = data.decode("utf-8", errors="replace")
        for path, text in sources.items():
            run = longest_shared_run(draft, text)
            if run > COPY_MAX_LINES:
                out.warning(
                    "ORQ-W433",
                    f"{entry.id}: {run} lines of {entry.path} are copied from {path}; refer to it",
                    raw_path,
                )
        for path, text in existing.items():
            if path != entry.path and near_duplicate(draft, text, NEAR_DUPLICATE_THRESHOLD):
                out.warning("ORQ-W434", f"{entry.id}: {entry.path} nearly repeats {path}", raw_path)
