"""Team resources: the pure domain rules (task team-conventions-resources, phase P-1).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files
`adr-002-*.md` and `adr-003-*.md` under docs/design/team-conventions-resources/design/, EC-n are
the expected changes of the manifest.yaml next to them, and AC-1 to AC-8 are the acceptance
criteria of phase P-1 in docs/design/team-conventions-resources/plan.yaml.

These tests were written first, by the Tester of phase P-1, before `orqlet.domain.resources`
existed. They cover AC-1 to AC-4 and AC-8; AC-5 (the scans run in linear time) is covered by the
timed tests of test_resources_properties.py, and the line-length boundary of AC-5 is checked here.

Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003). The module under test is pure and takes plain values, so no port is involved
and no fake from tests/fakes applies (ORQLET-TEST-001).

Behaviour that the design leaves open is deliberately not pinned here:
- the exact rule names that the problem functions return (only empty versus non-empty tuples,
  non-empty names and the absence of any part of the input are checked);
- which characters of a URL path and query value the allow-list admits beyond letters, digits,
  `-`, `_`, `.`, `/`, `=`, `&`, `;` and the escape `%20` (positive cases use only those);
- what `copy_problems` does beyond the two header lines (size, hidden text and credentials are
  checked by the other functions and by `validate resources`);
- the token prefixes of `credential_problems` beyond the two best-known ones that the tests use,
  the credential words of its key=value rule and the minimum length of a token-like body;
- the base of the line numbers of `credential_problems` (the tests learn it once and require it to
  be used consistently), and what counts as a line besides a line feed.
"""

import ast
import functools
import inspect
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone

import pytest

