"""MCP credentials: property tests and the worst-case time (task mcp-or-plugins, phase P-1, AC-6).

Every test cites its `expected_behavior_source`. ADR-002 is
docs/design/mcp-or-plugins/design/adr-002-one-credential-per-user.md and AC-1 to AC-7 are the
acceptance criteria of phase P-1 in docs/design/mcp-or-plugins/plan.yaml.

These tests were written first, by the Tester of phase P-1, before `orqlet.domain.mcp_credentials`
existed. The last test was added in rework round 1.

Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003). The builders are shared with test_mcp_credentials.py, as the end-to-end tests
share theirs.

"No function raises for arbitrary text" is applied to the five functions that judge text. The two
functions that refuse input by design, `rendered_entry` and `mcp_file_path`, are held to a
different rule: they either refuse (with any exception, the type is not fixed by the design) or
return the one entry that the design enables.
"""

import copy
import string
import time
from collections.abc import Callable

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

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
from tests.unit.domain.test_mcp_credentials import (
    ATLASSIAN_URL,
    CLAUDE_CODE,
    EYJ,
    GITHUB_URL,
    LITERAL,
    MAX_LINE,
    OAUTH,
    SHAPES,
    VALID_ID,
    VOCABULARY,
    body,
    finding_line,
    finding_rule,
    holds_any,
    refusal_text,
    shown_by,
)

pytestmark = pytest.mark.unit

# The limit for scanning one 4096-character line (ADR-002 decision 7, AC-6). The first measurement
# on 2026-10-26 gave at most 0.63 ms for the slowest line of this file, so 0.25 s is about 400
# times the measured worst case: slow CI machines pass and a pattern that backtracks does not.
WORST_CASE_SECONDS_PER_LINE = 0.25

# --- strategies ----------------------------------------------------------------------------------

_ALPHANUMERIC = string.ascii_letters + string.digits
# A distinctive part: the ZQ7 and 7QZ ends make a chance match with a rule name or a fixed word
# practically impossible, and the body is alphanumeric so that it fits inside a token.
_parts = st.text(alphabet=_ALPHANUMERIC, min_size=10, max_size=16).map(
    lambda text: "ZQ7" + text + "7QZ"
)


def padded(part: str, size: int) -> str:
    """`part` followed by filler up to `size` characters (the part is never longer than 22)."""
    return (part + body(size))[:size]


LINE_TEMPLATES: dict[str, Callable[[str], str]] = {
    "github-classic": lambda part: "ghp" + "_" + padded(part, 36),
    "github-fine-grained": lambda part: "github" + "_pat_" + padded(part, 22) + "_" + body(59),
    "atlassian": lambda part: "AT" + "ATT" + "3" + part + body(100),
    "anthropic": lambda part: "sk" + "-ant-" + "api03-" + part + body(70),
    "slack": lambda part: "xo" + "xb-" + "123456789012-123456789012-" + padded(part, 24),
    "jwt": lambda part: ".".join(
        (EYJ + "hbGciOiJIUzI1NiJ9", EYJ + part, padded(part, 43)),
    ),
    "user-information-with-password": lambda part: "https://someone:" + part + "@docs.example.com",
    "user-information": lambda part: "https://" + part + "@docs.example.com/mcp",
    "query-secret": lambda part: "https://docs.example.com/mcp?token=" + part,
    "encoded-query-secret": lambda part: "https://docs.example.com/mcp?to%6Ben=" + part,
    "bearer-literal": lambda part: "Authorization: Bearer " + part,
    "basic-literal": lambda part: '"Authorization": "Basic ' + part + '"',
    "credential-named-key": lambda part: '"' + part + '_secret": "' + LITERAL + '"',
    "credential-named-value": lambda part: '"password": "' + part + '"',
    "oversize-line": lambda part: part + "x" * (MAX_LINE + 4),
}

