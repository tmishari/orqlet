"""`orqlet validate integrations` through the real command line, on real temporary directories (task
mcp-or-plugins, phase P-3).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-00N-*.md`
under docs/design/mcp-or-plugins/design/, EC-n are the expected changes of the manifest.yaml next
to them, and AC-1 to AC-10 are the acceptance criteria of phase P-3 in
docs/design/mcp-or-plugins/plan.yaml. "The interface decision" is the reading of the plan author
that follows the other validators (tests/integration/test_resources_validate_cli.py): `orqlet
validate integrations [FILE]`; FILE defaults to `.orqlet/integrations.yaml`; PASS exits 0; FAIL and
NOT_RUN exit 5 (`ExitCode.CHECK_FAILED`); `--json` prints the envelope `orqlet.cli-result/v1`.

These tests were written first, by the Tester of phase P-3, before the command existed. The project
is a plain temporary directory: the command needs no Git history and no installation (ADR-002
decision 11). The declaration is the text of the valid fixture with its address replaced by the one
address that the closed table enables. Credential-shaped text is assembled from parts at run time
and never written as one literal (ORQLET-SEC-003).

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- the wording of any message, and the keys of `data` beyond `verdict`;
- the exit code for a root that does not exist;
- whether the human text of a finding shows the path of the file next to its message;
- whether `validate integrations` also prints the warning ORQ-W530 when the declaration is absent;
- the exit code of `doctor` and `sync` for the warning ORQ-W530 is tested at the level of the use
  cases (tests/unit/application/test_diagnose_integrations.py), where the exit code is computed.
"""

from __future__ import annotations

import inspect
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import typer
import yaml
from typer.testing import CliRunner

from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS, PLANNED_COMMANDS
from orqlet.domain.python_api import canonical_signature, extract_module_api
from orqlet.interface.cli.app import app
from orqlet.interface.cli.exit_codes import ExitCode

pytestmark = pytest.mark.integration

RUNNER = CliRunner()
DECLARATION = ".orqlet/integrations.yaml"
MCP = ".mcp.json"
CURSOR = ".cursor/mcp.json"
CODEX = ".codex/config.toml"
LIMIT = 256 * 1024
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
FIXTURE_ADDRESS = "https://docs.example.com/mcp"
ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"
ENTRY = {"type": "http", "url": ATLASSIAN}
SYMLINKS = pytest.mark.skipif(sys.platform == "win32", reason="symbolic links need privileges")

# The commands that existed before phase P-3 (capabilities.py at the base of the phase). The phase
# adds `validate integrations` and nothing else (AC-9, EC-11).
BASE_COMMANDS = frozenset(
    {
        "init",
        "upgrade",
        "rollback",
        "sync",
        "doctor",
        "explain",
        "release",
        "profile answer",
        "profile approve",
        "resources add",
        "resources update",
        "resources remove",
        "resources attach",
        "resources list",
        "conventions check",
        "standards for",
        "validate as-is",
        "validate design",
        "validate plan",
        "validate ledger",
        "validate resources",
        "gate status",
        "evidence cite",
        "evidence hash",
        "knowledge impact",
        "review prepare",
        "validate review",
        "validate test",
        "validate knowledge",
    }
)
# The public names of commands/validate.py at the base of the phase.
BASE_PUBLIC_NAMES = frozenset(
    {
        "BaseOption",
        "FileArgument",
        "HeadOption",
        "LedgerOption",
        "as_is_command",
        "design_command",
        "knowledge_command",
        "ledger_command",
        "output_of",
        "plan_command",
        "record_of_tests_command",
        "resources_command",
        "review_command",
        "validate_app",
    }
)

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0JxQz4M", "Ka8Ty2Vb"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    return project


# --- helpers --------------------------------------------------------------------------------------


def run(root: Path, *args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, ["validate", "integrations", *args, "--root", str(root), "--json"])
    assert result.exit_code != 2, result.output  # 2 is a usage error: the command is not there
    return result.exit_code, json.loads(result.stdout)


def write(root: Path, name: str, data: bytes | str) -> Path:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data.encode() if isinstance(data, str) else data)
    return target


