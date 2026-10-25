"""Canonical repository-relative paths.

Repository content is untrusted input. A path that reaches Orqlet is reduced to a canonical
form first and rejected when it cannot be. The key rules follow the plan validator of the
proposal (section 17.5): relative, `/` separators, Unicode NFC, per-component case-fold key,
no `.`, `..`, empty component, trailing dot or space, `:` or `\\`, no Windows reserved device
name and nothing named `.git`.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from orqlet.domain.errors import InvalidPath

_WINDOWS_RESERVED = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
)
_MAX_COMPONENT_BYTES = 255
_FORBIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Cs"})


def _fold(component: str) -> str:
    return unicodedata.normalize("NFC", component.casefold())


def _check_component(component: str, raw: str) -> str:
    if component == "":
        raise InvalidPath(f"empty path component in {raw!r}")
    if component in {".", ".."}:
        raise InvalidPath(f"relative step {component!r} is not allowed in {raw!r}")
    for char in component:
        if unicodedata.category(char) in _FORBIDDEN_CATEGORIES:
            raise InvalidPath(f"control or format character U+{ord(char):04X} in {raw!r}")
        if char in {"\\", ":"}:
            raise InvalidPath(f"character {char!r} is not allowed in {raw!r}")
    if component.endswith((".", " ")):
        raise InvalidPath(f"component {component!r} ends with a dot or a space")
    if len(component.encode("utf-8")) > _MAX_COMPONENT_BYTES:
        raise InvalidPath(f"component is longer than {_MAX_COMPONENT_BYTES} bytes in {raw!r}")
    if component.split(".", 1)[0].casefold() in _WINDOWS_RESERVED:
        raise InvalidPath(f"component {component!r} is a reserved device name on Windows")
    if _fold(component) == ".git":
        raise InvalidPath(f"nothing under .git may be managed: {raw!r}")
    return component


@dataclass(frozen=True)
class CanonicalPath:
    """A safe path relative to a repository root, in NFC spelling."""

    parts: tuple[str, ...]

    @classmethod
    def parse(cls, raw: str) -> CanonicalPath:
        if raw == "":
            raise InvalidPath("empty path")
        if raw.startswith("/"):
            raise InvalidPath(f"absolute path {raw!r}")
        normalized = unicodedata.normalize("NFC", raw)
        parts = tuple(_check_component(part, raw) for part in normalized.split("/"))
        return cls(parts)

    @property
    def key(self) -> tuple[str, ...]:
        """Comparison key: case-folded per component, so `SRC/` and `src/` are one directory."""
        return tuple(_fold(part) for part in self.parts)

    @property
    def name(self) -> str:
        return self.parts[-1]

    @property
    def parent(self) -> CanonicalPath | None:
        return CanonicalPath(self.parts[:-1]) if len(self.parts) > 1 else None

    def child(self, name: str) -> CanonicalPath:
        return CanonicalPath.parse("/".join((*self.parts, name)))

    def conflicts_with(self, other: CanonicalPath) -> bool:
        """True when the keys are equal or one is a proper component-prefix of the other."""
        shorter = min(len(self.parts), len(other.parts))
        return self.key[:shorter] == other.key[:shorter]

    def is_inside(self, directory: CanonicalPath) -> bool:
        count = len(directory.parts)
        return len(self.parts) > count and self.key[:count] == directory.key

    def sort_key(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return (self.key, self.parts)

    def __str__(self) -> str:
        return "/".join(self.parts)
