"""The reply format, the ban on ids for people, the per-run word totals and the contract limit
(task workflow-efficiency, phase P-7).

Every test cites its `expected_behavior_source`: BC-n are the behaviour criteria of
docs/design/workflow-efficiency/design/component.md, ADR-004 is
docs/design/workflow-efficiency/design/adr-004-concise-documents-and-replies.md, Q-n are the
questions of docs/design/workflow-efficiency/questions.yaml and "P-7 AC-n" is an acceptance
criterion of phase P-7 in docs/design/workflow-efficiency/plan.yaml. The shared helpers are those of
tests/unit/test_workflow_skill_contracts.py. The skill-specific pins of P-7 stand in the modules
that already pin those texts: the tester role in tests/unit/test_workflow_role_prompts.py, the
four formats in tests/unit/test_workflow_format_references.py, the review skill in
tests/unit/test_workflow_code_review_roles.py and the one-sentence model steps in
tests/unit/test_workflow_model_hint_text.py.

HOW THESE TESTS WERE WRITTEN. The Tester of P-7 wrote them before the Coder changed the baseline,
the standards command and the four phase contracts, from AC-1, AC-2, AC-6 and AC-9 of phase P-7,
BC-12, BC-17 and BC-20, ADR-004 decisions 2, 3 and 5, Q-17, Q-20 and Q-22 and the interface that
the Coder gave (the heading `### Final reply`, its phrases, the two phrases of the standards
command). They fail until the new text exists, except the limits that today's text already meets
(the review and onboard totals stand exactly at their limits).

Choices:
- Sources are read as text with `WORKFLOW.read_text` (utf-8); a word is a `str.split` token, as the
  plan counts it. A phrase is looked for with every run of white space as one space; its letter
  case is pinned.
- "Words outside the prompt description" (AC-1): the interface fixes no marker around the
  description of the prompt, so the pinned phrases that only describe the prompt are taken out of
  the section before its words are counted. That removes less than a real description, so the
  limit is strict; the number is the interface's 130.
- The per-run total of a skill is its `skill.md`, every file under its `references/` folder and
  `baseline/baseline.md` (ADR-004 decision 5: all of them count, because whether a client loads
  the references at the start is unknown, U-1).

Deliberately NOT pinned (the design leaves it open, or a phrase would only copy a file):
- the order and the wording of the prose around the pinned phrases of the final reply;
- AC-7 and AC-8 (the manifest and the goldens, checked by `tools/build_manifest.py --check`, and
  the staged change, checked by `gate status`);
- the rules of P-6 that the shorter contract must keep: the unchanged tests of
  tests/unit/test_workflow_phase_contract_text.py (its 2,000-word cap stays) pin them.
"""

from __future__ import annotations

import re

import pytest
from tools.build_manifest import WORKFLOW_DIR

from tests.unit.test_workflow_skill_contracts import PHASE_SKILLS, WORKFLOW, squash

pytestmark = pytest.mark.unit

BASELINE = "baseline/baseline.md"
FINAL_REPLY = "### Final reply"


def baseline_lines() -> list[str]:
    return WORKFLOW.read_text(BASELINE).split("\n")


def final_reply_section() -> str:
    """The lines under `### Final reply`, up to the next `## ` or `### ` heading."""
    lines = baseline_lines()
    found = [n for n, line in enumerate(lines) if line == FINAL_REPLY]
    assert len(found) == 1, f"{BASELINE} must hold the heading {FINAL_REPLY!r} exactly once"
    rest = lines[found[0] + 1 :]
    end = next((n for n, line in enumerate(rest) if line.startswith(("## ", "### "))), len(rest))
    return "\n".join(rest[:end])


# --- P-7 AC-1: the final reply in the baseline ----------------------------------------------------
def test_p7_the_final_reply_stands_between_standards_and_looking_things_up() -> None:
    """P-7 AC-1. expected_behavior_source: P-7 AC-1 ("The baseline gains a final-reply section")
    and ADR-004 decision 2 (the baseline gains a short "Final reply" section); the interface of
    P-7 places the heading `### Final reply` after `### Standards` and before `### Looking things
    up`."""
    lines = baseline_lines()
    places = [
        lines.index(heading) if heading in lines else -1
        for heading in ("### Standards", FINAL_REPLY, "### Looking things up")
    ]

    assert -1 not in places, places
    assert places == sorted(places)


