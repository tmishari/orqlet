"""`check_conventions`: every verdict and every NOT_RUN reason of ADR-003 decision 4 (task
team-conventions-resources, phase P-7).

Every test cites its `expected_behavior_source`. ADR-003 is the file `adr-003-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, S-n are the considerations of considerations.md, and AC-1 to AC-6 are the acceptance
criteria of phase P-7 in docs/design/team-conventions-resources/plan.yaml. "The interface decision"
is the reading of the plan author that the Tester of phase P-7 was given, because the ADR does not
spell it out:

- `ConventionsRequest(branch=None, base=None, head="HEAD")` and `check_conventions(services,
  request) -> ValidationResult` in `orqlet.application.usecases.conventions_check`; read-only and
  offline;
- the head id is `vcs.head_commit()` when the head is `HEAD`, else `vcs.resolve(head)`; the base id
  is `vcs.resolve(request.base)` when given, else the target branch of the profile in the working
  tree, resolved as `<remote>/<value>` and then as `<value>`; a refused name, an unresolved base or
  head, or a missing working-tree profile without `--base` is NOT_RUN with a reason; no merge base
  is NOT_RUN with the reason "no merge base";
- the rules are the profile at the base revision (`vcs.read_at(base_id, ...)`), never the head's;
  patterns are `repository.branch_patterns`, comma separated and trimmed (unknown or `none`: not
  configured) and each is re-checked with `pattern_problems`; the subject convention is
  `repository.commit_convention` (unknown or `none`: not configured; checkable when
  `is_checkable_convention`; any other text is free text);
- the branch is `request.branch` (always checked) or `vcs.current_branch()` (None: "branch
  unknown"); a defaulted branch equal to the target branch is not checked: ORQ-I520 and NOT_RUN for
  that check; a branch problem is ORQ-E520, a subject problem is ORQ-E521; 201 subjects mean "more
  than 200 commits" and are NOT_RUN for the subject check, while a failure found in the first 200
  is still reported;
- the verdict is FAIL when any finding is an error, else NOT_RUN when a configured check did not
  run or nothing was configured, else PASS; a FAIL that was found wins and the reasons stay in the
  result; every Finding message starts with fixed text and shows contributor text only through
  `printable(text, 100)`; a `VcsError` is a NOT_RUN reason and its text is never shown.

These tests were written first, by the Tester of phase P-7, before the use case existed.

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message or reason (reasons are found by the words the interface decision
  quotes: "no merge base", "branch unknown", "more than 200 commits"), and the keys of `data`;
- whether a bad branch is still reported when there is no merge base, when the head cannot be
  resolved or when the range cannot be read (every NOT_RUN test here uses a good branch);
- whether the 201st subject is checked, and what an empty item of a pattern list ("a,,b") does;
- whether a branch check that is not configured also leaves the reason "branch unknown";
- what the use case does with an empty `--base` or `--head`;
- `::error::` is printable ASCII, so `printable` keeps it: what is pinned is that no message and no
  line starts with contributor text, and that ESC, U+202E and every character beyond ASCII are
  escaped (the contributor text in these tests carries marker characters beyond ASCII).
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Iterator
from typing import Any

import pytest
import yaml

from orqlet.application.ports.vcs import CommitSummary, RepoState, VcsError
from orqlet.application.usecases.conventions_check import ConventionsRequest, check_conventions
from orqlet.application.usecases.validation import ValidationResult
from orqlet.domain.findings import Finding, Severity, Verdict
from tests.fakes.vcs import FakeVcs
from tests.support.artifacts import World, dump
from tests.support.trees import FIXTURES

pytestmark = pytest.mark.unit

BASE = "1" * 40
HEAD = "2" * 40
OTHER = "3" * 40
SECOND_HEAD = "4" * 40
PROFILE = ".orqlet/project-profile.yaml"
VALID_PROFILE = FIXTURES / "contracts" / "valid" / "orqlet.project-profile.v1.yaml"
RAW_ERROR = "zzq the raw error text of git"
MARKERS = "\u00e9\u65e5\U0001f680"  # characters beyond ASCII that must never be shown as they are
HEX_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


# --- helpers --------------------------------------------------------------------------------------


def profile(
    *,
    patterns: str | None = "feature/*, fix/*",
    convention: str | None = "conventional-commits",
    target: str | None = "main",
    remote: str = "origin",
    schema: str | None = None,
) -> bytes:
    """The valid fixture profile with the three facts of the check answered (or left unknown)."""
    document: dict[str, Any] = yaml.safe_load(VALID_PROFILE.read_text(encoding="utf-8"))
    repository = document["repository"]
    repository["target_branch"] = (
        {"value": target, "remote": remote, "answered_by": "maintainer"}
        if target is not None
        else {"value": None, "remote": remote, "question": "Which is the target branch?"}
    )
    repository["branch_patterns"] = _fact(patterns, "Which branch patterns are allowed?")
    repository["commit_convention"] = _fact(convention, "Is there a commit convention?")
    if schema is not None:
        document["schema"] = schema
    return dump(document).encode()


def _fact(value: str | None, question: str) -> dict[str, Any]:
    if value is None:
        return {"value": None, "question": question}
    return {"value": value, "answered_by": "maintainer"}


GOOD = profile()


def _summaries(subjects: tuple[str, ...]) -> tuple[CommitSummary, ...]:
    return tuple(
        CommitSummary(f"{0xC0DE0000 + i:040x}", subject) for i, subject in enumerate(subjects)
    )


def failing(method: str) -> type[FakeVcs]:
    """A fake whose `method` raises a `VcsError` that carries text which must never be shown."""

    class Failing(FakeVcs):
        def _fail(self, name: str) -> None:
            if name == method:
                raise VcsError(RAW_ERROR)

        def resolve(self, ref: str) -> str | None:
            self._fail("resolve")
            return super().resolve(ref)

        def head_commit(self) -> str | None:
            self._fail("head_commit")
            return super().head_commit()

        def current_branch(self) -> str | None:
            self._fail("current_branch")
            return super().current_branch()

        def merge_bases(self, first: str, second: str) -> tuple[str, ...]:
            self._fail("merge_bases")
            return super().merge_bases(first, second)

        def read_at(self, revision: str, path: str) -> bytes | None:
            self._fail("read_at")
            return super().read_at(revision, path)

        def commit_subjects(self, base: str, head: str) -> tuple[CommitSummary, ...]:
            self._fail("commit_subjects")
            return super().commit_subjects(base, head)

    return Failing


def make_world(
    *,
    base_profile: bytes | None = GOOD,
    head_profile: bytes | None = GOOD,
    working_profile: bytes | None = GOOD,
    branch: str | None = "feature/login",
    subjects: tuple[str, ...] = ("feat: add login", "fix(auth): handle an empty password"),
    refs: dict[str, str] | None = None,
    merge_bases: dict[tuple[str, str], tuple[str, ...]] | None = None,
    ranges: dict[tuple[str, str], tuple[CommitSummary, ...]] | None = None,
    has_head: bool = True,
    other_profile: bytes | None = profile(patterns=None, convention=None),
    vcs_class: type[FakeVcs] = FakeVcs,
) -> World:
    """A repository where `origin/main` is BASE (unless `refs` says otherwise), HEAD is one range
    ahead of it and OTHER is a third commit; each commit holds its own copy of the profile."""

    def files(data: bytes | None) -> dict[str, bytes]:
        return {} if data is None else {PROFILE: data}

    vcs = vcs_class(
        RepoState.HAS_COMMITS,
        branch=branch,
        commits=(CommitSummary(HEAD, "feat: head"),) if has_head else (),
        revisions={
            BASE: files(base_profile),
            HEAD: files(head_profile),
            OTHER: files(other_profile),
            SECOND_HEAD: files(head_profile),
        },
        refs={"origin/main": BASE} if refs is None else refs,
        merge_bases={(BASE, HEAD): (BASE,), **(merge_bases or {})},
        ranges={(BASE, HEAD): _summaries(subjects), **(ranges or {})},
    )
    world = World(vcs=vcs)
    if working_profile is not None:
        world.put(PROFILE, working_profile)
    return world


def run(world: World, **request: Any) -> ValidationResult:
    return check_conventions(world.services(), ConventionsRequest(**request))


def codes(result: ValidationResult) -> list[str]:
    return [finding.code for finding in result.findings]


def of_code(result: ValidationResult, code: str) -> list[Finding]:
    return [finding for finding in result.findings if finding.code == code]


def reasons(result: ValidationResult) -> str:
    return "\n".join(result.not_run)


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(key)
            yield from _strings(item)
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            yield from _strings(item)
    elif value is not None:
        yield str(value)


def everything(result: ValidationResult) -> str:
    """Every text that the result holds, as it is, so that a raw character can be found in it."""
    parts = [result.verdict.value, *result.not_run, *_strings(result.data)]
    for finding in result.findings:
        parts += [finding.code, finding.message, finding.path or "", finding.severity.value]
    return "\n".join(parts)


def not_run_and_not_failed(result: ValidationResult) -> None:
    assert result.verdict is Verdict.NOT_RUN, result
    assert result.errors == ()
    assert result.not_run


# --- the request ----------------------------------------------------------------------------------


def test_the_request_is_a_frozen_value_with_the_defaults_of_a_local_run() -> None:
    """AC-1. expected_behavior_source: EC-41 (`class ConventionsRequest`) and the interface
    decision (`branch: str | None = None, base: str | None = None, head: str = 'HEAD'`, frozen)."""
    request = ConventionsRequest()

    assert (request.branch, request.base, request.head) == (None, None, "HEAD")
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.__setattr__("branch", "x")  # a plain assignment is a type error as well


# --- PASS, FAIL: the checks themselves ------------------------------------------------------------


def test_a_good_range_on_an_allowed_branch_passes() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("`PASS` only if every configured check
    ran and passed") and AC-1."""
    result = run(make_world())

    assert result.verdict is Verdict.PASS, result
    assert result.errors == ()
    assert result.not_run == ()
    assert "ORQ-I520" not in codes(result)


