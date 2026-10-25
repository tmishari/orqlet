"""`profile answer` and `profile approve`: late answers and approval, journalled and undoable."""

from __future__ import annotations

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.diagnose import doctor
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import NotInitialised
from orqlet.application.usecases.profile_edit import answer_profile, approve_profile
from orqlet.application.usecases.rollback import RollbackOptions, rollback
from tests.fakes.ids import SequentialIds
from tests.fakes.vcs import FakeVcs
from tests.support.init_env import Env, read, tree
from tests.support.trees import repo

pytestmark = pytest.mark.unit

LOADER = StrictYamlLoader()


def initialised(name: str = "uv_fastapi") -> Env:
    env = Env(project=repo(name), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    assert init_project(env.services(), InitOptions(assume_yes=True)).status == "applied"
    env.ids = SequentialIds(start=100)
    return env


def profile_of(env: Env) -> ProjectProfile:
    return load_contract(
        LOADER, ProjectProfile, tree(env.project)[".orqlet/project-profile.yaml"], source="p"
    )


def codes(result) -> set[str]:  # type: ignore[no-untyped-def]
    return {finding.code for finding in result.findings}


def test_an_answer_fills_an_unknown_fact_and_doctor_stops_listing_it() -> None:
    env = initialised()

    result = answer_profile(
        env.services(), {"repository.branch_naming": "feature/*"}, assume_yes=True
    )

    assert result.status == "applied"
    fact = profile_of(env).repository.branch_naming
    assert (fact.value, fact.answered_by) == ("feature/*", "maintainer")
    messages = " ".join(f.message for f in doctor(env.services()).findings if f.code == "ORQ-W181")
    assert "branch_naming" not in messages
    assert "commit_convention" in messages


def test_the_manifest_records_the_new_profile_so_nothing_looks_edited() -> None:
    env = initialised()

    answer_profile(
        env.services(), {"repository.commit_convention": "conventional"}, assume_yes=True
    )

    lock = read(env.project, ".orqlet/generated.lock.yaml")
    from orqlet.domain.digest import sha256_hex

    profile_bytes = tree(env.project)[".orqlet/project-profile.yaml"]
    assert sha256_hex(profile_bytes) in lock
    assert not [f for f in doctor(env.services()).findings if f.severity.value == "error"]


def test_technologies_can_be_added_later_without_evidence_and_never_twice() -> None:
    env = initialised()
    answer = {"technologies": "database:PostgreSQL@16, queue:Kafka"}

    answer_profile(env.services(), answer, assume_yes=True)
    again = answer_profile(env.services(), answer, assume_yes=True)

    stated = [t for t in profile_of(env).technologies if t.source == "maintainer"]
    assert sorted((t.kind, t.name) for t in stated) == [
        ("database", "PostgreSQL"),
        ("queue", "Kafka"),
    ]
    assert again.status == "refused"
    assert "ORQ-E162" in codes(again)  # the second time it changes nothing


def test_an_answer_can_be_undone_with_rollback() -> None:
    env = initialised()
    before = tree(env.project)
    result = answer_profile(env.services(), {"repository.target_branch": "trunk"}, assume_yes=True)
    assert result.change_id is not None

    undone = rollback(env.services(), RollbackOptions(result.change_id, assume_yes=True))

    assert undone.status == "applied"
    assert tree(env.project) == before


@pytest.mark.parametrize(
    ("answers", "code"),
    [
        ({"repository.not_a_fact": "x"}, "ORQ-E160"),
        ({"facts.python": ">=3.9"}, "ORQ-E161"),  # read from pyproject.toml with evidence
        ({"facts.package_manager": "pip"}, "ORQ-E161"),
        ({"repository.target_branch": "../etc"}, "ORQ-E162"),  # rejected value: nothing changes
    ],
)
def test_answers_that_must_not_be_applied_are_refused_and_write_nothing(
    answers: dict[str, str], code: str
) -> None:
    env = initialised()
    before = tree(env.project)

    result = answer_profile(env.services(), answers, assume_yes=True)

    assert result.status == "refused"
    assert code in codes(result)
    assert tree(env.project) == before


def test_a_rejected_value_is_explained_and_the_good_answers_still_apply() -> None:
    env = initialised()

    result = answer_profile(
        env.services(),
        {"project.kind": "spaceship", "repository.branch_naming": "feature/*"},
        assume_yes=True,
    )

    assert result.status == "applied"
    assert "ORQ-W060" in codes(result)  # the rejected answer was ignored, and why
    assert profile_of(env).repository.branch_naming.value == "feature/*"
    assert profile_of(env).project.kind == "python-service"  # unchanged


def test_approving_records_who_and_when_and_clears_the_draft_warning() -> None:
    env = initialised()

    result = approve_profile(env.services(), "  Ada Lovelace  ", assume_yes=True)

    meta = profile_of(env).profile
    assert result.status == "applied"
    assert (meta.status, meta.reviewed_by) == ("approved", "Ada Lovelace")
    assert meta.reviewed_at is not None
    assert "ORQ-W180" not in {f.code for f in doctor(env.services()).findings}


def test_a_profile_cannot_be_approved_twice_and_a_reviewer_is_required() -> None:
    env = initialised()
    approve_profile(env.services(), "Ada", assume_yes=True)

    twice = approve_profile(env.services(), "Grace", assume_yes=True)
    nameless = approve_profile(initialised().services(), "   ", assume_yes=True)

    assert "ORQ-E164" in codes(twice)
    assert "ORQ-E163" in codes(nameless)
    assert profile_of(env).profile.reviewed_by == "Ada"


def test_changing_a_fact_withdraws_an_earlier_approval() -> None:
    env = initialised()
    approve_profile(env.services(), "Ada", assume_yes=True)

    result = answer_profile(env.services(), {"repository.branch_naming": "x/*"}, assume_yes=True)

    meta = profile_of(env).profile
    assert (meta.status, meta.reviewed_by) == ("draft", None)
    assert "ORQ-I070" in codes(result)
    assert "ORQ-W180" in {f.code for f in doctor(env.services()).findings}


def test_without_approval_and_on_a_dry_run_nothing_is_written() -> None:
    env = initialised()
    before = tree(env.project)

    quiet = approve_profile(env.services(), "Ada")
    dry = answer_profile(env.services(), {"repository.branch_naming": "x/*"}, dry_run=True)

    assert quiet.status == "needs-input"
    assert dry.status == "previewed"
    assert [str(w.path) for w in dry.plan.writes] == [  # type: ignore[union-attr]
        ".orqlet/project-profile.yaml",
        ".orqlet/generated.lock.yaml",
    ]
    assert tree(env.project) == before


def test_an_uninitialised_directory_is_refused() -> None:
    env = Env(project=repo("uv_fastapi"))

    with pytest.raises(NotInitialised):
        approve_profile(env.services(), "Ada", assume_yes=True)
