"""The pure change plan: what to write, and why (ADR-004, proposal section 9.3).

`build_plan` takes what a render wants, what is on disk and what Orqlet recorded last time, and
returns a plan. It reads and writes nothing. Nothing in the plan is applied until a person has
seen the preview and approved it, and the plan carries a digest so that apply can refuse a plan
that no longer matches the tree it was made from.
"""

from __future__ import annotations

import difflib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from orqlet.domain.blocks import (
    BlockError,
    BlockItem,
    decode_utf8,
    parse_blocks,
    remove_block,
    set_blocks,
)
from orqlet.domain.classify import FileState, classify
from orqlet.domain.digest import digest_of, sha256_hex
from orqlet.domain.errors import OrqletError
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath

PROPOSALS_DIR = CanonicalPath.parse(".orqlet/proposals")
_MAX_PROPOSAL_NAME = 150


class PlanError(OrqletError):
    """The inputs to a plan contradict each other, for example two renders for one path."""


class Action(StrEnum):
    NOOP = "noop"
    CREATE = "create"
    UPDATE = "update"
    RESTORE = "restore"  # a tampered protected file written back
    DELETE = "delete"
    PROPOSE = "propose"  # write a proposal file, change nothing live
    STOP = "stop"  # a conflict: nothing is written for this item


@dataclass(frozen=True, slots=True)
class Desired:
    """One thing the render wants. For a shared block, `content` is the block alone."""

    path: CanonicalPath
    owner: OwnerMode
    file_class: FileClass | None
    content: bytes
    block_name: str | None = None
    insert_after_heading: bool = False
    inputs: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Recorded:
    """One line of the ownership manifest: what Orqlet last wrote."""

    path: CanonicalPath
    owner: OwnerMode
    file_class: FileClass | None
    sha256: str
    block_name: str | None = None
    block: tuple[str, str] | None = None
    entry: str | None = None
    inputs: tuple[tuple[str, str, str], ...] = ()

    @property
    def key(self) -> tuple[str, str]:
        return (str(self.path), self.block_name or "")


@dataclass(frozen=True, slots=True)
class PlannedItem:
    path: CanonicalPath
    block_name: str | None
    owner: OwnerMode
    file_class: FileClass | None
    state: FileState
    action: Action
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PlannedWrite:
    path: CanonicalPath
    kind: str  # "create", "update" or "delete"
    before_sha256: str | None
    after_sha256: str | None
    content: bytes | None
    is_proposal: bool = False
    last: bool = False  # written after every other file (the manifest)


@dataclass(frozen=True, slots=True)
class ChangePlan:
    items: tuple[PlannedItem, ...]
    writes: tuple[PlannedWrite, ...]
    recorded_after: tuple[Recorded, ...]
    findings: tuple[str, ...] = field(default=())

    @property
    def is_empty(self) -> bool:
        return not self.writes

    @property
    def conflicts(self) -> tuple[PlannedItem, ...]:
        return tuple(item for item in self.items if item.action is Action.STOP)

    @property
    def digest(self) -> str:
        """Identifies the plan, its inputs' hashes included, for preview-to-apply integrity."""
        return digest_of(
            [
                [str(w.path), w.kind, w.before_sha256, w.after_sha256, w.is_proposal, w.last]
                for w in sorted(self.writes, key=lambda w: (w.last, w.path.sort_key()))
            ]
        )

    def with_manifest(
        self, path: CanonicalPath, content: bytes, current: bytes | None
    ) -> ChangePlan:
        """Add the ownership manifest as the final write, if it would change."""
        if current == content:
            return self
        write = PlannedWrite(
            path=path,
            kind="create" if current is None else "update",
            before_sha256=None if current is None else sha256_hex(current),
            after_sha256=sha256_hex(content),
            content=content,
            last=True,
        )
        return ChangePlan(self.items, (*self.writes, write), self.recorded_after, self.findings)


def normalised_hash(content: bytes) -> str:
    """SHA-256 with CRLF read as LF, so a Windows checkout classifies like a Linux one."""
    return sha256_hex(content.replace(b"\r\n", b"\n"))


def proposal_path(path: CanonicalPath, block_name: str | None) -> CanonicalPath:
    """Where a proposal for `path` (or one of its blocks) is written."""
    flat = str(path).replace("/", "__") + (f".{block_name}" if block_name else "")
    if len(flat.encode("utf-8")) > _MAX_PROPOSAL_NAME:
        flat = flat.encode("utf-8")[:_MAX_PROPOSAL_NAME].decode("utf-8", "ignore")
        flat += "-" + sha256_hex(str(path).encode("utf-8"))[:12]
    return PROPOSALS_DIR.child(f"{flat}.diff")


def build_plan(
    desired: Sequence[Desired],
    current: Mapping[CanonicalPath, bytes],
    recorded: Sequence[Recorded],
) -> ChangePlan:
    """Classify every desired and recorded file and decide the writes."""
    by_path: dict[str, list[Desired]] = {}
    for item in desired:
        by_path.setdefault(str(item.path), []).append(item)
    old = {entry.key: entry for entry in recorded}
    builder = _Builder(current, old)
    for key in sorted(by_path, key=lambda k: CanonicalPath.parse(k).sort_key()):
        group = by_path[key]
        if any(d.block_name is None for d in group):
            if len(group) != 1:
                raise PlanError(f"{key}: a whole-file render cannot share its path with another")
            builder.whole_file(group[0])
        else:
            builder.blocks(group)
    builder.orphans(desired)
    return builder.finish()


