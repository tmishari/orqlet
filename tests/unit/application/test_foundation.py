"""The composed behavioural foundation (task one-command-setup, phase P-3, AC-1, AC-2 and AC-3).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-3 in
docs/design/one-command-setup/plan.yaml, ADR-005 is
docs/design/one-command-setup/design/adr-005-behavioural-foundation.md, Q-n are the questions of
docs/design/one-command-setup/questions.yaml, "the upstream evidence" is
docs/design/one-command-setup/evidence/web/karpathy-skills.md (items 7 to 10 hold the upstream
sentences), "the token answer" is the person's answer to the P-3 AC-3 token question (2026-11-22):
the estimate is UTF-8 bytes divided by 4, rounded up; and "the interface" is the one that the Coder
gave for P-3 (`compose_foundation(workflow)`, the two files it reads, the `<!-- how-to-work -->`
marker line, the `### Three more habits` section, one attribution line, and `SourceError`).

HOW THESE TESTS WERE WRITTEN. The Tester of P-3 wrote them before the implementation existed. The
packaged foundation is composed from `PackagedWorkflow()`; the composition rules and the errors are
pinned with a small in-test fake workflow whose texts are written here, so they do not depend on
the shipped wording.

Choices:
- The "How to work" section of baseline/baseline.md is taken as the lines from `### How to work` up
  to the line before `### Phases and approvals`, without trailing blank lines (the interface).
- The three points (AC-2) are matched by meaning keywords, one point per bullet of
  `### Three more habits`: "interpretation"; "dead code", "mention" and "orphan" or "unused";
  "step", "check" or "verify", and "plan". The wording beyond these words is not pinned (Q-27: the
  wording is Orqlet's own).
- The precedence sentence is matched by "global", "repository" or "project", and one of
  "precedence", "applies", "wins", "overrides" or "priority" (AC-1, ADR-005 decision 4).
- "None of the upstream sentences appears verbatim" is checked case-insensitively, with runs of
  white space collapsed and curly apostrophes made straight, so that a change of case or spacing
  alone does not count as own wording.
- "No sentence says to skip error handling for impossible scenarios" is read as: no sentence holds
  "impossible" together with "error", "failure" or "handl", and the phrase "no error handling" does
  not appear.

Deliberately NOT pinned here:
- AC-4 (the project baseline block and its golden files stay byte-identical): the existing tests
  tests/unit/render/test_clients_golden.py (golden bytes, the shared baseline block across clients)
  and tests/unit/test_manifest.py (the baseline size) already cover it; this phase changes neither
  baseline.md nor a renderer, so it is not duplicated here;
- AC-5 (the manifest lists foundation.md) is the manifest check, and AC-6 (scope) is the gate
  check; neither is a unit test;
- the exact wording of the precedence sentence, the three points and the attribution line.
"""

from __future__ import annotations

import itertools
import math
import re

import pytest

from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.usecases.foundation import compose_foundation
from orqlet.application.usecases.workflow_sources import SourceError
from orqlet.domain.digest import sha256_hex
from orqlet.domain.versions import Version, WorkflowRelease

pytestmark = pytest.mark.unit

FOUNDATION_PATH = "baseline/foundation.md"
BASELINE_PATH = "baseline/baseline.md"
MARKER = "<!-- how-to-work -->"
HOW_TO_WORK = "### How to work"
NEXT_BASELINE_HEADING = "### Phases and approvals"
HABITS = "### Three more habits"
PINNED_URL = (
    "https://github.com/multica-ai/andrej-karpathy-skills/tree/"
    "2c606141936f1eeef17fa3043a72095b4765b9c2"
)
URL = re.compile(r"https?://[^\s)>\]\"']+")
SENTENCE_END = re.compile(r"[.!?](?:\s|$)")
MAX_CHARACTERS = 6000
MAX_TOKENS = 2500
CODEX_BLOCK_BEGIN = "<!-- orqlet:begin foundation workflow@0.5.0#" + "f" * 64 + " -->\n"
CODEX_BLOCK_END = "<!-- orqlet:end foundation -->\n"
# The upstream evidence, items 7 to 10 (skills/karpathy-guidelines/SKILL.md at 2c60614).
UPSTREAM_SENTENCES = (
    "State your assumptions explicitly. If uncertain, ask.",
    "If multiple interpretations exist, present them - don't pick silently.",
    "If a simpler approach exists, say so. Push back when warranted.",
    "No features beyond what was asked.",
    "No abstractions for single-use code.",
    'No "flexibility" or "configurability" that wasn\'t requested.',
    "No error handling for impossible scenarios.",
    'Don\'t "improve" adjacent code, comments, or formatting.',
    "Match existing style, even if you'd do it differently.",
    "If you notice unrelated dead code, mention it - don't delete it.",
    "Remove imports/variables/functions that YOUR changes made unused.",
    "Every changed line should trace directly to the user's request.",
    '"Fix the bug" → "Write a test that reproduces it, then make it pass"',
    "For multi-step tasks, state a brief plan",
    "[Step] → verify: [check]",
)


