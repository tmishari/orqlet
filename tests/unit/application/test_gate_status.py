"""`gate status`: what an artifact was written against, and whether that still holds."""

from __future__ import annotations

from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.vcs import CommitSummary, RepoState
from orqlet.application.usecases.gate_status import current_bound, gate_status
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.validation import Collector, ValidateServices, ValidationResult
from orqlet.domain.findings import Verdict
from orqlet.domain.paths import CanonicalPath
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED
from tests.support.artifacts import (
    AS_IS,
    BASE,
    DESIGN,
    LATER,
    PLAN,
    SOURCE,
    TASK,
    as_is,
    design,
    design_files,
    dump,
    header,
    plan,
    with_front_matter,
)
from tests.support.init_env import Env
from tests.support.trees import repo

pytestmark = pytest.mark.unit

FILES = {"src/pkg/mod.py": SOURCE, "docs/guide.md": b"# Guide\n"}


def installed(*, other: dict[str, dict[str, bytes]] | None = None, commits: bool = True) -> Env:
    revisions = {BASE: FILES, **(other or {})} if commits else {}
    env = Env(
        project=repo("uv_fastapi"),
        vcs=FakeVcs(
            RepoState.HAS_COMMITS,
            branch="main",
            commits=(CommitSummary(BASE, "base"),) if commits else (),
            committed=FILES if commits else {},
            revisions=revisions,
        ),
    )
    assert init_project(env.services(), InitOptions(assume_yes=True)).status == "applied"
    return env


def services(env: Env) -> ValidateServices:
    return ValidateServices(
        project=env.project, vcs=env.vcs, loader=StrictYamlLoader(), workflow=PINNED
    )


def codes(result: ValidationResult) -> list[str]:
    return sorted(finding.code for finding in result.findings)


def matching_header(env: Env, **bound: Any) -> dict[str, Any]:
    values = current_bound(services(env), Collector())
    document = header(base=values.base_revision or BASE)
    document["workflow_version"] = values.workflow_version
    document["protected_set_digest"] = values.protected_set_digest
    document["bound"].update(
        {
            "standards_lock_hash": values.standards_lock_hash,
            "applicable_rules_hash": values.applicable_rules_hash,
            "profile_version": values.profile_version,
            **bound,
        }
    )
    return document


def write_task(env: Env, **header_bound: Any) -> None:
    head = matching_header(env, **header_bound)
    as_is_document = as_is()
    as_is_document["header"] = head

    def put(path: str, data: bytes) -> None:
        env.project.write_atomic(CanonicalPath.parse(path), data)

    put(AS_IS, with_front_matter(as_is_document))
    for path, data in design_files().items():
        put(path, data)
    design_document = design()
    design_document["header"] = head
    put(DESIGN, dump(design_document).encode())
    plan_document = plan()
    plan_document["header"] = head
    put(PLAN, dump(plan_document).encode())


def test_without_a_task_it_prints_the_inputs_an_artifact_header_records() -> None:
    result = gate_status(services(installed()))

    bound = result.data["bound"]
    assert result.verdict is Verdict.PASS
    assert isinstance(bound, dict)
    assert bound["base_revision"] == BASE
    assert len(str(bound["protected_set_digest"])) == 64
    assert len(str(bound["standards_lock_hash"])) == 64
    assert bound["profile_version"] == 1
    assert bound["workflow_version"] == "0.1.0"


def test_the_bound_inputs_are_the_same_on_every_run() -> None:
    env = installed()

    assert gate_status(services(env)).data == gate_status(services(env)).data


def test_a_repository_without_a_commit_cannot_bind_anything() -> None:
    result = gate_status(services(installed(commits=False)))

    assert result.verdict is Verdict.NOT_RUN
    assert "no commit" in result.not_run[0]


def test_a_directory_that_was_never_initialised_is_a_failure() -> None:
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))

    result = gate_status(services(env))

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E390" in codes(result)


