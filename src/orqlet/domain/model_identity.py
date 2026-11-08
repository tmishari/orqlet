"""The one matching rule for model strings (ADR-005 decision 1, ADR-007 decisions 1 and 3).

Every comparison of model strings goes through this module: whether two strings name the same
model, which family a string belongs to, whether an exclusion matches it, and whether two catalog
entries claim one name. The functions take plain values, not contract objects, and read no clock,
locale or environment, so the same strings always give the same answer.

Identity is narrow and exclusion is broad, on purpose. A string names a model only through the
catalog: it matches the one entry whose routes list its normalised form. A string that no entry
lists, or that more than one entry lists, is unknown, and an unknown identity is never equal to
and never different from anything, so a duplicate entry cannot steer a family. The exclusion test
needs no catalog and leans the other way: it also reads the raw string with its bracket contents,
and a family tag matches anywhere once separators are removed, so a new spelling of an excluded
model is caught rather than let through.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from itertools import combinations
from typing import Literal

# The closed table of the prefixes that clients put in front of a model id. A vendor's model name
# never belongs here: an exclusion is data in the policy, not code.
PROVIDER_PREFIXES: tuple[str, ...] = ("anthropic/", "openai/", "google/", "xai/")

ApprovalState = Literal["proposed", "approved", "disabled", "retired"]

_SEPARATORS = re.compile(r"[-_. ]+")
_PLAIN_ID = re.compile(r"[A-Za-z][A-Za-z0-9._/+-]*")
# YAML 1.1 reads these as a boolean or null when they stand unquoted, whatever their letter case.
_YAML_WORDS = frozenset({"true", "false", "null", "yes", "no", "on", "off", "y", "n"})


@dataclass(frozen=True, slots=True)
class CatalogRoute:
    """The strings by which one client names a catalog model."""

    name: str | None
    resolves_to: str | None = None
    also_known_as: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """A catalog model: its logical id, its family, its approval state and its routes."""

    id: str
    family: str
    approval: ApprovalState
    routes: tuple[CatalogRoute, ...] = ()


@dataclass(frozen=True, slots=True)
class ExclusionRule:
    """What one `excluded[]` entry matches: aliases, `fnmatch`-style id patterns, family tags."""

    aliases: tuple[str, ...] = ()
    id_patterns: tuple[str, ...] = ()
    family_tags: tuple[str, ...] = ()


def normalise(model: str) -> str:
    """The identity form of a model string.

    NFKC and case folding, every bracketed option list removed, whitespace trimmed, one prefix of
    `PROVIDER_PREFIXES` removed, and each run of `-`, `_`, `.` and space made one `-`, with none at
    either end. A suffix such as `-xhigh` stays: the spellings that clients report are listed as
    `also_known_as` in the catalog, not guessed here.
    """
    text = _without_options(_folded(model)).strip()
    prefix = next((prefix for prefix in PROVIDER_PREFIXES if text.startswith(prefix)), "")
    return _SEPARATORS.sub("-", text[len(prefix) :]).strip("-")


def match_entry(
    model: str, catalog: Sequence[CatalogEntry], *, skip_proposed: bool
) -> CatalogEntry | None:
    """The one catalog entry that names `model`, or `None` when the string is unknown.

    With `skip_proposed`, an entry that no team has approved yet names nothing, so seed text can
    never create a family difference (BC-10). The caller must decide, so it has no default.
    """
    index = _match_index(model, catalog, skip_proposed=skip_proposed)
    return None if index is None else catalog[index]


def same_identity(
    first: str, second: str, catalog: Sequence[CatalogEntry], *, skip_proposed: bool
) -> bool | None:
    """`True` for one model, `False` for two, `None` when either string is unknown."""
    first_index = _match_index(first, catalog, skip_proposed=skip_proposed)
    second_index = _match_index(second, catalog, skip_proposed=skip_proposed)
    if first_index is None or second_index is None:
        return None
    return first_index == second_index


def family_of(model: str, catalog: Sequence[CatalogEntry], *, skip_proposed: bool) -> str | None:
    """The family of the entry that names `model`, or `None` when the string is unknown."""
    entry = match_entry(model, catalog, skip_proposed=skip_proposed)
    return None if entry is None else entry.family


def is_excluded(model: str, exclusions: Iterable[ExclusionRule]) -> bool:
    """True when a rule matches the raw or the normalised form of `model`.

    The raw form is the folded string with its bracket contents, so `x[model=fable]` is seen. A
    rule matches by an alias equal to the normalised string, by an id pattern in which only `*`
    and `?` are wildcards (so a regular expression matches only its own text), or by a family tag
    found anywhere once separators are removed.
    """
    forms = (_folded(model), normalise(model))
    return any(_rule_matches(rule, forms) for rule in exclusions)


def name_conflicts(catalog: Sequence[CatalogEntry]) -> tuple[tuple[int, int], ...]:
    """Index pairs `(i, j)`, `i < j`, of entries that claim one normalised name.

    A claim is a route `name` or `also_known_as`. Every approval state counts, because a proposed
    duplicate would steer a family as soon as it is approved.
    """
    claimants: dict[str, set[int]] = {}
    for index, entry in enumerate(catalog):
        for name in _claimed(entry):
            claimants.setdefault(name, set()).add(index)
    pairs = {pair for indexes in claimants.values() for pair in combinations(sorted(indexes), 2)}
    return tuple(sorted(pairs))


def cursor_plain_id(name: str) -> bool:
    """True when a Cursor `model` value may be written unquoted (ADR-003 decision 3)."""
    return _PLAIN_ID.fullmatch(name) is not None and name.lower() not in _YAML_WORDS


def _folded(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _joined(text: str) -> str:
    return _SEPARATORS.sub("", text)


def _without_options(text: str) -> str:
    """`text` without its bracketed option lists, nested ones included; a lone bracket stays.

    Each matched pair marks its span in a running count, so a string made of many brackets still
    costs linear time: a model string can come from a file that the repository controls.
    """
    covered = [0] * (len(text) + 1)
    opened: list[int] = []
    for index, character in enumerate(text):
        if character == "[":
            opened.append(index)
        elif character == "]" and opened:
            covered[opened.pop()] += 1
            covered[index + 1] -= 1
    kept: list[str] = []
    depth = 0
    for index, character in enumerate(text):
        depth += covered[index]
        if depth == 0:
            kept.append(character)
    return "".join(kept)


def _normalised(texts: Iterable[str | None]) -> set[str]:
    """The normalised forms of `texts`; a form that is empty names nothing and is left out."""
    names = {normalise(text) for text in texts if text is not None}
    names.discard("")
    return names


def _claimed(entry: CatalogEntry) -> set[str]:
    """What the routes of an entry claim as their own: each `name` and `also_known_as`."""
    return _normalised(
        text for route in entry.routes for text in (route.name, *route.also_known_as)
    )


def _names(entry: CatalogEntry) -> set[str]:
    """Every string that names an entry: its claims and what its aliases resolve to.

    The logical `id` is the catalog's own key and not a string that a client reports, so it is
    not one of them.
    """
    return _claimed(entry) | _normalised(route.resolves_to for route in entry.routes)


def _match_index(model: str, catalog: Sequence[CatalogEntry], *, skip_proposed: bool) -> int | None:
    wanted = normalise(model)
    found = [
        index
        for index, entry in enumerate(catalog)
        if not (skip_proposed and entry.approval == "proposed") and wanted in _names(entry)
    ]
    return found[0] if len(found) == 1 else None


def _glob(pattern: str) -> str:
    # In `fnmatch`, `[` opens a character class; made literal, `*` and `?` are the only wildcards.
    return _folded(pattern).replace("[", "[[]")


def _tags(rule: ExclusionRule) -> set[str]:
    tags = {_joined(_folded(tag)) for tag in rule.family_tags}
    tags.discard("")
    return tags


def _rule_matches(rule: ExclusionRule, forms: tuple[str, str]) -> bool:
    normalised = forms[1]
    joined = [_joined(form) for form in forms]
    return (
        normalised in _normalised(rule.aliases)
        or any(fnmatchcase(form, _glob(pattern)) for pattern in rule.id_patterns for form in forms)
        or any(tag in text for tag in _tags(rule) for text in joined)
    )
