"""`resources add`, `update`, `remove` and `attach` as use cases (task team-conventions-resources,
phase P-4).

Every test cites its `expected_behavior_source`. ADR-001 and ADR-002 are the files `adr-00*.md`
under docs/design/team-conventions-resources/design/, S-9 is a consideration of considerations.md
in the same folder, EC-n are the expected changes of the manifest.yaml next to them, and AC-1 to
AC-8 are the acceptance criteria of phase P-4 in docs/design/team-conventions-resources/plan.yaml.
"The interface decision" is the reading of the plan author that the Tester of phase P-4 was given,
because the ADRs do not spell it out:

1. `orqlet.application.usecases.resources_edit` gains `CopySpec` (a frozen dataclass with the
   required fields `id`, `form`, `ttl_days`), `ResourcesEditResult` (a frozen dataclass: `status`,
   `findings = ()`, `plan = None`, `change_id = None`, `resources = None`, `notes = ()`) and the
   four functions `add_resource(services, spec, assume_yes, dry_run)`, `update_resource(services,
   spec, assume_yes, dry_run)`, `remove_resource(services, resource_id, assume_yes, dry_run)` and
   `attach_copy(services, spec, assume_yes, dry_run)`. The project must be initialised
   (`load_installation`); the registry is read with `load_resources`.
2. A success is one `apply_plan` of exactly two writes: the registry (`contract_bytes`, entries in
   order of id) and the lock (last, with the registry recorded as seeded with the hash of the new
   bytes), journalled under the command `resources add`, `resources update`, `resources remove` or
   `resources attach`, so that `rollback` restores the earlier state. Nothing is rendered.
3. Confirmation as in `profile answer`: `dry_run` gives `previewed` and writes nothing;
   `assume_yes` applies; otherwise a terminal is asked `confirm('Change the registry of links?',
   default=False)` and a no gives `previewed`; without a terminal the status is `needs-input` with
   ORQ-E115 and nothing is written.
4. A refusal (a builder's ORQ-E509, or an invalid registry file with the findings of
   `load_resources`) gives `refused`, no plan, nothing written, and no part of an input value in a
   finding or a note.
5. `add` notes the next step `orqlet upgrade`; for access `login` (also an `update` that sets it)
   the findings hold the INFO finding ORQ-I500. `update` keeps the record of a stored copy and,
   when the address changes, says in `notes` that `docs/resources/<id>.md` has a `Source:` line
   that no longer matches. `remove` names the copy file in `notes` when it exists, and says that
   the person must delete it; it never touches the file.
6. `attach_copy` refuses an unknown id (ORQ-E509), a missing copy file (ORQ-E504), a copy that
   fails the checks of `validate resources` (ORQ-E506), a `form` other than `copy` or `summary`, a
   `ttl_days` outside 1 to 365 and the form `copy` for a login entry (ORQ-E509). It records `form`,
   the SHA-256 of the LF-normalised text, `retrieved_at` (`services.clock.now().isoformat()`) and
   `ttl_days`; a second attach replaces the record; the copy file is not touched. For a login
   entry it asks at a terminal EVEN with `assume_yes` (any text; the answer must be yes); without
   a terminal it is `needs-input` with ORQ-E510 and nothing is written, also with `assume_yes`.
   With `dry_run` it is `previewed` and nothing is asked.

These tests were written first, by the Tester of phase P-4, before the commands existed. The file
system is the in-memory fake of tests/fakes and the services are the ones of
tests/support/init_env.py (ORQLET-TEST-001). Credential-shaped text is assembled from parts at run
time and never written as one literal (ORQLET-SEC-003).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message and the words of the confirmation of `attach` for a login entry, what
  `Finding.path` holds, and every word of ORQ-I500 and of the `notes` except the few that the
  sources state;
- whether an update that changes nothing is refused or applied;
- whether a refused or `needs-input` result carries a plan or a registry;
- which refusal comes first when an attach has several reasons, and how many questions an attach
  of a login entry asks at a terminal when `assume_yes` is false (only that it asks);
- what an edit does with a registry that is missing while the lock records it (ORQ-E503 is the
  code of `init` and `upgrade` for it; the commands are not said to share it);
- whether `update`, `remove` and `attach` carry the next step in `notes` (only `add` does, in the
  interface decision; the human text of the command line is pinned in the integration test);
- whether `remove` or an `update` of something other than the address says anything about a copy;
- how a lone carriage return in a copy is read.
"""

from __future__ import annotations

import dataclasses
import functools
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.emit import YamlWriter
from orqlet.application.contracts.generated_lock import GeneratedLock, LockedFile
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import Resource, Resources
from orqlet.application.ports.filesystem import FileKind
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases import resources_edit
from orqlet.application.usecases.diagnose import doctor
from orqlet.application.usecases.init_files import contract_bytes
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.installation import NotInitialised
from orqlet.application.usecases.resources_edit import (
    CopySpec,
    ResourcesEditResult,
    ResourceSpec,
    add_resource,
    attach_copy,
    remove_resource,
    update_resource,
)
from orqlet.application.usecases.resources_source import load_resources
from orqlet.application.usecases.rollback import RollbackOptions, rollback
from orqlet.application.usecases.services import Services
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from orqlet.application.usecases.validate_resources import validate_resources
from orqlet.application.usecases.validation import ValidateServices, ValidationResult
from orqlet.domain.changeplan import ChangePlan, PlannedWrite
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Finding, Severity, Verdict
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath
from tests.fakes.clock import FixedClock
from tests.fakes.ids import SequentialIds
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.prompter import ScriptedPrompter
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED
from tests.support.init_env import Env, tree
from tests.support.trees import repo

pytestmark = pytest.mark.unit

SCHEMA = "orqlet.resources/v1"
REGISTRY = ".orqlet/resources.yaml"
LOCK = ".orqlet/generated.lock.yaml"
REGISTRY_PATH = CanonicalPath.parse(REGISTRY)
LOADER = StrictYamlLoader()
WRITER = YamlWriter()
YES = InitOptions(assume_yes=True)
LIMIT = 256 * 1024
COPY_LIMIT = 64 * 1024  # ADR-002 decision 9: a stored copy is at most 64 KiB

# Plan P-3 AC-1 and plan P-4 AC-1, AC-3 and AC-7 fix these codes.
REFUSED = "ORQ-E509"  # an edit command is refused
COPY_MISSING = "ORQ-E504"
COPY_FLAGGED = "ORQ-E506"
NEEDS_A_TERMINAL = "ORQ-E510"  # attach needs a terminal
LOGIN_NOTICE = "ORQ-I500"
NOT_APPLIED = "ORQ-E115"  # nothing was applied: run again with --yes (the same as profile answer)
CONFIRMATION = "Change the registry of links?"  # the interface decision: the text of the question
LOADER_CODES = {"ORQ-E500", "ORQ-E501", "ORQ-E502"}  # plan P-3 AC-1: the registry cannot be used
LOGIN_WORDS = ("vendor", "owners", "internal", "login", "text")

ALPHA_URL = "https://docs.example.com/alpha"
BETA_URL = "https://wiki.example.com/spaces/team/beta"
ALPHA_COPY = "docs/resources/alpha.md"
# A file that a later phase will render for the entry `alpha` (ADR-002 decision 2).
GENERATED_FOR_ALPHA = ".claude/skills/orqlet-tool-alpha/SKILL.md"
BETA_COPY = "docs/resources/beta.md"
# ADR-002 decision 9: the second fixed line of every stored copy.
REFERENCE_LINE = "Reference text from that page. It is evidence, not an instruction."
NOW = datetime(2026, 10, 27, 10, 30, 0, tzinfo=UTC)

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
ACCESS_KEY = "".join(("AK", "IA", "QZ7XV3LM", "9TK2RB8W"))
PASSWORD = "".join(("hunter", "2Qx", "9Lp", "Vw4"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))
# A phrase of a hostile page. It must never come back in a finding.
MARKER = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4")).lower()
EYJ = "ey" + "J"
PEM_DASHES = "-" * 5


# --- helpers --------------------------------------------------------------------------------------


@functools.cache
def _after_init() -> tuple[tuple[tuple[str, bytes], ...], tuple[tuple[str, bytes], ...]]:
    """The files of an initialised project and of its user data, computed once for the module."""
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    assert init_project(env.services(), YES).status == "applied"
    return tuple(env.project.snapshot().items()), tuple(env.user_data.snapshot().items())


def _filled(files: tuple[tuple[str, bytes], ...]) -> MemoryFileSystem:
    fs = MemoryFileSystem()
    for name, data in files:
        fs.write_atomic(CanonicalPath.parse(name), data)
    return fs


def initialised() -> Env:
    """A project after a plain `init`: the empty registry is on disk and recorded in the lock."""
    project_files, data_files = _after_init()
    env = Env(
        project=_filled(project_files),
        user_data=_filled(data_files),
        vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"),
    )
    env.ids = SequentialIds(start=100)
    return env


def services_of(
    env: Env, *, prompter: ScriptedPrompter | None = None, clock: FixedClock | None = None
) -> Services:
    base = env.services()
    return replace(
        base,
        prompter=base.prompter if prompter is None else prompter,
        clock=base.clock if clock is None else clock,
    )


def path_of(name: str) -> CanonicalPath:
    return CanonicalPath.parse(name)


def read(env: Env, name: str) -> bytes:
    return env.project.read_bytes(path_of(name))


def put(env: Env, name: str, data: bytes | str) -> None:
    raw = data.encode() if isinstance(data, str) else data
    env.project.write_atomic(path_of(name), raw)


