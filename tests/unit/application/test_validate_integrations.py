"""`integration_findings` and `validate_integrations` (task mcp-or-plugins, phase P-3).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-00N-*.md`
under docs/design/mcp-or-plugins/design/, EC-n are the expected changes of the manifest.yaml next
to them, and AC-1 to AC-10 are the acceptance criteria of phase P-3 in
docs/design/mcp-or-plugins/plan.yaml. The plan fixes the finding codes of the validator: ORQ-E534
an MCP file cannot be read safely (link, directory, unreadable, not UTF-8, above the caps, wrong
shape, duplicate key); ORQ-E535 a declared entry differs from `rendered_entry`; ORQ-E536 a declared
entry is absent from an existing file; ORQ-E537 an undeclared `orqlet-*` entry; ORQ-E538 a closed
key or the text `${` in an entry; ORQ-E539 a scan finding in an MCP file, raw or decoded; ORQ-W530
the declaration is absent and an MCP file holds `orqlet-`; ORQ-I530 an OAuth entry carries the
user's full permissions; ORQ-I531 the counts of undeclared entries; ORQ-I532 an MCP file is absent;
ORQ-I533 an MCP file could not be read and nothing was checked in it (declaration absent). The
errors of the declaration (ORQ-E530 to ORQ-E533) are the reader's and are tested in
test_integrations_source.py.

These tests were written first, by the Tester of phase P-3, before the validator existed. The one
declaration that the reader accepts names the Atlassian address for Claude Code with
`client-native-oauth` (ADR-002 decision 2); its one entry is `orqlet-docs` with the keys `type` and
`url` (ADR-003 decision 4). Files are written as JSON text; a JSON escape, a lone surrogate and a
credential shape are assembled at run time and never written as one literal (ORQLET-SEC-003). Where
a test needs an escape to be the only reason for a finding, it asserts that the raw text alone is
clean. The file system is the in-memory fake of tests/fakes (ORQLET-TEST-001).

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- the wording of any message beyond what a criterion states (the closed field names of ORQ-E535,
  the rule `duplicate-key` of ORQ-E534, the word `decoded` and the rule of a decoded ORQ-E539, the
  words about full permissions of ORQ-I530, the two numbers of ORQ-I531);
- what `Finding.path` holds, except that an ORQ-E534 finding names its file (AC-5: "for that file");
- whether ORQ-I531 is printed when there is no undeclared entry, whether it is one finding per file
  or one in all, and how its counts add up over several files (only a single file is tested);
- whether ORQ-I532 is printed for the file of a client that has no registered server, and whether
  ORQ-W530 is printed once per file or once in all (only one file is tested for a count);
- the code of a lone surrogate (ORQ-E534 and ORQ-E539 are both accepted), the exact counting of the
  nesting limit at 16 (clear cases only), whether a key above 2048 characters is a string, and
  whether a closed key written as a string value (not as a key) is a finding;
- a file without the key `mcpServers`, a file that starts with a byte-order mark, and what the
  validator does with MCP files when the declaration is invalid;
- whether `validate integrations` also prints the warning ORQ-W530 when the declaration is absent;
- how a path with control characters is printed (the argument is a file name, not a key).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.filesystem import FileSystemError

# isort: split
from orqlet.application.usecases.validate_integrations import (
    integration_findings,
    validate_integrations,
)

# isort: split
from orqlet.application.usecases.validation import ValidateServices, ValidationResult
from orqlet.domain.findings import Finding, Severity, Verdict
from orqlet.domain.mcp_credentials import entry_differences, find_literal_credentials
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.python_api import canonical_signature, extract_module_api
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED

pytestmark = pytest.mark.unit

DECLARATION_PATH = ".orqlet/integrations.yaml"
MCP = ".mcp.json"
CURSOR = ".cursor/mcp.json"
CODEX = ".codex/config.toml"
LIMIT = 256 * 1024  # ADR-002 decision 8: a file above 256 KiB is refused
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
LOADER = StrictYamlLoader()
ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"  # the one address of the table (ADR-002 decision 2)
OAUTH = "client-native-oauth"
EDITABLE = "client-enforced-editable"
ENTRY: dict[str, Any] = {"type": "http", "url": ATLASSIAN}  # the entry of ADR-003 decision 4

UNREADABLE_FILE = "ORQ-E534"
DIFFERS = "ORQ-E535"
ABSENT_ENTRY = "ORQ-E536"
UNDECLARED = "ORQ-E537"
CLOSED = "ORQ-E538"
SCANNED = "ORQ-E539"
NOT_CHECKED = "ORQ-W530"
FULL_PERMISSIONS = "ORQ-I530"
COUNTS = "ORQ-I531"
NO_FILE = "ORQ-I532"
NOT_READ = "ORQ-I533"
DECLARATION_ERRORS = {"ORQ-E530", "ORQ-E531", "ORQ-E532", "ORQ-E533"}
# ADR-002 decision 6: the key names that the evidence gives, compared case-insensitively.
EVIDENCE_KEYS = ("headersHelper", "http_headers_helper", "env_http_headers", "bearer_token_env_var")

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0JxQz4M", "Ka8Ty2Vb"))
PASSWORD = "".join(("hunter", "2Qx", "9Lp", "Vw4"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))
EYJ = "ey" + "J"
JWT = ".".join((EYJ + "hbGciOiJIUzI1NiJ9", EYJ + "zdWIiOiJ0ZXN0In0", "aB3" * 15))
MARKER = OPAQUE.lower()  # a name that is not a credential shape and must never come back


# --- helpers --------------------------------------------------------------------------------------


class Files(MemoryFileSystem):
    """The in-memory project, with files that can be found and cannot be read."""

    def __init__(self) -> None:
        super().__init__()
        self.unreadable: set[str] = set()

    def read_bytes(self, path: CanonicalPath) -> bytes:
        if str(path) in self.unreadable:
            raise FileSystemError("the file cannot be read")
        return super().read_bytes(path)


def fixture() -> dict[str, Any]:
    loaded = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def server(
    server_id: str = "docs",
    *,
    url: str = ATLASSIAN,
    registered: Sequence[str] = ("claude-code",),
) -> dict[str, Any]:
    """A server of the valid declaration, built from the fixture's first one."""
    base: dict[str, Any] = json.loads(json.dumps(fixture()["servers"][0]))
    base.update(
        id=server_id,
        identity={"kind": "remote", "url": url},
        registration={"name": f"orqlet-{server_id}", "mode": "read-only", "enforced_by": EDITABLE},
        per_client={client: {"register": True, "enforced_by": EDITABLE} for client in registered},
        clients=list(registered),
    )
    return base


def declaration(*servers: dict[str, Any]) -> bytes:
    data = fixture()
    data["servers"] = list(servers)
    data["roles"] = {"architecture-reviewer": {"servers": [item["id"] for item in servers]}}
    return json.dumps(data, indent=2).encode()


DECLARED = declaration(server())  # one registered OAuth server `docs`: the entry `orqlet-docs`
TWO_DECLARED = declaration(server("docs"), server("wiki"))


def entries_file(entries: Mapping[str, object], **top: object) -> bytes:
    """An MCP file as JSON text: one entry per line, so that a scan finding has a line."""
    members = ",\n".join(
        f"    {json.dumps(name)}: {json.dumps(body)}" for name, body in entries.items()
    )
    extra = "".join(f",\n  {json.dumps(key)}: {json.dumps(value)}" for key, value in top.items())
    return f'{{\n  "mcpServers": {{\n{members}\n  }}{extra}\n}}\n'.encode()


def raw_file(*members: str, top: str = "") -> bytes:
    """An MCP file whose entries and top-level members are raw JSON text, escapes included."""
    body = ",\n".join(f"    {member}" for member in members)
    tail = f",\n  {top}" if top else ""
    return f'{{\n  "mcpServers": {{\n{body}\n  }}{tail}\n}}\n'.encode()


def escaped(char: str) -> str:
    """The JSON escape of one character, assembled at run time: `g` gives backslash-u-0067."""
    return f"\\u{ord(char):04x}"


def with_escape(text: str, index: int) -> str:
    """`text` with the character at `index` written as a JSON escape."""
    return text[:index] + escaped(text[index]) + text[index + 1 :]


GOOD = entries_file({"orqlet-docs": ENTRY})


def put(project: MemoryFileSystem, path: str, data: bytes | str) -> None:
    raw = data.encode() if isinstance(data, str) else data
    project.write_atomic(CanonicalPath.parse(path), raw)


def project_with(
    files: Mapping[str, bytes | str] | None = None, *, declared: bytes | None = DECLARED
) -> Files:
    """A project with the declaration (unless `declared` is None) and the given MCP files."""
    project = Files()
    if declared is not None:
        put(project, DECLARATION_PATH, declared)
    for path, data in (files or {}).items():
        put(project, path, data)
    return project


def services_for(project: MemoryFileSystem) -> ValidateServices:
    return ValidateServices(project=project, vcs=FakeVcs(), loader=LOADER, workflow=PINNED)


def run(project: MemoryFileSystem, path: str = DECLARATION_PATH) -> ValidationResult:
    return validate_integrations(services_for(project), path)


def found(project: MemoryFileSystem, path: str = DECLARATION_PATH) -> tuple[Finding, ...]:
    return integration_findings(project, LOADER, path)


def codes(findings: Sequence[Finding]) -> set[str]:
    return {finding.code for finding in findings}


def with_code(findings: Sequence[Finding], code: str) -> list[Finding]:
    return [finding for finding in findings if finding.code == code]


