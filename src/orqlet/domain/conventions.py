"""Team conventions: the pure rules for branch names and commit subjects.

Task team-conventions-resources, phase P-1 (ADR-003 decisions 2 and 4). The branch and the subject
are typed by a contributor, so they are untrusted: a rule name is a fixed word and no function
puts a part of its input into its result, and `printable` is the one way to show such text.
Branch patterns are globs from a committed file; the shared matcher recurses over every split
point of a `**`, so a pattern may hold at most one `**` and a name is bounded before matching.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from orqlet.domain.globs import glob_match

_CONVENTIONAL_COMMITS = "conventional-commits"
_MAX_PATTERN = 60
_MAX_PATTERN_SEGMENTS = 8
_MAX_BRANCH = 255
_MAX_BRANCH_SEGMENTS = 32
_PATTERN_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/*?-")
_TYPE = re.compile(r"[a-z][a-z0-9-]*", re.ASCII)
_SCOPE = re.compile(r"[A-Za-z0-9._/-]+", re.ASCII)


def pattern_problems(pattern: str) -> tuple[str, ...]:
    """The rules that a branch pattern breaks: at most one `**`, 8 segments and 60 characters."""
    found: list[str] = []
    if not pattern:
        return ("pattern-empty",)
    if len(pattern) > _MAX_PATTERN:
        found.append("pattern-too-long")
    if any(c not in _PATTERN_CHARS for c in pattern):
        found.append("pattern-character")
    if pattern.startswith("/") or pattern.endswith("/") or "//" in pattern:
        found.append("pattern-slash")
    if ".." in pattern.split("/"):
        found.append("pattern-climbs-out")
    if pattern.count("**") > 1:
        found.append("pattern-double-star")
    if len(pattern.split("/")) > _MAX_PATTERN_SEGMENTS:
        found.append("pattern-segments")
    return tuple(found)


def branch_problems(branch: str, patterns: Sequence[str]) -> tuple[str, ...]:
    """Why a branch name is not allowed by any pattern; empty when one matches or none is set."""
    if not patterns:
        return ()
    if len(branch) > _MAX_BRANCH:
        return ("branch-too-long",)
    if len(branch.split("/")) > _MAX_BRANCH_SEGMENTS:
        return ("branch-segments",)
    if any(pattern_problems(pattern) for pattern in patterns):
        return ("pattern-invalid",)
    if any(glob_match(pattern, branch) for pattern in patterns):
        return ()
    return ("branch-not-allowed",)


def commit_subject_problems(subject: str) -> tuple[str, ...]:
    """Whether a subject has the Conventional Commits shape; `Merge ` subjects are exempt.

    The shape is a type of lower case letters, digits and hyphens that starts with a letter, an
    optional scope in parentheses, an optional `!`, a colon, one space and a description.
    """
    if subject.startswith("Merge "):
        return ()
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in subject):
        return ("subject-control-character",)
    colon = subject.find(":")
    if colon == -1:
        return ("subject-colon",)
    head, description = subject[:colon], subject[colon + 1 :]
    head = head.removesuffix("!")
    type_part, scope = head, None
    if head.endswith(")"):
        opening = head.find("(")
        if opening == -1:
            return ("subject-scope",)
        type_part, scope = head[:opening], head[opening + 1 : -1]
    if _TYPE.fullmatch(type_part) is None:
        return ("subject-type",)
    if scope is not None and _SCOPE.fullmatch(scope) is None:
        return ("subject-scope",)
    if not description.startswith(" ") or not description[1:] or description[1:].startswith(" "):
        return ("subject-description",)
    return ()


def is_checkable_convention(text: str) -> bool:
    """True when the answer reads as Conventional Commits, the one convention that is checked.

    The answer is trimmed, lower-cased and read with spaces and underscores as hyphens.
    """
    return re.sub(r"[ _]", "-", text.strip().lower()) == _CONVENTIONAL_COMMITS


def printable(text: str, limit: int) -> str:
    """The text as ASCII only: every other character, DEL and the C0 controls included, is escaped.

    A backslash is doubled so that an escape in the output is never mistaken for text.

    The result is cut at `limit` characters after escaping and then ends in `...`, so it is never
    longer than `limit + 3`. It is shown after a fixed prefix, never at the start of a line.
    """
    shown = "".join(_escape(char) for char in text)
    if len(shown) > limit:
        return shown[:limit] + "..."
    return shown


def _escape(char: str) -> str:
    point = ord(char)
    if char == "\\":
        return "\\\\"
    if 0x20 <= point <= 0x7E:
        return char
    if point <= 0xFF:
        return f"\\x{point:02x}"
    if point <= 0xFFFF:
        return f"\\u{point:04x}"
    return f"\\U{point:08x}"
