"""The model policy contract v2 and its constrained strings (task dynamic-model-profiles, P-1).

Each test names in `expected_behavior_source` the criterion of phase P-1 that it checks (AC-1 to
AC-4 of docs/design/dynamic-model-profiles/plan.yaml) and then the sources that the criterion
lists. EC-n are the expected changes of design/manifest.yaml, BC-n and C-n the behaviour and
constraint rows of design/component.md, and ADR-n the decision records of design/.

These tests were written first, by the Tester of phase P-1, before the v2 contract existed. The
valid fixture sets every field (tests/fixtures/contracts/valid/orqlet.model-policy.v2.yaml). A
test changes one thing in a copy of it and checks that this change is refused, or loads. The round
trip of the fixture, the unknown top-level key and the committed schema are also checked for every
contract by tests/contract/test_contracts.py.

The three string types are checked twice: on their own (a pydantic `TypeAdapter` over the type
that the criteria name) and in the fields that carry them, so a type that no field uses fails too.
`RecordedModel` lives in a review record, so its field tests load `ReviewResult`.

The criteria leave these open, so no test requires or refuses them:
- the type of an exclusion `id`, and the text type of `approved_by` and `approval_ref`;
- whether `approved` needs an approver (BC-13 puts that check in the validator, not the contract)
  and whether `evaluated.evidence` may be set while the state is `none`;
- whether a policy must hold every profile, every client, or a non-empty list;
- an integer or a negative number as a list price, and the calendar rules of a date;
- the wording and the location of a message, except where a test below says so.
"""

from __future__ import annotations

import copy
import functools
import json
import string
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts import CONTRACTS
from orqlet.application.contracts.common import (
    ClientId,
    Contract,
    ModelRef,
    PolicyText,
    RecordedModel,
)
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.contracts.review_result import ReviewResult
from orqlet.application.ports.documents import DocumentError

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "contracts" / "valid"
POLICY_FIXTURE = FIXTURES / "orqlet.model-policy.v2.yaml"
RECORD_FIXTURE = FIXTURES / "orqlet.review-result.v1.yaml"
LOADER = StrictYamlLoader()

SCHEMA_ID = "orqlet.model-policy/v2"
CLIENTS = ("claude-code", "codex", "cursor")
MODES = ("automatic", "manual", "automatic-with-fallbacks")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
PROFILE_IDS = ("quality", "engineering", "economy")
# What a constrained string (a pattern and a length) reports; a custom validator reports another.
STRING_ERRORS = ("string_pattern_mismatch", "string_too_long", "string_too_short")

Where = tuple[str | int, ...]
Level = tuple[Where, str]  # where an object sits in the fixture, and its keys in the criterion
Enumeration = tuple[Where, tuple[object, ...], tuple[object, ...]]
StringType = tuple[object, frozenset[str], int]

ID_ROUTE: Where = ("models", 0, "routes", 0)
ALIAS_ROUTE: Where = ("models", 0, "routes", 1)
LIST_PRICE: Where = ("models", 0, "list_price")
EXCLUSION: Where = ("excluded", 0)
ID_PATTERN: Where = ("excluded", 0, "id_patterns", 0)
ASSIGNMENT: Where = ("assignments", 0)


# --- helpers ---------------------------------------------------------------------------------


def parametrized(name: str, cases: Mapping[str, object]) -> pytest.MarkDecorator:
    """`pytest.mark.parametrize` over the values of a mapping, with its keys as test ids."""
    return pytest.mark.parametrize(name, list(cases.values()), ids=list(cases))


@functools.cache
def _parsed(path: Path) -> dict[str, Any]:
    loaded = LOADER.load(path.read_bytes(), source=path.name)
    assert isinstance(loaded, dict)
    return loaded


def policy() -> dict[str, Any]:
    """The valid fixture as plain data: a new copy on every call, which a test may change."""
    return copy.deepcopy(_parsed(POLICY_FIXTURE))


def record() -> dict[str, Any]:
    """The valid review record of tests/fixtures as plain data, a new copy on every call."""
    return copy.deepcopy(_parsed(RECORD_FIXTURE))


def document_for(model: type[Contract]) -> dict[str, Any]:
    return policy() if model is ModelPolicy else record()


def reach(document: Any, where: Where) -> Any:
    node = document
    for step in where:
        node = node[step]
    return node


def changed(document: dict[str, Any], where: Where, value: object) -> dict[str, Any]:
    """A copy of `document` with `value` at `where`; the last step names the key or the index."""
    result = copy.deepcopy(document)
    reach(result, where[:-1])[where[-1]] = value
    return result


def dump(model: Contract) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)


def refused(document: dict[str, Any], model: type[Contract] = ModelPolicy) -> ValidationError:
    with pytest.raises(ValidationError) as caught:
        model.model_validate(document)
    return caught.value


def error_types(error: ValidationError) -> set[str]:
    return {str(item["type"]) for item in error.errors(include_input=False, include_url=False)}


def error_places(error: ValidationError) -> set[Where]:
    return {item["loc"] for item in error.errors(include_input=False, include_url=False)}


def assert_refused_at(
    document: dict[str, Any], where: Where, model: type[Contract] = ModelPolicy
) -> ValidationError:
    """The document is refused, and every error sits at `where` or below it."""
    error = refused(document, model)
    places = error_places(error)
    assert places
    assert all(place[: len(where)] == where for place in places), places
    return error


def accepts_at(where: Where, value: object, model: type[Contract] = ModelPolicy) -> bool:
    try:
        model.model_validate(changed(document_for(model), where, value))
    except ValidationError:
        return False
    return True


def raised_text(model: type[Contract], document: dict[str, Any]) -> str:
    """The text that `load_contract` raises for a document that the contract refuses."""
    data = json.dumps(document).encode()  # JSON is YAML, and escapes what must not break a line
    with pytest.raises(DocumentError) as caught:
        load_contract(LOADER, model, data, source="document")
    return str(caught.value)


