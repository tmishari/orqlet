"""`orqlet conventions check` through the real command line, on real Git repositories (task
team-conventions-resources, phase P-7).

Every test cites its `expected_behavior_source`. ADR-003 is the file `adr-003-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, S-n are the considerations of considerations.md, and AC-1 to AC-6 are the acceptance
criteria of phase P-7 in docs/design/team-conventions-resources/plan.yaml. "The interface decision"
is the reading of the plan author that the Tester of phase P-7 was given, because the ADR does not
spell it out: `orqlet conventions check [--branch NAME] [--base REF] [--head REF] [--root DIR]
[--json]` (group `conventions`); it builds `ValidateServices` with `build_validate_services(root)`
and prints through `output_of(result, 'conventions')`: the first human line starts with the verdict;
PASS exits 0; FAIL and NOT_RUN exit 5; `IMPLEMENTED_COMMANDS` gains `conventions check`; the module
of the command has one public name, `conventions_group`. The profile at the base of each repository
below is the valid fixture profile with `branch_patterns` and `commit_convention` answered, and it
is committed on the base branch before the pull-request branch starts.

These tests were written first, by the Tester of phase P-7, before the command existed. Every
repository is built in `tmp_path`, with no network (`file://` clones only).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message, and the keys of `data` beyond `verdict`;
- the exit code for a root that does not exist;
- whether a bad branch is still reported when the base is missing or there is no merge base (those
  tests use a good branch);
- the form `--base REF` with a space (only the equals form that the README uses is pinned);
- `::error::` is printable ASCII, so `printable` keeps it: what is pinned is that no line starts
  with contributor text, and that ESC, U+202E and characters beyond ASCII are escaped.
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import typer
import yaml
from typer.testing import CliRunner

from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.interface.cli.app import app
from tests.support.artifacts import dump
from tests.support.git import clean_environ, commit_file, git, make_repo
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()
PROFILE = ".orqlet/project-profile.yaml"
VALID_PROFILE = FIXTURES / "contracts" / "valid" / "orqlet.project-profile.v1.yaml"
MARKERS = "\u00e9\u65e5\U0001f680"  # characters beyond ASCII that must never be shown as they are


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(home).items():
        monkeypatch.setenv(name, value)


# --- repositories ---------------------------------------------------------------------------------


def profile_text(
    patterns: str | None = "feature/*, fix/*", convention: str | None = "conventional-commits"
) -> str:
    """The valid fixture profile; the target branch is `main` of `origin`."""
    document: dict[str, Any] = yaml.safe_load(VALID_PROFILE.read_text(encoding="utf-8"))
    repository = document["repository"]
    for key, value in (("branch_patterns", patterns), ("commit_convention", convention)):
        repository[key] = (
            {"value": None, "question": f"What is the {key}?"}
            if value is None
            else {"value": value, "answered_by": "maintainer"}
        )
    return dump(document)


@dataclass(frozen=True)
class Project:
    origin: Path
    work: Path  # a clone of origin, on the branch `feature/login`
    base_id: str  # the tip of `origin/main`


def build_project(tmp_path: Path, **answers: str | None) -> Project:
    """`origin/main` holds the profile; `work` is a clone with a branch to commit on."""
    origin = make_repo(tmp_path / "origin")
    commit_file(origin, PROFILE, profile_text(**answers), "chore: add the profile")
    base_id = commit_file(origin, "README.txt", "hello\n", "chore: seed")
    environ = clean_environ(tmp_path)
    git(tmp_path, "clone", "--quiet", origin.as_uri(), "work", environ=environ)
    work = tmp_path / "work"
    git(work, "checkout", "--quiet", "-b", "feature/login", environ=environ)
    return Project(origin, work, base_id)


def build_shallow(tmp_path: Path, *, fetch_base: bool) -> Path:
    """A depth-1 clone of a branch that left `main` before `main` moved on, as a CI checkout is."""
    origin = make_repo(tmp_path / "origin")
    commit_file(origin, PROFILE, profile_text(), "chore: add the profile")
    environ = clean_environ(tmp_path)
    git(origin, "checkout", "--quiet", "-b", "feature/x", environ=environ)
    commit_file(origin, "f.txt", "f\n", "feat: add f")
    git(origin, "checkout", "--quiet", "main", environ=environ)
    commit_file(origin, "later.txt", "later\n", "chore: main moved on")
    git(
        tmp_path,
        *("clone", "--quiet", "--depth", "1", "--branch", "feature/x", origin.as_uri(), "shallow"),
        environ=environ,
    )
    work = tmp_path / "shallow"
    if fetch_base:
        git(work, "fetch", "--quiet", "--depth", "1", "origin", "main:refs/remotes/origin/main")
    assert git(work, "rev-parse", "--is-shallow-repository").strip() == "true"
    return work


@pytest.fixture
def project(tmp_path: Path) -> Project:
    return build_project(tmp_path)


def commit_in(project: Project, message: str, name: str = "change.txt") -> str:
    return commit_file(project.work, name, f"{message}\n", message)


# --- running the command --------------------------------------------------------------------------


def check(root: Path, *args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, ["conventions", "check", *args, "--root", str(root), "--json"])
    return result.exit_code, json.loads(result.stdout)


def check_text(root: Path, *args: str) -> Any:
    return RUNNER.invoke(app, ["conventions", "check", *args, "--root", str(root)])


def codes(document: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in document["findings"]]


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def assert_nothing_raw(root: Path, *args: str, secret: str | None = None) -> None:
    """Neither the human text nor the JSON shows an escape sequence, a right-to-left override, a
    character beyond ASCII from the contributor, or a line that starts with contributor text."""
    human = check_text(root, *args)
    code, document = check(root, *args)
    assert human.exit_code == code == 5
    for text in (human.stdout, human.stderr, "\n".join(_strings(document))):
        for raw in ("\x1b", "\u202e", "\r", *MARKERS):
            assert raw not in text, repr(raw)
        assert not any(line.startswith("::") for line in text.splitlines())
        assert "\n::" not in text
        if secret is not None:
            assert secret not in text
    for finding in document["findings"]:
        assert not finding["message"].startswith(("ZZQ", "::"))
        assert "\n" not in finding["message"]
    for line in human.stdout.splitlines():
        assert not line.startswith(("ZZQ", "::"))
    assert human.stdout.splitlines()[0].startswith(("FAIL", "NOT_RUN"))


# --- PASS: exit 0 ---------------------------------------------------------------------------------


def test_a_good_range_passes_with_exit_0_and_the_usual_envelope(project: Project) -> None:
    """AC-1. expected_behavior_source: the interface decision ("a good range with conventional
    subjects and an allowed branch name -> PASS exit 0"; PASS exits 0), EC-48 and AC-1."""
    commit_in(project, "feat: add the login form")
    commit_in(project, "fix(auth): handle an empty password", "other.txt")

    code, document = check(project.work, "--branch=feature/login", "--base=origin/main")

    assert code == 0, document
    assert document["schema"] == "orqlet.cli-result/v1"
    assert document["command"] == "conventions check"
    assert document["ok"] is True
    assert document["data"]["verdict"] == "PASS"
    assert document["not_run"] == []
    assert "ORQ-E520" not in codes(document)
    assert "ORQ-E521" not in codes(document)


def test_the_human_text_opens_with_the_verdict(project: Project) -> None:
    """AC-1. expected_behavior_source: the interface decision ("the first human line starts with
    the verdict") and EC-48 (the command prints through `output_of`)."""
    commit_in(project, "feat: add the login form")

    result = check_text(project.work, "--branch=feature/login", "--base=origin/main")

    assert result.exit_code == 0
    assert result.stdout.splitlines()[0].startswith("PASS")


def test_the_defaults_find_the_branch_and_the_base_by_themselves(project: Project) -> None:
    """AC-2. expected_behavior_source: the interface decision (defaults, for a local run: the head
    is `HEAD`, the branch is the checked-out one, the base is the target branch of the profile of
    the working tree, resolved as `origin/main`)."""
    commit_in(project, "feat: add the login form")

    code, document = check(project.work)

    assert code == 0, document
    assert document["data"]["verdict"] == "PASS"


def test_the_base_may_be_a_full_commit_id_and_the_head_a_commit_id_or_a_branch_name(
    project: Project,
) -> None:
    """AC-1. expected_behavior_source: the interface decision ("a base given as a full commit id
    ... work[s]"; the head is `vcs.resolve(head)` unless it is `HEAD`)."""
    tip = commit_in(project, "feat: add the login form")

    for args in (
        (f"--base={project.base_id}",),
        ("--base=origin/main", f"--head={tip}"),
        ("--base=origin/main", "--head=feature/login"),
        ("--base=origin/main", "--head=HEAD"),
    ):
        code, document = check(project.work, "--branch=feature/login", *args)
        assert code == 0, (args, document)


def test_a_merge_commit_subject_in_the_range_is_exempt(project: Project) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 4 ("a subject that starts with `Merge ` is
    exempt")."""
    commit_in(project, "Merge branch 'main' into feature/login")

    code, document = check(project.work, "--branch=feature/login", "--base=origin/main")

    assert code == 0, document


# --- FAIL: exit 5 ---------------------------------------------------------------------------------


def test_a_subject_with_the_wrong_shape_fails_with_orq_e521_and_exit_5(project: Project) -> None:
    """AC-1. expected_behavior_source: the interface decision ("a bad subject -> FAIL with
    ORQ-E521") and AC-1."""
    commit_in(project, "feat: add the login form")
    commit_in(project, "wip stuff", "other.txt")

    code, document = check(project.work, "--branch=feature/login", "--base=origin/main")

    assert code == 5, document
    assert document["ok"] is False
    assert document["data"]["verdict"] == "FAIL"
    assert codes(document).count("ORQ-E521") == 1
    assert "ORQ-E520" not in codes(document)


def test_a_failure_prints_the_verdict_first_and_the_code_after_it(project: Project) -> None:
    """AC-1. expected_behavior_source: the interface decision ("the first human line starts with
    the verdict") and EC-48."""
    commit_in(project, "wip stuff")

    result = check_text(project.work, "--branch=feature/login", "--base=origin/main")

    lines = result.stdout.splitlines()
    assert result.exit_code == 5
    assert lines[0].startswith("FAIL")
    assert any("ORQ-E521" in line for line in lines[1:])


def test_a_branch_name_that_no_pattern_allows_fails_with_orq_e520_and_exit_5(
    project: Project,
) -> None:
    """AC-1. expected_behavior_source: the interface decision ("a bad branch (`--branch=wip-stuff`
    with patterns `feature/*`) -> FAIL with ORQ-E520") and AC-1."""
    commit_in(project, "feat: add the login form")

    code, document = check(project.work, "--branch=wip-stuff", "--base=origin/main")

    assert code == 5, document
    assert document["data"]["verdict"] == "FAIL"
    assert "ORQ-E520" in codes(document)
    assert "ORQ-E521" not in codes(document)


def test_the_branch_that_is_checked_out_is_the_default_branch(project: Project) -> None:
    """AC-2. expected_behavior_source: the interface decision (branch: `request.branch` when given,
    else `vcs.current_branch()`)."""
    git(project.work, "checkout", "--quiet", "-b", "wip-stuff")
    commit_in(project, "feat: add the login form")

    code, document = check(project.work)

    assert code == 5, document
    assert "ORQ-E520" in codes(document)


def test_the_default_branch_that_is_the_target_is_skipped_and_is_not_a_pass(
    project: Project,
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("a defaulted branch equal to the target branch is
    skipped with ORQ-I520 and the verdict for that check is NOT_RUN, not PASS") and considerations
    S-14: the repository is on `main`, with a good range of commits ahead of `origin/main`."""
    git(project.work, "checkout", "--quiet", "main")
    commit_in(project, "feat: add the login form")

    code, document = check(project.work, f"--base={project.base_id}")

    assert code == 5, document
    assert document["data"]["verdict"] == "NOT_RUN"
    assert "ORQ-I520" in codes(document)
    assert "ORQ-E520" not in codes(document)


def test_the_profile_of_the_branch_cannot_relax_the_rule_that_judges_it(project: Project) -> None:
    """AC-2. expected_behavior_source: AC-2 and considerations S-14 ("The profile is read at the
    base revision, so a pull request cannot relax the rule that judges it"): the pull request
    commits a profile that allows every branch name and every subject."""
    permissive = profile_text(patterns="**", convention="none")
    commit_file(project.work, PROFILE, permissive, "chore: relax the rules")
    commit_in(project, "wip stuff")

    code, document = check(project.work, "--branch=wip-stuff", "--base=origin/main")

    assert code == 5, document
    assert document["data"]["verdict"] == "FAIL"
    assert "ORQ-E520" in codes(document)
    assert "ORQ-E521" in codes(document)


# --- NOT_RUN: exit 5 ------------------------------------------------------------------------------


def test_a_profile_at_the_base_that_configures_nothing_is_not_run(tmp_path: Path) -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN with the reason for: nothing configured") and
    ADR-003 decision 4 ("An adopter adds the step after the conventions are answered, because
    `NOT_RUN` exits 5")."""
    project = build_project(tmp_path, patterns=None, convention=None)
    commit_in(project, "wip stuff")

    code, document = check(project.work, "--branch=wip-stuff", "--base=origin/main")

    assert code == 5, document
    assert document["ok"] is False
    assert document["data"]["verdict"] == "NOT_RUN"
    assert document["not_run"]
    assert not {"ORQ-E520", "ORQ-E521"} & set(codes(document))


def test_not_run_prints_its_verdict_in_the_human_text(tmp_path: Path) -> None:
    """AC-1. expected_behavior_source: the interface decision ("the first human line starts with
    the verdict"; FAIL and NOT_RUN exit 5)."""
    project = build_project(tmp_path, patterns=None, convention=None)

    result = check_text(project.work, "--branch=feature/login", "--base=origin/main")

    assert result.exit_code == 5
    assert result.stdout.splitlines()[0].startswith("NOT_RUN")


def test_a_shallow_clone_that_lacks_the_base_is_not_run(tmp_path: Path) -> None:
    """AC-1. expected_behavior_source: the interface decision ("a shallow clone (`git clone --depth
    1 file://...` or a repo whose base is not fetched) -> NOT_RUN exit 5"), AC-1 ("a base that
    cannot be resolved") and ADR-003 decision 4 (a shallow clone)."""
    work = build_shallow(tmp_path, fetch_base=False)

    for args in (("--branch=feature/x", "--base=origin/main"), ("--branch=feature/x",)):
        code, document = check(work, *args)
        assert code == 5, document
        assert document["data"]["verdict"] == "NOT_RUN"
        assert document["not_run"]
        assert "ORQ-E520" not in codes(document)


def test_a_shallow_clone_that_has_no_merge_base_is_not_run(tmp_path: Path) -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN ... no merge base"), ADR-003 decision 4 ("a
    shallow clone") and the interface decision (reason 'no merge base'): the base is fetched at
    depth 1, so the two tips share no commit that this clone holds."""
    work = build_shallow(tmp_path, fetch_base=True)

    code, document = check(work, "--branch=feature/x", "--base=origin/main")

    assert code == 5, document
    assert document["data"]["verdict"] == "NOT_RUN"
    assert any("no merge base" in reason for reason in document["not_run"])


@pytest.mark.parametrize("name", ["release/1.0+x", "--upload-pack=x", "a..b", "HEAD~1"])
def test_a_base_name_that_git_could_read_otherwise_is_not_run_and_never_a_traceback(
    project: Project, name: str
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a base ... whose name check_ref_name refuses"),
    ADR-003 decision 4 (`release/1.0+x`; "never a traceback") and the interface decision (`--base`
    as `--base=NAME`; a refused name is NOT_RUN with a reason)."""
    commit_in(project, "feat: add the login form")

    result = RUNNER.invoke(
        app,
        [
            *("conventions", "check", "--branch=feature/login", f"--base={name}"),
            *("--root", str(project.work), "--json"),
        ],
    )

    document = json.loads(result.stdout)
    assert result.exit_code == 5, result.stdout
    assert document["data"]["verdict"] == "NOT_RUN"
    assert "Traceback" not in result.stdout + result.stderr
    assert "internal error" not in result.stdout + result.stderr


def test_a_head_that_names_nothing_is_not_run(project: Project) -> None:
    """AC-1. expected_behavior_source: the interface decision ("an unresolved head" is NOT_RUN)."""
    code, document = check(
        project.work, "--branch=feature/login", "--base=origin/main", "--head=nope"
    )

    assert code == 5, document
    assert document["data"]["verdict"] == "NOT_RUN"


def test_a_directory_that_is_not_a_repository_is_not_run_and_never_a_traceback(
    tmp_path: Path,
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("NOT_RUN ... a Git failure") and ADR-003 decision 4
    ("any Git call fails ... never a traceback")."""
    plain = tmp_path / "plain"
    plain.mkdir()

    result = RUNNER.invoke(app, ["conventions", "check", "--root", str(plain), "--json"])

    assert result.exit_code == 5, result.stdout
    assert json.loads(result.stdout)["data"]["verdict"] == "NOT_RUN"
    assert "Traceback" not in result.stdout + result.stderr


def test_a_repository_without_a_commit_is_not_run(tmp_path: Path) -> None:
    """AC-1. expected_behavior_source: the interface decision (an unresolved head is NOT_RUN: HEAD
    names no commit in an unborn repository)."""
    unborn = make_repo(tmp_path / "unborn")

    code, document = check(unborn, "--branch=feature/login", "--base=origin/main")

    assert code == 5, document
    assert document["data"]["verdict"] == "NOT_RUN"


# --- hostile text from the contributor ------------------------------------------------------------


def test_a_hostile_branch_name_never_reaches_the_terminal_raw(project: Project) -> None:
    """AC-3. expected_behavior_source: AC-3 ("Output lines start with a fixed code prefix, show
    branch ... text only through printable ... and no line starts with contributor text"),
    considerations S-8 and the interface decision (an ESC sequence, U+202E, a `::error::` log
    command): a line break in the branch is followed by a log command."""
    commit_in(project, "feat: add the login form")
    branch = f"ZZQ::error::boom\x1b[2J\u202e{MARKERS}\n::error::injected"

    assert_nothing_raw(project.work, f"--branch={branch}", "--base=origin/main")


def test_a_hostile_subject_never_reaches_the_terminal_raw(project: Project) -> None:
    """AC-3. expected_behavior_source: AC-3, considerations S-8 and the interface decision
    (hostile subject text: an ESC sequence, U+202E, `::error::`; a newline cannot be in a
    subject)."""
    commit_in(project, f"ZZQ::error::boom\x1b[2J\u202e{MARKERS}", "one.txt")
    commit_in(project, "::error::this is not a conventional subject", "two.txt")
    commit_in(project, f"feat: ZZQ\x1b[31m\u202e{MARKERS} has the right shape", "three.txt")

    assert_nothing_raw(project.work, "--branch=feature/login", "--base=origin/main")
    code, document = check(project.work, "--branch=feature/login", "--base=origin/main")
    assert code == 5
    assert "ORQ-E521" in codes(document)


def test_a_very_long_subject_is_cut_and_never_shown_whole(project: Project) -> None:
    """AC-3. expected_behavior_source: AC-3 ("cut at 100 characters"), considerations S-8 and the
    interface decision ("the full text of a long subject never appears")."""
    commit_in(project, "x" * 2000)

    assert_nothing_raw(
        project.work, "--branch=feature/login", "--base=origin/main", secret="x" * 101
    )
    code, document = check(project.work, "--branch=feature/login", "--base=origin/main")
    assert code == 5
    assert "ORQ-E521" in codes(document)


def test_a_very_long_branch_name_is_cut_and_never_shown_whole(project: Project) -> None:
    """AC-3. expected_behavior_source: AC-3 ("cut at 100 characters") and considerations S-8."""
    assert_nothing_raw(
        project.work, f"--branch={'b' * 400}", "--base=origin/main", secret="b" * 101
    )


# --- the command is part of the application -------------------------------------------------------


def registered_names(group: typer.Typer, prefix: str = "") -> set[str]:
    """The commands of an application, named as `IMPLEMENTED_COMMANDS` names them."""
    found = set()
    for command in group.registered_commands:
        callback = command.callback
        name = command.name or (callback.__name__ if callback is not None else "")
        found.add(f"{prefix}{name.removesuffix('_command').replace('_', '-')}".strip())
    for sub in group.registered_groups:
        if sub.typer_instance is not None:
            found |= registered_names(sub.typer_instance, f"{prefix}{sub.name} ")
    return found


def test_the_command_is_listed_as_implemented_and_is_registered() -> None:
    """AC-6. expected_behavior_source: EC-56 (`IMPLEMENTED_COMMANDS` gains `conventions check`),
    the interface decision (the equality test of test_validate_cli.py must still hold) and EC-48."""
    assert "conventions check" in IMPLEMENTED_COMMANDS
    assert "conventions check" in registered_names(app)
    assert registered_names(app) == set(IMPLEMENTED_COMMANDS)


def test_the_module_of_the_command_has_one_public_name_and_it_builds_the_group() -> None:
    """AC-6. expected_behavior_source: EC-48 (`conventions_group() -> typer.Typer`) and the
    interface decision (the module has exactly one public name, the factory)."""
    module = importlib.import_module("orqlet.interface.cli.commands.conventions")

    defined = {
        name
        for name, value in vars(module).items()
        if not name.startswith("_") and getattr(value, "__module__", None) == module.__name__
    }

    assert defined == {"conventions_group"}
    factory: Callable[[], typer.Typer] = module.conventions_group
    assert isinstance(factory(), typer.Typer)


def test_the_help_lists_the_command_and_its_options() -> None:
    """AC-6. expected_behavior_source: EC-48 and the interface decision (`orqlet conventions check
    [--branch NAME] [--base REF] [--head REF] [--root DIR] [--json]`)."""
    group = RUNNER.invoke(app, ["conventions", "--help"])
    command = RUNNER.invoke(app, ["conventions", "check", "--help"])

    plain = re.sub(r"\x1b\[[0-9;]*m", "", command.stdout)  # the help is coloured
    assert group.exit_code == 0
    assert "check" in group.stdout
    assert command.exit_code == 0
    for option in ("--branch", "--base", "--head", "--root", "--json"):
        assert option in plain
