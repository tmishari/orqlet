"""The matching rule of model strings, `model_identity` (dynamic-model-profiles, phase P-3).

Every test cites its `expected_behavior_source`. AC-1 to AC-5 are acceptance criteria of
phase P-3 in docs/design/dynamic-model-profiles/plan.yaml; AC-6 is checked by import-linter
and the gate, and the import tests at the end serve AC-5 and the brief only. BC-9,
BC-10, BC-18, BC-19, BC-23, BC-34, R-7 and R-12 are rows of design/component.md. ADR-005
decision 1 (design/adr-005-fable-exclusion-by-model-identity.md) is the matching rule.
ADR-007 (design/adr-007-independence-model-identity-and-fresh-context.md) decision 1 lets
only entries that are not `proposed` give a family, and decision 3 says that an alias,
effort, speed, context size, an option list and a provider prefix are no difference.
ADR-003 (design/adr-003-rendering-model-settings-into-generated-files.md) decision 3 says
that a Cursor pin is written only as a plain ID.

"The brief, item n" is the n-th numbered rule of the brief of this phase's Tester. The brief
fixes the public API of the module and what the plan leaves to the design of the functions:
the order of the normalisation steps and the canonical separator `-` (item 1), the names of
an entry (2), no match for an ambiguous or empty string (3), `None` for an unknown identity
(4), the family (5), the raw and the normalised form of the exclusion test with `*` and `?`
as the only wildcards (6), the sorted index pairs of a conflict (7) and the ASCII class of a
plain Cursor ID (8).

These tests were written first, by the Tester of phase P-3 on 2026-11-08, before
`orqlet.domain.model_identity` existed. Full-width text is built at run time and other
non-ASCII text is written as escapes, so the source holds no confusable character. Generated
text stays within the ASCII `RecordedModel` alphabet that the brief names (a part of what
BC-32 allows), so NFKC cannot compose a character across an inserted token. The import check
holds the module to the standard library and the domain, as the brief's API states, rather
than to the shorter list of modules that the brief gives as an example.

Behaviour that the sources leave open is deliberately not pinned here:
- whether an entry's logical `id` alone is a name of the entry, and whether a shared `id`, an
  `id` equal to another entry's name, or a shared `resolves_to` is a conflict: every `id`
  below is one of its own entry's names or a text that no test looks up;
- which part of a mix of nested and unmatched brackets (`a[b[c]`) stays as text;
- what a tab or other whitespace inside a string becomes (item 1 names only the space);
- whether a family tag spelled with separators inside a bracket (`x[model=fa-ble]`) is
  excluded: item 6 removes separators from the normalised form and can be read either way
  for the raw form;
- text that NFKC does not fold into the token: a combining mark or a zero-width character
  inside `fable`, or a look-alike letter of another script;
- whether `b-e-s-t` or `best-1m` is the alias `best` (under item 6 neither is, and the
  seed-like rule has no family tag `best`);
- an empty, `*`-only or whitespace-padded id pattern, and an argument that is not a string;
- that `normalise` is idempotent: it is not, since one call removes one provider prefix.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import re
import string
import sys
import unicodedata
from collections.abc import Callable, Sequence
from importlib.util import resolve_name

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.domain import model_identity
from orqlet.domain.model_identity import (
    PROVIDER_PREFIXES,
    ApprovalState,
    CatalogEntry,
    CatalogRoute,
    ExclusionRule,
    cursor_plain_id,
    family_of,
    is_excluded,
    match_entry,
    name_conflicts,
    normalise,
    same_identity,
)

pytestmark = pytest.mark.unit

# --- builders ------------------------------------------------------------

FULLWIDTH = {chr(code): chr(code + 0xFEE0) for code in range(0x21, 0x7F)} | {" ": "\u3000"}


def fullwidth(text: str) -> str:
    """`text` with each printable ASCII character and the space in its full-width form."""
    return "".join(FULLWIDTH.get(character, character) for character in text)


def route(name: str | None, *also_known_as: str, resolves_to: str | None = None) -> CatalogRoute:
    """A route with this name, these `also_known_as` spellings and this `resolves_to`."""
    return CatalogRoute(name=name, resolves_to=resolves_to, also_known_as=also_known_as)


def model(
    id_: str,
    *routes: CatalogRoute,
    family: str = "example-family",
    approval: ApprovalState = "approved",
) -> CatalogEntry:
    """A catalog entry with these routes."""
    return CatalogEntry(id=id_, family=family, approval=approval, routes=routes)


# A Claude Code id route that lists a reported spelling, an alias route that resolves to it,
# and an entry of another family. Each `id` is one of its own entry's names, so whether an
# `id` alone is a name (not pinned) changes no result below.
OPUS = model(
    "claude-opus-5-5",
    route("claude-opus-5-5", "claude-opus-5-5-xhigh"),
    route("opus", resolves_to="claude-opus-5-5"),
    family="anthropic",
)
SOL = model("gpt-6-1-sol", route("gpt-6.1-sol"), family="openai")
CATALOG = (OPUS, SOL)


def identities(
    first: str,
    second: str,
    catalog: Sequence[CatalogEntry] = CATALOG,
) -> set[bool | None]:
    """`same_identity` with and without proposed entries: one value when both agree."""
    return {same_identity(first, second, catalog, skip_proposed=skip) for skip in (True, False)}


OPUS_SPELLINGS = {
    "exact-id": "claude-opus-5-5",
    "alias": "opus",
    "effort-option": "claude-opus-5-5[effort=high]",
    "speed-option": "opus[fast]",
    "context-option": "claude-opus-5-5[1m]",
    "several-options": "opus[effort=low,fast=true,context=1m]",
    "provider-prefix": "anthropic/claude-opus-5-5",
    "display-text": "Claude Opus 5.5",
    "upper-case-and-underscores": "CLAUDE_OPUS_5_5",
    "also-known-as": "claude-opus-5-5-xhigh",
    "full-width-display-text": fullwidth("Claude Opus 5.5"),
    "all-at-once": " Anthropic/Claude Opus 5.5-xhigh[effort=high] ",
}
SOL_SPELLINGS = {
    "exact-id": "gpt-6.1-sol",
    "provider-prefix": "openai/gpt-6.1-sol",
    "display-text": "GPT 6.1 Sol",
    "effort-option": "gpt-6.1-sol[effort=xhigh]",
}
UNMATCHED = {
    "another-model": "llama-4-maverick",
    "unlisted-suffix": "claude-opus-5-5-high",
    "unbracketed-effort": "opus high",
    "prefix-outside-the-table": "openrouter/claude-opus-5-5",
    "family-word-alone": "claude",
    "options-alone": "[effort=high]",
    "empty": "",
    "blank": "   ",
}
ALL_SPELLINGS = [*OPUS_SPELLINGS.values(), *SOL_SPELLINGS.values(), *UNMATCHED.values()]
UNLISTED_SUFFIXES = [
    "claude-opus-5-5-high",
    "claude-opus-5-5-fast",
    "claude-opus-5-5-1m",
    "opus-xhigh",
]
APPROVAL_STATES: list[ApprovalState] = ["proposed", "approved", "disabled", "retired"]
# A catalog with a proposed entry and two entries that claim one name, for the properties.
MIXED = (
    OPUS,
    SOL,
    model("gpt-6-1-terra", route("gpt-6.1-terra"), family="openai", approval="proposed"),
    model("entry-d", route("shared")),
    model("entry-e", route("Shared")),
)
KNOWN_TEXT = [*ALL_SPELLINGS, "gpt-6.1-terra", "shared"]

# The exclusion rule of the shipped seed as ADR-005 decision 1 describes it, and each of its
# three mechanisms alone.
SEED = ExclusionRule(
    aliases=("fable", "best"),
    id_patterns=("claude-fable-*",),
    family_tags=("fable",),
)
ALIASES_ONLY = ExclusionRule(aliases=("fable",))
PATTERNS_ONLY = ExclusionRule(id_patterns=("claude-fable-*",))
TAGS_ONLY = ExclusionRule(family_tags=("fable",))

TABLE = ("anthropic/", "openai/", "google/", "xai/")

# The `RecordedModel` alphabet that the brief names: ASCII, so NFKC changes nothing.
RECORDED = string.ascii_letters + string.digits + " ._:/@+-[]=,"
UNBRACKETED = RECORDED.replace("[", "").replace("]", "")
recorded_text = st.text(alphabet=RECORDED, max_size=30)
unbracketed_text = st.text(alphabet=UNBRACKETED, max_size=30)
plain_text = st.text(alphabet=string.ascii_letters + string.digits + "-_.", max_size=30)
separator_gaps = st.lists(st.text(alphabet="-_. ", max_size=2), min_size=4, max_size=4)
model_text = st.one_of(st.sampled_from(KNOWN_TEXT), recorded_text)
FABLE_IN_CASES = ["fable", "FABLE", "Fable", "fAbLe"]


def spread(gaps: list[str]) -> str:
    """`fable` with one gap of separators after each of its first four letters."""
    return "".join(letter + gap for letter, gap in zip("fabl", gaps, strict=True)) + "e"


# --- the import check -----------------------------------------------------

DOMAIN = "orqlet.domain"
CLOCK_LOCALE_ENVIRONMENT = {"datetime", "locale", "os", "time"}
FORBIDDEN_NAMES = {"__import__", "eval", "exec", "open"}


def imported_modules(source: str) -> set[str]:
    """The absolute names of the modules that a source in `orqlet.domain` imports, anywhere."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(resolve_name("." * node.level + (node.module or ""), DOMAIN))
    return modules


