"""The one reader of `.orqlet/resources.yaml` (ADR-002 decisions 6 and 10).

`validate`, `doctor`, `compose` and the edit commands all take the result of `load_resources`, so
two readers can never disagree about the registry. A missing file is an empty registry. A file that
cannot be read safely, is above 256 KiB or fails its contract gives no registry and findings that
name the field and the rule and never the value (ORQLET-SEC-003): the loader's own messages, which
may repeat a key or a tag, are not passed on. The file is untrusted input (ORQLET-SEC-002): it is
read through the `FileSystem` port and parsed only by the strict loader.
"""

from __future__ import annotations

from pydantic import ValidationError

from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.domain.errors import InvalidPath
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.paths import CanonicalPath

_PATH = ".orqlet/resources.yaml"
_MAX_BYTES = 256 * 1024
_EMPTY = b"schema: orqlet.resources/v1\nresources: []\n"


def resources_path() -> CanonicalPath:
    """Where the registry lives."""
    return CanonicalPath.parse(_PATH)


def parse_resources(
    loader: DocumentLoader, raw: bytes, source: str
) -> tuple[Resources | None, tuple[Finding, ...]]:
    """The registry in `raw`, or no registry and the findings that say why not."""
    if len(raw) > _MAX_BYTES:
        return None, (_error("ORQ-E502", f"{source} is larger than 256 KiB", source),)
    try:
        data = loader.load(raw, source=source)
    except DocumentError:
        return None, (
            _error("ORQ-E501", f"{source} breaks the rules for reading a document", source),
        )
    try:
        return Resources.model_validate(data), ()
    except ValidationError as exc:
        problems = "; ".join(_problem(error) for error in exc.errors(include_input=False))
        return None, (_error("ORQ-E501", f"{source} fails its contract: {problems}", source),)


def load_resources(
    project: FileSystem, loader: DocumentLoader, path: str
) -> tuple[Resources | None, tuple[Finding, ...]]:
    """The registry at `path`: empty when the file is missing, none and findings when it is bad."""
    try:
        target = CanonicalPath.parse(path)
    except InvalidPath:
        return None, (_error("ORQ-E500", "the registry path is not a usable path", path),)
    try:
        kind = project.kind(target)
        if kind is None:
            empty, _ = parse_resources(loader, _EMPTY, path)
            return empty, ()
        if kind is not FileKind.FILE:
            return None, (_error("ORQ-E500", f"{path} is not a regular file", path),)
        raw = project.read_bytes(target)
    except FileSystemError:
        return None, (_error("ORQ-E500", f"{path} cannot be read safely", path),)
    return parse_resources(loader, raw, path)


def _problem(error: object) -> str:
    """One validation error as `location: message`, without the input or a stranger's key."""
    detail = error if isinstance(error, dict) else {}
    location = [str(part) for part in detail.get("loc", ())]
    if detail.get("type") == "extra_forbidden" and location:
        location[-1] = "(an unknown field)"
    return f"{'.'.join(location) or '(document)'}: {detail.get('msg', 'is not valid')}"


def _error(code: str, message: str, path: str) -> Finding:
    return Finding(code, message, Severity.ERROR, path)
