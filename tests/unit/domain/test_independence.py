"""Independence classes: derived from recorded identifiers, never above I2 (17.12.5).

The tests from `# --- phase P-9` on were written first, by the Tester of phase P-9 of the task
dynamic-model-profiles, before the implementation existed. Each cites its
`expected_behavior_source`: AC-n are the acceptance criteria of P-9 in
docs/design/dynamic-model-profiles/plan.yaml, BC-n, C-n and R-n the rows of design/component.md,
and ADR-006 and ADR-007 the decision records of design/. "The interface" is the interface that the
brief of the Tester states for the Coder; where it makes a choice that the plan leaves open, the
test says so. The names that the phase adds are read when a test runs, so that one missing name
fails one test and not the collection of the file.
"""

from __future__ import annotations

import ast
import builtins
import importlib
import inspect
import io
import itertools
import os
import pathlib
import sys
import time
from collections.abc import Callable
from typing import Any, NoReturn

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


# --- phase P-9: freshness, observed identities and the role of the minimum ----------------------
OTHER_ROLES: tuple[str, ...] = ("architecture-reviewer", "security-reviewer")
ROLES: tuple[str | None, ...] = (None, *OTHER_ROLES, "code-reviewer")
ROLE_IDS = ["no-role", "architecture", "security", "code"]
FRESHNESS: tuple[bool | None, ...] = (None, True, False)
FRESHNESS_IDS = ["not-recorded", "fresh", "not-fresh"]
CLIENT_PAIRS: tuple[tuple[str, str], ...] = (("cursor", "cursor"), ("cursor", "codex"))
# A side of a record is its family and whether its identity was observed. A side that is omitted
# has no family and is not observed.
Side = tuple[str | None, bool]
RECORDED_SIDES: tuple[Side, ...] = (("x", True), ("y", True))
OMITTED_SIDE: Side = (None, False)
SIDES: tuple[Side, ...] = (*RECORDED_SIDES, OMITTED_SIDE)
AGENT_FAMILIES: tuple[str | None, ...] = (None, "x")
CODER_FAMILIES: tuple[str | None, ...] = (None, "x", "y")
# Every combination of approval, freshness, role, equal or different client and the two sides.
FULL_GRID = list(
    itertools.product(
        (True, False),
        FRESHNESS,
        ROLES,
        CLIENT_PAIRS,
        SIDES,
        SIDES,
    )
)
# The arguments of the base revision: approval, clients, and the two families.
OLD_ARGUMENT_GRID = list(
    itertools.product(
        (True, False),
        CLIENT_PAIRS,
        AGENT_FAMILIES,
        CODER_FAMILIES,
    )
)


def new(name: str) -> Any:
    """A name that phase P-9 adds, read when a test runs."""
    return getattr(importlib.import_module("orqlet.domain.independence"), name)


def derived(
    approved: bool,
    fresh: bool | None,
    role: str | None,
    clients: tuple[str, str],
    agent_side: Side,
    coder_side: Side,
) -> Independence:
    return derive(
        approved_binding=approved,
        agent_client=clients[0],
        agent_family=agent_side[0],
        agent_observed=agent_side[1],
        coder_client=clients[1],
        coder_family=coder_side[0],
        coder_observed=coder_side[1],
        fresh=fresh,
        role=role,
    )


def derive_at_the_base_revision(
    *,
    approved_binding: bool,
    agent_client: str,
    agent_family: str | None,
    coder_client: str,
    coder_family: str | None,
) -> Independence:
    """`derive_independence` as it stood at the base revision of phase P-9, copied here."""
    if not approved_binding:
        return Independence.I0
    different_client = agent_client != coder_client
    different_family = (
        agent_family is not None and coder_family is not None and agent_family != coder_family
    )
    return Independence.I2 if different_client or different_family else Independence.I1


def minimum_at_the_base_revision(change_class: ChangeClass) -> Independence:
    """`minimum_independence` as it stood at the base revision of phase P-9, copied here."""
    return Independence.I2 if change_class is ChangeClass.D3 else Independence.I1


def minimum_of_the_role(change_class: ChangeClass, role: str | None) -> Independence:
    """The minimum that the interface states: I2 for the code reviewer, else as before."""
    if role == "code-reviewer":
        return Independence.I2
    return minimum_at_the_base_revision(change_class)


