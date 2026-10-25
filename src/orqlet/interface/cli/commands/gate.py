"""`orqlet gate status`: what an artifact was written against and whether that still holds."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.application.usecases.gate_status import gate_status
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption
from orqlet.interface.cli.commands.validate import BaseOption, HeadOption, output_of
from orqlet.interface.cli.runner import execute
from orqlet.interface.cli.wiring import build_validate_services

gate_app = typer.Typer(help="Check what the workflow's gates would see.", no_args_is_help=True)


@gate_app.command("status")
def status_command(
    task: Annotated[
        str | None,
        typer.Argument(help="A task folder name under docs/design. Without it, print the inputs."),
    ] = None,
    phase: Annotated[
        str | None,
        typer.Option(help="A phase, for example P-1: also compare the change with the design."),
    ] = None,
    base: BaseOption = None,
    head: HeadOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """Read-only and offline. Approval needs host evidence, so a task is always NOT_RUN here."""
    execute(
        "gate status",
        lambda: output_of(
            gate_status(build_validate_services(root), task, phase=phase, base=base, head=head),
            task or "inputs",
        ),
        as_json=json_output,
    )
