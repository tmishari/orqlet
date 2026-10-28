"""Edge cases of the rule and instruction renderers that the golden files do not show."""

from __future__ import annotations

import pytest

from orqlet.adapters.render.instructions import agents_block, claude_import_block
from orqlet.adapters.render.rules import claude_rule, cursor_rule
from orqlet.application.ports.instruction_adapter import RenderRequest, ScopedRule
from orqlet.application.usecases.render_request import (
    RenderRequestError,
    build_render_request,
    rule_slug,
)
from orqlet.domain.blocks import parse_blocks
from orqlet.domain.ownership import FileClass
from orqlet.domain.resolver import Level
from tests.support.render import EMPTY_RESOURCES, SAMPLE_RULES, packaged_request

pytestmark = pytest.mark.unit


def rule(name: str = "demo", paths: tuple[str, ...] = ("src/**",)) -> ScopedRule:
    return ScopedRule(name, "A rule", paths, "Body.\n", FileClass.GENERATED)


@pytest.mark.parametrize("name", ["Upper", "has space", "../escape", "", "-lead", "dot.name"])
def test_a_rule_name_that_is_not_a_plain_slug_is_refused(name: str) -> None:
    with pytest.raises(ValueError, match="file name"):
        claude_rule(rule(name=name))
    with pytest.raises(ValueError, match="file name"):
        cursor_rule(rule(name=name))


def test_a_rule_without_paths_is_refused_because_it_would_always_load() -> None:
    with pytest.raises(ValueError, match="no paths"):
        claude_rule(rule(paths=()))


def test_awkward_paths_and_descriptions_are_quoted_not_interpreted() -> None:
    odd = ScopedRule(
        "odd", 'Say "hi": now # ok', ("a: b/**", "- x", "#y"), "Body", FileClass.GENERATED
    )

    claude = claude_rule(odd).content.decode()
    cursor = cursor_rule(odd).content.decode()

    assert '  - "a: b/**"' in claude
    assert '  - "- x"' in claude
    assert 'description: "Say \\"hi\\": now # ok"' in cursor


def test_rule_files_are_orqlet_owned_and_keep_their_class() -> None:
    generated = claude_rule(rule())
    protected = claude_rule(
        ScopedRule("p", "d", ("a",), "b", FileClass.PROTECTED, inputs=(("x", "1", "0" * 64),))
    )

    assert generated.file_class is FileClass.GENERATED
    assert protected.file_class is FileClass.PROTECTED
    assert protected.inputs == (("x", "1", "0" * 64),)


def test_the_agents_block_records_the_workflow_version_and_a_hash_of_its_body() -> None:
    block = agents_block(RenderRequest(workflow_version="1.2.3", baseline_body="Text\r\n"))

    (parsed,) = parse_blocks(block.content.decode())
    assert parsed.name == "baseline"
    assert parsed.info.startswith("workflow@1.2.3#")
    assert parsed.body == "Text"
    assert block.block is not None
    assert block.block[0] in block.content.decode()


@pytest.mark.parametrize("path", ["@AGENTS.md", "@../AGENTS.md"])
def test_the_claude_import_block_accepts_only_the_two_known_imports(path: str) -> None:
    text = claude_import_block(import_path=path)

    (parsed,) = parse_blocks(text)
    assert parsed.name == "claude-import"
    assert parsed.body == path


@pytest.mark.parametrize("path", ["@/etc/passwd", "@../../x", "AGENTS.md", ""])
def test_any_other_import_is_refused(path: str) -> None:
    with pytest.raises(ValueError, match="import"):
        claude_import_block(import_path=path)


def test_only_must_rules_with_paths_are_written_and_names_come_from_ids() -> None:
    request = packaged_request()

    assert [r.name for r in request.scoped_rules] == ["workflow", "sample-001"]
    assert rule_slug("PY_001.a") == "py-001-a"


def test_two_rules_that_would_share_a_file_name_are_an_error() -> None:
    from dataclasses import replace

    first = SAMPLE_RULES[0]
    clash = replace(first, id="sample_001")

    with pytest.raises(RenderRequestError, match="reuse the file name"):
        _build([first, clash])


def test_a_rule_id_without_letters_or_digits_cannot_name_a_file() -> None:
    with pytest.raises(RenderRequestError):
        rule_slug("---")


def test_a_should_rule_is_never_written_as_a_file() -> None:
    should_only = [r for r in SAMPLE_RULES if r.level is Level.SHOULD]

    assert [r.name for r in _build(should_only).scoped_rules] == ["workflow"]


def _build(rules: list) -> RenderRequest:  # type: ignore[type-arg]
    from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
    from orqlet.adapters.workflow_package import PackagedWorkflow

    return build_render_request(
        PackagedWorkflow(), StrictYamlLoader(), rules, EMPTY_RESOURCES, None
    )
