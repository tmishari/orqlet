"""The scan of the committed check records (task mcp-or-plugins, phase P-8).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-004 are the files `adr-002-*.md`
and `adr-004-*.md` under docs/design/mcp-or-plugins/design/, and AC-3 is an acceptance criterion of
phase P-8 in docs/design/mcp-or-plugins/plan.yaml. A check record is a file under
docs/design/mcp-or-plugins/evidence/checks (ADR-004 decision 1); the folder does not exist until a
person writes the first record, and the scan passes when it is absent.

The scan is a small function of text, defined here, with three checks (ADR-004 decision 1):
- credential shapes, with `find_literal_credentials` of the domain module (ADR-002 decision 7);
- an at-sign address: a local part, an at sign and a dotted domain whose last label is letters
  (so a version such as `claude-code@2.1.0` and a package scope such as `@anthropic-ai/pkg` are not
  addresses);
- a host that ends in `.atlassian.net`, in any letter case, with a label before the dot.

A failure names the file and the checks that failed, never the text that matched. A file that is not
valid UTF-8 cannot be scanned and fails closed (ADR-002 decision 8: an unreadable file is an error).

Credential shapes, at-sign addresses and Atlassian hosts are assembled from parts at run time and
never written as one literal (ORQLET-SEC-003). The tests of the helper use `tmp_path` and never
create the folder of the records or a record.

Behaviour that the design leaves open is deliberately not pinned here:
- the name of a record (`V-<n>-<client>.md`) and its sections: the scan reads every file;
- whether a placeholder such as `<site>` before `.atlassian.net` counts as a host: it is not a host
  here, because no label stands before the dot;
- the rules "no account name" and "no private server address", which ADR-004 decision 1 leaves to
  review.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from orqlet.domain.mcp_credentials import find_literal_credentials

pytestmark = pytest.mark.unit

CHECKS = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "design"
    / "mcp-or-plugins"
    / "evidence"
    / "checks"
)

CREDENTIAL = "credential-shape"
ADDRESS = "at-sign-address"
HOST = "atlassian-net-host"
NOT_UTF8 = "not-utf-8"

# The lookbehind keeps a long run of word characters from being retried at every position.
AT_ADDRESS = re.compile(
    r"(?<![\w.%+-])[\w.%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![A-Za-z0-9-])"
)
ATLASSIAN_HOST = re.compile(r"[A-Za-z0-9-]\.atlassian\.net(?![A-Za-z0-9-])", re.IGNORECASE)


def problems_in(text: str) -> tuple[str, ...]:
    """The names of the checks that a record text fails, from a closed set, never a value."""
    found: list[str] = []
    if find_literal_credentials(text):
        found.append(CREDENTIAL)
    if AT_ADDRESS.search(text):
        found.append(ADDRESS)
    if ATLASSIAN_HOST.search(text):
        found.append(HOST)
    return tuple(found)


def scan_folder(folder: Path) -> dict[str, tuple[str, ...]]:
    """The failing files under a folder, by path relative to it. An absent folder has none."""
    failures: dict[str, tuple[str, ...]] = {}
    if not folder.is_dir():
        return failures
    for path in sorted(item for item in folder.rglob("*") if item.is_file()):
        relative = path.relative_to(folder).as_posix()
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            failures[relative] = (NOT_UTF8,)
            continue
        found = problems_in(text)
        if found:
            failures[relative] = found
    return failures


# --- what a good record looks like ---------------------------------------------------------------

GOOD_RECORDS: dict[str, str] = {
    "the layout of ADR-004 decision 1": (
        "# V-1, Claude Code\n"
        "\n"
        "Date: 2026-11-02\n"
        "Client: Claude Code 2.1.0, as printed by its version command\n"
        "Test account: a throwaway account of a test organisation, smallest scopes\n"
        "\n"
        "## Steps\n"
        "\n"
        "1. Opened a throwaway repository whose `.mcp.json` holds the one generated entry.\n"
        "2. Started an interactive session and listed the servers.\n"
        "\n"
        "## Observed result\n"
        "\n"
        "The client asked for approval before it connected to the project server.\n"
        "\n"
        "## Verdict\n"
        "\n"
        "Approval is asked in an interactive session. Not checked: a `claude -p` run.\n"
    ),
    "versions and package scopes that hold an at sign but no address": (
        "# V-9, Claude Code\n"
        "\n"
        "Client: claude-code@2.1.0 (package `@anthropic-ai/claude-code`)\n"
        "Tool: orqlet@v0.1.0 installed with `uv tool install`\n"
        "Pinned in the workflow as `actions/checkout@v7`.\n"
        "The reader accepted a duplicate key; the validator refuses it.\n"
    ),
    "the vendor address and a table": (
        "# V-5, Claude Code\n"
        "\n"
        "| Item | Result |\n"
        "|---|---|\n"
        "| Address of the server | https://mcp.atlassian.com/v2/mcp |\n"
        "| File mode of the store | 0600 |\n"
        "| Key names inspected, never values | yes |\n"
        "\n"
        "The sign-in was revoked after the check.\n"
    ),
    "a not-run verdict": (
        "# V-10, Claude Code\n\nNot run on a cloud agent: no throwaway repository was available.\n"
    ),
}


def body(size: int) -> str:
    """A deterministic alphanumeric run of `size` characters."""
    return ("aB3" * size)[:size]


def credential_shapes() -> dict[str, str]:
    """One credential-shaped line per rule family of ADR-002 decision 7, built from parts."""
    return {
        "github-token": "gh" + "p_" + body(36),
        "github-fine-grained": "github" + "_pat_" + body(22) + "_" + body(59),
        "atlassian-prefix": "AT" + "ATT" + "3" + body(120),
        "anthropic-key": "sk" + "-ant-" + "api03-" + body(93),
        "aws-key": "AK" + "IA" + "B3C4D5E6F7G8H9J2",
        "slack-token": "xo" + "xb-" + "123456789012-123456789012-" + body(24),
        "jwt": ".".join(
            ("ey" + "J" + "hbGciOiJIUzI1NiJ9", "ey" + "J" + "zdWIiOiJ0ZXN0In0", body(43))
        ),
        "header-value": "Authorization" + ": " + "Bearer " + body(30) + "9",
        "credential-key": '"api' + 'Key": "' + body(24) + '"',
        "query-parameter": "https://mcp.example.com/mcp?" + "api" + "_key=" + body(20),
        "oversize-line": "x" * 5000,
    }


def addresses() -> dict[str, str]:
    return {
        "plain": "qa.tester" + "@" + "example" + ".org",
        "plus-tag": "qa+v1" + "@" + "mail-test" + ".example" + ".io",
        "upper-case": ("QA.TESTER" + "@" + "EXAMPLE" + ".ORG"),
        "in-brackets": "<" + "tester" + "@" + "example" + ".com" + ">",
    }


def atlassian_hosts() -> dict[str, str]:
    host = "acme" + "." + "atlassian" + "." + "net"
    return {
        "bare": host,
        "url": "https://" + host + "/wiki/spaces/ABC",
        "port": host + ":443",
        "upper-case": host.upper(),
        "deeper": "a.b" + "." + "atlassian" + "." + "net",
    }


def with_extra_line(record: str, line: str) -> str:
    return record + "\n" + line + "\n"


# --- the scan is sound ---------------------------------------------------------------------------


@pytest.mark.parametrize("record", list(GOOD_RECORDS.values()), ids=list(GOOD_RECORDS))
def test_a_good_sample_record_passes_the_scan(record: str) -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 (a check record has the date, the client
    name and version, the kind of test account, the steps, the observed result and a verdict, and
    holds no credential, account name, raw log or private address; a record that obeys passes).
    It passes before any record exists."""
    assert problems_in(record) == ()


