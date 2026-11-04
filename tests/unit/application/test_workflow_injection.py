"""The injection mechanisms of the workflow, proven before any workflow text changes.

Task phase-skill-contracts, phase P-1 (ADR-005 decision 1). Every test cites its
`expected_behavior_source`: BC-n are the behaviour criteria of
docs/design/phase-skill-contracts/design/component.md, ADR-005 is
docs/design/phase-skill-contracts/design/adr-005-injection-unchanged-tests-and-version.md, A-n are
the facts of docs/design/phase-skill-contracts/as-is.md and AC-n are the acceptance criteria of
phase P-1 in docs/design/phase-skill-contracts/plan.yaml. AC-5 is in
tests/unit/render/test_rendered_formats.py.

These tests were written by the Tester of phase P-1 before `ChangedWorkflow` of
tests/fakes/workflow.py had its `skill_change` option and `SkillChange`; the Coder gave the Tester
their interface. The tests of AC-1, AC-3, AC-4 and AC-6, and the test of AC-7 without the option,
describe what exists and are expected to pass at once; the test of AC-2 and the other tests of
AC-7 need the option. The project is the in-memory fake of tests/fakes, wired by
tests/support/init_env.py (ORQLET-TEST-001).

Choices:
- AC-1 initialises pip_flask (kind python-service: Flask, Python, pip) and rust_cli (kind unknown:
  clap, Rust, SQLx, Tokio, Kafka). The plan's example uv_fastapi declares `uv`, and the shipped
  design-format.md names `uv.lock`; poetry_cli declares Typer, which as-is-format.md names. A pair
  that differs in kind needs one Python project, because every other kind is `unknown`.
- A technology is looked for as a word of its own in its declared letter case, so `rust` inside
  `trust` or `python` in a placeholder is not the name of a technology (plan, self_check.unverified:
  "a technology name that is also an ordinary word in the skill text needs a fixture that avoids
  it"). A project name and a uuid are looked for anywhere in the text.
- The paths come from tests/support/render.py (`skill_files` over SKILL_NAMES, and ROLE_NAMES), so a
  reference that a later phase adds there is covered without an edit here, and every path is
  required to exist. Codex also gets the sidecar `agents/openai.yaml` of each workflow skill, which
  holds the skill's invocation setting (BC-1); Cursor reads the same folder and has no sidecar.
- AC-6 runs init with the real packaged workflow, the release that the goldens are rendered from,
  and reads the committed goldens under tests/golden/<client>/docs-2026-10 itself: the `golden`
  fixture is not used, so `--update-golden` never writes a golden from what init wrote.

Deliberately not pinned: the text of any skill, reference or role (phases P-2 to P-5 rewrite it),
the number of files and references, the wording of findings, the order of a plan's writes, the
attributes of a block's begin marker, the status of an upgrade that only restores edited files,
and of `ChangedWorkflow` with a `SkillChange` its digest (only that it differs) and the message of
its `ValueError`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.ports.vcs import RepoState
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.diagnose import doctor
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Finding
from orqlet.domain.paths import CanonicalPath
from tests.fakes.ids import SequentialIds
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED, ChangedWorkflow, SkillChange
from tests.support.init_env import Env, read, tree
from tests.support.render import ROLE_NAMES, SKILL_NAMES, skill_files
from tests.support.trees import repo

pytestmark = pytest.mark.unit

YES = InitOptions(assume_yes=True)
GO = UpgradeOptions(assume_yes=True)
CLIENTS = ("claude-code", "codex", "cursor")
SKILL_ROOTS = {
    "claude-code": ".claude/skills",
    "codex": ".agents/skills",
    "cursor": ".agents/skills",
}
ROLE_FOLDERS = {
    "claude-code": (".claude/agents", ".md"),
    "codex": (".codex/agents", ".toml"),
    "cursor": (".cursor/agents", ".md"),
}
CODEX_SIDECAR = "agents/openai.yaml"
GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "golden"
GOLDEN_FAMILY = "docs-2026-10"

# The skill and reference that the upgrade and hand-edit tests change; both stay in every phase.
SKILL = "orqlet-plan"
REFERENCE = "plan-format.md"
ADDED_STEP = "- A step added in this release.\n"
HAND_EDIT = b"\n- A step that a person added by hand.\n"
# What `ChangedWorkflow` adds to the baseline and the PR template, unless told otherwise.
BASELINE_SUFFIX = "- A rule added in this release.\n"
SUFFIXED_SOURCES = ("baseline/baseline.md", "pr_template/workflow-section.md")
CHANGED_SOURCES = (f"skills/{SKILL}/skill.md", f"skills/{SKILL}/references/{REFERENCE}")


def workflow_files(client: str) -> list[str]:
    """The skill, reference and role files of one client: the paths of BC-6 and BC-38."""
    folder, suffix = ROLE_FOLDERS[client]
    root = SKILL_ROOTS[client]
    sidecars = [f"{root}/{name}/{CODEX_SIDECAR}" for name in SKILL_NAMES if client == "codex"]
    roles = [f"{folder}/{name}{suffix}" for name in ROLE_NAMES]
    return [*skill_files(root), *sidecars, *roles]


ALL_WORKFLOW_FILES = sorted({path for client in CLIENTS for path in workflow_files(client)})
CHANGED_FILES = [
    path
    for root in sorted(set(SKILL_ROOTS.values()))
    for path in (f"{root}/{SKILL}/SKILL.md", f"{root}/{SKILL}/references/{REFERENCE}")
]


def initialised(
    fixture: str = "uv_fastapi",
    options: InitOptions = YES,
    *,
    ids: SequentialIds | None = None,
    workflow: WorkflowSource | None = None,
) -> Env:
    env = Env(
        project=repo(fixture),
        vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"),
        ids=ids or SequentialIds(),
        workflow=workflow,
    )
    result = init_project(env.services(), options)
    assert result.status == "applied", result.findings
    return env


def profile_of(env: Env) -> ProjectProfile:
    return load_installation(env.services()).profile


def technologies(profile: ProjectProfile) -> set[str]:
    return {technology.name for technology in profile.technologies}


def names_word(text: str, word: str) -> bool:
    """`word` stands in `text` as a word of its own, in the letter case it is declared in."""
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text) is not None


def codes_at(findings: tuple[Finding, ...], path: str) -> set[str]:
    return {finding.code for finding in findings if finding.path == path}


def write(env: Env, path: str, content: bytes) -> None:
    env.project.write_atomic(CanonicalPath.parse(path), content)


# --- AC-1: two projects, the same workflow files, nothing of each other (BC-6) -------------------
ALPHA = "placeholder-project-alpha"
BETA = "placeholder-project-beta"


@pytest.fixture(scope="module")
def two_projects() -> tuple[Env, Env]:
    """pip_flask and rust_cli, each with its own name and its own first id (the project uuid)."""
    alpha = initialised(
        "pip_flask", InitOptions(assume_yes=True, project_name=ALPHA), ids=SequentialIds(start=0)
    )
    beta = initialised(
        "rust_cli", InitOptions(assume_yes=True, project_name=BETA), ids=SequentialIds(start=500)
    )
    return alpha, beta


def test_bc6_the_two_profiles_differ_in_name_kind_technologies_and_uuid_and_share_the_clients(
    two_projects: tuple[Env, Env],
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("profiles differ in name, kind and technologies ...
    with the same three clients ... and distinct project uuids") and BC-6: the fixtures give the
    two profiles that the criterion asks for, so the tests below compare what it means."""
    alpha, beta = (profile_of(env) for env in two_projects)

    assert (alpha.project.name, beta.project.name) == (ALPHA, BETA)
    assert alpha.project.kind != beta.project.kind
    assert alpha.project.uuid != beta.project.uuid
    assert technologies(alpha) - technologies(beta)
    assert technologies(beta) - technologies(alpha)
    assert set(alpha.clients.enabled) == set(beta.clients.enabled) == set(CLIENTS)


