"""`integrations_path`, `parse_integrations` and `load_integrations` (task mcp-or-plugins, P-3).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-00N-*.md`
under docs/design/mcp-or-plugins/design/, EC-n are the expected changes of the manifest.yaml next
to them, and AC-1 to AC-10 are the acceptance criteria of phase P-3 in
docs/design/mcp-or-plugins/plan.yaml. The plan fixes the finding codes of the reader: ORQ-E530 the
declaration is unreadable, above 256 KiB or refused by the strict loader; ORQ-E531 it fails its
contract; ORQ-E532 a server, mode and client that the closed table does not enable; ORQ-E533 a
scan finding in the declaration.

These tests were written first, by the Tester of phase P-3, before the reader existed. Every
declaration is built from the valid fixture (loaded as YAML, then a copy is changed, or the text of
the fixture with one address replaced), never by changing the fixture. The one pair that the closed
table enables is the Atlassian address with Claude Code; the fixture's own address is refused by
the table. Credential-shaped text is assembled from parts at run time and never written as one
literal (ORQLET-SEC-003). The file system is the in-memory fake of tests/fakes (ORQLET-TEST-001).

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- the wording of any message and what `Finding.path` holds (ADR-002 decision 9 says that a message
  prints `<key>` for a key of a free-form map and `unknown-key` for an unknown field, and that an
  unreadable declaration prints the rule `declaration-unreadable`; AC-1 and AC-2 do not state
  those words, so only the code, the severity, a non-empty message and the absence of any value or
  raw key are checked);
- how many findings one bad file gives (only the set of codes of the errors is checked);
- whether the reader itself prints the information finding ORQ-I530 for a registered OAuth server
  or the validator does (only that every finding of a valid declaration is information);
- the code for a document that the strict loader accepts and that is no mapping (an empty file, a
  list, a scalar): ORQ-E530 and ORQ-E531 are both accepted;
- whether the three small limits of ADR-002 decision 8 (nesting, entries, string length) apply to
  the declaration; AC-1 names only the size cap for it;
- what the reader does with a path that is not a canonical repository path beyond refusing it
  with ORQ-E530 and a finding that is not an exception.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.integrations import Integrations
from orqlet.application.contracts.loading import load_contract
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.filesystem import FileSystemError

# isort: split
from orqlet.application.usecases.integrations_source import (
    integrations_path,
    load_integrations,
    parse_integrations,
)

# isort: split
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.mcp_credentials import find_literal_credentials
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.python_api import canonical_signature, extract_module_api
from tests.fakes.memory_fs import MemoryFileSystem

pytestmark = pytest.mark.unit

type Outcome = tuple[Integrations | None, tuple[Finding, ...]]

PATH = ".orqlet/integrations.yaml"
LIMIT = 256 * 1024  # ADR-002 decision 8: a declaration above 256 KiB is refused
UNREADABLE = "ORQ-E530"  # plan P-3 objective: unreadable, above 256 KiB or refused by the loader
CONTRACT = "ORQ-E531"  # it fails its contract
TABLE = "ORQ-E532"  # the closed table does not enable the server, the mode and the client
SCAN = "ORQ-E533"  # the scan finds something in the declaration text
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
LOADER = StrictYamlLoader()
ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"  # the one address of the table (ADR-002 decision 2)
FIXTURE_ADDRESS = "https://docs.example.com/mcp"  # not on the table
GITHUB = "https://api.githubcopilot.com/mcp/"  # no row for GitHub (ADR-002 decision 2)
OAUTH = "client-native-oauth"
EDITABLE = "client-enforced-editable"
VARIABLE = "ORQLET_MCP_DOCS_TOKEN"
INFORMATION = Severity.INFO

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0JxQz4M", "Ka8Ty2Vb"))
PASSWORD = "".join(("hunter", "2Qx", "9Lp", "Vw4"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))


# --- helpers --------------------------------------------------------------------------------------


class CountingLoader:
    """The strict loader, counting how often it is asked to parse."""

    def __init__(self) -> None:
        self.calls = 0
        self._inner = StrictYamlLoader()

    def load(self, data: bytes, *, source: str) -> object:
        self.calls += 1
        return self._inner.load(data, source=source)


class UnreadableFileSystem(MemoryFileSystem):
    """A file system whose files can be found but not read (a permission error)."""

    def read_bytes(self, path: CanonicalPath) -> bytes:
        raise FileSystemError("the file cannot be read")


def fixture() -> dict[str, Any]:
    """The valid fixture as plain data, which a test may change freely."""
    loaded = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return copy.deepcopy(loaded)


def server(
    server_id: str = "docs",
    *,
    url: str = ATLASSIAN,
    registered: Sequence[str] = ("claude-code",),
    **changes: Any,
) -> dict[str, Any]:
    """A server that satisfies every rule of the contract, taken from the fixture's first one.

    A keyword that is not named replaces the whole field of that name.
    """
    base = copy.deepcopy(fixture()["servers"][0])
    base.update(
        id=server_id,
        identity={"kind": "remote", "url": url},
        registration={"name": f"orqlet-{server_id}", "mode": "read-only", "enforced_by": EDITABLE},
        per_client={client: {"register": True, "enforced_by": EDITABLE} for client in registered},
        clients=list(registered),
    )
    return {**base, **changes}


def env_ref_server(server_id: str = "docs", *, url: str = ATLASSIAN) -> dict[str, Any]:
    """A server that authenticates with one variable of the user's own (a valid contract)."""
    data_flow = copy.deepcopy(fixture()["servers"][0]["data_flow"])
    data_flow["backend_identity"] = "user-token"
    return server(
        server_id,
        url=url,
        auth={"mode": "env-ref", "env_refs": [VARIABLE]},
        data_flow=data_flow,
    )


