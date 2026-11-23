"""User-scope renders of Claude Code, Cursor and Codex (task one-command-setup, phase P-7).

Every test cites its `expected_behavior_source`: AC-2 to AC-8 are acceptance criteria of phase P-7
in docs/design/one-command-setup/plan.yaml (AC-1 and AC-7's request half are in
tests/unit/application/test_user_render_request.py; AC-9 is the gate status and is no test). BC-n
are the acceptance rows of docs/design/one-command-setup/design/component.md section 6, K-n its
constraints of section 9, and ADR-n the decision records of design/: ADR-002 decisions 1, 2, 3 and 7
(the prefixes and sub-paths of the user scope, the one shared `agents/skills` render with its
sidecar, hook entries as entry objects, the user request), ADR-004 decisions 1, 2, 3 and 7 (two
events, advisory only, one registration per client, the bare `orqlet` command) and ADR-005
decisions 3 and 4 (the global delivery of the foundation and its precedence sentence). "The K-12
citations" are the self-check of the plan (plan.yaml, the check that starts "K-12 citations"): the
hook schema and output field each client documents. "The plan's golden list" is the P-7
file_operations, which name the seven files of the user golden family `user-2026-11`.

HOW THESE TESTS WERE WRITTEN. The Tester of P-7 wrote them before the implementation existed. The
interface below is the Tester's reading of the design; the Coder aligns with it or raises it:
- a user render is the existing `render(request)` of each adapter, called with the request of
  `build_user_render_request(workflow)`, whose `scope` is `RenderScope.USER` (component.md section
  4: "`RenderRequest.scope: RenderScope`"); no new render method;
- a user-scope path carries the prefix of its root (ADR-002 decision 1): `claude/`, `cursor/`,
  `codex/`, `agents/` and `data/`; a skill or agent path is the project path without its leading
  dot (`.claude/skills/x` becomes `claude/skills/x`);
- a hook entry is one `RenderedFile` whose `path` is the shared JSON file, whose `entry` names the
  entry and whose `owner` is `OwnerMode.SHARED_ENTRY` (ADR-002 decision 3, the existing
  `RenderedFile.entry` field). The entry names `orqlet-session-start` and `orqlet-post-edit` and the
  golden name `<path>--<entry>` come from the plan's golden list;
- the content of an entry is the canonical JSON (`orqlet.domain.digest.canonical_json`) of one JSON
  object (plan P-7: "Canonical bytes of a hook entry"; ADR-002 decision 3: entries are compared by
  their canonical-JSON hash);
- the Codex `AGENTS.md` is a `SHARED_BLOCK` file holding the managed block (ADR-002 decision 2:
  "`AGENTS.md` takes a managed block").

Choices:
- Where inside its entry object a handler sits is not pinned: the handler is the one object of the
  entry that has a `command` key, and it must equal the object of AC-4 exactly. The event name must
  appear in the entry as a key or a string; the Claude Code post-edit matcher is the value of the
  one `matcher` key; Cursor's "version 1 file" is a `version` key with the value 1 in the entry.
- A left-out registration (AC-5) is a capability limit whose message holds `post-edit`, plus
  `context` for Cursor and `patch` for Codex. Its code and the rest of the wording are not pinned.
- "start with the precedence sentence" (AC-6) is read literally: the file, or for Codex the block
  after its begin marker line, starts with the first paragraph of the composed foundation.
- AC-7's "a model or effort field" is read together with AC-2's "the bytes of the same project
  file": a project agent with no policy carries `model: inherit`, which names no model and leaves
  the choice to the client (ADR-002 Consequences: user-scope agents "follow each client's default
  model"). So a `model` field is allowed only with the value `inherit`, and no `effort` or
  `model_reasoning_effort` field is allowed.
- "no absolute path" (AC-2) is checked as: no text holds the test's home folder, a POSIX path
  starting at a common system folder, a Windows drive path or a `~/` path.
- AC-8 reads the existing golden files directly, not through the `golden` fixture, so that
  `--update-golden` on this file cannot rewrite the project family.

Deliberately NOT pinned here:
- the limits that a user render reports besides the two of AC-5;
- the bytes of the user golden family, which the golden test compares and does not restate (they
  are written with `--update-golden` after the person's yes);
- the name of the Codex managed block and whether it differs from the project `baseline` block;
- the file class of a hook entry or of a foundation copy.
"""

