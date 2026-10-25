"""The front matter of every generated skill, agent and command reads the same in both views.

Cursor read the quotes of `name: "orqlet-inventory"` as part of the name, while a YAML parser reads
`orqlet-inventory`. These tests compare the two views for every file that the renderers produce
(harness2-fit, phase P-4).

Every test cites its `expected_behavior_source`. ADR-001 is
docs/design/harness2-fit/design/adr-001-client-visible-front-matter.md; AC-1 to AC-4 are the
acceptance criteria of phase P-4 in docs/design/harness2-fit/plan.yaml.

Deliberately not pinned, because the design leaves it open: strings inside lists or mappings under
the keyword, the wording of the difference messages and the order of keys. Messages are only
checked for their number and for the keys that they name.
"""

from __future__ import annotations

import re
import string
from collections.abc import Mapping, Sequence

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.emit import Data, front_matter
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.instruction_adapter import InstructionAdapter
from orqlet.application.usecases.validation import split_front_matter
from orqlet.domain.front_matter import front_matter_differences, simple_front_matter
from tests.support.render import packaged_request
from tests.unit.render.test_emit import AWKWARD, PLAIN_SAFE_STRINGS

pytestmark = pytest.mark.unit

LOADER = StrictYamlLoader()
ALL_ADAPTERS: list[InstructionAdapter] = [ClaudeCodeAdapter(), CursorAdapter(), CodexAdapter()]
ADAPTERS = {adapter.client_id: adapter for adapter in ALL_ADAPTERS}

# The three kinds of file of ADR-001 decision 3, chosen by path. `[^/]+` is one name of the path.
PATH_CLASSES = {
    "skill": re.compile(r"[^/]+/skills/[^/]+/SKILL\.md"),
    "agent": re.compile(r"[^/]+/agents/[^/]+\.md"),
    "command": re.compile(r"\.claude/commands/[^/]+\.md"),
}

# Which classes each client produces, from the Context of ADR-001: Cursor commands have no front
# matter and Codex roles are TOML files, so neither is a class of that client.
PRODUCED = [
    pytest.param("claude-code", "skill", id="claude-code-skills"),
    pytest.param("claude-code", "agent", id="claude-code-agents"),
    pytest.param("claude-code", "command", id="claude-code-commands"),
    pytest.param("cursor", "skill", id="cursor-skills"),
    pytest.param("cursor", "agent", id="cursor-agents"),
    pytest.param("codex", "skill", id="codex-skills"),
]


def rendered_texts(client: str, path_class: str) -> dict[str, str]:
    """The files of one path class that a client's renderers produce, by path."""
    files = ADAPTERS[client].render(packaged_request()).files
    pattern = PATH_CLASSES[path_class]
    return {str(f.path): f.content.decode("utf-8") for f in files if pattern.fullmatch(str(f.path))}


def parsed_by_the_strict_loader(block: str, source: str) -> Mapping[str, object]:
    parsed = LOADER.load(block.encode("utf-8"), source=source)
    assert isinstance(parsed, dict), source
    return parsed


def front_matter_problems(path: str, text: str) -> tuple[str, ...]:
    """What the release check reports for one file: no block, a block that does not parse, or
    the keys on which the line view and the parsed view differ."""
    split = split_front_matter(text)
    if split is None:
        return ("there is no front-matter block",)
    block = split[0]
    try:
        parsed = LOADER.load(block.encode("utf-8"), source=path)
    except DocumentError as error:
        return (f"the block does not parse: {error}",)
    if not isinstance(parsed, dict):
        return ("the block is not a mapping",)
    return front_matter_differences(simple_front_matter(block), parsed)


# --- AC-1: every rendered skill, agent and Claude Code command ---------------------------------


@pytest.mark.parametrize(("client", "path_class"), PRODUCED)
def test_a_client_yields_files_of_every_path_class_it_produces(
    client: str, path_class: str
) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 3 (files are chosen by path)."""
    assert rendered_texts(client, path_class)


@pytest.mark.parametrize(("client", "path_class"), PRODUCED)
def test_the_line_view_and_the_parsed_view_agree_for_every_rendered_file(
    client: str, path_class: str
) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 3 (the block exists, parses, and agrees)."""
    texts = rendered_texts(client, path_class)

    problems = {path: front_matter_problems(path, text) for path, text in texts.items()}

    assert texts
    assert {path: found for path, found in problems.items() if found} == {}


@pytest.mark.parametrize(
    "text",
    ["# A skill with no block\n", "", "name: x\n---\n", "---\nname: x\n"],
    ids=["no-fence", "empty", "no-opening-fence", "no-closing-fence"],
)
def test_a_file_without_a_front_matter_block_is_a_problem(text: str) -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 3 (it asserts that the block exists)."""
    assert front_matter_problems("fixture.md", text)


def test_a_block_that_does_not_parse_is_a_problem() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 3 (the test asserts that it parses)."""
    assert front_matter_problems("fixture.md", "---\nname: [unclosed\n---\nBody\n")


def test_a_block_whose_two_views_differ_is_a_problem() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 3 (differences must be empty)."""
    assert front_matter_problems("fixture.md", '---\nname: "orqlet-sample"\n---\nBody\n')


def test_a_block_whose_two_views_agree_is_no_problem() -> None:
    """AC-1. expected_behavior_source: ADR-001 decision 3 (differences must be empty)."""
    assert front_matter_problems("fixture.md", "---\nname: orqlet-sample\n---\nBody\n") == ()


# --- AC-2: the check catches a return of the quoting defect ------------------------------------

QUOTED_BLOCK = 'name: "orqlet-sample"\nmodel: "inherit"\ntools: "Read, Grep, Glob"\n'
PLAIN_BLOCK = "name: orqlet-sample\nmodel: inherit\ntools: Read, Grep, Glob\n"


def test_quoted_name_model_and_tools_are_three_differences() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 3 (every key is compared, `tools` too)."""
    parsed = parsed_by_the_strict_loader(QUOTED_BLOCK, "fixture")

    messages = front_matter_differences(simple_front_matter(QUOTED_BLOCK), parsed)

    assert len(messages) == 3
    for key in ("name", "model", "tools"):
        assert any(key in message for message in messages), key


