"""`Vcs` implemented on the hardened Git runner."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from orqlet.adapters.git.git_runner import GitRunner
from orqlet.adapters.git.objects import check_revision, read_blobs
from orqlet.application.ports.process import ProcessRunner
from orqlet.application.ports.vcs import (
    CommitSummary,
    RepoState,
    TreeChange,
    TreeFile,
    VcsError,
    check_ref_name,
)

_MAX_HEAD_FILE_BYTES = 4096
_STATUS_NAMES = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "T": "type-changed",
}
_NOT_A_REPOSITORY = "not a git repository"


class GitVcs:
    def __init__(
        self, process: ProcessRunner, root: Path, *, environ: Mapping[str, str] | None = None
    ) -> None:
        self._root = root.resolve(strict=True)
        self._git = GitRunner(process, str(self._root), environ=environ)
        # Objects named by a full id never change, so one command line may remember what it asked.
        self._trees: dict[str, tuple[TreeFile, ...]] = {}
        self._commits: dict[str, bool] = {}

    def state(self) -> RepoState:
        top = self._git.run("rev-parse", "--show-toplevel", accept=(0, 128))
        if top.returncode == 128:
            message = top.stderr.decode("utf-8", errors="replace")
            if _NOT_A_REPOSITORY in message:
                return RepoState.NOT_A_REPOSITORY
            raise VcsError(f"git cannot read this repository: {message.strip().splitlines()[0]}")
        if not self._same_directory(top.stdout.decode("utf-8").strip()):
            return RepoState.NESTED
        if self.head_commit() is not None:
            return RepoState.HAS_COMMITS
        refs = self._git.run("for-each-ref", "--count=1", "--format=%(refname)")
        files = self._git.run("ls-files", "-z", "--cached", "--others", "--exclude-standard")
        if refs.stdout.strip() or files.stdout:
            return RepoState.UNBORN_NONEMPTY
        return RepoState.UNBORN_EMPTY

    def head_commit(self) -> str | None:
        result = self._git.run("rev-parse", "--verify", "--quiet", "HEAD", accept=(0, 1))
        return result.stdout.decode("ascii").strip() if result.returncode == 0 else None

    def current_branch(self) -> str | None:
        """Read the branch from the HEAD file, because `rev-parse` cannot name an unborn branch."""
        located = self._git.run("rev-parse", "--git-path", "HEAD").stdout.decode("utf-8").strip()
        head_file = Path(located) if os.path.isabs(located) else self._root / located
        try:
            with head_file.open("rb") as handle:
                content = handle.read(_MAX_HEAD_FILE_BYTES).decode("utf-8", errors="replace")
        except OSError:
            return None
        prefix = "ref: refs/heads/"
        if content.startswith(prefix):
            return content[len(prefix) :].strip() or None
        return None

    def tracked_files(self) -> tuple[str, ...]:
        output = self._git.run("ls-files", "-z", "--cached").stdout
        return tuple(sorted(set(self._decode_names(output))))

    def read_committed(self, path: str) -> bytes | None:
        if self.head_commit() is None:
            return None
        return read_blobs(self._git, "HEAD", [path])[path]

    def has_revision(self, revision: str) -> bool:
        check_revision(revision)
        if revision in self._commits:
            return self._commits[revision]
        result = self._git.run(
            "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}", accept=(0, 1)
        )
        found = result.returncode == 0
        if revision != "HEAD":
            self._commits[revision] = found
        return found

    def read_at(self, revision: str, path: str) -> bytes | None:
        return read_blobs(self._git, revision, [path])[path]

    def read_many_at(self, revision: str, paths: Sequence[str]) -> dict[str, bytes | None]:
        return read_blobs(self._git, revision, list(paths))

    def tree_at(self, revision: str) -> tuple[TreeFile, ...]:
        """`ls-tree -r -z`: each entry is `mode type oid TAB path`. Only blobs and gitlinks."""
        check_revision(revision)
        if revision in self._trees:
            return self._trees[revision]
        shown = self._git.run(
            "rev-parse", "--verify", "--quiet", f"{revision}^{{tree}}", accept=(0, 1)
        )
        if shown.returncode != 0:
            return ()
        output = self._git.run("ls-tree", "-r", "-z", revision).stdout
        files = []
        for raw in output.split(b"\0"):
            if not raw:
                continue
            meta, separator, name = raw.partition(b"\t")
            fields = meta.split(b" ")
            if not separator or len(fields) != 3:
                raise VcsError("unexpected git ls-tree output")
            files.append(
                TreeFile(
                    self._decode_names(name)[0],
                    fields[0].decode("ascii"),
                    fields[2].decode("ascii"),
                )
            )
        listed = tuple(sorted(files, key=lambda file: file.path))
        if revision != "HEAD":
            self._trees[revision] = listed
        return listed

    def merge_bases(self, first: str, second: str) -> tuple[str, ...]:
        check_revision(first)
        check_revision(second)
        result = self._git.run("merge-base", "--all", first, second, accept=(0, 1))
        return tuple(sorted(result.stdout.decode("ascii").split()))

    def diff_tree(self, base: str, head: str) -> tuple[TreeChange, ...]:
        """`diff-tree -r -z --raw`: records of `:old new old-oid new-oid status NUL path NUL`."""
        check_revision(base)
        check_revision(head)
        output = self._git.run("diff-tree", "-r", "-z", "--raw", "--no-renames", base, head).stdout
        tokens = output.split(b"\0")
        changes = []
        for meta, name in zip(tokens[0::2], tokens[1::2], strict=False):
            fields = meta.decode("ascii").removeprefix(":").split(" ")
            if len(fields) != 5 or fields[4] not in _STATUS_NAMES:
                raise VcsError("unexpected git diff-tree output")
            changes.append(
                TreeChange(
                    path=self._decode_names(name)[0],
                    status=_STATUS_NAMES[fields[4]],
                    old_mode=fields[0],
                    new_mode=fields[1],
                    new_oid=fields[3],
                )
            )
        return tuple(sorted(changes, key=lambda change: change.path))

    def diff_patch(self, base: str, head: str) -> bytes:
        check_revision(base)
        check_revision(head)
        return self._git.run("diff-tree", "-r", "-p", "--no-renames", base, head).stdout

    def resolve(self, ref: str) -> str | None:
        check_ref_name(ref)
        result = self._git.run(
            "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", accept=(0, 1)
        )
        return result.stdout.decode("ascii").strip() if result.returncode == 0 else None

    def staged_tree(self) -> str:
        """`write-tree` fails on unmerged entries, so a half-merged index is never reviewed."""
        return self._git.run("write-tree").stdout.decode("ascii").strip()

    def recent_commits(self, limit: int) -> tuple[CommitSummary, ...]:
        if limit < 1 or self.head_commit() is None:
            return ()
        listed = self._git.run("rev-list", f"--max-count={limit}", "HEAD").stdout
        summaries: list[CommitSummary] = []
        for commit_id in listed.decode("ascii").split():
            raw = self._git.run("cat-file", "commit", commit_id).stdout
            message = raw.decode("utf-8", errors="replace").partition("\n\n")[2]
            summaries.append(CommitSummary(commit_id, message.splitlines()[0] if message else ""))
        return tuple(summaries)

    def remote_names(self) -> tuple[str, ...]:
        refs = self._git.run("for-each-ref", "--format=%(refname)", "refs/remotes").stdout
        names = {
            line.split("/")[2]
            for line in refs.decode("utf-8", errors="replace").splitlines()
            if line.count("/") >= 3
        }
        return tuple(sorted(names))

    def has_staged_changes(self) -> bool:
        if self.head_commit() is None:
            return bool(self._git.run("ls-files", "-z", "--cached").stdout)
        result = self._git.run("diff-index", "--cached", "--quiet", "HEAD", accept=(0, 1))
        return result.returncode == 1

    def ignored(self, paths: Sequence[str]) -> frozenset[str]:
        """Ask Git which of `paths` match an ignore rule. Names go in on stdin, never as options.

        `check-ignore` reads ignore files only; it runs no configured program. Tracked files are
        not reported, because Git does not ignore a file it already tracks.
        """
        wanted = [path for path in paths if path and "\0" not in path and "\n" not in path]
        if not wanted:
            return frozenset()
        payload = b"\0".join(path.encode("utf-8") for path in wanted) + b"\0"
        result = self._git.run("check-ignore", "-z", "--stdin", stdin=payload, accept=(0, 1))
        return frozenset(self._decode_names(result.stdout))

    def init_repository(self, branch: str) -> None:
        if self.state() is not RepoState.NOT_A_REPOSITORY:
            raise VcsError("a repository already exists here or above")
        self._git.init_repository(branch)

    # --- internals -----------------------------------------------------------------------
    def _same_directory(self, reported: str) -> bool:
        return os.path.normcase(os.path.realpath(reported)) == os.path.normcase(str(self._root))

    @staticmethod
    def _decode_names(output: bytes) -> list[str]:
        names: list[str] = []
        for raw in output.split(b"\0"):
            if not raw:
                continue
            try:
                names.append(raw.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise VcsError("the repository holds a file name that is not valid UTF-8") from exc
        return names
