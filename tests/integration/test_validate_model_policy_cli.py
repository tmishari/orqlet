"""`orqlet validate model-policy` through the real command line, on real temporary Git repositories
(task dynamic-model-profiles, phase P-7).

Every test cites its `expected_behavior_source`. AC-1 to AC-6 are the acceptance criteria of phase
P-7 in docs/design/dynamic-model-profiles/plan.yaml. R1 to R14 are the readings of the acceptance
criteria that the coder of the phase was given: R1 the states and the not-run text, R2 the base
tree, R8 ORQ-W542, R9 the files of the drift check, R11 what a drift finding prints, R13 the PATH
argument and R14 the order and the data of the result. The business rules themselves (every code,
every boundary) are tested on fakes in tests/unit/application/test_validate_model_policy.py; these
tests pin what only the command line shows: exit statuses, the envelope `orqlet.cli-result/v1`, the
human text, the arguments, the base tree of a real repository, and the wiring.

These tests were written first, by the Tester of phase P-7, before the command existed. The
project is a real Git repository with two branches: `main` holds the sound policy and the profile
(the target branch, `main`), and `feature` is the checked-out branch, one commit later. So the
default base, the merge base with the target branch, is the tip of `main`; `--base HEAD` is the tip
of `feature`. Each test says which base it uses. The clock is patched: `SystemClock` in the wiring
module returns a `FixedClock`, 2026-10-20 12:00 UTC. Credential-shaped text is assembled from parts
at run time and never written as one literal (ORQLET-SEC-003).

Behaviour that the criteria and the readings leave open is deliberately not pinned here:
- the wording of any message beyond the fixed words that the readings give;
- the `path` of the findings of ORQ-E547, of ORQ-E544 and of the warnings;
- the exit status and the text for a root that is no Git repository and for a `--base` that is no
  accepted ref name;
- the names of the parameters of `model_policy_command` (the options are pinned by `--help`).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.model_selection import policy_problems
from orqlet.application.usecases.validate_model_policy import ModelPolicyServices
from orqlet.interface.cli.app import app
from orqlet.interface.cli.exit_codes import ExitCode
from orqlet.interface.cli.wiring import build_model_policy_services
from tests.fakes.clock import FixedClock
from tests.support.git import clean_environ, git, make_repo

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()
Doc = dict[str, Any]

POLICY = ".orqlet/model-policy.yaml"
LOCK = ".orqlet/generated.lock.yaml"
PROFILE = ".orqlet/project-profile.yaml"
OTHER = "docs/other-policy.yaml"
PROFILE_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.project-profile.v1.yaml"
)
RELEASE = str(PackagedWorkflow().release.version)  # the version that the command compares with
NOTHING = "no model policy, nothing was checked"
CLIENTS = ("claude-code", "codex", "cursor")
TESTER = "orqlet-tester"
# Item 4 of the interface: the roles and the skills of the packaged workflow.
ROLES = (
    "orqlet-arch-reviewer",
    "orqlet-inventory",
    "orqlet-security-reviewer",
    "orqlet-tester",
    "orqlet-tracer",
)
SKILLS = (
    "orqlet-design",
    "orqlet-implement",
    "orqlet-onboard",
    "orqlet-plan",
    "orqlet-research",
    "orqlet-review",
)

# A placeholder shaped like a source-host token, assembled at run time (ORQLET-SEC-003).
CREDENTIAL = "".join(("gh", "p_", ("aB3" * 13)[:36]))


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(home).items():
        monkeypatch.setenv(name, value)
    # The date of the whole run: 2026-10-20 12:00 UTC.
    monkeypatch.setattr("orqlet.interface.cli.wiring.SystemClock", lambda: FixedClock())


# --- policies built in code -----------------------------------------------------------------------


def route(client: str, name: str, *, retires_on: str | None = None) -> Doc:
    return {
        "client": client,
        "kind": "id",
        "name": name,
        "resolves_to": None,
        "also_known_as": [],
        "access": "unknown",
        "retires_on": retires_on,
    }


def model(
    model_id: str, *, retires_on: str | None = None, approved_by: str | None = "example-approver"
) -> Doc:
    """An approved catalog entry with an id route for each client, named `<id>-<client>`.

    Only the Claude Code route retires on `retires_on`, so one date gives one warning."""
    return {
        "id": model_id,
        "family": "example-family",
        "approval": {"state": "approved", "approved_by": approved_by, "approval_ref": "pr:42"},
        "documented": {"evidence": "docs/example/evidence/entry.md", "date": "2026-10-30"},
        "callable": "not-run",
        "evaluated": {"state": "none"},
        "routes": [
            route(c, f"{model_id}-{c}", retires_on=retires_on if c == "claude-code" else None)
            for c in CLIENTS
        ],
    }


def exclusion(rule_id: str, *, aliases: list[str], id_patterns: list[str] | None = None) -> Doc:
    return {
        "id": rule_id,
        "reason": "Example reason.",
        "source": "Example notice.",
        "aliases": aliases,
        "id_patterns": id_patterns or [],
        "family_tags": [],
    }


def role_assignment(role: str, model_id: str) -> Doc:
    return {
        "target": {"kind": "role", "name": role},
        "task": None,
        "client": None,
        "profile": None,
        "model": model_id,
        "mode": "manual",
        "effort": None,
    }


RULE_A = exclusion("rule-a", aliases=["blocked-alias"], id_patterns=["blocked-model-*"])
RULE_B = exclusion("rule-b", aliases=["other-blocked-alias"])


def policy(**changes: Any) -> Doc:
    """A sound policy that pins nothing: two approved models and two exclusions."""
    document: Doc = {
        "schema": "orqlet.model-policy/v2",
        "policy_version": 1,
        "reviewed_for_release": RELEASE,
        "models": [model("example-a"), model("example-b")],
        "excluded": [RULE_A, RULE_B],
        "profiles": [],
        "assignments": [],
    }
    return {**document, **changes}


def text_of(document: Doc) -> str:
    """A policy as text: JSON is YAML, and the strict loader reads it."""
    return json.dumps(document, indent=2) + "\n"


def lock_text(*rows: Doc) -> str:
    document = {
        "schema": "orqlet.generated-lock/v1",
        "generator": {"orqlet": RELEASE},
        "files": rows,
    }
    return json.dumps(document, indent=2) + "\n"


SEEDED_POLICY_ROW: Doc = {"path": POLICY, "owner": "seeded", "seeded_sha256": "0" * 64}


def generated_row(path: str) -> Doc:
    return {"path": path, "owner": "orqlet", "class": "protected", "rendered_sha256": "2" * 64}


def agent_file(model_value: str) -> str:
    """An agent definition in the form that Claude Code and Cursor read: front matter and a body."""
    front_matter = f"name: example\ndescription: An example.\nmodel: {model_value}\n"
    return f"---\n{front_matter}---\n\nDo the work.\n"


# --- real repositories ----------------------------------------------------------------------------


def write(root: Path, name: str, data: str | bytes) -> Path:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data.encode() if isinstance(data, str) else data)
    return target


def commit(root: Path, files: dict[str, str], message: str) -> str:
    """Write and commit the files; the full id of the new commit."""
    for name, content in files.items():
        write(root, name, content)
        git(root, "add", "--", name)
    git(root, "commit", "--quiet", "-m", message)
    return git(root, "rev-parse", "HEAD").strip()


@dataclass(frozen=True)
class Repo:
    root: Path
    base: str  # the full id of the tip of `main`: the commit that holds the sound policy


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    """`main` holds the sound policy and the profile; `feature` is checked out, one commit later."""
    root = make_repo(tmp_path / "project", branch="main")
    base = commit(
        root,
        {POLICY: text_of(policy()), PROFILE: PROFILE_FIXTURE.read_text(encoding="utf-8")},
        "Add the model policy and the profile",
    )
    git(root, "checkout", "--quiet", "-b", "feature")
    commit(root, {"notes.txt": "A note.\n"}, "Add a note")
    return Repo(root, base)


@pytest.fixture
def bare_repo(tmp_path: Path) -> Path:
    """One commit with no model policy and no profile."""
    root = make_repo(tmp_path / "bare", branch="main")
    commit(root, {"README.txt": "A project.\n"}, "Add a readme")
    return root


# --- running the command --------------------------------------------------------------------------


def run(root: Path, *args: str) -> tuple[int, dict[str, Any]]:
    """Run the command with `--json`; the exit status and the envelope."""
    result = RUNNER.invoke(app, ["validate", "model-policy", *args, "--root", str(root), "--json"])
    assert result.exit_code != 2, result.output  # 2 is a usage error: the command is not there
    return result.exit_code, json.loads(result.stdout)


def codes(document: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in document["findings"]]


def verdict(document: dict[str, Any]) -> str:
    return str(document["data"]["verdict"])


def snapshot(root: Path) -> dict[str, bytes]:
    """Every file of the working tree, except the repository's own data."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def marker(label: str) -> str:
    """A unique, valid model string for one field: the same value on every run."""
    return "zq7mk-" + hashlib.sha256(label.encode()).hexdigest()[:12]


