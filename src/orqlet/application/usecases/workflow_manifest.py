"""Building and checking the workflow manifest (pure; the tool and the adapter both use it)."""

from __future__ import annotations

from collections.abc import Mapping

from orqlet.application.contracts.workflow_package import (
    ManifestEntry,
    WorkflowIdentity,
    WorkflowManifest,
)
from orqlet.domain.digest import digest_of, sha256_hex

# Files in the workflow folder that are not part of the protected set.
EXCLUDED_NAMES = frozenset({"MANIFEST.json", "releases.json", "__init__.py"})


def is_listed(relative_path: str) -> bool:
    """True for a file that belongs in the manifest."""
    parts = relative_path.split("/")
    return (
        parts[-1] not in EXCLUDED_NAMES
        and "__pycache__" not in parts
        and not parts[-1].endswith(".pyc")
    )


def normalised_hash(content: bytes) -> str:
    """Hash of the content with CRLF read as LF, so a Windows checkout gives the same digest."""
    return sha256_hex(content.replace(b"\r\n", b"\n"))


def build_manifest(identity: WorkflowIdentity, files: Mapping[str, bytes]) -> WorkflowManifest:
    entries = tuple(
        ManifestEntry(path=path, sha256=normalised_hash(files[path]))
        for path in sorted(files)
        if is_listed(path)
    )
    return WorkflowManifest(
        schema_id="orqlet.workflow-manifest/v1",
        workflow_version=identity.workflow_version,
        controls_level=identity.controls_level,
        files=entries,
    )


def manifest_digest(manifest: WorkflowManifest) -> str:
    """The `workflow_digest`: SHA-256 of the canonical JSON form of the manifest."""
    return digest_of(manifest.model_dump(mode="json", by_alias=True))


def manifest_problems(manifest: WorkflowManifest, files: Mapping[str, bytes]) -> tuple[str, ...]:
    """What differs between a manifest and the files actually present."""
    problems: list[str] = []
    listed = {entry.path: entry.sha256 for entry in manifest.files}
    present = {path for path in files if is_listed(path)}
    for path in sorted(listed.keys() - present):
        problems.append(f"{path} is listed but missing")
    for path in sorted(present - listed.keys()):
        problems.append(f"{path} is present but not listed")
    for path in sorted(listed.keys() & present):
        if normalised_hash(files[path]) != listed[path]:
            problems.append(f"{path} differs from the manifest")
    return tuple(problems)
