"""Helpers that build real temporary Git repositories for integration tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def clean_environ(home: Path) -> dict[str, str]:
    """A minimal environment: the test's own HOME, no system config, fixed identity."""
    environ = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }
    for name in ("SYSTEMROOT", "TEMP", "TMP", "TMPDIR"):
        if name in os.environ:
            environ[name] = os.environ[name]
    return environ


def git(repo: Path, *args: str, environ: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=environ or clean_environ(repo.parent),
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8")


def make_repo(path: Path, branch: str = "main") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "--quiet", f"--initial-branch={branch}")
    return path


def commit_file(repo: Path, name: str, content: str, message: str = "add file") -> str:
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    git(repo, "add", "--", name)
    git(repo, "commit", "--quiet", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()
