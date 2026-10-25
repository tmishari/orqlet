import pytest

from orqlet.adapters.scan.python_scanner import PythonScanner
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.usecases.draft_profile import draft_profile
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