_JSON_SCALARS = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False)
    | st.text(alphabet=st.characters(exclude_categories=["Cs"]), max_size=16)
)
_json_values = st.recursive(
    _JSON_SCALARS,
    lambda children: (
        st.lists(children, max_size=3) | st.dictionaries(st.text(max_size=8), children, max_size=3)
    ),
    max_leaves=8,
)
_entry_keys = st.sampled_from(
    ["type", "url", "headers", "bearer_token_env_var", "command", "args", "env"]
) | st.text(max_size=8)
_entries = st.dictionaries(_entry_keys, _json_values, max_size=5)

_NO_DOLLAR = st.text(alphabet=st.characters(exclude_categories=["Cs"], exclude_characters="$"))
# `referenced_variables` reads `bearer_token_env_var` at every depth, so no level may hold it.
_keys_without_the_holder = _NO_DOLLAR.filter(lambda key: key != "bearer_token_env_var")
_entries_without_a_reference = st.dictionaries(
    _keys_without_the_holder,
    st.recursive(
        st.none() | st.booleans() | st.integers() | _NO_DOLLAR,
        lambda children: (
            st.lists(children, max_size=3)
            | st.dictionaries(_keys_without_the_holder, children, max_size=3)
        ),
        max_leaves=8,
    ),
    max_size=5,
)

_valid_ids = st.from_regex(r"[a-z][a-z0-9-]{0,31}", fullmatch=True)
_valid_variables = st.lists(
    st.from_regex(r"[A-Z][A-Z0-9]{0,6}", fullmatch=True), min_size=1, max_size=4
).map(lambda segments: "ORQLET_MCP_" + "_".join(segments))
_valid_urls = st.from_regex(
    r"https://[a-z][a-z0-9]{1,8}(\.[a-z][a-z0-9]{1,8}){1,3}(/[a-z0-9]{1,8}){0,3}", fullmatch=True
)
_not_an_id_character = st.characters(
    exclude_categories=["Cs"], exclude_characters=string.ascii_lowercase + string.digits + "-"
)
_not_a_variable_character = st.characters(
    exclude_categories=["Cs"], exclude_characters=string.ascii_uppercase + string.digits + "_"
)

_token_pieces = [
    "ey" + "J",
    "gh" + "p_",
    "AK" + "IA",
    "xo" + "xb-",
    "sk" + "-ant-",
    "AT" + "ATT",
    ".",
    "%",
    "%41",
    "\\u0041",
    "?token=",
    "@",
    "https://",
    "Authorization",
    "Bearer ",
    "Basic ",
    "${",
    "}",
    '"',
    ":",
    "=",
    " ",
    "\t",
    "\r",
    "\n",
    "\r\n",
    "\x00",
    "\u212a",
    "x" * 60,
    "A1" * 30,
]
_structured_text = st.lists(st.sampled_from(_token_pieces), max_size=60).map("".join)
_any_text = st.text(alphabet=st.characters(exclude_categories=["Cs"]), max_size=200)


def line_count_bound(text: str) -> int:
    """A bound on the number of lines under any reasonable way of splitting a text."""
    return max(text.count("\n"), len(text.splitlines())) + 1


# --- AC-6: no finding and no message shows a part of the text ------------------------------------


@pytest.mark.parametrize("template", sorted(LINE_TEMPLATES))
@given(part=_parts)
def test_no_finding_shows_a_part_of_the_text_for_each_rule(template: str, part: str) -> None:
    """AC-6. expected_behavior_source: ADR-002 decisions 7 and 9 (line numbers and rule names,
    never values or raw keys). Each template is a case that the unit tests of AC-4 require to be
    found, so the result is never empty."""
    findings = find_literal_credentials("\n".join(["{", LINE_TEMPLATES[template](part), "}"]))

    assert findings
    assert not holds_any(shown_by(findings), part)


@given(st.lists(st.tuples(st.sampled_from(sorted(LINE_TEMPLATES)), _parts), min_size=1, max_size=6))
def test_no_finding_shows_a_part_of_a_text_that_mixes_the_rules(
    choices: list[tuple[str, str]],
) -> None:
    """AC-6. expected_behavior_source: ADR-002 decisions 7 and 9."""
    text = "\n".join(LINE_TEMPLATES[name](part) for name, part in choices)

    findings = find_literal_credentials(text)

    assert findings
    assert not holds_any(shown_by(findings), *(part for _, part in choices))