def test_a_branch_that_no_pattern_allows_fails_with_orq_e520() -> None:
    """AC-1. expected_behavior_source: AC-1 ("FAIL with ORQ-E520 for a branch name that no pattern
    allows") and ADR-003 decision 4 (the branch is checked against `branch_patterns`)."""
    result = run(make_world(), branch="wip-stuff")

    assert result.verdict is Verdict.FAIL
    (finding,) = of_code(result, "ORQ-E520")
    assert finding.severity is Severity.ERROR
    assert "ORQ-E521" not in codes(result)


def test_a_defaulted_branch_that_no_pattern_allows_fails_as_well() -> None:
    """AC-2. expected_behavior_source: the interface decision (the branch is `request.branch` or
    else `vcs.current_branch()`; only a defaulted branch that equals the target is skipped)."""
    result = run(make_world(branch="wip-stuff"))

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E520")) == 1


def test_a_branch_that_a_pattern_allows_passes_with_any_of_the_patterns() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 and the interface decision (patterns are
    comma separated and trimmed; a branch needs one of them)."""
    world = make_world(base_profile=profile(patterns="  feature/* ,fix/*  ,release/*"))

    for branch in ("feature/login", "fix/crash", "release/1.0"):
        assert run(world, branch=branch).verdict is Verdict.PASS, branch


def test_every_subject_with_the_wrong_shape_is_one_orq_e521() -> None:
    """AC-1. expected_behavior_source: AC-1 ("ORQ-E521 for each subject with the wrong shape") and
    ADR-003 decision 4."""
    result = run(make_world(subjects=("feat: fine", "wip", "Fix: capital", "docs: fine")))

    assert result.verdict is Verdict.FAIL
    found = of_code(result, "ORQ-E521")
    assert len(found) == 2
    assert all(finding.severity is Severity.ERROR for finding in found)
    assert "ORQ-E520" not in codes(result)


@pytest.mark.parametrize(
    "subject",
    [
        "Merge branch 'main' into feature/login",
        "Merge pull request #12 from team/feature",
        "feat: add login",
        "fix(auth/api)!: breaking change",
        "chore(deps.dev): bump a library",
    ],
)
def test_a_merge_subject_and_a_conventional_subject_pass(subject: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("a subject that starts with `Merge ` is
    exempt"; the Conventional Commits shape) and considerations S-14."""
    assert run(make_world(subjects=(subject,))).verdict is Verdict.PASS


