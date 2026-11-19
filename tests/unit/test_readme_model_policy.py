"""The README and the architecture proposal after the model policy (task dynamic-model-profiles,
phase P-12, AC-2 to AC-5).

Every test cites its `expected_behavior_source`. AC-1 to AC-6 are the acceptance criteria of phase
P-12 in docs/design/dynamic-model-profiles/plan.yaml. ADR-001 to ADR-007 are the files
`adr-00N-*.md` under docs/design/dynamic-model-profiles/design/, and BC-26, C-8 and C-9 are rows of
its component.md. Q-07 is the question about the code review gate in the architecture proposal. "The
interface decision" (R1 to R17 for the README, P1 to P7 for the proposal) is the list of exact
phrases and shapes that the plan author gave the Tester of phase P-12, because the ADRs say what
the documents must say and not in which words.

Reading rules, as the interface decision fixes them. A phrase is matched after the bold markers
`**` are removed, every run of white space (a line break too) is squashed to one space, and the case
is ignored; backticks stay in the phrase. A section of the README runs from its heading to the next
heading of the same or a higher level; a line inside a fenced block is never a heading. A
"paragraph" is a block of text between blank lines. Files are read as UTF-8 and split with
`splitlines()`, so a CRLF checkout reads the same on Windows.

The tests were written before the README and the proposal were changed. The reading rules (the
section, the tables, the numbered list, the sentences, the policy that is read from a fenced block)
are small functions of text. Each is also run on small texts that obey it and on texts that break
it, one of them with CRLF line endings, so a rule that cannot fail would fail here; those tests pass
before the documents change. The tests of the documents' words fail until the documents are
written. Four of them pass on the old text and are named as such in their docstrings: R12 (the old
README has no such sentence), P2 for section 10.3 and for the Q-07 rows (the old text already holds
`required gate`), and the guard of R17 a (the source modules define the 27 codes already).

Some numbers of the interface decision belong to two rules. The second rule of such a number carries
the key suffix `new` (`R12new-...`, `R13new-...`, `R15new-binding-built`), the second rule of R16 is
`proposal_10_3_problems`, and the name of the rule of R14 says what it reads (the rows of ORQ-E544
and ORQ-E547). R10'' is the rule that the identity that ORQ-W460 needs is one that "the policy or
`model_families` names", in the sentence and in the row of ORQ-W460. R15 says that the binding of
the code reviewer is built, in the README, and R16 says the same for section 10.3 of the proposal.

A table of (id, old fragment, new fragment) for each document pins every text edit (criteria A
and B, which the person approved in conversation and which are not in plan.yaml): the new fragment
occurs exactly once and the old one is gone. The ids R-1 to R-3 (the README) and P-1 to P-29 (the
proposal) belong to the edits and are not phase ids. The two texts are compared with each run of
white space squashed to one space, so a line wrap never matters; case and the bold markers stay, so
`**Q-08**` is not `Q-08`. P-19 only appends to its old fragment, so only its new fragment is
pinned. The phrase of R9 about a new session reads `does not satisfy the gate unless both sides were
observed to run different model families` (R-2, P-2a and P-2b). Two strings that the edits leave as
they are are guarded: `five specialist agents` of the README and the heading of section 22.0 of the
proposal.

Behaviour that the sources require but that no phrase fixes is deliberately NOT pinned here:
- where the new section sits in the README, its sub-headings and the order of its parts;
- the words of the one line of meaning of each finding code, except the rows of ORQ-E544 and
  ORQ-E547 (R14), and the order of the rows;
- what the host enforces for a required review (Q-34 was answered on 2026-11-05: nothing enforces
  it): the README may not claim any enforcement, and no test says what it must say instead;
- the wording of the architecture proposal beyond the phrases of P1 to P7, and the values inside the
  policy of section 24.1 beyond the checks of P5.
"""

from __future__ import annotations

import functools
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.documents import DocumentError
from orqlet.interface.cli.exit_codes import ExitCode

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
PROPOSAL = ROOT / "docs" / "design" / "orqlet-architecture-proposal.md"
USE_CASES = ROOT / "src" / "orqlet" / "application" / "usecases"
POLICY_FIXTURE = ROOT / "tests" / "fixtures" / "contracts" / "valid" / "orqlet.model-policy.v2.yaml"

# --- the interface decision: the README ----------------------------------------------------------

SECTION = "## Model policy and the code review gate"
STATUS = "## Status"
COMMANDS = "## Commands"
OPTIONS = "### Options that matter"
UPGRADE = "## Upgrade a project that already uses Orqlet"

POLICY_FILE = ".orqlet/model-policy.yaml"
RESOLVE = "`orqlet models resolve`"
VALIDATE = "`orqlet validate model-policy`"
EXIT_HEADER = ("Command", "Exit", "Meaning")
REQUIRED_STATUSES = frozenset(
    {(RESOLVE, status) for status in (0, 1, 2, 3)} | {(VALIDATE, status) for status in (0, 3, 5)}
)
STATE_HEADER = ("State", "Field", "Meaning")
STATES = ("documented", "approved", "account access", "callable", "evaluated")
STATES_SEPARATE = "none of the five states implies another"
MODE_HEADER = ("Mode", "What it does")
MODES = ("automatic", "manual", "automatic-with-fallbacks")
DEFAULT_MODE = "the default mode is `automatic`"
PRECEDENCE = (
    "an explicit override",
    "a team assignment for the role or skill",
    "a team assignment for the profile",
    "the automatic selection of the client",
)
PIN_RULES = (
    "only the mode `manual` renders a pin",
    "the only pin of the main agent is an explicit assignment of a skill in claude code",
)
FABLE_WORDS = ("Fable", "by model identity", "alias", "id pattern", "family tag")
# A new session of the same client is I1, and I1 does not satisfy the gate, unless both sides were
# observed to run different model families, which gives I2 (the sentences R-2, P-2a and P-2b).
SESSION_NOT_GATE = (
    "does not satisfy the gate unless both sides were observed to run different model families"
)
GATE_PHRASES = (
    "the code review gate is required at every phase",
    "independence I2",
    "is `NOT_RUN` when no reviewer qualifies",
    "a human code-owner review",
    "orqlet has no record for a human code-owner review",
    SESSION_NOT_GATE,
)
GATE_CLAIMS_NOT_MADE = (
    "enforced by the host",
    "branch protection blocks",
    "branch protection requires",
)
AWKWARD_POINTS = (
    "orq-w460 is printed when a record's client differs from the coder's client and at least "
    "one side has no observed identity that the policy or `model_families` names",
    "orq-w461 is printed when both sides ran the same observed model on different clients",
    "neither looks at the class",
    "also when the class is i0",
    "a binding that the staged tree removes stays approved when the base tree approves it",
)
# An overclaim that the code does not bear out: `independence_notes` prints nothing for a record
# whose client differs when the identities are known and the models differ, so "every record" is
# untrue.
AWKWARD_CLAIMS_NOT_MADE = ("printed for every record",)
# R10'': an observed string that matched no catalog model and no family is still unknown
# (`_is_known` of independence.py), so "no observed identity" alone is imprecise; the text of
# `_NOTE_TEXT[IDENTITY_UNKNOWN]` in review_identity.py adds what names an identity.
IDENTITY_NAMED_BY = " that the policy or `model_families` names"
NOTES_SENTENCE = (
    "ORQ-W460 is printed when a record's client differs from the coder's client and at least one "
    f"side has no observed identity{IDENTITY_NAMED_BY}, and ORQ-W461 is printed when both sides "
    "ran the same observed model on different clients. Neither looks at the class, so both are "
    "printed also when the class is I0: they are meant to qualify an I2 that rests on a different "
    "client, and next to an I0 they qualify nothing."
)
OLD_NOTES_SENTENCE = (
    "ORQ-W460 and ORQ-W461 are printed for every record whose client differs from the coder's "
    "client, also when the class is I0: they are meant to qualify an I2 that rests on a different "
    "client, and next to an I0 they qualify nothing."
)
# R12 (new): `models resolve` prints four of the five sources; `explicit-fallback` needs a caller
# that sets `ResolveRequest.fallback`, and no command does.
FALLBACK_PHRASES = (
    "no command names one of them yet",
    "the source of an answer that `models resolve` prints is one of `task-override`, "
    "`role-assignment`, `profile-assignment` and `automatic`",
    "the source `explicit-fallback`, for a fallback that a caller names, but no command names "
    "one yet",
    "`models resolve` never prints it",
)
FALLBACK_CLAIMS_NOT_MADE = ("that an agent may name", "`automatic` and `explicit-fallback`")
FALLBACK_ROW = (
    "| `automatic-with-fallbacks` | As `automatic`: nothing is rendered. The policy adds an "
    "ordered list of fallbacks that `models resolve` prints; no command names one of them yet |"
)
SOURCES_SENTENCE = (
    "The source of an answer that `models resolve` prints is one of `task-override`, "
    "`role-assignment`, `profile-assignment` and `automatic`. The resolver also knows the source "
    "`explicit-fallback`, for a fallback that a caller names, but no command names one yet, so "
    "`models resolve` never prints it."
)
# R13 (new): the recorded values are statements of whoever writes the record.
JUDGEMENT_START = "what is built is the judgement, not the reviewer."
RECORDED_VALUES = (
    "the recorded values are statements of whoever writes the record, and no tool verifies them",
    "a class says how independent a review claims to be",
)
JUDGEMENT_PARAGRAPH = (
    "What is built is the judgement, not the reviewer. `orqlet validate review` derives the "
    "independence class from the recorded values and judges the record against the minimum of "
    "its role. The recorded values are statements of whoever writes the record, and no tool "
    "verifies them: a class says how independent a review claims to be. `orqlet validate plan` "
    "requires `code-reviewer` in the `review_evidence` of every phase of a plan whose header "
    "names workflow 0.5.0 or later."
)
# R14 (new): two rows of the table of codes that say what the check does and does not find.
Meanings = Mapping[str, tuple[str, ...]]
CODE_MEANINGS: Meanings = {
    "ORQ-E544": (
        "an entry that keeps its `id` and loses an alias, a pattern or a tag is not found",
        "the check is skipped without a base tree or for a file given by path",
    ),
    "ORQ-E547": ("or, in `validate model-policy`, the base tree holds it",),
}
ORQ_CODE = re.compile(r"\bORQ-[A-Z]\d{3}\b")
E544_MEANING = (
    "The base tree has an exclusion entry, found by its `id`, that the file lacks; only a "
    "reviewed change removes an exclusion. An entry that keeps its `id` and loses an alias, a "
    "pattern or a tag is not found, and the check is skipped without a base tree or for a file "
    "given by path"
)
E547_MEANING = (
    "The policy file is missing but the lock records it as seeded, or, in "
    "`validate model-policy`, the base tree holds it; `upgrade` writes nothing until it is "
    "restored"
)
# R10'': the row of ORQ-W460 says which identities count as known; it is read with the
# mechanism of R14 and kept apart from it, so that a failure names the round that asked for it.
W460_MEANINGS: Meanings = {
    "ORQ-W460": (f"at least one side has no observed identity{IDENTITY_NAMED_BY}",)
}
W460_MEANING = (
    "The class rests on a different client and at least one side has no observed identity"
    f"{IDENTITY_NAMED_BY} (`identity-unknown`)"
)
NOT_BUILT_PHRASES = (
    "has no `orqlet-code-reviewer` role yet",
    "`review_evidence`",
    "workflow 0.5.0",
)
# R15: the binding of the code reviewer is built, the role is not. Evidence:
# render_all.py (`REVIEW_AGENTS` holds `code-reviewer`; its binding has `independence_capability`
# I2), tests/unit/application/test_lifecycle.py (`init` seeds the third binding) and upgrade.py
# (`_proposes_code_reviewer`, `_pin_notes`: ORQ-I540 and "A `code-reviewer` record is ORQ-E415
# until a reviewed edit applies it. Orqlet never applies the proposal.").
BINDING_BUILT = (
    "the binding for the role is already built",
    "`init` writes it to `.orqlet/role-bindings.yaml`",
    "`upgrade` proposes it to a project whose bindings lack it and says so (orq-i540)",
    "until a reviewed edit applies it a record of the role is orq-e415",
)
BINDING_CLAIMS_NOT_MADE = ("once the package ships the role",)
ROLE_PARAGRAPH = (
    "The workflow package has no `orqlet-code-reviewer` role yet, so the skill `/orqlet-review` "
    "starts two reviewers and the shipped workflow produces no record of the role. The binding "
    "for the role is already built: `init` writes it to `.orqlet/role-bindings.yaml`, and "
    "`upgrade` proposes it to a project whose bindings lack it and says so (ORQ-I540). Orqlet "
    "never applies that proposal, and until a reviewed edit applies it a record of the role is "
    "ORQ-E415."
)
# R16: the sentence of section 10.3 of the proposal about what is not built.
OLD_NOT_BUILT_10_3 = (
    "**What is not built:** the role `orqlet-code-reviewer`, its skill step and its seeded "
    "binding, which ship with workflow 0.5.0."
)
NOT_BUILT_10_3 = (
    "**What is not built:** the role `orqlet-code-reviewer` and its skill step, which ship with "
    "workflow 0.5.0. The binding for the role is built: `init` seeds it in "
    "`.orqlet/role-bindings.yaml` and `upgrade` proposes it to a project that lacks it."
)
PROPOSAL_PRESENT_10_3 = (
    "the role `orqlet-code-reviewer` and its skill step, which ship with workflow 0.5.0",
    "the binding for the role is built",
)
PROPOSAL_ABSENT_10_3 = ("its seeded binding",)
UPGRADE_PARAGRAPH = (
    "a pin changes the bytes of protected agent files and therefore `protected_set_digest`",
    "approvals of designs and plans in flight then show orq-w390",
    "the person decides",
    "the new roles, the changed role and skill text and the version stamps do the same once, "
    "at the upgrade that ships them",
)
OPTION_FLAGS = (
    "--client",
    "--role",
    "--skill",
    "--profile",
    "--task",
    "--override",
    "--different-family-from",
    "--coder-profile",
)
NOT_BUILT = "what is not built yet"

# AC-4: the 27 finding codes of the 54x and 46x families, and the modules that define them.
EXPECTED_CODES = frozenset(
    {f"ORQ-E{number}" for number in range(540, 549)}
    | {f"ORQ-W{number}" for number in range(540, 548)}
    | {"ORQ-I540", "ORQ-E460", "ORQ-E461", "ORQ-I460"}
    | {f"ORQ-W{number}" for number in range(460, 466)}
)
FAMILIES = re.compile(r"\bORQ-[EWI](?:54|46)\d\b")
CODE_HEADER = ("Code", "Meaning")
SOURCE_MODULES = (
    "model_policy_source",
    "model_selection",
    "validate_model_policy",
    "upgrade",
    "pin_staleness",
    "review_identity",
)

# --- the interface decision: the architecture proposal -------------------------------------------

