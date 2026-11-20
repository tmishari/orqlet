"""`models_resolve`, the use case behind `orqlet models resolve` (task dynamic-model-profiles,
phase P-8).

Every test cites its `expected_behavior_source`. AC-1 to AC-7 are the acceptance criteria of phase
P-8 in docs/design/dynamic-model-profiles/plan.yaml. component.md, adr-001 and adr-002 are the
files under docs/design/dynamic-model-profiles/design/; BC-n are the rows of the acceptance table of
component.md, F-n its failure rows. R-1 to R-14 are the readings of the acceptance criteria that
the coder of the phase was given: R-1 the services and the reader, R-2 the usage checks, R-3 the
refusals, R-4 the override and the reason `excluded`, R-5 the hint, R-6 the data, R-7 the exit
statuses, R-8 the text output, R-9 the markers, R-10 no git, no process and no clock, R-11 the task
scope, R-12 roles, skills and profiles, R-13 the registration and R-14 the sizes. The usage checks
(R-2), the text output (R-8) and the registration (R-13) belong to the command and are tested in
tests/integration/test_models_resolve_cli.py; this file tests the use case (AC-2 to AC-6).

These tests were written first, by the Tester of phase P-8, before the use case existed. They run
on the memory file system, the real strict loader and the real packaged workflow, wrapped so that
the file system fails on any access that the reading does not allow and the workflow counts its
calls. A policy is a document built in code and written as JSON text, which is YAML. Credential
shaped text is assembled from parts at run time and never written as one literal (ORQLET-SEC-003).
The module under test is imported inside `ask` and the tests that need it, so a missing module is
one failure for each test and not one error for the whole file.

The domain resolver has its own tests (tests/unit/domain/test_model_resolution.py). What a
resolution is for a policy is therefore pinned here only as far as the use case maps it: the keys
and the shape of `data`, the fields that come from the resolution, the ones the use case adds
(the hint, the list prices, `also_known_as`, `client_chooses`, `result`), the override rule, the
reader and the refusals. The premise tests at the start say what the domain gives for each fixture.

Behaviour that the criteria and the readings leave open is deliberately not pinned here:
- the wording of any finding beyond the codes, the field paths and the fixed words that the
  readings give (the one thing pinned is that no message says `upgrade`);
- the `path` of the findings of ORQ-E547 and the order of two findings of different codes;
- the hint of a target that has a pin and a profile assignment, or whose pin and profile both
  failed: R-5 reads the profile of the resolution, which is none there, and AC-4 reads whether the
  target has a profile (reported to the person);
- which models get a `list_prices` entry beyond the reading of R-6 (a model that the selection,
  the candidates or the fallbacks hold and that has a `list_price`), and the `list_prices` of a
  `task-override` selection other than that the selected model is the one entry;
- the exact `rejected` list when an unknown or proposed coder model leaves no candidate: the
  resolver shows no reason for a model that passed every constraint but cannot be shown different;
- the `rejected` entries of a fallback that the policy lists (the use case maps what the resolver
  gives; the fallback rules are tested in the domain tests);
- whether the workflow is read for its `release` or only for its names, and how often the policy
  file is read.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import importlib
import json
import re
import socket
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.filesystem import FileKind
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.model_selection import policy_problems, to_resolver_policy
from orqlet.application.usecases.workflow_sources import load_roles, load_skills
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.model_resolution import REJECTION_REASONS, ResolveRequest, resolve
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.versions import WorkflowRelease
from tests.fakes.memory_fs import MemoryFileSystem

if TYPE_CHECKING:
    from orqlet.application.usecases.models_resolve import ModelsResult

pytestmark = pytest.mark.unit

Doc = dict[str, Any]

USECASE = "orqlet.application.usecases.models_resolve"
SOURCE_FILE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "orqlet"
    / "application"
    / "usecases"
    / "models_resolve.py"
)
POLICY = ".orqlet/model-policy.yaml"
LOCK = ".orqlet/generated.lock.yaml"
LIMIT = 256 * 1024  # a policy of 262144 bytes is read; 262145 bytes is refused
LOCK_LIMIT = 1024 * 1024  # the strict loader refuses more than this before it parses

E540 = "ORQ-E540"
E541 = "ORQ-E541"
E542 = "ORQ-E542"
E543 = "ORQ-E543"
E545 = "ORQ-E545"
E547 = "ORQ-E547"

CLAUDE = "claude-code"
CODEX = "codex"
CURSOR = "cursor"
CLIENTS = (CLAUDE, CODEX, CURSOR)
MODES = ("automatic", "manual", "automatic-with-fallbacks")
TESTER = "orqlet-tester"
INVENTORY = "orqlet-inventory"
DESIGN = "orqlet-design"
# Item 4 of the interface of phase P-7 (the same packaged workflow): the names that the use case
# checks the assignments against.
ROLES = (
    "orqlet-arch-reviewer",
    "orqlet-inventory",
    "orqlet-security-reviewer",
    "orqlet-tester",
    "orqlet-tracer",
)
SKILLS = (
    "orqlet-design",
    "orqlet-implement",
    "orqlet-onboard",
    "orqlet-plan",
    "orqlet-research",
    "orqlet-review",
)

NO_POLICY = "no model policy; the client chooses"
NO_ASSIGNMENT = "no assignment for this target; the client chooses"
LOADER = StrictYamlLoader()
WORKFLOW = PackagedWorkflow()

# The ten words of the closed set of AC-2. `excluded` is one of them, but it can never be shown
# (R-4): a policy that names an excluded model is refused, and an excluded override is
# `override-invalid`.
SHOWN_REASONS = frozenset(REJECTION_REASONS) - {"excluded"}

# A credential-shaped placeholder, assembled at run time (ORQLET-SEC-003).
CREDENTIAL = "".join(("gh", "p_", ("aB3" * 13)[:36]))

# The keys of `data` (AC-2) and of each nested object.
DATA_KEYS = {
    "client",
    "target",
    "task",
    "policy",
    "profile",
    "mode",
    "source",
    "selection",
    "client_chooses",
    "candidates",
    "fallbacks",
    "escalation",
    "list_prices",
    "rejected",
    "hint",
    "result",
}
SELECTION_KEYS = {"model", "name", "kind", "effort"}
ENTRY_KEYS = {"model", "name", "kind", "effort", "also_known_as"}
PRICE_KEYS = {"model", "input_per_million_usd", "output_per_million_usd"}


def suggested(profile_id: str) -> str:
    """The hint of a target that has a profile (AC-4), word for word."""
    return (
        f"Suggested for this work: profile {profile_id}; "
        "the client keeps the choice and nothing here changes the model."
    )


# --- fakes that watch what the use case does --------------------------------------------------


class Files(MemoryFileSystem):
    """The project of a test. Once armed it records every path that is asked about and fails the
    test on any path but the policy and the lock, on a listing and on any write (R-10a)."""

    def __init__(self) -> None:
        super().__init__()
        self.armed = False
        self.touched: list[str] = []
        self.reads: list[str] = []

    def _watch(self, path: CanonicalPath) -> None:
        if self.armed:
            self.touched.append(str(path))
            if str(path) not in (POLICY, LOCK):
                raise AssertionError(f"the command asked about {path}")

    def _refuse_when_armed(self, what: str) -> None:
        if self.armed:
            raise AssertionError(f"a read-only command never does this: {what}")

    def kind(self, path: CanonicalPath) -> FileKind | None:
        self._watch(path)
        return super().kind(path)

    def read_bytes(self, path: CanonicalPath) -> bytes:
        self._watch(path)
        if self.armed:
            self.reads.append(str(path))
        return super().read_bytes(path)

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        self._refuse_when_armed("list a folder")
        return super().list_dir(path)

    def write_atomic(self, path: CanonicalPath, data: bytes) -> None:
        self._refuse_when_armed("write")
        super().write_atomic(path, data)

    def delete(self, path: CanonicalPath) -> None:
        self._refuse_when_armed("delete")
        super().delete(path)

    def make_dir(self, path: CanonicalPath) -> None:
        self._refuse_when_armed("make a folder")
        super().make_dir(path)

    def remove_empty_dir(self, path: CanonicalPath) -> None:
        self._refuse_when_armed("remove a folder")
        super().remove_empty_dir(path)


class CountingWorkflow:
    """The real packaged workflow, wrapped so that a test can see whether it was asked anything."""

    def __init__(self) -> None:
        self._inner: WorkflowSource = WORKFLOW
        self.calls: list[str] = []

    @property
    def release(self) -> WorkflowRelease:
        self.calls.append("release")
        return self._inner.release

    def read_text(self, path: str) -> str:
        self.calls.append(f"read_text {path}")
        return self._inner.read_text(path)

    def paths(self) -> tuple[str, ...]:
        self.calls.append("paths")
        return self._inner.paths()

    def problems(self) -> tuple[str, ...]:
        self.calls.append("problems")
        return self._inner.problems()


# --- policies built in code -------------------------------------------------------------------


def route(
    client: str,
    name: str | None,
    *,
    kind: str = "id",
    resolves_to: str | None = None,
    also_known_as: Sequence[str] = (),
    access: str = "unknown",
) -> Doc:
    return {
        "client": client,
        "kind": kind,
        "name": name,
        "resolves_to": resolves_to,
        "also_known_as": list(also_known_as),
        "access": access,
        "retires_on": None,
    }


def routes_of(
    prefix: str,
    *,
    clients: Sequence[str] = CLIENTS,
    also: Mapping[str, Sequence[str]] | None = None,
) -> list[Doc]:
    """One id route for each client, named `<prefix>-<client>`, with the spellings `also` lists."""
    spellings = also or {}
    return [
        route(client, f"{prefix}-{client}", also_known_as=spellings.get(client, ()))
        for client in clients
    ]


def entry(
    model_id: str,
    *routes: Doc,
    family: str = "family-one",
    state: str = "approved",
    price: tuple[str, str] | None = None,
    **extra: Any,
) -> Doc:
    """A catalog entry; an approved one carries an approver and `pr:42`."""
    granted = state == "approved"
    approval = {
        "state": state,
        "approved_by": extra.get("approved_by", "example-approver" if granted else None),
        "approval_ref": extra.get("approval_ref", "pr:42" if granted else None),
    }
    document: Doc = {
        "id": model_id,
        "family": family,
        "approval": approval,
        "documented": {
            "evidence": extra.get("evidence", "docs/example/evidence/entry.md"),
            "date": "2026-10-30",
        },
        "callable": "not-run",
        "evaluated": {"state": "none"},
        "routes": list(routes),
    }
    if price is not None:
        document["list_price"] = {
            "input_per_million_usd": price[0],
            "output_per_million_usd": price[1],
            "source": extra.get("price_source", "docs/example/evidence/prices.md"),
        }
    return document


def exclusion(
    rule_id: str,
    *,
    aliases: Sequence[str] = (),
    id_patterns: Sequence[str] = (),
    family_tags: Sequence[str] = (),
    reason: str = "Example reason.",
    source: str = "Example notice.",
) -> Doc:
    return {
        "id": rule_id,
        "reason": reason,
        "source": source,
        "aliases": list(aliases),
        "id_patterns": list(id_patterns),
        "family_tags": list(family_tags),
    }


def profile_doc(
    profile_id: str,
    *,
    mode: str = "manual",
    candidates: Sequence[str] | Mapping[str, Sequence[str]] = (),
    fallbacks: Sequence[str] | Mapping[str, Sequence[str]] = (),
    escalation: str | None = None,
    capability: str = "Example capability.",
) -> Doc:
    """A profile; a plain list is offered to every client, a mapping to the clients it names."""

    def lists(value: Sequence[str] | Mapping[str, Sequence[str]]) -> list[Doc]:
        by_client = value if isinstance(value, Mapping) else dict.fromkeys(CLIENTS, value)
        return [{"client": c, "models": list(m)} for c, m in by_client.items() if m]

    return {
        "id": profile_id,
        "capability": capability,
        "mode": mode,
        "candidates": lists(candidates),
        "fallbacks": lists(fallbacks),
        "escalation": escalation,
    }


def assignment_doc(
    kind: str,
    name: str,
    *,
    profile: str | None = None,
    model: str | None = None,
    mode: str = "manual",
    client: str | None = None,
    task: str | None = None,
    effort: str | None = None,
) -> Doc:
    return {
        "target": {"kind": kind, "name": name},
        "task": task,
        "client": client,
        "profile": profile,
        "model": model,
        "mode": mode,
        "effort": effort,
    }


def pinned(model_id: str, **fields: Any) -> Doc:
    """The tester role pinned to one model."""
    return assignment_doc("role", TESTER, model=model_id, **fields)


def via(profile_id: str, mode: str = "manual", **fields: Any) -> Doc:
    """The tester role assigned to a profile."""
    return assignment_doc("role", TESTER, profile=profile_id, mode=mode, **fields)


A, B, C, D = "example-a", "example-b", "example-c", "example-d"
PROPOSED, DISABLED, RETIRED = "example-proposed", "example-disabled", "example-retired"
CLAUDE_ONLY, UNNAMED, BLOCKED_ROUTE = "example-claude-only", "example-unnamed", "example-blocked"
ALIAS, TWO_ROUTES = "example-alias", "example-two-routes"
ALSO_A = "example-a-claude-code-xhigh"  # a spelling that the Claude Code route of A lists
# What `also_known_as` holds for a route of the catalog below, by model and client.
ALSO = {(A, CLAUDE): [ALSO_A], (TWO_ROUTES, CLAUDE): ["example-two-routes-second-alt"]}

CATALOG = [
    entry(A, *routes_of(A, also={CLAUDE: [ALSO_A]}), family="family-one", price=("3", "15")),
    entry(B, *routes_of(B), family="family-two"),
    entry(C, *routes_of(C), family="family-one", price=("0.25", "1.25")),
    entry(D, *routes_of(D), family="family-three"),
    entry(PROPOSED, *routes_of(PROPOSED), family="family-four", state="proposed"),
    entry(DISABLED, *routes_of(DISABLED), family="family-five", state="disabled"),
    entry(RETIRED, *routes_of(RETIRED), family="family-six", state="retired"),
    entry(CLAUDE_ONLY, route(CLAUDE, f"{CLAUDE_ONLY}-{CLAUDE}"), family="family-seven"),
    entry(
        UNNAMED,
        route(CURSOR, None),
        route(CLAUDE, f"{UNNAMED}-{CLAUDE}"),
        family="family-eight",
    ),
    entry(
        BLOCKED_ROUTE,
        route(CODEX, f"{BLOCKED_ROUTE}-{CODEX}", access="blocked"),
        route(CLAUDE, f"{BLOCKED_ROUTE}-{CLAUDE}"),
        family="family-nine",
    ),
    entry(
        ALIAS,
        route(
            CLAUDE,
            f"{ALIAS}-{CLAUDE}",
            kind="alias",
            resolves_to="example-alias-target",
        ),
        family="family-ten",
    ),
    entry(
        TWO_ROUTES,
        route(
            CLAUDE,
            "example-two-routes-first",
            access="blocked",
            also_known_as=["example-two-routes-first-alt"],
        ),
        route(
            CLAUDE,
            "example-two-routes-second",
            also_known_as=["example-two-routes-second-alt"],
        ),
        family="family-eleven",
    ),
]
EXCLUSION = exclusion(
    "blocked-example",
    aliases=["blocked-alias"],
    id_patterns=["blocked-model-*"],
    family_tags=["blocked-family"],
)
QUALITY = profile_doc("quality", mode="manual", candidates=[A, B])
ENGINEERING = profile_doc(
    "engineering",
    mode="automatic-with-fallbacks",
    candidates=[B, C],
    fallbacks=[D, A],
    escalation="quality",
)
ECONOMY = profile_doc("economy", mode="automatic", candidates=[C, D], escalation="engineering")
PROFILES = [QUALITY, ENGINEERING, ECONOMY]


def policy(
    *assignments: Doc,
    models: Sequence[Doc] = CATALOG,
    profiles: Sequence[Doc] = PROFILES,
    excluded: Sequence[Doc] = (EXCLUSION,),
) -> Doc:
    """A sound policy: the catalog above, the three profiles and one exclusion."""
    return {
        "schema": "orqlet.model-policy/v2",
        "policy_version": 1,
        "reviewed_for_release": "0.4.0",
        "models": list(models),
        "excluded": list(excluded),
        "profiles": list(profiles),
        "assignments": list(assignments),
    }


def raw_of(document: Doc) -> bytes:
    return json.dumps(document, indent=2).encode()


def pad(content: bytes, size: int) -> bytes:
    """`content` and comment lines of at most 80 bytes, so that the file has exactly `size` bytes.

    The lines are short because the reader of the policy refuses one line of thousands of
    characters (the `oversize` rule of its credential scan), which is not what these tests probe.
    """
    assert size >= len(content), "the content is longer than the size asked for"
    padded = bytearray(content)
    while len(padded) < size:
        width = min(80, size - len(padded))
        padded += b"\n" + b"#" + b"x" * (width - 2) if width >= 2 else b"\n"
    assert len(padded) == size
    return bytes(padded)


SEEDED = {"path": POLICY, "owner": "seeded", "seeded_sha256": "0" * 64}
OTHER_SEEDED = {"path": ".orqlet/role-bindings.yaml", "owner": "seeded", "seeded_sha256": "1" * 64}
TEAM_ROW = {"path": POLICY, "owner": "user", "rendered_sha256": "3" * 64}


def lock_bytes(*rows: Doc) -> bytes:
    document = {
        "schema": "orqlet.generated-lock/v1",
        "generator": {"orqlet": "0.4.0"},
        "files": list(rows),
    }
    return json.dumps(document, indent=2).encode()


def project(
    content: Doc | bytes | None = None, *, lock: Sequence[Doc] | bytes | None = None
) -> Files:
    """A project with the policy (a document, or the bytes of a file) and the lock."""
    tree = Files()
    if content is not None:
        raw = raw_of(content) if isinstance(content, dict) else content
        tree.write_atomic(CanonicalPath.parse(POLICY), raw)
    if lock is not None:
        data = lock if isinstance(lock, bytes) else lock_bytes(*lock)
        tree.write_atomic(CanonicalPath.parse(LOCK), data)
    return tree


# --- running the use case ----------------------------------------------------------------------


def ask(
    tree: Files,
    *,
    client: str = CLAUDE,
    kind: str = "role",
    name: str = TESTER,
    task: str | None = None,
    override: str | None = None,
    different_family_from: str | None = None,
    coder_profile: str | None = None,
    workflow: WorkflowSource | None = None,
) -> ModelsResult:
    """The use case on armed fakes: the file system fails on any access the readings forbid."""
    module = importlib.import_module(USECASE)
    tree.armed = True
    services = module.ModelsServices(
        project=tree, loader=LOADER, workflow=workflow if workflow is not None else WORKFLOW
    )
    query = module.ModelsQuery(
        client=client,
        kind=kind,
        name=name,
        task=task,
        override=override,
        different_family_from=different_family_from,
        coder_profile=coder_profile,
    )
    result: ModelsResult = module.models_resolve(services, query)
    return result


@dataclass
class Case:
    """A project and the query asked of it."""

    tree: Files
    query: dict[str, Any]


def run(case: Case) -> ModelsResult:
    return ask(case.tree, **case.query)


def data_of(result: ModelsResult) -> Doc:
    assert result.status != "refused", [(f.code, f.message) for f in result.findings]
    return dict(result.data)


def codes(result: ModelsResult) -> list[str]:
    return [finding.code for finding in result.findings]


def rejected_of(result: ModelsResult) -> list[tuple[str | None, str]]:
    return [(item["model"], item["reason"]) for item in data_of(result)["rejected"]]


def listed(
    model_id: str,
    client: str = CLAUDE,
    *,
    effort: str | None = None,
    kind: str = "id",
    also: Sequence[str] | None = None,
) -> Doc:
    """One entry of `candidates` or `fallbacks`: the catalog route of a model for a client."""
    known = ALSO.get((model_id, client), []) if also is None else list(also)
    return {
        "model": model_id,
        "name": f"{model_id}-{client}",
        "kind": kind,
        "effort": effort,
        "also_known_as": known,
    }


def chosen(entry_: Doc) -> Doc:
    """The `selection` that matches a listed entry: the same without `also_known_as`."""
    return {key: value for key, value in entry_.items() if key != "also_known_as"}


def rej(model_id: str | None, reason: str) -> Doc:
    return {"model": model_id, "reason": reason}


def shown(result: ModelsResult) -> str:
    """Everything that a result shows: its status, its data and each finding."""
    findings = [[f.code, f.severity.value, f.message, f.path, repr(f)] for f in result.findings]
    document = {"status": result.status, "data": result.data, "findings": findings}
    return json.dumps(document, ensure_ascii=False, sort_keys=True, default=str)


def leaked(text: str, secret: str, width: int = 10) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def marker(label: str) -> str:
    """A unique string for one field that is valid as a model string, a slug and a path part."""
    return "zq7mk-" + hashlib.sha256(label.encode()).hexdigest()[:12]


def names(finding: Finding, text: str) -> bool:
    """True when the finding names `text` in its path field or in its message."""
    return text in (finding.path or "") or text in finding.message


# --- the scenarios that most tests run on -------------------------------------------------------


def case_pinned() -> Case:
    return Case(project(policy(pinned(A, effort="high"))), {})


def case_profile_manual() -> Case:
    return Case(project(policy(via("quality"))), {})


def case_profile_automatic() -> Case:
    return Case(project(policy(via("economy", "automatic"))), {})


def case_profile_with_fallbacks() -> Case:
    return Case(project(policy(via("engineering", "automatic-with-fallbacks"))), {})


def case_profile_target() -> Case:
    return Case(project(policy()), {"kind": "profile", "name": "quality"})


def case_skill_target() -> Case:
    document = policy(assignment_doc("skill", DESIGN, profile="quality"))
    return Case(project(document), {"kind": "skill", "name": DESIGN})


def case_override_valid() -> Case:
    return Case(project(policy(via("quality"))), {"override": f"{B}-{CLAUDE}"})


def case_override_invalid() -> Case:
    return Case(project(policy(pinned(A))), {"override": f"{PROPOSED}-{CLAUDE}"})


def case_override_excluded() -> Case:
    return Case(project(policy()), {"override": "blocked-alias"})


def case_none_qualifies() -> Case:
    unusable = profile_doc("quality", candidates=[PROPOSED, RETIRED])
    return Case(project(policy(via("quality"), profiles=[unusable])), {})


def case_no_policy() -> Case:
    return Case(project(), {})


def case_no_policy_constrained() -> Case:
    return Case(project(), {"different_family_from": A})


def case_empty_policy() -> Case:
    return Case(project(policy(models=[], profiles=[], excluded=[])), {})


def case_unassigned() -> Case:
    return Case(project(policy(pinned(A))), {"name": INVENTORY})


def case_refused_invalid() -> Case:
    return Case(project(b"a: 1\na: 2\n"), {})


def case_refused_v1() -> Case:
    return Case(project(raw_of({"schema": "orqlet.model-policy/v1", "models": []})), {})


def case_refused_deleted() -> Case:
    return Case(project(lock=[SEEDED]), {})


def case_refused_excluded() -> Case:
    leaking = entry("blocked-model-1", *routes_of("blocked-model-1"))
    return Case(project(policy(models=[*CATALOG, leaking])), {})


def case_refused_reference() -> Case:
    return Case(project(policy(assignment_doc("role", "no-such-role", model=A))), {})


# name -> (the scenario, the status that its use case result has)
OK_SCENARIOS: dict[str, tuple[Callable[[], Case], str]] = {
    "pinned": (case_pinned, "selected"),
    "profile-manual": (case_profile_manual, "selected"),
    "profile-automatic": (case_profile_automatic, "automatic"),
    "profile-with-fallbacks": (case_profile_with_fallbacks, "automatic"),
    "profile-target": (case_profile_target, "selected"),
    "skill-target": (case_skill_target, "selected"),
    "override-valid": (case_override_valid, "selected"),
    "override-invalid": (case_override_invalid, "selected"),
    "override-excluded": (case_override_excluded, "none-qualifies"),
    "none-qualifies": (case_none_qualifies, "none-qualifies"),
    "no-policy": (case_no_policy, "automatic"),
    "no-policy-constrained": (case_no_policy_constrained, "none-qualifies"),
    "empty-policy": (case_empty_policy, "automatic"),
    "unassigned": (case_unassigned, "automatic"),
}
REFUSED_SCENARIOS: dict[str, Callable[[], Case]] = {
    "invalid": case_refused_invalid,
    "v1": case_refused_v1,
    "deleted": case_refused_deleted,
    "excluded": case_refused_excluded,
    "reference": case_refused_reference,
}
EVERY_SCENARIO = pytest.mark.parametrize(
    "name", [*OK_SCENARIOS, *(f"refused-{name}" for name in REFUSED_SCENARIOS)]
)
EVERY_RESULT = pytest.mark.parametrize("name", list(OK_SCENARIOS))
EVERY_REFUSAL = pytest.mark.parametrize("name", list(REFUSED_SCENARIOS))


def scenario(name: str) -> Case:
    if name.startswith("refused-"):
        return REFUSED_SCENARIOS[name.removeprefix("refused-")]()
    return OK_SCENARIOS[name][0]()


# Per problem of a policy that loads but is unsafe: the document, the code and the field path.
PROBLEMS: dict[str, tuple[Doc, str, str]] = {
    "excluded-route-name": (
        policy(
            models=[*CATALOG, entry("example-bad", route(CLAUDE, "blocked-alias"))],
        ),
        E543,
        f"models[{len(CATALOG)}]",
    ),
    "excluded-id-pattern": (
        policy(models=[entry("blocked-model-1", *routes_of("blocked-model-1")), *CATALOG]),
        E543,
        "models[0]",
    ),
    "excluded-family-tag": (
        policy(
            models=[
                *CATALOG,
                entry("example-tag", *routes_of("example-tag"), family="blocked-family-x"),
            ]
        ),
        E543,
        f"models[{len(CATALOG)}]",
    ),
    "unknown-role": (
        policy(assignment_doc("role", marker("role"), model=A)),
        E545,
        "assignments[0].target.name",
    ),
    "unknown-skill": (
        policy(assignment_doc("skill", marker("skill"), model=A)),
        E545,
        "assignments[0].target.name",
    ),
    "unknown-model": (
        policy(assignment_doc("role", TESTER, model="example-missing")),
        E545,
        "assignments[0].model",
    ),
    "unknown-candidate": (
        policy(profiles=[profile_doc("quality", candidates=["example-missing"])]),
        E545,
        "profiles[0].candidates[0].models[0]",
    ),
    "unknown-profile": (
        policy(via("quality"), profiles=[]),
        E545,
        "assignments[0].profile",
    ),
    "unknown-escalation": (
        policy(profiles=[profile_doc("quality", escalation="economy")]),
        E545,
        "profiles[0].escalation",
    ),
    "duplicate-model-id": (
        policy(models=[CATALOG[0], CATALOG[0]]),
        E545,
        "models[1].id",
    ),
    "two-models-claim-one-name": (
        policy(models=[CATALOG[0], entry("example-dup", route(CLAUDE, f"{A}-{CLAUDE}"))]),
        E545,
        "models[1]",
    ),
}


# --- premises: what the fixtures are, and what the domain gives for them -------------------------


def loaded(document: Doc) -> ModelPolicy:
    return load_contract(LOADER, ModelPolicy, raw_of(document), source=POLICY)


def test_the_premise_the_tester_role_and_the_design_skill_are_names_of_the_workflow() -> None:
    """Not a behaviour of the use case: the assignments of these tests name real workflow names,
    so a refusal is never an accident of a fixture. expected_behavior_source: R-1 (the names are
    those of the packaged workflow); the P-7 interface item 4 (five roles, six skills); P-13 AC-2
    and AC-3 (workflow 0.5.0 ships the roles `orqlet-code-reviewer` and `orqlet-pr-writer`)."""
    roles = {role.name for role in load_roles(WORKFLOW)}
    skills = {skill.name for skill in load_skills(WORKFLOW, frozenset())}

    assert roles == set(ROLES) | {"orqlet-code-reviewer", "orqlet-pr-writer"}
    assert skills == set(SKILLS)


def _loaded_documents() -> list[str]:
    """The scenarios that have a v2 policy file that loads."""
    found = []
    for name, (factory, _) in OK_SCENARIOS.items():
        raw = factory().tree.snapshot().get(POLICY)
        if raw is not None and json.loads(raw).get("schema") == "orqlet.model-policy/v2":
            found.append(name)
    return found


@pytest.mark.parametrize("name", _loaded_documents())
def test_the_premise_the_policies_of_the_loaded_scenarios_are_sound(name: str) -> None:
    """Not a behaviour of the use case: every policy that is meant to load is a valid contract and
    has no problem. expected_behavior_source: R-3 (`policy_problems` finds none)."""
    raw = OK_SCENARIOS[name][0]().tree.snapshot()[POLICY]

    assert policy_problems(loaded(json.loads(raw)), ROLES, SKILLS) == ()


@pytest.mark.parametrize(
    ("name", "expected"), [("excluded", {E543}), ("reference", {E545})], ids=["E543", "E545"]
)
def test_the_premise_the_policies_of_the_refusals_have_the_problems_they_name(
    name: str, expected: set[str]
) -> None:
    """Not a behaviour of the use case. expected_behavior_source: R-3 (ORQ-E543 an exclusion
    matches, ORQ-E545 a bad reference)."""
    raw = scenario(f"refused-{name}").tree.snapshot()[POLICY]

    found = policy_problems(loaded(json.loads(raw)), ROLES, SKILLS)

    assert {problem.code for problem in found} == expected


@pytest.mark.parametrize("name", list(PROBLEMS))
def test_the_premise_each_policy_with_a_problem_has_exactly_the_problem_it_names(
    name: str,
) -> None:
    """Not a behaviour of the use case. expected_behavior_source: R-3 (`policy_problems` returns
    the problem: ORQ-E543 for an exclusion, ORQ-E545 for a bad reference, at its field path)."""
    document, code, path = PROBLEMS[name]

    found = policy_problems(loaded(document), ROLES, SKILLS)

    assert {problem.code for problem in found} == {code}
    assert any(problem.path.startswith(path) or path.startswith(problem.path) for problem in found)


def _resolution_rows() -> list[Any]:
    """(policy, the query's extras, what the resolver gives) as (outcome, source, profile, mode,
    the model that is selected, the rejections as (model, reason))."""
    quality = via("quality")
    return [
        pytest.param(
            policy(pinned(A, effort="high")),
            {},
            ("selected", "role-assignment", None, "manual", A, []),
            id="pinned",
        ),
        pytest.param(
            policy(quality),
            {},
            ("selected", "profile-assignment", "quality", "manual", A, []),
            id="profile-manual",
        ),
        pytest.param(
            policy(via("economy", "automatic")),
            {},
            ("client-chooses", "automatic", "economy", "automatic", None, []),
            id="profile-automatic",
        ),
        pytest.param(
            policy(pinned(PROPOSED), quality),
            {},
            (
                "selected",
                "profile-assignment",
                "quality",
                "manual",
                A,
                [(PROPOSED, "not-approved")],
            ),
            id="an-invalid-pin-falls-to-the-profile",
        ),
        # The resolver's own reason for an override that fails is `not-approved`; the use case
        # turns it into `override-invalid` (R-4).
        pytest.param(
            policy(pinned(A)),
            {"override": f"{PROPOSED}-{CLAUDE}"},
            ("selected", "role-assignment", None, "manual", A, [(PROPOSED, "not-approved")]),
            id="an-invalid-override-falls-to-the-pin",
        ),
        pytest.param(
            policy(pinned(A)),
            {"override": f"{B}-{CLAUDE}"},
            ("selected", "task-override", None, None, B, []),
            id="a-valid-override",
        ),
        pytest.param(
            policy(),
            {"override": "blocked-alias"},
            ("none-qualifies", "automatic", None, None, None, [(None, "excluded")]),
            id="an-excluded-override",
        ),
    ]


@pytest.mark.parametrize(("document", "extra", "expected"), _resolution_rows())
def test_the_premise_the_domain_resolves_the_fixtures_as_the_tests_expect(
    document: Doc, extra: dict[str, Any], expected: tuple[Any, ...]
) -> None:
    """Not a behaviour of the use case: the resolution that the use case maps. The reason of an
    override is the resolver's own here (`not-approved`, `excluded`), which R-4 says the use case
    turns into `override-invalid`. expected_behavior_source: tests/unit/domain/
    test_model_resolution.py and ADR-001 decisions 3, 4 and 5."""
    request = ResolveRequest(client=CLAUDE, target_kind="role", target=TESTER, **extra)

    resolution = resolve(to_resolver_policy(loaded(document)), request)

    outcome, source, profile, mode, picked, rejections = expected
    assert resolution.outcome == outcome
    assert resolution.source == source
    assert resolution.profile == profile
    assert resolution.mode == mode
    assert (None if resolution.selected is None else resolution.selected.model) == picked
    assert [(r.model, r.reason) for r in resolution.rejected] == rejections


# --- the interface: the services, the query and the result ---------------------------------------


def assign(target: object, name: str, value: object) -> None:
    """An assignment that the type checker does not see, to try a frozen object."""
    setattr(target, name, value)


def test_the_services_are_a_frozen_slotted_dataclass_of_three_ports_in_order() -> None:
    """AC-5/R-10a. expected_behavior_source: AC-5 ("a services object with the project file
    system, the strict loader and the workflow package"); R-10a (the field names are exactly
    `project`, `loader`, `workflow`); the interface (frozen, slotted, in this order)."""
    module = importlib.import_module(USECASE)
    fields = dataclasses.fields(module.ModelsServices)

    assert tuple(f.name for f in fields) == ("project", "loader", "workflow")
    assert all(
        f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        for f in fields
    )
    assert "__slots__" in vars(module.ModelsServices)
    services = module.ModelsServices(project=Files(), loader=LOADER, workflow=WORKFLOW)
    with pytest.raises(dataclasses.FrozenInstanceError):
        assign(services, "workflow", CountingWorkflow())


@pytest.mark.parametrize("extra", ["vcs", "process", "runner", "clock"])
def test_the_services_take_no_vcs_no_process_runner_and_no_clock(extra: str) -> None:
    """AC-5/R-10a. expected_behavior_source: AC-5 ("and no VCS, process runner or clock"); R-1
    ("makes no git call and starts no process, and reads no clock"). A field for any of them is
    refused by the constructor."""
    module = importlib.import_module(USECASE)

    with pytest.raises(TypeError):
        module.ModelsServices(project=Files(), loader=LOADER, workflow=WORKFLOW, **{extra: None})


def test_the_query_is_a_frozen_dataclass_with_the_target_and_four_optional_values() -> None:
    """AC-1/AC-2. expected_behavior_source: the interface (`ModelsQuery(client, kind, name, task,
    override, different_family_from, coder_profile)`, frozen, the last four default to none)."""
    module = importlib.import_module(USECASE)
    fields = dataclasses.fields(module.ModelsQuery)

    assert tuple(f.name for f in fields) == (
        "client",
        "kind",
        "name",
        "task",
        "override",
        "different_family_from",
        "coder_profile",
    )
    query = module.ModelsQuery(CLAUDE, "role", TESTER)
    assert (query.task, query.override, query.different_family_from, query.coder_profile) == (
        None,
        None,
        None,
        None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        assign(query, "client", CODEX)


def test_the_result_is_a_frozen_dataclass_of_status_data_and_findings() -> None:
    """AC-2/R-3. expected_behavior_source: the interface (`ModelsResult(status, data,
    findings=())`, frozen)."""
    module = importlib.import_module(USECASE)
    fields = dataclasses.fields(module.ModelsResult)

    assert tuple(f.name for f in fields) == ("status", "data", "findings")
    assert fields[2].default == ()
    result = module.ModelsResult("automatic", {})
    assert result.findings == ()
    with pytest.raises(dataclasses.FrozenInstanceError):
        assign(result, "status", "refused")


# --- AC-5, R-1, R-10: what the use case may touch -----------------------------------------------


def test_a_present_policy_is_read_and_neither_the_lock_nor_any_other_file_is_touched() -> None:
    """AC-5/R-1/R-10a. expected_behavior_source: R-1 ("The lock is read only when the policy file
    is missing"); R-10a (a file system that fails on any path other than the policy and the
    lock, and on the lock when the policy is present)."""
    tree = project(policy(pinned(A)), lock=[SEEDED])

    ask(tree)

    assert set(tree.touched) == {POLICY}
    assert set(tree.reads) == {POLICY}


@pytest.mark.parametrize(
    ("lock", "reads"),
    [
        pytest.param(None, [], id="no-lock"),
        pytest.param([OTHER_SEEDED], [LOCK], id="a-lock-that-does-not-list-the-policy"),
        pytest.param([SEEDED], [LOCK], id="a-lock-that-lists-the-policy-as-seeded"),
    ],
)
def test_a_missing_policy_makes_the_use_case_look_at_the_lock_and_at_nothing_else(
    lock: list[Doc] | None, reads: list[str]
) -> None:
    """AC-5/R-1/R-10a. expected_behavior_source: R-1 (the lock is read when the policy file is
    missing, through the one reader); R-10a (the only paths are the policy and the lock)."""
    tree = project(lock=lock)

    ask(tree)

    assert set(tree.touched) == {POLICY, LOCK}
    assert set(tree.reads) == set(reads)


@EVERY_SCENARIO
def test_the_use_case_never_writes_deletes_or_makes_a_folder(name: str) -> None:
    """AC-5/R-10a. expected_behavior_source: R-10a ("a file system that raises on any write,
    delete or make-dir"); BC-23 ("read-only"). The armed file system raises on any of them and
    on a listing, and the files are the same afterwards."""
    case = scenario(name)
    before = case.tree.snapshot()

    run(case)

    assert case.tree.snapshot() == before


@pytest.mark.parametrize("state", ["absent", "deleted", "invalid", "v1"])
def test_the_workflow_is_not_read_when_no_policy_is_loaded(state: str) -> None:
    """AC-5/R-1/R-10a. expected_behavior_source: R-1 ("The workflow is the packaged data: only its
    role and skill names are read, and only when a policy is present and loaded")."""
    cases = {
        "absent": project(),
        "deleted": project(lock=[SEEDED]),
        "invalid": project(b"a: 1\na: 2\n"),
        "v1": project(raw_of({"schema": "orqlet.model-policy/v1", "models": []})),
    }
    workflow = CountingWorkflow()

    ask(cases[state], workflow=workflow)

    assert workflow.calls == []


def test_the_workflow_is_read_for_its_names_when_a_policy_is_loaded() -> None:
    """AC-5/R-1/R-3. expected_behavior_source: R-1 (the role and skill names are the names against
    which `policy_problems` checks the assignments, so they are read when a policy is loaded)."""
    workflow = CountingWorkflow()

    ask(project(policy(pinned(A))), workflow=workflow)

    assert workflow.calls != []


def test_a_run_on_the_fakes_opens_no_socket() -> None:
    """AC-5. expected_behavior_source: AC-5 (no process, no clock; the tests run offline);
    pyproject.toml addopts `--disable-socket`: a socket opened by the use case would fail."""
    # With `filterwarnings = error` the blocked-socket warning is what is raised.
    with pytest.raises((RuntimeError, UserWarning), match="socket"):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    assert ask(project(policy(pinned(A)))).status == "selected"


def test_the_use_case_imports_no_clock_no_process_no_file_module_and_never_locates_a_base() -> None:
    """AC-5/R-10d. expected_behavior_source: R-10d (the source imports none of `datetime`, `time`,
    `subprocess`, `socket`, `os`, `pathlib`, the clock, vcs and process ports, and does not import
    `locate` from binding_inputs); BC-23."""
    tree = ast.parse(SOURCE_FILE.read_text(encoding="utf-8"))
    forbidden = (
        "datetime",
        "time",
        "subprocess",
        "socket",
        "os",
        "pathlib",
        "orqlet.application.ports.clock",
        "orqlet.application.ports.vcs",
        "orqlet.application.ports.process",
    )
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            imported += [base, *(f"{base}.{alias.name}" for alias in node.names)]

    bad = [
        name
        for name in imported
        if any(name == word or name.startswith(f"{word}.") for word in forbidden)
    ]
    located = [
        node
        for node in ast.walk(tree)
        if (isinstance(node, ast.ImportFrom) and any(a.name == "locate" for a in node.names))
        or (isinstance(node, ast.Name) and node.id == "locate")
    ]
    assert bad == []
    assert located == []


# --- AC-2, R-6: the data -----------------------------------------------------------------------


@EVERY_RESULT
def test_the_data_has_exactly_the_keys_of_the_criterion(name: str) -> None:
    """AC-2/R-6. expected_behavior_source: AC-2 ("The `data` ... has exactly these keys"); R-6."""
    result = run(scenario(name))

    assert set(result.data) == DATA_KEYS
    assert set(data_of(result)["target"]) == {"kind", "name"}


@EVERY_RESULT
def test_every_nested_object_has_exactly_the_keys_of_the_criterion(name: str) -> None:
    """AC-2/R-6. expected_behavior_source: AC-2 (`selection`: `model`, `name`, `kind`, `effort`;
    `candidates` and `fallbacks`: the same with `also_known_as`; `list_prices`: `model`,
    `input_per_million_usd`, `output_per_million_usd`; `rejected`: `model` and `reason`)."""
    data = data_of(run(scenario(name)))

    if data["selection"] is not None:
        assert set(data["selection"]) == SELECTION_KEYS
    for item in (*data["candidates"], *data["fallbacks"]):
        assert set(item) == ENTRY_KEYS
        assert isinstance(item["also_known_as"], list)
    for item in data["list_prices"]:
        assert set(item) == PRICE_KEYS
    for item in data["rejected"]:
        assert set(item) == {"model", "reason"}


@EVERY_RESULT
def test_the_data_is_json_ready_with_lists_and_never_tuples(name: str) -> None:
    """AC-2/R-6. expected_behavior_source: R-6 and the interface ("JSON-ready: strings, booleans,
    None, lists of dicts; lists, never tuples"); AC-2 ("Keys are sorted": the CLI sorts them)."""
    result = run(scenario(name))

    json.dumps(result.data)  # a plain value: the envelope prints it

    def check(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                assert isinstance(key, str)
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)
        else:
            assert node is None or isinstance(node, str | bool), repr(node)

    check(result.data)


@EVERY_RESULT
def test_the_values_of_the_data_are_of_the_documented_kinds(name: str) -> None:
    """AC-2/R-6. expected_behavior_source: AC-2 (`policy` is `present` or `absent`, `client_chooses`
    a boolean, `result` one of three words, `rejected` reasons of the closed set, a profile id)."""
    data = data_of(run(scenario(name)))

    assert data["policy"] in {"present", "absent"}
    assert isinstance(data["client_chooses"], bool)
    assert data["result"] in {"selected", "automatic", "none-qualifies"}
    assert data["source"] in {
        "task-override",
        "role-assignment",
        "profile-assignment",
        "automatic",
        "explicit-fallback",
    }
    assert data["profile"] in {None, "quality", "engineering", "economy"}
    assert data["mode"] in {None, *MODES}
    assert data["escalation"] in {None, "quality", "engineering", "economy"}
    assert isinstance(data["hint"], str)
    assert {item["reason"] for item in data["rejected"]} <= SHOWN_REASONS


@pytest.mark.parametrize("name", list(OK_SCENARIOS))
def test_the_result_word_follows_the_outcome_and_client_chooses_follows_the_result(
    name: str,
) -> None:
    """AC-2/R-6/R-7. expected_behavior_source: R-6 (`result` is selected for a selection, automatic
    for client-chooses, none-qualifies for none; `client_chooses` is true exactly for
    client-chooses); R-7 (the status is `selected`, `automatic` or `none-qualifies`)."""
    factory, status = OK_SCENARIOS[name]

    result = run(factory())
    data = data_of(result)

    assert result.status == status
    assert data["result"] == status
    assert data["client_chooses"] is (status == "automatic")
    assert (data["selection"] is not None) is (status == "selected")
    assert result.findings == ()


def test_the_data_echoes_the_client_the_target_and_the_task() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (`client` is the query's client, `target` is
    `{"kind": ..., "name": ...}`, `task` the query's task or null)."""
    document = policy(via("quality", task="t-one"))

    with_task = data_of(ask(project(document), client=CODEX, task="t-one"))
    without = data_of(ask(project(document), client=CURSOR, kind="skill", name=DESIGN))

    assert with_task["client"] == CODEX
    assert with_task["target"] == {"kind": "role", "name": TESTER}
    assert with_task["task"] == "t-one"
    assert without["client"] == CURSOR
    assert without["target"] == {"kind": "skill", "name": DESIGN}
    assert without["task"] is None


def test_the_policy_word_is_present_when_a_policy_file_was_loaded() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (`policy` is "present" when a policy file was
    loaded); a policy with no models and no assignments is a policy."""
    assert data_of(ask(project(policy())))["policy"] == "present"
    assert data_of(ask(project(policy(models=[], profiles=[], excluded=[]))))["policy"] == "present"


# --- AC-2/AC-3: the three modes, on a role and on a profile ---------------------------------------


def test_manual_mode_selects_the_first_eligible_candidate_and_keeps_the_candidates() -> None:
    """AC-2/AC-3/R-6/R-12. expected_behavior_source: ADR-001 decision 3 (`manual`: the first
    eligible candidate in the approved order is pinned); R-6 (`selection`, `candidates` in order,
    `fallbacks` of the resolution, the source `profile-assignment`)."""
    data = data_of(run(case_profile_manual()))

    assert data["result"] == "selected"
    assert data["selection"] == chosen(listed(A))
    assert data["candidates"] == [listed(A), listed(B)]
    assert data["fallbacks"] == []
    assert (data["profile"], data["mode"], data["source"]) == (
        "quality",
        "manual",
        "profile-assignment",
    )
    assert data["escalation"] is None


def test_automatic_mode_selects_nothing_and_lists_the_candidates_and_the_escalation() -> None:
    """AC-2/AC-3/R-6/R-12. expected_behavior_source: ADR-001 decision 3 (`automatic`: no pin, the
    client's own selection applies); decision 4 (the recorded source is `automatic`); R-6
    (`client_chooses` true; the profile's `escalation` is shown)."""
    data = data_of(run(case_profile_automatic()))

    assert data["result"] == "automatic"
    assert data["client_chooses"] is True
    assert data["selection"] is None
    assert data["candidates"] == [listed(C), listed(D)]
    assert data["fallbacks"] == []
    assert (data["profile"], data["mode"], data["source"]) == (
        "economy",
        "automatic",
        "automatic",
    )
    assert data["escalation"] == "engineering"


def test_automatic_with_fallbacks_lists_the_candidates_and_the_ordered_fallbacks() -> None:
    """AC-2/AC-3/R-6/R-12. expected_behavior_source: ADR-001 decision 3 (`automatic-with-fallbacks`
    is `automatic` plus an ordered fallback list that `models resolve` returns); BC-27; R-6."""
    data = data_of(run(case_profile_with_fallbacks()))

    assert data["result"] == "automatic"
    assert data["selection"] is None
    assert data["candidates"] == [listed(B), listed(C)]
    assert data["fallbacks"] == [listed(D), listed(A)]
    assert (data["profile"], data["mode"], data["source"]) == (
        "engineering",
        "automatic-with-fallbacks",
        "automatic",
    )
    assert data["escalation"] == "quality"


@pytest.mark.parametrize(
    ("profile_id", "result", "mode"),
    [
        ("quality", "selected", "manual"),
        ("engineering", "automatic", "automatic-with-fallbacks"),
        ("economy", "automatic", "automatic"),
    ],
)
def test_a_profile_target_resolves_the_profile_itself_in_its_own_mode(
    profile_id: str, result: str, mode: str
) -> None:
    """AC-2/R-12. expected_behavior_source: R-12 ("A profile target (`--profile P`) resolves the
    profile itself"); ADR-001 decision 4 (level 3: for a profile request, the profile itself)."""
    data = data_of(ask(project(policy()), kind="profile", name=profile_id))

    assert (data["profile"], data["mode"], data["result"]) == (profile_id, mode, result)
    assert data["target"] == {"kind": "profile", "name": profile_id}


def test_a_profile_that_the_policy_does_not_define_is_a_target_with_no_levels() -> None:
    """AC-2/AC-4/R-12. expected_behavior_source: R-12 ("a profile id that the policy does not define
    is a target with no levels (status automatic, hint "no assignment for this target; the client
    chooses" when a policy is present)")."""
    document = policy(profiles=[profile_doc("economy", mode="automatic", candidates=[C, D])])

    result = ask(project(document), kind="profile", name="quality")
    data = data_of(result)

    assert result.status == "automatic"
    assert (data["profile"], data["mode"], data["selection"]) == (None, None, None)
    assert data["candidates"] == []
    assert data["fallbacks"] == []
    assert data["hint"] == NO_ASSIGNMENT


@pytest.mark.parametrize("client", CLIENTS)
def test_every_client_gets_its_own_route_name(client: str) -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (`name` is the catalog route of the model for the
    queried client); BC-3 (each client carries its own client's name)."""
    data = data_of(ask(project(policy(pinned(B))), client=client))

    assert data["client"] == client
    assert data["selection"] == chosen(listed(B, client))
    assert data["candidates"] == [listed(B, client)]


@pytest.mark.parametrize("client", CLIENTS)
def test_every_client_resolves_a_profile_with_its_own_candidates(client: str) -> None:
    """AC-2/R-6/R-12. expected_behavior_source: R-6; the resolver takes the candidates of the
    queried client (ADR-002 decision 3: ordered candidates per client)."""
    lists = {CLAUDE: [A, B], CODEX: [B, A], CURSOR: [C]}
    document = policy(via("quality"), profiles=[profile_doc("quality", candidates=lists)])

    data = data_of(ask(project(document), client=client))

    assert [item["model"] for item in data["candidates"]] == lists[client]
    assert data["selection"] == chosen(listed(lists[client][0], client))


# --- R-6: also_known_as, the kind, the route, the prices -----------------------------------------


def test_also_known_as_is_the_list_of_the_route_of_the_client() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (`also_known_as` is the list of `also_known_as` of
    the route of that catalog model for the queried client whose name is the entry's name)."""
    document = policy(via("quality"))

    claude = data_of(ask(project(document), client=CLAUDE))
    codex = data_of(ask(project(document), client=CODEX))

    assert claude["candidates"][0]["also_known_as"] == [ALSO_A]
    assert codex["candidates"][0]["also_known_as"] == []


def test_also_known_as_is_that_of_the_route_whose_name_was_chosen() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 ("the route ... whose name is the entry's name"): a
    model with two routes for one client is offered through its first route that is not blocked,
    and the list is the one of that route and not of the blocked one."""
    data = data_of(ask(project(policy(pinned(TWO_ROUTES)))))

    assert data["selection"] == {
        "model": TWO_ROUTES,
        "name": "example-two-routes-second",
        "kind": "id",
        "effort": None,
    }
    assert data["candidates"][0]["name"] == "example-two-routes-second"
    assert data["candidates"][0]["also_known_as"] == ["example-two-routes-second-alt"]


def test_an_alias_route_is_shown_as_an_alias() -> None:
    """AC-2/R-6. expected_behavior_source: AC-2 (`kind` of `selection` and of each entry); ADR-002
    decision 3 (a route is of kind `id` or `alias`); BC-28."""
    data = data_of(ask(project(policy(pinned(ALIAS)))))

    assert data["selection"] == {
        "model": ALIAS,
        "name": f"{ALIAS}-{CLAUDE}",
        "kind": "alias",
        "effort": None,
    }
    assert data["candidates"][0]["kind"] == "alias"


def test_list_prices_hold_one_entry_for_each_distinct_model_that_has_a_price() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (`list_prices` is one entry `{model,
    input_per_million_usd, output_per_million_usd}` for each distinct catalog model of the
    selection, the candidates and the fallbacks that has a `list_price`; a model with none has no
    entry); ADR-002 decision 3 (list prices are shown by `models resolve`)."""
    data = data_of(run(case_profile_manual()))  # selected A, candidates A and B

    assert data["list_prices"] == [
        {"model": A, "input_per_million_usd": "3", "output_per_million_usd": "15"}
    ]


def test_list_prices_follow_the_order_of_first_appearance_in_the_candidates_and_fallbacks() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 ("in the order of first appearance among the
    selection, the candidates and the fallbacks"). Candidates B (no price) and C, fallbacks D (no
    price) and A: the entries are C then A."""
    data = data_of(run(case_profile_with_fallbacks()))

    assert [item["model"] for item in data["list_prices"]] == [C, A]
    assert data["list_prices"][0] == {
        "model": C,
        "input_per_million_usd": "0.25",
        "output_per_million_usd": "1.25",
    }


def test_a_model_that_appears_twice_has_one_price_entry() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 ("one entry ... for each distinct catalog model").
    A is the first candidate and also a fallback."""
    both = profile_doc("quality", mode="automatic-with-fallbacks", candidates=[A, B], fallbacks=[A])
    document = policy(via("quality", "automatic-with-fallbacks"), profiles=[both])

    data = data_of(ask(project(document)))

    assert [item["model"] for item in data["candidates"]] == [A, B]
    assert [item["model"] for item in data["fallbacks"]] == [A]
    assert [item["model"] for item in data["list_prices"]] == [A]


def test_a_run_with_no_model_of_a_price_has_no_list_prices() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (a model with no list price has no entry)."""
    data = data_of(ask(project(policy(pinned(B)))))

    assert data["list_prices"] == []


# --- precedence: the four levels (ADR-001 decision 4, R-12) --------------------------------------


def test_a_pin_on_one_model_beats_a_profile_assignment_whatever_the_order_of_the_file() -> None:
    """AC-2/R-12. expected_behavior_source: ADR-001 decision 4 (level 2, an assignment that names
    one model, beats level 3, one that names a profile); R-12 ("a model pin level 2, a profile
    level 3, precedence"). The profile assignment comes first in the file."""
    data = data_of(ask(project(policy(via("quality"), pinned(B)))))

    assert data["source"] == "role-assignment"
    assert data["selection"] == chosen(listed(B))
    assert data["profile"] is None
    assert data["mode"] == "manual"


def test_an_invalid_pin_gives_way_to_the_profile_with_a_visible_rejection() -> None:
    """AC-2/AC-6/R-12. expected_behavior_source: ADR-001 decision 4 ("A choice at level 1 to 3
    that fails a constraint is reported with its reason and is never replaced by a lower level
    without a visible finding"); BC-5."""
    data = data_of(ask(project(policy(pinned(PROPOSED), via("quality")))))

    assert data["source"] == "profile-assignment"
    assert data["selection"] == chosen(listed(A))
    assert data["profile"] == "quality"
    assert data["rejected"] == [rej(PROPOSED, "not-approved")]


def test_a_pin_and_a_profile_that_both_fail_leave_nothing_that_qualifies() -> None:
    """AC-2/AC-3/R-12. expected_behavior_source: ADR-001 decision 4 ("When no level is valid and
    one was present, nothing qualifies": resolver module docstring); BC-4 (the reasons are
    listed). The profile's own list holds a disabled model only."""
    unusable = profile_doc("quality", candidates=[DISABLED])
    document = policy(pinned(PROPOSED), via("quality"), profiles=[unusable])

    result = ask(project(document))
    data = data_of(result)

    assert result.status == "none-qualifies"
    assert data["selection"] is None
    assert data["client_chooses"] is False
    assert data["rejected"] == [rej(PROPOSED, "not-approved"), rej(DISABLED, "disabled-or-retired")]


def test_an_assignment_that_the_policy_does_not_make_leaves_the_client_to_choose() -> None:
    """AC-2/AC-3/R-12. expected_behavior_source: ADR-001 decision 4 (level 4, the client's own
    automatic selection); decision 2 (the default is `automatic`)."""
    result = run(case_unassigned())
    data = data_of(result)

    assert result.status == "automatic"
    assert (data["profile"], data["mode"], data["source"]) == (None, None, "automatic")
    assert data["selection"] is None
    assert data["candidates"] == []
    assert data["rejected"] == []
    assert data["list_prices"] == []


def test_a_valid_override_beats_every_team_level() -> None:
    """AC-2/AC-6/R-4/R-12. expected_behavior_source: ADR-001 decision 4 (level 1, an override,
    beats the others); R-4 ("A valid override that is selected gives `source` "task-override" and
    `result` "selected""). The route name that is shown is the catalog's."""
    document = policy(pinned(A), via("quality"))

    result = ask(project(document), override=f"{B}-{CLAUDE}")
    data = data_of(result)

    assert result.status == "selected"
    assert (data["source"], data["result"]) == ("task-override", "selected")
    assert data["selection"] == chosen(listed(B))
    assert data["rejected"] == []


def test_a_valid_override_is_shown_with_the_name_of_the_catalog_route_and_not_its_own_text() -> (
    None
):
    """AC-6/R-4/R-9. expected_behavior_source: AC-6 ("the output never prints the override
    string, only catalog ids that passed `ModelRef` and fixed words"); R-4. A spelling that the
    route lists as `also_known_as`, and one with a bracketed option list, both name model A."""
    for override in (ALSO_A, f"{A}-{CLAUDE}[effort=high]", f"{A}-{CLAUDE.upper()}"):
        data = data_of(ask(project(policy(pinned(B))), override=override))

        assert data["source"] == "task-override"
        assert data["selection"] == chosen(listed(A))


def test_an_override_ends_the_resolution_and_leaves_no_candidates() -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (`profile`, `mode`, `source`, `escalation` come from
    the resolver's `Resolution`; a valid override returns a resolution with no profile, no mode,
    no candidate and no escalation)."""
    data = data_of(run(case_override_valid()))

    assert (data["profile"], data["mode"], data["escalation"]) == (None, None, None)
    assert data["candidates"] == []
    assert data["fallbacks"] == []


# --- precedence: the task and the client of an assignment (R-11) ----------------------------------


@pytest.mark.parametrize(
    ("task", "profile_id"),
    [("t-one", "quality"), ("t-two", "economy"), (None, "economy")],
    ids=["the-named-task", "another-task", "no-task"],
)
def test_an_assignment_that_names_a_task_applies_only_to_that_task(
    task: str | None, profile_id: str
) -> None:
    """AC-4/R-11. expected_behavior_source: ADR-001 decision 7 ("`models resolve --task` applies
    it"); R-11 ("applies only when `task` is T; with another or no task it is ignored"). The role
    has a general assignment to `economy` and one for `t-one` to `quality`."""
    document = policy(
        assignment_doc("role", TESTER, profile="economy", mode="automatic"),
        via("quality", task="t-one"),
    )

    data = data_of(ask(project(document), task=task))

    assert data["profile"] == profile_id
    assert data["task"] == task
    assert data["hint"] == suggested(profile_id)


def test_an_assignment_for_a_task_alone_is_ignored_without_that_task() -> None:
    """AC-4/R-11. expected_behavior_source: AC-4 ("An assignment that names a `task` appears only
    when `--task` names that task"); BC-43; R-11."""
    document = policy(via("quality", task="t-one"))

    without = data_of(ask(project(document)))
    other = data_of(ask(project(document), task="t-two"))
    named = data_of(ask(project(document), task="t-one"))

    for ignored in (without, other):
        assert ignored["profile"] is None
        assert ignored["selection"] is None
        assert ignored["hint"] == NO_ASSIGNMENT
    assert named["profile"] == "quality"
    assert named["selection"] == chosen(listed(A))


def test_the_assignment_of_a_task_beats_the_general_one_of_the_same_level() -> None:
    """AC-2/R-11. expected_behavior_source: the resolver's order of applicable assignments (a
    task, then a client) used through `to_resolver_policy` (not `to_render_policy`), R-3."""
    document = policy(pinned(A), pinned(B, task="t-one"))

    assert data_of(ask(project(document), task="t-one"))["selection"] == chosen(listed(B))
    assert data_of(ask(project(document)))["selection"] == chosen(listed(A))


def test_an_assignment_for_one_client_does_not_apply_to_the_others() -> None:
    """AC-2/R-12. expected_behavior_source: R-12 ("`client` of an assignment"); ADR-002 decision 3
    (an assignment has an optional `client`)."""
    document = policy(pinned(A, client=CODEX))

    codex = data_of(ask(project(document), client=CODEX))
    claude = data_of(ask(project(document), client=CLAUDE))

    assert codex["selection"] == chosen(listed(A, CODEX))
    assert claude["selection"] is None
    assert claude["hint"] == NO_ASSIGNMENT


def test_an_assignment_for_a_client_beats_the_general_assignment_for_that_client() -> None:
    """AC-2/R-12. expected_behavior_source: R-12 (precedence, `client` of an assignment); the
    resolver's order (a task, then a client)."""
    document = policy(pinned(B), pinned(A, client=CODEX))

    assert data_of(ask(project(document), client=CODEX))["selection"] == chosen(listed(A, CODEX))
    assert data_of(ask(project(document), client=CLAUDE))["selection"] == chosen(listed(B))


def test_the_effort_of_an_assignment_is_the_effort_of_the_selection_and_every_candidate() -> None:
    """AC-2/R-12. expected_behavior_source: R-12 ("`effort`"); AC-2 (`effort` of `selection` and of
    each entry); ADR-002 decision 3 (an assignment has an optional `effort`)."""
    document = policy(via("quality", effort="xhigh"))

    data = data_of(ask(project(document)))

    assert data["selection"] == chosen(listed(A, effort="xhigh"))
    assert [item["effort"] for item in data["candidates"]] == ["xhigh", "xhigh"]


def test_a_skill_is_resolved_through_the_assignments_of_kind_skill_and_a_role_through_roles() -> (
    None
):
    """AC-2/R-12. expected_behavior_source: R-12 ("`--skill` and `--role` targets are resolved
    through the assignments of the policy exactly as the resolver does (an assignment of kind skill
    or role"). A role assignment does not apply to a skill of that name, nor the other way."""
    document = policy(
        assignment_doc("role", TESTER, model=A),
        assignment_doc("skill", DESIGN, model=B),
    )

    skill = data_of(ask(project(document), kind="skill", name=DESIGN))
    role = data_of(ask(project(document), kind="role", name=TESTER))
    skill_named_like_the_role = data_of(ask(project(document), kind="skill", name=TESTER))
    role_named_like_the_skill = data_of(ask(project(document), kind="role", name=DESIGN))

    assert skill["selection"] == chosen(listed(B))
    assert skill["target"] == {"kind": "skill", "name": DESIGN}
    assert role["selection"] == chosen(listed(A))
    assert skill_named_like_the_role["selection"] is None
    assert role_named_like_the_skill["selection"] is None


def test_a_role_or_skill_that_the_workflow_does_not_have_is_a_target_with_no_assignment() -> None:
    """AC-1/R-2/R-12. expected_behavior_source: R-2 ("Role and skill names are NOT checked against
    the workflow ... `--role orqlet-code-reviewer` and `--role some-unknown-slug` are accepted");
    R-12 (a target that no assignment names)."""
    for kind, name in (
        ("role", "orqlet-code-reviewer"),
        ("role", "some-unknown-slug"),
        ("skill", "some-unknown-slug"),
    ):
        result = ask(project(policy(pinned(A))), kind=kind, name=name)

        assert result.status == "automatic", (kind, name)
        assert data_of(result)["hint"] == NO_ASSIGNMENT


# --- AC-6, R-4: the reasons, the override and the excluded model --------------------------------

# Per reason of the closed set that can be shown: a policy, the query and the rejection it shows.
REASON_CASES: dict[str, tuple[Doc, dict[str, Any], tuple[str | None, str]]] = {
    "not-approved": (
        policy(via("quality"), profiles=[profile_doc("quality", candidates=[PROPOSED, A])]),
        {},
        (PROPOSED, "not-approved"),
    ),
    "disabled": (
        policy(via("quality"), profiles=[profile_doc("quality", candidates=[DISABLED, A])]),
        {},
        (DISABLED, "disabled-or-retired"),
    ),
    "retired": (
        policy(via("quality"), profiles=[profile_doc("quality", candidates=[RETIRED, A])]),
        {},
        (RETIRED, "disabled-or-retired"),
    ),
    "no-route-for-client": (
        policy(via("quality"), profiles=[profile_doc("quality", candidates=[CLAUDE_ONLY, A])]),
        {"client": CODEX},
        (CLAUDE_ONLY, "no-route-for-client"),
    ),
    "route-name-unknown": (
        policy(via("quality"), profiles=[profile_doc("quality", candidates=[UNNAMED, A])]),
        {"client": CURSOR},
        (UNNAMED, "route-name-unknown"),
    ),
    "access-blocked": (
        policy(via("quality"), profiles=[profile_doc("quality", candidates=[BLOCKED_ROUTE, A])]),
        {"client": CODEX},
        (BLOCKED_ROUTE, "access-blocked"),
    ),
    "same-model-as-coder": (
        policy(via("quality"), profiles=[profile_doc("quality", candidates=[A, B])]),
        {"different_family_from": A},
        (A, "same-model-as-coder"),
    ),
    "same-family-as-coder": (
        policy(via("quality"), profiles=[profile_doc("quality", candidates=[C, B])]),
        {"different_family_from": A},
        (C, "same-family-as-coder"),
    ),
    "outside-profile": (
        policy(
            via("economy", "automatic"),
            profiles=[
                QUALITY,
                ENGINEERING,
                profile_doc("economy", mode="automatic", candidates=[C, D]),
            ],
        ),
        {"coder_profile": "engineering"},
        (D, "outside-profile"),
    ),
    "override-invalid": (
        policy(pinned(A)),
        {"override": f"{PROPOSED}-{CLAUDE}"},
        (PROPOSED, "override-invalid"),
    ),
}


@pytest.mark.parametrize("reason", list(REASON_CASES))
def test_every_reason_of_the_closed_set_that_can_be_shown_appears_in_rejected(reason: str) -> None:
    """AC-2/AC-6/R-4/R-6. expected_behavior_source: AC-2 (`rejected`: each `model` and `reason`, a
    reason of the closed set); component.md section 3 (the ten reasons); BC-4, BC-6, BC-38. The
    entry shows the catalog id and the use case keeps the resolver's order."""
    document, query, expected = REASON_CASES[reason]

    result = ask(project(document), **query)

    assert expected in rejected_of(result)
    assert {why for _, why in rejected_of(result)} <= SHOWN_REASONS


def test_the_cases_cover_every_reason_of_the_closed_set_except_excluded() -> None:
    """AC-6/R-4. expected_behavior_source: AC-2 (the closed set of reasons); R-4 ("the reason
    `excluded` can never appear in `rejected` of any run")."""
    covered = {expected[1] for _, _, expected in REASON_CASES.values()}

    assert covered == SHOWN_REASONS


def test_the_rejections_of_a_profile_come_in_the_order_of_its_list_and_the_rest_is_selected() -> (
    None
):
    """AC-2/R-6. expected_behavior_source: R-6 ("`rejected` is the resolution's rejections in its
    order"). Candidates for Codex: proposed, disabled, retired, no route, blocked, then A."""
    candidates = [PROPOSED, DISABLED, RETIRED, CLAUDE_ONLY, BLOCKED_ROUTE, A]
    document = policy(via("quality"), profiles=[profile_doc("quality", candidates=candidates)])

    data = data_of(ask(project(document), client=CODEX))

    assert data["selection"] == chosen(listed(A, CODEX))
    assert [(item["model"], item["reason"]) for item in data["rejected"]] == [
        (PROPOSED, "not-approved"),
        (DISABLED, "disabled-or-retired"),
        (RETIRED, "disabled-or-retired"),
        (CLAUDE_ONLY, "no-route-for-client"),
        (BLOCKED_ROUTE, "access-blocked"),
    ]
    assert data["candidates"] == [listed(A, CODEX)]


@pytest.mark.parametrize(
    "override",
    [
        "blocked-alias",
        "BLOCKED-ALIAS",
        " blocked-alias ",
        "anthropic/blocked-alias",
        "Blocked Alias",
        "blocked_alias",
        "blocked-alias[effort=high]",
        "blocked-model-9",
        "blocked-model-9[a=1]",
        "x-blocked-family-y",
        "x[model=blocked-family]",
    ],
)
def test_an_override_that_matches_an_exclusion_is_override_invalid_and_never_excluded(
    override: str,
) -> None:
    """AC-6/R-4. expected_behavior_source: AC-6 ("an override that matches an exclusion or fails a
    constraint is `override-invalid`"); R-4 ("Every rejection at the override level shows in
    `rejected` with the reason `override-invalid`, whatever the resolver's own reason"; `model` is
    the catalog id that the override matched, or null); BC-9 (the spellings of an excluded
    model). The override names no catalog entry, so `model` is null."""
    result = ask(project(policy()), override=override)
    data = data_of(result)

    assert result.status == "none-qualifies"
    assert data["rejected"] == [rej(None, "override-invalid")]
    assert data["selection"] is None
    assert data["client_chooses"] is False
    assert not leaked(shown(result), override.strip(), width=12)


@pytest.mark.parametrize("client", CLIENTS)
def test_an_override_that_fails_a_constraint_shows_the_catalog_id_it_matched(client: str) -> None:
    """AC-6/R-4. expected_behavior_source: R-4 ("`model` of such an entry is the catalog id that the
    override matched"). Each override names a catalog model by a route name of this client and
    fails one constraint: not approved, disabled, retired, or the coder's own model."""
    cases: dict[str, tuple[dict[str, Any], str]] = {
        f"{PROPOSED}-{client}": ({}, PROPOSED),
        f"{DISABLED}-{client}": ({}, DISABLED),
        f"{RETIRED}-{client}": ({}, RETIRED),
        f"{A}-{client}": ({"different_family_from": A}, A),
        f"{C}-{client}": ({"different_family_from": A}, C),
    }
    for override, (extra, model_id) in cases.items():
        result = ask(project(policy()), client=client, override=override, **extra)

        assert rejected_of(result) == [(model_id, "override-invalid")], override
        assert result.status == "none-qualifies"


def test_an_override_for_a_model_with_no_route_for_the_client_is_override_invalid() -> None:
    """AC-6/R-4. expected_behavior_source: R-4 (whatever the resolver's own reason: here
    no-route-for-client). The string names the Claude Code route of a model that only Claude Code
    has, asked for Codex."""
    result = ask(project(policy()), client=CODEX, override=f"{CLAUDE_ONLY}-{CLAUDE}")

    assert rejected_of(result) == [(CLAUDE_ONLY, "override-invalid")]


def test_an_override_that_matches_nothing_is_override_invalid_with_no_model() -> None:
    """AC-6/R-4. expected_behavior_source: R-4 ("`model` ... or null"); ADR-001 decision 4 (an
    invalid override is never replaced silently)."""
    result = ask(project(policy()), override=marker("unknown-override"))

    assert rejected_of(result) == [(None, "override-invalid")]
    assert result.status == "none-qualifies"


def test_an_invalid_override_falls_to_the_pin_with_a_visible_rejection() -> None:
    """AC-6/R-4/R-12. expected_behavior_source: R-4 (the override-level rejection shows in
    `rejected`); ADR-001 decision 4 (never replaced without a visible finding); BC-6 ("An invalid
    override is reported with its reason and is never replaced silently")."""
    data = data_of(run(case_override_invalid()))

    assert data["source"] == "role-assignment"
    assert data["selection"] == chosen(listed(A))
    assert data["rejected"] == [rej(PROPOSED, "override-invalid")]


def test_an_override_that_fails_the_coder_constraint_gives_way_to_the_next_level() -> None:
    """AC-6/R-4. expected_behavior_source: R-4 (an override that fails a constraint is
    `override-invalid`); ADR-001 decision 5 (constraints apply at every level, including the
    reviewer diversity of ADR-007). The override is B's route, which is B itself."""
    document = policy(pinned(C))

    result = ask(project(document), override=f"{B}-{CLAUDE}", different_family_from=B)
    data = data_of(result)

    assert data["rejected"] == [rej(B, "override-invalid")]
    assert data["source"] == "role-assignment"
    assert data["selection"] == chosen(listed(C))


@EVERY_RESULT
def test_the_reason_excluded_never_appears_in_the_rejected_of_any_run(name: str) -> None:
    """AC-6/R-4. expected_behavior_source: AC-6 ("An excluded model is never a candidate, a
    selection or a fallback"); R-4 ("So the reason `excluded` can never appear in `rejected` of any
    run: a policy that names an excluded model anywhere is refused first (R-3), and an excluded
    override is shown as `override-invalid`")."""
    data = data_of(run(scenario(name)))

    assert "excluded" not in {item["reason"] for item in data["rejected"]}
    assert "excluded" not in json.dumps(data["rejected"])


def test_an_excluded_model_in_a_profile_list_or_an_assignment_refuses_the_policy() -> None:
    """AC-6/R-3/R-4. expected_behavior_source: AC-6 ("An excluded model is never a candidate, a
    selection or a fallback"); R-3 (a policy for which `policy_problems` returns a problem is
    refused). The policy puts an excluded id in a profile list and in an assignment: it is
    refused, and nothing of it is listed."""
    excluded_id = "blocked-model-1"
    leaking = entry(excluded_id, *routes_of(excluded_id))
    documents = [
        policy(
            via("quality"),
            models=[*CATALOG, leaking],
            profiles=[profile_doc("quality", candidates=[excluded_id, A])],
        ),
        policy(pinned(excluded_id), models=[*CATALOG, leaking]),
    ]
    for document in documents:
        result = ask(project(document))

        assert result.status == "refused"
        assert result.data == {}
        assert E543 in codes(result)


# --- AC-4, R-5: the hint -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("document", "query", "profile_id"),
    [
        pytest.param(policy(via("quality")), {}, "quality", id="manual-profile"),
        pytest.param(policy(via("economy", "automatic")), {}, "economy", id="automatic-profile"),
        pytest.param(
            policy(via("engineering", "automatic-with-fallbacks")),
            {},
            "engineering",
            id="profile-with-fallbacks",
        ),
        pytest.param(policy(), {"kind": "profile", "name": "economy"}, "economy", id="profile"),
        pytest.param(
            policy(assignment_doc("skill", DESIGN, profile="quality")),
            {"kind": "skill", "name": DESIGN},
            "quality",
            id="skill",
        ),
    ],
)
def test_a_target_that_has_a_profile_gets_the_fixed_hint_with_the_profile(
    document: Doc, query: dict[str, Any], profile_id: str
) -> None:
    """AC-4/R-5. expected_behavior_source: AC-4 (the hint is the fixed sentence "Suggested for this
    work: profile <id>; the client keeps the choice and nothing here changes the model." for a
    target that has a profile); R-5 (<id> is the resolution's profile); BC-35."""
    data = data_of(ask(project(document), **query))

    assert data["hint"] == suggested(profile_id)
    assert data["profile"] == profile_id


def test_the_hint_of_a_profile_that_nothing_qualifies_in_is_still_the_profile() -> None:
    """AC-4/R-5. expected_behavior_source: R-5 ("when the resolution has a profile": none-qualifies
    keeps the profile of the first level tried); AC-4."""
    result = run(case_none_qualifies())
    data = data_of(result)

    assert result.status == "none-qualifies"
    assert data["profile"] == "quality"
    assert data["hint"] == suggested("quality")


def test_a_valid_override_keeps_the_profile_of_the_same_request_without_it() -> None:
    """AC-4/R-5. expected_behavior_source: R-5 ("When a valid override ended the resolution early
    (source "task-override"), the profile of the hint is that of the same request resolved
    without the override"). The data have no profile (R-6), the hint names `quality`."""
    data = data_of(run(case_override_valid()))

    assert data["source"] == "task-override"
    assert data["profile"] is None
    assert data["hint"] == suggested("quality")


def test_a_valid_override_on_a_target_with_no_assignment_has_the_no_assignment_hint() -> None:
    """AC-4/R-5. expected_behavior_source: R-5 (the same request without the override has no
    profile, a policy is present: "no assignment for this target; the client chooses")."""
    data = data_of(ask(project(policy()), override=f"{B}-{CLAUDE}"))

    assert data["source"] == "task-override"
    assert data["hint"] == NO_ASSIGNMENT


@pytest.mark.parametrize(
    "case",
    [case_unassigned, case_empty_policy],
    ids=["a-target-that-the-policy-does-not-assign", "a-policy-with-nothing-in-it"],
)
def test_a_target_that_a_present_policy_does_not_assign_has_the_no_assignment_hint(
    case: Callable[[], Case],
) -> None:
    """AC-4/R-5. expected_behavior_source: AC-4 ("no assignment for this target; the client
    chooses" for a target that a present policy does not assign); R-5."""
    data = data_of(run(case()))

    assert data["hint"] == NO_ASSIGNMENT
    assert data["policy"] == "present"


def test_a_target_that_is_pinned_to_one_model_and_names_no_profile_has_the_no_assignment_hint() -> (
    None
):
    """AC-4/R-5. expected_behavior_source: R-5 ("an assignment that pins one model and names no
    profile ... the hint is "no assignment for this target; the client chooses""). This is the
    reading of the person, which the coder states as an uncertainty: it is pinned as the reading
    and nothing more."""
    data = data_of(run(case_pinned()))

    assert data["hint"] == NO_ASSIGNMENT


@pytest.mark.parametrize(
    "case", [case_no_policy, case_no_policy_constrained], ids=["no-constraint", "a-coder-model"]
)
def test_no_policy_file_gives_the_no_model_policy_hint_and_the_absent_word(
    case: Callable[[], Case],
) -> None:
    """AC-2/AC-4/R-5. expected_behavior_source: AC-4 ("no model policy; the client chooses" when
    there is no policy); R-5; R-6 (`policy` is "absent" when there was none); F-15."""
    data = data_of(run(case()))

    assert data["hint"] == NO_POLICY
    assert data["policy"] == "absent"


def test_the_hint_is_the_same_whatever_the_client() -> None:
    """AC-4/R-5. expected_behavior_source: AC-4 (the fixed sentences carry nothing of the client)
    and R-5 (only the profile id varies)."""
    document = policy(via("quality"))

    hints = {data_of(ask(project(document), client=client))["hint"] for client in CLIENTS}

    assert hints == {suggested("quality")}


# --- AC-3, R-3, R-7: no policy, and the coder constraints ----------------------------------------


def test_no_policy_file_gives_an_automatic_result_with_nothing_listed() -> None:
    """AC-3/R-3/R-6. expected_behavior_source: AC-3 ("Exit status 0 means ... an automatic result
    exists, also when no policy file was ever present"); R-3 ("No policy file at all (and no lock
    row) gives an empty policy: policy "absent", status "automatic""); F-15."""
    result = run(case_no_policy())

    assert result.status == "automatic"
    assert result.findings == ()
    assert data_of(result) == {
        "client": CLAUDE,
        "target": {"kind": "role", "name": TESTER},
        "task": None,
        "policy": "absent",
        "profile": None,
        "mode": None,
        "source": "automatic",
        "selection": None,
        "client_chooses": True,
        "candidates": [],
        "fallbacks": [],
        "escalation": None,
        "list_prices": [],
        "rejected": [],
        "hint": NO_POLICY,
        "result": "automatic",
    }


@pytest.mark.parametrize(
    "lock",
    [
        pytest.param([OTHER_SEEDED], id="a-seeded-row-of-another-file"),
        pytest.param([TEAM_ROW], id="a-row-of-the-policy-owned-by-the-team"),
        pytest.param(b"files: not-a-list\n", id="a-lock-that-is-not-valid"),
        pytest.param(b"a: 1\na: 2\n", id="a-lock-that-is-not-strict-yaml"),
        pytest.param(pad(lock_bytes(SEEDED), LOCK_LIMIT + 1), id="a-lock-over-1-mib"),
    ],
)
def test_a_missing_policy_that_the_lock_cannot_prove_deleted_is_no_policy(
    lock: list[Doc] | bytes,
) -> None:
    """AC-3/R-1/R-3. expected_behavior_source: R-3 ("deleted file (the file is missing and the lock
    lists `.orqlet/model-policy.yaml` with owner `seeded`; ORQ-E547)": any other lock leaves the
    policy never present); R-1 ("a file larger than 1 MiB is refused by the strict loader before
    parsing")."""
    result = ask(project(lock=lock))

    assert result.status == "automatic"
    assert data_of(result)["policy"] == "absent"


@pytest.mark.parametrize("extra", [{"different_family_from": A}, {"coder_profile": "engineering"}])
def test_no_policy_file_and_a_coder_constraint_leaves_nothing_that_qualifies(
    extra: dict[str, Any],
) -> None:
    """AC-3/R-3/R-7. expected_behavior_source: R-3 ("No policy file at all ... unless a coder
    constraint (`different_family_from` or `coder_profile`) is given, then status "none-qualifies"
    and exit 1, in every case"); AC-3 ("1 means that no candidate qualifies, also when
    `--different-family-from` leaves none ... with no policy"); BC-38."""
    result = ask(project(), **extra)
    data = data_of(result)

    assert result.status == "none-qualifies"
    assert data["result"] == "none-qualifies"
    assert data["client_chooses"] is False
    assert data["selection"] is None
    assert data["policy"] == "absent"
    assert result.findings == ()


@pytest.mark.parametrize("mode", MODES)
def test_a_coder_constraint_with_no_different_candidate_leaves_nothing_in_every_mode(
    mode: str,
) -> None:
    """AC-3/R-7. expected_behavior_source: AC-3 ("1 means that no candidate qualifies, also when
    `--different-family-from` leaves none that can be shown different, in every mode"); BC-38; R-7.
    The candidates are the coder's own model and a model of its family, and a fallback that would
    qualify exists: a fallback is not a candidate."""
    both = profile_doc("quality", mode=mode, candidates=[A, C], fallbacks=[B])
    document = policy(via("quality", mode), profiles=[both])

    result = ask(project(document), different_family_from=A)
    data = data_of(result)

    assert result.status == "none-qualifies"
    assert data["client_chooses"] is False
    assert data["selection"] is None
    assert data["rejected"] == [
        rej(A, "same-model-as-coder"),
        rej(C, "same-family-as-coder"),
    ]


@pytest.mark.parametrize("mode", MODES)
def test_a_coder_constraint_that_leaves_a_candidate_gives_the_usual_result(mode: str) -> None:
    """AC-3/R-7. expected_behavior_source: AC-3 (exit 0 means a selection or an automatic result
    exists); BC-38 (a candidate from another family qualifies). Candidates A, C, B: only B is a
    different family from A, and the two others are rejected with their reasons."""
    wide = profile_doc("quality", mode=mode, candidates=[A, C, B])
    document = policy(via("quality", mode), profiles=[wide])

    result = ask(project(document), different_family_from=A)
    data = data_of(result)

    assert result.status == ("selected" if mode == "manual" else "automatic")
    assert data["candidates"] == [listed(B)]
    assert data["rejected"] == [rej(A, "same-model-as-coder"), rej(C, "same-family-as-coder")]


@pytest.mark.parametrize("coder", [PROPOSED, "example-missing"], ids=["proposed", "not-in-catalog"])
@pytest.mark.parametrize("mode", MODES)
def test_a_coder_model_that_gives_no_family_leaves_nothing_that_can_be_shown_different(
    mode: str, coder: str
) -> None:
    """AC-3/R-7. expected_behavior_source: R-7 ("`--different-family-from X` with no candidate that
    can be shown different exits 1 (this includes X not in the catalog, and X in the catalog but
    `proposed`, since a proposed entry gives no family)"); BC-10; BC-38. The candidates would
    qualify for any other coder."""
    document = policy(
        via("quality", mode),
        profiles=[profile_doc("quality", mode=mode, candidates=[A, B], fallbacks=[D])],
    )

    result = ask(project(document), different_family_from=coder)
    data = data_of(result)

    assert result.status == "none-qualifies"
    assert data["client_chooses"] is False
    assert data["selection"] is None
    assert data["candidates"] == []


def test_a_coder_constraint_on_a_target_with_no_assignment_leaves_nothing_that_qualifies() -> None:
    """AC-3/R-7. expected_behavior_source: BC-38 ("exits 1 in every mode, with or without a
    policy"); R-7 (the same with a policy that does not assign the target)."""
    result = ask(project(policy(pinned(A))), name=INVENTORY, different_family_from=A)

    assert result.status == "none-qualifies"
    assert data_of(result)["hint"] == NO_ASSIGNMENT


def test_a_coder_profile_is_the_floor_below_which_a_candidate_is_outside_the_profile() -> None:
    """AC-1/AC-6/R-6. expected_behavior_source: component.md section 3 (`--coder-profile` names
    the coder's profile for the `outside-profile` rule); BC-38 ("A reviewer candidate from a
    profile below `--coder-profile` ... is rejected with `outside-profile`"); ADR-006 (profiles
    ordered quality, engineering, economy). Economy lists C and D; `engineering` lists B and C."""
    document = policy(via("economy", "automatic"))

    at_engineering = data_of(ask(project(document), coder_profile="engineering"))
    at_quality = ask(project(document), coder_profile="quality")

    assert [item["model"] for item in at_engineering["candidates"]] == [C]
    assert at_engineering["rejected"] == [rej(D, "outside-profile")]
    assert at_quality.status == "none-qualifies"
    assert rejected_of(at_quality) == [(C, "outside-profile"), (D, "outside-profile")]


# --- AC-3, R-3: a policy that is present and refused ---------------------------------------------

# Per way that a file is invalid: its bytes and the one code of the reader that refuses it.
INVALID_FILES: dict[str, tuple[Callable[[], bytes], str]] = {
    "duplicate-key": (lambda: b"a: 1\na: 2\n", E540),
    "not-a-mapping": (lambda: b"- a\n- b\n", E541),
    "schema": (lambda: raw_of({"schema": "orqlet.model-policy/v2"}), E541),
    "v1": (lambda: raw_of({"schema": "orqlet.model-policy/v1", "models": []}), E541),
    "unknown-key": (lambda: raw_of({**policy(), marker("key"): 1}), E541),
    "credential": (lambda: raw_of(policy(pinned(A))) + f"\n# {CREDENTIAL}\n".encode(), E542),
    "oversize": (lambda: pad(raw_of(policy(pinned(A))), LIMIT + 1), E540),
}


@pytest.mark.parametrize("name", list(INVALID_FILES))
def test_an_invalid_file_is_refused_with_the_code_of_the_reader_and_no_data(name: str) -> None:
    """AC-3/R-3/R-1. expected_behavior_source: R-3 ("An invalid file (ORQ-E540, ORQ-E541, ORQ-E542),
    a v1 file ... is refused ...: status "refused", exit 3"; `data` is an empty mapping when
    `status` is "refused"); R-1 (the policy is read through `load_model_policy`, the one reader);
    F-1; ADR-002 (a v1 file gets exit 3, "a v1 file; migrate")."""
    build, code = INVALID_FILES[name]

    result = ask(project(build()))

    assert result.status == "refused"
    assert result.data == {}
    assert set(codes(result)) == {code}
    assert all(finding.severity is Severity.ERROR for finding in result.findings)


@pytest.mark.parametrize("name", list(INVALID_FILES))
def test_the_refusal_of_an_invalid_file_does_not_say_upgrade(name: str) -> None:
    """AC-3/R-3. expected_behavior_source: R-3 ("The wording of these refusals does not say "run
    orqlet upgrade" (the words `upgrade` must not appear in a finding message)")."""
    result = ask(project(INVALID_FILES[name][0]()))

    assert result.findings
    for finding in result.findings:
        assert "upgrade" not in finding.message.lower()


@pytest.mark.parametrize("name", ["duplicate-key", "schema", "v1"])
@pytest.mark.parametrize(
    "query",
    [
        {"override": f"{A}-{CLAUDE}"},
        {"kind": "profile", "name": "quality"},
        {"different_family_from": A, "client": CODEX},
    ],
    ids=["an-override", "a-profile-target", "a-coder-model"],
)
def test_a_refused_file_refuses_every_query(name: str, query: dict[str, Any]) -> None:
    """AC-3/R-3. expected_behavior_source: AC-3 ("3 means that a policy is present but invalid,
    deleted or a v1 file"): the refusal does not depend on what is asked; F-1."""
    result = ask(project(INVALID_FILES[name][0]()), **query)

    assert (result.status, result.data) == ("refused", {})
    assert result.findings


def test_a_policy_that_is_missing_while_the_lock_lists_it_as_seeded_is_deleted() -> None:
    """AC-3/AC-5/R-3. expected_behavior_source: R-3 ("a deleted file (the file is missing and the
    lock lists `.orqlet/model-policy.yaml` with owner `seeded`; ORQ-E547) is refused"); AC-5 ("A
    policy that is missing while the lock records it as seeded exits 3 without any git call");
    F-16."""
    tree = project(lock=[SEEDED, OTHER_SEEDED])

    result = ask(tree)

    assert result.status == "refused"
    assert result.data == {}
    assert set(codes(result)) == {E547}
    assert set(tree.touched) == {POLICY, LOCK}  # the lock is the only evidence; no git


def test_the_refusal_of_a_deleted_policy_does_not_say_upgrade() -> None:
    """AC-3/R-3. expected_behavior_source: R-3 (the words `upgrade` must not appear in a finding
    message). The wording of `upgrade` itself tells the person to run `upgrade` again, which is
    no help to a person who asked what the model is."""
    result = ask(project(lock=[SEEDED]))

    assert result.findings
    assert all("upgrade" not in finding.message.lower() for finding in result.findings)


def test_a_policy_that_is_present_is_not_deleted_whatever_the_lock_says() -> None:
    """AC-3/R-3. expected_behavior_source: R-3 (deleted needs the file to be missing); R-1 (the
    lock is read only when the policy file is missing)."""
    result = ask(project(policy(pinned(A)), lock=[SEEDED]))

    assert result.status == "selected"


@pytest.mark.parametrize("name", list(PROBLEMS))
def test_a_policy_with_a_problem_is_refused_with_its_code_and_the_field_path(name: str) -> None:
    """AC-3/AC-6/R-3. expected_behavior_source: R-3 ("A policy for which `policy_problems(policy,
    role_names, skill_names)` returns any problem (ORQ-E543 an exclusion matches; ORQ-E545 a bad
    reference) is refused: status "refused", exit 3, `findings` with those codes and field paths
    (for example `models[0]`)"); F-2; BC-9."""
    document, code, path = PROBLEMS[name]

    result = ask(project(document))

    assert result.status == "refused"
    assert result.data == {}
    assert set(codes(result)) == {code}
    assert any(names(finding, path) for finding in result.findings), (path, result.findings)
    assert all(finding.severity is Severity.ERROR for finding in result.findings)


@pytest.mark.parametrize("name", list(PROBLEMS))
def test_a_policy_with_a_problem_is_refused_in_words_that_do_not_say_upgrade(name: str) -> None:
    """AC-3/R-3. expected_behavior_source: R-3 (the words `upgrade` must not appear in a finding
    message). `model_selection` words its own refusal for `upgrade` ("run `orqlet upgrade`
    again")."""
    result = ask(project(PROBLEMS[name][0]))

    assert result.findings
    assert all("upgrade" not in finding.message.lower() for finding in result.findings)


@pytest.mark.parametrize("name", list(PROBLEMS))
def test_a_policy_with_a_problem_is_refused_for_any_target(name: str) -> None:
    """AC-3/R-3. expected_behavior_source: R-3 (the policy is refused, not the target); F-2. The
    asked target is a profile, which the policy may or may not define."""
    result = ask(project(PROBLEMS[name][0]), kind="profile", name="economy")

    assert (result.status, result.data) == ("refused", {})


def test_a_policy_with_both_kinds_of_problem_reports_both_codes() -> None:
    """AC-3/R-3. expected_behavior_source: R-3 (`findings` with those codes: E543 and E545)."""
    leaking = entry("blocked-model-1", *routes_of("blocked-model-1"))
    document = policy(assignment_doc("role", "no-such-role", model=A), models=[*CATALOG, leaking])

    result = ask(project(document))

    assert result.status == "refused"
    assert {E543, E545} <= set(codes(result))


def test_a_refused_policy_never_shows_a_value_of_the_file() -> None:
    """AC-3/AC-6/R-3/R-9. expected_behavior_source: R-3 ("never a value of the file"); BC-32 (no
    finding prints a model string); R-9 ("any value of a refused file"). The excluded alias, the
    unknown role and the unknown model are markers."""
    alias, role, missing = marker("alias"), marker("role"), marker("missing")
    document = policy(
        assignment_doc("role", role, model=A),
        assignment_doc("role", TESTER, model=missing),
        models=[*CATALOG, entry("example-bad", route(CLAUDE, alias))],
        excluded=[EXCLUSION, exclusion("marked", aliases=[alias])],
    )

    result = ask(project(document))

    assert {E543, E545} <= set(codes(result))
    text = shown(result)
    for value in (alias, role, missing):
        assert not leaked(text, value), value


# --- R-9: what the output never prints ------------------------------------------------------------


def marked_policy() -> tuple[Doc, dict[str, str]]:
    """A policy whose every field that AC-2 does not print holds a marker, and its markers."""
    markers = {
        label: marker(label)
        for label in (
            "approved-by",
            "approval-ref",
            "evidence",
            "price-source",
            "exclusion-reason",
            "exclusion-source",
            "capability",
        )
    }
    priced = entry(
        A,
        *routes_of(A),
        price=("3", "15"),
        approved_by=markers["approved-by"],
        approval_ref=markers["approval-ref"],
        evidence=f"docs/{markers['evidence']}.md",
        price_source=f"docs/{markers['price-source']}.md",
    )
    document = policy(
        via("quality"),
        models=[priced, CATALOG[1]],
        profiles=[
            profile_doc(
                "quality", candidates=[A, B], fallbacks=[B], capability=markers["capability"]
            )
        ],
        excluded=[
            exclusion(
                "marked-rule",
                aliases=["blocked-alias"],
                reason=markers["exclusion-reason"],
                source=markers["exclusion-source"],
            )
        ],
    )
    return document, markers


@pytest.mark.parametrize(
    "query",
    [
        {},
        {"override": f"{B}-{CLAUDE}"},
        {"override": "blocked-alias"},
        {"different_family_from": A},
        {"different_family_from": "example-missing"},
        {"different_family_from": B, "client": CODEX},
        {"kind": "profile", "name": "quality"},
    ],
    ids=[
        "selected",
        "override",
        "excluded-override",
        "coder-constraint",
        "none-qualifies",
        "codex",
        "profile",
    ],
)
def test_a_value_of_the_file_that_the_criterion_does_not_print_is_never_printed(
    query: dict[str, Any],
) -> None:
    """AC-2/AC-6/R-9. expected_behavior_source: R-9 ("File values that AC-2 does not print must
    never appear either: `approval.approved_by`, `approval.approval_ref`, `documented.evidence`,
    `list_price.source`, an exclusion's `reason` and `source`, a profile's `capability`"); BC-32."""
    document, markers = marked_policy()

    result = ask(project(document), **query)

    text = shown(result)
    for label, value in markers.items():
        assert not leaked(text, value), label
    assert result.status != "refused"


def test_a_value_that_the_criterion_prints_is_printed() -> None:
    """AC-2/R-9. expected_behavior_source: R-9 ("Values that AC-2 does print (route `name`,
    `also_known_as`, catalog ids, list prices) are printed and are not markers")."""
    text = shown(run(case_profile_manual()))

    for printed in (A, f"{A}-{CLAUDE}", ALSO_A, B, "3", "15", "quality", "manual"):
        assert printed in text, printed


@pytest.mark.parametrize("name", ["whole", "in-a-bracket-list", "valid-model", "invalid-model"])
def test_the_override_string_is_never_printed(name: str) -> None:
    """AC-6/R-4/R-9. expected_behavior_source: AC-6 ("the output never prints the override string,
    only catalog ids that passed `ModelRef` and fixed words"); R-9 (use a marker as the whole
    override and inside a bracket option list, since the matching rule treats a bracketed option
    list as no difference). Every override is either unknown, excluded, invalid or valid."""
    mark = marker("override")
    overrides = {
        "whole": mark,
        "in-a-bracket-list": f"blocked-alias[{mark}=1]",
        "valid-model": f"{B}-{CLAUDE}[{mark}=1]",
        "invalid-model": f"{PROPOSED}-{CLAUDE}[{mark}=1]",
    }

    result = ask(project(policy(pinned(A))), override=overrides[name])

    assert not leaked(shown(result), mark)


@pytest.mark.parametrize(
    "name",
    ["unknown-key", "bad-value", "bad-state", "duplicate-key", "credential"],
)
def test_no_value_of_a_refused_file_is_printed(name: str) -> None:
    """AC-3/R-3/R-9. expected_behavior_source: R-9 ("any value of a refused file (a marker in an
    unknown key or in a value of an invalid file)"); BC-32; ORQLET-SEC-003 (a credential is never
    put in a message). The unknown key is named `unknown-key` and the loader's own message, which
    can quote the file, is not passed on."""
    mark = marker("value")
    bad_value = {**policy(), "policy_version": mark}
    bad_state = policy(models=[entry(A, *routes_of(A), state=mark)])
    files = {
        "unknown-key": raw_of({**policy(), mark: 1}),
        "bad-value": raw_of(bad_value),
        "bad-state": raw_of(bad_state),
        "duplicate-key": f"{mark}: 1\n{mark}: 2\n".encode(),
        "credential": raw_of(policy()) + f"\n# {mark} {CREDENTIAL}\n".encode(),
    }

    result = ask(project(files[name]))

    assert result.status == "refused"
    text = shown(result)
    assert not leaked(text, mark)
    assert not leaked(text, CREDENTIAL)


# --- R-14: the size limit of the policy ----------------------------------------------------------


def test_a_policy_of_exactly_256_kib_is_read() -> None:
    """AC-3/R-1/R-14. expected_behavior_source: R-14 ("a policy file of exactly 262144 bytes is
    read"); R-1 (`load_model_policy` checks 256 KiB before it parses)."""
    raw = pad(raw_of(policy(pinned(A))), LIMIT)
    assert len(raw) == LIMIT

    result = ask(project(raw))

    assert result.status == "selected"
    assert data_of(result)["policy"] == "present"


def test_a_policy_of_one_byte_more_is_refused_as_invalid_without_its_content() -> None:
    """AC-3/R-1/R-14. expected_behavior_source: R-14 ("one of 262145 bytes is refused as invalid
    (ORQ-E540) with exit 3 and the finding does not print file content"). A marker is in the
    content: it is the id of a model that the policy lists."""
    mark = marker("content")
    document = policy(pinned(A), models=[*CATALOG, entry(mark, *routes_of(mark))])
    raw = pad(raw_of(document), LIMIT + 1)
    assert len(raw) == LIMIT + 1

    result = ask(project(raw))

    assert result.status == "refused"
    assert set(codes(result)) == {E540}
    assert not leaked(shown(result), mark)


# --- AC-5: the same input gives the same result --------------------------------------------------


@EVERY_SCENARIO
def test_the_result_is_deterministic(name: str) -> None:
    """AC-2/AC-5. expected_behavior_source: AC-2 ("the same input gives the same bytes"); AC-5
    ("Two runs print the same bytes"); BC-23 ("gives the same bytes for the same input")."""
    first = run(scenario(name))
    second = run(scenario(name))

    assert first == second
    assert shown(first) == shown(second)


@EVERY_REFUSAL
def test_every_finding_of_a_refusal_is_an_error_with_an_e_code(name: str) -> None:
    """AC-3/R-3. expected_behavior_source: R-3 (the findings carry the codes ORQ-E540 to ORQ-E547);
    the interface (`findings` is a tuple of `Finding`, empty unless `status` is "refused")."""
    result = run(REFUSED_SCENARIOS[name]())

    assert result.status == "refused"
    assert isinstance(result.findings, tuple)
    assert result.findings
    for finding in result.findings:
        assert isinstance(finding, Finding)
        assert finding.severity is Severity.ERROR
        assert re.fullmatch(r"ORQ-E54[0-7]", finding.code), finding.code
    assert result.data == {}


@EVERY_RESULT
def test_a_result_that_is_not_refused_has_no_findings(name: str) -> None:
    """AC-3/R-7. expected_behavior_source: the interface (`findings` is empty unless `status` is
    "refused"); R-7 (status "selected", "automatic" or "none-qualifies")."""
    result = run(scenario(name))

    assert result.status in {"selected", "automatic", "none-qualifies"}
    assert result.findings == ()
