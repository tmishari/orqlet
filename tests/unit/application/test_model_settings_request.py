"""Model selection for generated files and the request that carries it (phase P-5).

Every test cites its `expected_behavior_source`. AC-1 and AC-9 are acceptance criteria of phase P-5
in docs/design/dynamic-model-profiles/plan.yaml. This file also holds the application half of AC-3
to AC-8: what `select_models` returns for a policy. What the three client writers do with a
selection is in tests/unit/render/test_model_settings_render.py. BC-n are rows of
design/component.md, F-n its failure rows, C-11 its constraint, and ADR-n the decision records of
design/: ADR-001 decisions 2, 3 and 7 (default, modes, task scope), ADR-003 decisions 1 to 6 and 10
(the selection travels on the role and skill objects, a pin is the exact name, Cursor takes a plain
id, skills for Claude Code only, no settings file, the tests), and ADR-005 decision 2 (the
exclusion and the renderers).

"The interface decision" is the interface that the Coder of this phase implements and that the
brief of this phase's Tester states: `ModelSetting(name, kind, effort=None)` and the per-client
`model_settings` mapping of `ClientRole` and `ClientSkill` in the ports module;
`ModelSelection(roles, skills, findings, problems)` and `select_models(policy, role_names,
skill_names, clients)` in `orqlet.application.usecases.model_selection`; and the keyword
`selection` of `build_render_request` and of `compose`. A test that relies on one of the readings
that the person accepted on 2026-11-08 for the resolver says so in its docstring (a first
eligible candidate, a client-scoped assignment before an unscoped one, task-scoped assignments
dropped, a policy with a duplicate id or an unknown candidate refused by `policy_problems`).

These tests were written first, by the Tester of phase P-5 on 2026-11-08, before the
implementation existed. A policy is built in code as plain data and validated with
`ModelPolicy.model_validate`. Names and texts are placeholders (`example-*`); the only model
strings of a vendor kind are the three that AC-8 itself names (`fable`, `best` and
`claude-fable-*`).

Behaviour that neither the sources nor the brief settle is deliberately not pinned here:
- the wording of a finding. Pinned: its code, `Severity.WARNING`, that it names the target and the
  client id, that it holds no model or route string, that two policies that differ only in model
  names give the same text for the same target and client, and the order of the findings;
- whether the message also names the kind (`role` or `skill`) of the target;
- the type of the mappings inside a selection (compared as plain `dict`) and the order of the
  clients inside `roles[name]`;
- what `select_models` reports for a target whose manual assignment has no eligible candidate
  (the `missing-candidate` warning belongs to a later phase; here there is only no setting);
- the behaviour for a client id that is none of the three, for a name that `role_names` holds
  twice and for a name that the policy does not know (`policy_problems` refuses it first);
- whether a model that is written for Cursor plain with an effort of `None` and kind `alias`
  gives ORQ-W545 beyond what the brief says (a written alias does);
- the content of the three golden files of AC-3 (the render tests compare them).
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.instruction_adapter import (
    ClientRole,
    ClientSkill,
    InstructionAdapter,
    ModelSetting,
    RenderRequest,
)
from orqlet.application.usecases.model_selection import (
    ModelSelection,
    policy_problems,
    select_models,
)
from orqlet.application.usecases.render_all import compose
from orqlet.application.usecases.render_request import build_render_request
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.model_resolution import Effort, RouteKind
from tests.support.render import (
    EMPTY_RESOURCES,
    ROLE_NAMES,
    SAMPLE_RULES,
    SKILL_NAMES,
    packaged_request,
)

pytestmark = pytest.mark.unit

GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "golden"
BASE_FAMILY = "docs-2026-10"

CLAUDE = "claude-code"
CURSOR = "cursor"
CODEX = "codex"
CLIENTS = (CLAUDE, CURSOR, CODEX)
E543 = "ORQ-E543"
W545 = "ORQ-W545"
W546 = "ORQ-W546"
MARKER = "zq7leak"
INVENTORY = "orqlet-inventory"
TESTER = "orqlet-tester"
DESIGN = "orqlet-design"
REVIEW = "orqlet-review"
MODES = ("automatic", "manual", "automatic-with-fallbacks")

ADAPTERS: dict[str, InstructionAdapter] = {
    CLAUDE: ClaudeCodeAdapter(),
    CURSOR: CursorAdapter(),
    CODEX: CodexAdapter(),
}
ROLE_PATH = {
    CLAUDE: ".claude/agents/{}.md",
    CURSOR: ".cursor/agents/{}.md",
    CODEX: ".codex/agents/{}.toml",
}


# --- policies built in code ---------------------------------------------------------------


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
) -> dict[str, Any]:
    return {
        "id": profile_id,
        "capability": "Example capability.",
        "mode": "manual",
        "candidates": [{"client": client, "models": list(ids)} for client, ids in candidates],
        "fallbacks": [{"client": client, "models": list(ids)} for client, ids in fallbacks],
        "escalation": None,
    }


def everywhere(*model_ids: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """The same ordered ids for each of the three clients."""
    return tuple((client, model_ids) for client in CLIENTS)


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


def make_policy(
    models: Sequence[dict[str, Any]],
    assignments: Sequence[dict[str, Any]],
    *,
    profiles: Sequence[dict[str, Any]] = (),
    excluded: Sequence[dict[str, Any]] = (),
) -> ModelPolicy:
    return ModelPolicy.model_validate(
        {
            "schema": "orqlet.model-policy/v2",
            "policy_version": 1,
            "reviewed_for_release": "0.4.0",
            "models": list(models),
            "excluded": list(excluded),
            "profiles": list(profiles),
            "assignments": list(assignments),
        }
    )


def names_of(prefix: str) -> dict[str, str]:
    """The name that each client gives the model whose routes carry `prefix`."""
    return {CLAUDE: f"{prefix}-claude", CURSOR: f"{prefix}-cursor", CODEX: f"{prefix}-codex"}


def routes_of(prefix: str) -> list[dict[str, Any]]:
    return [route(client, name) for client, name in names_of(prefix).items()]


# Two approved models that have a differently named route for each of the three clients.
MODEL_A = entry("example-a", *routes_of("example-a"))
MODEL_B = entry("example-b", *routes_of("example-b"))
# An approved model whose route for each client is declared as an alias that resolves to an id.
MODEL_ALIAS = entry(
    "example-alias",
    *(
        route(client, name, kind="alias", resolves_to=f"{name}-1")
        for client, name in names_of("example-alias").items()
    ),
)


def settings_of(
    prefix: str,
    *,
    kind: RouteKind = "id",
    effort: Effort | None = None,
    clients: Sequence[str] = CLIENTS,
) -> dict[str, ModelSetting]:
    """The settings that a selection holds for the model of `prefix`, for these clients."""
    names = names_of(prefix)
    return {client: ModelSetting(names[client], kind, effort) for client in clients}


def select(policy_: ModelPolicy, clients: Sequence[str] = CLIENTS) -> ModelSelection:
    return select_models(policy_, ROLE_NAMES, SKILL_NAMES, clients)


def plain(table: Mapping[str, Mapping[str, ModelSetting]]) -> dict[str, dict[str, ModelSetting]]:
    """A selection's table as plain dicts, so that the type of the mapping is not compared."""
    return {name: dict(settings) for name, settings in table.items()}