SECTION_HEADINGS = {
    "s10_3": "### 10.3 ",
    "s14_9": "### 14.9 ",
    "s17_12_5": "#### 17.12.5 ",
    "s24_1": "### 24.1 ",
}
GATE_AT_I2 = "the code review gate is required at every phase at independence i2"
REQUIRED_GATE = "required gate"
PER_ROLE_PINS = "per-role pins exist in the mode `manual`"
PROPOSAL_PRESENT_14_9 = (
    "`orqlet.model-policy/v2`",
    "superseded",
    "a pin changes the bytes of the protected agent files and therefore `protected_set_digest`",
)
PROPOSAL_ABSENT_14_9 = (
    "excluded from the `protected_set_digest`",
    "not mistaken for tampering",
)
PROPOSAL_ABSENT_GATE_TEXT = (
    "provided capability",
    "required only by q-07",
    "only where decision q-07 makes it so",
    "keeps the four-role gate set unchanged",
)
Q07_ABSENT = (
    "provided capability only",
    "recommended [r]: (1) until the owners decide",
    "keeps `required: false`",
)
POLICY_SCHEMA = "orqlet.model-policy/v2"
POLICY_PROFILES = ["economy", "engineering", "quality"]

# --- reading Markdown ----------------------------------------------------------------------------

HEADING = re.compile(r"(#{1,6}) ")
CELL_BAR = re.compile(r"(?<!\\)\|")
TABLE_RULE = re.compile(r"\|[\s:|-]*-{3,}[\s:|-]*")
NUMBERED_ITEM = re.compile(r"(\d+)\.\s+(.*)")
UNITS = re.compile(r"(?<=[.!?])\s+|\n\s*\n|\n(?=\s*(?:[-*+]\s|\d+\.\s|\|))")
EXIT_NUMBER = re.compile(r"\d+")


def squash(text: str) -> str:
    """The text with every run of white space (a line break too) as one space; the rest is as is."""
    return " ".join(text.split())


def normalize(text: str) -> str:
    """The text as a phrase is matched against it: no bold markers, one space, lower case."""
    return squash(text.replace("**", "")).lower()


def missing(text: str, phrases: Iterable[str]) -> list[str]:
    found = normalize(text)
    return [phrase for phrase in phrases if normalize(phrase) not in found]


def present(text: str, phrases: Iterable[str]) -> list[str]:
    found = normalize(text)
    return [phrase for phrase in phrases if normalize(phrase) in found]


def plain(cell: str) -> str:
    """A table cell without its backticks and bold markers."""
    return cell.replace("`", "").replace("**", "").strip()


def is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def heading_level(line: str) -> int:
    """The level of a Markdown heading line, and 0 for any other line."""
    match = HEADING.match(line)
    return len(match.group(1)) if match else 0


def headings_of(lines: list[str]) -> list[tuple[int, int]]:
    """The index and the level of each heading line, never one inside a fenced block."""
    found: list[tuple[int, int]] = []
    inside = False
    for index, line in enumerate(lines):
        if is_fence(line):
            inside = not inside
        elif not inside and (level := heading_level(line)):
            found.append((index, level))
    return found


def section_of(text: str, heading: str, *, whole_line: bool = True) -> str:
    """The lines under a heading up to the next heading of the same or a higher level.

    The heading is a whole line, or the start of a line when `whole_line` is false. A heading that
    is missing or that occurs twice fails here, for that reason.
    """
    lines = text.splitlines()
    headings = headings_of(lines)
    starts = [
        index
        for index, _ in headings
        if (lines[index].rstrip() == heading if whole_line else lines[index].startswith(heading))
    ]
    if len(starts) != 1:
        pytest.fail(f"{heading!r} must open a section exactly once; it does so {len(starts)} times")
    level = heading_level(heading)
    end = next(
        (index for index, other in headings if index > starts[0] and other <= level), len(lines)
    )
    return "\n".join(lines[starts[0] + 1 : end])


def fenced_blocks(text: str) -> list[tuple[str, str]]:
    """The language (first word of the info string, lower case) and the body of each fenced block"""
    blocks: list[tuple[str, str]] = []
    language: str | None = None
    body: list[str] = []
    for line in text.splitlines():
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
    """The text without its fenced blocks; each block leaves one blank line behind."""
    kept: list[str] = []
    inside = False
    for line in text.splitlines():
        if is_fence(line):
            inside = not inside
            if not inside:
                kept.append("")
        elif not inside:
            kept.append(line)
    return "\n".join(kept)


def paragraphs_of(text: str) -> list[str]:
    joined = "\n".join(text.splitlines())
    return [paragraph for paragraph in re.split(r"\n\s*\n", joined) if paragraph.strip()]


def cells_of(row: str) -> list[str]:
    inner = row.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in CELL_BAR.split(inner)]


@dataclass(frozen=True)
class Table:
    header: list[str]
    rows: list[list[str]]
    row_lines: list[str]  # each data row as written, trimmed
    next_line: str  # the line after the last row; empty at the end of the text

    @property
    def ends_cleanly(self) -> bool:
        """No text follows the last row on the next line, where Markdown would read a row."""
        return not self.next_line.strip()


def tables_of(text: str) -> list[Table]:
    """Every Markdown table outside a fenced block: a header, a rule and the rows under them."""
    lines = prose_of(text).splitlines()
    tables: list[Table] = []
    index = 0
    while index < len(lines):
        rule = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if not (lines[index].strip().startswith("|") and TABLE_RULE.fullmatch(rule)):
            index += 1
            continue
        header = cells_of(lines[index])
        index += 2
        row_lines: list[str] = []
        while index < len(lines) and lines[index].strip().startswith("|"):
            row_lines.append(lines[index].strip())
            index += 1
        next_line = lines[index] if index < len(lines) else ""
        rows = [cells_of(line) for line in row_lines]
        tables.append(Table(header, rows, row_lines, next_line))
    return tables


def tables_with_header(text: str, header: Sequence[str]) -> list[Table]:
    wanted = [normalize(cell) for cell in header]
    return [table for table in tables_of(text) if [normalize(c) for c in table.header] == wanted]


def rows_under(text: str, header: Sequence[str]) -> list[list[str]]:
    """The data rows of every table with this header. A text with no such table fails here."""
    tables = tables_with_header(text, header)
    if not tables:
        pytest.fail(f"no table has the header cells {' | '.join(header)}")
    return [row for table in tables for row in table.rows]


def rows_starting_with(text: str, start: str) -> list[str]:
    """The table rows outside fenced blocks whose first cell starts with `start` (as a phrase)."""
    wanted = normalize(start)
    return [
        line.strip()
        for line in prose_of(text).splitlines()
        if line.lstrip().startswith("|") and normalize(cells_of(line)[0]).startswith(wanted)
    ]


def bullets_of(text: str) -> list[str]:
    """The items of the bullet lists of the text, each on one line."""
    items: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("- "):
            current = [line.removeprefix("- ").strip()]
            items.append(current)
        elif current is not None and line.strip() and line.startswith((" ", "\t")):
            current.append(line.strip())
        else:
            current = None
    return [" ".join(item) for item in items]


def numbered_lists(text: str) -> list[list[str]]:
    """The lists whose items are numbered 1, 2, 3 and so on from the left margin, one text each."""
    lists: list[list[str]] = []
    current: list[str] | None = None
    for line in prose_of(text).splitlines():
        match = NUMBERED_ITEM.match(line)
        if match and int(match.group(1)) == 1:
            current = [match.group(2)]
            lists.append(current)
        elif match and current is not None and int(match.group(1)) == len(current) + 1:
            current.append(match.group(2))
        elif match:
            current = None
        elif current is not None and line.strip() and line.startswith((" ", "\t")):
            current[-1] += " " + line.strip()
        elif line.strip():
            current = None
    return lists


def units_of(text: str) -> list[str]:
    """The sentences, list items, table rows and lines of code blocks of the text, normalized."""
    pieces = UNITS.split(prose_of(text))
    code = [line for _, body in fenced_blocks(text) for line in body.splitlines()]
    return [normalize(piece) for piece in [*pieces, *code] if piece.strip()]


def units_with_all(text: str, words: Iterable[str]) -> list[str]:
    wanted = [normalize(word) for word in words]
    return [unit for unit in units_of(text) if all(word in unit for word in wanted)]


# --- reading the tables of the README ------------------------------------------------------------


def is_exit_row(row: list[str]) -> bool:
    """A command of the two, one integer and a meaning (R3)."""
    return (
        len(row) == 3
        and normalize(row[0]) in {RESOLVE, VALIDATE}
        and EXIT_NUMBER.fullmatch(plain(row[1])) is not None
        and bool(row[2].strip())
    )


def malformed_exit_rows(rows: list[list[str]]) -> list[list[str]]:
    return [row for row in rows if not is_exit_row(row)]


def exit_pairs(rows: list[list[str]]) -> set[tuple[str, int]]:
    return {(normalize(row[0]), int(plain(row[1]))) for row in rows if is_exit_row(row)}


def first_cells(rows: list[list[str]]) -> list[str]:
    """The first cell of each row, without backticks, sorted so that the order does not count."""
    return sorted(normalize(plain(row[0])) for row in rows)


@dataclass(frozen=True)
class CodeRow:
    cell: str  # the first cell without backticks and bold markers
    meaning: str
    line: str
    table_ends_cleanly: bool


def code_rows(text: str) -> list[CodeRow]:
    """The rows of the tables `Code | Meaning` whose first cell holds a code of the 54x or 46x."""
    rows: list[CodeRow] = []
    for table in tables_with_header(text, CODE_HEADER):
        for cells, line in zip(table.rows, table.row_lines, strict=True):
            cell = plain(cells[0])
            if FAMILIES.search(cell):
                meaning = cells[1] if len(cells) > 1 else ""
                rows.append(CodeRow(cell, meaning, line, table.ends_cleanly))
    return rows


def codes_listed(rows: list[CodeRow]) -> set[str]:
    return {code for row in rows for code in FAMILIES.findall(row.cell)}


def is_code(row: CodeRow) -> bool:
    return FAMILIES.fullmatch(row.cell) is not None


def code_row_problems(rows: list[CodeRow]) -> list[str]:
    """R17 (c): each expected code is the whole first cell of exactly one row."""
    problems = [f"{row.cell!r}: the first cell is not one code" for row in rows if not is_code(row)]
    counts = Counter(row.cell for row in rows)
    problems += [f"{code}: {count} rows" for code, count in sorted(counts.items()) if count > 1]
    problems += [f"{code}: no row" for code in sorted(EXPECTED_CODES - set(counts))]
    return problems


def code_shape_problems(rows: list[CodeRow]) -> list[str]:
    """R17 (d): a meaning that is not empty, on the same physical line as its code."""
    problems: list[str] = []
    for row in rows:
        if not row.meaning:
            problems.append(f"{row.cell}: the meaning is empty")
        if not row.line.endswith("|") or row.line.endswith("\\|"):
            problems.append(f"{row.cell}: the row does not close with a bar on its own line")
        if not row.table_ends_cleanly:
            problems.append(f"{row.cell}: a line follows the table with no blank line between")
    return problems


def source_codes() -> set[str]:
    """The codes of the 54x and 46x families that the six source modules name (R17 a)."""
    return {
        code
        for name in SOURCE_MODULES
        for code in FAMILIES.findall((USE_CASES / f"{name}.py").read_text(encoding="utf-8"))
    }


# --- the documents -------------------------------------------------------------------------------


@functools.cache
def readme_text() -> str:
    return README.read_text(encoding="utf-8")


@functools.cache
def proposal_text() -> str:
    return PROPOSAL.read_text(encoding="utf-8")


def policy_section() -> str:
    return section_of(readme_text(), SECTION)


@functools.cache
def proposal_section(name: str) -> str:
    return section_of(proposal_text(), SECTION_HEADINGS[name], whole_line=False)


def q07_rows() -> list[str]:
    rows = rows_starting_with(proposal_text(), "Q-07")
    if not rows:
        pytest.fail("the proposal has no table row whose first cell starts with Q-07")
    return rows


def proposal_blocks(name: str) -> list[str]:
    """The texts that stand for `name`: a section, or each Q-07 row."""
    return q07_rows() if name == "q07" else [proposal_section(name)]


def in_any(blocks: list[str], phrase: str) -> bool:
    return any(not missing(block, [phrase]) for block in blocks)


def policy_of(markdown: str, *, source: str) -> ModelPolicy:
    """The first yaml block of the text, read with the strict loader and checked as a policy."""
    blocks = [body for language, body in fenced_blocks(markdown) if language == "yaml"]
    if not blocks:
        pytest.fail(f"{source} holds no fenced yaml block")
    data = blocks[0].encode("utf-8")
    try:
        return load_contract(StrictYamlLoader(), ModelPolicy, data, source=source)
    except DocumentError as error:
        pytest.fail(f"the first yaml block is not a valid model policy: {error}")


def profile_ids(policy: ModelPolicy) -> list[str]:
    return sorted(profile.id for profile in policy.profiles)


def assignment_modes(policy: ModelPolicy) -> set[str]:
    return {assignment.mode for assignment in policy.assignments}


def assignment_kinds(policy: ModelPolicy) -> set[str]:
    return {assignment.target.kind for assignment in policy.assignments}


# --- the rules of the new README section (R2 to R11) and of the upgrade paragraph (R16) ----------
# A rule reads the text of a section and returns what is wrong with it, so that the same rule runs
# on the README and on a reference text that obeys it.


def lacks(text: str, phrases: Iterable[str]) -> list[str]:
    return [f"lacks: {phrase}" for phrase in missing(text, phrases)]


def says(text: str, phrases: Iterable[str]) -> list[str]:
    return [f"says: {phrase}" for phrase in present(text, phrases)]


def policy_file_problems(section: str) -> list[str]:
    return lacks(section, [POLICY_FILE])


def exit_row_problems(section: str) -> list[str]:
    rows = malformed_exit_rows(rows_under(section, EXIT_HEADER))
    return [f"malformed row: {' | '.join(row)}" for row in rows]


def exit_status_problems(section: str) -> list[str]:
    pairs = exit_pairs(rows_under(section, EXIT_HEADER))
    absent = sorted(REQUIRED_STATUSES - pairs)
    return [f"no row for {command}, status {status}" for command, status in absent]


def state_problems(section: str) -> list[str]:
    problems = lacks(section, [STATES_SEPARATE])
    if first_cells(rows_under(section, STATE_HEADER)) != sorted(STATES):
        problems.append("the first cells of the table of states are not the five states")
    return problems


def mode_problems(section: str) -> list[str]:
    problems = lacks(section, [DEFAULT_MODE])
    if first_cells(rows_under(section, MODE_HEADER)) != sorted(MODES):
        problems.append("the first cells of the table of modes are not the three modes")
    return problems


def precedence_problems(section: str) -> list[str]:
    lists = [items for items in numbered_lists(section) if not missing(items[0], PRECEDENCE[:1])]
    if not lists:
        return ["no numbered list starts with an explicit override"]
    if len(lists[0]) != len(PRECEDENCE):
        return [f"the list has {len(lists[0])} items, not {len(PRECEDENCE)}"]
    return [
        f"item {number} lacks: {phrase}"
        for number, (item, phrase) in enumerate(zip(lists[0], PRECEDENCE, strict=True), start=1)
        if missing(item, [phrase])
    ]


