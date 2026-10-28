"""`orqlet conventions check`: the branch name and the commit subjects of a pull request.

Read-only and offline. FAIL and NOT_RUN both exit 5, so a CI step that runs it before the
conventions are answered fails visibly instead of passing (ADR-003 decision 5). Every command and
helper of this module is private; `conventions_group` is the one name that `app.py` needs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.application.usecases.conventions_check import ConventionsRequest, check_conventions
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption
from orqlet.interface.cli.commands.validate import output_of
from orqlet.interface.cli.runner import execute
from orqlet.interface.cli.wiring import build_validate_services


def conventions_group() -> typer.Typer:
    group = typer.Typer(
        help="Check the conventions of the profile that a tool can decide.", no_args_is_help=True
    )
    group.command("check")(_check)
    return group


def _check(
    branch: Annotated[
        str | None, typer.Option(help="The branch name to check. Default: the current branch.")
    ] = None,
    base: Annotated[
        str | None,
        typer.Option(
            help="The base: a branch name or a full commit id. Default: the target branch."
        ),
    ] = None,
    head: Annotated[
        str, typer.Option(help="The head: HEAD, a branch name or a full commit id.")
    ] = "HEAD",
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """Check the branch name and the commit subjects against the profile at the base."""
    request = ConventionsRequest(branch=branch, base=base, head=head)
    execute(
        "conventions check",
        lambda: output_of(check_conventions(build_validate_services(root), request), "conventions"),
        as_json=json_output,
    )
