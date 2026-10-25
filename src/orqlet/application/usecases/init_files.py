"""Turning renders, the profile and the lock into the `Desired` files of one `init`."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from orqlet.application.contracts.common import Contract
from orqlet.application.contracts.generated_lock import (
    BlockMarkers,
    GeneratedLock,
    GeneratorInfo,
    LockedFile,
    LockInput,
)
from orqlet.application.ports.documents import DocumentWriter
from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.application.ports.instruction_adapter import RenderedFile
from orqlet.application.ports.prompter import NoAnswerAvailable, Prompter, Question
from orqlet.domain.changeplan import Desired, Recorded
from orqlet.domain.errors import InvalidPath, OrqletError
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath

_BEGIN_NAME = re.compile(r"^<!-- orqlet:begin (?P<name>[a-z][a-z0-9-]*)")
_TEMPLATE_FILE = re.compile(r"pull_request_template\.(md|txt)", re.IGNORECASE)
_TEMPLATE_FOLDER = "pull_request_template"
DEFAULT_PR_TEMPLATE = ".github/pull_request_template.md"
PR_TARGETS_KEY = "repository.pull_requests.template.targets"


class MergeError(OrqletError):
    """Two client adapters disagree about a file they both write."""


def contract_bytes(writer: DocumentWriter, model: Contract) -> bytes:
    """A contract as a YAML file: schema first, fields in declaration order, no null noise."""
    return writer.dump(model.model_dump(mode="json", by_alias=True, exclude_none=True))


def block_name_of(begin_marker: str) -> str:
    match = _BEGIN_NAME.match(begin_marker)
    if match is None:
        raise MergeError(f"not a block marker: {begin_marker!r}")
    return match["name"]


def to_desired(rendered: RenderedFile) -> Desired:
    name = block_name_of(rendered.block[0]) if rendered.block is not None else None
    return Desired(
        path=rendered.path,
        owner=rendered.owner,
        file_class=rendered.file_class,
        content=rendered.content,
        block_name=name,
        insert_after_heading=False,
        inputs=rendered.inputs,
    )


def merge_rendered(files: Sequence[RenderedFile]) -> list[RenderedFile]:
    """One file per path and block. Identical files from several clients are one file.

    Two clients that write the same path with different bytes is a defect in an adapter, and
    the merge stops rather than pick one.
    """
    merged: dict[tuple[str, str | None], RenderedFile] = {}
    for rendered in files:
        key = (str(rendered.path), rendered.block[0] if rendered.block else None)
        earlier = merged.get(key)
        if earlier is not None and earlier != rendered:
            raise MergeError(f"clients render {rendered.path} differently")
        merged[key] = rendered
    return [merged[key] for key in sorted(merged)]


def lock_from_recorded(
    recorded: Sequence[Recorded], *, orqlet_version: str, standards_lock: str | None
) -> GeneratedLock:
    entries = []
    for item in sorted(recorded, key=lambda r: r.key):
        seeded = item.owner is OwnerMode.SEEDED
        entries.append(
            LockedFile(
                path=str(item.path),
                owner=item.owner,
                file_class=item.file_class,
                inputs=tuple(LockInput(id=i, version=v, sha256=h) for i, v, h in item.inputs),
                rendered_sha256=None if seeded else item.sha256,
                seeded_sha256=item.sha256 if seeded else None,
                block=None
                if item.block is None
                else BlockMarkers(begin=item.block[0], end=item.block[1]),
                entry=item.entry,
            )
        )
    return GeneratedLock(
        schema_id="orqlet.generated-lock/v1",
        generator=GeneratorInfo(orqlet=orqlet_version),
        standards_lock=standards_lock,
        files=tuple(entries),
    )


def recorded_from_lock(lock: GeneratedLock) -> list[Recorded]:
    recorded = []
    for entry in lock.files:
        sha = entry.seeded_sha256 if entry.owner is OwnerMode.SEEDED else entry.rendered_sha256
        recorded.append(
            Recorded(
                path=CanonicalPath.parse(entry.path),
                owner=entry.owner,
                file_class=entry.file_class,
                sha256=sha or "",
                block_name=None if entry.block is None else block_name_of(entry.block.begin),
                block=None if entry.block is None else (entry.block.begin, entry.block.end),
                entry=entry.entry,
                inputs=tuple((i.id, i.version, i.sha256) for i in entry.inputs),
            )
        )
    return recorded


# --- the pull-request template destination -----------------------------------------------------
def discover_pr_templates(project: FileSystem) -> tuple[tuple[str, ...], bool]:
    """Existing template files, and whether a `PULL_REQUEST_TEMPLATE/` folder exists."""
    candidates: list[str] = []
    has_folder = False
    for base in (".github", "docs", None):
        directory = None if base is None else CanonicalPath.parse(base)
        if directory is not None and project.kind(directory) is not FileKind.DIRECTORY:
            continue
        for name in project.list_dir(directory):
            try:
                child = CanonicalPath.parse(name) if directory is None else directory.child(name)
            except InvalidPath:
                continue  # `.git` and other names Orqlet never manages cannot be templates
            kind = project.kind(child)
            if kind is FileKind.FILE and _TEMPLATE_FILE.fullmatch(name):
                candidates.append(str(child))
            elif kind is FileKind.DIRECTORY and name.lower() == _TEMPLATE_FOLDER:
                has_folder = True
                candidates.extend(
                    str(child.child(inner))
                    for inner in project.list_dir(child)
                    if inner.lower().endswith((".md", ".txt"))
                )
    return tuple(sorted(candidates)), has_folder


def choose_pr_targets(
    candidates: tuple[str, ...],
    has_folder: bool,
    supplied: Mapping[str, str],
    prompter: Prompter,
) -> tuple[tuple[str, ...], bool]:
    """The files that receive the blocks, and whether the choice is still open.

    Orqlet never picks between several templates. With none it uses the default location, with
    exactly one it uses that file, and otherwise the maintainer chooses.
    """
    if not candidates:
        return (DEFAULT_PR_TEMPLATE,), False
    if len(candidates) == 1 and not has_folder:
        return candidates, False
    answer = supplied.get(PR_TARGETS_KEY)
    if answer is None and prompter.interactive:
        question = Question(
            PR_TARGETS_KEY,
            "Which pull-request template files receive the Orqlet blocks?",
            candidates,
        )
        try:
            answer = prompter.ask(question)
        except NoAnswerAvailable:
            answer = None
    if not answer:
        return (), True
    chosen = tuple(sorted({part.strip() for part in answer.split(",") if part.strip()}))
    if not chosen or any(item not in candidates for item in chosen):
        return (), True
    return chosen, False
