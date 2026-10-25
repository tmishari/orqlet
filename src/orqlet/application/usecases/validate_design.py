"""`orqlet validate design`: the design set at the depth of its change class (proposal 17.4).

The class is recomputed from the declared scope and the expected changes. Nobody can lower it:
a manifest that states a lower trigger class, or an effective class below the maximum, fails.
Every artifact kind the class requires must be declared, exist and match its hash. An approval
is a merge on the protected baseline and is not checked here.
"""

from __future__ import annotations

import re
from collections import Counter

from orqlet.application.contracts.design_set import DesignArtifact, DesignSet
from orqlet.application.contracts.question_ledger import QuestionLedger
from orqlet.application.usecases.design_scope import (
    EXTRACTOR_SURFACES,
    change_policy,
    change_scope,
)
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
from orqlet.domain.change_class import (
    ChangeClass,
    ChangeScope,
    effective_class,
    required_artifact_groups,
    trigger_class,
)
from orqlet.domain.errors import InvalidPath
from orqlet.domain.paths import CanonicalPath

_ADR_SECTIONS = ("context", "decision", "consequences", "rejected alternatives")
_DIAGRAMS = (
    "flowchart",
    "graph",
    "sequencediagram",
    "c4",
    "classdiagram",
    "statediagram",
    "erdiagram",
)
_DIAGRAM_KINDS = frozenset({"c4-context", "c4-container", "c4-component", "data-flow", "sequence"})


def validate_design(
    services: ValidateServices, raw_path: str, ledger: str | None = None
) -> ValidationResult:
    out = Collector()
    design, _, _ = read_artifact(services, raw_path, DesignSet, out)
    if design is None:
        return out.result()
    _check_task(design, raw_path, out)
    _check_as_is_ref(services, design, raw_path, out)
    _check_artifacts(services, design, raw_path, out)
    computed = _check_class(design, raw_path, out)
    _check_expected_changes(design, raw_path, out)
    _check_reviews(services, design, raw_path, out)
    _check_ledger(services, raw_path, ledger, out)
    return out.result(
        {
            "trigger_class": computed.name,
            "trigger_reasons": list(trigger_class(_scope(design), change_policy(design)).reasons),
            "effective_class": design.change_class.effective,
            "artifacts": len(design.artifacts),
            "expected_changes": len(design.expected_changes),
            "manual_expected_changes": sum(
                1 for c in design.expected_changes if c.verification == "manual"
            ),
        }
    )


def _scope(design: DesignSet) -> ChangeScope:
    return change_scope(design, design.scope.paths, design.expected_changes)


def _check_task(design: DesignSet, path: str, out: Collector) -> None:
    task = task_of(path)
    if task is not None and design.header.task != task:
        out.error(
            "ORQ-E350",
            f"the header names task {design.header.task} but the file sits in {task}",
            path,
        )


def _check_as_is_ref(
    services: ValidateServices, design: DesignSet, path: str, out: Collector
) -> None:
    parts = split_reference(design.as_is_ref)
    if parts is None:
        out.error("ORQ-E351", "as_is_ref must be `<path>#<sha256>`", path)
        return
    raw, digest = parts
    data = read_file(services, raw)
    if data is None:
        out.error("ORQ-E352", f"the AS-IS file {raw} does not exist", path)
    elif content_hash(data) != digest:
        out.error("ORQ-E353", f"the AS-IS file {raw} changed after the design cited it", path)


def _check_artifacts(
    services: ValidateServices, design: DesignSet, path: str, out: Collector
) -> None:
    for duplicate, count in sorted(Counter(a.id for a in design.artifacts).items()):
        if count > 1:
            out.error("ORQ-E354", f"the artifact id {duplicate} is used {count} times", path)
    for artifact in design.artifacts:
        if artifact.path is None or artifact.sha256 is None:
            continue
        data = read_file(services, artifact.path)
        if data is None:
            out.error("ORQ-E355", f"{artifact.id}: {artifact.path} does not exist", path)
            continue
        if content_hash(data) != artifact.sha256:
            out.error("ORQ-E356", f"{artifact.id}: {artifact.path} does not match its sha256", path)
        _check_artifact_text(artifact, data.decode("utf-8", errors="replace"), path, out)
    kinds = {a.kind for a in design.artifacts}
    effective = ChangeClass.parse(design.change_class.effective)
    for group in required_artifact_groups(effective):
        if not group & kinds:
            wanted = " or ".join(sorted(group))
            out.error(
                "ORQ-E357",
                f"a {effective.name} design needs an artifact of kind {wanted}",
                path,
            )