from __future__ import annotations

import functools
import json
import re
import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.ports.instruction_adapter import (
    InstructionAdapter,
    RenderedFile,
    RenderRequest,
    RenderResult,
    RenderScope,
)
from orqlet.application.usecases.foundation import compose_foundation
from orqlet.application.usecases.user_render_request import build_user_render_request
from orqlet.domain.digest import canonical_json
from orqlet.domain.ownership import OwnerMode
from tests.support.render import (
    API_GUIDELINES,
    PYTEST_DOCS,
    ROLE_NAMES,
    SKILL_NAMES,
    packaged_request,
    skill_files,
)

pytestmark = pytest.mark.unit

CLAUDE = "claude-code"
CURSOR = "cursor"
CODEX = "codex"
CLIENTS = (CLAUDE, CURSOR, CODEX)
ADAPTERS: dict[str, InstructionAdapter] = {
    CLAUDE: ClaudeCodeAdapter(),
    CURSOR: CursorAdapter(),
    CODEX: CodexAdapter(),
}
GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "golden"
USER_FAMILY = "user-2026-11"
PROJECT_FAMILY = "docs-2026-10"

SESSION_START = "orqlet-session-start"
POST_EDIT = "orqlet-post-edit"
CLAUDE_SETTINGS = "claude/settings.json"
CURSOR_HOOKS = "cursor/hooks.json"
CODEX_HOOKS = "codex/hooks.json"
CLAUDE_FOUNDATION = "claude/rules/orqlet-foundation.md"
CURSOR_USER_RULES = "data/cursor-user-rules.md"
CODEX_AGENTS = "codex/AGENTS.md"

SIDECARS = [f"agents/skills/{name}/agents/openai.yaml" for name in SKILL_NAMES]
EXPECTED_KEYS: dict[str, list[str]] = {
    CLAUDE: [
        *skill_files("claude/skills"),
        *(f"claude/agents/{name}.md" for name in ROLE_NAMES),
        CLAUDE_FOUNDATION,
        f"{CLAUDE_SETTINGS}--{SESSION_START}",
        f"{CLAUDE_SETTINGS}--{POST_EDIT}",
    ],
    CURSOR: [
        *skill_files("agents/skills"),
        *SIDECARS,
        *(f"cursor/agents/{name}.md" for name in ROLE_NAMES),
        f"{CURSOR_HOOKS}--{SESSION_START}",
        CURSOR_USER_RULES,
    ],
    CODEX: [
        *skill_files("agents/skills"),
        *SIDECARS,
        *(f"codex/agents/{name}.toml" for name in ROLE_NAMES),
        CODEX_AGENTS,
        f"{CODEX_HOOKS}--{SESSION_START}",
    ],
}
# The plan's golden list: the user family holds these files and no skill or agent file.
GOLDEN_KEYS: dict[str, frozenset[str]] = {
    CLAUDE: frozenset(
        {
            CLAUDE_FOUNDATION,
            f"{CLAUDE_SETTINGS}--{SESSION_START}",
            f"{CLAUDE_SETTINGS}--{POST_EDIT}",
        }
    ),
    CURSOR: frozenset({f"{CURSOR_HOOKS}--{SESSION_START}", CURSOR_USER_RULES}),
    CODEX: frozenset({CODEX_AGENTS, f"{CODEX_HOOKS}--{SESSION_START}"}),
}
FOUNDATION_COPIES = [
    (CLAUDE, CLAUDE_FOUNDATION),
    (CURSOR, CURSOR_USER_RULES),
    (CODEX, CODEX_AGENTS),
]