def pin_problems(section: str) -> list[str]:
    return lacks(section, PIN_RULES)


def fable_problems(section: str) -> list[str]:
    if any(not missing(paragraph, FABLE_WORDS) for paragraph in paragraphs_of(section)):
        return []
    return ["no paragraph holds all of: " + ", ".join(FABLE_WORDS)]


def gate_problems(section: str) -> list[str]:
    return lacks(section, GATE_PHRASES)


def gate_claim_problems(section: str) -> list[str]:
    return says(section, GATE_CLAIMS_NOT_MADE)


def awkward_point_problems(section: str) -> list[str]:
    return lacks(section, AWKWARD_POINTS) + says(section, AWKWARD_CLAIMS_NOT_MADE)


def fallback_source_problems(section: str) -> list[str]:
    """R12 (new): no command names a fallback, so `models resolve` never prints its source."""
    return lacks(section, FALLBACK_PHRASES) + says(section, FALLBACK_CLAIMS_NOT_MADE)


def judgement_problems(section: str) -> list[str]:
    """R13 (new): the paragraph that says what is built says that no tool verifies the values."""
    paragraphs = [p for p in paragraphs_of(section) if normalize(p).startswith(JUDGEMENT_START)]
    if len(paragraphs) != 1:
        return [f"{len(paragraphs)} paragraphs start with: {JUDGEMENT_START}"]
    return lacks(paragraphs[0], RECORDED_VALUES)


def binding_built_problems(section: str) -> list[str]:
    """R15: the binding of the code reviewer is built; only the role is not."""
    return lacks(section, BINDING_BUILT) + says(section, BINDING_CLAIMS_NOT_MADE)


def proposal_10_3_problems(section: str) -> list[str]:
    """R16: section 10.3 says that the binding is built and the role is not."""
    return lacks(section, PROPOSAL_PRESENT_10_3) + says(section, PROPOSAL_ABSENT_10_3)


def code_meaning_problems(text: str, meanings: Meanings = CODE_MEANINGS) -> list[str]:
    """R14 (new): the rows of ORQ-E544 and ORQ-E547 say what the checks find and do not find.

    R10'' reads the row of ORQ-W460 with the same function and the meanings `W460_MEANINGS`.
    """
    rows = {row.cell: row for row in code_rows(text)}
    problems: list[str] = []
    for code, phrases in meanings.items():
        row = rows.get(code)
        if row is None:
            problems.append(f"{code}: no row")
            continue
        problems += [f"{code} lacks: {phrase}" for phrase in missing(row.meaning, phrases)]
        problems += [f"{code} names {named}" for named in ORQ_CODE.findall(row.meaning)]
    return problems


def not_built_problems(section: str) -> list[str]:
    return lacks(section, NOT_BUILT_PHRASES)


def upgrade_problems(section: str) -> list[str]:
    if any(not missing(paragraph, UPGRADE_PARAGRAPH) for paragraph in paragraphs_of(section)):
        return []
    return ["no paragraph holds all of: " + "; ".join(UPGRADE_PARAGRAPH)]


SECTION_RULES: dict[str, Callable[[str], list[str]]] = {
    "R2-policy-file": policy_file_problems,
    "R3-exit-rows": exit_row_problems,
    "R3-exit-statuses": exit_status_problems,
    "R4-states": state_problems,
    "R5-modes": mode_problems,
    "R6-precedence": precedence_problems,
    "R7-pins": pin_problems,
    "R8-fable": fable_problems,
    "R9-gate": gate_problems,
    "R9-claims-not-made": gate_claim_problems,
    "R10-awkward-points": awkward_point_problems,
    "R11-not-built": not_built_problems,
    "R12new-fallback-source": fallback_source_problems,
    "R13new-recorded-values": judgement_problems,
    "R15new-binding-built": binding_built_problems,
}

# A text that obeys every rule of the new section, written in the words of the interface decision.
REFERENCE_SECTION = f"""\
Orqlet reads the policy of a team from `.orqlet/model-policy.yaml`.

| Command | Exit | Meaning |
|---|---|---|
| `orqlet models resolve` | 0 | a model was selected, or the mode is `automatic` |
| `orqlet models resolve` | 1 | no model qualifies |
| `orqlet models resolve` | 2 | wrong options |
| `orqlet models resolve` | 3 | refused |
| `orqlet validate model-policy` | 0 | PASS |
| `orqlet validate model-policy` | 3 | refused, for example outside a Git repository |
| `orqlet validate model-policy` | 5 | FAIL or NOT_RUN |

| State | Field | Meaning |
|---|---|---|
| `documented` | `documented` | a page of the vendor says that the model exists |
| `approved` | `approval.state` | the team approved it in a reviewed change |
| `account access` | `routes[].access` | the account of the team can reach it |
| `callable` | `callable` | a check called it |
| `evaluated` | `evaluated` | a report rates it for a role |

None of the five states implies another.

| Mode | What it does |
|---|---|
| `automatic` | nothing is rendered and the client chooses |
| `manual` | a pin is rendered |
{FALLBACK_ROW}

The default mode is `automatic`. Only the mode `manual` renders a pin, and the only pin of the
main agent is an explicit assignment of a skill in Claude Code.

The order of precedence, highest first:

1. an explicit override;
2. a team assignment for the role or skill;
3. a team assignment for the profile;
4. the automatic selection of the client.

{SOURCES_SENTENCE}

**Fable** is excluded by model identity: an `excluded` entry matches by alias, by id pattern and
by family tag.

The code review gate is required at every phase, at independence I2. The review is `NOT_RUN` when
no reviewer qualifies, and then a human code-owner review takes its place. Orqlet has no record
for a human code-owner review.
A new session of the same client {SESSION_NOT_GATE}; without that it is I1.

{JUDGEMENT_PARAGRAPH} {ROLE_PARAGRAPH}

{NOTES_SENTENCE} A binding that the staged tree removes stays approved when the base tree
approves it.
"""

# For each rule, a change to the reference text that breaks that rule and no other that matters.
BREAKS: dict[str, tuple[str, str]] = {
    "R2-policy-file": (".orqlet/model-policy.yaml", "the policy file"),
    "R3-exit-rows": ("| `orqlet models resolve` | 0 |", "| `orqlet models resolve` | zero |"),
    "R3-exit-statuses": ("| `orqlet validate model-policy` | 5 | FAIL or NOT_RUN |\n", ""),
    "R4-states": ("| `evaluated` | `evaluated` |", "| `ranked` | `evaluated` |"),
    "R5-modes": ("| `manual` | a pin", "| `fixed` | a pin"),
    "R6-precedence": ("a team assignment for the profile", "a team assignment for the group"),
    "R7-pins": ("Only the mode `manual` renders a pin", "Every mode renders a pin"),
    "R8-fable": ("by model identity", "by name"),
    "R9-gate": ("at independence I2", "at independence I1"),
    "R9-claims-not-made": (
        "different model families; without that it is I1.",
        "different model families; without that it is I1. Branch protection blocks the merge.",
    ),
    "R10-awkward-points": ("also when the class is I0", "when it is another class"),
    "R11-not-built": ("workflow 0.5.0", "a later workflow"),
    "R12new-fallback-source": ("`models resolve` never prints it", "`models resolve` prints it"),
    "R13new-recorded-values": (
        "a class says how independent a review claims to be",
        "a class says how independent a review is",
    ),
    "R15new-binding-built": (
        "The binding for the role is already built",
        "The binding for the role is not built",
    ),
}

# More ways to break the rules, each with the problem that it must give:
# (rule, old text, new text, the problem that the rule reports for the new text).
MORE_BREAKS: list[tuple[str, str, str, str]] = [
    (
        "R10-awkward-points",
        "at least one side has no observed identity",
        "at least one side is unknown",
        "lacks: orq-w460 is printed when a record's client differs from the coder's client",
    ),
    (
        "R10-awkward-points",
        f"{IDENTITY_NAMED_BY}, and ORQ-W461",
        ", and ORQ-W461",
        "lacks: orq-w460 is printed when a record's client differs from the coder's client and at "
        "least one side has no observed identity that the policy",
    ),
    (
        "R10-awkward-points",
        "ran the same observed model on different clients",
        "ran the same model",
        "lacks: orq-w461 is printed when both sides ran the same observed model",
    ),
    (
        "R10-awkward-points",
        "Neither looks at the class",
        "Both look at the class",
        "lacks: neither looks at the class",
    ),
    (
        "R12new-fallback-source",
        "; no command names one of them yet",
        " and that an agent may name when the automatic choice is unavailable",
        "says: that an agent may name",
    ),
    (
        "R12new-fallback-source",
        "`profile-assignment` and `automatic`. The resolver",
        "`profile-assignment`, `automatic` and `explicit-fallback`. The resolver",
        "says: `automatic` and `explicit-fallback`",
    ),
    (
        "R12new-fallback-source",
        "for a fallback that a caller names, but no command names one yet, so",
        "for a fallback that an agent names, so",
        "lacks: the source `explicit-fallback`, for a fallback that a caller names",
    ),
    (
        "R13new-recorded-values",
        "whoever writes the record, and no tool verifies them",
        "whoever writes the record, and Orqlet verifies them",
        "lacks: the recorded values are statements of whoever writes the record",
    ),
    (
        "R13new-recorded-values",
        "against the minimum of its role. The recorded values",
        "against the minimum of its role.\n\nThe recorded values",
        "lacks: the recorded values are statements of whoever writes the record",
    ),
    (
        "R13new-recorded-values",
        "What is built is the judgement, not the reviewer.",
        "What is built is the judgement.",
        f"0 paragraphs start with: {JUDGEMENT_START}",
    ),
    (
        "R15new-binding-built",
        "`init` writes it to `.orqlet/role-bindings.yaml`",
        "`init` writes it to the project",
        "lacks: `init` writes it to `.orqlet/role-bindings.yaml`",
    ),
    (
        "R15new-binding-built",
        "and `upgrade` proposes it to a project whose bindings lack it and says so (ORQ-I540)",
        "and `upgrade` proposes it",
        "lacks: `upgrade` proposes it to a project whose bindings lack it and says so",
    ),
    (
        "R15new-binding-built",
        "until a reviewed edit applies it a record of the role is ORQ-E415",
        "a record of the role is invalid until a reviewed edit does",
        "lacks: until a reviewed edit applies it a record of the role is orq-e415",
    ),
    (
        "R15new-binding-built",
        "The binding for the role is already built:",
        "Once the package ships the role, the binding for the role is already built:",
        "says: once the package ships the role",
    ),
    (
        "R9-gate",
        f"{SESSION_NOT_GATE};",
        "does not satisfy the gate;",
        f"lacks: {SESSION_NOT_GATE}",
    ),
]

REFERENCE_UPGRADE = """\
After `orqlet upgrade`, read this: a pin changes the bytes of protected agent files and therefore
`protected_set_digest`. Approvals of designs and plans in flight then show ORQ-W390, and
the person decides. The new roles, the changed role and skill text and the version stamps do the
same once, at the upgrade that ships them.

Start a new session in the client.
"""

# A table of codes in the words of the interface decision R14; the rows of
# other codes stand next to the two that the rule reads.
REFERENCE_CODE_ROWS = f"""\
Finding codes of the model policy.

| Code | Meaning |
|---|---|
| ORQ-E543 | A model matches an exclusion |
| ORQ-E544 | {E544_MEANING} |
| ORQ-E545 | The policy has a duplicate id; see ORQ-E541 |
| ORQ-E547 | {E547_MEANING} |
| ORQ-W460 | {W460_MEANING} |
"""

# Ways to break the reference table of codes: (old text, new text, the problem that must be given).
CODE_BREAKS: list[tuple[str, str, str]] = [
    (
        "An entry that keeps its `id` and loses an alias, a pattern or a tag is not found, and",
        "An entry that loses an alias, a pattern or a tag is found, and",
        "ORQ-E544 lacks: an entry that keeps its `id` and loses an alias",
    ),
    (
        "the check is skipped without a base tree or for a file given by path",
        "the check always runs",
        "ORQ-E544 lacks: the check is skipped without a base tree or for a file given by path",
    ),
    (
        "or, in `validate model-policy`, the base tree holds it",
        "or the base tree holds it",
        "ORQ-E547 lacks: or, in `validate model-policy`, the base tree holds it",
    ),
    (
        "given by path |",
        "given by path (see ORQ-E106) |",
        "ORQ-E544 names ORQ-E106",
    ),
    (
        "until it is restored |",
        "until it is restored (ORQ-W540) |",
        "ORQ-E547 names ORQ-W540",
    ),
    (
        "| ORQ-E547 |",
        "| ORQ-E548 |",
        "ORQ-E547: no row",
    ),
]

# The same for the row of ORQ-W460 (R10'').
W460_BREAKS: list[tuple[str, str, str]] = [
    (
        f"{IDENTITY_NAMED_BY} (`identity-unknown`)",
        " (`identity-unknown`)",
        "ORQ-W460 lacks: at least one side has no observed identity that the policy",
    ),
    (
        "(`identity-unknown`) |",
        "(`identity-unknown`, see ORQ-W461) |",
        "ORQ-W460 names ORQ-W461",
    ),
    (
        "| ORQ-W460 |",
        "| ORQ-W466 |",
        "ORQ-W460: no row",
    ),
]
ROW_BREAK_CASES: list[tuple[Meanings, str, str, str]] = [
    *((CODE_MEANINGS, old, new, expected) for old, new, expected in CODE_BREAKS),
    *((W460_MEANINGS, old, new, expected) for old, new, expected in W460_BREAKS),
]

# The proposal around section 10.3 in the words of R16: the sentence stands in the
# paragraph of the real text, next to its neighbours. Section 10.4 holds the old sentence, which
# the rule must not read, because it reads section 10.3 only.
REFERENCE_PROPOSAL = f"""\
## 10. Roles

### 10.3 Role catalogue (the base set)

The **required roles** of Phase 4 are the Coder, the Tester, the Architecture Reviewer, the Security
Reviewer and the Code Reviewer. The code review gate is a required gate. **What is built:** the
validators. {NOT_BUILT_10_3} Phase 1 uses specialist researchers.

### 10.4 Parallelism, reviewer independence and substitution

{OLD_NOT_BUILT_10_3}
"""


def reference_10_3(text: str = REFERENCE_PROPOSAL) -> str:
    """Section 10.3 of a proposal, read as the AC-5 tests read it."""
    return section_of(text, SECTION_HEADINGS["s10_3"], whole_line=False)


# --- the reading rules are sound -----------------------------------------------------------------


def test_a_phrase_is_matched_without_bold_markers_with_one_space_and_in_any_case() -> None:
    """AC-2. expected_behavior_source: the interface decision (the matching rule for every phrase).
    It passes before the documents change."""
    text = "The **Code** review\r\n  gate   IS\tRequired. Keep `a  b`."

    assert normalize(text) == "the code review gate is required. keep `a b`."
    assert missing(text, ["code review gate is required", "keep `a b`", "no such phrase"]) == [
        "no such phrase"
    ]
    assert present(text, ["CODE REVIEW", "keep `a  b`", "gate is optional"]) == [
        "CODE REVIEW",
        "keep `a  b`",
    ]