@pytest.mark.parametrize("kind", sorted(credential_shapes()))
def test_the_scan_fails_on_a_record_that_holds_a_credential_shape(kind: str) -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 (a repository test runs the credential
    scan of ADR-002 decision 7 over every committed check record) and AC-3 (the scan fails on a
    record that holds a credential shape). The shape is assembled at run time (ORQLET-SEC-003)."""
    for name, record in GOOD_RECORDS.items():
        assert problems_in(with_extra_line(record, credential_shapes()[kind])) == (CREDENTIAL,), (
            name
        )


def test_the_scan_fails_on_a_credential_in_the_user_information_of_an_address() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 7 (user information in a URL is a credential
    shape) and ADR-004 decision 1. The line also holds an at sign, so both checks fail."""
    line = "https://" + "svc" + ":" + body(12) + "@" + "mcp.example.com" + "/mcp"

    found = problems_in(with_extra_line(GOOD_RECORDS["a not-run verdict"], line))

    assert set(found) == {CREDENTIAL, ADDRESS}


@pytest.mark.parametrize("kind", sorted(addresses()))
def test_the_scan_fails_on_a_record_that_holds_an_at_sign_address(kind: str) -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 (the test also looks for an `@` address)
    and AC-3 (the scan fails on a record that holds an at-sign address). The address is assembled at
    run time (ORQLET-SEC-003)."""
    for name, record in GOOD_RECORDS.items():
        assert problems_in(with_extra_line(record, f"Signed in as {addresses()[kind]}")) == (
            ADDRESS,
        ), name


@pytest.mark.parametrize("kind", sorted(atlassian_hosts()))
def test_the_scan_fails_on_a_record_that_holds_an_atlassian_net_host(kind: str) -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 (the test also looks for a host ending in
    `.atlassian.net`) and AC-3 (the scan fails on a record that holds a `.atlassian.net` host). The
    host is assembled at run time (ORQLET-SEC-003)."""
    for name, record in GOOD_RECORDS.items():
        assert problems_in(with_extra_line(record, f"Site: {atlassian_hosts()[kind]}")) == (
            HOST,
        ), name


