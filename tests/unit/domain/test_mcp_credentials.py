"""MCP credentials: the pure domain rules (task mcp-or-plugins, phase P-1).

Every test cites its `expected_behavior_source`. ADR-002 is
docs/design/mcp-or-plugins/design/adr-002-one-credential-per-user.md, ADR-003 is
docs/design/mcp-or-plugins/design/adr-003-build-order-and-seeded-files.md, and AC-1 to AC-7 are the
acceptance criteria of phase P-1 in docs/design/mcp-or-plugins/plan.yaml.

These tests were written first, by the Tester of phase P-1, before `orqlet.domain.mcp_credentials`
existed. The section "rework round 1" at the end was added after the first review.

Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003). The module under test is pure and takes plain values, so no port is involved
and no fake from tests/fakes applies (ORQLET-TEST-001).

Behaviour that the design leaves open is deliberately not pinned here:
- the exact rule names of `name_problems` and `find_literal_credentials` (only empty versus
  non-empty tuples, line numbers and non-empty names are checked; `oversize` is the one named
  rule, ADR-002 decision 7);
- the exception type with which `rendered_entry` and `mcp_file_path` refuse input;
- the attribute names of `CredentialFinding` (it is read by type: one int, one str) and whether
  its line numbers start at 0 or 1 (the tests learn the base once and then require it to be used
  consistently);
- the order and the repetition of the names that `referenced_variables` and `entry_differences`
  return, and when `entry_differences` returns `entry`;
- letter case of credential-named keys and query names, and the minimum length of a token body.
"""

import ast
import base64
import dataclasses
import functools
import inspect
from collections.abc import Callable

import pytest

from orqlet.domain import mcp_credentials
from orqlet.domain.mcp_credentials import (
    CredentialFinding,
    allowed_auth_modes,
    entry_differences,
    find_literal_credentials,
    mcp_file_path,
    name_problems,
    referenced_variables,
    rendered_entry,
)

pytestmark = pytest.mark.unit

# --- values that the sources state ---------------------------------------------------------------

ATLASSIAN_URL = "https://mcp.atlassian.com/v2/mcp"  # ADR-002 decision 2 and 12
GITHUB_URL = "https://api.githubcopilot.com/mcp/"  # ADR-002 decision 12
OAUTH = "client-native-oauth"
CLAUDE_CODE = "claude-code"
OTHER_CLIENTS = ("cursor", "codex")
VALID_ID = "atlassian"
VALID_VARIABLE = "ORQLET_MCP_ATLASSIAN_TOKEN"
OVERSIZE = "oversize"  # ADR-002 decision 7: the one rule name that the design fixes
MAX_LINE = 4096  # ADR-002 decision 7
VOCABULARY = frozenset({"type", "url", "headers", "bearer_token_env_var", "entry", "unknown-key"})

LITERAL = "literal-value-4f2a"  # a plain word, not shaped like any credential
BENIGN_LINE = '  "type": "http",'
RENDERED_FILE_TEXT = (
    "{\n"
    '  "mcpServers": {\n'
    '    "orqlet-atlassian": {\n'
    '      "type": "http",\n'
    f'      "url": "{ATLASSIAN_URL}"\n'
    "    }\n"
    "  }\n"
    "}\n"
)  # the shape of ADR-003 decision 6 for the one generated entry

Arguments = tuple[str, str, str | None, str]

# --- builders (shared with the property tests) ---------------------------------------------------


def body(size: int) -> str:
    """A deterministic alphanumeric run of `size` characters."""
    return ("aB3" * size)[:size]


EYJ = "ey" + "J"  # the start of a JWT header; split so that no token-like literal exists


def token_shapes() -> dict[str, str]:
    """One string per prefix of ADR-002 decision 7, built from parts and with a realistic length."""
    shapes = {
        f"github-{kind}": kind + "_" + body(36) for kind in ("ghp", "gho", "ghu", "ghs", "ghr")
    }
    shapes["github-fine-grained"] = "github" + "_pat_" + body(22) + "_" + body(59)
    shapes["atlassian"] = "AT" + "ATT" + "3" + body(120)
    shapes["anthropic"] = "sk" + "-ant-" + "api03-" + body(93)
    shapes["aws"] = "AK" + "IA" + "B3C4D5E6F7G8H9J2"
    shapes["slack-bot"] = "xo" + "xb-" + "123456789012-123456789012-" + body(24)
    shapes["slack-user"] = "xo" + "xp-" + "123456789012-123456789012-" + body(24)
    return shapes


def jwt_shape() -> str:
    """Three base64url sections joined by dots, the first starting with the JWT header prefix."""
    return ".".join((EYJ + "hbGciOiJIUzI1NiJ9", EYJ + "zdWIiOiJ0ZXN0In0", body(43)))


SHAPES = token_shapes()
BASIC_VALUE = base64.b64encode(b"user:pw").decode("ascii")


def document_with(line: str, *, before: int = 2) -> str:
    """A text of benign lines with `line` after `before` of them and one more benign line after."""
    return "\n".join([*([BENIGN_LINE] * before), line, BENIGN_LINE, ""])


def finding_line(finding: CredentialFinding) -> int:
    """The line number of a finding, found by type because the field name is not fixed."""
    numbers = [
        value
        for value in (getattr(finding, field.name) for field in dataclasses.fields(finding))
        if isinstance(value, int) and not isinstance(value, bool)
    ]
    assert len(numbers) == 1
    return numbers[0]


def finding_rule(finding: CredentialFinding) -> str:
    """The rule name of a finding, found by type because the field name is not fixed."""
    names = [
        value
        for value in (getattr(finding, field.name) for field in dataclasses.fields(finding))
        if isinstance(value, str)
    ]
    assert len(names) == 1
    return names[0]


def flagged_lines(text: str) -> set[int]:
    return {finding_line(finding) for finding in find_literal_credentials(text)}


@functools.cache
def numbering_base() -> int:
    """The number of the first line (0 or 1), learned once from a text with one flagged line."""
    findings = find_literal_credentials(SHAPES["github-ghp"])
    assert findings
    return finding_line(findings[0])


def shown_by(findings: tuple[CredentialFinding, ...]) -> str:
    """Everything that findings show: field values, text form and repr, in lower case."""
    return " ".join(
        f"{finding!s} {finding!r} {dataclasses.astuple(finding)}" for finding in findings
    ).lower()


def holds_any(shown: str, *secrets: str) -> bool:
    return any(secret.lower() in shown.lower() for secret in secrets)


def refusal_text(call: Callable[[], object]) -> str:
    """Call `call`, require that it refuses, and return everything its exceptions show.

    The design leaves the exception type open (plan.yaml `unverified`), so any Exception counts.
    """
    with pytest.raises(Exception) as raised:  # noqa: PT011
        call()
    texts: list[str] = []
    error: BaseException | None = raised.value
    while error is not None:
        texts += [str(error), repr(error), *map(str, error.args)]
        error = error.__cause__ or error.__context__
    return " ".join(texts)


# --- AC-1: name_problems -------------------------------------------------------------------------

