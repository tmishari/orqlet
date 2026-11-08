"""Model selection use case, `model_selection` (task dynamic-model-profiles, phase P-4).

Every test cites its `expected_behavior_source`. AC-6 (the mapping half), AC-7 and the application
half of AC-8 are acceptance criteria of phase P-4 in docs/design/dynamic-model-profiles/plan.yaml;
AC-1 to AC-6 on plain values and the domain half of AC-8 are in
tests/unit/domain/test_model_resolution.py (lint-imports and the gate are not tests). BC-n are rows
of design/component.md and ADR-n the decision records of design/: ADR-001 decision 7 (task scope),
ADR-002 decision 3 (the v2 contract and what it holds), ADR-005 decisions 1 and 2 (the exclusion,
the matching rule), BC-9, BC-13, BC-32 and BC-43.

"The brief, item n" is the n-th numbered rule of the brief of this phase's Tester; "The brief,
application API" is its description of `orqlet.application.usecases.model_selection`: the mapping
of the v2 contract to `ResolverPolicy` field for field, the drop of task-scoped assignments for
rendering, the codes ORQ-E543 and ORQ-E545 and the field paths of the problems, in the style
`models[0].routes[1].name`. The P-3 readings stay as implemented in
`orqlet.domain.model_identity`: an id pattern matches only as written, a string that two entries
name is unknown, an entry's logical id is not one of its names, an empty alias or tag matches
nothing, and a shared `resolves_to` is no conflict. A test that relies on one of them says so.

These tests were written first, by the Tester of phase P-4 on 2026-11-08, before
`orqlet.application.usecases.model_selection` existed. A policy is built in code as plain data and
validated with `ModelPolicy.model_validate`, or read from the valid fixture
(tests/fixtures/contracts/valid/orqlet.model-policy.v2.yaml, as the P-1 tests do). Names and texts
are placeholders.

Behaviour that neither the sources nor the brief settle is deliberately not pinned here:
- the order of the tuple that `policy_problems` returns, and whether one place is reported twice:
  the tests compare sets of `(code, path)` and rely on determinism only;
- whether a problem at a parent location (`models[i]`) comes with a problem at a child
  (`models[i].routes[j]`) or at a list entry that names the same model: the ORQ-E543 tests
  require the location that the brief names and no other code;
- what a candidate or fallback that names an excluded model only through a route string gets (the
  brief gives that rule for an assignment only);
- what `policy_problems` says about `resolves_to`, a profile `capability`, `retires_on`, the
  `documented`, `callable` and `evaluated` labels, an exclusion's `reason` and `source`, and a
  model that appears twice in one list: the brief names no problem for them, and the clean
  policies below do not use them to test it;
- the mapping of the fields that `ResolverPolicy` does not hold (`approved_by`, `approval_ref`,
  `documented`, `callable`, `evaluated`, `list_price`, `retires_on`, `capability`, and an
  exclusion's `id`, `reason` and `source`), and the type of the mappings in a `ProfileInput`
  (compared as plain `dict`);
- the order of `ORQ-E545` among problems of one policy and the behaviour for a `role_names` or
  `skill_names` that holds a name twice.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import functools
import inspect
import re
from collections.abc import Callable, Collection, Sequence
from importlib.util import resolve_name
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.usecases import model_selection
from orqlet.application.usecases.model_selection import (
    PolicyProblem,
    policy_problems,
    to_render_policy,
    to_resolver_policy,
)
from orqlet.domain.model_identity import ExclusionRule
from orqlet.domain.model_resolution import (
    AssignmentInput,
    Choice,
    ModelInput,
    ProfileInput,
    Resolution,
    ResolveRequest,
    ResolverPolicy,
    RouteInput,
    resolve,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "contracts" / "valid"
FIXTURE = FIXTURES / "orqlet.model-policy.v2.yaml"
LOADER = StrictYamlLoader()

E543 = "ORQ-E543"
E545 = "ORQ-E545"
CLAUDE = "claude-code"
CODEX = "codex"
ROLE = "example-role"
SKILL = "example-skill"
MARKER = "zq7leak"
APPROVALS = ("proposed", "approved", "disabled", "retired")
# A path is field names and indexes: `models[0].routes[1].name`. No model string can be one.
PATH_SHAPE = re.compile(r"^[a-z_]+(\[[0-9]+\])?(\.[a-z_]+(\[[0-9]+\])?)*$")

# --- the valid fixture ---------------------------------------------------


@functools.cache
def _parsed() -> dict[str, Any]:
    loaded = LOADER.load(FIXTURE.read_bytes(), source=FIXTURE.name)
    assert isinstance(loaded, dict)
    return loaded


def fixture_document() -> dict[str, Any]:
    """The valid fixture as plain data: a new copy on every call, which a test may change."""
    return copy.deepcopy(_parsed())


def fixture_policy() -> ModelPolicy:
    return ModelPolicy.model_validate(fixture_document())


def with_assignments(*extra: dict[str, Any]) -> ModelPolicy:
    """The fixture with more assignments after its own two."""
    document_ = fixture_document()
    document_["assignments"] = [*document_["assignments"], *extra]
    return ModelPolicy.model_validate(document_)


# --- policies built in code ----------------------------------------------


def route(
    client: str,
    name: str | None,
    *,
    kind: str = "id",
    resolves_to: str | None = None,
    also_known_as: Sequence[str] = (),
    access: str = "unknown",
) -> dict[str, Any]:
    return {
        "client": client,
        "kind": kind,
        "name": name,
        "resolves_to": resolves_to,
        "also_known_as": list(also_known_as),
        "access": access,
    }


def entry(
    model_id: str,
    *routes: dict[str, Any],
    family: str = "example-family",
    state: str = "approved",
) -> dict[str, Any]:
    return {
        "id": model_id,
        "family": family,
        "approval": {"state": state},
        "documented": {"evidence": "docs/example/evidence/entry.md", "date": "2026-10-30"},
        "callable": "not-run",
        "evaluated": {"state": "none"},
        "routes": list(routes),
    }


def exclusion(
    rule_id: str,
    *,
    aliases: Sequence[str] = (),
    id_patterns: Sequence[str] = (),
    family_tags: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "reason": "Example reason.",
        "source": "Example notice.",
        "aliases": list(aliases),
        "id_patterns": list(id_patterns),
        "family_tags": list(family_tags),
    }


def profile_doc(
    profile_id: str,
    *,
    candidates: Sequence[tuple[str, Sequence[str]]] = (),
    fallbacks: Sequence[tuple[str, Sequence[str]]] = (),
    escalation: str | None = None,
) -> dict[str, Any]:
    return {
        "id": profile_id,
        "capability": "Example capability.",
        "mode": "manual",
        "candidates": [{"client": client, "models": list(ids)} for client, ids in candidates],
        "fallbacks": [{"client": client, "models": list(ids)} for client, ids in fallbacks],
        "escalation": escalation,
    }


def assignment_doc(
    kind: str,
    name: str,
    *,
    profile: str | None = None,
    model: str | None = None,
    mode: str = "manual",
    task: str | None = None,
    client: str | None = None,
    effort: str | None = None,
) -> dict[str, Any]:
    return {
        "target": {"kind": kind, "name": name},
        "task": task,
        "client": client,
        "profile": profile,
        "model": model,
        "mode": mode,
        "effort": effort,
    }


LARGE = entry("example-large", route(CLAUDE, "example-large-1"))
SMALL = entry("example-small", route(CLAUDE, "example-small-1"))
QUALITY = profile_doc("quality", candidates=((CLAUDE, ("example-large",)),))


def document(
    *,
    models: Sequence[dict[str, Any]] | None = None,
    extra_models: Sequence[dict[str, Any]] = (),
    excluded: Sequence[dict[str, Any]] = (),
    candidates: Sequence[str] = ("example-large",),
    fallbacks: Sequence[str] = ("example-small",),
    skill_model: str = "example-large",
    profiles: Sequence[dict[str, Any]] | None = None,
    assignments: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A policy that has no problem unless an argument puts one in.

    Models: `example-large` (0), `example-small` (1), then `extra_models` (2, 3, ...). Profiles:
    `engineering` (0, whose escalation is `quality`) and `quality` (1). Assignments: the role
    `example-role` to the profile `engineering` (0) and the skill `example-skill` to a model (1).
    """
    engineering = profile_doc(
        "engineering",
        candidates=((CLAUDE, candidates),),
        fallbacks=((CLAUDE, fallbacks),),
        escalation="quality",
    )
    return {
        "schema": "orqlet.model-policy/v2",
        "policy_version": 1,
        "reviewed_for_release": "0.4.0",
        "models": list([LARGE, SMALL, *extra_models] if models is None else models),
        "excluded": list(excluded),
        "profiles": list([engineering, QUALITY] if profiles is None else profiles),
        "assignments": list(
            [
                assignment_doc("role", ROLE, profile="engineering"),
                assignment_doc("skill", SKILL, model=skill_model),
            ]
            if assignments is None
            else assignments
        ),
    }