def test_bc6_two_projects_receive_byte_identical_skill_reference_and_role_files(
    two_projects: tuple[Env, Env],
) -> None:
    """AC-1. expected_behavior_source: BC-6 ("receive byte-identical workflow skill, reference and
    role files"), A-23 (no receiving-project value appears in a SKILL.md) and A-59 (one in-memory
    project and one data store per Env): every such path of the three clients is written into both
    projects with the same bytes."""
    alpha, beta = (tree(env.project) for env in two_projects)

    missing = [path for path in ALL_WORKFLOW_FILES if path not in alpha or path not in beta]
    differing = [path for path in ALL_WORKFLOW_FILES if alpha.get(path) != beta.get(path)]

    assert ALL_WORKFLOW_FILES
    assert missing == []
    assert differing == []


@pytest.mark.parametrize(("mine", "theirs"), [(0, 1), (1, 0)], ids=["in-alpha", "in-beta"])
def test_bc6_no_workflow_file_of_one_project_names_the_other_project(
    two_projects: tuple[Env, Env], mine: int, theirs: int
) -> None:
    """AC-1. expected_behavior_source: BC-6 ("No workflow skill, reference or role file written into
    one contains the other's project name, uuid or a technology that only the other declares"),
    for each of the two projects."""
    here, there = profile_of(two_projects[mine]), profile_of(two_projects[theirs])
    only_there = technologies(there) - technologies(here)
    found: dict[str, list[str]] = {}

    for path in ALL_WORKFLOW_FILES:
        text = read(two_projects[mine].project, path)
        hits = [value for value in (there.project.name, there.project.uuid) if value in text]
        hits += sorted(name for name in only_there if names_word(text, name))
        if hits:
            found[path] = hits

    assert only_there
    assert found == {}


