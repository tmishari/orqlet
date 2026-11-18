"""The model identity behind a review record, judged on two git trees (ADR-005, ADR-007).

A change must not vouch for itself, so `validate review` reads the model policy from the base tree
and from the staged tree with the one reader, `read_model_policy_at`, and each tree has its part:

- the exclusions are the union of the two, so a change cannot remove one and pass a record against
  its own edit (ADR-005 decision 2);
- a family comes only from the policy of the base tree, and only from an entry that is not
  `proposed` there, so neither seed text that no team approved nor an entry that the change adds
  can create a difference for that change (ADR-007 decision 1, BC-10);
- the staged tree decides whether the policy is refused: a file that is there and cannot be loaded,
  or that is deleted while the base tree has one, is an error for a record that names a model, and
  nothing falls back to `model_families` then;
- a deleted file is not an absent one (ADR-005 decision 2): when neither tree has the file and the
  lock of either tree lists it as seeded, an earlier change deleted it and the policy is refused
  in the same way. Only a project that never had the file gets the legacy rules.

Only an observed identity counts (ADR-007 decision 2). The module returns values and findings and
writes nothing. A finding names a catalog id, the word `unmatched` with a length, a closed name or
fixed text, and never a string from the record or a key from the policy (BC-32).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.contracts.review_result import AgentBinding, CoderBinding, ReviewResult
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.vcs import VcsError
from orqlet.application.usecases.model_policy_source import (
    PolicyAbsent,
    PolicyInvalid,
    PolicyLoaded,
    PolicyServices,
    model_policy_path,
    read_model_policy_at,
)
from orqlet.application.usecases.model_selection import to_resolver_policy
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.independence import (
    IDENTITY_UNKNOWN,
    SAME_MODEL_DIFFERENT_CLIENT,
    Independence,
    derive_independence,
    independence_notes,
    is_observed,
)
from orqlet.domain.independence import family_of as legacy_family_of
from orqlet.domain.model_identity import (
    CatalogEntry,
    ExclusionRule,
    is_excluded,
    match_entry,
    normalise,
)
from orqlet.domain.model_resolution import catalog_entries
from orqlet.domain.ownership import OwnerMode

# The same literal as the lock reader of `model_policy_source`, which reads the working tree and
# keeps its path private.
_LOCK_PATH = ".orqlet/generated.lock.yaml"
MODEL_REQUESTED_DIFFERS = "model-requested-differs-from-observed"
POLICY_CHANGED = "policy-changed-in-this-change"
BINDING_ADDED = "binding-added-in-this-change"
CODEX_READ_ONLY_NOT_STATED = "codex-read-only-not-stated"
# The closed warnings, in the order in which `independence_notes` lists them, with their codes.
CLOSED_WARNINGS: dict[str, str] = {
    MODEL_REQUESTED_DIFFERS: "ORQ-W464",
    IDENTITY_UNKNOWN: "ORQ-W460",
    SAME_MODEL_DIFFERENT_CLIENT: "ORQ-W461",
    POLICY_CHANGED: "ORQ-W462",
    BINDING_ADDED: "ORQ-W463",
    CODEX_READ_ONLY_NOT_STATED: "ORQ-W465",
}
CODEX_PHRASE = "read-only is not enforced by this client"

_NAMES_BY_CODE = {code: name for name, code in CLOSED_WARNINGS.items()}
_NOTE_TEXT = {
    IDENTITY_UNKNOWN: (
        "the class rests on a different client, and at least one side has no observed identity "
        "that the policy or `model_families` names"
    ),
    SAME_MODEL_DIFFERENT_CLIENT: (
        "both sides ran the same observed model on different clients, so only the client differs"
    ),
}


def closed_warning(name: str, text: str, path: str | None) -> Finding:
    """A warning of the closed set: its message starts with the name and a colon."""
    return Finding(CLOSED_WARNINGS[name], f"{name}: {text}", Severity.WARNING, path)


def ordered(names: Iterable[str]) -> tuple[str, ...]:
    """The closed names once each, in the fixed order of `CLOSED_WARNINGS`."""
    present = set(names)
    return tuple(name for name in CLOSED_WARNINGS if name in present)


# --- the two trees ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PolicyView:
    """What the two trees say about the policy, for one review."""

    catalog: tuple[CatalogEntry, ...]  # empty unless the base tree's policy may give families
    exclusions: tuple[ExclusionRule, ...]  # the union of the policies that could be loaded
    refusal: str | None  # why the staged policy is refused, or `None`
    changed: bool  # the staged policy is valid and is not the base tree's policy
    never_present: bool  # neither tree has a policy file


type _TreePolicy = PolicyAbsent | PolicyLoaded | PolicyInvalid


def read_policy_view(services: PolicyServices, base: str, staged: str) -> PolicyView:
    """Apply the tree matrix of ADR-007 decision 1 to the policy of the two trees."""
    at_base = read_model_policy_at(services, base)
    at_staged = read_model_policy_at(services, staged)
    base_policy = at_base.policy if isinstance(at_base, PolicyLoaded) else None
    staged_policy = at_staged.policy if isinstance(at_staged, PolicyLoaded) else None
    in_neither = isinstance(at_base, PolicyAbsent) and isinstance(at_staged, PolicyAbsent)
    deleted_earlier = in_neither and _lock_seeds_policy(services, (base, staged))
    refusal = _refusal(at_base, at_staged, deleted_earlier)
    loaded = (policy for policy in (base_policy, staged_policy) if policy is not None)
    return PolicyView(
        catalog=_catalog(base_policy) if refusal is None and base_policy else (),
        exclusions=tuple(rule for policy in loaded for rule in _rules(policy)),
        refusal=refusal,
        changed=staged_policy is not None and staged_policy != base_policy,
        never_present=in_neither and not deleted_earlier,
    )


def _lock_seeds_policy(services: PolicyServices, trees: Iterable[str]) -> bool:
    """True when a valid lock of any of the trees lists the policy file with the owner `seeded`.

    Both trees are read, so a change cannot drop the row to hide an earlier deletion. A lock that
    is missing, unreadable or invalid says nothing, as in the working-tree reader: the lock is
    validated elsewhere, and a broken lock is not a reason to refuse the policy.
    """
    policy_path = str(model_policy_path())
    for tree in trees:
        try:
            raw = services.vcs.read_at(tree, _LOCK_PATH)
            if raw is None:
                continue
            lock = load_contract(services.loader, GeneratedLock, raw, source=_LOCK_PATH)
        except (VcsError, DocumentError):
            continue
        if any(row.path == policy_path and row.owner is OwnerMode.SEEDED for row in lock.files):
            return True
    return False


def _refusal(at_base: _TreePolicy, at_staged: _TreePolicy, deleted_earlier: bool) -> str | None:
    """A deleted file is not an absent one; only a project that never had a policy is legacy."""
    if deleted_earlier:
        return "neither tree has it and the lock records it as seeded"
    if isinstance(at_staged, PolicyInvalid):
        codes = ", ".join(sorted({finding.code for finding in at_staged.findings}))
        return f"it cannot be loaded ({codes})"
    if isinstance(at_staged, PolicyAbsent) and not isinstance(at_base, PolicyAbsent):
        return "it is deleted while the base tree has one"
    return None


def _catalog(policy: ModelPolicy) -> tuple[CatalogEntry, ...]:
    return catalog_entries(to_resolver_policy(policy).models)


def _rules(policy: ModelPolicy) -> tuple[ExclusionRule, ...]:
    return to_resolver_policy(policy).exclusions


# --- one record ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Identity:
    """One side of a review: the catalog model and family of an observed identity, if any."""

    model_id: str | None
    family: str | None
    observed: bool


@dataclass(frozen=True, slots=True)
class ReviewIdentity:
    """The class derived for one record, and the findings and closed names behind it."""

    derived: Independence
    excluded: bool
    findings: tuple[Finding, ...]
    names: tuple[str, ...]


def assess_identity(
    services: PolicyServices,
    record: ReviewResult,
    *,
    base: str,
    staged: str,
    approved_binding: bool,
    legacy_families: Sequence[tuple[str, str]],
    path: str,
) -> ReviewIdentity:
    """Judge the models of `record` on the two trees and derive its independence class."""
    view = read_policy_view(services, base, staged)
    agent, coder = record.agent, record.coder_binding
    named = _named_models(agent, coder)
    hits = [(side, field) for side, field, model in named if is_excluded(model, view.exclusions)]
    fallback = () if view.refusal else tuple(legacy_families)
    sides = (_identity(agent, view, fallback), _identity(coder, view, fallback))
    findings = [
        *_policy_findings(view, bool(named), path),
        *(_excluded_finding(side, field, path) for side, field in hits),
        *_substitution_findings(agent, coder, view, path),
        *_note_findings(record, sides, path),
        *_codex_findings(record, path),
    ]
    derived = derive_independence(
        approved_binding=approved_binding,
        agent_client=agent.client,
        agent_family=sides[0].family,
        coder_client=coder.client,
        coder_family=sides[1].family,
        agent_observed=sides[0].observed,
        coder_observed=sides[1].observed,
        fresh=None if agent.context is None else agent.context.fresh,
        role=record.role,
    )
    names = ordered(_NAMES_BY_CODE[f.code] for f in findings if f.code in _NAMES_BY_CODE)
    return ReviewIdentity(Independence.I0 if hits else derived, bool(hits), tuple(findings), names)


def _named_models(agent: AgentBinding, coder: CoderBinding) -> list[tuple[str, str, str]]:
    """Each model string that the record names, with whose it is and whether it was requested."""
    return [
        (side, field, model)
        for side, binding in (("agent", agent), ("coder", coder))
        for field, model in (
            ("requested", binding.model_requested),
            ("observed", binding.model_observed),
        )
        if model is not None
    ]


def _identity(
    binding: AgentBinding | CoderBinding,
    view: PolicyView,
    legacy_families: Sequence[tuple[str, str]],
) -> Identity:
    """An identity counts only when it was observed; then the policy's family wins."""
    model = binding.model_observed
    if model is None or not is_observed(binding.identity_source, model):
        return Identity(None, None, False)
    entry = match_entry(model, view.catalog, skip_proposed=True)
    if entry is not None:
        return Identity(entry.id, entry.family, True)
    return Identity(None, legacy_family_of(model, legacy_families), True)


