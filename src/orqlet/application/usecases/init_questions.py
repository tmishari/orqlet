"""The consolidated questionnaire of `init` and how answers become profile facts."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Literal

from orqlet.application.contracts.common import FactValue
from orqlet.application.contracts.profile import (
    Facts,
    NamedFact,
    ProfileMeta,
    ProjectInfo,
    ProjectProfile,
    PullRequests,
    Repository,
    StackInfo,
    TargetBranch,
    Technology,
    TechnologyKind,
)
from orqlet.application.ports.prompter import NoAnswerAvailable, Prompter, Question
from orqlet.application.usecases.draft_profile import Origin, wants_python_questions
from orqlet.domain.conventions import pattern_problems
from orqlet.domain.resources import text_problems

ANSWER_KEYS = frozenset(
    {
        "facts.python",
        "facts.package_manager",
        "facts.frameworks",
        "project.kind",
        "structure.test_runner",
        "repository.target_branch",
        "repository.branch_naming",
        "repository.commit_convention",
        "repository.branch_model",
        "repository.branch_patterns",
        "repository.release_flow",
        "repository.pull_requests.shape",
        "repository.pull_requests.merge_strategy",
        "repository.pull_requests.reviewers",
        "repository.pull_requests.required_checks",
        "technologies",
    }
)
PACKAGE_MANAGERS = ("uv", "poetry", "pdm", "pipenv", "pip")
PROJECT_KINDS = ("python-cli", "python-service")
_KINDS: dict[str, Literal["python-cli", "python-service"]] = {
    "python-cli": "python-cli",
    "python-service": "python-service",
}
NEW_PROJECT_ORIGINS: frozenset[Origin] = frozenset({"empty", "unborn", "existing-no-code"})
_BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
_MAX_ANSWER = 200
_BRANCH_MODELS = ("trunk-based", "github-flow", "gitflow")
_MERGE_STRATEGIES = ("squash", "rebase", "merge-commit")
_VOCABULARIES = {
    "repository.branch_model": _BRANCH_MODELS,
    "repository.pull_requests.merge_strategy": _MERGE_STRATEGIES,
}
_LISTS = frozenset({"repository.branch_patterns", "repository.pull_requests.required_checks"})
_CONVENTION_KEYS = frozenset(
    {
        "repository.branch_model",
        "repository.branch_patterns",
        "repository.release_flow",
        "repository.pull_requests.shape",
        "repository.pull_requests.merge_strategy",
        "repository.pull_requests.reviewers",
        "repository.pull_requests.required_checks",
    }
)
_MAX_LIST_ITEMS = 12
_MAX_LIST_ITEM = 60
_MAX_LIST_TEXT = 160
_OTHER = re.compile(r"other:\s*\S.*")


def questions_for(profile: ProjectProfile, *, asks_stack: bool) -> list[Question]:
    """The questions still open in `profile`, in the order they are asked."""
    origin = profile.project.origin
    new_project = origin in NEW_PROJECT_ORIGINS
    asked: list[Question] = []
    if asks_stack and wants_python_questions(profile):
        facts = profile.facts
        if facts.python.value is None:
            asked.append(
                Question(
                    "facts.python",
                    "Which Python versions does this project support? (for example >=3.12)",
                )
            )
        if facts.package_manager.value is None:
            asked.append(
                Question(
                    "facts.package_manager", "Which package manager does it use?", PACKAGE_MANAGERS
                )
            )
        if new_project and profile.project.kind == "unknown":
            asked.append(Question("project.kind", "What kind of project is it?", PROJECT_KINDS))
        if new_project and not facts.frameworks:
            asked.append(
                Question(
                    "facts.frameworks",
                    "Which frameworks does it use? (comma separated, or leave empty)",
                )
            )
        if new_project and "test_runner" not in profile.structure:
            asked.append(Question("structure.test_runner", "Which test runner does it use?"))
    if asks_stack and new_project and not profile.technologies:
        asked.append(
            Question(
                "technologies",
                "Which languages, frameworks, databases and queues will it use? Separate them "
                "with commas. A version goes after @ and a kind before a colon, for example "
                "language:Go@1.25, database:PostgreSQL@16, queue:Kafka (leave empty if unknown)",
            )
        )
    repo = profile.repository
    if repo.target_branch.value is None:
        asked.append(Question("repository.target_branch", "Which branch do pull requests target?"))
    if repo.branch_naming.value is None:
        asked.append(
            Question(
                "repository.branch_naming", "Is there a branch naming rule? (leave empty if not)"
            )
        )
    if repo.commit_convention.value is None:
        asked.append(
            Question(
                "repository.commit_convention",
                "Is there a commit message convention? (leave empty if not)",
            )
        )
    asked += _convention_questions(repo)
    return asked


def _convention_questions(repo: Repository) -> list[Question]:
    """The convention questions that are still open. An empty answer keeps a fact unknown."""
    pull_requests = repo.pull_requests
    naming = repo.branch_naming.value
    asked: list[Question] = []
    if repo.branch_model.value is None:
        asked.append(_open("repository.branch_model", repo.branch_model))
    if repo.branch_patterns.value is None and naming is not None and not _is_none(naming):
        asked.append(_open("repository.branch_patterns", repo.branch_patterns))
    if repo.release_flow.value is None:
        asked.append(_open("repository.release_flow", repo.release_flow))
    if pull_requests.shape.value is None:
        asked.append(_open("repository.pull_requests.shape", pull_requests.shape))
    if pull_requests.merge_strategy == "unknown":
        asked.append(
            Question(
                "repository.pull_requests.merge_strategy",
                "How are pull requests merged (squash, rebase, merge-commit, other: text, "
                "or none)? Leave empty if unknown.",
                default="",
            )
        )
    if pull_requests.reviewers == "unknown":
        asked.append(
            Question(
                "repository.pull_requests.reviewers",
                "Who reviews a pull request, and how many approvals are needed? Leave empty if "
                "unknown.",
                default="",
            )
        )
    if pull_requests.required_checks.value is None:
        asked.append(
            _open("repository.pull_requests.required_checks", pull_requests.required_checks)
        )
    return asked


def _open(key: str, fact: FactValue) -> Question:
    return Question(key, f"{fact.question} Leave empty if unknown, or answer none.", default="")


def _is_none(text: str) -> bool:
    return text.strip().lower() == "none"


def collect_answers(
    questions: Sequence[Question], supplied: Mapping[str, str], prompter: Prompter
) -> dict[str, str]:
    """Answers given with `--answer` win; the rest are asked when there is a terminal."""
    answers: dict[str, str] = {}
    for question in questions:
        if question.id in supplied:
            answers[question.id] = supplied[question.id].strip()
        elif prompter.interactive:
            try:
                answers[question.id] = prompter.ask(question).strip()
            except NoAnswerAvailable:
                break
    return {key: value for key, value in answers.items() if value}


def apply_answers(
    profile: ProjectProfile, answers: Mapping[str, str], notes: list[str]
) -> ProjectProfile:
    """Return the profile with every acceptable answer recorded as the maintainer's own."""
    stripped = {
        key: value.strip() if key in _CONVENTION_KEYS else value for key, value in answers.items()
    }
    accepted = {key: value for key, value in stripped.items() if _acceptable(key, value, notes)}
    facts, structure = profile.facts, dict(profile.structure)
    if "facts.python" in accepted:
        facts = facts.model_copy(update={"python": _answered(accepted["facts.python"])})
    if "facts.package_manager" in accepted:
        facts = facts.model_copy(
            update={"package_manager": _answered(accepted["facts.package_manager"])}
        )
    if "facts.frameworks" in accepted:
        names = [name.strip() for name in accepted["facts.frameworks"].split(",") if name.strip()]
        facts = facts.model_copy(
            update={
                "frameworks": tuple(
                    NamedFact(name=n, value=n, answered_by="maintainer") for n in names
                )
            }
        )
    if "structure.test_runner" in accepted:
        structure["test_runner"] = _answered(accepted["structure.test_runner"])
    repository = _repository(profile.repository, accepted)
    stated = _technologies(accepted.get("technologies", ""), notes)
    project = profile.project
    if "project.kind" in accepted:
        project = ProjectInfo(
            uuid=project.uuid,
            name=project.name,
            kind=_KINDS[accepted["project.kind"]],
            origin=project.origin,
        )
    return profile.model_copy(
        update={
            "facts": facts,
            "structure": structure,
            "repository": repository,
            "project": project,
            "technologies": (*profile.technologies, *stated),
            "stack": _stack(profile.stack, facts, project, stated),
        }
    )


