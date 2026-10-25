"""A repository's own configuration must never make Orqlet run a program (ADR-003).

The repository below points `core.fsmonitor`, a clean filter, `diff.external` and a textconv at a
script that writes a marker file. First the same repository is read with plain `git`, as a control:
if no plain command fires the marker, this Git version cannot be used to prove anything and the
test says so by skipping. Then every `GitVcs` operation runs and the marker must stay absent.
"""

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
from orqlet.application.ports.vcs import VcsError
from tests.support.git import clean_environ, commit_file, git, make_repo

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]


class HostileRepo:
    def __init__(self, base: Path) -> None:
        self.path = make_repo(base / "hostile")
        self.marker = base / "marker.txt"
        script = base / "payload.py"
        script.write_text(
            f"from pathlib import Path\nPath({str(self.marker)!r}).write_text('ran')\n",
            encoding="utf-8",
        )
        self.command = f'"{Path(sys.executable).as_posix()}" "{script.as_posix()}"'
        commit_file(self.path, ".gitattributes", "* filter=evil diff=evil\n")
        commit_file(self.path, "a.txt", "one\n")
        # Configure only after the commits: setting these first would run them during setup.
        for key in ("core.fsmonitor", "filter.evil.clean", "diff.external", "diff.evil.textconv"):
            git(self.path, "config", key, self.command)
        (self.path / "a.txt").write_text("two\n")  # a modified file gives status and diff work
        (self.path / "new.txt").write_text("untracked\n")

    @property
    def fired(self) -> bool:
        return self.marker.exists()

    def reset(self) -> None:
        self.marker.unlink(missing_ok=True)


@pytest.fixture
def hostile(tmp_path: Path) -> HostileRepo:
    return HostileRepo(tmp_path)


CONTROLS = [
    ["status", "--porcelain"],
    ["diff", "HEAD"],
    ["ls-files", "--others", "--modified"],
    ["diff-index", "HEAD"],
    ["add", "--dry-run", "."],
]


def test_the_control_proves_this_git_version_runs_configured_programs(
    hostile: HostileRepo,
) -> None:
    fired_by: list[str] = []
    for command in CONTROLS:
        hostile.reset()
        subprocess.run(
            ["git", *command],
            cwd=hostile.path,
            env=clean_environ(hostile.path.parent),
            capture_output=True,
            check=False,
        )
        if hostile.fired:
            fired_by.append(command[0])
    if not fired_by:
        pytest.skip("no plain git command ran the configured programs on this Git version")
    assert fired_by  # at least one plain command is dangerous here, which is the point


def test_no_orqlet_operation_runs_a_configured_program(hostile: HostileRepo) -> None:
    environ = clean_environ(hostile.path.parent)
    vcs = GitVcs(SubprocessRunner(), hostile.path, environ=environ)
    runner = GitRunner(SubprocessRunner(), str(hostile.path), environ=environ)
    hostile.reset()

    vcs.state()
    vcs.head_commit()
    vcs.current_branch()
    vcs.tracked_files()
    vcs.read_committed("a.txt")
    vcs.recent_commits(5)
    vcs.remote_names()
    vcs.has_staged_changes()
    head = vcs.head_commit()
    assert head is not None
    vcs.has_revision(head)
    vcs.read_at(head, "a.txt")
    vcs.tree_at(head)
    vcs.ignored(["a.txt", "new.txt", ".gitattributes"])
    read_blobs(runner, "HEAD", ["a.txt", ".gitattributes"])
    runner.run("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    runner.run("diff-index", "--cached", "HEAD")
    runner.run("diff-tree", "-r", "HEAD", "HEAD")

    assert not hostile.fired


def test_committed_content_is_returned_unfiltered(hostile: HostileRepo) -> None:
    environ = clean_environ(hostile.path.parent)
    vcs = GitVcs(SubprocessRunner(), hostile.path, environ=environ)

    assert vcs.read_committed("a.txt") == b"one\n"


@pytest.mark.parametrize(
    "command",
    [
        ["diff-index", "HEAD"],
        ["ls-files", "--modified"],
        ["ls-files", "-m"],
        ["ls-files", "-mo"],
        ["cat-file", "--filters", "HEAD:a.txt"],
        ["cat-file", "--textconv", "HEAD:a.txt"],
        ["diff-tree", "--ext-diff", "HEAD", "HEAD"],
        ["diff-index", "--cached", "--textconv", "HEAD"],
    ],
)
def test_options_that_run_configured_programs_are_refused(
    hostile: HostileRepo, command: list[str]
) -> None:
    runner = GitRunner(
        SubprocessRunner(), str(hostile.path), environ=clean_environ(hostile.path.parent)
    )
    hostile.reset()

    with pytest.raises(VcsError, match="not allowed"):
        runner.run(*command)

    assert not hostile.fired


def test_a_pathspec_that_looks_like_a_forbidden_option_after_double_dash_is_allowed(
    hostile: HostileRepo,
) -> None:
    runner = GitRunner(
        SubprocessRunner(), str(hostile.path), environ=clean_environ(hostile.path.parent)
    )

    runner.run("ls-files", "--cached", "--", "-m")

    assert not hostile.fired