VALID_IDS = ["a", "atlassian", "a-b", "a1", "a-1-b", "a" + "b" * 31]  # the last has 32 characters
BROKEN_IDS = {
    "empty": "",
    "upper-case": "Atlassian",
    "all-upper-case": "ATLASSIAN",
    "starts-with-digit": "1atlassian",
    "starts-with-hyphen": "-atlassian",
    "underscore": "atlas_sian",
    "space": "atlas sian",
    "dot": "atlas.sian",
    "slash": "atlas/sian",
    "thirty-three-characters": "a" * 33,
    "trailing-newline": "atlassian\n",
    "leading-newline": "\natlassian",
    "kelvin-sign": "\u212a",
    "kelvin-sign-inside": "atlas\u212asian",
    "accented-letter": "caf\u00e9",
    "fullwidth-letter": "\uff41tlassian",
    "arabic-indic-digit": "a\u0661",
}

VALID_VARIABLES = [
    "ORQLET_MCP_A",
    "ORQLET_MCP_ATLASSIAN",
    "ORQLET_MCP_GITHUB_TOKEN",
    "ORQLET_MCP_A1_B2",
    "ORQLET_MCP_" + "A" * 37,  # 48 characters
]
BROKEN_VARIABLES = {
    "empty": "",
    "no-prefix": "GITHUB_TOKEN",
    "other-orqlet-name": "ORQLET_DATA_DIR",
    "lower-case": "orqlet_mcp_github",
    "lower-case-tail": "ORQLET_MCP_Github",
    "prefix-only": "ORQLET_MCP_",
    "digit-first": "ORQLET_MCP_1A",
    "double-underscore-after-prefix": "ORQLET_MCP__A",
    "double-underscore-inside": "ORQLET_MCP_A__B",
    "trailing-underscore": "ORQLET_MCP_A_",
    "segment-starts-with-digit": "ORQLET_MCP_A_1B",
    "hyphen": "ORQLET_MCP_A-B",
    "forty-nine-characters": "ORQLET_MCP_" + "A" * 38,
    "trailing-newline": VALID_VARIABLE + "\n",
    "leading-space": " " + VALID_VARIABLE,
    "reference-syntax": "${" + VALID_VARIABLE + "}",
    "kelvin-sign": "ORQLET_MCP_\u212a",
    "kelvin-sign-inside": "ORQLET_MCP_A\u212aB",
    "accented-letter": "ORQLET_MCP_\u00c9",
}


def github_user_info_url() -> str:
    """An address whose user information is a token-shaped string, built at run time."""
    return "https://" + SHAPES["github-ghp"] + "@docs.example.com/mcp"


VALID_URLS = [ATLASSIAN_URL, GITHUB_URL, "https://docs.example.com/mcp"]
BROKEN_URLS = {
    "empty": "",
    "plain-http": "http://docs.example.com/mcp",
    "other-scheme": "ftp://docs.example.com/mcp",
    "no-scheme": "docs.example.com/mcp",
    "scheme-relative": "//docs.example.com/mcp",
    "user-information": "https://someone@docs.example.com/mcp",
    "user-and-password": "https://someone:pw@docs.example.com/mcp",
    "token-as-user-information": github_user_info_url(),
    "query": "https://docs.example.com/mcp?page=2",
    "empty-query": "https://docs.example.com/mcp?",
    "fragment": "https://docs.example.com/mcp#top",
    "variable-in-host": "https://${HOST}/mcp",
    "variable-in-path": "https://docs.example.com/${PATH_PART}",
    "backslash": "https://docs.example.com\\mcp",
    "percent-encoded-letter": "https://docs.example.com/%41",
    "percent-encoded-slash-lower-case": "https://docs.example.com/a%2fb",
    "trailing-newline": "https://docs.example.com/mcp\n",
    "accented-host": "https://d\u00f6cs.example.com/mcp",
    "kelvin-sign-in-host": "https://\u212a.example.com/mcp",
}


