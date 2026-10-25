"""`orqlet.project-profile/v1` (proposal section 24.2)."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import Field, model_validator

from orqlet.application.contracts.common import Contract, Evidence, FactValue, SHA256Hex

TechnologyKind = Literal[
    "language",
    "runtime",
    "framework",
    "library",
    "database",
    "queue",
    "infrastructure",
    "tool",
    "other",
]


class Technology(Contract):
    """Something the project uses, with the evidence for it.

    `scope` is the directory the technology belongs to: `.` for the whole repository, a service
    folder in a monorepo. `version` is exactly as the source writes it (a range stays a range),
    or `None` when the source names no version. A scanner or an agent must cite evidence; only the
    maintainer may state a technology without it.
    """

    kind: TechnologyKind
    name: str
    version: str | None = None
    scope: str = "."
    evidence: tuple[Evidence, ...] = ()
    source: Literal["scanner", "maintainer", "agent"] = "scanner"

    @model_validator(mode="after")
    def _evidence_unless_stated_by_the_maintainer(self) -> Self:
        if self.source != "maintainer" and not self.evidence:
            raise ValueError(f"{self.name}: a technology found by a {self.source} needs evidence")
        return self


class ProjectInfo(Contract):
    uuid: str
    name: str
    kind: Literal["python-cli", "python-service", "unknown"]
    origin: Literal["existing", "existing-no-code", "unborn", "empty"]


class StackInfo(Contract):
    support: Literal["supported", "partly-covered", "unsupported", "unknown"]
    capability_limits: tuple[str, ...] = ()


class ProfileMeta(Contract):
    version: int
    status: Literal["draft", "approved"]
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class NamedFact(FactValue):
    name: str


class Facts(Contract):
    python: FactValue
    package_manager: FactValue
    frameworks: tuple[NamedFact, ...] = ()


class TargetBranch(FactValue):
    remote: str = "origin"


class PullRequestTemplate(Contract):
    targets: tuple[str, ...] = ()
    source_id: str | None = None
    status: Literal["provisioned", "team-template-unknown", "none"] = "none"


class PullRequests(Contract):
    template: PullRequestTemplate = PullRequestTemplate()
    reviewers: str = "unknown"
    merge_strategy: str = "unknown"


class Repository(Contract):
    target_branch: TargetBranch
    branch_naming: FactValue
    commit_convention: FactValue
    pull_requests: PullRequests = PullRequests()


class Dependency(Contract):
    name: str
    specifier: str = ""
    evidence: tuple[Evidence, ...] = ()


class LockedFile(Contract):
    file: str
    evidence: tuple[Evidence, ...] = ()


class Dependencies(Contract):
    declared: tuple[Dependency, ...] = ()
    locked: LockedFile | None = None


class StandardsSourceRef(Contract):
    kind: Literal["prompts-dir", "standards-pack"]
    path: str | None = None
    ref: str | None = None
    scaffold: Literal["seeded"] | None = None


class Clients(Contract):
    enabled: tuple[Literal["claude-code", "codex", "cursor"], ...]
    min_versions: dict[str, str | None] = Field(default_factory=dict)


class OrqletPin(Contract):
    version: str
    sha256: SHA256Hex | None = None


class OptionalComponents(Contract):
    exclude: tuple[str, ...] = ()


class CommandSpec(Contract):
    argv: tuple[str, ...]
    cwd: str = "."
    source: str


class ProjectProfile(Contract):
    schema_id: Literal["orqlet.project-profile/v1"] = Field(alias="schema")
    project: ProjectInfo
    stack: StackInfo
    profile: ProfileMeta
    facts: Facts
    repository: Repository
    structure: dict[str, FactValue] = Field(default_factory=dict)
    dependencies: Dependencies = Dependencies()
    auth_procedures: tuple[str, ...] = ()
    standards_sources: tuple[StandardsSourceRef, ...] = ()
    clients: Clients
    orqlet: OrqletPin
    optional_components: OptionalComponents = OptionalComponents()
    data_class: str | None = None
    commands: dict[str, CommandSpec] = Field(default_factory=dict)
    technologies: tuple[Technology, ...] = ()
    capabilities: dict[str, Any] = Field(default_factory=dict)
