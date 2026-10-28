"""The tightened contract `orqlet.integrations/v1` (task mcp-or-plugins, phase P-2).

Every test cites its `expected_behavior_source`. ADR-002, ADR-003 and ADR-004 are the files
`adr-00N-*.md` under docs/design/mcp-or-plugins/design/, EC-n are the expected changes of the
manifest.yaml next to them, Q-n are the answers in docs/design/mcp-or-plugins/questions.yaml, and
AC-1 to AC-8 are the acceptance criteria of phase P-2 in docs/design/mcp-or-plugins/plan.yaml.

These tests were written first, by the Tester of phase P-2, before the validators and
`Integrations.registered_for` existed. They cover AC-1 to AC-6 (a failing and a passing case for
every rule, the stdio rule, the independence of the contract from the closed table, the method
`registered_for`, and the text of every error). The committed schema, the round trip of the valid
fixture and the unknown-field checks are done for every contract by
tests/contract/test_contracts.py, and the public names of the module are checked by the extractor
(AC-7).

Every declaration is built from the valid fixture: it is loaded with `yaml.safe_load` and a copy
is changed, never the fixture. The fields that the new rules look at are set explicitly by
`server()`, so these tests do not depend on what the fixture holds in them. The closed table of
`allowed_auth_modes` is not a rule of the contract (ADR-002 decision 2, phase P-3), so no test here
needs an address that is on it.

Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003); every address uses example.com except the two that the closed table names.

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- the wording of any message, the type of the exception and whether a rule sits on a field or on
  the model (only that a ValidationError is raised, that its text is not empty and that it shows no
  part of the input are checked);
- the location (`loc`) of an error, which may hold the raw key of a free-form map; mapping an error
  to a closed field name is the loader's job (ADR-002 decision 9, phase P-3);
- whether an unregistered server with `auth.mode: none` is valid, and which `backend_identity` it
  would then carry (ADR-002 decision 1 says `none` is refused for a registered server only);
- a remote server without an address, a stdio server that carries an address, a stdio server that
  lacks a `command` or a `package`, and a remote server that carries a `command` or a `package`;
- whether `clients` may list a client that has no `per_client` entry or an entry that says false
  (the tests assume it may, because ADR-002 decision 10 asks only that `clients` include every
  client with `register: true`);
- a `per_client` key that is not one of the three clients and has `register: true`;
- the letter case of the client name that `registered_for` is given.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.integrations import Integrations, McpServer
from orqlet.application.contracts.loading import load_contract
from orqlet.application.ports.documents import DocumentError
from orqlet.domain.mcp_credentials import name_problems

pytestmark = pytest.mark.unit

SCHEMA = "orqlet.integrations/v1"
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
LOADER = StrictYamlLoader()

CLIENTS = ("claude-code", "codex", "cursor")
OAUTH = "client-native-oauth"
ENV_REF = "env-ref"
USER_OAUTH = "user-oauth"
USER_TOKEN = "user-token"
BACKEND_IDENTITY = {OAUTH: USER_OAUTH, ENV_REF: USER_TOKEN}
EDITABLE = (
    "client-enforced-editable"  # an `enforced_by` that no rule of ADR-002 decision 10 refuses
)
MANAGED = "client-managed"
GOOD_URL = "https://docs.example.com/mcp"
ATLASSIAN_URL = "https://mcp.atlassian.com/v2/mcp"
GITHUB_URL = "https://api.githubcopilot.com/mcp/"
VARIABLE = "ORQLET_MCP_DOCS_TOKEN"
OTHER_VARIABLE = "ORQLET_MCP_WIKI_TOKEN"
STDIO = {"kind": "stdio", "command": "npx", "package": "@example/docs-mcp"}
# The closed set of rule names that a refusal of the contract may name: the four of `name_problems`
# and the ones of the validators of ADR-002 decisions 1, 3, 4, 5 and 10 (rework of phase P-2: the
# first test of AC-6 only checked that the text was not empty).
RULE_NAMES = (
    "server-id-pattern",
    "variable-pattern",
    "variable-length",
    "address-literal-https",
    "registration-name",
    "reference-in-command",
    "reference-in-package",
    "env-refs-count",
    "auth-mode-none",
    "backend-identity",
    "enforced-by-server",
    "enforced-by-none",
    "verification-verified",
    "stdio-registered",
    "clients-omit-registered",
    "server-id-repeated",
    "variable-shared",
)


# --- helpers --------------------------------------------------------------------------------------


def parametrized(name: str, cases: Mapping[str, object]) -> pytest.MarkDecorator:
    """`pytest.mark.parametrize` over the values of a mapping, with its keys as test ids."""
    return pytest.mark.parametrize(name, list(cases.values()), ids=list(cases))


def fixture() -> dict[str, Any]:
    """The valid fixture as plain data, which a test may change freely."""
    loaded = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return copy.deepcopy(loaded)


def server(
    server_id: str = "docs",
    *,
    mode: str = OAUTH,
    variables: Sequence[str] = (),
    registered: Sequence[str] = ("claude-code",),
    backend_identity: str | None = None,
    **changes: Any,
) -> dict[str, Any]:
    """A server that satisfies every rule of the contract, taken from the fixture's first one.

    The fields that a rule looks at are set here: the id, the entry name `orqlet-<id>`, a literal
    https address, the enforced_by labels, the clients and the authentication with its backend
    identity. A keyword that is not named replaces the whole field of that name.
    """
    base = copy.deepcopy(fixture()["servers"][0])
    base.update(
        id=server_id,
        capability_tier="read",
        identity={"kind": "remote", "url": GOOD_URL},
        registration={"name": f"orqlet-{server_id}", "mode": "read-only", "enforced_by": EDITABLE},
        per_client={client: {"register": True, "enforced_by": EDITABLE} for client in registered},
        clients=list(registered),
        auth={"mode": mode, "env_refs": list(variables)},
    )
    if backend_identity is None:
        backend_identity = BACKEND_IDENTITY[mode]  # an empty string is a value, not "no value"
    base["data_flow"]["backend_identity"] = backend_identity
    return {**base, **changes}


def env_server(variable: str = VARIABLE, server_id: str = "docs", **changes: Any) -> dict[str, Any]:
    """A server that authenticates with one variable of the user's own."""
    return server(server_id, mode=ENV_REF, variables=(variable,), **changes)