def declaration(*servers: dict[str, Any]) -> dict[str, Any]:
    """The fixture's document with these servers, and a role that names each of them."""
    data = fixture()
    data["servers"] = [copy.deepcopy(item) for item in servers]
    data["roles"] = {"architecture-reviewer": {"servers": [item["id"] for item in servers]}}
    return data


def document(data: dict[str, Any]) -> bytes:
    """A declaration as JSON text, one key per line, which the strict loader reads as YAML."""
    return json.dumps(data, indent=2).encode()


def valid_bytes() -> bytes:
    """The one declaration that the loader accepts: Atlassian OAuth for Claude Code."""
    return document(declaration(server()))


def mutated(change: Callable[[dict[str, Any]], object]) -> bytes:
    """The valid declaration after `change` has edited a copy of its data."""
    data = declaration(server())
    change(data)
    return document(data)


def padded(size: int) -> bytes:
    """The valid declaration followed by short comment lines, so that the file has `size` bytes.

    The lines are short so that the scan's cap of 4096 characters per line cannot object.
    """
    base = valid_bytes() + b"\n"
    filler = size - len(base)
    assert filler >= 0
    lines, rest = divmod(filler, 64)
    tail = b"" if rest == 0 else (b"\n" if rest == 1 else b"#" + b"x" * (rest - 2) + b"\n")
    result = base + (b"#" + b"x" * 62 + b"\n") * lines + tail
    assert len(result) == size
    return result


def duplicated_purpose() -> bytes:
    """The valid declaration with one server's `purpose` key written twice."""
    text = valid_bytes()
    doubled = text.replace(
        b'"purpose": "documentation search",',
        b'"purpose": "documentation search",\n      "purpose": "again",',
        1,
    )
    assert doubled != text
    return doubled


def project_with(content: bytes, path: str = PATH) -> MemoryFileSystem:
    project = MemoryFileSystem()
    project.write_atomic(CanonicalPath.parse(path), content)
    return project


def error_codes(findings: tuple[Finding, ...]) -> set[str]:
    return {finding.code for finding in findings if finding.severity is Severity.ERROR}


def assert_refusal(outcome: Outcome, *codes: str) -> tuple[Finding, ...]:
    """No declaration, at least one error, every error with one of `codes`, every message set."""
    declared, findings = outcome
    assert declared is None
    assert isinstance(findings, tuple)
    assert all(isinstance(finding, Finding) for finding in findings)
    errors = error_codes(findings)
    assert errors, findings
    assert errors <= set(codes), (errors, codes)
    assert all(finding.message.strip() for finding in findings)
    return findings


def shown(findings: tuple[Finding, ...]) -> str:
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


# --- the declarations the tests refuse --------------------------------------------------------