def in_the_domain(module: str) -> bool:
    return module == DOMAIN or module.startswith(DOMAIN + ".")


def outside_the_brief(modules: set[str]) -> set[str]:
    """The modules that are neither in the standard library nor in the domain."""
    return {
        module
        for module in modules
        if module.split(".")[0] not in sys.stdlib_module_names and not in_the_domain(module)
    }


def used_names(source: str) -> set[str]:
    return {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}


# --- AC-1: normalise -------------------------------------------------------

FOLDED = {
    "full-width": (fullwidth("Claude Opus 5.5"), "claude-opus-5-5"),
    "full-width-prefix-and-options": (fullwidth("xai/grok-5[effort=high]"), "grok-5"),
    "no-break-space": ("claude\u00a0opus", "claude-opus"),
    "ligature": ("\ufb01ne-tuned", "fine-tuned"),
    "superscript-digit": ("model\u00b2", "model2"),
    "kelvin-sign": ("\u212aimi", "kimi"),
}
BRACKETED = {
    "at-the-end": ("claude-opus[effort=high]", "claude-opus"),
    "after-a-space": ("claude-opus [effort=high]", "claude-opus"),
    "at-the-start": ("[effort=high]claude-opus", "claude-opus"),
    "two-lists": ("claude[1m]-opus[fast]", "claude-opus"),
    "nested": ("claude-opus[a[b]c]", "claude-opus"),
    "nested-then-another": ("claude-opus[a[b]c][d]", "claude-opus"),
    "between-separators": ("claude-[x]-opus", "claude-opus"),
    "the-model-inside-a-list": ("x[model=fable]", "x"),
}
UNCLOSED = {
    "open-only": ("claude-opus[effort", "claude-opus[effort"),
    "close-only": ("claude-opus]", "claude-opus]"),
    "close-before-a-list": ("claude]opus[1m]", "claude]opus"),
}
RUNS = {
    "hyphens": ("a--b", "a-b"),
    "underscores": ("a__b", "a-b"),
    "dots": ("a..b", "a-b"),
    "spaces": ("a  b", "a-b"),
    "mixed": ("a -_. b", "a-b"),
    "one-of-each": ("a_b.c d-e", "a-b-c-d-e"),
}
ENDS = {
    "hyphens": ("-opus-", "opus"),
    "underscore-and-dot": ("_opus.", "opus"),
    "runs": (". opus _", "opus"),
    "after-a-provider-prefix": ("anthropic/-opus", "opus"),
    "before-an-option-list": ("opus-[1m]", "opus"),
}
OUTSIDE_THE_TABLE = [
    "meta/llama-4",
    "openrouter/claude-opus",
    "mistral/large-3",
    "anthropic",
    "anthropic-claude",
    "x-anthropic/claude",
    "anthropic:claude",
]
NO_NAME = [
    "",
    "   ",
    "[effort=high]",
    "---",
    "_. -",
    "anthropic/",
    " anthropic/[1m] ",
]


def test_the_provider_prefixes_are_a_closed_table_of_four() -> None:
    """expected_behavior_source: AC-1 ("a data table of the domain module"); ADR-005
    decision 1 (a closed list); the brief (`PROVIDER_PREFIXES`).
    """
    assert PROVIDER_PREFIXES == TABLE


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (" Fable-5.1 ", "fable-5-1"),
        ("Claude Fable 5.1", "claude-fable-5-1"),
        ("claude_fable_5_1", "claude-fable-5-1"),
        ("anthropic/claude-fable-5-1", "claude-fable-5-1"),
        ("claude-fable-5-1[effort=high]", "claude-fable-5-1"),
        ("fable-5.1-xhigh", "fable-5-1-xhigh"),
    ],
)
def test_the_examples_of_the_brief(text: str, expected: str) -> None:
    """expected_behavior_source: AC-1; BC-18; ADR-005 decision 1; the brief, item 1.

    Case, trimming, the three separators and the space, a provider prefix and an option list
    fold away; the suffix `-xhigh` stays.
    """
    assert normalise(text) == expected


@pytest.mark.parametrize(("text", "expected"), list(FOLDED.values()), ids=list(FOLDED))
def test_nfkc_forms_are_folded_first(text: str, expected: str) -> None:
    """expected_behavior_source: AC-1 ("applies NFKC"); BC-18; the brief, item 1.

    NFKC comes before every other step, so a full-width prefix, bracket or separator, a
    no-break space, a ligature, a superscript digit and the Kelvin sign fold too.
    """
    assert normalise(text) == expected


@pytest.mark.parametrize("text", ["STRASSE", "Stra\u00dfe", "stra\u00dfe"])
def test_normalise_case_folds_and_does_not_only_lower_case(text: str) -> None:
    """expected_behavior_source: AC-1 ("case folding"); the brief, item 1 (`str.casefold`)."""
    assert normalise(text) == "strasse"


@pytest.mark.parametrize(("text", "expected"), list(BRACKETED.values()), ids=list(BRACKETED))
def test_every_bracketed_option_list_is_removed(text: str, expected: str) -> None:
    """expected_behavior_source: AC-1 ("removes any bracketed option list"); BC-18; ADR-005
    decision 1; the brief, item 1 (nested lists too).
    """
    assert normalise(text) == expected


@pytest.mark.parametrize(("text", "expected"), list(UNCLOSED.values()), ids=list(UNCLOSED))
def test_an_unmatched_bracket_stays_as_text(text: str, expected: str) -> None:
    """expected_behavior_source: the brief, item 1 ("an unmatched bracket stays as text")."""
    assert normalise(text) == expected


@pytest.mark.parametrize("text", ["  opus  ", "\topus\n", "\u3000opus\u3000", "\r\nopus "])
def test_surrounding_whitespace_is_trimmed(text: str) -> None:
    """expected_behavior_source: AC-1 ("trimming"); the brief, item 1."""
    assert normalise(text) == "opus"


@pytest.mark.parametrize(("text", "expected"), list(RUNS.values()), ids=list(RUNS))
def test_a_run_of_separators_becomes_one_hyphen(text: str, expected: str) -> None:
    """expected_behavior_source: AC-1 ("treats `-`, `_`, `.` and the space as one separator");
    ADR-005 decision 1; the brief, item 1 (the canonical separator is `-`).
    """
    assert normalise(text) == expected