def schema_nodes(node: object) -> Iterator[dict[str, Any]]:
    """Every object of a JSON Schema document, however deep."""
    if isinstance(node, dict):
        yield node
        for child in node.values():
            yield from schema_nodes(child)
    elif isinstance(node, list):
        for child in node:
            yield from schema_nodes(child)


def is_keyed_by_text(node: dict[str, Any]) -> bool:
    """A `dict[str, X]` field shows in a JSON Schema as a value schema for any key."""
    return bool(node.get("additionalProperties")) or "patternProperties" in node


def adapter(spec: Any) -> TypeAdapter[Any]:
    """A validator for a type; `Any` because mypy takes `TypeAdapter`'s argument as a TypeForm."""
    return TypeAdapter(spec)


def assert_exact_fields(level: Level) -> None:
    """The object of the fixture at `where` holds the keys of `names`, and no others."""
    where, names = level
    dumped = dump(ModelPolicy.model_validate(policy()))

    assert set(reach(dumped, where)) == set(names.split())


def assert_exact_values(case: Enumeration) -> None:
    """A field takes each value that it should and refuses each value that it should not."""
    where, accepted, not_accepted = case

    wrongly_refused = [value for value in accepted if not accepts_at(where, value)]
    wrongly_accepted = [value for value in not_accepted if accepts_at(where, value)]

    assert not wrongly_refused, f"refused at {where}: {wrongly_refused}"
    assert not wrongly_accepted, f"accepted at {where}: {wrongly_accepted}"
    for value in not_accepted:
        assert_refused_at(changed(policy(), where, value), where)


# --- AC-1: the fixture, the schema id, the top level and the closed models ----------------------

TOP_LEVEL: Level = (
    (),
    "schema policy_version reviewed_for_release models excluded profiles assignments",
)
# Where each object of the contract sits in the fixture, and the keys the criterion gives it.
AC1_LEVELS: dict[str, Level] = {
    "model": (
        ("models", 0),
        "id family approval documented callable evaluated list_price routes",
    ),
    "approval": (
        ("models", 0, "approval"),
        "state approved_by approval_ref",
    ),
    "documented": (
        ("models", 0, "documented"),
        "evidence date",
    ),
    "evaluated": (
        ("models", 0, "evaluated"),
        "state evidence",
    ),
    "list-price": (
        LIST_PRICE,
        "input_per_million_usd output_per_million_usd source",
    ),
}
AC2_LEVELS: dict[str, Level] = {
    "route": (
        ID_ROUTE,
        "client kind name resolves_to also_known_as access retires_on",
    ),
    "exclusion": (
        EXCLUSION,
        "id reason source aliases id_patterns family_tags",
    ),
}
AC3_LEVELS: dict[str, Level] = {
    "profile": (
        ("profiles", 0),
        "id capability mode candidates fallbacks escalation",
    ),
    "candidates-entry": (
        ("profiles", 0, "candidates", 0),
        "client models",
    ),
    "fallbacks-entry": (
        ("profiles", 0, "fallbacks", 0),
        "client models",
    ),
    "assignment": (
        ASSIGNMENT,
        "target task client profile model mode effort",
    ),
    "target": (
        ("assignments", 0, "target"),
        "kind name",
    ),
}
ALL_LEVELS: dict[str, Level] = {"policy": TOP_LEVEL, **AC1_LEVELS, **AC2_LEVELS, **AC3_LEVELS}


def test_the_fixture_with_every_field_set_loads_and_round_trips() -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    A fixture that sets every field loads and round-trips.
    """
    loaded = load_contract(LOADER, ModelPolicy, POLICY_FIXTURE.read_bytes(), source="fixture")
    dumped = dump(loaded)

    assert dumped == policy()  # the fixture leaves no field out and the model adds none
    assert ModelPolicy.model_validate(dumped) == loaded


def test_the_registry_holds_the_contract_under_its_v2_id() -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `ModelPolicy` has the schema id `orqlet.model-policy/v2`, and the registry that
    tests/contract/test_contracts.py walks to find a fixture holds it under that id.
    """
    assert CONTRACTS[SCHEMA_ID] is ModelPolicy
    assert dump(ModelPolicy.model_validate(policy()))["schema"] == SCHEMA_ID


def test_the_v1_schema_id_is_refused() -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    The schema id is `orqlet.model-policy/v2`, so a document that says v1 is refused.
    """
    document = changed(policy(), ("schema",), "orqlet.model-policy/v1")

    assert_refused_at(document, ("schema",))


def test_the_top_level_keys_are_exactly_the_seven_of_the_criterion() -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    The top-level keys are exactly `schema`, `policy_version`, `reviewed_for_release`, `models`,
    `excluded`, `profiles` and `assignments`.
    """
    properties = ModelPolicy.model_json_schema(by_alias=True)["properties"]

    assert set(properties) == set(TOP_LEVEL[1].split())


@parametrized("level", AC1_LEVELS)
def test_a_model_holds_exactly_the_fields_the_criterion_names(level: Level) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    A model has `id`, `family`, `approval`, `documented`, `callable`, `evaluated`, `list_price` and
    `routes`; each of the first four objects, and `list_price`, has the keys that the criterion
    lists.
    """
    assert_exact_fields(level)


@parametrized("level", ALL_LEVELS)
def test_an_unknown_key_is_refused_at_every_level(level: Level) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    An unknown key at any level is refused.
    """
    where, _ = level
    document = policy()
    reach(document, where)["surprise"] = 1

    error = refused(document)

    assert error_types(error) == {"extra_forbidden"}
    assert error_places(error) == {(*where, "surprise")}