def old_arguments(
    approved: bool, clients: tuple[str, str], agent_family: str | None, coder_family: str | None
) -> dict[str, Any]:
    return {
        "approved_binding": approved,
        "agent_client": clients[0],
        "agent_family": agent_family,
        "coder_client": clients[1],
        "coder_family": coder_family,
    }


def test_the_names_that_the_phase_adds_hold_the_values_of_the_interface() -> None:
    """expected_behavior_source: AC-3 and AC-4; ADR-007 decision 2 (`client-reported` and
    `person-observed` are observed, `unknown` is not), decision 4 (the role that requires
    freshness is the code reviewer) and decision 5 (the two closed warnings); the interface for
    the order of the closed set (the order in which AC-4 names them)."""
    assert new("OBSERVED_SOURCES") == frozenset({"client-reported", "person-observed"})
    assert new("CODE_REVIEWER") == "code-reviewer"
    assert new("IDENTITY_UNKNOWN") == "identity-unknown"
    assert new("SAME_MODEL_DIFFERENT_CLIENT") == "same-model-different-client"
    assert new("INDEPENDENCE_NOTES") == ("identity-unknown", "same-model-different-client")


@pytest.mark.parametrize(
    ("identity_source", "model_observed", "expected"),
    [
        ("client-reported", "example-model-1", True),
        ("person-observed", "example-model-1", True),
        ("client-reported", None, False),
        ("person-observed", None, False),
        ("unknown", "example-model-1", False),
        ("unknown", None, False),
        (None, "example-model-1", False),
        (None, None, False),
        ("Client-Reported", "example-model-1", False),
        ("requested", "example-model-1", False),
    ],
    ids=[
        "client-reported",
        "person-observed",
        "client-reported-without-a-model",
        "person-observed-without-a-model",
        "unknown-source",
        "unknown-source-without-a-model",
        "missing-source",
        "missing-source-without-a-model",
        "source-is-case-sensitive",
        "a-source-that-is-not-in-the-set",
    ],
)
def test_only_a_model_with_an_observed_source_is_an_observed_identity(
    identity_source: str | None,
    model_observed: str | None,
    expected: bool,
) -> None:
    """expected_behavior_source: AC-3 ("a requested-only model, or `identity_source` unknown, is
    an unknown identity ... A missing `identity_source` means unknown"); ADR-007 decision 2
    (only an observed identity counts; `client-reported` and `person-observed` are the observed
    sources); the interface (`is_observed`)."""
    assert new("is_observed")(identity_source, model_observed) is expected


# --- AC-3: the class that derive_independence gives ---------------------------------------------


@pytest.mark.parametrize("fresh", FRESHNESS, ids=FRESHNESS_IDS)
@pytest.mark.parametrize("role", ROLES, ids=ROLE_IDS)
def test_a_binding_that_is_not_approved_is_i0_for_every_role_and_every_freshness(
    role: str | None,
    fresh: bool | None,
) -> None:
    """expected_behavior_source: AC-3 ("I0 for an unapproved binding"); BC-19; ADR-007 decision
    5 (I0 for an unapproved binding stays). The other facts would give I2."""
    result = derive(approved_binding=False, agent_client="codex", fresh=fresh, role=role)

    assert result is Independence.I0


@pytest.mark.parametrize("role", ROLES, ids=ROLE_IDS)
def test_a_context_recorded_as_not_fresh_is_i0_for_every_role(role: str | None) -> None:
    """expected_behavior_source: AC-3 ("I0 ... for a context recorded as not fresh"); ADR-007
    decision 4 (for the other two roles "a `false` value gives I0"). A different client would
    give I2."""
    result = derive(agent_client="claude-code", fresh=False, role=role)

    assert result is Independence.I0


@pytest.mark.parametrize("fresh", [None, False], ids=["not-recorded", "not-fresh"])
def test_the_code_reviewer_without_a_fresh_context_is_i0_even_in_another_client(
    fresh: bool | None,
) -> None:
    """expected_behavior_source: AC-3 ("for a role that requires freshness (the code reviewer),
    for a context that is not recorded as fresh"); ADR-007 decision 4 ("a missing or false value
    gives I0 for that role")."""
    result = derive(agent_client="claude-code", fresh=fresh, role="code-reviewer")

    assert result is Independence.I0


