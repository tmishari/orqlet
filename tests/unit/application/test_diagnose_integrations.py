"""`doctor` and `sync` run the check of the MCP configuration (task mcp-or-plugins, phase P-3).

Every test cites its `expected_behavior_source`. ADR-002 and ADR-003 are the files `adr-00N-*.md`
under docs/design/mcp-or-plugins/design/, EC-n are the expected changes of the manifest.yaml next
to them, and AC-1 to AC-10 are the acceptance criteria of phase P-3 in
docs/design/mcp-or-plugins/plan.yaml. The codes are the plan's: ORQ-E530 to ORQ-E539 errors,
ORQ-W530 the declaration is absent and an MCP file holds `orqlet-`, ORQ-I530 to ORQ-I533
information. "The family" below is that set of codes.

These tests were written first, by the Tester of phase P-3, before `doctor` and `sync` called
`integration_findings`. The file system is the in-memory fake of tests/fakes and the services are
the ones of tests/support/init_env.py (ORQLET-TEST-001). The exit code of `doctor` and `sync` is the
one that the command computes from the findings (`_check_exit` in interface/cli/commands/
lifecycle.py, as the tests of tests/unit/application/test_conventions_questions.py read it): any
error gives 5, any warning gives 1, information only gives 0. Credential-shaped text is assembled
from parts at run time and never written as one literal (ORQLET-SEC-003).

Behaviour that the plan and the ADRs leave open is deliberately not pinned here:
- the wording of any message beyond what a criterion states, and what `Finding.path` holds;
- whether ORQ-W530 is printed once per file or once in all when several files hold `orqlet-` (only a
  single file is tested for a count);
- the findings of the integration check when the declaration is invalid beyond the codes of the
  reader (ORQ-E530 to ORQ-E533);
- whether `doctor` and `sync` list the integration check in `not_run` when it ran;
- the order of the findings.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.diagnose import Diagnosis, doctor, sync
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import NotInitialised

# isort: split
from orqlet.application.usecases.validate_integrations import (
    integration_findings,
    validate_integrations,
)

# isort: split
from orqlet.application.usecases.validation import ValidateServices
from orqlet.domain.findings import Finding, Severity, Verdict
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.python_api import extract_module_api
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED
from tests.support.init_env import Env, tree
from tests.support.trees import repo

pytestmark = pytest.mark.unit

DECLARATION_PATH = ".orqlet/integrations.yaml"
MCP = ".mcp.json"
CURSOR = ".cursor/mcp.json"
CODEX = ".codex/config.toml"
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.integrations.v1.yaml"
)
LOADER = StrictYamlLoader()
YES = InitOptions(assume_yes=True)
ATLASSIAN = "https://mcp.atlassian.com/v2/mcp"
EDITABLE = "client-enforced-editable"
ENTRY: dict[str, Any] = {"type": "http", "url": ATLASSIAN}
NOT_CHECKED = "ORQ-W530"
FULL_PERMISSIONS = "ORQ-I530"
NOT_READ = "ORQ-I533"
DIFFERS = "ORQ-E535"
UNREADABLE_FILE = "ORQ-E534"
FAMILY = frozenset(
    {f"ORQ-E53{n}" for n in range(10)} | {NOT_CHECKED} | {f"ORQ-I53{n}" for n in range(4)}
)
# The base public names of diagnose.py: the hook is private and adds none (AC-10, EC-16).
BASE_PUBLIC_NAMES = frozenset(
    {"Diagnosis", "Drift", "DriftState", "RESERVED_PREFIX", "doctor", "measure_drift", "sync"}
)

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0JxQz4M", "Ka8Ty2Vb"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))
MARKER = OPAQUE.lower()


# --- helpers --------------------------------------------------------------------------------------


def initialised() -> Env:
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    assert init_project(env.services(), YES).status == "applied"
    return env


def uninitialised() -> Env:
    return Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))


def server(server_id: str = "docs", *, url: str = ATLASSIAN) -> dict[str, Any]:
    """A server of the valid declaration, built from the fixture's first one."""
    loaded = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    base: dict[str, Any] = json.loads(json.dumps(loaded["servers"][0]))
    base.update(
        id=server_id,
        identity={"kind": "remote", "url": url},
        registration={"name": f"orqlet-{server_id}", "mode": "read-only", "enforced_by": EDITABLE},
        per_client={"claude-code": {"register": True, "enforced_by": EDITABLE}},
        clients=["claude-code"],
    )
    return base


