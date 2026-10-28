"""The README section for adopters of the MCP declaration (task mcp-or-plugins, phase P-8).

Every test cites its `expected_behavior_source`. ADR-002, ADR-003 and ADR-004 are the files
`adr-002-*.md`, `adr-003-*.md` and `adr-004-*.md` under docs/design/mcp-or-plugins/design/, and AC-1
to AC-4 are the acceptance criteria of phase P-8 in docs/design/mcp-or-plugins/plan.yaml. "The
interface decision" is the list of exact phrases that the plan author gave the Tester of phase P-8,
because the ADRs say what the README must say and not in which words: the section is the text from
the heading `## MCP servers, one credential per user` up to the next heading of level 2, and a
phrase is exact and case sensitive, with a line break read as a space.

These tests were written first, by the Tester of phase P-8, before the README section existed. The
reading rules (the section, the fenced blocks, the table cells, the guards on claims) are small
functions of text. Each is also run on small texts that obey it and on texts that break it, so a
rule that cannot fail would fail here; those tests pass before the README is written.

Behaviour that the sources require but that no phrase fixes is deliberately NOT pinned here:
- where the section sits in the README, and its sub-headings;
- the steps "declare", "generate", "sign in" and "take the file over" beyond the phrases below;
- the instruction for the user's own credential (ADR-002 decision 12, "an instruction, not a check")
  and the statements about unattended surfaces and about the user's full permissions, which the ADR
  says the README makes "until it is answered";
- the change of ORQ-I030 (plan P-8, file list: README.md), which no criterion and no phrase names;
- the wording of the reason of the opt-out (only that a warning and `exit 1` are said beside it).

The guards of the claims (ADR-002 decision 12; AC-4) are heuristics over sentences: a sentence that
holds a claim word and no word of denial is a claim. They cannot replace the security reviewer, who
judges AC-4 as a whole.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

README = Path(__file__).resolve().parents[2] / "README.md"
SECTION_HEADING = "## MCP servers, one credential per user"
STATUS_HEADING = "## Status"
COMMANDS_HEADING = "## Commands"
NOT_BUILT = "What is **not** built yet"
CI_LINE = "orqlet validate integrations .orqlet/integrations.yaml"
CI_SNIPPET_FIRST_LINE = "name: orqlet-checks"

# --- the phrases of the interface decision -------------------------------------------------------

FILES_AND_COMMAND = (".orqlet/integrations.yaml", "orqlet validate integrations", ".mcp.json")
PROPOSAL = ("shows only the text that Orqlet wants", "stays until you merge it")
OPT_OUT = "delete the declaration and rename or remove the `orqlet-*` entries"
ONLY_THE_COMMAND_CHECKS = "only `orqlet validate integrations` checks the rules"
ROUTES = (
    "managed settings",
    "plugins that a committed settings file enables",
    "an entry that starts a process",
)
LIMITS = (
    "a project without a declaration is not checked",
    "the scan of the declaration reads its text and not its decoded values",
    "an undeclared entry whose name does not start with `orqlet-` is counted and not examined",
    "a declaration written for an earlier schema blocks `orqlet upgrade`",
    "the notice about CODEOWNERS matches text and does not check ownership",
)
REACH = ("only for Atlassian on Claude Code", "No check with a test account has run yet")
FILES_THAT_PIN_THE_TOOL = "the files that pin the tool"
REQUIRED_CODES = frozenset(
    {f"ORQ-E{number}" for number in range(530, 540)}
    | {"ORQ-W530"}
    | {f"ORQ-I{number}" for number in range(530, 535)}
)
INTEGRATION_FAMILIES = re.compile(r"ORQ-[EWI]53\d")

# --- reading the README --------------------------------------------------------------------------

CODE = re.compile(r"(?<![\w-])ORQ-[EWI]\d{3}(?!\d)")
CELL_BAR = re.compile(r"(?<!\\)\|")
TABLE_RULE = re.compile(r"\|[\s:|-]*-{3,}[\s:|-]*")
EXIT_ONE = re.compile(r"\bexit(?:s|ed)?(?: with)?(?: (?:code|status))? 1\b", re.IGNORECASE)


def squash(text: str) -> str:
    """The text with every run of white space as one space, so a re-wrapped phrase still matches."""
    return " ".join(text.split())


def is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def level_two_headings(lines: list[str]) -> list[int]:
    """The indexes of the lines that open a section of level 2, never one inside a fenced block."""
    found: list[int] = []
    inside = False
    for number, line in enumerate(lines):
        if is_fence(line):
            inside = not inside
        elif not inside and line.startswith("## "):
            found.append(number)
    return found


def section_of(text: str, heading: str) -> str:
    """The text under a heading of level 2 up to the next one. A missing heading fails here."""
    lines = text.split("\n")
    headings = level_two_headings(lines)
    starts = [number for number in headings if lines[number].rstrip() == heading]
    if len(starts) != 1:
        pytest.fail(
            f"README.md must hold the heading {heading!r} exactly once; it holds {len(starts)}"
        )
    following = [number for number in headings if number > starts[0]]
    end = following[0] if following else len(lines)
    return "\n".join(lines[starts[0] + 1 : end])


def fenced_blocks(text: str) -> list[tuple[str, str]]:
    """The language (first word of the info string, lower case) and the body of each fenced block"""
    blocks: list[tuple[str, str]] = []
    language: str | None = None
    body: list[str] = []
    for line in text.split("\n"):
        if is_fence(line):
            if language is None:
                words = line.lstrip().removeprefix("```").split()
                language = words[0].lower() if words else ""
                body = []
            else:
                blocks.append((language, "\n".join(body)))
                language = None
        elif language is not None:
            body.append(line)
    return blocks


def prose_of(text: str) -> str:
    """The text without its fenced blocks (their fence lines included)."""
    kept: list[str] = []
    inside = False
    for line in text.split("\n"):
        if is_fence(line):
            inside = not inside
        elif not inside:
            kept.append(line)
    return "\n".join(kept)


def paragraphs_of(text: str) -> list[str]:
    return [paragraph for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]


def cells_of(row: str) -> list[str]:
    return [
        cell.strip() for cell in CELL_BAR.split(row.strip().removeprefix("|").removesuffix("|"))
    ]


def table_rows(text: str) -> list[list[str]]:
    """The data rows of every Markdown table outside a fenced block: a header, a rule, the rows."""
    lines = prose_of(text).split("\n")
    rows: list[list[str]] = []
    index = 0
    while index < len(lines):
        opens_a_table = (
            lines[index].strip().startswith("|")
            and index + 1 < len(lines)
            and TABLE_RULE.fullmatch(lines[index + 1].strip()) is not None
        )
        if not opens_a_table:
            index += 1
            continue
        index += 2
        while index < len(lines) and lines[index].strip().startswith("|"):
            rows.append(cells_of(lines[index]))
            index += 1
    return rows


def codes_in_first_cells(text: str) -> set[str]:
    """The full finding codes that stand in the first cell of a row of a table."""
    return {code for row in table_rows(text) for code in CODE.findall(row[0])}


def bullets_of(text: str) -> list[str]:
    """The items of the bullet lists of the text, each on one line."""
    items: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if line.startswith("- "):
            current = [line.removeprefix("- ").strip()]
            items.append(current)
        elif current is not None and line.strip() and line.startswith((" ", "\t")):
            current.append(line.strip())
        else:
            current = None
    return [" ".join(item) for item in items]


def yaml_blocks(text: str) -> list[str]:
    return [body for language, body in fenced_blocks(text) if language in {"yaml", "yml"}]


def has_command_line(body: str, command: str) -> bool:
    """The body has the command alone on a line, with at most a trailing `# comment`."""
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped == command or re.fullmatch(re.escape(command) + r"\s+#.*", stripped):
            return True
    return False


def missing(text: str, phrases: Iterable[str]) -> list[str]:
    found = squash(text)
    return [phrase for phrase in phrases if phrase not in found]


def readme() -> str:
    return README.read_text(encoding="utf-8")


def integrations() -> str:
    return section_of(readme(), SECTION_HEADING)


# --- guards on claims (ADR-002 decision 12) ------------------------------------------------------

NEGATION = re.compile(
    r"\b(?:not|no|never|cannot|nothing|neither|nor|without|unable)\b|n't", re.IGNORECASE
)
SHARING_VERB = re.compile(r"\b(?:guarantee[sd]?|ensure[sd]?|prevent(?:s|ed)?)\b", re.IGNORECASE)
SHARING_TOPIC = re.compile(
    r"\b(?:credentials?|tokens?|shar\w*|lent|lend\w*|borrow\w*)\b", re.IGNORECASE
)
COVERAGE = re.compile(r"\b(?:every|all)\s+MCP\s+(?:entry|entries|servers?)\b", re.IGNORECASE)
READ_ONLY = re.compile(r"\bread[- ]only\b", re.IGNORECASE)
ENTRY_TOPIC = re.compile(
    r"\b(?:Atlassian|Jira|Confluence|entry|entries|servers?)\b|orqlet-", re.IGNORECASE
)
GITHUB = re.compile(r"\bGitHub\b", re.IGNORECASE)


def promises_that_no_credential_is_shared(unit: str) -> bool:
    return bool(
        SHARING_VERB.search(unit) and SHARING_TOPIC.search(unit) and not NEGATION.search(unit)
    )


def says_the_check_covers_everything(unit: str) -> bool:
    return bool(COVERAGE.search(unit) and not NEGATION.search(unit))


def calls_the_entry_read_only(unit: str) -> bool:
    return bool(
        READ_ONLY.search(unit)
        and ENTRY_TOPIC.search(unit)
        and not GITHUB.search(unit)
        and not NEGATION.search(unit)
    )


def units_of(text: str) -> list[str]:
    """The sentences, list items and table rows of the prose, each squashed to one line."""
    pieces = re.split(r"(?<=[.!?])\s+|\n\s*\n|\n(?=\s*(?:[-*+]\s|\d+\.\s|\|))", prose_of(text))
    return [squash(piece) for piece in pieces if piece.strip()]


def claims_in(text: str, guard: Callable[[str], bool]) -> list[str]:
    return [unit for unit in units_of(text) if guard(unit)]


# --- the reading rules themselves are sound ------------------------------------------------------


def test_a_section_ends_at_the_next_heading_of_level_two_and_keeps_those_of_level_three() -> None:
    """AC-1. expected_behavior_source: the interface decision (the section is the text from the
    heading up to the next heading of level 2). It passes before the README is written."""
    text = "## A\none\n### Sub\ntwo\n## B\nthree\n"

    assert section_of(text, "## A") == "one\n### Sub\ntwo"
    assert section_of(text, "## B") == "three\n"


def test_a_line_that_looks_like_a_heading_inside_a_fenced_block_is_not_one() -> None:
    """AC-1. expected_behavior_source: the interface decision (headings, not lines of a code block).
    It passes before the README is written."""
    text = "## A\none\n```sh\n## not a heading\n```\ntwo\n## B\n"

    assert section_of(text, "## A") == "one\n```sh\n## not a heading\n```\ntwo"


@pytest.mark.parametrize(
    ("text", "heading"),
    [
        pytest.param("## A\nx\n", "## B", id="missing"),
        pytest.param("## A\nx\n## B\n## A\ny\n", "## A", id="repeated"),
        pytest.param("### A\nx\n", "## A", id="level-three-only"),
    ],
)
def test_a_missing_or_repeated_heading_fails_the_reader(text: str, heading: str) -> None:
    """AC-1. expected_behavior_source: the interface decision (the section is found by its heading;
    a README without it fails for that reason). It passes before the README is written."""
    with pytest.raises(pytest.fail.Exception):
        section_of(text, heading)


def test_fenced_blocks_are_read_with_their_language_and_their_body() -> None:
    """AC-3. expected_behavior_source: the interface decision (a fenced block with the language
    `sh`; the README holds exactly one `yaml` block). It passes before the README is written."""
    text = "a\n```sh\nx\n```\nb\n```YAML title\nname: orqlet-checks\n\n```\n```\nplain\n```\n"

    assert fenced_blocks(text) == [("sh", "x"), ("yaml", "name: orqlet-checks\n"), ("", "plain")]
    assert yaml_blocks(text) == ["name: orqlet-checks\n"]
    assert prose_of(text) == "a\nb\n"


def test_a_command_line_may_end_in_a_comment_and_nothing_else() -> None:
    """AC-1. expected_behavior_source: the interface decision (the `sh` block contains the line
    `orqlet validate integrations .orqlet/integrations.yaml`). It passes before the README is
    written."""
    assert has_command_line(f"x\n  {CI_LINE}  \n", CI_LINE)
    assert has_command_line(f"{CI_LINE}   # the pinned tool\n", CI_LINE)
    assert not has_command_line(f"{CI_LINE} --json\n", CI_LINE)
    assert not has_command_line(f"# {CI_LINE}\n", CI_LINE)
    assert not has_command_line("orqlet validate integrations\n", CI_LINE)


def test_a_code_counts_only_when_it_is_whole_and_in_the_first_cell_of_a_table_row() -> None:
    """AC-1. expected_behavior_source: the interface decision (each code appears as a full code
    string in the first cell of some row of a table inside the section; a row may list several
    codes). It passes before the README is written."""
    table = (
        "| Code | Meaning |\n|---|---|\n"
        "| ORQ-E530, ORQ-E531 | one |\n"
        "| ORQ-E532, E533 | short form |\n"
        "| none | ORQ-E534 |\n"
        "| `ORQ-W530` | quoted |\n"
    )
    fenced = "```text\n| Code | x |\n|---|---|\n| ORQ-E535 | in a block |\n```\n"

    assert codes_in_first_cells(table) == {"ORQ-E530", "ORQ-E531", "ORQ-E532", "ORQ-W530"}
    assert codes_in_first_cells(fenced) == set()
    assert codes_in_first_cells("ORQ-E536 in a sentence, not a table\n") == set()


def test_the_bullets_of_a_list_are_joined_with_their_continuation_lines() -> None:
    """AC-1. expected_behavior_source: the interface decision (the Status list of what is built).
    It passes before the README is written."""
    text = "Intro:\n\n- one,\n  two;\n- three;\n\nafter\n- four\n"

    assert bullets_of(text) == ["one, two;", "three;", "four"]


@pytest.mark.parametrize(
    "unit",
    [
        "Orqlet guarantees that every credential stays with its owner.",
        "Orqlet ensures that every user brings their own token.",
        "This prevents a person from lending a token.",
        "Orqlet prevented a credential from being lent.",
    ],
)
def test_a_promise_that_no_credential_is_shared_is_flagged(unit: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 12 ("Never another user's credential: not
    enforceable by Orqlet. A person can lend a token or a shell"). It passes before the README is
    written."""
    assert promises_that_no_credential_is_shared(unit)