def assert_findings(findings: Sequence[Finding], expected: Sequence[tuple[str, str, str]]) -> None:
    """One warning for each `(code, target name, client id)`, in this order, each its own text."""
    assert len(findings) == len(expected), [finding.message for finding in findings]
    assert len({finding.message for finding in findings}) == len(findings)
    for finding, (code, target, client) in zip(findings, expected, strict=True):
        assert finding.code == code, finding.message
        assert finding.severity is Severity.WARNING
        assert target in finding.message, finding.message
        assert client in finding.message, finding.message


# --- the request builder -------------------------------------------------------------------


def build_request(selection: ModelSelection | None = None) -> RenderRequest:
    """The request of an installation with no registered link and no answered convention."""
    return build_render_request(
        PackagedWorkflow(),
        StrictYamlLoader(),
        SAMPLE_RULES,
        EMPTY_RESOURCES,
        None,
        selection=selection,
    )


def files_of(request: RenderRequest, client: str) -> dict[str, bytes]:
    return {str(file.path): file.content for file in ADAPTERS[client].render(request).files}


def stripped(request: RenderRequest) -> RenderRequest:
    """The request with the model settings of every role and skill taken away."""
    return dataclasses.replace(
        request,
        roles=tuple(dataclasses.replace(role, model_settings={}) for role in request.roles),
        skills=tuple(dataclasses.replace(skill, model_settings={}) for skill in request.skills),
    )


# --- AC-9: where the types live, and what does not change ----------------------------------


def test_a_model_setting_is_a_frozen_slotted_triple_with_no_effort_by_default() -> None:
    """expected_behavior_source: the interface decision 1 (`ModelSetting(name, kind, effort=None)`,
    a frozen and slotted dataclass); plan P-5 AC-9; ADR-003 decision 1; C-11.
    """
    setting = ModelSetting("example-name", "id")

    assert [field.name for field in dataclasses.fields(ModelSetting)] == ["name", "kind", "effort"]
    assert (setting.name, setting.kind, setting.effort) == ("example-name", "id", None)
    assert setting == ModelSetting(name="example-name", kind="id", effort=None)
    assert setting != ModelSetting("example-name", "id", "high")
    assert "__slots__" in vars(ModelSetting)
    field = "name"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(setting, field, "example-other")


def test_the_model_setting_and_the_mapping_live_in_the_ports_module_of_the_roles() -> None:
    """expected_behavior_source: plan P-5 AC-9 (`ModelSetting` and the `model_settings` mapping
    live in `application/ports/instruction_adapter.py`); ADR-003 decision 1; C-11 ("the selection
    type lives in the ports module that holds `ClientRole`, so adapters can import it").
    """
    module = "orqlet.application.ports.instruction_adapter"

    assert ModelSetting.__module__ == module
    assert ClientRole.__module__ == module
    assert ClientSkill.__module__ == module
    for carrier in (ClientRole, ClientSkill):
        assert "model_settings" in {field.name for field in dataclasses.fields(carrier)}


def test_a_role_and_a_skill_carry_no_model_settings_by_default() -> None:
    """expected_behavior_source: the interface decision 1 (`ClientRole.model_settings` and
    `ClientSkill.model_settings`: a mapping from client id to setting, default empty); ADR-003
    decision 1 ("with no entry, a role file is written as today").
    """
    role = ClientRole(name="orqlet-sample", description="d", body="b\n")
    skill = ClientSkill(name="orqlet-sample", description="d", body="b\n")

    assert dict(role.model_settings) == {}
    assert dict(skill.model_settings) == {}


def test_the_render_request_has_the_fields_that_it_had_before() -> None:
    """expected_behavior_source: plan P-5 AC-9 (`RenderRequest` unchanged); the interface decision
    1 (its dataclass field names are exactly the nine below); ADR-003 decision 1; C-11.
    """
    assert [field.name for field in dataclasses.fields(RenderRequest)] == [
        "workflow_version",
        "baseline_body",
        "scoped_rules",
        "commands",
        "skills",
        "roles",
        "client_version",
        "conventions",
        "integrations",
    ]


@pytest.mark.parametrize(
    "module_name",
    [
        "orqlet.adapters.clients.claude_code",
        "orqlet.adapters.clients.codex",
        "orqlet.adapters.clients.cursor",
    ],
)
def test_a_client_adapter_module_never_mentions_the_model_settings(module_name: str) -> None:
    """expected_behavior_source: plan P-5 AC-9 (the three client adapter modules are unchanged);
    the interface decision 1 (the adapters do not mention `model_settings` or `ModelSetting`);
    ADR-003 decision 1; ORQLET-ARCH-003 (the adapters stay independent).
    """
    source = inspect.getsource(importlib.import_module(module_name))

    assert "model_settings" not in source
    assert "ModelSetting" not in source


