"""A packaged workflow with a different version, text or controls level, to test upgrades."""

from __future__ import annotations

from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.domain.digest import sha256_hex
from orqlet.domain.versions import Version, WorkflowRelease


class PinnedWorkflow:
    """A real workflow with a fixed identity, so lifecycle tests do not move when a release is cut.

    The files are the packaged ones; only the version, digest and controls level are fixed. Tests
    that need "the next release" wrap this in `ChangedWorkflow`.
    """

    def __init__(
        self, base: WorkflowSource, *, version: str = "0.1.0", controls_level: int = 1
    ) -> None:
        self._base = base
        digest = sha256_hex(f"pinned|{version}|{controls_level}".encode())
        self._release = WorkflowRelease(Version.parse(version), digest, controls_level)

    @property
    def release(self) -> WorkflowRelease:
        return self._release

    def read_text(self, path: str) -> str:
        return self._base.read_text(path)

    def paths(self) -> tuple[str, ...]:
        return self._base.paths()

    def problems(self) -> tuple[str, ...]:
        return ()


class ChangedWorkflow:
    """Wraps a real workflow; the baseline gains a line and the identity changes."""

    def __init__(
        self,
        base: WorkflowSource,
        *,
        version: str,
        controls_level: int = 1,
        baseline_suffix: str = "- A rule added in this release.\n",
        digest_salt: str = "",
    ) -> None:
        self._base = base
        self._suffix = baseline_suffix
        material = (
            f"{version}|{controls_level}|{baseline_suffix}|{digest_salt}|{base.release.digest}"
        )
        self._release = WorkflowRelease(
            Version.parse(version), sha256_hex(material.encode()), controls_level
        )

    @property
    def release(self) -> WorkflowRelease:
        return self._release

    def read_text(self, path: str) -> str:
        text = self._base.read_text(path)
        if path == "baseline/baseline.md":
            return text.rstrip("\n") + "\n\n" + self._suffix
        if path == "pr_template/workflow-section.md":
            return text.rstrip("\n") + "\n\n" + self._suffix
        return text

    def paths(self) -> tuple[str, ...]:
        return self._base.paths()

    def problems(self) -> tuple[str, ...]:
        return ()


# The release most lifecycle tests start from: version 0.1.0 at controls level 1.
PINNED = PinnedWorkflow(PackagedWorkflow())
