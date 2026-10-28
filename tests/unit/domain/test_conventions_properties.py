"""Team conventions: property tests and the worst-case time (task team-conventions-resources, P-1).

Every test cites its `expected_behavior_source`. ADR-003 is the file `adr-003-*.md` under
docs/design/team-conventions-resources/design/, EC-12 to EC-16 are the expected changes of the
manifest.yaml next to it, AC-6 is an acceptance criterion of phase P-1 in
docs/design/team-conventions-resources/plan.yaml, and S-7 and S-8 are considerations of
considerations.md in the same folder.

These tests were written first, by the Tester of phase P-1, before `orqlet.domain.conventions`
existed. The builders are shared with test_conventions.py and test_resources_properties.py.

The properties are: `printable` output is ASCII only and never longer than the limit plus the mark
of a cut, the allow-lists accept what the design describes and refuse what it forbids, no problem
shows any part of the input, no function raises for arbitrary text, and the worst pattern that
`pattern_problems` accepts is matched against the longest allowed name in a generous absolute time.
The behaviour that the design leaves open is listed in test_conventions.py and is not pinned here.
"""

import string
from functools import partial

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from orqlet.domain.conventions import (
    branch_problems,
    commit_subject_problems,
    is_checkable_convention,
    pattern_problems,
    printable,
)
from tests.unit.domain.test_conventions import BOTH_LIMITS, cut_overhead, is_printable_ascii
from tests.unit.domain.test_resources import (
    assert_well_formed,
    holds_a_part,
    holds_any,
    shown,
)
from tests.unit.domain.test_resources_properties import (
    TIME_LIMIT_SECONDS,
    repeated,
    seconds_to_run,
)

pytestmark = pytest.mark.unit

# --- strategies -----------------------------------------------------------------------------------

_ALPHANUMERIC = string.ascii_letters + string.digits
# A distinctive part: the ZQ7 and 7QZ ends make a chance match with a rule name or a fixed word
# practically impossible.
_parts = st.text(alphabet=_ALPHANUMERIC, min_size=10, max_size=16).map(
    lambda text: "ZQ7" + text + "7QZ"
)
_any_text = st.text(max_size=200)
# Every code point, lone surrogates and the last plane included: str may hold all of them.
_codepoint_text = st.lists(st.integers(0, 0x10FFFF).map(chr), max_size=60).map("".join)
_PIECES = [
    "feat",
    "fix",
    "(",
    ")",
    "!",
    ":",
    ": ",
    " ",
    "Merge ",
    "Revert ",
    '"',
    "/",
    "**",
    "*",
    "?",
    ".",
    "-",
    "_",
    "\n",
    "\r",
    "\x1b",
    "\u202e",
    "conventional",
    "commits",
    "a" * 20,
]
_structured_text = st.lists(st.sampled_from(_PIECES), max_size=40).map("".join)
_texts = _any_text | _codepoint_text | _structured_text
_plain_characters = st.characters(min_codepoint=0x20, max_codepoint=0x7E, exclude_characters="\\")
_plain_text = st.text(alphabet=_plain_characters, max_size=100)
_long_plain_text = st.text(alphabet=_plain_characters, min_size=101, max_size=300)


# --- printable (AC-6; ADR-003 decision 4) ---------------------------------------------------------


@given(text=_texts, limit=st.integers(1, 300))
def test_printable_output_is_ascii_only_and_no_longer_than_the_limit_and_the_mark(
    text: str, limit: int
) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 ("only U+0020 to U+007E pass, and every
    other character ... is shown as an escape; text is cut at 100 characters"); plan P-1 (output
    is ASCII only and never longer than the limit plus the mark). The mark is learned from one
    plain overflow because its length is not fixed."""
    result = printable(text, limit)

    assert isinstance(result, str)
    assert is_printable_ascii(result)
    assert len(result) <= limit + cut_overhead(limit)
    assert printable(text, limit) == result


@given(text=_plain_text)
def test_printable_ascii_within_the_limit_passes_unchanged(text: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 ("only U+0020 to U+007E pass"). The
    backslash is left out: the design does not say whether an escape doubles it."""
    assert printable(text, 100) == text