# Strict-loader refusals: the bytes are not a document that the loader reads (ADR-002 decision 8).
LOADER_FAILURES: dict[str, bytes] = {
    "alias": b"schema: orqlet.integrations/v1\nservers: &s []\nagain: *s\n",
    "anchor": b"schema: orqlet.integrations/v1\nservers: &s []\n",
    "duplicate-key": b"schema: orqlet.integrations/v1\nservers: []\nservers: []\n",
    "duplicate-key-in-a-server": duplicated_purpose(),
    "merge-key": b"schema: orqlet.integrations/v1\nservers: []\n<<: {}\n",
    "python-tag": b"schema: orqlet.integrations/v1\nservers: !!python/object/apply:os.getcwd []\n",
    "local-tag": b"schema: orqlet.integrations/v1\nservers: !local []\n",
    "invalid-utf-8": b"schema: orqlet.integrations/v1\nservers: [\xff\xfe]\n",
    "control-character": b"schema: orqlet.integrations/v1\nservers: []\n\x00",
    "not-yaml": b"{{{ not yaml",
    "two-documents": valid_bytes() + b"\n---\n" + valid_bytes(),
    "nesting-deeper-than-the-loader-allows": (
        b"schema: orqlet.integrations/v1\nservers: " + b"[" * 40 + b"]" * 40 + b"\n"
    ),
}
# Documents that the strict loader reads and that are no declaration at all.
DEGENERATE: dict[str, bytes] = {
    "a-list": b"- one\n- two\n",
    "a-scalar": b"just text\n",
    "an-empty-file": b"",
}
CONTRACT_FAILURES: dict[str, Callable[[], bytes]] = {
    "unknown-top-level-field": lambda: mutated(lambda d: d.update(surprise=1)),
    "unknown-field-in-a-server": lambda: mutated(lambda d: d["servers"][0].update(surprise=1)),
    "missing-purpose": lambda: mutated(lambda d: d["servers"][0].pop("purpose")),
    "missing-policy": lambda: mutated(lambda d: d.pop("policy")),
    "another-schema": lambda: mutated(lambda d: d.update(schema="orqlet.integrations/v2")),
    "server-id-with-a-capital": lambda: document(
        declaration(
            server(
                "Docs",
                registration={"name": "orqlet-Docs", "mode": "read-only", "enforced_by": EDITABLE},
            )
        )
    ),
    "registration-name-that-is-not-orqlet-and-the-id": lambda: mutated(
        lambda d: d["servers"][0]["registration"].update(name="docs")
    ),
    "address-with-a-query": lambda: document(declaration(server(url=f"{ATLASSIAN}?a=1"))),
    "address-with-a-variable": lambda: document(declaration(server(url=f"{ATLASSIAN}/${{X}}"))),
    "address-that-is-not-https": lambda: document(
        declaration(server(url="http://mcp.atlassian.com/v2/mcp"))
    ),
    "authentication-mode-none-for-a-registered-server": lambda: mutated(
        lambda d: d["servers"][0].update(auth={"mode": "none"})
    ),
    "enforced-by-server": lambda: mutated(
        lambda d: d["servers"][0]["registration"].update(enforced_by="server")
    ),
    "verification-verified": lambda: mutated(
        lambda d: d["servers"][0]["per_client"]["claude-code"].update(verification="verified")
    ),
    "backend-identity-that-does-not-match-the-mode": lambda: mutated(
        lambda d: d["servers"][0]["data_flow"].update(backend_identity="user-token")
    ),
    "client-registered-and-missing-from-clients": lambda: mutated(
        lambda d: d["servers"][0].update(clients=[])
    ),
    "repeated-server-id": lambda: document(declaration(server("docs"), server("docs"))),
    "registration-mode-that-is-not-read-only": lambda: mutated(
        lambda d: d["servers"][0]["registration"].update(mode="read-write")
    ),
    "write-policy-that-is-not-deny": lambda: mutated(
        lambda d: d["servers"][0]["write_tools"].update(policy="allow")
    ),
    "unknown-capability-tier": lambda: mutated(
        lambda d: d["servers"][0].update(capability_tier="admin")
    ),
    "variable-for-an-oauth-server": lambda: mutated(
        lambda d: d["servers"][0]["auth"].update(env_refs=[VARIABLE])
    ),
    "stdio-server-registered-for-a-client": lambda: document(
        declaration(
            server(
                identity={"kind": "stdio", "command": "npx", "package": "@example/docs-mcp"},
            )
        )
    ),
}
# A valid contract that the closed table does not enable (ADR-002 decision 2).
TABLE_FAILURES: dict[str, Callable[[], bytes]] = {
    "the-address-of-the-fixture-for-claude-code": lambda: document(
        declaration(server(url=FIXTURE_ADDRESS))
    ),
    "atlassian-for-cursor": lambda: document(declaration(server(registered=("cursor",)))),
    "atlassian-for-codex": lambda: document(declaration(server(registered=("codex",)))),
    "atlassian-for-claude-code-and-cursor": lambda: document(
        declaration(server(registered=("claude-code", "cursor")))
    ),
    "atlassian-with-a-variable-instead-of-a-sign-in": lambda: document(
        declaration(env_ref_server())
    ),
    "atlassian-with-a-trailing-slash": lambda: document(declaration(server(url=f"{ATLASSIAN}/"))),
    "atlassian-with-a-capital-in-the-host": lambda: document(
        declaration(server(url="https://MCP.atlassian.com/v2/mcp"))
    ),
    "atlassian-with-another-path": lambda: document(
        declaration(server(url="https://mcp.atlassian.com/v1/sse"))
    ),
    "a-github-address": lambda: document(declaration(server(url=GITHUB))),
    "one-enabled-server-and-one-that-is-not": lambda: document(
        declaration(server("docs"), server("wiki", url=FIXTURE_ADDRESS))
    ),
}
# Findings of the scan on the declaration text (ADR-002 decision 7), each built at run time.
SCAN_FAILURES: dict[str, Callable[[], bytes]] = {
    "token-in-a-text": lambda: mutated(
        lambda d: d["servers"][0].update(purpose=f"use {TOKEN} to sign in")
    ),
    "token-in-a-free-form-value": lambda: mutated(
        lambda d: d["servers"][0]["data_flow"]["owner_review"].update(note=TOKEN)
    ),
    "token-in-a-free-form-key": lambda: mutated(
        lambda d: d["servers"][0]["data_flow"]["owner_review"].update({TOKEN: 1})
    ),
    "token-in-a-role-key": lambda: mutated(lambda d: d["roles"].update({TOKEN: {"servers": []}})),
    "token-in-a-per-client-key": lambda: mutated(
        lambda d: d["servers"][0]["per_client"].update(
            {TOKEN: {"register": False, "enforced_by": EDITABLE}}
        )
    ),
    "user-information-in-an-address-inside-a-text": lambda: mutated(
        lambda d: d["servers"][0].update(
            purpose=f"see https://deploy:{PASSWORD}@docs.example.com/x"
        )
    ),
    "authorization-value-in-a-text": lambda: mutated(
        lambda d: d["servers"][0].update(purpose=f"Authorization: Bearer {OPAQUE}")
    ),
    "credential-named-key-with-a-literal": lambda: mutated(
        lambda d: d["servers"][0]["data_flow"]["owner_review"].update(api_key=OPAQUE)
    ),
    "a-line-above-4096-characters": lambda: mutated(
        lambda d: d["servers"][0].update(purpose="word " * 1000)
    ),
    # Rework of P-3 (both P-2 reviewers asked for it): a stdio server is registered for no client
    # and the contract never looks at its address, so only the scan of the text can refuse it.
    "token-in-the-address-of-a-stdio-server": lambda: mutated(
        lambda d: d["servers"][0].update(
            identity={
                "kind": "stdio",
                "command": "npx",
                "package": "@example/docs-mcp",
                "url": f"https://docs.example.com/mcp?token={TOKEN}",
            },
            per_client={},
            clients=[],
        )
    ),
}


# --- EC-1: where the declaration lives --------------------------------------------------------


def test_the_declaration_is_the_file_orqlet_integrations_yaml() -> None:
    """AC-1. expected_behavior_source: EC-1 (`integrations_path() -> CanonicalPath`) and ADR-003
    decision 2 (`.orqlet/integrations.yaml` is committed)."""
    path = integrations_path()

    assert isinstance(path, CanonicalPath)
    assert path == CanonicalPath.parse(PATH)
    assert str(path) == PATH


# --- AC-10: the public names of the module ---------------------------------------------------


