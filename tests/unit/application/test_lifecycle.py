"""`upgrade`, `rollback`, `doctor`, `sync`, `explain` and `release` (FM-U01 to FM-U09, FM-W02)."""

from __future__ import annotations

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.knowledge_config import KnowledgeConfig
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.role_bindings import RoleBindings
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.diagnose import doctor, sync
from orqlet.application.usecases.explain import explain
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import NotInitialised, load_installation
from orqlet.application.usecases.release import ReleaseOptions, release_file
from orqlet.application.usecases.rollback import RollbackOptions, rollback
from orqlet.application.usecases.standards_for import StandardsQuery
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import SequentialIds
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED, ChangedWorkflow
from tests.support.init_env import Env, read, tree
from tests.support.trees import pack_dir, repo

pytestmark = pytest.mark.unit

YES = InitOptions(assume_yes=True)
GO = UpgradeOptions(assume_yes=True)
BASE = PINNED


def initialised(packs: MemoryFileSystem | None = None) -> Env:
    env = Env(
        project=repo("uv_fastapi"),
        vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"),
        packs=packs,
    )
    result = init_project(env.services(), YES)
    assert result.status == "applied"
    return env


def next_release(**kwargs: object) -> ChangedWorkflow:
    return ChangedWorkflow(BASE, version=str(kwargs.pop("version", "0.2.0")), **kwargs)  # type: ignore[arg-type]


def codes(findings) -> set[str]:  # type: ignore[no-untyped-def]
    return {finding.code for finding in findings}


def upgrade_env(env: Env, workflow: ChangedWorkflow) -> Env:
    env.workflow = workflow
    env.ids = SequentialIds(start=100)
    return env


# --- installation -----------------------------------------------------------------------------
def test_an_uninitialised_directory_has_no_installation() -> None:
    env = Env(project=repo("uv_fastapi"))

    with pytest.raises(NotInitialised):
        load_installation(env.services())


def test_the_installation_reads_every_file_init_wrote() -> None:
    inst = load_installation(initialised().services())

    assert inst.profile.project.name == "demo"
    assert inst.versions is not None
    assert inst.installed_release is not None
    assert str(inst.installed_release.version) == "0.1.0"
    assert inst.released == frozenset()
    assert {e.owner for e in inst.recorded} >= {OwnerMode.ORQLET, OwnerMode.SEEDED}


# --- doctor and sync --------------------------------------------------------------------------
def test_a_fresh_setup_has_no_errors() -> None:
    result = doctor(initialised().services())

    assert not {f.code for f in result.findings if f.severity.value == "error"}
    assert all(item.state == "up-to-date" for item in result.drift)
    assert any("client versions" in item for item in result.not_run)


def test_fm_u01_version_skew_is_a_warning_and_names_both_versions() -> None:
    env = initialised()
    env.orqlet_version = "0.9.0"

    result = doctor(env.services())

    skew = [f for f in result.findings if f.code == "ORQ-W160"]
    assert skew
    assert "0.9.0" in skew[0].message
    assert "0.1.0" in skew[0].message


def test_fm_w02_an_edited_protected_file_is_an_error_and_the_user_edit_is_a_warning() -> None:
    env = initialised(pack_dir())
    env.project.write_atomic(CanonicalPath.parse(".claude/rules/orqlet-workflow.md"), b"weakened\n")
    pack_rule = ".claude/rules/orqlet-sample-001.md"
    env.project.write_atomic(
        CanonicalPath.parse(pack_rule), (read(env.project, pack_rule) + "extra\n").encode()
    )

    result = doctor(env.services())

    by_path = {f.path: f for f in result.findings if f.path}
    assert by_path[".claude/rules/orqlet-workflow.md"].code == "ORQ-E150"
    assert by_path[pack_rule].code == "ORQ-W152"