class _Builder:
    def __init__(
        self, current: Mapping[CanonicalPath, bytes], recorded: dict[tuple[str, str], Recorded]
    ) -> None:
        self._current = current
        self._old = recorded
        self._items: list[PlannedItem] = []
        self._writes: dict[str, PlannedWrite] = {}
        self._after: dict[tuple[str, str], Recorded] = {}
        self._seen: set[tuple[str, str]] = set()

    def finish(self) -> ChangePlan:
        writes = tuple(sorted(self._writes.values(), key=lambda w: w.path.sort_key()))
        after = tuple(sorted(self._after.values(), key=lambda r: r.key))
        return ChangePlan(tuple(self._items), writes, after)

    # --- whole files -----------------------------------------------------------------------
    def whole_file(self, wanted: Desired) -> None:
        key = (str(wanted.path), "")
        self._seen.add(key)
        existing = self._current.get(wanted.path)
        state = classify(
            wanted.owner,
            wanted.file_class,
            current=None if existing is None else normalised_hash(existing),
            recorded=self._recorded_hash(key),
            new=normalised_hash(wanted.content),
        )
        action = _ACTIONS[state]
        self._items.append(
            PlannedItem(wanted.path, None, wanted.owner, wanted.file_class, state, action)
        )
        if action in {Action.CREATE, Action.UPDATE, Action.RESTORE}:
            self._write(wanted.path, existing, wanted.content)
        elif action in {Action.PROPOSE, Action.STOP}:
            self._propose(wanted.path, None, existing, wanted.content)
        self._record(wanted, key, state, wanted.content)

    # --- shared blocks ---------------------------------------------------------------------
    def blocks(self, group: list[Desired]) -> None:
        path = group[0].path
        existing = self._current.get(path)
        try:
            text = "" if existing is None else decode_utf8(existing)
            found = {block.name: block for block in parse_blocks(text)}
        except BlockError as exc:
            for wanted in group:
                key = (str(path), wanted.block_name or "")
                self._seen.add(key)
                self._items.append(
                    PlannedItem(
                        path,
                        wanted.block_name,
                        wanted.owner,
                        wanted.file_class,
                        FileState.CONFLICT,
                        Action.STOP,
                        str(exc),
                    )
                )
            return
        applied: list[BlockItem] = []
        for wanted in group:
            name = wanted.block_name or ""
            key = (str(path), name)
            self._seen.add(key)
            now = found.get(name)
            current_hash = (
                None if now is None else normalised_hash(text[now.start : now.end].encode())
            )
            state = classify(
                wanted.owner,
                wanted.file_class,
                current=current_hash,
                recorded=self._recorded_hash(key),
                new=normalised_hash(wanted.content),
            )
            action = _ACTIONS[state]
            self._items.append(
                PlannedItem(path, name, wanted.owner, wanted.file_class, state, action)
            )
            if action in {Action.CREATE, Action.UPDATE, Action.RESTORE}:
                applied.append(_block_item(wanted))
            elif action in {Action.PROPOSE, Action.STOP}:
                shown = b"" if now is None else text[now.start : now.end].encode()
                self._propose(path, name, shown or None, wanted.content)
            self._record(wanted, key, state, wanted.content)
        removals = [
            entry
            for key, entry in self._old.items()
            if key[0] == str(path) and key[1] and key not in self._seen
        ]
        new_text = set_blocks(text, applied, insert_after_heading=group[0].insert_after_heading)
        new_text = self._drop_blocks(path, text, new_text, removals)
        if new_text.encode("utf-8") != (existing or b"") and (existing is not None or new_text):
            self._write(path, existing, new_text.encode("utf-8"))

    def _drop_blocks(
        self, path: CanonicalPath, original: str, text: str, entries: list[Recorded]
    ) -> str:
        """Remove recorded blocks that are no longer rendered, if untouched; report otherwise."""
        found = {block.name: block for block in parse_blocks(original)}
        for entry in entries:
            name = entry.block_name or ""
            self._seen.add(entry.key)
            block = found.get(name)
            current = (
                None
                if block is None
                else normalised_hash(original[block.start : block.end].encode("utf-8"))
            )
            state = classify(
                entry.owner, entry.file_class, current=current, recorded=entry.sha256, new=None
            )
            action = Action.NOOP
            if state is FileState.ORPHAN_REMOVE:
                text, action = remove_block(text, name), Action.DELETE
            elif state is FileState.ORPHAN_REPORT:
                self._after[entry.key] = entry
            self._items.append(
                PlannedItem(path, name, entry.owner, entry.file_class, state, action)
            )
        return text

    # --- recorded files that are no longer rendered ----------------------------------------
    def orphans(self, desired: Sequence[Desired]) -> None:
        wanted_paths = {str(d.path) for d in desired}
        stray_blocks: dict[str, list[Recorded]] = {}
        for key, entry in sorted(self._old.items()):
            if key in self._seen:
                continue
            if entry.block_name is not None:
                stray_blocks.setdefault(key[0], []).append(entry)
                continue
            self._whole_file_orphan(entry)
        for path_text, entries in stray_blocks.items():
            if path_text in wanted_paths:
                continue  # handled with the other blocks of that file
            path = entries[0].path
            existing = self._current.get(path)
            if existing is None:
                self._seen.update(entry.key for entry in entries)
                continue
            try:
                original = decode_utf8(existing)
                text = self._drop_blocks(path, original, original, entries)
            except BlockError:
                self._after.update({entry.key: entry for entry in entries})
                continue
            if text != original:
                if text.strip():
                    self._write(path, existing, text.encode("utf-8"))
                else:
                    self._writes[path_text] = PlannedWrite(
                        path, "delete", sha256_hex(existing), None, None
                    )

    def _whole_file_orphan(self, entry: Recorded) -> None:
        existing = self._current.get(entry.path)
        state = classify(
            entry.owner,
            entry.file_class,
            current=None if existing is None else normalised_hash(existing),
            recorded=entry.sha256,
            new=None,
        )
        action = Action.DELETE if state is FileState.ORPHAN_REMOVE else Action.NOOP
        self._items.append(
            PlannedItem(entry.path, None, entry.owner, entry.file_class, state, action)
        )
        if action is Action.DELETE and existing is not None:
            self._writes[str(entry.path)] = PlannedWrite(
                entry.path, "delete", sha256_hex(existing), None, None
            )
        elif state is FileState.ORPHAN_REPORT:
            self._after[entry.key] = entry

    # --- helpers ---------------------------------------------------------------------------
    def _recorded_hash(self, key: tuple[str, str]) -> str | None:
        entry = self._old.get(key)
        return None if entry is None else entry.sha256

    def _write(self, path: CanonicalPath, before: bytes | None, content: bytes) -> None:
        self._writes[str(path)] = PlannedWrite(
            path=path,
            kind="create" if before is None else "update",
            before_sha256=None if before is None else sha256_hex(before),
            after_sha256=sha256_hex(content),
            content=content,
        )

    def _propose(
        self, path: CanonicalPath, block: str | None, shown: bytes | None, wanted: bytes
    ) -> None:
        target = proposal_path(path, block)
        text = _unified_diff(path, shown, wanted).encode("utf-8")
        before = self._current.get(target)
        if before != text:
            self._write(target, before, text)
            last = self._writes[str(target)]
            self._writes[str(target)] = PlannedWrite(
                last.path, last.kind, last.before_sha256, last.after_sha256, last.content, True
            )

    def _record(
        self, wanted: Desired, key: tuple[str, str], state: FileState, content: bytes
    ) -> None:
        keeps_old = state in {
            FileState.USER_EDIT_ONLY,
            FileState.CONFLICT,
            FileState.NAME_COLLISION,
            FileState.SEEDED_KEEP,
            FileState.SEEDED_PROPOSAL,
        }
        if keeps_old:
            if key in self._old:
                self._after[key] = self._old[key]
            return
        lines = content.decode("utf-8").rstrip("\n").split("\n")
        block = (lines[0], lines[-1]) if wanted.block_name else None
        self._after[key] = Recorded(
            path=wanted.path,
            owner=wanted.owner,
            file_class=wanted.file_class,
            sha256=normalised_hash(content),
            block_name=wanted.block_name,
            block=block,
            inputs=wanted.inputs,
        )