def stdio_server(
    server_id: str = "docs",
    *,
    mode: str = OAUTH,
    variables: Sequence[str] = (),
    **changes: Any,
) -> dict[str, Any]:
    """A stdio server that is registered for no client: the one valid kind of stdio server."""
    return server(
        server_id,
        mode=mode,
        variables=variables,
        registered=(),
        **{"identity": dict(STDIO), **changes},
    )


def changed(data: dict[str, Any], *path: str, value: object) -> dict[str, Any]:
    """A copy of `data` with `value` set at `path`, a way into nested mappings."""
    result = copy.deepcopy(data)
    node = result
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return result


def declaration(*servers: dict[str, Any]) -> dict[str, Any]:
    """The fixture's document with these servers, and a role that names each of them."""
    data = fixture()
    data["servers"] = [copy.deepcopy(item) for item in servers]
    data["roles"] = {"architecture-reviewer": {"servers": [item["id"] for item in servers]}}
    return data


def load(*servers: dict[str, Any]) -> Integrations:
    return Integrations.model_validate(declaration(*servers))


def refusal(*servers: dict[str, Any]) -> ValidationError:
    with pytest.raises(ValidationError) as caught:
        Integrations.model_validate(declaration(*servers))
    return caught.value


def ids_of(servers: Sequence[McpServer]) -> list[str]:
    return [item.id for item in servers]


def registered_for(loaded: Integrations, client: str) -> tuple[McpServer, ...]:
    """The one place that calls the new method, so the type check reports it once."""
    found: tuple[McpServer, ...] = loaded.registered_for(client)
    return found


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it (any letter case).

    A window of 8 characters of a random-looking secret cannot appear in a fixed message by chance.
    """
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def error_texts(error: ValidationError) -> str:
    """Everything that an error says without the input: type, message, location and context."""
    lines: list[str] = []
    for item in error.errors(include_input=False, include_url=False):
        lines.append(str(item["type"]))
        lines.append(str(item["msg"]))
        lines.append(".".join(str(part) for part in item["loc"]))
        lines.append(str(item.get("ctx", "")))
    return "\n".join(lines)


# --- values for the rules of ADR-002 decisions 3 and 4 (the domain function is the oracle) --------

GOOD_IDS = {
    "one-letter": "a",
    "one-word": "atlassian",
    "words-joined-by-a-hyphen": "a-b",
    "digit-after-the-first-letter": "a1",
    "thirty-two-characters": "a" + "b" * 31,
}
BAD_IDS = {
    "empty": "",
    "upper-case": "Atlassian",
    "starts-with-a-digit": "1atlassian",
    "starts-with-a-hyphen": "-atlassian",
    "underscore": "atlas_sian",
    "space": "atlas sian",
    "dot": "atlas.sian",
    "slash": "atlas/sian",
    "thirty-three-characters": "a" * 33,
    "trailing-line-feed": "atlassian\n",
    "kelvin-sign": "\u212a",
    "accented-letter": "caf\u00e9",
    "fullwidth-letter": "\uff41tlassian",
}
GOOD_VARIABLES = {
    "one-letter": "ORQLET_MCP_A",
    "two-segments": "ORQLET_MCP_GITHUB_TOKEN",
    "digits-after-a-letter": "ORQLET_MCP_A1_B2",
    "forty-eight-characters": "ORQLET_MCP_" + "A" * 37,
}
BAD_VARIABLES = {
    "empty": "",
    "no-prefix": "GITHUB_TOKEN",
    "the-one-variable-orqlet-reads": "ORQLET_DATA_DIR",
    "lower-case": "orqlet_mcp_github",
    "prefix-only": "ORQLET_MCP_",
    "double-underscore": "ORQLET_MCP_A__B",
    "trailing-underscore": "ORQLET_MCP_A_",
    "hyphen": "ORQLET_MCP_A-B",
    "forty-nine-characters": "ORQLET_MCP_" + "A" * 38,
    "trailing-line-feed": VARIABLE + "\n",
    "reference-syntax": "${" + VARIABLE + "}",
    "kelvin-sign": "ORQLET_MCP_\u212a",
}
GOOD_URLS = {
    "plain": GOOD_URL,
    "with-a-port": "https://docs.example.com:8443/mcp",
    "host-only": "https://docs.example.com",
    "trailing-slash": "https://docs.example.com/mcp/",
    "deep-path": "https://docs.example.com/a/b-c/d_e/f.g~h",
    "upper-case-host": "https://DOCS.EXAMPLE.COM/mcp",
}
BAD_URLS = {
    "empty": "",
    "plain-http": "http://docs.example.com/mcp",
    "other-scheme": "ftp://docs.example.com/mcp",
    "no-scheme": "docs.example.com/mcp",
    "scheme-relative": "//docs.example.com/mcp",
    "user-information": "https://someone@docs.example.com/mcp",
    "user-and-password": "https://someone:pw@docs.example.com/mcp",
    "query": "https://docs.example.com/mcp?page=2",
    "empty-query": "https://docs.example.com/mcp?",
    "fragment": "https://docs.example.com/mcp#top",
    "variable-in-the-host": "https://${HOST}/mcp",
    "variable-in-the-path": "https://docs.example.com/${PATH_PART}",
    "backslash": "https://docs.example.com\\mcp",
    "percent-encoded-letter": "https://docs.example.com/%41",
    "trailing-line-feed": GOOD_URL + "\n",
    "accented-host": "https://d\u00f6cs.example.com/mcp",
}
COMMANDS_WITH_A_REFERENCE = {
    "the-whole-command": "${COMMAND}",
    "inside-a-path": "run ${HOME}/bin",
    "default-form": "run ${NAME:-fallback}",
    "env-form": "run ${env:NAME}",
}
COMMANDS_WITHOUT_A_REFERENCE = {
    "a-name": "npx",
    "a-dollar-sign-alone": "run-$HOME",
    "a-brace-alone": "run-{value}",
}
PACKAGES_WITH_A_REFERENCE = {
    "the-whole-package": "${PACKAGE}",
    "inside-a-scope": "@example/${NAME}",
    "default-form": "pkg-${NAME:-fallback}",
}
PACKAGES_WITHOUT_A_REFERENCE = {
    "a-name": "docs-mcp",
    "scoped-with-a-version": "@example/docs-mcp@1.2.3",
}


# --- AC-1: server ids -----------------------------------------------------------------------------


@parametrized(
    "ids",
    {
        "two-next-to-each-other": ["docs", "docs"],
        "separated-by-another": ["docs", "wiki", "docs"],
        "at-the-end": ["docs", "wiki", "wiki"],
    },
)
def test_a_server_id_that_is_repeated_is_refused(ids: list[str]) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("Server ids are unique")."""
    refusal(*(server(value) for value in ids))


