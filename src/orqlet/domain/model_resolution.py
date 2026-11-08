"""Which model a client gets: precedence, constraints and reasons (ADR-001, ADR-006, ADR-007).

`resolve` is a pure function on plain values. It reads no clock, environment, file or network, so
the same policy and request give an equal `Resolution` on every call and on every day. A route's
`retires_on` is never an input: the application layer reports that date as a warning.

Precedence, highest first (ADR-001 decision 4):

1. an override that the caller names;
2. the assignment of the role or skill that names one model;
3. the assignment that names a profile (or, for a profile request, the profile itself);
4. the client's own automatic choice.

A level is used when it is valid. In mode `manual` a level is valid when one of its choices is
eligible. In the other modes it is valid always, unless the request is constrained (a coder model
or a profile floor was asked for): then it needs an eligible choice, so that no mode can drift to a
model that cannot be shown to qualify. An invalid level keeps its rejections and the next level is
tried, so a higher choice is never replaced without a visible entry. When no level is valid and
one was present, nothing qualifies.

Identity goes through the matching rule of `model_identity`, with two limits that follow from it.
A candidate is a catalog id and is compared by id and family directly, because a logical id is not
one of an entry's names. An override or a named fallback is a string and is matched by name, so a
string that equals only a logical id, or that two entries name, matches nothing.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal, get_args

from orqlet.domain.model_identity import (
    ApprovalState,
    CatalogEntry,
    CatalogRoute,
    ExclusionRule,
    is_excluded,
    match_entry,
)

Mode = Literal["automatic", "manual", "automatic-with-fallbacks"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]
RouteKind = Literal["id", "alias"]
Access = Literal["unknown", "confirmed", "blocked"]
Outcome = Literal["selected", "client-chooses", "none-qualifies"]
# Where a rejection arose: the override, an assignment that names one model, a profile's list, or
# a fallback.
Level = Literal["override", "assignment", "candidate", "fallback"]
Source = Literal[
    "task-override", "role-assignment", "profile-assignment", "automatic", "explicit-fallback"
]
# A closed set (AC-3). The order is the one of the criterion, not the order of the checks.
Reason = Literal[
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
]

SOURCES: tuple[Source, ...] = get_args(Source)
REJECTION_REASONS: tuple[Reason, ...] = get_args(Reason)

# Highest first: a candidate must come from the coder's profile or a higher one (ADR-006).
PROFILE_ORDER: tuple[str, ...] = ("quality", "engineering", "economy")
CODE_REVIEWER_ROLE = "orqlet-code-reviewer"
DEFAULT_CODER_PROFILE = "engineering"


@dataclass(frozen=True, slots=True)
class RouteInput:
    """One way a client names a model."""

    client: str
    kind: RouteKind
    name: str | None
    access: Access = "unknown"
    resolves_to: str | None = None
    also_known_as: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelInput:
    """A catalog model."""

    id: str
    family: str
    approval: ApprovalState
    routes: tuple[RouteInput, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfileInput:
    """A profile: ordered catalog ids per client, as candidates and as fallbacks."""

    id: str
    mode: Mode
    candidates: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    fallbacks: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    escalation: str | None = None


@dataclass(frozen=True, slots=True)
class AssignmentInput:
    """A team assignment of a role or skill to one catalog model or to a profile."""

    kind: Literal["role", "skill"]
    name: str
    mode: Mode
    model: str | None = None
    profile: str | None = None
    task: str | None = None
    client: str | None = None
    effort: Effort | None = None


@dataclass(frozen=True, slots=True)
class ResolverPolicy:
    models: tuple[ModelInput, ...] = ()
    exclusions: tuple[ExclusionRule, ...] = ()
    profiles: tuple[ProfileInput, ...] = ()
    assignments: tuple[AssignmentInput, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolveRequest:
    """What is asked. `override` and `fallback` are model strings, `coder_model` a catalog id."""

    client: str
    target_kind: Literal["role", "skill", "profile"]
    target: str
    task: str | None = None
    override: str | None = None
    fallback: str | None = None
    coder_model: str | None = None
    coder_profile: str | None = None


@dataclass(frozen=True, slots=True)
class Choice:
    """A model that can be used: its catalog id and the client's exact route name."""

    model: str
    name: str
    kind: RouteKind
    effort: Effort | None = None


@dataclass(frozen=True, slots=True)
class Rejection:
    """Why a choice was refused. `model` is the catalog id, never the string a caller gave."""

    level: Level
    model: str | None
    reason: Reason


