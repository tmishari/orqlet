"""`init` for existing, new and empty projects, with fakes for every port (FM-N, FM-P)."""

from __future__ import annotations

import json

import pytest

from orqlet.adapters.fs.journal import FsBackupStore, FsChangeJournal
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.apply_plan import PlanStale, apply_plan
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.domain.changeplan import Desired, build_plan
from orqlet.domain.digest import sha256_hex
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath
from tests.fakes.clock import FixedClock
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import ReplayIds, SequentialIds
from tests.fakes.lock import NoLock
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.prompter import ScriptedPrompter
from tests.fakes.vcs import FakeVcs
from tests.support.init_env import Env, read, tree
from tests.support.trees import pack_dir, repo, tech_packs, with_files

pytestmark = pytest.mark.unit

LOADER = StrictYamlLoader()
YES = InitOptions(assume_yes=True)


def existing_env(name: str = "uv_fastapi", **kwargs: object) -> Env:
    return Env(project=repo(name), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"), **kwargs)  # type: ignore[arg-type]


def codes(result) -> set[str]:  # type: ignore[no-untyped-def]
    return {finding.code for finding in result.findings}


# --- existing project ---------------------------------------------------------------------------
def test_an_existing_project_gets_every_expected_file() -> None:
    env = existing_env()

    result = init_project(env.services(), YES)

    assert result.status == "applied"
    written = set(tree(env.project))
    assert {
        "AGENTS.md",
        ".claude/CLAUDE.md",
        ".claude/rules/orqlet-workflow.md",
        ".cursor/rules/orqlet-workflow.mdc",
        ".prompts/README.md",
        ".prompts/foundations.md",
        ".prompts/rules.yaml",
        ".github/pull_request_template.md",
        ".orqlet/project-profile.yaml",
        ".orqlet/versions.yaml",
        ".orqlet/role-bindings.yaml",
        ".orqlet/standards.lock.yaml",
        ".orqlet/workflow.lock",
        ".orqlet/generated.lock.yaml",
    } <= written


def test_a_git_directory_in_the_project_is_ignored_when_looking_for_templates() -> None:
    env = existing_env()
    env.project.write_atomic(CanonicalPath.parse("x"), b"")  # keep the root listing non-trivial
    env.project.add_dir(".git")

    result = init_project(env.services(), YES)

    assert result.status == "applied"


def test_the_profile_records_evidence_and_leaves_unknowns_as_questions() -> None:
    env = existing_env()

    result = init_project(env.services(), YES)

    profile = load_contract(
        LOADER, ProjectProfile, tree(env.project)[".orqlet/project-profile.yaml"], source="p"
    )
    assert profile.facts.package_manager.value == "uv"
    assert profile.facts.python.value == ">=3.12"
    assert profile.repository.target_branch.value is None
    assert profile.profile.status == "draft"
    assert [q.id for q in result.open_questions] == [
        "repository.target_branch",
        "repository.branch_naming",
        "repository.commit_convention",
    ]


def test_answers_are_recorded_as_the_maintainers_and_the_profile_can_be_approved() -> None:
    env = existing_env()
    options = InitOptions(
        assume_yes=True,
        answers={"repository.target_branch": "trunk", "reviewer": "Ada"},
    )

    init_project(env.services(), options)

    profile = load_contract(
        LOADER, ProjectProfile, tree(env.project)[".orqlet/project-profile.yaml"], source="p"
    )
    assert profile.repository.target_branch.value == "trunk"
    assert profile.repository.target_branch.answered_by == "maintainer"
    assert (profile.profile.status, profile.profile.reviewed_by) == ("approved", "Ada")


def test_a_bad_answer_is_ignored_with_a_warning_not_recorded() -> None:
    env = existing_env()
    options = InitOptions(assume_yes=True, answers={"repository.target_branch": "../etc"})

    result = init_project(env.services(), options)

    assert "ORQ-W060" in codes(result)
    assert result.profile is not None
    assert result.profile.repository.target_branch.value is None


def test_the_lock_lists_every_written_file_with_the_hash_of_what_was_written() -> None:
    env = existing_env()
    init_project(env.services(), YES)
    files = tree(env.project)
    lock = load_contract(LOADER, GeneratedLock, files[".orqlet/generated.lock.yaml"], source="l")

    listed = {entry.path for entry in lock.files}
    written_by_init = (
        set(files) - set(repo("uv_fastapi").snapshot()) - {".orqlet/generated.lock.yaml"}
    )
    assert listed >= written_by_init - {
        name for name in written_by_init if name.startswith(".orqlet/proposals/")
    }
    for entry in lock.files:
        recorded = entry.rendered_sha256 or entry.seeded_sha256
        if entry.block is None:
            assert recorded == sha256_hex(files[entry.path]), entry.path
    assert {e.owner.value for e in lock.files} == {"orqlet", "shared-block", "seeded"}


def test_a_second_run_reports_already_initialised_and_changes_nothing() -> None:
    env = existing_env()
    init_project(env.services(), YES)
    before = tree(env.project)

    second = init_project(env.services(), YES)

    assert second.status == "already-initialised"
    assert "ORQ-I010" in codes(second)
    assert tree(env.project) == before


def test_dry_run_and_a_missing_approval_write_nothing() -> None:
    dry = existing_env()
    unapproved = existing_env()

    dry_result = init_project(dry.services(), InitOptions(dry_run=True))
    quiet_result = init_project(unapproved.services(), InitOptions())

    assert dry_result.status == "previewed"
    assert quiet_result.status == "needs-input"
    assert "ORQ-E115" in codes(quiet_result)
    assert tree(dry.project) == tree(unapproved.project) == tree(repo("uv_fastapi"))


def test_an_interactive_maintainer_answers_and_approves() -> None:
    answers = {
        "repository.target_branch": "main",
        "repository.branch_naming": "",
        "repository.commit_convention": "",
        "reviewer": "Ada",
    }
    prompter = ScriptedPrompter(answers, interactive=True, confirm_all=True)
    env = existing_env(prompter=prompter)

    result = init_project(env.services(), InitOptions())

    assert result.status == "applied"
    assert "repository.target_branch" in prompter.asked
    assert result.profile is not None
    assert result.profile.profile.reviewed_by == "Ada"


def test_an_interactive_maintainer_who_declines_changes_nothing() -> None:
    env = existing_env(
        prompter=ScriptedPrompter(
            {
                "repository.target_branch": "",
                "repository.branch_naming": "",
                "repository.commit_convention": "",
                "reviewer": "",
            },
            interactive=True,
            confirm_all=False,
        )
    )

    result = init_project(env.services(), InitOptions())

    assert result.status == "previewed"
    assert tree(env.project) == tree(repo("uv_fastapi"))


def test_a_javascript_project_is_recognised_without_python_questions_or_invented_standards() -> (
    None
):
    env = existing_env("js_only")

    result = init_project(env.services(), YES)

    assert result.status == "applied"
    profile = result.profile
    assert profile is not None
    assert profile.stack.support == "partly-covered"
    assert "no built-in standards" in profile.stack.capability_limits[0]
    assert {t.name for t in profile.technologies} >= {"JavaScript", "Express"}
    assert all(t.evidence for t in profile.technologies)
    ids = {q.id for q in result.open_questions}
    assert "facts.python" not in ids
    assert "repository.target_branch" in ids
    assert env.prompter.asked == []


def test_a_monorepo_gets_every_service_s_technologies_and_no_whole_repository_python_question() -> (
    None
):
    env = existing_env("monorepo")

    result = init_project(env.services(), YES)

    profile = result.profile
    assert profile is not None
    found = {(t.scope, t.name) for t in profile.technologies}
    assert {(".", "PostgreSQL"), ("apiserver", "Gin"), ("services/billing", "FastAPI")} <= found
    assert "facts.python" not in {q.id for q in result.open_questions}
    written = read(env.project, ".orqlet/project-profile.yaml")
    assert "scope: apiserver" in written
    assert "scope: services/billing" in written


def test_technology_packs_apply_by_language_and_by_technology_name() -> None:
    env = existing_env("monorepo", packs=tech_packs())

    result = init_project(env.services(), InitOptions(assume_yes=True, packs_path="packs"))

    lock = read(env.project, ".orqlet/standards.lock.yaml")
    assert "id: go" in lock
    assert "id: data" in lock
    assert "id: python-only" in lock  # the monorepo also has Python services
    files = tree(env.project)
    assert ".claude/rules/orqlet-go-001.md" in files
    assert ".cursor/rules/orqlet-data-001.mdc" in files
    assert result.profile is not None


def test_a_go_only_project_does_not_get_python_packs() -> None:
    env = existing_env("go_service", packs=tech_packs())

    init_project(env.services(), InitOptions(assume_yes=True, packs_path="packs"))

    lock = read(env.project, ".orqlet/standards.lock.yaml")
    assert "id: go" in lock
    assert "id: data" in lock  # PostgreSQL and Kafka are in its files
    assert "python-only" not in lock


def test_a_new_project_names_its_technologies_and_they_need_no_evidence() -> None:
    env = Env(project=MemoryFileSystem(), vcs=FakeVcs(RepoState.UNBORN_EMPTY, branch="main"))
    options = InitOptions(
        assume_yes=True,
        answers={"technologies": "language:Go@1.25, database:PostgreSQL@16, queue:Kafka, Redis"},
    )

    result = init_project(env.services(), options)

    profile = result.profile
    assert profile is not None
    stated = {(t.kind, t.name, t.version, t.source) for t in profile.technologies}
    assert stated == {
        ("language", "Go", "1.25", "maintainer"),
        ("database", "PostgreSQL", "16", "maintainer"),
        ("queue", "Kafka", None, "maintainer"),
        ("other", "Redis", None, "maintainer"),
    }
    assert profile.stack.support == "partly-covered"


def test_a_malformed_technology_answer_is_ignored_with_a_warning() -> None:
    env = Env(project=MemoryFileSystem(), vcs=FakeVcs(RepoState.UNBORN_EMPTY, branch="main"))
    options = InitOptions(
        assume_yes=True, answers={"technologies": "weird:Thing, Go@1.25, <script>"}
    )

    result = init_project(env.services(), options)

    assert result.profile is not None
    assert [t.name for t in result.profile.technologies] == ["Go"]
    assert sum(f.code == "ORQ-W060" for f in result.findings) == 2


# --- new and empty projects -----------------------------------------------------------------------
def test_an_empty_directory_without_a_repository_stops_after_the_preview() -> None:
    env = Env(project=MemoryFileSystem(), vcs=FakeVcs(RepoState.NOT_A_REPOSITORY))

    result = init_project(env.services(), YES)

    assert result.status == "previewed"
    assert "ORQ-E112" in codes(result)
    assert result.needs_git
    assert tree(env.project) == {}
    assert env.vcs.state() is RepoState.NOT_A_REPOSITORY


def test_git_init_needs_a_target_branch_and_never_assumes_main() -> None:
    env = Env(project=MemoryFileSystem(), vcs=FakeVcs(RepoState.NOT_A_REPOSITORY))

    result = init_project(env.services(), InitOptions(assume_yes=True, git_init=True))

    assert result.status == "needs-input"
    assert "ORQ-E113" in codes(result)
    assert env.vcs.state() is RepoState.NOT_A_REPOSITORY


def test_an_empty_directory_with_git_init_and_answers_becomes_a_supported_project() -> None:
    env = Env(project=MemoryFileSystem(), vcs=FakeVcs(RepoState.NOT_A_REPOSITORY))
    options = InitOptions(
        assume_yes=True,
        git_init=True,
        answers={
            "repository.target_branch": "trunk",
            "facts.python": ">=3.12",
            "facts.package_manager": "uv",
            "project.kind": "python-service",
            "facts.frameworks": "FastAPI, SQLAlchemy",
            "structure.test_runner": "pytest",
        },
    )

    result = init_project(env.services(), options)

    assert result.status == "applied"
    assert result.git_initialised
    assert env.vcs.state() is RepoState.UNBORN_EMPTY
    assert env.vcs.current_branch() == "trunk"
    profile = result.profile
    assert profile is not None
    assert profile.project.origin == "empty"
    assert profile.stack.support == "supported"
    assert [f.name for f in profile.facts.frameworks] == ["FastAPI", "SQLAlchemy"]
    assert profile.structure["test_runner"].value == "pytest"
    assert "AGENTS.md" in tree(env.project)


def test_an_unborn_repository_is_a_new_project_with_no_scaffolding_written() -> None:
    env = Env(project=MemoryFileSystem(), vcs=FakeVcs(RepoState.UNBORN_EMPTY, branch="main"))

    result = init_project(env.services(), YES)

    assert result.status == "applied"
    assert result.profile is not None
    assert result.profile.project.origin == "unborn"
    assert not any(name.startswith(("src/", "tests/")) for name in tree(env.project))
    assert "pyproject.toml" not in tree(env.project)


def test_a_repository_with_commits_and_no_code_asks_the_new_project_questions() -> None:
    project = with_files({"README.md": "# Readme\n"})
    env = Env(project=project, vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))

    result = init_project(env.services(), YES)

    assert result.profile is not None
    assert result.profile.project.origin == "existing-no-code"
    assert "facts.python" in {q.id for q in result.open_questions}


