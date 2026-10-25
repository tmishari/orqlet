from __future__ import annotations

from orqlet.application.ports.prompter import NoAnswerAvailable, Question


class ScriptedPrompter:
    """Answers questions from a script keyed by question id; fails loudly on a surprise."""

    def __init__(
        self,
        answers: dict[str, str] | None = None,
        confirmations: dict[str, bool] | None = None,
        *,
        interactive: bool = True,
        confirm_all: bool | None = None,
    ) -> None:
        self._answers = dict(answers or {})
        self._confirmations = dict(confirmations or {})
        self._interactive = interactive
        self._confirm_all = confirm_all
        self.asked: list[str] = []

    @property
    def interactive(self) -> bool:
        return self._interactive

    def ask(self, question: Question) -> str:
        if not self._interactive:
            raise NoAnswerAvailable(question.id)
        self.asked.append(question.id)
        if question.id in self._answers:
            return self._answers[question.id]
        if question.default is not None:
            return question.default
        raise AssertionError(f"unscripted question: {question.id}")

    def confirm(self, text: str, *, default: bool = False) -> bool:
        if not self._interactive:
            raise NoAnswerAvailable(text)
        self.asked.append(text)
        if self._confirm_all is not None:
            return self._confirm_all
        return self._confirmations.get(text, default)
