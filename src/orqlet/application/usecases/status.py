"""`orqlet status`: where the person stands and the one next step, read-only (ADR-001 decision 3).

The entry skill and the session-start hook act on this answer and nothing else, so every value is
from a closed set or follows the representability rules: what comes from a file or a path is shown
as it is, or not at all. Nothing is written and no folder is created, not even the data directory
(K-11). The command mode asks Git where the work tree is; the hook mode starts no process and is
given the project that its own search found.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from orqlet.application.contracts.common import RENDER_CLIENT_IDS, RenderClientId
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.user_scope import (
    USER_MANIFEST_PATH,
    UserHome,
    UserManifest,
)
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.executables import ExecutableLocator, OnPath
from orqlet.application.ports.filesystem import FileKind, FileSystemError, ReadOnlyFiles
from orqlet.application.ports.vcs import Vcs, VcsError, Worktree
from orqlet.application.usecases.bounded_read import BoundedReadRefused, read_bounded
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.representable import (
    PATH_NOT_REPRESENTABLE,
    representable_path,
    representable_version,
)
from orqlet.domain.versions import Version

PROJECT_FOLDER = CanonicalPath.parse(".orqlet")
WORKFLOW_LOCK = CanonicalPath.parse(".orqlet/workflow.lock")

WORKTREE_NOT_RUN = "git could not tell where the work tree is"
GIT_SKIPPED_NOT_RUN = "git was not run: PATH searches an unsafe element before git"
PROJECT_NOT_RUN = "the project folder could not be opened"
LOCK_NOT_RUN = ".orqlet/workflow.lock could not be read"
MANIFEST_NOT_RUN = "the user manifest could not be read"


class Location(StrEnum):
    NOT_A_REPOSITORY = "not-a-repository"
    REPOSITORY = "repository"
    INITIALIZED_PROJECT = "initialized-project"
    LINKED_WORKTREE = "linked-worktree"
    HOME_IS_WORK_TREE = "home-is-work-tree"


class NextStep(StrEnum):
    INSTALL_GLOBAL = "install-global"
    INIT = "init"
    UPGRADE = "upgrade"
    NONE = "none"
    REFUSE_NEWER_GLOBAL = "refuse-newer-global"
    REFUSE_LINKED_WORKTREE = "refuse-linked-worktree"
    REFUSE_HOME_IS_WORK_TREE = "refuse-home-is-work-tree"


class GlobalState(StrEnum):
    MISSING = "missing"
    CONFIGURED = "configured"
    OUTDATED = "outdated"  # the manifest's workflow version is below the installed one
    NEWER = "newer"  # above it, for example after a downgrade of the CLI


class HostStep(StrEnum):
    UNSAFE_PATH_ELEMENT = "unsafe-path-element"


@dataclass(frozen=True, slots=True)
class GlobalSources:
    user_data: ReadOnlyFiles | None  # the data directory; `None` when it does not exist
    loader: DocumentLoader
    installed: Version
    user_data_unreadable: bool = False  # it may exist, but it could not be checked


@dataclass(frozen=True, slots=True)
class StatusServices:
    sources: GlobalSources
    vcs: Vcs
    open_project: Callable[[str], ReadOnlyFiles]
    executables: ExecutableLocator
    home: UserHome


@dataclass(frozen=True, slots=True)
class StatusReport:
    clients: Mapping[RenderClientId, GlobalState]
    host_steps: tuple[HostStep, ...]
    orqlet_on_path: OnPath | None
    location: Location
    top_level: str | None
    top_level_reason: str | None
    installed: str
    project: str | None
    next: NextStep
    not_run: tuple[str, ...]

    def to_data(self) -> dict[str, object]:
        return {
            "global": {
                "clients": {client: str(self.clients[client]) for client in RENDER_CLIENT_IDS},
                "host_steps": [str(step) for step in self.host_steps],
            },
            "orqlet_on_path": None if self.orqlet_on_path is None else str(self.orqlet_on_path),
            "location": str(self.location),
            "top_level": self.top_level,
            "top_level_reason": self.top_level_reason,
            "versions": {"installed": self.installed, "project": self.project},
            "next": str(self.next),
        }


@dataclass(frozen=True, slots=True)
class _Place:
    location: Location
    top_level: str | None = None
    top_level_reason: str | None = None
    project: str | None = None
    not_run: tuple[str, ...] = ()


def read_status(services: StatusServices) -> StatusReport:
    """The command mode: Git locates the work tree, `PATH` locates `orqlet`."""
    place = _locate(services)
    lookup = services.executables.locate("orqlet")
    steps = (HostStep.UNSAFE_PATH_ELEMENT,) if lookup.unsafe_element_searched else ()
    return _report(services.sources, place, steps, lookup.on_path)


def read_project_status(sources: GlobalSources, project: ReadOnlyFiles) -> StatusReport:
    """The hook mode: the project is already found, and no process is started."""
    version, not_run = _project_version(project, sources.loader)
    place = _Place(Location.INITIALIZED_PROJECT, project=version, not_run=not_run)
    return _report(sources, place, (), None)


def _report(
    sources: GlobalSources,
    place: _Place,
    steps: tuple[HostStep, ...],
    on_path: OnPath | None,
) -> StatusReport:
    clients, manifest_not_run = _global_states(sources)
    return StatusReport(
        clients=clients,
        host_steps=steps,
        orqlet_on_path=on_path,
        location=place.location,
        top_level=place.top_level,
        top_level_reason=place.top_level_reason,
        installed=str(sources.installed),
        project=place.project,
        next=_next_step(clients, place, sources.installed),
        not_run=place.not_run + manifest_not_run,
    )


def _locate(services: StatusServices) -> _Place:
    if services.executables.searches_unsafe("git"):
        return _Place(Location.NOT_A_REPOSITORY, not_run=(GIT_SKIPPED_NOT_RUN,))
    try:
        worktree = services.vcs.worktree()
    except VcsError:
        return _Place(Location.NOT_A_REPOSITORY, not_run=(WORKTREE_NOT_RUN,))
    if worktree is None:
        return _Place(Location.NOT_A_REPOSITORY)
    shown = representable_path(worktree.top_level)
    reason = None if shown is not None else PATH_NOT_REPRESENTABLE
    location, version, not_run = _classify(services, worktree)
    return _Place(
        location, top_level=shown, top_level_reason=reason, project=version, not_run=not_run
    )


def _classify(
    services: StatusServices, worktree: Worktree
) -> tuple[Location, str | None, tuple[str, ...]]:
    if worktree.linked:
        return Location.LINKED_WORKTREE, None, ()
    if _same_or_below(services.home.path, worktree.top_level):
        return Location.HOME_IS_WORK_TREE, None, ()
    try:
        project = services.open_project(worktree.top_level)
        kind = project.kind(PROJECT_FOLDER)
    except (FileSystemError, OSError):  # the local file system lets a refused permission through
        return Location.REPOSITORY, None, (PROJECT_NOT_RUN,)
    if kind is None:
        return Location.REPOSITORY, None, ()
    if kind is not FileKind.DIRECTORY:
        return Location.INITIALIZED_PROJECT, None, (LOCK_NOT_RUN,)
    version, not_run = _project_version(project, services.sources.loader)
    return Location.INITIALIZED_PROJECT, version, not_run


def _same_or_below(path: str, folder: str) -> bool:
    if path == folder:
        return True
    return any(path.startswith(folder.rstrip(sep) + sep) for sep in ("/", "\\"))


def _project_version(
    project: ReadOnlyFiles, loader: DocumentLoader
) -> tuple[str | None, tuple[str, ...]]:
    """The lock's workflow version when representable; an unreadable lock is a check not run."""
    try:
        content = read_bounded(project, WORKFLOW_LOCK)
        if content is None:
            return None, ()
        parsed = loader.load(content, source=str(WORKFLOW_LOCK))
    except (BoundedReadRefused, FileSystemError, OSError, DocumentError):
        return None, (LOCK_NOT_RUN,)
    if not isinstance(parsed, Mapping):
        return None, (LOCK_NOT_RUN,)
    return representable_version(parsed.get("workflow_version")), ()


