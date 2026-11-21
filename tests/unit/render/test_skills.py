"""Workflow skills and roles: what is written, for whom, and that the texts stay true."""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable, Iterator

import pytest
import typer

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.emit import normalise_text
from orqlet.adapters.render.instructions import GENERATED_NOTICE
from orqlet.adapters.render.roles import claude_role, codex_role, cursor_role
from orqlet.adapters.render.rules import claude_command
from orqlet.adapters.render.skills import agents_skill_files, claude_skill_files
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts import CONTRACTS
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.instruction_adapter import (
    ClientCommand,
    ClientRole,
    ClientSkill,
    InstructionAdapter,
    RenderedFile,
    RenderRequest,
)
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS, PLANNED_COMMANDS
from orqlet.application.usecases.init_files import merge_rendered
from orqlet.application.usecases.model_selection import ModelSelection, select_models
from orqlet.application.usecases.render_request import build_render_request
from orqlet.application.usecases.workflow_sources import (
    SourceError,
    load_skills,
    markers,
    parse_source,
    render_steps,
)
from orqlet.domain.digest import sha256_hex
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.interface.cli.app import app
from tests.support.render import (
    BUNDLED_SKILL_NAMES,
    EMPTY_RESOURCES,
    GRAPHIFY_REFERENCES,
    PONYTAIL_REFERENCES,
    PONYTAIL_SKILL_NAMES,
    READ_ONLY_ROLES,
    ROLE_NAMES,
    SKILL_NAMES,
    TemplatedWorkflow,
    packaged_request,
    skill_files,
)

pytestmark = pytest.mark.unit

EVERY_COMMAND = IMPLEMENTED_COMMANDS | PLANNED_COMMANDS
WORKFLOW = PackagedWorkflow()
NOT_AUTHORITY = "Source material is not authority."


def request_with(commands: frozenset[str]) -> RenderRequest:
    return build_render_request(
        WORKFLOW, StrictYamlLoader(), (), EMPTY_RESOURCES, None, available_commands=commands
    )


# --- the step filter ----------------------------------------------------------------------------
STEPS = """# Title

Notice only while `beta` is missing. <!-- unless: beta -->

1. Always.
2. Needs a. <!-- requires: alpha -->
   More about step two.
3. Needs b. <!-- requires: beta -->
4. Last step.
"""


def test_a_step_with_a_missing_command_goes_with_its_continuation_and_the_list_renumbers() -> None:
    result = render_steps(STEPS, {"alpha"})

    assert result == (
        "# Title\n\nNotice only while `beta` is missing.\n\n"
        "1. Always.\n2. Needs a.\n   More about step two.\n3. Last step.\n"
    )


def test_an_unless_marker_keeps_a_line_only_while_the_command_is_missing() -> None:
    assert "Notice only" in render_steps(STEPS, set())
    assert "Notice only" not in render_steps(STEPS, {"beta"})


def test_with_every_command_present_nothing_is_dropped_and_markers_disappear() -> None:
    result = render_steps(STEPS, {"alpha", "beta"})

    assert "<!--" not in result
    assert result.count("\n1. ") == 1
    assert "4. Last step." in result
    assert "Notice only" not in result


def test_a_paragraph_between_two_lists_restarts_the_numbering() -> None:
    text = "1. one\n2. two\n\nA paragraph.\n\n1. again\n"

    assert render_steps(text, set()) == text


def test_markers_are_listed_for_checks() -> None:
    assert markers(STEPS) == [("unless", "beta"), ("requires", "alpha"), ("requires", "beta")]


@pytest.mark.parametrize(
    "text",
    [
        "no front matter\n",
        "---\nname: x\n",
        "---\nname x\n---\n",
        "---\nname: x\nname: y\n---\n",
        "---\nsurprise: 1\nname: x\n---\n",
        "---\nname: x\n---\n",  # description missing
    ],
)
def test_a_malformed_source_is_a_release_defect(text: str) -> None:
    with pytest.raises(SourceError):
        parse_source("skills/x/skill.md", text, required=("name", "description"))


# --- what the package ships ---------------------------------------------------------------------
def test_the_package_ships_the_expected_skills_roles_and_references() -> None:
    """phase-skill-contracts P-2, AC-5; one-command-setup P-2, AC-1, AC-2 and AC-11.
    expected_behavior_source: ADR-001 decision 3 of phase-skill-contracts (research, design, plan
    and implement each carry `references/phase-contract.md`; onboard and review do not) and BC-4;
    one-command-setup ADR-006 decision 1 (each bundled skill carries PROVENANCE.md and its licence
    file), Q-52 (graphify's seven shared references) and the interface that the Coder gave (the
    family files are not references). References are attached in path order, upper case first."""
    request = packaged_request()

    assert tuple(s.name for s in request.skills) == SKILL_NAMES
    assert tuple(r.name for r in request.roles) == ROLE_NAMES
    assert {s.name: [n for n, _ in s.references] for s in request.skills if s.references} == {
        "graphify": list(GRAPHIFY_REFERENCES),
        "orqlet-design": ["design-format.md", "phase-contract.md"],
        "orqlet-implement": ["phase-contract.md"],
        "orqlet-plan": ["phase-contract.md", "plan-format.md"],
        "orqlet-research": ["as-is-format.md", "phase-contract.md"],
        "orqlet-review": ["review-format.md"],
        **{name: list(PONYTAIL_REFERENCES) for name in PONYTAIL_SKILL_NAMES},
    }