@pytest.mark.parametrize(("text", "expected"), list(ENDS.values()), ids=list(ENDS))
def test_a_separator_at_either_end_is_dropped(text: str, expected: str) -> None:
    """expected_behavior_source: the brief, item 1 ("a separator at either end is dropped")."""
    assert normalise(text) == expected


def test_other_punctuation_is_no_separator() -> None:
    """expected_behavior_source: AC-1 (the separators are `-`, `_`, `.` and the space);
    the brief, item 1.
    """
    assert normalise("a/b:c@d+e=f,g") == "a/b:c@d+e=f,g"


@pytest.mark.parametrize("prefix", TABLE)
def test_a_prefix_of_the_table_is_removed(prefix: str) -> None:
    """expected_behavior_source: AC-1; BC-18; ADR-005 decision 1; the brief, item 1.

    The prefix is removed after case folding, bracket removal and trimming.
    """
    assert normalise(prefix + "Model-1") == "model-1"
    assert normalise(prefix.upper() + "Model-1") == "model-1"
    assert normalise(f"  {prefix}model-1[effort=high]  ") == "model-1"


@pytest.mark.parametrize("text", OUTSIDE_THE_TABLE)
def test_a_prefix_outside_the_table_is_kept(text: str) -> None:
    """expected_behavior_source: AC-1 ("the closed table"); ADR-005 decision 1 ("a closed
    list"); the brief, item 1.

    `meta/`, `openrouter/` and `mistral/` are not in the table, and a listed provider name
    that does not stand at the start or is not followed by `/` is no prefix.
    """
    assert normalise(text) == text


def test_only_one_provider_prefix_is_removed() -> None:
    """expected_behavior_source: the brief, item 1 ("one provider prefix ... is removed")."""
    assert normalise("anthropic/openai/gpt-6") == "openai/gpt-6"
    assert normalise("xai/xai/grok") == "xai/grok"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("fable-5.1-xhigh", "fable-5-1-xhigh"),
        ("claude-opus-5-5-xhigh", "claude-opus-5-5-xhigh"),
        ("gpt-6.1-sol-high", "gpt-6-1-sol-high"),
        ("opus-fast", "opus-fast"),
        ("claude-opus-5-5-1m", "claude-opus-5-5-1m"),
    ],
)
def test_a_suffix_is_not_stripped(text: str, expected: str) -> None:
    """expected_behavior_source: AC-1 ("A suffix such as `-xhigh` is not stripped"); ADR-005
    decision 1; the brief, item 1.
    """
    assert normalise(text) == expected


@pytest.mark.parametrize("text", NO_NAME)
def test_text_without_a_name_normalises_to_the_empty_string(text: str) -> None:
    """expected_behavior_source: the brief, item 1 (each step applied in order)."""
    assert normalise(text) == ""


def test_nfkc_folds_the_full_width_text_of_these_tests_back() -> None:
    """expected_behavior_source: the brief, item 1 (NFKC first); a premise of the full-width
    cases: NFKC turns each character that `fullwidth` writes back into ASCII.
    """
    ascii_text = string.digits + string.ascii_letters + string.punctuation + " "

    assert fullwidth(ascii_text) != ascii_text
    assert unicodedata.normalize("NFKC", fullwidth(ascii_text)) == ascii_text


@given(st.text(max_size=60))
def test_normalise_leaves_no_separator_run_and_no_separator_at_an_end(text: str) -> None:
    """expected_behavior_source: AC-1; the brief, item 1 (the last step, for any text)."""
    result = normalise(text)

    assert not set(result) & set("_. ")
    assert "--" not in result
    assert not result.startswith("-")
    assert not result.endswith("-")


@given(recorded_text)
def test_normalised_recorded_text_has_no_upper_case_letter(text: str) -> None:
    """expected_behavior_source: AC-1 ("case folding"); the brief, item 1."""
    result = normalise(text)

    assert result == result.lower()


@given(st.sampled_from(TABLE), plain_text)
def test_a_table_prefix_never_changes_the_normalised_form(prefix: str, name: str) -> None:
    """expected_behavior_source: AC-1; BC-18; ADR-005 decision 1; the brief, item 1."""
    assert normalise(prefix + name) == normalise(name)


@given(unbracketed_text, unbracketed_text)
def test_a_trailing_option_list_never_changes_the_name(name: str, options: str) -> None:
    """expected_behavior_source: AC-1; BC-18; ADR-005 decision 1; the brief, item 1."""
    assert normalise(f"{name}[{options}]") == normalise(name)


# --- AC-2: same_identity ---------------------------------------------------


@pytest.mark.parametrize("other", ["claude-opus-5-5", "opus"])
@pytest.mark.parametrize("spelling", list(OPUS_SPELLINGS.values()), ids=list(OPUS_SPELLINGS))
def test_a_spelling_is_the_same_identity_as_the_id_and_alias(spelling: str, other: str) -> None:
    """expected_behavior_source: AC-2; BC-18; R-7; ADR-007 decision 3; the brief, items 2
    and 4.

    An alias that resolves to the id, an effort, speed or context option, a provider prefix,
    display text, an `also_known_as` spelling and full-width text are no difference.
    """
    assert identities(spelling, other) == {True}


def test_every_two_spellings_of_one_model_are_the_same_identity() -> None:
    """expected_behavior_source: AC-2; BC-18; R-7; ADR-007 decision 3; the brief, item 4."""
    for spellings in (OPUS_SPELLINGS, SOL_SPELLINGS):
        for first in spellings.values():
            for second in spellings.values():
                assert identities(first, second) == {True}, (first, second)


def test_two_different_models_are_different_identities() -> None:
    """expected_behavior_source: AC-2; BC-18; the brief, item 4 (`False` for two entries)."""
    for first in OPUS_SPELLINGS.values():
        for second in SOL_SPELLINGS.values():
            assert identities(first, second) == {False}, (first, second)
            assert identities(second, first) == {False}, (second, first)


@pytest.mark.parametrize("unknown", list(UNMATCHED.values()), ids=list(UNMATCHED))
def test_a_string_that_matches_no_entry_is_unknown_against_anything(unknown: str) -> None:
    """expected_behavior_source: AC-2 ("neither equal to nor different from anything");
    BC-18; BC-19; ADR-005 decision 1; ADR-007 decision 3; the brief, item 4.
    """
    for other in ALL_SPELLINGS:
        assert identities(unknown, other) == {None}, other
        assert identities(other, unknown) == {None}, other


@pytest.mark.parametrize("unknown", list(UNMATCHED.values()), ids=list(UNMATCHED))
def test_an_unknown_string_is_not_equal_to_the_same_text(unknown: str) -> None:
    """expected_behavior_source: AC-2 ("including another unknown string with the same
    text"); BC-19; the brief, item 4 ("Two equal unmatched strings are `None`").
    """
    assert identities(unknown, unknown) == {None}
    assert identities(unknown, unknown.upper()) == {None}


@pytest.mark.parametrize("spelling", UNLISTED_SUFFIXES)
def test_an_unlisted_suffix_is_unknown_and_never_a_difference(spelling: str) -> None:
    """expected_behavior_source: AC-1 (a suffix is not stripped); AC-2; ADR-005 decision 1
    ("the spellings that clients report are listed as `also_known_as` in data"); the brief.
    """
    assert identities(spelling, "claude-opus-5-5") == {None}
    assert identities(spelling, "gpt-6.1-sol") == {None}


def test_same_identity_gives_the_same_answer_in_either_order() -> None:
    """expected_behavior_source: AC-2 (an identity is a relation of two strings); the brief,
    item 4.
    """
    for first in ALL_SPELLINGS:
        for second in ALL_SPELLINGS:
            assert identities(first, second) == identities(second, first), (first, second)


def test_a_string_that_two_entries_claim_is_unknown() -> None:
    """expected_behavior_source: ADR-005 decision 1 (a duplicate cannot steer a family);
    the brief, items 3 and 4.
    """
    catalog = (OPUS, model("entry-b", route("opus")))

    assert identities("opus", "opus", catalog) == {None}
    assert identities("opus", "claude-opus-5-5", catalog) == {None}
    assert identities("claude-opus-5-5", "Claude Opus 5.5", catalog) == {True}