def declaration(*servers: dict[str, Any]) -> bytes:
    loaded = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    loaded["servers"] = list(servers)
    loaded["roles"] = {"architecture-reviewer": {"servers": [item["id"] for item in servers]}}
    return json.dumps(loaded, indent=2).encode()


DECLARED = declaration(server())
TWO_DECLARED = declaration(server("docs"), server("wiki"))


def entries_file(entries: Mapping[str, object]) -> bytes:
    members = ",\n".join(
        f"    {json.dumps(name)}: {json.dumps(body)}" for name, body in entries.items()
    )
    return f'{{\n  "mcpServers": {{\n{members}\n  }}\n}}\n'.encode()


GOOD = entries_file({"orqlet-docs": ENTRY})


def put(env: Env, name: str, data: bytes | str) -> None:
    raw = data.encode() if isinstance(data, str) else data
    env.project.write_atomic(CanonicalPath.parse(name), raw)


def declare(env: Env, data: bytes = DECLARED) -> None:
    """The team's declaration, as a hand edit leaves it: the file changes, the lock does not."""
    put(env, DECLARATION_PATH, data)


def diagnose(env: Env) -> Diagnosis:
    return doctor(env.services())


def synchronise(env: Env) -> Diagnosis:
    return sync(env.services())


def exit_code_of(diagnosis: Diagnosis) -> int:
    """The exit code of `orqlet doctor` or `orqlet sync` for these findings, by the rule of the
    command itself."""
    from orqlet.interface.cli.commands.lifecycle import _check_exit

    return int(_check_exit(diagnosis.findings))


def codes(findings: Sequence[Finding]) -> set[str]:
    return {finding.code for finding in findings}


def with_code(findings: Sequence[Finding], code: str) -> list[Finding]:
    return [finding for finding in findings if finding.code == code]