def registered_names(group: typer.Typer, prefix: str = "") -> set[str]:
    """The commands of an application, named as `IMPLEMENTED_COMMANDS` names them."""
    names = set()
    for command in group.registered_commands:
        callback = command.callback
        name = command.name or (callback.__name__ if callback is not None else "")
        names.add(f"{prefix}{name.removesuffix('_command').replace('_', '-')}".strip())
    for sub in group.registered_groups:
        if sub.typer_instance is not None:
            names |= registered_names(sub.typer_instance, f"{prefix}{sub.name} ")
    return names


# --- AC-1: PASS exits 0 and prints the envelope ---------------------------------------------------


def test_a_sound_policy_passes_with_exit_0_and_the_usual_envelope(repo: Repo) -> None:
    """AC-1. expected_behavior_source: AC-1 ("Exit 0 on PASS ... `--json` prints the common
    envelope"); `orqlet.cli-result/v1`. Base: the full id of the tip of `main`."""
    code, document = run(repo.root, "--base", repo.base)

    assert code == int(ExitCode.OK), document
    assert document["schema"] == "orqlet.cli-result/v1"
    assert document["command"] == "validate model-policy"
    assert document["ok"] is True
    assert isinstance(document["orqlet_version"], str)
    assert verdict(document) == "PASS"
    assert document["not_run"] == []
    assert [f for f in document["findings"] if f["severity"] != "info"] == []


