"""`orqlet models resolve`: the model that the policy gives a role, a skill or a profile.

The use case is read-only and holds three ports: the project file system, the strict loader and the
packaged workflow. It has no VCS, no process runner and no clock, so it can make no git call, start
no process and read no date; the same files give the same answer on every day, in any folder, and
a folder that is not a git repository needs nothing more (ADR-001 decision 8, BC-23).

It reads the policy with `load_model_policy`, the one reader, so a file is refused here for the
same reasons as in `upgrade` and `validate model-policy`. That reader asks its caller for a `vcs`
that only `read_model_policy_at` uses; `_PolicyView` supplies a `vcs` that fails on use, so a call
that reached a git tree would be a defect and not a quiet read. The reader checks 256 KiB after it
has read the file in full, because the `FileSystem` port has no size query; it reads the lock only
when the policy file is missing, and the strict loader refuses a lock of more than 1 MiB before it
parses it. The workflow is packaged data: only its role and skill names are read, and only for a
policy that was loaded, because those are the names that `policy_problems` checks the assignments
against.

The policy is mapped with `to_resolver_policy`, not `to_render_policy`: the answer of this command
is the one place where an assignment that names a `task` applies (ADR-001 decision 7). A policy
with any problem (ORQ-E543, ORQ-E545), and a file that is invalid, a v1 file or deleted, is
refused and nothing is selected, as `upgrade` does; the wording is this command's own.

The target is not checked against the workflow: a name that no role or skill has is answered as an
unassigned target, so a skill can ask for any role, `orqlet-code-reviewer` included.

`data` holds only what the contract of AC-2 lists, and every value in it is a catalog id or route
name that passed `ModelRef`, a price that passed `DecimalText`, a profile id, a client, or a fixed
word. The override string, the free text of the file and every path of the file stay out of it
(BC-32). Every rejection at the level of the override is shown as `override-invalid`, whatever the
resolver's own reason was, so the string is never described by the reason that it hit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, NoReturn

from orqlet.application.contracts.model_policy import ModelEntry, ModelPolicy
from orqlet.application.ports.documents import DocumentLoader
from orqlet.application.ports.filesystem import FileSystem
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.model_policy_source import (
    PolicyAbsent,
    PolicyDeleted,
    PolicyInvalid,
    load_model_policy,
    model_policy_path,
)
from orqlet.application.usecases.model_selection import (
    BAD_REFERENCE,
    EXCLUDED_MODEL,
    POLICY_DELETED,
    PolicyProblem,
    policy_problems,
    to_resolver_policy,
)
from orqlet.application.usecases.workflow_sources import load_roles, load_skills
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.model_resolution import (
    Choice,
    Rejection,
    Resolution,
    ResolveRequest,
    ResolverPolicy,
    resolve,
)

type ModelsStatus = Literal["selected", "automatic", "none-qualifies", "refused"]
type TargetKind = Literal["role", "skill", "profile"]

NO_POLICY_HINT = "no model policy; the client chooses"
NO_ASSIGNMENT_HINT = "no assignment for this target; the client chooses"
_OVERRIDE_INVALID = "override-invalid"
# A refusal lists the field paths of a policy that is faulty in many places, and no more than this
# many: a file at the size limit can hold one problem for each of thousands of entries.
_MAX_PATHS = 20
_PROBLEM_TEXT = {
    EXCLUDED_MODEL: (
        "An exclusion matches a model, a route, a candidate, a fallback or an assignment of the "
        "model policy"
    ),
    BAD_REFERENCE: (
        "The model policy has a duplicate id, a reference or a name that nothing defines, or two "
        "models that claim one name"
    ),
}
_PROBLEM_REMEDY = "No selection is shown. Fix the file or restore it from Git."


@dataclass(frozen=True, slots=True)
class ModelsServices:
    """What `models resolve` may touch: the project's files, the strict loader, the workflow."""

    project: FileSystem
    loader: DocumentLoader
    workflow: WorkflowSource


