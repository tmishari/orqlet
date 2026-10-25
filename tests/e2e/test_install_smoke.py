"""Install the wheel into a clean environment and run it as a user would."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from orqlet import __version__
from tests.support.git import clean_environ, git, make_repo
from tests.support.trees import FIXTURES
from tests.support.wheel import build_wheel, uv

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(uv() is None, reason="uv is not installed"),
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The `orqlet` executable of a fresh virtual environment that holds only the wheel."""
    base = tmp_path_factory.mktemp("install")
    wheel = build_wheel(base / "wheel")
    environment = base / "venv"
    subprocess.run(
        [str(uv()), "venv", "--python", sys.executable, str(environment)],
        check=True,
        capture_output=True,
    )
    python = environment / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    subprocess.run(
        [str(uv()), "pip", "install", "--python", str(python), str(wheel)],
        check=True,
        capture_output=True,
    )
    return python.with_name("orqlet.exe" if sys.platform == "win32" else "orqlet")


def run(executable: Path, *args: str, cwd: Path, data: Path) -> subprocess.CompletedProcess[str]:
    environment = {**clean_environ(cwd.parent), "ORQLET_DATA_DIR": str(data)}
    return subprocess.run(
        [str(executable), *args],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_installed_command_reports_its_version(installed: Path, tmp_path: Path) -> None:
    result = run(installed, "--version", cwd=tmp_path, data=tmp_path / "data")

    assert result.returncode == 0
    assert result.stdout.strip() == f"orqlet {__version__}"


def test_init_doctor_and_the_pin_check_work_from_the_installed_wheel(
    installed: Path, tmp_path: Path
) -> None:
    root = tmp_path / "w" / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "initial")
    data = tmp_path / "data"

    init = run(installed, "init", "--yes", "--json", cwd=root, data=data)
    healthy = run(installed, "doctor", "--json", cwd=root, data=data)
    pins = root / ".orqlet" / "versions.yaml"
    pins.write_text(
        pins.read_text(encoding="utf-8").replace(f'pinned: "{__version__}"', 'pinned: "0.0.9"'),
        encoding="utf-8",
    )
    skewed = run(installed, "doctor", "--json", cwd=root, data=data)

    assert init.returncode == 0, init.stdout + init.stderr
    assert healthy.returncode in {0, 1}, healthy.stdout
    assert not [f for f in json.loads(healthy.stdout)["findings"] if f["severity"] == "error"]
    codes = {f["code"] for f in json.loads(skewed.stdout)["findings"]}
    assert "ORQ-W160" in codes, "doctor must warn when the CLI version differs from the pin"


def test_a_dry_run_from_the_installed_wheel_previews_and_writes_nothing(
    installed: Path, tmp_path: Path
) -> None:
    root = tmp_path / "w" / "project"
    shutil.copytree(FIXTURES / "repos" / "pip_flask", root)
    make_repo(root)

    before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())

    result = run(installed, "init", "--dry-run", "--json", cwd=root, data=tmp_path / "data")
    after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["data"]["status"] == "previewed"
    assert [n for n in after if not n.startswith(".git/")] == [
        n for n in before if not n.startswith(".git/")
    ]


def test_the_installed_wheel_ships_the_skills_and_the_commands_they_call(
    installed: Path, tmp_path: Path
) -> None:
    root = tmp_path / "w" / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "initial")
    data = tmp_path / "data"

    init = run(installed, "init", "--yes", "--json", cwd=root, data=data)
    status = run(installed, "gate", "status", "--json", cwd=root, data=data)
    cited = run(installed, "evidence", "cite", "pyproject.toml", "1", "--json", cwd=root, data=data)
    validated = run(installed, "validate", "ledger", "nothing.yaml", "--json", cwd=root, data=data)

    assert init.returncode == 0, init.stdout + init.stderr
    for name in ("onboard", "research", "design", "plan", "implement"):
        assert (root / ".agents" / "skills" / f"orqlet-{name}" / "SKILL.md").is_file(), name
        assert (root / ".claude" / "skills" / f"orqlet-{name}" / "SKILL.md").is_file(), name
    assert (root / ".codex" / "agents" / "orqlet-inventory.toml").is_file()
    assert json.loads(status.stdout)["data"]["verdict"] == "PASS", status.stdout
    assert len(json.loads(cited.stdout)["data"]["sha256"]) == 64, cited.stdout
    assert json.loads(validated.stdout)["findings"][0]["code"] == "ORQ-E321"