def test_a_non_empty_directory_that_looks_like_nothing_is_not_guessed_at() -> None:
    project = with_files({"notes.txt": "loose file\n"})
    env = Env(project=project, vcs=FakeVcs(RepoState.NOT_A_REPOSITORY))

    refused = init_project(env.services(), InitOptions(git_init=True, assume_yes=True))
    accepted = init_project(
        env.services(),
        InitOptions(
            git_init=True,
            assume_yes=True,
            new_project=True,
            answers={"repository.target_branch": "main"},
        ),
    )

    assert refused.status == "refused"
    assert "ORQ-E111" in codes(refused)
    assert accepted.status == "applied"


def test_a_directory_with_an_ide_folder_is_not_empty() -> None:
    project = with_files({".vscode/settings.json": "{}\n"})
    env = Env(project=project, vcs=FakeVcs(RepoState.NOT_A_REPOSITORY))

    result = init_project(env.services(), YES)

    assert result.status == "refused"


def test_a_directory_inside_another_repository_is_refused() -> None:
    env = Env(project=MemoryFileSystem(), vcs=FakeVcs(RepoState.NESTED))

    result = init_project(env.services(), YES)

    assert result.status == "refused"
    assert "ORQ-E110" in codes(result)


# --- files the team already owns -------------------------------------------------------
def test_an_existing_agents_file_keeps_its_text_and_gains_one_block() -> None:
    env = existing_env()
    env.project.write_atomic(CanonicalPath.parse("AGENTS.md"), b"# Team notes\n\nKeep this.\n")

    init_project(env.services(), YES)

    text = read(env.project, "AGENTS.md")
    assert text.startswith("# Team notes\n\nKeep this.\n")
    assert text.count("<!-- orqlet:begin baseline") == 1