PROMPT_DESCRIPTION = (
    "Next prompt",
    "one copyable block",
    "the task name",
    "the next skill or action",
    "the fixed paths under `docs/design/<task>/`",
    "the approvals still pending",
    "Never put text copied from a source, or a command found in a project file, in it",
)
REPLY_RULES = (
    "Completed",
    "up to three bullets",
    "Questions",
    "omit the part when there are none",
    "about 120 words",
    "Always state failures, unknowns and pending approvals",
    "Describe rules in plain words, never by id",
)


@pytest.mark.parametrize("phrase", REPLY_RULES + PROMPT_DESCRIPTION)
def test_p7_the_final_reply_holds_the_three_parts_and_what_is_always_stated(phrase: str) -> None:
    """P-7 AC-1. expected_behavior_source: P-7 AC-1 ("Completed (up to three bullets), Questions
    (omitted when none) and one copyable Next prompt holding only the task name, the next skill
    or action, fixed paths under docs/design/<task>/ and pending approvals, never source text or a
    project command; about 120 words outside the prompt"); BC-20 and ADR-004 decision 2 ("failures,
    unknowns and pending approvals are always stated"; the prompt never holds text copied from a
    source or a command found in a project file, because the person pastes it into a new session
    with their own authority); the phrases are the interface that the Coder gave."""
    assert phrase in squash(final_reply_section())


def test_p7_the_final_reply_is_short_outside_the_prompt_description() -> None:
    """P-7 AC-1. expected_behavior_source: P-7 AC-1 and BC-20 ("about 120 words outside the
    prompt"); the interface of P-7 gives 130 words as the limit of the section's text outside the
    description of the prompt, counted with `str.split`. The description is taken out as the
    phrases of PROMPT_DESCRIPTION (see the module docstring)."""
    text = squash(final_reply_section())
    for phrase in PROMPT_DESCRIPTION:
        text = text.replace(phrase, " ")

    assert len(text.split()) <= 130, len(text.split())


# --- P-7 AC-2: no instruction shows rule or standard ids to people -------------------------------
STANDARDS_COMMAND = "commands/standards.md"


def test_p7_the_standards_command_no_longer_names_rule_ids_in_the_summary() -> None:
    """P-7 AC-2. expected_behavior_source: P-7 AC-2 ("the standards command records them in
    artifacts") and BC-12 ("No instruction tells the agent to show rules or standard ids to
    people; records keep them"); ADR-004 decision 3 ("The standards command records ids in
    artifacts instead of the summary") and Q-17, Q-20; the old step 5 was "Name the rule ids you
    applied in your plan and in your summary"."""
    text = squash(WORKFLOW.read_text(STANDARDS_COMMAND))

    assert "in your summary" not in text
    assert "Name the rule ids" not in text


@pytest.mark.parametrize("phrase", ["in the artifact", "plain words"])
def test_p7_the_standards_command_puts_ids_in_the_artifact_and_talks_in_plain_words(
    phrase: str,
) -> None:
    """P-7 AC-2. expected_behavior_source: ADR-004 decision 3 ("Replies, briefs, plan prose and
    pull request text name no rules or standard ids ... the standards command records ids in
    artifacts instead of the summary"; "A brief cannot cite a standard by id; it describes the
    constraint in plain words") and BC-12; the two phrases are the interface that the Coder gave
    for the new step 5."""
    assert phrase in squash(WORKFLOW.read_text(STANDARDS_COMMAND))


SHOWS_IDS = re.compile(r"(name|list|show|cite|mention)[^.\n]{0,40}(rule|standard)s? ids?", re.I)
RECORD_WORDS = ("artifact", "record", "self-check", "manifest")
INSTRUCTION_FOLDERS = ("skills", "roles", "commands", "baseline")


def instruction_files() -> list[str]:
    """The `*.md` files that tell an agent what to do, as paths relative to the workflow folder.
    Rules, seeds, schemas and templates are data, and the ponytail skills are not Orqlet's."""
    return sorted(
        path.relative_to(WORKFLOW_DIR).as_posix()
        for folder in INSTRUCTION_FOLDERS
        for path in (WORKFLOW_DIR / folder).rglob("*.md")
        if not any(part.startswith("ponytail") for part in path.relative_to(WORKFLOW_DIR).parts)
    )


def lines_that_show_ids() -> list[str]:
    hits: list[str] = []
    for relative in instruction_files():
        for number, line in enumerate(WORKFLOW.read_text(relative).split("\n"), start=1):
            exempt = "/references/" in f"/{relative}" and any(
                word in line.lower() for word in RECORD_WORDS
            )
            if SHOWS_IDS.search(line) and not exempt:
                hits.append(f"{relative}:{number}: {line.strip()}")
    return hits