def test_the_selection_functions_take_the_arguments_of_the_interface_decision() -> None:
    """expected_behavior_source: the interface decision 3 (`select_models(policy, role_names,
    skill_names, clients)`) and 4 (`build_render_request(..., *, selection=None)` and `compose`
    with `selection: ModelSelection | None = None`).
    """
    assert list(inspect.signature(select_models).parameters) == [
        "policy",
        "role_names",
        "skill_names",
        "clients",
    ]
    selection = inspect.signature(build_render_request).parameters["selection"]
    assert selection.default is None
    assert selection.kind is inspect.Parameter.KEYWORD_ONLY
    assert inspect.signature(compose).parameters["selection"].default is None


def test_a_selection_is_a_frozen_slotted_record_of_four_parts_and_empty_by_default() -> None:
    """expected_behavior_source: the interface decision 3 (`ModelSelection(roles, skills,
    findings, problems)`, frozen and slotted; `ModelSelection()` is an empty selection).
    """
    selection = ModelSelection()

    assert [field.name for field in dataclasses.fields(ModelSelection)] == [
        "roles",
        "skills",
        "findings",
        "problems",
    ]
    assert plain(selection.roles) == {}
    assert plain(selection.skills) == {}
    assert selection.findings == ()
    assert selection.problems == ()
    assert "__slots__" in vars(ModelSelection)
    field = "findings"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(selection, field, ())


# --- AC-1: with no selection the request and the role files are those of today -------------


@pytest.mark.parametrize("role", ROLE_NAMES)
@pytest.mark.parametrize("client", CLIENTS)
def test_without_a_selection_each_role_file_is_byte_identical_to_its_base_golden(
    client: str, role: str
) -> None:
    """expected_behavior_source: plan P-5 AC-1 (with no policy given to the request builder, the
    five existing role files of each client are byte-identical to the files that the base
    revision renders); BC-1; C-3; A-28. The base files are the committed goldens of the family
    `docs-2026-10`, read from disk and not through the `golden` fixture.
    """
    path = ROLE_PATH[client].format(role)
    expected = (GOLDEN_ROOT / client / BASE_FAMILY / path).read_bytes()

    assert files_of(build_request(), client)[path] == expected


def test_a_request_built_with_no_selection_is_the_request_of_today() -> None:
    """expected_behavior_source: plan P-5 AC-1; the interface decision 4 (`selection=None` is
    exactly today's request); BC-1.
    """
    assert build_request() == packaged_request()
    assert build_request(None) == packaged_request()


def test_an_empty_selection_gives_the_request_of_today() -> None:
    """expected_behavior_source: plan P-5 AC-1; the interface decision 3 (`ModelSelection()` is an
    empty selection) and 4 (a selection pins only the names it holds); BC-1.
    """
    assert build_request(ModelSelection()) == packaged_request()


def test_a_policy_with_no_assignment_gives_the_request_of_today() -> None:
    """expected_behavior_source: plan P-5 AC-1; the interface decision 3 (`select_models` gives
    nothing for a target that no assignment names); BC-1.
    """
    selection = select(make_policy([MODEL_A], []))

    assert selection == ModelSelection()
    assert build_request(selection) == packaged_request()


@pytest.mark.parametrize("mode", ["automatic", "automatic-with-fallbacks"])
def test_a_policy_of_modes_that_do_not_pin_gives_the_request_of_today(mode: str) -> None:
    """expected_behavior_source: plan P-5 AC-2 (in mode `automatic` and `automatic-with-fallbacks`,
    with or without a policy, a role keeps its automatic setting); BC-2; BC-27; ADR-001 decision 3.
    The assignments really name roles, skills and profiles that have routes for all clients.
    """
    selection = select(mode_policy(mode))

    assert build_request(selection) == packaged_request()


# --- the request builder with a selection --------------------------------------------------


def test_a_selection_fills_the_model_settings_of_the_roles_and_skills_it_names() -> None:
    """expected_behavior_source: the interface decision 4 (with a selection, every role whose name
    is a key of `selection.roles` gets `model_settings=selection.roles[name]`, every skill
    likewise from `selection.skills`; everything else in the request is unchanged); ADR-003
    decision 1 ("set by `build_render_request`").
    """
    selection = ModelSelection(
        roles={TESTER: {CLAUDE: ModelSetting("example-claude", "id", "high")}},
        skills={REVIEW: {CODEX: ModelSetting("example-codex", "alias")}},
    )

    request = build_request(selection)

    roles = {role.name: role for role in request.roles}
    skills = {skill.name: skill for skill in request.skills}
    assert dict(roles[TESTER].model_settings) == dict(selection.roles[TESTER])
    assert dict(skills[REVIEW].model_settings) == dict(selection.skills[REVIEW])
    assert [name for name, role in roles.items() if role.model_settings] == [TESTER]
    assert [name for name, skill in skills.items() if skill.model_settings] == [REVIEW]
    assert stripped(request) == packaged_request()


def test_a_name_that_no_packaged_role_or_skill_has_is_ignored() -> None:
    """expected_behavior_source: the interface decision 4 ("a name that no packaged role or skill
    has is ignored").
    """
    setting = ModelSetting("example-claude", "id")
    selection = ModelSelection(
        roles={"example-no-such-role": {CLAUDE: setting}},
        skills={"example-no-such-skill": {CLAUDE: setting}},
    )

    assert build_request(selection) == packaged_request()


