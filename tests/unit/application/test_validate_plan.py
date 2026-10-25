"""`validate plan`: the projected tree, the design it implements and the knowledge scope."""

from __future__ import annotations

from typing import Any

import pytest

from orqlet.application.usecases.validate_plan import validate_plan
from orqlet.application.usecases.validation import ValidationResult
from orqlet.domain.findings import Verdict
from tests.support.artifacts import (
    BASE,
    DESIGN,
    LEDGER,
    PLAN,
    World,
    as_is,
    design,
    design_files,
    dump,
    ledger,
    make_world,
    phase,
    plan,
    question,
    with_front_matter,
)

pytestmark = pytest.mark.unit

AS_IS_BYTES = with_front_matter(as_is())


def world_for(
    document: dict[str, Any] | None = None,
    *,
    design_document: dict[str, Any] | None = None,
    **world_args: Any,
) -> World:
    world = make_world(**world_args)
    for path, data in design_files().items():
        world.put(path, data)
    design_text = dump(design_document or design(as_is_bytes=AS_IS_BYTES))
    world.put(DESIGN, design_text)
    world.put(PLAN, dump(document or plan(design_bytes=design_text.encode())))
    return world


def run(world: World) -> ValidationResult:
    return validate_plan(world.services(), PLAN)


def codes(result: ValidationResult) -> list[str]:
    return sorted(finding.code for finding in result.findings)


