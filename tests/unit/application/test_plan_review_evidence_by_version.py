"""Plan review evidence by workflow version (task dynamic-model-profiles, P-1).

Each test names in `expected_behavior_source` the criterion that it checks (AC-6 of phase P-1 in
docs/design/dynamic-model-profiles/plan.yaml) and then the sources that the criterion lists. EC-4
is the expected change of design/manifest.yaml, BC-15 a behaviour row of design/component.md, and
ADR-006 the decision record on the code reviewer.

These tests were written first, by the Tester of phase P-1, before the change existed. They build
a plan with `plan` and `phase` of tests/support/artifacts.py and change what is under test: the
`review_evidence` of each phase and the `workflow_version` of the header.

The criterion leaves these open, so no test requires or refuses them:
- the order of the roles in a phase (a set is what the criterion names, so one test lets the
  order vary);
- the wording and the location of a message;
- a `workflow_version` of another artifact than a plan.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.plan import ImplementationPlan, Phase
from tests.support.artifacts import phase, plan

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
THIS_TASKS_PLAN = ROOT / "docs" / "design" / "dynamic-model-profiles" / "plan.yaml"

THREE = ["architecture-reviewer", "security-reviewer", "tester"]
FOUR = [*THREE, "code-reviewer"]

# Versions below 0.5.0, and at or above it. 0.10.0 and 0.4.100 are above and below 0.5.0 as
# numbers; compared as text each is on the other side.
BELOW = ["0.0.1", "0.1.0", "0.4.0", "0.4.9", "0.4.100"]
AT_OR_ABOVE = ["0.5.0", "0.5.1", "0.10.0", "0.100.0", "1.0.0", "10.0.0"]
NOT_A_VERSION = [
    "0.5",
    "5",
    "1.0",
    "v0.5.0",
    "0.5.0.1",
    "0.5.x",
    "latest",
    "",
    "0.5.0-rc.1",
    "0.5.0+build",
    " 0.5.0",
    "0.5.0 ",
    "0.5.0\n",
    "0.05.0",
    "-1.0.0",
]
# Every other set of roles: the criterion refuses all that are not THREE or FOUR, each once.
OTHER_SETS = {
    "none": [],
    "the-tester-only": ["tester"],
    "the-code-reviewer-only": ["code-reviewer"],
    "the-two-reviewers": ["architecture-reviewer", "security-reviewer"],
    "an-architecture-reviewer-and-a-tester": ["architecture-reviewer", "tester"],
    "a-security-reviewer-and-a-tester": ["security-reviewer", "tester"],
    "a-tester-and-a-code-reviewer": ["tester", "code-reviewer"],
    "no-tester": ["architecture-reviewer", "security-reviewer", "code-reviewer"],
    "no-security-reviewer": ["architecture-reviewer", "tester", "code-reviewer"],
    "no-architecture-reviewer": ["security-reviewer", "tester", "code-reviewer"],
    "the-tester-twice": [*THREE, "tester"],
    "the-architecture-reviewer-twice": ["architecture-reviewer", *THREE],
    "the-code-reviewer-twice": [*FOUR, "code-reviewer"],
    "the-four-and-a-tester-again": [*FOUR, "tester"],
    "the-code-reviewer-four-times": ["code-reviewer"] * 4,
    "a-fourth-role-that-is-unknown": [*THREE, "author"],
    "an-unknown-role-for-the-code-reviewer": [*THREE, "Code-Reviewer"],
    "an-unknown-role-in-place-of-the-tester": ["architecture-reviewer", "security-reviewer", "x"],
}


def plan_at(version: str, *phases: Sequence[str]) -> dict[str, Any]:
    """A plan that says `version` in its header, with one phase for each list of roles."""
    built = [phase(number, review_evidence=list(roles)) for number, roles in enumerate(phases, 1)]
    document = plan(phases=built)
    document["header"]["workflow_version"] = version
    return document


# --- a phase on its own ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "roles",
    [
        THREE,
        FOUR,
        ["tester", "security-reviewer", "architecture-reviewer"],
        ["code-reviewer", "tester", "security-reviewer", "architecture-reviewer"],
    ],
    ids=["three", "four", "three-in-another-order", "four-in-another-order"],
)
def test_a_phase_accepts_the_three_roles_or_the_three_and_the_code_reviewer(
    roles: list[str],
) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    A phase accepts `review_evidence` that is exactly the three roles of today or those three plus
    `code-reviewer`, each once.
    """
    loaded = Phase.model_validate(phase(1, review_evidence=roles))

    assert sorted(loaded.review_evidence) == sorted(roles)