def _policy_findings(view: PolicyView, names_a_model: bool, path: str) -> list[Finding]:
    findings: list[Finding] = []
    if view.changed:
        findings.append(
            closed_warning(
                POLICY_CHANGED,
                "the policy of the staged tree is not the policy of the base tree, or the base "
                "tree has none that loads; exclusions are judged on both trees and a family "
                "only from the base tree",
                path,
            )
        )
    if names_a_model and view.refusal:
        findings.append(
            Finding(
                "ORQ-E461",
                f"the model policy of the staged tree is refused: {view.refusal}; the models of "
                "this record cannot be judged and nothing falls back to model_families",
                Severity.ERROR,
                path,
            )
        )
    elif names_a_model and view.never_present:
        findings.append(
            Finding(
                "ORQ-I460",
                "no exclusion list was available: neither tree has a model policy, so the legacy "
                "rules of model_families apply",
                Severity.INFO,
                path,
            )
        )
    return findings


def _excluded_finding(side: str, field: str, path: str) -> Finding:
    return Finding(
        "ORQ-E460",
        f"the {field} model of the {side} matches an exclusion of the model policy; the record "
        "is invalid evidence and its class is I0",
        Severity.ERROR,
        path,
    )


def _substitution_findings(
    agent: AgentBinding, coder: CoderBinding, view: PolicyView, path: str
) -> list[Finding]:
    findings: list[Finding] = []
    for side, binding in (("agent", agent), ("coder", coder)):
        requested, observed = binding.model_requested, binding.model_observed
        if requested is None or observed is None or not _differ(requested, observed, view):
            continue
        findings.append(
            closed_warning(
                MODEL_REQUESTED_DIFFERS,
                f"the {side} asked for {_label(requested, view)} and the client ran "
                f"{_label(observed, view)}",
                path,
            )
        )
    return findings