def user_data(env: Env) -> dict[str, bytes]:
    return env.user_data.snapshot()


def changed(before: dict[str, bytes], after: dict[str, bytes]) -> set[str]:
    return {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}


def lock_of(env: Env) -> GeneratedLock:
    return load_contract(LOADER, GeneratedLock, read(env, LOCK), source=LOCK)


def lock_entry(env: Env, name: str) -> LockedFile | None:
    return next((entry for entry in lock_of(env).files if entry.path == name), None)


def set_lock(env: Env, lock: GeneratedLock) -> None:
    env.project.write_atomic(path_of(LOCK), contract_bytes(WRITER, lock))


def drop_from_lock(env: Env, name: str) -> None:
    lock = lock_of(env)
    kept = tuple(entry for entry in lock.files if entry.path != name)
    set_lock(env, lock.model_copy(update={"files": kept}))


def plant_generated_file(env: Env, name: str, content: bytes) -> None:
    """A file that Orqlet generated earlier and recorded, as a render of the registry would be.

    Nothing is rendered from the registry in this phase, so the test plants the file by hand, as
    `plant_generated_file` of test_resources_diagnose.py does.
    """
    put(env, name, content)
    lock = lock_of(env)
    recorded = LockedFile(
        path=name,
        owner=OwnerMode.ORQLET,
        file_class=FileClass.GENERATED,
        rendered_sha256=sha256_hex(content),
    )
    set_lock(env, lock.model_copy(update={"files": (*lock.files, recorded)}))


def registry_of(env: Env) -> Resources:
    resources, findings = load_resources(env.project, LOADER, REGISTRY)
    assert resources is not None, findings
    return resources


def entry_of(resources: Resources, resource_id: str) -> Resource:
    return next(item for item in resources.resources if item.id == resource_id)


def ids_of(resources: Resources) -> list[str]:
    return [item.id for item in resources.resources]


def codes(findings: tuple[Finding, ...] | list[Finding]) -> set[str]:
    return {finding.code for finding in findings}


def shown(result: ResourcesEditResult) -> str:
    """Everything that a result shows: the findings and the notes, with their representation."""
    findings = "\n".join(f"{f.code}\n{f.message}\n{f.path}\n{f!r}" for f in result.findings)
    return findings + "\n" + "\n".join(result.notes)


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters of it in a row (any letter case).

    A window of 8 characters of a random-looking secret cannot appear in a fixed message by chance.
    """
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def written(plan: ChangePlan | None) -> dict[str, PlannedWrite]:
    assert plan is not None
    return {str(write.path): write for write in plan.writes}


def sound_copy(url: str = ALPHA_URL, body: str = "Notes taken from the page.\n") -> str:
    """A copy with the two fixed lines, a blank line and a body."""
    return f"Source: {url}\n{REFERENCE_LINE}\n\n{body}"


def padded_copy(size: int, url: str = ALPHA_URL) -> str:
    """A sound copy of exactly `size` bytes: short plain lines so that no line scan can object."""
    head = sound_copy(url, "")
    remaining = size - len(head.encode())
    assert remaining >= 0
    lines, rest = divmod(remaining, 64)
    text = head + ("x" * 63 + "\n") * lines
    if rest == 1:
        text += "\n"
    elif rest:
        text += "x" * (rest - 1) + "\n"
    assert len(text.encode()) == size
    return text


def spec(**changes: Any) -> ResourceSpec:
    """A spec with the five fields that an add needs. A change whose value is None leaves it out."""
    base: dict[str, Any] = {
        "id": "alpha",
        "url": ALPHA_URL,
        "title": "Alpha guide",
        "kind": "team-docs",
        "note": "Read before changing the alpha module.",
        "access": "public",
    }
    return ResourceSpec(**{**base, **changes})


def add_entry(env: Env, **changes: Any) -> ResourcesEditResult:
    result = add_resource(services_of(env), spec(**changes), assume_yes=True, dry_run=False)
    assert result.status == "applied", result.findings
    return result


def alpha_with_a_file(text: str | bytes | None = None, **entry_changes: Any) -> Env:
    """A project with the public entry `alpha` and its copy file; the entry has no record yet."""
    env = initialised()
    add_entry(env, **entry_changes)
    put(env, ALPHA_COPY, sound_copy() if text is None else text)
    return env


def beta_with_a_file() -> Env:
    """A project with the login entry `beta` and a summary file for it; no record yet."""
    env = initialised()
    add_entry(env, id="beta", url=BETA_URL, title="Beta wiki", access="login")
    put(env, BETA_COPY, sound_copy(BETA_URL, "A short summary of the page.\n"))
    return env


def attach(
    env: Env,
    resource_id: str = "alpha",
    form: str = "copy",
    ttl_days: int = 30,
    *,
    assume_yes: bool = True,
    dry_run: bool = False,
    prompter: ScriptedPrompter | None = None,
    clock: FixedClock | None = None,
) -> ResourcesEditResult:
    return attach_copy(
        services_of(env, prompter=prompter, clock=clock),
        CopySpec(id=resource_id, form=form, ttl_days=ttl_days),
        assume_yes=assume_yes,
        dry_run=dry_run,
    )


def journal_of(env: Env, change_id: str | None) -> dict[str, Any]:
    found = [
        json.loads(value)
        for key, value in env.user_data.snapshot().items()
        if key.endswith(f"{change_id}.json")
    ]
    assert len(found) == 1
    record: dict[str, Any] = found[0]
    return record


def validated(env: Env) -> ValidationResult:
    """`validate resources` on the project as it stands: what plan P-3 built, used as an oracle."""
    services = ValidateServices(project=env.project, vcs=FakeVcs(), loader=LOADER, workflow=PINNED)
    return validate_resources(services, REGISTRY)


# --- a registry that cannot be used ---------------------------------------------------------------


def _overwrite(content: bytes) -> Callable[[Env], None]:
    def damage(env: Env) -> None:
        env.project.write_atomic(REGISTRY_PATH, content)

    return damage


def _directory(env: Env) -> None:
    env.project.delete(REGISTRY_PATH)
    env.project.make_dir(REGISTRY_PATH)


def _symbolic_link(env: Env) -> None:
    env.project.add_symlink(REGISTRY)


def _padded_registry(size: int) -> bytes:
    empty = f"schema: {SCHEMA}\nresources: []\n".encode()
    return empty + b"#" + b"x" * (size - len(empty) - 2) + b"\n"


def _entry_document(resource_id: str = "alpha") -> dict[str, Any]:
    return {
        "id": resource_id,
        "title": "Alpha guide",
        "kind": "team-docs",
        "url": ALPHA_URL,
        "note": "Read before changing the alpha module.",
        "access": "public",
    }


# name -> how to damage the registry of an initialised project
INVALID_REGISTRIES: dict[str, Callable[[Env], None]] = {
    "fails-its-contract": _overwrite(
        json.dumps({"schema": SCHEMA, "resources": [_entry_document(), _entry_document()]}).encode()
    ),
    "refused-by-the-strict-loader": _overwrite(
        f"schema: {SCHEMA}\nresources: &r []\nagain: *r\n".encode()
    ),
    "is-above-256-kib": _overwrite(_padded_registry(LIMIT + 1)),
    "is-a-directory": _directory,
    "is-a-symbolic-link": _symbolic_link,
}


# --- the four commands, for the tests that hold for every one of them -----------------------------


@dataclass(frozen=True)
class Command:
    """One of the four edit commands and the state in which it applies."""

    label: str
    journal_name: str  # the command name that `apply_plan` records (the interface decision)
    prepare: Callable[[Env], None]
    run: Callable[[Services, bool, bool], ResourcesEditResult]


def _nothing(env: Env) -> None:
    """The project as `init` left it: the empty registry."""


def _an_entry(env: Env) -> None:
    add_entry(env)


def _an_entry_and_its_copy(env: Env) -> None:
    add_entry(env)
    put(env, ALPHA_COPY, sound_copy())


def _run_add(services: Services, assume_yes: bool, dry_run: bool) -> ResourcesEditResult:
    return add_resource(
        services,
        spec(id="beta", url="https://docs.example.com/beta", title="Beta guide"),
        assume_yes=assume_yes,
        dry_run=dry_run,
    )


def _run_update(services: Services, assume_yes: bool, dry_run: bool) -> ResourcesEditResult:
    return update_resource(
        services,
        ResourceSpec(id="alpha", title="Alpha guide, revised"),
        assume_yes=assume_yes,
        dry_run=dry_run,
    )


def _run_remove(services: Services, assume_yes: bool, dry_run: bool) -> ResourcesEditResult:
    return remove_resource(services, "alpha", assume_yes=assume_yes, dry_run=dry_run)


def _run_attach(services: Services, assume_yes: bool, dry_run: bool) -> ResourcesEditResult:
    return attach_copy(
        services,
        CopySpec(id="alpha", form="copy", ttl_days=30),
        assume_yes=assume_yes,
        dry_run=dry_run,
    )


COMMANDS = (
    Command("add", "resources add", _nothing, _run_add),
    Command("update", "resources update", _an_entry, _run_update),
    Command("remove", "resources remove", _an_entry, _run_remove),
    Command("attach", "resources attach", _an_entry_and_its_copy, _run_attach),
)


@pytest.fixture(params=COMMANDS, ids=[command.label for command in COMMANDS])
def command(request: pytest.FixtureRequest) -> Command:
    found: Command = request.param
    return found


def prepared(command: Command) -> Env:
    env = initialised()
    command.prepare(env)
    return env


# --- the names of the module ----------------------------------------------------------------------


def test_copy_spec_has_three_required_fields_and_is_frozen() -> None:
    """AC-8. expected_behavior_source: EC-26 (`class CopySpec`) and the interface decision ("a
    frozen dataclass with the required fields `id: str`, `form: str`, `ttl_days: int`")."""
    fields = {field.name: field for field in dataclasses.fields(CopySpec)}

    assert set(fields) == {"id", "form", "ttl_days"}
    assert all(
        field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING
        for field in fields.values()
    )
    copy = CopySpec(id="alpha", form="copy", ttl_days=30)
    with pytest.raises(dataclasses.FrozenInstanceError):
        copy.ttl_days = 31  # type: ignore[misc]
    with pytest.raises(TypeError):
        CopySpec(id="alpha", form="copy")  # type: ignore[call-arg]


def test_the_result_has_six_fields_and_five_of_them_default_to_nothing() -> None:
    """AC-8. expected_behavior_source: EC-27 (`class ResourcesEditResult`) and the interface
    decision (`status`; `findings = ()`, `plan = None`, `change_id = None`, `resources = None`,
    `notes = ()`; frozen)."""
    fields = {field.name: field for field in dataclasses.fields(ResourcesEditResult)}

    assert list(fields) == ["status", "findings", "plan", "change_id", "resources", "notes"]
    result = ResourcesEditResult("applied")
    assert (result.findings, result.plan, result.change_id) == ((), None, None)
    assert (result.resources, result.notes) == (None, ())
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "refused"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("function", "names"),
    [
        (add_resource, ["services", "spec", "assume_yes", "dry_run"]),
        (update_resource, ["services", "spec", "assume_yes", "dry_run"]),
        (remove_resource, ["services", "resource_id", "assume_yes", "dry_run"]),
        (attach_copy, ["services", "spec", "assume_yes", "dry_run"]),
    ],
    ids=["add", "update", "remove", "attach"],
)
def test_the_four_functions_take_the_arguments_of_the_manifest_in_order(
    function: Callable[..., ResourcesEditResult], names: list[str]
) -> None:
    """AC-8. expected_behavior_source: EC-30 to EC-33 (the four signatures) and the interface
    decision (`add_resource(services, spec, assume_yes, dry_run)` and the other three). Whether
    an argument has a default is not pinned."""
    parameters = inspect.signature(function).parameters

    assert list(parameters) == names


