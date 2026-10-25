"""The only place that builds a `git` command line (ADR-003).

Every call starts with `git -c core.fsmonitor=false -c core.hooksPath=`, runs with a scrubbed
environment and may use only the allow-listed subcommands. Anything that executes configured
programs on a read (`status`, porcelain `diff`, `add`, `checkout`) is not on the list.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence

from orqlet.adapters.process.environment import scrubbed_environment
from orqlet.application.ports.process import ProcessError, ProcessResult, ProcessRunner
from orqlet.application.ports.vcs import VcsError

ALLOWED_SUBCOMMANDS = frozenset(
    {
        "rev-parse",
        "for-each-ref",
        "rev-list",
        "merge-base",
        "ls-files",
        "ls-tree",
        "cat-file",
        "diff-tree",
        "diff-index",
        "write-tree",
        "check-ignore",
    }
)
_DIFF_SUBCOMMANDS = frozenset({"diff-tree", "diff-index"})
# Options that make an allow-listed subcommand run a repository-configured program. Found by the
# hostile-configuration test: `diff-index HEAD` compares the working tree and so runs the
# `filter.*.clean` program on every modified file, and `ls-files --modified` does the same.
_FORBIDDEN_OPTIONS = {
    "ls-files": frozenset({"--modified", "--eol"}),
    "cat-file": frozenset({"--filters", "--textconv"}),
    "diff-tree": frozenset({"--ext-diff", "--textconv"}),
    "diff-index": frozenset({"--ext-diff", "--textconv"}),
}
_REQUIRED_OPTIONS = {"diff-index": "--cached"}  # compare the index with a tree, never the files
_GIT_EXTRA_ENVIRONMENT = {
    "LC_ALL": "C",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_PAGER": "cat",
    "GIT_OPTIONAL_LOCKS": "0",
}
_BASE_ARGS = ("git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=")


class GitRunner:
    def __init__(
        self,
        process: ProcessRunner,
        root: str,
        *,
        environ: Mapping[str, str] | None = None,
        timeout_seconds: float = 30.0,
        max_output_bytes: int = 16 * 1024 * 1024,
    ) -> None:
        self._process = process
        self._root = root
        self._env = scrubbed_environment(
            os.environ if environ is None else environ, _GIT_EXTRA_ENVIRONMENT
        )
        self._timeout = timeout_seconds
        self._max_output = max_output_bytes

    def run(
        self,
        *args: str,
        stdin: bytes | None = None,
        accept: Sequence[int] = (0,),
    ) -> ProcessResult:
        """Run one allow-listed subcommand. A return code outside `accept` is a `VcsError`."""
        if not args or args[0] not in ALLOWED_SUBCOMMANDS:
            raise VcsError(f"git subcommand is not allowed: {args[0] if args else '(none)'}")
        self._check_options(args)
        wanted = args
        if args[0] in _DIFF_SUBCOMMANDS:
            wanted = (args[0], "--no-ext-diff", "--no-textconv", *args[1:])
        return self._execute(wanted, stdin=stdin, accept=accept)

    @staticmethod
    def _check_options(args: Sequence[str]) -> None:
        subcommand = args[0]
        options = [arg for arg in args[1:] if arg.startswith("-")]
        if "--" in args[1:]:
            options = [arg for arg in args[1 : args.index("--", 1)] if arg.startswith("-")]
        forbidden = _FORBIDDEN_OPTIONS.get(subcommand, frozenset())
        for option in options:
            short_cluster_runs_filter = (
                subcommand == "ls-files"
                and not option.startswith("--")
                and re.fullmatch(r"-[A-Za-z]+", option) is not None
                and "m" in option
            )
            if option in forbidden or short_cluster_runs_filter:
                raise VcsError(f"git {subcommand} option is not allowed: {option}")
        required = _REQUIRED_OPTIONS.get(subcommand)
        if required is not None and required not in options:
            raise VcsError(f"git {subcommand} is not allowed without {required}")

    def init_repository(self, branch: str) -> None:
        """Create a repository. The branch name is checked with git itself and by two extra rules.

        `init` is not a read, so it is not on the allow-list; this method is its only caller.
        """
        if branch.startswith(("refs/", "-")) or branch == "@":
            raise VcsError(f"not a usable branch name: {branch!r}")
        check = self._execute(("check-ref-format", "--branch", branch), accept=(0, 1))
        if check.returncode != 0:
            raise VcsError(f"not a valid branch name: {branch!r}")
        self._execute(("init", "--quiet", f"--initial-branch={branch}"))

    def _execute(
        self, args: Sequence[str], *, stdin: bytes | None = None, accept: Sequence[int] = (0,)
    ) -> ProcessResult:
        try:
            result = self._process.run(
                (*_BASE_ARGS, *args),
                cwd=self._root,
                env=self._env,
                timeout_seconds=self._timeout,
                max_output_bytes=self._max_output,
                stdin=stdin,
            )
        except ProcessError as exc:
            raise VcsError(f"git {args[0]}: {exc}") from exc
        if result.returncode not in accept:
            detail = result.stderr.decode("utf-8", errors="replace").strip().splitlines()
            raise VcsError(
                f"git {args[0]} failed ({result.returncode}): {detail[0] if detail else ''}"
            )
        return result
