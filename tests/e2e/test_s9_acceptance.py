"""Slice S9 end to end: a phase with its records, on real Git, through the commands an agent runs.

A script plays the agent. It stages a change, asks `knowledge impact` and `review prepare` for the
bindings, writes the three records from what they print and checks that every validator agrees.
Then it changes one input at a time and watches the right records go stale (FM-B, FM-K, FM-A).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from orqlet.application.usecases.validation import content_hash
from orqlet.domain.facts import line_range_hash
from orqlet.interface.cli.app import app
from tests.support.artifacts import (
    TASK_DIR,
    as_is,
    design,
    design_files,
    dump,
    fact,
    header,
    ledger,
    phase,
    plan,
    with_front_matter,
)
from tests.support.git import clean_environ, git, make_repo
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()
HASH = "a" * 64
SERVICE = "def existing() -> None: ...\n"
CREATE = "def create_order(customer_id: str) -> str: ...\n"
KNOWLEDGE_DOC = "# Service\n\nThe code lives in `src/pkg/service.py`.\n"
DRAFT = KNOWLEDGE_DOC + "\n## Orders\n\n`create_order` returns an order id for a customer.\n"
REVIEW = f"{TASK_DIR}/reviews/architecture-reviewer-P-1-r1.yaml"
TEST = f"{TASK_DIR}/tests/P-1.yaml"
KNOWLEDGE = f"{TASK_DIR}/knowledge/P-1.yaml"


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(home).items():
        monkeypatch.setenv(name, value)


def run(root: Path, *args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, [*args, "--root", str(root), "--json"])
    return result.exit_code, json.loads(result.stdout)


def put(root: Path, path: str, data: bytes | str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data.encode() if isinstance(data, str) else data)


def stage(root: Path, *paths: str) -> None:
    git(root, "add", "--", *paths) if paths else git(root, "add", "-A")


def codes(document: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in document["findings"]]


def bound_header(root: Path) -> dict[str, Any]:
    _, status = run(root, "gate", "status")
    values = status["data"]["bound"]
    document = header("demo", values["base_revision"])
    document["workflow_version"] = values["workflow_version"]
    document["protected_set_digest"] = values["protected_set_digest"]
    document["bound"].update(
        standards_lock_hash=values["standards_lock_hash"],
        applicable_rules_hash=values["applicable_rules_hash"],
        profile_version=values["profile_version"],
    )
    return document


@pytest.fixture(scope="module")
def project_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One initialised repository, built once: its first commit holds the task and the agent."""
    base = tmp_path_factory.mktemp("s9-template")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ORQLET_DATA_DIR", str(base / "userdata"))
        for name, value in clean_environ(base).items():
            patch.setenv(name, value)
        return build_project(base / "w" / "project")


@pytest.fixture
def project(project_template: Path, tmp_path: Path) -> Path:
    """A private copy of the template, so a test can stage and change what it likes."""
    root = tmp_path / "w" / "project"
    shutil.copytree(project_template, root, symlinks=True)
    return root


def build_project(root: Path) -> Path:
    """An initialised repository whose first commit holds the task, the agent and the knowledge."""
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    put(root, "src/pkg/__init__.py", "")
    put(root, "src/pkg/service.py", SERVICE)
    put(root, "docs/knowledge/service.md", KNOWLEDGE_DOC)
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "initial")
    code, _ = run(root, "init", "--yes", "--answer", "repository.target_branch=main")
    assert code == 0
    head = bound_header(root)

    put(
        root,
        ".orqlet/knowledge.yaml",
        "schema: orqlet.knowledge/v2\n"
        "sources:\n  - {kind: docs, scope: project, globs: ['docs/knowledge/**']}\n"
        "write_scope:\n  - {globs: ['docs/knowledge/**'], kinds: [docs]}\n",
    )
    as_is_document = as_is(base=head["bound"]["base_revision"])
    as_is_document["header"] = head
    as_is_document["facts"] = [fact(1, revision=head["bound"]["base_revision"])]
    put(root, f"{TASK_DIR}/as-is.md", with_front_matter(as_is_document))
    put(root, f"{TASK_DIR}/questions.yaml", dump(ledger()))
    for path, data in design_files().items():
        put(root, path, data)
    manifest = design(
        base=head["bound"]["base_revision"],
        change_class={"trigger": "D2", "declared": "D2", "effective": "D2"},
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
    )
    manifest["header"] = head
    put(root, f"{TASK_DIR}/design/manifest.yaml", dump(manifest))
    plan_document = plan(
        base=head["bound"]["base_revision"],
        knowledge_scope=["docs/knowledge/**"],
        phases=[phase(implements=["EC-1"])],
    )
    plan_document["header"] = head
    put(root, f"{TASK_DIR}/plan.yaml", dump(plan_document))
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "task, agent and knowledge configuration")
    git(root, "checkout", "--quiet", "-b", "feature")  # `main` stays where the work began
    return root


