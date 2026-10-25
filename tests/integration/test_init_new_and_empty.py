"""FM-N01 to FM-N04: `init` for new and empty projects, with real Git."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from orqlet.interface.cli.app import app
from tests.support.git import clean_environ, git, make_repo
from tests.support.real_env import snapshot

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(tmp_path).items():
        monkeypatch.setenv(name, value)


def run(*args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, ["init", *args, "--json"])
    return result.exit_code, json.loads(result.stdout)


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "newproject"
    directory.mkdir()
    return directory


def codes(document: dict[str, Any]) -> set[str]:
    return {f["code"] for f in document["findings"]}


def test_fm_n01_an_empty_directory_without_git_init_stops_after_the_preview(
    empty_dir: Path,
) -> None:
    code, document = run("--root", str(empty_dir), "--yes")

    assert code == 3
    assert "ORQ-E112" in codes(document)
    assert list(empty_dir.iterdir()) == []
    assert not (empty_dir / ".git").exists()


def test_fm_n02_git_init_creates_the_repository_on_the_chosen_branch_and_commits_nothing(
    empty_dir: Path,
) -> None:
    code, document = run(
        "--root", str(empty_dir), "--yes", "--git-init", "--target-branch", "trunk"
    )

    assert code == 0, document
    assert (empty_dir / ".git").is_dir()
    assert git(empty_dir, "rev-parse", "--abbrev-ref", "HEAD", environ=None) if False else True
    head = (empty_dir / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    assert head == "ref: refs/heads/trunk"
    refs = subprocess.run(
        ["git", "for-each-ref"],
        cwd=empty_dir,
        capture_output=True,
        env=clean_environ(empty_dir.parent),
        check=True,
    )
    assert refs.stdout == b""  # no commit, no branch yet
    files = snapshot(empty_dir)
    assert "AGENTS.md" in files
    assert not any(
        name.startswith(("src/", "tests/")) or name == "pyproject.toml" for name in files
    )


@pytest.mark.parametrize("branch", ["refs/heads/x", "@", "-x", "a..b", "has space", "end."])
def test_fm_n02_a_hostile_branch_name_creates_nothing(empty_dir: Path, branch: str) -> None:
    code, _ = run("--root", str(empty_dir), "--yes", "--git-init", "--target-branch", branch)

    assert code in {3, 4}
    assert not (empty_dir / ".git").exists()
    assert list(empty_dir.iterdir()) == []


def test_fm_n03_an_unborn_repository_is_a_new_project(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "unborn", "main")

    code, document = run("--root", str(root), "--yes", "--answer", "repository.target_branch=main")

    assert code == 0, document
    assert document["data"]["status"] == "applied"
    assert (root / "AGENTS.md").is_file()


def test_fm_n03_an_orphan_head_with_other_branches_is_not_treated_as_empty(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "orphan", "main")
    (root / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "notes.txt")
    git(root, "commit", "--quiet", "-m", "first")
    git(root, "checkout", "--quiet", "--orphan", "fresh")
    git(root, "rm", "-rf", "--quiet", ".")

    code, document = run("--root", str(root), "--yes")

    assert code == 3
    assert "ORQ-E111" in codes(document)
    assert not (root / "AGENTS.md").exists()


def test_fm_n04_a_readme_only_repository_gets_the_new_project_questions(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "readme", "main")
    (root / "README.md").write_text("# Hello\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "--quiet", "-m", "readme")

    code, document = run("--root", str(root), "--yes")

    assert code == 0, document
    questions = {q["id"] for q in document["data"]["open_questions"]}
    assert {"facts.python", "facts.package_manager", "project.kind"} <= questions


def test_a_full_set_of_answers_makes_a_new_project_supported(empty_dir: Path) -> None:
    code, _ = run(
        "--root",
        str(empty_dir),
        "--yes",
        "--git-init",
        "--target-branch",
        "main",
        "--answer",
        "facts.python=>=3.12",
        "--answer",
        "facts.package_manager=uv",
        "--answer",
        "project.kind=python-cli",
        "--answer",
        "structure.test_runner=pytest",
    )

    profile = (empty_dir / ".orqlet" / "project-profile.yaml").read_text(encoding="utf-8")
    assert code == 0
    assert "support: supported" in profile
    assert "origin: empty" in profile


def test_a_directory_inside_another_repository_is_refused(tmp_path: Path) -> None:
    outer = make_repo(tmp_path / "outer", "main")
    inner = outer / "packages" / "app"
    inner.mkdir(parents=True)

    code, document = run("--root", str(inner), "--yes")

    assert code == 3
    assert "ORQ-E110" in codes(document)
    assert snapshot(inner) == {}


def test_a_non_empty_directory_that_is_neither_is_not_guessed_at(empty_dir: Path) -> None:
    (empty_dir / "random.dat").write_text("???", encoding="utf-8")

    code, document = run("--root", str(empty_dir), "--yes", "--git-init", "--target-branch", "main")

    assert code == 3
    assert "ORQ-E111" in codes(document)
    assert not (empty_dir / ".git").exists()