def test_every_orqlet_skill_says_that_source_material_is_not_authority_and_stops_for_a_person() -> (
    None
):
    """Every packaged skill except the bundled upstream snapshots. expected_behavior_source:
    one-command-setup P-2, AC-3 and ADR-006 decision 2 (a bundled snapshot differs from upstream
    only by the adaptations its PROVENANCE.md lists, so Orqlet's sentences are not added to it)."""
    for skill in packaged_request().skills:
        if skill.name in BUNDLED_SKILL_NAMES:
            continue
        assert NOT_AUTHORITY in skill.body, skill.name
        assert "STOP." in skill.body, skill.name


def test_every_skill_description_fits_the_agent_skills_limits() -> None:
    for skill in packaged_request().skills:
        assert 0 < len(skill.name) <= 64
        assert 0 < len(skill.description) <= 1024
        assert "\n" not in skill.description


def test_a_marker_names_a_command_this_release_has_or_a_later_slice_will() -> None:
    for skill in packaged_request().skills:
        source = WORKFLOW.read_text(f"skills/{skill.name}/skill.md")
        for _, command in markers(source):
            assert command in EVERY_COMMAND, f"{skill.name}: {command}"


def command_options(path: str) -> set[str]:
    group = typer.main.get_command(app)
    for part in path.split():
        group = group.commands[part]  # type: ignore[attr-defined,unused-ignore]
    return {option for param in group.params for option in param.opts}


def mentioned_commands(text: str) -> Iterator[tuple[str, list[str]]]:
    """Each `orqlet ...` in backticks: the command words and the flags that follow them."""
    for span in re.findall(r"`(orqlet [^`]+)`", text):
        words = [w for w in span.split()[1:] if not w.startswith(("-", "<", "["))]
        flags = [w for w in span.split() if w.startswith("--")]
        yield " ".join(words[:2]), flags


def assert_only_known_commands(where: str, text: str) -> None:
    for command, flags in mentioned_commands(text):
        known = [
            c
            for c in IMPLEMENTED_COMMANDS | PLANNED_COMMANDS
            if c == command or c.startswith(command + " ")
        ]
        candidates = [
            c
            for c in IMPLEMENTED_COMMANDS
            if c == command or command.startswith(c + " ") or c.startswith(command + " ")
        ]
        assert known or candidates, f"{where}: `orqlet {command}`"
        full = next((c for c in IMPLEMENTED_COMMANDS if command.startswith(c)), None)
        if full is None:
            continue  # a planned command: its flags are checked when it exists
        for flag in flags:
            assert flag in command_options(full) | {"--help"}, f"{where}: {full} {flag}"


def test_skills_only_mention_commands_and_flags_that_exist_or_are_planned() -> None:
    """phase-skill-contracts P-2, AC-6. expected_behavior_source: BC-5 ("Every backticked
    `orqlet ...` in a skill body or a reference names an existing command and existing flags") and
    Q-4 (existing commands only): every body and, from this phase on, every reference."""
    for skill in request_with(EVERY_COMMAND).skills:
        assert_only_known_commands(skill.name, skill.body)
        for name, text in skill.references:
            assert_only_known_commands(f"{skill.name}/references/{name}", text)


# The commands that existed before the evidence records of slice S9.
BEFORE_RECORDS = IMPLEMENTED_COMMANDS - {
    "knowledge impact",
    "review prepare",
    "validate review",
    "validate test",
    "validate knowledge",
}


def test_a_skill_never_names_a_command_that_the_release_it_is_rendered_for_lacks() -> None:
    for available in (BEFORE_RECORDS, IMPLEMENTED_COMMANDS):
        for skill in request_with(available).skills:
            for command, _ in mentioned_commands(skill.body):
                assert any(
                    command == c or command.startswith(c + " ") or c.startswith(command + " ")
                    for c in available
                ), f"{skill.name}: `orqlet {command}` is not in this release"


def test_before_the_records_exist_the_implement_skill_drops_the_steps_that_need_them() -> None:
    """phase-skill-contracts P-2, AC-2. expected_behavior_source: ADR-001 consequences (each step
    count takes the new count, and the rule stays: numbering from 1 without a gap) and the
    interface that the Coder gave (7 steps with BEFORE_RECORDS)."""
    implement = next(s for s in request_with(BEFORE_RECORDS).skills if s.name == "orqlet-implement")

    assert "knowledge impact" not in implement.body
    assert "/orqlet-review" not in implement.body
    assert "orqlet validate test" not in implement.body
    assert re.findall(r"^(\d+)\. ", implement.body, re.MULTILINE) == [
        str(n) for n in range(1, 9)
    ]  # three steps are gone (of 11) and the list is numbered again without a gap; the lookup
    # step stays, because `resources list` is not one of the commands that came with the records,
    # and so does the PR-text step, which needs no command (P-13 AC-8)
    assert "orqlet-pr-writer" in implement.body