@pytest.mark.parametrize(
    "unit",
    [
        "Orqlet cannot prevent a person from lending a token.",
        "The scan is not a guarantee that no credential is shared.",
        "Nothing here ensures that a token is not lent.",
        "The scan reads the files that may hold a pasted credential.",
    ],
)
def test_a_denial_or_a_plain_statement_is_not_a_promise(unit: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 12 (the README may state the limit; it may
    not state the promise). It passes before the README is written."""
    assert not promises_that_no_credential_is_shared(unit)


@pytest.mark.parametrize(
    ("unit", "flagged"),
    [
        ("The check covers every MCP entry of the project.", True),
        ("`orqlet validate integrations` checks all MCP servers.", True),
        ("The check does not cover every MCP entry.", False),
        ("An undeclared entry whose name is not `orqlet-` is counted and not examined.", False),
    ],
)
def test_a_claim_of_full_coverage_is_flagged_and_its_denial_is_not(
    unit: str, flagged: bool
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 12 and ADR-002 decision 6 (an undeclared
    entry is left alone and counted; the check does not cover every entry); plan P-8 file list
    (the statements that CI validates every MCP entry are removed). It passes before the README is
    written."""
    assert says_the_check_covers_everything(unit) is flagged


@pytest.mark.parametrize(
    ("unit", "flagged"),
    [
        ("The Atlassian entry is read-only.", True),
        ("The generated entry is read only for Jira.", True),
        (
            "The contract forces the label read-only, but the entry does not restrict anything.",
            False,
        ),
        ("Create a fine-grained read-only token for GitHub.", False),
    ],
)
def test_the_label_read_only_on_the_entry_is_flagged_and_its_honest_use_is_not(
    unit: str, flagged: bool
) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 10 (the contract forces `read-only` and the
    generated entry restricts nothing: the agent gets the user's Atlassian permissions) and the
    consequence that the README names a fine-grained read-only token for GitHub. It passes before
    the README is written."""
    assert calls_the_entry_read_only(unit) is flagged


def test_the_units_of_a_text_are_its_sentences_list_items_and_rows() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 12 (a claim is judged where it is made).
    It passes before the README is written."""
    text = "One two\nthree. Four.\n\n- five\n- six\n| a | b |\n```sh\nseven.\n```\n"

    assert units_of(text) == ["One two three.", "Four.", "- five", "- six", "| a | b |"]


# --- the section: what it names (AC-1) -----------------------------------------------------------


def test_the_readme_holds_the_section_once() -> None:
    """AC-1. expected_behavior_source: plan P-8 file list (README.md: a section for adopters) and
    the interface decision (the heading `## MCP servers, one credential per user`)."""
    assert integrations().strip()


def test_the_section_names_the_declaration_the_command_and_the_generated_file() -> None:
    """AC-1. expected_behavior_source: AC-1 ("names the declaration file, the command, the
    generated file") and the interface decision (`.orqlet/integrations.yaml`; `orqlet validate
    integrations`; `.mcp.json`)."""
    assert missing(integrations(), FILES_AND_COMMAND) == []


def test_the_section_says_what_a_proposal_shows_and_how_long_it_stays() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 5 (the proposal shows the text that Orqlet
    wants and none of the team's file; it stays until the team merges it by hand), AC-1 ("the
    proposal that shows only the wanted text and stays until merged") and the interface decision."""
    assert missing(integrations(), PROPOSAL) == []


def test_the_section_gives_the_opt_out_and_says_that_a_warning_exits_1() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 11 (a team that takes the file over renames
    or removes the `orqlet-*` entries, "and the README says so"; a warning makes `doctor` exit 1),
    AC-1 ("the opt-out ... because a warning exits 1") and the interface decision. Only the phrase
    is exact; the reason is read as the words `warning` and `exit 1` in the same paragraph."""
    section = integrations()
    assert missing(section, [OPT_OUT]) == []

    holding = next(
        squash(block) for block in paragraphs_of(prose_of(section)) if OPT_OUT in squash(block)
    )
    assert "warning" in holding.lower(), "the paragraph of the opt-out gives no reason"
    assert EXIT_ONE.search(holding), "the paragraph of the opt-out does not say `exit 1`"


def test_the_section_says_that_only_validate_integrations_checks_the_rules() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 11 (the README "says that only this command
    checks the rules (the committed JSON Schema does not express them)"), AC-1 and the interface
    decision."""
    assert missing(integrations(), [ONLY_THE_COMMAND_CHECKS]) == []


def test_the_section_names_the_routes_that_orqlet_does_not_examine() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 12 ("Routes that Orqlet does not examine:
    managed MCP configuration ...; plugins and marketplaces that a committed `.claude/settings.json`
    enables ...; an undeclared entry that starts a process"), AC-1 and the interface decision."""
    assert missing(integrations(), ROUTES) == []


def test_the_section_states_the_limits() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 12 and decisions 6 and 7 (a project with no
    declaration is not checked; the scan reads text and not decoded values; an undeclared entry is
    counted and not examined), ADR-002 consequences (a declaration of an earlier schema blocks
    `upgrade`), ADR-003 decision 8 (the notice about CODEOWNERS is ORQ-I030, which lists paths) and
    the interface decision."""
    assert missing(integrations(), LIMITS) == []


def test_the_section_says_what_orqlet_generates_and_that_no_check_has_run() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 12 ("Reach of this change: the standard is
    met by what Orqlet generates only for Atlassian on Claude Code ... the README says so
    plainly"), ADR-004 decision 4 ("The README says which checks have run, and a check that was not
    run is reported as not run"), AC-1 and the interface decision."""
    assert missing(integrations(), REACH) == []


def test_the_ci_line_is_in_a_fenced_sh_block_and_the_files_that_pin_the_tool_are_named() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 11 (the README names the files that pin the
    tool and tells adopters to add `orqlet validate integrations .orqlet/integrations.yaml` to
    their CI), ADR-003 decision 8 (the README holds one yaml block that it does not touch), AC-1
    ("the CI line with the files that pin the tool") and the interface decision (a block with the
    language `sh`, never `yaml`, and the phrase in the prose around it)."""
    section = integrations()

    shell_blocks = [body for language, body in fenced_blocks(section) if language == "sh"]
    assert any(has_command_line(body, CI_LINE) for body in shell_blocks), (
        f"no fenced `sh` block of the section has the line `{CI_LINE}`"
    )
    assert yaml_blocks(section) == [], "the CI line may not sit in a yaml block"
    assert FILES_THAT_PIN_THE_TOOL in squash(prose_of(section))


def test_the_codes_table_lists_each_code_of_the_integrations_checks() -> None:
    """AC-1. expected_behavior_source: AC-1 ("the codes table lists ORQ-E530 to ORQ-E539, ORQ-W530
    and ORQ-I530 to ORQ-I534"), ADR-003 decision 6 (the families 53x) and the interface decision
    (a full code in the first cell of a row of a table inside the section; the short form `E531`
    under `ORQ-E530` does not count)."""
    listed = codes_in_first_cells(integrations())

    assert sorted(REQUIRED_CODES - listed) == []


def test_the_codes_table_lists_no_other_code_of_the_53x_families() -> None:
    """AC-1. expected_behavior_source: AC-1 (the list of codes is ORQ-E530 to ORQ-E539, ORQ-W530 and
    ORQ-I530 to ORQ-I534) and ADR-003 decision 6 ("the plan names each one"): a code that the plan
    does not name does not exist, so the README does not list it."""
    listed = {
        code
        for code in codes_in_first_cells(integrations())
        if INTEGRATION_FAMILIES.fullmatch(code)
    }

    assert sorted(listed - REQUIRED_CODES) == []


# --- the section: what it does not claim (AC-4) --------------------------------------------------


def test_the_section_does_not_promise_that_a_credential_cannot_be_shared_or_lent() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 12 ("Never another user's credential: not
    enforceable by Orqlet. A person can lend a token or a shell"; "Each user's own credential:
    detectable on demand", the scan can miss a shape). A heuristic over sentences: the words
    guarantees, ensures and prevents next to a credential or sharing, with no word of denial."""
    assert claims_in(integrations(), promises_that_no_credential_is_shared) == []


def test_the_section_does_not_say_that_the_check_covers_every_entry_or_every_server() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 6 (another undeclared entry is "left alone,
    and counted") and decision 12, and plan P-8 file list (the statements that CI validates every
    MCP entry are the ones to correct). The words `every MCP entry` and `all MCP servers`, and the
    forms `every MCP server` and `all MCP entries`, with no word of denial."""
    assert claims_in(integrations(), says_the_check_covers_everything) == []


def test_the_section_does_not_call_the_atlassian_entry_read_only() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 10 ("the generated entry restricts nothing:
    the OAuth consent decides the scopes, so the agent gets the user's Atlassian permissions")
    and decision 12 ("Reach of the entry"). The word `read-only` in a sentence about the entry, the
    server or Atlassian, with no word of denial and no mention of GitHub."""
    assert claims_in(integrations(), calls_the_entry_read_only) == []


# --- outside the section (AC-1, AC-3) ------------------------------------------------------------


def test_the_status_does_not_list_the_mcp_configuration_as_not_built() -> None:
    """AC-1. expected_behavior_source: ADR-003 context and decision 8 (the README says that the MCP
    configuration is not built, A-14; the change makes that wrong), plan P-8 objective ("Update
    the documents that the change makes wrong") and the interface decision (the words `the MCP
    configuration` are not in the paragraph that begins `What is **not** built yet`)."""
    status = section_of(readme(), STATUS_HEADING)
    paragraphs = [p for p in paragraphs_of(status) if p.lstrip().startswith(NOT_BUILT)]
    assert len(paragraphs) == 1, f"the Status must hold one paragraph that begins `{NOT_BUILT}`"

    assert "the MCP configuration" not in squash(paragraphs[0])


def test_the_status_list_of_what_is_built_names_validate_integrations() -> None:
    """AC-1. expected_behavior_source: the interface decision (the Status list of what is built
    names `validate integrations`) and plan P-8 objective ("Update the documents that the change
    makes wrong")."""
    status = section_of(readme(), STATUS_HEADING)
    not_built = next(p for p in paragraphs_of(status) if p.lstrip().startswith(NOT_BUILT))
    built = bullets_of(status[: status.index(not_built)])

    assert built, "the Status holds no list of what is built before the paragraph of what is not"
    assert "validate integrations" in squash(" ".join(built))


def commands_row(name: str) -> list[str]:
    rows = [
        row for row in table_rows(section_of(readme(), COMMANDS_HEADING)) if row[0] == f"`{name}`"
    ]
    if len(rows) != 1:
        pytest.fail(f"the Commands table must hold one row for `{name}`; it holds {len(rows)}")
    return rows[0]


def test_the_commands_table_still_has_one_row_for_validate() -> None:
    """AC-1. expected_behavior_source: the interface decision (the Commands table row of `validate`
    is the row that names `validate integrations`). It holds before the README is changed."""
    assert len(commands_row("validate")) >= 2


def test_the_commands_row_of_validate_names_validate_integrations() -> None:
    """AC-1. expected_behavior_source: the interface decision (the Commands table row of `validate`
    names `validate integrations`) and ADR-003 decision 6 (the new subcommand)."""
    assert "validate integrations" in squash(commands_row("validate")[1])


def test_the_readme_holds_exactly_one_yaml_block_and_it_is_the_one_that_ci_pins() -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 8 and plan P-8 file list (the one yaml block
    that tests/unit/test_readme_ci_snippet.py pins is not touched; the CI line of this section is
    an `sh` block) and the interface decision (the README holds exactly one fenced `yaml` block).
    It holds before the README is changed."""
    blocks = yaml_blocks(readme())

    assert len(blocks) == 1, f"the README holds {len(blocks)} yaml blocks; it may hold one"
    assert blocks[0].split("\n", 1)[0].strip() == CI_SNIPPET_FIRST_LINE
