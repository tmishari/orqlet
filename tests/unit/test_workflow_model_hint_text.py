"""The model hint, the diversity step, the PR-text step and the two references (task
dynamic-model-profiles, phase P-13, AC-6 to AC-9).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-13 in
docs/design/dynamic-model-profiles/plan.yaml, BC-n are the behaviour criteria of
docs/design/dynamic-model-profiles/design/component.md, "ADR-00n" are the files `adr-00n-*.md` in
the same folder, R-n are the requirements and Q-n the questions of
docs/design/dynamic-model-profiles/questions.yaml. The helpers are those of
tests/unit/test_workflow_skill_contracts.py (a body is the rendered body with every command
present unless a test says otherwise; a step is a numbered line with its indented continuation
lines; a phrase is looked for with every run of white space as one space, its letter case pinned).

HOW THESE TESTS WERE WRITTEN. The Tester of P-13 wrote them before the Coder changed the six skill
texts and the two references, from the criteria AC-6 to AC-9, BC-24, BC-35, BC-38, ADR-001 decision
8, ADR-006 decisions 3, 4, 5 and 8, ADR-007 decisions 2, 4, 5, 9 and 11, Q-37 and the interface
that the Coder gave for P-13 (the exact wording of the hint, of the diversity step, of the start
step and of the PR-text step, and the phrases of the two references). Each test is expected to
fail until its text exists. Those that today's files already meet pass at once: the four
`phase-contract.md` copies are identical and unchanged, and every test that checks the absence of
the hint passes while there is no hint.

THE PLAN NAMES NO TEST FILE FOR AC-9 (the two references). The plan lists this file for AC-6 to
AC-8 only; AC-9 is pinned here, at the end, and the Tester's report says so.

P-6 OF workflow-efficiency. The Tester of P-6 changed this file for the four phase skills only,
before the Coder changed their texts, from AC-1 and AC-7 of phase P-6 in
docs/design/workflow-efficiency/plan.yaml, BC-6 of docs/design/workflow-efficiency/design/
component.md, ADR-004 decision 4 of that folder and the interface that the Coder gave (the exact
one-sentence form). Research, design, plan and implement now end step 1 with `short_hint_of`;
review and onboard keep `long_hint_of`, and the `requires: models resolve` mechanics are as tested
below. The SHA-256 pin of the four contract copies is removed, because P-6 changes those copies.

Choices:
- The hint is the one indented continuation line at the end of step 1, in the source and in the
  render. With `models resolve` missing from the command set, the line goes and step 1 is what it
  was (`render_steps` drops a line whose `requires` marker names a missing command).
- The review skill with `models resolve` missing loses the diversity step and nothing else: it
  has one step fewer, numbered from 1 without a gap, and it still starts the three reviewers.
- The closed warnings of `orqlet validate review` are those of `CLOSED_WARNINGS` in
  src/orqlet/application/usecases/review_identity.py, six names. The interface lists four of them;
  AC-9 says "the closed warnings of `validate review`", so every name of the code is pinned.
- The size limits are those of BC-35 (70 lines, 900 words) with every command present; the
  existing test in tests/unit/test_workflow_skill_contracts.py pins the same limit and stays.

Deliberately NOT pinned (the design leaves it open, or a phrase would only copy a file):
- the wording of the references around the pinned phrases and the order of their rules;
- the starting assignment of `orqlet-pr-writer` (the profile `economy`): it is a fact of the seed
  and is pinned with the seed (AC-10);
- the golden files of the skills and the manifest (the golden tests and `manifest-check`).
"""

from __future__ import annotations

import re

import pytest
from tools.build_manifest import WORKFLOW_DIR

from orqlet.application.usecases.review_identity import CLOSED_WARNINGS
from orqlet.application.usecases.workflow_sources import parse_source
from orqlet.interface.cli.exit_codes import ExitCode
from tests.unit.render.test_skills import BEFORE_RECORDS, command_options
from tests.unit.test_workflow_lookup_text import products_in
from tests.unit.test_workflow_skill_contracts import (
    ALL_SKILLS,
    EVERY_COMMAND,
    NUMBERED,
    PHASE_SKILLS,
    WORKFLOW,
    blocks_before_the_sections,
    body,
    first_step_with,
    numbered_items,
    skills_for,
    source_of,
    squash,
)

pytestmark = pytest.mark.unit

