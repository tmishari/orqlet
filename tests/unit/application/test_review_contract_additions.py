"""The additions to the review record and the role bindings (task dynamic-model-profiles, P-1).

Each test names in `expected_behavior_source` the criterion that it checks (AC-5 of phase P-1 in
docs/design/dynamic-model-profiles/plan.yaml) and then the sources that the criterion lists. EC-n
are the expected changes of design/manifest.yaml, BC-n the behaviour rows of design/component.md,
and ADR-007 is the decision record on independence and model identity.

These tests were written first, by the Tester of phase P-1, before the change existed. They start
from the valid record of tests/fixtures/contracts/valid/orqlet.review-result.v1.yaml, which holds
none of the new fields, and change one thing in a copy of it. The strings of `model_requested` and
`model_observed` are checked with the other constrained strings, in test_model_policy_contract.py.

The criterion leaves these open, so no test requires or refuses them:
- whether `context` needs both `fresh` and `input` once it is present;
- the value that a record without `identity_source` reports (the criterion says it means unknown);
- a null `identity_source`, `context` or `selection_source`.
"""

from __future__ import annotations

import copy
import functools
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.review_result import ReviewResult
from orqlet.application.contracts.role_bindings import RoleBindings

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "contracts" / "valid"
RECORD_FIXTURE = FIXTURES / "orqlet.review-result.v1.yaml"
BINDINGS_FIXTURE = FIXTURES / "orqlet.role-bindings.v1.yaml"
LOADER = StrictYamlLoader()

SIDES = ("agent", "coder_binding")
CLIENTS = ("claude-code", "codex", "cursor")
ROLES = ("architecture-reviewer", "security-reviewer", "code-reviewer")
IDENTITY_SOURCES = ("client-reported", "person-observed", "unknown")
SELECTION_SOURCES = (
    "task-override",
    "role-assignment",
    "profile-assignment",
    "automatic",
    "explicit-fallback",
)
NEW_FIELDS = ("identity_source", "context", "selection_source")


@functools.cache
def _parsed(path: Path) -> dict[str, Any]:
    loaded = LOADER.load(path.read_bytes(), source=path.name)
    assert isinstance(loaded, dict)
    return loaded


def record(side: str | None = None, **changes: Any) -> dict[str, Any]:
    """The valid record, with `changes` set on its `agent` or `coder_binding`, or at the top."""
    document = copy.deepcopy(_parsed(RECORD_FIXTURE))
    (document if side is None else document[side]).update(changes)
    return document


def bindings(**changes: Any) -> dict[str, Any]:
    """The valid role bindings, with `changes` set on its first binding."""
    document = copy.deepcopy(_parsed(BINDINGS_FIXTURE))
    document["bindings"][0].update(changes)
    return document


def refused_at(document: dict[str, Any], where: tuple[str, ...]) -> None:
    """The record is refused, and every error sits at `where` or below it."""
    with pytest.raises(ValidationError) as caught:
        ReviewResult.model_validate(document)

    places = {item["loc"] for item in caught.value.errors(include_input=False, include_url=False)}
    assert places
    assert all(place[: len(where)] == where for place in places), places


# --- the record that holds none of the new fields ----------------------------------------------


def test_a_record_without_any_new_field_loads_as_before() -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    All new fields are optional in the schema, so a record without them loads as before.
    """
    document = _parsed(RECORD_FIXTURE)
    assert not set(NEW_FIELDS) & (set(document["agent"]) | set(document["coder_binding"]))

    loaded = load_contract(LOADER, ReviewResult, RECORD_FIXTURE.read_bytes(), source="fixture")

    assert loaded.role == "architecture-reviewer"


def test_a_record_that_sets_every_new_field_loads_and_keeps_each_one() -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `agent` and `coder_binding` gain `identity_source`; `agent` gains `context` and
    `selection_source`; `model_requested` and `model_observed` are a `RecordedModel` or null.
    """
    agent = {
        "identity_source": "client-reported",
        "model_requested": "Example Model 1.2 [effort=high]",
        "model_observed": "example-large-1",
        "context": {"fresh": True, "input": "packet-only"},
        "selection_source": "profile-assignment",
    }
    coder = {
        "identity_source": "person-observed",
        "model_requested": "example-small",
        "model_observed": None,
    }
    document = record(role="code-reviewer")
    document["agent"].update(agent)
    document["coder_binding"].update(coder)

    dumped = ReviewResult.model_validate(document).model_dump(mode="json", by_alias=True)

    assert dumped["agent"] == document["agent"]
    assert dumped["coder_binding"] == document["coder_binding"]