def declaration_text(address: str = ATLASSIAN) -> str:
    """The text of the valid fixture, with its address replaced."""
    text = FIXTURE.read_text(encoding="utf-8").replace(FIXTURE_ADDRESS, address)
    assert address in text
    return text


def mcp_file(entries: dict[str, object]) -> str:
    members = ",\n".join(
        f"    {json.dumps(name)}: {json.dumps(body)}" for name, body in entries.items()
    )
    return f'{{\n  "mcpServers": {{\n{members}\n  }}\n}}\n'


def write_sound(root: Path) -> None:
    """The declaration and the one file that matches it."""
    write(root, DECLARATION, declaration_text())
    write(root, MCP, mcp_file({"orqlet-docs": ENTRY}))


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def codes(document: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in document["findings"]]


def leaks(text: str, secret: str, width: int = 8) -> bool:
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


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


# --- PASS -----------------------------------------------------------------------------------------


def test_a_sound_declaration_with_its_file_passes_with_exit_0_and_the_usual_envelope(
    root: Path,
) -> None:
    """AC-9. expected_behavior_source: the interface decision ("PASS exits 0 ... `--json` prints the
    envelope"), EC-6 and AC-8 (one information finding ORQ-I530 for the registered OAuth server).
    The envelope is the one of `orqlet.cli-result/v1`."""
    write_sound(root)

    code, document = run(root)

    assert code == int(ExitCode.OK), document
    assert document["schema"] == "orqlet.cli-result/v1"
    assert document["command"] == "validate integrations"
    assert document["ok"] is True
    assert document["data"]["verdict"] == "PASS"
    assert document["not_run"] == []
    assert {finding["severity"] for finding in document["findings"]} <= {"info"}
    notes = [f for f in document["findings"] if f["code"] == "ORQ-I530"]
    assert len(notes) == 1
    assert "permission" in notes[0]["message"].lower()


def test_the_file_argument_defaults_to_the_declaration_and_can_name_another_file(
    root: Path,
) -> None:
    """AC-9. expected_behavior_source: AC-9 ("the default file of the command is
    .orqlet/integrations.yaml"), EC-6 (`file: Annotated[str, typer.Argument(...)] =
    '.orqlet/integrations.yaml'`) and the interface decision."""
    write(root, "other/declaration.yaml", declaration_text())
    write(root, MCP, mcp_file({"orqlet-docs": ENTRY}))
    write(root, DECLARATION, "{{{ not yaml")  # the default file breaks the strict loader

    default_code, default_document = run(root)
    other_code, other_document = run(root, "other/declaration.yaml")

    assert (default_code, default_document["data"]["verdict"]) == (5, "FAIL")
    assert (other_code, other_document["data"]["verdict"]) == (0, "PASS")


def test_the_default_file_is_the_one_that_the_manifest_says(root: Path) -> None:
    """AC-9. expected_behavior_source: EC-6 and AC-9 ("the default file of the command is
    .orqlet/integrations.yaml"): the same command, with and without the argument, reads the same
    file."""
    write_sound(root)

    assert run(root) == run(root, DECLARATION)


def test_a_file_that_is_checked_is_not_changed(root: Path) -> None:
    """AC-9. expected_behavior_source: the module docstring of validation.py ("A validator never
    writes") and ADR-002 decision 6."""
    write_sound(root)
    write(root, CURSOR, mcp_file({"orqlet-x": ENTRY}))
    before = snapshot(root)

    run(root)

    assert snapshot(root) == before


def test_the_human_text_opens_with_the_verdict(root: Path) -> None:
    """AC-9. expected_behavior_source: EC-6 (the command prints through `output_of`: the verdict
    first, as `render_validation` writes it)."""
    write_sound(root)

    result = RUNNER.invoke(app, ["validate", "integrations", "--root", str(root)])

    assert result.exit_code == 0
    assert result.stdout.splitlines()[0].startswith("PASS")


# --- FAIL: exit 5 ---------------------------------------------------------------------------------


def _differing_entry(root: Path) -> None:
    write_sound(root)
    write(root, MCP, mcp_file({"orqlet-docs": {"type": "sse", "url": ATLASSIAN}}))


def _absent_entry(root: Path) -> None:
    write_sound(root)
    write(root, MCP, mcp_file({}))