def test_an_existing_claude_file_gets_an_import_and_no_bridge_is_created() -> None:
    env = existing_env()
    env.project.write_atomic(CanonicalPath.parse("CLAUDE.md"), b"# Claude notes\n")

    init_project(env.services(), YES)

    assert "@AGENTS.md" in read(env.project, "CLAUDE.md")
    assert read(env.project, "CLAUDE.md").startswith("# Claude notes\n")
    assert ".claude/CLAUDE.md" not in tree(env.project)


def test_personal_files_and_an_ancestor_file_are_never_touched_and_the_ancestor_is_reported() -> (
    None
):
    env = existing_env(ancestors=("/home/dev/CLAUDE.md",))
    env.project.write_atomic(CanonicalPath.parse("CLAUDE.local.md"), b"my private notes\n")
    env.project.write_atomic(CanonicalPath.parse(".claude/settings.local.json"), b"{}\n")
    before = {k: v for k, v in tree(env.project).items() if "local" in k}

    result = init_project(env.services(), YES)

    after = {k: v for k, v in tree(env.project).items() if "local" in k}
    assert after == before
    assert "ORQ-I020" in codes(result)


def test_an_existing_prompts_folder_is_not_rewritten_and_a_clash_becomes_a_proposal() -> None:
    env = existing_env()
    env.project.write_atomic(CanonicalPath.parse(".prompts/README.md"), b"Our own readme\n")

    result = init_project(env.services(), YES)

    files = tree(env.project)
    assert files[".prompts/README.md"] == b"Our own readme\n"
    assert ".prompts/foundations.md" in files
    assert any(name.startswith(".orqlet/proposals/") and "README" in name for name in files)
    assert "ORQ-I031" in codes(result)


