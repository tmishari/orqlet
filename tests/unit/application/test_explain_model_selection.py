"""`explain` shows the model selection that `upgrade` would write (P-6, AC-7).

It covers the rows of the selection (`SelectionEntry` and `ModelSelection.entries`), what `explain`
returns for them (`Explanation.model_selection` and `Explanation.model_findings`), and the command
`orqlet explain` through the real Typer app on the in-memory file system: its JSON data, its text
and its exit status. It also holds the exit status of `orqlet upgrade` for a refused policy (AC-1),
because it is the same app, the same fakes and the same fixture policy.

Every test cites its `expected_behavior_source`. AC-7 is an acceptance criterion of phase P-6 in
docs/design/dynamic-model-profiles/plan.yaml, and AC-1 and AC-3 are cited where they are touched.
BC-n are the behaviour rows of design/component.md and ADR-n the decision records of design/.
"The interface" is the interface that the Coder of this phase implements and that the brief of this
phase's Tester states, items 4, 6 and 10: `SelectionEntry(kind, target, client, source, setting)`
and `ModelSelection.entries`; `Explanation.model_selection` and `Explanation.model_findings`; and
the JSON `data["declared"]["model_selection"]` and the text section `Model selection:` of the CLI.

These tests were written first, by the Tester of phase P-6, before the implementation existed.
A policy is built in code as plain data and written as JSON text, which is YAML. The file system is
the in-memory fake and the VCS is `FakeVcs` (ORQLET-TEST-001); the CLI is run with
`build_init_services` replaced by a function that returns the services of the test, so no real
directory, git or home is used. A marker (`zq7leak`) is put in every string that a finding must
not repeat (BC-32); a key-shaped string is assembled from fragments at run time and is no real key
(ORQLET-SEC-003).

Behaviour that neither the plan nor the brief settle is deliberately not pinned here:
- the wording of a line of the text, beyond that it names the target, the client, the source and
  the setting name or `none`;
- whether the section `Model selection:` is printed for a project that has no policy (the tests
  that read the section use a project that has a policy);
- whether `Explanation.declared` also holds the entries (the JSON `data["declared"]` does; the
  tests read the field of `Explanation` and the JSON, never `Explanation.declared`);
- what `Explanation.findings` holds for a policy (only `model_findings` is read);
- whether a section line is printed for each entry when the policy is refused (none is expected).
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

import orqlet.application.usecases.explain as explain_module
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.instruction_adapter import ModelSetting
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases import model_selection
from orqlet.application.usecases.explain import explain
from orqlet.application.usecases.init_project import InitOptions, InitServices, init_project
from orqlet.application.usecases.model_policy_source import PolicyLoaded
from orqlet.application.usecases.render_all import Composition, compose
from orqlet.application.usecases.standards_for import StandardsQuery
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.paths import CanonicalPath
from orqlet.interface.cli.app import app
from tests.fakes.vcs import FakeVcs
from tests.support.init_env import Env, tree
from tests.support.render import ROLE_NAMES, SKILL_NAMES
from tests.support.trees import repo

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
MARKER = "zq7leak"
ARCH = "orqlet-arch-reviewer"
INVENTORY = "orqlet-inventory"
TESTER = "orqlet-tester"
TRACER = "orqlet-tracer"
DESIGN = "orqlet-design"
REVIEW = "orqlet-review"
POLICY_PATH = ".orqlet/model-policy.yaml"
LOCK_PATH = ".orqlet/generated.lock.yaml"
ROLE_PATH = {
    CLAUDE: ".claude/agents/{}.md",
    CURSOR: ".cursor/agents/{}.md",
    CODEX: ".codex/agents/{}.toml",
}
FENCE_END = "\n---\n"
QUERY = StandardsQuery(phase="design")
LOADER = StrictYamlLoader()
LIFECYCLE = "orqlet.interface.cli.commands.lifecycle"
RUNNER = CliRunner()


# --- policies built in code ---------------------------------------------------------------


def route(
    client: str,
    name: str | None,
    *,
    kind: str = "id",
    resolves_to: str | None = None,
) -> dict[str, Any]:
    return {
        "client": client,
        "kind": kind,
        "name": name,
        "resolves_to": resolves_to,
        "also_known_as": [],
        "access": "unknown",
    }


def entry(
    model_id: str, *routes: dict[str, Any], state: str = "approved", family: str = "example-family"
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


def routes_of(prefix: str, *, kind: str = "id") -> list[dict[str, Any]]:
    """One route for each client, named `<prefix>-<client>`; an alias resolves to `<name>-1`."""
    return [
        route(
            client,
            f"{prefix}-{client}",
            kind=kind,
            resolves_to=f"{prefix}-{client}-1" if kind == "alias" else None,
        )
        for client in CLIENTS
    ]


def profile_doc(
    profile_id: str, *, mode: str = "manual", candidates: Sequence[str] = ()
) -> dict[str, Any]:
    return {
        "id": profile_id,
        "capability": "Example capability.",
        "mode": mode,
        "candidates": [{"client": c, "models": list(candidates)} for c in CLIENTS if candidates],
        "fallbacks": [],
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
    effort: str | None = None,
) -> dict[str, Any]:
    return {
        "target": {"kind": kind, "name": name},
        "task": task,
        "client": None,
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
) -> ModelPolicy:
    return ModelPolicy.model_validate(policy_doc(models, assignments, profiles=profiles))


def document(data: dict[str, Any]) -> bytes:
    return json.dumps(data, indent=2).encode()


def selection_doc() -> dict[str, Any]:
    """The fixture policy of AC-7: every kind of row that a selection can give.

    - the arch reviewer has a manual model that is only proposed: a missing candidate;
    - the inventory takes an alias model: pinned with ORQ-W545 for every client;
    - the tester takes a model with an effort: Claude Code and Codex pin it, Cursor cannot;
    - the tracer is assigned to the profile `engineering`: a pin from a profile;
    - the review skill takes a model: Claude Code pins it, Codex and Cursor read no skill model;
    - the design skill is in the mode `automatic`: no setting and no finding, so no row.
    """
    models = [
        entry("example-a", *routes_of("example-a")),
        entry("example-b", *routes_of("example-b")),
        entry("example-alias", *routes_of("example-alias", kind="alias")),
        entry("example-proposed", *routes_of("example-proposed"), state="proposed"),
    ]
    assignments = [
        assignment_doc("role", ARCH, model="example-proposed"),
        assignment_doc("role", INVENTORY, model="example-alias"),
        assignment_doc("role", TESTER, model="example-a", effort="high"),
        assignment_doc("role", TRACER, profile="engineering"),
        assignment_doc("skill", REVIEW, model="example-a"),
        assignment_doc("skill", DESIGN, model="example-a", mode="automatic"),
    ]
    return policy_doc(
        models,
        assignments,
        profiles=[profile_doc("engineering", candidates=["example-b"])],
    )


Row = tuple[str, str, str, str, tuple[str, str, str | None] | None]


def pinned(prefix: str, kind: str = "id", effort: str | None = None) -> Callable[[str], Any]:
    return lambda client: (f"{prefix}-{client}", kind, effort)


def rows(
    kind: str, target: str, source: str, setting: Callable[[str], Any] | None, *clients: str
) -> list[Row]:
    return [
        (kind, target, client, source, None if setting is None else setting(client))
        for client in clients
    ]


# What the fixture policy gives: roles by name, then skills by name; clients in the enabled order.
EXPECTED_ROWS: list[Row] = [
    *rows("role", ARCH, "automatic", None, *CLIENTS),
    *rows("role", INVENTORY, "role-assignment", pinned("example-alias", "alias"), *CLIENTS),
    *rows("role", TESTER, "role-assignment", pinned("example-a", "id", "high"), CLAUDE, CODEX),
    *rows("role", TESTER, "role-assignment", None, CURSOR),
    *rows("role", TRACER, "profile-assignment", pinned("example-b"), *CLIENTS),
    *rows("skill", REVIEW, "role-assignment", pinned("example-a"), CLAUDE),
    *rows("skill", REVIEW, "role-assignment", None, CODEX, CURSOR),
]
# The findings of that policy, in order: W545 and W546 first, then W540.
EXPECTED_FINDINGS = [
    (W545, INVENTORY, CLAUDE),
    (W545, INVENTORY, CODEX),
    (W545, INVENTORY, CURSOR),
    (W546, TESTER, CURSOR),
    (W546, REVIEW, CODEX),
    (W546, REVIEW, CURSOR),
    (W540, ARCH, CLAUDE),
    (W540, ARCH, CODEX),
    (W540, ARCH, CURSOR),
]


def row_of(item: model_selection.SelectionEntry) -> Row:
    setting = item.setting
    return (
        item.kind,
        item.target,
        item.client,
        item.source,
        None if setting is None else (setting.name, setting.kind, setting.effort),
    )


def described(finding: Finding) -> tuple[str, str, str]:
    targets = [name for name in (*ROLE_NAMES, *SKILL_NAMES) if name in finding.message]
    clients = [client for client in CLIENTS if client in finding.message]
    assert len(targets) == 1, finding
    assert len(clients) == 1, finding
    return finding.code, targets[0], clients[0]


# --- projects ------------------------------------------------------------------------------


def initialised() -> Env:
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    assert init_project(env.services(), InitOptions(assume_yes=True)).status == "applied"
    return env


def put(env: Env, path: str, content: bytes) -> None:
    env.project.write_atomic(CanonicalPath.parse(path), content)


def read(env: Env, path: str) -> bytes:
    return env.project.read_bytes(CanonicalPath.parse(path))


def install(env: Env, data: dict[str, Any]) -> None:
    put(env, POLICY_PATH, document(data))


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
    for finding in findings:
        for text in (finding.code, finding.message, finding.path or ""):
            assert MARKER not in text, finding
            for secret in secrets:
                assert secret not in text, finding


def body(size: int, unit: str = "aB3") -> str:
    return (unit * (size // len(unit) + 1))[:size]


# A key-shaped string is built at run time from parts (ORQLET-SEC-003); it is no real key.
KEY_SHAPED = "s" + "k-" + body(24)


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


def valid_doc() -> dict[str, Any]:
    return policy_doc(
        [entry("example-a", *routes_of("example-a"))],
        [assignment_doc("role", TESTER, model="example-a")],
    )


def arrange_directory(env: Env) -> None:
    env.project.delete(CanonicalPath.parse(POLICY_PATH))  # the seed that init wrote
    env.project.make_dir(CanonicalPath.parse(POLICY_PATH))


def arrange_contract_failure(env: Env) -> None:
    data = valid_doc()
    data["policy_version"] = 0
    data[f"{MARKER}-field"] = MARKER
    install(env, data)


def arrange_v1(env: Env) -> None:
    put(env, POLICY_PATH, document({"schema": "orqlet.model-policy/v1", MARKER: MARKER}))


def arrange_credential(env: Env) -> None:
    data = valid_doc()
    data["excluded"] = [
        exclusion("rule-x", id_patterns=[f"{MARKER}-*"], reason=f"{MARKER} {KEY_SHAPED}")
    ]
    install(env, data)


def arrange_deleted(env: Env) -> None:
    """The policy file is gone and the lock that init wrote still lists it as seeded."""
    env.project.delete(CanonicalPath.parse(POLICY_PATH))


def arrange_excluded_model(env: Env) -> None:
    excluded = entry(f"{MARKER}-excluded", route(CLAUDE, "claude-fable-9"))
    data = valid_doc()
    data["models"].append(excluded)
    data["excluded"] = [exclusion("rule-fable", id_patterns=["claude-fable-*"])]
    install(env, data)


def arrange_unknown_role(env: Env) -> None:
    data = valid_doc()
    data["assignments"].append(assignment_doc("role", f"{MARKER}-no-such-role", model="example-a"))
    install(env, data)


UNUSABLE: dict[str, tuple[Callable[[Env], None], str]] = {
    "the policy path is a directory": (arrange_directory, E540),
    "a contract failure": (arrange_contract_failure, E541),
    "a v1 file": (arrange_v1, E541),
    "a credential-shaped value": (arrange_credential, E542),
    "a deleted policy": (arrange_deleted, E547),
    "an excluded model": (arrange_excluded_model, E543),
    "a role that does not exist": (arrange_unknown_role, E545),
}


# =============================================================================================
# The rows of a selection
# =============================================================================================


def test_a_selection_entry_is_a_frozen_record_of_five_fields() -> None:
    """AC-7. expected_behavior_source: the interface item 4 (`SelectionEntry(kind, target, client,
    source, setting)` as a frozen dataclass) and item 2 (`ModelSelection` gains `entries:
    tuple[SelectionEntry, ...] = ()`).
    """
    setting = ModelSetting("example-a-claude-code", "id", "high")
    item = model_selection.SelectionEntry("role", TESTER, CLAUDE, "role-assignment", setting)

    assert (item.kind, item.target, item.client, item.source) == (
        "role",
        TESTER,
        CLAUDE,
        "role-assignment",
    )
    assert item.setting == setting
    assert model_selection.ModelSelection().entries == ()
    with pytest.raises(AttributeError):
        item.target = "other"  # type: ignore[misc]


def selected(
    policy: ModelPolicy, clients: Sequence[str] = CLIENTS
) -> model_selection.ModelSelection:
    return model_selection.select_models(policy, ROLE_NAMES, SKILL_NAMES, clients)


def test_each_role_and_skill_with_a_setting_or_a_finding_has_one_row_for_each_client() -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7 ("one entry for each role and skill that has a
    setting or a finding: the target, the client, the source, and the setting or null"); BC-43;
    ADR-001 decision 7; the interface item 4 (a pinned setting has the source of the assignment
    that gave it, `role-assignment` or `profile-assignment`, and the setting; a refusal of
    ORQ-W546 keeps the source as it was resolved and has no setting; a missing candidate has the
    source `automatic` and no setting; roles by name, then skills by name; clients in the enabled
    order). The fixture policy has one row of each kind, and a skill that gives neither a setting
    nor a finding has none.
    """
    selection = selected(ModelPolicy.model_validate(selection_doc()))

    assert [row_of(item) for item in selection.entries] == EXPECTED_ROWS


