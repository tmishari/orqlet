"""The `orqlet` command line. Subcommand groups are added with an explicit name."""

from __future__ import annotations

from typing import Annotated

import typer

from orqlet import __version__
from orqlet.interface.cli.commands.evidence import evidence_app
from orqlet.interface.cli.commands.gate import gate_app
from orqlet.interface.cli.commands.init import init_command
from orqlet.interface.cli.commands.knowledge import knowledge_app
from orqlet.interface.cli.commands.lifecycle import (
    doctor_command,
    explain_command,
    release_command,
    rollback_command,
    sync_command,
    upgrade_command,
)
from orqlet.interface.cli.commands.profile import profile_app
from orqlet.interface.cli.commands.review import review_app
from orqlet.interface.cli.commands.standards import standards_app
from orqlet.interface.cli.commands.validate import validate_app

app = typer.Typer(
    name="orqlet",
    help="Keep the AI context of a repository (skills, rules, standards) in order.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
app.command("init")(init_command)
app.command("upgrade")(upgrade_command)
app.command("rollback")(rollback_command)
app.command("sync")(sync_command)
app.command("doctor")(doctor_command)
app.command("explain")(explain_command)
app.command("release")(release_command)
app.add_typer(profile_app, name="profile")
app.add_typer(standards_app, name="standards")
app.add_typer(validate_app, name="validate")
app.add_typer(gate_app, name="gate")
app.add_typer(evidence_app, name="evidence")
app.add_typer(knowledge_app, name="knowledge")
app.add_typer(review_app, name="review")


def _show_version(value: bool) -> None:
    if value:
        typer.echo(f"orqlet {__version__}")
        raise typer.Exit


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_show_version, is_eager=True, help="Print the version."),
    ] = False,
) -> None:
    """Orqlet reads and writes files. It never starts an agent or calls a model."""


def main() -> None:
    app()
