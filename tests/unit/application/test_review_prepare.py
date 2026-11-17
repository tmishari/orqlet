"""`review prepare`: the read-only packet of the exact staged snapshot (proposal 19.5)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.vcs import CommitSummary, RepoState
from orqlet.application.usecases.review_prepare import review_prepare
from orqlet.application.usecases.validation import ValidateServices, ValidationResult
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Severity, Verdict
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED
from tests.support.artifacts import HASH, TASK_DIR, design, dump, phase, plan

pytestmark = pytest.mark.unit

BASE, HEADC, STAGED = "1" * 40, "2" * 40, "3" * 40
AGENT = b"---\nname: orqlet-arch-reviewer\n---\nReview.\n"


def tree(**extra: bytes) -> dict[str, bytes]:
    base = {
        "src/pkg/service.py": b"def existing() -> None: ...\n",
        f"{TASK_DIR}/plan.yaml": dump(plan(phases=[phase()])).encode(),
        f"{TASK_DIR}/design/manifest.yaml": dump(design()).encode(),
        ".orqlet/knowledge.yaml": b"schema: orqlet.knowledge/v2\n",
        ".prompts/rules.yaml": b"schema: orqlet.rules/v1\nrules: []\n",
        ".claude/agents/orqlet-arch-reviewer.md": AGENT,
        ".orqlet/standards.lock.yaml": (
            f"schema: orqlet.standards-lock/v1\napplicable_rules_hash: {'a' * 64}\n".encode()
        ),
        ".orqlet/workflow.lock": (
            "schema: orqlet.workflow-lock/v1\nworkflow_version: 0.2.0\n"
            f"workflow_digest: {'b' * 64}\ncontrols_level: 2\n".encode()
        ),
    }
    base.update({k.replace("__", "/"): v for k, v in extra.items()})
    return base


def world(
    staged: dict[str, bytes],
    *,
    modes: dict[tuple[str, str], str] | None = None,
    merge_bases: bool = True,
) -> ValidateServices:
    before = tree()
    vcs = FakeVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEADC, "head"),),
        committed=before,
        revisions={BASE: before, HEADC: before},
        merge_bases={(HEADC, BASE): (BASE,)} if merge_bases else {},
        staged=True,
        staged_tree=(STAGED, staged),
        modes=modes,
    )
    return ValidateServices(
        project=MemoryFileSystem(), vcs=vcs, loader=StrictYamlLoader(), workflow=PINNED
    )


def prepare(
    services: ValidateServices, packets: MemoryFileSystem, name: str = "pid", phase_id: str = "P-1"
) -> ValidationResult:
    return review_prepare(services, packets, name * 4, "demo", phase_id, base=BASE, head="staged")


def read(packets: MemoryFileSystem, path: str) -> bytes:
    return packets.read_bytes(CanonicalPath.parse(path))


def test_the_packet_holds_the_staged_snapshot_the_diff_and_the_context() -> None:
    staged = tree(src__pkg__service_py=b"unused")
    staged["src/pkg/service.py"] = b"def existing() -> None: ...\ndef more() -> None: ...\n"
    packets = MemoryFileSystem()

    result = prepare(world(staged), packets)

    assert result.verdict is Verdict.PASS
    name = str(result.data["packet"])
    assert name == "demo-P-1-pidpidpi"[: len(name)] or name.startswith("demo-P-1-")
    assert read(packets, f"{name}/snapshot/src/pkg/service.py").endswith(
        b"def more() -> None: ...\n"
    )
    assert b"service.py" in read(packets, f"{name}/diff.patch")
    for context in ("plan.yaml", "design-manifest.yaml", "standards/rules.yaml"):
        assert read(packets, f"{name}/context/{context}")
    assert result.data["tree"] == "staged"


def test_the_manifest_lists_every_file_with_its_hash_and_names_the_tree_and_the_base() -> None:
    packets = MemoryFileSystem()

    result = prepare(world(tree()), packets)

    name = str(result.data["packet"])
    manifest: dict[str, Any] = json.loads(read(packets, f"{name}/MANIFEST.json"))
    assert (manifest["base"], manifest["tree"], manifest["label"]) == (BASE, STAGED, "staged")
    listed = dict(manifest["files"])
    assert listed["snapshot/src/pkg/service.py"] == sha256_hex(tree()["src/pkg/service.py"])
    assert listed["context/plan.yaml"] == sha256_hex(tree()[f"{TASK_DIR}/plan.yaml"])


def test_a_symbolic_link_and_a_gitlink_are_left_out_and_the_result_says_so() -> None:
    staged = tree(bin__run=b"src/pkg/service.py", vendor__lib=b"")
    packets = MemoryFileSystem()

    result = prepare(
        world(staged, modes={(STAGED, "bin/run"): "120000", (STAGED, "vendor/lib"): "160000"}),
        packets,
    )

    name = str(result.data["packet"])
    assert packets.kind(CanonicalPath.parse(f"{name}/snapshot/bin/run")) is None
    omitted = [f.message for f in result.findings if f.code == "ORQ-I440"]
    assert len(omitted) == 2


def test_a_packet_is_written_once_into_a_folder_that_did_not_exist() -> None:
    packets = MemoryFileSystem()
    first = prepare(world(tree()), packets)

    again = prepare(world(tree()), packets)  # the same id again

    assert first.verdict is Verdict.PASS
    assert again.verdict is Verdict.FAIL
    assert [f.code for f in again.findings] == ["ORQ-E441"]


def test_an_unknown_phase_is_an_error_and_nothing_is_written() -> None:
    packets = MemoryFileSystem()

    result = prepare(world(tree()), packets, phase_id="P-9")

    assert [f.code for f in result.findings] == ["ORQ-E440"]
    assert packets.snapshot() == {}


def test_without_a_plan_or_a_design_in_the_tree_the_packet_is_not_run() -> None:
    staged = tree()
    del staged[f"{TASK_DIR}/plan.yaml"]
    packets = MemoryFileSystem()

    result = prepare(world(staged), packets)

    assert result.verdict is Verdict.NOT_RUN
    assert packets.snapshot() == {}


def test_a_half_merged_index_is_never_exported() -> None:
    vcs = FakeVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEADC, "head"),),
        committed=tree(),
        revisions={BASE: tree(), HEADC: tree()},
        merge_bases={(HEADC, BASE): (BASE,)},
        staged=True,
    )  # no staged tree: the index has unmerged entries
    services = ValidateServices(
        project=MemoryFileSystem(), vcs=vcs, loader=StrictYamlLoader(), workflow=PINNED
    )

    with pytest.raises(Exception, match="unmerged"):
        prepare(services, MemoryFileSystem())


def test_several_merge_bases_make_the_binding_not_run_instead_of_guessing() -> None:
    result = prepare(world(tree(), merge_bases=False), MemoryFileSystem())

    assert result.verdict is Verdict.NOT_RUN
    assert "merge base" in result.not_run[0]


def test_the_review_binding_is_printed_for_each_generated_reviewer_in_the_tree() -> None:
    result = prepare(world(tree()), MemoryFileSystem())

    inputs = result.data["review_inputs"]
    assert isinstance(inputs, dict)
    block = inputs["review"]["architecture-reviewer"]["claude-code"]
    assert block["covers"][0] == "code_tests"
    assert len(block["digest"]) == 64
    assert "security-reviewer" not in inputs["review"]  # that agent is not in the tree
    assert "test" in inputs


def test_without_a_generated_reviewer_the_review_binding_is_not_printed() -> None:
    staged = tree()
    del staged[".claude/agents/orqlet-arch-reviewer.md"]

    result = prepare(world(staged), MemoryFileSystem())

    assert "review" not in result.data["review_inputs"]  # type: ignore[operator]
    assert any(f.code == "ORQ-I441" for f in result.findings)


# --- phase P-9: the third reviewer in the printed inputs (AC-6) and in the binding (AC-1) -------
# These tests were written first, by the Tester of phase P-9 of the task dynamic-model-profiles,
# before the implementation existed. Each cites its `expected_behavior_source`: AC-n of phase P-9
# in docs/design/dynamic-model-profiles/plan.yaml, BC-n of design/component.md, and ADR-006.
# The tree of each test is built here: it holds the agent files that the test names and no
# others, so no test depends on whether `init` renders the file of the code reviewer (phase P-13
# adds it to the packaged workflow).

ROLE_AGENTS = {
    "architecture-reviewer": "orqlet-arch-reviewer",
    "security-reviewer": "orqlet-security-reviewer",
    "code-reviewer": "orqlet-code-reviewer",
}
I441 = "ORQ-I441"


def agent_path(client_folder: str, agent: str, extension: str = "md") -> str:
    return f"{client_folder}/agents/{agent}.{extension}"


def staged_with_agents(*roles: str) -> dict[str, bytes]:
    """The staged tree whose `claude-code` agent files are the files of these roles, and no more."""
    staged = tree()
    for agent in ROLE_AGENTS.values():
        staged.pop(agent_path(".claude", agent), None)
    for role in roles:
        agent = ROLE_AGENTS[role]
        staged[agent_path(".claude", agent)] = f"---\nname: {agent}\n---\nReview.\n".encode()
    return staged


def review_inputs(result: ValidationResult) -> dict[str, Any]:
    inputs = result.data["review_inputs"]
    assert isinstance(inputs, dict)
    return inputs


def printed_review(result: ValidationResult) -> dict[str, Any]:
    review = review_inputs(result)["review"]
    assert isinstance(review, dict)
    return review


def information_findings(result: ValidationResult) -> list[Any]:
    return [finding for finding in result.findings if finding.code == I441]


def roles_named(message: str) -> set[str]:
    return {role for role in ROLE_AGENTS if role in message}


def test_a_tree_with_the_agent_files_of_all_three_roles_prints_three_role_blocks() -> None:
    """expected_behavior_source: P-9 AC-6 ("`orqlet review prepare` prints the `review_input`
    block of each of the three reviewers whose agent file is in the tree, and ORQ-I441 for one
    that is not"); BC-15; BC-41; ADR-006 decision 6 (`DEFAULT_REVIEWERS` gains the third entry)."""
    result = prepare(world(staged_with_agents(*ROLE_AGENTS)), MemoryFileSystem())

    review = printed_review(result)

    assert set(review) == set(ROLE_AGENTS)
    for role in ROLE_AGENTS:
        assert set(review[role]) == {"claude-code"}  # the only client whose files are in the tree
        block = review[role]["claude-code"]
        assert block["schema"] == "orqlet.review-input/v1"
        assert block["covers"][0] == "code_tests"
        assert len(block["digest"]) == 64
    assert information_findings(result) == []


def test_each_role_block_is_bound_to_the_agent_file_of_its_own_role() -> None:
    """expected_behavior_source: P-9 AC-6 (a block for each of the three reviewers whose agent
    file is in the tree); the `reviewer_definition` component of binding_inputs.py is the hash of
    the file of the request's agent. Three different agent files give three different
    components, so no role is printed with the file of another."""
    result = prepare(world(staged_with_agents(*ROLE_AGENTS)), MemoryFileSystem())

    review = printed_review(result)

    definitions = {role: review[role]["claude-code"]["components"] for role in ROLE_AGENTS}
    assert len({parts["reviewer_definition"] for parts in definitions.values()}) == 3


def test_a_role_prints_a_block_for_each_client_whose_agent_file_is_in_the_tree() -> None:
    """expected_behavior_source: P-9 AC-6 ("the `review_input` block of each of the three
    reviewers whose agent file is in the tree"); the loop of `review prepare`, which visits each
    client of each role. The code reviewer has a file for the three clients, the others for
    `claude-code` only."""
    staged = staged_with_agents(*ROLE_AGENTS)
    code = ROLE_AGENTS["code-reviewer"]
    staged[agent_path(".cursor", code)] = b"---\nname: orqlet-code-reviewer\n---\nReview.\n"
    staged[agent_path(".codex", code, "toml")] = b'name = "orqlet-code-reviewer"\n'

    review = printed_review(prepare(world(staged), MemoryFileSystem()))

    assert set(review["code-reviewer"]) == {"claude-code", "cursor", "codex"}
    assert set(review["architecture-reviewer"]) == {"claude-code"}
    assert set(review["security-reviewer"]) == {"claude-code"}


def test_two_agent_files_print_two_blocks_and_one_i441_that_names_the_code_reviewer() -> None:
    """expected_behavior_source: P-9 AC-6 ("ORQ-I441 for one that is not"); the interface of the
    brief (ORQ-I441 is given once for each role that has no agent file in the tree for any
    client, and its message names the role). The tree holds the two files that exist today."""
    staged = staged_with_agents("architecture-reviewer", "security-reviewer")

    result = prepare(world(staged), MemoryFileSystem())

    assert set(printed_review(result)) == {"architecture-reviewer", "security-reviewer"}
    assert [roles_named(f.message) for f in information_findings(result)] == [{"code-reviewer"}]


def test_a_tree_without_an_agent_file_prints_no_review_and_one_i441_for_each_role() -> None:
    """expected_behavior_source: P-9 AC-6 ("ORQ-I441 for one that is not", for each of the three);
    the existing test of this file (no generated reviewer: no "review" key and an ORQ-I441); the
    interface of the brief (three ORQ-I441, each naming its role)."""
    result = prepare(world(staged_with_agents()), MemoryFileSystem())

    named = [roles_named(finding.message) for finding in information_findings(result)]

    assert "review" not in review_inputs(result)
    assert len(named) == 3
    assert all(len(roles) == 1 for roles in named)  # each message names one role
    assert {role for roles in named for role in roles} == set(ROLE_AGENTS)


def test_a_role_with_an_agent_file_for_one_client_only_gets_no_i441() -> None:
    """expected_behavior_source: P-9 AC-6 ("ORQ-I441 for one that is not" in the tree); the
    interface of the brief (ORQ-I441 is for a role with no agent file for any client). The code
    reviewer has a file for `cursor` only, so it is printed for `cursor` and has no ORQ-I441."""
    staged = staged_with_agents("architecture-reviewer", "security-reviewer")
    staged[agent_path(".cursor", ROLE_AGENTS["code-reviewer"])] = b"---\nname: x\n---\nReview.\n"

    result = prepare(world(staged), MemoryFileSystem())

    assert set(printed_review(result)["code-reviewer"]) == {"cursor"}
    assert information_findings(result) == []


@pytest.mark.parametrize(
    "present",
    [
        pytest.param(("architecture-reviewer", "security-reviewer"), id="code-reviewer-missing"),
        pytest.param((), id="all-three-missing"),
    ],
)
def test_each_i441_is_an_information_finding(present: tuple[str, ...]) -> None:
    """expected_behavior_source: P-9 AC-6 (the interface of the brief: ORQ-I441 is an information
    finding); the existing `Collector.info` use of ORQ-I441, which keeps the verdict as it was."""
    result = prepare(world(staged_with_agents(*present)), MemoryFileSystem())

    found = information_findings(result)

    assert found
    assert {finding.severity for finding in found} == {Severity.INFO}


# The effect of AC-1 on the binding: a record of the code reviewer is left out of `code_tests`.
# The record is a valid `orqlet.review-result/v1` of task `demo`, phase P-1, round 1.
REVIEW_COVERS = [
    "code_tests",
    "knowledge",
    "design",
    "plan",
    "standards",
    "reviewer_definition",
    "evidence_inputs",
]


def review_record(role: str) -> bytes:
    """A valid review record whose content names `role`, for the path that a test chooses."""
    revision = "b" * 40
    document: dict[str, Any] = {
        "schema": "orqlet.review-result/v1",
        "task": "demo",
        "phase": "P-1",
        "role": role,
        "round": 1,
        "verdict": "FAIL",
        "assurance": "advisory",
        "review_input": {
            "schema": "orqlet.review-input/v1",
            "covers": REVIEW_COVERS,
            "components": dict.fromkeys(REVIEW_COVERS, HASH),
            "digest": HASH,
            "merge_base": revision,
        },
        "agent": {
            "binding_ref": "orqlet-arch-reviewer",
            "definition_sha256": HASH,
            "client": "cursor",
            "model_requested": None,
            "model_observed": None,
        },
        "coder_binding": {"client": "cursor", "model_requested": None, "model_observed": None},
        "independence": "I1",
        "capability_limits": ["read-only is advisory"],
        "applicability": {"examined": ["src/pkg/service.py"], "conclusion": "findings"},
        "findings": [
            {
                "schema": "orqlet.finding/v1",
                "id": "F-1",
                "kind": "finding",
                "severity": "blocking",
                "category": "tests",
                "evidence": [
                    {
                        "kind": "absence",
                        "searched": ["tests/**"],
                        "method": "searched test names",
                        "revision": revision,
                    }
                ],
                "claim": "The error path has no test.",
                "suggested_action": "Add one.",
                "confidence": "medium",
            }
        ],
        "self_check": {
            "schema": "orqlet.self-check/v1",
            "checked_against": {"role": "architecture-reviewer", "phase": "implement"},
            "checks": [{"what": "packet read", "how": "orqlet review prepare", "result": "pass"}],
        },
    }
    return dump(document).encode()


def code_tests_with_a_record(path: str | None, content: bytes = b"") -> str:
    """The `code_tests` component of the printed review block when the staged tree adds a file."""
    staged = tree()
    if path is not None:
        staged[path] = content
    result = prepare(world(staged), MemoryFileSystem())
    block = printed_review(result)["architecture-reviewer"]["claude-code"]
    return str(block["components"]["code_tests"])


@pytest.mark.parametrize("role", list(ROLE_AGENTS))
def test_a_valid_record_of_each_reviewer_role_is_left_out_of_code_tests(role: str) -> None:
    """expected_behavior_source: P-9 AC-1 ("is recognised as a review record, is left out of
    `code_tests` and `knowledge` like the records of the other two roles"); BC-36; ADR-006
    decision 6 (a `code-reviewer` record "would count as an ordinary input of its own binding").
    The record is added to the staged tree: the component is the one of the tree without it."""
    path = f"{TASK_DIR}/reviews/{role}-P-1-r1.yaml"

    without = code_tests_with_a_record(None)
    with_record = code_tests_with_a_record(path, review_record(role))

    assert with_record == without


def test_a_code_reviewer_path_whose_content_names_another_role_stays_in_code_tests() -> None:
    """expected_behavior_source: P-9 AC-1 ("a path of the right shape whose content names another
    role is not excluded"); BC-36; the module docstring of evidence_artifacts.py (the role in the
    file must equal the role in its path)."""
    path = f"{TASK_DIR}/reviews/code-reviewer-P-1-r1.yaml"

    without = code_tests_with_a_record(None)
    with_record = code_tests_with_a_record(path, review_record("architecture-reviewer"))

    assert with_record != without


def test_a_record_with_any_other_role_name_in_its_path_stays_in_code_tests() -> None:
    """expected_behavior_source: P-9 AC-1 ("a path with any other role name stays an ordinary
    input"). The content is a valid code reviewer record, so only the path decides. This holds at
    the base revision too: it keeps holding once the third role is added."""
    path = f"{TASK_DIR}/reviews/code-reviewers-P-1-r1.yaml"

    without = code_tests_with_a_record(None)
    with_record = code_tests_with_a_record(path, review_record("code-reviewer"))

    assert with_record != without