def test_a_proposed_entry_gives_no_identity_when_proposed_entries_are_skipped() -> None:
    """expected_behavior_source: BC-10 ("a `proposed` entry never contributes to identity");
    ADR-007 decision 1; the brief, items 3 and 4.
    """
    catalog = (dataclasses.replace(OPUS, approval="proposed"), SOL)

    assert same_identity("opus", "claude-opus-5-5", catalog, skip_proposed=True) is None
    assert same_identity("opus", "gpt-6.1-sol", catalog, skip_proposed=True) is None
    assert same_identity("opus", "claude-opus-5-5", catalog, skip_proposed=False) is True
    assert same_identity("opus", "gpt-6.1-sol", catalog, skip_proposed=False) is False


@given(model_text, model_text, st.booleans())
def test_same_identity_is_symmetric(first: str, second: str, skip_proposed: bool) -> None:
    """expected_behavior_source: AC-2; the brief, item 4."""
    forward = same_identity(first, second, MIXED, skip_proposed=skip_proposed)
    backward = same_identity(second, first, MIXED, skip_proposed=skip_proposed)

    assert forward == backward


@given(model_text, st.booleans())
def test_a_string_is_never_different_from_itself(text: str, skip_proposed: bool) -> None:
    """expected_behavior_source: AC-2; the brief, items 3 and 4 (`True` for one matched entry,
    `None` for no match or an ambiguous one).
    """
    expected = None if match_entry(text, MIXED, skip_proposed=skip_proposed) is None else True

    assert same_identity(text, text, MIXED, skip_proposed=skip_proposed) is expected


# --- AC-2 and AC-4: match_entry --------------------------------------------

MATCHES = {
    f"{label}-{name}": (spelling, entry)
    for label, spellings, entry in (("opus", OPUS_SPELLINGS, OPUS), ("sol", SOL_SPELLINGS, SOL))
    for name, spelling in spellings.items()
}
KEYWORD_CALLS: dict[str, tuple[Callable[..., object], tuple[object, ...]]] = {
    "match_entry": (match_entry, ("opus", CATALOG)),
    "same_identity": (same_identity, ("opus", "opus", CATALOG)),
    "family_of": (family_of, ("opus", CATALOG)),
}


@pytest.mark.parametrize(("spelling", "entry"), list(MATCHES.values()), ids=list(MATCHES))
def test_match_entry_returns_the_named_entry_itself(spelling: str, entry: CatalogEntry) -> None:
    """expected_behavior_source: AC-2; BC-18; the brief, items 2 and 3 ("returned as the same
    object").
    """
    assert match_entry(spelling, CATALOG, skip_proposed=True) is entry
    assert match_entry(spelling, CATALOG, skip_proposed=False) is entry


@pytest.mark.parametrize("unknown", list(UNMATCHED.values()), ids=list(UNMATCHED))
def test_match_entry_finds_nothing_for_an_unknown_or_empty_string(unknown: str) -> None:
    """expected_behavior_source: AC-2; BC-19; the brief, item 3 (no match, and an empty
    normalised form).
    """
    assert match_entry(unknown, CATALOG, skip_proposed=False) is None


def test_every_name_of_every_route_is_a_name_of_its_entry() -> None:
    """expected_behavior_source: AC-2 ("the `resolves_to` or an `also_known_as` of a route");
    the brief, item 2 (a route without a `name` still gives its other names).
    """
    entry = model(
        "entry-x",
        route(None, "Example Large 1", resolves_to="example-large-1-20261101"),
        route("example-large-latest"),
    )
    catalog = (OPUS, entry, SOL)

    for spelling in ("example_large_1", "example-large-1-20261101", "Example Large Latest"):
        assert match_entry(spelling, catalog, skip_proposed=False) is entry, spelling


def test_a_string_that_two_entries_claim_matches_neither_entry() -> None:
    """expected_behavior_source: ADR-005 decision 1 ("a family cannot be steered by a
    duplicate"); the brief, item 3 (more than one match is no match).
    """
    first = model("entry-a", route("Shared Name"), route("only-in-a"))
    second = model("entry-b", route("x", "shared_name[1m]"))
    catalog = (first, second)

    assert match_entry("shared-name", catalog, skip_proposed=False) is None
    assert match_entry("only-in-a", catalog, skip_proposed=False) is first
    assert match_entry("x", catalog, skip_proposed=False) is second


def test_the_same_entry_listed_twice_is_ambiguous() -> None:
    """expected_behavior_source: the brief, items 3, 4 and 7 (entries are told apart by
    their position in the catalog).
    """
    assert match_entry("opus", (OPUS, OPUS), skip_proposed=False) is None
    assert identities("opus", "claude-opus-5-5", (OPUS, OPUS)) == {None}


def test_the_order_of_the_catalog_does_not_change_the_match() -> None:
    """expected_behavior_source: the brief, item 3 ("the one entry whose names contain")."""
    for spelling in OPUS_SPELLINGS.values():
        assert match_entry(spelling, [SOL, OPUS], skip_proposed=False) is OPUS, spelling


@pytest.mark.parametrize("approval", APPROVAL_STATES)
def test_skip_proposed_leaves_out_only_proposed_entries(approval: ApprovalState) -> None:
    """expected_behavior_source: AC-4; BC-10; ADR-007 decision 1 ("entries whose
    `approval.state` is not `proposed`"); the brief, item 3.
    """
    entry = dataclasses.replace(OPUS, approval=approval)
    catalog = (entry, SOL)
    expected = None if approval == "proposed" else entry

    assert match_entry("opus", catalog, skip_proposed=True) is expected
    assert match_entry("opus", catalog, skip_proposed=False) is entry


def test_a_proposed_duplicate_is_no_ambiguity_once_it_is_skipped() -> None:
    """expected_behavior_source: AC-4 ("seed text no team approved never creates a family
    difference"); BC-10; ADR-007 decision 1; the brief, item 3.
    """
    catalog = (OPUS, model("entry-b", route("OPUS"), approval="proposed"))

    assert match_entry("opus", catalog, skip_proposed=True) is OPUS
    assert match_entry("opus", catalog, skip_proposed=False) is None


@pytest.mark.parametrize("name", list(KEYWORD_CALLS))
def test_skip_proposed_must_be_given_and_only_by_keyword(name: str) -> None:
    """expected_behavior_source: the brief, item 3 ("`skip_proposed` is a required keyword
    argument") and the signatures of `same_identity` and `family_of`.
    """
    function, arguments = KEYWORD_CALLS[name]

    function(*arguments, skip_proposed=False)
    with pytest.raises(TypeError):
        function(*arguments)
    with pytest.raises(TypeError):
        function(*arguments, False)


# --- AC-4: family_of -------------------------------------------------------


@pytest.mark.parametrize(
    ("spelling", "family"),
    [
        ("opus", "anthropic"),
        ("Claude Opus 5.5[effort=high]", "anthropic"),
        ("openai/gpt-6.1-sol", "openai"),
    ],
)
def test_family_of_is_the_family_of_the_matched_entry(spelling: str, family: str) -> None:
    """expected_behavior_source: AC-4 ("returns the family of the catalog entry that a
    string matches"); ADR-007 decision 1; the brief, item 5.
    """
    assert family_of(spelling, CATALOG, skip_proposed=True) == family
    assert family_of(spelling, CATALOG, skip_proposed=False) == family


@pytest.mark.parametrize("unknown", list(UNMATCHED.values()), ids=list(UNMATCHED))
def test_the_family_of_an_unknown_string_is_unknown(unknown: str) -> None:
    """expected_behavior_source: AC-2; BC-19 (an unknown identity cannot establish a family
    difference); ADR-005 decision 1; the brief, item 5.
    """
    assert family_of(unknown, CATALOG, skip_proposed=True) is None
    assert family_of(unknown, CATALOG, skip_proposed=False) is None


