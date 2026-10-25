"""Build the wheel of this repository, for the packaging and install tests."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXED_EPOCH = "1700000000"


def uv() -> str | None:
    return shutil.which("uv")


def build_wheel(output: Path) -> Path:
    """Build one wheel into `output` with a fixed timestamp and return its path."""
    output.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, "SOURCE_DATE_EPOCH": FIXED_EPOCH}
    subprocess.run(
        [str(uv()), "build", "--wheel", "--out-dir", str(output), str(ROOT)],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    (wheel,) = output.glob("*.whl")
    return wheel


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