def problems_of(
    document_: dict[str, Any],
    roles: Collection[str] = (ROLE,),
    skills: Collection[str] = (SKILL,),
) -> set[tuple[str, str]]:
    """The problems of a document as `(code, path)`; each has a known code and a plain path."""
    problems = policy_problems(ModelPolicy.model_validate(document_), roles, skills)
    for item in problems:
        assert item.code in {E543, E545}
        assert PATH_SHAPE.fullmatch(item.path), item.path
    return {(item.code, item.path) for item in problems}


# --- the API -------------------------------------------------------------


def test_a_policy_problem_is_a_frozen_slotted_pair_of_a_code_and_a_path() -> None:
    """expected_behavior_source: AC-7 ("each problem is a code and a field path"); BC-32; the
    brief, application API (`PolicyProblem(code: str, path: str)`, frozen and slotted).
    """
    problem = PolicyProblem(E543, "models[0]")

    assert (problem.code, problem.path) == (E543, "models[0]")
    assert problem == PolicyProblem(code=E543, path="models[0]")
    assert "__slots__" in vars(PolicyProblem)
    field = "path"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(problem, field, "models[1]")


def test_the_functions_take_the_arguments_of_the_brief() -> None:
    """expected_behavior_source: AC-7 (`policy_problems(policy, role_names, skill_names)`); the
    brief, application API.
    """
    assert list(inspect.signature(policy_problems).parameters) == [
        "policy",
        "role_names",
        "skill_names",
    ]
    assert list(inspect.signature(to_resolver_policy).parameters) == ["policy"]
    assert list(inspect.signature(to_render_policy).parameters) == ["policy"]


# --- the mapping of the contract to the resolver's inputs ----------------

