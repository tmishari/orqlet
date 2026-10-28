"""`orqlet validate integrations`: the declaration and the MCP files (ADR-002 decisions 6 to 11).

`integration_findings` is the one function that checks; the command and `doctor` and `sync` call it,
so they cannot disagree. It reads the declaration through `load_integrations` and each MCP file
that exists through the `FileSystem` port. It writes nothing and runs offline.

With a declaration, a JSON MCP file (`.mcp.json`, `.cursor/mcp.json`) is parsed strictly and every
declared entry is compared with `rendered_entry`; `.codex/config.toml` gets the scan of its raw text
only, because no row of the table generates it. Without a declaration nothing is checked, except
that an MCP file which holds the text `orqlet-` gets one warning, so that deleting the declaration
is not silent (ADR-002 decision 11).

A finding names a rule, a position or a closed field name and never repeats a value, an entry name
or a key of a file (ADR-002 decision 9): the files are untrusted input and may hold a credential.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, auto

from orqlet.application.contracts.integrations import Integrations, McpServer
from orqlet.application.ports.documents import DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.usecases.integrations_source import load_integrations
from orqlet.application.usecases.validation import Collector, ValidateServices, ValidationResult
from orqlet.domain.conventions import printable
from orqlet.domain.errors import InvalidPath
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.mcp_credentials import (
    CredentialFinding,
    allowed_auth_modes,
    entry_differences,
    find_literal_credentials,
    mcp_file_path,
    rendered_entry,
)
from orqlet.domain.paths import CanonicalPath

_CLIENTS = ("claude-code", "cursor", "codex")
_JSON_CLIENTS = frozenset({"claude-code", "cursor"})
_MAX_BYTES = 256 * 1024
_MAX_DEPTH = 16
_MAX_ENTRIES = 64
_MAX_STRING = 2048
_PREFIX = "orqlet-"
# The key names that the evidence gives for a command that a file may run or a credential that it
# may hold (AS-IS A-64, A-91 to A-93). Names that the evidence does not give are not listed.
_CLOSED_KEYS = frozenset(
    {"headershelper", "http_headers_helper", "env_http_headers", "bearer_token_env_var"}
)
_SHOWN = 200


class _Read(Enum):
    ABSENT = auto()
    UNREADABLE = auto()
    TEXT = auto()


class _Duplicate(Exception):
    """A JSON object with the same key twice."""


@dataclass(frozen=True, slots=True)
class _Walk:
    """What one pass over a parsed document found."""

    depth: int
    longest: int
    closed_key: bool
    reference: bool
    unencodable: bool


def integration_findings(
    project: FileSystem, loader: DocumentLoader, path: str
) -> tuple[Finding, ...]:
    """Every finding about the declaration at `path` and the MCP files, or the one warning."""
    declaration, found = load_integrations(project, loader, path)
    if declaration is None:
        return found if found else _without_declaration(project)
    return (*found, *_with_declaration(project, declaration))


def validate_integrations(services: ValidateServices, raw_path: str) -> ValidationResult:
    out = Collector()
    findings = integration_findings(services.project, services.loader, raw_path)
    out.findings.extend(_with_printable_path(finding) for finding in findings)
    if _is_absent(services.project, raw_path):
        out.skip(f"{printable(raw_path, _SHOWN)} does not exist, so no integration was checked")
        return out.result()
    errors = sum(1 for finding in out.findings if finding.severity is Severity.ERROR)
    return out.result({"errors": errors, "findings": len(out.findings)})


def _is_absent(project: FileSystem, raw_path: str) -> bool:
    """True when the declaration file is not there; a path that is not usable is not absent."""
    try:
        return project.kind(CanonicalPath.parse(raw_path)) is None
    except (InvalidPath, FileSystemError, OSError):
        return False


def _with_printable_path(finding: Finding) -> Finding:
    """A finding whose path is the argument as typed, which may hold control characters."""
    if finding.path is None:
        return finding
    return Finding(finding.code, finding.message, finding.severity, printable(finding.path, _SHOWN))


# --- no declaration -----------------------------------------------------------------------------


def _without_declaration(project: FileSystem) -> tuple[Finding, ...]:
    """One warning for each MCP file that names an `orqlet-` entry, and nothing else."""
    found: list[Finding] = []
    for client in _CLIENTS:
        path = mcp_file_path(client)
        status, text = _read(project, path)
        if status is _Read.UNREADABLE:
            found.append(
                Finding(
                    "ORQ-I533",
                    f"{path} could not be read, so nothing was checked in it",
                    Severity.INFO,
                    path,
                )
            )
        elif status is _Read.TEXT and _names_an_entry(text, client):
            found.append(
                Finding(
                    "ORQ-W530",
                    f"{path} holds an `{_PREFIX}` name but there is no declaration, so nothing "
                    "was checked in it",
                    Severity.WARNING,
                    path,
                )
            )
    return tuple(found)


def _names_an_entry(text: str, client: str) -> bool:
    """The text `orqlet-` in any letter case, or a decoded entry name that starts with it."""
    if _PREFIX in text.lower():
        return True
    if client not in _JSON_CLIENTS:
        return False
    try:
        document = json.loads(text)
    except (ValueError, RecursionError):
        return False
    entries = document.get("mcpServers") if isinstance(document, dict) else None
    return isinstance(entries, dict) and any(
        str(name).lower().startswith(_PREFIX) for name in entries
    )


# --- with a declaration -------------------------------------------------------------------------


def _with_declaration(project: FileSystem, declaration: Integrations) -> list[Finding]:
    found = [
        Finding(
            "ORQ-I530",
            f"servers[{number}] uses sign-in: its entry gives the agent the user's full "
            "permissions and restricts nothing",
            Severity.INFO,
        )
        for number, server in enumerate(declaration.servers)
        if server.auth.mode == "client-native-oauth" and _registered_clients(declaration, server)
    ]
    for client in _CLIENTS:
        found.extend(_check_file(project, declaration, client))
    return found


def _registered_clients(declaration: Integrations, server: McpServer) -> list[str]:
    return [client for client in _CLIENTS if server in declaration.registered_for(client)]


def _check_file(project: FileSystem, declaration: Integrations, client: str) -> list[Finding]:
    path = mcp_file_path(client)
    declared = declaration.registered_for(client)
    status, text = _read(project, path)
    if status is _Read.ABSENT:
        if not declared:
            return []
        return [
            Finding(
                "ORQ-I532",
                f"{path} does not exist, so the declared entries were not checked",
                Severity.INFO,
                path,
            )
        ]
    if status is _Read.UNREADABLE:
        return [
            _error(
                "ORQ-E534",
                f"{path} cannot be read safely: a link, a directory, a file "
                "that is too large or a file that is not UTF-8",
                path,
            )
        ]
    found = _scan_findings(find_literal_credentials(text), path, raw=True)
    if client not in _JSON_CLIENTS:
        return found
    document, refused = _parse(text, path)
    if document is None:
        return [*found, *refused]
    return [*found, *_check_document(document, declared, client, path)]


def _check_document(
    document: dict[str, object], declared: tuple[McpServer, ...], client: str, path: str
) -> list[Finding]:
    entries = _entries(document)
    walked = _walk(document)
    if walked.unencodable:
        return [_error("ORQ-E534", f"{path} holds text that cannot be encoded", path)]
    if walked.depth > _MAX_DEPTH or walked.longest > _MAX_STRING or len(entries) > _MAX_ENTRIES:
        return [
            _error(
                "ORQ-E534",
                f"{path} is above a limit: {_MAX_DEPTH} levels, {_MAX_ENTRIES} entries or "
                f"{_MAX_STRING} characters in a string",
                path,
            )
        ]
    found = _scan_findings(
        find_literal_credentials(json.dumps(document, ensure_ascii=False, indent=1)),
        path,
        raw=False,
    )
    if walked.closed_key or walked.reference:
        found.append(
            _error(
                "ORQ-E538",
                f"{path} holds a key of the closed list or the text ${{ in an entry or a value",
                path,
            )
        )
    wanted = {f"{_PREFIX}{server.id}": server for server in declared}
    undeclared = 0
    off_table = 0
    for name, entry in entries.items():
        server = wanted.get(name)
        if server is not None:
            found.extend(_compare(server, entry, client, path))
        elif name.lower().startswith(_PREFIX):
            found.append(
                _error(
                    "ORQ-E537",
                    f"{path} holds an undeclared entry whose name starts with `{_PREFIX}`",
                    path,
                )
            )
        else:
            undeclared += 1
            address = entry.get("url")
            if not isinstance(address, str) or not allowed_auth_modes(address, client):
                off_table += 1
    for name, server in wanted.items():
        if name not in entries:
            found.append(
                _error(
                    "ORQ-E536", f"{path} lacks the entry of the declared server {server.id}", path
                )
            )
    if undeclared:
        found.append(
            Finding(
                "ORQ-I531",
                f"{path} holds {undeclared} undeclared entries, {off_table} of them with an "
                "address that is not on the table",
                Severity.INFO,
                path,
            )
        )
    return found


def _compare(server: McpServer, entry: dict[str, object], client: str, path: str) -> list[Finding]:
    """A declared entry against the one that `rendered_entry` builds for it."""
    variable = server.auth.env_refs[0] if server.auth.mode == "env-ref" else None
    try:
        pinned = rendered_entry(server.id, server.identity.url or "", variable, client)
    except ValueError:
        return []  # the loader refuses a combination that the table does not enable
    fields = entry_differences(pinned, entry)
    if not fields:
        return []
    return [
        _error(
            "ORQ-E535",
            f"the entry of the declared server {server.id} differs in {', '.join(fields)}",
            path,
        )
    ]


# --- reading and parsing ------------------------------------------------------------------------


def _read(project: FileSystem, path: str) -> tuple[_Read, str]:
    try:
        target = CanonicalPath.parse(path)
        kind = project.kind(target)
        if kind is None:
            return _Read.ABSENT, ""
        if kind is not FileKind.FILE:
            return _Read.UNREADABLE, ""
        data = project.read_bytes(target)
    except (InvalidPath, FileSystemError, OSError):
        return _Read.UNREADABLE, ""
    if len(data) > _MAX_BYTES:
        return _Read.UNREADABLE, ""
    try:
        return _Read.TEXT, data.decode("utf-8")
    except UnicodeDecodeError:
        return _Read.UNREADABLE, ""


def _parse(text: str, path: str) -> tuple[dict[str, object] | None, list[Finding]]:
    """The JSON object in `text`, or no document and one error that names the rule."""
    try:
        document = json.loads(text, object_pairs_hook=_no_duplicates)
    except _Duplicate:
        return None, [_error("ORQ-E534", f"{path} breaks the rule duplicate-key", path)]
    except (ValueError, RecursionError):
        return None, [_error("ORQ-E534", f"{path} is not valid JSON", path)]
    if not isinstance(document, dict):
        return None, [_error("ORQ-E534", f"{path} is not a JSON object", path)]
    entries = document.get("mcpServers", {})
    if not isinstance(entries, dict) or not all(isinstance(e, dict) for e in entries.values()):
        return None, [
            _error("ORQ-E534", f"{path} has a shape that is not mcpServers of objects", path)
        ]
    return document, []


def _entries(document: dict[str, object]) -> dict[str, dict[str, object]]:
    """The entries of a document that `_parse` has checked: a mapping of objects."""
    entries = document.get("mcpServers", {})
    if not isinstance(entries, dict):
        return {}
    return {name: entry for name, entry in entries.items() if isinstance(entry, dict)}


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _Duplicate
        result[key] = value
    return result


def _walk(document: object) -> _Walk:
    """Depth, the longest string, the closed keys, the text `${` and text that cannot be encoded."""
    depth = longest = 0
    closed = reference = unencodable = False
    stack: list[tuple[object, int]] = [(document, 1)]
    while stack:
        node, level = stack.pop()
        if isinstance(node, dict):
            depth = max(depth, level)
            for key, value in node.items():
                longest = max(longest, len(key))
                reference = reference or "${" in key
                closed = closed or key.lower() in _CLOSED_KEYS
                unencodable = unencodable or not _encodable(key)
                stack.append((value, level + 1))
        elif isinstance(node, list):
            depth = max(depth, level)
            stack.extend((item, level + 1) for item in node)
        elif isinstance(node, str):
            longest = max(longest, len(node))
            reference = reference or "${" in node
            unencodable = unencodable or not _encodable(node)
    return _Walk(depth, longest, closed, reference, unencodable)


def _encodable(text: str) -> bool:
    """False for a lone surrogate, which a JSON escape can produce and no file can hold."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _scan_findings(items: tuple[CredentialFinding, ...], path: str, *, raw: bool) -> list[Finding]:
    """One error for each scan finding: a rule and, for the raw text, a line; never the text."""
    return [
        _error(
            "ORQ-E539",
            f"{path} {_where(item, raw)}: the rule {item.rule} matched",
            path,
        )
        for item in items
    ]


def _where(item: CredentialFinding, raw: bool) -> str:
    return f"line {item.line}" if raw else "decoded text"


def _error(code: str, message: str, path: str) -> Finding:
    return Finding(code, message, Severity.ERROR, path)