@dataclass(frozen=True, slots=True)
class Resolution:
    outcome: Outcome
    source: Source
    selected: Choice | None = None
    profile: str | None = None
    mode: Mode | None = None
    candidates: tuple[Choice, ...] = ()
    fallbacks: tuple[Choice, ...] = ()
    rejected: tuple[Rejection, ...] = ()
    escalation: str | None = None
    # The coder's model is not a known, non-proposed entry, so no candidate can be shown different.
    diversity_unproven: bool = False


def catalog_entries(models: Sequence[ModelInput]) -> tuple[CatalogEntry, ...]:
    """The entries of `model_identity` for these models: the routes of every client, in order."""
    return tuple(
        CatalogEntry(
            id=model.id,
            family=model.family,
            approval=model.approval,
            routes=tuple(
                CatalogRoute(
                    name=route.name,
                    resolves_to=route.resolves_to,
                    also_known_as=route.also_known_as,
                )
                for route in model.routes
            ),
        )
        for model in models
    )


def is_model_excluded(model: ModelInput, exclusions: Sequence[ExclusionRule]) -> bool:
    """True when an exclusion matches the model's id, its family or any string of its routes.

    Every approval state counts and every client's route counts: one hit anywhere excludes the
    model, because the exclusion leans towards refusing (ADR-005).
    """
    rules = tuple(exclusions)
    return any(is_excluded(text, rules) for text in _strings_of(model))


def resolve(policy: ResolverPolicy, request: ResolveRequest) -> Resolution:
    """The selection for `request` under `policy`, with every rejected choice and its reason."""
    return _Resolver(policy, request).resolve()


def _strings_of(model: ModelInput) -> Iterator[str]:
    yield model.id
    yield model.family
    for route in model.routes:
        for text in (route.name, route.resolves_to, *route.also_known_as):
            if text is not None:
                yield text


@dataclass(frozen=True, slots=True)
class _Level:
    """One precedence level that is present: the ids it offers and how it is to be used."""

    source: Source
    rejection_level: Level
    choices: tuple[str, ...]
    fallbacks: tuple[str, ...]
    mode: Mode
    effort: Effort | None
    profile: str | None = None
    escalation: str | None = None


@dataclass(frozen=True, slots=True)
class _Evaluated:
    eligible: tuple[Choice, ...]
    fallbacks: tuple[Choice, ...]
    rejected: tuple[Rejection, ...]


@dataclass(frozen=True, slots=True)
class _Verdict:
    """What the constraints say about one model: a route to use, a reason, or neither.

    Neither means that the model passed every constraint, but the coder is unknown and so nothing
    can be shown different. No reason of the closed set would be true for it.
    """

    choice: Choice | None = None
    reason: Reason | None = None