@dataclass(frozen=True, slots=True)
class ModelsQuery:
    """What is asked. `different_family_from` is a catalog id, `coder_profile` a profile id."""

    client: str
    kind: TargetKind
    name: str
    task: str | None = None
    override: str | None = None
    different_family_from: str | None = None
    coder_profile: str | None = None


@dataclass(frozen=True, slots=True)
class ModelsResult:
    """`data` is the mapping of AC-2, empty for a refusal; `findings` say why a refusal happened."""

    status: ModelsStatus
    data: dict[str, Any]
    findings: tuple[Finding, ...] = ()


class _PolicyView:
    """The three ports that `load_model_policy` asks for, with a `vcs` that fails on use."""

    def __init__(self, services: ModelsServices) -> None:
        self._services = services

    @property
    def project(self) -> FileSystem:
        return self._services.project

    @property
    def loader(self) -> DocumentLoader:
        return self._services.loader

    @property
    def vcs(self) -> NoReturn:
        raise RuntimeError("models resolve reads no git tree")


def models_resolve(services: ModelsServices, query: ModelsQuery) -> ModelsResult:
    """The selection for `query`, or the refusal to give one. Writes nothing."""
    state = load_model_policy(_PolicyView(services))
    if isinstance(state, PolicyInvalid):
        return _refused(state.findings)
    if isinstance(state, PolicyDeleted):
        return _refused((_deleted_finding(),))
    if isinstance(state, PolicyAbsent):
        return _answer(query, ResolverPolicy(), None)
    roles, skills = _workflow_names(services.workflow)
    problems = policy_problems(state.policy, roles, skills)
    if problems:
        return _refused(_problem_findings(problems))
    return _answer(query, to_resolver_policy(state.policy), state.policy)


def _workflow_names(workflow: WorkflowSource) -> tuple[list[str], list[str]]:
    """The role and skill names of the packaged workflow, as `compose` reads them."""
    roles = [role.name for role in load_roles(workflow)]
    skills = [skill.name for skill in load_skills(workflow, IMPLEMENTED_COMMANDS)]
    return roles, skills


# --- the refusals ---------------------------------------------------------------------------


def _refused(findings: Sequence[Finding]) -> ModelsResult:
    return ModelsResult("refused", {}, tuple(findings))


def _deleted_finding() -> Finding:
    path = str(model_policy_path())
    return Finding(
        POLICY_DELETED,
        f"The model policy file {path} is missing, but the lock records it as seeded. No "
        "selection is shown, because a deleted policy drops every exclusion and pin that it "
        "held. Restore it from Git or write a valid policy file.",
        Severity.ERROR,
        path,
    )


def _problem_findings(problems: Sequence[PolicyProblem]) -> tuple[Finding, ...]:
    """One finding for each code, with the field paths and no value of the file."""
    paths: dict[str, list[str]] = {}
    for problem in problems:
        paths.setdefault(problem.code, []).append(problem.path)
    return tuple(
        Finding(
            code,
            f"{_PROBLEM_TEXT[code]}: {_listed(found)}. {_PROBLEM_REMEDY}",
            Severity.ERROR,
            str(model_policy_path()),
        )
        for code, found in paths.items()
    )


def _listed(paths: Sequence[str]) -> str:
    head = ", ".join(paths[:_MAX_PATHS])
    return head if len(paths) <= _MAX_PATHS else f"{head} and {len(paths) - _MAX_PATHS} more"


# --- the answer -----------------------------------------------------------------------------