def test_the_module_has_only_the_public_names_that_the_manifest_adds() -> None:
    """AC-8. expected_behavior_source: AC-8 ("The public API of the package differs from the base,
    in this phase, only by EC-26, EC-27, EC-30 to EC-33, EC-38, EC-39 and EC-47") and plan P-3
    (`ResourceSpec`, `resources_with` and `resources_without` are the public names of the module
    already): what the module defines and does not mark private is those nine names."""
    defined = {
        name
        for name, value in vars(resources_edit).items()
        if not name.startswith("_")
        and getattr(value, "__module__", None) == resources_edit.__name__
    }

    assert defined == {
        "ResourceSpec",
        "resources_with",
        "resources_without",
        "CopySpec",
        "ResourcesEditResult",
        "add_resource",
        "update_resource",
        "remove_resource",
        "attach_copy",
    }


# --- what every command does ----------------------------------------------------------------------


def test_a_dry_run_previews_the_two_writes_and_writes_nothing(command: Command) -> None:
    """AC-1, AC-3. expected_behavior_source: the interface decision ("dry_run gives status
    previewed and writes nothing"; the writes of the plan are the registry and the lock, "the
    lock (last)") and ORQLET-SAFE-001 (every write goes through a plan the person can preview)."""
    env = prepared(command)
    before, data = tree(env.project), user_data(env)

    result = command.run(services_of(env), False, True)

    assert result.status == "previewed", result.findings
    assert result.plan is not None
    assert [str(write.path) for write in result.plan.writes] == [REGISTRY, LOCK]
    writes = written(result.plan)
    assert writes[LOCK].last is True
    assert writes[REGISTRY].last is False
    assert result.change_id is None
    assert tree(env.project) == before
    assert user_data(env) == data


def test_an_applied_edit_changes_the_registry_and_the_lock_and_no_other_file(
    command: Command,
) -> None:
    """AC-1, AC-2, AC-3. expected_behavior_source: ADR-002 decision 7 ("build a ChangePlan of
    the registry and the lock"; "They do not render"), the interface decision ("They render
    nothing: no generated file changes") and EC-64 (a stored copy is never written by Orqlet)."""
    env = prepared(command)
    before = tree(env.project)

    result = command.run(services_of(env), True, False)

    assert result.status == "applied", result.findings
    assert result.change_id
    assert set(written(result.plan)) == {REGISTRY, LOCK}
    assert changed(before, tree(env.project)) == {REGISTRY, LOCK}


def test_the_registry_that_is_written_is_the_one_of_the_result_in_order_of_id(
    command: Command,
) -> None:
    """AC-1. expected_behavior_source: the interface decision ("serialised with contract_bytes,
    in order of id"; `resources` is "the registry after the change") and ADR-002 decision 1
    (written in order of id)."""
    env = prepared(command)

    result = command.run(services_of(env), True, False)

    assert result.resources is not None
    assert read(env, REGISTRY) == contract_bytes(WRITER, result.resources)
    assert registry_of(env) == result.resources
    assert ids_of(result.resources) == sorted(ids_of(result.resources))


def test_the_lock_records_the_registry_as_seeded_with_the_hash_of_what_was_written(
    command: Command,
) -> None:
    """AC-1, AC-2. expected_behavior_source: the interface decision ("recording the registry in
    the lock as owner seeded with the hash of the new bytes, exactly as profile_edit does for
    the profile") and ADR-002 decisions 1 and 7 (a seeded file; the edit records the new hash in
    the lock)."""
    env = prepared(command)
    before = lock_of(env)

    command.run(services_of(env), True, False)

    entry = lock_entry(env, REGISTRY)
    assert entry is not None
    assert entry.owner is OwnerMode.SEEDED
    assert entry.file_class is None
    assert entry.rendered_sha256 is None
    assert entry.seeded_sha256 == sha256_hex(read(env, REGISTRY))
    after = lock_of(env)
    assert after.generator == before.generator
    assert after.standards_lock == before.standards_lock
    assert [e for e in after.files if e.path != REGISTRY] == [
        e for e in before.files if e.path != REGISTRY
    ]


def test_the_edit_is_one_journalled_change_under_the_name_of_the_command(
    command: Command,
) -> None:
    """AC-1, AC-6. expected_behavior_source: ORQLET-SAFE-001 (every write goes through a
    journalled change plan) and the interface decision (`apply_plan` is called with the command
    `resources add`, `resources update`, `resources remove` or `resources attach`)."""
    env = prepared(command)

    result = command.run(services_of(env), True, False)

    record = journal_of(env, result.change_id)
    assert record["command"] == command.journal_name
    assert record["status"] == "complete"


def test_rollback_restores_the_earlier_registry_and_lock(command: Command) -> None:
    """AC-1, AC-6. expected_behavior_source: the interface decision ("The change is journalled
    ... so `rollback` restores the earlier state") and plan P-4 file operation for this test
    ("the applied change is undone by rollback")."""
    env = prepared(command)
    before = tree(env.project)
    result = command.run(services_of(env), True, False)
    assert result.change_id is not None

    undone = rollback(services_of(env), RollbackOptions(result.change_id, assume_yes=True))

    assert undone.status == "applied"
    assert tree(env.project) == before


def test_an_add_says_in_its_notes_that_the_next_step_is_upgrade() -> None:
    """AC-1. expected_behavior_source: AC-1 ("prints the next step orqlet upgrade") and the
    interface decision ("On success `notes` contains a sentence that names the next step `orqlet
    upgrade`"). The other three commands print it too (ADR-002 decision 7); the integration test
    of the command line pins that in the human text."""
    env = initialised()

    result = add_resource(services_of(env), spec(), assume_yes=True, dry_run=False)

    assert result.status == "applied", result.findings
    assert any("orqlet upgrade" in note for note in result.notes), result.notes


def test_an_upgrade_after_an_edit_makes_no_proposal_and_leaves_the_registry_alone(
    command: Command,
) -> None:
    """AC-1, AC-2. expected_behavior_source: ADR-002 decisions 5 and 7 (the edit records the new
    hash in the lock, so a hand edit and an edit by command alike make no proposal) and plan P-3
    AC-2 ("an edit made through the commands ... causes no proposal"). The test does not say
    that the upgrade has nothing at all to do: from phase P-6 on it renders files from the
    registry, and that is a change that the edit must not bundle (decision 7)."""
    env = prepared(command)
    command.run(services_of(env), True, False)
    registry_before = read(env, REGISTRY)

    check = upgrade(services_of(env), UpgradeOptions(check=True))
    errors = [f for f in doctor(services_of(env)).findings if f.severity is Severity.ERROR]

    assert check.status in {"up-to-date", "available"}, check.findings
    planned = {str(w.path) for w in check.plan.writes} if check.plan is not None else set()
    assert REGISTRY not in planned
    assert not any(name.startswith(".orqlet/proposals/") for name in tree(env.project))
    assert read(env, REGISTRY) == registry_before
    assert errors == []


