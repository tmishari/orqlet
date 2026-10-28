"""Turn the workflow package and the resolved rules into what the client adapters need."""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Sequence
from dataclasses import replace

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import Resources
from orqlet.application.contracts.workflow_package import WorkflowRuleMeta
from orqlet.application.ports.documents import DocumentLoader
from orqlet.application.ports.instruction_adapter import (
    ClientCommand,
    ClientSkill,
    ConventionsView,
    RenderRequest,
    ScopedRule,
)
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.resources_view import (
    catalogue_skill,
    resource_rules,
    resource_skills,
)
from orqlet.application.usecases.workflow_sources import (
    SourceError,
    load_roles,
    load_skills,
    parse_source,
)
from orqlet.domain.digest import sha256_hex
from orqlet.domain.errors import OrqletError
from orqlet.domain.ownership import FileClass
from orqlet.domain.resolver import Level, RuleSpec

WORKFLOW_RULE = "rules/orqlet-workflow"
COMMANDS_DIR = "commands/"
_SLOT = "{{lines}}"


class RenderRequestError(OrqletError):
    """The inputs cannot be rendered, for example two rules that would share a file name."""


def rule_slug(rule_id: str) -> str:
    """`PY-001` becomes `py-001`. Anything outside letters and digits becomes one hyphen."""
    slug = re.sub(r"[^a-z0-9]+", "-", rule_id.lower()).strip("-")
    if not slug:
        raise RenderRequestError(f"rule id {rule_id!r} has no letters or digits for a file name")
    return slug


def build_render_request(
    workflow: WorkflowSource,
    loader: DocumentLoader,
    rules: Sequence[RuleSpec],
    resources: Resources,
    conventions: ConventionsView | None,
    *,
    client_version: str | None = None,
    available_commands: Collection[str] = IMPLEMENTED_COMMANDS,
) -> RenderRequest:
    """The baseline, the workflow rule and one scoped file per MUST rule that names paths.

    Rules without paths are not written as files: they would load for every task and grow the
    always-on baseline. An agent reads them with `orqlet standards for`. The team's registry adds
    its rules, its tool skills and its catalogue, and the conventions view becomes the block of
    `AGENTS.md`; the fixed text around their lines comes from the templates of the workflow
    package, so that it is in the manifest and a change of it is a release.
    """
    version = str(workflow.release.version)
    meta = load_contract(
        loader,
        WorkflowRuleMeta,
        workflow.read_text(f"{WORKFLOW_RULE}.meta.yaml").encode("utf-8"),
        source=f"{WORKFLOW_RULE}.meta.yaml",
    )
    workflow_body = workflow.read_text(f"{WORKFLOW_RULE}.md")
    scoped = [
        ScopedRule(
            name=meta.name,
            description=meta.description,
            paths=meta.paths,
            body=workflow_body,
            file_class=FileClass.PROTECTED,
            inputs=((WORKFLOW_RULE, version, sha256_hex(workflow_body.encode("utf-8"))),),
        )
    ]
    seen = {meta.name}
    for rule in sorted(rules, key=lambda r: r.id):
        if rule.level is not Level.MUST or not rule.scope.paths:
            continue
        slug = rule_slug(rule.id)
        if slug in seen:
            raise RenderRequestError(f"rule {rule.id} would reuse the file name orqlet-{slug}")
        seen.add(slug)
        scoped.append(_pack_rule(rule, slug))
    for team_rule in resource_rules(resources):
        if team_rule.name in seen:
            raise RenderRequestError(
                f"a rule would reuse the file name orqlet-{team_rule.name}: a pack rule and a "
                "resource of the registry claim it"
            )
        seen.add(team_rule.name)
        scoped.append(_from_template(workflow, "resource-rule", team_rule, version))
    skills = list(_checked(lambda: load_skills(workflow, available_commands)))
    skills += _team_skills(workflow, resources, {skill.name for skill in skills}, version)
    return RenderRequest(
        workflow_version=version,
        baseline_body=workflow.read_text("baseline/baseline.md"),
        scoped_rules=tuple(scoped),
        commands=_commands(workflow, version),
        skills=tuple(skills),
        roles=_checked(lambda: load_roles(workflow)),
        client_version=client_version,
        conventions=_conventions_block(workflow, conventions),
    )


