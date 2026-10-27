"""The convention questions of `init` and `profile answer`, their checks, and what `doctor` says
about them (task team-conventions-resources, phase P-5).

Every test cites its `expected_behavior_source`. ADR-003 is the file `adr-003-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-6 are the acceptance criteria of phase P-5 in
docs/design/team-conventions-resources/plan.yaml. "The interface decision" is the reading of the
plan author that the Tester of phase P-5 was given, because the ADR does not spell it out:

- `ANSWER_KEYS` gains exactly seven keys; `questions_for` appends, after the three repository
  questions and in the order of the keys, a Question for each of them while the fact is unknown
  (`branch_patterns` only while `branch_naming` is answered and is not `none`, compared
  case-insensitively); `collect_answers` is unchanged;
- `apply_answers` records an accepted answer as the maintainer's own and ignores, with a note that
  contains the key, an answer that fails `text_problems(value, 200)`, the vocabulary of
  `branch_model` and `merge_strategy` (with `none` and `other: <text>`), the caps of the two lists
  (at most 12 items of at most 60 characters, at most 160 characters in all) or `pattern_problems`
  for an item of `branch_patterns`; the stored value is the text as given, stripped;
- `profile answer` takes the seven keys, withdraws an approval (ORQ-I070) and reports a refused
  value as ORQ-W060;
- `init` keeps every answer to the end (`_with_pr_template` keeps `shape` and `required_checks`);
- `doctor` (not `sync`) prints one INFO finding ORQ-I502 for the unknown conventions and one INFO
  finding ORQ-I503 when a convention that the host enforces is answered; neither changes its exit
  code, ORQ-W181 still lists three facts, and no public name is added.

These tests were written first, by the Tester of phase P-5, before the behaviour existed. The file
system is the in-memory fake of tests/fakes and the services are the ones of
tests/support/init_env.py (ORQLET-TEST-001). The tests of `init` (with and without a terminal), of
`draft_profile` and of `profile answer` are in test_init_project.py, test_draft_profile.py and
test_profile_edit.py.

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of a question, its options, and the wording of any message beyond what each test
  says (a refusal note: only that it holds the key and no part of the value; ORQ-I502: only the
  names of the keys; ORQ-I503: only that it says the host cannot be read and asks for the branch
  protection settings to be confirmed);
- whether a vocabulary word is accepted in another letter case (`Gitflow`, `NONE`), with blanks
  around it, or written `other:text` without a blank; the stored text of `other:` answers beyond
  being the text as given, stripped;
- whether an empty item of a list (`a,,b`, a trailing comma) is refused or skipped, and whether the
  160 characters of a list count the blanks around its commas (the tests use lists without blanks
  at the boundary, and blanks only where the total is far from it);
- whether ORQ-I502 names `branch_patterns` while `branch_naming` is unknown or `none` (it is only
  checked where `branch_naming` is answered);
- whether the public signatures change (only the public names are compared);
- the exit code of the real command, which `lifecycle.py` derives from the severities of the
  findings: it is read here through that rule, and tests/integration/test_lifecycle_cli.py runs it
  through the real command.

Hostile values are marked with two words that no fixed message holds; a message "holds part of the
value" when it holds one of them. Nothing here looks like a credential, so nothing needs to be
assembled from parts (ORQLET-SEC-003).
"""

from __future__ import annotations

import functools
import importlib
import re
from collections.abc import Mapping
from pathlib import Path

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.emit import YamlWriter
from orqlet.adapters.scan.python_scanner import PythonScanner
from orqlet.application.contracts.common import FactValue
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.diagnose import Diagnosis, doctor, sync
from orqlet.application.usecases.draft_profile import draft_profile, open_questions
from orqlet.application.usecases.init_files import contract_bytes
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.init_questions import (
    ANSWER_KEYS,
    apply_answers,
    collect_answers,
    questions_for,
)
from orqlet.domain.conventions import pattern_problems
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.python_api import extract_module_api
from orqlet.domain.resources import text_problems
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.prompter import ScriptedPrompter
from tests.fakes.vcs import FakeVcs
from tests.support.init_env import Env
from tests.support.trees import repo

pytestmark = pytest.mark.unit

LOADER = StrictYamlLoader()
WRITER = YamlWriter()
PROJECT_ID = "00000000-0000-4000-8000-000000000001"
PROFILE_PATH = CanonicalPath.parse(".orqlet/project-profile.yaml")

BRANCH_MODEL = "repository.branch_model"
BRANCH_PATTERNS = "repository.branch_patterns"
RELEASE_FLOW = "repository.release_flow"
SHAPE = "repository.pull_requests.shape"
MERGE_STRATEGY = "repository.pull_requests.merge_strategy"
REVIEWERS = "repository.pull_requests.reviewers"
REQUIRED_CHECKS = "repository.pull_requests.required_checks"
# the seven new keys, in the order in which the interface decision asks them
NEW_KEYS = (
    BRANCH_MODEL,
    BRANCH_PATTERNS,
    RELEASE_FLOW,
    SHAPE,
    MERGE_STRATEGY,
    REVIEWERS,
    REQUIRED_CHECKS,
)
ASKED_AT_FIRST = tuple(key for key in NEW_KEYS if key != BRANCH_PATTERNS)
THREE = (
    "repository.target_branch",
    "repository.branch_naming",
    "repository.commit_convention",
)
OLD_KEYS = frozenset(
    {
        "facts.python",
        "facts.package_manager",
        "facts.frameworks",
        "project.kind",
        "structure.test_runner",
        *THREE,
        "technologies",
    }
)
PLAIN_KEYS = frozenset({MERGE_STRATEGY, REVIEWERS})  # kept as plain text, `unknown` when unanswered
VOCABULARY_KEYS = frozenset({BRANCH_MODEL, MERGE_STRATEGY})
LIST_KEYS = (BRANCH_PATTERNS, REQUIRED_CHECKS)
FREE_TEXT_KEYS = (SHAPE, RELEASE_FLOW, REVIEWERS)
HOST_ENFORCED_KEYS = (MERGE_STRATEGY, REVIEWERS, REQUIRED_CHECKS, SHAPE, RELEASE_FLOW)
# the keys that contain an underscore are not words of the English text of a message
UNDERSCORED_KEYS = (BRANCH_MODEL, BRANCH_PATTERNS, RELEASE_FLOW, MERGE_STRATEGY, REQUIRED_CHECKS)

