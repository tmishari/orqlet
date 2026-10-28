"""Team conventions: the pure domain rules (task team-conventions-resources, phase P-1).

Every test cites its `expected_behavior_source`. ADR-003 is the file `adr-003-*.md` under
docs/design/team-conventions-resources/design/, EC-12 to EC-16 are the expected changes of the
manifest.yaml next to it, and AC-6 and AC-8 are acceptance criteria of phase P-1 in
docs/design/team-conventions-resources/plan.yaml. The tests cover AC-6 and AC-8 for
`orqlet.domain.conventions`; the timed and property tests are in test_conventions_properties.py.

These tests were written first, by the Tester of phase P-1, before `orqlet.domain.conventions`
existed. The module is pure and takes plain values, so no port is involved and no fake from
tests/fakes applies (ORQLET-TEST-001).

Behaviour that the design leaves open is deliberately not pinned here:
- the exact rule names that the problem functions return (only empty versus non-empty tuples,
  non-empty names and the absence of any part of the input are checked);
- what `printable` returns for a leading `::` (U+003A is inside U+0020 to U+007E, so it may pass;
  the fixed code prefix that the application writes keeps a log command from forming), for a
  backslash, and the form and the length of an escape and of the mark of a cut: the tests learn
  the overhead of a cut from one plain overflow;
- what `branch_problems` does with an empty list of patterns and what `pattern_problems` does
  with an empty pattern, a pattern of one star or a `**` inside a segment;
- what `commit_subject_problems` does with an empty scope `()`, a line feed in the subject and a
  subject longer than 1 KiB;
- whether `is_checkable_convention` trims the answer.
"""

import inspect

import pytest

from orqlet.domain import conventions
from orqlet.domain.conventions import (
    branch_problems,
    commit_subject_problems,
    is_checkable_convention,
    pattern_problems,
    printable,
)
from tests.unit.domain.test_resources import (
    assert_well_formed,
    clock_calls,
    clock_random_or_environment_imports,
    holds_a_part,
    holds_any,
    imports_outside_the_standard_library_and_the_domain,
    parametrized,
    public_assignments,
    shown,
)

pytestmark = pytest.mark.unit


# --- AC-6: pattern_problems ----------------------------------------------------------------------

VALID_PATTERNS = [
    "feature/*",
    "feature/**",
    "**/release",
    "main",
    "hotfix/*",
    "release/v?.?",
    "user/*/work",
    "a/b/c/d/e/f/g/h",  # 8 segments
    "**/a/b/c/d/e/f/g",  # 8 segments, one of them `**`
    "a" * 60,
    "feature/" + "a" * 52,  # 60 characters
]
BROKEN_PATTERNS = {
    "two-double-stars": "**/feature/**",
    "double-star-twice": "**/**",
    "double-stars-apart": "a/**/b/**/c",
    "three-double-stars": "**/**/**",
    "nine-segments": "a/b/c/d/e/f/g/h/i",
    "nine-single-stars": "*/*/*/*/*/*/*/*/*",
    "ten-segments-with-one-double-star": "**/a/b/c/d/e/f/g/h/i",
    "sixty-one-characters": "a" * 61,
    "sixty-one-characters-in-two-segments": "feature/" + "a" * 53,
}