EXPECTED_MODELS = (
    ModelInput(
        id="example-large",
        family="example-family",
        approval="approved",
        routes=(
            RouteInput(
                client="claude-code",
                kind="id",
                name="example-large-1",
                access="confirmed",
                resolves_to=None,
                also_known_as=("example-large-1-high",),
            ),
            RouteInput(
                client="codex",
                kind="alias",
                name="example-large-latest",
                access="blocked",
                resolves_to="example-large-1",
                also_known_as=(),
            ),
        ),
    ),
    ModelInput(
        id="example-small",
        family="example-family",
        approval="proposed",
        routes=(RouteInput(client="cursor", kind="id", name=None, access="unknown"),),
    ),
)
EXPECTED_EXCLUSIONS = (
    ExclusionRule(
        aliases=("blocked-alias",),
        id_patterns=("blocked-model-*", "vendor/blocked-?"),
        family_tags=("blocked-family",),
    ),
)
type Plain = tuple[str, str, dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], str | None]
EXPECTED_PROFILES: tuple[Plain, ...] = (
    (
        "quality",
        "manual",
        {CLAUDE: ("example-large",), CODEX: ("example-large", "example-small")},
        {CLAUDE: ("example-small",)},
        None,
    ),
    (
        "engineering",
        "automatic-with-fallbacks",
        {"cursor": ("example-small",)},
        {CODEX: ("example-small",)},
        "quality",
    ),
    (
        "economy",
        "automatic",
        {CLAUDE: ("example-small",)},
        {"cursor": ("example-small",)},
        "engineering",
    ),
)
REVIEWER_ASSIGNMENT = AssignmentInput(
    kind="role",
    name="example-reviewer",
    mode="automatic",
    model=None,
    profile="quality",
    task=None,
    client=None,
    effort=None,
)
SKILL_ASSIGNMENT = AssignmentInput(
    kind="skill",
    name="example-skill",
    mode="manual",
    model="example-large",
    profile=None,
    task="example-task",
    client="claude-code",
    effort="high",
)


def plain(item: ProfileInput) -> Plain:
    """A profile's fields with each mapping as a plain `dict`."""
    return (
        item.id,
        item.mode,
        dict(item.candidates),
        dict(item.fallbacks),
        item.escalation,
    )


def test_every_model_and_route_of_the_fixture_is_mapped_field_for_field() -> None:
    """expected_behavior_source: AC-6 (the mapping that later phases render from); BC-43; the
    brief, application API (`to_resolver_policy`: every model and route mapped field for field,
    the approval state from `approval.state`). The fixture sets every field of both routes.
    """
    mapped = to_resolver_policy(fixture_policy())

    assert mapped.models == EXPECTED_MODELS


def test_every_exclusion_of_the_fixture_is_mapped_to_a_rule() -> None:
    """expected_behavior_source: BC-9; ADR-005 decision 1; the brief, application API (every
    exclusion mapped; the rule is the P-3 `ExclusionRule`).
    """
    mapped = to_resolver_policy(fixture_policy())

    assert mapped.exclusions == EXPECTED_EXCLUSIONS


def test_every_profile_of_the_fixture_is_mapped_with_its_lists_keyed_by_client() -> None:
    """expected_behavior_source: the brief, application API ("mappings keyed by client"); the
    brief, item 5 (the lists of a profile are catalog ids by client, in order). The mappings are
    compared as plain `dict`: the type of a mapping is not pinned.
    """
    mapped = to_resolver_policy(fixture_policy())

    assert tuple(plain(item) for item in mapped.profiles) == EXPECTED_PROFILES


def test_every_assignment_of_the_fixture_is_mapped_with_its_target_as_kind_and_name() -> None:
    """expected_behavior_source: AC-6; BC-43; the brief, application API (assignment kind and
    name from `target`; the task is kept by the resolver mapping).
    """
    mapped = to_resolver_policy(fixture_policy())

    assert mapped.assignments == (REVIEWER_ASSIGNMENT, SKILL_ASSIGNMENT)


def test_the_result_is_made_of_the_plain_values_of_the_domain() -> None:
    """expected_behavior_source: AC-1 of P-4 (`resolve` takes plain values); the brief,
    application API (`ResolverPolicy`); AC-8 (no contract object crosses into the domain).
    """
    mapped = to_resolver_policy(fixture_policy())

    assert isinstance(mapped, ResolverPolicy)
    assert all(isinstance(item, ModelInput) for item in mapped.models)
    assert all(isinstance(item, RouteInput) for model in mapped.models for item in model.routes)
    assert all(isinstance(item, ExclusionRule) for item in mapped.exclusions)
    assert all(isinstance(item, ProfileInput) for item in mapped.profiles)
    assert all(isinstance(item, AssignmentInput) for item in mapped.assignments)
    assert isinstance(mapped.models, tuple)
    assert isinstance(mapped.assignments, tuple)


@pytest.mark.parametrize("state", APPROVALS)
def test_the_approval_state_of_a_model_is_the_state_of_its_approval(state: str) -> None:
    """expected_behavior_source: ADR-002 decision 3 (the approval is a state); the brief,
    application API ("approval state from `approval.state`").
    """
    extra = entry("example-extra", route(CLAUDE, "extra-1"), state=state)

    mapped = to_resolver_policy(ModelPolicy.model_validate(document(extra_models=[extra])))

    assert mapped.models[2].approval == state


def test_the_approval_state_is_read_from_the_fixture_too() -> None:
    """expected_behavior_source: the brief, application API ("approval state from
    `approval.state`"). The fixture's models are `approved` and `proposed`.
    """
    mapped = to_resolver_policy(fixture_policy())

    assert [item.approval for item in mapped.models] == ["approved", "proposed"]


