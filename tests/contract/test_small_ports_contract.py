"""Fakes for the clock, id, prompter and process ports behave as the ports promise."""

from __future__ import annotations

from datetime import UTC
from uuid import UUID

import pytest

from orqlet.application.ports.process import ProcessResult
from orqlet.application.ports.prompter import NoAnswerAvailable, Question
from tests.fakes.clock import FixedClock
from tests.fakes.ids import SequentialIds
from tests.fakes.process import ScriptedProcessRunner
from tests.fakes.prompter import ScriptedPrompter

pytestmark = pytest.mark.contract


def test_clock_is_timezone_aware_utc_and_can_advance() -> None:
    clock = FixedClock()
    first = clock.now()
    clock.advance(minutes=5)

    assert first.tzinfo is UTC
    assert (clock.now() - first).total_seconds() == 300


def test_ids_are_distinct_version_4_uuids() -> None:
    ids = SequentialIds()
    first, second = ids.new_id(), ids.new_id()

    assert first != second
    assert UUID(first).version == 4
    assert str(UUID(first)) == first


def test_prompter_answers_from_script_then_default() -> None:
    prompter = ScriptedPrompter({"branch": "main"})

    assert prompter.ask(Question("branch", "Target branch?")) == "main"
    assert prompter.ask(Question("name", "Name?", default="demo")) == "demo"


def test_non_interactive_prompter_raises_instead_of_guessing() -> None:
    prompter = ScriptedPrompter(interactive=False)

    assert prompter.interactive is False
    with pytest.raises(NoAnswerAvailable):
        prompter.ask(Question("branch", "Target branch?", default="main"))
    with pytest.raises(NoAnswerAvailable):
        prompter.confirm("Continue?")


def test_scripted_runner_records_calls_and_fails_on_surprise() -> None:
    result = ProcessResult(("git", "status"), 0, b"", b"")
    runner = ScriptedProcessRunner([result])

    got = runner.run(
        ["git", "status"], cwd="/x", env={"A": "1"}, timeout_seconds=1, max_output_bytes=10
    )

    assert got is result
    assert runner.calls == [("git", "status")]
    with pytest.raises(AssertionError):
        runner.run(["git"], cwd="/x", env={}, timeout_seconds=1, max_output_bytes=10)