@given(text=_long_plain_text, limit=st.integers(1, 100))
def test_printable_ascii_over_the_limit_keeps_its_first_characters(text: str, limit: int) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 ("text is cut at 100 characters"); AC-6
    ("cuts at the limit")."""
    result = printable(text, limit)

    assert result.startswith(text[:limit])
    assert len(result) <= limit + cut_overhead(limit)


# --- commit_subject_problems ----------------------------------------------------------------------

_types = st.from_regex(r"[a-z][a-z0-9]{0,5}(-[a-z0-9]{1,5})?", fullmatch=True)
_scopes = st.one_of(
    st.just(""),
    st.from_regex(r"[A-Za-z0-9._/-]{1,12}", fullmatch=True).map(lambda scope: f"({scope})"),
)
_descriptions = st.from_regex(r"[A-Za-z0-9][A-Za-z0-9 ,.()'/_:;!?#-]{0,40}", fullmatch=True)
_valid_subjects = st.builds(
    lambda kind, scope, bang, description: f"{kind}{scope}{bang}: {description}",
    _types,
    _scopes,
    st.sampled_from(["", "!"]),
    _descriptions,
)


@given(subject=_valid_subjects)
def test_a_generated_subject_of_the_shape_has_no_problem(subject: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (a type of lower case letters, digits and
    hyphens that starts with a letter; an optional scope of letters, digits and `._/-`; an optional
    `!`; a colon, one space and a description that does not start with a space)."""
    assert commit_subject_problems(subject) == ()