@pytest.mark.parametrize("skip_proposed", [True, False])
@pytest.mark.parametrize("approval", APPROVAL_STATES)
def test_only_a_proposed_entry_is_left_out_and_only_when_asked(
    approval: ApprovalState,
    skip_proposed: bool,
) -> None:
    """expected_behavior_source: AC-4 ("can be told to use only entries whose approval state
    is not `proposed`"); BC-10; ADR-007 decision 1; the brief, items 3 and 5.

    A `disabled` or `retired` entry still gives its family.
    """
    catalog = (dataclasses.replace(OPUS, approval=approval), SOL)
    expected = None if skip_proposed and approval == "proposed" else "anthropic"

    assert family_of("opus", catalog, skip_proposed=skip_proposed) == expected


@pytest.mark.parametrize("family", ["anthropic", "example-family"])
def test_two_entries_that_claim_a_name_give_no_family(family: str) -> None:
    """expected_behavior_source: BC-9 (two entries that claim one name are an error); ADR-005
    decision 1 ("a family cannot be steered by a duplicate"); the brief, items 3 and 5.

    Even when both entries name the same family, an ambiguous string has none.
    """
    catalog = (OPUS, model("entry-b", route("opus"), family=family))

    assert family_of("opus", catalog, skip_proposed=True) is None
    assert family_of("opus", catalog, skip_proposed=False) is None


def test_a_proposed_duplicate_cannot_steer_the_family() -> None:
    """expected_behavior_source: AC-4; BC-10; ADR-005 decision 1; ADR-007 decision 1; the
    brief, items 3 and 5.
    """
    catalog = (OPUS, model("entry-b", route("opus[1m]"), approval="proposed"))

    assert family_of("opus", catalog, skip_proposed=True) == "anthropic"
    assert family_of("opus", catalog, skip_proposed=False) is None


@pytest.mark.parametrize("approval", ["disabled", "retired"])
def test_a_disabled_or_retired_duplicate_still_counts(approval: ApprovalState) -> None:
    """expected_behavior_source: BC-10 (only a `proposed` entry is left out of identity and
    family); ADR-007 decision 1; the brief, item 3.
    """
    catalog = (OPUS, model("entry-b", route("opus"), approval=approval))

    assert family_of("opus", catalog, skip_proposed=True) is None
    assert match_entry("opus", catalog, skip_proposed=True) is None


# --- AC-4: name_conflicts --------------------------------------------------

SHARED = {
    "name-and-name": (route("opus"), route("opus")),
    "name-and-also-known-as": (route("opus"), route("claude-opus-5-5", "opus")),
    "also-known-as-twice": (route("x", "opus-high"), route("y", "opus-high")),
    "case-and-separators": (route("Claude Opus 5.5"), route("claude_opus_5_5")),
    "prefix-and-options": (route("anthropic/opus"), route("opus[1m]")),
    "full-width": (route(fullwidth("OPUS")), route("opus")),
}


@pytest.mark.parametrize(("first", "second"), list(SHARED.values()), ids=list(SHARED))
def test_two_entries_that_claim_one_normalised_name_are_one_conflict(
    first: CatalogRoute,
    second: CatalogRoute,
) -> None:
    """expected_behavior_source: AC-4 ("every pair of entries that claim the same normalised
    route `name` or `also_known_as`"); BC-9; ADR-005 decision 1; the brief, item 7.
    """
    catalog = (model("entry-a", first), model("entry-b", second))

    assert name_conflicts(catalog) == ((0, 1),)


def test_three_entries_that_claim_one_name_give_three_pairs() -> None:
    """expected_behavior_source: AC-4 ("every pair"); BC-9; the brief, item 7."""
    catalog = (
        model("entry-a", route("opus")),
        model("entry-b", route("x", "Opus")),
        model("entry-c", route("OPUS[1m]")),
    )

    assert name_conflicts(catalog) == ((0, 1), (0, 2), (1, 2))


def test_conflicts_are_sorted_index_pairs_each_given_once() -> None:
    """expected_behavior_source: the brief, item 7 ("a sorted tuple of index pairs `(i, j)`
    with `i < j`, each pair once").
    """
    catalog = (
        model("entry-a", route("y")),
        model("entry-b", route("z")),
        model("entry-c", route("z"), route("x")),
        model("entry-d", route("x"), route("y"), route("w")),
        model("entry-e", route("w", "v")),
        model("entry-f", route(None, "V")),
    )

    assert name_conflicts(catalog) == ((0, 3), (1, 2), (2, 3), (3, 4), (4, 5))


def test_two_entries_that_share_two_names_are_one_pair() -> None:
    """expected_behavior_source: the brief, item 7 ("each pair once")."""
    catalog = (
        model("entry-a", route("alpha"), route("beta")),
        model("entry-b", route("ALPHA"), route("Beta")),
    )

    assert name_conflicts(catalog) == ((0, 1),)


def test_a_name_repeated_within_one_entry_is_no_conflict() -> None:
    """expected_behavior_source: AC-4 ("pair of entries"); the brief, item 7 ("two routes of
    the same entry with the same name are no conflict").
    """
    repeated = model(
        "entry-a",
        route("opus", "OPUS", "opus[1m]"),
        route("Opus"),
        route("x", "opus"),
    )

    assert name_conflicts((repeated,)) == ()
    assert name_conflicts((repeated, SOL)) == ()


def test_names_that_normalise_to_nothing_are_no_conflict() -> None:
    """expected_behavior_source: the brief, items 2 and 7 ("names that normalise to the empty
    string are ignored").
    """
    catalog = (
        model("entry-a", route("[1m]"), route(None)),
        model("entry-b", route("---", "", "   ")),
        model("entry-c", route(None, "anthropic/", "[effort=high]")),
    )

    assert name_conflicts(catalog) == ()


@pytest.mark.parametrize("approval", APPROVAL_STATES)
def test_an_entry_in_every_approval_state_can_conflict(approval: ApprovalState) -> None:
    """expected_behavior_source: BC-9; ADR-005 decision 1 ("Two catalog entries that claim
    the same normalised `name` or `also_known_as` are an error"); the brief, item 7 ("any
    approval state").
    """
    catalog = (OPUS, model("entry-b", route("opus"), approval=approval))

    assert name_conflicts(catalog) == ((0, 1),)
    assert name_conflicts((catalog[1], catalog[0])) == ((0, 1),)


def test_the_same_entry_listed_twice_is_a_conflict() -> None:
    """expected_behavior_source: the brief, item 7 ("for every two entries", by index)."""
    assert name_conflicts((OPUS, SOL, OPUS)) == ((0, 2),)


def test_a_catalog_without_a_shared_name_has_no_conflict() -> None:
    """expected_behavior_source: AC-4 ("take plain values"); the brief, item 7.

    The test catalog has none; a list works as well as a tuple; an empty or one-entry
    catalog has none.
    """
    assert name_conflicts(CATALOG) == ()
    assert name_conflicts([OPUS, SOL]) == ()
    assert name_conflicts(()) == ()
    assert name_conflicts((OPUS,)) == ()


# --- AC-4: plain values ----------------------------------------------------

FROZEN = {
    "catalog-route": (route("opus"), "name"),
    "catalog-entry": (OPUS, "family"),
    "exclusion-rule": (SEED, "aliases"),
}


@pytest.mark.parametrize(("value", "field"), list(FROZEN.values()), ids=list(FROZEN))
def test_the_inputs_are_frozen_dataclasses(value: object, field: str) -> None:
    """expected_behavior_source: AC-4 ("Both take plain values"); the brief (`frozen=True`)."""
    assert dataclasses.is_dataclass(value)
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(value, field, "changed")


