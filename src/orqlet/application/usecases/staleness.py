"""Which files in a scope changed between two revisions (`validate as-is --against`, 17.3)."""

from __future__ import annotations

from collections.abc import Iterable

from orqlet.application.ports.vcs import TreeFile, Vcs
from orqlet.domain.globs import glob_match


def changed_in_scope(
    vcs: Vcs, base_revision: str, other_revision: str, scope: Iterable[str]
) -> tuple[str, ...] | None:
    """Paths under `scope` that differ between two revisions, sorted; `None` if one is missing.

    A path differs when it exists in one tree only or has another mode or object id. Renames are
    a removal plus an addition, so no similarity guess is involved.
    """
    if not (vcs.has_revision(base_revision) and vcs.has_revision(other_revision)):
        return None
    before = _by_path(vcs.tree_at(base_revision))
    after = _by_path(vcs.tree_at(other_revision))
    patterns = tuple(scope)
    changed = {
        path
        for path in before.keys() | after.keys()
        if before.get(path) != after.get(path)
        and any(glob_match(pattern, path) for pattern in patterns)
    }
    return tuple(sorted(changed))


def _by_path(tree: tuple[TreeFile, ...]) -> dict[str, tuple[str, str]]:
    return {file.path: (file.mode, file.oid) for file in tree}