@given(_parts, _parts, _parts)
def test_name_problems_never_shows_a_value(id_part: str, url_part: str, variable_part: str) -> None:
    """AC-6. expected_behavior_source: AC-1 ("no returned text contains an input value");
    ADR-002 decision 9. The upper-case ends of each part break the id and variable patterns."""
    broken_url = "https://" + url_part + "@docs.example.com/mcp?x=" + url_part
    cases = [
        (id_part, ATLASSIAN_URL, None),
        (VALID_ID, broken_url, None),
        (VALID_ID, ATLASSIAN_URL, variable_part),
        (id_part, broken_url, variable_part),
    ]

    for case in cases:
        problems = name_problems(*case)
        assert problems
        assert not holds_any(" ".join(problems), id_part, url_part, variable_part)


@given(_parts)
def test_a_refusal_never_shows_an_input_value(part: str) -> None:
    """AC-6. expected_behavior_source: AC-3 ("the refusal text holds no input value");
    ADR-002 decision 9. The `mcp_file_path` case follows the tester brief of phase P-1."""
    calls: list[Callable[[], object]] = [
        lambda: rendered_entry(part, ATLASSIAN_URL, None, CLAUDE_CODE),
        lambda: rendered_entry(
            VALID_ID, "https://" + part.lower() + ".example.com/mcp", None, CLAUDE_CODE
        ),
        lambda: rendered_entry(VALID_ID, ATLASSIAN_URL, "ORQLET_MCP_" + part.upper(), CLAUDE_CODE),
        lambda: rendered_entry(VALID_ID, ATLASSIAN_URL, None, part),
        lambda: mcp_file_path(part),
    ]

    for call in calls:
        assert not holds_any(refusal_text(call), part)


@given(_parts, _parts, _parts)
def test_entry_differences_never_shows_a_key_a_value_or_a_name(
    key_part: str, value_part: str, name_part: str
) -> None:
    """AC-6. expected_behavior_source: AC-5 ("never an unknown key, a value or an undeclared
    name"); ADR-002 decision 9."""
    pinned = {"type": "http", "url": ATLASSIAN_URL, "headers": {"X": "${ORQLET_MCP_DECLARED}"}}
    found = {
        "type": value_part,
        "url": "https://" + value_part.lower() + ".example.com/mcp",
        "headers": {key_part: "Bearer ${ORQLET_MCP_" + name_part.upper() + "}"},
        "bearer_token_env_var": name_part,
        key_part: value_part,
    }

    result = entry_differences(pinned, found)

    assert result
    assert not holds_any(" ".join(result), key_part, value_part, name_part)


# --- AC-5 and AC-6: the closed vocabulary --------------------------------------------------------


@given(_entries, _entries)
def test_entry_differences_names_only_the_closed_vocabulary(
    pinned: dict[str, object], found: dict[str, object]
) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (type, url, headers,
    bearer_token_env_var, entry, unknown-key) and AC-5 ("never an unknown key")."""
    result = entry_differences(pinned, found)

    assert isinstance(result, tuple)
    assert set(result) <= VOCABULARY


@given(_entries)
def test_an_entry_compared_with_a_copy_of_itself_gives_no_difference(
    entry: dict[str, object],
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("two equal entries give ()")."""
    assert entry_differences(entry, copy.deepcopy(entry)) == ()


