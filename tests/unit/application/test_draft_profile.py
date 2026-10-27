from pathlib import Path

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.scan.python_scanner import PythonScanner
from orqlet.application.contracts.common import FactValue
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.usecases.draft_profile import draft_profile, open_questions
from tests.support.trees import repo, with_files

pytestmark = pytest.mark.unit

SCANNERS = (PythonScanner(),)
PROJECT_ID = "00000000-0000-4000-8000-000000000001"


def draft(name: str, **kwargs: object):  # type: ignore[no-untyped-def]
    return draft_profile(
        repo(name),
        SCANNERS,
        project_id=PROJECT_ID,
        name=name,
        origin="existing",
        orqlet_version="0.1.0",
        **kwargs,  # type: ignore[arg-type]
    )


def test_a_python_project_gets_a_supported_draft_with_facts() -> None:
    result = draft("uv_fastapi")

    assert result.profile.stack.support == "supported"
    assert result.profile.facts.package_manager.value == "uv"
    assert result.profile.project.kind == "python-service"
    assert result.profile.profile.status == "draft"


def test_the_draft_validates_against_its_own_contract_after_a_round_trip() -> None:
    profile = draft("uv_fastapi").profile

    dumped = profile.model_dump(mode="json", by_alias=True)

    assert ProjectProfile.model_validate(dumped) == profile


def test_things_a_repository_cannot_say_become_questions_never_values() -> None:
    result = draft("uv_fastapi")

    ids = [q.id for q in result.questions]
    assert ids == [
        "repository.target_branch",
        "repository.branch_naming",
        "repository.commit_convention",
    ]
    assert result.profile.repository.target_branch.value is None


def test_a_javascript_only_repository_gets_a_capability_limit_and_no_guess() -> None:
    result = draft("js_only")

    stack = result.profile.stack
    assert stack.support == "unsupported"
    assert any("JavaScript or TypeScript" in limit for limit in stack.capability_limits)
    assert result.profile.facts.python.value is None
    assert result.profile.facts.frameworks == ()
    assert result.profile.dependencies.declared == ()
    assert {"facts.python", "facts.package_manager"} <= {q.id for q in result.questions}


def test_an_empty_repository_is_unknown_not_unsupported() -> None:
    result = draft("empty")

    assert result.profile.stack.support == "unknown"
    assert result.profile.facts.python.value is None


def test_an_existing_prompts_directory_is_listed_as_a_source() -> None:
    fs = with_files({"pyproject.toml": "[project]\nname='x'\n", ".prompts/README.md": "hi"})

    result = draft_profile(
        fs, SCANNERS, project_id=PROJECT_ID, name="x", origin="existing", orqlet_version="0.1.0"
    )

    assert [(s.kind, s.path) for s in result.profile.standards_sources] == [
        ("prompts-dir", ".prompts")
    ]


def test_the_selected_clients_are_recorded_and_unknown_versions_stay_null() -> None:
    result = draft("uv_fastapi", clients=("codex",))

    assert result.profile.clients.enabled == ("codex",)
    assert result.profile.clients.min_versions == {"codex": None}


def test_technologies_found_by_the_scanners_are_recorded_with_their_evidence() -> None:
    from orqlet.adapters.fs.yaml_loader import StrictYamlLoader  # noqa: F401
    from orqlet.adapters.scan.technology_scanners import GoScanner
    from orqlet.application.usecases.discover import discover_technologies

    fs = repo("go_service")
    found = discover_technologies(fs, (GoScanner(),)).technologies

    result = draft_profile(
        fs,
        SCANNERS,
        project_id=PROJECT_ID,
        name="x",
        origin="existing",
        orqlet_version="0.1.0",
        technologies=found,
    )

    assert result.profile.technologies == found
    assert result.profile.stack.support == "partly-covered"
    assert "Go" in result.profile.stack.capability_limits[0]
    assert "facts.python" not in {q.id for q in result.questions}
    assert (
        ProjectProfile.model_validate(result.profile.model_dump(mode="json", by_alias=True))
        == result.profile
    )


def test_python_questions_stay_when_the_repository_root_is_python() -> None:
    result = draft("uv_fastapi")

    assert {q.id for q in result.questions} >= {"repository.target_branch"}
    assert result.profile.facts.python.value == ">=3.12"


def test_a_root_dockerfile_with_a_python_image_does_not_make_the_root_a_python_project() -> None:
    from orqlet.adapters.scan.technology_scanners import ContainerScanner
    from orqlet.application.usecases.discover import discover_technologies

    fs = with_files(
        {"Dockerfile.worker": "FROM registry.example.com/team/python:3.13 AS builder\n"}
    )
    found = discover_technologies(fs, (ContainerScanner(),)).technologies

    result = draft_profile(
        fs,
        SCANNERS,
        project_id=PROJECT_ID,
        name="x",
        origin="existing",
        orqlet_version="0.1.0",
        technologies=found,
    )

    assert {(t.scope, t.name, t.version) for t in found} >= {(".", "Python", "3.13")}
    assert {q.id for q in result.questions} == {
        "repository.target_branch",
        "repository.branch_naming",
        "repository.commit_convention",
    }


