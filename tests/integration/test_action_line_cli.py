"""The action line that ends the human text of `validate` and `gate status`, through the real CLI.

Task workflow-efficiency, phase P-1. Every test cites its `expected_behavior_source`. ADR-002 is
`adr-002-plain-cli-results.md` under docs/design/workflow-efficiency/design/ (decisions 1, 2 and 6),
AC-n are the acceptance criteria of phase P-1 in docs/design/workflow-efficiency/plan.yaml, and
BC-9 is the acceptance criterion of component.md section 6.

The tests reach behaviour only through the command line (`orqlet.interface.cli.app.app`), on real
Git repositories in `tmp_path`, with no network. They pin the final line of the human text, the
exit status and the JSON field names; they do not pin the wording of any finding message, and they
name no helper of the interface layer.

A PASS with warnings is reached with `validate as-is` (a fact that reads as advice gives ORQ-W338
and an unknown that cites a missing ledger gives ORQ-W339): no other validator gives a warning from
a cheap fixture. The `(s)` in each line is literal text, so there is no singular form to test.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from orqlet.interface.cli.app import app
from tests.support.artifacts import (
    AS_IS,
    LEDGER,
    SOURCE,
    as_is,
    dump,
    fact,
    header,
    ledger,
    question,
    with_front_matter,
)
from tests.support.git import clean_environ, commit_file, git, make_repo
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()
ACTION_PREFIXES = ("Action needed", "No action needed")
NOT_RUN_LINE = (
    "Action needed: resolve the not-run reason(s) above and run the command again, "
    "or have the person confirm them."
)
ENVELOPE_FIELDS = {"schema", "ok", "command", "orqlet_version", "data", "findings", "not_run"}


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(home).items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, str]:
    """A Git repository with two commits and no Orqlet installation."""
    root = make_repo(tmp_path / "project")
    commit_file(root, "src/pkg/__init__.py", "")
    head = commit_file(root, "src/pkg/mod.py", SOURCE.decode())
    return root, head


@pytest.fixture
def initialised(tmp_path: Path) -> Path:
    root = tmp_path / "w" / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "initial")
    result = RUNNER.invoke(
        app, ["init", "--root", str(root), "--yes", "--answer", "repository.target_branch=main"]
    )
    assert result.exit_code == 0, result.stdout
    return root


def human(root: Path, *args: str) -> tuple[int, list[str]]:
    """The exit status and the lines of the human text (the trailing newline is not a line)."""
    result = RUNNER.invoke(app, [*args, "--root", str(root)])
    return result.exit_code, result.stdout.rstrip("\n").splitlines()


def machine(root: Path, *args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, [*args, "--root", str(root), "--json"])
    return result.exit_code, json.loads(result.stdout)


def action_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith(ACTION_PREFIXES)]


def count(document: dict[str, Any], severity: str) -> int:
    return sum(1 for finding in document["findings"] if finding["severity"] == severity)


def write_ledger(root: Path, document: dict[str, Any]) -> None:
    target = root / LEDGER
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump(document))


def write_as_is(root: Path, head: str, **overrides: Any) -> None:
    document = as_is(base=head, **overrides)
    document["header"] = header(base=head)
    target = root / AS_IS
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(with_front_matter(document))


def advice_and_missing_ledger(head: str) -> dict[str, Any]:
    """Two warnings and no error: advice in a fact (ORQ-W338), a question that has no ledger."""
    return {
        "facts": [
            fact(1, "The module should be split into two.", revision=head),
            fact(2, "The module defines a class.", start=5, end=6, revision=head),
        ],
        "unknowns": [{"id": "U-1", "what": "x", "material": True, "question_ref": "Q-1"}],
    }


def expected_line(verdict: str, errors: int, warnings: int) -> str:
    """The rule of ADR-002 decision 2 for a `validate` command."""
    if verdict == "FAIL":
        return f"Action needed: fix the {errors} error(s) above, then run the command again."
    if verdict == "NOT_RUN":
        return NOT_RUN_LINE
    return "No action needed." + (f" Read the {warnings} warning(s) above." if warnings else "")


# --- one literal line for each verdict -----------------------------------------------------------


def test_a_passing_validator_ends_with_no_action_needed(project: tuple[Path, str]) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 2 ("Any other PASS: 'No action
    needed.'")."""
    root, _ = project
    write_ledger(root, ledger())

    code, lines = human(root, "validate", "ledger", LEDGER)

    assert code == 0
    assert lines[0] == f"PASS: {LEDGER}"
    assert lines[-1] == "No action needed."
    assert len(action_lines(lines)) == 1


