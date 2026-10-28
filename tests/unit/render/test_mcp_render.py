"""`render_mcp_file`: the JSON text of one client's MCP file (task mcp-or-plugins, phase P-5).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-00N-*.md`
under docs/design/mcp-or-plugins/design/, EC-n are the expected changes of the manifest.yaml next
to them, and AC-1 and AC-2 are the criteria of phase P-5 in docs/design/mcp-or-plugins/plan.yaml
that concern this function (AC-1: the text, its shape, its determinism and the golden file; AC-2:
the scan of the text it builds).

These tests were written first, by the Tester of phase P-5, before `orqlet.adapters.render.mcp`
existed. The golden file `tests/golden/claude-code/integrations-2026-10/.mcp.json` was written by
hand from AC-1 (the specification, not the output), and a test below reads it back and compares it
with the same specification, so `--update-golden` cannot make a wrong renderer pass.

What the design fixes and the tests use: `render_mcp_file(servers, client) -> str`; the text is
`{"mcpServers": {"orqlet-<id>": {"type": "http", "url": "<address>"}}}` made with `json.dumps`,
an indent of two and one trailing newline, from `rendered_entry`; the entries come in the order of
the servers that are given; the text that it builds is scanned with `find_literal_credentials`,
imported by name into the module, and a finding makes it raise `ValueError` with a message that
holds no value (ADR-002 decision 7, decision 9); `rendered_entry` refuses (`ValueError`) a client
and an address that the closed table does not enable, which is the whole table but one pair: the
Atlassian address with `claude-code` (ADR-002 decision 2). Credential-shaped text is assembled from
parts at run time and never written as one literal (ORQLET-SEC-003).

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- what `render_mcp_file` does for an empty list of servers (the adapter does not call it then);
- the wording of the message of the `ValueError`, apart from its holding no value;
- the number of times the text is scanned (at least once, with the document that it returns);
- whether the scan sees the text with or without its final newline (only that the scanned text
  holds the whole document);
- the order of the checks when a text breaks several rules, and the `ValueError` for a server that
  is not a registered one (the function takes the servers that `registered_for` gives).
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from orqlet.adapters.render.mcp import render_mcp_file

from orqlet.adapters.render import mcp as mcp_module
from orqlet.application.contracts.integrations import McpServer
from orqlet.domain.mcp_credentials import CredentialFinding, rendered_entry

pytestmark = pytest.mark.unit

ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"  # the one address of the closed table
OTHER_ADDRESS = "https://docs.example.com/mcp"  # a valid address that the table does not enable
CLIENT = "claude-code"  # the one client for which the table enables an entry
EDITABLE = "client-enforced-editable"
FAMILY = "integrations-2026-10"
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
GOLDEN_FILE = Path(__file__).resolve().parents[2] / "golden" / CLIENT / FAMILY / ".mcp.json"
# The text of AC-1 for one server `atlassian`, written out: indent of two, one final newline.
ATLASSIAN_TEXT = (
    "{\n"
    '  "mcpServers": {\n'
    '    "orqlet-atlassian": {\n'
    '      "type": "http",\n'
    '      "url": "https://mcp.atlassian.com/v2/mcp"\n'
    "    }\n"
    "  }\n"
    "}\n"
)

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0JxQz4M", "Ka8Ty2Vb"))
SENTINEL = "".join(("entry-", "only-", "text-", "c41e", "7b93"))


# --- helpers --------------------------------------------------------------------------------------


def server(
    server_id: str = "atlassian",
    *,
    url: str = ATLASSIAN,
    registered: tuple[str, ...] = (CLIENT,),
    **changes: Any,
) -> McpServer:
    """A server that satisfies every rule of the contract, made from the fixture's first one."""
    loaded = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    base: dict[str, Any] = copy.deepcopy(loaded["servers"][0])
    base.update(
        id=server_id,
        identity={"kind": "remote", "url": url},
        registration={"name": f"orqlet-{server_id}", "mode": "read-only", "enforced_by": EDITABLE},
        per_client={name: {"register": True, "enforced_by": EDITABLE} for name in registered},
        clients=list(registered),
    )
    base.update(changes)
    return McpServer.model_validate(base)


def entry_names(text: str) -> list[str]:
    document = json.loads(text)
    return list(document["mcpServers"])


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters of it in a row (any case)."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


# --- AC-1: the text -------------------------------------------------------------------------------


