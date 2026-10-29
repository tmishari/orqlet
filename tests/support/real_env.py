"""`init` wired to the real adapters on temporary directories, for integration and fault tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from orqlet import __version__
from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.ancestors import FsAncestorFinder
from orqlet.adapters.fs.journal import FsBackupStore, FsChangeJournal
from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.adapters.render.emit import YamlWriter
from orqlet.adapters.render.renderers import PackagedRenderers
from orqlet.adapters.scan.python_scanner import PythonScanner
from orqlet.adapters.scan.technology_scanners import (
    ContainerScanner,
    GoScanner,
    NodeScanner,
    PythonTechnologyScanner,
    RustScanner,
)
from orqlet.adapters.standards.pack_source import DirectoryPackSource
from orqlet.application.ports.filesystem import FileSystem
from orqlet.application.ports.ids import IdGenerator
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.init_project import InitServices, Stores
from tests.fakes.clock import FixedClock
from tests.fakes.ids import SequentialIds
from tests.fakes.lock import NoLock
from tests.fakes.prompter import ScriptedPrompter
from tests.fakes.workflow import PINNED
from tests.support.git import clean_environ


def real_services(
    root: Path,
    data_dir: Path,
    *,
    wrap_project: Callable[[FileSystem], FileSystem] | None = None,
    ids: IdGenerator | None = None,
    packs_dir: Path | None = None,
    workflow: WorkflowSource | None = None,
    orqlet_version: str = __version__,
) -> InitServices:
    loader = StrictYamlLoader()
    data_dir.mkdir(parents=True, exist_ok=True)
    data = LocalFileSystem(data_dir)
    project: FileSystem = LocalFileSystem(root)
    if wrap_project is not None:
        project = wrap_project(project)
    return InitServices(
        project=project,
        vcs=GitVcs(SubprocessRunner(), root, environ=clean_environ(root.parent)),
        loader=loader,
        writer=YamlWriter(),
        workflow=workflow or PINNED,
        renderers=PackagedRenderers(),
        scanners=(PythonScanner(),),
        technology_scanners=(
            PythonTechnologyScanner(),
            GoScanner(),
            RustScanner(),
            NodeScanner(),
            ContainerScanner(),
        ),
        adapters={
            "claude-code": ClaudeCodeAdapter(),
            "codex": CodexAdapter(),
            "cursor": CursorAdapter(),
        },
        stores=lambda project_id: Stores(
            FsChangeJournal(data, project_id), FsBackupStore(data, project_id), NoLock()
        ),
        prompter=ScriptedPrompter(interactive=False),
        clock=FixedClock(),
        ids=ids or SequentialIds(),
        orqlet_version=orqlet_version,
        packs=None
        if packs_dir is None
        else DirectoryPackSource(LocalFileSystem(packs_dir), loader),
        ancestors=FsAncestorFinder(root),
        project_label=root.name,
    )


def snapshot(root: Path) -> dict[str, bytes]:
    """Every regular file below `root`, by relative POSIX path, skipping `.git`."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }
