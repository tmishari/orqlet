"""The user scope on disk: allow-listed roots, their sub-paths, and the root checks (ADR-002).

`UserScopeFileSystem` maps the first segment of a path (`claude/skills/orqlet/SKILL.md`) to one
root and hands the rest to a `LocalFileSystem` there, which refuses every link below the root. Only
the sub-paths of decision 1 can be written or read; the folders that lead to them can be listed.

`FsUserRootInspector` validates each root before anything reads it (decision 1a): not a link, under
the real home (the data directory may be elsewhere), owned by the user on POSIX, and not inside a
Git work tree, decided by looking for `.git` with no process. It creates and tightens folders only
in `prepare`, which the use case calls after the person's yes.

The checks and the later opens are separate system calls, so a process of the same account that
swaps a folder in between can still win a race; `prepare` validates again just before it opens.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orqlet.adapters.fs.local_fs import LocalFileSystem, is_link
from orqlet.application.contracts.user_scope import UserHome
from orqlet.application.ports.filesystem import FileKind, PathNotFound
from orqlet.application.ports.user_scope import (
    USER_PREFIXES,
    PathNotWritable,
    ReadOnlyUserScope,
    RootState,
    UserPrefix,
    UserRootRefused,
)
from orqlet.domain.paths import CanonicalPath

_PRIVATE_DIR_MODE = 0o700
_WIDE_BITS = 0o077
_ORQLET_FOLDERS = ("journal", "backups")
_WINDOWS_DATA_WARNING = (
    "the data directory is outside the home folder and its access is not checked on Windows; "
    "this risks the confidentiality and integrity of the journals and backups, because another "
    "account able to write there could plant journals and backups that rollback --user and "
    "adoption would trust"
)


def _owned(name: str) -> bool:
    return name == "orqlet" or name.startswith(("orqlet-", "ponytail"))


def _owned_markdown(name: str) -> bool:
    return name.endswith(".md") and _owned(name.removesuffix(".md"))


def _owned_with_extension(name: str) -> bool:
    stem, dot, extension = name.partition(".")
    return bool(dot and extension) and _owned(stem)


class _SubPath:
    """One writable entry of decision 1: a file in a folder, or a folder tree."""

    def __init__(self, first: str, *rest: str | Callable[[str], bool], tree: bool = False) -> None:
        self.first = first
        self._segments: tuple[str | Callable[[str], bool], ...] = (first, *rest)
        self._tree = tree

    def holds(self, parts: tuple[str, ...]) -> bool:
        if len(parts) < len(self._segments) or (
            len(parts) > len(self._segments) and not self._tree
        ):
            return False
        return all(
            part == segment if isinstance(segment, str) else segment(part)
            for part, segment in zip(parts, self._segments, strict=False)
        )


_SUB_PATHS: Mapping[str, tuple[_SubPath, ...]] = {
    "claude": (
        _SubPath("skills", _owned, tree=True),
        _SubPath("agents", _owned_markdown),
        _SubPath("rules", "orqlet-foundation.md"),
        _SubPath("settings.json"),
    ),
    "cursor": (_SubPath("agents", _owned_markdown), _SubPath("hooks.json")),
    "codex": (
        _SubPath("agents", _owned_with_extension),
        _SubPath("AGENTS.md"),
        _SubPath("hooks.json"),
    ),
    "agents": (_SubPath("skills", _owned, tree=True),),
    "copilot": (_SubPath("skills", _owned, tree=True), _SubPath("hooks", "orqlet.json")),
    "data": (_SubPath("manifest.json"), _SubPath("cursor-user-rules.md")),
}


class _Access(Enum):
    NONE = "none"
    BOUNDARY = "boundary"  # a root, or a folder that leads to a sub-path: list it, never remove it
    WRITABLE = "writable"


def _access(prefix: str, rest: tuple[str, ...]) -> _Access:
    sub_paths = _SUB_PATHS[prefix]
    if any(sub_path.holds(rest) for sub_path in sub_paths):
        return _Access.WRITABLE
    leads_somewhere = any(rest == (sub_path.first,) for sub_path in sub_paths)
    return _Access.BOUNDARY if not rest or leads_somewhere else _Access.NONE


class UserScopeFileSystem:
    """The composite `FileSystem` of the user scope; a `None` root is missing and reads as empty."""

    def __init__(
        self,
        roots: Mapping[str, Path | None],
        *,
        writable: bool,
        refused: Mapping[str, UserRootRefused] | None = None,
    ) -> None:
        unknown = set(roots) - set(_SUB_PATHS)
        if unknown:
            raise PathNotWritable(f"not a user-scope prefix: {', '.join(sorted(unknown))}")
        self._roots = {
            prefix: None if root is None else LocalFileSystem(root)
            for prefix, root in roots.items()
        }
        self._writable = writable
        self._refused = dict(refused or {})

    # --- port -------------------------------------------------------------------------
    def kind(self, path: CanonicalPath) -> FileKind | None:
        local, rest = self._resolve(path, _Access.BOUNDARY)
        if local is None:
            return None
        return FileKind.DIRECTORY if rest is None else local.kind(rest)

    def read_bytes(self, path: CanonicalPath) -> bytes:
        local, rest = self._resolve(path, _Access.WRITABLE)
        if local is None or rest is None:
            raise PathNotFound(str(path))
        return local.read_bytes(rest)

    def read_prefix(self, path: CanonicalPath, limit: int) -> bytes:
        local, rest = self._resolve(path, _Access.WRITABLE)
        if local is None or rest is None:
            raise PathNotFound(str(path))
        return local.read_prefix(rest, limit)

    def write_atomic(self, path: CanonicalPath, data: bytes) -> None:
        self._writing(path).write_atomic(_rest(path), data)

    def delete(self, path: CanonicalPath) -> None:
        self._writing(path).delete(_rest(path))

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        if path is None:
            return tuple(sorted(self._roots))
        local, rest = self._resolve(path, _Access.BOUNDARY)
        if local is None:
            return ()
        return local.list_dir(rest)

    def make_dir(self, path: CanonicalPath) -> None:
        self._writing(path).make_dir(_rest(path))

    def remove_empty_dir(self, path: CanonicalPath) -> None:
        self._refuse_when_read_only()
        local, rest = self._resolve(path, _Access.BOUNDARY)
        if _access(path.parts[0], path.parts[1:]) is _Access.BOUNDARY:
            return
        if local is not None and rest is not None:
            local.remove_empty_dir(rest)

    # --- internals -----------------------------------------------------------------------
    def _refuse_when_read_only(self) -> None:
        if not self._writable:
            raise ReadOnlyUserScope("the user scope is read-only until the person consents")

    def _resolve(
        self, path: CanonicalPath, needed: _Access
    ) -> tuple[LocalFileSystem | None, CanonicalPath | None]:
        """The root's file system and the rest of the path, after the allow-list check."""
        prefix, rest = path.parts[0], path.parts[1:]
        if prefix in self._refused:
            raise self._refused[prefix]
        if prefix not in self._roots:
            raise PathNotWritable(str(path))
        access = _access(prefix, rest)
        if access is _Access.NONE or (needed is _Access.WRITABLE and access is not needed):
            raise PathNotWritable(str(path))
        return self._roots[prefix], CanonicalPath(rest) if rest else None

    def _writing(self, path: CanonicalPath) -> LocalFileSystem:
        self._refuse_when_read_only()
        local, rest = self._resolve(path, _Access.WRITABLE)
        if local is None or rest is None:
            raise PathNotWritable(str(path))
        return local


