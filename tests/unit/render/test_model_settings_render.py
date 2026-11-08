"""The three client writers and the model settings a selection gives them (phase P-5).

Every test cites its `expected_behavior_source`. AC-2 to AC-8 are acceptance criteria of phase P-5
in docs/design/dynamic-model-profiles/plan.yaml (AC-10 is the gate status and is no test), and so
is the writer half of AC-9. BC-n are rows of design/component.md, F-n its failure rows, and ADR-n
the decision records of design/: ADR-001 decisions 2, 3 and 7 (default, modes, task scope),
ADR-003 decisions 1 to 6 (the selection travels on the role and skill objects, a pin is the exact
route name, a Cursor value is a plain id, skills for Claude Code only, no settings file, no
`missing-candidate` text here) and ADR-005 decision 2 (the exclusion, and the renderers write only
what the resolver returns). What `select_models` returns, the types and the request builder are
in tests/unit/application/test_model_settings_request.py.

"The interface decision" is the interface that the Coder of this phase implements and that the
brief of this phase's Tester states. For the writers: `claude_role` writes `model: <name>` where
`model: inherit` was, and `effort: <effort>` on the next line when the effort is set; `cursor_role`
writes `model: <name>` only when the entry has no effort and `cursor_plain_id(name)` is true, and
never an effort; `codex_role` writes `model = "<name>"` and, with an effort,
`model_reasoning_effort = "<effort>"` before `developer_instructions`; `claude_skill_files` adds
`model` and `effort` after the existing front matter fields; `agents_skill_files` never reads
`model_settings`; every writer reads only its own client's entry; every value passes through
`front_matter` or `toml_table`.

Some tests rely on a reading that the person accepted on 2026-11-08 for the resolver (P-4):
reading 3 (an invalid level passes to the next), reading 6 (the exclusion reads the family and
every route string of a model) and reading 8 (a client-scoped assignment before an unscoped one,
task-scoped assignments dropped). Each such test says so.

These tests were written first, by the Tester of phase P-5 on 2026-11-08, before the
implementation existed. A policy is built in code as plain data and validated with
`ModelPolicy.model_validate`. Names and texts are placeholders (`example-*`); the only model
strings of a vendor kind are the three that AC-8 itself names (`fable`, `best` and
`claude-fable-*`). The three golden files of AC-3 do not exist yet; the golden test fails on them
until they are written with `--update-golden` and read.

Behaviour that neither the sources nor the brief settle is deliberately not pinned here:
- the order of `model` and `model_reasoning_effort` in a Codex file and the place of both among
  `name`, `description` and `sandbox_mode` (the brief says only "before `developer_instructions`");
- the order of `model` and `effort` among the fields of a Claude Code skill beyond "after the
  existing fields", and the value of an `effort` for a skill that Cursor or Codex also reads;
- whether Cursor, which also reads `.claude/skills`, honours a `model` in a skill (ADR-003
  Consequences: an unknown, not a claim);
- the wording of any finding (the render path says nothing about it) and `missing-candidate`;
- what a writer does with a setting whose `kind` is `alias` beyond writing its name: it is written
  like an id (ADR-003 decision 2), the warning is the selection's;
- the bytes of the golden files, which the golden test compares and does not restate.
"""

from __future__ import annotations

import dataclasses
import functools
import tomllib
from collections.abc import Callable, Sequence
from typing import Any

import pytest
import yaml

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.roles import claude_role, codex_role, cursor_role
from orqlet.adapters.render.skills import agents_skill_files, claude_skill_files
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.instruction_adapter import (
    ClientRole,
    ClientSkill,
    InstructionAdapter,
    ModelSetting,
    RenderedFile,
    RenderRequest,
)
from orqlet.application.usecases.model_selection import select_models
from orqlet.application.usecases.render_request import build_render_request
from orqlet.domain.model_resolution import Effort
from tests.support.render import (
    EMPTY_RESOURCES,
    ROLE_NAMES,
    SAMPLE_RULES,
    SKILL_NAMES,
    skill_files,
)

pytestmark = pytest.mark.unit

CLAUDE = "claude-code"
CURSOR = "cursor"
CODEX = "codex"
CLIENTS = (CLAUDE, CURSOR, CODEX)
INVENTORY = "orqlet-inventory"
TESTER = "orqlet-tester"
REVIEW = "orqlet-review"
GOLDEN_FAMILY = "models-2026-11"
FENCE_END = "\n---\n"

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
CLAUDE_SKILL = ".claude/skills/{}/SKILL.md"
WRITERS: list[tuple[str, Callable[[ClientRole], RenderedFile]]] = [
    (CLAUDE, claude_role),
    (CURSOR, cursor_role),
    (CODEX, codex_role),
]


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


# Two approved models that have a differently named route for each of the three clients, and one
# whose routes are aliases that resolve to ids.
MODEL_A = entry("example-a", *routes_of("example-a"))
MODEL_B = entry("example-b", *routes_of("example-b"))
MODEL_ALIAS = entry(
    "example-alias",
    *(
        route(client, name, kind="alias", resolves_to=f"{name}-1")
        for client, name in names_of("example-alias").items()
    ),
)


# --- rendering and reading ---------------------------------------------------------------


def request_for(policy_: ModelPolicy, clients: Sequence[str] = CLIENTS) -> RenderRequest:
    """The request of an installation whose policy is `policy_` and whose clients are `clients`."""
    selection = select_models(policy_, ROLE_NAMES, SKILL_NAMES, clients)
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


@functools.cache
def base_files(client: str) -> dict[str, bytes]:
    """The files of a client with no policy: today's files."""
    request = build_render_request(
        PackagedWorkflow(), StrictYamlLoader(), SAMPLE_RULES, EMPTY_RESOURCES, None
    )
    return files_of(request, client)


