"""Draft `project-profile.yaml` from what the repository says, and list what it does not say."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from orqlet.application.contracts.common import FactValue
from orqlet.application.contracts.profile import (
    Clients,
    Dependencies,
    Facts,
    OrqletPin,
    ProfileMeta,
    ProjectInfo,
    ProjectProfile,
    Repository,
    StackInfo,
    StandardsSourceRef,
    TargetBranch,
    Technology,
)
from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.application.ports.scanner import ProjectScanner, ScanResult
from orqlet.domain.paths import CanonicalPath

Origin = Literal["existing", "existing-no-code", "unborn", "empty"]
Client = Literal["claude-code", "codex", "cursor"]
ALL_CLIENTS: tuple[Client, ...] = ("claude-code", "codex", "cursor")
# Files that show a stack Orqlet M1 does not read, so the capability limit can name it.
_NEW_PROJECT_ORIGINS = frozenset({"empty", "unborn", "existing-no-code"})
_OTHER_STACKS = {
    "package.json": "JavaScript or TypeScript",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java",
    "build.gradle": "Java or Kotlin",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
}


@dataclass(frozen=True, slots=True)
class OpenQuestion:
    id: str  # the profile field the answer belongs to, for example "facts.python"
    text: str


@dataclass(frozen=True, slots=True)
class ProfileDraft:
    profile: ProjectProfile
    questions: tuple[OpenQuestion, ...]
    notes: tuple[str, ...]


def draft_profile(
    fs: FileSystem,
    scanners: Sequence[ProjectScanner],
    *,
    project_id: str,
    name: str,
    origin: Origin,
    orqlet_version: str,
    clients: tuple[Client, ...] = ALL_CLIENTS,
    technologies: Sequence[Technology] = (),
) -> ProfileDraft:
    scan = next((s.scan(fs) for s in scanners if s.applies(fs)), None)
    notes = list(scan.notes) if scan else []
    profile = ProjectProfile(
        schema_id="orqlet.project-profile/v1",
        project=ProjectInfo(
            uuid=project_id,
            name=name,
            kind=_kind(scan),
            origin=origin,
        ),
        stack=_stack(fs, scan, technologies),
        profile=ProfileMeta(version=1, status="draft"),
        facts=scan.facts if scan else _unknown_facts(),
        repository=Repository(
            target_branch=TargetBranch(question="Which branch do pull requests target?"),
            branch_naming=FactValue(question="Is there a branch naming rule?"),
            commit_convention=FactValue(question="Is there a commit message convention?"),
        ),
        dependencies=scan.dependencies if scan else Dependencies(),
        technologies=tuple(technologies),
        standards_sources=_standards_sources(fs),
        clients=Clients(enabled=clients, min_versions=dict.fromkeys(clients)),
        orqlet=OrqletPin(version=orqlet_version),
    )
    return ProfileDraft(profile, open_questions(profile), tuple(notes))


def wants_python_questions(profile: ProjectProfile) -> bool:
    """Ask about Python only when the repository root holds a Python project, or nothing is known.

    A root `Dockerfile` that builds from a Python image, a monorepo whose Python lives in service
    folders and a Go project are not asked for "the" Python version of the repository. Only a
    Python manifest at the root (a dependency list, a lock file or a version fact with evidence)
    makes the question meaningful.
    """
    has_language = any(t.kind == "language" for t in profile.technologies)
    root_python = bool(
        profile.dependencies.declared
        or profile.dependencies.locked
        or profile.facts.python.evidence
        or profile.facts.package_manager.evidence
    )
    return not has_language or root_python


def open_questions(profile: ProjectProfile) -> tuple[OpenQuestion, ...]:
    python_facts: list[tuple[str, FactValue]] = (
        [
            ("facts.python", profile.facts.python),
            ("facts.package_manager", profile.facts.package_manager),
        ]
        if wants_python_questions(profile)
        else []
    )
    fields: list[tuple[str, FactValue]] = [
        *python_facts,
        ("repository.target_branch", profile.repository.target_branch),
        ("repository.branch_naming", profile.repository.branch_naming),
        ("repository.commit_convention", profile.repository.commit_convention),
        *((f"structure.{key}", value) for key, value in sorted(profile.structure.items())),
    ]
    open_ones = [
        OpenQuestion(field, value.question or "") for field, value in fields if value.value is None
    ]
    if profile.project.kind == "unknown" and profile.project.origin in _NEW_PROJECT_ORIGINS:
        position = next(
            (i for i, q in enumerate(open_ones) if q.id.startswith("repository.")), len(open_ones)
        )
        open_ones.insert(position, OpenQuestion("project.kind", "What kind of project is it?"))
    return tuple(open_ones)


def _kind(scan: ScanResult | None) -> Literal["python-cli", "python-service", "unknown"]:
    return scan.kind if scan else "unknown"


def _stack(
    fs: FileSystem, scan: ScanResult | None, technologies: Sequence[Technology]
) -> StackInfo:
    if scan is not None:
        return StackInfo(support="supported")
    languages = sorted({t.name for t in technologies if t.kind == "language"})
    if languages:
        return StackInfo(
            support="partly-covered",
            capability_limits=(
                f"Orqlet found {', '.join(languages)} from the files and has no built-in "
                "standards for it. Rules come from the packs you supply and from the standards "
                "folder.",
            ),
        )
    seen = sorted(
        label
        for marker, label in _OTHER_STACKS.items()
        if fs.kind(CanonicalPath.parse(marker)) is FileKind.FILE
    )
    limits = ["No scanner recognised a technology in this repository."]
    if seen:
        limits.append(f"Files for {' and '.join(sorted(set(seen)))} were found and not read.")
    return StackInfo(support="unsupported" if seen else "unknown", capability_limits=tuple(limits))


def _unknown_facts() -> Facts:
    return Facts(
        python=FactValue(question="Which language and version does this project use?"),
        package_manager=FactValue(question="Which package manager does this project use?"),
    )


def _standards_sources(fs: FileSystem) -> tuple[StandardsSourceRef, ...]:
    if fs.kind(CanonicalPath.parse(".prompts")) is FileKind.DIRECTORY:
        return (StandardsSourceRef(kind="prompts-dir", path=".prompts"),)
    return ()
