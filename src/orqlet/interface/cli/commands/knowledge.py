"""`orqlet knowledge impact`: what a phase may have made stale, found without a model."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.application.usecases.knowledge_impact import knowledge_impact
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption
from orqlet.interface.cli.commands.validate import BaseOption, HeadOption, output_of
from orqlet.interface.cli.runner import execute
from orqlet.interface.cli.wiring import build_validate_services

knowledge_app = typer.Typer(help="Knowledge that travels with the code.", no_args_is_help=True)


@knowledge_app.command("impact")
def impact_command(
    task: Annotated[str, typer.Argument(help="The task folder name under docs/design.")],
    phase: Annotated[str, typer.Argument(help="The phase, for example P-1.")],
    base: BaseOption = None,
    head: HeadOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """List the candidates of the phase and print the binding its record must carry.

    The analysis reads the committed tree only. It calls no model and uses no network.
    """
    execute(
        "knowledge impact",
        lambda: output_of(
            knowledge_impact(build_validate_services(root), task, phase, base, head),
            f"{task} {phase}",
        ),
        as_json=json_output,
    )
