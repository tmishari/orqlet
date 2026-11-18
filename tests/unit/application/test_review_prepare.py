"""`review prepare`: the read-only packet of the exact staged snapshot (proposal 19.5)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.vcs import CommitSummary, RepoState
from orqlet.application.usecases.review_prepare import MAX_FILE_BYTES, review_prepare
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
    base: dict[str, bytes] | None = None,
) -> ValidateServices:
    before = tree() if base is None else base
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


# --- phase P-11: the packet carries no earlier review conclusion (AC-3, AC-4) ------------------
# These tests were written first, by the Tester of phase P-11 of the task dynamic-model-profiles,
# before the implementation existed. Each cites its `expected_behavior_source`: AC-n of phase P-11
# in docs/design/dynamic-model-profiles/plan.yaml, BC-n and R-8 of design/component.md, and
# decision 8 of ADR-007 (design/adr-007-independence-model-identity-and-fresh-context.md). The
# `FakeVcs` of these tests applies the rule of the port: a pattern matches as `fnmatch` does, and
# a path matches only itself. Its patch lists paths and statuses, not content, so a sentinel in
# the content of a file can only be found in the snapshot, and a sentinel in a file name can be
# found in the snapshot, in `diff.patch` and in `MANIFEST.json`. The same checks on a real Git,
# with the content in the patch, are in tests/integration/test_review_packet_real_git.py.

CONCLUSION = "SENTINEL-CONCLUSION-5c1e9a"  # the text of an earlier review: in a record and a note
RECORD_NAME = "SENTINEL-NAME-8d2f41"  # a part of the file name of an earlier record
REVIEWS_DIR = f"{TASK_DIR}/reviews"
RECORD = f"{REVIEWS_DIR}/architecture-reviewer-P-1-r1.yaml"
DEEP_RECORD = f"{REVIEWS_DIR}/deep/security-reviewer-P-1-r1.yaml"
NAMED_RECORD = f"{REVIEWS_DIR}/security-reviewer-P-1-r2-{RECORD_NAME}.yaml"
OTHER_RECORD = "docs/design/other/reviews/architecture-reviewer-P-2-r1.yaml"
NOTE = "docs/notes/architecture-round-1.md"
SECOND_NOTE = "docs/notes/security-round-1.md"
ORDINARY = "docs/guide/overview.md"
SERVICE_PATH = "src/pkg/service.py"  # a source file that `tree()` holds
OVERVIEW = b"# Overview\n"
EARLIER = f"verdict: FAIL\nclaim: {CONCLUSION}\n".encode()
MANIFEST_PATH = f"{TASK_DIR}/design/manifest.yaml"


def manifest_naming(*notes: str, task: str = "demo") -> bytes:
    """The design manifest of `task` whose `reviews` name `notes`, for the two roles in turn."""
    roles = ("architecture-reviewer", "security-reviewer")
    reviews = [{"role": roles[number % 2], "note": note} for number, note in enumerate(notes)]
    return dump(design(task=task, reviews=reviews)).encode()


def staged_naming(
    notes: tuple[str, ...] = (), files: dict[str, bytes] | None = None
) -> dict[str, bytes]:
    """The staged tree whose design manifest names `notes`, plus the given files."""
    staged = tree()
    staged[MANIFEST_PATH] = manifest_naming(*notes)
    staged.update(files or {})
    return staged


def prepared(
    staged: dict[str, bytes],
    *,
    modes: dict[tuple[str, str], str] | None = None,
    name: str = "pid",
    base: dict[str, bytes] | None = None,
) -> tuple[ValidationResult, dict[str, bytes]]:
    """Run `review prepare` on `staged`: its result and the files of the packet by their path.

    Unless a test gives `base`, the design manifest of the base is the staged one: the design was
    approved before the change and the change leaves it alone. The notes that are left out come
    from the base (rework round 2, after F-1 of the security review r2).
    """
    packets = MemoryFileSystem()
    if base is None:
        base = {**tree(), MANIFEST_PATH: staged[MANIFEST_PATH]}
    result = prepare(world(staged, modes=modes, base=base), packets, name)
    assert result.verdict is Verdict.PASS
    prefix = f"{result.data['packet']}/"
    files = {
        path.removeprefix(prefix): data
        for path, data in packets.snapshot().items()
        if path.startswith(prefix)
    }
    return result, files


def header_of(path: str) -> bytes:
    """The line that starts the section of `path` in a patch; the fake and Git both write it."""
    return f"diff --git a/{path} b/{path}".encode()


def omitted_messages(result: ValidationResult) -> list[str]:
    return [finding.message for finding in result.findings if finding.code == "ORQ-I440"]


def leaks(files: dict[str, bytes], *needles: str) -> list[tuple[str, str]]:
    """Each (file, needle) where a needle shows in the name of a packet file or in its content."""
    return [
        (path, needle)
        for path, data in sorted(files.items())
        for needle in needles
        if needle in path or needle.encode() in data
    ]


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(RECORD, id="a-record-of-the-task"),
        pytest.param(DEEP_RECORD, id="a-record-in-a-folder-below"),
        pytest.param(OTHER_RECORD, id="a-record-of-another-task"),
    ],
)
def test_a_path_under_a_reviews_folder_is_left_out_of_snapshot_and_diff(path: str) -> None:
    """expected_behavior_source: P-11 AC-3 ("leaves out of `snapshot/`, of the context copies and
    of `diff.patch` every path that matches `docs/design/*/reviews/*`"); BC-21; ADR-007 decision
    8. `*` crosses `/`, so a record in a folder below the reviews folder and a record of another
    task match too."""
    _, packet = prepared(staged_naming(files={path: EARLIER, ORDINARY: OVERVIEW}))

    assert [name for name in packet if name.endswith(path)] == []
    assert header_of(path) not in packet["diff.patch"]
    assert f"snapshot/{ORDINARY}" in packet
    assert header_of(ORDINARY) in packet["diff.patch"]


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("docs/reviews/overview.md", id="a-reviews-folder-outside-docs-design"),
        pytest.param(f"{TASK_DIR}/reviews-summary.md", id="a-name-that-starts-with-reviews"),
        pytest.param("docs/design/reviews/overview.md", id="no-task-folder-above-reviews"),
    ],
)
def test_a_path_the_reviews_pattern_does_not_match_stays_in_the_packet(path: str) -> None:
    """expected_behavior_source: P-11 AC-3 (only "every path that matches
    `docs/design/*/reviews/*`" is left out; the packet is the exact staged snapshot, see the
    module docstring of review_prepare.py). A path that the pattern does not match stays in the
    snapshot and in the diff."""
    _, packet = prepared(staged_naming(files={path: OVERVIEW}))

    assert packet[f"snapshot/{path}"] == OVERVIEW
    assert header_of(path) in packet["diff.patch"]


def test_a_path_named_as_a_review_note_is_left_out_of_snapshot_and_diff() -> None:
    """expected_behavior_source: P-11 AC-3 ("every path that `reviews[].note` of the task's design
    manifest names"); BC-45; ADR-007 decision 8 (`DesignReview.note` is any repository path).
    Two notes of two roles, in a folder that the reviews pattern does not match."""
    files = {NOTE: EARLIER, SECOND_NOTE: EARLIER, ORDINARY: OVERVIEW}

    _, packet = prepared(staged_naming((NOTE, SECOND_NOTE), files))

    for note in (NOTE, SECOND_NOTE):
        assert [name for name in packet if name.endswith(note)] == []
        assert header_of(note) not in packet["diff.patch"]
    assert f"snapshot/{ORDINARY}" in packet


def test_a_note_path_with_glob_characters_names_only_that_path() -> None:
    """expected_behavior_source: P-11 AC-1 ("a path matches only itself") and AC-2 ("a literal
    path with glob characters is excluded only as that path"), as `review prepare` passes a note
    path to the port; BC-45. The note `[a-b].md` is left out and the file `a.md` stays."""
    brackets, plain = "docs/notes/[a-b].md", "docs/notes/a.md"

    _, packet = prepared(staged_naming((brackets,), {brackets: EARLIER, plain: b"a\n"}))

    assert f"snapshot/{brackets}" not in packet
    assert header_of(brackets) not in packet["diff.patch"]
    assert packet[f"snapshot/{plain}"] == b"a\n"
    assert header_of(plain) in packet["diff.patch"]


def test_a_note_path_that_names_a_directory_excludes_nothing_below_it() -> None:
    """expected_behavior_source: P-11 AC-1 ("a path matches only itself") and the brief of the
    phase (a note path that names a directory excludes nothing below it); BC-45. The files below
    `docs/notes` stay in the snapshot and in the diff."""
    files = {"docs/notes/a.md": b"a\n", "docs/notes/sub/x.md": b"x\n"}

    _, packet = prepared(staged_naming(("docs/notes",), files))

    for path in files:
        assert f"snapshot/{path}" in packet
        assert header_of(path) in packet["diff.patch"]


def test_only_the_design_manifest_of_the_task_names_notes() -> None:
    """expected_behavior_source: P-11 AC-3 ("every path that `reviews[].note` of the task's design
    manifest names"). The manifest of another task names `docs/notes/other-round-1.md`; the
    packet of `demo` keeps that file."""
    other_note = "docs/notes/other-round-1.md"
    files = {
        "docs/design/other/design/manifest.yaml": manifest_naming(other_note, task="other"),
        other_note: b"other\n",
    }

    _, packet = prepared(staged_naming(files=files))

    assert packet[f"snapshot/{other_note}"] == b"other\n"
    assert header_of(other_note) in packet["diff.patch"]


def test_a_note_path_that_is_also_a_context_source_leaves_that_copy_out() -> None:
    """expected_behavior_source: P-11 AC-3 ("leaves out of `snapshot/`, of the context copies and
    of `diff.patch` every path that ... `reviews[].note` ... names"); BC-21 (the context copies).
    The AS-IS file is copied to `context/as-is.md` when it is in the tree. Named as a note, it
    is in neither place. The control run, with the same file and no note, holds both."""
    as_is = f"{TASK_DIR}/as-is.md"
    files = {as_is: b"# AS-IS\n"}

    _, control = prepared(staged_naming(files=files))
    _, named = prepared(staged_naming((as_is,), files))

    assert control["context/as-is.md"] == b"# AS-IS\n"
    assert f"snapshot/{as_is}" in control
    assert "context/as-is.md" not in named
    assert f"snapshot/{as_is}" not in named


def test_the_design_manifest_copy_stays_in_the_packet_and_lists_the_note_paths() -> None:
    """expected_behavior_source: ADR-007 decision 8 ("The design-manifest copy lists note paths
    and holds no conclusion"); P-11 AC-3 (only the paths that the manifest names are left out,
    not the manifest). The copy and the snapshot file hold the manifest as it was staged."""
    staged = staged_naming((NOTE, SECOND_NOTE), {NOTE: EARLIER})

    _, packet = prepared(staged)

    copy = packet["context/design-manifest.yaml"]
    assert copy == staged[MANIFEST_PATH]
    assert NOTE.encode() in copy
    assert SECOND_NOTE.encode() in copy
    assert packet[f"snapshot/{MANIFEST_PATH}"] == staged[MANIFEST_PATH]


# Rework round 1, after finding F-1 of the architecture review r1. The Coder, not the Tester,
# wrote the cases below before the change. The staged manifest decides which paths are notes, so
# it must not be able to take out of the packet the files that the reviewer reads the change
# against: itself, the plan and the standards. Each member is (its path, its context copy).
MEMBERS = {
    "design-manifest": (MANIFEST_PATH, "context/design-manifest.yaml"),
    "plan": (f"{TASK_DIR}/plan.yaml", "context/plan.yaml"),
    "standards-file": (".prompts/rules.yaml", "context/standards/rules.yaml"),
}


@pytest.mark.parametrize("member", list(MEMBERS))
def test_a_note_never_takes_the_manifest_the_plan_or_a_standards_file_out_of_the_packet(
    member: str,
) -> None:
    """expected_behavior_source: ADR-007 decision 8 ("The design-manifest copy lists note paths");
    finding F-1 of the architecture review r1 of P-11 (a manifest that names itself as a note
    took its own copy, its diff section and the plan out, and `omitted` said nothing). The member
    is changed in the staged tree, so it has a section in the diff; its note entry in the approved
    manifest, the one at the base, is ignored. A real note named next to it is still left out."""
    path, copy = MEMBERS[member]
    approved = manifest_naming(path, NOTE)
    files = {NOTE: EARLIER}
    if member == "plan":
        files[path] = dump(plan(phases=[phase()])).encode() + b"# changed after the base\n"
    if member == "standards-file":
        files[path] = b"schema: orqlet.rules/v1\nrules: []\n# changed after the base\n"
    staged = staged_naming((path, NOTE), files)
    if member == "design-manifest":
        staged[MANIFEST_PATH] = approved + b"# changed after the base\n"

    result, packet = prepared(staged, base={**tree(), MANIFEST_PATH: approved})

    assert packet[copy] == staged[path]
    assert packet[f"snapshot/{path}"] == staged[path]
    assert header_of(path) in packet["diff.patch"]
    assert f"snapshot/{NOTE}" not in packet
    assert header_of(NOTE) not in packet["diff.patch"]
    assert omitted_messages(result) == []


# Rework round 2, after finding F-1 of the security review r2 (a staged manifest could name any
# changed file as a note and hide it, while the review binding still covers it). The Coder wrote
# the cases below before the change. The notes come from the design manifest at the merge base,
# the approved one: a change cannot choose what is hidden from its own review. ADR-007 decision 8
# and AC-3 say "the design manifest" and do not say which tree; this is the Coder's reading.
def test_a_note_that_only_the_staged_manifest_names_stays_in_the_packet() -> None:
    """expected_behavior_source: finding F-1 of the security review r2 of P-11; ADR-007 decision
    8 ("The design-manifest copy lists note paths"). The staged manifest names a changed source
    file as a note, and the approved manifest at the base names nothing. The file is in the
    snapshot and in the diff, and the manifest copy that lists the note is there too."""
    changed = b"def staged() -> None: ...\n"
    staged = staged_naming((SERVICE_PATH,), {SERVICE_PATH: changed})

    result, packet = prepared(staged, base=tree())

    assert packet[f"snapshot/{SERVICE_PATH}"] == changed
    assert header_of(SERVICE_PATH) in packet["diff.patch"]
    assert packet["context/design-manifest.yaml"] == staged[MANIFEST_PATH]
    assert SERVICE_PATH.encode() in packet["context/design-manifest.yaml"]
    assert omitted_messages(result) == []


def test_a_note_that_the_staged_manifest_drops_is_still_left_out() -> None:
    """expected_behavior_source: finding F-1 of the security review r2 of P-11; P-11 AC-3 (every
    path that a note of the design manifest names is left out). The approved manifest names the
    note; the staged manifest does not name it any more. A change cannot bring a note back into
    the packet by editing the manifest."""
    approved = manifest_naming(NOTE)
    staged = staged_naming((), {NOTE: EARLIER, ORDINARY: OVERVIEW})

    _, packet = prepared(staged, base={**tree(), MANIFEST_PATH: approved})

    assert f"snapshot/{NOTE}" not in packet
    assert header_of(NOTE) not in packet["diff.patch"]
    assert f"snapshot/{ORDINARY}" in packet


@pytest.mark.parametrize(
    "approved",
    [
        pytest.param(None, id="no-manifest-at-the-base"),
        pytest.param(b"reviews: [unclosed\n", id="a-manifest-at-the-base-that-cannot-be-read"),
    ],
)
def test_without_a_manifest_to_read_at_the_base_only_the_records_pattern_applies(
    approved: bytes | None,
) -> None:
    """expected_behavior_source: finding F-1 of the security review r2 of P-11 (the notes come
    from the base; a base without a usable manifest names none, so nothing is hidden on the word
    of the staged manifest); P-11 AC-3 (the records pattern still applies). The packet is made
    and the packet result has no error."""
    base = tree()
    del base[MANIFEST_PATH]
    if approved is not None:
        base[MANIFEST_PATH] = approved
    staged = staged_naming((NOTE,), {NOTE: EARLIER, RECORD: EARLIER})

    result, packet = prepared(staged, base=base)

    assert f"snapshot/{NOTE}" in packet
    assert header_of(NOTE) in packet["diff.patch"]
    assert f"snapshot/{RECORD}" not in packet
    assert header_of(RECORD) not in packet["diff.patch"]
    assert not [f for f in result.findings if f.severity is Severity.ERROR]


# Entries that the packet would report as left out: (mode, file name, content).
ODD_ENTRIES: dict[str, tuple[str, str, bytes]] = {
    "symbolic-link": ("120000", "link.yaml", b"src/pkg/service.py"),
    "gitlink": ("160000", "vendored", b""),
    "unwritable-name": ("100644", "con.yaml", b"x"),  # a device name on Windows
    "over-the-limits": ("100644", "huge.yaml", b"x" * (MAX_FILE_BYTES + 1)),
}
# A note whose name cannot be written is not a valid `RepoPath`, so that pair does not exist.
ODD_CASES = [
    pytest.param("symbolic-link", "reviews", id="a-symbolic-link-in-a-reviews-folder"),
    pytest.param("gitlink", "reviews", id="a-gitlink-in-a-reviews-folder"),
    pytest.param("unwritable-name", "reviews", id="an-unwritable-name-in-a-reviews-folder"),
    pytest.param("over-the-limits", "reviews", id="a-huge-file-in-a-reviews-folder"),
    pytest.param("symbolic-link", "note", id="a-note-that-is-a-symbolic-link"),
    pytest.param("gitlink", "note", id="a-note-that-is-a-gitlink"),
    pytest.param("over-the-limits", "note", id="a-note-over-the-limits"),
]


@pytest.mark.parametrize(("entry", "where"), ODD_CASES)
def test_an_excluded_path_is_neither_omitted_nor_listed_in_the_manifest(
    entry: str, where: str
) -> None:
    """expected_behavior_source: P-11 AC-3 ("Excluded paths appear in neither the `omitted` list
    nor `MANIFEST.json`"); BC-45; ADR-007 decision 8 (a line in `omitted` "would reveal that
    earlier rounds exist"). An excluded link, gitlink, unwritable name or oversize file is not
    reported. The link `bin/run`, which nothing excludes, still is: the report works."""
    mode, name, content = ODD_ENTRIES[entry]
    folder = REVIEWS_DIR if where == "reviews" else "docs/notes"
    path = f"{folder}/{name}"
    notes = (path,) if where == "note" else ()
    staged = staged_naming(notes, {path: content, "bin/run": b"src/pkg/service.py"})

    result, packet = prepared(staged, modes={(STAGED, path): mode, (STAGED, "bin/run"): "120000"})

    reported = omitted_messages(result)
    manifest: dict[str, Any] = json.loads(packet["MANIFEST.json"])
    assert len(reported) == 1
    assert "bin/run" in reported[0]
    # The finding says "left out of the packet: <note>"; the manifest holds the note itself.
    notes_reported = [message.removeprefix("left out of the packet: ") for message in reported]
    assert manifest["omitted"] == notes_reported
    assert all(path not in listed for listed, _ in manifest["files"])
    assert path.encode() not in packet["MANIFEST.json"]
    assert all(path not in finding.message for finding in result.findings)
    assert path not in str(result.data)


def test_two_runs_on_the_same_tree_give_the_same_packet_digest() -> None:
    """expected_behavior_source: P-11 AC-3 ("Each round builds the whole packet again from the
    staged snapshot and its diff, so two runs on the same tree give the same `packet_digest`");
    BC-21 ("every round rebuilds the whole packet"); ADR-007 decision 8. The two runs have
    different packet ids, so the packet folders differ, and every file of the two is equal."""
    files = {RECORD: EARLIER, NOTE: EARLIER, ORDINARY: OVERVIEW}
    staged = staged_naming((NOTE,), files)

    first, first_files = prepared(staged, name="aaa")
    second, second_files = prepared(staged, name="bbb")

    assert first.data["packet"] != second.data["packet"]
    assert first.data["packet_digest"] == second.data["packet_digest"]
    assert first_files == second_files


def test_a_record_that_a_later_round_adds_changes_nothing_in_the_packet() -> None:
    """expected_behavior_source: ADR-007 decision 8 ("The packet carries no earlier conclusion";
    "every round rebuilds the whole packet from the staged snapshot and diff"); BC-21; P-11 AC-3.
    The tree of the second round holds two more records and the content of the note. Both trees
    name the same note, so the manifest copy is the same, and the two packets are equal."""
    first_round = {ORDINARY: OVERVIEW}
    second_round = {**first_round, RECORD: EARLIER, NAMED_RECORD: EARLIER, NOTE: EARLIER}

    first, first_files = prepared(staged_naming((NOTE,), first_round), name="aaa")
    second, second_files = prepared(staged_naming((NOTE,), second_round), name="bbb")

    assert first.data["packet_digest"] == second.data["packet_digest"]
    assert first_files == second_files


def test_a_sentinel_from_earlier_records_is_found_in_no_file_of_the_packet() -> None:
    """expected_behavior_source: P-11 AC-4 ("A sentinel string written into a review record and
    into a note path named by the manifest is found in no file of the packet"; the scan covers
    every file); BC-21; BC-45; ADR-007 decision 8 ("A test scans the whole packet for a sentinel
    string taken from an earlier record"). The sentinel is in a record, in a second record and
    in the note; another is in the file name of a record. The scan reads every path and every
    content, and the findings of the result."""
    files = {RECORD: EARLIER, NAMED_RECORD: EARLIER, NOTE: EARLIER, ORDINARY: OVERVIEW}

    result, packet = prepared(staged_naming((NOTE,), files))

    assert {"MANIFEST.json", "diff.patch", "context/plan.yaml"} <= set(packet)
    assert f"snapshot/{ORDINARY}" in packet
    assert leaks(packet, CONCLUSION, RECORD_NAME) == []
    messages = " ".join(finding.message for finding in result.findings)
    assert CONCLUSION not in messages
    assert RECORD_NAME not in messages


def test_the_scan_finds_a_sentinel_that_sits_in_an_ordinary_file_and_path() -> None:
    """expected_behavior_source: P-11 AC-4 and ADR-007 decision 8 (a scan for a sentinel). A scan
    that cannot find a sentinel proves nothing, so this control puts the same two strings in an
    ordinary file and an ordinary file name and requires the scan to find them in the snapshot,
    in `diff.patch` and in `MANIFEST.json`."""
    holder = "docs/misc/overview.md"
    named = f"docs/misc/{RECORD_NAME}.md"
    files = {holder: f"claim: {CONCLUSION}\n".encode(), named: OVERVIEW}

    _, packet = prepared(staged_naming(files=files))

    places = {path for path, _ in leaks(packet, CONCLUSION, RECORD_NAME)}
    assert places >= {f"snapshot/{holder}", f"snapshot/{named}", "diff.patch", "MANIFEST.json"}