class FakeWorkflow:
    """Two baseline texts of the test's own, and a log of what was read."""

    def __init__(self, foundation: str, baseline: str) -> None:
        self._files = {FOUNDATION_PATH: foundation, BASELINE_PATH: baseline}
        self._release = WorkflowRelease(Version.parse("0.5.0"), sha256_hex(b"fake"), 1)
        self.reads: list[str] = []

    @property
    def release(self) -> WorkflowRelease:
        return self._release

    def read_text(self, path: str) -> str:
        self.reads.append(path)
        return self._files[path]

    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(self._files))

    def problems(self) -> tuple[str, ...]:
        return ()


FAKE_BASELINE = (
    "## Orqlet baseline\n"
    "\n"
    "Intro.\n"
    "\n"
    "### How to work\n"
    "\n"
    "- First rule.\n"
    "- Second rule.\n"
    "\n"
    "### Next section\n"
    "\n"
    "Other text.\n"
)
FAKE_SECTION = "### How to work\n\n- First rule.\n- Second rule."
FAKE_HABITS = "### Three more habits\n\n- Habit one.\n- Habit two.\n- Habit three."
FAKE_ATTRIBUTION = f"Inspired by [upstream]({PINNED_URL})."


def fake_foundation(marker_lines: str = MARKER) -> str:
    return f"Precedence.\n\n{marker_lines}\n\n{FAKE_HABITS}\n\n{FAKE_ATTRIBUTION}\n"


def composed() -> str:
    return compose_foundation(PackagedWorkflow())


def baseline_how_to_work() -> str:
    """The packaged baseline's "How to work" heading and bullets, without trailing blanks."""
    lines = PackagedWorkflow().read_text(BASELINE_PATH).split("\n")
    start = lines.index(HOW_TO_WORK)
    end = lines.index(NEXT_BASELINE_HEADING)
    return "\n".join(lines[start:end]).rstrip("\n")


def precedence_paragraph(text: str) -> str:
    return text.split("\n\n", 1)[0]


def habit_bullets(text: str) -> list[str]:
    """The `- ` lines after the `### Three more habits` heading."""
    lines = text.split("\n")
    assert lines.count(HABITS) == 1, HABITS
    return [line for line in lines[lines.index(HABITS) + 1 :] if line.startswith("- ")]


def normalised(text: str) -> str:
    return " ".join(text.replace("\u2019", "'").lower().split())


def sentences(text: str) -> list[str]:
    return [part for part in SENTENCE_END.split(text.replace("\n", " ")) if part.strip()]


def is_interpretations(line: str) -> bool:
    return "interpretation" in line.lower()


def is_dead_code(line: str) -> bool:
    lower = line.lower()
    return "dead code" in lower and "mention" in lower and ("orphan" in lower or "unused" in lower)


def is_step_check(line: str) -> bool:
    lower = line.lower()
    return "step" in lower and ("check" in lower or "verify" in lower) and "plan" in lower


POINTS = (is_interpretations, is_dead_code, is_step_check)


# --- AC-1: order, one link, determinism -----------------------------------------------------------


def test_ac1_the_foundation_starts_with_the_precedence_sentence() -> None:
    """AC-1. expected_behavior_source: AC-1 ("in order: the precedence sentence (a repository's own
    instructions take precedence over the global copy)"); ADR-005 decision 4 ("Every global copy
    starts with one sentence ... the project's version applies"); the interface (the first
    paragraph of foundation.md is the precedence sentence)."""
    paragraph = precedence_paragraph(composed())
    lower = paragraph.lower()

    assert len(SENTENCE_END.findall(paragraph)) == 1, paragraph
    assert not paragraph.startswith("#")
    assert "global" in lower
    assert "repository" in lower or "project" in lower
    assert any(word in lower for word in ("precedence", "applies", "wins", "overrides", "priority"))