def test_the_order_of_models_profiles_and_assignments_is_kept() -> None:
    """expected_behavior_source: the brief, item 5 (the order of the policy decides between two
    equally specific assignments); the brief, item 1 and 5 (candidate order is the policy's).
    """
    extra = [entry("example-z", route(CLAUDE, "z-1")), entry("example-a", route(CLAUDE, "a-1"))]
    document_ = document(extra_models=extra, candidates=("example-small", "example-large"))

    mapped = to_resolver_policy(ModelPolicy.model_validate(document_))

    assert [item.id for item in mapped.models] == [
        "example-large",
        "example-small",
        "example-z",
        "example-a",
    ]
    assert [item.id for item in mapped.profiles] == ["engineering", "quality"]
    assert dict(mapped.profiles[0].candidates) == {CLAUDE: ("example-small", "example-large")}
    assert [item.name for item in mapped.assignments] == [ROLE, SKILL]


def test_an_empty_policy_is_mapped_to_an_empty_resolver_policy() -> None:
    """expected_behavior_source: the brief, application API; the brief, item 7 (no policy and
    an empty policy give the same inputs).
    """
    empty = ModelPolicy.model_validate(document(models=(), profiles=(), assignments=()))

    assert to_resolver_policy(empty) == ResolverPolicy()
    assert to_render_policy(empty) == ResolverPolicy()


# --- AC-6: a task-scoped assignment can never reach a generated file -----


def skill_request(*, client: str = CLAUDE, task: str | None = None) -> ResolveRequest:
    """A request for the fixture's skill `example-skill`."""
    return ResolveRequest(client=client, target_kind="skill", target="example-skill", task=task)


def role_request(*, client: str = CLAUDE, task: str | None = None) -> ResolveRequest:
    """A request for the fixture's role `example-reviewer`."""
    return ResolveRequest(client=client, target_kind="role", target="example-reviewer", task=task)


TASK_PROFILE = assignment_doc("role", "example-reviewer", profile="economy", task="task-9")
TASK_MODEL = assignment_doc("skill", "example-other", model="example-large", task="task-8")
UNTASKED_MODEL = assignment_doc("skill", "example-third", model="example-small", client="codex")


def test_the_resolver_mapping_keeps_every_task_scoped_assignment() -> None:
    """expected_behavior_source: AC-6 ("an assignment that names a `task` applies only when the
    caller passes that task"; `to_resolver_policy` keeps it); BC-43; ADR-001 decision 7; the
    brief, application API.
    """
    mapped = to_resolver_policy(with_assignments(TASK_PROFILE, UNTASKED_MODEL, TASK_MODEL))

    assert [item.task for item in mapped.assignments] == [
        None,
        "example-task",
        "task-9",
        None,
        "task-8",
    ]
    assert [item.name for item in mapped.assignments] == [
        "example-reviewer",
        "example-skill",
        "example-reviewer",
        "example-third",
        "example-other",
    ]


def test_the_render_mapping_drops_every_task_scoped_assignment() -> None:
    """expected_behavior_source: AC-6 ("the mapping that later phases render from ignores every
    task-scoped assignment, so a task-scoped assignment can never reach a generated file"); BC-43;
    ADR-001 decision 7 ("task scope is a resolve-time selector only"); the brief, application API
    (`to_render_policy` removes every assignment whose `task` is not `None`). The assignments
    that stay keep their order.
    """
    mapped = to_render_policy(with_assignments(TASK_PROFILE, UNTASKED_MODEL, TASK_MODEL))

    assert all(item.task is None for item in mapped.assignments)
    assert [item.name for item in mapped.assignments] == ["example-reviewer", "example-third"]
    assert mapped.assignments[0] == REVIEWER_ASSIGNMENT
    assert mapped.assignments[1].model == "example-small"
    assert mapped.assignments[1].client == "codex"


def test_the_render_mapping_of_the_fixture_keeps_only_the_untasked_assignment() -> None:
    """expected_behavior_source: AC-6; BC-43; the brief, application API. The fixture's second
    assignment names the task `example-task`.
    """
    assert to_render_policy(fixture_policy()).assignments == (REVIEWER_ASSIGNMENT,)


def test_a_policy_of_task_scoped_assignments_only_renders_with_none() -> None:
    """expected_behavior_source: AC-6; BC-43; the brief, application API."""
    only_tasks = ModelPolicy.model_validate(
        document(assignments=[TASK_PROFILE, TASK_MODEL, TASK_PROFILE])
    )

    assert to_render_policy(only_tasks).assignments == ()
    assert len(to_resolver_policy(only_tasks).assignments) == 3


def test_the_two_mappings_differ_only_in_their_assignments() -> None:
    """expected_behavior_source: AC-6; the brief, application API ("the same, with every
    assignment whose `task` is not `None` removed").
    """
    policy_ = with_assignments(TASK_PROFILE, UNTASKED_MODEL, TASK_MODEL)

    resolver = to_resolver_policy(policy_)
    render = to_render_policy(policy_)

    assert render.models == resolver.models
    assert render.exclusions == resolver.exclusions
    assert tuple(plain(item) for item in render.profiles) == tuple(
        plain(item) for item in resolver.profiles
    )
    assert render.assignments != resolver.assignments


