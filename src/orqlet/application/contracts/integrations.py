"""`orqlet.integrations/v1` (proposal sections 15 and 24.4): per-project MCP declaration."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract, SHA256Hex

EnforcedBy = Literal["server", "client-enforced-editable", "client-managed", "none"]


class ServerIdentity(Contract):
    kind: Literal["remote", "stdio"]
    url: str | None = None
    command: str | None = None
    package: str | None = None


class Registration(Contract):
    name: str
    mode: Literal["read-only"]
    enforced_by: EnforcedBy


class PerClient(Contract):
    register_server: bool = Field(alias="register")
    enforced_by: EnforcedBy
    control: str | None = None
    decision: str | None = None
    pending: tuple[str, ...] = ()
    verification: Literal["not-tested", "verified"] = "not-tested"


class WriteTools(Contract):
    policy: Literal["deny"]
    names_verified: bool = False


class AuthSpec(Contract):
    mode: Literal["client-native-oauth", "env-ref", "none"]
    env_refs: tuple[str, ...] = ()


class DataFlow(Contract):
    backend_identity: str
    scope: tuple[str, ...]
    data_classes: tuple[str, ...]
    egress: str
    owner_review: dict[str, str | int]


class McpServer(Contract):
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


class IntegrationPolicy(Contract):
    modify_global_config: Literal["never"]
    live_inspection: Literal["opt-in"]


class RoleTools(Contract):
    servers: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()


class Integrations(Contract):
    schema_id: Literal["orqlet.integrations/v1"] = Field(alias="schema")
    project: str
    servers: tuple[McpServer, ...] = ()
    roles: dict[str, RoleTools] = Field(default_factory=dict)
    policy: IntegrationPolicy