def test_a_fresh_code_review_gets_the_class_of_its_clients_and_families() -> None:
    """expected_behavior_source: AC-3 ("Otherwise it gives I2 for a different client or for two
    different families that are both known from observed identities, and I1 for the rest");
    ADR-007 decision 5; ADR-006 decision 5 ("A new session of the same client is I1")."""
    code = {"role": "code-reviewer", "fresh": True, "agent_observed": True, "coder_observed": True}

    assert derive(agent_client="claude-code", **code) is Independence.I2
    assert derive(**code) is Independence.I1  # the same client and the same observed family
    assert derive(agent_family="openai", **code) is Independence.I2


@pytest.mark.parametrize(
    ("fresh", "different_client", "same_client"),
    [
        (None, Independence.I2, Independence.I1),
        (True, Independence.I2, Independence.I1),
        (False, Independence.I0, Independence.I0),
    ],
    ids=FRESHNESS_IDS,
)
def test_freshness_is_only_required_of_the_code_reviewer(
    fresh: bool | None,
    different_client: Independence,
    same_client: Independence,
) -> None:
    """expected_behavior_source: AC-3 and AC-5 ("for the architecture and security roles with no
    freshness recorded, the same class as the function of the base revision"); ADR-007
    decision 4 ("For the other two roles it is optional so existing records stay valid"). Only a
    `false` value changes the class of those roles, and it gives I0."""
    for role in (None, *OTHER_ROLES):
        assert derive(agent_client="claude-code", fresh=fresh, role=role) is different_client
        assert derive(fresh=fresh, role=role) is same_client


def test_one_client_with_two_observed_different_families_is_i2() -> None:
    """expected_behavior_source: AC-3 ("One client with two observed different families is
    I2"); BC-17; ADR-007 decision 5 (a different known family)."""
    result = derive(agent_family="openai", agent_observed=True, coder_observed=True)

    assert result is Independence.I2


def test_one_client_with_the_same_observed_family_is_i1() -> None:
    """expected_behavior_source: AC-3 ("the same client with the same observed family is I1");
    ADR-007 decision 3 (equal known identities never count as a difference)."""
    result = derive(agent_observed=True, coder_observed=True)

    assert result is Independence.I1


@pytest.mark.parametrize(
    ("agent_observed", "coder_observed", "expected"),
    [
        (True, True, Independence.I2),
        (False, True, Independence.I1),
        (True, False, Independence.I1),
        (False, False, Independence.I1),
    ],
    ids=["both-observed", "agent-requested-only", "coder-requested-only", "neither-observed"],
)
def test_a_family_difference_in_one_client_needs_both_identities_observed(
    agent_observed: bool,
    coder_observed: bool,
    expected: Independence,
) -> None:
    """expected_behavior_source: AC-3 ("a requested-only model, or `identity_source` unknown, is
    an unknown identity and never shows a family difference"); ADR-007 decision 2 ("A family
    difference needs both identities observed") and decision 5 ("`known` family means an
    *observed* identity")."""
    result = derive(
        agent_family="openai",
        agent_observed=agent_observed,
        coder_observed=coder_observed,
    )

    assert result is expected


@pytest.mark.parametrize(
    ("agent_observed", "coder_observed"),
    [(True, True), (False, True), (True, False), (False, False)],
    ids=["both-observed", "agent-requested-only", "coder-requested-only", "neither-observed"],
)
def test_a_different_client_is_i2_whether_or_not_an_identity_is_observed(
    agent_observed: bool,
    coder_observed: bool,
) -> None:
    """expected_behavior_source: AC-3 ("I2 for a different client"); ADR-007 decision 5 (I2 is "a
    different client, or a different known family"; the weak case is only warned about)."""
    result = derive(
        agent_client="claude-code",
        agent_family=None,
        coder_family=None,
        agent_observed=agent_observed,
        coder_observed=coder_observed,
    )

    assert result is Independence.I2


