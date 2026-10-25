"""Windows junctions are refused like symbolic links (proposal section 12.4, path-guard rule 1)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.application.ports.filesystem import FileKind, LinkRefused
from orqlet.domain.paths import CanonicalPath

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform != "win32", reason="junctions exist on Windows only"),
]


def make_junction(link: Path, target: Path) -> None:
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True
    )


def test_a_junction_is_a_link_and_nothing_is_read_or_written_through_it(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    make_junction(root / ".claude", outside)
    fs = LocalFileSystem(root)

    assert fs.kind(CanonicalPath.parse(".claude")) is FileKind.SYMLINK
    with pytest.raises(LinkRefused):
        fs.read_bytes(CanonicalPath.parse(".claude/secret.txt"))
    with pytest.raises(LinkRefused):
        fs.write_atomic(CanonicalPath.parse(".claude/new.txt"), b"x")
    assert not (outside / "new.txt").exists()
