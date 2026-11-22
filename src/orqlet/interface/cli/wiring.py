"""The composition root: the only place that picks concrete adapters."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import platformdirs

from orqlet import __version__
from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.ancestors import FsAncestorFinder
from orqlet.adapters.fs.apply_lock import FileApplyLock
from orqlet.adapters.fs.journal import FsBackupStore, FsChangeJournal
from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.adapters.prompt.tty_prompter import TtyPrompter
from orqlet.adapters.render.emit import YamlWriter
from orqlet.adapters.render.renderers import PackagedRenderers
from orqlet.adapters.scan.executables import PathExecutableLocator
from orqlet.adapters.scan.python_scanner import PythonScanner
from orqlet.adapters.scan.technology_scanners import (
    ContainerScanner,
    GoScanner,
    NodeScanner,
    PythonTechnologyScanner,
    RustScanner,
)
from orqlet.adapters.standards.pack_source import DirectoryPackSource
from orqlet.adapters.system import SystemClock, UuidGenerator
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.user_scope import UserHome
from orqlet.application.ports.documents import DocumentLoader
from orqlet.application.ports.filesystem import FileSystemError
from orqlet.application.ports.scanner import ProjectScanner, TechnologyScanner
from orqlet.application.usecases.models_resolve import ModelsServices
from orqlet.application.usecases.services import Services as LifecycleServices
from orqlet.application.usecases.services import Stores
from orqlet.application.usecases.status import GlobalSources, StatusServices
from orqlet.application.usecases.validate_model_policy import ModelPolicyServices
from orqlet.application.usecases.validation import ValidateServices

DATA_DIR_VARIABLE = "ORQLET_DATA_DIR"


@dataclass(frozen=True, slots=True)
class Services:
    project: LocalFileSystem
    loader: DocumentLoader
    scanners: tuple[ProjectScanner, ...]
    technology_scanners: tuple[TechnologyScanner, ...]


def build_services(root: Path) -> Services:
    return Services(
        project=LocalFileSystem(root),
        loader=StrictYamlLoader(),
        scanners=(PythonScanner(),),
        technology_scanners=technology_scanners(),
    )


def technology_scanners() -> tuple[TechnologyScanner, ...]:
    """The scanner plug-ins, one per ecosystem. Adding an ecosystem is adding one class here."""
    return (
        PythonTechnologyScanner(),
        GoScanner(),
        RustScanner(),
        NodeScanner(),
        ContainerScanner(),
    )


def resolve_data_directory() -> Path:
    """Where the data directory is. Nothing is created, so `status` and the hooks can use it."""
    override = os.environ.get(DATA_DIR_VARIABLE)
    return Path(override) if override else Path(platformdirs.user_data_dir("orqlet"))


def data_directory() -> Path:
    """Where journals and backups live: the user's data directory, never the repository."""
    directory = resolve_data_directory()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def build_status_services(root: Path) -> StatusServices:
    """Read-only services: no folder is opened for writing and none is created (K-11)."""
    resolved_root = root.resolve(strict=True)
    user_data, unreadable = _open_user_data(resolve_data_directory())
    loader = StrictYamlLoader()
    return StatusServices(
        sources=GlobalSources(
            user_data=user_data,
            loader=loader,
            installed=PackagedWorkflow().release.version,
            user_data_unreadable=unreadable,
        ),
        vcs=GitVcs(SubprocessRunner(), resolved_root),
        open_project=lambda top_level: LocalFileSystem(Path(top_level)),
        executables=PathExecutableLocator(
            os.environ.get("PATH", ""),
            _running_executable(),
            pathext=os.environ.get("PATHEXT"),
        ),
        home=UserHome(path=os.path.realpath(Path.home())),
    )


def _open_user_data(data: Path) -> tuple[LocalFileSystem | None, bool]:
    """The data directory and whether it could not be checked; only a missing one is `None`."""
    try:
        return LocalFileSystem(data), False
    except (FileNotFoundError, NotADirectoryError):
        return None, False
    except (FileSystemError, OSError):
        return None, True


def _running_executable() -> str | None:
    launched = sys.argv[0] if sys.argv else ""
    return launched if os.path.isabs(launched) and os.path.isfile(launched) else None


def build_packet_store() -> tuple[LocalFileSystem, Path]:
    """Where review packets go: the user's data directory, never the repository."""
    folder = data_directory() / "packets"
    folder.mkdir(parents=True, exist_ok=True)
    return LocalFileSystem(folder), folder


def build_validate_services(root: Path) -> ValidateServices:
    """What the validators need: the project's files, its Git history, the strict loader."""
    resolved_root = root.resolve(strict=True)
    return ValidateServices(
        project=LocalFileSystem(resolved_root),
        vcs=GitVcs(SubprocessRunner(), resolved_root),
        loader=StrictYamlLoader(),
        workflow=PackagedWorkflow(),
    )


def build_model_policy_services(root: Path) -> ModelPolicyServices:
    """The ports of the other validators, and the system clock for the retirement dates."""
    validators = build_validate_services(root)
    return ModelPolicyServices(
        project=validators.project,
        vcs=validators.vcs,
        loader=validators.loader,
        workflow=validators.workflow,
        clock=SystemClock(),
    )


def build_models_services(root: Path) -> ModelsServices:
    """What `models resolve` needs: the project's files, the strict loader, the workflow.

    It builds no Git adapter, no process runner and no clock: the command can make no git call.
    """
    return ModelsServices(
        project=LocalFileSystem(root.resolve(strict=True)),
        loader=StrictYamlLoader(),
        workflow=PackagedWorkflow(),
    )


def build_init_services(root: Path, packs_dir: Path | None) -> LifecycleServices:
    loader = StrictYamlLoader()
    data_path = data_directory()
    data = LocalFileSystem(data_path)
    resolved_root = root.resolve(strict=True)
    return LifecycleServices(
        project=LocalFileSystem(resolved_root),
        vcs=GitVcs(SubprocessRunner(), resolved_root),
        loader=loader,
        writer=YamlWriter(),
        workflow=PackagedWorkflow(),
        renderers=PackagedRenderers(),
        scanners=(PythonScanner(),),
        technology_scanners=technology_scanners(),
        adapters={
            "claude-code": ClaudeCodeAdapter(),
            "codex": CodexAdapter(),
            "cursor": CursorAdapter(),
        },
        stores=lambda project_id: Stores(
            FsChangeJournal(data, project_id),
            FsBackupStore(data, project_id),
            FileApplyLock(data_path / "projects" / project_id / "apply.lock"),
        ),
        prompter=TtyPrompter(sys.stdin, sys.stdout),
        clock=SystemClock(),
        ids=UuidGenerator(),
        orqlet_version=__version__,
        packs=(
            None
            if packs_dir is None
            else DirectoryPackSource(LocalFileSystem(packs_dir), loader, label="packs-dir")
        ),
        ancestors=FsAncestorFinder(resolved_root),
        project_label=resolved_root.name,
    )