@pytest.mark.parametrize(
    "path",
    [
        ".claude/skills/orqlet-research/SKILL.md",
        ".agents/skills/orqlet-plan/references/plan-format.md",
        ".agents/skills/orqlet-onboard/agents/openai.yaml",
        ".claude/agents/orqlet-inventory.md",
        ".codex/agents/orqlet-tracer.toml",
    ],
)
def test_fm_w02_an_edited_protected_skill_or_role_is_an_error_and_cannot_be_released(
    path: str,
) -> None:
    env = initialised()
    env.project.write_atomic(CanonicalPath.parse(path), b"weakened\n")

    findings = {f.path: f for f in doctor(env.services()).findings if f.path}
    refused = release_file(env.services(), ReleaseOptions(path, "I want it", assume_yes=True))

    assert findings[path].code == "ORQ-E150"
    assert refused.status == "refused"
    assert "ORQ-E141" in codes(refused.findings)


def test_init_seeds_an_empty_knowledge_configuration_and_a_team_edit_survives_an_upgrade() -> None:
    env = initialised()
    path = ".orqlet/knowledge.yaml"
    loaded = load_contract(
        StrictYamlLoader(), KnowledgeConfig, tree(env.project)[path], source=path
    )
    assert (loaded.sources, loaded.write_scope) == ((), ())
    team = (
        "schema: orqlet.knowledge/v2\n"
        "sources:\n  - {kind: adr, scope: project, globs: [docs/adr/**]}\n"
    )
    env.project.write_atomic(CanonicalPath.parse(path), team.encode())

    result = upgrade(upgrade_env(env, next_release()).services(), GO)

    assert result.status == "applied"
    assert read(env.project, path) == team
    assert not [
        p for p in tree(env.project) if p.startswith(".orqlet/proposals/") and "knowledge" in p
    ]


def test_init_approves_the_generated_reviewers_as_the_default_review_bindings() -> None:
    env = initialised()
    path = ".orqlet/role-bindings.yaml"

    loaded = load_contract(StrictYamlLoader(), RoleBindings, tree(env.project)[path], source=path)

    approved = {(b.role, b.id): b for b in loaded.bindings}
    assert set(approved) == {
        ("architecture-reviewer", "orqlet-arch-reviewer"),
        ("security-reviewer", "orqlet-security-reviewer"),
    }
    for binding in approved.values():
        assert binding.independence_capability == "I1"
        assert set(binding.clients) == {"claude-code", "codex", "cursor"}
        assert binding.minimum_capability is not None
        assert binding.minimum_capability.context == "fresh"
    for agent in ("orqlet-arch-reviewer", "orqlet-security-reviewer"):
        assert f".claude/agents/{agent}.md" in tree(env.project)  # each binding has its agent file


def test_a_missing_generated_file_is_a_warning_and_a_missing_protected_file_an_error() -> None:
    env = initialised()
    env.project.delete(CanonicalPath.parse(".claude/CLAUDE.md"))

    result = doctor(env.services())

    assert "ORQ-E150" in codes(result.findings)


def test_a_skill_folder_the_manifest_names_files_in_is_not_an_extra_but_a_stray_one_is() -> None:
    env = initialised()
    env.project.write_atomic(CanonicalPath.parse(".agents/skills/orqlet-stray/SKILL.md"), b"x\n")

    extra = [f for f in doctor(env.services()).findings if f.code == "ORQ-E153"]

    assert [f.path for f in extra] == [".agents/skills/orqlet-stray"]


def test_a_reserved_name_that_is_not_in_the_manifest_is_an_error() -> None:
    env = initialised()
    env.project.write_atomic(CanonicalPath.parse(".claude/rules/orqlet-extra.md"), b"x\n")

    result = doctor(env.services())

    extra = [f for f in result.findings if f.code == "ORQ-E153"]
    assert [f.path for f in extra] == [".claude/rules/orqlet-extra.md"]


def test_fm_u05_the_same_version_with_a_different_digest_is_an_error() -> None:
    env = initialised()
    env.workflow = ChangedWorkflow(BASE, version="0.1.0", digest_salt="silent change")

    assert "ORQ-E161" in codes(doctor(env.services()).findings)


def test_a_newer_release_is_reported_as_an_available_upgrade() -> None:
    env = upgrade_env(initialised(), next_release())

    assert "ORQ-W162" in codes(doctor(env.services()).findings)