def test_the_codeowners_suggestion_is_made_once_and_written_nowhere() -> None:
    env = existing_env()

    result = init_project(env.services(), YES)

    assert "ORQ-I030" in codes(result)
    assert not any("CODEOWNERS" in name for name in tree(env.project))


# --- pull-request template ---------------------------------------------------------------
def test_one_existing_template_receives_the_blocks_and_keeps_its_text() -> None:
    env = existing_env()
    env.project.write_atomic(
        CanonicalPath.parse(".github/PULL_REQUEST_TEMPLATE.md"),
        b"# Pull request\n\nOur checklist.\n",
    )

    init_project(env.services(), YES)

    text = read(env.project, ".github/PULL_REQUEST_TEMPLATE.md")
    assert text.startswith("# Pull request\n")
    assert text.endswith("\nOur checklist.\n")
    assert "orqlet:begin orqlet-workflow" in text
    assert ".github/pull_request_template.md" not in tree(env.project)


def test_several_templates_are_never_chosen_for_the_maintainer() -> None:
    env = existing_env()
    env.project.write_atomic(CanonicalPath.parse(".github/pull_request_template.md"), b"# A\n")
    env.project.write_atomic(CanonicalPath.parse("docs/pull_request_template.md"), b"# B\n")

    result = init_project(env.services(), YES)

    assert "ORQ-W050" in codes(result)
    assert read(env.project, ".github/pull_request_template.md") == "# A\n"
    assert read(env.project, "docs/pull_request_template.md") == "# B\n"


