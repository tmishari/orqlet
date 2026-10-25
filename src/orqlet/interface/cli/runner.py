"""One way to run a command: build the result, print it as text or JSON, set the exit code."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import typer

from orqlet import __version__
from orqlet.application.contracts.cli_result import CliResult, FindingOut
from orqlet.domain.errors import OrqletError
from orqlet.interface.cli.errors import INTERNAL_CODE, code_for
from orqlet.interface.cli.exit_codes import ExitCode
from orqlet.interface.cli.render_json import render_json


@dataclass(frozen=True, slots=True)
class CommandOutput:
    data: dict[str, object]
    human: str
    findings: tuple[FindingOut, ...] = ()
    not_run: tuple[str, ...] = ()
    exit_code: ExitCode = ExitCode.OK
    echo_findings: bool = True  # False when the human text already lists them


def execute(command: str, action: Callable[[], CommandOutput], *, as_json: bool) -> None:
    """Run `action`, print its result and exit. Expected failures never show a traceback."""
    try:
        output = action()
    except OrqletError as exc:
        output = _failure(code_for(exc), str(exc), ExitCode.REFUSED)
    except Exception as exc:
        output = _failure(INTERNAL_CODE, f"internal error: {type(exc).__name__}", ExitCode.INTERNAL)
    result = CliResult(
        schema_id="orqlet.cli-result/v1",
        ok=output.exit_code is ExitCode.OK,
        command=command,
        orqlet_version=__version__,
        data=output.data,
        findings=output.findings,
        not_run=output.not_run,
    )
    if as_json:
        typer.echo(render_json(result))
    else:
        typer.echo(output.human)
        for finding in output.findings if output.echo_findings else ():
            typer.echo(f"{finding.code}: {finding.message}", err=True)
    raise typer.Exit(int(output.exit_code))


def _failure(code: str, message: str, exit_code: ExitCode) -> CommandOutput:
    return CommandOutput(
        data={},
        human="",
        findings=(FindingOut(code=code, message=message, severity="error"),),
        exit_code=exit_code,
    )
