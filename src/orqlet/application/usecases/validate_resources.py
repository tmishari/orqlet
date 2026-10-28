"""`orqlet validate resources`: the registry and every stored copy (ADR-002 decision 9).

The registry is read by `load_resources`, so this validator and `doctor` can never disagree about
what is valid. Each entry with a `stored_copy` record must have a file `docs/resources/<id>.md`
that is a regular file, is at most 64 KiB, hashes to the recorded value after CRLF is read as LF,
starts with the two fixed header lines and holds no hidden text and no credential shape. The
folder `docs/resources` is then walked to a depth of three: anything that is not a regular file
named for such an entry is reported, and a link is never followed.

Offline, and nothing is written. Findings name the file and the rule and never repeat a part of a
copy; a name that comes from the repository is printed through `printable`.
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import islice

from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.usecases.resources_source import load_resources
from orqlet.application.usecases.validation import (
    Collector,
    ValidateServices,
    ValidationResult,
    content_hash,
)
from orqlet.domain.conventions import printable
from orqlet.domain.errors import InvalidPath
from orqlet.domain.findings import Finding
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resources import (
    copy_path,
    copy_problems,
    credential_problems,
    hidden_text_problems,
)

_COPY_FOLDER = "docs/resources"
_MAX_COPY_BYTES = 64 * 1024
_MAX_DEPTH = 3
_MAX_LISTED = 100
_SHOWN = 200


def validate_resources(services: ValidateServices, raw_path: str) -> ValidationResult:
    out = Collector()
    resources, found = load_resources(services.project, services.loader, raw_path)
    out.findings.extend(_with_printable_path(finding) for finding in found)
    if resources is None:
        return out.result()
    if _is_missing(services.project, raw_path):
        out.skip(f"{printable(raw_path, _SHOWN)} does not exist, so no resource was checked")
        return out.result()
    copies = [(item, item.stored_copy) for item in resources.resources if item.stored_copy]
    for item, record in copies:
        _check_copy(services.project, item.id, item.url, record.sha256, out)
    named = frozenset(f"{item.id}.md" for item, _ in copies)
    _report_unnamed(services.project, named, out)
    return out.result({"resources": len(resources.resources), "stored_copies": len(copies)})


def _is_missing(project: FileSystem, raw_path: str) -> bool:
    """True when the registry file is not there; the loader has already parsed the path."""
    return project.kind(CanonicalPath.parse(raw_path)) is None


def _with_printable_path(finding: Finding) -> Finding:
    """A loader finding whose path is the argument as typed, which may hold control characters."""
    if finding.path is None:
        return finding
    return Finding(finding.code, finding.message, finding.severity, printable(finding.path, _SHOWN))


# --- one stored copy ----------------------------------------------------------------------------
def _check_copy(
    project: FileSystem, resource_id: str, address: str, recorded: str, out: Collector
) -> None:
    path = copy_path(resource_id)
    data = _read_copy(project, path, out)
    if data is None:
        return
    if len(data) > _MAX_COPY_BYTES:
        out.error("ORQ-E506", f"{path} is above 64 KiB", path)
        return
    if content_hash(data) != recorded:
        out.error(
            "ORQ-E505",
            f"{path} differs from the SHA-256 recorded for it. If the change is wanted, record "
            "the new hash with `orqlet resources attach`.",
            path,
        )
    try:
        text = data.replace(b"\r\n", b"\n").decode("utf-8")
    except UnicodeDecodeError:
        out.error("ORQ-E506", f"{path} is not valid UTF-8", path)
        return
    problems = (
        *copy_problems(text, address),
        *hidden_text_problems(text),
        *credential_problems(text),
    )
    if problems:
        out.error("ORQ-E506", f"{path} fails these checks: {', '.join(problems)}", path)


def _read_copy(project: FileSystem, path: str, out: Collector) -> bytes | None:
    """The bytes of a stored copy, or `None` after a finding for a copy that cannot be used."""
    target = CanonicalPath.parse(path)
    try:
        kind = project.kind(target)
        if kind is None:
            out.error("ORQ-E504", f"{path} is missing", path)
            return None
        if kind is not FileKind.FILE:
            out.error("ORQ-E504", f"{path} is not a regular file", path)
            return None
        return project.read_bytes(target)
    except FileSystemError:
        out.error("ORQ-E504", f"{path} cannot be read safely", path)
        return None


# --- the folder ---------------------------------------------------------------------------------
def _report_unnamed(project: FileSystem, named: frozenset[str], out: Collector) -> None:
    root = CanonicalPath.parse(_COPY_FOLDER)
    try:
        kind = project.kind(root)
    except FileSystemError:
        out.error("ORQ-E508", f"{_COPY_FOLDER} cannot be read safely", _COPY_FOLDER)
        return
    if kind is None:
        return
    if kind is not FileKind.DIRECTORY:
        out.error("ORQ-E508", f"{_COPY_FOLDER} is not a folder", _COPY_FOLDER)
        return
    unnamed = list(islice(_unnamed_items(project, root, 1, named), _MAX_LISTED + 1))
    for shown in unnamed[:_MAX_LISTED]:
        out.error(
            "ORQ-E508",
            f"{shown} is not a regular file named for an entry of the registry that records a "
            "stored copy. Move or remove it.",
            shown,
        )
    if len(unnamed) > _MAX_LISTED:
        out.error(
            "ORQ-E508", f"{_COPY_FOLDER} holds more unnamed items than are listed", _COPY_FOLDER
        )


def _unnamed_items(
    project: FileSystem, folder: CanonicalPath, depth: int, named: frozenset[str]
) -> Iterator[str]:
    """Every item below `folder` that is not a named stored copy, as text that is safe to print."""
    try:
        names = project.list_dir(folder)
    except FileSystemError:
        yield printable(str(folder), _SHOWN)
        return
    for name in names:
        shown = printable(f"{folder}/{name}", _SHOWN)
        try:
            child = CanonicalPath.parse(f"{folder}/{name}")
            kind = project.kind(child)
        except (InvalidPath, FileSystemError):
            yield shown
            continue
        if kind is FileKind.FILE and depth == 1 and name in named:
            continue
        yield shown
        if kind is FileKind.DIRECTORY and depth < _MAX_DEPTH:
            yield from _unnamed_items(project, child, depth + 1, named)