@pytest.mark.parametrize(
    "subject",
    [
        'Revert "feat: add login"',
        "wip",
        "Feat: x",
        "feat:x",
        "feat:  x",
        "feat(): x",
        "",
        "merge x",
    ],
)
def test_a_subject_without_the_shape_fails_and_a_revert_is_not_exempt(subject: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 Consequences ("The Conventional Commits shape
    rejects Git's default `Revert "..."` subject ... No exemption list is invented beyond
    `Merge `"), decision 4 (the shape) and the interface decision (an empty message gives a
    subject that fails)."""
    result = run(make_world(subjects=(subject,)))

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E521")) == 1


@pytest.mark.parametrize(
    "spelling", ["Conventional Commits", "conventional_commits", " CONVENTIONAL-COMMITS "]
)
def test_the_convention_is_read_as_is_checkable_convention_reads_it(spelling: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 2 (`is_checkable_convention` is true when
    the answer, lower-cased with spaces and underscores read as hyphens, equals
    `conventional-commits`) and decision 4 (that convention is the one that is checked)."""
    result = run(make_world(base_profile=profile(convention=spelling), subjects=("wip",)))

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E521")) == 1


# --- NOT_RUN: nothing configured, a convention that is not checked --------------------------------


@pytest.mark.parametrize(
    ("patterns", "convention"),
    [(None, None), ("none", "none"), (None, "none"), ("none", None)],
    ids=["both-unknown", "both-none", "unknown-and-none", "none-and-unknown"],
)
def test_nothing_configured_is_not_run(patterns: str | None, convention: str | None) -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN with the reason for: nothing configured")
    and the interface decision (unknown or `none` means that check is not configured)."""
    world = make_world(
        base_profile=profile(patterns=patterns, convention=convention), subjects=("wip",)
    )

    result = run(world, branch="wip-stuff")

    not_run_and_not_failed(result)
    assert not {"ORQ-E520", "ORQ-E521"} & set(codes(result))


@pytest.mark.parametrize("convention", [None, "none"])
def test_a_branch_check_alone_passes_when_the_subjects_are_not_configured(
    convention: str | None,
) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("`PASS` only if every configured check
    ran and passed") and the interface decision (unknown or `none` is not configured): a check that
    is not configured does not stop a PASS, and its subjects are not examined."""
    world = make_world(base_profile=profile(convention=convention), subjects=("wip", "!!"))

    result = run(world, branch="feature/login")

    assert result.verdict is Verdict.PASS, result
    assert "ORQ-E521" not in codes(result)


@pytest.mark.parametrize("patterns", [None, "none"])
def test_a_subject_check_alone_passes_and_fails_by_its_subjects(patterns: str | None) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 and the interface decision (no pattern
    check is configured, so any branch name is left alone)."""
    world = make_world(base_profile=profile(patterns=patterns))
    bad = make_world(base_profile=profile(patterns=patterns), subjects=("wip",))

    assert run(world, branch="anything-goes").verdict is Verdict.PASS
    result = run(bad, branch="anything-goes")
    assert result.verdict is Verdict.FAIL
    assert "ORQ-E520" not in codes(result)
    assert len(of_code(result, "ORQ-E521")) == 1


def test_a_free_text_convention_is_not_run_and_its_subjects_are_not_judged() -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN ... a free-text convention") and the
    interface decision ("any other text is free text -> NOT_RUN reason for that check")."""
    world = make_world(
        base_profile=profile(convention="gitmoji, then the ticket number"), subjects=("wip",)
    )

    result = run(world)

    not_run_and_not_failed(result)
    assert "ORQ-E521" not in codes(result)


def test_a_free_text_convention_does_not_hide_a_branch_that_fails() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("a FAIL that was found is reported as
    FAIL") and the interface decision (a FAIL that was found wins over NOT_RUN reasons; both are in
    the result)."""
    world = make_world(base_profile=profile(convention="free text of the team"))

    result = run(world, branch="wip-stuff")

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E520" in codes(result)
    assert result.not_run


# --- the branch: explicit, defaulted, unknown -----------------------------------------------------


def test_a_defaulted_branch_equal_to_the_target_is_skipped_with_orq_i520_and_is_not_a_pass() -> (
    None
):
    """AC-2. expected_behavior_source: AC-2 ("a defaulted branch equal to the target branch is
    skipped with ORQ-I520 and the verdict for that check is NOT_RUN, not PASS"), considerations
    S-14 and ADR-003 decision 4."""
    result = run(make_world(branch="main"))

    assert result.verdict is Verdict.NOT_RUN
    (finding,) = of_code(result, "ORQ-I520")
    assert finding.severity is Severity.INFO
    assert "ORQ-E520" not in codes(result)  # `main` matches no pattern, and is not judged
    assert result.not_run


def test_an_explicit_branch_is_checked_even_when_it_is_the_target_branch() -> None:
    """AC-2. expected_behavior_source: AC-2 ("an explicit --branch is always checked"),
    considerations S-14 ("An explicit `--branch` is always checked") and ADR-003 decision 4."""
    result = run(make_world(), branch="main")

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E520")) == 1
    assert "ORQ-I520" not in codes(result)


def test_an_explicit_branch_that_is_the_target_passes_when_a_pattern_allows_it() -> None:
    """AC-2. expected_behavior_source: AC-2 (an explicit branch is always checked, so it is
    judged by the patterns like any other) and the interface decision."""
    world = make_world(base_profile=profile(patterns="main, feature/*"))

    result = run(world, branch="main")

    assert result.verdict is Verdict.PASS, result
    assert "ORQ-I520" not in codes(result)


def test_the_explicit_branch_replaces_the_current_one() -> None:
    """AC-2. expected_behavior_source: the interface decision ("Branch: `request.branch` when
    given ...; else `vcs.current_branch()`")."""
    result = run(make_world(branch="main"), branch="feature/login")

    assert result.verdict is Verdict.PASS, result
    assert "ORQ-I520" not in codes(result)


def test_the_target_branch_that_decides_the_skip_is_the_one_of_the_profile_at_the_base() -> None:
    """AC-2. expected_behavior_source: the interface decision ("a DEFAULTED branch that equals the
    profile's target branch (at base) is not checked"): with `--base` the profile of the working
    tree is not needed at all."""
    world = make_world(working_profile=None, branch="main")

    result = run(world, base="origin/main")

    assert result.verdict is Verdict.NOT_RUN
    assert len(of_code(result, "ORQ-I520")) == 1
    assert "ORQ-E520" not in codes(result)


def test_a_skipped_branch_does_not_hide_a_subject_that_fails() -> None:
    """AC-2. expected_behavior_source: ADR-003 decision 4 (a FAIL that was found is reported as
    FAIL) and AC-1 (the verdict combinations)."""
    result = run(make_world(branch="main", subjects=("wip",)))

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E521")) == 1
    assert len(of_code(result, "ORQ-I520")) == 1


def test_an_unknown_branch_is_not_run_and_the_subjects_are_still_read() -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN with the reason for: ... an unknown branch"),
    ADR-003 decision 4 ("the branch is unknown (detached head without `--branch`)") and the
    interface decision (reason 'branch unknown')."""
    result = run(make_world(branch=None))

    not_run_and_not_failed(result)
    assert "branch unknown" in reasons(result)


def test_an_unknown_branch_does_not_hide_a_subject_that_fails() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 / the interface decision ("A FAIL that
    was found wins over NOT_RUN reasons (both are in the result)")."""
    result = run(make_world(branch=None, subjects=("wip",)))

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E521")) == 1
    assert "branch unknown" in reasons(result)


# --- the rules come from the base -----------------------------------------------------------------


def test_the_rules_are_read_at_the_base_and_not_at_the_head() -> None:
    """AC-2. expected_behavior_source: AC-2 ("The rules come from the profile at the base revision,
    not from the head"), considerations S-14 and ADR-003 decision 4 (a pull request cannot relax
    the rule that judges it): the head allows everything, the base allows `feature/*` only."""
    world = make_world(
        base_profile=profile(patterns="feature/*", convention="conventional-commits"),
        head_profile=profile(patterns="**", convention="none"),
    )

    result = run(world, branch="wip-stuff")

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E520" in codes(result)


def test_the_head_profile_is_never_read() -> None:
    """AC-2. expected_behavior_source: ADR-003 decision 4 ("not from the pull request's own tree"):
    a head profile that cannot be read changes nothing."""
    world = make_world(head_profile=b"\xff\xfe {not: [yaml")

    assert run(world).verdict is Verdict.PASS


def test_a_rule_that_only_the_head_has_is_not_applied() -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-003 decision 4: the base configures nothing
    and the head configures everything, so nothing is configured and the check is NOT_RUN."""
    world = make_world(
        base_profile=profile(patterns=None, convention=None),
        head_profile=profile(),
        subjects=("wip",),
    )

    result = run(world, branch="wip-stuff")

    not_run_and_not_failed(result)
    assert not {"ORQ-E520", "ORQ-E521"} & set(codes(result))


def test_the_working_tree_profile_does_not_decide_the_rules() -> None:
    """AC-2. expected_behavior_source: the interface decision (the working-tree profile only names
    the target branch when `--base` is not given; "The RULES are read from the profile at the
    BASE revision")."""
    world = make_world(working_profile=profile(patterns="**", convention="none"))

    result = run(world, branch="wip-stuff")

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E520" in codes(result)


def _not_a_profile() -> list[tuple[str, bytes | None]]:
    return [
        ("missing", None),
        ("not-utf8", b"\xff\xfe\x00 not text"),
        ("not-yaml", b"schema: [orqlet\n  broken: {"),
        ("not-a-mapping", b"- a\n- b\n"),
        ("empty", b""),
        ("invalid", b"schema: orqlet.project-profile/v1\nproject: {}\n"),
        ("a-later-version", profile(schema="orqlet.project-profile/v9")),
    ]


@pytest.mark.parametrize(
    "data", [item[1] for item in _not_a_profile()], ids=[item[0] for item in _not_a_profile()]
)
def test_a_base_profile_that_is_missing_unreadable_or_invalid_is_not_run(
    data: bytes | None,
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN with the reason for: ... a missing or
    unreadable base profile") and ADR-003 decision 4 ("the profile at the base is missing,
    unreadable or of a version this release does not read")."""
    result = run(make_world(base_profile=data), branch="feature/login")

    not_run_and_not_failed(result)


# --- resolving the base and the head --------------------------------------------------------------


def test_with_no_base_the_target_branch_of_the_working_tree_profile_names_it() -> None:
    """AC-1. expected_behavior_source: the interface decision (base = the target branch of the
    profile in the working tree, resolved as `<remote>/<value>` first) and ADR-003 decision 4."""
    assert run(make_world()).verdict is Verdict.PASS


def test_the_plain_target_branch_name_is_tried_when_the_remote_one_is_unknown() -> None:
    """AC-1. expected_behavior_source: the interface decision ("resolve `<remote>/<value>` first,
    then `<value>`, as binding_inputs does")."""
    assert run(make_world(refs={"main": BASE})).verdict is Verdict.PASS


def test_the_remote_qualified_name_wins_over_the_plain_one() -> None:
    """AC-1. expected_behavior_source: the interface decision (`<remote>/<value>` first): the plain
    `main` names a commit with no rules, so using it would not be a PASS."""
    world = make_world(refs={"origin/main": BASE, "main": OTHER})

    assert run(world).verdict is Verdict.PASS


def test_the_remote_of_the_profile_is_the_one_that_is_tried() -> None:
    """AC-1. expected_behavior_source: the interface decision (`repository.target_branch.value`
    and `.remote`)."""
    upstream = profile(remote="upstream")

    found = make_world(working_profile=upstream, refs={"upstream/main": BASE})
    elsewhere = make_world(working_profile=upstream)  # only origin/main is known
    assert run(found).verdict is Verdict.PASS
    not_run_and_not_failed(run(elsewhere))


def test_an_explicit_base_wins_over_the_target_branch() -> None:
    """AC-1. expected_behavior_source: the interface decision (base = `vcs.resolve(request.base)`
    when given)."""
    world = make_world(
        working_profile=profile(target="trunk"),
        refs={"trunk": OTHER, "release/1.x": BASE},
    )

    assert run(world, base="release/1.x").verdict is Verdict.PASS


def test_an_explicit_base_needs_no_profile_in_the_working_tree() -> None:
    """AC-1. expected_behavior_source: the interface decision ("a missing profile in the working
    tree when no --base is given" is NOT_RUN: with `--base` it is not needed)."""
    assert run(make_world(working_profile=None), base="origin/main").verdict is Verdict.PASS


@pytest.mark.parametrize(
    "working",
    [None, b"\xff\xfe broken", b"schema: orqlet.project-profile/v1\n", profile(target=None)],
    ids=["missing", "unreadable", "invalid", "target-unknown"],
)
def test_with_no_base_a_working_tree_profile_that_names_no_target_is_not_run(
    working: bytes | None,
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a base that cannot be resolved") and the interface
    decision ("a missing profile in the working tree when no --base is given" is NOT_RUN)."""
    not_run_and_not_failed(run(make_world(working_profile=working)))


def test_a_base_that_resolves_to_nothing_is_not_run() -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN ... a base that cannot be resolved") and
    ADR-003 decision 4 (a shallow clone): an explicit name, and a target branch that no ref
    names."""
    not_run_and_not_failed(run(make_world(), base="not-fetched"))
    not_run_and_not_failed(run(make_world(working_profile=profile(target="gone"))))
    not_run_and_not_failed(run(make_world(refs={})))


@pytest.mark.parametrize(
    "name", ["release/1.0+x", "--upload-pack=x", "a..b", "HEAD~1", "main:file", "a^b", "x{y}", "-x"]
)
def test_a_base_name_that_git_could_read_otherwise_is_not_run_and_never_echoes_the_error(
    name: str,
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a base ... whose name check_ref_name refuses"),
    ADR-003 decision 4 (`release/1.0+x`) and the interface decision (a refused name is NOT_RUN
    with a reason; "never a traceback and never the raw error text")."""
    result = run(make_world(), base=name)

    not_run_and_not_failed(result)
    assert "accepted ref name" not in everything(result)  # the text of the VcsError


@pytest.mark.parametrize("name", ["release/1.0+x", "--upload-pack=x", "a..b", "HEAD~1"])
def test_a_head_name_that_git_could_read_otherwise_is_not_run_and_never_echoes_the_error(
    name: str,
) -> None:
    """AC-1. expected_behavior_source: the interface decision (`vcs.resolve` raising VcsError for a
    refused name, for the head as for the base, is NOT_RUN with a reason; "never the raw error
    text") and ADR-003 decision 4 (`Vcs.resolve` ... refuses a name that could be read as an option
    or a revision expression)."""
    result = run(make_world(), head=name)

    not_run_and_not_failed(result)
    assert "accepted ref name" not in everything(result)


def test_a_head_that_resolves_to_nothing_is_not_run() -> None:
    """AC-1. expected_behavior_source: the interface decision ("an unresolved head" is NOT_RUN)."""
    not_run_and_not_failed(run(make_world(), head="not-fetched"))


def test_an_unborn_head_is_not_run() -> None:
    """AC-1. expected_behavior_source: the interface decision (head id = `vcs.head_commit()` when
    the head is `HEAD`; none is an unresolved head)."""
    not_run_and_not_failed(run(make_world(has_head=False)))


def test_a_head_that_is_a_branch_name_is_resolved_and_its_range_is_read() -> None:
    """AC-1. expected_behavior_source: the interface decision (head id = `vcs.resolve(head)` when
    the head is not `HEAD`)."""
    world = make_world(
        refs={"origin/main": BASE, "feature/other": SECOND_HEAD},
        merge_bases={(BASE, SECOND_HEAD): (BASE,)},
        ranges={(BASE, SECOND_HEAD): _summaries(("wip",))},
    )

    assert run(world).verdict is Verdict.PASS  # the range of HEAD is good
    result = run(world, head="feature/other")
    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E521")) == 1
    assert run(world, head="HEAD").verdict is Verdict.PASS


def test_no_merge_base_is_not_run_with_its_reason() -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN ... no merge base"), ADR-003 decision 4 (a
    shallow clone) and the interface decision (reason 'no merge base')."""
    result = run(make_world(merge_bases={(BASE, HEAD): ()}))

    not_run_and_not_failed(result)
    assert "no merge base" in reasons(result)


# --- a Git failure is a reason and never a traceback ----------------------------------------------


@pytest.mark.parametrize(
    "method",
    ["resolve", "head_commit", "current_branch", "merge_bases", "read_at", "commit_subjects"],
)
def test_a_git_failure_is_not_run_and_its_text_is_never_shown(method: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN ... a Git failure or limit"), ADR-003
    decision 4 ("any Git call fails or exceeds the runner's output or time limits (`VcsError`)
    ... never a traceback") and the interface decision ("never the raw error text")."""
    world = make_world(vcs_class=failing(method))

    result = run(world)

    not_run_and_not_failed(result)
    assert RAW_ERROR not in everything(result)


# --- how many commits are read --------------------------------------------------------------------


def _good_subjects(count: int) -> tuple[str, ...]:
    return tuple(f"chore: change {number}" for number in range(count))


def test_200_commits_are_read_and_pass() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("more than 200 commits are in the
    range" is NOT_RUN, so exactly 200 are read) and the interface decision."""
    result = run(make_world(subjects=_good_subjects(200)))

    assert result.verdict is Verdict.PASS, result
    assert "more than 200 commits" not in reasons(result)


@pytest.mark.parametrize("count", [201, 250], ids=["201-returned", "more-than-the-port-returns"])
def test_more_than_200_commits_is_not_run_for_the_subjects(count: int) -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN ... more than 200 commits") and the interface
    decision (201 results -> reason 'more than 200 commits')."""
    result = run(make_world(subjects=_good_subjects(count)))

    not_run_and_not_failed(result)
    assert "more than 200 commits" in reasons(result)


@pytest.mark.parametrize("position", [0, 100, 199])
def test_a_failure_in_the_first_200_is_reported_when_the_range_is_longer(position: int) -> None:
    """AC-1. expected_behavior_source: the interface decision ("any failure found in the first 200
    is still reported") and ADR-003 decision 4 (a FAIL that was found is reported as FAIL)."""
    subjects = list(_good_subjects(201))
    subjects[position] = "wip"

    result = run(make_world(subjects=tuple(subjects)))

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E521")) == 1
    assert "more than 200 commits" in reasons(result)


# --- patterns that are read again -----------------------------------------------------------------

BAD_PATTERNS = [
    "a/**/b/**",
    "feature/$ref",
    "q" * 61,
    "/leading",
    "a/b/c/d/e/f/g/h/i",
    "..",
    "feature//x",
]


@pytest.mark.parametrize("pattern", BAD_PATTERNS)
def test_a_pattern_that_pattern_problems_refuses_makes_the_branch_check_not_run(
    pattern: str,
) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("The patterns read from the base profile
    are checked again with `pattern_problems` before use, and one that fails is a `NOT_RUN`
    reason") and the interface decision (the pattern text is never echoed). The other pattern would
    allow the branch, so a PASS would show the bad one was dropped."""
    world = make_world(base_profile=profile(patterns=f"feature/*, {pattern}"))

    result = run(world, branch="feature/login")

    not_run_and_not_failed(result)
    assert "ORQ-E520" not in codes(result)
    assert pattern not in everything(result)


def test_a_bad_pattern_does_not_stop_the_subject_check() -> None:
    """AC-1. expected_behavior_source: the interface decision ("one that fails makes that check
    NOT_RUN with a reason") and ADR-003 decision 4 (a FAIL that was found is reported as FAIL)."""
    world = make_world(base_profile=profile(patterns="feature/*, a/**/b/**"), subjects=("wip",))

    result = run(world, branch="feature/login")

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E521")) == 1
    assert result.not_run


# --- output ---------------------------------------------------------------------------------------


def test_a_hostile_branch_is_never_shown_raw_and_no_message_starts_with_it() -> None:
    """AC-3. expected_behavior_source: AC-3 ("Output lines start with a fixed code prefix, show
    branch ... text only through printable ... and no line starts with contributor text"),
    considerations S-8 and ADR-003 decision 4: an escape sequence, a right-to-left override, a
    line break that is followed by a CI log command, and characters beyond ASCII."""
    branch = f"ZZQ::error::\x1b[31m\u202e{MARKERS}\n::error::inj"

    result = run(make_world(), branch=branch)

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E520")) == 1
    _assert_no_raw_contributor_text(result, "ZZQ")


def test_a_hostile_subject_is_never_shown_raw_and_no_message_starts_with_it() -> None:
    """AC-3. expected_behavior_source: AC-3, considerations S-8 and ADR-003 decision 4: a subject
    with a shape that is wrong, one that has the right shape and an escape sequence, and one that
    holds characters beyond ASCII."""
    subjects = (
        f"ZZQ::error::\x1b[2J\u202e{MARKERS}",
        "feat: ZZQ\x1b[2J\u202e after the shape",
        f"feat: ZZQ {MARKERS}",
    )

    result = run(make_world(subjects=subjects))

    assert result.verdict is Verdict.FAIL
    assert len(of_code(result, "ORQ-E521")) >= 2  # the control character is a problem of the shape
    _assert_no_raw_contributor_text(result, "ZZQ")


def test_a_long_branch_and_a_long_subject_are_cut_at_100_characters() -> None:
    """AC-3. expected_behavior_source: AC-3 ("cut at 100 characters"), considerations S-8 and the
    interface decision ("the full text of a long subject never appears")."""
    result = run(make_world(subjects=("s" * 500,)), branch="b" * 300)

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E520" in codes(result)
    assert "ORQ-E521" in codes(result)
    text = everything(result)
    assert "s" * 101 not in text
    assert "b" * 101 not in text


def test_a_finding_for_a_subject_names_a_commit_id_or_nothing_as_its_path() -> None:
    """AC-3. expected_behavior_source: the interface decision ("`Finding.path` for a subject
    finding may hold the commit id (hex) or nothing")."""
    result = run(make_world(subjects=("wip", "feat: fine")))

    for finding in of_code(result, "ORQ-E521"):
        assert finding.path is None or HEX_ID.fullmatch(finding.path), finding.path


def _assert_no_raw_contributor_text(result: ValidationResult, marker: str) -> None:
    text = everything(result)
    for raw in ("\x1b", "\u202e", "\r", *MARKERS):
        assert raw not in text, repr(raw)
    for finding in result.findings:
        assert not finding.message.startswith((marker, "::")), finding.message
        assert "\n" not in finding.message
    for reason in result.not_run:
        assert not reason.startswith((marker, "::")), reason
        assert "\n" not in reason
    assert "\n::" not in text


# --- read-only ------------------------------------------------------------------------------------


def test_the_check_writes_nothing() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("is read-only and offline") and the
    interface decision."""
    world = make_world(subjects=("wip",))
    before = world.project.snapshot()

    run(world, branch="wip-stuff")

    assert world.project.snapshot() == before
