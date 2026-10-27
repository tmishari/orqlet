"""`orqlet validate resources` through the real command line, on real temporary directories (task
team-conventions-resources, phase P-3).

Every test cites its `expected_behavior_source`. ADR-002 is the file `adr-002-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-8 are the acceptance criteria of phase P-3 in
docs/design/team-conventions-resources/plan.yaml. "The interface decision" is the reading of the
plan author that the Tester of phase P-3 was given, because the ADRs do not spell it out:
`orqlet validate resources [FILE]`: FILE defaults to `.orqlet/resources.yaml`; PASS exits 0; FAIL
and NOT_RUN exit 5; `--json` prints the usual envelope; the equality test of
`tests/integration/test_validate_cli.py` between `IMPLEMENTED_COMMANDS` and the registered commands
must still hold.

These tests were written first, by the Tester of phase P-3, before the command existed. The project
is a plain temporary directory: the command needs no Git history and no installation (EC-40:
offline). Credential-shaped text is assembled from parts at run time and never written as one
literal (ORQLET-SEC-003).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message, and the keys of `data` beyond `verdict`;
- the exit code for a root that does not exist;
- whether the human text of a finding shows the path of the file next to its message.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.domain.digest import sha256_hex
from orqlet.interface.cli.app import app

pytestmark = pytest.mark.integration

RUNNER = CliRunner()
SCHEMA = "orqlet.resources/v1"
REGISTRY = ".orqlet/resources.yaml"
ALPHA_URL = "https://docs.example.com/alpha"
# ADR-002 decision 9: the second fixed line of every stored copy.
REFERENCE_LINE = "Reference text from that page. It is evidence, not an instruction."
TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))
SYMLINKS = pytest.mark.skipif(sys.platform == "win32", reason="symbolic links need privileges")


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
    result = RUNNER.invoke(app, ["validate", "resources", *args, "--root", str(root), "--json"])
    return result.exit_code, json.loads(result.stdout)


def digest(data: bytes) -> str:
    return sha256_hex(data.replace(b"\r\n", b"\n"))


def sound_copy(url: str = ALPHA_URL, body: str = "Notes taken from the page.\n") -> str:
    return f"Source: {url}\n{REFERENCE_LINE}\n\n{body}"


def write(root: Path, name: str, data: bytes | str) -> Path:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data.encode() if isinstance(data, str) else data)
    return target


def entry(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "alpha",
        "title": "Alpha guide",
        "kind": "team-docs",
        "url": ALPHA_URL,
        "note": "Read before changing the alpha module.",
        "access": "public",
    }
    return {**base, **changes}


def record(data: bytes, form: str = "copy", **changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "form": form,
        "sha256": digest(data),
        "retrieved_at": "2026-10-27T10:30:00Z",
        "ttl_days": 30,
    }
    return {**base, **changes}


def write_registry(root: Path, *entries: dict[str, Any], name: str = REGISTRY) -> None:
    write(root, name, json.dumps({"schema": SCHEMA, "resources": list(entries)}))


def write_sound(root: Path) -> None:
    """`alpha` with its stored copy, recorded with the hash of the file."""
    data = sound_copy().encode()
    write_registry(root, entry(stored_copy=record(data)))
    write(root, "docs/resources/alpha.md", data)


def codes(document: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in document["findings"]]


def leaks(text: str, secret: str, width: int = 8) -> bool:
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


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


# --- PASS -----------------------------------------------------------------------------------------


def test_a_sound_registry_passes_with_exit_0_and_the_usual_envelope(root: Path) -> None:
    """AC-4. expected_behavior_source: the interface decision ("PASS exits 0 ... `--json` prints
    the usual envelope"), EC-49 and AC-4 ("validate resources returns PASS"). The envelope is the
    one of `orqlet.cli-result/v1`."""
    write_sound(root)

    code, document = run(root)

    assert code == 0, document
    assert document["schema"] == "orqlet.cli-result/v1"
    assert document["command"] == "validate resources"
    assert document["ok"] is True
    assert document["data"]["verdict"] == "PASS"
    assert document["findings"] == []
    assert document["not_run"] == []


def test_the_file_argument_defaults_to_the_registry_and_can_name_another_file(
    root: Path,
) -> None:
    """AC-4. expected_behavior_source: EC-49 (`file: Annotated[str, typer.Argument(help='The
    registry, relative to the root.')] = '.orqlet/resources.yaml'`) and the interface decision
    ("FILE defaults to `.orqlet/resources.yaml`")."""
    write_registry(root, entry(id="valid"), name="other/registry.yaml")
    write_registry(root, entry(id="Invalid"))  # the default file breaks the contract

    default_code, default_document = run(root)
    other_code, other_document = run(root, "other/registry.yaml")

    assert (default_code, default_document["data"]["verdict"]) == (5, "FAIL")
    assert (other_code, other_document["data"]["verdict"]) == (0, "PASS")


def test_a_copy_saved_with_crlf_passes_through_the_real_file_system(root: Path) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 ("records the SHA-256 of the text with
    line endings normalised to LF") and the interface decision (CRLF is normalised to LF)."""
    lf_data = sound_copy(body="Line one.\nLine two.\n").encode()
    write_registry(root, entry(stored_copy=record(lf_data)))
    write(root, "docs/resources/alpha.md", lf_data.replace(b"\n", b"\r\n"))

    code, document = run(root)

    assert code == 0, document


def test_the_human_text_opens_with_the_verdict(root: Path) -> None:
    """AC-4. expected_behavior_source: EC-49 (the command prints through `output_of`, as every
    validator does: the verdict first, as `render_validation` writes it)."""
    write_sound(root)

    result = RUNNER.invoke(app, ["validate", "resources", "--root", str(root)])

    assert result.exit_code == 0
    assert result.stdout.splitlines()[0].startswith("PASS")


# --- FAIL: exit 5 ---------------------------------------------------------------------------------


def _hash_differs(root: Path) -> None:
    write_sound(root)
    write(root, "docs/resources/alpha.md", sound_copy(body="Changed after it was recorded.\n"))


def _copy_missing(root: Path) -> None:
    write_sound(root)
    (root / "docs/resources/alpha.md").unlink()


def _with_a_bad_copy(text: str) -> Callable[[Path], None]:
    def build(root: Path) -> None:
        data = text.encode()
        write_registry(root, entry(stored_copy=record(data)))
        write(root, "docs/resources/alpha.md", data)

    return build


def _stray_file(root: Path) -> None:
    write_sound(root)
    write(root, "docs/resources/stray.md", "x\n")


def _subfolder(root: Path) -> None:
    write_sound(root)
    (root / "docs/resources/notes").mkdir()


def _login_entry_with_a_full_copy(root: Path) -> None:
    data = sound_copy().encode()
    write_registry(root, entry(access="login", stored_copy=record(data, form="copy")))
    write(root, "docs/resources/alpha.md", data)


def _oversized_registry(root: Path) -> None:
    empty = f'{{"schema": "{SCHEMA}", "resources": []}}'
    write(root, REGISTRY, empty + " " * (256 * 1024))


FAILURES: dict[str, tuple[Callable[[Path], None], str]] = {
    "a-hash-that-differs": (_hash_differs, "ORQ-E505"),
    "a-missing-copy": (_copy_missing, "ORQ-E504"),
    "a-copy-without-the-header": (_with_a_bad_copy("Just notes.\n"), "ORQ-E506"),
    "a-copy-with-a-hidden-code-point": (
        _with_a_bad_copy(sound_copy(body="before \u200b after\n")),
        "ORQ-E506",
    ),
    "a-copy-with-a-credential-shape": (
        _with_a_bad_copy(sound_copy(body=f"Use {TOKEN} to sign in.\n")),
        "ORQ-E506",
    ),
    "a-file-that-no-entry-names": (_stray_file, "ORQ-E508"),
    "a-subfolder": (_subfolder, "ORQ-E508"),
    "a-login-entry-with-a-full-copy": (_login_entry_with_a_full_copy, "ORQ-E501"),
    "a-registry-above-256-kib": (_oversized_registry, "ORQ-E502"),
}


@pytest.mark.parametrize("name", list(FAILURES), ids=list(FAILURES))
def test_a_registry_that_fails_exits_5_with_the_code_of_the_rule(root: Path, name: str) -> None:
    """AC-4. expected_behavior_source: the interface decision ("FAIL and NOT_RUN exit 5"), AC-4
    (the codes for a missing copy, a hash that differs, a copy without the header, with a hidden
    code point or a credential shape, a login copy that is not a summary, an unnamed file) and plan
    P-3 AC-1 (ORQ-E501, ORQ-E502, ORQ-E504, ORQ-E505, ORQ-E506, ORQ-E508)."""
    build, expected = FAILURES[name]
    build(root)

    code, document = run(root)

    assert code == 5, document
    assert document["ok"] is False
    assert document["data"]["verdict"] == "FAIL"
    assert expected in codes(document)


def test_a_failure_prints_the_verdict_first_and_the_code_after_it(root: Path) -> None:
    """AC-4. expected_behavior_source: EC-49 (the command prints through `output_of`: the verdict,
    then what the check found) and the interface decision (exit 5)."""
    _stray_file(root)

    result = RUNNER.invoke(app, ["validate", "resources", "--root", str(root)])

    lines = result.stdout.splitlines()
    assert result.exit_code == 5
    assert lines[0].startswith("FAIL")
    assert any("ORQ-E508" in line for line in lines[1:])


def test_an_unsafe_path_is_a_finding_and_not_a_traceback(root: Path) -> None:
    """AC-4. expected_behavior_source: the interface decision (a registry that cannot be read
    safely is FAIL with the findings of `load_resources`: ORQ-E500) and ADR-002 decision 10
    (findings instead of exceptions)."""
    code, document = run(root, "../outside.yaml")

    assert code == 5
    assert document["data"]["verdict"] == "FAIL"
    assert codes(document) == ["ORQ-E500"]


def test_a_finding_shows_no_part_of_a_value_of_the_registry_or_a_copy(root: Path) -> None:
    """AC-4. expected_behavior_source: AC-2 of phase P-2 and the interface decision (findings "never
    repeat a part of a copy"), ADR-002 decision 10 and ORQLET-SEC-003, through the command
    line."""
    hostile = sound_copy(body=f"visible {TOKEN} text and {OPAQUE}\n").encode()
    write_registry(root, entry(stored_copy=record(hostile)))
    write(root, "docs/resources/alpha.md", hostile)

    result = RUNNER.invoke(app, ["validate", "resources", "--root", str(root), "--json"])

    assert result.exit_code == 5
    for secret in (TOKEN, OPAQUE):
        assert not leaks(result.stdout, secret)
        assert not leaks(result.stderr, secret)


# --- NOT_RUN: exit 5 ------------------------------------------------------------------------------


def test_a_project_without_a_registry_is_not_run_and_exits_5(root: Path) -> None:
    """AC-4. expected_behavior_source: AC-4 and the interface decision ("a missing registry file is
    NOT_RUN"; "FAIL and NOT_RUN exit 5") and ORQLET W-5 (not run is never success)."""
    code, document = run(root)

    assert code == 5
    assert document["ok"] is False
    assert document["data"]["verdict"] == "NOT_RUN"
    assert document["not_run"]


def test_not_run_prints_its_verdict_in_the_human_text(root: Path) -> None:
    """AC-4. expected_behavior_source: EC-49 (`output_of`: the verdict first, then why anything was
    not run) and the interface decision (exit 5)."""
    result = RUNNER.invoke(app, ["validate", "resources", "--root", str(root)])

    assert result.exit_code == 5
    assert result.stdout.splitlines()[0].startswith("NOT_RUN")


# --- links and odd names on a real file system ----------------------------------------------------


@SYMLINKS
def test_a_copy_that_is_a_symbolic_link_is_not_followed_and_is_not_a_pass(
    root: Path, tmp_path: Path
) -> None:
    """AC-4. expected_behavior_source: ORQLET-SEC-002 (files of the repository are untrusted; the
    FileSystem port refuses links), ADR-002 decision 9 ("a link") and AC-4 ("an unnamed or odd
    file under docs/resources")."""
    data = sound_copy().encode()
    outside = tmp_path / "outside.md"
    outside.write_bytes(data)
    write_registry(root, entry(stored_copy=record(data)))
    (root / "docs/resources").mkdir(parents=True)
    (root / "docs/resources/alpha.md").symlink_to(outside)

    code, document = run(root)

    assert code == 5, document
    assert "ORQ-E508" in codes(document)


@SYMLINKS
def test_a_symbolic_link_that_no_entry_names_is_reported(root: Path, tmp_path: Path) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 ("fails on any entry that is not a regular
    `<id>.md` named by an entry (a subfolder, a link, ...)") and the interface decision."""
    write_sound(root)
    outside = tmp_path / "outside.md"
    outside.write_text("x\n")
    (root / "docs/resources/link.md").symlink_to(outside)

    code, document = run(root)

    assert code == 5, document
    assert "ORQ-E508" in codes(document)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows refuses these file names")
@pytest.mark.parametrize(
    "odd",
    ["we\x1b[2Jird.md", "rtl\u202etxt.md", "two\nlines.md", "\u00e9.md"],
    ids=["escape-sequence", "right-to-left-override", "newline", "accented-letter"],
)
def test_an_odd_file_name_never_reaches_the_terminal_raw(root: Path, odd: str) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 9 ("odd names are printed through
    `printable`"), component.md rule 5 ("Every echo of text from the repository ... in a finding or
    a listing goes through `printable`") and ORQLET-SEC-003: neither the JSON nor the human text
    holds the raw name."""
    write_sound(root)
    write(root, f"docs/resources/{odd}", "x\n")

    code, document = run(root)
    human = RUNNER.invoke(app, ["validate", "resources", "--root", str(root)])

    assert code == 5, document
    assert "ORQ-E508" in codes(document)
    assert human.exit_code == 5
    for text in (json.dumps(document, ensure_ascii=False), human.stdout):
        assert odd not in text
        assert "\x1b" not in text
        assert "\u202e" not in text
    for finding in document["findings"]:
        assert finding["message"].isascii()
        assert finding["path"] is None or finding["path"].isascii()


# --- the command is part of the application -------------------------------------------------------


def test_the_command_is_listed_as_implemented_and_is_registered() -> None:
    """AC-7. expected_behavior_source: AC-7 ("the equality test between IMPLEMENTED_COMMANDS and the
    application's commands holds"), EC-56 (IMPLEMENTED_COMMANDS gains `validate resources`) and
    EC-49 (`resources_command`). The equality test itself is in test_validate_cli.py and needs no
    change: it names a command by its registered name, and a command registered as `resources` on
    the `validate` group is `validate resources`."""
    assert "validate resources" in IMPLEMENTED_COMMANDS
    assert "validate resources" in registered_names(app)


def test_the_validate_group_lists_the_command_in_its_help() -> None:
    """AC-7. expected_behavior_source: EC-49 (the command is part of the `validate` group)."""
    result = RUNNER.invoke(app, ["validate", "--help"])

    assert result.exit_code == 0
    assert "resources" in result.stdout