def implement(root: Path) -> None:
    """The phase's change: a new public function and the drafted knowledge, staged."""
    put(root, "src/pkg/service.py", SERVICE + CREATE)
    put(root, "docs/knowledge/service.md", DRAFT)
    stage(root, "src/pkg/service.py", "docs/knowledge/service.md")


def staged_line_hash(root: Path, path: str, line: int) -> str:
    data = git(root, "show", f":{path}").encode()
    return line_range_hash(data, line, line)


def knowledge_record(root: Path, impact: dict[str, Any]) -> dict[str, Any]:
    data = impact["data"]
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(data["candidates"], start=1):
        evidence = [
            {
                "kind": "code",
                "ref": "src/pkg/service.py:2",
                "sha256": staged_line_hash(root, "src/pkg/service.py", 2),
            }
        ]
        if item["kind"] == "reference":
            entries.append(
                {
                    "id": f"K-{index}",
                    "candidate_ref": item["id"],
                    "action": "correct",
                    "scope": "project",
                    "path": "docs/knowledge/service.md",
                    "claims": [{"id": "CL-1", "anchor": "## Orders", "evidence": evidence}],
                }
            )
        else:
            entries.append(
                {
                    "id": f"K-{index}",
                    "candidate_ref": item["id"],
                    "action": "unaffected",
                    "scope": "project",
                    "reason": "Covered by the correction of the service page.",
                    "evidence": evidence,
                }
            )
    return {
        "schema": "orqlet.knowledge-impact/v1",
        "task": "demo",
        "phase": "P-1",
        "review_input": data["review_input"],
        "outcome": "updated",
        "analysis": {
            "command": "orqlet knowledge impact",
            "orqlet_version": "0.2.0",
            "candidates_digest": data["candidates_digest"],
            "candidate_count": data["candidate_count"],
            "input": "pre-draft-tree",
            "views": ["committed:HEAD"],
            "index_state": "not-used",
        },
        "entries": entries,
    }


def record_of_tests(prepared: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "orqlet.test-record/v1",
        "task": "demo",
        "phase": "P-1",
        "review_input": prepared["review_inputs"]["test"],
        "verdict": "PASS",
        "evidence_kind": "claimed",
        "commands": [{"id": "tests", "exit_code": 0, "summary": "3 passed", "result_digest": HASH}],
        "acceptance_coverage": [{"ac": "AC-1", "check_ref": "tests", "result": "pass"}],
    }


