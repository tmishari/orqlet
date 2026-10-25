"""Deterministic validation of an implementation plan on a projected tree (proposal 17.5).

A plan lists, per phase, the files it creates, modifies and deletes. Checking every operation
against the base revision would reject the legitimate pattern "create a module in phase 1, extend
it in phase 2", so each phase is checked against `projected(P)`: the base tree after the
operations of all transitive predecessors of P.

Readings of the proposal that the code makes explicit:

* Rule 2 says no two operations of one phase may conflict, while cases 10 and 11 are valid: a
  case-only rename and a file-to-directory replacement. Both pair a `delete` with a `create`, so
  that pair is the only conflict the rule lets through inside one phase (rule 4 says the same:
  a create is checked against the tree minus what its own phase deletes).
* The tracked spelling is the only spelling a plan may use. The proposal states this for
  directories; the same check is applied to the file name of a `modify` or `delete`, because a
  case difference would name another file on a case-sensitive file system.
* Tree entries that cannot be reduced to a canonical path are ignored: no valid plan operation
  can collide with them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from orqlet.domain.errors import InvalidPath
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.paths import CanonicalPath

type Key = tuple[str, ...]


class Op(StrEnum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class EntryMode(StrEnum):
    FILE = "file"
    SYMLINK = "symlink"
    GITLINK = "gitlink"


@dataclass(frozen=True, slots=True)
class FileOperation:
    op: Op
    path: str
    moved_from: str | None = None  # only a `create` may name the file it replaces


@dataclass(frozen=True, slots=True)
class PlanPhase:
    id: str
    depends_on: tuple[str, ...] = ()
    operations: tuple[FileOperation, ...] = ()


@dataclass(frozen=True, slots=True)
class TreeEntry:
    path: str
    mode: EntryMode = EntryMode.FILE


@dataclass(frozen=True, slots=True)
class _Parsed:
    op: Op
    path: CanonicalPath
    moved_from: CanonicalPath | None


@dataclass(frozen=True, slots=True)
class _Tracked:
    parts: tuple[str, ...]
    mode: EntryMode


type _Tree = dict[Key, _Tracked]


def check_plan(tree: Sequence[TreeEntry], phases: Sequence[PlanPhase]) -> tuple[Finding, ...]:
    """Every problem of the plan, sorted so that the order of the phases never matters."""
    found: list[Finding] = []
    parsed = {phase.id: _parse_operations(phase, found) for phase in phases}
    order = _graph(phases, found)
    for phase in phases:
        _check_inside_phase(phase.id, parsed[phase.id], found)
    if order is not None:
        base = _base_tree(tree)
        before = {phase.id: _predecessors(phase.id, phases) for phase in phases}
        for phase in phases:
            projected = _project(base, [p for p in order if p in before[phase.id]], parsed)
            _check_against_projection(phase.id, parsed[phase.id], projected, found)
        _check_concurrent(phases, before, parsed, found)
    return tuple(sorted(found, key=lambda f: (f.code, f.path or "", f.message)))


def structural_changes(phases: Sequence[PlanPhase]) -> tuple[str, ...]:
    """What changes the shape of the tree, derived from the operations and never authored."""
    lines: list[str] = []
    for phase in sorted(phases, key=lambda p: p.id):
        moved = {op.moved_from for op in phase.operations if op.moved_from is not None}
        for op in phase.operations:
            if op.op is Op.CREATE and op.moved_from is not None:
                lines.append(f"{phase.id}: move {op.moved_from} -> {op.path}")
            elif op.op is Op.CREATE:
                lines.append(f"{phase.id}: create {op.path}")
            elif op.op is Op.DELETE and op.path not in moved:
                lines.append(f"{phase.id}: delete {op.path}")
    return tuple(lines)


# --- structure and path identity --------------------------------------------------------------
def _error(code: str, message: str, path: str | None = None) -> Finding:
    return Finding(code, message, Severity.ERROR, path)


def _parse_operations(phase: PlanPhase, found: list[Finding]) -> list[_Parsed]:
    parsed: list[_Parsed] = []
    for operation in phase.operations:
        try:
            path = CanonicalPath.parse(operation.path)
            source = (
                CanonicalPath.parse(operation.moved_from)
                if operation.moved_from is not None
                else None
            )
        except InvalidPath as error:
            found.append(_error("ORQ-E300", f"{phase.id}: {error}", operation.path))
            continue
        if source is not None and operation.op is not Op.CREATE:
            found.append(
                _error(
                    "ORQ-E306",
                    f"{phase.id}: `moved_from` is allowed only on a create, not on a "
                    f"{operation.op.value}",
                    operation.path,
                )
            )
            continue
        parsed.append(_Parsed(operation.op, path, source))
    return parsed


def _graph(phases: Sequence[PlanPhase], found: list[Finding]) -> list[str] | None:
    """A topological order, or `None` when the dependencies are not a valid acyclic graph."""
    ids = [phase.id for phase in phases]
    ok = True
    for phase_id in sorted({i for i in ids if ids.count(i) > 1}):
        found.append(_error("ORQ-E301", f"phase id {phase_id} is used more than once"))
        ok = False
    known = set(ids)
    for phase in phases:
        seen: set[str] = set()
        for dependency in phase.depends_on:
            if dependency == phase.id:
                found.append(_error("ORQ-E303", f"{phase.id} depends on itself"))
                ok = False
            elif dependency not in known:
                found.append(_error("ORQ-E302", f"{phase.id} depends on unknown {dependency}"))
                ok = False
            elif dependency in seen:
                found.append(_error("ORQ-E302", f"{phase.id} lists {dependency} twice"))
                ok = False
            seen.add(dependency)
    if not ok:
        return None
    order = _topological(phases)
    if order is None:
        found.append(_error("ORQ-E304", "the phase dependencies form a cycle"))
    return order


def _topological(phases: Sequence[PlanPhase]) -> list[str] | None:
    remaining = {phase.id: set(phase.depends_on) for phase in phases}
    order: list[str] = []
    while remaining:
        ready = sorted(i for i, deps in remaining.items() if not deps)
        if not ready:
            return None
        order.extend(ready)
        for done in ready:
            del remaining[done]
        for deps in remaining.values():
            deps.difference_update(ready)
    return order


def _predecessors(phase_id: str, phases: Sequence[PlanPhase]) -> frozenset[str]:
    by_id = {phase.id: phase for phase in phases}
    seen: set[str] = set()
    stack = list(by_id[phase_id].depends_on)
    while stack:
        current = stack.pop()
        if current not in seen:
            seen.add(current)
            stack.extend(by_id[current].depends_on)
    return frozenset(seen)


# --- operations inside one phase --------------------------------------------------------------
def _check_inside_phase(phase_id: str, operations: list[_Parsed], found: list[Finding]) -> None:
    for index, first in enumerate(operations):
        for second in operations[index + 1 :]:
            if not first.path.conflicts_with(second.path):
                continue
            if {first.op, second.op} == {Op.DELETE, Op.CREATE}:
                continue  # a replacement: the delete removes what the create would collide with
            found.append(
                _error(
                    "ORQ-E305",
                    f"{phase_id}: {first.op.value} {first.path} and {second.op.value} "
                    f"{second.path} conflict inside one phase",
                    str(first.path),
                )
            )


# --- projection --------------------------------------------------------------------------------
def _base_tree(tree: Sequence[TreeEntry]) -> _Tree:
    base: _Tree = {}
    for entry in tree:
        try:
            path = CanonicalPath.parse(entry.path)
        except InvalidPath:
            continue
        base[path.key] = _Tracked(path.parts, entry.mode)
    return base


def _project(base: _Tree, predecessors: list[str], parsed: Mapping[str, list[_Parsed]]) -> _Tree:
    projected = dict(base)
    for phase_id in predecessors:
        for operation in parsed[phase_id]:
            if operation.op is Op.DELETE:
                projected.pop(operation.path.key, None)
            elif operation.op is Op.CREATE:
                projected[operation.path.key] = _Tracked(operation.path.parts, EntryMode.FILE)
    return projected


def _check_against_projection(
    phase_id: str, operations: list[_Parsed], projected: _Tree, found: list[Finding]
) -> None:
    deleted = {op.path.key for op in operations if op.op is Op.DELETE}
    available = {key: tracked for key, tracked in projected.items() if key not in deleted}
    moved_sources: set[Key] = set()
    for operation in operations:
        if operation.op is Op.CREATE:
            _check_create(phase_id, operation, projected, available, found)
            if operation.moved_from is not None:
                _check_move(phase_id, operation, projected, deleted, moved_sources, found)
        else:
            _check_existing(phase_id, operation, projected, found)


def _check_create(
    phase_id: str, operation: _Parsed, projected: _Tree, available: _Tree, found: list[Finding]
) -> None:
    path = operation.path
    if _blocked_by_link(path, projected):
        found.append(_symlink_error(phase_id, path))
        return
    spelled = _directory_spelling(available)
    for count in range(1, len(path.parts)):
        tracked = spelled.get(path.key[:count])
        if tracked is not None and tracked != path.parts[:count]:
            found.append(
                _error(
                    "ORQ-E312",
                    f"{phase_id}: create {path} spells the directory "
                    f"{'/'.join(path.parts[:count])} differently from the tracked "
                    f"{'/'.join(tracked)}",
                    str(path),
                )
            )
            return
    if _collides(path, available):
        found.append(
            _error(
                "ORQ-E308",
                f"{phase_id}: create {path} collides with a path that already exists "
                "(the same file, or a file and a directory)",
                str(path),
            )
        )


def _check_existing(
    phase_id: str, operation: _Parsed, projected: _Tree, found: list[Finding]
) -> None:
    path = operation.path
    tracked = projected.get(path.key)
    if tracked is None:
        found.append(
            _error(
                "ORQ-E309",
                f"{phase_id}: {operation.op.value} {path} names a file that does not exist "
                "at that point of the plan",
                str(path),
            )
        )
        return
    if tracked.mode is not EntryMode.FILE or _blocked_by_link(path, projected):
        found.append(_symlink_error(phase_id, path))
    elif tracked.parts != path.parts:
        found.append(
            _error(
                "ORQ-E312",
                f"{phase_id}: {operation.op.value} {path} is spelled differently from the "
                f"tracked {'/'.join(tracked.parts)}",
                str(path),
            )
        )


def _check_move(
    phase_id: str,
    operation: _Parsed,
    projected: _Tree,
    deleted: set[Key],
    used: set[Key],
    found: list[Finding],
) -> None:
    source = operation.moved_from
    if source is None:
        return
    problem = None
    if source.key not in projected:
        problem = "does not exist at that point of the plan"
    elif source.key in used:
        problem = "is the source of more than one move"
    elif source.key not in deleted:
        problem = "is not deleted by an operation of the same phase"
    used.add(source.key)
    if problem is not None:
        found.append(
            _error(
                "ORQ-E307",
                f"{phase_id}: create {operation.path} moves from {source}, which {problem}",
                str(operation.path),
            )
        )


def _blocked_by_link(path: CanonicalPath, projected: _Tree) -> bool:
    """True when an ancestor of the path is a symbolic link or a gitlink."""
    for count in range(1, len(path.parts)):
        tracked = projected.get(path.key[:count])
        if tracked is not None and tracked.mode is not EntryMode.FILE:
            return True
    return False


def _symlink_error(phase_id: str, path: CanonicalPath) -> Finding:
    return _error(
        "ORQ-E311",
        f"{phase_id}: {path} is, or sits below, a symbolic link or a gitlink",
        str(path),
    )


def _directory_spelling(tree: _Tree) -> dict[Key, tuple[str, ...]]:
    spelled: dict[Key, tuple[str, ...]] = {}
    for tracked in tree.values():
        for count in range(1, len(tracked.parts)):
            directory = CanonicalPath(tracked.parts[:count])
            spelled.setdefault(directory.key, directory.parts)
    return spelled


def _collides(path: CanonicalPath, available: _Tree) -> bool:
    if any(path.key[:count] in available for count in range(1, len(path.parts) + 1)):
        return True  # the file exists, or a file sits where a directory is needed
    size = len(path.key)
    return any(key[:size] == path.key for key in available)  # a directory exists at the path


# --- concurrent phases -------------------------------------------------------------------------
def _check_concurrent(
    phases: Sequence[PlanPhase],
    before: Mapping[str, frozenset[str]],
    parsed: Mapping[str, list[_Parsed]],
    found: list[Finding],
) -> None:
    ids = sorted(phase.id for phase in phases)
    for index, first in enumerate(ids):
        for second in ids[index + 1 :]:
            if first in before[second] or second in before[first]:
                continue
            for left in parsed[first]:
                for right in parsed[second]:
                    if left.path.conflicts_with(right.path):
                        found.append(
                            _error(
                                "ORQ-E310",
                                f"{first} and {second} are not ordered but both touch "
                                f"{left.path} and {right.path}: add a dependency",
                                str(left.path),
                            )
                        )