def _check_artifact_text(artifact: DesignArtifact, text: str, path: str, out: Collector) -> None:
    if artifact.kind == "adr":
        headings = {
            m.group(1).lower()
            for m in re.finditer(r"^#{1,6}\s*([A-Za-z ]+?)\s*$", text, re.MULTILINE)
        }
        missing = [name for name in _ADR_SECTIONS if name not in headings]
        if missing:
            out.error(
                "ORQ-E358",
                f"{artifact.id}: the ADR lacks the section(s) {', '.join(missing)}",
                path,
            )
    elif artifact.kind in _DIAGRAM_KINDS:
        fence = re.search(r"```mermaid\s*\n\s*(\S+)", text)
        if fence is None or not fence.group(1).lower().startswith(_DIAGRAMS):
            out.warning(
                "ORQ-W359",
                f"{artifact.id}: no Mermaid diagram was found; a table is acceptable only where "
                "nothing changes structure, and a reviewer checks that",
                path,
            )


def _check_class(design: DesignSet, path: str, out: Collector) -> ChangeClass:
    computed = trigger_class(_scope(design), change_policy(design)).change_class
    stated = design.change_class
    trigger, declared = ChangeClass.parse(stated.trigger), ChangeClass.parse(stated.declared)
    if trigger < computed:
        out.error(
            "ORQ-E360",
            f"the manifest states trigger class {trigger.name}; the scope triggers "
            f"{computed.name}. A class cannot be lowered",
            path,
        )
    elif trigger > computed:
        out.warning(
            "ORQ-W362",
            f"the manifest states trigger class {trigger.name}, higher than the {computed.name} "
            "computed from the scope",
            path,
        )
    wanted = effective_class(max(trigger, computed), declared)
    if ChangeClass.parse(stated.effective) != wanted:
        out.error(
            "ORQ-E361",
            f"the effective class must be the maximum, {wanted.name}, not {stated.effective}",
            path,
        )
    return computed


def _check_expected_changes(design: DesignSet, path: str, out: Collector) -> None:
    for duplicate, count in sorted(Counter(c.id for c in design.expected_changes).items()):
        if count > 1:
            out.error("ORQ-E363", f"the expected change {duplicate} is used {count} times", path)
    config = design.extractor_config
    configured = {
        "public-api": config.public_api is not None,
        "dependency": bool(config.dependency_manifests),
        "security": bool(config.security_globs),
    }
    for change in design.expected_changes:
        stage_ids = [stage.id for stage in change.stages]
        if len(stage_ids) != len(set(stage_ids)):
            out.error("ORQ-E363", f"{change.id} repeats a stage id", path)
        if change.verification != "extractor":
            continue
        if change.surface not in EXTRACTOR_SURFACES:
            out.error(
                "ORQ-E364",
                f"{change.id}: this release has no extractor for {change.surface}; "
                "declare `verification: manual`",
                path,
            )
        elif not configured[change.surface]:
            out.error(
                "ORQ-E364",
                f"{change.id}: `extractor_config` does not say where to look for a "
                f"{change.surface} change",
                path,
            )


def _check_reviews(
    services: ValidateServices, design: DesignSet, path: str, out: Collector
) -> None:
    effective = ChangeClass.parse(design.change_class.effective)
    if effective < ChangeClass.D2:
        return
    have = {review.role for review in design.reviews}
    for role in ("architecture-reviewer", "security-reviewer"):
        if role not in have:
            out.error("ORQ-E365", f"a {effective.name} design needs a note from the {role}", path)
    for review in design.reviews:
        if read_file(services, review.note) is None:
            out.error("ORQ-E366", f"the {review.role} note {review.note} does not exist", path)


def _check_ledger(
    services: ValidateServices, raw_path: str, explicit: str | None, out: Collector
) -> None:
    candidate = explicit
    if candidate is None:
        try:
            parent = CanonicalPath.parse(raw_path).parent
            grandparent = parent.parent if parent is not None else None
        except InvalidPath:
            return
        if grandparent is None:
            return
        candidate = str(grandparent.child(LEDGER_FILE))
        if read_file(services, candidate) is None:
            return
    ledger, _, _ = read_artifact(services, candidate, QuestionLedger, out)
    if ledger is None:
        return
    for question in blocking_questions(ledger, "design"):
        out.error("ORQ-E367", f"{question.id} is open and blocks design: {question.text}", raw_path)
