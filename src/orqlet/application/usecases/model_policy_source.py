"""The one reader of `.orqlet/model-policy.yaml` (ADR-002 decision 3, ADR-005, BC-32).

The policy file is a repository file that a person writes, so it is untrusted input
(ORQLET-SEC-002). This module is the only place that reads it. It has two entry points and one
parser, so the same bytes give the same state on either path:

- `load_model_policy` reads the working tree through the project file system. It is the only one
  that can say the file was deleted, because only the working tree has a lock to compare with.
- `read_model_policy_at` reads one git tree through the `Vcs` port and touches nothing else.

Both return a state, never an exception. There are four states: absent, loaded, invalid and
deleted. Every reason a file is refused is one finding with a code that the person can act on:

- `ORQ-E540`: the file cannot be read, is not a regular file, is larger than 256 KiB, or breaks
  the rules for reading a document (anchors, aliases, repeated keys, depth, size).
- `ORQ-E541`: the file fails its contract, or is a v1 file that needs a migration.
- `ORQ-E542`: the file holds credential-shaped text.

A finding never carries a value or a key from the file. The contract finding is built only from the
field path and the type of the rule that failed, never from the text of a pydantic message, which
can repeat the value. A key that the contract does not know is named `unknown-key`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.ports.vcs import Vcs, VcsError
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.model_policy_scan import find_policy_credentials
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath

_PATH = ".orqlet/model-policy.yaml"
# The lock path is written here and not imported from `render_all`: that module will read the
# policy, so an import the other way would be a cycle.
_LOCK_PATH = ".orqlet/generated.lock.yaml"
_MAX_BYTES = 256 * 1024
_V1_SCHEMA = "orqlet.model-policy/v1"

_UNREADABLE = "ORQ-E540"
_CONTRACT = "ORQ-E541"
_CREDENTIAL = "ORQ-E542"


@dataclass(frozen=True, slots=True)
class PolicyAbsent:
    """There is no policy file: the baseline applies and nothing else is asked."""


@dataclass(frozen=True, slots=True)
class PolicyLoaded:
    """The file is there and passes the reading rules, the contract and the credential scan."""

    policy: ModelPolicy


@dataclass(frozen=True, slots=True)
class PolicyInvalid:
    """The file is there and is refused; each finding says one reason."""

    findings: tuple[Finding, ...]


@dataclass(frozen=True, slots=True)
class PolicyDeleted:
    """The file is gone from the working tree, but the lock still lists it as seeded."""


type PolicyState = PolicyAbsent | PolicyLoaded | PolicyInvalid | PolicyDeleted


class PolicyServices(Protocol):
    """What the reader needs from the caller's services, so every command can pass its own."""

    @property
    def project(self) -> FileSystem: ...

    @property
    def vcs(self) -> Vcs: ...

    @property
    def loader(self) -> DocumentLoader: ...


def model_policy_path() -> CanonicalPath:
    """Where the policy file lives."""
    return CanonicalPath.parse(_PATH)


def load_model_policy(services: PolicyServices) -> PolicyState:
    """The policy in the working tree. Does not use the `Vcs` port."""
    target = model_policy_path()
    try:
        kind = services.project.kind(target)
        if kind is None:
            return PolicyDeleted() if _lock_lists_policy_as_seeded(services) else PolicyAbsent()
        if kind is not FileKind.FILE:
            return _invalid(_UNREADABLE, "the policy path is not a regular file")
        raw = services.project.read_bytes(target)
    except (FileSystemError, OSError):
        return _invalid(_UNREADABLE, "the policy file cannot be read safely")
    return _parse(services.loader, raw)


def read_model_policy_at(
    services: PolicyServices, tree: str
) -> PolicyAbsent | PolicyLoaded | PolicyInvalid:
    """The policy in the git tree `tree`. Does not use the project file system.

    A tree has no lock to compare with, so a file that is not there is absent, never deleted. The
    port reads a blob and does not say whether the entry is a link, so a link whose target text is
    a valid policy reads as a file here; the working-tree reader refuses a link.
    """
    try:
        raw = services.vcs.read_at(tree, _PATH)
    except VcsError:
        return _invalid(_UNREADABLE, "the policy file cannot be read from the tree")
    if raw is None:
        return PolicyAbsent()
    return _parse(services.loader, raw)


def _lock_lists_policy_as_seeded(services: PolicyServices) -> bool:
    """True only when a valid lock lists the policy file with the owner `seeded`.

    A lock that is missing, unreadable or invalid says nothing about the policy, so the answer is
    no and the file reads as absent: the lock is validated elsewhere, and a broken lock is not a
    reason to refuse the policy.
    """
    lock_path = CanonicalPath.parse(_LOCK_PATH)
    try:
        if services.project.kind(lock_path) is not FileKind.FILE:
            return False
        lock = load_contract(
            services.loader,
            GeneratedLock,
            services.project.read_bytes(lock_path),
            source=_LOCK_PATH,
        )
    except (FileSystemError, OSError, DocumentError):
        return False
    return any(row.path == _PATH and row.owner is OwnerMode.SEEDED for row in lock.files)


def _parse(loader: DocumentLoader, raw: bytes) -> PolicyLoaded | PolicyInvalid:
    """The one parser both entry points use: reading rules, contract, then credential scan."""
    if len(raw) > _MAX_BYTES:
        return _invalid(_UNREADABLE, "the policy file is larger than 256 KiB")
    try:
        data = loader.load(raw, source=_PATH)
    except DocumentError:
        # The loader's own message can quote the file, so it is not passed on.
        return _invalid(_UNREADABLE, "the policy file breaks the rules for reading a document")
    if isinstance(data, dict) and data.get("schema") == _V1_SCHEMA:
        return _invalid(_CONTRACT, "a v1 file; migrate")
    try:
        policy = ModelPolicy.model_validate(data)
    except ValidationError as exc:
        return PolicyInvalid(
            tuple(
                _finding(_CONTRACT, _contract_message(error["loc"], error["type"]))
                for error in exc.errors(include_input=False, include_url=False)
            )
        )
    # After the contract, as the integrations reader does: a file that fails its contract is
    # reported for that, and a file that passes it is then checked for secrets.
    hits = find_policy_credentials(raw.decode("utf-8", errors="replace"))
    if hits:
        return PolicyInvalid(
            tuple(
                _finding(_CREDENTIAL, f"line {hit.line}: the rule {hit.rule} matched")
                for hit in hits
            )
        )
    return PolicyLoaded(policy)


def _contract_message(location: tuple[int | str, ...], rule: str) -> str:
    """Where in the document a rule failed and which rule, and nothing the file wrote.

    A name in a location is a field of the contract, except the last part of an unknown-key error:
    that is the file's own key, so it is replaced.
    """
    parts: list[str] = []
    for index, part in enumerate(location):
        if isinstance(part, int):
            parts.append(f"[{part}]")
        elif rule == "extra_forbidden" and index == len(location) - 1:
            parts.append("unknown-key")
        else:
            parts.append(part)
    where = ".".join(parts).replace(".[", "[") or "(document)"
    return f"the policy fails its contract at {where}: {rule}"


def _invalid(code: str, message: str) -> PolicyInvalid:
    return PolicyInvalid((_finding(code, message),))


def _finding(code: str, message: str) -> Finding:
    return Finding(code=code, message=message, severity=Severity.ERROR, path=_PATH)