def test_a_section_runs_to_the_next_heading_of_the_same_or_a_higher_level() -> None:
    """AC-2. expected_behavior_source: the interface decision (a section of the README runs from its
    heading to the next heading of level 2; the proposal's sections run to the next heading of
    their own level or a higher one, and a section of level 3 keeps its level-4 subsections). It
    passes before the documents change."""
    text = "# T\n## A\none\n### Sub\ntwo\n#### Deep\nthree\n## B\nfour\n"

    assert section_of(text, "## A") == "one\n### Sub\ntwo\n#### Deep\nthree"
    assert section_of(text, "### Sub") == "two\n#### Deep\nthree"
    assert section_of(text, "#### Deep") == "three"
    assert section_of(text, "## B") == "four"


def test_a_section_ignores_headings_in_fenced_blocks_and_reads_crlf_and_a_prefix() -> None:
    """AC-5. expected_behavior_source: the interface decision (the proposal's sections are found by
    the start of their heading line, `### 10.3 `; a text with CRLF line endings reads the same).
    It passes before the documents change."""
    text = "### 10.3 Role catalogue\r\nbody\r\n```sh\r\n## not one\r\n```\r\nmore\r\n### 10.4 N\r\n"

    assert section_of(text, "### 10.3 ", whole_line=False) == "body\n```sh\n## not one\n```\nmore"
    with pytest.raises(pytest.fail.Exception):
        section_of(text, "### 10.3", whole_line=True)


@pytest.mark.parametrize(
    ("text", "heading"),
    [
        pytest.param("## A\nx\n", "## B", id="missing"),
        pytest.param("## A\nx\n## B\n## A\ny\n", "## A", id="repeated"),
        pytest.param("### A\nx\n", "## A", id="other-level"),
        pytest.param("```\n## A\n```\n", "## A", id="only-in-a-fence"),
    ],
)
def test_a_heading_that_is_missing_or_repeated_fails_the_reader(text: str, heading: str) -> None:
    """AC-2. expected_behavior_source: the interface decision (R1: the heading exists exactly once).
    It passes before the documents change."""
    with pytest.raises(pytest.fail.Exception):
        section_of(text, heading)


def test_fenced_blocks_are_read_with_their_language_and_prose_leaves_a_blank_line() -> None:
    """AC-5. expected_behavior_source: the interface decision (P5: the first fenced block that
    starts with ```yaml). It passes before the documents change."""
    lines = [
        "a",
        "```sh",
        "x",
        "```",
        "b",
        "``` YAML title",
        "k: v",
        "",
        "```",
        "```",
        "plain",
        "```",
    ]
    text = "\r\n".join(lines) + "\r\n"

    assert fenced_blocks(text) == [("sh", "x"), ("yaml", "k: v\n"), ("", "plain")]
    assert prose_of(text) == "a\n\nb\n\n"


TABLES = (
    "intro\n\n"
    "| A | B |\n|---|:-:|\n| `x` | one \\| two |\n| y | |\n\n"
    "```text\n| A | B |\n|---|---|\n| z | in a block |\n```\n"
    "| C | D |\n| --- | --- |\n| 1 | 2 |\nlazy line\n"
)


def test_tables_are_read_with_escaped_bars_and_never_from_a_fenced_block() -> None:
    """AC-2. expected_behavior_source: the interface decision (R3 to R5, R14, R15 and R17 read the
    tables by their header cells; a row may hold an escaped bar). It passes before the documents
    change."""
    first, second = tables_of(TABLES)

    assert first.header == ["A", "B"]
    assert first.rows == [["`x`", "one \\| two"], ["y", ""]]
    assert first.ends_cleanly
    assert second.header == ["C", "D"]
    assert second.rows == [["1", "2"]]
    assert not second.ends_cleanly
    assert [t.header for t in tables_with_header(TABLES, ("c", " D "))] == [["C", "D"]]
    assert tables_of(TABLES.replace("\n", "\r\n")) == tables_of(TABLES)


def test_a_text_with_no_table_of_the_header_fails_the_row_reader() -> None:
    """AC-2. expected_behavior_source: the interface decision (R3: a table with these header cells
    must exist). It passes before the documents change."""
    assert rows_under(TABLES, ("A", "B")) == [["`x`", "one \\| two"], ["y", ""]]
    with pytest.raises(pytest.fail.Exception):
        rows_under(TABLES, ("A", "C"))


def test_rows_are_found_by_the_start_of_their_first_cell_without_bold_markers() -> None:
    """AC-5. expected_behavior_source: the interface decision (the Q-07 rows are the table rows
    whose first cell, with `**` removed, starts with Q-07). It passes before the documents
    change."""
    text = (
        "| Id | T |\n|---|---|\n| Q-06 | no |\n| **Q-07** (v0.5) | yes |\n| Q-07 (done) | yes |\n"
        "```text\n| Q-07 in a block | no |\n```\nQ-07 as plain text\n"
    )

    assert rows_starting_with(text, "Q-07") == [
        "| **Q-07** (v0.5) | yes |",
        "| Q-07 (done) | yes |",
    ]


def test_the_items_of_a_numbered_list_are_joined_with_their_continuation_lines() -> None:
    """AC-2. expected_behavior_source: the interface decision (R6: an ordered list of four
    consecutive items numbered 1. to 4.). It passes before the documents change."""
    text = "intro\n1. one,\n   more\n2. two\n\n3. three\n4. four\nafter\n1. again\n3. skipped\n"

    assert numbered_lists(text) == [["one, more", "two", "three", "four"], ["again"]]


def test_the_bullets_of_a_list_are_joined_with_their_continuation_lines() -> None:
    """AC-2. expected_behavior_source: the interface decision (R13: the Status list of what is
    built). It passes before the documents change."""
    text = "Intro:\n\n- one,\n  two;\n- three;\n\nafter\n- four\n"

    assert bullets_of(text) == ["one, two;", "three;", "four"]


def test_the_units_of_a_text_are_its_sentences_list_items_rows_and_code_lines() -> None:
    """AC-2. expected_behavior_source: the interface decision (R12: no sentence holds both words;
    sentences end at `.`, `!` or `?` followed by white space). It passes before the documents
    change."""
    text = "One two\nthree. Four!\n\n- five\n- six\n| a | b |\n```sh\nseven. eight\n```\n"

    assert units_of(text) == [
        "one two three.",
        "four!",
        "- five",
        "- six",
        "| a | b |",
        "seven. eight",
    ]


def test_a_sentence_with_both_words_is_found_and_two_rows_or_two_sentences_are_not_one() -> None:
    """AC-2. expected_behavior_source: the interface decision (R12: no sentence of the README holds
    both `code review` and `optional`, or both `code reviewer` and `provided capability`). It
    passes before the documents change."""
    text = (
        "The code reviewer is optional. It runs.\r\n\r\n| Role | Note |\r\n|---|---|\r\n"
        "| code review | required |\r\n| other | OPTIONAL |\r\n"
    )

    assert units_with_all(text, ("code review", "optional")) == ["the code reviewer is optional."]
    assert units_with_all(text, ("code reviewer", "provided capability")) == []


def test_an_exit_row_needs_one_of_the_two_commands_an_integer_and_a_meaning() -> None:
    """AC-2. expected_behavior_source: the interface decision (R3: the first cell is exactly one of
    the two commands, the second one integer, the third a non-empty text). It passes before the
    documents change."""
    good = [[RESOLVE, "0", "selected"], [VALIDATE, "`5`", "FAIL or NOT_RUN"]]
    bad = [
        ["`orqlet models resolve --json`", "0", "x"],
        [RESOLVE, "zero", "x"],
        [RESOLVE, "0, 1", "x"],
        [RESOLVE, "1", " "],
        [RESOLVE, "1"],
    ]

    assert malformed_exit_rows(good) == []
    assert malformed_exit_rows([*good, *bad]) == bad
    assert exit_pairs(good) == {(RESOLVE, 0), (VALIDATE, 5)}


def test_the_first_cells_of_a_table_are_read_without_backticks_and_in_any_order() -> None:
    """AC-2. expected_behavior_source: the interface decision (R4 and R5: the first cells, with
    backticks removed, are exactly the five states and the three modes, in any order). It passes
    before the documents change."""
    rows = [["`Manual`", "x"], ["**automatic**", "y"], ["`automatic-with-fallbacks`", "z"]]

    assert first_cells(rows) == sorted(MODES)


def test_the_codes_table_is_read_from_the_tables_with_the_header_code_and_meaning() -> None:
    """AC-4. expected_behavior_source: the interface decision (R17: every table whose header cells
    are `Code | Meaning` is read; the first cell is a code, optionally in backticks; only the
    families 54x and 46x count). It passes before the documents change."""
    text = (
        "| Code | Meaning |\n|---|---|\n| `ORQ-E540` | one |\n| ORQ-W461 | two |\n"
        "| ORQ-E530 | another family |\n| ORQ-E541, ORQ-E542 | two codes |\n| ORQ-I460 | |\n\n"
        "| Code | Other |\n|---|---|\n| ORQ-E543 | other header |\n"
    )
    rows = code_rows(text.replace("\n", "\r\n"))

    assert [row.cell for row in rows] == ["ORQ-E540", "ORQ-W461", "ORQ-E541, ORQ-E542", "ORQ-I460"]
    assert codes_listed(rows) == {"ORQ-E540", "ORQ-W461", "ORQ-E541", "ORQ-E542", "ORQ-I460"}
    assert code_shape_problems(rows) == ["ORQ-I460: the meaning is empty"]


def test_a_missing_a_repeated_and_a_combined_code_are_each_a_problem() -> None:
    """AC-4. expected_behavior_source: the interface decision (R17 c: each of the 27 codes is the
    first cell of exactly one row; one code per cell). It passes before the documents change."""
    rows = [CodeRow(code, "m", f"| {code} | m |", True) for code in sorted(EXPECTED_CODES)]
    assert code_row_problems(rows) == []

    combined = CodeRow("ORQ-E540, ORQ-E541", "m", "|", True)
    problems = code_row_problems([*rows[1:], rows[2], combined])

    assert f"{rows[0].cell}: no row" in problems
    assert f"{rows[2].cell}: 2 rows" in problems
    assert "'ORQ-E540, ORQ-E541': the first cell is not one code" in problems
    assert len(problems) == 3


def test_a_row_cut_over_two_lines_or_followed_by_text_is_not_one_physical_line() -> None:
    """AC-4. expected_behavior_source: the interface decision (R17 d: the row is one physical
    line). It passes before the documents change."""
    cut = "| Code | Meaning |\n|---|---|\n| ORQ-E540 | the meaning\n  goes on |\n\n"
    lazy = "| Code | Meaning |\n|---|---|\n| ORQ-E540 | one line |\ncontinued text\n"
    whole = "| Code | Meaning |\n|---|---|\n| ORQ-E540 | one line |\r\n\r\ntext\r\n"

    assert code_shape_problems(code_rows(whole)) == []
    assert code_shape_problems(code_rows(cut)) == [
        "ORQ-E540: the row does not close with a bar on its own line",
        "ORQ-E540: a line follows the table with no blank line between",
    ]
    assert code_shape_problems(code_rows(lazy)) == [
        "ORQ-E540: a line follows the table with no blank line between"
    ]


def test_a_policy_is_read_from_the_first_yaml_block_and_a_bad_block_fails() -> None:
    """AC-5. expected_behavior_source: the interface decision (P5: the first fenced block that
    starts with ```yaml is loaded with the strict loader and validated as `ModelPolicy`) and the
    valid sample tests/fixtures/contracts/valid/orqlet.model-policy.v2.yaml. It passes before the
    documents change."""
    fixture = POLICY_FIXTURE.read_text(encoding="utf-8")
    markdown = f"```text\nx: 1\n```\n```yaml\n{fixture}\n```\n```yaml\nnot: valid\n```\n"

    policy = policy_of(markdown.replace("\n", "\r\n"), source="a sample")

    assert policy.schema_id == POLICY_SCHEMA
    assert profile_ids(policy) == POLICY_PROFILES
    assert assignment_modes(policy) == {"automatic", "manual"}
    assert assignment_kinds(policy) == {"role", "skill"}
    not_a_policy = "```yaml\npolicy_version: 0.0.0-draft\n```\n"
    duplicate_key = "```yaml\na: 1\na: 2\n```\n"
    for broken in (not_a_policy, duplicate_key, "no block at all"):
        with pytest.raises(pytest.fail.Exception):
            policy_of(broken, source="a sample")


# --- the README: the section and the commands (AC-2) ---------------------------------------------


def test_the_readme_holds_the_section_once() -> None:
    """AC-2. expected_behavior_source: the interface decision R1 (the heading
    `## Model policy and the code review gate` exists exactly once) and plan P-12 file list
    (README.md: documents the policy, the two commands, the gate and the effect of a pin)."""
    assert policy_section().strip()


def test_the_section_names_the_policy_file() -> None:
    """AC-2. expected_behavior_source: AC-2 ("the file `.orqlet/model-policy.yaml`"), ADR-002 (the
    file is the policy's home) and the interface decision R2."""
    assert policy_file_problems(policy_section()) == []


def test_the_exit_status_table_has_only_well_formed_rows_of_the_two_commands() -> None:
    """AC-2. expected_behavior_source: AC-2 ("with their exit statuses") and the interface decision
    R3 (a table `Command | Exit | Meaning`; the first cell is `orqlet models resolve` or
    `orqlet validate model-policy`, the second one integer, the third a non-empty text)."""
    assert exit_row_problems(policy_section()) == []


def test_the_exit_status_table_gives_every_status_that_the_two_commands_can_end_with() -> None:
    """AC-2. expected_behavior_source: the interface decision R3 (`models resolve` 0, 1, 2 and 3;
    `validate model-policy` 0, 3 and 5; the facts of src/orqlet/interface/cli/exit_codes.py:
    selected or automatic is 0, no qualifying model is 1, wrong options are 2, a refusal is 3, and
    FAIL or NOT_RUN of a validator is 5)."""
    assert exit_status_problems(policy_section()) == []


def test_the_statuses_of_the_table_are_exit_codes_of_the_command_line() -> None:
    """AC-2. expected_behavior_source: src/orqlet/interface/cli/exit_codes.py (`ExitCode`: 0, 1, 2,
    3, 4, 5 and 70 are the values a command may end with) and the interface decision R3. It guards
    the README against a status that no command has."""
    statuses = {status for _, status in exit_pairs(rows_under(policy_section(), EXIT_HEADER))}

    assert sorted(statuses - {code.value for code in ExitCode}) == []


