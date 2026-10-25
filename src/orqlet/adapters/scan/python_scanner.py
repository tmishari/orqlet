"""Reads a Python project's manifests and records facts with evidence.

Rule of the scanner: a fact is recorded only when a file says it, and it cites the file, the
line and a hash of that line. When the files do not say, or disagree, the fact is unknown and
carries a question for the maintainer. Nothing is imported, executed or installed.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from typing import Any, Literal

from orqlet.adapters.scan.known_technologies import lookup, normalize_name
from orqlet.application.contracts.common import Evidence, FactValue
from orqlet.application.contracts.profile import (
    Dependencies,
    Dependency,
    Facts,
    LockedFile,
    NamedFact,
)
from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.application.ports.scanner import ScanResult
from orqlet.domain.facts import EvidenceError, find_line, line_range_hash, split_lines
from orqlet.domain.paths import CanonicalPath

MAX_FILE_BYTES = 1_048_576
_MARKERS = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile")
_LOCK_FILES = (("uv.lock", "uv"), ("poetry.lock", "poetry"), ("pdm.lock", "pdm"))
_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*([^;#]*)")


@dataclass(frozen=True, slots=True)
class _Source:
    path: str
    content: bytes


def _evidence_at(source: _Source, line: int | None) -> Evidence | None:
    if line is None:
        return None
    try:
        return Evidence(
            path=source.path,
            lines=f"{line}-{line}",
            sha256=line_range_hash(source.content, line, line),
        )
    except EvidenceError:
        return None


def _evidence_matching(source: _Source, pattern: str) -> Evidence | None:
    return _evidence_at(source, find_line(source.content, re.compile(pattern.encode("utf-8"))))


class PythonScanner:
    language = "python"

    def applies(self, fs: FileSystem) -> bool:
        return any(fs.kind(CanonicalPath.parse(name)) is FileKind.FILE for name in _MARKERS)

    def scan(self, fs: FileSystem) -> ScanResult:
        notes: list[str] = []
        pyproject = self._read(fs, "pyproject.toml", notes)
        data = self._parse(pyproject, notes)
        requirement_files = self._requirement_files(fs, notes)
        dependencies = self._dependencies(pyproject, data, requirement_files)
        frameworks = self._frameworks(dependencies)
        facts = Facts(
            python=self._python(fs, pyproject, data, notes),
            package_manager=self._package_manager(fs, pyproject, data, requirement_files, notes),
            frameworks=frameworks,
        )
        return ScanResult(
            language=self.language,
            facts=facts,
            dependencies=Dependencies(declared=dependencies, locked=self._locked(fs, notes)),
            kind=self._kind(data, frameworks),
            notes=tuple(notes),
        )

    # --- reading -------------------------------------------------------------------------
    @staticmethod
    def _read(fs: FileSystem, name: str, notes: list[str]) -> _Source | None:
        path = CanonicalPath.parse(name)
        if fs.kind(path) is not FileKind.FILE:
            return None
        content = fs.read_bytes(path)
        if len(content) > MAX_FILE_BYTES:
            notes.append(f"{name} is larger than {MAX_FILE_BYTES} bytes and was not read")
            return None
        return _Source(name, content)

    @staticmethod
    def _parse(source: _Source | None, notes: list[str]) -> dict[str, Any]:
        if source is None:
            return {}
        try:
            return tomllib.loads(source.content.decode("utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
            notes.append(f"{source.path} could not be parsed: {type(exc).__name__}")
            return {}

    def _requirement_files(self, fs: FileSystem, notes: list[str]) -> list[_Source]:
        names = sorted(
            name
            for name in fs.list_dir(None)
            if re.fullmatch(r"requirements[A-Za-z0-9._-]*\.txt", name)
        )
        sources = [self._read(fs, name, notes) for name in names]
        return [source for source in sources if source is not None]

    # --- facts ---------------------------------------------------------------------------
    def _python(
        self, fs: FileSystem, pyproject: _Source | None, data: dict[str, Any], notes: list[str]
    ) -> FactValue:
        declared = _get(data, "project", "requires-python")
        if isinstance(declared, str) and pyproject is not None:
            evidence = _evidence_matching(pyproject, r"^\s*requires-python\s*=")
            if evidence is not None:
                return FactValue(value=declared, evidence=(evidence,))
        poetry = _get(data, "tool", "poetry", "dependencies", "python")
        if isinstance(poetry, str) and pyproject is not None:
            evidence = _evidence_matching(pyproject, r"^\s*python\s*=")
            if evidence is not None:
                return FactValue(value=poetry, evidence=(evidence,))
        pinned = self._read(fs, ".python-version", notes)
        if pinned is not None:
            first = split_lines(pinned.content)[:1]
            evidence = _evidence_at(pinned, 1) if first and first[0].strip() else None
            if evidence is not None:
                return FactValue(value=first[0].decode("utf-8").strip(), evidence=(evidence,))
        return FactValue(question="Which Python versions does this project support?")

    def _package_manager(
        self,
        fs: FileSystem,
        pyproject: _Source | None,
        data: dict[str, Any],
        requirement_files: list[_Source],
        notes: list[str],
    ) -> FactValue:
        found: dict[str, list[Evidence]] = {}

        def add(manager: str, evidence: Evidence | None) -> None:
            if evidence is not None:
                found.setdefault(manager, []).append(evidence)

        for file_name, manager in _LOCK_FILES:
            source = self._read(fs, file_name, notes)
            if source is not None:
                add(manager, _evidence_at(source, 1))
        pipfile = self._read(fs, "Pipfile", notes)
        if pipfile is not None:
            add("pipenv", _evidence_at(pipfile, 1))
        tool = _get(data, "tool")
        if pyproject is not None and isinstance(tool, dict):
            for manager in ("uv", "poetry", "pdm"):
                if manager in tool:
                    add(manager, _evidence_matching(pyproject, rf"^\s*\[tool\.{manager}[\].]"))
        if not found:
            for source in requirement_files:
                add("pip", _evidence_at(source, 1))
        if len(found) == 1:
            ((manager, evidence),) = found.items()
            return FactValue(value=manager, evidence=tuple(evidence))
        if len(found) > 1:
            names = " and ".join(sorted(found))
            return FactValue(question=f"Files for {names} are both present. Which one is used?")
        return FactValue(question="Which package manager does this project use?")

    @staticmethod
    def _locked(fs: FileSystem, notes: list[str]) -> LockedFile | None:
        for file_name in ("uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock"):
            source = PythonScanner._read(fs, file_name, notes)
            if source is not None:
                evidence = _evidence_at(source, 1)
                return LockedFile(file=file_name, evidence=(evidence,) if evidence else ())
        return None

    # --- dependencies ----------------------------------------------------------------------
    def _dependencies(
        self, pyproject: _Source | None, data: dict[str, Any], requirement_files: list[_Source]
    ) -> tuple[Dependency, ...]:
        found: dict[str, Dependency] = {}

        def add(text: str, source: _Source | None, line_pattern: str | None = None) -> None:
            match = _REQUIREMENT.match(text)
            if match is None:
                return
            name, specifier = match.group(1), match.group(2).strip()
            key = normalize_name(name)
            if key in found:
                return
            pattern = line_pattern or re.escape(text)
            evidence = None if source is None else _evidence_matching(source, pattern)
            found[key] = Dependency(
                name=name, specifier=specifier, evidence=(evidence,) if evidence else ()
            )

        for text in self._strings(_get(data, "project", "dependencies")):
            add(text, pyproject)
        for groups in (
            _get(data, "project", "optional-dependencies"),
            _get(data, "dependency-groups"),
        ):
            for group in groups.values() if isinstance(groups, dict) else ():
                for text in self._strings(group):
                    add(text, pyproject)
        poetry = _get(data, "tool", "poetry", "dependencies")
        for name, spec in poetry.items() if isinstance(poetry, dict) else ():
            if name.lower() != "python":
                add(
                    f"{name}{spec if isinstance(spec, str) else ''}",
                    pyproject,
                    rf"^\s*{re.escape(name)}\s*=",
                )
        for source in requirement_files:
            for line in split_lines(source.content):
                text = line.decode("utf-8", errors="replace").strip()
                if text and not text.startswith(("#", "-", "git+", "http")):
                    add(text, source)
        return tuple(sorted(found.values(), key=lambda d: normalize_name(d.name)))

    @staticmethod
    def _strings(value: object) -> list[str]:
        return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []

    @staticmethod
    def _frameworks(dependencies: tuple[Dependency, ...]) -> tuple[NamedFact, ...]:
        facts = []
        for dependency in dependencies:
            technology = lookup(dependency.name)
            if technology is not None and dependency.evidence:
                facts.append(
                    NamedFact(
                        name=technology.name,
                        value=f"{dependency.name}{dependency.specifier}",
                        evidence=dependency.evidence,
                    )
                )
        return tuple(sorted(facts, key=lambda fact: fact.name))

    @staticmethod
    def _kind(
        data: dict[str, Any], frameworks: tuple[NamedFact, ...]
    ) -> Literal["python-cli", "python-service", "unknown"]:
        has_scripts = bool(_get(data, "project", "scripts"))
        has_web = any(_is_web(f.name) for f in frameworks)
        if has_scripts and not has_web:
            return "python-cli"
        if has_web and not has_scripts:
            return "python-service"
        return "unknown"


def _get(data: object, *path: str) -> object:
    """Walk nested tables, returning `None` as soon as a step is missing or not a table."""
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _is_web(name: str) -> bool:
    technology = lookup(name)
    return technology is not None and technology.category == "web"
