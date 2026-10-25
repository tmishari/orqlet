"""Running an external program. Used by the Git adapter only; no shell, ever."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from orqlet.domain.errors import OrqletError


@dataclass(frozen=True, slots=True)
class ProcessResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes


class ProcessError(OrqletError):
    """The program could not be started or exceeded a limit."""


class ProcessTimeout(ProcessError):
    pass


class OutputLimitExceeded(ProcessError):
    pass


class ProcessRunner(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str,
        env: Mapping[str, str],
        timeout_seconds: float,
        max_output_bytes: int,
        stdin: bytes | None = None,
    ) -> ProcessResult:
        """Run `argv` with exactly `env`, in `cwd`, bounded in time and output size."""
        ...
