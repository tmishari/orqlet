"""`orqlet resources add | update | remove | attach | list` through the real command line, on real
temporary directories and a real Git repository (task team-conventions-resources, phase P-4).

Every test cites its `expected_behavior_source`. ADR-002 is the file `adr-002-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-8 are the acceptance criteria of phase P-4 in
docs/design/team-conventions-resources/plan.yaml. "The interface decision" is the reading of the
plan author that the Tester of phase P-4 was given, because the ADRs do not spell it out:

- `orqlet resources add URL --id ID --title T --kind K --note N [--access public|login]
  [--path GLOB]... [--tool NAME] [--version V] [--root DIR] [--yes] [--dry-run] [--json]`;
  `update ID` with the same options for the fields that change and `--url`; `remove ID`;
  `attach ID --form copy|summary --ttl-days N`; `list [--uncovered] [--root] [--json]`;
- exit codes through `simple_exit`, as `profile answer` has them: 0 applied or previewed, 3
  refused, 4 needs-input (no `--yes` and no terminal; the attach of a login entry without a
  terminal, also with `--yes`);
- the envelope is `orqlet.cli-result/v1` with the command name as in `IMPLEMENTED_COMMANDS`;
  `data` of an edit command holds `status`, `change_id`, `writes` (a list of `{path, kind}`) and
  `notes`; the human text of an applied change names the next step `orqlet upgrade`; `data` of
  `list --json` is exactly `{"resources": [rows of ADR-002 decision 7], "uncovered": [names]}`;
- the human text of `list` shows one line for each entry with the id, kind, access, host and
  title, and with `--uncovered` the uncovered names; every value that comes from the repository is
  escaped by `printable`, so a hostile title, note, id or glob (ESC, a leading double colon,
  U+202E) never reaches standard output or standard error raw.

These tests were written first, by the Tester of phase P-4, before the commands existed. The
project is initialised once for the module with the real `init` command and copied for each test.
Git is used for real, with no hooks and no network (the suite runs with sockets disabled).
Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message, and the layout of the human text beyond what is said above;
- the exit code for a `--form` that is not `copy` or `summary` and for a `--ttl-days` outside 1 to
  365 (the use case refuses them with exit 3; the command line parser may refuse them first with
  exit 2): only that the exit code is not 0 and nothing is written;
- the exit code of `list` for an invalid registry (only that no row is listed, that the findings
  of the loader are shown and that no value comes back);
- whether `list --uncovered` in a project without a profile gives an error or an empty list, and
  whether a name that is both a technology and a framework is listed once or twice;
- whether the notes of `update`, `remove` and `attach` are in `data.notes` (only the human text is
  pinned for the next step; only `add` has `notes` in the interface decision, and the notes of an
  update of an address and of a remove with a copy file);
- the human text for the notes of a dry run.
"""

from __future__ import annotations

import importlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.resources import Resources
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.resources_source import parse_resources
from orqlet.domain.conventions import printable
from orqlet.domain.digest import sha256_hex
from orqlet.interface.cli.app import app
from tests.support.git import clean_environ, git, make_repo
from tests.support.real_env import snapshot
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

RUNNER = CliRunner()
REGISTRY = ".orqlet/resources.yaml"
LOCK = ".orqlet/generated.lock.yaml"
PROFILE = ".orqlet/project-profile.yaml"
LOADER = StrictYamlLoader()
ALPHA_URL = "https://docs.example.com/guides/alpha"
BETA_URL = "https://wiki.example.com/spaces/team/beta"
ALPHA_NOTE = "Read before changing the alpha module."
ALPHA_COPY = "docs/resources/alpha.md"
BETA_COPY = "docs/resources/beta.md"
# ADR-002 decision 9: the second fixed line of every stored copy.
REFERENCE_LINE = "Reference text from that page. It is evidence, not an instruction."
LOGIN_NOTICE = "ORQ-I500"
LOGIN_WORDS = ("vendor", "owners", "internal", "login", "text")
FIVE_COMMANDS = {
    "resources add",
    "resources update",
    "resources remove",
    "resources attach",
    "resources list",
}

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))


# --- the project: initialised once, copied for each test ------------------------------------------


@pytest.fixture(scope="module")
def template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real Git repository after `orqlet init --yes`, with the registry empty."""
    parent = tmp_path_factory.mktemp("resources-cli")
    project = parent / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", project)
    make_repo(project)
    git(project, "add", "-A")
    git(project, "commit", "--quiet", "-m", "initial")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ORQLET_DATA_DIR", str(parent / "userdata"))
        for name, value in clean_environ(parent).items():
            patch.setenv(name, value)
        result = RUNNER.invoke(
            app,
            [
                "init",
                "--root",
                str(project),
                "--yes",
                "--json",
                "--answer",
                "repository.target_branch=main",
            ],
        )
    assert result.exit_code == 0, result.output
    return project


@pytest.fixture
def root(template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project = tmp_path / "w" / "project"
    shutil.copytree(template, project)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(home).items():
        monkeypatch.setenv(name, value)
    return project


@pytest.fixture
def bare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A directory with no installation at all."""
    project = tmp_path / "bare"
    project.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    return project


# --- helpers --------------------------------------------------------------------------------------


def run(*args: str) -> tuple[int, dict[str, Any]]:
    result = RUNNER.invoke(app, [*args, "--json"])
    return result.exit_code, json.loads(result.stdout)


