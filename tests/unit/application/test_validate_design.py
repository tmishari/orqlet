"""`validate design`: the class is recomputed and cannot be lowered (proposal 17.4)."""

from __future__ import annotations

from typing import Any

import pytest

from orqlet.application.usecases.validate_design import validate_design
from orqlet.application.usecases.validation import ValidationResult, content_hash
from orqlet.domain.findings import Verdict
from tests.support.artifacts import (
    AS_IS,
    DESIGN,
    LEDGER,
    TASK_DIR,
    World,
    as_is,
    design,
    design_files,
    dump,
    ledger,
    make_world,
    question,
    with_front_matter,
)

pytestmark = pytest.mark.unit

AS_IS_BYTES = with_front_matter(as_is())


def world_with_design(document: dict[str, Any] | None = None) -> World:
    world = make_world()
    world.put(AS_IS, AS_IS_BYTES)
    for path, data in design_files().items():
        world.put(path, data)
    world.put(DESIGN, dump(document or design(as_is_bytes=AS_IS_BYTES)))
    return world


def run(world: World) -> ValidationResult:
    return validate_design(world.services(), DESIGN)


def codes(result: ValidationResult) -> list[str]:
    return sorted(finding.code for finding in result.findings)


def with_change(**changes: Any) -> dict[str, Any]:
    return design(as_is_bytes=AS_IS_BYTES, **changes)


def test_a_sound_d1_design_passes() -> None:
    result = run(world_with_design())

    assert result.verdict is Verdict.PASS
    assert result.data["trigger_class"] == "D1"
    assert result.data["effective_class"] == "D1"


def test_validation_never_writes() -> None:
    world = world_with_design()
    before = world.project.snapshot()

    run(world)

    assert world.project.snapshot() == before


def test_a_security_surface_triggers_d3_and_a_lower_class_is_refused() -> None:
    document = with_change(
        expected_changes=[
            {
                "id": "EC-1",
                "surface": "security",
                "action": "change",
                "identity": "login",
                "expected_after": {"kind": "paths", "value": "src/pkg/mod.py"},
                "verification": "manual",
            }
        ]
    )

    result = run(world_with_design(document))

    assert result.verdict is Verdict.FAIL
    assert {"ORQ-E360", "ORQ-E361"} <= set(codes(result))
    assert result.data["trigger_class"] == "D3"


def test_a_path_on_a_security_glob_triggers_d3() -> None:
    document = with_change(extractor_config={"security_globs": ["src/pkg/**"]})

    result = run(world_with_design(document))

    assert "ORQ-E360" in codes(result)
    assert "security-sensitive glob" in str(result.data["trigger_reasons"])


def test_a_declared_class_raises_the_effective_class_and_the_artifacts_it_needs() -> None:
    document = with_change(change_class={"trigger": "D1", "declared": "D2", "effective": "D2"})

    result = run(world_with_design(document))

    assert "ORQ-E357" in codes(result)  # a D2 design also needs a container view
    assert "ORQ-E365" in codes(result)  # and the two reviewers' notes


def test_the_effective_class_must_be_the_maximum() -> None:
    document = with_change(change_class={"trigger": "D1", "declared": "D2", "effective": "D1"})

    assert "ORQ-E361" in codes(run(world_with_design(document)))


def test_a_stated_trigger_above_the_computed_one_is_only_noted() -> None:
    document = with_change(change_class={"trigger": "D2", "declared": "D2", "effective": "D2"})

    assert "ORQ-W362" in codes(run(world_with_design(document)))


def test_every_artifact_kind_the_class_requires_must_be_declared() -> None:
    document = with_change()
    document["artifacts"] = [a for a in document["artifacts"] if a["kind"] != "sequence"]

    assert "ORQ-E357" in codes(run(world_with_design(document)))


def test_artifact_files_must_exist_and_match_their_hash() -> None:
    document = with_change()
    document["artifacts"][0]["sha256"] = "0" * 64
    document["artifacts"][1]["path"] = f"{TASK_DIR}/design/missing.md"

    assert {"ORQ-E355", "ORQ-E356"} <= set(codes(run(world_with_design(document))))


