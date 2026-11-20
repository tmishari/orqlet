"""`init` and `upgrade` with the seed of the model policy (task dynamic-model-profiles, P-13).

Acceptance criterion AC-12.

The seed is the packaged file `seeds/orqlet/model-policy.yaml`. The renderer function
`orqlet.adapters.render.prompts_seed.model_policy_seed`, the method `PackagedRenderers
.model_policy_seed` and `compose` give it to `init` and `upgrade` as the seeded file
`.orqlet/model-policy.yaml`: written once, recorded in the lock, then the team's.

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-13 in
docs/design/dynamic-model-profiles/plan.yaml, BC-n a behaviour of design/component.md, EC-n an edge
case, A-n an assumption of the AS-IS file, C-n a constraint, ADR-n a decision record of design/,
and "the interface" the section 4 of the interface that the Coder of P-13 gave the Tester.

These tests were written first, by the Tester of phase P-13, before the renderer function existed.
They use the fakes of tests/fakes: the in-memory file system, `FakeVcs`, a workflow that is the
packaged one with another version or another seed, and no network (ORQLET-TEST-001).

What the criteria leave open is not pinned: the text of the proposal beyond the line that it
changes, the findings of an `init` or an `upgrade` that concern other files, and the order of the
writes of a plan.

Already pinned and not repeated here: the proposal for `.orqlet/role-bindings.yaml` that adds the
third binding of `orqlet-code-reviewer`, with a patched list of the reviewers, in
tests/unit/application/test_upgrade_model_policy.py (AC-5 of P-6), and the seeded binding of
`init` in tests/unit/application/test_lifecycle.py (AC-2 of P-9). This file adds what those leave
out: the same proposal for a project that an earlier release initialised, with no patch at the
time of the upgrade.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render import prompts_seed
from orqlet.adapters.render.emit import normalise_text
from orqlet.adapters.render.renderers import PackagedRenderers
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.renderers import FileRenderers
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases import render_all
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.model_policy_source import (
    PolicyAbsent,
    PolicyLoaded,
    PolicyState,
    load_model_policy,
)
from orqlet.application.usecases.model_selection import follow_policy
from orqlet.application.usecases.render_all import Composition, compose, resolve_for
from orqlet.application.usecases.upgrade import UpgradeOptions, UpgradeResult, upgrade
from orqlet.application.usecases.workflow_sources import load_roles, load_skills
from orqlet.domain.changeplan import proposal_path
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Finding
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from tests.fakes.ids import SequentialIds
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED, ChangedWorkflow
from tests.support.init_env import Env, tree
from tests.support.trees import repo

pytestmark = pytest.mark.unit

SEED_SOURCE = "seeds/orqlet/model-policy.yaml"
POLICY_PATH = ".orqlet/model-policy.yaml"
GOLDEN_PATH = "common/.orqlet/model-policy.yaml"
PROPOSAL_PATH = ".orqlet/proposals/.orqlet__model-policy.yaml.diff"
BINDINGS_PATH = ".orqlet/role-bindings.yaml"
BINDINGS_PROPOSAL = ".orqlet/proposals/.orqlet__role-bindings.yaml.diff"
LOCK_PATH = ".orqlet/generated.lock.yaml"
CODE_REVIEWER = ("code-reviewer", "orqlet-code-reviewer")
CLIENTS = ("claude-code", "codex", "cursor")
GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "golden"
LOADER = StrictYamlLoader()
YES = InitOptions(assume_yes=True)
GO = UpgradeOptions(assume_yes=True)
MODES = {
    "apply": GO,
    "dry-run": UpgradeOptions(dry_run=True),
    "check": UpgradeOptions(check=True),
}


def shipped_seed() -> bytes:
    """The seed as a renderer must write it: the packaged text with one final line break."""
    return normalise_text(PackagedWorkflow().read_text(SEED_SOURCE)).encode("utf-8")


# --- projects ------------------------------------------------------------------------------


def new_env() -> Env:
    return Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))


def initialised() -> Env:
    env = new_env()
    assert init_project(env.services(), YES).status == "applied"
    return env


def put(env: Env, path: str, content: bytes) -> None:
    env.project.write_atomic(CanonicalPath.parse(path), content)


def read(env: Env, path: str) -> bytes:
    return env.project.read_bytes(CanonicalPath.parse(path))


def lock_document(env: Env) -> dict[str, Any]:
    document = LOADER.load(read(env, LOCK_PATH), source="lock")
    assert isinstance(document, dict)
    return document


def lock_row(env: Env, path: str) -> Any:
    lock = load_contract(LOADER, GeneratedLock, read(env, LOCK_PATH), source=LOCK_PATH)
    rows = [row for row in lock.files if row.path == path]
    assert len(rows) <= 1, path
    return rows[0] if rows else None


def a_project_of_an_earlier_release() -> Env:
    """An initialised project that has no model policy file and no lock row for it.

    This is what `init` of release 0.4.0 left: the seed did not exist.
    """
    env = initialised()
    env.project.delete(CanonicalPath.parse(POLICY_PATH))
    lock = lock_document(env)
    lock["files"] = [row for row in lock["files"] if row["path"] != POLICY_PATH]
    put(env, LOCK_PATH, json.dumps(lock, indent=2).encode())
    return env


def team_copy(version: int = 2) -> bytes:
    """The seed after a reviewed edit of the team: still a valid policy, `policy_version` raised."""
    document = LOADER.load(shipped_seed(), source=SEED_SOURCE)
    assert isinstance(document, dict)
    document["policy_version"] = version
    return json.dumps(document, indent=2).encode() + b"\n"


class NextReleaseWithSeed(ChangedWorkflow):
    """The next release, whose shipped seed has another `policy_version` than the packaged one."""

    def __init__(self, version: int = 3) -> None:
        super().__init__(PINNED, version="0.2.0", digest_salt=f"seed-{version}")
        self._seed = team_copy(version).decode("utf-8")

    def read_text(self, path: str) -> str:
        return self._seed if path == SEED_SOURCE else super().read_text(path)


def run_upgrade(
    env: Env, workflow: ChangedWorkflow | None, mode: str = "apply", *, start: int = 100
) -> UpgradeResult:
    env.workflow = workflow
    env.ids = SequentialIds(start=start)
    return upgrade(env.services(), MODES[mode])


def written_paths(result: UpgradeResult) -> set[str]:
    assert result.plan is not None
    return {str(write.path) for write in result.plan.writes}


# =============================================================================================
# The renderer function, the method of the renderers and the port
# =============================================================================================


def test_the_function_renders_the_seed_as_a_seeded_file_of_the_team() -> None:
    """AC-12. expected_behavior_source: AC-12 ("`init` writes `.orqlet/model-policy.yaml` once as a
    seeded file"); the interface section 4 (path `.orqlet/model-policy.yaml`, the text of the
    shipped seed normalised with `normalise_text` as UTF-8 bytes, owner `SEEDED`, no file class);
    ADR-002 decision 1 (owner `seeded`, like `role-bindings.yaml`); C-5.
    """
    rendered = prompts_seed.model_policy_seed(PackagedWorkflow())

    assert str(rendered.path) == POLICY_PATH
    assert rendered.content == shipped_seed()
    assert rendered.owner is OwnerMode.SEEDED
    assert rendered.file_class is None


def test_the_function_records_the_source_the_release_and_the_digest_of_what_it_wrote() -> None:
    """AC-12. expected_behavior_source: the interface section 4 (`inputs` is one item: the seed
    path in the package, the workflow release version, and the SHA-256 of the bytes); the pattern
    of `seed_files` in test_prompts_seed.py ("every seed file records what it was made from").
    """
    workflow = PackagedWorkflow()

    rendered = prompts_seed.model_policy_seed(workflow)

    assert rendered.inputs == (
        (SEED_SOURCE, str(workflow.release.version), sha256_hex(rendered.content)),
    )


def test_the_function_follows_the_text_of_the_workflow_it_is_given() -> None:
    """AC-12. expected_behavior_source: the interface section 4 (the function reads the seed from
    the `WorkflowSource` it is given, so a release with another seed renders another file); AC-12
    ("a fake workflow whose seed differs").
    """
    changed = NextReleaseWithSeed(version=9)

    rendered = prompts_seed.model_policy_seed(changed)

    assert rendered.content == team_copy(9)
    assert rendered.content != shipped_seed()
    assert rendered.inputs[0][1] == "0.2.0"


@pytest.mark.golden
def test_the_rendered_seed_is_the_golden_file(golden: Callable[[str, bytes], None]) -> None:
    """AC-12. expected_behavior_source: AC-12 ("The golden file
    `tests/golden/common/.orqlet/model-policy.yaml` equals the shipped seed byte for byte");
    ORQLET-DET-001 (generated output is compared with a committed file).
    """
    rendered = prompts_seed.model_policy_seed(PackagedWorkflow())

    golden(GOLDEN_PATH, rendered.content)


def test_the_golden_file_equals_the_shipped_seed_byte_for_byte() -> None:
    """AC-12. expected_behavior_source: AC-12 (the golden file "equals the shipped seed byte for
    byte"). The golden file is read here from disk and compared with the packaged text, so a
    golden file that was rewritten from a changed renderer would still have to be the seed.
    """
    golden_file = GOLDEN_ROOT / GOLDEN_PATH

    assert golden_file.is_file()
    assert golden_file.read_bytes() == shipped_seed()


def test_the_packaged_renderers_expose_the_function() -> None:
    """AC-12. expected_behavior_source: the interface section 4 (`PackagedRenderers
    .model_policy_seed(self, workflow)` returns the rendered file); plan P-13 file_operations
    (`renderers.py`: "The packaged renderers expose the new seed function").
    """
    workflow = PackagedWorkflow()

    assert PackagedRenderers().model_policy_seed(workflow) == prompts_seed.model_policy_seed(
        workflow
    )


def test_the_renderer_port_declares_the_method() -> None:
    """AC-12. expected_behavior_source: the interface section 4 (the protocol `FileRenderers` gains
    `model_policy_seed(self, workflow: WorkflowSource) -> RenderedFile`); plan P-13 file_operations
    (`ports/renderers.py`: "The renderer port gains the model-policy seed method").
    """
    parameters = inspect.signature(FileRenderers.model_policy_seed).parameters

    assert list(parameters) == ["self", "workflow"]
    assert parameters["workflow"].annotation == "WorkflowSource"


def test_the_seed_of_the_standards_folder_does_not_take_the_model_policy() -> None:
    """AC-12. expected_behavior_source: the interface section 4 (`adapters/render` gains no module;
    `seed_files` reads `seeds/prompts/` only, so `.prompts/` gets no model policy); the golden test
    of the three `.prompts/` files in test_prompts_seed.py. This holds before the seed exists.
    """
    paths = [str(f.path) for f in prompts_seed.seed_files(PackagedWorkflow())]

    assert paths == [".prompts/README.md", ".prompts/foundations.md", ".prompts/rules.yaml"]


# =============================================================================================
# compose: the file is part of every composition
# =============================================================================================


def composition_of(env: Env, policy: PolicyState | None) -> Composition:
    services = env.services()
    inst = load_installation(services)
    return compose(
        services,
        inst.profile,
        resolve_for(services, inst.profile),
        Resources(schema_id="orqlet.resources/v1"),
        clients=inst.profile.clients.enabled,
        prompts_dir=".prompts",
        pr_targets=(),
        profile_bytes=b"",
        resources_bytes=b"",
        policy=policy,
    )


def test_compose_adds_the_seed_once_as_a_seeded_desired_file() -> None:
    """AC-12. expected_behavior_source: the interface section 4 (`compose` adds that file to the
    `Desired` files it returns for every call, so `init` and `upgrade` write it as a seeded file
    and record it in the lock); plan P-13 file_operations (`render_all.py`: "The function
    `compose` adds the seed to the files it returns").
    """
    composition = composition_of(initialised(), None)

    found = [item for item in composition.desired if str(item.path) == POLICY_PATH]
    assert len(found) == 1
    assert found[0].owner is OwnerMode.SEEDED
    assert found[0].file_class is None
    assert found[0].content == shipped_seed()
    assert found[0].block_name is None


def test_compose_adds_the_seed_whatever_the_state_of_the_policy_it_is_given() -> None:
    """AC-12. expected_behavior_source: the interface section 4 ("adds that file ... for every
    call"). With no policy, with no file and with the seed loaded as the policy, the same one file
    is desired and nothing is refused.
    """
    env = initialised()
    loaded = load_model_policy(env.services())
    assert isinstance(loaded, PolicyLoaded)

    for policy in (None, PolicyAbsent(), loaded):
        composition = composition_of(env, policy)

        desired = [str(item.path) for item in composition.desired]
        assert desired.count(POLICY_PATH) == 1
        assert not composition.model_outcome.refused


def test_the_public_names_of_render_all_do_not_change() -> None:
    """AC-12. expected_behavior_source: the interface section 4 ("the public names of
    `render_all.py` do not change (a test of another task pins them)"). The names that the other
    tests of this phase import are still there.
    """
    for name in ("compose", "resolve_for", "Composition", "REVIEW_AGENTS", "LOCK_PATH"):
        assert hasattr(render_all, name), name


# =============================================================================================
# init
# =============================================================================================


def test_init_writes_the_seed_to_the_policy_path() -> None:
    """AC-12. expected_behavior_source: AC-12 ("`init` writes `.orqlet/model-policy.yaml` once as a
    seeded file"); BC-12; C-5; ADR-002 decision 1. The file is the shipped seed, byte for byte.
    """
    env = initialised()

    assert read(env, POLICY_PATH) == shipped_seed()


def test_init_records_the_seed_in_the_lock_as_a_seeded_file_with_its_hash() -> None:
    """AC-12. expected_behavior_source: AC-12 ("records it in the lock"); the interface section 4
    (owner `seeded`); the lock rows of the other seeded files, which hold `seeded_sha256` and no
    `rendered_sha256` (test_init_project.py).
    """
    env = initialised()

    row = lock_row(env, POLICY_PATH)

    assert row is not None
    assert row.owner is OwnerMode.SEEDED
    assert row.seeded_sha256 == sha256_hex(read(env, POLICY_PATH))
    assert row.rendered_sha256 is None
    assert row.block is None


def test_init_writes_it_once_and_a_second_run_leaves_the_team_copy_alone() -> None:
    """AC-12. expected_behavior_source: AC-12 ("once"); BC-12; EC-8 (a seeded file belongs to the
    team after it is written). A second `init` reports that the project is initialised and does
    not touch the edited file.
    """
    env = initialised()
    put(env, POLICY_PATH, team_copy())
    before = tree(env.project)

    second = init_project(env.services(), YES)

    assert second.status == "already-initialised"
    assert tree(env.project) == before


def test_after_init_the_seeded_policy_loads_and_the_selection_refuses_nothing() -> None:
    """AC-12, AC-10. expected_behavior_source: AC-12 (after `init` the seeded policy loads and the
    roles and skills it assigns all exist in the packaged workflow, so no finding of the model
    selection refuses it); ADR-002 consequences (seeded `proposed` entries make nothing render).
    """
    env = initialised()
    workflow = PackagedWorkflow()
    roles = [role.name for role in load_roles(workflow)]
    skills = [skill.name for skill in load_skills(workflow, IMPLEMENTED_COMMANDS)]

    state = load_model_policy(env.services())

    assert isinstance(state, PolicyLoaded)
    outcome = follow_policy(state, roles, skills, CLIENTS)
    assert outcome.refused is False
    assert outcome.findings == ()
    assert outcome.selection is not None
    assert outcome.selection.problems == ()
    assert dict(outcome.selection.roles) == {}
    assert dict(outcome.selection.skills) == {}


def test_the_upgrade_of_a_fresh_init_is_up_to_date_and_changes_nothing() -> None:
    """AC-12. expected_behavior_source: AC-12; BC-12 (the seed in the lock is what the render
    wants, so the next `upgrade` finds nothing to do); the existing check of `upgrade` after `init`
    in test_lifecycle.py.
    """
    env = initialised()
    before = tree(env.project)

    result = run_upgrade(env, None)

    assert result.status == "up-to-date"
    assert tree(env.project) == before


# =============================================================================================
# upgrade: a project without the file
# =============================================================================================


@pytest.mark.parametrize("mode", list(MODES))
def test_upgrade_over_a_project_without_the_file_plans_it_as_a_new_file(mode: str) -> None:
    """AC-12. expected_behavior_source: AC-12 ("`upgrade` over a project without it creates it as a
    new file"); EC-8; A-21; C-5; the state `new` of classify.py (a seeded file with no record and
    no file). The plan holds one create for the policy path, and it is not a proposal.
    """
    env = a_project_of_an_earlier_release()

    result = run_upgrade(env, None, mode)

    assert result.plan is not None
    writes = [w for w in result.plan.writes if str(w.path) == POLICY_PATH]
    assert [(w.kind, w.is_proposal) for w in writes] == [("create", False)]
    assert PROPOSAL_PATH not in written_paths(result)


def test_upgrade_over_a_project_without_the_file_writes_the_seed_and_records_it() -> None:
    """AC-12. expected_behavior_source: AC-12 ("creates it as a new file"); the interface section 4
    (a seeded file recorded in the lock). After the run the file is the shipped seed and the lock
    has its seeded row; a second run has nothing to do.
    """
    env = a_project_of_an_earlier_release()

    result = run_upgrade(env, None)

    assert result.status == "applied"
    assert read(env, POLICY_PATH) == shipped_seed()
    row = lock_row(env, POLICY_PATH)
    assert row is not None
    assert (row.owner, row.seeded_sha256) == (OwnerMode.SEEDED, sha256_hex(shipped_seed()))
    assert run_upgrade(env, None, start=200).status == "up-to-date"


@pytest.mark.parametrize("mode", ["dry-run", "check"])
def test_a_preview_of_that_upgrade_writes_no_file(mode: str) -> None:
    """AC-12. expected_behavior_source: AC-12; the existing rule of `upgrade --dry-run` and
    `--check` (no write; test_upgrade_model_policy.py). The file stays missing.
    """
    env = a_project_of_an_earlier_release()
    before = tree(env.project)

    result = run_upgrade(env, None, mode)

    assert POLICY_PATH in written_paths(result)
    assert tree(env.project) == before


# =============================================================================================
# upgrade: a project whose copy the team edited
# =============================================================================================


def test_upgrade_writes_nothing_to_a_copy_that_the_team_edited_for_the_same_release() -> None:
    """AC-12. expected_behavior_source: AC-12 ("over a project whose copy the team edited it writes
    nothing"); BC-12; EC-8; A-21 (a seeded file changes only as a proposal); the state
    `seeded-keep` of classify.py. The whole tree is the same after the run.
    """
    env = initialised()
    put(env, POLICY_PATH, team_copy())
    before = tree(env.project)

    result = run_upgrade(env, None)

    assert result.status == "up-to-date"
    assert tree(env.project) == before


def test_upgrade_writes_nothing_to_an_edited_copy_when_the_release_has_the_same_seed() -> None:
    """AC-12. expected_behavior_source: AC-12 ("over a project whose copy the team edited it writes
    nothing"); A-21. The next release changes other files, not the seed: the plan holds neither a
    write of the team's file nor a proposal for it, and the file is the team's bytes after the run.
    """
    env = initialised()
    put(env, POLICY_PATH, team_copy())

    result = run_upgrade(env, ChangedWorkflow(PINNED, version="0.2.0"))

    assert result.status == "applied"
    assert not {POLICY_PATH, PROPOSAL_PATH} & written_paths(result)
    assert read(env, POLICY_PATH) == team_copy()


# =============================================================================================
# upgrade: the shipped seed changes
# =============================================================================================


@pytest.mark.parametrize("edited", [False, True], ids=["untouched-copy", "edited-copy"])
@pytest.mark.parametrize("mode", list(MODES))
def test_a_changed_seed_is_a_proposal_and_never_a_write_of_the_team_file(
    edited: bool, mode: str
) -> None:
    """AC-12. expected_behavior_source: AC-12 ("when the shipped seed changes (a fake workflow
    whose seed differs) it writes `.orqlet/proposals/.orqlet__model-policy.yaml.diff` and never
    the team's file"); ADR-004 decision 5 (`orqlet upgrade` writes a changed shipped seed as a
    pending diff of the team's file and never overwrites it); A-21; EC-8. The plan holds the
    proposal, marked as one, and no write of the policy path itself.
    """
    env = initialised()
    if edited:
        put(env, POLICY_PATH, team_copy(2))
    before = read(env, POLICY_PATH)

    result = run_upgrade(env, NextReleaseWithSeed(version=3), mode)

    assert result.plan is not None
    assert str(proposal_path(CanonicalPath.parse(POLICY_PATH), None)) == PROPOSAL_PATH
    proposals = [w for w in result.plan.writes if str(w.path) == PROPOSAL_PATH]
    assert [(w.kind, w.is_proposal) for w in proposals] == [("create", True)]
    assert POLICY_PATH not in written_paths(result)
    assert read(env, POLICY_PATH) == before


@pytest.mark.parametrize("edited", [False, True], ids=["untouched-copy", "edited-copy"])
def test_the_proposal_of_a_changed_seed_is_a_diff_that_the_team_can_review(edited: bool) -> None:
    """AC-12. expected_behavior_source: ADR-004 decision 5 ("The diff runs from the team's current
    file to the new seed ... a merge aid"); AC-12. After an applied upgrade the proposal file
    exists, is not empty and shows the line that changed; the team's file is the bytes it had, also
    after a second run.
    """
    env = initialised()
    if edited:
        put(env, POLICY_PATH, team_copy(2))
    before = read(env, POLICY_PATH)

    result = run_upgrade(env, NextReleaseWithSeed(version=3))
    again = run_upgrade(env, NextReleaseWithSeed(version=3), start=200)

    assert result.status == "applied"
    diff = read(env, PROPOSAL_PATH).decode("utf-8")
    assert diff.strip()
    assert "policy_version" in diff
    assert read(env, POLICY_PATH) == before
    assert again.status in {"up-to-date", "applied"}
    assert read(env, POLICY_PATH) == before


# =============================================================================================
# upgrade: the role binding of the code reviewer, for a project of an earlier release
# =============================================================================================


def an_existing_project_with_two_bindings() -> Env:
    """A project that an earlier release initialised: the bindings file holds two reviewers."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            render_all,
            "REVIEW_AGENTS",
            tuple(entry for entry in render_all.REVIEW_AGENTS if entry != CODE_REVIEWER),
        )
        env = initialised()
    assert b"orqlet-code-reviewer" not in read(env, BINDINGS_PATH)
    return env


@pytest.mark.parametrize("mode", list(MODES))
def test_a_project_of_an_earlier_release_gets_the_third_binding_as_a_proposal(mode: str) -> None:
    """AC-12. expected_behavior_source: AC-12 ("A role-bindings proposal with the third binding is
    written for an existing project and is never applied"); ADR-006 decision 6 (the seeded
    binding of the third reviewer; an existing project gets it as a proposal); ADR-004 decision 5;
    A-21; C-5. The list of reviewers is the real one at the time of the upgrade, with no patch.
    """
    env = an_existing_project_with_two_bindings()

    result = run_upgrade(env, None, mode)

    assert result.plan is not None
    proposals = [w for w in result.plan.writes if str(w.path) == BINDINGS_PROPOSAL]
    assert [(w.kind, w.is_proposal) for w in proposals] == [("create", True)]
    assert BINDINGS_PATH not in written_paths(result)


def test_that_proposal_names_the_third_binding_and_the_bindings_file_stays_as_it_was() -> None:
    """AC-12. expected_behavior_source: AC-12 ("never applied"); ADR-004 decision 5; ADR-006
    decision 6. After two applied upgrades the bindings file has the bytes it had, the proposal
    shows the binding of `orqlet-code-reviewer`, and the information finding says that Orqlet never
    applies it (ORQ-I540, pinned in test_upgrade_model_policy.py).
    """
    env = an_existing_project_with_two_bindings()
    before = read(env, BINDINGS_PATH)

    first = run_upgrade(env, None)
    second = run_upgrade(env, None, start=200)

    assert first.status == "applied"
    assert read(env, BINDINGS_PATH) == before
    assert b"orqlet-code-reviewer" in read(env, BINDINGS_PROPOSAL)
    assert second.status in {"up-to-date", "applied"}
    assert read(env, BINDINGS_PATH) == before
    informed: list[Finding] = [f for f in first.findings if f.code == "ORQ-I540"]
    assert len(informed) == 1