@pytest.mark.parametrize("version", [1, 2, 2026])
def test_a_policy_version_from_1_loads(version: int) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `policy_version` is an integer from 1.
    """
    document = ModelPolicy.model_validate(changed(policy(), ("policy_version",), version))

    assert dump(document)["policy_version"] == version


@parametrized(
    "version",
    {
        "zero": 0,
        "negative": -1,
        "a-fraction": 1.5,
        "the-text-of-the-v1-contract": "2026.10.1",
        "a-word": "one",
    },
)
def test_a_policy_version_that_is_not_an_integer_from_1_is_refused(version: object) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `policy_version` is an integer from 1 (v1 held a text such as `2026.10.1`).
    """
    assert_refused_at(changed(policy(), ("policy_version",), version), ("policy_version",))


@pytest.mark.parametrize("release", ["0.4.0", "0.10.2", "10.0.0"])
def test_a_reviewed_for_release_of_three_numbers_loads(release: str) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `reviewed_for_release` is a `major.minor.patch` string.
    """
    document = ModelPolicy.model_validate(changed(policy(), ("reviewed_for_release",), release))

    assert dump(document)["reviewed_for_release"] == release


@pytest.mark.parametrize(
    "release",
    ["0.4", "0.4.0.1", "v0.4.0", "0.4.x", "", "latest", "0.4.0\n", "0.4.0-rc.1", " 0.4.0"],
)
def test_a_reviewed_for_release_that_is_not_three_numbers_is_refused(release: str) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `reviewed_for_release` is a `major.minor.patch` string.
    """
    document = changed(policy(), ("reviewed_for_release",), release)

    assert_refused_at(document, ("reviewed_for_release",))


# --- AC-1: the enumerations of a model ----------------------------------------------------------

# name -> (where, the values that load, the values that are refused). A field whose accepted
# values depend on another field is checked by the tests of that rule instead.
AC1_ENUMERATIONS: dict[str, Enumeration] = {
    "approval-state": (
        ("models", 0, "approval", "state"),
        ("proposed", "approved", "disabled", "retired"),
        ("draft", "Approved", "pending", ""),
    ),
    "callable": (
        ("models", 0, "callable"),
        ("not-run", "verified"),
        ("not_run", "unverified", "yes", ""),
    ),
    "evaluated-state": (
        ("models", 1, "evaluated", "state"),
        (),
        ("pending", "verified", ""),
    ),
}


@parametrized("case", AC1_ENUMERATIONS)
def test_a_model_enumeration_takes_exactly_its_values(case: Enumeration) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `approval.state` is `proposed`, `approved`, `disabled` or `retired`; `callable` is `not-run` or
    `verified`; `evaluated.state` is `none` or `evidenced` (its two values are loaded by the
    fixture and by the evidence tests below).
    """
    assert_exact_values(case)


# --- AC-1: the model entry ----------------------------------------------------------------------


def test_evidence_is_required_when_the_evaluation_is_evidenced() -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `evaluated.evidence` is a repository path, required when the state is `evidenced`.
    """
    where = ("models", 0, "evaluated", "evidence")
    omitted = policy()
    del omitted["models"][0]["evaluated"]["evidence"]

    refused(changed(policy(), where, None))
    refused(omitted)


def test_an_evaluation_that_is_none_needs_no_evidence() -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `evaluated.evidence` is required only when evidenced: the second model of the fixture is
    `none` with a null evidence.
    """
    second = dump(ModelPolicy.model_validate(policy()))["models"][1]["evaluated"]

    assert second == {"state": "none", "evidence": None}


REPOSITORY_PATHS: dict[str, Where] = {
    "documented-evidence": ("models", 0, "documented", "evidence"),
    "evaluated-evidence": ("models", 0, "evaluated", "evidence"),
    "list-price-source": (*LIST_PRICE, "source"),
}


@pytest.mark.parametrize("value", ["../outside.md", "/etc/passwd", "a\\b.md", ".git/config"])
@parametrized("where", REPOSITORY_PATHS)
def test_an_evidence_or_source_path_must_stay_inside_the_repository(
    where: Where, value: str
) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `documented.evidence`, `evaluated.evidence` and `list_price.source` are each a repository
    path.
    """
    assert_refused_at(changed(policy(), where, value), where)


@pytest.mark.parametrize("value", ["yesterday", "30/10/2026", ""])
def test_a_documented_date_that_is_not_a_date_is_refused(value: str) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `documented` holds `evidence`, a repository path, and `date`.
    """
    where = ("models", 0, "documented", "date")

    assert_refused_at(changed(policy(), where, value), where)


@pytest.mark.parametrize("field", ["input_per_million_usd", "output_per_million_usd"])
@pytest.mark.parametrize("price", ["3", "0.25", "15", "1.75", "100"])
def test_a_list_price_is_a_decimal_string(field: str, price: str) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `input_per_million_usd` and `output_per_million_usd` are decimal strings such as `3` or
    `0.25`.
    """
    where = (*LIST_PRICE, field)

    loaded = dump(ModelPolicy.model_validate(changed(policy(), where, price)))

    assert reach(loaded, where) == price