def test_the_new_parameters_default_so_that_the_old_call_is_unchanged() -> None:
    """expected_behavior_source: the interface ("The new parameters default so that a call with
    only the five old keyword arguments gives exactly the result it gave before this phase");
    AC-5 ("a call that gives no role behaves as before"); the one existing caller is changed
    only in phase P-10."""
    parameters = inspect.signature(derive_independence).parameters
    new_names = ("agent_observed", "coder_observed", "fresh", "role")

    defaults = {name: parameters[name].default for name in new_names}

    assert defaults == {
        "agent_observed": True,
        "coder_observed": True,
        "fresh": None,
        "role": None,
    }
    assert all(parameters[name].kind is inspect.Parameter.KEYWORD_ONLY for name in new_names)


def test_the_old_call_gives_the_class_of_the_base_revision_for_every_combination() -> None:
    """expected_behavior_source: the interface (the five old keyword arguments give the result
    they gave before this phase); AC-5 ("a call that gives no role behaves as before"). The
    function of the base revision holds for this call, so it is a characterisation: it passes
    at once."""
    for approved, clients, agent_family, coder_family in OLD_ARGUMENT_GRID:
        arguments = old_arguments(approved, clients, agent_family, coder_family)

        assert derive_independence(**arguments) is derive_at_the_base_revision(**arguments)


def test_no_recorded_identifier_or_freshness_can_make_a_review_i3() -> None:
    """expected_behavior_source: AC-3 ("It yields I0, I1 or I2"); ADR-007 decision 5 ("It yields
    I0, I1 or I2") and decision 6 (I3 is not derived from a record); it extends the existing
    test of the base revision to the new arguments."""
    for approved, fresh, role, clients, agent_side, coder_side in FULL_GRID:
        result = derived(approved, fresh, role, clients, agent_side, coder_side)

        assert result in (Independence.I0, Independence.I1, Independence.I2)


# --- AC-4: the closed notes and "recording is never worse than omitting" ------------------------

IDENTITY_UNKNOWN = "identity-unknown"
SAME_MODEL = "same-model-different-client"
MODELS: tuple[str | None, ...] = (None, "m1", "m2")
SIDE_FAMILIES: tuple[str | None, ...] = (None, "f1")
OBSERVED_CHOICES: tuple[bool, ...] = (True, False)
# One side of `independence_notes`: its model, its family and whether it was observed.
NOTE_SIDES = list(itertools.product(MODELS, SIDE_FAMILIES, OBSERVED_CHOICES))
NOTE_GRID = list(
    itertools.product(
        CLIENT_PAIRS,
        NOTE_SIDES,
        NOTE_SIDES,
    )
)


