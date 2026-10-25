"""Independence classes: derived from recorded identifiers, never above I2 (17.12.5)."""

from __future__ import annotations

import pytest

from orqlet.domain.change_class import ChangeClass
from orqlet.domain.independence import (
    Independence,
    derive_independence,
    family_of,
    minimum_independence,
    satisfies,
)

pytestmark = pytest.mark.unit

FAMILIES = (("claude-*", "anthropic"), ("gpt-*", "openai"))


def derive(**overrides: object) -> Independence:
    arguments: dict[str, object] = {
        "approved_binding": True,
        "agent_client": "cursor",
        "agent_family": "anthropic",
        "coder_client": "cursor",
        "coder_family": "anthropic",
        **overrides,
    }
    return derive_independence(**arguments)  # type: ignore[arg-type]


def test_a_binding_that_is_not_approved_is_i0_whatever_else_is_true() -> None:
    assert derive(approved_binding=False, agent_client="codex") is Independence.I0


def test_an_approved_binding_in_the_same_client_and_family_is_i1() -> None:
    assert derive() is Independence.I1


def test_another_client_or_another_model_family_is_i2() -> None:
    assert derive(agent_client="claude-code") is Independence.I2
    assert derive(agent_family="openai") is Independence.I2


def test_a_family_that_is_unknown_on_either_side_cannot_show_a_difference() -> None:
    assert derive(agent_family=None) is Independence.I1
    assert derive(coder_family=None) is Independence.I1


def test_no_recorded_identifier_can_make_a_review_i3() -> None:
    for client in ("cursor", "codex", "claude-code", "a-human"):
        assert derive(agent_client=client, agent_family="openai") < Independence.I3


def test_the_first_matching_pattern_names_the_family_and_none_matches_to_unknown() -> None:
    assert family_of("claude-opus-9", FAMILIES) == "anthropic"
    assert family_of("gpt-7", FAMILIES) == "openai"
    assert family_of("llama-3", FAMILIES) is None
    assert family_of(None, FAMILIES) is None


@pytest.mark.parametrize(
    ("change_class", "minimum"),
    [
        (ChangeClass.D1, Independence.I1),
        (ChangeClass.D2, Independence.I1),
        (ChangeClass.D3, Independence.I2),
    ],
)
def test_d3_requires_i2_and_the_others_i1(change_class: ChangeClass, minimum: Independence) -> None:
    assert minimum_independence(change_class) is minimum


def test_i0_never_satisfies_a_gate_and_i1_does_not_satisfy_d3() -> None:
    assert not any(satisfies(Independence.I0, c) for c in ChangeClass)
    assert satisfies(Independence.I1, ChangeClass.D2)
    assert not satisfies(Independence.I1, ChangeClass.D3)
    assert satisfies(Independence.I2, ChangeClass.D3)
    assert satisfies(Independence.I3, ChangeClass.D3)