def test_without_yes_and_without_a_terminal_nothing_is_written_and_the_person_is_told(
    command: Command,
) -> None:
    """AC-1. expected_behavior_source: the interface decision ("without a terminal the status is
    needs-input with finding ORQ-E115 and nothing is written")."""
    env = prepared(command)
    before, data = tree(env.project), user_data(env)

    result = command.run(services_of(env), False, False)

    assert result.status == "needs-input"
    assert NOT_APPLIED in codes(result.findings)
    assert tree(env.project) == before
    assert user_data(env) == data


def test_at_a_terminal_it_asks_once_and_a_yes_applies(command: Command) -> None:
    """AC-1. expected_behavior_source: the interface decision ("with a terminal the prompter is
    asked `confirm('Change the registry of links?', default=False)`")."""
    env = prepared(command)
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = command.run(services_of(env, prompter=prompter), False, False)

    assert result.status == "applied", result.findings
    assert prompter.asked == [CONFIRMATION]


def test_at_a_terminal_a_no_gives_a_preview_and_writes_nothing(command: Command) -> None:
    """AC-1. expected_behavior_source: the interface decision ("a refusal gives previewed": the
    answer no to the question)."""
    env = prepared(command)
    before, data = tree(env.project), user_data(env)
    prompter = ScriptedPrompter(interactive=True, confirm_all=False)

    result = command.run(services_of(env, prompter=prompter), False, False)

    assert result.status == "previewed"
    assert prompter.asked == [CONFIRMATION]
    assert tree(env.project) == before
    assert user_data(env) == data


def test_with_yes_nothing_is_asked_even_at_a_terminal(command: Command) -> None:
    """AC-1. expected_behavior_source: the interface decision ("assume_yes applies"; only the
    attach of a login entry asks with it, and the entry of `attach` here is public)."""
    env = prepared(command)
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = command.run(services_of(env, prompter=prompter), True, False)

    assert result.status == "applied"
    assert prompter.asked == []


def test_an_uninitialised_directory_is_refused_by_every_command(command: Command) -> None:
    """AC-1. expected_behavior_source: the interface decision ("All four take the installed
    project (load_installation ...)"): `load_installation` raises `NotInitialised`, as it does
    for `profile answer`."""
    env = Env(project=repo("uv_fastapi"))

    with pytest.raises(NotInitialised):
        command.run(services_of(env), True, False)


@pytest.mark.parametrize("name", list(INVALID_REGISTRIES), ids=list(INVALID_REGISTRIES))
def test_an_invalid_registry_is_refused_with_the_findings_of_the_loader_and_nothing_is_written(
    command: Command, name: str
) -> None:
    """AC-1, AC-3. expected_behavior_source: the interface decision ("An invalid registry file
    on disk gives status refused with the findings of load_resources (ORQ-E500, ORQ-E501 or
    ORQ-E502); the exact set is not pinned") and ADR-002 decision 6 (an invalid registry is
    never replaced by an empty one). The oracle is `load_resources` itself on the same damaged
    file."""
    env = prepared(command)
    INVALID_REGISTRIES[name](env)
    _, loader_findings = load_resources(env.project, LOADER, REGISTRY)
    assert loader_findings
    assert codes(loader_findings) <= LOADER_CODES
    before, data = tree(env.project), user_data(env)

    result = command.run(services_of(env), True, False)

    assert result.status == "refused"
    assert codes(loader_findings) <= codes(result.findings)
    assert result.change_id is None
    assert tree(env.project) == before
    assert user_data(env) == data


def test_an_add_to_a_registry_that_is_missing_and_not_recorded_creates_it() -> None:
    """AC-1. expected_behavior_source: the interface decision ("the registry is read with
    load_resources", which gives an empty registry and no finding for a missing file: plan P-3
    AC-3) and ADR-002 decision 6 ("a registry that is missing and not recorded is an empty
    one")."""
    env = initialised()
    env.project.delete(REGISTRY_PATH)
    drop_from_lock(env, REGISTRY)

    result = add_resource(services_of(env), spec(), assume_yes=True, dry_run=False)

    assert result.status == "applied", result.findings
    assert written(result.plan)[REGISTRY].kind == "create"
    assert ids_of(registry_of(env)) == ["alpha"]
    entry = lock_entry(env, REGISTRY)
    assert entry is not None
    assert entry.owner is OwnerMode.SEEDED
    assert entry.seeded_sha256 == sha256_hex(read(env, REGISTRY))


@pytest.mark.parametrize("command", COMMANDS[1:], ids=[c.label for c in COMMANDS[1:]])
def test_the_other_commands_find_no_entry_in_a_missing_unrecorded_registry_and_write_nothing(
    command: Command,
) -> None:
    """AC-1. expected_behavior_source: the interface decision ("the registry is read with
    load_resources": a missing file is an empty registry, plan P-3 AC-3; so there is no entry to
    update, remove or attach to, and a refusal writes nothing) and ADR-002 decision 6 ("missing
    and not recorded is an empty one")."""
    env = initialised()
    env.project.delete(REGISTRY_PATH)
    drop_from_lock(env, REGISTRY)
    before, data = tree(env.project), user_data(env)

    result = command.run(services_of(env), True, False)

    assert (result.status, codes(result.findings)) == ("refused", {REFUSED})
    assert tree(env.project) == before
    assert user_data(env) == data


# --- add ------------------------------------------------------------------------------------------


def test_an_add_puts_the_entry_in_the_registry_with_the_given_fields() -> None:
    """AC-1. expected_behavior_source: AC-1 ("resources add writes the entry") and ADR-002
    decisions 1 and 7."""
    env = initialised()

    result = add_resource(
        services_of(env),
        spec(
            id="fastapi-docs",
            kind="tool-docs",
            tool="FastAPI",
            version="0.115",
            paths=("src/api/**/*.py", "tests/api/**/*.py"),
        ),
        assume_yes=True,
        dry_run=False,
    )

    assert result.status == "applied", result.findings
    found = entry_of(registry_of(env), "fastapi-docs")
    assert (found.url, found.title, found.kind, found.access) == (
        ALPHA_URL,
        "Alpha guide",
        "tool-docs",
        "public",
    )
    assert (found.tool, found.version) == ("FastAPI", "0.115")
    assert found.applies_to is not None
    assert found.applies_to.paths == ("src/api/**/*.py", "tests/api/**/*.py")
    assert found.stored_copy is None


def test_adds_in_any_order_give_a_registry_in_order_of_id() -> None:
    """AC-1. expected_behavior_source: AC-1 ("writes the entry in order of id") and ADR-002
    decision 1."""
    env = initialised()

    for resource_id in ("zeta", "alpha", "mid"):
        add_entry(env, id=resource_id, url=f"https://docs.example.com/{resource_id}")

    assert ids_of(registry_of(env)) == ["alpha", "mid", "zeta"]


def test_an_add_and_then_a_remove_give_back_the_same_files() -> None:
    """AC-1, AC-2. expected_behavior_source: ADR-002 decision 7 ("An id cannot change (remove
    the entry and add another)": the two commands are inverses) and the interface decision (the
    same serialisation and the same lock record every time)."""
    env = initialised()
    before = tree(env.project)

    add_entry(env)
    removed = remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    assert removed.status == "applied", removed.findings
    assert tree(env.project) == before


def test_the_same_add_twice_is_refused_the_second_time_and_changes_nothing() -> None:
    """AC-1. expected_behavior_source: AC-1 ("is refused (exit 3, ORQ-E509) for a repeated id") and
    ORQLET-TEST-002 (a re-run is safe): the second run of the same command finds the entry that the
    first one wrote."""
    env = initialised()
    first = add_resource(services_of(env), spec(), assume_yes=True, dry_run=False)
    after_first, data = tree(env.project), user_data(env)

    second = add_resource(services_of(env), spec(), assume_yes=True, dry_run=False)

    assert first.status == "applied", first.findings
    assert (second.status, codes(second.findings)) == ("refused", {REFUSED})
    assert tree(env.project) == after_first
    assert user_data(env) == data


def test_the_same_remove_twice_is_refused_the_second_time_and_changes_nothing() -> None:
    """AC-2. expected_behavior_source: the interface decision ("remove: resources_without; unknown
    id refused") and ORQLET-TEST-002 (a re-run is safe): the second run finds no entry."""
    env = initialised()
    add_entry(env)
    first = remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)
    after_first, data = tree(env.project), user_data(env)

    second = remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    assert first.status == "applied", first.findings
    assert (second.status, codes(second.findings)) == ("refused", {REFUSED})
    assert tree(env.project) == after_first
    assert user_data(env) == data


BROKEN_ADDS: dict[str, dict[str, Any]] = {
    "id-that-is-already-there": {"id": "alpha"},
    "id-with-capitals": {"id": "Alpha"},
    "id-with-a-double-hyphen": {"id": "my--docs"},
    "id-that-is-a-windows-device-name": {"id": "con"},
    "id-that-is-a-path": {"id": "../etc"},
    "address-that-is-not-https": {"url": "http://docs.example.com/alpha"},
    "address-with-a-fragment": {"url": "https://docs.example.com/alpha#intro"},
    "address-with-a-port": {"url": "https://docs.example.com:8443/alpha"},
    "address-with-a-credential-in-its-query": {
        "url": f"https://docs.example.com/guide?token={TOKEN}"
    },
    "title-of-two-lines": {"title": "two\nlines"},
    "title-with-an-escape-character": {"title": "two\x1b[2Jlines"},
    "note-with-a-backtick": {"note": "run `make` first"},
    "note-with-a-link": {"note": "see https://docs.example.com/other"},
    "note-above-200-characters": {"note": "n" * 201},
    "kind-outside-the-list": {"kind": "wiki"},
    "access-outside-the-list": {"access": "private"},
    "glob-that-is-absolute": {"paths": ("/abs/*.py",)},
    "glob-that-matches-everything": {"paths": ("**/*",)},
    "tool-on-an-entry-that-is-not-tool-docs": {"kind": "team-docs", "tool": "FastAPI"},
    "public-entry-on-an-internal-host": {"url": "https://wiki.example.internal/x"},
    "no-note": {"note": None},
    "no-address": {"url": None},
}