@pytest.mark.parametrize("field", ["input_per_million_usd", "output_per_million_usd"])
@parametrized(
    "price",
    {
        "a-float": 3.5,
        "a-float-that-reads-like-a-whole-number": 3.0,
        "a-word": "three",
        "empty": "",
        "with-a-unit": "0.25 USD",
        "a-comma": "1,5",
        "a-fraction": "1/2",
        "with-a-currency-sign": "$3",
    },
)
def test_a_list_price_that_is_not_a_decimal_string_is_refused(field: str, price: object) -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    A price is a decimal string such as `3` or `0.25`, so a float or a text that is not a decimal
    is refused.
    """
    where = (*LIST_PRICE, field)

    assert_refused_at(changed(policy(), where, price), where)


def test_a_model_without_a_list_price_loads() -> None:
    """expected_behavior_source: AC-1; EC-1; ADR-002 decision 3; BC-11.

    `list_price` is null, or the three fields.
    """
    document = changed(policy(), LIST_PRICE, None)

    assert dump(ModelPolicy.model_validate(document))["models"][0]["list_price"] is None


# --- AC-2: routes and exclusions ----------------------------------------------------------------

AC2_ENUMERATIONS: dict[str, Enumeration] = {
    "route-client": (
        (*ID_ROUTE, "client"),
        CLIENTS,
        ("vscode", "Codex", "claude_code", ""),
    ),
    "route-kind": (
        (*ID_ROUTE, "kind"),
        (),
        ("pattern", "Alias", ""),
    ),
    "route-access": (
        (*ID_ROUTE, "access"),
        ("unknown", "confirmed", "blocked"),
        ("allowed", "granted", ""),
    ),
}


@parametrized("level", AC2_LEVELS)
def test_a_route_and_an_exclusion_hold_exactly_the_fields_the_criterion_names(
    level: Level,
) -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    A route has `client`, `kind`, `name`, `resolves_to`, `also_known_as`, `access` and
    `retires_on`; an exclusion has `id`, `reason`, `source`, `aliases`, `id_patterns` and
    `family_tags`.
    """
    assert_exact_fields(level)


@parametrized("case", AC2_ENUMERATIONS)
def test_a_route_enumeration_takes_exactly_its_values(case: Enumeration) -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `client` is `claude-code`, `codex` or `cursor`; `access` is `unknown`, `confirmed` or
    `blocked`; `kind` is `id` or `alias` (each is loaded by the fixture and by the tests below).
    """
    assert_exact_values(case)


def test_the_client_set_is_closed_to_the_three_clients() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    The type of a client is `claude-code`, `codex` or `cursor`, and no other text.
    """
    checker = adapter(ClientId)

    assert [checker.validate_python(client) for client in CLIENTS] == list(CLIENTS)
    for value in ("vscode", "Codex", "claude_code", "", " codex", "codex\n", "windsurf"):
        assert not accepts(checker, value), value


def test_an_alias_route_without_resolves_to_is_refused() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    A route of kind `alias` must carry `resolves_to`.
    """
    refused(changed(policy(), (*ALIAS_ROUTE, "resolves_to"), None))


def test_an_id_route_that_carries_resolves_to_is_refused() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    A route of kind `id` must not carry `resolves_to`.
    """
    refused(changed(policy(), (*ID_ROUTE, "resolves_to"), "example-large-1"))


def test_changing_the_kind_of_a_route_without_its_resolves_to_is_refused() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    An `alias` carries `resolves_to` and an `id` does not, so each route fails when only its
    `kind` is flipped.
    """
    refused(changed(policy(), (*ID_ROUTE, "kind"), "alias"))
    refused(changed(policy(), (*ALIAS_ROUTE, "kind"), "id"))


def test_an_alias_route_that_names_what_it_resolves_to_loads_and_is_kept() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    A route of kind `alias` carries `resolves_to`.
    """
    route = dump(ModelPolicy.model_validate(policy()))["models"][0]["routes"][1]

    assert (route["kind"], route["resolves_to"]) == ("alias", "example-large-1")


@pytest.mark.parametrize("count", [0, 1, 8])
def test_a_route_lists_at_most_eight_other_spellings(count: int) -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `also_known_as` holds at most 8 `ModelRef`.
    """
    where = (*ID_ROUTE, "also_known_as")
    names = [f"example-name-{number}" for number in range(count)]

    loaded = dump(ModelPolicy.model_validate(changed(policy(), where, names)))

    assert reach(loaded, where) == names


@pytest.mark.parametrize("count", [9, 20])
def test_a_route_with_more_than_eight_other_spellings_is_refused(count: int) -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `also_known_as` holds at most 8 `ModelRef`.
    """
    where = (*ID_ROUTE, "also_known_as")
    names = [f"example-name-{number}" for number in range(count)]

    assert_refused_at(changed(policy(), where, names), where)


@pytest.mark.parametrize("value", ["soon", "30/10/2026", ""])
def test_a_retirement_that_is_not_a_date_is_refused(value: str) -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `retires_on` is a date or null.
    """
    where = (*ID_ROUTE, "retires_on")

    assert_refused_at(changed(policy(), where, value), where)


def test_a_route_may_have_no_retirement_date() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `retires_on` is a date or null.
    """
    where = (*ID_ROUTE, "retires_on")

    loaded = dump(ModelPolicy.model_validate(changed(policy(), where, None)))

    assert reach(loaded, where) is None


def exclusion_with(**lists: list[str]) -> dict[str, Any]:
    """The fixture with the three lists of its exclusion emptied, then these set."""
    document = policy()
    document["excluded"][0].update({"aliases": [], "id_patterns": [], "family_tags": []})
    document["excluded"][0].update(lists)
    return document


def test_an_exclusion_with_nothing_to_match_is_refused() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    An exclusion has the lists `aliases`, `id_patterns` and `family_tags`, at least one of them
    not empty.
    """
    refused(exclusion_with())


@parametrized(
    "lists",
    {
        "aliases": {"aliases": ["blocked-alias"]},
        "id-patterns": {"id_patterns": ["blocked-model-*"]},
        "family-tags": {"family_tags": ["blocked-family"]},
    },
)
def test_an_exclusion_with_one_non_empty_list_loads(lists: dict[str, list[str]]) -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    At least one of the three lists is not empty, so one is enough.
    """
    loaded = dump(ModelPolicy.model_validate(exclusion_with(**lists)))

    assert loaded["excluded"][0]["aliases"] == lists.get("aliases", [])
    assert loaded["excluded"][0]["id_patterns"] == lists.get("id_patterns", [])
    assert loaded["excluded"][0]["family_tags"] == lists.get("family_tags", [])