def test_a_task_whose_artifacts_are_current_passes_with_no_not_run_reason() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 ("PASS ... when no artifact is stale, no
    error was found and no other check was skipped"); plan.yaml P-1 AC-1; component.md BC-8."""
    env = installed()
    write_task(env)

    result = gate_status(services(env), TASK)

    assert result.verdict is Verdict.PASS
    assert result.not_run == ()
    assert "ORQ-W390" not in codes(result)
    assert result.data["artifacts"] == {
        "as-is": {"found": True, "readable": True, "stale": []},
        "design": {"found": True, "readable": True, "stale": []},
        "plan": {"found": True, "readable": True, "stale": []},
    }


def test_the_approval_note_says_the_input_check_and_not_this_command_checks_approval() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (ORQ-I393 "stays as an info finding,
    worded as 'approval is checked by the input check, not by this command'")."""
    env = installed()
    write_task(env)

    result = gate_status(services(env), TASK)

    notes = [f for f in result.findings if f.code == "ORQ-I393"]
    assert len(notes) == 1
    assert notes[0].severity.value == "info"
    assert "approval" in notes[0].message
    assert "input check" in notes[0].message


def test_an_artifact_written_against_other_inputs_is_stale() -> None:
    env = installed()
    write_task(env, standards_lock_hash="0" * 64, applicable_rules_hash="1" * 64, profile_version=7)

    result = gate_status(services(env), TASK)

    assert "ORQ-W390" in codes(result)
    stale = result.data["artifacts"]["as-is"]["stale"]  # type: ignore[index]
    assert stale == ["standards_lock_hash", "applicable_rules_hash", "profile_version"]
    # AC-2. expected_behavior_source: ADR-002 decision 1 ("Stale input ... keep NOT_RUN").
    assert result.verdict is Verdict.NOT_RUN
    assert result.not_run


def test_a_changed_workflow_or_protected_set_makes_an_artifact_stale() -> None:
    env = installed()
    write_task(env)
    text = (
        env.project.read_bytes(CanonicalPath.parse(AS_IS))
        .decode()
        .replace("workflow_version: 0.1.0", "workflow_version: 0.0.9")
    )
    env.project.write_atomic(CanonicalPath.parse(AS_IS), text.encode())

    result = gate_status(services(env), TASK)

    assert result.data["artifacts"]["as-is"]["stale"] == ["workflow_version"]  # type: ignore[index]


def test_a_moved_head_that_changed_the_scope_makes_the_artifact_stale() -> None:
    changed = {**FILES, "src/pkg/mod.py": SOURCE + b"# edited\n"}
    env = installed(other={LATER: changed})
    write_task(env)
    env.vcs._commits = (CommitSummary(LATER, "later"), CommitSummary(BASE, "base"))
    env.vcs._revisions["HEAD"] = changed

    result = gate_status(services(env), TASK)

    assert result.data["artifacts"]["as-is"]["stale"] == ["base_revision"]  # type: ignore[index]
    assert "ORQ-W390" in codes(result)
    # AC-2. expected_behavior_source: ADR-002 decision 1 ("Stale input ... keep NOT_RUN").
    assert result.verdict is Verdict.NOT_RUN
    assert result.not_run


def test_a_moved_head_that_left_the_scope_alone_is_only_noted() -> None:
    changed = {**FILES, "docs/guide.md": b"# Guide, edited\n"}
    env = installed(other={LATER: changed})
    write_task(env)
    env.vcs._commits = (CommitSummary(LATER, "later"), CommitSummary(BASE, "base"))

    result = gate_status(services(env), TASK)

    assert "ORQ-I392" in codes(result)
    assert result.data["artifacts"]["plan"]["stale"] == []  # type: ignore[index]
    # AC-1. expected_behavior_source: ADR-002 decision 1 (nothing stale, nothing skipped: PASS).
    assert result.verdict is Verdict.PASS
    assert result.not_run == ()


def test_artifacts_that_do_not_exist_yet_are_noted_and_the_verdict_is_pass() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 2 and consequences ("A well-formed task
    name with no artifact moves from exit 5 to exit 0 ... the input check still stops on
    ORQ-I394"); plan.yaml P-1 AC-3."""
    result = gate_status(services(installed()), "not-started")

    assert result.verdict is Verdict.PASS
    assert result.not_run == ()
    assert codes(result).count("ORQ-I394") == 3
    assert "ORQ-I393" in codes(result)
    assert result.data["artifacts"]["plan"] == {"found": False}  # type: ignore[index]


def test_a_repository_without_a_commit_is_not_run_even_with_a_task() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 ("a missing revision ... keep NOT_RUN");
    plan.yaml P-1 AC-2."""
    result = gate_status(services(installed(commits=False)), TASK)

    assert result.verdict is Verdict.NOT_RUN
    assert "no commit" in result.not_run[0]


def test_gate_status_never_writes() -> None:
    env = installed()
    write_task(env)
    before = env.project.snapshot()

    gate_status(services(env), TASK)

    assert env.project.snapshot() == before
