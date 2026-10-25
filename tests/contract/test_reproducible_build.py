"""The wheel is a hash-pinnable artifact: the same source builds to the same bytes."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from orqlet import __version__
from orqlet.adapters.workflow_package import PackagedWorkflow
from tests.support.wheel import build_wheel, sha256_of, uv

pytestmark = [
    pytest.mark.contract,
    pytest.mark.skipif(uv() is None, reason="uv is not installed"),
]


@pytest.fixture(scope="module")
def wheels(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    base = tmp_path_factory.mktemp("wheels")
    return build_wheel(base / "first"), build_wheel(base / "second")


def test_two_builds_of_the_same_source_have_the_same_sha256(wheels: tuple[Path, Path]) -> None:
    first, second = wheels

    assert first.name == second.name == f"orqlet-{__version__}-py3-none-any.whl"
    assert sha256_of(first) == sha256_of(second)


def test_the_wheel_carries_the_workflow_package_and_the_entry_point(
    wheels: tuple[Path, Path],
) -> None:
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        entry_points = archive.read(f"orqlet-{__version__}.dist-info/entry_points.txt").decode()

    assert {
        "orqlet/py.typed",
        "orqlet/workflow/MANIFEST.json",
        "orqlet/workflow/baseline/baseline.md",
        "orqlet/workflow/seeds/prompts/rules.yaml",
        "orqlet/workflow/schemas/orqlet.versions.v1.json",
    } <= names
    assert "orqlet = orqlet.interface.cli.app:main" in entry_points


def test_the_workflow_inside_the_wheel_is_the_workflow_in_the_source(
    wheels: tuple[Path, Path], tmp_path: Path
) -> None:
    with zipfile.ZipFile(wheels[0]) as archive:
        archive.extractall(tmp_path)

    packaged = PackagedWorkflow(root=tmp_path / "orqlet" / "workflow")

    assert packaged.problems() == ()
    assert packaged.release == PackagedWorkflow().release


def test_the_wheel_has_no_test_fixtures_or_golden_files(wheels: tuple[Path, Path]) -> None:
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()

    assert not [n for n in names if n.startswith(("tests/", "tools/", "docs/"))]


def test_the_runtime_dependencies_are_exactly_pinned_and_hold_no_model_sdk(
    wheels: tuple[Path, Path],
) -> None:
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata = archive.read(f"orqlet-{__version__}.dist-info/METADATA").decode()

    requirements = [line for line in metadata.splitlines() if line.startswith("Requires-Dist:")]
    assert requirements
    assert all("==" in line for line in requirements)
    forbidden = ("openai", "anthropic", "langchain", "litellm", "ollama", "google-generativeai")
    assert not [line for line in requirements if any(name in line.lower() for name in forbidden)]