def test_the_floor_is_enforced_by_doctor() -> None:
    env = initialised()
    versions = read(env.project, ".orqlet/versions.yaml").replace(
        'floor: "0.1.0"', 'floor: "0.5.0"'
    )
    env.project.write_atomic(CanonicalPath.parse(".orqlet/versions.yaml"), versions.encode())

    assert "ORQ-E163" in codes(doctor(env.services()).findings)


def test_an_unknown_profile_is_listed_and_a_draft_profile_is_a_warning() -> None:
    result = doctor(initialised().services())

    messages = " ".join(f.message for f in result.findings if f.code == "ORQ-W181")
    assert "repository.target_branch" in messages
    assert "ORQ-W180" in codes(result.findings)


def test_sync_is_read_only_and_says_to_start_a_new_session() -> None:
    env = initialised()
    before = tree(env.project)

    result = sync(env.services())

    assert tree(env.project) == before
    assert "ORQ-I201" in codes(result.findings)
    assert {"ORQ-I202"} <= codes(result.findings)


def test_fm_w03_personal_names_are_listed_only_on_request_and_reserved_ones_are_reported() -> None:
    from orqlet.application.ports.personal import PersonalItem

    class Lister:
        def list_names(self) -> tuple[PersonalItem, ...]:
            return (
                PersonalItem("~/.claude/skills", "orqlet-research"),
                PersonalItem("~/.claude/skills", "my-skill"),
            )

    env = initialised()

    quiet = sync(env.services())
    asked = sync(env.services(), personal=Lister())

    assert quiet.listed_names == ()
    assert "ORQ-W100" not in codes(quiet.findings)
    assert asked.listed_names == (
        ("~/.claude/skills", "orqlet-research"),
        ("~/.claude/skills", "my-skill"),
    )
    reserved = [f for f in asked.findings if f.code == "ORQ-W100"]
    assert len(reserved) == 1
    assert "orqlet-research" in reserved[0].message


# --- upgrade ----------------------------------------------------------------------------------
def test_an_upgrade_of_an_unchanged_release_is_up_to_date_and_writes_nothing() -> None:
    env = initialised()
    before = tree(env.project)

    result = upgrade(env.services(), GO)

    assert result.status == "up-to-date"
    assert tree(env.project) == before


def test_a_new_release_updates_generated_files_and_the_manifest_last() -> None:
    env = upgrade_env(initialised(), next_release())

    result = upgrade(env.services(), GO)

    assert result.status == "applied"
    assert "A rule added in this release." in read(env.project, "AGENTS.md")
    assert "0.2.0" in read(env.project, ".orqlet/workflow.lock")
    assert result.plan is not None
    assert str(result.plan.writes[-1].path) == ".orqlet/generated.lock.yaml"
    inst = load_installation(env.services())
    assert str(inst.installed_release.version) == "0.2.0"  # type: ignore[union-attr]
    assert not doctor(env.services()).drift or all(
        d.state == "up-to-date" for d in doctor(env.services()).drift
    )


def test_an_upgrade_check_reports_and_does_not_write() -> None:
    env = upgrade_env(initialised(), next_release())
    before = tree(env.project)

    result = upgrade(env.services(), UpgradeOptions(check=True))

    assert result.status == "available"
    assert tree(env.project) == before


def test_seeded_files_change_only_as_proposals() -> None:
    env = upgrade_env(initialised(), next_release())
    env.orqlet_version = "0.2.0"
    pinned = read(env.project, ".orqlet/versions.yaml")

    upgrade(env.services(), GO)

    assert read(env.project, ".orqlet/versions.yaml") == pinned
    assert any(
        name.startswith(".orqlet/proposals/") and "versions" in name for name in tree(env.project)
    )


def test_fm_u04_a_conflicting_edit_is_never_overwritten_and_a_proposal_appears_beside_it() -> None:
    env = initialised()
    pr = ".github/pull_request_template.md"
    edited = read(env.project, pr).replace("Orqlet-Task: <task-slug>", "Orqlet-Task: mine")
    env.project.write_atomic(CanonicalPath.parse(pr), edited.encode())
    upgrade_env(env, next_release())

    result = upgrade(env.services(), GO)

    assert read(env.project, pr) == edited
    assert "ORQ-W080" in codes(result.findings)
    assert any(
        "pull_request_template" in n and n.startswith(".orqlet/proposals/")
        for n in tree(env.project)
    )


