"""`orqlet review prepare`: the read-only packet for the independent reviewers."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from orqlet.adapters.system import UuidGenerator
from orqlet.application.usecases.review_prepare import review_prepare
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption
from orqlet.interface.cli.commands.validate import BaseOption, HeadOption, output_of
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_packet_store, build_validate_services

review_app = typer.Typer(help="Independent review of a staged change.", no_args_is_help=True)


@review_app.command("prepare")
def prepare_command(
    task: Annotated[str, typer.Argument(help="The task folder name under docs/design.")],
    phase: Annotated[str, typer.Argument(help="The phase, for example P-1.")],
    base: BaseOption = None,
    head: HeadOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """Export the staged snapshot, the diff, the plan and the records outside the repository."""

    def action() -> CommandOutput:
        packets, folder = build_packet_store()
        result = review_prepare(
            build_validate_services(root),
            packets,
            UuidGenerator().new_id(),
            task,
            phase,
            base=base,
            head=head,
        )
        output = output_of(result, f"{task} {phase}")
        if "packet" not in result.data:
            return output
        location = str(folder / str(result.data["packet"]))
        return replace(
            output,
            data={**output.data, "path": location},
            human=f"{output.human}\nPacket: {location}",
        )

    execute("review prepare", action, as_json=json_output)
