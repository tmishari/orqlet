"""Worktree information from real Git: a linked worktree and a home work tree (P-4 AC-7)."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.interface.cli.app import app
from tests.support.git import commit_file, git, make_repo

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()


@pytest.fixture(autouse=True)
def _safe_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Q-73 skips Git when PATH searches an unsafe element, so the runner's own PATH is not used."""
    git = shutil.which("git")
    if git is not None:
        monkeypatch.setenv("PATH", os.path.dirname(git))


def status_data(root: Path) -> dict[str, object]:
    result = RUNNER.invoke(app, ["status", "--root", str(root), "--json"])
    assert result.exit_code == 0, result.stdout
    data: dict[str, object] = json.loads(result.stdout)["data"]
    return data


def test_a_main_checkout_is_not_linked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "main")
    commit_file(repo, "a.txt", "a\n")
    (repo / "sub").mkdir()

    worktree = GitVcs(SubprocessRunner(), repo / "sub").worktree()

    assert worktree is not None
    assert worktree.top_level == os.path.realpath(repo)
    assert not worktree.linked


def test_a_linked_worktree_is_reported(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "main")
    commit_file(repo, "a.txt", "a\n")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--quiet", str(linked), "-b", "side")

    worktree = GitVcs(SubprocessRunner(), linked).worktree()
    data = status_data(linked)

    assert worktree is not None
    assert worktree.linked
    assert worktree.top_level == os.path.realpath(linked)
    assert data["location"] == "linked-worktree"
    assert data["next"] == "refuse-linked-worktree"


def test_a_home_that_is_a_work_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = make_repo(tmp_path / "dotfiles-home")
    commit_file(home, ".profile", "export A=1\n")
    project = home / "work" / "project"
    project.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    data = status_data(project)

    assert data["location"] == "home-is-work-tree"
    assert data["next"] == "refuse-home-is-work-tree"


def test_outside_a_repository_there_is_no_worktree(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    assert GitVcs(SubprocessRunner(), plain).worktree() is None


def test_a_git_failure_gives_a_null_top_level(tmp_path: Path) -> None:
    """Inside the `.git` folder `--show-toplevel` fails: no top level, and the check did not run."""
    repo = make_repo(tmp_path / "main")
    commit_file(repo, "a.txt", "a\n")

    result = RUNNER.invoke(app, ["status", "--root", str(repo / ".git"), "--json"])
    envelope = json.loads(result.stdout)

    assert result.exit_code == 5
    assert envelope["data"]["top_level"] is None
    assert envelope["not_run"]


@pytest.mark.skipif(os.name == "nt", reason="a line feed cannot be part of a Windows file name")
def test_a_top_level_with_a_line_feed_is_refused(tmp_path: Path) -> None:
    """Code review of P-4, round 2: the extra line is refused, never taken for another field."""
    repo = make_repo(tmp_path / "a\nb")
    commit_file(repo, "a.txt", "a\n")

    result = RUNNER.invoke(app, ["status", "--root", str(repo), "--json"])
    envelope = json.loads(result.stdout)

    assert result.exit_code == 5
    assert envelope["data"]["top_level"] is None
    assert envelope["not_run"]