def test_a_role_name_in_the_skills_of_a_selection_is_not_a_skill() -> None:
    """expected_behavior_source: the interface decision 4 (every skill gets its settings "from
    `selection.skills`" and every role from `selection.roles`: the two tables are separate).
    """
    setting = ModelSetting("example-claude", "id")
    selection = ModelSelection(
        skills={TESTER: {CLAUDE: setting}}, roles={REVIEW: {CLAUDE: setting}}
    )

    assert build_request(selection) == packaged_request()


# --- select_models: one model, a profile, the scope of an assignment ----------------------


def test_a_policy_with_no_assignment_selects_nothing() -> None:
    """expected_behavior_source: the interface decision 3 (a target with no setting for any client
    has no key; the selection of a policy with no problem has no problem).
    """
    selection = select(make_policy([MODEL_A, MODEL_B], []))

    assert plain(selection.roles) == {}
    assert plain(selection.skills) == {}
    assert selection.findings == ()
    assert selection.problems == ()


def test_a_manual_assignment_of_one_model_gives_each_client_its_own_name() -> None:
    """expected_behavior_source: plan P-5 AC-3 (in mode `manual`, with an approved candidate whose
    route has a name for the client, that client gets that client's name; with two or three
    clients each gets its own); BC-3; the interface decision 3 (`ModelSetting(choice.name,
    choice.kind, choice.effort)` for each client).
    """
    selection = select(make_policy([MODEL_A], [assignment_doc("role", TESTER, model="example-a")]))

    assert plain(selection.roles) == {TESTER: settings_of("example-a")}
    assert plain(selection.skills) == {}
    assert selection.findings == ()
    assert selection.problems == ()


def test_only_the_enabled_clients_get_a_setting() -> None:
    """expected_behavior_source: plan P-5 AC-3 ("with two or three clients enabled each file
    carries its own client's name"); the interface decision 3 (a setting for each client of
    `clients`, in the given order).
    """
    policy_ = make_policy([MODEL_A], [assignment_doc("role", TESTER, model="example-a")])

    assert plain(select(policy_, (CODEX,)).roles) == {
        TESTER: settings_of("example-a", clients=(CODEX,))
    }
    assert plain(select(policy_, (CODEX, CLAUDE)).roles) == {
        TESTER: settings_of("example-a", clients=(CLAUDE, CODEX))
    }
    assert plain(select(policy_, ()).roles) == {}


def test_an_effort_reaches_claude_code_and_codex_and_cursor_gets_a_finding_instead() -> None:
    """expected_behavior_source: plan P-5 AC-3 (`effort` where the assignment sets one: Claude Code
    and Codex) and AC-4 (an effort assignment for Cursor gives ORQ-W546 and no setting); BC-34; the
    interface decision 3 (Cursor: when the selected choice has an effort there is no setting for
    that role and the finding ORQ-W546). The other two clients keep their settings.
    """
    selection = select(
        make_policy([MODEL_A], [assignment_doc("role", TESTER, model="example-a", effort="high")])
    )

    assert plain(selection.roles) == {
        TESTER: settings_of("example-a", effort="high", clients=(CLAUDE, CODEX))
    }
    assert_findings(selection.findings, [(W546, TESTER, CURSOR)])


@pytest.mark.parametrize("cursor_name", ["1-example-cursor", "true", "Yes", "n", "example:cursor"])
def test_a_name_that_cursor_cannot_take_unquoted_is_refused_with_a_finding(
    cursor_name: str,
) -> None:
    """expected_behavior_source: plan P-5 AC-4 (a name that is not plain-safe gives ORQ-W546, no
    setting for that role); BC-34; ADR-003 decision 3; the interface decision 3 (Cursor: when
    `cursor_plain_id(name)` is false). Each name is one that the contract accepts (`ModelRef`) and
    that `cursor_plain_id` refuses: it starts with a digit, is a YAML word, or holds a colon.
    """
    model = entry(
        "example-a",
        route(CLAUDE, "example-a-claude"),
        route(CURSOR, cursor_name),
        route(CODEX, "example-a-codex"),
    )

    selection = select(make_policy([model], [assignment_doc("role", TESTER, model="example-a")]))

    assert plain(selection.roles) == {TESTER: settings_of("example-a", clients=(CLAUDE, CODEX))}
    assert_findings(selection.findings, [(W546, TESTER, CURSOR)])


def test_a_plain_cursor_name_without_an_effort_is_selected() -> None:
    """expected_behavior_source: plan P-5 AC-3 (Cursor `model:` only) and AC-4 (a Cursor value is
    written when `cursor_plain_id` is true); the interface decision 3 (Cursor gets a setting
    unless the choice has an effort or a name that is not plain).
    """
    model = entry("example-a", route(CURSOR, "Example.Cursor_2/x+y"))

    selection = select(make_policy([model], [assignment_doc("role", TESTER, model="example-a")]))

    assert plain(selection.roles) == {TESTER: {CURSOR: ModelSetting("Example.Cursor_2/x+y", "id")}}
    assert selection.findings == ()


def test_a_profile_gives_each_client_the_first_approved_candidate_of_its_own_list() -> None:
    """expected_behavior_source: plan P-5 AC-3 ("an assignment that names a profile whose
    candidates are listed per client"); BC-3; ADR-001 decision 3 (manual: "the first eligible
    candidate in the approved order is pinned"); the interface decision 3. The first candidate of
    the Codex list is only proposed, so it is skipped.
    """
    proposed = entry("example-p", *routes_of("example-p"), state="proposed")
    engineering = profile_doc(
        "engineering",
        candidates=(
            (CLAUDE, ("example-a",)),
            (CURSOR, ("example-b",)),
            (CODEX, ("example-p", "example-b", "example-a")),
        ),
    )

    selection = select(
        make_policy(
            [MODEL_A, MODEL_B, proposed],
            [assignment_doc("role", INVENTORY, profile="engineering")],
            profiles=[engineering],
        )
    )

    assert plain(selection.roles) == {
        INVENTORY: {
            CLAUDE: ModelSetting("example-a-claude", "id"),
            CURSOR: ModelSetting("example-b-cursor", "id"),
            CODEX: ModelSetting("example-b-codex", "id"),
        }
    }
    assert selection.findings == ()
    assert selection.problems == ()


