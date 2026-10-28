"""The one reader of `.orqlet/integrations.yaml` (ADR-003 decision 3; ADR-002 decisions 2, 8, 9).

`upgrade`, `validate integrations`, `doctor` and `sync` all take the result of `load_integrations`,
so no two readers can disagree about the declaration. The result has three shapes: an absent file
gives `(None, ())`; a file that cannot be used gives `(None, findings)` with at least one error;
a valid file gives the declaration and findings that are information only.

The file is untrusted input (ORQLET-SEC-002): it is read through the `FileSystem` port, refused
above 256 KiB, parsed only by the strict loader, and checked against its contract, the closed table
of the domain and the scan. A finding names a rule, a position or a closed field name and never
repeats a value or a key of the file (ORQLET-SEC-003): the loader's own messages and the contract
loader's default text, which may hold a key or a tag, are not passed on.
"""

from __future__ import annotations

from pydantic import ValidationError

from orqlet.application.contracts.integrations import Integrations
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.domain.errors import InvalidPath
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.mcp_credentials import allowed_auth_modes, find_literal_credentials
from orqlet.domain.paths import CanonicalPath

_PATH = ".orqlet/integrations.yaml"
_MAX_BYTES = 256 * 1024
# The maps whose keys are free text: a key in an error location must not be printed.
_FREE_FORM = frozenset({"per_client", "roles", "owner_review"})
_CLIENTS = ("claude-code", "codex", "cursor")


def integrations_path() -> CanonicalPath:
    """Where the declaration lives."""
    return CanonicalPath.parse(_PATH)


def parse_integrations(
    loader: DocumentLoader, raw: bytes, source: str
) -> tuple[Integrations | None, tuple[Finding, ...]]:
    """The declaration in `raw`, or no declaration and the findings that say why not."""
    if len(raw) > _MAX_BYTES:
        return None, (
            _error("ORQ-E530", "declaration-unreadable: the file is larger than 256 KiB", source),
        )
    try:
        data = loader.load(raw, source=source)
    except DocumentError:
        return None, (
            _error(
                "ORQ-E530",
                "declaration-unreadable: the file breaks the rules for reading a document",
                source,
            ),
        )
    try:
        declaration = Integrations.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(_problem(error) for error in exc.errors(include_input=False))
        return None, (
            _error("ORQ-E531", f"the declaration fails its contract: {problems}", source),
        )
    scanned = _scan(raw, source)
    if scanned:
        return None, scanned
    refused = _table(declaration, source)
    if refused:
        return None, refused
    return declaration, ()


def load_integrations(
    project: FileSystem, loader: DocumentLoader, path: str
) -> tuple[Integrations | None, tuple[Finding, ...]]:
    """The declaration at `path`: none and no finding when the file is absent."""
    try:
        target = CanonicalPath.parse(path)
    except InvalidPath:
        return None, (
            _error("ORQ-E530", "declaration-unreadable: the path is not a usable path", path),
        )
    try:
        kind = project.kind(target)
        if kind is None:
            return None, ()
        if kind is not FileKind.FILE:
            return None, (_error("ORQ-E530", "declaration-unreadable: not a regular file", path),)
        raw = project.read_bytes(target)
    except (FileSystemError, OSError):
        return None, (
            _error("ORQ-E530", "declaration-unreadable: the file cannot be read safely", path),
        )
    return parse_integrations(loader, raw, path)


def _scan(raw: bytes, source: str) -> tuple[Finding, ...]:
    """A credential-shaped text in the declaration: a rule and a line, never the text."""
    text = raw.decode("utf-8", errors="replace")
    return tuple(
        _error("ORQ-E533", f"line {item.line}: the rule {item.rule} matched", source)
        for item in find_literal_credentials(text)
    )


def _table(declaration: Integrations, source: str) -> tuple[Finding, ...]:
    """Every server that is registered for a client must use a mode that the table enables."""
    refused = []
    for number, server in enumerate(declaration.servers):
        for client in _CLIENTS:
            if server not in declaration.registered_for(client):
                continue
            modes = allowed_auth_modes(server.identity.url or "", client)
            if server.auth.mode not in modes:
                refused.append(
                    _error(
                        "ORQ-E532",
                        f"servers[{number}] is registered for {client} with a mode that the "
                        "table of this release does not enable for its address",
                        source,
                    )
                )
    return tuple(refused)


def _problem(error: object) -> str:
    """One validation error as `location: message`, without the input or a stranger's key."""
    detail = error if isinstance(error, dict) else {}
    unknown = detail.get("type") == "extra_forbidden"
    parts: list[str] = []
    previous = ""
    for part in detail.get("loc", ()):
        if isinstance(part, int):
            parts.append(f"[{part}]")
        elif previous in _FREE_FORM:
            parts.append("<key>")
        else:
            parts.append(str(part))
        previous = part if isinstance(part, str) else ""
    if unknown and parts:
        parts[-1] = "unknown-key"
    location = ".".join(parts).replace(".[", "[") or "(document)"
    return f"{location}: {detail.get('msg', 'is not valid')}"


def _error(code: str, message: str, path: str) -> Finding:
    return Finding(code, message, Severity.ERROR, path)