_TECH_KINDS: dict[str, TechnologyKind] = {
    kind: kind
    for kind in (
        "language",
        "runtime",
        "framework",
        "library",
        "database",
        "queue",
        "infrastructure",
        "tool",
        "other",
    )
}
_TECHNOLOGY = re.compile(
    r"(?:(?P<kind>[a-z]+):)?(?P<name>[A-Za-z0-9][A-Za-z0-9 ._+/#-]{0,60}?)"
    r"(?:@(?P<version>[A-Za-z0-9._<>=^~*-]{1,30}))?"
)


def _technologies(text: str, notes: list[str]) -> list[Technology]:
    """Technologies the maintainer named, one per comma-separated entry. They need no evidence."""
    stated: list[Technology] = []
    for entry in (part.strip() for part in text.split(",")):
        if not entry:
            continue
        match = _TECHNOLOGY.fullmatch(entry)
        kind = match["kind"] if match else None
        if match is None or (kind is not None and kind not in _TECH_KINDS):
            notes.append(
                f"The technology {entry!r} was ignored: write it as [kind:]name[@version]."
            )
            continue
        stated.append(
            Technology(
                kind=_TECH_KINDS[kind or "other"],
                name=match["name"].strip(),
                version=match["version"],
                source="maintainer",
            )
        )
    return stated