def test_the_inputs_are_plain_values_and_not_contract_objects() -> None:
    """expected_behavior_source: AC-4 ("take plain values, not contract objects"); the brief
    (dataclasses with `slots=True`).

    No class in their hierarchy comes from outside the domain, so no contract class is one.
    """
    for kind in (CatalogRoute, CatalogEntry, ExclusionRule):
        modules = {cls.__module__ for cls in kind.__mro__}
        assert all(name == "builtins" or in_the_domain(name) for name in modules), kind
        assert "__slots__" in vars(kind), kind


def test_the_optional_fields_of_the_inputs_default_to_empty() -> None:
    """expected_behavior_source: the brief (the defaults of the three dataclasses)."""
    plain = CatalogRoute(name="opus")

    assert plain == CatalogRoute(name="opus", resolves_to=None, also_known_as=())
    assert CatalogEntry(id="m", family="f", approval="approved").routes == ()
    assert ExclusionRule() == ExclusionRule(aliases=(), id_patterns=(), family_tags=())


# --- AC-3: is_excluded -----------------------------------------------------

FABLE_VARIANTS = [
    "FABLE",
    " Fable-5.1 ",
    "anthropic/claude-fable-5-1",
    "Claude Fable 5.1",
    "claude_fable_5_1",
    "claude-fable-5-1[effort=high]",
    "Fable5",
    "fable-5.1-xhigh",
    "x[model=fable]",
]
BEST_VARIANTS = ["BEST", " best ", "best[1m]", "anthropic/best"]
FULL_WIDTH_VARIANTS = [
    fullwidth("FABLE"),
    fullwidth("Claude Fable 5.1"),
    fullwidth("anthropic/best"),
    fullwidth("best[1m]"),
]
CLEAN = ["claude-opus-5-5", "gpt-6.1-sol", "sonnet", "bestow"]
BY_ALIAS = {
    "upper-case": ("FABLE", True),
    "padded": (" Fable ", True),
    "with-options": ("fable[1m]", True),
    "with-a-provider-prefix": ("anthropic/fable", True),
    "full-width": (fullwidth("fable"), True),
    "with-a-version": ("Fable5", False),
    "with-a-separated-version": ("fable-5.1", False),
    "inside-a-bracket": ("x[model=fable]", False),
    "inside-an-id": ("claude-fable-5-1", False),
    "split-by-a-separator": ("fa_ble", False),
}
BY_PATTERN = {
    "the-id": ("claude-fable-5-1", True),
    "upper-case": ("Claude-Fable-5", True),
    "provider-prefix": ("anthropic/claude-fable-5-1", True),
    "underscores": ("claude_fable_5_1", True),
    "display-text": ("Claude Fable 5.1", True),
    "options": ("claude-fable-5-1[effort=high]", True),
    "padded": (" claude-fable-5 ", True),
    "full-width": (fullwidth("claude-fable-5"), True),
    "the-alias": ("fable", False),
    "the-tag-alone": ("Fable5", False),
    "another-model": ("claude-opus-5-5", False),
    "inside-a-bracket": ("x[model=fable]", False),
    "no-hyphen-after-the-stem": ("claude-fable", False),
    "no-separators": ("claudefable5", False),
}
BY_TAG = {
    "a-version-without-a-separator": ("Fable5", True),
    "a-suffix": ("fable-5.1-xhigh", True),
    "inside-a-bracket": ("x[model=fable]", True),
    "underscores": ("claude_fable_5_1", True),
    "upper-case": ("FABLE", True),
    "a-separator-between-each-letter": ("f-a-b-l-e", True),
    "mixed-separators-and-case": ("F.a_b l-e", True),
    "split-by-an-option-list": ("fa[effort=high]ble", True),
    "inside-a-longer-word": ("superfable", True),
    "another-model": ("claude-opus-5-5", False),
    "a-word-that-shares-letters": ("fabric", False),
    "sonnet": ("sonnet", False),
    "a-letter-short": ("fabe", False),
}
FOLDED_PATTERNS = [
    "Claude-Fable-*",
    "CLAUDE-FABLE-*",
    fullwidth("claude-fable-*"),
]
# As regular expressions each of these matches `claude-fable-5`; as patterns they must not.
REGEX_PATTERNS = [
    r"claude-fable-\d+",
    "claude-(fable|opus)-5",
    "claude-fable-[0-9]",
    "claude-fable-.+",
    "claude-fable-.*",
]
NO_RULES: dict[str, Sequence[ExclusionRule]] = {
    "an-empty-tuple": (),
    "an-empty-list": [],
    "one-empty-rule": [ExclusionRule()],
}


@pytest.mark.parametrize("spelling", [*FABLE_VARIANTS, *BEST_VARIANTS])
def test_every_variant_of_bc_9_is_excluded(spelling: str) -> None:
    """expected_behavior_source: AC-3 (the nine Fable variants and the four of `best`); BC-9;
    R-12; ADR-005 decisions 1 and 3; the brief, item 6.
    """
    assert is_excluded(spelling, (SEED,)) is True


@pytest.mark.parametrize("spelling", FULL_WIDTH_VARIANTS)
def test_a_full_width_spelling_is_excluded(spelling: str) -> None:
    """expected_behavior_source: AC-3 ("a full-width spelling matches"); R-12; ADR-005
    decision 1 (NFKC); the brief, item 6.
    """
    assert is_excluded(spelling, (SEED,)) is True


@pytest.mark.parametrize("spelling", CLEAN)
def test_a_model_that_is_not_fable_or_best_is_not_excluded(spelling: str) -> None:
    """expected_behavior_source: AC-3 ("`claude-opus-5-5`, `gpt-6.1-sol`, `sonnet` and
    `bestow` do not"); the brief, item 6.
    """
    assert is_excluded(spelling, (SEED,)) is False


@pytest.mark.parametrize(("text", "expected"), list(BY_ALIAS.values()), ids=list(BY_ALIAS))
def test_an_alias_matches_the_whole_normalised_string_only(text: str, expected: bool) -> None:
    """expected_behavior_source: AC-3 ("by exact alias after normalisation"); ADR-005
    decision 1 ("or when the string equals a listed alias"); the brief, item 6 (a).
    """
    assert is_excluded(text, (ALIASES_ONLY,)) is expected


@pytest.mark.parametrize("alias", ["Claude Fable", "claude_fable", "xai/claude-fable[1m]"])
def test_an_alias_is_compared_in_its_normalised_form(alias: str) -> None:
    """expected_behavior_source: AC-3; the brief, item 6 (a) (`normalise(alias)`)."""
    rule = ExclusionRule(aliases=(alias,))

    for spelling in ("claude-fable", "CLAUDE.FABLE", "anthropic/Claude Fable"):
        assert is_excluded(spelling, (rule,)) is True, spelling
    assert is_excluded("claude-fable-5", (rule,)) is False


@pytest.mark.parametrize("alias", ["", "   ", "[1m]", "---", "anthropic/"])
def test_an_alias_that_normalises_to_nothing_excludes_nothing(alias: str) -> None:
    """expected_behavior_source: the brief, item 6 (a) ("an alias whose normalised form is
    not empty").
    """
    rule = ExclusionRule(aliases=(alias,))

    for spelling in ("", "   ", "[effort=high]", "-", "opus"):
        assert is_excluded(spelling, (rule,)) is False, spelling


@pytest.mark.parametrize(("text", "expected"), list(BY_PATTERN.values()), ids=list(BY_PATTERN))
def test_an_id_pattern_matches_the_raw_or_the_normalised_form(text: str, expected: bool) -> None:
    """expected_behavior_source: AC-3 ("on the raw NFKC and case-folded string ... and on
    the normalised form"; "by `fnmatch` pattern"); ADR-005 decision 1; the brief, item 6 (b).
    """
    assert is_excluded(text, (PATTERNS_ONLY,)) is expected


