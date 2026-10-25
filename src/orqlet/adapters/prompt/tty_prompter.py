"""Questions at a terminal. Interactive only when both input and output are terminals."""

from __future__ import annotations

from typing import TextIO

from orqlet.application.ports.prompter import NoAnswerAvailable, Question

_MAX_TRIES = 3


class TtyPrompter:
    def __init__(self, stdin: TextIO, stdout: TextIO) -> None:
        self._stdin = stdin
        self._stdout = stdout

    @property
    def interactive(self) -> bool:
        return self._stdin.isatty() and self._stdout.isatty()

    def ask(self, question: Question) -> str:
        if not self.interactive:
            raise NoAnswerAvailable(question.id)
        for _ in range(_MAX_TRIES):
            answer = self._read(self._format(question))
            if not answer and question.default is not None:
                return question.default
            if not question.options or not answer or answer in question.options:
                return answer
            self._stdout.write(f"Please answer with one of: {', '.join(question.options)}\n")
        return ""

    def confirm(self, text: str, *, default: bool = False) -> bool:
        if not self.interactive:
            raise NoAnswerAvailable(text)
        hint = "[Y/n]" if default else "[y/N]"
        answer = self._read(f"{text} {hint} ").lower()
        return default if not answer else answer in {"y", "yes"}

    def _read(self, prompt: str) -> str:
        self._stdout.write(prompt)
        self._stdout.flush()
        line = self._stdin.readline()
        if line == "":
            raise NoAnswerAvailable("end of input")
        return line.strip()

    @staticmethod
    def _format(question: Question) -> str:
        options = f" [{'/'.join(question.options)}]" if question.options else ""
        default = f" (default: {question.default})" if question.default else ""
        return f"{question.text}{options}{default}: "