def test_in_this_release_the_implement_skill_is_complete() -> None:
    implement = next(s for s in packaged_request().skills if s.name == "orqlet-implement")

    assert "orqlet knowledge impact" in implement.body
    assert "no independent review" not in implement.body


def test_with_every_command_the_implement_skill_has_all_eleven_steps() -> None:
    """phase-skill-contracts P-2, AC-2 and AC-19; dynamic-model-profiles P-13, AC-8.
    expected_behavior_source: ADR-001 consequences of phase-skill-contracts (the step count with
    every command takes the new count) and the interface that the Coder gave for P-13 (11 steps
    with every command: the PR-text step of ADR-006 decision 8 comes before the stop step)."""
    implement = next(s for s in request_with(EVERY_COMMAND).skills if s.name == "orqlet-implement")

    assert re.findall(r"^(\d+)\. ", implement.body, re.MULTILINE) == [str(n) for n in range(1, 12)]
    assert "orqlet knowledge impact" in implement.body
    assert "/orqlet-review" in implement.body


def test_references_hold_examples_that_pass_the_contracts_they_describe() -> None:
    """phase-skill-contracts P-2, AC-5. expected_behavior_source: ADR-001 consequences ("the
    YAML-example test, which applies only to the four format references from now on"):
    phase-contract.md describes no artifact, so it holds no example."""
    schemas = {
        "as-is-format.md": "orqlet.as-is/v1",
        "design-format.md": "orqlet.design-set/v1",
        "plan-format.md": "orqlet.implementation-plan/v1",
        "review-format.md": "orqlet.review-result/v1",
    }
    found = 0
    for skill in packaged_request().skills:
        for name, text in skill.references:
            if name not in schemas:
                continue
            match = re.search(r"```yaml\n(.*?)```", text, re.DOTALL)
            assert match is not None, name
            schema_id = schemas[name]
            load_contract(
                StrictYamlLoader(), CONTRACTS[schema_id], match.group(1).encode(), source=name
            )
            found += 1
    assert found == 4


# --- what each client gets ----------------------------------------------------------------------
SKILL = ClientSkill(
    name="orqlet-sample",
    description="A sample skill",
    body="# Sample\n\n1. Do it.\n",
    references=(("notes.md", "Notes\n"),),
    inputs=(("skills/orqlet-sample", "0.2.0", "a" * 64),),
)


def test_claude_and_the_agents_folder_get_the_same_skill_file_at_different_paths() -> None:
    claude = claude_skill_files(SKILL)
    agents = agents_skill_files(SKILL)

    assert [str(f.path) for f in claude] == [
        ".claude/skills/orqlet-sample/SKILL.md",
        ".claude/skills/orqlet-sample/references/notes.md",
    ]
    assert [str(f.path) for f in agents] == [
        ".agents/skills/orqlet-sample/SKILL.md",
        ".agents/skills/orqlet-sample/references/notes.md",
    ]
    assert [f.content for f in claude] == [f.content for f in agents]


def test_a_skill_file_names_itself_and_cannot_be_started_by_the_model() -> None:
    text = claude_skill_files(SKILL)[0].content.decode()

    head = "---\nname: orqlet-sample\ndescription: A sample skill\n"
    assert text.startswith(head + "disable-model-invocation: true\n---\n")
    assert "<!-- Generated by Orqlet." in text


# harness2-fit, phase P-3, AC-3: the skill, role and command renderers pass `plain_when_safe=True`
# (the rule renderers do not; that part is in test_emit.py). Every test cites its
# `expected_behavior_source`: ADR-001 is
# docs/design/harness2-fit/design/adr-001-client-visible-front-matter.md, decision 1.
def test_the_agents_folder_skill_file_is_unquoted_too() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (the skill renderer passes it)."""
    text = agents_skill_files(SKILL)[0].content.decode()

    head = "---\nname: orqlet-sample\ndescription: A sample skill\n"
    assert text.startswith(head + "disable-model-invocation: true\n---\n")


def test_a_skill_keeps_quotes_only_on_the_text_that_needs_them() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (not plain-safe stays quoted)."""
    needs_quotes = ClientSkill(
        name="orqlet-sample",
        description="A sample: with a colon",
        body="# Sample\n",
        inputs=SKILL.inputs,
    )

    for files in (claude_skill_files(needs_quotes), agents_skill_files(needs_quotes)):
        text = files[0].content.decode()
        assert text.startswith(
            "---\nname: orqlet-sample\n"
            'description: "A sample: with a colon"\n'
            "disable-model-invocation: true\n---\n"
        )


