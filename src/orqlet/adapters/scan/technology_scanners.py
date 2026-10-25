"""Technology scanners: one small plug-in per ecosystem, all reading manifests as evidence.

Each scanner reads the files of one directory and reports what they say, citing the file, the
line and a hash of the line. None runs, imports or installs anything. A name that is not in the
tables of `stack_tables` is not reported, and a version the source does not give stays `None`.
"""

from __future__ import annotations

import json
import re
import tomllib
from typing import Any

from orqlet.adapters.scan.common import (
    Source,
    at,
    evidence_at,
    evidence_matching,
    read_source,
    scope_text,
)
from orqlet.adapters.scan.python_scanner import PythonScanner
from orqlet.adapters.scan.scoped import ScopedFileSystem
from orqlet.adapters.scan.stack_tables import (
    CRATES,
    GO,
    NPM,
    Known,
    image_version,
    lookup_image,
    lookup_prefix,
    lookup_pypi,
)
from orqlet.application.contracts.common import Evidence
from orqlet.application.contracts.profile import Technology, TechnologyKind
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.domain.errors import InvalidPath
from orqlet.domain.facts import split_lines
from orqlet.domain.paths import CanonicalPath


def _names(fs: FileSystem, scope: CanonicalPath | None) -> tuple[str, ...]:
    try:
        return fs.list_dir(scope)
    except FileSystemError:
        return ()


def _tech(
    kind: TechnologyKind,
    name: str,
    scope: CanonicalPath | None,
    evidence: Evidence | None,
    version: str | None = None,
) -> Technology | None:
    """A technology with its evidence, or `None` when no line could be cited for it."""
    if evidence is None:
        return None
    return Technology(
        kind=kind,
        name=name,
        version=version,
        scope=scope_text(scope),
        evidence=(evidence,),
    )


def _dependency_version(known: Known, version: str | None) -> str | None:
    """A dependency's version says something about the technology only when it is the technology.

    `psycopg>=3.1` is the version of a driver, not of PostgreSQL, so databases, queues and
    infrastructure reached through a client library carry no version.
    """
    return (
        version if known.kind in {"framework", "library", "language", "runtime", "tool"} else None
    )


def _present(items: list[Technology | None]) -> tuple[Technology, ...]:
    return tuple(item for item in items if item is not None)


class PythonTechnologyScanner:
    """Python from its manifests, through the scanner that also fills the profile's Python facts."""

    name = "python"

    def __init__(self) -> None:
        self._python = PythonScanner()

    def scan(self, fs: FileSystem, scope: CanonicalPath | None) -> tuple[Technology, ...]:
        view: FileSystem = fs if scope is None else ScopedFileSystem(fs, scope)  # type: ignore[assignment]
        if not self._python.applies(view):
            return ()
        result = self._python.scan(view)
        prefix = "" if scope is None else f"{scope}/"
        found: list[Technology | None] = []
        python = result.facts.python
        if python.value is not None:
            found.append(
                _tech("language", "Python", scope, _first(python.evidence, prefix), python.value)
            )
        manager = result.facts.package_manager
        if manager.value is not None:
            found.append(_tech("tool", manager.value, scope, _first(manager.evidence, prefix)))
        for dependency in result.dependencies.declared:
            known = lookup_pypi(dependency.name)
            if known is not None:
                found.append(
                    _tech(
                        known.kind,
                        known.name,
                        scope,
                        _first(dependency.evidence, prefix),
                        _dependency_version(known, dependency.specifier or None),
                    )
                )
        if not any(item is not None and item.name == "Python" for item in found):
            # The manifests exist but name no version: Python is still what the project is.
            marker = _first([e for d in result.dependencies.declared for e in d.evidence], prefix)
            found.insert(0, _tech("language", "Python", scope, marker))
        return _present(found)


def _first(evidence: tuple[Evidence, ...] | list[Evidence], prefix: str) -> Evidence | None:
    """The first piece of evidence, with its path made relative to the repository root."""
    if not evidence:
        return None
    item = evidence[0]
    return item.model_copy(update={"path": f"{prefix}{item.path}"})