def _undeclared_entry(root: Path) -> None:
    write_sound(root)
    write(root, MCP, mcp_file({"orqlet-docs": ENTRY, "Orqlet-Other": ENTRY}))


def _reference_in_an_entry(root: Path) -> None:
    write_sound(root)
    write(
        root,
        MCP,
        mcp_file(
            {
                "orqlet-docs": ENTRY,
                "team": {"url": "https://team.example.com/mcp", "headers": {"X": "Bearer ${NAME}"}},
            }
        ),
    )


def _closed_key(root: Path) -> None:
    write_sound(root)
    write(
        root,
        MCP,
        mcp_file(
            {
                "orqlet-docs": ENTRY,
                "team": {"url": "https://team.example.com/mcp", "headersHelper": "x"},
            }
        ),
    )


def _token_in_a_file(root: Path) -> None:
    write_sound(root)
    write(
        root,
        CURSOR,
        mcp_file({"team": {"url": "https://team.example.com/mcp", "env": {"NAME": TOKEN}}}),
    )


def _token_in_the_toml_file(root: Path) -> None:
    write_sound(root)
    write(root, CODEX, f'[mcp_servers.team]\nGITHUB = "{TOKEN}"\n')


def _directory_in_the_place_of_a_file(root: Path) -> None:
    write_sound(root)
    (root / CURSOR).mkdir(parents=True)


def _file_that_is_not_utf_8(root: Path) -> None:
    write_sound(root)
    write(root, CURSOR, b'{"mcpServers": {"x": "\xff\xfe"}}')


