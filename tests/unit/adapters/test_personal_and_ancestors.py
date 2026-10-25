"""The names-only scan lists directory entries and nothing else; ancestors are found by name."""

from __future__ import annotations

from pathlib import Path

import pytest

from orqlet.adapters.fs.ancestors import FsAncestorFinder
from orqlet.adapters.scan.personal_names import LOCATIONS, FsPersonalNames

pytestmark = pytest.mark.unit


def test_it_lists_entry_names_in_the_known_locations_in_a_fixed_order(tmp_path: Path) -> None:
    (tmp_path / ".claude" / "skills" / "zeta").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "alpha").mkdir(parents=True)
    (tmp_path / ".codex" / "agents").mkdir(parents=True)
    (tmp_path / ".codex" / "agents" / "reviewer.toml").write_text("model = 'x'\n")

    items = FsPersonalNames(tmp_path).list_names()

    assert [(i.location, i.name) for i in items] == [
        ("~/.claude/skills", "alpha"),
        ("~/.claude/skills", "zeta"),
        ("~/.codex/agents", "reviewer.toml"),
    ]


def test_it_never_reads_file_contents(tmp_path: Path) -> None:
    secret = tmp_path / ".claude" / "agents" / "private.md"
    secret.parent.mkdir(parents=True)
    secret.write_text("API_KEY=do-not-read\n")
    secret.chmod(0o000)
    try:
        items = FsPersonalNames(tmp_path).list_names()
    finally:
        secret.chmod(0o600)

    assert [i.name for i in items] == ["private.md"]


def test_missing_locations_are_skipped_without_error(tmp_path: Path) -> None:
    assert FsPersonalNames(tmp_path).list_names() == ()
    assert len(LOCATIONS) == len(set(LOCATIONS))


def test_ancestor_files_above_the_root_are_found_by_name(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("shared\n")
    (tmp_path / "team" / "AGENTS.md").parent.mkdir()
    (tmp_path / "team" / "AGENTS.md").write_text("team\n")
    project = tmp_path / "team" / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text("inside, not an ancestor\n")

    found = FsAncestorFinder(project).find()

    assert str(tmp_path / "team" / "AGENTS.md") in found
    assert str(tmp_path / "CLAUDE.md") in found
    assert str(project / "CLAUDE.md") not in found
