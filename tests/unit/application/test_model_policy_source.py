"""The loader of the model policy file (task dynamic-model-profiles, phase P-2).

It covers `model_policy_path`, `load_model_policy` and `read_model_policy_at`.

Every test cites its `expected_behavior_source`. AC-1 to AC-5 are the acceptance criteria of phase
P-2 in docs/design/dynamic-model-profiles/plan.yaml (AC-6 is the import-linter check and AC-7 the
gate check; the Coder runs both). BC-n and C-n are the behaviour and constraint rows of
design/component.md, and ADR-002, ADR-005 and ADR-007 are the decision records next to it.

These tests were written first, by the Tester of phase P-2 on 2026-11-05, before
`orqlet.application.usecases.model_policy_source` existed. The plan names the two entry points
and the four states. The names `PolicyAbsent`, `PolicyLoaded`, `PolicyInvalid`, `PolicyDeleted`,
`PolicyState` and `PolicyServices`, the codes ORQ-E540 (unreadable or refused by the strict
reading rules), ORQ-E541 (contract) and ORQ-E542 (credential scan), and the form of the messages
come from the brief of this phase's Tester, which is the design of the public API. A policy is a
copy of the valid fixture (tests/fixtures/contracts/valid/orqlet.model-policy.v2.yaml) that a
test changes, never the fixture itself. The files are written as JSON text, which is YAML.
Credential-shaped text is assembled from fragments at run time and none is written as one literal
(ORQLET-SEC-003). The file system is the in-memory fake and the VCS is `FakeVcs` (ORQLET-TEST-001);
the recording wrappers of the two are in this file, because tests/fakes is not changed.

Behaviour that the plan and the brief leave open is deliberately not pinned here:
- the wording of a message: only the fixed text of a v1 file is exact; an ORQ-E541 message holds
  the field path and the rule, an ORQ-E542 message holds the rule and `line N`, and neither holds
  a marker, a key or a value of the file;
- the code for a path that is a directory, a link or not a regular file, a link above the file, a
  read that fails and a `VcsError`: the tests say `PolicyInvalid` and keep the one assertion on
  ORQ-E540 for these causes in its own test, so it is easy to change;
- the code for a document that the strict loader reads and that is no mapping (an empty file, a
  list, a scalar): ORQ-E540 and ORQ-E541 are both accepted;
- whether a file that fails its contract and also holds a key shape is given ORQ-E542 as well;
- whether the size is checked before the loader runs (only that 262144 bytes load and 262145 do
  not);
- the order of the findings of one file, and the order in which the contract is checked;
- how the lock names the path (its spelling or letter case): only the exact path is a row;
- what a link to the lock, a lock above 256 KiB or a lock with two rows for the path gives.
"""

from __future__ import annotations

import copy
import dataclasses
import functools
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, get_args

import pytest
from pydantic import ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import (
    FileKind,
    FileSystem,
    FileSystemError,
    PathNotFound,
)
from orqlet.application.ports.vcs import CommitSummary, Vcs, VcsError
from orqlet.application.usecases.model_policy_source import (
    PolicyAbsent,
    PolicyDeleted,
    PolicyInvalid,
    PolicyLoaded,
    PolicyServices,
    PolicyState,
    load_model_policy,
    model_policy_path,
    read_model_policy_at,
)
from orqlet.application.usecases.services import Services
from orqlet.application.usecases.validation import ValidateServices
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.model_policy_scan import find_policy_credentials
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs

pytestmark = pytest.mark.unit

type Where = tuple[str | int, ...]

PATH = ".orqlet/model-policy.yaml"
LOCK = ".orqlet/generated.lock.yaml"
LIMIT = 256 * 1024  # a file of 262144 bytes is not above the limit; 262145 bytes is
UNREADABLE = "ORQ-E540"  # unreadable, or refused by the strict reading rules
CONTRACT = "ORQ-E541"  # the contract fails
CREDENTIAL = "ORQ-E542"  # the credential scan finds something in a file whose contract passed
V1_TEXT = "a v1 file; migrate"
UNKNOWN_KEY = "unknown-key"
DOCUMENT = "(document)"
SCHEMA_ID = "orqlet.model-policy/v2"
TREE = "a" * 40  # a full object id, as `read_at` accepts
OTHER_TREE = "b" * 40
STAGED_TREE = "c" * 40
COMMIT = "d" * 40
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.model-policy.v2.yaml"
)
LOADER = StrictYamlLoader()
MARKER = re.compile(r"marker-[a-z0-9-]+")
HEADER = b"schema: orqlet.model-policy/v2"

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------


