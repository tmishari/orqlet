from __future__ import annotations

import re
from collections.abc import Sequence

from orqlet.application.ports.vcs import (
    CommitSummary,
    RepoState,
    TreeChange,
    TreeFile,
    VcsError,
    check_ref_name,
)
from orqlet.domain.digest import sha256_hex


class FakeVcs:
    """A repository described by plain data; enough to test code that only reads Git state."""

    def __init__(
        self,
        state: RepoState = RepoState.NOT_A_REPOSITORY,
        *,
        branch: str | None = None,
        tracked: tuple[str, ...] = (),
        committed: dict[str, bytes] | None = None,
        commits: tuple[CommitSummary, ...] = (),
        remotes: tuple[str, ...] = (),
        staged: bool = False,
        ignored: tuple[str, ...] = (),
        revisions: dict[str, dict[str, bytes]] | None = None,
        modes: dict[tuple[str, str], str] | None = None,
        merge_bases: dict[tuple[str, str], tuple[str, ...]] | None = None,
        staged_tree: tuple[str, dict[str, bytes]] | None = None,
        refs: dict[str, str] | None = None,
    ) -> None:
        self._state = state
        self._branch = branch
        self._tracked = tracked
        self._committed = dict(committed or {})
        self._commits = commits
        self._remotes = remotes
        self._staged = staged
        self._ignored = frozenset(ignored)
        self._revisions = {name: dict(files) for name, files in (revisions or {}).items()}
        self._modes = dict(modes or {})  # (revision, path) -> Git mode other than 100644
        self._merge_bases = dict(merge_bases or {})
        self._refs = dict(refs or {})
        self._trees: dict[str, dict[str, bytes]] = {}  # tree object ids, never commits
        self._staged_tree = None if staged_tree is None else staged_tree[0]
        if staged_tree is not None:
            self._trees[staged_tree[0]] = dict(staged_tree[1])

    def state(self) -> RepoState:
        return self._state

    def head_commit(self) -> str | None:
        return self._commits[0].commit_id if self._commits else None

    def current_branch(self) -> str | None:
        return self._branch

    def tracked_files(self) -> tuple[str, ...]:
        return tuple(sorted(self._tracked))

    def read_committed(self, path: str) -> bytes | None:
        return self._committed.get(path)

    def _files_at(self, revision: str) -> dict[str, bytes] | None:
        if not re.fullmatch(r"HEAD|[0-9a-f]{40}|[0-9a-f]{64}", revision):
            raise VcsError(f"not an accepted revision: {revision!r}")
        if revision in self._revisions:
            return self._revisions[revision]
        if revision in self._trees:
            return self._trees[revision]
        if revision == "HEAD" and self.head_commit() is not None:
            return self._committed  # the content of HEAD, as given to the fake
        return None

    def has_revision(self, revision: str) -> bool:
        """True for a commit. A tree object id names no commit."""
        return revision not in self._trees and self._files_at(revision) is not None

    def read_at(self, revision: str, path: str) -> bytes | None:
        files = self._files_at(revision)
        return None if files is None else files.get(path)

    def read_many_at(self, revision: str, paths: Sequence[str]) -> dict[str, bytes | None]:
        return {path: self.read_at(revision, path) for path in paths}

    def tree_at(self, revision: str) -> tuple[TreeFile, ...]:
        files = self._files_at(revision) or {}
        named = self.head_commit() if revision == "HEAD" else revision
        return tuple(
            TreeFile(
                path,
                self._modes.get((named or revision, path), "100644"),
                sha256_hex(files[path])[:40],
            )
            for path in sorted(files)
        )

    def merge_bases(self, first: str, second: str) -> tuple[str, ...]:
        for revision in (first, second):
            self._files_at(revision)  # refuses anything but HEAD or a full object id
        found = self._merge_bases.get((first, second)) or self._merge_bases.get((second, first))
        return tuple(sorted(found or ()))

    def diff_tree(self, base: str, head: str) -> tuple[TreeChange, ...]:
        before = {file.path: file for file in self.tree_at(base)}
        after = {file.path: file for file in self.tree_at(head)}
        changes = []
        for path in sorted(before.keys() | after.keys()):
            old, new = before.get(path), after.get(path)
            if old is not None and new is not None and (old.mode, old.oid) == (new.mode, new.oid):
                continue
            if old is None and new is not None:
                status = "added"
            elif old is not None and new is None:
                status = "deleted"
            elif old is not None and new is not None and old.mode != new.mode:
                status = "type-changed" if old.mode[:2] != new.mode[:2] else "modified"
            else:
                status = "modified"
            changes.append(
                TreeChange(
                    path=path,
                    status=status,
                    old_mode="000000" if old is None else old.mode,
                    new_mode="000000" if new is None else new.mode,
                    new_oid="0" * 40 if new is None else new.oid,
                )
            )
        return tuple(changes)

    def diff_patch(self, base: str, head: str) -> bytes:
        lines = [
            f"diff --git a/{c.path} b/{c.path}\n{c.status} {c.old_mode} {c.new_mode}"
            for c in self.diff_tree(base, head)
        ]
        return ("\n".join(lines) + "\n").encode() if lines else b""

    def resolve(self, ref: str) -> str | None:
        check_ref_name(ref)
        return self._refs.get(ref)

    def staged_tree(self) -> str:
        if self._staged_tree is None:
            raise VcsError("the index has unmerged entries")
        return self._staged_tree

    def recent_commits(self, limit: int) -> tuple[CommitSummary, ...]:
        return self._commits[:limit]

    def remote_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._remotes))

    def has_staged_changes(self) -> bool:
        return self._staged

    def ignored(self, paths: Sequence[str]) -> frozenset[str]:
        return frozenset(path for path in paths if path in self._ignored)

    def init_repository(self, branch: str) -> None:
        if self._state is not RepoState.NOT_A_REPOSITORY:
            raise VcsError("a repository already exists")
        self._state = RepoState.UNBORN_EMPTY
        self._branch = branch
