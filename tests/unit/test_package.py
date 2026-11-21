import ast
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

import orqlet

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
SOURCE_ROOT = REPO_ROOT / "src" / "orqlet"
RICH_PRESENTER = SOURCE_ROOT / "interface" / "cli" / "render_rich.py"

EXISTING_EXACT_PINS = (
    "typer==0.27.3",
    "pydantic==2.14.1",
    "PyYAML==6.0.3",
    "filelock==4.2.4",
    "platformdirs==4.13.5",
)

# Distribution names, or prefixes ending in "-", of model provider SDKs and model frameworks.
MODEL_PROVIDER_SDKS = (
    "openai",
    "anthropic",
    "google-generativeai",
    "google-genai",
    "cohere",
    "mistralai",
    "litellm",
    "langchain",
    "langchain-",
    "ollama",
    "groq",
)


def _pyproject() -> dict[str, Any]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _distribution_name(requirement: str) -> str:
    name = re.split(r"[\s<>=!~;\[@]", requirement.strip(), maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name).lower()


def _all_requirements(project_file: dict[str, Any]) -> list[str]:
    project = project_file["project"]
    requirements: list[str] = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        requirements.extend(extra)
    for group in project_file.get("dependency-groups", {}).values():
        requirements.extend(entry for entry in group if isinstance(entry, str))
    return requirements


def _is_model_provider_sdk(name: str) -> bool:
    return any(
        name.startswith(sdk) if sdk.endswith("-") else name == sdk for sdk in MODEL_PROVIDER_SDKS
    )


def test_version_is_a_three_part_release_number() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", orqlet.__version__)


def test_rich_is_pinned_exactly_beside_the_existing_runtime_pins() -> None:
    # AC-1; EC-7; ADR-007 decision 2 (`rich==15.0.0` as a direct dependency); A-51
    dependencies = _pyproject()["project"]["dependencies"]

    assert "rich==15.0.0" in dependencies
    for pin in EXISTING_EXACT_PINS:
        assert pin in dependencies


def test_no_model_provider_sdk_is_a_dependency() -> None:
    # AC-1; ORQLET-NOMODEL-001 (.prompts/rules.yaml: "Do not add a model SDK dependency")
    names = [_distribution_name(entry) for entry in _all_requirements(_pyproject())]

    assert [name for name in names if _is_model_provider_sdk(name)] == []


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        ("openai==1.0.0", True),
        ("Anthropic>=0.30", True),
        ("google_genai", True),
        ("langchain-openai==0.1", True),
        ("rich==15.0.0", False),
        ("typer==0.27.3", False),
    ],
)
def test_model_provider_detection_recognises_provider_names(
    requirement: str, expected: bool
) -> None:
    # AC-1; guards the check above against a name normalisation that would never match
    assert _is_model_provider_sdk(_distribution_name(requirement)) is expected


def _imports_rich(source: str) -> bool:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        if any(name == "rich" or name.startswith("rich.") for name in names):
            return True
    return False


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import rich", True),
        ("import os, rich.console", True),
        ("from rich.text import Text", True),
        ("if True:\n    from rich import print", True),
        ("import richer", False),
        ("from .rich import x", False),
    ],
)
def test_rich_import_detection_covers_every_import_form(source: str, expected: bool) -> None:
    # AC-7; review round 1 of P-1 (a line pattern missed `import os, rich`)
    assert _imports_rich(source) is expected


def test_only_the_rich_presenter_imports_rich() -> None:
    # AC-7; ADR-007 decision 1 (Rich only through a Console created in orqlet.interface); BC-25
    importers = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in SOURCE_ROOT.rglob("*.py")
        if _imports_rich(path.read_text(encoding="utf-8"))
    )

    assert importers == [RICH_PRESENTER.relative_to(REPO_ROOT).as_posix()]
