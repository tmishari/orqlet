"""The protected workflow that ships inside the Orqlet release."""

from __future__ import annotations

from typing import Protocol

from orqlet.domain.versions import WorkflowRelease


class WorkflowSource(Protocol):
    @property
    def release(self) -> WorkflowRelease:
        """Version, digest and controls level of this release."""
        ...

    def read_text(self, path: str) -> str:
        """The UTF-8 text of one workflow file, by its path below the workflow root."""
        ...

    def paths(self) -> tuple[str, ...]:
        """Every file the manifest lists, sorted by code point."""
        ...

    def problems(self) -> tuple[str, ...]:
        """Differences between the files and the manifest. Empty when the package is intact."""
        ...
