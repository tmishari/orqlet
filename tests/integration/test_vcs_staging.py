"""The staged snapshot, merge bases and type changes on real repositories."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.application.ports.vcs import VcsError
from tests.support.git import clean_environ, commit_file, git, make_repo

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]


def vcs_for(path: Path) -> GitVcs:
    return GitVcs(SubprocessRunner(), path, environ=clean_environ(path.parent))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = make_repo(tmp_path / "repo")
    commit_file(root, "a.txt", "one\n")
    return root


def test_the_staged_tree_is_the_snapshot_of_the_index_and_not_of_the_working_tree(
    repo: Path,
) -> None:
    vcs = vcs_for(repo)
    (repo / "a.txt").write_text("staged\n")
    git(repo, "add", "a.txt")
    (repo / "a.txt").write_text("working tree only\n")
    (repo / "new.txt").write_text("untracked\n")

    tree = vcs.staged_tree()

    assert tree == git(repo, "write-tree").strip()
    assert vcs.read_at(tree, "a.txt") == b"staged\n"
    assert [f.path for f in vcs.tree_at(tree)] == ["a.txt"]
    assert not vcs.has_revision(tree)  # a tree object names no commit


def test_the_diff_between_head_and_the_staged_tree_is_what_a_commit_would_hold(
    repo: Path,
) -> None:
    vcs = vcs_for(repo)
    (repo / "a.txt").write_text("changed\n")
    (repo / "b.txt").write_text("added\n")
    git(repo, "add", "-A")
    head = git(repo, "rev-parse", "HEAD").strip()

    changes = vcs.diff_tree(head, vcs.staged_tree())

    assert [(c.path, c.status) for c in changes] == [("a.txt", "modified"), ("b.txt", "added")]


def test_an_index_with_unmerged_entries_cannot_be_snapshotted(repo: Path) -> None:
    git(repo, "checkout", "--quiet", "-b", "other")
    commit_file(repo, "a.txt", "other side\n")
    git(repo, "checkout", "--quiet", "main")
    commit_file(repo, "a.txt", "main side\n")
    with contextlib.suppress(subprocess.CalledProcessError):
        git(repo, "merge", "other")  # stops on the conflict and leaves unmerged entries

    with pytest.raises(VcsError):
        vcs_for(repo).staged_tree()


def test_a_file_that_becomes_a_symbolic_link_is_a_type_change(repo: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("no symbolic links on this platform")
    before = git(repo, "rev-parse", "HEAD").strip()
    (repo / "a.txt").unlink()
    try:
        (repo / "a.txt").symlink_to("elsewhere")
    except OSError:
        pytest.skip("symbolic links are not allowed here")
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", "link")
    after = git(repo, "rev-parse", "HEAD").strip()

    (change,) = vcs_for(repo).diff_tree(before, after)

    assert (change.path, change.status, change.new_mode) == ("a.txt", "type-changed", "120000")


def test_a_diverged_history_has_one_merge_base_and_unrelated_histories_have_none(
    repo: Path,
) -> None:
    base = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "checkout", "--quiet", "-b", "feature")
    left = commit_file(repo, "left.txt", "l\n")
    git(repo, "checkout", "--quiet", "main")
    right = commit_file(repo, "right.txt", "r\n")
    git(repo, "checkout", "--quiet", "--orphan", "island")
    git(repo, "rm", "-rf", "--quiet", ".")
    island = commit_file(repo, "island.txt", "i\n")
    vcs = vcs_for(repo)

    assert vcs.merge_bases(left, right) == (base,)
    assert vcs.merge_bases(left, island) == ()


def test_a_criss_cross_history_has_two_merge_bases(repo: Path) -> None:
    git(repo, "checkout", "--quiet", "-b", "left")
    x1 = commit_file(repo, "x.txt", "x\n")
    git(repo, "checkout", "--quiet", "main")
    git(repo, "checkout", "--quiet", "-b", "right")
    y1 = commit_file(repo, "y.txt", "y\n")
    git(repo, "checkout", "--quiet", "left")
    git(repo, "merge", "--quiet", "--no-ff", "--no-edit", y1)  # M1 has parents x1 and y1
    git(repo, "checkout", "--quiet", "right")
    git(repo, "merge", "--quiet", "--no-ff", "--no-edit", x1)  # M2 has parents y1 and x1
    m1 = git(repo, "rev-parse", "left").strip()
    m2 = git(repo, "rev-parse", "right").strip()

    assert vcs_for(repo).merge_bases(m1, m2) == tuple(sorted((x1, y1)))


def test_a_branch_name_resolves_to_the_commit_it_points_at(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "branch", "feature/x")

    vcs = vcs_for(repo)

    assert vcs.resolve("main") == head
    assert vcs.resolve("feature/x") == head
    assert vcs.resolve("nope") is None


def test_the_staged_patch_is_the_unified_diff_of_the_index_against_head(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD").strip()
    (repo / "a.txt").write_text("one\nstaged\n")
    git(repo, "add", "a.txt")
    vcs = vcs_for(repo)

    patch = vcs.diff_patch(head, vcs.staged_tree()).decode()

    assert "+staged" in patch
    assert patch.startswith("diff --git a/a.txt b/a.txt")
