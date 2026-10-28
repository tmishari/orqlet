"""The pure rules that keep a credential out of a committed MCP entry (ADR-002 of mcp-or-plugins).

Everything here takes plain values and returns plain values: no file, no environment, no clock.
The closed table of addresses, the name patterns, the key sets and the credential patterns are
private names, so the module has the public surface that the design lists and nothing else.

A finding is a line number and the name of a rule, and a refusal says which rule failed and never
what was passed in. `entry_differences` names fields from a closed vocabulary. The one exception is
`referenced_variables`: it returns names exactly as they are written, and a name may be a secret
that was pasted in the wrong place, so a caller compares the names and never prints them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

# --- the closed table (ADR-002 decision 2) -------------------------------------------------------
_OAUTH = "client-native-oauth"
_ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"
_CLAUDE_CODE = "claude-code"
# One row in this release. Codex, Cursor, GitHub and every variable-based entry are enabled by a
# later release that cites the check records of ADR-004; the adopter's repository cannot read them.
_ENABLED: Mapping[tuple[str, str], tuple[str, ...]] = {(_ATLASSIAN, _CLAUDE_CODE): (_OAUTH,)}

_FILE_PATHS: Mapping[str, str] = {
    _CLAUDE_CODE: ".mcp.json",
    "cursor": ".cursor/mcp.json",
    "codex": ".codex/config.toml",
}

# --- names (ADR-002 decisions 3 and 4) -----------------------------------------------------------
# re.ASCII and fullmatch, never IGNORECASE: U+212A (Kelvin sign) and a trailing newline must fail.
_ID = re.compile(r"[a-z][a-z0-9-]{0,31}", re.ASCII)
_VARIABLE = re.compile(r"ORQLET_MCP_[A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)*", re.ASCII)
_MAX_VARIABLE = 48
# A literal https address: no user information, query, fragment, `${`, backslash or percent sign.
_ADDRESS = re.compile(
    r"https://[A-Za-z0-9.-]{1,253}(?::[0-9]{1,5})?(?:/[A-Za-z0-9._~/-]{0,2000})?", re.ASCII
)

# --- the scan (ADR-002 decision 7) ---------------------------------------------------------------
_MAX_LINE = 4096
_OVERSIZE = "oversize"
_RULE_TOKEN = "token-prefix"
_RULE_JWT = "jwt-shape"
_RULE_USER_INFORMATION = "url-user-information"
_RULE_QUERY = "url-query-credential"
_RULE_AUTHORIZATION = "authorization-literal"
_RULE_KEY = "credential-key-literal"

# Every repetition is bounded, so the worst case of one line of at most _MAX_LINE characters is
# fixed. Where a run of letters follows a fixed prefix the repetition is also possessive, so the
# engine does not give characters back. The runs that must see a whole line (an address, its
# authority and the leading blanks of a key) are bounded by the line cap, so nothing in the
# scanned window is skipped; the runs inside a token stay at 2048. The tests time the worst lines.
_FLAGS = re.ASCII | re.IGNORECASE
_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"gh[pousr]_[A-Za-z0-9]{36,255}+"
    r"|github_pat_[A-Za-z0-9_]{22,255}+"
    r"|ATATT[A-Za-z0-9_=-]{20,2048}+"
    r"|sk-ant-[A-Za-z0-9_-]{20,2048}+"
    r"|AKIA[0-9A-Z]{16}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,2048}+"
    r")",
    re.ASCII,
)
_JWT = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,2048}+\.[A-Za-z0-9_-]{8,2048}+\.[A-Za-z0-9_-]{8,2048}+",
    re.ASCII,
)
_URL = re.compile(
    r"(?<![A-Za-z0-9+.-])[A-Za-z][A-Za-z0-9+.-]{0,31}://[^\s\"'<>]{0,4096}+", re.ASCII
)
_USER_INFORMATION = re.compile(
    r"(?<![A-Za-z0-9+.-])[A-Za-z][A-Za-z0-9+.-]{0,31}://[^/?#\s\"'<>@]{1,4096}+@", re.ASCII
)
_PERCENT = re.compile(r"%([0-9A-Fa-f]{2})", re.ASCII)
_QUERY_NAMES = frozenset(
    {"key", "api_key", "apikey", "token", "access_token", "secret", "password", "sig"}
)
_AUTHORIZATION = re.compile(
    r"authorization[\"']?[ \t]{0,64}[:=][ \t]{0,64}[\"']?([^\"'\n]{0,2048}+)", _FLAGS
)
_ANCHORED = re.compile(
    r"Bearer \$\{(?:env:)?ORQLET_MCP_[A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)*\}", re.ASCII
)
# The scheme word, then a token that holds a digit, `=`, `+` or `/`: ordinary prose such as
# "Basic configuration" has none of them and is not a credential.
_BEARER_OR_BASIC = re.compile(
    r"(?<![A-Za-z0-9])(?i:Bearer|Basic)[ \t]{1,64}(?!\$\{)"
    r"(?=[A-Za-z0-9._~+/=-]{0,2048}[0-9=+/])[A-Za-z0-9._~+/=-]{8,2048}+",
    re.ASCII,
)
_LINE_KEY = re.compile(
    r"[ \t]{0,4096}[\"']?([A-Za-z0-9_.-]{1,128})[\"']?[ \t]{0,64}[:=][ \t]{0,64}(.*)", re.ASCII
)
_PAIR = re.compile(
    r"\"([A-Za-z0-9_.-]{1,128})\"[ \t]{0,64}:[ \t]{0,64}\"([^\"\n]{0,2048}+)\"", re.ASCII
)
_CREDENTIAL_WORDS = (
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "private_key",
    "authorization",
)
_REFERENCE_HOLDER = "bearer_token_env_var"

# --- references and entries (ADR-002 decisions 6 and 9) ------------------------------------------
_REFERENCE = re.compile(
    r"\$\{(?:env:)?([A-Za-z_][A-Za-z0-9_]{0,255})(?::-[^}]{0,2048}+)?\}", re.ASCII
)
# A value that is only one reference holds nothing literal: `${NAME}` or `${env:NAME}`.
_WHOLE_REFERENCE = re.compile(r"\$\{(?:env:)?[A-Za-z_][A-Za-z0-9_]{0,255}\}", re.ASCII)
_MAX_DEPTH = 32
_ENTRY_FIELDS = ("type", "url", "headers", "bearer_token_env_var")
_UNKNOWN_KEY = "unknown-key"
_MISSING = object()


@dataclass(frozen=True, slots=True)
class CredentialFinding:
    """Where a rule matched and which rule: never the text that matched, never a key."""

    line: int  # one-based
    rule: str


def name_problems(server_id: str, url: str, variable: str | None) -> tuple[str, ...]:
    """The names of the rules that an id, an address and a variable name break, or ()."""
    problems: list[str] = []
    if _ID.fullmatch(server_id) is None:
        problems.append("server-id-pattern")
    if variable is not None:
        if _VARIABLE.fullmatch(variable) is None:
            problems.append("variable-pattern")
        if len(variable) > _MAX_VARIABLE:
            problems.append("variable-length")
    if _ADDRESS.fullmatch(url) is None:
        problems.append("address-literal-https")
    return tuple(problems)


def allowed_auth_modes(url: str, client: str) -> tuple[str, ...]:
    """The modes that this release enables for an exact address and a client; () for the rest."""
    return _ENABLED.get((url, client), ())


def mcp_file_path(client: str) -> str:
    """The path of a client's MCP file. An unknown client is refused without being echoed."""
    path = _FILE_PATHS.get(client)
    if path is None:
        raise ValueError("the client has no MCP file in this release")
    return path


