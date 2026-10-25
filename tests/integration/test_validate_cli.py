"""`validate` and `gate status` through the real CLI, on real Git repositories."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.interface.cli.app import app
from tests.support.artifacts import (
    AS_IS,
    SOURCE,
    as_is,
    evidence,
    fact,
    header,
    with_front_matter,
)
from tests.support.git import clean_environ, commit_file, git, make_repo
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(home).items():
        monkeypatch.setenv(name, value)


def run(*args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout)


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, str]:
    root = make_repo(tmp_path / "project")
    commit_file(root, "src/pkg/__init__.py", "")
    head = commit_file(root, "src/pkg/mod.py", SOURCE.decode())
    return root, head


def write_as_is(root: Path, head: str, **overrides: Any) -> None:
    document = as_is(base=head, **overrides)
    document["facts"] = [
        fact(1, revision=head),
        fact(2, "The module defines a class.", start=5, end=6, revision=head),
    ]
    document["header"] = header(base=head)
    target = root / AS_IS
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(with_front_matter(document))


def codes(document: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in document["findings"]]


def test_a_sound_as_is_file_passes_against_real_git(project: tuple[Path, str]) -> None:
    root, head = project
    write_as_is(root, head)

    code, document = run("validate", "as-is", AS_IS, "--root", str(root))

    assert code == 0, document
    assert document["data"]["verdict"] == "PASS"
    assert document["data"]["facts"] == 2


def test_evidence_that_does_not_match_the_commit_fails_with_exit_5(
    project: tuple[Path, str],
) -> None:
    root, head = project
    write_as_is(root, head)
    (root / "src/pkg/mod.py").write_text("changed in the working tree only\n")  # HEAD is unchanged
    text = (root / AS_IS).read_text()
    (root / AS_IS).write_text(text.replace(evidence(revision=head)["sha256"], "f" * 64, 1))

    code, document = run("validate", "as-is", AS_IS, "--root", str(root))

    assert code == 5
    assert document["data"]["verdict"] == "FAIL"
    assert "ORQ-E335" in codes(document)


def test_a_repository_without_a_commit_is_not_run_and_exits_5(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "empty")
    write_as_is(root, "1" * 40)

    code, document = run("validate", "as-is", AS_IS, "--root", str(root))

    assert code == 5
    assert document["data"]["verdict"] == "NOT_RUN"
    assert document["not_run"]
    assert document["ok"] is False


def test_a_new_commit_in_the_scope_makes_the_file_stale(project: tuple[Path, str]) -> None:
    root, head = project
    write_as_is(root, head)
    git(root, "commit", "--quiet", "--allow-empty", "-m", "empty")
    commit_file(root, "src/pkg/mod.py", SOURCE.decode() + "# edited\n")
    newest = git(root, "rev-parse", "HEAD").strip()

    code, document = run("validate", "as-is", AS_IS, "--against", newest, "--root", str(root))

    assert code == 5
    assert document["data"]["verdict"] == "NOT_RUN"
    assert "ORQ-W341" in codes(document)


def test_an_unsafe_path_is_a_finding_not_a_traceback(project: tuple[Path, str]) -> None:
    root, _ = project

    code, document = run("validate", "as-is", "../outside.md", "--root", str(root))

    assert code == 5
    assert codes(document) == ["ORQ-E320"]


def test_the_human_summary_opens_with_the_verdict_and_the_uncertainty(
    project: tuple[Path, str],
) -> None:
    root, head = project
    write_as_is(root, head)

    result = RUNNER.invoke(app, ["validate", "as-is", AS_IS, "--root", str(root)])

    lines = result.stdout.splitlines()
    assert lines[0] == f"PASS: {AS_IS}"
    assert lines[2].startswith("1 unknown(s) (1 material), 0 contradiction(s), 2 fact(s)")


def test_the_ledger_command_reads_a_ledger_file(project: tuple[Path, str]) -> None:
    root, _ = project
    target = root / "docs/design/demo/questions.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("schema: orqlet.question-ledger/v1\ntask: demo\n")

    code, document = run(
        "validate", "ledger", "docs/design/demo/questions.yaml", "--root", str(root)
    )

    assert code == 0, document
    assert document["data"]["questions"] == 0


def test_gate_status_prints_the_inputs_of_an_initialised_repository(tmp_path: Path) -> None:
    root = tmp_path / "w" / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "initial")
    init_code, _ = run(
        "init", "--root", str(root), "--yes", "--answer", "repository.target_branch=main"
    )
    assert init_code == 0

    code, document = run("gate", "status", "--root", str(root))

    assert code == 0, document
    bound = document["data"]["bound"]
    assert bound["base_revision"] == git(root, "rev-parse", "HEAD").strip()
    assert bound["workflow_version"]
    assert document["data"]["verdict"] == "PASS"

    task_code, task = run("gate", "status", "demo", "--root", str(root))
    assert task_code == 5
    assert task["data"]["verdict"] == "NOT_RUN"


def test_gate_status_in_an_uninitialised_repository_fails(project: tuple[Path, str]) -> None:
    root, _ = project

    code, document = run("gate", "status", "--root", str(root))

    assert code == 5
    assert "ORQ-E390" in codes(document)


def registered_commands(group: typer.Typer, prefix: str = "") -> set[str]:
    names = set()
    for command in group.registered_commands:
        callback = command.callback
        name = command.name or (callback.__name__ if callback is not None else "")
        names.add(f"{prefix}{name.removesuffix('_command').replace('_', '-')}".strip())
    for sub in group.registered_groups:
        if sub.typer_instance is not None:
            names |= registered_commands(sub.typer_instance, f"{prefix}{sub.name} ")
    return names


def test_the_list_of_implemented_commands_matches_the_application() -> None:
    assert registered_commands(app) == set(IMPLEMENTED_COMMANDS)


def test_evidence_cite_prints_what_validate_as_is_then_accepts(project: tuple[Path, str]) -> None:
    root, head = project
    code, cited = run("evidence", "cite", "src/pkg/mod.py", "1-2", "--root", str(root))
    assert code == 0, cited
    assert cited["data"]["revision"] == head
    write_as_is(root, head)
    text = (root / AS_IS).read_text()
    assert cited["data"]["sha256"] in text  # the same hash the builder computed independently

    check_code, checked = run("validate", "as-is", AS_IS, "--root", str(root))

    assert check_code == 0, checked


def test_evidence_hash_prints_references_for_files(project: tuple[Path, str]) -> None:
    root, _ = project
    code, document = run("evidence", "hash", "src/pkg/mod.py", "--root", str(root))

    assert code == 0, document
    (item,) = document["data"]["files"]
    assert item["reference"] == f"src/pkg/mod.py#{item['sha256']}"