def _answer(
    query: ModelsQuery, resolver: ResolverPolicy, policy: ModelPolicy | None
) -> ModelsResult:
    request = ResolveRequest(
        client=query.client,
        target_kind=query.kind,
        target=query.name,
        task=query.task,
        override=query.override,
        coder_model=query.different_family_from,
        coder_profile=query.coder_profile,
    )
    resolution = resolve(resolver, request)
    status = _status(resolution)
    catalog = {} if policy is None else _first_by_id(policy)
    chosen = [] if resolution.selected is None else [resolution.selected]
    data: dict[str, Any] = {
        "client": query.client,
        "target": {"kind": query.kind, "name": query.name},
        "task": query.task,
        "policy": "absent" if policy is None else "present",
        "profile": resolution.profile,
        "mode": resolution.mode,
        "source": resolution.source,
        "selection": None if resolution.selected is None else _choice(resolution.selected),
        "client_chooses": resolution.outcome == "client-chooses",
        "candidates": [_listed_choice(c, catalog, query.client) for c in resolution.candidates],
        "fallbacks": [_listed_choice(c, catalog, query.client) for c in resolution.fallbacks],
        "escalation": resolution.escalation,
        "list_prices": _prices(catalog, [*chosen, *resolution.candidates, *resolution.fallbacks]),
        "rejected": [_rejection(item) for item in resolution.rejected],
        "hint": _hint(policy is not None, resolution, resolver, request),
        "result": status,
    }
    return ModelsResult(status, data)


def _status(resolution: Resolution) -> ModelsStatus:
    if resolution.outcome == "selected":
        return "selected"
    return "automatic" if resolution.outcome == "client-chooses" else "none-qualifies"


def _first_by_id(policy: ModelPolicy) -> dict[str, ModelEntry]:
    """The catalog by id; the resolver keeps the first entry of an id, and so does this."""
    catalog: dict[str, ModelEntry] = {}
    for entry in policy.models:
        catalog.setdefault(entry.id, entry)
    return catalog


def _choice(choice: Choice) -> dict[str, Any]:
    return {
        "model": choice.model,
        "name": choice.name,
        "kind": choice.kind,
        "effort": choice.effort,
    }


def _listed_choice(choice: Choice, catalog: dict[str, ModelEntry], client: str) -> dict[str, Any]:
    return {**_choice(choice), "also_known_as": _also_known_as(catalog, choice, client)}


def _also_known_as(catalog: dict[str, ModelEntry], choice: Choice, client: str) -> list[str]:
    """The other names of the route that gave `choice`: the client's first route of that name."""
    entry = catalog.get(choice.model)
    if entry is None:
        return []
    for route in entry.routes:
        if route.client == client and route.name == choice.name:
            return list(route.also_known_as)
    return []


def _prices(catalog: dict[str, ModelEntry], choices: Sequence[Choice]) -> list[dict[str, Any]]:
    """The list price of each distinct model that is shown, in the order that they are shown."""
    prices: list[dict[str, Any]] = []
    for model in dict.fromkeys(choice.model for choice in choices):
        entry = catalog.get(model)
        if entry is not None and entry.list_price is not None:
            prices.append(
                {
                    "model": model,
                    "input_per_million_usd": entry.list_price.input_per_million_usd,
                    "output_per_million_usd": entry.list_price.output_per_million_usd,
                }
            )
    return prices


def _rejection(item: Rejection) -> dict[str, Any]:
    """The catalog id (or none) and the reason; the override's own reason is never shown."""
    reason = _OVERRIDE_INVALID if item.level == "override" else item.reason
    return {"model": item.model, "reason": reason}


def _hint(
    present: bool, resolution: Resolution, resolver: ResolverPolicy, request: ResolveRequest
) -> str:
    """The fixed sentence for the profile of this work.

    A valid override ends the resolution before any profile is read, so the profile of the hint is
    that of the same request without the override.
    """
    if not present:
        return NO_POLICY_HINT
    profile = resolution.profile
    if resolution.source == "task-override":
        profile = resolve(resolver, replace(request, override=None)).profile
    if profile is None:
        return NO_ASSIGNMENT_HINT
    return (
        f"Suggested for this work: profile {profile}; the client keeps the choice and nothing "
        "here changes the model."
    )
