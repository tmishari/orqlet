"""`orqlet.integrations/v1` (proposal sections 15 and 24.4): per-project MCP declaration.

The rules of ADR-002 decisions 1, 3, 4, 5 and 10 are validators, not field patterns, so the
committed JSON Schema shows the structure only and the patterns stay private to
`orqlet.domain.mcp_credentials`. Every message of a validator names a rule and never holds a
value: a declaration is untrusted input and a value in it may be a credential pasted into the
wrong place. The location of an error can still hold the raw key of a free-form map; the loader
maps each error to a rule and a closed field name before anything is printed (ADR-002 decision 9).
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import ConfigDict, Field, model_validator

from orqlet.application.contracts.common import Contract, SHA256Hex
from orqlet.domain.mcp_credentials import name_problems

EnforcedBy = Literal["server", "client-enforced-editable", "client-managed", "none"]

_OAUTH = "client-native-oauth"
_ENV_REF = "env-ref"
# One label per authentication mode (ADR-002 decision 1): a label that restricts nothing else.
_BACKEND_IDENTITY = {_OAUTH: "user-oauth", _ENV_REF: "user-token"}
_ADDRESS_RULE = "address-literal-https"
# Pydantic merges this into the closed config of `Contract`: an error never repeats the input.
_HIDE_INPUT = ConfigDict(hide_input_in_errors=True)


class ServerIdentity(Contract):
    model_config = _HIDE_INPUT

    kind: Literal["remote", "stdio"]
    url: str | None = None
    command: str | None = None
    package: str | None = None


class Registration(Contract):
    model_config = _HIDE_INPUT

    name: str
    mode: Literal["read-only"]
    enforced_by: EnforcedBy


class PerClient(Contract):
    model_config = _HIDE_INPUT

    register_server: bool = Field(alias="register")
    enforced_by: EnforcedBy
    control: str | None = None
    decision: str | None = None
    pending: tuple[str, ...] = ()
    verification: Literal["not-tested", "verified"] = "not-tested"


class WriteTools(Contract):
    model_config = _HIDE_INPUT

    policy: Literal["deny"]
    names_verified: bool = False


class AuthSpec(Contract):
    model_config = _HIDE_INPUT

    mode: Literal["client-native-oauth", "env-ref", "none"]
    env_refs: tuple[str, ...] = ()


class DataFlow(Contract):
    model_config = _HIDE_INPUT

    backend_identity: str
    scope: tuple[str, ...]
    data_classes: tuple[str, ...]
    egress: str
    owner_review: dict[str, str | int]


class McpServer(Contract):
    model_config = _HIDE_INPUT

    id: str
    purpose: str
    identity: ServerIdentity
    expected_publisher: str
    capability_tier: Literal["read", "write", "destructive"]
    registration: Registration
    per_client: dict[str, PerClient] = Field(default_factory=dict)
    write_tools: WriteTools
    auth: AuthSpec
    data_flow: DataFlow
    tools_digest: SHA256Hex | None = None
    clients: tuple[Literal["claude-code", "codex", "cursor"], ...] = ()

    @model_validator(mode="after")
    def _keeps_the_rules(self) -> Self:
        broken = _unique(
            [
                *self._name_rules(),
                *self._identity_rules(),
                *self._authentication_rules(),
                *self._label_rules(),
                *self._registration_rules(),
            ]
        )
        if broken:
            raise ValueError(f"the server breaks the rules {', '.join(broken)}")
        return self

    def _registered(self) -> frozenset[str]:
        return frozenset(name for name, entry in self.per_client.items() if entry.register_server)

    def _name_rules(self) -> list[str]:
        """The id, the address and each variable name, by the one function that owns the patterns.

        A stdio server has no address, so it passes an empty one and the address rule is dropped.
        """
        found = [] if self.registration.name == f"orqlet-{self.id}" else ["registration-name"]
        stdio = self.identity.kind == "stdio"
        address = "" if stdio else (self.identity.url or "")
        for variable in self.auth.env_refs or (None,):
            problems = name_problems(self.id, address, variable)
            found += [rule for rule in problems if not (stdio and rule == _ADDRESS_RULE)]
        return found

    def _identity_rules(self) -> list[str]:
        found = []
        if "${" in (self.identity.command or ""):
            found.append("reference-in-command")
        if "${" in (self.identity.package or ""):
            found.append("reference-in-package")
        return found

    def _authentication_rules(self) -> list[str]:
        found = []
        mode, names = self.auth.mode, self.auth.env_refs
        if (mode == _ENV_REF and len(names) != 1) or (mode == _OAUTH and names):
            found.append("env-refs-count")
        if mode == "none" and self._registered():
            found.append("auth-mode-none")
        wanted = _BACKEND_IDENTITY.get(mode)
        if wanted is not None and self.data_flow.backend_identity != wanted:
            found.append("backend-identity")
        return found

    def _label_rules(self) -> list[str]:
        """Labels that say only what holds: no server-side limit exists, and nothing is verified."""
        found = []
        labels = [self.registration.enforced_by, *(e.enforced_by for e in self.per_client.values())]
        if "server" in labels:
            found.append("enforced-by-server")
        if self.capability_tier != "read" and "none" in labels:
            found.append("enforced-by-none")
        if any(entry.verification == "verified" for entry in self.per_client.values()):
            found.append("verification-verified")
        return found

    def _registration_rules(self) -> list[str]:
        found = []
        registered = self._registered()
        if registered and self.identity.kind == "stdio":
            found.append("stdio-registered")
        if not registered <= set(self.clients):
            found.append("clients-omit-registered")
        return found


class IntegrationPolicy(Contract):
    model_config = _HIDE_INPUT

    modify_global_config: Literal["never"]
    live_inspection: Literal["opt-in"]


class RoleTools(Contract):
    model_config = _HIDE_INPUT

    servers: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()


class Integrations(Contract):
    model_config = _HIDE_INPUT

    schema_id: Literal["orqlet.integrations/v1"] = Field(alias="schema")
    project: str
    servers: tuple[McpServer, ...] = ()
    roles: dict[str, RoleTools] = Field(default_factory=dict)
    policy: IntegrationPolicy

    @model_validator(mode="after")
    def _keeps_the_rules_between_servers(self) -> Self:
        ids = [server.id for server in self.servers]
        names = [name for server in self.servers for name in server.auth.env_refs]
        broken = []
        if len(set(ids)) != len(ids):
            broken.append("server-id-repeated")
        if len(set(names)) != len(names):
            broken.append("variable-shared")
        if broken:
            raise ValueError(f"the declaration breaks the rules {', '.join(broken)}")
        return self

    def registered_for(self, client: str) -> tuple[McpServer, ...]:
        """The servers whose entry for `client` says `register: true`, in declaration order."""
        return tuple(
            server
            for server in self.servers
            if (entry := server.per_client.get(client)) is not None and entry.register_server
        )


def _unique(items: list[str]) -> list[str]:
    """The items without repeats, in the order of first appearance."""
    return list(dict.fromkeys(items))