_ACTIONS: dict[FileState, Action] = {
    FileState.UP_TO_DATE: Action.NOOP,
    FileState.NEW: Action.CREATE,
    FileState.SAFE_UPDATE: Action.UPDATE,
    FileState.USER_EDIT_ONLY: Action.NOOP,
    FileState.TAMPERED: Action.RESTORE,
    FileState.CONFLICT: Action.STOP,
    FileState.NAME_COLLISION: Action.STOP,
    FileState.ORPHAN_REMOVE: Action.DELETE,
    FileState.ORPHAN_REPORT: Action.NOOP,
    FileState.SEEDED_KEEP: Action.NOOP,
    FileState.SEEDED_PROPOSAL: Action.PROPOSE,
}


def _block_item(wanted: Desired) -> BlockItem:
    lines = wanted.content.decode("utf-8").rstrip("\n").split("\n")
    begin = lines[0]
    prefix = f"<!-- orqlet:begin {wanted.block_name}"
    info = begin[len(prefix) : -len(" -->")].strip()
    return BlockItem(wanted.block_name or "", info, "\n".join(lines[1:-1]))


def _unified_diff(path: CanonicalPath, shown: bytes | None, wanted: bytes) -> str:
    try:
        before = [] if shown is None else shown.decode("utf-8").splitlines()
        after = wanted.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return f"binary content differs for {path}\n"
    lines = difflib.unified_diff(
        before, after, fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="", n=3
    )
    return "\n".join(lines) + "\n"
