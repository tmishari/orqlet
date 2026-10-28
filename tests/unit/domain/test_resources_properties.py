"""Team resources: property tests and the worst-case time (task team-conventions-resources, P-1).

Every test cites its `expected_behavior_source`. ADR-002 is the file `adr-002-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, AC-1 to AC-5 are acceptance criteria of phase P-1 in
docs/design/team-conventions-resources/plan.yaml, and S-5 and S-7 are the considerations of
considerations.md in the same folder.

These tests were written first, by the Tester of phase P-1, before `orqlet.domain.resources`
existed. The builders are shared with test_resources.py, as the precedent of the MCP credentials
shares theirs. Credential-shaped text is assembled from parts at run time and never written as one
literal (ORQLET-SEC-003).

The properties are: no problem shows any part of the input (every function returns fixed rule
names), no function raises for arbitrary text, the allow-lists accept what the design describes
and refuse what it forbids, and the scans finish within a generous absolute time for hostile input.
The behaviour that the design leaves open is listed in test_resources.py and is not pinned here.
"""

import string
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from orqlet.domain.resources import (
    copy_problems,
    credential_problems,
    glob_problems,
    hidden_text_problems,
    host_of,
    is_stale,
    resource_id_problems,
    text_problems,
    uncovered_names,
    url_problems,
)
from tests.unit.domain.test_resources import (
    ADDRESS,
    EYJ,
    HIDDEN_RANGES,
    PEM_DASHES,
    REFERENCE_LINE,
    WINDOWS_DEVICE_NAMES,
    assert_well_formed,
    body,
    copy_text,
    holds_a_part,
    holds_any,
    is_hidden,
    shown,
)

pytestmark = pytest.mark.unit

# The limit for every timed test. It is set before a first measurement: the implementation does not
# exist when this file is written, so the number comes from the sizes and not from a run. 5 seconds
# is far above what a linear scan of 256 KiB can need (a few hundred milliseconds even with ten
# patterns) and far below what a quadratic scan of the same input needs (about 7e10 steps) or an
# exponential one. The first measurement may lower it; a limit that proved too low is raised only
# with the measurement written next to it.
TIME_LIMIT_SECONDS = 5.0
# First measurement (2026-10-27, Python 3.14, one laptop): the slowest timed test of these two
# files takes 0.30 s, so the limit is about sixteen times the slowest run and still catches a
# quadratic scan.
TEXT_SIZE = 262_144  # 256 KiB, the largest text that ADR-002 decision 9 and ADR-004 let reach these
LINE_CAP = 4096  # ADR-002 decision 9


# --- strategies -----------------------------------------------------------------------------------

_ALPHANUMERIC = string.ascii_letters + string.digits
# A distinctive part: the ZQ7 and 7QZ ends make a chance match with a rule name or a fixed word
# practically impossible, and the middle is alphanumeric so that it fits inside a token.
_parts = st.text(alphabet=_ALPHANUMERIC, min_size=10, max_size=16).map(
    lambda text: "ZQ7" + text + "7QZ"
)
_any_text = st.text(max_size=200)
# Every code point, lone surrogates and the last plane included: str may hold all of them.
_codepoint_text = st.lists(st.integers(0, 0x10FFFF).map(chr), max_size=40).map("".join)
_PIECES = [
    "https://",
    "://",
    "](",
    "<!--",
    "-->",
    "`",
    "<",
    ">",
    "@",
    ":",
    "\\",
    "%",
    "%25",
    "%2f",
    "${",
    "#",
    "?",
    "&",
    ";",
    "=",
    ".",
    "..",
    "-",
    "--",
    "xn--",
    "nip.io",
    "localhost",
    "0x",
    "127.1",
    "token",
    "Source: ",
    REFERENCE_LINE,
    "\n",
    "\r\n",
    "\t",
    "\x00",
    "\u202e",
    EYJ,
    "Authorization: Bearer ",
    "cookies",
    "origins",
    PEM_DASHES + "BEGIN ",
    "gh" + "p_",
    "x" * 40,
    "aB3" * 14,
    " ",
    "/",
    "*",
    "{",
    "}",
    "!",
]
_structured_text = st.lists(st.sampled_from(_PIECES), max_size=40).map("".join)
_texts = _any_text | _codepoint_text | _structured_text


def padded(part: str, size: int) -> str:
    """`part` followed by filler up to `size` characters (the part is never longer than 22)."""
    return (part + body(size))[:size]


# --- no problem shows a part of the input ---------------------------------------------------------

