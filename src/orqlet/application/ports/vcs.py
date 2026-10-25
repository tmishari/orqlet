"""Read access to version control, plus the one write Orqlet needs: creating a repository."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from orqlet.domain.errors import OrqletError


class RepoState(StrEnum):
    NOT_A_REPOSITORY = "not-a-repository"
    UNBORN_EMPTY = "unborn-empty"
    UNBORN_NONEMPTY = "unborn-nonempty"  # no commit at HEAD, but files or other refs exist
    HAS_COMMITS = "has-commits"
    NESTED = "inside-other-repository"  # the directory sits below a repository root


class VcsError(OrqletError):
    """A repository command failed or was refused by the allow-list."""


_REF_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@-]*")


def check_ref_name(ref: str) -> None:
    """Accept a plain branch, tag or remote branch name. Refuse what Git could read otherwise.

    A name that starts with a dash is an option, and `..`, `~`, `^`, `:` and `{` are revision
    expressions. Neither may reach a Git command as a name.
    """
    if not _REF_NAME.fullmatch(ref) or ".." in ref or ref.endswith((".lock", "/", ".")):
        raise VcsError(f"not an accepted ref name: {ref!r}")


@dataclass(frozen=True, slots=True)
class CommitSummary:
    commit_id: str
    subject: str


@dataclass(frozen=True, slots=True)
class TreeFile:
    """One tracked file in a commit's tree."""

    path: str
    mode: str  # the Git file mode: 100644, 100755, 120000 (symbolic link) or 160000 (gitlink)
    oid: str  # the object id of the content, so two trees can be compared without reading files


@dataclass(frozen=True, slots=True)
class TreeChange:
    """One path that differs between two trees. A rename is a deletion plus an addition."""

    path: str
    status: str  # added, modified, deleted or type-changed
    old_mode: str
    new_mode: str
    new_oid: str  # the object id on the new side; all zeros for a deletion


class Vcs(Protocol):
    def state(self) -> RepoState:
        """Classify the directory: no repository, unborn (empty or not) or with commits."""
        ...

    def head_commit(self) -> str | None:
        """The id of HEAD, or `None` on an unborn branch."""
        ...

    def current_branch(self) -> str | None:
        """The checked-out branch name, or `None` when detached or unknown."""
        ...

    def tracked_files(self) -> tuple[str, ...]:
        """Repository-relative names of tracked files, as raw text, sorted by code point."""
        ...

    def read_committed(self, path: str) -> bytes | None:
        """The content of `path` at HEAD, or `None` when it is not there."""
        ...

    def has_revision(self, revision: str) -> bool:
        """True when `revision` (`HEAD` or a full object id) names a commit that exists."""
        ...

    def read_at(self, revision: str, path: str) -> bytes | None:
        """The content of `path` at `revision`, or `None` when the file or the revision is missing.

        `revision` is `HEAD` or a full object id. Anything else is a `VcsError`.
        """
        ...

    def read_many_at(self, revision: str, paths: Sequence[str]) -> dict[str, bytes | None]:
        """`read_at` for many paths with one Git process. Missing paths map to `None`."""
        ...

    def tree_at(self, revision: str) -> tuple[TreeFile, ...]:
        """Every tracked file at a commit or a tree, sorted by path. Empty when it is missing."""
        ...

    def merge_bases(self, first: str, second: str) -> tuple[str, ...]:
        """Every best common ancestor of two commits. Empty when they share no history."""
        ...

    def diff_tree(self, base: str, head: str) -> tuple[TreeChange, ...]:
        """The paths that differ between two commits or trees, sorted by path. No renames."""
        ...

    def diff_patch(self, base: str, head: str) -> bytes:
        """The unified diff between two commits or trees. No external diff or text conversion."""
        ...

    def resolve(self, ref: str) -> str | None:
        """The commit id of a branch, tag or remote branch name; `None` when it names none.

        A name that could be read as an option or as a revision expression is a `VcsError`.
        """
        ...

    def staged_tree(self) -> str:
        """The tree object id of the index. Raises `VcsError` when there are unmerged entries."""
        ...

    def recent_commits(self, limit: int) -> tuple[CommitSummary, ...]:
        """Up to `limit` commits reachable from HEAD, newest first."""
        ...

    def remote_names(self) -> tuple[str, ...]:
        """Remotes that have remote-tracking refs, sorted by code point."""
        ...

    def has_staged_changes(self) -> bool:
        """True when the index differs from HEAD. The working tree is never compared."""
        ...

    def ignored(self, paths: Sequence[str]) -> frozenset[str]:
        """The subset of `paths` that Git would ignore, so a commit would not include them."""
        ...

    def init_repository(self, branch: str) -> None:
        """Create a repository whose first branch is `branch`. Refuses an existing one."""
        ...