def test_the_five_states_of_a_model_are_five_rows_and_none_implies_another() -> None:
    """AC-2. expected_behavior_source: AC-2 ("the five separate states of a model"), ADR-002
    decision 4 ("The five states are separate fields. Documented, approved, account access,
    callable-verified and evaluated: none implies another") and the interface decision R4 (a table
    `State | Field | Meaning` whose first cells are exactly the five)."""
    assert state_problems(policy_section()) == []


def test_the_three_modes_are_three_rows_and_the_default_is_automatic() -> None:
    """AC-2. expected_behavior_source: AC-2 ("the three modes and the default `automatic`"),
    ADR-001 decision 2 ("The default mode is `automatic`") and the interface decision R5 (a table
    `Mode | What it does` whose first cells are exactly the three modes)."""
    assert mode_problems(policy_section()) == []


def test_the_precedence_is_a_numbered_list_of_four_in_the_order_of_adr_001() -> None:
    """AC-2. expected_behavior_source: AC-2 ("the precedence order"), ADR-001 decision 4
    ("Precedence, highest first": an explicit override, a team assignment for the role or skill, a
    team assignment for the profile, the automatic selection) and the interface decision R6 (four
    consecutive items numbered 1. to 4., the k-th item holds the k-th phrase)."""
    assert precedence_problems(policy_section()) == []


def test_the_section_says_that_only_manual_pins_and_what_pins_the_main_agent() -> None:
    """AC-2. expected_behavior_source: AC-2 ("only `manual` pins and only an explicit Claude Code
    skill assignment pins the main agent"), ADR-003 decisions 2, 4 and 5 ("Only the mode `manual`
    renders a pin"; "Otherwise the main agent is never pinned"), BC-8 and the interface decision
    R7."""
    assert pin_problems(policy_section()) == []


def test_one_paragraph_says_that_fable_is_excluded_by_model_identity() -> None:
    """AC-2. expected_behavior_source: AC-2 ("the Fable exclusion by model identity"), ADR-005
    decision 1 (`excluded[]` entries match by alias name, by model-ID pattern and by family tag) and
    the interface decision R8 (one paragraph holds `Fable`, `by model identity`, `alias`,
    `id pattern` and `family tag`)."""
    assert fable_problems(policy_section()) == []


def test_the_section_says_what_the_gate_is_and_what_stands_in_when_it_cannot_run() -> None:
    """AC-2. expected_behavior_source: AC-2 ("the code review gate as required at every phase with
    independence I2, NOT_RUN when no reviewer qualifies, and a human code-owner review as the
    fallback"), ADR-006 decisions 3, 4 and 5 (every phase; I2 at every class; NOT_RUN and a human
    code-owner review; "A new session of the same client is I1 and does not satisfy the gate";
    "Orqlet has no record path for" a human review) and the interface decision R9. The sentence
    about a new session is qualified by criterion A (edit R-2, approved by the person in
    conversation): it "does not satisfy the gate unless both sides were observed to run different
    model families", for which `derive_independence` in src/orqlet/domain/independence.py gives I2
    (`different_family`). The matching squashes white space, so a line wrap in the README does not
    matter."""
    assert gate_problems(policy_section()) == []


def test_the_section_does_not_say_that_the_host_enforces_the_gate() -> None:
    """AC-2. expected_behavior_source: Q-34 (main has no branch protection; "The human code-owner
    review that stands in for an AI reviewer (I3) is therefore enforced by nothing") and the
    interface decision R9 (the README must not claim `enforced by the host`, `branch protection
    blocks` or `branch protection requires`). It fails while the section does not exist, because
    the reader of the section fails; it guards the new text."""
    assert gate_claim_problems(policy_section()) == []


def test_the_section_states_the_two_awkward_points_of_what_is_built() -> None:
    """AC-2. expected_behavior_source: the interface decision R10 (open
    observations 2 and 3 of PR #21); src/orqlet/domain/independence.py `independence_notes`
    (nothing when the clients are equal; ORQ-W460 when the clients differ and at least one side
    has no observed identity; ORQ-W461 when both sides are known and ran the same observed model;
    nothing when the clients differ and the two known models differ);
    src/orqlet/application/usecases/review_identity.py `_note_findings` (it calls
    `independence_notes` without looking at the class, so a record of class I0 gets the notes
    too) and `approved = approved_at_base or ...` (a binding that the staged tree removes stays
    approved). The section must not say that a note is printed "for every record"."""
    assert awkward_point_problems(policy_section()) == []


def test_the_section_says_that_models_resolve_never_prints_the_source_explicit_fallback() -> None:
    """AC-2. expected_behavior_source: the interface decision R12;
    src/orqlet/domain/model_resolution.py (the source `explicit-fallback` is set only when
    `ResolveRequest.fallback` is given); src/orqlet/application/usecases/models_resolve.py
    (`ModelsQuery` has no fallback field and its `ResolveRequest` sets none) and
    src/orqlet/application/usecases/model_selection.py (its three `ResolveRequest` calls set
    none). The section may not say that an agent may name a fallback, nor list `explicit-fallback`
    as a source that the command prints."""
    assert fallback_source_problems(policy_section()) == []


def test_the_paragraph_of_what_is_built_says_that_no_tool_verifies_the_recorded_values() -> None:
    """AC-2. expected_behavior_source: the interface decision R13 and the
    module docstring of src/orqlet/domain/independence.py ("recorded identifiers, which an
    approver attests and no tool verifies ... A class says how independent a review *claims* to
    be"). The sentences must stand in the paragraph that starts `What is built is the judgement,
    not the reviewer.`"""
    assert judgement_problems(policy_section()) == []


def test_the_section_says_that_the_binding_of_the_code_reviewer_is_built() -> None:
    """AC-2. expected_behavior_source: the interface decision R15;
    src/orqlet/application/usecases/render_all.py (`REVIEW_AGENTS` holds `code-reviewer`, and the
    composition writes its binding with `independence_capability` I2),
    tests/unit/application/test_lifecycle.py lines 164-197 (`init` seeds the third binding) and
    src/orqlet/application/usecases/upgrade.py `_proposes_code_reviewer` and `_pin_notes` (`upgrade`
    proposes the binding to a project whose bindings lack it and prints ORQ-I540: "A
    `code-reviewer` record is ORQ-E415 until a reviewed edit applies it. Orqlet never applies the
    proposal."). The section may not say "once the package ships the role"; that the role is not
    built stays pinned by R11."""
    assert binding_built_problems(policy_section()) == []


def test_the_section_says_what_is_not_built_yet() -> None:
    """AC-2. expected_behavior_source: the interface decision R11, ADR-006 decision 1 (the role
    `orqlet-code-reviewer` is a new role of the protected workflow, shipped by plan phase P-13) and
    plan P-13 (workflow version 0.5.0; the phase `review_evidence` that gains `code-reviewer`)."""
    assert not_built_problems(policy_section()) == []


def test_a_section_that_follows_the_interface_decision_obeys_every_rule() -> None:
    """AC-2. expected_behavior_source: the interface decision R2 to R11, R12, R13
    and R15 (keys `R12new-...`, `R13new-...` and `R15new-...`: the same numbers name other rules
    below). The reference text is written in the
    words that the decision fixes, so the rules can be met together. It passes before the
    documents change."""
    found = {name: rule(REFERENCE_SECTION) for name, rule in SECTION_RULES.items()}

    assert {name: problems for name, problems in found.items() if problems} == {}


def test_every_rule_of_the_section_has_a_way_to_break_it() -> None:
    """AC-2. expected_behavior_source: the interface decision R2 to R13 and R15. It keeps the rules
    and their broken copies in step and passes before the documents change."""
    assert set(SECTION_RULES) == set(BREAKS)


@pytest.mark.parametrize("name", list(SECTION_RULES))
def test_a_rule_of_the_section_fails_on_a_text_that_breaks_it(name: str) -> None:
    """AC-2. expected_behavior_source: the interface decision R2 to R13 and R15 (each rule fails on
    the reference text with one change). It passes before the documents change."""
    old, new = BREAKS[name]
    assert old in REFERENCE_SECTION

    assert SECTION_RULES[name](REFERENCE_SECTION.replace(old, new)) != []


@pytest.mark.parametrize(
    ("name", "old", "new", "expected"),
    MORE_BREAKS,
    ids=[f"{name}-{index}" for index, (name, *_) in enumerate(MORE_BREAKS)],
)
def test_a_rule_gives_its_own_problem_on_each_further_way_to_break_it(
    name: str, old: str, new: str, expected: str
) -> None:
    """AC-2. expected_behavior_source: the interface decision R10, R12, R13 and R15: each phrase
    that the rule pins is needed, and each phrase that it forbids is found. It passes before the
    documents change."""
    assert REFERENCE_SECTION.count(old) == 1

    problems = SECTION_RULES[name](REFERENCE_SECTION.replace(old, new))

    assert any(problem.startswith(expected) for problem in problems), problems


def test_the_old_overclaim_that_a_note_is_printed_for_every_record_fails_the_rule() -> None:
    """AC-2. expected_behavior_source: the interface decision R10 and
    src/orqlet/domain/independence.py `independence_notes` (a record whose client differs, whose
    identities are known and whose models differ gets no note, so "every record" is untrue). The
    old sentence put back into the reference text fails the rule, also next to the new one. It
    passes before the documents change."""
    assert NOTES_SENTENCE in REFERENCE_SECTION
    assert awkward_point_problems(REFERENCE_SECTION) == []

    replaced = REFERENCE_SECTION.replace(NOTES_SENTENCE, OLD_NOTES_SENTENCE)
    added = f"{REFERENCE_SECTION}\n{OLD_NOTES_SENTENCE}\n"

    assert "says: printed for every record" in awkward_point_problems(replaced)
    assert len(awkward_point_problems(replaced)) == 4
    assert awkward_point_problems(added) == ["says: printed for every record"]


def test_no_sentence_calls_the_code_review_optional_or_a_provided_capability() -> None:
    """AC-2. expected_behavior_source: AC-2 ("It no longer says that the code reviewer is
    optional"), BC-26 ("the README and the proposal no longer say the code reviewer is optional")
    and the interface decision R12 (no sentence holds both `code review` and `optional`, and none
    both `code reviewer` and `provided capability`). The old README has no such sentence, so this
    test also passes before the documents change; it guards the new text."""
    text = readme_text()

    assert units_with_all(text, ("code review", "optional")) == []
    assert units_with_all(text, ("code reviewer", "provided capability")) == []


def status_parts() -> tuple[list[str], str]:
    """The bullets of what is built and the paragraph that starts `What is not built yet`."""
    status = section_of(readme_text(), STATUS)
    paragraphs = [p for p in paragraphs_of(status) if normalize(p).startswith(NOT_BUILT)]
    if len(paragraphs) != 1:
        pytest.fail(f"the Status must hold one paragraph that starts `{NOT_BUILT}`")
    return bullets_of(status[: status.index(paragraphs[0])]), paragraphs[0]


def test_the_status_list_of_what_is_built_names_the_two_commands() -> None:
    """AC-2. expected_behavior_source: plan P-12 objective ("say what is built"), BC-26 and the
    interface decision R13 (the Status list names `orqlet models resolve` and `orqlet validate
    model-policy`)."""
    built, _ = status_parts()

    assert built, "the Status holds no list of what is built before the paragraph of what is not"
    assert missing(" ".join(built), [RESOLVE, VALIDATE]) == []


def test_the_status_paragraph_of_what_is_not_built_names_the_code_reviewer_role() -> None:
    """AC-2. expected_behavior_source: ADR-006 decision 1 and plan P-13 (the role
    `orqlet-code-reviewer` does not exist until phase P-13) and the interface decision R13 (the
    paragraph that starts `What is not built yet` names `orqlet-code-reviewer`)."""
    _, not_built = status_parts()

    assert missing(not_built, ["`orqlet-code-reviewer`"]) == []


def commands_table_row(first_cell: str) -> list[str]:
    rows = [
        row
        for row in rows_under(section_of(readme_text(), COMMANDS), ("Command", "Purpose"))
        if normalize(row[0]) == first_cell
    ]
    if len(rows) != 1:
        pytest.fail(f"the Commands table must hold one row for {first_cell}; it holds {len(rows)}")
    return rows[0]


def test_the_commands_table_has_one_row_for_models_and_it_names_models_resolve() -> None:
    """AC-2. expected_behavior_source: plan P-12 file list (README.md documents the two commands)
    and the interface decision R14 (exactly one row whose first cell is `models`; its second cell
    names `models resolve`)."""
    row = commands_table_row("`models`")

    assert missing(row[1], ["`models resolve`"]) == []


def test_the_commands_table_has_one_row_for_validate_and_it_names_validate_model_policy() -> None:
    """AC-2. expected_behavior_source: the interface decision R14 (the `validate` row stays one row
    and its second cell also names `validate model-policy`)."""
    row = commands_table_row("`validate`")

    assert missing(row[1], ["`validate model-policy`"]) == []


def options_row(first_cell: str, *, only_the_start: bool = False) -> list[str]:
    """The one row of the options table whose first cell is `first_cell` (or starts with it)."""

    def matches(cell: str) -> bool:
        found = normalize(cell)
        return found.startswith(first_cell) if only_the_start else found == first_cell

    table = rows_under(section_of(readme_text(), OPTIONS), ("Command", "Options"))
    rows = [row for row in table if matches(row[0])]
    if len(rows) != 1:
        pytest.fail(f"the options table must hold one row for {first_cell}, not {len(rows)}")
    return rows[0]


def test_the_options_of_models_resolve_name_every_flag_of_the_command() -> None:
    """AC-2. expected_behavior_source: the interface decision R15 (the row `models resolve` of the
    table under `### Options that matter` names `--client`, `--role`, `--skill`, `--profile`,
    `--task`, `--override`, `--different-family-from` and `--coder-profile`), ADR-001 decision 8
    and plan P-13 AC-7 (the flags that the skills use)."""
    row = options_row("`models resolve`")

    assert missing(row[1], OPTION_FLAGS) == []


def test_the_options_of_validate_name_the_kind_model_policy() -> None:
    """AC-2. expected_behavior_source: the interface decision R15 (the row `validate <kind> [file]`
    names the kind `model-policy`)."""
    row = options_row("`validate <kind> [file]`", only_the_start=True)

    assert missing(row[1], ["`model-policy`"]) == []


# --- the README: the sentence about the constraints of every level (AC-2) -----------------------
# The sentence that starts `The constraints hold at every level:` lists what `models resolve`
# checks at every level, and nothing that it does not check. In the file
# src/orqlet/domain/model_resolution.py, `_judge` fails a catalog model on the first of four
# constraints: the model is excluded, it is not approved, its route for the client has no known
# identifier, or the access is blocked. `_judge_id` and `_judge_text` call it at every level: for
# an override, for an assignment that names one model (`_pinned_level`) and for the list of a
# profile. None of the four is profile membership. The override path and `_pinned_level` check
# none, and the only profile check is the floor (`_floor_of`, `_meets_floor`), which counts only
# with `--coder-profile` or, by default, for the role `orqlet-code-reviewer` when
# `--different-family-from` names the coder's model. The test
# `test_another_role_has_no_floor_unless_it_is_asked_for`, in the file
# tests/unit/domain/test_model_resolution.py, shows it. ADR-001 decision 5 says that the
# constraints apply at every level. The next sentence of the README describes the floor, and it
# is the only place that does.