def notes(**overrides: object) -> tuple[str, ...]:
    """The notes of two different clients whose identities are both observed and differ."""
    arguments: dict[str, object] = {
        "agent_client": "cursor",
        "coder_client": "codex",
        "agent_model": "example-model-a",
        "agent_family": "example-family-a",
        "agent_observed": True,
        "coder_model": "example-model-b",
        "coder_family": "example-family-b",
        "coder_observed": True,
        **overrides,
    }
    return tuple(new("independence_notes")(**arguments))


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param(
            {"agent_client": "cursor", "coder_client": "cursor"},
            (),
            id="equal-clients-need-no-note",
        ),
        pytest.param(
            {"coder_client": "cursor", "agent_observed": False, "coder_observed": False},
            (),
            id="equal-clients-with-unobserved-identities-need-no-note",
        ),
        pytest.param(
            {"coder_client": "cursor", "agent_model": "m", "coder_model": "m"},
            (),
            id="equal-clients-with-the-same-model-need-no-note",
        ),
        pytest.param(
            {},
            (),
            id="different-clients-with-different-observed-models",
        ),
        pytest.param(
            {"agent_observed": False},
            (IDENTITY_UNKNOWN,),
            id="agent-requested-only",
        ),
        pytest.param(
            {"coder_observed": False},
            (IDENTITY_UNKNOWN,),
            id="coder-requested-only",
        ),
        pytest.param(
            {"agent_observed": False, "coder_observed": False},
            (IDENTITY_UNKNOWN,),
            id="neither-observed",
        ),
        pytest.param(
            {"agent_model": None, "agent_family": None},
            (IDENTITY_UNKNOWN,),
            id="agent-observed-but-matched-nothing",
        ),
        pytest.param(
            {"coder_model": None, "coder_family": None},
            (IDENTITY_UNKNOWN,),
            id="coder-observed-but-matched-nothing",
        ),
        pytest.param(
            {"agent_model": None, "agent_family": None, "coder_model": None, "coder_family": None},
            (IDENTITY_UNKNOWN,),
            id="both-observed-but-matched-nothing",
        ),
        pytest.param(
            {"agent_model": "m", "coder_model": "m", "coder_family": "example-family-a"},
            (SAME_MODEL,),
            id="the-same-observed-model-in-two-clients",
        ),
        pytest.param(
            {"agent_model": "m", "coder_model": "m", "agent_family": None, "coder_family": None},
            (SAME_MODEL,),
            id="the-same-observed-model-without-a-family",
        ),
        pytest.param(
            {"agent_model": "m", "coder_model": "m", "agent_observed": False},
            (IDENTITY_UNKNOWN,),
            id="same-model-but-the-agent-is-not-observed",
        ),
        pytest.param(
            {"agent_model": "m", "coder_model": "m", "coder_observed": False},
            (IDENTITY_UNKNOWN,),
            id="same-model-but-the-coder-is-not-observed",
        ),
        pytest.param(
            {"agent_model": None, "coder_model": None},
            (),
            id="families-known-without-a-model-id-on-either-side",
        ),
        pytest.param(
            {"agent_model": None, "coder_model": None, "coder_family": "example-family-a"},
            (),
            id="the-same-family-known-without-a-model-id-on-either-side",
        ),
        pytest.param(
            {"agent_family": None, "coder_model": None},
            (),
            id="agent-with-a-model-only-and-coder-with-a-family-only",
        ),
    ],
)
def test_the_notes_of_each_case(overrides: dict[str, object], expected: tuple[str, ...]) -> None:
    """expected_behavior_source: AC-4 ("`identity-unknown` when a different client rests on an
    unknown identity on either side, and `same-model-different-client` when two observed
    identities are the same model on different clients"); ADR-007 decision 5 (the two closed
    warnings) and decision 3 ("a string that matches nothing is unknown"); the interface for the
    reading of "known" (observed, and a model or a family) and for the cases where a family is
    known and no model id is: there are two observed identities but no model to call equal."""
    assert notes(**overrides) == expected


def reference_notes(
    agent_client: str,
    coder_client: str,
    agent: tuple[str | None, str | None, bool],
    coder: tuple[str | None, str | None, bool],
) -> tuple[str, ...]:
    """The rules of the interface for `independence_notes`, written out once more."""
    if agent_client == coder_client:
        return ()
    agent_model, agent_family, agent_observed = agent
    coder_model, coder_family, coder_observed = coder
    agent_known = agent_observed and (agent_model is not None or agent_family is not None)
    coder_known = coder_observed and (coder_model is not None or coder_family is not None)
    found: list[str] = []
    if not (agent_known and coder_known):
        found.append(IDENTITY_UNKNOWN)
    if agent_known and coder_known and agent_model is not None and agent_model == coder_model:
        found.append(SAME_MODEL)
    return tuple(found)


def test_the_notes_are_from_the_closed_set_in_its_order_for_every_combination() -> None:
    """expected_behavior_source: AC-4 ("returns, in a fixed order and from the closed set");
    ADR-007 decision 5 (two closed warnings) and decision 2 (no recorded string is echoed); the
    interface (each name at most once, in the order of `INDEPENDENCE_NOTES`, and the two names
    exclude each other)."""
    closed = new("INDEPENDENCE_NOTES")

    for (agent_client, coder_client), agent, coder in NOTE_GRID:
        result = notes(
            agent_client=agent_client,
            coder_client=coder_client,
            agent_model=agent[0],
            agent_family=agent[1],
            agent_observed=agent[2],
            coder_model=coder[0],
            coder_family=coder[1],
            coder_observed=coder[2],
        )

        assert isinstance(result, tuple)
        assert set(result) <= set(closed)
        assert len(set(result)) == len(result)
        assert result == tuple(name for name in closed if name in result)
        assert len(result) <= 1  # the two names exclude each other
        assert result == reference_notes(agent_client, coder_client, agent, coder)