def test_ac1_one_server_gives_the_text_of_the_specification() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 (`{"mcpServers": {"orqlet-<id>":
    {"type": "http", "url": "<address>"}}}`, `json.dumps`, an indent of two and a trailing
    newline) and AC-1 ("one JSON object text ... with an indent of two, a trailing newline")."""
    assert render_mcp_file((server(),), CLIENT) == ATLASSIAN_TEXT


def test_ac1_two_servers_give_both_entries_in_the_order_that_is_given() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 (one `orqlet-<id>` entry per server) and
    ADR-002 decision 5 ("`registered_for` ... in declaration order"): the text is written out for
    the order `zeta`, `alpha`."""
    text = render_mcp_file((server("zeta"), server("alpha")), CLIENT)

    assert text == (
        "{\n"
        '  "mcpServers": {\n'
        '    "orqlet-zeta": {\n'
        '      "type": "http",\n'
        '      "url": "https://mcp.atlassian.com/v2/mcp"\n'
        "    },\n"
        '    "orqlet-alpha": {\n'
        '      "type": "http",\n'
        '      "url": "https://mcp.atlassian.com/v2/mcp"\n'
        "    }\n"
        "  }\n"
        "}\n"
    )


@pytest.mark.parametrize(
    "ids",
    [
        ("alpha", "mid", "zeta"),
        ("zeta", "mid", "alpha"),
        ("mid", "zeta", "alpha"),
        ("a", "a1", "a-b", "z" * 32),
    ],
    ids=["sorted", "reversed", "shuffled", "edges-of-the-id-pattern"],
)
def test_ac1_the_entries_follow_the_order_of_the_servers_and_are_never_sorted(
    ids: tuple[str, ...],
) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("entries in the order given") and
    ADR-002 decision 5 (`orqlet-<id>` for every server, an id of at most 32 characters): any order
    that is given comes back as it is, so a renderer that sorts the names fails."""
    text = render_mcp_file(tuple(server(name) for name in ids), CLIENT)

    assert entry_names(text) == [f"orqlet-{name}" for name in ids]
    assert text == json.dumps(json.loads(text), indent=2) + "\n"


def test_ac1_the_golden_file_is_the_file_that_the_renderer_writes(
    golden: Callable[[str, bytes], None],
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("the golden file is byte-identical") and plan P-5
    file_operations (`tests/golden/claude-code/integrations-2026-10/.mcp.json`, "the golden file
    of the rendered .mcp.json for one declared Atlassian server"). `--update-golden` rewrites it
    and the next test reads it back."""
    golden(f"{CLIENT}/{FAMILY}/.mcp.json", render_mcp_file((server(),), CLIENT).encode("utf-8"))


def test_ac1_the_golden_file_is_the_specification_and_not_the_output_of_the_renderer() -> None:
    """AC-1. expected_behavior_source: AC-1 (the text, indent of two, one trailing newline, no
    key other than type and url) and ORQLET-DET-001: the committed golden file was written by hand
    from the specification, and it still is the specification after any `--update-golden`."""
    assert GOLDEN_FILE.read_bytes() == ATLASSIAN_TEXT.encode("utf-8")


def test_ac1_the_text_is_one_object_with_the_one_key_and_the_entry_has_two_keys() -> None:
    """AC-1. expected_behavior_source: AC-1 ("no key other than type and url") and ADR-003
    decision 4 (the output is one JSON object, `mcpServers` is its one key)."""
    document = json.loads(render_mcp_file((server("one"), server("two")), CLIENT))

    assert list(document) == ["mcpServers"]
    for name, entry in document["mcpServers"].items():
        assert list(entry) == ["type", "url"], name
        assert entry == {"type": "http", "url": ATLASSIAN}