CONSTRAINTS_SUBJECT = "The constraints hold"
CONSTRAINTS_OPENING = f"{CONSTRAINTS_SUBJECT} at every level:"
# One phrase for each of the four constraints of `_judge`: excluded, approval, route, access.
CONSTRAINT_PHRASES = (
    "is not excluded",
    "it is approved",
    "known identifier for the client",
    "access is not blocked",
)
PROFILE_WORD = "profile"
# The sentence is read from the subject `The constraints hold` to the first full stop, and not
# from the whole opening, so that a sentence that says `at some levels` is still read as this
# sentence and judged for it, and does not count as a missing one.
CONSTRAINTS_TO_FULL_STOP = re.compile(re.escape(CONSTRAINTS_SUBJECT) + r"\b.*?\.(?=\s|$)")

CONSTRAINTS_SENTENCE = (
    "The constraints hold at every level: the model is not excluded, it is approved, the route "
    "has a known identifier for the client, and the access is not blocked."
)
# What the README must not say: `models resolve` checks no profile membership at every level.
SENTENCE_CLAIMING_PROFILE_MEMBERSHIP = (
    "The constraints hold at every level: the model is not excluded, it is approved, the route "
    "has a known identifier for the client, the access is not blocked, and the model sits in the "
    "profile that the work needs."
)
# The same sentence as the README writes it, wrapped over three lines.
WRAPPED_CONSTRAINTS_SENTENCE = (
    "The constraints hold at every level: the model is not excluded, it is approved, the route\n"
    "has a known identifier for the client, and the\n"
    "access is not blocked."
)
# The sentence after it describes the floor, holds the word `profile` and is not read by the rule.
FLOOR_SENTENCE = (
    "A reviewer may also not be of a lower profile than the coder: `--coder-profile` sets that "
    "floor for any target, and without it the floor (the profile `engineering`) applies only to "
    "the role `orqlet-code-reviewer` and only when `--different-family-from` names the coder's "
    "model."
)
REFERENCE_CONSTRAINTS_TEXT = f"""\
The order of precedence, highest first:

1. an explicit override;
2. a team assignment for the role or skill;
3. a team assignment for the profile;
4. the automatic selection of the client.

{CONSTRAINTS_SENTENCE} {FLOOR_SENTENCE}
`--different-family-from` (a catalog id), `--coder-profile` and `--task` narrow the answer for
those cases.
"""
WRAPPED_REFERENCE_CONSTRAINTS_TEXT = REFERENCE_CONSTRAINTS_TEXT.replace(
    CONSTRAINTS_SENTENCE, WRAPPED_CONSTRAINTS_SENTENCE
)

# For each way to break the sentence: the text to change in the reference text, the text that
# takes its place and the problems that the rule must give, and no others.
CONSTRAINTS_BREAKS: dict[str, tuple[str, str, list[str]]] = {
    "profile-membership-claimed": (
        CONSTRAINTS_SENTENCE,
        SENTENCE_CLAIMING_PROFILE_MEMBERSHIP,
        ["the word `profile` is in the sentence"],
    ),
    "excluded-missing": (
        "the model is not excluded",
        "the model is listed",
        ["lacks: is not excluded"],
    ),
    "approval-missing": (
        "it is approved",
        "it is reviewed",
        ["lacks: it is approved"],
    ),
    "route-missing": (
        "the route has a known identifier for the client",
        "the route exists",
        ["lacks: known identifier for the client"],
    ),
    "access-missing": (
        "the access is not blocked",
        "the access is granted",
        ["lacks: access is not blocked"],
    ),
    "not-at-every-level": (
        "The constraints hold at every level:",
        "The constraints hold at some levels:",
        ["the sentence does not start with: The constraints hold at every level:"],
    ),
    "sentence-missing": (
        f"{CONSTRAINTS_SENTENCE} ",
        "",
        ["0 sentences start with: The constraints hold"],
    ),
    "sentence-twice": (
        CONSTRAINTS_SENTENCE,
        f"{CONSTRAINTS_SENTENCE}\n\n{CONSTRAINTS_SENTENCE}",
        ["2 sentences start with: The constraints hold"],
    ),
}


def constraints_sentences(text: str) -> list[str]:
    """The sentences that start `The constraints hold`, each up to and including its full stop.

    Each sentence is read from the text with every run of white space squashed to one space, so a
    line wrap or a CRLF line ending never matters. A full stop is a `.` that white space follows,
    or that ends the text.
    """
    return CONSTRAINTS_TO_FULL_STOP.findall(squash(text))


def constraints_sentence_problems(text: str) -> list[str]:
    """What is wrong with the sentence about the constraints of every level, in a README text.

    The text holds the sentence exactly once; it starts with `The constraints hold at every
    level:`; it holds a phrase for each of the four constraints; and it holds no word `profile`.
    """
    sentences = constraints_sentences(text)
    if len(sentences) != 1:
        return [f"{len(sentences)} sentences start with: {CONSTRAINTS_SUBJECT}"]
    sentence = sentences[0]
    problems: list[str] = []
    if not normalize(sentence).startswith(normalize(CONSTRAINTS_OPENING)):
        problems.append(f"the sentence does not start with: {CONSTRAINTS_OPENING}")
    problems += lacks(sentence, CONSTRAINT_PHRASES)
    if present(sentence, [PROFILE_WORD]):
        problems.append("the word `profile` is in the sentence")
    return problems


def test_the_readme_lists_the_four_constraints_of_every_level_and_names_no_profile() -> None:
    """AC-2. expected_behavior_source: src/orqlet/domain/model_resolution.py `_judge` (the first
    constraint that a catalog model fails: excluded, approval, route, access), which `_judge_id`
    and `_judge_text` call at every level; `_pinned_level` and the override path check no profile
    membership, and the only profile check is the floor of `_floor_of` and `_meets_floor`, which
    applies with `--coder-profile` or, by default, to the role `orqlet-code-reviewer` when
    `--different-family-from` names the coder's model; tests/unit/domain/test_model_resolution.py
    (the test `test_another_role_has_no_floor_unless_it_is_asked_for`); ADR-001 decision 5 (the
    constraints apply at every level). The one sentence of README.md that starts `The constraints
    hold at every level:` says that four constraints hold at every level (the model is not
    excluded, it is approved, the route has a known identifier for the client, the access is not
    blocked) and says nothing about a profile; the next sentence is the only place that describes
    the profile floor. It fails while that sentence holds the word `profile`."""
    problems = constraints_sentence_problems(readme_text())

    assert problems == [], (
        f"README.md: the sentence that starts `{CONSTRAINTS_OPENING}` must list the four "
        "constraints that every level checks (the model is not excluded, it is approved, the "
        "route has a known identifier for the client, the access is not blocked) and no profile "
        f"membership, which `_judge` does not check: {problems}"
    )


def test_the_constraints_sentence_is_read_up_to_its_full_stop_across_wraps_and_crlf() -> None:
    """AC-2. expected_behavior_source: README.md, where the sentence that starts `The constraints
    hold at every level:` is wrapped over several lines at about 100 columns and is followed by
    the sentence about the floor (`A reviewer may also not be of a lower profile than the
    coder: ...`), which holds the word `profile` and is the only place that describes the floor
    (`_floor_of` and `_meets_floor` in src/orqlet/domain/model_resolution.py). The reader returns
    the first sentence only, up to its full stop, in one line, and a text with CRLF line endings
    reads the same. It reads no file."""
    assert squash(WRAPPED_CONSTRAINTS_SENTENCE) == CONSTRAINTS_SENTENCE
    assert WRAPPED_REFERENCE_CONSTRAINTS_TEXT != REFERENCE_CONSTRAINTS_TEXT

    for text in (
        REFERENCE_CONSTRAINTS_TEXT,
        WRAPPED_REFERENCE_CONSTRAINTS_TEXT,
        WRAPPED_REFERENCE_CONSTRAINTS_TEXT.replace("\n", "\r\n"),
    ):
        assert constraints_sentences(text) == [CONSTRAINTS_SENTENCE]


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(REFERENCE_CONSTRAINTS_TEXT, id="one-line"),
        pytest.param(WRAPPED_REFERENCE_CONSTRAINTS_TEXT, id="wrapped"),
        pytest.param(WRAPPED_REFERENCE_CONSTRAINTS_TEXT.replace("\n", "\r\n"), id="wrapped-crlf"),
    ],
)
def test_the_correct_constraints_sentence_gives_no_problem(text: str) -> None:
    """AC-2. expected_behavior_source: src/orqlet/domain/model_resolution.py `_judge` (excluded,
    approval, route, access: four constraints and no profile membership) and ADR-001 decision 5
    (the constraints apply at every level). The sentence `The constraints hold at every level:
    the model is not excluded, it is approved, the route has a known identifier for the client,
    and the access is not blocked.`, once, on one line or wrapped over several lines (with CRLF
    line endings too), gives no problem, although the sentence after it holds the word
    `profile`. It reads no file."""
    assert constraints_sentence_problems(text) == []


@pytest.mark.parametrize("name", list(CONSTRAINTS_BREAKS))
def test_the_rule_of_the_constraints_sentence_gives_its_own_problem_on_each_way_to_break_it(
    name: str,
) -> None:
    """AC-2. expected_behavior_source: src/orqlet/domain/model_resolution.py `_judge` (each of the
    four constraints is checked at every level, and profile membership is not: `_pinned_level`
    and the override path check none, and `_floor_of` and `_meets_floor` are the only profile
    check), the test `test_another_role_has_no_floor_unless_it_is_asked_for` of
    tests/unit/domain/test_model_resolution.py and ADR-001 decision 5 (the constraints apply at
    every level). Each change of the correct sentence gives a sentence that the README must not
    hold, and the rule gives the problem of that change and no other: the profile clause put
    back; one of the four constraints missing; `at some levels` for `at every level`; no such
    sentence; the sentence twice. It reads no file."""
    old, new, expected = CONSTRAINTS_BREAKS[name]
    assert REFERENCE_CONSTRAINTS_TEXT.count(old) == 1

    assert constraints_sentence_problems(REFERENCE_CONSTRAINTS_TEXT.replace(old, new)) == expected


def test_every_constraint_phrase_of_the_rule_has_a_way_to_break_it() -> None:
    """AC-2. expected_behavior_source: src/orqlet/domain/model_resolution.py `_judge` (the four
    constraints: excluded, approval, route, access). Each of the four phrases that the rule
    requires has a copy of the sentence that lacks it, so a phrase that the rule requires cannot
    stop being checked. It reads no file."""
    expected = {problem for _, _, problems in CONSTRAINTS_BREAKS.values() for problem in problems}

    assert len(CONSTRAINT_PHRASES) == 4
    assert {f"lacks: {phrase}" for phrase in CONSTRAINT_PHRASES} <= expected


def test_each_way_to_break_the_constraints_sentence_has_its_own_problem() -> None:
    """AC-2. expected_behavior_source: src/orqlet/domain/model_resolution.py `_judge` (the four
    constraints: excluded, approval, route, access; no profile membership) and ADR-001 decision 5
    (the constraints apply at every level). Each copy of the sentence that the README must not
    hold has a problem of its own, so that a failure names what the README must change. It reads
    no file."""
    expected = [tuple(problems) for _, _, problems in CONSTRAINTS_BREAKS.values()]

    assert all(expected)
    assert len(set(expected)) == len(expected)


# --- the README: the upgrade paragraph (AC-3) ----------------------------------------------------


def test_one_paragraph_of_the_upgrade_section_says_what_a_pin_does_to_the_approvals() -> None:
    """AC-3. expected_behavior_source: AC-3, ADR-003 decision 7 and consequences ("A policy edit
    changes protected files and so `protected_set_digest`. An approved design or plan in flight
    then shows ORQ-W390 ... and the person decides"), C-8 and the interface decision R16 (one
    paragraph of the section `## Upgrade a project that already uses Orqlet` holds all four
    sentences)."""
    assert upgrade_problems(section_of(readme_text(), UPGRADE)) == []


def test_the_four_sentences_of_the_upgrade_paragraph_must_stand_in_one_paragraph() -> None:
    """AC-3. expected_behavior_source: the interface decision R16 ("ONE paragraph"; a blank line
    ends a paragraph). It passes before the documents change."""
    split = REFERENCE_UPGRADE.replace(". Approvals", ".\n\nApprovals")
    changed = REFERENCE_UPGRADE.replace("the person decides", "nobody decides")

    assert split != REFERENCE_UPGRADE != changed
    assert upgrade_problems(REFERENCE_UPGRADE.replace("\n", "\r\n")) == []
    assert upgrade_problems(split) != []
    assert upgrade_problems(changed) != []


# --- the README: the table of finding codes (AC-4) -----------------------------------------------


def test_the_source_modules_define_the_27_codes_of_the_plan_and_no_other() -> None:
    """AC-4. expected_behavior_source: AC-4 (ORQ-E540 to ORQ-E548, ORQ-W540 to ORQ-W547, ORQ-I540,
    ORQ-E460, ORQ-E461, ORQ-W460 to ORQ-W465 and ORQ-I460, read from model_policy_source.py,
    model_selection.py, validate_model_policy.py, upgrade.py, pin_staleness.py and
    review_identity.py under src/orqlet/application/usecases/) and the interface decision R17 a.
    It guards the plan against the source and holds before the documents change."""
    found = source_codes()

    assert len(EXPECTED_CODES) == 27
    assert (sorted(EXPECTED_CODES - found), sorted(found - EXPECTED_CODES)) == ([], [])


def test_the_codes_table_lists_the_codes_that_the_source_modules_define_and_no_other() -> None:
    """AC-4. expected_behavior_source: AC-4 ("finds each in the table and no other code of the 54x
    and 46x families in the table"), BC-26, BC-13, BC-37 and the interface decision R17 b."""
    listed = codes_listed(code_rows(readme_text()))
    defined = source_codes()

    assert (sorted(defined - listed), sorted(listed - defined)) == ([], [])


def test_each_code_is_the_whole_first_cell_of_exactly_one_row() -> None:
    """AC-4. expected_behavior_source: AC-4 ("a table of the finding codes ... each with one line of
    meaning") and the interface decision R17 c (no duplicate row, one code per cell)."""
    assert code_row_problems(code_rows(readme_text())) == []


def test_each_code_row_has_a_meaning_and_is_one_physical_line() -> None:
    """AC-4. expected_behavior_source: AC-4 ("each with one line of meaning") and the interface
    decision R17 d (the meaning cell is not empty; the row is one physical line). It fails while
    there are no rows, because the README then holds no code of the two families."""
    rows = code_rows(readme_text())

    assert rows, "the README holds no row for a code of the 54x or 46x families"
    assert code_shape_problems(rows) == []


