"""The text of the three format references that phase outputs follow (task phase-skill-contracts,
phase P-4).

Every test cites its `expected_behavior_source`: BC-n are the behaviour criteria of
docs/design/phase-skill-contracts/design/component.md, ADR-002 and ADR-004 are the files
`adr-00n-*.md` in the same folder, Q-n are the questions of
docs/design/phase-skill-contracts/questions.yaml and "P-4 AC-n" is an acceptance criterion of
phase P-4 in docs/design/phase-skill-contracts/plan.yaml. The skill bodies are pinned in
tests/unit/test_workflow_skill_contracts.py, whose helpers this module shares. Pinned elsewhere
and not repeated here: the YAML example of each of the four format references passes its contract
and four examples are found, and every backticked `orqlet ...` in a reference names an existing
command and flags (tests/unit/render/test_skills.py; BC-5); review-format.md, the goldens and the
manifest (the golden tests and tests/unit/test_workflow_lookup_text.py); the section "Evidence
from the web" of as-is-format.md (tests/unit/test_workflow_lookup_text.py).

HOW THESE TESTS WERE WRITTEN. The Tester of P-4 wrote them before the Coder changed the three
references, from the criteria of P-4, BC-20, BC-21 and BC-22, ADR-004 decisions 1, 2 and 3,
ADR-002 decisions 3 and 6, Q-12 and the interface that the Coder gave for P-4: the headings
`## The research brief`, `## The design brief`, `## The test plan` and `## The implementation
checklist` and their places, the opening words of the six sections of the research brief and of
the nine parts of the design brief, the inference example line, the key phrases pinned below, and
the shape of the plan example (key order, criterion sources, one completion entry per check, the
warning mark). Each test is expected to fail until its text exists. Those that today's references
already meet pass at once: every criterion source of the plan example is an id (its only source is
`Q-1`), and Q-12. Before any implementation existed, the Coder answered the Tester's four
questions: Q-12 belongs under AC-6; the warning mark sits in the marked check's own completion
entry and in a self-check entry that names that check; the key-order pin and the fact-id pattern
hold for the examples only. The warning-mark test was tightened to that answer.

Choices:
- The text is the packaged file as `PackagedWorkflow().read_text` returns it. A section runs from
  its `## ` heading to the next `## ` line (the shared `section`, which fails on a missing or
  repeated heading). An item is a numbered line with its indented continuation lines (the shared
  `numbered_items`), compared without its number. A phrase is looked for with every run of white
  space as one space; its letter case is pinned.
- The YAML example is the first ```yaml block, parsed with the strict loader. The key order of a
  phase is the order of its mapping as written, which the loader keeps. Every phase of the plan
  example holds `acceptance_criteria`, `checks` and `file_operations`; that pin is on the example
  only, not on real plans, where the contract lets `file_operations` be empty.
- The inference example is the first line inside a fenced block of `## The research brief` that
  starts with "- I-1 ", without its indentation, so the block may sit inside a numbered item. Its
  fact ids `A-n` in parentheses pin the example line only; a real brief is not constrained by that
  pattern.
- A check's own completion entry is the one that starts with the check's id, a colon and a space.
  Its command is a backticked span, and a placeholder is a name between `<` and `>` in that span.
  A self-check `how` names a check when the id stands in it with no letter, digit, `_` or `-`
  touching it, so `unit` does not name `unit-tests`.
- Q-12 is pinned for the three references that P-4 changes.

Deliberately NOT pinned (the design leaves it open, or a phrase would only copy a file):
- the wording around the pinned phrases, and an item's text after its opening words;
- where `## The research brief` stands relative to the YAML example, and the other sections of
  the three references;
- the order of `acceptance_criteria` and `checks` between themselves, and of a phase's other keys;
- the number of phases, criteria and checks of the plan example, which check is on the warning
  list, the text of its self-check entry beyond "warning list" and the check id, and the cited
  values of a completion entry beyond the word "sha256";
- AC-4 (BC-23), a review item, and AC-7, the gate-status-phase check.
"""