# --- AC-2: a skill and a reference change, then two upgrades in a row (BC-27) --------------------
def test_bc27_after_a_skill_change_the_first_upgrade_writes_it_and_the_second_writes_nothing() -> (
    None
):
    """AC-2. expected_behavior_source: BC-27 ("Two `orqlet upgrade` runs in a row after a workflow
    change that changes a skill: the second plans nothing and writes nothing"), AC-2 (the change
    reaches a skill body and a reference, not only the baseline) and A-59 (before this phase the
    changed workflow of the tests changed only the baseline and the PR template)."""
    env = initialised()
    change = SkillChange(skill=SKILL, reference=REFERENCE, line=ADDED_STEP)
    env.workflow = ChangedWorkflow(PINNED, version="0.2.0", skill_change=change)

    first = upgrade(env.services(), GO)

    assert first.status == "applied"
    assert first.plan is not None
    updated = {str(planned.path) for planned in first.plan.writes if planned.kind == "update"}
    assert set(CHANGED_FILES) <= updated
    for path in CHANGED_FILES:
        assert ADDED_STEP.rstrip("\n") in read(env.project, path), path

    settled_project, settled_data = tree(env.project), tree(env.user_data)
    second = upgrade(env.services(), GO)

    assert second.status == "up-to-date"
    assert second.plan is not None
    assert second.plan.writes == ()
    assert tree(env.project) == settled_project
    assert tree(env.user_data) == settled_data


# --- AC-3: team text around the managed blocks of AGENTS.md (BC-28) ------------------------------
AGENTS = "AGENTS.md"
BLOCK = re.compile(
    r"<!-- orqlet:begin (?P<name>[a-z][a-z-]*) [^\n]*-->\n.*?<!-- orqlet:end (?P=name) -->",
    re.DOTALL,
)
TEAM_BEFORE = "# Team guide\n\nText the team wrote before the blocks — keep it.\n\n"
TEAM_BETWEEN = "\n\n## Between the blocks\n\n<!-- a team comment -->\nThe team keeps this here.\n\n"
TEAM_AFTER = "\n\n## After the blocks\n\nText the team wrote after the blocks.\n"
CONVENTIONS = InitOptions(assume_yes=True, answers={"repository.branch_model": "trunk-based"})


def blocks_and_text_around(text: str) -> tuple[list[str], list[str], list[str]]:
    """The names and texts of the managed blocks in order, and the text before, between, after."""
    names, blocks, around, start = [], [], [], 0
    for match in BLOCK.finditer(text):
        names.append(match["name"])
        blocks.append(match.group(0))
        around.append(text[start : match.start()])
        start = match.end()
    around.append(text[start:])
    return names, blocks, around


