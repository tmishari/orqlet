"""The guard of `_Builder._propose`: a proposal for an MCP file holds no byte of the existing file.

Task `mcp-or-plugins`, phase P-4. Every test cites its `expected_behavior_source`. ADR-003 is
docs/design/mcp-or-plugins/design/adr-003-build-order-and-seeded-files.md (decision 5 is "Seeded
file, no entry-level editing, and no copy of the team's text"), EC-14 is an expected change of the
manifest.yaml next to it, and AC-1 to AC-5 are the acceptance criteria of phase P-4 in
docs/design/mcp-or-plugins/plan.yaml.

These tests were written first, by the Tester of phase P-4, before the guard existed. They run at
the level of `build_plan` and the public domain types: the guard is private, so no test calls it.

The guard, as the design states it: when the path of a proposal is the MCP file of `claude-code`,
`codex` or `cursor` (`mcp_file_path`), compared on `CanonicalPath.key`, `_propose` passes no
existing bytes, so the proposal is a unified diff against nothing. The three paths are
`.mcp.json`, `.cursor/mcp.json` and `.codex/config.toml`. `_propose` has two call sites,
`whole_file` (a seeded proposal, or a stop) and `blocks` (a shared block that stops or is
proposed); the scenarios below reach each of them with each state that gives it a proposal.

A sentinel is a text that exists only in the team's file. It is assembled at run time from parts
and never written as one literal (ORQLET-SEC-003).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of a proposal's headers beyond what `build_plan` has always written (`a/<path>` and
  `b/<path>`, the path as it is spelled in the `Desired`); the expected texts are built with
  `difflib` from the same arguments, so they pin "a diff against nothing" and nothing more;
- what a `BlockError` puts in `PlannedItem.reason` (that branch does not call `_propose`, and
  the design does not cover it; see the QUESTIONS of the Tester's report);
- a plan that also updates a live block in the same MCP file (the design says it does not cover a
  profile that names an MCP path as a block target);
- whether `_MCP_CLIENTS` is a tuple, a list or a frozenset (the design says "a constant of client
  ids"; only its content is pinned).
"""

from __future__ import annotations

import ast
import difflib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import orqlet.domain.changeplan as changeplan
from orqlet.domain.blocks import render_block
from orqlet.domain.changeplan import (
    Action,
    ChangePlan,
    Desired,
    PlannedWrite,
    Recorded,
    build_plan,
    proposal_path,
)
from orqlet.domain.classify import FileState
from orqlet.domain.digest import sha256_hex
from orqlet.domain.mcp_credentials import mcp_file_path
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.python_api import extract_module_api

pytestmark = pytest.mark.unit

# --- the paths ------------------------------------------------------------------------------------

MCP_PATHS = (".mcp.json", ".cursor/mcp.json", ".codex/config.toml")
# AC-2: paths are compared on the case-folded key, so a case variant is the same MCP file.
CASE_VARIANTS = (".MCP.json", ".Cursor/mcp.json", ".CODEX/config.toml")
# U+017F (the long s) folds to "s". These two paths have the key of an MCP file and are spelled
# in a way that no `lower()` or `upper()` call turns into it: only the key compares them equal.
FOLD_VARIANTS = (".mcp.j\u017fon", ".cur\u017for/mcp.json")
GUARDED_PATHS = (*MCP_PATHS, *CASE_VARIANTS, *FOLD_VARIANTS)
# AC-3: every other path. The near misses start or end like an MCP path, or belong to a client
# for which `mcp_file_path` has no file in this release.
OTHER_PATHS = (
    ".prompts/a.md",
    ".github/pull_request_template.md",
    "docs/.mcp.json",
    ".mcp.json.bak",
    ".cursor/mcp.json.bak",
    ".codex/config.toml.orig",
    ".cursor/other.json",
    ".vscode/mcp.json",
)

# --- the sentinel, assembled at run time (ORQLET-SEC-003) -----------------------------------------

SENTINEL = "".join(("team-", "only-", "text-", "4f7c", "91a2"))
OTHER_SENTINEL = "".join(("second-", "team-", "text-", "b83d", "05e6"))


# --- helpers --------------------------------------------------------------------------------------


def cp(text: str) -> CanonicalPath:
    return CanonicalPath.parse(text)


def is_toml(path: str) -> bool:
    return cp(path).name.endswith(".toml")


