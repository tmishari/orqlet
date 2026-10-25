"""`doctor`, `sync`, `explain`, `upgrade`, `rollback` and `release` through the real CLI."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.interface.cli.app import app
from tests.support.git import clean_environ, git, make_repo
from tests.support.real_env import snapshot
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "home"
    directory.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(directory).items():
        monkeypatch.setenv(name, value)
    return directory


@pytest.fixture
def root(tmp_path: Path, home: Path) -> Path:
    project = tmp_path / "w" / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", project)
    make_repo(project)
    git(project, "add", "-A")
    git(project, "commit", "--quiet", "-m", "initial")
    return project


def run(*args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout)


def init(root: Path) -> dict[str, Any]:
    code, document = run(
        "init", "--root", str(root), "--yes", "--answer", "repository.target_branch=main"
    )
    assert code == 0, document
    return document


def codes(document: dict[str, Any]) -> set[str]:
    return {finding["code"] for finding in document["findings"]}


def test_a_commands_that_need_an_installation_say_so_when_there_is_none(root: Path) -> None:
    for command in ("doctor", "sync", "explain", "upgrade"):
        code, document = run(command, "--root", str(root))

        assert code == 3, command
        assert "ORQ-E130" in codes(document)


def test_doctor_on_a_fresh_setup_has_no_errors_and_writes_nothing(root: Path) -> None:
    init(root)
    before = snapshot(root)

    code, document = run("doctor", "--root", str(root))

    assert code == 1  # warnings: the profile is a draft and facts are unknown
    assert not [f for f in document["findings"] if f["severity"] == "error"]
    assert snapshot(root) == before
    assert document["not_run"]


def test_fm_w02_an_edited_protected_file_fails_doctor_cannot_be_released_and_upgrade_restores_it(
    root: Path,
) -> None:
    init(root)
    rule = root / ".claude" / "rules" / "orqlet-workflow.md"
    original = rule.read_bytes()
    rule.write_text("weakened\n", encoding="utf-8")

    doctor_code, doctor = run("doctor", "--root", str(root))
    release_code, released = run(
        "release", ".claude/rules/orqlet-workflow.md", "--reason", "x", "--root", str(root), "--yes"
    )
    upgrade_code, _ = run("upgrade", "--root", str(root), "--yes")

    assert doctor_code == 5
    assert "ORQ-E150" in codes(doctor)
    assert release_code == 3
    assert "ORQ-E141" in codes(released)
    assert upgrade_code == 0
    assert rule.read_bytes() == original


def test_fm_w03_personal_names_are_listed_only_with_the_opt_in(root: Path, home: Path) -> None:
    init(root)
    (home / ".claude" / "skills" / "orqlet-research").mkdir(parents=True)
    (home / ".claude" / "skills" / "my-skill").mkdir(parents=True)

    _, quiet = run("sync", "--root", str(root))
    _, asked = run("sync", "--root", str(root), "--check-personal-names")

    assert quiet["data"]["listed_personal_names"] == []
    assert "ORQ-W100" not in codes(quiet)
    names = {item["name"] for item in asked["data"]["listed_personal_names"]}
    assert names == {"orqlet-research", "my-skill"}
    assert "ORQ-W100" in codes(asked)


def test_a_reserved_name_in_the_repository_that_is_not_in_the_manifest_fails_doctor(
    root: Path,
) -> None:
    init(root)
    (root / ".cursor" / "rules" / "orqlet-extra.mdc").write_text("x\n", encoding="utf-8")

    code, document = run("doctor", "--root", str(root))

    assert code == 5
    assert "ORQ-E153" in codes(document)


def test_sync_is_read_only_and_explain_lists_what_cannot_be_inspected(root: Path) -> None:
    init(root)
    before = snapshot(root)

    sync_code, _ = run("sync", "--root", str(root))
    explain_code, explanation = run("explain", "--root", str(root), "--phase", "design")

    assert sync_code == 0  # only notes: profile questions are doctor's business
    assert explain_code == 0
    assert snapshot(root) == before
    assert any("Cursor Team Rules" in item for item in explanation["data"]["cannot_be_inspected"])
    assert explanation["data"]["declared"]["workflow_version"] == str(
        PackagedWorkflow().release.version
    )
    assert explanation["not_run"]


def test_upgrade_check_on_an_unchanged_release_is_clean(root: Path) -> None:
    init(root)

    check_code, check = run("upgrade", "--root", str(root), "--check")
    apply_code, applied = run("upgrade", "--root", str(root), "--yes")

    assert (check_code, apply_code) == (0, 0)
    assert check["data"]["status"] == "up-to-date"
    assert applied["data"]["status"] == "up-to-date"


def test_rollback_of_init_removes_the_setup_and_restores_changed_files(
    root: Path, tmp_path: Path
) -> None:
    (root / "AGENTS.md").write_text("# Team notes\n", encoding="utf-8")
    git(root, "add", "AGENTS.md")
    git(root, "commit", "--quiet", "-m", "agents")
    before = snapshot(root)
    document = init(root)
    change_id = document["data"]["change_id"]

    dry_code, dry = run("rollback", change_id, "--root", str(root), "--dry-run")
    code, result = run("rollback", change_id, "--root", str(root), "--yes")

    assert dry_code == 0
    assert dry["data"]["status"] == "previewed"
    assert code == 0, result
    assert snapshot(root) == before


def test_rollback_without_approval_asks_for_it(root: Path) -> None:
    change_id = init(root)["data"]["change_id"]

    code, document = run("rollback", change_id, "--root", str(root))

    assert code == 4
    assert document["ok"] is False


def test_the_profile_commands_clear_doctor_s_warnings_and_can_be_undone(root: Path) -> None:
    init_document = RUNNER.invoke(
        app,
        [
            "init",
            "--root",
            str(root),
            "--yes",
            "--json",
            "--answer",
            "repository.target_branch=main",
        ],
    )
    assert init_document.exit_code == 0
    _, before = run("doctor", "--root", str(root))
    assert {"ORQ-W180", "ORQ-W181"} <= codes(before)

    answered_code, answered = run(
        "profile",
        "answer",
        "repository.branch_naming=feature/*",
        "repository.commit_convention=conventional commits",
        "--root",
        str(root),
        "--yes",
    )
    approved_code, approved = run(
        "profile", "approve", "--reviewer", "Ada", "--root", str(root), "--yes"
    )
    doctor_code, after = run("doctor", "--root", str(root))

    assert (answered_code, approved_code) == (0, 0), (answered, approved)
    assert not {"ORQ-W180", "ORQ-W181"} & codes(after)
    assert doctor_code == 0
    undo_code, _ = run("rollback", approved["data"]["change_id"], "--root", str(root), "--yes")
    assert undo_code == 0
    _, reopened = run("doctor", "--root", str(root))
    assert "ORQ-W180" in codes(reopened)


def test_profile_commands_refuse_clearly(root: Path) -> None:
    init(root)

    bad_code, bad = run("profile", "answer", "nonsense=1", "--root", str(root), "--yes")
    code, _ = run("profile", "approve", "--reviewer", "Ada", "--root", str(root))

    assert bad_code == 3
    assert "ORQ-E160" in codes(bad)
    assert code == 4  # approval needed and there is no terminal


def test_init_writes_the_commands_and_a_team_edit_to_one_survives_an_upgrade(root: Path) -> None:
    init(root)
    cursor = root / ".cursor" / "commands" / "orqlet-doctor.md"
    claude = root / ".claude" / "commands" / "orqlet-doctor.md"
    assert cursor.is_file()
    assert claude.is_file()
    _, healthy = run("doctor", "--root", str(root))
    assert "ORQ-W152" not in codes(healthy)

    cursor.write_text(cursor.read_text() + "\nAlso check the CI badge.\n")
    code, upgraded = run("upgrade", "--root", str(root), "--yes")
    _, after = run("doctor", "--root", str(root))

    assert code == 0, upgraded
    assert cursor.read_text().endswith("Also check the CI badge.\n")
    assert "ORQ-W152" in codes(after)  # reported, never overwritten
    assert claude.read_text().startswith("---\ndescription:")  # untouched