def body(size: int, unit: str = "aB3") -> str:
    """A deterministic run of `size` key characters."""
    return (unit * (size // len(unit) + 1))[:size]


KEYS = {
    "sk-key": "s" + "k-" + body(24),
    "xai-key": "xa" + "i-" + body(24),
    "aiza-key": "AI" + "za" + body(35),
    "github-token": "".join(("gh", "p_", body(36))),
}
KEY_RULES = {
    "sk-key": "sk-key-prefix",
    "xai-key": "xai-key-prefix",
    "aiza-key": "aiza-key-prefix",
    "github-token": "token-prefix",
}

# --- the services of the tests ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FakeServices:
    """The three ports that the loader needs, and nothing else."""

    project: FileSystem
    vcs: Vcs
    loader: DocumentLoader


def make_services(
    project: FileSystem | None = None,
    vcs: Vcs | None = None,
    loader: DocumentLoader | None = None,
) -> FakeServices:
    return FakeServices(
        project=MemoryFileSystem() if project is None else project,
        vcs=FakeVcs() if vcs is None else vcs,
        loader=LOADER if loader is None else loader,
    )


def _fake_services_fit_the_protocol(fake: FakeServices) -> PolicyServices:
    """Never called: mypy checks that a bundle of the three ports is a `PolicyServices`."""
    return fake


def _real_service_bundles_fit_the_protocol(
    services: Services, validating: ValidateServices
) -> None:
    """Never called: mypy checks that both bundles of the product are a `PolicyServices`."""
    load_model_policy(services)
    load_model_policy(validating)
    read_model_policy_at(services, TREE)
    read_model_policy_at(validating, TREE)


_QUIET = frozenset({"accessed", "forget", "reads"})


class Recorded:
    """A mixin that remembers the name of every public attribute looked up on the object."""

    accessed: list[str]

    def __getattribute__(self, name: str) -> Any:
        if not name.startswith("_") and name not in _QUIET:
            object.__getattribute__(self, "accessed").append(name)
        return object.__getattribute__(self, name)

    def forget(self) -> None:
        """Drop what was recorded so far, such as the set-up of a test."""
        self.accessed.clear()


class RecordingFileSystem(Recorded, MemoryFileSystem):
    def __init__(self) -> None:
        self.accessed = []
        super().__init__()


class RecordingVcs(Recorded, FakeVcs):
    def __init__(self, revisions: dict[str, dict[str, bytes]] | None = None) -> None:
        self.accessed = []
        self.reads: list[tuple[str, str]] = []
        super().__init__(revisions=revisions)

    def read_at(self, revision: str, path: str) -> bytes | None:
        self.reads.append((revision, path))
        return super().read_at(revision, path)


class FailingVcs(FakeVcs):
    """A VCS whose read fails, with a message that holds a marker."""

    def read_at(self, revision: str, path: str) -> bytes | None:
        raise VcsError("marker-vcs-error")


class FaultyFileSystem(MemoryFileSystem):
    """A memory file system in which one path can fail a lookup or a read, or look odd."""

    def __init__(self) -> None:
        super().__init__()
        self._broken: str | None = None
        self._forced: FileKind | None = None
        self._kind_error: Exception | None = None
        self._read_error: Exception | None = None

    def break_path(
        self,
        path: str,
        *,
        forced: FileKind | None = None,
        kind_error: Exception | None = None,
        read_error: Exception | None = None,
    ) -> None:
        self._broken = str(CanonicalPath.parse(path))
        self._forced = forced
        self._kind_error = kind_error
        self._read_error = read_error

    def kind(self, path: CanonicalPath) -> FileKind | None:
        if str(path) == self._broken:
            if self._kind_error is not None:
                raise self._kind_error
            if self._forced is not None:
                return self._forced
        return super().kind(path)

    def read_bytes(self, path: CanonicalPath) -> bytes:
        if str(path) == self._broken and self._read_error is not None:
            raise self._read_error
        return super().read_bytes(path)


class CountingLoader:
    """The strict loader, remembering every document it is asked to parse."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._inner = StrictYamlLoader()

    def load(self, data: bytes, *, source: str) -> object:
        self.calls.append(source)
        return self._inner.load(data, source=source)


class RefusingLoader:
    """A loader that refuses every document, with a message that holds a marker."""

    def load(self, data: bytes, *, source: str) -> object:
        raise DocumentError(f"{source}: marker-loader-error")


class StubLoader:
    """A loader that hands back the data it was given, whatever the bytes are."""

    def __init__(self, data: object) -> None:
        self._data = data

    def load(self, data: bytes, *, source: str) -> object:
        return copy.deepcopy(self._data)


# --- documents -------------------------------------------------------------------------


@functools.cache
def _fixture_as_read() -> dict[str, Any]:
    loaded = LOADER.load(FIXTURE.read_bytes(), source=FIXTURE.name)
    assert isinstance(loaded, dict)
    return loaded


def fixture() -> dict[str, Any]:
    """The valid fixture as plain data, which a test may change freely."""
    return copy.deepcopy(_fixture_as_read())


def document(data: dict[str, Any]) -> bytes:
    """A document as JSON text, one key per line, which the strict loader reads as YAML."""
    return json.dumps(data, indent=2).encode()


def valid_bytes() -> bytes:
    return document(fixture())


def mutated(change: Callable[[dict[str, Any]], object]) -> bytes:
    """The valid document after `change` has edited a copy of its data."""
    data = fixture()
    change(data)
    return document(data)


def reach(node: Any, where: Where) -> Any:
    for step in where:
        node = node[step]
    return node


def set_at(data: dict[str, Any], where: Where, value: object) -> None:
    reach(data, where[:-1])[where[-1]] = value


def yaml_lines(*items: bytes) -> bytes:
    return b"\n".join(items) + b"\n"


PADDING_LINE = b"# marker-padding-1 " + b"x" * 44 + b"\n"  # exactly 64 bytes


def padded(size: int) -> bytes:
    """The valid policy followed by comment lines, so that the file has exactly `size` bytes.

    The lines are short, so the cap of 4096 characters per line of the scan cannot object.
    """
    base = valid_bytes() + b"\n"
    filler = size - len(base)
    assert filler >= 0
    lines, rest = divmod(filler, len(PADDING_LINE))
    tail = b"" if rest == 0 else (b"\n" if rest == 1 else b"#" + b"x" * (rest - 2) + b"\n")
    result = base + PADDING_LINE * lines + tail
    assert len(result) == size
    return result


def duplicated_family() -> bytes:
    """The valid policy with the `family` key of its first model written twice."""
    text = valid_bytes()
    doubled = text.replace(
        b'"family": "example-family",',
        b'"family": "example-family",\n      "family": "again",',
        1,
    )
    assert doubled != text
    return doubled


def expected_policy(raw: bytes) -> ModelPolicy:
    """What the contract loader makes of the same bytes."""
    return load_contract(LOADER, ModelPolicy, raw, source="expected")


def v1_document() -> bytes:
    """A minimal document of the retired v1 shape, with a marker in every value."""
    return document(
        {
            "schema": "orqlet.model-policy/v1",
            "status": "draft",
            "excluded": ["marker-v1-excluded-1"],
            "models": [{"id": "marker-v1-model-1", "note": "marker-v1-note-1"}],
        }
    )


# --- the lock --------------------------------------------------------------------------

SEEDED_ROW = {"path": PATH, "owner": "seeded", "seeded_sha256": "0" * 64}
OTHER_SEEDED_ROW = {
    "path": ".orqlet/role-bindings.yaml",
    "owner": "seeded",
    "seeded_sha256": "1" * 64,
}
GENERATED_ROW = {
    "path": PATH,
    "owner": "orqlet",
    "class": "protected",
    "rendered_sha256": "2" * 64,
}
USER_ROW = {"path": PATH, "owner": "user", "rendered_sha256": "3" * 64}


def lock_bytes(*rows: dict[str, Any], **extra: Any) -> bytes:
    """A generated lock with these rows (JSON text, which is YAML)."""
    data = {
        "schema": "orqlet.generated-lock/v1",
        "generator": {"orqlet": "0.4.0"},
        "files": list(rows),
        **extra,
    }
    return json.dumps(data, indent=2).encode()


def write(project: MemoryFileSystem, path: str, content: bytes) -> None:
    project.write_atomic(CanonicalPath.parse(path), content)


def project_with(policy: bytes | None = None, lock: bytes | None = None) -> MemoryFileSystem:
    project = MemoryFileSystem()
    if policy is not None:
        write(project, PATH, policy)
    if lock is not None:
        write(project, LOCK, lock)
    return project


def unreadable_lock(error: Exception) -> MemoryFileSystem:
    """A lock that says 'seeded' and cannot be read."""
    project = FaultyFileSystem()
    write(project, LOCK, lock_bytes(SEEDED_ROW))
    project.break_path(LOCK, read_error=error)
    return project


def odd_lock() -> MemoryFileSystem:
    """A lock that says 'seeded' and that the file system reports as no regular file."""
    project = FaultyFileSystem()
    write(project, LOCK, lock_bytes(SEEDED_ROW))
    project.break_path(LOCK, forced=FileKind.OTHER)
    return project


def lock_directory() -> MemoryFileSystem:
    project = MemoryFileSystem()
    project.make_dir(CanonicalPath.parse(LOCK))
    return project


def lock_link() -> MemoryFileSystem:
    project = MemoryFileSystem()
    project.add_symlink(LOCK)
    return project


# A lock that cannot be trusted to prove a deletion: the policy is absent, never deleted.
ABSENT_LOCKS: dict[str, Callable[[], MemoryFileSystem]] = {
    "there-is-no-lock": MemoryFileSystem,
    "the-lock-has-no-rows": lambda: project_with(lock=lock_bytes()),
    "the-lock-is-a-directory": lock_directory,
    "the-lock-is-a-symbolic-link": lock_link,
    "the-lock-is-no-regular-file": odd_lock,
    "the-read-of-the-lock-raises-a-file-system-error": lambda: unreadable_lock(
        FileSystemError("marker-lock-error")
    ),
    "the-read-of-the-lock-raises-an-os-error": lambda: unreadable_lock(
        PermissionError("marker-lock-error")
    ),
    "the-lock-is-not-yaml": lambda: project_with(lock=b"{{{ not yaml"),
    "the-lock-has-a-duplicate-key": lambda: project_with(
        lock=yaml_lines(b"schema: orqlet.generated-lock/v1", b"schema: orqlet.generated-lock/v1")
    ),
    "the-lock-is-not-utf-8": lambda: project_with(lock=yaml_lines(b"schema: \xff\xfe")),
    "the-lock-fails-its-contract": lambda: project_with(
        lock=lock_bytes(SEEDED_ROW, surprise=1),
    ),
    "the-lock-names-another-schema": lambda: project_with(
        lock=lock_bytes(SEEDED_ROW).replace(b"generated-lock/v1", b"generated-lock/v9")
    ),
    "the-lock-has-the-seeded-row-and-an-invalid-row": lambda: project_with(
        lock=lock_bytes(SEEDED_ROW, {"path": "x", "owner": "seeded"})
    ),
    "the-lock-has-no-row-for-the-path": lambda: project_with(lock=lock_bytes(OTHER_SEEDED_ROW)),
    "the-row-of-the-path-has-another-owner": lambda: project_with(lock=lock_bytes(GENERATED_ROW)),
    "the-row-of-the-path-is-user-owned": lambda: project_with(lock=lock_bytes(USER_ROW)),
}


# --- a path that cannot be used as a file ----------------------------------------------


def policy_that_is_a_directory(lock: bytes | None) -> MemoryFileSystem:
    project = project_with(lock=lock)
    project.make_dir(CanonicalPath.parse(PATH))
    return project


def policy_that_is_a_link(lock: bytes | None) -> MemoryFileSystem:
    project = project_with(lock=lock)
    project.add_symlink(PATH)
    return project


def policy_below_a_link(lock: bytes | None) -> MemoryFileSystem:
    project = project_with(valid_bytes(), lock)
    project.add_symlink(".orqlet")
    return project


def faulty_policy(lock: bytes | None, **faults: Any) -> MemoryFileSystem:
    project = FaultyFileSystem()
    write(project, PATH, valid_bytes())
    if lock is not None:
        write(project, LOCK, lock)
    project.break_path(PATH, **faults)
    return project


UNUSABLE_FILES: dict[str, Callable[[bytes | None], MemoryFileSystem]] = {
    "a-directory": policy_that_is_a_directory,
    "a-symbolic-link": policy_that_is_a_link,
    "a-symbolic-link-above-the-file": policy_below_a_link,
    "no-regular-file": lambda lock: faulty_policy(lock, forced=FileKind.OTHER),
    "a-lookup-that-raises-an-os-error": lambda lock: faulty_policy(
        lock, kind_error=PermissionError("marker-os-error")
    ),
    "a-read-that-raises-a-file-system-error": lambda lock: faulty_policy(
        lock, read_error=FileSystemError("marker-file-system-error")
    ),
    "a-read-that-raises-an-os-error": lambda lock: faulty_policy(
        lock, read_error=PermissionError("marker-os-error")
    ),
    "a-file-that-is-gone-by-the-time-of-the-read": lambda lock: faulty_policy(
        lock, read_error=PathNotFound("marker-gone-error")
    ),
}

# --- the two entry points, read through the same bytes ---------------------------------


class Reader(Protocol):
    def __call__(self, raw: bytes, *, loader: DocumentLoader = ...) -> PolicyState: ...


def from_working_tree(raw: bytes, *, loader: DocumentLoader = LOADER) -> PolicyState:
    return load_model_policy(make_services(project_with(raw), loader=loader))


def from_git_tree(raw: bytes, *, loader: DocumentLoader = LOADER) -> PolicyState:
    vcs = FakeVcs(revisions={TREE: {PATH: raw}})
    return read_model_policy_at(make_services(vcs=vcs, loader=loader), TREE)


ENTRY_POINTS: dict[str, Reader] = {"working-tree": from_working_tree, "git-tree": from_git_tree}
EITHER_ENTRY_POINT = pytest.mark.parametrize(
    "read", list(ENTRY_POINTS.values()), ids=list(ENTRY_POINTS)
)


# --- what the tests look at ------------------------------------------------------------


def shown(findings: tuple[Finding, ...]) -> str:
    """Everything that findings show: code, message, path and the representation."""
    return "\n".join(f"{f.code}\n{f.message}\n{f.path}\n{f!r}" for f in findings)


def invalid(state: PolicyState) -> tuple[Finding, ...]:
    """The findings of an invalid state; fails when the state is another one."""
    assert isinstance(state, PolicyInvalid), state
    assert isinstance(state.findings, tuple)
    assert state.findings
    for finding in state.findings:
        assert isinstance(finding, Finding)
        assert finding.severity is Severity.ERROR
        assert finding.path == PATH
        assert finding.message.strip()
    return state.findings


def codes(findings: tuple[Finding, ...]) -> set[str]:
    return {finding.code for finding in findings}


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def markers_in(raw: bytes) -> set[str]:
    """Every marker of the text of a document."""
    return set(MARKER.findall(raw.decode("utf-8", errors="replace")))


def long_values(node: object) -> set[str]:
    """Every text value of the document that is 12 characters or longer (keys are not values)."""
    found: set[str] = set()
    if isinstance(node, dict):
        for value in node.values():
            found |= long_values(value)
    elif isinstance(node, list):
        for item in node:
            found |= long_values(item)
    elif isinstance(node, str) and len(node) >= 12 and node != SCHEMA_ID:
        found.add(node)
    return found


def assert_nothing_of_the_file_is_shown(findings: tuple[Finding, ...], raw: bytes) -> None:
    """No marker and no long value of the document is in a code, a message or a path."""
    text = shown(findings)
    for marker in markers_in(raw):
        assert marker not in text, marker
    for value in long_values(LOADER.load(raw, source="document")):
        assert value not in text, value


def field_path(location: tuple[int | str, ...], rule: str) -> str:
    """The field path of a validation error, worked out from the contract and not from the loader.

    Names of the contract, a list position as `[n]`, an unknown key as the fixed word `unknown-key`
    and no location at all as `(document)`.
    """
    parts: list[str] = []
    for index, part in enumerate(location):
        if isinstance(part, int):
            parts.append(f"[{part}]")
        elif rule == "extra_forbidden" and index == len(location) - 1:
            parts.append(UNKNOWN_KEY)
        else:
            parts.append(part)
    return ".".join(parts).replace(".[", "[") or DOCUMENT


def contract_problems(raw: bytes) -> list[tuple[str, str]]:
    """The (field path, rule) of every error that the contract finds in these bytes."""
    data = LOADER.load(raw, source="document")
    with pytest.raises(ValidationError) as caught:
        ModelPolicy.model_validate(data)
    return [
        (field_path(error["loc"], str(error["type"])), str(error["type"]))
        for error in caught.value.errors(include_input=False, include_url=False)
    ]


def assert_contract_findings(findings: tuple[Finding, ...], raw: bytes) -> None:
    """One ORQ-E541 finding per validation error, each with its field path and its rule."""
    problems = contract_problems(raw)
    assert codes(findings) == {CONTRACT}
    assert len(findings) == len(problems)
    for path, rule in problems:
        assert any(path in f.message and rule in f.message for f in findings), (path, rule)
    for finding in findings:
        assert any(path in finding.message and rule in finding.message for path, rule in problems)


def line_of(raw: bytes, needle: str) -> int:
    """The one-based line of the text on which `needle` stands."""
    for number, line in enumerate(raw.decode("utf-8").split("\n"), start=1):
        if needle in line:
            return number
    raise AssertionError("the text is not in the document")


# --- the documents that the tests refuse -----------------------------------------------

# The causes of ORQ-E540 that the plan names, each with a marker where a name stands.
STRICT_REFUSALS: dict[str, bytes] = {
    "a-duplicate-key": yaml_lines(
        HEADER, b"marker-duplicate-key-1: 1", b"marker-duplicate-key-1: 2"
    ),
    "a-duplicate-key-in-a-model": duplicated_family(),
    "an-anchor": yaml_lines(HEADER, b"models: &marker-anchor-name-1 []"),
    "an-alias": yaml_lines(HEADER, b"models: *marker-alias-name-1"),
    "nesting-deeper-than-32-levels": yaml_lines(HEADER, b"models: " + b"[" * 40 + b"]" * 40),
    "bytes-that-are-not-utf-8": yaml_lines(HEADER, b"marker-bytes-1: \xff\xfe"),
    "a-file-above-256-kib": padded(LIMIT + 1),
}
# Other refusals of the strict loader: "breaks the strict reading rules" says them all.
OTHER_REFUSALS: dict[str, bytes] = {
    "a-merge-key": yaml_lines(HEADER, b"<<: {}"),
    "a-python-tag": yaml_lines(HEADER, b"models: !!python/object/apply:os.getcwd []"),
    "a-local-tag": yaml_lines(HEADER, b"models: !marker-tag-name-1 []"),
    "a-control-character": yaml_lines(HEADER, b"models: []") + b"\x00",
    "text-that-is-not-yaml": b"{{{ not yaml",
    "two-documents": valid_bytes() + b"\n---\n" + valid_bytes(),
}
# Documents that the strict loader reads and that are no mapping at all.
DEGENERATE: dict[str, bytes] = {
    "a-list": b"- one\n- two\n",
    "a-scalar": b"just text\n",
    "an-empty-file": b"",
}
CONTRACT_FAILURES: dict[str, Callable[[], bytes]] = {
    "a-missing-top-level-field": lambda: mutated(lambda d: d.pop("policy_version")),
    "another-schema-id": lambda: mutated(lambda d: d.update(schema="orqlet.model-policy/v3")),
    "an-unknown-top-level-key": lambda: mutated(lambda d: d.update(surprise=1)),
    "an-unknown-key-in-a-model": lambda: mutated(lambda d: d["models"][0].update(surprise=1)),
    "a-client-that-is-not-one-of-the-three": lambda: mutated(
        lambda d: d["models"][0]["routes"][1].update(client="vscode")
    ),
    "a-model-id-with-a-space": lambda: mutated(lambda d: d["models"][0].update(id="has a space")),
    "a-policy-version-as-text": lambda: mutated(lambda d: d.update(policy_version="1")),
    "a-profile-id-used-twice": lambda: mutated(lambda d: d["profiles"][1].update(id="quality")),
    "an-evidenced-evaluation-without-evidence": lambda: mutated(
        lambda d: d["models"][0]["evaluated"].update(evidence=None)
    ),
    "a-repository-path-that-climbs-out": lambda: mutated(
        lambda d: d["models"][0]["documented"].update(evidence="../outside.md")
    ),
    "several-errors-at-once": lambda: mutated(
        lambda d: (
            d.pop("policy_version"),
            d["models"][0].update(id="has a space"),
            d["models"][1].update(surprise=1),
        )
    ),
}
# The field path and the rule of the one error that each of these documents has.
ONE_PROBLEM: dict[str, tuple[str, str]] = {
    "a-missing-top-level-field": ("policy_version", "missing"),
    "another-schema-id": ("schema", "literal_error"),
    "an-unknown-top-level-key": (UNKNOWN_KEY, "extra_forbidden"),
    "an-unknown-key-in-a-model": (f"models[0].{UNKNOWN_KEY}", "extra_forbidden"),
    "a-client-that-is-not-one-of-the-three": ("models[0].routes[1].client", "literal_error"),
    "a-model-id-with-a-space": ("models[0].id", "string_pattern_mismatch"),
    "a-profile-id-used-twice": (DOCUMENT, "value_error"),
    "an-evidenced-evaluation-without-evidence": ("models[0].evaluated", "value_error"),
    "a-repository-path-that-climbs-out": ("models[0].documented.evidence", "value_error"),
}

# --- the sites of AC-5 -----------------------------------------------------------------

MODEL_SITES: dict[str, Where] = {
    "model-id": ("models", 0, "id"),
    "model-family": ("models", 0, "family"),
    "route-name": ("models", 0, "routes", 0, "name"),
    "route-resolves-to": ("models", 0, "routes", 1, "resolves_to"),
    "route-also-known-as": ("models", 0, "routes", 0, "also_known_as", 0),
    "assignment-model": ("assignments", 1, "model"),
    "profile-candidate": ("profiles", 0, "candidates", 0, "models", 0),
    "profile-fallback": ("profiles", 0, "fallbacks", 0, "models", 0),
    "exclusion-id": ("excluded", 0, "id"),
    "exclusion-alias": ("excluded", 0, "aliases", 0),
    "exclusion-family-tag": ("excluded", 0, "family_tags", 0),
    "exclusion-id-pattern": ("excluded", 0, "id_patterns", 0),
}
TEXT_SITES: dict[str, Where] = {
    "approved-by": ("models", 0, "approval", "approved_by"),
    "approval-ref": ("models", 0, "approval", "approval_ref"),
    "exclusion-reason": ("excluded", 0, "reason"),
    "exclusion-source": ("excluded", 0, "source"),
    "profile-capability": ("profiles", 0, "capability"),
}
PATH_SITES: dict[str, Where] = {
    "documented-evidence": ("models", 0, "documented", "evidence"),
    "evaluated-evidence": ("models", 0, "evaluated", "evidence"),
    "list-price-source": ("models", 0, "list_price", "source"),
}
# The objects that receive a key that the contract does not know.
STRANGER_SITES: dict[str, Where] = {
    "top-level": (),
    "model": ("models", 0),
    "route": ("models", 0, "routes", 0),
    "approval": ("models", 0, "approval"),
    "candidates-entry": ("profiles", 0, "candidates", 0),
    "assignment-target": ("assignments", 0, "target"),
}


def refused_model_string(marker: str) -> str:
    return f"{marker} !"  # a space and `!` are outside the alphabet of a model name


def refused_text(marker: str) -> str:
    return f"{marker}\u00e9"  # one character outside printable ASCII


def refused_path(marker: str) -> str:
    return f"docs/../../{marker}"  # climbs out of the repository


def valid_path(marker: str) -> str:
    return f"docs/{marker}.md"


def valid_text(marker: str) -> str:
    return marker


def refusals_at(
    sites: dict[str, Where], refuse: Callable[[str], str], rule: str
) -> dict[str, tuple[Where, Callable[[str], str], str]]:
    return {name: (where, refuse, rule) for name, where in sites.items()}


REFUSALS: dict[str, tuple[Where, Callable[[str], str], str]] = {
    **refusals_at(MODEL_SITES, refused_model_string, "string_pattern_mismatch"),
    **refusals_at(TEXT_SITES, refused_text, "string_pattern_mismatch"),
    **refusals_at(PATH_SITES, refused_path, "value_error"),
}


def add_strangers(data: dict[str, Any], where: Where, label: str, variant: int) -> None:
    """Two keys that the contract does not know: one with a text and one with a map as value."""
    holder = reach(data, where)
    holder[f"marker-unknown-key-{label}-{variant}"] = f"marker-unknown-value-{label}-{variant}"
    inner_key = f"marker-unknown-inner-key-{label}-{variant}"
    inner_value = f"marker-unknown-inner-value-{label}-{variant}"
    holder[f"marker-unknown-map-{label}-{variant}"] = {inner_key: inner_value}


def refused_at(name: str, variant: int) -> bytes:
    """The valid policy with one site refused, and a marker in the refused value."""
    where, refuse, _ = REFUSALS[name]
    data = fixture()
    set_at(data, where, refuse(f"marker-{name}-{variant}"))
    return document(data)


def strangers_at(name: str, variant: int) -> bytes:
    """The valid policy with two unknown keys, with markers, in one object."""
    data = fixture()
    add_strangers(data, STRANGER_SITES[name], name, variant)
    return document(data)


def everything_refused(variant: int) -> bytes:
    """Every site refused with its own marker, and unknown keys in every object."""
    data = fixture()
    for name, (where, refuse, _) in REFUSALS.items():
        set_at(data, where, refuse(f"marker-{name}-{variant}"))
    for name, where in STRANGER_SITES.items():
        add_strangers(data, where, name, variant)
    return document(data)


def valid_values_next_to_one_refusal(variant: int) -> bytes:
    """A marker in every model, text and path field, all of them valid, and then one refused path.

    The document is invalid because of the one path and the unknown keys; every other marker
    sits in a field that the contract accepts.
    """
    data = fixture()
    for name, where in {**MODEL_SITES, **TEXT_SITES}.items():
        set_at(data, where, valid_text(f"marker-{name}-{variant}"))
    for name, where in PATH_SITES.items():
        set_at(data, where, valid_path(f"marker-{name}-{variant}"))
    set_at(data, PATH_SITES["documented-evidence"], refused_path(f"marker-refused-path-{variant}"))
    for name, where in STRANGER_SITES.items():
        add_strangers(data, where, name, variant)
    return document(data)


def key_in_a_field(where: Where, key: str) -> bytes:
    data = fixture()
    set_at(data, where, f"use {key} here")
    return document(data)


def key_in_a_comment(key: str) -> bytes:
    return valid_bytes() + f"\n# remember {key} for later\n".encode()


# --- AC-1: where the policy lives and the four states ----------------------------------


def test_the_policy_file_is_orqlet_model_policy_yaml() -> None:
    """expected_behavior_source: AC-1; BC-39; ADR-005 decision 2; ADR-002 decision 1.

    `model_policy_path()` is the canonical path `.orqlet/model-policy.yaml`.
    """
    path = model_policy_path()

    assert isinstance(path, CanonicalPath)
    assert path == CanonicalPath.parse(PATH)
    assert str(path) == PATH


def test_the_states_are_frozen_dataclasses_that_compare_by_value() -> None:
    """expected_behavior_source: AC-1; BC-39; ADR-005 decision 2.

    `PolicyAbsent()` and `PolicyDeleted()` have no field, `PolicyLoaded` has `policy` and
    `PolicyInvalid` has `findings`; all four are frozen and equal when their content is.
    """
    policy = expected_policy(valid_bytes())
    finding = Finding(UNREADABLE, "a message", Severity.ERROR, PATH)
    states: list[PolicyState] = [
        PolicyAbsent(),
        PolicyLoaded(policy=policy),
        PolicyInvalid(findings=(finding,)),
        PolicyDeleted(),
    ]

    assert [[f.name for f in dataclasses.fields(state)] for state in states] == [
        [],
        ["policy"],
        ["findings"],
        [],
    ]
    for state in states:
        assert dataclasses.is_dataclass(state)
        for field in dataclasses.fields(state):
            with pytest.raises(dataclasses.FrozenInstanceError):
                setattr(state, field.name, None)
    assert PolicyAbsent() == PolicyAbsent()
    assert PolicyDeleted() == PolicyDeleted()
    assert hash(PolicyAbsent()) == hash(PolicyAbsent())
    # Typed as `object` because mypy refuses to compare two types that can never be equal.
    absent: object = PolicyAbsent()
    assert absent != PolicyDeleted()
    assert PolicyLoaded(policy=policy) == PolicyLoaded(policy=expected_policy(valid_bytes()))
    assert PolicyInvalid(findings=(finding,)) == PolicyInvalid(findings=(finding,))
    assert PolicyInvalid(findings=(finding,)) != PolicyInvalid(findings=())


def test_policy_state_is_the_union_of_the_four_states() -> None:
    """expected_behavior_source: AC-1; BC-39; ADR-005 decision 2.

    `PolicyState` is a `type` alias of the union of the four classes.
    """
    import orqlet.application.usecases.model_policy_source as module

    alias = vars(module)["PolicyState"]

    assert set(get_args(alias.__value__)) == {
        PolicyAbsent,
        PolicyLoaded,
        PolicyInvalid,
        PolicyDeleted,
    }


def test_no_file_and_no_lock_is_absent_and_nothing_is_written() -> None:
    """expected_behavior_source: AC-1 ("absent (no file and no seeded row for it in the lock)");
    BC-39; ADR-005 decision 2 ("Only a project where the file was never present").
    """
    project = MemoryFileSystem()

    assert load_model_policy(make_services(project)) == PolicyAbsent()
    assert project.snapshot() == {}


def test_other_files_in_the_folder_do_not_make_the_policy_present() -> None:
    """expected_behavior_source: AC-1; ADR-005 decision 2.

    Absent means that the file is not there, whatever else the folder holds.
    """
    project = project_with()
    write(project, ".orqlet/other.yaml", b"x: 1\n")

    assert load_model_policy(make_services(project)) == PolicyAbsent()


def test_a_valid_file_is_loaded_as_the_contract_and_nothing_is_written() -> None:
    """expected_behavior_source: AC-1 ("loaded (the v2 contract)"); BC-39; ADR-002 decision 1.

    The state holds what `load_contract` makes of the same bytes.
    """
    project = project_with(valid_bytes())
    before = project.snapshot()

    state = load_model_policy(make_services(project))

    assert state == PolicyLoaded(policy=expected_policy(valid_bytes()))
    assert isinstance(state, PolicyLoaded)
    assert isinstance(state.policy, ModelPolicy)
    assert project.snapshot() == before


@EITHER_ENTRY_POINT
def test_the_fixture_as_written_yaml_is_loaded(read: Reader) -> None:
    """expected_behavior_source: AC-1 and AC-2; BC-39; ADR-002 decision 1.

    The real YAML of the fixture (block style, with comments) loads, not only JSON text.
    """
    raw = FIXTURE.read_bytes()

    assert read(raw) == PolicyLoaded(policy=expected_policy(raw))


def test_no_file_and_a_seeded_row_in_the_lock_is_deleted() -> None:
    """expected_behavior_source: AC-1 ("deleted (no file, and the lock records the path with owner
    `seeded`)"); BC-39; ADR-005 decision 2 ("A deleted file is not 'absent'").
    """
    project = project_with(lock=lock_bytes(SEEDED_ROW))
    before = project.snapshot()

    assert load_model_policy(make_services(project)) == PolicyDeleted()
    assert project.snapshot() == before


def test_the_seeded_row_is_found_among_other_rows() -> None:
    """expected_behavior_source: AC-1; BC-39; ADR-005 decision 2.

    Rows of other files, and a row of another owner for other paths, do not hide it.
    """
    other = {"path": ".orqlet/versions.yaml", "owner": "orqlet", "class": "generated"}
    lock = lock_bytes(OTHER_SEEDED_ROW, {**other, "rendered_sha256": "4" * 64}, SEEDED_ROW)
    load_contract(LOADER, GeneratedLock, lock, source="lock")

    assert load_model_policy(make_services(project_with(lock=lock))) == PolicyDeleted()


@pytest.mark.parametrize("name", list(ABSENT_LOCKS), ids=list(ABSENT_LOCKS))
def test_a_lock_that_cannot_prove_a_deletion_leaves_the_policy_absent(name: str) -> None:
    """expected_behavior_source: AC-1 ("A lock that cannot be read is not proof of a deletion, so
    the state is absent"); BC-39; ADR-005 decision 2.

    No lock, a lock that is a directory or a link or no regular file, a lock that cannot be read,
    that is not valid YAML or that fails its contract, a lock without a row for the path and a row
    with another owner each give `PolicyAbsent`, never `PolicyDeleted` and never an error.
    """
    assert load_model_policy(make_services(ABSENT_LOCKS[name]())) == PolicyAbsent()


def test_a_seeded_row_never_makes_an_existing_valid_file_deleted() -> None:
    """expected_behavior_source: AC-1; BC-39; ADR-005 decision 2.

    A seeded row says that the file was once seeded; a file that is there is loaded.
    """
    project = project_with(valid_bytes(), lock_bytes(SEEDED_ROW))

    assert load_model_policy(make_services(project)) == PolicyLoaded(
        policy=expected_policy(valid_bytes())
    )


def test_a_seeded_row_never_makes_an_existing_broken_file_deleted_or_absent() -> None:
    """expected_behavior_source: AC-1 ("invalid (findings)"); BC-39; ADR-005 decision 2.

    A broken file that is there is invalid, whatever the lock says.
    """
    broken = CONTRACT_FAILURES["a-model-id-with-a-space"]()
    project = project_with(broken, lock_bytes(SEEDED_ROW))

    invalid(load_model_policy(make_services(project)))


def test_the_locks_of_the_cases_are_what_the_cases_say() -> None:
    """expected_behavior_source: AC-1; BC-39 (the generated-lock contract). This holds before the
    loader exists and guards the premise of the tests above: the row that proves a deletion is a
    valid lock row, and the locks that must not prove it are refused by the contract or have no
    seeded row for the path.
    """
    seeded = load_contract(LOADER, GeneratedLock, lock_bytes(SEEDED_ROW), source="lock")
    assert [(row.path, row.owner.value) for row in seeded.files] == [(PATH, "seeded")]
    for row in (OTHER_SEEDED_ROW, GENERATED_ROW, USER_ROW):
        lock = load_contract(LOADER, GeneratedLock, lock_bytes(row), source="lock")
        seeded_rows_of_the_policy = [
            entry for entry in lock.files if entry.path == PATH and entry.owner.value == "seeded"
        ]
        assert seeded_rows_of_the_policy == []
    for refused in (
        lock_bytes(SEEDED_ROW, surprise=1),
        lock_bytes(SEEDED_ROW).replace(b"generated-lock/v1", b"generated-lock/v9"),
        lock_bytes(SEEDED_ROW, {"path": "x", "owner": "seeded"}),
    ):
        with pytest.raises(DocumentError):
            load_contract(LOADER, GeneratedLock, refused, source="lock")


@pytest.mark.parametrize("lock", [None, lock_bytes(SEEDED_ROW)], ids=["no-lock", "seeded-row"])
@pytest.mark.parametrize("name", list(UNUSABLE_FILES), ids=list(UNUSABLE_FILES))
def test_a_path_that_cannot_be_used_as_a_file_is_invalid(name: str, lock: bytes | None) -> None:
    """expected_behavior_source: AC-1 ("A file that is a directory, a link or not a regular file
    is invalid"); BC-39; ORQLET-SEC-002 (files of the repository are untrusted and read through
    the port, which refuses links).

    A directory, a symbolic link, a link above the file, a path that is no regular file and a read
    that fails give `PolicyInvalid`: never an exception, never `PolicyAbsent`, never
    `PolicyDeleted`, even when the lock holds a seeded row.
    """
    invalid(load_model_policy(make_services(UNUSABLE_FILES[name](lock))))


@pytest.mark.parametrize("name", list(UNUSABLE_FILES), ids=list(UNUSABLE_FILES))
def test_a_path_that_cannot_be_used_as_a_file_gets_the_unreadable_code(name: str) -> None:
    """expected_behavior_source: AC-1 and AC-3 (ORQ-E540 is "unreadable or refused by the strict
    reading rules"); BC-39. The plan says only `invalid` for these causes; the code is the Coder's
    choice by analogy with ORQ-E530 of the integrations reader, so this is the one place to change.
    """
    findings = invalid(load_model_policy(make_services(UNUSABLE_FILES[name](None))))

    assert codes(findings) == {UNREADABLE}


@pytest.mark.parametrize("name", list(UNUSABLE_FILES), ids=list(UNUSABLE_FILES))
def test_a_finding_for_an_unusable_path_holds_no_text_of_an_error(name: str) -> None:
    """expected_behavior_source: AC-5 ("a fixed text ... nothing else"); BC-32; ORQLET-SEC-002.

    The messages of the errors that the file system raises carry a marker; no finding shows it.
    """
    findings = invalid(load_model_policy(make_services(UNUSABLE_FILES[name](None))))

    assert "marker" not in shown(findings)


# --- AC-2: the tree entry point --------------------------------------------------------


def test_the_tree_entry_point_gives_absent_loaded_or_invalid() -> None:
    """expected_behavior_source: AC-2 ("returns absent, loaded or invalid"); BC-23; BC-44;
    ADR-007 decision 10.
    """
    absent = FakeVcs(revisions={TREE: {"README.md": b"text"}})
    loaded = FakeVcs(revisions={TREE: {PATH: valid_bytes()}})
    broken = FakeVcs(revisions={TREE: {PATH: CONTRACT_FAILURES["a-model-id-with-a-space"]()}})

    assert read_model_policy_at(make_services(vcs=absent), TREE) == PolicyAbsent()
    assert read_model_policy_at(make_services(vcs=loaded), TREE) == PolicyLoaded(
        policy=expected_policy(valid_bytes())
    )
    invalid(read_model_policy_at(make_services(vcs=broken), TREE))


def test_a_tree_that_the_vcs_does_not_know_is_absent() -> None:
    """expected_behavior_source: AC-2 (`read_at` returns None: absent); BC-44.

    `read_at` answers None for a missing file and for a missing revision.
    """
    vcs = FakeVcs(revisions={TREE: {PATH: valid_bytes()}})

    assert read_model_policy_at(make_services(vcs=vcs), OTHER_TREE) == PolicyAbsent()
    assert read_model_policy_at(make_services(vcs=FakeVcs()), "HEAD") == PolicyAbsent()


def test_the_tree_can_be_head_a_commit_id_or_a_tree_id() -> None:
    """expected_behavior_source: AC-2 ("a git tree (`HEAD` or a full object id)"); BC-44;
    ADR-007 decision 10.
    """
    expected = PolicyLoaded(policy=expected_policy(valid_bytes()))
    at_head = FakeVcs(
        committed={PATH: valid_bytes()}, commits=(CommitSummary(COMMIT, "a subject"),)
    )
    at_commit = FakeVcs(revisions={COMMIT: {PATH: valid_bytes()}})
    at_tree = FakeVcs(staged_tree=(STAGED_TREE, {PATH: valid_bytes()}))

    assert read_model_policy_at(make_services(vcs=at_head), "HEAD") == expected
    assert read_model_policy_at(make_services(vcs=at_commit), COMMIT) == expected
    assert read_model_policy_at(make_services(vcs=at_tree), STAGED_TREE) == expected


def test_the_tree_entry_point_never_returns_deleted() -> None:
    """expected_behavior_source: AC-2 (absent, loaded or invalid); BC-44; ADR-005 decision 2.

    A file that is missing from the tree is absent, even when the lock of the working tree holds
    a seeded row: the deletion rule belongs to the working tree and not to a tree of the VCS.
    """
    project = project_with(lock=lock_bytes(SEEDED_ROW))
    vcs = FakeVcs(revisions={TREE: {"README.md": b"text"}})

    state = read_model_policy_at(make_services(project, vcs), TREE)

    assert state == PolicyAbsent()


def test_a_vcs_error_is_an_invalid_state_and_not_an_exception() -> None:
    """expected_behavior_source: AC-2 and AC-3 (ORQ-E540 for `vcs.read_at` raising `VcsError`);
    BC-44; ORQLET-SEC-002.

    A VCS that refuses the revision, and one that fails to read, give `PolicyInvalid`.
    """
    refusing = make_services(vcs=FakeVcs())
    failing = make_services(vcs=FailingVcs())

    invalid(read_model_policy_at(refusing, "not-a-revision"))
    invalid(read_model_policy_at(failing, TREE))


def test_a_vcs_error_gets_the_unreadable_code_and_shows_no_text_of_the_error() -> None:
    """expected_behavior_source: AC-3 (ORQ-E540) and AC-5 ("a fixed text ... nothing else"); BC-32.

    The code for this cause is the Coder's choice by analogy with the working tree: it is
    asserted here only, so it is easy to change. The message of the `VcsError` carries a marker.
    """
    findings = invalid(read_model_policy_at(make_services(vcs=FailingVcs()), TREE))

    assert codes(findings) == {UNREADABLE}
    assert "marker" not in shown(findings)


SAME_BYTES: dict[str, tuple[bytes, type[PolicyLoaded] | type[PolicyInvalid]]] = {
    "a-valid-file": (valid_bytes(), PolicyLoaded),
    "a-file-above-256-kib": (STRICT_REFUSALS["a-file-above-256-kib"], PolicyInvalid),
    "a-duplicate-key": (STRICT_REFUSALS["a-duplicate-key"], PolicyInvalid),
    "an-anchor": (STRICT_REFUSALS["an-anchor"], PolicyInvalid),
    "an-alias": (STRICT_REFUSALS["an-alias"], PolicyInvalid),
    "nesting-deeper-than-32-levels": (
        STRICT_REFUSALS["nesting-deeper-than-32-levels"],
        PolicyInvalid,
    ),
    "bytes-that-are-not-utf-8": (STRICT_REFUSALS["bytes-that-are-not-utf-8"], PolicyInvalid),
    "a-contract-failure": (CONTRACT_FAILURES["several-errors-at-once"](), PolicyInvalid),
    "a-v1-file": (v1_document(), PolicyInvalid),
    "a-credential": (key_in_a_field(("profiles", 0, "capability"), KEYS["sk-key"]), PolicyInvalid),
    "a-credential-in-a-comment": (key_in_a_comment(KEYS["aiza-key"]), PolicyInvalid),
    "refused-values-with-markers": (everything_refused(1), PolicyInvalid),
}


@pytest.mark.parametrize("name", list(SAME_BYTES), ids=list(SAME_BYTES))
def test_the_same_bytes_give_equal_states_from_both_entry_points(name: str) -> None:
    """expected_behavior_source: AC-2 ("the same bytes give the same state from both entry
    points"); ADR-007 decision 10 ("Two entry points, one parser"); BC-23; BC-44.

    A valid file and one file of each invalid kind: oversize, duplicate key, anchor, alias, too
    deep, invalid UTF-8, contract failure, v1 and credential. The states compare by value.
    """
    raw, expected_class = SAME_BYTES[name]

    from_files = from_working_tree(raw)
    from_tree = from_git_tree(raw)

    assert isinstance(from_files, expected_class)
    assert from_files == from_tree


def test_load_model_policy_reads_the_working_tree_through_the_port_and_never_the_vcs() -> None:
    """expected_behavior_source: AC-2 ("`load_model_policy` never calls the VCS port; the fakes
    record every call and the test asserts both"); BC-23; BC-44.

    For each of the four outcomes, the recording file system was used and the recording VCS was
    not touched, though the VCS holds a valid policy.
    """
    scenarios = {
        "absent": (None, None),
        "loaded": (valid_bytes(), None),
        "invalid": (CONTRACT_FAILURES["a-model-id-with-a-space"](), None),
        "deleted": (None, lock_bytes(SEEDED_ROW)),
    }
    for policy, lock in scenarios.values():
        project = RecordingFileSystem()
        if policy is not None:
            write(project, PATH, policy)
        if lock is not None:
            write(project, LOCK, lock)
        project.forget()
        vcs = RecordingVcs({TREE: {PATH: valid_bytes()}, "HEAD": {PATH: valid_bytes()}})

        load_model_policy(make_services(project, vcs))

        assert vcs.accessed == []
        assert vcs.reads == []
        assert project.accessed != []


def test_read_model_policy_at_reads_the_tree_through_read_at_and_never_the_working_tree() -> None:
    """expected_behavior_source: AC-2 ("reads the same path from a git tree through `vcs.read_at`
    ... It never reads the working tree"); BC-23; BC-44; ADR-007 decision 10.

    For an absent, a loaded and two invalid files of the tree, the only use of the VCS is `read_at`
    of the policy path at that tree, and the recording file system is not touched, though the
    working tree holds a valid policy and a lock with a seeded row.
    """
    trees: dict[str, dict[str, bytes]] = {
        "absent": {"README.md": b"text"},
        "loaded": {PATH: valid_bytes()},
        "invalid": {PATH: CONTRACT_FAILURES["a-model-id-with-a-space"]()},
        "refused": {PATH: STRICT_REFUSALS["an-anchor"]},
    }
    for files in trees.values():
        project = RecordingFileSystem()
        write(project, PATH, valid_bytes())
        write(project, LOCK, lock_bytes(SEEDED_ROW))
        project.forget()
        vcs = RecordingVcs({TREE: files})

        read_model_policy_at(make_services(project, vcs), TREE)

        assert project.accessed == []
        assert set(vcs.accessed) == {"read_at"}
        assert set(vcs.reads) == {(TREE, PATH)}


def test_the_tree_entry_point_judges_the_tree_and_not_the_working_tree() -> None:
    """expected_behavior_source: AC-2; BC-44; ADR-007 decision 10 (independence is derived from
    the exact snapshot that was reviewed, "not from the change's own edit of the policy").

    The same call gives the state of the tree whether the working tree holds a valid file, a
    broken one or none.
    """
    broken = CONTRACT_FAILURES["a-model-id-with-a-space"]()
    valid_tree = FakeVcs(revisions={TREE: {PATH: valid_bytes()}})
    broken_tree = FakeVcs(revisions={TREE: {PATH: broken}})
    expected = PolicyLoaded(policy=expected_policy(valid_bytes()))

    for project in (project_with(broken), project_with(valid_bytes()), project_with()):
        assert read_model_policy_at(make_services(project, valid_tree), TREE) == expected
        invalid(read_model_policy_at(make_services(project, broken_tree), TREE))


def test_the_working_tree_entry_point_judges_the_working_tree_and_not_the_vcs() -> None:
    """expected_behavior_source: AC-2; BC-23; BC-44.

    A policy at `HEAD` and at a tree does not make a project without a file loaded, and a broken
    file at `HEAD` does not make a project with a valid file invalid.
    """
    holding = FakeVcs(
        committed={PATH: valid_bytes()},
        commits=(CommitSummary(COMMIT, "a subject"),),
        revisions={TREE: {PATH: valid_bytes()}},
    )
    broken = FakeVcs(
        committed={PATH: CONTRACT_FAILURES["a-model-id-with-a-space"]()},
        commits=(CommitSummary(COMMIT, "a subject"),),
    )

    assert load_model_policy(make_services(MemoryFileSystem(), holding)) == PolicyAbsent()
    assert load_model_policy(make_services(project_with(valid_bytes()), broken)) == PolicyLoaded(
        policy=expected_policy(valid_bytes())
    )


@EITHER_ENTRY_POINT
def test_the_loader_of_the_services_is_the_parser_of_the_file(read: Reader) -> None:
    """expected_behavior_source: AC-2 and AC-3 (one strict parser, ORQLET-SEC-002: YAML only
    through the strict loader); BC-32; ADR-007 decision 10.

    The bytes are not YAML at all; the loader that the services hold hands back the fixture, and
    that is what the state holds.
    """
    state = read(b"this is not a document at all {{{", loader=StubLoader(fixture()))

    assert state == PolicyLoaded(policy=expected_policy(valid_bytes()))


@EITHER_ENTRY_POINT
def test_a_loader_that_refuses_the_file_makes_it_invalid_without_its_message(read: Reader) -> None:
    """expected_behavior_source: AC-3 ("breaks the strict reading rules" is ORQ-E540); BC-32;
    ORQLET-SEC-002; AC-5.

    The `DocumentError` of the loader carries a marker; the finding is a fixed text.
    """
    findings = invalid(read(valid_bytes(), loader=RefusingLoader()))

    assert codes(findings) == {UNREADABLE}
    assert "marker" not in shown(findings)


def test_a_loader_that_refuses_the_lock_leaves_the_policy_absent() -> None:
    """expected_behavior_source: AC-1 (a lock that cannot be read is not proof of a deletion);
    BC-39; ADR-005 decision 2.
    """
    project = project_with(lock=lock_bytes(SEEDED_ROW))

    assert load_model_policy(make_services(project, loader=RefusingLoader())) == PolicyAbsent()


def test_the_lock_is_parsed_by_the_loader_of_the_services() -> None:
    """expected_behavior_source: AC-1 ("read `.orqlet/generated.lock.yaml` through
    `services.project` and parse it with `services.loader`"); BC-39; ADR-005 decision 2.
    """
    loader = CountingLoader()
    project = project_with(lock=lock_bytes(SEEDED_ROW))

    state = load_model_policy(make_services(project, loader=loader))

    assert state == PolicyDeleted()
    assert loader.calls


def test_nothing_is_parsed_when_there_is_nothing_to_read() -> None:
    """expected_behavior_source: AC-1 and AC-2 (absent: no file and no lock; no file in the
    tree); BC-39; BC-44.
    """
    loader = CountingLoader()

    assert load_model_policy(make_services(loader=loader)) == PolicyAbsent()
    assert read_model_policy_at(make_services(loader=loader), TREE) == PolicyAbsent()
    assert loader.calls == []


# --- AC-3: ORQ-E540, the file cannot be used as a document -----------------------------


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("name", list(STRICT_REFUSALS), ids=list(STRICT_REFUSALS))
def test_a_file_that_breaks_the_strict_rules_gives_orq_e540(read: Reader, name: str) -> None:
    """expected_behavior_source: AC-3 ("A file above 256 KiB, a duplicate key, an anchor or alias,
    a document nested too deep and an invalid byte sequence each give the finding ORQ-E540");
    BC-32; BC-37; ORQLET-SEC-002.
    """
    findings = invalid(read(STRICT_REFUSALS[name]))

    assert codes(findings) == {UNREADABLE}


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("name", list(OTHER_REFUSALS), ids=list(OTHER_REFUSALS))
def test_every_other_refusal_of_the_strict_loader_gives_orq_e540(read: Reader, name: str) -> None:
    """expected_behavior_source: AC-3 (ORQ-E540 is the file that "breaks the strict reading rules":
    a merge key, a tag, a control character, text that is not YAML and two documents are refusals
    of the same loader); BC-32; ORQLET-SEC-002.
    """
    findings = invalid(read(OTHER_REFUSALS[name]))

    assert codes(findings) == {UNREADABLE}


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("name", list(DEGENERATE), ids=list(DEGENERATE))
def test_a_document_that_is_no_mapping_is_invalid(read: Reader, name: str) -> None:
    """expected_behavior_source: AC-3 (a file that is no policy is invalid; the code for a
    document that the loader reads and that is no mapping is not fixed, so either of the two is
    accepted); BC-32.
    """
    findings = invalid(read(DEGENERATE[name]))

    assert codes(findings) <= {UNREADABLE, CONTRACT}


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("size", [LIMIT + 1, 2 * LIMIT])
def test_a_file_above_256_kib_is_refused(read: Reader, size: int) -> None:
    """expected_behavior_source: AC-3 ("A file above 256 KiB"); BC-32; ORQLET-SEC-002.

    The file is a valid policy followed by comment lines, so only its size is wrong (the next
    test shows that the same padding at exactly 256 KiB is a valid policy).
    """
    findings = invalid(read(padded(size)))

    assert codes(findings) == {UNREADABLE}


@EITHER_ENTRY_POINT
def test_a_file_of_exactly_256_kib_is_not_above_the_limit(read: Reader) -> None:
    """expected_behavior_source: AC-3 (the limit is 256 KiB: 262144 bytes are accepted by the size
    rule and 262145 are refused); BC-32.
    """
    raw = padded(LIMIT)

    assert read(raw) == PolicyLoaded(policy=expected_policy(raw))


@EITHER_ENTRY_POINT
@pytest.mark.parametrize(
    "name", [*STRICT_REFUSALS, *OTHER_REFUSALS], ids=[*STRICT_REFUSALS, *OTHER_REFUSALS]
)
def test_a_finding_for_a_strict_refusal_holds_no_text_of_the_file(read: Reader, name: str) -> None:
    """expected_behavior_source: AC-5 ("no finding of the loader contains a marker, a key of the
    file or a value of the file"); BC-32; ORQLET-SEC-002.

    A marker stands in a duplicate key, an anchor name, an alias name, a tag name, a line of the
    padding of an oversize file: none is in a finding. The loader's own messages hold some of
    them, so the loader's text is not passed on.
    """
    raw = {**STRICT_REFUSALS, **OTHER_REFUSALS}[name]

    findings = invalid(read(raw))

    assert "marker" not in shown(findings)


# --- AC-3: ORQ-E541, the contract ------------------------------------------------------


@pytest.mark.parametrize("name", list(CONTRACT_FAILURES), ids=list(CONTRACT_FAILURES))
def test_the_contract_failures_of_the_cases_are_contract_failures(name: str) -> None:
    """expected_behavior_source: AC-3 (a file that "breaks the contract"); ADR-002 decision 3.

    This holds before the loader exists and guards the premise of the tests below: each document
    is read by the strict loader and refused by `ModelPolicy`.
    """
    assert contract_problems(CONTRACT_FAILURES[name]())


@pytest.mark.parametrize("name", list(ONE_PROBLEM), ids=list(ONE_PROBLEM))
def test_the_one_problem_of_a_case_is_the_one_that_the_case_names(name: str) -> None:
    """expected_behavior_source: AC-3; BC-32. This holds before the loader exists and guards the
    premise of the tests below: the field path (names of the contract, `[n]`, `unknown-key`,
    `(document)`) and the rule (the type of the validation error) of each document.
    """
    assert contract_problems(CONTRACT_FAILURES[name]()) == [ONE_PROBLEM[name]]


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("name", list(CONTRACT_FAILURES), ids=list(CONTRACT_FAILURES))
def test_a_file_that_breaks_the_contract_gives_one_orq_e541_per_error(
    read: Reader, name: str
) -> None:
    """expected_behavior_source: AC-3 ("A file that breaks the contract gives ORQ-E541 with the
    field path and the rule only"); BC-32; BC-37; ADR-002 consequences.

    One finding per validation error; each message holds the field path and the rule (the
    type of the pydantic error).
    """
    raw = CONTRACT_FAILURES[name]()

    assert_contract_findings(invalid(read(raw)), raw)


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("name", list(ONE_PROBLEM), ids=list(ONE_PROBLEM))
def test_the_message_holds_the_field_path_and_the_rule(read: Reader, name: str) -> None:
    """expected_behavior_source: AC-3 (the field path and the rule); BC-32. Examples of the
    brief: `models[0].routes[1].client` with `literal_error`, a missing field with `missing`, an
    unknown key as `unknown-key` with `extra_forbidden`, `string_pattern_mismatch`, and the empty
    path as `(document)`.
    """
    path, rule = ONE_PROBLEM[name]

    findings = invalid(read(CONTRACT_FAILURES[name]()))

    assert len(findings) == 1
    assert path in findings[0].message
    assert rule in findings[0].message


@EITHER_ENTRY_POINT
@pytest.mark.parametrize(
    "name", ["an-unknown-top-level-key", "an-unknown-key-in-a-model", "several-errors-at-once"]
)
def test_an_unknown_key_is_printed_as_the_fixed_word_and_never_as_itself(
    read: Reader, name: str
) -> None:
    """expected_behavior_source: AC-3 and AC-5 (an unknown key is never printed); BC-32;
    ORQLET-SEC-002. The key of these documents is `surprise`.
    """
    findings = invalid(read(CONTRACT_FAILURES[name]()))

    assert UNKNOWN_KEY in shown(findings)
    assert "surprise" not in shown(findings)


@EITHER_ENTRY_POINT
def test_a_v1_file_gives_one_finding_with_the_fixed_text_and_nothing_else(read: Reader) -> None:
    """expected_behavior_source: AC-3 ("A file whose `schema` is `orqlet.model-policy/v1` gives
    ORQ-E541 with the fixed text "a v1 file; migrate" and no other content of the file");
    BC-37; ADR-002 consequences ("a v1 file; migrate").
    """
    raw = v1_document()

    findings = invalid(read(raw))

    assert len(findings) == 1
    assert findings[0].code == CONTRACT
    assert findings[0].message == V1_TEXT
    assert_nothing_of_the_file_is_shown(findings, raw)


@EITHER_ENTRY_POINT
def test_a_valid_policy_whose_schema_says_v1_is_still_only_a_v1_file(read: Reader) -> None:
    """expected_behavior_source: AC-3 (a file whose `schema` is v1 gives exactly the fixed
    finding, whatever else it holds); BC-37.
    """
    raw = mutated(lambda d: d.update(schema="orqlet.model-policy/v1"))

    findings = invalid(read(raw))

    assert [(f.code, f.message) for f in findings] == [(CONTRACT, V1_TEXT)]


# --- AC-4: ORQ-E542, the credential scan -----------------------------------------------

FIELD_FOR_A_KEY: Where = ("profiles", 0, "capability")


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("placement", ["a-field-value", "a-comment"])
@pytest.mark.parametrize("kind", list(KEYS), ids=list(KEYS))
def test_a_key_in_a_valid_policy_is_one_orq_e542_per_hit_with_the_rule_and_the_line_only(
    read: Reader, kind: str, placement: str
) -> None:
    """expected_behavior_source: AC-4 ("each hit is the finding ORQ-E542 with the rule name and
    the line number only"); BC-32; ADR-002 decision 3; ORQLET-SEC-003.

    The contract passes: the key stands in a free text, or in a YAML comment that no contract
    sees. The rule names are those of the brief: `sk-key-prefix`, `xai-key-prefix`,
    `aiza-key-prefix`, and `token-prefix` of the integrations scan.
    """
    key = KEYS[kind]
    raw = (
        key_in_a_field(FIELD_FOR_A_KEY, key)
        if placement == "a-field-value"
        else key_in_a_comment(key)
    )
    expected_policy(raw)  # the premise: the contract accepts the file
    hits = find_policy_credentials(raw.decode("utf-8"))
    line = line_of(raw, key)
    assert (line, KEY_RULES[kind]) in {(hit.line, hit.rule) for hit in hits}

    findings = invalid(read(raw))

    assert codes(findings) == {CREDENTIAL}
    assert len(findings) == len(hits)
    for hit in hits:
        assert any(
            hit.rule in f.message and re.search(rf"\bline {hit.line}\b", f.message)
            for f in findings
        ), hit
    source_line = raw.decode("utf-8").split("\n")[line - 1]
    assert not leaks(shown(findings), key)
    assert not leaks(shown(findings), source_line.strip())


@EITHER_ENTRY_POINT
def test_a_key_in_a_value_and_one_in_a_comment_are_two_findings_on_two_lines(
    read: Reader,
) -> None:
    """expected_behavior_source: AC-4 (one finding per hit); BC-32; ADR-002 decision 3.

    A hit is a rule and a line, so the same rule on two lines is two findings.
    """
    key = KEYS["xai-key"]
    data = fixture()
    set_at(data, FIELD_FOR_A_KEY, f"use {key} here")
    raw = document(data) + f"\n# remember {key} for later\n".encode()
    lines = {line_of(raw, key), len(raw.decode("utf-8").split("\n")) - 1}

    findings = invalid(read(raw))

    assert len(lines) == 2
    assert codes(findings) == {CREDENTIAL}
    assert len(findings) == len(find_policy_credentials(raw.decode("utf-8")))
    assert len(findings) >= 2
    for number in lines:
        assert any(re.search(rf"\bline {number}\b", f.message) for f in findings), number


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("kind", list(KEYS), ids=list(KEYS))
def test_a_file_that_fails_its_contract_and_holds_a_key_is_invalid_and_shows_no_key(
    read: Reader, kind: str
) -> None:
    """expected_behavior_source: AC-3 and AC-4 (the contract is reported; a hit shows a rule and a
    line only); BC-32; ORQLET-SEC-003. Whether such a file also gets ORQ-E542 is not pinned.
    """
    key = KEYS[kind]
    data = fixture()
    set_at(data, FIELD_FOR_A_KEY, f"use {key} here")
    data["models"][0]["id"] = "has a space"
    raw = document(data)

    findings = invalid(read(raw))

    assert CONTRACT in codes(findings)
    assert codes(findings) <= {CONTRACT, CREDENTIAL}
    assert not leaks(shown(findings), key)


# --- AC-5: no finding shows a marker, a key or a value of the file ---------------------


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("name", list(REFUSALS), ids=list(REFUSALS))
def test_a_refused_value_is_reported_at_its_field_path_and_never_shown(
    read: Reader, name: str
) -> None:
    """expected_behavior_source: AC-5 (a refused field, with a marker in it); BC-32; C-1;
    ORQLET-SEC-002. The P-1 reviews asked for this: the contract's own error text for a refused
    path names the path, so the loader builds its messages from the field path and the type of
    the error and never from the contract's message.

    A model string with a space and `!`, a text with a character outside printable ASCII and a
    repository path that climbs out with `..`, each in its own field of a valid policy.
    """
    where, _, rule = REFUSALS[name]
    raw = refused_at(name, 1)

    findings = invalid(read(raw))

    assert_contract_findings(findings, raw)
    assert_nothing_of_the_file_is_shown(findings, raw)
    assert len(findings) == 1
    assert field_path(tuple(where), "") in findings[0].message
    assert rule in findings[0].message


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("name", list(STRANGER_SITES), ids=list(STRANGER_SITES))
def test_an_unknown_key_and_its_value_are_never_shown(read: Reader, name: str) -> None:
    """expected_behavior_source: AC-5 (an unknown key and an unknown key's value, at the top level
    and nested); BC-32; ORQLET-SEC-002.

    Two keys that no contract knows, one with a text and one with a map as value, each with a
    marker in the key and in the value. The findings print `unknown-key` and the rule.
    """
    raw = strangers_at(name, 1)

    findings = invalid(read(raw))

    assert_contract_findings(findings, raw)
    assert_nothing_of_the_file_is_shown(findings, raw)
    assert len(findings) == 2
    assert all(UNKNOWN_KEY in f.message and "extra_forbidden" in f.message for f in findings)


@EITHER_ENTRY_POINT
def test_no_finding_shows_a_marker_when_every_field_is_refused(read: Reader) -> None:
    """expected_behavior_source: AC-5 ("no finding of the loader contains a marker, a key of the
    file or a value of the file"); BC-32; C-1; ORQLET-SEC-002.

    A marker in each free-text field, each model field and each repository path field, every one
    of them refused, and unknown keys in every object: one finding per error and no marker.
    """
    raw = everything_refused(1)

    findings = invalid(read(raw))

    assert_contract_findings(findings, raw)
    assert_nothing_of_the_file_is_shown(findings, raw)
    assert len(findings) == len(REFUSALS) + 2 * len(STRANGER_SITES)


@EITHER_ENTRY_POINT
def test_no_finding_shows_a_marker_that_sits_in_a_field_that_is_valid(read: Reader) -> None:
    """expected_behavior_source: AC-5; BC-32; C-1; ORQLET-SEC-002.

    Every model, text and path field holds a valid marker; the file is invalid only because of
    one refused repository path and the unknown keys. The findings about those do not show the
    markers of the neighbours either.
    """
    raw = valid_values_next_to_one_refusal(1)
    assert len(markers_in(raw)) > 40

    findings = invalid(read(raw))

    assert_contract_findings(findings, raw)
    assert_nothing_of_the_file_is_shown(findings, raw)
    assert len(findings) == 1 + 2 * len(STRANGER_SITES)


def builder_of_refused(site: str) -> Callable[[int], bytes]:
    return lambda variant: refused_at(site, variant)


def builder_of_strangers(site: str) -> Callable[[int], bytes]:
    return lambda variant: strangers_at(site, variant)


BUILDERS: dict[str, Callable[[int], bytes]] = {
    "every-field-refused": everything_refused,
    "valid-fields-and-one-refusal": valid_values_next_to_one_refusal,
    **{f"refused-{name}": builder_of_refused(name) for name in REFUSALS},
    **{f"strangers-in-{name}": builder_of_strangers(name) for name in STRANGER_SITES},
}


@EITHER_ENTRY_POINT
@pytest.mark.parametrize("name", list(BUILDERS), ids=list(BUILDERS))
def test_the_findings_do_not_depend_on_any_value_or_key_of_the_file(
    read: Reader, name: str
) -> None:
    """expected_behavior_source: AC-5 ("A finding holds a code, a fixed text, a field path made of
    contract field names and a line number, nothing else"); BC-32; ORQLET-SEC-002.

    The same document with other markers, of the same length, gives the very same findings, so
    a finding is a function of the field path and the rule and of nothing that the file holds.
    """
    first = read(BUILDERS[name](1))
    second = read(BUILDERS[name](2))

    assert invalid(first)
    assert first == second


@pytest.mark.parametrize("name", list(BUILDERS), ids=list(BUILDERS))
def test_the_marker_files_give_the_same_findings_from_both_entry_points(name: str) -> None:
    """expected_behavior_source: AC-2 and AC-5 ("the same marker file read through the tree entry
    point gives equal findings"); ADR-007 decision 10; BC-32.
    """
    raw = BUILDERS[name](1)

    assert from_working_tree(raw) == from_git_tree(raw)