def test_a_failing_validator_ends_with_the_number_of_errors(project: tuple[Path, str]) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 2 (FAIL: 'Action needed: fix the N
    error(s) above, then run the command again.'; N = the error findings). The ledger names
    another task (one error) and supersedes a question that does not exist (a second one)."""
    root, _ = project
    broken = ledger("other")
    broken["questions"] = [question(1, status="open", supersedes=["Q-9"])]
    write_ledger(root, broken)

    code, lines = human(root, "validate", "ledger", LEDGER)
    _, document = machine(root, "validate", "ledger", LEDGER)

    assert code == 5
    assert count(document, "error") == 2
    assert lines[-1] == "Action needed: fix the 2 error(s) above, then run the command again."
    assert len(action_lines(lines)) == 1


def test_a_not_run_validator_ends_with_the_not_run_action(tmp_path: Path) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 2 (NOT_RUN line). A repository without a
    commit cannot bind the AS-IS file to a revision, the case that test_validate_cli pins."""
    root = make_repo(tmp_path / "empty")
    write_as_is(root, "1" * 40)

    code, lines = human(root, "validate", "as-is", AS_IS)

    assert code == 5
    assert lines[0] == f"NOT_RUN: {AS_IS}"
    assert lines[-1] == NOT_RUN_LINE
    assert len(action_lines(lines)) == 1


def test_a_pass_with_warnings_adds_the_warning_count_on_the_same_line(
    project: tuple[Path, str],
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 2 ("On PASS with warnings, 'Read the N
    warning(s) above.' follows") and plan.yaml P-1 AC-4 (one line: 'No action needed. Read the 2
    warning(s) above.')."""
    root, head = project
    write_as_is(root, head, **advice_and_missing_ledger(head))

    code, lines = human(root, "validate", "as-is", AS_IS)
    _, document = machine(root, "validate", "as-is", AS_IS)

    assert code == 0
    assert document["data"]["verdict"] == "PASS"
    assert count(document, "warning") == 2
    assert lines[-1] == "No action needed. Read the 2 warning(s) above."
    assert len(action_lines(lines)) == 1


# --- every validator --------------------------------------------------------------------------

MISSING = "docs/design/demo/missing.yaml"
VALIDATORS = {
    "as-is": ("validate", "as-is", MISSING),
    "design": ("validate", "design", MISSING),
    "plan": ("validate", "plan", MISSING),
    "ledger": ("validate", "ledger", MISSING),
    "resources": ("validate", "resources"),
    "integrations": ("validate", "integrations"),
    "model-policy": ("validate", "model-policy"),
    "review": ("validate", "review", MISSING),
    "test": ("validate", "test", MISSING),
    "knowledge": ("validate", "knowledge", MISSING),
}


@pytest.mark.parametrize("name", VALIDATORS)
def test_every_validator_ends_with_exactly_one_action_line_for_its_verdict(
    project: tuple[Path, str], name: str
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 2 ("The human text of `gate status` and of
    every validator ends with exactly one action line ... from the verdict and the finding
    counts") and plan.yaml P-1 AC-4 (the ten commands). Each validator runs on a repository with
    no Orqlet installation; whatever verdict that gives, the last line follows from the verdict
    and the counts that the same run prints in `--json`."""
    root, _ = project
    args = VALIDATORS[name]

    _, lines = human(root, *args)
    _, document = machine(root, *args)

    verdict = document["data"]["verdict"]
    errors, warnings = count(document, "error"), count(document, "warning")
    assert lines[-1] == expected_line(verdict, errors, warnings)
    assert len(action_lines(lines)) == 1


# --- the commands that print no action line ---------------------------------------------------

NO_ACTION_LINE = {
    "evidence cite": ("evidence", "cite", "src/pkg/mod.py", "1-2"),
    "evidence cite of a missing file": ("evidence", "cite", "src/pkg/missing.py", "1-2"),
    "evidence hash": ("evidence", "hash", "src/pkg/mod.py"),
    "evidence hash of a missing file": ("evidence", "hash", "src/pkg/missing.py"),
    "knowledge impact": ("knowledge", "impact", "demo", "P-1"),
    "review prepare": ("review", "prepare", "demo", "P-1"),
    "conventions check": ("conventions", "check"),
}


@pytest.mark.parametrize("name", NO_ACTION_LINE)
def test_these_commands_print_no_action_line_whatever_their_verdict(
    project: tuple[Path, str], name: str
) -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 2 ("`evidence cite` and `evidence hash`
    render without an action line") and plan.yaml P-1 AC-6 (also `knowledge impact`, `review
    prepare` and `conventions check`). The repository has no installation, so several of these
    do not pass; none of them may print an action line either way."""
    root, _ = project

    result = RUNNER.invoke(app, [*NO_ACTION_LINE[name], "--root", str(root)])

    assert result.exit_code != 2, result.stdout  # a usage error would prove nothing
    assert result.stdout.strip()
    assert "Action needed" not in result.stdout
    assert "No action needed" not in result.stdout


def test_a_passing_evidence_command_prints_no_action_line(project: tuple[Path, str]) -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 2 (`evidence cite` and `evidence hash`
    render without an action line); the PASS case, where an action line would otherwise be
    'No action needed.'."""
    root, _ = project

    for args in (
        ("evidence", "cite", "src/pkg/mod.py", "1-2"),
        ("evidence", "hash", "src/pkg/mod.py"),
    ):
        code, lines = human(root, *args)
        assert code == 0
        assert not action_lines(lines)


# --- gate status --------------------------------------------------------------------------------


def test_gate_status_without_a_task_ends_with_no_action_needed(initialised: Path) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 2 ("Any other PASS: 'No action needed.'";
    the approval sentence is for a PASS of `gate status` with a task) and plan.yaml P-1 AC-5."""
    code, lines = human(initialised, "gate", "status")

    assert code == 0
    assert lines[-1] == "No action needed."
    assert len(action_lines(lines)) == 1


def test_gate_status_of_an_uninitialised_repository_ends_with_the_fail_line(
    project: tuple[Path, str],
) -> None:
    """AC-5. expected_behavior_source: plan.yaml P-1 AC-5 ("on FAIL/NOT_RUN the lines of AC-4
    apply first") and ADR-002 decision 2 (FAIL line)."""
    root, _ = project

    code, lines = human(root, "gate", "status")
    _, document = machine(root, "gate", "status")

    assert code == 5
    assert document["data"]["verdict"] == "FAIL"
    errors = count(document, "error")
    assert errors >= 1
    assert lines[-1] == (
        f"Action needed: fix the {errors} error(s) above, then run the command again."
    )


# --- the JSON envelopes do not change ----------------------------------------------------------


def test_the_json_of_a_validator_keeps_its_fields_and_holds_no_action_line(
    project: tuple[Path, str],
) -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 6 ("The fields of the JSON envelope ... do
    not change") and decision 2 ("rendered in the interface layer"; no `next_action` field)."""
    root, _ = project
    write_ledger(root, ledger())

    result = RUNNER.invoke(app, ["validate", "ledger", LEDGER, "--root", str(root), "--json"])
    document = json.loads(result.stdout)

    assert result.exit_code == 0
    assert set(document) == ENVELOPE_FIELDS
    assert document["command"] == "validate ledger"
    assert document["ok"] is True
    assert document["findings"] == []
    assert document["not_run"] == []
    assert set(document["data"]) == {
        "verdict",
        "questions",
        "open",
        "conflicts",
        "unruled_conflicts",
    }
    assert "ction needed" not in result.stdout


def test_the_json_of_gate_status_keeps_its_fields_and_holds_no_action_line(
    initialised: Path,
) -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 6 (the JSON envelope's fields do not
    change) and the data that `gate status` returns today (gate_status.py: verdict, bound, task,
    artifacts)."""
    result = RUNNER.invoke(app, ["gate", "status", "demo", "--root", str(initialised), "--json"])
    document = json.loads(result.stdout)

    assert result.exit_code == 0
    assert set(document) == ENVELOPE_FIELDS
    assert document["command"] == "gate status"
    assert document["ok"] is True
    assert set(document["data"]) == {"verdict", "bound", "task", "artifacts"}
    assert set(document["data"]["bound"]) == {
        "base_revision",
        "standards_lock_hash",
        "applicable_rules_hash",
        "profile_version",
        "workflow_version",
        "protected_set_digest",
    }
    assert document["data"]["task"] == "demo"
    assert "ction needed" not in result.stdout