def test_servers_with_distinct_ids_load_in_the_order_they_are_written() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("Server ids are unique"); ADR-002
    decision 5 (a server list in declaration order). The ids are not in alphabetical order."""
    loaded = load(server("wiki"), server("docs"), server("api"))

    assert ids_of(loaded.servers) == ["wiki", "docs", "api"]


@parametrized("value", BAD_IDS)
def test_an_id_that_name_problems_rejects_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("A server `id` matches
    `^[a-z][a-z0-9-]{0,31}$`", fullmatch, `re.ASCII`) and decision 5 (the validators call
    `name_problems`). The registration name is `orqlet-` and the id, so only the id breaks a
    rule."""
    assert name_problems(value, GOOD_URL, None)

    refusal(server(value))


@parametrized("value", GOOD_IDS)
def test_an_id_that_name_problems_accepts_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (`^[a-z][a-z0-9-]{0,31}$`)."""
    assert name_problems(value, GOOD_URL, None) == ()

    (loaded,) = load(server(value)).servers

    assert loaded.id == value


# --- AC-1: the registration name ------------------------------------------------------------------


@parametrized(
    "name",
    {
        "the-id-alone": "docs",
        "the-prefix-alone": "orqlet-",
        "another-id": "orqlet-wiki",
        "longer-than-the-id": "orqlet-docs-2",
        "prefix-twice": "orqlet-orqlet-docs",
        "upper-case-prefix": "ORQLET-docs",
        "underscore-for-the-hyphen": "orqlet_docs",
        "leading-space": " orqlet-docs",
        "trailing-space": "orqlet-docs ",
        "trailing-line-feed": "orqlet-docs\n",
        "empty": "",
    },
)
def test_a_registration_name_other_than_orqlet_and_the_id_is_refused(name: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("the entry is named `orqlet-<id>`, and
    `registration.name` equals `orqlet-<id>`"); the old fixture used `docs`."""
    refusal(changed(server("docs"), "registration", "name", value=name))


