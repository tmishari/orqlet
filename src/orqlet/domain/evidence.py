"""Evidence references: `{path, lines, revision, sha256}` and whether they resolve (proposal 17.3).

A reference proves that the cited lines exist and have that content at that revision. It does not
prove that the lines support the statement that cites them: a reviewer judges that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from orqlet.domain.errors import OrqletError
from orqlet.domain.facts import EvidenceError, line_range_hash

_LINES = re.compile(r"(?P<start>[1-9][0-9]*)(?:-(?P<end>[1-9][0-9]*))?")


class InvalidEvidence(OrqletError):
    """A reference is malformed, for example a line range that runs backwards."""


class EvidenceStatus(StrEnum):
    RESOLVED = "resolved"
    MISSING = "missing"  # the file does not exist at that revision
    OUT_OF_RANGE = "out-of-range"  # the cited lines are not in the file
    CHANGED = "changed"  # the lines exist but their hash differs


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    path: str
    start: int
    end: int
    revision: str
    sha256: str

    @classmethod
    def parse(cls, path: str, lines: str, revision: str, sha256: str) -> EvidenceRef:
        """Build a reference from the textual `a-b` (or `a`) form used in artifacts."""
        match = _LINES.fullmatch(lines.strip())
        if match is None:
            raise InvalidEvidence(f"lines {lines!r} is not `a-b` or `a` with numbers from 1")
        start = int(match["start"])
        end = int(match["end"] or start)
        if end < start:
            raise InvalidEvidence(f"lines {lines!r} run backwards")
        return cls(path, start, end, revision, sha256)

    @property
    def lines(self) -> str:
        return str(self.start) if self.start == self.end else f"{self.start}-{self.end}"


def check_reference(ref: EvidenceRef, content: bytes | None) -> EvidenceStatus:
    """Compare a reference with the bytes of its file at the cited revision (`None`: no file)."""
    if content is None:
        return EvidenceStatus.MISSING
    try:
        actual = line_range_hash(content, ref.start, ref.end)
    except EvidenceError:
        return EvidenceStatus.OUT_OF_RANGE
    return EvidenceStatus.RESOLVED if actual == ref.sha256 else EvidenceStatus.CHANGED