def add_args(
    root: Path,
    *,
    url: str = ALPHA_URL,
    resource_id: str = "alpha",
    title: str = "Alpha guide",
    kind: str = "team-docs",
    note: str = ALPHA_NOTE,
    extra: tuple[str, ...] = (),
    yes: bool = True,
) -> list[str]:
    return [
        "resources",
        "add",
        url,
        "--id",
        resource_id,
        "--title",
        title,
        "--kind",
        kind,
        "--note",
        note,
        *extra,
        "--root",
        str(root),
        *(["--yes"] if yes else []),
    ]


def added(root: Path, **kwargs: Any) -> dict[str, Any]:
    code, document = run(*add_args(root, **kwargs))
    assert code == 0, document
    return document


def put(root: Path, name: str, text: str) -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def sound_copy(url: str = ALPHA_URL) -> str:
    return f"Source: {url}\n{REFERENCE_LINE}\n\nNotes taken from the page.\n"


def registry_on_disk(root: Path) -> Resources:
    resources, findings = parse_resources(LOADER, (root / REGISTRY).read_bytes(), REGISTRY)
    assert resources is not None, findings
    return resources


def ids_on_disk(root: Path) -> list[str]:
    return [item.id for item in registry_on_disk(root).resources]


def codes(document: dict[str, Any]) -> set[str]:
    return {finding["code"] for finding in document["findings"]}


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or `width` characters of it in a row (any letter case)."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def rewrite_profile(root: Path, technologies: list[str], frameworks: list[str]) -> None:
    """The profile of the project with the technologies and frameworks that a test names."""
    path = root / PROFILE
    document = LOADER.load(path.read_bytes(), source=PROFILE)
    assert isinstance(document, dict)
    document["technologies"] = [
        {"kind": "other", "name": name, "scope": ".", "source": "maintainer"}
        for name in technologies
    ]
    document["facts"]["frameworks"] = [
        {"name": name, "value": name, "answered_by": "maintainer"} for name in frameworks
    ]
    path.write_text(json.dumps(document), encoding="utf-8")


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


# --- add ------------------------------------------------------------------------------------------


def test_add_with_yes_applies_and_prints_the_envelope(root: Path) -> None:
    """AC-1. expected_behavior_source: AC-1 ("resources add writes the entry in order of id, records
    the registry and the lock in one journalled change, prints the next step orqlet upgrade") and
    the interface decision (exit 0; the envelope `orqlet.cli-result/v1`; `data` holds `status`,
    `change_id`, `writes` and `notes`)."""
    before = snapshot(root)

    code, document = run(*add_args(root))

    assert code == 0, document
    assert document["schema"] == "orqlet.cli-result/v1"
    assert document["command"] == "resources add"
    assert document["ok"] is True
    data = document["data"]
    assert data["status"] == "applied"
    assert isinstance(data["change_id"], str)
    assert {(item["path"], item["kind"]) for item in data["writes"]} == {
        (REGISTRY, "update"),
        (LOCK, "update"),
    }
    assert any("orqlet upgrade" in note for note in data["notes"])
    assert ids_on_disk(root) == ["alpha"]
    after = snapshot(root)
    assert {
        name for name in before.keys() | after.keys() if before.get(name) != after.get(name)
    } == {
        REGISTRY,
        LOCK,
    }


def test_add_prints_the_next_step_in_the_human_text(root: Path) -> None:
    """AC-1. expected_behavior_source: AC-1 ("prints the next step orqlet upgrade")."""
    result = RUNNER.invoke(app, add_args(root))

    assert result.exit_code == 0, result.output
    assert "orqlet upgrade" in result.output


def test_add_keeps_the_entries_in_order_of_id(root: Path) -> None:
    """AC-1. expected_behavior_source: AC-1 ("writes the entry in order of id") and ADR-002
    decision 1."""
    added(root, resource_id="zeta", url="https://docs.example.com/zeta")
    added(root, resource_id="alpha", url="https://docs.example.com/alpha")

    assert ids_on_disk(root) == ["alpha", "zeta"]


def test_add_stores_every_option(root: Path) -> None:
    """AC-1. expected_behavior_source: the interface decision (`--access`, `--path` repeatable,
    `--tool`, `--version`) and ADR-002 decisions 1 and 7."""
    code, document = run(
        *add_args(
            root,
            resource_id="fastapi-docs",
            kind="tool-docs",
            extra=(
                "--access",
                "public",
                "--path",
                "src/api/**/*.py",
                "--path",
                "tests/api/**/*.py",
                "--tool",
                "FastAPI",
                "--version",
                "0.115",
            ),
        )
    )

    assert code == 0, document
    (found,) = registry_on_disk(root).resources
    assert (found.tool, found.version, found.access) == ("FastAPI", "0.115", "public")
    assert found.applies_to is not None
    assert found.applies_to.paths == ("src/api/**/*.py", "tests/api/**/*.py")


def test_add_is_public_unless_it_is_told_otherwise(root: Path) -> None:
    """AC-1. expected_behavior_source: the interface decision (`--access public|login (default
    public)`)."""
    added(root)

    assert registry_on_disk(root).resources[0].access == "public"


def test_add_with_dry_run_previews_and_writes_nothing(root: Path) -> None:
    """AC-1. expected_behavior_source: the interface decision (0 for applied or previewed;
    `--dry-run` writes nothing)."""
    before = snapshot(root)

    code, document = run(*add_args(root, extra=("--dry-run",)))

    assert code == 0, document
    assert document["data"]["status"] == "previewed"
    assert document["data"]["change_id"] is None
    assert {item["path"] for item in document["data"]["writes"]} == {REGISTRY, LOCK}
    assert snapshot(root) == before