ID_PATTERN_CHARACTERS = frozenset(string.ascii_letters + string.digits + "._:/@+*?-")


def test_an_id_pattern_takes_exactly_its_alphabet() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `id_patterns` are patterns of 1 to 128 characters from `A-Za-z0-9._:/@+*?-`.
    """
    accepted = {char for char in map(chr, range(0x80)) if accepts_at(ID_PATTERN, f"a{char}b")}

    assert not accepted ^ ID_PATTERN_CHARACTERS, sorted(accepted ^ ID_PATTERN_CHARACTERS)
    assert not accepts_at(ID_PATTERN, "a\u00e9b")


def test_an_id_pattern_is_one_to_128_characters_long() -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `id_patterns` are patterns of 1 to 128 characters (and, by AC-4, are never truncated).
    """
    for value in ("a", "*", "?", "a" * 128):
        kept = dump(ModelPolicy.model_validate(changed(policy(), ID_PATTERN, value)))

        assert reach(kept, ID_PATTERN) == value
    assert_refused_at(changed(policy(), ID_PATTERN, ""), ID_PATTERN)
    assert_refused_at(changed(policy(), ID_PATTERN, "a" * 129), ID_PATTERN)


@pytest.mark.parametrize(
    "pattern",
    ["^model-.*$", "model-(a|b)", "model[0-9]", "model\\d+", "model{2}", "a|b", "model\\.x"],
)
def test_an_id_pattern_that_is_a_regular_expression_is_refused(pattern: str) -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `id_patterns` are fnmatch-style patterns, never regular expressions. Each value holds a
    character outside the alphabet (an anchor, a group, a class, a brace, a bar or a backslash).
    """
    assert_refused_at(changed(policy(), ID_PATTERN, pattern), ID_PATTERN)


@pytest.mark.parametrize("field", ["aliases", "family_tags"])
def test_an_exclusion_alias_and_family_tag_are_model_refs(field: str) -> None:
    """expected_behavior_source: AC-2; BC-28; BC-9; ADR-005 decision 1.

    `aliases` and `family_tags` are lists of `ModelRef`.
    """
    where = (*EXCLUSION, field, 0)

    assert_refused_at(changed(policy(), where, "not a model ref"), where)


# --- AC-3: profiles, candidates and assignments -------------------------------------------------

AC3_ENUMERATIONS: dict[str, Enumeration] = {
    "profile-id": (
        ("profiles", 0, "id"),
        (),
        ("premium", "Quality", ""),
    ),
    "profile-mode": (
        ("profiles", 0, "mode"),
        MODES,
        ("auto", "Manual", "fallbacks", ""),
    ),
    "profile-escalation": (
        ("profiles", 2, "escalation"),
        ("quality", "engineering", None),
        ("premium", ""),
    ),
    "candidates-client": (
        ("profiles", 0, "candidates", 0, "client"),
        (),
        ("vscode", ""),
    ),
    "fallbacks-client": (
        ("profiles", 0, "fallbacks", 0, "client"),
        (),
        ("vscode", ""),
    ),
    "target-kind": (
        (*ASSIGNMENT, "target", "kind"),
        ("role", "skill"),
        ("agent", "Role", ""),
    ),
    "assignment-client": (
        (*ASSIGNMENT, "client"),
        (*CLIENTS, None),
        ("vscode", ""),
    ),
    "assignment-profile": (
        (*ASSIGNMENT, "profile"),
        PROFILE_IDS,
        ("premium", ""),
    ),
    "assignment-mode": (
        (*ASSIGNMENT, "mode"),
        MODES,
        ("auto", ""),
    ),
    "assignment-effort": (
        (*ASSIGNMENT, "effort"),
        (*EFFORTS, None),
        ("none", "minimal", "ultra", "XHIGH", ""),
    ),
}


@parametrized("level", AC3_LEVELS)
def test_a_profile_and_an_assignment_hold_exactly_the_fields_the_criterion_names(
    level: Level,
) -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    A profile has `id`, `capability`, `mode`, `candidates`, `fallbacks` and `escalation`; each
    entry of `candidates` and `fallbacks` is `{client, models}`; an assignment has `target`,
    `task`, `client`, `profile`, `model`, `mode` and `effort`; a `target` is `{kind, name}`.
    """
    assert_exact_fields(level)


@parametrized("case", AC3_ENUMERATIONS)
def test_a_profile_or_assignment_enumeration_takes_exactly_its_values(case: Enumeration) -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    A profile `id` is `quality`, `engineering` or `economy` (refusal only: the fixture holds each
    once); `mode` and an assignment's `mode` are `automatic`, `manual` or
    `automatic-with-fallbacks`; `escalation` is a profile id or null; `target.kind` is `role` or
    `skill`; `client` is a client id or null; `effort` is `low`, `medium`, `high`, `xhigh`, `max`
    or null.
    """
    assert_exact_values(case)


@parametrized(
    "change",
    {
        "engineering-as-quality": (1, "quality"),
        "economy-as-quality": (2, "quality"),
        "economy-as-engineering": (2, "engineering"),
    },
)
def test_a_profile_id_used_twice_is_refused(change: tuple[int, str]) -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    A profile `id` is `quality`, `engineering` or `economy`, each at most once.
    """
    index, profile_id = change

    refused(changed(policy(), ("profiles", index, "id"), profile_id))


def test_the_three_profiles_of_the_fixture_each_load_once() -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    `quality`, `engineering` and `economy` each load, once.
    """
    loaded = dump(ModelPolicy.model_validate(policy()))

    assert [profile["id"] for profile in loaded["profiles"]] == list(PROFILE_IDS)


@pytest.mark.parametrize("field", ["candidates", "fallbacks"])
def test_a_client_has_one_entry_in_candidates_and_in_fallbacks(field: str) -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    `candidates` and `fallbacks` are each a list of `{client, models}` objects, one per client.
    """
    document = policy()
    entries = document["profiles"][0][field]
    entries.append(copy.deepcopy(entries[0]))

    refused(document)


