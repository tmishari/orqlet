"""`orqlet status`: the global setup, the location and the next step. It changes nothing."""

from __future__ import annotations

from pathlib import Path

from orqlet.application.contracts.common import RENDER_CLIENT_IDS
from orqlet.application.usecases.status import StatusReport, read_status
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption
from orqlet.interface.cli.exit_codes import ExitCode
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_status_services


def status_command(root: RootOption = Path(), json_output: JsonOption = False) -> None:
    """Show the global setup, where ROOT stands and the next step. Nothing is written."""

    def action() -> CommandOutput:
        report = read_status(build_status_services(root))
        return CommandOutput(
            data=report.to_data(),
            human=_human(report),
            not_run=report.not_run,
            exit_code=ExitCode.CHECK_FAILED if report.not_run else ExitCode.OK,
        )

    execute("status", action, as_json=json_output)


def _human(report: StatusReport) -> str:
    clients = ", ".join(f"{client} {report.clients[client]}" for client in RENDER_CLIENT_IDS)
    lines = [
        f"global: {clients}",
        f"orqlet on PATH: {report.orqlet_on_path}",
        f"location: {report.location}",
        f"top level: {report.top_level or report.top_level_reason or 'none'}",
        f"versions: installed {report.installed}, project {report.project or 'none'}",
        f"next: {report.next}",
    ]
    lines += [f"host step: {step}" for step in report.host_steps]
    lines += [f"not run: {reason}" for reason in report.not_run]
    return "\n".join(lines)