def test_ac1_the_how_to_work_section_follows_with_the_bytes_of_the_baseline() -> None:
    """AC-1. expected_behavior_source: AC-1 ("the "How to work" section with bytes equal to that
    section of baseline/baseline.md"); ADR-005 decisions 1 and 2 (the baseline section, held once
    in the workflow package); the interface (the marker line is replaced by the section, heading
    and bullets without trailing blank lines; parts are separated by one blank line)."""
    text = composed()
    paragraph = precedence_paragraph(text)

    assert text[len(paragraph) :].startswith(f"\n\n{baseline_how_to_work()}\n\n{HABITS}\n")
    assert MARKER not in text


def test_ac1_three_habit_bullets_follow_the_section() -> None:
    """AC-1. expected_behavior_source: AC-1 ("the three points"), after the "How to work" section;
    ADR-005 decision 1; the interface (a section `### Three more habits` with the three points as
    `- ` bullets)."""
    text = composed()

    assert text.index(baseline_how_to_work()) < text.index(HABITS)
    assert len(habit_bullets(text)) == 3, habit_bullets(text)


def test_ac1_exactly_one_link_and_it_is_the_pinned_upstream_revision() -> None:
    """AC-1. expected_behavior_source: AC-1 ("one attribution link to
    https://github.com/multica-ai/andrej-karpathy-skills/tree/2c60614..."); ADR-005 decision 1
    (one attribution link to the upstream repository at revision 2c60614); Q-27 ("with an
    attribution link")."""
    assert URL.findall(composed()) == [PINNED_URL]


def test_ac1_the_attribution_line_is_last_and_the_only_line_with_the_link() -> None:
    """AC-1. expected_behavior_source: AC-1 (the link comes after the three points); the interface
    (then one attribution line holding the only link; text ending in exactly one newline)."""
    lines = composed().rstrip("\n").split("\n")
    with_link = [line for line in lines if PINNED_URL in line]

    assert with_link == [lines[-1]]
    assert not lines[-1].startswith("- ")


def test_ac1_the_foundation_ends_in_exactly_one_newline() -> None:
    """AC-1. expected_behavior_source: the interface ("returns text ending in exactly one
    newline")."""
    text = composed()

    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_ac1_composing_twice_gives_the_same_bytes() -> None:
    """AC-1. expected_behavior_source: AC-1 ("Composing twice gives the same bytes"); R-10. Both
    from one workflow and from a second instance of it."""
    workflow = PackagedWorkflow()

    first = compose_foundation(workflow).encode("utf-8")

    assert compose_foundation(workflow).encode("utf-8") == first
    assert compose_foundation(PackagedWorkflow()).encode("utf-8") == first


def test_ac1_composition_replaces_the_marker_line_with_the_section_exactly() -> None:
    """AC-1. expected_behavior_source: the interface (reads `baseline/foundation.md` and
    `baseline/baseline.md` through `read_text`; replaces the marker line with the baseline's
    `### How to work` section, heading and bullets, without trailing blank lines, up to the next
    heading; parts separated by one blank line; one final newline); ADR-005 decision 2 (one
    source in the workflow package)."""
    workflow = FakeWorkflow(fake_foundation(), FAKE_BASELINE)

    text = compose_foundation(workflow)

    assert text == f"Precedence.\n\n{FAKE_SECTION}\n\n{FAKE_HABITS}\n\n{FAKE_ATTRIBUTION}\n"
    assert set(workflow.reads) == {FOUNDATION_PATH, BASELINE_PATH}


# --- AC-2: the three points, the failure handling line, no upstream text --------------------------


def test_ac2_each_bullet_carries_one_of_the_three_points() -> None:
    """AC-2. expected_behavior_source: AC-2 ("name several interpretations instead of choosing one
    silently; mention unrelated dead code and remove only orphans of the person's own change;
    outside a phase plan, give each step a check"); ADR-005 Context (the three points not stated
    in Orqlet or Ponytail) and decision 5 (step-then-verify outside a phase plan); BC-20. One point
    per bullet, in any order."""
    bullets = habit_bullets(composed())

    assert len(bullets) == len(POINTS), bullets
    assert any(
        all(point(bullet) for point, bullet in zip(POINTS, order, strict=True))
        for order in itertools.permutations(bullets)
    ), bullets