@pytest.mark.parametrize(
    "base",
    ["HEAD", "main", "FULL_ID"],
    ids=["the-word-head", "a-branch-name", "a-full-commit-id"],
)
def test_the_base_can_be_head_a_branch_name_or_a_full_commit_id(repo: Repo, base: str) -> None:
    """AC-1/AC-2/R2. expected_behavior_source: R2 ("the optional `--base`: a branch name, a full
    commit id or `HEAD`"). The working tree equals the policy of each of these trees, so each
    base gives PASS."""
    code, document = run(repo.root, "--base", repo.base if base == "FULL_ID" else base)

    assert (code, verdict(document)) == (0, "PASS"), document


# --- AC-1: FAIL and NOT_RUN exit 5 ----------------------------------------------------------------


def test_a_policy_with_an_error_fails_with_exit_5_and_is_not_ok(repo: Repo) -> None:
    """AC-1. expected_behavior_source: AC-1 ("exit 5 on FAIL"). Base: the tip of `main`."""
    write(repo.root, POLICY, text_of(policy(models=[model("example-a", approved_by=None)])))

    code, document = run(repo.root, "--base", repo.base)

    assert code == int(ExitCode.CHECK_FAILED)
    assert document["ok"] is False
    assert verdict(document) == "FAIL"
    assert codes(document) == ["ORQ-E546"]


def _break_with_a_duplicate_key(root: Path) -> None:
    write(root, POLICY, "a: 1\na: 2\n")


def _break_the_schema(root: Path) -> None:
    write(root, POLICY, text_of({"schema": "orqlet.model-policy/v2"}))


def _break_with_a_credential(root: Path) -> None:
    write(root, POLICY, text_of(policy()) + f"# {CREDENTIAL}\n")


def _break_with_an_excluded_route(root: Path) -> None:
    write(root, POLICY, text_of(policy(models=[model("example-a"), model("blocked-model-1")])))


def _break_with_an_unknown_role(root: Path) -> None:
    write(root, POLICY, text_of(policy(assignments=[role_assignment("no-such-role", "example-a")])))


def _break_with_an_unapproved_model(root: Path) -> None:
    write(root, POLICY, text_of(policy(models=[model("example-a", approved_by=None)])))


def _break_with_an_excluded_value_in_a_file(root: Path) -> None:
    write(root, ".claude/agents/team.md", agent_file("blocked-alias"))


@pytest.mark.parametrize(
    ("code", "edit"),
    [
        pytest.param("ORQ-E540", _break_with_a_duplicate_key, id="loader-ORQ-E540"),
        pytest.param("ORQ-E541", _break_the_schema, id="loader-ORQ-E541"),
        pytest.param("ORQ-E542", _break_with_a_credential, id="loader-ORQ-E542"),
        pytest.param("ORQ-E543", _break_with_an_excluded_route, id="excluded-model"),
        pytest.param("ORQ-E545", _break_with_an_unknown_role, id="unknown-role"),
        pytest.param("ORQ-E546", _break_with_an_unapproved_model, id="approval"),
        pytest.param("ORQ-E548", _break_with_an_excluded_value_in_a_file, id="excluded-file-value"),
    ],
)
def test_every_error_of_the_command_gives_fail_and_exit_5(
    repo: Repo, code: str, edit: Callable[[Path], None]
) -> None:
    """AC-1/AC-2/AC-4. expected_behavior_source: AC-1 ("exit 5 on FAIL"); AC-2 (the codes E540 to
    E546); AC-4 (E548). Base: the tip of `main`, whose policy the working tree still contains."""
    edit(repo.root)

    exit_code, document = run(repo.root, "--base", repo.base)

    assert exit_code == int(ExitCode.CHECK_FAILED)
    assert verdict(document) == "FAIL"
    assert document["ok"] is False
    assert code in codes(document)