@pytest.mark.parametrize("name", list(BROKEN_ADDS), ids=list(BROKEN_ADDS))
def test_an_add_that_the_builder_refuses_is_refused_with_e509_and_writes_nothing(
    name: str,
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("is refused (exit 3, ORQ-E509) for a repeated id,
    an invalid address, text or glob, or a tool on a kind that is not tool-docs") and the
    interface decision ("Refusals give status refused, plan None, nothing written, findings with
    code ORQ-E509 (from resources_with / resources_without)"). Each of these specs is refused by
    `resources_with` of phase P-3."""
    env = initialised()
    add_entry(env)  # `alpha` is there, for the case of a repeated id
    before, data = tree(env.project), user_data(env)

    result = add_resource(
        services_of(env), spec(**BROKEN_ADDS[name]), assume_yes=True, dry_run=False
    )

    assert result.status == "refused"
    assert codes(result.findings) == {REFUSED}
    assert all(finding.severity is Severity.ERROR for finding in result.findings)
    assert result.plan is None
    assert result.change_id is None
    assert tree(env.project) == before
    assert user_data(env) == data


def test_a_refused_add_is_refused_also_in_a_dry_run_and_at_a_terminal() -> None:
    """AC-1. expected_behavior_source: the interface decision ("Refusals give status refused,
    plan None, nothing written"), whatever the confirmation: a dry run and a terminal that says
    yes do not turn a refusal into a preview or a change."""
    env = initialised()
    add_entry(env)
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    dry = add_resource(services_of(env), spec(), assume_yes=False, dry_run=True)
    asked = add_resource(
        services_of(env, prompter=prompter), spec(), assume_yes=False, dry_run=False
    )

    assert (dry.status, asked.status) == ("refused", "refused")
    assert (dry.plan, asked.plan) == (None, None)


LEAKY_ADDS: dict[str, tuple[dict[str, Any], tuple[str, ...]]] = {
    "address": ({"url": f"https://docs.example.com/guide?token={TOKEN}"}, (TOKEN,)),
    "address-with-user-information": (
        {"url": f"https://deploy:{PASSWORD}@docs.example.com/guide"},
        (PASSWORD,),
    ),
    "address-with-an-opaque-segment": ({"url": f"https://docs.example.com/{OPAQUE}"}, (OPAQUE,)),
    "note": ({"note": f"use `{TOKEN}` first"}, (TOKEN,)),
    "note-with-a-link": ({"note": f"see https://{ACCESS_KEY}.example.com/x"}, (ACCESS_KEY,)),
    "title": ({"title": f"[{TOKEN}](x)"}, (TOKEN,)),
    "glob": ({"paths": (f"!{TOKEN}",)}, (TOKEN,)),
    "glob-climbing-out": ({"paths": (f"{ACCESS_KEY}/../x",)}, (ACCESS_KEY,)),
    "id": ({"id": TOKEN}, (TOKEN,)),
    "tool": ({"kind": "tool-docs", "tool": f"{TOKEN}#"}, (TOKEN,)),
    "version": ({"kind": "tool-docs", "tool": "demo", "version": f"{TOKEN}#"}, (TOKEN,)),
    "several-fields-at-once": (
        {
            "id": ACCESS_KEY,
            "title": f"[{PASSWORD}](x)",
            "url": f"https://docs.example.com/guide?token={TOKEN}",
            "note": f"see `{OPAQUE}`",
            "paths": (f"!{TOKEN}",),
        },
        (TOKEN, ACCESS_KEY, PASSWORD, OPAQUE),
    ),
}


@pytest.mark.parametrize("name", list(LEAKY_ADDS), ids=list(LEAKY_ADDS))
def test_no_finding_of_a_refused_add_shows_a_part_of_what_was_typed(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-1. expected_behavior_source: ORQLET-SEC-003 (no finding, exception, standard output or
    standard error shows a credential-shaped value), ADR-002 decision 10 and plan P-3 AC-2."""
    changes, secrets = LEAKY_ADDS[name]
    env = initialised()

    result = add_resource(services_of(env), spec(**changes), assume_yes=True, dry_run=False)
    streams = capsys.readouterr()

    assert result.status == "refused"
    for secret in secrets:
        assert not leaks(shown(result), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


# --- the login notice -----------------------------------------------------------------------------


def _notices(result: ResourcesEditResult) -> list[Finding]:
    return [finding for finding in result.findings if finding.code == LOGIN_NOTICE]


def test_an_add_with_access_login_carries_the_notice_about_the_model_vendor() -> None:
    """AC-7. expected_behavior_source: AC-7 ("prints ORQ-I500, which says that page text goes to
    the client's model vendor and that using the login route for internal content is an owners'
    decision"), ADR-001 consequences and considerations S-9 (the same words). The exact wording
    is not pinned: the message holds a stable set of words that those sources state."""
    env = initialised()

    result = add_resource(
        services_of(env),
        spec(id="beta", url=BETA_URL, access="login"),
        assume_yes=True,
        dry_run=False,
    )

    (notice,) = _notices(result)
    assert notice.severity is Severity.INFO
    text = notice.message.lower()
    for word in LOGIN_WORDS:
        assert word in text, word


def test_the_notice_is_also_shown_in_a_preview() -> None:
    """AC-7. expected_behavior_source: the interface decision ("For `access == 'login'` the
    findings contain an INFO finding ORQ-I500"), so the person sees it before the first yes."""
    env = initialised()

    result = add_resource(
        services_of(env),
        spec(id="beta", url=BETA_URL, access="login"),
        assume_yes=False,
        dry_run=True,
    )

    assert result.status == "previewed"
    assert len(_notices(result)) == 1


def test_an_add_with_access_public_carries_no_notice() -> None:
    """AC-7. expected_behavior_source: AC-7 (the notice is for `--access login`) and ADR-001
    consequences (the login route is the case that sends internal text to the vendor)."""
    env = initialised()

    result = add_resource(services_of(env), spec(), assume_yes=True, dry_run=False)

    assert _notices(result) == []


def test_an_update_that_sets_access_login_carries_the_notice() -> None:
    """AC-7. expected_behavior_source: the interface decision ("updating access to login also
    yields ORQ-I500")."""
    env = initialised()
    add_entry(env)

    result = update_resource(
        services_of(env), ResourceSpec(id="alpha", access="login"), assume_yes=True, dry_run=False
    )

    assert result.status == "applied", result.findings
    (notice,) = _notices(result)
    assert all(word in notice.message.lower() for word in LOGIN_WORDS)


def test_an_update_that_does_not_set_login_carries_no_notice() -> None:
    """AC-7. expected_behavior_source: the interface decision ("a public entry has no
    ORQ-I500"): a title change of a public entry and a change back to `public` do not give the
    notice."""
    env = initialised()
    add_entry(env)
    add_entry(env, id="beta", url=BETA_URL, access="login")

    title = update_resource(
        services_of(env),
        ResourceSpec(id="alpha", title="Alpha guide, revised"),
        assume_yes=True,
        dry_run=False,
    )
    public = update_resource(
        services_of(env), ResourceSpec(id="beta", access="public"), assume_yes=True, dry_run=False
    )

    assert (title.status, public.status) == ("applied", "applied")
    assert _notices(title) == []
    assert _notices(public) == []


# --- update ---------------------------------------------------------------------------------------


def test_an_update_changes_only_the_fields_that_are_given() -> None:
    """AC-2. expected_behavior_source: AC-2 ("resources update changes only the fields that are
    given") and the interface decision ("only the fields that are given change")."""
    env = initialised()
    add_entry(env, id="beta", url="https://docs.example.com/beta", kind="tool-docs", tool="Celery")
    add_entry(env)
    before = registry_of(env)

    result = update_resource(
        services_of(env),
        ResourceSpec(id="beta", title="Beta guide, revised"),
        assume_yes=True,
        dry_run=False,
    )

    assert result.status == "applied", result.findings
    after = registry_of(env)
    assert ids_of(after) == ["alpha", "beta"]
    assert entry_of(after, "alpha") == entry_of(before, "alpha")
    changed_entry, original = entry_of(after, "beta"), entry_of(before, "beta")
    assert changed_entry.title == "Beta guide, revised"
    assert changed_entry.model_copy(update={"title": original.title}) == original


def test_an_update_of_an_id_that_is_not_there_is_refused_and_cannot_rename_an_entry() -> None:
    """AC-2. expected_behavior_source: AC-2 ("refuses an id change") and ADR-002 decision 7 ("An
    id cannot change (remove the entry and add another)"): the spec has no field for a new id,
    so asking for another id is asking for an entry that does not exist."""
    env = initialised()
    add_entry(env)
    before, data = tree(env.project), user_data(env)

    result = update_resource(
        services_of(env),
        ResourceSpec(id="gamma", title="Renamed entry"),
        assume_yes=True,
        dry_run=False,
    )

    assert (result.status, codes(result.findings)) == ("refused", {REFUSED})
    assert result.plan is None
    assert tree(env.project) == before
    assert user_data(env) == data
    assert ids_of(registry_of(env)) == ["alpha"]


def test_an_unknown_id_is_not_shown_back() -> None:
    """AC-2. expected_behavior_source: the interface decision ("no part of any input value in a
    finding, note or message"), ORQLET-SEC-003 and ADR-002 decision 10."""
    env = initialised()
    unknown = OPAQUE.lower()[:30]  # a valid id that no entry has

    updated = update_resource(
        services_of(env), ResourceSpec(id=unknown, title="x"), assume_yes=True, dry_run=False
    )
    removed = remove_resource(services_of(env), unknown, assume_yes=True, dry_run=False)

    assert not leaks(shown(updated), unknown)
    assert not leaks(shown(removed), unknown)


@pytest.mark.parametrize(
    "changes",
    [
        {"url": "http://docs.example.com/alpha"},
        {"note": "run `make` first"},
        {"title": "two\nlines"},
        {"paths": ("/abs/*.py",)},
        {"tool": "FastAPI"},
        {"access": "private"},
    ],
    ids=["address", "note", "title", "glob", "tool-on-team-docs", "access"],
)
def test_an_update_that_breaks_a_rule_is_refused_with_e509_and_writes_nothing(
    changes: dict[str, Any],
) -> None:
    """AC-2. expected_behavior_source: the interface decision ("update:
    resources_with(replace=True)"; "Refusals give status refused, plan None, nothing written,
    findings with code ORQ-E509") and ADR-002 decision 8. Each of these changes is refused by
    `resources_with` of phase P-3."""
    env = initialised()
    add_entry(env)
    before, data = tree(env.project), user_data(env)

    result = update_resource(
        services_of(env), ResourceSpec(id="alpha", **changes), assume_yes=True, dry_run=False
    )

    assert (result.status, codes(result.findings)) == ("refused", {REFUSED})
    assert result.plan is None
    assert tree(env.project) == before
    assert user_data(env) == data


def test_an_update_to_login_is_refused_for_an_entry_whose_record_is_a_full_copy() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (a login entry may only store a
    summary, a cross-field rule of the contract) and the interface decision (a builder refusal)."""
    env = alpha_with_a_file()
    assert attach(env).status == "applied"
    before = tree(env.project)

    result = update_resource(
        services_of(env), ResourceSpec(id="alpha", access="login"), assume_yes=True, dry_run=False
    )

    assert (result.status, codes(result.findings)) == ("refused", {REFUSED})
    assert tree(env.project) == before


@pytest.mark.parametrize("name", list(LEAKY_ADDS), ids=list(LEAKY_ADDS))
def test_no_finding_of_a_refused_update_shows_a_part_of_what_was_typed(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2. expected_behavior_source: ORQLET-SEC-003 and ADR-002 decision 10. The id of the
    update is the one of `alpha`, a team-docs entry that exists, unless the case puts a secret
    in the id itself."""
    changes, secrets = LEAKY_ADDS[name]
    env = initialised()
    add_entry(env)
    resource_id = changes.get("id", "alpha")
    given = {key: value for key, value in changes.items() if key != "id"}

    result = update_resource(
        services_of(env), ResourceSpec(id=resource_id, **given), assume_yes=True, dry_run=False
    )
    streams = capsys.readouterr()

    assert result.status == "refused"
    for secret in secrets:
        assert not leaks(shown(result), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


def test_an_update_of_the_address_keeps_the_record_and_says_that_the_source_line_is_stale() -> None:
    """AC-2. expected_behavior_source: AC-2 ("keeps the stored-copy record when the address
    changes while printing that the Source line no longer matches"), ADR-002 decision 7 and the
    interface decision (`notes` names `docs/resources/<id>.md` and says that its `Source:` line
    no longer matches)."""
    env = alpha_with_a_file()
    assert attach(env).status == "applied"
    record = entry_of(registry_of(env), "alpha").stored_copy
    assert record is not None
    copy_before = read(env, ALPHA_COPY)

    result = update_resource(
        services_of(env),
        ResourceSpec(id="alpha", url="https://docs.example.com/moved"),
        assume_yes=True,
        dry_run=False,
    )

    assert result.status == "applied", result.findings
    after = entry_of(registry_of(env), "alpha")
    assert after.url == "https://docs.example.com/moved"
    assert after.stored_copy == record
    text = " ".join(result.notes)
    assert ALPHA_COPY in text
    assert "Source" in text
    assert "match" in text.lower()
    assert read(env, ALPHA_COPY) == copy_before


def test_after_such_an_update_validate_resources_fails_until_the_copy_is_refreshed() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 7 ("so `validate resources` fails until
    the copy is refreshed and attached again") and plan P-3 AC-4 (ORQ-E506: a copy without the
    header line of its address)."""
    env = alpha_with_a_file()
    attach(env)
    assert validated(env).verdict is Verdict.PASS
    update_resource(
        services_of(env),
        ResourceSpec(id="alpha", url="https://docs.example.com/moved"),
        assume_yes=True,
        dry_run=False,
    )

    stale = validated(env)
    put(env, ALPHA_COPY, sound_copy("https://docs.example.com/moved"))
    refreshed = attach(env)
    final = validated(env)

    assert stale.verdict is Verdict.FAIL
    assert COPY_FLAGGED in {finding.code for finding in stale.findings}
    assert refreshed.status == "applied", refreshed.findings
    assert final.verdict is Verdict.PASS, final.findings


# --- remove ---------------------------------------------------------------------------------------


def test_a_remove_deletes_the_entry_and_keeps_the_others_in_order() -> None:
    """AC-2. expected_behavior_source: AC-2 ("resources remove deletes the entry") and ADR-002
    decision 7."""
    env = initialised()
    for resource_id in ("alpha", "beta", "gamma"):
        add_entry(env, id=resource_id, url=f"https://docs.example.com/{resource_id}")
    before = registry_of(env)

    result = remove_resource(services_of(env), "beta", assume_yes=True, dry_run=False)

    assert result.status == "applied", result.findings
    after = registry_of(env)
    assert ids_of(after) == ["alpha", "gamma"]
    assert entry_of(after, "alpha") == entry_of(before, "alpha")
    assert entry_of(after, "gamma") == entry_of(before, "gamma")


def test_removing_the_last_entry_leaves_an_empty_valid_registry() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 6 (an empty valid registry is
    `resources: []`, which `remove` leaves), and plan P-3 AC-3."""
    env = initialised()
    add_entry(env)

    remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    assert registry_of(env).resources == ()


def test_a_remove_of_an_id_that_is_not_there_is_refused_and_writes_nothing() -> None:
    """AC-2. expected_behavior_source: the interface decision ("remove: resources_without;
    unknown id refused"; "findings with code ORQ-E509")."""
    env = initialised()
    add_entry(env)
    before, data = tree(env.project), user_data(env)

    result = remove_resource(services_of(env), "gamma", assume_yes=True, dry_run=False)

    assert (result.status, codes(result.findings)) == ("refused", {REFUSED})
    assert result.plan is None
    assert tree(env.project) == before
    assert user_data(env) == data


def test_a_remove_never_touches_the_copy_file_and_says_that_the_person_must_delete_it() -> None:
    """AC-2. expected_behavior_source: AC-2 ("prints that a kept copy must be deleted by the
    person"), the interface decision ("when `docs/resources/<id>.md` exists, `notes` contains a
    sentence that names that path and says the person must delete it; the copy file itself is
    never touched"), ADR-002 decision 7 and EC-64 (never deleted by Orqlet)."""
    env = alpha_with_a_file()
    attach(env)
    copy_before = read(env, ALPHA_COPY)

    result = remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    assert result.status == "applied", result.findings
    assert read(env, ALPHA_COPY) == copy_before
    assert ids_of(registry_of(env)) == []
    text = " ".join(result.notes)
    assert ALPHA_COPY in text
    assert "delete" in text.lower()


def test_a_copy_file_of_an_entry_without_a_record_is_named_too() -> None:
    """AC-2. expected_behavior_source: the interface decision ("when `docs/resources/<id>.md`
    exists, `notes` contains a sentence that names that path and says the person must delete
    it"): the entry has no stored-copy record here, and the file is there."""
    env = alpha_with_a_file()  # the file is there; no record was attached

    result = remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    assert result.status == "applied", result.findings
    assert read(env, ALPHA_COPY) == sound_copy().encode()
    text = " ".join(result.notes)
    assert ALPHA_COPY in text
    assert "delete" in text.lower()


def test_a_remove_does_not_ask_the_question_of_a_login_entry() -> None:
    """AC-2, AC-3. expected_behavior_source: ADR-002 decision 9 (the question "whether this
    repository may hold internal content of that host" belongs to `attach`) and the interface
    decision (the login rule is "of attach")."""
    env = beta_with_a_file()
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = remove_resource(
        services_of(env, prompter=prompter), "beta", assume_yes=True, dry_run=False
    )

    assert result.status == "applied", result.findings
    assert prompter.asked == []


def test_after_a_remove_an_upgrade_leaves_the_copy_in_place_and_doctor_finds_no_error() -> None:
    """AC-2. expected_behavior_source: AC-2 ("after upgrade ... doctor is clean"), EC-64 (Orqlet
    never deletes a stored copy) and ADR-002 decision 7 (`doctor` names a copy whose entry is
    gone: ORQ-I501, information only)."""
    env = alpha_with_a_file()
    attach(env)
    copy_before = read(env, ALPHA_COPY)
    remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    upgraded = upgrade(services_of(env), UpgradeOptions(assume_yes=True))
    findings = doctor(services_of(env)).findings

    assert upgraded.status in {"up-to-date", "applied"}, upgraded.findings
    assert read(env, ALPHA_COPY) == copy_before
    assert [f for f in findings if f.severity is Severity.ERROR] == []
    gone = [f for f in findings if f.code == "ORQ-I501"]
    assert gone
    assert all(f.severity is Severity.INFO for f in gone)


def test_after_a_remove_an_upgrade_deletes_the_generated_files_and_doctor_is_clean() -> None:
    """AC-2. expected_behavior_source: AC-2 ("after upgrade the generated files of that entry
    are gone and doctor is clean") and ADR-002 decision 7 ("`remove` deletes the entry, and the
    generated files become orphans that the next upgrade removes; ... `doctor` is changed to
    ignore a reserved-prefix folder that holds no file ...; a test covers remove, upgrade and
    doctor"). The remove itself renders and deletes nothing, so the recorded file is still there
    after it and the lock still records it; the upgrade then deletes it and the empty folder
    that stays is no error of `doctor`."""
    env = alpha_with_a_file()
    attach(env)
    plant_generated_file(env, GENERATED_FOR_ALPHA, b"a skill that an earlier render wrote\n")

    removed = remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    assert removed.status == "applied", removed.findings
    assert read(env, GENERATED_FOR_ALPHA) == b"a skill that an earlier render wrote\n"
    assert lock_entry(env, GENERATED_FOR_ALPHA) is not None
    upgraded = upgrade(services_of(env), UpgradeOptions(assume_yes=True))
    findings = doctor(services_of(env)).findings

    assert upgraded.status == "applied", upgraded.findings
    assert GENERATED_FOR_ALPHA not in tree(env.project)
    assert lock_entry(env, GENERATED_FOR_ALPHA) is None
    assert [f for f in findings if f.severity is Severity.ERROR] == []
    assert "ORQ-E153" not in codes(findings)
    assert ALPHA_COPY in tree(env.project)  # the copy is the team's: no upgrade deletes it


def test_after_a_remove_an_upgrade_leaves_no_empty_skill_folder() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 7 ("the upgrade deletes the orphans and the
    folders that they leave empty, and stops at the first folder that still holds something")."""
    env = alpha_with_a_file()
    attach(env)
    plant_generated_file(env, GENERATED_FOR_ALPHA, b"a skill that an earlier render wrote\n")
    remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    upgraded = upgrade(services_of(env), UpgradeOptions(assume_yes=True))

    assert upgraded.status == "applied", upgraded.findings
    skill_folder = CanonicalPath.parse(GENERATED_FOR_ALPHA).parent
    assert skill_folder is not None
    assert env.project.kind(skill_folder) is None
    assert env.project.kind(CanonicalPath.parse(".claude/skills")) is FileKind.DIRECTORY


def test_an_entry_can_be_added_again_after_it_was_removed() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 7 ("An id cannot change (remove the
    entry and add another)")."""
    env = initialised()
    add_entry(env)
    remove_resource(services_of(env), "alpha", assume_yes=True, dry_run=False)

    result = add_resource(
        services_of(env), spec(title="Alpha, again"), assume_yes=True, dry_run=False
    )

    assert result.status == "applied", result.findings
    assert entry_of(registry_of(env), "alpha").title == "Alpha, again"


# --- attach: what is recorded ---------------------------------------------------------------------


def test_attach_records_the_form_the_hash_the_time_and_the_time_to_live() -> None:
    """AC-3. expected_behavior_source: AC-3 ("records form, the SHA-256 of the LF-normalised
    text, retrieved_at from the clock and ttl_days"), ADR-002 decision 9 and the interface
    decision (`retrieved_at` = `services.clock.now().isoformat()`)."""
    text = sound_copy(body="Line one.\nLine two.\n")
    env = alpha_with_a_file(text)

    result = attach(env, form="copy", ttl_days=45, clock=FixedClock(NOW))

    assert result.status == "applied", result.findings
    record = entry_of(registry_of(env), "alpha").stored_copy
    assert record is not None
    assert (record.form, record.ttl_days) == ("copy", 45)
    assert record.sha256 == sha256_hex(text.encode())
    assert record.retrieved_at == NOW.isoformat()


def test_attach_never_changes_the_copy_file() -> None:
    """AC-3. expected_behavior_source: the interface decision ("the copy file is not touched")
    and EC-64 (the stored copy is the team's)."""
    env = alpha_with_a_file()
    before = tree(env.project)

    attach(env)

    assert changed(before, tree(env.project)) == {REGISTRY, LOCK}
    assert read(env, ALPHA_COPY) == sound_copy().encode()


def test_the_hash_is_of_the_text_with_line_feeds_whatever_the_line_endings_of_the_file() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 9 ("records the SHA-256 of the text with
    line endings normalised to LF") and the interface decision ("valid UTF-8 after CRLF is read
    as LF"; `sha256` of "the bytes after replacing CRLF by LF")."""
    lf_text = sound_copy(body="Line one.\nLine two.\n")
    env = alpha_with_a_file(lf_text.replace("\n", "\r\n"))

    result = attach(env)

    assert result.status == "applied", result.findings
    record = entry_of(registry_of(env), "alpha").stored_copy
    assert record is not None
    assert record.sha256 == sha256_hex(lf_text.encode())
    assert read(env, ALPHA_COPY) == lf_text.replace("\n", "\r\n").encode()


def test_a_copy_that_was_attached_passes_validate_resources_and_doctor() -> None:
    """AC-3. expected_behavior_source: AC-3 ("checks the copy as validate resources does"), plan
    P-3 AC-4 (PASS for a sound copy with its record) and plan P-3 AC-5 (doctor reports ORQ-E505
    for a hash that differs: not here)."""
    env = alpha_with_a_file(sound_copy().replace("\n", "\r\n"))
    attach(env, clock=FixedClock(NOW))

    result = validated(env)
    findings = doctor(services_of(env, clock=FixedClock(NOW))).findings

    assert result.verdict is Verdict.PASS, result.findings
    assert "ORQ-E505" not in codes(findings)
    assert [f for f in findings if f.severity is Severity.ERROR] == []


def test_attaching_again_replaces_the_record() -> None:
    """AC-3. expected_behavior_source: the interface decision ("a second attach replaces the
    record")."""
    env = alpha_with_a_file()
    attach(env, form="copy", ttl_days=30, clock=FixedClock(NOW))
    newer = sound_copy(body="Notes taken again, after the page changed.\n")
    put(env, ALPHA_COPY, newer)
    later = NOW + timedelta(days=5)

    result = attach(env, form="summary", ttl_days=60, clock=FixedClock(later))

    assert result.status == "applied", result.findings
    record = entry_of(registry_of(env), "alpha").stored_copy
    assert record is not None
    assert (record.form, record.ttl_days) == ("summary", 60)
    assert record.sha256 == sha256_hex(newer.encode())
    assert record.retrieved_at == later.isoformat()
    assert ids_of(registry_of(env)) == ["alpha"]


@pytest.mark.parametrize("ttl_days", [1, 365])
def test_the_limits_of_the_time_to_live_are_accepted(ttl_days: int) -> None:
    """AC-3. expected_behavior_source: the interface decision ("`ttl_days` outside 1..365 ->
    refused") and ADR-002 decision 1 (`ttl_days` 1 to 365)."""
    env = alpha_with_a_file()

    result = attach(env, ttl_days=ttl_days)

    assert result.status == "applied", result.findings
    record = entry_of(registry_of(env), "alpha").stored_copy
    assert record is not None
    assert record.ttl_days == ttl_days


# --- attach: what is refused ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("form", "ttl_days"),
    [("page", 30), ("", 30), ("COPY", 30), ("copy", 0), ("copy", 366), ("copy", -1)],
    ids=["unknown-form", "empty-form", "capitals", "ttl-0", "ttl-366", "ttl-negative"],
)
def test_a_form_or_a_time_to_live_outside_the_rules_is_refused_with_e509(
    form: str, ttl_days: int
) -> None:
    """AC-3. expected_behavior_source: the interface decision ("`form` must be copy or summary
    and `ttl_days` 1..365 (else refused ORQ-E509)")."""
    env = alpha_with_a_file()
    before, data = tree(env.project), user_data(env)

    result = attach(env, form=form, ttl_days=ttl_days)

    assert result.status == "refused"
    assert REFUSED in codes(result.findings)
    assert tree(env.project) == before
    assert user_data(env) == data


def test_an_attach_to_an_id_that_is_not_there_is_refused_with_e509() -> None:
    """AC-3. expected_behavior_source: the interface decision ("the entry must exist (unknown id
    refused ORQ-E509)")."""
    env = alpha_with_a_file()
    before = tree(env.project)

    result = attach(env, resource_id="gamma")

    assert result.status == "refused"
    assert REFUSED in codes(result.findings)
    assert tree(env.project) == before


def test_a_copy_file_that_is_missing_is_refused_with_e504() -> None:
    """AC-3. expected_behavior_source: the interface decision ("the file
    `docs/resources/<id>.md` must exist (missing: refused with ORQ-E504)")."""
    env = initialised()
    add_entry(env)
    before = tree(env.project)

    result = attach(env)

    assert result.status == "refused"
    assert COPY_MISSING in codes(result.findings)
    assert result.plan is None
    assert tree(env.project) == before


def _a_folder_in_place_of_the_copy(env: Env) -> None:
    env.project.make_dir(path_of(ALPHA_COPY))


def _a_link_in_place_of_the_copy(env: Env) -> None:
    env.project.add_symlink(ALPHA_COPY)


@pytest.mark.parametrize(
    "make_irregular",
    [_a_folder_in_place_of_the_copy, _a_link_in_place_of_the_copy],
    ids=["folder", "symbolic-link"],
)
def test_a_copy_that_is_not_a_regular_file_is_refused_with_an_error_and_nothing_is_written(
    make_irregular: Callable[[Env], None],
) -> None:
    """AC-3. expected_behavior_source: the interface decision ("the file
    `docs/resources/<id>.md` must exist" and "it is checked as `validate resources` checks a
    copy") and ORQLET-SEC-002 (the file system port refuses links). The code is not pinned: a
    folder or a link is not a copy that exists, and the person gets a refusal, not an exception."""
    env = initialised()
    add_entry(env)
    make_irregular(env)
    before = tree(env.project)

    result = attach(env)

    assert result.status == "refused"
    assert any(f.severity is Severity.ERROR for f in result.findings)
    assert result.plan is None
    assert tree(env.project) == before


BAD_COPIES: dict[str, str | bytes] = {
    "without-the-header": "Just notes.\n",
    "with-the-address-of-another-entry": sound_copy("https://docs.example.com/other"),
    "without-the-reference-line": f"Source: {ALPHA_URL}\nNotes.\n",
    "with-a-hidden-code-point": sound_copy(body="before \u200b after\n"),
    "with-a-right-to-left-override": sound_copy(body="before \u202e after\n"),
    "with-a-tag-character": sound_copy(body="before \U000e0041 after\n"),
    "with-an-html-comment": sound_copy(body="<!-- hidden -->\n"),
    "with-a-control-character": sound_copy(body="before \x1b[2J after\n"),
    "with-a-credential-shape": sound_copy(body=f"Use {TOKEN} to sign in.\n"),
    "with-a-private-key-block": sound_copy(body=f"{PEM_DASHES}BEGIN PRIVATE KEY{PEM_DASHES}\n"),
    "with-the-shape-of-a-storage-state-file": sound_copy(body='{"cookies": [], "origins": []}\n'),
    "with-a-line-of-4097-characters": sound_copy(body="x" * 4097 + "\n"),
    "above-64-kib": padded_copy(COPY_LIMIT + 1),
    "that-is-not-utf-8": b"Source: "
    + ALPHA_URL.encode()
    + b"\n"
    + REFERENCE_LINE.encode()
    + b"\n\xff\xfe\n",
}


@pytest.mark.parametrize("name", list(BAD_COPIES), ids=list(BAD_COPIES))
def test_a_copy_that_fails_the_checks_of_validate_resources_is_refused_with_e506(
    name: str,
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("checks the copy as validate resources does"), the
    interface decision ("it is checked as `validate resources` checks a copy: at most 64 KiB,
    valid UTF-8 after CRLF is read as LF, header lines for the entry's address, no hidden code
    point, no credential shape; a failing copy is refused with ORQ-E506") and ADR-002 decision
    9. Each of these copies fails `validate_resources` of phase P-3 with ORQ-E506, which is the
    check of this table."""
    env = alpha_with_a_file(BAD_COPIES[name])
    before, data = tree(env.project), user_data(env)

    result = attach(env)

    assert result.status == "refused"
    assert COPY_FLAGGED in codes(result.findings)
    assert result.plan is None
    assert tree(env.project) == before
    assert user_data(env) == data


def test_a_copy_of_exactly_64_kib_is_accepted_and_one_byte_more_is_not() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 9 ("It is at most 64 KiB") and the
    interface decision ("at most 64 KiB")."""
    exact = alpha_with_a_file(padded_copy(COPY_LIMIT))
    over = alpha_with_a_file(padded_copy(COPY_LIMIT + 1))

    accepted = attach(exact)
    refused = attach(over)

    assert accepted.status == "applied", accepted.findings
    assert refused.status == "refused"
    assert COPY_FLAGGED in codes(refused.findings)


def test_a_finding_about_a_copy_shows_no_part_of_it(capsys: pytest.CaptureFixture[str]) -> None:
    """AC-3. expected_behavior_source: the interface decision ("a failing copy is refused with
    ORQ-E506 and no finding repeats a part of the copy"), ADR-002 decision 9 (findings hold the
    rule name and the line, "never the text") and ORQLET-SEC-003."""
    body = f"visible {TOKEN} text and {OPAQUE} and {MARKER} and {EYJ}{ACCESS_KEY}\n"
    env = alpha_with_a_file(sound_copy(body=body))

    result = attach(env)
    streams = capsys.readouterr()

    assert result.status == "refused"
    for secret in (TOKEN, OPAQUE, MARKER, ACCESS_KEY):
        assert not leaks(shown(result), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


def test_a_login_entry_with_the_form_copy_is_refused_with_e509() -> None:
    """AC-3. expected_behavior_source: the interface decision ("a login entry with form copy is
    refused ORQ-E509") and ADR-002 decisions 1 and 9."""
    env = beta_with_a_file()
    before = tree(env.project)

    result = attach(
        env,
        resource_id="beta",
        form="copy",
        prompter=ScriptedPrompter(interactive=True, confirm_all=True),
    )

    assert result.status == "refused"
    assert REFUSED in codes(result.findings)
    assert tree(env.project) == before


# --- attach: the question for a login entry -------------------------------------------------------


def test_a_login_entry_asks_at_a_terminal_even_with_yes_and_a_yes_applies() -> None:
    """AC-3. expected_behavior_source: AC-3 ("for a login entry asks at a terminal also with
    --yes"), ADR-002 decision 9 and the interface decision ("`prompter.confirm` is called (any
    text) and must be answered yes")."""
    env = beta_with_a_file()
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = attach(env, resource_id="beta", form="summary", prompter=prompter, assume_yes=True)

    assert result.status == "applied", result.findings
    assert prompter.asked
    record = entry_of(registry_of(env), "beta").stored_copy
    assert record is not None
    assert record.form == "summary"


def test_a_no_to_the_question_writes_nothing_and_is_not_applied() -> None:
    """AC-3. expected_behavior_source: the interface decision ("a no answer writes nothing and
    the status is not applied")."""
    env = beta_with_a_file()
    before, data = tree(env.project), user_data(env)
    prompter = ScriptedPrompter(interactive=True, confirm_all=False)

    result = attach(env, resource_id="beta", form="summary", prompter=prompter, assume_yes=True)

    assert result.status != "applied"
    assert prompter.asked
    assert tree(env.project) == before
    assert user_data(env) == data
    assert entry_of(registry_of(env), "beta").stored_copy is None


def test_without_a_terminal_a_login_entry_needs_input_with_e510_even_with_yes() -> None:
    """AC-3. expected_behavior_source: AC-3 ("stops with ORQ-E510 without one") and the
    interface decision ("without a terminal the status is 'needs-input' with ORQ-E510 and
    nothing is written, even with `assume_yes=True`")."""
    env = beta_with_a_file()
    before, data = tree(env.project), user_data(env)

    result = attach(env, resource_id="beta", form="summary", assume_yes=True)

    assert result.status == "needs-input"
    assert NEEDS_A_TERMINAL in codes(result.findings)
    assert tree(env.project) == before
    assert user_data(env) == data


def test_without_a_terminal_and_without_yes_a_login_entry_is_not_applied_either() -> None:
    """AC-3. expected_behavior_source: the interface decision (no terminal: 'needs-input' and
    nothing written; ORQ-E510 or the ORQ-E115 of every command, whichever is said first)."""
    env = beta_with_a_file()
    before = tree(env.project)

    result = attach(env, resource_id="beta", form="summary", assume_yes=False)

    assert result.status == "needs-input"
    assert codes(result.findings) & {NEEDS_A_TERMINAL, NOT_APPLIED}
    assert tree(env.project) == before


def test_at_a_terminal_a_login_entry_without_yes_is_applied_after_a_yes() -> None:
    """AC-3. expected_behavior_source: the interface decision ("`prompter.confirm` is called
    (any text) and must be answered yes"): a yes at a terminal, without `assume_yes`, applies."""
    env = beta_with_a_file()
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = attach(env, resource_id="beta", form="summary", prompter=prompter, assume_yes=False)

    assert result.status == "applied", result.findings
    assert prompter.asked


def test_a_dry_run_of_a_login_entry_asks_nothing_and_writes_nothing() -> None:
    """AC-3. expected_behavior_source: the interface decision ("With dry_run no prompt is needed
    and the status is previewed")."""
    env = beta_with_a_file()
    before, data = tree(env.project), user_data(env)
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = attach(
        env, resource_id="beta", form="summary", prompter=prompter, assume_yes=True, dry_run=True
    )

    assert result.status == "previewed"
    assert prompter.asked == []
    assert tree(env.project) == before
    assert user_data(env) == data


def test_a_dry_run_of_a_public_entry_asks_nothing_and_writes_nothing() -> None:
    """AC-3. expected_behavior_source: the interface decision ("With dry_run no prompt is needed
    and the status is previewed")."""
    env = alpha_with_a_file()
    before = tree(env.project)
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = attach(env, prompter=prompter, assume_yes=False, dry_run=True)

    assert result.status == "previewed"
    assert prompter.asked == []
    assert tree(env.project) == before


def test_a_public_entry_is_never_asked_about_internal_content() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 9 (the question is for "an `access:
    login` entry") and the interface decision (the login rule)."""
    env = alpha_with_a_file()
    prompter = ScriptedPrompter(interactive=True, confirm_all=True)

    result = attach(env, prompter=prompter, assume_yes=True)

    assert result.status == "applied", result.findings
    assert prompter.asked == []
