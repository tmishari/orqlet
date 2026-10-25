"""FM-P01 to FM-P03 and FM-P06 through the real CLI. (FM-P04 is the upgrade, tested in P-8.)"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from orqlet.domain.blocks import parse_blocks
from orqlet.interface.cli.app import app
from tests.support.git import clean_environ, commit_file, git, make_repo
from tests.support.real_env import snapshot
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


def block_names(text: str) -> list[str]:
    return [block.name for block in parse_blocks(text)]


def test_fm_p01_no_template_creates_the_file_with_the_workflow_block_and_reports_unknown_team_text(
    root: Path,
) -> None:
    (root / ".github").mkdir()

    code, _ = init(root)

    text = (root / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert code == 0
    assert block_names(text) == ["orqlet-workflow"]
    assert "team-template-unknown" in (root / ".orqlet" / "project-profile.yaml").read_text("utf-8")


def test_fm_p02_an_existing_template_keeps_its_text_and_gains_the_blocks(root: Path) -> None:
    commit_file(root, ".github/pull_request_template.md", "# Summary\n\n## Testing\n\nSteps.\n")

    init(root)

    text = (root / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert text.startswith("# Summary\n")
    assert text.endswith("\n## Testing\n\nSteps.\n")
    assert block_names(text) == ["orqlet-workflow"]


def test_fm_p02_a_template_that_cannot_be_edited_safely_is_left_alone_with_a_named_conflict(
    root: Path,
) -> None:
    broken = "# T\n<!-- orqlet:begin orqlet-workflow x -->\nnever closed\n"
    commit_file(root, ".github/pull_request_template.md", broken)

    code, document = init(root)

    assert code == 1
    assert (root / ".github" / "pull_request_template.md").read_text(encoding="utf-8") == broken
    assert any(f["code"] == "ORQ-W080" for f in document["findings"])


@pytest.mark.parametrize(
    "body",
    [
        "# T\n\n```\nunclosed fence\n",
        "# T\n\n=======\n\ntext\n",
        "\ufeff# T\n\ntext\n",
        "# T\r\n\r\ntext\r\n",
        "# T\n\n<!-- orqlet:begin a -->\n<!-- orqlet:begin b -->\n",
        "# T\n\n<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> branch\n",
    ],
)
def test_fm_p03_hostile_templates_give_a_clean_result_or_a_named_conflict_never_a_partial_write(
    root: Path, body: str
) -> None:
    path = root / ".github" / "pull_request_template.md"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(body.encode("utf-8"))

    code, _ = init(root)

    after = path.read_text(encoding="utf-8")
    if after != body:
        assert block_names(after) == ["orqlet-workflow"]
        assert after.count("orqlet:begin") == 1
        assert code == 0
    else:
        assert code == 1  # a named conflict, and the live file is untouched


def test_fm_p03_a_second_run_is_empty_and_the_file_is_byte_identical(root: Path) -> None:
    init(root)
    before = snapshot(root)

    code, document = init(root)

    assert code == 0
    assert document["data"]["status"] == "already-initialised"
    assert snapshot(root) == before


def test_fm_p06_several_templates_are_asked_about_and_the_others_stay_byte_identical(
    root: Path,
) -> None:
    commit_file(root, "pull_request_template.md", "# Root template\n")
    commit_file(root, ".github/PULL_REQUEST_TEMPLATE/bug.md", "# Bug\n")
    commit_file(root, ".github/PULL_REQUEST_TEMPLATE/feature.md", "# Feature\n")
    before = snapshot(root)

    code, document = init(root)

    assert any(f["code"] == "ORQ-W050" for f in document["findings"])
    for name in ("pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE/bug.md"):
        assert snapshot(root)[name] == before[name]
    assert code == 0


def test_fm_p06_the_chosen_templates_receive_the_blocks_and_the_choice_is_recorded(
    root: Path,
) -> None:
    commit_file(root, "pull_request_template.md", "# Root template\n")
    commit_file(root, ".github/PULL_REQUEST_TEMPLATE/bug.md", "# Bug\n")
    commit_file(root, ".github/PULL_REQUEST_TEMPLATE/feature.md", "# Feature\n")

    code, _ = init(
        root,
        "--answer",
        "repository.pull_requests.template.targets=.github/PULL_REQUEST_TEMPLATE/bug.md",
    )

    assert code == 0
    assert "orqlet:begin" in (root / ".github/PULL_REQUEST_TEMPLATE/bug.md").read_text("utf-8")
    assert (root / ".github/PULL_REQUEST_TEMPLATE/feature.md").read_text("utf-8") == "# Feature\n"
    assert (root / "pull_request_template.md").read_text("utf-8") == "# Root template\n"
    profile = (root / ".orqlet" / "project-profile.yaml").read_text("utf-8")
    assert "PULL_REQUEST_TEMPLATE/bug.md" in profile


def test_a_template_that_is_not_utf8_is_a_conflict_not_a_rewrite(root: Path) -> None:
    path = root / ".github" / "pull_request_template.md"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes("# Caf\u00e9\n".encode("latin-1"))

    code, _ = init(root)

    assert code == 1
    assert path.read_bytes() == "# Caf\u00e9\n".encode("latin-1")
