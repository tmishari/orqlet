"""`SubprocessRunner` with real child processes (the Python interpreter itself)."""

from __future__ import annotations

import sys

import pytest

from orqlet.adapters.process.environment import scrubbed_environment
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.application.ports.process import OutputLimitExceeded, ProcessError, ProcessTimeout

pytestmark = pytest.mark.integration

RUNNER = SubprocessRunner()
ENV = scrubbed_environment({"PATH": "/usr/bin:/bin"})


def python(code: str, **kwargs: object) -> object:
    options: dict[str, object] = {
        "cwd": ".",
        "env": ENV,
        "timeout_seconds": 20,
        "max_output_bytes": 1_000_000,
    }
    options.update(kwargs)
    return RUNNER.run([sys.executable, "-c", code], **options)  # type: ignore[arg-type]


def test_captures_output_and_returns_nonzero_codes_without_raising() -> None:
    result = python("import sys; print('out'); sys.stderr.write('err'); sys.exit(3)")

    assert (result.returncode, result.stdout.strip(), result.stderr) == (3, b"out", b"err")  # type: ignore[attr-defined]


def test_stdin_is_delivered() -> None:
    result = python("import sys; print(sys.stdin.read().upper())", stdin=b"abc")

    assert result.stdout.strip() == b"ABC"  # type: ignore[attr-defined]


def test_the_environment_is_exactly_what_was_passed() -> None:
    result = python("import os; print(sorted(os.environ))", env={"ONLY": "1"})

    assert b"ONLY" in result.stdout  # type: ignore[attr-defined]
    assert b"HOME" not in result.stdout  # type: ignore[attr-defined]


def test_shell_metacharacters_are_plain_arguments() -> None:
    result = RUNNER.run(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", "a; echo injected $(id)"],
        cwd=".",
        env=ENV,
        timeout_seconds=20,
        max_output_bytes=1000,
    )

    assert result.stdout.strip() == b"a; echo injected $(id)"


def test_a_slow_program_is_killed_at_the_timeout() -> None:
    with pytest.raises(ProcessTimeout):
        python("import time; time.sleep(30)", timeout_seconds=0.5)


def test_output_over_the_cap_is_an_error() -> None:
    with pytest.raises(OutputLimitExceeded):
        python("print('x' * 100000)", max_output_bytes=1000)


def test_a_missing_program_is_a_process_error() -> None:
    with pytest.raises(ProcessError, match="cannot start"):
        RUNNER.run(
            ["definitely-not-a-program-orqlet"],
            cwd=".",
            env=ENV,
            timeout_seconds=5,
            max_output_bytes=100,
        )


def test_scrubbed_environment_keeps_only_allowed_names_and_applies_extras() -> None:
    source = {"PATH": "/bin", "HOME": "/h", "AWS_SECRET_ACCESS_KEY": "nope", "LC_ALL": "de"}

    assert scrubbed_environment(source, {"LC_ALL": "C"}) == {
        "PATH": "/bin",
        "HOME": "/h",
        "LC_ALL": "C",
    }
