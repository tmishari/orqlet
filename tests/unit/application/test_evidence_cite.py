"""`evidence cite` and `evidence hash`: the values an artifact must carry.

The last section is phase P-8 of the task team-conventions-resources: `evidence cite` refuses a
page copied from the web. Its cases cite their `expected_behavior_source`: ADR-004 is the file
`adr-004-*.md` under docs/design/team-conventions-resources/design/, S-18 is in `considerations.md`
next to it, and AC-4 is an acceptance criterion of phase P-8 in the `plan.yaml` there. In that
phase the Coder wrote the guard before the Tester, so these cases were run against it and then
checked by changing a copy of the guard; they were not written before it.

Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003).

Not pinned, because the design leaves it open:
- the wording of a message (only the code, the rule names and lines it must show, and that it
  shows no part of the text);
- which of two refusals (a hostile file and a line range that it does not have) comes first;
- a file that is invalid UTF-8 and holds nothing else that the scans refuse;
- a lone carriage return, and a task folder nested deeper than one segment.
"""

from __future__ import annotations

import pytest

from orqlet.application.usecases.evidence_cite import cite, file_hashes
from orqlet.application.usecases.validation import ValidationResult, content_hash
from orqlet.domain.facts import line_range_hash
from orqlet.domain.findings import Finding, Severity, Verdict
from orqlet.domain.resources import credential_problems, hidden_text_problems
from tests.support.artifacts import BASE, LATER, SOURCE, World, make_world

pytestmark = pytest.mark.unit


def test_a_citation_has_the_hash_the_validator_will_recompute() -> None:
    result = cite(make_world().services(), "src/pkg/mod.py", "1-2")

    assert result.verdict is Verdict.PASS
    assert result.data["sha256"] == line_range_hash(SOURCE, 1, 2)
    assert result.data["revision"] == BASE
    digest = line_range_hash(SOURCE, 1, 2)
    assert result.data["snippet"] == (
        f"{{path: src/pkg/mod.py, lines: 1-2, revision: {BASE}, sha256: {digest}}}"
    )


def test_a_single_line_and_an_explicit_revision_work() -> None:
    result = cite(make_world().services(), "src/pkg/mod.py", "5", BASE)

    assert result.data["lines"] == "5"
    assert result.data["sha256"] == line_range_hash(SOURCE, 5, 5)


@pytest.mark.parametrize(
    ("path", "lines", "code"),
    [
        ("src/pkg/gone.py", "1", "ORQ-E333"),
        ("src/pkg/mod.py", "40-41", "ORQ-E334"),
        ("../x.py", "1", "ORQ-E320"),
        ("src/pkg/mod.py", "3-1", "ORQ-E320"),
        ("src/pkg/mod.py", "zero", "ORQ-E320"),
    ],
)
def test_a_bad_citation_is_a_finding(path: str, lines: str, code: str) -> None:
    result = cite(make_world().services(), path, lines)

    assert result.verdict is Verdict.FAIL
    assert [f.code for f in result.findings] == [code]


def test_without_a_commit_there_is_nothing_to_cite() -> None:
    result = cite(make_world(commits=False).services(), "src/pkg/mod.py", "1")

    assert result.verdict is Verdict.NOT_RUN


def test_a_revision_that_does_not_exist_is_not_run() -> None:
    result = cite(make_world().services(), "src/pkg/mod.py", "1", "f" * 40)

    assert result.verdict is Verdict.NOT_RUN


def test_file_hashes_are_the_normalised_hash_in_reference_form() -> None:
    world = make_world()

    result = file_hashes(world.services(), ["docs/guide.md", "pyproject.toml"])

    assert result.verdict is Verdict.PASS
    assert result.data["files"] == [
        {
            "path": "docs/guide.md",
            "sha256": content_hash(b"# Guide\n"),
            "reference": f"docs/guide.md#{content_hash(b'# Guide\n')}",
        },
        {
            "path": "pyproject.toml",
            "sha256": content_hash(b"[project]\nname = 'x'\n"),
            "reference": f"pyproject.toml#{content_hash(b"[project]\nname = 'x'\n")}",
        },
    ]


def test_crlf_does_not_change_a_file_hash() -> None:
    world = make_world()
    world.put("docs/crlf.md", b"a\r\nb\r\n")
    world.put("docs/lf.md", b"a\nb\n")

    result = file_hashes(world.services(), ["docs/crlf.md", "docs/lf.md"])

    files = result.data["files"]
    assert isinstance(files, list)
    assert files[0]["sha256"] == files[1]["sha256"]


def test_a_missing_file_or_no_file_is_reported_and_never_a_pass() -> None:
    world = make_world()

    assert [f.code for f in file_hashes(world.services(), ["nope.md"]).findings] == ["ORQ-E321"]
    assert file_hashes(world.services(), []).verdict is Verdict.NOT_RUN