def test_a_credential_in_the_policy_is_never_printed(repo: Repo) -> None:
    """AC-2/AC-5. expected_behavior_source: AC-2 (ORQ-E542 comes from the loader); ORQLET-SEC-003
    (a credential is never put in a message). Base: the tip of `main`."""
    _break_with_a_credential(repo.root)

    as_json = RUNNER.invoke(
        app, ["validate", "model-policy", "--base", repo.base, "--root", str(repo.root), "--json"]
    )
    as_text = RUNNER.invoke(
        app, ["validate", "model-policy", "--base", repo.base, "--root", str(repo.root)]
    )

    for result in (as_json, as_text):
        assert result.exit_code == 5
        assert not leaks(result.stdout, CREDENTIAL)
        assert not leaks(result.stderr, CREDENTIAL)


def test_a_policy_that_was_never_present_is_not_run_and_exits_5(bare_repo: Path) -> None:
    """AC-1/R1. expected_behavior_source: AC-1 ("A never-present policy is NOT_RUN with the reason
    'no model policy, nothing was checked'"; "exit 5 on FAIL and on NOT_RUN"). Base: `HEAD`."""
    code, document = run(bare_repo, "--base", "HEAD")

    assert code == int(ExitCode.CHECK_FAILED)
    assert document["ok"] is False
    assert verdict(document) == "NOT_RUN"
    assert NOTHING in document["not_run"]
    assert not [f for f in document["findings"] if f["severity"] == "error"]


def test_the_human_text_of_a_policy_that_was_never_present_says_why(bare_repo: Path) -> None:
    """AC-1/R1. expected_behavior_source: AC-1 (the reason text); the human summary of the other
    validators (the verdict first). Base: `HEAD`."""
    result = RUNNER.invoke(
        app, ["validate", "model-policy", "--base", "HEAD", "--root", str(bare_repo)]
    )

    assert result.exit_code == 5
    assert result.stdout.splitlines()[0].startswith("NOT_RUN")
    assert NOTHING in result.stdout


def test_a_policy_deleted_after_the_base_is_orq_e547(repo: Repo) -> None:
    """AC-1/R1. expected_behavior_source: AC-1 ("A deleted policy is FAIL with ORQ-E547. Deleted
    means missing from the working tree but present at the base tree"). Base: the tip of `main`,
    which holds the policy."""
    (repo.root / POLICY).unlink()

    code, document = run(repo.root, "--base", repo.base)

    assert code == 5
    assert verdict(document) == "FAIL"
    assert codes(document) == ["ORQ-E547"]
    assert document["ok"] is False


def test_a_policy_that_the_lock_records_as_seeded_and_is_missing_is_orq_e547(
    bare_repo: Path,
) -> None:
    """AC-1/R1. expected_behavior_source: AC-1 ("... or recorded as seeded in the lock"). Base:
    `HEAD`, which holds no policy, so the lock is the only evidence."""
    commit(bare_repo, {LOCK: lock_text(SEEDED_POLICY_ROW)}, "Add the lock")

    code, document = run(bare_repo, "--base", "HEAD")

    assert code == 5
    assert verdict(document) == "FAIL"
    assert codes(document) == ["ORQ-E547"]


def test_a_policy_that_the_lock_records_as_owned_by_the_team_is_never_present(
    bare_repo: Path,
) -> None:
    """AC-1/R1. expected_behavior_source: R1 (deleted needs a lock row with the owner `seeded`).
    Base: `HEAD`."""
    row = {"path": POLICY, "owner": "user", "rendered_sha256": "3" * 64}
    commit(bare_repo, {LOCK: lock_text(row)}, "Add the lock")

    code, document = run(bare_repo, "--base", "HEAD")

    assert (code, verdict(document)) == (5, "NOT_RUN")
    assert "ORQ-E547" not in codes(document)


# --- AC-2: the base tree of a real repository -----------------------------------------------------


@pytest.fixture
def repo_that_dropped_an_exclusion(repo: Repo) -> Repo:
    """`feature` has committed a policy without `rule-b`, which the tip of `main` still holds."""
    commit(repo.root, {POLICY: text_of(policy(excluded=[RULE_A]))}, "Drop an exclusion")
    return repo


@pytest.mark.parametrize(
    "base",
    [None, "main", "FULL_ID"],
    ids=["the-merge-base-with-the-target-branch", "a-branch-name", "a-full-commit-id"],
)
def test_an_exclusion_that_the_base_holds_and_the_file_lacks_is_orq_e544(
    repo_that_dropped_an_exclusion: Repo, base: str | None
) -> None:
    """AC-2/R2. expected_behavior_source: AC-2 (E544: "an excluded entry present in the base tree
    but missing from the file. The base is the optional `--base`, otherwise the merge base `validate
    review` uses"). The merge base of `feature` and `main` is the tip of `main`, which holds
    `rule-b`; the working tree equals the tip of `feature`, which has dropped it."""
    repo = repo_that_dropped_an_exclusion
    args = () if base is None else ("--base", repo.base if base == "FULL_ID" else base)

    code, document = run(repo.root, *args)

    assert (code, verdict(document)) == (5, "FAIL"), document
    assert codes(document) == ["ORQ-E544"]


