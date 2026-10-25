"""`GitRunner` builds only allow-listed, hardened command lines."""

from __future__ import annotations

import pytest

from orqlet.adapters.git.git_runner import ALLOWED_SUBCOMMANDS, GitRunner
from orqlet.application.ports.process import ProcessResult
from orqlet.application.ports.vcs import VcsError
from tests.fakes.process import ScriptedProcessRunner

pytestmark = pytest.mark.unit

HARDENING = ("git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=")


def ok(stdout: bytes = b"") -> ProcessResult:
    return ProcessResult(("git",), 0, stdout, b"")


def runner_with(*results: ProcessResult) -> tuple[GitRunner, ScriptedProcessRunner]:
    process = ScriptedProcessRunner(list(results))
    environ = {"PATH": "/bin", "HOME": "/h", "GIT_DIR": "/evil", "GIT_EXTERNAL_DIFF": "evil"}
    return GitRunner(process, "/repo", environ=environ), process


def test_every_call_starts_with_the_hardening_options() -> None:
    git, process = runner_with(ok())

    git.run("rev-parse", "HEAD")

    assert process.calls[0][:5] == HARDENING
    assert process.calls[0][5:] == ("rev-parse", "HEAD")


@pytest.mark.parametrize(
    "args", [("diff-tree", "-r", "HEAD", "HEAD"), ("diff-index", "--cached", "HEAD")]
)
def test_diff_commands_never_run_external_programs(args: tuple[str, ...]) -> None:
    git, process = runner_with(ok())

    git.run(*args)

    assert process.calls[0][5:8] == (args[0], "--no-ext-diff", "--no-textconv")


@pytest.mark.parametrize(
    "subcommand", ["status", "diff", "add", "checkout", "config", "init", "-c", "--exec-path", ""]
)
def test_subcommands_outside_the_allow_list_are_refused(subcommand: str) -> None:
    git, process = runner_with()

    with pytest.raises(VcsError, match="not allowed"):
        git.run(subcommand)

    assert process.calls == []


def test_the_allow_list_is_the_decision_records_plus_the_one_amendment() -> None:
    # `check-ignore` was added after ADR-003 so Orqlet can warn that a generated file is ignored
    # by Git. It reads ignore files only and runs no configured program. Any further change
    # needs the same deliberate edit here and in the decision record.
    assert {
        "rev-parse",
        "for-each-ref",
        "rev-list",
        "merge-base",
        "ls-files",
        "ls-tree",
        "cat-file",
        "diff-tree",
        "diff-index",
        "write-tree",
        "check-ignore",
    } == ALLOWED_SUBCOMMANDS


def test_the_environment_is_scrubbed_and_fixed() -> None:
    git, process = runner_with(ok())

    git.run("rev-parse", "HEAD")

    assert process.environments[0] == {
        "PATH": "/bin",
        "HOME": "/h",
        "LC_ALL": "C",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_PAGER": "cat",
        "GIT_OPTIONAL_LOCKS": "0",
    }


def test_an_unaccepted_return_code_is_a_vcs_error_with_the_first_stderr_line() -> None:
    failure = ProcessResult(("git",), 128, b"", b"fatal: bad thing\nsecond line\n")
    git, _ = runner_with(failure)

    with pytest.raises(VcsError, match="fatal: bad thing"):
        git.run("rev-parse", "HEAD")


def test_an_accepted_return_code_is_returned() -> None:
    git, _ = runner_with(ProcessResult(("git",), 1, b"", b""))

    assert git.run("rev-parse", "--verify", "HEAD", accept=(0, 1)).returncode == 1


@pytest.mark.parametrize("branch", ["refs/heads/x", "@", "-bad", "--help"])
def test_init_rejects_dangerous_branch_names_before_running_git(branch: str) -> None:
    git, process = runner_with()

    with pytest.raises(VcsError):
        git.init_repository(branch)

    assert process.calls == []


def test_init_checks_the_name_with_git_then_passes_it_as_one_attached_option() -> None:
    git, process = runner_with(ok(b"main\n"), ok())

    git.init_repository("main")

    assert process.calls[0][5:] == ("check-ref-format", "--branch", "main")
    assert process.calls[1][5:] == ("init", "--quiet", "--initial-branch=main")


def test_init_refuses_a_name_that_git_rejects() -> None:
    git, process = runner_with(ProcessResult(("git",), 1, b"", b""))

    with pytest.raises(VcsError, match="not a valid branch"):
        git.init_repository("bad..name")

    assert len(process.calls) == 1


@pytest.mark.parametrize(
    "args",
    [
        ("diff-index", "HEAD"),
        ("ls-files", "--modified"),
        ("ls-files", "-m"),
        ("ls-files", "-om"),
        ("ls-files", "-z", "--eol"),
        ("cat-file", "--filters", "HEAD:a"),
        ("cat-file", "--textconv", "HEAD:a"),
        ("diff-tree", "--ext-diff", "A", "B"),
        ("diff-index", "--cached", "--textconv", "HEAD"),
    ],
)
def test_options_that_run_repository_programs_are_refused(args: tuple[str, ...]) -> None:
    git, process = runner_with()

    with pytest.raises(VcsError, match="not allowed"):
        git.run(*args)

    assert process.calls == []


def test_safe_forms_of_the_same_subcommands_are_accepted() -> None:
    git, process = runner_with(ok(), ok(), ok(), ok())

    git.run("diff-index", "--cached", "--quiet", "HEAD")
    git.run("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    git.run("cat-file", "--batch")
    git.run("ls-files", "--cached", "--", "-m")

    assert len(process.calls) == 4


def test_check_ignore_gets_its_names_on_stdin_and_never_as_options() -> None:
    git, process = runner_with(ok(b""))

    git.run("check-ignore", "-z", "--stdin", stdin=b"-rf\0", accept=(0, 1))

    assert process.calls[0][5:] == ("check-ignore", "-z", "--stdin")