def _differ(requested: str, observed: str, view: PolicyView) -> bool:
    """Two catalog models differ by id; a string that names none differs by its normal form."""
    first = match_entry(requested, view.catalog, skip_proposed=True)
    second = match_entry(observed, view.catalog, skip_proposed=True)
    if first is not None and second is not None:
        return first.id != second.id
    return normalise(requested) != normalise(observed)


def _label(model: str, view: PolicyView) -> str:
    """A catalog id, or `unmatched` and a length: never the string that the record wrote."""
    entry = match_entry(model, view.catalog, skip_proposed=True)
    return entry.id if entry is not None else f"unmatched ({len(model)} characters)"


def _note_findings(
    record: ReviewResult, sides: tuple[Identity, Identity], path: str
) -> list[Finding]:
    agent_side, coder_side = sides
    notes = independence_notes(
        agent_client=record.agent.client,
        coder_client=record.coder_binding.client,
        agent_model=agent_side.model_id,
        agent_family=agent_side.family,
        agent_observed=agent_side.observed,
        coder_model=coder_side.model_id,
        coder_family=coder_side.family,
        coder_observed=coder_side.observed,
    )
    return [closed_warning(name, _NOTE_TEXT[name], path) for name in notes]


def _codex_findings(record: ReviewResult, path: str) -> list[Finding]:
    """Codex cannot enforce read-only, so a record of it must say so (ADR-007 decision 9)."""
    if record.agent.client != "codex" or any(CODEX_PHRASE in t for t in record.capability_limits):
        return []
    text = f'a codex record must state "{CODEX_PHRASE}" in capability_limits'
    return [closed_warning(CODEX_READ_ONLY_NOT_STATED, text, path)]