def test_recording_an_identity_is_never_worse_than_omitting_it() -> None:
    """expected_behavior_source: AC-4 ("Recording an identity is never worse than omitting it:
    for every combination, the class with an observed identity is at least the class without
    it"); ADR-007 decision 5 ("Recording the truth is therefore never worse than omitting it");
    the interface (a side is recorded with a family and observed, or omitted with no family and
    not observed). Every combination of approval, freshness, role and client, with the identity
    of the agent, the coder or both left out."""
    for approved, fresh, role, clients, agent_side, coder_side in FULL_GRID:
        recorded = derived(approved, fresh, role, clients, agent_side, coder_side)
        without_agent = derived(approved, fresh, role, clients, OMITTED_SIDE, coder_side)
        without_coder = derived(approved, fresh, role, clients, agent_side, OMITTED_SIDE)
        without_both = derived(approved, fresh, role, clients, OMITTED_SIDE, OMITTED_SIDE)

        where = (approved, fresh, role, clients, agent_side, coder_side)
        assert recorded >= without_agent, where
        assert recorded >= without_coder, where
        assert recorded >= without_both, where


# --- AC-5: the minimum by role, and the base revision as the reference --------------------------


@pytest.mark.parametrize("role", OTHER_ROLES, ids=["architecture", "security"])
def test_with_no_freshness_recorded_the_two_old_roles_get_the_class_of_the_base_revision(
    role: str,
) -> None:
    """expected_behavior_source: AC-5 ("A table-driven test over every combination of approval,
    equal or different client and unknown, equal or different family gives, for the architecture
    and security roles with no freshness recorded, the same class as the function of the base
    revision"); C-7; the interface (the observed flags are not given, so they are True)."""
    for approved, clients, agent_family, coder_family in OLD_ARGUMENT_GRID:
        arguments = old_arguments(approved, clients, agent_family, coder_family)

        result = derive_independence(role=role, **arguments)

        assert result is derive_at_the_base_revision(**arguments)


def test_with_no_role_the_minimum_is_the_one_of_the_base_revision_for_every_class() -> None:
    """expected_behavior_source: AC-5 ("a call that gives no role behaves as before"; the
    minimum is "unchanged for the other roles (I2 at D3, I1 below)"); R-10. The call of the base
    revision holds, so this passes at once."""
    for change_class in ChangeClass:
        assert minimum_independence(change_class) is minimum_at_the_base_revision(change_class)


@pytest.mark.parametrize("role", [None, *OTHER_ROLES], ids=ROLE_IDS[:3])
def test_the_minimum_of_the_two_old_roles_is_the_one_of_the_base_revision(
    role: str | None,
) -> None:
    """expected_behavior_source: AC-5 ("unchanged for the other roles (I2 at D3, I1 below)");
    ADR-006 decision 4 ("The architecture and security reviewers keep today's minimum"); R-10."""
    for change_class in ChangeClass:
        expected = minimum_at_the_base_revision(change_class)

        assert minimum_independence(change_class, role) is expected


@pytest.mark.parametrize("change_class", list(ChangeClass), ids=lambda c: c.name)
def test_the_code_reviewer_needs_i2_at_every_class(change_class: ChangeClass) -> None:
    """expected_behavior_source: AC-5 ("`minimum_independence(change_class, role)` is I2 at every
    class for `code-reviewer`"); ADR-006 decision 4 ("The code reviewer needs at least I2 at
    every class"); R-10 (D1 and D2 changes needed I1 before)."""
    assert minimum_independence(change_class, "code-reviewer") is Independence.I2
    assert minimum_independence(change_class, role="code-reviewer") is Independence.I2


@pytest.mark.parametrize(
    "role",
    ["tester", "Code-Reviewer", "code-reviewers", "coder", ""],
    ids=["tester", "capitalised", "plural", "coder", "empty"],
)
def test_every_other_role_string_keeps_the_minimum_of_the_base_revision(role: str) -> None:
    """expected_behavior_source: AC-5 ("unchanged for the other roles"); the interface ("for
    every other role string and for no role: unchanged"); ADR-006 decision 4."""
    for change_class in ChangeClass:
        expected = minimum_at_the_base_revision(change_class)

        assert minimum_independence(change_class, role) is expected


@pytest.mark.parametrize("role", ROLES, ids=ROLE_IDS)
def test_satisfies_compares_a_class_with_the_minimum_of_the_role(role: str | None) -> None:
    """expected_behavior_source: AC-5 ("`satisfies` takes the role; a call that gives no role
    behaves as before"); the interface (`independence >= minimum_independence(change_class,
    role)`). Every class of independence against every change class, with the role positional
    and, when it is not none, as a keyword."""
    for independence, change_class in itertools.product(Independence, ChangeClass):
        expected = independence >= minimum_of_the_role(change_class, role)

        assert satisfies(independence, change_class, role) is expected
        if role is not None:
            assert satisfies(independence, change_class, role=role) is expected


