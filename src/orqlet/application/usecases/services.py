"""The ports that the lifecycle use cases (`init`, `upgrade`, `sync`, ...) are given."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from orqlet.application.ports.ancestors import AncestorFinder
from orqlet.application.ports.change_journal import BackupStore, ChangeJournal
from orqlet.application.ports.clock import Clock
from orqlet.application.ports.documents import DocumentLoader, DocumentWriter
from orqlet.application.ports.filesystem import FileSystem
from orqlet.application.ports.ids import IdGenerator
from orqlet.application.ports.instruction_adapter import InstructionAdapter
from orqlet.application.ports.lock import ApplyLock
from orqlet.application.ports.prompter import Prompter
from orqlet.application.ports.renderers import FileRenderers
from orqlet.application.ports.scanner import ProjectScanner, TechnologyScanner
from orqlet.application.ports.standards import StandardsSource
from orqlet.application.ports.vcs import Vcs
from orqlet.application.ports.workflow import WorkflowSource


@dataclass(frozen=True, slots=True)
class Stores:
    journal: ChangeJournal
    backups: BackupStore
    lock: ApplyLock


@dataclass(frozen=True, slots=True)
class Services:
    project: FileSystem
    vcs: Vcs
    loader: DocumentLoader
    writer: DocumentWriter
    workflow: WorkflowSource
    renderers: FileRenderers
    scanners: Sequence[ProjectScanner]
    adapters: Mapping[str, InstructionAdapter]
    stores: Callable[[str], Stores]
    prompter: Prompter
    clock: Clock
    ids: IdGenerator
    orqlet_version: str
    packs: StandardsSource | None = None
    ancestors: AncestorFinder | None = None
    technology_scanners: Sequence[TechnologyScanner] = ()
    project_label: str = "project"  # the directory name, the default project name
