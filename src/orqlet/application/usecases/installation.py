"""Reading an installed Orqlet setup: the manifest, the profile and the version files."""

from __future__ import annotations

from dataclasses import dataclass

from orqlet.application.contracts.common import Contract
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.contracts.standards_lock import StandardsLock
from orqlet.application.contracts.versions_file import Versions
from orqlet.application.contracts.workflow_package import Released, WorkflowLock
from orqlet.application.ports.filesystem import FileKind
from orqlet.application.usecases.init_files import recorded_from_lock
from orqlet.application.usecases.render_all import (
    LOCK_PATH,
    PROFILE_PATH,
    RELEASED_PATH,
    STANDARDS_LOCK_PATH,
    VERSIONS_PATH,
    WORKFLOW_LOCK_PATH,
)
from orqlet.application.usecases.services import Services
from orqlet.domain.changeplan import Recorded
from orqlet.domain.errors import OrqletError
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.versions import Version, WorkflowRelease


class NotInitialised(OrqletError):
    """The directory has no Orqlet manifest. Run `orqlet init` first."""


@dataclass(frozen=True, slots=True)
class Installation:
    lock: GeneratedLock
    profile: ProjectProfile
    versions: Versions | None
    workflow_lock: WorkflowLock | None
    standards_lock: StandardsLock | None
    released: frozenset[str]

    @property
    def recorded(self) -> list[Recorded]:
        return recorded_from_lock(self.lock)

    @property
    def installed_release(self) -> WorkflowRelease | None:
        if self.workflow_lock is None:
            return None
        return WorkflowRelease(
            Version.parse(self.workflow_lock.workflow_version),
            self.workflow_lock.workflow_digest,
            self.workflow_lock.controls_level,
        )

    @property
    def floor(self) -> Version | None:
        return None if self.versions is None else Version.parse(self.versions.workflow.floor)


def load_installation(services: Services) -> Installation:
    """Read every file an installation consists of. Raises `NotInitialised` without a manifest."""
    project = services.project
    if project.kind(LOCK_PATH) is not FileKind.FILE:
        raise NotInitialised(
            "This directory has no Orqlet manifest (.orqlet/generated.lock.yaml). "
            "Run `orqlet init` first."
        )

    lock = _read_required(services, LOCK_PATH, GeneratedLock)
    profile = _read_optional(services, PROFILE_PATH, ProjectProfile)
    if profile is None:
        raise NotInitialised("The project profile (.orqlet/project-profile.yaml) is missing.")
    released = _read_optional(services, RELEASED_PATH, Released)
    return Installation(
        lock=lock,
        profile=profile,
        versions=_read_optional(services, VERSIONS_PATH, Versions),
        workflow_lock=_read_optional(services, WORKFLOW_LOCK_PATH, WorkflowLock),
        standards_lock=_read_optional(services, STANDARDS_LOCK_PATH, StandardsLock),
        released=frozenset() if released is None else frozenset(f.path for f in released.files),
    )


def _read_optional[T: Contract](
    services: Services, path: CanonicalPath, model: type[T]
) -> T | None:
    if services.project.kind(path) is not FileKind.FILE:
        return None
    return load_contract(
        services.loader, model, services.project.read_bytes(path), source=str(path)
    )


def _read_required[T: Contract](services: Services, path: CanonicalPath, model: type[T]) -> T:
    found = _read_optional(services, path, model)
    if found is None:
        raise NotInitialised(f"{path} is missing.")
    return found