def test_satisfies_without_a_role_is_the_call_of_the_base_revision() -> None:
    """expected_behavior_source: AC-5 ("a call that gives no role behaves as before"). Passes at
    once: the call of the base revision holds."""
    for independence, change_class in itertools.product(Independence, ChangeClass):
        expected = independence >= minimum_at_the_base_revision(change_class)

        assert satisfies(independence, change_class) is expected


def test_i0_never_satisfies_a_gate_for_any_role() -> None:
    """expected_behavior_source: the module docstring and the existing test ("I0 never satisfies
    a review gate"), with AC-5 (`satisfies` takes the role); ADR-007 decision 4 (I0 for a missing
    freshness is never a pass)."""
    for change_class, role in itertools.product(ChangeClass, ROLES):
        assert not satisfies(Independence.I0, change_class, role)


def test_a_same_client_review_of_the_code_does_not_satisfy_the_gate_at_any_class() -> None:
    """expected_behavior_source: ADR-006 decision 5 ("A new session of the same client is I1 and
    does not satisfy the gate"); AC-3 and AC-5 together: a fresh code review in the same client
    and the same observed family is I1, and the code reviewer needs I2 at every class."""
    same_client = derive(role="code-reviewer", fresh=True)
    other_client = derive(role="code-reviewer", fresh=True, agent_client="claude-code")

    for change_class in ChangeClass:
        assert not satisfies(same_client, change_class, "code-reviewer")
        assert satisfies(other_client, change_class, "code-reviewer")


# --- the derivation reads no clock and no file ---------------------------------------------------

MODULE_NAME = "orqlet.domain.independence"
CLOCK_AND_FILE_MODULES = frozenset(
    {
        "time",
        "datetime",
        "os",
        "pathlib",
        "io",
        "sys",
        "subprocess",
        "socket",
        "shutil",
        "tempfile",
        "glob",
    }
)
OUTER_LAYERS = ("orqlet.application", "orqlet.adapters", "orqlet.interface")
DYNAMIC_CALLS = frozenset({"open", "eval", "exec", "compile", "__import__"})


def imported_names(source: str) -> list[str]:
    """Every absolute dotted name that the source imports, with a relative name resolved."""
    package = MODULE_NAME.split(".")[:-1]
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            keep = len(package) - (node.level - 1) if node.level else 0
            module = ".".join([*package[:keep], node.module or ""]).strip(".")
            found.append(module)
            found += [f"{module}.{alias.name}" for alias in node.names]
    return found


def called_names(source: str) -> list[str]:
    calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
    return [call.func.id for call in calls if isinstance(call.func, ast.Name)]


def is_impure_import(name: str) -> bool:
    if name.split(".")[0] in CLOCK_AND_FILE_MODULES:
        return True
    return any(name == layer or name.startswith(f"{layer}.") for layer in OUTER_LAYERS)


def impurities(source: str) -> list[str]:
    """What the source imports or calls that a pure function of recorded values must not."""
    found = [f"imports {name}" for name in imported_names(source) if is_impure_import(name)]
    found += [f"calls {name}" for name in called_names(source) if name in DYNAMIC_CALLS]
    return found


def is_outside_the_domain_and_the_library(name: str) -> bool:
    if name.split(".")[0] in sys.stdlib_module_names:
        return False
    return name != "orqlet.domain" and not name.startswith("orqlet.domain.")


@pytest.mark.parametrize(
    "source",
    [
        "import time",
        "import os.path",
        "from datetime import datetime",
        "from pathlib import Path",
        "import io as stream",
        "from orqlet.application.usecases import render_all",
        "from orqlet.adapters.fs import journal",
        "from orqlet import interface",
        "from ..application import ports",
        "x = open('f')",
        "eval('1')",
        "exec('x = 1')",
        "compile('1', 'f', 'eval')",
        "__import__('os')",
    ],
)
def test_the_purity_check_finds_each_import_and_call_it_looks_for(source: str) -> None:
    """expected_behavior_source: the brief of this phase's Tester (the list of modules, layers and
    calls); ORQLET-ARCH-002 (domain code is pure). The check must find what it looks for, or the
    test of the real module below proves nothing."""
    assert impurities(source)


