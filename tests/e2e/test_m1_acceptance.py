"""The M1 acceptance list of proposal section 22, one test per item that is not covered elsewhere.

Items covered by other suites, and where:
- golden files per client: tests/unit/render/test_clients_golden.py
- the resolver property: tests/unit/domain/test_resolver_properties.py
- the release gate (FM-U05): tests/contract/test_release_gate.py and
  tests/unit/application/test_lifecycle.py
- kill after k of n files (FM-U03): tests/fault/*, tests/unit/application/test_*.py
- rollback below the floor (FM-U09), reserved names (FM-W03), version pin (FM-U01): see
  tests/unit/application/test_lifecycle.py and tests/integration/test_lifecycle_cli.py
- FM-N01 to FM-N04: tests/integration/test_init_new_and_empty.py
- FM-P01 to FM-P03 and FM-P06: tests/integration/test_pr_template.py
- the wheel, reproducibility and install: tests/contract/test_reproducible_build.py and this folder
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.usecases.init_project import InitOptions, init_project
from orqlet.application.usecases.rollback import RollbackOptions, rollback
from orqlet.application.usecases.upgrade import UpgradeOptions, upgrade
from orqlet.domain.blocks import parse_blocks
from tests.fakes.ids import SequentialIds
from tests.fakes.workflow import PINNED, ChangedWorkflow
from tests.support.git import commit_file, make_repo
from tests.support.real_env import real_services
from tests.support.trees import FIXTURES

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
]

NEXT = ChangedWorkflow(PINNED, version="0.2.0")
YES = InitOptions(assume_yes=True)


def project(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "work" / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    make_repo(root)
    return root, tmp_path / "data"


def test_personal_and_local_files_and_an_ancestor_file_are_untouched_by_init_and_upgrade(
    tmp_path: Path,
) -> None:
    root, data = project(tmp_path)
    ancestor = root.parent / "CLAUDE.md"
    ancestor.write_text("shared with other projects\n", encoding="utf-8")
    personal = {
        "CLAUDE.local.md": "my private notes\n",
        ".claude/settings.local.json": '{"permissions": {}}\n',
        ".codex/config.local.toml": "model = 'private'\n",
    }
    for name, text in personal.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    init_project(real_services(root, data), YES)
    upgrade(
        real_services(root, data, workflow=NEXT, ids=SequentialIds(start=100)),
        UpgradeOptions(assume_yes=True),
    )

    assert ancestor.read_text(encoding="utf-8") == "shared with other projects\n"
    for name, text in personal.items():
        assert (root / name).read_text(encoding="utf-8") == text, name


def test_fm_p04_an_upgrade_updates_an_untouched_block_keeps_an_edited_one_and_preserves_the_rest(
    tmp_path: Path,
) -> None:
    root, data = project(tmp_path)
    commit_file(root, ".github/pull_request_template.md", "# Summary\n\nProject text.\n")
    init_project(real_services(root, data), YES)
    template = root / ".github" / "pull_request_template.md"
    outside = "# Summary\n\nProject text.\n"
    assert template.read_text(encoding="utf-8").endswith("\nProject text.\n")

    upgrade(
        real_services(root, data, workflow=NEXT, ids=SequentialIds(start=100)),
        UpgradeOptions(assume_yes=True),
    )

    updated = template.read_text(encoding="utf-8")
    assert "A rule added in this release." in updated  # the untouched block moved forward
    assert updated.startswith("# Summary\n")
    assert updated.endswith("\nProject text.\n")
    assert outside.splitlines()[0] in updated
    assert [b.name for b in parse_blocks(updated)] == ["orqlet-workflow"]

    edited = updated.replace("Orqlet-Task: <task-slug>", "Orqlet-Task: ours")
    template.write_text(edited, encoding="utf-8")
    newer = ChangedWorkflow(
        PackagedWorkflow(), version="0.3.0", baseline_suffix="- Another line.\n"
    )
    result = upgrade(
        real_services(root, data, workflow=newer, ids=SequentialIds(start=300)),
        UpgradeOptions(assume_yes=True),
    )

    assert template.read_text(encoding="utf-8") == edited  # an edited block is never overwritten
    assert any(f.code == "ORQ-W080" for f in result.findings)
    assert any(
        p.name.startswith(".github__pull_request_template")
        for p in (root / ".orqlet" / "proposals").iterdir()
    )


def test_fm_p04_rollback_of_an_upgrade_leaves_the_content_outside_the_blocks_untouched(
    tmp_path: Path,
) -> None:
    root, data = project(tmp_path)
    commit_file(root, ".github/pull_request_template.md", "# Summary\n\nProject text.\n")
    init_project(real_services(root, data), YES)
    template = root / ".github" / "pull_request_template.md"
    before = template.read_bytes()
    result = upgrade(
        real_services(root, data, workflow=NEXT, ids=SequentialIds(start=100)),
        UpgradeOptions(assume_yes=True),
    )
    assert result.change_id is not None

    undone = rollback(
        real_services(root, data, workflow=NEXT, ids=SequentialIds(start=500)),
        RollbackOptions(result.change_id, assume_yes=True),
    )

    assert undone.status == "applied"
    assert template.read_bytes() == before


def test_every_file_written_by_init_lies_inside_the_root(tmp_path: Path) -> None:
    root, data = project(tmp_path)
    result = init_project(real_services(root, data), YES)

    assert result.plan is not None
    for write in result.plan.writes:
        assert ".." not in write.path.parts
        assert write.path.parts[0] != ".git"
        assert (root / Path(*write.path.parts)).resolve().is_relative_to(root.resolve())
    assert not any(p.is_relative_to(data) for p in root.rglob("*"))