def test_the_word_head_as_the_base_is_the_tip_of_the_checked_out_branch(
    repo_that_dropped_an_exclusion: Repo,
) -> None:
    """AC-2/R2. expected_behavior_source: R2 (`HEAD` is an accepted base); the tip of `feature`
    has already dropped `rule-b`, so nothing is missing from the working tree. Base: `HEAD`."""
    code, document = run(repo_that_dropped_an_exclusion.root, "--base", "HEAD")

    assert (code, verdict(document)) == (0, "PASS"), document


def test_an_exclusion_missing_from_the_uncommitted_file_is_orq_e544(repo: Repo) -> None:
    """AC-2/R2. expected_behavior_source: AC-2 (E544 compares the working-tree file with the base
    tree); the removal is not committed. Base: none (the merge base with `main`)."""
    write(repo.root, POLICY, text_of(policy(excluded=[RULE_A])))

    code, document = run(repo.root)

    assert (code, verdict(document)) == (5, "FAIL")
    assert codes(document) == ["ORQ-E544"]


def test_an_added_exclusion_is_not_a_removal(repo: Repo) -> None:
    """AC-2. expected_behavior_source: AC-2 (E544 is for an entry present in the base and missing
    from the file); an extra entry is not. Base: none (the merge base with `main`)."""
    extra = exclusion("rule-c", aliases=["third-blocked-alias"])
    write(repo.root, POLICY, text_of(policy(excluded=[RULE_A, RULE_B, extra])))

    code, document = run(repo.root)

    assert (code, verdict(document)) == (0, "PASS"), document


def test_without_a_base_and_without_a_known_target_branch_nothing_passes(bare_repo: Path) -> None:
    """AC-1/AC-2/R2. expected_behavior_source: R2 (when no base tree could be located the reasons
    are listed and the verdict cannot be PASS); `validate review` says "name the base with
    --base". There is no profile, so the target branch is unknown. Base: none."""
    write(bare_repo, POLICY, text_of(policy()))

    code, document = run(bare_repo)

    assert (code, verdict(document)) == (5, "NOT_RUN")
    assert document["not_run"]
    assert document["ok"] is False


def test_a_base_that_names_nothing_is_not_run_and_never_a_traceback(repo: Repo) -> None:
    """AC-1/AC-2/R2. expected_behavior_source: R2 (the reasons that no base tree was located are
    not-run reasons). Base: a branch name that does not exist."""
    code, document = run(repo.root, "--base", "no-such-branch")

    assert (code, verdict(document)) == (5, "NOT_RUN")
    assert document["not_run"]


def test_an_error_is_a_failure_even_when_the_base_cannot_be_found(repo: Repo) -> None:
    """AC-1/R2. expected_behavior_source: R2 ("an error still gives FAIL"); the verdict rule of the
    other validators (an error beats NOT_RUN). Base: a branch name that does not exist."""
    _break_with_an_excluded_route(repo.root)

    code, document = run(repo.root, "--base", "no-such-branch")

    assert (code, verdict(document)) == (5, "FAIL")
    assert "ORQ-E543" in codes(document)
    assert document["not_run"]


# --- AC-3: the warnings do not fail the command ---------------------------------------------------


def quality_profile() -> Doc:
    """A manual profile with a candidate for Claude Code only."""
    return {
        "id": "quality",
        "capability": "Example capability.",
        "mode": "manual",
        "candidates": [{"client": "claude-code", "models": ["example-a"]}],
        "fallbacks": [],
        "escalation": None,
    }


def _warn_of_a_missing_candidate(root: Path) -> None:
    write(root, POLICY, text_of(policy(profiles=[quality_profile()])))


def _warn_of_an_old_review(root: Path) -> None:
    write(root, POLICY, text_of(policy(reviewed_for_release="0.0.1")))


def _warn_of_a_retirement(root: Path) -> None:
    write(root, POLICY, text_of(policy(models=[model("example-a", retires_on="2026-10-30")])))


def _warn_of_a_generated_file_that_differs(root: Path) -> None:
    path = ".cursor/agents/orqlet-tester.md"
    write(root, path, agent_file("example-other-model"))
    write(root, LOCK, lock_text(generated_row(path)))


def _warn_of_a_file_that_cannot_be_read(root: Path) -> None:
    write(root, ".claude/agents/broken.md", "---\nname: example\nmodel: [unclosed\n---\n\nBody.\n")


