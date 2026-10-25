"""Pure rules of the knowledge-impact analysis (proposal 17.13 and 19.2).

References are found by exact match only: repository-relative paths in Markdown link targets and
inline-code spans, entries of fenced `orqlet-ref` blocks, and qualified Python names in inline-code
spans. A prose mention in any other form is not found. The analysis calls no model: a word it does
not find is a reference the analysis cannot see, and the reviewers' judgement covers the rest.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass

from orqlet.domain.digest import digest_of

_LINK = re.compile(r"\]\(\s*([^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
_CODE = re.compile(r"`([^`\n]+)`")
_REF_BLOCK = re.compile(r"^```orqlet-ref[ \t]*\n(.*?)^```", re.MULTILINE | re.DOTALL)
_WORD = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True, slots=True)
class Candidate:
    """Something the phase may have made stale, or something the change made new."""

    id: str
    kind: str  # reference, interface-digest, public-symbol, expected-change or docs-map
    subject: str  # the path, symbol or entry that changed
    knowledge: str | None  # the knowledge file that is affected, if there is one
    reason: str


def candidate(kind: str, subject: str, knowledge: str | None, reason: str) -> Candidate:
    """A candidate whose id is a function of what it is about, so the list is reproducible."""
    return Candidate(
        id=f"cand-{digest_of([kind, subject, knowledge or ''])[:12]}",
        kind=kind,
        subject=subject,
        knowledge=knowledge,
        reason=reason,
    )


def candidates_digest(candidates: Sequence[Candidate]) -> str:
    return digest_of(sorted(c.id for c in candidates))


def markdown_references(doc_path: str, text: str) -> frozenset[str]:
    """Every path-like or symbol-like string a Markdown file names by an exact form."""
    found: set[str] = set()
    folder = posixpath.dirname(doc_path)
    for target in _LINK.findall(text):
        resolved = _link_path(folder, target)
        if resolved is not None:
            found.add(resolved)
    found.update(span.strip() for span in _CODE.findall(text) if span.strip())
    for block in _REF_BLOCK.findall(text):
        found.update(line.strip() for line in block.splitlines() if line.strip())
    return frozenset(found)


def _link_path(folder: str, target: str) -> str | None:
    if "://" in target or target.startswith(("mailto:", "#", "/")):
        return None
    path = target.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return None
    joined = posixpath.normpath(posixpath.join(folder, path))
    return None if joined.startswith("..") else joined


def near_duplicate(first: str, second: str, threshold: float = 0.8) -> bool:
    """Word 5-gram Jaccard similarity of the normalised texts at or above the threshold."""
    left, right = _shingles(first), _shingles(second)
    if not left or not right:
        return False
    return len(left & right) / len(left | right) >= threshold


def _shingles(text: str, size: int = 5) -> frozenset[tuple[str, ...]]:
    words = _WORD.findall(text.lower())
    if len(words) < size:
        return frozenset({tuple(words)}) if words else frozenset()
    return frozenset(tuple(words[i : i + size]) for i in range(len(words) - size + 1))


def longest_shared_run(draft: str, source: str) -> int:
    """The most consecutive non-empty lines of `draft` that also run consecutively in `source`."""
    left = [line.strip() for line in draft.splitlines() if line.strip()]
    right = [line.strip() for line in source.splitlines() if line.strip()]
    best = 0
    previous = [0] * (len(right) + 1)
    for line in left:
        current = [0] * (len(right) + 1)
        for column, other in enumerate(right, start=1):
            if line == other:
                current[column] = previous[column - 1] + 1
                best = max(best, current[column])
        previous = current
    return best
