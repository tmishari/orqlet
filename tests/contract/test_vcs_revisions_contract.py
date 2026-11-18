"""Reading files and trees at a revision: one suite for the fake and for real Git (A-3)."""

from __future__ import annotations

import io
import os
import shutil
from collections.abc import Callable, Sequence
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


# --- phase P-11: a patch without the paths that are left out (AC-1, AC-2) ----------------------
# These tests were written first, by the Tester of phase P-11 of the task dynamic-model-profiles,
# before the implementation existed. Each cites its `expected_behavior_source`: AC-n of phase P-11
# in docs/design/dynamic-model-profiles/plan.yaml and decision 8 of ADR-007. They use a scenario
# of their own, so FIRST_FILES and SECOND_FILES above stay as they are. The patch of the fake is
# simplified (a header line and a status line for each path), so the tests compare only what the
# fake and Git can both give: the patch cut into sections at the lines that start with
# `diff --git `, and the list of those sections.

ROUND_ONE = "docs/design/t/reviews/round1.yaml"
ROUND_TWO = "docs/design/t/reviews/deep/round2.yaml"
PLAIN = "docs/notes/a.md"
BRACKETS = "docs/notes/[a-b].md"  # a literal name; read as a glob it would match a.md
DEEP_NOTE = "docs/notes/sub/x.md"
EXCLUSION_FIRST = {
    "src/a.py": b"one\n",
    ROUND_ONE: b"round one\n",
    PLAIN: b"a one\n",
    BRACKETS: b"brackets one\n",
    DEEP_NOTE: b"x one\n",
}
EXCLUSION_SECOND = {
    "src/a.py": b"two\n",
    ROUND_ONE: b"round one, answered\n",
    ROUND_TWO: b"round two\n",
    PLAIN: b"a two\n",
    BRACKETS: b"brackets two\n",
    DEEP_NOTE: b"x two\n",
}
CHANGED = frozenset(EXCLUSION_SECOND)  # every path of the scenario differs between the commits
REVIEWS = frozenset({ROUND_ONE, ROUND_TWO})
REVIEWS_PATTERN = "docs/design/*/reviews/*"
SECTION_START = b"diff --git "


def fake_exclusion_scenario(_tmp: Path) -> Scenario:
    first, second = "1" * 40, "2" * 40
    return Scenario(
        FakeVcs(
            RepoState.HAS_COMMITS,
            commits=(CommitSummary(second, "second"), CommitSummary(first, "first")),
            committed=dict(EXCLUSION_SECOND),
            revisions={first: dict(EXCLUSION_FIRST), second: dict(EXCLUSION_SECOND)},
            merge_bases={(first, second): (first,)},
        ),
        first,
        second,
    )


def commit_state(repo: Path, files: dict[str, bytes]) -> str:
    """Write the files as bytes (no line-ending change) and commit them in one commit."""
    for name, content in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", "state")
    return git(repo, "rev-parse", "HEAD").strip()


def git_exclusion_scenario(tmp: Path) -> Scenario:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    repo = make_repo(tmp / "repo")
    first = commit_state(repo, EXCLUSION_FIRST)
    second = commit_state(repo, EXCLUSION_SECOND)
    return Scenario(GitVcs(SubprocessRunner(), repo, environ=clean_environ(tmp)), first, second)


EXCLUSION_SCENARIOS: dict[str, Callable[[Path], Scenario]] = {
    "fake": fake_exclusion_scenario,
    "git": git_exclusion_scenario,
}


@pytest.fixture(params=sorted(EXCLUSION_SCENARIOS))
def exclusion(request: pytest.FixtureRequest, tmp_path: Path) -> Scenario:
    return EXCLUSION_SCENARIOS[request.param](tmp_path)


def sections(patch: bytes) -> list[bytes]:
    """The patch cut into one piece for each file, at the lines that start with `diff --git `."""
    found: list[bytes] = []
    for line in io.BytesIO(patch):
        if line.startswith(SECTION_START):
            found.append(b"")
        assert found, "a patch starts with the header of a file"
        found[-1] += line
    return found


def path_of(section: bytes) -> str:
    """The path in the header of a section. There are no renames, so both sides name one path."""
    header = section.split(b"\n", 1)[0].decode("utf-8").removeprefix("diff --git ")
    length = (len(header) - len("a/ b/")) // 2
    return header[len("a/") : len("a/") + length]


def patch_sections(
    scenario: Scenario, *, patterns: Sequence[str] = (), paths: Sequence[str] = ()
) -> list[bytes]:
    patch = scenario.vcs.diff_patch(
        scenario.first, scenario.second, exclude_patterns=patterns, exclude_paths=paths
    )
    return sections(patch)