@pytest.mark.parametrize(
    ("code", "edit"),
    [
        pytest.param("ORQ-W540", _warn_of_a_missing_candidate, id="missing-candidate"),
        pytest.param("ORQ-W541", _warn_of_an_old_review, id="old-review"),
        pytest.param("ORQ-W542", _warn_of_a_retirement, id="retirement"),
        pytest.param("ORQ-W543", _warn_of_a_generated_file_that_differs, id="generated-drift"),
        pytest.param("ORQ-W544", _warn_of_a_file_that_cannot_be_read, id="unreadable-file"),
    ],
)
def test_a_warning_alone_keeps_the_verdict_pass_and_the_exit_0(
    repo: Repo, code: str, edit: Callable[[Path], None]
) -> None:
    """AC-1/AC-3/AC-4. expected_behavior_source: AC-1 ("Exit 0 on PASS"); AC-3 (W540, W541, W542
    are warnings); AC-4 (W543, W544 are warnings). Base: the tip of `main`."""
    edit(repo.root)

    exit_code, document = run(repo.root, "--base", repo.base)

    assert exit_code == int(ExitCode.OK), document
    assert verdict(document) == "PASS"
    assert document["ok"] is True
    found = [f for f in document["findings"] if f["code"] == code]
    assert found, codes(document)
    assert {f["severity"] for f in found} == {"warning"}
    assert not [f for f in document["findings"] if f["severity"] == "error"]


def test_a_retirement_date_is_read_through_the_clock_of_the_wiring(repo: Repo) -> None:
    """AC-3/AC-6/R8. expected_behavior_source: AC-6 ("the Clock port"); the wiring uses
    `SystemClock`, which these tests replace with a `FixedClock` at 2026-10-20 12:00 UTC. A route
    retiring 10 days later warns. Base: the tip of `main`."""
    write(repo.root, POLICY, text_of(policy(models=[model("example-a", retires_on="2026-10-30")])))

    _, document = run(repo.root, "--base", repo.base)

    assert codes(document) == ["ORQ-W542"]


def test_a_retirement_date_more_than_30_days_after_the_fixed_date_is_quiet(repo: Repo) -> None:
    """AC-3/R8. expected_behavior_source: R8 (a date more than 30 days after today is quiet);
    36 days after 2026-10-20 is 2026-11-25. Base: the tip of `main`."""
    write(repo.root, POLICY, text_of(policy(models=[model("example-a", retires_on="2026-11-25")])))

    code, document = run(repo.root, "--base", repo.base)

    assert (code, verdict(document)) == (0, "PASS")
    assert codes(document) == []


def test_the_findings_come_in_the_order_of_the_readings(repo: Repo) -> None:
    """R14. expected_behavior_source: R14 ("E543, E545, E546, E544, then W540, W541, W542, then the
    drift findings"). Base: the tip of `main`; the policy has an excluded route (E543), an unknown
    role (E545), an old review (W541), and a file with an excluded value (E548)."""
    write(
        repo.root,
        POLICY,
        text_of(
            policy(
                models=[model("example-a"), model("blocked-model-1")],
                assignments=[role_assignment("no-such-role", "example-a")],
                reviewed_for_release="0.0.1",
            )
        ),
    )
    _break_with_an_excluded_value_in_a_file(repo.root)

    _, document = run(repo.root, "--base", repo.base)

    assert codes(document) == ["ORQ-E543", "ORQ-E545", "ORQ-W541", "ORQ-E548"]


# --- AC-5: nothing of a model string is shown -----------------------------------------------------


def _model_named(route_name: str) -> Doc:
    entry = model("example-c")
    entry["routes"] = [route("claude-code", route_name)]
    return entry


def _marked_exclusion(root: Path) -> list[str]:
    """A rule whose alias is the name of a route and the `model` value of a team file, and whose id
    is a marker too: the findings ORQ-E543 and ORQ-E548."""
    alias, rule = marker("alias"), marker("rule")
    excluded = [RULE_A, RULE_B, exclusion(rule, aliases=[alias])]
    models = [model("example-a"), _model_named(alias)]
    write(root, POLICY, text_of(policy(models=models, excluded=excluded)))
    write(root, ".claude/agents/team.md", agent_file(alias))
    return [alias, rule]


def _marked_drift(root: Path) -> list[str]:
    """A value in a generated file that no catalog entry has: the finding ORQ-W543."""
    value = marker("value")
    path = ".cursor/agents/orqlet-tester.md"
    write(root, path, agent_file(value))
    write(root, LOCK, lock_text(generated_row(path)))
    return [value]


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        pytest.param(_marked_exclusion, ["ORQ-E543", "ORQ-E548"], id="excluded-values"),
        pytest.param(_marked_drift, ["ORQ-W543"], id="a-value-that-matches-nothing"),
    ],
)
def test_a_model_string_never_appears_in_the_json_or_the_human_text(
    repo: Repo, scenario: Callable[[Path], list[str]], expected: list[str]
) -> None:
    """AC-5/R11. expected_behavior_source: AC-5 ("A finding prints the catalog id or `unmatched`
    with the length, never the string. A unique marker in each model field never appears in text or
    data"); R11. Base: the tip of `main`."""
    markers = scenario(repo.root)

    as_json = RUNNER.invoke(
        app, ["validate", "model-policy", "--base", repo.base, "--root", str(repo.root), "--json"]
    )
    as_text = RUNNER.invoke(
        app, ["validate", "model-policy", "--base", repo.base, "--root", str(repo.root)]
    )

    assert codes(json.loads(as_json.stdout)) == expected
    for result in (as_json, as_text):
        for value in markers:
            assert not leaks(result.stdout, value), value
            assert not leaks(result.stderr, value), value


