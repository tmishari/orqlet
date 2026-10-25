"""Discovery walks a monorepo, skips what it must and says when it stopped early."""

from __future__ import annotations

import pytest

from orqlet.adapters.scan.technology_scanners import (
    ContainerScanner,
    GoScanner,
    NodeScanner,
    PythonTechnologyScanner,
    RustScanner,
)
from orqlet.application.usecases import discover
from orqlet.application.usecases.discover import discover_technologies
from tests.fakes.memory_fs import MemoryFileSystem
from tests.support.trees import repo, with_files

pytestmark = pytest.mark.unit

SCANNERS = (
    PythonTechnologyScanner(),
    GoScanner(),
    RustScanner(),
    NodeScanner(),
    ContainerScanner(),
)


def found(fs: MemoryFileSystem) -> set[tuple[str, str]]:
    return {(t.scope, t.name) for t in discover_technologies(fs, SCANNERS).technologies}


def test_every_service_of_a_monorepo_is_scanned_with_its_own_scope() -> None:
    result = found(repo("monorepo"))

    assert {
        (".", "PostgreSQL"),
        (".", "OpenSearch"),
        ("apiserver", "Gin"),
        ("apiserver", "Go"),
        ("services/billing", "FastAPI"),
        ("dag-worker", "Python"),
        ("helm", "MinIO"),
    } <= result


def test_hidden_folders_and_third_party_folders_are_not_scanned() -> None:
    scopes = {scope for scope, _ in found(repo("monorepo"))}

    assert not scopes & {".worktrees/skip", "node_modules/ignored"}


def test_a_driver_version_is_not_reported_as_the_databases_version() -> None:
    technologies = discover_technologies(repo("monorepo"), SCANNERS).technologies

    postgres = [t for t in technologies if t.name == "PostgreSQL"]
    by_scope = {t.scope: t.version for t in postgres}
    assert by_scope["."] == "16"  # from the image the repository runs
    assert by_scope["services/billing"] is None  # from `psycopg>=3.1`, the driver's version


def test_a_discrepancy_between_files_is_shown_not_resolved() -> None:
    technologies = discover_technologies(repo("monorepo"), SCANNERS).technologies

    versions = {t.version for t in technologies if t.name == "Go" and t.scope == "apiserver"}
    assert versions == {"1.24", "1.25"}  # go.mod says 1.24, the builder image says 1.25


def test_the_walk_stops_at_the_depth_limit() -> None:
    fs = with_files(
        {"a/b/c/go.mod": "module x\n\ngo 1.25\n", "a/b/go.mod": "module y\n\ngo 1.24\n"}
    )

    scopes = {scope for scope, name in found(fs) if name == "Go"}

    assert scopes == {"a/b"}


def test_the_directory_limit_is_reported_in_the_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discover, "MAX_DIRECTORIES", 3)
    fs = with_files({f"svc{i}/go.mod": f"module m{i}\n\ngo 1.2{i}\n" for i in range(6)})

    result = discover_technologies(fs, SCANNERS)

    assert any("stopped" in note for note in result.notes)
    assert len({t.scope for t in result.technologies}) <= 2


def test_the_technology_limit_is_reported_in_the_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discover, "MAX_TECHNOLOGIES", 2)

    result = discover_technologies(repo("monorepo"), SCANNERS)

    assert len(result.technologies) == 2
    assert any("Stopped after 2 technologies" in note for note in result.notes)


def test_a_symlinked_folder_is_not_followed() -> None:
    fs = with_files({"real/go.mod": "module x\n\ngo 1.25\n"})
    fs.add_symlink("linked")

    assert {scope for scope, _ in found(fs)} == {"real"}


def test_the_result_is_ordered_and_repeatable() -> None:
    first = discover_technologies(repo("monorepo"), SCANNERS)
    second = discover_technologies(repo("monorepo"), SCANNERS)

    assert first == second
    assert first.technologies[0].scope == "."
    scopes = [t.scope for t in first.technologies]
    assert scopes == sorted(scopes, key=lambda scope: (scope != ".", scope))


def test_languages_lists_every_language_found() -> None:
    assert discover_technologies(repo("monorepo"), SCANNERS).languages() == {"Go", "Python"}


def test_an_empty_repository_has_no_technologies() -> None:
    assert discover_technologies(repo("empty"), SCANNERS).technologies == ()
