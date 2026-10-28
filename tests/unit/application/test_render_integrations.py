"""The declaration reaches the rendering: the adapters, `compose`, `upgrade`, `init` and `explain`
(task mcp-or-plugins, phase P-5; the part that needs no real file system).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-00N-*.md`
under docs/design/mcp-or-plugins/design/, EC-n are the expected changes of the manifest.yaml next
to them, and AC-3, AC-4, AC-5, AC-6 and AC-10 are criteria of phase P-5 in
docs/design/mcp-or-plugins/plan.yaml. AC-1 and AC-2 (the renderer) are in
tests/unit/render/test_mcp_render.py; AC-7 to AC-9 (a real tree, the sentinel, the faults) are in
tests/integration/test_upgrade_mcp_files.py and tests/fault/test_mcp_file_apply.py.

These tests were written first, by the Tester of phase P-5, before the implementation existed. The
project is the in-memory fake of tests/fakes with the services of tests/support/init_env.py
(ORQLET-TEST-001). The declaration is the text of the valid fixture with its one server changed to
the one pair that the closed table enables (id `atlassian`, address https://mcp.atlassian.com/v2/mcp,
client `claude-code`), written as JSON, which the strict loader reads as YAML.

What the design fixes and the tests use: `RenderRequest.integrations` is an optional field, default
`None`, that holds the `Integrations` object (EC-10); the Claude Code adapter adds one `.mcp.json`,
owner `seeded` and no file class, when `registered_for("claude-code")` is not empty, and the other
two adapters ignore the field (ADR-003 decision 4); `compose` takes the keyword parameter
`integrations`, after `build_render_request`, with `dataclasses.replace` (EC-9); `upgrade` reads
`.orqlet/integrations.yaml`, refuses with the loader's findings and writes nothing when it is
invalid, passes it to `compose` otherwise (ADR-003 decision 3); `init` composes without it and
`explain` is not changed (ADR-003 decision 3).

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- the `inputs` of the generated `.mcp.json`, and whether the Claude Code adapter reports a
  capability limit for it;
- whether `upgrade` passes the information findings of a valid declaration on to its result;
- the order of the refusals of `upgrade` (a pending journal, a downgrade, an invalid registry and an
  invalid declaration, when more than one holds);
- what `init` does with an invalid declaration that is already in the repository (the design says
  only that it composes without one);
- whether a refused `upgrade` for a link or a folder at `.mcp.json` is raised as `InitRefused` or
  returned as `refused`: both are accepted at the level of `upgrade`; `plan_changes` itself raises
  `InitRefused` with the code ORQ-E114 (ADR-002 decision 8) and the command exits 3 (the real
  command is tested in tests/integration/test_upgrade_mcp_files.py);
- whether an `upgrade` with `--check` or `--dry-run` refuses an invalid declaration (the tests
  below require it, from "before any plan is built" of ADR-003 decision 3; it is listed as a
  question in the report of the Tester);
- the wording of any message.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib
import inspect
import json
from collections.abc import Callable, Sequence
from functools import cache, partial
from pathlib import Path
from typing import Any

import pytest
import yaml
from orqlet.adapters.render.mcp import render_mcp_file

import orqlet.application.usecases.explain as explain_module
import orqlet.application.usecases.init_project as init_module
from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.generated_lock import GeneratedLock, LockedFile
from orqlet.application.contracts.integrations import Integrations
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.instruction_adapter import (
    InstructionAdapter,
    RenderedFile,
    RenderRequest,
    RenderResult,
)
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.explain import explain
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.init_state import InitRefused
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.integrations_source import load_integrations
from orqlet.application.usecases.render_all import Composition, compose, plan_changes, resolve_for
from orqlet.application.usecases.render_request import build_render_request
from orqlet.application.usecases.services import Services
from orqlet.application.usecases.standards_for import StandardsQuery
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.python_api import extract_module_api
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED, ChangedWorkflow
from tests.support.init_env import Env, tree
from tests.support.render import packaged_request
from tests.support.trees import repo

pytestmark = pytest.mark.unit

ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"  # the one address of the closed table
OTHER_ADDRESS = "https://docs.example.com/mcp"  # a good address for the contract, not on the table
EDITABLE = "client-enforced-editable"
DECLARATION = ".orqlet/integrations.yaml"
MCP = ".mcp.json"
CURSOR_MCP = ".cursor/mcp.json"
CODEX_MCP = ".codex/config.toml"
LOCK = ".orqlet/generated.lock.yaml"
PROFILE = ".orqlet/project-profile.yaml"
MCP_PATHS = (MCP, CURSOR_MCP, CODEX_MCP)
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
LOADER = StrictYamlLoader()
YES = InitOptions(assume_yes=True)
GO = UpgradeOptions(assume_yes=True)
QUERY = StandardsQuery(phase="design")
NEXT = ChangedWorkflow(PINNED, version="0.2.0")
EMPTY_REGISTRY = Resources(schema_id="orqlet.resources/v1")
# The text of AC-1 of the renderer for the one server `atlassian`, written out by hand.
ATLASSIAN_TEXT = (
    "{\n"
    '  "mcpServers": {\n'
    '    "orqlet-atlassian": {\n'
    '      "type": "http",\n'
    '      "url": "https://mcp.atlassian.com/v2/mcp"\n'
    "    }\n"
    "  }\n"
    "}\n"
)

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0JxQz4M", "Ka8Ty2Vb"))


# --- the declaration ------------------------------------------------------------------------------


def fixture() -> dict[str, Any]:
    """The valid fixture as plain data, which a test may change freely."""
    loaded = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return copy.deepcopy(loaded)


def server(
    server_id: str = "atlassian",
    *,
    url: str = ATLASSIAN,
    registered: Sequence[str] = ("claude-code",),
    **changes: Any,
) -> dict[str, Any]:
    """A server that satisfies every rule of the contract, taken from the fixture's first one."""
    base = copy.deepcopy(fixture()["servers"][0])
    base.update(
        id=server_id,
        identity={"kind": "remote", "url": url},
        registration={"name": f"orqlet-{server_id}", "mode": "read-only", "enforced_by": EDITABLE},
        per_client={name: {"register": True, "enforced_by": EDITABLE} for name in registered},
        clients=list(registered),
    )
    return {**base, **changes}


