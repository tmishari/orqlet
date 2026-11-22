"""`orqlet hook session-start|post-edit`: advisory context for a client's session (ADR-004).

A client starts the hook in any folder it opens, including an untrusted clone, so the hook trusts
nothing it reads. It finds the project by an upward `.orqlet/` search that never leaves the home,
reads at most two bounded files, starts no process, writes nothing, and fills fixed templates whose
only variable fields are a version, a closed next step or a representable path (decision 1a). On
any doubt it gives no context; a client cannot be blocked by a hook, so silence is the safe answer.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

from orqlet.application.contracts.common import RenderClientId
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.hook_payload import (
    HookFields,
    HookPayloadError,
    read_hook_fields,
)
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.user_scope import UserHome
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystemError, ReadOnlyFiles
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.bounded_read import BoundedReadRefused, read_bounded
from orqlet.application.usecases.foundation import compose_foundation
from orqlet.application.usecases.status import GlobalSources, NextStep, read_project_status
from orqlet.domain.errors import InvalidPath
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.representable import representable_path, representable_version
from orqlet.domain.strict_json import StrictJsonError, parse_object

MAX_STATUS_CHARACTERS = 1200
MAX_AGENTS_BYTES = 262_144
MAX_SEARCH_LEVELS = 64  # parents of the working folder that the search may visit

SESSION_TEMPLATE = "templates/hook-session-start.md"
POST_EDIT_TEMPLATE = "templates/hook-post-edit.md"
PROJECT_FOLDER = ".orqlet"
AGENTS_FILE = CanonicalPath.parse("AGENTS.md")
GENERATED_LOCK = CanonicalPath.parse(".orqlet/generated.lock.yaml")

_SLOT = re.compile(r"\{\{([a-z]+)\}\}")
_BASELINE_BEGIN = re.compile(r"^<!-- orqlet:begin baseline(?: [^\r\n]*)? -->\r?$", re.MULTILINE)


class HookEvent(StrEnum):
    SESSION_START = "session-start"
    POST_EDIT = "post-edit"


class DeadlinePassed(FileSystemError):
    """The time budget is spent, so every later read fails as a file-system error would."""


@dataclass(frozen=True, slots=True)
class HookServices:
    home: UserHome
    home_files: ReadOnlyFiles | None  # rooted at `home`; `None` when the home cannot be opened
    sources: GlobalSources
    workflow: WorkflowSource
    expired: Callable[[], bool]  # True once the internal deadline has passed


def run_hook(
    event: HookEvent, client: RenderClientId, payload: bytes, services: HookServices
) -> dict[str, object]:
    """The client's output object; `{}` when there is no context to give."""
    fields = _fields(client, payload)
    if fields is not None and client == "claude-code" and fields.from_cursor:
        return {}  # Cursor runs Claude Code's hooks too and answers through its own registration
    if event is HookEvent.POST_EDIT:
        return _post_edit(client, fields, services)
    return _session_start(client, fields, services)


def _fields(client: RenderClientId, payload: bytes) -> HookFields | None:
    try:
        return read_hook_fields(client, parse_object(payload))
    except (StrictJsonError, HookPayloadError):
        return None


# --- session start -----------------------------------------------------------------------------


def _session_start(
    client: RenderClientId, fields: HookFields | None, services: HookServices
) -> dict[str, object]:
    files = _reader(services)
    start = None if fields is None else _below_home(services.home, fields.working_folder)
    status: str | None = None
    agents_folder: tuple[str, ...] | None = None
    if files is not None and start is not None:
        root = _search(files, start)
        status = None if root is None else _status(_Below(files, root), services)
        agents_folder = start if root is None else root
    texts = [] if status is None else [status]
    if client == "copilot" and not _has_baseline(files, agents_folder):
        # The foundation is packaged text, so it is safe to give wherever the hook cannot read.
        texts.append(compose_foundation(services.workflow))
    return _session_output(client, "\n".join(texts)) if texts else {}


def _status(project: ReadOnlyFiles, services: HookServices) -> str | None:
    """The filled template, or `None` when the status must not be acted on (Q-72, Q-77)."""
    report = read_project_status(_timed_sources(services), project)
    if report.not_run or report.next is NextStep.REFUSE_HOME_IS_WORK_TREE:
        return None
    values = {
        "installed": representable_version(report.installed),
        "project": representable_version(report.project),
        "next": str(report.next),
    }
    text = _fill(services.workflow.read_text(SESSION_TEMPLATE), values)
    return text if len(text) <= MAX_STATUS_CHARACTERS else None


def _has_baseline(files: ReadOnlyFiles | None, folder: tuple[str, ...] | None) -> bool:
    """Whether AGENTS.md has the baseline block; a file that cannot be read has none."""
    if files is None or folder is None:
        return False
    try:
        content = read_bounded(_Below(files, folder), AGENTS_FILE, limit=MAX_AGENTS_BYTES)
        text = None if content is None else content.decode("utf-8-sig")
    except (BoundedReadRefused, FileSystemError, OSError, UnicodeDecodeError):
        return False
    return text is not None and _BASELINE_BEGIN.search(text) is not None


def _session_output(client: RenderClientId, text: str) -> dict[str, object]:
    if client in ("claude-code", "codex"):
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}
    if client == "cursor":
        return {"additional_context": text}
    return {"additionalContext": text}


