"""The review records that a changed agent file makes stale (ORQ-W547, ADR-003 decision 7).

A review record binds one agent file: `agent.binding_ref` and `agent.client` name it, and the
definition digest in the record is that file's bytes at the time of the review. A model pin changes
the bytes of a reviewer's agent file, and with them the protected files and `protected_set_digest`,
so a record made before the pin is about a file that no longer exists. This module finds those
records so that `upgrade` can say so before it writes. It decides nothing and changes nothing.

The records are read through the `FileSystem` port with the strict loader, and a record that cannot
be read, is too large, or does not validate is skipped, because it is not a record that anything
binds to. Only the paths that match the review-record pattern of `evidence_artifacts` are read.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.review_result import ReviewResult
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.usecases.binding_inputs import AGENT_FILES
from orqlet.application.usecases.validation import TASK_ROOT
from orqlet.domain.binding import RecordKind
from orqlet.domain.changeplan import PlannedWrite
from orqlet.domain.errors import InvalidPath
from orqlet.domain.evidence_artifacts import MAX_EVIDENCE_BYTES, parse_evidence_path
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.paths import CanonicalPath

STALE_REVIEW = "ORQ-W547"
MAX_LISTED = 20

_AGENT_PREFIXES = tuple(pattern.split("{ref}")[0] for pattern in AGENT_FILES.values())


def stale_review_records(
    project: FileSystem, loader: DocumentLoader, writes: Iterable[PlannedWrite]
) -> tuple[str, ...]:
    """The paths of the review records whose agent file one of `writes` changes, sorted.

    A proposal changes no live file and so makes no record stale. Nothing is read when no write
    touches an agent file.
    """
    changed = {
        write.path
        for write in writes
        if not write.is_proposal and str(write.path).startswith(_AGENT_PREFIXES)
    }
    if not changed:
        return ()
    return tuple(
        sorted(
            path
            for path, record in _review_records(project, loader)
            if _agent_file(record) in changed
        )
    )


def stale_review_finding(paths: Sequence[str]) -> Finding | None:
    """ORQ-W547 for these record paths, or `None` when there are none."""
    if not paths:
        return None
    listed = ", ".join(paths[:MAX_LISTED])
    more = f" and {len(paths) - MAX_LISTED} more" if len(paths) > MAX_LISTED else ""
    return Finding(
        STALE_REVIEW,
        "This upgrade changes agent files that review records name, so those records no longer "
        f"describe the current files: {listed}{more}. Designs and plans in progress will then "
        "show changed inputs. The person decides what to do about them; Orqlet changes no record.",
        Severity.WARNING,
    )


def _agent_file(record: ReviewResult) -> CanonicalPath | None:
    """The agent file the record binds, or `None` for a client without agent files."""
    pattern = AGENT_FILES.get(record.agent.client)
    if pattern is None:
        return None
    try:
        return CanonicalPath.parse(pattern.format(ref=record.agent.binding_ref))
    except InvalidPath:  # a reference that is not a file name
        return None


def _review_records(
    project: FileSystem, loader: DocumentLoader
) -> Iterator[tuple[str, ReviewResult]]:
    for task in _names(project, TASK_ROOT):
        folder = f"{TASK_ROOT}/{task}/reviews"
        for name in _names(project, folder):
            path = f"{folder}/{name}"
            identity = parse_evidence_path(path)
            if identity is None or identity.kind is not RecordKind.REVIEW:
                continue
            record = _read(project, loader, path)
            if record is not None:
                yield path, record


def _names(project: FileSystem, folder: str) -> tuple[str, ...]:
    try:
        return project.list_dir(CanonicalPath.parse(folder))
    except (FileSystemError, InvalidPath, OSError):  # no folder, a link, or no valid name
        return ()


def _read(project: FileSystem, loader: DocumentLoader, path: str) -> ReviewResult | None:
    try:
        target = CanonicalPath.parse(path)
        if project.kind(target) is not FileKind.FILE:
            return None
        raw = project.read_bytes(target)
        if len(raw) > MAX_EVIDENCE_BYTES:
            return None
        return load_contract(loader, ReviewResult, raw, source=path)
    except (FileSystemError, DocumentError, InvalidPath, OSError):
        return None