REVIEW = "orqlet-review"
IMPLEMENT = "orqlet-implement"
MARKER = "<!-- requires: models resolve -->"
WITHOUT_MODELS_RESOLVE = EVERY_COMMAND - {"models resolve"}
CONTRACT_COPIES = {
    skill: WORKFLOW_DIR / "skills" / skill / "references" / "phase-contract.md"
    for skill in PHASE_SKILLS
}


def long_hint_of(skill: str) -> str:
    """The sentence of AC-6 of P-13, with the skill's own name: review and onboard keep it."""
    return (
        f"Run `orqlet models resolve --skill {skill} --client <your client>`, offer the person "
        "the profile and the models it prints as a suggestion for this work, and never change "
        "the model yourself; with exit status 1 or 3, say that no suggestion exists and go on."
    )


def short_hint_of(skill: str) -> str:
    """The one sentence of P-6 AC-7 (workflow-efficiency) that research, design, plan and
    implement carry instead of the long one."""
    return (
        f"Run `orqlet models resolve --skill {skill} --client <your client>` and give the person "
        "its opening sentence as a suggestion; never change the model yourself, and on exit "
        "status 1 or 3 say that none exists and go on."
    )


def hint_of(skill: str) -> str:
    """The hint that the skill's step 1 ends with: the short sentence in the four phase skills
    (P-6), the long sentence of P-13 in review and onboard (P-6 leaves them as they were)."""
    return short_hint_of(skill) if skill in PHASE_SKILLS else long_hint_of(skill)


def step_one_lines(skill: str) -> list[str]:
    """The lines of step 1 of the source: the numbered line and its indented continuations."""
    lines = source_of(skill).split("\n")
    start = next(n for n, line in enumerate(lines) if NUMBERED.match(line))
    end = start + 1
    while end < len(lines) and lines[end].startswith(" "):
        end += 1
    return lines[start:end]


def step_numbers(text: str) -> list[str]:
    return re.findall(r"^(\d+)\. ", text, re.MULTILINE)


