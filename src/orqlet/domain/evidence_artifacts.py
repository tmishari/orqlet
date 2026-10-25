"""Which files count as evidence about a change, and so stay out of its own binding (6.14.1).

A path is excluded from `code_tests` and `knowledge` only when all three conditions hold: it
matches exactly one of three patterns for a task that exists, it is a regular file that parses and
validates against the closed schema of its kind, and the task, phase, role and round in the file
equal the ones in its path. Anything else is an ordinary input. No directory is excluded.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from orqlet.domain.binding import RecordKind

MAX_EVIDENCE_BYTES = 64 * 1024
MAX_FREE_TEXT_CHARACTERS = 2000
REGULAR_FILE_MODE = "100644"

_TASK = r"(?P<task>[a-z0-9]+(?:-[a-z0-9]+)*)"
_PATTERNS: tuple[tuple[RecordKind, re.Pattern[str]], ...] = (
    (
        RecordKind.REVIEW,
        re.compile(
            rf"^docs/design/{_TASK}/reviews/"
            r"(?P<role>architecture-reviewer|security-reviewer)-(?P<phase>P-[1-9]\d*)-r(?P<round>[1-9]\d*)\.yaml$"
        ),
    ),
    (RecordKind.TEST, re.compile(rf"^docs/design/{_TASK}/tests/(?P<phase>P-[1-9]\d*)\.yaml$")),
    (
        RecordKind.KNOWLEDGE_IMPACT,
        re.compile(rf"^docs/design/{_TASK}/knowledge/(?P<phase>P-[1-9]\d*)\.yaml$"),
    ),
)


@dataclass(frozen=True, slots=True)
class EvidencePath:
    kind: RecordKind
    task: str
    phase: str
    role: str | None = None
    round: int | None = None


def parse_evidence_path(path: str) -> EvidencePath | None:
    """The kind and identity a path states, or `None` when it matches no pattern exactly."""
    for kind, pattern in _PATTERNS:
        match = pattern.match(path)
        if match is not None:
            groups = match.groupdict()
            return EvidencePath(
                kind=kind,
                task=groups["task"],
                phase=groups["phase"],
                role=groups.get("role"),
                round=int(groups["round"]) if groups.get("round") else None,
            )
    return None


def is_excluded(
    path: str,
    *,
    mode: str,
    task_exists: bool,
    schema_valid: bool,
    content_matches_path: bool,
) -> bool:
    """True only when every one of the three conditions holds."""
    return (
        parse_evidence_path(path) is not None
        and task_exists
        and mode == REGULAR_FILE_MODE
        and schema_valid
        and content_matches_path
    )


def rounds_are_contiguous(rounds: Iterable[int]) -> bool:
    """`r1`, `r2`, ... with no gap: a removed failing round cannot leave an earlier PASS highest."""
    found = sorted(set(rounds))
    return bool(found) and found == list(range(1, len(found) + 1))
