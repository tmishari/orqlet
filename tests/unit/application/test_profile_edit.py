"""`profile answer` and `profile approve`: late answers and approval, journalled and undoable."""

from __future__ import annotations

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.common import FactValue
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


# --- team conventions (task team-conventions-resources, phase P-5) -------------------------------
# Every test below cites its expected_behavior_source: AC-n are the acceptance criteria of phase P-5
# in docs/design/team-conventions-resources/plan.yaml, ADR-003 is the file `adr-003-*.md` under
# docs/design/team-conventions-resources/design/, and "the interface decision" is the reading of the
# plan author that the Tester of phase P-5 was given (see test_conventions_questions.py): `profile
# answer` takes the seven keys through ANSWER_KEYS, withdraws an approval and adds ORQ-I070 as
# before, reports a refused value as the existing ORQ-W060 note and an answer that changes nothing
# as ORQ-E162.
BRANCH_MODEL = "repository.branch_model"
BRANCH_PATTERNS = "repository.branch_patterns"
RELEASE_FLOW = "repository.release_flow"
SHAPE = "repository.pull_requests.shape"
MERGE_STRATEGY = "repository.pull_requests.merge_strategy"
REVIEWERS = "repository.pull_requests.reviewers"
REQUIRED_CHECKS = "repository.pull_requests.required_checks"
CONVENTION_KEYS = (
    BRANCH_MODEL,
    BRANCH_PATTERNS,
    RELEASE_FLOW,
    SHAPE,
    MERGE_STRATEGY,
    REVIEWERS,
    REQUIRED_CHECKS,
)
PLAIN_KEYS = frozenset({MERGE_STRATEGY, REVIEWERS})
ANSWERS = {
    BRANCH_MODEL: "gitflow",
    BRANCH_PATTERNS: "feature/*, fix/*, release/*",
    RELEASE_FLOW: "release branches are cut from develop and tagged on main",
    SHAPE: "one change per pull request, with a description of the why",
    MERGE_STRATEGY: "squash",
    REVIEWERS: "two reviewers, one from the owning team",
    REQUIRED_CHECKS: "lint, tests, security scan",
}
HEAD, TAIL = "QX7HEAD", "ZK9TAIL"


def convention(profile: ProjectProfile, key: str) -> FactValue | str:
    repository = profile.repository
    pull_requests = repository.pull_requests
    table: dict[str, FactValue | str] = {
        BRANCH_MODEL: repository.branch_model,
        BRANCH_PATTERNS: repository.branch_patterns,
        RELEASE_FLOW: repository.release_flow,
        SHAPE: pull_requests.shape,
        MERGE_STRATEGY: pull_requests.merge_strategy,
        REVIEWERS: pull_requests.reviewers,
        REQUIRED_CHECKS: pull_requests.required_checks,
    }
    return table[key]


def maintainers(key: str, text: str) -> FactValue | str:
    """The form in which a maintainer's answer to `key` is recorded."""
    return text if key in PLAIN_KEYS else FactValue(value=text, answered_by="maintainer")


def is_unknown(profile: ProjectProfile, key: str) -> bool:
    item = convention(profile, key)
    return item == "unknown" if isinstance(item, str) else item.value is None


def messages_of(result, code: str) -> list[str]:  # type: ignore[no-untyped-def]
    return [finding.message for finding in result.findings if finding.code == code]


def unknown_conventions_listed_by_doctor(env: Env) -> str:
    """The message of ORQ-I502 of `doctor`, or an empty text when there is none."""
    found = [f.message for f in doctor(env.services()).findings if f.code == "ORQ-I502"]
    assert len(found) <= 1
    return found[0] if found else ""