def test_the_module_has_exactly_the_three_public_names_that_the_manifest_adds() -> None:
    """AC-10. expected_behavior_source: AC-10 ("every other new name of the new modules starts with
    an underscore"), EC-1, EC-2 and EC-3 (the three signatures, produced by the extractor)."""
    import orqlet.application.usecases.integrations_source as module

    assert module.__file__ is not None
    api = extract_module_api(Path(module.__file__).read_text(encoding="utf-8"))

    assert api.errors == ()
    assert api.manual == ()
    assert {name: symbol.signature for name, symbol in api.symbols.items()} == {
        "integrations_path": canonical_signature("def integrations_path() -> CanonicalPath"),
        "parse_integrations": canonical_signature(
            "def parse_integrations(loader: DocumentLoader, raw: bytes, source: str)"
            " -> tuple[Integrations | None, tuple[Finding, ...]]"
        ),
        "load_integrations": canonical_signature(
            "def load_integrations(project: FileSystem, loader: DocumentLoader, path: str)"
            " -> tuple[Integrations | None, tuple[Finding, ...]]"
        ),
    }


# --- AC-1: a valid declaration ---------------------------------------------------------------


def test_the_valid_declaration_gives_the_declaration_and_information_only() -> None:
    """AC-1. expected_behavior_source: AC-1 ("(declaration, findings) with information findings
    only for a valid file"), ADR-003 decision 3 ("`(declaration, findings)` for a valid one, where
    the findings are information only") and EC-2."""
    expected = load_contract(LOADER, Integrations, valid_bytes(), source="expected")

    declared, findings = parse_integrations(LOADER, valid_bytes(), "declaration")

    assert declared == expected
    assert all(finding.severity is INFORMATION for finding in findings)
    assert all(finding.message.strip() for finding in findings)


def test_the_text_of_the_fixture_with_the_one_enabled_address_is_valid() -> None:
    """AC-1. expected_behavior_source: AC-1, ADR-002 decision 2 (the table enables the Atlassian
    address with `client-native-oauth` for `claude-code`) and the assignment ("build declarations
    by loading the fixture as YAML text and changing a copy"): the real YAML of the fixture is read,
    not only JSON."""
    text = FIXTURE.read_text(encoding="utf-8").replace(FIXTURE_ADDRESS, ATLASSIAN)
    assert ATLASSIAN in text

    declared, findings = parse_integrations(LOADER, text.encode(), "declaration")

    assert declared is not None
    assert declared.registered_for("claude-code")[0].identity.url == ATLASSIAN
    assert all(finding.severity is INFORMATION for finding in findings)


