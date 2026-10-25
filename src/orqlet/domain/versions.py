"""Workflow versions, the floor and downgrade protection (proposal sections 17.12.2 and 20.8)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from orqlet.domain.errors import InvalidVersion

_VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
_DIGEST = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> Version:
        match = _VERSION.fullmatch(text)
        if match is None:
            raise InvalidVersion(f"{text!r} is not a major.minor.patch version")
        return cls(int(match[1]), int(match[2]), int(match[3]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class WorkflowRelease:
    """The identity of one release of the protected workflow."""

    version: Version
    digest: str
    controls_level: int

    def __post_init__(self) -> None:
        if _DIGEST.fullmatch(self.digest) is None:
            raise InvalidVersion("a workflow digest is 64 lower-case hex characters")
        if self.controls_level < 0:
            raise InvalidVersion("controls_level cannot be negative")


def is_below_floor(version: Version, floor: Version) -> bool:
    return version < floor


def is_downgrade(current: WorkflowRelease, candidate: WorkflowRelease) -> bool:
    """A lower workflow version or a lower controls level weakens what is required."""
    return candidate.version < current.version or candidate.controls_level < current.controls_level


def check_release_history(
    current: WorkflowRelease, history: Sequence[WorkflowRelease]
) -> tuple[str, ...]:
    """Problems that make `current` a release defect, compared with what was already released.

    - the same version with a different digest or controls level is a silent change (FM-U05);
    - a version below the newest release, or a controls level below any earlier one, is a downgrade.
    An empty result means the build may be released.
    """
    problems: list[str] = []
    seen = {release.version: release for release in history}
    if len(seen) != len(history):
        problems.append("the release history lists a version twice")
    same = seen.get(current.version)
    if same is not None and (same.digest != current.digest):
        problems.append(
            f"workflow {current.version} was released with a different digest: "
            "change the workflow_version"
        )
    if same is not None and same.controls_level != current.controls_level:
        problems.append(f"workflow {current.version} was released with another controls_level")
    newest = max((release.version for release in history), default=None)
    if newest is not None and current.version < newest:
        problems.append(f"workflow {current.version} is older than the released {newest}")
    highest = max((release.controls_level for release in history), default=None)
    if highest is not None and current.controls_level < highest:
        problems.append("controls_level is lower than an earlier release")
    return tuple(problems)