def _global_states(
    sources: GlobalSources,
) -> tuple[dict[RenderClientId, GlobalState], tuple[str, ...]]:
    missing = dict.fromkeys(RENDER_CLIENT_IDS, GlobalState.MISSING)
    if sources.user_data_unreadable:
        return missing, (MANIFEST_NOT_RUN,)
    if sources.user_data is None:
        return missing, ()
    try:
        content = read_bounded(sources.user_data, USER_MANIFEST_PATH)
        if content is None:
            return missing, ()
        manifest = load_contract(
            sources.loader, UserManifest, content, source=str(USER_MANIFEST_PATH)
        )
    except (BoundedReadRefused, FileSystemError, OSError, DocumentError):
        return missing, (MANIFEST_NOT_RUN,)
    return {
        client: _client_state(manifest, client, sources.installed) for client in RENDER_CLIENT_IDS
    }, ()


def _client_state(
    manifest: UserManifest, client: RenderClientId, installed: Version
) -> GlobalState:
    versions = [
        Version.parse(entry.workflow_version)
        for entry in manifest.entries
        if client in entry.owners
    ]
    if not versions:
        return GlobalState.MISSING
    if any(version > installed for version in versions):
        return GlobalState.NEWER
    if any(version < installed for version in versions):
        return GlobalState.OUTDATED
    return GlobalState.CONFIGURED


def _next_step(
    clients: Mapping[RenderClientId, GlobalState], place: _Place, installed: Version
) -> NextStep:
    """The person's answer to the P-4 status questions: the first rule that matches wins."""
    states = set(clients.values())
    if GlobalState.NEWER in states:
        return NextStep.REFUSE_NEWER_GLOBAL
    if place.location is Location.LINKED_WORKTREE:
        return NextStep.REFUSE_LINKED_WORKTREE
    if place.location is Location.HOME_IS_WORK_TREE:
        return NextStep.REFUSE_HOME_IS_WORK_TREE
    if states == {GlobalState.MISSING} or GlobalState.OUTDATED in states:
        return NextStep.INSTALL_GLOBAL
    if place.location is Location.NOT_A_REPOSITORY:
        return NextStep.NONE
    if place.location is Location.REPOSITORY:
        return NextStep.INIT
    if place.project is None or Version.parse(place.project) < installed:
        return NextStep.UPGRADE
    return NextStep.NONE