def in_family(findings: Sequence[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.code in FAMILY]


def errors(findings: Sequence[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.severity is Severity.ERROR]


def shown(findings: Sequence[Finding]) -> str:
    return "\n".join(
        f"{finding.code}\n{finding.message}\n{finding.path}\n{finding!r}" for finding in findings
    )


def leaks(text: str, secret: str, width: int = 8) -> bool:
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def signature_of(findings: Sequence[Finding]) -> Counter[tuple[str, Severity]]:
    """The findings of the family as a multiset of (code, severity)."""
    return Counter((finding.code, finding.severity) for finding in in_family(findings))


# --- a setup that has no declaration and no MCP file ----------------------------------------------


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
def test_a_fresh_setup_has_no_finding_of_the_family(command: Any) -> None:
    """AC-6. expected_behavior_source: AC-6 ("doctor and sync ... print nothing for a project
    without such a name") and ADR-003 consequences ("A project with no declaration is unchanged in
    the files it holds"). `init` writes no declaration and no MCP file."""
    assert in_family(command(initialised()).findings) == []


def test_the_baseline_exit_codes_that_the_other_tests_compare_with() -> None:
    """AC-6. expected_behavior_source: the existing behaviour of `doctor` (a draft profile is a
    warning: exit 1) and `sync` (only notes: exit 0), as tests/integration/test_lifecycle_cli.py
    reads it. This holds before the change and guards the premise of the exit tests below."""
    env = initialised()

    assert exit_code_of(diagnose(env)) == 1
    assert exit_code_of(synchronise(env)) == 0


# --- a declaration --------------------------------------------------------------------------------


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
def test_a_declaration_and_the_matching_file_give_no_error_and_one_note_about_permissions(
    command: Any,
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("doctor and sync both run integration_findings"), AC-8
    ("For each registered OAuth server validate integrations and doctor print one information
    finding I530") and ADR-003 decision 6 (`doctor` and `sync` call `integration_findings`)."""
    env = initialised()
    declare(env)
    put(env, MCP, GOOD)

    result = command(env)

    assert len(with_code(result.findings, FULL_PERMISSIONS)) == 1
    assert errors(in_family(result.findings)) == []
    assert NOT_CHECKED not in codes(result.findings)
    assert all(f.severity is Severity.INFO for f in in_family(result.findings))


def test_a_clean_declaration_leaves_the_exit_code_of_sync_at_zero() -> None:
    """AC-7. expected_behavior_source: ADR-002 decision 6 and AC-8 (information findings only) and
    ADR-002 decision 11 ("A warning makes `doctor` exit 1, like the other warnings": information
    does not)."""
    env = initialised()
    declare(env)
    put(env, MCP, GOOD)

    assert exit_code_of(synchronise(env)) == 0


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
def test_an_entry_that_differs_from_the_declaration_is_an_error_of_the_command(
    command: Any,
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("doctor and sync both run integration_findings"), plan
    P-3 objective (ORQ-E535) and ADR-002 decision 11 ("`orqlet doctor` and `orqlet sync` run
    `integration_findings` like their other checks") and the Consequences ("They exit 5 on any
    error above")."""
    env = initialised()
    declare(env)
    put(env, MCP, entries_file({"orqlet-docs": {"type": "sse", "url": ATLASSIAN}}))

    result = command(env)

    assert with_code(result.findings, DIFFERS)
    assert exit_code_of(result) == 5


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
def test_an_undeclared_orqlet_entry_and_an_absent_declared_entry_are_errors_of_the_command(
    command: Any,
) -> None:
    """AC-7. expected_behavior_source: AC-7, plan P-3 objective (ORQ-E536, ORQ-E537) and ADR-003
    decision 6 ("an existing MCP file that lacks a declared entry is an error")."""
    env = initialised()
    declare(env)
    put(env, MCP, entries_file({"orqlet-other": ENTRY}))

    result = command(env)

    assert {"ORQ-E536", "ORQ-E537"} <= codes(result.findings)
    assert exit_code_of(result) == 5


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"{{{ not yaml", "ORQ-E530"),
        (json.dumps({**json.loads(DECLARED), "surprise": 1}).encode(), "ORQ-E531"),
        (declaration(server(url="https://docs.example.com/mcp")), "ORQ-E532"),
        (declaration({**server(), "purpose": f"use {TOKEN}"}), "ORQ-E533"),
    ],
    ids=["strict-loader", "contract", "closed-table", "scan"],
)
def test_an_invalid_declaration_is_an_error_of_the_command(
    command: Any, data: bytes, code: str
) -> None:
    """AC-7. expected_behavior_source: AC-7, plan P-3 objective (ORQ-E530 to ORQ-E533) and ADR-003
    decision 3 ("`validate integrations` and `doctor` call the shared function
    `integration_findings`, so exit 3 and exit 5 come from one reader")."""
    env = initialised()
    declare(env, data)

    result = command(env)

    assert code in codes(result.findings)
    assert exit_code_of(result) == 5
    assert not leaks(shown(result.findings), TOKEN)


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
def test_a_link_in_the_place_of_an_mcp_file_is_an_error_when_a_declaration_exists(
    command: Any,
) -> None:
    """AC-5. expected_behavior_source: AC-5 ("when a declaration exists, a link ... give[s] an error
    finding for that file, exit 5") and ADR-002 decision 8, through `doctor` and `sync`."""
    env = initialised()
    declare(env)
    env.project.add_symlink(MCP)

    result = command(env)

    assert UNREADABLE_FILE in codes(result.findings)
    assert exit_code_of(result) == 5


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
def test_each_registered_oauth_server_gets_its_own_note_about_permissions(command: Any) -> None:
    """AC-8. expected_behavior_source: AC-8 ("For each registered OAuth server validate integrations
    and doctor print one information finding I530 that says the entry gives the user's full
    permissions") and ADR-002 decision 10."""
    env = initialised()
    declare(env, TWO_DECLARED)
    put(env, MCP, entries_file({"orqlet-docs": ENTRY, "orqlet-wiki": ENTRY}))

    notes = with_code(command(env).findings, FULL_PERMISSIONS)

    assert len(notes) == 2
    for note in notes:
        assert note.severity is Severity.INFO
        assert "permission" in note.message.lower()


# --- the findings are the ones of the shared function ---------------------------------------------


def _clean(env: Env) -> None:
    declare(env)
    put(env, MCP, GOOD)


def _differing(env: Env) -> None:
    declare(env)
    put(env, MCP, entries_file({"orqlet-docs": {"type": "sse", "url": ATLASSIAN}}))


def _with_secrets(env: Env) -> None:
    declare(env)
    put(env, MCP, entries_file({"orqlet-docs": ENTRY, "team": {"env": {"NAME": TOKEN}}}))
    put(env, CURSOR, entries_file({"orqlet-x": ENTRY}))


def _link_and_codex(env: Env) -> None:
    declare(env)
    env.project.add_symlink(MCP)
    put(env, CODEX, f'GITHUB = "{TOKEN}"\n')


def _no_declaration_but_a_name(env: Env) -> None:
    put(env, MCP, GOOD)


def _no_declaration_and_a_link(env: Env) -> None:
    env.project.add_symlink(MCP)


def _bad_declaration(env: Env) -> None:
    declare(env, b"{{{ not yaml")


SCENARIOS = {
    "clean": _clean,
    "differing": _differing,
    "secrets-and-an-undeclared-entry": _with_secrets,
    "link-and-a-token-in-toml": _link_and_codex,
    "no-declaration-but-an-orqlet-name": _no_declaration_but_a_name,
    "no-declaration-and-a-link": _no_declaration_and_a_link,
    "invalid-declaration": _bad_declaration,
}


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
@pytest.mark.parametrize("name", list(SCENARIOS), ids=list(SCENARIOS))
def test_doctor_and_sync_report_what_integration_findings_reports(command: Any, name: str) -> None:
    """AC-7. expected_behavior_source: AC-7 ("doctor and sync both run integration_findings"),
    ADR-003 decision 6 ("`doctor` and `sync` call `integration_findings` from `_diagnose` outside
    its `full` branch, so both run it") and ADR-003 consequences ("One reader means `doctor`,
    `validate` and `upgrade` cannot disagree about what is valid")."""
    env = initialised()
    SCENARIOS[name](env)
    expected = signature_of(integration_findings(env.project, LOADER, DECLARATION_PATH))
    assert expected

    result = command(env)

    assert signature_of(result.findings) == expected


@pytest.mark.parametrize("name", list(SCENARIOS), ids=list(SCENARIOS))
def test_the_command_and_doctor_agree_on_the_errors(name: str) -> None:
    """AC-7. expected_behavior_source: ADR-003 consequences ("`doctor`, `validate` and `upgrade`
    cannot disagree about what is valid") and decision 6 (exit 3 and exit 5 come from one
    reader)."""
    env = initialised()
    SCENARIOS[name](env)
    services = ValidateServices(project=env.project, vcs=FakeVcs(), loader=LOADER, workflow=PINNED)
    command_result = validate_integrations(services, DECLARATION_PATH)

    result = diagnose(env)

    assert codes(errors(in_family(result.findings))) == codes(command_result.errors)


def test_sync_runs_the_check_outside_the_full_branch_of_the_diagnosis() -> None:
    """AC-7. expected_behavior_source: AC-7 ("doctor and sync both run integration_findings, outside
    the full branch of _diagnose") and plan P-3 file operation on diagnose.py: `sync` prints the
    notes of its own branch (ORQ-I201) and none of the full branch (ORQ-I200), and has the findings
    of the integration check."""
    env = initialised()
    _differing(env)

    result = synchronise(env)

    assert "ORQ-I201" in codes(result.findings)
    assert "ORQ-I200" not in codes(result.findings)
    assert DIFFERS in codes(result.findings)


def test_doctor_runs_the_check_next_to_the_checks_of_its_full_branch() -> None:
    """AC-7. expected_behavior_source: AC-7 and plan P-3 file operation on diagnose.py: `doctor` is
    the full branch, and the integration check is one of its findings, once."""
    env = initialised()
    _differing(env)

    result = diagnose(env)

    assert "ORQ-I200" in codes(result.findings)
    assert len(with_code(result.findings, DIFFERS)) == 1


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
def test_the_check_writes_nothing(command: Any) -> None:
    """AC-7. expected_behavior_source: the module docstring of diagnose.py ("Nothing here writes")
    and ADR-002 decision 6 (the validator never writes)."""
    env = initialised()
    _with_secrets(env)
    before = tree(env.project)

    command(env)

    assert tree(env.project) == before


# --- without a declaration, an orqlet- name is a warning ------------------------------------------

NAMED: dict[str, tuple[str, bytes | str]] = {
    "claude-code": (MCP, entries_file({"orqlet-docs": ENTRY})),
    "claude-code-in-capitals": (MCP, entries_file({"ORQLET-DOCS": ENTRY})),
    "cursor": (CURSOR, entries_file({"orqlet-docs": ENTRY})),
    "codex": (CODEX, '[mcp_servers.orqlet-docs]\nurl = "https://x.example.com/mcp"\n'),
    "text-in-a-value": (MCP, entries_file({"team": {"note": "see orqlet-docs"}})),
}


@pytest.mark.parametrize("name", list(NAMED), ids=list(NAMED))
def test_without_a_declaration_a_name_in_an_mcp_file_is_a_warning_in_doctor_and_sync(
    name: str,
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("doctor and sync print the warning and exit 1 on it"),
    plan P-3 objective (ORQ-W530) and ADR-002 decision 11 ("When the declaration is absent and an
    MCP file of any client holds the text `orqlet-` in any letter case ... `doctor` and `sync` print
    a warning that says nothing was checked and why; the signal does not depend on the lock")."""
    path, content = NAMED[name]
    env = initialised()
    put(env, path, content)

    for command in (diagnose, synchronise):
        result = command(env)

        (warning,) = with_code(result.findings, NOT_CHECKED)
        assert warning.severity is Severity.WARNING
        assert errors(in_family(result.findings)) == []


def test_the_warning_makes_sync_exit_1_and_nothing_else_changes() -> None:
    """AC-6. expected_behavior_source: AC-6 ("doctor and sync print the warning and exit 1 on it")
    and ADR-002 decision 11 ("A warning makes `doctor` exit 1, like the other warnings"). `sync`
    exits 0 on a fresh setup, so the exit code of 1 is the warning's."""
    env = initialised()
    assert exit_code_of(synchronise(env)) == 0
    put(env, MCP, GOOD)

    result = synchronise(env)

    assert exit_code_of(result) == 1
    assert NOT_CHECKED in codes(result.findings)


def test_the_warning_is_not_an_error_of_doctor() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 11 ("A warning makes `doctor` exit 1, like
    the other warnings. So deleting the declaration is visible while an `orqlet-` name remains,
    but it is not blocked")."""
    env = initialised()
    put(env, MCP, GOOD)

    result = diagnose(env)

    assert NOT_CHECKED in codes(result.findings)
    assert exit_code_of(result) == 1


def test_the_signal_does_not_depend_on_the_lock() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 11 ("the signal does not depend on the lock,
    which forgets a seeded file once nothing is wanted for it") and ADR-003 context (the lock
    forgets a seeded file): the file is not in the lock, and the warning is printed."""
    env = initialised()
    put(env, MCP, GOOD)
    assert (
        MCP
        not in env.project.read_bytes(CanonicalPath.parse(".orqlet/generated.lock.yaml")).decode()
    )

    assert NOT_CHECKED in codes(diagnose(env).findings)


NOT_NAMED: dict[str, dict[str, bytes | str]] = {
    "other-servers": {MCP: entries_file({"team": ENTRY})},
    "a-credential-and-closed-keys-in-other-entries": {
        MCP: entries_file(
            {"team": {"headersHelper": "tool", "args": ["${HOME}"], "env": {"NAME": TOKEN}}}
        )
    },
    "a-token-in-the-file-of-codex": {CODEX: f'GITHUB = "{TOKEN}"\n'},
    "a-file-that-is-no-json": {MCP: b"{{{ not json"},
    "valid-json-of-the-wrong-shape": {CURSOR: b"[]"},
}


@pytest.mark.parametrize("name", list(NOT_NAMED), ids=list(NOT_NAMED))
def test_without_a_declaration_and_without_such_a_name_doctor_and_sync_print_nothing(
    name: str,
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("doctor and sync ... print nothing for a project
    without such a name"), ADR-002 decision 8 and ADR-003 consequences ("A project with no
    declaration is unchanged"): the findings and the exit codes are those of the same setup without
    the file."""
    env = initialised()
    before = {"doctor": diagnose(env), "sync": synchronise(env)}
    for path, content in NOT_NAMED[name].items():
        put(env, path, content)

    after = {"doctor": diagnose(env), "sync": synchronise(env)}

    for command in before:
        assert sorted(f.code for f in after[command].findings) == sorted(
            f.code for f in before[command].findings
        )
        assert exit_code_of(after[command]) == exit_code_of(before[command])


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
def test_without_a_declaration_a_link_is_a_note_and_changes_no_exit_code(command: Any) -> None:
    """AC-6. expected_behavior_source: AC-6 ("one information finding I533 for a file that cannot be
    read, with no error") and ADR-002 decision 8 ("one information finding, which does not change
    the exit code")."""
    env = initialised()
    baseline = exit_code_of(command(env))
    env.project.add_symlink(MCP)

    result = command(env)

    assert len(with_code(result.findings, NOT_READ)) == 1
    assert errors(in_family(result.findings)) == []
    assert exit_code_of(result) == baseline


def test_the_warning_and_the_notes_show_no_name_of_the_file() -> None:
    """AC-2. expected_behavior_source: AC-2 ("No message, finding or exit text of the reader or the
    validator holds a credential-shaped value or a raw key") and ADR-002 decision 9, through
    `doctor` and `sync`."""
    env = initialised()
    put(env, MCP, entries_file({f"orqlet-{MARKER}": ENTRY, TOKEN: ENTRY}))
    env.project.add_symlink(CURSOR)

    for command in (diagnose, synchronise):
        result = command(env)

        assert NOT_CHECKED in codes(result.findings)
        assert not leaks(shown(result.findings), MARKER)
        assert not leaks(shown(result.findings), TOKEN)


def test_a_secret_in_an_mcp_file_is_not_shown_by_doctor_or_sync_with_a_declaration() -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-002 decision 9, through `doctor` and `sync` with
    a declaration: a secret as the name of an entry, a key and a value."""
    env = initialised()
    declare(env)
    put(
        env,
        MCP,
        entries_file(
            {
                "orqlet-docs": {**ENTRY, MARKER: 1},
                TOKEN: {"env": {OPAQUE: TOKEN}},
                f"orqlet-{MARKER}": ENTRY,
            }
        ),
    )

    for command in (diagnose, synchronise):
        result = command(env)

        assert errors(in_family(result.findings))
        for secret in (TOKEN, OPAQUE, MARKER):
            assert not leaks(shown(result.findings), secret)


# --- an uninitialised repository ------------------------------------------------------------------


@pytest.mark.parametrize("command", [diagnose, synchronise], ids=["doctor", "sync"])
@pytest.mark.parametrize("with_files", [False, True], ids=["nothing", "declaration-and-file"])
def test_an_uninitialised_repository_behaves_as_for_the_other_checks(
    command: Any, with_files: bool
) -> None:
    """AC-7. expected_behavior_source: AC-7 ("an uninitialised repository behaves as for their other
    checks") and ADR-003 decision 6 ("they load the installation like their other checks, so they
    need an initialised repository"): `doctor` and `sync` refuse with the same exception whether
    or not a declaration is there (the command maps it to exit 3 and ORQ-E130)."""
    env = uninitialised()
    if with_files:
        declare(env)
        put(env, MCP, GOOD)

    with pytest.raises(NotInitialised):
        command(env)


def test_the_command_needs_no_installed_profile() -> None:
    """AC-7. expected_behavior_source: AC-7 ("validate integrations needs no installed profile") and
    ADR-002 decision 11 ("It works without an installed profile; it reads only the declaration and
    the MCP files")."""
    env = uninitialised()
    declare(env)
    put(env, MCP, GOOD)
    services = ValidateServices(project=env.project, vcs=FakeVcs(), loader=LOADER, workflow=PINNED)

    result = validate_integrations(services, DECLARATION_PATH)

    assert result.verdict is Verdict.PASS
    assert integration_findings(env.project, LOADER, DECLARATION_PATH)


# --- AC-10: the public names of the module --------------------------------------------------------


def test_the_hook_adds_no_public_name_to_diagnose() -> None:
    """AC-10. expected_behavior_source: AC-10 ("every other new name of the new modules starts with
    an underscore"), the component view ("In every module that this change edits, the only public
    names added are the ones listed below": none for `diagnose.py`) and EC-16."""
    import orqlet.application.usecases.diagnose as module

    assert module.__file__ is not None
    api = extract_module_api(Path(module.__file__).read_text(encoding="utf-8"))

    assert api.errors == ()
    assert api.manual == ()
    assert frozenset(api.symbols) == BASE_PUBLIC_NAMES
