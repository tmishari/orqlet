from __future__ import annotations

from collections.abc import Mapping, Sequence

from orqlet.application.ports.process import ProcessResult


class ScriptedProcessRunner:
    """Returns canned results in order and records every call."""

    def __init__(self, results: Sequence[ProcessResult] = ()) -> None:
        self._results = list(results)
        self.calls: list[tuple[str, ...]] = []
        self.environments: list[Mapping[str, str]] = []

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
        self.calls.append(tuple(argv))
        self.environments.append(dict(env))
        if not self._results:
            raise AssertionError(f"no scripted result for {list(argv)}")
        return self._results.pop(0)