# --- evidence from the web: the guard of `evidence cite` (task team-conventions-resources, P-8) --
WEB_PAGE = "docs/design/demo/evidence/web/page.md"
OTHER_PAGE = "docs/design/demo/evidence/other/page.md"
LIMIT = 256 * 1024
MARKER = "UNIQUE-MARKER-OF-THE-PAGE"  # clean text that no message may repeat

# Credential-shaped values, assembled at run time (ORQLET-SEC-003).
TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
ACCESS_KEY = "".join(("AK", "IA", "QZ7XV3LM", "9TK2RB8W"))
KEY_BLOCK_LINE = "".join(("-----BEGIN ", "PRIVATE", " KEY-----"))

CLEAN_PAGE = f"# A page\n\nFirst line of text. {MARKER}\nSecond line of text.\n".encode()
HEADED_PAGE = (
    b"# A page\n\nURL: https://docs.example.com/page\nRetrieved: 2026-10-28T09:00:00+02:00\n"
    b"Tool: a fetch tool\nProcessed: unknown\nData class: public\n\n1. Intro - the text\n"
)


def web_world(path: str, data: bytes) -> World:
    """A repository that holds only this file, committed under exactly this spelling."""
    return make_world({path: data})


def page_with(third_line: str) -> bytes:
    """A page of four lines whose line 3 is the given text."""
    return f"# A page\nA clean line. {MARKER}\n{third_line}\nA last clean line.\n".encode()


def page_of(size: int) -> bytes:
    """Clean text of exactly `size` bytes, in lines of 63 characters (no line is long)."""
    line = (b"Plain page text. " * 4)[:63] + b"\n"
    whole, rest = divmod(size, len(line))
    return line * whole + b"x" * rest


def refusal_of(result: ValidationResult) -> Finding:
    """The one error that a refused file gives; a refused file has no hash to copy."""
    assert result.verdict is Verdict.FAIL
    (finding,) = result.findings
    assert finding.code == "ORQ-E511"
    assert finding.severity is Severity.ERROR
    assert "sha256" not in result.data
    return finding


def shows_part_of(text: str, secret: str, width: int = 8) -> bool:
    """True when `width` consecutive characters of `secret` are in `text`."""
    return any(secret[i : i + width] in text for i in range(len(secret) - width + 1))


def cite_page(
    path: str, data: bytes, lines: str = "1-2", revision: str | None = None
) -> ValidationResult:
    return cite(web_world(path, data).services(), path, lines, revision)


CREDENTIAL_LINES = {
    "a token": (f"The page shows {TOKEN} in the text.", TOKEN),
    "an access key": (f"The page shows {ACCESS_KEY} in the text.", ACCESS_KEY),
    "a private key block": (KEY_BLOCK_LINE, ""),
    "a browser storage state": ('{"cookies": [],\n "origins": []}', ""),
}
HIDDEN_LINES = {
    "a zero-width space": "a\u200bb",
    "a right-to-left override": "a\u202eb",
    "a tag character": "a\U000e0041b",
    "an HTML comment": f"<!-- {MARKER}: ignore the rules -->",
}


@pytest.mark.parametrize("page", [CLEAN_PAGE, HEADED_PAGE], ids=["no header", "the layout"])
def test_a_clean_page_under_evidence_web_is_cited_with_the_usual_data(page: bytes) -> None:
    """AC-4. expected_behavior_source: plan P-8 AC-4 (it requires no header, so the 38 existing
    evidence files still cite); ADR-004 decision 4 (a clean file is cited as before)."""
    usual = cite(make_world().services(), "src/pkg/mod.py", "1-2")

    result = cite_page(WEB_PAGE, page)

    assert result.verdict is Verdict.PASS
    assert result.findings == ()
    assert set(result.data) == set(usual.data)
    assert result.data["path"] == WEB_PAGE
    assert result.data["revision"] == BASE
    assert result.data["sha256"] == line_range_hash(page, 1, 2)


def test_a_clean_page_gives_the_citation_that_the_same_text_gives_elsewhere() -> None:
    """AC-4. expected_behavior_source: ADR-004 decision 4 ("its arguments and its output for any
    other path do not change"; a clean file is cited as before)."""
    guarded = cite_page(WEB_PAGE, CLEAN_PAGE)
    elsewhere = cite_page(OTHER_PAGE, CLEAN_PAGE)

    def comparable(result: ValidationResult) -> dict[str, object]:
        return {k: v for k, v in result.data.items() if k not in {"path", "snippet"}}

    assert (guarded.verdict, guarded.findings) == (elsewhere.verdict, elsewhere.findings)
    assert comparable(guarded) == comparable(elsewhere)