@given(
    _entries,
    st.text(min_size=1, max_size=12).filter(
        lambda key: key not in VOCABULARY | {"type", "url", "headers", "bearer_token_env_var"}
    ),
    _json_values,
)
def test_an_added_unknown_key_is_reported_as_unknown_key(
    entry: dict[str, object], key: str, value: object
) -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (`unknown-key` stands for any key that
    is not one of the entry fields)."""
    assume(key not in entry)

    result = entry_differences(entry, {**entry, key: value})

    assert "unknown-key" in result
    assert key not in result


@given(_valid_variables, _valid_variables, _valid_variables)
def test_every_reference_in_a_header_and_every_bearer_variable_is_returned(
    first: str, second: str, third: str
) -> None:
    """AC-5. expected_behavior_source: AC-5 (every `${NAME}`, `${env:NAME}` and
    bearer_token_env_var)."""
    entry = {
        "url": "https://docs.example.com/mcp",
        "headers": {"Authorization": "Bearer ${" + first + "}", "X-Env": "${env:" + second + "}"},
        "bearer_token_env_var": third,
    }

    assert set(referenced_variables(entry)) == {first, second, third}


@given(_entries_without_a_reference)
def test_generated_entries_without_a_reference_give_an_empty_tuple(
    entry: dict[str, object],
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("() for an entry without any")."""
    assert referenced_variables(entry) == ()


# --- AC-1 to AC-3: generated cases ---------------------------------------------------------------


