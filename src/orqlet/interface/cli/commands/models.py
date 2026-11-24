"""`orqlet models resolve`: the model that the model policy gives a role, a skill or a profile.

The command changes nothing and makes no git call: it reads `.orqlet/model-policy.yaml` (and the
lock, when the file is missing) and prints the answer. Every usage rule is checked here, before the
use case runs and before any file is read, and a breach exits 2 with a fixed sentence that names
the option and never repeats its value.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, get_args

import typer
from pydantic import TypeAdapter, ValidationError

from orqlet.application.contracts.common import ClientId, ModelRef, RecordedModel, Slug
from orqlet.application.contracts.model_policy import ProfileId
from orqlet.application.usecases.models_resolve import (
    ModelsQuery,
    ModelsResult,
    ModelsStatus,
    TargetKind,
    models_resolve,
)
from orqlet.interface.cli.commands.lifecycle import JsonOption, RootOption, findings_out
from orqlet.interface.cli.exit_codes import ExitCode
from orqlet.interface.cli.runner import CommandOutput, execute
from orqlet.interface.cli.wiring import build_models_services

models_app = typer.Typer(
    help="Show what the model policy says about a model; nothing is changed.", no_args_is_help=True
)

_SLUG = TypeAdapter(Slug)
_MODEL_REF = TypeAdapter(ModelRef)
_RECORDED_MODEL = TypeAdapter(RecordedModel)

_NAME_RULE = "must be a lower-case name of letters, digits and single hyphens, at most 64 long."
_MODEL_RULE = "must be a catalog id of letters, digits and . _ : / @ + -, at most 128 long."
_OVERRIDE_RULE = (
    "must be a model string of letters, digits, spaces and . _ : / @ + - [ ] = , at most 128 long."
)
_PROFILE_RULE = "must be quality, engineering or economy."
_CLIENT_RULE = "must be claude-code, codex or cursor."
_TARGET_RULE = "give exactly one of --role, --skill and --profile."

_EXIT_OF_STATUS: dict[ModelsStatus, ExitCode] = {
    "selected": ExitCode.OK,
    "automatic": ExitCode.OK,
    "none-qualifies": ExitCode.PROBLEMS,
    "refused": ExitCode.REFUSED,
}
_REFUSED_TEXT = "refused: no selection is shown, because the model policy cannot be used."


@models_app.command("resolve")
def resolve_command(
    client: Annotated[str, typer.Option(help="The client: claude-code, codex or cursor.")],
    role: Annotated[str | None, typer.Option(help="A role name.")] = None,
    skill: Annotated[str | None, typer.Option(help="A skill name.")] = None,
    profile: Annotated[
        str | None, typer.Option(help="A profile: quality, engineering or economy.")
    ] = None,
    task: Annotated[
        str | None, typer.Option(help="A task name, for an assignment that names a task.")
    ] = None,
    override: Annotated[
        str | None, typer.Option(help="A model string that the person asked for.")
    ] = None,
    different_family_from: Annotated[
        str | None, typer.Option(help="A catalog id: the answer must be of another family.")
    ] = None,
    coder_profile: Annotated[
        str | None, typer.Option(help="The profile of the coder: the answer may not be below it.")
    ] = None,
    root: RootOption = Path(),
    json_output: JsonOption = False,
) -> None:
    """The model for a role, a skill or a profile, and where the answer comes from."""
    kind, name = _check_usage(
        client=client,
        targets=(("role", role), ("skill", skill), ("profile", profile)),
        task=task,
        override=override,
        different_family_from=different_family_from,
        coder_profile=coder_profile,
    )
    query = ModelsQuery(
        client=client,
        kind=kind,
        name=name,
        task=task,
        override=override,
        different_family_from=different_family_from,
        coder_profile=coder_profile,
    )
    execute(
        "models resolve",
        lambda: _output(models_resolve(build_models_services(root), query)),
        as_json=json_output,
    )


# --- the usage checks -----------------------------------------------------------------------


def _check_usage(
    *,
    client: str,
    targets: tuple[tuple[TargetKind, str | None], ...],
    task: str | None,
    override: str | None,
    different_family_from: str | None,
    coder_profile: str | None,
) -> tuple[TargetKind, str]:
    """Raise `BadParameter` (exit 2) for the first breach; the value is never in the message."""
    if client not in get_args(ClientId):
        raise _breach("client", _CLIENT_RULE)
    given = [(kind, value) for kind, value in targets if value is not None]
    if len(given) != 1:
        raise typer.BadParameter(_TARGET_RULE)
    kind, name = given[0]
    if kind == "profile":
        _require_profile("profile", name)
    else:
        _require(_SLUG, kind, name, _NAME_RULE)
    if task is not None:
        _require(_SLUG, "task", task, _NAME_RULE)
    if override is not None:
        _require(_RECORDED_MODEL, "override", override, _OVERRIDE_RULE)
    if different_family_from is not None:
        _require(_MODEL_REF, "different-family-from", different_family_from, _MODEL_RULE)
    if coder_profile is not None:
        _require_profile("coder-profile", coder_profile)
    return kind, name


def _require(adapter: TypeAdapter[str], option: str, value: str, rule: str) -> None:
    try:
        adapter.validate_python(value, strict=True)
    except ValidationError:
        raise _breach(option, rule) from None


def _require_profile(option: str, value: str) -> None:
    if value not in get_args(ProfileId):
        raise _breach(option, _PROFILE_RULE)


def _breach(option: str, rule: str) -> typer.BadParameter:
    return typer.BadParameter(rule, param_hint=f"'--{option}'")


# --- the output -----------------------------------------------------------------------------


def _output(result: ModelsResult) -> CommandOutput:
    if result.status == "refused":
        return CommandOutput(
            data={},
            human=_REFUSED_TEXT,
            findings=findings_out(result.findings),
            exit_code=ExitCode.REFUSED,
        )
    return CommandOutput(
        data=result.data, human=_text(result.data), exit_code=_EXIT_OF_STATUS[result.status]
    )


def _text(data: Mapping[str, Any]) -> str:
    """One opening sentence, then a `label: value` line for each field that holds a value.

    Rejected models and the hint stay in `--json`: a person needs the suggestion, not the reasons.
    """
    fields = (
        ("target", _target_line(data)),
        ("policy", data["policy"]),
        ("profile", _profile_line(data)),
        ("source", data["source"]),
        ("selected", _route(data["selection"]) if data["selection"] is not None else ""),
        ("candidates", _choices_line(data["candidates"])),
        ("fallbacks", _choices_line(data["fallbacks"])),
        ("escalation", data["escalation"]),
    )
    return "\n".join([_opening(data), *(f"{label}: {value}" for label, value in fields if value)])


def _opening(data: Mapping[str, Any]) -> str:
    profile = (
        f"Suggested profile: {data['profile']}" if data["profile"] else "No profile is suggested"
    )
    model = "a model is suggested" if data["selection"] is not None else "no model is suggested"
    return f"{profile}; {model}; the client keeps the choice and nothing here changes the model."


def _target_line(data: Mapping[str, Any]) -> str:
    target = data["target"]
    line = f"{target['kind']} {target['name']} for {data['client']}"
    return line if data["task"] is None else f"{line}, task {data['task']}"


def _profile_line(data: Mapping[str, Any]) -> str:
    if data["profile"] is None:
        return ""
    return f"{data['profile']}, mode {data['mode']}" if data["mode"] else str(data["profile"])


def _route(choice: Mapping[str, Any]) -> str:
    effort = choice["effort"] or "no effort"
    return f"{choice['name']} ({choice['kind']} route, {effort}), catalog id {choice['model']}"


def _choices_line(choices: list[Mapping[str, Any]]) -> str:
    return "; ".join(_route(choice) for choice in choices)