class GoScanner:
    name = "go"
    _REQUIRE = re.compile(r"^\s*(?:require\s+)?(\S+)\s+(v\S+)")

    def scan(self, fs: FileSystem, scope: CanonicalPath | None) -> tuple[Technology, ...]:
        source = read_source(fs, scope, "go.mod")
        if source is None:
            return ()
        found: list[Technology | None] = []
        go_line = evidence_matching(source, r"^\s*go\s+\d")
        version = _after(source, r"^\s*go\s+(\S+)")
        found.append(
            _tech(
                "language",
                "Go",
                scope,
                go_line or evidence_matching(source, r"^\s*module\s"),
                version,
            )
        )
        block = False
        for number, raw in enumerate(split_lines(source.content), start=1):
            line = raw.decode("utf-8", errors="replace")
            if re.match(r"^\s*require\s*\(", line):
                block = True
                continue
            if block and line.strip() == ")":
                block = False
                continue
            if not (block or line.lstrip().startswith("require ")) or "// indirect" in line:
                continue
            match = self._REQUIRE.match(line)
            known = None if match is None else lookup_prefix(GO, match.group(1))
            if match is not None and known is not None:
                found.append(
                    _tech(
                        known.kind,
                        known.name,
                        scope,
                        evidence_at(source, number),
                        _dependency_version(known, match.group(2)),
                    )
                )
        return _present(found)


def _after(source: Source, pattern: str) -> str | None:
    """The first capture group of the first line that matches `pattern`."""
    expression = re.compile(pattern)
    for raw in split_lines(source.content):
        match = expression.match(raw.decode("utf-8", errors="replace"))
        if match:
            return match.group(1)
    return None


