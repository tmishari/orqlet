"""`find_policy_credentials`, the credential scan of the model policy (dynamic-model-profiles, P-2).

Every test cites its `expected_behavior_source`. AC-4 is the fourth acceptance criterion of phase
P-2 in docs/design/dynamic-model-profiles/plan.yaml, BC-32 is a behaviour row of
design/component.md, ADR-002 is design/adr-002-model-policy-v2-contract-and-home.md (decision 3:
"The credential scan is the integrations scan plus the key shapes of the vendors in the catalog
(`sk-`, `xai-`, `AIza`)") and ORQLET-SEC-003 is the standard that forbids a key-shaped literal in
code, tests and fixtures.

These tests were written first, by the Tester of phase P-2 on 2026-11-05, before
`orqlet.domain.model_policy_scan` existed. The plan fixes only the three shapes and the rule that
a finding is a rule name and a line. The rule names, the least length of each shape, the token
boundary, the window of 4096 characters and the order of the result come from the brief of this
phase's Tester, which is the design of the public function: `find_policy_credentials(text)` returns
the findings of `find_literal_credentials(text)` plus `sk-key-prefix`, `xai-key-prefix` (`sk-` and
`xai-` followed by 20 or more of `A-Za-z0-9_-`) and `aiza-key-prefix` (`AIza` followed by 35 or
more), with no duplicate, sorted by (line, rule). A shape is case-sensitive and is not preceded by
one of `A-Za-z0-9_`.

Every key-shaped text is assembled from fragments at run time and none is written as one literal,
not even in a comment (ORQLET-SEC-003). Where a test needs to know what `find_literal_credentials`
reports for the same text, it asks that function and compares: a test never relies on a rule of
the older scan staying silent by accident.

Behaviour that the plan and the brief leave open is deliberately not pinned here:
- a shape that is preceded by `-` or `.` (the brief says only that `A-Za-z0-9_` before it is no
  boundary, so such a shape is a hit, but no test asks for it);
- a shape that starts inside the first 4096 characters of a line and runs past the cap (whether
  the run is cut at the cap or counted whole);
- a model id of a real catalog that starts with `sk-` or `xai-` and then holds 20 or more key
  characters (the stated rule flags it; whether that is wanted is a question for the person);
- other vendor key shapes, and unkeyed free text (a stated limit of ADR-002 decision 3);
- the rule names of `find_literal_credentials` beyond the seven that its source defines.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

import pytest

from orqlet.domain.mcp_credentials import CredentialFinding, find_literal_credentials
from orqlet.domain.model_policy_scan import find_policy_credentials

pytestmark = pytest.mark.unit

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.model-policy.v2.yaml"
)
MAX_LINE = 4096  # the window of the new shapes; a longer line is `oversize` for the older scan
OVERSIZE = "oversize"
WORST_CASE_SECONDS_PER_LINE = 0.5  # generous: the older scan alone is held to 0.25 elsewhere

SK = "sk-key-prefix"
XAI = "xai-key-prefix"
AIZA = "aiza-key-prefix"
RULES = (SK, XAI, AIZA)
# The text that starts each shape, split so that no prefix stands as one literal, and the least
# number of key characters (`A-Za-z0-9_-`) that must follow it.
PREFIX = {SK: "s" + "k-", XAI: "xa" + "i-", AIZA: "AI" + "za"}
MINIMUM = {SK: 20, XAI: 20, AIZA: 35}

# --- run-time builders ----------------------------------------------------------------------------


def body(size: int, unit: str = "aB3") -> str:
    """A deterministic run of `size` characters, all of them key characters."""
    return (unit * (size // len(unit) + 1))[:size]


TOKEN = "".join(("gh", "p_", body(36)))
JWT = ".".join(("ey" + "J" + "hbGciOiJIUzI1NiJ9", "ey" + "J" + "zdWIiOiJ0ZXN0In0", body(45)))
PASSWORD = "".join(("hunter", "2Qx", "9Lp", "Vw4"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))


def shape(rule: str, size: int | None = None, unit: str = "aB3") -> str:
    """The prefix of `rule` and `size` key characters (the least that the rule needs by default)."""
    return PREFIX[rule] + body(MINIMUM[rule] if size is None else size, unit)


def repeated(unit: str, size: int = MAX_LINE) -> str:
    """`unit` repeated and cut to exactly `size` characters."""
    return (unit * (size // len(unit) + 1))[:size]


def document_with(line: str) -> str:
    """Three lines of a policy. The line under test is line 2."""
    return "\n".join(("schema: orqlet.model-policy/v2", line, "policy_version: 1"))


def pairs(findings: Sequence[CredentialFinding]) -> set[tuple[int, str]]:
    return {(finding.line, finding.rule) for finding in findings}


def added(text: str) -> set[tuple[int, str]]:
    """What the policy scan reports beyond `find_literal_credentials`, as (line, rule)."""
    return pairs(find_policy_credentials(text)) - pairs(find_literal_credentials(text))


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def seconds_to_scan(text: str) -> float:
    """The time that one scan takes. This is the only clock in the tests: the module has none."""
    started = time.perf_counter()
    findings = find_policy_credentials(text)
    elapsed = time.perf_counter() - started
    assert isinstance(findings, tuple)
    return elapsed


# Where a person could put a key by mistake in a policy file: a value, a quoted value, a list
# item, a comment, a sentence. None of these lines holds a credential rule of the older scan.
PLACEMENTS = {
    "bare": "{}",
    "after-a-key": "  note: {}",
    "in-double-quotes": '  note: "{}"',
    "in-single-quotes": "  note: '{}'",
    "in-a-comment": "# {}",
    "after-an-equals-sign": "  note={}",
    "in-a-flow-list": "  items: [one, {}, two]",
    "in-a-sentence": "  note: use {} for access",
}
# One text for each rule that find_literal_credentials defines, built at run time.
OLD_TEXTS = {
    "token-prefix": f"  value: {TOKEN}",
    "jwt-shape": f"  value: {JWT}",
    "url-user-information": f"  value: https://deploy:{PASSWORD}@docs.example.com/x",
    "url-query-credential": f"  value: https://docs.example.com/x?api_key={OPAQUE}",
    "authorization-literal": f"  value: Authorization: Bearer {OPAQUE}",
    "credential-key-literal": f"  api_key: {OPAQUE}",
    OVERSIZE: "x" * (MAX_LINE + 1),
}
# A character that is not one of `A-Za-z0-9_-` and so ends a run of key characters.
BREAKS = {
    "dot": ".",
    "space": " ",
    "plus": "+",
    "slash": "/",
    "equals-sign": "=",
    "colon": ":",
    "at-sign": "@",
    "tilde": "~",
    "latin-letter-with-an-accent": "\u00e9",
    "fullwidth-digit": "\uff10",
}
# One run character each, to show that every character of `A-Za-z0-9_-` counts.
KEY_CHARACTERS = {
    "lower-case": "a",
    "upper-case": "Z",
    "digit": "7",
    "underscore": "_",
    "hyphen": "-",
    "all-of-them": "aB_-3",
}
# Text that may come right before a shape without hiding it: not one of `A-Za-z0-9_`.
BOUNDARIES = {
    "start-of-line": "",
    "space": " ",
    "tab": "\t",
    "double-quote": '"',
    "single-quote": "'",
    "equals-sign": "=",
    "colon": ":",
    "open-parenthesis": "(",
    "comma": ",",
    "open-bracket": "[",
    "hash": "#",
}
# One of `A-Za-z0-9_` right before a shape makes it the tail of a longer word.
INSIDE_A_WORD = {
    "lower-case-letter": "a",
    "upper-case-letter": "Z",
    "digit": "7",
    "underscore": "_",
}
# The same letters in another case: every shape is case-sensitive.
WRONG_CASE = {
    "sk-upper": (SK, "SK-"),
    "sk-capital": (SK, "Sk-"),
    "sk-second-upper": (SK, "sK-"),
    "xai-upper": (XAI, "XAI-"),
    "xai-capital": (XAI, "Xai-"),
    "xai-second-upper": (XAI, "xAI-"),
    "xai-third-upper": (XAI, "xaI-"),
    "aiza-lower": (AIZA, "aiza"),
    "aiza-upper": (AIZA, "AIZA"),
    "aiza-capital": (AIZA, "Aiza"),
    "aiza-first-lower": (AIZA, "aIza"),
    "aiza-last-upper": (AIZA, "AIzA"),
}
# Characters that `str.splitlines` would treat as a line end and `split("\n")` does not.
NOT_LINE_BREAKS = {
    "carriage-return": "\r",
    "vertical-tab": "\x0b",
    "form-feed": "\x0c",
    "next-line": "\x85",
    "line-separator": "\u2028",
    "paragraph-separator": "\u2029",
}
WORST_CASE_LINES = {
    "run-of-letters": repeated("a"),
    "run-of-hyphens": repeated("-"),
    "run-of-underscores": repeated("_"),
    **{f"repeated-prefix-of-{rule}": repeated(PREFIX[rule]) for rule in RULES},
    **{
        f"repeated-prefix-and-a-run-one-short-of-{rule}": repeated(
            PREFIX[rule] + body(MINIMUM[rule] - 1) + "."
        )
        for rule in RULES
    },
    **{
        f"prefix-then-a-run-to-the-cap-of-{rule}": PREFIX[rule]
        + repeated("a", MAX_LINE - len(PREFIX[rule]))
        for rule in RULES
    },
    "oversize-run": repeated("a", 500_000),
    "oversize-prefix-then-a-run": PREFIX[SK] + repeated("a", 500_000),
}


# --- AC-4: the three shapes -----------------------------------------------------------------------


@pytest.mark.parametrize("placement", list(PLACEMENTS), ids=list(PLACEMENTS))
@pytest.mark.parametrize("rule", list(RULES))
def test_a_vendor_key_shape_is_found_at_its_line_with_its_rule(rule: str, placement: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3; ORQLET-SEC-003.

    `sk-`, `xai-` and `AIza` followed by key-length text are findings with the rule names of the
    brief, on the line where the shape stands: in a value, in quotes, in a list and in a comment.
    """
    text = document_with(PLACEMENTS[placement].format(shape(rule)))

    assert added(text) == {(2, rule)}