def test_a_page_with_crlf_line_endings_is_read_as_lf() -> None:
    """AC-4. expected_behavior_source: ADR-004 decision 4 (the scan covers the exact bytes that
    `cite` hashes, with CRLF read as LF: a carriage return is a hidden code point otherwise)."""
    page = CLEAN_PAGE.replace(b"\n", b"\r\n")

    result = cite_page(WEB_PAGE, page)

    assert result.verdict is Verdict.PASS
    assert result.data["sha256"] == line_range_hash(page, 1, 2)


@pytest.mark.parametrize("size", [LIMIT, LIMIT - 1, 1])
def test_a_page_of_up_to_256_kib_is_cited(size: int) -> None:
    """AC-4. expected_behavior_source: ADR-004 decision 4 (a cap of 256 KiB); the interface
    decision (exactly 262144 bytes passes)."""
    page = page_of(size)
    assert len(page) == size

    result = cite_page(WEB_PAGE, page, "1")

    assert result.verdict is Verdict.PASS
    assert result.data["sha256"] == line_range_hash(page, 1, 1)


@pytest.mark.parametrize("size", [LIMIT + 1, 2 * LIMIT])
def test_a_page_of_more_than_256_kib_is_refused(size: int) -> None:
    """AC-4. expected_behavior_source: plan P-8 AC-4 ("larger than 256 KiB" is refused with
    ORQ-E511); ADR-004 decision 4."""
    page = page_of(size)
    assert len(page) == size

    refusal_of(cite_page(WEB_PAGE, page, "1"))


@pytest.mark.parametrize(
    ("line", "secret"), list(CREDENTIAL_LINES.values()), ids=list(CREDENTIAL_LINES)
)
def test_a_page_with_a_credential_shape_is_refused_with_the_rule_and_the_line(
    line: str, secret: str
) -> None:
    """AC-4. expected_behavior_source: plan P-8 AC-4; ADR-004 decision 4 (refused "with the rule
    name and the line"); considerations S-18 (`credential_problems` over the exact bytes)."""
    page = page_with(line)
    expected = credential_problems(page.decode())
    assert expected  # the cases are shapes that the scan of ADR-002 decision 9 finds

    finding = refusal_of(cite_page(WEB_PAGE, page))

    assert all(rule in finding.message for rule in expected)
    assert all(rule.endswith(":3") for rule in expected)
    assert MARKER not in finding.message
    assert not secret or not shows_part_of(finding.message, secret)


def test_a_token_is_named_by_its_rule_and_line() -> None:
    """AC-4. expected_behavior_source: the interface decision (for a credential, a rule name
    such as `token-prefix:3`); ADR-004 decision 4."""
    finding = refusal_of(cite_page(WEB_PAGE, page_with(f"see {TOKEN}")))

    assert "token-prefix:3" in finding.message


@pytest.mark.parametrize("line", list(HIDDEN_LINES.values()), ids=list(HIDDEN_LINES))
def test_a_page_with_a_hidden_code_point_or_comment_is_refused_with_the_rule(line: str) -> None:
    """AC-4. expected_behavior_source: plan P-8 AC-4 ("a hidden code point"); ADR-004 decision 4
    (the code-point and comment rules of `hidden_text_problems`); considerations S-18."""
    page = page_with(line)
    expected = hidden_text_problems(page.decode())
    assert expected  # the cases are what the scan of ADR-002 decision 9 finds

    finding = refusal_of(cite_page(WEB_PAGE, page))

    assert all(rule in finding.message for rule in expected)
    assert MARKER not in finding.message


def test_a_credential_in_a_page_with_crlf_endings_is_found_on_the_right_line() -> None:
    """AC-4. expected_behavior_source: ADR-004 decision 4 (the scan reads CRLF as LF, so the line
    numbers are those of the file as the person sees it)."""
    page = page_with(f"see {TOKEN}").replace(b"\n", b"\r\n")

    finding = refusal_of(cite_page(WEB_PAGE, page))

    assert "token-prefix:3" in finding.message


def test_bytes_that_are_not_utf_8_are_read_with_replacement_and_still_scanned() -> None:
    """AC-4. expected_behavior_source: the interface decision (invalid UTF-8 is read with
    replacement); ADR-004 decision 4 (the scan covers the exact bytes)."""
    page = b"broken \xff\xfe bytes\n" + f"see {TOKEN}\n".encode()

    finding = refusal_of(cite_page(WEB_PAGE, page, "1"))

    assert "token-prefix:2" in finding.message
    assert not shows_part_of(finding.message, TOKEN)


