"""Reading the skills and roles of the workflow package into what the adapters render.

A skill text marks a step that needs a command with `<!-- requires: <command> -->`, and a step
that only applies while a command is missing with `<!-- unless: <command> -->`. The renderer drops
the steps whose condition does not hold and renumbers the list, so a skill never tells an agent to
call a command that this release does not provide (proposal 17.10).
"""

from __future__ import annotations

import re
from collections.abc import Collection

from orqlet.application.ports.instruction_adapter import ClientRole, ClientSkill
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.domain.digest import sha256_hex
from orqlet.domain.errors import OrqletError


class SourceError(OrqletError):
    """A skill, role or command source of the package is malformed: a defect of the release."""


_MARKER = re.compile(r"\s*<!--\s*(requires|unless):\s*([a-z][a-z -]*[a-z])\s*-->\s*$")
_NUMBERED = re.compile(r"^(\d+)\.(\s)")
_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")


def parse_source(
    path: str, text: str, *, required: tuple[str, ...], optional: tuple[str, ...] = ()
) -> tuple[dict[str, str], str]:
    """The front-matter fields (one `key: value` line each) and the body of a source file."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---":
        raise SourceError(f"{path}: a front-matter block is expected first")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise SourceError(f"{path}: the front-matter block is not closed") from None
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator or not value.strip():
            raise SourceError(f"{path}: front-matter line {line!r} must be `key: value`")
        if key in fields:
            raise SourceError(f"{path}: the field {key} appears twice")
        if key not in (*required, *optional):
            raise SourceError(f"{path}: the field {key} is not known here")
        fields[key] = value.strip()
    for key in required:
        if key not in fields:
            raise SourceError(f"{path}: the field {key} is missing")
    return fields, "\n".join(lines[end + 1 :])


def markers(text: str) -> list[tuple[str, str]]:
    """Every (`requires` or `unless`, command) marker in a text, for tests and checks."""
    return [(m.group(1), m.group(2)) for line in text.split("\n") if (m := _MARKER.search(line))]


def render_steps(text: str, available: Collection[str]) -> str:
    """Drop the steps whose marker condition does not hold, then renumber what is left."""
    kept: list[str] = []
    dropping = False
    for line in text.replace("\r\n", "\n").split("\n"):
        marker = _MARKER.search(line)
        if marker is not None:
            present = marker.group(2) in available
            dropping = not (present if marker.group(1) == "requires" else not present)
            line = line[: marker.start()]
        elif not line.strip() or not line.startswith(" "):
            dropping = False
        if not dropping:
            kept.append(line)
    return _collapse_blank_lines(_renumber(kept))


def _renumber(lines: list[str]) -> list[str]:
    result: list[str] = []
    expected = 0
    for line in lines:
        match = _NUMBERED.match(line)
        if match is None:
            if not line.startswith(" ") and line.strip():
                expected = 0  # a paragraph ends the list
            result.append(line)
            continue
        expected += 1
        result.append(f"{expected}.{line[match.end(1) + 1 :]}")
    return result


def _collapse_blank_lines(lines: list[str]) -> str:
    out: list[str] = []
    for line in lines:
        if not line.strip() and (not out or not out[-1].strip()):
            continue
        out.append(line.rstrip())
    while out and not out[-1]:
        out.pop()
    return "\n".join(out) + "\n"


def load_skills(workflow: WorkflowSource, available: Collection[str]) -> tuple[ClientSkill, ...]:
    """One skill per `skills/<name>/skill.md`, with its `references/` files, in name order."""
    version = str(workflow.release.version)
    skills = []
    for path in workflow.paths():
        parts = path.split("/")
        if len(parts) != 3 or parts[0] != "skills" or parts[2] != "skill.md":
            continue
        name = parts[1]
        if not _NAME.fullmatch(name):
            raise SourceError(f"{path}: a skill directory is lower case letters and hyphens")
        fields, body = parse_source(
            path, workflow.read_text(path), required=("name", "description")
        )
        if fields["name"] != name:
            raise SourceError(
                f"{path}: the name {fields['name']!r} must equal the directory {name!r}"
            )
        rendered = render_steps(body, available)
        references = tuple(
            (ref.removeprefix(f"skills/{name}/references/"), workflow.read_text(ref))
            for ref in workflow.paths()
            if ref.startswith(f"skills/{name}/references/") and ref.endswith(".md")
        )
        skills.append(
            ClientSkill(
                name=name,
                description=fields["description"],
                body=rendered,
                references=references,
                inputs=((f"skills/{name}", version, sha256_hex(rendered.encode("utf-8"))),),
            )
        )
    return tuple(skills)


def load_roles(workflow: WorkflowSource) -> tuple[ClientRole, ...]:
    """One role per `roles/<name>.md`, in name order. The body is the role's system prompt."""
    version = str(workflow.release.version)
    roles = []
    for path in workflow.paths():
        parts = path.split("/")
        if len(parts) != 2 or parts[0] != "roles" or not parts[1].endswith(".md"):
            continue
        name = parts[1].removesuffix(".md")
        if not _NAME.fullmatch(name):
            raise SourceError(f"{path}: a role file name is lower case letters and hyphens")
        fields, body = parse_source(
            path, workflow.read_text(path), required=("name", "description", "mode")
        )
        if fields["name"] != name:
            raise SourceError(
                f"{path}: the name {fields['name']!r} must equal the file name {name!r}"
            )
        if fields["mode"] not in {"read-only", "writes"}:
            raise SourceError(f"{path}: mode is `read-only` or `writes`, not {fields['mode']!r}")
        text = _collapse_blank_lines(body.split("\n"))
        roles.append(
            ClientRole(
                name=name,
                description=fields["description"],
                body=text,
                read_only=fields["mode"] == "read-only",
                inputs=((f"roles/{name}", version, sha256_hex(text.encode("utf-8"))),),
            )
        )
    return tuple(roles)
