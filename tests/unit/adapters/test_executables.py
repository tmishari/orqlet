"""Finding `orqlet` on PATH without starting a process (task one-command-setup, phase P-4, AC-3).

Every test cites its `expected_behavior_source`: AC-3 is the acceptance criterion of phase P-4 in
docs/design/one-command-setup/plan.yaml; ADR-004 decision 7 is in
docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md; "the interface" is the one
that the Coder gave for P-4 (`PathExecutableLocator(path_value, running, *, windows=None,
pathext=".COM;.EXE;.BAT;.CMD")`, and
`locate(name) -> ExecutableLookup(on_path, unsafe_element_searched)`).

HOW THESE TESTS WERE WRITTEN. The Tester of P-4 wrote them from the acceptance criteria and the
interface, before the implementation existed, with real temporary folders. Each test moves the
working directory to a folder that holds no `orqlet`, with the empty folders `relative/bin` and
`bin`, so that `.` and the relative PATH elements exist and hold no match; whether a relative
element that does not exist counts as unsafe is left open. Every program file is made
executable, also in the Windows-form cases, so that no case depends on how the locator reads the
executable bit there.

Choices:
- `windows=False` is passed explicitly wherever the case is not about Windows lookup.
- The cases about file modes (a non-executable file, a folder writable by others, a linked folder)
  are skipped on Windows, and so is every POSIX-form case that finds a program or reads a folder's
  mode: Windows reports no execute bit for a file without an extension and the others-write bit
  for an ordinary folder.
"""

from __future__ import annotations

import ast
import inspect
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from orqlet.adapters.scan import executables as executables_module
from orqlet.adapters.scan.executables import PathExecutableLocator
from orqlet.application.ports.executables import ExecutableLookup, OnPath

pytestmark = pytest.mark.unit

POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
NAME = "orqlet"


@pytest.fixture(autouse=True)
def _empty_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = tmp_path / "cwd"
    (empty / "relative" / "bin").mkdir(parents=True)
    (empty / "bin").mkdir()
    monkeypatch.chdir(empty)


def _folder(tmp_path: Path, name: str) -> Path:
    folder = tmp_path / name
    folder.mkdir()
    return folder


def _program(folder: Path, name: str = NAME, *, mode: int = 0o755) -> Path:
    path = folder / name
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(mode)
    return path


def _path(*elements: str | Path) -> str:
    return os.pathsep.join(str(element) for element in elements)


def _locate(
    path_value: str, running: Path | str | None, *, windows: bool = False
) -> ExecutableLookup:
    running_text = None if running is None else str(running)
    return PathExecutableLocator(path_value, running_text, windows=windows).locate(NAME)


# --- same, different, absent ----------------------------------------------------------------


@POSIX_ONLY
def test_the_running_executable_found_first_is_same(tmp_path: Path) -> None:
    """AC-3, ADR-004 decision 7: PATH resolves `orqlet` to the running executable."""
    bin_dir = _folder(tmp_path, "bin")
    program = _program(bin_dir)

    lookup = _locate(_path(bin_dir), program)

    assert lookup == ExecutableLookup(on_path=OnPath.SAME, unsafe_element_searched=False)


@POSIX_ONLY
def test_another_orqlet_found_first_is_different(tmp_path: Path) -> None:
    """AC-3, ADR-004 decision 7: the first match wins; it is not the running executable."""
    first = _program(_folder(tmp_path, "first"))
    running = _program(_folder(tmp_path, "second"))

    lookup = _locate(_path(first.parent, running.parent), running)

    assert lookup.on_path is OnPath.DIFFERENT
    assert lookup.unsafe_element_searched is False


@POSIX_ONLY
def test_an_unknown_running_executable_is_different(tmp_path: Path) -> None:
    """The interface: `running` None gives DIFFERENT when PATH holds a match."""
    bin_dir = _folder(tmp_path, "bin")
    _program(bin_dir)

    assert _locate(_path(bin_dir), None).on_path is OnPath.DIFFERENT


def test_no_orqlet_on_path_is_absent(tmp_path: Path) -> None:
    """AC-3: no element holds `orqlet`."""
    empty = _folder(tmp_path, "empty")
    elsewhere = _program(_folder(tmp_path, "elsewhere"))

    lookup = _locate(_path(empty), elsewhere)

    assert lookup == ExecutableLookup(on_path=OnPath.ABSENT, unsafe_element_searched=False)


def test_an_empty_path_value_is_absent(tmp_path: Path) -> None:
    """The interface: nothing found gives ABSENT, and unsafe_element_searched is False then."""
    assert _locate("", None) == ExecutableLookup(OnPath.ABSENT, False)


def test_absent_never_reports_an_unsafe_element(tmp_path: Path) -> None:
    """The interface: unsafe_element_searched is False when ABSENT, whatever PATH holds."""
    empty = _folder(tmp_path, "empty")

    lookup = _locate(_path("", ".", "relative/bin", empty), None)

    assert lookup == ExecutableLookup(OnPath.ABSENT, False)