def _rest(path: CanonicalPath) -> CanonicalPath:
    return CanonicalPath(path.parts[1:])


_CURRENT_USER_ID: int | None = os.getuid() if hasattr(os, "getuid") else None


class FsUserRootInspector:
    """The `UserRootInspector` on the local disk; `windows` and `user_id` let a test fake both."""

    def __init__(
        self,
        *,
        environment: Mapping[str, str],
        data_directory: Path,
        windows: bool = os.name == "nt",
        user_id: int | None = _CURRENT_USER_ID,
    ) -> None:
        self._environment = dict(environment)
        self._data_directory = data_directory
        self._windows = windows
        self._user_id = None if windows else user_id
        self._home: Path | None = None

    def inspect(self, home: UserHome) -> Mapping[UserPrefix, RootState]:
        self._home = Path(os.path.realpath(home.path))
        return {prefix: self._inspect(prefix, self._home) for prefix in USER_PREFIXES}

    def planning_fs(self, states: Mapping[UserPrefix, RootState]) -> UserScopeFileSystem:
        refused: dict[str, UserRootRefused] = {
            prefix: _refusal(state) for prefix, state in states.items() if state.refusal is not None
        }
        roots: dict[str, Path | None] = {
            prefix: Path(state.path) if state.exists and prefix not in refused else None
            for prefix, state in states.items()
        }
        return UserScopeFileSystem(roots, writable=False, refused=refused)

    def prepare(self, states: Mapping[UserPrefix, RootState]) -> UserScopeFileSystem:
        for state in states.values():
            if state.refusal is not None:
                raise _refusal(state)
        self._validate_again(states)
        for state in states.values():
            for folder in state.creates:
                _make_private_dir(Path(folder))
            for folder in state.tightens:
                os.chmod(folder, _PRIVATE_DIR_MODE)
        self._validate_again(states)
        roots: dict[str, Path | None] = {}
        for prefix, state in states.items():
            opened = LocalFileSystem(Path(state.path)).root
            if str(opened) != state.path:
                raise _moved(state, str(opened))
            roots[prefix] = opened
        return UserScopeFileSystem(roots, writable=True)

    # --- validation ----------------------------------------------------------------------
    def _validate_again(self, states: Mapping[UserPrefix, RootState]) -> None:
        if self._home is None:
            raise RuntimeError("prepare() needs the states of inspect()")
        for prefix, pinned in states.items():
            fresh = self._inspect(prefix, self._home)
            if fresh.refusal is not None:
                raise _refusal(fresh)
            if fresh.path != pinned.path:
                raise _moved(pinned, fresh.path)

    def _inspect(self, prefix: UserPrefix, home: Path) -> RootState:
        configured, variable = self._configured(prefix, home)
        located = _locate(configured)
        reason = self._reason(prefix, configured, located, home)
        is_data = prefix == "data" and reason is None
        outside_home = not located.real.is_relative_to(home)
        return RootState(
            prefix=prefix,
            variable=variable,
            path=str(located.real),
            exists=located.exists,
            refusal=None
            if reason is None
            else f"{variable}: the {prefix} root {configured} {reason}",
            creates=located.creates,
            tightens=_wide_folders(configured) if is_data and not self._windows else (),
            warning=_WINDOWS_DATA_WARNING if is_data and self._windows and outside_home else None,
        )

    def _configured(self, prefix: UserPrefix, home: Path) -> tuple[Path, str]:
        home_variable = "USERPROFILE" if self._windows else "HOME"
        if prefix == "data":
            return self._data_directory / "user", "ORQLET_DATA_DIR"
        override = {"codex": "CODEX_HOME", "copilot": "COPILOT_HOME"}.get(prefix)
        if override is not None and self._environment.get(override):
            return Path(self._environment[override]), override
        return home / f".{prefix}", home_variable

    def _reason(
        self, prefix: UserPrefix, configured: Path, located: _Located, home: Path
    ) -> str | None:
        if not configured.is_absolute():
            return "is not an absolute path"
        checked = (self._data_directory, configured) if prefix == "data" else (configured,)
        if prefix == "data":
            checked = (*checked, *(configured / name for name in _ORQLET_FOLDERS))
        for folder in checked:
            if is_link(folder):
                return f"is a link ({folder})"
        if located.exists and not located.real.is_dir():
            return "is not a folder"
        if prefix != "data" and (located.real == home or not located.real.is_relative_to(home)):
            return "is not below the home folder"
        if self._user_id is not None:
            for folder in checked:
                if os.path.lexists(folder) and os.lstat(folder).st_uid != self._user_id:
                    return f"is owned by another user ({folder})"
        if _inside_work_tree(located.real if located.exists else located.ancestor):
            return "lies inside a Git work tree"
        return None


