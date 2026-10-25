"""Reading files and trees at a revision: one suite for the fake and for real Git (A-3)."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.application.ports.vcs import CommitSummary, RepoState, Vcs, VcsError
from tests.fakes.vcs import FakeVcs
from tests.support.git import clean_environ, commit_file, git, make_repo

pytestmark = pytest.mark.contract

FIRST_FILES = {"src/a.py": b"one\n", "docs/b.md": b"doc\n"}
SECOND_FILES = {
    "src/a.py": b"two\n",
    "docs/b.md": b"doc\n",
    "bin/run": b"src/a.py",
    "vendor/lib": b"",
}
SECOND_MODES = {"bin/run": "120000", "vendor/lib": "160000"}
UNKNOWN = "f" * 40


@dataclass
class Scenario:
    vcs: Vcs
    first: str
    second: str


def fake_scenario(_tmp: Path) -> Scenario:
    first, second = "1" * 40, "2" * 40
    return Scenario(
        FakeVcs(
            RepoState.HAS_COMMITS,
            commits=(CommitSummary(second, "second"), CommitSummary(first, "first")),
            committed=dict(SECOND_FILES),
            revisions={first: dict(FIRST_FILES), second: dict(SECOND_FILES)},
            modes={(second, path): mode for path, mode in SECOND_MODES.items()},
            merge_bases={(first, second): (first,)},
        ),
        first,
        second,
    )


def git_scenario(tmp: Path) -> Scenario:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    if not hasattr(os, "symlink"):
        pytest.skip("no symbolic links on this platform")
    repo = make_repo(tmp / "repo")
    commit_file(repo, "docs/b.md", "doc\n")
    first = commit_file(repo, "src/a.py", "one\n")
    (repo / "src" / "a.py").write_text("two\n", newline="\n")
    (repo / "bin").mkdir()
    try:
        (repo / "bin" / "run").symlink_to("src/a.py")
    except OSError:
        pytest.skip("symbolic links are not allowed here")
    git(repo, "add", "-A")
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{first},vendor/lib")
    git(repo, "commit", "--quiet", "-m", "second")
    second = git(repo, "rev-parse", "HEAD").strip()
    return Scenario(GitVcs(SubprocessRunner(), repo, environ=clean_environ(tmp)), first, second)


SCENARIOS: dict[str, Callable[[Path], Scenario]] = {"fake": fake_scenario, "git": git_scenario}


@pytest.fixture(params=sorted(SCENARIOS))
def scenario(request: pytest.FixtureRequest, tmp_path: Path) -> Scenario:
    return SCENARIOS[request.param](tmp_path)


def test_a_file_is_read_as_it_was_at_each_revision(scenario: Scenario) -> None:
    vcs = scenario.vcs

    assert vcs.read_at(scenario.first, "src/a.py") == b"one\n"
    assert vcs.read_at(scenario.second, "src/a.py") == b"two\n"
    assert vcs.read_at("HEAD", "src/a.py") == b"two\n"


def test_a_missing_file_or_revision_reads_as_nothing(scenario: Scenario) -> None:
    vcs = scenario.vcs

    assert vcs.read_at(scenario.first, "bin/run") is None  # added later
    assert vcs.read_at(scenario.second, "nowhere.txt") is None
    assert vcs.read_at(UNKNOWN, "src/a.py") is None


def test_a_revision_exists_when_it_names_a_commit(scenario: Scenario) -> None:
    vcs = scenario.vcs

    assert vcs.has_revision("HEAD")
    assert vcs.has_revision(scenario.first)
    assert vcs.has_revision(scenario.second)
    assert not vcs.has_revision(UNKNOWN)


def test_the_tree_lists_every_tracked_file_with_its_mode_sorted_by_path(scenario: Scenario) -> None:
    tree = scenario.vcs.tree_at(scenario.second)

    assert [f.path for f in tree] == ["bin/run", "docs/b.md", "src/a.py", "vendor/lib"]
    assert {f.path: f.mode for f in tree} == {
        "bin/run": "120000",
        "docs/b.md": "100644",
        "src/a.py": "100644",
        "vendor/lib": "160000",
    }
    assert scenario.vcs.tree_at("HEAD") == tree


def test_an_older_tree_does_not_list_later_files(scenario: Scenario) -> None:
    older = scenario.vcs.tree_at(scenario.first)
    newer = {file.path: file for file in scenario.vcs.tree_at(scenario.second)}

    assert [(file.path, file.mode) for file in older] == [
        ("docs/b.md", "100644"),
        ("src/a.py", "100644"),
    ]
    assert {file.path: file.oid for file in older}["docs/b.md"] == newer["docs/b.md"].oid
    assert {file.path: file.oid for file in older}["src/a.py"] != newer["src/a.py"].oid


def test_a_missing_revision_has_an_empty_tree(scenario: Scenario) -> None:
    assert scenario.vcs.tree_at(UNKNOWN) == ()


@pytest.mark.parametrize(
    "revision", ["main", "HEAD~1", "--all", "abc123", "", "HEAD:src/a.py", "a" * 39]
)
def test_only_head_and_full_object_ids_are_accepted(scenario: Scenario, revision: str) -> None:
    with pytest.raises(VcsError, match="accepted revision"):
        scenario.vcs.read_at(revision, "src/a.py")
    with pytest.raises(VcsError, match="accepted revision"):
        scenario.vcs.has_revision(revision)
    with pytest.raises(VcsError, match="accepted revision"):
        scenario.vcs.tree_at(revision)


def test_an_unborn_repository_has_no_head_and_nothing_to_read(tmp_path: Path) -> None:
    fake = FakeVcs(RepoState.UNBORN_EMPTY)
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    real = GitVcs(
        SubprocessRunner(), make_repo(tmp_path / "unborn"), environ=clean_environ(tmp_path)
    )

    for vcs in (fake, real):
        assert not vcs.has_revision("HEAD")
        assert vcs.read_at("HEAD", "a.txt") is None
        assert vcs.tree_at("HEAD") == ()


def test_the_merge_base_of_a_commit_and_its_descendant_is_the_older_commit(
    scenario: Scenario,
) -> None:
    vcs = scenario.vcs

    assert vcs.merge_bases(scenario.first, scenario.second) == (scenario.first,)
    assert vcs.merge_bases(scenario.second, scenario.first) == (scenario.first,)


def test_a_diff_lists_what_was_added_modified_and_deleted_sorted_by_path(
    scenario: Scenario,
) -> None:
    forward = scenario.vcs.diff_tree(scenario.first, scenario.second)
    backward = scenario.vcs.diff_tree(scenario.second, scenario.first)

    assert [(c.path, c.status) for c in forward] == [
        ("bin/run", "added"),
        ("src/a.py", "modified"),
        ("vendor/lib", "added"),
    ]
    assert [(c.path, c.status) for c in backward] == [
        ("bin/run", "deleted"),
        ("src/a.py", "modified"),
        ("vendor/lib", "deleted"),
    ]


def test_a_diff_carries_the_modes_and_the_new_object_id(scenario: Scenario) -> None:
    forward = {c.path: c for c in scenario.vcs.diff_tree(scenario.first, scenario.second)}
    tree = {f.path: f for f in scenario.vcs.tree_at(scenario.second)}

    assert (forward["bin/run"].old_mode, forward["bin/run"].new_mode) == ("000000", "120000")
    assert forward["vendor/lib"].new_mode == "160000"
    assert forward["src/a.py"].new_oid == tree["src/a.py"].oid
    backward = {c.path: c for c in scenario.vcs.diff_tree(scenario.second, scenario.first)}
    assert backward["bin/run"].new_oid == "0" * 40


def test_two_equal_trees_have_no_difference(scenario: Scenario) -> None:
    assert scenario.vcs.diff_tree(scenario.second, scenario.second) == ()


def test_the_diff_only_accepts_head_and_full_object_ids(scenario: Scenario) -> None:
    with pytest.raises(VcsError, match="accepted revision"):
        scenario.vcs.diff_tree("main", scenario.second)
    with pytest.raises(VcsError, match="accepted revision"):
        scenario.vcs.merge_bases(scenario.first, "HEAD~1")


def test_a_patch_is_empty_between_equal_trees_and_names_the_changed_files_otherwise(
    scenario: Scenario,
) -> None:
    assert scenario.vcs.diff_patch(scenario.second, scenario.second) == b""
    patch = scenario.vcs.diff_patch(scenario.first, scenario.second)

    assert b"src/a.py" in patch
    assert b"bin/run" in patch


def test_a_ref_name_that_could_be_an_option_or_an_expression_is_refused(scenario: Scenario) -> None:
    for name in ("--all", "-x", "a..b", "HEAD~1", "main:file", "a^b", "x{y}", "", "a/", "x.lock"):
        with pytest.raises(VcsError, match="ref name"):
            scenario.vcs.resolve(name)


def test_an_unknown_ref_resolves_to_nothing(scenario: Scenario) -> None:
    assert scenario.vcs.resolve("no-such-branch") is None


def test_many_files_are_read_at_once_and_a_missing_one_maps_to_nothing(scenario: Scenario) -> None:
    result = scenario.vcs.read_many_at(scenario.second, ["src/a.py", "docs/b.md", "nowhere.txt"])

    assert result == {"src/a.py": b"two\n", "docs/b.md": b"doc\n", "nowhere.txt": None}
    assert scenario.vcs.read_many_at(scenario.second, []) == {}
