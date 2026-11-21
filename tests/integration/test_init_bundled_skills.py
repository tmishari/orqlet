"""`orqlet init` and `orqlet upgrade` write the bundled skills for the three clients (task
one-command-setup, phase P-2, AC-8).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-2 in
docs/design/one-command-setup/plan.yaml, EC-2 an expected change of the design manifest there,
and "the interface" is the one that the Coder gave for P-2 (the seven bundled skill folders and
the files they render, listed in tests/support/render.py).

HOW THESE TESTS WERE WRITTEN. The Tester of P-2 wrote them before the skills existed, so each is
expected to fail until the skills are in the workflow package. A project is a copy of
tests/fixtures/repos/uv_fastapi in a temporary Git repository; HOME is an empty folder of the test
and the data directory of the command (`ORQLET_DATA_DIR`, where the journal and the backups go) is
another, as in tests/integration/test_init_cli.py and test_upgrade_mcp_files.py.

Choices:
- "A project initialized at the base revision" is simulated by `init_project` with the packaged
  workflow minus the seven bundled skill folders (`WithoutBundledSkills`), at the same release;
  `upgrade` then runs through the real command line with the packaged workflow. `upgrade` plans
  every run (application/usecases/upgrade.py), so the same release number does not hide the new
  files.
- "Nothing is written outside the project" is read as test_init_cli.py reads it: HOME stays empty
  and a sibling folder of the project is unchanged; the data directory is Orqlet's own journal and
  backup store and is not the project's surroundings.

Deliberately NOT pinned: the bytes of the new files (the golden tests), the other writes that an
upgrade may plan, and the human output.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.generated_lock import GeneratedLock, LockedFile
from orqlet.application.contracts.loading import load_contract
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.versions import WorkflowRelease
from orqlet.interface.cli.app import app
from tests.support.git import clean_environ, git, make_repo
from tests.support.real_env import real_services, snapshot
from tests.support.render import BUNDLED_SKILL_NAMES, PHASE_SKILL_NAMES, skill_files
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()
LOCK = ".orqlet/generated.lock.yaml"
HIDDEN = tuple(f"skills/{name}/" for name in BUNDLED_SKILL_NAMES)
NEW_FILES = sorted(
    {
        *skill_files(".claude/skills", BUNDLED_SKILL_NAMES),
        *skill_files(".agents/skills", BUNDLED_SKILL_NAMES),
        *(f".agents/skills/{name}/agents/openai.yaml" for name in BUNDLED_SKILL_NAMES),
    }
)
PHASE_FILES = sorted(
    {
        *skill_files(".claude/skills", PHASE_SKILL_NAMES),
        *skill_files(".agents/skills", PHASE_SKILL_NAMES),
    }
)
SIBLING = "notes.txt"


class WithoutBundledSkills:
    """The packaged workflow without the seven bundled skill folders that phase P-2 adds."""

    def __init__(self) -> None:
        self._base = PackagedWorkflow()

    @property
    def release(self) -> WorkflowRelease:
        return self._base.release

    def read_text(self, path: str) -> str:
        if path.startswith(HIDDEN):
            raise KeyError(f"{path} is not a file of this workflow")
        return self._base.read_text(path)

    def paths(self) -> tuple[str, ...]:
        return tuple(path for path in self._base.paths() if not path.startswith(HIDDEN))

    def problems(self) -> tuple[str, ...]:
        return self._base.problems()


class Setup:
    def __init__(self, tmp_path: Path) -> None:
        self.home = tmp_path / "home"
        self.data = tmp_path / "data"
        self.work = tmp_path / "work"
        self.root = self.work / "project"


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Setup:
    """A committed project, an empty HOME, a data directory and a sibling file of the project."""
    paths = Setup(tmp_path)
    paths.home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(paths.data))
    for name, value in clean_environ(paths.home).items():
        monkeypatch.setenv(name, value)
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", paths.root)
    make_repo(paths.root)
    git(paths.root, "add", "-A")
    git(paths.root, "commit", "--quiet", "-m", "initial")
    (paths.work / SIBLING).write_text("not ours\n", encoding="utf-8")
    return paths


def run(*args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout)


def lock_entries(root: Path) -> dict[str, LockedFile]:
    lock = load_contract(StrictYamlLoader(), GeneratedLock, (root / LOCK).read_bytes(), source=LOCK)
    return {entry.path: entry for entry in lock.files}


def assert_nothing_outside_the_project(setup: Setup) -> None:
    assert snapshot(setup.home) == {}
    outside = {k: v for k, v in snapshot(setup.work).items() if not k.startswith("project/")}
    assert outside == {SIBLING: b"not ours\n"}


def assert_orqlet_owns_the_new_files(root: Path) -> None:
    entries = lock_entries(root)
    for path in NEW_FILES:
        assert (root / path).is_file(), path
        assert path in entries, path
        assert entries[path].owner is OwnerMode.ORQLET, path
        assert entries[path].file_class is FileClass.PROTECTED, path


def test_ac8_init_writes_the_bundled_skills_for_the_three_clients(setup: Setup) -> None:
    """AC-8. expected_behavior_source: AC-8 ("`orqlet init` in a temporary repository with the three
    clients writes the bundled skill files for each client ... Nothing is written outside the
    project"); EC-2; ADR-006 decision 3 (the bundled skills render as the other packaged skills do,
    for every client); AC-6 (30 files per skill folder and 7 Codex sidecars). The three clients are
    init's default (`ALL_CLIENTS`)."""
    code, document = run(
        "init", "--root", str(setup.root), "--yes", "--answer", "repository.target_branch=main"
    )

    assert code == 0, document
    assert len(NEW_FILES) == 30 * 2 + 7
    assert_orqlet_owns_the_new_files(setup.root)
    assert_nothing_outside_the_project(setup)


def test_ac8_upgrade_of_a_project_set_up_before_these_skills_adds_them_as_orqlet_owned_files(
    setup: Setup,
) -> None:
    """AC-8. expected_behavior_source: AC-8 ("`orqlet upgrade` of a project initialized at the base
    revision adds them as Orqlet-owned files. Nothing is written outside the project"); EC-2; R-6.
    The phase skills that the project already had keep their bytes, and a second upgrade finds
    nothing to do."""
    result = init_project(
        real_services(setup.root, setup.data, workflow=WithoutBundledSkills()),
        InitOptions(assume_yes=True),
    )
    assert result.status == "applied", result.findings
    before = snapshot(setup.root)
    assert not [path for path in NEW_FILES if path in before]
    assert not set(NEW_FILES) & set(lock_entries(setup.root))
    assert all(path in before for path in PHASE_FILES)

    code, document = run("upgrade", "--root", str(setup.root), "--yes")

    assert code == 0, document
    assert document["data"]["status"] == "applied"
    created = {item["path"] for item in document["data"]["writes"] if item["kind"] == "create"}
    assert set(NEW_FILES) <= created
    assert_orqlet_owns_the_new_files(setup.root)
    after = snapshot(setup.root)
    for path in PHASE_FILES:
        assert after[path] == before[path], path
    assert_nothing_outside_the_project(setup)

    again_code, again = run("upgrade", "--root", str(setup.root), "--yes")
    assert again_code == 0, again
    assert again["data"]["status"] == "up-to-date"