from __future__ import annotations

import re
from functools import cache

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.domain.prescriptive import prescriptive_hits
from tests.unit.test_workflow_phase_contract_text import FENCE
from tests.unit.test_workflow_skill_contracts import (
    NUMBERED,
    TECHNOLOGY_WORDS,
    names_word,
    numbered_items,
    section,
    squash,
)

pytestmark = pytest.mark.unit

AS_IS_FORMAT = "skills/orqlet-research/references/as-is-format.md"
DESIGN_FORMAT = "skills/orqlet-design/references/design-format.md"
PLAN_FORMAT = "skills/orqlet-plan/references/plan-format.md"
YAML_EXAMPLE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


@cache
def reference(path: str) -> str:
    return PackagedWorkflow().read_text(path)


def heading_line(path: str, heading: str) -> int:
    """The line number of a heading that appears exactly once."""
    lines = reference(path).split("\n")
    assert lines.count(heading) == 1, f"the heading {heading!r} must appear exactly once"
    return lines.index(heading)


def example_line(path: str) -> int:
    lines = reference(path).split("\n")
    found = [n for n, line in enumerate(lines) if line.startswith("```yaml")]
    assert found, f"{path} holds no ```yaml block"
    return found[0]


def before_line(path: str, end: int) -> str:
    return squash("\n".join(reference(path).split("\n")[:end]))


def items(path: str, heading: str) -> list[str]:
    """The numbered items under a heading, squashed, each without its number."""
    text = section(reference(path), heading)
    return [NUMBERED.sub("", item, count=1) for item in numbered_items(text)]


def item_starting(path: str, heading: str, start: str) -> str:
    found = [item for item in items(path, heading) if item.startswith(start)]
    assert len(found) == 1, f"exactly one item under {heading!r} must begin with {start!r}"
    return found[0]


def fenced_lines(text: str) -> list[str]:
    """The lines inside fenced blocks, without their indentation."""
    found: list[str] = []
    fenced = False
    for line in text.split("\n"):
        if FENCE.match(line):
            fenced = not fenced
        elif fenced:
            found.append(line.strip())
    return found


@cache
def example(path: str) -> dict[str, object]:
    match = YAML_EXAMPLE.search(reference(path))
    assert match is not None, f"{path} holds no ```yaml block"
    loaded = StrictYamlLoader().load(match.group(1).encode(), source=path)
    assert isinstance(loaded, dict)
    return loaded


