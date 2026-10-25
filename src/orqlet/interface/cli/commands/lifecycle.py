"""`upgrade`, `rollback`, `sync`, `doctor`, `explain` and `release`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.adapters.scan.personal_names import FsPersonalNames
from orqlet.application.contracts.cli_result import FindingOut
from orqlet.application.usecases.diagnose import Diagnosis, doctor, sync
from orqlet.application.usecases.explain import Explanation, explain
from orqlet.application.usecases.release import ReleaseOptions, release_file
from orqlet.application.usecases.rollback import RollbackOptions, rollback
from orqlet.application.usecases.standards_for import StandardsQuery
from orqlet.application.usecases.upgrade import UpgradeOptions, UpgradeResult, upgrade
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.paths import CanonicalPath
from orqlet.interface.cli.exit_codes import ExitCode
from orqlet.interface.cli.render_human import (
    render_diagnosis,
    render_explanation,
    render_release,
    render_rollback,
    render_upgrade,
)
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_init_services

RootOption = Annotated[Path, typer.Option(exists=True, file_okay=False, help="The project root.")]
PacksOption = Annotated[
    Path | None,
    typer.Option(exists=True, file_okay=False, help="A folder that holds standards packs."),
]
JsonOption = Annotated[bool, typer.Option("--json", help="Print the JSON envelope.")]
YesOption = Annotated[bool, typer.Option("--yes", help="Apply without asking.")]


def findings_out(findings: tuple[Finding, ...] | list[Finding]) -> tuple[FindingOut, ...]:
    return tuple(
        FindingOut(code=f.code, message=f.message, severity=f.severity.value, path=f.path)
        for f in findings
    )


def plan_data(plan: object) -> dict[str, object]:
    writes = getattr(plan, "writes", ()) if plan is not None else ()
    return {"writes": [{"path": str(w.path), "kind": w.kind} for w in writes]}


def _check_exit(findings: tuple[Finding, ...]) -> ExitCode:
    severities = {f.severity for f in findings}
    if Severity.ERROR in severities:
        return ExitCode.CHECK_FAILED
    return ExitCode.PROBLEMS if Severity.WARNING in severities else ExitCode.OK


# --- upgrade -------------------------------------------------------------------------------------
def upgrade_command(
    root: RootOption = Path(),
    check: Annotated[
        bool, typer.Option("--check", help="Only report whether an upgrade exists.")
    ] = False,
    resume: Annotated[
        bool, typer.Option("--resume", help="Finish a change that was interrupted.")
    ] = False,
    allow_weaker: Annotated[
        bool, typer.Option("--allow-weaker", help="Allow a downgrade. It needs two approvals.")
    ] = False,
    packs_dir: PacksOption = None,
    yes: YesOption = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show the plan; write nothing.")
    ] = False,
    json_output: JsonOption = False,
) -> None:
    """Re-render the setup from this release, without overwriting the team's edits."""

    def action() -> CommandOutput:
        services = build_init_services(root, packs_dir)
        result = upgrade(
            services,
            UpgradeOptions(
                check=check,
                resume=resume,
                assume_yes=yes,
                dry_run=dry_run,
                allow_weaker=allow_weaker,
            ),
        )
        return CommandOutput(
            data={
                "status": result.status,
                "change_id": result.change_id,
                "installed_workflow": _version(result.installed),
                "candidate_workflow": _version(result.candidate),
                "resumed": list(result.resumed),
                **plan_data(result.plan),
            },
            human=render_upgrade(result),
            findings=findings_out(result.findings),
            exit_code=_upgrade_exit(result),
        )

    execute("upgrade", action, as_json=json_output)


def _version(release: object) -> str | None:
    return None if release is None else str(release.version)  # type: ignore[attr-defined]


def _upgrade_exit(result: UpgradeResult) -> ExitCode:
    if result.status == "refused":
        return ExitCode.REFUSED
    if result.status == "needs-input":
        return ExitCode.NEEDS_INPUT
    if result.status == "available" or any(f.code == "ORQ-W080" for f in result.findings):
        return ExitCode.PROBLEMS
    return ExitCode.OK


# --- rollback ------------------------------------------------------------------------------------
def rollback_command(
    change_id: Annotated[
        str, typer.Argument(help="The change to undo, as printed by init or upgrade.")
    ],
    root: RootOption = Path(),
    allow_weaker: Annotated[
        bool, typer.Option("--allow-weaker", help="Allow a rollback that lowers the workflow.")
    ] = False,
    project_id: Annotated[
        str | None, typer.Option(help="The project id, when the profile is gone.")
    ] = None,
    yes: YesOption = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show the plan; write nothing.")
    ] = False,
    json_output: JsonOption = False,
) -> None:
    """Restore the files of one change, if nothing has touched them since."""

    def action() -> CommandOutput:
        services = build_init_services(root, None)
        result = rollback(
            services,
            RollbackOptions(
                change_id=change_id,
                assume_yes=yes,
                dry_run=dry_run,
                allow_weaker=allow_weaker,
                project_id=project_id,
            ),
        )
        return CommandOutput(
            data={
                "status": result.status,
                "change_id": result.change_id,
                **plan_data(result.plan),
            },
            human=render_rollback(result),
            findings=findings_out(result.findings),
            exit_code=simple_exit(result.status),
        )

    execute("rollback", action, as_json=json_output)


