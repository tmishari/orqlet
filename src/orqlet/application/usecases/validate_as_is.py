"""`orqlet validate as-is`: facts only, evidence that resolves, uncertainty kept (proposal 17.3).

The validator, not the model, enforces the discipline: the schema has no field for proposals,
every fact cites lines that must exist at the bound revision with the cited hash (task-owned
evidence may instead be read at HEAD), the size budget counts facts only, and unknowns and
contradictions can never be dropped. A reference proves that
the cited lines exist and have that content. It does not prove they support the statement, which
is why the design approver and a reviewer sample the facts.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from orqlet.application.contracts.as_is import AsIsArtifact, AsIsFragment, FactEvidence
from orqlet.application.contracts.question_ledger import QuestionLedger
from orqlet.application.ports.filesystem import FileKind, FileSystemError
from orqlet.application.usecases.evidence_cite import problem_list, web_evidence_problems
from orqlet.application.usecases.staleness import changed_in_scope
from orqlet.application.usecases.validate_ledger import LEDGER_FILE, blocking_questions
from orqlet.application.usecases.validation import (
    Collector,
    ValidateServices,
    ValidationResult,
    read_artifact,
    task_of,
)
from orqlet.domain.conventions import printable
from orqlet.domain.errors import InvalidPath
from orqlet.domain.evidence import EvidenceRef, EvidenceStatus, check_reference
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.prescriptive import prescriptive_hits


@dataclass(frozen=True, slots=True)
class AsIsOptions:
    against: str | None = None  # a revision (HEAD or a full object id) to compare the scope with
    fragments_dir: str | None = None  # a folder inside the project that holds the fragments
    ledger: str | None = None  # the question ledger; default: `questions.yaml` beside the file


def validate_as_is(
    services: ValidateServices, raw_path: str, options: AsIsOptions | None = None
) -> ValidationResult:
    options = options or AsIsOptions()
    out = Collector()
    artifact, _, body = read_artifact(services, raw_path, AsIsArtifact, out, front_matter=True)
    if artifact is None:
        return out.result()
    _check_consistency(artifact, raw_path, out)
    _check_ids(artifact, out, raw_path)
    _check_evidence(services, artifact, out, raw_path)
    words = _check_size(artifact, out, raw_path)
    _check_language(artifact, body, out, raw_path)
    if not artifact.facts:
        out.skip("the AS-IS file lists no facts, so nothing was checked")
    _check_ledger(services, artifact, options.ledger, raw_path, out)
    if options.fragments_dir is not None:
        _check_fragments(services, artifact, options.fragments_dir, out)
    if options.against is not None:
        _check_against(services, artifact, options.against, out, raw_path)
    return out.result(
        {
            "facts": len(artifact.facts),
            "unknowns": len(artifact.unknowns),
            "material_unknowns": sum(1 for u in artifact.unknowns if u.material),
            "contradictions": len(artifact.contradictions),
            "words": words,
            "research_mode": artifact.research_mode,
            "base_revision": artifact.base_revision,
        }
    )


def _check_consistency(artifact: AsIsArtifact, path: str, out: Collector) -> None:
    if artifact.base_revision != artifact.header.bound.base_revision:
        out.error(
            "ORQ-E330",
            "base_revision and header.bound.base_revision are different revisions",
            path,
        )
    task = task_of(path)
    if task is not None:
        if artifact.header.task != task:
            out.error(
                "ORQ-E331",
                f"the header names task {artifact.header.task} but the file sits in {task}",
                path,
            )
        if artifact.scope.request_ref != task:
            out.error(
                "ORQ-E331",
                f"scope.request_ref is {artifact.scope.request_ref} but the task is {task}",
                path,
            )


def _check_ids(artifact: AsIsArtifact, out: Collector, path: str) -> None:
    groups = (
        ("fact", [f.id for f in artifact.facts]),
        ("unknown", [u.id for u in artifact.unknowns]),
        ("contradiction", [c.id for c in artifact.contradictions]),
    )
    for kind, ids in groups:
        for duplicate, count in sorted(Counter(ids).items()):
            if count > 1:
                out.error("ORQ-E336", f"the {kind} id {duplicate} is used {count} times", path)


def _is_task_owned(evidence_path: str, task: str) -> bool:
    """A file inside `docs/design/<task>/evidence/`, compared exactly and case-sensitively."""
    parts = evidence_path.split("/")
    return len(parts) > 4 and parts[:4] == ["docs", "design", task, "evidence"]


class _TaskEvidenceAtHead:
    """Task-owned evidence that cites another revision (ADR-003 decisions 2 and 3).

    A squash merge leaves the revision of a commit on a branch behind, so the content hash is the
    binding: the file is read at HEAD, scanned once like web evidence and hash-checked.
    """

    def __init__(self, services: ValidateServices, out: Collector) -> None:
        self._services = services
        self._out = out
        self._has_head: bool | None = None
        self._read: dict[str, tuple[bytes | None, tuple[str, ...]]] = {}

    def check(self, fact_id: str, item: FactEvidence, artifact_path: str) -> None:
        if self._has_head is None:
            self._has_head = self._services.vcs.has_revision("HEAD")
        if not self._has_head:
            self._out.skip("HEAD is not in this repository, so task evidence was not read")
            return
        if item.path not in self._read:
            self._read[item.path] = self._read_and_scan(fact_id, item.path, artifact_path)
        content, problems = self._read[item.path]
        if problems:
            return
        reference = EvidenceRef.parse(item.path, item.lines, item.revision, item.sha256)
        _report_status(
            fact_id, reference, check_reference(reference, content), self._out, artifact_path
        )

    def _read_and_scan(
        self, fact_id: str, evidence_path: str, artifact_path: str
    ) -> tuple[bytes | None, tuple[str, ...]]:
        content = self._services.vcs.read_at("HEAD", evidence_path)
        problems = () if content is None else web_evidence_problems(content)
        if problems:
            self._out.error(
                "ORQ-E338",
                f"{fact_id}: {printable(evidence_path, 200)} fails these checks for evidence: "
                f"{problem_list(problems)}. Treat a credential that it shows as exposed, because "
                "the file may already be pushed or merged: revoke or rotate it. Then remove the "
                "text from the file and cite the file again.",
                artifact_path,
            )
        return content, problems


def _check_evidence(
    services: ValidateServices, artifact: AsIsArtifact, out: Collector, path: str
) -> None:
    revision = artifact.base_revision
    # The task comes from the file's own path, never from its header: a copy kept elsewhere
    # exempts nothing (ADR-003 decision 2).
    task = task_of(path)
    at_head = _TaskEvidenceAtHead(services, out)
    available = services.vcs.has_revision(revision)
    if not available:
        out.skip(f"the base revision {revision[:12]} is not in this repository")
    contents: dict[tuple[str, str], bytes | None] = {}
    for fact in artifact.facts:
        for item in fact.evidence:
            if item.revision != revision:
                if task is not None and _is_task_owned(item.path, task):
                    at_head.check(fact.id, item, path)
                    continue
                out.error(
                    "ORQ-E332",
                    f"{fact.id}: evidence cites revision {item.revision[:12]}, but the file is "
                    f"bound to {revision[:12]}",
                    path,
                )
                continue
            if not available:
                continue
            key = (item.revision, item.path)
            if key not in contents:
                contents[key] = services.vcs.read_at(item.revision, item.path)
            reference = EvidenceRef.parse(item.path, item.lines, item.revision, item.sha256)
            status = check_reference(reference, contents[key])
            _report_status(fact.id, reference, status, out, path)


_STATUS_CODES = {
    EvidenceStatus.MISSING: ("ORQ-E333", "does not exist at that revision"),
    EvidenceStatus.OUT_OF_RANGE: ("ORQ-E334", "does not have those lines"),
    EvidenceStatus.CHANGED: ("ORQ-E335", "has other content on those lines than the hash says"),
}


def _report_status(
    fact_id: str, ref: EvidenceRef, status: EvidenceStatus, out: Collector, path: str
) -> None:
    if status is EvidenceStatus.RESOLVED:
        return
    code, what = _STATUS_CODES[status]
    out.error(code, f"{fact_id}: {ref.path} lines {ref.lines} {what}", path)


def _check_size(artifact: AsIsArtifact, out: Collector, path: str) -> int:
    words = sum(len(fact.statement.split()) for fact in artifact.facts)
    if words > artifact.size_budget.max_words:
        out.error(
            "ORQ-E337",
            f"the facts use {words} words; the budget is {artifact.size_budget.max_words}. "
            "Unknowns and contradictions do not count and may not be cut to fit",
            path,
        )
    return words


def _check_language(artifact: AsIsArtifact, body: str, out: Collector, path: str) -> None:
    for fact in artifact.facts:
        phrases = sorted({hit.phrase for hit in prescriptive_hits(fact.statement)})
        if phrases:
            out.warning(
                "ORQ-W338",
                f"{fact.id} reads as advice ({', '.join(phrases)}); an AS-IS file states facts",
                path,
            )
    phrases = sorted({hit.phrase for hit in prescriptive_hits(body)})
    if phrases:
        out.warning(
            "ORQ-W338",
            f"the text after the front matter reads as advice ({', '.join(phrases)}); the "
            "structured facts are what is validated",
            path,
        )


def _ledger(
    services: ValidateServices, explicit: str | None, raw_path: str, out: Collector
) -> QuestionLedger | None:
    candidate = explicit
    if candidate is None:
        try:
            parent = CanonicalPath.parse(raw_path).parent
        except InvalidPath:
            return None
        if parent is None:
            return None
        candidate = str(parent.child(LEDGER_FILE))
        try:
            if services.project.kind(CanonicalPath.parse(candidate)) is not FileKind.FILE:
                return None
        except (InvalidPath, FileSystemError):
            return None
    ledger, _, _ = read_artifact(services, candidate, QuestionLedger, out)
    return ledger


def _check_ledger(
    services: ValidateServices,
    artifact: AsIsArtifact,
    explicit: str | None,
    raw_path: str,
    out: Collector,
) -> None:
    refs = {u.question_ref for u in artifact.unknowns if u.question_ref}
    ledger = _ledger(services, explicit, raw_path, out)
    if ledger is None:
        if refs:
            out.warning(
                "ORQ-W339",
                f"unknowns cite {', '.join(sorted(refs))} but no question ledger was found",
                raw_path,
            )
        return
    known = {q.id for q in ledger.questions}
    for missing in sorted(refs - known):
        out.error(
            "ORQ-E339", f"an unknown cites {missing}, which the ledger does not hold", raw_path
        )
    for question in blocking_questions(ledger, "research"):
        out.error(
            "ORQ-E345",
            f"{question.id} is open and blocks research: {question.text}",
            raw_path,
        )


def _check_fragments(
    services: ValidateServices, artifact: AsIsArtifact, directory: str, out: Collector
) -> None:
    """Every unknown and contradiction of every fragment appears in the synthesis (17.3)."""
    fragments = _read_fragments(services, directory, out)
    if fragments is None:
        return
    kept = {ref for unknown in artifact.unknowns for ref in unknown.merged_from}
    kept |= {ref for contradiction in artifact.contradictions for ref in contradiction.merged_from}
    unknown_text = {u.what.strip() for u in artifact.unknowns}
    contradiction_text = {c.note.strip() for c in artifact.contradictions}
    for fragment in fragments:
        entries: Iterable[tuple[str, str, set[str]]] = (
            *((u.id, u.what.strip(), unknown_text) for u in fragment.unknowns),
            *((c.id, c.note.strip(), contradiction_text) for c in fragment.contradictions),
        )
        for entry_id, text, same_text in entries:
            reference = f"{fragment.fragment_id}/{entry_id}"
            if reference not in kept and text not in same_text:
                out.error(
                    "ORQ-E340",
                    f"{reference} was dropped: it is neither repeated nor named in a "
                    "`merged_from` list of the synthesis",
                    directory,
                )


def _read_fragments(
    services: ValidateServices, directory: str, out: Collector
) -> list[AsIsFragment] | None:
    try:
        base = CanonicalPath.parse(directory)
        if services.project.kind(base) is not FileKind.DIRECTORY:
            out.error("ORQ-E321", f"{directory} is not a folder inside the project", directory)
            return None
        names = [n for n in services.project.list_dir(base) if n.endswith((".yaml", ".yml"))]
    except (InvalidPath, FileSystemError) as error:
        out.error("ORQ-E322", f"{directory} cannot be read: {error}", directory)
        return None
    found: list[AsIsFragment] = []
    for name in names:
        fragment, _, _ = read_artifact(services, str(base.child(name)), AsIsFragment, out)
        if fragment is not None:
            found.append(fragment)
    if not found and not out.has_errors():
        out.skip(f"{directory} holds no fragment files, so nothing was compared")
    return found


def _check_against(
    services: ValidateServices, artifact: AsIsArtifact, against: str, out: Collector, path: str
) -> None:
    changed = changed_in_scope(services.vcs, artifact.base_revision, against, artifact.scope.paths)
    if changed is None:
        out.skip(f"the revision {against[:12]} or the base revision is not in this repository")
        return
    if changed:
        shown = ", ".join(changed[:5]) + (" and more" if len(changed) > 5 else "")
        out.warning(
            "ORQ-W341",
            f"stale: {len(changed)} file(s) in scope changed since the base revision ({shown})",
            path,
        )
        out.skip("the AS-IS file is stale: its base revision no longer matches the scope")
