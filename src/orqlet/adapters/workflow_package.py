"""The protected workflow, read from the installed `orqlet.workflow` package data."""

from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.workflow_package import (
    ReleaseHistory,
    WorkflowManifest,
)
from orqlet.application.usecases.workflow_manifest import (
    is_listed,
    manifest_digest,
    manifest_problems,
)
from orqlet.domain.versions import Version, WorkflowRelease

_LOADER = StrictYamlLoader()


class PackagedWorkflow:
    def __init__(self, root: Traversable | None = None) -> None:
        self._root = root if root is not None else files("orqlet.workflow")
        self._manifest = load_contract(
            _LOADER,
            WorkflowManifest,
            self._root.joinpath("MANIFEST.json").read_bytes(),
            source="MANIFEST.json",
        )

    @property
    def release(self) -> WorkflowRelease:
        return WorkflowRelease(
            Version.parse(self._manifest.workflow_version),
            manifest_digest(self._manifest),
            self._manifest.controls_level,
        )

    def read_text(self, path: str) -> str:
        if path not in {entry.path for entry in self._manifest.files}:
            raise KeyError(f"{path} is not a file of the workflow manifest")
        return self._file(path).decode("utf-8")

    def paths(self) -> tuple[str, ...]:
        return tuple(entry.path for entry in self._manifest.files)

    def problems(self) -> tuple[str, ...]:
        return manifest_problems(self._manifest, self._present_files())

    def history(self) -> tuple[WorkflowRelease, ...]:
        record = load_contract(
            _LOADER,
            ReleaseHistory,
            self._root.joinpath("releases.json").read_bytes(),
            source="releases.json",
        )
        return tuple(
            WorkflowRelease(Version.parse(item.version), item.digest, item.controls_level)
            for item in record.releases
        )

    # --- internals -----------------------------------------------------------------------
    def _file(self, path: str) -> bytes:
        node = self._root
        for part in path.split("/"):
            node = node.joinpath(part)
        return node.read_bytes()

    def _present_files(self) -> dict[str, bytes]:
        found: dict[str, bytes] = {}
        pending: list[tuple[Traversable, str]] = [(self._root, "")]
        while pending:
            node, prefix = pending.pop()
            for child in node.iterdir():
                relative = f"{prefix}{child.name}"
                if child.is_dir():
                    if child.name != "__pycache__":
                        pending.append((child, f"{relative}/"))
                elif is_listed(relative):
                    found[relative] = child.read_bytes()
        return found
