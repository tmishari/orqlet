"""`GitVcs` against real temporary repositories."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from orqlet.adapters.git.git_runner import GitRunner
from orqlet.adapters.git.objects import read_blobs
from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.application.ports.vcs import RepoState, VcsError
from tests.support.git import clean_environ, commit_file, git, make_repo

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]


def vcs_for(path: Path) -> GitVcs:
    return GitVcs(SubprocessRunner(), path, environ=clean_environ(path.parent))


@pytest.fixture
def work(tmp_path: Path) -> Path:
    directory = tmp_path / "work"
    directory.mkdir()
    return directory


def test_a_plain_directory_is_not_a_repository(work: Path) -> None:
    assert vcs_for(work).state() is RepoState.NOT_A_REPOSITORY


def test_a_fresh_repository_is_unborn_and_empty(work: Path) -> None:
    make_repo(work, "trunk")

    vcs = vcs_for(work)

    assert vcs.state() is RepoState.UNBORN_EMPTY
    assert vcs.head_commit() is None
    assert vcs.current_branch() == "trunk"
    assert vcs.recent_commits(5) == ()
    assert vcs.read_committed("a.txt") is None


def test_files_before_the_first_commit_make_it_unborn_nonempty(work: Path) -> None:
    make_repo(work)
    (work / "notes.txt").write_text("x")

    assert vcs_for(work).state() is RepoState.UNBORN_NONEMPTY


def test_an_orphan_head_with_other_branches_is_unborn_nonempty(work: Path) -> None:
    make_repo(work, "main")
    commit_file(work, "a.txt", "a")
    git(work, "checkout", "--quiet", "--orphan", "fresh")
    git(work, "rm", "-rf", "--quiet", ".")

    vcs = vcs_for(work)

    assert vcs.state() is RepoState.UNBORN_NONEMPTY
    assert vcs.current_branch() == "fresh"


def test_a_repository_with_commits(work: Path) -> None:
    make_repo(work)
    head = commit_file(work, "src/a.txt", "hello\n", "feat: first")
    commit_file(work, "b.txt", "b", "fix: second")

    vcs = vcs_for(work)

    assert vcs.state() is RepoState.HAS_COMMITS
    assert vcs.head_commit() == git(work, "rev-parse", "HEAD").strip()
    assert vcs.current_branch() == "main"
    assert vcs.tracked_files() == ("b.txt", "src/a.txt")
    assert vcs.read_committed("src/a.txt") == b"hello\n"
    assert vcs.read_committed("missing.txt") is None
    assert [c.subject for c in vcs.recent_commits(5)] == ["fix: second", "feat: first"]
    assert vcs.recent_commits(1)[0].commit_id != head


def test_a_detached_head_has_no_branch(work: Path) -> None:
    make_repo(work)
    head = commit_file(work, "a.txt", "a")
    git(work, "checkout", "--quiet", "--detach", head)

    assert vcs_for(work).current_branch() is None


def test_a_subdirectory_of_a_repository_is_nested(work: Path) -> None:
    make_repo(work)
    commit_file(work, "a.txt", "a")
    inner = work / "packages" / "app"
    inner.mkdir(parents=True)

    assert vcs_for(inner).state() is RepoState.NESTED


def test_staged_changes_are_seen_but_working_tree_edits_are_not(work: Path) -> None:
    make_repo(work)
    commit_file(work, "a.txt", "one")
    vcs = vcs_for(work)

    (work / "a.txt").write_text("two")
    assert vcs.has_staged_changes() is False

    git(work, "add", "a.txt")
    assert vcs.has_staged_changes() is True


def test_an_unborn_repository_with_a_staged_file_has_staged_changes(work: Path) -> None:
    make_repo(work)
    (work / "a.txt").write_text("x")
    git(work, "add", "a.txt")

    assert vcs_for(work).has_staged_changes() is True


def test_remote_names_come_from_remote_tracking_refs(work: Path) -> None:
    make_repo(work)
    head = commit_file(work, "a.txt", "a")
    git(work, "update-ref", "refs/remotes/origin/main", head)
    git(work, "update-ref", "refs/remotes/upstream/dev", head)

    assert vcs_for(work).remote_names() == ("origin", "upstream")


def test_init_repository_creates_a_repository_with_the_named_branch(work: Path) -> None:
    vcs = vcs_for(work)

    vcs.init_repository("trunk")

    assert vcs.state() is RepoState.UNBORN_EMPTY
    assert vcs.current_branch() == "trunk"


def test_init_repository_refuses_an_existing_repository(work: Path) -> None:
    make_repo(work)

    with pytest.raises(VcsError, match="already exists"):
        vcs_for(work).init_repository("main")


def test_init_repository_refuses_a_directory_inside_a_repository(work: Path) -> None:
    make_repo(work)
    inner = work / "sub"
    inner.mkdir()

    with pytest.raises(VcsError, match="already exists"):
        vcs_for(inner).init_repository("main")


@pytest.mark.parametrize("branch", ["refs/heads/x", "@", "a..b", "-x", "has space", "end."])
def test_init_repository_refuses_bad_branch_names(work: Path, branch: str) -> None:
    with pytest.raises(VcsError):
        vcs_for(work).init_repository(branch)

    assert vcs_for(work).state() is RepoState.NOT_A_REPOSITORY


@pytest.mark.skipif(sys.platform == "win32", reason="byte-string arguments are POSIX only")
def test_a_file_name_that_is_not_utf8_is_reported_not_guessed(work: Path) -> None:
    make_repo(work)
    environ = clean_environ(work.parent)
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=work,
        input=b"",
        env=environ,
        capture_output=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        [b"git", b"update-index", b"--add", b"--cacheinfo", b"100644," + blob + b",bad\xff.txt"],
        cwd=work,
        env=environ,
        capture_output=True,
        check=True,
    )

    with pytest.raises(VcsError, match="UTF-8"):
        vcs_for(work).tracked_files()


def test_read_blobs_returns_none_for_missing_and_for_directories(work: Path) -> None:
    make_repo(work)
    head = commit_file(work, "dir/a.txt", "a\nb\n")
    runner = GitRunner(SubprocessRunner(), str(work), environ=clean_environ(work.parent))

    found = read_blobs(runner, head, ["dir/a.txt", "dir", "nope.txt"])

    assert found == {"dir/a.txt": b"a\nb\n", "dir": None, "nope.txt": None}


def test_read_blobs_handles_binary_content_with_embedded_newlines(work: Path) -> None:
    make_repo(work)
    (work / "bin").write_bytes(b"\x00\n\xff\n\n")
    git(work, "add", "bin")
    git(work, "commit", "--quiet", "-m", "bin")
    runner = GitRunner(SubprocessRunner(), str(work), environ=clean_environ(work.parent))

    assert read_blobs(runner, "HEAD", ["bin"]) == {"bin": b"\x00\n\xff\n\n"}


@pytest.mark.parametrize("revision", ["main", "HEAD~1", "HEAD:x", "--all", "abc"])
def test_read_blobs_accepts_only_head_or_a_full_object_id(work: Path, revision: str) -> None:
    make_repo(work)
    runner = GitRunner(SubprocessRunner(), str(work), environ=clean_environ(work.parent))

    with pytest.raises(VcsError, match="revision"):
        read_blobs(runner, revision, ["a"])


def test_read_blobs_refuses_a_path_with_a_line_break(work: Path) -> None:
    make_repo(work)
    runner = GitRunner(SubprocessRunner(), str(work), environ=clean_environ(work.parent))

    with pytest.raises(VcsError, match="line break"):
        read_blobs(runner, "HEAD", ["a\nHEAD:b"])


def test_ignored_reports_files_that_a_gitignore_rule_matches(work: Path) -> None:
    make_repo(work)
    commit_file(work, ".gitignore", ".claude/*\n!.claude/settings.json\n*.log\n")

    found = vcs_for(work).ignored(
        [".claude/CLAUDE.md", ".claude/settings.json", "src/app.py", "build.log", "has space.log"]
    )

    assert found == {".claude/CLAUDE.md", "build.log", "has space.log"}


def test_a_tracked_file_is_never_reported_as_ignored(work: Path) -> None:
    make_repo(work)
    commit_file(work, ".gitignore", "*.log\n")
    git(work, "add", "-f", "-A")
    (work / "kept.log").write_text("x")
    git(work, "add", "-f", "kept.log")

    assert vcs_for(work).ignored(["kept.log"]) == frozenset()


def test_ignored_with_no_names_or_hostile_names_runs_nothing_dangerous(work: Path) -> None:
    make_repo(work)
    vcs = vcs_for(work)

    assert vcs.ignored([]) == frozenset()
    assert vcs.ignored(["a\nb", "", "c\0d"]) == frozenset()
    assert vcs.ignored(["--help", "-rf"]) == frozenset()  # names are data, never options