def test_add_without_yes_and_without_a_terminal_exits_4_and_writes_nothing(root: Path) -> None:
    """AC-1. expected_behavior_source: the interface decision ("4 needs-input (no --yes and no
    terminal)") and ORQ-E115 as `profile answer` says it."""
    before = snapshot(root)

    code, document = run(*add_args(root, yes=False))

    assert code == 4
    assert document["ok"] is False
    assert document["data"]["status"] == "needs-input"
    assert "ORQ-E115" in codes(document)
    assert snapshot(root) == before


REFUSED_ADDS: dict[str, dict[str, Any]] = {
    "address-that-is-not-https": {"url": "http://docs.example.com/alpha"},
    "address-with-a-fragment": {"url": "https://docs.example.com/alpha#intro"},
    "address-with-a-credential-in-its-query": {
        "url": f"https://docs.example.com/guide?token={TOKEN}"
    },
    "id-with-capitals": {"resource_id": "Alpha"},
    "note-with-a-backtick": {"note": "run `make` first"},
    "title-of-a-link": {"title": f"[{OPAQUE}](x)"},
    "glob-that-is-absolute": {"extra": ("--path", "/abs/*.py")},
    "tool-on-a-kind-that-is-not-tool-docs": {"extra": ("--tool", "FastAPI")},
    "kind-outside-the-list": {"kind": "wiki"},
}