@pytest.mark.parametrize("rule", list(RULES))
def test_a_line_that_holds_only_a_shape_gives_exactly_that_one_finding(rule: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    A text that is only one shape gives one finding: line 1 and the rule, as a `CredentialFinding`.
    """
    assert find_policy_credentials(shape(rule)) == (CredentialFinding(1, rule),)


@pytest.mark.parametrize("placement", list(PLACEMENTS), ids=list(PLACEMENTS))
@pytest.mark.parametrize("rule", list(RULES))
def test_find_literal_credentials_itself_knows_none_of_the_three_shapes(
    rule: str, placement: str
) -> None:
    """expected_behavior_source: AC-4 (`find_literal_credentials` itself is unchanged).

    The older scan stays as it was, so the three shapes are the policy scan's own addition. This
    also guards the premise of the tests above: no rule of the older scan fires on these lines.
    """
    text = document_with(PLACEMENTS[placement].format(shape(rule)))

    assert find_literal_credentials(text) == ()


@pytest.mark.parametrize("extra", [0, 1, 5, 80, 300, 2000])
@pytest.mark.parametrize("rule", list(RULES))
def test_a_run_of_the_least_length_or_more_is_a_hit(rule: str, extra: int) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3 ("key-length text").

    `sk-` and `xai-` need 20 key characters, `AIza` needs 35; more is a hit as well.
    """
    text = document_with(f"  note: {shape(rule, MINIMUM[rule] + extra)}")

    assert added(text) == {(2, rule)}


@pytest.mark.parametrize("rule", list(RULES))
def test_a_run_one_character_short_of_the_least_length_is_no_hit(rule: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3 ("key-length text").

    19 characters after `sk-` or `xai-`, and 34 after `AIza`, are not a key.
    """
    text = document_with(f"  note: {shape(rule, MINIMUM[rule] - 1)}")

    assert added(text) == set()


@pytest.mark.parametrize("rule", list(RULES))
def test_a_line_of_exactly_4096_characters_that_is_one_shape_is_a_hit_without_oversize(
    rule: str,
) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    The cap is 4096 characters of a line: a shape that fills a line of exactly that length is
    inside it, and the line is not `oversize`.
    """
    line = shape(rule, MAX_LINE - len(PREFIX[rule]))
    assert len(line) == MAX_LINE

    findings = find_policy_credentials(document_with(line))

    assert (2, rule) in pairs(findings)
    assert OVERSIZE not in {finding.rule for finding in findings}


@pytest.mark.parametrize("unit", list(KEY_CHARACTERS.values()), ids=list(KEY_CHARACTERS))
@pytest.mark.parametrize("rule", list(RULES))
def test_every_character_of_the_alphabet_counts_towards_the_run(rule: str, unit: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3 (key-length text).

    The run is made of `A-Za-z0-9_-`: a run of only one kind of those characters is long enough.
    """
    text = document_with(f"  note: {shape(rule, unit=unit)}")

    assert added(text) == {(2, rule)}


@pytest.mark.parametrize("name", list(BREAKS), ids=list(BREAKS))
@pytest.mark.parametrize("rule", list(RULES))
def test_a_character_outside_the_alphabet_cuts_the_run(rule: str, name: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    Two runs that are each too short are not one run: a character that is not in `A-Za-z0-9_-`
    ends it, even when a long run of key characters follows.
    """
    least = MINIMUM[rule]
    cut = PREFIX[rule] + body(least - 1) + BREAKS[name] + body(least)

    assert added(document_with(f"  note: {cut}")) == set()


@pytest.mark.parametrize("name", list(BREAKS), ids=list(BREAKS))
@pytest.mark.parametrize("rule", list(RULES))
def test_a_run_of_the_least_length_that_is_followed_by_another_character_is_a_hit(
    rule: str, name: str
) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    A key that is followed by a dot, a space or a colon is still a key.
    """
    text = PREFIX[rule] + body(MINIMUM[rule]) + BREAKS[name] + "rest"

    assert added(document_with(f"  note: {text}")) == {(2, rule)}


# --- AC-4: the token boundary and the case --------------------------------------------------------


@pytest.mark.parametrize("name", list(BOUNDARIES), ids=list(BOUNDARIES))
@pytest.mark.parametrize("rule", list(RULES))
def test_a_shape_after_a_character_that_is_no_part_of_a_word_is_a_hit(rule: str, name: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    A shape starts at a token boundary: at the start of a line, or after a character that is
    not one of `A-Za-z0-9_` (a space, a quote, `=`, `:`, a bracket, a comma).
    """
    assert added(document_with(BOUNDARIES[name] + shape(rule))) == {(2, rule)}


@pytest.mark.parametrize("name", list(INSIDE_A_WORD), ids=list(INSIDE_A_WORD))
@pytest.mark.parametrize("rule", list(RULES))
def test_a_shape_that_is_the_tail_of_a_longer_word_is_no_hit(rule: str, name: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    A letter, a digit or an underscore right before the prefix makes it part of another word.
    """
    assert added(document_with(INSIDE_A_WORD[name] + shape(rule))) == set()


@pytest.mark.parametrize("word", ["risk-", "task-", "disk-", "mask-"])
def test_sk_at_the_end_of_an_ordinary_word_is_no_hit(word: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    `risk-...` and `task-...` hold the text `sk-` and are not keys, however long the rest is.
    """
    text = document_with(f"  note: {word}{body(30)}")

    assert added(text) == set()


def test_a_shape_after_a_word_that_is_no_hit_is_still_found() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    The boundary is judged for each shape on its own: a `task-` word does not hide a key that
    follows it on the same line.
    """
    text = document_with(f"  note: task-{body(30)} {shape(SK)}")

    assert added(text) == {(2, SK)}


@pytest.mark.parametrize("name", list(WRONG_CASE), ids=list(WRONG_CASE))
def test_a_shape_in_another_letter_case_is_no_hit(name: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    The three prefixes are written `sk-`, `xai-` and `AIza`; no other spelling is a shape.
    """
    rule, prefix = WRONG_CASE[name]
    text = document_with(f"  note: {prefix}{body(MINIMUM[rule])}")

    assert added(text) == set()


# --- AC-4: every rule of the older scan, and the shape of the result ------------------------------


@pytest.mark.parametrize("rule", list(OLD_TEXTS), ids=list(OLD_TEXTS))
def test_every_rule_of_the_integrations_scan_is_still_reported_with_its_line(rule: str) -> None:
    """expected_behavior_source: AC-4 ("reports every rule of `find_literal_credentials`");
    BC-32; ADR-002 decision 3.

    Text that holds one rule of `find_literal_credentials` and no new shape gives the same
    findings from the policy scan: same line, same rule name.
    """
    text = document_with(OLD_TEXTS[rule])
    older = find_literal_credentials(text)
    assert rule in {finding.rule for finding in older}, "the text must hold the rule it names"

    assert find_policy_credentials(text) == older


def test_the_policy_scan_reports_everything_of_the_older_scan_and_the_three_shapes_too() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    One text with a line for each older rule and then a line for each new shape: the result is a
    superset of the older result, and what it adds is exactly the three new findings.
    """
    shapes = [f"  note: {shape(rule)}" for rule in RULES]
    text = "\n".join([*OLD_TEXTS.values(), *shapes])
    older = find_literal_credentials(text)
    newer = find_policy_credentials(text)
    first_shape_line = len(OLD_TEXTS) + 1

    assert {rule for _, rule in pairs(older)} >= set(OLD_TEXTS)
    assert set(older) <= set(newer)
    assert pairs(newer) - pairs(older) == {
        (first_shape_line + index, rule) for index, rule in enumerate(RULES)
    }


def test_a_line_with_an_older_finding_and_a_new_one_reports_both_sorted_by_rule() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    The result is the union of both scans, with no duplicate and sorted by (line, rule).
    """
    text = document_with(f"  note: {TOKEN} {shape(SK)}")
    older = find_literal_credentials(text)

    assert find_policy_credentials(text) == tuple(
        sorted({*older, CredentialFinding(2, SK)}, key=lambda found: (found.line, found.rule))
    )


def test_findings_on_one_line_are_sorted_by_rule_name() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    The three shapes on one line give three findings, in the order of their rule names.
    """
    text = document_with("  note: " + " ".join(shape(rule) for rule in (XAI, SK, AIZA)))
    findings = find_policy_credentials(text)

    assert [(finding.line, finding.rule) for finding in findings] == [
        (2, AIZA),
        (2, SK),
        (2, XAI),
    ]


def test_findings_are_sorted_by_line_first() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    A shape on a later line comes after one on an earlier line, whatever the rule names are.
    """
    text = "\n".join((f"  note: {shape(XAI)}", "a: 1", f"  note: {shape(AIZA)}", shape(SK)))
    findings = find_policy_credentials(text)

    assert [(finding.line, finding.rule) for finding in findings] == [(1, XAI), (3, AIZA), (4, SK)]


def test_the_same_shape_twice_on_a_line_is_one_finding() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3 ("no duplicates").

    A finding is a rule and a line, so two keys of one rule on one line are reported once.
    """
    text = document_with(f"  note: {shape(SK)} and {shape(SK, 30)}")

    assert find_policy_credentials(text) == (CredentialFinding(2, SK),)


def test_the_same_rule_on_two_lines_is_two_findings() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    Each line that holds a key is a finding of its own.
    """
    text = "\n".join((shape(XAI), "a: 1", shape(XAI)))

    assert find_policy_credentials(text) == (CredentialFinding(1, XAI), CredentialFinding(3, XAI))


@pytest.mark.parametrize("rule", list(RULES))
def test_a_finding_holds_a_line_and_a_rule_and_never_the_text_that_matched(rule: str) -> None:
    """expected_behavior_source: AC-4 ("the rule name and the line number only"); BC-32;
    ORQLET-SEC-003.

    The result is a tuple of `CredentialFinding`: an integer line and a rule name, and nothing in
    it shows the key.
    """
    key = shape(rule)
    findings = find_policy_credentials(document_with(f"  note: {key}"))

    assert isinstance(findings, tuple)
    assert findings
    assert all(isinstance(finding, CredentialFinding) for finding in findings)
    assert all(isinstance(finding.line, int) for finding in findings)
    assert {finding.rule for finding in findings} == {rule}
    assert not leaks(repr(findings), key)


# --- AC-4: line numbers ---------------------------------------------------------------------------


@pytest.mark.parametrize("ending", ["\n", "\r\n"], ids=["lf", "crlf"])
@pytest.mark.parametrize("rule", list(RULES))
def test_lines_are_counted_from_one_and_a_carriage_return_before_the_line_feed_is_no_line(
    rule: str, ending: str
) -> None:
    """expected_behavior_source: AC-4 (the lines of `find_literal_credentials`); BC-32.

    A text is split on line feeds and counted from one, with or without a trailing line feed.
    """
    lines = ("one: 1", "", "three: 3", f"  note: {shape(rule)}", "five: 5")

    assert added(ending.join(lines)) == {(4, rule)}
    assert added(ending.join(lines) + ending) == {(4, rule)}


def test_a_shape_on_the_first_and_on_the_last_line_without_a_trailing_line_feed() -> None:
    """expected_behavior_source: AC-4 (the lines of `find_literal_credentials`); BC-32."""
    text = "\n".join((shape(SK), "middle: 1", shape(XAI)))

    assert pairs(find_policy_credentials(text)) == {(1, SK), (3, XAI)}


@pytest.mark.parametrize("name", list(NOT_LINE_BREAKS), ids=list(NOT_LINE_BREAKS))
def test_only_a_line_feed_ends_a_line(name: str) -> None:
    """expected_behavior_source: AC-4 (lines are counted as `find_literal_credentials` does:
    split on a line feed, nothing else); BC-32.

    A carriage return alone, a form feed or a Unicode line separator does not start a new line.
    """
    separator = NOT_LINE_BREAKS[name]
    text = f"one{separator}two{separator}  note: {shape(AIZA)}\nlast: 1"

    assert added(text) == {(1, AIZA)}


# --- AC-4: the window of 4096 characters ----------------------------------------------------------


def test_a_shape_in_the_first_4096_characters_of_a_long_line_is_found_with_oversize() -> None:
    """expected_behavior_source: AC-4 (the older scan's `oversize` finding stays); BC-32;
    ADR-002 decision 3.

    A line above 4096 characters is `oversize`, and a key that stands inside the first 4096
    characters of it is a finding as well.
    """
    key = shape(SK)
    line = key + " " + "x" * (MAX_LINE + 100)

    findings = find_policy_credentials(line)

    assert pairs(findings) == pairs(find_literal_credentials(line)) | {(1, SK)}
    assert (1, OVERSIZE) in pairs(findings)


def test_a_shape_that_ends_exactly_at_character_4096_of_a_long_line_is_found() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    The window is the first 4096 characters: a shape that ends at its last character is inside.
    """
    key = shape(XAI)
    line = " " * (MAX_LINE - len(key)) + key + " tail"
    assert len(line) > MAX_LINE

    assert (1, XAI) in pairs(find_policy_credentials(line))


@pytest.mark.parametrize("rule", list(RULES))
def test_a_shape_that_starts_after_the_first_4096_characters_adds_nothing(rule: str) -> None:
    """expected_behavior_source: AC-4 ("the new shapes look only at the first 4096 characters of
    a line"); BC-32.

    A line above the cap is already an `oversize` finding of the older scan; a shape beyond the
    window is not looked at.
    """
    line = "x" * MAX_LINE + " " + shape(rule)

    assert (1, OVERSIZE) in pairs(find_literal_credentials(line))
    assert find_policy_credentials(line) == find_literal_credentials(line)


def test_the_cap_is_per_line_and_many_short_lines_with_a_shape_each_are_all_found() -> None:
    """expected_behavior_source: AC-4; BC-32.

    The cap is on one line, not on the text: a long text of short lines is scanned to its end.
    """
    count = 300
    text = "\n".join(f"  note: {shape(SK)}" if n % 3 == 0 else "a: 1" for n in range(count))

    assert len(text) > MAX_LINE
    assert pairs(find_policy_credentials(text)) == {(n + 1, SK) for n in range(0, count, 3)}


# --- AC-4: nothing to report ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\n",
        "\n\n\n",
        "A model that ships for the task, at some risk, with no key in the text.",
        "names such as sk-learn, xai-grok-4 and AIzaTest are short and are no keys",
        "the sk- prefix, the xai- prefix and the AIza prefix, written out without a key",
    ],
    ids=["empty", "line-feed", "blank-lines", "prose", "short-names", "prefixes-alone"],
)
def test_text_without_a_credential_gives_an_empty_tuple(text: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    A text that holds no credential gives `()`, as a tuple.
    """
    assert find_policy_credentials(text) == ()


def test_the_valid_fixture_of_the_policy_holds_no_credential() -> None:
    """expected_behavior_source: AC-4; BC-32; ADR-002 decision 3.

    The valid v2 fixture, which the loader must accept, has no finding: every model id, path and
    free text of a real policy has to stay clear of the scan.
    """
    assert find_policy_credentials(FIXTURE.read_text(encoding="utf-8")) == ()


# --- AC-4: the cost of a line ---------------------------------------------------------------------


@pytest.mark.parametrize("line", list(WORST_CASE_LINES.values()), ids=list(WORST_CASE_LINES))
def test_a_worst_case_line_is_scanned_within_the_limit(line: str) -> None:
    """expected_behavior_source: AC-4; BC-32; ORQLET-SEC-002 (the file is untrusted input, so a
    crafted line must not make the scan slow); ADR-002 decision 3.

    A line of near 4096 characters of key characters, of repeated prefixes and of runs one short
    of a key, and a line far above the cap, each finish quickly.
    """
    assert seconds_to_scan(line) < WORST_CASE_SECONDS_PER_LINE


def test_a_text_of_many_worst_case_lines_costs_the_limit_per_line_at_most() -> None:
    """expected_behavior_source: AC-4; BC-32; ORQLET-SEC-002; ADR-002 decision 3.

    The cost is per line, so a text of many such lines costs the sum and not more.
    """
    lines = [line for line in WORST_CASE_LINES.values() if len(line) <= MAX_LINE]

    assert len(lines) > 10
    assert seconds_to_scan("\n".join(lines)) < WORST_CASE_SECONDS_PER_LINE * len(lines)