@given(_valid_ids, _valid_urls, st.none() | _valid_variables)
def test_generated_valid_names_have_no_problem(
    server_id: str, url: str, variable: str | None
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decisions 3 and 4 (the patterns)."""
    assert name_problems(server_id, url, variable) == ()


@given(_valid_ids, _not_an_id_character)
def test_an_id_with_a_character_outside_the_class_is_a_problem(
    server_id: str, character: str
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (`[a-z0-9-]` only, ASCII, no
    IGNORECASE)."""
    assert name_problems(server_id + character, ATLASSIAN_URL, None)
    assert name_problems(character + server_id, ATLASSIAN_URL, None)


@given(_valid_ids)
def test_an_id_with_a_trailing_newline_or_more_than_32_characters_is_a_problem(
    server_id: str,
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (fullmatch; at most 32 characters)."""
    assert name_problems(server_id + "\n", ATLASSIAN_URL, None)
    assert name_problems(server_id + "a" * 32, ATLASSIAN_URL, None)


@given(_valid_variables, _not_a_variable_character)
def test_a_variable_with_a_character_outside_the_class_is_a_problem(
    variable: str, character: str
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (`[A-Z0-9_]` only, ASCII, no
    IGNORECASE)."""
    assert name_problems(VALID_ID, ATLASSIAN_URL, variable + character)


@given(_valid_variables)
def test_a_variable_with_a_trailing_newline_or_more_than_48_characters_is_a_problem(
    variable: str,
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 3 (fullmatch; at most 48 characters)."""
    assert name_problems(VALID_ID, ATLASSIAN_URL, variable + "\n")
    assert name_problems(VALID_ID, ATLASSIAN_URL, variable + "A" * 49)


@pytest.mark.parametrize("suffix", ["?x=1", "#top", "\n", "\\mcp", "%41", "${X}", "/%2e"])
@given(url=_valid_urls)
def test_an_address_with_a_forbidden_part_is_a_problem(suffix: str, url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 (no query, fragment, `${`, backslash or
    percent-encoding; a trailing newline breaks the fullmatch of decision 3)."""
    assert name_problems(VALID_ID, url + suffix, None)


@given(_valid_urls)
def test_an_address_with_user_information_or_without_https_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 4 (https, no user information)."""
    host_and_path = url.removeprefix("https://")

    assert name_problems(VALID_ID, "https://someone@" + host_and_path, None)
    assert name_problems(VALID_ID, "http://" + host_and_path, None)


@st.composite
def mutated_atlassian_urls(draw: st.DrawFn) -> str:
    """The Atlassian address with one character inserted, removed or replaced."""
    index = draw(st.integers(0, len(ATLASSIAN_URL) - 1))
    character = draw(st.characters(exclude_categories=["Cs"]))
    operation = draw(st.sampled_from(["insert", "delete", "replace"]))
    head, tail = ATLASSIAN_URL[:index], ATLASSIAN_URL[index:]
    if operation == "insert":
        return head + character + tail
    if operation == "delete":
        return head + tail[1:]
    return head + character + tail[1:]


_urls = st.sampled_from([ATLASSIAN_URL, GITHUB_URL]) | mutated_atlassian_urls() | _any_text
_clients = st.sampled_from([CLAUDE_CODE, "cursor", "codex"]) | _any_text


@given(_urls, _clients)
def test_only_the_one_address_with_the_one_client_enables_a_mode(url: str, client: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 2 (exactly one row: Atlassian OAuth for
    Claude Code; any other address, a letter-case change or a one-character edit enables none)."""
    modes = allowed_auth_modes(url, client)

    assert modes == ((OAUTH,) if (url, client) == (ATLASSIAN_URL, CLAUDE_CODE) else ())


@given(
    _valid_ids | _any_text,
    _urls,
    st.none() | _valid_variables | _any_text,
    _clients,
)
def test_rendered_entry_returns_only_the_one_enabled_entry(
    server_id: str, url: str, variable: str | None, client: str
) -> None:
    """AC-3. expected_behavior_source: AC-3 (the mapping for the Atlassian address, no variable
    and Claude Code; every other combination, and any value with a name problem, is refused)."""
    try:
        entry = rendered_entry(server_id, url, variable, client)
    except Exception:
        # A refusal: the design does not fix its exception type. The unit tests of AC-3 hold
        # the cases that must be refused, so this property only constrains what is returned.
        return

    assert (url, variable, client) == (ATLASSIAN_URL, None, CLAUDE_CODE)
    assert name_problems(server_id, url, variable) == ()
    assert list(entry) == ["type", "url"]
    assert entry == {"type": "http", "url": ATLASSIAN_URL}


# --- AC-6: no function raises for arbitrary text, and each is deterministic ----------------------


@given(_any_text | _structured_text)
def test_the_scan_never_raises_and_returns_findings_of_a_line_and_a_rule(text: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("no function raises for arbitrary text");
    ADR-002 decision 7. Line numbers are only bounded, because their base is not stated."""
    findings = find_literal_credentials(text)

    assert isinstance(findings, tuple)
    for finding in findings:
        assert isinstance(finding, CredentialFinding)
        assert finding_rule(finding)
        assert 0 <= finding_line(finding) <= line_count_bound(text)


@given(_any_text | _structured_text)
def test_the_scan_gives_the_same_findings_on_every_call(text: str) -> None:
    """AC-6. expected_behavior_source: ORQLET-DET-001 and the component view (each function is
    deterministic on its inputs)."""
    assert find_literal_credentials(text) == find_literal_credentials(text)


@given(_any_text | _structured_text, _any_text | _structured_text, st.none() | _any_text)
def test_name_problems_never_raises_and_returns_rule_names(
    server_id: str, url: str, variable: str | None
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("no function raises for arbitrary text")."""
    problems = name_problems(server_id, url, variable)

    assert isinstance(problems, tuple)
    assert all(isinstance(name, str) and name for name in problems)
    assert name_problems(server_id, url, variable) == problems


@given(_any_text, _any_text)
def test_allowed_auth_modes_never_raises_and_returns_a_tuple_of_names(
    url: str, client: str
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("no function raises for arbitrary text")."""
    modes = allowed_auth_modes(url, client)

    assert isinstance(modes, tuple)
    assert all(isinstance(mode, str) and mode for mode in modes)


@given(_entries, _entries)
def test_entry_differences_never_raises_for_arbitrary_mappings(
    pinned: dict[str, object], found: dict[str, object]
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("no function raises for arbitrary text")."""
    assert isinstance(entry_differences(pinned, found), tuple)


@given(_entries)
def test_referenced_variables_never_raises_and_returns_names(entry: dict[str, object]) -> None:
    """AC-6. expected_behavior_source: AC-6 ("no function raises for arbitrary text")."""
    names = referenced_variables(entry)

    assert isinstance(names, tuple)
    assert all(isinstance(name, str) for name in names)


# --- AC-6: the worst case of the scan ------------------------------------------------------------


def repeated(unit: str, size: int = MAX_LINE) -> str:
    """`unit` repeated and cut to exactly `size` characters."""
    return (unit * (size // len(unit) + 1))[:size]


RUN_CHARACTERS = {
    "lower-case-letter": "a",
    "upper-case-letter": "A",
    "digit": "0",
    "underscore": "_",
    "hyphen": "-",
    "dot": ".",
    "equals-sign": "=",
    "percent-sign": "%",
    "colon": ":",
    "at-sign": "@",
    "question-mark": "?",
    "ampersand": "&",
    "space": " ",
    "backslash": "\\",
    "double-quote": '"',
    "slash": "/",
}
REPEATED_UNITS = {
    "eyj": EYJ,
    "eyj-and-dot": EYJ + ".",
    "eyj-letter-and-dot": EYJ + "a.",
    "github-prefix": "gh" + "p_",
    "fine-grained-prefix": "github" + "_pat_",
    "atlassian-prefix": "AT" + "ATT",
    "aws-prefix": "AK" + "IA",
    "slack-prefix": "xo" + "xb-",
    "anthropic-prefix": "sk" + "-ant-",
    "bearer": "Bearer ",
    "basic": "Basic ",
    "authorization": "Authorization: ",
    "credential-query": "?token=a&",
    "scheme": "https://",
    "scheme-and-user": "https://a@",
    "percent-encoded-letter": "%41",
    "unicode-escape": "\\u0041",
    "credential-key": '"token": "',
    "key-value-pairs": '"a": "b", ',
    "reference": "${ORQLET_MCP_A}",
}
WORST_CASE_LINES = {
    **{f"run-of-{name}": repeated(char) for name, char in RUN_CHARACTERS.items()},
    **{f"repeated-{name}": repeated(unit) for name, unit in REPEATED_UNITS.items()},
    "token-prefix-then-a-long-run": SHAPES["github-ghp"][:4] + repeated("A", MAX_LINE - 4),
    "oversize-run": repeated("a", 500_000),
    "oversize-repeated-eyj": repeated(EYJ + ".", 500_000),
    "oversize-token-prefix-then-a-run": SHAPES["github-ghp"][:4] + repeated("A", 500_000),
}


def seconds_to_scan(text: str) -> float:
    """The time that one scan takes. This is the only clock in the tests: the module has none."""
    started = time.perf_counter()
    findings = find_literal_credentials(text)
    elapsed = time.perf_counter() - started
    assert isinstance(findings, tuple)
    return elapsed


@pytest.mark.parametrize("line", list(WORST_CASE_LINES.values()), ids=list(WORST_CASE_LINES))
def test_a_worst_case_line_is_scanned_within_the_limit(line: str) -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 ("its worst case per line is fixed";
    repeated `eyJ` and long runs of one character; a time limit per 4096-character line, which
    the implementer sets after a first measurement)."""
    assert seconds_to_scan(line) < WORST_CASE_SECONDS_PER_LINE


def test_a_text_of_many_worst_case_lines_costs_the_limit_per_line_at_most() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 (the limit is per line, so the cost of a
    text grows with its number of lines and not faster)."""
    lines = [line for line in WORST_CASE_LINES.values() if len(line) == MAX_LINE]

    assert len(lines) > 10
    assert seconds_to_scan("\n".join(lines)) < WORST_CASE_SECONDS_PER_LINE * len(lines)


@pytest.mark.parametrize("unit", ["${a:-", "${", "${a:-${b:-", "${ORQLET_MCP_A:-x"])
def test_referenced_variables_on_a_worst_case_string_is_fast(unit: str) -> None:
    """AC-6. expected_behavior_source: review r1 security F-4 (a long run of reference starts
    without a closing brace). The time limit is that of the scan."""
    entry: dict[str, object] = {"headers": repeated(unit, 2048), "env": {"a": repeated(unit, 2048)}}
    started = time.perf_counter()
    names = referenced_variables(entry)
    elapsed = time.perf_counter() - started

    assert isinstance(names, tuple)
    assert elapsed < WORST_CASE_SECONDS_PER_LINE
