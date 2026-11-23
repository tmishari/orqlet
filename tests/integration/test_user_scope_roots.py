"""Root inspection and preparation of the user scope against real temporary folders (P-6).

Acceptance criteria AC-2 (root refusals naming the variable), AC-3 (the planning view), AC-4
(preparation after consent), AC-5 (the data folder) and AC-6 (the Windows data folder warning) of
phase P-6 of task one-command-setup.

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-6 in
docs/design/one-command-setup/plan.yaml, BC-n a behaviour of design/component.md, "ADR-002
decision 1a" the root validation of design/adr-002-user-scope-root-journal-and-manifest.md, Q-n an
answered question of questions.yaml, and "the interface" the interface of `FsUserRootInspector` and
`RootState` that the Coder of P-6 gave the Tester (the field names, the variable named for each
prefix, and the `user_id` and `windows` parameters that let a test fake another owner or Windows).

Only temporary folders are used: the home, the data directory and CODEX_HOME or COPILOT_HOME are
passed in, never read from the real environment. These tests were written first, by the Tester of
phase P-6, before the inspector existed.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import NoReturn

import pytest

from orqlet.adapters.fs.user_scope import FsUserRootInspector
from orqlet.application.contracts.user_scope import UserHome
from orqlet.application.ports.user_scope import (
    USER_PREFIXES,
    ReadOnlyUserScope,
    RootState,
    UserPrefix,
    UserRootRefused,
)
from orqlet.domain.errors import OrqletError
from orqlet.domain.paths import CanonicalPath

pytestmark = pytest.mark.integration

WINDOWS = sys.platform == "win32"
HOME_VARIABLE = "USERPROFILE" if WINDOWS else "HOME"
CLIENT_PREFIXES: tuple[UserPrefix, ...] = ("agents", "claude", "codex", "copilot", "cursor")
posix_only = pytest.mark.skipif(WINDOWS, reason="POSIX permission bits and ownership")


def current_uid() -> int | None:
    if sys.platform == "win32":
        return None
    return os.getuid()


def p(text: str) -> CanonicalPath:
    return CanonicalPath.parse(text)


def make_link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("this account cannot create symbolic links")


def snapshot(base: Path) -> dict[str, int]:
    """Every path below `base` with its mode, links not followed."""
    found: dict[str, int] = {}
    for folder, dirs, files in os.walk(base):
        for name in (*dirs, *files):
            path = Path(folder) / name
            found[path.relative_to(base).as_posix()] = os.lstat(path).st_mode
    return found


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def no_process(*_args: object, **_kwargs: object) -> NoReturn:
    raise AssertionError("root inspection started a process")


@pytest.fixture(autouse=True)
def _outside_any_work_tree(tmp_path: Path) -> None:
    for folder in (tmp_path, *tmp_path.parents):
        if os.path.lexists(folder / ".git"):
            pytest.skip("the temporary folder lies inside a Git work tree")


@pytest.fixture
def home(tmp_path: Path) -> Path:
    folder = tmp_path / "home"
    folder.mkdir()
    return folder.resolve()


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """The data directory, outside the home and not created."""
    return tmp_path.resolve() / "data"


def make_inspector(
    data_dir: Path,
    *,
    environment: Mapping[str, str] | None = None,
    windows: bool = WINDOWS,
    user_id: int | None = current_uid(),
) -> FsUserRootInspector:
    return FsUserRootInspector(
        environment=dict(environment or {}),
        data_directory=data_dir,
        windows=windows,
        user_id=user_id,
    )


def inspect(
    home: Path,
    data_dir: Path,
    *,
    environment: Mapping[str, str] | None = None,
    windows: bool = WINDOWS,
    user_id: int | None = current_uid(),
) -> Mapping[UserPrefix, RootState]:
    inspector = make_inspector(data_dir, environment=environment, windows=windows, user_id=user_id)
    return inspector.inspect(UserHome(path=str(home)))


def assert_refused(state: RootState, variable: str) -> None:
    assert state.variable == variable
    assert state.refusal is not None
    assert state.refusal.startswith(variable)


# --- AC-2: refusals naming the variable ----------------------------------------------------------


def test_every_prefix_is_inspected_and_a_plain_home_is_accepted(home: Path, data_dir: Path) -> None:
    """AC-2. expected_behavior_source: AC-2; ADR-002 decision 1a (a RootState for each prefix);
    the interface (the variable of each prefix, the default roots)."""
    (home / ".claude").mkdir()
    states = inspect(home, data_dir)

    assert set(states) == set(USER_PREFIXES)
    assert all(state.refusal is None for state in states.values())
    defaults: list[tuple[UserPrefix, str]] = [
        ("claude", ".claude"),
        ("cursor", ".cursor"),
        ("agents", ".agents"),
        ("codex", ".codex"),
        ("copilot", ".copilot"),
    ]
    for prefix, folder in defaults:
        assert states[prefix].variable == HOME_VARIABLE
        assert states[prefix].path == str(home / folder)
    assert states["claude"].exists is True
    assert states["cursor"].exists is False
    assert states["data"].variable == "ORQLET_DATA_DIR"
    assert states["data"].path == str(data_dir / "user")


def test_a_root_that_is_a_link_is_refused_naming_the_home_variable(
    home: Path, data_dir: Path
) -> None:
    """AC-2. expected_behavior_source: AC-2; ADR-002 decision 1a ("The root itself must not be a
    link"); BC-6; section 5 failures (naming the root, the variable and the reason)."""
    target = home / "dotfiles-claude"
    target.mkdir()
    make_link(home / ".claude", target)

    states = inspect(home, data_dir)

    assert_refused(states["claude"], HOME_VARIABLE)
    assert states["claude"].refusal is not None
    assert "claude" in states["claude"].refusal
    assert states["cursor"].refusal is None


@posix_only
def test_a_root_owned_by_another_user_is_refused(home: Path, data_dir: Path) -> None:
    """AC-2. expected_behavior_source: AC-2; ADR-002 decision 1a ("owned by the current user (on
    POSIX)"); the interface (user_id stands for the current user)."""
    (home / ".claude").mkdir()
    uid = current_uid()
    assert uid is not None

    states = inspect(home, data_dir, user_id=uid + 1)

    assert_refused(states["claude"], HOME_VARIABLE)


@pytest.mark.parametrize("as_file", [False, True], ids=["git-folder", "git-file"])
def test_a_root_that_is_a_git_work_tree_is_refused(
    home: Path, data_dir: Path, as_file: bool
) -> None:
    """AC-2. expected_behavior_source: AC-2; ADR-002 decision 1a ("A root must not lie inside a
    Git work tree ... by looking for a .git entry"); Q-44."""
    root = home / ".claude"
    root.mkdir()
    if as_file:
        (root / ".git").write_text("gitdir: /elsewhere\n")
    else:
        (root / ".git").mkdir()

    states = inspect(home, data_dir)

    assert_refused(states["claude"], HOME_VARIABLE)
    assert states["cursor"].refusal is None


@pytest.mark.parametrize("exists", [True, False], ids=["existing", "missing"])
def test_a_root_below_a_work_tree_is_refused_naming_codex_home(
    home: Path, data_dir: Path, exists: bool
) -> None:
    """AC-2. expected_behavior_source: AC-2; ADR-002 decision 1a (the root and its ancestors; for
    a missing root its nearest existing ancestor); the interface (CODEX_HOME is named when set)."""
    repository = home / "dotfiles"
    (repository / ".git").mkdir(parents=True)
    codex = repository / "codex"
    if exists:
        codex.mkdir()

    states = inspect(home, data_dir, environment={"CODEX_HOME": str(codex)})

    assert_refused(states["codex"], "CODEX_HOME")
    assert states["claude"].refusal is None


def test_a_home_that_is_a_work_tree_refuses_every_client_root_without_a_process(
    home: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("including a home that is a work tree (no process is
    started for it)"); ADR-002 decision 1a and Consequences; BC-7 (no process)."""
    (home / ".git").mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(subprocess, "Popen", no_process)
    monkeypatch.setattr(os, "system", no_process)

    states = inspect(home, data_dir)

    for prefix in CLIENT_PREFIXES:
        assert_refused(states[prefix], HOME_VARIABLE)
    assert states["data"].refusal is None


@pytest.mark.parametrize("exists", [True, False], ids=["existing", "missing"])
@pytest.mark.parametrize(
    ("prefix", "variable"), [("codex", "CODEX_HOME"), ("copilot", "COPILOT_HOME")]
)
def test_codex_home_or_copilot_home_outside_the_home_is_refused(
    home: Path, data_dir: Path, tmp_path: Path, prefix: UserPrefix, variable: str, exists: bool
) -> None:
    """AC-2. expected_behavior_source: AC-2; ADR-002 decision 1a ("A CODEX_HOME or COPILOT_HOME
    value outside home is refused with exit 3"); section 5 failures."""
    outside = tmp_path / "elsewhere" / prefix
    if exists:
        outside.mkdir(parents=True)

    states = inspect(home, data_dir, environment={variable: str(outside)})

    assert_refused(states[prefix], variable)


@pytest.mark.parametrize(
    ("prefix", "variable"), [("codex", "CODEX_HOME"), ("copilot", "COPILOT_HOME")]
)
def test_codex_home_or_copilot_home_inside_the_home_is_used(
    home: Path, data_dir: Path, prefix: UserPrefix, variable: str
) -> None:
    """AC-2. expected_behavior_source: ADR-002 decision 1 (root `$CODEX_HOME`, `$COPILOT_HOME`);
    the interface (the variable is named when set)."""
    custom = home / "custom" / prefix
    custom.mkdir(parents=True)

    states = inspect(home, data_dir, environment={variable: str(custom)})

    assert states[prefix].refusal is None
    assert states[prefix].variable == variable
    assert states[prefix].path == str(custom)
    assert states[prefix].exists is True


def test_a_missing_root_below_a_link_out_of_the_home_is_refused(
    home: Path, data_dir: Path, tmp_path: Path
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("a missing root whose nearest existing ancestor is a
    link out of the home"); ADR-002 decision 1a."""
    outside = tmp_path / "outside"
    outside.mkdir()
    make_link(home / "linked", outside)

    states = inspect(home, data_dir, environment={"CODEX_HOME": str(home / "linked" / "codex")})

    assert_refused(states["codex"], "CODEX_HOME")
    assert not (outside / "codex").exists()


# --- AC-3: the planning view ---------------------------------------------------------------------


def test_the_planning_view_reads_missing_roots_as_empty_and_creates_nothing(
    home: Path, data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-3. expected_behavior_source: AC-3; ADR-002 decision 1a ("Nothing is created or changed
    before consent", missing roots read as empty and reported as `will create`); BC-7."""
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_bytes(b"{}")
    before = snapshot(tmp_path)
    monkeypatch.setattr(subprocess, "Popen", no_process)
    inspector = make_inspector(data_dir)

    states = inspector.inspect(UserHome(path=str(home)))
    fs = inspector.planning_fs(states)

    assert states["agents"].exists is False
    assert states["agents"].path == str(home / ".agents")
    assert states["agents"].creates == (str(home / ".agents"),)
    assert states["claude"].exists is True
    assert states["claude"].creates == ()
    assert states["data"].exists is False
    assert states["data"].creates == (str(data_dir), str(data_dir / "user"))
    assert fs.list_dir(None) == USER_PREFIXES
    assert fs.kind(p("agents")) is None
    assert fs.list_dir(p("agents")) == ()
    assert fs.kind(p("agents/skills/orqlet/SKILL.md")) is None
    assert fs.list_dir(p("data")) == ()
    assert fs.kind(p("data/manifest.json")) is None
    assert fs.read_bytes(p("claude/settings.json")) == b"{}"
    with pytest.raises(ReadOnlyUserScope):
        fs.write_atomic(p("agents/skills/orqlet/SKILL.md"), b"x")
    with pytest.raises(ReadOnlyUserScope):
        fs.make_dir(p("agents/skills/orqlet"))
    with pytest.raises(ReadOnlyUserScope):
        fs.delete(p("claude/settings.json"))
    assert snapshot(tmp_path) == before


def test_will_create_lists_the_missing_parents_outermost_first(home: Path, data_dir: Path) -> None:
    """AC-3. expected_behavior_source: AC-3; ADR-002 decision 1a ("each missing root and its
    missing parents under home"); the interface (`creates` outermost first)."""
    codex = home / "a" / "b" / "codex"

    states = inspect(home, data_dir, environment={"CODEX_HOME": str(codex)})

    assert states["codex"].refusal is None
    assert states["codex"].path == str(codex)
    assert states["codex"].creates == (str(home / "a"), str(home / "a" / "b"), str(codex))


@posix_only
def test_the_planning_view_reports_folders_to_tighten_and_changes_no_mode(
    home: Path, data_dir: Path, tmp_path: Path
) -> None:
    """AC-3. expected_behavior_source: AC-3; BC-7 and BC-29 (an existing user/, user/journal or
    user/backups with mode 0755 is reported as `will tighten`); ADR-002 decision 1a."""
    user = data_dir / "user"
    (user / "journal").mkdir(parents=True)
    (user / "backups").mkdir()
    user.chmod(0o755)
    (user / "journal").chmod(0o750)
    (user / "backups").chmod(0o700)
    before = snapshot(tmp_path)
    inspector = make_inspector(data_dir)

    states = inspector.inspect(UserHome(path=str(home)))
    inspector.planning_fs(states).list_dir(p("data"))

    data = states["data"]
    assert data.refusal is None
    assert data.exists is True
    assert data.creates == ()
    assert sorted(data.tightens) == sorted([str(user), str(user / "journal")])
    assert snapshot(tmp_path) == before
    assert mode(user) == 0o755


def test_a_refused_prefix_cannot_be_read_through_the_planning_view(
    home: Path, data_dir: Path
) -> None:
    """AC-3. expected_behavior_source: AC-2, AC-3; ADR-002 decision 1a ("Root validation, before
    any read for a plan"); the interface (a refused prefix raises UserRootRefused on access)."""
    target = home / "dotfiles-claude"
    target.mkdir()
    (target / "settings.json").write_bytes(b"{}")
    make_link(home / ".claude", target)
    inspector = make_inspector(data_dir)
    states = inspector.inspect(UserHome(path=str(home)))

    fs = inspector.planning_fs(states)

    with pytest.raises(UserRootRefused):
        fs.kind(p("claude/settings.json"))
    with pytest.raises(UserRootRefused):
        fs.read_bytes(p("claude/settings.json"))
    with pytest.raises(UserRootRefused):
        fs.list_dir(p("claude"))
    assert fs.list_dir(p("cursor")) == ()


# --- AC-4: preparation after consent -------------------------------------------------------------


def test_prepare_creates_the_missing_roots_and_returns_a_writable_composite(
    home: Path, data_dir: Path
) -> None:
    """AC-4. expected_behavior_source: AC-4; ADR-002 decision 1a ("create each missing root and
    its missing parents ... with mode 0700, validate the root again, and only then open"); BC-29."""
    codex = home / "a" / "b" / "codex"
    inspector = make_inspector(data_dir, environment={"CODEX_HOME": str(codex)})
    states = inspector.inspect(UserHome(path=str(home)))
    created = [Path(folder) for state in states.values() for folder in state.creates]

    fs = inspector.prepare(states)

    assert created
    for folder in created:
        assert folder.is_dir(), folder
        if not WINDOWS:
            assert mode(folder) == 0o700, folder
    assert {
        home / "a",
        home / "a" / "b",
        codex,
        home / ".agents",
        data_dir,
        data_dir / "user",
    } <= set(created)
    fs.write_atomic(p("codex/AGENTS.md"), b"block")
    fs.write_atomic(p("data/manifest.json"), b"{}")
    fs.write_atomic(p("agents/skills/orqlet/SKILL.md"), b"skill")
    assert (codex / "AGENTS.md").read_bytes() == b"block"
    assert (data_dir / "user" / "manifest.json").read_bytes() == b"{}"
    assert (home / ".agents" / "skills" / "orqlet" / "SKILL.md").read_bytes() == b"skill"


@posix_only
def test_prepare_tightens_orqlets_own_folders_to_0700(home: Path, data_dir: Path) -> None:
    """AC-4. expected_behavior_source: AC-4; BC-29 ("tightened to 0700 only after consent");
    ADR-002 decision 1a."""
    user = data_dir / "user"
    (user / "journal").mkdir(parents=True)
    (user / "backups").mkdir()
    user.chmod(0o755)
    (user / "journal").chmod(0o755)
    (user / "backups").chmod(0o750)
    inspector = make_inspector(data_dir)

    inspector.prepare(inspector.inspect(UserHome(path=str(home))))

    for folder in (user, user / "journal", user / "backups"):
        assert mode(folder) == 0o700, folder


def test_prepare_refuses_any_refused_state_and_creates_nothing(
    home: Path, data_dir: Path, tmp_path: Path
) -> None:
    """AC-4. expected_behavior_source: AC-4; ADR-002 decision 1a; the interface (prepare raises
    UserRootRefused if any given state has a refusal)."""
    target = home / "dotfiles-claude"
    target.mkdir()
    make_link(home / ".claude", target)
    inspector = make_inspector(data_dir)
    states = inspector.inspect(UserHome(path=str(home)))
    before = snapshot(tmp_path)

    with pytest.raises(UserRootRefused):
        inspector.prepare(states)

    assert snapshot(tmp_path) == before


def test_prepare_validates_again(home: Path, data_dir: Path) -> None:
    """AC-4. expected_behavior_source: AC-4 ("validates again"); ADR-002 decision 1a."""
    (home / ".claude").mkdir()
    inspector = make_inspector(data_dir)
    states = inspector.inspect(UserHome(path=str(home)))
    (home / ".claude" / ".git").mkdir()

    with pytest.raises(UserRootRefused):
        inspector.prepare(states)


def test_prepare_validates_again_a_root_swapped_for_a_link(home: Path, data_dir: Path) -> None:
    """AC-4. expected_behavior_source: AC-4 ("validates again"); ADR-002 decision 1a."""
    (home / ".cursor").mkdir()
    inspector = make_inspector(data_dir)
    states = inspector.inspect(UserHome(path=str(home)))
    target = home / "elsewhere"
    target.mkdir()
    (home / ".cursor").rmdir()
    make_link(home / ".cursor", target)

    with pytest.raises(UserRootRefused):
        inspector.prepare(states)


def test_prepare_refuses_an_opened_root_that_differs_from_the_pinned_path(
    home: Path, data_dir: Path
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("refuses with exit 3 when an opened root differs from
    the pinned path"); BC-46; ADR-002 decision 1a; the interface (UserRootRefused carries prefix
    and variable, and its text starts with the variable)."""
    (home / ".claude").mkdir()
    other = home / "other"
    other.mkdir()
    inspector = make_inspector(data_dir)
    states = inspector.inspect(UserHome(path=str(home)))
    tampered: dict[UserPrefix, RootState] = dict(states)
    tampered["claude"] = replace(states["claude"], path=str(other))

    with pytest.raises(UserRootRefused) as refused:
        inspector.prepare(tampered)

    assert isinstance(refused.value, OrqletError)
    assert refused.value.prefix == "claude"
    assert refused.value.variable == HOME_VARIABLE
    assert str(refused.value).startswith(HOME_VARIABLE)
    assert list(other.iterdir()) == []


# --- AC-5: the data folder -----------------------------------------------------------------------


@pytest.mark.parametrize("linked", ["user", "data-directory"])
def test_a_data_folder_that_is_a_link_is_refused(
    home: Path, data_dir: Path, tmp_path: Path, linked: str
) -> None:
    """AC-5. expected_behavior_source: AC-5; BC-29 ("A data directory that is a link ... is
    refused with exit 3"); section 5 failures ("The data directory or user/ is a link")."""
    real = tmp_path / "real-data"
    (real / "user").mkdir(parents=True)
    if linked == "user":
        data_dir.mkdir()
        make_link(data_dir / "user", real / "user")
    else:
        make_link(data_dir, real)

    states = inspect(home, data_dir)

    assert_refused(states["data"], "ORQLET_DATA_DIR")


@posix_only
@pytest.mark.parametrize("with_user", [True, False], ids=["user-exists", "user-missing"])
def test_a_data_folder_owned_by_another_user_is_refused(
    home: Path, data_dir: Path, with_user: bool
) -> None:
    """AC-5. expected_behavior_source: AC-5; BC-29 ("owned by another user is refused"); section 5
    failures; the interface (the data directory and user/ are checked)."""
    data_dir.mkdir()
    if with_user:
        (data_dir / "user").mkdir()
    uid = current_uid()
    assert uid is not None

    states = inspect(home, data_dir, user_id=uid + 1)

    assert_refused(states["data"], "ORQLET_DATA_DIR")


# --- AC-6: a data folder outside the home ---------------------------------------------------------


def test_on_windows_a_data_folder_outside_the_home_is_allowed_with_a_warning(
    home: Path, data_dir: Path
) -> None:
    """AC-6. expected_behavior_source: AC-6; Q-41 ("Allow it, with a warning in the preview");
    ADR-002 decision 1a (the warning names planted journals and backups); BC-39; BC-46;
    ORQLET-SAFE-001 ("On Windows, ownership is not checked")."""
    user = data_dir / "user"
    (user / "journal").mkdir(parents=True)
    if not WINDOWS:
        user.chmod(0o755)

    states = inspect(home, data_dir, windows=True, user_id=None)

    data = states["data"]
    assert data.refusal is None
    assert data.warning is not None
    warning = data.warning.lower()
    for word in ("not checked", "confidentiality", "integrity", "journal", "backup"):
        assert word in warning, word
    assert data.tightens == ()
    assert states["claude"].variable == "USERPROFILE"


def test_on_windows_a_data_folder_inside_the_home_has_no_warning(home: Path) -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 1a (the warning is for a data directory
    outside home); the interface (`warning`: Windows data directory outside home)."""
    states = inspect(home, home / "orqlet-data", windows=True, user_id=None)

    assert states["data"].refusal is None
    assert states["data"].warning is None


@posix_only
def test_on_posix_a_data_folder_outside_the_home_is_allowed_silently(
    home: Path, data_dir: Path
) -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 1a ("The data directory may lie outside
    home when ORQLET_DATA_DIR says so"); the interface (on POSIX silently)."""
    (data_dir / "user").mkdir(parents=True)

    states = inspect(home, data_dir, windows=False)

    assert states["data"].refusal is None
    assert states["data"].warning is None
