"""The monotone rule resolver (proposal section 17.12.4).

Layers are given from the most general (a company pack) to the most specific (the project). A
later layer may add rules and may restate an existing rule only if it is at least as strict.
A restatement that would remove or relax a requirement is an error, never silently ignored, so
adding any layer can only keep or enlarge the set of requirements.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum

from orqlet.domain.digest import digest_of
from orqlet.domain.errors import OrqletError
from orqlet.domain.globs import glob_match


class WeakeningError(OrqletError):
    """A layer tries to relax a rule that an earlier layer set, or repeats a rule in one layer."""


class Level(IntEnum):
    MAY = 1
    SHOULD = 2
    MUST = 3


class Waiver(IntEnum):
    REVIEWED = 1  # a reviewed waiver is possible
    NONE = 2  # no waiver: stricter


class Enforcement(IntEnum):
    GUIDANCE = 1
    REVIEW = 2
    DETERMINISTIC = 3


@dataclass(frozen=True, slots=True)
class Scope:
    """Where a rule applies. An empty set on a dimension means everywhere."""

    paths: frozenset[str] = frozenset()
    roles: frozenset[str] = frozenset()
    phases: frozenset[str] = frozenset()

    def covers(self, other: Scope) -> bool:
        """True when this scope applies wherever `other` does."""
        return all(
            not mine or (bool(theirs) and theirs <= mine)
            for mine, theirs in (
                (self.paths, other.paths),
                (self.roles, other.roles),
                (self.phases, other.phases),
            )
        )

    def matches(self, *, path: str | None, role: str | None, phase: str | None) -> bool:
        """True when the rule applies to the query; a dimension the query omits is not filtered."""
        if path is not None and self.paths and not any(glob_match(g, path) for g in self.paths):
            return False
        if role is not None and self.roles and role not in self.roles:
            return False
        return not (phase is not None and self.phases and phase not in self.phases)


@dataclass(frozen=True, slots=True)
class RuleSpec:
    id: str
    level: Level
    waiver: Waiver
    enforcement: Enforcement
    scope: Scope
    text: str
    source: str

    def at_least_as_strict_as(self, other: RuleSpec) -> bool:
        return (
            self.level >= other.level
            and self.waiver >= other.waiver
            and self.enforcement >= other.enforcement
            and self.scope.covers(other.scope)
        )


@dataclass(frozen=True, slots=True)
class Layer:
    name: str
    rules: tuple[RuleSpec, ...]


def resolve(layers: Sequence[Layer]) -> dict[str, RuleSpec]:
    """Merge layers into one rule per id, sorted by id."""
    merged: dict[str, RuleSpec] = {}
    for layer in layers:
        seen: set[str] = set()
        for rule in layer.rules:
            if rule.id in seen:
                raise WeakeningError(f"rule {rule.id} appears twice in {layer.name}")
            seen.add(rule.id)
            earlier = merged.get(rule.id)
            if earlier is not None and not rule.at_least_as_strict_as(earlier):
                raise WeakeningError(
                    f"{layer.name} would relax rule {rule.id} that {earlier.source} sets"
                )
            merged[rule.id] = rule
    return dict(sorted(merged.items()))


def dominates(bigger: Mapping[str, RuleSpec], smaller: Mapping[str, RuleSpec]) -> bool:
    """True when `bigger` keeps every rule of `smaller` at the same strictness or higher."""
    return all(
        rule_id in bigger and bigger[rule_id].at_least_as_strict_as(rule)
        for rule_id, rule in smaller.items()
    )


def select(
    rules: Mapping[str, RuleSpec],
    *,
    path: str | None = None,
    role: str | None = None,
    phase: str | None = None,
) -> tuple[RuleSpec, ...]:
    """Rules whose scope matches the query, strictest first, then by id."""
    chosen = [r for r in rules.values() if r.scope.matches(path=path, role=role, phase=phase)]
    return tuple(sorted(chosen, key=lambda r: (-r.level, r.id)))


def rules_hash(rules: Sequence[RuleSpec]) -> str:
    """Digest of the rules that apply, independent of which pack supplied them."""
    entries = [
        {
            "id": r.id,
            "level": r.level.name,
            "waiver": r.waiver.name,
            "enforcement": r.enforcement.name,
            "paths": sorted(r.scope.paths),
            "roles": sorted(r.scope.roles),
            "phases": sorted(r.scope.phases),
            "text": r.text,
        }
        for r in sorted(rules, key=lambda rule: rule.id)
    ]
    return digest_of(entries)