def entry_text(path: str, server: str, address: str) -> str:
    """A file with one server, in the syntax of the file: TOML for Codex, JSON for the others."""
    if is_toml(path):
        return f'[mcp_servers.{server}]\nurl = "{address}"\n'
    document = {"mcpServers": {server: {"type": "http", "url": address}}}
    return json.dumps(document, indent=2) + "\n"


def wanted_text(path: str, revision: int = 1) -> str:
    """What Orqlet wants. It holds no sentinel; each revision has text that no other has."""
    return entry_text(path, f"orqlet-rev{revision}", f"https://example.com/rev{revision}")


def team_text(path: str, sentinel: str = SENTINEL) -> str:
    """The team's own file: the server line and the address line hold the sentinel."""
    return entry_text(path, f"team-{sentinel}", f"https://example.com/{sentinel}")


def unified(path: str, shown: str | None, wanted: str) -> str:
    """The diff that `build_plan` writes for a proposal: `shown` is the old side."""
    before = [] if shown is None else shown.splitlines()
    lines = difflib.unified_diff(
        before, wanted.splitlines(), fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="", n=3
    )
    return "\n".join(lines) + "\n"


def seeded(path: str, text: str) -> Desired:
    return Desired(cp(path), OwnerMode.SEEDED, None, text.encode())


def generated(path: str, text: str) -> Desired:
    return Desired(cp(path), OwnerMode.ORQLET, FileClass.GENERATED, text.encode())


def block_of(
    path: str, name: str, body: str, *, owner: OwnerMode = OwnerMode.SHARED_BLOCK
) -> Desired:
    file_class = None if owner is OwnerMode.SEEDED else FileClass.GENERATED
    content = render_block(name, "v1", body).encode()
    return Desired(cp(path), owner, file_class, content, block_name=name)


def apply(plan: ChangePlan, tree: dict[CanonicalPath, bytes]) -> dict[CanonicalPath, bytes]:
    result = dict(tree)
    for write in plan.writes:
        if write.kind == "delete":
            result.pop(write.path, None)
        else:
            assert write.content is not None
            result[write.path] = write.content
    return result


# --- the scenarios: one for each state that makes `_propose` run ----------------------------------


@dataclass(frozen=True)
class Scenario:
    path: str
    desired: list[Desired]
    current: dict[CanonicalPath, bytes]
    wanted: str  # the text that the proposal must hold: the whole file, or the block
    shown: str  # the old side that the builder shows for any path that is not an MCP file
    outcome: list[tuple[FileState, Action]]  # the branch that the scenario reaches
    block: str | None = None  # the block name that the proposal path carries, if any
    recorded: list[Recorded] = field(default_factory=list)
    leaks: tuple[str, ...] = (SENTINEL,)  # text that is only in the existing file


def seeded_clash(path: str) -> Scenario:
    """`whole_file`, action PROPOSE: a seeded file that exists and that Orqlet never recorded."""
    wanted, team = wanted_text(path), team_text(path)
    return Scenario(
        path=path,
        desired=[seeded(path, wanted)],
        current={cp(path): team.encode()},
        wanted=wanted,
        shown=team,
        outcome=[(FileState.SEEDED_PROPOSAL, Action.PROPOSE)],
    )


def seeded_newer_text_over_a_team_edit(path: str) -> Scenario:
    """`whole_file`, action PROPOSE: Orqlet wrote v1, the team rewrote it, the render is v2."""
    first = build_plan([seeded(path, wanted_text(path, 1))], {}, [])
    wanted, team = wanted_text(path, 2), team_text(path)
    return Scenario(
        path=path,
        desired=[seeded(path, wanted)],
        current={cp(path): team.encode()},
        recorded=list(first.recorded_after),
        wanted=wanted,
        shown=team,
        outcome=[(FileState.SEEDED_PROPOSAL, Action.PROPOSE)],
    )


def seeded_newer_text_over_the_file_orqlet_wrote(path: str) -> Scenario:
    """`whole_file`, action PROPOSE: the file is what Orqlet wrote (v1) and the render is v2."""
    first_text = wanted_text(path, 1)
    first = build_plan([seeded(path, first_text)], {}, [])
    wanted = wanted_text(path, 2)
    return Scenario(
        path=path,
        desired=[seeded(path, wanted)],
        current=apply(first, {}),
        recorded=list(first.recorded_after),
        wanted=wanted,
        shown=first_text,
        leaks=("rev1",),  # the old text of Orqlet's own file: the proposal does not diff against it
        outcome=[(FileState.SEEDED_PROPOSAL, Action.PROPOSE)],
    )