def errors_of(findings: Sequence[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.severity is Severity.ERROR]


def names(finding: Finding, path: str) -> bool:
    """True when the finding names `path` in its path field or in its message."""
    return path in (finding.path or "") or path in finding.message


def shown(findings: Sequence[Finding]) -> str:
    """Everything that findings show: code, message, path and the representation."""
    return "\n".join(
        f"{finding.code}\n{finding.message}\n{finding.path}\n{finding!r}" for finding in findings
    )


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it (any letter case).

    A window of 8 characters of a random-looking secret cannot appear in a fixed message by chance.
    """
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def decoded_text(raw: bytes) -> str:
    """The re-serialisation that ADR-002 decision 7 scans: every decoded key and value."""
    return json.dumps(json.loads(raw), ensure_ascii=False, indent=1)


def padded(data: bytes, size: int) -> bytes:
    """`data` followed by blank lines of 64 bytes, so that the file has exactly `size` bytes."""
    assert len(data) <= size
    lines, rest = divmod(size - len(data), 64)
    return data + (b" " * 63 + b"\n") * lines + b" " * rest


def team(extra: str = "") -> str:
    """An undeclared entry as raw JSON text, with `extra` members written after `type` and `url`."""
    return f'"team": {{"type": "http", "url": "https://team.example.com/mcp"{extra}}}'


def other_entry(**fields: object) -> dict[str, object]:
    """An undeclared entry that carries `fields` (a key of `fields` may replace `type` or `url`)."""
    return {"type": "http", "url": "https://team.example.com/mcp", **fields}


def in_team(**fields: object) -> bytes:
    """The declared entry and an undeclared one that carries `fields`."""
    return entries_file({"orqlet-docs": ENTRY, "team": other_entry(**fields)})


def team_only(**fields: object) -> bytes:
    """An undeclared entry that carries `fields`, and no entry whose name starts with `orqlet-`."""
    return entries_file({"team": other_entry(**fields)})


def assert_fails_with(result: ValidationResult, *wanted: str) -> list[Finding]:
    assert result.verdict is Verdict.FAIL, shown(result.findings)
    present = {finding.code for finding in errors_of(result.findings)}
    assert set(wanted) <= present, (wanted, present)
    return [finding for finding in result.findings if finding.code in wanted]


def assert_passes(result: ValidationResult) -> None:
    assert result.verdict is Verdict.PASS, shown(result.findings)
    assert result.errors == ()
    assert result.not_run == ()


def all_information(findings: Sequence[Finding]) -> bool:
    return all(finding.severity is Severity.INFO for finding in findings)


# --- EC-4, EC-5, AC-10: the signatures and the public names -----------------------------------


def test_the_module_has_exactly_the_two_public_names_that_the_manifest_adds() -> None:
    """AC-10. expected_behavior_source: AC-10 ("every other new name of the new modules starts with
    an underscore"; the closed key list is "a private constant of validate_integrations.py"), EC-4
    and EC-5 (the two signatures, produced by the extractor)."""
    import orqlet.application.usecases.validate_integrations as module

    assert module.__file__ is not None
    api = extract_module_api(Path(module.__file__).read_text(encoding="utf-8"))

    assert api.errors == ()
    assert api.manual == ()
    assert {name: symbol.signature for name, symbol in api.symbols.items()} == {
        "validate_integrations": canonical_signature(
            "def validate_integrations(services: ValidateServices, raw_path: str)"
            " -> ValidationResult"
        ),
        "integration_findings": canonical_signature(
            "def integration_findings(project: FileSystem, loader: DocumentLoader, path: str)"
            " -> tuple[Finding, ...]"
        ),
    }


# --- PASS ----------------------------------------------------------------------------------------


def test_a_file_that_holds_exactly_the_declared_entry_passes() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (a declared entry that equals
    `rendered_entry` is no finding) and ADR-003 decision 4 (the entry is `{"type": "http", "url":
    <address>}`). The only findings are information: the full permissions of the sign-in and the
    files that are absent."""
    result = run(project_with({MCP: GOOD}))

    assert_passes(result)
    assert all_information(result.findings)
    assert with_code(result.findings, FULL_PERMISSIONS)


def test_the_findings_of_the_shared_function_are_the_findings_of_the_command() -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 6 ("`validate integrations` and `doctor`
    call the shared function `integration_findings`, so exit 3 and exit 5 come from one reader")
    and EC-5."""
    project = project_with({MCP: GOOD})

    assert codes(found(project)) == codes(run(project).findings)


@pytest.mark.parametrize(
    "content",
    [
        b'{"mcpServers": {"orqlet-docs": {"url": "' + ATLASSIAN.encode() + b'", "type": "http"}}}',
        b'{"mcpServers":{"orqlet-docs":{"type":"http","url":"' + ATLASSIAN.encode() + b'"}}}',
        GOOD.replace(b"\n", b"\r\n"),
        GOOD + b"\n\n   \n",
        entries_file({"orqlet-docs": ENTRY}, inputs=[], note="kept by the team"),
    ],
    ids=[
        "keys-in-another-order",
        "compact",
        "crlf-line-ends",
        "trailing-blank-lines",
        "other-top-level-keys",
    ],
)
def test_the_entry_is_compared_as_a_mapping_and_not_as_text(content: bytes) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 ("the validator compares a file with it
    through `entry_differences`") and decision 6 ("Top-level keys other than `mcpServers` are not
    examined")."""
    assert_passes(run(project_with({MCP: content})))


def test_two_declared_servers_need_two_entries() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 ("The set of names that a file may hold as
    declared entries is exactly `orqlet-<id>` of those servers"): both entries present is a pass."""
    both = entries_file({"orqlet-docs": ENTRY, "orqlet-wiki": ENTRY})

    assert_passes(run(project_with({MCP: both}, declared=TWO_DECLARED)))


def test_validating_writes_nothing_and_gives_the_same_answer_twice() -> None:
    """AC-3. expected_behavior_source: the module docstring of validation.py ("A validator never
    writes") and ORQLET-DET-001."""
    project = project_with({MCP: in_team(headersHelper="x"), CURSOR: GOOD})
    before = project.snapshot()

    first, second = run(project), run(project)

    assert project.snapshot() == before
    assert (first.verdict, first.findings, first.not_run) == (
        second.verdict,
        second.findings,
        second.not_run,
    )


# --- ORQ-E535: a declared entry differs from rendered_entry ---------------------------------------

DIFFERENT_ENTRIES: dict[str, dict[str, Any]] = {
    "another-address": {"type": "http", "url": f"https://{MARKER}.example.com/mcp"},
    "another-type": {"type": "sse", "url": ATLASSIAN},
    "address-with-a-trailing-slash": {"type": "http", "url": ATLASSIAN + "/"},
    "address-that-is-not-a-string": {"type": "http", "url": 5},
    "address-missing": {"type": "http"},
    "type-missing": {"url": ATLASSIAN},
    "a-header-added": {"type": "http", "url": ATLASSIAN, "headers": {"X-Team": "docs"}},
    "an-unknown-key-added": {"type": "http", "url": ATLASSIAN, MARKER: 1},
    "a-process-instead-of-an-address": {"type": "stdio", "command": "npx", "args": []},
    "an-empty-object": {},
}


@pytest.mark.parametrize("name", list(DIFFERENT_ENTRIES), ids=list(DIFFERENT_ENTRIES))
def test_a_declared_entry_that_differs_is_an_error_naming_closed_fields(name: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("an error for a declared entry that differs from
    rendered_entry (naming fields from the closed vocabulary)"), plan P-3 objective (ORQ-E535) and
    ADR-002 decision 9 ("`entry_differences` names fields from a closed vocabulary (`type`, `url`,
    `headers`, `bearer_token_env_var`, `unknown-key`) and never an unknown key or an undeclared
    name"). The fields that the message must name are the ones that `entry_differences` gives."""
    found_entry = DIFFERENT_ENTRIES[name]
    fields = entry_differences(ENTRY, found_entry)
    assert fields

    result = run(project_with({MCP: entries_file({"orqlet-docs": found_entry})}))

    differing = assert_fails_with(result, DIFFERS)
    assert any(all(field in finding.message for field in fields) for finding in differing)
    assert not leaks(shown(result.findings), MARKER)


def test_an_unknown_key_is_named_unknown_key_and_never_by_its_own_name() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 9 ("`entry_differences` names fields from a
    closed vocabulary ... and never an unknown key") and ORQLET-SEC-003."""
    result = run(
        project_with(
            {MCP: entries_file({"orqlet-docs": DIFFERENT_ENTRIES["an-unknown-key-added"]})}
        )
    )

    differing = assert_fails_with(result, DIFFERS)
    assert any("unknown-key" in finding.message for finding in differing)
    assert not leaks(shown(result.findings), MARKER)


def test_only_the_entry_that_differs_is_reported() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (a declared entry that differs is an
    error; a declared entry that matches is not) and decision 5 (one entry per registered
    server)."""
    both = entries_file({"orqlet-docs": ENTRY, "orqlet-wiki": DIFFERENT_ENTRIES["another-type"]})

    result = run(project_with({MCP: both}, declared=TWO_DECLARED))

    assert len(assert_fails_with(result, DIFFERS)) == 1
    assert ABSENT_ENTRY not in codes(result.findings)


# --- ORQ-E536: a declared entry is absent from an existing file ----------------------------------


@pytest.mark.parametrize(
    "content",
    [
        entries_file({}),
        entries_file({"team": {"type": "http", "url": "https://team.example.com/mcp"}}),
    ],
    ids=["no-entry", "another-entry-only"],
)
def test_a_declared_entry_that_is_absent_from_an_existing_file_is_an_error(content: bytes) -> None:
    """AC-3. expected_behavior_source: AC-3 ("an error ... for a declared entry that is absent from
    an existing file"), plan P-3 objective (ORQ-E536), ADR-002 decision 6 and ADR-003 decision 6
    ("an existing MCP file that lacks a declared entry is an error")."""
    result = run(project_with({MCP: content}))

    assert_fails_with(result, ABSENT_ENTRY)
    assert UNDECLARED not in codes(result.findings)


def test_one_missing_entry_of_two_is_one_error() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (each declared entry that is absent is an
    error) and decision 5 (the declared names are `orqlet-<id>` of the registered servers)."""
    result = run(project_with({MCP: entries_file({"orqlet-docs": ENTRY})}, declared=TWO_DECLARED))

    assert len(assert_fails_with(result, ABSENT_ENTRY)) == 1


def test_an_entry_name_is_compared_with_the_declared_name_case_sensitively() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 ("A name is compared case-sensitively with
    the declared names, and a name that starts with `orqlet-` in any letter case and is not exactly
    a declared name is an undeclared `orqlet-*` entry"): `Orqlet-Docs` is not `orqlet-docs`."""
    result = run(project_with({MCP: entries_file({"Orqlet-Docs": ENTRY})}))

    assert_fails_with(result, ABSENT_ENTRY, UNDECLARED)


def test_an_absent_file_is_information_and_not_an_error() -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 6 ("An absent MCP file is an information
    finding") and plan P-3 objective (ORQ-I532 MCP file absent)."""
    result = run(project_with())

    assert result.verdict is not Verdict.FAIL
    assert result.errors == ()
    assert with_code(result.findings, NO_FILE)
    assert all(finding.severity is Severity.INFO for finding in with_code(result.findings, NO_FILE))


def test_a_declaration_with_no_registered_server_wants_no_entry() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 ("When no server is registered for a
    client, no file is written for it"; the declared names are those of the registered servers):
    an empty declaration and a file that holds no `orqlet-` entry is a pass."""
    result = run(project_with({MCP: entries_file({})}, declared=declaration()))

    assert_passes(result)


# --- ORQ-E537: an undeclared orqlet-* entry ------------------------------------------------------

UNDECLARED_NAMES = {
    "another-id": "orqlet-other",
    "capitals": "ORQLET-OTHER",
    "first-letter-capital": "Orqlet-other",
    "mixed-case": "oRqLeT-other",
    "the-prefix-alone": "orqlet-",
    "the-declared-name-with-a-suffix": "orqlet-docs-2",
    "the-declared-name-in-capitals": "ORQLET-DOCS",
}


@pytest.mark.parametrize("name", list(UNDECLARED_NAMES), ids=list(UNDECLARED_NAMES))
@pytest.mark.parametrize("path", [MCP, CURSOR], ids=["claude-code", "cursor"])
def test_an_undeclared_orqlet_entry_is_an_error_in_any_letter_case(name: str, path: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("an error ... for an undeclared orqlet-* entry in any
    letter case"), plan P-3 objective (ORQ-E537), ADR-002 decision 6 and decision 5 (the names that
    a file may hold are those of the servers registered for its client: no server is registered for
    Cursor here, so every `orqlet-` entry of `.cursor/mcp.json` is undeclared)."""
    declared_entry = {"orqlet-docs": ENTRY} if path == MCP else {}
    files = {MCP: GOOD, path: entries_file({**declared_entry, UNDECLARED_NAMES[name]: ENTRY})}

    assert_fails_with(run(project_with(files)), UNDECLARED)


def test_an_undeclared_name_that_is_written_with_an_escape_is_judged_by_its_decoded_name() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (names are compared as parsed; "a decoded
    entry name that starts with `orqlet-`", decision 11) and AC-4 ("an escaped ... entry name")."""
    raw = raw_file(
        f'"orqlet-docs": {json.dumps(ENTRY)}', f'"{escaped("o")}rqlet-other": {json.dumps(ENTRY)}'
    )
    assert "orqlet-other" not in raw.decode()

    assert_fails_with(run(project_with({MCP: raw})), UNDECLARED)


def test_a_declared_name_written_with_an_escape_is_the_declared_entry() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (the parsed document is compared, so a
    JSON escape "changes nothing")."""
    raw = raw_file(f'"{escaped("o")}rqlet-docs": {json.dumps(ENTRY)}')
    assert "orqlet-docs" not in raw.decode()

    assert_passes(run(project_with({MCP: raw})))


def test_an_undeclared_entry_name_is_not_shown() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 9 ("`entry_differences` ... never an unknown
    key or an undeclared name") and AC-2 (no raw key in any message)."""
    name = f"orqlet-{MARKER}"

    result = run(project_with({MCP: entries_file({"orqlet-docs": ENTRY, name: ENTRY})}))

    assert_fails_with(result, UNDECLARED)
    assert not leaks(shown(result.findings), MARKER)


def test_an_empty_declaration_makes_every_orqlet_entry_undeclared() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 (the declared names are exactly those of
    the registered servers: none) and decision 6."""
    result = run(project_with({MCP: GOOD}, declared=declaration()))

    assert_fails_with(result, UNDECLARED)


def test_a_declared_name_is_undeclared_in_the_file_of_a_client_with_no_registered_server() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 ("`registered_for(client)` returns the
    servers whose `per_client[client].register` is true ... The set of names that a file may hold as
    declared entries is exactly `orqlet-<id>` of those servers"): the names are those of the
    client's own file, and no server is registered for Cursor here."""
    result = run(project_with({CURSOR: GOOD}))

    assert_fails_with(result, UNDECLARED)


# --- an undeclared entry that is none of the above is left alone, and counted --------------------


def counted(finding: Finding) -> list[int]:
    return sorted(int(number) for number in re.findall(r"\d+", finding.message))


def counts_of(result: ValidationResult) -> list[Finding]:
    """The ORQ-I531 findings that count something: a finding with two zeros says nothing, and the
    design does not say whether one is printed for a file that has no undeclared entry."""
    return [f for f in with_code(result.findings, COUNTS) if counted(f) != [0, 0]]


def test_other_undeclared_entries_are_left_alone_and_counted_with_two_numbers() -> None:
    """AC-3. expected_behavior_source: AC-3 ("another undeclared entry is left alone and counted by
    one information finding with two numbers and no names"), plan P-3 objective (ORQ-I531) and
    ADR-002 decision 6 ("one information finding with two counts, never names: the undeclared
    entries, and those among them whose `url` has no enabled mode for the client"). Four entries
    are undeclared; three of them have an address that is not the enabled one for Claude Code."""
    others = {
        f"team-{MARKER}-a": {"type": "http", "url": "https://one.example.com/mcp"},
        f"team-{MARKER}-b": {"type": "http", "url": "https://two.example.com/mcp"},
        f"team-{MARKER}-c": {"type": "http", "url": ATLASSIAN},
        f"team-{MARKER}-d": {"type": "http", "url": ATLASSIAN + "/"},
    }

    result = run(project_with({MCP: entries_file({"orqlet-docs": ENTRY, **others})}))

    assert_passes(result)
    (summary,) = counts_of(result)
    assert summary.severity is Severity.INFO
    assert counted(summary) == [3, 4]
    assert not leaks(shown(result.findings), MARKER)
    for entry_name in others:
        assert entry_name not in shown(result.findings)


def test_the_count_of_entries_off_the_table_is_per_client() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 ("those among them whose `url` has no
    enabled mode for the client") and decision 2 (the one enabled row is for `claude-code`): in the
    file of Cursor the Atlassian address is off the table as well."""
    content = entries_file(
        {
            "team-a": {"type": "http", "url": ATLASSIAN},
            "team-b": {"type": "http", "url": "https://two.example.com/mcp"},
        }
    )

    result = run(project_with({MCP: GOOD, CURSOR: content}))

    assert_passes(result)
    (summary,) = counts_of(result)
    assert counted(summary) == [2, 2]


# --- ORQ-E538 and AC-9: a key of the closed list, or the text ${ ---------------------------------

VARIANTS: dict[str, Callable[[str], str]] = {
    "as-given": lambda key: key,
    "lower": lambda key: key.lower(),
    "upper": lambda key: key.upper(),
    "swapped": lambda key: key.swapcase(),
    "title": lambda key: "_".join(part.capitalize() for part in key.split("_")),
}


@pytest.mark.parametrize("variant", list(VARIANTS), ids=list(VARIANTS))
@pytest.mark.parametrize("key", EVIDENCE_KEYS)
@pytest.mark.parametrize("path", [MCP, CURSOR], ids=["claude-code", "cursor"])
def test_a_key_of_the_closed_list_is_an_error_in_any_letter_case(
    path: str, key: str, variant: str
) -> None:
    """AC-9. expected_behavior_source: AC-9 ("the closed key list ... holds only the key names that
    the evidence gives (headersHelper, http_headers_helper, env_http_headers,
    bearer_token_env_var)"), AC-3 ("a key of the closed list (compared case-insensitively)"), plan
    P-3 objective (ORQ-E538) and ADR-002 decision 6. The list is a private constant, so only the
    behaviour is tested."""
    entry = {"type": "http", "url": "https://team.example.com/mcp", VARIANTS[variant](key): "value"}
    content = entries_file({**({"orqlet-docs": ENTRY} if path == MCP else {}), "team": entry})

    assert_fails_with(run(project_with({MCP: GOOD, path: content})), CLOSED)


NESTED_KEYS = {
    "in-a-declared-entry": lambda key: entries_file({"orqlet-docs": {**ENTRY, key: "value"}}),
    "below-headers": lambda key: in_team(headers={key: "value"}),
    "three-levels-down": lambda key: in_team(a={"b": {"c": {key: "value"}}}),
    "in-a-list": lambda key: in_team(a=[{key: "value"}]),
    "as-the-name-of-an-entry": lambda key: entries_file(
        {"orqlet-docs": ENTRY, key: {"type": "http"}}
    ),
    "as-a-top-level-key": lambda key: entries_file({"orqlet-docs": ENTRY}, **{key: "value"}),
}


@pytest.mark.parametrize("where", list(NESTED_KEYS), ids=list(NESTED_KEYS))
def test_a_key_of_the_closed_list_is_found_wherever_it_is(where: str) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 ("the validator walks the whole parsed
    document, entry names and top-level keys included, and every decoded key and string value at
    any depth, and applies the closed-key test")."""
    content = NESTED_KEYS[where]("headersHelper")

    assert_fails_with(run(project_with({MCP: content})), CLOSED)


@pytest.mark.parametrize(
    "key",
    [
        "headers",
        "env",
        "command",
        "args",
        "timeout",
        "headers_helper",
        "env_headers",
        "http_headers",
        "oauth",
        "disabled",
    ],
)
def test_a_key_that_the_evidence_does_not_give_is_not_in_the_closed_list(key: str) -> None:
    """AC-9. expected_behavior_source: ADR-002 decision 6 ("it holds the key names that the evidence
    gives: `headersHelper` (A-64), and `http_headers_helper`, `env_http_headers` and
    `bearer_token_env_var` (A-91 to A-93) ... Names the evidence does not give ... are not
    listed"). An undeclared entry with such a key and a harmless value is left alone."""
    content = in_team(**{key: "docs"})

    result = run(project_with({MCP: content}))

    assert_passes(result)
    assert CLOSED not in codes(result.findings)


def test_an_authorization_header_that_refers_to_a_variable_is_an_error_in_any_entry() -> None:
    """AC-3. expected_behavior_source: ADR-002 context (a changed entry can send a variable's value
    elsewhere: `Authorization: Bearer ${NAME}` aimed at another host) and decision 6 ("Any entry
    with ... whose text holds the substring `${`: error")."""
    content = in_team(headers={"Authorization": "Bearer ${ORQLET_MCP_DOCS_TOKEN}"})

    assert_fails_with(run(project_with({MCP: content})), CLOSED)


@pytest.mark.parametrize(
    "where",
    [
        lambda text: in_team(url_note=text),
        lambda text: in_team(args=["--flag", text]),
        lambda text: in_team(env={"HOME_DIR": text}),
        lambda text: entries_file({"orqlet-docs": {**ENTRY, "url": ATLASSIAN + text}}),
        lambda text: entries_file({"orqlet-docs": ENTRY, text: {"type": "http"}}),
        lambda text: entries_file({"orqlet-docs": ENTRY}, **{text: "x"}),
    ],
    ids=[
        "a-value",
        "a-list-item",
        "an-env-value",
        "a-declared-address",
        "an-entry-name",
        "a-top-level-key",
    ],
)
def test_the_text_dollar_brace_in_a_key_or_a_string_is_an_error(
    where: Callable[[str], bytes],
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("or the text ${ anywhere in a decoded key or string"),
    plan P-3 objective (ORQ-E538) and ADR-002 decision 6."""
    content = where("/${HOME}")

    assert_fails_with(run(project_with({MCP: content})), CLOSED)


def test_a_dollar_sign_without_a_brace_is_not_a_reference() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (the test is for the substring `${`)."""
    content = in_team(price="costs $5 {each}", note="a { and a $")

    assert_passes(run(project_with({MCP: content})))


def test_a_variable_reference_in_the_toml_file_is_not_judged() -> None:
    """AC-4. expected_behavior_source: AC-4 ("The .codex/config.toml file gets the raw scan only")
    and ADR-002 decision 6 ("For `.codex/config.toml` the validator runs the scan only"): neither
    the closed keys nor the text `${` are tests of the scan."""
    toml = (
        '[mcp_servers.team]\nurl = "https://team.example.com/${HOME}"\n'
        'http_headers_helper = "tool"\nbearer_token_env_var = "ORQLET_MCP_DOCS_TOKEN"\n'
    )

    assert_passes(run(project_with({MCP: GOOD, CODEX: toml})))


# --- ORQ-E539: the scan of the raw text ----------------------------------------------------------

RAW_SHAPES: dict[str, Callable[[], dict[str, Any]]] = {
    "provider-token-in-a-value": lambda: {"env": {"NAME": TOKEN}},
    "token-in-an-argument": lambda: {"args": ["--flag", TOKEN]},
    "jwt-shape": lambda: {"env": {"NAME": JWT}},
    "user-information-in-an-address": lambda: {
        "url": f"https://deploy:{PASSWORD}@team.example.com/mcp"
    },
    "credential-in-the-query": lambda: {"url": f"https://team.example.com/mcp?token={OPAQUE}"},
    "authorization-header-with-a-literal": lambda: {
        "headers": {"Authorization": f"Bearer {OPAQUE}1"}
    },
    "credential-named-key-with-a-literal": lambda: {"env": {"api_key": OPAQUE}},
}


@pytest.mark.parametrize("name", list(RAW_SHAPES), ids=list(RAW_SHAPES))
@pytest.mark.parametrize("path", [MCP, CURSOR], ids=["claude-code", "cursor"])
def test_a_credential_shape_in_an_mcp_file_is_an_error(name: str, path: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("Any file or decoded string with a scan finding"),
    plan P-3 objective (ORQ-E539), ADR-002 decision 6 and decision 7 (the shapes of the scan: token
    prefixes, the JWT shape, user information in a URL, a query parameter, an `Authorization`
    value, a credential-named key with a literal value). The shape is assembled at run time."""
    entry = {"type": "http", "url": "https://team.example.com/mcp", **RAW_SHAPES[name]()}
    content = entries_file({**({"orqlet-docs": ENTRY} if path == MCP else {}), "team": entry})
    assert find_literal_credentials(content.decode())

    result = run(project_with({MCP: GOOD, path: content}))

    assert_fails_with(result, SCANNED)
    for secret in (TOKEN, JWT, PASSWORD, OPAQUE):
        assert not leaks(shown(result.findings), secret)


def test_a_credential_shape_in_the_toml_file_is_an_error() -> None:
    """AC-4. expected_behavior_source: AC-4 ("The .codex/config.toml file gets the raw scan only")
    and ADR-002 decision 6 ("the validator runs the scan only"): the raw scan does run."""
    toml = f'[mcp_servers.team]\nurl = "https://team.example.com/mcp"\nGITHUB = "{TOKEN}"\n'
    assert find_literal_credentials(toml)

    result = run(project_with({MCP: GOOD, CODEX: toml}))

    assert_fails_with(result, SCANNED)
    assert not leaks(shown(result.findings), TOKEN)


def test_a_line_above_4096_characters_is_a_scan_finding() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 7 ("the scan reads at most 4096 characters
    per line, and a longer line is itself a finding (`oversize`)": a credential must not hide
    behind the cap) and plan P-3 objective (ORQ-E539)."""
    content = GOOD.replace(b'{\n  "mcpServers"', b"{" + b" " * 5000 + b'\n  "mcpServers"', 1)
    assert content != GOOD

    assert_fails_with(run(project_with({MCP: content})), SCANNED)


def test_the_toml_file_is_not_parsed_and_an_orqlet_table_in_it_is_left_alone() -> None:
    """AC-4. expected_behavior_source: AC-4 ("The .codex/config.toml file gets the raw scan only")
    and ADR-002 decision 6 ("a TOML reader would add a second parser path"): no entry check and no
    parse error for the file of Codex, even for an `orqlet-` name that no server declares or text
    that is no TOML."""
    for toml in (
        '[mcp_servers.orqlet-other]\nurl = "https://team.example.com/mcp"\n',
        "[[[ this is no toml",
    ):
        result = run(project_with({MCP: GOOD, CODEX: toml}))

        assert_passes(result)
        assert not codes(result.findings) & {
            UNREADABLE_FILE,
            DIFFERS,
            ABSENT_ENTRY,
            UNDECLARED,
            CLOSED,
        }


# --- AC-4: the decoded scan ----------------------------------------------------------------------

# Each case writes ONE thing with a JSON escape, so that the raw text is clean and the finding
# can come only from the decoded text: (the entry as raw JSON text, the top-level text, the code
# that the decoded text must give). Everything is assembled at run time.
Escaped = tuple[str, str, str]


def _case_token(index: int) -> Callable[[], Escaped]:
    return lambda: (team(f', "env": {{"NAME": "{with_escape(TOKEN, index)}"}}'), "", SCANNED)


ESCAPED_SHAPES: dict[str, Callable[[], Escaped]] = {
    **{f"token-prefix-letter-{index}": _case_token(index) for index in range(4)},
    "token-in-the-middle": _case_token(10),
    "credential-named-key-letter": lambda: (
        team(f', "env": {{"{with_escape("api_key", 2)}": "{OPAQUE}"}}'),
        "",
        SCANNED,
    ),
    "credential-named-key-underscore": lambda: (
        team(f', "env": {{"{with_escape("api_key", 3)}": "{OPAQUE}"}}'),
        "",
        SCANNED,
    ),
    "authorization-word-letter": lambda: (
        team(f', "headers": {{"{with_escape("Authorization", 6)}": "{OPAQUE}"}}'),
        "",
        SCANNED,
    ),
    "authorization-word-first-letter": lambda: (
        team(f', "headers": {{"{with_escape("Authorization", 0)}": "{OPAQUE}"}}'),
        "",
        SCANNED,
    ),
    "token-as-the-name-of-an-entry": lambda: (
        f'"{with_escape(TOKEN, 0)}": {{"type": "http", "url": "https://team.example.com/mcp"}}',
        "",
        SCANNED,
    ),
    "token-as-a-top-level-key": lambda: (team(), f'"{with_escape(TOKEN, 1)}": 1', SCANNED),
    "dollar-sign": lambda: (team(f', "args": ["{with_escape("${HOME}", 0)}"]'), "", CLOSED),
    "dollar-brace": lambda: (team(f', "args": ["{with_escape("${HOME}", 1)}"]'), "", CLOSED),
    "dollar-sign-in-an-address": lambda: (
        f'"team": {{"type": "http", "url": "https://team.example.com/{with_escape("${X}", 0)}"}}',
        "",
        CLOSED,
    ),
    "closed-key-letter": lambda: (
        team(f', "{with_escape("headersHelper", 7)}": "tool"'),
        "",
        CLOSED,
    ),
    "closed-key-first-letter": lambda: (
        team(f', "{with_escape("headersHelper", 0)}": "tool"'),
        "",
        CLOSED,
    ),
    "closed-key-as-a-top-level-key": lambda: (
        team(),
        f'"{with_escape("headersHelper", 7)}": "tool"',
        CLOSED,
    ),
}


@pytest.mark.parametrize("name", list(ESCAPED_SHAPES), ids=list(ESCAPED_SHAPES))
def test_an_escape_does_not_hide_a_shape_from_the_validator(name: str) -> None:
    """AC-4. expected_behavior_source: AC-4 ("the shapes ghp_, api_key, Authorization and ${ written
    with a JSON escape in one letter, an escaped credential in an entry name ... are each found"),
    ADR-002 decision 6 ("a JSON escape such as `\\u0024{` or `Author\\u0069zation` changes
    nothing") and decision 7 ("a re-serialisation of the whole parsed document"). The test checks
    first that the raw text alone is clean."""
    entry, top, code = ESCAPED_SHAPES[name]()
    raw = raw_file(f'"orqlet-docs": {json.dumps(ENTRY)}', entry, top=top)
    text = raw.decode()
    assert find_literal_credentials(text) == ()
    assert "${" not in text
    assert not re.search("headersHelper|api_key|Authorization", text)
    assert json.loads(raw)

    result = run(project_with({MCP: raw}))

    assert_fails_with(result, code)
    assert code in codes(found(project_with({MCP: raw})))
    for secret in (TOKEN, OPAQUE):
        assert not leaks(shown(result.findings), secret)


@pytest.mark.parametrize(
    "name", [name for name, build in ESCAPED_SHAPES.items() if build()[2] == SCANNED]
)
def test_a_finding_on_the_decoded_text_carries_the_rule_and_the_word_decoded(name: str) -> None:
    """AC-4. expected_behavior_source: AC-4 ("a finding on the decoded text carries the rule and the
    word decoded with no line and no key") and ADR-002 decision 7 ("A finding on that text names the
    rule and the word `decoded`, with no line and no key"). The rules are the ones that the scan
    itself gives for the re-serialised document."""
    entry, top, _ = ESCAPED_SHAPES[name]()
    raw = raw_file(f'"orqlet-docs": {json.dumps(ENTRY)}', entry, top=top)
    rules = {finding.rule for finding in find_literal_credentials(decoded_text(raw))}
    assert rules

    result = run(project_with({MCP: raw}))

    decoded = [f for f in with_code(result.findings, SCANNED) if "decoded" in f.message.lower()]
    assert decoded, shown(result.findings)
    assert any(rule in finding.message for finding in decoded for rule in rules)
    for finding in decoded:
        assert re.search(r"\bline\s*\d", finding.message, re.IGNORECASE) is None
    for secret in (TOKEN, OPAQUE):
        assert not leaks(shown(result.findings), secret)


@pytest.mark.parametrize(
    "escape", ["\\ud800", "\\udc00", "\\udbff"], ids=["high", "low", "last-high"]
)
@pytest.mark.parametrize(
    "build",
    [
        lambda escape: team(f', "note": "a{escape}b"'),
        lambda escape: team(f', "a{escape}b": 1'),
        lambda escape: f'"a{escape}b": {{"type": "http", "url": "https://team.example.com/mcp"}}',
    ],
    ids=["in-a-value", "in-a-key", "in-an-entry-name"],
)
def test_a_lone_surrogate_is_an_error_and_never_an_exception(
    build: Callable[[str], str], escape: str
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("... and a lone surrogate are each found") and ADR-002
    decision 7 ("A test uses a lone surrogate (`\\ud800`) in a JSON string"). The code is not fixed
    (the file cannot be read safely, or the scan finds it), so either is accepted; every text of the
    result must be encodable."""
    raw = raw_file(f'"orqlet-docs": {json.dumps(ENTRY)}', build(escape))

    result = run(project_with({MCP: raw}))

    assert result.verdict is Verdict.FAIL
    assert codes(errors_of(result.findings)) & {UNREADABLE_FILE, SCANNED}, shown(result.findings)
    shown(result.findings).encode("utf-8")


def test_the_same_shapes_without_an_escape_are_found_by_the_raw_scan() -> None:
    """AC-4. expected_behavior_source: AC-4 ("The scan runs on the raw text and on a
    re-serialisation of the whole parsed document"): the unescaped token of the first case is the
    raw scan's."""
    raw = raw_file(f'"orqlet-docs": {json.dumps(ENTRY)}', team(f', "env": {{"NAME": "{TOKEN}"}}'))

    assert_fails_with(run(project_with({MCP: raw})), SCANNED)


def test_an_escaped_token_in_the_toml_file_is_not_decoded() -> None:
    """AC-4. expected_behavior_source: AC-4 ("The .codex/config.toml file gets the raw scan only")
    and ADR-002 decision 7 ("The TOML file gets the raw scan only; that leaves TOML `\\u` and `\\U`
    escapes ... unscanned"): a stated limit, pinned so that a decoder is not added by accident."""
    toml = f'[mcp_servers.team]\nGITHUB = "{with_escape(TOKEN, 0)}"\n'
    assert find_literal_credentials(toml) == ()

    assert_passes(run(project_with({MCP: GOOD, CODEX: toml})))


# --- AC-5: parsing is strict and bounded ---------------------------------------------------------


def unreadable_findings(result: ValidationResult, path: str) -> list[Finding]:
    return [f for f in with_code(result.findings, UNREADABLE_FILE) if names(f, path)]


def test_a_file_of_exactly_256_kib_is_read() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 8 ("refused above 256 KiB": at the cap it
    is read)."""
    content = padded(GOOD, LIMIT)
    assert len(content) == LIMIT

    assert_passes(run(project_with({MCP: content})))


@pytest.mark.parametrize("size", [LIMIT + 1, 2 * LIMIT])
@pytest.mark.parametrize("path", [MCP, CURSOR, CODEX], ids=["claude-code", "cursor", "codex"])
def test_a_file_above_256_kib_is_an_error_for_that_file(path: str, size: int) -> None:
    """AC-5. expected_behavior_source: AC-5 ("a file above 256 KiB ... give an error finding for
    that file, exit 5"), plan P-3 objective (ORQ-E534) and ADR-002 decision 8."""
    result = run(project_with({MCP: GOOD, path: padded(GOOD, size)}))

    assert_fails_with(result, UNREADABLE_FILE)
    assert unreadable_findings(result, path)


def nested(depth: int) -> object:
    """An object with `depth` levels of nesting below it."""
    value: object = "leaf"
    for _ in range(depth):
        value = {"k": value}
    return value


@pytest.mark.parametrize("depth", [20, 40, 100])
def test_nesting_above_16_levels_is_an_error_for_that_file(depth: int) -> None:
    """AC-5. expected_behavior_source: AC-5 ("nesting above 16 levels"), plan P-3 objective
    (ORQ-E534) and ADR-002 decision 8. Only clear cases are tested: the entry sits three levels
    below the top, so `depth` of 20 or more is above 16 however the levels are counted."""
    result = run(project_with({MCP: in_team(deep=nested(depth))}))

    assert unreadable_findings(result, MCP)
    assert result.verdict is Verdict.FAIL


def test_nesting_of_a_few_levels_is_read() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 8 (the limit is above 16 levels)."""
    assert_passes(run(project_with({MCP: in_team(deep=nested(5))})))


def test_nesting_that_exhausts_the_stack_is_an_error_and_not_an_exception() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 8 ("`RecursionError` ... [is] turned into a
    finding")."""
    content = b'{"mcpServers": {"team": ' + b"[" * 20000 + b"]" * 20000 + b"}}"

    result = run(project_with({MCP: content}))

    assert unreadable_findings(result, MCP)


def entry_count(count: int) -> bytes:
    """A file with the declared entry and `count - 1` others: `count` entries in all."""
    others = {
        f"team-{n}": {"type": "http", "url": f"https://team.example.com/{n}"}
        for n in range(count - 1)
    }
    return entries_file({"orqlet-docs": ENTRY, **others})


def test_64_entries_are_read() -> None:
    """AC-5. expected_behavior_source: AC-5 ("more than 64 entries") and ADR-002 decision 8 (64
    entries): 64 is not more than 64."""
    assert_passes(run(project_with({MCP: entry_count(64)})))


@pytest.mark.parametrize("count", [65, 66, 200])
def test_more_than_64_entries_is_an_error_for_that_file(count: int) -> None:
    """AC-5. expected_behavior_source: AC-5 ("more than 64 entries"), plan P-3 objective (ORQ-E534)
    and ADR-002 decision 8."""
    result = run(project_with({MCP: entry_count(count)}))

    assert unreadable_findings(result, MCP)
    assert result.verdict is Verdict.FAIL


def test_a_string_of_2048_characters_is_read() -> None:
    """AC-5. expected_behavior_source: AC-5 ("a string above 2048 characters") and ADR-002
    decision 8: 2048 is not above 2048."""
    assert_passes(run(project_with({MCP: in_team(note="a" * 2048)})))


@pytest.mark.parametrize("length", [2049, 3000])
def test_a_string_above_2048_characters_is_an_error_for_that_file(length: int) -> None:
    """AC-5. expected_behavior_source: AC-5 ("a string above 2048 characters"), plan P-3 objective
    (ORQ-E534) and ADR-002 decision 8."""
    result = run(project_with({MCP: in_team(note="a" * length)}))

    assert unreadable_findings(result, MCP)
    assert result.verdict is Verdict.FAIL


DUPLICATES: dict[str, Callable[[str], bytes]] = {
    "in-the-top-level": lambda key: f'{{"mcpServers": {{}}, "{key}": 1, "{key}": 2}}'.encode(),
    "in-the-entries": lambda key: f'{{"mcpServers": {{"{key}": {{}}, "{key}": {{}}}}}}'.encode(),
    "in-an-entry": lambda key: f'{{"mcpServers": {{"team": {{"{key}": 1, "{key}": 2}}}}}}'.encode(),
    "below-an-entry": lambda key: (
        f'{{"mcpServers": {{"team": {{"a": {{"{key}": 1, "{key}": 2}}}}}}}}'.encode()
    ),
    "one-written-with-an-escape": lambda key: (
        f'{{"mcpServers": {{"team": {{"{key}": 1, "{with_escape(key, 0)}": 2}}}}}}'.encode()
    ),
}


@pytest.mark.parametrize("key", [OPAQUE, TOKEN, "k"], ids=["opaque", "token", "short"])
@pytest.mark.parametrize("where", list(DUPLICATES), ids=list(DUPLICATES))
def test_a_duplicate_key_is_an_error_that_names_the_rule_and_not_the_key(
    where: str, key: str
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("a duplicate key (rule duplicate-key, no key text)"),
    plan P-3 objective (ORQ-E534) and ADR-002 decision 8 ("JSON is read with duplicate keys
    rejected") and decision 9 ("The JSON reader raises a rule `duplicate-key` and no key text")."""
    content = DUPLICATES[where](key)

    result = run(project_with({MCP: content}))

    flagged = unreadable_findings(result, MCP)
    assert flagged
    assert any("duplicate-key" in finding.message for finding in flagged)
    if len(key) > 1:
        assert not leaks(shown(result.findings), key)


NOT_JSON: dict[str, bytes] = {
    "an-empty-file": b"",
    "only-spaces": b"   \n",
    "an-unclosed-object": b'{"mcpServers": {',
    "a-trailing-comma": b'{"mcpServers": {},}',
    "single-quotes": b"{'mcpServers': {}}",
    "a-comment": b'// the team\n{"mcpServers": {}}',
    "plain-text": b"not json at all",
    "two-documents": b'{"mcpServers": {}} {"mcpServers": {}}',
    "a-number-with-5000-digits": b'{"mcpServers": {"team": {"n": ' + b"1" * 5000 + b"}}}",
}
WRONG_SHAPES: dict[str, bytes] = {
    "a-list": b"[]",
    "a-string": b'"text"',
    "a-number": b"5",
    "null": b"null",
    "true": b"true",
    "servers-as-a-list": b'{"mcpServers": []}',
    "servers-as-a-string": b'{"mcpServers": "x"}',
    "servers-as-null": b'{"mcpServers": null}',
    "servers-as-a-number": b'{"mcpServers": 5}',
    "an-entry-that-is-a-list": b'{"mcpServers": {"team": []}}',
    "an-entry-that-is-a-string": b'{"mcpServers": {"team": "x"}}',
    "an-entry-that-is-null": b'{"mcpServers": {"team": null}}',
    "an-entry-that-is-a-number": b'{"mcpServers": {"team": 5}}',
    "the-declared-entry-as-a-string": b'{"mcpServers": {"orqlet-docs": "x"}}',
}


@pytest.mark.parametrize("name", list(NOT_JSON), ids=list(NOT_JSON))
def test_a_file_that_is_not_json_is_an_error_for_that_file(name: str) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 8 ("`json.JSONDecodeError`,
    `UnicodeDecodeError`, `RecursionError`, `OverflowError` and `ValueError` are each turned into a
    finding") and plan P-3 objective (ORQ-E534)."""
    result = run(project_with({MCP: NOT_JSON[name]}))

    assert unreadable_findings(result, MCP)
    assert result.verdict is Verdict.FAIL


@pytest.mark.parametrize("name", list(WRONG_SHAPES), ids=list(WRONG_SHAPES))
def test_valid_json_of_the_wrong_shape_is_an_error_and_not_an_exception(name: str) -> None:
    """AC-5. expected_behavior_source: AC-5 ("valid JSON of the wrong shape"), ADR-002 decision 8
    ("Valid input of the wrong shape (the top level, `mcpServers` or an entry that is not an object)
    is a finding, not an exception") and plan P-3 objective (ORQ-E534)."""
    result = run(project_with({MCP: WRONG_SHAPES[name]}))

    assert unreadable_findings(result, MCP)
    assert result.verdict is Verdict.FAIL


# What each way of an MCP file being unusable looks like to the project. Every builder takes the
# path of the file and the project, and makes the file unusable in the way its name says.
def _link(project: Files, path: str) -> None:
    project.add_symlink(path)


def _directory(project: Files, path: str) -> None:
    project.make_dir(CanonicalPath.parse(path))


def _not_utf_8(project: Files, path: str) -> None:
    put(project, path, b'{"mcpServers": {"x": "\xff\xfe"}}')


def _above_the_cap(project: Files, path: str) -> None:
    put(project, path, padded(GOOD, LIMIT + 1))


def _refused_by_the_system(project: Files, path: str) -> None:
    put(project, path, GOOD)
    project.unreadable.add(path)


def _link_in_a_parent_folder(project: Files, path: str) -> None:
    put(project, path, GOOD)
    project.add_symlink(path.split("/")[0])


PROBLEMS: dict[str, Callable[[Files, str], None]] = {
    "a-symbolic-link": _link,
    "a-directory": _directory,
    "invalid-utf-8": _not_utf_8,
    "above-256-kib": _above_the_cap,
    "refused-by-the-system": _refused_by_the_system,
}
PROBLEMS_OF_A_NESTED_FILE = {**PROBLEMS, "a-link-in-a-parent-folder": _link_in_a_parent_folder}


def broken_project(problem: Callable[[Files, str], None], path: str, *, declared: bool) -> Files:
    project = project_with(
        {MCP: GOOD} if path != MCP else None, declared=DECLARED if declared else None
    )
    problem(project, path)
    return project


@pytest.mark.parametrize("name", list(PROBLEMS), ids=list(PROBLEMS))
@pytest.mark.parametrize("path", [MCP, CURSOR, CODEX], ids=["claude-code", "cursor", "codex"])
def test_an_unusable_file_is_an_error_for_that_file_when_a_declaration_exists(
    path: str, name: str
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("when a declaration exists, a link, a directory, an
    unreadable file, a file that is not UTF-8 ... each give an error finding for that file, exit
    5"), plan P-3 objective (ORQ-E534) and ADR-002 decision 8 ("is an `unreadable` error for that
    file (exit 5)": "a link must not hide an entry from the validator while a client may follow
    it")."""
    project = broken_project(PROBLEMS[name], path, declared=True)

    result = run(project)

    assert_fails_with(result, UNREADABLE_FILE)
    assert unreadable_findings(result, path)
    assert NOT_READ not in codes(result.findings)


@pytest.mark.parametrize(
    "name", list(PROBLEMS_OF_A_NESTED_FILE), ids=list(PROBLEMS_OF_A_NESTED_FILE)
)
@pytest.mark.parametrize("path", [CURSOR, CODEX], ids=["cursor", "codex"])
def test_an_unusable_nested_file_is_an_error_even_for_a_link_in_a_parent_folder(
    path: str, name: str
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("a link in a parent folder"), ADR-002 decision 8
    ("Every file-system error is caught for the one file, including a link in a parent folder") and
    the FileSystem port ("A link above it raises `LinkRefused`")."""
    project = broken_project(PROBLEMS_OF_A_NESTED_FILE[name], path, declared=True)

    result = run(project)

    assert unreadable_findings(result, path)
    assert result.verdict is Verdict.FAIL


def test_an_unusable_file_does_not_stop_the_other_checks() -> None:
    """AC-5. expected_behavior_source: AC-5 ("... each give an error finding for that file ... and
    do not stop the other checks") and ADR-002 decision 8 ("does not stop the other checks"). One
    file is a link, one holds an undeclared entry and one holds a token."""
    project = project_with(
        {
            CURSOR: entries_file({"orqlet-other": ENTRY}),
            CODEX: f'GITHUB = "{TOKEN}"\n',
        }
    )
    project.add_symlink(MCP)

    result = run(project)

    assert_fails_with(result, UNREADABLE_FILE, UNDECLARED, SCANNED)
    assert unreadable_findings(result, MCP)


def test_two_unusable_files_are_two_findings() -> None:
    """AC-5. expected_behavior_source: AC-5 ("an error finding for that file": one for each)."""
    project = project_with({CODEX: "x = 1\n"})
    project.add_symlink(MCP)
    project.add_symlink(CURSOR)

    result = run(project)

    assert unreadable_findings(result, MCP)
    assert unreadable_findings(result, CURSOR)
    assert not unreadable_findings(result, CODEX)


def test_an_unusable_file_of_a_file_name_with_a_secret_is_not_echoed() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 9 and ORQLET-SEC-003: the finding names the
    rule and the file of the three known paths, never what is inside."""
    project = project_with({MCP: f'{{"mcpServers": {{"{TOKEN}": 1, "{TOKEN}": 2}}}}'})

    result = run(project)

    assert unreadable_findings(result, MCP)
    assert not leaks(shown(result.findings), TOKEN)


# --- AC-6: no declaration -------------------------------------------------------------------------

HOLDS_THE_PREFIX: dict[str, tuple[str, bytes | str]] = {
    "an-entry-named-orqlet-docs": (MCP, entries_file({"orqlet-docs": ENTRY})),
    "an-entry-in-capitals": (MCP, entries_file({"ORQLET-DOCS": ENTRY})),
    "an-entry-in-mixed-case": (MCP, entries_file({"Orqlet-Docs": ENTRY})),
    "the-prefix-alone": (MCP, entries_file({"orqlet-": ENTRY})),
    "an-entry-name-written-with-an-escape": (
        MCP,
        raw_file(f'"{escaped("o")}rqlet-docs": {json.dumps(ENTRY)}'),
    ),
    "a-decoded-name-that-starts-with-the-prefix-among-others": (
        MCP,
        raw_file(f'"team": {json.dumps(ENTRY)}', f'"{escaped("O")}RQLET-x": {json.dumps(ENTRY)}'),
    ),
    "the-text-in-a-value": (MCP, entries_file({"team": {"note": "see orqlet-docs"}})),
    "the-text-inside-a-longer-name": (MCP, entries_file({"my-orqlet-docs": ENTRY})),
    "the-text-in-a-file-that-is-not-json": (MCP, b"not json at all, orqlet-docs"),
    "an-entry-of-the-file-of-cursor": (CURSOR, entries_file({"orqlet-docs": ENTRY})),
    "a-table-of-the-file-of-codex": (
        CODEX,
        '[mcp_servers.orqlet-docs]\nurl = "https://x.example.com"\n',
    ),
    "a-table-of-the-file-of-codex-in-capitals": (CODEX, "[mcp_servers.ORQLET-docs]\n"),
}
DOES_NOT_HOLD_THE_PREFIX: dict[str, dict[str, bytes | str]] = {
    "no-file": {},
    "other-servers": {MCP: entries_file({"team": ENTRY})},
    "orqlet-without-a-dash": {MCP: entries_file({"orqlet": ENTRY})},
    "orqlet-with-an-underscore": {MCP: entries_file({"orqlet_docs": ENTRY})},
    "a-dash-inside-the-word": {MCP: entries_file({"or-qlet-docs": ENTRY})},
    "closed-keys-and-references-in-other-entries": {
        MCP: team_only(
            headersHelper="tool", args=["${HOME}"], headers={"Authorization": "Bearer ${X}"}
        )
    },
    "a-credential-in-another-entry": {MCP: team_only(env={"NAME": TOKEN})},
    "a-credential-in-the-file-of-codex": {CODEX: f'GITHUB = "{TOKEN}"\n'},
    "valid-json-of-the-wrong-shape": {MCP: b"[]"},
    "text-that-is-not-json": {MCP: b"{{{ not json"},
    "an-empty-file": {MCP: b""},
}


@pytest.mark.parametrize("name", list(HOLDS_THE_PREFIX), ids=list(HOLDS_THE_PREFIX))
def test_without_a_declaration_a_file_that_holds_orqlet_gives_one_warning_and_no_error(
    name: str,
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("integration_findings returns ... the warning W530 when
    an MCP file holds orqlet- in any letter case or, for a JSON file that parses, a decoded entry
    name that starts with orqlet-"), plan P-3 objective (ORQ-W530) and ADR-002 decision 11 ("When
    the declaration is absent and an MCP file of any client holds the text `orqlet-` in any letter
    case, or ... a decoded entry name that starts with `orqlet-`, `doctor` and `sync` print a
    warning that says nothing was checked")."""
    path, content = HOLDS_THE_PREFIX[name]
    project = project_with({path: content}, declared=None)

    findings = found(project)

    (warning,) = with_code(findings, NOT_CHECKED)
    assert warning.severity is Severity.WARNING
    assert warning.message.strip()
    assert errors_of(findings) == []


@pytest.mark.parametrize("name", list(DOES_NOT_HOLD_THE_PREFIX), ids=list(DOES_NOT_HOLD_THE_PREFIX))
def test_without_a_declaration_a_file_that_does_not_hold_orqlet_gives_no_finding(name: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("integration_findings returns no finding ... and doctor
    and sync ... print nothing for a project without such a name"), ADR-003 decision 6 ("With the
    declaration absent it returns no finding, or the one warning") and ADR-002 decision 8 ("nothing
    is checked in it, because a project without a declaration keeps its behaviour"): no credential
    scan, no closed key and no shape check runs."""
    project = project_with(DOES_NOT_HOLD_THE_PREFIX[name], declared=None)

    assert found(project) == ()


@pytest.mark.parametrize("name", list(HOLDS_THE_PREFIX), ids=list(HOLDS_THE_PREFIX))
def test_without_a_declaration_the_command_is_not_run_by_its_own_existence_check(name: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("With no declaration, validate integrations is not run
    (exit 5) by its own existence check"), ADR-002 decision 11 ("`orqlet validate integrations`
    returns not run (exit 5) when the declaration is absent") and ADR-003 decision 6
    ("`validate_integrations` does its own existence check, as `validate_resources` does")."""
    path, content = HOLDS_THE_PREFIX[name]

    result = run(project_with({path: content}, declared=None))

    assert result.verdict is Verdict.NOT_RUN
    assert result.not_run
    assert result.errors == ()


def test_without_a_declaration_and_without_files_the_command_is_not_run() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 11 (not run, exit 5, when the declaration is
    absent) and ORQLET W-5 (a check that did not run is never success)."""
    result = run(project_with(declared=None))

    assert result.verdict is Verdict.NOT_RUN
    assert result.not_run
    assert result.errors == ()


def test_the_command_reads_the_declaration_from_the_path_it_is_given() -> None:
    """AC-6. expected_behavior_source: EC-4 (the `raw_path` parameter) and EC-6 (the command's file
    argument defaults to the declaration and can name another file)."""
    project = project_with({MCP: GOOD}, declared=None)
    put(project, "other/declaration.yaml", DECLARED)

    assert_passes(run(project, "other/declaration.yaml"))
    assert run(project).verdict is Verdict.NOT_RUN


def test_a_warning_does_not_name_the_entries_it_found() -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-002 decision 9 (no raw key in any message) and
    decision 11 (a warning that says nothing was checked, and why)."""
    project = project_with(
        {MCP: entries_file({f"orqlet-{MARKER}": ENTRY, TOKEN: ENTRY})}, declared=None
    )

    findings = found(project)

    assert with_code(findings, NOT_CHECKED)
    assert not leaks(shown(findings), MARKER)
    assert not leaks(shown(findings), TOKEN)


@pytest.mark.parametrize("name", list(PROBLEMS), ids=list(PROBLEMS))
@pytest.mark.parametrize("path", [MCP, CURSOR, CODEX], ids=["claude-code", "cursor", "codex"])
def test_without_a_declaration_an_unusable_file_is_one_information_finding(
    path: str, name: str
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("one information finding I533 for a file that cannot be
    read, with no error"), plan P-3 objective (ORQ-I533), ADR-002 decision 8 ("When the declaration
    is absent, such a file produces one information finding, which does not change the exit code,
    and nothing is checked in it"; tests cover a link, a file over the cap and a file that is not
    UTF-8 "in each branch"). ADR-003 decision 6 says that `integration_findings` "skips unreadable
    files without a finding" in that branch; the plan (AC-6, ORQ-I533) and ADR-002 decision 8 are
    later and name one information finding, so this test follows them (see QUESTIONS)."""
    project = broken_project(PROBLEMS[name], path, declared=False)

    findings = found(project)

    (note,) = with_code(findings, NOT_READ)
    assert note.severity is Severity.INFO
    assert errors_of(findings) == []
    assert UNREADABLE_FILE not in codes(findings)
    assert run(project).verdict is Verdict.NOT_RUN


@pytest.mark.parametrize("path", [CURSOR, CODEX], ids=["cursor", "codex"])
def test_without_a_declaration_a_link_in_a_parent_folder_is_one_information_finding(
    path: str,
) -> None:
    """AC-6. expected_behavior_source: AC-6, ADR-002 decision 8 ("tests cover ... a symlinked parent
    folder ... in each branch") and the FileSystem port."""
    project = broken_project(_link_in_a_parent_folder, path, declared=False)

    findings = found(project)

    (note,) = with_code(findings, NOT_READ)
    assert note.severity is Severity.INFO
    assert errors_of(findings) == []


def test_without_a_declaration_each_unusable_file_is_its_own_information_finding() -> None:
    """AC-6. expected_behavior_source: AC-6 ("one information finding I533 for a file that cannot be
    read")."""
    project = project_with({CODEX: "x = 1\n"}, declared=None)
    project.add_symlink(MCP)
    project.add_symlink(CURSOR)

    findings = found(project)

    assert len(with_code(findings, NOT_READ)) == 2
    assert errors_of(findings) == []


def test_without_a_declaration_a_warning_and_a_note_can_come_together() -> None:
    """AC-6. expected_behavior_source: AC-6 (the warning for the file that holds `orqlet-` and the
    information for the file that cannot be read, with no error)."""
    project = project_with({MCP: GOOD}, declared=None)
    project.add_symlink(CURSOR)

    findings = found(project)

    assert len(with_code(findings, NOT_CHECKED)) == 1
    assert len(with_code(findings, NOT_READ)) == 1
    assert errors_of(findings) == []


# --- an invalid or unreadable declaration ---------------------------------------------------------


def test_a_declaration_that_is_a_directory_is_a_failure_and_not_an_absent_declaration() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 6 (`validate_integrations` is not run only
    when the declaration is absent) and AC-1 (an unreadable file is an error): a path that exists
    and cannot be read is a failure."""
    project = project_with({MCP: GOOD}, declared=None)
    project.make_dir(CanonicalPath.parse(DECLARATION_PATH))

    result = run(project)

    assert_fails_with(result, "ORQ-E530")


def test_a_declaration_that_is_a_link_is_a_failure_and_not_an_absent_declaration() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 6 and ADR-002 decision 8 ("a link must not
    hide an entry from the validator while a client may follow it")."""
    project = project_with({MCP: GOOD}, declared=None)
    project.add_symlink(DECLARATION_PATH)

    assert_fails_with(run(project), "ORQ-E530")


@pytest.mark.parametrize("path", ["../outside.yaml", "/etc/integrations.yaml", ""])
def test_a_path_that_is_not_a_usable_path_is_a_failure_and_not_an_exception(path: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 3 (the reader returns findings) and plan P-3
    objective (ORQ-E530), through the validator."""
    assert_fails_with(run(MemoryFileSystem(), path), "ORQ-E530")


@pytest.mark.parametrize(
    ("declared", "code"),
    [
        (b"{{{ not yaml", "ORQ-E530"),
        (padded(DECLARED, LIMIT + 1), "ORQ-E530"),
        (declaration(server(url="https://docs.example.com/mcp")), "ORQ-E532"),
        (
            json.dumps({**json.loads(DECLARED), "surprise": 1}).encode(),
            "ORQ-E531",
        ),
        (declaration({**server(), "purpose": f"use {TOKEN}"}), "ORQ-E533"),
    ],
    ids=["strict-loader", "above-256-kib", "closed-table", "contract", "scan"],
)
def test_an_invalid_declaration_is_a_failure_with_the_finding_of_the_reader(
    declared: bytes, code: str
) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 3 ("`validate integrations` and `doctor`
    call the shared function `integration_findings`, so exit 3 and exit 5 come from one reader") and
    plan P-3 objective (ORQ-E530 to ORQ-E533)."""
    project = project_with({MCP: GOOD}, declared=declared)

    result = run(project)

    assert_fails_with(result, code)
    assert code in codes(found(project))
    assert not leaks(shown(result.findings), TOKEN)


@pytest.mark.parametrize(
    "files",
    [
        {MCP: GOOD},
        {MCP: entries_file({"orqlet-docs": DIFFERENT_ENTRIES["another-type"]})},
        {MCP: entries_file({"orqlet-docs": ENTRY, "orqlet-x": ENTRY}), CURSOR: GOOD},
        {MCP: in_team(env={"NAME": TOKEN})},
        {MCP: b"[]", CODEX: "x = 1\n"},
    ],
    ids=["clean", "differing", "undeclared", "token", "wrong-shape"],
)
def test_the_errors_of_the_function_are_the_errors_of_the_command(
    files: Mapping[str, bytes | str],
) -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 6 (one function, `integration_findings`,
    for the command, `doctor` and `sync`) and EC-5."""
    project = project_with(files)

    assert codes(errors_of(found(project))) == codes(run(project).errors)


# --- AC-8: the information about the full permissions --------------------------------------------


def test_each_registered_oauth_server_gets_one_information_finding_about_its_permissions() -> None:
    """AC-8. expected_behavior_source: AC-8 ("For each registered OAuth server validate integrations
    ... print one information finding I530 that says the entry gives the user's full permissions"),
    plan P-3 objective (ORQ-I530) and ADR-002 decision 10 ("print one information finding for each
    registered OAuth server that says the entry gives the user's full permissions"). The words are
    pinned only as far as the criterion states them: the message speaks of permissions."""
    both = entries_file({"orqlet-docs": ENTRY, "orqlet-wiki": ENTRY})

    notes = with_code(
        run(project_with({MCP: both}, declared=TWO_DECLARED)).findings, FULL_PERMISSIONS
    )

    assert len(notes) == 2
    for note in notes:
        assert note.severity is Severity.INFO
        assert "full permission" in note.message.lower()  # rework of P-3: the criterion says "full"


def test_one_registered_server_gives_one_finding() -> None:
    """AC-8. expected_behavior_source: AC-8 and ADR-002 decision 10."""
    notes = with_code(run(project_with({MCP: GOOD})).findings, FULL_PERMISSIONS)

    assert len(notes) == 1


def test_a_server_that_is_registered_for_no_client_gets_no_finding_about_permissions() -> None:
    """AC-8. expected_behavior_source: AC-8 ("For each registered OAuth server") and ADR-002
    decision 10 ("for each registered OAuth server"): an unregistered server has no entry."""
    declared = declaration(
        server("docs"), server("wiki", url="https://docs.example.com/mcp", registered=())
    )

    notes = with_code(run(project_with({MCP: GOOD}, declared=declared)).findings, FULL_PERMISSIONS)

    assert len(notes) == 1


def test_a_declaration_without_a_registered_server_gets_no_finding_about_permissions() -> None:
    """AC-8. expected_behavior_source: AC-8 and ADR-002 decision 10."""
    result = run(project_with({MCP: entries_file({})}, declared=declaration()))

    assert not with_code(result.findings, FULL_PERMISSIONS)


def test_the_finding_about_permissions_is_not_an_error_and_the_function_gives_it_too() -> None:
    """AC-8. expected_behavior_source: AC-8 ("validate integrations and doctor print") and ADR-003
    decision 6 (`integration_findings` is what `doctor` and `sync` call)."""
    project = project_with({MCP: GOOD})

    assert len(with_code(found(project), FULL_PERMISSIONS)) == 1


def test_no_finding_of_a_clean_run_claims_a_read_only_limit() -> None:
    """AC-8. expected_behavior_source: AC-8 ("no finding of the validator or the loader claims a
    read-only limit") and ADR-002 decision 10 ("the generated entry restricts nothing: the OAuth
    consent decides the scopes"). Read strictly: no message uses the words."""
    result = run(project_with({MCP: GOOD}))

    assert result.findings
    for finding in result.findings:
        assert not re.search(r"read[- ]?only", finding.message, re.IGNORECASE)


# --- AC-2: no credential-shaped value and no raw key in any message -------------------------------

SECRETS = {"token": TOKEN, "password": PASSWORD, "opaque": OPAQUE}

PLACEMENTS: dict[str, Callable[[str], bytes]] = {
    "name-of-an-undeclared-entry": lambda s: entries_file({"orqlet-docs": ENTRY, s: ENTRY}),
    "name-of-an-undeclared-orqlet-entry": lambda s: entries_file(
        {"orqlet-docs": ENTRY, f"orqlet-{s}": ENTRY}
    ),
    "name-of-an-unknown-key-of-the-declared-entry": lambda s: entries_file(
        {"orqlet-docs": {**ENTRY, s: 1}}
    ),
    "key-of-an-undeclared-entry": lambda s: in_team(**{s: 1}),
    "value-of-an-undeclared-entry": lambda s: in_team(env={"NAME": s}),
    "value-of-the-address-of-the-declared-entry": lambda s: entries_file(
        {"orqlet-docs": {**ENTRY, "url": f"https://{s}.example.com"}}
    ),
    "value-of-the-type-of-the-declared-entry": lambda s: entries_file(
        {"orqlet-docs": {**ENTRY, "type": s}}
    ),
    "key-below-a-closed-key": lambda s: in_team(headersHelper={s: "x"}),
    "value-with-a-reference": lambda s: in_team(args=["${" + s + "}"]),
    "name-of-a-duplicated-key": lambda s: (
        f'{{"mcpServers": {{"team": {{"{s}": 1, "{s}": 2}}}}}}'.encode()
    ),
    "name-of-an-entry-that-is-no-object": lambda s: f'{{"mcpServers": {{"{s}": []}}}}'.encode(),
    "name-of-a-top-level-key": lambda s: entries_file({"orqlet-docs": ENTRY}, **{s: 1}),
    "key-in-a-nested-file-above-the-depth-limit": lambda s: in_team(deep={s: nested(30)}),
    "string-above-2048-characters": lambda s: in_team(note=s * 200),
    "name-of-an-entry-in-a-file-with-more-than-64-entries": lambda s: entries_file(
        {"orqlet-docs": ENTRY, s: ENTRY, **{f"t{n}": {"type": "http"} for n in range(70)}}
    ),
}


@pytest.mark.parametrize("secret", list(SECRETS.values()), ids=list(SECRETS))
@pytest.mark.parametrize("placement", list(PLACEMENTS), ids=list(PLACEMENTS))
def test_no_finding_of_the_validator_shows_a_part_of_the_input(
    placement: str, secret: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("a test puts a shape, assembled at run time, in a key
    and in a value ... of an MCP file and requires that no output contains it"), ADR-002 decision 9
    ("Messages never carry a value or a raw key") and ORQLET-SEC-003."""
    project = project_with({MCP: PLACEMENTS[placement](secret)})

    result = run(project)
    function_findings = found(project)
    streams = capsys.readouterr()

    for text in (shown(result.findings), shown(function_findings), streams.out, streams.err):
        assert not leaks(text, secret)


@pytest.mark.parametrize("secret", list(SECRETS.values()), ids=list(SECRETS))
@pytest.mark.parametrize("path", [CURSOR, CODEX], ids=["cursor", "codex"])
def test_no_finding_about_the_other_files_shows_a_part_of_the_input(path: str, secret: str) -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-002 decision 9, for the two other MCP files:
    a secret as a name, as a key and as a value."""
    content: bytes | str
    if path == CODEX:
        content = (
            f'[mcp_servers.{secret}]\nGITHUB = "{secret}"\nurl = "https://{secret}.example.com"\n'
        )
    else:
        content = entries_file(
            {secret: {"type": "http", "env": {"NAME": secret}}, f"orqlet-{secret}": ENTRY}
        )
    project = project_with({MCP: GOOD, path: content})

    result = run(project)

    assert not leaks(shown(result.findings), secret)


@pytest.mark.parametrize("secret", [TOKEN, OPAQUE], ids=["token", "opaque"])
def test_no_finding_without_a_declaration_shows_a_part_of_the_input(secret: str) -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-002 decision 9, in the branch without a
    declaration (the warning and the information finding)."""
    project = project_with(
        {MCP: entries_file({f"orqlet-{secret}": ENTRY, secret: ENTRY})}, declared=None
    )
    project.add_symlink(CURSOR)

    assert not leaks(shown(found(project)), secret)


# --- the counts and the files that are absent ----------------------------------------------------


def test_the_counts_name_no_entry_even_when_every_undeclared_name_is_a_secret() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 ("one information finding with two counts,
    never names") and AC-2."""
    others = {
        f"{MARKER}-{n}": {"type": "http", "url": f"https://{n}.example.com/mcp"} for n in range(3)
    }

    result = run(project_with({MCP: entries_file({"orqlet-docs": ENTRY, **others})}))

    (summary,) = counts_of(result)
    assert counted(summary) == [3, 3]
    assert not leaks(shown(result.findings), MARKER)


def test_the_information_findings_do_not_change_the_verdict() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (an undeclared entry with none of the
    problems "is left alone, and counted") and ADR-003 decision 6 (an absent MCP file is
    information)."""
    result = run(project_with({CURSOR: entries_file({"team": ENTRY})}, declared=declaration()))

    assert result.verdict is Verdict.PASS
    assert all_information(result.findings)


# --- rework of P-3: a lookup that fails with a bare OSError, and the error count ------------------


class Denied(Files):
    """A project in which looking up one path fails with a bare OSError (no search permission)."""

    def __init__(self, denied: str) -> None:
        super().__init__()
        self.denied = denied

    def kind(self, path: CanonicalPath) -> Any:
        if str(path) == self.denied:
            raise PermissionError("no search permission")
        return super().kind(path)


def denied_project(path: str, *, declared: bytes | None) -> Denied:
    project = Denied(path)
    if declared is not None:
        put(project, DECLARATION_PATH, declared)
    put(project, MCP, GOOD)
    return project


def test_an_oserror_on_an_mcp_file_is_an_error_with_a_declaration_and_the_rest_is_checked() -> None:
    """AC-5. expected_behavior_source: AC-5 ("... an unreadable file ... give an error finding for
    that file, exit 5, and do not stop the other checks") and ADR-002 decision 8 ("Every file-system
    error is caught for the one file"). The adapter does not wrap every OSError."""
    project = denied_project(CURSOR, declared=DECLARED)
    project.write_atomic(CanonicalPath.parse(MCP), entries_file({"orqlet-docs": {"type": "http"}}))

    result = run(project)

    assert result.verdict is Verdict.FAIL
    assert any(names(finding, CURSOR) for finding in errors_of(result.findings))
    assert DIFFERS in codes(result.findings)  # the other file was still compared


def test_an_oserror_on_an_mcp_file_without_a_declaration_is_information_only() -> None:
    """AC-6. expected_behavior_source: AC-6 ("... one information finding I533 for a file that
    cannot be read, with no error") and ADR-002 decision 8."""
    project = denied_project(CURSOR, declared=None)

    findings = found(project)

    assert errors_of(findings) == []
    assert [finding.code for finding in findings if names(finding, CURSOR)] == [NOT_READ]


def test_the_data_of_the_command_counts_the_errors_and_not_every_finding() -> None:
    """AC-9. expected_behavior_source: AC-9 ("exit codes follow exit_codes.py") and ADR-003
    decision 6; found by the architecture review of P-3 (a passing run printed errors: 1)."""
    clean = run(project_with({MCP: GOOD}))
    broken = run(project_with({MCP: entries_file({"orqlet-docs": ENTRY, "orqlet-x": ENTRY})}))

    assert clean.verdict is Verdict.PASS
    assert clean.data["errors"] == 0
    assert broken.data["errors"] == len(errors_of(broken.findings)) >= 1