@pytest.mark.parametrize("server_id", ["docs", "a", "atlassian", "a-1-b", "a" + "b" * 31])
def test_a_registration_name_of_orqlet_followed_by_the_id_loads(server_id: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (`registration.name` equals
    `orqlet-<id>`)."""
    (loaded,) = load(server(server_id)).servers

    assert loaded.registration.name == f"orqlet-{server_id}"


# --- AC-1: env_refs and the authentication mode ---------------------------------------------------


@parametrized("value", GOOD_VARIABLES)
def test_an_env_ref_server_with_one_name_that_name_problems_accepts_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("A variable name matches
    `^ORQLET_MCP_[A-Z][A-Z0-9]*(_[A-Z][A-Z0-9]*)*$` with at most 48 characters. An `env-ref`
    server has exactly one variable")."""
    assert name_problems("docs", GOOD_URL, value) == ()

    (loaded,) = load(env_server(value)).servers

    assert loaded.auth.env_refs == (value,)


@parametrized("value", BAD_VARIABLES)
def test_a_variable_name_that_name_problems_rejects_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (the pattern, fullmatch, `re.ASCII`, at
    most 48 characters) and decision 5 (the validators call `name_problems`)."""
    assert name_problems("docs", GOOD_URL, value)

    refusal(env_server(value))


@parametrized(
    "names",
    {
        "two-different-names": (VARIABLE, OTHER_VARIABLE),
        "the-same-name-twice": (VARIABLE, VARIABLE),
        "three-names": (VARIABLE, OTHER_VARIABLE, "ORQLET_MCP_THIRD"),
    },
)
def test_an_env_ref_server_with_more_than_one_name_is_refused(names: tuple[str, ...]) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("An `env-ref` server has exactly one
    variable") and EC-12 ("env_refs holds exactly one name for env-ref")."""
    refusal(server(mode=ENV_REF, variables=names))


def test_an_env_ref_server_with_no_name_is_refused() -> None:
    """AC-1. expected_behavior_source: EC-12 ("env_refs holds exactly one name for env-ref") and
    ADR-002 decision 3 ("An `env-ref` server has exactly one variable"). The wording of AC-1 names
    only more than one name; the lower bound comes from these two sources."""
    refusal(server(mode=ENV_REF, variables=()))


@parametrized(
    "names",
    {
        "a-valid-name": (VARIABLE,),
        "an-invalid-name": ("not a variable name",),
        "two-names": (VARIABLE, OTHER_VARIABLE),
    },
)
def test_a_name_in_env_refs_for_client_native_oauth_is_refused(names: tuple[str, ...]) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("an OAuth server none") and EC-12
    ("env_refs holds ... none for client-native-oauth")."""
    refusal(server(mode=OAUTH, variables=names))


def test_client_native_oauth_with_no_name_loads() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("an OAuth server none")."""
    (loaded,) = load(server(mode=OAUTH, variables=())).servers

    assert loaded.auth.mode == OAUTH
    assert loaded.auth.env_refs == ()


@pytest.mark.parametrize("backend_identity", [USER_OAUTH, USER_TOKEN, "Example"])
@pytest.mark.parametrize("client", CLIENTS)
def test_the_mode_none_is_refused_for_a_server_registered_for_a_client(
    client: str, backend_identity: str
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 ("`none` stays in the contract type but
    is refused for a registered server")."""
    refusal(server(mode="none", registered=(client,), backend_identity=backend_identity))


# --- AC-1: the backend identity -------------------------------------------------------------------


@parametrized(
    "label",
    {
        "the-token-label": USER_TOKEN,
        "free-text": "Example",
        "a-shared-account": "service-account",
        "empty": "",
        "upper-case": "User-OAuth",
        "trailing-space": "user-oauth ",
        "trailing-line-feed": "user-oauth\n",
    },
)
def test_client_native_oauth_with_a_backend_identity_other_than_user_oauth_is_refused(
    label: str,
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 ("`backend_identity` is `user-oauth`
    with `client-native-oauth` and `user-token` with `env-ref`, and nothing else") and Q-9 ("No:
    no shared identity is allowed for any integration; every credential is one user's own")."""
    refusal(server(mode=OAUTH, backend_identity=label))


@parametrized(
    "label",
    {
        "the-oauth-label": USER_OAUTH,
        "free-text": "Example",
        "a-shared-account": "service-account",
        "empty": "",
        "upper-case": "User-Token",
        "trailing-line-feed": "user-token\n",
    },
)
def test_env_ref_with_a_backend_identity_other_than_user_token_is_refused(label: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 ("`user-token` with `env-ref`, and
    nothing else") and Q-9 (no shared identity)."""
    refusal(server(mode=ENV_REF, variables=(VARIABLE,), backend_identity=label))


def test_each_mode_loads_with_its_own_backend_identity() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`user-oauth` with `client-native-oauth`
    and `user-token` with `env-ref`)."""
    oauth, token = load(server("docs"), env_server(VARIABLE, "wiki")).servers

    assert (oauth.auth.mode, oauth.data_flow.backend_identity) == (OAUTH, USER_OAUTH)
    assert (token.auth.mode, token.data_flow.backend_identity) == (ENV_REF, USER_TOKEN)


# --- AC-1: one variable name belongs to one server ------------------------------------------------


@parametrized(
    "servers",
    {
        "two-registered-servers": (env_server(VARIABLE, "docs"), env_server(VARIABLE, "wiki")),
        "the-first-and-the-last-of-three": (
            env_server(VARIABLE, "docs"),
            env_server(OTHER_VARIABLE, "wiki"),
            env_server(VARIABLE, "api"),
        ),
        "the-second-server-is-not-registered": (
            env_server(VARIABLE, "docs"),
            stdio_server("wiki", mode=ENV_REF, variables=(VARIABLE,)),
        ),
    },
)
def test_a_variable_name_that_belongs_to_two_servers_is_refused(
    servers: tuple[dict[str, Any], ...],
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("one variable name belongs to one
    server")."""
    refusal(*servers)


def test_two_servers_with_different_variable_names_load() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("one variable name belongs to one
    server")."""
    loaded = load(env_server(VARIABLE, "docs"), env_server(OTHER_VARIABLE, "wiki"))

    assert [item.auth.env_refs for item in loaded.servers] == [(VARIABLE,), (OTHER_VARIABLE,)]


# --- AC-1: verification ---------------------------------------------------------------------------


def test_verified_in_a_registered_client_entry_is_refused() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 ("`verification: verified` is refused,
    because no check record exists that a declaration could point to")."""
    refusal(changed(server(), "per_client", "claude-code", "verification", value="verified"))


def test_verified_in_a_client_entry_that_is_not_registered_is_refused() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`verification: verified` is refused;
    the sentence names no client entry that is exempt)."""
    entry = {"register": False, "enforced_by": EDITABLE, "verification": "verified"}

    refusal(changed(server(), "per_client", "codex", value=entry))


def test_not_tested_loads_whether_it_is_written_or_left_out() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (only `verified` is refused)."""
    written = changed(server(), "per_client", "claude-code", "verification", value="not-tested")

    (explicit,) = load(written).servers
    (default,) = load(server()).servers

    assert explicit.per_client["claude-code"].verification == "not-tested"
    assert default.per_client["claude-code"].verification == "not-tested"


# --- AC-1: the address, the command and the package -----------------------------------------------


@parametrized("value", BAD_URLS)
def test_an_address_that_is_not_a_literal_https_address_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 ("The address is a literal: `https`, a
    host, an optional port and an optional path of ASCII path characters; no user information,
    query or fragment, no `${`, no backslash and no percent-encoding") and decision 5 (the
    validators call `name_problems`)."""
    assert name_problems("docs", value, None)

    refusal(server(identity={"kind": "remote", "url": value}))


@parametrized("value", GOOD_URLS)
def test_a_literal_https_address_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 (a literal `https` address with a host,
    an optional port and an optional path)."""
    assert name_problems("docs", value, None) == ()

    (loaded,) = load(server(identity={"kind": "remote", "url": value})).servers

    assert loaded.identity.url == value


@parametrized("value", COMMANDS_WITH_A_REFERENCE)
def test_a_command_with_a_variable_reference_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 ("`command` and `package` contain no
    `${`") and EC-12 ("command and package contain no ${")."""
    refusal(stdio_server(identity={**STDIO, "command": value}))


@parametrized("value", COMMANDS_WITHOUT_A_REFERENCE)
def test_a_command_without_the_text_dollar_brace_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 (`command` contains no `${`; a dollar
    sign or a brace on its own is not a reference)."""
    (loaded,) = load(stdio_server(identity={**STDIO, "command": value})).servers

    assert loaded.identity.command == value


@parametrized("value", PACKAGES_WITH_A_REFERENCE)
def test_a_package_with_a_variable_reference_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 ("`command` and `package` contain no
    `${`") and EC-12."""
    refusal(stdio_server(identity={**STDIO, "package": value}))


@parametrized("value", PACKAGES_WITHOUT_A_REFERENCE)
def test_a_package_without_the_text_dollar_brace_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 (`package` contains no `${`)."""
    (loaded,) = load(stdio_server(identity={**STDIO, "package": value})).servers

    assert loaded.identity.package == value


# --- AC-2: enforced_by ----------------------------------------------------------------------------

PLACES = ("registration", "a-registered-client", "a-client-that-is-not-registered")


def with_enforced_by(place: str, value: str, **changes: Any) -> dict[str, Any]:
    """A server whose `enforced_by` is `value` in one place and a harmless label in the others."""
    data = server(**changes)
    if place == "registration":
        data["registration"]["enforced_by"] = value
    elif place == "a-registered-client":
        data["per_client"]["claude-code"]["enforced_by"] = value
    else:
        data["per_client"]["codex"] = {"register": False, "enforced_by": value}
    return data


@pytest.mark.parametrize("place", PLACES)
def test_enforced_by_server_is_refused_wherever_it_is_written(place: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 10 ("The contract therefore refuses
    `enforced_by: server` in `registration` and in every `per_client` entry, because no row of the
    table has a server-side limit")."""
    refusal(with_enforced_by(place, "server"))


@pytest.mark.parametrize("value", [EDITABLE, MANAGED, "none"])
@pytest.mark.parametrize("place", PLACES)
def test_the_other_enforced_by_labels_load_for_a_server_that_only_reads(
    place: str, value: str
) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 10 (only `server` is refused everywhere;
    `none` is refused for a `capability_tier` other than `read`)."""
    (loaded,) = load(with_enforced_by(place, value)).servers

    assert loaded.capability_tier == "read"


@pytest.mark.parametrize("tier", ["write", "destructive"])
@pytest.mark.parametrize("place", PLACES)
def test_enforced_by_none_is_refused_for_a_tier_other_than_read(place: str, tier: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 10 ("a server with a `capability_tier`
    other than `read` cannot have `enforced_by: none` anywhere")."""
    refusal(with_enforced_by(place, "none", capability_tier=tier))


@pytest.mark.parametrize("value", [EDITABLE, MANAGED])
@pytest.mark.parametrize("tier", ["write", "destructive"])
@pytest.mark.parametrize("place", PLACES)
def test_a_tier_other_than_read_loads_with_a_label_that_is_not_none(
    place: str, tier: str, value: str
) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 10 (the refusal is of `enforced_by: none`
    for a tier other than `read`, so any other label stays valid)."""
    (loaded,) = load(with_enforced_by(place, value, capability_tier=tier)).servers

    assert loaded.capability_tier == tier


# --- AC-2: clients --------------------------------------------------------------------------------


@parametrized(
    "data",
    {
        "an-empty-list": server(clients=[]),
        "another-client-only": server(clients=["codex"]),
        "one-of-two-registered": server(registered=("claude-code", "codex"), clients=["codex"]),
        "the-second-registered-client-is-missing": server(
            registered=("codex", "cursor"), clients=["codex"]
        ),
    },
)
def test_a_server_whose_clients_omit_a_registered_client_is_refused(data: dict[str, Any]) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 10 ("`clients` must include every client
    with `register: true`")."""
    refusal(data)


def test_a_server_without_a_clients_field_is_refused_when_it_is_registered() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 10 (`clients` must include every client
    with `register: true`; a missing field is an empty list); the old fixture had no `clients`."""
    data = server()
    del data["clients"]

    refusal(data)


@parametrized(
    "data",
    {
        "exactly-the-registered-clients": server(registered=("claude-code", "codex")),
        "every-client-and-one-registered": server(clients=list(CLIENTS)),
        "a-listed-client-with-no-entry": server(clients=["claude-code", "cursor"]),
        "a-listed-client-that-is-not-registered": changed(
            server(clients=["claude-code", "codex"]),
            "per_client",
            "codex",
            value={"register": False, "enforced_by": EDITABLE},
        ),
        "nothing-registered-and-no-clients": server(registered=(), clients=[]),
    },
)
def test_a_server_whose_clients_include_every_registered_client_loads(
    data: dict[str, Any],
) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 10 (`clients` must include every client
    with `register: true`; nothing says that it may hold no other)."""
    (loaded,) = load(data).servers

    registered = {name for name, entry in loaded.per_client.items() if entry.register_server}
    assert registered <= set(loaded.clients)


# --- AC-2: stdio servers cannot be registered -----------------------------------------------------


@pytest.mark.parametrize("client", CLIENTS)
def test_a_stdio_server_registered_for_a_client_is_refused(client: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 4 ("A stdio server can be declared, but it
    cannot be registered for a client in this change") and decision 5; EC-12 ("a stdio server
    cannot be registered"). `clients` lists the client, so only the stdio rule can refuse."""
    refusal(server(registered=(client,), identity=dict(STDIO)))


def test_a_stdio_server_registered_for_one_client_of_several_is_refused() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 4 and AC-2 ("a stdio server has register
    true for any client")."""
    data = stdio_server(
        per_client={
            "claude-code": {"register": False, "enforced_by": EDITABLE},
            "codex": {"register": True, "enforced_by": EDITABLE},
        },
        clients=["codex"],
    )

    refusal(data)


@pytest.mark.parametrize("client", CLIENTS)
def test_a_remote_server_registered_for_a_client_loads(client: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 4 (only a stdio server cannot be
    registered)."""
    (loaded,) = load(server(registered=(client,))).servers

    assert loaded.identity.kind == "remote"
    assert loaded.per_client[client].register_server is True


# --- AC-3: the stdio rule -------------------------------------------------------------------------


@parametrized(
    "data",
    {
        "no-client-entry": stdio_server(),
        "every-client-entry-says-false": stdio_server(
            per_client={client: {"register": False, "enforced_by": EDITABLE} for client in CLIENTS},
            clients=list(CLIENTS),
        ),
    },
)
def test_a_stdio_server_that_is_not_registered_is_valid_without_an_address(
    data: dict[str, Any],
) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 ("a stdio server has no address, so for
    it the validator passes an empty address to `name_problems` and drops `address-literal-https`
    from the result") and AC-3 ("a stdio server that is not registered is valid")."""
    assert name_problems("docs", "", None) == ("address-literal-https",)

    (loaded,) = load(data).servers

    assert loaded.identity.kind == "stdio"
    assert loaded.identity.url is None


@parametrized("value", BAD_IDS)
def test_a_stdio_server_keeps_the_rule_for_the_id(value: str) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 (the validator drops the rule name
    `address-literal-https` and no other from what `name_problems` returns)."""
    assert name_problems(value, "", None) != ("address-literal-https",)

    refusal(stdio_server(value))


@parametrized("value", BAD_VARIABLES)
def test_a_stdio_server_keeps_the_rule_for_the_variable_name(value: str) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 (only `address-literal-https` is
    dropped) and decision 3 (the pattern of a variable name)."""
    assert set(name_problems("docs", "", value)) - {"address-literal-https"}

    refusal(stdio_server(mode=ENV_REF, variables=(value,)))


@parametrized("value", GOOD_VARIABLES)
def test_a_stdio_server_with_a_valid_variable_name_loads(value: str) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 (a stdio server that is not registered
    is valid) and decision 3 (an `env-ref` server has exactly one variable)."""
    (loaded,) = load(stdio_server(mode=ENV_REF, variables=(value,))).servers

    assert loaded.auth.env_refs == (value,)


# --- AC-4: the closed table is not a rule of the contract -----------------------------------------


@parametrized(
    "url",
    {
        "an-address-of-an-example-host": GOOD_URL,
        "an-address-with-a-port": "https://docs.example.com:8443/mcp",
        "an-address-with-a-deep-path": "https://docs.example.com/a/b/c",
        "the-address-of-a-host-only": "https://docs.example.com",
        "the-github-address": GITHUB_URL,
        "the-atlassian-address-with-a-slash": ATLASSIAN_URL + "/",
        "the-atlassian-address-in-capitals": "https://MCP.ATLASSIAN.COM/v2/mcp",
    },
)
def test_a_well_formed_https_address_that_is_not_on_the_closed_table_is_valid(url: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 2 ("The table lives in the domain module,
    outside the contract, so the contract's own rules do not change when a tool release changes
    the table") and AC-4 ("the table is a check of the loader (phase P-3), not a contract rule")."""
    assert name_problems("docs", url, None) == ()

    (loaded,) = load(server(identity={"kind": "remote", "url": url})).servers

    assert loaded.identity.url == url


@pytest.mark.parametrize("client", ["codex", "cursor"])
def test_the_atlassian_address_registered_for_a_client_that_the_table_does_not_enable_is_valid(
    client: str,
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 2 (the table enables the one pair of the
    Atlassian address and Claude Code; the contract does not apply it) and AC-4."""
    data = server(registered=(client,), identity={"kind": "remote", "url": ATLASSIAN_URL})

    (loaded,) = load(data).servers

    assert loaded.identity.url == ATLASSIAN_URL
    assert loaded.per_client[client].register_server is True


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize("url", [ATLASSIAN_URL, GITHUB_URL, GOOD_URL])
def test_an_env_ref_server_for_an_address_that_the_table_does_not_enable_is_valid(
    url: str, client: str
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 2 (no `env-ref` row exists in this change,
    and the check of the table belongs to the loader, ADR-003 decision 3) and AC-4."""
    data = env_server(registered=(client,), identity={"kind": "remote", "url": url})

    (loaded,) = load(data).servers

    assert loaded.auth.mode == ENV_REF


# --- AC-5: Integrations.registered_for ------------------------------------------------------------


def both_entries(*, claude_code: bool, codex: bool) -> dict[str, Any]:
    """A `per_client` mapping that names both clients, each registered or not."""
    return {
        "claude-code": {"register": claude_code, "enforced_by": EDITABLE},
        "codex": {"register": codex, "enforced_by": EDITABLE},
    }


def mixed_declaration() -> Integrations:
    """Four servers, written in an order that is not alphabetical.

    zeta: claude-code and codex. alpha: codex only, with an entry for claude-code that says false.
    mid: claude-code only, with `clients` that also lists cursor and no entry for it. idle: none.
    """
    return load(
        server("zeta", registered=("claude-code", "codex")),
        server(
            "alpha",
            registered=("codex",),
            per_client=both_entries(claude_code=False, codex=True),
        ),
        server("mid", registered=("claude-code",), clients=["claude-code", "cursor"]),
        server("idle", registered=()),
    )


@parametrized(
    "case",
    {
        "claude-code": ("claude-code", ["zeta", "mid"]),
        "codex": ("codex", ["zeta", "alpha"]),
        "cursor-has-no-entry-with-register-true": ("cursor", []),
        "a-client-that-is-not-known": ("vscode", []),
        "an-empty-client-name": ("", []),
    },
)
def test_registered_for_returns_the_servers_registered_for_the_client_in_declaration_order(
    case: tuple[str, list[str]],
) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 5 ("`Integrations.registered_for(client)`
    returns the servers whose `per_client[client].register` is true, in declaration order") and
    EC-8 (`def registered_for(self, client: str) -> tuple[McpServer, ...]`). The servers are
    written zeta, alpha, mid, idle, so the order is not alphabetical."""
    client, expected = case

    found = registered_for(mixed_declaration(), client)

    assert ids_of(found) == expected


def test_registered_for_is_a_method_and_not_a_field_of_the_contract() -> None:
    """AC-5. expected_behavior_source: EC-8 (`def registered_for(self, client: str) ->
    tuple[McpServer, ...]` is a method of `Integrations`) and ADR-003 decision 2 (the committed
    JSON Schema does not change, which a new field would do)."""
    assert hasattr(Integrations, "registered_for")
    assert "registered_for" not in Integrations.model_fields


def test_registered_for_returns_a_tuple_of_the_servers_of_the_declaration() -> None:
    """AC-5. expected_behavior_source: EC-8 (the return type is `tuple[McpServer, ...]`) and
    ADR-002 decision 5 (it returns the servers, not copies of their fields)."""
    loaded = mixed_declaration()

    found = registered_for(loaded, "claude-code")

    assert isinstance(found, tuple)
    assert all(isinstance(item, McpServer) for item in found)
    assert list(found) == [loaded.servers[0], loaded.servers[2]]
    assert found[0] is loaded.servers[0]
    assert found[1] is loaded.servers[2]


def test_registered_for_follows_the_register_flag_and_not_the_list_of_clients() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 5 (the servers "whose
    `per_client[client].register` is true"). The server `mid` lists cursor in `clients`, which is
    not a registration."""
    loaded = mixed_declaration()
    mid = next(item for item in loaded.servers if item.id == "mid")

    assert "cursor" in mid.clients
    assert "mid" not in ids_of(registered_for(loaded, "cursor"))


def test_registered_for_leaves_out_a_server_whose_entry_says_register_false() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 5 ("`register` is true"). The server
    `alpha` has an entry for claude-code that says false."""
    loaded = mixed_declaration()
    alpha = next(item for item in loaded.servers if item.id == "alpha")

    assert alpha.per_client["claude-code"].register_server is False
    assert "alpha" not in ids_of(registered_for(loaded, "claude-code"))


def test_registered_for_returns_every_server_in_the_order_written_when_all_are_registered() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 5 ("in declaration order")."""
    loaded = load(server("wiki"), server("docs"), server("api"))

    assert ids_of(registered_for(loaded, "claude-code")) == ["wiki", "docs", "api"]


@parametrized(
    "data",
    {
        "no-servers": declaration(),
        "servers-that-are-all-unregistered": declaration(
            server("docs", registered=()), stdio_server("wiki")
        ),
        "servers-registered-for-other-clients-only": declaration(
            server("docs", registered=("codex", "cursor"))
        ),
    },
)
def test_registered_for_returns_an_empty_tuple_when_no_server_is_registered(
    data: dict[str, Any],
) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 5 and AC-5 ("an empty tuple when there is
    none"); EC-8 (the return type is a tuple)."""
    found = registered_for(Integrations.model_validate(data), "claude-code")

    assert found == ()
    assert isinstance(found, tuple)


def test_registered_for_gives_the_same_answer_on_every_call() -> None:
    """AC-5. expected_behavior_source: ORQLET-DET-001 (the same input gives the same output); the
    declaration is a frozen contract, so a read changes nothing."""
    loaded = mixed_declaration()
    before = loaded.model_dump(mode="json", by_alias=True)

    first = registered_for(loaded, "codex")
    second = registered_for(loaded, "codex")

    assert first == second
    assert loaded.model_dump(mode="json", by_alias=True) == before


# --- AC-6: no error text holds a part of an input value -------------------------------------------

# Credential-shaped values, assembled at run time (ORQLET-SEC-003). The token has the shape of a
# GitHub personal token (a prefix and 36 letters and digits), the access key that of an AWS key.
TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0JxKa3M"))
ACCESS_KEY = "".join(("AK", "IA", "QZ7XV3LM", "9TK2RB8W"))
PASSWORD = "".join(("hunter", "2Qx", "9Lp", "Vw4"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1"))
OPAQUE_ID = OPAQUE.lower()  # a valid id of 24 characters that reads like a secret
SHARED_PART = "ZQ7SHAREDVAR3B8A"  # the part of a valid variable name that no fixed message holds
SHARED_VARIABLE = "ORQLET_MCP_" + SHARED_PART


def shown_in(text: str) -> tuple[str, ...]:
    """The credential-shaped values among TOKEN and ACCESS_KEY that `text` holds."""
    return tuple(secret for secret in (TOKEN, ACCESS_KEY) if secret in text)


def secret_cases() -> dict[str, tuple[tuple[dict[str, Any], ...], tuple[str, ...]]]:
    """Declarations that break one rule each, with the parts of the input that no text may show.

    The four places of AC-6 are an id, an address, a variable name and a registration name; the
    other validators (a repeated id, a shared variable name, the backend identity, the command and
    the package) are included because "every validator error" is what the criterion names.
    """
    rename = {"id-is-a-token": TOKEN, "id-is-an-access-key": ACCESS_KEY}
    cases: dict[str, tuple[tuple[dict[str, Any], ...], tuple[str, ...]]] = {
        name: ((server(value),), (value,)) for name, value in rename.items()
    }
    cases["id-is-a-token-and-the-name-is-wrong"] = (
        (changed(server(TOKEN), "registration", "name", value="docs"),),
        (TOKEN,),
    )
    cases["id-is-repeated"] = ((server(OPAQUE_ID), server(OPAQUE_ID)), (OPAQUE_ID,))
    for name, url in {
        "address-user-information": f"https://{TOKEN}@docs.example.com/mcp",
        "address-query": f"https://docs.example.com/mcp?token={TOKEN}",
        "address-not-https": f"http://docs.example.com/{TOKEN}",
        "address-reference": f"https://docs.example.com/${{{TOKEN}}}",
        "address-access-key-in-the-host-with-a-query": f"https://{ACCESS_KEY}.example.com/mcp?x=1",
        "address-backslash": f"https://docs.example.com\\{TOKEN}",
    }.items():
        cases[name] = ((server(identity={"kind": "remote", "url": url}),), shown_in(url))
    cases["variable-is-a-token"] = ((env_server(TOKEN),), (TOKEN,))
    cases["variable-is-an-access-key"] = ((env_server(ACCESS_KEY),), (ACCESS_KEY,))
    cases["variable-is-too-long"] = ((env_server("ORQLET_MCP_" + ACCESS_KEY * 3),), (ACCESS_KEY,))
    cases["variable-is-one-of-two-names"] = (
        (server(mode=ENV_REF, variables=("ORQLET_MCP_A", TOKEN)),),
        (TOKEN,),
    )
    cases["variable-is-shared-by-two-servers"] = (
        (env_server(SHARED_VARIABLE, "docs"), env_server(SHARED_VARIABLE, "wiki")),
        (SHARED_PART,),
    )
    cases["variable-is-written-for-an-oauth-server"] = (
        (server(mode=OAUTH, variables=(SHARED_VARIABLE,)),),
        (SHARED_PART,),
    )
    cases["variable-of-an-oauth-server-is-a-token"] = (
        (server(mode=OAUTH, variables=(TOKEN,)),),
        (TOKEN,),
    )
    for name, value in {
        "registration-name-is-a-token": TOKEN,
        "registration-name-is-orqlet-and-a-token": "orqlet-" + TOKEN,
        "registration-name-is-an-access-key": ACCESS_KEY,
    }.items():
        renamed = changed(server(), "registration", "name", value=value)
        cases[name] = ((renamed,), shown_in(value))
    cases["backend-identity-is-a-token"] = (
        (changed(server(), "data_flow", "backend_identity", value=TOKEN),),
        (TOKEN,),
    )
    cases["command-refers-to-a-token"] = (
        (stdio_server(identity={**STDIO, "command": "run ${" + TOKEN + "}"}),),
        (TOKEN,),
    )
    cases["package-refers-to-a-token"] = (
        (stdio_server(identity={**STDIO, "package": "pkg-${" + TOKEN + "}"}),),
        (TOKEN,),
    )
    several = server(
        ACCESS_KEY,
        mode=ENV_REF,
        variables=(PASSWORD,),
        identity={"kind": "remote", "url": f"https://docs.example.com/mcp?token={TOKEN}"},
    )
    cases["all-four-places-at-once"] = (
        (changed(several, "registration", "name", value=OPAQUE),),
        (ACCESS_KEY, OPAQUE, TOKEN, PASSWORD),
    )
    return cases


SECRET_CASES = secret_cases()


@parametrized("case", SECRET_CASES)
def test_no_message_of_the_contract_shows_a_part_of_the_input(
    case: tuple[tuple[dict[str, Any], ...], tuple[str, ...]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("the text of every validator error names a rule and
    holds no input value: a test places a credential-shaped string, assembled at run time, in an
    id, an address, a variable name and a registration name and requires that no error text
    contains it"), ADR-002 decision 9 ("Messages never carry a value or a raw key ... No custom
    validator formats a value") and ORQLET-SEC-003. Checked on the type, message, location and
    context that an error reports without the input, and on standard output and error."""
    servers, secrets = case

    error = refusal(*servers)
    shown = error_texts(error)
    streams = capsys.readouterr()

    assert any(rule in shown for rule in RULE_NAMES)  # a refusal names the rule that failed
    for secret in secrets:
        assert not leaks(shown, secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


@parametrized("case", SECRET_CASES)
def test_the_text_of_a_validation_error_does_not_show_the_input_either(
    case: tuple[tuple[dict[str, Any], ...], tuple[str, ...]],
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("no error text contains it") and ORQLET-SEC-003
    (never put secrets in messages). The strict reading: `str(error)` and `repr(error)` of the
    ValidationError itself, which pydantic fills with `input_value=...` unless the models hide the
    input (`hide_input_in_errors`, as `orqlet.resources/v1` does). Drop this test if only the
    fixed-text messages are meant."""
    servers, secrets = case

    error = refusal(*servers)

    for secret in secrets:
        assert not leaks(str(error), secret)
        assert not leaks(repr(error), secret)


@parametrized("case", SECRET_CASES)
def test_the_error_of_the_contract_loader_does_not_show_the_input(
    case: tuple[tuple[dict[str, Any], ...], tuple[str, ...]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-6. expected_behavior_source: AC-6 and ADR-002 decision 9 (the default error text of
    `load_contract` prints `loc` and `msg`, so a validator message that held a value would reach
    it). The document is written as JSON, which the strict loader reads as YAML."""
    servers, secrets = case
    document = json.dumps(declaration(*servers)).encode()

    with pytest.raises(DocumentError) as caught:
        load_contract(LOADER, Integrations, document, source="declaration")
    streams = capsys.readouterr()

    assert str(caught.value).strip()
    for secret in secrets:
        assert not leaks(str(caught.value), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)