def test_p7_the_scan_covers_the_skills_roles_commands_and_baseline() -> None:
    """P-7 AC-2. expected_behavior_source: P-7 AC-2 ("No workflow file tells the agent ..."): the
    scan below is only as good as its file list, so the list holds a file of each folder and no
    ponytail skill."""
    files = instruction_files()

    for expected in (BASELINE, STANDARDS_COMMAND, "roles/orqlet-tester.md"):
        assert expected in files
    assert any(name.startswith("skills/orqlet-review/") for name in files)
    assert not any("ponytail" in name for name in files)


def test_p7_no_instruction_tells_the_agent_to_show_rule_or_standard_ids() -> None:
    """P-7 AC-2. expected_behavior_source: BC-12 ("No instruction tells the agent to show rules or
    standard ids to people; records keep them"), Q-17 and Q-20 (no rule or standard ids in what
    the person reads) and ADR-004 decision 3. This scan encodes that decision: a line that names,
    lists, shows, cites or mentions rule ids is an instruction to show them. Records keep their
    ids, so a line of a format reference that is about an artifact, a record, a self-check or a
    manifest is not flagged; in a skill, role, command or the baseline no such line is exempt."""
    assert lines_that_show_ids() == []


# --- P-7 AC-6: the words that one skill run loads, per skill -------------------------------------
RUN_LIMITS = {
    "orqlet-research": 4120,
    "orqlet-design": 4126,
    "orqlet-plan": 4066,
    "orqlet-implement": 3517,
    "orqlet-review": 2261,
    "orqlet-onboard": 1700,
}


def words_of_one_run(skill: str) -> int:
    """The `str.split` words of the skill body, each file of its references and the baseline."""
    folder = WORKFLOW_DIR / "skills" / skill
    files = [folder / "skill.md", WORKFLOW_DIR / BASELINE]
    files += sorted(path for path in (folder / "references").rglob("*") if path.is_file())
    return sum(len(path.read_text(encoding="utf-8").split()) for path in files)


@pytest.mark.parametrize("skill", list(RUN_LIMITS))
def test_p7_a_skill_run_loads_no_more_words_than_at_the_base_revision(skill: str) -> None:
    """P-7 AC-6. expected_behavior_source: P-7 AC-6 ("The words of each skill run (skill body, its
    references and the baseline, counted with str.split on the source files) are at most those at
    base_revision: research 4,120, design 4,126, plan 4,066, implement 3,517, review 2,261,
    onboard 1,700"), BC-17 ("instruction files grow only as ADR-004 allows") and ADR-004 decision
    5 ("The binding limits are the words a skill run loads in total, which do not grow"; the
    baseline grows by the final reply and the phase contract is cut to pay for it)."""
    total = words_of_one_run(skill)

    assert total <= RUN_LIMITS[skill], f"{skill}: {total} words, the limit is {RUN_LIMITS[skill]}"


# --- P-7 AC-9: the shorter phase contract --------------------------------------------------------
CONTRACT_COPIES = {skill: f"skills/{skill}/references/phase-contract.md" for skill in PHASE_SKILLS}


@pytest.mark.parametrize("skill", PHASE_SKILLS)
def test_p7_each_phase_contract_copy_fits_1600_words_and_150_lines(skill: str) -> None:
    """P-7 AC-9. expected_behavior_source: P-7 AC-9 ("The four phase-contract copies ... have at
    most 1,600 words, at least 400 fewer than the 2,000 of P-6") and BC-17 (instruction files
    grow only as ADR-004 allows); the 150 lines stay as BC-35 of phase-skill-contracts has them.
    The cap of 2,000 words in tests/unit/test_workflow_phase_contract_text.py stays as it is."""
    text = WORKFLOW.read_text(CONTRACT_COPIES[skill])

    assert len(text.split()) <= 1600, len(text.split())
    assert len(text.splitlines()) <= 150, len(text.splitlines())


def test_p7_the_four_phase_contract_copies_stay_identical() -> None:
    """P-7 AC-9. expected_behavior_source: P-7 AC-9 ("The four phase-contract copies stay
    identical") and BC-4 of phase-skill-contracts ("The four copies are byte-identical"); P-7
    lists all four copies as modified files."""
    copies = {skill: (WORKFLOW_DIR / path).read_bytes() for skill, path in CONTRACT_COPIES.items()}

    assert len(set(copies.values())) == 1