def test_the_models_of_a_candidates_entry_keep_their_order() -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    `models` is an ordered list of catalog ids.
    """
    where = ("profiles", 0, "candidates", 1, "models")
    ordered = ["example-small", "example-large"]

    loaded = dump(ModelPolicy.model_validate(changed(policy(), where, ordered)))

    assert reach(loaded, where) == ordered


def test_an_assignment_with_both_a_profile_and_a_model_is_refused() -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    An assignment has exactly one of `profile` (a profile id) and `model` (a catalog id).
    """
    refused(changed(policy(), (*ASSIGNMENT, "model"), "example-large"))


def test_an_assignment_with_neither_a_profile_nor_a_model_is_refused() -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    An assignment has exactly one of `profile` and `model`.
    """
    refused(changed(policy(), (*ASSIGNMENT, "profile"), None))


def test_an_assignment_names_a_profile_or_a_model_and_the_other_stays_null() -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    An assignment has exactly one of `profile` and `model`.
    """
    first, second = dump(ModelPolicy.model_validate(policy()))["assignments"]

    assert (first["profile"], first["model"]) == ("quality", None)
    assert (second["profile"], second["model"]) == (None, "example-large")


SLUGS: dict[str, Where] = {
    "task": ("assignments", 1, "task"),
    "target-name": ("assignments", 1, "target", "name"),
}


@pytest.mark.parametrize("value", ["x", "a1-b2", "orqlet-code-reviewer", "a" * 64])
@parametrized("where", SLUGS)
def test_a_task_and_a_target_name_take_a_slug(where: Where, value: str) -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    A `target` is `{kind, name: a slug}` and `task` is a slug or null.
    """
    loaded = dump(ModelPolicy.model_validate(changed(policy(), where, value)))

    assert reach(loaded, where) == value


@pytest.mark.parametrize(
    "value",
    ["Upper", "has space", "under_score", "", "a" * 65, "-leading", "trailing-", "double--hyphen"],
)
@parametrized("where", SLUGS)
def test_a_task_and_a_target_name_that_are_not_a_slug_are_refused(where: Where, value: str) -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    The `name` of a `target` and a `task` are a slug.
    """
    assert_refused_at(changed(policy(), where, value), where)


def test_a_task_may_be_null() -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    `task` is a slug or null.
    """
    document = changed(policy(), ("assignments", 1, "task"), None)

    assert dump(ModelPolicy.model_validate(document))["assignments"][1]["task"] is None


def test_no_map_of_the_contract_is_keyed_by_free_text() -> None:
    """expected_behavior_source: AC-3; ADR-002 decision 3; ADR-001 decision 3; C-1.

    No map of the contract is keyed by free text. A `dict[str, X]` field shows in the JSON Schema
    as `additionalProperties` that is not false, or as pattern properties.
    """
    schema = ModelPolicy.model_json_schema(by_alias=True)

    keyed = [sorted(node) for node in schema_nodes(schema) if is_keyed_by_text(node)]

    assert not keyed


# --- AC-4: the three constrained strings, on their own -----------------------------------------

LETTERS_AND_DIGITS = string.ascii_letters + string.digits
# type, the ASCII characters it accepts, its longest length
STRING_TYPES: dict[str, StringType] = {
    "model-ref": (
        ModelRef,
        frozenset(LETTERS_AND_DIGITS + "._:/@+-"),
        128,
    ),
    "recorded-model": (
        RecordedModel,
        frozenset(LETTERS_AND_DIGITS + " ._:/@+-[]=,"),
        128,
    ),
    "policy-text": (
        PolicyText,
        frozenset(map(chr, range(0x20, 0x7F))),
        400,
    ),
}
# Characters that a pattern written with `\w`, `\d` or a case-insensitive flag would let through.
NON_ASCII = {
    "latin-letter": "\u00e9",
    "sharp-s": "\u00df",
    "dotless-i": "\u0131",
    "kelvin-sign": "\u212a",
    "fullwidth-letter": "\uff21",
    "arabic-indic-digit": "\u0663",
    "no-break-space": "\u00a0",
    "line-separator": "\u2028",
}


def accepts(checker: TypeAdapter[Any], value: str) -> bool:
    try:
        checker.validate_python(value)
    except ValidationError:
        return False
    return True


@parametrized("kind", STRING_TYPES)
def test_a_string_type_accepts_exactly_its_ascii_alphabet(kind: StringType) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    `ModelRef` is a string over `A-Za-z0-9._:/@+-`; `RecordedModel` is one over letters, digits,
    the space and `. _ : / @ + - [ ] = ,`; `PolicyText` is printable ASCII.
    """
    spec, alphabet, _ = kind
    checker = adapter(spec)

    accepted = {char for char in map(chr, range(0x80)) if accepts(checker, f"a{char}b")}

    assert not accepted ^ alphabet, f"decided wrongly: {sorted(accepted ^ alphabet)!r}"


@parametrized("kind", STRING_TYPES)
def test_a_string_type_refuses_every_non_ascii_character(kind: StringType) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    A non-ASCII letter is a breaking string. A pattern written with `\\w`, `\\d` or a flag
    that ignores case lets some of them through, so several kinds are tried.
    """
    checker = adapter(kind[0])

    wrongly_accepted = [name for name, char in NON_ASCII.items() if accepts(checker, f"a{char}b")]

    assert not wrongly_accepted


@parametrized("kind", STRING_TYPES)
def test_a_string_type_keeps_one_character_up_to_its_limit_whole_and_refuses_the_rest(
    kind: StringType,
) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    A string is 1 to 128 characters (1 to 400 for `PolicyText`), refused when it breaks its
    length and never truncated.
    """
    spec, _, limit = kind
    checker = adapter(spec)

    assert checker.validate_python("a") == "a"
    assert checker.validate_python("a" * limit) == "a" * limit
    assert not accepts(checker, "")
    assert not accepts(checker, "a" * (limit + 1))