# --- the arguments --------------------------------------------------------------------------------


def test_a_path_argument_names_the_policy_to_check(repo: Repo) -> None:
    """AC-1/R13. expected_behavior_source: R13 (`PATH` names the policy; the default is
    `.orqlet/model-policy.yaml`). The default file is broken and the other one is sound; the other
    one is named. Base: the tip of `main`."""
    write(repo.root, POLICY, "a: 1\na: 2\n")
    write(repo.root, OTHER, text_of(policy()))

    default_code, default_document = run(repo.root, "--base", repo.base)
    other_code, other_document = run(repo.root, OTHER, "--base", repo.base)

    assert (default_code, verdict(default_document)) == (5, "FAIL")
    assert (other_code, verdict(other_document)) == (0, "PASS")


def test_the_findings_of_another_path_name_that_path(repo: Repo) -> None:
    """R13. expected_behavior_source: R13 (the findings of the loader name the path that was read).
    Base: the tip of `main`."""
    write(repo.root, OTHER, "a: 1\na: 2\n")

    _, document = run(repo.root, OTHER, "--base", repo.base)

    assert codes(document) == ["ORQ-E540"]
    assert document["findings"][0]["path"] == OTHER


@pytest.mark.parametrize(
    "path",
    ["../outside.yaml", "/nonexistent-orqlet-dir/policy.yaml", "docs/../../outside.yaml"],
    ids=["parent-folder", "absolute", "escapes-the-root"],
)
def test_a_path_outside_the_project_is_orq_e320_and_is_never_read(repo: Repo, path: str) -> None:
    """R13. expected_behavior_source: R13 (a PATH that is not a safe repository path is ORQ-E320;
    "an unusable path is a finding, not a traceback"). Base: the tip of `main`."""
    code, document = run(repo.root, path, "--base", repo.base)

    assert (code, verdict(document)) == (5, "FAIL")
    assert "ORQ-E320" in codes(document)


def test_a_custom_path_that_is_missing_is_not_run(repo: Repo) -> None:
    """AC-1/R13. expected_behavior_source: R1 and R13 (a policy named by PATH that does not exist
    was never present). Base: the tip of `main`, which holds the default policy only."""
    code, document = run(repo.root, OTHER, "--base", repo.base)

    assert (code, verdict(document)) == (5, "NOT_RUN")
    assert NOTHING in document["not_run"]


def test_the_command_is_deterministic(repo: Repo) -> None:
    """R14. expected_behavior_source: R14 (the order of the findings and the content of `data` are
    fixed). Two runs on the same tree print the same envelope. Base: the tip of `main`."""
    _break_with_an_excluded_route(repo.root)

    first = run(repo.root, "--base", repo.base)
    second = run(repo.root, "--base", repo.base)

    assert first == second


# --- the command only reads -----------------------------------------------------------------------


def test_the_command_writes_nothing_to_the_project_or_the_repository(repo: Repo) -> None:
    """AC-1/AC-6. expected_behavior_source: the command is read-only (AC-1; AC-6 "never writes").
    Every file of the working tree and the state of the repository are the same after a run that
    reports findings. Base: the tip of `main`."""
    _break_with_an_excluded_route(repo.root)
    _warn_of_a_generated_file_that_differs(repo.root)
    status = git(repo.root, "status", "--porcelain")
    refs = git(repo.root, "for-each-ref")
    before = snapshot(repo.root)

    run(repo.root, "--base", repo.base)

    assert snapshot(repo.root) == before
    assert git(repo.root, "status", "--porcelain") == status
    assert git(repo.root, "for-each-ref") == refs


# --- the human text -------------------------------------------------------------------------------


def _change_nothing(root: Path) -> None:
    """The sound policy of the fixture is left as it is."""


@pytest.mark.parametrize(
    ("verdict_word", "edit", "exit_code"),
    [
        pytest.param("PASS", _change_nothing, 0, id="pass"),
        pytest.param("FAIL", _break_with_an_excluded_route, 5, id="fail"),
    ],
)
def test_the_human_text_opens_with_the_verdict(
    repo: Repo, verdict_word: str, edit: Callable[[Path], None], exit_code: int
) -> None:
    """AC-1. expected_behavior_source: the human summary of the other validators (`output_of`: the
    verdict first). Base: the tip of `main`."""
    edit(repo.root)

    result = RUNNER.invoke(
        app, ["validate", "model-policy", "--base", repo.base, "--root", str(repo.root)]
    )

    assert result.exit_code == exit_code
    assert result.stdout.splitlines()[0].startswith(verdict_word)