def stop_name_collision(path: str) -> Scenario:
    """`whole_file`, action STOP: a file of Orqlet's kind, unrecorded, and the path is taken."""
    wanted, team = wanted_text(path), team_text(path)
    return Scenario(
        path=path,
        desired=[generated(path, wanted)],
        current={cp(path): team.encode()},
        wanted=wanted,
        shown=team,
        outcome=[(FileState.NAME_COLLISION, Action.STOP)],
    )


def stop_conflict(path: str) -> Scenario:
    """`whole_file`, action STOP: both the team's file and the render changed since Orqlet wrote."""
    first = build_plan([generated(path, wanted_text(path, 1))], {}, [])
    wanted, team = wanted_text(path, 2), team_text(path)
    return Scenario(
        path=path,
        desired=[generated(path, wanted)],
        current={cp(path): team.encode()},
        recorded=list(first.recorded_after),
        wanted=wanted,
        shown=team,
        outcome=[(FileState.CONFLICT, Action.STOP)],
    )


def _file_around(block_text: str) -> str:
    return f"# Notes {SENTINEL}\n\n{block_text}\nafter {SENTINEL}\n"


def block_name_collision(path: str) -> Scenario:
    """`blocks`, action STOP: a block of that name exists, differs and Orqlet never recorded it."""
    existing_block = render_block("team-block", "v1", f"team body {SENTINEL}")
    return Scenario(
        path=path,
        block="team-block",
        desired=[block_of(path, "team-block", "wanted body")],
        current={cp(path): _file_around(existing_block).encode()},
        wanted=render_block("team-block", "v1", "wanted body"),
        shown=existing_block,
        outcome=[(FileState.NAME_COLLISION, Action.STOP)],
    )


def block_conflict(path: str) -> Scenario:
    """`blocks`, action STOP: the team edited the block that Orqlet wrote, and the render moved."""
    first = build_plan([block_of(path, "orqlet-wf", "wf v1")], {}, [])
    edited_block = render_block("orqlet-wf", "v1", f"wf v1 {SENTINEL}")
    return Scenario(
        path=path,
        block="orqlet-wf",
        desired=[block_of(path, "orqlet-wf", "wf v2")],
        current={cp(path): _file_around(edited_block).encode()},
        recorded=list(first.recorded_after),
        wanted=render_block("orqlet-wf", "v1", "wf v2"),
        shown=edited_block,
        outcome=[(FileState.CONFLICT, Action.STOP)],
    )


def block_seeded_proposal(path: str) -> Scenario:
    """`blocks`, action PROPOSE: a seeded block whose name is taken by a block that differs."""
    existing_block = render_block("team-block", "v1", f"team body {SENTINEL}")
    return Scenario(
        path=path,
        block="team-block",
        desired=[block_of(path, "team-block", "wanted body", owner=OwnerMode.SEEDED)],
        current={cp(path): _file_around(existing_block).encode()},
        wanted=render_block("team-block", "v1", "wanted body"),
        shown=existing_block,
        outcome=[(FileState.SEEDED_PROPOSAL, Action.PROPOSE)],
    )


WHOLE_FILE_BRANCHES: dict[str, Callable[[str], Scenario]] = {
    "seeded-clash": seeded_clash,
    "seeded-newer-text-over-a-team-edit": seeded_newer_text_over_a_team_edit,
    "seeded-newer-text-over-the-file-orqlet-wrote": seeded_newer_text_over_the_file_orqlet_wrote,
    "stop-name-collision": stop_name_collision,
    "stop-conflict": stop_conflict,
}
BLOCK_BRANCHES: dict[str, Callable[[str], Scenario]] = {
    "block-name-collision": block_name_collision,
    "block-conflict": block_conflict,
    "block-seeded-proposal": block_seeded_proposal,
}
BRANCHES = WHOLE_FILE_BRANCHES | BLOCK_BRANCHES


def branch_cases(paths: tuple[str, ...]) -> list[object]:
    return [
        pytest.param(branch, path, id=f"{branch}|{path}") for branch in BRANCHES for path in paths
    ]


def plan_of(scenario: Scenario) -> ChangePlan:
    return build_plan(scenario.desired, scenario.current, scenario.recorded)