URL_TEMPLATES: dict[str, Callable[[str], str]] = {
    "user-information": lambda part: f"https://{part}@docs.example.com/guides",
    "upper-case-host-label": lambda part: f"https://{part}.example.com/guides",
    "port": lambda part: f"https://docs.example.com:8443/{part}",
    "fragment": lambda part: f"https://docs.example.com/guides#{part}",
    "credential-query-key": lambda part: f"https://docs.example.com/guides?{part}_token=1",
    "open-redirect-value": lambda part: (
        f"https://docs.example.com/guides?next=https%253A%252F%252F{part}.example.net"
    ),
    "opaque-query-value": lambda part: f"https://docs.example.com/guides?ref={part}{body(30)}",
    "opaque-path-segment": lambda part: f"https://docs.example.com/{part}{body(30)}",
    "wildcard-dns": lambda part: f"https://{part.lower()}.nip.io/guides",
    "reserved-label": lambda part: f"https://{part.lower()}.localhost/guides",
    "dollar-brace": lambda part: "https://docs.example.com/${" + part + "}",
    "backslash-before-the-at-sign": lambda part: (
        "https://docs.example.com\\@" + part.lower() + ".example.net/guides"
    ),
    "single-label-host": lambda part: f"https://{part.lower()}/guides",
}
FORBIDDEN_IN_TEXT = [
    "@",
    "\u202e",
    "<",
    ">",
    "`",
    "://",
    "](",
    "<!--",
    "-->",
    "\n",
    "\u200b",
    "\U000e0041",
]
CREDENTIAL_TEMPLATES: dict[str, Callable[[str], str]] = {
    "github-classic": lambda part: "gh" + "p_" + padded(part, 36),
    "jwt": lambda part: ".".join((EYJ + "hbGciOiJIUzI1NiJ9", EYJ + part, padded(part, 43))),
    "user-information-with-a-password": lambda part: (
        "https://someone:" + part + "@docs.example.com"
    ),
    "user-information": lambda part: "https://" + part + "@docs.example.com/page",
    "authorization-bearer": lambda part: "Authorization: Bearer " + part + body(30),
    "key-value-secret": lambda part: "secret=" + part + body(30),
    "key-value-password": lambda part: "password=" + part + body(30),
    "private-key-body": lambda part: (
        PEM_DASHES + "BEGIN PRIVATE KEY" + PEM_DASHES + "\n" + part + body(60)
    ),
    "storage-state": lambda part: '{"cookies": [], "origins": [], "x": "' + part + '"}',
    "oversize-line": lambda part: part + "x" * (LINE_CAP + 4),
}
HIDDEN_SAMPLE = sorted(
    {
        code_point
        for first, last in HIDDEN_RANGES.values()
        for code_point in (first, (first + last) // 2, last)
        if is_hidden(code_point)
    }
)


@pytest.mark.parametrize("template", sorted(URL_TEMPLATES))
@given(part=_parts)
def test_url_problems_shows_no_part_of_a_refused_address(template: str, part: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("it never contains the input"); ORQLET-SEC-003. Each
    template is an address that the unit tests of AC-1 require to be refused."""
    problems = url_problems(URL_TEMPLATES[template](part))

    assert problems
    assert not holds_any(shown(problems), part, part[:12])


@given(part=_parts, element=st.sampled_from(FORBIDDEN_IN_TEXT))
def test_text_problems_shows_no_part_of_a_refused_text(part: str, element: str) -> None:
    """AC-2. expected_behavior_source: ORQLET-SEC-003; ADR-002 decision 8 (text_problems)."""
    problems = text_problems(part + element + part[::-1], 200)

    assert problems
    assert not holds_any(shown(problems), part, part[:12], part[::-1])


@given(part=_parts)
def test_resource_id_problems_shows_no_part_of_a_refused_id(part: str) -> None:
    """AC-2. expected_behavior_source: ORQLET-SEC-003; ADR-002 decision 1 (the upper case ends of
    the part break the id grammar)."""
    lowered = part.lower()
    for value in (part, lowered + "-", lowered + "--a", "1" + lowered, lowered + "_x", lowered * 5):
        problems = resource_id_problems(value)

        assert problems
        assert not holds_any(shown(problems), part, part[:12])


@given(part=_parts)
def test_glob_problems_shows_no_part_of_a_refused_glob(part: str) -> None:
    """AC-2. expected_behavior_source: ORQLET-SEC-003; ADR-002 decision 1 (glob_problems)."""
    for value in (
        "!" + part,
        "/" + part,
        part + "/../x",
        "{" + part + "}",
        part + "\u202e",
        part * 20,
    ):
        problems = glob_problems(value)

        assert problems
        assert not holds_any(shown(problems), part, part[:12])


@given(part=_parts, other=_parts)
def test_copy_problems_shows_no_part_of_the_text_or_the_address(part: str, other: str) -> None:
    """AC-4. expected_behavior_source: ORQLET-SEC-003; ADR-002 decision 9 (the header lines)."""
    address = "https://" + other.lower() + ".example.com/guides"
    texts = [
        part,
        f"Source: {part}\n{REFERENCE_LINE}\nbody",
        f"Source: {address}\n{part}\nbody",
        f"{REFERENCE_LINE}\nSource: {address}\n{part}",
    ]
    for text in texts:
        problems = copy_problems(text, address)

        assert problems
        assert not holds_any(shown(problems), part, part[:12], other, other[:12])


@given(part=_parts, code_point=st.sampled_from(HIDDEN_SAMPLE))
def test_hidden_text_problems_shows_neither_the_text_nor_the_code_point(
    part: str, code_point: int
) -> None:
    """AC-4. expected_behavior_source: ORQLET-SEC-003; ADR-002 decision 9 (hidden_text_problems)."""
    for text in (f"line {part}{chr(code_point)} end", f"<!-- {part} -->"):
        problems = hidden_text_problems(text)

        assert problems
        assert not holds_any(shown(problems), part, part[:12])
        assert chr(code_point) not in shown(problems)


@pytest.mark.parametrize("template", sorted(CREDENTIAL_TEMPLATES))
@given(part=_parts)
def test_credential_problems_shows_no_part_of_the_text(template: str, part: str) -> None:
    """AC-4. expected_behavior_source: AC-4 ("never the text"); ADR-002 decision 9 (the rule name
    and the line); ORQLET-SEC-003. Each template is a case that the unit tests of AC-4 require to
    be found, so the result is never empty."""
    problems = credential_problems(
        "\n".join(["Heading", CREDENTIAL_TEMPLATES[template](part), "end"])
    )

    assert problems
    assert not holds_any(shown(problems), part, part[:12])


@given(
    st.lists(
        st.tuples(st.sampled_from(sorted(CREDENTIAL_TEMPLATES)), _parts), min_size=1, max_size=6
    )
)
def test_credential_problems_shows_no_part_of_a_text_that_mixes_the_rules(
    choices: list[tuple[str, str]],
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("never the text"); ORQLET-SEC-003."""
    text = "\n".join(CREDENTIAL_TEMPLATES[name](part) for name, part in choices)

    problems = credential_problems(text)

    assert problems
    assert not holds_any(shown(problems), *(part for _, part in choices))


# --- no function raises for arbitrary text --------------------------------------------------------

UNARY_FUNCTIONS: dict[str, Callable[[str], tuple[str, ...]]] = {
    "url_problems": url_problems,
    "resource_id_problems": resource_id_problems,
    "glob_problems": glob_problems,
    "hidden_text_problems": hidden_text_problems,
    "credential_problems": credential_problems,
}


@pytest.mark.parametrize("name", sorted(UNARY_FUNCTIONS))
@given(text=_texts)
def test_a_problem_function_never_raises_and_returns_rule_names(name: str, text: str) -> None:
    """AC-1 to AC-4. expected_behavior_source: plan P-1 (no function raises for arbitrary text);
    EC-1, EC-3, EC-4, EC-7 and EC-8 (`-> tuple[str, ...]`); ORQLET-SEC-003 (no problem shows a
    part of the input; texts shorter than 16 characters are left out of that check because a
    short text can equal a word that a fixed rule name contains)."""
    function = UNARY_FUNCTIONS[name]
    problems = function(text)

    assert_well_formed(problems)
    assert function(text) == problems
    assert len(text) < 16 or not holds_a_part(problems, text)


@given(text=_texts, limit=st.integers(1, 400))
def test_text_problems_never_raises_and_returns_rule_names(text: str, limit: int) -> None:
    """AC-2. expected_behavior_source: plan P-1 (no function raises for arbitrary text); EC-2."""
    problems = text_problems(text, limit)

    assert_well_formed(problems)
    assert text_problems(text, limit) == problems
    assert len(text) < 16 or not holds_a_part(problems, text)


@given(text=_texts, address=_texts)
def test_copy_problems_never_raises_and_returns_rule_names(text: str, address: str) -> None:
    """AC-4. expected_behavior_source: plan P-1 (no function raises for arbitrary text); EC-6."""
    problems = copy_problems(text, address)

    assert_well_formed(problems)
    assert len(text) < 16 or not holds_a_part(problems, text)


@given(text=_texts)
def test_host_of_never_raises_for_arbitrary_text(text: str) -> None:
    """AC-3. expected_behavior_source: plan P-1 (no function raises for arbitrary text); EC-11
    (`-> str`). What it returns for an address that url_problems refuses is not fixed."""
    assert isinstance(host_of(text), str)


_names = st.lists(_texts, max_size=8)


@given(technologies=_names, covered=_names)
def test_uncovered_names_never_raises_and_returns_a_tuple_of_text(
    technologies: list[str], covered: list[str]
) -> None:
    """AC-3. expected_behavior_source: plan P-1 (no function raises for arbitrary text); EC-10."""
    result = uncovered_names(technologies, covered)

    assert isinstance(result, tuple)
    assert all(isinstance(name, str) for name in result)


_zones = st.sampled_from([timezone(timedelta(hours=hours)) for hours in range(-12, 15)] + [UTC])
_instants = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=_zones,
)


@given(retrieved_at=_instants, ttl_days=st.integers(1, 365), now=_instants)
def test_is_stale_compares_instants_for_any_two_aware_datetimes(
    retrieved_at: datetime, ttl_days: int, now: datetime
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("raises no error for two timezone-aware datetimes and
    compares ttl_days"); ADR-002 decision 9 (retrieved_at plus ttl_days has passed). The instant of
    equality is not pinned."""
    deadline = retrieved_at + timedelta(days=ttl_days)
    assume(now != deadline)

    assert is_stale(retrieved_at, ttl_days, now) is (now > deadline)


# --- the allow-lists accept what the design describes and refuse what it forbids ------------------

_RESERVED_LAST_LABELS = {"localhost", "local", "localdomain"}
_LISTED_NAMES = {
    "nip.io",
    "sslip.io",
    "xip.io",
    "localtest.me",
    "lvh.me",
    "home.arpa",
    "bit.ly",
    "t.co",
    "tinyurl.com",
}


def _is_plain_host(host: str) -> bool:
    labels = host.split(".")
    return labels[-1] not in _RESERVED_LAST_LABELS and ".".join(labels[-2:]) not in _LISTED_NAMES


_labels = st.from_regex(r"[a-z][a-z0-9]{1,8}", fullmatch=True)
_segments = st.from_regex(r"[a-z0-9]{1,8}", fullmatch=True)
_hosts = st.lists(_labels, min_size=2, max_size=4).map(".".join).filter(_is_plain_host)
_paths = st.lists(_segments, max_size=3).map(lambda segments: "".join("/" + s for s in segments))

SPOILERS: dict[str, Callable[[str, str], str]] = {
    "port": lambda host, path: "https://" + host + ":8443" + path,
    "user-information": lambda host, path: "https://someone@" + host + path,
    "plain-http": lambda host, path: "http://" + host + path,
    "fragment": lambda host, path: "https://" + host + path + "#top",
    "credential-query-key": lambda host, path: "https://" + host + path + "?token=1",
    "upper-case-host": lambda host, path: "https://" + host.upper() + path,
    "opaque-path-segment": lambda host, path: "https://" + host + path + "/" + "a" * 32,
    "dollar-brace": lambda host, path: "https://" + host + path + "/${x}",
    "open-redirect": lambda host, path: "https://" + host + path + "?next=//evil.example.net",
}


@given(host=_hosts, path=_paths)
def test_a_generated_address_within_the_grammar_has_no_problem_and_its_host_is_known(
    host: str, path: str
) -> None:
    """AC-1 and AC-3. expected_behavior_source: ADR-002 decision 8 (https, a host of two to eight
    labels, an optional path); AC-3 (host_of returns the host that url_problems checked)."""
    url = "https://" + host + path

    assert url_problems(url) == ()
    assert host_of(url) == host


@pytest.mark.parametrize("spoiler", sorted(SPOILERS))
@given(host=_hosts, path=_paths)
def test_a_generated_address_with_one_forbidden_part_is_a_problem(
    spoiler: str, host: str, path: str
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (no port, user information, fragment,
    `${`, opaque run, credential query key or open-redirect value; https only; lower case host)."""
    assert url_problems(SPOILERS[spoiler](host, path))


_printable_without_markup = st.characters(
    min_codepoint=0x20, max_codepoint=0x7E, exclude_characters="<>`@"
)
_valid_texts = (
    st.text(alphabet=_printable_without_markup, min_size=1, max_size=60)
    .filter(lambda value: "://" not in value and "](" not in value)
    .filter(lambda value: value == value.strip())
)


@given(value=_valid_texts)
def test_a_generated_printable_ascii_text_has_no_problem(value: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 8 (printable U+0020 to U+007E on one line,
    none of `://`, `](`, `<!--`, `-->`, no backtick, neither `<` nor `>`)."""
    assert text_problems(value, 80) == ()


@given(
    value=_valid_texts,
    outside=st.integers(0, 0x10FFFF).filter(lambda code_point: not 0x20 <= code_point <= 0x7E),
    position=st.integers(0, 60),
)
def test_a_text_with_one_character_outside_the_printable_range_is_a_problem(
    value: str, outside: int, position: int
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("accepts only printable ASCII ... every code point
    above U+007E"); ADR-002 decision 8 (nothing outside U+0020 to U+007E, controls included)."""
    index = min(position, len(value))

    assert text_problems(value[:index] + chr(outside) + value[index:], 80)


@given(value=_valid_texts, element=st.sampled_from(["<", ">", "`", "://", "](", "<!--", "-->"]))
def test_a_text_with_one_forbidden_sequence_is_a_problem(value: str, element: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 8 (the forbidden sequences and
    characters)."""
    assert text_problems(value + element, 200)
    assert text_problems(element + value, 200)


@given(value=_valid_texts, extra=st.integers(1, 40))
def test_a_text_over_the_limit_is_a_problem(value: str, extra: int) -> None:
    """AC-2. expected_behavior_source: AC-2 ("within the limit"); ADR-002 decision 1 (title up to
    80, note up to 200 characters)."""
    assert text_problems(value, len(value)) == ()
    assert text_problems(value + "a" * extra, len(value))
    assert text_problems("a" * (80 + extra), 80)


_first_words = st.from_regex(r"[a-z][a-z0-9]{0,5}", fullmatch=True)
_next_words = st.from_regex(r"[a-z0-9]{1,6}", fullmatch=True)
_valid_ids = st.builds(
    lambda first, rest: "-".join([first, *rest]),
    _first_words,
    st.lists(_next_words, max_size=3),
).filter(lambda value: value not in WINDOWS_DEVICE_NAMES)


@given(resource_id=_valid_ids)
def test_a_generated_id_of_the_grammar_has_no_problem(resource_id: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (`[a-z][a-z0-9]*(-[a-z0-9]+)*`, up to
    32 characters, not a Windows device name)."""
    assert resource_id_problems(resource_id) == ()


@given(
    resource_id=_valid_ids,
    mutation=st.sampled_from(
        ["trailing-hyphen", "doubled-hyphen", "leading-hyphen", "upper-case", "newline", "too-long"]
    ),
)
def test_a_generated_id_with_one_defect_is_a_problem(resource_id: str, mutation: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (fullmatch, so no trailing or doubled
    hyphen and no trailing newline; lower case; at most 32 characters)."""
    mutated = {
        "trailing-hyphen": resource_id + "-",
        "doubled-hyphen": resource_id + "--a",
        "leading-hyphen": "-" + resource_id,
        "upper-case": resource_id.upper(),
        "newline": resource_id + "\n",
        "too-long": resource_id + "a" * 33,
    }[mutation]
    assume(mutated != resource_id)

    assert resource_id_problems(mutated)


_glob_segment = st.from_regex(r"[a-z0-9_-]{1,8}\*?", fullmatch=True) | st.sampled_from(["*", "**"])
_valid_globs = st.builds(
    lambda prefix, literal: "/".join([*prefix, literal]),
    st.lists(_glob_segment, max_size=6),
    st.from_regex(r"[a-z0-9_-]{1,8}", fullmatch=True),
)


@given(pattern=_valid_globs)
def test_a_generated_glob_that_names_something_has_no_problem(pattern: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (glob_problems: at most 120 characters,
    at least one character that is not `*`, `?` or `/`)."""
    assert glob_problems(pattern) == ()


@given(
    pattern=_valid_globs,
    spoiler=st.sampled_from(["!", "{", "}", "/", "\\", "\u202e", "../", "\n"]),
)
def test_a_generated_glob_with_one_forbidden_part_is_a_problem(pattern: str, spoiler: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (no `!`, `{` or `}`, no leading `/` or
    `\\`, no `..` segment, ASCII printable only)."""
    glob = {
        "!": "!" + pattern,
        "{": pattern + "{",
        "}": pattern + "}",
        "/": "/" + pattern,
        "\\": "\\" + pattern,
        "\u202e": pattern + "\u202e",
        "../": "../" + pattern,
        "\n": pattern + "\n",
    }[spoiler]

    assert glob_problems(glob)


@given(pattern=_valid_globs, extra=st.integers(1, 30))
def test_a_glob_over_120_characters_is_a_problem(pattern: str, extra: int) -> None:
    """AC-2. expected_behavior_source: AC-2 ("more than 120 characters")."""
    assert glob_problems(pattern + "a" * (121 - len(pattern) + extra - 1))


_copy_bodies = st.text(alphabet=string.ascii_letters + " \n.", min_size=1, max_size=100).filter(
    str.strip
)


@given(host=_hosts, path=_paths, rest=_copy_bodies, blank_line=st.booleans())
def test_a_generated_copy_with_the_two_header_lines_has_no_problem(
    host: str, path: str, rest: str, blank_line: bool
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (the file starts with `Source:
    <address>` and the reference line)."""
    address = "https://" + host + path

    assert copy_problems(copy_text(address, rest=rest, blank_line=blank_line), address) == ()


@given(host=_hosts, path=_paths, other=_hosts, rest=_copy_bodies)
def test_a_generated_copy_for_another_address_is_a_problem(
    host: str, path: str, other: str, rest: str
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("refuses a text whose first two lines are not
    `Source: <address>` ..."); ADR-002 decision 7 (a changed address leaves a stale Source line)."""
    address = "https://" + host + path
    other_address = "https://" + other + path
    assume(other_address != address)

    assert copy_problems(copy_text(other_address, rest=rest), address)


_benign_characters = st.characters(categories=("Lu", "Ll", "Nd")) | st.sampled_from(
    list(" \t\n.,;:!?-_/()")
)
_benign_texts = st.text(alphabet=_benign_characters, max_size=80)
_hidden_code_points = (
    st.sampled_from(sorted(HIDDEN_RANGES.values()))
    .flatmap(lambda bounds: st.integers(bounds[0], bounds[1]))
    .filter(is_hidden)
)


@given(text=_benign_texts)
def test_text_of_letters_digits_blanks_and_punctuation_is_not_hidden_text(text: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (a closed table: letters, digits, tab,
    line feed and ordinary punctuation are in none of its ranges)."""
    assert hidden_text_problems(text) == ()


@given(text=_benign_texts, code_point=_hidden_code_points, position=st.integers(0, 80))
def test_one_code_point_of_the_table_anywhere_in_a_text_is_hidden_text(
    text: str, code_point: int, position: int
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (the numeric table of ranges)."""
    index = min(position, len(text))

    assert hidden_text_problems(text[:index] + chr(code_point) + text[index:])


@given(text=st.text(alphabet=string.ascii_lowercase + " \n.,", max_size=200))
def test_plain_lower_case_prose_has_no_credential_problem(text: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (every rule needs a prefix, a dot
    separated header, a marker, an `@`, a colon, an equals sign or a quoted key, none of which
    plain lower case words and blanks hold)."""
    assert credential_problems(text) == ()


_short_names = st.text(alphabet=string.ascii_letters, min_size=1, max_size=8)


@given(technologies=st.lists(_short_names, max_size=8), covered=st.lists(_short_names, max_size=8))
def test_uncovered_names_is_the_difference_after_trimming_and_case_folding(
    technologies: list[str], covered: list[str]
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("compares after trimming and case folding"); ADR-002
    decision 7 (the technologies that no entry names as its tool)."""
    shifted = [" " + name.swapcase() + "\t" for name in covered]
    expected = {name.casefold() for name in technologies} - {name.casefold() for name in covered}

    result = uncovered_names(technologies, shifted)

    assert {name.strip().casefold() for name in result} == expected


# --- AC-5: the worst case of the scans ------------------------------------------------------------


def repeated(unit: str, size: int) -> str:
    """`unit` repeated and cut to exactly `size` characters."""
    return (unit * (size // len(unit) + 1))[:size]


def seconds_to_run(call: Callable[[], object]) -> float:
    """The time that one call takes. This is the only clock in the tests: the module has none."""
    started = time.perf_counter()
    call()
    return time.perf_counter() - started


CREDENTIAL_UNITS = {
    "eyj": EYJ,
    "eyj-and-dot": EYJ + ".",
    "eyj-letter-and-dot": EYJ + "a.",
    "equals-signs": "=",
    "spaces": " ",
    "bearer": "Bearer ",
    "authorization": "Authorization: ",
    "key-and-equals": "token=",
    "key-spaces-and-equals": "password = ",
    "begin-marker-start": PEM_DASHES + "BEGIN ",
    "scheme-and-user": "https://a@",
    "scheme": "https://",
    "percent-encoded-letter": "%41",
    "github-prefix": "gh" + "p_",
    "aws-prefix": "AK" + "IA",
    "cookies-key": '"cookies": ',
    "origins-key": '"origins": ',
    "braces-and-quotes": '{"a": ',
    "dashes": "-",
    "dots": ".",
}


def credential_inputs() -> dict[str, str]:
    """Each hostile unit as a line of 4096 and of 4097 characters, a text of 64 such lines and
    one line of 256 KiB, which the scan must treat as one finding and not as one scan."""
    inputs: dict[str, str] = {}
    for name, unit in CREDENTIAL_UNITS.items():
        line = repeated(unit, LINE_CAP)
        inputs[f"line-of-4096-{name}"] = line
        inputs[f"line-of-4097-{name}"] = repeated(unit, LINE_CAP + 1)
        inputs[f"text-of-64-lines-{name}"] = "\n".join([line] * (TEXT_SIZE // LINE_CAP))
        inputs[f"line-of-256-kib-{name}"] = repeated(unit, TEXT_SIZE)
    return inputs


CREDENTIAL_INPUTS = credential_inputs()


@pytest.mark.parametrize("text", list(CREDENTIAL_INPUTS.values()), ids=list(CREDENTIAL_INPUTS))
def test_credential_problems_finishes_in_the_limit_on_hostile_lines(text: str) -> None:
    """AC-5. expected_behavior_source: AC-5 ("the timed hostile-input tests finish under the
    recorded limit"); ADR-002 decision 9 (linear-time patterns on lines of at most 4096
    characters; hostile input is long runs of `eyJ`, of `=` and of spaces); considerations S-5."""
    results: list[tuple[str, ...]] = []

    elapsed = seconds_to_run(lambda: results.append(credential_problems(text)))

    assert elapsed < TIME_LIMIT_SECONDS
    assert_well_formed(results[0])


def test_credential_problems_finishes_in_the_limit_on_many_findings() -> None:
    """AC-5. expected_behavior_source: AC-5; ADR-002 decision 9 (a rule name and a line for each
    finding: a text with a finding on every line must not cost more than the lines)."""
    text = "\n".join("gh" + "p_" + body(36) for _ in range(5_000))
    results: list[tuple[str, ...]] = []

    elapsed = seconds_to_run(lambda: results.append(credential_problems(text)))

    assert elapsed < TIME_LIMIT_SECONDS
    assert results[0]


@pytest.mark.parametrize("size", [4096, 4097])
def test_a_line_at_the_cap_of_hostile_runs_is_scanned_in_the_limit_whatever_it_finds(
    size: int,
) -> None:
    """AC-5. expected_behavior_source: AC-5 (a line of 4096 characters is scanned, one of 4097 is
    itself a finding); plan P-1 (timed tests with a line of 4096 and one of 4097 characters). All
    hostile units in one text of 20 lines."""
    text = "\n".join(repeated(unit, size) for unit in CREDENTIAL_UNITS.values())

    assert seconds_to_run(lambda: credential_problems(text)) < TIME_LIMIT_SECONDS


HIDDEN_TEXT_UNITS = {
    "letters": "a",
    "spaces": " ",
    "line-feeds": "\n",
    "angle-brackets": "<",
    "comment-start-without-the-end": "<!-",
    "comment-start": "<!--",
    "comment-start-and-text": "<!-- a ",
    "comment-end": "-->",
    "dashes": "-",
    "zero-width-spaces": "\u200b",
    "supplementary-private-use": "\U000f0000",
    "accented-letters": "\u00e9",
    "mixed": "a\u200b<!--",
}


@pytest.mark.parametrize("unit", list(HIDDEN_TEXT_UNITS.values()), ids=list(HIDDEN_TEXT_UNITS))
def test_hidden_text_problems_finishes_in_the_limit_on_256_kib(unit: str) -> None:
    """AC-5. expected_behavior_source: AC-5; ADR-002 decision 9 (a copy and an evidence file are
    scanned whole: up to 64 KiB and 256 KiB). A comment start without an end is the input on which
    a scan that looks for the end from every start is quadratic."""
    text = repeated(unit, TEXT_SIZE)

    assert seconds_to_run(lambda: hidden_text_problems(text)) < TIME_LIMIT_SECONDS


@pytest.mark.parametrize("unit", list(HIDDEN_TEXT_UNITS.values()), ids=list(HIDDEN_TEXT_UNITS))
def test_copy_problems_finishes_in_the_limit_on_256_kib(unit: str) -> None:
    """AC-5. expected_behavior_source: AC-5; ADR-002 decision 9 (the header lines of a copy)."""
    after_the_header = copy_text(ADDRESS, rest=repeated(unit, TEXT_SIZE))
    huge_first_line = "Source: " + repeated(unit, TEXT_SIZE) + "\n" + REFERENCE_LINE + "\nbody"

    assert seconds_to_run(lambda: copy_problems(after_the_header, ADDRESS)) < TIME_LIMIT_SECONDS
    assert seconds_to_run(lambda: copy_problems(huge_first_line, ADDRESS)) < TIME_LIMIT_SECONDS
    assert (
        seconds_to_run(lambda: copy_problems(after_the_header, huge_first_line))
        < TIME_LIMIT_SECONDS
    )


@pytest.mark.parametrize(
    "unit",
    ["a", " ", "<!-", "](", ":/", "-->", "`", "\u202e", "a\n"],
    ids=[
        "letters",
        "spaces",
        "comment-start",
        "link-close-and-open",
        "colon-slash",
        "comment-end",
        "backtick",
        "override",
        "line-feeds",
    ],
)
def test_text_problems_finishes_in_the_limit_on_256_kib(unit: str) -> None:
    """AC-5. expected_behavior_source: AC-5; ADR-002 decision 8 (text_problems is a scan of an
    allow-list and refuses a value of 256 KiB without cost out of proportion)."""
    text = repeated(unit, TEXT_SIZE)
    results: list[tuple[str, ...]] = []

    assert seconds_to_run(lambda: results.append(text_problems(text, 200))) < TIME_LIMIT_SECONDS
    assert results[0]


@pytest.mark.parametrize(
    ("function", "unit"),
    [
        (glob_problems, "*"),
        (glob_problems, "**/"),
        (glob_problems, "../"),
        (glob_problems, "/"),
        (glob_problems, "a"),
        (glob_problems, "{"),
        (glob_problems, "*a"),
        (resource_id_problems, "a"),
        (resource_id_problems, "a-"),
        (resource_id_problems, "-"),
        (resource_id_problems, "--"),
        (resource_id_problems, "a-a"),
    ],
)
def test_glob_and_id_problems_finish_in_the_limit_on_256_kib(
    function: Callable[[str], tuple[str, ...]], unit: str
) -> None:
    """AC-5. expected_behavior_source: AC-5; ADR-002 decision 1 (an id and a glob are bounded where
    they enter; a value far over the limit is refused without a scan out of proportion)."""
    value = repeated(unit, TEXT_SIZE)
    results: list[tuple[str, ...]] = []

    assert seconds_to_run(lambda: results.append(function(value))) < TIME_LIMIT_SECONDS
    assert results[0]


HOSTILE_ADDRESSES = {
    "hosts-of-many-labels": "https://" + "a." * (TEXT_SIZE // 4) + "com",
    "one-label-of-256-kib": "https://" + "a" * TEXT_SIZE + ".com/",
    "label-of-hyphen-runs": "https://" + "a-" * (TEXT_SIZE // 4) + "a.com",
    "many-at-signs": "https://" + "a@" * (TEXT_SIZE // 4) + "docs.example.com/",
    "many-colons-before-the-at-sign": "https://" + ":" * TEXT_SIZE + "@docs.example.com/",
    "long-path-of-segments": "https://docs.example.com/" + "a/" * (TEXT_SIZE // 4),
    "one-path-segment-of-256-kib": "https://docs.example.com/" + "a" * TEXT_SIZE,
    "percent-escapes-in-the-path": "https://docs.example.com/" + "%25" * (TEXT_SIZE // 6),
    "many-query-pairs": "https://docs.example.com/x?" + "a=b&" * (TEXT_SIZE // 8),
    "many-semicolon-pairs": "https://docs.example.com/x?" + "a=b;" * (TEXT_SIZE // 8),
    "equals-signs-in-the-query": "https://docs.example.com/x?a" + "=" * TEXT_SIZE,
    "double-encoded-values": "https://docs.example.com/x?next=" + "%2525" * (TEXT_SIZE // 10),
    "question-marks": "https://docs.example.com/x" + "?" * TEXT_SIZE,
    "dots-in-the-path": "https://docs.example.com/" + "." * TEXT_SIZE,
    "token-prefixes-in-the-path": "https://docs.example.com/" + ("gh" + "p_") * (TEXT_SIZE // 8),
    "jwt-starts-in-the-query": "https://docs.example.com/x?a=" + (EYJ + ".") * (TEXT_SIZE // 8),
}


@pytest.mark.parametrize("url", list(HOSTILE_ADDRESSES.values()), ids=list(HOSTILE_ADDRESSES))
def test_url_problems_and_host_of_finish_in_the_limit_on_hostile_addresses(url: str) -> None:
    """AC-5. expected_behavior_source: AC-5 and plan P-1 (hosts of many labels; hostile input);
    ADR-002 decision 8 (the whole address is at most 300 characters, so every address here is
    refused, and host_of shares the splitter, so it is as fast); considerations S-7."""
    problems: list[tuple[str, ...]] = []

    assert seconds_to_run(lambda: problems.append(url_problems(url))) < TIME_LIMIT_SECONDS
    assert seconds_to_run(lambda: host_of(url)) < TIME_LIMIT_SECONDS
    assert problems[0]