def test_an_adr_needs_its_four_sections() -> None:
    document = with_change()
    document["artifacts"][3] = {
        "id": "adr-0001",
        "kind": "adr",
        "path": f"{TASK_DIR}/design/adr-0001.md",
        "covers": "A decision",
        "sha256": "0" * 64,
    }
    world = world_with_design(document)
    broken = b"# ADR 1\n\n## Context\nx\n\n## Decision\ny\n"
    world.put(f"{TASK_DIR}/design/adr-0001.md", broken)
    document["artifacts"][3]["sha256"] = content_hash(broken)
    world.put(DESIGN, dump(document))

    result = run(world)

    assert "ORQ-E358" in codes(result)
    assert "consequences" in result.findings[0].message


def test_a_diagram_file_without_a_mermaid_block_is_only_a_warning() -> None:
    world = world_with_design()
    path = f"{TASK_DIR}/design/component.md"
    world.put(path, b"# Component\n\njust a table\n")
    document = with_change()
    document["artifacts"][0]["sha256"] = content_hash(b"# Component\n\njust a table\n")
    world.put(DESIGN, dump(document))

    result = run(world)

    assert result.verdict is Verdict.PASS
    assert codes(result) == ["ORQ-W359"]


def test_the_as_is_reference_must_resolve_and_match() -> None:
    bad_form = with_change(as_is_ref="docs/design/demo/as-is.md")
    assert "ORQ-E351" in codes(run(world_with_design(bad_form)))

    missing = with_change(as_is_ref=f"docs/design/demo/nothing.md#{'0' * 64}")
    assert "ORQ-E352" in codes(run(world_with_design(missing)))

    changed = with_change(as_is_ref=f"{AS_IS}#{'0' * 64}")
    assert "ORQ-E353" in codes(run(world_with_design(changed)))


def test_an_extractor_is_only_allowed_where_this_release_has_one_and_where_it_looks() -> None:
    def change(surface: str, verification: str) -> dict[str, Any]:
        return {
            "id": "EC-1",
            "surface": surface,
            "action": "add",
            "identity": "x",
            "expected_after": {"kind": "declaration", "value": "x"},
            "verification": verification,
        }

    contract = run(
        world_with_design(with_change(expected_changes=[change("http-contract", "extractor")]))
    )
    unconfigured = run(
        world_with_design(with_change(expected_changes=[change("public-api", "extractor")]))
    )
    configured = run(
        world_with_design(
            with_change(
                expected_changes=[change("public-api", "extractor")],
                extractor_config={"public_api": {"packages": ["pkg"], "mode": "ast"}},
                change_class={"trigger": "D2", "declared": "D2", "effective": "D2"},
            )
        )
    )
    manual = run(
        world_with_design(with_change(expected_changes=[change("http-contract", "manual")]))
    )

    assert "ORQ-E364" in codes(contract)
    assert "ORQ-E364" in codes(unconfigured)
    assert "ORQ-E364" not in codes(configured)
    assert "ORQ-E364" not in codes(manual)


def test_duplicate_artifact_and_expected_change_ids_are_refused() -> None:
    document = with_change()
    document["artifacts"].append(dict(document["artifacts"][0]))
    change = {
        "id": "EC-1",
        "surface": "dependency",
        "action": "add",
        "identity": "x",
        "expected_after": {"kind": "specifier", "value": ">=1"},
        "verification": "manual",
    }
    document["expected_changes"] = [change, dict(change)]

    assert {"ORQ-E354", "ORQ-E363"} <= set(codes(run(world_with_design(document))))


def test_d2_and_above_need_both_reviewer_notes_and_the_notes_must_exist() -> None:
    document = with_change(
        change_class={"trigger": "D2", "declared": "D2", "effective": "D2"},
        reviews=[{"role": "architecture-reviewer", "note": f"{TASK_DIR}/reviews/arch.md"}],
    )
    document["artifacts"].append(
        {**document["artifacts"][0], "id": "container", "kind": "c4-container"}
    )

    result = run(world_with_design(document))

    assert {"ORQ-E365", "ORQ-E366"} <= set(codes(result))


def test_an_open_question_that_blocks_design_fails_it() -> None:
    world = world_with_design()
    world.put_yaml(LEDGER, ledger(questions=[question(1, blocks=["design"])]))

    assert "ORQ-E367" in codes(run(world))


def test_the_header_task_must_match_the_folder() -> None:
    document = design(task="other", as_is_bytes=AS_IS_BYTES)

    assert "ORQ-E350" in codes(run(world_with_design(document)))
