"""Findings and verdicts. A missing or unknown result is never success (W-5)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    severity: Severity = Severity.WARNING
    path: str | None = None


def combine(verdicts: Iterable[Verdict]) -> Verdict:
    """FAIL beats NOT_RUN, which beats PASS. No evidence at all is NOT_RUN, not PASS."""
    seen = set(verdicts)
    if Verdict.FAIL in seen:
        return Verdict.FAIL
    if Verdict.NOT_RUN in seen or not seen:
        return Verdict.NOT_RUN
    return Verdict.PASS


def is_success(verdict: Verdict) -> bool:
    return verdict is Verdict.PASS