@pytest.mark.parametrize("key", CONVENTION_KEYS)
def test_profile_answer_accepts_each_new_key_and_records_it_as_the_maintainers(key: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("init and profile answer accept ..."), the interface
    decision (`profile answer` accepts the seven keys through ANSWER_KEYS; an accepted answer is
    recorded as the maintainer's) and ADR-003 decision 2 ("`profile answer` sets them later")."""
    env = initialised()

    result = answer_profile(env.services(), {key: ANSWERS[key]}, assume_yes=True)

    assert "ORQ-E160" not in codes(result)
    assert result.status == "applied", result.findings
    assert convention(profile_of(env), key) == maintainers(key, ANSWERS[key])


def test_all_seven_answers_can_be_given_in_one_command() -> None:
    """AC-1. expected_behavior_source: AC-1 and the interface decision (the seven keys are answer
    keys; each is recorded)."""
    env = initialised()

    result = answer_profile(env.services(), ANSWERS, assume_yes=True)

    assert result.status == "applied", result.findings
    assert "ORQ-W060" not in codes(result)
    for key in CONVENTION_KEYS:
        assert convention(profile_of(env), key) == maintainers(key, ANSWERS[key]), key


@pytest.mark.parametrize("key", CONVENTION_KEYS)
def test_the_answer_none_is_accepted_for_each_new_key_and_is_a_value(key: str) -> None:
    """AC-2. expected_behavior_source: AC-2 ("The answer none is recorded as a value and the fact
    is no longer unknown"), ADR-003 decision 2 and the interface decision (`none` is accepted for
    every key)."""
    env = initialised()

    result = answer_profile(env.services(), {key: "none"}, assume_yes=True)

    assert result.status == "applied", result.findings
    profile = profile_of(env)
    assert convention(profile, key) == maintainers(key, "none")
    assert not is_unknown(profile, key)


@pytest.mark.parametrize("key", [BRANCH_PATTERNS, REQUIRED_CHECKS])
def test_a_list_within_the_caps_is_accepted(key: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 2 (comma-separated lists of at most 12 items
    of at most 60 characters whose whole text is at most 160 characters) and the interface decision
    (the same caps). Twelve items, and a list of exactly 160 characters."""
    twelve = ", ".join(f"c{number:02d}" for number in range(12))
    at_the_limit = ",".join(["a" * 60, "b" * 60, "c" * 38])
    assert len(at_the_limit) == 160
    for value in (twelve, at_the_limit):
        env = initialised()

        result = answer_profile(env.services(), {key: value}, assume_yes=True)

        assert result.status == "applied", result.findings
        assert convention(profile_of(env), key) == maintainers(key, value)


# case -> (key, a value that must be refused)
REFUSED: dict[str, tuple[str, str]] = {
    "shape-with-a-backtick": (SHAPE, "use the `template`"),
    "release-flow-with-a-link": (RELEASE_FLOW, "see https://example.com/flow"),
    "reviewers-over-200-characters": (REVIEWERS, "x" * 201),
    "branch-model-outside-the-vocabulary": (BRANCH_MODEL, "svn-flow"),
    "branch-model-other-without-a-text": (BRANCH_MODEL, "other:"),
    "merge-strategy-outside-the-vocabulary": (MERGE_STRATEGY, "fast-forward"),
    "pattern-with-two-double-stars": (BRANCH_PATTERNS, "feature/**/**"),
    "list-of-13-checks": (REQUIRED_CHECKS, ", ".join(f"c{number:02d}" for number in range(13))),
    "list-of-161-characters": (
        BRANCH_PATTERNS,
        ",".join(["a" * 60, "b" * 60, "c" * 39]),
    ),
    "item-of-61-characters": (REQUIRED_CHECKS, "a" * 61),
    "checks-with-an-escape": (REQUIRED_CHECKS, "lint\x1b[31m"),
    "release-flow-with-a-bidi-override": (RELEASE_FLOW, "flow\u202e"),
    "shape-with-a-line-break": (SHAPE, "line one\nline two"),
}


@pytest.mark.parametrize(("key", "value"), list(REFUSED.values()), ids=list(REFUSED))
def test_a_refused_value_is_a_warning_that_names_the_key_and_changes_nothing(
    key: str, value: str
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("refuse a value that fails the vocabulary, the caps or
    text_problems with a note that names the key"; "a pattern with two `**`"), the interface
    decision (`profile answer` reports a refused value as the existing ORQ-W060 warning note; an
    answer that changes nothing is ORQ-E162 as before) and ADR-003 decision 2."""
    env = initialised()
    before = tree(env.project)

    result = answer_profile(env.services(), {key: value}, assume_yes=True)

    assert "ORQ-E160" not in codes(result)  # it is a key that can be answered
    assert any(key in note for note in messages_of(result, "ORQ-W060")), result.findings
    assert "ORQ-E162" in codes(result)
    assert result.status == "refused"
    assert tree(env.project) == before


def test_a_good_answer_is_applied_next_to_a_refused_one() -> None:
    """AC-1. expected_behavior_source: the interface decision (a refused value is an ORQ-W060 note;
    the rest is applied as today, see the existing test of a rejected value)."""
    env = initialised()

    result = answer_profile(
        env.services(), {BRANCH_MODEL: "svn-flow", SHAPE: ANSWERS[SHAPE]}, assume_yes=True
    )

    assert result.status == "applied", result.findings
    notes = messages_of(result, "ORQ-W060")
    assert any(BRANCH_MODEL in note for note in notes), notes
    assert not any(SHAPE in note for note in notes), notes
    profile = profile_of(env)
    assert convention(profile, SHAPE) == maintainers(SHAPE, ANSWERS[SHAPE])
    assert is_unknown(profile, BRANCH_MODEL)


@pytest.mark.parametrize("key", CONVENTION_KEYS)
@pytest.mark.parametrize(
    "mark", ["\x1b[31m", "`", "://", "\u202e", "\n"], ids=["esc", "tick", "link", "bidi", "lf"]
)
def test_a_refused_value_is_not_shown_in_any_finding(key: str, mark: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 (a message never holds text that came from
    outside) and AC-1 ("a note that names the key"): the finding names the key and holds no part of
    the value, which is marked by two words."""
    env = initialised()
    prefix = "other: " if key in {BRANCH_MODEL, MERGE_STRATEGY} else ""
    value = f"{prefix}{HEAD}{mark}{TAIL}"

    result = answer_profile(env.services(), {key: value}, assume_yes=True)

    assert any(key in note for note in messages_of(result, "ORQ-W060")), result.findings
    for finding in result.findings:
        assert HEAD not in finding.message
        assert TAIL not in finding.message
        assert all(0x20 <= ord(char) <= 0x7E for char in finding.message), finding.message


@pytest.mark.parametrize("key", CONVENTION_KEYS)
def test_answering_a_convention_withdraws_the_approval_and_approving_stays_a_persons_act(
    key: str,
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("Answering a convention withdraws the profile's
    approval (ORQ-I070) and approving stays a person's act"), ADR-003 decision 7 ("The approval rule
    is unchanged") and the interface decision (ORQ-I070 as before)."""
    env = initialised()
    approve_profile(env.services(), "Ada", assume_yes=True)
    assert profile_of(env).profile.status == "approved"

    result = answer_profile(env.services(), {key: ANSWERS[key]}, assume_yes=True)

    meta = profile_of(env).profile
    assert result.status == "applied", result.findings
    assert (meta.status, meta.reviewed_by) == ("draft", None)
    assert "ORQ-I070" in codes(result)
    assert "ORQ-W180" in {f.code for f in doctor(env.services()).findings}
    again = approve_profile(env.services(), "Grace", assume_yes=True)
    assert again.status == "applied"
    assert profile_of(env).profile.reviewed_by == "Grace"


def test_a_refused_convention_answer_does_not_withdraw_an_approval() -> None:
    """AC-5. expected_behavior_source: AC-5 and the interface decision (an answer withdraws an
    approval "as before": the profile changes, and a refused answer changes nothing, ORQ-E162). A
    good answer to the same install does withdraw it."""
    env = initialised()
    approve_profile(env.services(), "Ada", assume_yes=True)

    refused = answer_profile(env.services(), {BRANCH_MODEL: "svn-flow"}, assume_yes=True)

    assert "ORQ-I070" not in codes(refused)
    assert profile_of(env).profile.status == "approved"
    accepted = answer_profile(env.services(), {BRANCH_MODEL: "gitflow"}, assume_yes=True)
    assert "ORQ-I070" in codes(accepted)
    assert profile_of(env).profile.status == "draft"


def test_the_same_convention_answer_twice_changes_nothing_the_second_time() -> None:
    """AC-2. expected_behavior_source: the interface decision ("an answer that changes nothing is
    ORQ-E162 as before"), as the existing test of technologies shows it for another key."""
    env = initialised()
    first = answer_profile(env.services(), {SHAPE: ANSWERS[SHAPE]}, assume_yes=True)

    again = answer_profile(env.services(), {SHAPE: ANSWERS[SHAPE]}, assume_yes=True)

    assert first.status == "applied", first.findings
    assert again.status == "refused"
    assert "ORQ-E162" in codes(again)


def test_an_answer_removes_the_convention_from_the_unknown_conventions_of_doctor() -> None:
    """AC-2, AC-4. expected_behavior_source: AC-2 ("a question is asked again only while the fact
    is unknown"), the interface decision (ORQ-I502 names each unknown key) and ADR-003 decision 2
    ("`init` asks them, and `profile answer` sets them later"). Answered with `none`, the key is no
    longer listed, and the others still are."""
    env = initialised()
    assert "release_flow" in unknown_conventions_listed_by_doctor(env)

    answer_profile(env.services(), {RELEASE_FLOW: "none"}, assume_yes=True)

    listed = unknown_conventions_listed_by_doctor(env)
    assert "release_flow" not in listed
    assert "branch_model" in listed
    assert "required_checks" in listed


def test_once_every_convention_is_answered_doctor_no_longer_lists_unknown_conventions() -> None:
    """AC-2, AC-4. expected_behavior_source: the interface decision (no ORQ-I502 when none of the
    seven is unknown) and AC-1 (`profile answer` accepts the seven keys). The finding is there
    before the answers."""
    env = initialised()
    assert unknown_conventions_listed_by_doctor(env)

    answer_profile(env.services(), ANSWERS, assume_yes=True)

    assert unknown_conventions_listed_by_doctor(env) == ""


def test_a_convention_answer_can_be_undone_with_rollback() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 1 (the answers are profile facts; the
    profile is a normal journalled apply) and the existing behaviour of `profile answer` that the
    test of a target branch shows."""
    env = initialised()
    before = tree(env.project)
    result = answer_profile(
        env.services(), {REQUIRED_CHECKS: ANSWERS[REQUIRED_CHECKS]}, assume_yes=True
    )
    assert result.change_id is not None

    undone = rollback(env.services(), RollbackOptions(result.change_id, assume_yes=True))

    assert undone.status == "applied"
    assert tree(env.project) == before


def test_a_dry_run_of_a_convention_answer_shows_the_profile_and_writes_nothing() -> None:
    """AC-1. expected_behavior_source: the existing contract of `profile answer` (`dry_run` is
    `previewed` and writes nothing) applied to a new key, and the interface decision (the seven keys
    are accepted)."""
    env = initialised()
    before = tree(env.project)

    result = answer_profile(env.services(), {SHAPE: ANSWERS[SHAPE]}, dry_run=True)

    assert result.status == "previewed"
    assert result.profile is not None
    assert convention(result.profile, SHAPE) == maintainers(SHAPE, ANSWERS[SHAPE])
    assert tree(env.project) == before
