"""A packaged workflow with a different version, text or controls level, to test upgrades."""

from __future__ import annotations

from dataclasses import dataclass

from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.domain.digest import sha256_hex
from orqlet.domain.versions import Version, WorkflowRelease

# The sources that every `ChangedWorkflow` appends its baseline suffix to.
_SUFFIXED_SOURCES = ("baseline/baseline.md", "pr_template/workflow-section.md")


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


@dataclass(frozen=True, slots=True)
class SkillChange:
    """A line appended to the body of one packaged skill and to one of its references."""

    skill: str
    reference: str
    line: str = "- A step added in this release.\n"

    def sources(self) -> tuple[str, str]:
        return (
            f"skills/{self.skill}/skill.md",
            f"skills/{self.skill}/references/{self.reference}",
        )


class ChangedWorkflow:
    """Wraps a real workflow; the baseline gains a line and the identity changes.

    With a `SkillChange`, one skill body and one of its references gain a line too, so an upgrade
    test can change what a skill says and not only the baseline.
    """

    def __init__(
        self,
        base: WorkflowSource,
        *,
        version: str,
        controls_level: int = 1,
        baseline_suffix: str = "- A rule added in this release.\n",
        digest_salt: str = "",
        skill_change: SkillChange | None = None,
    ) -> None:
        self._base = base
        self._suffix = baseline_suffix
        self._skill_lines = _skill_lines(base, skill_change)
        material = (
            f"{version}|{controls_level}|{baseline_suffix}|{digest_salt}|{base.release.digest}"
        )
        # Without a skill change the material stays as it was, so existing identities do not move.
        if skill_change is not None:
            material += f"|{skill_change.skill}|{skill_change.reference}|{skill_change.line}"
        self._release = WorkflowRelease(
            Version.parse(version), sha256_hex(material.encode()), controls_level
        )

    @property
    def release(self) -> WorkflowRelease:
        return self._release

    def read_text(self, path: str) -> str:
        text = self._base.read_text(path)
        if path in _SUFFIXED_SOURCES:
            return _with_line(text, self._suffix)
        if path in self._skill_lines:
            return _with_line(text, self._skill_lines[path])
        return text

    def paths(self) -> tuple[str, ...]:
        return self._base.paths()

    def problems(self) -> tuple[str, ...]:
        return ()


def _skill_lines(base: WorkflowSource, change: SkillChange | None) -> dict[str, str]:
    """The sources that gain the change's line, by path; a source the base lacks is refused.

    A test that names a skill or reference the package does not ship would otherwise change
    nothing and still pass.
    """
    if change is None:
        return {}
    missing = [path for path in change.sources() if path not in base.paths()]
    if missing:
        raise ValueError(f"the base workflow has no {', '.join(missing)}")
    return dict.fromkeys(change.sources(), change.line)


def _with_line(text: str, line: str) -> str:
    return text.rstrip("\n") + "\n\n" + line


# The release most lifecycle tests start from: version 0.1.0 at controls level 1.
PINNED = PinnedWorkflow(PackagedWorkflow())
