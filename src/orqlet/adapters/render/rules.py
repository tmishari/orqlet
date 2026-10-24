"""Path-scoped rule files for the clients that read them (proposal section 12.4)."""

from __future__ import annotations

import re

from orqlet.adapters.render.emit import front_matter, normalise_text
from orqlet.adapters.render.instructions import GENERATED_NOTICE
from orqlet.application.ports.instruction_adapter import ClientCommand, RenderedFile, ScopedRule
from orqlet.domain.digest import sha256_hex
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath

_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")


def _checked_name(rule: ScopedRule) -> str:
    if _NAME.fullmatch(rule.name) is None:
        raise ValueError(
            f"a rule file name is lower case letters, digits and hyphens: {rule.name!r}"
        )
    if not rule.paths:
        raise ValueError(f"rule {rule.name!r} has no paths; it would load for every task")
    return f"orqlet-{rule.name}"


def _body(rule: ScopedRule) -> str:
    return f"{GENERATED_NOTICE}\n\n{normalise_text(rule.body)}"


def claude_rule(rule: ScopedRule) -> RenderedFile:
    """`.claude/rules/orqlet-<name>.md` with a `paths` list."""
    stem = _checked_name(rule)
    text = front_matter([("paths", list(rule.paths))]) + _body(rule)
    return _file(f".claude/rules/{stem}.md", text, rule)


def cursor_rule(rule: ScopedRule) -> RenderedFile:
    """`.cursor/rules/orqlet-<name>.mdc` attached by `globs`, never always on."""
    stem = _checked_name(rule)
    text = front_matter(
        [("description", rule.description), ("globs", list(rule.paths)), ("alwaysApply", False)]
    ) + _body(rule)
    return _file(f".cursor/rules/{stem}.mdc", text, rule)


def _file(path: str, text: str, rule: ScopedRule) -> RenderedFile:
    data = text.encode("utf-8")
    return RenderedFile(
        path=CanonicalPath.parse(path),
        content=data,
        owner=OwnerMode.ORQLET,
        file_class=rule.file_class,
        inputs=rule.inputs or ((rule.name, "1", sha256_hex(data)),),
    )


def claude_command(command: ClientCommand) -> RenderedFile:
    """`.claude/commands/orqlet-<name>.md`, listed by Claude Code as `/orqlet-<name>`."""
    text = front_matter([("description", command.description)], plain_when_safe=True)
    text += _command_body(command)
    return _command_file(f".claude/commands/orqlet-{_command_name(command)}.md", text, command)


def cursor_command(command: ClientCommand) -> RenderedFile:
    """`.cursor/commands/orqlet-<name>.md`: plain Markdown without front matter."""
    return _command_file(
        f".cursor/commands/orqlet-{_command_name(command)}.md", _command_body(command), command
    )


def _command_name(command: ClientCommand) -> str:
    if _NAME.fullmatch(command.name) is None:
        raise ValueError(
            f"a command file name is lower case letters, digits and hyphens: {command.name!r}"
        )
    return command.name


def _command_body(command: ClientCommand) -> str:
    return f"{GENERATED_NOTICE}\n\n{normalise_text(command.body)}"


def _command_file(path: str, text: str, command: ClientCommand) -> RenderedFile:
    data = text.encode("utf-8")
    return RenderedFile(
        path=CanonicalPath.parse(path),
        content=data,
        owner=OwnerMode.ORQLET,
        file_class=FileClass.GENERATED,
        inputs=command.inputs or ((command.name, "1", sha256_hex(data)),),
    )
