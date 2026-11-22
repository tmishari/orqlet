"""The behavioural foundation that every global copy carries (ADR-005).

`baseline/foundation.md` holds the precedence sentence, the three habits and the attribution link,
and one marker line where the "How to work" section of `baseline/baseline.md` goes. Composing it
from the package keeps the project baseline and every global copy on one source.
"""

from __future__ import annotations

from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.workflow_sources import SourceError

FOUNDATION_PATH = "baseline/foundation.md"
BASELINE_PATH = "baseline/baseline.md"
_MARKER = "<!-- how-to-work -->"
_SECTION = "### How to work"


def compose_foundation(workflow: WorkflowSource) -> str:
    """The foundation text with the baseline's "How to work" section in place of its marker."""
    lines = workflow.read_text(FOUNDATION_PATH).split("\n")
    if lines.count(_MARKER) != 1:
        raise SourceError(f"{FOUNDATION_PATH}: the line {_MARKER} must appear exactly once")
    at = lines.index(_MARKER)
    section = _how_to_work(workflow.read_text(BASELINE_PATH))
    return "\n".join([*lines[:at], section, *lines[at + 1 :]]).rstrip("\n") + "\n"


def _how_to_work(baseline: str) -> str:
    """The "How to work" heading and its lines, up to the next heading, without trailing blanks."""
    lines = baseline.split("\n")
    if _SECTION not in lines:
        raise SourceError(f"{BASELINE_PATH}: the section {_SECTION!r} is missing")
    start = lines.index(_SECTION)
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("#")),
        len(lines),
    )
    return "\n".join(lines[start:end]).rstrip("\n")
