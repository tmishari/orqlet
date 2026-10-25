"""`validate as-is`: facts only, evidence that resolves, uncertainty kept (proposal 17.3)."""

from __future__ import annotations

from typing import Any

import pytest

from orqlet.application.usecases.validate_as_is import AsIsOptions, validate_as_is
from orqlet.application.usecases.validation import ValidationResult
from orqlet.domain.findings import Verdict
from tests.support.artifacts import (
    AS_IS,
    BASE,
    LATER,
    LEDGER,
    SOURCE,
    World,
    as_is,
    evidence,
    fact,
    happy_task,
    ledger,
    make_world,
    question,
    with_front_matter,
)

pytestmark = pytest.mark.unit


def run(
    world: World, document: dict[str, Any], *, body: str = "", options: AsIsOptions | None = None
) -> ValidationResult:
    world.put(AS_IS, with_front_matter(document, body))
    return validate_as_is(world.services(), AS_IS, options)


def codes(result: ValidationResult) -> list[str]:
    return [finding.code for finding in result.findings]


def test_a_sound_file_passes_and_its_summary_leads_with_the_uncertainty() -> None:
    result = run(make_world(), as_is())

    assert result.verdict is Verdict.PASS
    assert codes(result) == []
    assert result.data["facts"] == 2
    assert (result.data["unknowns"], result.data["material_unknowns"]) == (1, 1)
    assert result.data["contradictions"] == 0


def test_validation_never_writes() -> None:
    world = make_world()
    world.put(AS_IS, with_front_matter(as_is()))
    before = world.project.snapshot()

    validate_as_is(world.services(), AS_IS)

    assert world.project.snapshot() == before


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda d: d["facts"][0]["evidence"][0].update(sha256="0" * 64), "ORQ-E335"),
        (lambda d: d["facts"][0]["evidence"][0].update(lines="40-45"), "ORQ-E334"),
        (lambda d: d["facts"][0]["evidence"][0].update(path="src/pkg/gone.py"), "ORQ-E333"),
        (lambda d: d["facts"][0]["evidence"][0].update(revision=LATER), "ORQ-E332"),
    ],
)
def test_evidence_that_does_not_resolve_at_the_bound_revision_fails(mutate: Any, code: str) -> None:
    document = as_is()
    mutate(document)

    result = run(make_world(), document)

    assert result.verdict is Verdict.FAIL
    assert code in codes(result)


def test_an_unknown_revision_is_not_run_and_never_a_pass() -> None:
    result = run(make_world(commits=False), as_is())

    assert result.verdict is Verdict.NOT_RUN
    assert codes(result) == []
    assert "not in this repository" in result.not_run[0]


def test_a_file_without_facts_proves_nothing() -> None:
    result = run(make_world(), as_is(facts=[]))

    assert result.verdict is Verdict.NOT_RUN
    assert "no facts" in result.not_run[0]


def test_the_size_budget_counts_facts_and_never_unknowns_or_contradictions() -> None:
    long_unknown = {"id": "U-2", "what": "word " * 300, "material": False}
    ok = run(make_world(), as_is(unknowns=[long_unknown]))
    over = run(make_world(), as_is(size_budget={"max_words": 3}))

    assert ok.verdict is Verdict.PASS
    assert "ORQ-E337" in codes(over)


def test_advice_in_a_fact_or_in_the_text_is_flagged_but_does_not_fail_the_file() -> None:
    document = as_is(facts=[fact(1, "The module should be split into two.")])

    result = run(make_world(), document, body="We recommend a rewrite.")

    assert result.verdict is Verdict.PASS
    assert codes(result) == ["ORQ-W338", "ORQ-W338"]


def test_ids_are_unique_within_their_kind() -> None:
    document = as_is(facts=[fact(1), fact(1, "Another fact.", start=5, end=6)])

    assert "ORQ-E336" in codes(run(make_world(), document))


def test_the_header_and_the_body_agree_on_the_base_revision_and_the_task() -> None:
    document = as_is()
    document["header"]["bound"]["base_revision"] = LATER
    assert "ORQ-E330" in codes(run(make_world(), document))

    other_task = as_is(task="other")
    assert codes(run(make_world(), other_task)).count("ORQ-E331") == 2


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"no front matter at all\n", "ORQ-E324"),
        (b"---\nschema: orqlet.as-is/v1\n---\n", "ORQ-E325"),
        (b"---\nanchor: &a 1\nschema: orqlet.as-is/v1\n---\n", "ORQ-E325"),
        (b"x" * (512 * 1024 + 1), "ORQ-E323"),
    ],
)
def test_a_file_that_cannot_be_trusted_is_reported_not_crashed_on(data: bytes, code: str) -> None:
    world = make_world()
    world.put(AS_IS, data)

    result = validate_as_is(world.services(), AS_IS)

    assert result.verdict is Verdict.FAIL
    assert codes(result) == [code]


