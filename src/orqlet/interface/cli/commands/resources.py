"""`orqlet resources add|update|remove|attach|list`: the registry of links to team resources.

The edit commands write `.orqlet/resources.yaml` and the lock in one journalled change, as
`profile answer` does for the profile; the files that follow from a change are written by the next
`orqlet upgrade`. Every command and helper of this module is private: `resources_group` is the one
name that `app.py` needs. Text that comes from the repository reaches the screen only through
`printable`, which `list_resources` applies to every row.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from orqlet.application.usecases.resources_edit import (
    CopySpec,
    ResourcesEditResult,
    ResourceSpec,
    add_resource,
    attach_copy,
    remove_resource,
    update_resource,
)
from orqlet.application.usecases.resources_view import ResourcesListing, list_resources
from orqlet.application.usecases.services import Services
from orqlet.domain.findings import Severity
from orqlet.interface.cli.commands.lifecycle import (
    JsonOption,
    RootOption,
    YesOption,
    findings_out,
    plan_data,
    simple_exit,
)
from orqlet.interface.cli.exit_codes import ExitCode
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_init_services, build_validate_services

_DryRunOption = Annotated[bool, typer.Option("--dry-run", help="Show the change; write nothing.")]
_PathOption = Annotated[
    list[str] | None,
    typer.Option("--path", help="A glob of repository paths the link applies to. Repeat it."),
]
_Id = Annotated[str, typer.Argument(help="The id of the entry; it never changes.")]
_NEXT_STEP = "Next step: run `orqlet upgrade` to write the files that follow from this change."


def resources_group() -> typer.Typer:
    group = typer.Typer(
        help="Register links to team resources: API guidelines, tool documentation, pages.",
        no_args_is_help=True,
    )
    group.command("add")(_add)
    group.command("update")(_update)
    group.command("remove")(_remove)
    group.command("attach")(_attach)
    group.command("list")(_list)
    return group


def _add(
    url: Annotated[str, typer.Argument(help="The address of the page. https only.")],
    resource_id: Annotated[str, typer.Option("--id", help="A short id: lower case, digits, -.")],
    title: Annotated[str, typer.Option(help="One line, up to 80 characters.")],
    kind: Annotated[str, typer.Option(help="api-guidelines, tool-docs, team-docs or other.")],
    note: Annotated[str, typer.Option(help="Why and when to use it. One line, up to 200.")],
    access: Annotated[str, typer.Option(help="public or login.")] = "public",
    path: _PathOption = None,
    tool: Annotated[str | None, typer.Option(help="The tool, for a tool-docs entry.")] = None,
    version: Annotated[str | None, typer.Option(help="The version of the tool.")] = None,
    root: RootOption = Path(),
    yes: YesOption = False,
    dry_run: _DryRunOption = False,
    json_output: JsonOption = False,
) -> None:
    """Add a link. Nothing is rendered until `orqlet upgrade`."""
    spec = ResourceSpec(
        id=resource_id,
        url=url,
        title=title,
        kind=kind,
        note=note,
        access=access,
        paths=tuple(path or ()),
        tool=tool,
        version=version,
    )
    _run("resources add", json_output, lambda: add_resource(_services(root), spec, yes, dry_run))


def _update(
    resource_id: _Id,
    url: Annotated[str | None, typer.Option(help="A new address.")] = None,
    title: Annotated[str | None, typer.Option(help="A new title.")] = None,
    kind: Annotated[str | None, typer.Option(help="A new kind.")] = None,
    note: Annotated[str | None, typer.Option(help="A new note.")] = None,
    access: Annotated[str | None, typer.Option(help="public or login.")] = None,
    path: _PathOption = None,
    tool: Annotated[str | None, typer.Option(help="A new tool.")] = None,
    version: Annotated[str | None, typer.Option(help="A new version.")] = None,
    root: RootOption = Path(),
    yes: YesOption = False,
    dry_run: _DryRunOption = False,
    json_output: JsonOption = False,
) -> None:
    """Change the fields that are given. The stored copy keeps its record."""
    spec = ResourceSpec(
        id=resource_id,
        url=url,
        title=title,
        kind=kind,
        note=note,
        access=access,
        paths=None if path is None else tuple(path),
        tool=tool,
        version=version,
    )
    _run(
        "resources update",
        json_output,
        lambda: update_resource(_services(root), spec, yes, dry_run),
    )


def _remove(
    resource_id: _Id,
    root: RootOption = Path(),
    yes: YesOption = False,
    dry_run: _DryRunOption = False,
    json_output: JsonOption = False,
) -> None:
    """Remove a link. A stored copy stays; you delete it."""
    _run(
        "resources remove",
        json_output,
        lambda: remove_resource(_services(root), resource_id, yes, dry_run),
    )


def _attach(
    resource_id: _Id,
    form: Annotated[str, typer.Option(help="copy or summary. A login entry stores a summary.")],
    ttl_days: Annotated[
        int, typer.Option(help="Days after which the copy is advised to be read again.")
    ],
    root: RootOption = Path(),
    yes: YesOption = False,
    dry_run: _DryRunOption = False,
    json_output: JsonOption = False,
) -> None:
    """Record the copy at docs/resources/<id>.md: its form, SHA-256, time and time-to-live."""
    spec = CopySpec(id=resource_id, form=form, ttl_days=ttl_days)
    _run("resources attach", json_output, lambda: attach_copy(_services(root), spec, yes, dry_run))


def _list(
    uncovered: Annotated[
        bool, typer.Option("--uncovered", help="Show the technologies that no entry names.")
    ] = False,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """Show the registry, one line for each entry. The address is shown as a host."""

    def action() -> CommandOutput:
        listing = list_resources(build_validate_services(root), uncovered)
        failed = any(finding.severity is Severity.ERROR for finding in listing.findings)
        return CommandOutput(
            data={"resources": list(listing.resources), "uncovered": list(listing.uncovered)},
            human=_listing_text(listing, uncovered),
            findings=findings_out(listing.findings),
            exit_code=ExitCode.CHECK_FAILED if failed else ExitCode.OK,
        )

    execute("resources list", action, as_json=json_output)


# --- helpers ------------------------------------------------------------------------------------
def _services(root: Path) -> Services:
    return build_init_services(root, None)


def _run(name: str, json_output: bool, change: Callable[[], ResourcesEditResult]) -> None:
    def action() -> CommandOutput:
        result = change()
        return CommandOutput(
            data={
                "status": result.status,
                "change_id": result.change_id,
                **plan_data(result.plan),
                "notes": list(result.notes),
            },
            human=_edit_text(result),
            findings=findings_out(result.findings),
            exit_code=simple_exit(result.status),
        )

    execute(name, action, as_json=json_output)


def _edit_text(result: ResourcesEditResult) -> str:
    headline = {
        "applied": "The registry of links was changed.",
        "previewed": "Preview only. Nothing was written.",
        "needs-input": "Nothing was written: an approval is missing.",
        "refused": "Refused. Nothing was written.",
    }[result.status]
    lines = [headline]
    if result.plan is not None:
        lines += ["", *(f"  {write.kind:<7} {write.path}" for write in result.plan.writes)]
    if result.notes:
        lines += ["", *result.notes]
    if result.status == "applied":
        lines += ["", f"Change {result.change_id}. Undo it with `orqlet rollback`.", _NEXT_STEP]
    return "\n".join(lines)


def _listing_text(listing: ResourcesListing, uncovered: bool) -> str:
    lines = [
        f"{row['id']}  {row['kind']}  {row['access']}  {row['host']}  {row['title']}"
        for row in listing.resources
    ]
    if not lines and not listing.findings:
        lines = ["No links are registered. Add one with `orqlet resources add`."]
    if uncovered:
        lines += ["", "Technologies that no entry names as its tool:"]
        lines += [f"  {name}" for name in listing.uncovered] or ["  (none)"]
    return "\n".join(lines)
