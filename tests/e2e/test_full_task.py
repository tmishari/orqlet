"""The whole workflow on one real repository, from research to the records of a phase (Plan A).

A script plays the agent that the five skills describe. Every artifact is written from the values
the commands print, every validator must agree, and a change made after the fact must turn the
verdicts into NOT_RUN with a non-zero exit code. NOT_RUN is never success.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from orqlet.application.usecases.validation import content_hash
from tests.e2e import test_s9_acceptance as s9
from tests.support.artifacts import (
    TASK_DIR,
    as_is,
    design,
    design_files,
    dump,
    ledger,
    phase,
    plan,
    with_front_matter,
)
from tests.support.git import clean_environ, git

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

AS_IS = f"{TASK_DIR}/as-is.md"
DESIGN = f"{TASK_DIR}/design/manifest.yaml"
PLAN = f"{TASK_DIR}/plan.yaml"
LEDGER = f"{TASK_DIR}/questions.yaml"
NOTES = {
    "architecture-reviewer": f"{TASK_DIR}/reviews/architecture-reviewer-design.md",
    "security-reviewer": f"{TASK_DIR}/reviews/security-reviewer-design.md",
}


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(home).items():
        monkeypatch.setenv(name, value)


def cited(root: Path, lines: str) -> dict[str, Any]:
    code, result = s9.run(root, "evidence", "cite", "src/pkg/service.py", lines)
    assert code == 0, result
    return {key: result["data"][key] for key in ("path", "lines", "revision", "sha256")}


def reference(root: Path, path: str) -> str:
    _, hashed = s9.run(root, "evidence", "hash", path)
    return str(hashed["data"]["files"][0]["reference"])


def write_task(root: Path) -> None:
    """Research, design and plan, each passing its own validator, committed on `main`."""
    head = s9.bound_header(root)
    base = head["bound"]["base_revision"]
    s9.put(root, LEDGER, dump(ledger()))

    research = as_is(base=base)
    research["header"] = head
    research["facts"] = [
        {
            "id": "A-1",
            "kind": "structure",
            "statement": "The service module defines one function.",
            "evidence": [cited(root, "1")],
        }
    ]
    as_is_bytes = with_front_matter(research)
    s9.put(root, AS_IS, as_is_bytes)

    for path, data in design_files().items():
        s9.put(root, path, data)
    s9.put(
        root,
        f"{TASK_DIR}/design/container.md",
        "# Container\n\n```mermaid\nflowchart LR\n  A --> B\n```\n",
    )
    for role, note in NOTES.items():
        s9.put(root, note, f"# Design review by the {role}\n\nNo blocking finding.\n")
    manifest = design(
        base=base,
        as_is_bytes=as_is_bytes,
        change_class={"trigger": "D2", "declared": "D2", "effective": "D2"},
        scope={"paths": ["src/pkg/service.py"], "trust_boundaries": []},
        extractor_config={"public_api": {"packages": ["pkg"], "mode": "ast"}},
        expected_changes=[
            {
                "id": "EC-1",
                "surface": "public-api",
                "action": "add",
                "identity": "pkg.service.create_order",
                "expected_after": {
                    "kind": "signature",
                    "value": "def create_order(customer_id: str) -> str",
                },
                "verification": "extractor",
            }
        ],
        reviews=[{"role": role, "note": note} for role, note in NOTES.items()],
    )
    manifest["header"] = head
    manifest["artifacts"].append(
        {
            "id": "container",
            "kind": "c4-container",
            "path": f"{TASK_DIR}/design/container.md",
            "covers": "The service and what it talks to",
            "sha256": content_hash((root / f"{TASK_DIR}/design/container.md").read_bytes()),
        }
    )
    manifest_text = dump(manifest)
    s9.put(root, DESIGN, manifest_text)

    operations = [
        {"op": "modify", "path": "src/pkg/service.py", "why": "Add create_order"},
        {"op": "modify", "path": "docs/knowledge/service.md", "why": "Document it"},
    ]
    document = plan(
        base=base,
        design_bytes=manifest_text.encode(),
        knowledge_scope=["docs/knowledge/**"],
        phases=[phase(implements=["EC-1"], file_operations=operations)],
    )
    document["header"] = head
    s9.put(root, PLAN, dump(document))
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "research, design and plan")


@pytest.fixture(scope="module")
def template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("full-task")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ORQLET_DATA_DIR", str(base / "userdata"))
        for name, value in clean_environ(base).items():
            patch.setenv(name, value)
        root = s9.build_project(base / "w" / "project")
        git(root, "checkout", "--quiet", "main")
        write_task(root)
        git(root, "checkout", "--quiet", "-B", "feature")  # `main` keeps the approved task
        return root


@pytest.fixture
def project(template: Path, tmp_path: Path) -> Path:
    root = tmp_path / "w" / "project"
    shutil.copytree(template, root, symlinks=True)
    return root


def exit_code(root: Path, *args: str) -> tuple[int, dict[str, Any]]:
    return s9.run(root, *args)


def complete_phase(root: Path) -> None:
    """The phase as `orqlet-implement` describes it, then the review as `orqlet-review` does."""
    s9.implement(root)
    _, impact = s9.run(root, "knowledge", "impact", "demo", "P-1")
    _, first = s9.run(root, "review", "prepare", "demo", "P-1")
    s9.put(root, s9.KNOWLEDGE, dump(s9.knowledge_record(root, impact)))
    s9.put(root, s9.TEST, dump(s9.record_of_tests(first["data"])))
    s9.stage(root)
    _, prepared = s9.run(root, "review", "prepare", "demo", "P-1")
    s9.put(root, s9.REVIEW, dump(s9.review_record(root, prepared["data"])))
    s9.stage(root)


ARTIFACTS = {
    "ledger": ("validate", "ledger", LEDGER),
    "as-is": ("validate", "as-is", AS_IS),
    "design": ("validate", "design", DESIGN),
    "plan": ("validate", "plan", PLAN),
}
RECORDS = {
    "knowledge": ("validate", "knowledge", s9.KNOWLEDGE),
    "test": ("validate", "test", s9.TEST),
    "review": ("validate", "review", s9.REVIEW),
}


def validators(root: Path, runs: Mapping[str, tuple[str, ...]]) -> dict[str, tuple[int, str]]:
    """The exit code and the verdict of each validator, as a script would read them."""
    found = {}
    for name, args in runs.items():
        code, document = exit_code(root, *args)
        found[name] = (code, document["data"]["verdict"])
    return found


def test_research_design_and_plan_pass_their_validators_on_the_approved_branch(
    project: Path,
) -> None:
    git(project, "checkout", "--quiet", "main")

    result = validators(project, ARTIFACTS)

    assert result == {
        "ledger": (0, "PASS"),
        "as-is": (0, "PASS"),
        "design": (0, "PASS"),
        "plan": (0, "PASS"),
    }


def test_every_artifact_and_every_record_of_a_whole_task_passes_and_exits_zero(
    project: Path,
) -> None:
    complete_phase(project)

    assert validators(project, {**ARTIFACTS, **RECORDS}) == dict.fromkeys(
        (*ARTIFACTS, *RECORDS), (0, "PASS")
    )


def test_gate_status_for_the_phase_agrees_and_still_cannot_confirm_approval(project: Path) -> None:
    complete_phase(project)

    code, status = exit_code(project, "gate", "status", "demo", "--phase", "P-1")

    outcomes = {item["id"]: item["outcome"] for item in status["data"]["expected_changes"]}
    assert outcomes == {"EC-1": "implemented as designed"}
    assert [a["stale"] for a in status["data"]["artifacts"].values()] == [[], [], []]
    assert status["data"]["verdict"] == "NOT_RUN"
    assert code == 5
    assert any("host evidence" in reason for reason in status["not_run"])


def test_a_change_after_the_records_turns_every_record_into_not_run_with_a_non_zero_exit(
    project: Path,
) -> None:
    complete_phase(project)
    s9.put(project, "src/pkg/service.py", s9.SERVICE + s9.CREATE + "# edited after review\n")
    s9.stage(project, "src/pkg/service.py")

    after = validators(project, {**ARTIFACTS, **RECORDS})

    for record in RECORDS:
        assert after[record] == (5, "NOT_RUN"), record
    for artifact in ARTIFACTS:  # the task artifacts are not records of the change
        assert after[artifact] == (0, "PASS"), artifact
