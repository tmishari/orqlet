"""`upgrade` follows the model policy (task dynamic-model-profiles, phase P-6).

It covers what the plan of P-6 asks of `upgrade` and of the code under it: `follow_policy` and the
findings of `model_selection`, the keyword `policy` of `compose` and its `model_outcome`, and the
findings ORQ-E547, ORQ-W540, ORQ-W545, ORQ-W546, ORQ-W547 and ORQ-I540 of `upgrade`. The list of
stale review records (`pin_staleness`) is in test_pin_staleness.py and `explain` with the CLI is in
test_explain_model_selection.py.

Every test cites its `expected_behavior_source`. AC-1 to AC-6 and AC-8 are acceptance criteria of
phase P-6 in docs/design/dynamic-model-profiles/plan.yaml (AC-7 is `explain`, AC-9 is the gate
check; the Coder runs the second and no test is written for it). BC-n and F-n are the behaviour and
failure rows of design/component.md, C-n its constraints, R-n its risks, and ADR-n the decision
records of design/. "The interface" is the interface that the Coder of this phase implements and
that the brief of this phase's Tester states; its items are numbered 1 to 10 in that brief:
1. `compose(..., policy: PolicyState | None = None)` replaces the keyword `selection`, runs the
   selection itself and returns `Composition.model_outcome` (a `PolicyOutcome`);
2. `PolicyOutcome(selection, findings, refused)` and `follow_policy(state, role_names, skill_names,
   clients)`, with the codes ORQ-E547 and ORQ-W540 as `POLICY_DELETED` and `MISSING_CANDIDATE`;
3. ORQ-W540 for a target that a manual mode cannot pin, or a fallback mode cannot give a fallback;
4. `SelectionEntry` rows (these are tested in test_explain_model_selection.py);
5. `upgrade` loads the policy, refuses before any plan, check, dry run or write, and adds ORQ-W547
   and ORQ-I540 after the plan is built;
6. `explain` (the other test file);
7. `pin_staleness` (the other test file);
8. ORQ-I540;
9. `init` calls `compose` with `policy=None`;
10. the CLI (the other test file).

These tests were written first, by the Tester of phase P-6, before the implementation existed. A
policy is built in code as plain data and written as JSON text, which is YAML, or validated with
`ModelPolicy.model_validate`. Names and texts are placeholders (`example-*`); a marker string
(`zq7leak`) is put in every model id, route name and key that a finding must never repeat (BC-32).
Credential-shaped text is assembled from fragments at run time and none is written as one literal
(ORQLET-SEC-003). The file system is the in-memory fake, the VCS is `FakeVcs`, and the crash is the
faulty file system of tests/fakes (ORQLET-TEST-001); the model clients are never started.

Behaviour that neither the plan nor the brief settle is deliberately not pinned here:
- the wording of a finding. Pinned: its code, its severity (the refusals are errors, the rest
  warnings, ORQ-I540 information), the target and the client, the closed `<level> <reason>` pairs
  of ORQ-W540, a few key words, and that no model string, route name or other value of the file is
  in it;
- the order of the findings of one run, except that W545 and W546 come before W540;
- what `compose` returns as `desired` when the policy is refused (the callers stop first);
- whether an unscoped skill assignment gives ORQ-W540 for Codex and Cursor too (this file only
  tests a skill assignment that is scoped to Claude Code);
- the message when no candidate or fallback is listed, beyond that it holds the word `none`;
- a manual assignment that falls through to a profile that rescues it.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import tomllib
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from typing import Any

import pytest
import yaml

import orqlet.application.usecases.init_project as init_module
from orqlet.adapters.fs.journal import FsChangeJournal
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases import model_selection, render_all
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.model_policy_source import (
    PolicyAbsent,
    PolicyDeleted,
    PolicyInvalid,
    PolicyLoaded,
    PolicyState,
)
from orqlet.application.usecases.render_all import Composition, compose, resolve_for
from orqlet.application.usecases.upgrade import UpgradeOptions, UpgradeResult, upgrade
from orqlet.domain.changeplan import proposal_path
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.paths import CanonicalPath
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import SequentialIds
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED, ChangedWorkflow
from tests.support.init_env import Env, tree
from tests.support.render import ROLE_NAMES, SKILL_NAMES
from tests.support.trees import FIXTURES, repo

pytestmark = pytest.mark.unit

CLAUDE = "claude-code"
CODEX = "codex"
CURSOR = "cursor"
# The clients of the sample project, in the order that its profile enables them.
CLIENTS = (CLAUDE, CODEX, CURSOR)
E540 = "ORQ-E540"
E541 = "ORQ-E541"
E542 = "ORQ-E542"
E543 = "ORQ-E543"
E545 = "ORQ-E545"
E547 = "ORQ-E547"
W540 = "ORQ-W540"
W545 = "ORQ-W545"
W546 = "ORQ-W546"
W547 = "ORQ-W547"
I540 = "ORQ-I540"
MARKER = "zq7leak"
TESTER = "orqlet-tester"
INVENTORY = "orqlet-inventory"
ARCH = "orqlet-arch-reviewer"
SECURITY = "orqlet-security-reviewer"
REVIEW = "orqlet-review"
DESIGN = "orqlet-design"
POLICY_PATH = ".orqlet/model-policy.yaml"
LOCK_PATH = ".orqlet/generated.lock.yaml"
BINDINGS_PATH = ".orqlet/role-bindings.yaml"
ROLE_PATH = {
    CLAUDE: ".claude/agents/{}.md",
    CURSOR: ".cursor/agents/{}.md",
    CODEX: ".codex/agents/{}.toml",
}
FENCE_END = "\n---\n"
YES = InitOptions(assume_yes=True)
MODES = {
    "apply": UpgradeOptions(assume_yes=True),
    "dry-run": UpgradeOptions(dry_run=True),
    "check": UpgradeOptions(check=True),
}
STATUS_WITH_A_PLAN = {"apply": "applied", "dry-run": "previewed", "check": "available"}
NEXT = ChangedWorkflow(PINNED, version="0.2.0")
CODE_REVIEWER = ("code-reviewer", "orqlet-code-reviewer")
LOADER = StrictYamlLoader()


# --- policies built in code ---------------------------------------------------------------


def route(
    client: str,
    name: str | None,
    *,
    kind: str = "id",
    resolves_to: str | None = None,
    access: str = "unknown",
) -> dict[str, Any]:
    return {
        "client": client,
        "kind": kind,
        "name": name,
        "resolves_to": resolves_to,
        "also_known_as": [],
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


def routes_of(
    prefix: str, clients: Sequence[str] = CLIENTS, *, access: str = "unknown"
) -> list[dict[str, Any]]:
    """One id route for each client, named `<prefix>-<client>`."""
    return [route(client, f"{prefix}-{client}", access=access) for client in clients]


def exclusion(
    rule_id: str, *, id_patterns: Sequence[str], reason: str = "Example."
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "reason": reason,
        "source": "Example notice.",
        "aliases": [],
        "id_patterns": list(id_patterns),
        "family_tags": [],
    }


def profile_doc(
    profile_id: str,
    *,
    mode: str = "manual",
    candidates: Sequence[str] = (),
    fallbacks: Sequence[str] = (),
    clients: Sequence[str] = CLIENTS,
) -> dict[str, Any]:
    """A profile whose candidates and fallbacks are the same ordered ids for each client given."""
    return {
        "id": profile_id,
        "capability": "Example capability.",
        "mode": mode,
        "candidates": [{"client": c, "models": list(candidates)} for c in clients if candidates],
        "fallbacks": [{"client": c, "models": list(fallbacks)} for c in clients if fallbacks],
        "escalation": None,
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


def policy_doc(
    models: Sequence[dict[str, Any]],
    assignments: Sequence[dict[str, Any]],
    *,
    profiles: Sequence[dict[str, Any]] = (),
    excluded: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "schema": "orqlet.model-policy/v2",
        "policy_version": 1,
        "reviewed_for_release": "0.4.0",
        "models": list(models),
        "excluded": list(excluded),
        "profiles": list(profiles),
        "assignments": list(assignments),
    }


def make_policy(
    models: Sequence[dict[str, Any]],
    assignments: Sequence[dict[str, Any]],
    *,
    profiles: Sequence[dict[str, Any]] = (),
    excluded: Sequence[dict[str, Any]] = (),
) -> ModelPolicy:
    return ModelPolicy.model_validate(
        policy_doc(models, assignments, profiles=profiles, excluded=excluded)
    )


def document(data: dict[str, Any]) -> bytes:
    return json.dumps(data, indent=2).encode()


# Two approved models with an id route for each client: `example-a-claude-code` and so on.
MODEL_A = entry("example-a", *routes_of("example-a"))
MODEL_B = entry("example-b", *routes_of("example-b"))
# A model with a marker in its id and in every route name, which no finding may repeat.
SECRET_ID = f"{MARKER}-model"
SECRET_ROUTES = f"{MARKER}-route"


def secret_model(state: str = "approved", **kwargs: Any) -> dict[str, Any]:
    return entry(SECRET_ID, *routes_of(SECRET_ROUTES, **kwargs), state=state)


def pin_doc(role: str = TESTER) -> dict[str, Any]:
    """A valid policy that pins `role` to the model `example-a` for every client."""
    return policy_doc([MODEL_A], [assignment_doc("role", role, model="example-a")])


def no_pin_doc() -> dict[str, Any]:
    """The same policy with the mode `automatic`: a valid file that pins nothing."""
    return policy_doc(
        [MODEL_A], [assignment_doc("role", TESTER, model="example-a", mode="automatic")]
    )


# --- projects ------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def before_the_code_reviewer_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tests of this module start from a project that `init` gave no code reviewer binding.

    Phase P-9 puts that binding into `REVIEW_AGENTS`, so `initialised()` would already hold it and
    `code_reviewer_binding()` would add it a second time. Taking it out here keeps what each test
    means: the binding is added only where the test asks for it (the seed itself is tested in
    test_lifecycle.py and test_review_maps.py).
    """
    monkeypatch.setattr(
        render_all,
        "REVIEW_AGENTS",
        tuple(entry for entry in render_all.REVIEW_AGENTS if entry != CODE_REVIEWER),
    )