@POSIX_ONLY
def test_an_element_that_does_not_exist_is_skipped(tmp_path: Path) -> None:
    """The interface: elements that do not exist are skipped silently and are not unsafe."""
    program = _program(_folder(tmp_path, "bin"))

    lookup = _locate(_path(tmp_path / "missing", program.parent), program)

    assert lookup == ExecutableLookup(OnPath.SAME, False)


@POSIX_ONLY
def test_a_folder_named_orqlet_is_not_a_match(tmp_path: Path) -> None:
    """The interface: only a regular, executable file is a match."""
    first = _folder(tmp_path, "first")
    (first / NAME).mkdir()
    program = _program(_folder(tmp_path, "second"))

    assert _locate(_path(first, program.parent), program).on_path is OnPath.SAME


@POSIX_ONLY
def test_a_file_that_is_not_executable_is_skipped(tmp_path: Path) -> None:
    """The interface: a regular file without execute permission is not a match."""
    _program(_folder(tmp_path, "first"), mode=0o644)
    program = _program(_folder(tmp_path, "second"))

    lookup = _locate(_path(tmp_path / "first", program.parent), program)

    assert lookup == ExecutableLookup(OnPath.SAME, False)


@POSIX_ONLY
def test_a_linked_path_folder_resolving_to_the_running_executable_is_same(tmp_path: Path) -> None:
    """The interface: SAME compares realpath(match) with realpath(running)."""
    program = _program(_folder(tmp_path, "real"))
    linked = tmp_path / "linked"
    linked.symlink_to(program.parent, target_is_directory=True)

    assert _locate(_path(linked), program).on_path is OnPath.SAME


# --- unsafe elements before the match --------------------------------------------------------


@POSIX_ONLY
@pytest.mark.parametrize(
    "element", ["", ".", "relative/bin", "bin"], ids=["empty", "dot", "rel", "bare"]
)
def test_an_unsafe_element_searched_the_match_is_reported(tmp_path: Path, element: str) -> None:
    """AC-3, ADR-004 decision 7: an empty, `.` or relative element before the match."""
    program = _program(_folder(tmp_path, "bin"))

    lookup = _locate(_path(element, program.parent), program)

    assert lookup == ExecutableLookup(OnPath.SAME, True)


@POSIX_ONLY
@pytest.mark.parametrize("element", ["", ".", "relative/bin"], ids=["empty", "dot", "rel"])
def test_an_unsafe_element_after_the_match_is_not_reported(tmp_path: Path, element: str) -> None:
    """AC-3: an element after the matching one is never searched."""
    program = _program(_folder(tmp_path, "bin"))

    lookup = _locate(_path(program.parent, element), program)

    assert lookup == ExecutableLookup(OnPath.SAME, False)


@POSIX_ONLY
def test_a_folder_writable_by_others_before_the_match_is_reported(tmp_path: Path) -> None:
    """AC-3: an existing folder writable by others (POSIX) before the match is unsafe."""
    shared = _folder(tmp_path, "shared")
    shared.chmod(0o777)
    assert shared.stat().st_mode & stat.S_IWOTH
    program = _program(_folder(tmp_path, "bin"))

    lookup = _locate(_path(shared, program.parent), program)

    assert lookup == ExecutableLookup(OnPath.SAME, True)


@POSIX_ONLY
def test_a_folder_writable_by_others_after_the_match_is_not_reported(tmp_path: Path) -> None:
    """AC-3; the interface: strictly before the match only."""
    shared = _folder(tmp_path, "shared")
    shared.chmod(0o777)
    program = _program(_folder(tmp_path, "bin"))

    lookup = _locate(_path(program.parent, shared), program)

    assert lookup == ExecutableLookup(OnPath.SAME, False)


@POSIX_ONLY
def test_a_matching_folder_writable_by_others_is_reported(tmp_path: Path) -> None:
    """Q-79: the folder that holds the match counts, as for git (Q-73)."""
    shared = _folder(tmp_path, "shared")
    program = _program(shared)
    shared.chmod(0o777)

    assert _locate(_path(shared), program) == ExecutableLookup(OnPath.SAME, True)


@POSIX_ONLY
@pytest.mark.parametrize("element", ["", "."], ids=["empty", "dot"])
def test_a_matching_working_folder_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, element: str
) -> None:
    """Q-79: an orqlet found through the working folder could be an untrusted clone's own."""
    program = _program(_folder(tmp_path, "clone"))
    monkeypatch.chdir(program.parent)

    assert _locate(element, program) == ExecutableLookup(OnPath.SAME, True)


@POSIX_ONLY
def test_a_folder_writable_by_its_group_only_is_not_unsafe(tmp_path: Path) -> None:
    """AC-3: the rule is "writable by others" (S_IWOTH), not by the group."""
    group = _folder(tmp_path, "group")
    group.chmod(0o775)
    program = _program(_folder(tmp_path, "bin"))

    assert _locate(_path(group, program.parent), program) == ExecutableLookup(OnPath.SAME, False)


@POSIX_ONLY
def test_a_different_match_after_an_unsafe_element_reports_both(tmp_path: Path) -> None:
    """AC-3: on_path and the unsafe element are reported independently."""
    first = _program(_folder(tmp_path, "first"))
    running = _program(_folder(tmp_path, "second"))

    lookup = _locate(_path(".", first.parent, running.parent), running)

    assert lookup == ExecutableLookup(OnPath.DIFFERENT, True)