@dataclass(frozen=True, slots=True)
class _Located:
    """Where a root stands on disk: its real path, below its nearest existing ancestor."""

    real: Path
    ancestor: Path  # the root itself when it exists
    exists: bool
    creates: tuple[str, ...]  # the missing folders down to the root, outermost first


def _locate(configured: Path) -> _Located:
    if os.path.lexists(configured):
        real = Path(os.path.realpath(configured))
        return _Located(real, real, True, ())
    missing: list[str] = []
    current = configured
    while not os.path.lexists(current):
        missing.insert(0, current.name)
        current = current.parent
    ancestor = Path(os.path.realpath(current))
    creates = tuple(str(ancestor.joinpath(*missing[: index + 1])) for index in range(len(missing)))
    return _Located(ancestor.joinpath(*missing), ancestor, False, creates)


def _inside_work_tree(start: Path) -> bool:
    return any(os.path.lexists(folder / ".git") for folder in (start, *start.parents))


def _wide_folders(user: Path) -> tuple[str, ...]:
    wide = []
    for folder in (user, *(user / name for name in _ORQLET_FOLDERS)):
        try:
            info = os.lstat(folder)
        except FileNotFoundError:
            continue
        if stat.S_ISDIR(info.st_mode) and info.st_mode & _WIDE_BITS:
            wide.append(str(folder))
    return tuple(wide)


def _make_private_dir(folder: Path) -> None:
    try:
        folder.mkdir(mode=_PRIVATE_DIR_MODE)
    except FileExistsError:
        return  # validated again before it is opened
    os.chmod(folder, _PRIVATE_DIR_MODE)


def _refusal(state: RootState) -> UserRootRefused:
    return UserRootRefused(state.prefix, state.variable, state.refusal or state.variable)


def _moved(state: RootState, actual: str) -> UserRootRefused:
    return UserRootRefused(
        state.prefix,
        state.variable,
        f"{state.variable}: the {state.prefix} root resolves to {actual}, "
        f"not the pinned {state.path}",
    )