def declaration(*servers: dict[str, Any]) -> dict[str, Any]:
    """The fixture's document with these servers, and a role that names each of them."""
    data = fixture()
    data["servers"] = [copy.deepcopy(item) for item in servers]
    data["roles"] = {"architecture-reviewer": {"servers": [item["id"] for item in servers]}}
    return data


def document(data: dict[str, Any]) -> bytes:
    """A declaration as JSON text, one key per line, which the strict loader reads as YAML."""
    return json.dumps(data, indent=2).encode()


def integrations_of(*servers: dict[str, Any]) -> Integrations:
    return Integrations.model_validate(declaration(*servers))


def valid_bytes() -> bytes:
    """The one declaration that the loader accepts: Atlassian OAuth for Claude Code."""
    return document(declaration(server()))


def unregistered() -> dict[str, Any]:
    """A server at the table's address that the file `.mcp.json` must not hold: not registered."""
    return server(
        "idle",
        per_client={"claude-code": {"register": False, "enforced_by": EDITABLE}},
        clients=["claude-code"],
    )


# --- helpers --------------------------------------------------------------------------------------


def initialised(options: InitOptions = YES) -> Env:
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    result = init_project(env.services(), options)
    assert result.status == "applied"
    return env


def path_of(name: str) -> CanonicalPath:
    return CanonicalPath.parse(name)


def read(env: Env, name: str) -> bytes:
    return env.project.read_bytes(path_of(name))


def declare(env: Env, content: bytes) -> None:
    env.project.write_atomic(path_of(DECLARATION), content)


def lock_of(env: Env) -> GeneratedLock:
    return load_contract(LOADER, GeneratedLock, read(env, LOCK), source=LOCK)


def lock_entry(env: Env, name: str) -> LockedFile | None:
    return next((entry for entry in lock_of(env).files if entry.path == name), None)


def not_limits(findings: Sequence[Finding]) -> list[Finding]:
    """The findings that are not capability limits (ORQ-L...): the adapters own those."""
    return [finding for finding in findings if not finding.code.startswith("ORQ-L")]


def codes(findings: Sequence[Finding]) -> set[str]:
    return {finding.code for finding in findings}


def shown(findings: Sequence[Finding]) -> str:
    return "\n".join(
        f"{finding.code}\n{finding.message}\n{finding.path}\n{finding!r}" for finding in findings
    )


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters of it in a row (any case)."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


@cache
def base_request() -> RenderRequest:
    """The request of the packaged workflow, built once: the request is immutable."""
    return packaged_request()


def request_with(declared: Integrations | None) -> RenderRequest:
    return dataclasses.replace(base_request(), integrations=declared)


def sorted_files(files: Sequence[RenderedFile]) -> list[RenderedFile]:
    return sorted(files, key=lambda f: (str(f.path), f.block or ("", "")))


def composer(
    env: Env, *, services: Services | None = None, clients: Sequence[str] | None = None
) -> partial[Composition]:
    """`compose` for the installed project, with every argument but `integrations`."""
    services = services or env.services()
    inst = load_installation(services)
    return partial(
        compose,
        services,
        inst.profile,
        resolve_for(services, inst.profile),
        EMPTY_REGISTRY,
        clients=inst.profile.clients.enabled if clients is None else clients,
        prompts_dir=".prompts",
        pr_targets=inst.profile.repository.pull_requests.template.targets,
        profile_bytes=read(env, PROFILE),
        resources_bytes=b"schema: orqlet.resources/v1\nresources: []\n",
    )


ADAPTERS: dict[str, InstructionAdapter] = {
    "claude-code": ClaudeCodeAdapter(),
    "codex": CodexAdapter(),
    "cursor": CursorAdapter(),
}

# Declarations for the adapters, each valid for the contract. The loader would refuse the last two
# (the table enables Claude Code only), which is not the adapters' business.
DECLARATIONS: dict[str, Integrations | None] = {
    "none-at-all": None,
    "no-server": integrations_of(),
    "server-not-registered": integrations_of(unregistered()),
    "registered-for-other-clients-only": integrations_of(
        server("docs", url=OTHER_ADDRESS, registered=("codex", "cursor"))
    ),
    "registered-for-claude-code": integrations_of(server()),
    "registered-for-all-three": integrations_of(
        server(registered=("claude-code", "codex", "cursor"))
    ),
}
NO_MCP_FILE_FOR_CLAUDE_CODE = [
    "none-at-all",
    "no-server",
    "server-not-registered",
    "registered-for-other-clients-only",
]


# --- EC-10: the field of the request --------------------------------------------------------------


def test_ac3_the_request_has_an_optional_field_integrations_that_defaults_to_none() -> None:
    """AC-3, AC-4. expected_behavior_source: EC-10 (`RenderRequest` "gains one optional field,
    integrations, typed Integrations | None with the default None") and ADR-003 decision 4
    ("The field holds the contract object, `Integrations`")."""
    fields = {field.name: field for field in dataclasses.fields(RenderRequest)}

    assert "integrations" in fields
    assert fields["integrations"].default is None
    assert RenderRequest(workflow_version="1", baseline_body="b").integrations is None
    declared = integrations_of(server())
    assert dataclasses.replace(packaged_request(), integrations=declared).integrations is declared