def test_a_task_scoped_assignment_applies_through_the_resolver_mapping_with_its_task_only() -> None:
    """expected_behavior_source: AC-6 ("applies only when the caller passes that task"); BC-43;
    ADR-001 decision 7; the brief, items 5 and 6. The fixture's second assignment gives the
    skill `example-skill`, for `claude-code` and the task `example-task`, the model
    `example-large` at effort `high`. That model is approved and its Claude Code route is named.
    """
    resolver = to_resolver_policy(fixture_policy())

    with_task = resolve(resolver, skill_request(task="example-task"))
    without_task = resolve(resolver, skill_request())
    other_task = resolve(resolver, skill_request(task="example-other-task"))
    other_client = resolve(resolver, skill_request(client=CODEX, task="example-task"))

    chosen = Choice(model="example-large", name="example-large-1", kind="id", effort="high")
    assert (with_task.outcome, with_task.source, with_task.selected) == (
        "selected",
        "role-assignment",
        chosen,
    )
    assert with_task.candidates == (chosen,)
    clients_choice = Resolution(outcome="client-chooses", source="automatic")
    assert without_task == clients_choice
    assert other_task == clients_choice
    assert other_client == clients_choice


def test_a_task_scoped_assignment_never_reaches_the_render_mapping() -> None:
    """expected_behavior_source: AC-6 ("a task-scoped assignment can never reach a generated
    file"); BC-43; ADR-001 decision 7; the brief, items 5 and 6. Through the render mapping the
    same request, with the task, is answered as if the assignment did not exist.
    """
    render = to_render_policy(fixture_policy())

    result = resolve(render, skill_request(task="example-task"))

    assert result == Resolution(outcome="client-chooses", source="automatic")


def test_the_untasked_assignments_resolve_the_same_through_both_mappings() -> None:
    """expected_behavior_source: AC-6; the brief, application API (the render mapping differs
    only in the dropped assignments); the brief, items 5 to 7. The fixture's role
    `example-reviewer` goes to the profile `quality` in mode `automatic`: for `claude-code` the
    client chooses among the one eligible candidate `example-large`.
    """
    policy_ = fixture_policy()

    through_resolver = resolve(to_resolver_policy(policy_), role_request())
    through_render = resolve(to_render_policy(policy_), role_request())

    assert through_resolver == through_render
    assert through_resolver == Resolution(
        outcome="client-chooses",
        source="automatic",
        profile="quality",
        mode="automatic",
        candidates=(Choice(model="example-large", name="example-large-1", kind="id"),),
    )


def test_a_task_scoped_assignment_beats_an_untasked_one_only_through_the_resolver_mapping() -> None:
    """expected_behavior_source: AC-6; BC-43; ADR-001 decision 7; the brief, item 5 (a set task
    before an unset one). The role `example-reviewer` has an untasked profile assignment and a
    task-scoped model assignment: with the task, the resolver mapping picks the model, and the
    render mapping still gives the profile.
    """
    scoped = assignment_doc("role", "example-reviewer", model="example-large", task="task-9")
    policy_ = with_assignments(scoped)

    resolver = resolve(to_resolver_policy(policy_), role_request(task="task-9"))
    render = resolve(to_render_policy(policy_), role_request(task="task-9"))

    assert (resolver.outcome, resolver.source) == ("selected", "role-assignment")
    assert (render.outcome, render.source) == ("client-chooses", "automatic")
    assert render.profile == "quality"


# --- AC-7: policy_problems -----------------------------------------------

EXCLUDED_KINDS = (
    "model-id",
    "model-id-pattern",
    "model-family",
    "route-name",
    "route-resolves-to",
    "route-also-known-as",
    "candidate",
    "fallback",
    "assignment-string",
    "assignment-through-the-model",
)


def excluded_document(kind: str, state: str) -> tuple[dict[str, Any], str]:
    """A document with one place that an exclusion matches, and the path that is reported."""
    alias = exclusion("rule-1", aliases=("banned-thing",))
    banned = entry("banned-thing", route(CLAUDE, "plain-route-1"), state=state)
    match kind:
        case "model-id":
            return document(extra_models=[banned], excluded=[alias]), "models[2]"
        case "model-id-pattern":
            pattern = exclusion("rule-1", id_patterns=("banned-model-*",))
            model = entry("banned-model-1", route(CLAUDE, "plain-route-2"), state=state)
            return document(extra_models=[model], excluded=[pattern]), "models[2]"
        case "model-family":
            tag = exclusion("rule-1", family_tags=("banned-family",))
            model = entry(
                "plain-id-3", route(CLAUDE, "plain-route-3"), family="banned-family", state=state
            )
            return document(extra_models=[model], excluded=[tag]), "models[2]"
        case "route-name":
            model = entry("plain-id-4", route(CLAUDE, "banned-thing"), state=state)
            return document(extra_models=[model], excluded=[alias]), "models[2].routes[0]"
        case "route-resolves-to":
            model = entry(
                "plain-id-5",
                route(CLAUDE, "plain-route-5"),
                route(CLAUDE, "plain-alias-5", kind="alias", resolves_to="banned-thing"),
                state=state,
            )
            return document(extra_models=[model], excluded=[alias]), "models[2].routes[1]"
        case "route-also-known-as":
            model = entry(
                "plain-id-6",
                route(CLAUDE, "plain-route-6", also_known_as=("banned-thing",)),
                state=state,
            )
            return document(extra_models=[model], excluded=[alias]), "models[2].routes[0]"
        case "candidate":
            listed = ("example-large", "banned-thing")
            result = document(extra_models=[banned], excluded=[alias], candidates=listed)
            return result, "profiles[0].candidates[0].models[1]"
        case "fallback":
            listed = ("example-small", "banned-thing")
            result = document(extra_models=[banned], excluded=[alias], fallbacks=listed)
            return result, "profiles[0].fallbacks[0].models[1]"
        case "assignment-string":
            result = document(extra_models=[banned], excluded=[alias], skill_model="banned-thing")
            return result, "assignments[1].model"
        case "assignment-through-the-model":
            model = entry("plain-id-7", route(CLAUDE, "banned-thing"), state=state)
            result = document(extra_models=[model], excluded=[alias], skill_model="plain-id-7")
            return result, "assignments[1].model"
        case _:
            raise AssertionError(kind)