def test_a_client_without_a_candidate_gets_no_setting_and_a_target_with_none_gets_no_key() -> None:
    """expected_behavior_source: the interface decision 3 (only a `selected` outcome gives a
    setting; a target with no setting for any client has no key). No finding is pinned for the
    client that has no candidate (see the module docstring).
    """
    some = profile_doc("quality", candidates=((CLAUDE, ("example-a",)),))
    none = profile_doc("economy", candidates=())
    assignments = [
        assignment_doc("role", TESTER, profile="quality"),
        assignment_doc("role", INVENTORY, profile="economy"),
    ]

    selection = select(make_policy([MODEL_A], assignments, profiles=[some, none]))

    assert plain(selection.roles) == {TESTER: settings_of("example-a", clients=(CLAUDE,))}


def test_a_client_scoped_assignment_beats_an_unscoped_one_for_that_client() -> None:
    """expected_behavior_source: plan P-5 AC-3 ("client-scoped assignments (client set) beating
    unscoped ones for that client"); reading 8 accepted on 2026-11-08 (assignments are ordered by
    task, then client), so the order in the file does not matter; the interface decision 3.
    """
    unscoped = assignment_doc("role", TESTER, model="example-a")
    scoped = assignment_doc("role", TESTER, model="example-b", client=CLAUDE)
    expected = {
        TESTER: {
            CLAUDE: ModelSetting("example-b-claude", "id"),
            CURSOR: ModelSetting("example-a-cursor", "id"),
            CODEX: ModelSetting("example-a-codex", "id"),
        }
    }

    for assignments in ([unscoped, scoped], [scoped, unscoped]):
        selection = select(make_policy([MODEL_A, MODEL_B], assignments))
        assert plain(selection.roles) == expected


def test_a_client_scoped_profile_assignment_beats_an_unscoped_one_for_that_client() -> None:
    """expected_behavior_source: plan P-5 AC-3 (client-scoped assignments beat unscoped ones); the
    shape that names a profile; reading 8 accepted on 2026-11-08.
    """
    quality = profile_doc("quality", candidates=everywhere("example-a"))
    engineering = profile_doc("engineering", candidates=everywhere("example-b"))
    assignments = [
        assignment_doc("role", TESTER, profile="quality"),
        assignment_doc("role", TESTER, profile="engineering", client=CODEX),
    ]

    selection = select(
        make_policy([MODEL_A, MODEL_B], assignments, profiles=[quality, engineering])
    )

    assert plain(selection.roles) == {
        TESTER: {
            CLAUDE: ModelSetting("example-a-claude", "id"),
            CURSOR: ModelSetting("example-a-cursor", "id"),
            CODEX: ModelSetting("example-b-codex", "id"),
        }
    }


def test_a_task_scoped_assignment_is_never_selected() -> None:
    """expected_behavior_source: plan P-5 AC-7 (a task-scoped assignment is never rendered into a
    file); BC-43; ADR-001 decision 7 (task scope is a resolve-time selector only); the interface
    decision 3 (the render policy, which drops every task-scoped assignment).
    """
    task_only = make_policy(
        [MODEL_A], [assignment_doc("role", TESTER, model="example-a", task="example-task")]
    )
    both = make_policy(
        [MODEL_A, MODEL_B],
        [
            assignment_doc("role", TESTER, model="example-b", task="example-task"),
            assignment_doc("role", TESTER, model="example-a"),
        ],
    )

    assert plain(select(task_only).roles) == {}
    assert select(task_only).findings == ()
    assert plain(select(both).roles) == {TESTER: settings_of("example-a")}


def test_the_first_named_route_that_is_not_blocked_is_the_one_selected() -> None:
    """expected_behavior_source: plan P-5 AC-7 ("the first non-blocked named route is the one
    written; a blocked route is skipped", the behaviour of phase P-4); BC-28; the interface
    decision 3. The route without a name and the blocked route come first.
    """
    model = entry(
        "example-a",
        route(CLAUDE, None),
        route(CLAUDE, "example-a-blocked", access="blocked"),
        route(CLAUDE, "example-a-claude", access="confirmed"),
        route(CLAUDE, "example-a-later"),
    )

    selection = select(make_policy([model], [assignment_doc("role", TESTER, model="example-a")]))

    assert plain(selection.roles) == {TESTER: {CLAUDE: ModelSetting("example-a-claude", "id")}}


def test_a_model_whose_only_route_is_blocked_is_not_selected() -> None:
    """expected_behavior_source: ADR-003 decision 6 (in `manual` mode a blocked access gives no
    pin); the interface decision 3 (only a `selected` outcome gives a setting).
    """
    model = entry("example-a", route(CLAUDE, "example-a-blocked", access="blocked"))

    selection = select(make_policy([model], [assignment_doc("role", TESTER, model="example-a")]))

    assert plain(selection.roles) == {}


def test_the_name_of_the_route_is_pinned_and_none_of_its_other_strings() -> None:
    """expected_behavior_source: plan P-5 AC-7 ("a pin uses the route's exact `name`"); BC-28;
    ADR-003 decision 2 ("a pin uses the exact ID"); the interface decision 3.
    """
    model = entry(
        "example-a",
        route(CLAUDE, "example-a-claude", also_known_as=("example-a-claude-high", "example-a-aka")),
    )

    selection = select(make_policy([model], [assignment_doc("role", TESTER, model="example-a")]))

    assert plain(selection.roles) == {TESTER: {CLAUDE: ModelSetting("example-a-claude", "id")}}