@pytest.mark.parametrize("server_id", VALID_IDS)
def test_an_id_that_fullmatches_the_pattern_has_no_problem(server_id: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (`^[a-z][a-z0-9-]{0,31}$`)."""
    assert name_problems(server_id, ATLASSIAN_URL, None) == ()


@pytest.mark.parametrize("server_id", list(BROKEN_IDS.values()), ids=list(BROKEN_IDS))
def test_an_id_that_breaks_the_pattern_is_a_problem(server_id: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (fullmatch, re.ASCII, no IGNORECASE).

    The trailing newline and U+212A are the two cases that the criterion names.
    """
    assert name_problems(server_id, ATLASSIAN_URL, None)


@pytest.mark.parametrize("variable", VALID_VARIABLES)
def test_a_variable_that_fullmatches_the_pattern_has_no_problem(variable: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (pattern and at most 48 characters)."""
    assert name_problems(VALID_ID, ATLASSIAN_URL, variable) == ()


@pytest.mark.parametrize("variable", list(BROKEN_VARIABLES.values()), ids=list(BROKEN_VARIABLES))
def test_a_variable_that_breaks_the_pattern_is_a_problem(variable: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (fullmatch, re.ASCII, no IGNORECASE)."""
    assert name_problems(VALID_ID, ATLASSIAN_URL, variable)


def test_no_variable_is_not_a_problem() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 ("a variable, when given")."""
    assert name_problems(VALID_ID, ATLASSIAN_URL, None) == ()


@pytest.mark.parametrize("url", VALID_URLS)
def test_a_literal_https_address_has_no_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 (a literal https address).

    The closed table of addresses is a separate check (`allowed_auth_modes`), not a name rule.
    """
    assert name_problems(VALID_ID, url, None) == ()


@pytest.mark.parametrize("url", list(BROKEN_URLS.values()), ids=list(BROKEN_URLS))
def test_an_address_that_is_not_a_plain_literal_https_address_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 (https; no user information, query,
    fragment, `${`, backslash or percent-encoding) and decision 3 (ASCII only, fullmatch)."""
    assert name_problems(VALID_ID, url, None)


def test_valid_values_for_all_three_give_an_empty_tuple() -> None:
    """AC-1. expected_behavior_source: ADR-002 decisions 3 and 4 (an empty tuple when none)."""
    assert name_problems(VALID_ID, ATLASSIAN_URL, VALID_VARIABLE) == ()


def test_the_problems_are_a_tuple_of_non_empty_rule_names() -> None:
    """AC-1. expected_behavior_source: AC-1 ("returns the names of the rules ... a tuple")."""
    problems = name_problems("Bad Id", "http://docs.example.com/mcp?x=1", "bad")

    assert isinstance(problems, tuple)
    assert problems
    assert all(isinstance(name, str) and name for name in problems)


def test_every_rule_that_one_value_breaks_is_named_when_all_three_are_broken() -> None:
    """AC-1. expected_behavior_source: AC-1 ("the names of the rules that the three values
    break")."""
    broken_id, broken_url, broken_variable = "Bad Id", "http://docs.example.com/mcp", "bad"
    alone = (
        set(name_problems(broken_id, ATLASSIAN_URL, None))
        | set(name_problems(VALID_ID, broken_url, None))
        | set(name_problems(VALID_ID, ATLASSIAN_URL, broken_variable))
    )

    assert alone
    assert alone <= set(name_problems(broken_id, broken_url, broken_variable))


def test_no_rule_name_contains_an_input_value() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 9 (messages never carry a value) and AC-1
    ("no returned text contains an input value")."""
    id_marker = "zq7-marker-id-91c2"
    url_marker = "zq7-marker-url-5d1e"
    variable_marker = "zq7_var_3b8a"
    problems = name_problems(
        "Zq7-Marker-Id-91c2",
        "https://" + url_marker + ".example.com/mcp?x=1",
        variable_marker,
    )

    assert problems
    assert not holds_any(" ".join(problems), id_marker, url_marker, variable_marker)


def test_a_credential_shaped_value_is_never_named_in_a_problem() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 9 and ORQLET-SEC-003."""
    token = SHAPES["github-ghp"]

    problems = name_problems(token, github_user_info_url(), token)

    assert problems
    assert not holds_any(" ".join(problems), token, token[-20:])


# --- AC-2: allowed_auth_modes --------------------------------------------------------------------

OTHER_ADDRESSES = {
    "trailing-slash": ATLASSIAN_URL + "/",
    "upper-case-host": "https://MCP.ATLASSIAN.COM/v2/mcp",
    "upper-case-path": "https://mcp.atlassian.com/V2/MCP",
    "upper-case-scheme": "HTTPS://mcp.atlassian.com/v2/mcp",
    "query": ATLASSIAN_URL + "?x=1",
    "fragment": ATLASSIAN_URL + "#top",
    "trailing-newline": ATLASSIAN_URL + "\n",
    "leading-space": " " + ATLASSIAN_URL,
    "plain-http": "http://mcp.atlassian.com/v2/mcp",
    "other-version": "https://mcp.atlassian.com/v1/mcp",
    "github": GITHUB_URL,
    "github-without-slash": GITHUB_URL.rstrip("/"),
    "other-host": "https://docs.example.com/mcp",
    "empty": "",
}
OTHER_CLIENT_NAMES = [*OTHER_CLIENTS, "", "Claude-Code", "CLAUDE-CODE", "claude-code ", "unknown"]


def test_the_atlassian_address_with_claude_code_enables_oauth_only() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 2 (the one enabled row)."""
    assert allowed_auth_modes(ATLASSIAN_URL, CLAUDE_CODE) == (OAUTH,)


@pytest.mark.parametrize("url", list(OTHER_ADDRESSES.values()), ids=list(OTHER_ADDRESSES))
def test_any_other_address_with_claude_code_enables_nothing(url: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 2 (exactly the one address)."""
    assert allowed_auth_modes(url, CLAUDE_CODE) == ()


@pytest.mark.parametrize("client", OTHER_CLIENT_NAMES)
@pytest.mark.parametrize("url", [ATLASSIAN_URL, GITHUB_URL])
def test_any_other_client_enables_nothing_for_any_address(url: str, client: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 2 (Codex and Cursor wait for a later
    release; every other client is outside the table)."""
    assert allowed_auth_modes(url, client) == ()


# --- AC-3: rendered_entry and mcp_file_path ------------------------------------------------------


@pytest.mark.parametrize("server_id", [VALID_ID, "a", "docs-2"])
def test_the_atlassian_oauth_entry_for_claude_code_has_type_and_url_in_that_order(
    server_id: str,
) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 and ADR-003 decision 6."""
    entry = rendered_entry(server_id, ATLASSIAN_URL, None, CLAUDE_CODE)

    assert isinstance(entry, dict)
    assert list(entry) == ["type", "url"]
    assert entry == {"type": "http", "url": ATLASSIAN_URL}


def test_the_entry_is_the_same_on_every_call() -> None:
    """AC-3. expected_behavior_source: ORQLET-DET-001 (component view: each function is
    deterministic on its inputs)."""
    first = rendered_entry(VALID_ID, ATLASSIAN_URL, None, CLAUDE_CODE)

    assert rendered_entry(VALID_ID, ATLASSIAN_URL, None, CLAUDE_CODE) == first
    assert list(rendered_entry(VALID_ID, ATLASSIAN_URL, None, CLAUDE_CODE)) == list(first)


REFUSED: dict[str, Arguments] = {
    "a-variable": (VALID_ID, ATLASSIAN_URL, VALID_VARIABLE, CLAUDE_CODE),
    "cursor": (VALID_ID, ATLASSIAN_URL, None, "cursor"),
    "codex": (VALID_ID, ATLASSIAN_URL, None, "codex"),
    "empty-client": (VALID_ID, ATLASSIAN_URL, None, ""),
    "unknown-client": (VALID_ID, ATLASSIAN_URL, None, "unknown"),
    "github-address": (VALID_ID, GITHUB_URL, None, CLAUDE_CODE),
    "trailing-slash": (VALID_ID, ATLASSIAN_URL + "/", None, CLAUDE_CODE),
    "other-address": (VALID_ID, "https://docs.example.com/mcp", None, CLAUDE_CODE),
    "empty-address": (VALID_ID, "", None, CLAUDE_CODE),
    "upper-case-id": ("Atlassian", ATLASSIAN_URL, None, CLAUDE_CODE),
    "empty-id": ("", ATLASSIAN_URL, None, CLAUDE_CODE),
    "long-id": ("a" * 33, ATLASSIAN_URL, None, CLAUDE_CODE),
    "id-with-trailing-newline": ("atlassian\n", ATLASSIAN_URL, None, CLAUDE_CODE),
    "id-with-kelvin-sign": ("\u212a", ATLASSIAN_URL, None, CLAUDE_CODE),
    "malformed-variable": (VALID_ID, ATLASSIAN_URL, "lower_case", CLAUDE_CODE),
}
NAME_PROBLEM_CASES = [
    "upper-case-id",
    "empty-id",
    "long-id",
    "id-with-trailing-newline",
    "id-with-kelvin-sign",
    "malformed-variable",
]


@pytest.mark.parametrize("arguments", list(REFUSED.values()), ids=list(REFUSED))
def test_any_other_combination_is_refused(arguments: Arguments) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 5 (the only combination built is Atlassian
    OAuth for Claude Code; a variable or any other client or address is refused)."""
    refusal_text(lambda: rendered_entry(*arguments))


@pytest.mark.parametrize("name", NAME_PROBLEM_CASES)
def test_a_value_for_which_name_problems_reports_a_rule_is_refused(name: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("any value for which name_problems reports a
    rule"); ADR-002 decision 5."""
    arguments = REFUSED[name]

    assert name_problems(arguments[0], arguments[1], arguments[2])
    refusal_text(lambda: rendered_entry(*arguments))


def refusal_cases() -> dict[str, tuple[Arguments, str]]:
    """Each input position with a distinctive marker, and two with a credential-shaped text."""
    token = SHAPES["github-ghp"]
    return {
        "id": (("Zq7-Marker-Id-91c2", ATLASSIAN_URL, None, CLAUDE_CODE), "zq7-marker-id-91c2"),
        "address": (
            (VALID_ID, "https://zq7-marker-url-5d1e.example.com/mcp", None, CLAUDE_CODE),
            "zq7-marker-url-5d1e",
        ),
        "variable": (
            (VALID_ID, ATLASSIAN_URL, "ORQLET_MCP_ZQ7MARKERVAR3B8A", CLAUDE_CODE),
            "zq7markervar3b8a",
        ),
        "client": (
            (VALID_ID, ATLASSIAN_URL, None, "zq7-marker-client-0e6f"),
            "zq7-marker-client-0e6f",
        ),
        "credential-in-address": (
            (VALID_ID, "https://" + token + "@docs.example.com/mcp", None, CLAUDE_CODE),
            token,
        ),
        "credential-as-id": ((token, ATLASSIAN_URL, None, CLAUDE_CODE), token),
    }


REFUSAL_CASES = refusal_cases()


@pytest.mark.parametrize(
    ("arguments", "secret"), list(REFUSAL_CASES.values()), ids=list(REFUSAL_CASES)
)
def test_the_refusal_text_holds_no_input_value(arguments: Arguments, secret: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("the refusal text holds no input value");
    ADR-002 decision 9."""
    text = refusal_text(lambda: rendered_entry(*arguments))

    assert not holds_any(text, secret)


@pytest.mark.parametrize(
    ("client", "path"),
    [(CLAUDE_CODE, ".mcp.json"), ("cursor", ".cursor/mcp.json"), ("codex", ".codex/config.toml")],
)
def test_each_client_has_its_own_mcp_file_path(client: str, path: str) -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 6 and decision 2 (the three seeded files);
    ADR-002 decision 5 (`mcp_file_path` gives the path of a client's file)."""
    assert mcp_file_path(client) == path


def test_an_unknown_client_has_no_file_path_and_is_not_echoed() -> None:
    """AC-3. expected_behavior_source: the tester brief of phase P-1 (mcp_file_path refuses
    input). AC-3 does not say how an unknown client is treated; the plan lists the refusal type as
    unverified and the implementation refuses with a ValueError."""
    text = refusal_text(lambda: mcp_file_path("zq7-marker-client-0e6f"))

    assert not holds_any(text, "zq7-marker-client-0e6f")


# --- AC-4: find_literal_credentials --------------------------------------------------------------

CONTEXTS = {
    "bare": "{value}",
    "json-value": '  "note": "{value}",',
    "toml-value": 'note = "{value}"',
    "yaml-value": "note: {value}",
    "in-prose": "see {value} for the details",
}


def in_context(context: str, value: str) -> str:
    return CONTEXTS[context].format(value=value)


def assert_flagged_only_on_line(text: str, index: int) -> None:
    """The text has findings and every one is on the line at zero-based position `index`."""
    findings = find_literal_credentials(text)

    assert findings
    assert {finding_line(finding) for finding in findings} == {index + numbering_base()}


def test_the_findings_are_a_tuple_of_credential_findings() -> None:
    """AC-4. expected_behavior_source: AC-4 and EC-2 (`-> tuple[CredentialFinding, ...]`)."""
    findings = find_literal_credentials(document_with(SHAPES["github-ghp"]))

    assert isinstance(findings, tuple)
    assert findings
    assert all(isinstance(finding, CredentialFinding) for finding in findings)


def test_a_finding_is_a_frozen_dataclass_of_a_line_number_and_a_rule_name() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("line numbers and rule names, never
    values") and the tester brief (a frozen dataclass)."""
    finding = find_literal_credentials(SHAPES["github-ghp"])[0]
    fields = dataclasses.fields(finding)

    assert dataclasses.is_dataclass(finding)
    assert len(fields) == 2
    assert finding_rule(finding)
    assert isinstance(finding_line(finding), int)
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(finding, fields[0].name, finding_line(finding))


def test_the_first_line_is_numbered_zero_or_one() -> None:
    """AC-4. expected_behavior_source: AC-4 ("with a line number"). The base of the numbering is
    not stated, so only 0 or 1 is accepted and the tests below require it to be consistent."""
    assert numbering_base() in (0, 1)


@pytest.mark.parametrize("index", [0, 1, 5, 40])
def test_a_finding_is_numbered_from_the_same_base_on_every_line(index: int) -> None:
    """AC-4. expected_behavior_source: AC-4 ("with a line number")."""
    assert_flagged_only_on_line(document_with(SHAPES["github-ghp"], before=index), index)


def test_two_credentials_on_two_lines_give_findings_on_both_lines() -> None:
    """AC-4. expected_behavior_source: AC-4 (a line number for each finding)."""
    text = "\n".join([BENIGN_LINE, SHAPES["github-ghp"], BENIGN_LINE, jwt_shape(), BENIGN_LINE])

    assert flagged_lines(text) == {1 + numbering_base(), 3 + numbering_base()}


def test_an_empty_text_and_the_generated_file_text_have_no_finding() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (the scan runs on each rendered text
    before it is written, so the one generated entry must pass)."""
    assert find_literal_credentials("") == ()
    assert find_literal_credentials(RENDERED_FILE_TEXT) == ()


# The token-shaped strings -----------------------------------------------------------------------


@pytest.mark.parametrize("context", list(CONTEXTS))
@pytest.mark.parametrize("shape", list(SHAPES))
def test_a_string_with_a_known_token_prefix_is_found_on_its_line(shape: str, context: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (GitHub prefixes, ATATT, sk-ant-, AKIA
    and xox-style prefixes). The body lengths are those of real tokens; the minimum length that
    the design requires is a question for the person."""
    assert_flagged_only_on_line(document_with(in_context(context, SHAPES[shape])), 2)


@pytest.mark.parametrize("shape", list(SHAPES))
def test_a_token_at_the_end_of_the_text_is_found_with_and_without_a_trailing_newline(
    shape: str,
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7; ADR-002 decision 3 (the trailing
    newline is a case that the tests must cover)."""
    for text in (SHAPES[shape], SHAPES[shape] + "\n"):
        assert_flagged_only_on_line(text, 0)


@pytest.mark.parametrize("context", list(CONTEXTS))
def test_a_jwt_shaped_string_is_found_on_its_line(context: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (a JWT-shaped string)."""
    assert_flagged_only_on_line(document_with(in_context(context, jwt_shape())), 2)


@pytest.mark.parametrize(
    "line",
    [
        "docs.example.com",
        'version = "1.2.3"',
        "release: a.b.c",
        '  "url": "https://docs.example.com/v1.2.3/mcp"',
        "name: orqlet-atlassian",
    ],
)
def test_dotted_text_that_is_not_jwt_shaped_has_no_finding(line: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (a JWT-shaped string starts with the
    JWT header prefix)."""
    assert find_literal_credentials(document_with(line)) == ()


# User information in a URL ----------------------------------------------------------------------

USER_INFO_URLS = {
    "user-only": "https://someone@docs.example.com/mcp",
    "user-and-password": "https://someone:pw@docs.example.com/mcp",
    "token-as-user": "https://" + SHAPES["github-ghp"] + "@docs.example.com/mcp",
}


@pytest.mark.parametrize("context", ["bare", "json-value", "toml-value"])
@pytest.mark.parametrize("url", list(USER_INFO_URLS.values()), ids=list(USER_INFO_URLS))
def test_user_information_in_a_url_is_found_on_its_line(url: str, context: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (user information in a URL)."""
    assert_flagged_only_on_line(document_with(in_context(context, url)), 2)


@pytest.mark.parametrize(
    "line",
    [
        '  "url": "https://docs.example.com/mcp"',
        '  "url": "https://docs.example.com/@scope/package"',
        "contact: someone@docs.example.com",
        f'  "url": "{ATLASSIAN_URL}"',
    ],
    ids=["plain-address", "at-sign-in-the-path", "mail-address-without-a-scheme", "atlassian"],
)
def test_a_url_without_user_information_has_no_finding(line: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (user information is the part before
    the `@` of the authority, RFC 3986; a path or a mail address has none)."""
    assert find_literal_credentials(document_with(line)) == ()


# Credential-named URL query parameters ----------------------------------------------------------

QUERY_NAMES = ["key", "api_key", "apikey", "token", "access_token", "secret", "password", "sig"]


def percent_encode(text: str, *, upper: bool = True) -> str:
    return "".join(f"%{ord(char):02X}" if upper else f"%{ord(char):02x}" for char in text)


def query_url(parameter: str) -> str:
    return "https://docs.example.com/mcp?" + parameter + "=" + LITERAL


@pytest.mark.parametrize("name", QUERY_NAMES)
def test_a_credential_named_query_parameter_is_found_on_its_line(name: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (the names key, api_key, apikey, token,
    access_token, secret, password, sig)."""
    line = in_context("json-value", query_url(name))

    assert_flagged_only_on_line(document_with(line), 2)


@pytest.mark.parametrize(
    "encode",
    [
        pytest.param(lambda name: percent_encode(name[0]) + name[1:], id="first-letter"),
        pytest.param(lambda name: percent_encode(name[0], upper=False) + name[1:], id="lower-hex"),
        pytest.param(lambda name: name.replace("_", "%5F"), id="underscore"),
        pytest.param(lambda name: percent_encode(name), id="every-character"),
        pytest.param(lambda name: percent_encode(name, upper=False), id="every-character-lower"),
    ],
)
@pytest.mark.parametrize("name", QUERY_NAMES)
def test_a_percent_encoded_credential_name_is_found_after_decoding(
    name: str, encode: Callable[[str], str]
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("a credential-named URL query
    parameter after percent-decoding")."""
    line = in_context("json-value", query_url(encode(name)))

    assert_flagged_only_on_line(document_with(line), 2)


def test_a_credential_named_parameter_after_other_parameters_is_found() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7."""
    line = in_context("json-value", "https://docs.example.com/mcp?page=2&q=a&token=" + LITERAL)

    assert_flagged_only_on_line(document_with(line), 2)


@pytest.mark.parametrize(
    "url",
    [
        "https://docs.example.com/mcp?page=2",
        "https://docs.example.com/mcp?page=2&q=hello",
        "https://docs.example.com/mcp?%70age=2",
        "https://docs.example.com/mcp?pa%67e=2",
        "https://docs.example.com/mcp?q=" + LITERAL,
    ],
)
def test_a_query_without_a_credential_name_has_no_finding(url: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (only the named parameters count, also
    after decoding: `%70age` is `page`)."""
    assert find_literal_credentials(document_with(in_context("json-value", url))) == ()


# Authorization, Bearer and Basic values ---------------------------------------------------------

LITERAL_AUTH_LINES = {
    "raw-bearer": "Authorization: Bearer " + LITERAL,
    "json-bearer": '      "Authorization": "Bearer ' + LITERAL + '"',
    "raw-basic": "Authorization: Basic " + BASIC_VALUE,
    "json-basic": '      "Authorization": "Basic ' + BASIC_VALUE + '"',
    "json-bare-value": '      "Authorization": "' + LITERAL + '"',
    "template-with-a-suffix": '      "Authorization": "Bearer ${' + VALID_VARIABLE + '}extra"',
    "template-with-a-prefix": '      "Authorization": "Bearer pre${' + VALID_VARIABLE + '}"',
    "template-with-a-default": (
        '      "Authorization": "Bearer ${' + VALID_VARIABLE + ":-" + LITERAL + '}"'
    ),
}
ANCHORED_TEMPLATE_LINES = {
    "claude-code-json": '      "Authorization": "Bearer ${' + VALID_VARIABLE + '}"',
    "cursor-json": '      "Authorization": "Bearer ${env:' + VALID_VARIABLE + '}"',
    "claude-code-raw": "Authorization: Bearer ${" + VALID_VARIABLE + "}",
}


@pytest.mark.parametrize("line", list(LITERAL_AUTH_LINES.values()), ids=list(LITERAL_AUTH_LINES))
def test_an_authorization_value_that_is_not_the_anchored_template_is_found(line: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (an Authorization, Bearer or Basic value
    that is not the anchored template) and decision 4 (the default form `:-` is forbidden)."""
    assert_flagged_only_on_line(document_with(line), 2)


@pytest.mark.parametrize(
    "line", list(ANCHORED_TEMPLATE_LINES.values()), ids=list(ANCHORED_TEMPLATE_LINES)
)
def test_the_anchored_template_has_no_finding(line: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 4 (the single header value
    `Authorization: Bearer ${NAME}`, or `${env:NAME}` for Cursor) and decision 7."""
    assert find_literal_credentials(document_with(line)) == ()


# Credential-named keys with a literal value -----------------------------------------------------

CREDENTIAL_KEYS = [
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "private_key",
    "authorization",
]
KEY_STYLES = {
    "json": '  "{key}": "{value}",',
    "toml": '{key} = "{value}"',
    "yaml": "{key}: {value}",
}


def keyed_line(style: str, key: str, value: str = LITERAL) -> str:
    return KEY_STYLES[style].format(key=key, value=value)


@pytest.mark.parametrize("style", list(KEY_STYLES))
@pytest.mark.parametrize("key", CREDENTIAL_KEYS)
def test_a_credential_named_key_with_a_literal_value_is_found(key: str, style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (a credential-named key with a literal
    value; the names token, secret, password, passwd, apikey, api_key, private_key,
    authorization)."""
    assert_flagged_only_on_line(document_with(keyed_line(style, key)), 2)


@pytest.mark.parametrize("style", list(KEY_STYLES))
@pytest.mark.parametrize("key", ["client_secret", "my_token_value", "db_password_hint"])
def test_a_key_that_contains_a_credential_name_is_credential_named(key: str, style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("a key that contains token, secret,
    password, ...")."""
    assert_flagged_only_on_line(document_with(keyed_line(style, key)), 2)


@pytest.mark.parametrize("style", list(KEY_STYLES))
@pytest.mark.parametrize("key", ["type", "url", "name", "command", "mode", "keyboard"])
def test_a_key_without_a_credential_name_has_no_finding(key: str, style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (only keys that contain a listed name
    count; `keyboard` contains none of them)."""
    assert find_literal_credentials(document_with(keyed_line(style, key))) == ()


def test_a_credential_word_in_a_value_is_not_a_credential_named_key() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (the rule is about the key)."""
    line = '  "description": "Sign in with your own token"'

    assert find_literal_credentials(document_with(line)) == ()


@pytest.mark.parametrize(
    "line",
    [
        pytest.param('      "bearer_token_env_var": "' + VALID_VARIABLE + '"', id="json"),
        pytest.param('bearer_token_env_var = "' + VALID_VARIABLE + '"', id="toml"),
        pytest.param("bearer_token_env_var: " + VALID_VARIABLE, id="yaml"),
    ],
)
def test_bearer_token_env_var_with_a_matching_variable_name_is_exempt(line: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (a key that holds a reference by design
    is exempt) and AC-4 ("whose value matches the variable pattern")."""
    assert find_literal_credentials(document_with(line)) == ()


@pytest.mark.parametrize("value", [LITERAL, "GITHUB_TOKEN", "orqlet_mcp_github", "ORQLET_MCP_"])
@pytest.mark.parametrize("style", list(KEY_STYLES))
def test_bearer_token_env_var_with_another_value_is_not_exempt(value: str, style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (the exemption needs a name that
    matches the variable pattern of decision 3)."""
    line = keyed_line(style, "bearer_token_env_var", value)

    assert_flagged_only_on_line(document_with(line), 2)


# Findings never show a value or a raw key --------------------------------------------------------


def leak_cases() -> dict[str, tuple[str, tuple[str, ...]]]:
    """A line for each rule, and the parts of it that no finding may show."""
    key, value = "zq7-key-marker-91c2_token", "zq7-value-marker-7d1e"
    cases: dict[str, tuple[str, tuple[str, ...]]] = {
        f"token-{name}": (token, (token, token[-20:])) for name, token in SHAPES.items()
    }
    cases["jwt"] = (jwt_shape(), (jwt_shape(), jwt_shape()[-20:]))
    cases["user-information"] = (
        "https://zq7-user-marker-2c9a:" + value + "@docs.example.com/mcp",
        ("zq7-user-marker-2c9a", value),
    )
    cases["query"] = ("https://docs.example.com/mcp?to%6Ben=" + value, (value,))
    cases["authorization"] = ("Authorization: Bearer " + value, (value,))
    cases["credential-key"] = (keyed_line("json", key, value), (key, value))
    cases["oversize"] = ("x" * (MAX_LINE + 1) + value, (value,))
    return cases


LEAK_CASES = leak_cases()


@pytest.mark.parametrize(("line", "secrets"), list(LEAK_CASES.values()), ids=list(LEAK_CASES))
def test_a_finding_shows_neither_the_matched_text_nor_the_raw_key(
    line: str, secrets: tuple[str, ...]
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("never a value or a raw key"); ADR-002 decisions 7
    and 9."""
    findings = find_literal_credentials(document_with(line))

    assert findings
    assert not holds_any(shown_by(findings), *secrets)


# Oversize lines ---------------------------------------------------------------------------------


@pytest.mark.parametrize("ending", ["", "\n"])
def test_a_line_of_exactly_4096_characters_is_not_oversize(ending: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("a line ... longer than 4096
    characters" is a finding; 4096 is within the cap)."""
    assert find_literal_credentials("x" * MAX_LINE + ending) == ()


@pytest.mark.parametrize("length", [MAX_LINE + 1, MAX_LINE + 2, 3 * MAX_LINE, 200_000])
def test_a_line_longer_than_4096_characters_is_an_oversize_finding(length: int) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (`oversize`)."""
    findings = find_literal_credentials(document_with("x" * length))
    oversize_lines = {finding_line(f) for f in findings if finding_rule(f) == OVERSIZE}

    assert oversize_lines == {2 + numbering_base()}


@pytest.mark.parametrize("shape", [*SHAPES, "jwt"])
def test_a_credential_at_offset_4097_is_found_by_the_oversize_finding(shape: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("a credential-shaped string at offset
    4097 of one line", "so a credential past the cap cannot hide behind it")."""
    token = jwt_shape() if shape == "jwt" else SHAPES[shape]
    line = "x" * (MAX_LINE + 1) + token

    findings = find_literal_credentials(document_with(line))
    oversize_lines = {finding_line(f) for f in findings if finding_rule(f) == OVERSIZE}

    assert oversize_lines == {2 + numbering_base()}
    assert not holds_any(shown_by(findings), token)


def test_the_cap_is_per_line_and_a_long_text_of_short_lines_is_not_oversize() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("the scan reads at most 4096
    characters per line"; a file is scanned as raw text up to 256 KiB, decision 8)."""
    text = "\n".join(["x" * 40] * 300) + "\n"

    assert len(text) > MAX_LINE
    assert find_literal_credentials(text) == ()


def test_a_line_after_an_oversize_line_is_still_scanned() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (the finding is per line)."""
    text = "\n".join(["x" * (MAX_LINE + 1), BENIGN_LINE, SHAPES["github-ghp"], ""])
    base = numbering_base()
    findings = find_literal_credentials(text)
    oversize_lines = {finding_line(f) for f in findings if finding_rule(f) == OVERSIZE}

    assert oversize_lines == {0 + base}
    assert 2 + base in flagged_lines(text)


def test_every_rule_name_is_a_non_empty_string() -> None:
    """AC-4. expected_behavior_source: AC-4 ("a rule name"); the exact names are not pinned."""
    text = "\n".join([line for line, _ in LEAK_CASES.values()])

    findings = find_literal_credentials(text)

    assert findings
    assert all(finding_rule(finding) for finding in findings)


# --- AC-5: entry_differences and referenced_variables --------------------------------------------

PINNED: dict[str, object] = {"type": "http", "url": ATLASSIAN_URL}
PINNED_WITH_HEADERS: dict[str, object] = {
    **PINNED,
    "headers": {"Authorization": "Bearer ${ORQLET_MCP_DECLARED}"},
}
PINNED_FOR_CODEX: dict[str, object] = {"url": ATLASSIAN_URL, "bearer_token_env_var": VALID_VARIABLE}


def assert_closed_vocabulary(result: tuple[str, ...]) -> None:
    assert isinstance(result, tuple)
    assert set(result) <= VOCABULARY


@pytest.mark.parametrize("pinned", [PINNED, PINNED_WITH_HEADERS, PINNED_FOR_CODEX, {}])
def test_two_equal_entries_give_no_difference(pinned: dict[str, object]) -> None:
    """AC-5. expected_behavior_source: AC-5 ("two equal entries give ()"); ADR-002 decision 9."""
    assert entry_differences(pinned, dict(pinned)) == ()


def test_two_equal_entries_with_another_key_order_give_no_difference() -> None:
    """AC-5. expected_behavior_source: AC-5 (equal entries; a mapping's equality ignores order)."""
    assert entry_differences(PINNED, {"url": ATLASSIAN_URL, "type": "http"}) == ()


def test_a_changed_type_is_named() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (closed vocabulary: type)."""
    assert entry_differences(PINNED, {**PINNED, "type": "sse"}) == ("type",)


def test_a_changed_url_is_named() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (closed vocabulary: url)."""
    assert entry_differences(PINNED, {**PINNED, "url": GITHUB_URL}) == ("url",)


def test_changed_headers_are_named() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (closed vocabulary: headers)."""
    found = {**PINNED_WITH_HEADERS, "headers": {"Authorization": "Bearer pre${ORQLET_MCP_X}"}}

    assert entry_differences(PINNED_WITH_HEADERS, found) == ("headers",)


def test_a_changed_bearer_token_env_var_is_named() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (closed vocabulary:
    bearer_token_env_var)."""
    found = {**PINNED_FOR_CODEX, "bearer_token_env_var": "ORQLET_MCP_OTHER"}

    assert entry_differences(PINNED_FOR_CODEX, found) == ("bearer_token_env_var",)


def test_every_field_that_differs_is_named_once() -> None:
    """AC-5. expected_behavior_source: AC-5 ("returns the fields in which the found entry
    differs")."""
    result = entry_differences(PINNED, {"type": "sse", "url": GITHUB_URL})

    assert_closed_vocabulary(result)
    assert sorted(result) == ["type", "url"]


@pytest.mark.parametrize("key", ["zq7-extra-marker-5d1e", "Zq7ExtraMarker"])
def test_an_unknown_key_is_reported_as_unknown_key_and_never_by_name(key: str) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (`unknown-key`; never an unknown key)."""
    result = entry_differences(PINNED, {**PINNED, key: "zq7-value-marker-7d1e"})

    assert result == ("unknown-key",)
    assert not holds_any(" ".join(result), key, "zq7-value-marker-7d1e")


def test_an_unknown_key_and_a_changed_type_are_both_reported() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (closed vocabulary)."""
    result = entry_differences(PINNED, {**PINNED, "type": "sse", "zq7-extra-marker-5d1e": 1})

    assert_closed_vocabulary(result)
    assert set(result) == {"type", "unknown-key"}
    assert not holds_any(" ".join(result), "zq7-extra-marker-5d1e")


def test_no_value_and_no_undeclared_name_appears_in_the_result() -> None:
    """AC-5. expected_behavior_source: AC-5 ("never an unknown key, a value or an undeclared
    name"); ADR-002 decision 9."""
    pinned = {"url": "https://zq7-pinned-url-1a2b.example.com/mcp", "headers": {"x": "zq7-pin-1"}}
    found = {
        "url": "https://zq7-found-url-3c4d.example.com/mcp",
        "headers": {"Authorization": "Bearer ${ORQLET_MCP_ZQ7UNDECLARED}"},
        "bearer_token_env_var": "ORQLET_MCP_ZQ7OTHERNAME",
        "zq7-extra-marker-5d1e": "zq7-value-marker-7d1e",
    }

    result = entry_differences(pinned, found)

    assert result
    assert_closed_vocabulary(result)
    assert not holds_any(
        " ".join(result),
        "zq7-pinned-url-1a2b",
        "zq7-found-url-3c4d",
        "zq7-pin-1",
        "ZQ7UNDECLARED",
        "ZQ7OTHERNAME",
        "zq7-extra-marker-5d1e",
        "zq7-value-marker-7d1e",
    )


def test_the_name_in_bearer_token_env_var_is_a_reference() -> None:
    """AC-5. expected_behavior_source: AC-5 ("and of bearer_token_env_var in an entry")."""
    entry = {"url": ATLASSIAN_URL, "bearer_token_env_var": "ORQLET_MCP_X"}

    assert referenced_variables(entry) == ("ORQLET_MCP_X",)


def test_a_dollar_brace_reference_in_a_header_is_a_variable() -> None:
    """AC-5. expected_behavior_source: AC-5 (`${NAME}`); ADR-002 decision 4."""
    headers = {"Authorization": "Bearer ${ORQLET_MCP_A}"}
    entry = {"type": "http", "url": ATLASSIAN_URL, "headers": headers}

    assert referenced_variables(entry) == ("ORQLET_MCP_A",)


def test_a_dollar_brace_env_reference_in_a_header_is_a_variable_without_its_prefix() -> None:
    """AC-5. expected_behavior_source: AC-5 (`${env:NAME}`); ADR-002 decision 4 (Cursor)."""
    entry = {"url": ATLASSIAN_URL, "headers": {"Authorization": "Bearer ${env:ORQLET_MCP_B}"}}

    assert referenced_variables(entry) == ("ORQLET_MCP_B",)


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param({"url": "https://${ORQLET_MCP_H}/mcp"}, id="url"),
        pytest.param({"headers": {"X-Other": "${ORQLET_MCP_H}"}}, id="header"),
        pytest.param({"command": "run", "args": ["--flag", "${ORQLET_MCP_H}"]}, id="argument"),
        pytest.param({"command": "run", "env": {"TOKEN_VALUE": "${ORQLET_MCP_H}"}}, id="env"),
    ],
)
def test_a_reference_anywhere_in_an_entry_is_a_variable(entry: dict[str, object]) -> None:
    """AC-5. expected_behavior_source: AC-5 ("every `${NAME}` ... reference ... in an entry");
    ADR-002 decision 6 (used on undeclared entries, which may hold a reference anywhere)."""
    assert referenced_variables(entry) == ("ORQLET_MCP_H",)


def test_a_reference_to_a_variable_outside_the_orqlet_prefix_is_a_variable() -> None:
    """AC-5. expected_behavior_source: AC-5 (every `${NAME}`); ADR-002 decision 6 (an undeclared
    entry that sends another environment variable to a host)."""
    entry = {"url": "https://docs.example.com/mcp", "headers": {"x": "Bearer ${SOME_OTHER_VAR}"}}

    assert referenced_variables(entry) == ("SOME_OTHER_VAR",)


def test_several_references_are_all_returned() -> None:
    """AC-5. expected_behavior_source: AC-5 (every reference). Order is not stated."""
    entry = {
        "url": "https://docs.example.com/mcp",
        "headers": {"Authorization": "Bearer ${ORQLET_MCP_A}", "X-Env": "${env:ORQLET_MCP_B}"},
        "bearer_token_env_var": "ORQLET_MCP_C",
    }

    assert sorted(referenced_variables(entry)) == ["ORQLET_MCP_A", "ORQLET_MCP_B", "ORQLET_MCP_C"]


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param({}, id="empty"),
        pytest.param({"type": "http", "url": ATLASSIAN_URL}, id="oauth-entry"),
        pytest.param({"command": "run", "args": ["--flag", "value"]}, id="process"),
        pytest.param({"url": GITHUB_URL, "headers": {"X-Static": "plain text"}}, id="plain-header"),
    ],
)
def test_an_entry_without_a_reference_gives_an_empty_tuple(entry: dict[str, object]) -> None:
    """AC-5. expected_behavior_source: AC-5 ("() for an entry without any")."""
    assert referenced_variables(entry) == ()


# --- AC-7: the module is pure --------------------------------------------------------------------

ALLOWED_IMPORTS = frozenset({"re", "collections.abc", "typing", "dataclasses"})
# `from __future__ import annotations` is a compiler directive, not a dependency; whether the
# criterion counts it is a question for the person.
COMPILER_DIRECTIVES = frozenset({"__future__"})
FORBIDDEN_NAMES = frozenset({"__import__", "eval", "exec", "open"})


def imported_modules(source: str) -> set[str]:
    """The modules that a source imports, at any depth; a relative import shows as dots."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add("." * node.level + (node.module or ""))
    return modules


def used_names(source: str) -> set[str]:
    return {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}


def test_the_module_imports_only_the_allowed_standard_library_modules() -> None:
    """AC-7. expected_behavior_source: AC-7 and ORQLET-ARCH-002 ("imports only re,
    collections.abc, typing and dataclasses"); component view layer rules."""
    imported = imported_modules(inspect.getsource(mcp_credentials))

    assert imported - ALLOWED_IMPORTS - COMPILER_DIRECTIVES == set()


def test_the_module_reaches_for_no_dynamic_import_and_no_file() -> None:
    """AC-7. expected_behavior_source: AC-7 ("uses no clock, random number or environment")."""
    assert used_names(inspect.getsource(mcp_credentials)) & FORBIDDEN_NAMES == set()


def test_the_import_check_finds_a_clock_a_random_number_and_the_environment() -> None:
    """AC-7. expected_behavior_source: AC-7 (the failing case of the check above)."""
    source = "import os\nfrom time import time\n\ndef f() -> None:\n    import random\n"

    assert imported_modules(source) == {"os", "time", "random"}
    assert imported_modules(source) - ALLOWED_IMPORTS == {"os", "time", "random"}


def test_the_import_check_finds_a_relative_import_and_a_dynamic_import() -> None:
    """AC-7. expected_behavior_source: AC-7 (the failing case of the checks above)."""
    source = "from . import sibling\nmodule = __import__('os')\n"

    assert imported_modules(source) == {"."}
    assert used_names(source) & FORBIDDEN_NAMES == {"__import__"}


def test_the_import_check_passes_the_four_allowed_modules() -> None:
    """AC-7. expected_behavior_source: AC-7 (the passing case of the checks above)."""
    source = (
        "import re\nfrom collections.abc import Mapping\nfrom dataclasses import dataclass\n"
        "from typing import Final\n"
    )

    assert imported_modules(source) - ALLOWED_IMPORTS == set()
    assert used_names(source) & FORBIDDEN_NAMES == set()


# --- rework round 1: the findings of the first review --------------------------------------------
# Sources: ADR-002 decision 7 and the non-blocking findings of review round 1 of phase P-1
# (security F-1 to F-6, architecture F-3 to F-6).


@pytest.mark.parametrize("style", list(KEY_STYLES))
def test_a_credential_named_key_with_a_literal_and_a_reference_is_found(style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (a credential-named key with a literal
    value); review r1 security F-2 (a value that mixes a literal with a reference is a literal)."""
    value = LITERAL + "${" + VALID_VARIABLE + "}"

    assert_flagged_only_on_line(document_with(keyed_line(style, "password", value)), 2)


@pytest.mark.parametrize("style", list(KEY_STYLES))
@pytest.mark.parametrize("value", ["${" + VALID_VARIABLE + "}", "${env:" + VALID_VARIABLE + "}"])
def test_a_credential_named_key_with_only_a_reference_has_no_finding(
    style: str, value: str
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 4 (a reference holds no literal)."""
    assert find_literal_credentials(document_with(keyed_line(style, "password", value))) == ()


@pytest.mark.parametrize("style", list(KEY_STYLES))
@pytest.mark.parametrize(
    "key", ["x-api-key", "api-key", "private-key", "X-Api-Key", "client-secret", "x-auth-token"]
)
def test_a_hyphenated_credential_name_is_credential_named(key: str, style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (names such as api_key and private_key);
    review r1 security F-3 (`x-api-key` is the same name as `x_api_key`)."""
    assert_flagged_only_on_line(document_with(keyed_line(style, key)), 2)


@pytest.mark.parametrize("style", list(KEY_STYLES))
@pytest.mark.parametrize("key", ["x-request-id", "content-type", "x-api-version"])
def test_a_hyphenated_name_without_a_credential_word_has_no_finding(key: str, style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (only listed words count)."""
    assert find_literal_credentials(document_with(keyed_line(style, key))) == ()


@pytest.mark.parametrize(
    "line",
    [
        "Basic configuration of the server",
        "Bearer authentication is described in the guide",
        '  "purpose": "Basic search over Bearer protected pages"',
    ],
)
def test_prose_with_a_scheme_word_has_no_finding(line: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("a Bearer or Basic value that is not
    the anchored template" is a credential, a word of prose is not); review r1 security F-6 and
    architecture F-4. A token needs a digit, `=`, `+` or `/`."""
    assert find_literal_credentials(document_with(line)) == ()


@pytest.mark.parametrize("scheme", ["Bearer", "Basic"])
def test_a_scheme_word_followed_by_a_token_with_digits_is_found(scheme: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7; review r1 architecture F-4."""
    line = f"see {scheme} " + body(12) + " in the log"

    assert_flagged_only_on_line(document_with(line), 2)


def test_variable_names_are_returned_as_written_and_are_not_filtered() -> None:
    """AC-5. expected_behavior_source: review r1 security F-1 and architecture F-3: the names are
    for comparison only, so a caller must never print them."""
    pasted = "not a variable name"

    assert referenced_variables({"bearer_token_env_var": pasted}) == (pasted,)


def test_a_reference_deeper_than_the_depth_limit_is_not_searched() -> None:
    """AC-5. expected_behavior_source: review r1 architecture F-6 and security F-5; the caller caps
    depth first (ADR-002 decision 8, nesting above 16 levels is refused)."""
    entry: dict[str, object] = {"headers": "${ORQLET_MCP_H}"}
    shallow = entry
    for _ in range(10):
        shallow = {"inner": shallow}
    deep = entry
    for _ in range(40):
        deep = {"inner": deep}

    assert referenced_variables(shallow) == ("ORQLET_MCP_H",)
    assert referenced_variables(deep) == ()


def test_a_default_form_reports_the_outer_name_only() -> None:
    """AC-5. expected_behavior_source: review r1 architecture F-6 (documented limit); the default
    form `:-` is forbidden by ADR-002 decision 4, so any entry that uses it fails elsewhere."""
    entry = {"headers": {"Authorization": "Bearer ${ORQLET_MCP_A:-${ORQLET_MCP_B}}"}}

    assert referenced_variables(entry) == ("ORQLET_MCP_A",)


# --- rework round 2: the findings of the second review -------------------------------------------
# Sources: ADR-002 decision 7 and the non-blocking findings of review round 2 of phase P-1
# (security F-1 and F-2, architecture F-4 and F-6).


@pytest.mark.parametrize("style", list(KEY_STYLES))
@pytest.mark.parametrize("value", ["[x1y2z3]", "{x1y2z3}", "[", "{"])
def test_a_quoted_value_that_starts_with_a_bracket_is_a_literal(style: str, value: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7; review r2 security F-1. A quoted value
    is a string whatever its first character is."""
    quoted = {"json": f'  "password": "{value}",', "toml": f'password = "{value}"'}
    line = quoted.get(style, f"password: '{value}'")

    assert_flagged_only_on_line(document_with(line), 2)


@pytest.mark.parametrize("line", ['  "password": {', "password: {", "password = {", '  "token": ['])
def test_an_unquoted_opening_bracket_is_a_nested_structure_and_not_a_literal(line: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (a nested structure holds no literal)."""
    assert find_literal_credentials(document_with(line)) == ()


@pytest.mark.parametrize("name", ["api-key", "access-token", "API-KEY"])
def test_a_hyphenated_query_name_is_a_credential_name(name: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (the query names api_key and
    access_token); review r2 security F-2 (`api-key` is the same name as `api_key`)."""
    line = in_context("json-value", query_url(name))

    assert_flagged_only_on_line(document_with(line), 2)


@pytest.mark.parametrize("scheme", ["bearer", "BEARER", "basic", "BASIC"])
def test_the_scheme_word_is_matched_in_any_letter_case(scheme: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7; review r2 security F-2 (scheme names
    are case-insensitive)."""
    line = f"see {scheme} " + body(12) + " in the log"

    assert_flagged_only_on_line(document_with(line), 2)


@pytest.mark.parametrize("run", [2100, 3000, 4000])
def test_a_query_credential_after_a_long_path_is_found(run: int) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (a credential past the repetition cap
    must not hide inside the 4096-character window); review r2 architecture F-4."""
    url = "https://docs.example.com/" + "a" * run + "?token=" + LITERAL

    assert_flagged_only_on_line(document_with(url[:MAX_LINE]), 2)


@pytest.mark.parametrize("run", [2100, 3000, 4000])
def test_user_information_after_a_long_authority_is_found(run: int) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (user information in a URL); review r2
    architecture F-4."""
    url = "https://" + "a" * run + "@docs.example.com/mcp"

    assert_flagged_only_on_line(document_with(url[:MAX_LINE]), 2)


@pytest.mark.parametrize("style", list(KEY_STYLES))
def test_a_bearer_token_env_var_of_49_characters_is_not_exempt(style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 3 and 7 (the exemption needs a name that
    matches the variable pattern, at most 48 characters); review r2 architecture F-6."""
    line = keyed_line(style, "bearer_token_env_var", "ORQLET_MCP_" + "A" * 38)

    assert_flagged_only_on_line(document_with(line), 2)


@pytest.mark.parametrize("style", list(KEY_STYLES))
def test_a_bearer_token_env_var_of_48_characters_is_exempt(style: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 3 and 7 (at most 48 characters)."""
    line = keyed_line(style, "bearer_token_env_var", "ORQLET_MCP_" + "A" * 37)

    assert find_literal_credentials(document_with(line)) == ()
