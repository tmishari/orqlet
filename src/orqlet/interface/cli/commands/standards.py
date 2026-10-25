"""`orqlet standards ...`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.adapters.standards.pack_source import DirectoryPackSource
from orqlet.application.contracts.cli_result import FindingOut
from orqlet.application.usecases.standards_for import (
    StandardsAnswer,
    StandardsQuery,
    standards_for,
)
from orqlet.domain.paths import CanonicalPath
from orqlet.interface.cli.render_human import render_standards
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_services

standards_app = typer.Typer(help="Read the standards that apply here.", no_args_is_help=True)


@standards_app.command("for")
def standards_for_command(
    path: Annotated[
        str | None, typer.Option(help="A file or folder, relative to the root.")
    ] = None,
    role: Annotated[str | None, typer.Option(help="A role, for example architect.")] = None,
    phase: Annotated[str | None, typer.Option(help="A phase, for example design.")] = None,
    root: Annotated[
        Path, typer.Option(exists=True, file_okay=False, help="The project root.")
    ] = Path(),
    packs_dir: Annotated[
        Path | None,
        typer.Option(exists=True, file_okay=False, help="A folder that holds standards packs."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print the JSON envelope.")] = False,
) -> None:
    """Print the rules that apply to a path, a role or a phase."""

    def action() -> CommandOutput:
        services = build_services(root)
        packs = (
            DirectoryPackSource(LocalFileSystem(packs_dir), services.loader, label="packs-dir")
            if packs_dir is not None
            else None
        )
        query = StandardsQuery(
            path=str(CanonicalPath.parse(path)) if path else None, role=role, phase=phase
        )
        answer = standards_for(
            services.project,
            services.loader,
            services.scanners,
            packs,
            query,
            services.technology_scanners,
        )
        findings = (
            ()
            if answer.language
            else (
                FindingOut(
                    code="ORQ-I001",
                    message="No scanner applies to this project; packs that name a language "
                    "were skipped.",
                    severity="info",
                ),
            )
        )
        return CommandOutput(
            data=_data(answer, query),
            human=render_standards(answer),
            findings=findings,
            not_run=answer.not_run,
        )

    execute("standards for", action, as_json=json_output)


def _data(answer: StandardsAnswer, query: StandardsQuery) -> dict[str, object]:
    return {
        "query": {"path": query.path, "role": query.role, "phase": query.phase},
        "applicable_rules_hash": answer.rules_hash,
        "rules": [
            {
                "id": rule.id,
                "level": rule.level.name,
                "waiver": rule.waiver.name.lower(),
                "enforcement": rule.enforcement.name.lower(),
                "paths": sorted(rule.scope.paths),
                "roles": sorted(rule.scope.roles),
                "phases": sorted(rule.scope.phases),
                "text": rule.text,
                "source": rule.source,
            }
            for rule in answer.rules
        ],
        "technologies": [
            {"kind": t.kind, "name": t.name, "version": t.version, "scope": t.scope}
            for t in answer.technologies
        ],
        "packs": [{"id": p.id, "version": p.version, "sha256": p.sha256} for p in answer.packs],
        "skipped": [{"id": pack_id, "reason": reason} for pack_id, reason in answer.skipped],
    }