@parametrized("kind", STRING_TYPES)
def test_a_line_break_anywhere_in_a_string_is_refused(kind: StringType) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    A line break is a breaking string. A trailing line feed is the classic hole of a pattern that
    ends in `$`.
    """
    checker = adapter(kind[0])
    values = ("a\n", "\na", "a\nb", "a\r", "a\r\nb", "\n")

    wrongly_accepted = [value for value in values if accepts(checker, value)]

    assert not wrongly_accepted


@parametrized("kind", STRING_TYPES)
def test_a_refused_string_reports_a_built_in_error_and_never_a_custom_one(kind: StringType) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    None of the three has a custom validator message: a refused string is reported with the
    error of a pattern or of a length, because a custom message can repeat the value.
    """
    spec, _, limit = kind
    checker = adapter(spec)

    for value in ("", "a" * (limit + 1), "a\nb", "a\u00e9b", "a\tb"):
        with pytest.raises(ValidationError) as caught:
            checker.validate_python(value)

        assert error_types(caught.value) <= set(STRING_ERRORS), value


# --- AC-4: the types in the fields that carry them ---------------------------------------------

# Fields that the criteria give the type `ModelRef`.
MODEL_REF_FIELDS: dict[str, Where] = {
    "model-id": ("models", 0, "id"),
    "model-family": ("models", 0, "family"),
    "route-name": (*ID_ROUTE, "name"),
    "route-resolves-to": (*ALIAS_ROUTE, "resolves_to"),
    "route-also-known-as": (*ID_ROUTE, "also_known_as", 0),
    "exclusion-alias": (*EXCLUSION, "aliases", 0),
    "exclusion-family-tag": (*EXCLUSION, "family_tags", 0),
}
# Fields that name "a catalog id". The criteria do not spell their type; a catalog id is a model
# `id`, so they are only checked for refusal, never for how long a value they keep.
CATALOG_ID_FIELDS: dict[str, Where] = {
    "candidate-model": ("profiles", 0, "candidates", 0, "models", 0),
    "fallback-model": ("profiles", 0, "fallbacks", 0, "models", 0),
    "assignment-model": ("assignments", 1, "model"),
}
POLICY_TEXT_FIELDS: dict[str, Where] = {
    "exclusion-reason": (*EXCLUSION, "reason"),
    "exclusion-source": (*EXCLUSION, "source"),
    "profile-capability": ("profiles", 0, "capability"),
}
RECORDED_MODEL_FIELDS: dict[str, Where] = {
    "agent-requested": ("agent", "model_requested"),
    "agent-observed": ("agent", "model_observed"),
    "coder-requested": ("coder_binding", "model_requested"),
    "coder-observed": ("coder_binding", "model_observed"),
}
ALPHABET_OF_A_MODEL_REF = "Aa0._:/@+-"
DISPLAY_TEXT = "Example Model 1.2 [effort=high, speed=fast]"
ALPHABET_OF_A_RECORD = "aZ09 ._:/@+-[]=,"


@parametrized("where", MODEL_REF_FIELDS)
def test_a_model_ref_field_keeps_a_value_of_its_whole_alphabet_whole(where: Where) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    `ModelRef` is a constrained string of 1 to 128 characters that is never truncated. The fields
    `id`, `family`, `name`, `resolves_to`, `also_known_as`, `aliases` and `family_tags` carry it.
    """
    for value in (ALPHABET_OF_A_MODEL_REF, "a", "a" * 128):
        loaded = dump(ModelPolicy.model_validate(changed(policy(), where, value)))

        assert reach(loaded, where) == value


@parametrized("where", {**MODEL_REF_FIELDS, **CATALOG_ID_FIELDS})
def test_a_model_name_field_refuses_a_value_outside_the_pattern_and_the_length(
    where: Where,
) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    A `ModelRef` is refused when it breaks its pattern or its length, and none has a custom
    validator message.
    """
    for value in ("a b", "a" * 129, "", "a\u00e9b"):
        error = assert_refused_at(changed(policy(), where, value), where)

        assert error_types(error) <= set(STRING_ERRORS), value


@parametrized("where", POLICY_TEXT_FIELDS)
def test_a_policy_text_field_keeps_printable_ascii_up_to_400_characters_whole(
    where: Where,
) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    `PolicyText` is printable ASCII of 1 to 400 characters and is never truncated. An exclusion's
    `reason` and `source` and a profile's `capability` carry it.
    """
    everything = "".join(map(chr, range(0x20, 0x7F)))
    for value in (everything, "x", "x" * 400):
        loaded = dump(ModelPolicy.model_validate(changed(policy(), where, value)))

        assert reach(loaded, where) == value


@parametrized("where", POLICY_TEXT_FIELDS)
def test_a_policy_text_field_refuses_a_value_outside_the_pattern_and_the_length(
    where: Where,
) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    `PolicyText` is refused when it breaks its pattern or its length, and none has a custom
    validator message.
    """
    for value in ("", "x" * 401, "a\nb", "a\tb", "a\u00e9b", "a\x7fb"):
        error = assert_refused_at(changed(policy(), where, value), where)

        assert error_types(error) <= set(STRING_ERRORS), value