def test_ac4_build_render_request_is_unchanged_and_leaves_the_field_empty() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 4 ("`compose` sets it with
    `dataclasses.replace(request, integrations=integrations)` after `build_render_request`, so
    `render_request.py` and its signature do not change") and AC-4 ("render_request.py and
    build_render_request are unchanged")."""
    parameters = inspect.signature(build_render_request).parameters

    assert list(parameters) == [
        "workflow",
        "loader",
        "rules",
        "resources",
        "conventions",
        "client_version",
        "available_commands",
    ]
    assert packaged_request().integrations is None


# --- AC-3: the three adapters ---------------------------------------------------------------------


@pytest.mark.parametrize("name", ["registered-for-claude-code", "registered-for-all-three"])
def test_ac3_claude_code_writes_the_mcp_file_for_a_registered_server_and_nothing_else_changes(
    name: str,
) -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 4 ("The Claude Code adapter calls
    `render_mcp_file(servers, client)` with `Integrations.registered_for(client)`") and decision 5
    (".mcp.json is written as a complete text that holds only the generated entries, with owner
    `seeded` and no file class") and EC-13 (".mcp.json, owner seeded and no file class"): one more
    file, with the text of the renderer, and every other file as it was."""
    declared = DECLARATIONS[name]
    assert declared is not None
    adapter = ADAPTERS["claude-code"]
    without = adapter.render(request_with(None))

    result = adapter.render(request_with(declared))

    written = [f for f in result.files if str(f.path) == MCP]
    assert len(written) == 1
    (mcp,) = written
    assert mcp.owner is OwnerMode.SEEDED
    assert mcp.file_class is None
    assert mcp.block is None
    assert mcp.entry is None
    assert (
        mcp.content
        == render_mcp_file(declared.registered_for("claude-code"), "claude-code").encode()
    )
    assert mcp.content == ATLASSIAN_TEXT.encode("utf-8")
    others = [f for f in result.files if str(f.path) != MCP]
    assert sorted_files(others) == sorted_files(without.files)
    assert len(result.files) == len(without.files) + 1


@pytest.mark.parametrize("name", NO_MCP_FILE_FOR_CLAUDE_CODE)
def test_ac3_claude_code_writes_no_mcp_file_without_a_server_registered_for_it(name: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("writes nothing otherwise") and ADR-002 decision 5
    ("When no server is registered for a client, no file is written for it, not an empty one"):
    no declaration, an empty one, a server that is not registered, and a server that is
    registered for other clients only, each give the file set of a request without the field."""
    adapter = ADAPTERS["claude-code"]
    base = adapter.render(request_with(None))

    result = adapter.render(request_with(DECLARATIONS[name]))

    assert MCP not in {str(f.path) for f in result.files}
    assert result == base


def test_ac3_the_file_of_claude_code_holds_only_the_servers_that_are_registered_for_it() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 ("`Integrations.registered_for(client)`
    returns the servers whose `per_client[client].register` is true, in declaration order") and
    ADR-003 decision 4: of three servers, the second is not registered and is not in the file,
    and the other two keep the order of the declaration."""
    declared = integrations_of(server("zeta"), unregistered(), server("alpha"))

    result = ADAPTERS["claude-code"].render(request_with(declared))

    (mcp,) = [f for f in result.files if str(f.path) == MCP]
    assert list(json.loads(mcp.content)["mcpServers"]) == ["orqlet-zeta", "orqlet-alpha"]
    assert (
        mcp.content
        == render_mcp_file(declared.registered_for("claude-code"), "claude-code").encode()
    )


def test_ac3_the_same_request_gives_the_same_files_of_claude_code() -> None:
    """AC-3. expected_behavior_source: ORQLET-DET-001 and AC-1 ("the same input gives the same
    bytes"), through the adapter: two renders of two requests made from the same data are equal."""
    adapter = ADAPTERS["claude-code"]

    assert adapter.render(request_with(integrations_of(server()))) == adapter.render(
        request_with(integrations_of(server()))
    )


@pytest.mark.parametrize("client", ["codex", "cursor"])
@pytest.mark.parametrize("name", list(DECLARATIONS))
def test_ac3_codex_and_cursor_give_the_same_result_with_and_without_a_declaration(
    client: str, name: str
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("the Codex and Cursor adapters produce the same bytes
    with and without a declaration") and ADR-003 decision 4 ("the Codex and Cursor adapters ignore
    the field in this change"), including a declaration that registers them: the whole result, the
    files and the limits, is the one of a request without the field."""
    adapter = ADAPTERS[client]

    assert adapter.render(request_with(DECLARATIONS[name])) == adapter.render(request_with(None))


@pytest.mark.parametrize("client", ["claude-code", "codex", "cursor"])
@pytest.mark.parametrize("name", list(DECLARATIONS))
def test_ac3_no_adapter_writes_the_mcp_file_of_cursor_or_of_codex(client: str, name: str) -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 1 ("This change builds and generates one
    entry kind: Atlassian OAuth for Claude Code") and EC-13 (".cursor/mcp.json and
    .codex/config.toml are specified and built by the release that enables them")."""
    result = ADAPTERS[client].render(request_with(DECLARATIONS[name]))

    paths = {str(f.path) for f in result.files}
    assert CURSOR_MCP not in paths
    assert CODEX_MCP not in paths
    if client != "claude-code":
        assert MCP not in paths


def test_ac3_the_file_sets_of_the_three_adapters_without_a_declaration_are_unchanged() -> None:
    """AC-3. expected_behavior_source: AC-3 ("the file sets of the three adapters for a request
    without a declaration are unchanged") and ADR-003 consequences ("A project with no declaration
    is unchanged in the files it holds"): none of the three writes an MCP file, and the
    declaration that holds no server adds none either."""
    for client, adapter in ADAPTERS.items():
        for declared in (None, integrations_of()):
            paths = {str(f.path) for f in adapter.render(request_with(declared)).files}
            assert not paths & set(MCP_PATHS), client


# --- AC-4: compose --------------------------------------------------------------------------------


def test_ac4_compose_with_a_declaration_adds_one_seeded_file_and_changes_nothing_else() -> None:
    """AC-4. expected_behavior_source: AC-4 ("compose takes the keyword parameter integrations
    ... and sets the request field") and ADR-003 decision 4 ("`compose` renders only for clients
    that the profile enables"): the composition of an initialised project gains `.mcp.json`, owner
    seeded, no file class, the text of the specification, and its other files and its findings,
    the capability limits of the adapters apart, are those of the composition without a
    declaration."""
    env = initialised()
    compose_here = composer(env)
    without = compose_here(integrations=None)

    with_declaration = compose_here(integrations=integrations_of(server()))

    (mcp,) = [item for item in with_declaration.desired if str(item.path) == MCP]
    assert mcp.owner is OwnerMode.SEEDED
    assert mcp.file_class is None
    assert mcp.block_name is None
    assert mcp.content == ATLASSIAN_TEXT.encode("utf-8")
    assert [item for item in with_declaration.desired if str(item.path) != MCP] == without.desired
    assert not_limits(with_declaration.findings) == not_limits(without.findings)
    assert with_declaration.resolution == without.resolution


def test_ac4_the_parameter_defaults_to_no_declaration() -> None:
    """AC-4. expected_behavior_source: EC-9 (`integrations: Integrations | None=None`) and
    ADR-003 decision 2 ("It is optional. When it is absent, `upgrade` writes no MCP file"): a call
    that does not pass the parameter and a call that passes `None` give the same composition,
    without an MCP file."""
    env = initialised()
    compose_here = composer(env)

    omitted = compose_here()
    explicit = compose_here(integrations=None)

    assert omitted.desired == explicit.desired
    assert omitted.findings == explicit.findings
    assert MCP not in {str(item.path) for item in omitted.desired}


def test_ac4_compose_does_not_read_the_declaration_from_the_project_itself() -> None:
    """AC-4. expected_behavior_source: ADR-003 rejected alternatives ("Let `compose` call the
    loader itself. Every other input of `compose` is passed in, and the registry set the
    pattern"): a valid declaration in the project and no parameter give no MCP file."""
    env = initialised()
    declare(env, valid_bytes())

    composition = composer(env)()

    assert MCP not in {str(item.path) for item in composition.desired}


@pytest.mark.parametrize("clients", [("codex", "cursor"), ("codex",), ("cursor",), ()])
def test_ac4_compose_renders_only_for_the_clients_that_the_profile_enables(
    clients: tuple[str, ...],
) -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 4 ("`compose` renders only for clients that
    the profile enables") and EC-13 (".mcp.json ... written by the Claude Code adapter only when ...
    the profile enables it"): a declaration that registers Claude Code gives no `.mcp.json` when
    `claude-code` is not among the clients."""
    env = initialised()

    composition = composer(env, clients=clients)(integrations=integrations_of(server()))

    assert MCP not in {str(item.path) for item in composition.desired}


class RecordingAdapter:
    """An adapter that writes no file and keeps the request that it was given."""

    client_id = "recording"

    def __init__(self) -> None:
        self.requests: list[RenderRequest] = []

    def render(self, request: RenderRequest) -> RenderResult:
        self.requests.append(request)
        return RenderResult(files=())


def test_ac4_compose_sets_the_field_of_the_request_and_changes_no_other_field() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 4 ("`compose` sets it with
    `dataclasses.replace(request, integrations=integrations)` after `build_render_request`") and
    AC-4: the adapter gets the declaration itself (the same object) in the field, a request without
    a declaration holds `None`, and the two requests are equal in every other field."""
    env = initialised()
    spy = RecordingAdapter()
    services = dataclasses.replace(env.services(), adapters={spy.client_id: spy})
    declared = integrations_of(server())
    compose_here = composer(env, services=services, clients=(spy.client_id,))

    compose_here(integrations=None)
    compose_here(integrations=declared)

    without, with_declaration = spy.requests
    assert without.integrations is None
    assert with_declaration.integrations is declared
    assert dataclasses.replace(with_declaration, integrations=None) == without


# --- AC-5: upgrade --------------------------------------------------------------------------------


def test_ac5_an_upgrade_without_a_declaration_writes_no_mcp_file() -> None:
    """AC-5. expected_behavior_source: AC-5 ("upgrade with no declaration writes no MCP file") and
    ADR-003 decision 2 ("When it is absent, `upgrade` writes no MCP file. This repository gets none
    from this change")."""
    env = initialised()
    before = tree(env.project)

    result = upgrade(env.services(), GO)

    assert result.status == "up-to-date"
    assert tree(env.project) == before
    assert not set(MCP_PATHS) & set(tree(env.project))
    assert lock_entry(env, MCP) is None


def test_ac5_an_upgrade_with_a_declaration_creates_the_mcp_file_and_records_it_as_seeded() -> None:
    """AC-5. expected_behavior_source: AC-5 ("with a valid declaration it creates .mcp.json with
    the rendered text and records it in the lock with owner seeded") and ADR-003 decision 5
    ("with owner `seeded` and no file class"): the plan creates the file and updates the lock, and
    nothing else, the file holds the text of the specification, and the lock holds its hash."""
    env = initialised()
    declare(env, valid_bytes())

    result = upgrade(env.services(), GO)

    assert result.status == "applied"
    assert result.plan is not None
    assert {(str(w.path), w.kind) for w in result.plan.writes} == {
        (MCP, "create"),
        (LOCK, "update"),
    }
    assert read(env, MCP) == ATLASSIAN_TEXT.encode("utf-8")
    entry = lock_entry(env, MCP)
    assert entry is not None
    assert entry.owner is OwnerMode.SEEDED
    assert entry.file_class is None
    assert entry.seeded_sha256 == sha256_hex(read(env, MCP))
    assert entry.rendered_sha256 is None
    assert not [f for f in result.findings if f.severity is Severity.ERROR]


def test_ac5_the_file_is_up_to_date_after_the_first_upgrade_and_a_check_finds_nothing() -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 5 ("Classification is unchanged, so a
    re-run, `--resume` and `--check` converge") and ORQLET-SAFE-001: a second run and a check
    change nothing and find nothing to write."""
    env = initialised()
    declare(env, valid_bytes())
    upgrade(env.services(), GO)
    settled = tree(env.project)

    again = upgrade(env.services(), GO)
    check = upgrade(env.services(), UpgradeOptions(check=True))

    assert again.status == "up-to-date"
    assert check.status == "up-to-date"
    assert tree(env.project) == settled


def test_ac5_a_declaration_that_registers_no_server_for_claude_code_writes_no_file() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 5 ("When no server is registered for a
    client, no file is written for it") and EC-13: a valid declaration whose one server is not
    registered gives no `.mcp.json`."""
    env = initialised()
    declare(env, document(declaration(unregistered())))

    result = upgrade(env.services(), GO)

    assert result.status == "up-to-date"
    assert MCP not in tree(env.project)


def test_ac5_a_profile_without_claude_code_gets_no_mcp_file() -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 4 ("`compose` renders only for clients that
    the profile enables") and EC-13 ("only when ... the profile enables it"): a project that
    enabled Codex and Cursor only, with a declaration that registers Claude Code, gets no file."""
    env = initialised(InitOptions(assume_yes=True, clients=("codex", "cursor")))
    declare(env, valid_bytes())

    result = upgrade(env.services(), GO)

    assert result.status == "up-to-date"
    assert MCP not in tree(env.project)


def test_ac5_a_file_that_the_declaration_no_longer_wants_is_left_where_it_is() -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 5 (".mcp.json is written as a complete text
    ... with owner `seeded`", "A team that deletes the file does not get it back", "Once nothing is
    wanted for a seeded file, the lock forgets it") and `classify` (a seeded file is never
    deleted): after the declaration is removed the next `upgrade` leaves `.mcp.json` as it is."""
    env = initialised()
    declare(env, valid_bytes())
    upgrade(env.services(), GO)
    env.project.delete(path_of(DECLARATION))

    result = upgrade(env.services(), GO)

    assert result.status in {"applied", "up-to-date"}
    assert read(env, MCP) == ATLASSIAN_TEXT.encode("utf-8")
    assert not [w for w in (result.plan.writes if result.plan else ()) if w.kind == "delete"]


# The declarations that the loader refuses, by the code that it gives (plan P-3: ORQ-E530 the file
# is unreadable, over 256 KiB or refused by the strict loader; ORQ-E531 it fails its contract;
# ORQ-E532 the table does not enable a server, a mode and a client; ORQ-E533 the scan found
# something). Each is made from the valid declaration.
def _duplicated_key() -> bytes:
    text = valid_bytes()
    doubled = text.replace(
        b'"purpose": "documentation search",',
        b'"purpose": "documentation search",\n      "purpose": "again",',
        1,
    )
    assert doubled != text
    return doubled


def _fails_the_contract() -> bytes:
    data = declaration(server())
    data["servers"][0]["registration"]["name"] = "orqlet-another"
    return document(data)


def _not_on_the_table() -> bytes:
    return document(declaration(server(url=OTHER_ADDRESS)))


def _holds_a_token() -> bytes:
    data = declaration(server())
    data["servers"][0]["purpose"] = f"search with {TOKEN}"
    return document(data)


def _over_the_cap() -> bytes:
    return valid_bytes() + b"\n" + b"#" * 256 * 1024 + b"\n"


INVALID_DECLARATIONS: dict[str, tuple[bytes, str]] = {
    "repeated-key": (_duplicated_key(), "ORQ-E530"),
    "over-256-kib": (_over_the_cap(), "ORQ-E530"),
    "fails-its-contract": (_fails_the_contract(), "ORQ-E531"),
    "not-on-the-table": (_not_on_the_table(), "ORQ-E532"),
    "holds-a-token": (_holds_a_token(), "ORQ-E533"),
}


def loader_errors(env: Env) -> list[Finding]:
    declared, findings = load_integrations(env.project, LOADER, DECLARATION)
    assert declared is None
    return [finding for finding in findings if finding.severity is Severity.ERROR]


@pytest.mark.parametrize("name", list(INVALID_DECLARATIONS))
def test_ac5_an_invalid_declaration_refuses_the_upgrade_and_writes_nothing(name: str) -> None:
    """AC-5. expected_behavior_source: AC-5 ("with an invalid declaration it refuses with exit 3
    and writes nothing, including the other generated files") and ADR-003 decision 3 ("the helper
    that reads it appends an error finding and returns a refused result before any plan is built,
    as `_registry` does"): a new release would rewrite many files, none is written, no plan is
    built, no journal is opened, and the result holds the loader's error findings."""
    content, loader_code = INVALID_DECLARATIONS[name]
    env = initialised()
    control = initialised()
    control.workflow = NEXT
    assert upgrade(control.services(), UpgradeOptions(check=True)).status == "available"
    env.workflow = NEXT
    declare(env, content)
    before, before_data = tree(env.project), tree(env.user_data)
    errors = loader_errors(env)
    assert loader_code in codes(errors)

    result = upgrade(env.services(), GO)

    assert result.status == "refused"  # which the command turns into exit 3
    assert result.plan is None
    assert result.change_id is None
    assert {(f.code, f.message) for f in errors} <= {(f.code, f.message) for f in result.findings}
    assert [f for f in result.findings if f.severity is Severity.ERROR]
    assert tree(env.project) == before
    assert tree(env.user_data) == before_data


@pytest.mark.parametrize("options", [UpgradeOptions(check=True), UpgradeOptions(dry_run=True)])
@pytest.mark.parametrize("name", ["fails-its-contract", "not-on-the-table"])
def test_ac5_a_check_and_a_preview_refuse_an_invalid_declaration_too(
    name: str, options: UpgradeOptions
) -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 3 ("the helper ... returns a refused result
    before any plan is built", which the options do not change) and ORQLET-SAFE-001 ("so that a
    half-applied security setting never exists"): `--check` and `--dry-run` do not report an
    upgrade that the real run would refuse."""
    env = initialised()
    env.workflow = NEXT
    declare(env, INVALID_DECLARATIONS[name][0])
    before = tree(env.project)

    result = upgrade(env.services(), options)

    assert result.status == "refused"
    assert result.plan is None
    assert tree(env.project) == before


def test_ac5_the_refusal_of_an_invalid_declaration_shows_no_part_of_a_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 ("Messages never carry a value or a raw
    key") and ORQLET-SEC-003: a declaration with a token in its text is refused and nothing that
    the result or the process printed shows a part of the token."""
    env = initialised()
    declare(env, INVALID_DECLARATIONS["holds-a-token"][0])

    result = upgrade(env.services(), GO)

    streams = capsys.readouterr()
    assert result.status == "refused"
    assert not leaks(shown(result.findings), TOKEN)
    assert not leaks(streams.out, TOKEN)
    assert not leaks(streams.err, TOKEN)


def _make_declaration_a_link(env: Env) -> None:
    env.project.add_symlink(DECLARATION)


def _make_declaration_a_folder(env: Env) -> None:
    env.project.make_dir(path_of(DECLARATION))


@pytest.mark.parametrize("damage", [_make_declaration_a_link, _make_declaration_a_folder])
def test_ac5_a_declaration_that_is_a_link_or_a_folder_is_refused_and_writes_nothing(
    damage: Callable[[Env], None],
) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 8 ("a link, a directory, an unreadable file
    ... is an `unreadable` error": ORQ-E530) and ADR-003 decision 3 (an invalid declaration makes
    `upgrade` refuse): the declaration path is a link in one project and a folder in another."""
    env = initialised()
    env.workflow = NEXT
    damage(env)
    before = tree(env.project)

    result = upgrade(env.services(), GO)

    assert result.status == "refused"
    assert "ORQ-E530" in codes(result.findings)
    assert tree(env.project) == before


# --- AC-9 at the level of the plan ----------------------------------------------------------------


def _make_link(env: Env) -> None:
    env.project.add_symlink(MCP)


def _make_folder(env: Env) -> None:
    env.project.make_dir(path_of(MCP))


MCP_FILE_DAMAGE: dict[str, Callable[[Env], None]] = {"a-link": _make_link, "a-folder": _make_folder}


@pytest.mark.parametrize("name", list(MCP_FILE_DAMAGE))
def test_ac9_plan_changes_refuses_an_mcp_file_that_is_not_a_regular_file(name: str) -> None:
    """AC-9. expected_behavior_source: AC-9 ("a symlinked or non-regular .mcp.json makes
    plan_changes refuse with ORQ-E114") and ADR-002 decision 8 ("When a declaration registers
    Claude Code and `.mcp.json` is a link or not a regular file, `plan_changes` already refuses with
    `ORQ-E114`"): the composition holds `.mcp.json`, so the path is read and refused."""
    env = initialised()
    MCP_FILE_DAMAGE[name](env)
    services = env.services()
    composition = composer(env)(integrations=integrations_of(server()))
    recorded = load_installation(services).recorded

    with pytest.raises(InitRefused) as refused:
        plan_changes(services, composition.desired, recorded)

    assert refused.value.code == "ORQ-E114"


@pytest.mark.parametrize("name", list(MCP_FILE_DAMAGE))
def test_ac9_an_upgrade_with_a_declaration_stops_before_anything_is_written(name: str) -> None:
    """AC-9. expected_behavior_source: AC-9 ("upgrade exit 3 before anything is written") and
    ADR-002 decision 8 ("`upgrade` exits 3 before anything is written"): with a declaration that
    registers Claude Code and a new release that would rewrite many files, the upgrade is refused
    with ORQ-E114 (raised or returned) and the project and the journal are as they were."""
    env = initialised()
    env.workflow = NEXT
    declare(env, valid_bytes())
    MCP_FILE_DAMAGE[name](env)
    before, before_data = tree(env.project), tree(env.user_data)

    refused_with: set[str] = set()
    try:
        result = upgrade(env.services(), GO)
    except InitRefused as error:
        refused_with = {error.code}
    else:
        assert result.status == "refused"
        refused_with = codes(result.findings)

    assert "ORQ-E114" in refused_with
    assert tree(env.project) == before
    assert tree(env.user_data) == before_data


@pytest.mark.parametrize("name", list(MCP_FILE_DAMAGE))
def test_ac9_without_a_declaration_the_same_file_does_not_stop_an_upgrade(name: str) -> None:
    """AC-9. expected_behavior_source: ADR-002 decision 8 ("a project without a declaration keeps
    its behaviour") and ADR-003 decision 2 ("When it is absent, `upgrade` writes no MCP file"): the
    link or the folder at `.mcp.json` is not read when no `.mcp.json` is wanted."""
    env = initialised()
    MCP_FILE_DAMAGE[name](env)

    result = upgrade(env.services(), GO)

    assert result.status == "up-to-date"


# --- AC-6: init and explain -----------------------------------------------------------------------


def with_declaration_before_init() -> Env:
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    declare(env, valid_bytes())
    return env


def test_ac6_init_writes_no_mcp_file_even_when_a_declaration_exists() -> None:
    """AC-6. expected_behavior_source: AC-6 ("init composes without a declaration, so no MCP file is
    written by init even when a declaration exists") and ADR-003 decision 3 ("`init` composes
    without a declaration, as it does without the registry, so the first `.mcp.json` is written
    by the next `upgrade`")."""
    env = with_declaration_before_init()

    result = init_project(env.services(), YES)

    assert result.status == "applied"
    assert result.plan is not None
    assert MCP not in {str(w.path) for w in result.plan.writes}
    assert MCP not in tree(env.project)
    assert lock_entry(env, MCP) is None
    assert read(env, DECLARATION) == valid_bytes()


def test_ac6_a_dry_run_of_init_plans_no_mcp_file() -> None:
    """AC-6. expected_behavior_source: AC-6 and ADR-003 decision 3, for the preview: the plan of
    `init --dry-run` does not hold `.mcp.json` either."""
    env = with_declaration_before_init()

    result = init_project(env.services(), InitOptions(dry_run=True))

    assert result.status == "previewed"
    assert result.plan is not None
    assert MCP not in {str(w.path) for w in result.plan.writes}


def test_ac6_the_first_mcp_file_is_written_by_the_upgrade_that_follows_init() -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 3 ("so the first `.mcp.json` is written
    by the next `upgrade`") and ADR-003 consequences ("a first run needs `init` and then
    `upgrade`")."""
    env = with_declaration_before_init()
    init_project(env.services(), YES)

    result = upgrade(env.services(), GO)

    assert result.status == "applied"
    assert read(env, MCP) == ATLASSIAN_TEXT.encode("utf-8")


def test_ac6_init_passes_no_declaration_to_compose(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 3 ("`init` composes without a declaration")
    and EC-9: the call of `compose` that `init` makes passes no declaration or `None`."""
    calls: list[dict[str, Any]] = []

    def recording(*args: Any, **kwargs: Any) -> Composition:
        calls.append(dict(kwargs))
        return compose(*args, **kwargs)

    monkeypatch.setattr(init_module, "compose", recording)
    env = with_declaration_before_init()

    init_project(env.services(), YES)

    assert calls
    assert all(call.get("integrations") is None for call in calls)


def test_ac6_explain_is_the_same_with_a_valid_declaration_in_the_project() -> None:
    """AC-6. expected_behavior_source: AC-6 ("explain is not changed") and ADR-003 decision 3
    ("`explain` is not changed"): the explanation of a project with a declaration is equal in every
    field to the one of the same project without it."""
    plain = explain(initialised().services(), QUERY)
    env = initialised()
    declare(env, valid_bytes())

    assert explain(env.services(), QUERY) == plain


@pytest.mark.parametrize("name", list(INVALID_DECLARATIONS))
def test_ac6_explain_does_not_read_an_invalid_declaration(name: str) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 3 ("`explain` is not changed"; `explain`
    previews without the declaration and builds no plan): an invalid declaration does not refuse
    it and adds no finding."""
    plain = explain(initialised().services(), QUERY)
    env = initialised()
    declare(env, INVALID_DECLARATIONS[name][0])

    assert explain(env.services(), QUERY) == plain


def test_ac6_explain_composes_without_a_declaration(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-6. expected_behavior_source: ADR-003 decision 3 ("`explain` is not changed") and EC-9:
    the call of `compose` that `explain` makes passes no declaration or `None`."""
    calls: list[dict[str, Any]] = []

    def recording(*args: Any, **kwargs: Any) -> Composition:
        calls.append(dict(kwargs))
        return compose(*args, **kwargs)

    env = initialised()
    declare(env, valid_bytes())
    monkeypatch.setattr(explain_module, "compose", recording)

    explain(env.services(), QUERY)

    assert calls
    assert all(call.get("integrations") is None for call in calls)


def test_ac6_the_signature_of_explain_is_unchanged() -> None:
    """AC-6. expected_behavior_source: EC-5 to EC-9 list no change of `explain` and ADR-003
    decision 3 ("`explain` is not changed")."""
    assert list(inspect.signature(explain).parameters) == ["services", "query"]


# --- AC-10: the public API ------------------------------------------------------------------------

# The public names of each module that this phase edits, or must leave alone, as the project's
# extractor reads them from the file at the base (the commit of phase P-4): name and signature.
RENDER_SIGNATURE = "def render(self, request: RenderRequest) -> RenderResult"
INSTRUCTION_ADAPTER_API = {
    "RenderedFile": "class RenderedFile",
    "CapabilityLimit": "class CapabilityLimit",
    "ScopedRule": "class ScopedRule",
    "ClientCommand": "class ClientCommand",
    "ClientSkill": "class ClientSkill",
    "ClientRole": "class ClientRole",
    "ConventionsView": "class ConventionsView",
    "RenderRequest": "class RenderRequest",  # EC-10: the field is not visible to the extractor
    "RenderResult": "class RenderResult",
    "InstructionAdapter": "class InstructionAdapter(Protocol)",
    "InstructionAdapter.render": RENDER_SIGNATURE,
}
CLAUDE_CODE_API = {
    "DOCUMENTATION_LIMIT": "DOCUMENTATION_LIMIT",
    "ClaudeCodeAdapter": "class ClaudeCodeAdapter",
    "ClaudeCodeAdapter.render": RENDER_SIGNATURE,
}
CODEX_API = {
    "DOCUMENTATION_LIMIT": "DOCUMENTATION_LIMIT",
    "NO_PATH_RULES_LIMIT": "NO_PATH_RULES_LIMIT",
    "NO_COMMANDS_LIMIT": "NO_COMMANDS_LIMIT",
    "SKILL_FIELD_LIMIT": "SKILL_FIELD_LIMIT",
    "CodexAdapter": "class CodexAdapter",
    "CodexAdapter.render": RENDER_SIGNATURE,
}
CURSOR_API = {
    "DOCUMENTATION_LIMIT": "DOCUMENTATION_LIMIT",
    "SKILL_PLACES_LIMIT": "SKILL_PLACES_LIMIT",
    "CursorAdapter": "class CursorAdapter",
    "CursorAdapter.render": RENDER_SIGNATURE,
}
MCP_RENDER_API = {  # EC-7: a new module with one public name
    "render_mcp_file": "def render_mcp_file(servers: Sequence[McpServer], client: str) -> str",
}
RENDER_ALL_API = {
    "PROFILE_PATH": "PROFILE_PATH",
    "LOCK_PATH": "LOCK_PATH",
    "VERSIONS_PATH": "VERSIONS_PATH",
    "BINDINGS_PATH": "BINDINGS_PATH",
    "STANDARDS_LOCK_PATH": "STANDARDS_LOCK_PATH",
    "WORKFLOW_LOCK_PATH": "WORKFLOW_LOCK_PATH",
    "RELEASED_PATH": "RELEASED_PATH",
    "KNOWLEDGE_PATH": "KNOWLEDGE_PATH",
    "REVIEW_AGENTS": (
        "REVIEW_AGENTS: tuple[tuple[Literal['architecture-reviewer', 'security-reviewer'], str],"
        " ...]"
    ),
    "Composition": "class Composition",
    "stack_of_profile": "def stack_of_profile(profile: ProjectProfile) -> Stack",
    "resolve_for": (
        "def resolve_for(services: Services, profile: ProjectProfile, *, prompts_dir: str |"
        " None=None) -> Resolution"
    ),
    # EC-9: the one changed signature, `integrations` between `resources_bytes` and `orqlet_owned`.
    "compose": (
        "def compose(services: Services, profile: ProjectProfile, resolution: Resolution,"
        " resources: Resources, *, clients: Sequence[str], prompts_dir: str, pr_targets:"
        " tuple[str, ...], profile_bytes: bytes, resources_bytes: bytes, integrations:"
        " Integrations | None=None, orqlet_owned: frozenset[str]=frozenset(), released:"
        " frozenset[str]=frozenset(), released_record: bytes | None=None) -> Composition"
    ),
    "team_template": (
        "def team_template(loaded: Sequence[LoadedPack], findings: list[Finding]) ->"
        " TeamTemplate | None"
    ),
    "pr_template_files": (
        "def pr_template_files(services: Services, targets: tuple[str, ...], team: TeamTemplate"
        " | None) -> list[Desired]"
    ),
    "seed_files": (
        "def seed_files(services: Services, prompts_dir: str, findings: list[Finding]) ->"
        " list[Desired]"
    ),
    "data_files": (
        "def data_files(services: Services, profile_bytes: bytes, resources_bytes: bytes,"
        " resolution: Resolution) -> list[Desired]"
    ),
    "source_of": "def source_of(pack_id: str, resolution: Resolution) -> str",
    "claude_entry_points": (
        "def claude_entry_points(files: list[RenderedFile], services: Services, orqlet_owned:"
        " frozenset[str]) -> list[RenderedFile]"
    ),
    "limit_findings": "def limit_findings(limits: Iterable[CapabilityLimit]) -> list[Finding]",
    "plan_changes": (
        "def plan_changes(services: Services, desired: list[Desired], recorded:"
        " Sequence[Recorded]) -> ChangePlan"
    ),
    "environment_findings": (
        "def environment_findings(services: Services, prompts_dir: str) -> list[Finding]"
    ),
    "codeowners_mentions": "def codeowners_mentions(project: FileSystem, prompts_dir: str) -> bool",
    "ignored_findings": (
        "def ignored_findings(services: Services, paths: Iterable[CanonicalPath]) -> list[Finding]"
    ),
    "planned_write": (
        "def planned_write(services: Services, path: CanonicalPath, content: bytes, *, last:"
        " bool=False) -> PlannedWrite"
    ),
}
UPGRADE_API = {
    "UpgradeStatus": "UpgradeStatus",
    "UpgradeOptions": "class UpgradeOptions",
    "UpgradeResult": "class UpgradeResult",
    "upgrade": "def upgrade(services: Services, options: UpgradeOptions) -> UpgradeResult",
}
RENDER_REQUEST_API = {
    "WORKFLOW_RULE": "WORKFLOW_RULE",
    "COMMANDS_DIR": "COMMANDS_DIR",
    "RenderRequestError": "class RenderRequestError(OrqletError)",
    "rule_slug": "def rule_slug(rule_id: str) -> str",
    "build_render_request": (
        "def build_render_request(workflow: WorkflowSource, loader: DocumentLoader, rules:"
        " Sequence[RuleSpec], resources: Resources, conventions: ConventionsView | None, *,"
        " client_version: str | None=None, available_commands:"
        " Collection[str]=IMPLEMENTED_COMMANDS) -> RenderRequest"
    ),
    "parse_command": "def parse_command(path: str, text: str) -> tuple[str, str]",
}
EXPLAIN_API = {
    "UNINSPECTABLE": "UNINSPECTABLE",
    "Explanation": "class Explanation",
    "explain": "def explain(services: Services, query: StandardsQuery) -> Explanation",
}
INIT_API = {
    "InitOptions": "class InitOptions",
    "InitResult": "class InitResult",
    "InitServices": "InitServices = Services",
    "Stores": "from orqlet.application.usecases.services import Stores as Stores",
    "init_project": "def init_project(services: InitServices, options: InitOptions) -> InitResult",
}
MODULE_APIS: dict[str, dict[str, str]] = {
    "orqlet.application.ports.instruction_adapter": INSTRUCTION_ADAPTER_API,
    "orqlet.adapters.clients.claude_code": CLAUDE_CODE_API,
    "orqlet.adapters.clients.codex": CODEX_API,
    "orqlet.adapters.clients.cursor": CURSOR_API,
    "orqlet.adapters.render.mcp": MCP_RENDER_API,
    "orqlet.application.usecases.render_all": RENDER_ALL_API,
    "orqlet.application.usecases.upgrade": UPGRADE_API,
    "orqlet.application.usecases.render_request": RENDER_REQUEST_API,
    "orqlet.application.usecases.explain": EXPLAIN_API,
    "orqlet.application.usecases.init_project": INIT_API,
}
# The modules of `adapters/render` at the base, and the one that EC-7 adds.
RENDER_MODULES = {
    "__init__.py",
    "emit.py",
    "instructions.py",
    "mcp.py",
    "pr_template.py",
    "prompts_seed.py",
    "renderers.py",
    "roles.py",
    "rules.py",
    "skills.py",
}


@pytest.mark.parametrize("module", list(MODULE_APIS))
def test_ac10_the_public_names_of_each_edited_module_are_the_base_ones_and_the_expected_changes(
    module: str,
) -> None:
    """AC-10. expected_behavior_source: AC-10 ("The public API of the package differs from the
    base, in this phase, only by EC-7, EC-9 and EC-10; every other new name starts with an
    underscore"), EC-7 (`render_mcp_file`), EC-9 (`compose` gains `integrations`) and EC-10
    (`RenderRequest`, whose class line does not change) and component.md ("the only public names
    added are the ones listed"): the extractor reads each module that is edited, and the modules
    that must stay as they are, and finds the base names with their base signatures, and in
    `render_all` the one new signature of `compose`."""
    path = importlib.import_module(module).__file__
    assert path is not None

    api = extract_module_api(Path(path).read_text(encoding="utf-8"))

    assert api.errors == ()
    assert api.manual == ()
    assert {name: symbol.signature for name, symbol in api.symbols.items()} == MODULE_APIS[module]


def test_ac10_the_render_package_has_one_new_module_and_it_is_mcp() -> None:
    """AC-10. expected_behavior_source: EC-7 (`orqlet.adapters.render.mcp.render_mcp_file`) and
    component.md ("`render_mcp_file` is an adapter helper"): the modules of `adapters/render` are
    the ones of the base and `mcp.py`."""
    import orqlet.adapters.render as package

    folder = Path(package.__file__ or "").parent

    assert {path.name for path in folder.glob("*.py")} == RENDER_MODULES
