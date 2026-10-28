"""`Vcs.commit_subjects`: one suite for the fake and for real Git (task team-conventions-resources,
phase P-7).

Every test cites its `expected_behavior_source`. ADR-003 is the file `adr-003-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-6 are the acceptance criteria of phase P-7 in
docs/design/team-conventions-resources/plan.yaml. "The interface decision" is the reading of the
plan author that the Tester of phase P-7 was given, because the ADR does not spell it out:
`Vcs.commit_subjects(base, head)` takes `HEAD` or a full 40 or 64 hex commit id (anything else is a
`VcsError`, as `check_revision` does), returns the commits of `base..head` (reachable from head, not
from base) newest first, at most 201, each subject being the first line of the message cut at 1024
characters; an empty range gives `()`; an id that names no commit is a `VcsError`. `GitVcs` runs
only `rev-list` (one process) and `cat-file --batch` (one process) with ids only, and the Git
allow-list does not change. The fake takes `ranges=` and applies the same limits.

These tests were written first, by the Tester of phase P-7, before `commit_subjects` existed in the
port or in `GitVcs`.

Behaviour that the design leaves open is deliberately not pinned here:
- whether the cut at 1 KiB counts characters or bytes of a subject that is not ASCII (the ADR says
  "1 KiB", the interface decision says "1024 characters"): only ASCII subjects are cut here;
- the order of commits of a range that has merges (Git orders them by date, and the test commits
  share one second): only linear ranges, and ranges of one commit, are compared;
- how a message that is not valid UTF-8 is decoded;
- the exact Git command line (`base..head`, `^base head`, `--max-count`) and the text of a
  `VcsError` from Git;
- what the fake does with the literal `HEAD` (the use case resolves it to an id first); only real
  Git is asked about `HEAD`.
"""

from __future__ import annotations

import inspect
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from orqlet.adapters.git.git_runner import ALLOWED_SUBCOMMANDS
from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.application.ports.process import (
    OutputLimitExceeded,
    ProcessResult,
    ProcessTimeout,
)
from orqlet.application.ports.vcs import CommitSummary, RepoState, Vcs, VcsError
from tests.fakes.vcs import FakeVcs
from tests.support.git import clean_environ, commit_file, git, make_repo

pytestmark = pytest.mark.contract

UNKNOWN_SHA1 = "f" * 40
UNKNOWN_SHA256 = "e" * 64
ROOT = "chore: root"
# `git -c core.fsmonitor=false -c core.hooksPath= <subcommand> ...`: the subcommand is argv[5].
SUBCOMMAND_AT = 5
HEX_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
# What a revision argument of `rev-list` may look like when only ids are used.
ID_ONLY_ARGUMENT = re.compile(
    r"\^?(?:HEAD|[0-9a-f]{40}|[0-9a-f]{64})(?:\.\.(?:HEAD|[0-9a-f]{40}|[0-9a-f]{64}))?"
)


@dataclass(frozen=True)
class Commit:
    """One commit to build: its whole message and the commit it follows."""

    message: str
    parent: int | None = None  # an index in the chain; None: the commit before this one

    @property
    def expected(self) -> str:
        """What `commit_subjects` reports when the subject is not cut: the first line."""
        return self.message.split("\n", 1)[0]


def chain_of(*specs: str | Commit) -> list[Commit]:
    """A root commit, which no range lists, followed by the commits under test."""
    return [Commit(ROOT), *(Commit(spec) if isinstance(spec, str) else spec for spec in specs)]


class RecordingProcess:
    """The real process runner, with a record of every command line and every input."""

    def __init__(self) -> None:
        self._real = SubprocessRunner()
        self.calls: list[tuple[tuple[str, ...], bytes | None]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str,
        env: Mapping[str, str],
        timeout_seconds: float,
        max_output_bytes: int,
        stdin: bytes | None = None,
    ) -> ProcessResult:
        self.calls.append((tuple(argv), stdin))
        return self._real.run(
            argv,
            cwd=cwd,
            env=env,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            stdin=stdin,
        )

    @property
    def subcommands(self) -> list[str]:
        return [argv[SUBCOMMAND_AT] for argv, _ in self.calls]


