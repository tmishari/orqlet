"""The knowledge-impact analysis and its record validator, on a fake repository (17.13, FM-K)."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.vcs import CommitSummary, RepoState
from orqlet.application.usecases.knowledge_impact import analyse, knowledge_impact
from orqlet.application.usecases.validate_records import RecordOptions, validate_knowledge
from orqlet.application.usecases.validation import Collector, ValidateServices, ValidationResult
from orqlet.domain.digest import digest_of
from orqlet.domain.facts import line_range_hash
from orqlet.domain.findings import Verdict
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.python_api import extract_module_api
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED
from tests.support.artifacts import TASK_DIR, design, dump, phase, plan

pytestmark = pytest.mark.unit

BASE, HEADC = "1" * 40, "2" * 40
RECORD = f"{TASK_DIR}/knowledge/P-1.yaml"
HASH = "a" * 64
SERVICE = "def existing() -> None: ...\n"
CREATED = SERVICE + "def create_order(customer_id: str) -> str: ...\n"
DOC = "# Service\n\nThe code lives in `src/pkg/service.py`.\n"
KNOWLEDGE = (
    "schema: orqlet.knowledge/v2\n"
    "sources:\n  - {kind: docs, scope: project, globs: ['docs/knowledge/**']}\n"
    "write_scope:\n  - {globs: ['docs/knowledge/**'], kinds: [docs]}\n"
)


def files(**extra: str | bytes) -> dict[str, bytes]:
    base: dict[str, str | bytes] = {
        "src/pkg/__init__.py": "",
        "src/pkg/service.py": SERVICE,
        "docs/knowledge/service.md": DOC,
        ".orqlet/knowledge.yaml": KNOWLEDGE,
        f"{TASK_DIR}/plan.yaml": dump(
            plan(knowledge_scope=["docs/knowledge/**"], phases=[phase(implements=[])])
        ),
        f"{TASK_DIR}/design/manifest.yaml": dump(
            design(extractor_config={"public_api": {"packages": ["pkg"], "mode": "ast"}})
        ),
    }
    for key, value in extra.items():
        path = key.replace("__", "/")
        base[path if "." in path else f"{path}.md"] = value
    return {path: data.encode() if isinstance(data, str) else data for path, data in base.items()}


def services(
    before: dict[str, bytes], after: dict[str, bytes], record: dict[str, Any] | None = None
) -> ValidateServices:
    project = MemoryFileSystem()
    if record is not None:
        project.write_atomic(CanonicalPath.parse(RECORD), dump(record).encode())
    vcs = FakeVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEADC, "head"),),
        committed=after,
        revisions={BASE: before, HEADC: after},
        merge_bases={(HEADC, BASE): (BASE,)},
    )
    return ValidateServices(project=project, vcs=vcs, loader=StrictYamlLoader(), workflow=PINNED)


def candidates(world: ValidateServices) -> list[tuple[str, str]]:
    result = knowledge_impact(world, "demo", "P-1", BASE, "HEAD")
    listed = result.data["candidates"]
    assert isinstance(listed, list)
    return [(c["kind"], c["subject"]) for c in listed]


def after_change(**extra: str | bytes) -> dict[str, bytes]:
    return files(**{"src__pkg__service.py": CREATED, **extra})


# --- the candidates -------------------------------------------------------------------------
def test_a_document_that_names_a_changed_file_and_a_new_public_symbol_are_candidates() -> None:
    world = services(files(), after_change())

    assert sorted(candidates(world)) == [
        ("public-symbol", "pkg.service.create_order"),
        ("reference", "src/pkg/service.py"),
    ]


def test_a_change_that_nothing_refers_to_has_no_candidate() -> None:
    quiet = files(**{"docs__knowledge__service.md": "# Service\n\nNothing named here.\n"})

    assert (
        candidates(services(quiet, files(**{"src__pkg__service.py": SERVICE + "# note\n"}))) == []
    )


def test_the_candidate_list_comes_from_the_pre_draft_tree_so_a_draft_cannot_change_it() -> None:
    before = files()
    plain = after_change()
    drafted = after_change(**{"docs__knowledge__service.md": DOC + "\nSee `src/pkg/other.py`.\n"})

    assert candidates(services(before, plain)) == candidates(services(before, drafted))


def test_a_new_knowledge_document_is_not_part_of_the_pre_draft_tree() -> None:
    drafted = after_change(**{"docs__knowledge__new.md": "Mentions `src/pkg/service.py`.\n"})

    assert ("reference", "src/pkg/service.py") in candidates(services(files(), drafted))
    result = analyse(services(files(), drafted), "demo", BASE, "HEAD", Collector())
    assert result is not None
    assert "docs/knowledge/new.md" not in result.paths


def test_a_card_is_a_candidate_only_while_its_interface_digest_differs_from_the_code() -> None:
    def card(digest: str) -> str:
        return (
            "schema: orqlet.module-card/v1\nid: service\nkind: same-repo-module\nsummary: s\n"
            "owner: team\ninterface:\n  python: {import_path: pkg.service, public_symbols: []}\n"
            f"interface_digest: {digest}\n"
        )

    api = extract_module_api(CREATED)
    right = digest_of(sorted([n, s.digest] for n, s in api.symbols.items()))

    def run(digest: str) -> list[tuple[str, str]]:
        before = files()
        before["docs/knowledge/service-card.yaml"] = card(digest).encode()
        after = after_change()
        after["docs/knowledge/service-card.yaml"] = card(digest).encode()
        return candidates(services(before, after))

    assert ("interface-digest", "pkg.service") in run(HASH)
    assert ("interface-digest", "pkg.service") not in run(right)


def test_the_paths_and_symbols_in_a_cards_front_matter_are_references() -> None:
    card = (
        "---\nschema: orqlet.module-card/v1\nid: service\nkind: same-repo-module\nsummary: s\n"
        "owner: team\npaths: [src/pkg/service.py]\nsymbols: [pkg.service.create_order]\n"
        "---\n# Card\n"
    )
    before = files(docs__knowledge__service=DOC.replace("`src/pkg/service.py`", "nothing"))
    before["docs/knowledge/card.md"] = card.encode()
    after = after_change(docs__knowledge__service=DOC.replace("`src/pkg/service.py`", "nothing"))
    after["docs/knowledge/card.md"] = card.encode()

    found = candidates(services(before, after))

    assert ("reference", "src/pkg/service.py") in found
    assert ("reference", "pkg.service.create_order") in found


def test_a_docs_map_entry_adds_a_candidate_for_each_target() -> None:
    docs_map = (
        "schema: orqlet.docs-map/v1\ntargets:\n"
        "  - code: ['src/pkg/**']\n    docs:\n      - {path: docs/knowledge/service.md}\n"
        "    owner: team\n"
    )
    before = files()
    before[".orqlet/docs-map.yaml"] = docs_map.encode()
    after = after_change()
    after[".orqlet/docs-map.yaml"] = docs_map.encode()

    assert ("docs-map", "src/pkg/service.py") in candidates(services(before, after))


def test_without_a_configuration_nothing_can_refer_to_the_change_and_the_result_says_so() -> None:
    bare = files()
    del bare[".orqlet/knowledge.yaml"]
    after = after_change()
    del after[".orqlet/knowledge.yaml"]

    result = knowledge_impact(services(bare, after), "demo", "P-1", BASE, "HEAD")

    assert any("no knowledge sources" in f.message for f in result.findings)


def test_the_design_without_public_api_packages_says_public_symbols_are_not_compared() -> None:
    bare_design = dump(design())
    after = after_change()
    after[f"{TASK_DIR}/design/manifest.yaml"] = bare_design.encode()

    result = knowledge_impact(services(files(), after), "demo", "P-1", BASE, "HEAD")

    assert any("no public_api packages" in f.message for f in result.findings)


# --- the record -----------------------------------------------------------------------------
def evidence(text: str = "src/pkg/service.py:1", sha256: str | None = None) -> dict[str, Any]:
    real = line_range_hash(CREATED.encode(), 1, 1)
    return {"kind": "code", "ref": text, "sha256": sha256 or real}


def record(world: ValidateServices, entries: list[dict[str, Any]], **over: Any) -> dict[str, Any]:
    data = knowledge_impact(world, "demo", "P-1", BASE, "HEAD").data
    document: dict[str, Any] = {
        "schema": "orqlet.knowledge-impact/v1",
        "task": "demo",
        "phase": "P-1",
        "review_input": {
            "schema": "orqlet.review-input/v1",
            "covers": ["code_tests", "knowledge", "plan", "standards", "candidates"],
            "components": dict.fromkeys(
                ("code_tests", "knowledge", "plan", "standards", "candidates"), HASH
            ),
            "digest": HASH,
            "merge_base": BASE,
        },
        "outcome": "updated",
        "analysis": {
            "command": "orqlet knowledge impact",
            "orqlet_version": "0.2.0",
            "candidates_digest": data["candidates_digest"],
            "candidate_count": data["candidate_count"],
            "input": "pre-draft-tree",
            "views": ["committed:HEAD"],
            "index_state": "not-used",
        },
        "entries": entries,
    }
    document.update(over)
    return document


def resolve_all(world: ValidateServices) -> list[dict[str, Any]]:
    listed = knowledge_impact(world, "demo", "P-1", BASE, "HEAD").data["candidates"]
    assert isinstance(listed, list)
    entries = []
    for index, item in enumerate(listed, start=1):
        base: dict[str, Any] = {"id": f"K-{index}", "candidate_ref": item["id"], "scope": "project"}
        if item["kind"] == "reference":
            entries.append(
                {
                    **base,
                    "action": "correct",
                    "path": "docs/knowledge/service.md",
                    "claims": [{"id": "CL-1", "anchor": "## Orders", "evidence": [evidence()]}],
                }
            )
        else:
            entries.append(
                {**base, "action": "unaffected", "reason": "Covered.", "evidence": [evidence()]}
            )
    return entries


def draft_files() -> dict[str, bytes]:
    return after_change(docs__knowledge__service=DOC + "\n## Orders\n\nAbout orders.\n")


def validate(world: ValidateServices) -> ValidationResult:
    return validate_knowledge(world, RECORD, RecordOptions(BASE, "HEAD"))


def codes(result: ValidationResult) -> list[str]:
    return sorted(f.code for f in result.findings)


def sound() -> tuple[ValidateServices, list[dict[str, Any]]]:
    world = services(files(), draft_files())
    entries = resolve_all(world)
    return services(files(), draft_files(), record(world, entries)), entries


def test_a_record_that_resolves_every_candidate_with_evidence_that_holds_has_no_errors() -> None:
    world = services(files(), draft_files())
    document = record(world, resolve_all(world))
    # a real hash for the cited line, as `orqlet evidence cite` prints it
    from orqlet.domain.facts import line_range_hash

    for entry in document["entries"]:
        for ev in [
            *entry.get("evidence", []),
            *(e for c in entry.get("claims", []) for e in c["evidence"]),
        ]:
            ev["sha256"] = line_range_hash(CREATED.encode(), 1, 1)

    result = validate(services(files(), draft_files(), document))

    assert [c for c in codes(result) if c.startswith("ORQ-E")] == []


def test_fm_k04_an_unresolved_candidate_a_foreign_ref_and_a_double_resolution_are_errors() -> None:
    world = services(files(), draft_files())
    entries = resolve_all(world)
    dropped = [entry for entry in entries if entry["action"] == "correct"]
    foreign = [*entries, {**entries[0], "id": "K-9", "candidate_ref": "cand-unknown000"}]
    twice = [*entries, {**entries[0], "id": "K-9"}]

    assert "ORQ-E423" in codes(validate(services(files(), draft_files(), record(world, dropped))))
    assert "ORQ-E421" in codes(validate(services(files(), draft_files(), record(world, foreign))))
    assert "ORQ-E422" in codes(validate(services(files(), draft_files(), record(world, twice))))


def test_a_stale_candidate_list_is_not_run() -> None:
    world = services(files(), draft_files())
    document = record(world, resolve_all(world))
    document["analysis"]["candidates_digest"] = HASH

    result = validate(services(files(), draft_files(), document))

    assert "ORQ-W420" in codes(result)
    assert result.verdict is Verdict.NOT_RUN


def no_impact(world: ValidateServices, **block: Any) -> dict[str, Any]:
    listed = knowledge_impact(world, "demo", "P-1", BASE, "HEAD").data["candidates"]
    assert isinstance(listed, list)
    entries = [
        {
            "id": f"K-{i}",
            "candidate_ref": item["id"],
            "action": "unaffected",
            "scope": "project",
            "reason": "Nothing to say.",
            "evidence": [evidence()],
        }
        for i, item in enumerate(listed, start=1)
    ]
    block = {
        "category": "mechanical-dependency-change",
        "reason": "Only a version moved.",
        "absence_record": {
            "scopes_searched": ["project"],
            "views": ["committed:HEAD"],
            "revision": BASE,
            "method": "read the shared sources",
            "index_state": "not-used",
            "candidates_found": len(listed),
        },
        **block,
    }
    return record(world, entries, outcome="no-impact", no_impact=block)


def test_fm_k03_a_justified_no_impact_record_is_accepted() -> None:
    world = services(files(), after_change())

    result = validate(services(files(), after_change(), no_impact(world)))

    assert [c for c in codes(result) if c.startswith("ORQ-E")] == []


def test_a_refactor_category_is_refused_while_a_public_symbol_delta_exists() -> None:
    world = services(files(), after_change())

    result = validate(
        services(files(), after_change(), no_impact(world, category="internal-refactor"))
    )

    assert "ORQ-E424" in codes(result)


def test_the_absence_record_must_count_the_candidates_the_analysis_found() -> None:
    world = services(files(), after_change())
    document = no_impact(world)
    document["no_impact"]["absence_record"]["candidates_found"] = 0

    assert "ORQ-E425" in codes(validate(services(files(), after_change(), document)))


def test_a_draft_must_be_in_the_tree_inside_the_scope_and_carry_its_anchor() -> None:
    world, entries = sound()
    missing_anchor = after_change(docs__knowledge__service="# Service\n\nNo orders here.\n")
    outside = copy.deepcopy(entries)
    outside[0]["path"] = "docs/elsewhere/service.md"
    gone = copy.deepcopy(entries)
    gone[0]["path"] = "docs/knowledge/gone.md"

    assert "ORQ-E428" in codes(validate(services(files(), missing_anchor, record(world, entries))))
    assert "ORQ-E426" in codes(validate(services(files(), draft_files(), record(world, outside))))
    assert "ORQ-E427" in codes(validate(services(files(), draft_files(), record(world, gone))))


def test_a_removed_item_must_leave_no_dangling_reference() -> None:
    other = "# Other\n\nSee [the service](service.md).\n"
    before = files(docs__knowledge__other=other)
    after = after_change(docs__knowledge__other=other)
    del after["docs/knowledge/service.md"]
    world = services(before, after)
    entries = resolve_all(world)
    entries[0] = {
        "id": "K-1",
        "candidate_ref": entries[0]["candidate_ref"],
        "action": "remove",
        "scope": "project",
        "path": "docs/knowledge/service.md",
        "reason": "The feature is gone.",
        "evidence": [evidence()],
    }

    result = validate(services(before, after, record(world, entries)))

    assert "ORQ-E430" in codes(result)


def test_evidence_that_needs_ci_or_a_source_is_not_run_and_a_statement_is_flagged() -> None:
    world, entries = sound()
    document = record(world, entries)
    document["entries"][0]["claims"][0]["evidence"] = [
        {"kind": "test", "ref": "tests/test_a.py::test_x", "sha256": HASH},
        {"kind": "developer-statement", "ref": "ada", "sha256": HASH},
    ]

    result = validate(services(files(), draft_files(), document))

    assert "ORQ-W432" in codes(result)
    assert any("offline run cannot confirm" in reason for reason in result.not_run)


def test_a_record_cannot_cite_an_evidence_record_as_evidence() -> None:
    world, entries = sound()
    document = record(world, entries)
    document["entries"][0]["claims"][0]["evidence"] = [evidence(f"{TASK_DIR}/tests/P-1.yaml:1")]

    assert "ORQ-E435" in codes(validate(services(files(), draft_files(), document)))


def test_evidence_that_does_not_resolve_is_an_error() -> None:
    world, entries = sound()
    document = record(world, entries)
    document["entries"][0]["claims"][0]["evidence"][0]["sha256"] = HASH

    result = validate(services(files(), draft_files(), document))  # a hash that is not the line's

    assert "ORQ-E431" in codes(result)


def test_a_copied_run_of_source_and_a_near_duplicate_are_flagged_not_failed() -> None:
    source = "\n".join(f"    value_{n} = compute({n})" for n in range(12)) + "\n"
    drafted = DOC + "\n## Orders\n\n" + source
    near = (
        "# Copy\n\nThe code lives in `src/pkg/service.py` and nothing else matters here at all.\n"
    )
    before = files(docs__knowledge__near=near)
    after = after_change(
        **{"src__pkg__service.py": CREATED + source, "docs__knowledge__service.md": drafted}
    )
    after["docs/knowledge/near.md"] = near.encode()
    world = services(before, after)
    document = record(world, resolve_all(world))

    result = validate(services(before, after, document))

    assert "ORQ-W433" in codes(result)
    assert {"ORQ-W433"} <= {c for c in codes(result) if c.startswith("ORQ-W")}


def test_an_unexplained_edit_inside_the_knowledge_scope_is_an_error() -> None:
    world, entries = sound()
    extra = draft_files()
    extra["docs/knowledge/extra.md"] = b"# Extra\n"

    assert "ORQ-E429" in codes(validate(services(files(), extra, record(world, entries))))
