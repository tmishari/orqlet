"""The registry reaches composition: `init`, `upgrade`, `explain`, `compose` and `data_files` (task
team-conventions-resources, phase P-3).

Every test cites its `expected_behavior_source`. ADR-002 is the file `adr-002-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-8 are the acceptance criteria of phase P-3 in
docs/design/team-conventions-resources/plan.yaml (AC-1 fixes ORQ-E503: init or upgrade refuses an
invalid or recorded-but-missing registry). "The interface decision" is the reading of the plan
author that the Tester of phase P-3 was given, because the ADRs do not spell it out: `init` writes
an empty `.orqlet/resources.yaml` recorded in the lock with owner `seeded`; `upgrade` writes it when
it is absent from disk and from the lock; a registry that fails its contract makes `upgrade`
return the status `refused` with ORQ-E503 before any plan is built and deletes no file, and so does
a registry that is missing from disk while the lock records it; `explain` on an invalid registry
does not refuse and returns its explanation with a finding that names the problem; an edit of the
registry (the current bytes equal the file, the lock record older) causes no proposal on the next
`upgrade`; an interrupted `init` that is run again (profile on disk, no lock) loads the registry on
disk and refuses an invalid one with ORQ-E503 (status `refused`).

These tests were written first, by the Tester of phase P-3, before the composition changed. The
file system is the in-memory fake of tests/fakes and the services are the ones of
tests/support/init_env.py (ORQLET-TEST-001). Credential-shaped text is assembled from parts at run
time and never written as one literal (ORQLET-SEC-003).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message; whether ORQ-E503 also carries the underlying finding of the loader
  (ORQ-E500, ORQ-E501 or ORQ-E502) next to it; the code and the place of the finding that `explain`
  returns (the tests look at every `Finding` of every field of the `Explanation` and accept any of
  ORQ-E500 to ORQ-E503);
- how the bytes of the empty registry are written (only that the file loads as an empty registry);
- the result of `upgrade --check`, of a pending journal (ORQ-E131) or of a downgrade (ORQ-E120) when
  the registry is invalid, and the order of these refusals;
- `explain` for a registry that is missing while the lock records it;
- the first `init` in a directory that holds a registry but no profile;
- whether a partly mentioned CODEOWNERS file silences ORQ-I030 for the paths it does mention.
"""

from __future__ import annotations

import dataclasses
import inspect
from collections.abc import Callable
from pathlib import Path

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.emit import YamlWriter
from orqlet.application.contracts.generated_lock import GeneratedLock, LockedFile
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.explain import Explanation, explain
from orqlet.application.usecases.init_files import contract_bytes
from orqlet.application.usecases.init_project import InitOptions, InitResult, init_project
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.render_all import (
    Composition,
    compose,
    data_files,
    resolve_for,
)
from orqlet.application.usecases.resources_source import load_resources
from orqlet.application.usecases.standards_for import StandardsQuery
from orqlet.application.usecases.upgrade import UpgradeOptions, UpgradeResult, upgrade
from orqlet.domain.changeplan import Desired
from orqlet.domain.digest import sha256_hex
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath
from tests.fakes.vcs import FakeVcs
from tests.support.init_env import Env, tree
from tests.support.trees import repo

pytestmark = pytest.mark.unit

REGISTRY = ".orqlet/resources.yaml"
LOCK = ".orqlet/generated.lock.yaml"
PROFILE = ".orqlet/project-profile.yaml"
REGISTRY_PATH = CanonicalPath.parse(REGISTRY)
REFUSED = "ORQ-E503"  # plan P-3 AC-1: init or upgrade refuses an invalid or missing registry
REGISTRY_CODES = {"ORQ-E500", "ORQ-E501", "ORQ-E502", REFUSED}
LOADER = StrictYamlLoader()
YES = InitOptions(assume_yes=True)
GO = UpgradeOptions(assume_yes=True)
EMPTY = b"schema: orqlet.resources/v1\nresources: []\n"
LIMIT = 256 * 1024
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.resources.v1.yaml"
)
# A registry as a team writes it by hand: a comment, its own spacing and a flow list. A composition
# that serialised the parsed registry again would lose the comment and rewrite the file.
TEAM_REGISTRY = (
    b"# Links of our team\n"
    b"schema: orqlet.resources/v1\n"
    b"resources:\n"
    b"  - id: api-guide\n"
    b"    title: API guidelines\n"
    b"    kind: api-guidelines\n"
    b"    url: https://docs.example.com/api-guidelines\n"
    b"    note: Read before adding or changing an endpoint.\n"
    b"    access: public\n"
    b'    applies_to: {paths: ["src/api/**/*.py"]}\n'
)
ANOTHER_REGISTRY = TEAM_REGISTRY.replace(b"api-guide", b"data-guide").replace(
    b"API guidelines", b"Data guidelines"
)
RESOURCE_FILE = ".claude/rules/orqlet-resource-alpha.md"

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))


