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
from orqlet.domain.findings import Verdict
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED
from tests.support.artifacts import TASK_DIR, design, dump, phase, plan

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