# --- post edit ---------------------------------------------------------------------------------


def _post_edit(
    client: RenderClientId, fields: HookFields | None, services: HookServices
) -> dict[str, object]:
    """One line when an Orqlet-owned file was edited; only Claude Code's return is cited."""
    files = _reader(services)
    if client != "claude-code" or fields is None or files is None:
        return {}
    start = _below_home(services.home, fields.working_folder)
    edited = _below_home(services.home, fields.edited_path)
    if start is None or edited is None:
        return {}
    root = _search(files, start)
    if root is None or len(edited) <= len(root) or edited[: len(root)] != root:
        return {}
    relative = CanonicalPath(edited[len(root) :])
    shown = representable_path(str(relative))
    if shown is None or not _owned_file(files, root, relative, services.sources.loader):
        return {}
    line = _fill(services.workflow.read_text(POST_EDIT_TEMPLATE), {"path": shown})
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": line}}


def _owned_file(
    files: ReadOnlyFiles, root: tuple[str, ...], relative: CanonicalPath, loader: DocumentLoader
) -> bool:
    """A regular file, not a link, that the project lock lists as Orqlet's own."""
    project = _Below(files, root)
    try:
        if project.kind(relative) is not FileKind.FILE:
            return False
        content = read_bounded(project, GENERATED_LOCK)
        if content is None:
            return False
        lock = load_contract(loader, GeneratedLock, content, source=str(GENERATED_LOCK))
    except (BoundedReadRefused, FileSystemError, OSError, DocumentError):
        return False
    return any(
        entry.owner is OwnerMode.ORQLET and _same_path(entry.path, relative) for entry in lock.files
    )


def _same_path(text: str, path: CanonicalPath) -> bool:
    try:
        return CanonicalPath.parse(text).parts == path.parts
    except InvalidPath:
        return False


# --- finding the project -----------------------------------------------------------------------


def _below_home(home: UserHome, path: str | None) -> tuple[str, ...] | None:
    """The components of `path` below the home, or `None` when it is not there or not canonical.

    A relative path, another drive or a sibling folder never starts with the home and a separator,
    so nothing outside the home is ever looked at (ADR-004 decision 5).
    """
    if path is None:
        return None
    if path == home.path:
        return ()
    windows = "\\" in home.path
    for separator in ("/", "\\") if windows else ("/",):
        prefix = home.path.rstrip(separator) + separator
        if path.startswith(prefix):
            rest = path[len(prefix) :]
            try:
                return CanonicalPath.parse(rest.replace("\\", "/") if windows else rest).parts
            except InvalidPath:
                return None
    return None


def _search(files: ReadOnlyFiles, start: tuple[str, ...]) -> tuple[str, ...] | None:
    """The folder holding `.orqlet/`, from `start` up to 64 levels, never the home or above it.

    The hook cannot run Git to tell whether the home is a work tree, so the home is never a
    project root (Q-77).
    """
    lowest = max(1, len(start) - MAX_SEARCH_LEVELS)
    try:
        for depth in range(len(start), lowest - 1, -1):
            kind = files.kind(CanonicalPath((*start[:depth], PROJECT_FOLDER)))
            if kind is FileKind.DIRECTORY:
                return start[:depth]
            if kind is not None:
                return None  # a file or a link at `.orqlet` is not a project to read
    except (FileSystemError, OSError):  # a link on the way, a refused folder, the deadline
        return None
    return None


# --- readers and templates ---------------------------------------------------------------------


def _reader(services: HookServices) -> ReadOnlyFiles | None:
    files = services.home_files
    return None if files is None else _Timed(files, services.expired)


def _timed_sources(services: HookServices) -> GlobalSources:
    user_data = services.sources.user_data
    if user_data is None:
        return services.sources
    return replace(services.sources, user_data=_Timed(user_data, services.expired))


def _fill(template: str, values: Mapping[str, str | None]) -> str:
    """The template with its slots filled; a line whose value is missing is left out."""
    lines = []
    for line in template.rstrip("\n").split("\n"):
        names = _SLOT.findall(line)
        if any(values.get(name) is None for name in names):
            continue
        lines.append(_SLOT.sub(lambda match: values[match[1]] or "", line))
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class _Timed:
    """A reader that refuses every call once the deadline has passed."""

    files: ReadOnlyFiles
    expired: Callable[[], bool]

    def kind(self, path: CanonicalPath) -> FileKind | None:
        self._check()
        return self.files.kind(path)

    def read_prefix(self, path: CanonicalPath, limit: int) -> bytes:
        self._check()
        return self.files.read_prefix(path, limit)

    def _check(self) -> None:
        if self.expired():
            raise DeadlinePassed("the hook's time budget is spent")


@dataclass(frozen=True, slots=True)
class _Below:
    """The home reader seen from one folder below the home, such as the project root."""

    files: ReadOnlyFiles
    folder: tuple[str, ...]

    def kind(self, path: CanonicalPath) -> FileKind | None:
        return self.files.kind(CanonicalPath((*self.folder, *path.parts)))

    def read_prefix(self, path: CanonicalPath, limit: int) -> bytes:
        return self.files.read_prefix(CanonicalPath((*self.folder, *path.parts)), limit)