@given(
    subject=_valid_subjects,
    mutation=st.sampled_from(
        [
            "upper-case-type",
            "no-space",
            "two-spaces",
            "no-colon",
            "empty-description",
            "no-description-at-all",
        ]
    ),
)
def test_a_generated_subject_with_one_defect_is_a_problem(subject: str, mutation: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (the shape; plan P-1: a colon and a space
    and an empty description)."""
    head = subject[: subject.index(": ")]
    mutated = {
        "upper-case-type": subject[0].upper() + subject[1:],
        "no-space": subject.replace(": ", ":", 1),
        "two-spaces": subject.replace(": ", ":  ", 1),
        "no-colon": subject.replace(":", "", 1),
        "empty-description": head + ": ",
        "no-description-at-all": head + ":",
    }[mutation]

    assert commit_subject_problems(mutated)


@given(text=_plain_text)
def test_any_subject_that_starts_with_merge_and_a_space_is_exempt(text: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("exempts subjects that start with Merge"); ADR-003
    decision 4 ("a subject that starts with `Merge ` is exempt")."""
    assert commit_subject_problems("Merge " + text) == ()


@given(text=_texts)
def test_commit_subject_problems_never_raises_and_returns_rule_names(text: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (subjects are typed by a contributor, so
    no text may raise; a result is never a traceback); EC-14 (`-> tuple[str, ...]`);
    ORQLET-SEC-003 (texts shorter than 16 characters are left out of the check for a part of the
    input because a short text can equal a word that a fixed rule name contains)."""
    problems = commit_subject_problems(text)

    assert_well_formed(problems)
    assert commit_subject_problems(text) == problems
    assert len(text) < 16 or not holds_a_part(problems, text)


@given(part=_parts)
def test_commit_subject_problems_shows_no_part_of_a_refused_subject(part: str) -> None:
    """AC-6. expected_behavior_source: ORQLET-SEC-003; ADR-003 decision 4 (a contributor's text is
    never echoed by a rule name)."""
    for subject in (
        part + " no shape",
        "feat:" + part,
        "feat: " + " " + part,
        'Revert "' + part + '"',
    ):
        problems = commit_subject_problems(subject)

        assert problems
        assert not holds_any(shown(problems), part, part[:12])


# --- pattern_problems and branch_problems ---------------------------------------------------------

_pattern_segments = st.from_regex(r"[a-z0-9_-]{1,6}\*?", fullmatch=True)


@st.composite
def valid_patterns(draw: st.DrawFn) -> str:
    """A pattern within the caps: two to eight segments, at most one `**`, at most 60 characters."""
    segments = draw(st.lists(_pattern_segments, min_size=2, max_size=8))
    if draw(st.booleans()):
        segments[draw(st.integers(0, len(segments) - 1))] = "**"
    pattern = "/".join(segments)
    assume(len(pattern) <= 60)
    return pattern


@st.composite
def patterns_over_a_cap(draw: st.DrawFn) -> str:
    """A pattern that breaks one cap: two `**`, nine or more segments, or over 60 characters."""
    kind = draw(st.sampled_from(["two-double-stars", "many-segments", "too-long"]))
    if kind == "two-double-stars":
        segments = draw(st.lists(_pattern_segments, min_size=0, max_size=6))
        first = draw(st.integers(0, len(segments)))
        segments.insert(first, "**")
        segments.insert(draw(st.integers(0, len(segments))), "**")
        return "/".join(segments)
    if kind == "many-segments":
        return "/".join(
            draw(st.lists(st.from_regex(r"[a-z]{1,3}", fullmatch=True), min_size=9, max_size=12))
        )
    return draw(st.text(alphabet=string.ascii_lowercase, min_size=61, max_size=200))


@given(pattern=valid_patterns())
def test_a_generated_pattern_within_the_caps_has_no_problem(pattern: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (at most one `**`, at most 8 segments;
    at most 60 characters per item)."""
    assert pattern_problems(pattern) == ()


@given(pattern=patterns_over_a_cap())
def test_a_generated_pattern_over_a_cap_is_a_problem(pattern: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("pattern_problems refuses more"); ADR-003 decision 2;
    plan P-1 (more than one **, more than 8 segments, more than 60 characters)."""
    assert pattern_problems(pattern)


@given(text=_texts)
def test_pattern_problems_never_raises_and_returns_rule_names(text: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (a pattern comes from a committed file
    and may be anything); EC-12 (`-> tuple[str, ...]`); ORQLET-SEC-003."""
    problems = pattern_problems(text)

    assert_well_formed(problems)
    assert pattern_problems(text) == problems
    assert len(text) < 16 or not holds_a_part(problems, text)


@given(part=_parts)
def test_pattern_problems_shows_no_part_of_a_refused_pattern(part: str) -> None:
    """AC-6. expected_behavior_source: ORQLET-SEC-003."""
    for pattern in (part + "/**/x/**", "**/" + part + "/**", part * 10):
        problems = pattern_problems(pattern)

        assert problems
        assert not holds_any(shown(problems), part, part[:12])


_branch_segments = st.from_regex(r"[a-z0-9]{1,6}", fullmatch=True)


@given(segments=st.lists(_branch_segments, min_size=2, max_size=8), position=st.integers(0, 7))
def test_a_name_matches_a_pattern_made_of_it_with_one_segment_replaced_by_a_star(
    segments: list[str], position: int
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("branch_problems matches branch names"); ADR-003
    decision 2 (`*` stays inside a segment)."""
    index = position % len(segments)
    pattern = "/".join([*segments[:index], "*", *segments[index + 1 :]])

    assert branch_problems("/".join(segments), [pattern]) == ()


@given(segments=st.lists(_branch_segments, min_size=2, max_size=8), position=st.integers(0, 7))
def test_a_name_matches_a_prefix_followed_by_a_double_star(
    segments: list[str], position: int
) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (`**` spans segments)."""
    prefix = "/".join(segments[: 1 + position % (len(segments) - 1)])

    assert branch_problems("/".join(segments), [prefix + "/**"]) == ()


@given(segments=st.lists(_branch_segments, min_size=2, max_size=8), position=st.integers(0, 7))
def test_a_name_does_not_match_a_pattern_with_another_literal_or_an_extra_segment(
    segments: list[str], position: int
) -> None:
    """AC-6. expected_behavior_source: AC-6; ADR-003 decision 4 (a name that no pattern allows is
    a finding)."""
    index = position % len(segments)
    other_literal = "/".join([*segments[:index], segments[index] + "x", *segments[index + 1 :]])
    extra_segment = "/".join([*segments, "extra"])
    name = "/".join(segments)

    assert branch_problems(name, [other_literal])
    assert branch_problems(name, [extra_segment])
    assert branch_problems(name, [other_literal, extra_segment])


@given(length=st.integers(256, 2_000))
def test_a_name_over_255_characters_is_a_problem_whatever_the_pattern_says(length: int) -> None:
    """AC-6. expected_behavior_source: AC-6 ("a name over 255 characters ... is a finding before
    matching"); ADR-003 decision 2."""
    assert branch_problems("a" * length, ["a*"])


@given(count=st.integers(33, 300))
def test_a_name_over_32_segments_is_a_problem_whatever_the_pattern_says(count: int) -> None:
    """AC-6. expected_behavior_source: AC-6 ("a name over ... 32 segments is a finding before
    matching"); ADR-003 decision 2."""
    assert branch_problems("/".join(["a"] * count), ["a/**"])


@given(branch=_texts)
def test_branch_problems_never_raises_and_returns_rule_names(branch: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (a branch name is typed by a
    contributor; never a traceback); EC-13 (`-> tuple[str, ...]`); ORQLET-SEC-003."""
    problems = branch_problems(branch, ["feature/*", "**/release/*", "main"])

    assert_well_formed(problems)
    assert branch_problems(branch, ["feature/*", "**/release/*", "main"]) == problems
    assert len(branch) < 16 or not holds_a_part(problems, branch)


@given(part=_parts)
def test_branch_problems_shows_no_part_of_a_refused_name(part: str) -> None:
    """AC-6. expected_behavior_source: ORQLET-SEC-003; ADR-003 decision 4."""
    for branch in ("hotfix/" + part, part, part * 30):
        problems = branch_problems(branch, ["feature/*"])

        assert problems
        assert not holds_any(shown(problems), part, part[:12])


# --- is_checkable_convention ----------------------------------------------------------------------

_PHRASE = "conventional-commits"
_casings = st.lists(st.booleans(), min_size=len(_PHRASE), max_size=len(_PHRASE))


def _written(casing: list[bool], separator: str) -> str:
    letters = [char.upper() if upper else char for char, upper in zip(_PHRASE, casing, strict=True)]
    return "".join(letters).replace("-", separator)


@given(casing=_casings, separator=st.sampled_from(["-", " ", "_"]))
def test_the_phrase_in_any_case_with_any_of_the_three_separators_is_checkable(
    casing: list[bool], separator: str
) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (lower-cased with spaces and underscores
    read as hyphens, the answer equals `conventional-commits`); plan P-1 (spaces, case and
    underscores)."""
    assert is_checkable_convention(_written(casing, separator)) is True


@given(
    casing=_casings,
    separator=st.sampled_from(["-", " ", "_"]),
    position=st.integers(0, len(_PHRASE)),
    extra=st.characters(min_codepoint=0x20, max_codepoint=0x7E),
    operation=st.sampled_from(["insert", "delete"]),
)
def test_the_phrase_with_one_character_added_or_removed_is_not_checkable(
    casing: list[bool], separator: str, position: int, extra: str, operation: str
) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 ("equals `conventional-commits`": any
    other text is not the one value that the check understands). The inserted character is ASCII
    because the design says `lower-cased`, and a character such as U+017F lower-cases to itself."""
    written = _written(casing, separator)
    index = min(position, len(written) - 1)
    mutated = (
        written[:index] + extra + written[index:]
        if operation == "insert"
        else written[:index] + written[index + 1 :]
    )
    # The answer is trimmed before it is read (ADR-003 decision 2), so a space added at either end
    # leaves the phrase as it was. Found by Hypothesis in phase P-8; the P-1 test missed it.
    normalised = mutated.strip().lower().replace(" ", "-").replace("_", "-")
    assume(normalised != _PHRASE)

    assert is_checkable_convention(mutated) is False


@given(text=_texts)
def test_is_checkable_convention_never_raises_and_returns_a_bool(text: str) -> None:
    """AC-6. expected_behavior_source: EC-15 (`-> bool`); ADR-003 decision 2."""
    assert isinstance(is_checkable_convention(text), bool)


# --- AC-6: the worst case of the matcher ----------------------------------------------------------

HUGE = 1_000_000
SEGMENT_NAMES = {
    "255-characters-in-32-segments": BOTH_LIMITS,
    "255-characters-in-32-segments-ending-in-b": BOTH_LIMITS[:-1] + "b",
    "255-characters-in-one-segment": "a" * 255,
    "255-characters-in-one-segment-ending-in-b": "a" * 254 + "b",
}
# Patterns that pattern_problems accepts (the test asserts it) and that are the worst for the
# matcher of domain/globs.py: one `**` in front of or behind many `*`, and many `*` in one segment,
# each ending in a literal `c` that no name holds, so that matching never succeeds early.
WORST_ACCEPTED_PATTERNS = {
    "double-star-then-six-stars-and-a-literal": "**/*/*/*/*/*/*/c",
    "six-stars-then-a-double-star-and-a-literal": "*/*/*/*/*/*/**/c",
    "double-star-then-a-segment-of-many-stars": "**/a*a*a*a*a*a*a*c",
    "many-stars-in-one-segment": "*a" * 29 + "c",
    "stars-with-a-double-star-in-the-middle": "a*/**/*a*/*a*/*a*/*a*/*c",
}


@pytest.mark.parametrize("name", list(SEGMENT_NAMES.values()), ids=list(SEGMENT_NAMES))
@pytest.mark.parametrize(
    "pattern", list(WORST_ACCEPTED_PATTERNS.values()), ids=list(WORST_ACCEPTED_PATTERNS)
)
def test_branch_problems_finishes_in_the_limit_on_the_worst_accepted_pattern(
    pattern: str, name: str
) -> None:
    """AC-6. expected_behavior_source: plan P-1 (a timed test of branch_problems with the worst
    pattern that pattern_problems accepts against a 255-character, 32-segment name); ADR-003
    decision 2 and considerations S-7 (the matcher's cost stays quadratic at worst). The limit is
    set before a first measurement, in test_resources_properties.py."""
    assert pattern_problems(pattern) == (), "the pattern must be one that the caps accept"
    results: list[tuple[str, ...]] = []

    elapsed = seconds_to_run(lambda: results.append(branch_problems(name, [pattern] * 12)))

    assert elapsed < TIME_LIMIT_SECONDS
    assert results[0], "no name holds a `c`, so no pattern can match"


HOSTILE_NAMES = {
    "one-segment-of-a-million-characters": "a" * HUGE,
    "half-a-million-segments": "a/" * (HUGE // 2),
    "a-million-slashes": "/" * HUGE,
    "a-million-stars": "*" * HUGE,
}
HOSTILE_PATTERNS = {
    "many-double-stars": "**/" * (HUGE // 3),
    "many-segments": "a/" * (HUGE // 2),
    "a-million-stars": "*" * HUGE,
    "a-million-letters": "a" * HUGE,
    "double-stars-without-slashes": "**" * (HUGE // 2),
    "a-million-question-marks": "?" * HUGE,
}


@pytest.mark.parametrize("name", list(HOSTILE_NAMES.values()), ids=list(HOSTILE_NAMES))
def test_branch_problems_refuses_a_huge_name_in_the_limit(name: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 ("a longer branch name than 255
    characters or with more than 32 segments is a finding before matching"); considerations S-7."""
    results: list[tuple[str, ...]] = []

    elapsed = seconds_to_run(lambda: results.append(branch_problems(name, ["a/**", "*a*a*a*c"])))

    assert elapsed < TIME_LIMIT_SECONDS
    assert results[0]


@pytest.mark.parametrize("pattern", list(HOSTILE_PATTERNS.values()), ids=list(HOSTILE_PATTERNS))
def test_pattern_problems_refuses_a_huge_pattern_in_the_limit(pattern: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (the caps of pattern_problems bound a
    pattern that comes from a committed file); considerations S-7."""
    results: list[tuple[str, ...]] = []

    elapsed = seconds_to_run(lambda: results.append(pattern_problems(pattern)))

    assert elapsed < TIME_LIMIT_SECONDS
    assert results[0]


HOSTILE_SUBJECT_UNITS = {
    "letters": "a",
    "spaces": " ",
    "open-parentheses": "(",
    "colons": ":",
    "bangs": "!",
    "colon-and-space": ": ",
    "scope-characters": "a/",
    "hyphenated-words": "a-",
    "digits": "9",
}


@pytest.mark.parametrize(
    "unit", list(HOSTILE_SUBJECT_UNITS.values()), ids=list(HOSTILE_SUBJECT_UNITS)
)
def test_commit_subject_problems_finishes_in_the_limit_on_a_huge_subject(unit: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 ("The commit grammar is a fixed scan";
    considerations S-7); a subject is cut at 1 KiB after reading, but the function itself must
    not depend on that. Each unit is placed in every part of the shape."""
    run = repeated(unit, HUGE)
    subjects = [
        run,
        "feat: " + run,
        "feat(" + run,
        "feat(" + run + "): x",
        "feat" + run + ": x",
        "feat!" + run,
        "Merge " + run,
        run + ": x",
    ]

    for subject in subjects:
        assert seconds_to_run(partial(commit_subject_problems, subject)) < TIME_LIMIT_SECONDS


@pytest.mark.parametrize(
    "character",
    ["\x00", "a", "\u202e", "\U000e0041", "\n", "\ud800"],
    ids=["nul", "letter", "override", "tag-letter", "line-feed", "lone-surrogate"],
)
def test_printable_finishes_in_the_limit_on_a_huge_text(character: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 4 (every echo of a contributor's text goes
    through one function; the text is cut at 100 characters); considerations S-8."""
    text = character * HUGE
    results: list[str] = []

    elapsed = seconds_to_run(lambda: results.append(printable(text, 100)))

    assert elapsed < TIME_LIMIT_SECONDS
    assert is_printable_ascii(results[0])
    assert len(results[0]) <= 100 + cut_overhead(100)


@pytest.mark.parametrize(
    "unit",
    [" ", "_", "a", "-", "conventional "],
    ids=["spaces", "underscores", "letters", "hyphens", "words"],
)
def test_is_checkable_convention_finishes_in_the_limit_on_a_huge_text(unit: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 2 (the reading of an answer is a fixed
    comparison; an answer is at most 200 characters, but the function must not depend on that)."""
    text = repeated(unit, HUGE)
    results: list[bool] = []

    elapsed = seconds_to_run(lambda: results.append(is_checkable_convention(text)))

    assert elapsed < TIME_LIMIT_SECONDS
    assert results == [False]


def test_the_helpers_of_the_timed_tests_build_what_they_say() -> None:
    """AC-6. expected_behavior_source: plan P-1 (a 255-character, 32-segment name); this guards the
    names of this file against a wrong length."""
    assert len(BOTH_LIMITS) == 255
    assert len(BOTH_LIMITS.split("/")) == 32
    assert all(len(name) == 255 for name in SEGMENT_NAMES.values())