@dataclass
class Chain:
    vcs: Vcs
    ids: tuple[str, ...]  # the commits in the order they were built; ids[0] is the root
    subjects: tuple[str, ...]  # what each commit must report
    process: RecordingProcess | None = None

    def listing(self, *indexes: int) -> tuple[CommitSummary, ...]:
        return tuple(CommitSummary(self.ids[i], self.subjects[i]) for i in indexes)

    def newest_first(self, base: int, head: int) -> tuple[CommitSummary, ...]:
        """The commits after `base` up to `head` of a linear chain, newest first."""
        return self.listing(*range(head, base, -1))


# --- the two builders -----------------------------------------------------------------------------


def _ancestors(commits: Sequence[Commit], index: int) -> set[int]:
    found: set[int] = set()
    pending = [index]
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        if current > 0:
            parent = commits[current].parent
            pending.append(current - 1 if parent is None else parent)
    return found


def fake_chain(_tmp: Path, commits: Sequence[Commit]) -> Chain:
    ids = tuple(f"{index + 1:040x}" for index in range(len(commits)))
    summaries = [
        CommitSummary(ids[i], commits[i].message.split("\n", 1)[0]) for i in range(len(ids))
    ]
    reachable = [_ancestors(commits, i) for i in range(len(ids))]
    ranges = {
        (ids[base], ids[head]): tuple(
            summaries[i] for i in sorted(reachable[head] - reachable[base], reverse=True)
        )
        for base in range(min(3, len(ids)))
        for head in range(len(ids))
        if base != head
    }
    vcs = FakeVcs(
        RepoState.HAS_COMMITS,
        commits=tuple(reversed(summaries)),
        ranges=ranges,
    )
    return Chain(vcs, ids, tuple(c.expected for c in commits))


