"""The three-way comparison of proposal section 9.3: what to do with one generated file.

Three hashes decide everything: what is on disk now (`current`), what Orqlet wrote last time
(`recorded`) and what this render wants (`new`). Each is a SHA-256 or `None` when absent.
"""

from __future__ import annotations

from enum import StrEnum

from orqlet.domain.ownership import FileClass, OwnerMode


class FileState(StrEnum):
    UP_TO_DATE = "up-to-date"
    NEW = "new"
    SAFE_UPDATE = "safe-update"  # untouched since Orqlet wrote it; the new render differs
    USER_EDIT_ONLY = "user-edit-only"  # the team changed it and the render did not: leave it
    TAMPERED = "tampered"  # a protected file that no longer equals what Orqlet wrote
    CONFLICT = "conflict"  # both the file and the render changed
    NAME_COLLISION = "name-collision"  # an unmanaged file already holds the path
    ORPHAN_REMOVE = "orphan-remove"  # no longer rendered and still untouched
    ORPHAN_REPORT = "orphan-report"  # no longer rendered but edited: report, keep
    SEEDED_KEEP = "seeded-keep"  # team-owned from now on; nothing to do
    SEEDED_PROPOSAL = "seeded-proposal"  # newer seed text or a name clash: write a proposal only


def classify(
    owner: OwnerMode,
    file_class: FileClass | None,
    *,
    current: str | None,
    recorded: str | None,
    new: str | None,
) -> FileState:
    if owner is OwnerMode.USER:
        return FileState.SEEDED_KEEP
    if owner is OwnerMode.SEEDED:
        return _seeded(current, recorded, new)
    if new is None:
        return _orphan(current, recorded)
    if recorded is None:
        return _unrecorded(current, new)
    if current == new:
        return FileState.UP_TO_DATE
    if current == recorded:
        return FileState.SAFE_UPDATE
    if file_class is FileClass.PROTECTED:
        return FileState.TAMPERED
    return FileState.USER_EDIT_ONLY if new == recorded else FileState.CONFLICT


def _unrecorded(current: str | None, new: str) -> FileState:
    if current is None:
        return FileState.NEW
    return FileState.UP_TO_DATE if current == new else FileState.NAME_COLLISION


def _orphan(current: str | None, recorded: str | None) -> FileState:
    if recorded is None or current is None:
        return FileState.UP_TO_DATE
    return FileState.ORPHAN_REMOVE if current == recorded else FileState.ORPHAN_REPORT


def _seeded(current: str | None, recorded: str | None, new: str | None) -> FileState:
    if new is None:
        return FileState.SEEDED_KEEP
    if recorded is None:
        if current is None:
            return FileState.NEW
        return FileState.UP_TO_DATE if current == new else FileState.SEEDED_PROPOSAL
    if current is None:
        return FileState.SEEDED_KEEP  # the team deleted it; Orqlet never brings it back
    return FileState.SEEDED_PROPOSAL if new != recorded else FileState.SEEDED_KEEP
