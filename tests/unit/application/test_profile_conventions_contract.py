"""The additive convention facts of `orqlet.project-profile/v1` (task team-conventions-resources,
phase P-2).

Every test cites its `expected_behavior_source`. ADR-003 is the file `adr-003-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-6 are the acceptance criteria of phase P-2 in
docs/design/team-conventions-resources/plan.yaml.

These tests were written first, by the Tester of phase P-2, before the contract changed. They cover
AC-4 (an existing profile loads unchanged and its new facts are unknowns with questions); the
equality of the committed profile schema with the export is checked by
tests/contract/test_contracts.py.

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of the default questions, and whether the five questions differ from one another
  (only that each is not empty);
- whether the contract itself limits the answers (length, `text_problems`, at most 12 items):
  ADR-003 decision 2 applies those rules "when it is given" and "when it is rendered", which are
  later phases, and EC-60 declares plain facts;
- the order in which the profile writes its fields.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.common import Evidence, FactValue
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import (
    ProjectProfile,
    PullRequests,
    Repository,
    TargetBranch,
)

pytestmark = pytest.mark.unit

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.project-profile.v1.yaml"
)
LOADER = StrictYamlLoader()
HASH = "a" * 64

type FactPath = tuple[str, ...]

BRANCH_MODEL: FactPath = ("repository", "branch_model")
RELEASE_FLOW: FactPath = ("repository", "release_flow")
BRANCH_PATTERNS: FactPath = ("repository", "branch_patterns")
SHAPE: FactPath = ("repository", "pull_requests", "shape")
REQUIRED_CHECKS: FactPath = ("repository", "pull_requests", "required_checks")

# the five facts that EC-60 adds, with an answer that a maintainer could give
NEW_FACTS: dict[str, tuple[FactPath, str]] = {
    "branch_model": (BRANCH_MODEL, "gitflow"),
    "release_flow": (RELEASE_FLOW, "release branches are cut from develop and tagged on main"),
    "branch_patterns": (BRANCH_PATTERNS, "feature/*, fix/*, release/*"),
    "shape": (SHAPE, "one change per pull request, with a description of the why"),
    "required_checks": (REQUIRED_CHECKS, "lint, tests, security scan"),
}
LIST_FACTS: dict[str, FactPath] = {
    "branch_patterns": BRANCH_PATTERNS,
    "required_checks": REQUIRED_CHECKS,
}


# --- helpers --------------------------------------------------------------------------------------


def parametrized(name: str, cases: Mapping[str, object]) -> pytest.MarkDecorator:
    """`pytest.mark.parametrize` over the values of a mapping, with its keys as test ids."""
    return pytest.mark.parametrize(name, list(cases.values()), ids=list(cases))


def raw_profile() -> dict[str, Any]:
    """The valid profile fixture as plain data, which a test may change freely."""
    loaded = LOADER.load(FIXTURE.read_bytes(), source="fixture")
    assert isinstance(loaded, dict)
    return copy.deepcopy(cast("dict[str, Any]", loaded))


def with_value(path: FactPath, value: object) -> dict[str, Any]:
    """The fixture with `value` set at `path`, a dotted way into the document."""
    data = raw_profile()
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return data


def fact_at(profile: ProjectProfile, path: FactPath) -> FactValue:
    node: object = profile
    for name in path:
        node = getattr(node, name)
    assert isinstance(node, FactValue)
    return node


def answered(value: str) -> dict[str, Any]:
    return {"value": value, "answered_by": "maintainer"}


def old_profile() -> ProjectProfile:
    """The profile fixture, written before the five facts existed."""
    return load_contract(LOADER, ProjectProfile, FIXTURE.read_bytes(), source="fixture")


# --- AC-4: a profile written before this change still loads ---------------------------------------


def test_the_profile_fixture_has_none_of_the_new_fields() -> None:
    """AC-4. expected_behavior_source: AC-4 ("an existing profile fixture loads unchanged") - the
    fixture is the profile as it was written before this change, so none of the five keys is in
    it."""
    repository = raw_profile()["repository"]

    assert not {"branch_model", "release_flow", "branch_patterns"} & set(repository)
    assert not {"shape", "required_checks"} & set(repository["pull_requests"])


def test_an_existing_profile_still_loads_with_its_values_unchanged() -> None:
    """AC-4. expected_behavior_source: AC-4 ("an existing profile fixture loads unchanged"),
    ADR-003 decision 1 ("an existing profile still loads") and EC-60."""
    profile = old_profile()
    repository = profile.repository

    assert repository.target_branch.value == "main"
    assert repository.target_branch.remote == "origin"
    assert repository.target_branch.answered_by == "maintainer"
    assert repository.branch_naming.value is None
    assert repository.commit_convention.value is None
    assert repository.pull_requests.template.targets == (".github/pull_request_template.md",)
    assert repository.pull_requests.template.status == "team-template-unknown"
    assert profile.profile.status == "draft"


@parametrized("path", {name: path for name, (path, _) in NEW_FACTS.items()})
def test_each_new_fact_of_an_existing_profile_is_an_unknown_with_its_question(
    path: FactPath,
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("its new facts are unknowns with questions"),
    ADR-003 decision 1 ("All five are `FactValue`, each with a default that is an unknown with its
    question") and EC-60."""
    fact = fact_at(old_profile(), path)

    assert fact.value is None
    assert fact.question is not None
    assert fact.question.strip()
    assert fact.evidence == ()
    assert fact.answered_by is None