def _commit_tree(repo: Path, tree: str, parent: str, message: str, environ: dict[str, str]) -> str:
    body = (message + "\n").encode("utf-8") if message else b""
    result = subprocess.run(
        ["git", "commit-tree", tree, "-p", parent, "-F", "-"],
        cwd=repo,
        env=environ,
        input=body,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("ascii").strip()


def git_chain(tmp: Path, commits: Sequence[Commit]) -> Chain:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    repo = make_repo(tmp / "repo")
    environ = clean_environ(tmp)
    root = commit_file(repo, "root.txt", "root\n", commits[0].message)
    tree = git(repo, "rev-parse", f"{root}^{{tree}}").strip()
    ids = [root]
    for index, item in enumerate(commits[1:], start=1):
        parent = ids[index - 1 if item.parent is None else item.parent]
        ids.append(_commit_tree(repo, tree, parent, item.message, environ))
    git(repo, "update-ref", "refs/heads/main", ids[-1])
    process = RecordingProcess()
    vcs = GitVcs(process, repo, environ=environ)
    return Chain(vcs, tuple(ids), tuple(c.expected for c in commits), process)


BUILDERS: dict[str, Callable[[Path, Sequence[Commit]], Chain]] = {
    "fake": fake_chain,
    "git": git_chain,
}


@pytest.fixture(params=sorted(BUILDERS))
def build(request: pytest.FixtureRequest, tmp_path: Path) -> Callable[[Sequence[Commit]], Chain]:
    builder = BUILDERS[request.param]
    return lambda commits: builder(tmp_path, commits)


# --- the range, its order and its limits ----------------------------------------------------------


def test_a_range_lists_its_commits_newest_first_and_leaves_out_the_base(
    build: Callable[[Sequence[Commit]], Chain],
) -> None:
    """AC-4. expected_behavior_source: the interface decision ("the commits of `base..head`,
    newest first") and ADR-003 decision 4 (the subject of every commit in `base..head`)."""
    chain = build(chain_of("feat: one", "fix(api): two", "docs: three"))

    found = chain.vcs.commit_subjects(chain.ids[0], chain.ids[3])

    assert found == chain.listing(3, 2, 1)


def test_a_range_starts_after_its_base(build: Callable[[Sequence[Commit]], Chain]) -> None:
    """AC-4. expected_behavior_source: the interface decision (reachable from head, not from
    base)."""
    chain = build(chain_of("feat: one", "fix: two", "docs: three"))

    assert chain.vcs.commit_subjects(chain.ids[1], chain.ids[3]) == chain.listing(3, 2)
    assert chain.vcs.commit_subjects(chain.ids[2], chain.ids[3]) == chain.listing(3)


def test_a_commit_that_the_base_reaches_is_not_listed_when_the_histories_diverge(
    build: Callable[[Sequence[Commit]], Chain],
) -> None:
    """AC-4. expected_behavior_source: the interface decision ("reachable from head, not from
    base"): the common parent of two branches belongs to neither range."""
    chain = build(chain_of("feat: left", Commit("fix: right", parent=0)))

    assert chain.vcs.commit_subjects(chain.ids[1], chain.ids[2]) == chain.listing(2)
    assert chain.vcs.commit_subjects(chain.ids[2], chain.ids[1]) == chain.listing(1)


def test_an_empty_range_gives_no_commits(build: Callable[[Sequence[Commit]], Chain]) -> None:
    """AC-4. expected_behavior_source: the interface decision ("An empty range gives `()`"):
    a commit with itself, and a base that is newer than the head."""
    chain = build(chain_of("feat: one", "fix: two"))

    assert chain.vcs.commit_subjects(chain.ids[2], chain.ids[2]) == ()
    assert chain.vcs.commit_subjects(chain.ids[2], chain.ids[1]) == ()


def test_the_subject_is_the_first_line_of_the_message(
    build: Callable[[Sequence[Commit]], Chain],
) -> None:
    """AC-4. expected_behavior_source: the interface decision ("each `subject` being the first
    line of the commit message")."""
    chain = build(chain_of("fix: the subject\n\nA body line.\nAnother body line.\n\nRefs: 1"))

    (found,) = chain.vcs.commit_subjects(chain.ids[0], chain.ids[1])

    assert found.subject == "fix: the subject"


def test_a_subject_is_cut_at_1024_characters(
    build: Callable[[Sequence[Commit]], Chain],
) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 4 ("A subject is cut at 1 KiB") and the
    interface decision (the first 1024 characters): 1500 characters are cut, 1025 are cut, 1024 are
    kept. ASCII only: the ADR and the interface decision differ on bytes and characters."""
    chain = build(chain_of("x" * 1500, "y" * 1025, "z" * 1024))

    found = chain.vcs.commit_subjects(chain.ids[0], chain.ids[3])

    assert [(item.commit_id, item.subject) for item in found] == [
        (chain.ids[3], "z" * 1024),
        (chain.ids[2], "y" * 1024),
        (chain.ids[1], "x" * 1024),
    ]


def test_an_empty_message_gives_an_empty_subject(
    build: Callable[[Sequence[Commit]], Chain],
) -> None:
    """AC-4. expected_behavior_source: the interface decision ("an empty message gives '' ")."""
    chain = build(chain_of("feat: before", "", "feat: after"))

    found = chain.vcs.commit_subjects(chain.ids[0], chain.ids[3])

    assert [item.subject for item in found] == ["feat: after", "", "feat: before"]


def test_a_subject_with_characters_beyond_ascii_is_kept(
    build: Callable[[Sequence[Commit]], Chain],
) -> None:
    """AC-4. expected_behavior_source: the interface decision (a subject that has a non-ASCII
    character) and ADR-003 decision 4 (`printable` escapes it on output, so the port must hand it
    over whole)."""
    subject = "feat: caf\u00e9 \u65e5\u672c\u8a9e \u2713 \U0001f680"
    chain = build(chain_of(subject))

    (found,) = chain.vcs.commit_subjects(chain.ids[0], chain.ids[1])

    assert found == CommitSummary(chain.ids[1], subject)


@pytest.mark.parametrize("separator", ["\x0b", "\x0c", "\x1c", "\x85", "\u2028"])
def test_a_control_character_stays_in_the_subject(
    build: Callable[[Sequence[Commit]], Chain], separator: str
) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 4 (a subject with a control character is
    refused by the shape check, so the port must hand it over whole up to the line feed) and
    rework round 1 of phase P-7 (both reviewers: `splitlines` cut the subject at these
    characters, so the check never saw what followed)."""
    subject = f"feat: before{separator}after"
    chain = build(chain_of(subject))

    (found,) = chain.vcs.commit_subjects(chain.ids[0], chain.ids[1])

    assert found == CommitSummary(chain.ids[1], subject)


def test_a_range_holds_at_most_201_commits_and_keeps_the_newest(
    build: Callable[[Sequence[Commit]], Chain],
) -> None:
    """AC-4. expected_behavior_source: the interface decision ("at most 201"; 201 commits give
    exactly 201 and 202 commits give 201) and ADR-003 Consequences (the port returns at most 201 so
    that the use case can see that the range is longer than the 200 that the check reads)."""
    chain = build(chain_of(*(f"chore: change {number}" for number in range(1, 203))))

    two_hundred = chain.vcs.commit_subjects(chain.ids[0], chain.ids[200])
    exactly = chain.vcs.commit_subjects(chain.ids[0], chain.ids[201])
    longer = chain.vcs.commit_subjects(chain.ids[0], chain.ids[202])

    assert len(two_hundred) == 200
    assert len(exactly) == 201
    assert exactly == chain.newest_first(0, 201)
    assert len(longer) == 201
    assert longer == chain.newest_first(1, 202)  # the oldest commit is the one that is dropped
    if chain.process is not None:  # a long range starts no more Git processes than a short one
        chain.process.calls.clear()
        chain.vcs.commit_subjects(chain.ids[0], chain.ids[3])
        calls_for_three = len(chain.process.calls)
        chain.process.calls.clear()
        chain.vcs.commit_subjects(chain.ids[0], chain.ids[202])
        assert len(chain.process.calls) == calls_for_three


# --- ids that name no commit, and revisions that are not ids --------------------------------------


@pytest.mark.parametrize("unknown", [UNKNOWN_SHA1, UNKNOWN_SHA256], ids=["sha1", "sha256"])
def test_an_id_that_names_no_commit_is_a_vcs_error(
    build: Callable[[Sequence[Commit]], Chain], unknown: str
) -> None:
    """AC-4. expected_behavior_source: the interface decision ("An id that names no commit is a
    VcsError") and plan P-7 AC-4 (a Git failure is never anything but a VcsError)."""
    chain = build(chain_of("feat: one"))

    with pytest.raises(VcsError):
        chain.vcs.commit_subjects(unknown, chain.ids[1])
    with pytest.raises(VcsError):
        chain.vcs.commit_subjects(chain.ids[0], unknown)
    with pytest.raises(VcsError):
        chain.vcs.commit_subjects(unknown, unknown)


@pytest.mark.parametrize(
    "revision", ["HEAD~1", "--all", "main", "abc123", "", "HEAD:root.txt", "a" * 39, "-x"]
)
def test_only_head_and_full_commit_ids_are_accepted(
    build: Callable[[Sequence[Commit]], Chain], revision: str
) -> None:
    """AC-4. expected_behavior_source: the interface decision (`HEAD` or a full 40 or 64 hex id;
    "anything else is a VcsError, as `check_revision` does") and ORQLET-SEC-001 (a name that could
    be an option or an expression never reaches a Git command)."""
    chain = build(chain_of("feat: one"))

    with pytest.raises(VcsError, match="accepted revision"):
        chain.vcs.commit_subjects(revision, chain.ids[1])
    with pytest.raises(VcsError, match="accepted revision"):
        chain.vcs.commit_subjects(chain.ids[0], revision)
    if chain.process is not None:
        assert chain.process.calls == []  # refused before any Git process was started


# --- the fake and the declarations ---------------------------------------------------------------


def test_the_fake_knows_every_id_that_its_data_names() -> None:
    """AC-4. expected_behavior_source: the interface decision (the fake raises VcsError when an id
    is not known to it; known = every commit_id in the values of `ranges` and in `commits`, every
    value of `refs`, every key of `revisions`, every key and member of `merge_bases`). Fake only."""
    in_commits, in_ranges, in_refs, in_revisions = "1" * 40, "2" * 40, "3" * 40, "4" * 40
    first_key, second_key, member = "5" * 40, "6" * 40, "7" * 40
    fake = FakeVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(in_commits, "feat: head"),),
        refs={"main": in_refs},
        revisions={in_revisions: {}},
        merge_bases={(first_key, second_key): (member,)},
        ranges={(in_refs, in_commits): (CommitSummary(in_ranges, "fix: inside"),)},
    )

    known = (in_commits, in_ranges, in_refs, in_revisions, first_key, second_key, member)
    for commit_id in known:
        assert fake.commit_subjects(commit_id, commit_id) == ()
    assert fake.commit_subjects(in_refs, in_commits) == (CommitSummary(in_ranges, "fix: inside"),)
    with pytest.raises(VcsError):
        fake.commit_subjects(UNKNOWN_SHA1, in_commits)


