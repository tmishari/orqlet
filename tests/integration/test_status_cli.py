"""`orqlet status` through the real CLI: exit statuses, the envelope and the no-write rule (P-4)."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.scan.executables import PathExecutableLocator
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.user_scope import UserHome
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.status import GlobalSources, StatusServices
from orqlet.domain.versions import Version
from orqlet.interface.cli import wiring
from orqlet.interface.cli.app import app
from orqlet.interface.cli.commands import status as status_module
from tests.fakes.vcs import FakeVcs
from tests.support.git import commit_file, make_repo

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


USER_VARIABLES = ("HOME", "USERPROFILE", "CODEX_HOME", "COPILOT_HOME", "ORQLET_DATA_DIR")


def run_status(*args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, ["status", *args, "--json"])
    return result.exit_code, json.loads(result.stdout)


def tree_state(folder: Path) -> set[tuple[str, int, int]]:
    """Every path below `folder` with its size and mode, links not followed."""
    found = set()
    for path in folder.rglob("*"):
        info = path.lstat()
        found.add((path.relative_to(folder).as_posix(), info.st_size, info.st_mode))
    return found


def write_manifest(data: Path, version: str) -> None:
    (data / "user").mkdir(parents=True)
    manifest = {
        "schema": "orqlet.user-manifest/v1",
        "change_id": "c-1",
        "created_at": "2026-11-22T10:00:00Z",
        "roots": {},
        "entries": [
            {
                "path": "claude/skills/orqlet/SKILL.md",
                "sha256": "0" * 64,
                "workflow_version": version,
                "owners": ["claude-code"],
            }
        ],
    }
    (data / "user" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_every_test_runs_under_a_temporary_home(tmp_path_factory: pytest.TempPathFactory) -> None:
    """AC-9: the autouse fixture points the five variables into the pytest base temporary folder."""
    base = tmp_path_factory.getbasetemp().resolve()
    for name in USER_VARIABLES:
        assert Path(os.environ[name]).resolve().is_relative_to(base), name


def test_status_is_an_implemented_command() -> None:
    """AC-12: `IMPLEMENTED_COMMANDS` lists `status` (the equality test is test_validate_cli)."""
    assert "status" in IMPLEMENTED_COMMANDS


def test_a_repository_reports_init_in_the_envelope(tmp_path: Path) -> None:
    """AC-6, AC-1: exit 0 and the existing envelope; a repository without `.orqlet` gives init.

    P-5 AC-16 (BC-11, BC-24): the manifest holds the packaged release version, not a pinned one,
    so the client stays `configured` after a workflow version bump.
    """
    repo = make_repo(tmp_path / "project")
    commit_file(repo, "README.txt", "hello\n")
    write_manifest(Path(os.environ["ORQLET_DATA_DIR"]), str(PackagedWorkflow().release.version))

    code, envelope = run_status("--root", str(repo))

    assert code == 0
    assert envelope["schema"] == "orqlet.cli-result/v1"
    assert envelope["command"] == "status"
    assert envelope["ok"] is True
    data = envelope["data"]
    assert data["location"] == "repository"
    assert data["top_level"] == os.path.realpath(repo)
    assert data["top_level_reason"] is None
    assert data["global"]["clients"]["claude-code"] == "configured"
    assert data["orqlet_on_path"] in {"same", "different", "absent"}
    assert data["next"] == "init"


def test_a_folder_outside_any_repository(tmp_path: Path) -> None:
    """AC-1, AC-2: no manifest gives missing for every client and next install-global."""
    plain = tmp_path / "plain"
    plain.mkdir()

    code, envelope = run_status("--root", str(plain))

    assert code == 0
    assert envelope["data"]["location"] == "not-a-repository"
    assert set(envelope["data"]["global"]["clients"].values()) == {"missing"}
    assert envelope["data"]["next"] == "install-global"


def test_a_data_directory_outside_the_home_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-2: ORQLET_DATA_DIR outside the home is read, and a newer version refuses."""
    data = tmp_path / "elsewhere" / "data"
    write_manifest(data, "99.0.0")
    monkeypatch.setenv("ORQLET_DATA_DIR", str(data))

    code, envelope = run_status("--root", str(tmp_path))

    assert code == 0
    assert envelope["data"]["global"]["clients"]["claude-code"] == "newer"
    assert envelope["data"]["next"] == "refuse-newer-global"


