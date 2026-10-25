"""Change classes D1 Delta, D2 Standard and D3 Full (proposal 17.4).

The class sets how deep the design work goes, never whether it happens. It is the maximum of what
the scope triggers, what the architect declares and what an approver raises, and nobody can lower
it: a lower value is rejected, and a lower class after approval needs a new approved design.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from orqlet.domain.globs import glob_match


class ChangeClass(IntEnum):
    D1 = 1
    D2 = 2
    D3 = 3

    @classmethod
    def parse(cls, text: str) -> ChangeClass:
        try:
            return cls[text]
        except KeyError:
            raise ValueError(f"change class must be D1, D2 or D3, not {text!r}") from None


@dataclass(frozen=True, slots=True)
class ChangeScope:
    """What a change touches, as facts the caller derived from the design or the plan."""

    paths: tuple[str, ...]
    one_module: bool  # stays inside one existing module's boundary
    changes_interface: bool = False  # new or changed public interface or contract
    changes_dependency: bool = False
    changes_persisted_format: bool = False
    changes_configuration: bool = False
    trust_boundary: bool = False  # a new trust boundary or external integration
    security_domain: bool = False  # authentication, authorization, cryptography, secrets, IAM
    data_model: bool = False  # a data model or a migration
    infrastructure: bool = False  # infrastructure, deployment or CI
    cross_service_contract: bool = False


@dataclass(frozen=True, slots=True)
class ChangePolicy:
    d1_max_files: int = 10  # initial release value (proposal 17.4); a project can only lower it
    security_globs: tuple[str, ...] = ()
    d3_globs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Trigger:
    change_class: ChangeClass
    reasons: tuple[str, ...]


def trigger_class(scope: ChangeScope, policy: ChangePolicy) -> Trigger:
    """The class the scope triggers, with the reasons, strongest first."""
    d3: list[str] = []
    for flag, reason in (
        (scope.trust_boundary, "a new trust boundary or external integration"),
        (scope.security_domain, "authentication, authorization, cryptography, secrets or IAM"),
        (scope.data_model, "a data model or a migration"),
        (scope.infrastructure, "infrastructure, deployment or CI"),
        (scope.cross_service_contract, "a cross-service contract"),
    ):
        if flag:
            d3.append(reason)
    d3 += _glob_reasons(scope.paths, policy.d3_globs, "a path on a D3 glob")
    d3 += _glob_reasons(scope.paths, policy.security_globs, "a path on a security-sensitive glob")
    if d3:
        return Trigger(ChangeClass.D3, tuple(d3))
    breaks_d1: list[str] = []
    for flag, reason in (
        (not scope.one_module, "the change leaves one module's boundary"),
        (scope.changes_interface, "a new or changed public interface or contract"),
        (scope.changes_dependency, "a new or changed dependency"),
        (scope.changes_persisted_format, "a new or changed persisted format"),
        (scope.changes_configuration, "a new or changed configuration schema"),
        (len(scope.paths) > policy.d1_max_files, f"more than {policy.d1_max_files} files"),
    ):
        if flag:
            breaks_d1.append(reason)
    if breaks_d1:
        return Trigger(ChangeClass.D2, tuple(breaks_d1))
    return Trigger(ChangeClass.D1, ())


def effective_class(
    trigger: ChangeClass, declared: ChangeClass, raised_by_approver: ChangeClass | None = None
) -> ChangeClass:
    return max(trigger, declared, raised_by_approver or ChangeClass.D1)


def _glob_reasons(paths: tuple[str, ...], globs: tuple[str, ...], reason: str) -> list[str]:
    hits = sorted({path for path in paths for pattern in globs if glob_match(pattern, path)})
    return [f"{reason}: {path}" for path in hits]


_GLOB_CHARACTERS = frozenset("*?[")


def shared_directory(patterns: tuple[str, ...]) -> tuple[str, ...]:
    """The directory that every path or glob lies under, as components; empty for the root.

    The literal part of each pattern is the components before the first glob character, and a
    pattern with no glob character names a file, so its directory is its parent. One module's
    boundary is read as one shared non-root directory (a conservative reading: a doubt gives D2).
    """
    directories: list[tuple[str, ...]] = []
    for pattern in patterns:
        parts = pattern.split("/")
        literal: list[str] = []
        for part in parts[:-1]:  # the last component is a file or a glob, never a directory
            if _GLOB_CHARACTERS & set(part):
                break
            literal.append(part)
        directories.append(tuple(literal))
    if not directories:
        return ()
    shared = directories[0]
    for directory in directories[1:]:
        size = 0
        while size < min(len(shared), len(directory)) and shared[size] == directory[size]:
            size += 1
        shared = shared[:size]
    return shared


_ARTIFACT_GROUPS: dict[ChangeClass, tuple[frozenset[str], ...]] = {
    ChangeClass.D1: (
        frozenset({"c4-component"}),
        frozenset({"data-flow"}),
        frozenset({"sequence"}),
        frozenset({"adr", "adr-not-required"}),
    ),
    ChangeClass.D2: (
        frozenset({"c4-container"}),
        frozenset({"c4-component"}),
        frozenset({"data-flow"}),
        frozenset({"sequence"}),
        frozenset({"adr", "adr-not-required"}),
    ),
    ChangeClass.D3: (
        frozenset({"c4-context"}),
        frozenset({"c4-container"}),
        frozenset({"c4-component"}),
        frozenset({"data-flow"}),
        frozenset({"sequence"}),
        frozenset({"adr"}),
    ),
}


def required_artifact_groups(change_class: ChangeClass) -> tuple[frozenset[str], ...]:
    """What a design set must contain at a class; any one kind of a group satisfies it."""
    return _ARTIFACT_GROUPS[change_class]
