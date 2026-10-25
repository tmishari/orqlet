"""Direct dependencies and lockfile packages, read from `pyproject.toml` and TOML lockfiles.

The fingerprint of the dependency surface is the direct dependency set (package name and
specifier) and the index and source settings that decide where those packages come from. A change
to a source setting is a deviation unless the design declares it (proposal 17.4.1). Nothing here
runs a package manager: the files are parsed as text.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field

_REQUIREMENT = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?P<rest>.*?)\s*$"
)


@dataclass(frozen=True, slots=True)
class Dependencies:
    direct: dict[str, str] = field(default_factory=dict)  # canonical name -> specifier
    sources: dict[str, str] = field(default_factory=dict)  # setting -> canonical text
    problems: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DependencyDelta:
    added: dict[str, str] = field(default_factory=dict)
    removed: dict[str, str] = field(default_factory=dict)
    changed: dict[str, tuple[str, str]] = field(default_factory=dict)  # name -> (before, after)
    source_changes: tuple[str, ...] = ()

    def names(self) -> frozenset[str]:
        return frozenset(self.added) | frozenset(self.removed) | frozenset(self.changed)

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed or self.source_changes)


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def canonical_specifier(text: str) -> str:
    """A specifier without spaces, so `>= 1.0, < 2` and `>=1.0,<2` are one fingerprint."""
    return re.sub(r"\s+", "", text)


def parse_pyproject(text: str) -> Dependencies:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return Dependencies(problems=(f"pyproject.toml cannot be parsed ({error})",))
    direct: dict[str, str] = {}
    problems: list[str] = []
    for requirement in _requirements(data):
        parsed = _REQUIREMENT.match(requirement)
        if parsed is None:
            problems.append(f"requirement {requirement!r} cannot be read")
            continue
        direct[canonical_name(parsed["name"])] = canonical_specifier(parsed["rest"])
    for name, spec in _poetry(data).items():
        direct[canonical_name(name)] = spec
    return Dependencies(direct, _sources(data), tuple(problems))


def lock_packages(text: str) -> frozenset[str] | None:
    """Package names of a TOML lockfile (`[[package]]` tables), or `None` for another format."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    packages = data.get("package")
    if not isinstance(packages, list):
        return None
    return frozenset(
        canonical_name(item["name"])
        for item in packages
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    )


def dependency_delta(before: Dependencies, after: Dependencies) -> DependencyDelta:
    added = {n: s for n, s in after.direct.items() if n not in before.direct}
    removed = {n: s for n, s in before.direct.items() if n not in after.direct}
    changed = {
        n: (before.direct[n], after.direct[n])
        for n in before.direct.keys() & after.direct.keys()
        if before.direct[n] != after.direct[n]
    }
    settings = sorted(
        key
        for key in before.sources.keys() | after.sources.keys()
        if before.sources.get(key) != after.sources.get(key)
    )
    return DependencyDelta(added, removed, changed, tuple(settings))


# --- reading the tables ---------------------------------------------------------------------
def _requirements(data: dict[str, object]) -> list[str]:
    found: list[str] = []
    project = _table(data.get("project"))
    found += _strings(project.get("dependencies"))
    for group in _table(project.get("optional-dependencies")).values():
        found += _strings(group)
    for group in _table(data.get("dependency-groups")).values():
        found += _strings(group)
    found += _strings(_table(_table(data.get("tool")).get("uv")).get("dev-dependencies"))
    return found


def _poetry(data: dict[str, object]) -> dict[str, str]:
    table = _table(_table(_table(data.get("tool")).get("poetry")).get("dependencies"))
    found = {}
    for name, spec in table.items():
        if name.lower() == "python":
            continue
        found[name] = canonical_specifier(spec) if isinstance(spec, str) else _canonical_text(spec)
    return found


def _sources(data: dict[str, object]) -> dict[str, str]:
    tool = _table(data.get("tool"))
    uv = _table(tool.get("uv"))
    found: dict[str, str] = {}
    for key in ("index-url", "extra-index-url", "find-links", "index-strategy"):
        if key in uv:
            found[f"uv.{key}"] = _canonical_text(uv[key])
    for name, value in _table(uv.get("sources")).items():
        found[f"uv.sources.{name}"] = _canonical_text(value)
    for index, entry in enumerate(_list(uv.get("index"))):
        label = _table(entry).get("name") or index
        found[f"uv.index.{label}"] = _canonical_text(entry)
    poetry = _table(tool.get("poetry"))
    for index, entry in enumerate(_list(poetry.get("source"))):
        label = _table(entry).get("name") or index
        found[f"poetry.source.{label}"] = _canonical_text(entry)
    return found


def _canonical_text(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _table(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [item for item in _list(value) if isinstance(item, str)]