def mappings(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    assert all(isinstance(entry, dict) for entry in value)
    return value


def texts(value: object) -> list[str]:
    assert isinstance(value, list)
    assert all(isinstance(entry, str) for entry in value)
    return [squash(entry) for entry in value]


def plan_phases() -> list[dict[str, object]]:
    phases = mappings(example(PLAN_FORMAT)["phases"])
    assert phases, "the plan example holds no phase"
    return phases


def criterion_sources() -> list[str]:
    criteria = [c for phase in plan_phases() for c in mappings(phase["acceptance_criteria"])]
    assert criteria, "the plan example holds no acceptance criterion"
    return [str(criterion["source"]) for criterion in criteria]


def own_entries() -> list[tuple[str, str]]:
    """(check id, its own completion entry) for every check of every phase of the plan example."""
    found: list[tuple[str, str]] = []
    for phase in plan_phases():
        completion = texts(phase["completion"])
        checks = texts(phase["checks"])
        assert checks, phase["id"]
        for check in checks:
            entries = [entry for entry in completion if entry.startswith(f"{check}: ")]
            assert len(entries) == 1, (phase["id"], check, completion)
            found.append((check, entries[0]))
    return found


def warning_list_hows() -> list[str]:
    """The `how` of every self-check entry of the plan example whose `what` names the list."""
    self_check = example(PLAN_FORMAT)["self_check"]
    assert isinstance(self_check, dict)
    entries = mappings(self_check["checks"])
    return [
        squash(str(entry.get("how", "")))
        for entry in entries
        if "warning list" in squash(str(entry.get("what", "")))
    ]


def names_id(text: str, ident: str) -> bool:
    """`ident` stands in `text` as a whole id: no letter, digit, `_` or `-` touches it."""
    return re.search(rf"(?<![\w-]){re.escape(ident)}(?![\w-])", text) is not None


# --- BC-20: the research brief (as-is-format.md) -------------------------------------------------
RESEARCH_BRIEF = "## The research brief"
RESEARCH_SECTIONS = (
    "Request:",
    "Scope:",
    "Existing capabilities and behaviour:",
    "Inferences:",
    "Open questions:",
    "Inputs for design:",
)
INFERENCE_PHRASES = (
    "Each statement names the fact ids it rests on",
    "An inference has its own id `I-n`, names the facts it rests on and says what would confirm it",
)
NO_ADVICE_PHRASES = (
    "The brief recommends nothing",
    "ORQ-W338",
    "the design's `as_is_ref` covers it by hash",
)
FACT_IDS = re.compile(r"\(A-\d+(?:, A-\d+)*\)")


def research_brief() -> str:
    return squash(section(reference(AS_IS_FORMAT), RESEARCH_BRIEF))


def inference_example() -> str:
    lines = fenced_lines(section(reference(AS_IS_FORMAT), RESEARCH_BRIEF))
    found = [line for line in lines if line.startswith("- I-1 ")]
    assert found, f"no fenced line under {RESEARCH_BRIEF!r} starts with '- I-1 '"
    return found[0]


def test_bc20_the_research_brief_has_its_heading_before_the_evidence_from_the_web() -> None:
    """P-4 AC-1. expected_behavior_source: BC-20 (`as-is-format.md` defines the research brief)
    and ADR-004 decision 1 ("The text after the front matter of `as-is.md` is the brief"); the
    interface of P-4 gives the heading `## The research brief`, once, before `## Evidence from the
    web`."""
    brief = heading_line(AS_IS_FORMAT, RESEARCH_BRIEF)

    assert brief < heading_line(AS_IS_FORMAT, "## Evidence from the web")


def test_bc20_the_opening_says_the_text_after_the_front_matter_is_the_research_brief() -> None:
    """P-4 AC-1. expected_behavior_source: ADR-004 decision 1 ("The text after the front matter of
    `as-is.md` is the brief") and BC-20; the interface of P-4 puts the sentence before the YAML
    example."""
    opening = before_line(AS_IS_FORMAT, example_line(AS_IS_FORMAT))

    assert "The text after the front matter is the research brief." in opening


def test_bc20_the_reference_no_longer_asks_for_an_empty_text() -> None:
    """P-4 AC-1. expected_behavior_source: ADR-004 Context (the format reference "asks for it to be
    empty or a restatement", as-is-format.md:3) and decision 1 (that text is now the brief); the
    interface of P-4 removes "keep it empty"."""
    assert "keep it empty" not in squash(reference(AS_IS_FORMAT))


def test_bc20_the_research_brief_has_the_six_sections_of_adr_004_in_order() -> None:
    """P-4 AC-1. expected_behavior_source: ADR-004 decision 1 ("with the sections Request, Scope,
    Existing capabilities and behaviour, Inferences, Open questions and Inputs for design") and
    BC-20 ("the sections of ADR-004 decision 1"); the interface of P-4 makes each a numbered item
    that begins with its name and a colon."""
    found = items(AS_IS_FORMAT, RESEARCH_BRIEF)

    assert len(found) == len(RESEARCH_SECTIONS), found
    pairs = zip(found, RESEARCH_SECTIONS, strict=True)
    assert [start for item, start in pairs if not item.startswith(start)] == []


@pytest.mark.parametrize("phrase", INFERENCE_PHRASES)
def test_bc20_the_research_brief_ties_statements_and_inferences_to_fact_ids(phrase: str) -> None:
    """P-4 AC-1. expected_behavior_source: ADR-004 decision 1 ("Each statement names the fact ids
    it rests on. An inference has its own id `I-n`, names its facts and says what would confirm
    it.") and BC-20 ("inferences `I-n` that name their fact ids")."""
    assert phrase in research_brief()


def test_bc20_the_inference_example_names_its_facts_and_what_would_confirm_it() -> None:
    """P-4 AC-1. expected_behavior_source: ADR-004 decision 1 (an inference "has its own id `I-n`,
    names its facts and says what would confirm it") and BC-20; the fact ids are `A-n`
    (src/orqlet/application/contracts/as_is.py:39). The interface of P-4 gives the example line:
    "- I-1 ", the fact ids in parentheses and "would confirm it"."""
    line = inference_example()

    assert FACT_IDS.search(line) is not None, line
    assert "would confirm it" in line


def test_bc20_the_inference_example_does_not_read_as_advice() -> None:
    """P-4 AC-1. expected_behavior_source: ADR-004 decision 1 ("The brief recommends nothing,
    which the advice lint backs up") and BC-20 ("no recommendation"); the advice lint is
    `prescriptive_hits` (src/orqlet/domain/prescriptive.py), which `orqlet validate as-is` runs on
    the text after the front matter (ORQ-W338, src/orqlet/application/usecases/validate_as_is.py
    lines 174-181)."""
    assert prescriptive_hits(inference_example()) == ()


@pytest.mark.parametrize("phrase", NO_ADVICE_PHRASES)
def test_bc20_the_research_brief_recommends_nothing_and_is_covered_by_hash(phrase: str) -> None:
    """P-4 AC-1. expected_behavior_source: ADR-004 decision 1 ("The brief recommends nothing, which
    the advice lint backs up"; "The brief is inside `as-is.md`, so `as_is_ref` covers it by hash")
    and BC-20 ("no recommendation"); ORQ-W338 is the warning of that lint on the text after the
    front matter (src/orqlet/application/usecases/validate_as_is.py lines 174-181)."""
    assert phrase in research_brief()


# --- BC-21: the design brief (design-format.md) --------------------------------------------------
DESIGN_BRIEF = "## The design brief"
DESIGN_PARTS = (
    "The summary, with the recommended approach",
    "The requirements `R-n`",
    "The behaviour",
    "The responsibilities and interfaces",
    "The failures",
    "The acceptance criteria `BC-n`",
    "The decisions",
    "The unresolved decisions",
    "The constraints that the plan must respect",
)
BEHAVIOUR_KINDS = (
    "command line (arguments, output, exit status)",
    "library API (calls, results, errors)",
    "network API (requests, responses)",
    "messages and events",
    "files and data written",
    "scheduled jobs",
    "logs and metrics",
    "a user interface when there is one",
    "A project without a graphical interface states its behaviour at the other kinds.",
)
CRITERION_SOURCE_KINDS = (
    "`R-n`",
    "`Q-n`",
    "`A-n`",
    "`U-n`",
    "`C-n`",
    "an ADR decision",
    "a standard's id",
)
DESIGN_RULES = (
    "Each ADR compares the real alternatives, and its Consequences name the trade-offs of the "
    "choice.",
    "A consequential decision that the design cannot make is a ledger question that blocks design",
    "ORQ-E367",
    "A design contains no phase order: no phase list, build order or task list.",
    "An ordering that must hold is a constraint with its reason, and the plan sequences it.",
)


def design_part(start: str) -> str:
    return item_starting(DESIGN_FORMAT, DESIGN_BRIEF, start)


def test_bc21_the_design_brief_has_its_heading_before_the_manifest() -> None:
    """P-4 AC-2. expected_behavior_source: BC-21 (`design-format.md` defines the design brief at
    the top of `component.md`) and ADR-004 decision 2; the interface of P-4 gives the heading
    `## The design brief`, once, before `## The manifest`."""
    brief = heading_line(DESIGN_FORMAT, DESIGN_BRIEF)

    assert brief < heading_line(DESIGN_FORMAT, "## The manifest")


def test_bc21_component_md_opens_with_the_design_brief() -> None:
    """P-4 AC-2. expected_behavior_source: ADR-004 decision 2 ("`component.md` opens with the
    brief") and its rejected alternative ("`component.md` is required at every class and is
    hashed"), and BC-21 ("at the top of `component.md`")."""
    phrase = "`component.md`, which every class requires, opens with the design brief."

    assert phrase in squash(section(reference(DESIGN_FORMAT), DESIGN_BRIEF))


def test_bc21_the_design_brief_has_the_nine_parts_of_adr_004_in_order() -> None:
    """P-4 AC-2. expected_behavior_source: ADR-004 decision 2 (in this order: the summary with the
    recommended approach, the requirements `R-n`, the behaviour, the responsibilities and
    interfaces, the failures, the acceptance criteria `BC-n`, the decisions, the unresolved
    decisions, the constraints that the plan must respect) and BC-21 ("with the parts of ADR-004
    decision 2")."""
    found = items(DESIGN_FORMAT, DESIGN_BRIEF)

    assert len(found) == len(DESIGN_PARTS), found
    pairs = zip(found, DESIGN_PARTS, strict=True)
    assert [start for item, start in pairs if not item.startswith(start)] == []


@pytest.mark.parametrize("phrase", BEHAVIOUR_KINDS)
def test_bc21_the_behaviour_is_stated_at_each_kind_of_interface(phrase: str) -> None:
    """P-4 AC-2. expected_behavior_source: ADR-004 decision 2 (the behaviour "stated as observable
    input and result at the project's interfaces: command line (arguments, output, exit status),
    library API (calls, results, errors), network API (requests, responses), messages and events,
    files and data written, scheduled jobs, logs and metrics, and a user interface when there is
    one") and BC-21 ("including behaviour by interface kind for projects without a graphical
    interface"); the interface of P-4 gives the sentence for a project without one."""
    assert phrase in design_part("The behaviour")


def test_bc21_each_failure_has_its_trigger_result_and_recovery() -> None:
    """P-4 AC-2. expected_behavior_source: ADR-004 decision 2 ("the failures, each with its
    trigger, observable result and recovery") and BC-21 ("with the parts of ADR-004 decision
    2")."""
    assert "each with its trigger, observable result and recovery" in design_part("The failures")


@pytest.mark.parametrize("kind", CRITERION_SOURCE_KINDS)
def test_bc21_each_acceptance_criterion_names_a_source_of_these_kinds(kind: str) -> None:
    """P-4 AC-2. expected_behavior_source: ADR-004 decision 2 ("the acceptance criteria `BC-n`,
    each with its source: a requirement `R-n`, a question `Q-n`, an AS-IS entry (`A-n`, `U-n`,
    `C-n`), an ADR decision or a standard's id") and BC-21."""
    assert kind in design_part("The acceptance criteria `BC-n`")


@pytest.mark.parametrize("phrase", DESIGN_RULES)
def test_bc21_the_design_compares_alternatives_blocks_on_open_decisions_and_orders_nothing(
    phrase: str,
) -> None:
    """P-4 AC-2. expected_behavior_source: ADR-004 decision 2 ("Each ADR compares the real
    alternatives, and its Consequences name the trade-offs of the choice. A consequential decision
    that the design cannot make becomes a ledger question that blocks design (ORQ-E367). The
    design orders nothing: no phase list, build order or task list. An ordering that must hold is
    stated as a constraint with its reason, and the plan sequences it.") and BC-21 ("a design
    contains no phase order and ... an unresolved consequential decision is a blocking ledger
    question"); ORQ-E367 is the error of `orqlet validate design` for an open question that blocks
    design (src/orqlet/application/usecases/validate_design.py lines 257-258)."""
    assert phrase in squash(section(reference(DESIGN_FORMAT), DESIGN_BRIEF))


# --- BC-22: the test plan before the implementation checklist (plan-format.md) -------------------
TEST_PLAN = "## The test plan"
CHECKLIST = "## The implementation checklist"
TEST_PLAN_PHRASES = (
    "Each acceptance criterion is a scenario with its expected outcome.",
    "Its source is a `BC-n`, an `R-n` or a `Q-n` for new behaviour, or the AS-IS fact `A-n` for a "
    "regression that must keep working. It is never taken from code, including code written in an "
    "earlier phase.",
    "Each check has a `completion` entry that starts with the check's id.",
    "replaced by a named placeholder",
    "its sources as `orqlet evidence cite` prints them (path, lines, revision and sha256): the "
    "lines that define it, the files the command directly invokes and the configuration lines it "
    "reads.",
    "A command that matches the warning list of `references/phase-contract.md` is marked in its "
    "`completion` entry and in the plan's self-check.",
    "A check whose command the project does not define is a question.",
)
CRITERION_SOURCE = re.compile(r"^(BC|R|Q|A)-\d+$")
REGRESSION_SOURCE = re.compile(r"^A-\d+$")
BACKTICKED = re.compile(r"`([^`]+)`")
PLACEHOLDER = re.compile(r"<[^<>`]+>")


def test_bc22_the_test_plan_comes_before_the_implementation_checklist_and_the_example() -> None:
    """P-4 AC-3. expected_behavior_source: ADR-004 decision 3 ("For each phase, the plan writes
    its acceptance criteria and checks before its file operations") and decision 4 ("After the
    test plan comes the checklist"), and BC-22; the interface of P-4 gives the two headings, once
    each, both before the YAML example."""
    test_plan = heading_line(PLAN_FORMAT, TEST_PLAN)
    checklist = heading_line(PLAN_FORMAT, CHECKLIST)

    assert test_plan < checklist < example_line(PLAN_FORMAT)


def test_bc22_the_opening_says_the_test_plan_comes_first() -> None:
    """P-4 AC-3. expected_behavior_source: ADR-004 decision 3 (the test plan first, for each
    phase) and decision 4 ("After the test plan comes the checklist"), and BC-22; the interface of
    P-4 puts the sentence before `## The test plan`."""
    opening = before_line(PLAN_FORMAT, heading_line(PLAN_FORMAT, TEST_PLAN))

    assert (
        "For each phase the plan holds the test plan first, then the implementation checklist."
        in opening
    )


@pytest.mark.parametrize("phrase", TEST_PLAN_PHRASES)
def test_bc22_the_test_plan_states_sources_completion_entries_and_the_warning_mark(
    phrase: str,
) -> None:
    """P-4 AC-3. expected_behavior_source: ADR-004 decision 3 (a criterion is a scenario with its
    expected outcome; its source is a `BC-n`, an `R-n` or a `Q-n`, or the AS-IS fact `A-n` for a
    regression, never code; a `completion` entry per check with the command, every expanded
    expression replaced by a placeholder, and its sources as `orqlet evidence cite` prints them;
    the warning-list mark; "A check without a found command is a question"), BC-22 and ADR-002
    decision 3 (*No credentials*: "replaced by a named placeholder"; *Who runs what*: path, lines,
    revision, sha256, the defining lines, the files it directly invokes, the configuration lines
    it reads, and the mark in the `completion` entry and the plan's self-check). The warning list
    of ADR-002 decision 6 is in the plan skill's references/phase-contract.md (line 33)."""
    assert phrase in squash(section(reference(PLAN_FORMAT), TEST_PLAN))


def test_bc22_in_the_example_criteria_and_checks_come_before_file_operations() -> None:
    """P-4 AC-3. expected_behavior_source: BC-22 ("In the `plan-format.md` example,
    `acceptance_criteria` and `checks` come before `file_operations`") and ADR-004 decision 3 ("in
    the format example"); ADR-004 Context records that the example listed file operations first
    (plan-format.md:21-35)."""
    for phase in plan_phases():
        keys = list(phase)
        assert {"acceptance_criteria", "checks", "file_operations"} <= set(keys), keys
        assert keys.index("acceptance_criteria") < keys.index("file_operations"), keys
        assert keys.index("checks") < keys.index("file_operations"), keys


def test_bc22_every_criterion_source_in_the_example_is_a_requirement_or_fact_id() -> None:
    """P-4 AC-3. expected_behavior_source: BC-22 ("a criterion's source is a `BC-n`, `R-n` or
    `Q-n`, or, for a regression, an `A-n`, never code") and ADR-004 decision 3; ADR-004 Context:
    the contract leaves the source free text (src/orqlet/application/contracts/plan.py:31), so the
    format and its example carry the rule."""
    sources = criterion_sources()

    assert [s for s in sources if not CRITERION_SOURCE.match(s)] == []


def test_bc22_the_example_holds_a_regression_and_a_new_behaviour() -> None:
    """P-4 AC-3. expected_behavior_source: ADR-004 decision 3 ("Its source is a `BC-n`, an `R-n`
    or a `Q-n` for new behaviour, or the AS-IS fact `A-n` for a regression that must keep
    working") and BC-22; the interface of P-4 shows both kinds in the example."""
    sources = criterion_sources()

    assert any(REGRESSION_SOURCE.match(s) for s in sources), sources
    assert any(not REGRESSION_SOURCE.match(s) for s in sources), sources


def test_bc22_each_check_has_one_completion_entry_with_its_command_placeholder_and_hash() -> None:
    """P-4 AC-3. expected_behavior_source: BC-22 ("each check has a `completion` entry with the
    command, every expanded expression replaced by a placeholder, and its sources as `orqlet
    evidence cite` prints them"), ADR-004 decision 3 and ADR-002 decision 3 (`orqlet evidence
    cite` gives path, lines, revision and sha256; an expanded expression becomes a named
    placeholder such as `<API_TOKEN>`); the interface of P-4: the entry starts with the check's id,
    a colon and a space."""
    for _, entry in own_entries():
        commands = BACKTICKED.findall(entry)
        assert commands, entry
        assert any(PLACEHOLDER.search(command) for command in commands), entry
        assert "sha256" in entry


def test_bc22_the_example_marks_a_warning_list_check_in_its_own_entry_and_the_self_check() -> None:
    """P-4 AC-3. expected_behavior_source: ADR-004 decision 3 ("A command that matches the warning
    list of ADR-002 decision 6 is marked in its entry and in the plan's self-check") and ADR-002
    decision 3 (*Who runs what*: "A check whose command matches the warning list of decision 6 is
    marked as such in its `completion` entry and in the plan's self-check, so the reviewer of the
    plan pull request sees it"), and BC-22. The interface of P-4, as the Coder answered the
    Tester: a check's own entry holds "Warning list:", and a self-check entry whose `what` names
    the "warning list" has a `how` that names that check's id."""
    marked = [check for check, entry in own_entries() if "Warning list:" in entry]
    hows = warning_list_hows()

    assert marked, "no check's own completion entry holds 'Warning list:'"
    assert hows, "no self-check entry of the plan example names the 'warning list'"
    assert [check for check in marked if not any(names_id(how, check) for how in hows)] == []


# --- Q-12: no technology word in the references of P-4 -------------------------------------------
@pytest.mark.parametrize("path", [AS_IS_FORMAT, DESIGN_FORMAT, PLAN_FORMAT])
def test_q12_no_format_reference_names_a_technology_that_the_injection_test_counts(
    path: str,
) -> None:
    """P-4 AC-6. expected_behavior_source: Q-12 ("No skill, reference or role text of P-2 to P-5
    names Python, Flask, pip, Rust, clap, SQLx, Tokio or Kafka as a word, and the P-1 test stays
    as it is"), for the three references that P-4 changes. AC-6 requires the tests of P-1 to P-3
    to pass without edit, among them the P-1 test of BC-6 that counts those words."""
    text = reference(path)

    assert [word for word in TECHNOLOGY_WORDS if names_word(text, word)] == []