def test_the_maintainer_can_pick_which_templates_receive_the_blocks() -> None:
    env = existing_env()
    env.project.write_atomic(CanonicalPath.parse(".github/pull_request_template.md"), b"# A\n")
    env.project.write_atomic(CanonicalPath.parse("docs/pull_request_template.md"), b"# B\n")
    options = InitOptions(
        assume_yes=True,
        answers={"repository.pull_requests.template.targets": "docs/pull_request_template.md"},
    )

    init_project(env.services(), options)

    assert "orqlet:begin" in read(env.project, "docs/pull_request_template.md")
    assert read(env.project, ".github/pull_request_template.md") == "# A\n"


def test_a_template_with_broken_markers_is_a_conflict_and_is_left_alone() -> None:
    env = existing_env()
    broken = b"# T\n<!-- orqlet:begin orqlet-workflow x -->\nnever closed\n"
    env.project.write_atomic(CanonicalPath.parse(".github/pull_request_template.md"), broken)

    result = init_project(env.services(), YES)

    assert read(env.project, ".github/pull_request_template.md") == broken.decode()
    assert "ORQ-W080" in codes(result)


def test_a_team_template_from_a_pack_is_distributed_unchanged() -> None:
    body = "## Summary\n\nWhat and why.\n"
    manifest = (
        "schema: orqlet.standards-pack/v1\nid: team\nversion: 2.0.0\nowner: o\n"
        "applies_to: {languages: [python]}\n"
        "assets:\n"
        "  - kind: pr-template\n    id: team/pr\n    path: assets/pr.md\n    owner: o\n"
        f"    version: 2.0.0\n    sha256: {sha256_hex(body.encode())}\n"
    )
    packs = with_files({"team/pack.yaml": manifest, "team/assets/pr.md": body})
    env = existing_env(packs=packs)

    result = init_project(env.services(), YES)

    text = read(env.project, ".github/pull_request_template.md")
    assert "<!-- orqlet:begin team-template team/pr@2.0.0#" in text
    assert "## Summary\n\nWhat and why.\n" in text
    assert result.profile is not None
    assert result.profile.repository.pull_requests.template.status == "provisioned"