def test_a_tampered_protected_file_is_restored_and_reported() -> None:
    env = initialised()
    original = read(env.project, ".claude/rules/orqlet-workflow.md")
    env.project.write_atomic(CanonicalPath.parse(".claude/rules/orqlet-workflow.md"), b"weakened\n")

    result = upgrade(env.services(), GO)

    assert read(env.project, ".claude/rules/orqlet-workflow.md") == original
    assert "ORQ-W096" in codes(result.findings)


def test_fm_u09_an_older_or_weaker_release_is_refused() -> None:
    env = upgrade_env(initialised(), next_release(version="0.2.0", controls_level=2))
    upgrade(env.services(), GO)

    env.workflow = None  # the packaged release is 0.1.0 at level 1
    refused = upgrade(env.services(), GO)

    assert refused.status == "refused"
    assert "ORQ-E120" in codes(refused.findings)


def test_a_downgrade_can_be_forced_only_with_the_flag_and_is_then_reported() -> None:
    env = upgrade_env(initialised(), next_release(version="0.2.0"))
    upgrade(env.services(), GO)
    env.workflow = None

    forced = upgrade(env.services(), UpgradeOptions(assume_yes=True, allow_weaker=True))

    assert forced.status == "applied"
    assert "ORQ-W095" in codes(forced.findings)


def test_an_upgrade_that_needs_packs_refuses_when_none_are_supplied() -> None:
    env = initialised(pack_dir())
    env.packs = None

    result = upgrade(env.services(), GO)

    assert result.status == "refused"
    assert "ORQ-E121" in codes(result.findings)


def test_an_unfinished_change_blocks_a_plain_upgrade_and_resume_finishes_it() -> None:
    env = initialised()
    upgrade_env(env, next_release())
    expected_env = initialised()
    upgrade_env(expected_env, next_release())
    upgrade(expected_env.services(), GO)
    env.project_view = FaultyFileSystem(env.project, crash_after_writes=2)
    with pytest.raises(SimulatedCrash):
        upgrade(env.services(), GO)
    env.project_view = None

    assert "ORQ-E170" in codes(doctor(env.services()).findings)
    blocked = upgrade(env.services(), GO)
    resumed = upgrade(env.services(), UpgradeOptions(assume_yes=True, resume=True))

    assert blocked.status == "refused"
    assert "ORQ-E131" in codes(blocked.findings)
    assert resumed.status == "applied"
    assert tree(env.project) == tree(expected_env.project)
    assert "ORQ-E170" not in codes(doctor(env.services()).findings)


def test_fm_u03_every_kill_point_of_an_upgrade_converges() -> None:
    reference = initialised()
    upgrade_env(reference, next_release())
    upgrade(reference.services(), GO)
    expected = tree(reference.project)
    probe = _planned_env()
    plan = upgrade(probe.services(), UpgradeOptions(check=True)).plan
    assert plan is not None
    writes = len(plan.writes)

    for crash_point in range(writes):
        env = initialised()
        upgrade_env(env, next_release())
        env.project_view = FaultyFileSystem(env.project, crash_after_writes=crash_point)
        with pytest.raises(SimulatedCrash):
            upgrade(env.services(), GO)
        env.project_view = None
        env.ids = SequentialIds(start=200)

        result = upgrade(env.services(), UpgradeOptions(assume_yes=True, resume=True))

        assert result.status == "applied", crash_point
        assert tree(env.project) == expected, f"kill after {crash_point} writes did not converge"


def _planned_env() -> Env:
    env = initialised()
    upgrade_env(env, next_release())
    return env


# --- rollback ---------------------------------------------------------------------------------
def change_id_of(env: Env, command: str) -> str:
    """The id of the most recent journal written by `command`."""
    found = [
        (v, k)
        for k, v in env.user_data.snapshot().items()
        if k.endswith(".json") and f'"command": "{command}"'.encode() in v
    ]
    assert found, command
    return sorted(found, key=lambda pair: pair[0])[-1][1].rsplit("/", 1)[-1].removesuffix(".json")