def test_status_writes_nothing_and_creates_no_data_folder(tmp_path: Path) -> None:
    """AC-5: paths, sizes and modes under the home and the project are the same after the run."""
    home = Path(os.environ["HOME"])
    data = Path(os.environ["ORQLET_DATA_DIR"])
    repo = make_repo(tmp_path / "project")
    commit_file(repo, "README.txt", "hello\n")
    (repo / ".orqlet").mkdir()
    (repo / ".orqlet" / "workflow.lock").write_text("workflow_version: 0.5.0\n", encoding="utf-8")
    before = (tree_state(home), tree_state(repo))

    code, envelope = run_status("--root", str(repo))

    assert code == 0
    assert envelope["data"]["location"] == "initialized-project"
    assert (tree_state(home), tree_state(repo)) == before
    assert not data.exists()


def test_a_failing_vcs_exits_5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-6, AC-7: a check that could not run exits 5, and its top level is null."""

    def services(_root: Path) -> StatusServices:
        return StatusServices(
            sources=GlobalSources(None, StrictYamlLoader(), Version(0, 5, 0)),
            vcs=FakeVcs(worktree_error="git is not installed"),
            open_project=lambda top: LocalFileSystem(Path(top)),
            executables=PathExecutableLocator(str(tmp_path / "bin"), None),
            home=UserHome(path=str(tmp_path / "home")),
        )

    monkeypatch.setattr(status_module, "build_status_services", services)

    code, envelope = run_status("--root", str(tmp_path))

    assert code == 5
    assert envelope["ok"] is False
    assert envelope["data"]["top_level"] is None
    assert any("work tree" in reason for reason in envelope["not_run"])
    assert not any("git was not run" in reason for reason in envelope["not_run"])


def test_an_unknown_option_exits_2(tmp_path: Path) -> None:
    """AC-6: a usage error exits 2."""
    result = RUNNER.invoke(app, ["status", "--root", str(tmp_path), "--no-such-option"])

    assert result.exit_code == 2


def test_data_directory_still_creates_and_the_resolver_never_does() -> None:
    """AC-10: `data_directory()` keeps creating the folder (K-10); the new resolver never does."""
    target = Path(os.environ["ORQLET_DATA_DIR"])
    assert not target.exists()

    assert wiring.resolve_data_directory() == target
    assert not target.exists()

    assert wiring.data_directory() == target
    assert target.is_dir()


POSIX_USER = pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0, reason="POSIX permissions that bind this user"
)


@POSIX_USER
@pytest.mark.parametrize("unreadable", ["project", "data"])
def test_an_unreadable_folder_is_a_check_not_run(tmp_path: Path, unreadable: str) -> None:
    """Code review of P-4, round 2: a refused permission exits 5 with a not_run entry, not 70."""
    repo = make_repo(tmp_path / "project")
    commit_file(repo, "README.txt", "hello\n")
    (repo / ".orqlet").mkdir()
    data = Path(os.environ["ORQLET_DATA_DIR"])
    (data / "user").mkdir(parents=True)
    locked = repo / ".orqlet" if unreadable == "project" else data / "user"
    locked.chmod(0)
    try:
        code, envelope = run_status("--root", str(repo))
    finally:
        locked.chmod(0o700)

    assert code == 5
    assert envelope["not_run"]


@POSIX_USER
def test_a_data_directory_below_an_unsearchable_folder_is_a_check_not_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q-74: a data directory that cannot be checked is not reported as missing with exit 0."""
    repo = make_repo(tmp_path / "project")
    commit_file(repo, "README.txt", "hello\n")
    locked = tmp_path / "locked"
    (locked / "data").mkdir(parents=True)
    monkeypatch.setenv("ORQLET_DATA_DIR", str(locked / "data"))
    locked.chmod(0)
    try:
        code, envelope = run_status("--root", str(repo))
    finally:
        locked.chmod(0o700)

    assert code == 5
    assert envelope["not_run"]