def test_packs_that_apply_are_pinned_and_their_path_rules_become_files() -> None:
    env = existing_env(packs=pack_dir())

    init_project(env.services(), InitOptions(assume_yes=True, packs_path="packs"))

    files = tree(env.project)
    assert ".claude/rules/orqlet-sample-001.md" in files
    assert ".cursor/rules/orqlet-web-001.mdc" in files
    lock = read(env.project, ".orqlet/standards.lock.yaml")
    assert "id: sample" in lock
    assert "id: web" in lock
    assert "packs" in read(env.project, ".orqlet/project-profile.yaml")


# --- crash and resume -----------------------------------------------------------------------------
def _uninterrupted() -> tuple[dict[str, bytes], int]:
    """The final tree of a clean run, and how many files that run wrote."""
    env = existing_env()
    init_project(env.services(), YES)
    final = tree(env.project)
    return final, len(final) - len(repo("uv_fastapi").snapshot())


def test_every_kill_point_converges_to_the_uninterrupted_result() -> None:
    expected, writes = _uninterrupted()

    for crash_point in range(writes):
        env = existing_env()
        env.project_view = FaultyFileSystem(env.project, crash_after_writes=crash_point)
        with pytest.raises(SimulatedCrash):
            init_project(env.services(), YES)

        # A rerun after the crash: the same project id (nothing was recorded elsewhere), a fresh
        # change id, and the journal of the crashed change still in the user data directory.
        env.project_view = None
        env.ids = ReplayIds(SequentialIds().new_id())
        result = init_project(env.services(), YES)

        assert result.status == "applied", crash_point
        assert tree(env.project) == expected, f"kill after {crash_point} writes did not converge"


def test_a_crash_before_the_manifest_leaves_no_manifest_and_an_open_journal() -> None:
    env = existing_env()
    _, writes = _uninterrupted()
    env.project_view = FaultyFileSystem(env.project, crash_after_writes=writes - 1)

    with pytest.raises(SimulatedCrash):
        init_project(env.services(), YES)

    assert ".orqlet/generated.lock.yaml" not in tree(env.project)
    journals = [v for k, v in env.user_data.snapshot().items() if k.endswith(".json")]
    assert len(journals) == 1
    assert b'"status": "open"' in journals[0]
    assert b'"done": true' in journals[0]
    assert b'"done": false' in journals[0]