def test_the_same_three_values_unquoted_are_no_difference() -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 3 (the plain forms are what must agree)."""
    parsed = parsed_by_the_strict_loader(PLAIN_BLOCK, "fixture")

    assert front_matter_differences(simple_front_matter(PLAIN_BLOCK), parsed) == ()


def front_matter_without_the_keyword(
    fields: Sequence[tuple[str, Data]], *, plain_when_safe: bool = False
) -> str:
    """The emitter as the renderers used it before the fix: their request for plain values is lost.

    It calls the original `front_matter` imported above; `monkeypatch` replaces only the names
    inside the renderer modules.
    """
    return front_matter(fields)


@pytest.fixture
def quoting_defect(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in ("skills", "roles"):
        monkeypatch.setattr(
            f"orqlet.adapters.render.{module}.front_matter", front_matter_without_the_keyword
        )


@pytest.mark.parametrize(
    ("client", "path_class"),
    [
        pytest.param("claude-code", "skill", id="skill"),
        pytest.param("claude-code", "agent", id="claude-code-role"),
        pytest.param("cursor", "agent", id="cursor-role"),
    ],
)
def test_the_whole_check_goes_red_when_the_quoting_defect_returns(
    client: str, path_class: str, quoting_defect: None
) -> None:
    """AC-2. expected_behavior_source: ADR-001 decision 3 (a return of the defect fails it)."""
    texts = rendered_texts(client, path_class)

    assert texts
    for path, text in texts.items():
        problems = front_matter_problems(path, text)
        assert any("name" in problem for problem in problems), path


# --- AC-3: a string written bare reads the same in every reader --------------------------------


def bare_block(value: str) -> str | None:
    """The block that `front_matter` writes for `key`, or `None` when the value is quoted."""
    text = front_matter([("key", value)], plain_when_safe=True)
    if text != f"---\nkey: {value}\n---\n":
        return None
    split = split_front_matter(text)
    assert split is not None
    return split[0]


def assert_every_reader_agrees(value: str) -> None:
    """The strict loader, PyYAML's safe loader (YAML 1.1) and the line view return `value`.

    A value written quoted says nothing: the check is for the bare ones only.
    """
    block = bare_block(value)
    if block is None:
        return
    assert LOADER.load(block.encode("utf-8"), source="fixture") == {"key": value}
    assert yaml.safe_load(block) == {"key": value}
    assert simple_front_matter(block) == {"key": value}


def test_the_cross_reader_checks_have_bare_strings_to_check() -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 1 (a string of letters is written bare).

    A precondition, not a rule: if the emitter quoted these strings, the tests below would pass
    without comparing anything.
    """
    assert bare_block("plain") is not None
    assert [value for value in PLAIN_SAFE_STRINGS if bare_block(value) is None] == []


@pytest.mark.parametrize("value", AWKWARD)
def test_every_reader_agrees_on_an_awkward_string_when_it_is_written_bare(value: str) -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 4 (the awkward strings of test_emit.py)."""
    assert_every_reader_agrees(value)


@pytest.mark.parametrize("value", PLAIN_SAFE_STRINGS)
def test_every_reader_agrees_on_a_plain_safe_string(value: str) -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 4 (strings that the allow-list accepts)."""
    assert_every_reader_agrees(value)


# `st.text()` almost never writes a bare value, so the second strategy is built to do so often:
# a letter, then letters, digits, spaces and the characters of the allow-list.
ALLOWED_TAIL = string.ascii_letters + string.digits + " ,.;()/_+=-'"
arbitrary_text = st.text(max_size=30)
plain_like_text = st.builds(
    "".join,
    st.tuples(st.sampled_from(string.ascii_letters), st.text(alphabet=ALLOWED_TAIL, max_size=30)),
)

# The third strategy takes plain-like text and puts one fragment that a reader may treat as syntax
# or as another type anywhere in it. It checks the boundary of what is written bare, whatever
# that boundary is: a fragment that gets through must be read the same by every reader.
SYNTAX_FRAGMENTS = [
    *':#"\\\t\n~<>[]{}*&!%@|?`^$',
    ": ",
    " #",
    "- ",
    "é",
    "\u0661",
    "\u2028",
    "\u00a0",
    "\u0085",
    "\ufeff",
    "\x00",
]


def with_fragment(text: str, fragment: str, at: int) -> str:
    return text[:at] + fragment + text[at:]


poisoned_text = st.builds(
    with_fragment, plain_like_text, st.sampled_from(SYNTAX_FRAGMENTS), st.integers(0, 31)
)


@given(arbitrary_text)
def test_every_reader_agrees_on_any_text_when_it_is_written_bare(value: str) -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 4 (a property test over arbitrary text)."""
    assert_every_reader_agrees(value)


@given(plain_like_text)
def test_every_reader_agrees_on_text_that_is_often_plain_safe(value: str) -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 4 (a property test over plain-like text)."""
    assert_every_reader_agrees(value)


@given(poisoned_text)
def test_every_reader_agrees_on_plain_like_text_with_a_syntax_fragment(value: str) -> None:
    """AC-3. expected_behavior_source: ADR-001 decision 4 (a property test at the boundary)."""
    assert_every_reader_agrees(value)
