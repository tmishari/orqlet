"""A scrubbed environment for child processes: a short allow-list, nothing inherited by default."""

from __future__ import annotations

from collections.abc import Mapping

# Compared case-insensitively because Windows environment names are.
_ALLOWED = frozenset(
    {
        "PATH",
        "PATHEXT",
        "HOME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "XDG_CONFIG_HOME",
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "TMPDIR",
        "TEMP",
        "TMP",
    }
)


def scrubbed_environment(
    source: Mapping[str, str], extra: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Keep allow-listed names from `source`, then apply `extra` on top."""
    environment = {name: value for name, value in source.items() if name.upper() in _ALLOWED}
    environment.update(extra or {})
    return environment