def test_a_manual_assignment_that_names_an_ineligible_model_falls_through_to_a_profile() -> None:
    """expected_behavior_source: reading 3 accepted on 2026-11-08 for the resolver (an invalid
    level passes to the next): the pinned model is only proposed, so the manual profile assignment
    of the same role gives the name; ADR-001 decision 4 (precedence); the interface decision 3.
    """
    proposed = entry("example-p", *routes_of("example-p"), state="proposed")
    quality = profile_doc("quality", candidates=everywhere("example-b"))
    assignments = [
        assignment_doc("role", TESTER, model="example-p"),
        assignment_doc("role", TESTER, profile="quality"),
    ]

    selection = select(make_policy([MODEL_B, proposed], assignments, profiles=[quality]))

    assert plain(selection.roles) == {TESTER: settings_of("example-b")}


# --- AC-2: only the mode `manual` selects --------------------------------------------------


def mode_policy(mode: str) -> ModelPolicy:
    """Roles and skills assigned by one model and by a profile in `mode`, with an effort set on
    some. Every model has a route for all three clients, so that a mode that pinned anyway would
    show.
    """
    quality = profile_doc(
        "quality",
        candidates=everywhere("example-a", "example-b"),
        fallbacks=everywhere("example-b"),
    )
    assignments = [
        assignment_doc("role", TESTER, model="example-a", mode=mode, effort="high"),
        assignment_doc("role", INVENTORY, profile="quality", mode=mode),
        assignment_doc("skill", REVIEW, model="example-b", mode=mode),
        assignment_doc("skill", DESIGN, profile="quality", mode=mode, effort="low"),
    ]
    return make_policy([MODEL_A, MODEL_B], assignments, profiles=[quality])


@pytest.mark.parametrize("mode", ["automatic", "automatic-with-fallbacks"])
def test_the_modes_that_do_not_pin_select_nothing_and_say_nothing(mode: str) -> None:
    """expected_behavior_source: plan P-5 AC-2 (in mode `automatic` and `automatic-with-fallbacks`,
    with or without a policy, nothing is pinned); BC-2; BC-27; ADR-001 decision 3 (`manual` is the
    only mode that renders a pin); the interface decision 3 (`automatic` and
    `automatic-with-fallbacks` give nothing, even with a profile and candidates). The reading that
    such a policy gives no finding either follows from the brief: a finding is about a setting
    that was chosen (ORQ-W545 for a written alias, ORQ-W546 for a selected choice that is not
    written).
    """
    selection = select(mode_policy(mode))

    assert plain(selection.roles) == {}
    assert plain(selection.skills) == {}
    assert selection.findings == ()
    assert selection.problems == ()


def test_the_policy_of_the_mode_tests_selects_in_mode_manual() -> None:
    """expected_behavior_source: ADR-001 decision 3 (`manual` is the only mode that renders a
    pin). A control: it shows that the policy of the two tests above would pin if the mode let it.
    """
    selection = select(mode_policy("manual"))

    assert plain(selection.roles) == {
        TESTER: settings_of("example-a", effort="high", clients=(CLAUDE, CODEX)),
        INVENTORY: settings_of("example-a"),
    }
    assert set(plain(selection.skills)) == {REVIEW, DESIGN}


# --- AC-5: skills are pinned for Claude Code only ------------------------------------------


def test_a_manual_skill_assignment_pins_claude_code_and_warns_for_the_other_clients() -> None:
    """expected_behavior_source: plan P-5 AC-5 (an assignment of a skill for Codex or Cursor gives
    ORQ-W546 and no change; a skill assignment with no `client` pins Claude Code and gives
    ORQ-W546 for each of the other two enabled clients); BC-7; ADR-003 decision 4; F-4; the
    interface decision 3 (a skill: only `claude-code` gets a setting).
    """
    policy_ = make_policy(
        [MODEL_A], [assignment_doc("skill", REVIEW, model="example-a", effort="high")]
    )

    selection = select(policy_)

    assert plain(selection.roles) == {}
    assert plain(selection.skills) == {
        REVIEW: {CLAUDE: ModelSetting("example-a-claude", "id", "high")}
    }
    assert_findings(selection.findings, [(W546, REVIEW, CURSOR), (W546, REVIEW, CODEX)])
    only_codex = select(policy_, (CLAUDE, CODEX))
    assert_findings(only_codex.findings, [(W546, REVIEW, CODEX)])
    assert plain(only_codex.skills) == plain(selection.skills)
    assert select(policy_, (CLAUDE,)).findings == ()


@pytest.mark.parametrize("client", [CODEX, CURSOR])
def test_a_skill_assignment_scoped_to_codex_or_cursor_gives_a_finding_and_no_setting(
    client: str,
) -> None:
    """expected_behavior_source: plan P-5 AC-5 ("an assignment of a skill for Codex or Cursor
    gives ORQ-W546 and no change"); BC-7; F-4 ("a skill is assigned a model for Codex or Cursor:
    warning that the client documents no skill-level model; nothing rendered"); ADR-003 decision 4.
    """
    selection = select(
        make_policy([MODEL_A], [assignment_doc("skill", REVIEW, model="example-a", client=client)])
    )

    assert plain(selection.skills) == {}
    assert plain(selection.roles) == {}
    assert_findings(selection.findings, [(W546, REVIEW, client)])


def test_a_skill_assignment_by_a_profile_pins_claude_code_with_the_first_candidate() -> None:
    """expected_behavior_source: plan P-5 AC-5 (a skill assignment in mode `manual` writes the
    Claude Code setting); BC-7; the interface decision 3. The assignment names a profile.
    """
    quality = profile_doc("quality", candidates=((CLAUDE, ("example-b", "example-a")),))

    selection = select(
        make_policy(
            [MODEL_A, MODEL_B],
            [assignment_doc("skill", DESIGN, profile="quality")],
            profiles=[quality],
        ),
        (CLAUDE,),
    )

    assert plain(selection.skills) == {DESIGN: settings_of("example-b", clients=(CLAUDE,))}
    assert selection.findings == ()


# --- AC-7: aliases and the finding ORQ-W545 -----------------------------------------------


