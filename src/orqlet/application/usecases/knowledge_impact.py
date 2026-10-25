"""`orqlet knowledge impact`: what a phase may have made stale, found without a model (17.13.3).

The analysis reads shared sources only: the committed tree, never a private store. It works on the
**pre-draft tree**: the tree under review with every path in the plan's knowledge scope, or named by
`knowledge.yaml` as a source or a write scope, reset to its merge-base content. A draft therefore
cannot change its own candidate list, which is a pure function of the code, the tests and the
knowledge as it stood before the phase.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.knowledge_config import DocsMap, KnowledgeConfig
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.module_card import ModuleCard
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.ports.documents import DocumentError
from orqlet.application.usecases.binding_inputs import (
    BindingRequest,
    ChangeSet,
    KnowledgeScope,
    Target,
    change_set,
    compute_components,
    knowledge_scope,
    locate,
    read_contract_at,
    read_knowledge_config,
)
from orqlet.application.usecases.expected_change import (
    evaluate_expected_changes,
    public_api_delta,
)
from orqlet.application.usecases.validation import (
    TASK_ROOT,
    Collector,
    ValidateServices,
    ValidationResult,
    split_front_matter,
)
from orqlet.domain.binding import COVERS, RecordKind, input_digest
from orqlet.domain.digest import digest_of
from orqlet.domain.expected_change import ApiDelta, Outcome
from orqlet.domain.globs import glob_match
from orqlet.domain.knowledge import (
    Candidate,
    candidate,
    candidates_digest,
    markdown_references,
)
from orqlet.domain.python_api import extract_module_api

DOCS_MAP_PATH = ".orqlet/docs-map.yaml"
TEXT_EXTENSIONS = (".md", ".rst", ".txt", ".adoc", ".yaml", ".yml")


@dataclass(frozen=True, slots=True)
class Analysis:
    """The candidates of one phase, with everything the validator needs to recompute them."""

    candidates: tuple[Candidate, ...]
    digest: str
    target: Target
    changes: ChangeSet
    scope: KnowledgeScope
    plan: ImplementationPlan | None
    design: DesignSet | None
    notes: tuple[str, ...] = ()
    paths: frozenset[str] = field(default_factory=frozenset)


def analyse(
    services: ValidateServices,
    task: str,
    base: str | None,
    head: str | None,
    out: Collector,
    *,
    target: Target | None = None,
) -> Analysis | None:
    if target is None:
        located = locate(services, base, head)
        if located.target is None:
            for problem in located.problems:
                out.skip(problem)
            return None
        target = located.target
    folder = f"{TASK_ROOT}/{task}"
    plan = read_contract_at(services, target.tree, f"{folder}/plan.yaml", ImplementationPlan, out)
    design = read_contract_at(
        services, target.tree, f"{folder}/design/manifest.yaml", DesignSet, out
    )
    scope = knowledge_scope(services, target.tree, plan)
    changes = change_set(services, target, scope)
    notes: list[str] = []
    candidates: dict[str, Candidate] = {}

    def add(item: Candidate) -> None:
        candidates[item.id] = item

    changed = {file.path: file.status for file in changes.code_tests}
    delta = _api_delta(services, design, target, notes)
    names = delta.names() if delta is not None else frozenset()
    documents = _pre_draft_documents(services, target, scope, notes)
    for path, text in documents.items():
        for subject in _references(services, path, text) & (set(changed) | names):
            what = changed.get(subject) or "changed"
            add(candidate("reference", subject, path, f"{path} names {subject}, which was {what}"))
    for path, text in documents.items():
        _card_digest_candidate(services, target, path, text, add)
    if delta is not None:
        for name, kind in (
            *((n, "added") for n in delta.added),
            *((n, "removed") for n in delta.removed),
            *((n, "changed") for n in delta.changed),
        ):
            add(candidate("public-symbol", name, None, f"the public symbol {name} was {kind}"))
    _implemented_changes(services, design, plan, target, add)
    _docs_map_candidates(services, target, changed, names, add)
    ordered = tuple(sorted(candidates.values(), key=lambda c: c.id))
    return Analysis(
        ordered,
        candidates_digest(ordered),
        target,
        changes,
        scope,
        plan,
        design,
        tuple(notes),
        frozenset(documents),
    )


def knowledge_impact(
    services: ValidateServices, task: str, phase: str, base: str | None, head: str | None
) -> ValidationResult:
    out = Collector()
    analysis = analyse(services, task, base, head, out)
    if analysis is None or out.has_errors():
        return out.result()
    for note in analysis.notes:
        out.info("ORQ-I400", note)
    if analysis.plan is None or analysis.design is None:
        out.skip("the plan and the design are needed to bind the record to its inputs")
    data: dict[str, object] = {
        "candidates": [
            {
                "id": c.id,
                "kind": c.kind,
                "subject": c.subject,
                "knowledge": c.knowledge,
                "reason": c.reason,
            }
            for c in analysis.candidates
        ],
        "candidate_count": len(analysis.candidates),
        "candidates_digest": analysis.digest,
        "tree": analysis.target.label,
        "base": analysis.target.base,
    }
    binding = knowledge_binding(services, task, phase, analysis, out)
    if binding is not None:
        data["review_input"] = binding
    return out.result(data)


def knowledge_binding(
    services: ValidateServices, task: str, phase: str, analysis: Analysis, out: Collector
) -> dict[str, object] | None:
    """The `review_input` block a knowledge-impact record must carry for this tree."""
    request = BindingRequest(
        task, phase, analysis.target, analysis.changes, candidates_digest=analysis.digest
    )
    components = compute_components(services, request, out)
    covers = COVERS[RecordKind.KNOWLEDGE_IMPACT]
    if any(component not in components for component in covers):
        return None
    return {
        "schema": "orqlet.review-input/v1",
        "covers": [component.value for component in covers],
        "components": {c.value: components[c] for c in covers},
        "digest": input_digest(components, covers),
        "merge_base": analysis.target.base,
    }


# --- the pre-draft knowledge ----------------------------------------------------------------
def _knowledge_globs(config: KnowledgeConfig | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if config is None:
        return (), ()
    include = tuple(g for s in config.sources if s.scope == "project" for g in s.globs) + tuple(
        g for w in config.write_scope for g in w.globs
    )
    return include, config.exclude


def _pre_draft_documents(
    services: ValidateServices, target: Target, scope: KnowledgeScope, notes: list[str]
) -> dict[str, str]:
    """The knowledge documents as they stood at the merge base: what a draft cannot change."""
    config = read_knowledge_config(services, target.tree)
    include, exclude = _knowledge_globs(config)
    if not include:
        notes.append(
            "no knowledge sources are configured (`.orqlet/knowledge.yaml`); only the plan's "
            "knowledge scope names documents the change can refer to"
        )
    wanted = [
        file.path
        for file in sorted(services.vcs.tree_at(target.base), key=lambda f: f.path)
        if file.path.lower().endswith(TEXT_EXTENSIONS)
        and any(glob_match(g, file.path) for g in (*include, *scope.requested))
        and not any(glob_match(g, file.path) for g in exclude)
    ]
    documents: dict[str, str] = {}
    for path, data in services.vcs.read_many_at(target.base, wanted).items():
        if data is not None:
            documents[path] = data.decode("utf-8", errors="replace")
    return documents


def _references(services: ValidateServices, path: str, text: str) -> set[str]:
    found = set(markdown_references(path, text))
    card = _card(services, path, text)
    if card is not None:
        found |= {*card.refs, *card.paths, *card.symbols}
    return found


def _card(services: ValidateServices, path: str, text: str) -> ModuleCard | None:
    """A module card from a YAML file or from the front matter of a Markdown file, or `None`."""
    body = text
    if path.lower().endswith(".md"):
        split = split_front_matter(text)
        if split is None:
            return None
        body = split[0]
    try:
        return load_contract(services.loader, ModuleCard, body.encode("utf-8"), source=path)
    except DocumentError:
        return None


# --- the detectors --------------------------------------------------------------------------
def _api_delta(
    services: ValidateServices, design: DesignSet | None, target: Target, notes: list[str]
) -> ApiDelta | None:
    packages = (
        design.extractor_config.public_api.packages
        if design and design.extractor_config.public_api
        else ()
    )
    if not packages:
        notes.append("the design names no public_api packages, so public symbols are not compared")
        return None
    return public_api_delta(services, packages, target.base, target.tree, notes)


def _module_file(services: ValidateServices, tree: str, import_path: str) -> str | None:
    stem = import_path.replace(".", "/")
    known = {file.path for file in services.vcs.tree_at(tree)}
    for option in (
        f"src/{stem}.py",
        f"{stem}.py",
        f"src/{stem}/__init__.py",
        f"{stem}/__init__.py",
    ):
        if option in known:
            return option
    return None


def _card_digest_candidate(
    services: ValidateServices,
    target: Target,
    path: str,
    text: str,
    add: Callable[[Candidate], None],
) -> None:
    card = _card(services, path, text)
    if card is None or card.interface.python is None or card.interface_digest is None:
        return
    source = _module_file(services, target.tree, card.interface.python.import_path)
    if source is None:
        return
    data = services.vcs.read_at(target.tree, source) or b""
    api = extract_module_api(
        data.decode("utf-8", errors="replace"), is_package_init=source.endswith("__init__.py")
    )
    current = digest_of(sorted([name, symbol.digest] for name, symbol in api.symbols.items()))
    if current != card.interface_digest:
        add(
            candidate(
                "interface-digest",
                card.interface.python.import_path,
                path,
                f"the interface of {card.interface.python.import_path} differs from the one "
                f"{path} declares",
            )
        )


def _implemented_changes(
    services: ValidateServices,
    design: DesignSet | None,
    plan: ImplementationPlan | None,
    target: Target,
    add: Callable[[Candidate], None],
) -> None:
    if design is None or not design.expected_changes:
        return
    report = evaluate_expected_changes(services, design, plan, None, target.base, target.tree)
    for result in report.results:
        if result.id is not None and result.outcome in {Outcome.IMPLEMENTED, Outcome.DEVIATION}:
            add(
                candidate(
                    "expected-change", result.id, None, f"{result.id} ({result.outcome.value})"
                )
            )


def _docs_map_candidates(
    services: ValidateServices,
    target: Target,
    changed: dict[str, str],
    symbols: frozenset[str],
    add: Callable[[Candidate], None],
) -> None:
    data = services.vcs.read_at(target.tree, DOCS_MAP_PATH)
    if data is None:
        return
    try:
        docs_map = load_contract(services.loader, DocsMap, data, source=DOCS_MAP_PATH)
    except DocumentError:
        return
    for entry in docs_map.targets:
        hits = sorted(
            {p for p in changed for g in entry.code if glob_match(g, p)}
            | {s for s in symbols for g in entry.code if s == g or s.endswith(f".{g}")}
        )
        for subject in hits:
            for doc in entry.docs:
                add(
                    candidate(
                        "docs-map",
                        subject,
                        doc.path,
                        f"docs-map maps it to {doc.path} ({entry.owner})",
                    )
                )