def test_every_packaged_skill_names_itself_without_quote_characters() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 and its Context (AS-IS O-11)."""
    for skill in packaged_request().skills:
        for files in (claude_skill_files(skill), agents_skill_files(skill)):
            lines = files[0].content.decode().splitlines()
            assert f"name: {skill.name}" in lines, skill.name
            assert "disable-model-invocation: true" in lines, skill.name


def test_skills_and_roles_are_protected_files_that_orqlet_owns() -> None:
    request = packaged_request()
    files = [
        f
        for adapter in (ClaudeCodeAdapter(), CursorAdapter(), CodexAdapter())
        for f in adapter.render(request).files
        if "skills" in str(f.path)
        or ("agents" in str(f.path) and not str(f.path).startswith("AGENTS"))
    ]

    assert files
    assert {f.owner for f in files} == {OwnerMode.ORQLET}
    assert {f.file_class for f in files} == {FileClass.PROTECTED}
    assert all(f.inputs for f in files)


def test_cursor_and_codex_files_merge_into_one_set_without_a_conflict() -> None:
    request = packaged_request()
    both = [*CursorAdapter().render(request).files, *CodexAdapter().render(request).files]

    merged = merge_rendered(both)

    assert len({str(f.path) for f in merged}) == len(merged)


def test_codex_keeps_a_skill_from_starting_on_its_own_with_a_sidecar() -> None:
    files = {str(f.path): f for f in CodexAdapter().render(packaged_request()).files}

    sidecar = files[".agents/skills/orqlet-research/agents/openai.yaml"].content.decode()

    assert "allow_implicit_invocation: false" in sidecar
    assert "ORQ-L005" in {limit.code for limit in CodexAdapter().render(packaged_request()).limits}


def test_cursor_says_it_may_list_a_skill_twice_when_claude_is_enabled_too() -> None:
    assert "ORQ-L004" in {limit.code for limit in CursorAdapter().render(packaged_request()).limits}


ROLE = ClientRole(name="orqlet-sample", description="A sample role", body="Be careful.\n")


def test_a_read_only_role_is_read_only_by_the_strongest_control_of_each_client() -> None:
    assert "tools: Read, Grep, Glob" in claude_role(ROLE).content.decode()
    assert "readonly: true" in cursor_role(ROLE).content.decode()
    assert 'sandbox_mode = "read-only"' in codex_role(ROLE).content.decode()


# harness2-fit, phase P-3, AC-3 (continued): the Claude Code and Cursor role renderers and the
# Claude Code command renderer pass `plain_when_safe=True`. expected_behavior_source: ADR-001
# decision 1.
def test_the_claude_code_role_writes_plain_safe_values_without_quotes() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (the role renderers pass the keyword)."""
    text = claude_role(ROLE).content.decode()

    assert text.startswith(
        "---\nname: orqlet-sample\ndescription: A sample role\n"
        "tools: Read, Grep, Glob\nmodel: inherit\n---\n"
    )


def test_the_claude_code_role_that_writes_is_unquoted_and_has_no_tools_line() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (the role renderers pass the keyword)."""
    writer = ClientRole(name="orqlet-writer", description="A writer", body="b\n", read_only=False)

    text = claude_role(writer).content.decode()

    assert text.startswith("---\nname: orqlet-writer\ndescription: A writer\nmodel: inherit\n---\n")


def test_the_cursor_role_writes_plain_safe_values_without_quotes() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (the role renderers pass the keyword)."""
    text = cursor_role(ROLE).content.decode()

    assert text.startswith(
        "---\nname: orqlet-sample\ndescription: A sample role\n"
        "model: inherit\nreadonly: true\n---\n"
    )


def test_a_role_keeps_quotes_only_on_the_text_that_needs_them() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (not plain-safe stays quoted)."""
    needs_quotes = ClientRole(name="orqlet-sample", description="Reads: carefully", body="b\n")

    claude = claude_role(needs_quotes).content.decode()
    cursor = cursor_role(needs_quotes).content.decode()

    assert claude.startswith(
        '---\nname: orqlet-sample\ndescription: "Reads: carefully"\n'
        "tools: Read, Grep, Glob\nmodel: inherit\n---\n"
    )
    assert cursor.startswith(
        '---\nname: orqlet-sample\ndescription: "Reads: carefully"\n'
        "model: inherit\nreadonly: true\n---\n"
    )


def test_every_packaged_role_names_itself_and_its_model_without_quote_characters() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 and its Context (AS-IS O-11, O-12)."""
    for role in packaged_request().roles:
        claude = claude_role(role).content.decode().splitlines()
        cursor = cursor_role(role).content.decode().splitlines()
        for lines in (claude, cursor):
            assert f"name: {role.name}" in lines, role.name
            assert "model: inherit" in lines, role.name
        assert ("tools: Read, Grep, Glob" in claude) is role.read_only, role.name
        assert f"readonly: {'true' if role.read_only else 'false'}" in cursor, role.name


def test_the_claude_code_command_writes_a_plain_safe_description_without_quotes() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (the command renderer passes it)."""
    command = ClientCommand(name="sample", description="A sample command", body="Do it.\n")

    text = claude_command(command).content.decode()

    assert text.startswith("---\ndescription: A sample command\n---\n")


def test_the_claude_code_command_keeps_quotes_on_text_that_needs_them() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (not plain-safe stays quoted)."""
    command = ClientCommand(name="sample", description="Run it: now", body="Do it.\n")

    text = claude_command(command).content.decode()

    assert text.startswith('---\ndescription: "Run it: now"\n---\n')


