"""`orqlet.knowledge/v2` (`.orqlet/knowledge.yaml`) and `orqlet.docs-map/v1` (proposal 24.9).

The configuration says which committed files hold shared knowledge and where a plan's
`knowledge_scope` may write drafts. The `index` block belongs to M3; it is accepted and ignored.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from orqlet.application.contracts.common import Contract, Glob, RepoPath

SourceKind = Literal["adr", "module-card", "docs", "standards-reference"]
WriteKind = Literal["adr", "module-card", "docs"]


class KnowledgeSource(Contract):
    kind: SourceKind
    scope: Literal["project", "team", "company"]
    globs: tuple[Glob, ...] = ()
    pack: str | None = None  # for a `standards-reference` read from a hash-verified pack


class WriteScope(Contract):
    globs: tuple[Glob, ...] = Field(min_length=1)
    kinds: tuple[WriteKind, ...] = Field(min_length=1)


class IndexConfig(Contract):
    views: tuple[str, ...] = ()
    target_branch_ref: str | None = None
    tokenizer: str | None = None
    refresh_policy: Literal["manual", "warn", "refresh-local-only"] | None = None
    generations_kept: int | None = Field(default=None, ge=1)


class KnowledgeConfig(Contract):
    schema_id: Literal["orqlet.knowledge/v2"] = Field(alias="schema")
    sources: tuple[KnowledgeSource, ...] = ()
    exclude: tuple[Glob, ...] = ()
    write_scope: tuple[WriteScope, ...] = ()
    index: IndexConfig | None = None


class DocsTarget(Contract):
    path: RepoPath
    anchors: tuple[str, ...] = ()
    kind: Literal["hand-written", "generated"] = "hand-written"


class DocsMapEntry(Contract):
    code: tuple[str, ...] = Field(min_length=1)  # a path glob or a symbol
    docs: tuple[DocsTarget, ...] = Field(min_length=1)
    owner: str = Field(min_length=1)


class DocsMap(Contract):
    """One more source of candidates. It never waives the knowledge step."""

    schema_id: Literal["orqlet.docs-map/v1"] = Field(alias="schema")
    targets: tuple[DocsMapEntry, ...] = ()
