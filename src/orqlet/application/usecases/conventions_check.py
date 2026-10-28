"""`orqlet conventions check`: the two conventions that a tool can decide offline (ADR-003).

The branch name is checked against the branch patterns of the profile, and the subject of every
commit in `base..head` against the Conventional Commits shape. The rules are read from the profile
at the base revision, never from the pull request's own tree, so a pull request cannot relax the
rule that judges it. Everything else is `NOT_RUN` with its reason, and `PASS` is returned only when
every configured check ran and passed (the baseline: a check that did not run is never success).

Branch names and commit subjects are typed by a contributor. They reach the output only through
`printable` (ASCII, cut at 100 characters) and only after a fixed text, so no line starts with
contributor text. Nothing here runs a Git command that is not on the allow-list, opens a
connection or reads a credential.
"""

from __future__ import annotations

from dataclasses import dataclass

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.filesystem import FileKind, FileSystemError
from orqlet.application.ports.vcs import VcsError
from orqlet.application.usecases.validation import Collector, ValidateServices, ValidationResult
from orqlet.domain.conventions import (
    branch_problems,
    commit_subject_problems,
    is_checkable_convention,
    pattern_problems,
    printable,
)
from orqlet.domain.paths import CanonicalPath

_PROFILE_PATH = ".orqlet/project-profile.yaml"
_MAX_COMMITS = 200
_SHOWN = 100


@dataclass(frozen=True, slots=True)
class ConventionsRequest:
    branch: str | None = None
    base: str | None = None
    head: str = "HEAD"


def check_conventions(services: ValidateServices, request: ConventionsRequest) -> ValidationResult:
    out = Collector()
    counts = {"commits": 0}
    try:
        _check(services, request, out, counts)
    except VcsError:
        out.skip("a Git command failed or went over its limits, so the rest was not checked")
    return out.result({"commits": counts["commits"]})


def _check(
    services: ValidateServices,
    request: ConventionsRequest,
    out: Collector,
    counts: dict[str, int],
) -> None:
    vcs = services.vcs
    head = vcs.head_commit() if request.head == "HEAD" else vcs.resolve(request.head)
    if head is None:
        out.skip("the head does not name a commit in this repository")
        return
    base = _base(services, request, out)
    if base is None:
        return
    if not vcs.merge_bases(base, head):
        out.skip("the base and the head share no history (a shallow clone has none): no merge base")
        return
    profile = _profile_at(services, base, out)
    if profile is None:
        return
    patterns = _patterns(profile, out)
    convention = profile.repository.commit_convention.value
    checks_subjects = convention is not None and is_checkable_convention(convention)
    if convention is not None and convention.strip().lower() != "none" and not checks_subjects:
        out.skip("the commit convention is free text, so commit subjects are not checked")
    if not patterns and not checks_subjects:
        out.skip(
            "nothing is configured: the profile at the base has no branch patterns and no "
            "checkable commit convention"
        )
    if patterns:
        _check_branch(services, request, profile, patterns, out)
    if checks_subjects:
        counts["commits"] = _check_subjects(services, base, head, out)


def _base(services: ValidateServices, request: ConventionsRequest, out: Collector) -> str | None:
    vcs = services.vcs
    if request.base is not None:
        try:
            found = vcs.resolve(request.base)
        except VcsError:
            out.skip("the base name is not accepted (a shallow clone or a name with special signs)")
            return None
        if found is None:
            out.skip("the base does not name a commit in this repository")
        return found
    profile = _working_profile(services)
    target = None if profile is None else profile.repository.target_branch
    if target is None or target.value is None:
        out.skip("no base was given and the profile in the working tree names no target branch")
        return None
    for name in (f"{target.remote}/{target.value}", target.value):
        try:
            found = vcs.resolve(name)
        except VcsError:
            continue
        if found is not None:
            return found
    out.skip("the target branch is not known to this clone: pass --base")
    return None


def _working_profile(services: ValidateServices) -> ProjectProfile | None:
    path = CanonicalPath.parse(_PROFILE_PATH)
    try:
        if services.project.kind(path) is not FileKind.FILE:
            return None
        raw = services.project.read_bytes(path)
        return load_contract(services.loader, ProjectProfile, raw, source=_PROFILE_PATH)
    except (DocumentError, FileSystemError):
        return None


def _profile_at(services: ValidateServices, base: str, out: Collector) -> ProjectProfile | None:
    raw = services.vcs.read_at(base, _PROFILE_PATH)
    if raw is None:
        out.skip("the base revision has no project profile, so there are no rules to apply")
        return None
    try:
        return load_contract(services.loader, ProjectProfile, raw, source=_PROFILE_PATH)
    except DocumentError:
        out.skip("the project profile at the base revision cannot be read by this release")
        return None


def _patterns(profile: ProjectProfile, out: Collector) -> list[str]:
    value = profile.repository.branch_patterns.value
    if value is None or value.strip().lower() == "none":
        return []
    patterns = [part.strip() for part in value.split(",")]
    if any(pattern_problems(pattern) for pattern in patterns):
        out.skip(
            "a branch pattern of the profile at the base is not valid, so the branch is not checked"
        )
        return []
    return patterns


def _check_branch(
    services: ValidateServices,
    request: ConventionsRequest,
    profile: ProjectProfile,
    patterns: list[str],
    out: Collector,
) -> None:
    branch = request.branch
    if branch is None:
        branch = services.vcs.current_branch()
        if branch is None:
            out.skip("branch unknown: the head is detached, so pass --branch")
            return
        if branch == profile.repository.target_branch.value:
            out.info(
                "ORQ-I520",
                "The branch check was skipped: the current branch is the target branch of the "
                "profile. Pass --branch to check the name of a pull request branch.",
            )
            out.skip("the branch name was not checked: the current branch is the target branch")
            return
    problems = branch_problems(branch, patterns)
    if problems:
        out.error(
            "ORQ-E520",
            f"The branch name is not allowed by the branch patterns of the profile "
            f"({', '.join(problems)}): {printable(branch, _SHOWN)}",
        )


def _check_subjects(services: ValidateServices, base: str, head: str, out: Collector) -> int:
    commits = services.vcs.commit_subjects(base, head)
    if len(commits) > _MAX_COMMITS:
        out.skip("more than 200 commits are in the range, so the subjects were not all checked")
    for commit in commits[:_MAX_COMMITS]:
        problems = commit_subject_problems(commit.subject)
        if problems:
            out.error(
                "ORQ-E521",
                f"A commit subject does not have the Conventional Commits shape "
                f"({', '.join(problems)}): {printable(commit.subject, _SHOWN)}",
                commit.commit_id,
            )
    return min(len(commits), _MAX_COMMITS)