def test_a_role_that_writes_is_not_given_the_read_only_controls() -> None:
    writer = ClientRole(name="orqlet-writer", description="d", body="b\n", read_only=False)

    assert "tools:" not in claude_role(writer).content.decode()
    assert "readonly: false" in cursor_role(writer).content.decode()
    assert "sandbox_mode" not in codex_role(writer).content.decode()


def test_a_role_file_names_a_model_only_when_assigned_and_never_an_excluded_one() -> None:
    """P-5 AC-9. expected_behavior_source: plan P-5 AC-9 ("the vendor-name test is modified": a
    role file names a model only when the policy assigned it, and never an excluded one); AC-1
    (with no policy the files are those of today); AC-8 (an excluded string reaches no file); BC-1;
    ADR-003 decision 1; ADR-005 decision 2. The names assigned here are placeholders. The brief
    of this phase keeps the vendor-name check for the case with no policy.
    """
    vendors = ("gpt-", "claude-", "sonnet", "opus", "haiku", "gemini")
    excluded_strings = ("fable", "best", "claude-fable-")
    assigned = {"claude-code": "example-alpha", "cursor": "example-beta", "codex": "example-gamma"}

    def policy(route_names: dict[str, str], excluded: list[dict[str, object]]) -> ModelPolicy:
        routes: list[dict[str, object]] = [
            {
                "client": client,
                "kind": "id",
                "name": name,
                "resolves_to": None,
                "also_known_as": [],
                "access": "unknown",
            }
            for client, name in route_names.items()
        ]
        model = {
            "id": "example-model",
            "family": "example-family",
            "approval": {"state": "approved"},
            "documented": {"evidence": "docs/example/evidence/entry.md", "date": "2026-10-30"},
            "callable": "not-run",
            "evaluated": {"state": "none"},
            "routes": routes,
        }
        assignment = {
            "target": {"kind": "role", "name": "orqlet-tester"},
            "task": None,
            "client": None,
            "profile": None,
            "model": "example-model",
            "mode": "manual",
            "effort": None,
        }
        return ModelPolicy.model_validate(
            {
                "schema": "orqlet.model-policy/v2",
                "policy_version": 1,
                "reviewed_for_release": "0.4.0",
                "models": [model],
                "excluded": excluded,
                "profiles": [],
                "assignments": [assignment],
            }
        )

    def role_files(selection: ModelSelection | None) -> dict[str, str]:
        request = build_render_request(
            WORKFLOW, StrictYamlLoader(), (), EMPTY_RESOURCES, None, selection=selection
        )
        return {
            str(rendered.path): rendered.content.decode()
            for role in request.roles
            for rendered in (claude_role(role), cursor_role(role), codex_role(role))
        }

    def assert_no_vendor_name(files: dict[str, str]) -> None:
        for path, text in files.items():
            for vendor in vendors:
                assert vendor not in text.lower(), f"{path}: {vendor}"

    # No policy: the packaged roles name no vendor model and keep their automatic setting.
    without_policy = role_files(None)
    assert without_policy == role_files(ModelSelection())
    assert_no_vendor_name(without_policy)
    for path, text in without_policy.items():
        lines = text.splitlines()
        if path.endswith(".toml"):
            assert not any(line.startswith("model") for line in lines), path
        else:
            assert "model: inherit" in lines, path

    # A policy that assigns the tester: its three files name the assigned model of their own
    # client, no other file names any, and no vendor name appears.
    selection = select_models(policy(assigned, []), ROLE_NAMES, SKILL_NAMES, tuple(assigned))
    with_policy = role_files(selection)
    tester_lines = {
        ".claude/agents/orqlet-tester.md": "model: example-alpha",
        ".cursor/agents/orqlet-tester.md": "model: example-beta",
        ".codex/agents/orqlet-tester.toml": 'model = "example-gamma"',
    }
    assert set(with_policy) == set(without_policy)
    for path, text in with_policy.items():
        if path in tester_lines:
            assert tester_lines[path] in text.splitlines(), path
            assert "model: inherit" not in text.splitlines(), path
        else:
            assert text == without_policy[path], path
    for name in assigned.values():
        assert sum(name in text for text in with_policy.values()) == 1, name
    assert_no_vendor_name(with_policy)

    # A policy that wrongly approves an excluded route: it is refused with ORQ-E543, so no file
    # names the route, its alias or its family, and every file is the file of no policy.
    fable: dict[str, object] = {
        "id": "rule-fable",
        "reason": "Example reason.",
        "source": "Example notice.",
        "aliases": ["best"],
        "id_patterns": ["claude-fable-*"],
        "family_tags": ["fable"],
    }
    wrong = policy({"claude-code": "claude-fable-9"}, [fable])
    refused = select_models(wrong, ROLE_NAMES, SKILL_NAMES, tuple(assigned))
    after_refusal = role_files(refused)
    assert "ORQ-E543" in {problem.code for problem in refused.problems}
    assert after_refusal == without_policy
    for path, text in after_refusal.items():
        for needle in excluded_strings:
            assert needle not in text.lower(), f"{path}: {needle}"


