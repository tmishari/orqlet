"""`orqlet.model-policy/v1` (proposal sections 14.9 and 24.1): advisory input for model pins."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract


class Compatibility(Contract):
    orqlet: str
    min_client_versions: dict[str, str | None] = Field(default_factory=dict)


class DataClass(Contract):
    id: str
    cloud_routes_allowed: bool


class Supports(Contract):
    reasoning_levels: str | None = None
    context_window: str | None = None


class DataHandling(Contract):
    allowed_data_classes: tuple[str, ...] = ()


class Observability(Contract):
    model_identity: Literal["init-and-usage", "init-only", "none", "unknown"]


class Route(Contract):
    route_id: str
    executor: Literal["claude-code", "codex", "cursor"]
    provider: str | None = None
    runtime_id: str | None = None
    alias: str | None = None
    rank: int | None = None
    price_rank: int | None = None
    retires_on: str | None = None
    options: dict[str, str] = Field(default_factory=dict)
    locality: Literal["inference-local", "inference-remote", "unknown"] = "unknown"
    data_handling: DataHandling = DataHandling()
    observability: Observability | None = None
    enabled: bool = False


class ModelEntry(Contract):
    logical_id: str
    status: Literal["proposed", "approved", "disabled", "retired"]
    approved_by: str | None = None
    supports: Supports = Supports()
    routes: tuple[Route, ...] = ()


class ProfileRequires(Contract):
    independence_from_roles: tuple[str, ...] = ()


class ModelProfile(Contract):
    id: str
    prefer: Literal["rank", "price_rank"] | None = None
    requires: ProfileRequires | None = None
    candidates: tuple[str, ...] = ()


class ModelPolicy(Contract):
    schema_id: Literal["orqlet.model-policy/v1"] = Field(alias="schema")
    policy_version: str
    status: Literal["draft", "approved"]
    owner: str
    compatibility: Compatibility
    data_classes: tuple[DataClass, ...] = ()
    models: tuple[ModelEntry, ...] = ()
    excluded: tuple[str, ...] = ()
    reviewed_at: str | None = None
    max_age_days: int | None = None
    profiles: tuple[ModelProfile, ...] = ()
    roles: dict[str, str] = Field(default_factory=dict)