class _Resolver:
    def __init__(self, policy: ResolverPolicy, request: ResolveRequest) -> None:
        self._policy = policy
        self._request = request
        self._rules = tuple(policy.exclusions)
        self._catalog = catalog_entries(policy.models)
        self._models: dict[str, ModelInput] = {}
        for model in policy.models:
            self._models.setdefault(model.id, model)
        self._floor = _floor_of(request)
        coder = None if request.coder_model is None else self._models.get(request.coder_model)
        # A proposed entry gives no family (BC-10), so it cannot stand for the coder.
        self._coder = coder if coder is not None and coder.approval != "proposed" else None
        self._unproven = request.coder_model is not None and self._coder is None
        self._constrained = request.coder_model is not None or self._floor is not None

    def resolve(self) -> Resolution:
        rejected: list[Rejection] = []
        present = False
        first: _Level | None = None
        if self._request.override is not None:
            outcome = self._judge_text(self._request.override, "override", None, None)
            if isinstance(outcome, Choice):
                return Resolution("selected", "task-override", selected=outcome)
            if outcome is not None:
                rejected.append(outcome)
            present = True
        for level in self._team_levels():
            if first is None:
                first = level
            present = True
            evaluated = self._evaluate(level)
            if self._is_valid(level, evaluated):
                return self._used(level, evaluated, rejected)
            rejected.extend(evaluated.rejected)
        if present or self._constrained:
            return self._nothing_qualifies(first, rejected)
        return Resolution("client-chooses", "automatic")

    def _nothing_qualifies(self, first: _Level | None, rejected: list[Rejection]) -> Resolution:
        """No level could be used. The profile and mode shown are those of the first level tried."""
        return Resolution(
            "none-qualifies",
            "automatic",
            profile=None if first is None else first.profile,
            mode=None if first is None else first.mode,
            rejected=tuple(rejected),
            escalation=None if first is None else first.escalation,
            diversity_unproven=self._unproven,
        )

    # --- levels ---------------------------------------------------------------------------

    def _team_levels(self) -> Iterator[_Level]:
        request = self._request
        if request.target_kind == "profile":
            profile = self._profile(request.target)
            if profile is not None:
                yield self._profile_level(profile, profile.mode, None)
            return
        applicable = self._applicable_assignments()
        for level in (self._pinned_level(applicable), self._named_profile_level(applicable)):
            if level is not None:
                yield level

    def _pinned_level(self, applicable: Sequence[AssignmentInput]) -> _Level | None:
        """Level 2: the assignment that names one model."""
        for assignment in applicable:
            if assignment.model is not None:
                return _Level(
                    "role-assignment",
                    "assignment",
                    (assignment.model,),
                    (),
                    assignment.mode,
                    assignment.effort,
                )
        return None

    def _named_profile_level(self, applicable: Sequence[AssignmentInput]) -> _Level | None:
        """Level 3: the assignment that names a profile, and so that profile's own list."""
        for assignment in applicable:
            if assignment.profile is None:
                continue
            profile = self._profile(assignment.profile)
            if profile is None:
                # A profile that the policy does not define offers nothing; the policy check
                # reports the name.
                return _Level(
                    "profile-assignment",
                    "candidate",
                    (),
                    (),
                    assignment.mode,
                    assignment.effort,
                    assignment.profile,
                )
            return self._profile_level(profile, assignment.mode, assignment.effort)
        return None

    def _profile_level(self, profile: ProfileInput, mode: Mode, effort: Effort | None) -> _Level:
        client = self._request.client
        with_fallbacks = mode == "automatic-with-fallbacks"
        return _Level(
            "profile-assignment",
            "candidate",
            profile.candidates.get(client, ()),
            profile.fallbacks.get(client, ()) if with_fallbacks else (),
            mode,
            effort,
            profile.id,
            profile.escalation,
        )

    def _applicable_assignments(self) -> list[AssignmentInput]:
        """The assignments that apply here, most specific first (a task, then a client)."""
        request = self._request
        fitting = [
            assignment
            for assignment in self._policy.assignments
            if assignment.kind == request.target_kind
            and assignment.name == request.target
            and assignment.client in (None, request.client)
            and assignment.task in (None, request.task)
        ]
        return sorted(fitting, key=lambda a: (a.task is None, a.client is None))

    def _profile(self, profile_id: str) -> ProfileInput | None:
        return next((p for p in self._policy.profiles if p.id == profile_id), None)

    def _evaluate(self, level: _Level) -> _Evaluated:
        eligible, rejected = self._split(level.choices, level.rejection_level, level.effort)
        fallbacks, fallback_rejected = self._split(level.fallbacks, "fallback", level.effort)
        return _Evaluated(eligible, fallbacks, rejected + fallback_rejected)

    def _is_valid(self, level: _Level, evaluated: _Evaluated) -> bool:
        if level.mode == "manual" or self._constrained:
            return bool(evaluated.eligible)
        return True

    def _used(self, level: _Level, evaluated: _Evaluated, before: list[Rejection]) -> Resolution:
        rejected = (*before, *evaluated.rejected)
        named = self._named_fallback(level)
        if named is not None and not isinstance(named, Choice):
            rejected = (*rejected, named)
        base = Resolution(
            "client-chooses",
            "automatic",
            profile=level.profile,
            mode=level.mode,
            candidates=evaluated.eligible,
            fallbacks=evaluated.fallbacks,
            rejected=rejected,
            escalation=level.escalation,
            diversity_unproven=self._unproven,
        )
        if level.mode == "manual":
            return replace(
                base,
                outcome="selected",
                source=level.source,
                selected=evaluated.eligible[0],
                fallbacks=(),
            )
        if isinstance(named, Choice):
            return replace(base, outcome="selected", source="explicit-fallback", selected=named)
        return base

    def _named_fallback(self, level: _Level) -> Choice | Rejection | None:
        """The fallback that the caller named, judged against this level's own fallbacks.

        Outside mode `automatic-with-fallbacks` the level has none, so a named one is refused with
        a visible entry and changes nothing else.
        """
        text = self._request.fallback
        if text is None:
            return None
        return self._judge_text(text, "fallback", level.fallbacks, level.effort)

    # --- constraints ----------------------------------------------------------------------

    def _split(
        self, ids: Sequence[str], level: Level, effort: Effort | None
    ) -> tuple[tuple[Choice, ...], tuple[Rejection, ...]]:
        outcomes = [self._judge_id(model_id, level, effort) for model_id in ids]
        return (
            tuple(o for o in outcomes if isinstance(o, Choice)),
            tuple(o for o in outcomes if isinstance(o, Rejection)),
        )

    def _judge_id(
        self, model_id: str, level: Level, effort: Effort | None
    ) -> Choice | Rejection | None:
        model = self._models.get(model_id)
        if model is None:
            # No entry carries the id, so no team approved it.
            return Rejection(level, None, "not-approved")
        return _outcome(level, model.id, self._judge(model, effort))

    def _judge_text(
        self, text: str, level: Level, within: Sequence[str] | None, effort: Effort | None
    ) -> Choice | Rejection | None:
        """A model string (an override or a named fallback), refused or turned into a choice.

        `within` is the list of ids the string must be one of: a named fallback must be one of its
        level's fallbacks. An unmatched override is invalid; an unmatched fallback is outside.
        """
        entry = match_entry(text, self._catalog, skip_proposed=False)
        model = None if entry is None else self._models.get(entry.id)
        model_id = None if model is None else model.id
        excluded = model is not None and is_model_excluded(model, self._rules)
        if excluded or is_excluded(text, self._rules):
            return Rejection(level, model_id, "excluded")
        if model is None:
            unmatched: Reason = "override-invalid" if within is None else "outside-profile"
            return Rejection(level, None, unmatched)
        if within is not None and model.id not in within:
            return Rejection(level, model.id, "outside-profile")
        return _outcome(level, model.id, self._judge(model, effort))

    def _judge(self, model: ModelInput, effort: Effort | None) -> _Verdict:
        """The first constraint a catalog model fails for this client, or its route to use."""
        if is_model_excluded(model, self._rules):
            return _Verdict(reason="excluded")
        if model.approval == "proposed":
            return _Verdict(reason="not-approved")
        if model.approval != "approved":
            return _Verdict(reason="disabled-or-retired")
        route = self._route(model)
        if isinstance(route, str):
            return _Verdict(reason=route)
        reason = self._diversity_reason(model)
        if reason is not None:
            return _Verdict(reason=reason)
        if self._unproven:
            return _Verdict()
        name, kind = route
        return _Verdict(choice=Choice(model.id, name, kind, effort))

    def _route(self, model: ModelInput) -> tuple[str, RouteKind] | Reason:
        """The client's first named route that is not blocked, or why there is none."""
        routes = [route for route in model.routes if route.client == self._request.client]
        if not routes:
            return "no-route-for-client"
        named = [
            (route.name, route.kind, route.access) for route in routes if route.name is not None
        ]
        if not named:
            return "route-name-unknown"
        for name, kind, access in named:
            if access != "blocked":
                return name, kind
        return "access-blocked"

    def _diversity_reason(self, model: ModelInput) -> Reason | None:
        if self._coder is not None:
            if model.id == self._coder.id:
                return "same-model-as-coder"
            if model.family == self._coder.family:
                return "same-family-as-coder"
        return None if self._meets_floor(model.id) else "outside-profile"

    def _meets_floor(self, model_id: str) -> bool:
        """True when a profile at the floor or above lists the model for this client."""
        if self._floor is None:
            return True
        if self._floor not in PROFILE_ORDER:
            return False
        limit = PROFILE_ORDER.index(self._floor)
        client = self._request.client
        return any(
            PROFILE_ORDER.index(profile.id) <= limit
            for profile in self._policy.profiles
            if profile.id in PROFILE_ORDER and model_id in profile.candidates.get(client, ())
        )


def _floor_of(request: ResolveRequest) -> str | None:
    """The lowest profile a candidate may come from, when one applies."""
    if request.coder_profile is not None:
        return request.coder_profile
    reviews = request.target_kind == "role" and request.target == CODE_REVIEWER_ROLE
    return DEFAULT_CODER_PROFILE if reviews and request.coder_model is not None else None


def _outcome(level: Level, model_id: str, verdict: _Verdict) -> Choice | Rejection | None:
    if verdict.choice is not None:
        return verdict.choice
    if verdict.reason is not None:
        return Rejection(level, model_id, verdict.reason)
    return None