def test_a_declaration_without_servers_is_valid() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 2 ("It is optional"; a declaration lists
    servers) and ADR-002 decision 2 (the table is checked "for every server and client it
    registers": there is none)."""
    declared, findings = parse_integrations(LOADER, document(declaration()), "declaration")

    assert declared is not None
    assert declared.servers == ()
    assert all(finding.severity is INFORMATION for finding in findings)


def test_two_servers_on_the_enabled_pair_are_valid() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 2 (the table enables an address, a mode
    and a client; it does not limit how many servers use it) and decision 5 (`registered_for`
    returns servers in declaration order)."""
    declared, findings = parse_integrations(
        LOADER, document(declaration(server("docs"), server("wiki"))), "declaration"
    )

    assert declared is not None
    assert [item.id for item in declared.registered_for("claude-code")] == ["docs", "wiki"]
    assert all(finding.severity is INFORMATION for finding in findings)


def test_a_server_that_is_registered_for_no_client_is_not_checked_against_the_table() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 3 ("the closed table (`allowed_auth_modes`)
    for every server and client it registers"): an unregistered server may name any valid
    address, and the declaration stays valid."""
    data = declaration(server("docs"), server("wiki", url=FIXTURE_ADDRESS, registered=()))

    declared, findings = parse_integrations(LOADER, document(data), "declaration")

    assert declared is not None
    assert [item.id for item in declared.registered_for("claude-code")] == ["docs"]
    assert all(finding.severity is INFORMATION for finding in findings)


def test_valid_findings_claim_no_read_only_limit() -> None:
    """AC-8. expected_behavior_source: AC-8 ("no finding of the validator or the loader claims a
    read-only limit") and ADR-002 decision 10 (the entry restricts nothing: the consent decides the
    scopes). Read strictly: no message of the reader uses the words."""
    _, findings = parse_integrations(LOADER, valid_bytes(), "declaration")

    for finding in findings:
        assert "read-only" not in finding.message.lower()
        assert "read only" not in finding.message.lower()


def test_the_same_bytes_give_the_same_answer() -> None:
    """AC-1. expected_behavior_source: ORQLET-DET-001 (deterministic output) and EC-2."""
    for content in (valid_bytes(), CONTRACT_FAILURES["repeated-server-id"](), b"{{{"):
        assert parse_integrations(LOADER, content, "declaration") == parse_integrations(
            LOADER, content, "declaration"
        )


# --- AC-1: absent ----------------------------------------------------------------------------


def test_an_absent_file_is_no_declaration_and_no_finding() -> None:
    """AC-1. expected_behavior_source: AC-1 ("load_integrations returns (None, ()) for an absent
    file"), ADR-003 decision 3 ("`(None, ())` for an absent file") and EC-3."""
    project = MemoryFileSystem()

    assert load_integrations(project, LOADER, PATH) == (None, ())
    assert project.snapshot() == {}


def test_an_absent_file_in_an_existing_folder_is_no_declaration_and_no_finding() -> None:
    """AC-1. expected_behavior_source: AC-1 and ADR-003 decision 3 (absent means that the file is
    not there, whatever else the folder holds)."""
    project = project_with(b"x: 1\n", ".orqlet/other.yaml")

    assert load_integrations(project, LOADER, PATH) == (None, ())


def test_a_valid_file_loads_and_nothing_is_written() -> None:
    """AC-1. expected_behavior_source: EC-3 (`load_integrations(project, loader, path)`) and
    ADR-003 decision 3 (the reader reads through the `FileSystem` port; the loader owns the
    checks; nothing is written)."""
    project = project_with(valid_bytes())
    before = project.snapshot()
    expected = load_contract(LOADER, Integrations, valid_bytes(), source="expected")

    declared, findings = load_integrations(project, LOADER, PATH)

    assert declared == expected
    assert all(finding.severity is INFORMATION for finding in findings)
    assert project.snapshot() == before


def test_load_integrations_reads_the_path_it_is_given() -> None:
    """AC-1. expected_behavior_source: EC-3 (the `path` parameter) and plan P-3 file operation on
    commands/validate.py (`validate integrations` takes a file argument)."""
    project = project_with(valid_bytes(), "other/declaration.yaml")

    assert load_integrations(project, LOADER, "other/declaration.yaml")[0] is not None
    assert load_integrations(project, LOADER, PATH) == (None, ())


# --- AC-1: ORQ-E530, the declaration cannot be used as a document -----------------------------


@pytest.mark.parametrize("name", list(LOADER_FAILURES), ids=list(LOADER_FAILURES))
def test_a_document_that_the_strict_loader_refuses_is_an_unreadable_declaration(name: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("(None, findings) with at least one error for a file
    that is ... refused by the strict loader"), plan P-3 objective (ORQ-E530: refused by the strict
    loader) and ADR-002 decision 8 (anchors, tags and duplicate keys are refused; the declaration
    is read with the strict loader)."""
    assert_refusal(parse_integrations(LOADER, LOADER_FAILURES[name], "declaration"), UNREADABLE)


@pytest.mark.parametrize("name", list(DEGENERATE), ids=list(DEGENERATE))
def test_a_document_that_is_no_mapping_is_refused(name: str) -> None:
    """AC-1. expected_behavior_source: AC-1 (a file that is refused by the strict loader or breaks
    the contract is `(None, findings)`) and ADR-003 decision 3. The code is not fixed for a
    document that the loader reads and that is no mapping, so either of the two is accepted."""
    assert_refusal(
        parse_integrations(LOADER, DEGENERATE[name], "declaration"), UNREADABLE, CONTRACT
    )


def test_an_unreadable_declaration_never_raises_out_of_the_reader() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 3 (an invalid declaration is `(None,
    findings)`, so that `upgrade` can refuse with exit 3 and the validator with exit 5) and
    ADR-002 decision 9 (the reader catches `DocumentError`)."""
    for content in (*LOADER_FAILURES.values(), *DEGENERATE.values()):
        declared, findings = parse_integrations(LOADER, content, "declaration")

        assert declared is None
        assert findings


@pytest.mark.parametrize("size", [LIMIT + 1, 2 * LIMIT, 8 * LIMIT])
def test_bytes_above_256_kib_are_refused_before_they_are_parsed(size: int) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a file that is ... over 256 KiB"), plan P-3 objective
    (ORQ-E530: over 256 KiB) and ADR-002 decision 8 ("refused above 256 KiB ... the size is checked
    after the file is read"). The padded text is a valid declaration, so only its size is wrong; the
    loader of the test has the default bound of 1 MiB, so the refusal is not the loader's."""
    loader = CountingLoader()

    assert_refusal(parse_integrations(loader, padded(size), "declaration"), UNREADABLE)
    assert loader.calls == 0


def test_oversized_bytes_that_are_not_even_yaml_are_refused_for_their_size() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (the size cap comes first)."""
    loader = CountingLoader()

    assert_refusal(parse_integrations(loader, b"{{{" * LIMIT, "declaration"), UNREADABLE)
    assert loader.calls == 0


def test_bytes_of_exactly_256_kib_are_not_above_the_limit() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 ("refused above 256 KiB": a file of
    exactly 256 KiB is parsed)."""
    declared, findings = parse_integrations(LOADER, padded(LIMIT), "declaration")

    assert declared is not None
    assert all(finding.severity is INFORMATION for finding in findings)


def test_a_directory_in_the_place_of_the_file_cannot_be_read() -> None:
    """AC-1. expected_behavior_source: AC-1 ("a file that is unreadable"), ADR-003 decision 3
    (the reader reads through the `FileSystem` port) and plan P-3 objective (ORQ-E530). The port
    refuses a read of anything that is not a regular file."""
    project = MemoryFileSystem()
    project.make_dir(CanonicalPath.parse(PATH))
    loader = CountingLoader()

    assert_refusal(load_integrations(project, loader, PATH), UNREADABLE)
    assert loader.calls == 0


def test_a_symbolic_link_in_the_place_of_the_file_cannot_be_read() -> None:
    """AC-1. expected_behavior_source: AC-1, ORQLET-SEC-002 (files of the repository are untrusted
    and read through the port, which refuses links) and plan P-3 objective (ORQ-E530)."""
    project = MemoryFileSystem()
    project.add_symlink(PATH)
    loader = CountingLoader()

    assert_refusal(load_integrations(project, loader, PATH), UNREADABLE)
    assert loader.calls == 0


def test_a_symbolic_link_above_the_file_cannot_be_read() -> None:
    """AC-1. expected_behavior_source: AC-1, the FileSystem port ("a link above it raises
    `LinkRefused`, because nothing below a link may be trusted"), ADR-002 decision 8 ("every
    file-system error is caught ..., including a link in a parent folder") and plan P-3 objective
    (ORQ-E530)."""
    project = project_with(valid_bytes())
    project.add_symlink(".orqlet")
    loader = CountingLoader()

    assert_refusal(load_integrations(project, loader, PATH), UNREADABLE)
    assert loader.calls == 0


def test_a_file_that_the_port_cannot_read_is_a_finding_and_not_an_exception() -> None:
    """AC-1. expected_behavior_source: AC-1 ("a file that is unreadable"), ADR-002 decision 8 (a
    file-system error is caught) and plan P-3 objective (ORQ-E530). The local adapter raises
    `FileSystemError` for an error of the operating system, such as a permission error."""
    project = UnreadableFileSystem()
    project.write_atomic(CanonicalPath.parse(PATH), valid_bytes())
    loader = CountingLoader()

    assert_refusal(load_integrations(project, loader, PATH), UNREADABLE)
    assert loader.calls == 0


@pytest.mark.parametrize("path", ["../outside.yaml", "/etc/integrations.yaml", "", "a/../../b"])
def test_a_path_that_is_not_a_usable_path_is_a_finding_and_not_an_exception(path: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a file that is unreadable": the path cannot name one),
    ADR-003 decision 3 (the reader returns findings) and plan P-3 objective (ORQ-E530)."""
    assert_refusal(load_integrations(MemoryFileSystem(), LOADER, path), UNREADABLE)


@pytest.mark.parametrize("size", [LIMIT + 1, 2 * LIMIT])
def test_a_file_above_256_kib_is_refused_after_it_is_read_and_before_it_is_parsed(
    size: int,
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("over 256 KiB"), ADR-002 decision 8 and plan P-3
    objective (ORQ-E530)."""
    loader = CountingLoader()

    assert_refusal(load_integrations(project_with(padded(size)), loader, PATH), UNREADABLE)
    assert loader.calls == 0


def test_a_file_of_exactly_256_kib_is_loaded() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (only a file above 256 KiB is refused)."""
    declared, _ = load_integrations(project_with(padded(LIMIT)), LOADER, PATH)

    assert declared is not None


# --- AC-1: ORQ-E531, the contract ------------------------------------------------------------


@pytest.mark.parametrize("name", list(CONTRACT_FAILURES), ids=list(CONTRACT_FAILURES))
def test_a_declaration_that_breaks_the_contract_is_refused(name: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a file that ... breaks the contract"), plan P-3
    objective (ORQ-E531 declaration fails its contract) and ADR-003 decision 3 ("the strict read
    and the contract validation (including `name_problems`)"). Each case breaks one rule of the
    tightened contract (ADR-002 decisions 1, 3, 4, 5 and 10) or its structure."""
    assert_refusal(parse_integrations(LOADER, CONTRACT_FAILURES[name](), "declaration"), CONTRACT)


def test_a_contract_refusal_names_no_error_of_another_family() -> None:
    """AC-1. expected_behavior_source: plan P-3 objective (E531 for a contract failure, E532 for the
    table, E533 for the scan: one family per cause)."""
    findings = assert_refusal(
        parse_integrations(LOADER, CONTRACT_FAILURES["repeated-server-id"](), "declaration"),
        CONTRACT,
    )

    assert error_codes(findings) == {CONTRACT}


# --- AC-1: ORQ-E532, the closed table --------------------------------------------------------


@pytest.mark.parametrize("name", list(TABLE_FAILURES), ids=list(TABLE_FAILURES))
def test_a_server_mode_and_client_that_the_table_does_not_enable_are_refused(name: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("names a server, mode and client that the table does
    not enable"), plan P-3 objective (ORQ-E532), ADR-002 decision 2 ("a declaration that names a
    combination which a later table no longer enables is refused by the loader, with a rule that
    says so"; one row: the Atlassian address, `client-native-oauth`, `claude-code`) and ADR-003
    decision 3 (the loader owns the closed table). Each contract is valid, so only the table
    refuses."""
    findings = assert_refusal(
        parse_integrations(LOADER, TABLE_FAILURES[name](), "declaration"), TABLE
    )

    assert error_codes(findings) == {TABLE}


@pytest.mark.parametrize("name", list(TABLE_FAILURES), ids=list(TABLE_FAILURES))
def test_the_table_cases_are_valid_for_the_contract(name: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 2 ("The table lives in the domain module,
    outside the contract, so the contract's own rules do not change when a tool release changes
    the table"): the declarations of the table cases load as contracts. This holds before the
    reader exists and guards the premise of the test above."""
    load_contract(LOADER, Integrations, TABLE_FAILURES[name](), source="declaration")


# --- AC-1: ORQ-E533, the scan ----------------------------------------------------------------


@pytest.mark.parametrize("name", list(SCAN_FAILURES), ids=list(SCAN_FAILURES))
def test_a_declaration_with_a_scan_finding_is_refused(name: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("or holds a scan finding"), plan P-3 objective
    (ORQ-E533 scan finding in the declaration) and ADR-002 decision 7 ("The scan runs on the
    declaration (in the loader)"). Each text is a valid contract and holds one credential shape,
    built at run time."""
    findings = assert_refusal(
        parse_integrations(LOADER, SCAN_FAILURES[name](), "declaration"), SCAN
    )

    assert error_codes(findings) == {SCAN}


@pytest.mark.parametrize("name", list(SCAN_FAILURES), ids=list(SCAN_FAILURES))
def test_the_scan_texts_are_valid_for_the_contract(name: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 7 (the scan, not the contract, finds them).
    This holds before the reader exists and guards the premise of the test above."""
    load_contract(LOADER, Integrations, SCAN_FAILURES[name](), source="declaration")


@pytest.mark.parametrize("name", list(SCAN_FAILURES), ids=list(SCAN_FAILURES))
def test_the_scan_texts_are_found_by_the_scan_itself(name: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 7 (`find_literal_credentials` reports the
    shapes). This holds before the reader exists and guards the premise of the test above: the
    shapes are long enough for the scan, and the valid declaration holds none."""
    assert find_literal_credentials(SCAN_FAILURES[name]().decode())
    assert find_literal_credentials(valid_bytes().decode()) == ()


@pytest.mark.parametrize("name", list(CONTRACT_FAILURES), ids=list(CONTRACT_FAILURES))
def test_the_contract_cases_are_invalid_for_the_contract(name: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decisions 1, 3, 4, 5 and 10 (the validators of the
    contract). This holds before the reader exists and guards the premise of the tests above."""
    with pytest.raises(DocumentError):
        load_contract(LOADER, Integrations, CONTRACT_FAILURES[name](), source="declaration")


# --- load_integrations gives the answer of parse_integrations --------------------------------

ALL_CASES: dict[str, bytes] = {
    "valid": valid_bytes(),
    **{f"loader-{name}": content for name, content in LOADER_FAILURES.items()},
    **{f"degenerate-{name}": content for name, content in DEGENERATE.items()},
    **{f"contract-{name}": build() for name, build in CONTRACT_FAILURES.items()},
    **{f"table-{name}": build() for name, build in TABLE_FAILURES.items()},
    **{f"scan-{name}": build() for name, build in SCAN_FAILURES.items()},
}


@pytest.mark.parametrize("name", list(ALL_CASES), ids=list(ALL_CASES))
def test_load_gives_the_answer_of_parse_for_the_bytes_of_the_file(name: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 3 ("`load_integrations(project, loader,
    path)`": the one reader; `parse_integrations` is the part that turns bytes into a result) and
    ADR-003 consequences ("One reader means `doctor`, `validate` and `upgrade` cannot disagree")."""
    content = ALL_CASES[name]
    parsed, parse_findings = parse_integrations(LOADER, content, PATH)

    loaded, load_findings = load_integrations(project_with(content), LOADER, PATH)

    assert loaded == parsed
    assert {(f.code, f.severity) for f in load_findings} == {
        (f.code, f.severity) for f in parse_findings
    }


# --- AC-2: no message holds a credential-shaped value or a raw key ----------------------------

# A placement puts one secret where a person could put it by mistake: in a key or a value of a
# free-form map, in the name of an unknown field, in a closed field, in the document's own syntax.
# Every case is a refusal, so a finding exists and none may show any part of the secret.
PLACEMENTS: dict[str, Callable[[str], bytes]] = {
    "name-of-an-unknown-top-level-field": lambda s: mutated(lambda d: d.update({s: 1})),
    "name-of-an-unknown-field-in-a-server": lambda s: mutated(
        lambda d: d["servers"][0].update({s: 1})
    ),
    "name-of-an-unknown-field-in-the-identity": lambda s: mutated(
        lambda d: d["servers"][0]["identity"].update({s: 1})
    ),
    "name-of-an-unknown-field-in-the-data-flow": lambda s: mutated(
        lambda d: d["servers"][0]["data_flow"].update({s: 1})
    ),
    "name-of-an-unknown-field-in-a-role": lambda s: mutated(
        lambda d: d["roles"]["architecture-reviewer"].update({s: 1})
    ),
    "name-of-an-unknown-field-in-the-policy": lambda s: mutated(
        lambda d: d["policy"].update({s: 1})
    ),
    "key-of-a-per-client-map-with-an-entry-of-the-wrong-shape": lambda s: mutated(
        lambda d: d["servers"][0]["per_client"].update({s: {"register": "not-a-boolean"}})
    ),
    "key-of-the-owner-review-map-with-a-value-of-the-wrong-shape": lambda s: mutated(
        lambda d: d["servers"][0]["data_flow"]["owner_review"].update({s: ["a", "list"]})
    ),
    "key-of-the-roles-map-with-a-role-of-the-wrong-shape": lambda s: mutated(
        lambda d: d["roles"].update({s: {"servers": "not-a-list"}})
    ),
    "value-in-the-capability-tier": lambda s: mutated(
        lambda d: d["servers"][0].update(capability_tier=s)
    ),
    "value-in-the-schema": lambda s: mutated(lambda d: d.update(schema=s)),
    "value-in-the-identity-kind": lambda s: mutated(
        lambda d: d["servers"][0]["identity"].update(kind=s)
    ),
    "value-in-the-authentication-mode": lambda s: mutated(
        lambda d: d["servers"][0]["auth"].update(mode=s)
    ),
    "value-in-the-registration-mode": lambda s: mutated(
        lambda d: d["servers"][0]["registration"].update(mode=s)
    ),
    "value-in-a-label": lambda s: mutated(
        lambda d: d["servers"][0]["registration"].update(enforced_by=s)
    ),
    "entry-of-the-clients-list": lambda s: mutated(lambda d: d["servers"][0].update(clients=[s])),
    "server-id": lambda s: mutated(
        lambda d: d["servers"][0].update(
            id=s, registration={"name": f"orqlet-{s}", "mode": "read-only", "enforced_by": EDITABLE}
        )
    ),
    "registration-name": lambda s: mutated(
        lambda d: d["servers"][0]["registration"].update(name=s)
    ),
    "address": lambda s: mutated(
        lambda d: d["servers"][0]["identity"].update(url=f"{ATLASSIAN}?{s}=1")
    ),
    "variable-name": lambda s: mutated(
        lambda d: d["servers"][0].update(
            auth={"mode": "env-ref", "env_refs": [s]},
            data_flow={**d["servers"][0]["data_flow"], "backend_identity": "user-token"},
        )
    ),
    "name-of-a-duplicated-key": lambda s: (
        f"schema: orqlet.integrations/v1\n{s}: 1\n{s}: 2\n".encode()
    ),
    "name-of-an-anchor": lambda s: f"schema: orqlet.integrations/v1\nservers: &{s} []\n".encode(),
    "name-of-an-alias": lambda s: (
        f"schema: orqlet.integrations/v1\nservers: &a []\nagain: *{s}\n".encode()
    ),
    "name-of-a-tag": lambda s: f"schema: orqlet.integrations/v1\nservers: !{s} []\n".encode(),
    "name-of-a-tag-in-a-value": lambda s: f"schema: !{s} orqlet.integrations/v1\n".encode(),
    "an-oversized-file-full-of-it": lambda s: (f"token: {s}\n".encode() * (LIMIT // 8))[
        : LIMIT + 1
    ],
}
SECRETS = {"token": TOKEN, "password": PASSWORD, "opaque": OPAQUE}


@pytest.mark.parametrize("secret", list(SECRETS.values()), ids=list(SECRETS))
@pytest.mark.parametrize("placement", list(PLACEMENTS), ids=list(PLACEMENTS))
def test_no_finding_of_parse_integrations_shows_a_part_of_the_input(
    placement: str, secret: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("a test puts a shape, assembled at run time, in a key
    and in a value of each free-form map of the declaration ... and requires that no output
    contains it"), ADR-002 decision 9 ("The loader does not use the default error text of the
    contract loader, which prints `loc` and `msg` (so raw keys of free-form maps), and it catches
    `DocumentError` from the strict YAML loader, whose text can hold a duplicate key or a tag")
    and ORQLET-SEC-003."""
    content = PLACEMENTS[placement](secret)

    findings = assert_refusal(
        parse_integrations(LOADER, content, "declaration"), UNREADABLE, CONTRACT, SCAN
    )
    streams = capsys.readouterr()

    assert not leaks(shown(findings), secret)
    assert not leaks(streams.out, secret)
    assert not leaks(streams.err, secret)


@pytest.mark.parametrize("secret", list(SECRETS.values()), ids=list(SECRETS))
@pytest.mark.parametrize("placement", list(PLACEMENTS), ids=list(PLACEMENTS))
def test_no_finding_of_load_integrations_shows_a_part_of_the_input(
    placement: str, secret: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-002 decision 9 (the same as above, through the
    file system port) and ORQLET-SEC-003."""
    content = PLACEMENTS[placement](secret)

    findings = assert_refusal(
        load_integrations(project_with(content), LOADER, PATH), UNREADABLE, CONTRACT, SCAN
    )
    streams = capsys.readouterr()

    assert not leaks(shown(findings), secret)
    assert not leaks(streams.out, secret)
    assert not leaks(streams.err, secret)


@pytest.mark.parametrize("secret", [TOKEN, OPAQUE], ids=["token", "opaque"])
def test_a_secret_in_the_free_form_values_of_a_valid_declaration_is_not_shown(secret: str) -> None:
    """AC-2. expected_behavior_source: AC-2 ("in a key and in a value of each free-form map") and
    ADR-002 decision 9. A value of the owner review, a role's server list and a free text are valid
    for the contract; whatever the reader prints about the declaration, it holds no part of
    them."""
    content = mutated(
        lambda d: (
            d["servers"][0]["data_flow"]["owner_review"].update(note=secret),
            d["servers"][0].update(purpose=f"note {secret}"),
            d["roles"]["architecture-reviewer"]["servers"].append(secret),
        )
    )

    _, findings = parse_integrations(LOADER, content, "declaration")

    assert not leaks(shown(findings), secret)


def test_a_finding_about_one_server_does_not_name_another_servers_secret() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 9 (a message names a rule and a closed
    field name, never a value): two servers, one with a rule broken and a secret as the other's
    purpose."""
    data = declaration(
        server("docs", purpose=f"note {OPAQUE}"), server("wiki", url=FIXTURE_ADDRESS)
    )

    findings = assert_refusal(
        parse_integrations(LOADER, document(data), "declaration"), TABLE, SCAN, CONTRACT
    )

    assert not leaks(shown(findings), OPAQUE)


# --- rework of P-3: the lists that the reader keeps in step with the contract and the domain ------


class PermissionDeniedFileSystem(MemoryFileSystem):
    """A file system whose lookup of the declaration fails with a bare OSError."""

    def kind(self, path: CanonicalPath) -> Any:
        raise PermissionError("no search permission")


def test_an_oserror_of_the_file_system_is_a_finding_and_never_an_exception() -> None:
    """AC-1. expected_behavior_source: AC-1 ("... a file that is unreadable ... gives (None,
    findings) with at least one error") and ADR-002 decision 8 ("Any other exception is a defect
    and exits 70": an unreadable directory is not a defect). The file system adapter does not wrap
    every OSError, so the reader must."""
    outcome = load_integrations(PermissionDeniedFileSystem(), LOADER, PATH)

    assert outcome[0] is None
    assert {finding.code for finding in outcome[1]} == {UNREADABLE}


def test_the_free_form_maps_that_the_reader_masks_are_the_dict_fields_of_the_contract() -> None:
    """AC-2. expected_behavior_source: AC-2 ("no message ... holds ... a raw key") and ADR-002
    decision 9 (`<key>` for a key of a free-form map). A dict field that the reader did not know
    would print its raw keys in an error location."""
    import typing

    import orqlet.application.contracts.integrations as contract
    import orqlet.application.usecases.integrations_source as module
    from orqlet.application.contracts.common import Contract

    models = [
        value
        for value in vars(contract).values()
        if isinstance(value, type) and issubclass(value, Contract)
    ]
    dict_fields = {
        name
        for model in models
        for name, field in model.model_fields.items()
        if typing.get_origin(field.annotation) is dict
    }

    assert dict_fields == set(module._FREE_FORM)


def test_the_clients_of_the_reader_and_of_the_validator_are_those_that_have_an_mcp_file() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 5 ("a test fails when [the places that
    enumerate the clients] diverge") and EC-16. The three clients are the ones for which
    `mcp_file_path` gives a path; an unknown client gives none."""
    import orqlet.application.usecases.integrations_source as source
    import orqlet.application.usecases.validate_integrations as validator
    from orqlet.domain.mcp_credentials import mcp_file_path

    def has_a_file(client: str) -> bool:
        try:
            mcp_file_path(client)
        except ValueError:
            return False
        return True

    known = {
        client for client in ("claude-code", "codex", "cursor", "vscode") if has_a_file(client)
    }

    assert known == {"claude-code", "codex", "cursor"}
    assert set(source._CLIENTS) == known
    assert set(validator._CLIENTS) == known
