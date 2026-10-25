"""A word-list lint for prescriptive language in facts (proposal 17.3).

An AS-IS file says what exists. A fact that reads as advice ("should be refactored") has crept in
from a design. The list is deliberately short and deterministic. It finds words, not meaning: a
reviewer still samples the facts, and a flagged word in a quotation of code is the author's call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS = (
    r"should(?:n't| not)?",
    r"ought",
    r"recommend(?:s|ed|ation|ations)?",
    r"suggest(?:s|ed|ion|ions)?",
    r"propos(?:e|es|ed|al|als)",
    r"needs? to",
    r"better (?:to|if)",
    r"would be (?:better|best|nice|good)",
    r"ideally",
    r"improv(?:e|es|ed|ement|ements)",
    r"refactor(?:s|ed|ing)?",
    r"in the future",
    r"future (?:work|version|plan|plans)",
    r"consider(?:s|ed|ing)?",
)
_LINT = re.compile(r"\b(?:" + "|".join(_PATTERNS) + r")\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PrescriptiveHit:
    phrase: str
    offset: int


def prescriptive_hits(statement: str) -> tuple[PrescriptiveHit, ...]:
    """Every prescriptive word or phrase in a statement, in the order it occurs."""
    return tuple(PrescriptiveHit(m.group(0).lower(), m.start()) for m in _LINT.finditer(statement))