def test_the_rerun_supersedes_the_journal_of_the_crashed_change() -> None:
    env = existing_env()
    env.project_view = FaultyFileSystem(env.project, crash_after_writes=3)
    with pytest.raises(SimulatedCrash):
        init_project(env.services(), YES)
    env.project_view = None
    env.ids = ReplayIds(SequentialIds().new_id())

    init_project(env.services(), YES)

    statuses = sorted(
        json.loads(v)["status"] for k, v in env.user_data.snapshot().items() if k.endswith(".json")
    )
    assert statuses == ["complete", "superseded"]


def test_the_journal_of_a_finished_change_is_complete() -> None:
    env = existing_env()
    result = init_project(env.services(), YES)

    journal = next(
        v for k, v in env.user_data.snapshot().items() if k.endswith(f"{result.change_id}.json")
    )
    assert b'"status": "complete"' in journal
    assert b'"done": false' not in journal


def test_backups_keep_what_an_existing_file_was_before_the_change() -> None:
    env = existing_env()
    env.project.write_atomic(CanonicalPath.parse("AGENTS.md"), b"# Team notes\n")

    result = init_project(env.services(), YES)

    backups = [
        v
        for k, v in env.user_data.snapshot().items()
        if f"backups/{result.change_id}/AGENTS.md" in k
    ]
    assert backups == [b"# Team notes\n"]


def test_a_file_changed_between_preview_and_apply_aborts_without_writing() -> None:
    fs = MemoryFileSystem()
    store = MemoryFileSystem()
    path = CanonicalPath.parse("a.md")
    first = build_plan([Desired(path, OwnerMode.ORQLET, FileClass.GENERATED, b"v1\n")], {}, [])
    apply_plan(
        fs,
        FsChangeJournal(store, "p"),
        FsBackupStore(store, "p"),
        first,
        lock=NoLock(),
        change_id="c0",
        command="init",
        clock=FixedClock(),
    )
    plan = build_plan(
        [Desired(path, OwnerMode.ORQLET, FileClass.GENERATED, b"v2\n")],
        {path: b"v1\n"},
        list(first.recorded_after),
    )
    assert plan.writes[0].kind == "update"
    fs.write_atomic(path, b"changed meanwhile\n")

    with pytest.raises(PlanStale):
        apply_plan(
            fs,
            FsChangeJournal(store, "p"),
            FsBackupStore(store, "p"),
            plan,
            lock=NoLock(),
            change_id="c1",
            command="upgrade",
            clock=FixedClock(),
        )

    assert fs.read_bytes(path) == b"changed meanwhile\n"
    assert not any("c1" in name for name in store.snapshot())


def test_a_symlink_where_a_file_belongs_is_refused_without_a_traceback() -> None:
    env = existing_env()
    env.project.add_symlink(".claude")

    result = init_project(env.services(), YES)

    assert result.status == "refused"
    assert "ORQ-E114" in codes(result)


# --- files that Git ignores ---------------------------------------------------------------------
def test_a_generated_file_that_git_ignores_is_reported_so_it_is_not_silently_unshared() -> None:
    env = Env(
        project=repo("uv_fastapi"),
        vcs=FakeVcs(
            RepoState.HAS_COMMITS,
            branch="main",
            ignored=(".claude/CLAUDE.md", ".claude/rules/orqlet-workflow.md"),
        ),
    )

    result = init_project(env.services(), YES)

    warned = {f.path for f in result.findings if f.code == "ORQ-W097"}
    assert warned == {".claude/CLAUDE.md", ".claude/rules/orqlet-workflow.md"}
    assert "!.claude/CLAUDE.md" in next(f.message for f in result.findings if f.code == "ORQ-W097")


def test_nothing_is_reported_when_nothing_is_ignored_or_there_is_no_repository_yet() -> None:
    clean = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    fresh = Env(project=MemoryFileSystem(), vcs=FakeVcs(RepoState.NOT_A_REPOSITORY))

    assert "ORQ-W097" not in codes(init_project(clean.services(), YES))
    assert "ORQ-W097" not in codes(init_project(fresh.services(), YES))