def proposal_of(scenario: Scenario, plan: ChangePlan) -> PlannedWrite:
    """The one write of a scenario: the proposal, at its own path, written as a new file."""
    target = proposal_path(cp(scenario.path), scenario.block)
    assert [str(w.path) for w in plan.writes] == [str(target)]
    (write,) = plan.writes
    assert write.is_proposal
    assert write.kind == "create"
    assert write.before_sha256 is None
    assert write.content is not None
    assert write.after_sha256 == sha256_hex(write.content)
    return write


def assert_branch_reached(scenario: Scenario, plan: ChangePlan) -> None:
    """The scenario must really reach the branch it names, or its test would prove nothing."""
    assert [(i.state, i.action) for i in plan.items] == scenario.outcome


def assert_withheld(scenario: Scenario) -> str:
    """The proposal holds none of the existing file and is the diff against nothing."""
    plan = plan_of(scenario)
    assert_branch_reached(scenario, plan)
    text = (proposal_of(scenario, plan).content or b"").decode("utf-8")
    for leak in scenario.leaks:
        assert leak not in text, "the existing file's text is in the proposal"
        assert all(leak.encode() not in (w.content or b"") for w in plan.writes), (
            "the existing file's text is in a planned write"
        )
        assert leak not in repr(plan), "the existing file's text is somewhere in the plan"
    assert text == unified(scenario.path, None, scenario.wanted)
    return text


def assert_unchanged(scenario: Scenario) -> str:
    """The proposal of any other path still shows the existing text, as removed lines."""
    plan = plan_of(scenario)
    assert_branch_reached(scenario, plan)
    text = (proposal_of(scenario, plan).content or b"").decode("utf-8")
    assert text == unified(scenario.path, scenario.shown, scenario.wanted)
    removed = {line[1:] for line in text.splitlines() if line.startswith("-") and line[:3] != "---"}
    wanted_lines = set(scenario.wanted.splitlines())
    shown_only = {line for line in scenario.shown.splitlines() if line not in wanted_lines}
    assert shown_only
    assert shown_only <= removed
    for leak in scenario.leaks:
        assert leak in text
    return text


# --- AC-1: a seeded file that exists and differs gets a diff against nothing ----------------------