def plan_for(
    world_design: dict[str, Any] | None = None, **overrides: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    design_document = world_design or design(as_is_bytes=AS_IS_BYTES)
    return design_document, plan(design_bytes=dump(design_document).encode(), **overrides)


def build(world_design: dict[str, Any] | None = None, **overrides: Any) -> World:
    design_document, document = plan_for(world_design, **overrides)
    return world_for(document, design_document=design_document)


def test_a_sound_plan_passes_and_reports_what_changes_the_tree() -> None:
    result = run(world_for())

    assert result.verdict is Verdict.PASS
    assert result.data["structural_changes"] == ["P-1: create src/pkg/service.py"]
    assert result.data["phases"] == 1


def test_validation_never_writes() -> None:
    world = world_for()
    before = world.project.snapshot()

    run(world)

    assert world.project.snapshot() == before


def test_the_projection_findings_of_the_domain_are_reported() -> None:
    document = phase(
        file_operations=[{"op": "create", "path": "src/pkg/mod.py", "why": "It already exists"}]
    )

    result = run(build(phases=[document]))

    assert result.verdict is Verdict.FAIL
    assert codes(result) == ["ORQ-E308"]


def test_a_later_phase_can_extend_what_an_earlier_one_created() -> None:
    second = phase(
        2,
        depends_on=["P-1"],
        file_operations=[{"op": "modify", "path": "src/pkg/service.py", "why": "Extend it"}],
    )

    assert run(build(phases=[phase(1), second])).verdict is Verdict.PASS


def test_an_unknown_revision_is_not_run() -> None:
    result = run(world_for(commits=False))

    assert result.verdict is Verdict.NOT_RUN
    assert codes(result) == []


def test_the_design_reference_must_resolve_and_match() -> None:
    assert "ORQ-E371" in codes(run(build(design_ref="docs/design/demo/design/manifest.yaml")))
    assert "ORQ-E371" in codes(run(build(design_ref=f"docs/design/demo/nothing.yaml#{'0' * 64}")))
    assert "ORQ-E371" in codes(run(build(design_ref=f"{DESIGN}#{'0' * 64}")))


def test_a_phase_needs_acceptance_criteria_that_map_to_a_check_or_a_review_item() -> None:
    none = phase(acceptance_criteria=[])
    unmapped = phase(
        acceptance_criteria=[
            {"id": "AC-1", "text": "It works", "source": "Q-1", "check_ref": "vibes"}
        ]
    )
    review = phase(
        acceptance_criteria=[
            {
                "id": "AC-1",
                "text": "It is secure",
                "source": "Q-1",
                "check_ref": "security-reviewer",
            }
        ]
    )

    assert "ORQ-E374" in codes(run(build(phases=[none])))
    assert "ORQ-E375" in codes(run(build(phases=[unmapped])))
    assert run(build(phases=[review])).verdict is Verdict.PASS


def test_duplicate_phase_and_criterion_ids_are_refused() -> None:
    twice = phase(
        acceptance_criteria=[
            {"id": "AC-1", "text": "One", "source": "Q-1", "check_ref": "tests"},
            {"id": "AC-1", "text": "Two", "source": "Q-1", "check_ref": "tests"},
        ]
    )

    assert "ORQ-E373" in codes(run(build(phases=[twice])))
    assert "ORQ-E373" in codes(run(build(phases=[phase(1), phase(1)])))


CHANGE = {
    "id": "EC-1",
    "surface": "dependency",
    "action": "add",
    "identity": "requests",
    "expected_after": {"kind": "specifier", "value": ">=2"},
    "stages": [{"id": "S-1", "expected_after": {"kind": "specifier", "value": ">=2"}}],
    "verification": "manual",
}


def with_change() -> dict[str, Any]:
    return design(
        as_is_bytes=AS_IS_BYTES,
        expected_changes=[CHANGE],
        change_class={"trigger": "D2", "declared": "D2", "effective": "D2"},
        reviews=[],
    )


def test_a_phase_may_implement_a_declared_change_or_one_of_its_stages() -> None:
    document = with_change()
    document["artifacts"].append(
        {**document["artifacts"][0], "id": "container", "kind": "c4-container"}
    )

    result = run(build(document, phases=[phase(implements=["EC-1@S-1"])]))

    assert "ORQ-E376" not in codes(result)
    assert "ORQ-W377" not in codes(result)


def test_implementing_something_the_design_does_not_declare_is_refused() -> None:
    result = run(build(with_change(), phases=[phase(implements=["EC-9", "EC-1@S-9"])]))

    assert codes(result).count("ORQ-E376") == 2


def test_a_declared_change_that_no_phase_selects_is_a_warning() -> None:
    result = run(build(with_change(), phases=[phase(implements=[])]))

    assert "ORQ-W377" in codes(result)


def test_the_plan_cannot_trigger_a_class_above_the_approved_design() -> None:
    risky = phase(
        file_operations=[{"op": "create", "path": "src/pkg/auth/login.py", "why": "Login"}]
    )
    document = design(
        as_is_bytes=AS_IS_BYTES, extractor_config={"security_globs": ["src/pkg/auth/**"]}
    )
    document["scope"]["paths"] = ["src/pkg/mod.py"]

    result = run(build(document, phases=[risky]))

    assert "ORQ-E378" in codes(result)


def test_amends_is_a_plan_hash() -> None:
    assert "ORQ-E379" in codes(run(build(amends="the first plan")))
    assert "ORQ-E379" not in codes(run(build(amends="a" * 64)))


@pytest.mark.parametrize(
    "scope",
    [[".claude/**"], ["src/orqlet/workflow/**"], ["AGENTS.md"], ["src/**"], ["pyproject.toml"]],
)
def test_a_knowledge_scope_cannot_reach_agent_configuration_workflow_files_or_code(
    scope: list[str],
) -> None:
    assert "ORQ-E386" in codes(run(build(knowledge_scope=scope)))


def test_a_knowledge_scope_over_documentation_is_accepted() -> None:
    assert run(build(knowledge_scope=["docs/**"])).verdict is Verdict.PASS


def test_an_open_question_that_blocks_the_plan_fails_it() -> None:
    world = build()
    world.put_yaml(LEDGER, ledger(questions=[question(1, blocks=["plan"])]))

    assert "ORQ-E387" in codes(run(world))


def test_the_plan_names_its_base_revision_and_its_header_task() -> None:
    _, document = plan_for(task="other")

    assert "ORQ-E370" in codes(run(world_for(document)))
    assert BASE in dump(document)
