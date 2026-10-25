"""The `.prompts/` seed through the real CLI (proposal section 12.8)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from orqlet.interface.cli.app import app
from tests.support.git import clean_environ, commit_file, git, make_repo
from tests.support.trees import FIXTURES

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


@pytest.fixture
def root(tmp_path: Path) -> Path:
    project = tmp_path / "w" / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", project)
    make_repo(project)
    git(project, "add", "-A")
    git(project, "commit", "--quiet", "-m", "initial")
    return project


def init(root: Path, *extra: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, ["init", "--root", str(root), "--yes", "--json", *extra])
    return result.exit_code, json.loads(result.stdout)


def test_the_seed_is_written_once_and_recorded_as_team_owned(root: Path) -> None:
    code, _ = init(root)

    assert code == 0
    assert sorted(p.name for p in (root / ".prompts").iterdir()) == [
        "README.md",
        "foundations.md",
        "rules.yaml",
    ]
    lock = (root / ".orqlet" / "generated.lock.yaml").read_text("utf-8")
    assert lock.count("owner: seeded") >= 3
    assert "seeded_sha256" in lock


def test_the_seed_can_go_to_another_folder_and_the_profile_says_where(root: Path) -> None:
    code, _ = init(root, "--prompts-dir", "docs/standards")

    assert code == 0
    assert (root / "docs" / "standards" / "README.md").is_file()
    assert not (root / ".prompts").exists()
    assert "docs/standards" in (root / ".orqlet" / "project-profile.yaml").read_text("utf-8")


def test_an_existing_prompts_folder_is_never_rewritten(root: Path) -> None:
    commit_file(root, ".prompts/README.md", "Our own readme\n")
    commit_file(root, ".prompts/api-standards.md", "API rules\n")

    code, document = init(root)

    assert code == 0
    assert (root / ".prompts" / "README.md").read_text("utf-8") == "Our own readme\n"
    assert (root / ".prompts" / "api-standards.md").read_text("utf-8") == "API rules\n"
    assert (root / ".prompts" / "foundations.md").is_file()
    proposals = [p.name for p in (root / ".orqlet" / "proposals").iterdir()]
    assert any("README" in name for name in proposals)
    assert any(f["code"] == "ORQ-I031" for f in document["findings"])


def test_the_seed_carries_no_company_policy_and_an_empty_rule_list(root: Path) -> None:
    init(root)

    foundations = (root / ".prompts" / "foundations.md").read_text("utf-8")
    rules = (root / ".prompts" / "rules.yaml").read_text("utf-8")
    assert "Orqlet writes no company policy" in foundations
    assert "rules: []" in rules


def test_a_rule_added_to_the_seeded_rules_file_is_served_and_becomes_a_scoped_rule_file(
    root: Path,
) -> None:
    init(root)
    rules = root / ".prompts" / "rules.yaml"
    rules.write_text(
        "schema: orqlet.rules/v1\nrules:\n"
        "  - id: TEAM-001\n    level: MUST\n    text: Services log with correlation ids.\n"
        "    scope: {paths: ['src/**']}\n",
        encoding="utf-8",
    )

    served = RUNNER.invoke(
        app, ["standards", "for", "--root", str(root), "--path", "src/app/main.py", "--json"]
    )
    code, _ = init(root)  # already initialised: nothing changes
    upgraded = RUNNER.invoke(app, ["upgrade", "--root", str(root), "--yes", "--json"])

    rule_ids = [r["id"] for r in json.loads(served.stdout)["data"]["rules"]]
    assert rule_ids == ["TEAM-001"]
    assert code == 0
    assert upgraded.exit_code == 0, upgraded.stdout
    assert (root / ".claude" / "rules" / "orqlet-team-001.md").is_file()
    assert (root / ".cursor" / "rules" / "orqlet-team-001.mdc").is_file()
    assert rules.read_text(encoding="utf-8").startswith(
        "schema: orqlet.rules/v1\nrules:\n  - id: TEAM-001"
    )


def test_a_custom_standards_folder_is_the_one_that_is_read(root: Path) -> None:
    init(root, "--prompts-dir", "docs/standards")
    (root / "docs" / "standards" / "rules.yaml").write_text(
        "schema: orqlet.rules/v1\nrules:\n  - {id: DOC-1, level: MUST, text: Write docs.}\n",
        encoding="utf-8",
    )

    served = RUNNER.invoke(app, ["standards", "for", "--root", str(root), "--json"])

    assert [r["id"] for r in json.loads(served.stdout)["data"]["rules"]] == ["DOC-1"]