def test_ac2_the_baseline_failure_handling_line_is_kept() -> None:
    """AC-2. expected_behavior_source: AC-2 ("The explicit failure handling line of the baseline is
    kept"); Q-28 (simplicity keeps validation at trust boundaries and meaningful error handling);
    ADR-005 decision 1 (C-6). The line is read from the packaged baseline."""
    baseline_lines = PackagedWorkflow().read_text(BASELINE_PATH).split("\n")
    failure_lines = [line for line in baseline_lines if "Handle failures explicitly." in line]

    assert len(failure_lines) == 1
    assert failure_lines[0] in composed().split("\n")


def test_ac2_no_sentence_says_to_skip_error_handling_for_impossible_scenarios() -> None:
    """AC-2. expected_behavior_source: AC-2 ("no sentence says to skip error handling for
    impossible scenarios"); ADR-005 decision 1 ("The upstream "no error handling" line is left
    out", C-6); Q-28 (meaningful error handling is kept); the upstream evidence item 8."""
    text = composed()

    assert "no error handling" not in normalised(text)
    for sentence in sentences(text):
        lower = sentence.lower()
        if "impossible" in lower:
            assert not any(word in lower for word in ("error", "failure", "handl")), sentence


@pytest.mark.parametrize("sentence", UPSTREAM_SENTENCES)
def test_ac2_no_upstream_sentence_appears_verbatim(sentence: str) -> None:
    """AC-2. expected_behavior_source: AC-2 ("none of the upstream sentences that the test lists
    appears verbatim"); Q-27 ("Do not vendor its text; write Orqlet's own wording"); ADR-005
    decision 1 ("in Orqlet's own wording"); the upstream evidence items 7 to 10."""
    assert normalised(sentence) not in normalised(composed())


# --- AC-3: size budgets ---------------------------------------------------------------------------


def test_ac3_the_foundation_is_under_6000_characters() -> None:
    """AC-3. expected_behavior_source: AC-3 ("The foundation is under 6,000 characters"); BC-21;
    ADR-005 decision 1 ("The text is under 6,000 characters")."""
    assert len(composed()) < MAX_CHARACTERS


def test_ac3_the_codex_managed_block_is_under_2500_estimated_tokens() -> None:
    """AC-3. expected_behavior_source: AC-3 (the Codex managed block that carries the foundation is
    under 2,500 tokens by the estimate of the existing Codex budget test, which counts bytes:
    tests/unit/test_manifest.py:151-155); the token answer (UTF-8 bytes divided by 4, rounded up);
    A-37 (Codex caps context at 2,500 tokens); the interface (the block's begin and end lines)."""
    block = CODEX_BLOCK_BEGIN + composed() + CODEX_BLOCK_END

    assert math.ceil(len(block.encode("utf-8")) / 4) < MAX_TOKENS


# --- The source errors ----------------------------------------------------------------------------


def test_a_foundation_without_the_marker_is_a_source_error() -> None:
    """expected_behavior_source: the interface (`SourceError` when the marker is missing);
    ADR-005 decision 2 (the foundation must carry the baseline section, so the copies cannot
    drift)."""
    workflow = FakeWorkflow(fake_foundation("No marker here."), FAKE_BASELINE)

    with pytest.raises(SourceError):
        compose_foundation(workflow)


def test_a_foundation_with_the_marker_twice_is_a_source_error() -> None:
    """expected_behavior_source: the interface (`SourceError` when the marker appears more than
    once); AC-1 (the section appears once, in order)."""
    workflow = FakeWorkflow(fake_foundation(f"{MARKER}\n\n{MARKER}"), FAKE_BASELINE)

    with pytest.raises(SourceError):
        compose_foundation(workflow)


def test_a_baseline_without_the_how_to_work_section_is_a_source_error() -> None:
    """expected_behavior_source: the interface (`SourceError` when baseline.md has no
    `### How to work` section); AC-1 (the section is part of the foundation)."""
    baseline = FAKE_BASELINE.replace(HOW_TO_WORK, "### How we work")
    workflow = FakeWorkflow(fake_foundation(), baseline)

    with pytest.raises(SourceError):
        compose_foundation(workflow)
