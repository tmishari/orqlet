"""The ownership file `.github/CODEOWNERS` (task dynamic-model-profiles, phase P-12, AC-1).

Every test cites its `expected_behavior_source`. AC-1 is the first acceptance criterion of phase
P-12 in docs/design/dynamic-model-profiles/plan.yaml. ADR-004 is the file `adr-004-*.md` under
docs/design/dynamic-model-profiles/design/ (decision 2, CODEOWNERS). Q-32 and Q-34 are entries of
docs/design/dynamic-model-profiles/questions.yaml: Q-32 is answered "No second owner. Only
@tmishari is a code owner" of the four paths, and Q-34 asks what the host enforces. "The interface
decision C1 to C3" is the reading that the plan author gave the Tester of phase P-12, because the
plan does not spell out what a malformed line is.

These tests were written first, by the Tester of phase P-12, before the four entries were added.
The parser is a small function of text. It is also run on small texts, including one with CRLF line
endings, so that a rule that cannot fail would fail here; those tests pass before the file changes.

Behaviour that no source fixes is deliberately NOT pinned here:
- whether an entry line may end in a `# comment` (the stored GitHub excerpt does not say; such a
  word is read as an owner and is refused);
- the exact characters that a user name, a team name or an email may hold (an owner has to look
  like `@name`, `@org/team` or an email address and nothing more);
- the blank lines and comments of the file.

The rule that a pattern may not start with `!` or hold `[` or `]` is the interface decision C1. The
stored GitHub excerpt (evidence/web/github-required-reviews-and-codeowners.md) does not state that
GitHub refuses them, so the rule rests on the plan author's decision.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

import pytest

pytestmark = pytest.mark.unit

CODEOWNERS = Path(__file__).resolve().parents[2] / ".github" / "CODEOWNERS"

OWNER = ("@tmishari",)
# The ten entries of the file at HEAD 1fc9851, in order (AC-1: "keeps every line that it has").
ORIGINAL_ENTRIES = [
    (pattern, OWNER)
    for pattern in (
        "/.prompts/",
        ".orqlet/**",
        "docs/resources/**",
        ".github/workflows/**",
        "AGENTS.md",
        ".claude/**",
        ".cursor/**",
        ".agents/**",
        ".codex/**",
        ".mcp.json",
    )
]
# AC-1: the four paths that gain the owner of Q-32 (ADR-004 decision 2), after the general entries.
NEW_PATTERNS = (
    "src/orqlet/workflow/seeds/**",
    ".github/CODEOWNERS",
    "src/orqlet/**",
    "tests/**",
)
OWNED_PATTERNS = (*NEW_PATTERNS, ".orqlet/**")

NAME = r"[A-Za-z0-9_][A-Za-z0-9_.-]*"
OWNER_FORM = re.compile(rf"@{NAME}(?:/{NAME})?|[^@\s]+@[^@\s]+\.[^@\s]+")


class Entry(NamedTuple):
    number: int  # the line of the file, counted from 1
    pattern: str
    owners: tuple[str, ...]


# --- reading the file ----------------------------------------------------------------------------


def entries_of(text: str) -> list[Entry]:
    """The lines that are not blank and not a comment, each split into a pattern and its owners."""
    entries: list[Entry] = []
    for number, line in enumerate(text.splitlines(), start=1):
        words = line.split()
        if words and not words[0].startswith("#"):
            entries.append(Entry(number, words[0], tuple(words[1:])))
    return entries


def problems_of(entries: Iterable[Entry]) -> list[str]:
    """One message for each way in which a line is malformed."""
    problems: list[str] = []
    for entry in entries:
        where = f"line {entry.number}"
        if entry.pattern.startswith("!") or "[" in entry.pattern or "]" in entry.pattern:
            problems.append(f"{where}: the pattern {entry.pattern!r} uses a syntax GitHub refuses")
        if not entry.owners:
            problems.append(f"{where}: the pattern {entry.pattern!r} has no owner")
        problems.extend(
            f"{where}: {owner!r} is not an owner"
            for owner in entry.owners
            if OWNER_FORM.fullmatch(owner) is None
        )
    return problems


def repeated_patterns(entries: Iterable[Entry]) -> list[str]:
    """The patterns that more than one line lists, compared character by character."""
    counts = Counter(entry.pattern for entry in entries)
    return sorted(pattern for pattern, count in counts.items() if count > 1)


def owners_of(entries: Iterable[Entry], pattern: str) -> list[tuple[str, ...]]:
    """The owners of each line that lists the pattern."""
    return [entry.owners for entry in entries if entry.pattern == pattern]


def positions_of(entries: list[Entry], pattern: str) -> list[int]:
    return [index for index, entry in enumerate(entries) if entry.pattern == pattern]


def real_entries() -> list[Entry]:
    return entries_of(CODEOWNERS.read_text(encoding="utf-8"))


# --- the parser is sound (C1) --------------------------------------------------------------------


def test_the_parser_skips_blank_lines_and_comments_and_keeps_the_line_numbers() -> None:
    """AC-1. expected_behavior_source: the interface decision C1 (blank lines and `#` comments are
    skipped; a line is `pattern owner [owner ...]`). It passes before the file changes."""
    text = "# a comment\n\n  # indented\nsrc/** @a @org/team\n\t\ndocs/ dev@example.com\n"

    assert entries_of(text) == [
        Entry(4, "src/**", ("@a", "@org/team")),
        Entry(6, "docs/", ("dev@example.com",)),
    ]
    assert problems_of(entries_of(text)) == []


def test_the_parser_reads_a_text_with_crlf_line_endings() -> None:
    """AC-1. expected_behavior_source: the interface decision C1 (the text is read with
    `splitlines()`, so CRLF works; the tests also run on Windows). It passes before the file
    changes."""
    text = "a/** @x\r\n# comment\r\n\r\nb/** @y @z\r\n"

    assert entries_of(text) == [Entry(1, "a/**", ("@x",)), Entry(4, "b/**", ("@y", "@z"))]
    assert problems_of(entries_of(text)) == []


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("* @a", id="everything"),
        pytest.param("/.prompts/ @tmishari", id="directory-from-the-root"),
        pytest.param("src/orqlet/** @tmishari", id="recursive"),
        pytest.param("*.js @org/js-team", id="team"),
        pytest.param("docs/** dev@example.com", id="email"),
        pytest.param("docs/** @a @b dev@example.com", id="three-owners"),
        pytest.param("a\t@a", id="tab-between-words"),
    ],
)
def test_a_well_formed_line_has_no_problem(line: str) -> None:
    """AC-1. expected_behavior_source: the interface decision C1 (an owner is `@name`, `@org/team`
    or an email address). It passes before the file changes."""
    assert problems_of(entries_of(line)) == []


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        pytest.param("docs/**", "has no owner", id="no-owner"),
        pytest.param("docs/** tmishari", "is not an owner", id="name-without-at"),
        pytest.param("docs/** @", "is not an owner", id="at-alone"),
        pytest.param("docs/** @@a", "is not an owner", id="two-ats"),
        pytest.param("docs/** @org/", "is not an owner", id="team-without-name"),
        pytest.param("docs/** a@b", "is not an owner", id="email-without-a-domain-dot"),
        pytest.param("docs/** @a, @b", "is not an owner", id="comma"),
        pytest.param("!docs/** @a", "syntax GitHub refuses", id="negated-pattern"),
        pytest.param("docs/[ab]/** @a", "syntax GitHub refuses", id="character-class"),
        pytest.param("docs/a] @a", "syntax GitHub refuses", id="closing-bracket-only"),
        pytest.param("docs/[a @a", "syntax GitHub refuses", id="opening-bracket-only"),
    ],
)
def test_each_kind_of_malformed_line_is_reported(line: str, reason: str) -> None:
    """AC-1. expected_behavior_source: the interface decision C1 (malformed: a pattern with no
    owner; an owner that is neither `@name`, `@org/team` nor an email; a pattern that starts with
    `!` or holds `[` or `]`). It passes before the file changes."""
    problems = problems_of(entries_of(f"# header\n{line}\n"))

    assert len(problems) == 1
    assert problems[0].startswith("line 2: ")
    assert reason in problems[0]


def test_a_pattern_listed_twice_is_found_and_a_similar_one_is_not() -> None:
    """AC-1. expected_behavior_source: the interface decision C2 (no pattern appears twice, compared
    literally: `src/**` and `src/**/` are two patterns). It passes before the file changes."""
    entries = entries_of("a/** @x\nb/** @x\na/** @y\nb/**/ @x\nA/** @x\n")

    assert repeated_patterns(entries) == ["a/**"]


def test_the_owners_and_the_position_of_a_pattern_are_read_from_every_line_that_lists_it() -> None:
    """AC-1. expected_behavior_source: the interface decision C2 and C3 (owners of a pattern;
    positions of an entry in the file). It passes before the file changes."""
    entries = entries_of("a/** @x\n\nb/** @y\na/** @z\n")

    assert owners_of(entries, "a/**") == [("@x",), ("@z",)]
    assert owners_of(entries, "c/**") == []
    assert positions_of(entries, "a/**") == [0, 2]
    assert positions_of(entries, "c/**") == []


# --- the real file (C2, C3) ----------------------------------------------------------------------


def test_the_file_has_no_malformed_line() -> None:
    """AC-1. expected_behavior_source: AC-1 ("no line is malformed") and the interface decision C1.
    It holds before the file changes."""
    assert problems_of(real_entries()) == []


def test_the_file_lists_no_pattern_twice() -> None:
    """AC-1. expected_behavior_source: AC-1 ("no pattern is listed twice") and the interface
    decision C2. It holds before the file changes."""
    assert repeated_patterns(real_entries()) == []


@pytest.mark.parametrize("pattern", OWNED_PATTERNS)
def test_the_pattern_has_an_owner_that_starts_with_at(pattern: str) -> None:
    """AC-1. expected_behavior_source: AC-1 (each of `src/orqlet/workflow/seeds/**`,
    `.github/CODEOWNERS`, `src/orqlet/**`, `tests/**` and `.orqlet/**` "has at least one owner that
    starts with `@`") and ADR-004 decision 2 (the paths that need an owner)."""
    owners = [owner for line in owners_of(real_entries(), pattern) for owner in line]

    assert any(owner.startswith("@") for owner in owners), f"{pattern} has no owner that is @name"


@pytest.mark.parametrize("pattern", NEW_PATTERNS)
def test_the_new_pattern_has_exactly_the_owner_that_q_32_names(pattern: str) -> None:
    """AC-1. expected_behavior_source: AC-1 (the owner `@tmishari` for the four paths), Q-32 (the
    answer: "No second owner. Only @tmishari is a code owner of these paths") and the interface
    decision C2 (exactly `['@tmishari']`)."""
    lines = owners_of(real_entries(), pattern)

    assert [list(owners) for owners in lines] == [["@tmishari"]]


def test_the_ten_entries_that_the_file_had_are_still_the_first_ten_in_the_same_order() -> None:
    """AC-1. expected_behavior_source: AC-1 ("keeps every line that it has") and the interface
    decision C3 (the ten entries of the file at HEAD 1fc9851, written here as literal values). It
    holds before the file changes."""
    assert [(entry.pattern, entry.owners) for entry in real_entries()[:10]] == ORIGINAL_ENTRIES


def test_the_four_new_entries_come_after_the_last_entry_that_the_file_had() -> None:
    """AC-1. expected_behavior_source: AC-1 ("adds, after the general entries") and the interface
    decision C3 (the later pattern wins in CODEOWNERS, so the order matters: each new entry sits
    below the last original one). Q-32 says the same of "the last matching pattern of the file"."""
    entries = real_entries()
    last_original = max(
        position for pattern, _ in ORIGINAL_ENTRIES for position in positions_of(entries, pattern)
    )

    for pattern in NEW_PATTERNS:
        positions = positions_of(entries, pattern)
        assert positions, f"{pattern} is not listed"
        assert min(positions) > last_original, f"{pattern} is listed above an original entry"