# --- AC-6: the command is part of the application -------------------------------------------------


def test_the_command_is_listed_as_implemented() -> None:
    """AC-6. expected_behavior_source: AC-6 ("`IMPLEMENTED_COMMANDS` lists `validate
    model-policy`")."""
    assert "validate model-policy" in IMPLEMENTED_COMMANDS


def test_the_commands_that_the_application_registers_are_the_implemented_commands() -> None:
    """AC-6. expected_behavior_source: AC-6 and the equality test of tests/integration/
    test_validate_cli.py: a command registered as `model-policy` on the `validate` group is
    `validate model-policy`."""
    assert registered_names(app) == set(IMPLEMENTED_COMMANDS)
    assert "validate model-policy" in registered_names(app)


def test_the_validate_group_lists_the_command_in_its_help() -> None:
    """AC-6. expected_behavior_source: AC-6 (the command is part of the `validate` group)."""
    result = RUNNER.invoke(app, ["validate", "--help"])

    assert result.exit_code == 0
    assert "model-policy" in result.stdout


def test_the_help_of_the_command_names_the_three_options() -> None:
    """AC-1/R2. expected_behavior_source: the interface of phase P-7 (`orqlet validate
    model-policy [PATH] [--base BASE] [--root DIR] [--json]`). The name of the positional argument
    is not pinned: the default file and the named file are pinned by behaviour above."""
    result = RUNNER.invoke(app, ["validate", "model-policy", "--help"])

    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)  # the help is coloured
    assert result.exit_code == 0
    for option in ("--base", "--root", "--json"):
        assert option in plain


def test_the_command_is_a_function_of_the_validate_module() -> None:
    """AC-6/interface item 2. expected_behavior_source: interface item 2 (`model_policy_command` in
    `orqlet.interface.cli.commands.validate`)."""
    from orqlet.interface.cli.commands import validate

    assert callable(validate.model_policy_command)


def test_the_services_of_the_command_are_built_from_the_real_adapters(tmp_path: Path) -> None:
    """AC-6/interface item 2. expected_behavior_source: interface item 2 (`build_model_policy_
    services(root)` uses `LocalFileSystem`, `GitVcs`, `StrictYamlLoader`, `PackagedWorkflow` and
    `SystemClock`; AC-6: "built from a services object adding the Clock port"). `SystemClock` is
    replaced by these tests, so the clock is the `FixedClock`."""
    root = tmp_path / "project"
    root.mkdir()

    services = build_model_policy_services(root)

    assert isinstance(services, ModelPolicyServices)
    assert isinstance(services.project, LocalFileSystem)
    assert isinstance(services.vcs, GitVcs)
    assert isinstance(services.loader, StrictYamlLoader)
    assert isinstance(services.workflow, PackagedWorkflow)
    assert isinstance(services.clock, FixedClock)


# --- premises -------------------------------------------------------------------------------------


def test_the_premise_the_documents_of_these_tests_are_valid_contracts() -> None:
    """Not a behaviour of the command: what the tests write is read by the contracts of the
    project, so a finding of the command is never an accident of a bad fixture.

    expected_behavior_source: the contracts `ModelPolicy`, `GeneratedLock` and `ProjectProfile`,
    and `policy_problems` (the exclusion and reference checks of R5).
    """
    loader = StrictYamlLoader()
    alias = marker("alias")
    clean = [
        policy(),
        policy(models=[model("example-a", approved_by=None)]),  # E546, not E541
        policy(models=[model("example-a", retires_on="2026-10-30")]),
        policy(reviewed_for_release="0.0.1"),
        policy(profiles=[quality_profile()]),
    ]
    with_problems = [
        policy(models=[model("example-a"), model("blocked-model-1")]),
        policy(assignments=[role_assignment("no-such-role", "example-a")]),
        policy(
            models=[model("example-a"), _model_named(alias)],
            excluded=[RULE_A, RULE_B, exclusion(marker("rule"), aliases=[alias])],
        ),
    ]
    for document in (*clean, *with_problems):
        load_contract(loader, ModelPolicy, text_of(document).encode(), source=POLICY)
    for document in clean:
        loaded = load_contract(loader, ModelPolicy, text_of(document).encode(), source=POLICY)
        assert policy_problems(loaded, ROLES, SKILLS) == ()
    for document in with_problems:
        loaded = load_contract(loader, ModelPolicy, text_of(document).encode(), source=POLICY)
        assert policy_problems(loaded, ROLES, SKILLS)
    rows = lock_text(SEEDED_POLICY_ROW, generated_row(".cursor/agents/orqlet-tester.md"))
    load_contract(loader, GeneratedLock, rows.encode(), source=LOCK)
    profile = load_contract(loader, ProjectProfile, PROFILE_FIXTURE.read_bytes(), source=PROFILE)
    assert profile.repository.target_branch.value == "main"  # the default base is `main`
    assert tuple(profile.clients.enabled) == CLIENTS