@parametrized("where", RECORDED_MODEL_FIELDS)
def test_a_recorded_model_field_keeps_display_text_whole(where: Where) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    `RecordedModel` is a constrained string over letters, digits, the space and
    `. _ : / @ + - [ ] = ,` of 1 to 128 characters, and is never truncated.
    """
    for value in (DISPLAY_TEXT, ALPHABET_OF_A_RECORD, "a", "a" * 128):
        loaded = dump(ReviewResult.model_validate(changed(record(), where, value)))

        assert reach(loaded, where) == value


@parametrized("where", RECORDED_MODEL_FIELDS)
def test_a_recorded_model_field_refuses_a_value_outside_the_pattern_and_the_length(
    where: Where,
) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    `RecordedModel` is refused when it breaks its pattern or its length, and none has a custom
    validator message.
    """
    for value in ("", "a" * 129, "a'b", "a\nb", "a\u00e9b", "a\tb", "a;b"):
        error = assert_refused_at(changed(record(), where, value), where, ReviewResult)

        assert error_types(error) <= set(STRING_ERRORS), value


# --- AC-4: no text that load_contract raises shows a refused string ---------------------------

MARK = "ZQ7LEAK"  # a marker that no fixed message holds; every refused string carries it
MODEL_REF = "model-ref"
RECORDED_MODEL = "recorded-model"
POLICY_TEXT = "policy-text"
ID_PATTERN_KIND = "id-pattern"
ALL_KINDS = frozenset({MODEL_REF, RECORDED_MODEL, POLICY_TEXT, ID_PATTERN_KIND})
NOT_TEXT = ALL_KINDS - {POLICY_TEXT}  # a printable ASCII text allows what the others refuse
REF_LIKE = frozenset({MODEL_REF, ID_PATTERN_KIND})  # no space, no bracket
# name -> (the string, the kinds of string that it breaks). The criterion says "ten breaking
# strings" and lists eight: a line break, a quote, a backtick, `;`, `$`, a non-ASCII letter, a
# bracket in a `ModelRef` and 129 characters. A space in a `ModelRef` (which a `RecordedModel`
# allows) and a tab (which none allows) are the two narrowest additions the patterns give.
BREAKING: dict[str, tuple[str, frozenset[str]]] = {
    "line-break": (f"{MARK}\nTAIL", ALL_KINDS),
    "quote": (f'{MARK}"TAIL', NOT_TEXT),
    "backtick": (f"{MARK}`TAIL", NOT_TEXT),
    "semicolon": (f"{MARK};TAIL", NOT_TEXT),
    "dollar-sign": (f"{MARK}$TAIL", NOT_TEXT),
    "non-ascii-letter": (f"{MARK}\u00e9TAIL", ALL_KINDS),
    "bracket-in-a-model-ref": (f"{MARK}[TAIL]", REF_LIKE),
    "129-characters": ((MARK * 19)[:129], NOT_TEXT),
    "space-in-a-model-ref": (f"{MARK} TAIL", REF_LIKE),
    "tab": (f"{MARK}\tTAIL", ALL_KINDS),
}
FIELDS_OF_KIND: dict[str, tuple[type[Contract], Mapping[str, Where]]] = {
    MODEL_REF: (ModelPolicy, {**MODEL_REF_FIELDS, **CATALOG_ID_FIELDS}),
    RECORDED_MODEL: (ReviewResult, RECORDED_MODEL_FIELDS),
    POLICY_TEXT: (ModelPolicy, POLICY_TEXT_FIELDS),
    ID_PATTERN_KIND: (ModelPolicy, {"id-pattern": ID_PATTERN}),
}


def cases(*, breaking: bool) -> dict[str, tuple[type[Contract], Where, str]]:
    """Every (contract, field, string) where the string breaks the type of the field, or not."""
    found: dict[str, tuple[type[Contract], Where, str]] = {}
    for kind, (model, fields) in FIELDS_OF_KIND.items():
        for string_name, (value, breaks) in BREAKING.items():
            if (kind in breaks) == breaking:
                for field_name, where in fields.items():
                    found[f"{string_name}/{field_name}"] = (model, where, value)
    return found


def test_the_ten_breaking_strings_are_ten_distinct_strings() -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    "For each of ten breaking strings": the criterion lists eight, so two were added (see
    BREAKING). This keeps the table from shrinking.
    """
    values = [value for value, _ in BREAKING.values()]

    assert len(values) == len(set(values)) == 10


@parametrized("case", cases(breaking=True))
def test_the_text_that_load_contract_raises_does_not_contain_the_refused_string(
    case: tuple[type[Contract], Where, str],
) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    The text that `load_contract` raises does not contain the string. Each string holds a marker,
    so a partial echo of it fails the test as well as a whole one.
    """
    model, where, value = case

    text = raised_text(model, changed(document_for(model), where, value))

    assert value not in text
    assert MARK not in text


@parametrized("case", cases(breaking=False))
def test_a_string_that_the_pattern_of_a_type_allows_loads_whole(
    case: tuple[type[Contract], Where, str],
) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    A quote, a backtick, `;` and `$` break `ModelRef` and `RecordedModel` but not `PolicyText`,
    which is printable ASCII; a bracket and a space break `ModelRef` but `RecordedModel` allows
    them. This keeps each string to the types that the stated patterns refuse.
    """
    model, where, value = case

    loaded = dump(model.model_validate(changed(document_for(model), where, value)))

    assert reach(loaded, where) == value


@parametrized("where", POLICY_TEXT_FIELDS)
def test_the_text_that_load_contract_raises_does_not_contain_an_over_long_policy_text(
    where: Where,
) -> None:
    """expected_behavior_source: AC-4; BC-32; C-1; ORQLET-SEC-002; ORQLET-SEC-003.

    `PolicyText` is 1 to 400 characters, and the text that `load_contract` raises does not
    contain the string.
    """
    value = (MARK * 60)[:401]

    text = raised_text(ModelPolicy, changed(policy(), where, value))

    assert value not in text
    assert MARK not in text
