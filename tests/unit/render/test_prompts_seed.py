"""The `.prompts/` seed is written as seeded files and carries no company policy."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.render.prompts_seed import seed_files
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.standards_pack import RuleFile
from orqlet.domain.ownership import OwnerMode

pytestmark = pytest.mark.golden


def test_the_seed_is_three_seeded_files_in_path_order(golden: Callable[[str, bytes], None]) -> None:
    files = seed_files(PackagedWorkflow())

    assert [str(f.path) for f in files] == [
        ".prompts/README.md",
        ".prompts/foundations.md",
        ".prompts/rules.yaml",
    ]
    assert {f.owner for f in files} == {OwnerMode.SEEDED}
    assert {f.file_class for f in files} == {None}
    for rendered in files:
        golden(f"common/{rendered.path}", rendered.content)


def test_the_seed_can_go_to_another_folder() -> None:
    files = seed_files(PackagedWorkflow(), base="docs/standards")

    assert str(files[0].path) == "docs/standards/README.md"


def test_the_seeded_rule_list_is_empty_and_valid() -> None:
    rules = next(f for f in seed_files(PackagedWorkflow()) if f.path.name == "rules.yaml")

    assert load_contract(StrictYamlLoader(), RuleFile, rules.content, source="seed").rules == ()


def test_the_seed_text_makes_no_company_policy() -> None:
    text = b"".join(f.content for f in seed_files(PackagedWorkflow())).decode()

    assert "Orqlet writes no company policy" in text
    assert "MUST " not in text.replace("MUST, SHOULD and MAY", "")


def test_every_seed_file_records_what_it_was_made_from() -> None:
    for rendered in seed_files(PackagedWorkflow()):
        (item,) = rendered.inputs
        assert item[0].startswith("seeds/prompts/")
        assert len(item[2]) == 64