def test_a_missing_file_and_an_unsafe_path_are_findings() -> None:
    world = make_world()

    assert [
        f.code for f in validate_as_is(world.services(), "docs/design/demo/as-is.md").findings
    ] == ["ORQ-E321"]
    assert [f.code for f in validate_as_is(world.services(), "../outside.md").findings] == [
        "ORQ-E320"
    ]


def test_a_validation_error_names_the_field_and_not_the_value() -> None:
    document = as_is()
    document["facts"][0]["statement"] = ""

    result = run(make_world(), document)

    message = result.findings[0].message
    assert "facts.0.statement" in message


def test_an_unknown_cites_a_question_that_must_exist_in_the_ledger() -> None:
    world = make_world()
    world.put_yaml(LEDGER, ledger())
    document = as_is(unknowns=[{"id": "U-1", "what": "x", "material": True, "question_ref": "Q-9"}])

    assert "ORQ-E339" in codes(run(world, document))


def test_without_a_ledger_a_question_reference_is_only_a_warning() -> None:
    document = as_is(unknowns=[{"id": "U-1", "what": "x", "material": True, "question_ref": "Q-1"}])

    result = run(make_world(), document)

    assert (result.verdict, codes(result)) == (Verdict.PASS, ["ORQ-W339"])


def test_an_open_question_that_blocks_research_fails_the_file() -> None:
    world = make_world()
    world.put_yaml(LEDGER, ledger(questions=[question(1, blocks=["research"])]))

    result = run(world, as_is())

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E345" in codes(result)


def test_an_answered_question_blocks_nothing() -> None:
    world = make_world()
    happy_task(world)

    assert validate_as_is(world.services(), AS_IS).verdict is Verdict.PASS


FRAGMENT = {
    "schema": "orqlet.as-is-fragment/v1",
    "fragment_id": "cli-area",
    "base_revision": BASE,
    "scope": {"paths": ["src/**"], "request_ref": "demo"},
    "facts": [],
    "unknowns": [{"id": "U-1", "what": "Whether exit codes are stable", "material": False}],
    "contradictions": [{"id": "C-1", "sources": ["a.md", "b.md"], "note": "Two defaults"}],
}


def fragments_world() -> World:
    world = make_world()
    world.put_yaml("scratch/fragments/cli-area.yaml", FRAGMENT)
    return world


def test_an_unknown_or_contradiction_of_a_fragment_cannot_be_dropped() -> None:
    options = AsIsOptions(fragments_dir="scratch/fragments")

    result = run(fragments_world(), as_is(), options=options)

    assert [f.code for f in result.findings] == ["ORQ-E340", "ORQ-E340"]
    assert "cli-area/U-1" in result.findings[0].message


def test_a_fragment_entry_is_kept_when_it_is_named_in_merged_from_or_repeated_verbatim() -> None:
    document = as_is(
        unknowns=[
            {
                "id": "U-1",
                "what": "Merged entry",
                "material": False,
                "merged_from": ["cli-area/U-1"],
            }
        ],
        contradictions=[
            {"id": "C-1", "sources": ["a.md", "b.md"], "note": "Two defaults"}  # verbatim
        ],
    )

    result = run(
        fragments_world(), document, options=AsIsOptions(fragments_dir="scratch/fragments")
    )

    assert result.verdict is Verdict.PASS


def test_a_fragments_folder_that_is_not_there_or_is_empty_is_reported() -> None:
    missing = run(make_world(), as_is(), options=AsIsOptions(fragments_dir="scratch/none"))
    assert "ORQ-E321" in codes(missing)

    world = make_world()
    world.project.add_dir("scratch/empty")
    empty = run(world, as_is(), options=AsIsOptions(fragments_dir="scratch/empty"))
    assert empty.verdict is Verdict.NOT_RUN


def test_the_scope_is_stale_when_a_file_in_it_changed_since_the_base_revision() -> None:
    changed = dict(make_world().vcs._revisions[BASE])
    changed["src/pkg/mod.py"] = SOURCE + b"# edited\n"
    world = make_world(other_revisions={LATER: changed})

    result = run(world, as_is(), options=AsIsOptions(against=LATER))

    assert result.verdict is Verdict.NOT_RUN
    assert codes(result) == ["ORQ-W341"]
    assert "src/pkg/mod.py" in result.findings[0].message


def test_a_moved_head_that_leaves_the_scope_alone_is_fine() -> None:
    changed = dict(make_world().vcs._revisions[BASE])
    changed["docs/guide.md"] = b"# Guide, edited\n"
    world = make_world(other_revisions={LATER: changed})

    result = run(world, as_is(), options=AsIsOptions(against=LATER))

    assert result.verdict is Verdict.PASS


def test_comparing_with_a_revision_that_does_not_exist_is_not_run() -> None:
    result = run(make_world(), as_is(), options=AsIsOptions(against="f" * 40))

    assert result.verdict is Verdict.NOT_RUN


def test_evidence_helper_agrees_with_the_domain_hash() -> None:
    assert evidence()["lines"] == "1-2"