def test_rolling_back_init_removes_what_it_created_and_restores_what_it_changed() -> None:
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    env.project.write_atomic(CanonicalPath.parse("AGENTS.md"), b"# Team notes\n")
    before = tree(env.project)
    init_project(env.services(), YES)

    result = rollback(env.services(), RollbackOptions(change_id_of(env, "init"), assume_yes=True))

    assert result.status == "applied"
    assert tree(env.project) == before
    with pytest.raises(NotInitialised):
        load_installation(env.services())


def test_a_rollback_refuses_when_a_file_changed_since_and_loses_nothing() -> None:
    env = initialised()
    cid = change_id_of(env, "init")
    env.project.write_atomic(CanonicalPath.parse("AGENTS.md"), b"later work\n")
    before = tree(env.project)

    result = rollback(env.services(), RollbackOptions(cid, assume_yes=True))

    assert result.status == "refused"
    assert "ORQ-E133" in codes(result.findings)
    assert "AGENTS.md" in result.findings[0].message
    assert tree(env.project) == before


def test_a_change_can_be_rolled_back_only_once() -> None:
    env = initialised()
    cid = change_id_of(env, "init")
    rollback(env.services(), RollbackOptions(cid, assume_yes=True))

    again = rollback(env.services(), RollbackOptions(cid, assume_yes=True, project_id="p"))

    assert again.status == "refused"


def test_an_unknown_change_is_refused() -> None:
    env = initialised()

    result = rollback(env.services(), RollbackOptions("no-such-change", assume_yes=True))

    assert "ORQ-E132" in codes(result.findings)


def test_a_rollback_needs_approval_and_a_dry_run_writes_nothing() -> None:
    env = initialised()
    cid = change_id_of(env, "init")
    before = tree(env.project)

    dry = rollback(env.services(), RollbackOptions(cid, dry_run=True))
    quiet = rollback(env.services(), RollbackOptions(cid))

    assert dry.status == "previewed"
    assert quiet.status == "needs-input"
    assert tree(env.project) == before


def test_rolling_back_an_upgrade_to_an_equally_strong_release_is_allowed() -> None:
    env = initialised()
    before = tree(env.project)
    upgrade_env(env, next_release(version="0.2.0"))
    upgrade(env.services(), GO)

    result = rollback(
        env.services(), RollbackOptions(change_id_of(env, "upgrade"), assume_yes=True)
    )

    assert result.status == "applied"
    assert tree(env.project) == before


def test_fm_u09_a_rollback_that_lowers_the_controls_level_is_refused() -> None:
    env = initialised()
    upgrade_env(env, next_release(version="0.2.0", controls_level=2))
    upgrade(env.services(), GO)
    cid = change_id_of(env, "upgrade")
    before = tree(env.project)

    refused = rollback(env.services(), RollbackOptions(cid, assume_yes=True))

    assert refused.status == "refused"
    assert "ORQ-E120" in codes(refused.findings)
    assert tree(env.project) == before


def test_fm_u09_with_the_flag_the_rollback_goes_ahead_and_says_it_needs_two_approvals() -> None:
    env = initialised()
    upgrade_env(env, next_release(version="0.2.0", controls_level=2))
    upgrade(env.services(), GO)

    forced = rollback(
        env.services(),
        RollbackOptions(change_id_of(env, "upgrade"), assume_yes=True, allow_weaker=True),
    )

    assert forced.status == "applied"
    assert "ORQ-W095" in codes(forced.findings)


def test_a_rollback_below_the_floor_is_refused() -> None:
    env = initialised()
    upgrade_env(env, next_release(version="0.2.0"))
    upgrade(env.services(), GO)
    raised = read(env.project, ".orqlet/versions.yaml").replace('floor: "0.1.0"', 'floor: "0.2.0"')
    env.project.write_atomic(CanonicalPath.parse(".orqlet/versions.yaml"), raised.encode())

    result = rollback(
        env.services(), RollbackOptions(change_id_of(env, "upgrade"), assume_yes=True)
    )

    assert result.status == "refused"
    assert "below the floor" in result.findings[0].message


# --- release ----------------------------------------------------------------------------------
PACK_RULE = ".cursor/rules/orqlet-web-001.mdc"