def test_the_clients_of_the_rows_follow_the_order_in_which_they_are_passed() -> None:
    """AC-7. expected_behavior_source: the interface item 4 ("clients in enabled-client order").
    The same policy with the clients passed as Cursor and then Claude Code: each target has its
    Cursor row first, and the Codex rows are not there.
    """
    selection = selected(ModelPolicy.model_validate(selection_doc()), (CURSOR, CLAUDE))

    keys = [(item.kind, item.target, item.client) for item in selection.entries]
    assert keys == [
        ("role", ARCH, CURSOR),
        ("role", ARCH, CLAUDE),
        ("role", INVENTORY, CURSOR),
        ("role", INVENTORY, CLAUDE),
        ("role", TESTER, CURSOR),
        ("role", TESTER, CLAUDE),
        ("role", TRACER, CURSOR),
        ("role", TRACER, CLAUDE),
        ("skill", REVIEW, CURSOR),
        ("skill", REVIEW, CLAUDE),
    ]


def test_a_profile_with_a_missing_candidate_gives_a_finding_and_no_row() -> None:
    """AC-7. expected_behavior_source: the interface item 4 ("A profile W540 gives a finding but no
    entry"): a row is for a role or a skill. A profile that no role uses has nothing eligible.
    """
    proposed = entry("example-proposed", *routes_of("example-proposed"), state="proposed")
    policy = make_policy(
        [proposed], [], profiles=[profile_doc("quality", candidates=["example-proposed"])]
    )

    outcome = model_selection.follow_policy(PolicyLoaded(policy), ROLE_NAMES, SKILL_NAMES, CLIENTS)

    assert outcome.selection is not None
    assert [f.code for f in outcome.findings] == [W540, W540, W540]
    assert outcome.selection.entries == ()


