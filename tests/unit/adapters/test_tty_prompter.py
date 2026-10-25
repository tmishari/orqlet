"""The terminal prompter is interactive only on a terminal and never loops forever."""

from __future__ import annotations

import io

import pytest

from orqlet.adapters.prompt.tty_prompter import TtyPrompter
from orqlet.adapters.system import SystemClock, UuidGenerator
from orqlet.application.ports.prompter import NoAnswerAvailable, Question

pytestmark = pytest.mark.unit


class Terminal(io.StringIO):
    def __init__(self, text: str = "", *, tty: bool = True) -> None:
        super().__init__(text)
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def prompter(answers: str, *, tty: bool = True) -> tuple[TtyPrompter, Terminal]:
    out = Terminal(tty=tty)
    return TtyPrompter(Terminal(answers, tty=tty), out), out


def test_it_is_interactive_only_when_both_ends_are_terminals() -> None:
    assert prompter("")[0].interactive
    assert not prompter("", tty=False)[0].interactive
    assert not TtyPrompter(Terminal(tty=True), Terminal(tty=False)).interactive


def test_a_non_terminal_never_asks() -> None:
    quiet, out = prompter("main\n", tty=False)

    with pytest.raises(NoAnswerAvailable):
        quiet.ask(Question("branch", "Branch?"))
    with pytest.raises(NoAnswerAvailable):
        quiet.confirm("Go?")
    assert out.getvalue() == ""


def test_an_answer_is_trimmed_and_an_empty_answer_uses_the_default() -> None:
    asking, _ = prompter("  main  \n\n")

    assert asking.ask(Question("branch", "Branch?")) == "main"
    assert asking.ask(Question("branch", "Branch?", default="trunk")) == "trunk"


def test_a_choice_outside_the_options_is_asked_again_a_bounded_number_of_times() -> None:
    asking, out = prompter("nope\nstill nope\nuv\n")

    answer = asking.ask(Question("pm", "Package manager?", options=("uv", "pip")))

    assert answer == "uv"
    assert "one of: uv, pip" in out.getvalue()


def test_three_wrong_choices_give_an_empty_answer_not_an_endless_loop() -> None:
    asking, _ = prompter("a\nb\nc\nuv\n")

    assert asking.ask(Question("pm", "Package manager?", options=("uv", "pip"))) == ""


def test_end_of_input_is_no_answer() -> None:
    asking, _ = prompter("")

    with pytest.raises(NoAnswerAvailable):
        asking.ask(Question("branch", "Branch?"))


@pytest.mark.parametrize(
    ("typed", "default", "expected"),
    [
        ("y\n", False, True),
        ("YES\n", False, True),
        ("n\n", True, False),
        ("\n", True, True),
        ("\n", False, False),
        ("maybe\n", True, False),
    ],
)
def test_confirm(typed: str, default: bool, expected: bool) -> None:
    asking, _ = prompter(typed)

    assert asking.confirm("Go?", default=default) is expected


def test_the_system_clock_is_utc_and_ids_are_distinct_uuid_text() -> None:
    now = SystemClock().now()
    first, second = UuidGenerator().new_id(), UuidGenerator().new_id()

    assert now.utcoffset() is not None
    assert now.utcoffset().total_seconds() == 0  # type: ignore[union-attr]
    assert first != second
    assert len(first) == 36