@pytest.mark.parametrize("state", APPROVALS)
@pytest.mark.parametrize("kind", EXCLUDED_KINDS)
def test_a_place_that_matches_an_exclusion_is_reported_in_every_approval_state(
    kind: str, state: str
) -> None:
    """expected_behavior_source: AC-7 ("ORQ-E543 for every model, route, candidate, fallback or
    assignment that matches an exclusion in any approval state"); BC-9; ADR-005 decisions 1 and
    2; the brief, application API (the locations `models[i]`, `models[i].routes[j]`,
    `profiles[p].candidates[c].models[m]`, `profiles[p].fallbacks[c].models[m]` and
    `assignments[a].model`, the last also when the model it names is excluded). The id-pattern
    case relies on the P-3 reading that a pattern matches only as written.
    """
    document_, path = excluded_document(kind, state)

    found = problems_of(document_)

    assert (E543, path) in found
    assert {code for code, _ in found} == {E543}


def test_an_exclusion_that_matches_nothing_gives_no_problem() -> None:
    """expected_behavior_source: AC-7 (a clean policy returns `()`); ADR-005 decision 1 (an
    exclusion is data and matches only what it lists).
    """
    rule = exclusion(
        "rule-1",
        aliases=("banned-thing",),
        id_patterns=("banned-model-*",),
        family_tags=("banned-family",),
    )

    assert problems_of(document(excluded=[rule])) == set()


class Case(NamedTuple):
    """A document, the paths of ORQ-E545 that it must give, and the names it is checked with."""

    document: dict[str, Any]
    paths: frozenset[str]
    roles: tuple[str, ...] = (ROLE,)
    skills: tuple[str, ...] = (SKILL,)


def pair(
    first_route: dict[str, Any], second_route: dict[str, Any], state: str = "approved"
) -> list[dict[str, Any]]:
    """Two models, at 2 and 3 of a document, whose routes are these."""
    return [entry("plain-a", first_route), entry("plain-b", second_route, state=state)]


UNKNOWN_ENGINEERING = profile_doc(
    "engineering",
    candidates=((CLAUDE, ("example-large",)),),
    fallbacks=((CLAUDE, ("example-small",)),),
    escalation="quality",
)
E545_CASES = {
    "duplicate-model-id": Case(
        document(extra_models=[entry("example-large", route(CLAUDE, "example-large-copy"))]),
        frozenset({"models[2].id"}),
    ),
    "duplicate-exclusion-id": Case(
        document(
            excluded=[
                exclusion("rule-1", aliases=("banned-a",)),
                exclusion("rule-1", aliases=("banned-b",)),
            ]
        ),
        frozenset({"excluded[1].id"}),
    ),
    "unknown-candidate": Case(
        document(candidates=("example-large", "no-such-model")),
        frozenset({"profiles[0].candidates[0].models[1]"}),
    ),
    "unknown-fallback": Case(
        document(fallbacks=("example-small", "no-such-model")),
        frozenset({"profiles[0].fallbacks[0].models[1]"}),
    ),
    "unknown-assignment-model": Case(
        document(skill_model="no-such-model"), frozenset({"assignments[1].model"})
    ),
    "unknown-escalation": Case(
        document(profiles=[UNKNOWN_ENGINEERING]), frozenset({"profiles[0].escalation"})
    ),
    "unknown-assignment-profile": Case(
        document(profiles=[QUALITY]), frozenset({"assignments[0].profile"})
    ),
    "unknown-role": Case(document(), frozenset({"assignments[0].target.name"}), roles=()),
    "unknown-skill": Case(document(), frozenset({"assignments[1].target.name"}), skills=()),
    "a-skill-name-is-no-role": Case(
        document(), frozenset({"assignments[1].target.name"}), roles=(ROLE, SKILL), skills=()
    ),
    "a-role-name-is-no-skill": Case(
        document(), frozenset({"assignments[0].target.name"}), roles=(), skills=(ROLE, SKILL)
    ),
    "same-route-name": Case(
        document(
            extra_models=pair(route(CLAUDE, "shared-name"), route(CLAUDE, "Shared_Name")),
        ),
        frozenset({"models[3]"}),
    ),
    "route-name-and-also-known-as": Case(
        document(
            extra_models=pair(
                route(CLAUDE, "plain-route-a", also_known_as=("shared-name",)),
                route(CLAUDE, "shared-name"),
            ),
        ),
        frozenset({"models[3]"}),
    ),
    "two-also-known-as": Case(
        document(
            extra_models=pair(
                route(CLAUDE, "plain-route-a", also_known_as=("shared-name",)),
                route(CLAUDE, "plain-route-b", also_known_as=("SHARED_NAME",)),
            ),
        ),
        frozenset({"models[3]"}),
    ),
    "same-name-for-two-clients": Case(
        document(extra_models=pair(route(CLAUDE, "shared-name"), route(CODEX, "shared-name"))),
        frozenset({"models[3]"}),
    ),
    "same-name-with-a-proposed-model": Case(
        document(
            extra_models=pair(
                route(CLAUDE, "shared-name"), route(CLAUDE, "shared-name"), state="proposed"
            ),
        ),
        frozenset({"models[3]"}),
    ),
    "same-name-of-three-models": Case(
        document(
            extra_models=[
                entry("plain-a", route(CLAUDE, "shared-name")),
                entry("plain-b", route(CLAUDE, "shared-name")),
                entry("plain-c", route(CLAUDE, "shared-name")),
            ],
        ),
        frozenset({"models[3]", "models[4]"}),
    ),
}