def review_record(root: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    agent = (root / ".claude/agents/orqlet-arch-reviewer.md").read_bytes()
    block = prepared["review_inputs"]["review"]["architecture-reviewer"]["claude-code"]
    return {
        "schema": "orqlet.review-result/v1",
        "task": "demo",
        "phase": "P-1",
        "role": "architecture-reviewer",
        "round": 1,
        "verdict": "PASS",
        "assurance": "advisory",
        "review_input": block,
        "agent": {
            "binding_ref": "orqlet-arch-reviewer",
            "definition_sha256": content_hash(agent),
            "client": "claude-code",
        },
        "coder_binding": {"client": "claude-code"},
        "independence": "I1",
        "capability_limits": ["read-only is advisory"],
        "applicability": {"examined": ["src/pkg/service.py"], "conclusion": "findings"},
        "findings": [],
        "self_check": {
            "schema": "orqlet.self-check/v1",
            "checked_against": {"role": "architecture-reviewer", "phase": "implement"},
            "checks": [{"what": "packet read", "how": "orqlet review prepare", "result": "pass"}],
        },
    }


@pytest.fixture
def phase_done(project: Path) -> dict[str, Any]:
    """The change staged and all three records written and staged with it.

    The order is the workflow's: the tester's and the knowledge records first, staged, then the
    packet, then the review, which binds the two records it examined as `evidence_inputs`.
    """
    implement(project)
    _, impact = run(project, "knowledge", "impact", "demo", "P-1")
    _, first = run(project, "review", "prepare", "demo", "P-1")
    put(project, KNOWLEDGE, dump(knowledge_record(project, impact)))
    put(project, TEST, dump(record_of_tests(first["data"])))
    stage(project)
    _, prepared = run(project, "review", "prepare", "demo", "P-1")
    put(project, REVIEW, dump(review_record(project, prepared["data"])))
    stage(project)
    return {"impact": impact, "prepared": prepared["data"]}


def verdicts(root: Path) -> dict[str, str]:
    result = {}
    for name, path in (("knowledge", KNOWLEDGE), ("test", TEST), ("review", REVIEW)):
        _, document = run(root, "validate", name, path)
        result[name] = document["data"]["verdict"]
    return result


# --- the expected change --------------------------------------------------------------------
def test_fm_a01_the_declared_public_function_is_implemented_as_designed(project: Path) -> None:
    implement(project)

    code, status = run(project, "gate", "status", "demo", "--phase", "P-1")

    outcomes = {item["id"]: item["outcome"] for item in status["data"]["expected_changes"]}
    assert outcomes == {"EC-1": "implemented as designed"}
    assert "ORQ-E450" not in codes(status)
    assert "ORQ-E451" not in codes(status)
    assert code == 5  # approval is never confirmed offline


def test_fm_a02_a_second_public_function_is_additional_and_blocks(project: Path) -> None:
    implement(project)
    put(project, "src/pkg/service.py", SERVICE + CREATE + "def refund() -> None: ...\n")
    stage(project, "src/pkg/service.py")

    _, status = run(project, "gate", "status", "demo", "--phase", "P-1")

    outcomes = [item["outcome"] for item in status["data"]["expected_changes"]]
    assert outcomes == ["implemented as designed", "additional"]
    assert "ORQ-E451" in codes(status)


# --- the knowledge step ---------------------------------------------------------------------
def test_knowledge_impact_lists_the_candidates_from_the_pre_draft_tree(project: Path) -> None:
    implement(project)

    code, impact = run(project, "knowledge", "impact", "demo", "P-1")

    assert code == 0, impact
    kinds = sorted(c["kind"] for c in impact["data"]["candidates"])
    assert kinds == ["expected-change", "public-symbol", "reference"]
    assert impact["data"]["review_input"]["covers"] == [
        "code_tests",
        "knowledge",
        "plan",
        "standards",
        "candidates",
    ]


def test_a_draft_cannot_change_its_own_candidate_list(project: Path) -> None:
    implement(project)
    _, before = run(project, "knowledge", "impact", "demo", "P-1")
    put(project, "docs/knowledge/service.md", DRAFT + "\nMore about `src/pkg/service.py`.\n")
    stage(project, "docs/knowledge/service.md")

    _, after = run(project, "knowledge", "impact", "demo", "P-1")

    assert after["data"]["candidates_digest"] == before["data"]["candidates_digest"]


def test_a_complete_phase_passes_all_three_validators(
    phase_done: dict[str, Any], project: Path
) -> None:
    assert verdicts(project) == {"knowledge": "PASS", "test": "PASS", "review": "PASS"}


def test_fm_b01_committing_the_records_with_the_code_does_not_change_the_digests(
    phase_done: dict[str, Any], project: Path
) -> None:
    before = verdicts(project)
    git(project, "commit", "--quiet", "-m", "the phase and its evidence")

    after = verdicts(project)

    assert before == after == {"knowledge": "PASS", "test": "PASS", "review": "PASS"}


def test_review_prepare_exports_the_staged_snapshot_outside_the_repository(
    phase_done: dict[str, Any], project: Path
) -> None:
    prepared = phase_done["prepared"]

    packet = Path(prepared["path"])
    assert project not in packet.parents
    assert (packet / "snapshot/src/pkg/service.py").read_text() == SERVICE + CREATE
    assert "+def create_order" in (packet / "diff.patch").read_text()
    assert (packet / "context/plan.yaml").is_file()
    manifest = json.loads((packet / "MANIFEST.json").read_text())
    assert manifest["label"] == "staged"
    assert [p for p, _ in manifest["files"] if p == "context/plan.yaml"] == ["context/plan.yaml"]


def test_a_packet_is_written_once(project: Path) -> None:
    implement(project)
    _, first = run(project, "review", "prepare", "demo", "P-1")
    _, second = run(project, "review", "prepare", "demo", "P-1")

    assert first["data"]["packet"] != second["data"]["packet"]  # a new id each time, never reused


# --- staleness ------------------------------------------------------------------------------
def test_fm_b02_and_fm_k02_a_later_code_change_makes_every_record_stale(
    phase_done: dict[str, Any], project: Path
) -> None:
    put(project, "src/pkg/service.py", SERVICE + CREATE + "# later edit\n")
    stage(project, "src/pkg/service.py")

    results = {
        name: run(project, "validate", name, path)[1]
        for name, path in (("knowledge", KNOWLEDGE), ("test", TEST), ("review", REVIEW))
    }

    for name, document in results.items():
        assert document["data"]["verdict"] == "NOT_RUN", name
        assert "ORQ-W410" in codes(document), name
        assert any("code_tests" in finding["message"] for finding in document["findings"]), name


def test_fm_b03_a_design_edit_in_the_tree_is_a_change_of_code_and_of_design_alike(
    phase_done: dict[str, Any], project: Path
) -> None:
    """Offline the design is read from the tree under review, so it cannot be told apart from code.

    Which record a change in the *approved* design alone makes stale is derived from what each
    record covers (see `kinds_made_stale_by`); only the host's merge evidence, in S11, separates
    the approved design from the pull request's own diff.
    """
    manifest = project / TASK_DIR / "design/manifest.yaml"
    put(project, f"{TASK_DIR}/design/manifest.yaml", manifest.read_text() + "# amended\n")
    stage(project, f"{TASK_DIR}/design/manifest.yaml")

    assert verdicts(project) == {"knowledge": "NOT_RUN", "test": "NOT_RUN", "review": "NOT_RUN"}
    _, review = run(project, "validate", "review", REVIEW)
    stale = next(f["message"] for f in review["findings"] if f["code"] == "ORQ-W410")
    assert "design" in stale
    assert "code_tests" in stale


def test_fm_b03_a_changed_plan_stales_all_three(phase_done: dict[str, Any], project: Path) -> None:
    plan_path = project / TASK_DIR / "plan.yaml"
    put(project, f"{TASK_DIR}/plan.yaml", plan_path.read_text() + "# amended\n")
    stage(project, f"{TASK_DIR}/plan.yaml")

    assert verdicts(project) == {"knowledge": "NOT_RUN", "test": "NOT_RUN", "review": "NOT_RUN"}


def test_fm_b04_a_source_file_placed_where_records_live_stays_in_the_binding(
    phase_done: dict[str, Any], project: Path
) -> None:
    put(project, f"{TASK_DIR}/reviews/helper.py", "print('hidden change')\n")
    stage(project, f"{TASK_DIR}/reviews/helper.py")

    assert verdicts(project) == {"knowledge": "NOT_RUN", "test": "NOT_RUN", "review": "NOT_RUN"}


def test_fm_b04_a_record_whose_path_and_content_disagree_is_not_excluded(
    phase_done: dict[str, Any], project: Path
) -> None:
    text = (project / TEST).read_text().replace("phase: P-1", "phase: P-2")
    put(project, TEST, text)
    stage(project, TEST)

    _, document = run(project, "validate", "test", TEST)

    assert "ORQ-E401" in codes(document)  # the record says P-2, its path says P-1
    assert document["data"]["verdict"] == "FAIL"


# --- what a record may not claim ------------------------------------------------------------
def test_fm_k04_an_unresolved_candidate_fails_the_knowledge_record(
    phase_done: dict[str, Any], project: Path
) -> None:
    document = yaml.safe_load((project / KNOWLEDGE).read_text())
    document["entries"].pop()
    put(project, KNOWLEDGE, dump(document))
    stage(project, KNOWLEDGE)

    _, result = run(project, "validate", "knowledge", KNOWLEDGE)

    assert "ORQ-E423" in codes(result)
    assert result["data"]["verdict"] == "FAIL"


def test_fm_k08_a_claim_whose_anchor_is_not_in_the_draft_fails(
    phase_done: dict[str, Any], project: Path
) -> None:
    put(project, "docs/knowledge/service.md", KNOWLEDGE_DOC + "\nNo orders section here.\n")
    stage(project, "docs/knowledge/service.md")

    _, result = run(project, "validate", "knowledge", KNOWLEDGE)

    assert "ORQ-E428" in codes(result)


def test_fm_k05_evidence_of_kind_private_is_refused(
    phase_done: dict[str, Any], project: Path
) -> None:
    document = yaml.safe_load((project / KNOWLEDGE).read_text())
    entry = document["entries"][0]
    evidence = entry["claims"][0]["evidence"] if "claims" in entry else entry["evidence"]
    evidence[0]["kind"] = "private"
    put(project, KNOWLEDGE, dump(document))
    stage(project, KNOWLEDGE)

    exit_status, result = run(project, "validate", "knowledge", KNOWLEDGE)

    assert "ORQ-E325" in codes(result)  # the closed schema has no `private` kind
    assert result["data"]["verdict"] == "FAIL"
    assert exit_status == 5


def test_a_knowledge_edit_that_no_entry_explains_fails(
    phase_done: dict[str, Any], project: Path
) -> None:
    put(project, "docs/knowledge/extra.md", "# Extra\n")
    stage(project, "docs/knowledge/extra.md")

    _, result = run(project, "validate", "knowledge", KNOWLEDGE)

    assert "ORQ-E429" in codes(result)


def test_an_unapproved_review_binding_is_an_error_and_not_a_pass(
    phase_done: dict[str, Any], project: Path
) -> None:
    text = (
        (project / REVIEW)
        .read_text()
        .replace("binding_ref: orqlet-arch-reviewer", "binding_ref: my-private-agent")
    )
    put(project, REVIEW, text)
    stage(project, REVIEW)

    _, result = run(project, "validate", "review", REVIEW)

    assert "ORQ-E415" in codes(result)
    assert result["data"]["independence_derived"] == "I0"


def test_a_record_cannot_claim_more_independence_than_its_identifiers_give(
    phase_done: dict[str, Any], project: Path
) -> None:
    text = (project / REVIEW).read_text().replace("independence: I1", "independence: I3")
    put(project, REVIEW, text)
    stage(project, REVIEW)

    _, result = run(project, "validate", "review", REVIEW)

    assert "ORQ-E412" in codes(result)


def test_a_test_record_that_leaves_a_criterion_out_is_not_a_pass(
    phase_done: dict[str, Any], project: Path
) -> None:
    document = yaml.safe_load((project / TEST).read_text())
    document["acceptance_coverage"] = []
    put(project, TEST, dump(document))
    stage(project, TEST)

    _, result = run(project, "validate", "test", TEST)

    assert "ORQ-E419" in codes(result)


def test_a_review_round_gap_is_an_error(phase_done: dict[str, Any], project: Path) -> None:
    text = (project / REVIEW).read_text().replace("round: 1", "round: 3")
    put(project, f"{TASK_DIR}/reviews/architecture-reviewer-P-1-r3.yaml", text)
    stage(project, f"{TASK_DIR}/reviews/architecture-reviewer-P-1-r3.yaml")

    _, result = run(
        project, "validate", "review", f"{TASK_DIR}/reviews/architecture-reviewer-P-1-r3.yaml"
    )

    assert "ORQ-E403" in codes(result)


def test_a_record_outside_its_exact_path_is_not_evidence(project: Path) -> None:
    implement(project)
    put(project, "notes/P-1.yaml", "schema: orqlet.test-record/v1\n")

    _, result = run(project, "validate", "test", "notes/P-1.yaml")

    assert codes(result) == ["ORQ-E400"]


def test_without_the_target_branch_the_binding_is_not_run_and_the_message_says_why(
    project: Path,
) -> None:
    implement(project)
    git(project, "branch", "-m", "main", "trunk")  # the profile still names `main`
    _, impact = run(project, "knowledge", "impact", "demo", "P-1")

    assert impact["data"]["verdict"] == "NOT_RUN"
    assert "target branch" in impact["not_run"][0]


def test_naming_the_base_explicitly_works_without_the_target_branch(project: Path) -> None:
    implement(project)
    git(project, "branch", "-m", "main", "trunk")

    _, impact = run(project, "knowledge", "impact", "demo", "P-1", "--base", "trunk")

    assert impact["data"]["verdict"] == "PASS"


def test_the_commands_never_write_to_the_repository(
    phase_done: dict[str, Any], project: Path
) -> None:
    before = git(project, "status", "--porcelain=v1", "-uall")
    files = {p: p.read_bytes() for p in (project / "docs").rglob("*") if p.is_file()}

    verdicts(project)
    run(project, "knowledge", "impact", "demo", "P-1")
    run(project, "gate", "status", "demo", "--phase", "P-1")

    assert git(project, "status", "--porcelain=v1", "-uall") == before
    assert {p: p.read_bytes() for p in (project / "docs").rglob("*") if p.is_file()} == files
