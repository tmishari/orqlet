"""The plan check does not depend on the order phases are written in, and is symmetric."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.domain.plan_projection import FileOperation, Op, PlanPhase, TreeEntry, check_plan

pytestmark = pytest.mark.unit

PATHS = st.sampled_from(["a.py", "b.py", "pkg/c.py", "pkg/d.py", "pkg", "pkg/c.py/x"])
OPERATIONS = st.builds(FileOperation, st.sampled_from(Op), PATHS)
TREES = st.lists(st.sampled_from(["a.py", "pkg/c.py"]), unique=True, max_size=2).map(
    lambda paths: [TreeEntry(path) for path in paths]
)


@st.composite
def plans(draw: st.DrawFn) -> list[PlanPhase]:
    count = draw(st.integers(min_value=1, max_value=4))
    ids = [f"P{n}" for n in range(1, count + 1)]
    phases = []
    for index, phase_id in enumerate(ids):
        earlier = draw(st.lists(st.sampled_from(ids[:index]), unique=True)) if index else []
        operations = tuple(draw(st.lists(OPERATIONS, max_size=3)))
        phases.append(PlanPhase(phase_id, tuple(earlier), operations))
    return phases


@given(TREES, plans(), st.randoms(use_true_random=False))
def test_the_order_phases_are_written_in_does_not_change_the_result(
    tree: list[TreeEntry], phases: list[PlanPhase], random: object
) -> None:
    shuffled = list(phases)
    random.shuffle(shuffled)  # type: ignore[attr-defined]

    assert check_plan(tree, phases) == check_plan(tree, shuffled)


@given(TREES, plans())
def test_a_plan_with_no_operations_never_has_findings(
    tree: list[TreeEntry], phases: list[PlanPhase]
) -> None:
    empty = [PlanPhase(p.id, p.depends_on) for p in phases]

    assert check_plan(tree, empty) == ()


@given(PATHS, PATHS)
def test_the_concurrency_rule_is_symmetric(first: str, second: str) -> None:
    left = [
        PlanPhase("P1", (), (FileOperation(Op.CREATE, first),)),
        PlanPhase("P2", (), (FileOperation(Op.CREATE, second),)),
    ]
    right = [
        PlanPhase("P1", (), (FileOperation(Op.CREATE, second),)),
        PlanPhase("P2", (), (FileOperation(Op.CREATE, first),)),
    ]

    assert bool(check_plan([], left)) == bool(check_plan([], right))