def test_the_port_and_the_adapter_declare_the_same_method() -> None:
    """AC-4. expected_behavior_source: EC-44 (`def commit_subjects(self, base: str, head: str) ->
    tuple[CommitSummary, ...]` on the port) and EC-45 (the same on `GitVcs`)."""
    for owner in (Vcs, GitVcs, FakeVcs):
        signature = inspect.signature(vars(owner)["commit_subjects"], eval_str=True)
        assert list(signature.parameters) == ["self", "base", "head"], owner
        assert signature.parameters["base"].annotation is str, owner
        assert signature.parameters["head"].annotation is str, owner
        assert signature.return_annotation == tuple[CommitSummary, ...], owner


# --- real Git only: HEAD, the processes it starts, the allow-list ---------------------------------


def test_head_names_the_tip_in_real_git(tmp_path: Path) -> None:
    """AC-4. expected_behavior_source: the interface decision (`base` and `head` are `HEAD` or a
    full id). Real Git only: what the fake does with the literal `HEAD` is not specified."""
    chain = git_chain(tmp_path, chain_of("feat: one", "fix: two"))

    assert chain.vcs.commit_subjects(chain.ids[0], "HEAD") == chain.listing(2, 1)
    assert chain.vcs.commit_subjects("HEAD", chain.ids[0]) == ()
    assert chain.vcs.commit_subjects("HEAD", "HEAD") == ()


