"""What may reach an agent's context from a file or a path: shown as it is, or not at all.

A value that breaks a rule is never repaired. Stripping a control character or cutting a long path
would print a path that does not exist, and an agent could act on it (ADR-001 decision 3).
"""

from __future__ import annotations

import unicodedata

from orqlet.domain.errors import InvalidVersion
from orqlet.domain.versions import Version

PATH_NOT_REPRESENTABLE = "path-not-representable"
MAX_PATH_CHARACTERS = 200

# Control, format (bidirectional and zero-width marks among them), surrogate (an undecodable byte
# of a file name), private use, unassigned, and the line and paragraph separators.
_HIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})
# Invisible although their category is not one of the above: variation selectors, the Hangul
# fillers, the Braille blank, the combining grapheme joiner, the Khmer inherent vowels and the
# Mongolian selectors (Q-69 and Q-70). Combining accents stay allowed, because decomposed file
# names hold them.
_HIDDEN_RANGES = (
    (0xFE00, 0xFE0F),
    (0xE0100, 0xE01EF),
    (0x115F, 0x1160),
    (0x3164, 0x3164),
    (0xFFA0, 0xFFA0),
    (0x2800, 0x2800),
    (0x034F, 0x034F),
    (0x17B4, 0x17B5),
    (0x180B, 0x180D),
    (0x180F, 0x180F),
)


def _hidden(character: str) -> bool:
    if unicodedata.category(character) in _HIDDEN_CATEGORIES:
        return True
    code = ord(character)
    return any(low <= code <= high for low, high in _HIDDEN_RANGES)


def representable_version(value: object) -> str | None:
    """The value itself when it is a `major.minor.patch` version, otherwise `None`."""
    if not isinstance(value, str) or not value.isascii():
        return None  # `Version.parse` also takes digits of other scripts
    try:
        Version.parse(value)
    except (InvalidVersion, ValueError):  # ValueError: a part over Python's int digit limit
        return None
    return value


def representable_path(text: str) -> str | None:
    """The text itself when it is short and shows every character it holds, otherwise `None`."""
    if not text or len(text) > MAX_PATH_CHARACTERS:
        return None
    if any(_hidden(character) for character in text):
        return None
    return text
