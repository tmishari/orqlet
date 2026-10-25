"""`orqlet standards for` through the real command line (Typer's CliRunner)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from orqlet import __version__
from orqlet.application.contracts.cli_result import CliResult
from orqlet.interface.cli.app import app
from tests.support.trees import FIXTURES

pytestmark = pytest.mark.integration

RUNNER = CliRunner()
PACKS = str(FIXTURES / "packs")


def repo_args(name: str) -> list[str]:
    return ["--root", str(FIXTURES / "repos" / name), "--packs-dir", PACKS]


def test_version_flag() -> None:
    result = RUNNER.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"orqlet {__version__}"


def test_no_arguments_shows_help() -> None:
    result = RUNNER.invoke(app, [])

    assert "standards" in result.stdout


def test_human_output_lists_rules_and_packs() -> None:
    result = RUNNER.invoke(app, ["standards", "for", *repo_args("uv_fastapi"), "--phase", "design"])

    assert result.exit_code == 0
    assert "SAMPLE-003" in result.stdout
    assert "Packs: sample@1.0.0, web@2.1.0" in result.stdout


def test_json_output_is_the_documented_envelope() -> None:
    result = RUNNER.invoke(app, ["standards", "for", *repo_args("uv_fastapi"), "--json"])

    assert result.exit_code == 0
    document = json.loads(result.stdout)
    CliResult.model_validate(document)  # the envelope contract accepts its own output
    assert document["schema"] == "orqlet.cli-result/v1"
    assert document["ok"] is True
    assert document["data"]["rules"][0]["id"] == "SAMPLE-001"
    assert len(document["data"]["applicable_rules_hash"]) == 64


def test_the_json_output_is_byte_identical_on_every_run() -> None:
    args = ["standards", "for", *repo_args("uv_fastapi"), "--json"]

    assert RUNNER.invoke(app, args).stdout == RUNNER.invoke(app, args).stdout


def test_a_javascript_project_is_recognised_but_gets_no_rules_it_did_not_ask_for() -> None:
    result = RUNNER.invoke(app, ["standards", "for", *repo_args("js_only"), "--json"])

    document = json.loads(result.stdout)
    names = {t["name"] for t in document["data"]["technologies"]}
    assert result.exit_code == 0
    assert {"JavaScript", "Express"} <= names
    assert document["data"]["rules"] == []  # the sample packs are for Python
    assert {s["id"] for s in document["data"]["skipped"]} == {"sample", "web"}


def test_a_repository_with_no_recognised_technology_gets_an_info_finding() -> None:
    result = RUNNER.invoke(app, ["standards", "for", *repo_args("empty"), "--json"])

    document = json.loads(result.stdout)
    assert result.exit_code == 0
    assert document["data"]["technologies"] == []
    assert document["findings"][0]["code"] == "ORQ-I001"


def test_a_monorepo_reports_each_service_s_technologies_with_their_folder() -> None:
    result = RUNNER.invoke(app, ["standards", "for", *repo_args("monorepo"), "--json"])

    found = {(t["scope"], t["name"]) for t in json.loads(result.stdout)["data"]["technologies"]}
    assert (".", "PostgreSQL") in found
    assert ("apiserver", "Gin") in found
    assert ("services/billing", "FastAPI") in found
    assert ("dag-worker", "Apache Airflow") in found


def test_a_missing_root_is_a_usage_error() -> None:
    result = RUNNER.invoke(app, ["standards", "for", "--root", "/definitely/not/here"])

    assert result.exit_code == 2


def test_a_traversal_in_path_is_refused_with_a_code(tmp_path: Path) -> None:
    result = RUNNER.invoke(
        app, ["standards", "for", "--root", str(tmp_path), "--path", "../etc/passwd", "--json"]
    )

    document = json.loads(result.stdout)
    assert result.exit_code == 3
    assert document["ok"] is False
    assert document["findings"][0]["code"] == "ORQ-E107"


def test_a_pack_that_breaks_its_contract_is_refused_not_ignored(tmp_path: Path) -> None:
    packs = tmp_path / "packs" / "bad"
    packs.mkdir(parents=True)
    (packs / "pack.yaml").write_text("schema: orqlet.standards-pack/v1\nid: bad\nextra: 1\n")
    project = tmp_path / "project"
    project.mkdir()

    result = RUNNER.invoke(
        app,
        ["standards", "for", "--root", str(project), "--packs-dir", str(packs.parent), "--json"],
    )

    document = json.loads(result.stdout)
    assert result.exit_code == 3
    assert document["findings"][0]["code"] == "ORQ-E103"