def test_a_pinned_alias_route_gives_w545_for_each_client_that_writes_it() -> None:
    """expected_behavior_source: plan P-5 AC-7 (an alias name is written only when the route is
    `kind: alias` with `resolves_to`, and the selection then returns ORQ-W545); BC-28; BC-43;
    ADR-003 decision 2 (`alias-route-rendered`); F-17; the interface decision 3 (a written setting
    whose kind is alias adds ORQ-W545). One finding for each target and client.
    """
    selection = select(
        make_policy([MODEL_ALIAS], [assignment_doc("role", TESTER, model="example-alias")])
    )

    assert plain(selection.roles) == {TESTER: settings_of("example-alias", kind="alias")}
    assert_findings(
        selection.findings, [(W545, TESTER, CLAUDE), (W545, TESTER, CURSOR), (W545, TESTER, CODEX)]
    )


def test_a_route_of_kind_id_never_gives_w545() -> None:
    """expected_behavior_source: plan P-5 AC-7 ("a route of kind `id` never produces ORQ-W545");
    BC-28; the interface decision 3.
    """
    selection = select(
        make_policy(
            [MODEL_A],
            [
                assignment_doc("role", TESTER, model="example-a", effort="high"),
                assignment_doc("skill", REVIEW, model="example-a"),
            ],
        )
    )

    assert W545 not in {finding.code for finding in selection.findings}
    assert {finding.code for finding in selection.findings} == {W546}


def test_a_setting_that_is_not_written_gives_no_w545() -> None:
    """expected_behavior_source: the interface decision 3 (ORQ-W545 is for a *written* setting
    whose kind is alias; a Cursor effort and a skill for Codex are not written and give ORQ-W546
    only); plan P-5 AC-4 and AC-5.
    """
    selection = select(
        make_policy(
            [MODEL_ALIAS],
            [
                assignment_doc("role", TESTER, model="example-alias", effort="high", client=CURSOR),
                assignment_doc("skill", REVIEW, model="example-alias", client=CODEX),
            ],
        )
    )

    assert plain(selection.roles) == {}
    assert plain(selection.skills) == {}
    assert_findings(selection.findings, [(W546, TESTER, CURSOR), (W546, REVIEW, CODEX)])


def test_the_findings_come_in_the_order_roles_then_skills_names_sorted_clients_as_given() -> None:
    """expected_behavior_source: the interface decision 3 (one finding for each code, target and
    client; the order is deterministic: roles then skills, names sorted, clients in the given
    order). The assignments are listed in the reverse of that order, and the clients are given
    in the order Codex, Claude Code.
    """
    assignments = [
        assignment_doc("skill", REVIEW, model="example-alias"),
        assignment_doc("skill", DESIGN, model="example-alias"),
        assignment_doc("role", TESTER, model="example-alias"),
        assignment_doc("role", INVENTORY, model="example-alias"),
    ]
    policy_ = make_policy([MODEL_ALIAS], assignments)

    selection = select(policy_, (CODEX, CLAUDE))

    assert_findings(
        selection.findings,
        [
            (W545, INVENTORY, CODEX),
            (W545, INVENTORY, CLAUDE),
            (W545, TESTER, CODEX),
            (W545, TESTER, CLAUDE),
            (W546, DESIGN, CODEX),
            (W545, DESIGN, CLAUDE),
            (W546, REVIEW, CODEX),
            (W545, REVIEW, CLAUDE),
        ],
    )
    assert select(policy_, (CODEX, CLAUDE)) == selection
    reversed_names = select_models(policy_, ROLE_NAMES[::-1], SKILL_NAMES[::-1], (CODEX, CLAUDE))
    assert reversed_names == selection


# --- AC-4: a finding holds no model string -------------------------------------------------


def leaky_policy(tag: str) -> ModelPolicy:
    """Every string of the model holds `tag`; the role and the skill are both pinned.

    For Claude Code and Codex the route is an alias (written, so ORQ-W545); the Cursor name starts
    with a digit (refused, so ORQ-W546); a skill is refused for Codex and Cursor (ORQ-W546).
    """
    model = entry(
        f"example-{tag}-id",
        route(
            CLAUDE,
            f"example-{tag}-claude",
            kind="alias",
            resolves_to=f"example-{tag}-claude-1",
            also_known_as=(f"example-{tag}-aka",),
        ),
        route(CURSOR, f"1-{tag}-cursor"),
        route(CODEX, f"example-{tag}-codex", kind="alias", resolves_to=f"example-{tag}-codex-1"),
        family=f"example-{tag}-family",
    )
    assignments = [
        assignment_doc("role", TESTER, model=f"example-{tag}-id"),
        assignment_doc("skill", REVIEW, model=f"example-{tag}-id"),
    ]
    return make_policy([model], assignments)


def test_a_finding_names_the_target_and_the_client_and_holds_no_model_string() -> None:
    """expected_behavior_source: plan P-5 AC-4 (ORQ-W546 "with a fixed text and no model string");
    the interface decision 3 (the message is a fixed text plus the target and the client id; it
    never holds a model name, a route name or any string of the policy other than the target name
    and the client id; a warning). Every model string of the policy holds a marker.
    """
    selection = select(leaky_policy(MARKER))

    assert_findings(
        selection.findings,
        [
            (W545, TESTER, CLAUDE),
            (W546, TESTER, CURSOR),
            (W545, TESTER, CODEX),
            (W545, REVIEW, CLAUDE),
            (W546, REVIEW, CURSOR),
            (W546, REVIEW, CODEX),
        ],
    )
    for finding in selection.findings:
        assert MARKER not in finding.message
        assert MARKER not in finding.code


def test_two_policies_that_differ_only_in_model_names_give_the_same_findings() -> None:
    """expected_behavior_source: the interface decision 3 (the message is a fixed text plus the
    target and the client id, so it does not depend on a model name).
    """
    first = select(leaky_policy(MARKER)).findings
    second = select(leaky_policy("other")).findings

    assert first
    assert [(f.code, f.message, f.severity) for f in first] == [
        (f.code, f.message, f.severity) for f in second
    ]