def comment_lines(size: int) -> str:
    """Short comment lines that add up to at least `size` bytes, so that no line is long."""
    return ("#" + "x" * 62 + "\n") * (size // 64 + 1)


def _file_above_the_cap(root: Path) -> None:
    write_sound(root)
    write(root, CODEX, comment_lines(LIMIT))


def _duplicate_key(root: Path) -> None:
    write_sound(root)
    write(root, CURSOR, '{"mcpServers": {"a": {}, "a": {}}}')


def _wrong_shape(root: Path) -> None:
    write_sound(root)
    write(root, CURSOR, "[]")


def _not_json(root: Path) -> None:
    write_sound(root)
    write(root, CURSOR, "{{{ not json")


def _declaration_above_the_cap(root: Path) -> None:
    write(root, DECLARATION, declaration_text() + comment_lines(LIMIT))


def _declaration_breaks_the_strict_loader(root: Path) -> None:
    write(root, DECLARATION, "servers: &a []\nagain: *a\n")


def _declaration_breaks_the_contract(root: Path) -> None:
    write(root, DECLARATION, declaration_text() + "surprise: 1\n")


def _declaration_names_an_address_off_the_table(root: Path) -> None:
    write(root, DECLARATION, declaration_text(FIXTURE_ADDRESS))


def _declaration_holds_a_token(root: Path) -> None:
    text = declaration_text().replace("documentation search", f"use {TOKEN} to sign in")
    assert TOKEN in text
    write(root, DECLARATION, text)


FAILURES: dict[str, tuple[Callable[[Path], None], str]] = {
    "an-entry-that-differs": (_differing_entry, "ORQ-E535"),
    "a-declared-entry-that-is-absent": (_absent_entry, "ORQ-E536"),
    "an-undeclared-orqlet-entry": (_undeclared_entry, "ORQ-E537"),
    "a-reference-in-an-entry": (_reference_in_an_entry, "ORQ-E538"),
    "a-closed-key": (_closed_key, "ORQ-E538"),
    "a-token-in-the-file-of-cursor": (_token_in_a_file, "ORQ-E539"),
    "a-token-in-the-file-of-codex": (_token_in_the_toml_file, "ORQ-E539"),
    "a-directory-in-the-place-of-a-file": (_directory_in_the_place_of_a_file, "ORQ-E534"),
    "a-file-that-is-not-utf-8": (_file_that_is_not_utf_8, "ORQ-E534"),
    "a-file-above-256-kib": (_file_above_the_cap, "ORQ-E534"),
    "a-duplicate-key": (_duplicate_key, "ORQ-E534"),
    "valid-json-of-the-wrong-shape": (_wrong_shape, "ORQ-E534"),
    "a-file-that-is-not-json": (_not_json, "ORQ-E534"),
    "a-declaration-above-256-kib": (_declaration_above_the_cap, "ORQ-E530"),
    "a-declaration-that-breaks-the-strict-loader": (
        _declaration_breaks_the_strict_loader,
        "ORQ-E530",
    ),
    "a-declaration-that-breaks-the-contract": (_declaration_breaks_the_contract, "ORQ-E531"),
    "an-address-that-is-off-the-table": (_declaration_names_an_address_off_the_table, "ORQ-E532"),
    "a-declaration-that-holds-a-token": (_declaration_holds_a_token, "ORQ-E533"),
}


@pytest.mark.parametrize("name", list(FAILURES), ids=list(FAILURES))
def test_a_declaration_or_a_file_that_fails_exits_5_with_the_code_of_the_rule(
    root: Path, name: str
) -> None:
    """AC-9. expected_behavior_source: AC-9 ("exit codes follow exit_codes.py": a failed check is
    `ExitCode.CHECK_FAILED`, 5), the interface decision ("FAIL and NOT_RUN exit 5"), ADR-002
    Consequences ("They exit 5 on any error above") and the codes of the plan (ORQ-E530 to
    ORQ-E539)."""
    build, expected = FAILURES[name]
    build(root)

    code, document = run(root)

    assert code == int(ExitCode.CHECK_FAILED), document
    assert document["ok"] is False
    assert document["data"]["verdict"] == "FAIL"
    assert expected in codes(document)


@SYMLINKS
@pytest.mark.parametrize("where", [MCP, CURSOR, CODEX])
def test_a_link_in_the_place_of_an_mcp_file_is_not_followed_and_exits_5(
    root: Path, tmp_path: Path, where: str
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("when a declaration exists, a link ... give[s] an error
    finding for that file, exit 5") and ORQLET-SEC-002 (the FileSystem port refuses links), on a
    real file system."""
    write_sound(root)
    outside = write(tmp_path, "outside.json", mcp_file({"orqlet-docs": ENTRY}))
    target = root / where
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    target.symlink_to(outside)

    code, document = run(root)

    assert code == 5, document
    assert "ORQ-E534" in codes(document)


@SYMLINKS
def test_a_link_in_a_parent_folder_of_an_mcp_file_exits_5(root: Path, tmp_path: Path) -> None:
    """AC-5. expected_behavior_source: AC-5 ("a link in a parent folder") and ADR-002 decision 8
    ("including a link in a parent folder"), on a real file system."""
    write_sound(root)
    outside = tmp_path / "outside"
    write(outside, "mcp.json", mcp_file({"orqlet-other": ENTRY}))
    (root / ".cursor").symlink_to(outside, target_is_directory=True)

    code, document = run(root)

    assert code == 5, document
    assert "ORQ-E534" in codes(document)


@SYMLINKS
def test_a_declaration_that_is_a_link_exits_5_and_is_not_an_absent_declaration(
    root: Path, tmp_path: Path
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 ("a link must not hide an entry from the
    validator while a client may follow it") and ADR-003 decision 6 (not run only when absent)."""
    outside = write(tmp_path, "outside.yaml", declaration_text())
    (root / ".orqlet").mkdir()
    (root / DECLARATION).symlink_to(outside)

    code, document = run(root)

    assert code == 5
    assert document["data"]["verdict"] == "FAIL"
    assert "ORQ-E530" in codes(document)


def test_a_failure_prints_the_verdict_first_and_the_code_after_it(root: Path) -> None:
    """AC-9. expected_behavior_source: EC-6 (the command prints through `output_of`: the verdict,
    then what the check found) and the interface decision (exit 5)."""
    _undeclared_entry(root)

    result = RUNNER.invoke(app, ["validate", "integrations", "--root", str(root)])

    lines = result.stdout.splitlines()
    assert result.exit_code == 5
    assert lines[0].startswith("FAIL")
    assert any("ORQ-E537" in line for line in lines[1:])


def test_an_unsafe_path_is_a_finding_and_not_a_traceback(root: Path) -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 3 (the reader returns findings: a path that
    cannot be read safely is ORQ-E530) and the interface decision."""
    code, document = run(root, "../outside.yaml")

    assert code == 5
    assert document["data"]["verdict"] == "FAIL"
    assert "ORQ-E530" in codes(document)


def test_a_finding_shows_no_part_of_a_value_or_a_key_of_a_file(root: Path) -> None:
    """AC-2. expected_behavior_source: AC-2 ("No message, finding or exit text of the reader or the
    validator holds a credential-shaped value or a raw key"), ADR-002 decision 9 and ORQLET-SEC-003,
    through the command line: the standard output and the standard error, as JSON and as text."""
    write_sound(root)
    write(
        root,
        MCP,
        mcp_file(
            {
                "orqlet-docs": {**ENTRY, OPAQUE: 1},
                TOKEN: {"url": "https://team.example.com/mcp", "env": {OPAQUE: TOKEN}},
                f"orqlet-{OPAQUE.lower()}": ENTRY,
            }
        ),
    )
    write(root, CURSOR, f'{{"mcpServers": {{"{OPAQUE}": {{}}, "{OPAQUE}": {{}}}}}}')

    as_json = RUNNER.invoke(app, ["validate", "integrations", "--root", str(root), "--json"])
    as_text = RUNNER.invoke(app, ["validate", "integrations", "--root", str(root)])

    assert as_json.exit_code == as_text.exit_code == 5
    for result in (as_json, as_text):
        for secret in (TOKEN, OPAQUE):
            assert not leaks(result.stdout, secret)
            assert not leaks(result.stderr, secret)


def test_a_finding_shows_no_part_of_a_value_or_a_key_of_the_declaration(root: Path) -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-002 decision 9 (the loader prints a rule and a
    closed field name, never a key or a value), through the command line."""
    data = yaml.safe_load(declaration_text())
    data["servers"][0][OPAQUE] = 1
    data["servers"][0]["per_client"][TOKEN] = {"register": "not-a-boolean"}
    data["roles"][OPAQUE.lower()] = {"servers": "not-a-list"}
    write(root, DECLARATION, json.dumps(data))

    as_json = RUNNER.invoke(app, ["validate", "integrations", "--root", str(root), "--json"])
    as_text = RUNNER.invoke(app, ["validate", "integrations", "--root", str(root)])

    assert as_json.exit_code == as_text.exit_code == 5
    for result in (as_json, as_text):
        for secret in (TOKEN, OPAQUE):
            assert not leaks(result.stdout, secret)
            assert not leaks(result.stderr, secret)


# --- NOT_RUN: exit 5 ------------------------------------------------------------------------------


def test_a_project_without_a_declaration_is_not_run_and_exits_5(root: Path) -> None:
    """AC-6. expected_behavior_source: AC-6 ("With no declaration, validate integrations is not run
    (exit 5) by its own existence check") and ADR-002 decision 11 ("returns not run (exit 5) when
    the declaration is absent") and ORQLET W-5 (not run is never success)."""
    code, document = run(root)

    assert code == int(ExitCode.CHECK_FAILED)
    assert document["ok"] is False
    assert document["data"]["verdict"] == "NOT_RUN"
    assert document["not_run"]
    assert not [f for f in document["findings"] if f["severity"] == "error"]


def test_a_file_that_holds_an_orqlet_name_does_not_make_a_missing_declaration_a_failure(
    root: Path,
) -> None:
    """AC-6. expected_behavior_source: AC-6 (the command is not run when the declaration is absent;
    the warning ORQ-W530 is for `doctor` and `sync`) and ADR-002 decision 11."""
    write(root, MCP, mcp_file({"orqlet-docs": ENTRY, "team": {"env": {"NAME": TOKEN}}}))

    code, document = run(root)

    assert code == 5
    assert document["data"]["verdict"] == "NOT_RUN"
    assert not [f for f in document["findings"] if f["severity"] == "error"]


def test_not_run_prints_its_verdict_in_the_human_text(root: Path) -> None:
    """AC-6. expected_behavior_source: EC-6 (`output_of`: the verdict first, then why anything was
    not run) and the interface decision (exit 5)."""
    result = RUNNER.invoke(app, ["validate", "integrations", "--root", str(root)])

    assert result.exit_code == 5
    assert result.stdout.splitlines()[0].startswith("NOT_RUN")


def test_a_command_without_an_installation_still_runs(root: Path) -> None:
    """AC-7. expected_behavior_source: AC-7 ("validate integrations needs no installed profile") and
    ADR-002 decision 11 ("It works without an installed profile"): the project is no Git repository
    and holds no `.orqlet` file but the declaration."""
    write_sound(root)

    code, document = run(root)

    assert code == 0, document
    assert sorted(path.name for path in root.iterdir()) == [".mcp.json", ".orqlet"]


# --- AC-9, EC-6, EC-11: the command is part of the application ------------------------------------


def test_the_implemented_commands_differ_from_the_base_by_exactly_the_new_command() -> None:
    """AC-9. expected_behavior_source: AC-9 ("IMPLEMENTED_COMMANDS and the commands that the CLI
    registers differ by exactly validate integrations") and EC-11 (IMPLEMENTED_COMMANDS gains
    `validate integrations`). The base is the list of `BASE_COMMANDS` above."""
    added = IMPLEMENTED_COMMANDS - BASE_COMMANDS

    assert added == {"validate integrations"}
    assert BASE_COMMANDS <= IMPLEMENTED_COMMANDS


def test_the_commands_that_the_application_registers_are_the_implemented_commands() -> None:
    """AC-9. expected_behavior_source: AC-9 and EC-6 (`integrations_command`): a command registered
    as `integrations` on the `validate` group is `validate integrations`. The equality test of
    tests/integration/test_validate_cli.py needs no change."""
    assert registered_names(app) == set(IMPLEMENTED_COMMANDS)
    assert registered_names(app) - BASE_COMMANDS == {"validate integrations"}
    assert "validate integrations" not in PLANNED_COMMANDS


def test_the_validate_group_lists_the_command_in_its_help() -> None:
    """AC-9. expected_behavior_source: EC-6 (the command is part of the `validate` group)."""
    result = RUNNER.invoke(app, ["validate", "--help"])

    assert result.exit_code == 0
    assert "integrations" in result.stdout


def test_the_command_has_the_signature_that_the_manifest_gives() -> None:
    """AC-9. expected_behavior_source: EC-6 (`def integrations_command(file: Annotated[str,
    typer.Argument(help='The declaration, relative to the root.')]='.orqlet/integrations.yaml',
    root: RootOption=Path(), json_output: JsonOption=False) -> None`) and AC-10 (the one new public
    name of the module): the module has the names of the base and this one."""
    import orqlet.interface.cli.commands.validate as module

    assert module.__file__ is not None
    api = extract_module_api(Path(module.__file__).read_text(encoding="utf-8"))

    assert api.errors == ()
    assert api.manual == ()
    assert frozenset(api.symbols) == BASE_PUBLIC_NAMES | {"integrations_command"}
    assert api.symbols["integrations_command"].signature == canonical_signature(
        "def integrations_command(file: Annotated[str, typer.Argument("
        "help='The declaration, relative to the root.')]='.orqlet/integrations.yaml', "
        "root: RootOption=Path(), json_output: JsonOption=False) -> None"
    )


def test_the_default_of_the_file_argument_is_the_declaration() -> None:
    """AC-9. expected_behavior_source: AC-9 ("the default file of the command is
    .orqlet/integrations.yaml") and EC-6."""
    from orqlet.interface.cli.commands.validate import integrations_command

    assert inspect.signature(integrations_command).parameters["file"].default == DECLARATION


def test_the_capabilities_module_adds_no_public_name() -> None:
    """AC-10. expected_behavior_source: AC-10 and EC-11 ("The extractor reads an assignment by name
    only, so it cannot see the new entry": the set gains an entry, the module gains no name)."""
    import orqlet.application.usecases.capabilities as module

    assert module.__file__ is not None
    api = extract_module_api(Path(module.__file__).read_text(encoding="utf-8"))

    assert frozenset(api.symbols) == {"IMPLEMENTED_COMMANDS", "PLANNED_COMMANDS"}
