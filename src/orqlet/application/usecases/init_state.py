"""What kind of directory `init` was pointed at (proposal section 9.1.1)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orqlet.application.ports.filesystem import FileSystem
from orqlet.application.ports.scanner import ProjectScanner
from orqlet.application.ports.vcs import RepoState, Vcs
from orqlet.application.usecases.draft_profile import Origin
from orqlet.domain.errors import OrqletError

# Entries that do not make a directory "not empty". Everything else does, including the IDE and
# agent folders, because an IDE or Git can run what they contain.
HARMLESS_NAMES = frozenset({".DS_Store", "Thumbs.db", ".git"})


class InitRefused(OrqletError):
    """`init` stops with a reason and a code, and writes nothing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class RootState:
    origin: Origin
    needs_git: bool
    has_code: bool


def detect_root_state(
    project: FileSystem,
    vcs: Vcs,
    scanners: Sequence[ProjectScanner],
    *,
    confirm_new_project: bool,
    languages_found: bool = False,
) -> RootState:
    state = vcs.state()
    has_code = languages_found or any(scanner.applies(project) for scanner in scanners)
    entries = [name for name in project.list_dir(None) if name not in HARMLESS_NAMES]
    if state is RepoState.NESTED:
        raise InitRefused(
            "ORQ-E110",
            "This directory is inside another repository. Run init at the repository root, "
            "or pass that root with --root.",
        )
    if state is RepoState.HAS_COMMITS:
        return RootState("existing" if has_code else "existing-no-code", False, has_code)
    if state is RepoState.UNBORN_EMPTY:
        return RootState("unborn", False, has_code)
    needs_git = state is RepoState.NOT_A_REPOSITORY
    # An unborn HEAD that is not an empty fresh repository (other branches, objects or files) is
    # an existing repository, however empty its working tree looks: the maintainer is asked.
    ambiguous = state is RepoState.UNBORN_NONEMPTY and not has_code
    if not entries and not ambiguous:
        return RootState("empty", needs_git, False)
    if has_code:
        return RootState("existing", needs_git, True)
    if confirm_new_project:
        return RootState("unborn" if not needs_git else "empty", needs_git, False)
    raise InitRefused(
        "ORQ-E111",
        "This directory is not empty and holds no project that Orqlet recognises. "
        "If this is a new project in this directory, run init again with --new-project; "
        "otherwise pass the right directory with --root.",
    )
