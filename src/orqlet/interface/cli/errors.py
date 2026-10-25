"""Stable codes for failures, so a script or a person can search for them."""

from __future__ import annotations

from orqlet.application.ports.change_journal import JournalError
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.filesystem import FileSystemError
from orqlet.application.ports.lock import ApplyBusy
from orqlet.application.ports.standards import PackError
from orqlet.application.ports.vcs import VcsError
from orqlet.application.usecases.apply_plan import PlanStale
from orqlet.application.usecases.installation import NotInitialised
from orqlet.domain.errors import InvalidPath, OrqletError
from orqlet.domain.resolver import WeakeningError

_CODES: tuple[tuple[type[OrqletError], str], ...] = (
    (NotInitialised, "ORQ-E130"),
    (PlanStale, "ORQ-E135"),
    (JournalError, "ORQ-E136"),
    (ApplyBusy, "ORQ-E137"),
    (WeakeningError, "ORQ-E104"),
    (PackError, "ORQ-E103"),
    (DocumentError, "ORQ-E102"),
    (FileSystemError, "ORQ-E105"),
    (VcsError, "ORQ-E106"),
    (InvalidPath, "ORQ-E107"),
)
INTERNAL_CODE = "ORQ-E900"


def code_for(error: OrqletError) -> str:
    for kind, code in _CODES:
        if isinstance(error, kind):
            return code
    return "ORQ-E100"
