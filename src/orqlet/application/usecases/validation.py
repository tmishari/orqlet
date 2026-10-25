"""Shared pieces of the artifact validators: result, safe reading and the task folder layout.

A validator never writes. It reads an artifact the agent wrote (untrusted input), checks it
against its contract and the repository, and returns findings. A check that could not run is
`NOT_RUN` and is never reported as success.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from orqlet.application.contracts.common import Contract
from orqlet.application.contracts.loading import load_contract
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.ports.vcs import Vcs
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.domain.digest import sha256_hex
from orqlet.domain.errors import InvalidPath
from orqlet.domain.findings import Finding, Severity, Verdict
from orqlet.domain.paths import CanonicalPath

MAX_ARTIFACT_BYTES = 512 * 1024
TASK_ROOT = "docs/design"
_TASK_PATH = re.compile(r"^docs/design/(?P<task>[a-z0-9]+(?:-[a-z0-9]+)*)/")


@dataclass(frozen=True, slots=True)
class ValidateServices:
    project: FileSystem
    vcs: Vcs
    loader: DocumentLoader
    workflow: WorkflowSource


@dataclass(frozen=True, slots=True)
class ValidationResult:
    verdict: Verdict
    findings: tuple[Finding, ...]
    not_run: tuple[str, ...]
    data: dict[str, object]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)


@dataclass(slots=True)
class Collector:
    """Gathers findings and the reasons a check did not run while one validator works."""

    findings: list[Finding] = field(default_factory=list)
    not_run: list[str] = field(default_factory=list)

    def error(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.append(Finding(code, message, Severity.ERROR, path))

    def warning(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.append(Finding(code, message, Severity.WARNING, path))

    def info(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.append(Finding(code, message, Severity.INFO, path))

    def skip(self, reason: str) -> None:
        """A check that could not run. It keeps the verdict from being PASS."""
        if reason not in self.not_run:
            self.not_run.append(reason)

    def has_errors(self) -> bool:
        return any(f.severity is Severity.ERROR for f in self.findings)

    def result(self, data: dict[str, object] | None = None) -> ValidationResult:
        if self.has_errors():
            verdict = Verdict.FAIL
        elif self.not_run:
            verdict = Verdict.NOT_RUN
        else:
            verdict = Verdict.PASS
        return ValidationResult(verdict, tuple(self.findings), tuple(self.not_run), data or {})


def content_hash(data: bytes) -> str:
    """SHA-256 with CRLF read as LF, so a Windows checkout and a Linux checkout agree."""
    return sha256_hex(data.replace(b"\r\n", b"\n"))


def task_of(path: str) -> str | None:
    """`docs/design/<task>/...` gives the task; any other path gives `None`."""
    match = _TASK_PATH.match(path)
    return match["task"] if match else None


def split_front_matter(text: str) -> tuple[str, str] | None:
    """The YAML between the opening and closing `---` lines, and what follows. `None` if absent."""
    unified = text.removeprefix("\ufeff").replace("\r\n", "\n")
    if not unified.startswith("---\n"):
        return None
    end = unified.find("\n---\n", 3)
    if end < 0:
        if unified.endswith("\n---"):
            return unified[4:-4], ""
        return None
    return unified[4 : end + 1], unified[end + 5 :]


def read_artifact[T: Contract](
    services: ValidateServices,
    raw_path: str,
    model: type[T],
    out: Collector,
    *,
    front_matter: bool = False,
) -> tuple[T | None, bytes | None, str]:
    """The validated artifact, the bytes of its file and the Markdown body (if any).

    Every failure is a finding. The result is `None` when the file cannot be trusted at all.
    """
    try:
        path = CanonicalPath.parse(raw_path)
    except InvalidPath as error:
        out.error("ORQ-E320", f"not a usable path: {error}", raw_path)
        return None, None, ""
    try:
        kind = services.project.kind(path)
        if kind is None:
            out.error("ORQ-E321", f"{path} does not exist", str(path))
            return None, None, ""
        if kind is not FileKind.FILE:
            out.error("ORQ-E322", f"{path} is not a regular file", str(path))
            return None, None, ""
        data = services.project.read_bytes(path)
    except FileSystemError as error:
        out.error("ORQ-E322", f"{path} cannot be read safely: {error}", str(path))
        return None, None, ""
    if len(data) > MAX_ARTIFACT_BYTES:
        out.error("ORQ-E323", f"{path} is larger than {MAX_ARTIFACT_BYTES // 1024} KiB", str(path))
        return None, data, ""
    body = ""
    document = data
    if front_matter:
        split = split_front_matter(data.decode("utf-8", errors="replace"))
        if split is None:
            out.error(
                "ORQ-E324", f"{path} must start with a YAML front-matter block (---)", str(path)
            )
            return None, data, ""
        document, body = split[0].encode("utf-8"), split[1]
    try:
        loaded = load_contract(services.loader, model, document, source=str(path))
    except DocumentError as error:
        out.error("ORQ-E325", str(error), str(path))
        return None, data, body
    return loaded, data, body


def read_file(services: ValidateServices, raw_path: str) -> bytes | None:
    """The bytes of a regular file inside the project, or `None` when it is not one."""
    try:
        path = CanonicalPath.parse(raw_path)
        if services.project.kind(path) is not FileKind.FILE:
            return None
        return services.project.read_bytes(path)
    except (InvalidPath, FileSystemError):
        return None


def split_reference(reference: str) -> tuple[str, str] | None:
    """`path#sha256` into its two parts, or `None` when it has that form no more."""
    path, separator, digest = reference.rpartition("#")
    if not separator or not path or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return None
    return path, digest