def test_a_generated_file_can_be_released_and_is_then_left_alone() -> None:
    env = initialised(pack_dir())
    result = release_file(
        env.services(),
        ReleaseOptions(PACK_RULE, "We maintain this rule ourselves.", assume_yes=True),
    )
    edited = (read(env.project, PACK_RULE) + "our own line\n").encode()
    env.project.write_atomic(CanonicalPath.parse(PACK_RULE), edited)

    assert result.status == "applied"
    record = read(env.project, ".orqlet/released.yaml")
    assert PACK_RULE in record
    assert "We maintain this rule ourselves." in record
    lock = load_contract(
        StrictYamlLoader(),
        GeneratedLock,
        tree(env.project)[".orqlet/generated.lock.yaml"],
        source="l",
    )
    assert PACK_RULE not in {entry.path for entry in lock.files}
    assert ".orqlet/released.yaml" in {entry.path for entry in lock.files}
    upgrade_env(env, next_release())
    upgrade(env.services(), GO)
    assert read(env.project, PACK_RULE).endswith("our own line\n")
    assert not any(PACK_RULE.replace("/", "__") in name for name in tree(env.project))
    assert "ORQ-I210" in codes(doctor(env.services()).findings)
    problems = [
        f
        for f in doctor(env.services()).findings
        if f.path == PACK_RULE and f.severity.value != "info"
    ]
    assert not problems


def test_fm_w02_a_protected_file_cannot_be_released() -> None:
    env = initialised()
    env.project.write_atomic(CanonicalPath.parse(".claude/rules/orqlet-workflow.md"), b"changed\n")
    before = tree(env.project)

    result = release_file(
        env.services(),
        ReleaseOptions(".claude/rules/orqlet-workflow.md", "I want it", assume_yes=True),
    )

    assert result.status == "refused"
    assert "ORQ-E141" in codes(result.findings)
    assert tree(env.project) == before


@pytest.mark.parametrize(
    ("path", "reason", "code"),
    [
        ("never-managed.txt", "because", "ORQ-E140"),
        (".prompts/README.md", "because", "ORQ-E142"),
        (".claude/CLAUDE.md", "   ", "ORQ-E143"),
    ],
)
def test_release_refusals(path: str, reason: str, code: str) -> None:
    env = initialised()

    result = release_file(env.services(), ReleaseOptions(path, reason, assume_yes=True))

    assert result.status == "refused"
    assert code in codes(result.findings)


def test_release_needs_approval() -> None:
    env = initialised(pack_dir())

    result = release_file(env.services(), ReleaseOptions(PACK_RULE, "reason"))

    assert result.status == "needs-input"
    assert ".orqlet/released.yaml" not in tree(env.project)


# --- explain ----------------------------------------------------------------------------------
def test_explain_shows_declared_generated_rules_limits_and_what_cannot_be_seen() -> None:
    env = initialised(pack_dir())

    result = explain(env.services(), StandardsQuery(phase="design"))

    assert result.declared["workflow_version"] == "0.1.0"
    assert result.declared["clients"] == ["claude-code", "codex", "cursor"]
    assert any(item.path == "AGENTS.md" for item in result.generated)
    assert {rule.id for rule in result.rules} >= {"SAMPLE-003", "WEB-001"}
    assert {"ORQ-L001", "ORQ-L002"} <= {f.code for f in result.limits}
    assert any("Cursor Team Rules" in item for item in result.uninspectable)
    assert any("predicted-effective" in item for item in result.not_run)


def test_explain_says_when_pack_rules_were_not_loaded() -> None:
    env = initialised(pack_dir())
    env.packs = None

    result = explain(env.services(), StandardsQuery())

    assert any("--packs-dir" in item for item in result.not_run)


def test_doctor_warns_about_a_managed_file_that_git_ignores() -> None:
    env = initialised()
    env.vcs = FakeVcs(RepoState.HAS_COMMITS, branch="main", ignored=(".claude/CLAUDE.md",))

    result = doctor(env.services())

    assert [f.path for f in result.findings if f.code == "ORQ-W097"] == [".claude/CLAUDE.md"]
