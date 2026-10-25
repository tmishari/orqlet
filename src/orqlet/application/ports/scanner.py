"""Reading a project to produce facts. Implementations only read through the file system port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from orqlet.application.contracts.profile import Dependencies, Facts, Technology
from orqlet.application.ports.filesystem import FileSystem
from orqlet.domain.paths import CanonicalPath


@dataclass(frozen=True, slots=True)
class ScanResult:
    language: str
    facts: Facts
    dependencies: Dependencies
    kind: Literal["python-cli", "python-service", "unknown"]
    notes: tuple[str, ...] = ()  # things the scan could not read, in plain words


class ProjectScanner(Protocol):
    language: str

    def applies(self, fs: FileSystem) -> bool:
        """True when this scanner recognises the project's language from its files."""
        ...

    def scan(self, fs: FileSystem) -> ScanResult:
        """Read manifests and configuration; never run project code or install anything."""
        ...


class TechnologyScanner(Protocol):
    """Finds technologies in one directory. One plug-in per ecosystem."""

    name: str

    def scan(self, fs: FileSystem, scope: CanonicalPath | None) -> tuple[Technology, ...]:
        """Read the manifests in `scope` (the root when `None`); never run or install anything."""
        ...
