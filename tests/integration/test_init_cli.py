"""`orqlet init` end to end through the real CLI, real files and real Git."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from orqlet.interface.cli.app import app
from tests.support.git import clean_environ, commit_file, git, make_repo
from tests.support.real_env import snapshot
from tests.support.render import COMMAND_NAMES, ROLE_NAMES, skill_files
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "userdata"
    monkeypatch.setenv("ORQLET_DATA_DIR", str(directory))
    for name, value in clean_environ(tmp_path).items():
        monkeypatch.setenv(name, value)
    return directory


def existing_project(tmp_path: Path, fixture: str = "uv_fastapi") -> Path:
    root = tmp_path / "work" / "project"
    shutil.copytree(FIXTURES / "repos" / fixture, root)
    make_repo(root)
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "initial")
    return root


def run(*args: str) -> tuple[int, dict[str, Any], str]:
    result = RUNNER.invoke(app, ["init", *args, "--json"])
    return result.exit_code, json.loads(result.stdout), result.stdout


def test_an_existing_project_is_set_up_and_nothing_is_committed(
    tmp_path: Path, data_dir: Path
) -> None:
    root = existing_project(tmp_path)
    head = git(root, "rev-parse", "HEAD")
    before = snapshot(root)

    code, document, _ = run(
        "--root", str(root), "--yes", "--answer", "repository.target_branch=main"
    )

    assert code == 0, document
    assert document["ok"] is True
    assert git(root, "rev-parse", "HEAD") == head
    after = snapshot(root)
    assert set(before) < set(after)
    assert all(after[name] == data for name, data in before.items())
    assert {".orqlet/generated.lock.yaml", "AGENTS.md", ".prompts/rules.yaml"} <= set(after)


def test_a_second_run_changes_nothing_and_says_so(tmp_path: Path, data_dir: Path) -> None:
    root = existing_project(tmp_path)
    run("--root", str(root), "--yes")
    first = snapshot(root)

    code, document, _ = run("--root", str(root), "--yes")

    assert code == 0
    assert document["data"]["status"] == "already-initialised"
    assert snapshot(root) == first


def test_without_approval_nothing_is_written_and_the_exit_code_says_input_is_needed(
    tmp_path: Path, data_dir: Path
) -> None:
    root = existing_project(tmp_path)
    before = snapshot(root)

    code, document, _ = run("--root", str(root))

    assert code == 4
    assert document["ok"] is False
    assert snapshot(root) == before


def test_dry_run_shows_the_plan_and_writes_nothing(tmp_path: Path, data_dir: Path) -> None:
    root = existing_project(tmp_path)
    before = snapshot(root)

    code, document, _ = run("--root", str(root), "--dry-run")

    assert code == 0
    assert document["data"]["status"] == "previewed"
    assert len(document["data"]["writes"]) > 5
    assert snapshot(root) == before


def test_the_journal_and_backups_live_outside_the_repository(
    tmp_path: Path, data_dir: Path
) -> None:
    root = existing_project(tmp_path)
    (root / "AGENTS.md").write_text("# Team notes\n", encoding="utf-8")

    run("--root", str(root), "--yes")

    assert not (root / ".orqlet" / "journal").exists()
    stored = [p for p in data_dir.rglob("*") if p.is_file()]
    assert any(p.name.endswith(".json") for p in stored)
    assert any(p.read_bytes() == b"# Team notes\n" for p in stored)


def test_no_write_lands_outside_the_root_and_ancestor_files_are_untouched(
    tmp_path: Path, data_dir: Path
) -> None:
    root = existing_project(tmp_path)
    ancestor = root.parent / "CLAUDE.md"
    ancestor.write_text("shared by other projects\n", encoding="utf-8")
    sibling = root.parent / "other.txt"
    sibling.write_text("not ours\n", encoding="utf-8")
    outside_before = snapshot(tmp_path / "work") | {}

    code, document, _ = run("--root", str(root), "--yes")

    assert code == 0
    assert ancestor.read_text(encoding="utf-8") == "shared by other projects\n"
    assert sibling.read_text(encoding="utf-8") == "not ours\n"
    outside_files = {
        k: v for k, v in snapshot(tmp_path / "work").items() if not k.startswith("project/")
    }
    assert outside_files == {
        k: v for k, v in outside_before.items() if not k.startswith("project/")
    }
    assert any(f["code"] == "ORQ-I020" for f in document["findings"])


def test_a_tracked_symlinked_agent_folder_is_refused_not_followed(
    tmp_path: Path, data_dir: Path
) -> None:
    root = existing_project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    try:
        (root / ".claude").symlink_to(elsewhere, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot create symbolic links")

    code, document, _ = run("--root", str(root), "--yes")

    assert code == 3
    assert list(elsewhere.iterdir()) == []
    assert document["ok"] is False


def test_the_json_envelope_validates_against_its_contract(tmp_path: Path, data_dir: Path) -> None:
    from orqlet.application.contracts.cli_result import CliResult

    root = existing_project(tmp_path)
    _, document, _ = run("--root", str(root), "--dry-run")

    CliResult.model_validate(document)


def test_existing_files_with_other_line_endings_survive(tmp_path: Path, data_dir: Path) -> None:
    root = existing_project(tmp_path)
    commit_file(root, ".github/pull_request_template.md", "# PR\r\n\r\nChecklist\r\n")
    original = (root / ".github" / "pull_request_template.md").read_bytes()

    run("--root", str(root), "--yes")

    text = (root / ".github" / "pull_request_template.md").read_bytes()
    assert text.startswith(b"# PR\r\n")
    assert text.endswith(b"Checklist\r\n")
    assert b"orqlet:begin orqlet-workflow" in text
    assert b"\n" not in text.replace(b"\r\n", b"")
    assert original != text


def test_the_human_output_prints_the_change_id_that_rollback_needs(
    tmp_path: Path, data_dir: Path
) -> None:
    root = existing_project(tmp_path)

    result = RUNNER.invoke(app, ["init", "--root", str(root), "--yes"])

    line = next(ln for ln in result.stdout.splitlines() if ln.startswith("Change id: "))
    change_id = line.split()[2]
    undo = RUNNER.invoke(app, ["rollback", change_id, "--root", str(root), "--yes"])
    assert undo.exit_code == 0, undo.stdout


def test_a_monorepo_is_set_up_with_every_service_s_technologies(
    tmp_path: Path, data_dir: Path
) -> None:
    root = existing_project(tmp_path, "monorepo")

    code, document, _ = run(
        "--root", str(root), "--yes", "--answer", "repository.target_branch=main"
    )

    assert code == 0, document
    profile = (root / ".orqlet" / "project-profile.yaml").read_text(encoding="utf-8")
    assert "scope: apiserver" in profile
    assert "scope: services/billing" in profile
    assert "name: Gin" in profile
    assert "facts.python" not in {q["id"] for q in document["data"]["open_questions"]}
    assert not (root / ".worktrees" / "skip" / ".orqlet").exists()


def test_init_warns_when_the_gitignore_hides_the_generated_agent_files(
    tmp_path: Path, data_dir: Path
) -> None:
    root = existing_project(tmp_path)
    commit_file(root, ".gitignore", ".claude/*\n!.claude/settings.json\n")

    code, document, _ = run("--root", str(root), "--yes")

    warned = {f["path"] for f in document["findings"] if f["code"] == "ORQ-W097"}
    assert code == 0
    required = {
        ".claude/CLAUDE.md",
        ".claude/rules/orqlet-workflow.md",
        *(f".claude/commands/orqlet-{name}.md" for name in COMMAND_NAMES),
        *skill_files(".claude/skills"),
        *(f".claude/agents/{name}.md" for name in ROLE_NAMES),
    }
    assert warned == required
    status = git(root, "status", "--short", "--untracked-files=all")
    assert ".claude/CLAUDE.md" not in status  # the warning is true: Git does not see it