# --- a policy with a problem pins nothing --------------------------------------------------


def problem_policies() -> dict[str, ModelPolicy]:
    """Policies that `policy_problems` refuses, each with a valid pin for the tester besides."""
    pin = assignment_doc("role", TESTER, model="example-a")
    fable = exclusion("rule-fable", aliases=("best",), id_patterns=("claude-fable-*",))
    unknown_candidate = profile_doc(
        "quality", candidates=((CLAUDE, ("example-a", "example-none")),)
    )
    copy = entry("example-a", route(CLAUDE, "example-a-copy"))
    excluded_model = entry("example-x", route(CLAUDE, "claude-fable-9"))
    return {
        "an unknown candidate (ORQ-E545)": make_policy(
            [MODEL_A], [pin], profiles=[unknown_candidate]
        ),
        "an unknown role (ORQ-E545)": make_policy(
            [MODEL_A], [pin, assignment_doc("role", "example-no-such-role", model="example-a")]
        ),
        "a duplicate model id (ORQ-E545)": make_policy([MODEL_A, copy], [pin]),
        "an excluded model that nothing assigns (ORQ-E543)": make_policy(
            [MODEL_A, excluded_model], [pin], excluded=[fable]
        ),
    }


@pytest.mark.parametrize("case", list(problem_policies()))
def test_a_policy_with_a_problem_pins_nothing_at_all(case: str) -> None:
    """expected_behavior_source: the interface decision 3 (`select_models` calls `policy_problems`
    first; when the policy has any problem it returns those problems and no roles, no skills and
    no findings: the whole policy is refused, not only the offending target); the plan's AC text
    does not state this, it is the reading that the person asked for. Readings 7 and 8 accepted on
    2026-11-08: an unknown candidate id and a duplicate model id are refused by `policy_problems`.
    The tester has a valid pin in every policy, and the problem is somewhere else.
    """
    policy_ = problem_policies()[case]
    expected = policy_problems(policy_, ROLE_NAMES, SKILL_NAMES)

    selection = select(policy_)

    assert expected
    assert selection.problems == expected
    assert plain(selection.roles) == {}
    assert plain(selection.skills) == {}
    assert selection.findings == ()


def test_a_policy_with_no_problem_returns_no_problem() -> None:
    """expected_behavior_source: the interface decision 3 (the problems of a selection are those
    of `policy_problems`; a clean policy has none).
    """
    policy_ = mode_policy("manual")

    assert policy_problems(policy_, ROLE_NAMES, SKILL_NAMES) == ()
    assert select(policy_).problems == ()


# --- AC-8: an excluded route is never selected ---------------------------------------------

FABLE = exclusion(
    "rule-fable", aliases=("best",), id_patterns=("claude-fable-*",), family_tags=("fable",)
)
# The place where the exclusion matches an approved model that the policy wrongly approves.
EXCLUDED_VARIANTS = (
    "route-name",
    "alias",
    "family-tag",
    "also-known-as",
    "resolves-to",
    "route-of-another-client",
    "family",
    "model-id",
)


def wrongly_approved(variant: str, mode: str = "manual") -> ModelPolicy:
    """An approved model that the exclusion of `fable`, `best` and `claude-fable-*` matches in one
    place, and an assignment of it to the tester for Claude Code.
    """
    routes = [route(CLAUDE, "example-claude-1")]
    model_id = "example-wrong"
    family = "example-family"
    match variant:
        case "route-name":
            routes = [route(CLAUDE, "claude-fable-9")]
        case "alias":
            routes = [route(CLAUDE, "best")]
        case "family-tag":
            routes = [route(CLAUDE, "example-fable-9")]
        case "also-known-as":
            routes = [route(CLAUDE, "example-claude-1", also_known_as=("claude-fable-9",))]
        case "resolves-to":
            routes = [
                route(CLAUDE, "example-claude-latest", kind="alias", resolves_to="claude-fable-9")
            ]
        case "route-of-another-client":
            routes = [route(CLAUDE, "example-claude-1"), route(CODEX, "claude-fable-9")]
        case "family":
            family = "example-fable-family"
        case "model-id":
            model_id = "claude-fable-9"
        case _:
            raise AssertionError(variant)
    return make_policy(
        [entry(model_id, *routes, family=family)],
        [assignment_doc("role", TESTER, model=model_id, mode=mode, client=CLAUDE)],
        excluded=[FABLE],
    )


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("variant", EXCLUDED_VARIANTS)
def test_a_policy_that_approves_an_excluded_route_selects_nothing(variant: str, mode: str) -> None:
    """expected_behavior_source: plan P-5 AC-8 (for a policy that wrongly approves a route
    matching the exclusion of `fable`, `best` and `claude-fable-*`, the selection returns no
    setting for it; the policy has a problem, ORQ-E543, so nothing is pinned); BC-9; R-12;
    ADR-005 decision 2 (the exclusion reads every route string of a model, in every client, and
    its family: reading 6 accepted on 2026-11-08). One case for each place of a model string and
    each mode.
    """
    selection = select(wrongly_approved(variant, mode))

    assert E543 in {problem.code for problem in selection.problems}
    assert plain(selection.roles) == {}
    assert plain(selection.skills) == {}
    assert selection.findings == ()


def test_the_same_route_is_selected_when_no_exclusion_matches_it() -> None:
    """expected_behavior_source: plan P-5 AC-8. A control, not a rule: it shows that it is the
    exclusion alone that stops a pin of the route `claude-fable-9` in the tests above.
    """
    model = entry("example-wrong", route(CLAUDE, "claude-fable-9"))
    policy_ = make_policy(
        [model], [assignment_doc("role", TESTER, model="example-wrong", client=CLAUDE)]
    )

    selection = select(policy_)

    assert selection.problems == ()
    assert plain(selection.roles) == {TESTER: {CLAUDE: ModelSetting("claude-fable-9", "id")}}
