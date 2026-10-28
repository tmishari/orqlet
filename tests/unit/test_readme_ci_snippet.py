"""The CI step in README.md that an adopter copies into a workflow (task team-conventions-resources,
phase P-7).

Every test cites its `expected_behavior_source`. ADR-003 is the file `adr-003-*.md` under
docs/design/team-conventions-resources/design/, S-n are the considerations of considerations.md,
and AC-1 to AC-6 are the acceptance criteria of phase P-7 in
docs/design/team-conventions-resources/plan.yaml. "The interface decision" is the reading of the
plan author that the Tester of phase P-7 was given, because the ADR does not spell it out: the
README holds one fenced `yaml` block whose first line is `name: orqlet-checks`; the tests below pin
that block, and these phrases of the README prose (exact, case sensitive, with line breaks read as
spaces): `two of the eight conventions`, `squash-merge title`, `storage-state`, ``raw diff of
`docs/resources` `` and `required status check`.

These tests were written first, by the Tester of phase P-7, before the README section existed. The
rules are small functions of the snippet text and of the YAML that the strict loader reads from it.
Each rule is also run on a reference snippet that obeys all of them, and on copies of it that each
break that rule, so that a rule that cannot fail would fail here (those tests pass before the
README is written).

Behaviour that the design leaves open is deliberately not pinned here:
- the order of the three steps, the runner, the version in the install line (only that it is not a
  moving name such as `main`), the names of the steps and the exact text around the block;
- the warning of considerations S-8 not to pipe the output into a job summary unescaped (the
  interface decision lists no phrase for it);
- how an adopter makes the step a required status check (the README only has to say that it must
  be one).
"""

from __future__ import annotations

import itertools
import re
import shlex
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.documents import DocumentError
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS

pytestmark = pytest.mark.unit