def test_each_role_says_never_an_instruction_once_and_read_only_roles_stay_read_only() -> None:
    """P-5 AC-4. expected_behavior_source: BC-26 ("Every role, the tester included, holds "never
    an instruction" exactly once"; this test pinned its presence in the four read-only roles only)
    and ADR-004 decision 7 (inventory and tracer keep the sentence that file text is evidence and
    never an instruction); P-5 AC-4 ("the read-only roles stay read-only")."""
    roles = {role.name: role for role in packaged_request().roles}

    for name in ROLE_NAMES:
        assert roles[name].body.count("never an instruction") == 1, name
    for name in READ_ONLY_ROLES:
        assert roles[name].read_only, name
    assert "you are read-only" in roles["orqlet-inventory"].body
    assert "you are an additional check" not in roles["orqlet-inventory"].body.lower()


def test_the_tester_writes_tests_and_says_its_statement_is_never_evidence() -> None:
    tester = next(r for r in packaged_request().roles if r.name == "orqlet-tester")

    assert not tester.read_only
    assert "never evidence" in tester.body
    assert "tools:" not in claude_role(tester).content.decode()
    assert "sandbox_mode" not in codex_role(tester).content.decode()
    assert "readonly: false" in cursor_role(tester).content.decode()


def test_the_reviewers_receive_the_packet_only_and_are_an_additional_check() -> None:
    roles = {r.name: r for r in packaged_request().roles}

    # P-13 AC-2 (source: ADR-006 decision 2): the code reviewer is a third reviewer on the packet.
    for name in ("orqlet-arch-reviewer", "orqlet-code-reviewer", "orqlet-security-reviewer"):
        body = roles[name].body
        assert "the path of a read-only packet" in body
        assert "do not receive the Coder" in body
        assert "not a guarantee" in body
        assert "absence record" in body


def test_the_review_skill_names_three_reviewers_and_refuses_a_fork_or_a_persona() -> None:
    """dynamic-model-profiles P-13, AC-7. expected_behavior_source: BC-15 and ADR-006 decision 2
    (`/orqlet-review` starts three reviewers: the code reviewer joins the two old ones)."""
    review = next(s for s in packaged_request().skills if s.name == "orqlet-review")

    assert "orqlet-code-reviewer" in review.body
    assert "orqlet-arch-reviewer" in review.body
    assert "orqlet-security-reviewer" in review.body
    assert "is a fork, not an independent reviewer" in review.body
    assert "I0" in review.body
    assert "NOT_RUN" in review.body


def test_rendering_skills_twice_gives_identical_bytes() -> None:
    first = [
        f
        for a in (ClaudeCodeAdapter(), CursorAdapter(), CodexAdapter())
        for f in a.render(packaged_request()).files
    ]
    second = [
        f
        for a in (ClaudeCodeAdapter(), CursorAdapter(), CodexAdapter())
        for f in a.render(packaged_request()).files
    ]

    assert first == second


# --- one-command-setup, phase P-2: family references (AC-5) and the bundled skills' files (AC-6) -
# Every test cites its `expected_behavior_source`: AC-n is a criterion of phase P-2 in
# docs/design/one-command-setup/plan.yaml, ADR-006 is adr-006-*.md under
# docs/design/one-command-setup/design/, and "the interface" is the one that the Coder gave for
# P-2: `ClientSkill.family_references` maps a family (`claude`, `agents`, `copilot`) to a text that
# `load_skills` reads unchanged from `skills/<name>/families/<family>.md`; the renderer writes the
# client's family as `references/dispatch.md`, built like a reference, after the other references,
# with the input id `skills/<name>/families/<family>.md`.
FAMILIES = ("agents", "claude", "copilot")
FAMILY_TEXT = {
    "claude": "Dispatch for Claude Code.\r\nUse its subagents.",
    "agents": "Dispatch for Cursor and Codex.\n",
    "copilot": "Dispatch for Copilot.\n",
}
CLIENT_BASES = {
    "claude-code": ".claude/skills",
    "cursor": ".agents/skills",
    "codex": ".agents/skills",
}
CLIENT_ADAPTERS: tuple[InstructionAdapter, ...] = (
    ClaudeCodeAdapter(),
    CursorAdapter(),
    CodexAdapter(),
)


def family_skill() -> ClientSkill:
    """SKILL with the three families."""
    return dataclasses.replace(SKILL, family_references=FAMILY_TEXT)


def family_file_text(text: str) -> str:
    """A family reference as the interface builds it: the text of a normal reference."""
    return f"{GENERATED_NOTICE}\n\n{normalise_text(text)}"