def test_bc28_an_upgrade_keeps_the_team_text_around_the_blocks_and_one_copy_of_each_block() -> None:
    """AC-3. expected_behavior_source: BC-28 ("keeps that text byte-identical and holds exactly one
    copy of each block") and ADR-005 decision 1 (the mechanism of A-41: shared files keep the text
    outside their managed blocks byte for byte). The upgrade rewrites the baseline block, so the
    text around it is kept by the merge and not because nothing was written."""
    env = initialised(options=CONVENTIONS)
    names, blocks, _ = blocks_and_text_around(read(env.project, AGENTS))
    assert names == ["baseline", "conventions"]
    team_file = TEAM_BEFORE + blocks[0] + TEAM_BETWEEN + blocks[1] + TEAM_AFTER
    write(env, AGENTS, team_file.encode("utf-8"))
    env.workflow = ChangedWorkflow(PINNED, version="0.2.0")

    result = upgrade(env.services(), GO)

    text = read(env.project, AGENTS)
    names, blocks, around = blocks_and_text_around(text)
    assert result.status == "applied"
    assert names == ["baseline", "conventions"]
    assert around == [TEAM_BEFORE, TEAM_BETWEEN, TEAM_AFTER]
    assert BASELINE_SUFFIX.rstrip("\n") in blocks[0]
    for name in names:
        assert text.count(f"<!-- orqlet:begin {name} ") == 1, name
        assert text.count(f"<!-- orqlet:end {name} -->") == 1, name


# --- AC-4: an edited SKILL.md and reference, reported and restored (BC-29) -----------------------
@pytest.mark.parametrize("root", sorted(set(SKILL_ROOTS.values())))
def test_bc29_an_edited_skill_and_reference_are_reported_by_doctor_and_restored_by_upgrade(
    root: str,
) -> None:
    """AC-4. expected_behavior_source: BC-29 ("An upgrade over an edited installed `SKILL.md` and an
    edited reference restores both and reports ORQ-W096 for each; `orqlet doctor` run before the
    upgrade reports ORQ-E150 for each") and ADR-005 decision 1 (A-44, A-47), in both skill
    folders."""
    env = initialised()
    edited = (f"{root}/{SKILL}/SKILL.md", f"{root}/{SKILL}/references/{REFERENCE}")
    rendered = {path: tree(env.project)[path] for path in edited}
    for path in edited:
        write(env, path, rendered[path] + HAND_EDIT)

    diagnosis = doctor(env.services())
    result = upgrade(env.services(), GO)

    for path in edited:
        assert "ORQ-E150" in codes_at(diagnosis.findings, path), path
        assert tree(env.project)[path] == rendered[path], path
        assert "ORQ-W096" in codes_at(result.findings, path), path


# --- AC-6: what init writes equals the goldens (BC-38) -------------------------------------------
@pytest.fixture(scope="module")
def packaged_project() -> Env:
    """A project with no registered resource and no integration, set up from the real package."""
    return initialised(workflow=PackagedWorkflow())


@pytest.mark.golden
@pytest.mark.parametrize("client", CLIENTS)
def test_bc38_what_init_writes_at_the_workflow_paths_equals_the_committed_goldens(
    client: str, packaged_project: Env
) -> None:
    """AC-6. expected_behavior_source: BC-38 ("the files that `orqlet init` writes for the three
    clients equal the committed goldens byte for byte ... The goldens' rule files come from
    `SAMPLE_RULES` and are not compared"), A-56 (the goldens compared adapter output only) and
    A-22, A-23 (those bytes depend on the workflow version only)."""
    written = tree(packaged_project.project)
    goldens = {path: GOLDEN_ROOT / client / GOLDEN_FAMILY / path for path in workflow_files(client)}

    missing = [path for path, golden in goldens.items() if not golden.is_file()]
    differing = [
        path
        for path, golden in goldens.items()
        if golden.is_file() and written.get(path) != golden.read_bytes()
    ]

    assert goldens
    assert missing == []
    assert differing == []