def approve(profile: ProjectProfile, reviewer: str, now: datetime) -> ProjectProfile:
    meta = ProfileMeta(
        version=profile.profile.version,
        status="approved",
        reviewed_by=reviewer,
        reviewed_at=now.isoformat(),
    )
    return profile.model_copy(update={"profile": meta})


# --- internals ---------------------------------------------------------------------------
def _answered(text: str) -> FactValue:
    return FactValue(value=text, answered_by="maintainer")


def _repository(repository: Repository, accepted: Mapping[str, str]) -> Repository:
    changes: dict[str, object] = {}
    if "repository.target_branch" in accepted:
        changes["target_branch"] = TargetBranch(
            value=accepted["repository.target_branch"],
            remote=repository.target_branch.remote,
            answered_by="maintainer",
        )
    if "repository.branch_naming" in accepted:
        changes["branch_naming"] = _answered(accepted["repository.branch_naming"])
    if "repository.commit_convention" in accepted:
        changes["commit_convention"] = _answered(accepted["repository.commit_convention"])
    for name in ("branch_model", "branch_patterns", "release_flow"):
        if f"repository.{name}" in accepted:
            changes[name] = _answered(accepted[f"repository.{name}"])
    changes["pull_requests"] = _pull_requests(repository.pull_requests, accepted)
    return repository.model_copy(update=changes)


def _pull_requests(current: PullRequests, accepted: Mapping[str, str]) -> PullRequests:
    """The pull-request settings with the answers applied; the other fields are kept."""
    changes: dict[str, object] = {}
    for name in ("shape", "required_checks"):
        if f"repository.pull_requests.{name}" in accepted:
            changes[name] = _answered(accepted[f"repository.pull_requests.{name}"])
    for name in ("merge_strategy", "reviewers"):
        if f"repository.pull_requests.{name}" in accepted:
            changes[name] = accepted[f"repository.pull_requests.{name}"]
    return current.model_copy(update=changes)


def _stack(
    current: StackInfo, facts: Facts, project: ProjectInfo, stated: Sequence[Technology]
) -> StackInfo:
    """A project whose maintainer named a Python version is in the supported stack."""
    if current.support == "unsupported":
        return current
    if facts.python.value is not None and project.origin in NEW_PROJECT_ORIGINS:
        return StackInfo(support="supported")
    if stated and current.support in {"unknown", "unsupported"}:
        names = ", ".join(sorted({t.name for t in stated if t.kind == "language"} or {"them"}))
        return StackInfo(
            support="partly-covered",
            capability_limits=(
                f"You named {names}; Orqlet has no built-in standards for it. Rules come from "
                "the packs you supply and from the standards folder.",
            ),
        )
    return current


def _acceptable(key: str, value: str, notes: list[str]) -> bool:
    problem: str | None = None
    if len(value) > _MAX_ANSWER or "\n" in value or "\r" in value:
        problem = "is too long or has a line break"
    elif key == "facts.package_manager" and value not in PACKAGE_MANAGERS:
        problem = f"must be one of {', '.join(PACKAGE_MANAGERS)}"
    elif key == "project.kind" and value not in PROJECT_KINDS:
        problem = f"must be one of {', '.join(PROJECT_KINDS)}"
    elif key == "repository.target_branch" and (
        _BRANCH.fullmatch(value) is None
        or ".." in value
        or value.startswith("refs/")
        or value.endswith(("/", ".", ".lock"))
    ):
        problem = "is not a branch name Orqlet accepts"
    elif key in _CONVENTION_KEYS:
        problem = _convention_problem(key, value)
    if problem is not None:
        notes.append(f"The answer for {key} was ignored: it {problem}.")
    return problem is None


def _convention_problem(key: str, value: str) -> str | None:
    """Why a convention answer is refused, or `None`. The text reaches the agents' instructions."""
    if text_problems(value, _MAX_ANSWER):
        return "is not plain one-line text (ASCII, no link, markup or backtick)"
    if _is_none(value):
        return None
    vocabulary = _VOCABULARIES.get(key)
    if vocabulary is not None and value not in vocabulary and _OTHER.fullmatch(value) is None:
        return f"must be one of {', '.join(vocabulary)}, none, or other: and a text"
    if key in _LISTS:
        return _list_problem(key, value)
    return None


def _list_problem(key: str, value: str) -> str | None:
    items = [part.strip() for part in value.split(",")]
    if len(value) > _MAX_LIST_TEXT:
        return f"must be at most {_MAX_LIST_TEXT} characters"
    if len(items) > _MAX_LIST_ITEMS:
        return f"must have at most {_MAX_LIST_ITEMS} items"
    if any(not item or len(item) > _MAX_LIST_ITEM for item in items):
        return f"must have items of 1 to {_MAX_LIST_ITEM} characters, separated by commas"
    if key == "repository.branch_patterns" and any(pattern_problems(item) for item in items):
        return "has an item that is not a branch pattern (one ** at most, 8 segments, no spaces)"
    return None