@pytest.mark.parametrize("pattern", VALID_PATTERNS)
def test_a_pattern_within_the_caps_has_no_problem(pattern: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (a glob in the existing dialect with at
    most one `**`, at most 8 segments and, for a list item, at most 60 characters)."""
    assert pattern_problems(pattern) == ()


@parametrized("pattern", BROKEN_PATTERNS)
def test_a_pattern_over_a_cap_is_a_problem(pattern: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("pattern_problems refuses more [than one **]");
    ADR-003 decision 2 (at most 8 segments; at most 60 characters per item); plan P-1 (more than
    one **, more than 8 segments, more than 60 characters)."""
    assert pattern_problems(pattern)


def test_the_problems_of_a_pattern_hold_no_part_of_it() -> None:
    """AC-6. expected_behavior_source: ORQLET-SEC-003 (a fixed rule name holds no input value);
    ADR-003 decision 2 (pattern_problems)."""
    value = "zq7marker-pattern-5d1e/**/x/**"
    problems = pattern_problems(value)

    assert problems
    assert_well_formed(problems)
    assert not holds_any(shown(problems), "zq7marker-pattern-5d1e")


# --- AC-6: branch_problems ------------------------------------------------------------------------

MATCHING_BRANCHES = {
    "one-star-inside-a-segment": ("feature/login", ["feature/*"]),
    "second-pattern-matches": ("feature/login", ["bugfix/*", "feature/*"]),
    "release-with-dots": ("release/1.2.0", ["release/*"]),
    "plain-name": ("main", ["main"]),
    "double-star-spans-segments": ("feature/a/b", ["feature/**"]),
    "double-star-spans-no-segment": ("feature", ["feature/**"]),
    "double-star-first": ("user/x/feature/y", ["**/feature/*"]),
    "ticket-name": ("feature/ABC-123-add-login", ["feature/*"]),
    "question-mark": ("release/v1.2", ["release/v?.?"]),
}
UNMATCHED_BRANCHES = {
    "other-prefix": ("hotfix/login", ["feature/*"]),
    "one-star-stays-in-a-segment": ("feature/a/b", ["feature/*"]),
    "case-sensitive": ("Feature/login", ["feature/*"]),
    "missing-segment": ("feature", ["feature/*"]),
    "longer-name": ("mainline", ["main"]),
    "no-pattern-matches": ("main", ["feature/*", "release/*"]),
    "question-mark-is-one-character": ("release/v10.2", ["release/v?.?"]),
}
ONE_SEGMENT_OF_255 = "a" * 255
THIRTY_TWO_SEGMENTS = "/".join(["a"] * 32)
THIRTY_THREE_SEGMENTS = "/".join(["a"] * 33)
BOTH_LIMITS = "/".join(["a" * 7] * 32)  # 32 segments and exactly 255 characters


@parametrized("case", MATCHING_BRANCHES)
def test_a_name_that_one_pattern_matches_has_no_problem(case: tuple[str, list[str]]) -> None:
    """AC-6. expected_behavior_source: AC-6 ("branch_problems matches branch names"); ADR-003
    decision 2 (`*` stays inside a segment, `**` spans segments); the plan names the existing
    matcher of domain/globs.py, whose dialect and rows (tests/unit/domain/test_globs.py) these
    cases follow."""
    branch, patterns = case

    assert branch_problems(branch, patterns) == ()


@parametrized("case", UNMATCHED_BRANCHES)
def test_a_name_that_no_pattern_matches_is_a_problem(case: tuple[str, list[str]]) -> None:
    """AC-6. expected_behavior_source: AC-6; ADR-003 decision 4 (a branch name that no pattern
    allows is a failure of the check, ORQ-E520, so the function must report it); the matcher is
    case sensitive (domain/globs.py: `glob_match` "Case sensitive")."""
    branch, patterns = case

    assert branch_problems(branch, patterns)


@pytest.mark.parametrize(
    ("branch", "patterns"),
    [
        (ONE_SEGMENT_OF_255, ["a*"]),
        (THIRTY_TWO_SEGMENTS, ["a/**"]),
        (BOTH_LIMITS, ["**/a*"]),
    ],
    ids=["255-characters", "32-segments", "255-characters-and-32-segments"],
)
def test_a_name_at_the_limits_is_matched(branch: str, patterns: list[str]) -> None:
    """AC-6. expected_behavior_source: AC-6 ("a name over 255 characters or 32 segments is a
    finding"; so exactly 255 and 32 are not); ADR-003 decision 2."""
    assert len(branch) <= 255
    assert len(branch.split("/")) <= 32
    assert branch_problems(branch, patterns) == ()


@pytest.mark.parametrize(
    ("branch", "patterns"),
    [
        ("a" * 256, ["a*"]),
        ("a" * 1_000, ["a*"]),
        (THIRTY_THREE_SEGMENTS, ["a/**"]),
        ("/".join(["a"] * 200), ["a/**"]),
    ],
    ids=["256-characters", "1000-characters", "33-segments", "200-segments"],
)
def test_a_name_over_a_limit_is_a_problem_before_matching(branch: str, patterns: list[str]) -> None:
    """AC-6. expected_behavior_source: AC-6 ("a name over 255 characters or 32 segments is a
    finding before matching"); ADR-003 decision 2. The pattern would match each name, so only the
    limit can make it a problem."""
    assert branch_problems(branch, patterns)


def test_the_problems_of_a_branch_hold_no_part_of_the_name() -> None:
    """AC-6. expected_behavior_source: ORQLET-SEC-003 and ADR-003 decision 4 (a branch name is
    typed by a contributor; a fixed rule name holds no input value)."""
    name = "zq7marker-branch-5d1e/x"
    for problems in (branch_problems(name, ["feature/*"]), branch_problems(name * 20, ["x"])):
        assert problems
        assert_well_formed(problems)
        assert not holds_any(shown(problems), "zq7marker-branch-5d1e")
        assert not holds_a_part(problems, name)


# --- AC-6: commit_subject_problems ----------------------------------------------------------------

VALID_SUBJECTS = {
    "type-and-description": "feat: add login",
    "scope": "fix(api): handle a null body",
    "scope-and-bang": "feat(api)!: drop version one",
    "bang": "feat!: drop version one",
    "scope-with-a-hyphen": "chore(deps-dev): bump pytest",
    "scope-with-a-slash": "refactor(core/utils): split the module",
    "scope-with-a-dot-and-underscore": "fix(a.b_c): keep the order",
    "scope-with-capital-letters": "feat(API-v2): add the endpoint",
    "type-with-a-digit": "fix2: a type with a digit",
    "type-with-a-hyphen": "my-type: a type with a hyphen",
    "colon-inside-the-description": "docs: add the (optional) examples: part two",
    "one-character-description": "feat: x",
    "capital-letter-in-the-description": "feat: Add the Login Page",
    "merge-of-a-branch": "Merge branch 'main' into feature/x",
    "merge-of-a-pull-request": "Merge pull request #12 from team/feature/x",
    "merge-remote-tracking": "Merge remote-tracking branch 'origin/main'",
    "merge-with-any-text": "Merge nothing to see here",
    "merge-as-a-type": "merge: a lower case merge type",
}
BROKEN_SUBJECTS = {
    "empty": "",
    "spaces-only": "   ",
    "upper-case-type": "Feat: add login",
    "type-starts-with-a-digit": "1fix: add login",
    "type-starts-with-a-hyphen": "-fix: add login",
    "type-with-an-underscore": "my_type: add login",
    "type-with-a-space": "my type: add login",
    "leading-space": " feat: add login",
    "no-colon": "feat add login",
    "no-space-after-the-colon": "feat:add login",
    "two-spaces-after-the-colon": "feat:  add login",
    "colon-without-a-description": "feat:",
    "space-without-a-description": "feat: ",
    "space-before-the-colon": "feat : add login",
    "unclosed-scope": "feat(api: add login",
    "space-in-the-scope": "feat(a b): add login",
    "colon-in-the-scope": "feat(a:b): add login",
    "bang-in-the-scope": "feat(api!): add login",
    "bang-before-the-scope": "feat!(api): add login",
    "two-bangs": "feat!!: add login",
    "two-scopes": "feat(a)(b): add login",
    "text-between-the-scope-and-the-colon": "feat(a)x: add login",
    "git-revert-subject": 'Revert "feat: add login"',
    "git-revert-subject-without-a-type": 'Revert "Add login"',
    "lower-case-merge-without-a-colon": "merge branch main",
    "merged-is-not-merge": "Merged things",
    "merge-with-a-colon": "Merge: add login",
    "merge-alone": "Merge",
}


@parametrized("subject", VALID_SUBJECTS)
def test_a_subject_of_the_conventional_commits_shape_has_no_problem(subject: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("accepts type, optional scope of letters, digits and
    ._/-, optional !, a colon, one space and a description, and exempts subjects that start with
    Merge"); ADR-003 decision 4 (a type of lower case letters, digits and hyphens that starts
    with a letter; the exemption is for a subject that starts with `Merge `)."""
    assert commit_subject_problems(subject) == ()


@parametrized("subject", BROKEN_SUBJECTS)
def test_a_subject_outside_the_shape_is_a_problem(subject: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (the shape, an optional `!` after the
    scope, a colon, one space and a description that does not start with a space); the
    consequences of ADR-003 ("The Conventional Commits shape rejects Git's default `Revert "..."`
    subject"; no exemption beyond `Merge `); plan P-1 (an empty description)."""
    assert commit_subject_problems(subject)


@pytest.mark.parametrize("subject", ["Merge branch 'x'", "Merge !!!", "Merge : x"])
def test_a_subject_that_starts_with_merge_and_a_space_is_exempt_from_the_shape(
    subject: str,
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("exempts subjects that start with Merge"); ADR-003
    decision 4 ("a subject that starts with `Merge ` is exempt")."""
    assert commit_subject_problems(subject) == ()


def test_the_problems_of_a_subject_hold_no_part_of_it() -> None:
    """AC-6. expected_behavior_source: ORQLET-SEC-003 and ADR-003 decision 4 (subjects are typed by
    a contributor; a fixed rule name holds no input value)."""
    subject = "Zq7marker subject 5d1e without the shape"
    problems = commit_subject_problems(subject)

    assert problems
    assert_well_formed(problems)
    assert not holds_any(shown(problems), "zq7marker", "subject 5d1e")
    assert not holds_a_part(problems, subject)


# --- AC-6: is_checkable_convention ----------------------------------------------------------------


@pytest.mark.parametrize(
    "answer",
    [
        "conventional-commits",
        "Conventional Commits",
        "conventional commits",
        "conventional_commits",
        "CONVENTIONAL-COMMITS",
        "Conventional_Commits",
        "Conventional-Commits",
        "conventional_Commits",
    ],
)
def test_conventional_commits_is_checkable_with_spaces_case_and_underscores(answer: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (`is_checkable_convention` is true when
    the answer, lower-cased with spaces and underscores read as hyphens, equals
    `conventional-commits`); plan P-1 (spaces, case and underscores)."""
    assert is_checkable_convention(answer) is True


@pytest.mark.parametrize(
    "answer",
    [
        "",
        "none",
        "unknown",
        "angular",
        "free text",
        "conventional-commit",
        "conventionalcommits",
        "conventional commits 1.0",
        "conventional-commits-ish",
        "other: conventional commits",
        "conventional.commits",
        "conventional/commits",
    ],
)
def test_any_other_answer_is_not_checkable(answer: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (the answer must equal
    `conventional-commits` after the reading; `commit_convention` stays free text and
    `conventional-commits` is the one value that the check understands)."""
    assert is_checkable_convention(answer) is False


# --- AC-6: printable ------------------------------------------------------------------------------

LIMIT = 100  # ADR-003 decision 4: text is cut at 100 characters
PRINTABLE_ASCII_WITHOUT_BACKSLASH = "".join(
    chr(code_point) for code_point in range(0x20, 0x7F) if chr(code_point) != "\\"
)
NOT_PRINTABLE = {
    "escape-u001b": "\x1b",
    "carriage-return-u000d": "\r",
    "bell-u0007": "\x07",
    "nul-u0000": "\x00",
    "delete-u007f": "\x7f",
    "line-feed-u000a": "\n",
    "tab-u0009": "\t",
    "unit-separator-u001f": "\x1f",
    "next-line-u0085": "\u0085",
    "no-break-space-u00a0": "\u00a0",
    "accented-letter-u00e9": "\u00e9",
    "right-to-left-override-u202e": "\u202e",
    "zero-width-space-u200b": "\u200b",
    "line-separator-u2028": "\u2028",
    "variation-selector-ufe0f": "\ufe0f",
    "tag-letter-ue0041": "\U000e0041",
    "emoji-u1f600": "\U0001f600",
    "lone-surrogate-ud800": "\ud800",
}


def is_printable_ascii(text: str) -> bool:
    return all(0x20 <= ord(character) <= 0x7E for character in text)


def cut_overhead(limit: int) -> int:
    """How much longer than `limit` the output of one plain overflow is (the mark of the cut)."""
    return max(0, len(printable("a" * (limit + 1), limit)) - limit)


@pytest.mark.parametrize(
    "text",
    [
        "feature/TICKET-123 add login",
        "main",
        "",
        PRINTABLE_ASCII_WITHOUT_BACKSLASH,
        "fix(api)!: handle a null body, then retry",
    ],
    ids=["branch", "word", "empty", "every-printable-character", "subject"],
)
def test_printable_ascii_passes_unchanged(text: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 ("only U+0020 to U+007E pass"); AC-6.
    The backslash is left out: the design does not say whether an escape doubles it."""
    assert printable(text, LIMIT) == text


@parametrized("character", NOT_PRINTABLE)
def test_a_character_outside_u_0020_to_u_007e_is_shown_as_an_escape(character: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 ("every other character, DEL and the C0
    controls included, is shown as an escape"); AC-6 ("printable escapes everything outside U+0020
    to U+007E"); plan P-1 (ESC, CR, BEL, NUL, DEL, U+202E)."""
    result = printable("a" + character + "b", LIMIT)

    assert is_printable_ascii(result)
    assert character not in result
    assert result.startswith("a")
    assert result.endswith("b")
    assert len(result) > len("ab")


def test_an_ansi_sequence_loses_its_escape_character() -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (ESC is a C0 control and is shown as an
    escape; the printable rest of the sequence passes); considerations S-8."""
    result = printable("\x1b[31mred\x1b[0m", LIMIT)

    assert "\x1b" not in result
    assert is_printable_ascii(result)
    assert "red" in result


def test_a_line_break_cannot_start_a_second_line_of_output() -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (CR is shown as an escape; "no line
    starts with text from a contributor"); considerations S-8."""
    result = printable("one\r\ntwo\nthree", LIMIT)

    assert "\r" not in result
    assert "\n" not in result
    assert is_printable_ascii(result)


def test_a_leading_double_colon_leaves_only_printable_ascii() -> None:
    """AC-6. expected_behavior_source: plan P-1 (printable is tested with a leading double colon);
    ADR-003 decision 4 and considerations S-8 (a CI log command `::error::` cannot be formed). The
    design does not say whether `printable` itself changes the colons or whether the fixed code
    prefix of the caller is the control, so only the invariants of the output are checked."""
    result = printable("::error::boom", LIMIT)

    assert is_printable_ascii(result)
    assert "error" in result
    assert "boom" in result


@pytest.mark.parametrize("limit", [10, LIMIT])
def test_a_text_of_exactly_the_limit_is_not_cut(limit: int) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 ("text is cut at 100 characters"); AC-6
    ("cuts at the limit")."""
    assert printable("a" * limit, limit) == "a" * limit
    assert printable("a" * (limit - 1), limit) == "a" * (limit - 1)


@pytest.mark.parametrize("limit", [10, LIMIT])
def test_a_longer_text_is_cut_at_the_limit(limit: int) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 ("text is cut at 100 characters"); plan
    P-1 (the cut at 100 characters). The first `limit` characters stay; what the cut adds is the
    mark, whose length the design does not fix."""
    text = "a" * 10_000
    result = printable(text, limit)

    assert result.startswith("a" * limit)
    assert len(result) < len(text)
    assert len(result) <= limit + cut_overhead(limit)
    assert is_printable_ascii(result)


def test_every_echo_is_ascii_even_when_the_cut_falls_among_escapes() -> None:
    """AC-6. expected_behavior_source: AC-6 ("printable escapes everything outside U+0020 to
    U+007E and cuts at the limit"); plan P-1 for the property file (output is ASCII only and never
    longer than the limit plus the mark)."""
    text = "\x00" * 500 + "\u202e" * 500 + "a" * 500
    result = printable(text, LIMIT)

    assert is_printable_ascii(result)
    assert len(result) <= LIMIT + cut_overhead(LIMIT)


# --- AC-8: the module is pure ---------------------------------------------------------------------


def test_the_module_imports_only_the_standard_library_and_domain_modules() -> None:
    """AC-8. expected_behavior_source: AC-8 and ORQLET-ARCH-002 ("Both modules import only the
    standard library and domain modules"); plan P-1 (conventions.py uses glob_match from
    domain/globs.py)."""
    source = inspect.getsource(conventions)

    assert imports_outside_the_standard_library_and_the_domain(source) == set()


def test_the_module_uses_no_clock_random_number_or_environment() -> None:
    """AC-8. expected_behavior_source: AC-8 ("use no clock, random number or environment")."""
    source = inspect.getsource(conventions)

    assert clock_random_or_environment_imports(source) == set()
    assert clock_calls(source) == set()


def test_the_module_defines_no_public_name_that_is_not_a_function_or_a_class() -> None:
    """AC-8. expected_behavior_source: AC-8 and component rule 6 ("No new public assignment":
    constants stay private because the public-API extractor reads assignments)."""
    assert public_assignments(inspect.getsource(conventions)) == set()


# --- rework round 1: findings of the first review round (architecture F-5, F-8) ---


def test_printable_doubles_a_backslash_so_that_an_escape_is_never_mistaken_for_text() -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (every character outside U+0020 to
    U+007E is shown as an escape; a backslash is the escape character); architecture review F-5."""
    assert printable("a\\b", LIMIT) == "a\\\\b"
    assert printable("\u202e", LIMIT) == "\\u202e"


def test_printable_ends_a_cut_text_with_three_dots_and_keeps_the_first_limit_characters() -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (cut at the limit); architecture F-5."""
    assert printable("abcdefgh", 5) == "abcde..."
    assert printable("abcde", 5) == "abcde"


def test_branch_problems_gives_nothing_for_no_pattern_and_a_problem_for_a_broken_pattern() -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (nothing configured is `NOT_RUN` in the
    use case, so the pure function has nothing to refuse; a pattern that breaks a cap is never
    matched); architecture review F-8."""
    assert branch_problems("feature/x", []) == ()
    assert branch_problems("feature/x", ["**/**"])
    assert branch_problems("feature/x", ["feature/*", "**/**"])
