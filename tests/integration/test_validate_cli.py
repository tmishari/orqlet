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
from orqlet.domain.facts import line_range_hash
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

    # AC-3. expected_behavior_source: ADR-002 decision 1 and consequences (a well-formed task name
    # with no artifact is exit 0 with PASS; the input check still stops on ORQ-I394).
    task_code, task = run("gate", "status", "demo", "--root", str(root))
    assert task_code == 0, task
    assert task["data"]["verdict"] == "PASS"
    assert not task["not_run"]
    assert codes(task).count("ORQ-I394") == 3
    assert "ORQ-I393" in codes(task)
    human = RUNNER.invoke(app, ["gate", "status", "demo", "--root", str(root)])
    assert human.exit_code == 0
    assert human.stdout.rstrip("\n").splitlines()[-1] == (
        "No artifact of task demo exists yet; check the task name unless you are starting research."
    )


@pytest.mark.parametrize("task", ["Bad_Name", "../x", "double--hyphen", "UPPER", "x" * 65])
def test_a_task_name_that_breaks_the_slug_rule_is_a_usage_error_before_anything_is_read(
    project: tuple[Path, str], task: str
) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 1 ("A task name that breaks the existing
    task-name rule ... is a usage error with exit 2, raised in the CLI layer against the `Slug`
    contract, as `models resolve` does for `--task`"). The repository is not initialised: without
    the check, the command would read the installation and exit 5 with ORQ-E390."""
    root, _ = project

    result = RUNNER.invoke(app, ["gate", "status", task, "--root", str(root), "--json"])

    assert result.exit_code == 2
    assert "ORQ-E390" not in result.stdout


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


# --- evidence cite with several pairs (task workflow-efficiency, P-2) --------------------------
# `expected_behavior_source`: ADR-001 decision 7 and EC-2 (`design/adr-001-check-reuse-and-
# rechecking.md` and `design/manifest.yaml`) and the acceptance criteria AC-1 to AC-5 of phase P-2
# in `plan.yaml`, all under docs/design/workflow-efficiency/.
NOTES = "alpha\nbeta\ngamma\n"
MOD = "src/pkg/mod.py"
NOTES_PATH = "docs/notes.md"


def snippet_of(path: str, lines: str, revision: str, content: str, start: int, end: int) -> str:
    digest = line_range_hash(content.encode(), start, end)
    return f"{{path: {path}, lines: {lines}, revision: {revision}, sha256: {digest}}}"


def entry_of(
    path: str, lines: str, revision: str, content: str, start: int, end: int
) -> dict[str, str]:
    digest = line_range_hash(content.encode(), start, end)
    return {"path": path, "lines": lines, "revision": revision, "sha256": digest}


@pytest.fixture
def two_files(project: tuple[Path, str]) -> tuple[Path, str]:
    """The project plus a second committed file; the head is the commit that holds both."""
    root, _ = project
    return root, commit_file(root, NOTES_PATH, NOTES)


def snippet_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("{path:")]


def test_two_pairs_exit_0_with_two_citations_in_order(two_files: tuple[Path, str]) -> None:
    """AC-1. expected_behavior_source: EC-2 ("data.citations lists one entry per pair in the
    given order, in today's entry shape"); plan P-2 AC-1."""
    root, head = two_files
    args = ["evidence", "cite", MOD, "1-2", NOTES_PATH, "3", "--root", str(root)]

    code, document = run(*args)

    assert code == 0, document
    assert document["data"]["verdict"] == "PASS"
    assert document["data"]["citations"] == [
        entry_of(MOD, "1-2", head, SOURCE.decode(), 1, 2),
        entry_of(NOTES_PATH, "3", head, NOTES, 3, 3),
    ]
    reverse_code, reverse = run(
        "evidence", "cite", NOTES_PATH, "3", MOD, "1-2", "--root", str(root)
    )
    assert reverse_code == 0, reverse
    assert reverse["data"]["citations"] == document["data"]["citations"][::-1]


def test_two_pairs_print_one_snippet_line_each_and_no_action_line(
    two_files: tuple[Path, str],
) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 7 ("The human text prints one snippet
    line per pair, its subject lists the files, and it has no action line"); EC-2."""
    root, head = two_files

    result = RUNNER.invoke(
        app, ["evidence", "cite", MOD, "1-2", NOTES_PATH, "3", "--root", str(root)]
    )

    assert result.exit_code == 0, result.output
    assert snippet_lines(result.stdout) == [
        snippet_of(MOD, "1-2", head, SOURCE.decode(), 1, 2),
        snippet_of(NOTES_PATH, "3", head, NOTES, 3, 3),
    ]
    first = result.stdout.splitlines()[0]
    assert first.startswith("PASS:")
    assert MOD in first
    assert NOTES_PATH in first
    lines = result.stdout.splitlines()
    assert not any(line.startswith(("Action needed", "No action needed")) for line in lines)


def test_a_single_pair_keeps_its_top_level_fields_and_lists_its_entry(
    project: tuple[Path, str],
) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 7 ("a single pair also keeps today's
    top-level fields"); EC-2; plan P-2 AC-2 (regression)."""
    root, head = project
    entry = entry_of(MOD, "1-2", head, SOURCE.decode(), 1, 2)

    code, document = run("evidence", "cite", MOD, "1-2", "--root", str(root))

    assert code == 0, document
    data = document["data"]
    assert {k: data[k] for k in ("path", "lines", "revision", "sha256")} == entry
    assert data["snippet"] == snippet_of(MOD, "1-2", head, SOURCE.decode(), 1, 2)
    assert data["citations"] == [entry]


def test_a_single_pair_prints_the_snippet_line_as_before(project: tuple[Path, str]) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 7 (a single pair "behaves as today");
    EC-2 ("a single pair also keeps today's top-level fields and text")."""
    root, head = project

    result = RUNNER.invoke(app, ["evidence", "cite", MOD, "1-2", "--root", str(root)])

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        f"PASS: {MOD}",
        "",
        snippet_of(MOD, "1-2", head, SOURCE.decode(), 1, 2),
    ]


@pytest.mark.parametrize(
    "arguments",
    [
        [MOD],
        [MOD, "1-2", NOTES_PATH],
    ],
    ids=["one argument", "three arguments"],
)
@pytest.mark.parametrize("json_output", [True, False], ids=["json", "text"])
def test_an_odd_number_of_arguments_is_a_usage_error_with_exit_2(
    two_files: tuple[Path, str], arguments: list[str], json_output: bool
) -> None:
    """AC-3. expected_behavior_source: EC-2 ("An odd number of arguments is a usage error with
    exit 2"); ADR-001 decision 7; plan P-2 AC-3 (nothing is cited)."""
    root, _ = two_files
    extra = ["--json"] if json_output else []

    result = RUNNER.invoke(app, ["evidence", "cite", *arguments, "--root", str(root), *extra])

    assert result.exit_code == 2
    assert "sha256" not in result.output


@pytest.mark.parametrize("good_first", [True, False], ids=["good first", "good last"])
@pytest.mark.parametrize(
    ("bad", "code"),
    [
        (("src/pkg/gone.py", "1"), "ORQ-E333"),
        ((MOD, "40-41"), "ORQ-E334"),
    ],
    ids=["missing file", "missing lines"],
)
def test_a_failing_pair_exits_5_and_the_other_pair_keeps_its_hash(
    two_files: tuple[Path, str], bad: tuple[str, str], code: str, good_first: bool
) -> None:
    """AC-4. expected_behavior_source: EC-2 ("A failing pair is reported with its finding and
    carries no revision and no sha256; the other pairs are still returned, and the exit status is
    5"); plan P-2 AC-4."""
    root, head = two_files
    good = (NOTES_PATH, "1-2")
    pairs = [good, bad] if good_first else [bad, good]
    arguments = [part for pair in pairs for part in pair]

    exit_code, document = run("evidence", "cite", *arguments, "--root", str(root))

    assert exit_code == 5
    assert document["data"]["verdict"] == "FAIL"
    assert [(f["code"], f["path"]) for f in document["findings"]] == [(code, bad[0])]
    entries = document["data"]["citations"]
    assert [e["path"] for e in entries] == [pair[0] for pair in pairs]
    good_entry = entries[0] if good_first else entries[1]
    bad_entry = entries[1] if good_first else entries[0]
    assert good_entry == entry_of(NOTES_PATH, "1-2", head, NOTES, 1, 2)
    assert bad_entry == {"path": bad[0], "lines": bad[1]}


def test_a_failing_pair_prints_a_snippet_line_only_for_the_cited_pair(
    two_files: tuple[Path, str],
) -> None:
    """AC-4. expected_behavior_source: ADR-001 decision 7 (the human text prints one snippet
    line per pair that was cited; a refused or failing pair carries no hash); EC-2."""
    root, head = two_files

    result = RUNNER.invoke(
        app, ["evidence", "cite", NOTES_PATH, "1-2", "src/pkg/gone.py", "1", "--root", str(root)]
    )

    assert result.exit_code == 5
    assert snippet_lines(result.stdout) == [snippet_of(NOTES_PATH, "1-2", head, NOTES, 1, 2)]
    assert "ORQ-E333" in result.stdout
    assert "src/pkg/gone.py" in result.stdout


def test_the_revision_option_applies_to_every_pair(two_files: tuple[Path, str]) -> None:
    """AC-5. expected_behavior_source: ADR-001 decision 7 ("`--revision` applies to every
    pair"); EC-2."""
    root, _ = two_files
    # At the commit before HEAD the notes file does not exist and the module is the same.
    earlier = git(root, "rev-parse", "HEAD~1").strip()

    code, document = run(
        "evidence", "cite", MOD, "1-2", MOD, "5", "--revision", earlier, "--root", str(root)
    )

    assert code == 0, document
    assert [e["revision"] for e in document["data"]["citations"]] == [earlier, earlier]
    assert document["data"]["citations"][1]["sha256"] == line_range_hash(SOURCE, 5, 5)

    absent_code, absent = run(
        "evidence", "cite", MOD, "1-2", NOTES_PATH, "1", "--revision", earlier, "--root", str(root)
    )

    assert absent_code == 5
    assert [(f["code"], f["path"]) for f in absent["findings"]] == [("ORQ-E333", NOTES_PATH)]
    assert absent["data"]["citations"][0]["revision"] == earlier