def test_a_requested_only_model_loads() -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `model_requested` and `model_observed` are each a `RecordedModel` or null, so a record may
    name one and leave the other null.
    """
    document = record("agent", model_requested="example-large", model_observed=None)

    loaded = ReviewResult.model_validate(document)

    assert (loaded.agent.model_requested, loaded.agent.model_observed) == ("example-large", None)


# --- the role ----------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ROLES)
def test_a_review_role_of_the_three_loads_and_is_kept(role: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `ReviewResult.role` admits `code-reviewer` (the two roles of today stay).
    """
    loaded = ReviewResult.model_validate(record(role=role))

    assert loaded.role == role


@pytest.mark.parametrize("role", ["author", "tester", "", "Code-Reviewer", "code_reviewer"])
def test_a_role_outside_the_three_is_refused(role: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `ReviewResult.role` admits `code-reviewer` and no other role beyond the two of today.
    """
    refused_at(record(role=role), ("role",))


def test_a_code_reviewer_record_without_a_context_is_schema_valid() -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `context` is optional in the schema: a `code-reviewer` record without it loads (BC-16 gives it
    the class I0 outside the schema).
    """
    document = record(role="code-reviewer")
    assert "context" not in document["agent"]

    assert ReviewResult.model_validate(document).role == "code-reviewer"


# --- the clients -------------------------------------------------------------------------------


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize("side", SIDES)
def test_a_client_of_the_closed_set_loads_and_is_kept(side: str, client: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `agent.client` and `coder_binding.client` are exactly `claude-code`, `codex` or `cursor`.
    """
    loaded = ReviewResult.model_validate(record(side, client=client))

    assert getattr(loaded, side).client == client


@pytest.mark.parametrize(
    "client", ["vscode", "windsurf", "Codex", "claude_code", "", " cursor", "cursor\n", "claude"]
)
@pytest.mark.parametrize("side", SIDES)
def test_a_client_outside_the_closed_set_is_refused(side: str, client: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `agent.client` and `coder_binding.client` are exactly `claude-code`, `codex` or `cursor`.
    """
    refused_at(record(side, client=client), (side, "client"))


# --- identity_source ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", IDENTITY_SOURCES)
@pytest.mark.parametrize("side", SIDES)
def test_an_identity_source_of_the_three_loads_and_is_kept(side: str, source: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `agent` and `coder_binding` gain `identity_source`: `client-reported`, `person-observed` or
    `unknown`.
    """
    loaded = ReviewResult.model_validate(record(side, identity_source=source))

    assert getattr(loaded, side).identity_source == source


@pytest.mark.parametrize(
    "source", ["guessed", "Client-Reported", "client_reported", "", "observed", "person-observed "]
)
@pytest.mark.parametrize("side", SIDES)
def test_an_identity_source_outside_the_three_is_refused(side: str, source: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `identity_source` is `client-reported`, `person-observed` or `unknown`.
    """
    refused_at(record(side, identity_source=source), (side, "identity_source"))


# --- context -----------------------------------------------------------------------------------


@pytest.mark.parametrize("fresh", [True, False])
def test_a_context_loads_with_either_value_of_fresh(fresh: bool) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `agent` gains `context` (`fresh`: a boolean, `input`: `packet-only`). A `false` value is a
    valid record that ADR-007 decision 4 classes I0, so it loads.
    """
    context = {"fresh": fresh, "input": "packet-only"}

    loaded = ReviewResult.model_validate(record("agent", context=context))

    assert loaded.agent.context is not None
    assert loaded.agent.context.fresh is fresh
    assert loaded.agent.context.input == "packet-only"


@pytest.mark.parametrize("fresh", ["maybe", 2, [], {"value": True}])
def test_a_fresh_that_is_not_a_boolean_is_refused(fresh: object) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `context.fresh` is a boolean.
    """
    context = {"fresh": fresh, "input": "packet-only"}

    refused_at(record("agent", context=context), ("agent", "context", "fresh"))


@pytest.mark.parametrize("value", ["full-repository", "Packet-Only", "packet_only", "", "diff"])
def test_an_input_other_than_packet_only_is_refused(value: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `context.input` is `packet-only`.
    """
    context = {"fresh": True, "input": value}

    refused_at(record("agent", context=context), ("agent", "context", "input"))


def test_a_context_with_an_unknown_key_is_refused() -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `context` holds `fresh` and `input`. Every contract model is closed (`Contract` in
    `common.py`), so a third key is refused.
    """
    context = {"fresh": True, "input": "packet-only", "surprise": 1}

    refused_at(record("agent", context=context), ("agent", "context", "surprise"))


# --- selection_source --------------------------------------------------------------------------


@pytest.mark.parametrize("source", SELECTION_SOURCES)
def test_a_selection_source_of_the_five_loads_and_is_kept(source: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `agent` gains `selection_source`: `task-override`, `role-assignment`, `profile-assignment`,
    `automatic` or `explicit-fallback`.
    """
    loaded = ReviewResult.model_validate(record("agent", selection_source=source))

    assert loaded.agent.selection_source == source


@pytest.mark.parametrize(
    "source", ["pin", "task", "Automatic", "explicit_fallback", "", "role-assignment\n"]
)
def test_a_selection_source_outside_the_five_is_refused(source: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `selection_source` is `task-override`, `role-assignment`, `profile-assignment`, `automatic` or
    `explicit-fallback`.
    """
    refused_at(record("agent", selection_source=source), ("agent", "selection_source"))


@pytest.mark.parametrize(
    "change",
    [
        {"context": {"fresh": True, "input": "packet-only"}},
        {"selection_source": "automatic"},
    ],
    ids=["context", "selection_source"],
)
def test_the_coder_binding_does_not_gain_a_context_or_a_selection_source(
    change: dict[str, Any],
) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `agent` gains `context` and `selection_source`; `coder_binding` gains only `identity_source`.
    """
    (field,) = change

    refused_at(record("coder_binding", **change), ("coder_binding", field))


# --- the role bindings -------------------------------------------------------------------------


def test_the_role_bindings_of_the_fixture_still_load() -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `Binding.role` of `RoleBindings` admits `code-reviewer`, and a file without one still loads.
    """
    loaded = load_contract(LOADER, RoleBindings, BINDINGS_FIXTURE.read_bytes(), source="fixture")

    assert [binding.role for binding in loaded.bindings] == ["architecture-reviewer"]


@pytest.mark.parametrize("role", ROLES)
def test_a_binding_role_of_the_three_loads_and_is_kept(role: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `Binding.role` of `RoleBindings` admits `code-reviewer` (the two roles of today stay).
    """
    loaded = RoleBindings.model_validate(bindings(role=role))

    assert loaded.bindings[0].role == role


@pytest.mark.parametrize("role", ["author", "tester", "", "Code-Reviewer", "code_reviewer"])
def test_a_binding_role_outside_the_three_is_refused(role: str) -> None:
    """expected_behavior_source: AC-5; EC-3; EC-5; BC-16; BC-42; ADR-007 decisions 2 and 4.

    `Binding.role` admits `code-reviewer` and no other role beyond the two of today.
    """
    with pytest.raises(ValidationError) as caught:
        RoleBindings.model_validate(bindings(role=role))

    places = {item["loc"] for item in caught.value.errors(include_input=False, include_url=False)}
    assert places == {("bindings", 0, "role")}