# an answer that a maintainer could give to each key
ACCEPTED: dict[str, str] = {
    BRANCH_MODEL: "gitflow",
    BRANCH_PATTERNS: "feature/*, fix/*, release/*",
    RELEASE_FLOW: "release branches are cut from develop and tagged on main",
    SHAPE: "one change per pull request, with a description of the why",
    MERGE_STRATEGY: "squash",
    REVIEWERS: "two reviewers, one from the owning team",
    REQUIRED_CHECKS: "lint, tests, security scan",
}
EXISTING_ANSWERS = {
    "repository.target_branch": "main",
    "repository.branch_naming": "feature/*",
    "repository.commit_convention": "conventional-commits",
    "reviewer": "Ada",
}

# What a hostile answer holds. Each is put between two marker words.
HEAD, TAIL = "QX7HEAD", "ZK9TAIL"
HOSTILE: dict[str, str] = {
    "escape": "\x1b[31m",
    "backtick": "`",
    "link": "://",
    "bidi-override": "\u202e",
    "newline": "\n",
    "carriage-return": "\r",
    "markup": "](",
    "at-sign": "@",
    "angle-bracket": "<",
    "not-ascii": "\u00e9",
    "delete": "\x7f",
}

PUBLIC_NAMES_AT_BASE: dict[str, frozenset[str]] = {
    "orqlet.application.usecases.init_questions": frozenset(
        {
            "ANSWER_KEYS",
            "NEW_PROJECT_ORIGINS",
            "PACKAGE_MANAGERS",
            "PROJECT_KINDS",
            "apply_answers",
            "approve",
            "collect_answers",
            "questions_for",
        }
    ),
    "orqlet.application.usecases.draft_profile": frozenset(
        {
            "ALL_CLIENTS",
            "Client",
            "OpenQuestion",
            "Origin",
            "ProfileDraft",
            "draft_profile",
            "open_questions",
            "wants_python_questions",
        }
    ),
    "orqlet.application.usecases.diagnose": frozenset(
        {
            "Diagnosis",
            "Drift",
            "DriftState",
            "RESERVED_PREFIX",
            "doctor",
            "measure_drift",
            "sync",
        }
    ),
    "orqlet.application.usecases.init_project": frozenset(
        {"InitOptions", "InitResult", "InitServices", "Stores", "init_project"}
    ),
}


# --- helpers --------------------------------------------------------------------------------------


def short(key: str) -> str:
    return key.rsplit(".", 1)[-1]


def parametrized(name: str, cases: Mapping[str, object]) -> pytest.MarkDecorator:
    """`pytest.mark.parametrize` over the values of a mapping, with its keys as test ids."""
    return pytest.mark.parametrize(name, list(cases.values()), ids=list(cases))


def per_key(keys: tuple[str, ...] = NEW_KEYS) -> pytest.MarkDecorator:
    """One test case for each key, named by the short name of the key."""
    return parametrized("key", {short(key): key for key in keys})


def answered(text: str) -> FactValue:
    return FactValue(value=text, answered_by="maintainer")


def draft() -> ProjectProfile:
    """A fresh draft of a Python project: every new convention is an unknown."""
    return draft_profile(
        repo("uv_fastapi"),
        (PythonScanner(),),
        project_id=PROJECT_ID,
        name="demo",
        origin="existing",
        orqlet_version="0.1.0",
    ).profile


def with_naming(profile: ProjectProfile, text: str) -> ProjectProfile:
    """The profile with a branch naming rule, which `branch_patterns` depends on."""
    repository = profile.repository.model_copy(update={"branch_naming": answered(text)})
    return profile.model_copy(update={"repository": repository})


def with_answers(profile: ProjectProfile, by_key: Mapping[str, str]) -> ProjectProfile:
    """The profile with the given answers set by hand, the way a team's own file would hold them.

    This does not go through `apply_answers`, so a test of a question or of `doctor` does not
    depend on the recording of an answer.
    """
    repository_changes: dict[str, object] = {}
    pull_request_changes: dict[str, object] = {}
    for key, value in by_key.items():
        if key in PLAIN_KEYS:
            pull_request_changes[short(key)] = value
        elif key.startswith("repository.pull_requests."):
            pull_request_changes[short(key)] = answered(value)
        else:
            repository_changes[short(key)] = answered(value)
    repository = profile.repository
    pull_requests = repository.pull_requests.model_copy(update=pull_request_changes)
    repository = repository.model_copy(
        update={**repository_changes, "pull_requests": pull_requests}
    )
    return profile.model_copy(update={"repository": repository})


def stored(profile: ProjectProfile, key: str) -> FactValue | str:
    """What the profile holds for a new key: a fact, or the plain text of the two plain keys."""
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


def is_unknown(profile: ProjectProfile, key: str) -> bool:
    item = stored(profile, key)
    return item == "unknown" if isinstance(item, str) else item.value is None


def recorded_as(profile: ProjectProfile, key: str, text: str) -> bool:
    """True when the profile holds `text` for `key` in the form of the maintainer's answer."""
    item = stored(profile, key)
    if key in PLAIN_KEYS:
        return item == text
    return item == answered(text)


def apply(profile: ProjectProfile, answers: Mapping[str, str]) -> tuple[ProjectProfile, list[str]]:
    notes: list[str] = []
    return apply_answers(profile, answers, notes), notes


def ids_of(profile: ProjectProfile, *, asks_stack: bool = False) -> list[str]:
    return [question.id for question in questions_for(profile, asks_stack=asks_stack)]


def printable_line(text: str) -> bool:
    return all(0x20 <= ord(char) <= 0x7E for char in text)


def hostile_answer(key: str, mark: str) -> str:
    """An answer for `key` that holds `mark` between the two markers and otherwise passes."""
    text = f"{HEAD}{mark}{TAIL}"
    return f"other: {text}" if key in VOCABULARY_KEYS else text


def assert_refused(base: ProjectProfile, key: str, value: str) -> list[str]:
    """`value` is ignored for `key`, a note names the key, and the profile is the same."""
    result, notes = apply(base, {key: value})
    assert result == base, f"{key} was recorded for {value!r}"
    assert any(key in note for note in notes), f"no note names {key}: {notes}"
    return notes


def assert_no_part_of(value: str, notes: list[str]) -> None:
    for note in notes:
        assert HEAD not in note
        assert TAIL not in note
        assert value not in note
        assert printable_line(note), f"a note is not printable ASCII on one line: {note!r}"


def checks(count: int) -> list[str]:
    return [f"c{number:02d}" for number in range(count)]


def patterns(count: int) -> list[str]:
    return [f"p{number:02d}/*" for number in range(count)]


LIST_ITEMS = {BRANCH_PATTERNS: patterns, REQUIRED_CHECKS: checks}


# --- an installed project, as `doctor` reads it ---------------------------------------------------


@functools.cache
def _snapshot(approved: bool) -> tuple[tuple[str, bytes], ...]:
    """The files of an `init` of the Python fixture: approved with the three old facts answered,
    or a draft with nothing answered. Built once; every test gets its own copy."""
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    answers = EXISTING_ANSWERS if approved else {}
    result = init_project(env.services(), InitOptions(assume_yes=True, answers=answers))
    assert result.status == "applied", result.findings
    return tuple(env.project.snapshot().items())