# --- helpers --------------------------------------------------------------------------------------


def initialised() -> Env:
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    result = init_project(env.services(), YES)
    assert result.status == "applied"
    return env


def path_of(name: str) -> CanonicalPath:
    return CanonicalPath.parse(name)


def read(env: Env, name: str) -> bytes:
    return env.project.read_bytes(path_of(name))


def lock_of(env: Env) -> GeneratedLock:
    return load_contract(LOADER, GeneratedLock, read(env, LOCK), source=LOCK)


def lock_entry(env: Env, name: str) -> LockedFile | None:
    return next((entry for entry in lock_of(env).files if entry.path == name), None)


def set_lock(env: Env, lock: GeneratedLock) -> None:
    env.project.write_atomic(path_of(LOCK), contract_bytes(YamlWriter(), lock))


def drop_from_lock(env: Env, name: str) -> None:
    lock = lock_of(env)
    kept = tuple(entry for entry in lock.files if entry.path != name)
    set_lock(env, lock.model_copy(update={"files": kept}))


def record_in_lock(env: Env, name: str, content: bytes) -> None:
    """The lock says that Orqlet last wrote `content` to the seeded file `name`."""
    lock = lock_of(env)
    entry = lock_entry(env, name)
    assert entry is not None
    changed = entry.model_copy(update={"seeded_sha256": sha256_hex(content)})
    files = tuple(changed if item.path == name else item for item in lock.files)
    set_lock(env, lock.model_copy(update={"files": files}))


def plant_generated_file(env: Env, name: str, content: bytes) -> None:
    """A file that Orqlet generated earlier and recorded, as a render of the registry would be."""
    env.project.write_atomic(path_of(name), content)
    lock = lock_of(env)
    entry = LockedFile(
        path=name,
        owner=OwnerMode.ORQLET,
        file_class=FileClass.GENERATED,
        rendered_sha256=sha256_hex(content),
    )
    set_lock(env, lock.model_copy(update={"files": (*lock.files, entry)}))


def registry_of(env: Env) -> tuple[Resources | None, tuple[Finding, ...]]:
    return load_resources(env.project, LOADER, REGISTRY)


def proposals(env: Env) -> list[str]:
    return [name for name in tree(env.project) if name.startswith(".orqlet/proposals/")]


def codes(findings: tuple[Finding, ...] | list[Finding]) -> set[str]:
    return {finding.code for finding in findings}


def named(finding: Finding, name: str) -> bool:
    return name in (finding.path or "") or name in finding.message


def shown(findings: tuple[Finding, ...] | list[Finding]) -> str:
    return "\n".join(
        f"{finding.code}\n{finding.message}\n{finding.path}\n{finding!r}" for finding in findings
    )


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters of it in a row (any case)."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def findings_of(explanation: Explanation) -> list[Finding]:
    """Every `Finding` in any field of an explanation: the design does not say which field."""
    found: list[Finding] = []
    for field in dataclasses.fields(explanation):
        value = getattr(explanation, field.name)
        if isinstance(value, Finding):
            found.append(value)
        elif isinstance(value, tuple | list):
            found += [item for item in value if isinstance(item, Finding)]
    return found


def padded_registry(size: int) -> bytes:
    filler = size - len(EMPTY) - 2
    return EMPTY + b"#" + b"x" * filler + b"\n"


def _overwrite(content: bytes) -> Callable[[Env], None]:
    def damage(env: Env) -> None:
        env.project.write_atomic(REGISTRY_PATH, content)

    return damage


def _directory(env: Env) -> None:
    env.project.delete(REGISTRY_PATH)
    env.project.make_dir(REGISTRY_PATH)


def _symbolic_link(env: Env) -> None:
    env.project.add_symlink(REGISTRY)


