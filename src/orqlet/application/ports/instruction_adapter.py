"""One adapter per AI client. Adapters do not know about each other (client independence)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath


@dataclass(frozen=True, slots=True)
class RenderedFile:
    """One file a renderer wants on disk.

    For `SHARED_BLOCK` the content is the block alone (marker lines included), to be merged into
    a file the project owns. For `SEEDED` the content is written once and never touched again.
    """

    path: CanonicalPath
    content: bytes
    owner: OwnerMode
    file_class: FileClass | None
    inputs: tuple[tuple[str, str, str], ...] = ()  # (id, version, sha256) of what it was made from
    block: tuple[str, str] | None = None  # (begin, end) marker lines of a shared block
    entry: str | None = None  # entry name of a shared-entry file


@dataclass(frozen=True, slots=True)
class CapabilityLimit:
    """A thing this client cannot enforce or that is not verified, so no one assumes it is."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ScopedRule:
    """A rule that applies to some paths. Clients that read path-scoped rules get a file for it."""

    name: str  # lower case letters, digits and hyphens; the file is `orqlet-<name>`
    description: str
    paths: tuple[str, ...]
    body: str
    file_class: FileClass
    inputs: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ClientCommand:
    """A prompt the user starts from the client's `/` menu. Clients without commands skip it."""

    name: str  # lower case letters, digits and hyphens; the file is `orqlet-<name>`
    description: str
    body: str
    inputs: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ClientSkill:
    """A workflow skill. The steps whose commands this release lacks are already left out."""

    name: str  # the directory and the `name` field: `orqlet-<phase>`
    description: str
    body: str
    references: tuple[tuple[str, str], ...] = ()  # (file name, text) of `references/<file>`
    inputs: tuple[tuple[str, str, str], ...] = ()  # (id, version, sha256) of the skill text
    agent_may_start: bool = False  # True: the agent may start it; a workflow skill is person-only


@dataclass(frozen=True, slots=True)
class ClientRole:
    """A subagent definition. Role files never name a vendor model."""

    name: str
    description: str
    body: str
    read_only: bool = True
    inputs: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ConventionsView:
    """The finished lines of the conventions block of `AGENTS.md`, and the registry's size."""

    lines: tuple[str, ...]
    resources: int


@dataclass(frozen=True, slots=True)
class RenderRequest:
    """Everything an adapter needs, already resolved: it never re-reads the profile or packs."""

    workflow_version: str
    baseline_body: str
    scoped_rules: tuple[ScopedRule, ...] = ()
    commands: tuple[ClientCommand, ...] = ()
    skills: tuple[ClientSkill, ...] = ()
    roles: tuple[ClientRole, ...] = ()
    client_version: str | None = None  # recorded when known; no floor is assumed (spike S-21)
    conventions: ConventionsView | None = None  # None: no convention answered, no link registered


@dataclass(frozen=True, slots=True)
class RenderResult:
    files: tuple[RenderedFile, ...]
    limits: tuple[CapabilityLimit, ...] = ()


class InstructionAdapter(Protocol):
    client_id: str

    def render(self, request: RenderRequest) -> RenderResult:
        """Produce the files this client reads. Deterministic: same request, same bytes."""
        ...