@pytest.mark.parametrize(
    "assignment",
    [
        pytest.param(
            assignment_doc("role", TESTER, model="example-a", task="example-task"), id="a-task"
        ),
        pytest.param(
            assignment_doc("role", TESTER, model="example-a", mode="automatic"), id="auto"
        ),
    ],
)
def test_an_assignment_that_is_not_rendered_gives_no_row(assignment: dict[str, Any]) -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7 (an entry for a role or skill "that has a
    setting or a finding"); ADR-001 decision 7 (a task-scoped assignment is never rendered); the
    interface item 4. A task-scoped assignment and one in the mode `automatic` give neither a
    setting nor a finding, so the target has no row.
    """
    policy = make_policy([entry("example-a", *routes_of("example-a"))], [assignment])

    assert selected(policy).entries == ()


def test_a_policy_with_no_assignment_gives_no_row() -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7; the interface item 4: nothing is assigned, so
    nothing is selected and nothing is said.
    """
    assert selected(make_policy([entry("example-a", *routes_of("example-a"))], [])).entries == ()


# =============================================================================================
# explain
# =============================================================================================


def test_explain_lists_the_rows_that_upgrade_writes_into_the_files() -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7 ("`explain` reports ... one entry for each
    role and skill that has a setting or a finding ... For a fixture policy the entries equal what
    `upgrade` writes into the files, compared by parsing the written files"); BC-43; ADR-001
    decision 7; the interface item 6 (`Explanation.model_selection`; "Entries equal what `upgrade`
    writes into the files (verified by parsing the written agent and skill files)"). `explain`
    runs first and writes nothing. Then `upgrade` runs, and for every role and skill and every
    client the model and effort in the written file are the entry's setting, or no pin when the
    entry has none or there is no entry.
    """
    env = initialised()
    install(env, selection_doc())
    before = (tree(env.project), tree(env.user_data))

    explanation = explain(env.services(), QUERY)

    assert (tree(env.project), tree(env.user_data)) == before
    entries: dict[tuple[str, str, str], model_selection.SelectionEntry] = {
        (e.kind, e.target, e.client): e for e in explanation.model_selection
    }
    assert [row_of(e) for e in explanation.model_selection] == EXPECTED_ROWS
    assert len(entries) == len(EXPECTED_ROWS)

    assert upgrade(env.services(), UpgradeOptions(assume_yes=True)).status == "applied"
    files = tree(env.project)
    checked = 0
    for client in CLIENTS:
        for kind, names in (("role", ROLE_NAMES), ("skill", SKILL_NAMES)):
            for name in names:
                found = entries.get((kind, name, client))
                setting = None if found is None or found.setting is None else found.setting
                expected = None if setting is None else (setting.name, setting.effort)
                assert written_pin(files, client, kind, name) == expected, (kind, name, client)
                checked += 1
    assert checked == len(CLIENTS) * (len(ROLE_NAMES) + len(SKILL_NAMES))


def test_explain_reports_the_findings_that_upgrade_would_print() -> None:
    """AC-3, AC-7. expected_behavior_source: plan P-6 AC-3 ("appear in the preview of `upgrade`
    and in `explain`") and AC-7; BC-43; the interface item 6 (`Explanation.model_findings` is the
    outcome's findings): the same findings, in the same order, as the preview of `upgrade --check`
    prints for the policy, W545 and W546 first and W540 last. No finding holds a model string.
    """
    env = initialised()
    install(env, selection_doc())

    explanation = explain(env.services(), QUERY)
    preview = upgrade(env.services(), UpgradeOptions(check=True))

    assert [described(f) for f in explanation.model_findings] == EXPECTED_FINDINGS
    assert all(f.severity is Severity.WARNING for f in explanation.model_findings)
    from_upgrade = [f for f in preview.findings if f.code in {W540, W545, W546}]
    assert list(explanation.model_findings) == from_upgrade
    no_leak(explanation.model_findings, "example-a", "example-alias", "example-proposed")


def test_explain_keeps_the_findings_of_the_policy_out_of_the_limits() -> None:
    """AC-3, AC-7. expected_behavior_source: the interface item 6 (the policy findings are
    `model_findings`; `limits` stay the client limits, the findings that start with `ORQ-L`) and
    item 10 (in the JSON, "next to the limits").
    """
    env = initialised()
    install(env, selection_doc())

    explanation = explain(env.services(), QUERY)

    assert explanation.limits
    assert all(f.code.startswith("ORQ-L") for f in explanation.limits)
    assert not {f.code for f in explanation.limits} & {W540, W545, W546}


def test_explain_with_no_policy_has_no_row_and_no_finding() -> None:
    """AC-7. expected_behavior_source: the interface item 6 ("No policy: both fields empty and
    every other field equal to before"). The project is the one of every other explain test.
    """
    explanation = explain(initialised().services(), QUERY)

    assert explanation.model_selection == ()
    assert explanation.model_findings == ()
    assert explanation.findings == ()
    assert explanation.limits


def test_explain_composes_with_the_policy_that_it_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-7. expected_behavior_source: the interface item 6 ("Loads the policy and calls
    `compose(policy=...)`") and item 1. A valid policy file is passed to `compose` as a loaded
    state. A project that `init` made holds the seed (P-13 AC-12), so the plain project loads the
    seed and the other one loads its own file.
    """
    calls: list[dict[str, Any]] = []

    def recording(*args: Any, **kwargs: Any) -> Composition:
        calls.append(dict(kwargs))
        return compose(*args, **kwargs)

    monkeypatch.setattr(explain_module, "compose", recording)
    plain = initialised()
    with_policy = initialised()
    install(with_policy, valid_doc())

    explain(plain.services(), QUERY)
    explain(with_policy.services(), QUERY)

    assert len(calls) == 2
    assert "policy" in calls[0]
    assert isinstance(calls[0]["policy"], PolicyLoaded)
    assert isinstance(calls[1]["policy"], PolicyLoaded)
    assert calls[0]["policy"].policy != calls[1]["policy"].policy


@pytest.mark.parametrize("case", list(UNUSABLE))
def test_explain_of_a_policy_that_cannot_be_used_prints_the_finding_and_lists_no_row(
    case: str,
) -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7 ("With an invalid, deleted or v1 policy
    `explain` prints the finding, lists no entry, writes nothing and does not fail"); BC-43; the
    interface item 6 ("Invalid/deleted/v1/problem policy: `model_findings` holds the refusal
    findings, `model_selection == ()`, nothing is written, nothing raises"); BC-32 (no value of
    the file).
    """
    arrange, code = UNUSABLE[case]
    env = initialised()
    arrange(env)
    before = (tree(env.project), tree(env.user_data))

    explanation = explain(env.services(), QUERY)

    assert explanation.model_selection == ()
    assert code in {f.code for f in explanation.model_findings}
    assert any(f.severity is Severity.ERROR for f in explanation.model_findings)
    assert (tree(env.project), tree(env.user_data)) == before
    no_leak(explanation.model_findings, KEY_SHAPED)


# =============================================================================================
# The command
# =============================================================================================


def serve(monkeypatch: pytest.MonkeyPatch, env: Env) -> None:
    """Make every command use the services of `env` instead of the real directory."""

    def services(root: object, packs_dir: object) -> InitServices:
        return env.services()

    monkeypatch.setattr(f"{LIFECYCLE}.build_init_services", services)


def explain_json(root: Path) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, ["explain", "--root", str(root), "--phase", "design", "--json"])
    return result.exit_code, json.loads(result.stdout)


def selection_rows(document_: dict[str, Any]) -> list[dict[str, Any]]:
    rows_ = document_["data"]["declared"]["model_selection"]
    assert isinstance(rows_, list)
    return rows_


def test_the_json_of_explain_has_one_object_for_each_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7 ("`explain` reports, in its `declared` data and
    its text, one entry for each role and skill ..."); the interface item 10 (JSON
    `data["declared"]["model_selection"]` is a list of `{"kind","target","client","source",
    "setting"}` with `setting` null or `{"name","kind","effort"}`).
    """
    env = initialised()
    install(env, selection_doc())
    serve(monkeypatch, env)

    code, parsed = explain_json(tmp_path)

    assert code == 0
    objects = selection_rows(parsed)
    assert all(set(o) == {"kind", "target", "client", "source", "setting"} for o in objects)
    assert all(
        o["setting"] is None or set(o["setting"]) == {"name", "kind", "effort"} for o in objects
    )
    assert [
        (
            o["kind"],
            o["target"],
            o["client"],
            o["source"],
            None
            if o["setting"] is None
            else (o["setting"]["name"], o["setting"]["kind"], o["setting"]["effort"]),
        )
        for o in objects
    ] == EXPECTED_ROWS


def test_the_json_of_explain_has_the_key_with_no_row_when_there_is_no_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-7. expected_behavior_source: the interface item 10 ("The key is present (empty) with no
    policy").
    """
    serve(monkeypatch, initialised())

    code, parsed = explain_json(tmp_path)

    assert code == 0
    assert selection_rows(parsed) == []
    assert parsed["data"]["declared"]["workflow_version"]


def test_the_json_findings_of_explain_hold_the_limits_and_the_policy_findings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-3, AC-7. expected_behavior_source: the interface item 10 ("Policy findings are in the JSON
    `findings` next to the limits; explain's exit code stays 0"); plan P-6 AC-3 (the findings
    appear in `explain`, "each prints only a fixed text and the target").
    """
    env = initialised()
    install(env, selection_doc())
    serve(monkeypatch, env)

    code, parsed = explain_json(tmp_path)

    assert code == 0
    found = parsed["findings"]
    assert any(f["code"].startswith("ORQ-L") for f in found)
    policy = [f for f in found if f["code"] in {W540, W545, W546}]
    assert [f["code"] for f in policy] == [code_ for code_, _, _ in EXPECTED_FINDINGS]
    assert all(f["severity"] == "warning" for f in policy)
    for finding, (_, target, client) in zip(policy, EXPECTED_FINDINGS, strict=True):
        assert target in finding["message"]
        assert client in finding["message"]
        assert MARKER not in finding["message"]


@pytest.mark.parametrize("case", list(UNUSABLE))
def test_explain_does_not_fail_for_a_policy_that_cannot_be_used(
    case: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7 ("`explain` prints the finding, lists no entry,
    writes nothing and does not fail"); the interface item 10 ("explain's exit code stays 0"). The
    command exits with 0, lists no row, prints the error as a finding, and the tree and the
    journal are as they were.
    """
    arrange, expected = UNUSABLE[case]
    env = initialised()
    arrange(env)
    before = (tree(env.project), tree(env.user_data))
    serve(monkeypatch, env)

    code, parsed = explain_json(tmp_path)

    assert code == 0
    assert selection_rows(parsed) == []
    refusals = [f for f in parsed["findings"] if f["code"] == expected]
    assert refusals
    assert all(f["severity"] == "error" for f in refusals)
    assert MARKER not in json.dumps(parsed["findings"])
    assert KEY_SHAPED not in json.dumps(parsed)
    assert (tree(env.project), tree(env.user_data)) == before


def model_section(text: str) -> list[str]:
    """The lines under `Model selection:` up to the next line that starts in the first column."""
    lines = text.splitlines()
    assert "Model selection:" in lines
    start = lines.index("Model selection:") + 1
    section: list[str] = []
    for line in lines[start:]:
        if line.strip() and not line[0].isspace():
            break
        section.append(line)
    return [line for line in section if line.strip()]


def test_the_text_of_explain_has_a_section_with_one_line_for_each_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7 ("... in its `declared` data and its text, one
    entry for each role and skill ..."); the interface item 10 ("The human text has a `Model
    selection:` section with one line per entry (target, client, source, setting name or `none`)
    plus the finding lines"). A line of an entry has no finding code; a line of a finding has one
    and holds the code and the message that the JSON shows for the finding.
    """
    env = initialised()
    install(env, selection_doc())
    serve(monkeypatch, env)

    result = RUNNER.invoke(app, ["explain", "--root", str(tmp_path), "--phase", "design"])
    _, parsed = explain_json(tmp_path)

    assert result.exit_code == 0
    section = model_section(result.stdout)
    entry_lines = [line for line in section if "ORQ-" not in line]
    finding_lines = [line for line in section if "ORQ-" in line]
    assert len(entry_lines) == len(EXPECTED_ROWS)
    for kind, target, client, source, setting in EXPECTED_ROWS:
        matching = [line for line in entry_lines if target in line and client in line]
        assert len(matching) == 1, (kind, target, client)
        assert source in matching[0]
        assert (setting[0] if setting is not None else "none") in matching[0]
    policy = [f for f in parsed["findings"] if f["code"] in {W540, W545, W546}]
    assert len(finding_lines) == len(policy)
    for finding in policy:
        assert any(finding["code"] in line and finding["message"] in line for line in finding_lines)


def test_the_text_of_explain_for_a_refused_policy_has_the_finding_and_no_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-7. expected_behavior_source: plan P-6 AC-7 ("With an invalid, deleted or v1 policy
    `explain` prints the finding, lists no entry"); the interface item 10 (the section has the
    finding lines). The policy is a v1 file: the section holds ORQ-E541 and no line names a role.
    """
    env = initialised()
    arrange_v1(env)
    serve(monkeypatch, env)

    result = RUNNER.invoke(app, ["explain", "--root", str(tmp_path), "--phase", "design"])

    assert result.exit_code == 0
    section = model_section(result.stdout)
    assert any(E541 in line for line in section)
    assert not any(name in line for line in section for name in (*ROLE_NAMES, *SKILL_NAMES))
    assert MARKER not in result.output


# --- upgrade, through the same app ------------------------------------------------------------


@pytest.mark.parametrize(
    "flags", [["--yes"], ["--dry-run"], ["--check"]], ids=["yes", "dry", "check"]
)
@pytest.mark.parametrize("case", ["a contract failure", "a deleted policy", "an excluded model"])
def test_the_command_upgrade_exits_with_3_and_writes_nothing_for_a_refused_policy(
    case: str, flags: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-1. expected_behavior_source: plan P-6 AC-1 ("`upgrade` returns `refused` with exit status
    3 and writes nothing, in a normal run and with `--dry-run` and `--check`"); BC-37; F-1; F-2;
    the interface item 5. The status is the one that the CLI already maps to 3; the policy is
    what makes the upgrade refuse. The error is printed as a finding and no value of the file is.
    """
    arrange, code = UNUSABLE[case]
    env = initialised()
    arrange(env)
    before = (tree(env.project), tree(env.user_data))
    serve(monkeypatch, env)

    result = RUNNER.invoke(app, ["upgrade", "--root", str(tmp_path), *flags, "--json"])

    assert result.exit_code == 3
    parsed = json.loads(result.stdout)
    assert parsed["data"]["status"] == "refused"
    assert code in {f["code"] for f in parsed["findings"]}
    assert MARKER not in json.dumps(parsed["findings"])
    assert (tree(env.project), tree(env.user_data)) == before