@pytest.mark.parametrize(
    ("render", "base", "family"),
    [(claude_skill_files, ".claude", "claude"), (agents_skill_files, ".agents", "agents")],
    ids=["claude", "agents"],
)
def test_ac5_the_family_of_the_client_renders_as_dispatch_md_after_the_other_references(
    render: Callable[[ClientSkill], tuple[RenderedFile, ...]], base: str, family: str
) -> None:
    """AC-5. expected_behavior_source: AC-5 (`families/claude.md` renders as
    `.claude/skills/<name>/references/dispatch.md`, `families/agents.md` as
    `.agents/skills/<name>/references/dispatch.md`); ADR-006 decision 2 (client references chosen
    per adapter); the interface (built like a reference, last, Orqlet-owned and protected, input
    id `skills/<name>/families/<family>.md`)."""
    files = render(family_skill())

    assert [str(f.path) for f in files] == [
        f"{base}/skills/orqlet-sample/SKILL.md",
        f"{base}/skills/orqlet-sample/references/notes.md",
        f"{base}/skills/orqlet-sample/references/dispatch.md",
    ]
    dispatch = files[-1]
    text = family_file_text(FAMILY_TEXT[family])
    assert dispatch.content == text.encode("utf-8")
    assert dispatch.owner is OwnerMode.ORQLET
    assert dispatch.file_class is FileClass.PROTECTED
    assert dispatch.inputs == (
        (
            f"skills/orqlet-sample/families/{family}.md",
            SKILL.inputs[0][1],
            sha256_hex(text.encode("utf-8")),
        ),
    )
    assert files[:2] == render(SKILL)


def test_ac5_no_family_file_renders_for_another_family() -> None:
    """AC-5. expected_behavior_source: AC-5 ("no family file renders for another family") and the
    interface (`copilot` renders for no current client; Copilot arrives in P-8): neither folder
    holds the text of another family, and a skill whose only family is `copilot` renders as one
    without families."""
    contents = {
        "claude": [f.content for f in claude_skill_files(family_skill())],
        "agents": [f.content for f in agents_skill_files(family_skill())],
    }
    for family, rendered in contents.items():
        for other in FAMILIES:
            if other != family:
                assert family_file_text(FAMILY_TEXT[other]).encode("utf-8") not in rendered

    only_copilot = dataclasses.replace(SKILL, family_references={"copilot": "Copilot only.\n"})
    assert claude_skill_files(only_copilot) == claude_skill_files(SKILL)
    assert agents_skill_files(only_copilot) == agents_skill_files(SKILL)


def test_ac5_a_skill_without_families_renders_exactly_as_before() -> None:
    """AC-5. expected_behavior_source: AC-5 ("A skill without families renders exactly as
    before"): the default is no family, and the files, their order and their bytes are those of the
    base revision (SKILL.md and one reference built as GENERATED_NOTICE, a blank line, the text)."""
    assert dict(SKILL.family_references) == {}
    claude = claude_skill_files(SKILL)

    assert [str(f.path) for f in claude] == [
        ".claude/skills/orqlet-sample/SKILL.md",
        ".claude/skills/orqlet-sample/references/notes.md",
    ]
    assert claude[1].content == f"{GENERATED_NOTICE}\n\nNotes\n".encode()
    assert claude[1].inputs == (
        (
            "skills/orqlet-sample/references/notes.md",
            "0.2.0",
            sha256_hex(f"{GENERATED_NOTICE}\n\nNotes\n".encode()),
        ),
    )
    assert claude_skill_files(dataclasses.replace(SKILL, family_references={})) == claude
    assert [f.content for f in agents_skill_files(SKILL)] == [f.content for f in claude]


SAMPLE_SOURCE = "---\nname: orqlet-sample\ndescription: A sample\n---\n# Sample\n\n1. Do it.\n"
# Family text is plain text: no front matter and no step rendering, so a marker line stays.
SAMPLE_FAMILY = "Run the extraction. <!-- requires: no-such-command -->\n1. kept\n"


def sample_workflow(families: dict[str, str]) -> TemplatedWorkflow:
    return TemplatedWorkflow(
        {
            "skills/orqlet-sample/skill.md": SAMPLE_SOURCE,
            "skills/orqlet-sample/references/notes.md": "Notes\n",
            **{f"skills/orqlet-sample/families/{name}": text for name, text in families.items()},
        }
    )


def sample_skill(families: dict[str, str]) -> ClientSkill:
    skills = load_skills(sample_workflow(families), IMPLEMENTED_COMMANDS)
    return next(skill for skill in skills if skill.name == "orqlet-sample")


def test_ac5_load_skills_reads_each_family_file_unchanged_and_not_as_a_reference() -> None:
    """AC-5. expected_behavior_source: AC-5 (`ClientSkill` gains `family_references` keyed by the
    families) and the interface (`load_skills` reads `families/<family>.md` as plain text, with no
    front matter and no step rendering; family files are not part of `references`)."""
    skill = sample_skill({"claude.md": SAMPLE_FAMILY, "agents.md": "Agents.\n"})

    assert skill.references == (("notes.md", "Notes\n"),)
    assert dict(skill.family_references) == {"agents": "Agents.\n", "claude": SAMPLE_FAMILY}


def test_ac5_a_skill_without_a_families_folder_has_no_family_reference() -> None:
    """AC-5. expected_behavior_source: AC-5 ("A skill without families renders exactly as
    before") and the interface."""
    assert dict(sample_skill({}).family_references) == {}


