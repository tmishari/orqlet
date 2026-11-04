"""Every file that each client adapter renders parses in its format and holds no template text.

Task phase-skill-contracts, phase P-1, AC-5. Every test cites its `expected_behavior_source`:
BC-30 is a behaviour criterion of docs/design/phase-skill-contracts/design/component.md, ADR-005 is
docs/design/phase-skill-contracts/design/adr-005-injection-unchanged-tests-and-version.md, U-12 and
A-57 are entries of docs/design/phase-skill-contracts/as-is.md, and AC-5 is the criterion of phase
P-1 in docs/design/phase-skill-contracts/plan.yaml.

These tests were written by the Tester of phase P-1, before any workflow text changes. The adapters
and the requests exist, so they describe the base and are expected to pass at once; the later
phases that rewrite skills, references and roles must keep them passing without an edit.

Choices:
- A file's format is chosen by the suffix of its name. `.md` and `.mdc` (Cursor's rule files) are
  Markdown: when the text opens with a `---` line, its front matter runs to the next `---` line and
  is read with the strict YAML loader. `.toml` is read with tomllib, `.yaml` and `.yml` with the
  strict YAML loader and `.json` with json. A suffix outside this list fails the test, because a
  file whose format is not known cannot be shown to parse.
- The request with one integration is the packaged request with a declaration of one server: the
  valid fixture tests/fixtures/contracts/valid/orqlet.integrations.v1.yaml, with its server moved to
  the one pair that the closed table enables (the Atlassian address for Claude Code), which is the
  only declaration for which an adapter writes a file (`.mcp.json`). No request goes to the address.

Deliberately not pinned: which Markdown files carry front matter and which keys it holds (BC-1 and
tests/unit/render/test_front_matter_views.py pin those), the angle-bracket slots such as `<task>`
that the agent fills when it runs (ADR-005 decision 1, U-12), and the number and names of the files.
"""

from __future__ import annotations

import dataclasses
import json
import tomllib
from collections.abc import Callable
from functools import cache
from pathlib import PurePosixPath
from typing import Any

import pytest

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.integrations import Integrations
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.instruction_adapter import InstructionAdapter, RenderRequest
from tests.support.render import packaged_request, resources_request
from tests.support.trees import FIXTURES

pytestmark = pytest.mark.unit

LOADER = StrictYamlLoader()
ADAPTERS: list[InstructionAdapter] = [ClaudeCodeAdapter(), CodexAdapter(), CursorAdapter()]
FENCE = "---\n"
MARKDOWN = frozenset({".md", ".mdc"})
YAML = frozenset({".yaml", ".yml"})
# The text that rendering must never leave behind: template braces and unrendered step markers.
UNRESOLVED = ("{{", "}}", "<!-- requires:", "<!-- unless:")
INTEGRATIONS_FIXTURE = FIXTURES / "contracts" / "valid" / "orqlet.integrations.v1.yaml"
ENABLED_ADDRESS = "https://mcp.atlassian.com/v2/mcp"  # the one address of the closed table
ENABLED_ID = "atlassian"


@cache
def one_integration() -> Integrations:
    """The valid declaration, its one server moved to the pair that the closed table enables."""
    data: Any = LOADER.load(INTEGRATIONS_FIXTURE.read_bytes(), source="fixture")
    (server,) = data["servers"]
    server["id"] = ENABLED_ID
    server["identity"] = {"kind": "remote", "url": ENABLED_ADDRESS}
    server["registration"]["name"] = f"orqlet-{ENABLED_ID}"
    data["roles"] = {"architecture-reviewer": {"servers": [ENABLED_ID]}}
    return Integrations.model_validate(data)


def one_integration_request() -> RenderRequest:
    return dataclasses.replace(packaged_request(), integrations=one_integration())


REQUESTS: dict[str, Callable[[], RenderRequest]] = {
    "packaged": packaged_request,
    "resources": resources_request,
    "one-integration": one_integration_request,
}


