"""The two hard-coded reviewer maps agree, and both hold the three reviewers (task
dynamic-model-profiles, phase P-9, AC-2).

`REVIEW_AGENTS` (render_all.py) says which reviewers `init` seeds a binding for, and
`DEFAULT_REVIEWERS` (review_prepare.py) says which agent files `review prepare` prints a
`review_input` block for. They stay hard-coded (ADR-006 decision 6), so nothing but these tests
keeps them in step with each other and with the role literal of the binding contract. The seeded
binding of the third reviewer is tested in test_lifecycle.py.

Every test cites its `expected_behavior_source`: AC-2 of phase P-9 in
docs/design/dynamic-model-profiles/plan.yaml, BC-41 and EC-5 of the design, and ADR-006 decision 6.
These tests were written first, by the Tester of phase P-9, before the third reviewer was added.
"""

from __future__ import annotations

from typing import get_args

import pytest

from orqlet.application.contracts.role_bindings import Binding
from orqlet.application.usecases.render_all import REVIEW_AGENTS
from orqlet.application.usecases.review_prepare import DEFAULT_REVIEWERS

pytestmark = pytest.mark.unit

THREE_REVIEWERS = {
    "architecture-reviewer": "orqlet-arch-reviewer",
    "security-reviewer": "orqlet-security-reviewer",
    "code-reviewer": "orqlet-code-reviewer",
}


def test_the_two_maps_hold_the_same_roles_and_the_same_agent_names() -> None:
    """expected_behavior_source: AC-2 ("a unit test asserts that the two maps hold the same roles
    and the same agent names"); ADR-006 decision 6 (the two maps "stay hard-coded ... but gain the
    third entry, with a unit test that asserts they agree"). This holds before the third reviewer
    is added too: both maps hold the same two."""
    assert dict(REVIEW_AGENTS) == DEFAULT_REVIEWERS


def test_review_agents_holds_the_three_reviewers_in_the_order_of_the_contract() -> None:
    """expected_behavior_source: AC-2 ("`REVIEW_AGENTS` and `DEFAULT_REVIEWERS` each hold the three
    reviewers (`architecture-reviewer` and `orqlet-arch-reviewer`, `security-reviewer` and
    `orqlet-security-reviewer`, `code-reviewer` and `orqlet-code-reviewer`)"); the interface of the
    brief for the order of the tuple."""
    assert tuple(THREE_REVIEWERS.items()) == REVIEW_AGENTS


def test_default_reviewers_holds_exactly_the_three_reviewers() -> None:
    """expected_behavior_source: AC-2 (as above: each map holds the three reviewers); ADR-006
    decision 6."""
    assert DEFAULT_REVIEWERS == THREE_REVIEWERS


def test_neither_map_names_a_role_or_an_agent_twice() -> None:
    """expected_behavior_source: AC-2 (each map holds the three reviewers, so no role and no agent
    is listed twice); ADR-006 decision 6. The tuple is checked, not `dict(REVIEW_AGENTS)`, which
    would hide a role that is listed twice."""
    roles = [role for role, _ in REVIEW_AGENTS]
    agents = [agent for _, agent in REVIEW_AGENTS]

    assert len(set(roles)) == len(roles)
    assert len(set(agents)) == len(agents)
    assert len(set(DEFAULT_REVIEWERS.values())) == len(DEFAULT_REVIEWERS)


def test_the_roles_of_both_maps_are_exactly_the_roles_of_the_binding_contract() -> None:
    """expected_behavior_source: AC-2 (its sources: BC-41; EC-5; ADR-006 decision 6, "Everything
    that knows the two reviewer roles gains the third", `Binding.role` among them); the brief of
    this phase's Tester (the three roles are exactly the arguments of the Literal of
    `Binding.role`). A seeded binding of a role that the contract refuses would make `init` write
    a file that does not load."""
    contract_roles = set(get_args(Binding.model_fields["role"].annotation))

    assert contract_roles == {role for role, _ in REVIEW_AGENTS}
    assert contract_roles == set(DEFAULT_REVIEWERS)
