"""`PATH` lookup done by reading folders, as a shell would resolve a bare command name.

No process is started and nothing is written: the locator only lists folders and reads file modes.
"""

from __future__ import annotations

import os
import stat

from orqlet.application.ports.executables import ExecutableLookup, OnPath

_DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD"


class PathExecutableLocator:
    def __init__(
        self,
        path_value: str,
        running: str | None,
        *,
        windows: bool | None = None,
        pathext: str | None = None,
    ) -> None:
        self._elements = path_value.split(os.pathsep)
        self._running = running
        self._windows = os.name == "nt" if windows is None else windows
        extensions = (pathext or _DEFAULT_PATHEXT).split(";")
        self._extensions = [ext for ext in extensions if ext] if self._windows else []

    def locate(self, name: str) -> ExecutableLookup:
        unsafe_seen = False
        for element in self._elements:
            match = self._match_in(element, name)
            unsafe_seen = unsafe_seen or self._is_unsafe(element)
            if match is not None:
                return ExecutableLookup(self._compare(match), unsafe_seen)
        return ExecutableLookup(OnPath.ABSENT, unsafe_element_searched=False)

    def searches_unsafe(self, name: str) -> bool:
        for element in self._elements:
            if self._is_unsafe(element):
                return True
            if self._match_in(element, name) is not None:
                return False
        return False

    def _match_in(self, element: str, name: str) -> str | None:
        folder = element or "."
        # Windows runs a bare name only through a PATHEXT extension, never a file without one.
        candidates = [name + ext for ext in self._extensions] if self._windows else [name]
        for candidate in candidates:
            path = os.path.join(folder, candidate)
            if self._is_executable(path):
                return path
        return None

    def _is_executable(self, path: str) -> bool:
        try:
            info = os.stat(path)
        except (OSError, ValueError):
            return False
        if not stat.S_ISREG(info.st_mode):
            return False
        return self._windows or bool(info.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

    def _is_unsafe(self, element: str) -> bool:
        if not element or not os.path.isabs(element):
            return True  # empty and `.` are relative too: they name the working folder
        if self._windows:
            return False
        try:
            return bool(os.stat(element).st_mode & stat.S_IWOTH)
        except (OSError, ValueError):
            return False

    def _compare(self, match: str) -> OnPath:
        if self._running is None:
            return OnPath.DIFFERENT
        same = os.path.realpath(match) == os.path.realpath(self._running)
        return OnPath.SAME if same else OnPath.DIFFERENT
