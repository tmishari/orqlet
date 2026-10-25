"""Direct dependencies, index and source settings, and lockfile packages."""

from __future__ import annotations

import pytest

from orqlet.domain.dependencies import (
    canonical_name,
    canonical_specifier,
    dependency_delta,
    lock_packages,
    parse_pyproject,
)

pytestmark = pytest.mark.unit

BEFORE = """
[project]
name = "x"
dependencies = ["requests>=2,<3", "Typer [all] >= 0.12"]
[project.optional-dependencies]
dev = ["pytest==8.0"]
[dependency-groups]
lint = ["ruff>=0.5"]
[tool.uv]
dev-dependencies = ["mypy>=1"]
[tool.uv.sources]
internal = { git = "https://example.invalid/internal" }
"""


def test_the_direct_set_is_read_from_every_group_with_canonical_names() -> None:
    parsed = parse_pyproject(BEFORE)

    assert parsed.direct == {
        "requests": ">=2,<3",
        "typer": ">=0.12",
        "pytest": "==8.0",
        "ruff": ">=0.5",
        "mypy": ">=1",
    }
    assert "uv.sources.internal" in parsed.sources


def test_names_and_specifiers_are_canonical() -> None:
    assert canonical_name("My_Package.Name") == "my-package-name"
    assert canonical_specifier(">= 1.0 , < 2") == ">=1.0,<2"


def test_a_poetry_table_is_read_and_python_is_not_a_dependency() -> None:
    text = (
        "[tool.poetry.dependencies]\npython = '^3.12'\nflask = '^3.0'\n"
        "django = { version = '^5', extras = ['argon2'] }\n"
    )

    parsed = parse_pyproject(text)

    assert set(parsed.direct) == {"flask", "django"}
    assert parsed.direct["flask"] == "^3.0"


def test_a_pyproject_that_cannot_be_parsed_is_reported_and_has_no_dependencies() -> None:
    parsed = parse_pyproject("[project\n")

    assert parsed.direct == {}
    assert "cannot be parsed" in parsed.problems[0]


def test_the_delta_lists_added_removed_and_changed_packages_and_changed_sources() -> None:
    after_text = BEFORE.replace('"requests>=2,<3"', '"requests>=2.5,<3"').replace(
        '"pytest==8.0"', '"pytest==8.0", "httpx>=0.27"'
    )
    after_text = after_text.replace('"ruff>=0.5"', "").replace(
        'internal = { git = "https://example.invalid/internal" }',
        'internal = { git = "https://example.invalid/other" }',
    )

    delta = dependency_delta(parse_pyproject(BEFORE), parse_pyproject(after_text))

    assert delta.added == {"httpx": ">=0.27"}
    assert delta.changed == {"requests": (">=2,<3", ">=2.5,<3")}
    assert set(delta.removed) == {"ruff"}
    assert delta.source_changes == ("uv.sources.internal",)
    assert delta.names() == {"httpx", "requests", "ruff"}


def test_an_unchanged_manifest_has_an_empty_delta() -> None:
    parsed = parse_pyproject(BEFORE)

    assert dependency_delta(parsed, parsed).is_empty()


def test_lockfile_packages_come_from_a_toml_lock_and_other_formats_are_unknown() -> None:
    lock = '[[package]]\nname = "Requests"\nversion = "2"\n[[package]]\nname = "idna"\n'

    assert lock_packages(lock) == frozenset({"requests", "idna"})
    assert lock_packages("requests==2.0\n") is None
    assert lock_packages("[tool]\nx = 1\n") is None