def role_text(request: RenderRequest, client: str, role: str) -> str:
    return files_of(request, client)[ROLE_PATH[client].format(role)].decode("utf-8")


def base_text(client: str, role: str) -> str:
    return base_files(client)[ROLE_PATH[client].format(role)].decode("utf-8")


def swap_model_line(base: str, *replacement: str) -> str:
    """The base role file with its `model: inherit` line replaced by the lines given."""
    lines = base.split("\n")
    index = lines.index("model: inherit")
    return "\n".join([*lines[:index], *replacement, *lines[index + 1 :]])


def front_matter_of(text: str) -> dict[str, Any]:
    """The front matter of a Markdown file as PyYAML reads it (YAML 1.1, a line reader's peer)."""
    assert text.startswith("---\n")
    end = text.index(FENCE_END, 3)
    parsed = yaml.safe_load(text[4 : end + 1])
    assert isinstance(parsed, dict)
    return parsed


def body_of(text: str) -> str:
    """The text after the front matter of a Markdown file."""
    return text[text.index(FENCE_END, 3) + len(FENCE_END) :]


def assert_only(request: RenderRequest, client: str, *changed: str) -> None:
    """Every file of the client is the file of no policy, except exactly the paths given."""
    files = files_of(request, client)
    base = base_files(client)
    assert set(files) == set(base)
    assert sorted(path for path in files if files[path] != base[path]) == sorted(changed)


def role_paths(client: str, *roles: str) -> list[str]:
    return [ROLE_PATH[client].format(role) for role in roles]


# --- AC-2: only the mode `manual` pins -----------------------------------------------------


def full_policy(mode: str) -> ModelPolicy:
    """Every packaged role and skill is assigned in `mode`, by one model (with an effort) or by a
    profile. Every model has a route for all three clients, so a mode that pinned would show.
    """
    quality = profile_doc(
        "quality",
        candidates=everywhere("example-a", "example-b"),
        fallbacks=everywhere("example-b"),
    )
    assignments: list[dict[str, Any]] = []
    for index, name in enumerate(ROLE_NAMES):
        if index % 2 == 0:
            assignments.append(
                assignment_doc("role", name, model="example-a", mode=mode, effort="high")
            )
        else:
            assignments.append(assignment_doc("role", name, profile="quality", mode=mode))
    for index, name in enumerate(SKILL_NAMES):
        if index % 2 == 0:
            assignments.append(
                assignment_doc("skill", name, model="example-b", mode=mode, effort="low")
            )
        else:
            assignments.append(assignment_doc("skill", name, profile="quality", mode=mode))
    return make_policy([MODEL_A, MODEL_B], assignments, profiles=[quality])


NO_PIN_MODES = ["automatic", "automatic-with-fallbacks"]


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize("mode", NO_PIN_MODES)
def test_the_modes_that_do_not_pin_render_the_files_of_no_policy(mode: str, client: str) -> None:
    """expected_behavior_source: plan P-5 AC-2 (in mode `automatic` and `automatic-with-fallbacks`,
    with or without a policy, the files are as today); BC-2; BC-27; R-9; ADR-001 decision 3
    (`manual` is the only mode that renders a pin; the files of the other modes are those of
    `automatic`). The policy assigns every role and skill, so that a mode that pinned would show.
    """
    request = request_for(full_policy(mode))

    assert_only(request, client)


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize("mode", NO_PIN_MODES)
def test_in_the_modes_that_do_not_pin_a_role_keeps_its_automatic_model_setting(
    mode: str, client: str
) -> None:
    """expected_behavior_source: plan P-5 AC-2 (the model line of a Claude Code and a Cursor role
    file is `model: inherit` and a Codex role file has no model key, as today); BC-2; ADR-001
    decision 2.
    """
    request = request_for(full_policy(mode))

    for role in ROLE_NAMES:
        text = role_text(request, client, role)
        if client == CODEX:
            data = tomllib.loads(text)
            assert "model" not in data, role
            assert "model_reasoning_effort" not in data, role
        else:
            fields = front_matter_of(text)
            assert fields["model"] == "inherit", role
            assert "effort" not in fields, role


@pytest.mark.parametrize("client", CLIENTS)
def test_the_files_of_the_two_modes_that_do_not_pin_are_identical(client: str) -> None:
    """expected_behavior_source: plan P-5 AC-2 ("the files of the two modes are identical"); BC-27
    (`automatic-with-fallbacks` renders the files of `automatic`); ADR-001 decision 3.
    """
    automatic = files_of(request_for(full_policy("automatic")), client)
    with_fallbacks = files_of(request_for(full_policy("automatic-with-fallbacks")), client)

    assert automatic == with_fallbacks


def test_the_policy_of_the_mode_tests_pins_in_mode_manual() -> None:
    """expected_behavior_source: ADR-001 decision 3 (`manual` is the only mode that renders a
    pin). A control for AC-2: the policy of the tests above does change files when its mode lets it.
    Claude Code and Codex change every role file; Cursor changes the roles that are assigned by a
    profile and keeps `model: inherit` for the roles that have an effort (ADR-003 decision 3).
    """
    request = request_for(full_policy("manual"))

    claude_skills = [CLAUDE_SKILL.format(name) for name in SKILL_NAMES]
    assert_only(request, CLAUDE, *role_paths(CLAUDE, *ROLE_NAMES), *claude_skills)
    assert_only(request, CODEX, *role_paths(CODEX, *ROLE_NAMES))
    profile_roles = [name for index, name in enumerate(ROLE_NAMES) if index % 2 == 1]
    assert_only(request, CURSOR, *role_paths(CURSOR, *profile_roles))