@pytest.mark.parametrize("roles", list(OTHER_SETS.values()), ids=list(OTHER_SETS))
def test_a_phase_refuses_every_other_set_of_roles(roles: list[str]) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    A phase refuses every set of `review_evidence` other than the three roles, or the three plus
    `code-reviewer`, each once.
    """
    with pytest.raises(ValidationError):
        Phase.model_validate(phase(1, review_evidence=roles))


# --- a plan below 0.5.0 ------------------------------------------------------------------------


@pytest.mark.parametrize("version", BELOW)
def test_a_plan_below_0_5_0_that_holds_the_three_roles_in_every_phase_loads(version: str) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    A plan whose `header.workflow_version` is below 0.5.0 must hold exactly the three roles.
    """
    loaded = ImplementationPlan.model_validate(plan_at(version, THREE, THREE))

    assert loaded.header.workflow_version == version
    assert all(sorted(each.review_evidence) == sorted(THREE) for each in loaded.phases)


@pytest.mark.parametrize("version", BELOW)
def test_a_plan_below_0_5_0_that_holds_the_four_roles_is_refused(version: str) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    A plan whose `header.workflow_version` is below 0.5.0 must hold exactly the three roles, so
    the four are refused there.
    """
    with pytest.raises(ValidationError):
        ImplementationPlan.model_validate(plan_at(version, FOUR, FOUR))


# --- a plan at or above 0.5.0 ------------------------------------------------------------------


@pytest.mark.parametrize("version", AT_OR_ABOVE)
def test_a_plan_at_or_above_0_5_0_that_holds_the_four_roles_in_every_phase_loads(
    version: str,
) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    A plan whose `header.workflow_version` is 0.5.0 or higher (compared as `Version` values, so
    0.10.0 is above 0.5.0) must hold the four roles in every phase.
    """
    loaded = ImplementationPlan.model_validate(plan_at(version, FOUR, FOUR))

    assert loaded.header.workflow_version == version
    assert all(sorted(each.review_evidence) == sorted(FOUR) for each in loaded.phases)


@pytest.mark.parametrize("version", AT_OR_ABOVE)
def test_a_plan_at_or_above_0_5_0_that_holds_the_three_roles_is_refused(version: str) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    A plan whose `header.workflow_version` is 0.5.0 or higher must hold the four roles, so the
    three are refused there (0.10.0 is compared as a number, not as text).
    """
    with pytest.raises(ValidationError):
        ImplementationPlan.model_validate(plan_at(version, THREE, THREE))


@pytest.mark.parametrize("version", ["0.4.0", "0.5.0"])
@pytest.mark.parametrize(
    "phases",
    [(THREE, FOUR), (FOUR, THREE)],
    ids=["the-second-phase-has-the-four", "the-first-phase-has-the-four"],
)
def test_a_plan_with_one_phase_of_each_kind_is_refused_at_either_side_of_the_boundary(
    version: str, phases: tuple[list[str], list[str]]
) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    A plan below 0.5.0 holds exactly the three, and a plan at or above it holds the four, "in
    every phase", so a plan that mixes the two sets fails on either side.
    """
    with pytest.raises(ValidationError):
        ImplementationPlan.model_validate(plan_at(version, *phases))


@pytest.mark.parametrize("version", ["0.4.0", "0.5.0", "0.10.0"])
@pytest.mark.parametrize("roles", list(OTHER_SETS.values()), ids=list(OTHER_SETS))
def test_a_plan_refuses_every_other_set_of_roles_at_any_version(
    version: str, roles: list[str]
) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    The version chooses between the three and the four; no version makes any other set valid.
    """
    with pytest.raises(ValidationError):
        ImplementationPlan.model_validate(plan_at(version, roles))


# --- the version itself ------------------------------------------------------------------------


@pytest.mark.parametrize("roles", [THREE, FOUR], ids=["three", "four"])
@pytest.mark.parametrize("version", NOT_A_VERSION)
def test_a_version_that_is_not_major_minor_patch_is_refused(version: str, roles: list[str]) -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    A version that is not `major.minor.patch` is refused, whichever set of roles the plan holds.
    `0.05.0` has a leading zero, which `Version.parse` refuses.
    """
    with pytest.raises(ValidationError):
        ImplementationPlan.model_validate(plan_at(version, roles))


# --- the plan of this task ---------------------------------------------------------------------


def test_the_plan_of_this_task_still_loads() -> None:
    """expected_behavior_source: AC-6; EC-4; BC-15; ADR-006 decision 3.

    The plan of this task (`workflow_version` 0.4.0, three roles) still loads.
    """
    loaded = load_contract(
        StrictYamlLoader(),
        ImplementationPlan,
        THIS_TASKS_PLAN.read_bytes(),
        source="docs/design/dynamic-model-profiles/plan.yaml",
    )

    assert loaded.header.workflow_version == "0.4.0"
    assert all(sorted(each.review_evidence) == sorted(THREE) for each in loaded.phases)
