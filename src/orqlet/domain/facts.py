"""Evidence helpers: a fact cites a file, a line range and a hash that anyone can recompute.

The hash covers the cited lines only, with line endings normalised to LF and without the final
line break, so a Windows checkout and a Linux checkout cite the same hash.
"""

from __future__ import annotations

import re

from orqlet.domain.digest import sha256_hex
from orqlet.domain.errors import OrqletError


class EvidenceError(OrqletError):
    """A line range does not exist in the content it is cited against."""


def split_lines(content: bytes) -> list[bytes]:
    """Lines without their breaks. A trailing break does not add an empty last line."""
    normalised = content.replace(b"\r\n", b"\n")
    lines = normalised.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    return lines


def line_range_hash(content: bytes, start: int, end: int) -> str:
    """SHA-256 of lines `start` to `end`, both 1-based and inclusive."""
    lines = split_lines(content)
    if not 1 <= start <= end <= len(lines):
        raise EvidenceError(f"lines {start}-{end} are outside a file of {len(lines)} lines")
    return sha256_hex(b"\n".join(lines[start - 1 : end]))


def find_line(content: bytes, pattern: re.Pattern[bytes]) -> int | None:
    """The 1-based number of the first line the pattern matches, or `None`."""
    for number, line in enumerate(split_lines(content), start=1):
        if pattern.search(line):
            return number
    return None