def initialised() -> Env:
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    assert init_project(env.services(), YES).status == "applied"
    return env


def put(env: Env, path: str, content: bytes) -> None:
    env.project.write_atomic(CanonicalPath.parse(path), content)


def read(env: Env, path: str) -> bytes:
    return env.project.read_bytes(CanonicalPath.parse(path))


def install(env: Env, data: dict[str, Any]) -> None:
    put(env, POLICY_PATH, document(data))


def codes(findings: Sequence[Finding]) -> list[str]:
    return [finding.code for finding in findings]


def of_code(findings: Sequence[Finding], code: str) -> list[Finding]:
    return [finding for finding in findings if finding.code == code]


def first_error(findings: Sequence[Finding]) -> Finding:
    return next(finding for finding in findings if finding.severity is Severity.ERROR)


@contextmanager
def code_reviewer_binding() -> Iterator[None]:
    """The generated role bindings gain a binding of `orqlet-code-reviewer` (ADR-006)."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(render_all, "REVIEW_AGENTS", (*render_all.REVIEW_AGENTS, CODE_REVIEWER))
        yield


def binding_if(wanted: bool) -> AbstractContextManager[None]:
    return code_reviewer_binding() if wanted else nullcontext()


def written_pin(
    files: Mapping[str, bytes], client: str, kind: str, name: str
) -> tuple[str, str | None] | None:
    """The model and effort that a generated file pins, parsed from the file; `None` if none."""
    if kind == "role":
        text = files[ROLE_PATH[client].format(name)].decode("utf-8")
    elif client == CLAUDE:
        text = files[f".claude/skills/{name}/SKILL.md"].decode("utf-8")
    else:
        text = files[f".agents/skills/{name}/SKILL.md"].decode("utf-8")
    if client == CODEX and kind == "role":
        data = tomllib.loads(text)
        model = data.get("model")
        return None if model is None else (model, data.get("model_reasoning_effort"))
    assert text.startswith("---\n")
    fields = yaml.safe_load(text[4 : text.index(FENCE_END, 3) + 1])
    model = fields.get("model")
    if model is None or model == "inherit":
        return None
    return (model, fields.get("effort"))


def no_leak(findings: Sequence[Finding], *secrets: str) -> None:
    """BC-32: no finding repeats the marker or any other string of the file."""
    for finding in findings:
        for text in (finding.code, finding.message, finding.path or ""):
            assert MARKER not in text, finding
            for secret in secrets:
                assert secret not in text, finding


# =============================================================================================
# The interface: compose, PolicyOutcome and follow_policy
# =============================================================================================


def composed(env: Env, state: PolicyState | None) -> Composition:
    services = env.services()
    inst = load_installation(services)
    return compose(
        services,
        inst.profile,
        resolve_for(services, inst.profile),
        Resources(schema_id="orqlet.resources/v1"),
        clients=inst.profile.clients.enabled,
        prompts_dir=".prompts",
        pr_targets=(),
        profile_bytes=b"",
        resources_bytes=b"",
        policy=state,
    )


def test_compose_takes_the_policy_state_in_place_of_the_selection() -> None:
    """AC-1. expected_behavior_source: plan P-6 file_operations (`render_all.py`: "the function
    `compose` takes the policy state and returns its findings with the composition"); the interface
    item 1 (the keyword `selection` is replaced by `policy: PolicyState | None = None`, the last
    keyword parameter, after `released_record`).
    """
    parameters = inspect.signature(compose).parameters

    assert "selection" not in parameters
    assert list(parameters)[-1] == "policy"
    assert list(parameters)[-2] == "released_record"
    assert parameters["policy"].default is None
    assert parameters["policy"].kind is inspect.Parameter.KEYWORD_ONLY


def test_the_composition_carries_an_empty_outcome_by_default() -> None:
    """AC-1. expected_behavior_source: the interface item 1 (`Composition` gains `model_outcome:
    PolicyOutcome`, default empty) and item 2 (`PolicyOutcome(selection=None, findings=(),
    refused=False)`, a frozen dataclass).
    """
    outcome = model_selection.PolicyOutcome()
    env = initialised()
    services = env.services()
    resolution = resolve_for(services, load_installation(services).profile)

    assert dataclasses.is_dataclass(outcome)
    assert (outcome.selection, outcome.findings, outcome.refused) == (None, (), False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        outcome.refused = True  # type: ignore[misc]
    assert Composition([], [], resolution).model_outcome == outcome


def test_the_two_new_codes_are_the_ones_of_the_interface() -> None:
    """AC-1, AC-2. expected_behavior_source: the interface item 2 (`MISSING_CANDIDATE =
    "ORQ-W540"` and `POLICY_DELETED = "ORQ-E547"` in `model_selection`); plan P-6 AC-1 and AC-2.
    """
    assert model_selection.MISSING_CANDIDATE == W540
    assert model_selection.POLICY_DELETED == E547


@pytest.mark.parametrize("state", [None, PolicyAbsent()], ids=["none", "absent"])
def test_compose_without_a_policy_gives_the_files_of_no_policy_and_an_empty_outcome(
    state: PolicyState | None,
) -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 ("With no policy file ever present the upgrade
    plan equals the plan before this phase") and AC-8 (`init` composes with no policy); the
    interface items 1 and 2 (`follow_policy` of `None` or `PolicyAbsent` is the empty outcome).
    """
    env = initialised()

    composition = composed(env, state)

    assert composition.model_outcome == model_selection.PolicyOutcome()
    assert not {f.code for f in composition.findings} & {W540, W545, W546}
    pinned = [item for item in composition.desired if str(item.path).startswith(".claude/agents/")]
    assert pinned
    assert all(b"model: inherit" in item.content for item in pinned)


def test_compose_runs_the_selection_and_returns_its_outcome_and_findings() -> None:
    """AC-1, AC-3. expected_behavior_source: the interface item 1 ("`compose` runs the selection
    itself via `select_models`. `Composition.findings` contains the outcome findings"); plan P-6
    AC-3. The tester is pinned with an effort: Claude Code and Codex take it, Cursor does not
    (ORQ-W546).
    """
    env = initialised()
    doc = policy_doc([MODEL_A], [assignment_doc("role", TESTER, model="example-a", effort="high")])

    composition = composed(env, PolicyLoaded(ModelPolicy.model_validate(doc)))

    outcome = composition.model_outcome
    assert outcome.refused is False
    assert outcome.selection is not None
    assert [f.code for f in outcome.findings] == [W546]
    assert all(finding in composition.findings for finding in outcome.findings)
    files = {str(item.path): item.content for item in composition.desired}
    assert written_pin(files, CLAUDE, "role", TESTER) == ("example-a-claude-code", "high")
    assert written_pin(files, CODEX, "role", TESTER) == ("example-a-codex", "high")
    assert written_pin(files, CURSOR, "role", TESTER) is None


# --- follow_policy -------------------------------------------------------------------------


def follow(state: PolicyState | None) -> model_selection.PolicyOutcome:
    return model_selection.follow_policy(state, ROLE_NAMES, SKILL_NAMES, CLIENTS)


@pytest.mark.parametrize("state", [None, PolicyAbsent()], ids=["none", "absent"])
def test_follow_policy_of_no_policy_is_the_empty_outcome(state: PolicyState | None) -> None:
    """AC-1. expected_behavior_source: the interface item 2 ("None/PolicyAbsent -> empty
    outcome")."""
    assert follow(state) == model_selection.PolicyOutcome()


def test_follow_policy_refuses_an_invalid_policy_with_the_findings_of_the_reader() -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 (invalid policy, ORQ-E540 to ORQ-E542); the
    interface item 2 ("PolicyInvalid -> refused with the reader's findings"), not changed or added
    to.
    """
    findings = (
        Finding(E541, "the policy fails its contract at (document)", Severity.ERROR, POLICY_PATH),
        Finding(E542, "line 3: the rule x matched", Severity.ERROR, POLICY_PATH),
    )

    outcome = follow(PolicyInvalid(findings))

    assert outcome.refused is True
    assert outcome.selection is None
    assert outcome.findings == findings


def test_follow_policy_refuses_a_deleted_policy_with_one_fixed_error() -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 (deleted, ORQ-E547: "the file is missing and
    the lock records it as seeded"); the interface item 2 ("PolicyDeleted -> refused with one
    ORQ-E547 error finding (path `.orqlet/model-policy.yaml`, fixed text saying nothing was changed
    and to restore the file)"). Pinned by key words.
    """
    outcome = follow(PolicyDeleted())

    assert outcome.refused is True
    assert outcome.selection is None
    assert len(outcome.findings) == 1
    finding = outcome.findings[0]
    assert finding.code == E547
    assert finding.severity is Severity.ERROR
    assert finding.path == POLICY_PATH
    assert "nothing was changed" in finding.message.lower()
    assert "restore" in finding.message.lower()


def recording_select(
    monkeypatch: pytest.MonkeyPatch, result: model_selection.ModelSelection | None = None
) -> list[tuple[ModelPolicy, tuple[str, ...], tuple[str, ...], tuple[str, ...]]]:
    """Replace `select_models` by a recorder; it returns `result`, or the real selection."""
    real = model_selection.select_models
    calls: list[tuple[ModelPolicy, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = []

    def recorder(
        policy: ModelPolicy,
        role_names: Sequence[str],
        skill_names: Sequence[str],
        clients: Sequence[str],
    ) -> model_selection.ModelSelection:
        calls.append((policy, tuple(role_names), tuple(skill_names), tuple(clients)))
        return real(policy, role_names, skill_names, clients) if result is None else result

    monkeypatch.setattr(model_selection, "select_models", recorder)
    return calls


def test_follow_policy_asks_select_models_with_the_names_and_the_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1. expected_behavior_source: the interface item 2 (`follow_policy(state, role_names,
    skill_names, clients)` builds the selection) and item 1 ("`compose` runs the selection itself
    via `select_models`"); the plan P-6 AC-1 (a policy that fails `policy_problems` is refused).
    """
    policy = make_policy([MODEL_A], [assignment_doc("role", TESTER, model="example-a")])
    calls = recording_select(monkeypatch)

    outcome = follow(PolicyLoaded(policy))

    assert len(calls) == 1
    assert calls[0][0] is policy
    assert set(calls[0][1]) == set(ROLE_NAMES)
    assert set(calls[0][2]) == set(SKILL_NAMES)
    assert calls[0][3] == CLIENTS
    assert outcome.refused is False
    assert outcome.selection is not None


def test_a_selection_with_problems_is_refused_with_one_finding_for_each_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 ("fails `policy_problems` (ORQ-E543,
    ORQ-E545). Each refusal prints the code, the fixed text and a field path, and no value of the
    file"); the interface item 2 ("PolicyLoaded with `problems` -> refused with ONE finding per
    code (E543/E545) whose message holds fixed text plus field paths"). The selection is a stub
    that carries three problems of two codes, so the mapping is the thing that is tested.
    """
    problems = (
        model_selection.PolicyProblem(E543, "models[3]"),
        model_selection.PolicyProblem(E545, "assignments[1].profile"),
        model_selection.PolicyProblem(E543, "profiles[0].candidates[2].models[1]"),
    )
    recording_select(monkeypatch, model_selection.ModelSelection(problems=problems))
    policy = make_policy([MODEL_A], [])

    outcome = follow(PolicyLoaded(policy))

    assert outcome.refused is True
    assert outcome.selection is None
    assert sorted(codes(outcome.findings)) == [E543, E545]
    assert all(f.severity is Severity.ERROR for f in outcome.findings)
    excluded = of_code(outcome.findings, E543)[0].message
    assert "models[3]" in excluded
    assert "profiles[0].candidates[2].models[1]" in excluded
    assert "assignments[1].profile" in of_code(outcome.findings, E545)[0].message
    assert "assignments[1].profile" not in excluded


def test_the_field_paths_of_one_finding_are_at_most_twenty_and_then_a_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1. expected_behavior_source: the interface item 2 ("field paths (max 20, then `and N
    more`)"). Twenty-five problems of one code give one finding with the first twenty paths in the
    order of the document and `and 5 more`.
    """
    problems = tuple(
        model_selection.PolicyProblem(E545, f"assignments[{n}].target.name") for n in range(25)
    )
    recording_select(monkeypatch, model_selection.ModelSelection(problems=problems))

    outcome = follow(PolicyLoaded(make_policy([MODEL_A], [])))

    assert codes(outcome.findings) == [E545]
    text = outcome.findings[0].message
    assert all(f"assignments[{n}].target.name" in text for n in range(20))
    assert not any(f"assignments[{n}].target.name" in text for n in range(20, 25))
    assert "and 5 more" in text


def test_exactly_twenty_field_paths_have_no_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-1. expected_behavior_source: the interface item 2 ("max 20, then `and N more`"): at the
    limit all twenty are listed and nothing is counted.
    """
    problems = tuple(
        model_selection.PolicyProblem(E545, f"assignments[{n}].target.name") for n in range(20)
    )
    recording_select(monkeypatch, model_selection.ModelSelection(problems=problems))

    outcome = follow(PolicyLoaded(make_policy([MODEL_A], [])))

    text = outcome.findings[0].message
    assert all(f"assignments[{n}].target.name" in text for n in range(20))
    assert " more" not in text


def test_a_real_policy_with_problems_is_refused_without_a_value_of_the_file() -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 (ORQ-E543 and ORQ-E545 "no value of the
    file"); BC-32; the interface item 2. An excluded model that nothing assigns and a role that
    does not exist: one finding for each code, and the marker that sits in the model id and in the
    role name appears nowhere.
    """
    excluded = entry(f"{MARKER}-excluded", route(CLAUDE, "claude-fable-9"))
    policy = make_policy(
        [MODEL_A, excluded],
        [
            assignment_doc("role", TESTER, model="example-a"),
            assignment_doc("role", f"{MARKER}-no-such-role", model="example-a"),
        ],
        excluded=[exclusion("rule-fable", id_patterns=["claude-fable-*"])],
    )

    outcome = follow(PolicyLoaded(policy))

    assert outcome.refused is True
    assert sorted(codes(outcome.findings)) == [E543, E545]
    assert "models[1]" in of_code(outcome.findings, E543)[0].message
    assert "assignments[1].target.name" in of_code(outcome.findings, E545)[0].message
    no_leak(outcome.findings)


def test_a_policy_without_problems_gives_its_selection_and_the_findings_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1, AC-2, AC-3. expected_behavior_source: the interface item 2 ("Otherwise `selection` =
    the selection, and findings = W545/W546 followed by W540"). The selection is a stub with two
    findings and one missing candidate, so the join is what is tested.
    """
    alias = Finding(W545, "role a for claude-code: alias", Severity.WARNING)
    refused = Finding(W546, "role a for cursor: refused", Severity.WARNING)
    missing = Finding(W540, "role b for codex: missing", Severity.WARNING)
    stub = model_selection.ModelSelection(findings=(alias, refused), missing=(missing,))
    recording_select(monkeypatch, stub)

    outcome = follow(PolicyLoaded(make_policy([MODEL_A], [])))

    assert outcome.refused is False
    assert outcome.selection is stub
    assert outcome.findings == (alias, refused, missing)


def test_a_real_selection_puts_the_missing_candidates_after_the_unrenderable_settings() -> None:
    """AC-2, AC-3. expected_behavior_source: the interface item 2 (W545/W546 followed by W540) and
    item 3. The tester is pinned with an effort (ORQ-W546 for Cursor) and the arch reviewer has no
    eligible model (ORQ-W540): the first warning comes first although the reviewer sorts first.
    """
    policy = make_policy(
        [MODEL_A, secret_model("proposed")],
        [
            assignment_doc("role", ARCH, model=SECRET_ID),
            assignment_doc("role", TESTER, model="example-a", effort="high"),
        ],
    )

    outcome = follow(PolicyLoaded(policy))

    found = codes(outcome.findings)
    assert found == [W546, W540, W540, W540]
    selection = outcome.selection
    assert selection is not None
    assert codes(selection.findings) == [W546]
    assert codes(selection.missing) == [W540, W540, W540]
    assert outcome.findings == (*selection.findings, *selection.missing)


# =============================================================================================
# AC-2: ORQ-W540 missing-candidate
# =============================================================================================


@dataclass(frozen=True, slots=True)
class Missing:
    """One expected ORQ-W540: the target as the message names it, a client and the reasons."""

    target: str
    client: str
    pairs: tuple[str, ...]


def everywhere(target: str, *pairs: str) -> tuple[Missing, ...]:
    return tuple(Missing(target, client, pairs) for client in CLIENTS)


def other_model(model_id: str, state: str) -> dict[str, Any]:
    return entry(model_id, *routes_of(f"{model_id}-route"), state=state)


def manual_pin(state: str = "approved", **kwargs: Any) -> ModelPolicy:
    return make_policy(
        [secret_model(state, **kwargs)], [assignment_doc("role", TESTER, model=SECRET_ID)]
    )


def with_a_profile(profile: dict[str, Any], mode: str, *models: dict[str, Any]) -> ModelPolicy:
    """The tester assigned to `profile` in `mode`; the profile has the mode of its own document."""
    return make_policy(
        list(models),
        [assignment_doc("role", TESTER, profile=profile["id"], mode=mode)],
        profiles=[profile],
    )


def missing_scenarios() -> dict[str, tuple[ModelPolicy, tuple[Missing, ...]]]:
    role = f"role {TESTER}"
    proposed = secret_model("proposed")
    only_claude = secret_model(clients=(CLAUDE,))
    claude_pin = [assignment_doc("role", TESTER, model=SECRET_ID)]
    return {
        "a manual model that is only proposed": (
            manual_pin("proposed"),
            everywhere(role, "assignment not-approved"),
        ),
        "a manual model that is disabled": (
            manual_pin("disabled"),
            everywhere(role, "assignment disabled-or-retired"),
        ),
        "a manual model that is retired": (
            manual_pin("retired"),
            everywhere(role, "assignment disabled-or-retired"),
        ),
        "a manual model with a route for one client only": (
            make_policy([only_claude], claude_pin),
            (
                Missing(role, CODEX, ("assignment no-route-for-client",)),
                Missing(role, CURSOR, ("assignment no-route-for-client",)),
            ),
        ),
        "a manual model whose route name is unknown": (
            make_policy(
                [entry(SECRET_ID, *(route(c, None) for c in CLIENTS))],
                claude_pin,
            ),
            everywhere(role, "assignment route-name-unknown"),
        ),
        "a manual model whose route is blocked": (
            manual_pin(access="blocked"),
            everywhere(role, "assignment access-blocked"),
        ),
        "a manual profile whose candidates are not approved": (
            with_a_profile(
                profile_doc("engineering", mode="automatic", candidates=[SECRET_ID]),
                "manual",
                proposed,
            ),
            everywhere(role, "candidate not-approved"),
        ),
        "two candidates that fail for the same reason": (
            with_a_profile(
                profile_doc(
                    "engineering", mode="automatic", candidates=[SECRET_ID, f"{MARKER}-second"]
                ),
                "manual",
                proposed,
                other_model(f"{MARKER}-second", "proposed"),
            ),
            everywhere(role, "candidate not-approved"),
        ),
        "two candidates that fail for two reasons": (
            with_a_profile(
                profile_doc(
                    "engineering", mode="automatic", candidates=[SECRET_ID, f"{MARKER}-other"]
                ),
                "manual",
                proposed,
                other_model(f"{MARKER}-other", "disabled"),
            ),
            everywhere(role, "candidate not-approved", "candidate disabled-or-retired"),
        ),
        "a fallback mode whose fallbacks are not approved": (
            with_a_profile(
                profile_doc("economy", mode="automatic", fallbacks=[SECRET_ID]),
                "automatic-with-fallbacks",
                proposed,
            ),
            everywhere(role, "fallback not-approved"),
        ),
        "a fallback mode with no fallback listed": (
            with_a_profile(
                profile_doc("economy", mode="automatic"),
                "automatic-with-fallbacks",
                secret_model(),
            ),
            everywhere(role),
        ),
        "an assignment that is scoped to one client": (
            make_policy(
                [proposed], [assignment_doc("role", TESTER, model=SECRET_ID, client=CODEX)]
            ),
            (Missing(role, CODEX, ("assignment not-approved",)),),
        ),
        "a skill assignment that is scoped to Claude Code": (
            make_policy(
                [proposed], [assignment_doc("skill", REVIEW, model=SECRET_ID, client=CLAUDE)]
            ),
            (Missing(f"skill {REVIEW}", CLAUDE, ("assignment not-approved",)),),
        ),
        "two roles that have no eligible model": (
            make_policy(
                [proposed],
                [
                    assignment_doc("role", TESTER, model=SECRET_ID),
                    assignment_doc("role", INVENTORY, model=SECRET_ID),
                ],
            ),
            (
                *everywhere(f"role {INVENTORY}", "assignment not-approved"),
                *everywhere(role, "assignment not-approved"),
            ),
        ),
        "a manual profile with nothing eligible that no role uses": (
            make_policy(
                [proposed],
                [],
                profiles=[profile_doc("engineering", mode="manual", candidates=[SECRET_ID])],
            ),
            everywhere("profile engineering", "candidate not-approved"),
        ),
        "a manual profile that lists candidates for one client only": (
            make_policy(
                [secret_model()],
                [],
                profiles=[
                    profile_doc("quality", mode="manual", candidates=[SECRET_ID], clients=(CLAUDE,))
                ],
            ),
            (
                Missing("profile quality", CODEX, ()),
                Missing("profile quality", CURSOR, ()),
            ),
        ),
        "a fallback profile whose fallbacks are not approved": (
            make_policy(
                [proposed],
                [],
                profiles=[
                    profile_doc("economy", mode="automatic-with-fallbacks", fallbacks=[SECRET_ID])
                ],
            ),
            everywhere("profile economy", "fallback not-approved"),
        ),
    }


def clean_scenarios() -> dict[str, ModelPolicy]:
    """Policies for which no model is missing."""
    proposed = secret_model("proposed")
    return {
        "a manual model with a route for every client": manual_pin(),
        "the mode automatic with a model that is only proposed": make_policy(
            [proposed], [assignment_doc("role", TESTER, model=SECRET_ID, mode="automatic")]
        ),
        "a fallback mode that pins a model that is only proposed": make_policy(
            [proposed],
            [assignment_doc("role", TESTER, model=SECRET_ID, mode="automatic-with-fallbacks")],
        ),
        "a task-scoped manual assignment with nothing eligible": make_policy(
            [proposed], [assignment_doc("role", TESTER, model=SECRET_ID, task="example-task")]
        ),
        "a manual profile with eligible candidates": with_a_profile(
            profile_doc("engineering", mode="manual", candidates=["example-a"]),
            "manual",
            MODEL_A,
        ),
        "a fallback profile with an eligible fallback": with_a_profile(
            profile_doc("economy", mode="automatic-with-fallbacks", fallbacks=["example-a"]),
            "automatic-with-fallbacks",
            MODEL_A,
        ),
        "a profile in the mode automatic with nothing eligible": make_policy(
            [proposed],
            [],
            profiles=[profile_doc("engineering", mode="automatic", candidates=[SECRET_ID])],
        ),
        "a policy with no assignment and no profile": make_policy([MODEL_A], []),
    }


LEVELS = ("override", "assignment", "candidate", "fallback")
REASONS = (
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


def missing_of(policy: ModelPolicy) -> list[Finding]:
    outcome = follow(PolicyLoaded(policy))
    assert outcome.refused is False
    return of_code(outcome.findings, W540)


@pytest.mark.parametrize("case", list(missing_scenarios()))
def test_a_missing_candidate_is_one_warning_for_each_target_and_client(case: str) -> None:
    """AC-2. expected_behavior_source: plan P-6 AC-2 ("For each profile or assignment in mode
    `manual` with no eligible candidate, and for an `automatic-with-fallbacks` one with no eligible
    fallback, `upgrade` prints ORQ-W540 (`missing-candidate`) naming the target and the closed
    reason of each rejected candidate"); BC-4; BC-37; F-3; the interface item 3 (one finding for
    each assignment or profile and each enabled client that the assignment applies to; the message
    names the target `role <name>`, `skill <name>` or `profile <id>`, the client, and the distinct
    closed reasons as `<level> <reason>` pairs, or says none is listed; no model id or route name).
    """
    policy, expected = missing_scenarios()[case]
    found = missing_of(policy)

    assert len(found) == len(expected)
    for item in expected:
        matching = [f for f in found if item.target in f.message and item.client in f.message]
        assert len(matching) == 1, item
        finding = matching[0]
        assert finding.severity is Severity.WARNING
        assert finding.path is None
        for pair in item.pairs:
            assert finding.message.count(pair) == 1, (item, pair)
        wanted = set(item.pairs)
        for level in LEVELS:
            for reason in REASONS:
                pair = f"{level} {reason}"
                assert (pair in finding.message) == (pair in wanted), (item, pair)
        if not item.pairs:
            assert "none" in finding.message.lower()
    no_leak(found)


@pytest.mark.parametrize("case", list(clean_scenarios()))
def test_no_warning_is_given_when_nothing_is_missing(case: str) -> None:
    """AC-2. expected_behavior_source: plan P-6 AC-2 (only a `manual` target with no eligible
    candidate and an `automatic-with-fallbacks` one with no eligible fallback); the interface item
    3 ("Task-scoped assignments give no finding; a model-pinning assignment in
    `automatic-with-fallbacks` gives none"); ADR-001 decision 7 (a task-scoped assignment is
    never rendered).
    """
    assert missing_of(clean_scenarios()[case]) == []


def test_a_target_with_a_missing_candidate_is_pinned_for_no_client() -> None:
    """AC-2. expected_behavior_source: plan P-6 AC-2 ("nothing is pinned and the role keeps its
    automatic setting"); the interface item 3 ("Nothing is pinned for such a target").
    """
    outcome = follow(PolicyLoaded(manual_pin("proposed")))

    selection = outcome.selection
    assert selection is not None
    assert dict(selection.roles) == {}
    assert dict(selection.skills) == {}
    assert len(of_code(outcome.findings, W540)) == 3


def test_select_models_keeps_the_missing_findings_apart_from_the_others() -> None:
    """AC-2. expected_behavior_source: the interface item 2 (`ModelSelection` gains `missing:
    tuple[Finding, ...] = ()`; its `findings` stay the W545 and W546 ones); P-5 test of
    `select_models` pins `findings == ()` for a target with no eligible candidate.
    """
    selection = model_selection.select_models(
        manual_pin("proposed"), ROLE_NAMES, SKILL_NAMES, CLIENTS
    )

    assert selection.findings == ()
    assert codes(selection.missing) == [W540, W540, W540]
    assert selection.problems == ()
    refused = model_selection.select_models(
        make_policy([MODEL_A], [assignment_doc("role", "example-no-such-role", model="example-a")]),
        ROLE_NAMES,
        SKILL_NAMES,
        CLIENTS,
    )
    assert refused.problems
    assert refused.missing == ()
    assert refused.entries == ()


def test_upgrade_prints_the_missing_candidate_and_changes_no_file() -> None:
    """AC-2. expected_behavior_source: plan P-6 AC-2 (`upgrade` prints ORQ-W540; "nothing is
    pinned and the role keeps its automatic setting"); BC-37; the interface item 3 ("its generated
    file equals the no-policy file") and item 5 (the outcome findings are in `result.findings`).
    """
    env = initialised()
    install(
        env,
        policy_doc([secret_model("proposed")], [assignment_doc("role", TESTER, model=SECRET_ID)]),
    )
    before = tree(env.project)

    result = upgrade(env.services(), MODES["apply"])

    assert result.status == "up-to-date"
    assert result.plan is not None
    assert result.plan.is_empty
    assert tree(env.project) == before
    found = of_code(result.findings, W540)
    assert len(found) == 3
    assert all(TESTER in f.message for f in found)
    assert sorted(c for f in found for c in CLIENTS if c in f.message) == sorted(CLIENTS)
    no_leak(result.findings)
    assert written_pin(tree(env.project), CLAUDE, "role", TESTER) is None


@pytest.mark.parametrize("mode", list(MODES))
def test_a_client_with_a_model_is_pinned_while_the_others_get_the_warning(mode: str) -> None:
    """AC-2. expected_behavior_source: plan P-6 AC-2 ("nothing is pinned" for the target and
    client that lack a candidate); the interface item 3 (one finding for each enabled client that
    the assignment applies to) and item 5. The model has a route for Claude Code only: that file
    is pinned, and the Codex and Cursor files stay what they were; both get ORQ-W540.
    """
    env = initialised()
    before = tree(env.project)
    install(
        env,
        policy_doc(
            [secret_model(clients=(CLAUDE,))], [assignment_doc("role", TESTER, model=SECRET_ID)]
        ),
    )

    result = upgrade(env.services(), MODES[mode])

    assert result.status == STATUS_WITH_A_PLAN[mode]
    found = of_code(result.findings, W540)
    assert sorted(client for f in found for client in (CODEX, CURSOR) if client in f.message) == [
        CODEX,
        CURSOR,
    ]
    assert len(found) == 2
    assert result.plan is not None
    changed = {str(w.path) for w in result.plan.writes}
    assert ROLE_PATH[CLAUDE].format(TESTER) in changed
    assert ROLE_PATH[CODEX].format(TESTER) not in changed
    assert ROLE_PATH[CURSOR].format(TESTER) not in changed
    if mode == "apply":
        after = tree(env.project)
        assert after[ROLE_PATH[CODEX].format(TESTER)] == before[ROLE_PATH[CODEX].format(TESTER)]
        assert after[ROLE_PATH[CURSOR].format(TESTER)] == before[ROLE_PATH[CURSOR].format(TESTER)]
        assert written_pin(after, CLAUDE, "role", TESTER) == (f"{SECRET_ROUTES}-claude-code", None)
    no_leak(result.findings)


# =============================================================================================
# AC-1: a policy that cannot be used refuses the upgrade before any write
# =============================================================================================


def body(size: int, unit: str = "aB3") -> str:
    return (unit * (size // len(unit) + 1))[:size]


# A key-shaped string is built at run time from parts (ORQLET-SEC-003); it is no real key.
KEY_SHAPED = "s" + "k-" + body(24)


def arrange_directory(env: Env) -> None:
    env.project.delete(CanonicalPath.parse(POLICY_PATH))  # the seed that init wrote
    env.project.make_dir(CanonicalPath.parse(POLICY_PATH))


def arrange_repeated_key(env: Env) -> None:
    put(env, POLICY_PATH, f"schema: orqlet.model-policy/v2\n{MARKER}: 1\n{MARKER}: 2\n".encode())


def arrange_too_large(env: Env) -> None:
    raw = document(pin_doc())
    filler = 256 * 1024 + 1 - len(raw) - len(f"\n# {MARKER}\n")
    put(env, POLICY_PATH, raw + f"\n# {MARKER}".encode() + b"x" * filler + b"\n")


def arrange_contract_failure(env: Env) -> None:
    data = pin_doc()
    data["policy_version"] = 0
    data[f"{MARKER}-field"] = MARKER
    put(env, POLICY_PATH, document(data))


def arrange_v1(env: Env) -> None:
    put(env, POLICY_PATH, document({"schema": "orqlet.model-policy/v1", MARKER: MARKER}))


def arrange_credential(env: Env) -> None:
    data = pin_doc()
    data["excluded"] = [
        exclusion("rule-x", id_patterns=[f"{MARKER}-*"], reason=f"{MARKER} {KEY_SHAPED}")
    ]
    put(env, POLICY_PATH, document(data))


def arrange_deleted(env: Env) -> None:
    """The policy file is gone and the lock that init wrote still lists it as seeded."""
    env.project.delete(CanonicalPath.parse(POLICY_PATH))


def arrange_excluded_model(env: Env) -> None:
    excluded = entry(f"{MARKER}-excluded", route(CLAUDE, "claude-fable-9"))
    data = policy_doc(
        [MODEL_A, excluded],
        [assignment_doc("role", TESTER, model="example-a")],
        excluded=[exclusion("rule-fable", id_patterns=["claude-fable-*"])],
    )
    put(env, POLICY_PATH, document(data))


def arrange_unknown_role(env: Env) -> None:
    data = policy_doc(
        [MODEL_A],
        [
            assignment_doc("role", TESTER, model="example-a"),
            assignment_doc("role", f"{MARKER}-no-such-role", model="example-a"),
        ],
    )
    put(env, POLICY_PATH, document(data))


# case -> (how the project is made, the code of the refusal, a field path that the message holds)
REFUSED: dict[str, tuple[Callable[[Env], None], str, str | None]] = {
    "the policy path is a directory": (arrange_directory, E540, None),
    "a repeated key": (arrange_repeated_key, E540, None),
    "a file over 256 KiB": (arrange_too_large, E540, None),
    "a contract failure": (arrange_contract_failure, E541, "policy_version"),
    "a v1 file": (arrange_v1, E541, None),
    "a credential-shaped value": (arrange_credential, E542, None),
    "a deleted policy": (arrange_deleted, E547, None),
    "an excluded model": (arrange_excluded_model, E543, "models[1]"),
    "a role that does not exist": (arrange_unknown_role, E545, "assignments[1].target.name"),
}


@pytest.mark.parametrize("mode", list(MODES))
@pytest.mark.parametrize("case", list(REFUSED))
def test_a_policy_that_cannot_be_used_refuses_before_any_plan_or_write(
    case: str, mode: str
) -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 ("`upgrade` returns `refused` ... and writes
    nothing, in a normal run and with `--dry-run` and `--check`, when the policy is invalid
    (ORQ-E540, ORQ-E541, ORQ-E542), deleted (the file is missing and the lock records it as
    seeded; ORQ-E547), a v1 file, or fails `policy_problems` (ORQ-E543, ORQ-E545). Each refusal
    prints the code, the fixed text and a field path, and no value of the file"); BC-37; F-1; F-2;
    F-16; C-3; BC-32; the interface item 5 (the refusal comes before any plan, check, dry run or
    write, with the tree and the journal untouched). The marker is in a key, a value or a model id
    of each file, and a key-shaped string is in one.
    """
    arrange, code, where = REFUSED[case]
    env = initialised()
    arrange(env)
    project, journal = tree(env.project), tree(env.user_data)
    installed = load_installation(env.services()).installed_release

    result = upgrade(env.services(), MODES[mode])

    assert result.status == "refused"
    refusal = of_code(result.findings, code)
    assert refusal
    assert all(f.severity is Severity.ERROR for f in refusal)
    if where is not None:
        assert any(where in f.message for f in refusal)
    assert result.plan is None
    assert result.change_id is None
    assert result.installed == installed
    assert result.candidate == PINNED.release
    assert tree(env.project) == project
    assert tree(env.user_data) == journal
    no_leak(result.findings, KEY_SHAPED)


def test_a_policy_with_two_kinds_of_problem_is_refused_for_both() -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 (ORQ-E543 and ORQ-E545); the interface item 2
    (one finding for each code): the excluded model and the unknown role in one file.
    """
    env = initialised()
    excluded = entry(f"{MARKER}-excluded", route(CLAUDE, "claude-fable-9"))
    install(
        env,
        policy_doc(
            [MODEL_A, excluded],
            [assignment_doc("role", f"{MARKER}-no-such-role", model="example-a")],
            excluded=[exclusion("rule-fable", id_patterns=["claude-fable-*"])],
        ),
    )

    result = upgrade(env.services(), MODES["check"])

    assert result.status == "refused"
    assert sorted(code for code in codes(result.findings) if code in {E543, E545}) == [E543, E545]
    no_leak(result.findings)


def test_a_valid_policy_is_not_refused() -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 (only an invalid, deleted or v1 policy, or one
    that fails `policy_problems`, is refused); a control for the tests above.
    """
    env = initialised()
    install(env, pin_doc())

    result = upgrade(env.services(), MODES["apply"])

    assert result.status == "applied"
    assert not {E540, E541, E542, E543, E545, E547} & set(codes(result.findings))


def test_a_refusal_for_an_older_release_comes_before_the_refusal_for_the_policy() -> None:
    """AC-1. expected_behavior_source: the interface item 5 ("Refusal order: existing refusals
    first, then the policy"). A downgrade (ORQ-E120) and an invalid policy: the first error is the
    downgrade. This passes before the implementation; it guards the order.
    """
    env = initialised()
    env.workflow = ChangedWorkflow(PINNED, version="0.2.0", controls_level=2)
    env.ids = SequentialIds(start=100)
    assert upgrade(env.services(), MODES["apply"]).status == "applied"
    env.workflow = None
    arrange_repeated_key(env)

    result = upgrade(env.services(), MODES["apply"])

    assert result.status == "refused"
    assert first_error(result.findings).code == "ORQ-E120"


def test_a_refusal_for_an_unfinished_change_comes_before_the_refusal_for_the_policy() -> None:
    """AC-1. expected_behavior_source: the interface item 5 ("existing refusals first, then the
    policy"). An interrupted change (ORQ-E131) and an invalid policy: the first error is the
    unfinished change. This passes before the implementation; it guards the order.
    """
    env = initialised()
    env.workflow = NEXT
    env.ids = SequentialIds(start=100)
    env.project_view = FaultyFileSystem(env.project, crash_after_writes=2)
    with pytest.raises(SimulatedCrash):
        upgrade(env.services(), MODES["apply"])
    env.project_view = None
    arrange_repeated_key(env)

    result = upgrade(env.services(), MODES["apply"])

    assert result.status == "refused"
    assert first_error(result.findings).code == "ORQ-E131"


# What the upgrade of a project with no policy file writes, as it did before this phase.
NO_POLICY_PLAN = [
    (".github/pull_request_template.md", "update", False),
    (".orqlet/proposals/.orqlet__versions.yaml.diff", "create", True),
    (".orqlet/workflow.lock", "update", False),
    ("AGENTS.md", "update", False),
    (".orqlet/generated.lock.yaml", "update", False),
]
NO_POLICY_CODES = {
    "ORQ-I030",
    "ORQ-I031",
    "ORQ-L001",
    "ORQ-L002",
    "ORQ-L003",
    "ORQ-L004",
    "ORQ-L005",
    "ORQ-L006",
}


@pytest.mark.parametrize("mode", list(MODES))
def test_with_no_policy_file_the_upgrade_plan_is_the_one_of_before(mode: str) -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 ("With no policy file ever present the upgrade
    plan equals the plan before this phase"); EC-8. The next release is installed over an
    initialised project that never had a policy: the writes (path, kind, proposal) and the set of
    finding codes are those that the code of HEAD gives, and no policy finding is added. This
    passes before the implementation; it is a regression check.
    """
    env = initialised()
    env.workflow = NEXT
    env.ids = SequentialIds(start=100)

    result = upgrade(env.services(), MODES[mode])

    assert result.status == STATUS_WITH_A_PLAN[mode]
    assert result.plan is not None
    assert [(str(w.path), w.kind, w.is_proposal) for w in result.plan.writes] == NO_POLICY_PLAN
    assert set(codes(result.findings)) == NO_POLICY_CODES


def test_with_no_policy_file_an_unchanged_project_is_up_to_date() -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 (no policy file, the plan of before); EC-8.
    This passes before the implementation; it is a regression check.
    """
    env = initialised()
    before = tree(env.project)

    result = upgrade(env.services(), MODES["apply"])

    assert result.status == "up-to-date"
    assert tree(env.project) == before
    assert set(codes(result.findings)) == NO_POLICY_CODES


# =============================================================================================
# AC-3: ORQ-W545 and ORQ-W546 in the findings of the upgrade
# =============================================================================================


def leaky_doc() -> dict[str, Any]:
    """A policy with an alias model and a model whose Cursor name needs quotes; marked.

    The tester takes the alias with an effort, the inventory takes the plain model, and the review
    skill takes the plain model for every client.
    """
    alias = entry(
        f"{MARKER}-alias",
        *(
            route(c, f"{MARKER}-alias-{c}", kind="alias", resolves_to=f"{MARKER}-alias-{c}-1")
            for c in CLIENTS
        ),
    )
    plain = entry(
        f"{MARKER}-plain",
        route(CLAUDE, f"{MARKER}-plain-claude"),
        route(CODEX, f"{MARKER}-plain-codex"),
        route(CURSOR, f"{MARKER}:plain-cursor"),
    )
    return policy_doc(
        [alias, plain],
        [
            assignment_doc("role", TESTER, model=f"{MARKER}-alias", effort="high"),
            assignment_doc("role", INVENTORY, model=f"{MARKER}-plain"),
            assignment_doc("skill", REVIEW, model=f"{MARKER}-plain"),
        ],
    )


# What the leaky policy must report: roles by name, then skills; clients in the enabled order.
LEAKY_FINDINGS = [
    (W546, INVENTORY, CURSOR),
    (W545, TESTER, CLAUDE),
    (W545, TESTER, CODEX),
    (W546, TESTER, CURSOR),
    (W546, REVIEW, CODEX),
    (W546, REVIEW, CURSOR),
]


def described(finding: Finding) -> tuple[str, str, str]:
    targets = [name for name in (*ROLE_NAMES, *SKILL_NAMES) if name in finding.message]
    clients = [client for client in CLIENTS if client in finding.message]
    assert len(targets) == 1, finding
    assert len(clients) == 1, finding
    return finding.code, targets[0], clients[0]


@pytest.mark.parametrize("mode", list(MODES))
def test_the_upgrade_reports_the_alias_pins_and_the_settings_a_client_cannot_take(
    mode: str,
) -> None:
    """AC-3. expected_behavior_source: plan P-6 AC-3 ("The findings ORQ-W545 (alias route
    rendered) and ORQ-W546 (a skill assignment for Codex or Cursor, a Cursor effort, a name that
    Cursor cannot take unquoted) appear in the preview of `upgrade` and in `explain`, and each
    prints only a fixed text and the target"); BC-43; BC-7; F-4; F-17; BC-32; the interface item 5
    (the outcome findings are in `result.findings` of every run that is not refused, a preview and
    a check included).
    """
    env = initialised()
    install(env, leaky_doc())

    result = upgrade(env.services(), MODES[mode])

    assert result.status == STATUS_WITH_A_PLAN[mode]
    policy_findings = [f for f in result.findings if f.code in {W545, W546}]
    assert [described(f) for f in policy_findings] == LEAKY_FINDINGS
    assert all(f.severity is Severity.WARNING for f in policy_findings)
    assert of_code(result.findings, W540) == []
    no_leak(policy_findings, f"{MARKER}:plain-cursor")


def test_the_alias_that_the_warning_names_is_the_one_that_is_written() -> None:
    """AC-3. expected_behavior_source: plan P-6 AC-3 (ORQ-W545 "alias route rendered"); BC-43; the
    interface item 3 of the P-5 brief that a pin is the exact route name: the file holds the name
    that the warning leaves out.
    """
    env = initialised()
    install(env, leaky_doc())

    upgrade(env.services(), MODES["apply"])

    files = tree(env.project)
    assert written_pin(files, CLAUDE, "role", TESTER) == (f"{MARKER}-alias-claude-code", "high")
    assert written_pin(files, CODEX, "role", TESTER) == (f"{MARKER}-alias-codex", "high")
    assert written_pin(files, CURSOR, "role", TESTER) is None
    assert written_pin(files, CURSOR, "role", INVENTORY) is None


# =============================================================================================
# AC-4: ORQ-W547, the review records that a pin makes stale
# =============================================================================================

FIXTURE = FIXTURES / "contracts" / "valid" / "orqlet.review-result.v1.yaml"


def add_record(
    env: Env,
    *,
    task: str = "demo",
    role: str = "architecture-reviewer",
    phase: str = "P-1",
    round_no: int = 1,
    client: str = CLAUDE,
    ref: str = ARCH,
) -> str:
    """Write a valid review record into the project and return its path."""
    data = LOADER.load(FIXTURE.read_bytes(), source="fixture")
    assert isinstance(data, dict)
    data.update(task=task, role=role, phase=phase, round=round_no)
    data["agent"].update(client=client, binding_ref=ref)
    path = f"docs/design/{task}/reviews/{role}-{phase}-r{round_no}.yaml"
    put(env, path, document(data))
    return path


def arch_pin_for(*clients: str) -> dict[str, Any]:
    """The arch reviewer pinned to a model that has a route for each client given."""
    model = entry("example-a", *routes_of("example-a", clients))
    return policy_doc([model], [assignment_doc("role", ARCH, model="example-a")])


@pytest.mark.parametrize("mode", list(MODES))
def test_a_pin_that_changes_an_agent_file_lists_the_records_that_name_it(mode: str) -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("When the plan changes the bytes of an agent
    file that an earlier review record names (`agent.binding_ref` and `agent.client`), `upgrade`
    prints ORQ-W547 with the path of each such record ... The text says that a pin changes
    protected files and `protected_set_digest`, that approvals of designs and plans in flight then
    show ORQ-W390 and that the person decides"); BC-37; F-12; ADR-003 decision 7; C-8; the
    interface item 5 (ORQ-W547 is added after the plan is built). The message no longer names
    the field or the code: workflow-efficiency plan P-5 AC-3 and ADR-002 decision 5 (reworked
    for that reason only). The model has a route for Claude
    Code only, so only the Claude Code file of the arch reviewer changes: the two records of that
    file are listed, and the records of the Cursor file, the Codex file and the security reviewer
    are not.
    """
    env = initialised()
    install(env, arch_pin_for(CLAUDE))
    stale = [
        add_record(env, task="alpha", round_no=1),
        add_record(env, task="beta", round_no=2, phase="P-3"),
    ]
    fresh = [
        add_record(env, task="gamma", client=CURSOR),
        add_record(env, task="delta", client=CODEX),
        add_record(env, task="epsilon", role="security-reviewer", ref=SECURITY),
    ]
    records = {path: read(env, path) for path in (*stale, *fresh)}

    result = upgrade(env.services(), MODES[mode])

    assert result.status == STATUS_WITH_A_PLAN[mode]
    found = of_code(result.findings, W547)
    assert len(found) == 1
    finding = found[0]
    assert finding.severity is Severity.WARNING
    assert all(path in finding.message for path in stale)
    assert not any(path in finding.message for path in fresh)
    assert "ORQ-" not in finding.message  # workflow-efficiency P-5 AC-3: no finding code
    assert "protected_set_digest" not in finding.message  # ... and no internal field name
    assert "person" in finding.message
    assert result.plan is not None
    assert not {str(w.path) for w in result.plan.writes} & set(records)
    assert {path: read(env, path) for path in records} == records


def test_the_warning_lists_twenty_records_and_counts_the_others() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("at most 20, then the count"); the interface
    item 7 (at most 20 paths, then `and N more`). Twenty-five stale records are sorted by path:
    the first twenty are listed.
    """
    env = initialised()
    install(env, arch_pin_for(CLAUDE))
    paths = sorted(add_record(env, task=f"task-{n:02d}") for n in range(25))

    result = upgrade(env.services(), MODES["check"])

    found = of_code(result.findings, W547)
    assert len(found) == 1
    finding = found[0]
    assert all(path in finding.message for path in paths[:20])
    assert not any(path in finding.message for path in paths[20:])
    assert "and 5 more" in finding.message


def test_no_warning_is_given_when_the_pin_changes_no_file_that_a_record_names() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 (only an agent file that a record names);
    BC-37. The tester is pinned, and the records name the two reviewers, so no record is stale.
    """
    env = initialised()
    install(env, pin_doc(TESTER))
    add_record(env, task="alpha")
    add_record(env, task="beta", role="security-reviewer", ref=SECURITY)

    result = upgrade(env.services(), MODES["check"])

    assert result.status == "available"
    assert of_code(result.findings, W547) == []


def test_no_warning_is_given_without_a_policy_even_when_records_exist() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 and AC-1 (no policy, the plan of before): the
    next release changes no agent file, so no record is stale. This passes before the
    implementation; it is a regression check.
    """
    env = initialised()
    env.workflow = NEXT
    add_record(env, task="alpha")

    result = upgrade(env.services(), MODES["check"])

    assert of_code(result.findings, W547) == []


# =============================================================================================
# AC-5: ORQ-I540, a role binding that waits for a reviewed edit
# =============================================================================================


def bindings_proposal() -> str:
    return str(proposal_path(CanonicalPath.parse(BINDINGS_PATH), None))


@pytest.mark.parametrize("mode", list(MODES))
def test_a_proposal_that_adds_the_code_reviewer_binding_is_announced(mode: str) -> None:
    """AC-5. expected_behavior_source: plan P-6 AC-5 ("When the plan holds a proposal for
    `.orqlet/role-bindings.yaml` that adds a binding for `orqlet-code-reviewer`, `upgrade` prints
    ORQ-I540 saying that a `code-reviewer` record is ORQ-E415 until a reviewed edit applies the
    proposal. Orqlet never applies it."); BC-37; F-13; ADR-006 consequences; the interface item 8
    (an information finding; the message says a `code-reviewer` record is ORQ-E415 until a reviewed
    edit applies the proposal, and that Orqlet never applies it).
    """
    env = initialised()

    with code_reviewer_binding():
        result = upgrade(env.services(), MODES[mode])

    assert result.status == STATUS_WITH_A_PLAN[mode]
    assert result.plan is not None
    proposal = [w for w in result.plan.writes if str(w.path) == bindings_proposal()]
    assert len(proposal) == 1
    assert proposal[0].is_proposal
    found = of_code(result.findings, I540)
    assert len(found) == 1
    assert found[0].severity is Severity.INFO
    text = found[0].message
    assert "code-reviewer" in text
    assert "ORQ-E415" in text
    assert "reviewed edit" in text
    assert "never" in text


def test_the_binding_file_is_never_changed_and_only_the_proposal_is_written() -> None:
    """AC-5, AC-8. expected_behavior_source: plan P-6 AC-5 ("Orqlet never applies it") and AC-8
    ("Every pin and every proposal reaches disk through the journalled change plan"); ADR-004
    (seeded files change only as proposals). The bindings bytes are the same before and after, and
    again after a second upgrade; the proposal is a journalled write that is marked as one.
    """
    env = initialised()
    before = tree(env.project)

    with code_reviewer_binding():
        first = upgrade(env.services(), MODES["apply"])
        second = upgrade(env.services(), MODES["apply"])

    after = tree(env.project)
    assert read(env, BINDINGS_PATH) == before[BINDINGS_PATH]
    assert set(after) - set(before) == {bindings_proposal()}
    assert [path for path in before if after[path] != before[path]] == []
    assert first.change_id is not None
    assert second.status in {"up-to-date", "applied"}
    project_id = load_installation(env.services()).profile.project.uuid
    record = FsChangeJournal(env.user_data, project_id).read(first.change_id)
    assert record is not None
    assert [(e.path, e.is_proposal, e.done) for e in record.entries] == [
        (bindings_proposal(), True, True)
    ]


def test_no_announcement_is_made_when_the_binding_is_already_on_disk() -> None:
    """AC-5. expected_behavior_source: plan P-6 AC-5 (a proposal "that adds a binding for
    `orqlet-code-reviewer`"); the interface item 8 ("the wanted bindings add `orqlet-code-reviewer`
    that the on-disk file lacks"). The project is initialised with the binding, so there is none to
    add.
    """
    with code_reviewer_binding():
        env = initialised()
        result = upgrade(env.services(), MODES["apply"])

    assert result.status == "up-to-date"
    assert of_code(result.findings, I540) == []
    assert bindings_proposal() not in tree(env.project)


def test_no_announcement_is_made_for_a_proposal_that_adds_another_binding() -> None:
    """AC-5. expected_behavior_source: the interface item 8 ("the wanted bindings add
    `orqlet-code-reviewer` that the on-disk file lacks"): the proposal adds a reviewer of the
    security role that the file lacks, and the code reviewer is already on disk.
    """
    with code_reviewer_binding():
        env = initialised()
    extra = ("security-reviewer", "orqlet-extra-reviewer")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            render_all, "REVIEW_AGENTS", (*render_all.REVIEW_AGENTS, CODE_REVIEWER, extra)
        )
        result = upgrade(env.services(), MODES["check"])

    assert result.plan is not None
    assert bindings_proposal() in {str(w.path) for w in result.plan.writes}
    assert of_code(result.findings, I540) == []


def test_no_announcement_is_made_when_the_plan_holds_no_bindings_proposal() -> None:
    """AC-5. expected_behavior_source: plan P-6 AC-5 (only a proposal for the bindings file; a plan
    that holds none gets no announcement). This passes before the implementation; it is a
    regression check.
    """
    env = initialised()
    env.workflow = NEXT

    result = upgrade(env.services(), MODES["check"])

    assert of_code(result.findings, I540) == []


# =============================================================================================
# AC-6: reverting a policy edit restores the files byte for byte
# =============================================================================================


def pin_two_doc() -> dict[str, Any]:
    """The tester and the review skill, both manual on `example-a`."""
    return policy_doc(
        [MODEL_A],
        [
            assignment_doc("role", TESTER, model="example-a"),
            assignment_doc("skill", REVIEW, model="example-a"),
        ],
    )


def unpin_two_doc() -> dict[str, Any]:
    """The same policy in the mode `automatic`: a valid file that pins nothing."""
    data = pin_two_doc()
    for item in data["assignments"]:
        item["mode"] = "automatic"
    return data


PINNED_FILES = {
    ROLE_PATH[CLAUDE].format(TESTER),
    ROLE_PATH[CODEX].format(TESTER),
    ROLE_PATH[CURSOR].format(TESTER),
    f".claude/skills/{REVIEW}/SKILL.md",
}


def test_reverting_a_policy_edit_restores_the_generated_files_byte_for_byte() -> None:
    """AC-6. expected_behavior_source: plan P-6 AC-6 ("Reverting a policy edit and running `upgrade`
    again restores the generated files of the earlier state byte for byte, tested with three
    upgrades (no pin, a pin, the edit reverted)"); BC-29; R-4; ADR-003 consequences. The first
    upgrade installs the next release with a policy that pins nothing; the second pins the tester
    and the review skill; the third writes the first policy back. The whole tree after the third
    equals the tree after the first, and the second differs from it in the policy file, the four
    pinned files and the lock, and in nothing else.
    """
    env = initialised()
    env.workflow = NEXT
    env.ids = SequentialIds(start=100)
    install(env, unpin_two_doc())
    first = upgrade(env.services(), MODES["apply"])
    after_none = tree(env.project)

    install(env, pin_two_doc())
    second = upgrade(env.services(), MODES["apply"])
    after_pin = tree(env.project)

    install(env, unpin_two_doc())
    third = upgrade(env.services(), MODES["apply"])
    after_revert = tree(env.project)

    assert (first.status, second.status, third.status) == ("applied", "applied", "applied")
    for client in CLIENTS:
        assert written_pin(after_none, client, "role", TESTER) is None
        assert written_pin(after_revert, client, "role", TESTER) is None
    assert written_pin(after_pin, CLAUDE, "role", TESTER) == ("example-a-claude-code", None)
    assert written_pin(after_pin, CODEX, "role", TESTER) == ("example-a-codex", None)
    assert written_pin(after_pin, CURSOR, "role", TESTER) == ("example-a-cursor", None)
    assert written_pin(after_pin, CLAUDE, "skill", REVIEW) == ("example-a-claude-code", None)
    assert written_pin(after_none, CLAUDE, "skill", REVIEW) is None
    assert set(after_pin) == set(after_none)
    changed = {path for path in after_none if after_pin[path] != after_none[path]}
    assert changed == {*PINNED_FILES, POLICY_PATH, LOCK_PATH}
    assert after_revert == after_none


# =============================================================================================
# AC-8: every pin and every proposal goes through the journalled plan; init composes with none
# =============================================================================================


def pinned_env() -> Env:
    env = initialised()
    install(env, pin_two_doc())
    return env


def test_every_changed_file_of_a_pin_is_a_journalled_write() -> None:
    """AC-8. expected_behavior_source: plan P-6 AC-8 ("Every pin and every proposal reaches disk
    through the journalled change plan"); C-5; ORQLET-SAFE-001; EC-8. The files that differ after
    a pin are exactly the paths of the plan, and the journal of the change lists each of them as
    done.
    """
    env = pinned_env()
    before = tree(env.project)

    result = upgrade(env.services(), MODES["apply"])

    after = tree(env.project)
    assert result.status == "applied"
    assert result.plan is not None
    assert result.change_id is not None
    changed = {path for path in after if after.get(path) != before.get(path)}
    assert changed == {str(w.path) for w in result.plan.writes}
    assert changed >= PINNED_FILES
    project_id = load_installation(env.services()).profile.project.uuid
    record = FsChangeJournal(env.user_data, project_id).read(result.change_id)
    assert record is not None
    assert record.command == "upgrade"
    assert record.status == "complete"
    assert {e.path for e in record.entries} == changed
    assert all(e.done for e in record.entries)


def planned_writes(proposal: bool) -> int:
    env = pinned_env()
    with binding_if(proposal):
        plan = upgrade(env.services(), MODES["check"]).plan
    assert plan is not None
    return len(plan.writes)


@pytest.mark.parametrize("proposal", [False, True], ids=["a-pin", "a-pin-and-a-proposal"])
def test_an_upgrade_that_is_cut_short_resumes_to_the_same_files(proposal: bool) -> None:
    """AC-8. expected_behavior_source: plan P-6 AC-8 ("a test with the faulty file system of
    tests/fakes shows that an interrupted upgrade with a pin resumes to the same files"); C-5;
    ORQLET-SAFE-001; EC-8; the pattern of `test_fm_u03_every_kill_point_of_an_upgrade_converges`
    of tests/unit/application/test_lifecycle.py. The upgrade is cut after each number of writes in
    turn, then run again with `--resume`; the tree is each time the tree of an upgrade that was not
    cut. The second case adds the proposal for the role bindings to the plan.
    """

    def run(env: Env, options: UpgradeOptions) -> UpgradeResult:
        with binding_if(proposal):
            return upgrade(env.services(), options)

    reference = pinned_env()
    assert run(reference, MODES["apply"]).status == "applied"
    expected = tree(reference.project)
    initial = tree(initialised().project)
    assert {p for p in expected if expected[p] != initial.get(p)} >= PINNED_FILES
    writes = planned_writes(proposal)
    assert writes >= len(PINNED_FILES) + (1 if proposal else 0)

    for crash_point in range(writes):
        env = pinned_env()
        env.project_view = FaultyFileSystem(env.project, crash_after_writes=crash_point)
        with pytest.raises(SimulatedCrash):
            run(env, MODES["apply"])
        env.project_view = None
        env.ids = SequentialIds(start=200)

        resumed = run(env, UpgradeOptions(assume_yes=True, resume=True))

        assert resumed.status == "applied", crash_point
        assert tree(env.project) == expected, f"cut after {crash_point} writes did not converge"


def test_init_composes_with_no_policy_whatever_the_project_holds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-8. expected_behavior_source: plan P-6 AC-8 ("`init` calls `compose` with no policy and
    its output is unchanged for a project that has none"); the interface item 9 (`init_project`
    calls `compose` with `policy=None` explicitly). The project already holds a valid policy that
    pins the tester: the call still passes `policy=None`, and the files of the init are the files
    of the same init without the policy file, apart from the policy file itself.
    """
    calls: list[dict[str, Any]] = []

    def recording(*args: Any, **kwargs: Any) -> Composition:
        calls.append(dict(kwargs))
        return compose(*args, **kwargs)

    monkeypatch.setattr(init_module, "compose", recording)
    plain = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    with_policy = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    install(with_policy, pin_two_doc())

    assert init_project(plain.services(), YES).status == "applied"
    plain_calls = len(calls)
    assert init_project(with_policy.services(), YES).status == "applied"

    assert plain_calls >= 1
    assert len(calls) > plain_calls
    assert [call.get("policy", "not passed") for call in calls] == [None] * len(calls)
    expected = tree(plain.project)
    actual = tree(with_policy.project)
    assert actual.pop(POLICY_PATH) == document(pin_two_doc())
    # Init writes its seed once. Over the team's file it proposes the seed in a diff and records
    # no lock row for the file; that is the whole difference, apart from the file itself.
    assert actual.pop(".orqlet/proposals/.orqlet__model-policy.yaml.diff")
    expected.pop(POLICY_PATH)
    assert without_policy_row(actual.pop(LOCK_PATH)) == without_policy_row(expected.pop(LOCK_PATH))
    assert actual == expected


def without_policy_row(lock: bytes) -> Any:
    document = LOADER.load(lock, source="lock")
    assert isinstance(document, dict)
    document["files"] = [row for row in document["files"] if row["path"] != POLICY_PATH]
    return document