def claude_handler(event: str) -> dict[str, Any]:
    return {
        "type": "command",
        "command": "orqlet",
        "args": ["hook", event, "--client", CLAUDE],
        "timeout": 5,
    }


# (client, shared file, entry name) to (event name, matcher or None, handler), from AC-4.
HOOK_ENTRIES: dict[tuple[str, str, str], tuple[str, str | None, dict[str, Any]]] = {
    (CLAUDE, CLAUDE_SETTINGS, SESSION_START): (
        "SessionStart",
        None,
        claude_handler("session-start"),
    ),
    (CLAUDE, CLAUDE_SETTINGS, POST_EDIT): (
        "PostToolUse",
        "Write|Edit",
        claude_handler("post-edit"),
    ),
    (CURSOR, CURSOR_HOOKS, SESSION_START): (
        "sessionStart",
        None,
        {"command": "orqlet hook session-start --client cursor", "timeout": 5},
    ),
    (CODEX, CODEX_HOOKS, SESSION_START): (
        "SessionStart",
        None,
        {"type": "command", "command": "orqlet hook session-start --client codex", "timeout": 5},
    ),
}
HOOK_IDS = [f"{client}:{entry}" for client, _, entry in HOOK_ENTRIES]
SKILL_OR_AGENT = re.compile(r"^(?:(?:claude|agents)/skills/|(?:claude|cursor|codex)/agents/)")
ABSOLUTE_PATH = re.compile(
    r"(?:^|[\s\"'`(=<\[])(?:/(?:Users|home|root|tmp|private|var|opt|usr|etc)/|[A-Za-z]:\\|~/)"
)
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
# What a project request with the sample registry and an integration declaration carries.
RESOURCE_TEXTS = (
    "Resource: ",
    "orqlet-tool-",
    str(API_GUIDELINES["url"]),
    str(PYTEST_DOCS["url"]),
    "docs.example.com",
    "docs.pytest.org",
)
CONVENTIONS_MARKER = "orqlet:begin conventions"
INTEGRATION_TEXTS = ("mcpServers", "mcp_servers", "orqlet-docs")


def user_request() -> RenderRequest:
    return build_user_render_request(PackagedWorkflow())


@functools.cache
def user_result(client: str) -> RenderResult:
    return ADAPTERS[client].render(user_request())


def key(file: RenderedFile) -> str:
    return str(file.path) if file.entry is None else f"{file.path}--{file.entry}"


def user_file(client: str, wanted: str) -> RenderedFile:
    found = [file for file in user_result(client).files if key(file) == wanted]
    assert len(found) == 1, f"{client}: {wanted} is rendered exactly once"
    return found[0]


@functools.cache
def project_files() -> dict[str, bytes]:
    """Every project file of the three clients, by path, from the packaged request."""
    files: dict[str, bytes] = {}
    for adapter in ADAPTERS.values():
        for file in adapter.render(packaged_request()).files:
            files.setdefault(str(file.path), file.content)
    return files


def precedence_sentence() -> str:
    return compose_foundation(PackagedWorkflow()).split("\n\n", 1)[0]


def entry_object(client: str, path: str, entry: str) -> Any:
    return json.loads(user_file(client, f"{path}--{entry}").content)


def walk(value: Any) -> Iterator[tuple[str | None, Any]]:
    """Every (key, value) pair of a JSON value, depth first; a list item has the key None."""
    if isinstance(value, dict):
        for name, item in value.items():
            yield name, item
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield None, item
            yield from walk(item)


def words(value: Any) -> list[str]:
    """Every key and every string value of a JSON value."""
    found = []
    for name, item in walk(value):
        if name is not None:
            found.append(name)
        if isinstance(item, str):
            found.append(item)
    return found


# --- AC-2: the files of each client, the shared bytes, no absolute path ---------------------------


