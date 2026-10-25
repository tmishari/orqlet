"""Path globs for rule scopes: `*` and `?` stay inside a segment, `**` spans segments."""

from __future__ import annotations

from fnmatch import fnmatchcase


def glob_match(pattern: str, path: str) -> bool:
    """Match a `/`-separated glob against a `/`-separated path. Case sensitive."""
    return _match(pattern.split("/"), path.split("/"))


def _match(pattern: list[str], path: list[str]) -> bool:
    if not pattern:
        return not path
    head, rest = pattern[0], pattern[1:]
    if head == "**":
        return any(_match(rest, path[skip:]) for skip in range(len(path) + 1))
    if not path:
        return False
    return fnmatchcase(path[0], head) and _match(rest, path[1:])