from orqlet.domain import resources
from orqlet.domain.resources import (
    copy_path,
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

pytestmark = pytest.mark.unit


# --- helpers (shared with the other test files of this phase) ------------------------------------


def parametrized(name: str, cases: Mapping[str, object]) -> pytest.MarkDecorator:
    """`pytest.mark.parametrize` over the values of a mapping, with its keys as test ids."""
    return pytest.mark.parametrize(name, list(cases.values()), ids=list(cases))


def body(size: int) -> str:
    """A deterministic alphanumeric run of exactly `size` characters."""
    return ("aB3" * size)[:size]


def shown(problems: tuple[str, ...]) -> str:
    """Everything that a result shows, in lower case."""
    return " ".join(problems).lower()


def holds_any(text: str, *parts: str) -> bool:
    return any(part.lower() in text.lower() for part in parts)


def holds_a_part(problems: tuple[str, ...], text: str, width: int = 16) -> bool:
    """True when the problems show the whole of `text` or any `width` characters in a row of it.

    A window of 16 characters is long enough that no fixed rule name can contain one by chance.
    """
    size = min(width, len(text))
    lowered = text.lower()
    return size > 0 and any(
        lowered[start : start + size] in shown(problems) for start in range(len(lowered) - size + 1)
    )


def assert_well_formed(problems: object) -> None:
    """A tuple of non-empty rule names (EC-1 to EC-8: `-> tuple[str, ...]`)."""
    assert isinstance(problems, tuple)
    assert all(isinstance(name, str) and name for name in problems)


EYJ = "ey" + "J"  # the start of a JWT header; split so that no token-like literal exists
PEM_DASHES = "-" * 5
LITERAL = "literal-value-4f2a"  # a plain word, not shaped like any credential


# --- the addresses that the sources name ----------------------------------------------------------

DOCS = "https://docs.example.com"
GUIDES = DOCS + "/guides"
API_GUIDE = "https://docs.example.com/guides/api"  # AC-1
CONFLUENCE_STYLE = "https://wiki.example.com/pages/viewpage.action?pageId=123456"  # AC-1


def at_host(host: str) -> str:
    return f"https://{host}/guides"


def url_of_length(size: int) -> str:
    """A valid address of exactly `size` characters: short path segments, no opaque run."""
    filler = ("a" * 10 + "/") * (size // 11 + 1)
    return (DOCS + "/" + filler)[:size]


OPAQUE_32 = "aB3_" * 8  # 32 letters, digits and underscores
OPAQUE_31 = OPAQUE_32[:-1]
OPAQUE_WITH_HYPHEN_32 = "aB3-" * 8
OPAQUE_LABEL_32 = "a1b2-" * 6 + "a1"  # lower case letters, digits and hyphens, ends in a digit
OPAQUE_LABEL_31 = OPAQUE_LABEL_32[:-1]

VALID_URLS = {
    "guides-address": API_GUIDE,
    "confluence-style-with-a-page-id-query": CONFLUENCE_STYLE,
    "host-only": DOCS,
    "host-and-slash": DOCS + "/",
    "two-labels": "https://example.com/docs",
    "eight-labels": "https://a.b.c.d.e.f.g.com/docs",
    "hyphens-in-labels": "https://my-docs.example-site.com/docs",
    "digits-in-labels": "https://docs2.example.com/v2/api-3",
    "dotted-path": "https://docs.example.com/guides/v1.2/api_reference-guide.html",
    "path-with-an-escape": "https://docs.example.com/a%20b",
    "several-query-keys": GUIDES + "?q=rest&lang=en&page=2",
    "semicolon-between-safe-keys": GUIDES + "?lang=en;page=2",
    "path-segment-of-31-characters": GUIDES + "/" + OPAQUE_31,
    "query-value-of-31-characters": GUIDES + "?ref=" + OPAQUE_WITH_HYPHEN_32[:-1],
    "host-label-of-31-characters": at_host(OPAQUE_LABEL_31 + ".example.com"),
    "address-of-300-characters": url_of_length(300),
}
HOSTS_OF_VALID_URLS = {
    API_GUIDE: "docs.example.com",
    CONFLUENCE_STYLE: "wiki.example.com",
    DOCS: "docs.example.com",
    DOCS + "/": "docs.example.com",
    "https://a.b.c.d.e.f.g.com/docs": "a.b.c.d.e.f.g.com",
    "https://my-docs.example-site.com/docs?lang=en": "my-docs.example-site.com",
}

# --- the refused addresses, by rule (ADR-002 decision 8) ------------------------------------------

SCHEME_VECTORS = {
    "empty": "",
    "plain-http": "http://docs.example.com/guides",
    "other-scheme": "ftp://docs.example.com/guides",
    "no-scheme": "docs.example.com/guides",
    "scheme-relative": "//docs.example.com/guides",
    "script-scheme": "javascript:alert(1)",
    "no-host": "https:///guides",
    "scheme-only": "https://",
}
HOST_SHAPE_VECTORS = {
    "single-label": at_host("docs"),
    "nine-labels": at_host("a.b.c.d.e.f.g.h.com"),
    "label-starts-with-a-hyphen": at_host("-docs.example.com"),
    "label-ends-with-a-hyphen": at_host("docs-.example.com"),
    "punycode-label": at_host("xn--docs-9ua.example.com"),
    "empty-label": at_host("docs..example.com"),
    "leading-dot": at_host(".docs.example.com"),
    "trailing-dot": at_host("docs.example.com."),
    "upper-case-letters": at_host("Docs.Example.com"),
    "underscore": at_host("my_docs.example.com"),
    "accented-letter": at_host("d\u00f6cs.example.com"),
    "space-in-the-host": at_host("docs .example.com"),
    "tab-after-the-host": at_host("docs.example.com\t"),
}
AUTHORITY_VECTORS = {
    "port": "https://docs.example.com:8443/guides",
    "port-without-a-path": "https://docs.example.com:443",
    "user-information": "https://someone@docs.example.com/guides",
    "user-and-password": "https://someone:pw@docs.example.com/guides",
    "empty-user-information": "https://@docs.example.com/guides",
    "another-host-after-the-at-sign": "https://docs.example.com@evil.example.net/guides",
    "backslash-before-the-at-sign": "https://docs.example.com\\@evil.example.net/guides",
    "percent-sign-before-the-at-sign": "https://docs.example.com%2f@evil.example.net/guides",
    "encoded-at-sign": "https://docs.example.com%40evil.example.net/guides",
    "percent-sign-in-the-host": "https://docs%2eexample.com/guides",
    "backslash-in-the-host": "https://docs.example.com\\guides",
}
RESERVED_HOST_VECTORS = {
    "bare-localhost": at_host("localhost"),
    "upper-case-localhost": at_host("LOCALHOST"),
    "subdomain-of-localhost": at_host("app.localhost"),
    "upper-case-subdomain-of-localhost": at_host("app.LOCALHOST"),
    "local": at_host("printer.local"),
    "localdomain": at_host("box.localdomain"),
    "short-ip-127-1": at_host("127.1"),
    "bare-0x-last-label": at_host("127.1.0x"),
    "docs-with-a-bare-0x-label": at_host("docs.0x"),
    "ten-with-a-bare-0x-label": at_host("10.0.0.0x"),
    "short-ip-10-1": at_host("10.1"),
    "dotted-quad": at_host("127.0.0.1"),
    "private-dotted-quad": at_host("192.168.1.1"),
    "hex-dotted-quad": at_host("0xa9.0xfe.0xa9.0xfe"),
    "hex-last-label": at_host("docs.0x7f"),
    "decimal-ip": at_host("2130706433"),
    "last-label-without-a-letter": at_host("docs.example.123"),
}
WILDCARD_VECTORS = {
    "nip-io-with-labels": at_host("a.b.nip.io"),
    "nip-io-with-an-ip": at_host("127-0-0-1.nip.io"),
    "nip-io-itself": at_host("nip.io"),
    "sslip-io": at_host("app.sslip.io"),
    "xip-io": at_host("app.xip.io"),
    "localtest-me": at_host("app.localtest.me"),
    "lvh-me": at_host("app.lvh.me"),
    "home-arpa": at_host("router.home.arpa"),
    "bit-ly": "https://bit.ly/abc",
    "t-co": "https://t.co/abc",
    "tinyurl-com": "https://tinyurl.com/abc",
}
FRAGMENT_AND_VARIABLE_VECTORS = {
    "fragment": GUIDES + "#top",
    "empty-fragment": GUIDES + "#",
    "fragment-after-a-query": GUIDES + "?lang=en#top",
    "dollar-brace-in-the-path": GUIDES + "/${section}",
    "dollar-brace-in-a-query-value": GUIDES + "?lang=${LANG}",
    "dollar-brace-in-the-host": at_host("${HOST}.example.com"),
}
PATH_VECTORS = {
    "space": GUIDES + "/a b",
    "backslash": GUIDES + "/a\\b",
    "angle-bracket": GUIDES + "/<script>",
    "double-quote": GUIDES + '/a"b',
    "nul": GUIDES + "/a\x00b",
    "trailing-newline": GUIDES + "\n",
    "accented-letter": GUIDES + "/caf\u00e9",
    "right-to-left-override": GUIDES + "/a\u202eb",
    "dollar": GUIDES + "/a$b",
    "apostrophe": GUIDES + "/a'b",
    "exclamation-mark": GUIDES + "/a!b",
    "star": GUIDES + "/a*b",
    "path-parameter": GUIDES + "/a;jsessionid=x",
}
OPAQUE_VECTORS = {
    "path-segment-of-32-characters": GUIDES + "/" + OPAQUE_32,
    "path-segment-of-32-letters": GUIDES + "/" + "a" * 32,
    "path-segment-of-64-hex-digits": GUIDES + "/" + "0123456789abcdef" * 4,
    "opaque-segment-in-the-middle": GUIDES + "/" + OPAQUE_32 + "/more",
    "query-value-of-32-characters": GUIDES + "?ref=" + OPAQUE_WITH_HYPHEN_32,
    "query-value-of-32-letters": GUIDES + "?ref=" + "a" * 32,
    "host-label-of-32-characters": at_host(OPAQUE_LABEL_32 + ".example.com"),
    "host-label-of-32-letters": at_host("a" * 32 + ".example.com"),
}
OPEN_REDIRECT_VECTORS = {
    "double-encoded-open-redirect": GUIDES + "?next=https%253A%252F%252Fevil.example.net%252Fx",
    "double-encoded-scheme-relative": GUIDES + "?redirect=%252F%252Fevil.example.net",
    "single-encoded-open-redirect": GUIDES + "?next=https%3A%2F%2Fevil.example.net",
    "plain-open-redirect": GUIDES + "?next=https://evil.example.net",
    "scheme-relative-open-redirect": GUIDES + "?next=//evil.example.net",
    "slash-backslash-open-redirect": GUIDES + "?next=/%5Cevil.example.net",
    "double-backslash-open-redirect": GUIDES + "?next=%5C%5Cevil.example.net",
}

CREDENTIAL_STEMS = (
    "token",
    "secret",
    "passw",
    "pwd",
    "signature",
    "auth",
    "session",
    "jwt",
    "ticket",
    "otp",
    "credential",
    "bearer",
    "private",
)
KEYS_ENDING_IN_KEY_OR_SIG = ("key", "api_key", "apikey", "x-api-key", "sig", "x-sig")
EXACT_KEYS = ("sid", "code")
TRACKING_KEYS = ("utm", "fbclid", "gclid", "mceid", "mkttok")
QUERY_KEY_VECTORS = {
    "x-amz-signature": GUIDES + "?X-Amz-Signature=abc",  # the vectors that the plan names
    "private-token": GUIDES + "?private_token=abc",
    **{f"stem-{stem}": f"{GUIDES}?{stem}=1" for stem in CREDENTIAL_STEMS},
    **{f"stem-inside-a-key-{stem}": f"{GUIDES}?my-{stem}-value=1" for stem in CREDENTIAL_STEMS},
    **{f"ends-in-{key}": f"{GUIDES}?{key}=1" for key in KEYS_ENDING_IN_KEY_OR_SIG},
    **{f"is-{key}": f"{GUIDES}?{key}=1" for key in EXACT_KEYS},
    **{f"tracking-{key}": f"{GUIDES}?{key}=1" for key in TRACKING_KEYS},
    "upper-case-key": GUIDES + "?TOKEN=1",
    "percent-encoded-letter": GUIDES + "?to%6Ben=1",
    "percent-encoded-upper-case-letter": GUIDES + "?T%4FKEN=1",
    "percent-encoded-underscore": GUIDES + "?api%5Fkey=1",
    "dot-in-the-key": GUIDES + "?access.token=1",
    "hyphen-splits-the-word": GUIDES + "?se-cret=1",
    "underscore-splits-the-word": GUIDES + "?pass_word=1",
    "dot-splits-the-word": GUIDES + "?to.ken=1",
    "second-key-after-an-ampersand": GUIDES + "?lang=en&token=1",
    "second-key-after-a-semicolon": GUIDES + "?lang=en;token=1",
}

REFUSED_URL_GROUPS = {
    "scheme": SCHEME_VECTORS,
    "host-shape": HOST_SHAPE_VECTORS,
    "authority": AUTHORITY_VECTORS,
    "reserved-host": RESERVED_HOST_VECTORS,
    "wildcard": WILDCARD_VECTORS,
    "fragment-or-variable": FRAGMENT_AND_VARIABLE_VECTORS,
    "path": PATH_VECTORS,
    "opaque": OPAQUE_VECTORS,
    "open-redirect": OPEN_REDIRECT_VECTORS,
    "query-key": QUERY_KEY_VECTORS,
    "length": {"address-of-301-characters": url_of_length(301)},
}
ALL_REFUSED_URLS = {
    f"{group}-{name}": url
    for group, vectors in REFUSED_URL_GROUPS.items()
    for name, url in vectors.items()
}

INTERNAL_LOOKING_HOSTS = {
    "metadata-google-internal": "https://metadata.google.internal/computeMetadata/v1/",
    "corp": "https://wiki.example.corp/home",
    "lan": "https://nas.example.lan/docs",
    "intranet": "https://wiki.example.intranet/docs",
}


# --- AC-1: url_problems ---------------------------------------------------------------------------


@parametrized("url", VALID_URLS)
def test_an_address_within_the_grammar_has_no_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (https, a host, an optional path and
    query; every limit at its boundary is accepted: 31-character runs, 300 characters, eight
    labels)."""
    assert url_problems(url) == ()


def test_the_two_addresses_that_ac_1_names_have_no_problem() -> None:
    """AC-1. expected_behavior_source: AC-1 ("accepts https://docs.example.com/guides/api and a
    Confluence-style address with a pageId query")."""
    assert url_problems("https://docs.example.com/guides/api") == ()
    assert url_problems("https://wiki.example.com/pages/viewpage.action?pageId=123456") == ()


@parametrized("url", INTERNAL_LOOKING_HOSTS)
def test_an_internal_looking_host_is_not_a_problem_of_the_address_alone(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (an intranet host such as
    metadata.google.internal is legitimate for a login entry; the rule that a public entry cannot
    use `internal`, `corp`, `lan`, `home` or `intranet` is "a cross-field rule of the contract
    that url_problems alone cannot see", so the contract of phase P-2 owns that test)."""
    assert url_problems(url) == ()


@parametrized("url", SCHEME_VECTORS)
def test_an_address_that_is_not_an_https_address_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 ("accepts only https:// followed by a
    host")."""
    assert url_problems(url)


@parametrized("url", HOST_SHAPE_VECTORS)
def test_a_host_outside_the_label_grammar_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (lower case letters, digits and hyphens
    in two to eight labels; no label starts or ends with a hyphen or starts with xn--; no empty
    label, trailing dot or whitespace)."""
    assert url_problems(url)


@parametrized("url", AUTHORITY_VECTORS)
def test_a_port_user_information_backslash_or_percent_sign_in_the_authority_is_a_problem(
    url: str,
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 ("no trailing dot, port, user
    information, backslash, percent sign or whitespace"); AC-1 and plan P-1 (a backslash and a
    percent sign before the at sign, user information, a port)."""
    assert url_problems(url)


@parametrized("url", RESERVED_HOST_VECTORS)
def test_a_reserved_or_numeric_host_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (the last label contains a letter, is not
    localhost, local or localdomain and is not 0x plus hex digits, so 127.1, 10.1 and
    0xa9.0xfe.0xa9.0xfe fail; LOCALHOST fails the lower case rule)."""
    assert url_problems(url)


@parametrized("url", WILDCARD_VECTORS)
def test_a_wildcard_dns_name_or_a_public_redirector_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (the last two labels are not on the
    closed list nip.io, sslip.io, xip.io, localtest.me, lvh.me, home.arpa, bit.ly, t.co and
    tinyurl.com; the design calls the list an example, so only its named names are tested)."""
    assert url_problems(url)


@parametrized("url", FRAGMENT_AND_VARIABLE_VECTORS)
def test_a_fragment_or_a_dollar_brace_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 ("There is no fragment and no ${")."""
    assert url_problems(url)


@parametrized("url", PATH_VECTORS)
def test_a_path_character_outside_the_url_allow_list_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 ("the path uses an allow-list of URL
    characters"); a space, a backslash, an angle bracket, a quote, a control character and a
    non-ASCII character are in no allow-list of URL characters."""
    assert url_problems(url)


@parametrized("url", OPAQUE_VECTORS)
def test_an_opaque_run_in_a_path_a_query_value_or_a_host_label_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (no path segment of 32 or more letters,
    digits and underscores; no query value or host label of 32 or more letters, digits,
    underscores and hyphens; a long opaque token)."""
    assert url_problems(url)


@parametrized("url", OPEN_REDIRECT_VECTORS)
def test_a_query_value_that_decodes_to_a_double_slash_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (a query value is percent-decoded twice
    and refused when it then contains `//`: an open-redirect parameter)."""
    assert url_problems(url)


@parametrized("url", QUERY_KEY_VECTORS)
def test_a_credential_or_tracking_query_key_is_a_problem(url: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (a key is percent-decoded, lower-cased,
    stripped of `-`, `_` and `.`, split at `&` and `;`, and refused when it contains a credential
    stem, ends in key or sig, is sid or code, or is a tracking key); AC-1 and plan P-1
    (X-Amz-Signature, private_token)."""
    assert url_problems(url)


def test_an_address_of_301_characters_is_a_problem_and_one_of_300_is_not() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 ("the whole address is at most 300
    characters"); component rule 5 (an address up to 300)."""
    assert len(url_of_length(300)) == 300
    assert url_problems(url_of_length(300)) == ()
    assert url_problems(url_of_length(301))


@pytest.mark.parametrize("segment", [OPAQUE_31, "a" * 31])
def test_a_path_segment_of_31_characters_is_not_opaque(segment: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (a segment of 32 or more is refused; the
    boundary is 32)."""
    assert url_problems(GUIDES + "/" + segment) == ()


def test_a_long_path_segment_with_hyphens_is_not_an_opaque_run() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (the path rule counts letters, digits
    and underscores only; the query and host rules add the hyphen, so a readable hyphenated
    title is not "a segment made only of letters, digits and underscores")."""
    slug = "how-to-design-a-versioned-public-rest-endpoint"

    assert len(slug) > 32
    assert url_problems(GUIDES + "/" + slug) == ()


def test_the_same_host_in_upper_case_is_a_problem_and_in_lower_case_is_not() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (the host is lower case letters); the
    plan names LOCALHOST."""
    assert url_problems(at_host("docs.example.com")) == ()
    assert url_problems(at_host("DOCS.EXAMPLE.COM"))


def test_every_refused_address_gives_a_tuple_of_rule_names() -> None:
    """AC-1. expected_behavior_source: AC-1 ("returns the names of the rules that an address
    breaks ... a tuple"); EC-1 (`-> tuple[str, ...]`)."""
    for url in ALL_REFUSED_URLS.values():
        problems = url_problems(url)
        assert_well_formed(problems)
        assert problems, url


@parametrized("url", ALL_REFUSED_URLS)
def test_no_problem_of_a_refused_address_shows_a_part_of_it(url: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("it never contains the input"); ORQLET-SEC-003."""
    assert not holds_a_part(url_problems(url), url)


@pytest.mark.parametrize(
    "template",
    [
        "https://{marker}@docs.example.com/guides",
        "https://docs.example.com/guides?{marker}_token=1",
        "https://docs.example.com/guides?next=https%253A%252F%252F{marker}.example.net",
        "https://docs.example.com/{marker}#top",
        "https://{marker}.nip.io/guides",
    ],
    ids=["user-information", "query-key", "open-redirect", "fragment", "wildcard"],
)
def test_a_marker_planted_in_a_refused_address_is_not_shown(template: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("it never contains the input"); ORQLET-SEC-003."""
    marker = "zq7marker5d1e"
    problems = url_problems(template.format(marker=marker))

    assert problems
    assert not holds_any(shown(problems), marker, marker[3:10])


def test_a_credential_shaped_address_is_refused_and_never_shown() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 (the address is scanned with
    credential_problems; user information is refused); ORQLET-SEC-003."""
    token = "gh" + "p_" + body(36)
    url = "https://" + token + "@docs.example.com/guides?lang=en&" + token + "=1"

    problems = url_problems(url)

    assert problems
    assert not holds_any(shown(problems), token, token[-20:])


# --- AC-2: text_problems --------------------------------------------------------------------------

LIMIT = 80
FORBIDDEN_SEQUENCES = {
    "scheme-separator": "see https://example.com",
    "bare-scheme-separator": "a://b",
    "link-close-and-open": "[docs](page)",
    "html-comment-open": "a <!-- b",
    "html-comment-close": "a --> b",
    "backtick": "run `rm` now",
    "single-backtick": "a`b",
    "less-than": "a<b",
    "greater-than": "a>b",
    "pseudo-tag": "feature/<ticket>",
    "at-sign-import": "see @docs/page",
    "at-sign-home-import": "see @~/.ssh/key",
    "at-sign-alone": "@",
}
HIDDEN_CHARACTERS = {
    "right-to-left-override-u202e": "a\u202eb",
    "zero-width-space-u200b": "a\u200bb",
    "tag-letter-ue0041": "a\U000e0041b",
    "line-separator-u2028": "a\u2028b",
    "variation-selector-ufe0f": "a\ufe0fb",
    "braille-blank-u2800": "a\u2800b",
    "no-break-space-u00a0": "a\u00a0b",
    "byte-order-mark-ufeff": "\ufeffabc",
    "first-c1-control-u0080": "a\u0080b",
    "next-line-u0085": "a\u0085b",
    "delete-u007f": "a\x7fb",
    "accented-letter-u00e9": "caf\u00e9",
    "fullwidth-letter-uff21": "\uff21bc",
    "emoji-u1f600": "a\U0001f600b",
    "lone-surrogate-ud800": "a\ud800b",
}
CONTROL_CHARACTERS = {
    "line-feed": "a\nb",
    "trailing-line-feed": "abc\n",
    "carriage-return": "a\rb",
    "tab": "a\tb",
    "nul": "a\x00b",
    "escape-sequence": "a\x1b[31mb",
    "unit-separator": "a\x1fb",
    "form-feed": "a\x0cb",
    "vertical-tab": "a\x0bb",
}
ALLOWED_PRINTABLE = "".join(
    chr(code_point) for code_point in range(0x20, 0x7F) if chr(code_point) not in "<>`@"
)
VALID_TEXTS = {
    "branch-example-of-the-design": "feature/TICKET-slug",
    "plain-sentence": "Use when changing public REST endpoints (v2); see feature/TICKET-slug.",
    "one-character": "a",
    "every-allowed-printable-character": ALLOWED_PRINTABLE,
}


@parametrized("value", VALID_TEXTS)
def test_printable_ascii_on_one_line_within_the_limit_has_no_problem(value: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 8 (ASCII only, U+0020 to U+007E, one line,
    none of the listed sequences, no backtick, neither < nor >; `feature/TICKET-slug` is the
    spelling that the design recommends)."""
    assert text_problems(value, 200) == ()


@parametrized("value", FORBIDDEN_SEQUENCES)
def test_a_forbidden_sequence_or_character_is_a_problem(value: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 8 (none of `://`, `](`, `<!--`, `-->`; no
    backtick; neither `<` nor `>`); AC-2."""
    assert text_problems(value, 200)


@parametrized("value", HIDDEN_CHARACTERS)
def test_a_code_point_above_u_007e_is_a_problem(value: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 8 (ASCII only: it removes every invisible,
    bidirectional, variation-selector, filler and look-alike code point at once); AC-2 ("every
    code point above U+007E"); plan P-1 (U+202E, U+200B, U+E0041, U+2028, U+FE0F, U+2800)."""
    assert text_problems(value, 200)


@parametrized("value", CONTROL_CHARACTERS)
def test_a_control_character_or_a_second_line_is_a_problem(value: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 8 (printable characters U+0020 to U+007E,
    on one line); AC-2 ("only printable ASCII on one line")."""
    assert text_problems(value, 200)


@pytest.mark.parametrize("limit", [1, LIMIT, 200])
def test_a_text_of_exactly_the_limit_is_accepted_and_one_more_is_not(limit: int) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (title up to 80, note up to 200
    characters) and AC-2 ("within the limit")."""
    assert text_problems("a" * limit, limit) == ()
    assert text_problems("a" * (limit + 1), limit)


def test_text_that_breaks_several_rules_gives_non_empty_rule_names() -> None:
    """AC-2. expected_behavior_source: EC-2 (`-> tuple[str, ...]`); AC-2."""
    problems = text_problems("a\u202e<b>`c`\n" + "x" * 300, LIMIT)

    assert_well_formed(problems)
    assert problems


@pytest.mark.parametrize(
    "element",
    [*FORBIDDEN_SEQUENCES.values(), *HIDDEN_CHARACTERS.values()],
    ids=[*FORBIDDEN_SEQUENCES, *HIDDEN_CHARACTERS],
)
def test_no_problem_of_a_text_shows_a_part_of_it(element: str) -> None:
    """AC-2. expected_behavior_source: ORQLET-SEC-003 (every problem is a fixed rule name and
    holds no input value; ADR-002 decision 8 and the plan's file operation for resources.py)."""
    value = "zq7marker-head-5d1e " + element + " zq7marker-tail-9a3c"
    problems = text_problems(value, 200)

    assert problems
    assert not holds_any(shown(problems), "zq7marker-head-5d1e", "zq7marker-tail-9a3c")
    assert not holds_a_part(problems, value)


# --- AC-2: resource_id_problems -------------------------------------------------------------------

WINDOWS_DEVICE_NAMES = (
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{digit}" for digit in range(1, 10)),
    *(f"lpt{digit}" for digit in range(1, 10)),
)
VALID_IDS = [
    "a",
    "tool",
    "api-guidelines",
    "a1",
    "a-1-b",
    "team-docs-2",
    "a" + "b" * 31,  # 32 characters
    "console",
    "auxiliary",
    "null",
]
BROKEN_IDS = {
    "empty": "",
    "upper-case": "Api",
    "all-upper-case": "API",
    "starts-with-a-digit": "1api",
    "starts-with-a-hyphen": "-api",
    "trailing-hyphen": "api-",
    "doubled-hyphen": "api--guide",
    "hyphen-only": "-",
    "underscore": "api_guide",
    "space": "api guide",
    "dot": "api.guide",
    "slash": "api/guide",
    "backslash": "api\\guide",
    "parent-directory": "..",
    "thirty-three-characters": "a" * 33,
    "trailing-newline": "api\n",
    "leading-newline": "\napi",
    "kelvin-sign": "\u212a",
    "accented-letter": "caf\u00e9",
    "fullwidth-letter": "\uff41pi",
    "arabic-indic-digit": "a\u0661",
}


@pytest.mark.parametrize("resource_id", VALID_IDS)
def test_an_id_of_the_grammar_has_no_problem(resource_id: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (`[a-z][a-z0-9]*(-[a-z0-9]+)*`, up to 32
    characters); a word that merely starts with a device name is not a device name."""
    assert resource_id_problems(resource_id) == ()


@parametrized("resource_id", BROKEN_IDS)
def test_an_id_outside_the_grammar_is_a_problem(resource_id: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (matched with fullmatch, so no trailing
    or doubled hyphen and no trailing newline; ASCII lower case only; at most 32 characters)."""
    assert resource_id_problems(resource_id)


@pytest.mark.parametrize("name", WINDOWS_DEVICE_NAMES)
def test_every_windows_device_name_is_a_problem(name: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (not a Windows device name: con, prn,
    aux, nul, com1 to com9, lpt1 to lpt9, because the id becomes a file name)."""
    assert resource_id_problems(name)


def test_the_problems_of_an_id_hold_no_part_of_it() -> None:
    """AC-2. expected_behavior_source: ORQLET-SEC-003 (a fixed rule name holds no input value)."""
    value = "Zq7-marker-id-91c2--"
    problems = resource_id_problems(value)

    assert problems
    assert_well_formed(problems)
    assert not holds_any(shown(problems), "zq7-marker-id-91c2")


# --- AC-2: glob_problems --------------------------------------------------------------------------

VALID_GLOBS = [
    "src/api/**",
    "**/*.py",
    "docs/**/*.md",
    "src/**/api/*.py",
    "*.md",
    "README.md",
    "api/v?/*.yaml",
    "src/api-gateway/**",
    "a",
    "a" * 120,
]
BROKEN_GLOBS = {
    # Rework round 1 of phase P-6 (security review F-1): a glob reaches the catalogue skill.
    "space": "src/my dir/*.py",
    "at-sign": "src/** @notes/secret",
    "backtick": "src/`x`/*.py",
    "less-than": "src/<x>/*.py",
    "greater-than": "src/x>/*.py",
    "single-star": "*",
    "double-star": "**",
    "star-slash-star": "*/*",
    "double-star-slash-star": "**/*",
    "double-star-twice": "**/**",
    "question-mark": "?",
    "slash-only": "/",
    "stars-slashes-and-a-question-mark": "**/*/?/",
    "empty": "",
    "parent-only": "..",
    "parent-first": "../secrets/*",
    "parent-in-the-middle": "src/../secrets/*",
    "parent-last": "src/..",
    "leading-slash": "/src/**",
    "leading-backslash": "\\src\\**",
    "negation": "!src/**",
    "negation-inside": "src/!x/*.py",
    "open-and-close-brace": "src/*.{py,pyi}",
    "open-brace-only": "{src/*.py",
    "close-brace-only": "src/*.py}",
    "one-hundred-twenty-one-characters": "a" * 121,
    "accented-letter": "src/caf\u00e9/*",
    "right-to-left-override": "src/\u202e/*",
    "line-feed": "src/a\nb/*",
    "comma": "src/a,b/*",
    "star-dot-star": "*.*",
    "double-star-slash-star-dot-star": "**/*.*",
    "tab": "src/a\tb/*",
    "nul": "src/a\x00b",
}


@pytest.mark.parametrize("pattern", VALID_GLOBS)
def test_a_glob_that_names_something_has_no_problem(pattern: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (`glob_problems` rules; at most 120
    characters; at least one character that is not `*`, `?` or `/`)."""
    assert glob_problems(pattern) == ()


@parametrized("pattern", BROKEN_GLOBS)
def test_a_glob_that_breaks_a_rule_is_a_problem(pattern: str) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (ASCII printable, at most 120
    characters, no leading `/` or `\\`, no `..` segment, no `!`, no `{` or `}`, and at least one
    character that is not `*`, `?` or `/`, so that no glob matches everything); AC-2."""
    assert glob_problems(pattern)


def test_the_problems_of_a_glob_hold_no_part_of_it() -> None:
    """AC-2. expected_behavior_source: ORQLET-SEC-003 (a fixed rule name holds no input value)."""
    value = "zq7marker-glob-3b8a/../{x}"
    problems = glob_problems(value)

    assert problems
    assert_well_formed(problems)
    assert not holds_any(shown(problems), "zq7marker-glob-3b8a")


# --- AC-3: copy_path, host_of, uncovered_names, is_stale ------------------------------------------


@pytest.mark.parametrize("resource_id", ["api-guidelines", "a", "pytest", "a" + "b" * 31])
def test_the_copy_of_an_entry_is_at_docs_resources_id_md(resource_id: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("copy_path(id) is docs/resources/<id>.md");
    ADR-002 decision 1 ("the path is always docs/resources/<id>.md")."""
    assert copy_path(resource_id) == f"docs/resources/{resource_id}.md"


@pytest.mark.parametrize(("url", "host"), list(HOSTS_OF_VALID_URLS.items()))
def test_host_of_returns_the_host_that_url_problems_checked(url: str, host: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("host_of returns the host that url_problems
    checked"); ADR-002 decision 8 (the host that a reviewer sees on its own line)."""
    assert url_problems(url) == ()
    assert host_of(url) == host


def test_host_of_leaves_out_the_path_and_the_query() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 8 ("the host is printed on its own line
    wherever an address is shown")."""
    host = host_of("https://docs.example.com/guides?pageId=1")

    assert host == "docs.example.com"
    assert "/" not in host
    assert "?" not in host


def normalised(names: tuple[str, ...]) -> set[str]:
    return {name.strip().casefold() for name in names}


def test_uncovered_names_are_the_technologies_that_no_tool_names() -> None:
    """AC-3. expected_behavior_source: AC-3 ("uncovered_names compares after trimming and case
    folding"); ADR-002 decision 7 (`--uncovered` prints the technologies that no entry names as
    its tool)."""
    result = uncovered_names(["Python", "pytest", "FastAPI", "Django"], ["pytest", "fastapi"])

    assert isinstance(result, tuple)
    assert normalised(result) == {"python", "django"}


def test_uncovered_names_trims_both_sides_before_comparing() -> None:
    """AC-3. expected_behavior_source: AC-3 (trimming); ADR-002 decision 7."""
    result = uncovered_names(["  pytest ", "ruff"], [" pytest\t", "\nruff  "])

    assert result == ()


def test_uncovered_names_folds_the_case_of_both_sides() -> None:
    """AC-3. expected_behavior_source: AC-3 (case folding, which maps U+00DF to `ss` where lower
    casing does not); ADR-002 decision 7."""
    assert uncovered_names(["PyTest", "Stra\u00dfe"], ["pYTEST", "STRASSE"]) == ()


@pytest.mark.parametrize(
    ("technologies", "covered", "expected"),
    [
        ([], [], set()),
        ([], ["pytest"], set()),
        (["pytest", "ruff"], [], {"pytest", "ruff"}),
        (["pytest", "ruff"], ["pytest", "ruff", "mypy"], set()),
    ],
    ids=["nothing-at-all", "nothing-to-cover", "nothing-covers", "everything-covered"],
)
def test_uncovered_names_at_the_edges(
    technologies: list[str], covered: list[str], expected: set[str]
) -> None:
    """AC-3. expected_behavior_source: AC-3 and ADR-002 decision 7 (the technologies that no entry
    names)."""
    assert normalised(uncovered_names(technologies, covered)) == expected


RETRIEVED = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
ONE_SECOND = timedelta(seconds=1)


@pytest.mark.parametrize("ttl_days", [1, 30, 365])
def test_a_copy_inside_its_time_to_live_is_not_stale(ttl_days: int) -> None:
    """AC-3. expected_behavior_source: AC-3 ("compares ttl_days"); ADR-002 decision 9 (doctor warns
    when retrieved_at plus ttl_days has passed). The instant of equality is not pinned."""
    now = RETRIEVED + timedelta(days=ttl_days) - ONE_SECOND

    assert is_stale(RETRIEVED, ttl_days, now) is False


@pytest.mark.parametrize("ttl_days", [1, 30, 365])
def test_a_copy_past_its_time_to_live_is_stale(ttl_days: int) -> None:
    """AC-3. expected_behavior_source: AC-3 ("compares ttl_days"); ADR-002 decision 9."""
    now = RETRIEVED + timedelta(days=ttl_days) + ONE_SECOND

    assert is_stale(RETRIEVED, ttl_days, now) is True


def test_the_same_age_is_stale_for_a_short_time_to_live_and_fresh_for_a_long_one() -> None:
    """AC-3. expected_behavior_source: AC-3 ("compares ttl_days")."""
    now = RETRIEVED + timedelta(days=2)

    assert is_stale(RETRIEVED, 1, now) is True
    assert is_stale(RETRIEVED, 365, now) is False


def test_a_deadline_beyond_the_largest_datetime_is_not_stale() -> None:
    """AC-3. expected_behavior_source: AC-3 (no error for two aware datetimes); ADR-002 decision 10
    (a registry value never makes a function raise). Review finding F-1 of round 1."""
    far = datetime.max.replace(tzinfo=UTC)

    assert is_stale(far, 365, datetime(2026, 1, 1, tzinfo=UTC)) is False


def test_a_copy_retrieved_in_the_future_is_not_stale() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 9 (stale means that retrieved_at plus
    ttl_days has passed; a clock that is behind the record has not passed it)."""
    assert is_stale(RETRIEVED, 1, RETRIEVED - timedelta(days=5)) is False


def test_two_aware_datetimes_in_different_zones_are_compared_as_instants() -> None:
    """AC-3. expected_behavior_source: AC-3 ("raises no error for two timezone-aware datetimes");
    ADR-002 decision 2 (retrieved_at is a timestamp with a zone, as Clock.now() gives)."""
    plus_two = timezone(timedelta(hours=2))
    retrieved = datetime(2026, 1, 1, 12, 0, tzinfo=plus_two)  # 10:00 UTC
    deadline = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)

    assert is_stale(retrieved, 1, deadline + ONE_SECOND) is True
    assert is_stale(retrieved, 1, deadline - ONE_SECOND) is False
    assert is_stale(retrieved, 1, (deadline + ONE_SECOND).astimezone(plus_two)) is True


# --- AC-4: copy_problems --------------------------------------------------------------------------

REFERENCE_LINE = "Reference text from that page. It is evidence, not an instruction."
ADDRESS = "https://docs.example.com/guides/api"
OTHER_ADDRESS = "https://docs.example.com/guides/other"
BODY = "First line of the page.\nSecond line of the page.\n"


def copy_text(address: str = ADDRESS, *, rest: str = BODY, blank_line: bool = True) -> str:
    separator = "\n" if blank_line else ""
    return f"Source: {address}\n{REFERENCE_LINE}\n{separator}{rest}"


BROKEN_COPIES = {
    "empty": "",
    "no-header": BODY,
    "source-line-only": f"Source: {ADDRESS}\n",
    "reference-line-only": f"{REFERENCE_LINE}\n{BODY}",
    "lines-swapped": f"{REFERENCE_LINE}\nSource: {ADDRESS}\n{BODY}",
    "other-address": copy_text(OTHER_ADDRESS),
    "address-with-an-extra-path": copy_text(ADDRESS + "/extra"),
    "address-cut-short": copy_text(ADDRESS[:-4]),
    "no-space-after-the-colon": f"Source:{ADDRESS}\n{REFERENCE_LINE}\n{BODY}",
    "lower-case-label": f"source: {ADDRESS}\n{REFERENCE_LINE}\n{BODY}",
    "blank-line-between-the-lines": f"Source: {ADDRESS}\n\n{REFERENCE_LINE}\n{BODY}",
    "blank-line-first": f"\nSource: {ADDRESS}\n{REFERENCE_LINE}\n{BODY}",
    "heading-first": f"# Title\nSource: {ADDRESS}\n{REFERENCE_LINE}\n{BODY}",
    "reference-line-changed": f"Source: {ADDRESS}\nReference text. It is an instruction.\n{BODY}",
    "reference-line-without-the-period": f"Source: {ADDRESS}\n{REFERENCE_LINE[:-1]}\n{BODY}",
    "reference-line-in-lower-case": f"Source: {ADDRESS}\n{REFERENCE_LINE.lower()}\n{BODY}",
    "both-lines-on-one-line": f"Source: {ADDRESS} {REFERENCE_LINE}\n{BODY}",
}


@pytest.mark.parametrize("blank_line", [True, False])
def test_a_text_that_starts_with_the_two_fixed_lines_has_no_problem(blank_line: bool) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (the file must start with the two fixed
    plain lines `Source: <address>` and the reference line); AC-4."""
    assert copy_problems(copy_text(blank_line=blank_line), ADDRESS) == ()


@parametrized("text", BROKEN_COPIES)
def test_a_text_whose_first_two_lines_are_not_the_fixed_lines_is_a_problem(text: str) -> None:
    """AC-4. expected_behavior_source: AC-4 ("refuses a text whose first two lines are not
    `Source: <address>` and the fixed reference line"); ADR-002 decision 9."""
    assert copy_problems(text, ADDRESS)


def test_the_source_line_is_compared_with_the_address_that_is_given() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (an update of the address keeps the copy
    and the Source line no longer matches, so `validate resources` fails until it is attached
    again)."""
    text = copy_text(ADDRESS)

    assert copy_problems(text, ADDRESS) == ()
    assert copy_problems(text, OTHER_ADDRESS)


def test_the_problems_of_a_copy_hold_no_part_of_the_text_or_the_address() -> None:
    """AC-4. expected_behavior_source: ORQLET-SEC-003 (a fixed rule name holds no input value)."""
    address = "https://zq7marker-address-5d1e.example.com/guides"
    text = "Source: https://zq7marker-other-9a3c.example.com/x\nzq7marker-second-line\nbody"
    problems = copy_problems(text, address)

    assert problems
    assert_well_formed(problems)
    assert not holds_any(
        shown(problems), "zq7marker-address-5d1e", "zq7marker-other-9a3c", "zq7marker-second-line"
    )


# --- AC-4: hidden_text_problems -------------------------------------------------------------------

HIDDEN_RANGES = {  # ADR-002 decision 9, one entry per range; tab and line feed are carved out
    "c0-controls-except-tab-and-line-feed": (0x0000, 0x001F),
    "delete-and-c1-controls": (0x007F, 0x009F),
    "soft-hyphen": (0x00AD, 0x00AD),
    "combining-grapheme-joiner": (0x034F, 0x034F),
    "arabic-letter-mark": (0x061C, 0x061C),
    "hangul-choseong-and-jungseong-fillers": (0x115F, 0x1160),
    "khmer-inherent-vowels": (0x17B4, 0x17B5),
    "mongolian-variation-selectors": (0x180B, 0x180F),
    "zero-width-and-direction-marks": (0x200B, 0x200F),
    "line-separator-to-right-to-left-override": (0x2028, 0x202E),
    "word-joiner-to-nominal-digit-shapes": (0x2060, 0x206F),
    "braille-pattern-blank": (0x2800, 0x2800),
    "hangul-filler": (0x3164, 0x3164),
    "surrogates": (0xD800, 0xDFFF),
    "private-use-area": (0xE000, 0xF8FF),
    "variation-selectors": (0xFE00, 0xFE0F),
    "byte-order-mark": (0xFEFF, 0xFEFF),
    "halfwidth-hangul-filler": (0xFFA0, 0xFFA0),
    "specials-and-interlinear-annotation": (0xFFF0, 0xFFFC),
    "tags": (0xE0000, 0xE007F),
    "variation-selectors-supplement": (0xE0100, 0xE01EF),
    "supplementary-private-use-plane-15": (0xF0000, 0xFFFFD),
    "supplementary-private-use-plane-16": (0x100000, 0x10FFFD),
}
TAB, LINE_FEED = 0x09, 0x0A
# The design does not say whether the non-characters (U+FDD0 to U+FDEF and the last two code points
# of every plane, which include the end of each supplementary private use plane) belong to the
# table, so no test relies on them.
UNSPECIFIED_CODE_POINTS = frozenset(
    {*range(0xFDD0, 0xFDF0)}
    | {plane * 0x10000 + offset for plane in range(17) for offset in (0xFFFE, 0xFFFF)}
)
LAST_CODE_POINT = 0x10FFFF


def is_hidden(code_point: int) -> bool:
    """Whether the table of ADR-002 decision 9 holds the code point."""
    if code_point in (TAB, LINE_FEED):
        return False
    return any(first <= code_point <= last for first, last in HIDDEN_RANGES.values())


def sampled(first: int, last: int) -> list[int]:
    """Every code point of a small range; the edges, middle and a prime stride of a large one."""
    if last - first < 7000:
        return [
            code_point
            for code_point in range(first, last + 1)
            if not (TAB <= code_point <= LINE_FEED)
        ]
    return sorted({first, last, (first + last) // 2, *range(first, last + 1, 251)})


def hidden_in_the_middle(code_point: int) -> tuple[str, ...]:
    problems: tuple[str, ...] = hidden_text_problems("a" + chr(code_point) + "b")
    return problems


@pytest.mark.parametrize(("first", "last"), list(HIDDEN_RANGES.values()), ids=list(HIDDEN_RANGES))
def test_every_code_point_of_a_range_of_the_table_is_hidden_text(first: int, last: int) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 ("each range has a test"; the numeric
    table); AC-4 ("one test per range"). Small ranges are swept whole; the large ones at their
    edges, their middle and a prime stride."""
    missed = [
        f"U+{code_point:04X}"
        for code_point in sampled(first, last)
        if not hidden_in_the_middle(code_point)
    ]

    assert missed[:10] == []


@pytest.mark.parametrize(("first", "last"), list(HIDDEN_RANGES.values()), ids=list(HIDDEN_RANGES))
def test_the_code_points_next_to_a_range_are_not_hidden_text(first: int, last: int) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (a closed table "kept in the source, not
    read from unicodedata": a code point outside every listed range is allowed). A neighbour that
    is itself in another range, or a non-character, is left out."""
    neighbours = [
        code_point
        for code_point in (first - 1, last + 1)
        if 0 <= code_point <= LAST_CODE_POINT
        and not is_hidden(code_point)
        and code_point not in UNSPECIFIED_CODE_POINTS
    ]
    wrongly_refused = [
        f"U+{code_point:04X}" for code_point in neighbours if hidden_in_the_middle(code_point)
    ]

    assert wrongly_refused == []


def test_the_table_has_the_ranges_of_the_decision_and_no_gap_in_the_test() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (21 listed ranges and the two
    supplementary private use planes); this guards the table of this file against a lost range."""
    assert len(HIDDEN_RANGES) == 23
    assert all(first <= last for first, last in HIDDEN_RANGES.values())


@pytest.mark.parametrize("code_point", [TAB, LINE_FEED])
def test_a_tab_and_a_line_feed_are_allowed(code_point: int) -> None:
    """AC-4. expected_behavior_source: AC-4 ("allows tab and line feed"); ADR-002 decision 9
    ("U+0000 to U+001F except tab and line feed")."""
    assert hidden_in_the_middle(code_point) == ()


def test_a_carriage_return_is_hidden_text() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (every control of U+0000 to U+001F other
    than tab and line feed, so U+000D too; line endings are normalised to LF only when the hash is
    made)."""
    assert hidden_in_the_middle(0x0D)
    assert hidden_text_problems("one\r\ntwo\r\n")


@pytest.mark.parametrize(
    "text",
    [
        "Plain text with a tab\tand a line feed\nand a second line.\n",
        "".join(chr(code_point) for code_point in range(0x20, 0x7F)),
        "caf\u00e9 \u00fc\u00df \u65e5\u672c\u8a9e \u0434\u0430",
        "an emoji \U0001f600 with no selector",
        "Use <code>orqlet</code> or a < b and c > d.",
    ],
    ids=["tab-and-line-feed", "printable-ascii", "letters-of-other-scripts", "emoji", "markup"],
)
def test_ordinary_text_is_not_hidden_text(text: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (only the listed code points and HTML
    comments are refused; letters of any script, a plain emoji and raw markup that is not a
    comment are not in the table)."""
    assert hidden_text_problems(text) == ()


@pytest.mark.parametrize(
    "text",
    [
        "before <!-- a hidden instruction --> after",
        "<!-- first line\nsecond line -->",
        "<!---->",
        "line one\nline two <!-- note --> \n",
    ],
    ids=["inline", "multi-line", "empty", "after-text"],
)
def test_an_html_comment_is_hidden_text(text: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 ("free of HTML comments"); AC-4
    ("and HTML comments")."""
    assert hidden_text_problems(text)


def test_hidden_text_problems_gives_rule_names_and_never_the_text() -> None:
    """AC-4. expected_behavior_source: EC-7 (`-> tuple[str, ...]`); ORQLET-SEC-003."""
    marker = "zq7marker-hidden-5d1e"
    for hidden in ("\u202e", "\u200b", "\U000e0041", "\x00", "<!-- " + marker + " -->"):
        problems = hidden_text_problems("head " + marker + hidden + " tail")

        assert problems
        assert_well_formed(problems)
        assert not holds_any(shown(problems), marker, hidden.strip())


# --- AC-4 and AC-5: credential_problems -----------------------------------------------------------

BENIGN_LINE = "A short line of ordinary prose."
LINE_INDEX = 37
SECRET_BODY = "Zq7Secret" + body(31)  # 40 characters, token-like


def github_token() -> str:
    return "gh" + "p_" + body(36)


def llm_vendor_key() -> str:
    """The shape of a model vendor key: a short prefix and a long body (review finding F-7)."""
    return "s" + "k-" + "ant-" + body(40)


def aws_access_key() -> str:
    return "AK" + "IA" + "QWERTYUIOP234567"


def jwt_shape() -> str:
    """Three base64url sections joined by dots, the first starting with the JWT header prefix."""
    return ".".join((EYJ + "hbGciOiJIUzI1NiJ9", EYJ + "zdWIiOiJ0ZXN0In0", body(43)))


def private_key_marker(label: str) -> str:
    return PEM_DASHES + "BEGIN " + label + PEM_DASHES


def document_with(line: str, *, before: int = LINE_INDEX) -> str:
    """A text of benign lines with `line` after `before` of them and one more benign line after."""
    return "\n".join([*([BENIGN_LINE] * before), line, BENIGN_LINE, ""])


def present(problems: tuple[str, ...], number: int) -> bool:
    """Whether a result shows `number` as a whole decimal number."""
    return re.search(rf"(?<!\d){number}(?!\d)", " ".join(problems)) is not None


@functools.cache
def numbering_base() -> int:
    """The number of the first line (0 or 1), learned once from a text with one flagged line."""
    problems = credential_problems(document_with(github_token()))
    assert problems
    by_zero_base, by_one_base = present(problems, LINE_INDEX), present(problems, LINE_INDEX + 1)
    assert by_zero_base != by_one_base, "the result must show the line number, from 0 or from 1"
    return 0 if by_zero_base else 1


def assert_found_on(text: str, *indices: int) -> None:
    """The text has problems; each zero-based line in `indices` is shown, its neighbours are not."""
    problems = credential_problems(text)
    base = numbering_base()

    assert problems
    for index in indices:
        assert present(problems, index + base), f"line {index} is not shown"
        for neighbour in (index - 1, index + 1):
            if neighbour not in indices:
                assert not present(problems, neighbour + base), f"line {neighbour} is shown"


CONTEXTS = {
    "bare": "{value}",
    "quoted": '"{value}"',
    "in-prose": "see {value} for the details",
    "list-item": "- note: {value}",
    "in-backticks": "`{value}`",
}
TOKEN_SHAPES = {
    "github-classic-token": github_token,
    "aws-access-key-id": aws_access_key,
    "jwt": jwt_shape,
    "llm-vendor-key": llm_vendor_key,
}


def credential_cases() -> dict[str, tuple[str, str]]:
    """One line for each rule of ADR-002 decision 9, with the part of it that must never be shown.

    The part is empty where the whole line is only fixed words (a marker, a key shape): the words
    of a rule name may overlap those, so only the whole line is checked there.
    """
    cases = {
        "token-prefix-github": (github_token(), github_token()),
        "token-prefix-aws": (aws_access_key(), aws_access_key()),
        "jwt-shape": (jwt_shape(), jwt_shape()),
        "user-information-with-a-password": (
            "https://someone:" + LITERAL + "@docs.example.com/page",
            LITERAL,
        ),
        "user-information-only": (
            "https://someone@docs.example.com/page",
            "someone@docs.example.com",
        ),
        "token-as-user-information": (
            "https://" + github_token() + "@docs.example.com/page",
            github_token(),
        ),
        "authorization-bearer": ("Authorization: Bearer " + SECRET_BODY, SECRET_BODY),
        "authorization-basic": ("Authorization: Basic " + SECRET_BODY, SECRET_BODY),
        "storage-state-shape": ('{"cookies": [], "origins": []}', ""),
    }
    for label in ("PRIVATE KEY", "RSA PRIVATE KEY", "OPENSSH PRIVATE KEY", "EC PRIVATE KEY"):
        cases["private-key-" + label.lower().replace(" ", "-")] = (private_key_marker(label), "")
    for key in ("password", "secret", "token", "api_key"):
        cases["key-value-" + key] = (f"{key}={SECRET_BODY}", SECRET_BODY)
    return cases


CREDENTIAL_CASES = credential_cases()
CREDENTIAL_LINES = {name: line for name, (line, _) in CREDENTIAL_CASES.items()}
PRETTY_STORAGE_STATE = '{\n  "cookies": [],\n  "origins": []\n}\n'


@pytest.mark.parametrize("index", [12, LINE_INDEX, 85])
def test_a_finding_is_numbered_from_the_same_base_on_every_line(index: int) -> None:
    """AC-4. expected_behavior_source: AC-4 ("a rule name and a line number for each rule"). The
    base of the numbering is not stated, so the tests learn it once and require it everywhere."""
    assert_found_on(document_with(github_token(), before=index), index)


def test_the_result_is_a_tuple_of_rule_names_with_line_numbers() -> None:
    """AC-4. expected_behavior_source: EC-8 (`-> tuple[str, ...]`); AC-4."""
    problems = credential_problems(document_with(github_token()))

    assert_well_formed(problems)
    assert problems


@parametrized("line", CREDENTIAL_LINES)
def test_every_rule_of_the_decision_is_reported_with_its_line(line: str) -> None:
    """AC-4. expected_behavior_source: AC-4 ("a rule name and a line number for each rule of
    decision 9 including the storage-state shape"); ADR-002 decision 9 (token prefixes of
    well-known providers, the JWT shape, private-key block markers, user information in an
    address, Authorization values with a token-like body, key=value pairs whose key is a credential
    word, and the shape of a browser storage-state file). GitHub and AWS are the two best-known
    prefixes; the key words are password, secret, token and api_key."""
    assert_found_on(document_with(line), LINE_INDEX)


def test_two_credentials_on_two_lines_are_reported_on_both_lines() -> None:
    """AC-4. expected_behavior_source: AC-4 (a line number for each rule)."""
    lines = [BENIGN_LINE] * 60
    lines[LINE_INDEX], lines[52] = github_token(), jwt_shape()

    assert_found_on("\n".join(lines), LINE_INDEX, 52)


@pytest.mark.parametrize("context", list(CONTEXTS))
@pytest.mark.parametrize("shape", list(TOKEN_SHAPES))
def test_a_token_shape_is_found_in_its_context(shape: str, context: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (the scan is written for Markdown, so a
    token sits in prose, a list item, quotes or an inline code span)."""
    value = TOKEN_SHAPES[shape]()

    assert_found_on(document_with(CONTEXTS[context].format(value=value)), LINE_INDEX)


@pytest.mark.parametrize("ending", ["", "\n"])
@pytest.mark.parametrize("shape", list(TOKEN_SHAPES))
def test_a_token_at_the_end_of_the_text_is_found_with_and_without_a_final_line_feed(
    shape: str, ending: str
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (a bounded scan of lines)."""
    assert credential_problems(TOKEN_SHAPES[shape]() + ending)


def test_the_storage_state_shape_is_found_when_it_is_written_over_several_lines() -> None:
    """AC-4. expected_behavior_source: AC-4 ("including the storage-state shape"); ADR-002
    decision 9 (top-level `cookies` and `origins` keys; the shape that Playwright writes has one
    key per line)."""
    assert credential_problems(document_with(PRETTY_STORAGE_STATE))
    assert credential_problems(PRETTY_STORAGE_STATE)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\n",
        BENIGN_LINE,
        f"Source: {ADDRESS}\n{REFERENCE_LINE}\n\n# Title\nBody of the page.\n",
        "Version 1.2.3 of docs.example.com, release a.b.c.\n",
        "See https://docs.example.com/@scope/package for the package.\n",
        "Send the Authorization header with each request.\n",
        '{"title": "' + SECRET_BODY + '"}\n',
        "title=" + SECRET_BODY + "\n",
        "token=abc\n",
        '{"title": "Settings"}\n',
        "x" * 4096 + "\n",
    ],
    ids=[
        "empty",
        "line-feed",
        "prose",
        "copy-header-and-body",
        "dotted-version-numbers",
        "at-sign-in-the-path",
        "prose-with-the-word-authorization",
        "json-title-with-a-long-value",
        "plain-key-with-a-long-value",
        "credential-word-with-a-short-value",
        "json-without-the-storage-state-keys",
        "line-of-4096-characters",
    ],
)
def test_text_without_a_credential_has_no_problem(text: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (the rules are prefixes, the JWT shape,
    private-key markers, user information in an address, Authorization values with a token-like
    body, key=value pairs with a credential word and a token-like value, and the storage-state
    shape; nothing else is a finding, and a line of 4096 characters is within the cap)."""
    assert credential_problems(text) == ()


@pytest.mark.parametrize(
    ("line", "secret"), list(CREDENTIAL_CASES.values()), ids=list(CREDENTIAL_CASES)
)
def test_no_problem_shows_a_part_of_the_matched_text(line: str, secret: str) -> None:
    """AC-4. expected_behavior_source: AC-4 ("never the text"); ORQLET-SEC-003."""
    problems = credential_problems(document_with(line))

    assert problems
    assert line.lower() not in shown(problems)
    assert not secret or not holds_a_part(problems, secret, width=12)


def test_the_body_of_a_private_key_block_is_never_shown() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (private-key block markers; the scan
    reports a rule name and a line and never the text); ORQLET-SEC-003."""
    block = "\n".join(
        [
            private_key_marker("PRIVATE KEY"),
            SECRET_BODY,
            PEM_DASHES + "END PRIVATE KEY" + PEM_DASHES,
        ]
    )
    problems = credential_problems(document_with(block))

    assert problems
    assert not holds_a_part(problems, SECRET_BODY, width=12)


@pytest.mark.parametrize("shape", list(TOKEN_SHAPES))
def test_a_token_in_a_context_is_never_shown(shape: str) -> None:
    """AC-4. expected_behavior_source: AC-4 ("never the text"); ORQLET-SEC-003."""
    value = TOKEN_SHAPES[shape]()
    problems = credential_problems(document_with(f"see {value} for the details"))

    assert problems
    assert not holds_a_part(problems, value, width=12)


# AC-5: a line of more than 4096 characters is itself a finding ----------------------------------


@pytest.mark.parametrize("ending", ["", "\n"])
def test_a_line_of_exactly_4096_characters_is_not_a_finding(ending: str) -> None:
    """AC-5. expected_behavior_source: AC-5 and ADR-002 decision 9 ("lines of at most 4096
    characters (a longer line is itself a finding)")."""
    assert credential_problems("x" * 4096 + ending) == ()


@pytest.mark.parametrize("length", [4097, 4098, 12_288, 200_000])
def test_a_line_of_more_than_4096_characters_is_a_finding_on_its_line(length: int) -> None:
    """AC-5. expected_behavior_source: AC-5 ("a line of more than 4096 characters is itself a
    finding"); AC-4 (a line number for each finding)."""
    assert_found_on(document_with("x" * length), LINE_INDEX)


def test_the_cap_is_per_line_and_many_short_lines_are_not_a_finding() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (the cap is on a line, not on the
    text; a copy may hold 64 KiB)."""
    text = "\n".join(["x" * 40] * 1500) + "\n"

    assert len(text) > 4096
    assert credential_problems(text) == ()


def test_a_line_after_an_oversize_line_is_still_scanned() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (a finding per line); AC-5."""
    lines = [BENIGN_LINE] * 60
    lines[LINE_INDEX], lines[52] = "x" * 4097, github_token()

    assert_found_on("\n".join(lines), LINE_INDEX, 52)


def test_a_credential_after_offset_4097_of_a_line_is_not_hidden_by_the_cap() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 9 (a longer line is itself a finding, so a
    credential past the cap cannot hide); ORQLET-SEC-003 (it is never shown)."""
    token = github_token()
    text = document_with("x" * 4097 + token)

    assert_found_on(text, LINE_INDEX)
    assert not holds_a_part(credential_problems(text), token, width=12)


# --- AC-8: the module is pure -------------------------------------------------------------------

CLOCK_RANDOM_AND_ENVIRONMENT_MODULES = frozenset(
    {"time", "random", "secrets", "uuid", "os", "platform"}
)
CLOCK_CALLS = frozenset({"now", "utcnow", "today"})


def imported_modules(source: str) -> set[str]:
    """The absolute modules that a source imports, at any depth; a relative import stays inside the
    package and is not listed."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            modules.add(node.module or "")
    return modules


def imports_outside_the_standard_library_and_the_domain(source: str) -> set[str]:
    return {
        name
        for name in imported_modules(source)
        if name.split(".")[0] not in sys.stdlib_module_names
        and name != "orqlet.domain"
        and not name.startswith("orqlet.domain.")
    }


def clock_random_or_environment_imports(source: str) -> set[str]:
    return {
        name
        for name in imported_modules(source)
        if name.split(".")[0] in CLOCK_RANDOM_AND_ENVIRONMENT_MODULES
    }


def clock_calls(source: str) -> set[str]:
    return {
        node.attr
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute) and node.attr in CLOCK_CALLS
    }


def _assigned_names(target: ast.expr) -> list[str]:
    return [node.id for node in ast.walk(target) if isinstance(node, ast.Name)]


def public_assignments(source: str) -> set[str]:
    """Public names that a module assigns at its top level (also inside `if` and `try`)."""
    found: set[str] = set()
    pending: list[ast.stmt] = list(ast.parse(source).body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.Assign):
            names = [name for target in node.targets for name in _assigned_names(target)]
        elif isinstance(node, ast.AnnAssign | ast.AugAssign):
            names = _assigned_names(node.target)
        elif isinstance(node, ast.TypeAlias):
            names = _assigned_names(node.name)
        else:
            if isinstance(node, ast.If):
                pending.extend([*node.body, *node.orelse])
            elif isinstance(node, ast.Try):
                handlers = [statement for handler in node.handlers for statement in handler.body]
                pending.extend([*node.body, *handlers, *node.orelse, *node.finalbody])
            continue
        found.update(name for name in names if not name.startswith("_"))
    return found


def test_the_module_imports_only_the_standard_library_and_domain_modules() -> None:
    """AC-8. expected_behavior_source: AC-8 and ORQLET-ARCH-002 ("Both modules import only the
    standard library and domain modules"); plan P-1 (standard library only for resources.py)."""
    source = inspect.getsource(resources)

    assert imports_outside_the_standard_library_and_the_domain(source) == set()


def test_the_module_uses_no_clock_random_number_environment_or_unicode_table() -> None:
    """AC-8. expected_behavior_source: AC-8 ("use no clock, random number or environment");
    plan P-1 (no unicodedata: the code point table is numeric); ADR-002 decision 9."""
    source = inspect.getsource(resources)

    assert clock_random_or_environment_imports(source) == set()
    assert "unicodedata" not in imported_modules(source)
    assert clock_calls(source) == set()


def test_the_module_defines_no_public_name_that_is_not_a_function_or_a_class() -> None:
    """AC-8. expected_behavior_source: AC-8 and component rule 6 ("No new public assignment":
    constants stay private because the public-API extractor reads assignments)."""
    assert public_assignments(inspect.getsource(resources)) == set()


def test_the_purity_checks_find_what_they_look_for() -> None:
    """AC-8. expected_behavior_source: AC-8 (the failing and the passing case of the checks
    above)."""
    source = (
        "import os\nimport re\nimport yaml\nimport unicodedata\nfrom time import time\n"
        "from orqlet.application import x\nfrom orqlet.domain.globs import glob_match\n"
        "from . import sibling\nstamp = datetime.now()\nLIMIT = 3\n_PRIVATE = 4\nA: int = 5\n"
        "type Alias = int\nif LIMIT:\n    NESTED = 1\n"
    )

    assert imports_outside_the_standard_library_and_the_domain(source) == {
        "yaml",
        "orqlet.application",
    }
    assert clock_random_or_environment_imports(source) == {"os", "time"}
    assert clock_calls(source) == {"now"}
    assert public_assignments(source) == {"stamp", "LIMIT", "A", "Alias", "NESTED"}
    assert imported_modules("import re\nfrom collections.abc import Mapping\n") == {
        "re",
        "collections.abc",
    }
    assert public_assignments("def f() -> None:\n    return None\n\nclass C:\n    X = 1\n") == set()


# --- rework round 1: findings of the first review round (security F-2, F-3; architecture F-13) ---


def test_host_of_gives_nothing_for_an_address_whose_authority_holds_user_information() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 8 (the host is shown on its own line, so a
    refused address must not come back as a host); security review of phase P-1, finding F-2."""
    address = "https://someone:" + "pw" + body(12) + "@docs.example.com/guides"

    assert url_problems(address)
    assert host_of(address) == ""


@pytest.mark.parametrize("resource_id", ["../x", "a/b", "con", "A", "", "a" * 33])
def test_copy_path_refuses_an_id_that_would_not_pass_the_id_rules(resource_id: str) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 1 (the id becomes a file name) and
    decision 9 (the path of a copy is derived from a validated id); security review F-3."""
    with pytest.raises(ValueError, match="resource id") as caught:
        copy_path(resource_id)

    assert not holds_a_part((str(caught.value),), resource_id) or len(resource_id) < 8


def test_a_slug_that_starts_like_a_cloud_key_prefix_is_not_a_credential() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 (a rule has no bypass flag, so it must
    not refuse a plain address); architecture review of phase P-1, finding F-13."""
    assert url_problems(GUIDES + "/ASIA-pacific-handbook-2026") == ()
    assert not credential_problems("ASIA-pacific-handbook-2026 and AKIA-region-guide-v2-final")
