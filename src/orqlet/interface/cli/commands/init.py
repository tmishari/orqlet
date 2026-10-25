"""`orqlet init`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.application.contracts.cli_result import FindingOut
from orqlet.application.usecases.draft_profile import Client
from orqlet.application.usecases.init_project import InitOptions, InitResult, init_project
from orqlet.interface.cli.exit_codes import ExitCode
from orqlet.interface.cli.render_human import render_init
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_init_services

CLIENTS: tuple[Client, ...] = ("claude-code", "codex", "cursor")


def init_command(
    root: Annotated[
        Path, typer.Option(exists=True, file_okay=False, help="The project root.")
    ] = Path(),
    client: Annotated[
        list[str] | None, typer.Option(help="A client to set up. Repeat for several. Default: all.")
    ] = None,
    answer: Annotated[
        list[str] | None,
        typer.Option(help="An answer as KEY=VALUE, for example repository.target_branch=main."),
    ] = None,
    target_branch: Annotated[
        str | None,
        typer.Option(
            help="The branch pull requests target (also names a new repository's branch)."
        ),
    ] = None,
    git_init: Annotated[
        bool, typer.Option("--git-init", help="Create the Git repository if there is none.")
    ] = False,
    new_project: Annotated[
        bool,
        typer.Option("--new-project", help="Confirm that a non-empty directory is a new project."),
    ] = False,
    name: Annotated[
        str | None, typer.Option(help="The project name. Default: the directory name.")
    ] = None,
    prompts_dir: Annotated[
        str, typer.Option(help="Where the standards folder is seeded.")
    ] = ".prompts",
    packs_dir: Annotated[
        Path | None,
        typer.Option(exists=True, file_okay=False, help="A folder that holds standards packs."),
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", help="Apply without asking.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show the plan; write nothing.")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print the JSON envelope.")] = False,
) -> None:
    """Set up the AI context of a project: existing, new or empty."""

    def action() -> CommandOutput:
        clients = _clients(client)
        answers = _answers(answer)
        if target_branch is not None:
            answers.setdefault("repository.target_branch", target_branch)
        outside = packs_dir is not None and not _inside(packs_dir, root)
        services = build_init_services(root, packs_dir)
        options = InitOptions(
            clients=clients,
            answers=answers,
            assume_yes=yes,
            dry_run=dry_run,
            git_init=git_init,
            new_project=new_project,
            project_name=name,
            prompts_dir=prompts_dir,
            packs_path=_relative(packs_dir, root)
            if packs_dir is not None and not outside
            else None,
            packs_outside_repository=outside,
        )
        return _output(init_project(services, options))

    execute("init", action, as_json=json_output)


def _clients(requested: list[str] | None) -> tuple[Client, ...]:
    if not requested:
        return CLIENTS
    unknown = sorted(set(requested) - set(CLIENTS))
    if unknown:
        raise typer.BadParameter(f"unknown client {unknown[0]!r}; choose from {', '.join(CLIENTS)}")
    return tuple(c for c in CLIENTS if c in requested)


def _answers(pairs: list[str] | None) -> dict[str, str]:
    answers: dict[str, str] = {}
    for pair in pairs or []:
        key, separator, value = pair.partition("=")
        if not separator or not key:
            raise typer.BadParameter(f"--answer needs KEY=VALUE, got {pair!r}")
        answers[key] = value
    return answers


def _inside(directory: Path, root: Path) -> bool:
    return directory.resolve().is_relative_to(root.resolve())


def _relative(directory: Path, root: Path) -> str:
    return directory.resolve().relative_to(root.resolve()).as_posix()


def _exit_code(result: InitResult) -> ExitCode:
    has_error = any(f.severity.value == "error" for f in result.findings)
    if result.status == "needs-input":
        return ExitCode.NEEDS_INPUT
    if result.status == "refused" or has_error:
        return ExitCode.REFUSED
    if any(f.code == "ORQ-W080" for f in result.findings):
        return ExitCode.PROBLEMS
    return ExitCode.OK


def _output(result: InitResult) -> CommandOutput:
    plan = result.plan
    files = (
        []
        if plan is None
        else [
            {
                "path": str(item.path),
                "block": item.block_name,
                "owner": item.owner.value,
                "class": None if item.file_class is None else item.file_class.value,
                "state": item.state.value,
                "action": item.action.value,
            }
            for item in plan.items
        ]
    )
    data: dict[str, object] = {
        "status": result.status,
        "change_id": result.change_id,
        "git_initialised": result.git_initialised,
        "needs_git": result.needs_git,
        "plan_digest": None if plan is None else plan.digest,
        "files": files,
        "writes": []
        if plan is None
        else [{"path": str(w.path), "kind": w.kind} for w in plan.writes],
        "open_questions": [{"id": q.id, "text": q.text} for q in result.open_questions],
    }
    return CommandOutput(
        data=data,
        human=render_init(result),
        findings=tuple(
            FindingOut(code=f.code, message=f.message, severity=f.severity.value, path=f.path)
            for f in result.findings
        ),
        exit_code=_exit_code(result),
    )