@pytest.mark.parametrize("case", list(E545_CASES.values()), ids=list(E545_CASES))
def test_one_cross_reference_problem_gives_exactly_its_orq_e545_paths(case: Case) -> None:
    """expected_behavior_source: AC-7 ("ORQ-E545 for a duplicate id, an unknown model, profile,
    role or skill name in a profile, fallback, escalation or assignment, and for two entries that
    claim the same normalised name or `also_known_as`"); BC-13; ADR-002 decision 3; the brief,
    application API (`models[j].id`, `excluded[j].id`, the list entries, `assignments[a].model`,
    `profiles[p].escalation`, `assignments[a].profile`, `assignments[a].target.name` and
    `models[j]` for each pair `(i, j)` of `name_conflicts`, where `j` is the later entry). The
    same-name cases rely on the P-3 readings that a name is compared normalised and that a claim
    is a route `name` or an `also_known_as`.
    """
    found = problems_of(case.document, case.roles, case.skills)

    assert found == {(E545, path) for path in case.paths}


CLEAN_CASES = {
    "base": document(),
    "a-shared-resolves-to": document(
        extra_models=[
            entry("plain-x", route(CLAUDE, "alias-one", kind="alias", resolves_to="pinned-target")),
            entry("plain-y", route(CLAUDE, "alias-two", kind="alias", resolves_to="pinned-target")),
        ]
    ),
    "an-id-equal-to-another-route-name": document(
        extra_models=[
            entry("shared-thing", route(CLAUDE, "other-thing")),
            entry("plain-y", route(CLAUDE, "shared-thing")),
        ]
    ),
    "one-model-claiming-a-name-twice": document(
        extra_models=[entry("plain-x", route(CLAUDE, "same-name", also_known_as=("Same_Name",)))]
    ),
    "routes-without-a-name": document(
        extra_models=[
            entry("plain-x", route(CLAUDE, None)),
            entry("plain-y", route(CLAUDE, None)),
        ]
    ),
    "a-proposed-model-in-a-list": document(
        extra_models=[entry("example-proposed", route(CLAUDE, "proposed-1"), state="proposed")],
        candidates=("example-large", "example-proposed"),
    ),
}


@pytest.mark.parametrize("case", list(CLEAN_CASES.values()), ids=list(CLEAN_CASES))
def test_a_policy_with_nothing_wrong_gives_no_problem(case: dict[str, Any]) -> None:
    """expected_behavior_source: AC-7 ("a clean policy returns `()`"); BC-13. The cases rely on
    the P-3 readings that a shared `resolves_to` is no conflict and that an entry's logical id is
    not one of its names, so a catalog id equal to another entry's route name is no conflict.
    """
    policy_ = ModelPolicy.model_validate(case)

    assert policy_problems(policy_, (ROLE,), (SKILL,)) == ()


def test_the_valid_fixture_gives_no_problem() -> None:
    """expected_behavior_source: AC-7 (a clean policy built from the valid fixture returns
    `()`); BC-13. The fixture's role and skill are `example-reviewer` and `example-skill`.
    """
    result = policy_problems(fixture_policy(), ("example-reviewer",), ("example-skill",))

    assert result == ()


def test_the_problems_are_a_tuple_of_policy_problems() -> None:
    """expected_behavior_source: AC-7; the brief, application API (`-> tuple[PolicyProblem,
    ...]`).
    """
    problems = policy_problems(ModelPolicy.model_validate(document()), (), ())

    assert isinstance(problems, tuple)
    assert problems
    assert all(isinstance(item, PolicyProblem) for item in problems)


def marked(text: str) -> str:
    return f"{MARKER}-{text}"


def leaking_document() -> dict[str, Any]:
    """A policy with problems of both codes, and the marker in every model string."""
    first = entry(
        marked("a"),
        route(CLAUDE, marked("route-a"), also_known_as=(marked("aka"),)),
        route(CLAUDE, marked("alias-a"), kind="alias", resolves_to=marked("target")),
        family=marked("family"),
    )
    second = entry(marked("a"), route(CLAUDE, marked("route-a")), family=marked("family"))
    engineering = profile_doc(
        "engineering",
        candidates=((CLAUDE, (marked("a"), marked("ghost"))),),
        fallbacks=((CLAUDE, (marked("ghost"),)),),
        escalation="quality",
    )
    return document(
        models=[first, second],
        excluded=[
            exclusion(marked("rule"), aliases=(marked("route-a"),)),
            exclusion(marked("rule"), id_patterns=(marked("*"),)),
        ],
        profiles=[engineering],
        assignments=[
            assignment_doc("role", marked("role"), model=marked("ghost")),
            assignment_doc("skill", marked("skill"), model=marked("a")),
        ],
    )