def test_a_range_is_read_with_rev_list_and_cat_file_and_ids_only(tmp_path: Path) -> None:
    """AC-4. expected_behavior_source: the interface decision ("GitVcs uses only `rev-list` (one
    process) and `cat-file --batch` (one process) with ids only"), ADR-003 decision 4 ("`rev-list`
    and `cat-file` get ids only") and ORQLET-SEC-001."""
    chain = git_chain(tmp_path, chain_of("feat: one", "fix: two", "docs: three"))
    process = chain.process
    assert process is not None
    process.calls.clear()

    chain.vcs.commit_subjects(chain.ids[0], chain.ids[3])

    assert process.subcommands == ["rev-list", "cat-file"]
    (rev_list, _), (cat_file, cat_input) = process.calls
    assert any(arg.startswith("--batch") for arg in cat_file[SUBCOMMAND_AT + 1 :])
    revisions = [arg for arg in rev_list[SUBCOMMAND_AT + 1 :] if not arg.startswith("-")]
    assert revisions
    assert all(ID_ONLY_ARGUMENT.fullmatch(arg) for arg in revisions), revisions
    assert all(arg.startswith("-") for arg in cat_file[SUBCOMMAND_AT + 1 :])  # ids go in on stdin
    assert cat_input is not None
    assert all(HEX_ID.fullmatch(line) for line in cat_input.decode("ascii").splitlines())


