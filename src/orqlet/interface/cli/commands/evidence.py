"""`orqlet evidence cite|hash`: the exact hashes to write into an artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.application.usecases.evidence_cite import cite, file_hashes
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption
from orqlet.interface.cli.commands.validate import output_of
from orqlet.interface.cli.runner import execute
from orqlet.interface.cli.wiring import build_validate_services

evidence_app = typer.Typer(
    help="Print the hashes that an artifact must carry.", no_args_is_help=True
)


@evidence_app.command("cite")
def cite_command(
    file: Annotated[str, typer.Argument(help="The file, relative to the root.")],
    lines: Annotated[str, typer.Argument(help="The lines, as `a-b` or `a`, counted from 1.")],
    revision: Annotated[
        str | None, typer.Option(help="HEAD or a full object id. Default: HEAD.")
    ] = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """The evidence entry (path, lines, revision, sha256) for lines of a committed file."""
    execute(
        "evidence cite",
        lambda: output_of(cite(build_validate_services(root), file, lines, revision), file),
        as_json=json_output,
    )


@evidence_app.command("hash")
def hash_command(
    files: Annotated[list[str], typer.Argument(help="Files, relative to the root.")],
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """`path#sha256` of each file, as an artifact or a design reference needs it."""
    execute(
        "evidence hash",
        lambda: output_of(file_hashes(build_validate_services(root), files), ", ".join(files)),
        as_json=json_output,
    )