def installed(*, approved: bool = True, legacy: bool = False) -> Env:
    """A project after `init`; with `legacy` its profile is written as before this change, with
    none of the five new fields (a document made by an older Orqlet)."""
    project = MemoryFileSystem()
    for name, data in _snapshot(approved):
        project.write_atomic(CanonicalPath.parse(name), data)
    env = Env(project=project, vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    if legacy:
        strip_new_fields(env)
    return env


def strip_new_fields(env: Env) -> None:
    document = LOADER.load(env.project.read_bytes(PROFILE_PATH), source="profile")
    assert isinstance(document, dict)
    repository = document["repository"]
    for name in ("branch_model", "release_flow", "branch_patterns"):
        repository.pop(name, None)
    for name in ("shape", "required_checks"):
        repository["pull_requests"].pop(name, None)
    env.project.write_atomic(PROFILE_PATH, WRITER.dump(document))
    written = LOADER.load(env.project.read_bytes(PROFILE_PATH), source="profile")
    assert isinstance(written, dict)
    assert not {"branch_model", "release_flow", "branch_patterns"} & set(written["repository"])
    assert not {"shape", "required_checks"} & set(written["repository"]["pull_requests"])


def written_profile(env: Env) -> ProjectProfile:
    return load_contract(
        LOADER, ProjectProfile, env.project.read_bytes(PROFILE_PATH), source="profile"
    )


def set_conventions(env: Env, by_key: Mapping[str, str]) -> None:
    """Write the profile with the given conventions set by hand, as a team's own edit would."""
    profile = with_answers(written_profile(env), by_key)
    env.project.write_atomic(PROFILE_PATH, contract_bytes(WRITER, profile))


def diagnose(env: Env) -> Diagnosis:
    return doctor(env.services())


def with_code(diagnosis: Diagnosis, code: str) -> list[Finding]:
    return [finding for finding in diagnosis.findings if finding.code == code]


def names(message: str, key: str) -> bool:
    """True when the message names the key, by its short name or by its whole name."""
    return re.search(rf"\b{re.escape(short(key))}\b", message) is not None


def problems_of(diagnosis: Diagnosis) -> list[Finding]:
    """The findings that make the exit code of `doctor` non-zero."""
    return [f for f in diagnosis.findings if f.severity in {Severity.WARNING, Severity.ERROR}]


def exit_code_of(diagnosis: Diagnosis) -> int:
    """The exit code of `orqlet doctor` for these findings, by the rule of the command itself
    (`_check_exit` in interface/cli/commands/lifecycle.py, which ADR-003 names in its Context)."""
    from orqlet.interface.cli.commands.lifecycle import _check_exit

    return int(_check_exit(diagnosis.findings))


# --- AC-6, EC-57: the answer keys and the public names --------------------------------------------


def test_the_answer_keys_are_the_nine_old_keys_and_exactly_the_seven_new_ones() -> None:
    """AC-6. expected_behavior_source: AC-6 ("ANSWER_KEYS gains seven keys"), EC-57 and ADR-003
    decision 2 (the seven keys by name)."""
    assert OLD_KEYS | set(NEW_KEYS) == ANSWER_KEYS
    assert len(ANSWER_KEYS) == 16


def test_the_nine_old_answer_keys_are_still_answer_keys() -> None:
    """AC-6. expected_behavior_source: EC-57 ("The set gains ..."; nothing is taken away). This
    holds before the change as well: it guards the old keys."""
    assert OLD_KEYS <= ANSWER_KEYS


@parametrized("module_name", {name.rsplit(".", 1)[-1]: name for name in PUBLIC_NAMES_AT_BASE})
def test_the_phase_adds_no_public_name_to_a_module_it_changes(module_name: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("The public API of the package differs from the base,
    in this phase, by nothing") and the interface decision (no new public function in
    draft_profile.py; this phase adds no public name). The names are the ones of git HEAD before
    the phase, read with the extractor of the package from the source text. This holds before the
    change as well: it guards the surface."""
    module = importlib.import_module(module_name)
    assert module.__file__ is not None
    api = extract_module_api(Path(module.__file__).read_text(encoding="utf-8"))

    assert api.errors == ()
    assert api.manual == ()
    assert frozenset(api.symbols) == PUBLIC_NAMES_AT_BASE[module_name]


def test_the_sample_answers_of_this_file_pass_the_rules_they_are_tested_against() -> None:
    """Self-check of the test data; no behaviour of the phase. expected_behavior_source: the
    interface decision (`text_problems(value, 200)` and `pattern_problems(item) == ()`). This holds
    before the change as well."""
    for key, text in ACCEPTED.items():
        assert text_problems(text, 200) == (), key
    for item in ACCEPTED[BRANCH_PATTERNS].split(","):
        assert pattern_problems(item.strip()) == ()


# --- AC-1, AC-2: which questions are asked --------------------------------------------------------


@pytest.mark.parametrize("asks_stack", [True, False])
def test_a_fresh_profile_is_asked_the_new_questions_after_the_three_repository_ones(
    asks_stack: bool,
) -> None:
    """AC-1. expected_behavior_source: the interface decision (`questions_for` appends, after the
    three repository questions and in this order, a Question for each unknown fact; branch_patterns
    only once branch_naming is answered), ADR-003 decision 2 and plan P-5 file operation for
    init_questions.py."""
    assert ids_of(draft(), asks_stack=asks_stack) == [*THREE, *ASKED_AT_FIRST]


def test_the_new_questions_come_last_after_every_question_about_the_stack() -> None:
    """AC-1. expected_behavior_source: the interface decision ("appends, after the existing three
    repository questions"): in an empty project the questions about the stack come first."""
    empty = draft_profile(
        MemoryFileSystem(),
        (PythonScanner(),),
        project_id=PROJECT_ID,
        name="demo",
        origin="empty",
        orqlet_version="0.1.0",
    ).profile

    ids = ids_of(empty, asks_stack=True)

    assert ids[ids.index("repository.target_branch") :] == [*THREE, *ASKED_AT_FIRST]
    assert ids.index("facts.python") < ids.index("repository.target_branch")


@pytest.mark.parametrize(
    "naming", ["feature/*", "Feature branches are named after the ticket"], ids=["glob", "text"]
)
def test_branch_patterns_are_asked_right_after_the_branch_model_once_naming_is_answered(
    naming: str,
) -> None:
    """AC-1. expected_behavior_source: the interface decision (branch_patterns: value is None AND
    branch_naming.value is not None and not 'none'; the order is branch_model, branch_patterns,
    release_flow, ...)."""
    ids = ids_of(with_naming(draft(), naming))

    assert ids == ["repository.target_branch", "repository.commit_convention", *NEW_KEYS]


@pytest.mark.parametrize("naming", ["none", "None", "NONE"], ids=["lower", "capitalised", "upper"])
def test_branch_patterns_are_not_asked_when_the_naming_rule_is_none_in_any_letter_case(
    naming: str,
) -> None:
    """AC-1, AC-2. expected_behavior_source: the interface decision ("branch_naming.value is not
    None AND not 'none', compared case-insensitively") and ADR-003 decision 2 (`none` means the
    team has no rule)."""
    ids = ids_of(with_naming(draft(), naming))

    assert BRANCH_PATTERNS not in ids
    assert [key for key in NEW_KEYS if key != BRANCH_PATTERNS] == [
        key for key in ids if key in NEW_KEYS
    ]


def test_branch_patterns_are_not_asked_while_the_naming_rule_is_unknown() -> None:
    """AC-1. expected_behavior_source: the interface decision (branch_patterns only when
    branch_naming.value is not None; the other new questions are asked)."""
    profile = draft()
    assert profile.repository.branch_naming.value is None

    ids = ids_of(profile)

    assert BRANCH_MODEL in ids
    assert BRANCH_PATTERNS not in ids


@pytest.mark.parametrize(
    "key",
    [pytest.param(key, id=short(key)) for key in NEW_KEYS],
)
@pytest.mark.parametrize("text", ["answer", "none"], ids=["an-answer", "the-answer-none"])
def test_a_fact_that_has_an_answer_is_not_asked_again_and_the_others_still_are(
    key: str, text: str
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("a question is asked again only while the fact is
    unknown"; "The answer none is recorded as a value and the fact is no longer unknown") and the
    interface decision ("A fact that has an answer (including the answer `none`) is not asked
    again"). The naming rule is answered, so that branch_patterns is a question of its own."""
    value = ACCEPTED[key] if text == "answer" else "none"
    profile = with_naming(with_answers(draft(), {key: value}), "feature/*")
    assert not is_unknown(profile, key)

    ids = ids_of(profile)

    assert ids == [
        "repository.target_branch",
        "repository.commit_convention",
        *[other for other in NEW_KEYS if other != key],
    ]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (MERGE_STRATEGY, "squash, then rebase when the history is long"),
        (REVIEWERS, "whoever is free"),
    ],
    ids=["merge-strategy", "reviewers"],
)
def test_a_plain_text_other_than_unknown_means_that_the_fact_is_answered(
    key: str, value: str
) -> None:
    """AC-2. expected_behavior_source: the interface decision (`pull_requests.merge_strategy
    (value == 'unknown')`, `pull_requests.reviewers (value == 'unknown')`: the text `unknown` is
    the unanswered state, ADR-003 decision 1). A profile written by hand holds any text. The
    other new questions are still asked."""
    profile = with_answers(draft(), {key: value})

    assert ids_of(profile) == [*THREE, *[other for other in ASKED_AT_FIRST if other != key]]


@pytest.mark.parametrize("key", [MERGE_STRATEGY, REVIEWERS], ids=["merge-strategy", "reviewers"])
def test_a_plain_text_that_is_unknown_is_asked(key: str) -> None:
    """AC-1. expected_behavior_source: the interface decision (`value == 'unknown'` is asked) and
    ADR-003 decision 1 (the text `unknown` is their unanswered state)."""
    profile = draft()
    assert stored(profile, key) == "unknown"

    assert key in ids_of(profile)


def test_every_new_question_has_a_text_to_show() -> None:
    """AC-1. expected_behavior_source: the interface decision (a Question for each key; only the
    ids and the order are pinned, so only that the text is not empty)."""
    questions = {
        q.id: q for q in questions_for(with_naming(draft(), "feature/*"), asks_stack=False)
    }

    assert set(NEW_KEYS) <= set(questions)
    for key in NEW_KEYS:
        assert questions[key].text.strip(), key


# --- AC-2: an empty answer, the answer none -------------------------------------------------------


def test_collect_answers_drops_an_empty_answer_and_keeps_none_and_strips() -> None:
    """AC-2. expected_behavior_source: the interface decision (`collect_answers` is unchanged: an
    empty answer is dropped, so the fact stays unknown; the answer `none` is a value) and AC-2
    ("an empty answer keeps the fact unknown")."""
    questions = questions_for(draft(), asks_stack=False)
    supplied = {BRANCH_MODEL: "", RELEASE_FLOW: "none", SHAPE: "  one change per pull request  "}

    answers = collect_answers(questions, supplied, ScriptedPrompter(interactive=False))

    assert answers == {RELEASE_FLOW: "none", SHAPE: "one change per pull request"}


def test_an_empty_answer_keeps_the_fact_unknown_and_the_question_is_asked_again() -> None:
    """AC-2. expected_behavior_source: AC-2 ("an empty answer keeps the fact unknown; a question is
    asked again only while the fact is unknown") and the interface decision (an empty answer is
    dropped by `collect_answers`). A person who presses return at every new question."""
    base = draft()
    questions = questions_for(base, asks_stack=False)
    prompter = ScriptedPrompter(dict.fromkeys([*THREE, *NEW_KEYS], ""), interactive=True)

    answers = collect_answers(questions, {}, prompter)
    result, notes = apply(base, answers)

    assert answers == {}
    assert notes == []
    assert result == base
    assert prompter.asked == [question.id for question in questions]
    assert set(ASKED_AT_FIRST) <= set(prompter.asked)
    assert ids_of(result) == [question.id for question in questions]


def test_the_answer_none_given_to_a_question_is_recorded_and_not_asked_again() -> None:
    """AC-2. expected_behavior_source: AC-2 ("The answer none is recorded as a value and the fact
    is no longer unknown"), ADR-003 decision 2 and the interface decision (the answer `none` is a
    value; a fact that has an answer is not asked again)."""
    base = draft()
    questions = questions_for(base, asks_stack=False)
    supplied = dict.fromkeys(ASKED_AT_FIRST, "none")

    answers = collect_answers(questions, supplied, ScriptedPrompter(interactive=False))
    result, notes = apply(base, answers)

    assert answers == supplied
    assert notes == []
    for key in ASKED_AT_FIRST:
        assert recorded_as(result, key, "none"), key
        assert not is_unknown(result, key), key
    assert ids_of(result) == list(THREE)


# --- AC-1: what an accepted answer is recorded as -------------------------------------------------


@per_key((BRANCH_MODEL, BRANCH_PATTERNS, RELEASE_FLOW, SHAPE, REQUIRED_CHECKS))
def test_an_accepted_answer_to_a_fact_is_recorded_as_the_maintainers(key: str) -> None:
    """AC-1. expected_behavior_source: the interface decision (`apply_answers` records an accepted
    answer as FactValue(value=text, answered_by='maintainer') for the five FactValue fields) and
    ADR-003 decision 1."""
    result, notes = apply(draft(), {key: ACCEPTED[key]})

    assert notes == []
    assert stored(result, key) == FactValue(value=ACCEPTED[key], answered_by="maintainer")


@per_key((MERGE_STRATEGY, REVIEWERS))
def test_an_accepted_answer_to_merge_strategy_or_reviewers_is_recorded_as_plain_text(
    key: str,
) -> None:
    """AC-1. expected_behavior_source: the interface decision ("the plain string for merge_strategy
    and reviewers") and ADR-003 decision 1 (they keep their type)."""
    result, notes = apply(draft(), {key: ACCEPTED[key]})

    assert notes == []
    assert stored(result, key) == ACCEPTED[key]


def test_the_seven_answers_can_be_given_together_and_all_are_recorded() -> None:
    """AC-1. expected_behavior_source: AC-1 ("init and profile answer accept ...") and the
    interface decision (each key is recorded)."""
    result, notes = apply(draft(), ACCEPTED)

    assert notes == []
    for key, text in ACCEPTED.items():
        assert recorded_as(result, key, text), key


@per_key()
def test_one_answer_changes_that_fact_only_and_the_nested_keys_keep_their_neighbours(
    key: str,
) -> None:
    """AC-1. expected_behavior_source: the interface decision ("the nested keys update
    `repository.pull_requests` by model_copy, and the other pull_requests fields (template, the
    other new fields) are kept") and ADR-003 decision 1. Every other new fact holds the answer
    `none` and the template names a file, so that a rebuild of `pull_requests` would lose one."""
    others = {other: "none" for other in NEW_KEYS if other != key}
    base = with_answers(draft(), others)
    template = base.repository.pull_requests.template.model_copy(
        update={"targets": (".github/pull_request_template.md",), "status": "provisioned"}
    )
    repository = base.repository.model_copy(
        update={
            "pull_requests": base.repository.pull_requests.model_copy(update={"template": template})
        }
    )
    base = base.model_copy(update={"repository": repository})

    result, notes = apply(base, {key: ACCEPTED[key]})

    assert notes == []
    assert recorded_as(result, key, ACCEPTED[key])
    assert result == with_answers(base, {key: ACCEPTED[key]})
    assert result.repository.pull_requests.template == template
    for other in others:
        assert recorded_as(result, other, "none"), other


@per_key((SHAPE, RELEASE_FLOW, REVIEWERS, BRANCH_PATTERNS, REQUIRED_CHECKS))
def test_the_stored_value_is_the_text_as_given_but_stripped(key: str) -> None:
    """AC-1. expected_behavior_source: the interface decision ("The stored value is the text as
    given, stripped")."""
    result, notes = apply(draft(), {key: f"   {ACCEPTED[key]}  "})

    assert notes == []
    assert recorded_as(result, key, ACCEPTED[key])


@per_key()
def test_the_answer_none_is_a_recorded_value_for_every_key(key: str) -> None:
    """AC-2. expected_behavior_source: AC-2 ("The answer none is recorded as a value and the fact
    is no longer unknown"), ADR-003 decision 2 and the interface decision ("`none` is accepted for
    every key")."""
    base = draft()
    assert is_unknown(base, key)

    result, notes = apply(base, {key: "none"})

    assert notes == []
    assert recorded_as(result, key, "none")
    assert not is_unknown(result, key)


@per_key()
def test_an_answer_that_is_already_recorded_changes_nothing(key: str) -> None:
    """AC-2. expected_behavior_source: the interface decision (the stored value is the text as
    given: the same answer twice gives the same profile, which `profile answer` reports as
    ORQ-E162). The first answer is recorded."""
    once, _ = apply(draft(), {key: ACCEPTED[key]})
    assert recorded_as(once, key, ACCEPTED[key])

    twice, notes = apply(once, {key: ACCEPTED[key]})

    assert notes == []
    assert twice == once


# --- AC-1: the vocabulary of branch_model and merge_strategy --------------------------------------


@pytest.mark.parametrize(
    "value",
    ["trunk-based", "github-flow", "gitflow", "none", "other: release trains", "other: x"],
)
def test_branch_model_accepts_its_vocabulary_and_other_with_a_text(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("repository.branch_model (trunk-based, github-flow,
    gitflow, other: text)"), ADR-003 decision 2 and the interface decision (trunk-based,
    github-flow, gitflow, none, or `other: <text>`)."""
    result, notes = apply(draft(), {BRANCH_MODEL: value})

    assert notes == []
    assert recorded_as(result, BRANCH_MODEL, value)


@pytest.mark.parametrize(
    "value",
    [
        "svn-flow",
        "trunk based",
        "git-flow",
        "trunk-based, gitflow",
        "trunk-based and gitflow",
        "other",
        "other:",
        "other:   ",
    ],
)
def test_branch_model_refuses_a_value_outside_its_vocabulary(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("refuse a value that fails the vocabulary ... with a
    note that names the key") and the interface decision (branch_model must be one of trunk-based,
    github-flow, gitflow, none, or `other: <text>` with non-empty text after the colon)."""
    assert_refused(draft(), BRANCH_MODEL, value)


@pytest.mark.parametrize(
    "value",
    ["squash", "rebase", "merge-commit", "none", "other: fast-forward only", "other: x"],
)
def test_merge_strategy_accepts_its_vocabulary_and_other_with_a_text(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("repository.pull_requests.merge_strategy (squash,
    rebase, merge-commit, other: text)"), ADR-003 decision 2 and the interface decision (squash,
    rebase, merge-commit, none, or `other: <text>`)."""
    result, notes = apply(draft(), {MERGE_STRATEGY: value})

    assert notes == []
    assert recorded_as(result, MERGE_STRATEGY, value)


@pytest.mark.parametrize(
    "value",
    [
        "fast-forward",
        "merge commit",
        "merge",
        "squash and merge",
        "squash, rebase",
        "other",
        "other:",
        "other:   ",
    ],
)
def test_merge_strategy_refuses_a_value_outside_its_vocabulary(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("refuse a value that fails the vocabulary ... with a
    note that names the key") and the interface decision (merge_strategy must be one of squash,
    rebase, merge-commit, none, or `other: <text>`)."""
    assert_refused(draft(), MERGE_STRATEGY, value)


def test_a_refused_answer_does_not_stop_the_good_ones_and_only_it_has_a_note() -> None:
    """AC-1. expected_behavior_source: the interface decision (an answer is ignored with a note that
    contains the key; the rest is applied, as for every answer today)."""
    base = draft()

    result, notes = apply(base, {BRANCH_MODEL: "svn-flow", SHAPE: ACCEPTED[SHAPE]})

    assert recorded_as(result, SHAPE, ACCEPTED[SHAPE])
    assert is_unknown(result, BRANCH_MODEL)
    assert any(BRANCH_MODEL in note for note in notes), notes
    assert not any(SHAPE in note for note in notes), notes


# --- AC-1: the length of an answer ----------------------------------------------------------------


@per_key(FREE_TEXT_KEYS)
def test_a_free_text_answer_of_200_characters_is_accepted_and_one_of_201_is_refused(
    key: str,
) -> None:
    """AC-1. expected_behavior_source: the interface decision (`text_problems(value, 200)`: an
    answer of 200 characters passes) and ADR-003 decision 2 ("inside the existing answer limit of
    200 characters")."""
    base = draft()
    result, notes = apply(base, {key: "x" * 200})
    assert notes == []
    assert recorded_as(result, key, "x" * 200)

    assert_refused(base, key, "x" * 201)


@per_key((BRANCH_MODEL, MERGE_STRATEGY))
def test_an_other_answer_of_200_characters_is_accepted_and_one_of_201_is_refused(key: str) -> None:
    """AC-1. expected_behavior_source: the interface decision (`text_problems(value, 200)` applies
    to any of the seven keys, `other: <text>` included)."""
    base = draft()
    result, notes = apply(base, {key: "other: " + "x" * 193})
    assert notes == []
    assert recorded_as(result, key, "other: " + "x" * 193)

    assert_refused(base, key, "other: " + "x" * 194)


@per_key()
def test_an_answer_over_the_limit_is_refused_without_showing_a_part_of_it(key: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a note that names the key") and ADR-003 decision 4
    (nothing from the value in a message)."""
    value = hostile_answer(key, "x" * 190)

    notes = assert_refused(draft(), key, value)

    assert_no_part_of(value, notes)


# --- AC-1: the two lists --------------------------------------------------------------------------


@pytest.mark.parametrize("separator", [",", ", "], ids=["no-blank", "blank"])
@per_key(LIST_KEYS)
def test_a_list_of_12_items_is_accepted_and_one_of_13_is_refused(key: str, separator: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 2 ("comma-separated lists of at most 12
    items") and the interface decision (at most 12 non-empty items; blanks around a comma are
    trimmed when counting items). Both lists are well under 160 characters."""
    make = LIST_ITEMS[key]
    twelve, thirteen = separator.join(make(12)), separator.join(make(13))
    assert len(thirteen) < 160
    assert all(pattern_problems(item) == () for item in make(13))
    base = draft()

    result, notes = apply(base, {key: twelve})
    assert notes == []
    assert recorded_as(result, key, twelve)

    assert_refused(base, key, thirteen)


@per_key(LIST_KEYS)
def test_an_item_of_60_characters_is_accepted_and_one_of_61_is_refused(key: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 2 ("items of at most 60 characters") and
    the interface decision (at most 60 characters each)."""
    base = draft()
    result, notes = apply(base, {key: "a" * 60})
    assert notes == []
    assert recorded_as(result, key, "a" * 60)

    assert_refused(base, key, "a" * 61)
    assert_refused(base, key, f"ok,{'a' * 61},ok")


@per_key(LIST_KEYS)
def test_blanks_around_a_comma_are_not_counted_in_the_length_of_an_item(key: str) -> None:
    """AC-1. expected_behavior_source: the interface decision ("blanks around a comma are trimmed
    when counting items"): an item of 60 characters next to a comma with blanks is 60 characters."""
    value = f"{'a' * 60} , b"

    result, notes = apply(draft(), {key: value})

    assert notes == []
    assert recorded_as(result, key, value)


@per_key(LIST_KEYS)
def test_a_list_of_160_characters_is_accepted_and_one_of_161_is_refused(key: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 2 ("whose whole text is at most 160
    characters") and the interface decision (the whole text is at most 160 characters). Every item
    is within 60 characters and there are 3 items, so only the whole text differs; no blank."""
    at_the_limit = ",".join(["a" * 60, "b" * 60, "c" * 38])
    over_the_limit = ",".join(["a" * 60, "b" * 60, "c" * 39])
    assert (len(at_the_limit), len(over_the_limit)) == (160, 161)
    base = draft()

    result, notes = apply(base, {key: at_the_limit})
    assert notes == []
    assert recorded_as(result, key, at_the_limit)

    assert_refused(base, key, over_the_limit)


@per_key(LIST_KEYS)
def test_one_bad_item_refuses_the_whole_list(key: str) -> None:
    """AC-1. expected_behavior_source: the interface decision (an answer that fails is ignored
    whole; a list of 13 items has 12 good ones)."""
    value = ",".join(["ok", "a" * 61])

    assert_refused(draft(), key, value)


@pytest.mark.parametrize(
    "pattern",
    [
        "feature/**/**",
        "**/a/**",
        "a/b/c/d/e/f/g/h/i",
        "feature/[x]",
        "/feature",
        "feature/../x",
        "feature x/*",
    ],
    ids=[
        "two-double-stars",
        "two-double-stars-apart",
        "nine-segments",
        "bracket",
        "leading-slash",
        "climbs-out",
        "inner-blank",
    ],
)
def test_branch_patterns_refuse_an_item_that_fails_pattern_problems(pattern: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 2 (a pattern has at most one `**` and at
    most 8 segments) and the interface decision (every branch_patterns item must have
    `pattern_problems(item) == ()`, so a pattern with two `**` is refused). The pattern alone and
    among good ones."""
    assert pattern_problems(pattern) != ()
    base = draft()

    assert_refused(base, BRANCH_PATTERNS, pattern)
    assert_refused(base, BRANCH_PATTERNS, f"feature/*, {pattern}, fix/*")


@pytest.mark.parametrize(
    "pattern",
    ["feature/*", "release/**", "a/b/c/d/e/f/g/h", "hotfix-?", "main", "v1.2.x", "**/ticket-*"],
)
def test_branch_patterns_accept_an_item_that_passes_pattern_problems(pattern: str) -> None:
    """AC-1. expected_behavior_source: the interface decision (an item with
    `pattern_problems(item) == ()` is accepted) and ADR-003 decision 2 (one `**`, 8 segments)."""
    assert pattern_problems(pattern) == ()

    result, notes = apply(draft(), {BRANCH_PATTERNS: pattern})

    assert notes == []
    assert recorded_as(result, BRANCH_PATTERNS, pattern)


def test_required_checks_are_names_and_not_branch_patterns() -> None:
    """AC-1. expected_behavior_source: the interface decision (only branch_patterns items must pass
    `pattern_problems`; required_checks are a comma-separated list within the caps and
    `text_problems`)."""
    value = "Unit tests (3.12), Lint & types"
    assert pattern_problems("Unit tests (3.12)") != ()

    result, notes = apply(draft(), {REQUIRED_CHECKS: value})

    assert notes == []
    assert recorded_as(result, REQUIRED_CHECKS, value)


# --- AC-1: text_problems and hostile values -------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "mark"),
    [
        pytest.param(key, mark, id=f"{short(key)}-{name}")
        for key in NEW_KEYS
        for name, mark in HOSTILE.items()
    ],
)
def test_a_hostile_answer_is_refused_with_a_note_that_names_the_key_and_holds_no_part_of_it(
    key: str, mark: str
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("refuse a value that fails ... text_problems with a
    note that names the key"), the interface decision (an answer for any of the seven keys is
    ignored with a note that contains the key when it fails `text_problems(value, 200)`) and
    ADR-003 decision 2 (ASCII only, one line, no link or markup sequences) and decision 4 (nothing
    from the value in a message). The marks are an escape, a backtick, `://`, U+202E, a line break
    and the like."""
    assert text_problems(f"{HEAD}{mark}{TAIL}", 200) != ()
    value = hostile_answer(key, mark)

    notes = assert_refused(draft(), key, value)

    assert_no_part_of(value, notes)


@pytest.mark.parametrize("mark", list(HOSTILE.values()), ids=list(HOSTILE))
def test_a_hostile_item_in_a_list_refuses_the_whole_list_and_is_not_shown(mark: str) -> None:
    """AC-1. expected_behavior_source: the interface decision (text_problems applies to the text of
    a list too) and ADR-003 decision 2."""
    for key in LIST_KEYS:
        value = f"ok, {HEAD}{mark}{TAIL}, fine"

        notes = assert_refused(draft(), key, value)

        assert_no_part_of(value, notes)


# --- AC-4: what doctor says about the conventions -------------------------------------------------


def test_doctor_prints_one_information_finding_for_the_unknown_conventions() -> None:
    """AC-4. expected_behavior_source: AC-4 ("prints ORQ-I502 as information only"), ADR-003
    decision 2 ("reported by one information finding") and the interface decision (one INFO finding
    ORQ-I502 when at least one of the seven new facts is unknown, whose message names each unknown
    key). A draft install: every convention is unknown (branch_patterns is not checked here, see the
    header)."""
    found = with_code(diagnose(installed(approved=False)), "ORQ-I502")

    assert len(found) == 1
    assert found[0].severity is Severity.INFO
    for key in ASKED_AT_FIRST:
        assert names(found[0].message, key), key


def test_the_finding_names_branch_patterns_when_the_naming_rule_is_answered() -> None:
    """AC-4. expected_behavior_source: the interface decision (ORQ-I502 names each unknown key,
    `branch_patterns` among them). The naming rule is answered by the install."""
    found = with_code(diagnose(installed()), "ORQ-I502")

    assert len(found) == 1
    for key in NEW_KEYS:
        assert names(found[0].message, key), key


@per_key()
def test_the_finding_names_the_one_convention_that_is_unknown_and_none_of_the_others(
    key: str,
) -> None:
    """AC-4. expected_behavior_source: the interface decision (a message that "names each unknown
    key"; no ORQ-I502 for a fact that is answered). The other six are answered by hand, the naming
    rule is answered by the install; the keys with an underscore are checked for absence."""
    env = installed()
    set_conventions(env, {other: ACCEPTED[other] for other in NEW_KEYS if other != key})

    found = with_code(diagnose(env), "ORQ-I502")

    assert len(found) == 1
    assert found[0].severity is Severity.INFO
    assert names(found[0].message, key)
    for other in UNDERSCORED_KEYS:
        if other != key:
            assert not names(found[0].message, other), other


@pytest.mark.parametrize("text", ["answer", "none"], ids=["answers", "the-answer-none"])
def test_doctor_prints_no_such_finding_when_no_convention_is_unknown(text: str) -> None:
    """AC-4. expected_behavior_source: the interface decision (no ORQ-I502 when none is unknown)
    and AC-2 (the answer none is no longer unknown). With one fact still unknown the finding is
    there; once that fact is answered too, it is gone."""
    answers = {key: ACCEPTED[key] if text == "answer" else "none" for key in NEW_KEYS}
    env = installed()
    set_conventions(env, {key: value for key, value in answers.items() if key != SHAPE})
    assert len(with_code(diagnose(env), "ORQ-I502")) == 1

    set_conventions(env, {SHAPE: answers[SHAPE]})

    assert with_code(diagnose(env), "ORQ-I502") == []


def test_doctor_reads_a_profile_written_before_the_change_and_lists_its_unknown_conventions() -> (
    None
):
    """AC-4. expected_behavior_source: AC-4 ("doctor exits as before for an existing install that
    has none of the new answers and prints ORQ-I502 as information only"), ADR-003 decision 1 (an
    existing profile still loads) and the interface decision (use a profile document written
    without the new fields)."""
    env = installed(legacy=True)

    diagnosis = diagnose(env)

    (found,) = with_code(diagnosis, "ORQ-I502")
    assert found.severity is Severity.INFO
    for key in NEW_KEYS:
        assert names(found.message, key), key


def test_an_approved_existing_install_keeps_its_exit_code_and_gains_no_warning() -> None:
    """AC-4. expected_behavior_source: AC-4 ("doctor exits as before for an existing install that
    has none of the new answers"), ADR-003 decision 2 ("the exit code of `doctor` for an existing
    install does not change when it upgrades") and the interface decision (neither finding adds a
    warning or an error). Before: an approved profile with its three facts answered exits 0."""
    diagnosis = diagnose(installed(legacy=True))

    assert with_code(diagnosis, "ORQ-I502")
    assert problems_of(diagnosis) == []
    assert exit_code_of(diagnosis) == 0


def test_a_draft_existing_install_keeps_its_warnings_and_its_exit_code() -> None:
    """AC-4. expected_behavior_source: AC-4 (exit as before; "ORQ-W181 still lists only
    target_branch, branch_naming and commit_convention") and the interface decision (no warning or
    error is added). Before: a draft with nothing answered has ORQ-W180 and ORQ-W181 and exits 1."""
    diagnosis = diagnose(installed(approved=False, legacy=True))

    assert with_code(diagnosis, "ORQ-I502")
    assert {finding.code for finding in problems_of(diagnosis)} == {"ORQ-W180", "ORQ-W181"}
    assert exit_code_of(diagnosis) == 1


def test_the_warning_about_unknown_facts_lists_the_three_old_facts_and_no_new_one() -> None:
    """AC-4. expected_behavior_source: AC-4 ("ORQ-W181 still lists only repository.target_branch,
    branch_naming and commit_convention") and ADR-003 decision 2 ("Report the new unknown facts as
    ORQ-W181" is rejected). This holds before the change as well: it guards the warning."""
    env = installed(approved=False)

    (found,) = with_code(diagnose(env), "ORQ-W181")

    assert "3 fact(s)" in found.message
    for key in THREE:
        assert key in found.message
    for key in NEW_KEYS:
        assert key not in found.message
    for key in UNDERSCORED_KEYS:
        assert not names(found.message, key)


def test_the_open_questions_of_a_profile_are_the_three_old_facts_whatever_the_new_ones_are() -> (
    None
):
    """AC-4. expected_behavior_source: the interface decision ("`open_questions(profile)` is
    unchanged") and ADR-003 decision 2 (the unknown conventions are not added to open_questions).
    This holds before the change as well: it guards the list."""
    base = draft()
    answered_all = with_answers(base, ACCEPTED)

    assert [q.id for q in open_questions(base)] == list(THREE)
    assert [q.id for q in open_questions(answered_all)] == list(THREE)
    assert [q.id for q in open_questions(written_profile(installed(approved=False)))] == list(THREE)


@per_key(HOST_ENFORCED_KEYS)
def test_doctor_prints_one_information_finding_when_a_convention_that_the_host_enforces_is_answered(
    key: str,
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("ORQ-I503 is printed when a host-enforced convention
    is answered"), ADR-003 decision 6 ("doctor prints one information finding when any of these is
    answered: Orqlet cannot read the host, so confirm the branch protection settings") and the
    interface decision (merge_strategy, reviewers, required_checks, shape or release_flow with a
    value that is neither unknown nor `none`)."""
    env = installed()
    set_conventions(env, {key: ACCEPTED[key]})

    found = with_code(diagnose(env), "ORQ-I503")

    assert len(found) == 1
    assert found[0].severity is Severity.INFO
    message = found[0].message.lower()
    assert "host" in message
    assert "branch protection" in message
    assert "confirm" in message


def test_one_finding_is_printed_however_many_conventions_the_host_enforces() -> None:
    """AC-4. expected_behavior_source: the interface decision ("One INFO finding ORQ-I503 when at
    least one of ...") and ADR-003 decision 6 ("one information finding")."""
    env = installed()
    set_conventions(env, {key: ACCEPTED[key] for key in HOST_ENFORCED_KEYS})

    found = with_code(diagnose(env), "ORQ-I503")

    assert len(found) == 1


def test_no_host_finding_is_printed_when_no_convention_is_answered() -> None:
    """AC-4. expected_behavior_source: the interface decision (ORQ-I503 only for an answered
    convention of the five) and ADR-003 decision 6. The same install with one answer has it."""
    assert with_code(diagnose(installed()), "ORQ-I503") == []
    assert with_code(diagnose(installed(legacy=True)), "ORQ-I503") == []
    answered_one = installed()
    set_conventions(answered_one, {MERGE_STRATEGY: ACCEPTED[MERGE_STRATEGY]})
    assert len(with_code(diagnose(answered_one), "ORQ-I503")) == 1


def test_no_host_finding_is_printed_when_the_five_are_none() -> None:
    """AC-4. expected_behavior_source: the interface decision ("a value that is neither unknown nor
    `none`") and ADR-003 decision 2 (`none` means the team has no rule: nothing for the host to
    enforce). One real answer among the `none` brings the finding back."""
    env = installed()
    set_conventions(env, dict.fromkeys(HOST_ENFORCED_KEYS, "none"))
    assert with_code(diagnose(env), "ORQ-I503") == []

    set_conventions(env, {REVIEWERS: ACCEPTED[REVIEWERS]})

    assert len(with_code(diagnose(env), "ORQ-I503")) == 1


def test_no_host_finding_is_printed_for_the_two_conventions_that_the_host_does_not_enforce() -> (
    None
):
    """AC-4. expected_behavior_source: the interface decision (only merge_strategy, reviewers,
    required_checks, shape and release_flow count) and ADR-003 decision 6 (branch model and branch
    naming are told or checked by the tool, not by the host). With a fifth convention answered the
    finding is there."""
    env = installed()
    set_conventions(
        env, {BRANCH_MODEL: ACCEPTED[BRANCH_MODEL], BRANCH_PATTERNS: ACCEPTED[BRANCH_PATTERNS]}
    )
    assert with_code(diagnose(env), "ORQ-I503") == []

    set_conventions(env, {SHAPE: ACCEPTED[SHAPE]})

    assert len(with_code(diagnose(env), "ORQ-I503")) == 1


def test_every_convention_answered_keeps_the_exit_code_of_an_approved_install() -> None:
    """AC-4. expected_behavior_source: AC-4 ("ORQ-I503 is printed ..." and the exit code as before)
    and the interface decision (neither finding changes the exit code of doctor)."""
    env = installed()
    set_conventions(env, ACCEPTED)

    diagnosis = diagnose(env)

    assert with_code(diagnosis, "ORQ-I503")
    assert with_code(diagnosis, "ORQ-I502") == []
    assert problems_of(diagnosis) == []
    assert exit_code_of(diagnosis) == 0


def test_the_new_findings_are_for_doctor_and_not_for_sync() -> None:
    """AC-4. expected_behavior_source: the interface decision ("`doctor`, full mode only; `sync`
    unchanged"). `doctor` prints both findings for this install; `sync` prints neither."""
    env = installed(approved=False)
    set_conventions(env, {key: ACCEPTED[key] for key in HOST_ENFORCED_KEYS})
    assert with_code(diagnose(env), "ORQ-I503")

    diagnosis = sync(env.services())

    assert with_code(diagnosis, "ORQ-I502") == []
    assert with_code(diagnosis, "ORQ-I503") == []


def test_a_hand_edited_profile_with_hostile_text_is_never_echoed_raw_by_doctor() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 4 ("one function (`printable`) escapes
    every echo of text that comes from the repository (... the profile ...) by `validate
    resources`, `doctor` and `resources list`"): a team's profile is read from a file that a pull
    request may change, so the messages of the new findings are printable ASCII on one line, and
    show no marker of the value unescaped."""
    env = installed()
    hostile = dict.fromkeys(HOST_ENFORCED_KEYS, f"{HEAD}\x1b[31m\u202e\n`://{TAIL}")
    set_conventions(env, hostile)

    diagnosis = diagnose(env)

    found = [*with_code(diagnosis, "ORQ-I502"), *with_code(diagnosis, "ORQ-I503")]
    assert with_code(diagnosis, "ORQ-I503")
    for finding in found:
        assert printable_line(finding.message), finding.message
        assert "\x1b" not in finding.message
        assert "\u202e" not in finding.message