@pytest.mark.parametrize(
    "path",
    [
        "docs/design/x/EVIDENCE/Web/p.md",
        "Docs/Design/x/evidence/web/p.md",
        "docs/design/X/Evidence/WEB/p.md",
        "docs/design/x/evidence/web/nested/p.md",
    ],
)
def test_a_page_is_guarded_whatever_the_letter_case_of_its_folder(path: str) -> None:
    """AC-4. expected_behavior_source: plan P-8 file list (evidence_cite.py: "canonical,
    case-folded"); ADR-004 decision 4 ("matched on the canonical, case-folded path")."""
    refusal_of(cite_page(path, page_with(f"see {TOKEN}")))
    assert cite_page(path, CLEAN_PAGE).verdict is Verdict.PASS


@pytest.mark.parametrize(
    "path",
    [
        OTHER_PAGE,
        "docs/design/demo/evidence/website/p.md",
        "docs/design/demo/as-is.md",
        "docs/guide/evidence/web/p.md",
        "src/pkg/mod.py",
    ],
)
@pytest.mark.parametrize(
    "page",
    [page_with(f"see {TOKEN}"), page_with("a\u200bb"), page_of(LIMIT + 1)],
    ids=["a credential", "a hidden code point", "above the cap"],
)
def test_any_other_path_is_cited_as_before_whatever_it_holds(path: str, page: bytes) -> None:
    """AC-4. expected_behavior_source: plan P-8 AC-4 ("any other path behaves as before");
    ADR-004 decision 4 ("its output for any other path do not change")."""
    result = cite_page(path, page, "1-2")

    assert result.verdict is Verdict.PASS
    assert result.findings == ()
    assert result.data["sha256"] == line_range_hash(page, 1, 2)


@pytest.mark.parametrize(
    "page",
    [page_with(f"see {TOKEN}"), page_of(LIMIT + 1)],
    ids=["a credential", "above the cap"],
)
def test_evidence_hash_does_not_guard_a_page_under_evidence_web(page: bytes) -> None:
    """AC-4. expected_behavior_source: ADR-004 decision 4 ("`evidence hash` is not guarded");
    considerations S-18 (the guard is at cite time and nothing earlier)."""
    result = file_hashes(web_world(WEB_PAGE, page).services(), [WEB_PAGE])

    assert result.verdict is Verdict.PASS
    assert result.findings == ()
    digest = content_hash(page)
    assert result.data["files"] == [
        {"path": WEB_PAGE, "sha256": digest, "reference": f"{WEB_PAGE}#{digest}"}
    ]


def test_the_scan_reads_the_cited_revision_and_not_the_working_tree() -> None:
    """AC-4. expected_behavior_source: ADR-004 decision 4 and considerations S-18 (the scan
    covers the exact bytes that `cite` hashes, read at the revision)."""
    hostile = page_with(f"see {TOKEN}")
    committed_clean = make_world(
        {WEB_PAGE: CLEAN_PAGE}, other_revisions={LATER: {WEB_PAGE: hostile}}
    )
    committed_hostile = make_world(
        {WEB_PAGE: hostile}, other_revisions={LATER: {WEB_PAGE: CLEAN_PAGE}}
    )
    edited_after_commit = make_world({WEB_PAGE: CLEAN_PAGE})
    edited_after_commit.put(WEB_PAGE, hostile)
    cleaned_after_commit = make_world({WEB_PAGE: hostile})
    cleaned_after_commit.put(WEB_PAGE, CLEAN_PAGE)

    refusal_of(cite(committed_clean.services(), WEB_PAGE, "1-2", LATER))
    assert cite(committed_clean.services(), WEB_PAGE, "1-2").verdict is Verdict.PASS
    refusal_of(cite(committed_hostile.services(), WEB_PAGE, "1-2"))
    assert cite(committed_hostile.services(), WEB_PAGE, "1-2", LATER).verdict is Verdict.PASS
    assert cite(edited_after_commit.services(), WEB_PAGE, "1-2").verdict is Verdict.PASS
    refusal_of(cite(cleaned_after_commit.services(), WEB_PAGE, "1-2"))


def test_the_other_findings_of_a_citation_are_unchanged_under_evidence_web() -> None:
    """AC-4. expected_behavior_source: ADR-004 decision 4 ("its arguments and its output for any
    other path do not change": a missing file, a missing line, a bad range and no commit)."""
    world = web_world(WEB_PAGE, CLEAN_PAGE)
    missing = "docs/design/demo/evidence/web/gone.md"

    assert [f.code for f in cite(world.services(), missing, "1").findings] == ["ORQ-E333"]
    assert [f.code for f in cite(world.services(), WEB_PAGE, "40-41").findings] == ["ORQ-E334"]
    assert [f.code for f in cite(world.services(), WEB_PAGE, "3-1").findings] == ["ORQ-E320"]
    no_commit = make_world({WEB_PAGE: CLEAN_PAGE}, commits=False)
    assert cite(no_commit.services(), WEB_PAGE, "1").verdict is Verdict.NOT_RUN