def test_an_id_pattern_also_sees_the_brackets_and_their_content() -> None:
    """expected_behavior_source: AC-3 ("brackets included"); ADR-005 decision 1 ("bracket
    contents included"); the brief, item 6 (b) (`[` and `]` are literal).
    """
    options = ExclusionRule(id_patterns=("*[effort=high]",))
    inside = ExclusionRule(id_patterns=("*claude-fable-*",))

    assert is_excluded("claude-opus-5-5[effort=high]", (options,)) is True
    assert is_excluded("claude-opus-5-5[effort=low]", (options,)) is False
    assert is_excluded("claude-opus-5-5", (options,)) is False
    assert is_excluded("sonnet", (options,)) is False
    assert is_excluded("x[model=claude-fable-5]", (inside,)) is True


@pytest.mark.parametrize("pattern", FOLDED_PATTERNS)
def test_an_id_pattern_is_nfkc_folded_and_case_folded(pattern: str) -> None:
    """expected_behavior_source: AC-3; the brief, item 6 (b) ("the pattern,
    NFKC-and-casefolded").
    """
    rule = ExclusionRule(id_patterns=(pattern,))

    assert is_excluded("claude-fable-5", (rule,)) is True
    assert is_excluded("Claude Fable 5.1", (rule,)) is True
    assert is_excluded("claude-opus-5-5", (rule,)) is False


def test_an_id_pattern_is_not_separator_normalised() -> None:
    """expected_behavior_source: the brief, item 6 (b) ("not separator-normalised"); the
    person's decision after F-1 of architecture-reviewer-P-3-r2 to keep this reading until the
    design decides it.
    """
    rule = ExclusionRule(id_patterns=("claude_fable_*",))

    assert is_excluded("claude_fable_5", (rule,)) is True
    assert is_excluded("Claude_Fable_5", (rule,)) is True
    assert is_excluded("claude-fable-5", (rule,)) is False
    assert is_excluded("Claude Fable 5", (rule,)) is False


@pytest.mark.parametrize(
    ("pattern", "named"),
    [
        ("xai/*", "xai/grok-5"),
        ("anthropic/*", "anthropic/claude-opus"),
        ("openai/*-mini", "openai/gpt-6-mini"),
        (".*", ".x"),
        ("-*", "-x"),
        ("*.", "x."),
    ],
)
def test_a_prefix_or_a_separator_never_widens_an_id_pattern(pattern: str, named: str) -> None:
    """expected_behavior_source: AC-3 ("by `fnmatch` pattern"); ADR-005 decision 1 ("a vendor
    the company rules out" is a team exclusion); F-1 of architecture-reviewer-P-3-r2, where a
    normalised pattern became `*` and excluded every model.
    """
    rule = ExclusionRule(id_patterns=(pattern,))

    assert is_excluded(named, (rule,)) is True
    for spelling in ("claude-opus-5-5", "gpt-6-mini", "Claude Opus 5.5"):
        assert is_excluded(spelling, (rule,)) is False, spelling


def test_a_question_mark_stands_for_exactly_one_character() -> None:
    """expected_behavior_source: AC-3 ("`fnmatch` pattern"); ADR-005 decision 1
    ("`fnmatch`-style globs"); the brief, item 6 (b).
    """
    rule = ExclusionRule(id_patterns=("claude-fable-?",))

    assert is_excluded("claude-fable-5", (rule,)) is True
    assert is_excluded("claude-fable-51", (rule,)) is False
    assert is_excluded("claude-fable-", (rule,)) is False


@pytest.mark.parametrize("pattern", REGEX_PATTERNS)
def test_a_pattern_in_regular_expression_syntax_matches_only_itself(pattern: str) -> None:
    """expected_behavior_source: AC-3 ("a pattern with regular-expression syntax matches only
    itself"); ADR-005 decision 1 ("never regular expressions"); the brief, item 6 (b).
    """
    rule = ExclusionRule(id_patterns=(pattern,))

    assert re.fullmatch(pattern, "claude-fable-5"), "as a regular expression it would match"
    assert is_excluded("claude-fable-5", (rule,)) is False
    assert is_excluded("claude-opus-5", (rule,)) is False
    assert is_excluded(pattern, (rule,)) is True


@pytest.mark.parametrize(("text", "expected"), list(BY_TAG.values()), ids=list(BY_TAG))
def test_a_family_tag_matches_once_separators_are_removed(text: str, expected: bool) -> None:
    """expected_behavior_source: AC-3 ("by a family tag that occurs in the string once
    separators are removed"); ADR-005 decision 1; R-12; the brief, item 6 (c).
    """
    assert is_excluded(text, (TAGS_ONLY,)) is expected


@pytest.mark.parametrize("tag", ["Fa-ble", "f a.b_l-e", fullwidth("FABLE")])
def test_a_family_tag_is_folded_and_loses_its_separators(tag: str) -> None:
    """expected_behavior_source: AC-3; the brief, item 6 (c) ("the tag, NFKC-and-casefolded
    with every `-`, `_`, `.` and space removed").
    """
    rule = ExclusionRule(family_tags=(tag,))

    assert is_excluded("claude-fable-5", (rule,)) is True
    assert is_excluded("Fable5", (rule,)) is True
    assert is_excluded("claude-opus-5-5", (rule,)) is False


@pytest.mark.parametrize("tag", ["", " ", "-", " ._-", fullwidth(" ")])
def test_a_family_tag_that_is_empty_once_folded_excludes_nothing(tag: str) -> None:
    """expected_behavior_source: the brief, item 6 (c) ("a non-empty substring")."""
    rule = ExclusionRule(family_tags=(tag,))

    for spelling in ("claude-opus-5-5", "", "fable"):
        assert is_excluded(spelling, (rule,)) is False, spelling


def test_a_model_is_excluded_when_any_rule_matches() -> None:
    """expected_behavior_source: the brief, item 6 ("`True` when at least one rule matches";
    the rules are an `Iterable`).
    """
    rules = (ExclusionRule(aliases=("x-model",)), TAGS_ONLY)

    assert is_excluded("X_Model", rules) is True
    assert is_excluded("Fable5", rules) is True
    assert is_excluded("y-model", rules) is False
    assert is_excluded("Fable5", iter(rules)) is True


@pytest.mark.parametrize("rules", list(NO_RULES.values()), ids=list(NO_RULES))
def test_no_rules_or_an_empty_rule_exclude_nothing(rules: Sequence[ExclusionRule]) -> None:
    """expected_behavior_source: the brief, item 6 ("An empty iterable of rules excludes
    nothing"; a rule with no alias, pattern or tag has nothing to match).
    """
    for spelling in ("fable", "best", "claude-fable-5", ""):
        assert is_excluded(spelling, rules) is False, spelling


@given(recorded_text, st.sampled_from(FABLE_IN_CASES), recorded_text)
def test_recorded_text_that_holds_fable_is_excluded_wherever_it_stands(
    before: str,
    token: str,
    after: str,
) -> None:
    """expected_behavior_source: AC-3; BC-9; R-12; ADR-005 decision 1 (fail-safe: the token
    as a substring of the raw string, bracket contents included); the brief, item 6 (c).
    """
    text = before + token + after

    assert is_excluded(text, (TAGS_ONLY,)) is True
    assert is_excluded(text, (SEED,)) is True


@given(unbracketed_text, separator_gaps, unbracketed_text)
def test_fable_with_separators_between_its_letters_is_excluded_outside_brackets(
    before: str,
    gaps: list[str],
    after: str,
) -> None:
    """expected_behavior_source: AC-3 ("once separators are removed"); ADR-005 decision 1;
    the brief, item 6 (c) (the normalised form with separators removed).
    """
    assert is_excluded(before + spread(gaps) + after, (TAGS_ONLY,)) is True


@given(recorded_text)
def test_no_rule_excludes_any_recorded_text(text: str) -> None:
    """expected_behavior_source: the brief, item 6 ("An empty iterable of rules excludes
    nothing").
    """
    assert is_excluded(text, ()) is False


# --- AC-5: cursor_plain_id -------------------------------------------------