# --- Windows lookup ------------------------------------------------------------------------


def test_windows_lookup_tries_each_pathext_extension(tmp_path: Path) -> None:
    """The interface: on Windows `name` plus each PATHEXT extension is tried."""
    bin_dir = _folder(tmp_path, "bin")
    program = _program(bin_dir, "orqlet.EXE")

    locator = PathExecutableLocator(_path(bin_dir), str(program), windows=True, pathext=".COM;.EXE")

    assert locator.locate(NAME) == ExecutableLookup(OnPath.SAME, False)


def test_windows_lookup_uses_the_default_pathext(tmp_path: Path) -> None:
    """The interface: the default PATHEXT is .COM;.EXE;.BAT;.CMD."""
    bin_dir = _folder(tmp_path, "bin")
    program = _program(bin_dir, "orqlet.CMD")

    locator = PathExecutableLocator(_path(bin_dir), str(program), windows=True)

    assert locator.locate(NAME).on_path is OnPath.SAME


def test_windows_lookup_reports_an_unsafe_element_searched_the_match(tmp_path: Path) -> None:
    """AC-3, ADR-004 decision 7: the empty, `.` and relative rule holds on every system."""
    bin_dir = _folder(tmp_path, "bin")
    program = _program(bin_dir, "orqlet.EXE")

    locator = PathExecutableLocator(_path(".", bin_dir), str(program), windows=True)

    assert locator.locate(NAME) == ExecutableLookup(OnPath.SAME, True)


def test_posix_lookup_does_not_add_extensions(tmp_path: Path) -> None:
    """The interface: PATHEXT applies on Windows only."""
    bin_dir = _folder(tmp_path, "bin")
    _program(bin_dir, "orqlet.EXE")

    locator = PathExecutableLocator(_path(bin_dir), None, windows=False, pathext=".EXE")

    assert locator.locate(NAME) == ExecutableLookup(OnPath.ABSENT, False)


def test_windows_lookup_skips_a_file_without_an_extension(tmp_path: Path) -> None:
    """Code review of P-4: on Windows a bare `orqlet` file earlier on PATH is not the program."""
    stray = _folder(tmp_path, "stray")
    _program(stray, NAME)
    bin_dir = _folder(tmp_path, "bin")
    program = _program(bin_dir, "orqlet.EXE")

    locator = PathExecutableLocator(_path(stray, bin_dir), str(program), windows=True)

    assert locator.locate(NAME) == ExecutableLookup(OnPath.SAME, False)


def test_windows_defaults_to_the_running_system(tmp_path: Path) -> None:
    """The interface: `windows` defaults to os.name == "nt"."""
    bin_dir = _folder(tmp_path, "bin")
    program = _program(bin_dir, "orqlet.EXE")

    found = PathExecutableLocator(_path(bin_dir), str(program), pathext=".EXE").locate(NAME)

    assert found.on_path is (OnPath.SAME if os.name == "nt" else OnPath.ABSENT)


# --- no process ----------------------------------------------------------------------------


@POSIX_ONLY
def test_the_locator_starts_no_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-3: the locator starts no process (and does not use shutil.which)."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the locator must start no process")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(shutil, "which", refuse)
    monkeypatch.setattr(os, "system", refuse)
    program = _program(_folder(tmp_path, "bin"))

    assert _locate(_path(".", program.parent), program) == ExecutableLookup(OnPath.SAME, True)


def test_the_locator_module_imports_no_process_module() -> None:
    """AC-3, ORQLET-SEC-001: no subprocess import and no shutil.which in the adapter."""
    tree = ast.parse(inspect.getsource(executables_module))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
            if node.module == "shutil":
                assert "which" not in {alias.name for alias in node.names}
        elif isinstance(node, ast.Attribute):
            assert node.attr not in {"which", "system", "popen", "spawnv", "execv"}

    assert imported.isdisjoint({"subprocess", "multiprocessing", "pty"})


@POSIX_ONLY
def test_an_unsafe_element_searched_the_match_is_searched(tmp_path: Path) -> None:
    """Q-73: git started by its bare name could come from the working folder first."""
    program = _program(_folder(tmp_path, "bin"), "git")
    locator = PathExecutableLocator(_path("", program.parent), None, windows=False)

    assert locator.searches_unsafe("git") is True


@POSIX_ONLY
def test_an_unsafe_element_after_the_match_is_not_searched(tmp_path: Path) -> None:
    program = _program(_folder(tmp_path, "bin"), "git")
    locator = PathExecutableLocator(_path(program.parent, "."), None, windows=False)

    assert locator.searches_unsafe("git") is False


@POSIX_ONLY
def test_an_absent_name_searches_every_element(tmp_path: Path) -> None:
    assert PathExecutableLocator(_path(tmp_path, "rel"), None, windows=False).searches_unsafe("git")
    assert not PathExecutableLocator(str(tmp_path), None, windows=False).searches_unsafe("git")