@pytest.mark.parametrize("name", ["vscode.md", "Claude.md", "copilot-chat.md", "codex.md"])
def test_ac5_a_family_file_outside_the_three_families_is_a_release_defect(name: str) -> None:
    """AC-5. expected_behavior_source: AC-5 (the families `claude`, `agents` and `copilot`) and
    the interface (a family file whose name is not one of the three raises `SourceError`)."""
    with pytest.raises(SourceError):
        sample_skill({name: "Text.\n"})


def test_ac5_only_graphify_has_family_references_and_it_has_the_three_families() -> None:
    """AC-5. expected_behavior_source: plan P-2 file operations (graphify's `families/claude.md`,
    `families/agents.md` and `families/copilot.md`; no other skill has a families folder)."""
    skills = {skill.name: skill for skill in packaged_request().skills}

    assert set(skills["graphify"].family_references) == set(FAMILIES)
    assert all(text.strip() for text in skills["graphify"].family_references.values())
    assert {name for name, s in skills.items() if s.family_references} == {"graphify"}


def test_ac5_graphify_dispatch_md_is_its_client_family_and_cursor_and_codex_share_the_bytes() -> (
    None
):
    """AC-5. expected_behavior_source: AC-5 (`families/claude.md` renders as
    `.claude/skills/graphify/references/dispatch.md` for Claude Code, `families/agents.md` as
    `.agents/skills/graphify/references/dispatch.md` for Cursor and Codex with the same bytes, and
    no family file renders for another family); the interface (copilot renders for no client)."""
    source = {
        family: WORKFLOW.read_text(f"skills/graphify/families/{family}.md") for family in FAMILIES
    }
    request = packaged_request()
    rendered = {
        adapter.client_id: {str(f.path): f.content for f in adapter.render(request).files}
        for adapter in CLIENT_ADAPTERS
    }
    claude = rendered["claude-code"][".claude/skills/graphify/references/dispatch.md"]
    cursor = rendered["cursor"][".agents/skills/graphify/references/dispatch.md"]
    codex = rendered["codex"][".agents/skills/graphify/references/dispatch.md"]

    assert claude == family_file_text(source["claude"]).encode("utf-8")
    assert cursor == codex == family_file_text(source["agents"]).encode("utf-8")
    copilot = family_file_text(source["copilot"]).encode("utf-8")
    for client, files in rendered.items():
        dispatch = [path for path in files if path.endswith("/references/dispatch.md")]
        assert dispatch == [f"{CLIENT_BASES[client]}/graphify/references/dispatch.md"], client
        if source["copilot"] not in (source["claude"], source["agents"]):
            assert copilot not in files.values(), client


@pytest.mark.parametrize("adapter", CLIENT_ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_ac6_each_client_gets_30_files_of_the_bundled_skills_in_render_order(
    adapter: InstructionAdapter,
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("30 skill files per client"); the interface (graphify
    SKILL.md, 10 references and dispatch.md; six ponytail skills with SKILL.md, LICENSE.md and
    PROVENANCE.md; dispatch.md after the other references)."""
    base = CLIENT_BASES[adapter.client_id]
    prefixes = tuple(f"{base}/{name}/" for name in BUNDLED_SKILL_NAMES)
    paths = [
        str(f.path)
        for f in adapter.render(packaged_request()).files
        if str(f.path).startswith(prefixes) and not str(f.path).endswith("/agents/openai.yaml")
    ]

    assert len(paths) == 30
    assert paths == skill_files(base, BUNDLED_SKILL_NAMES)


def test_ac6_codex_gets_a_sidecar_for_each_of_the_seven_bundled_skills() -> None:
    """AC-6, AC-1. expected_behavior_source: AC-6 ("the 7 Codex `agents/openai.yaml` sidecars"),
    AC-1 ("none is marked as a skill the agent may start") and ADR-006 decision 3 (the bundled
    skills render as the other packaged skills do)."""
    rendered = CodexAdapter().render(packaged_request()).files
    files = {str(f.path): f.content.decode() for f in rendered}
    sidecars = {
        path: text
        for path, text in files.items()
        if path.endswith("/agents/openai.yaml") and path.split("/")[2] in BUNDLED_SKILL_NAMES
    }

    assert set(sidecars) == {f".agents/skills/{n}/agents/openai.yaml" for n in BUNDLED_SKILL_NAMES}
    for path, text in sidecars.items():
        assert "allow_implicit_invocation: false" in text, path


def test_ac1_no_bundled_skill_may_be_started_by_the_agent() -> None:
    """AC-1. expected_behavior_source: AC-1 ("none is marked as a skill the agent may start") and
    ADR-006 decision 3: each renders `disable-model-invocation: true` for Claude Code and
    Cursor."""
    skills = {skill.name: skill for skill in packaged_request().skills}
    for name in BUNDLED_SKILL_NAMES:
        assert not skills[name].agent_may_start, name
        for files in (claude_skill_files(skills[name]), agents_skill_files(skills[name])):
            assert "disable-model-invocation: true" in files[0].content.decode().splitlines(), name