# --- AC-3: a manual assignment pins each client with its own name -------------------------


def pinned_request(
    role: str, *, effort: Effort | None, clients: Sequence[str] = CLIENTS
) -> RenderRequest:
    """The role is assigned the model `example-a` in mode `manual`, with `effort`."""
    policy_ = make_policy(
        [MODEL_A], [assignment_doc("role", role, model="example-a", effort=effort)]
    )
    return request_for(policy_, clients)


@pytest.mark.parametrize("effort", [None, "high"])
@pytest.mark.parametrize("role", [TESTER, INVENTORY])
def test_claude_code_gets_the_name_and_the_effort_where_inherit_was(
    role: str, effort: Effort | None
) -> None:
    """expected_behavior_source: plan P-5 AC-3 (Claude Code `model:` and, when the assignment sets
    an effort, `effort:`); BC-3; ADR-003 decision 2; the interface decision 2 (`model: <name>` in
    the same place as `model: inherit`, `effort: <effort>` on the next line, `tools:` and the rest
    unchanged). The tester has no `tools` line and the inventory role has one.
    """
    request = pinned_request(role, effort=effort)
    replacement = ["model: example-a-claude"]
    if effort is not None:
        replacement.append(f"effort: {effort}")

    assert role_text(request, CLAUDE, role) == swap_model_line(
        base_text(CLAUDE, role), *replacement
    )
    assert_only(request, CLAUDE, *role_paths(CLAUDE, role))


@pytest.mark.parametrize("role", [TESTER, INVENTORY])
def test_cursor_gets_the_name_and_no_effort_where_inherit_was(role: str) -> None:
    """expected_behavior_source: plan P-5 AC-3 (Cursor `model:` only); BC-3; ADR-003 decision 2;
    the interface decision 2 (`model: <name>` only when the entry has no effort and the name is a
    plain id; never a quoted value and never an `effort` line).
    """
    request = pinned_request(role, effort=None)
    text = role_text(request, CURSOR, role)

    assert text == swap_model_line(base_text(CURSOR, role), "model: example-a-cursor")
    assert "effort" not in front_matter_of(text)
    assert_only(request, CURSOR, *role_paths(CURSOR, role))


@pytest.mark.parametrize("effort", [None, "high"])
@pytest.mark.parametrize("role", [TESTER, INVENTORY])
def test_codex_gets_the_name_and_the_reasoning_effort_before_the_instructions(
    role: str, effort: Effort | None
) -> None:
    """expected_behavior_source: plan P-5 AC-3 (Codex `model` and `model_reasoning_effort`); BC-3;
    ADR-003 decision 2; the interface decision 2 (`model = "<name>"` and, with an effort,
    `model_reasoning_effort = "<effort>"` lines written through `toml_table`, before
    `developer_instructions`). The other keys and their order are those of no policy.
    """
    request = pinned_request(role, effort=effort)
    text = role_text(request, CODEX, role)
    data = tomllib.loads(text)
    base = tomllib.loads(base_text(CODEX, role))
    keys = list(data)

    assert data["model"] == "example-a-codex"
    assert keys.index("model") < keys.index("developer_instructions")
    assert 'model = "example-a-codex"' in text.splitlines()
    if effort is None:
        assert "model_reasoning_effort" not in data
    else:
        assert data["model_reasoning_effort"] == effort
        assert keys.index("model_reasoning_effort") < keys.index("developer_instructions")
        assert f'model_reasoning_effort = "{effort}"' in text.splitlines()
    rest = {key: value for key, value in data.items() if not key.startswith("model")}
    assert rest == base
    assert list(rest) == list(base)
    assert_only(request, CODEX, *role_paths(CODEX, role))


def test_each_of_the_three_enabled_clients_gets_its_own_name_and_none_of_the_others() -> None:
    """expected_behavior_source: plan P-5 AC-3 ("with two or three clients enabled each file
    carries its own client's name"; the model has three routes with three different names); BC-3;
    ADR-003 decision 1.
    """
    request = pinned_request(TESTER, effort=None)
    names = names_of("example-a")

    for client in CLIENTS:
        text = role_text(request, client, TESTER)
        assert names[client] in text
        for other in CLIENTS:
            if other != client:
                assert names[other] not in text, (client, other)


def test_a_client_that_is_not_enabled_keeps_its_automatic_setting() -> None:
    """expected_behavior_source: plan P-5 AC-3 (two clients enabled: each file carries its own
    client's name); BC-3; the interface decision 3 (a setting only for the clients of `clients`).
    Codex is not enabled, so its role file is the file of no policy.
    """
    request = pinned_request(TESTER, effort=None, clients=(CLAUDE, CURSOR))

    assert_only(request, CLAUDE, *role_paths(CLAUDE, TESTER))
    assert_only(request, CURSOR, *role_paths(CURSOR, TESTER))
    assert_only(request, CODEX)


