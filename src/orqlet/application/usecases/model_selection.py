"""From the v2 model policy to the resolver's plain inputs, and the checks that make a policy safe.

The policy contract is a Pydantic shape; the resolver in `orqlet.domain.model_resolution` takes
plain values and knows nothing of it. This module is the one place that maps one to the other, and
that checks the references and the exclusions of a whole policy. It reads no file and starts no
process: the policy is already loaded (`model_policy_source`), and the workflow's role and skill
names are passed in by the caller.

Two mappings exist on purpose. An assignment that names a `task` applies only to a caller that
passes that task (`models resolve --task`), and a generated file is global and cannot depend on a
task. So what is rendered is read through `to_render_policy`, which drops every task-scoped
assignment, and a task-scoped assignment can never reach a generated file (ADR-001 decision 7).

`select_models` is the one step from a policy to the settings that the renderers write. The
resolver is safe only for a policy that has passed `policy_problems`, so the selection asks first
and, for a policy with any problem, pins nothing at all: a generated file never follows a policy
that is known to be unsafe or inconsistent (ADR-005, the P-4 security review).
"""

from __future__ import annotations

from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

from orqlet.application.contracts.model_policy import (
    Assignment,
    ClientModels,
    Exclusion,
    ModelEntry,
    ModelPolicy,
    Profile,
    Route,
)
from orqlet.application.ports.instruction_adapter import ModelSetting
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.model_identity import (
    ExclusionRule,
    cursor_plain_id,
    is_excluded,
    name_conflicts,
)
from orqlet.domain.model_resolution import (
    AssignmentInput,
    Choice,
    ModelInput,
    ProfileInput,
    ResolveRequest,
    ResolverPolicy,
    RouteInput,
    catalog_entries,
    is_model_excluded,
    resolve,
)

EXCLUDED_MODEL = "ORQ-E543"
BAD_REFERENCE = "ORQ-E545"
ALIAS_RENDERED = "ORQ-W545"
NOT_RENDERABLE = "ORQ-W546"

CLAUDE_CODE = "claude-code"
CURSOR = "cursor"

type TargetKind = Literal["role", "skill"]

_ALIAS_TEXT = "the pin is an alias route, and an environment variable can remap an alias"


@dataclass(frozen=True, slots=True)
class PolicyProblem:
    """One problem of a policy: a code and the path of the field. Never a model string.

    A path is made of the contract's field names and list positions only, so it can be printed
    whatever the file holds (BC-32).
    """

    code: str
    path: str


def to_resolver_policy(policy: ModelPolicy) -> ResolverPolicy:
    """Every model, route, exclusion, profile and assignment, as the resolver's plain values."""
    return ResolverPolicy(
        models=tuple(_model(entry) for entry in policy.models),
        exclusions=tuple(_rule(exclusion) for exclusion in policy.excluded),
        profiles=tuple(_profile(profile) for profile in policy.profiles),
        assignments=tuple(_assignment(assignment) for assignment in policy.assignments),
    )


def to_render_policy(policy: ModelPolicy) -> ResolverPolicy:
    """The same inputs without any task-scoped assignment: what a generated file may follow."""
    resolver = to_resolver_policy(policy)
    return replace(
        resolver,
        assignments=tuple(a for a in resolver.assignments if a.task is None),
    )


def policy_problems(
    policy: ModelPolicy, role_names: Collection[str], skill_names: Collection[str]
) -> tuple[PolicyProblem, ...]:
    """The exclusion and reference problems of `policy`, in the order of the document.

    ORQ-E543: a model, route, candidate, fallback or assignment that an exclusion matches, in any
    approval state. ORQ-E545: a duplicate id, a name that nothing defines (a model, profile, role
    or skill) and two entries that claim the same normalised name. The caller passes the names of
    the packaged workflow, so a role or skill that does not exist is found here.
    """
    resolver = to_resolver_policy(policy)
    return (
        *_exclusion_problems(policy, resolver),
        *_reference_problems(policy, frozenset(role_names), frozenset(skill_names)),
        *_name_problems(resolver),
    )


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """What the generated files may follow: a setting for each target and client, and what was said.

    `roles` and `skills` map a target name to a client id to a setting; a target that no client
    pins has no key. A selection made from a policy that has problems holds those `problems` and
    nothing else, so that a caller can refuse the policy and no file follows it.
    """

    roles: Mapping[str, Mapping[str, ModelSetting]] = field(default_factory=dict)
    skills: Mapping[str, Mapping[str, ModelSetting]] = field(default_factory=dict)
    findings: tuple[Finding, ...] = ()
    problems: tuple[PolicyProblem, ...] = ()