def rendered_entry(
    server_id: str, url: str, variable: str | None, client: str
) -> dict[str, object]:
    """The one entry that this release builds: Atlassian OAuth for Claude Code.

    The renderer writes this mapping and the validator compares a file with it, so the pin and
    the output cannot drift apart. Anything else is refused with rule names, never with a value.
    """
    problems = name_problems(server_id, url, variable)
    if problems:
        raise ValueError("the entry breaks the rules: " + ", ".join(problems))
    if variable is not None:
        raise ValueError("a variable is not enabled in this release")
    if _OAUTH not in allowed_auth_modes(url, client):
        raise ValueError("the address and the client are not enabled in this release")
    return {"type": "http", "url": url}


def entry_differences(pinned: Mapping[str, object], found: Mapping[str, object]) -> tuple[str, ...]:
    """The fields in which a found entry differs from the pinned one, from a closed vocabulary.

    A key that is not an entry field is reported as `unknown-key` and its name is never returned.
    """
    differing = [
        field
        for field in _ENTRY_FIELDS
        if pinned.get(field, _MISSING) != found.get(field, _MISSING)
    ]
    others = {key for key in (*pinned, *found) if key not in _ENTRY_FIELDS}
    if any(pinned.get(key, _MISSING) != found.get(key, _MISSING) for key in others):
        differing.append(_UNKNOWN_KEY)
    return tuple(differing)