@POSIX_USER
def test_a_git_in_the_project_is_not_run_through_an_empty_path_element(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q-73: an empty PATH element names the working folder, where git would start."""
    repo = make_repo(tmp_path / "project")
    commit_file(repo, "README.txt", "hello\n")
    marker = tmp_path / "hostile-git-ran"
    hostile = repo / "git"
    hostile.write_text(f"#!/bin/sh\n: > '{marker}'\n", encoding="utf-8")  # no PATH lookup
    hostile.chmod(0o755)
    real_git = shutil.which("git")
    assert real_git is not None
    monkeypatch.setenv("PATH", os.pathsep + str(Path(real_git).parent))

    code, envelope = run_status("--root", str(repo))

    assert not marker.exists()
    assert code == 5
    assert envelope["data"]["top_level"] is None


@pytest.mark.parametrize(("where", "expected"), [("at", 5), ("below", 0)])
def test_a_data_path_through_a_regular_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, where: str, expected: int
) -> None:
    """Q-74: a file at the data path cannot be checked; a file above it means it does not exist."""
    repo = make_repo(tmp_path / "project")
    commit_file(repo, "README.txt", "hello\n")
    blocker = tmp_path / "blocker"
    blocker.write_text("not a folder\n", encoding="utf-8")
    monkeypatch.setenv("ORQLET_DATA_DIR", str(blocker if where == "at" else blocker / "data"))

    code, envelope = run_status("--root", str(repo))

    assert code == expected
    assert set(envelope["data"]["global"]["clients"].values()) == {"missing"}


# --- P-5: orqlet_on_path absent and the plain-text output (AC-15, AC-17) ---------------------


def test_orqlet_on_path_is_absent_whatever_path_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P-5 AC-15 (BC-38, Q-82): no PATH element holds orqlet, with empty, `.` and relative ones."""
    working = tmp_path / "working"
    working.mkdir()
    empty = tmp_path / "empty-folder"
    empty.mkdir()
    monkeypatch.chdir(working)
    monkeypatch.setenv("PATH", os.pathsep.join(["", ".", "relative/bin", str(empty)]))

    result = RUNNER.invoke(app, ["status", "--root", str(working), "--json"])

    envelope = json.loads(result.stdout)
    assert envelope["data"]["orqlet_on_path"] == "absent"


PLAIN_LABELS = ["global", "orqlet on PATH", "location", "top level", "versions", "next"]


def _labels(lines: list[str]) -> list[str]:
    return [line.split(": ", 1)[0] for line in lines]


def test_status_prints_plain_lines_with_the_exit_status_of_json(tmp_path: Path) -> None:
    """P-5 AC-17 (BC-11, BC-40, A-50): the same fields as plain lines, no ANSI code, same exit."""
    repo = make_repo(tmp_path / "project")
    commit_file(repo, "README.txt", "hello\n")
    write_manifest(Path(os.environ["ORQLET_DATA_DIR"]), str(PackagedWorkflow().release.version))

    plain = RUNNER.invoke(app, ["status", "--root", str(repo)])
    as_json = RUNNER.invoke(app, ["status", "--root", str(repo), "--json"])

    lines = plain.stdout.splitlines()
    assert _labels(lines) == PLAIN_LABELS
    assert "\x1b" not in plain.stdout
    assert lines[0].startswith("global: ")
    assert "claude-code configured" in lines[0]
    assert lines[2] == "location: repository"
    assert lines[3] == f"top level: {os.path.realpath(repo)}"
    assert lines[5] == "next: init"
    assert plain.exit_code == as_json.exit_code == 0


@POSIX_USER
def test_status_prints_host_step_and_not_run_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P-5 AC-17 (BC-11, BC-40, A-50): host steps and checks not run, plain, with exit 5 twice.

    A relative PATH element searched before the folder that holds `orqlet` is a host step
    (unsafe-path-element), and Git is skipped, so the location is a check not run (Q-73).
    """
    working = tmp_path / "working"
    working.mkdir()
    tools = tmp_path / "tools"
    tools.mkdir()
    fake = tools / "orqlet"
    fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.chdir(working)
    monkeypatch.setenv("PATH", os.pathsep.join(["relative", str(tools)]))

    plain = RUNNER.invoke(app, ["status", "--root", str(working)])
    as_json = RUNNER.invoke(app, ["status", "--root", str(working), "--json"])

    lines = plain.stdout.splitlines()
    assert _labels(lines)[: len(PLAIN_LABELS)] == PLAIN_LABELS
    assert "host step: unsafe-path-element" in lines
    assert any(line.startswith("not run: ") for line in lines)
    assert set(_labels(lines)[len(PLAIN_LABELS) :]) <= {"host step", "not run"}
    assert "\x1b" not in plain.stdout
    assert plain.exit_code == as_json.exit_code == 5