def test_a_profile_with_candidates_per_client_pins_each_client_with_its_own_candidate() -> None:
    """expected_behavior_source: plan P-5 AC-3 ("an assignment that names a profile whose
    candidates are listed per client"); BC-3; ADR-001 decision 3 (the first eligible candidate).
    The first Codex candidate is only proposed, so it is skipped. The other four roles of every
    client are the files of no policy.
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
    policy_ = make_policy(
        [MODEL_A, MODEL_B, proposed],
        [assignment_doc("role", INVENTORY, profile="engineering")],
        profiles=[engineering],
    )
    request = request_for(policy_)

    assert role_text(request, CLAUDE, INVENTORY) == swap_model_line(
        base_text(CLAUDE, INVENTORY), "model: example-a-claude"
    )
    assert role_text(request, CURSOR, INVENTORY) == swap_model_line(
        base_text(CURSOR, INVENTORY), "model: example-b-cursor"
    )
    assert tomllib.loads(role_text(request, CODEX, INVENTORY))["model"] == "example-b-codex"
    for client in CLIENTS:
        assert_only(request, client, *role_paths(client, INVENTORY))


def test_a_client_scoped_assignment_beats_an_unscoped_one_in_the_file_of_that_client() -> None:
    """expected_behavior_source: plan P-5 AC-3 ("client-scoped assignments (client set) beating
    unscoped ones for that client"); reading 8 accepted on 2026-11-08 (assignments are ordered by
    task, then client); BC-3. The scoped assignment is listed first in the second policy.
    """
    unscoped = assignment_doc("role", TESTER, model="example-a")
    scoped = assignment_doc("role", TESTER, model="example-b", client=CLAUDE)

    for assignments in ([unscoped, scoped], [scoped, unscoped]):
        request = request_for(make_policy([MODEL_A, MODEL_B], assignments))
        assert role_text(request, CLAUDE, TESTER) == swap_model_line(
            base_text(CLAUDE, TESTER), "model: example-b-claude"
        )
        assert role_text(request, CURSOR, TESTER) == swap_model_line(
            base_text(CURSOR, TESTER), "model: example-a-cursor"
        )
        assert tomllib.loads(role_text(request, CODEX, TESTER))["model"] == "example-a-codex"


def test_a_pinned_model_that_is_not_eligible_falls_through_to_the_profile_in_the_file() -> None:
    """expected_behavior_source: reading 3 accepted on 2026-11-08 for the resolver (an invalid
    level passes to the next), reaching a file: the model that the role is pinned to is only
    proposed, so the manual assignment of the profile of the same role is what is written; ADR-001
    decision 4 (precedence); BC-3.
    """
    proposed = entry("example-p", *routes_of("example-p"), state="proposed")
    quality = profile_doc("quality", candidates=everywhere("example-b"))
    assignments = [
        assignment_doc("role", TESTER, model="example-p"),
        assignment_doc("role", TESTER, profile="quality"),
    ]

    request = request_for(make_policy([MODEL_B, proposed], assignments, profiles=[quality]))

    assert role_text(request, CLAUDE, TESTER) == swap_model_line(
        base_text(CLAUDE, TESTER), "model: example-b-claude"
    )
    assert role_text(request, CURSOR, TESTER) == swap_model_line(
        base_text(CURSOR, TESTER), "model: example-b-cursor"
    )
    assert tomllib.loads(role_text(request, CODEX, TESTER))["model"] == "example-b-codex"


def golden_policy() -> ModelPolicy:
    """The fixture policy of the golden files: three client-scoped assignments of the tester in
    mode `manual`. Claude Code and Codex get an effort of `high`; Cursor gets none.
    """
    model = entry(
        "example-tester-model",
        route(CLAUDE, "example-tester-claude"),
        route(CODEX, "example-tester-codex"),
        route(CURSOR, "example-tester-cursor"),
    )
    assignments = [
        assignment_doc("role", TESTER, model="example-tester-model", client=CLAUDE, effort="high"),
        assignment_doc("role", TESTER, model="example-tester-model", client=CODEX, effort="high"),
        assignment_doc("role", TESTER, model="example-tester-model", client=CURSOR),
    ]
    return make_policy([model], assignments)


@pytest.mark.golden
def test_a_pinned_tester_is_written_as_each_client_reads_it(
    golden: Callable[[str, bytes], None],
) -> None:
    """expected_behavior_source: plan P-5 AC-3 ("a pinned `orqlet-tester` is pinned by new golden
    files for each client, family `models-2026-11`"); ADR-003 decision 10 ("a new golden set
    renders a fixture policy for each client"); ORQLET-DET-001. The three files do not exist
    before the Coder writes them with `--update-golden`; this test writes nothing else. Each file
    must also differ from the file of no policy, so that a golden written from an unpinned
    render cannot pass.
    """
    request = request_for(golden_policy())

    for client in CLIENTS:
        path = ROLE_PATH[client].format(TESTER)
        rendered = next(f for f in ADAPTERS[client].render(request).files if str(f.path) == path)
        assert rendered.content != base_files(client)[path], client
        golden(f"{client}/{GOLDEN_FAMILY}/{rendered.path}", rendered.content)


# --- AC-4: Cursor takes a plain id only; no writer builds text by hand ---------------------

SAMPLE_ROLE = ClientRole(name="orqlet-sample", description="Reads carefully", body="Do the work.\n")
SAMPLE_SKILL = ClientSkill(
    name="orqlet-sample",
    description="Reads carefully",
    body="Do the work.\n",
    references=(("notes.md", "Some notes.\n"),),
    inputs=(("skills/orqlet-sample", "1", "0" * 64),),
)
# What Cursor cannot take as a plain value: a bracketed option, an effort, a name that starts with
# a digit, a YAML word, a name with a colon, a space, a quote, a backslash or a line break.
CURSOR_REFUSED = [
    ModelSetting("claude-opus[effort=high]", "id"),
    ModelSetting("claude-opus[effort=high]", "id", "high"),
    ModelSetting("example-cursor", "id", "high"),
    ModelSetting("example-cursor", "alias", "low"),
    ModelSetting("1-example-cursor", "id"),
    ModelSetting("true", "id"),
    ModelSetting("n", "id"),
    ModelSetting("example:cursor", "id"),
    ModelSetting("example cursor", "id"),
    ModelSetting('example"cursor', "id"),
    ModelSetting("back\\slash", "id"),
    ModelSetting("[example]", "id"),
    ModelSetting("example-cursor\nmodel: injected", "id"),
]
# Values that need quotes in front matter or in a TOML string, and values that look like an
# injected line. Each must read back as the same string.
AWKWARD_NAMES = [
    'example "quoted"',
    "back\\slash",
    "colon:name",
    "at@sign",
    "with space # hash",
    "[bracketed]",
    "true",
    "Null",
    "123",
    "tab\tname",
    "name-\u00e9",
    "'single'",
    "- dash",
    "~",
    "line1\nmodel: injected",
    'x"\nmodel = "injected',
]


def with_setting(role: ClientRole, client: str, setting: ModelSetting) -> ClientRole:
    return dataclasses.replace(role, model_settings={client: setting})


@pytest.mark.parametrize("setting", CURSOR_REFUSED)
def test_cursor_keeps_inherit_for_an_effort_a_bracket_or_a_name_that_is_not_plain(
    setting: ModelSetting,
) -> None:
    """expected_behavior_source: plan P-5 AC-4 (a Cursor value is written only when
    `cursor_plain_id` is true and never with a bracketed option; an effort assignment for Cursor
    and a name that is not plain-safe leave `model: inherit`); BC-34; ADR-003 decision 3; the
    interface decision 2 (`cursor_role` keeps `model: inherit` otherwise; Cursor never gets an
    effort line). A role is built by hand with the setting, so that the writer is tested alone.
    """
    role = with_setting(SAMPLE_ROLE, CURSOR, setting)

    text = cursor_role(role).content.decode("utf-8")

    assert cursor_role(role).content == cursor_role(SAMPLE_ROLE).content
    assert "[" not in text
    assert front_matter_of(text)["model"] == "inherit"


@pytest.mark.parametrize("name", ["example-cursor-1", "Example.Cursor_2/x+y", "a", "Cursor-3"])
def test_cursor_writes_a_plain_id_bare_and_never_quoted(name: str) -> None:
    """expected_behavior_source: plan P-5 AC-4 and AC-3 (a Cursor value is written when
    `cursor_plain_id` is true; `model:` only); ADR-003 decision 3 (a plain id, never quoted:
    Cursor once read the quotes of a `name` literally); the interface decision 2 (`model: <name>`,
    never quoted).
    """
    role = with_setting(SAMPLE_ROLE, CURSOR, ModelSetting(name, "id"))

    text = cursor_role(role).content.decode("utf-8")

    assert text == swap_model_line(
        cursor_role(SAMPLE_ROLE).content.decode("utf-8"), f"model: {name}"
    )
    assert front_matter_of(text)["model"] == name


def test_cursor_writes_an_alias_name_that_is_plain_like_an_id() -> None:
    """expected_behavior_source: plan P-5 AC-7 (an alias name is written when the route is
    declared as an alias); ADR-003 decision 2; the interface decision 2 (the writer reads the
    name; the warning for an alias is the selection's).
    """
    role = with_setting(SAMPLE_ROLE, CURSOR, ModelSetting("example-cursor-latest", "alias"))

    text = cursor_role(role).content.decode("utf-8")

    assert text == swap_model_line(
        cursor_role(SAMPLE_ROLE).content.decode("utf-8"), "model: example-cursor-latest"
    )


@pytest.mark.parametrize("name", AWKWARD_NAMES)
def test_claude_code_quotes_a_name_that_needs_it_and_it_reads_back_as_written(name: str) -> None:
    """expected_behavior_source: plan P-5 AC-4 ("no writer builds text by hand: every value passes
    through `front_matter`"); ADR-003 decision 3; the interface decision 2 (every value passes
    through `front_matter` / `toml_table`). The front matter is read with PyYAML: the name and
    nothing else is the value of `model`, and no field is added by a name that holds a line break.
    """
    role = with_setting(SAMPLE_ROLE, CLAUDE, ModelSetting(name, "id", "high"))

    fields = front_matter_of(claude_role(role).content.decode("utf-8"))

    assert list(fields) == ["name", "description", "tools", "model", "effort"]
    assert fields["model"] == name
    assert fields["effort"] == "high"


@pytest.mark.parametrize("name", AWKWARD_NAMES)
def test_codex_quotes_a_name_that_needs_it_and_it_reads_back_as_written(name: str) -> None:
    """expected_behavior_source: plan P-5 AC-4 ("every value passes through ... `toml_table`");
    ADR-003 decision 3; the interface decision 2. The file is read with `tomllib`: the name is the
    value of `model`, and no key is added by a name that holds a line break or a quote. The
    other keys are those of no policy.
    """
    role = with_setting(SAMPLE_ROLE, CODEX, ModelSetting(name, "id", "medium"))

    data = tomllib.loads(codex_role(role).content.decode("utf-8"))
    base = tomllib.loads(codex_role(SAMPLE_ROLE).content.decode("utf-8"))

    assert data["model"] == name
    assert data["model_reasoning_effort"] == "medium"
    assert {key: value for key, value in data.items() if not key.startswith("model")} == base


@pytest.mark.parametrize("name", AWKWARD_NAMES)
def test_the_claude_code_skill_quotes_a_name_that_needs_it_and_it_reads_back(name: str) -> None:
    """expected_behavior_source: plan P-5 AC-4 (every value passes through `front_matter`) and
    AC-5 (the Claude Code skill file gets `model:` and `effort:`); the interface decision 2
    (`claude_skill_files` adds `model` and `effort` after the existing fields).
    """
    skill = dataclasses.replace(
        SAMPLE_SKILL, model_settings={CLAUDE: ModelSetting(name, "id", "low")}
    )

    fields = front_matter_of(claude_skill_files(skill)[0].content.decode("utf-8"))

    assert list(fields) == [
        "name",
        "description",
        "disable-model-invocation",
        "model",
        "effort",
    ]
    assert fields["model"] == name
    assert fields["effort"] == "low"


# --- AC-5: a skill is pinned in the Claude Code file only ---------------------------------


def skill_request(
    mode: str = "manual", *, effort: str | None, client: str | None = None
) -> RenderRequest:
    """The review skill is assigned the model `example-a`, for `client` or for every client."""
    assignment = assignment_doc(
        "skill", REVIEW, model="example-a", mode=mode, effort=effort, client=client
    )
    return request_for(make_policy([MODEL_A], [assignment]))


@pytest.mark.parametrize("effort", [None, "high"])
def test_a_manual_skill_assignment_writes_model_and_effort_into_the_claude_code_skill(
    effort: str | None,
) -> None:
    """expected_behavior_source: plan P-5 AC-5 (a skill assignment in mode `manual` writes
    `model:` and, when set, `effort:` into the front matter of the Claude Code skill file); BC-7;
    ADR-003 decision 4; the interface decision 2 (after the existing fields; references never
    changed). The body of the skill and every other file are those of no policy.
    """
    request = skill_request(effort=effort)
    path = CLAUDE_SKILL.format(REVIEW)
    text = files_of(request, CLAUDE)[path].decode("utf-8")
    base = base_files(CLAUDE)[path].decode("utf-8")
    base_fields = front_matter_of(base)
    expected = {**base_fields, "model": "example-a-claude"}
    if effort is not None:
        expected["effort"] = effort

    fields = front_matter_of(text)

    assert fields == expected
    assert list(fields) == list(expected)
    assert body_of(text) == body_of(base)
    assert_only(request, CLAUDE, path)


@pytest.mark.parametrize("client", [CURSOR, CODEX])
def test_the_shared_agents_skill_files_never_change_with_a_policy(client: str) -> None:
    """expected_behavior_source: plan P-5 AC-5 (the `.agents/skills` file, which Cursor and Codex
    share, never changes); BC-8; ADR-003 decision 4; the interface decision 2 (`agents_skill_files`
    never reads `model_settings`). The full policy in mode `manual` assigns every skill; the
    bytes of every file under `.agents/skills`, the Codex sidecars included, are those of no
    policy, for the Cursor adapter and for the Codex adapter.
    """
    request = request_for(full_policy("manual"))
    shared = skill_files(".agents/skills")

    files = files_of(request, client)
    base = base_files(client)

    assert shared
    assert {p: c for p, c in files.items() if p.startswith(".agents/skills/")} == {
        p: c for p, c in base.items() if p.startswith(".agents/skills/")
    }
    assert all(files[path] == base[path] for path in shared)


@pytest.mark.parametrize("mode", NO_PIN_MODES)
def test_a_skill_assignment_in_a_mode_that_does_not_pin_writes_nothing(mode: str) -> None:
    """expected_behavior_source: plan P-5 AC-5 ("in any other mode it writes none"); BC-7;
    ADR-003 decision 4; ADR-001 decision 3.
    """
    request = skill_request(mode, effort="high")

    for client in CLIENTS:
        assert_only(request, client)


@pytest.mark.parametrize("client", [CODEX, CURSOR])
def test_a_skill_assignment_scoped_to_codex_or_cursor_changes_no_file(client: str) -> None:
    """expected_behavior_source: plan P-5 AC-5 ("an assignment of a skill for Codex or Cursor gives
    ORQ-W546 and no change"; the finding is tested with the selection); BC-7; F-4; ADR-003
    decision 4. Claude Code has no assignment, so its skill file is not pinned either.
    """
    request = skill_request(effort="high", client=client)

    for adapter_client in CLIENTS:
        assert_only(request, adapter_client)


def test_a_skill_assignment_with_no_client_pins_claude_code_and_no_other_client_file() -> None:
    """expected_behavior_source: plan P-5 AC-5 (a skill assignment for Codex or Cursor with no
    client set pins Claude Code; nothing changes for the other two); BC-7; BC-8; ADR-003 decision
    4. The model name of the other two clients is in no file of theirs.
    """
    request = skill_request(effort=None)

    assert_only(request, CLAUDE, CLAUDE_SKILL.format(REVIEW))
    assert_only(request, CURSOR)
    assert_only(request, CODEX)


def test_the_skill_writers_read_only_the_claude_code_entry_and_leave_the_references_alone() -> None:
    """expected_behavior_source: the interface decision 2 (`claude_skill_files(skill)` writes the
    claude-code entry; `agents_skill_files(skill)` never reads `model_settings`; references are
    never changed); plan P-5 AC-9 (each writer reads only its own client's entry).
    """
    every_client = {
        CLAUDE: ModelSetting("example-claude", "id", "high"),
        CURSOR: ModelSetting("example-cursor", "id"),
        CODEX: ModelSetting("example-codex", "id", "low"),
    }
    skill = dataclasses.replace(SAMPLE_SKILL, model_settings=every_client)
    only_others = dataclasses.replace(
        SAMPLE_SKILL, model_settings={CURSOR: every_client[CURSOR], CODEX: every_client[CODEX]}
    )

    claude = claude_skill_files(skill)
    text = claude[0].content.decode("utf-8")
    fields = front_matter_of(text)

    assert agents_skill_files(skill) == agents_skill_files(SAMPLE_SKILL)
    assert agents_skill_files(only_others) == agents_skill_files(SAMPLE_SKILL)
    assert claude_skill_files(only_others) == claude_skill_files(SAMPLE_SKILL)
    assert (fields["model"], fields["effort"]) == ("example-claude", "high")
    assert "example-cursor" not in text
    assert "example-codex" not in text
    assert len(claude) == 2
    assert claude[1:] == claude_skill_files(SAMPLE_SKILL)[1:]
    assert body_of(text) == body_of(claude_skill_files(SAMPLE_SKILL)[0].content.decode("utf-8"))


# --- AC-6: no settings file and no new path ------------------------------------------------


def test_a_full_policy_adds_and_removes_no_file_for_any_client() -> None:
    """expected_behavior_source: plan P-5 AC-6 (for a request with a full fixture policy and all
    three clients, the set of paths that the adapters write equals the set for no policy: no
    `settings.json`, `settings.local.json`, `config.toml` or model file); BC-8; ADR-003 decision
    5. The policy pins roles and skills, so the files do change: only their bytes.
    """
    request = request_for(full_policy("manual"))
    settings_files = {"settings.json", "settings.local.json", "config.toml"}

    for client in CLIENTS:
        files = files_of(request, client)
        assert set(files) == set(base_files(client)), client
        assert files != base_files(client), client
        assert not {p for p in files if p.rsplit("/", 1)[-1] in settings_files}, client


# --- AC-7: the exact name, aliases, task scope, blocked routes -----------------------------


def test_a_pin_writes_the_exact_route_name_and_none_of_its_other_strings() -> None:
    """expected_behavior_source: plan P-5 AC-7 ("a pin uses the route's exact `name`"); BC-28;
    ADR-003 decision 2 (a pin uses the exact ID). Each route also lists a longer spelling.
    """
    model = entry(
        "example-a",
        *(
            route(client, name, also_known_as=(f"{name}-high",))
            for client, name in names_of("example-a").items()
        ),
    )
    policy_ = make_policy([model], [assignment_doc("role", TESTER, model="example-a")])

    request = request_for(policy_)

    assert role_text(request, CLAUDE, TESTER) == swap_model_line(
        base_text(CLAUDE, TESTER), "model: example-a-claude"
    )
    assert role_text(request, CURSOR, TESTER) == swap_model_line(
        base_text(CURSOR, TESTER), "model: example-a-cursor"
    )
    assert tomllib.loads(role_text(request, CODEX, TESTER))["model"] == "example-a-codex"
    for client, name in names_of("example-a").items():
        assert f"{name}-high" not in role_text(request, client, TESTER)


def test_an_alias_route_is_written_by_its_name_and_never_by_what_it_resolves_to() -> None:
    """expected_behavior_source: plan P-5 AC-7 (an alias name is written only when the route is
    `kind: alias` with `resolves_to`; the warning ORQ-W545 is tested with the selection); BC-28;
    ADR-003 decision 2; F-17.
    """
    policy_ = make_policy([MODEL_ALIAS], [assignment_doc("role", TESTER, model="example-alias")])

    request = request_for(policy_)

    assert role_text(request, CLAUDE, TESTER) == swap_model_line(
        base_text(CLAUDE, TESTER), "model: example-alias-claude"
    )
    assert role_text(request, CURSOR, TESTER) == swap_model_line(
        base_text(CURSOR, TESTER), "model: example-alias-cursor"
    )
    assert tomllib.loads(role_text(request, CODEX, TESTER))["model"] == "example-alias-codex"
    for client, name in names_of("example-alias").items():
        assert f"{name}-1" not in role_text(request, client, TESTER)


def test_a_task_scoped_assignment_is_never_written_into_a_file() -> None:
    """expected_behavior_source: plan P-5 AC-7 and BC-43 (a task-scoped assignment is never
    rendered into a file); ADR-001 decision 7 (task scope is a resolve-time selector only);
    reading 8 accepted on 2026-11-08 (task-scoped assignments are dropped for rendering). The
    first policy has task-scoped assignments only; in the second, an unscoped assignment in a
    mode that does not pin sits beside a task-scoped manual one that must not win.
    """
    task_only = make_policy(
        [MODEL_A],
        [
            assignment_doc("role", TESTER, model="example-a", task="example-task"),
            assignment_doc("skill", REVIEW, model="example-a", task="example-task"),
        ],
    )
    beaten = make_policy(
        [MODEL_A, MODEL_B],
        [
            assignment_doc("role", TESTER, model="example-b", task="example-task"),
            assignment_doc("role", TESTER, model="example-a", mode="automatic"),
        ],
    )

    for policy_ in (task_only, beaten):
        request = request_for(policy_)
        for client in CLIENTS:
            assert_only(request, client)


def test_a_blocked_route_is_skipped_and_the_first_other_named_route_is_written() -> None:
    """expected_behavior_source: plan P-5 AC-7 ("the first non-blocked named route is the one
    written; a blocked route is skipped", the behaviour of phase P-4); BC-28. The other two
    clients have no route, so their files are those of no policy.
    """
    model = entry(
        "example-a",
        route(CLAUDE, "example-a-blocked", access="blocked"),
        route(CLAUDE, "example-a-claude"),
        route(CLAUDE, "example-a-later"),
    )
    policy_ = make_policy([model], [assignment_doc("role", TESTER, model="example-a")])

    request = request_for(policy_)

    assert role_text(request, CLAUDE, TESTER) == swap_model_line(
        base_text(CLAUDE, TESTER), "model: example-a-claude"
    )
    assert_only(request, CURSOR)
    assert_only(request, CODEX)


# --- AC-8: an excluded string reaches no file ---------------------------------------------

FABLE = exclusion(
    "rule-fable", aliases=("best",), id_patterns=("claude-fable-*",), family_tags=("fable",)
)
EXCLUDED_STRINGS = ("fable", "best", "claude-fable-")
MODES = ("automatic", "manual", "automatic-with-fallbacks")
# Where the exclusion of `fable`, `best` and `claude-fable-*` matches an approved model.
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
    """An approved model that the exclusion matches in one place, and an assignment of it to the
    tester for Claude Code. The policy has a problem, so no setting must reach a file.
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


def excluded_hits(request: RenderRequest, client: str) -> list[str]:
    """Each file of the client that holds one of the three strings, in any letter case."""
    hits: list[str] = []
    for path, content in files_of(request, client).items():
        text = content.decode("utf-8").lower()
        hits += [f"{path}: {needle}" for needle in EXCLUDED_STRINGS if needle in text]
    return hits


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("variant", EXCLUDED_VARIANTS)
def test_no_file_of_any_client_holds_an_excluded_string_in_any_mode(
    variant: str, mode: str
) -> None:
    """expected_behavior_source: plan P-5 AC-8 (for a policy that wrongly approves a route
    matching the Fable exclusion, for every combination of mode and client none of the rendered
    files, role files and skill files included, contains `fable`, `best` or `claude-fable-` in any
    letter case); BC-9; R-12; ADR-005 decision 2 (the renderers write only what the resolver
    returns). The excluded string is the route name, an alias, a family tag, an `also_known_as`,
    a `resolves_to`, the route of another client, the family or the id (reading 6 accepted on
    2026-11-08: the exclusion reads the family and every route string of a model).
    """
    request = request_for(wrongly_approved(variant, mode))

    for client in CLIENTS:
        assert excluded_hits(request, client) == [], client
        assert_only(request, client)


def test_the_scan_of_the_files_does_find_a_name_that_is_written() -> None:
    """expected_behavior_source: plan P-5 AC-8. A control, not a rule: when no exclusion matches
    the route `claude-fable-9`, the same policy pins it and the scan of the tests above sees it
    in the Claude Code file, so that the scan can fail.
    """
    model = entry("example-wrong", route(CLAUDE, "claude-fable-9"))
    policy_ = make_policy(
        [model], [assignment_doc("role", TESTER, model="example-wrong", client=CLAUDE)]
    )

    request = request_for(policy_)

    path = ROLE_PATH[CLAUDE].format(TESTER)
    assert sorted(excluded_hits(request, CLAUDE)) == [f"{path}: claude-fable-", f"{path}: fable"]


# --- AC-9: each writer reads only its own client's entry ----------------------------------

EVERY_CLIENT = {
    CLAUDE: ModelSetting("example-claude", "id", "high"),
    CURSOR: ModelSetting("example-cursor", "id"),
    CODEX: ModelSetting("example-codex", "id", "low"),
}


def test_each_role_writer_writes_its_own_clients_entry_and_none_of_the_others() -> None:
    """expected_behavior_source: plan P-5 AC-9 (each writer reads only its own client's entry);
    ADR-003 decision 1; the interface decision 2 (writers read ONLY their own client's entry). A
    role is built by hand with an entry for each client; the efforts differ (`high` for Claude
    Code, `low` for Codex, none for Cursor), so an effort of another client would show.
    """
    role = dataclasses.replace(SAMPLE_ROLE, model_settings=EVERY_CLIENT)

    claude = claude_role(role).content.decode("utf-8")
    cursor = cursor_role(role).content.decode("utf-8")
    codex = codex_role(role).content.decode("utf-8")

    assert claude == swap_model_line(
        claude_role(SAMPLE_ROLE).content.decode("utf-8"), "model: example-claude", "effort: high"
    )
    assert cursor == swap_model_line(
        cursor_role(SAMPLE_ROLE).content.decode("utf-8"), "model: example-cursor"
    )
    data = tomllib.loads(codex)
    assert (data["model"], data["model_reasoning_effort"]) == ("example-codex", "low")
    for text, others in (
        (claude, ("example-cursor", "example-codex")),
        (cursor, ("example-claude", "example-codex")),
        (codex, ("example-claude", "example-cursor")),
    ):
        for other in others:
            assert other not in text


@pytest.mark.parametrize(("client", "writer"), WRITERS)
def test_a_role_with_only_other_clients_entries_is_written_as_today(
    client: str, writer: Callable[[ClientRole], RenderedFile]
) -> None:
    """expected_behavior_source: plan P-5 AC-9 (each writer reads only its own client's entry);
    the interface decision 2 (a role with only other clients' entries stays `inherit` or has no
    model key); BC-1.
    """
    others = {name: setting for name, setting in EVERY_CLIENT.items() if name != client}
    role = dataclasses.replace(SAMPLE_ROLE, model_settings=others)

    assert writer(role) == writer(SAMPLE_ROLE)


@pytest.mark.parametrize(("client", "writer"), WRITERS)
def test_a_role_with_no_model_settings_is_written_as_today(
    client: str, writer: Callable[[ClientRole], RenderedFile]
) -> None:
    """expected_behavior_source: plan P-5 AC-1 and the interface decision 1 (an empty
    `model_settings` is the default and the role is written as before: `model: inherit` for
    Claude Code and Cursor, no model key for Codex); BC-1; ADR-003 decision 1.
    """
    text = writer(dataclasses.replace(SAMPLE_ROLE, model_settings={})).content.decode("utf-8")

    if client == CODEX:
        assert "model" not in tomllib.loads(text)
    else:
        assert front_matter_of(text)["model"] == "inherit"
    assert writer(SAMPLE_ROLE).content.decode("utf-8") == text