# --- AC-6: the hint line in step 1 of each of the six skills --------------------------------------
@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_ac6_step_one_of_the_source_ends_with_one_indented_gated_hint_line(skill: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("Step 1 of each of the six skills gains one indented
    continuation line, gated by `<!-- requires: models resolve -->`, in this wording with the
    skill's own name"); BC-35 ("each workflow skill's opening step names that hint and does not
    change the model"); ADR-001 decision 8 (the hint is gated on the command). P-6 AC-7
    (workflow-efficiency; BC-6, ADR-004 decision 4: "The model-suggestion step stays in each skill
    that runs it ... and shrinks to one sentence") changes the wording for research, design, plan
    and implement to `short_hint_of`; review and onboard keep the wording of P-13."""
    lines = step_one_lines(skill)

    assert lines[-1] == f"   {hint_of(skill)} {MARKER}"
    assert sum(MARKER in line for line in lines) == 1
    assert source_of(skill).count(hint_of(skill)) == 1


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_ac6_step_one_of_the_rendered_skill_ends_with_the_hint_and_no_marker(skill: str) -> None:
    """AC-6. expected_behavior_source: AC-6 (the wording, `orqlet models resolve --skill <skill
    name> --client <your client>`; "offer the person the profile and the models it prints as a
    suggestion for this work, and never change the model yourself; with exit status 1 or 3, say
    that no suggestion exists and go on"); BC-35; R-1 (the person decides the model). The quoted
    wording is the one that review and onboard keep; for the four phase skills P-6 AC-7 and
    ADR-004 decision 4 give the one sentence of `short_hint_of`."""
    first = numbered_items(body(skill))[0]

    assert first.endswith(hint_of(skill))
    assert "<!--" not in body(skill)


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_ac6_the_hint_is_gone_when_models_resolve_is_not_an_implemented_command(
    skill: str,
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("gated by `<!-- requires: models resolve -->`");
    ADR-001 decision 8 and the step filter of `render_steps` (a line whose `requires` marker names
    a command that the release lacks is dropped, and the list is numbered again): step 1 is what
    it was without the hint, and no skill names `orqlet models` at all."""
    with_hint = numbered_items(body(skill))[0]
    without = body(skill, WITHOUT_MODELS_RESOLVE)

    assert numbered_items(without)[0] == with_hint.removesuffix(f" {hint_of(skill)}")
    assert "models resolve" not in squash(without)
    assert "orqlet models" not in squash(without)
    assert step_numbers(without) == [str(n) for n in range(1, len(step_numbers(without)) + 1)]


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_ac6_each_skill_names_only_its_own_name_in_the_hint(skill: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("with the skill's own name"); BC-35 (`--skill S`
    names the skill that runs it): one `--skill` flag in the body, and it names this skill."""
    assert re.findall(r"--skill (\S+)", body(skill)) == [skill]


def test_ac6_the_hint_names_flags_that_the_command_has_and_the_exit_codes_it_gives() -> None:
    """AC-6. expected_behavior_source: AC-6 ("with exit status 1 or 3, say that no suggestion
    exists"); BC-38 (exit 1 when no candidate qualifies); ADR-001 decision 8 and the command in
    src/orqlet/interface/cli/commands/models.py (a refusal exits 3); the flags of the hint and of
    the diversity step (AC-7) exist."""
    options = command_options("models resolve")

    assert {"--skill", "--client", "--profile", "--role", "--different-family-from"} <= options
    assert int(ExitCode.PROBLEMS) == 1
    assert int(ExitCode.REFUSED) == 3


@pytest.mark.parametrize("skill", PHASE_SKILLS)
def test_ac6_the_phase_contract_references_stay_byte_identical_in_their_four_folders(
    skill: str,
) -> None:
    """AC-6; P-6 AC-1. expected_behavior_source: AC-6 ("The phase-contract references stay
    byte-identical in their four folders") and P-6 AC-1 of workflow-efficiency ("The four copies
    of the phase contract are identical"). P-6 lists all four copies as modified files, so the
    SHA-256 of the copies of the base commit that P-13 pinned here is removed with the text it
    hashed; the identity of the four copies stays."""
    data = CONTRACT_COPIES[skill].read_bytes()

    assert data == CONTRACT_COPIES["orqlet-research"].read_bytes()


@pytest.mark.parametrize("skill", PHASE_SKILLS)
def test_p6_the_model_step_of_a_phase_skill_is_one_sentence_without_the_long_wording(
    skill: str,
) -> None:
    """P-6 AC-7. expected_behavior_source: BC-6 of workflow-efficiency and ADR-004 decision 4
    ("The model-suggestion step ... shrinks to one sentence"); the interface of P-6 (one sentence
    of the exact form of `short_hint_of`). The sentence ends the step, holds one full stop, and
    the long wording of P-13 is gone from the rendered body."""
    hint = short_hint_of(skill)
    first = numbered_items(body(skill))[0]
    line = step_one_lines(skill)[-1].removesuffix(MARKER).strip()

    assert first.endswith(hint)
    assert line == hint
    assert line.count(". ") == 0
    assert line.endswith(".")
    assert long_hint_of(skill) not in squash(body(skill))
    assert "offer the person the profile" not in squash(body(skill))


@pytest.mark.parametrize("skill", ["orqlet-onboard", "orqlet-review"])
def test_p6_review_and_onboard_keep_the_long_model_sentence(skill: str) -> None:
    """P-6 AC-7. expected_behavior_source: the interface of P-6 ("review and onboard keep today's
    longer sentence and today's pins"); ADR-004 decision 4 (the step "stays in each skill that
    runs it, because review and onboard have no phase contract")."""
    assert numbered_items(body(skill))[0].endswith(long_hint_of(skill))


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_ac6_each_body_with_every_command_fits_70_lines_and_900_words(skill: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("With every command present, each skill body is at
    most 70 lines and 900 words"); BC-35 ("Every rendered skill body is at most 70 lines and 900
    words"). The hint adds about 45 words to each skill, so a skill that stood near 900 words
    must be shortened elsewhere."""
    text = body(skill)

    assert len(text.splitlines()) <= 70
    assert len(text.split()) <= 900


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_ac6_each_body_names_no_product_or_vendor_client(skill: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("names no product or vendor"); ADR-001 decision 8 of
    the task team-conventions-resources (no skill text names a product), whose list of names
    tests/unit/test_workflow_lookup_text.py holds; R-1 (the client names the model, not the
    skill)."""
    assert products_in(body(skill)) == []


# --- AC-7: the review skill starts three reviewers, after the diversity step ----------------
def review_steps() -> list[str]:
    return numbered_items(body(REVIEW))


def test_ac7_the_review_skill_description_names_the_three_reviews() -> None:
    """AC-7. expected_behavior_source: AC-7 ("three independent reviewers read the packet (Code,
    Architecture, Security)"); BC-15 (`/orqlet-review` starts three reviewers); the interface of
    P-13 gives the description; ADR-001 decision 1 of phase-skill-contracts (the trigger stays)."""
    fields, _ = parse_source(
        f"skills/{REVIEW}/skill.md", source_of(REVIEW), required=("name", "description")
    )

    assert fields["description"] == (
        "Start the independent Code, Architecture and Security reviews of the staged change on a "
        "read-only packet, and record their results. Use only when the person runs it, before "
        "committing."
    )


def test_ac7_the_purpose_says_that_three_independent_reviewers_read_the_packet() -> None:
    """AC-7. expected_behavior_source: AC-7 ("The review skill says in its purpose that three
    independent reviewers read the packet (Code, Architecture, Security)"); BC-15; ADR-006
    decision 2."""
    purpose = squash(blocks_before_the_sections(body(REVIEW))[1])

    assert purpose.startswith(
        "Three independent reviewers read the exact staged snapshot of one phase"
    )
    assert "the Code Reviewer, the Architecture Reviewer and the Security Reviewer." in purpose


def test_ac7_no_text_of_the_review_skill_counts_two_reviewers_any_more() -> None:
    """AC-7. expected_behavior_source: AC-7 and BC-15 (three reviewers); the interface of P-13
    ("'Three' appears nowhere as 'Two'"): the old purpose said "Two independent reviewers"."""
    text = squash(body(REVIEW)).lower()
    description = squash(source_of(REVIEW).split("\n---\n", 1)[0]).lower()

    for stale in ("two independent", "both reviewers", "two reviewers", "the two reviewers"):
        assert stale not in text
    assert "independent architecture and security reviews" not in description


def test_ac7_the_review_skill_has_ten_steps_and_the_stop_step_stays_last() -> None:
    """AC-7. expected_behavior_source: AC-7 ("Between steps 2 and 3 it holds the diversity
    step"); the interface of P-13 (old steps 3 to 9 become 4 to 10; the STOP step stays last);
    BC-2 of phase-skill-contracts (the last step holds "STOP.")."""
    steps = review_steps()

    assert step_numbers(body(REVIEW)) == [str(n) for n in range(1, 11)]
    assert "STOP." in steps[-1]


def test_ac7_the_inputs_still_name_the_step_that_writes_the_packet() -> None:
    """AC-7. expected_behavior_source: AC-7 (the diversity step sits between steps 2 and 3, so the
    packet is still written by step 2); BC-2 of phase-skill-contracts: a reference to a step by
    number names the step that does the work."""
    steps = review_steps()
    named = re.findall(r"The packet that step (\d+) writes", body(REVIEW))

    assert named == [str(first_step_with(steps, "Run `orqlet review prepare") + 1)]


DIVERSITY_PHRASES = (
    "Record the coder's model, requested and observed, with the source of each.",
    "exact match with a `name` or an `also_known_as`",
    "`orqlet models resolve --profile engineering --client <coder's client>`",
    "`orqlet models resolve --role orqlet-code-reviewer --client <reviewer's client> "
    "--different-family-from <that id>`",
    "leave the flag out, saying so, when nothing matches",
    "When the client lets a start name a model, start the code reviewer on the first candidate",
    "record the model requested and the model observed",
    "On exit status 1 report the review as NOT_RUN and ask for another client or a human "
    "code-owner review, never a new session of the same client.",
)


def diversity_step() -> str:
    steps = review_steps()
    return steps[first_step_with(steps, "--different-family-from")]


@pytest.mark.parametrize("phrase", DIVERSITY_PHRASES)
def test_ac7_the_diversity_step_holds_its_phrases(phrase: str) -> None:
    """AC-7. expected_behavior_source: AC-7 ("record the coder's model, requested and observed,
    with its source; find the catalog id of that model by an exact match with a `name` or
    `also_known_as` among the candidates that `orqlet models resolve --profile engineering
    --client <coder's client>` prints; run `orqlet models resolve --role orqlet-code-reviewer
    --client <reviewer's client> --different-family-from <that id>`, leaving the flag out when
    nothing matches and saying so; start the reviewer on the first candidate when the client lets
    a start name a model and record requested and observed; on exit status 1 report NOT_RUN and
    ask for another client or a human code-owner review, never a new session of the same
    client"); ADR-007 decision 11; ADR-006 decision 5; Q-37 (another client or a human only)."""
    assert phrase in diversity_step()


def test_ac7_the_diversity_step_records_the_coders_model_before_the_lookups() -> None:
    """AC-7. expected_behavior_source: AC-7 and ADR-007 decision 11 ("Before it starts the code
    reviewer it records the coder's model ..., runs `orqlet models resolve ...`"): the record
    comes first, the lookup of the id second, the family flag third, the start fourth, the exit
    status fifth."""
    step = diversity_step()
    order = [
        "Record the coder's model",
        "--profile engineering",
        "--different-family-from",
        "start the code reviewer on the first candidate",
        "On exit status 1",
    ]

    positions = [step.index(part) for part in order]
    assert positions == sorted(positions)


def test_ac7_the_diversity_step_sits_between_the_packet_and_the_start_of_the_reviewers() -> None:
    """AC-7. expected_behavior_source: AC-7 ("Between steps 2 and 3 it holds the diversity step",
    steps 2 and 3 of the old numbering: the packet, then the start of the reviewers); ADR-007
    decision 11 (before it starts the code reviewer); the interface of P-13 (the start step is
    now step 4)."""
    steps = review_steps()
    prepare = first_step_with(steps, "Run `orqlet review prepare")
    diversity = first_step_with(steps, "--different-family-from")
    start = first_step_with(steps, "Start `orqlet-code-reviewer`")

    assert (prepare, diversity, start) == (1, 2, 3)


def test_ac7_the_diversity_step_is_gated_on_the_command_in_the_source() -> None:
    """AC-7. expected_behavior_source: AC-7 (the step runs `orqlet models resolve`); ADR-001
    decision 8 and BC-35 (a step that names a command carries the `requires` marker of that
    command, as `test_a_skill_never_names_a_command_that_the_release_it_is_rendered_for_lacks`
    of tests/unit/render/test_skills.py demands)."""
    lines = [line for line in source_of(REVIEW).split("\n") if "--different-family-from" in line]

    assert len(lines) == 1
    assert NUMBERED.match(lines[0])
    assert lines[0].endswith(MARKER)


def test_ac7_without_models_resolve_the_review_skill_loses_only_the_diversity_step() -> None:
    """AC-7. expected_behavior_source: AC-7 and ADR-001 decision 8 (the gate): the render without
    `models resolve` keeps the start of the three reviewers and the stop step, numbers the nine
    steps from 1 without a gap, and no longer names the family flag."""
    text = body(REVIEW, WITHOUT_MODELS_RESOLVE)
    steps = numbered_items(text)

    assert step_numbers(text) == [str(n) for n in range(1, 10)]
    assert "--different-family-from" not in text
    assert "Start `orqlet-code-reviewer`" in steps[2]
    assert "STOP." in steps[-1]


START_PHRASES = (
    "Start `orqlet-code-reviewer`, `orqlet-arch-reviewer` and `orqlet-security-reviewer` as "
    "typed subagents, each in a clean context, giving each the packet path and nothing else:",
    "A subagent that inherits this conversation is a fork, not an independent reviewer.",
)


@pytest.mark.parametrize("phrase", START_PHRASES)
def test_ac7_the_start_step_names_the_three_reviewers_each_in_a_clean_context(phrase: str) -> None:
    """AC-7. expected_behavior_source: AC-7 ("starts `orqlet-code-reviewer`,
    `orqlet-arch-reviewer` and `orqlet-security-reviewer` in step 3, each in a clean context with
    the packet path and nothing else"); ADR-006 decision 2; ADR-007 decision 4 (a fresh context);
    tests/unit/render/test_skills.py pins "is a fork, not an independent reviewer"."""
    steps = review_steps()

    assert phrase in steps[first_step_with(steps, "Start `orqlet-code-reviewer`")]


def test_ac7_the_step_that_says_what_a_reviewer_returns_speaks_of_each_reviewer() -> None:
    """AC-7. expected_behavior_source: AC-7 and BC-15 (three reviewers, so the old "Each reviewer
    returns findings" stays true); the interface of P-13 (the step says "Each reviewer returns
    findings"). This passes at once: today's step already says it."""
    steps = review_steps()

    assert (
        "Each reviewer returns findings in the format of `references/review-format.md`"
        in (steps[first_step_with(steps, "Each reviewer returns findings")])
    )


# --- AC-8: the implement skill drafts the pull-request text ---------------------------------
def implement_steps(commands: frozenset[str] = EVERY_COMMAND) -> list[str]:
    return numbered_items(skills_for(commands)[IMPLEMENT].body)


PR_STEP_PHRASES = (
    "Start `orqlet-pr-writer` as a typed subagent, giving it the paths of the plan, the design "
    "brief and a summary of the staged diff, and nothing else.",
    "Show the title and the description that it returns to the person as a draft",
    "never open the pull request yourself",
    "Without subagents, say so and skip the draft.",
)


@pytest.mark.parametrize("phrase", PR_STEP_PHRASES)
def test_ac8_the_pr_text_step_starts_the_pr_writer_with_three_inputs_and_shows_a_draft(
    phrase: str,
) -> None:
    """AC-8. expected_behavior_source: AC-8 ("a step that starts `orqlet-pr-writer` as a typed
    subagent with the paths of the plan, the design brief and a summary of the staged diff and
    nothing else, shows the returned title and description to the person as a draft and never
    opens the pull request; without subagents it says so and skips the draft"); ADR-006 decision
    8 ("shows the draft to the person, who opens the pull request"); BC-24."""
    steps = implement_steps()

    assert phrase in steps[first_step_with(steps, "orqlet-pr-writer")]


def test_ac8_the_pr_text_step_comes_before_the_stop_step_and_the_stop_step_stays_last() -> None:
    """AC-8. expected_behavior_source: AC-8 ("before its final stop step"; "The stop step stays
    the last"); BC-24 ("The implement skill's last step starts `orqlet-pr-writer`", read with the
    plan's AC-8: the PR-text step precedes the stop step); the interface of P-13 (the old step 10
    becomes step 11)."""
    steps = implement_steps()
    holders = [n for n, step in enumerate(steps) if "orqlet-pr-writer" in step]

    assert len(steps) == 11
    assert holders == [len(steps) - 2]
    assert "STOP." in steps[-1]
    assert "STOP." not in steps[-2]
    assert steps[-1].startswith("11. STOP.")


def test_ac8_the_pr_text_step_needs_no_command_so_every_release_keeps_it() -> None:
    """AC-8. expected_behavior_source: AC-8 and the interface of P-13 ("no `requires` marker; the
    role is part of the package"): the step carries no marker in the source, and the render for
    the commands that came before the records still has it, second to last, and still ends with
    the stop step."""
    lines = [line for line in source_of(IMPLEMENT).split("\n") if "orqlet-pr-writer" in line]
    before = implement_steps(BEFORE_RECORDS)

    assert len(lines) == 1
    assert "<!--" not in lines[0]
    assert "orqlet-pr-writer" in before[-2]
    assert "STOP." in before[-1]


def test_ac8_the_implement_skill_no_longer_counts_two_reviewers() -> None:
    """AC-8. expected_behavior_source: BC-15 and ADR-006 decision 2 (`/orqlet-review`, which the
    implement skill hands over to, starts three reviewers, so a purpose paragraph that says "both
    reviewers" is false); AGENTS.md ("Update the documentation that your change makes wrong"). The
    Tester's reading, put to the Coder as a question."""
    assert "both reviewers" not in squash(body(IMPLEMENT))


# --- AC-9: the two references ---------------------------------------------------------------------
PLAN_FORMAT = "skills/orqlet-plan/references/plan-format.md"
REVIEW_FORMAT = "skills/orqlet-review/references/review-format.md"


def plan_format() -> str:
    return squash(WORKFLOW.read_text(PLAN_FORMAT))


def review_format() -> str:
    return squash(WORKFLOW.read_text(REVIEW_FORMAT))


PLAN_FORMAT_PHRASES = (
    "`review_evidence` is `architecture-reviewer`, `security-reviewer` and `tester`",
    "and also `code-reviewer` for a plan whose header names workflow version 0.5.0 or higher",
    "`orqlet validate plan` enforces it at the plan level",
)


@pytest.mark.parametrize("phrase", PLAN_FORMAT_PHRASES)
def test_ac9_the_plan_format_says_which_roles_review_evidence_holds_and_who_enforces_it(
    phrase: str,
) -> None:
    """AC-9. expected_behavior_source: AC-9 ("`references/plan-format.md` says that
    `review_evidence` is the three roles, or the three plus `code-reviewer` for a plan whose header
    names workflow version 0.5.0 or higher, and that the plan-level check enforces it"); ADR-006
    decision 3 (the rule moves to the plan level); BC-15 (an older plan still validates)."""
    assert phrase in plan_format()


def test_ac9_the_plan_format_no_longer_says_that_the_evidence_is_always_the_three_roles() -> None:
    """AC-9. expected_behavior_source: AC-9 and ADR-006 decision 3 (a plan of workflow 0.5.0 or
    higher holds four roles, so "always the three roles" is false); BC-15."""
    assert "`review_evidence` is always the three roles" not in plan_format()


def test_ac9_the_review_format_lists_the_code_reviewer_and_its_record_path() -> None:
    """AC-9. expected_behavior_source: AC-9 ("lists the role `code-reviewer` and its path");
    ADR-006 decision 2 (the record role is `code-reviewer`, in
    `docs/design/<task>/reviews/code-reviewer-P-<n>-r<k>.yaml`); decision 6 (every place that
    knows the two reviewer roles gains the third); the path form of the reference is
    `<role>-<phase>-r<round>`."""
    text = review_format()

    assert "`code-reviewer`" in text
    assert "`docs/design/<task>/reviews/code-reviewer-<phase>-r<round>.yaml`" in text
    assert "`<role>` is `architecture-reviewer` or `security-reviewer`" not in text


@pytest.mark.parametrize("field", ["context", "identity_source", "selection_source"])
def test_ac9_the_review_format_shows_the_optional_agent_fields(field: str) -> None:
    """AC-9. expected_behavior_source: AC-9 ("shows the optional fields `context`,
    `identity_source` and `selection_source`"); ADR-007 decisions 2 and 4 (`agent` carries
    `identity_source`, `selection_source` and `context`); BC-16 (the fields are optional, a
    missing `identity_source` means `unknown`)."""
    assert f"`{field}`" in review_format() or f"{field}:" in review_format()


@pytest.mark.parametrize("field", ["fresh", "input"])
def test_ac9_the_review_format_names_the_two_fields_of_the_context(field: str) -> None:
    """AC-9. expected_behavior_source: AC-9 and ADR-007 decision 4 ("`agent.context` records
    `fresh` and `input: packet-only`"); the contract `Context` in
    src/orqlet/application/contracts/review_result.py (fields `fresh` and `input`)."""
    text = review_format()

    assert f"`{field}`" in text or f"{field}:" in text
    assert "packet-only" in text


REVIEW_FORMAT_PHRASES = (
    "only an observed identity shows a family difference",
    "a `code-reviewer` record needs `context.fresh: true`",
    "is NOT_RUN below I2 at every change class",
    "read-only is not enforced by this client",
)


@pytest.mark.parametrize("phrase", REVIEW_FORMAT_PHRASES)
def test_ac9_the_review_format_states_the_identity_freshness_and_codex_rules(phrase: str) -> None:
    """AC-9. expected_behavior_source: AC-9 ("states that only an observed identity shows a
    family difference, that a `code-reviewer` record needs `context.fresh: true` and is NOT_RUN
    below I2 at every class, the phrase for Codex records"); ADR-007 decision 2 ("A family
    difference needs both identities observed"), decision 4 (the freshness attestation), decision
    9 (the fixed phrase of a Codex record, which `CODEX_PHRASE` of review_identity.py holds);
    ADR-006 decision 4 (I2 at every class); BC-16 and BC-22."""
    assert phrase in review_format()


@pytest.mark.parametrize("warning", list(CLOSED_WARNINGS))
def test_ac9_the_review_format_lists_every_closed_warning_of_validate_review(warning: str) -> None:
    """AC-9. expected_behavior_source: AC-9 ("the closed warnings of `validate review`"); ADR-007
    decisions 1, 2, 5 and 9 (`policy-changed-in-this-change`, `binding-added-in-this-change`,
    `identity-unknown`, `same-model-different-client`, the warning for a requested model that
    differs from the observed one, the warning for a Codex record that lacks the phrase). The six
    names are those of `CLOSED_WARNINGS`; the interface of P-13 lists four, which is a question for
    the Coder."""
    assert f"`{warning}`" in review_format()