def test_the_purity_check_accepts_what_the_module_may_import() -> None:
    """expected_behavior_source: ORQLET-ARCH-002 (the domain imports the standard library and
    `orqlet.domain` only)."""
    lines = [
        "from __future__ import annotations",
        "from collections.abc import Sequence",
        "from enum import IntEnum",
        "from orqlet.domain.change_class import ChangeClass",
        "from .change_class import ChangeClass as Alias",
    ]

    assert impurities("\n".join(lines)) == []


def test_the_independence_module_imports_only_the_standard_library_and_the_domain() -> None:
    """expected_behavior_source: the interface ("Module `orqlet.domain.independence` stays pure:
    stdlib and orqlet.domain imports only, no clock, no file, no network"); ORQLET-ARCH-002
    ("Domain code is pure: no I/O and no third-party imports"); ADR-007 decision 5 ("The
    derivation stays a pure function of recorded values")."""
    source = inspect.getsource(importlib.import_module(MODULE_NAME))

    outside = [n for n in imported_names(source) if is_outside_the_domain_and_the_library(n)]

    assert impurities(source) == []
    assert outside == []


def refuse(*_arguments: object, **_keywords: object) -> NoReturn:
    raise AssertionError("the derivation read a clock or a file")


def sample_calls() -> list[Callable[[], object]]:
    """The five functions of the phase, each on sample values that reach several branches."""
    derive_new: Any = derive_independence
    notes_of: Any = new("independence_notes")
    observed: Any = new("is_observed")
    return [
        lambda: derive_new(
            approved_binding=True,
            agent_client="cursor",
            agent_family="x",
            coder_client="codex",
            coder_family="y",
            agent_observed=True,
            coder_observed=False,
            fresh=True,
            role="code-reviewer",
        ),
        lambda: derive_new(
            approved_binding=True,
            agent_client="cursor",
            agent_family="x",
            coder_client="cursor",
            coder_family="y",
            agent_observed=True,
            coder_observed=True,
            fresh=None,
            role="architecture-reviewer",
        ),
        lambda: notes_of(
            agent_client="cursor",
            coder_client="codex",
            agent_model="m",
            agent_family="f",
            agent_observed=True,
            coder_model="m",
            coder_family="f",
            coder_observed=True,
        ),
        lambda: notes_of(
            agent_client="cursor",
            coder_client="codex",
            agent_model=None,
            agent_family=None,
            agent_observed=False,
            coder_model="m",
            coder_family=None,
            coder_observed=True,
        ),
        lambda: minimum_independence(ChangeClass.D2, "code-reviewer"),
        lambda: minimum_independence(ChangeClass.D3),
        lambda: satisfies(Independence.I1, ChangeClass.D3, "code-reviewer"),
        lambda: satisfies(Independence.I2, ChangeClass.D1),
        lambda: observed("client-reported", "m"),
        lambda: observed(None, "m"),
    ]


def test_the_five_functions_read_no_clock_and_no_file_and_give_the_same_answer_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """expected_behavior_source: P-9 objective and ADR-007 decision 5 ("The derivation stays a
    pure function of recorded values"); ORQLET-ARCH-002 (domain code is pure). Every function
    that reads a clock or a file, as the brief names them, raises while the five functions run;
    they are restored before any assertion is evaluated."""
    calls = sample_calls()  # resolved before the clock and the files are taken away
    targets: list[tuple[object, str]] = [
        (builtins, "open"),
        (io, "open"),
        (os, "stat"),
        (os, "listdir"),
        (os, "scandir"),
        (pathlib.Path, "open"),
        (pathlib.Path, "read_text"),
        (pathlib.Path, "read_bytes"),
        (pathlib.Path, "stat"),
        (time, "time"),
        (time, "time_ns"),
        (time, "monotonic"),
        (time, "perf_counter"),
    ]

    with monkeypatch.context() as patch:
        for target, name in targets:
            patch.setattr(target, name, refuse)
        first = [call() for call in calls]
        second = [call() for call in calls]
    outside = [call() for call in calls]

    assert first == second == outside
    assert len(first) == len(calls)
