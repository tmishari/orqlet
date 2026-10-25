"""Comparing the approved expected change with what the implementation changed (proposal 17.4.1).

The design declares, per watched surface, what the implementation may change. The extractors
report what it did change. Each watched surface of the final tree gets one result:

* implemented as designed: the change matches an entry's fingerprint;
* pending: the entry is not selected by the claimed phase and is not implemented yet;
* not delivered: the claimed phase selected the entry and delivered nothing;
* deviation: the surface changed but the fingerprint differs;
* additional: a watched surface changed and no entry covers it;
* manual: no extractor exists in this release; the Architecture Reviewer compares by hand.

This proves that the implementation matches the *declared* change on the surfaces that have an
extractor. It cannot see behaviour that no extracted name, signature or file captures.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from orqlet.domain.dependencies import (
    DependencyDelta,
    canonical_name,
    canonical_specifier,
)
from orqlet.domain.python_api import Symbol, canonical_signature, signature_digest


class Outcome(StrEnum):
    IMPLEMENTED = "implemented as designed"
    PENDING = "pending"
    NOT_DELIVERED = "not delivered"
    DEVIATION = "deviation"
    ADDITIONAL = "additional"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class Expectation:
    id: str
    surface: str
    action: str  # add, change or remove
    identity: str
    value: str  # the expected-after text
    verification: str  # extractor or manual
    stages: Mapping[str, str] = field(default_factory=dict)  # stage id -> expected-after text


@dataclass(frozen=True, slots=True)
class ApiDelta:
    added: Mapping[str, Symbol] = field(default_factory=dict)
    removed: Mapping[str, Symbol] = field(default_factory=dict)
    changed: Mapping[str, Symbol] = field(default_factory=dict)  # the new symbol

    def names(self) -> frozenset[str]:
        return frozenset(self.added) | frozenset(self.removed) | frozenset(self.changed)


@dataclass(frozen=True, slots=True)
class Actual:
    api: ApiDelta | None = None
    dependencies: DependencyDelta | None = None
    lock_added: frozenset[str] | None = None  # None when there is no readable lockfile
    lock_removed: frozenset[str] | None = None
    security_paths: tuple[str, ...] = ()  # touched paths on the security globs
    undeclared_files: tuple[str, ...] = ()  # contract or migration files changed, not declared


@dataclass(frozen=True, slots=True)
class Result:
    id: str | None
    surface: str
    outcome: Outcome
    detail: str


def api_delta(before: Mapping[str, Symbol], after: Mapping[str, Symbol]) -> ApiDelta:
    return ApiDelta(
        added={n: s for n, s in after.items() if n not in before},
        removed={n: s for n, s in before.items() if n not in after},
        changed={n: s for n, s in after.items() if n in before and before[n].digest != s.digest},
    )


def compare(
    expectations: Sequence[Expectation],
    selected: frozenset[str],
    actual: Actual,
    expected_lock_packages: Iterable[str] = (),
) -> tuple[Result, ...]:
    """One result per expected change, then one per change that nothing expected."""
    results: list[Result] = []
    covered_symbols: set[str] = set()
    covered_packages: set[str] = set()
    covered_security = False
    for entry in expectations:
        chosen = _is_selected(entry.id, selected)
        value = _expected_value(entry, selected)
        if entry.verification == "manual":
            results.append(
                Result(entry.id, entry.surface, Outcome.MANUAL, "no extractor; compare by hand")
            )
        elif entry.surface == "public-api":
            covered_symbols.add(entry.identity)
            results.append(_compare_api(entry, value, chosen, actual.api))
        elif entry.surface == "dependency":
            covered_packages.add(canonical_name(entry.identity))
            results.append(_compare_dependency(entry, value, chosen, actual.dependencies))
        elif entry.surface == "security":
            covered_security = True
            results.append(_compare_security(entry, value, chosen, actual.security_paths))
        else:
            results.append(Result(entry.id, entry.surface, Outcome.MANUAL, "no extractor"))
    results += _additional(
        actual, covered_symbols, covered_packages, covered_security, expected_lock_packages
    )
    return tuple(results)


def _is_selected(change_id: str, selected: frozenset[str]) -> bool:
    return change_id in selected or any(item.startswith(f"{change_id}@") for item in selected)


def _expected_value(entry: Expectation, selected: frozenset[str]) -> str:
    for stage, value in entry.stages.items():
        if f"{entry.id}@{stage}" in selected:
            return value
    return entry.value


def _missing(chosen: bool) -> Outcome:
    return Outcome.NOT_DELIVERED if chosen else Outcome.PENDING


def _compare_api(entry: Expectation, value: str, chosen: bool, delta: ApiDelta | None) -> Result:
    surface = entry.surface
    if delta is None:
        return Result(entry.id, surface, Outcome.MANUAL, "the public API could not be extracted")
    name = entry.identity
    elsewhere = [
        label
        for label, part in (
            ("added", delta.added),
            ("removed", delta.removed),
            ("changed", delta.changed),
        )
        if name in part and not _is_expected_part(entry.action, label)
    ]
    if elsewhere:
        return Result(
            entry.id,
            surface,
            Outcome.DEVIATION,
            f"{name} was {elsewhere[0]}, but the design says {entry.action}",
        )
    if entry.action == "remove":
        found = name in delta.removed
        return Result(
            entry.id,
            surface,
            Outcome.IMPLEMENTED if found else _missing(chosen),
            f"{name} was removed" if found else f"{name} is still there",
        )
    declared = canonical_signature(value)
    if declared is None:
        return Result(entry.id, surface, Outcome.DEVIATION, "the declared signature cannot be read")
    symbol = (delta.added if entry.action == "add" else delta.changed).get(name)
    if symbol is None:
        return Result(entry.id, surface, _missing(chosen), f"{name} has no {entry.action}")
    if symbol.digest == signature_digest(declared):
        return Result(entry.id, surface, Outcome.IMPLEMENTED, symbol.signature)
    return Result(
        entry.id,
        surface,
        Outcome.DEVIATION,
        f"declared {declared!r} but the code has {symbol.signature!r}",
    )


def _is_expected_part(action: str, label: str) -> bool:
    return (action, label) in {("add", "added"), ("change", "changed"), ("remove", "removed")}


def _compare_dependency(
    entry: Expectation, value: str, chosen: bool, delta: DependencyDelta | None
) -> Result:
    surface = entry.surface
    if delta is None:
        return Result(entry.id, surface, Outcome.MANUAL, "no dependency manifest could be read")
    name = canonical_name(entry.identity)
    wanted = canonical_specifier(value)
    if entry.action == "remove":
        found = name in delta.removed
        return Result(
            entry.id,
            surface,
            Outcome.IMPLEMENTED if found else _missing(chosen),
            f"{name} was removed" if found else f"{name} is still a dependency",
        )
    actual = (
        delta.added.get(name)
        if entry.action == "add"
        else (delta.changed[name][1] if name in delta.changed else None)
    )
    if actual is None:
        return Result(entry.id, surface, _missing(chosen), f"{name} has no {entry.action}")
    if actual == wanted:
        return Result(entry.id, surface, Outcome.IMPLEMENTED, f"{name}{actual}")
    return Result(entry.id, surface, Outcome.DEVIATION, f"declared {wanted!r} but found {actual!r}")


_PATHS = re.compile(r"[\n,]")


def _compare_security(
    entry: Expectation, value: str, chosen: bool, touched: tuple[str, ...]
) -> Result:
    declared = {part.strip() for part in _PATHS.split(value) if part.strip()}
    if not touched:
        return Result(entry.id, entry.surface, _missing(chosen), "no security path was touched")
    outside = sorted(set(touched) - declared)
    if outside:
        return Result(
            entry.id,
            entry.surface,
            Outcome.DEVIATION,
            f"security paths outside the declared ones: {', '.join(outside)}",
        )
    return Result(entry.id, entry.surface, Outcome.IMPLEMENTED, ", ".join(sorted(touched)))


def _additional(
    actual: Actual,
    symbols: set[str],
    packages: set[str],
    security: bool,
    lock_packages: Iterable[str],
) -> list[Result]:
    found: list[Result] = []
    if actual.api is not None:
        for name in sorted(actual.api.names() - symbols):
            found.append(Result(None, "public-api", Outcome.ADDITIONAL, f"{name} changed"))
    if actual.dependencies is not None:
        for name in sorted(actual.dependencies.names() - packages):
            found.append(Result(None, "dependency", Outcome.ADDITIONAL, f"{name} changed"))
        for setting in actual.dependencies.source_changes:
            found.append(
                Result(None, "dependency", Outcome.ADDITIONAL, f"source setting {setting} changed")
            )
    if actual.security_paths and not security:
        found.append(
            Result(
                None,
                "security",
                Outcome.ADDITIONAL,
                f"security paths changed: {', '.join(sorted(actual.security_paths))}",
            )
        )
    allowed = {canonical_name(p) for p in lock_packages} | packages
    for label, names in (("added", actual.lock_added), ("removed", actual.lock_removed)):
        for name in sorted((names or frozenset()) - allowed):
            found.append(
                Result(
                    None,
                    "dependency",
                    Outcome.ADDITIONAL,
                    f"lockfile package {name} was {label}, outside expected_lock_packages",
                )
            )
    for path in actual.undeclared_files:
        found.append(Result(None, "contract", Outcome.ADDITIONAL, f"{path} changed, undeclared"))
    return found