README = Path(__file__).resolve().parents[2] / "README.md"
FENCE = re.compile(r"^```ya?ml[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
FIRST_LINE = "name: orqlet-checks"
VALIDATE = "orqlet validate resources"
CONVENTIONS = 'orqlet conventions check --branch="$HEAD_REF" --base="origin/$BASE_REF"'
UPGRADE = "orqlet upgrade --check"
HEAD_REF_VALUE = "${{ github.head_ref }}"
BASE_REF_VALUE = "${{ github.base_ref }}"
INSTALL_SOURCE = "git+https://github.com/tmishari/orqlet@"
PINNED_ACTION = re.compile(r"uses: [\w./-]+@[0-9a-f]{40}(?:\s|$)")
MOVING_REFS = {"", "main", "master", "head", "latest", "develop"}
PHRASES = [
    "two of the eight conventions",
    "squash-merge title",
    "storage-state",
    "raw diff of " + "`docs/resources`",
    "required status check",
]

REFERENCE = """\
name: orqlet-checks

on:
  pull_request:

permissions:
  contents: read

jobs:
  orqlet:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
      - run: uv tool install "git+https://github.com/tmishari/orqlet@v0.1.0"
      - run: orqlet validate resources
      - run: orqlet conventions check --branch="$HEAD_REF" --base="origin/$BASE_REF"
        env:
          HEAD_REF: ${{ github.head_ref }}
          BASE_REF: ${{ github.base_ref }}
      - run: orqlet upgrade --check
"""


# --- reading the README ---------------------------------------------------------------------------


def snippets_of(text: str) -> list[str]:
    return [
        match.group(1)
        for match in FENCE.finditer(text)
        if match.group(1).split("\n", 1)[0].strip() == FIRST_LINE
    ]


def readme_snippet() -> str:
    found = snippets_of(README.read_text(encoding="utf-8"))
    if len(found) != 1:
        pytest.fail(
            f"README.md must hold exactly one yaml block whose first line is `{FIRST_LINE}`; "
            f"it holds {len(found)}"
        )
    return found[0]


def parsed(text: str) -> dict[str, Any] | None:
    """The block as the strict loader reads it, or `None` when it is not a mapping or not YAML."""
    try:
        document = StrictYamlLoader().load(text.encode("utf-8"), source="README.md")
    except DocumentError:
        return None
    return document if isinstance(document, dict) else None


def steps_of(document: dict[str, Any] | None) -> list[dict[str, Any]]:
    jobs = document.get("jobs") if document else None
    if not isinstance(jobs, dict):
        return []
    return [
        step
        for job in jobs.values()
        if isinstance(job, dict)
        for step in job.get("steps", [])
        if isinstance(step, dict)
    ]


def commands_of(document: dict[str, Any] | None) -> list[str]:
    return [step["run"] for step in steps_of(document) if isinstance(step.get("run"), str)]


def lines_of(text: str) -> list[str]:
    return text.splitlines()


def walk(node: object, path: tuple[object, ...] = ()) -> Iterator[tuple[tuple[object, ...], str]]:
    """Every string of the document with the keys and indexes that lead to it."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, item in node.items():
            yield from walk(item, (*path, key))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from walk(item, (*path, index))


def conventions_step_env(document: dict[str, Any] | None) -> dict[str, object]:
    """What the conventions step sees: the environment of the workflow, its job and its step."""
    if not document:
        return {}
    for job in (document.get("jobs") or {}).values():
        for step in job.get("steps", []):
            if step.get("run") == CONVENTIONS:
                return {
                    **(document.get("env") or {}),
                    **(job.get("env") or {}),
                    **(step.get("env") or {}),
                }
    return {}


# --- the rules ------------------------------------------------------------------------------------

Rule = Callable[[str, dict[str, Any] | None], bool]


def _trigger_is_pull_request(text: str, document: dict[str, Any] | None) -> bool:
    lines = [line.rstrip() for line in lines_of(text)]
    return any(a == "on:" and b == "  pull_request:" for a, b in itertools.pairwise(lines))


def _no_pull_request_target(text: str, document: dict[str, Any] | None) -> bool:
    return "pull_request_target" not in text


def _read_only_permissions(text: str, document: dict[str, Any] | None) -> bool:
    return "permissions:" in text and "contents: read" in text


def _no_write_permission(text: str, document: dict[str, Any] | None) -> bool:
    code = [line.split(" #")[0] for line in lines_of(text) if not line.lstrip().startswith("#")]
    return not any(re.search(r":\s*write\b|write-all", line) for line in code)


def _no_secrets(text: str, document: dict[str, Any] | None) -> bool:
    return re.search(r"\$\{\{\s*secrets\.", text) is None


def _credentials_not_persisted(text: str, document: dict[str, Any] | None) -> bool:
    return "persist-credentials: false" in text


def _full_history(text: str, document: dict[str, Any] | None) -> bool:
    return "fetch-depth: 0" in text


def _has_a_timeout(text: str, document: dict[str, Any] | None) -> bool:
    return "timeout-minutes:" in text


def _no_if(text: str, document: dict[str, Any] | None) -> bool:
    return not any(re.match(r"\s*(?:-\s+)?if:", line) for line in lines_of(text))


def _no_continue_on_error(text: str, document: dict[str, Any] | None) -> bool:
    return "continue-on-error" not in text


def _actions_are_pinned_to_a_commit(text: str, document: dict[str, Any] | None) -> bool:
    uses = [line for line in lines_of(text) if re.match(r"\s*(?:-\s+)?uses:", line)]
    return bool(uses) and all(PINNED_ACTION.search(line) for line in uses)


def _runs(command: str) -> Rule:
    def rule(text: str, document: dict[str, Any] | None) -> bool:
        return command in commands_of(document)

    return rule


def _refs_only_in_an_env_mapping(text: str, document: dict[str, Any] | None) -> bool:
    if document is None:
        return False
    hits = [
        (path, value)
        for path, value in walk(document)
        if "github.head_ref" in value or "github.base_ref" in value
    ]
    if not hits:
        return False
    for path, value in hits:
        expected = {"HEAD_REF": HEAD_REF_VALUE, "BASE_REF": BASE_REF_VALUE}.get(str(path[-1]))
        if "env" not in path or "run" in path or value != expected:
            return False
    env = conventions_step_env(document)
    return env.get("HEAD_REF") == HEAD_REF_VALUE and env.get("BASE_REF") == BASE_REF_VALUE


def _no_ref_in_a_run_line(text: str, document: dict[str, Any] | None) -> bool:
    if document is None:
        return False
    lines_with_run = [line for line in lines_of(text) if "run:" in line]
    return not any(
        "github.head_ref" in value or "github.base_ref" in value
        for value in [*commands_of(document), *lines_with_run]
    )


def _installs_the_pinned_version_before_it_is_used(
    text: str, document: dict[str, Any] | None
) -> bool:
    commands = commands_of(document)
    installs = [
        index
        for index, command in enumerate(commands)
        if "uv tool install" in command and INSTALL_SOURCE in command
    ]
    uses = [index for index, command in enumerate(commands) if command.startswith("orqlet ")]
    if not installs or not uses or installs[0] > uses[0]:
        return False
    reference = re.search(
        r"git\+https://github\.com/tmishari/orqlet@([^\s\"']*)", commands[installs[0]]
    )
    return reference is not None and reference.group(1).lower() not in MOVING_REFS


def _parses_and_has_one_job(text: str, document: dict[str, Any] | None) -> bool:
    jobs = document.get("jobs") if document else None
    return isinstance(jobs, dict) and len(jobs) == 1


def _is_named(text: str, document: dict[str, Any] | None) -> bool:
    return document is not None and document.get("name") == "orqlet-checks"


RULES: dict[str, tuple[Rule, str]] = {
    "the-trigger-is-pull-request": (_trigger_is_pull_request, "ADR-003 decision 5"),
    "no-pull-request-target": (_no_pull_request_target, "ADR-003 decision 5, S-15"),
    "permissions-are-contents-read": (_read_only_permissions, "ADR-003 decision 5, S-15"),
    "no-write-permission": (_no_write_permission, "ADR-003 decision 5 (contents: read only)"),
    "no-secrets": (_no_secrets, "ADR-003 decision 5, S-15 (no secrets)"),
    "credentials-are-not-persisted": (_credentials_not_persisted, "ADR-003 decision 5, S-15"),
    "the-checkout-has-full-history": (_full_history, "ADR-003 decision 5, S-15"),
    "the-job-has-a-timeout": (_has_a_timeout, "ADR-003 decision 5, S-15"),
    "no-if-at-job-or-step-level": (_no_if, "ADR-003 decision 5 (a skipped job counts as passed)"),
    "no-continue-on-error": (_no_continue_on_error, "ADR-003 decision 5, S-15"),
    "every-action-is-pinned-to-a-commit": (_actions_are_pinned_to_a_commit, "ADR-003 decision 5"),
    "validate-resources-is-a-step": (_runs(VALIDATE), "ADR-003 decision 5, S-15"),
    "conventions-check-is-a-step-in-the-equals-form": (_runs(CONVENTIONS), "ADR-003 decision 5"),
    "upgrade-check-is-a-step": (_runs(UPGRADE), "ADR-003 decision 5, S-15"),
    "the-refs-reach-the-script-through-env-only": (
        _refs_only_in_an_env_mapping,
        "ADR-003 decision 5, S-15 (never interpolated into a script)",
    ),
    "no-ref-in-a-run-line": (_no_ref_in_a_run_line, "ADR-003 decision 5, S-15"),
    "orqlet-is-installed-from-the-repository-at-a-pinned-version": (
        _installs_the_pinned_version_before_it_is_used,
        "ADR-003 decision 5 (the version that cli.pinned names, no published package)",
    ),
    "the-workflow-has-one-job": (_parses_and_has_one_job, "the interface decision"),
    "the-workflow-is-named": (_is_named, "the interface decision"),
}

MUTATIONS: dict[str, list[Callable[[str], str]]] = {
    "the-trigger-is-pull-request": [lambda t: t.replace("  pull_request:", "  push:")],
    "no-pull-request-target": [
        lambda t: t.replace("  pull_request:", "  pull_request:\n  pull_request_target:")
    ],
    "permissions-are-contents-read": [lambda t: t.replace("permissions:\n  contents: read\n", "")],
    "no-write-permission": [
        lambda t: t.replace("contents: read", "contents: read\n  id-token: write")
    ],
    "no-secrets": [
        lambda t: t.replace(
            "      - run: orqlet upgrade --check",
            "      - run: orqlet upgrade --check\n        env:\n          T: ${{ secrets.TOKEN }}",
        )
    ],
    "credentials-are-not-persisted": [
        lambda t: t.replace("persist-credentials: false", "persist-credentials: true"),
        lambda t: t.replace("          persist-credentials: false\n", ""),
    ],
    "the-checkout-has-full-history": [lambda t: t.replace("          fetch-depth: 0\n", "")],
    "the-job-has-a-timeout": [lambda t: t.replace("    timeout-minutes: 10\n", "")],
    "no-if-at-job-or-step-level": [
        lambda t: t.replace(
            "    runs-on: ubuntu-latest\n",
            "    runs-on: ubuntu-latest\n    if: github.event.pull_request.draft == false\n",
        ),
        lambda t: t.replace(
            "      - run: orqlet upgrade --check",
            "      - if: always()\n        run: orqlet upgrade --check",
        ),
    ],
    "no-continue-on-error": [
        lambda t: t.replace(
            "      - run: orqlet upgrade --check",
            "      - run: orqlet upgrade --check\n        continue-on-error: true",
        )
    ],
    "every-action-is-pinned-to-a-commit": [
        lambda t: t.replace("3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1", "v7"),
        lambda t: t.replace("@1c37ad07a6a961277cf70c0d37d6f313000f5884", "@main"),
        lambda t: t.replace("@3d3c42e5aac5ba805825da76410c181273ba90b1", "@3d3c42e"),
    ],
    "validate-resources-is-a-step": [
        lambda t: t.replace("- run: orqlet validate resources\n", ""),
        lambda t: t.replace("orqlet validate resources", "orqlet validate resources --json"),
    ],
    "conventions-check-is-a-step-in-the-equals-form": [
        lambda t: t.replace('--branch="$HEAD_REF"', '--branch "$HEAD_REF"'),
        lambda t: t.replace('--base="origin/$BASE_REF"', '--base="$BASE_REF"'),
        lambda t: t.replace("orqlet conventions check", "orqlet conventions"),
    ],
    "upgrade-check-is-a-step": [lambda t: t.replace("orqlet upgrade --check", "orqlet upgrade")],
    "the-refs-reach-the-script-through-env-only": [
        lambda t: t.replace(
            f"          HEAD_REF: {HEAD_REF_VALUE}\n          BASE_REF: {BASE_REF_VALUE}\n",
            "          HEAD_REF: main\n          BASE_REF: main\n",
        ),
        lambda t: t.replace('--branch="$HEAD_REF"', '--branch="${{ github.head_ref }}"'),
        lambda t: t.replace("        env:\n", "        with:\n"),
    ],
    "no-ref-in-a-run-line": [
        lambda t: t.replace('--branch="$HEAD_REF"', '--branch="${{ github.head_ref }}"'),
        lambda t: t.replace('--base="origin/$BASE_REF"', '--base="origin/${{ github.base_ref }}"'),
    ],
    "orqlet-is-installed-from-the-repository-at-a-pinned-version": [
        lambda t: t.replace("orqlet@v0.1.0", "orqlet@main"),
        lambda t: t.replace("orqlet@v0.1.0", "orqlet@"),
        lambda t: t.replace("git+https://github.com/tmishari/orqlet@v0.1.0", "orqlet"),
        lambda t: t.replace(
            '      - run: uv tool install "git+https://github.com/tmishari/orqlet@v0.1.0"\n', ""
        ).replace(
            "      - run: orqlet upgrade --check",
            '      - run: orqlet upgrade --check\n      - run: uv tool install "git+https://github.com/tmishari/orqlet@v0.1.0"',
        ),
    ],
    "the-workflow-has-one-job": [
        lambda t: t + "  second:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        lambda t: t.replace("  orqlet:\n", "  orqlet:\n  orqlet:\n"),
    ],
    "the-workflow-is-named": [lambda t: t.replace("name: orqlet-checks", "name: other")],
}


def rule_holds(name: str, text: str) -> bool:
    return RULES[name][0](text, parsed(text))


def broken_copies() -> list[tuple[str, int]]:
    return [
        (name, index) for name, mutations in MUTATIONS.items() for index in range(len(mutations))
    ]


# --- the rules themselves are sound ---------------------------------------------------------------


def test_every_rule_has_a_source_and_a_way_to_break_it() -> None:
    """AC-5. expected_behavior_source: plan P-7 AC-5 (a test pins the README step); this test keeps
    the rules and their broken copies in step. It passes before the README is written."""
    assert set(RULES) == set(MUTATIONS)
    assert all(source for _, source in RULES.values())


def test_the_reference_snippet_obeys_every_rule() -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 5 and considerations S-15 (the step as the
    ADR fixes it). It passes before the README is written."""
    broken = [name for name in RULES if not rule_holds(name, REFERENCE)]

    assert broken == []
    assert snippets_of(f"text\n```yaml\n{REFERENCE}```\n") == [REFERENCE]


@pytest.mark.parametrize(
    ("name", "index"), broken_copies(), ids=[f"{name}-{index}" for name, index in broken_copies()]
)
def test_a_rule_fails_on_a_snippet_that_breaks_it(name: str, index: int) -> None:
    """AC-5. expected_behavior_source: ADR-003 decision 5 and considerations S-15: each broken copy
    of the reference snippet breaks the rule it is named for. It passes before the README is
    written."""
    broken = MUTATIONS[name][index](REFERENCE)

    assert broken != REFERENCE
    assert not rule_holds(name, broken)


def test_a_block_that_is_not_yaml_obeys_no_structural_rule() -> None:
    """AC-5. expected_behavior_source: the interface decision ("the YAML parses with the strict
    loader"): an anchor, a duplicate key or a tab leaves no parsed document. It passes before the
    README is written."""
    for text in ("name: a\nname: b\n", "a: &x 1\nb: *x\n", "jobs: [\n"):
        assert parsed(text) is None


# --- the README -----------------------------------------------------------------------------------


def test_the_readme_holds_the_snippet_once() -> None:
    """AC-5. expected_behavior_source: the interface decision (the README holds a ```yaml fence
    whose first line is `name: orqlet-checks`) and plan P-7 (a section for adopters with the CI
    step of ADR-003 decision 5)."""
    assert readme_snippet().startswith(FIRST_LINE)


@pytest.mark.parametrize("name", list(RULES))
def test_the_readme_snippet_obeys_the_rule(name: str) -> None:
    """AC-5. expected_behavior_source: the source named in RULES for the rule (ADR-003 decision 5
    and considerations S-15), and the interface decision for the lines it pins."""
    assert rule_holds(name, readme_snippet()), f"{name} ({RULES[name][1]})"


def test_the_run_lines_of_the_snippet_are_implemented_commands() -> None:
    """AC-6. expected_behavior_source: EC-56 (IMPLEMENTED_COMMANDS gains `conventions check`) and
    the interface decision (every command of the README snippet's run lines is in
    IMPLEMENTED_COMMANDS: `validate resources`, `conventions check`, `upgrade`)."""
    document = parsed(readme_snippet())
    found: set[str] = set()
    for command in commands_of(document):
        words = shlex.split(command)
        if words[0] != "orqlet":
            continue
        names = []
        for word in words[1:]:
            if word.startswith("-"):
                break
            names.append(word)
        known = [
            " ".join(names[:size])
            for size in range(len(names), 0, -1)
            if " ".join(names[:size]) in IMPLEMENTED_COMMANDS
        ]
        assert known, f"`{command}` is not an implemented command"
        found.add(known[0])

    assert found == {"validate resources", "conventions check", "upgrade"}


@pytest.mark.parametrize("phrase", PHRASES)
def test_the_readme_says(phrase: str) -> None:
    """AC-5. expected_behavior_source: plan P-7 (README: "two of eight conventions are checked, ...
    a squash-merge title is outside the check, that stored copies and storage-state files stay out
    of Git, and that reviewers read the raw diff of docs/resources"), ADR-003 decisions 5 and 6
    (whether the step blocks a merge depends on a required status check) and the interface decision
    (the phrases, exact and case sensitive; a line break counts as a space)."""
    text = " ".join(README.read_text(encoding="utf-8").split())

    assert phrase in text
