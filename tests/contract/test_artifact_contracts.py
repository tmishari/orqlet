"""The workflow artifact contracts: what they accept, what they refuse and why (proposal 17.11)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts import CONTRACTS
from orqlet.application.contracts.as_is import AsIsArtifact
from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.contracts.question_ledger import QuestionLedger
from orqlet.application.contracts.self_check import SelfCheck
from orqlet.application.ports.documents import DocumentError

pytestmark = pytest.mark.contract

VALID = Path(__file__).resolve().parents[1] / "fixtures" / "contracts" / "valid"
ARTIFACT_IDS = [
    "orqlet.artifact-header/v1",
    "orqlet.as-is/v1",
    "orqlet.as-is-fragment/v1",
    "orqlet.design-set/v1",
    "orqlet.implementation-plan/v1",
    "orqlet.question-ledger/v1",
    "orqlet.self-check/v1",
]


def fixture(schema_id: str) -> dict[str, Any]:
    name = schema_id.replace("/", ".") + ".yaml"
    loaded = yaml.safe_load((VALID / name).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def rejects(schema_id: str, data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        CONTRACTS[schema_id].model_validate(data)


@pytest.mark.parametrize("schema_id", ARTIFACT_IDS)
def test_a_yaml_anchor_or_an_unknown_tag_is_refused_by_the_loader(schema_id: str) -> None:
    text = (VALID / (schema_id.replace("/", ".") + ".yaml")).read_text("utf-8")
    model = CONTRACTS[schema_id]

    with pytest.raises(DocumentError):
        load_contract(StrictYamlLoader(), model, ("anchor: &x 1\n" + text).encode(), source="t")
    with pytest.raises(DocumentError):
        load_contract(
            StrictYamlLoader(),
            model,
            text.replace("schema:", "x: !!python/object:os.system\nschema:", 1).encode(),
            source="t",
        )


def test_the_fixtures_load_through_the_strict_loader_too() -> None:
    for schema_id in ARTIFACT_IDS:
        text = (VALID / (schema_id.replace("/", ".") + ".yaml")).read_bytes()
        load_contract(StrictYamlLoader(), CONTRACTS[schema_id], text, source=schema_id)


def test_a_fact_without_evidence_is_refused() -> None:
    data = fixture("orqlet.as-is/v1")
    data["facts"][0]["evidence"] = []

    rejects("orqlet.as-is/v1", data, "evidence")


def test_there_is_no_field_for_a_proposal() -> None:
    data = fixture("orqlet.as-is/v1")
    data["facts"][0]["recommendation"] = "split the module"

    rejects("orqlet.as-is/v1", data, "recommendation")


def test_the_limitation_goes_with_a_research_mode_that_is_not_parallel() -> None:
    data = fixture("orqlet.as-is/v1")
    data["limitation"] = None
    rejects("orqlet.as-is/v1", data, "needs a limitation")

    data = fixture("orqlet.as-is/v1")
    data["research_mode"] = "parallel-subagents"
    rejects("orqlet.as-is/v1", data, "only when research was not parallel")


def test_a_contradiction_names_at_least_two_sources() -> None:
    data = fixture("orqlet.as-is/v1")
    data["contradictions"][0]["sources"] = ["a.md"]

    rejects("orqlet.as-is/v1", data, "sources")


@pytest.mark.parametrize(
    "path", ["../outside.py", "/etc/passwd", "a\\b.py", "aux.py", ".git/config"]
)
def test_an_unsafe_path_is_refused_where_it_enters(path: str) -> None:
    data = fixture("orqlet.as-is/v1")
    data["facts"][0]["evidence"][0]["path"] = path

    rejects("orqlet.as-is/v1", data, "path")


@pytest.mark.parametrize("glob", ["../x/**", "/abs/**", "a\\b"])
def test_a_glob_cannot_leave_the_repository(glob: str) -> None:
    data = fixture("orqlet.as-is/v1")
    data["scope"]["paths"] = [glob]

    rejects("orqlet.as-is/v1", data, "glob")


def test_a_revision_is_a_full_object_id() -> None:
    data = fixture("orqlet.as-is/v1")
    data["base_revision"] = "main"

    rejects("orqlet.as-is/v1", data, "base_revision")


def test_a_pass_must_say_how_it_was_made() -> None:
    data = fixture("orqlet.self-check/v1")
    data["checks"][0]["how"] = " "

    rejects("orqlet.self-check/v1", data, "without saying how")
    assert SelfCheck.model_validate(fixture("orqlet.self-check/v1")).checks[1].result == "not-run"


def test_an_artifact_without_a_self_check_is_refused() -> None:
    for schema_id in ("orqlet.as-is/v1", "orqlet.design-set/v1", "orqlet.implementation-plan/v1"):
        data = fixture(schema_id)
        del data["self_check"]

        rejects(schema_id, data, "self_check")


def test_an_adr_that_is_not_required_has_no_file_and_every_other_kind_has_one() -> None:
    data = fixture("orqlet.design-set/v1")
    data["artifacts"][1]["path"] = "docs/x.md"
    rejects("orqlet.design-set/v1", data, "has no file")

    data = fixture("orqlet.design-set/v1")
    del data["artifacts"][0]["sha256"]
    rejects("orqlet.design-set/v1", data, "needs a path and a sha256")


def test_not_affected_needs_evidence() -> None:
    data = fixture("orqlet.design-set/v1")
    data["considerations"]["security"]["evidence_refs"] = []

    rejects("orqlet.design-set/v1", data, "needs evidence references")


def test_a_design_names_a_known_surface_and_a_known_class() -> None:
    data = fixture("orqlet.design-set/v1")
    data["expected_changes"][0]["surface"] = "everything"
    rejects("orqlet.design-set/v1", data, "surface")

    data = fixture("orqlet.design-set/v1")
    data["change_class"]["effective"] = "D4"
    rejects("orqlet.design-set/v1", data, "effective")


def test_review_evidence_is_always_all_three_roles_each_once() -> None:
    for evidence in (
        ["tester"],
        ["architecture-reviewer", "security-reviewer", "tester", "tester"],
    ):
        data = fixture("orqlet.implementation-plan/v1")
        data["phases"][0]["review_evidence"] = evidence

        rejects("orqlet.implementation-plan/v1", data, "review_evidence is always")


def test_the_knowledge_step_cannot_be_omitted_and_structural_changes_cannot_be_authored() -> None:
    data = fixture("orqlet.implementation-plan/v1")
    data["phases"][0]["knowledge_step"] = "optional"
    rejects("orqlet.implementation-plan/v1", data, "knowledge_step")

    data = fixture("orqlet.implementation-plan/v1")
    data["structural_changes"] = ["P-1: create x"]
    rejects("orqlet.implementation-plan/v1", data, "structural_changes")


def test_a_plan_needs_at_least_one_phase_and_an_id_in_the_agreed_form() -> None:
    data = fixture("orqlet.implementation-plan/v1")
    data["phases"] = []
    rejects("orqlet.implementation-plan/v1", data, "phases")

    data = fixture("orqlet.implementation-plan/v1")
    data["phases"][0]["id"] = "phase-one"
    rejects("orqlet.implementation-plan/v1", data, "id")


def test_an_answer_goes_with_the_answered_status_and_with_no_other() -> None:
    data = fixture("orqlet.question-ledger/v1")
    data["questions"][0]["answer"] = None
    rejects("orqlet.question-ledger/v1", data, "has no answer")

    data = fixture("orqlet.question-ledger/v1")
    data["questions"][1]["answer"] = data["questions"][0]["answer"]
    rejects("orqlet.question-ledger/v1", data, "has an answer but its status")


def test_a_conflict_needs_two_sources() -> None:
    data = fixture("orqlet.question-ledger/v1")
    data["conflicts"][0]["sources"] = data["conflicts"][0]["sources"][:1]

    rejects("orqlet.question-ledger/v1", data, "sources")


def test_contracts_are_frozen() -> None:
    plan = ImplementationPlan.model_validate(fixture("orqlet.implementation-plan/v1"))

    with pytest.raises(ValidationError):
        plan.base_revision = "c" * 40  # type: ignore[misc]


def test_the_fixtures_build_the_models_the_tests_import() -> None:
    assert AsIsArtifact.model_validate(fixture("orqlet.as-is/v1")).facts[0].id == "A-1"
    assert (
        DesignSet.model_validate(fixture("orqlet.design-set/v1")).expected_changes[0].id == "EC-1"
    )
    assert (
        QuestionLedger.model_validate(fixture("orqlet.question-ledger/v1")).questions[0].id == "Q-1"
    )
