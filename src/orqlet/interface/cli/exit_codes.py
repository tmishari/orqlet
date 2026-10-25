"""Exit codes of every command. A script can rely on these numbers."""

from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    PROBLEMS = 1  # the command ran and found problems in the project
    USAGE = 2  # wrong options or arguments (the value Typer and Click use)
    REFUSED = 3  # the command refused: invalid input, unsafe state or a rule that forbids it
    NEEDS_INPUT = 4  # a question is open and there is no terminal to ask it
    CHECK_FAILED = 5  # a read-only check (doctor, sync) found an error
    INTERNAL = 70  # a bug in Orqlet