def assert_patch_without(
    scenario: Scenario,
    excluded: frozenset[str],
    *,
    patterns: Sequence[str] = (),
    paths: Sequence[str] = (),
) -> None:
    """The patch with the exclusions is the whole patch minus the sections of `excluded`."""
    whole = patch_sections(scenario)
    assert {path_of(section) for section in whole} == CHANGED
    assert excluded <= CHANGED  # a typo in a test must not make it pass for nothing
    kept = patch_sections(scenario, patterns=patterns, paths=paths)
    assert kept == [section for section in whole if path_of(section) not in excluded]


def test_a_patch_without_an_exclusion_is_the_whole_patch(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (the port is `diff_patch(base, head, *,
    exclude_patterns=(), exclude_paths=())`); the brief of the phase (called with no exclusion it
    behaves exactly as before). Naming both parameters empty is naming none, and the patch holds
    a section for every changed path."""
    vcs = exclusion.vcs

    plain = vcs.diff_patch(exclusion.first, exclusion.second)
    named = vcs.diff_patch(
        exclusion.first,
        exclusion.second,
        exclude_patterns=(),
        exclude_paths=(),
    )

    assert named == plain
    assert {path_of(section) for section in sections(plain)} == CHANGED


def test_a_pattern_removes_the_sections_of_the_paths_it_matches(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 ("a path that matches any pattern gets no section";
    "a pattern matches as `fnmatch` does, with `*` crossing `/`"); AC-2 (the fake and the real
    adapter run the same scenario and agree); ADR-007 decision 8. The pattern of `review
    prepare` removes a record and a record in a folder below the reviews folder, and keeps the
    other sections as they were."""
    assert_patch_without(exclusion, REVIEWS, patterns=(REVIEWS_PATTERN,))


def test_a_star_in_a_pattern_also_matches_the_slash(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 ("a pattern matches as `fnmatch` does, with `*`
    crossing `/`"). `docs/*.md` removes the notes at every depth below `docs/`, and
    `*round1.yaml` removes the record whatever folder holds it."""
    notes = frozenset({PLAIN, BRACKETS, DEEP_NOTE})

    assert_patch_without(exclusion, notes, patterns=("docs/*.md",))
    assert_patch_without(exclusion, frozenset({ROUND_ONE}), patterns=("*round1.yaml",))


def test_a_question_mark_in_a_pattern_also_matches_the_slash(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 ("a pattern matches as `fnmatch` does"; `fnmatch`
    lets `?` match `/`) and the brief of the phase (`*` and `?` both match `/`). `docs/notes?a.md`
    names `docs/notes/a.md` and nothing else."""
    assert_patch_without(exclusion, frozenset({PLAIN}), patterns=("docs/notes?a.md",))


def test_a_character_class_in_a_pattern_is_read_as_a_glob(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 ("a pattern matches as `fnmatch` does"; `[a-c]` is one
    of `a`, `b` and `c`). The class matches `a.md`, and not the file whose name is `[a-b].md`.
    The pattern is not equal to the name of any file, so a reading of it as plain text finds
    nothing."""
    assert_patch_without(exclusion, frozenset({PLAIN}), patterns=("docs/notes/[a-c].md",))


def test_a_pattern_has_to_match_the_whole_path(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (a pattern matches the whole repository-relative path
    as `fnmatch.fnmatchcase` does, so a pattern that matches only the end of a path does not
    match it). `reviews/*` does not match `docs/design/t/reviews/round1.yaml`."""
    assert_patch_without(exclusion, frozenset(), patterns=("reviews/*", "round1.yaml"))


def test_a_pattern_that_matches_nothing_changes_nothing(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (only a path that matches gets no section); AC-2
    ("holds the other sections byte for byte as the unfiltered patch holds them")."""
    assert_patch_without(exclusion, frozenset(), patterns=("docs/nothing/*", "*.rs"))


def test_a_path_removes_the_section_of_the_path_that_equals_it(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 ("a path that equals an `exclude_paths` entry gets no
    section"; "a path matches only itself"); AC-2."""
    assert_patch_without(exclusion, frozenset({"src/a.py"}), paths=("src/a.py",))


def test_a_literal_path_with_glob_characters_is_excluded_only_as_that_path(
    exclusion: Scenario,
) -> None:
    """expected_behavior_source: P-11 AC-2 ("a literal path with glob characters is excluded only
    as that path"); AC-1 ("a path matches only itself"). The file `[a-b].md` is dropped. A glob
    reading of the entry would drop `a.md` and keep `[a-b].md`, which is the opposite."""
    assert_patch_without(exclusion, frozenset({BRACKETS}), paths=(BRACKETS,))

    kept = {path_of(section) for section in patch_sections(exclusion, paths=(BRACKETS,))}
    assert PLAIN in kept
    assert BRACKETS not in kept


def test_a_wildcard_in_a_path_is_not_a_wildcard(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (a path matches only itself) and the brief of the
    phase (glob characters in an `exclude_paths` entry are literal). No file is named `*.md`,
    `?.md` or like the pattern of the reviews, so nothing is removed."""
    entries = ("docs/notes/*.md", "docs/notes/?.md", REVIEWS_PATTERN)

    assert_patch_without(exclusion, frozenset(), paths=entries)


def test_a_path_that_is_only_the_start_of_a_name_is_not_that_path(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (a path matches only itself). `src/a` and `src/a.p`
    are the start of the name `src/a.py`, and `docs/notes/a.m` of `docs/notes/a.md`."""
    assert_patch_without(exclusion, frozenset(), paths=("src/a", "src/a.p", "docs/notes/a.m"))


def test_a_path_that_names_a_directory_excludes_no_file_below_it(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 ("a path matches only itself") and the brief of the
    phase (an entry that names a directory matches no file below it). Git reads a pathspec that
    names a directory as everything below it, so the real adapter may not give this with
    `:(exclude,literal)` alone: see the question that the Tester put to the person."""
    assert_patch_without(exclusion, frozenset(), paths=("docs/notes", "docs/notes/sub"))


def test_both_parameters_together_exclude_the_union_of_their_paths(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (the port takes `exclude_patterns` and `exclude_paths`
    together, as `review prepare` passes them); the brief of the phase (the union is excluded
    and every other section stays as it was); AC-2."""
    assert_patch_without(
        exclusion, REVIEWS | {BRACKETS}, patterns=(REVIEWS_PATTERN,), paths=(BRACKETS,)
    )


def test_excluding_every_changed_path_leaves_an_empty_patch(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (a path that matches gets no section); the existing
    contract that a patch with no difference is empty."""
    patch = exclusion.vcs.diff_patch(
        exclusion.first,
        exclusion.second,
        exclude_patterns=("*",),
    )

    assert patch == b""


def test_an_entry_that_looks_like_an_option_is_only_a_path(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (the adapter passes the entries "only after `--`"); AC-6
    (no git option beyond the pathspec is added). An entry is data: one that reads like an option
    changes nothing and is not an error."""
    entries = ("--stat", "-p", "--output=leak.patch", "--help")

    whole = patch_sections(exclusion)

    assert patch_sections(exclusion, patterns=entries) == whole
    assert patch_sections(exclusion, paths=entries) == whole


def test_a_revision_that_is_not_head_or_a_full_id_is_still_refused(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 (the allow-listed `diff-tree` "whose option check is
    unchanged") and AC-6; the existing contract that only `HEAD` and full object ids are accepted
    as revisions. An exclusion does not turn a refused revision into an accepted one."""
    with pytest.raises(VcsError, match="accepted revision"):
        exclusion.vcs.diff_patch("main", exclusion.second, exclude_paths=("src/a.py",))
    with pytest.raises(VcsError, match="accepted revision"):
        exclusion.vcs.diff_patch(exclusion.first, "HEAD~1", exclude_patterns=("*",))


# --- phase P-11: the Coder's own cases (the plan does not state them; a measurement does) ------
# Written by the Coder after the code, not by the Tester: no acceptance criterion names them. Each
# cites what it rests on. They run against the fake and the real adapter like the cases above.


@pytest.mark.parametrize(
    ("patterns", "paths"),
    [
        pytest.param(("",), (), id="an-empty-pattern"),
        pytest.param(("docs/\0x",), (), id="a-pattern-with-a-nul"),
        pytest.param((), ("",), id="an-empty-path"),
        pytest.param((), ("docs/../src/a.py",), id="a-path-that-climbs"),
        pytest.param((), ("/src/a.py",), id="an-absolute-path"),
        pytest.param((), ("docs/",), id="a-path-with-a-trailing-slash"),
        pytest.param((), ("docs\\b.md",), id="a-path-with-a-backslash"),
    ],
)
def test_an_exclusion_that_git_could_read_as_something_else_is_refused(
    exclusion: Scenario, patterns: tuple[str, ...], paths: tuple[str, ...]
) -> None:
    """expected_behavior_source: the measurement of the Coder with git 2.56.1 (an empty
    `:(exclude,literal)` pathspec dropped every section of the patch with no error, and `..` or a
    trailing `/` in a literal pathspec names a directory); P-11 AC-1 ("a path matches only
    itself"); the baseline ("validate input where it enters"). The port refuses these entries,
    in the fake and in the adapter, before any command runs."""
    with pytest.raises(VcsError, match="exclu"):
        exclusion.vcs.diff_patch(
            exclusion.first, exclusion.second, exclude_patterns=patterns, exclude_paths=paths
        )


def test_a_path_that_is_in_no_tree_excludes_nothing(exclusion: Scenario) -> None:
    """expected_behavior_source: P-11 AC-1 ("a path matches only itself": nothing equals it) and
    the measurement of the Coder with git 2.56.1 (a literal pathspec that names no path is not an
    error). A note that names a file that is not in the tree, or not yet, changes nothing."""
    assert_patch_without(exclusion, frozenset(), paths=("docs/notes/not-written-yet.md",))
