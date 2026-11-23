"""`orqlet gate status`: what an artifact was written against and whether that still holds."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import TypeAdapter, ValidationError

from orqlet.application.contracts.common import Slug
from orqlet.application.usecases.gate_status import gate_status
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption
from orqlet.interface.cli.commands.validate import BaseOption, HeadOption, output_of
from orqlet.interface.cli.render_human import gate_action_line
from orqlet.interface.cli.runner import execute
from orqlet.interface.cli.wiring import build_validate_services

gate_app = typer.Typer(help="Check what the workflow's gates would see.", no_args_is_help=True)

_TASK = TypeAdapter(Slug)
_TASK_RULE = "must be a lower-case name of letters, digits and single hyphens, at most 64 long."


def _require_task_name(task: str | None) -> None:
    """A usage error (exit 2) before anything is read; the value is never in the message."""
    if task is None:
        return
    try:
        _TASK.validate_python(task, strict=True)
    except ValidationError:
        raise typer.BadParameter(_TASK_RULE, param_hint="'TASK'") from None


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
    """Read-only and offline. It never checks approval: the input check confirms that."""
    _require_task_name(task)
    execute(
        "gate status",
        lambda: output_of(
            gate_status(build_validate_services(root), task, phase=phase, base=base, head=head),
            task or "inputs",
            closing=lambda result: gate_action_line(result, task),
        ),
        as_json=json_output,
    )