# --- AC-7: ChangedWorkflow keeps its behaviour and gains the skill change ------------------------
def digest_before_the_option(
    base: WorkflowSource, version: str, controls_level: int = 1, salt: str = ""
) -> str:
    """The release digest that `ChangedWorkflow` gave before the option (tests/fakes/workflow.py,
    lines 53-58 at 66b58898b8d2f84bd90b2ee43c9057f6dd5bb1d1)."""
    material = f"{version}|{controls_level}|{BASELINE_SUFFIX}|{salt}|{base.release.digest}"
    return sha256_hex(material.encode())


def with_line(text: str, line: str) -> str:
    """A source with a line appended the way `ChangedWorkflow` appends one."""
    return text.rstrip("\n") + "\n\n" + line


@pytest.mark.parametrize(
    ("version", "controls_level", "salt"),
    [("0.2.0", 1, ""), ("0.1.0", 1, "silent change"), ("0.2.0", 2, "")],
    ids=["next-release", "same-version-other-digest", "higher-controls-level"],
)
def test_without_a_skill_change_the_changed_workflow_behaves_as_before(
    version: str, controls_level: int, salt: str
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("ChangedWorkflow keeps its current behaviour when no
    skill or reference change is asked for, so every existing test that uses it passes without
    edit") and A-59 with tests/fakes/workflow.py:42-70 at the base: the baseline and the PR
    template get the line, every other source is the base's, and the identity is the old one."""
    changed = ChangedWorkflow(
        PINNED, version=version, controls_level=controls_level, digest_salt=salt
    )

    for path in PINNED.paths():
        base = PINNED.read_text(path)
        expected = with_line(base, BASELINE_SUFFIX) if path in SUFFIXED_SOURCES else base
        assert changed.read_text(path) == expected, path
    assert changed.paths() == PINNED.paths()
    assert changed.problems() == ()
    assert str(changed.release.version) == version
    assert changed.release.controls_level == controls_level
    assert changed.release.digest == digest_before_the_option(PINNED, version, controls_level, salt)


def test_a_skill_change_changes_the_named_skill_body_and_reference_only() -> None:
    """AC-7. expected_behavior_source: AC-7 ("the new option changes the named skill body and
    reference only"), plan P-1 file_operations (tests/fakes/workflow.py: "an optional change of one
    skill body and one reference ... The default stays as it is") and the interface that the Coder
    gave: the line is appended as the baseline line is, and the digest differs."""
    plain = ChangedWorkflow(PINNED, version="0.2.0")
    change = SkillChange(skill=SKILL, reference=REFERENCE, line=ADDED_STEP)

    changed = ChangedWorkflow(PINNED, version="0.2.0", skill_change=change)

    assert set(CHANGED_SOURCES) <= set(PINNED.paths())
    for path in PINNED.paths():
        if path in CHANGED_SOURCES:
            expected = with_line(PINNED.read_text(path), ADDED_STEP)
        else:
            expected = plain.read_text(path)
        assert changed.read_text(path) == expected, path
    assert changed.paths() == plain.paths()
    assert changed.release.version == plain.release.version
    assert changed.release.controls_level == plain.release.controls_level
    assert changed.release.digest != plain.release.digest


@pytest.mark.parametrize(
    ("skill", "reference"),
    [("orqlet-missing", REFERENCE), (SKILL, "missing-format.md"), ("orqlet-design", REFERENCE)],
    ids=["no-such-skill", "no-such-reference", "a-reference-of-another-skill"],
)
def test_a_skill_change_that_names_no_packaged_file_is_refused(skill: str, reference: str) -> None:
    """AC-7. expected_behavior_source: the interface that the Coder gave ("Naming a skill or
    reference that the base workflow does not have raises ValueError when the ChangedWorkflow is
    constructed"); AC-7 does not name it (see the Tester's report)."""
    change = SkillChange(skill=skill, reference=reference)

    with pytest.raises(ValueError, match=r".*"):
        ChangedWorkflow(PINNED, version="0.2.0", skill_change=change)