class RustScanner:
    name = "rust"

    def scan(self, fs: FileSystem, scope: CanonicalPath | None) -> tuple[Technology, ...]:
        source = read_source(fs, scope, "Cargo.toml")
        if source is None:
            return ()
        try:
            data = tomllib.loads(source.content.decode("utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            return ()
        package = data.get("package") if isinstance(data.get("package"), dict) else {}
        rust_version = package.get("rust-version") if isinstance(package, dict) else None
        found: list[Technology | None] = [
            _tech(
                "language",
                "Rust",
                scope,
                evidence_matching(source, r"^\s*rust-version\s*=")
                or evidence_matching(source, r"^\s*\[(package|workspace)\]"),
                rust_version if isinstance(rust_version, str) else None,
            )
        ]
        tables = [data.get("dependencies"), (data.get("workspace") or {}).get("dependencies")]
        for table in tables:
            for crate, spec in table.items() if isinstance(table, dict) else ():
                known = CRATES.get(str(crate).lower())
                if known is None:
                    continue
                version = (
                    spec
                    if isinstance(spec, str)
                    else (spec or {}).get("version")
                    if isinstance(spec, dict)
                    else None
                )
                found.append(
                    _tech(
                        known.kind,
                        known.name,
                        scope,
                        evidence_matching(source, rf"^\s*{re.escape(str(crate))}\s*[=.]"),
                        _dependency_version(known, version if isinstance(version, str) else None),
                    )
                )
        return _present(found)


class NodeScanner:
    name = "node"

    def scan(self, fs: FileSystem, scope: CanonicalPath | None) -> tuple[Technology, ...]:
        source = read_source(fs, scope, "package.json")
        if source is None:
            return ()
        try:
            data: Any = json.loads(source.content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return ()
        if not isinstance(data, dict):
            return ()
        packages: dict[str, str] = {}
        for section in ("dependencies", "devDependencies"):
            table = data.get(section)
            if isinstance(table, dict):
                packages.update({str(k): str(v) for k, v in table.items()})
        anchor = evidence_matching(source, r'"name"\s*:') or evidence_at(source, 1)
        language = "TypeScript" if "typescript" in packages else "JavaScript"
        found: list[Technology | None] = [
            _tech(
                "language",
                language,
                scope,
                evidence_matching(source, r'"typescript"\s*:')
                if language == "TypeScript"
                else anchor,
                packages.get("typescript"),
            )
        ]
        engines = data.get("engines")
        node = engines.get("node") if isinstance(engines, dict) else None
        if isinstance(node, str):
            found.append(
                _tech("runtime", "Node.js", scope, evidence_matching(source, r'"node"\s*:'), node)
            )
        for package, version in packages.items():
            known = NPM.get(package.lower())
            if known is not None:
                found.append(
                    _tech(
                        known.kind,
                        known.name,
                        scope,
                        evidence_matching(source, rf'"{re.escape(package)}"\s*:'),
                        _dependency_version(known, version),
                    )
                )
        return _present(found)


class ContainerScanner:
    """Dockerfiles, Compose files and Helm charts: the images and charts a service is built from."""

    name = "containers"
    _FROM = re.compile(r"^\s*FROM\s+(?:--\S+\s+)*(\S+)", re.IGNORECASE)
    _IMAGE = re.compile(r"^\s*image:\s*['\"]?([^\s'\"#]+)")
    _COMPOSE = re.compile(r"^(docker-)?compose[^/]*\.ya?ml$", re.IGNORECASE)

    def scan(self, fs: FileSystem, scope: CanonicalPath | None) -> tuple[Technology, ...]:
        found: list[Technology | None] = []
        for name in _names(fs, scope):
            lowered = name.lower()
            if name.startswith("."):
                continue  # `.git` and other hidden entries are never manifests (and may be refused)
            try:
                is_file = fs.kind(at(scope, name)) is FileKind.FILE
            except (FileSystemError, InvalidPath):
                continue
            if not is_file:
                continue
            if lowered.startswith("dockerfile") or lowered.endswith(".dockerfile"):
                found += self._references(fs, scope, name, self._FROM, "Docker")
            elif self._COMPOSE.match(name):
                found += self._references(fs, scope, name, self._IMAGE, "Docker Compose")
            elif name == "Chart.yaml":
                found += self._helm(fs, scope, name)
        return _present(found)

    def _references(
        self,
        fs: FileSystem,
        scope: CanonicalPath | None,
        name: str,
        pattern: re.Pattern[str],
        tool: str,
    ) -> list[Technology | None]:
        source = read_source(fs, scope, name)
        if source is None:
            return []
        found: list[Technology | None] = []
        first: Evidence | None = None
        for number, raw in enumerate(split_lines(source.content), start=1):
            match = pattern.match(raw.decode("utf-8", errors="replace"))
            if match is None:
                continue
            reference = match.group(1)
            first = first or evidence_at(source, number)
            known: Known | None = None if "$" in reference else lookup_image(reference)
            if known is not None:
                found.append(
                    _tech(
                        known.kind,
                        known.name,
                        scope,
                        evidence_at(source, number),
                        image_version(reference),
                    )
                )
        found.insert(0, _tech("tool", tool, scope, first))
        return found

    def _helm(
        self, fs: FileSystem, scope: CanonicalPath | None, name: str
    ) -> list[Technology | None]:
        source = read_source(fs, scope, name)
        if source is None:
            return []
        found: list[Technology | None] = [
            _tech(
                "tool",
                "Helm",
                scope,
                evidence_matching(source, r"^\s*apiVersion:") or evidence_at(source, 1),
            )
        ]
        lines = [raw.decode("utf-8", errors="replace") for raw in split_lines(source.content)]
        in_dependencies = False
        for index, line in enumerate(lines):
            if re.match(r"^dependencies:\s*$", line):
                in_dependencies = True
                continue
            if in_dependencies and re.match(r"^\S", line):
                in_dependencies = False
            match = re.match(r"^\s*-\s*name:\s*['\"]?([^\s'\"]+)", line)
            if not (in_dependencies and match):
                continue
            known = lookup_image(match.group(1))
            if known is None:
                continue
            # A chart's version is the chart's, not the database's, so none is reported.
            found.append(_tech(known.kind, known.name, scope, evidence_at(source, index + 1)))
        return found
