"""Everything an `init` test needs, wired to fakes and the real packaged workflow."""

from __future__ import annotations

from dataclasses import dataclass, field

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.journal import FsBackupStore, FsChangeJournal
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
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
from orqlet.application.ports.vcs import RepoState
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.init_project import InitServices, Stores
from orqlet.domain.paths import CanonicalPath
from tests.fakes.clock import FixedClock
from tests.fakes.ids import SequentialIds
from tests.fakes.lock import NoLock
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.prompter import ScriptedPrompter
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED

ORQLET_VERSION = "0.1.0"


@dataclass
class Env:
    project: MemoryFileSystem
    user_data: MemoryFileSystem = field(default_factory=MemoryFileSystem)
    vcs: FakeVcs = field(default_factory=FakeVcs)
    prompter: ScriptedPrompter = field(default_factory=lambda: ScriptedPrompter(interactive=False))
    packs: MemoryFileSystem | None = None
    ancestors: tuple[str, ...] = ()
    project_view: FileSystem | None = None  # e.g. a crashing wrapper around `project`
    ids: IdGenerator = field(default_factory=SequentialIds)
    workflow: WorkflowSource | None = None
    orqlet_version: str = ORQLET_VERSION

    def services(self) -> InitServices:
        loader = StrictYamlLoader()
        user_data = self.user_data
        return InitServices(
            project=self.project_view or self.project,
            vcs=self.vcs,
            loader=loader,
            writer=YamlWriter(),
            workflow=self.workflow or PINNED,
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
                FsChangeJournal(user_data, project_id),
                FsBackupStore(user_data, project_id),
                NoLock(),
            ),
            prompter=self.prompter,
            clock=FixedClock(),
            ids=self.ids,
            orqlet_version=self.orqlet_version,
            packs=None if self.packs is None else DirectoryPackSource(self.packs, loader),
            ancestors=_Ancestors(self.ancestors) if self.ancestors else None,
            project_label="demo",
        )


class _Ancestors:
    def __init__(self, found: tuple[str, ...]) -> None:
        self._found = found

    def find(self) -> tuple[str, ...]:
        return self._found


def git_repo(state: RepoState = RepoState.HAS_COMMITS) -> FakeVcs:
    return FakeVcs(state)


def tree(fs: MemoryFileSystem) -> dict[str, bytes]:
    """Every file of the project, by path, for comparing whole trees."""
    return fs.snapshot()


def read(fs: MemoryFileSystem, path: str) -> str:
    return fs.read_bytes(CanonicalPath.parse(path)).decode("utf-8")