def _fill(workflow: WorkflowSource, name: str, lines: str) -> tuple[str, str]:
    """The template `templates/<name>.md` with its one slot replaced, and the template's name."""
    path = f"templates/{name}.md"
    template = workflow.read_text(path)
    if template.count(_SLOT) != 1:
        raise RenderRequestError(f"{path} must have exactly one slot, the line {_SLOT}")
    text = template.replace(_SLOT, lines)
    return (text if text.endswith("\n") else text + "\n"), f"templates/{name}"


def _from_template[T: (ScopedRule, ClientSkill)](
    workflow: WorkflowSource, name: str, item: T, version: str
) -> T:
    text, source = _fill(workflow, name, item.body)
    return replace(item, body=text, inputs=((source, version, sha256_hex(text.encode("utf-8"))),))


def _team_skills(
    workflow: WorkflowSource, resources: Resources, taken: set[str], version: str
) -> list[ClientSkill]:
    found = [
        _from_template(workflow, "tool-skill", skill, version)
        for skill in resource_skills(resources)
    ]
    catalogue = catalogue_skill(resources)
    if catalogue is not None:
        found.append(_from_template(workflow, "catalogue-skill", catalogue, version))
    for skill in found:
        if skill.name in taken:
            raise RenderRequestError(f"two skills would use the name {skill.name}")
        taken.add(skill.name)
    return found


def _conventions_block(
    workflow: WorkflowSource, conventions: ConventionsView | None
) -> ConventionsView | None:
    if conventions is None:
        return None
    text, _ = _fill(workflow, "conventions-block", "\n".join(conventions.lines))
    return ConventionsView(tuple(text.rstrip("\n").split("\n")), conventions.resources)


def _checked[T](load: Callable[[], T]) -> T:
    try:
        return load()
    except SourceError as error:
        raise RenderRequestError(str(error)) from None


def _commands(workflow: WorkflowSource, version: str) -> tuple[ClientCommand, ...]:
    """One command per `commands/<name>.md` of the workflow package, in name order."""
    found = []
    for path in workflow.paths():
        if not (path.startswith(COMMANDS_DIR) and path.endswith(".md")):
            continue
        name = path.removeprefix(COMMANDS_DIR).removesuffix(".md")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise RenderRequestError(f"{path}: a command name is lower case letters and hyphens")
        description, body = parse_command(path, workflow.read_text(path))
        found.append(
            ClientCommand(
                name=name,
                description=description,
                body=body,
                inputs=((path.removesuffix(".md"), version, sha256_hex(body.encode("utf-8"))),),
            )
        )
    return tuple(found)


def parse_command(path: str, text: str) -> tuple[str, str]:
    """The description and the body of a command source.

    A source starts with a front-matter block holding exactly one `description:` line. The
    workflow package ships the file, so a malformed one is a defect of the release, not input.
    """
    try:
        fields, body = parse_source(path, text, required=("description",))
    except SourceError as error:
        raise RenderRequestError(str(error)) from None
    return fields["description"], body


def _pack_rule(rule: RuleSpec, slug: str) -> ScopedRule:
    lines = [f"# {rule.id}", "", f"{rule.level.name}: {rule.text}", ""]
    if rule.scope.roles:
        lines.append(f"Roles: {', '.join(sorted(rule.scope.roles))}")
    if rule.scope.phases:
        lines.append(f"Phases: {', '.join(sorted(rule.scope.phases))}")
    lines.append(f"Source: {rule.source}")
    body = "\n".join(lines) + "\n"
    return ScopedRule(
        name=slug,
        description=f"{rule.id}: {rule.text}",
        paths=tuple(sorted(rule.scope.paths)),
        body=body,
        file_class=FileClass.GENERATED,
        inputs=((rule.id, rule.source, sha256_hex(body.encode("utf-8"))),),
    )
