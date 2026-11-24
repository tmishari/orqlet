"""`doctor`, `sync`, `explain`, `upgrade`, `rollback` and `release` through the real CLI."""

from __future__ import annotations

import json
import re
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


RULE = (
    "  - id: {id}\n    level: {level}\n    text: A rule of the test.\n    enforcement: guidance\n"
)
RULE_LEVELS = ("MUST", "SHOULD", "MAY")


def write_rules(path: Path, prefix: str, count: int) -> None:
    """A rules file with `count` rules whose ids are `<prefix>-<n>`, the levels taking turns."""
    rules = "".join(
        RULE.format(id=f"{prefix}-{n}", level=RULE_LEVELS[n % len(RULE_LEVELS)])
        for n in range(1, count + 1)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"schema: orqlet.rules/v1\nrules:\n{rules}", encoding="utf-8")


def explain_text(root: Path) -> tuple[int, str, str]:
    """The exit status, stdout and stderr of `explain --phase design` without `--json`."""
    result = RUNNER.invoke(app, ["explain", "--root", str(root), "--phase", "design"])
    return result.exit_code, result.stdout, result.stderr


def standards_section(stdout: str) -> list[str]:
    """The lines from the `N rule(s) apply:` header up to the next blank line."""
    lines = stdout.splitlines()
    start = next(n for n, line in enumerate(lines) if line.endswith("rule(s) apply:"))
    end = next((n for n in range(start, len(lines)) if not lines[n].strip()), len(lines))
    return lines[start:end]


def test_explain_text_lists_each_limit_once_and_does_not_echo_findings_to_stderr(
    root: Path,
) -> None:
    """expected_behavior_source: workflow-efficiency plan P-5 AC-2 ("explain prints its limits
    once"); ADR-002 decision 4 ("`explain` lists its limits once"). Each limit message of the
    JSON findings is in the combined stdout and stderr exactly once."""
    init(root)

    exit_code, stdout, stderr = explain_text(root)
    _, document = run("explain", "--root", str(root), "--phase", "design")

    limits = [f["message"] for f in document["findings"] if f["code"].startswith("ORQ-L")]
    assert exit_code == 0
    assert limits
    combined = f"{stdout}\n{stderr}"
    for message in limits:
        assert combined.count(message) == 1, message
    assert "ORQ-L" not in stderr


def test_explain_text_lists_a_model_finding_once(root: Path) -> None:
    """expected_behavior_source: workflow-efficiency plan P-5 AC-2 ("Model-policy findings
    (ORQ-W540, W545, W546, E541) that the text's `Model selection:` section prints also appear
    once"); ADR-002 decision 4. A policy that is no mapping gives ORQ-E541; its message is in the
    `Model selection:` section and nowhere else."""
    init(root)
    (root / ".orqlet" / "model-policy.yaml").write_bytes(b"- a\n- b\n")

    _, stdout, stderr = explain_text(root)
    _, document = run("explain", "--root", str(root), "--phase", "design")

    messages = [f["message"] for f in document["findings"] if f["code"] == "ORQ-E541"]
    assert messages
    combined = f"{stdout}\n{stderr}"
    for message in messages:
        assert combined.count(message) == 1, message
    assert stdout.index("Model selection:") < stdout.index(messages[0])
    assert "ORQ-E541" not in stderr


def test_explain_text_shows_the_standards_as_a_count_per_source(root: Path) -> None:
    """expected_behavior_source: workflow-efficiency plan P-5 AC-2 ("the standards as a count per
    source, without rule ids or levels"; the header `<N> rule(s) apply:` stays; one line per rule
    source, sorted by source name, with its count, equal to the counts of `--json`
    `data.rules[].source`); ADR-002 decision 4."""
    init(root)
    write_rules(root / ".prompts" / "rules.yaml", "ZZTEAM", 3)
    write_rules(root / ".orqlet" / "rules.yaml", "ZZPROJECT", 2)

    _, stdout, _ = explain_text(root)
    _, document = run("explain", "--root", str(root), "--phase", "design")

    rules = document["data"]["rules"]
    counts = {
        source: sum(1 for rule in rules if rule["source"] == source)
        for source in sorted({rule["source"] for rule in rules})
    }
    assert len(rules) == 5
    assert len(counts) == 2
    section = standards_section(stdout)
    assert section[0] == f"{len(rules)} rule(s) apply:"
    lines = section[1:]
    assert len(lines) == len(counts)
    for line, (source, count) in zip(lines, counts.items(), strict=True):  # sorted by source
        assert source in line
        assert re.findall(r"\d+", line) == [str(count)], line
    assert sum(int(re.findall(r"\d+", line)[0]) for line in lines) == len(rules)


def test_explain_text_has_no_rule_id_and_no_level_word_in_the_standards(root: Path) -> None:
    """expected_behavior_source: workflow-efficiency plan P-5 AC-2 ("The text contains NO rule id
    and NO level word in that part"; "without rule ids or levels"); ADR-002 decision 4 ("rule ids
    and levels stay in `--json`")."""
    init(root)
    write_rules(root / ".prompts" / "rules.yaml", "ZZTEAM", 3)
    write_rules(root / ".orqlet" / "rules.yaml", "ZZPROJECT", 2)

    _, stdout, _ = explain_text(root)
    _, document = run("explain", "--root", str(root), "--phase", "design")

    section = "\n".join(standards_section(stdout))
    assert document["data"]["rules"]
    assert "ORQLET-" not in section
    for rule in document["data"]["rules"]:
        assert rule["id"] not in stdout
    for level in RULE_LEVELS:
        assert re.search(rf"\b{level}\b", section) is None


def test_explain_json_still_lists_each_rule_with_id_level_source_and_text(root: Path) -> None:
    """expected_behavior_source: workflow-efficiency plan P-5 AC-2 ("its --json still lists each
    rule with id, level, source and text"; "its model-selection section is unchanged"); ADR-002
    decision 4 and decision 6 (the fields of the JSON envelope do not change). The findings still
    hold the limits and the model findings."""
    init(root)
    write_rules(root / ".prompts" / "rules.yaml", "ZZTEAM", 3)
    write_rules(root / ".orqlet" / "rules.yaml", "ZZPROJECT", 2)
    (root / ".orqlet" / "model-policy.yaml").write_bytes(b"- a\n- b\n")

    code, document = run("explain", "--root", str(root), "--phase", "design")

    assert code == 0
    rules = document["data"]["rules"]
    assert {rule["id"] for rule in rules} == {f"ZZTEAM-{n}" for n in (1, 2, 3)} | {
        f"ZZPROJECT-{n}" for n in (1, 2)
    }
    for rule in rules:
        assert set(rule) == {"id", "level", "source", "text"}
        assert rule["level"] in RULE_LEVELS
    assert {rule["source"] for rule in rules} == {"prompts", "project"}
    assert {f["code"] for f in document["findings"]} >= {"ORQ-L001", "ORQ-L006", "ORQ-E541"}
    assert isinstance(document["data"]["declared"]["model_selection"], list)
    for entry in document["data"]["declared"]["model_selection"]:
        assert set(entry) == {"kind", "target", "client", "source", "setting"}


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
