"""The evidence record contracts: what they accept, what they refuse and why (proposal 17.11)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts import CONTRACTS
from orqlet.application.contracts.loading import load_contract
from orqlet.application.ports.documents import DocumentError

pytestmark = pytest.mark.contract

VALID = Path(__file__).resolve().parents[1] / "fixtures" / "contracts" / "valid"
RECORD_IDS = [
    "orqlet.finding/v1",
    "orqlet.review-input/v1",
    "orqlet.review-result/v1",
    "orqlet.test-record/v1",
    "orqlet.knowledge-impact/v1",
    "orqlet.module-card/v1",
    "orqlet.knowledge/v2",
    "orqlet.docs-map/v1",
]
HASH = "a" * 64
OID = "b" * 40


def fixture(schema_id: str) -> dict[str, Any]:
    loaded = yaml.safe_load((VALID / (schema_id.replace("/", ".") + ".yaml")).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def rejects(schema_id: str, data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        CONTRACTS[schema_id].model_validate(data)


@pytest.mark.parametrize("schema_id", RECORD_IDS)
def test_the_fixtures_load_through_the_strict_loader_and_refuse_anchors_and_tags(
    schema_id: str,
) -> None:
    text = (VALID / (schema_id.replace("/", ".") + ".yaml")).read_text("utf-8")
    model = CONTRACTS[schema_id]

    load_contract(StrictYamlLoader(), model, text.encode(), source="t")
    with pytest.raises(DocumentError):
        load_contract(StrictYamlLoader(), model, ("anchor: &x 1\n" + text).encode(), source="t")
    with pytest.raises(DocumentError):
        load_contract(
            StrictYamlLoader(),
            model,
            text.replace("schema:", "x: !!binary AAAA\nschema:", 1).encode(),
            source="t",
        )


# --- review input ------------------------------------------------------------------------------
def test_the_binding_has_no_field_for_a_commit_a_tree_or_its_own_digest() -> None:
    for field in ("commit", "head_sha", "tree_oid", "self_digest"):
        data = fixture("orqlet.review-input/v1")
        data[field] = "x"

        rejects("orqlet.review-input/v1", data, field)


def test_the_components_are_exactly_the_covered_ones() -> None:
    data = fixture("orqlet.review-input/v1")
    del data["components"]["plan"]
    rejects("orqlet.review-input/v1", data, "exactly one digest per covered component")

    data = fixture("orqlet.review-input/v1")
    data["components"]["design"] = HASH
    rejects("orqlet.review-input/v1", data, "exactly one digest per covered component")

    data = fixture("orqlet.review-input/v1")
    data["covers"] = ["plan", "plan"]
    rejects("orqlet.review-input/v1", data, "covered twice")


def test_an_unknown_component_is_refused() -> None:
    data = fixture("orqlet.review-input/v1")
    data["covers"] = ["code_tests", "plan", "vibes"]

    rejects("orqlet.review-input/v1", data, "covers")


# --- findings ----------------------------------------------------------------------------------
def test_only_evidence_can_make_a_finding_and_an_observation_never_blocks() -> None:
    data = fixture("orqlet.finding/v1")
    data["evidence"] = []
    rejects("orqlet.finding/v1", data, "needs evidence")

    data = fixture("orqlet.finding/v1")
    data.update(kind="observation", evidence=[])
    rejects("orqlet.finding/v1", data, "never blocks")

    data = fixture("orqlet.finding/v1")
    data.update(kind="observation", evidence=[], severity="info")
    assert CONTRACTS["orqlet.finding/v1"].model_validate(data)


def test_evidence_is_a_quote_or_an_absence_record_and_nothing_else() -> None:
    data = fixture("orqlet.finding/v1")
    data["evidence"] = [{"kind": "hunch", "path": "a.py"}]
    rejects("orqlet.finding/v1", data, "evidence")

    data = fixture("orqlet.finding/v1")
    data["evidence"][1]["searched"] = []
    rejects("orqlet.finding/v1", data, "searched")


# --- review results ----------------------------------------------------------------------------
def test_a_pass_cannot_hold_a_blocking_finding_and_a_fail_needs_one() -> None:
    data = fixture("orqlet.review-result/v1")
    data["verdict"] = "PASS"
    rejects("orqlet.review-result/v1", data, "cannot hold a blocking finding")

    data = fixture("orqlet.review-result/v1")
    data["findings"][0]["severity"] = "non-blocking"
    rejects("orqlet.review-result/v1", data, "needs at least one blocking finding")


def test_an_i0_review_is_never_a_pass() -> None:
    data = fixture("orqlet.review-result/v1")
    data.update(verdict="PASS", independence="I0", findings=[])

    rejects("orqlet.review-result/v1", data, "never a PASS")


def test_a_review_covers_the_seven_components_that_a_review_covers() -> None:
    data = copy.deepcopy(fixture("orqlet.review-result/v1"))
    data["review_input"]["covers"].remove("design")
    del data["review_input"]["components"]["design"]

    rejects("orqlet.review-result/v1", data, "a review covers")


def test_a_no_impact_conclusion_needs_an_absence_record() -> None:
    data = fixture("orqlet.review-result/v1")
    data["applicability"] = {"examined": ["src/a.py"], "conclusion": "no-impact"}

    rejects("orqlet.review-result/v1", data, "needs an absence record")


def test_a_role_a_round_a_verdict_and_an_assurance_come_from_closed_sets() -> None:
    for field, value in (
        ("role", "coder"),
        ("round", 0),
        ("verdict", "MAYBE"),
        ("assurance", "guaranteed"),
        ("independence", "I4"),
        ("phase", "phase-1"),
    ):
        data = fixture("orqlet.review-result/v1")
        data[field] = value

        rejects("orqlet.review-result/v1", data, field)


def test_a_review_without_a_self_check_is_refused() -> None:
    data = fixture("orqlet.review-result/v1")
    del data["self_check"]

    rejects("orqlet.review-result/v1", data, "self_check")


def test_two_findings_cannot_share_an_id() -> None:
    data = fixture("orqlet.review-result/v1")
    data["findings"].append(copy.deepcopy(data["findings"][0]))

    rejects("orqlet.review-result/v1", data, "used twice")


# --- test records ------------------------------------------------------------------------------
def test_a_test_record_is_claimed_and_its_free_text_is_capped() -> None:
    data = fixture("orqlet.test-record/v1")
    data["evidence_kind"] = "verified"
    rejects("orqlet.test-record/v1", data, "evidence_kind")

    data = fixture("orqlet.test-record/v1")
    data["commands"][0]["summary"] = "x" * 2001
    rejects("orqlet.test-record/v1", data, "summary")


# --- knowledge impact --------------------------------------------------------------------------
def impact_entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": "K-2",
        "candidate_ref": "cand-2",
        "action": "unaffected",
        "scope": "project",
        "reason": "The behaviour did not change.",
        "evidence": [{"kind": "code", "ref": "src/a.py:1-3", "sha256": HASH}],
    }
    entry.update(overrides)
    return entry


def no_impact_block(**overrides: Any) -> dict[str, Any]:
    block: dict[str, Any] = {
        "category": "internal-refactor",
        "reason": "A rename inside one function.",
        "absence_record": {
            "scopes_searched": ["project"],
            "views": ["committed:HEAD"],
            "revision": OID,
            "method": "read the shared sources",
            "index_state": "not-used",
            "candidates_found": 1,
        },
    }
    block.update(overrides)
    return block


def test_evidence_of_kind_private_does_not_exist() -> None:
    data = fixture("orqlet.knowledge-impact/v1")
    data["entries"][0]["claims"][0]["evidence"][0]["kind"] = "private"

    rejects("orqlet.knowledge-impact/v1", data, "kind")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"path": None}, "needs a path"),
        ({"claims": []}, "at least one claim with evidence"),
        ({"action": "supersede"}, "`replaces`"),
        ({"action": "remove", "claims": [], "reason": None}, "a reason"),
        ({"action": "unaffected", "path": None, "claims": [], "reason": "x"}, "evidence"),
        ({"action": "proposal", "path": None, "claims": [], "reason": "x"}, "an owner"),
    ],
)
def test_each_action_needs_what_the_proposal_says_it_needs(
    changes: dict[str, Any], message: str
) -> None:
    data = fixture("orqlet.knowledge-impact/v1")
    data["entries"][0].update(changes)
    if changes.get("action") == "proposal":
        data["entries"].append({**data["entries"][0], "action": "add"})

    rejects("orqlet.knowledge-impact/v1", data, message)


def test_a_claim_needs_at_least_one_piece_of_evidence() -> None:
    data = fixture("orqlet.knowledge-impact/v1")
    data["entries"][0]["claims"][0]["evidence"] = []

    rejects("orqlet.knowledge-impact/v1", data, "evidence")


def test_updated_needs_a_writing_entry_and_a_proposal_never_satisfies_it() -> None:
    data = fixture("orqlet.knowledge-impact/v1")
    data["entries"] = [impact_entry(action="proposal", owner="team", evidence=[])]

    rejects("orqlet.knowledge-impact/v1", data, "a proposal never satisfies it")


def test_updated_cannot_carry_a_no_impact_block_and_no_impact_must_carry_one() -> None:
    data = fixture("orqlet.knowledge-impact/v1")
    data["no_impact"] = no_impact_block()
    rejects("orqlet.knowledge-impact/v1", data, "has no no_impact block")

    data = fixture("orqlet.knowledge-impact/v1")
    data.update(outcome="no-impact", entries=[impact_entry()])
    rejects("orqlet.knowledge-impact/v1", data, "needs its no_impact block")


def test_a_no_impact_outcome_lists_every_candidate_as_unaffected() -> None:
    ok = fixture("orqlet.knowledge-impact/v1")
    ok.update(outcome="no-impact", entries=[impact_entry()], no_impact=no_impact_block())
    assert CONTRACTS["orqlet.knowledge-impact/v1"].model_validate(ok)

    bad = copy.deepcopy(ok)
    bad["entries"].append(fixture("orqlet.knowledge-impact/v1")["entries"][0])
    rejects("orqlet.knowledge-impact/v1", bad, "lists every candidate as unaffected")


def test_a_no_impact_reason_comes_from_the_fixed_list_and_already_documented_needs_references() -> (
    None
):
    data = fixture("orqlet.knowledge-impact/v1")
    data.update(outcome="no-impact", entries=[impact_entry()])
    data["no_impact"] = no_impact_block(category="not worth writing")
    rejects("orqlet.knowledge-impact/v1", data, "category")

    data["no_impact"] = no_impact_block(category="already-documented")
    rejects("orqlet.knowledge-impact/v1", data, "references that already say it")


def test_entry_ids_are_unique() -> None:
    data = fixture("orqlet.knowledge-impact/v1")
    data["entries"].append(copy.deepcopy(data["entries"][0]))

    rejects("orqlet.knowledge-impact/v1", data, "used twice")


# --- module cards, configuration and the docs map ----------------------------------------------
def test_a_superseded_card_names_its_replacement() -> None:
    data = fixture("orqlet.module-card/v1")
    data["status"] = "superseded"

    rejects("orqlet.module-card/v1", data, "names the card that replaces it")


def test_a_card_cannot_reference_a_path_outside_the_repository() -> None:
    data = fixture("orqlet.module-card/v1")
    data["refs"] = ["../outside.md"]

    rejects("orqlet.module-card/v1", data, "refs")


def test_the_knowledge_configuration_refuses_globs_that_climb_and_unknown_kinds() -> None:
    data = fixture("orqlet.knowledge/v2")
    data["write_scope"][0]["globs"] = ["../x/**"]
    rejects("orqlet.knowledge/v2", data, "glob")

    data = fixture("orqlet.knowledge/v2")
    data["sources"][0]["kind"] = "wiki"
    rejects("orqlet.knowledge/v2", data, "kind")


def test_an_empty_knowledge_configuration_is_valid_and_is_what_init_seeds() -> None:
    data = {"schema": "orqlet.knowledge/v2"}

    model = CONTRACTS["orqlet.knowledge/v2"].model_validate(data)

    assert model.model_dump(mode="json", by_alias=True, exclude_none=True) == {
        "schema": "orqlet.knowledge/v2",
        "sources": [],
        "exclude": [],
        "write_scope": [],
    }


def test_the_docs_map_needs_code_docs_and_an_owner() -> None:
    for field in ("code", "docs", "owner"):
        data = fixture("orqlet.docs-map/v1")
        del data["targets"][0][field]

        rejects("orqlet.docs-map/v1", data, field)