@pytest.mark.parametrize("path", MCP_PATHS)
def test_ac1_a_sentinel_in_the_existing_file_is_absent_from_the_proposal_and_every_write(
    path: str,
) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 5 ("it passes no existing bytes ... it shows
    the text that Orqlet wants and none of the team's file"); EC-14 ("none of the bytes of the
    existing file"); ORQLET-SEC-003 (the sentinel is assembled at run time)."""
    scenario = seeded_clash(path)
    assert SENTINEL.encode() in scenario.current[cp(path)]

    plan = plan_of(scenario)
    assert_branch_reached(scenario, plan)
    proposal = proposal_of(scenario, plan)

    assert SENTINEL not in (proposal.content or b"").decode("utf-8")
    assert all(SENTINEL.encode() not in (write.content or b"") for write in plan.writes)
    assert [str(write.path) for write in plan.writes] == [str(proposal_path(cp(path), None))]


@pytest.mark.parametrize("path", MCP_PATHS)
def test_ac1_every_wanted_line_is_an_added_line_and_no_line_is_removed(path: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 5 ("The proposal is then a diff against
    nothing: it shows the text that Orqlet wants"); EC-14 ("a unified diff against nothing: it holds
    the text that Orqlet wants")."""
    scenario = seeded_clash(path)
    plan = plan_of(scenario)
    lines = (proposal_of(scenario, plan).content or b"").decode("utf-8").splitlines()

    added = [line[1:] for line in lines if line.startswith("+") and line[:3] != "+++"]
    removed = [line for line in lines if line.startswith("-") and line[:3] != "---"]
    context = [line for line in lines if line.startswith(" ")]
    assert added == scenario.wanted.splitlines()
    assert removed == []
    assert context == []


@pytest.mark.parametrize("path", MCP_PATHS)
def test_ac1_the_proposal_is_the_diff_against_nothing_written_out(path: str) -> None:
    """AC-1. expected_behavior_source: EC-14 ("A proposal for .mcp.json, .cursor/mcp.json or
    .codex/config.toml is a unified diff against nothing"); ADR-003 decision 5 ("a diff against
    nothing"). The expected text is a unified diff of an empty file against the wanted text."""
    wanted = '{\n  "mcpServers": {}\n}\n'
    desired = [seeded(path, wanted)]
    existing = {cp(path): f"team {SENTINEL}\nsecond line\n".encode()}

    plan = build_plan(desired, existing, [])

    (write,) = plan.writes
    assert (write.content or b"").decode("utf-8") == (
        f'--- a/{path}\n+++ b/{path}\n@@ -0,0 +1,3 @@\n+{{\n+  "mcpServers": {{}}\n+}}\n'
    )


@pytest.mark.parametrize("path", MCP_PATHS)
def test_ac1_an_existing_file_that_is_not_utf8_gets_the_wanted_text_too(path: str) -> None:
    """AC-1. expected_behavior_source: EC-14 ("it holds the text that Orqlet wants and none of the
    bytes of the existing file"); ADR-003 decision 5 ("whichever branch calls it"). The existing
    file cannot be read as text, so the proposal must not fall back to a note about its content."""
    wanted = wanted_text(path)
    existing = {cp(path): b"\xff\xfe" + SENTINEL.encode()}

    plan = build_plan([seeded(path, wanted)], existing, [])

    (write,) = plan.writes
    assert write.is_proposal
    assert (write.content or b"").decode("utf-8") == unified(path, None, wanted)


@pytest.mark.parametrize("path", MCP_PATHS)
def test_ac1_the_proposal_does_not_depend_on_the_bytes_of_the_existing_file(path: str) -> None:
    """AC-1. expected_behavior_source: EC-14 ("a unified diff against nothing"); ADR-003 decision 5
    ("The proposal is then a diff against nothing"). Two different existing files give one and the
    same proposal, byte for byte."""
    wanted = wanted_text(path)
    one = build_plan([seeded(path, wanted)], {cp(path): team_text(path).encode()}, [])
    other = build_plan(
        [seeded(path, wanted)], {cp(path): team_text(path, OTHER_SENTINEL).encode()}, []
    )

    assert [w.content for w in one.writes] == [w.content for w in other.writes]
    assert [w.after_sha256 for w in one.writes] == [w.after_sha256 for w in other.writes]
    assert one.digest == other.digest


@pytest.mark.parametrize("path", MCP_PATHS)
def test_ac1_a_proposal_on_disk_is_not_rewritten_when_the_team_changes_its_file(path: str) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 5 ("a proposal file that already holds the
    same text is not rewritten, so `upgrade --check` finds nothing to write"; "a diff against
    nothing"). The proposal does not depend on the existing file, so a new edit by the team does
    not change it."""
    wanted = wanted_text(path)
    first = build_plan([seeded(path, wanted)], {cp(path): team_text(path).encode()}, [])
    tree = apply(first, {cp(path): team_text(path).encode()})
    tree[cp(path)] = team_text(path, OTHER_SENTINEL).encode()

    again = build_plan([seeded(path, wanted)], tree, [])

    assert again.writes == ()


@pytest.mark.parametrize("path", MCP_PATHS)
def test_ac1_a_proposal_written_before_the_guard_is_replaced_by_one_without_the_team_text(
    path: str,
) -> None:
    """AC-1. expected_behavior_source: ADR-003 Consequences ("The proposal files for the three MCP
    paths change in content (EC-14)"); EC-14 ("none of the bytes of the existing file"). A proposal
    that an earlier release wrote, with the team's text in it, is updated; the plan holds the new
    text only."""
    wanted = wanted_text(path)
    stale = unified(path, team_text(path), wanted)  # the proposal of a build without the guard
    target = proposal_path(cp(path), None)
    current = {cp(path): team_text(path).encode(), target: stale.encode()}

    plan = build_plan([seeded(path, wanted)], current, [])

    assert len(plan.writes) == 1, "the proposal on disk, with the team's text, is not replaced"
    (write,) = plan.writes
    assert write.path == target
    assert write.kind == "update"
    assert write.is_proposal
    assert write.before_sha256 == sha256_hex(stale.encode())
    assert (write.content or b"").decode("utf-8") == unified(path, None, wanted)
    assert SENTINEL.encode() not in (write.content or b"")
    assert SENTINEL not in repr(plan)


# --- AC-2: every branch that calls `_propose`, and a case variant of each path --------------------


def mcp_file_path_of_key(path: str) -> str:
    """The MCP file whose key is the key of `path`."""
    matching = [known for known in MCP_PATHS if cp(known).key == cp(path).key]
    assert len(matching) == 1
    return matching[0]


@pytest.mark.parametrize(("branch", "path"), branch_cases(MCP_PATHS))
def test_ac2_each_branch_that_proposes_withholds_the_existing_text(branch: str, path: str) -> None:
    """AC-2. expected_behavior_source: ADR-003 decision 5 ("it passes no existing bytes, whichever
    branch calls it"); EC-14 ("whichever branch calls it"); the branches are the seeded proposal,
    the stop and the shared block of AC-2."""
    assert_withheld(BRANCHES[branch](path))


@pytest.mark.parametrize(("branch", "path"), branch_cases((*CASE_VARIANTS, *FOLD_VARIANTS)))
def test_ac2_each_branch_withholds_the_existing_text_for_a_case_variant_of_the_path(
    branch: str, path: str
) -> None:
    """AC-2. expected_behavior_source: ADR-003 decision 5 ("Paths are compared on
    `CanonicalPath.key`, which folds case, so `.MCP.json` is covered"); AC-2 ("a case variant of
    each path (.MCP.json) is covered because paths are compared on the case-folded key")."""
    scenario = BRANCHES[branch](path)
    assert cp(path).key == cp(mcp_file_path_of_key(path)).key
    assert str(cp(path)) != mcp_file_path_of_key(path)

    assert_withheld(scenario)


def _propose_call_sites() -> list[str]:
    assert changeplan.__file__ is not None
    tree = ast.parse(Path(changeplan.__file__).read_text(encoding="utf-8"))
    sites: list[str] = []
    for function in ast.walk(tree):
        if isinstance(function, ast.FunctionDef):
            sites += [
                function.name
                for node in ast.walk(function)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_propose"
            ]
    return sorted(sites)


def test_ac2_the_scenarios_cover_every_call_site_of_propose() -> None:
    """AC-2. expected_behavior_source: AC-2 ("The guard covers every branch that calls _propose");
    ADR-003 Context ("built from the existing bytes at one place, `_propose` ... called at lines
    215 and 265"). `_propose` is called from `whole_file` and from `blocks` and from nowhere
    else; a new call site needs its own scenario in this file."""
    assert _propose_call_sites() == ["blocks", "whole_file"]
    reached = {
        (FileState.SEEDED_PROPOSAL, Action.PROPOSE),
        (FileState.NAME_COLLISION, Action.STOP),
        (FileState.CONFLICT, Action.STOP),
    }
    assert {s("x").outcome[0] for s in WHOLE_FILE_BRANCHES.values()} == reached
    assert {s("x").outcome[0] for s in BLOCK_BRANCHES.values()} == reached


# --- AC-3: every other path is unchanged, and so are the state, the action and the lock -----------


def test_ac3_an_ordinary_seeded_proposal_shows_the_existing_text_as_removed_lines() -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 5 (the guard is for "the MCP file of any
    client"); EC-14 ("Proposals for other paths are unchanged")."""
    plan = build_plan([seeded(".prompts/a.md", "seed\n")], {cp(".prompts/a.md"): b"mine\n"}, [])

    (write,) = plan.writes
    assert write.is_proposal
    assert (write.content or b"").decode("utf-8") == (
        "--- a/.prompts/a.md\n+++ b/.prompts/a.md\n@@ -1 +1 @@\n-mine\n+seed\n"
    )


def test_ac3_an_ordinary_shared_block_proposal_shows_the_existing_block_as_removed_lines() -> None:
    """AC-3. expected_behavior_source: EC-14 ("Proposals for other paths are unchanged"); AC-3
    ("Proposals for every other path are byte-identical to the base"). A block of
    `.github/pull_request_template.md` that is taken and differs gets the diff against it."""
    path = ".github/pull_request_template.md"
    existing = render_block("team-template", "v1", "team text")

    plan = build_plan(
        [block_of(path, "team-template", "wanted text")], {cp(path): existing.encode()}, []
    )

    (write,) = plan.writes
    assert write.is_proposal
    assert (write.content or b"").decode("utf-8") == (
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1,3 +1,3 @@\n"
        " <!-- orqlet:begin team-template v1 -->\n"
        "-team text\n"
        "+wanted text\n"
        " <!-- orqlet:end team-template -->\n"
    )


@pytest.mark.parametrize(("branch", "path"), branch_cases(OTHER_PATHS))
def test_ac3_every_other_path_keeps_the_diff_against_its_existing_text(
    branch: str, path: str
) -> None:
    """AC-3. expected_behavior_source: EC-14 ("Proposals for other paths are unchanged"); AC-3
    ("Proposals for every other path are byte-identical to the base"). The paths include ones
    that start or end like an MCP file and `.vscode/mcp.json`, for which `mcp_file_path` raises."""
    assert_unchanged(BRANCHES[branch](path))


def _shape(
    plan: ChangePlan,
) -> tuple[list[object], list[object], list[object], tuple[str, ...], int]:
    """Everything of a plan that is not a path, a hash or a text: what the guard must not touch."""
    items: list[object] = [
        (i.block_name, i.owner, i.file_class, i.state, i.action, i.reason) for i in plan.items
    ]
    records: list[object] = [
        (r.owner, r.file_class, r.sha256, r.block_name, r.block, r.entry, r.inputs)
        for r in plan.recorded_after
    ]
    writes: list[object] = [(w.kind, w.is_proposal, w.last) for w in plan.writes]
    return items, records, writes, plan.findings, len(plan.conflicts)


@pytest.mark.parametrize(("branch", "path"), branch_cases(GUARDED_PATHS))
def test_ac3_the_guard_changes_no_state_action_item_or_lock_entry(branch: str, path: str) -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 5 ("Classification is unchanged, so a
    re-run, `--resume` and `--check` converge"); AC-3 ("classify.py is unchanged"). The same
    scenario for an MCP path and for an ordinary path gives the same items, the same records for
    the lock and the same kind of write: only the text of the proposal differs."""
    # The text of a whole file follows the syntax of its path, so the control has the same one.
    whole_file_control = ".prompts/a.toml" if is_toml(path) else ".prompts/a.md"
    control_path = whole_file_control if branch in WHOLE_FILE_BRANCHES else OTHER_PATHS[1]
    guarded = plan_of(BRANCHES[branch](path))
    control = plan_of(BRANCHES[branch](control_path))

    assert _shape(guarded) == _shape(control)
    assert [i.path for i in guarded.items] == [cp(path)]
    assert [(i.state, i.action) for i in guarded.items] == BRANCHES[branch](path).outcome


def _one_plan_for_mcp_and_other_files() -> tuple[list[Scenario], list[Scenario], dict[str, str]]:
    """One plan with a proposal from every call site for three MCP files and three other files."""
    guarded = [
        seeded_clash(".mcp.json"),
        stop_conflict(".cursor/mcp.json"),
        block_conflict(".codex/config.toml"),
    ]
    others = [
        seeded_clash(".prompts/a.md"),
        stop_conflict("docs/.mcp.json"),
        block_conflict(".github/pull_request_template.md"),
    ]
    scenarios = [*guarded, *others]
    plan = build_plan(
        [d for s in scenarios for d in s.desired],
        {path: data for s in scenarios for path, data in s.current.items()},
        [r for s in scenarios for r in s.recorded],
    )
    written = {str(w.path): (w.content or b"").decode("utf-8") for w in plan.writes}
    assert set(written) == {str(proposal_path(cp(s.path), s.block)) for s in scenarios}
    return guarded, others, written


def test_ac3_in_one_plan_the_proposals_of_the_other_paths_are_unchanged() -> None:
    """AC-3. expected_behavior_source: EC-14 ("Proposals for other paths are unchanged"); ADR-003
    decision 5 ("The guard is derived from the path"). The plan also holds proposals for MCP
    files, so a guard that switched on for the whole plan would show here."""
    _, others, written = _one_plan_for_mcp_and_other_files()

    for scenario in others:
        target = str(proposal_path(cp(scenario.path), scenario.block))
        assert written[target] == unified(scenario.path, scenario.shown, scenario.wanted)
        assert SENTINEL in written[target]


def test_ac2_in_one_plan_every_proposal_for_an_mcp_file_is_withheld() -> None:
    """AC-2. expected_behavior_source: ADR-003 decision 5 ("it passes no existing bytes, whichever
    branch calls it"; "The guard is derived from the path"). The seeded proposal, the stop and
    the shared block of three different MCP files are in one plan."""
    guarded, _, written = _one_plan_for_mcp_and_other_files()

    for scenario in guarded:
        target = str(proposal_path(cp(scenario.path), scenario.block))
        assert SENTINEL not in written[target]
        assert written[target] == unified(scenario.path, None, scenario.wanted)


@pytest.mark.parametrize("path", MCP_PATHS)
def test_ac3_a_second_run_over_the_applied_proposal_writes_nothing(path: str) -> None:
    """AC-3. expected_behavior_source: ADR-003 decision 5 ("Classification is unchanged, so a
    re-run, `--resume` and `--check` converge"; "a proposal file that already holds the same text
    is not rewritten"). The item stays a seeded proposal on every run."""
    desired = [seeded(path, wanted_text(path))]
    current = {cp(path): team_text(path).encode()}
    first = build_plan(desired, current, [])

    second = build_plan(desired, apply(first, current), list(first.recorded_after))

    assert second.is_empty
    assert [(i.state, i.action) for i in second.items] == [
        (FileState.SEEDED_PROPOSAL, Action.PROPOSE)
    ]
    assert second.recorded_after == first.recorded_after


# --- AC-4: the client ids of the guard are the clients that have an MCP file ----------------------

KNOWN_CLIENTS = ("claude-code", "codex", "cursor", "vscode")


def _has_mcp_file(client: str) -> bool:
    try:
        mcp_file_path(client)
    except ValueError:
        return False
    return True


def test_ac4_the_guard_knows_exactly_the_clients_for_which_mcp_file_path_succeeds() -> None:
    """AC-4. expected_behavior_source: ADR-003 decision 5 ("The places that enumerate the clients
    are: the private table of paths in `mcp_credentials.py`, the constant of client ids in
    `changeplan.py` ... a test fails when they diverge, and a fourth client needs all three")."""
    clients = getattr(changeplan, "_MCP_CLIENTS", None)

    assert clients is not None, "orqlet.domain.changeplan has no constant `_MCP_CLIENTS`"
    assert all(isinstance(client, str) for client in clients)
    assert set(clients) == {client for client in KNOWN_CLIENTS if _has_mcp_file(client)}
    assert "vscode" not in clients
    assert {mcp_file_path(client) for client in clients} == set(MCP_PATHS)


def test_ac4_three_client_ids_have_a_path_and_an_unknown_id_raises() -> None:
    """AC-4. expected_behavior_source: AC-4 ("the three ids succeed and an unknown id raises");
    ADR-003 decision 5 (`mcp_file_path` for `claude-code`, `codex` and `cursor`)."""
    assert {client: mcp_file_path(client) for client in ("claude-code", "codex", "cursor")} == {
        "claude-code": ".mcp.json",
        "codex": ".codex/config.toml",
        "cursor": ".cursor/mcp.json",
    }
    assert not any(_has_mcp_file(unknown) for unknown in ("vscode", "unknown-client", ""))


# --- AC-5: the guard and its constant are private -------------------------------------------------

# The public names of orqlet/domain/changeplan.py as the project's extractor reads them from the
# file before this phase, with their canonical signatures.
BASE_PUBLIC_API = {
    "PROPOSALS_DIR": "PROPOSALS_DIR",
    "PlanError": "class PlanError(OrqletError)",
    "Action": "class Action(StrEnum)",
    "Desired": "class Desired",
    "Recorded": "class Recorded",
    "Recorded.key": "def key(self) -> tuple[str, str]",
    "PlannedItem": "class PlannedItem",
    "PlannedWrite": "class PlannedWrite",
    "ChangePlan": "class ChangePlan",
    "ChangePlan.is_empty": "def is_empty(self) -> bool",
    "ChangePlan.conflicts": "def conflicts(self) -> tuple[PlannedItem, ...]",
    "ChangePlan.digest": "def digest(self) -> str",
    "ChangePlan.with_manifest": (
        "def with_manifest(self, path: CanonicalPath, content: bytes, current: bytes | None)"
        " -> ChangePlan"
    ),
    "normalised_hash": "def normalised_hash(content: bytes) -> str",
    "proposal_path": (
        "def proposal_path(path: CanonicalPath, block_name: str | None) -> CanonicalPath"
    ),
    "build_plan": (
        "def build_plan(desired: Sequence[Desired], current: Mapping[CanonicalPath, bytes],"
        " recorded: Sequence[Recorded]) -> ChangePlan"
    ),
}


def test_ac5_the_public_names_of_the_change_plan_module_are_those_of_the_base() -> None:
    """AC-5. expected_behavior_source: EC-14 ("The guard is private and has no public name");
    AC-5 ("the guard and its constant are private"); component.md ("the constant of client ids in
    `changeplan.py`" is among the names that are "Not public and therefore not listed")."""
    assert changeplan.__file__ is not None
    api = extract_module_api(Path(changeplan.__file__).read_text(encoding="utf-8"))

    assert api.errors == ()
    assert api.manual == ()
    assert {name: symbol.signature for name, symbol in api.symbols.items()} == BASE_PUBLIC_API
    assert not [name for name in api.symbols if "mcp" in name.lower() or "guard" in name.lower()]