def test_no_problem_holds_a_model_string() -> None:
    """expected_behavior_source: AC-7 ("each problem is a code and a field path and holds no
    model string"); BC-32; ADR-002 decision 3. A marker is in every model string of the policy
    (an id, a family, a route name, `resolves_to`, an alias, a list entry, an exclusion and the
    names of the assignment's target), and the policy has problems of both codes at several
    places.
    """
    policy_ = ModelPolicy.model_validate(leaking_document())

    problems = policy_problems(policy_, (ROLE,), (SKILL,))

    assert {item.code for item in problems} == {E543, E545}
    for item in problems:
        assert MARKER not in item.code
        assert MARKER not in item.path
        assert PATH_SHAPE.fullmatch(item.path), item.path
    assert MARKER not in repr(problems)
    assert MARKER not in str(problems)


def test_the_same_input_gives_the_same_problems_in_the_same_order() -> None:
    """expected_behavior_source: AC-7; the brief, application API ("the same input gives the
    same tuple"); BC-23's spirit for the validator.
    """
    policy_ = ModelPolicy.model_validate(leaking_document())

    first = policy_problems(policy_, (ROLE,), (SKILL,))

    assert [policy_problems(policy_, (ROLE,), (SKILL,)) for _ in range(5)] == [first] * 5


@pytest.mark.parametrize(
    "collection", [list, tuple, set, frozenset], ids=["list", "tuple", "set", "frozenset"]
)
def test_the_role_and_skill_names_may_be_any_collection(
    collection: Callable[[list[str]], Collection[str]],
) -> None:
    """expected_behavior_source: AC-7 (`policy_problems(policy, role_names, skill_names)`); the
    brief, application API (`Collection[str]`).
    """
    clean = ModelPolicy.model_validate(document())
    unknown = ModelPolicy.model_validate(document(skill_model="no-such-model"))

    assert policy_problems(clean, collection([ROLE]), collection([SKILL])) == ()
    found = policy_problems(unknown, collection([ROLE]), collection([SKILL]))
    assert {(item.code, item.path) for item in found} == {(E545, "assignments[1].model")}


# --- AC-8: the import check ----------------------------------------------

PACKAGE = "orqlet.application.usecases"
FILE_PROCESS_NETWORK = {
    "os",
    "pathlib",
    "io",
    "shutil",
    "tempfile",
    "subprocess",
    "socket",
    "urllib",
    "http",
    "ssl",
    "asyncio",
    "requests",
    "httpx",
    "glob",
    "sqlite3",
    "ftplib",
    "smtplib",
    "multiprocessing",
}
OUTER_LAYERS = ("orqlet.adapters", "orqlet.interface")
FORBIDDEN_NAMES = {"__import__", "eval", "exec", "open"}


def imported_modules(source: str) -> set[str]:
    """The absolute names of the modules that a source in the `usecases` package imports."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(resolve_name("." * node.level + (node.module or ""), PACKAGE))
    return modules


def refused_modules(modules: set[str]) -> set[str]:
    """The modules of a file, process or network kind, and the outer layers."""
    return {
        module
        for module in modules
        if module.split(".")[0] in FILE_PROCESS_NETWORK
        or any(module == layer or module.startswith(layer + ".") for layer in OUTER_LAYERS)
    }


def used_names(source: str) -> set[str]:
    return {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}


def test_the_module_imports_no_file_process_or_network_module() -> None:
    """expected_behavior_source: AC-8 ("the application module imports no file, process or
    network module (`os`, `pathlib`, `io`, `shutil`, `tempfile`, `subprocess`, `socket`,
    `urllib`, `http`, `ssl`, `asyncio`, `requests`, `httpx` and the like)"); ORQLET-ARCH-001;
    ORQLET-ARCH-002; C-1.
    """
    imported = imported_modules(inspect.getsource(model_selection))

    assert refused_modules(imported) == set()


def test_the_module_imports_nothing_from_the_adapters_or_the_interface() -> None:
    """expected_behavior_source: AC-8 (the layers: the application imports the domain and itself
    only); ORQLET-ARCH-001.
    """
    imported = imported_modules(inspect.getsource(model_selection))

    assert not any(module.startswith(OUTER_LAYERS) for module in imported)
    assert any(module.startswith("orqlet.domain") for module in imported)


def test_the_module_reaches_for_no_dynamic_import_and_no_file() -> None:
    """expected_behavior_source: AC-8 (no file module; the builtin `open` reads a file, which is
    this test's reading of the criterion); BC-23.
    """
    assert used_names(inspect.getsource(model_selection)) & FORBIDDEN_NAMES == set()


def test_the_import_check_finds_what_it_must_refuse() -> None:
    """expected_behavior_source: AC-8 (the failing and the passing case of the checks above)."""
    source = (
        "import os\nimport urllib.request\nfrom pathlib import Path\nimport dataclasses\n"
        "from orqlet.adapters.fs import yaml_loader\nfrom ...interface import cli\n"
        "from ..contracts import model_policy\nfrom orqlet.domain import model_resolution\n\n"
        "def f() -> None:\n    open('x')\n"
    )
    modules = imported_modules(source)

    assert refused_modules(modules) == {
        "os",
        "urllib.request",
        "pathlib",
        "orqlet.adapters.fs",
        "orqlet.interface",
    }
    assert {"orqlet.application.contracts", "orqlet.domain", "dataclasses"} <= modules
    assert used_names(source) & FORBIDDEN_NAMES == {"open"}