def test_the_scan_names_every_check_that_a_record_fails() -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 (the three searches are independent) and
    AC-3 (fails on a credential shape, an at-sign address or a `.atlassian.net` host)."""
    record = GOOD_RECORDS["a not-run verdict"]
    for line in (
        credential_shapes()["github-token"],
        addresses()["plain"],
        atlassian_hosts()["bare"],
    ):
        record = with_extra_line(record, line)

    assert problems_in(record) == (CREDENTIAL, ADDRESS, HOST)


def test_the_answer_of_the_scan_never_holds_the_text_that_matched() -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 (a record holds no credential value,
    account name or private address, so a failure must not copy one into a log) and ADR-002
    decision 9 (messages never carry a value)."""
    lines = [
        credential_shapes()["github-token"],
        addresses()["plain"],
        atlassian_hosts()["bare"],
    ]
    record = "\n".join(lines)

    shown = " ".join(problems_in(record))

    assert shown == f"{CREDENTIAL} {ADDRESS} {HOST}"
    assert not any(line in shown for line in lines)


# --- the folder ----------------------------------------------------------------------------------


def test_a_folder_that_is_absent_or_empty_has_no_failure(tmp_path: Path) -> None:
    """AC-3. expected_behavior_source: AC-3 ("passes with no record present") and ADR-004 decision 1
    (the records are written by a person later, so the folder does not exist yet)."""
    empty = tmp_path / "checks"
    empty.mkdir()

    assert scan_folder(tmp_path / "absent") == {}
    assert scan_folder(empty) == {}


def test_every_file_of_the_folder_is_scanned_nested_ones_too(tmp_path: Path) -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 ("over every committed check record") and
    plan P-8 file list ("over every file under docs/design/mcp-or-plugins/evidence/checks")."""
    nested = tmp_path / "later" / "deeper"
    nested.mkdir(parents=True)
    for number, record in enumerate(GOOD_RECORDS.values(), start=1):
        (tmp_path / f"V-{number}-claude-code.md").write_text(record, encoding="utf-8")
    (nested / "bad.md").write_text(
        with_extra_line(GOOD_RECORDS["a not-run verdict"], addresses()["plain"]), encoding="utf-8"
    )
    (tmp_path / "bad-credential.txt").write_text(credential_shapes()["aws-key"], encoding="utf-8")

    assert scan_folder(tmp_path) == {
        "later/deeper/bad.md": (ADDRESS,),
        "bad-credential.txt": (CREDENTIAL,),
    }


def test_a_file_that_is_not_utf_8_cannot_be_scanned_and_fails(tmp_path: Path) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 8 (a file that is not valid UTF-8 is an
    error, not a pass) applied to ADR-004 decision 1 (every committed record is scanned)."""
    (tmp_path / "V-1-claude-code.md").write_bytes(b"# V-1\n\xff\xfe not text\n")

    assert scan_folder(tmp_path) == {"V-1-claude-code.md": (NOT_UTF8,)}


def test_a_folder_of_good_samples_has_no_failure(tmp_path: Path) -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 (a record that obeys its rules passes)."""
    for number, record in enumerate(GOOD_RECORDS.values(), start=1):
        (tmp_path / f"V-{number}-claude-code.md").write_text(record, encoding="utf-8")

    assert scan_folder(tmp_path) == {}


def test_no_committed_check_record_holds_a_credential_an_address_or_an_atlassian_host() -> None:
    """AC-3. expected_behavior_source: ADR-004 decision 1 ("A repository test runs the credential
    scan of ADR-002 decision 7 over every committed check record, and also looks for an `@` address
    and a host ending in `.atlassian.net`") and AC-3 (passes with no record present). It reports
    the file and the check, never the text."""
    assert scan_folder(CHECKS) == {}