# The entry of TEAM_REGISTRY twice: a repeated id, which the contract refuses.
CONTRACT_BREAKING = TEAM_REGISTRY + TEAM_REGISTRY.split(b"resources:\n")[1]
# name -> (how to damage the registry of an initialised project, the code of the loader)
INVALID_REGISTRIES: dict[str, tuple[Callable[[Env], None], str]] = {
    "fails-its-contract": (_overwrite(CONTRACT_BREAKING), "ORQ-E501"),
    "refused-by-the-strict-loader": (
        _overwrite(b"schema: orqlet.resources/v1\nresources: &r []\nagain: *r\n"),
        "ORQ-E501",
    ),
    "is-above-256-kib": (_overwrite(padded_registry(LIMIT + 1)), "ORQ-E502"),
    "is-a-directory": (_directory, "ORQ-E500"),
    "is-a-symbolic-link": (_symbolic_link, "ORQ-E500"),
}


def credential_registry() -> bytes:
    """A registry that breaks the contract in several fields and holds credential-shaped values."""
    return (
        b"schema: orqlet.resources/v1\nresources:\n"
        b"  - id: alpha\n"
        b"    title: A guide\n"
        b"    kind: team-docs\n"
        + f"    url: https://docs.example.com/guide?token={TOKEN}\n".encode()
        + f"    note: use `{OPAQUE}` first\n".encode()
        + b"    access: public\n"
    )


def composed(env: Env, resources_bytes: bytes) -> Composition:
    """`compose` for the installed project with the registry that `resources_bytes` holds."""
    services = env.services()
    inst = load_installation(services)
    resources = load_contract(LOADER, Resources, resources_bytes, source="registry")
    return compose(
        services,
        inst.profile,
        resolve_for(services, inst.profile),
        resources,
        clients=inst.profile.clients.enabled,
        prompts_dir=".prompts",
        pr_targets=inst.profile.repository.pull_requests.template.targets,
        profile_bytes=read(env, PROFILE),
        resources_bytes=resources_bytes,
    )


# --- init: an empty registry, seeded --------------------------------------------------------------


def test_init_writes_an_empty_registry_that_loads_as_an_empty_registry() -> None:
    """AC-2. expected_behavior_source: AC-2 ("init writes an empty .orqlet/resources.yaml recorded
    as seeded"), ADR-002 decisions 1 and 6 and EC-61 ("written empty by init")."""
    env = initialised()

    registry, findings = registry_of(env)

    assert REGISTRY in tree(env.project)
    assert findings == ()
    assert registry is not None
    assert registry.resources == ()


def test_init_records_the_registry_in_the_lock_as_a_seeded_file_with_its_hash() -> None:
    """AC-2. expected_behavior_source: AC-2 and EC-61 ("A seeded file, owner seeded and no file
    class, ... recorded in the lock")."""
    env = initialised()

    entry = lock_entry(env, REGISTRY)

    assert entry is not None
    assert entry.owner is OwnerMode.SEEDED
    assert entry.file_class is None
    assert entry.rendered_sha256 is None
    assert entry.seeded_sha256 == sha256_hex(read(env, REGISTRY))


def test_a_dry_run_of_init_plans_the_registry_and_writes_nothing() -> None:
    """AC-2. expected_behavior_source: AC-2, ORQLET-SAFE-001 (every write goes through a plan the
    person can preview) and ADR-002 decision 6 ("the bytes are written in the one plan of
    `init`")."""
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    before = tree(env.project)

    result = init_project(env.services(), InitOptions(dry_run=True))

    assert result.status == "previewed"
    assert result.plan is not None
    created = {str(write.path) for write in result.plan.writes if write.kind == "create"}
    assert REGISTRY in created
    assert tree(env.project) == before


def test_init_plans_the_registry_after_the_profile_and_before_the_lock() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 6 ("The plan writes the profile before the
    registry"; the registry is in the one plan of `init`) and ORQLET-SAFE-001 ("the manifest is
    written last")."""
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))

    result = init_project(env.services(), YES)

    assert result.plan is not None
    order = [str(write.path) for write in result.plan.writes]
    assert order.index(PROFILE) < order.index(REGISTRY) < order.index(LOCK)
    assert order[-1] == LOCK