def test_the_rows_of_the_base_exclusions_and_the_deleted_policy_say_what_the_checks_do() -> None:
    """AC-4. expected_behavior_source: the interface decision R14;
    src/orqlet/application/usecases/validate_model_policy.py `_removed_exclusions` ("The
    comparison is by `id`: an entry that kept its id and lost an alias, a pattern or a tag is not
    found"; "not-used" for a file given by path; a skip when no base is located), `_absent` and
    `_deleted` (ORQ-E547 also when the base tree holds the file), and `POLICY_DELETED` in
    models_resolve.py and model_selection.py (ORQ-E547 when the lock records the file as seeded).
    The two meanings hold no ORQ code."""
    assert code_meaning_problems(readme_text()) == []


def test_the_reference_table_of_codes_obeys_the_rule_of_the_two_rows() -> None:
    """AC-4. expected_behavior_source: the interface decision R14 (the
    reference table is written in the words that it fixes). The row of another code may name a
    code: the rule reads the two rows only. It passes before the documents change."""
    assert code_meaning_problems(REFERENCE_CODE_ROWS) == []
    assert code_meaning_problems(REFERENCE_CODE_ROWS.replace("\n", "\r\n")) == []
    assert "ORQ-E541" in REFERENCE_CODE_ROWS


def test_the_row_of_orq_w460_says_which_identities_count_as_known() -> None:
    """AC-4. expected_behavior_source: the interface decision R10'';
    src/orqlet/application/usecases/review_identity.py `_NOTE_TEXT[IDENTITY_UNKNOWN]` ("the class
    rests on a different client, and at least one side has no observed identity that the policy or
    `model_families` names") and src/orqlet/domain/independence.py `_is_known` ("An observed
    string that matched no catalog model and no family is still unknown"). The meaning holds no
    ORQ code."""
    assert code_meaning_problems(readme_text(), W460_MEANINGS) == []


def test_the_reference_table_of_codes_obeys_the_rule_of_the_row_of_orq_w460() -> None:
    """AC-4. expected_behavior_source: the interface decision R10'' (the reference row is
    written in the words that it fixes). It passes before the documents change."""
    assert code_meaning_problems(REFERENCE_CODE_ROWS, W460_MEANINGS) == []
    assert code_meaning_problems(REFERENCE_CODE_ROWS.replace("\n", "\r\n"), W460_MEANINGS) == []


@pytest.mark.parametrize(
    ("meanings", "old", "new", "expected"),
    ROW_BREAK_CASES,
    ids=[f"break-{index}" for index in range(len(ROW_BREAK_CASES))],
)
def test_the_rule_of_a_code_row_gives_its_own_problem_on_each_way_to_break_it(
    meanings: Meanings, old: str, new: str, expected: str
) -> None:
    """AC-4. expected_behavior_source: the interface decision R14 and
    R10'': each phrase that the rule pins is needed, a row may not be missing and an ORQ
    code may not be named inside the meanings. It passes before the documents change."""
    assert REFERENCE_CODE_ROWS.count(old) == 1

    problems = code_meaning_problems(REFERENCE_CODE_ROWS.replace(old, new), meanings)

    assert any(problem.startswith(expected) for problem in problems), problems


def test_a_row_that_is_not_in_a_table_with_the_header_code_and_meaning_is_not_read() -> None:
    """AC-4. expected_behavior_source: the interface decision R14 and R17 (the rows are read from
    the tables with the header `Code | Meaning`). The rule must not take the meanings from text
    outside such a table. It passes before the documents change."""
    outside = REFERENCE_CODE_ROWS.replace("| Code | Meaning |", "| Id | Text |")

    assert code_meaning_problems(outside) == ["ORQ-E544: no row", "ORQ-E547: no row"]
    assert code_meaning_problems(outside, W460_MEANINGS) == ["ORQ-W460: no row"]


# --- the architecture proposal (AC-5) ------------------------------------------------------------