def select_models(
    policy: ModelPolicy,
    role_names: Collection[str],
    skill_names: Collection[str],
    clients: Sequence[str],
) -> ModelSelection:
    """The settings of every role and skill of the workflow for each enabled client.

    Only a `selected` resolution is written, and the resolver selects only in mode `manual`; every
    other mode, and a target nobody assigned, leaves the client's own choice as it is today. A
    setting that a client cannot take is left out with a finding (ORQ-W546), and a pin on an
    alias route is written with a warning (ORQ-W545). A finding holds a fixed text, the target and
    the client, never a model string (BC-32).
    """
    problems = policy_problems(policy, role_names, skill_names)
    if problems:
        return ModelSelection(problems=problems)
    resolver = to_render_policy(policy)
    enabled = tuple(dict.fromkeys(clients))
    findings: list[Finding] = []
    return ModelSelection(
        roles=_settings_of("role", role_names, enabled, resolver, findings),
        skills=_settings_of("skill", skill_names, enabled, resolver, findings),
        findings=tuple(findings),
    )


# --- what a file follows ------------------------------------------------------------------


def _settings_of(
    kind: TargetKind,
    names: Collection[str],
    clients: Sequence[str],
    resolver: ResolverPolicy,
    findings: list[Finding],
) -> dict[str, dict[str, ModelSetting]]:
    table: dict[str, dict[str, ModelSetting]] = {}
    for name in sorted(set(names)):
        settings: dict[str, ModelSetting] = {}
        for client in clients:
            request = ResolveRequest(client=client, target_kind=kind, target=name)
            resolution = resolve(resolver, request)
            if resolution.outcome != "selected" or resolution.selected is None:
                continue
            setting = _setting(kind, name, client, resolution.selected, findings)
            if setting is not None:
                settings[client] = setting
        if settings:
            table[name] = settings
    return table


def _setting(
    kind: TargetKind, name: str, client: str, choice: Choice, findings: list[Finding]
) -> ModelSetting | None:
    refusal = _refusal(kind, client, choice)
    if refusal is not None:
        findings.append(_finding(NOT_RENDERABLE, kind, name, client, refusal))
        return None
    if choice.kind == "alias":
        findings.append(_finding(ALIAS_RENDERED, kind, name, client, _ALIAS_TEXT))
    return ModelSetting(choice.name, choice.kind, choice.effort)


def _refusal(kind: TargetKind, client: str, choice: Choice) -> str | None:
    """Why this client cannot be given the choice, in a fixed text; `None` when it can."""
    if kind == "skill" and client != CLAUDE_CODE:
        return "the client documents no skill-level model, so nothing is written"
    if client != CURSOR:
        return None
    if choice.effort is not None:
        return "Cursor takes no effort in a model value, so nothing is written"
    if not cursor_plain_id(choice.name):
        return "Cursor cannot take this model name without quotes, so nothing is written"
    return None


def _finding(code: str, kind: TargetKind, name: str, client: str, text: str) -> Finding:
    return Finding(code, f"{kind} {name} for {client}: {text}", Severity.WARNING)


# --- the mapping --------------------------------------------------------------------------


def _model(entry: ModelEntry) -> ModelInput:
    return ModelInput(
        id=entry.id,
        family=entry.family,
        approval=entry.approval.state,
        routes=tuple(_route(route) for route in entry.routes),
    )


def _route(route: Route) -> RouteInput:
    return RouteInput(
        client=route.client,
        kind=route.kind,
        name=route.name,
        access=route.access,
        resolves_to=route.resolves_to,
        also_known_as=route.also_known_as,
    )


def _rule(exclusion: Exclusion) -> ExclusionRule:
    return ExclusionRule(
        aliases=exclusion.aliases,
        id_patterns=exclusion.id_patterns,
        family_tags=exclusion.family_tags,
    )