@pytest.mark.parametrize("count", [1, 2, 3])
def test_ac1_the_text_ends_with_exactly_one_newline_and_has_no_other_whitespace_at_the_end(
    count: int,
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("an indent of two, a trailing newline") and ADR-003
    decision 4 (`json.dumps` ... "a trailing newline"): the text ends with `}` and one `\\n`, with
    no blank line after it, and uses `\\n` for every line break."""
    text = render_mcp_file(tuple(server(f"s{number}") for number in range(count)), CLIENT)

    assert text.endswith("}\n")
    assert not text.endswith("\n\n")
    assert "\r" not in text
    assert text == text.rstrip() + "\n"
    assert not [line for line in text.split("\n")[:-1] if line != line.rstrip()]
    assert text.isascii()


def test_ac1_the_indent_is_two_spaces_for_every_level_and_never_a_tab() -> None:
    """AC-1. expected_behavior_source: AC-1 ("an indent of two"): the lines of the text start with
    an even number of spaces, at most six, and with no tab."""
    lines = render_mcp_file((server("one"), server("two")), CLIENT).split("\n")[:-1]

    depths = {len(line) - len(line.lstrip(" ")) for line in lines}
    assert depths == {0, 2, 4, 6}
    assert not [line for line in lines if "\t" in line]


def test_ac1_the_same_input_gives_the_same_bytes() -> None:
    """AC-1. expected_behavior_source: AC-1 ("the same input gives the same bytes") and
    ORQLET-DET-001: two calls with the same servers, and two calls with servers that were made
    twice from the same data, give equal text and equal bytes."""
    first = render_mcp_file((server("one"), server("two")), CLIENT)
    second = render_mcp_file((server("one"), server("two")), CLIENT)
    again = render_mcp_file((server("one"), server("two")), CLIENT)

    assert first == second == again
    assert first.encode("utf-8") == second.encode("utf-8")


def test_ac1_the_text_does_not_depend_on_the_folder_or_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("no timestamp, absolute path or random value") and
    ORQLET-DET-001: a render in another working folder and with another home folder, user name
    and time zone gives the same bytes, and the text holds none of them."""
    before = render_mcp_file((server(),), CLIENT)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USER", "someone-else")
    monkeypatch.setenv("TZ", "Pacific/Auckland")
    after = render_mcp_file((server(),), CLIENT)

    assert after == before == ATLASSIAN_TEXT
    assert str(tmp_path) not in after


def test_ac1_each_entry_is_what_rendered_entry_returns_for_the_server() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 5 ("`rendered_entry(server_id, url,
    variable, client)` builds the entry ... the renderer writes what `rendered_entry` returns")
    and ADR-003 decision 4 ("built from `rendered_entry`"): the entry of each server is the mapping
    of the function, for the id, the address, no variable and the client."""
    text = render_mcp_file((server("one"), server("two")), CLIENT)

    entries = json.loads(text)["mcpServers"]
    assert entries["orqlet-one"] == rendered_entry("one", ATLASSIAN, None, CLIENT)
    assert entries["orqlet-two"] == rendered_entry("two", ATLASSIAN, None, CLIENT)


def test_ac1_the_renderer_writes_what_rendered_entry_returns_for_each_server_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 5 ("The renderer writes what
    `rendered_entry` returns and the validator compares a file with it, so the pin and the output
    cannot drift apart") and ADR-003 decision 4 (`rendered_entry` imported by name into the
    module): a substitute that returns another mapping shows in the text, and it is asked for the
    id, the address, no variable and the client of each server, the servers in the order given."""
    asked: list[tuple[str, str, str | None, str]] = []

    def entry(server_id: str, url: str, variable: str | None, client: str) -> dict[str, object]:
        asked.append((server_id, url, variable, client))
        return {"type": "http", "url": f"https://entry.example.test/{server_id}"}

    monkeypatch.setattr(mcp_module, "rendered_entry", entry)

    text = render_mcp_file((server("one"), server("two")), CLIENT)

    assert list(dict.fromkeys(asked)) == [
        ("one", ATLASSIAN, None, CLIENT),
        ("two", ATLASSIAN, None, CLIENT),
    ]
    assert json.loads(text) == {
        "mcpServers": {
            "orqlet-one": {"type": "http", "url": "https://entry.example.test/one"},
            "orqlet-two": {"type": "http", "url": "https://entry.example.test/two"},
        }
    }


@pytest.mark.parametrize(
    "client", ["codex", "cursor", "vscode", "unknown-client", "", "Claude-Code"]
)
def test_ac1_a_client_that_the_table_does_not_enable_is_refused(client: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 2 (the table enables one row: the
    Atlassian address with `claude-code`) and decision 5 ("`rendered_entry` refuses ... its
    refusal is the second guard"): no text is returned for Codex, Cursor or a client that is not
    known, and a client id is compared as it is written."""
    with pytest.raises(ValueError, match=r".*"):
        render_mcp_file((server(),), client)


def test_ac1_an_address_that_the_table_does_not_enable_is_refused() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 2 ("any other combination is an error")
    and decision 5 (`rendered_entry` refuses): a server at the address of the valid fixture, which
    is a good address for the contract, gets no entry, and no text is written for the others."""
    with pytest.raises(ValueError, match=r".*"):
        render_mcp_file((server("one"), server("two", url=OTHER_ADDRESS)), CLIENT)


def test_ac1_a_server_that_has_no_address_is_refused() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 5 ("a stdio server has no address" and
    "`rendered_entry` never meets an unenabled combination in normal use; its refusal is the
    second guard"): a stdio server that is given by mistake gives no entry with an empty address."""
    stdio = server(
        "tool",
        identity={"kind": "stdio", "command": "tool-server", "package": "tool-server"},
        registered=(),
    )

    with pytest.raises(ValueError, match=r".*"):
        render_mcp_file((stdio,), CLIENT)


def test_ac1_a_server_that_names_a_variable_is_refused_and_the_name_is_not_shown() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 5 ("a variable or any other client or
    address is refused") and decision 9 ("Messages never carry a value"): an `env-ref` server gets
    no entry in this release, and the message does not repeat the name of its variable."""
    name = "ORQLET_MCP_ATLASSIAN_TOKEN"
    data_flow = copy.deepcopy(
        yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["servers"][0]["data_flow"]
    )
    data_flow["backend_identity"] = "user-token"
    with_variable = server(
        auth={"mode": "env-ref", "env_refs": [name]},
        data_flow=data_flow,
    )

    with pytest.raises(ValueError, match=r".*") as caught:
        render_mcp_file((with_variable,), CLIENT)

    assert name not in str(caught.value)


# --- AC-2: the scan of the text that it builds ----------------------------------------------------


def test_ac2_the_scan_sees_the_document_that_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 7 ("The scan of a rendered text runs
    inside `render_mcp_file`") and AC-2 ("scans the text it builds"): the text that the scan gets
    is the whole document that the function returns, for two servers."""
    seen: list[str] = []

    def scan(text: str) -> tuple[CredentialFinding, ...]:
        seen.append(text)
        return ()

    monkeypatch.setattr(mcp_module, "find_literal_credentials", scan)

    text = render_mcp_file((server("one"), server("two")), CLIENT)

    assert seen
    for scanned in seen:
        assert json.loads(scanned) == json.loads(text)
        assert "orqlet-one" in scanned
        assert "orqlet-two" in scanned
        assert ATLASSIAN in scanned


def test_ac2_a_finding_of_the_scan_makes_the_renderer_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("raises when anything is found ... the test forces a
    finding with a substituted scan") and ADR-002 decision 7 ("`render_mcp_file` raises, and the
    run exits 70 with nothing written"): one finding of any rule is enough and no text comes
    back."""
    forced: list[str] = []

    def scan(text: str) -> tuple[CredentialFinding, ...]:
        forced.append(text)
        return (CredentialFinding(line=3, rule="token-prefix"),)

    monkeypatch.setattr(mcp_module, "find_literal_credentials", scan)

    with pytest.raises(ValueError, match=r".*"):
        render_mcp_file((server(),), CLIENT)

    assert forced


def test_ac2_the_message_of_the_refusal_holds_no_value_of_the_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 7 ("a finding there is a defect,
    `render_mcp_file` raises") and decision 9 ("Messages never carry a value or a raw key"):
    the entry that is scanned holds a run-time sentinel in its address, the scan finds something,
    and the message holds neither the sentinel nor the address nor the text."""

    def entry(server_id: str, url: str, variable: str | None, client: str) -> dict[str, object]:
        return {"type": "http", "url": f"https://entry.example.test/{SENTINEL}"}

    def scan(text: str) -> tuple[CredentialFinding, ...]:
        return (CredentialFinding(line=4, rule="credential-key-literal"),)

    monkeypatch.setattr(mcp_module, "rendered_entry", entry)
    monkeypatch.setattr(mcp_module, "find_literal_credentials", scan)

    with pytest.raises(ValueError, match=r".*") as caught:
        render_mcp_file((server(),), CLIENT)

    message = str(caught.value)
    assert message
    assert not leaks(message, SENTINEL)
    assert "entry.example.test" not in message
    assert "mcpServers" not in message


def test_ac2_the_real_scan_refuses_a_credential_in_the_text_that_is_built(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 7 (the scan runs "on each rendered text
    before it is written") with the scan of the domain left as it is: an entry that holds a token
    in its address is refused by the function, whose message holds no part of the token."""

    def entry(server_id: str, url: str, variable: str | None, client: str) -> dict[str, object]:
        return {"type": "http", "url": f"https://entry.example.test/{TOKEN}"}

    monkeypatch.setattr(mcp_module, "rendered_entry", entry)

    with pytest.raises(ValueError, match=r".*") as caught:
        render_mcp_file((server(),), CLIENT)

    assert not leaks(str(caught.value), TOKEN)
    assert str(caught.value)


def test_ac2_a_scan_that_finds_nothing_lets_the_text_through_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 7 (the entry has no credential field, so a
    finding is a defect and the normal case has none): with the scan substituted by one that finds
    nothing, the text is the text of the specification: the scan only decides whether to raise."""
    monkeypatch.setattr(mcp_module, "find_literal_credentials", lambda _text: ())

    assert render_mcp_file((server(),), CLIENT) == ATLASSIAN_TEXT


def test_ac2_the_text_of_the_one_enabled_entry_has_no_finding_of_the_real_scan() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 7 ("the entry has no credential field, so
    a finding there is a defect") with the real scan, for one and for several servers: the one
    entry that this release builds is never refused by the scan."""
    for servers in (
        (server(),),
        (server("one"), server("two"), server("three")),
        (server("token"), server("secret"), server("password")),
    ):
        assert render_mcp_file(servers, CLIENT)
