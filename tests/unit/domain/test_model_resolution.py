"""Model resolution, `model_resolution` (task dynamic-model-profiles, phase P-4).

Every test cites its `expected_behavior_source`. AC-1 to AC-6 and AC-8 are acceptance criteria of
phase P-4 in docs/design/dynamic-model-profiles/plan.yaml; AC-7 and the mapping from a loaded
policy to the inputs of `resolve` are tested in tests/unit/application/test_model_selection.py,
which also holds the application half of AC-8 (lint-imports and the gate are not tests). BC-n are
rows of design/component.md and ADR-n the decision records of design/: ADR-001 decisions 3 to 7
(modes, precedence, constraints, sources, task scope), ADR-004 decision 3 (nothing shipped is
approved), ADR-005 decisions 1 and 2 (the exclusion), ADR-006 decision 7 (the reviewer's profile)
and ADR-007 decisions 1, 3 and 11 (family, identity, the diversity step).

"The brief, item n" is the n-th numbered rule of the brief of this phase's Tester. The brief fixes
the public API of the module and what the plan leaves to the design of the function: the order of
the constraints on one model and the route that is taken (item 1), the diversity rule (2), the
profile floor (3), the strings of an override and of a fallback (4), the levels and which
assignment applies (5), when a level is valid and what each outcome holds (6), what the result is
when no level is valid (7) and purity (8). The readings of `model_identity` that P-3 settled stay
as implemented: an id pattern matches only as written, a string that two entries name is unknown,
an entry's logical id is not one of its names, an empty alias or tag matches nothing, and a
shared `resolves_to` is no conflict. A test that relies on one of them says so.

These tests were written first, by the Tester of phase P-4 on 2026-11-08, before
`orqlet.domain.model_resolution` existed. Models, routes and policies are plain placeholder
values and never contract objects.

Behaviour that neither the sources nor the brief settle is deliberately not pinned here:
- the order of `rejected` and whether one rejection is reported twice: the tests compare sets of
  `(level, model, reason)`, and only `candidates` and `fallbacks` are compared as ordered;
- `Rejection.model` of a candidate id that no model carries (item 1 gives only its reason);
- `profile`, `mode` and `escalation` of a result whose first evaluated team level was invalid
  while a later level was valid (item 7 reads as the first level that was evaluated, which is not
  the level that gave the source);
- a named fallback when the mode is not `automatic-with-fallbacks`, a named fallback together
  with an override, and the fallbacks of a `profile` request;
- the role `orqlet-code-reviewer` with neither a coder model nor a coder profile (item 3 sets no
  floor; ADR-006 decision 7 and ADR-007 decision 11 can be read as always setting one);
- a `profile` request for a profile that the policy does not define, and the name of a skill that
  equals the reviewer role;
- two models with one id, and which of several routes an override string names (item 1 takes the
  first named, non-blocked route of the client, which is all the tests rely on);
- the effort of an override and of an explicit fallback, and what `diversity_unproven` is for a
  request that has no coder model.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import sys
import typing
from collections.abc import Mapping, Sequence
from importlib.util import resolve_name
from typing import Any, Literal, NamedTuple

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.domain import model_resolution
from orqlet.domain.model_identity import (
    ApprovalState,
    CatalogEntry,
    CatalogRoute,
    ExclusionRule,
    match_entry,
)
from orqlet.domain.model_resolution import (
    CODE_REVIEWER_ROLE,
    DEFAULT_CODER_PROFILE,
    PROFILE_ORDER,
    REJECTION_REASONS,
    SOURCES,
    Access,
    AssignmentInput,
    Choice,
    Effort,
    Level,
    Mode,
    ModelInput,
    Outcome,
    ProfileInput,
    Rejection,
    Resolution,
    ResolveRequest,
    ResolverPolicy,
    RouteInput,
    RouteKind,
    catalog_entries,
    is_model_excluded,
    resolve,
)

pytestmark = pytest.mark.unit

Kind = Literal["role", "skill"]
Target = Literal["role", "skill", "profile"]

# --- builders ------------------------------------------------------------

CLAUDE = "claude-code"
CODEX = "codex"
CURSOR = "cursor"
ROLE = "example-role"
SKILL = "example-skill"
MODES: tuple[Mode, ...] = ("automatic", "manual", "automatic-with-fallbacks")
EFFORTS: tuple[Effort, ...] = ("low", "medium", "high", "xhigh", "max")
APPROVALS: tuple[ApprovalState, ...] = ("proposed", "approved", "disabled", "retired")
ACCESS_VALUES: tuple[Access, ...] = ("unknown", "confirmed", "blocked")


def route(
    client: str,
    name: str | None,
    *,
    kind: RouteKind = "id",
    access: Access = "unknown",
    resolves_to: str | None = None,
    also_known_as: tuple[str, ...] = (),
) -> RouteInput:
    """One route of a model for one client."""
    return RouteInput(
        client=client,
        kind=kind,
        name=name,
        access=access,
        resolves_to=resolves_to,
        also_known_as=also_known_as,
    )


def model(
    id_: str,
    *routes: RouteInput,
    family: str = "anthropic",
    approval: ApprovalState = "approved",
) -> ModelInput:
    """A catalog model with these routes."""
    return ModelInput(id=id_, family=family, approval=approval, routes=routes)


def profile(
    id_: str,
    mode: Mode = "manual",
    candidates: Mapping[str, tuple[str, ...]] | None = None,
    fallbacks: Mapping[str, tuple[str, ...]] | None = None,
    escalation: str | None = None,
) -> ProfileInput:
    """A profile whose lists are catalog ids by client id."""
    return ProfileInput(
        id=id_,
        mode=mode,
        candidates=candidates or {},
        fallbacks=fallbacks or {},
        escalation=escalation,
    )


def assign_profile(
    profile_id: str,
    mode: Mode = "manual",
    *,
    name: str = ROLE,
    kind: Kind = "role",
    task: str | None = None,
    client: str | None = None,
    effort: Effort | None = None,
) -> AssignmentInput:
    """An assignment of a role or skill to a profile."""
    return AssignmentInput(
        kind=kind,
        name=name,
        mode=mode,
        profile=profile_id,
        task=task,
        client=client,
        effort=effort,
    )


def assign_model(
    model_id: str,
    mode: Mode = "manual",
    *,
    name: str = ROLE,
    kind: Kind = "role",
    task: str | None = None,
    client: str | None = None,
    effort: Effort | None = None,
) -> AssignmentInput:
    """An assignment of a role or skill to one catalog model."""
    return AssignmentInput(
        kind=kind,
        name=name,
        mode=mode,
        model=model_id,
        task=task,
        client=client,
        effort=effort,
    )


# One catalog. A name is claimed by one model only, so no string is ambiguous. The Claude Code
# route name of a model is its id; the other clients' names differ from it.
OPUS = model(
    "claude-opus-5-5",
    route(CLAUDE, "claude-opus-5-5", also_known_as=("claude-opus-5-5-xhigh",)),
    route(CURSOR, "cursor-opus"),
)
SONNET = model(
    "claude-sonnet-5-5", route(CLAUDE, "claude-sonnet-5-5"), route(CURSOR, "cursor-sonnet")
)
HAIKU = model("claude-haiku-5-5", route(CLAUDE, "claude-haiku-5-5"))
GEMINI = model("gemini-4-argon", route(CURSOR, "cursor-gemini-argon"), family="google")
SOL = model("gpt-6.1-sol", route(CODEX, "gpt-6.1-sol"), family="openai")
TERRA = model("gpt-6.1-terra", route(CODEX, "gpt-6.1-terra"), family="openai")
LUNA = model("gpt-6-luna", route(CODEX, "gpt-6-luna"), family="openai")
PROPOSED = model("claude-new-5", route(CLAUDE, "claude-new-5"), approval="proposed")
DISABLED = model("claude-old-4", route(CLAUDE, "claude-old-4"), approval="disabled")
RETIRED = model("claude-old-3", route(CLAUDE, "claude-old-3"), approval="retired")
CATALOG = (OPUS, SONNET, HAIKU, GEMINI, SOL, TERRA, LUNA)
EXTENDED = (*CATALOG, PROPOSED, DISABLED, RETIRED)

QUALITY = profile(
    "quality", "manual", {CLAUDE: (OPUS.id,), CODEX: (SOL.id,), CURSOR: (OPUS.id, GEMINI.id)}
)
ENGINEERING = profile(
    "engineering",
    "manual",
    {CLAUDE: (SONNET.id,), CODEX: (TERRA.id,), CURSOR: (SONNET.id, OPUS.id, GEMINI.id)},
    escalation="quality",
)
ECONOMY = profile(
    "economy", "manual", {CLAUDE: (HAIKU.id,), CODEX: (LUNA.id,)}, escalation="engineering"
)
PROFILES = (QUALITY, ENGINEERING, ECONOMY)


def policy(
    *,
    models: Sequence[ModelInput] = EXTENDED,
    exclusions: Sequence[ExclusionRule] = (),
    profiles: Sequence[ProfileInput] = PROFILES,
    assignments: Sequence[AssignmentInput] = (),
) -> ResolverPolicy:
    """A resolver policy from sequences."""
    return ResolverPolicy(
        models=tuple(models),
        exclusions=tuple(exclusions),
        profiles=tuple(profiles),
        assignments=tuple(assignments),
    )


def via_profile(
    candidates: Sequence[str],
    *,
    mode: Mode = "manual",
    fallbacks: Sequence[str] = (),
    client: str = CLAUDE,
    models: Sequence[ModelInput] = EXTENDED,
    exclusions: Sequence[ExclusionRule] = (),
    escalation: str | None = None,
    target: str = ROLE,
    effort: Effort | None = None,
) -> ResolverPolicy:
    """A policy that assigns the role `target` the profile `engineering` in `mode`.

    The profile offers these lists to `client` only. Its own mode is never the assignment's, so
    a test that passes has read the mode from the assignment (item 5).
    """
    own_mode: Mode = "automatic" if mode == "manual" else "manual"
    engineering = profile(
        "engineering",
        own_mode,
        {client: tuple(candidates)},
        {client: tuple(fallbacks)},
        escalation,
    )
    return policy(
        models=models,
        exclusions=exclusions,
        profiles=(engineering,),
        assignments=(assign_profile("engineering", mode, name=target, effort=effort),),
    )


def ask(
    target: str = ROLE,
    *,
    kind: Target = "role",
    client: str = CLAUDE,
    task: str | None = None,
    override: str | None = None,
    fallback: str | None = None,
    coder_model: str | None = None,
    coder_profile: str | None = None,
) -> ResolveRequest:
    """A request to resolve `target` for `client`."""
    return ResolveRequest(
        client=client,
        target_kind=kind,
        target=target,
        task=task,
        override=override,
        fallback=fallback,
        coder_model=coder_model,
        coder_profile=coder_profile,
    )


def choice(
    entry: ModelInput,
    name: str | None = None,
    kind: RouteKind = "id",
    effort: Effort | None = None,
) -> Choice:
    """The choice of `entry`; the name defaults to its id, which is its Claude Code route name."""
    return Choice(model=entry.id, name=entry.id if name is None else name, kind=kind, effort=effort)


def found(result: Resolution) -> set[tuple[str, str | None, str]]:
    """The rejections of a result as `(level, model, reason)`."""
    return {(item.level, item.model, item.reason) for item in result.rejected}


def ids_of(choices: Sequence[Choice]) -> list[str]:
    return [item.model for item in choices]


def literal_values(alias: Any) -> set[object]:
    """The values of a `Literal` alias, written as an assignment or as a `type` statement."""
    return set(typing.get_args(getattr(alias, "__value__", alias)))


# --- the public API ------------------------------------------------------


def test_the_constants_are_those_of_the_brief() -> None:
    """expected_behavior_source: the brief (the constants of the module); ADR-002 decision 6
    (the profiles are ordered quality, engineering, economy); ADR-006 decision 7 (the code
    reviewer and the coder draw from `engineering`).
    """
    assert PROFILE_ORDER == ("quality", "engineering", "economy")
    assert CODE_REVIEWER_ROLE == "orqlet-code-reviewer"
    assert DEFAULT_CODER_PROFILE == "engineering"


def test_the_sources_are_the_five_of_adr_001_and_no_other() -> None:
    """expected_behavior_source: AC-2 ("the sources are the five of ADR-001 decision 6 and no
    other"); ADR-001 decision 6.
    """
    assert SOURCES == (
        "task-override",
        "role-assignment",
        "profile-assignment",
        "automatic",
        "explicit-fallback",
    )


def test_the_rejection_reasons_are_the_closed_set_of_ac_3_in_its_order() -> None:
    """expected_behavior_source: AC-3 ("the rejection reasons are a closed set"); BC-10;
    ADR-001 decision 5; the brief (`REJECTION_REASONS` is the ten reasons in the order of AC-3).
    """
    assert REJECTION_REASONS == (
        "excluded",
        "not-approved",
        "disabled-or-retired",
        "no-route-for-client",
        "route-name-unknown",
        "access-blocked",
        "same-family-as-coder",
        "same-model-as-coder",
        "outside-profile",
        "override-invalid",
    )


def test_the_literals_are_the_closed_sets_of_the_brief() -> None:
    """expected_behavior_source: AC-2 and AC-3 (closed sets); ADR-001 decision 3 (the three
    modes); ADR-002 decision 3 (effort, route kind and access are closed enumerations); the
    brief (the literals of the module).
    """
    assert literal_values(Mode) == {"automatic", "manual", "automatic-with-fallbacks"}
    assert literal_values(Effort) == {"low", "medium", "high", "xhigh", "max"}
    assert literal_values(RouteKind) == {"id", "alias"}
    assert literal_values(Access) == {"unknown", "confirmed", "blocked"}
    assert literal_values(Outcome) == {"selected", "client-chooses", "none-qualifies"}
    assert literal_values(Level) == {"override", "assignment", "candidate", "fallback"}


FROZEN: dict[str, tuple[object, str]] = {
    "route": (route(CLAUDE, "n"), "name"),
    "model": (OPUS, "family"),
    "profile": (ENGINEERING, "mode"),
    "assignment": (assign_model(SONNET.id), "mode"),
    "policy": (policy(), "models"),
    "request": (ask(), "client"),
    "choice": (choice(OPUS), "model"),
    "rejection": (Rejection(level="candidate", model=None, reason="excluded"), "reason"),
    "resolution": (Resolution(outcome="client-chooses", source="automatic"), "outcome"),
}


@pytest.mark.parametrize(("value", "field"), list(FROZEN.values()), ids=list(FROZEN))
def test_the_inputs_and_outputs_are_frozen_slotted_dataclasses(value: object, field: str) -> None:
    """expected_behavior_source: AC-1 ("`resolve` takes plain values"); the brief (frozen
    slotted dataclasses).
    """
    assert dataclasses.is_dataclass(value)
    assert "__slots__" in vars(type(value))
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(value, field, "changed")


def test_the_inputs_and_outputs_are_plain_values_of_the_domain() -> None:
    """expected_behavior_source: AC-1 ("plain values"); AC-8 (the domain module imports nothing
    outside the standard library and the domain); the brief.

    No class in their hierarchy comes from outside the domain, so no contract class is one.
    """
    for value, _ in FROZEN.values():
        modules = {cls.__module__ for cls in type(value).__mro__}
        assert all(name == "builtins" or in_the_domain(name) for name in modules), value


def test_the_optional_fields_default_to_empty() -> None:
    """expected_behavior_source: the brief (the defaults of the dataclasses)."""
    plain_route = RouteInput(client=CLAUDE, kind="id", name="n")
    bare_profile = ProfileInput(id="economy", mode="manual")
    bare_assignment = AssignmentInput(kind="role", name="n", mode="manual")
    bare_request = ResolveRequest(client=CLAUDE, target_kind="role", target="n")
    empty = ResolverPolicy()
    bare_result = Resolution(outcome="client-chooses", source="automatic")

    assert (plain_route.access, plain_route.resolves_to, plain_route.also_known_as) == (
        "unknown",
        None,
        (),
    )
    assert ModelInput(id="m", family="f", approval="approved").routes == ()
    assert (len(bare_profile.candidates), len(bare_profile.fallbacks)) == (0, 0)
    assert bare_profile.escalation is None
    assert (bare_assignment.model, bare_assignment.profile, bare_assignment.task) == (
        None,
        None,
        None,
    )
    assert (bare_assignment.client, bare_assignment.effort) == (None, None)
    assert (empty.models, empty.exclusions, empty.profiles, empty.assignments) == ((), (), (), ())
    assert (bare_request.task, bare_request.override, bare_request.fallback) == (None, None, None)
    assert (bare_request.coder_model, bare_request.coder_profile) == (None, None)
    assert Choice(model="m", name="n", kind="id").effort is None
    assert (bare_result.selected, bare_result.profile, bare_result.mode) == (None, None, None)
    assert (bare_result.candidates, bare_result.fallbacks, bare_result.rejected) == ((), (), ())
    assert (bare_result.escalation, bare_result.diversity_unproven) == (None, False)


def test_resolve_takes_a_policy_and_a_request_and_no_clock() -> None:
    """expected_behavior_source: AC-1 ("`resolve` takes plain values and no clock"); BC-23; the
    brief, item 8.
    """
    assert len(inspect.signature(resolve).parameters) == 2


# --- AC-1: the four levels in manual mode --------------------------------

# One role, three levels. An override would name OPUS, the role assignment names SONNET, and the
# profile assignment, listed first so that the order of the policy is no help, offers HAIKU.
LEVELS = policy(assignments=(assign_profile("economy"), assign_model(SONNET.id)))


def test_a_valid_override_wins_over_every_team_level() -> None:
    """expected_behavior_source: AC-1 ("a valid higher level wins"); BC-5; R-5; ADR-001
    decision 4 (level 1); the brief, items 5 to 7 (a valid override leaves no profile, mode
    or escalation).
    """
    result = resolve(LEVELS, ask(override="claude-opus-5-5"))

    assert result == Resolution(outcome="selected", source="task-override", selected=choice(OPUS))


def test_a_valid_role_assignment_wins_over_a_profile_assignment() -> None:
    """expected_behavior_source: AC-1; BC-5; R-5; ADR-001 decision 4 (level 2 beats level 3);
    the brief, items 5 and 6.
    """
    result = resolve(LEVELS, ask())

    assert (result.outcome, result.source) == ("selected", "role-assignment")
    assert result.selected == choice(SONNET)
    assert result.candidates == (choice(SONNET),)
    assert result.rejected == ()
    assert result.mode == "manual"


def test_a_valid_profile_assignment_wins_over_the_automatic_result() -> None:
    """expected_behavior_source: AC-1; BC-5; R-5; ADR-001 decision 4 (level 3 beats level 4);
    the brief, items 5 to 7 (profile, mode and escalation come from the level).
    """
    result = resolve(policy(assignments=(assign_profile("economy"),)), ask())

    assert result == Resolution(
        outcome="selected",
        source="profile-assignment",
        selected=choice(HAIKU),
        profile="economy",
        mode="manual",
        candidates=(choice(HAIKU),),
        escalation="engineering",
    )


NO_LEVEL = {
    "no-assignment": policy(),
    "no-policy-at-all": ResolverPolicy(),
    "assignments-of-another-role": policy(
        assignments=(
            assign_model(SONNET.id, name="another-role"),
            assign_profile("economy", name="another-role"),
        )
    ),
}


@pytest.mark.parametrize("subject", list(NO_LEVEL.values()), ids=list(NO_LEVEL))
def test_with_no_override_and_no_assignment_the_automatic_result_applies(
    subject: ResolverPolicy,
) -> None:
    """expected_behavior_source: AC-1 ("then the automatic result"); BC-5; ADR-001 decisions 2
    and 4 (level 4: the client's own automatic selection); the brief, item 7.
    """
    assert resolve(subject, ask()) == Resolution(outcome="client-chooses", source="automatic")


@pytest.mark.parametrize(
    ("assignments", "source", "chosen"),
    [
        ((assign_model(SONNET.id),), "role-assignment", SONNET),
        ((assign_profile("economy"),), "profile-assignment", HAIKU),
    ],
    ids=["role-assignment", "profile-assignment"],
)
def test_an_invalid_override_is_reported_and_the_next_level_is_used(
    assignments: tuple[AssignmentInput, ...], source: str, chosen: ModelInput
) -> None:
    """expected_behavior_source: AC-1 ("an invalid higher level is reported in `rejected` with
    its reason, after which the next level is used and the source says which"); BC-5; BC-6;
    R-6; ADR-001 decision 4; the brief, items 5 to 7.
    """
    result = resolve(policy(assignments=assignments), ask(override="no-such-model"))

    assert (result.outcome, result.source) == ("selected", source)
    assert result.selected == choice(chosen)
    assert found(result) == {("override", None, "override-invalid")}
    assert len(result.rejected) == 1


def test_an_invalid_role_assignment_is_reported_and_the_profile_assignment_is_used() -> None:
    """expected_behavior_source: AC-1; BC-5; R-6; ADR-001 decision 4 ("a choice at level 1 to 3
    that fails a constraint is reported with its reason and is never replaced by a lower level
    without a visible finding"); the brief, items 5 and 6 (level `assignment`).
    """
    assignments = (assign_model(PROPOSED.id), assign_profile("economy"))

    result = resolve(policy(assignments=assignments), ask())

    assert (result.outcome, result.source) == ("selected", "profile-assignment")
    assert result.selected == choice(HAIKU)
    assert found(result) == {("assignment", PROPOSED.id, "not-approved")}


def test_when_every_team_level_is_invalid_nothing_qualifies_and_each_reason_is_kept() -> None:
    """expected_behavior_source: AC-1; BC-5; R-6; ADR-001 decision 4; the brief, items 6 and 7
    (an invalid level keeps its rejections; none valid and some present is `none-qualifies`).
    """
    unusable = profile("economy", "manual", {CLAUDE: (DISABLED.id,)})
    assignments = (assign_model(PROPOSED.id), assign_profile("economy"))

    result = resolve(policy(profiles=(unusable,), assignments=assignments), ask())

    assert (result.outcome, result.source) == ("none-qualifies", "automatic")
    assert result.selected is None
    assert result.candidates == ()
    assert found(result) == {
        ("assignment", PROPOSED.id, "not-approved"),
        ("candidate", DISABLED.id, "disabled-or-retired"),
    }


def test_each_invalid_level_above_the_one_used_leaves_its_rejection() -> None:
    """expected_behavior_source: AC-1; BC-5; BC-6; ADR-001 decision 4; the brief, items 5 to 7.

    An invalid override, then an invalid role assignment, then the valid profile assignment.
    """
    assignments = (assign_model(PROPOSED.id), assign_profile("economy"))

    result = resolve(policy(assignments=assignments), ask(override="no-such-model"))

    assert (result.outcome, result.source) == ("selected", "profile-assignment")
    assert result.selected == choice(HAIKU)
    assert found(result) == {
        ("override", None, "override-invalid"),
        ("assignment", PROPOSED.id, "not-approved"),
    }


@pytest.mark.parametrize("subject", [ResolverPolicy(), policy()], ids=["no-policy", "a-policy"])
def test_an_invalid_override_with_no_other_level_is_never_replaced_by_the_automatic_result(
    subject: ResolverPolicy,
) -> None:
    """expected_behavior_source: AC-1 ("an invalid override is never replaced without that
    entry"); BC-6; R-6; ADR-001 decision 4; the brief, item 7 (a level present but invalid).
    """
    result = resolve(subject, ask(override="no-such-model"))

    assert result == Resolution(
        outcome="none-qualifies",
        source="automatic",
        rejected=(Rejection(level="override", model=None, reason="override-invalid"),),
    )


class OverrideCase(NamedTuple):
    """An override string, the catalog and exclusions it meets, and the rejection it earns."""

    models: tuple[ModelInput, ...]
    exclusions: tuple[ExclusionRule, ...]
    override: str
    model: str | None
    reason: str


BANNED = ExclusionRule(aliases=("banned-model",), family_tags=("bannedfam",))
OVERRIDE_CASES = {
    "a-string-that-no-model-names": OverrideCase((), (), "no-such-model", None, "override-invalid"),
    "a-logical-id-is-no-name": OverrideCase(
        (model("m-logical", route(CLAUDE, "route-name-1")),),
        (),
        "m-logical",
        None,
        "override-invalid",
    ),
    "a-string-that-two-models-name": OverrideCase(
        (
            model("m-a", route(CLAUDE, "shared-name")),
            model("m-b", route(CLAUDE, "other-b", also_known_as=("Shared_Name",))),
        ),
        (),
        "shared-name",
        None,
        "override-invalid",
    ),
    "excluded-string-that-no-model-names": OverrideCase(
        (), (BANNED,), "Banned Model", None, "excluded"
    ),
    "excluded-string-of-a-model": OverrideCase(
        (model("m-x", route(CLAUDE, "banned-model")),), (BANNED,), "banned-model", "m-x", "excluded"
    ),
    "string-of-an-excluded-model": OverrideCase(
        (model("m-f", route(CLAUDE, "plain-name-f"), family="bannedfam-x"),),
        (BANNED,),
        "plain-name-f",
        "m-f",
        "excluded",
    ),
    "proposed": OverrideCase((PROPOSED,), (), "claude-new-5", PROPOSED.id, "not-approved"),
    "disabled": OverrideCase((DISABLED,), (), "claude-old-4", DISABLED.id, "disabled-or-retired"),
    "retired": OverrideCase((RETIRED,), (), "claude-old-3", RETIRED.id, "disabled-or-retired"),
    "route-of-another-client": OverrideCase(
        (model("m-o", route(CODEX, "name-o")),), (), "name-o", "m-o", "no-route-for-client"
    ),
    "route-without-a-name": OverrideCase(
        (model("m-u", route(CLAUDE, None, also_known_as=("spelling-u",))),),
        (),
        "spelling-u",
        "m-u",
        "route-name-unknown",
    ),
    "blocked-route": OverrideCase(
        (model("m-b", route(CLAUDE, "name-b", access="blocked")),),
        (),
        "name-b",
        "m-b",
        "access-blocked",
    ),
}


@pytest.mark.parametrize("case", list(OVERRIDE_CASES.values()), ids=list(OVERRIDE_CASES))
def test_an_invalid_override_is_reported_with_its_reason(case: OverrideCase) -> None:
    """expected_behavior_source: AC-1; AC-3 ("one fixture per reason", an override where item 4
    says so); BC-6; ADR-001 decision 5; the brief, items 1 and 4 (`Rejection.model` is the
    catalog id of the entry, or `None` when the string matched no entry). The cases
    `a-logical-id-is-no-name` and `a-string-that-two-models-name` rely on the P-3 readings that
    an entry's logical id is not one of its names and that a string two entries name is unknown.
    """
    subject = policy(models=case.models, exclusions=case.exclusions)

    result = resolve(subject, ask(override=case.override))

    assert (result.outcome, result.source, result.selected) == ("none-qualifies", "automatic", None)
    assert found(result) == {("override", case.model, case.reason)}
    assert len(result.rejected) == 1


@pytest.mark.parametrize("case", list(OVERRIDE_CASES.values()), ids=list(OVERRIDE_CASES))
def test_an_invalid_override_is_never_replaced_without_its_entry(case: OverrideCase) -> None:
    """expected_behavior_source: AC-1 ("an invalid override is never replaced without that
    entry"); BC-6; R-6; ADR-001 decision 4; the brief, items 4 to 6.
    """
    subject = policy(
        models=(*case.models, SONNET),
        exclusions=case.exclusions,
        assignments=(assign_model(SONNET.id),),
    )

    result = resolve(subject, ask(override=case.override))

    assert (result.outcome, result.source) == ("selected", "role-assignment")
    assert result.selected == choice(SONNET)
    assert found(result) == {("override", case.model, case.reason)}


@pytest.mark.parametrize(
    "spelling",
    ["anthropic/claude-opus-5-5[effort=high]", "Claude Opus 5.5", "claude-opus-5-5-xhigh"],
)
def test_an_override_is_matched_through_the_rule_and_names_the_clients_route(
    spelling: str,
) -> None:
    """expected_behavior_source: AC-2 ("a named override is `task-override`"); BC-18; ADR-005
    decision 1 (the one matching rule); ADR-007 decision 3; the brief, item 4 (the string is
    matched through `match_entry`); the result names the client's exact route name (item 1).
    """
    result = resolve(policy(), ask(override=spelling))

    assert (result.outcome, result.source) == ("selected", "task-override")
    assert result.selected == choice(OPUS, name="claude-opus-5-5")


def test_an_override_names_a_model_through_an_alias_route_that_resolves_to_it() -> None:
    """expected_behavior_source: AC-2; BC-18; ADR-005 decision 1 (the `resolves_to` of a route
    is a name of the entry); the brief, item 4 (`match_entry`); item 1 (the route is the first
    named, non-blocked route of the client, here the only one).
    """
    aliased = model(
        "m-aliased",
        route(CLAUDE, "alias-latest", kind="alias", resolves_to="pinned-version-1"),
    )

    result = resolve(policy(models=(aliased,)), ask(override="pinned-version-1"))

    assert result.source == "task-override"
    assert result.selected == Choice(model="m-aliased", name="alias-latest", kind="alias")


def test_a_rejection_never_holds_the_string_that_a_caller_gave() -> None:
    """expected_behavior_source: BC-32 (no finding prints a recorded model string); ADR-002
    decision 3 ("no finding prints a recorded model string"); the brief (`Rejection.model` is
    the catalog id, or `None`, "never the raw string").
    """
    marker = "zq7leak"
    for text in (f"{marker}-no-such-model", f"{marker} Banned Model"):
        result = resolve(policy(exclusions=(BANNED,)), ask(override=text, fallback=text))

        assert result.rejected
        assert marker not in repr(result)


# --- AC-2: the modes and the sources -------------------------------------


def test_automatic_lists_the_ordered_eligible_candidates_and_the_client_chooses() -> None:
    """expected_behavior_source: AC-2 ("no selected model, says that the client chooses, and has
    the source `automatic`; it lists the ordered eligible candidates"); BC-2; BC-27; ADR-001
    decision 3; the brief, items 5 and 6 (an `automatic` result lists no fallbacks).
    """
    subject = via_profile(
        (SONNET.id, HAIKU.id), mode="automatic", fallbacks=(OPUS.id,), escalation="quality"
    )

    result = resolve(subject, ask())

    assert result == Resolution(
        outcome="client-chooses",
        source="automatic",
        profile="engineering",
        mode="automatic",
        candidates=(choice(SONNET), choice(HAIKU)),
        escalation="quality",
    )


def test_automatic_with_fallbacks_lists_the_ordered_eligible_fallbacks_too() -> None:
    """expected_behavior_source: AC-2 ("and, for fallbacks, the ordered eligible fallbacks");
    BC-27; ADR-001 decision 3; the brief, items 5 and 6.
    """
    subject = via_profile(
        (SONNET.id, HAIKU.id), mode="automatic-with-fallbacks", fallbacks=(OPUS.id, HAIKU.id)
    )

    result = resolve(subject, ask())

    assert (result.outcome, result.source, result.selected) == ("client-chooses", "automatic", None)
    assert result.mode == "automatic-with-fallbacks"
    assert result.candidates == (choice(SONNET), choice(HAIKU))
    assert result.fallbacks == (choice(OPUS), choice(HAIKU))


def test_the_candidates_and_the_fallbacks_keep_the_order_of_the_policy() -> None:
    """expected_behavior_source: AC-2 ("ordered"); BC-27; ADR-001 decision 3 ("the first
    eligible candidate in the approved order"; "an explicit, approved, ordered fallback list").
    """
    subject = via_profile(
        (HAIKU.id, OPUS.id, SONNET.id),
        mode="automatic-with-fallbacks",
        fallbacks=(SONNET.id, HAIKU.id, OPUS.id),
    )

    result = resolve(subject, ask())

    assert ids_of(result.candidates) == [HAIKU.id, OPUS.id, SONNET.id]
    assert ids_of(result.fallbacks) == [SONNET.id, HAIKU.id, OPUS.id]


def test_an_ineligible_candidate_or_fallback_is_not_listed_and_has_its_reason() -> None:
    """expected_behavior_source: AC-2 ("ordered eligible"); AC-3 (a `proposed` model is never
    listed); BC-10; the brief, item 6 (levels `candidate` and `fallback`).
    """
    subject = via_profile(
        (SONNET.id, PROPOSED.id, HAIKU.id),
        mode="automatic-with-fallbacks",
        fallbacks=(DISABLED.id, OPUS.id),
    )

    result = resolve(subject, ask())

    assert ids_of(result.candidates) == [SONNET.id, HAIKU.id]
    assert ids_of(result.fallbacks) == [OPUS.id]
    assert found(result) == {
        ("candidate", PROPOSED.id, "not-approved"),
        ("fallback", DISABLED.id, "disabled-or-retired"),
    }


def test_automatic_without_an_eligible_candidate_still_lets_the_client_choose() -> None:
    """expected_behavior_source: ADR-001 decision 3 (`automatic`: no pin, the client's own
    selection applies); the brief, item 6 (a non-manual level is valid when the request is not
    constrained) and item 7.
    """
    result = resolve(via_profile((PROPOSED.id,), mode="automatic"), ask())

    assert (result.outcome, result.source, result.selected) == ("client-chooses", "automatic", None)
    assert result.candidates == ()
    assert found(result) == {("candidate", PROPOSED.id, "not-approved")}


FALLBACKS = via_profile(
    (SONNET.id,), mode="automatic-with-fallbacks", fallbacks=(OPUS.id, HAIKU.id)
)


@pytest.mark.parametrize(
    "spelling",
    ["claude-opus-5-5", "Claude Opus 5.5", "anthropic/claude-opus-5-5[effort=high]"],
)
def test_a_fallback_named_by_the_caller_is_the_source_explicit_fallback(spelling: str) -> None:
    """expected_behavior_source: AC-2 ("a fallback named by the caller is the source
    `explicit-fallback`"); BC-27; ADR-001 decisions 3 and 6; the brief, items 4 and 6.
    """
    result = resolve(FALLBACKS, ask(fallback=spelling))

    assert (result.outcome, result.source) == ("selected", "explicit-fallback")
    assert result.selected == choice(OPUS)
    assert result.selected in result.fallbacks


def test_a_named_fallback_that_the_level_does_not_list_is_outside_the_profile() -> None:
    """expected_behavior_source: the brief, items 4 and 6 (a named fallback that is not one of
    the level's fallbacks is `outside-profile` at level `fallback`, and the outcome stays
    `client-chooses`).
    """
    result = resolve(FALLBACKS, ask(fallback="claude-sonnet-5-5"))

    assert (result.outcome, result.source, result.selected) == ("client-chooses", "automatic", None)
    assert ("fallback", SONNET.id, "outside-profile") in found(result)


def test_a_named_fallback_that_matches_no_model_is_outside_the_profile_without_its_text() -> None:
    """expected_behavior_source: the brief, items 4 and 6 (unmatched: `Rejection.model` is
    `None`); BC-32 (no recorded string is repeated).
    """
    result = resolve(FALLBACKS, ask(fallback="zq7leak-no-such-model"))

    assert (result.outcome, result.source) == ("client-chooses", "automatic")
    assert ("fallback", None, "outside-profile") in found(result)
    assert "zq7leak" not in repr(result)


def test_a_named_fallback_that_is_listed_but_not_eligible_is_rejected_with_its_reason() -> None:
    """expected_behavior_source: AC-3; BC-10; the brief, items 4 and 6 ("otherwise rule 1 to 3
    decide"; "if it is not eligible, a Rejection is added and the outcome stays
    `client-chooses`").
    """
    subject = via_profile(
        (SONNET.id,), mode="automatic-with-fallbacks", fallbacks=(DISABLED.id, OPUS.id)
    )

    result = resolve(subject, ask(fallback="claude-old-4"))

    assert (result.outcome, result.source, result.selected) == ("client-chooses", "automatic", None)
    assert ("fallback", DISABLED.id, "disabled-or-retired") in found(result)


SOURCE_SCENARIOS: dict[str, tuple[ResolverPolicy, ResolveRequest, str]] = {
    "task-override": (policy(), ask(override="claude-sonnet-5-5"), "task-override"),
    "role-assignment": (policy(assignments=(assign_model(SONNET.id),)), ask(), "role-assignment"),
    "skill-assignment": (
        policy(assignments=(assign_model(SONNET.id, kind="skill", name=SKILL),)),
        ask(SKILL, kind="skill"),
        "role-assignment",
    ),
    "profile-assignment": (via_profile((SONNET.id,)), ask(), "profile-assignment"),
    "profile-request": (policy(), ask("engineering", kind="profile"), "profile-assignment"),
    "automatic": (via_profile((SONNET.id,), mode="automatic"), ask(), "automatic"),
    "no-policy": (ResolverPolicy(), ask(), "automatic"),
    "none-qualifies": (via_profile((PROPOSED.id,)), ask(), "automatic"),
    "invalid-override": (policy(), ask(override="no-such-model"), "automatic"),
    "explicit-fallback": (FALLBACKS, ask(fallback="claude-opus-5-5"), "explicit-fallback"),
    "rejected-fallback": (FALLBACKS, ask(fallback="no-such-model"), "automatic"),
}


@pytest.mark.parametrize(
    ("subject", "request_", "source"), list(SOURCE_SCENARIOS.values()), ids=list(SOURCE_SCENARIOS)
)
def test_the_source_of_a_result_is_one_of_the_five(
    subject: ResolverPolicy, request_: ResolveRequest, source: str
) -> None:
    """expected_behavior_source: AC-2 ("the sources are the five of ADR-001 decision 6 and no
    other"); BC-27; ADR-001 decision 6; the brief, items 5 to 7.
    """
    result = resolve(subject, request_)

    assert result.source == source
    assert result.source in SOURCES


def test_every_one_of_the_five_sources_is_produced_by_a_fixture() -> None:
    """expected_behavior_source: AC-2 (the five sources); ADR-001 decision 6; BC-27."""
    assert {source for _, _, source in SOURCE_SCENARIOS.values()} == set(SOURCES)


# --- AC-3: the closed set of reasons -------------------------------------

BANNED_MODEL = model("m-banned", route(CLAUDE, "banned-model"))
UNNAMED = model("m-unnamed", route(CLAUDE, None))
BLOCKED = model("m-blocked", route(CLAUDE, "name-blocked", access="blocked"))
REASON_FIXTURES: dict[str, tuple[ResolverPolicy, ResolveRequest]] = {
    "excluded": (
        via_profile((BANNED_MODEL.id,), models=(BANNED_MODEL,), exclusions=(BANNED,)),
        ask(),
    ),
    "not-approved": (via_profile((PROPOSED.id,)), ask()),
    "disabled-or-retired": (via_profile((DISABLED.id,)), ask()),
    "no-route-for-client": (via_profile((SOL.id,)), ask()),
    "route-name-unknown": (via_profile((UNNAMED.id,), models=(UNNAMED,)), ask()),
    "access-blocked": (via_profile((BLOCKED.id,), models=(BLOCKED,)), ask()),
    "same-family-as-coder": (
        via_profile((OPUS.id,), client=CURSOR),
        ask(client=CURSOR, coder_model=SONNET.id),
    ),
    "same-model-as-coder": (via_profile((SONNET.id,)), ask(coder_model=SONNET.id)),
    "outside-profile": (
        policy(assignments=(assign_profile("economy"),)),
        ask(coder_profile="engineering"),
    ),
    "override-invalid": (policy(), ask(override="no-such-model")),
}


def test_there_is_one_fixture_for_each_reason_of_the_closed_set() -> None:
    """expected_behavior_source: AC-3 ("one fixture per reason"); the brief (the reasons)."""
    assert set(REASON_FIXTURES) == set(REJECTION_REASONS)


@pytest.mark.parametrize("reason", REJECTION_REASONS)
def test_one_fixture_per_reason_yields_exactly_that_reason(reason: str) -> None:
    """expected_behavior_source: AC-3 ("one fixture per reason yields exactly that reason");
    BC-10; BC-4; ADR-001 decision 5; ADR-004 decision 3; the brief, items 1 to 4.
    """
    subject, request_ = REASON_FIXTURES[reason]

    result = resolve(subject, request_)

    assert (result.outcome, result.selected, result.candidates) == ("none-qualifies", None, ())
    assert {item.reason for item in result.rejected} == {reason}
    assert len(result.rejected) == 1
    expected_level = "override" if reason == "override-invalid" else "candidate"
    assert result.rejected[0].level == expected_level


class ExcludedCase(NamedTuple):
    """A model, by id and family and routes, that a rule excludes, and the rule."""

    id: str
    routes: tuple[RouteInput, ...]
    family: str
    rule: ExclusionRule


EXCLUDED_CASES = {
    "alias-of-the-id": ExcludedCase(
        "banned-thing",
        (route(CLAUDE, "plain-name-1"),),
        "anthropic",
        ExclusionRule(aliases=("banned-thing",)),
    ),
    "alias-of-a-route-name": ExcludedCase(
        "m-2",
        (route(CLAUDE, "banned-thing"),),
        "anthropic",
        ExclusionRule(aliases=("banned-thing",)),
    ),
    "alias-of-a-resolves-to": ExcludedCase(
        "m-3",
        (route(CLAUDE, "alias-3", kind="alias", resolves_to="banned-thing"),),
        "anthropic",
        ExclusionRule(aliases=("banned-thing",)),
    ),
    "alias-of-an-also-known-as": ExcludedCase(
        "m-4",
        (route(CLAUDE, "plain-name-4", also_known_as=("Banned_Thing",)),),
        "anthropic",
        ExclusionRule(aliases=("banned-thing",)),
    ),
    "id-pattern-on-the-id": ExcludedCase(
        "banned-5",
        (route(CLAUDE, "plain-name-5"),),
        "anthropic",
        ExclusionRule(id_patterns=("banned-*",)),
    ),
    "id-pattern-on-a-route-name": ExcludedCase(
        "m-6", (route(CLAUDE, "banned-6"),), "anthropic", ExclusionRule(id_patterns=("banned-?",))
    ),
    "family-tag-on-the-family": ExcludedCase(
        "m-7",
        (route(CLAUDE, "plain-name-7"),),
        "BannedFam-1",
        ExclusionRule(family_tags=("bannedfam",)),
    ),
}


@pytest.mark.parametrize("approval", APPROVALS)
@pytest.mark.parametrize("case", list(EXCLUDED_CASES.values()), ids=list(EXCLUDED_CASES))
def test_an_excluded_model_is_rejected_whatever_its_state(
    case: ExcludedCase, approval: ApprovalState
) -> None:
    """expected_behavior_source: AC-3 ("an `excluded` model is rejected whatever its state");
    BC-9; ADR-005 decision 2 ("an exclusion applies to entries in every state, `proposed`
    included"; the resolver rejects it with the reason `excluded`); the brief, item 1 (a)
    (`is_model_excluded` on the id, the family and every route string). The id pattern cases
    rely on the P-3 reading that a pattern matches only as written.
    """
    entry = model(case.id, *case.routes, family=case.family, approval=approval)

    result = resolve(
        via_profile((entry.id,), models=(entry,), exclusions=(case.rule,)),
        ask(),
    )

    assert result.outcome == "none-qualifies"
    assert result.selected is None
    assert found(result) == {("candidate", entry.id, "excluded")}


def test_an_excluded_model_is_reported_as_excluded_before_any_other_reason() -> None:
    """expected_behavior_source: AC-3; ADR-005 decision 2; the brief, item 1 (the first failing
    constraint decides, and `excluded` is the first).
    """
    entry = model("banned-thing", approval="proposed")
    rule = ExclusionRule(aliases=("banned-thing",))

    result = resolve(via_profile((entry.id,), models=(entry,), exclusions=(rule,)), ask())

    assert found(result) == {("candidate", entry.id, "excluded")}


class CandidateCase(NamedTuple):
    """A model that a manual profile offers, and the reason it earns."""

    model: ModelInput
    reason: str


CANDIDATE_CASES = {
    "proposed": CandidateCase(PROPOSED, "not-approved"),
    "disabled": CandidateCase(DISABLED, "disabled-or-retired"),
    "retired": CandidateCase(RETIRED, "disabled-or-retired"),
    "no-routes": CandidateCase(model("m-1"), "no-route-for-client"),
    "a-route-of-another-client": CandidateCase(
        model("m-2", route(CODEX, "name-2")), "no-route-for-client"
    ),
    "an-unnamed-route-of-another-client-only": CandidateCase(
        model("m-3", route(CODEX, None)), "no-route-for-client"
    ),
    "an-unnamed-route": CandidateCase(model("m-4", route(CLAUDE, None)), "route-name-unknown"),
    "unnamed-routes-one-of-them-blocked": CandidateCase(
        model("m-5", route(CLAUDE, None), route(CLAUDE, None, access="blocked")),
        "route-name-unknown",
    ),
    "an-unnamed-route-that-is-blocked": CandidateCase(
        model("m-6", route(CLAUDE, None, access="blocked")), "route-name-unknown"
    ),
    "a-blocked-route": CandidateCase(
        model("m-7", route(CLAUDE, "name-7", access="blocked")), "access-blocked"
    ),
    "every-named-route-blocked": CandidateCase(
        model(
            "m-8",
            route(CLAUDE, "name-8a", access="blocked"),
            route(CLAUDE, "name-8b", access="blocked"),
        ),
        "access-blocked",
    ),
    "an-unnamed-route-and-a-blocked-named-one": CandidateCase(
        model("m-9", route(CLAUDE, None), route(CLAUDE, "name-9", access="blocked")),
        "access-blocked",
    ),
    "proposed-without-routes": CandidateCase(model("m-10", approval="proposed"), "not-approved"),
    "disabled-without-routes": CandidateCase(
        model("m-11", approval="disabled"), "disabled-or-retired"
    ),
}


@pytest.mark.parametrize("case", list(CANDIDATE_CASES.values()), ids=list(CANDIDATE_CASES))
def test_a_candidate_that_fails_a_constraint_gets_the_first_failing_reason(
    case: CandidateCase,
) -> None:
    """expected_behavior_source: AC-3; BC-4; BC-10; ADR-001 decision 5; ADR-004 decision 3; the
    brief, item 1 (the first failing one decides, in the order: excluded, not-approved,
    disabled-or-retired, no-route-for-client, route-name-unknown, access-blocked; (c) approval;
    (d) the routes of the request's client).
    """
    result = resolve(via_profile((case.model.id,), models=(case.model,)), ask())

    assert (result.outcome, result.selected) == ("none-qualifies", None)
    assert found(result) == {("candidate", case.model.id, case.reason)}


def test_a_catalog_id_that_no_model_carries_is_not_approved() -> None:
    """expected_behavior_source: the brief, item 1 (b) ("a catalog id that no model carries is
    `not-approved`"); `Rejection.model` for it is deliberately not pinned.
    """
    result = resolve(via_profile(("m-ghost",)), ask())

    assert result.outcome == "none-qualifies"
    assert [(item.level, item.reason) for item in result.rejected] == [
        ("candidate", "not-approved")
    ]


@pytest.mark.parametrize("access", ["unknown", "confirmed"])
def test_an_unknown_or_confirmed_access_passes(access: Access) -> None:
    """expected_behavior_source: the brief, item 1 (d) ("access `unknown` and `confirmed` both
    pass"); ADR-002 decision 3 (`access` is an attested label); ADR-001 decision 5 (access not
    blocked).
    """
    entry = model("m-1", route(CLAUDE, "name-1", access=access))

    result = resolve(via_profile((entry.id,), models=(entry,)), ask())

    assert result.selected == choice(entry, name="name-1")


@pytest.mark.parametrize("kind", ["id", "alias"])
def test_the_choice_carries_the_name_and_the_kind_of_the_route(kind: RouteKind) -> None:
    """expected_behavior_source: AC-3 (route `name`); BC-3; BC-28; the brief, item 1 (d) ("its
    `name` and `kind` go into the Choice").
    """
    resolves_to = "name-1" if kind == "alias" else None
    entry = model("m-1", route(CLAUDE, "alias-1", kind=kind, resolves_to=resolves_to))

    result = resolve(via_profile((entry.id,), models=(entry,)), ask())

    assert result.selected == Choice(model="m-1", name="alias-1", kind=kind)


def test_the_route_is_the_first_named_route_that_is_not_blocked() -> None:
    """expected_behavior_source: the brief, item 1 (d) ("the route is the first named,
    non-blocked one"); AC-3 (a route whose `name` is null names nothing).
    """
    entry = model(
        "m-1",
        route(CLAUDE, "name-blocked", access="blocked"),
        route(CLAUDE, None),
        route(CLAUDE, "name-first", access="confirmed"),
        route(CLAUDE, "name-second"),
    )

    result = resolve(via_profile((entry.id,), models=(entry,)), ask())

    assert result.selected == choice(entry, name="name-first")


def test_the_routes_of_another_client_are_never_used() -> None:
    """expected_behavior_source: AC-3 (`no-route-for-client`); BC-3 ("each file carries its own
    client's name"); the brief, item 1 (d) ("routes of the model whose `client` equals the
    request's client").
    """
    entry = model("m-1", route(CODEX, "name-codex"), route(CLAUDE, "name-claude"))
    for client, expected in ((CLAUDE, "name-claude"), (CODEX, "name-codex")):
        subject = via_profile((entry.id,), models=(entry,), client=client)

        result = resolve(subject, ask(client=client))

        assert result.selected == choice(entry, name=expected)


def test_a_candidate_is_a_catalog_id_and_not_a_string_that_is_matched() -> None:
    """expected_behavior_source: ADR-002 decision 3 (a candidate is a catalog id of the model
    list); the brief, items 1 and 5 (each choice id goes through the constraints; only an
    override or a fallback is a string). It relies on the P-3 reading that an entry's logical
    id is not one of its names.
    """
    entry = model("m-logical", route(CLAUDE, "route-name-1"))

    result = resolve(via_profile((entry.id,), models=(entry,)), ask())

    assert result.selected == choice(entry, name="route-name-1")


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "unusable", [PROPOSED, DISABLED, RETIRED], ids=["proposed", "disabled", "retired"]
)
def test_a_model_that_is_not_approved_is_never_selected_or_listed(
    unusable: ModelInput, mode: Mode
) -> None:
    """expected_behavior_source: AC-3 ("a `proposed`, `disabled` or `retired` model is never
    selected and never listed as a candidate"); BC-10; ADR-004 decision 3; ADR-001 decision 5.
    """
    subject = via_profile(
        (unusable.id, SONNET.id), mode=mode, fallbacks=(unusable.id, HAIKU.id), client=CLAUDE
    )

    result = resolve(subject, ask())

    listed = ids_of((*result.candidates, *result.fallbacks))
    if result.selected is not None:
        listed.append(result.selected.model)
    assert unusable.id not in listed
    assert SONNET.id in ids_of(result.candidates)


def test_the_constraints_are_checked_for_an_assignment_of_one_model_too() -> None:
    """expected_behavior_source: AC-3; ADR-001 decision 5 ("constraints apply at every level");
    the brief, items 5 and 6 (level `assignment`).
    """
    for entry, reason in ((PROPOSED, "not-approved"), (DISABLED, "disabled-or-retired")):
        result = resolve(policy(assignments=(assign_model(entry.id),)), ask())

        assert result.outcome == "none-qualifies"
        assert found(result) == {("assignment", entry.id, reason)}


# --- AC-4: manual mode ---------------------------------------------------


def test_manual_selects_the_first_eligible_candidate_and_reports_the_ones_before_it() -> None:
    """expected_behavior_source: AC-4 ("the first eligible candidate of the client's own ordered
    list is selected"; "the others are not skipped silently"); BC-4; ADR-001 decision 3; the
    brief, item 6 (a valid manual level: the first eligible is selected, the candidates are
    every eligible one in order).
    """
    result = resolve(via_profile((PROPOSED.id, SONNET.id, HAIKU.id)), ask())

    assert (result.outcome, result.source) == ("selected", "profile-assignment")
    assert result.selected == choice(SONNET)
    assert result.candidates == (choice(SONNET), choice(HAIKU))
    assert found(result) == {("candidate", PROPOSED.id, "not-approved")}


def test_manual_follows_the_order_of_the_policy_and_not_the_order_of_the_catalog() -> None:
    """expected_behavior_source: AC-4 ("the client's own ordered list"); ADR-001 decision 3
    ("in the approved order").
    """
    result = resolve(via_profile((HAIKU.id, SONNET.id, OPUS.id)), ask())

    assert result.selected == choice(HAIKU)
    assert ids_of(result.candidates) == [HAIKU.id, SONNET.id, OPUS.id]


def test_manual_reads_only_the_list_of_the_requests_client() -> None:
    """expected_behavior_source: AC-4 ("the client's own ordered list"); BC-3; ADR-001
    decision 3; the brief, item 5 (`candidates` of the profile for the client).
    """
    both = profile("engineering", "automatic", {CLAUDE: (SONNET.id,), CODEX: (TERRA.id, SOL.id)})
    subject = policy(profiles=(both,), assignments=(assign_profile("engineering"),))

    result = resolve(subject, ask(client=CODEX))

    assert result.selected == choice(TERRA)
    assert ids_of(result.candidates) == [TERRA.id, SOL.id]


def test_manual_with_no_eligible_candidate_selects_nothing_and_gives_every_reason() -> None:
    """expected_behavior_source: AC-4 ("nothing is selected, each candidate has its reason in
    `rejected`, and the result is `none-qualifies`"); BC-4; ADR-001 decision 3 ("nothing is
    pinned, the exact reason is reported"); the brief, item 7 (profile, mode and escalation of
    the first team level).
    """
    banned = model("banned-thing", route(CLAUDE, "plain-name"))
    rule = ExclusionRule(aliases=("banned-thing",))
    subject = via_profile(
        (PROPOSED.id, DISABLED.id, RETIRED.id, banned.id),
        models=(PROPOSED, DISABLED, RETIRED, banned),
        exclusions=(rule,),
        escalation="quality",
    )

    result = resolve(subject, ask())

    assert (result.outcome, result.source) == ("none-qualifies", "automatic")
    assert result.selected is None
    assert result.candidates == ()
    assert (result.profile, result.mode, result.escalation) == ("engineering", "manual", "quality")
    assert found(result) == {
        ("candidate", PROPOSED.id, "not-approved"),
        ("candidate", DISABLED.id, "disabled-or-retired"),
        ("candidate", RETIRED.id, "disabled-or-retired"),
        ("candidate", banned.id, "excluded"),
    }
    assert len(result.rejected) == 4


def test_manual_with_no_list_for_the_client_selects_nothing() -> None:
    """expected_behavior_source: AC-4 (none eligible gives `none-qualifies`); BC-4; the brief,
    items 5 to 7 (a manual level is valid only with an eligible candidate, and a client with no
    entry has none).
    """
    subject = via_profile((SONNET.id,), client=CODEX)

    result = resolve(subject, ask(client=CLAUDE))

    assert (result.outcome, result.source, result.selected) == ("none-qualifies", "automatic", None)
    assert result.rejected == ()


def test_a_profile_assignment_for_an_undefined_profile_offers_no_candidate() -> None:
    """expected_behavior_source: the brief, item 5 ("empty when the profile is not defined")
    and items 6 and 7.
    """
    cases: tuple[tuple[Mode, Outcome], ...] = (
        ("manual", "none-qualifies"),
        ("automatic", "client-chooses"),
    )
    for mode, outcome in cases:
        subject = policy(profiles=(), assignments=(assign_profile("quality", mode),))

        result = resolve(subject, ask())

        assert (result.outcome, result.source, result.candidates) == (outcome, "automatic", ())


@pytest.mark.parametrize("name", list(SOURCE_SCENARIOS))
def test_the_same_input_gives_the_same_output_on_every_call(name: str) -> None:
    """expected_behavior_source: AC-4 ("the same input gives the same output on every call and
    on every day"); BC-23; the brief, item 8 (`resolve` is a pure function).
    """
    subject, request_, _ = SOURCE_SCENARIOS[name]
    first = resolve(subject, request_)

    assert [resolve(subject, request_) for _ in range(5)] == [first] * 5


# --- AC-5: reviewer diversity --------------------------------------------

# A reviewer for Cursor, whose models come from three families: the coder's own model, a model
# of the coder's family and a model of another family, offered by `engineering` in that order.
REVIEWER = CODE_REVIEWER_ROLE
CURSOR_REVIEW = policy(assignments=(assign_profile("engineering", name=REVIEWER),))


def test_a_reviewer_candidate_of_the_coders_model_or_family_is_rejected() -> None:
    """expected_behavior_source: AC-5 ("a candidate of the same model is `same-model-as-coder`
    and a candidate of the same family is `same-family-as-coder`"); BC-38; R-7; ADR-007
    decision 11; the brief, item 2.
    """
    result = resolve(CURSOR_REVIEW, ask(REVIEWER, client=CURSOR, coder_model=SONNET.id))

    assert (result.outcome, result.source) == ("selected", "profile-assignment")
    assert result.selected == choice(GEMINI, name="cursor-gemini-argon")
    assert result.candidates == (choice(GEMINI, name="cursor-gemini-argon"),)
    assert found(result) == {
        ("candidate", SONNET.id, "same-model-as-coder"),
        ("candidate", OPUS.id, "same-family-as-coder"),
    }
    assert result.diversity_unproven is False


@pytest.mark.parametrize("mode", ["automatic", "automatic-with-fallbacks"])
def test_diversity_filters_the_candidates_of_a_non_manual_mode_too(mode: Mode) -> None:
    """expected_behavior_source: AC-5 ("in every mode"); BC-38; ADR-007 decision 11; the brief,
    items 2 and 6.
    """
    subject = policy(assignments=(assign_profile("engineering", mode, name=REVIEWER),))

    result = resolve(subject, ask(REVIEWER, client=CURSOR, coder_model=SONNET.id))

    assert (result.outcome, result.source, result.selected) == ("client-chooses", "automatic", None)
    assert result.candidates == (choice(GEMINI, name="cursor-gemini-argon"),)
    assert found(result) == {
        ("candidate", SONNET.id, "same-model-as-coder"),
        ("candidate", OPUS.id, "same-family-as-coder"),
    }


def test_a_fallback_of_the_coders_model_is_rejected_at_the_fallback_level() -> None:
    """expected_behavior_source: AC-5; ADR-007 decision 11; the brief, items 2 and 6 (fallbacks
    go through the same constraints, at level `fallback`).
    """
    subject = via_profile(
        (GEMINI.id,),
        mode="automatic-with-fallbacks",
        fallbacks=(SONNET.id, OPUS.id, GEMINI.id),
        client=CURSOR,
        target=REVIEWER,
    )

    result = resolve(subject, ask(REVIEWER, client=CURSOR, coder_model=SONNET.id))

    assert ids_of(result.fallbacks) == [GEMINI.id]
    assert found(result) == {
        ("fallback", SONNET.id, "same-model-as-coder"),
        ("fallback", OPUS.id, "same-family-as-coder"),
    }


def test_the_coders_own_model_is_the_same_model_and_not_only_the_same_family() -> None:
    """expected_behavior_source: AC-5; the brief, items 1 and 2 (the same model is checked
    before the same family).
    """
    result = resolve(via_profile((SONNET.id,)), ask(coder_model=SONNET.id))

    assert found(result) == {("candidate", SONNET.id, "same-model-as-coder")}


def test_the_coder_is_compared_by_catalog_id_and_family_and_not_through_a_name() -> None:
    """expected_behavior_source: the brief, item 2 ("these compare catalog ids and family
    strings of entries directly, not through `same_identity`"). It relies on the P-3 reading
    that an entry's logical id is not one of its names, so a comparison through `same_identity`
    would find nothing here.
    """
    coder = model("m-coder", route(CLAUDE, "name-of-the-coder"), family="family-x")
    sibling = model("m-sibling", route(CLAUDE, "name-of-the-sibling"), family="family-x")
    other = model("m-other", route(CLAUDE, "name-of-the-other"), family="family-y")
    subject = via_profile(
        (coder.id, sibling.id, other.id), models=(coder, sibling, other), mode="automatic"
    )

    result = resolve(subject, ask(coder_model=coder.id))

    assert ids_of(result.candidates) == [other.id]
    assert found(result) == {
        ("candidate", coder.id, "same-model-as-coder"),
        ("candidate", sibling.id, "same-family-as-coder"),
    }


@pytest.mark.parametrize("effort", EFFORTS)
def test_effort_never_makes_a_candidate_different(effort: Effort) -> None:
    """expected_behavior_source: AC-5 ("effort, speed and context size never make a candidate
    different"); R-7; BC-18; ADR-007 decision 3; the brief, item 2 ("effort never matters").
    """
    same = policy(assignments=(assign_model(SONNET.id, name=REVIEWER, effort=effort),))
    different = policy(assignments=(assign_model(GEMINI.id, name=REVIEWER, effort=effort),))
    asked = ask(REVIEWER, client=CURSOR, coder_model=SONNET.id)

    rejected = resolve(same, asked)
    chosen = resolve(different, asked)

    assert found(rejected) == {("assignment", SONNET.id, "same-model-as-coder")}
    assert rejected.outcome == "none-qualifies"
    assert chosen.selected == choice(GEMINI, name="cursor-gemini-argon", effort=effort)


@pytest.mark.parametrize(
    "spelling",
    [
        "cursor-sonnet[effort=max]",
        "cursor-sonnet[fast]",
        "cursor-sonnet[1m]",
        "cursor-sonnet[effort=low,fast=true,context=1m]",
        "Cursor Sonnet",
        "anthropic/cursor-sonnet",
    ],
)
def test_an_option_list_or_a_prefix_on_an_override_never_makes_it_different(spelling: str) -> None:
    """expected_behavior_source: AC-5 ("effort, speed and context size never make a candidate
    different"); R-7; BC-18; ADR-005 decision 1 and ADR-007 decision 3 (an option list and a
    provider prefix are no difference); the brief, items 2 and 4.
    """
    asked = ask(REVIEWER, client=CURSOR, override=spelling, coder_model=SONNET.id)

    result = resolve(policy(), asked)

    assert result.outcome == "none-qualifies"
    assert found(result) == {("override", SONNET.id, "same-model-as-coder")}


def test_an_override_of_the_coders_family_is_rejected_and_another_family_is_chosen() -> None:
    """expected_behavior_source: AC-5; AC-3 (an override where item 4 says so); BC-38; the
    brief, items 2 and 4.
    """
    asked = ask(REVIEWER, client=CURSOR, coder_model=SONNET.id)

    family = resolve(policy(), dataclasses.replace(asked, override="cursor-opus"))
    other = resolve(policy(), dataclasses.replace(asked, override="cursor-gemini-argon"))

    assert found(family) == {("override", OPUS.id, "same-family-as-coder")}
    assert (other.outcome, other.source) == ("selected", "task-override")
    assert other.selected == choice(GEMINI, name="cursor-gemini-argon")


# The floor of the profile: the reviewer's candidates come from the coder's profile or higher.
ECONOMY_REVIEW = policy(assignments=(assign_profile("economy", name=REVIEWER),))


def test_the_code_reviewer_with_a_coder_model_gets_the_floor_engineering_by_default() -> None:
    """expected_behavior_source: AC-5 ("a candidate from a profile below the coder's profile
    (default `engineering` for the role `orqlet-code-reviewer`) is `outside-profile`"); BC-38;
    ADR-006 decision 7; ADR-007 decision 11; the brief, item 3. The coder runs in Codex, so the
    economy candidate is a different model of a different family.
    """
    result = resolve(ECONOMY_REVIEW, ask(REVIEWER, coder_model=SOL.id))

    assert (result.outcome, result.selected) == ("none-qualifies", None)
    assert found(result) == {("candidate", HAIKU.id, "outside-profile")}
    assert result.diversity_unproven is False


def test_another_role_has_no_floor_unless_it_is_asked_for() -> None:
    """expected_behavior_source: the brief, item 3 ("floor = `request.coder_profile` if given,
    else `DEFAULT_CODER_PROFILE` when the target is the role `CODE_REVIEWER_ROLE` and
    `coder_model` is given, else none"); ADR-006 decision 7.
    """
    subject = policy(assignments=(assign_profile("economy"),))

    result = resolve(subject, ask(coder_model=SOL.id))

    assert result.selected == choice(HAIKU)
    assert result.rejected == ()


@pytest.mark.parametrize(
    ("coder_profile", "chosen", "outside"),
    [
        ("economy", True, set()),
        ("engineering", False, {("candidate", HAIKU.id, "outside-profile")}),
        ("quality", False, {("candidate", HAIKU.id, "outside-profile")}),
    ],
)
def test_an_explicit_coder_profile_sets_the_floor_for_any_role(
    coder_profile: str, chosen: bool, outside: set[tuple[str, str, str]]
) -> None:
    """expected_behavior_source: AC-5; BC-38 ("below `--coder-profile`"); ADR-007 decision 11;
    the brief, item 3 (a floor needs no coder model).
    """
    subject = policy(assignments=(assign_profile("economy"),))

    result = resolve(subject, ask(coder_profile=coder_profile))

    assert (result.selected == choice(HAIKU)) is chosen
    assert found(result) == outside
    assert result.diversity_unproven is False


def test_a_candidate_listed_in_a_higher_profile_passes_the_floor() -> None:
    """expected_behavior_source: AC-5; ADR-006 decision 7 ("a reviewer candidate must come from
    the coder's profile or a higher one"); the brief, item 3 ("listed in `candidates[client]`
    of a profile whose rank ... is the floor's rank or higher").
    """
    mixed = profile("economy", "manual", {CLAUDE: (HAIKU.id, SONNET.id)})
    subject = policy(
        profiles=(QUALITY, ENGINEERING, mixed), assignments=(assign_profile("economy"),)
    )

    result = resolve(subject, ask(coder_profile="engineering"))

    assert result.selected == choice(SONNET)
    assert found(result) == {("candidate", HAIKU.id, "outside-profile")}


def test_the_floor_reads_the_list_of_the_requests_client() -> None:
    """expected_behavior_source: the brief, item 3 (`candidates[client]`)."""
    elsewhere = profile("engineering", "manual", {CODEX: (SONNET.id,)})
    mixed = profile("economy", "manual", {CLAUDE: (SONNET.id,)})
    subject = policy(profiles=(elsewhere, mixed), assignments=(assign_profile("economy"),))

    result = resolve(subject, ask(coder_profile="engineering"))

    assert result.selected is None
    assert found(result) == {("candidate", SONNET.id, "outside-profile")}


def test_a_floor_that_is_no_profile_rejects_every_candidate() -> None:
    """expected_behavior_source: the brief, item 3 ("a floor that is not in `PROFILE_ORDER`
    rejects every candidate as `outside-profile`").
    """
    result = resolve(via_profile((SONNET.id, HAIKU.id)), ask(coder_profile="platinum"))

    assert result.outcome == "none-qualifies"
    assert found(result) == {
        ("candidate", SONNET.id, "outside-profile"),
        ("candidate", HAIKU.id, "outside-profile"),
    }


def test_an_override_below_the_floor_is_outside_the_profile() -> None:
    """expected_behavior_source: AC-3 (an override where item 4 says so); BC-38; ADR-006
    decision 7; the brief, items 3 and 4.
    """
    result = resolve(policy(), ask(REVIEWER, coder_model=SOL.id, override="claude-haiku-5-5"))

    assert result.outcome == "none-qualifies"
    assert found(result) == {("override", HAIKU.id, "outside-profile")}


def test_the_same_model_and_the_same_family_are_reported_before_the_profile() -> None:
    """expected_behavior_source: the brief, item 1 (the order: same-model-as-coder,
    same-family-as-coder, outside-profile).
    """
    same_model = resolve(ECONOMY_REVIEW, ask(REVIEWER, coder_model=HAIKU.id))
    same_family = resolve(ECONOMY_REVIEW, ask(REVIEWER, coder_model=SONNET.id))

    assert found(same_model) == {("candidate", HAIKU.id, "same-model-as-coder")}
    assert found(same_family) == {("candidate", HAIKU.id, "same-family-as-coder")}


@pytest.mark.parametrize("mode", MODES)
def test_a_coder_model_that_the_catalog_does_not_know_shows_no_candidate_different(
    mode: Mode,
) -> None:
    """expected_behavior_source: AC-5 ("when no candidate can be shown different the result is
    `none-qualifies` in every mode"); BC-38; ADR-007 decisions 1 and 11; the brief, item 2 (the
    candidates that pass the other constraints are dropped with no rejection, and
    `diversity_unproven` is set).
    """
    result = resolve(via_profile((SONNET.id, HAIKU.id), mode=mode), ask(coder_model="m-unknown"))

    assert (result.outcome, result.source, result.selected) == ("none-qualifies", "automatic", None)
    assert result.candidates == ()
    assert result.rejected == ()
    assert result.diversity_unproven is True


@pytest.mark.parametrize("mode", MODES)
def test_a_proposed_coder_entry_shows_no_candidate_different(mode: Mode) -> None:
    """expected_behavior_source: AC-5; BC-10 (a `proposed` entry never contributes to identity
    or family); ADR-007 decision 1; the brief, item 2 ("the first model ... whose approval is
    not `proposed`").
    """
    result = resolve(via_profile((SONNET.id,), mode=mode), ask(coder_model=PROPOSED.id))

    assert (result.outcome, result.selected) == ("none-qualifies", None)
    assert result.rejected == ()
    assert result.diversity_unproven is True


def test_a_candidate_failing_another_constraint_keeps_its_reason_if_the_coder_is_unknown() -> None:
    """expected_behavior_source: the brief, item 2 ("every candidate that passes the other
    constraints is dropped with no rejection"); items 1 and 6.
    """
    result = resolve(via_profile((PROPOSED.id, SONNET.id)), ask(coder_model="m-unknown"))

    assert found(result) == {("candidate", PROPOSED.id, "not-approved")}
    assert len(result.rejected) == 1
    assert result.diversity_unproven is True


def test_the_fallbacks_are_dropped_too_when_the_coder_is_unknown() -> None:
    """expected_behavior_source: the brief, items 2 and 6 (fallbacks go through the same
    constraints as candidates).
    """
    subject = via_profile(
        (SONNET.id,), mode="automatic-with-fallbacks", fallbacks=(OPUS.id,), target=REVIEWER
    )

    result = resolve(subject, ask(REVIEWER, coder_model="m-unknown"))

    assert result.outcome == "none-qualifies"
    assert result.fallbacks == ()
    assert result.diversity_unproven is True


@pytest.mark.parametrize("approval", ["disabled", "retired"])
def test_a_disabled_or_retired_coder_entry_still_gives_its_family(approval: ApprovalState) -> None:
    """expected_behavior_source: BC-10 (only a `proposed` entry is left out of family
    derivation); ADR-007 decision 1 (entries whose state is not `proposed`); the brief, item 2.
    """
    coder = model("m-coder", route(CLAUDE, "name-coder"), approval=approval)

    result = resolve(
        via_profile((SONNET.id,), mode="automatic", models=(coder, SONNET)),
        ask(coder_model=coder.id),
    )

    assert found(result) == {("candidate", SONNET.id, "same-family-as-coder")}
    assert result.diversity_unproven is False


@pytest.mark.parametrize("mode", MODES)
def test_with_no_candidate_for_the_client_a_coder_model_leaves_nothing_that_qualifies(
    mode: Mode,
) -> None:
    """expected_behavior_source: AC-5 ("and also when the policy has no entry for the client");
    BC-38 ("exits 1 in every mode, with or without a policy"); the brief, item 7.
    """
    subject = via_profile((SONNET.id,), mode=mode, client=CODEX, target=REVIEWER)

    result = resolve(subject, ask(REVIEWER, client=CLAUDE, coder_model=SONNET.id))

    assert (result.outcome, result.source, result.selected) == ("none-qualifies", "automatic", None)
    assert result.diversity_unproven is False


@pytest.mark.parametrize(
    ("subject", "coder_model", "unproven"),
    [
        (ResolverPolicy(), SONNET.id, True),
        (ResolverPolicy(), "m-unknown", True),
        (policy(), SONNET.id, False),
        (policy(), "m-unknown", True),
    ],
    ids=["no-policy-known-id", "no-policy-unknown-id", "a-policy-known-id", "a-policy-unknown-id"],
)
def test_with_no_level_at_all_a_coder_model_leaves_nothing_that_qualifies(
    subject: ResolverPolicy, coder_model: str, unproven: bool
) -> None:
    """expected_behavior_source: AC-5; BC-38 ("with or without a policy"); the brief, item 7
    ("if no level was present at all but the request is constrained, also `none-qualifies`")
    and item 2 (the flag is set when the catalog has no non-proposed entry for the coder: an
    empty policy has none).
    """
    result = resolve(subject, ask(REVIEWER, coder_model=coder_model))

    assert (result.outcome, result.source, result.selected) == ("none-qualifies", "automatic", None)
    assert result.candidates == ()
    assert result.diversity_unproven is unproven


def test_a_floor_alone_leaves_nothing_that_qualifies_when_no_level_is_present() -> None:
    """expected_behavior_source: the brief, items 3 and 7 (a floor makes the request
    constrained); BC-38.
    """
    result = resolve(ResolverPolicy(), ask(coder_profile="engineering"))

    assert (result.outcome, result.source) == ("none-qualifies", "automatic")


def test_without_a_coder_model_or_a_floor_the_client_chooses_in_every_mode() -> None:
    """expected_behavior_source: BC-38 and F-15 (without `--different-family-from` nothing is
    constrained, so with no policy file "the client chooses"); the brief, items 6 and 7.
    """
    non_manual: tuple[Mode, ...] = ("automatic", "automatic-with-fallbacks")

    assert resolve(ResolverPolicy(), ask()).outcome == "client-chooses"
    for mode in non_manual:
        subject = via_profile((SONNET.id,), mode=mode, client=CODEX)

        assert resolve(subject, ask()).outcome == "client-chooses"


def test_a_known_coder_leaves_the_flag_unset() -> None:
    """expected_behavior_source: the brief, items 2 and 7 (`diversity_unproven` is set only in
    the no-coder-entry case)."""
    unconstrained = resolve(via_profile((SONNET.id,)), ask())
    known = resolve(via_profile((HAIKU.id,)), ask(coder_model=SOL.id))

    assert unconstrained.diversity_unproven is False
    assert known.diversity_unproven is False
    assert known.selected == choice(HAIKU)


# --- AC-6 and the levels: which assignment applies -----------------------


@pytest.mark.parametrize(("task", "applies"), [(None, False), ("task-2", False), ("task-1", True)])
@pytest.mark.parametrize("by", ["model", "profile"])
def test_an_assignment_that_names_a_task_applies_only_when_the_caller_passes_it(
    by: str, task: str | None, applies: bool
) -> None:
    """expected_behavior_source: AC-6 ("an assignment that names a `task` applies only when the
    caller passes that task"); BC-43; ADR-001 decision 7 ("task scope is a resolve-time
    selector only"); the brief, item 5.
    """
    if by == "model":
        assignment = assign_model(SONNET.id, task="task-1")
        source = "role-assignment"
    else:
        assignment = assign_profile("economy", task="task-1")
        source = "profile-assignment"

    result = resolve(policy(assignments=(assignment,)), ask(task=task))

    if applies:
        assert (result.outcome, result.source) == ("selected", source)
    else:
        assert result == Resolution(outcome="client-chooses", source="automatic")


def test_an_assignment_for_the_task_wins_over_one_for_every_task() -> None:
    """expected_behavior_source: AC-6; ADR-001 decision 7; the brief, item 5 ("a set task before
    an unset one").
    """
    subject = policy(assignments=(assign_model(HAIKU.id), assign_model(SONNET.id, task="task-1")))

    with_task = resolve(subject, ask(task="task-1"))
    other_task = resolve(subject, ask(task="task-2"))
    no_task = resolve(subject, ask())

    assert with_task.selected == choice(SONNET)
    assert other_task.selected == choice(HAIKU)
    assert no_task.selected == choice(HAIKU)


def test_a_task_outranks_a_client_and_a_client_outranks_none_and_then_the_order_decides() -> None:
    """expected_behavior_source: the brief, item 5 ("the most specific one: a set task before an
    unset one, then a set client before an unset one, then the order in the policy").
    """
    by_client = assign_model(SONNET.id, client=CLAUDE)
    by_task = assign_model(OPUS.id, task="task-1")
    plain = assign_model(HAIKU.id)
    plain_later = assign_model(GEMINI.id)

    client_first = resolve(policy(assignments=(plain, by_client)), ask())
    task_first = resolve(policy(assignments=(by_client, by_task)), ask(task="task-1"))
    order = resolve(policy(assignments=(plain, plain_later)), ask())

    assert client_first.selected == choice(SONNET)
    assert task_first.selected == choice(OPUS)
    assert order.selected == choice(HAIKU)


def test_an_assignment_for_another_client_does_not_apply() -> None:
    """expected_behavior_source: ADR-001 decision 4 (level 2: "for the client"); the brief,
    item 5 (`client` is `None` or equals the request's).
    """
    subject = policy(assignments=(assign_model(SONNET.id, client=CODEX),))

    assert resolve(subject, ask(client=CLAUDE)) == Resolution(
        outcome="client-chooses", source="automatic"
    )


def test_a_role_assignment_and_a_skill_assignment_apply_only_to_their_own_kind() -> None:
    """expected_behavior_source: ADR-001 decision 4 ("a team assignment for the role or
    skill"); the brief, item 5 ("the request's kind (role or skill) and name"); a skill
    assignment has the source `role-assignment` (ADR-001 decision 6).
    """
    subject = policy(
        assignments=(
            assign_model(SONNET.id, name="same-name", kind="role"),
            assign_model(HAIKU.id, name="same-name", kind="skill"),
        )
    )

    as_role = resolve(subject, ask("same-name", kind="role"))
    as_skill = resolve(subject, ask("same-name", kind="skill"))

    assert (as_role.source, as_role.selected) == ("role-assignment", choice(SONNET))
    assert (as_skill.source, as_skill.selected) == ("role-assignment", choice(HAIKU))


def test_the_mode_and_the_effort_of_the_assignment_are_those_of_the_result() -> None:
    """expected_behavior_source: ADR-001 decision 3 (modes are "per assignment or profile");
    ADR-002 decision 3 (`effort` of an assignment); the brief, item 5 ("mode and effort from the
    assignment").
    """
    by_model = resolve(policy(assignments=(assign_model(SONNET.id, effort="xhigh"),)), ask())
    by_profile = resolve(via_profile((SONNET.id,), effort="low"), ask())

    assert by_model.selected == choice(SONNET, effort="xhigh")
    assert by_profile.selected == choice(SONNET, effort="low")
    assert by_profile.candidates == (choice(SONNET, effort="low"),)
    assert (by_model.mode, by_profile.mode) == ("manual", "manual")


def test_the_fallbacks_of_a_profile_are_listed_only_in_the_mode_with_fallbacks() -> None:
    """expected_behavior_source: ADR-001 decision 3; the brief, item 5 ("fallbacks ... only
    when the assignment's mode is `automatic-with-fallbacks`").
    """
    cases: tuple[tuple[Mode, bool], ...] = (
        ("manual", False),
        ("automatic", False),
        ("automatic-with-fallbacks", True),
    )
    for mode, listed in cases:
        result = resolve(via_profile((SONNET.id,), mode=mode, fallbacks=(OPUS.id,)), ask())

        assert bool(result.fallbacks) is listed


def test_a_profile_request_resolves_the_profile_with_its_own_mode_and_no_effort() -> None:
    """expected_behavior_source: ADR-001 decision 8 (`models resolve --profile`); BC-35; the
    brief, item 5 ("for a `profile` request, the profile named by `target` with its own mode
    and no effort").
    """
    manual = resolve(policy(), ask("engineering", kind="profile"))
    automatic_profile = profile("engineering", "automatic", {CLAUDE: (SONNET.id, HAIKU.id)})
    automatic = resolve(policy(profiles=(automatic_profile,)), ask("engineering", kind="profile"))

    assert (manual.outcome, manual.source) == ("selected", "profile-assignment")
    assert manual.selected == choice(SONNET)
    assert (manual.profile, manual.mode, manual.escalation) == ("engineering", "manual", "quality")
    assert (automatic.outcome, automatic.source) == ("client-chooses", "automatic")
    assert automatic.mode == "automatic"
    assert ids_of(automatic.candidates) == [SONNET.id, HAIKU.id]


def test_an_override_applies_to_a_profile_request_too() -> None:
    """expected_behavior_source: ADR-001 decision 4 (level 1 applies to every request); the
    brief, item 5 (L1 is `override` when it is not `None`).
    """
    result = resolve(policy(), ask("engineering", kind="profile", override="claude-opus-5-5"))

    assert (result.outcome, result.source) == ("selected", "task-override")
    assert result.selected == choice(OPUS)


# --- the helpers of the module -------------------------------------------

EXCLUDES_BY: dict[str, ExclusionRule] = {
    "alias": ExclusionRule(aliases=("banned-thing",)),
    "id-pattern": ExclusionRule(id_patterns=("banned-*",)),
    "family-tag": ExclusionRule(family_tags=("bannedfam",)),
}


@pytest.mark.parametrize("approval", APPROVALS)
@pytest.mark.parametrize(
    ("entry", "rule"),
    [
        (model("banned-thing", route(CLAUDE, "plain-1")), "alias"),
        (model("banned-2", route(CLAUDE, "plain-2")), "id-pattern"),
        (model("m-3", route(CLAUDE, "plain-3"), family="BannedFam-1"), "family-tag"),
        (model("m-4", route(CLAUDE, "Banned Thing")), "alias"),
        (model("m-5", route(CLAUDE, "plain-5", kind="alias", resolves_to="banned-thing")), "alias"),
        (model("m-6", route(CLAUDE, "plain-6", also_known_as=("banned-thing",))), "alias"),
        (model("m-7", route(CLAUDE, None, also_known_as=("banned-7",))), "id-pattern"),
        (model("m-8", route(CODEX, "banned-8"), route(CLAUDE, "plain-8")), "id-pattern"),
    ],
    ids=[
        "id",
        "id-by-pattern",
        "family",
        "route-name",
        "resolves-to",
        "also-known-as",
        "also-known-as-of-an-unnamed-route",
        "route-of-another-client",
    ],
)
def test_is_model_excluded_reads_the_id_the_family_and_every_route_string(
    entry: ModelInput, rule: str, approval: ApprovalState
) -> None:
    """expected_behavior_source: AC-3; BC-9; ADR-005 decision 2 ("an exclusion applies to
    entries in every state"); the brief (`is_model_excluded`: true when `is_excluded` matches
    the model's id, its family or any route name, `resolves_to` or `also_known_as`, in any
    approval state, whatever the client of the route).
    """
    changed = dataclasses.replace(entry, approval=approval)

    assert is_model_excluded(changed, (EXCLUDES_BY[rule],)) is True


@pytest.mark.parametrize("entry", CATALOG, ids=[entry.id for entry in CATALOG])
def test_is_model_excluded_is_false_for_a_model_that_no_rule_matches(entry: ModelInput) -> None:
    """expected_behavior_source: ADR-005 decision 1 (an exclusion is data and matches only what
    it lists); the brief (`is_model_excluded`).
    """
    assert is_model_excluded(entry, tuple(EXCLUDES_BY.values())) is False
    assert is_model_excluded(entry, ()) is False
    assert is_model_excluded(entry, [ExclusionRule()]) is False


def test_catalog_entries_are_the_p_3_entries_with_the_routes_of_every_client_in_order() -> None:
    """expected_behavior_source: the brief (`catalog_entries`: the P-3 entries, routes of all
    clients, in the same order); ADR-005 decision 1 (the one matching rule).
    """
    first = model(
        "m-1",
        route(CLAUDE, "name-1", also_known_as=("spelling-a", "spelling-b")),
        route(CODEX, None, kind="alias", resolves_to="name-1", access="blocked"),
        family="family-1",
        approval="proposed",
    )

    entries = catalog_entries((first, SONNET))

    assert entries == (
        CatalogEntry(
            id="m-1",
            family="family-1",
            approval="proposed",
            routes=(
                CatalogRoute(name="name-1", also_known_as=("spelling-a", "spelling-b")),
                CatalogRoute(name=None, resolves_to="name-1", also_known_as=()),
            ),
        ),
        CatalogEntry(
            id="claude-sonnet-5-5",
            family="anthropic",
            approval="approved",
            routes=(
                CatalogRoute(name="claude-sonnet-5-5"),
                CatalogRoute(name="cursor-sonnet"),
            ),
        ),
    )


def test_catalog_entries_of_nothing_are_nothing_and_a_list_works_as_well_as_a_tuple() -> None:
    """expected_behavior_source: the brief (`catalog_entries(models: Sequence[ModelInput])`
    returns a tuple).
    """
    assert catalog_entries(()) == ()
    assert catalog_entries([OPUS]) == catalog_entries((OPUS,))
    assert isinstance(catalog_entries([OPUS]), tuple)


@pytest.mark.parametrize("entry", CATALOG, ids=[entry.id for entry in CATALOG])
def test_every_route_name_matches_its_own_entry_through_the_p_3_rule(entry: ModelInput) -> None:
    """expected_behavior_source: the brief (`catalog_entries` feeds `match_entry`); ADR-005
    decision 1 (a string names a model only through the catalog).
    """
    entries = catalog_entries(CATALOG)

    for item in entry.routes:
        matched = match_entry(item.name or "", entries, skip_proposed=False)

        assert matched is not None
        assert matched.id == entry.id


# --- properties over small generated policies ----------------------------

BANNED_FAMILY = "bannedfam"
GHOST = "m-ghost"


@st.composite
def small_catalogs(draw: st.DrawFn) -> tuple[ModelInput, ...]:
    """One to four models: any approval state, a Claude Code route or none, a name or none."""
    entries: list[ModelInput] = []
    for index in range(draw(st.integers(min_value=1, max_value=4))):
        has_route = draw(st.booleans())
        name = draw(st.sampled_from((None, f"name-{index}")))
        access = draw(st.sampled_from(ACCESS_VALUES))
        routes = (route(CLAUDE, name, access=access),) if has_route else ()
        entries.append(
            model(
                f"m-{index}",
                *routes,
                family=draw(st.sampled_from(("fam-a", "fam-b", BANNED_FAMILY))),
                approval=draw(st.sampled_from(APPROVALS)),
            )
        )
    return tuple(entries)


@st.composite
def scenarios(draw: st.DrawFn) -> tuple[ResolverPolicy, ResolveRequest]:
    """A catalog, two profiles, up to two assignments for one role, and a request."""
    catalog = draw(small_catalogs())
    ids = [entry.id for entry in catalog] + [GHOST]
    lists = st.lists(st.sampled_from(ids), max_size=4).map(tuple)
    engineering = profile(
        "engineering",
        draw(st.sampled_from(MODES)),
        {CLAUDE: draw(lists)},
        {CLAUDE: draw(lists)},
    )
    economy = profile("economy", draw(st.sampled_from(MODES)), {CLAUDE: draw(lists)})
    target = draw(st.sampled_from((ROLE, CODE_REVIEWER_ROLE)))
    assignments: list[AssignmentInput] = []
    if draw(st.booleans()):
        assignments.append(
            assign_profile(
                draw(st.sampled_from(("engineering", "economy"))),
                draw(st.sampled_from(MODES)),
                name=target,
            )
        )
    if draw(st.booleans()):
        assignments.append(
            assign_model(draw(st.sampled_from(ids)), draw(st.sampled_from(MODES)), name=target)
        )
    subject = policy(
        models=catalog,
        exclusions=(ExclusionRule(family_tags=(BANNED_FAMILY,)),),
        profiles=(engineering, economy),
        assignments=assignments,
    )
    request_ = ask(
        target,
        override=draw(st.sampled_from((None, "name-0", "name-1", "no-such-model"))),
        fallback=draw(st.sampled_from((None, "name-0", "no-such-model"))),
        coder_model=draw(st.sampled_from((None, *ids))),
        coder_profile=draw(st.sampled_from((None, "engineering", "economy", "platinum"))),
    )
    return subject, request_


def assert_the_invariants(
    subject: ResolverPolicy, asked: ResolveRequest, result: Resolution
) -> None:
    """What every result must satisfy, whatever the policy."""
    by_id = {entry.id: entry for entry in subject.models}
    picks = [*result.candidates, *result.fallbacks]
    if result.selected is not None:
        picks.append(result.selected)
    assert result.source in SOURCES
    assert (result.selected is not None) == (result.outcome == "selected")
    if result.outcome == "none-qualifies":
        assert not picks
    for pick in picks:
        entry = by_id[pick.model]
        assert entry.approval == "approved"
        assert not is_model_excluded(entry, subject.exclusions)
        wanted = next(
            item
            for item in entry.routes
            if item.client == asked.client and item.name is not None and item.access != "blocked"
        )
        assert (pick.name, pick.kind) == (wanted.name, wanted.kind)
    for rejection in result.rejected:
        assert rejection.reason in REJECTION_REASONS
        assert rejection.level in literal_values(Level)
        assert rejection.model is None or rejection.model in {*by_id, GHOST}

    coder = next(
        (
            entry
            for entry in subject.models
            if entry.id == asked.coder_model and entry.approval != "proposed"
        ),
        None,
    )
    assert result.diversity_unproven == (asked.coder_model is not None and coder is None)
    if coder is not None:
        for pick in picks:
            assert pick.model != coder.id
            assert by_id[pick.model].family != coder.family
    elif asked.coder_model is not None:
        assert not picks

    floor = asked.coder_profile
    if floor is None and asked.target == CODE_REVIEWER_ROLE and asked.coder_model is not None:
        floor = DEFAULT_CODER_PROFILE
    if floor is not None:
        allowed = [
            item
            for item in subject.profiles
            if floor in PROFILE_ORDER and PROFILE_ORDER.index(item.id) <= PROFILE_ORDER.index(floor)
        ]
        for pick in picks:
            assert any(pick.model in item.candidates.get(asked.client, ()) for item in allowed)
    if (asked.coder_model is not None or floor is not None) and result.outcome == "client-chooses":
        assert result.candidates


@given(scenarios())
def test_no_generated_result_breaks_an_invariant(
    scenario: tuple[ResolverPolicy, ResolveRequest],
) -> None:
    """expected_behavior_source: AC-2 and AC-3 (the closed sets; a model that is not approved or
    that is excluded is never selected or listed); AC-5 (diversity and the floor, none-qualifies
    when none can be shown different, in every mode); BC-10; BC-38; the brief, items 1 to 3, 6
    and 7.
    """
    subject, asked = scenario

    assert_the_invariants(subject, asked, resolve(subject, asked))


@given(scenarios())
def test_the_same_generated_input_gives_the_same_result(
    scenario: tuple[ResolverPolicy, ResolveRequest],
) -> None:
    """expected_behavior_source: AC-4 ("the same input gives the same output on every call");
    BC-23; the brief, item 8.
    """
    subject, asked = scenario

    assert resolve(subject, asked) == resolve(subject, asked)


# --- AC-8: the import check ----------------------------------------------

DOMAIN = "orqlet.domain"
CLOCK_LOCALE_ENVIRONMENT = {"datetime", "locale", "os", "random", "time"}
FORBIDDEN_NAMES = {"__import__", "eval", "exec", "open"}


def imported_modules(source: str) -> set[str]:
    """The absolute names of the modules that a source in `orqlet.domain` imports, anywhere."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(resolve_name("." * node.level + (node.module or ""), DOMAIN))
    return modules


def in_the_domain(module: str) -> bool:
    return module == DOMAIN or module.startswith(DOMAIN + ".")


def outside_the_brief(modules: set[str]) -> set[str]:
    """The modules that are neither in the standard library nor in the domain."""
    return {
        module
        for module in modules
        if module.split(".")[0] not in sys.stdlib_module_names and not in_the_domain(module)
    }


def used_names(source: str) -> set[str]:
    return {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}


def test_the_module_imports_only_the_standard_library_and_the_domain() -> None:
    """expected_behavior_source: AC-8 ("the domain module imports nothing outside the standard
    library and the domain"); C-1; ORQLET-ARCH-001; ORQLET-ARCH-002; the brief (the module is
    pure: standard library and `orqlet.domain` only).
    """
    assert outside_the_brief(imported_modules(inspect.getsource(model_resolution))) == set()


def test_the_module_imports_no_clock_locale_or_environment_module() -> None:
    """expected_behavior_source: AC-1 ("no clock"); AC-4 ("on every day"); BC-23 ("reads no
    clock"); ADR-001 decision 5 (selection never depends on today's date); the brief, item 8
    ("it reads no clock, environment, file or network").
    """
    imported = imported_modules(inspect.getsource(model_resolution))

    assert {module.split(".")[0] for module in imported} & CLOCK_LOCALE_ENVIRONMENT == set()


def test_the_module_reaches_for_no_dynamic_import_and_no_file() -> None:
    """expected_behavior_source: AC-8; BC-23; the brief, item 8."""
    assert used_names(inspect.getsource(model_resolution)) & FORBIDDEN_NAMES == set()


def test_the_import_check_finds_what_it_must_refuse() -> None:
    """expected_behavior_source: AC-8 (the failing and the passing case of the checks above)."""
    source = (
        "import os\nfrom time import monotonic\nimport locale\nfrom datetime import date\n"
        "from pydantic import BaseModel\nfrom .. import application\nfrom . import names\n"
        "from .names import plain\nimport dataclasses\n\ndef f() -> None:\n    open('x')\n"
    )
    modules = imported_modules(source)

    assert outside_the_brief(modules) == {"orqlet", "pydantic"}
    assert {module.split(".")[0] for module in modules} & CLOCK_LOCALE_ENVIRONMENT == {
        "datetime",
        "locale",
        "os",
        "time",
    }
    assert {"orqlet.domain", "orqlet.domain.names", "dataclasses"} <= modules
    assert used_names(source) & FORBIDDEN_NAMES == {"open"}