@pytest.mark.parametrize("name", list(REFUSED_ADDS), ids=list(REFUSED_ADDS))
def test_an_add_that_a_rule_refuses_exits_3_with_e509_and_shows_nothing_that_was_typed(
    root: Path, name: str
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("is refused (exit 3, ORQ-E509) for ... an invalid
    address, text or glob, or a tool on a kind that is not tool-docs"), ORQLET-SEC-003 and ADR-002
    decision 10 (no value that was typed comes back in a message, standard output or standard
    error)."""
    before = snapshot(root)

    result = RUNNER.invoke(app, [*add_args(root, **REFUSED_ADDS[name]), "--json"])

    assert result.exit_code == 3, result.output
    document = json.loads(result.stdout)
    assert document["ok"] is False
    assert document["data"]["status"] == "refused"
    assert "ORQ-E509" in codes(document)
    assert snapshot(root) == before
    for secret in (TOKEN, OPAQUE):
        assert not leaks(result.stdout, secret)
        assert not leaks(result.stderr, secret)


def test_an_add_of_an_id_that_is_already_there_exits_3_with_e509(root: Path) -> None:
    """AC-1. expected_behavior_source: AC-1 ("is refused (exit 3, ORQ-E509) for a repeated id")."""
    added(root)
    before = snapshot(root)

    code, document = run(*add_args(root, url="https://docs.example.com/other"))

    assert code == 3
    assert "ORQ-E509" in codes(document)
    assert snapshot(root) == before


def test_an_add_of_a_hostile_value_never_prints_it_raw(root: Path) -> None:
    """AC-4. expected_behavior_source: component.md rule 5 ("Every echo of text from the repository
    ... goes through `printable`") and the interface decision (an ESC or U+202E must not reach
    standard output raw). The note and the id are refused by the contract."""
    note = "a\x1b[2Jb"
    resource_id = "x\u202ey"

    human = RUNNER.invoke(app, add_args(root, note=note, resource_id=resource_id))
    machine = RUNNER.invoke(app, [*add_args(root, note=note, resource_id=resource_id), "--json"])

    for result in (human, machine):
        assert result.exit_code == 3, result.output
        for text in (result.stdout, result.stderr):
            assert "\x1b" not in text
            assert "\u202e" not in text


def test_an_add_with_access_login_prints_the_notice_about_the_model_vendor(root: Path) -> None:
    """AC-7. expected_behavior_source: AC-7 ("resources add with --access login prints ORQ-I500,
    which says that page text goes to the client's model vendor and that using the login route for
    internal content is an owners' decision"), EC-47 and ADR-001 consequences. The wording is not
    pinned: the message holds the stable words of those sources."""
    args = add_args(root, url=BETA_URL, resource_id="beta", extra=("--access", "login"))

    code, document = run(*args)
    human = RUNNER.invoke(
        app, add_args(root, url=BETA_URL, resource_id="gamma", extra=("--access", "login"))
    )

    assert code == 0, document
    (notice,) = [f for f in document["findings"] if f["code"] == LOGIN_NOTICE]
    assert notice["severity"] == "info"
    assert all(word in notice["message"].lower() for word in LOGIN_WORDS)
    assert human.exit_code == 0, human.output
    assert LOGIN_NOTICE in human.output


def test_an_add_with_access_public_prints_no_notice(root: Path) -> None:
    """AC-7. expected_behavior_source: AC-7 (the notice is for `--access login`)."""
    document = added(root)

    assert LOGIN_NOTICE not in codes(document)


def test_a_rollback_undoes_an_add(root: Path) -> None:
    """AC-1. expected_behavior_source: ORQLET-SAFE-001 and the interface decision (the change is
    journalled, so `rollback <change_id>` restores the earlier registry and lock)."""
    before = snapshot(root)
    change_id = added(root)["data"]["change_id"]

    code, undone = run("rollback", change_id, "--root", str(root), "--yes")

    assert code == 0, undone
    assert snapshot(root) == before


# --- update ---------------------------------------------------------------------------------------


def test_update_changes_only_the_fields_that_are_given(root: Path) -> None:
    """AC-2. expected_behavior_source: AC-2 ("resources update changes only the fields that are
    given") and the interface decision (`update ID` with the same options)."""
    added(root, kind="tool-docs", extra=("--tool", "Celery", "--path", "src/tasks/**/*.py"))
    before = registry_on_disk(root).resources[0]

    code, document = run(
        "resources", "update", "alpha", "--title", "Alpha, revised", "--root", str(root), "--yes"
    )

    assert code == 0, document
    assert document["command"] == "resources update"
    assert document["data"]["status"] == "applied"
    after = registry_on_disk(root).resources[0]
    assert after.title == "Alpha, revised"
    assert after.model_copy(update={"title": before.title}) == before


def test_update_of_an_id_that_is_not_there_exits_3_and_writes_nothing(root: Path) -> None:
    """AC-2. expected_behavior_source: AC-2 ("refuses an id change") and the interface decision (3
    for a builder refusal)."""
    added(root)
    before = snapshot(root)

    code, document = run(
        "resources", "update", "gamma", "--title", "x", "--root", str(root), "--yes"
    )

    assert code == 3
    assert "ORQ-E509" in codes(document)
    assert snapshot(root) == before


def test_update_of_the_address_keeps_the_copy_record_and_says_the_source_line_is_stale(
    root: Path,
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("keeps the stored-copy record when the address changes
    while printing that the Source line no longer matches") and the interface decision (`data.notes`
    names `docs/resources/<id>.md`)."""
    added(root)
    put(root, ALPHA_COPY, sound_copy())
    attached, _ = run(
        "resources",
        "attach",
        "alpha",
        "--form",
        "copy",
        "--ttl-days",
        "30",
        "--root",
        str(root),
        "--yes",
    )
    assert attached == 0
    record = registry_on_disk(root).resources[0].stored_copy
    assert record is not None

    code, document = run(
        "resources",
        "update",
        "alpha",
        "--url",
        "https://docs.example.com/moved",
        "--root",
        str(root),
        "--yes",
    )

    assert code == 0, document
    assert registry_on_disk(root).resources[0].stored_copy == record
    text = " ".join(document["data"]["notes"])
    assert ALPHA_COPY in text
    assert "Source" in text


# --- remove ---------------------------------------------------------------------------------------


def test_remove_deletes_the_entry_keeps_the_copy_and_says_who_deletes_it(root: Path) -> None:
    """AC-2. expected_behavior_source: AC-2 ("resources remove deletes the entry, prints that a
    kept copy must be deleted by the person"), ADR-002 decision 7 and EC-64 (Orqlet never deletes a
    copy)."""
    added(root)
    put(root, ALPHA_COPY, sound_copy())

    code, document = run("resources", "remove", "alpha", "--root", str(root), "--yes")

    assert code == 0, document
    assert document["command"] == "resources remove"
    assert ids_on_disk(root) == []
    assert (root / ALPHA_COPY).read_text(encoding="utf-8") == sound_copy()
    text = " ".join(document["data"]["notes"])
    assert ALPHA_COPY in text
    assert "delete" in text.lower()


def test_remove_of_an_id_that_is_not_there_exits_3(root: Path) -> None:
    """AC-2. expected_behavior_source: the interface decision (3 for a builder refusal)."""
    before = snapshot(root)

    code, document = run("resources", "remove", "alpha", "--root", str(root), "--yes")

    assert code == 3
    assert "ORQ-E509" in codes(document)
    assert snapshot(root) == before


def test_after_a_remove_an_upgrade_and_doctor_find_nothing_wrong(root: Path) -> None:
    """AC-2. expected_behavior_source: AC-2 ("after upgrade ... doctor is clean") and the interface
    decision (nothing is rendered in this phase, so the check is that nothing breaks and the copy
    file is still there)."""
    added(root)
    put(root, ALPHA_COPY, sound_copy())
    run(
        "resources",
        "attach",
        "alpha",
        "--form",
        "copy",
        "--ttl-days",
        "30",
        "--root",
        str(root),
        "--yes",
    )
    run("resources", "remove", "alpha", "--root", str(root), "--yes")

    upgrade_code, upgraded = run("upgrade", "--root", str(root), "--yes")
    doctor_code, diagnosis = run("doctor", "--root", str(root))

    assert upgrade_code == 0, upgraded
    assert not [f for f in diagnosis["findings"] if f["severity"] == "error"], diagnosis
    assert doctor_code in {0, 1}  # warnings (a draft profile) are not errors
    assert (root / ALPHA_COPY).read_text(encoding="utf-8") == sound_copy()


# --- attach ---------------------------------------------------------------------------------------


def attach_args(
    root: Path, resource_id: str = "alpha", form: str = "copy", ttl: str = "30"
) -> list[str]:
    return [
        "resources",
        "attach",
        resource_id,
        "--form",
        form,
        "--ttl-days",
        ttl,
        "--root",
        str(root),
        "--yes",
    ]


def test_attach_records_the_form_the_hash_the_time_and_the_time_to_live(root: Path) -> None:
    """AC-3. expected_behavior_source: AC-3 ("records form, the SHA-256 of the LF-normalised text,
    retrieved_at from the clock and ttl_days") and the interface decision (the command prints the
    usual envelope and exits 0)."""
    added(root)
    text = sound_copy()
    put(root, ALPHA_COPY, text)

    code, document = run(*attach_args(root, ttl="45"))

    assert code == 0, document
    assert document["command"] == "resources attach"
    assert document["data"]["status"] == "applied"
    record = registry_on_disk(root).resources[0].stored_copy
    assert record is not None
    assert (record.form, record.ttl_days) == ("copy", 45)
    assert record.sha256 == sha256_hex(text.encode())
    assert datetime.fromisoformat(record.retrieved_at).tzinfo is not None
    assert (root / ALPHA_COPY).read_text(encoding="utf-8") == text


def test_a_copy_that_was_attached_passes_validate_resources(root: Path) -> None:
    """AC-3. expected_behavior_source: AC-3 ("checks the copy as validate resources does") and plan
    P-3 AC-4 (PASS for a sound copy with its record)."""
    added(root)
    put(root, ALPHA_COPY, sound_copy())
    run(*attach_args(root))

    code, document = run("validate", "resources", "--root", str(root))

    assert code == 0, document
    assert document["data"]["verdict"] == "PASS"


def test_attach_of_a_copy_with_a_credential_exits_3_and_shows_no_part_of_it(root: Path) -> None:
    """AC-3. expected_behavior_source: AC-3 (checks as validate resources does: ORQ-E506), the
    interface decision (3 for a refusal) and ORQLET-SEC-003 (no standard output or standard error
    shows a credential-shaped value)."""
    added(root)
    put(root, ALPHA_COPY, sound_copy() + f"Use {TOKEN} to sign in, then {OPAQUE}.\n")
    before = snapshot(root)

    result = RUNNER.invoke(app, [*attach_args(root), "--json"])

    assert result.exit_code == 3, result.output
    assert "ORQ-E506" in codes(json.loads(result.stdout))
    assert snapshot(root) == before
    for secret in (TOKEN, OPAQUE):
        assert not leaks(result.stdout, secret)
        assert not leaks(result.stderr, secret)


def test_attach_of_a_missing_copy_exits_3_with_e504(root: Path) -> None:
    """AC-3. expected_behavior_source: the interface decision (a missing copy file is refused with
    ORQ-E504)."""
    added(root)
    before = snapshot(root)

    code, document = run(*attach_args(root))

    assert code == 3
    assert "ORQ-E504" in codes(document)
    assert snapshot(root) == before


def test_attach_of_an_unknown_id_exits_3_with_e509(root: Path) -> None:
    """AC-3. expected_behavior_source: the interface decision (an unknown id is refused with
    ORQ-E509)."""
    before = snapshot(root)

    code, document = run(*attach_args(root, resource_id="gamma"))

    assert code == 3
    assert "ORQ-E509" in codes(document)
    assert snapshot(root) == before


@pytest.mark.parametrize(
    ("form", "ttl"),
    [("page", "30"), ("copy", "0"), ("copy", "366"), ("copy", "-1")],
    ids=["unknown-form", "ttl-0", "ttl-366", "ttl-negative"],
)
def test_attach_with_a_form_or_a_time_to_live_outside_the_rules_is_not_applied(
    root: Path, form: str, ttl: str
) -> None:
    """AC-3. expected_behavior_source: the interface decision ("`form` not 'copy' or 'summary' or
    `ttl_days` outside 1..365 -> refused ORQ-E509"). The exit code is not pinned (see the module
    docstring): the command line parser may refuse the value before the use case does."""
    added(root)
    put(root, ALPHA_COPY, sound_copy())
    before = snapshot(root)

    result = RUNNER.invoke(app, attach_args(root, form=form, ttl=ttl))

    assert result.exit_code != 0
    assert snapshot(root) == before


def test_attach_of_a_login_entry_without_a_terminal_exits_4_with_e510_even_with_yes(
    root: Path,
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("for a login entry asks at a terminal also with --yes
    and stops with ORQ-E510 without one") and the interface decision (4 for needs-input)."""
    added(root, url=BETA_URL, resource_id="beta", extra=("--access", "login"))
    put(root, BETA_COPY, sound_copy(BETA_URL))
    before = snapshot(root)

    code, document = run(*attach_args(root, resource_id="beta", form="summary"))

    assert code == 4
    assert document["ok"] is False
    assert document["data"]["status"] == "needs-input"
    assert "ORQ-E510" in codes(document)
    assert snapshot(root) == before


# --- list -----------------------------------------------------------------------------------------


ALPHA_ROW: dict[str, Any] = {
    "id": "alpha",
    "title": "Alpha guide",
    "kind": "team-docs",
    "access": "public",
    "host": "docs.example.com",
    "tool": None,
    "version": None,
    "applies_to": [],
    "stored_copy": None,
}


def test_list_json_is_the_shape_of_adr_002_decision_7(root: Path) -> None:
    """AC-4. expected_behavior_source: AC-4 ("--json prints the shape of ADR-002 decision 7"),
    ADR-002 decision 7 (`{"resources": [{id, title, kind, access, host, tool, version, applies_to,
    stored_copy}], "uncovered": [names]}`) and the interface decision (`data` is exactly that)."""
    added(root)
    added(
        root,
        url=BETA_URL,
        resource_id="beta",
        title="Beta wiki",
        extra=("--access", "login"),
    )

    code, document = run("resources", "list", "--root", str(root))

    assert code == 0, document
    assert document["command"] == "resources list"
    assert set(document["data"]) == {"resources", "uncovered"}
    alpha, beta = document["data"]["resources"]
    assert alpha == ALPHA_ROW
    assert beta == {
        **ALPHA_ROW,
        "id": "beta",
        "title": "Beta wiki",
        "access": "login",
        "host": "wiki.example.com",
    }
    assert document["data"]["uncovered"] == []


def test_list_of_a_registry_with_a_copy_and_a_tool_shows_them(root: Path) -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (`applies_to` the globs, `stored_copy`
    `{form, sha256, retrieved_at, ttl_days}`, `tool` and `version`)."""
    added(
        root,
        resource_id="fastapi-docs",
        kind="tool-docs",
        extra=("--tool", "FastAPI", "--version", "0.115", "--path", "src/api/**/*.py"),
    )
    put(root, "docs/resources/fastapi-docs.md", sound_copy())
    run(*attach_args(root, resource_id="fastapi-docs", ttl="90"))

    code, document = run("resources", "list", "--root", str(root))

    assert code == 0, document
    (row,) = document["data"]["resources"]
    assert (row["tool"], row["version"]) == ("FastAPI", "0.115")
    assert row["applies_to"] == ["src/api/**/*.py"]
    assert set(row["stored_copy"]) == {"form", "sha256", "retrieved_at", "ttl_days"}
    assert (row["stored_copy"]["form"], row["stored_copy"]["ttl_days"]) == ("copy", 90)


def test_list_of_an_empty_registry_is_an_empty_list(root: Path) -> None:
    """AC-4. expected_behavior_source: the interface decision ("a missing registry is an empty list
    with no finding"; an empty one is the same) and ADR-002 decision 7."""
    code, document = run("resources", "list", "--root", str(root))

    assert code == 0, document
    assert document["data"] == {"resources": [], "uncovered": []}
    assert document["findings"] == []


def test_list_in_a_directory_with_no_installation_is_an_empty_list(bare: Path) -> None:
    """AC-4. expected_behavior_source: the interface decision (`list_resources` takes the services
    of the validators, which need no installation; "a missing registry is an empty list with no
    finding")."""
    code, document = run("resources", "list", "--root", str(bare))

    assert code == 0, document
    assert document["data"] == {"resources": [], "uncovered": []}
    assert document["findings"] == []


def test_list_in_human_text_has_one_line_for_each_entry_with_the_host_and_never_the_address(
    root: Path,
) -> None:
    """AC-4. expected_behavior_source: the interface decision ("Human output of list shows each
    entry's id, kind, access, host and title on one line and never the raw address on a line of its
    own with other text") and ADR-002 decisions 7 and 8 (the host is shown separately; the host is
    printed on its own wherever an address is shown). The address may not share a line with other
    text; it may be absent."""
    added(root, title="Alpha guide")
    added(
        root,
        url=BETA_URL,
        resource_id="beta",
        title="Beta wiki",
        kind="api-guidelines",
        extra=("--access", "login"),
    )

    result = RUNNER.invoke(app, ["resources", "list", "--root", str(root)])

    assert result.exit_code == 0, result.output
    lines = result.stdout.splitlines()
    for resource_id, kind, access, host, title in (
        ("alpha", "team-docs", "public", "docs.example.com", "Alpha guide"),
        ("beta", "api-guidelines", "login", "wiki.example.com", "Beta wiki"),
    ):
        found = [
            line
            for line in lines
            if all(token in line for token in (resource_id, kind, access, host, title))
        ]
        assert len(found) == 1, (resource_id, lines)
    for address in (ALPHA_URL, BETA_URL):
        assert all(line.strip() == address for line in lines if address in line)


def test_list_with_an_invalid_registry_shows_the_findings_and_no_row(root: Path) -> None:
    """AC-4. expected_behavior_source: the interface decision ("An invalid registry gives no rows
    and the loader's findings"), ADR-002 decision 10 and ORQLET-SEC-003. The exit code is not
    pinned."""
    bad = {
        "schema": "orqlet.resources/v1",
        "resources": [
            {
                "id": "alpha",
                "title": "Alpha guide",
                "kind": "team-docs",
                "url": f"https://docs.example.com/guide?token={TOKEN}",
                "note": f"use `{OPAQUE}` first",
                "access": "public",
            }
        ],
    }
    (root / REGISTRY).write_text(json.dumps(bad), encoding="utf-8")

    result = RUNNER.invoke(app, ["resources", "list", "--root", str(root), "--json"])

    document = json.loads(result.stdout)
    assert document["data"].get("resources", []) == []
    assert "ORQ-E501" in codes(document)
    for secret in (TOKEN, OPAQUE):
        assert not leaks(result.stdout, secret)
        assert not leaks(result.stderr, secret)


def test_list_uncovered_prints_the_technologies_that_no_entry_names_as_its_tool(root: Path) -> None:
    """AC-4. expected_behavior_source: AC-4 ("--uncovered prints the technologies of the profile
    that no entry covers") and ADR-002 decision 7 (compared after trimming and case folding)."""
    rewrite_profile(root, ["Kafka", "PostgreSQL"], ["FastAPI"])
    added(
        root,
        resource_id="postgres-docs",
        kind="tool-docs",
        url="https://docs.example.com/postgres",
        extra=("--tool", "postgresql"),
    )

    plain_code, plain = run("resources", "list", "--root", str(root))
    code, document = run("resources", "list", "--uncovered", "--root", str(root))
    human = RUNNER.invoke(app, ["resources", "list", "--uncovered", "--root", str(root)])

    assert (plain_code, code) == (0, 0)
    assert plain["data"]["uncovered"] == []
    assert set(document["data"]["uncovered"]) == {"Kafka", "FastAPI"}
    assert human.exit_code == 0, human.output
    assert "Kafka" in human.stdout
    assert "FastAPI" in human.stdout


HOSTILE_TECHNOLOGIES = [
    "Evil\x1b[2Jname",
    "rtl\u202etext",
    "line1\n::warning::injected",
    "ORQ-E999: forged",
    "back\\slash",
]


def test_a_hostile_name_in_the_profile_never_reaches_standard_output_raw(root: Path) -> None:
    """AC-4. expected_behavior_source: AC-4 ("every value from the repository is escaped by
    printable"), the interface decision ("an ESC, U+202E or a newline in a ... value must not
    reach stdout raw") and the docstring of `printable` ("shown after a fixed prefix, never at the
    start of a line"). The profile is a file of the repository; its names can hold anything."""
    rewrite_profile(root, HOSTILE_TECHNOLOGIES, [])

    code, document = run("resources", "list", "--uncovered", "--root", str(root))
    human = RUNNER.invoke(app, ["resources", "list", "--uncovered", "--root", str(root)])

    assert code == 0, document
    assert set(document["data"]["uncovered"]) == {printable(n, 200) for n in HOSTILE_TECHNOLOGIES}
    assert human.exit_code == 0, human.output
    for text in (human.stdout, human.stderr):
        assert "\x1b" not in text
        assert "\u202e" not in text
    for line in human.stdout.splitlines():
        assert not line.startswith("::")
        assert not line.startswith("ORQ-E999")
        assert not line.startswith("injected")


# --- the four edit commands, one after the other --------------------------------------------------

EDITS = ("add", "update", "remove", "attach")


def edit_args(root: Path, name: str) -> list[str]:
    """The arguments of one edit command, without `--yes`, `--dry-run` and `--json`."""
    if name == "add":
        return [
            "resources",
            "add",
            "https://docs.example.com/beta",
            "--id",
            "beta",
            "--title",
            "Beta guide",
            "--kind",
            "team-docs",
            "--note",
            ALPHA_NOTE,
            "--root",
            str(root),
        ]
    if name == "update":
        return ["resources", "update", "alpha", "--title", "Alpha, revised", "--root", str(root)]
    if name == "remove":
        return ["resources", "remove", "alpha", "--root", str(root)]
    return [
        "resources",
        "attach",
        "alpha",
        "--form",
        "copy",
        "--ttl-days",
        "30",
        "--root",
        str(root),
    ]


def prepare(root: Path, name: str) -> None:
    """The state in which the command applies: the entry `alpha`, and its copy for an attach."""
    if name != "add":
        added(root)
    if name == "attach":
        put(root, ALPHA_COPY, sound_copy())


@pytest.mark.parametrize("name", EDITS)
def test_an_applied_command_names_the_next_step_in_its_human_text(root: Path, name: str) -> None:
    """AC-1, AC-2, AC-3. expected_behavior_source: the interface decision ("the human output of an
    applied change names the next step `orqlet upgrade`") and ADR-002 decision 7 ("they ... print
    the next step, `orqlet upgrade`")."""
    prepare(root, name)

    result = RUNNER.invoke(app, [*edit_args(root, name), "--yes"])

    assert result.exit_code == 0, result.output
    assert "orqlet upgrade" in result.stdout


@pytest.mark.parametrize("name", EDITS)
def test_a_dry_run_exits_0_shows_the_two_writes_and_writes_nothing(root: Path, name: str) -> None:
    """AC-1, AC-2, AC-3. expected_behavior_source: the interface decision ("Exit codes through
    simple_exit: 0 for applied and previewed"; `--dry-run`) and ORQLET-SAFE-001."""
    prepare(root, name)
    before = snapshot(root)

    code, document = run(*edit_args(root, name), "--dry-run")

    assert code == 0, document
    assert document["data"]["status"] == "previewed"
    assert document["data"]["change_id"] is None
    assert {item["path"] for item in document["data"]["writes"]} == {REGISTRY, LOCK}
    assert snapshot(root) == before


@pytest.mark.parametrize("name", EDITS)
def test_without_yes_and_without_a_terminal_a_command_exits_4_and_writes_nothing(
    root: Path, name: str
) -> None:
    """AC-1, AC-2, AC-3. expected_behavior_source: the interface decision ("4 for needs-input";
    "without a terminal the status is needs-input with finding ORQ-E115 and nothing is
    written")."""
    prepare(root, name)
    before = snapshot(root)

    code, document = run(*edit_args(root, name))

    assert code == 4, document
    assert document["data"]["status"] == "needs-input"
    assert "ORQ-E115" in codes(document)
    assert snapshot(root) == before


@pytest.mark.parametrize("name", EDITS)
def test_a_rollback_undoes_every_command(root: Path, name: str) -> None:
    """AC-1, AC-2, AC-3, AC-6. expected_behavior_source: the interface decision ("The change is
    journalled ... so `rollback` restores the earlier state") and ORQLET-SAFE-001."""
    prepare(root, name)
    before = snapshot(root)
    code, document = run(*edit_args(root, name), "--yes")
    assert code == 0, document

    code, undone = run("rollback", document["data"]["change_id"], "--root", str(root), "--yes")

    assert code == 0, undone
    assert snapshot(root) == before


# --- hostile values in the repository -------------------------------------------------------------

HOSTILE_ENTRY = {
    "id": "x\u202ey",
    "title": "a\x1b[2Jb",
    "kind": "team-docs",
    "url": ALPHA_URL,
    "note": "::warning::\x1b[2J boom",
    "access": "public",
    "applies_to": {"paths": ["::\x1b*"]},
}


def write_registry(root: Path, *entries: dict[str, Any]) -> None:
    document = {"schema": "orqlet.resources/v1", "resources": list(entries)}
    (root / REGISTRY).write_text(json.dumps(document), encoding="utf-8")


def assert_nothing_raw(*texts: str) -> None:
    for text in texts:
        assert "\x1b" not in text
        assert "\u202e" not in text
        assert not [line for line in text.splitlines() if line.startswith("::")]


@pytest.mark.parametrize(
    "arguments",
    [
        ["resources", "list"],
        ["resources", "list", "--uncovered"],
        ["resources", "remove", "alpha", "--yes"],
        ["resources", "update", "alpha", "--title", "Alpha", "--yes"],
        ["resources", "attach", "alpha", "--form", "copy", "--ttl-days", "30", "--yes"],
    ],
    ids=["list", "list-uncovered", "remove", "update", "attach"],
)
def test_a_hostile_registry_never_reaches_standard_output_or_error_raw(
    root: Path, arguments: list[str]
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("every value from the repository is escaped by
    printable"), the interface decision ("a hostile title, note, id or glob (ESC, a leading `::`,
    U+202E) never reaches stdout or stderr raw") and component.md rule 5. The registry is a file of
    the repository: it can hold anything. The contract refuses these values, so the command
    reports an invalid registry; no value comes back, in text or in JSON."""
    write_registry(root, HOSTILE_ENTRY)

    human = RUNNER.invoke(app, [*arguments, "--root", str(root)])
    machine = RUNNER.invoke(app, [*arguments, "--root", str(root), "--json"])

    for result in (human, machine):
        assert_nothing_raw(result.stdout, result.stderr)
    assert "ORQ-E501" in codes(json.loads(machine.stdout))


@pytest.mark.parametrize("title", ["::warning::boom", "ORQ-E999: forged", "back\\slash"])
def test_a_title_that_looks_like_a_command_is_shown_as_data_in_the_list(
    root: Path, title: str
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("every value from the repository is escaped by
    printable") and component.md rule 5. These titles are valid (ASCII, one line); the human list
    shows an entry on one line that starts with its id, so no line of the output is a workflow
    command or a forged finding, and the JSON row holds the title as `printable` gives it."""
    write_registry(
        root,
        {
            "id": "alpha",
            "title": title,
            "kind": "team-docs",
            "url": ALPHA_URL,
            "note": ALPHA_NOTE,
            "access": "public",
        },
    )

    human = RUNNER.invoke(app, ["resources", "list", "--root", str(root)])
    code, document = run("resources", "list", "--root", str(root))

    assert human.exit_code == 0, human.output
    assert code == 0, document
    for line in human.stdout.splitlines():
        assert not line.startswith(("::", "ORQ-E999"))
    assert document["data"]["resources"][0]["title"] == printable(title, 200)
    assert printable(title, 200) in human.stdout


# --- no installation ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "arguments",
    [
        [
            "add",
            ALPHA_URL,
            "--id",
            "alpha",
            "--title",
            "Alpha",
            "--kind",
            "team-docs",
            "--note",
            ALPHA_NOTE,
        ],
        ["update", "alpha", "--title", "Alpha"],
        ["remove", "alpha"],
        ["attach", "alpha", "--form", "copy", "--ttl-days", "30"],
    ],
    ids=["add", "update", "remove", "attach"],
)
def test_the_edit_commands_say_so_when_there_is_no_installation(
    bare: Path, arguments: list[str]
) -> None:
    """AC-1. expected_behavior_source: the interface decision ("A command run in a directory with no
    installation exits 3 or whatever profile answer does"): `profile answer` and every command
    that needs an installation exit 3 with ORQ-E130 (tests/integration/test_lifecycle_cli.py)."""
    code, document = run("resources", *arguments, "--root", str(bare), "--yes")

    assert code == 3
    assert "ORQ-E130" in codes(document)
    assert list(bare.iterdir()) == []


# --- the commands are part of the application -----------------------------------------------------


def test_the_five_commands_are_listed_as_implemented_and_are_registered() -> None:
    """AC-8. expected_behavior_source: AC-8 ("the equality test between IMPLEMENTED_COMMANDS and the
    application's commands holds") and EC-56 (IMPLEMENTED_COMMANDS gains resources add, resources
    update, resources remove, resources attach and resources list). The equality test itself is in
    test_validate_cli.py and needs no change."""
    assert FIVE_COMMANDS <= IMPLEMENTED_COMMANDS
    assert registered_names(app) >= FIVE_COMMANDS


def test_the_module_of_the_commands_has_one_public_name_and_it_builds_the_group() -> None:
    """AC-8. expected_behavior_source: AC-8 ("every command function and helper of the new module
    is private") and EC-47 (`resources_group() -> typer.Typer`; "every command and helper is
    private")."""
    module = importlib.import_module("orqlet.interface.cli.commands.resources")

    defined = {
        name
        for name, value in vars(module).items()
        if not name.startswith("_") and getattr(value, "__module__", None) == module.__name__
    }

    assert defined == {"resources_group"}
    assert isinstance(module.resources_group(), typer.Typer)


def test_the_resources_group_lists_its_commands_in_its_help() -> None:
    """AC-8. expected_behavior_source: EC-47 (`app.add_typer(resources_group(), name="resources")`)
    and the interface decision (the five commands)."""
    result = RUNNER.invoke(app, ["resources", "--help"])

    assert result.exit_code == 0
    for name in ("add", "update", "remove", "attach", "list"):
        assert name in result.stdout


def test_the_journal_of_an_edit_is_in_the_user_data_folder_and_not_in_the_repository(
    root: Path, tmp_path: Path
) -> None:
    """AC-1. expected_behavior_source: ORQLET-SAFE-001 (a journalled change; the journal and the
    backups are the user's data, never the repository: `wiring.data_directory`)."""
    document = added(root)

    journals = list((tmp_path / "userdata").rglob(f"{document['data']['change_id']}.json"))
    assert len(journals) == 1
    assert not list(root.rglob(f"{document['data']['change_id']}.json"))