def test_the_new_facts_have_defaults_when_the_classes_are_built_without_them() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 and EC-60 (the fields are optional and
    default to an unknown with its question)."""
    repository = Repository(
        target_branch=TargetBranch(value="main", answered_by="maintainer"),
        branch_naming=FactValue(question="Is there a branch naming rule?"),
        commit_convention=FactValue(question="Is there a commit convention?"),
    )

    facts = [
        repository.branch_model,
        repository.release_flow,
        repository.branch_patterns,
        repository.pull_requests.shape,
        repository.pull_requests.required_checks,
    ]
    for fact in facts:
        assert isinstance(fact, FactValue)
        assert fact.value is None
        assert fact.question
    assert repository.pull_requests == PullRequests()


def test_the_version_of_the_contract_stays_v1() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 ("an additive, minor change under
    Section 20.2, so the contract stays `v1`") and EC-60 ("the version stays v1")."""
    dumped = old_profile().model_dump(mode="json", by_alias=True)

    assert dumped["schema"] == "orqlet.project-profile/v1"
    with pytest.raises(ValidationError):
        ProjectProfile.model_validate({**raw_profile(), "schema": "orqlet.project-profile/v2"})


def test_merge_strategy_and_reviewers_keep_their_type_and_their_unanswered_text() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 ("`merge_strategy` and `reviewers` keep
    their type; the text `unknown` is their unanswered state") and EC-60."""
    pull_requests = old_profile().repository.pull_requests

    assert pull_requests.merge_strategy == "unknown"
    assert pull_requests.reviewers == "unknown"


def test_merge_strategy_and_reviewers_still_take_a_plain_text() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 and EC-60 (they keep their type: a
    string)."""
    data = raw_profile()
    data["repository"]["pull_requests"]["merge_strategy"] = "squash"
    data["repository"]["pull_requests"]["reviewers"] = "two reviewers"

    pull_requests = ProjectProfile.model_validate(data).repository.pull_requests

    assert pull_requests.merge_strategy == "squash"
    assert pull_requests.reviewers == "two reviewers"


@pytest.mark.parametrize("field", ["merge_strategy", "reviewers"])
def test_merge_strategy_and_reviewers_do_not_become_facts(field: str) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 and EC-60 ("`merge_strategy` and
    `reviewers` keep their type": a fact written as a mapping is not their type)."""
    data = with_value(("repository", "pull_requests", field), answered("squash"))

    with pytest.raises(ValidationError):
        ProjectProfile.model_validate(data)


def test_an_old_profile_dumped_and_loaded_again_is_the_same_profile() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 (the new facts have defaults that a
    rewritten profile carries) and the round trip that tests/contract/test_contracts.py asserts
    for every fixture."""
    profile = old_profile()

    dumped = profile.model_dump(mode="json", by_alias=True)

    assert ProjectProfile.model_validate(dumped) == profile


# --- an answered fact -----------------------------------------------------------------------------


@parametrized("case", NEW_FACTS)
def test_each_new_field_accepts_an_answer_of_the_maintainer(case: tuple[FactPath, str]) -> None:
    """AC-4. expected_behavior_source: plan P-2 file operation on
    test_profile_conventions_contract.py ("each new field accepts an answered FactValue"),
    ADR-003 decision 1 and EC-60."""
    path, text = case

    profile = ProjectProfile.model_validate(with_value(path, answered(text)))

    fact = fact_at(profile, path)
    assert (fact.value, fact.answered_by) == (text, "maintainer")
    assert fact.question is None


@parametrized("case", NEW_FACTS)
def test_each_new_field_accepts_a_value_with_evidence(case: tuple[FactPath, str]) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 (all five are `FactValue`, and a
    `FactValue` allows a value that has evidence) and EC-60."""
    path, text = case
    evidence = {"path": "CONTRIBUTING.md", "lines": "10-12", "sha256": HASH}

    profile = ProjectProfile.model_validate(
        with_value(path, {"value": text, "evidence": [evidence]})
    )

    fact = fact_at(profile, path)
    assert fact.value == text
    assert fact.evidence == (Evidence(path="CONTRIBUTING.md", lines="10-12", sha256=HASH),)


@parametrized("case", NEW_FACTS)
def test_the_answer_none_is_a_recorded_value_and_not_an_unknown(case: tuple[FactPath, str]) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 2 ("The answer `none` is a recorded value
    that means 'the team has no rule'; it is no longer unknown")."""
    path, _ = case

    profile = ProjectProfile.model_validate(with_value(path, answered("none")))

    fact = fact_at(profile, path)
    assert fact.value == "none"
    assert fact.answered_by == "maintainer"


@parametrized("case", NEW_FACTS)
def test_an_answered_profile_dumped_and_loaded_again_keeps_the_answer(
    case: tuple[FactPath, str],
) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 (the answers are profile facts, which
    `profile answer` rewrites) and EC-60."""
    path, text = case
    profile = ProjectProfile.model_validate(with_value(path, answered(text)))

    reloaded = ProjectProfile.model_validate(profile.model_dump(mode="json", by_alias=True))

    assert reloaded == profile
    assert fact_at(reloaded, path).value == text


def test_all_five_answers_can_be_given_together() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 and EC-60 (five independent fields)."""
    data = raw_profile()
    for path, text in NEW_FACTS.values():
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = answered(text)

    profile = ProjectProfile.model_validate(data)

    for path, text in NEW_FACTS.values():
        assert fact_at(profile, path).value == text


# --- the facts follow the rules of every fact -----------------------------------------------------


@parametrized("case", NEW_FACTS)
def test_a_new_fact_with_a_value_and_no_evidence_or_answer_is_refused(
    case: tuple[FactPath, str],
) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 (all five are `FactValue`) and the rule
    of `FactValue` ("a fact needs evidence or an answer from the maintainer"). The answered form
    of the same fact is accepted first, so that the refusal is the rule's and not the absence of
    the field."""
    path, text = case
    ProjectProfile.model_validate(with_value(path, answered(text)))

    with pytest.raises(ValidationError):
        ProjectProfile.model_validate(with_value(path, {"value": text}))


@parametrized("case", NEW_FACTS)
def test_a_new_fact_with_no_value_and_no_question_is_refused(case: tuple[FactPath, str]) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 (all five are `FactValue`) and the rule
    of `FactValue` ("an unknown fact needs a question"). The unknown with its question is accepted
    first, so that the refusal is the rule's and not the absence of the field."""
    path, _ = case
    ProjectProfile.model_validate(with_value(path, {"value": None, "question": "Which one?"}))

    with pytest.raises(ValidationError):
        ProjectProfile.model_validate(with_value(path, {"value": None}))


@parametrized("path", LIST_FACTS)
def test_a_list_is_comma_separated_text_and_not_a_yaml_list(path: FactPath) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 ("a list is stored as one
    comma-separated text") and EC-60 ("the lists are comma-separated text inside the fact"). The
    comma-separated text is accepted first, so that the refusal is the type's and not the absence
    of the field."""
    ProjectProfile.model_validate(with_value(path, answered("feature/*, fix/*")))

    with pytest.raises(ValidationError):
        ProjectProfile.model_validate(
            with_value(path, {"value": ["feature/*", "fix/*"], "answered_by": "maintainer"})
        )


@parametrized("case", NEW_FACTS)
def test_a_new_fact_refuses_a_field_that_a_fact_does_not_have(case: tuple[FactPath, str]) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 (the contract is closed) and the closed
    `FactValue`. The fact without the extra field is accepted first, so that the refusal is the
    closed contract's and not the absence of the field."""
    path, text = case
    ProjectProfile.model_validate(with_value(path, answered(text)))

    with pytest.raises(ValidationError):
        ProjectProfile.model_validate(with_value(path, {**answered(text), "surprise": 1}))


# --- the contract stays closed --------------------------------------------------------------------


@parametrized(
    "path",
    {
        "repository": ("repository", "surprise"),
        "repository-near-miss": ("repository", "branch_models"),
        "pull-requests": ("repository", "pull_requests", "surprise"),
        "pull-requests-near-miss": ("repository", "pull_requests", "shapes"),
        "profile": ("surprise",),
    },
)
def test_an_unknown_extra_field_is_refused(path: FactPath) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 ("an older Orqlet refuses a new one (the
    contract is closed ...)") and EC-60 ("an unknown extra field is refused")."""
    with pytest.raises(ValidationError):
        ProjectProfile.model_validate(with_value(path, answered("x")))


@pytest.mark.parametrize("field", ["branch_model", "release_flow", "branch_patterns"])
def test_the_new_repository_fields_are_optional_in_the_schema(field: str) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 and EC-60 (additive optional fields with
    defaults, "a minor change under Section 20.2": a field that the schema requires would make
    every existing profile invalid)."""
    definition = ProjectProfile.model_json_schema(by_alias=True)["$defs"]["Repository"]

    assert field in definition["properties"]
    assert field not in definition.get("required", [])


@pytest.mark.parametrize("field", ["shape", "required_checks"])
def test_the_new_pull_request_fields_are_optional_in_the_schema(field: str) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 1 and EC-60 (additive optional fields with
    defaults)."""
    definition = ProjectProfile.model_json_schema(by_alias=True)["$defs"]["PullRequests"]

    assert field in definition["properties"]
    assert field not in definition.get("required", [])
