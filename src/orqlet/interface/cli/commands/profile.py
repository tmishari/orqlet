"""`orqlet profile answer` and `orqlet profile approve`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.application.usecases.profile_edit import (
    ProfileEditResult,
    answer_profile,
    approve_profile,
)
from orqlet.interface.cli.commands.lifecycle import (
    JsonOption,
    RootOption,
    YesOption,
    findings_out,
    plan_data,
    simple_exit,
)
from orqlet.interface.cli.render_human import render_profile_edit
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_init_services

profile_app = typer.Typer(
    help="Answer open facts and approve the project profile.", no_args_is_help=True
)
DryRunOption = Annotated[bool, typer.Option("--dry-run", help="Show the change; write nothing.")]


@profile_app.command("answer")
def answer_command(
    pairs: Annotated[
        list[str],
        typer.Argument(
            help="One or more KEY=VALUE, for example repository.branch_naming=feature/*"
        ),
    ],
    root: RootOption = Path(),
    yes: YesOption = False,
    dry_run: DryRunOption = False,
    json_output: JsonOption = False,
) -> None:
    """Record answers for facts that were left unknown. Changing a fact withdraws approval."""

    def action() -> CommandOutput:
        answers = _parse(pairs)
        result = answer_profile(
            build_init_services(root, None), answers, assume_yes=yes, dry_run=dry_run
        )
        return _output(result)

    execute("profile answer", action, as_json=json_output)


@profile_app.command("approve")
def approve_command(
    reviewer: Annotated[str, typer.Option(help="Your name, recorded as the reviewer.")],
    root: RootOption = Path(),
    yes: YesOption = False,
    dry_run: DryRunOption = False,
    json_output: JsonOption = False,
) -> None:
    """Record that the project profile was reviewed and approved."""

    def action() -> CommandOutput:
        result = approve_profile(
            build_init_services(root, None), reviewer, assume_yes=yes, dry_run=dry_run
        )
        return _output(result)

    execute("profile approve", action, as_json=json_output)


def _parse(pairs: list[str]) -> dict[str, str]:
    answers: dict[str, str] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key:
            raise typer.BadParameter(f"expected KEY=VALUE, got {pair!r}")
        answers[key] = value
    return answers


def _output(result: ProfileEditResult) -> CommandOutput:
    return CommandOutput(
        data={"status": result.status, "change_id": result.change_id, **plan_data(result.plan)},
        human=render_profile_edit(result),
        findings=findings_out(result.findings),
        exit_code=simple_exit(result.status),
    )