def referenced_variables(entry: Mapping[str, object]) -> tuple[str, ...]:
    """The variable names that an entry refers to, in order of appearance and without repeats.

    Names are returned as written and are for comparison only: never print them. Content nested
    deeper than 32 levels is not searched, and a reference inside a default (`${A:-${B}}`) reports
    only the outer name; the caller caps depth and size first (ADR-002 decision 8).
    """
    names: dict[str, None] = {}
    _collect_references(entry, names, 0)
    return tuple(names)


def find_literal_credentials(text: str) -> tuple[CredentialFinding, ...]:
    """Line numbers and rule names for credential-shaped content; never a value or a raw key."""
    found: set[tuple[int, str]] = set()
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.removesuffix("\r")
        if len(line) > _MAX_LINE:
            # A credential past the cap must not hide behind it, so the long line is a finding.
            found.add((number, _OVERSIZE))
        found.update((number, rule) for rule in _rules_matching(line[:_MAX_LINE]))
    return tuple(CredentialFinding(line, rule) for line, rule in sorted(found))


# --- helpers -------------------------------------------------------------------------------------
def _collect_references(value: object, names: dict[str, None], depth: int) -> None:
    if depth > _MAX_DEPTH:
        return
    if isinstance(value, str):
        for match in _REFERENCE.finditer(value):
            names[match.group(1)] = None
    elif isinstance(value, Mapping):
        for key, item in value.items():
            if key == _REFERENCE_HOLDER and isinstance(item, str) and item:
                names[item] = None
            _collect_references(item, names, depth + 1)
    elif isinstance(value, list | tuple):
        for item in value:
            _collect_references(item, names, depth + 1)


def _rules_matching(line: str) -> set[str]:
    rules: set[str] = set()
    if _TOKEN.search(line):
        rules.add(_RULE_TOKEN)
    if _JWT.search(line):
        rules.add(_RULE_JWT)
    if _USER_INFORMATION.search(line):
        rules.add(_RULE_USER_INFORMATION)
    if _has_credential_query(line):
        rules.add(_RULE_QUERY)
    if _has_literal_authorization(line):
        rules.add(_RULE_AUTHORIZATION)
    if _has_credential_key(line):
        rules.add(_RULE_KEY)
    return rules


def _decoded(name: str) -> str:
    """Percent-decoding by hand: the domain may not import urllib."""
    return _PERCENT.sub(lambda match: chr(int(match.group(1), 16)), name)


def _has_credential_query(line: str) -> bool:
    for url in _URL.finditer(line):
        query = url.group(0).partition("?")[2].partition("#")[0]
        for parameter in query.split("&"):
            name, separator, _ = parameter.partition("=")
            if separator and _decoded(name).lower().replace("-", "_") in _QUERY_NAMES:
                return True
    return False


def _has_literal_authorization(line: str) -> bool:
    for match in _AUTHORIZATION.finditer(line):
        value = match.group(1).strip()
        if value and _ANCHORED.fullmatch(value) is None:
            return True
    return _BEARER_OR_BASIC.search(line) is not None


def _is_literal(value: str) -> bool:
    """A value that holds something: not empty, not a nested structure, not only a reference.

    A quoted value is a string even when it starts with `{` or `[`. A value that mixes a literal
    with a reference is still a literal.
    """
    stripped = value.strip().removesuffix(",").strip()
    plain = stripped.strip("\"'")
    if not plain or (stripped[:1] not in "\"'" and plain[0] in "{["):
        return False
    return _WHOLE_REFERENCE.fullmatch(plain) is None


def _has_credential_key(line: str) -> bool:
    # The value of a JSON pair was matched inside its quotes: put them back, it is a string.
    pairs: list[tuple[str, str]] = [(m.group(1), f'"{m.group(2)}"') for m in _PAIR.finditer(line)]
    keyed = _LINE_KEY.fullmatch(line)
    if keyed is not None:
        pairs.append((keyed.group(1), keyed.group(2)))
    return any(_is_credential_pair(key, value) for key, value in pairs)


def _is_credential_pair(key: str, value: str) -> bool:
    # `x-api-key` and `x_api_key` are the same name. A key that ends in `authorization` is judged
    # by the Authorization rule, which also accepts the anchored template.
    lowered = key.lower().replace("-", "_")
    if lowered.endswith("authorization"):
        return False
    if not any(word in lowered for word in _CREDENTIAL_WORDS) or not _is_literal(value):
        return False
    if lowered == _REFERENCE_HOLDER:
        plain = value.strip().removesuffix(",").strip().strip("\"'")
        return not (_VARIABLE.fullmatch(plain) and len(plain) <= _MAX_VARIABLE)
    return True