def test_the_number_of_git_processes_does_not_grow_with_the_number_of_commits(
    tmp_path: Path,
) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 4 ("the whole range is read with a fixed
    number of Git processes") and the interface decision (compare 3 and 50 commits)."""
    chain = git_chain(tmp_path, chain_of(*(f"chore: change {number}" for number in range(1, 51))))
    process = chain.process
    assert process is not None

    process.calls.clear()
    three = chain.vcs.commit_subjects(chain.ids[0], chain.ids[3])
    calls_for_three = len(process.calls)
    process.calls.clear()
    fifty = chain.vcs.commit_subjects(chain.ids[0], chain.ids[50])
    calls_for_fifty = len(process.calls)

    assert (len(three), len(fifty)) == (3, 50)
    assert calls_for_three == calls_for_fifty
    assert set(process.subcommands) <= {"rev-list", "cat-file"}


def test_an_empty_range_starts_no_process_other_than_the_two_allowed_ones(tmp_path: Path) -> None:
    """AC-4. expected_behavior_source: the interface decision (only `rev-list` and `cat-file`)."""
    chain = git_chain(tmp_path, chain_of("feat: one"))
    process = chain.process
    assert process is not None
    process.calls.clear()

    assert chain.vcs.commit_subjects(chain.ids[1], chain.ids[1]) == ()

    assert set(process.subcommands) <= {"rev-list", "cat-file"}


def test_the_git_allow_list_is_unchanged() -> None:
    """AC-6. expected_behavior_source: plan P-7 AC-6 ("no new subcommand is added to the Git
    allow-list") and the interface decision (`ALLOWED_SUBCOMMANDS` must stay exactly as it is): a
    literal copy of the set at the base of this phase. It passes before the change as well."""
    assert (
        frozenset(
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
        == ALLOWED_SUBCOMMANDS
    )


# --- a Git failure is never anything but a VcsError ----------------------------------------------


class FailingProcess:
    """Answers the calls in order with a result or raises an exception; records nothing else."""

    def __init__(self, *steps: ProcessResult | Exception) -> None:
        self._steps = list(steps)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str,
        env: Mapping[str, str],
        timeout_seconds: float,
        max_output_bytes: int,
        stdin: bytes | None = None,
    ) -> ProcessResult:
        step = self._steps.pop(0) if self._steps else ProcessResult(tuple(argv), 0, b"", b"")
        if isinstance(step, Exception):
            raise step
        return step


A_REV_LIST = ProcessResult(("git",), 0, f"{'2' * 40}\n{'1' * 40}\n".encode("ascii"), b"")
A_FAILURE = ProcessResult(("git",), 128, b"", b"fatal: bad revision\n")
BASE_ID, HEAD_ID = "3" * 40, "4" * 40

FAILURES: dict[str, tuple[ProcessResult | Exception, ...]] = {
    "rev-list-fails": (A_FAILURE,),
    "rev-list-exceeds-its-time": (ProcessTimeout("too slow"),),
    "rev-list-exceeds-its-output": (OutputLimitExceeded("too much"),),
    "cat-file-fails": (A_REV_LIST, A_FAILURE),
    "cat-file-exceeds-its-time": (A_REV_LIST, ProcessTimeout("too slow")),
    "cat-file-exceeds-its-output": (A_REV_LIST, OutputLimitExceeded("too much")),
}


@pytest.mark.parametrize("name", list(FAILURES), ids=list(FAILURES))
def test_a_git_failure_or_a_limit_surfaces_as_a_vcs_error(tmp_path: Path, name: str) -> None:
    """AC-4. expected_behavior_source: plan P-7 AC-4 ("never lets a Git failure surface as anything
    but a VcsError"), ADR-003 decision 4 ("any Git call fails or exceeds the runner's output or
    time limits (`VcsError`)") and EC-45 (a Git failure or the runner's limit becomes a
    VcsError)."""
    vcs = GitVcs(FailingProcess(*FAILURES[name]), tmp_path, environ={"PATH": "/bin"})

    with pytest.raises(VcsError):
        vcs.commit_subjects(BASE_ID, HEAD_ID)