def _profile(profile: Profile) -> ProfileInput:
    return ProfileInput(
        id=profile.id,
        mode=profile.mode,
        candidates=_by_client(profile.candidates),
        fallbacks=_by_client(profile.fallbacks),
        escalation=profile.escalation,
    )


def _by_client(entries: tuple[ClientModels, ...]) -> dict[str, tuple[str, ...]]:
    return {entry.client: entry.models for entry in entries}


def _assignment(assignment: Assignment) -> AssignmentInput:
    return AssignmentInput(
        kind=assignment.target.kind,
        name=assignment.target.name,
        mode=assignment.mode,
        model=assignment.model,
        profile=assignment.profile,
        task=assignment.task,
        client=assignment.client,
        effort=assignment.effort,
    )


# --- ORQ-E543 -----------------------------------------------------------------------------


def _exclusion_problems(policy: ModelPolicy, resolver: ResolverPolicy) -> Iterator[PolicyProblem]:
    rules = resolver.exclusions
    excluded_ids = {model.id for model in resolver.models if is_model_excluded(model, rules)}
    for index, model in enumerate(resolver.models):
        if is_excluded(model.id, rules) or is_excluded(model.family, rules):
            yield PolicyProblem(EXCLUDED_MODEL, f"models[{index}]")
        for route_index, route in enumerate(model.routes):
            strings = (route.name, route.resolves_to, *route.also_known_as)
            if any(text is not None and is_excluded(text, rules) for text in strings):
                yield PolicyProblem(EXCLUDED_MODEL, f"models[{index}].routes[{route_index}]")
    for path, model_id in _model_references(policy):
        if model_id in excluded_ids or is_excluded(model_id, rules):
            yield PolicyProblem(EXCLUDED_MODEL, path)


def _model_references(policy: ModelPolicy) -> Iterator[tuple[str, str]]:
    """Every place that names a catalog model by id, with the path of that place."""
    for profile_index, profile in enumerate(policy.profiles):
        for field_name, lists in (
            ("candidates", profile.candidates),
            ("fallbacks", profile.fallbacks),
        ):
            for list_index, entry in enumerate(lists):
                for position, model_id in enumerate(entry.models):
                    prefix = f"profiles[{profile_index}].{field_name}[{list_index}]"
                    yield f"{prefix}.models[{position}]", model_id
    for index, assignment in enumerate(policy.assignments):
        if assignment.model is not None:
            yield f"assignments[{index}].model", assignment.model


# --- ORQ-E545 -----------------------------------------------------------------------------


def _reference_problems(
    policy: ModelPolicy, role_names: frozenset[str], skill_names: frozenset[str]
) -> Iterator[PolicyProblem]:
    yield from _duplicate_ids(policy)
    known_models = {entry.id for entry in policy.models}
    for path, model_id in _model_references(policy):
        if model_id not in known_models:
            yield PolicyProblem(BAD_REFERENCE, path)
    known_profiles = {profile.id for profile in policy.profiles}
    for index, profile in enumerate(policy.profiles):
        if profile.escalation is not None and profile.escalation not in known_profiles:
            yield PolicyProblem(BAD_REFERENCE, f"profiles[{index}].escalation")
    for index, assignment in enumerate(policy.assignments):
        if assignment.profile is not None and assignment.profile not in known_profiles:
            yield PolicyProblem(BAD_REFERENCE, f"assignments[{index}].profile")
        names = role_names if assignment.target.kind == "role" else skill_names
        if assignment.target.name not in names:
            yield PolicyProblem(BAD_REFERENCE, f"assignments[{index}].target.name")


def _duplicate_ids(policy: ModelPolicy) -> Iterator[PolicyProblem]:
    for field_name, ids in (
        ("models", [entry.id for entry in policy.models]),
        ("excluded", [exclusion.id for exclusion in policy.excluded]),
    ):
        seen: set[str] = set()
        for index, item_id in enumerate(ids):
            if item_id in seen:
                yield PolicyProblem(BAD_REFERENCE, f"{field_name}[{index}].id")
            seen.add(item_id)


def _name_problems(resolver: ResolverPolicy) -> Iterator[PolicyProblem]:
    """Two entries that claim one normalised name, reported at the later entry."""
    for _earlier, later in name_conflicts(catalog_entries(resolver.models)):
        yield PolicyProblem(BAD_REFERENCE, f"models[{later}]")