@pytest.mark.parametrize("client", CLIENTS)
def test_ac2_each_client_renders_exactly_its_user_files(client: str) -> None:
    """AC-2. expected_behavior_source: AC-2 (Claude Code: `claude/skills/...`,
    `claude/agents/<role>.md`, `claude/rules/orqlet-foundation.md` and entries in
    `claude/settings.json`; Cursor: `agents/skills/...` with the sidecars,
    `cursor/agents/<role>.md`, an entry in `cursor/hooks.json` and `data/cursor-user-rules.md`; Codex: `agents/skills/...` with
    the sidecars, `codex/agents/<role>.toml`, the managed block of `codex/AGENTS.md` and an entry
    in `codex/hooks.json`); BC-4; ADR-002 decisions 1 and 2; component.md section 3 ("Files and
    data written"); the plan's golden list (the entry names)."""
    keys = sorted(key(file) for file in user_result(client).files)

    assert keys == sorted(EXPECTED_KEYS[client])


@pytest.mark.parametrize("client", CLIENTS)
def test_ac2_every_user_skill_and_agent_file_has_the_bytes_of_the_project_file(
    client: str,
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("Every user-scope skill and agent file has the bytes
    of the same project file"); component.md section 3 ("The files are those the project adapters
    already render"); ADR-002 decision 2. The project file is the one at the same path with its
    leading dot, rendered from the request with no registry, conventions or model policy."""
    project = project_files()
    shared = [file for file in user_result(client).files if SKILL_OR_AGENT.match(str(file.path))]

    assert shared
    for file in shared:
        assert file.content == project[f".{file.path}"], str(file.path)


@pytest.mark.parametrize("client", CLIENTS)
def test_ac2_no_user_file_holds_an_absolute_path(client: str, temporary_home: Path) -> None:
    """AC-2. expected_behavior_source: AC-2 ("no rendered file contains an absolute path"); BC-4
    ("No absolute path appears in a rendered file"); ORQLET-DET-001; K-8. The home folder of the
    test is the one the autouse fixture of tests/conftest.py sets."""
    for file in user_result(client).files:
        text = file.content.decode("utf-8")
        assert str(temporary_home) not in text, key(file)
        assert str(temporary_home.resolve()) not in text, key(file)
        assert ABSOLUTE_PATH.search(text) is None, key(file)


@pytest.mark.parametrize("client", CLIENTS)
def test_ac2_rendering_the_user_scope_twice_gives_identical_bytes(client: str) -> None:
    """AC-2. expected_behavior_source: ORQLET-DET-001 ("Generated output is deterministic"),
    cited by AC-2."""
    adapter = ADAPTERS[client]

    assert adapter.render(user_request()) == adapter.render(user_request())


# --- AC-3: one shared agents/skills render for Cursor and Codex -----------------------------------


def agents_skills(client: str) -> dict[str, bytes]:
    return {
        str(file.path): file.content
        for file in user_result(client).files
        if str(file.path).startswith("agents/skills/")
    }


def test_ac3_cursor_and_codex_render_byte_identical_agents_skills() -> None:
    """AC-3. expected_behavior_source: AC-3 ("The Cursor and Codex user renders of
    `agents/skills/...` are byte-identical, including the sidecars"); BC-27; ADR-002 decision 2
    ("both adapters render this folder through the shared skills helper ... with the sidecar on,
    so the two renders are byte-identical")."""
    cursor = agents_skills(CURSOR)

    assert cursor
    assert cursor == agents_skills(CODEX)


@pytest.mark.parametrize("client", [CURSOR, CODEX])
def test_ac3_every_user_sidecar_keeps_implicit_invocation_off(client: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("the sidecars with `allow_implicit_invocation:
    false`"); Q-34 (workflow skills stay person-started for Codex); BC-27. The key nesting is that
    of the existing project sidecar (adapters/render/skills.py `codex_sidecar`)."""
    for path in SIDECARS:
        sidecar = yaml.safe_load(user_file(client, path).content)
        assert sidecar["policy"]["allow_implicit_invocation"] is False, path


# --- AC-4: the hook entries -----------------------------------------------------------------------


@pytest.mark.parametrize("client", CLIENTS)
def test_ac4_each_client_renders_only_the_cited_hook_entries_as_entry_objects(
    client: str,
) -> None:
    """AC-4. expected_behavior_source: AC-4 (claude-code SessionStart and PostToolUse; cursor
    sessionStart; codex SessionStart); K-12 (a registration only where the plan cites it);
    ADR-004 decisions 1 and 3; ADR-002 decision 3 ("renders its hook entries under
    `RenderScope.user` as entry objects, never as whole files")."""
    entries = [file for file in user_result(client).files if file.entry is not None]
    expected = sorted(f"{path}--{entry}" for owner, path, entry in HOOK_ENTRIES if owner == client)

    assert sorted(key(file) for file in entries) == expected
    assert {file.owner for file in entries} == {OwnerMode.SHARED_ENTRY}


@pytest.mark.parametrize(("client", "path", "entry"), list(HOOK_ENTRIES), ids=HOOK_IDS)
def test_ac4_an_entry_is_the_canonical_json_of_one_object(
    client: str, path: str, entry: str
) -> None:
    """AC-4. expected_behavior_source: plan P-7 file_operations (hooks.py: "Canonical bytes of a
    hook entry with its fixed command"); ADR-002 decision 3 (an entry is compared by its
    canonical-JSON hash); ORQLET-DET-001."""
    content = user_file(client, f"{path}--{entry}").content
    value = json.loads(content)

    assert isinstance(value, dict)
    assert content == canonical_json(value)


@pytest.mark.parametrize(("client", "path", "entry"), list(HOOK_ENTRIES), ids=HOOK_IDS)
def test_ac4_an_entry_holds_exactly_the_fixed_handler(client: str, path: str, entry: str) -> None:
    """AC-4. expected_behavior_source: AC-4 (each handler written out); K-8 (the bare `orqlet`);
    K-12 (Claude Code's exec form "runs when `args` is present", `timeout` in seconds; Cursor's
    and Codex's command schemas); ADR-004 decision 7 ("the fixed command `orqlet hook <event>
    --client <id>`, with no value taken from a payload or a project"); Q-45."""
    _, _, handler = HOOK_ENTRIES[(client, path, entry)]
    value = entry_object(client, path, entry)

    handlers = [item for _, item in walk(value) if isinstance(item, dict) and "command" in item]

    assert handlers == [handler]


@pytest.mark.parametrize(("client", "path", "entry"), list(HOOK_ENTRIES), ids=HOOK_IDS)
def test_ac4_an_entry_names_its_event_and_the_post_edit_matcher(
    client: str, path: str, entry: str
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("claude-code SessionStart and PostToolUse with
    matcher `Write|Edit`", "cursor sessionStart", "codex SessionStart"); K-12 (Claude Code's
    Write input `tool_input.file_path`); ADR-004 decision 1 (post-edit on the client's post-tool
    event for file-edit tools)."""
    event, matcher, _ = HOOK_ENTRIES[(client, path, entry)]
    value = entry_object(client, path, entry)

    assert event in words(value)
    if matcher is not None:
        assert [item for name, item in walk(value) if name == "matcher"] == [matcher]


def test_ac4_the_cursor_entry_belongs_to_a_version_1_file() -> None:
    """AC-4. expected_behavior_source: AC-4 ("cursor sessionStart ... in a version 1 file"); K-12
    (Cursor's hooks page). Where the entry carries the version is not pinned beyond a `version`
    key with the value 1."""
    value = entry_object(CURSOR, CURSOR_HOOKS, SESSION_START)

    assert ("version", 1) in [(name, item) for name, item in walk(value) if name == "version"]


@pytest.mark.parametrize(("client", "path", "entry"), list(HOOK_ENTRIES), ids=HOOK_IDS)
def test_ac4_an_entry_runs_the_bare_orqlet_and_holds_no_path(
    client: str, path: str, entry: str
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("Every entry runs the bare `orqlet`, holds no
    absolute path"); K-8 ("Hook entries call the bare `orqlet` executable, never an absolute
    path"); ADR-004 decision 7; ORQLET-DET-001."""
    _, _, handler = HOOK_ENTRIES[(client, path, entry)]
    value = entry_object(client, path, entry)

    assert str(handler["command"]).split(" ")[0] == "orqlet"
    for word in words(value):
        assert "/" not in word, word
        assert "\\" not in word, word
        assert not word.startswith("~"), word


@pytest.mark.parametrize(("client", "path", "entry"), list(HOOK_ENTRIES), ids=HOOK_IDS)
def test_ac4_no_entry_is_pre_tool_fail_closed_or_blocking(
    client: str, path: str, entry: str
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("none is a pre-tool hook, a fail-closed entry or a
    blocking entry"); ADR-004 decision 2 ("No `PreToolUse` or `preToolUse` hook, and no blocking,
    `failClosed` or `onFailure: block` option")."""
    value = entry_object(client, path, entry)

    for word in words(value):
        folded = re.sub(r"[-_\s]", "", word.lower())
        assert "pretool" not in folded, word
        assert "failclosed" not in folded, word
        assert "onfailure" not in folded, word
        assert "block" not in folded, word


# --- AC-5: the registrations left out are capability limits ---------------------------------------


def post_edit_limits(client: str) -> list[str]:
    return [
        limit.message.lower()
        for limit in user_result(client).limits
        if "post-edit" in limit.message.lower()
    ]


@pytest.mark.parametrize(
    ("client", "reason"),
    [(CURSOR, "context"), (CODEX, "patch")],
    ids=[CURSOR, CODEX],
)
def test_ac5_a_left_out_post_edit_registration_is_a_capability_limit(
    client: str, reason: str
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("Cursor post-edit (no cited edited-path field on an
    event that can return context) and Codex post-edit (the path exists only inside the patch
    text)"); BC-43; K-12 (Cursor's afterFileEdit "has `file_path` but no output field"; Codex's
    "apply_patch input is the patch text"); ADR-004 decision 1."""
    messages = post_edit_limits(client)

    assert len(messages) == 1, messages
    assert reason in messages[0]


def test_ac5_claude_code_leaves_no_post_edit_registration_out() -> None:
    """AC-5. expected_behavior_source: AC-5 (only the Cursor and Codex post-edit registrations are
    left out); K-12 (Claude Code's PostToolUse `additionalContext` is cited); ADR-004 decision 1."""
    assert post_edit_limits(CLAUDE) == []


# --- AC-6: the foundation copies and the user golden family ---------------------------------------


@pytest.mark.parametrize(("client", "path"), FOUNDATION_COPIES, ids=list(CLIENTS))
def test_ac6_each_copy_holds_the_foundation_and_starts_with_the_precedence_sentence(
    client: str, path: str
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("`claude/rules/orqlet-foundation.md`, the managed
    block of `codex/AGENTS.md` and `data/cursor-user-rules.md` each hold the composed foundation
    and start with the precedence sentence"); ADR-005 decisions 3 and 4 ("Every global copy
    starts with one sentence"); BC-20; R-5."""
    file = user_file(client, path)
    text = file.content.decode("utf-8")
    if path == CODEX_AGENTS:
        assert file.owner is OwnerMode.SHARED_BLOCK
        assert file.block is not None
        first, text = text.split("\n", 1)
        assert first == file.block[0]

    assert text.startswith(precedence_sentence())
    assert compose_foundation(PackagedWorkflow()).rstrip("\n") in text


@pytest.mark.golden
@pytest.mark.parametrize("client", CLIENTS)
def test_ac6_the_user_family_matches_its_golden_files(
    client: str, golden: Callable[[str, bytes], None]
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("the golden files of the user family match"); the
    plan's golden list (`tests/golden/<client>/user-2026-11/...`, seven files); BC-4 (the files
    match golden files); ORQLET-DET-001. Skill and agent files are not in the family: AC-2 pins
    them to the project golden bytes."""
    files = {
        key(file): file.content
        for file in user_result(client).files
        if not SKILL_OR_AGENT.match(str(file.path))
    }

    assert set(files) == GOLDEN_KEYS[client]
    for name, content in sorted(files.items()):
        golden(f"{client}/{USER_FAMILY}/{name}", content)


# --- AC-7: no model, convention, integration or resource in a user file ---------------------------


def model_fields(file: RenderedFile) -> dict[str, Any]:
    """The model and effort fields a file declares: front matter, TOML, YAML or JSON keys."""
    text = file.content.decode("utf-8")
    path = str(file.path)
    names = {"model", "effort", "model_reasoning_effort", "reasoning_effort"}
    if path.endswith(".toml"):
        return {name: value for name, value in tomllib.loads(text).items() if name in names}
    if path.endswith(".yaml"):
        return {name: value for name, value in walk(yaml.safe_load(text)) if name in names}
    if file.entry is not None:
        return {name: value for name, value in walk(json.loads(text)) if name in names}
    match = FRONT_MATTER.match(text)
    if match is None:
        return {}
    head = yaml.safe_load(match.group(1)) or {}
    return {name: value for name, value in head.items() if name in names}


@pytest.mark.parametrize("client", CLIENTS)
def test_ac7_no_user_file_has_a_model_or_effort_field(client: str) -> None:
    """AC-7. expected_behavior_source: AC-7 ("No user-scope file has a model name, a model or
    effort field"); BC-26; ADR-002 decision 7; ORQLET-MODEL-001. Read with AC-2 (the bytes of the
    project file): `model: inherit` names no model and is the only model value allowed."""
    for file in user_result(client).files:
        fields = model_fields(file)
        assert set(fields) <= {"model"}, (key(file), fields)
        assert fields.get("model", "inherit") == "inherit", (key(file), fields)


@pytest.mark.parametrize("client", CLIENTS)
def test_ac7_no_user_file_has_a_convention_an_integration_or_a_resource_link(client: str) -> None:
    """AC-7. expected_behavior_source: AC-7 ("a convention, an integration or a resource link,
    even when the project request had them"); BC-26; ADR-002 decision 7. The texts are what the
    sample registry (tests/support/render.py), the conventions block and an MCP declaration put
    into project files; no user path is an MCP or a scoped-rule file."""
    for file in user_result(client).files:
        path = str(file.path)
        text = file.content.decode("utf-8")
        assert "mcp" not in path.lower(), path
        assert not re.search(r"/rules/orqlet-(?!foundation\.md$)", path), path
        assert CONVENTIONS_MARKER not in text, key(file)
        for forbidden in (*RESOURCE_TEXTS, *INTEGRATION_TEXTS):
            assert forbidden not in text, (key(file), forbidden)


# --- AC-8: the project renders do not move --------------------------------------------------------


def test_ac8_a_project_request_keeps_the_project_scope() -> None:
    """AC-8. expected_behavior_source: AC-8 (the project renders stay as they are); A-25;
    component.md section 4 (`RenderScope` of `project` or `user`). A request that names no scope,
    as every existing caller builds it, is a project request."""
    assert packaged_request().scope is RenderScope.PROJECT
    assert RenderRequest(workflow_version="1", baseline_body="b\n").scope is RenderScope.PROJECT


@pytest.mark.parametrize("client", CLIENTS)
def test_ac8_project_renders_stay_byte_identical_to_the_existing_golden_files(client: str) -> None:
    """AC-8. expected_behavior_source: AC-8 ("Regression: the project renders of the three adapters
    stay byte-identical to the existing golden files"); BC-18 ("The existing three adapters'
    golden output is unchanged"); A-25. The family `docs-2026-10` is read from disk, so
    `--update-golden` on this file cannot rewrite it; no file is added or dropped."""
    family = GOLDEN_ROOT / client / PROJECT_FAMILY
    expected = {
        path.relative_to(family).as_posix(): path.read_bytes()
        for path in family.rglob("*")
        if path.is_file()
    }

    files = ADAPTERS[client].render(packaged_request()).files
    rendered = {str(file.path): file.content for file in files}

    assert rendered == expected