def simple_exit(status: str) -> ExitCode:
    return {"refused": ExitCode.REFUSED, "needs-input": ExitCode.NEEDS_INPUT}.get(
        status, ExitCode.OK
    )


# --- sync and doctor -----------------------------------------------------------------------------
def sync_command(
    root: RootOption = Path(),
    check_personal_names: Annotated[
        bool,
        typer.Option(
            "--check-personal-names",
            help="List personal skill and agent names and compare them with reserved names.",
        ),
    ] = False,
    json_output: JsonOption = False,
) -> None:
    """Check this checkout against the manifest. Writes nothing."""
    _diagnose_command("sync", sync, root, check_personal_names, json_output)


def doctor_command(
    root: RootOption = Path(),
    check_personal_names: Annotated[
        bool,
        typer.Option(
            "--check-personal-names",
            help="List personal skill and agent names and compare them with reserved names.",
        ),
    ] = False,
    json_output: JsonOption = False,
) -> None:
    """Report what is missing, edited, stale or unknown. Writes nothing."""
    _diagnose_command("doctor", doctor, root, check_personal_names, json_output)


def _diagnose_command(name, run, root, personal, json_output) -> None:  # type: ignore[no-untyped-def]
    def action() -> CommandOutput:
        services = build_init_services(root, None)
        lister = FsPersonalNames(Path.home()) if personal else None
        diagnosis: Diagnosis = run(services, personal=lister)
        return CommandOutput(
            data={
                "drift": [
                    {"path": d.path, "block": d.block, "state": d.state} for d in diagnosis.drift
                ],
                "listed_personal_names": [
                    {"location": location, "name": item}
                    for location, item in diagnosis.listed_names
                ],
            },
            human=render_diagnosis(diagnosis),
            findings=findings_out(diagnosis.findings),
            not_run=diagnosis.not_run,
            exit_code=_check_exit(diagnosis.findings),
            echo_findings=False,
        )

    execute(name, action, as_json=json_output)


# --- explain -------------------------------------------------------------------------------------
def explain_command(
    root: RootOption = Path(),
    path: Annotated[
        str | None, typer.Option(help="A file or folder, relative to the root.")
    ] = None,
    role: Annotated[str | None, typer.Option(help="A role, for example architect.")] = None,
    phase: Annotated[str | None, typer.Option(help="A phase, for example design.")] = None,
    packs_dir: PacksOption = None,
    json_output: JsonOption = False,
) -> None:
    """Show what is declared, what is generated and what Orqlet cannot see."""

    def action() -> CommandOutput:
        services = build_init_services(root, packs_dir)
        query = StandardsQuery(
            path=str(CanonicalPath.parse(path)) if path else None, role=role, phase=phase
        )
        explanation: Explanation = explain(services, query)
        return CommandOutput(
            data={
                "declared": explanation.declared,
                "generated": [
                    {"path": d.path, "block": d.block, "owner": d.owner.value, "state": d.state}
                    for d in explanation.generated
                ],
                "rules": [
                    {"id": r.id, "level": r.level.name, "source": r.source, "text": r.text}
                    for r in explanation.rules
                ],
                "cannot_be_inspected": list(explanation.uninspectable),
            },
            human=render_explanation(explanation),
            findings=findings_out(explanation.limits),
            not_run=explanation.not_run,
        )

    execute("explain", action, as_json=json_output)


# --- release -------------------------------------------------------------------------------------
def release_command(
    path: Annotated[str, typer.Argument(help="The generated file to hand over to the team.")],
    reason: Annotated[str, typer.Option(help="Why. It is written to the divergence record.")],
    root: RootOption = Path(),
    yes: YesOption = False,
    json_output: JsonOption = False,
) -> None:
    """Take a file out of the manifest. Protected files cannot be released."""

    def action() -> CommandOutput:
        services = build_init_services(root, None)
        result = release_file(services, ReleaseOptions(path=path, reason=reason, assume_yes=yes))
        return CommandOutput(
            data={
                "status": result.status,
                "change_id": result.change_id,
                **plan_data(result.plan),
            },
            human=render_release(result),
            findings=findings_out(result.findings),
            exit_code=simple_exit(result.status),
        )

    execute("release", action, as_json=json_output)