# --- team conventions (task team-conventions-resources, phase P-5) -------------------------------
# Every test below cites its expected_behavior_source: AC-n are the acceptance criteria of phase P-5
# in docs/design/team-conventions-resources/plan.yaml, ADR-003 is the file `adr-003-*.md` under
# docs/design/team-conventions-resources/design/, and "the interface decision" is the reading of the
# plan author that the Tester of phase P-5 was given (see test_conventions_questions.py): the five
# new facts are unknowns with questions, merge_strategy and reviewers are `unknown`, and
# draft_profile.py gets no new public function. These tests hold before the change as well, because
# the contract of phase P-2 already gives the defaults: they guard the behaviour that this phase
# must keep.
THREE_OLD_FACTS = [
    "repository.target_branch",
    "repository.branch_naming",
    "repository.commit_convention",
]
NEW_FACT_KEYS = (
    "repository.branch_model",
    "repository.branch_patterns",
    "repository.release_flow",
    "repository.pull_requests.shape",
    "repository.pull_requests.required_checks",
)
OLD_PROFILE_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.project-profile.v1.yaml"
)


def new_fact(profile: ProjectProfile, key: str) -> FactValue:
    repository = profile.repository
    pull_requests = repository.pull_requests
    table = {
        "repository.branch_model": repository.branch_model,
        "repository.branch_patterns": repository.branch_patterns,
        "repository.release_flow": repository.release_flow,
        "repository.pull_requests.shape": pull_requests.shape,
        "repository.pull_requests.required_checks": pull_requests.required_checks,
    }
    return table[key]


@pytest.mark.parametrize("name", ["uv_fastapi", "js_only", "empty"])
@pytest.mark.parametrize("key", NEW_FACT_KEYS)
def test_a_fresh_draft_holds_each_new_fact_as_an_unknown_with_its_question(
    name: str, key: str
) -> None:
    """AC-1, AC-2. expected_behavior_source: the interface decision (the new facts are unknowns with
    questions for a fresh draft), ADR-003 decision 1 ("each with a default that is an unknown with
    its question") and plan P-5 file operation for draft_profile.py."""
    fact = new_fact(draft(name).profile, key)

    assert fact.value is None
    assert fact.question is not None
    assert fact.question.strip()
    assert fact.evidence == ()
    assert fact.answered_by is None


@pytest.mark.parametrize("name", ["uv_fastapi", "js_only", "empty"])
def test_a_fresh_draft_leaves_merge_strategy_and_reviewers_at_unknown(name: str) -> None:
    """AC-2. expected_behavior_source: ADR-003 decision 1 (`merge_strategy` and `reviewers` keep
    their type; the text `unknown` is their unanswered state) and the interface decision."""
    pull_requests = draft(name).profile.repository.pull_requests

    assert (pull_requests.merge_strategy, pull_requests.reviewers) == ("unknown", "unknown")


@pytest.mark.parametrize("name", ["uv_fastapi", "js_only", "empty"])
def test_the_new_facts_are_not_open_questions_of_the_draft(name: str) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 2 ("The new unknown facts are reported by
    one information finding, not by ORQ-W181") and the interface decision (`open_questions` is
    unchanged; no new public function in draft_profile.py: the unknown conventions are not listed
    here)."""
    result = draft(name)
    ids = [question.id for question in result.questions]

    assert [i for i in ids if i.startswith("repository.")] == THREE_OLD_FACTS
    plain = {"repository.pull_requests.merge_strategy", "repository.pull_requests.reviewers"}
    assert not {*NEW_FACT_KEYS, *plain} & set(ids)
    assert result.questions == open_questions(result.profile)


def test_answering_the_new_facts_does_not_change_the_open_questions() -> None:
    """AC-4. expected_behavior_source: the interface decision (`open_questions(profile)` is
    unchanged) and ADR-003 decision 2: the list holds the three old facts whatever the new ones
    are."""
    profile = draft("uv_fastapi").profile
    answered = FactValue(value="none", answered_by="maintainer")
    repository = profile.repository.model_copy(
        update={
            "branch_model": answered,
            "branch_patterns": answered,
            "release_flow": answered,
            "pull_requests": profile.repository.pull_requests.model_copy(
                update={"shape": answered, "required_checks": answered}
            ),
        }
    )

    changed = profile.model_copy(update={"repository": repository})

    assert open_questions(changed) == open_questions(profile)
    assert [q.id for q in open_questions(changed)] == THREE_OLD_FACTS


def test_an_old_profile_has_the_unknown_defaults_and_no_new_open_question() -> None:
    """AC-2, AC-4. expected_behavior_source: the interface decision ("An old or new draft profile
    gets the unknown defaults of the new facts"; use a profile document written without the new
    fields) and ADR-003 decision 1 (an existing profile still loads). The fixture is a document of
    the old shape: it has none of the five keys."""
    profile = load_contract(
        StrictYamlLoader(), ProjectProfile, OLD_PROFILE_FIXTURE.read_bytes(), source="fixture"
    )

    for key in NEW_FACT_KEYS:
        fact = new_fact(profile, key)
        assert fact.value is None
        assert fact.question
    ids = [q.id for q in open_questions(profile)]
    assert [i for i in ids if i.startswith("repository.")] == [
        "repository.branch_naming",
        "repository.commit_convention",
    ]
