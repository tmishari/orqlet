"""`orqlet validate as-is|design|plan|ledger`: check an artifact an agent wrote."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.application.usecases.validate_as_is import AsIsOptions, validate_as_is
from orqlet.application.usecases.validate_design import validate_design
from orqlet.application.usecases.validate_ledger import validate_ledger
from orqlet.application.usecases.validate_plan import validate_plan
from orqlet.application.usecases.validate_records import (
    RecordOptions,
    validate_knowledge,
    validate_review,
    validate_test,
)
from orqlet.application.usecases.validation import ValidationResult
from orqlet.domain.findings import Verdict
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption, findings_out
from orqlet.interface.cli.exit_codes import ExitCode
from orqlet.interface.cli.render_human import render_validation
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_validate_services

validate_app = typer.Typer(help="Check an artifact that an agent wrote.", no_args_is_help=True)

FileArgument = Annotated[str, typer.Argument(help="The file, relative to the root.")]
LedgerOption = Annotated[
    str | None,
    typer.Option(help="The question ledger. Default: questions.yaml in the task folder."),
]


def output_of(result: ValidationResult, subject: str) -> CommandOutput:
    """PASS exits 0. FAIL and NOT_RUN both exit 5: not run is never success."""
    return CommandOutput(
        data={"verdict": result.verdict.value, **result.data},
        human=render_validation(result, subject=subject),
        findings=findings_out(result.findings),
        not_run=result.not_run,
        exit_code=ExitCode.OK if result.verdict is Verdict.PASS else ExitCode.CHECK_FAILED,
        echo_findings=False,
    )


@validate_app.command("as-is")
def as_is_command(
    file: FileArgument,
    against: Annotated[
        str | None, typer.Option(help="A revision (HEAD or a full id) to compare the scope with.")
    ] = None,
    fragments: Annotated[
        str | None, typer.Option(help="A folder of researcher fragments to compare with.")
    ] = None,
    ledger: LedgerOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """Facts only, evidence that resolves, unknowns and contradictions kept."""
    execute(
        "validate as-is",
        lambda: output_of(
            validate_as_is(
                build_validate_services(root), file, AsIsOptions(against, fragments, ledger)
            ),
            file,
        ),
        as_json=json_output,
    )


@validate_app.command("design")
def design_command(
    file: FileArgument,
    ledger: LedgerOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """The design set at the depth of its change class."""
    execute(
        "validate design",
        lambda: output_of(validate_design(build_validate_services(root), file, ledger), file),
        as_json=json_output,
    )


@validate_app.command("plan")
def plan_command(
    file: FileArgument,
    ledger: LedgerOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """The implementation plan on a projected tree."""
    execute(
        "validate plan",
        lambda: output_of(validate_plan(build_validate_services(root), file, ledger), file),
        as_json=json_output,
    )


@validate_app.command("ledger")
def ledger_command(
    file: FileArgument,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """The question ledger: one entry per question, answers kept."""
    execute(
        "validate ledger",
        lambda: output_of(validate_ledger(build_validate_services(root), file), file),
        as_json=json_output,
    )


BaseOption = Annotated[
    str | None,
    typer.Option(help="The base: a branch name or a full commit id. Default: the target branch."),
]
HeadOption = Annotated[
    str | None,
    typer.Option(help="The tree under review: `staged`, `HEAD` or a full commit id."),
]


@validate_app.command("review")
def review_command(
    file: FileArgument,
    base: BaseOption = None,
    head: HeadOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """One review round: its path, its binding to the inputs, its independence."""
    execute(
        "validate review",
        lambda: output_of(
            validate_review(build_validate_services(root), file, RecordOptions(base, head)), file
        ),
        as_json=json_output,
    )


@validate_app.command("test")
def record_of_tests_command(
    file: FileArgument,
    base: BaseOption = None,
    head: HeadOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """The tester's record: commands that ran, criteria covered, bound to the inputs."""
    execute(
        "validate test",
        lambda: output_of(
            validate_test(build_validate_services(root), file, RecordOptions(base, head)), file
        ),
        as_json=json_output,
    )


@validate_app.command("knowledge")
def knowledge_command(
    file: FileArgument,
    base: BaseOption = None,
    head: HeadOption = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """The knowledge-impact record: every candidate resolved, evidence that resolves."""
    execute(
        "validate knowledge",
        lambda: output_of(
            validate_knowledge(build_validate_services(root), file, RecordOptions(base, head)),
            file,
        ),
        as_json=json_output,
    )