def test_the_journal_of_init_holds_the_registry_with_the_other_files() -> None:
    """AC-2. expected_behavior_source: ORQLET-SAFE-001 (every write goes through a journalled
    change plan) and ADR-002 decision 6 (the registry is written in the one plan of `init`)."""
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))

    result = init_project(env.services(), YES)

    journal = next(
        value
        for key, value in env.user_data.snapshot().items()
        if key.endswith(f"{result.change_id}.json")
    )
    assert REGISTRY.encode() in journal


# --- init run again after an interruption ---------------------------------------------------------


def interrupted(env: Env) -> None:
    """The state of an `init` that stopped before it wrote the lock: the profile, no lock."""
    env.project.delete(path_of(LOCK))


def test_an_init_that_is_run_again_keeps_the_registry_that_is_on_disk() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 6 ("a re-run after an interruption reads
    what is on disk, as `_load_existing_profile` does for the profile") and EC-61 ("composition
    receives its current bytes")."""
    env = initialised()
    env.project.write_atomic(REGISTRY_PATH, TEAM_REGISTRY)
    interrupted(env)

    result = init_project(env.services(), YES)

    assert result.status == "applied"
    assert read(env, REGISTRY) == TEAM_REGISTRY
    assert proposals(env) == []
    entry = lock_entry(env, REGISTRY)
    assert entry is not None
    assert entry.seeded_sha256 == sha256_hex(TEAM_REGISTRY)


@pytest.mark.parametrize("name", list(INVALID_REGISTRIES), ids=list(INVALID_REGISTRIES))
def test_an_init_that_is_run_again_refuses_an_invalid_registry_and_writes_nothing(
    name: str,
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("An invalid registry stops init (re-run) and upgrade
    with the status refused and ORQ-E503 before any plan is built"), ADR-002 decision 6 and the
    interface decision ("`init` returns its result with status `refused`")."""
    damage, _ = INVALID_REGISTRIES[name]
    env = initialised()
    damage(env)
    interrupted(env)
    before = tree(env.project)

    result = init_project(env.services(), YES)

    assert result.status == "refused"
    assert REFUSED in codes(result.findings)
    assert result.plan is None
    assert tree(env.project) == before
    assert LOCK not in tree(env.project)


def test_the_refusal_of_a_re_run_of_init_names_the_registry_and_shows_no_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-3. expected_behavior_source: AC-3, plan P-3 AC-1 (ORQ-E503), ADR-002 decision 10 and
    ORQLET-SEC-003 (no finding holds a part of an input value)."""
    env = initialised()
    env.project.write_atomic(REGISTRY_PATH, credential_registry())
    interrupted(env)

    result = init_project(env.services(), YES)

    refusal = [finding for finding in result.findings if finding.code == REFUSED]
    assert refusal
    assert all(finding.severity is Severity.ERROR for finding in refusal)
    assert any(named(finding, REGISTRY) for finding in refusal)
    streams = capsys.readouterr()
    for secret in (TOKEN, OPAQUE):
        assert not leaks(shown(result.findings), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


# --- upgrade: writing the registry ----------------------------------------------------------------


def test_an_upgrade_writes_the_registry_when_it_is_absent_from_disk_and_from_the_lock() -> None:
    """AC-2. expected_behavior_source: AC-2 ("upgrade writes it when absent"), ADR-002 decisions 1
    and 6 ("a registry that is missing and not recorded is an empty one"; "`upgrade` (when
    absent)") and the interface decision ("`upgrade` writes it when it is absent from disk and from
    the lock")."""
    env = initialised()
    env.project.delete(REGISTRY_PATH)
    drop_from_lock(env, REGISTRY)
    assert lock_entry(env, REGISTRY) is None

    result = upgrade(env.services(), GO)

    assert result.status == "applied"
    assert result.plan is not None
    assert (REGISTRY, "create") in {(str(w.path), w.kind) for w in result.plan.writes}
    registry, findings = registry_of(env)
    assert findings == ()
    assert registry is not None
    assert registry.resources == ()
    entry = lock_entry(env, REGISTRY)
    assert entry is not None
    assert entry.owner is OwnerMode.SEEDED
    assert entry.seeded_sha256 == sha256_hex(read(env, REGISTRY))


def test_an_upgrade_after_that_changes_nothing() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 5 (the classification of a seeded file
    converges) and ORQLET-SAFE-001 ("a re-run converges")."""
    env = initialised()
    env.project.delete(REGISTRY_PATH)
    drop_from_lock(env, REGISTRY)
    upgrade(env.services(), GO)
    before = tree(env.project)

    again = upgrade(env.services(), GO)

    assert again.status == "up-to-date"
    assert tree(env.project) == before


def test_an_upgrade_leaves_a_registry_that_the_lock_records_as_it_is() -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 6 ("`compose` takes `resources` and
    `resources_bytes`") and EC-61 ("composition receives its current bytes"): the bytes of the file
    reach `compose` as they are, so a registry that the team wrote and recorded makes no
    proposal."""
    env = initialised()
    env.project.write_atomic(REGISTRY_PATH, TEAM_REGISTRY)
    record_in_lock(env, REGISTRY, TEAM_REGISTRY)
    before = tree(env.project)

    result = upgrade(env.services(), GO)

    assert result.status == "up-to-date"
    assert tree(env.project) == before


@pytest.mark.parametrize(
    "recorded",
    [EMPTY, ANOTHER_REGISTRY],
    ids=["the-lock-is-older", "the-lock-line-comes-from-another-branch"],
)
def test_an_edit_of_the_registry_makes_no_proposal_and_the_next_upgrade_advances_the_record(
    recorded: bytes,
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("an edit made through the commands or by hand (current
    equal to the file, record older) causes no proposal"), ADR-002 decision 5 ("A hand edit, or two
    branches that each added a link and a lock that was merged either way, then needs no proposal
    and no repair"; "until then `upgrade --check` exits 1 ('available'), which is intended";
    `upgrade` "advances the lock") and the interface decision."""
    env = initialised()
    env.project.write_atomic(REGISTRY_PATH, TEAM_REGISTRY)
    record_in_lock(env, REGISTRY, recorded)
    edited = tree(env.project)

    check = upgrade(env.services(), UpgradeOptions(check=True))
    assert check.status == "available"
    assert tree(env.project) == edited

    result = upgrade(env.services(), GO)

    assert result.status == "applied"
    assert proposals(env) == []
    assert read(env, REGISTRY) == TEAM_REGISTRY
    entry = lock_entry(env, REGISTRY)
    assert entry is not None
    assert entry.seeded_sha256 == sha256_hex(TEAM_REGISTRY)
    assert upgrade(env.services(), GO).status == "up-to-date"


def test_an_upgrade_never_changes_or_deletes_a_stored_copy() -> None:
    """AC-2. expected_behavior_source: EC-64 ("never deleted by Orqlet") and ADR-002 decision 7
    ("The stored copy is the team's: Orqlet never deletes it"): a copy whose entry is gone and a
    copy of an entry survive an upgrade."""
    env = initialised()
    env.project.write_atomic(path_of("docs/resources/gone.md"), b"a copy whose entry is gone\n")
    env.project.write_atomic(path_of("docs/resources/api-guide.md"), b"a copy\n")
    env.project.write_atomic(REGISTRY_PATH, TEAM_REGISTRY)
    record_in_lock(env, REGISTRY, TEAM_REGISTRY)
    before = tree(env.project)

    upgrade(env.services(), GO)

    assert tree(env.project) == before


# --- upgrade: a registry that is invalid or missing is refused before any plan --------------------


def test_the_planted_generated_file_is_an_orphan_that_an_upgrade_would_delete() -> None:
    """AC-3 (control for the tests below). expected_behavior_source: ADR-002 decision 6 ("an empty
    registry would make every recorded `orqlet-resource-*` ... file an orphan and delete it") and
    changeplan.py (a recorded file that is no longer wanted and is unchanged is removed). No file is
    rendered from the registry in phase P-3, so the test records one by hand."""
    env = initialised()
    plant_generated_file(env, RESOURCE_FILE, b"generated from a resource\n")

    result = upgrade(env.services(), UpgradeOptions(check=True))

    assert result.plan is not None
    assert (RESOURCE_FILE, "delete") in {(str(w.path), w.kind) for w in result.plan.writes}


@pytest.mark.parametrize("name", list(INVALID_REGISTRIES), ids=list(INVALID_REGISTRIES))
def test_an_upgrade_refuses_an_invalid_registry_before_any_plan_and_deletes_nothing(
    name: str,
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("An invalid registry stops init (re-run) and upgrade
    with the status refused and ORQ-E503 before any plan is built and no file is deleted"),
    ADR-002 decision 6 ("`upgrade` ... refuse before any plan is built, because an empty registry
    would make every recorded `orqlet-resource-*`, `orqlet-tool-*` and `orqlet-resources` file an
    orphan and delete it (a test shows that nothing is deleted)") and the interface decision."""
    damage, _ = INVALID_REGISTRIES[name]
    env = initialised()
    plant_generated_file(env, RESOURCE_FILE, b"generated from a resource\n")
    damage(env)
    before = tree(env.project)

    result = upgrade(env.services(), GO)

    assert result.status == "refused"
    assert REFUSED in codes(result.findings)
    assert result.plan is None
    assert tree(env.project) == before
    assert RESOURCE_FILE in tree(env.project)


def test_the_refusal_of_an_upgrade_names_the_registry_and_shows_no_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-3. expected_behavior_source: AC-3, plan P-3 AC-1 (ORQ-E503), ADR-002 decision 10 and
    ORQLET-SEC-003."""
    env = initialised()
    env.project.write_atomic(REGISTRY_PATH, credential_registry())

    result = upgrade(env.services(), GO)

    refusal = [finding for finding in result.findings if finding.code == REFUSED]
    assert result.status == "refused"
    assert refusal
    assert all(finding.severity is Severity.ERROR for finding in refusal)
    assert any(named(finding, REGISTRY) for finding in refusal)
    streams = capsys.readouterr()
    for secret in (TOKEN, OPAQUE):
        assert not leaks(shown(result.findings), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


def test_an_upgrade_refuses_a_registry_that_is_missing_while_the_lock_records_it() -> None:
    """AC-3. expected_behavior_source: AC-3 ("a registry that is missing while the lock records it
    is refused the same way"), ADR-002 decision 6 ("A registry that is missing while the lock
    records it is refused in the same way") and the interface decision."""
    env = initialised()
    plant_generated_file(env, RESOURCE_FILE, b"generated from a resource\n")
    assert lock_entry(env, REGISTRY) is not None
    env.project.delete(REGISTRY_PATH)
    before = tree(env.project)

    result = upgrade(env.services(), GO)

    assert result.status == "refused"
    assert REFUSED in codes(result.findings)
    assert result.plan is None
    assert tree(env.project) == before
    assert RESOURCE_FILE in tree(env.project)


def test_the_refusal_of_a_missing_registry_names_the_registry_and_a_way_out() -> None:
    """AC-3. expected_behavior_source: AC-3 ("the finding names the way out") and ADR-002
    decision 6 ("the finding says to restore the file from Git or to write an empty valid one
    (`schema: orqlet.resources/v1` and `resources: []`) and then remove entries with `orqlet
    resources remove`"). The wording is not pinned: the message must name the registry and hold at
    least one phrase of that sentence."""
    env = initialised()
    env.project.delete(REGISTRY_PATH)

    result = upgrade(env.services(), GO)

    refusal = [finding for finding in result.findings if finding.code == REFUSED]
    assert refusal
    assert any(named(finding, REGISTRY) for finding in refusal)
    text = " ".join(finding.message for finding in refusal).lower()
    assert any(phrase in text for phrase in ("git", "resources: []", "resources remove"))


def test_writing_an_empty_valid_registry_is_a_way_out_of_the_refusal() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 ("restore the file from Git or ... write
    an empty valid one (`schema: orqlet.resources/v1` and `resources: []`)")."""
    env = initialised()
    env.project.delete(REGISTRY_PATH)
    assert upgrade(env.services(), GO).status == "refused"

    env.project.write_atomic(REGISTRY_PATH, EMPTY)
    result = upgrade(env.services(), GO)

    assert result.status in {"up-to-date", "applied"}
    assert REFUSED not in codes(result.findings)
    assert proposals(env) == []


def test_a_registry_that_is_missing_and_not_recorded_is_an_empty_one_and_not_a_refusal() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 ("a registry that is missing and not
    recorded is an empty one")."""
    env = initialised()
    env.project.delete(REGISTRY_PATH)
    drop_from_lock(env, REGISTRY)

    result = upgrade(env.services(), UpgradeOptions(check=True))

    assert result.status == "available"
    assert REFUSED not in codes(result.findings)


# --- explain: it previews and prints the finding --------------------------------------------------


QUERY = StandardsQuery(phase="design")


def test_explain_of_a_valid_registry_reports_no_registry_problem() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (`explain` "prints the finding" only
    when the registry is invalid)."""
    env = initialised()

    assert not codes(findings_of(explain(env.services(), QUERY))) & REGISTRY_CODES


@pytest.mark.parametrize("name", list(INVALID_REGISTRIES), ids=list(INVALID_REGISTRIES))
def test_explain_of_an_invalid_registry_does_not_refuse_and_prints_the_finding(name: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("explain previews without resource files and prints
    the finding"), ADR-002 decision 6 ("`explain` builds no plan and so cannot delete anything, so
    it does not refuse: it previews without the resource files and prints the finding") and the
    interface decision ("returns its explanation and a finding that names the problem")."""
    damage, loader_code = INVALID_REGISTRIES[name]
    healthy = explain(initialised().services(), QUERY)
    env = initialised()
    damage(env)
    before = tree(env.project)

    explanation = explain(env.services(), QUERY)

    assert codes(findings_of(explanation)) & {loader_code, REFUSED}
    assert explanation.declared == healthy.declared
    assert explanation.generated == healthy.generated
    assert explanation.rules == healthy.rules
    assert explanation.limits == healthy.limits
    assert explanation.uninspectable == healthy.uninspectable
    assert tree(env.project) == before


def test_the_finding_of_explain_shows_no_part_of_an_input_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 10 and ORQLET-SEC-003 (no finding holds a
    part of an input value), through `explain`."""
    env = initialised()
    env.project.write_atomic(REGISTRY_PATH, credential_registry())

    registry_findings = [
        finding
        for finding in findings_of(explain(env.services(), QUERY))
        if finding.code in REGISTRY_CODES
    ]
    streams = capsys.readouterr()

    assert registry_findings
    for secret in (TOKEN, OPAQUE):
        assert not leaks(shown(registry_findings), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


# --- compose and data_files -----------------------------------------------------------------------


def test_compose_takes_the_registry_and_its_bytes_next_to_the_profile_and_its_bytes() -> None:
    """AC-7. expected_behavior_source: EC-50 (`def compose(services, profile, resolution,
    resources, *, clients, prompts_dir, pr_targets, profile_bytes, resources_bytes, orqlet_owned,
    released, released_record) -> Composition`)."""
    parameters = inspect.signature(compose).parameters

    assert list(parameters) == [
        "services",
        "profile",
        "resolution",
        "resources",
        "clients",
        "prompts_dir",
        "pr_targets",
        "profile_bytes",
        "resources_bytes",
        "orqlet_owned",
        "released",
        "released_record",
    ]
    keyword_only = {
        name for name, p in parameters.items() if p.kind is inspect.Parameter.KEYWORD_ONLY
    }
    assert keyword_only == set(list(parameters)[4:])
    assert parameters["resources"].default is inspect.Parameter.empty
    assert parameters["resources_bytes"].default is inspect.Parameter.empty


def test_data_files_takes_the_bytes_of_the_registry_before_the_resolution() -> None:
    """AC-7. expected_behavior_source: EC-51 (`def data_files(services, profile_bytes,
    resources_bytes, resolution) -> list[Desired]`)."""
    parameters = inspect.signature(data_files).parameters

    assert list(parameters) == ["services", "profile_bytes", "resources_bytes", "resolution"]
    assert parameters["resources_bytes"].default is inspect.Parameter.empty


def test_data_files_seeds_the_registry_with_the_bytes_it_is_given() -> None:
    """AC-2. expected_behavior_source: EC-51 and EC-61 ("A seeded file, owner seeded and no file
    class") and ADR-002 decision 6 (composition receives the registry's current bytes)."""
    env = initialised()
    services = env.services()
    inst = load_installation(services)
    resolution = resolve_for(services, inst.profile)

    desired = data_files(services, read(env, PROFILE), TEAM_REGISTRY, resolution)

    (registry,) = [item for item in desired if item.path == REGISTRY_PATH]
    assert registry.owner is OwnerMode.SEEDED
    assert registry.file_class is None
    assert registry.content == TEAM_REGISTRY
    profile = next(item for item in desired if str(item.path) == PROFILE)
    assert profile.content == read(env, PROFILE)


@pytest.mark.parametrize(
    "content",
    [EMPTY, TEAM_REGISTRY, FIXTURE.read_bytes()],
    ids=["empty", "written-by-hand", "fixture"],
)
def test_compose_passes_the_bytes_of_the_registry_through_unchanged(content: bytes) -> None:
    """AC-2. expected_behavior_source: EC-50, EC-61 and ADR-002 decision 6 ("`compose` takes
    `resources` and `resources_bytes` next to `profile` and `profile_bytes`"; a seeded file whose
    current bytes are given is kept, not rewritten)."""
    env = initialised()

    composition = composed(env, content)

    (registry,) = [item for item in composition.desired if item.path == REGISTRY_PATH]
    assert registry.content == content
    assert registry.owner is OwnerMode.SEEDED
    assert registry.file_class is None


def test_nothing_is_rendered_from_the_registry_in_this_phase() -> None:
    """AC-7. expected_behavior_source: plan P-3 objective ("nothing is rendered from it yet"),
    completion ("No client file is rendered from the registry in this phase") and AC-7 ("The
    resources parameter of compose is acknowledged with del and unused until P-6"): a registry with
    a path-scoped entry, a tool entry and stored copies gives the same files as the empty
    registry, except for the registry file itself. This test belongs to phase P-3 and is replaced
    in phase P-6."""
    env = initialised()

    without = composed(env, EMPTY)
    with_links = composed(env, FIXTURE.read_bytes())

    def others(composition: Composition) -> list[Desired]:
        return [item for item in composition.desired if item.path != REGISTRY_PATH]

    assert others(with_links) == others(without)
    assert with_links.findings == without.findings


# --- AC-8: the code-owners notice -----------------------------------------------------------------


NOTICE_PATHS = (".orqlet/**", "docs/resources/**", ".github/workflows/**", "AGENTS.md")


def notice_text(result: InitResult | UpgradeResult) -> str:
    return " ".join(f.message for f in result.findings if f.code == "ORQ-I030")


def test_the_codeowners_notice_names_the_new_paths() -> None:
    """AC-8. expected_behavior_source: AC-8 ("The code-owners notice ORQ-I030 names the registry,
    the stored copies, the generated paths and the workflow files when no CODEOWNERS entry mentions
    them") and ADR-002 decision 11 (`.orqlet/**`, `docs/resources/**`, "the generated rule, skill
    and `AGENTS.md` paths and `.github/workflows/**`")."""
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))

    result = init_project(env.services(), YES)

    notice = [finding for finding in result.findings if finding.code == "ORQ-I030"]
    assert notice
    assert all(finding.severity is Severity.INFO for finding in notice)
    text = notice_text(result)
    for path in (*NOTICE_PATHS, ".prompts"):
        assert path in text, path
    assert any(root in text for root in (".claude/", ".cursor/", ".agents/", ".codex/"))
    assert not any("CODEOWNERS" in name for name in tree(env.project))


def test_the_codeowners_notice_is_silent_when_a_codeowners_entry_mentions_every_path() -> None:
    """AC-8. expected_behavior_source: AC-8 ("when no CODEOWNERS entry mentions them") and ADR-002
    decision 11. The file mentions each path in the folder form and in the glob form: the unit
    under test decides what 'mentions' means, so the test gives it every reading."""
    env = Env(project=repo("uv_fastapi"), vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"))
    owned = (
        ".prompts",
        ".orqlet",
        "docs/resources",
        ".github/workflows",
        ".claude",
        ".claude/rules",
        ".claude/skills",
        ".claude/agents",
        ".cursor",
        ".cursor/rules",
        ".cursor/agents",
        ".agents",
        ".agents/skills",
        ".codex",
        ".codex/agents",
    )
    lines = [f"/{name}/ @team" for name in owned] + [f"{name}/** @team" for name in owned]
    lines.append("/AGENTS.md @team")
    env.project.write_atomic(path_of(".github/CODEOWNERS"), ("\n".join(lines) + "\n").encode())

    result = init_project(env.services(), YES)

    assert "ORQ-I030" not in codes(result.findings)


def test_the_codeowners_notice_of_an_upgrade_names_the_same_paths() -> None:
    """AC-8. expected_behavior_source: ADR-002 decision 11 (one notice, extended; `init`, `upgrade`
    and `doctor` all raise it through `environment_findings`)."""
    env = initialised()

    result = upgrade(env.services(), UpgradeOptions(check=True))

    text = notice_text(result)
    for path in NOTICE_PATHS:
        assert path in text, path