@pytest.mark.parametrize("name", ["s10_3", "s14_9", "s17_12_5", "q07"])
def test_the_proposal_says_that_the_code_review_gate_is_required_at_every_phase_at_i2(
    name: str,
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("the code review gate is required at every phase at
    independence I2" in sections 10.3, 14.9 and 17.12.5 and in the Q-07 entry), ADR-006 decisions 3
    and 4 and decision 9 ("The proposal's Q-07 text is updated ... to say the code review gate is
    required"), C-9 and the interface decision P1."""
    assert in_any(proposal_blocks(name), GATE_AT_I2), f"{name} lacks: {GATE_AT_I2}"


@pytest.mark.parametrize("name", ["s10_3", "s17_12_5", "q07"])
def test_the_proposal_calls_the_code_review_a_required_gate(name: str) -> None:
    """AC-5. expected_behavior_source: AC-5 ("a test pins ... the presence of `required gate`"),
    ADR-006 decision 9 and the interface decision P2. The old text of section 10.3 ("whether its
    record is a required gate is decision Q-07") and the title of the old Q-07 row hold the phrase
    already, so for those two this test passes before the documents change; P1, P6 and P7 are the
    tests that fail on the old text."""
    assert in_any(proposal_blocks(name), REQUIRED_GATE), f"{name} lacks: {REQUIRED_GATE}"


@pytest.mark.parametrize("name", ["s14_9", "s24_1"])
def test_the_proposal_says_that_per_role_pins_exist_in_the_mode_manual(name: str) -> None:
    """AC-5. expected_behavior_source: AC-5 ("per-role pins exist in the mode `manual`"), ADR-003
    decision 2 ("Only the mode `manual` renders a pin"), C-9 and the interface decision P3."""
    assert in_any(proposal_blocks(name), PER_ROLE_PINS), f"{name} lacks: {PER_ROLE_PINS}"


def test_section_14_9_names_the_v2_policy_and_the_effect_of_a_pin_on_the_protected_digest() -> None:
    """AC-5. expected_behavior_source: AC-5 ("the v2 policy has the spelling of this change"),
    ADR-003 decision 7 (a pin changes the agent file bytes, hence `protected_set_digest`), C-8, C-9
    and the interface decision P4 (`orqlet.model-policy/v2`, `superseded` and the sentence about the
    protected agent files)."""
    assert missing(proposal_section("s14_9"), PROPOSAL_PRESENT_14_9) == []


def test_section_14_9_no_longer_excludes_the_pin_from_the_protected_digest() -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 7 and consequences (a policy edit changes
    protected files and so `protected_set_digest`; `protected_set_digest` "covers every protected
    row without exclusion", A-25) and the interface decision P4 (neither `excluded from the
    `protected_set_digest`` nor `not mistaken for tampering`)."""
    assert present(proposal_section("s14_9"), PROPOSAL_ABSENT_14_9) == []


def test_section_24_1_is_a_valid_model_policy_with_the_spelling_of_this_change() -> None:
    """AC-5. expected_behavior_source: AC-5 ("the v2 policy has the spelling of this change"),
    ADR-002 (the contract `orqlet.model-policy/v2` of src/orqlet/application/contracts/
    model_policy.py) and the interface decision P5 (the first yaml block of section 24.1 is loaded
    with the strict loader and validated as `ModelPolicy`)."""
    assert policy_of(proposal_section("s24_1"), source="section 24.1").policy_version >= 1


def test_the_policy_of_section_24_1_has_the_schema_id_of_the_contract() -> None:
    """AC-5. expected_behavior_source: ADR-002 decision 1 (the schema id `orqlet.model-policy/v2`)
    and the interface decision P5 (`schema_id` is `orqlet.model-policy/v2`)."""
    policy = policy_of(proposal_section("s24_1"), source="section 24.1")

    assert policy.schema_id == POLICY_SCHEMA


def test_the_policy_of_section_24_1_holds_exactly_the_three_profiles() -> None:
    """AC-5. expected_behavior_source: ADR-002 (the profiles are quality, engineering and economy;
    `ProfileId` of the contract) and the interface decision P5 (the profiles are exactly quality,
    engineering and economy)."""
    policy = policy_of(proposal_section("s24_1"), source="section 24.1")

    assert profile_ids(policy) == POLICY_PROFILES


def test_the_policy_of_section_24_1_has_an_assignment_in_the_mode_manual() -> None:
    """AC-5. expected_behavior_source: AC-5 ("per-role pins exist in the mode `manual`"), ADR-003
    decision 2 and the interface decision P5 (at least one assignment has the mode `manual`)."""
    policy = policy_of(proposal_section("s24_1"), source="section 24.1")

    assert "manual" in assignment_modes(policy)


def test_the_policy_of_section_24_1_assigns_a_role_and_a_skill() -> None:
    """AC-5. expected_behavior_source: ADR-001 (an assignment targets a role or a skill; `Target`
    of the contract) and the interface decision P5 (at least one assignment targets a role and at
    least one a skill)."""
    policy = policy_of(proposal_section("s24_1"), source="section 24.1")

    assert {"role", "skill"} <= assignment_kinds(policy)


@pytest.mark.parametrize("name", ["s10_3", "s17_12_5"])
def test_the_gate_sections_no_longer_describe_the_review_as_a_provided_capability(
    name: str,
) -> None:
    """AC-5. expected_behavior_source: BC-26 ("the README and the proposal no longer say the code
    reviewer is optional"), ADR-006 decision 9 and the interface decision P6 (neither `provided
    capability`, `required only by Q-07`, `only where decision Q-07 makes it so` nor `keeps the
    four-role gate set unchanged`)."""
    assert present(proposal_section(name), PROPOSAL_ABSENT_GATE_TEXT) == []


def test_section_10_3_says_that_the_binding_of_the_code_reviewer_is_built() -> None:
    """AC-5. expected_behavior_source: the interface decision R16 and the
    evidence of R15: src/orqlet/application/usecases/render_all.py (the composition writes the
    binding of `code-reviewer`), tests/unit/application/test_lifecycle.py lines 164-197 (`init`
    seeds the third binding) and src/orqlet/application/usecases/upgrade.py
    `_proposes_code_reviewer` and `_pin_notes` (`upgrade` proposes the binding to a project that
    lacks it). The role and its skill step ship with workflow 0.5.0; the binding is built; the
    phrase `its seeded binding` no longer stands in section 10.3."""
    assert proposal_10_3_problems(proposal_section("s10_3")) == []


def test_the_reference_proposal_obeys_the_rule_of_section_10_3() -> None:
    """AC-5. expected_behavior_source: the interface decision R16 (the reference
    text is written in the words that it fixes). Section 10.4 of it holds the old sentence, which
    the rule does not read. It passes before the documents change."""
    assert "its seeded binding" in REFERENCE_PROPOSAL
    assert proposal_10_3_problems(reference_10_3()) == []
    assert proposal_10_3_problems(reference_10_3(REFERENCE_PROPOSAL.replace("\n", "\r\n"))) == []


def test_the_old_sentence_of_section_10_3_put_back_fails_the_rule() -> None:
    """AC-5. expected_behavior_source: the interface decision R16: the old
    sentence ("the role `orqlet-code-reviewer`, its skill step and its seeded binding, which ship
    with workflow 0.5.0") fails the rule, put in the place of the new one and put next to it. It
    passes before the documents change."""
    assert NOT_BUILT_10_3 in REFERENCE_PROPOSAL

    replaced = REFERENCE_PROPOSAL.replace(NOT_BUILT_10_3, OLD_NOT_BUILT_10_3)
    added = REFERENCE_PROPOSAL.replace(NOT_BUILT_10_3, f"{NOT_BUILT_10_3} {OLD_NOT_BUILT_10_3}")

    assert proposal_10_3_problems(reference_10_3(replaced)) == [
        f"lacks: {PROPOSAL_PRESENT_10_3[0]}",
        f"lacks: {PROPOSAL_PRESENT_10_3[1]}",
        "says: its seeded binding",
    ]
    assert proposal_10_3_problems(reference_10_3(added)) == ["says: its seeded binding"]


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        (
            "the role `orqlet-code-reviewer` and its skill step, which ship",
            "the role `orqlet-code-reviewer`, which ships",
            "lacks: the role `orqlet-code-reviewer` and its skill step, which ship",
        ),
        (
            " The binding for the role is built: `init` seeds it in `.orqlet/role-bindings.yaml`"
            " and `upgrade` proposes it to a project that lacks it.",
            " The binding for the role ships with it.",
            "lacks: the binding for the role is built",
        ),
        (
            "### 10.3 Role catalogue (the base set)",
            "### 10.3 Role catalogue (the base set)\n\nIts seeded binding is not built.",
            "says: its seeded binding",
        ),
    ],
    ids=["the-skill-step", "the-binding", "the-seeded-binding"],
)
def test_the_rule_of_section_10_3_gives_its_own_problem_on_each_way_to_break_it(
    old: str, new: str, expected: str
) -> None:
    """AC-5. expected_behavior_source: the interface decision R16: each phrase of
    the rule is needed, and `its seeded binding` is found in any case and any place of section
    10.3. It passes before the documents change."""
    assert REFERENCE_PROPOSAL.count(old) == 1

    problems = proposal_10_3_problems(reference_10_3(REFERENCE_PROPOSAL.replace(old, new)))

    assert any(problem.startswith(expected) for problem in problems), problems


def test_the_q_07_rows_no_longer_hold_the_old_answer() -> None:
    """AC-5. expected_behavior_source: AC-5 ("The Q-07 row no longer holds "provided capability
    only", "Recommended [R]: (1) until the owners decide" or "keeps `required: false`""), ADR-006
    decision 9 and the interface decision P7."""
    offending = [
        (row_number, phrase)
        for row_number, row in enumerate(q07_rows(), start=1)
        for phrase in present(row, Q07_ABSENT)
    ]

    assert offending == []


# --- the text edits (criteria A and B) ------------------------------------------------------------
# One edit is its id, the fragment that must be gone and the fragment that takes its place. Each
# fragment is written on one line; the texts are compared with white space squashed, so the line
# wraps of the README (about 100 columns) and of the coder's new text never matter.

Edit = tuple[str, str, str]

FIVE_SPECIALIST_AGENTS = "five specialist agents"
HEADING_22_0 = "### 22.0 Build status and what v0.5 changes in it"


def edit_ids(edits: Iterable[Edit]) -> list[str]:
    return [edit_id for edit_id, _, _ in edits]


def appends_only(edit: Edit) -> bool:
    """True when the new fragment holds the old one, so that the old one stays in the text."""
    _, old, new = edit
    return squash(old) in squash(new)


def occurrences(text: str, fragment: str) -> int:
    """How often the fragment stands in the text; case and bold markers count, wraps do not."""
    return squash(text).count(squash(fragment))


def new_fragment_problems(text: str, edit: Edit) -> list[str]:
    edit_id, _, new = edit
    found = occurrences(text, new)
    if found == 1:
        return []
    return [f"{edit_id}: the new fragment {squash(new)[:80]!r} stands {found} times, not once"]


def old_fragment_problems(text: str, edit: Edit) -> list[str]:
    edit_id, old, _ = edit
    found = occurrences(text, old)
    if found == 0:
        return []
    return [f"{edit_id}: the old fragment {squash(old)[:80]!r} still stands {found} times"]


README_EDITS: tuple[Edit, ...] = (
    (
        "R-1",
        "A reviewer may also not be of a lower profile than the coder.",
        "A reviewer may also not be of a lower profile than the coder: `--coder-profile` sets "
        "that floor for any target, and without it the floor (the profile `engineering`) applies "
        "only to the role `orqlet-code-reviewer` and only when `--different-family-from` names "
        "the coder's model.",
    ),
    (
        "R-2",
        "does not satisfy the gate: it is I1.",
        "does not satisfy the gate unless both sides were observed to run different model "
        "families; without that it is I1.",
    ),
    (
        "R-3",
        "# export the staged snapshot, diff, plan and records for the reviewers",
        "# export the staged snapshot, diff, plan and the test and knowledge records; earlier "
        "review records stay out",
    ),
)

PROPOSAL_EDITS: tuple[Edit, ...] = (
    (
        "P-1",
        "(six shipped with the protected workflow, one optional)",
        "(five ship with the protected workflow, the Code Reviewer ships with workflow 0.5.0, "
        "and the Knowledge drafter is optional)",
    ),
    (
        "P-2a",
        "and a new session of the same client is I1 and does not satisfy the gate.",
        "and a new session of the same client is I1 and does not satisfy the gate unless both "
        "sides were observed to run different model families.",
    ),
    (
        "P-2b",
        "A new session of the same client is I1 and does not satisfy the gate.",
        "A new session of the same client is I1 and does not satisfy the gate unless both sides "
        "were observed to run different model families, which is I2.",
    ),
    (
        "P-3",
        "(option (1): the Code Reviewer is a provided capability, not a required gate)",
        "(option (1): the Code Reviewer is a provided capability, not a required gate; task "
        "`dynamic-model-profiles` re-decided it: the gate is required at every phase, Section "
        "10.3)",
    ),
    (
        "P-4",
        "a Code Reviewer capability is provided (gate: Q-07)",
        "a Code Reviewer capability is provided (gate: Q-07; required at every phase since task "
        "`dynamic-model-profiles`, §10.3)",
    ),
    (
        "P-5",
        "(Architecture, Security and the provided Code Reviewer)",
        "(Architecture, Security and the Code Reviewer, whose gate is required at every phase, "
        "Section 10.3)",
    ),
    (
        "P-6",
        "and the Code Reviewer runs as a provided capability (a required gate only where "
        "decision Q-07 says so)",
        "and the Code Reviewer runs too: its gate is required at every phase at independence I2 "
        "(Section 10.3; the role ships with workflow 0.5.0)",
    ),
    (
        "P-7",
        "the provided Code Reviewer); **the four required gate roles are the Phase 4 Coder, "
        "Tester, Architecture Reviewer and Security Reviewer** (the Code Reviewer becomes a "
        "fifth only by decision Q-07)",
        "the Code Reviewer); **the five required gate roles are the Phase 4 Coder, Tester, "
        "Architecture Reviewer, Security Reviewer and Code Reviewer** (the Code Reviewer became "
        "the fifth in task `dynamic-model-profiles`, which re-decided Q-07)",
    ),
    (
        "P-8",
        "starts the two required reviewers (Architecture and Security) and the provided Code "
        "Reviewer on the same packet:",
        "starts the required reviewers (Architecture, Security and, from workflow 0.5.0, the "
        "Code Reviewer) on the same packet:",
    ),
    (
        "P-9a",
        "or the Code Reviewer where Q-07 requires it)",
        "or the Code Reviewer, whose gate is required, Section 10.3)",
    ),
    (
        "P-9b",
        "| FM-O05 | The policy is `managed`",
        "| FM-O05 (superseded: Section 14.9.0 says what is built) | The policy is `managed`",
    ),
    (
        "P-10",
        "| FM-O06 | A vendor alias moves",
        "| FM-O06 (Section 14.9.0 says what is built) | A vendor alias moves",
    ),
    (
        "P-11",
        "and the provided code reviewer; the optional knowledge drafter comes with M3)",
        "and the code reviewer, which ships with workflow 0.5.0 and is not built yet; the "
        "optional knowledge drafter comes with M3)",
    ),
    (
        "P-12a",
        "plus a provided Code Reviewer capability (v0.5)**",
        "plus a provided Code Reviewer capability (v0.5; a required gate since task "
        "`dynamic-model-profiles`, Section 10.3)**",
    ),
    (
        "P-12b",
        "a read-only Code Reviewer provided by `/orqlet-review` and required only by decision "
        "Q-07;",
        "a read-only Code Reviewer started by `/orqlet-review`, required only by decision Q-07 "
        "in v0.5 and at every phase since task `dynamic-model-profiles`;",
    ),
    (
        "P-13",
        "it is not a required gate (Q-07, option (1), answered 2026-10-25)",
        "it is not a required gate (Q-07, option (1), answered 2026-10-25; re-decided in task "
        "`dynamic-model-profiles`: a required gate at every phase, Section 10.3)",
    ),
    (
        "P-14",
        "Partially covered: the Code Reviewer is provided; whether it is a required gate is "
        "**Q-07**",
        "Partially covered: the gate is required at every phase (Q-07, re-decided in task "
        "`dynamic-model-profiles`); the role `orqlet-code-reviewer` is not built yet",
    ),
    (
        "P-15",
        "the Code Reviewer gate (7.7: Q-07)",
        "the Code Reviewer role (7.7: not built yet)",
    ),
    (
        "P-16",
        "**Q-07** (the Code Reviewer gate) and **Q-08** (the approved basis)",
        "**Q-08** (the approved basis; Q-07, the Code Reviewer gate, was re-decided in task "
        "`dynamic-model-profiles`)",
    ),
    (
        "P-17",
        "| §14.9 model refresh | A required role",
        "| §14.9 model refresh (superseded in part: Section 14.9.0) | A required role",
    ),
    (
        "P-18",
        "| Model policy and pins | A required role",
        "| Model policy and pins (superseded in part: Section 14.9.0) | A required role",
    ),
    (
        "P-19",
        "excluded models; schema and compatibility mismatches. The example schema is in Section "
        "24.1.",
        "excluded models; schema and compatibility mismatches. The example schema is in Section "
        "24.1. **Superseded in part (Section 14.9.0):** the profile, route and required-role "
        "checks of this paragraph describe the v0.5 policy; Section 14.9.0 says what `orqlet "
        "validate model-policy` checks.",
    ),
    (
        "P-20",
        "model_profile: <strong-reviewer> # a logical tier hint; informational (Section 14)",
        "model_profile: <profile id> # a logical tier hint; informational (Section 14); profile "
        "ids are the team's (Section 24.1)",
    ),
    (
        "P-21",
        "| D-47 | Default (new) |",
        "| D-47 | Default (new; superseded in part: Section 14.9.0) |",
    ),
    (
        "P-22",
        "| D-51 | Default (new, v0.5) |",
        "| D-51 | Default (new, v0.5; superseded in part: Section 14.9.0) |",
    ),
    (
        "P-23",
        "their gates and the four required roles are part of the CLI release",
        "their gates and the required roles (five since task `dynamic-model-profiles`, Section "
        "10.3) are part of the CLI release",
    ),
    (
        "P-24",
        "canonical role contracts (the four required roles and the researchers)",
        "canonical role contracts (the required roles and the researchers)",
    ),
    (
        "P-25",
        'the four phases and their approvals, the four required roles, and "NOT_RUN is never '
        'success"',
        'the four phases and their approvals, the required roles, and "NOT_RUN is never success"',
    ),
    (
        "P-26",
        "**the four Phase 4 roles are always activated**",
        "**the Phase 4 roles (the Coder, the Tester, and the Architecture, Security and Code "
        "Reviewers) are always activated**",
    ),
    (
        "P-27",
        "**All four roles are required in every phase**",
        "**All five roles are required in every phase** (the Code Reviewer from workflow 0.5.0)",
    ),
    (
        "P-28",
        "the four roles' results",
        "the roles' results",
    ),
    (
        "P-29",
        "Status: this rule lands with the v0.5 packet plan. The built `review prepare` (Section "
        "22.0) exports the staged tree and has no assertion until then, and this text changes no "
        "code.",
        "Status: this rule was not built as written. The built `review prepare` (task "
        "`dynamic-model-profiles`, ADR-007 decision 8) leaves the review records of every task "
        "(the pattern `docs/design/*/reviews/*`, a folder below included) and the notes that the "
        "design manifest names at the merge base out of the snapshot, the context copies and the "
        "diff, and lists none of them as omitted; a note never takes out the manifest, the plan "
        "or a standards file. The findings that `review prepare` raises itself are ORQ-E440 to "
        "ORQ-E442, ORQ-I440 and ORQ-I441, and none concerns an invalid review record. This text "
        "changes no code.",
    ),
)


# The edits that replace text. P-19 only appends to its old fragment, so it is pinned by its new
# fragment alone; `test_only_the_edit_p_19_appends_to_its_old_fragment` keeps that list honest.
REPLACING_PROPOSAL_EDITS = tuple(edit for edit in PROPOSAL_EDITS if not appends_only(edit))


# --- the reading of the edits is sound -----------------------------------------------------------


def test_a_fragment_is_found_across_a_line_wrap_and_in_a_text_with_crlf_line_endings() -> None:
    """Criterion A. expected_behavior_source: the criterion (the README is hard-wrapped, so
    both sides are compared with every run of white space, a line break too, as one space). It
    passes before the documents change."""
    text = "one two\r\n  three   four\nfive"

    assert occurrences(text, "two three four five") == 1
    assert occurrences(text, "two  three\nfour") == 1
    assert occurrences(text, "two,three") == 0
    assert occurrences(text.replace("\r\n", "\n"), "one two three") == 1


def test_a_fragment_is_matched_in_the_case_and_with_the_bold_markers_of_the_text() -> None:
    """Criterion A. expected_behavior_source: the criterion (the new fragment stands there
    exactly; only white space is squashed, so `**Q-08**` is not `Q-08` and `The Gate` is not
    `the gate`). It passes before the documents change."""
    assert occurrences("the **Q-08** row", "**Q-08**") == 1
    assert occurrences("the Q-08 row", "**Q-08**") == 0
    assert occurrences("The Gate", "the gate") == 0


def test_a_new_fragment_that_is_missing_or_repeated_is_a_problem() -> None:
    """Criterion A. expected_behavior_source: the criterion (the file holds the new
    fragment exactly once). It passes before the documents change."""
    edit = ("X-1", "old words", "new words")

    assert new_fragment_problems("a new\r\nwords b", edit) == []
    assert len(new_fragment_problems("a old words b", edit)) == 1
    assert len(new_fragment_problems("new words, new\nwords", edit)) == 1


def test_an_old_fragment_that_is_still_there_is_a_problem_in_any_wrap() -> None:
    """Criterion A. expected_behavior_source: the criterion (the file does not contain the
    old fragment). It passes before the documents change."""
    edit = ("X-1", "old words", "new words")

    assert old_fragment_problems("a new words b", edit) == []
    assert len(old_fragment_problems("an old words", edit)) == 1
    assert len(old_fragment_problems("an old\r\n  words", edit)) == 1


def test_an_edit_that_only_appends_keeps_its_old_fragment_and_so_has_no_absence_check() -> None:
    """Criterion A. expected_behavior_source: the criterion (an entry whose new fragment
    holds the old one, P-19, gets only the positive check). It passes before the documents
    change."""
    assert appends_only(("X-1", "a b.", "a b. And more."))
    assert appends_only(("X-1", "a b.", "a\nb. And more."))
    assert not appends_only(("X-1", "a b.", "a c."))


def test_the_ids_of_the_edits_are_unique_and_every_edit_changes_its_text() -> None:
    """Criterion A. expected_behavior_source: the criterion (the table of edits: one id,
    one old and one new fragment each). It passes before the documents change."""
    edits = (*README_EDITS, *PROPOSAL_EDITS)
    ids = edit_ids(edits)

    assert len(ids) == len(set(ids))
    assert [edit_id for edit_id, old, new in edits if not squash(old) or not squash(new)] == []
    assert [edit_id for edit_id, old, new in edits if squash(old) == squash(new)] == []


def test_only_the_edit_p_19_appends_to_its_old_fragment() -> None:
    """Criterion A. expected_behavior_source: the criterion (P-19 only appends; every other
    entry also has its old fragment pinned as gone). It passes before the documents change."""
    edits = (*README_EDITS, *PROPOSAL_EDITS)

    assert [edit[0] for edit in edits if appends_only(edit)] == ["P-19"]


# --- the README and the proposal: the edits (criterion A) -----------------------------------------


@pytest.mark.parametrize("edit", README_EDITS, ids=edit_ids(README_EDITS))
def test_the_readme_holds_the_new_fragment_of_an_edit_exactly_once(edit: Edit) -> None:
    """Criterion A. expected_behavior_source: the edit table (the person
    approved it in conversation; it is not in plan.yaml). It fails until the README is edited."""
    assert new_fragment_problems(readme_text(), edit) == []


@pytest.mark.parametrize("edit", README_EDITS, ids=edit_ids(README_EDITS))
def test_the_readme_no_longer_holds_the_old_fragment_of_an_edit(edit: Edit) -> None:
    """Criterion A. expected_behavior_source: the edit table (as above; each
    old fragment stood once in the README before the edits). It fails until the README is
    edited."""
    assert old_fragment_problems(readme_text(), edit) == []


@pytest.mark.parametrize("edit", PROPOSAL_EDITS, ids=edit_ids(PROPOSAL_EDITS))
def test_the_proposal_holds_the_new_fragment_of_an_edit_exactly_once(edit: Edit) -> None:
    """Criterion A. expected_behavior_source: the edit table (the person
    approved it in conversation; it is not in plan.yaml). It fails until the proposal is edited."""
    assert new_fragment_problems(proposal_text(), edit) == []


@pytest.mark.parametrize("edit", REPLACING_PROPOSAL_EDITS, ids=edit_ids(REPLACING_PROPOSAL_EDITS))
def test_the_proposal_no_longer_holds_the_old_fragment_of_an_edit(edit: Edit) -> None:
    """Criterion A. expected_behavior_source: the edit table (as above; each
    old fragment stood once in the proposal before the edits; P-19 only appends and has no such
    check). It fails until the proposal is edited."""
    assert old_fragment_problems(proposal_text(), edit) == []


# --- the guards: what the edits leave as they are (criterion B) -----------------------------------


def test_the_readme_still_says_that_five_specialist_agents_ship() -> None:
    """Criterion B. expected_behavior_source: the criterion (the README line about `five
    specialist agents` is not changed by the edits; it is still true) and README.md, the table
    row `Agents that follow a process`. It passes before the documents change and must pass after
    them."""
    assert occurrences(readme_text(), FIVE_SPECIALIST_AGENTS) > 0


def test_the_proposal_still_has_the_heading_of_section_22_0() -> None:
    """Criterion B. expected_behavior_source: the criterion (the heading `### 22.0 Build
    status and what v0.5 changes in it` is dated history and is not changed by the edits). It
    passes before the documents change and must pass after them."""
    assert section_of(proposal_text(), HEADING_22_0, whole_line=False).strip()