PLAIN_IDS = [
    "claude-opus-5-5",
    "gpt-6.1-sol",
    "composer-2",
    "a",
    "Z",
    "o3",
    "Claude.Opus_5+5/x-y",
    "claude-4-sonnet-thinking",
]
# Words that start like a YAML word or hold one, and are not one of them.
NEAR_YAML_WORDS = [
    "yes2",
    "Nope",
    "null-model",
    "offline",
    "n1",
    "y-1",
    "on-demand",
    "true-north",
    "False1",
    "nn",
    "yy",
    "onn",
]
YAML_WORDS = ("true", "false", "null", "yes", "no", "on", "off", "y", "n")


def in_every_case(word: str) -> set[str]:
    """`word` in lower case, upper case, title case and alternating case."""
    alternating = "".join(
        letter.upper() if index % 2 else letter for index, letter in enumerate(word)
    )
    return {word, word.upper(), word.title(), alternating}


CASED_YAML_WORDS = sorted({cased for word in YAML_WORDS for cased in in_every_case(word)})
BAD_STARTS = [
    "",
    "1claude",
    "9",
    ".claude",
    "-claude",
    "_claude",
    "/claude",
    "+claude",
    " claude",
]
NOT_PLAIN = {
    "space": " ",
    "colon": ":",
    "hash": "#",
    "open-bracket": "[",
    "close-bracket": "]",
    "double-quote": '"',
    "single-quote": "'",
    "at-sign": "@",
    "equals-sign": "=",
    "comma": ",",
    "open-brace": "{",
    "close-brace": "}",
    "ampersand": "&",
    "asterisk": "*",
    "exclamation-mark": "!",
    "vertical-bar": "|",
    "greater-than": ">",
    "percent": "%",
    "backtick": "`",
    "question-mark": "?",
    "tilde": "~",
    "backslash": "\\",
    "tab": "\t",
    "line-feed": "\n",
}
NON_ASCII = {
    "latin-letter-with-an-accent": "claud\u00e9",
    "full-width-letters": fullwidth("claude"),
    "full-width-digit": "claude-opus-" + fullwidth("5"),
    "kelvin-sign": "\u212aimi",
    "dotless-i": "\u0131nfo",
    "long-s": "\u017fonnet",
    "greek-capital-omega": "\u03a9mega",
    "no-break-space": "claude\u00a0opus",
    "zero-width-space": "claude\u200bopus",
}
BRACKETED_IDS = [
    "claude-opus-5[effort=high]",
    "claude-opus-5[effort=high,fast=true]",
]


@pytest.mark.parametrize("name", [*PLAIN_IDS, *NEAR_YAML_WORDS])
def test_a_plain_id_is_accepted(name: str) -> None:
    """expected_behavior_source: AC-5 ("starts with a letter, holds only letters, digits and
    `. _ / + -`"); BC-34; ADR-003 decision 3; the brief, item 8.

    Only the exact YAML words are refused, so a word that merely starts like one is plain.
    """
    assert cursor_plain_id(name) is True


@pytest.mark.parametrize("name", CASED_YAML_WORDS)
def test_a_yaml_word_in_any_letter_case_is_refused(name: str) -> None:
    """expected_behavior_source: AC-5 ("is not one of the YAML words `true`, `false`,
    `null`, `yes`, `no`, `on`, `off`, `y`, `n`"); BC-34; the brief, item 8 (compared
    case-insensitively).
    """
    assert cursor_plain_id(name) is False


@pytest.mark.parametrize("name", BAD_STARTS)
def test_a_name_that_does_not_start_with_an_ascii_letter_is_refused(name: str) -> None:
    """expected_behavior_source: AC-5 ("starts with a letter"); BC-34; the brief, item 8."""
    assert cursor_plain_id(name) is False


@pytest.mark.parametrize("character", list(NOT_PLAIN.values()), ids=list(NOT_PLAIN))
def test_a_character_outside_the_plain_set_is_refused(character: str) -> None:
    """expected_behavior_source: AC-5 ("holds only letters, digits and `. _ / + -`"); BC-34;
    ADR-003 decision 3 ("plain-safe"); the brief, item 8 (the whole name must match).
    """
    assert cursor_plain_id(f"claude{character}opus") is False
    assert cursor_plain_id(f"claude-opus{character}") is False


@pytest.mark.parametrize("name", list(NON_ASCII.values()), ids=list(NON_ASCII))
def test_a_name_with_a_non_ascii_character_is_refused(name: str) -> None:
    """expected_behavior_source: BC-34; the brief, item 8 ("ASCII `[A-Za-z][A-Za-z0-9._/+-]*`";
    "A non-ASCII letter ... give `False`").
    """
    assert cursor_plain_id(name) is False


@pytest.mark.parametrize("name", BRACKETED_IDS)
def test_a_cursor_id_with_a_bracketed_option_is_refused(name: str) -> None:
    """expected_behavior_source: BC-34 ("no bracketed option is written"); ADR-003 decision 3
    ("a Cursor `model` value is written only when it is plain-safe, with no bracketed
    options"); the brief, item 8.
    """
    assert cursor_plain_id(name) is False


# --- AC-5: no clock, locale or environment, and the same result every time ----

CALLS: dict[str, Callable[[], object]] = {
    "normalise": lambda: normalise(" Anthropic/Claude Opus 5.5[effort=high] "),
    "match_entry": lambda: match_entry("opus", CATALOG, skip_proposed=True),
    "same_identity": lambda: same_identity("opus[1m]", "OPUS", CATALOG, skip_proposed=True),
    "family_of": lambda: family_of("GPT 6.1 Sol", CATALOG, skip_proposed=True),
    "is_excluded": lambda: is_excluded("x[model=fable]", (SEED,)),
    "name_conflicts": lambda: name_conflicts((OPUS, SOL, OPUS)),
    "cursor_plain_id": lambda: cursor_plain_id("claude-opus-5-5"),
}


@pytest.mark.parametrize("name", list(CALLS))
def test_every_function_gives_the_same_result_on_every_call(name: str) -> None:
    """expected_behavior_source: AC-5 ("give the same result on every call"); BC-23 ("gives
    the same bytes for the same input"); the brief (pure functions).
    """
    call = CALLS[name]
    first = call()

    assert [call() for _ in range(5)] == [first] * 5


def test_the_module_imports_only_the_standard_library_and_the_domain() -> None:
    """expected_behavior_source: the brief ("Standard library and `orqlet.domain` only")."""
    assert outside_the_brief(imported_modules(inspect.getsource(model_identity))) == set()


def test_the_module_imports_no_clock_locale_or_environment_module() -> None:
    """expected_behavior_source: AC-5 ("The functions read no clock, locale or environment");
    BC-23 ("reads no clock"); the brief ("no clock, locale, environment or I/O").
    """
    imported = imported_modules(inspect.getsource(model_identity))
    top_level = {module.split(".")[0] for module in imported}

    assert top_level & CLOCK_LOCALE_ENVIRONMENT == set()


def test_the_module_reaches_for_no_dynamic_import_and_no_file() -> None:
    """expected_behavior_source: AC-5; BC-23; the brief ("Pure: no ... I/O")."""
    assert used_names(inspect.getsource(model_identity)) & FORBIDDEN_NAMES == set()


def test_the_import_check_finds_what_it_must_refuse() -> None:
    """expected_behavior_source: AC-5 (the failing and the passing case of the checks above)."""
    source = (
        "import os\nfrom time import monotonic\nimport locale\nfrom datetime import date\n"
        "from pydantic import BaseModel\nfrom .. import application\nfrom . import names\n"
        "from .names import plain\nimport unicodedata\n\ndef f() -> None:\n    open('x')\n"
    )
    modules = imported_modules(source)
    top_level = {module.split(".")[0] for module in modules}

    assert outside_the_brief(modules) == {"orqlet", "pydantic"}
    assert top_level & CLOCK_LOCALE_ENVIRONMENT == CLOCK_LOCALE_ENVIRONMENT
    assert {"orqlet.domain", "orqlet.domain.names", "unicodedata"} <= modules
    assert used_names(source) & FORBIDDEN_NAMES == {"open"}