def front_matter(text: str, source: str) -> bool:
    """Read the front matter of a Markdown text; `False` when the text has none."""
    if not text.startswith(FENCE):
        return False
    end = text.find("\n" + FENCE, len(FENCE) - 1)
    if end < 0:
        raise ValueError("the front matter has no closing `---` line")
    parsed = LOADER.load(text[len(FENCE) : end + 1].encode("utf-8"), source=source)
    if not isinstance(parsed, dict):
        raise ValueError("the front matter is not a mapping")
    return True


def parsed_format(path: str, content: bytes) -> str | None:
    """Parse one rendered file in the format of its name and say which format that was.

    `None` is a Markdown file without front matter. A file that does not parse raises.
    """
    text = content.decode("utf-8")
    suffix = PurePosixPath(path).suffix
    if suffix in MARKDOWN:
        return "front matter" if front_matter(text, path) else None
    if suffix == ".toml":
        tomllib.loads(text)
        return "toml"
    if suffix in YAML:
        LOADER.load(content, source=path)
        return "yaml"
    if suffix == ".json":
        json.loads(text)
        return "json"
    raise ValueError(f"no format is known for the suffix {suffix!r}")


def format_problems(adapter: InstructionAdapter, request: RenderRequest) -> dict[str, str]:
    """Why each file that does not parse in its format fails, by path."""
    problems: dict[str, str] = {}
    for rendered in adapter.render(request).files:
        try:
            parsed_format(str(rendered.path), rendered.content)
        except (DocumentError, ValueError) as error:
            problems[str(rendered.path)] = str(error)
    return problems


@pytest.mark.parametrize("request_name", list(REQUESTS))
@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_bc30_every_rendered_file_parses_in_its_format(
    adapter: InstructionAdapter, request_name: str
) -> None:
    """AC-5. expected_behavior_source: BC-30 ("Every file that each client adapter renders parses
    in its format (YAML front matter, TOML, YAML sidecar, JSON)"), AC-5 (the strict YAML loader for
    front matter and YAML, tomllib for TOML, json for JSON; the packaged request, the resources
    request and a request with one integration) and A-57 (the Codex TOML roles and sidecars were
    checked only by golden bytes and substrings)."""
    request = REQUESTS[request_name]()

    assert adapter.render(request).files
    assert format_problems(adapter, request) == {}


@pytest.mark.parametrize("request_name", list(REQUESTS))
@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda adapter: adapter.client_id)
def test_bc30_no_rendered_file_holds_template_braces_or_step_markers(
    adapter: InstructionAdapter, request_name: str
) -> None:
    """AC-5. expected_behavior_source: BC-30 ("none contains `{{`, `}}`, `<!-- requires:` or
    `<!-- unless:`"), ADR-005 decision 1 (the check looks for template braces and unrendered step
    markers, not for angle brackets) and U-12 (no check scanned rendered files for them)."""
    files = adapter.render(REQUESTS[request_name]()).files

    found = {
        str(rendered.path): [
            text for text in UNRESOLVED if text.encode("utf-8") in rendered.content
        ]
        for rendered in files
    }

    assert files
    assert {path: texts for path, texts in found.items() if texts} == {}


def test_bc30_the_three_requests_reach_every_format_that_the_criterion_names() -> None:
    """AC-5. expected_behavior_source: AC-5 (front matter, `.toml`, `.yaml` or `.yml`, `.json`)
    and BC-30: the requests above give each adapter files of every format the criterion names, so
    the parse test is not passed by a format that no request renders."""
    seen = {
        parsed_format(str(rendered.path), rendered.content)
        for adapter in ADAPTERS
        for make_request in REQUESTS.values()
        for rendered in adapter.render(make_request()).files
    }

    assert {"front matter", "toml", "yaml", "json"} <= seen


def test_bc30_the_request_with_one_integration_declares_one_server_that_claude_code_writes() -> (
    None
):
    """AC-5. expected_behavior_source: AC-5 ("a request with one integration") and the
    mcp-or-plugins design that tests/unit/application/test_render_integrations.py pins (ADR-003
    decision 4: the Claude Code adapter writes `.mcp.json` for a server registered for it)."""
    request = one_integration_request()

    assert request.integrations is not None
    assert len(request.integrations.servers) == 1
    paths = {str(rendered.path) for rendered in ClaudeCodeAdapter().render(request).files}
    assert ".mcp.json" in paths
