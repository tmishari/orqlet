"""The technology scanners report what manifests say, with evidence, and nothing else."""

from __future__ import annotations

import contextlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.adapters.scan.stack_tables import GO, image_version, lookup_image, lookup_prefix
from orqlet.adapters.scan.technology_scanners import (
    ContainerScanner,
    GoScanner,
    NodeScanner,
    PythonTechnologyScanner,
    RustScanner,
)
from orqlet.application.contracts.common import Evidence
from orqlet.application.contracts.profile import Technology
from orqlet.application.ports.filesystem import FileSystem
from orqlet.domain.facts import line_range_hash
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.support.trees import repo, with_files

pytestmark = pytest.mark.unit


def summary(found: tuple[Technology, ...]) -> set[tuple[str, str, str | None]]:
    return {(t.kind, t.name, t.version) for t in found}


def assert_resolves(fs: FileSystem, evidence: Evidence) -> None:
    content = fs.read_bytes(CanonicalPath.parse(evidence.path))
    start, end = (int(part) for part in evidence.lines.split("-"))
    assert line_range_hash(content, start, end) == evidence.sha256


def test_go_reads_the_language_version_and_direct_dependencies_only() -> None:
    fs = repo("go_service")

    found = GoScanner().scan(fs, None)

    assert summary(found) == {
        ("language", "Go", "1.25"),
        ("framework", "Gin", "v1.9.1"),
        ("database", "PostgreSQL", None),  # pgx's version is the driver's, not the database's
        ("queue", "Kafka", None),
        ("database", "Redis", None),  # a single-line `require` is read too
    }
    assert not [t for t in found if t.name == "unknown-lib"]  # unknown modules are not guessed
    assert not any(t.version == "v1.10.9" for t in found)  # `// indirect` is not a choice


def test_rust_reads_rust_version_and_known_crates() -> None:
    found = RustScanner().scan(repo("rust_cli"), None)

    assert summary(found) == {
        ("language", "Rust", "1.80"),
        ("framework", "clap", "4.5"),
        ("library", "Tokio", "1"),
        ("library", "SQLx", "0.8"),
        ("queue", "Kafka", None),
    }


def test_node_reads_engines_and_picks_typescript_when_it_is_a_dependency() -> None:
    found = NodeScanner().scan(repo("node_web"), None)

    assert summary(found) == {
        ("language", "TypeScript", "^5.4.0"),
        ("runtime", "Node.js", ">=20"),
        ("framework", "Express", "^4.19.0"),
        ("database", "PostgreSQL", None),
        ("queue", "Kafka", None),
    }


def test_containers_read_images_with_their_tags_and_skip_what_they_cannot_resolve() -> None:
    found = ContainerScanner().scan(repo("go_service"), None)

    assert ("language", "Go", "1.25") in summary(found)
    assert ("database", "PostgreSQL", "16") in summary(found)
    assert ("database", "Redis", "7") in summary(found)
    assert ("queue", "Kafka", "3.7.0") in summary(found)
    assert ("tool", "Docker", None) in summary(found)
    assert ("tool", "Docker Compose", None) in summary(found)
    names = {t.name for t in found}
    assert "billing" not in names  # an application's own image is not a technology
    assert "chainguard-base" not in names  # an unknown base image is not guessed


def test_helm_dependencies_are_reported_without_the_charts_version() -> None:
    found = ContainerScanner().scan(repo("monorepo"), CanonicalPath.parse("helm"))

    assert summary(found) == {
        ("tool", "Helm", None),
        ("database", "PostgreSQL", None),
        ("infrastructure", "MinIO", None),
    }


def test_python_is_scanned_inside_a_service_folder_with_paths_from_the_root() -> None:
    fs = repo("monorepo")
    scope = CanonicalPath.parse("services/billing")

    found = PythonTechnologyScanner().scan(fs, scope)

    assert summary(found) >= {
        ("language", "Python", ">=3.12"),
        ("framework", "FastAPI", ">=0.110"),
        ("database", "PostgreSQL", None),
    }
    assert {t.scope for t in found} == {"services/billing"}
    for technology in found:
        assert technology.evidence[0].path.startswith("services/billing/")
        assert_resolves(fs, technology.evidence[0])


@pytest.mark.parametrize(
    ("scanner", "fixture"),
    [
        (GoScanner(), "go_service"),
        (RustScanner(), "rust_cli"),
        (NodeScanner(), "node_web"),
        (ContainerScanner(), "go_service"),
        (PythonTechnologyScanner(), "uv_fastapi"),
    ],
)
def test_every_technology_cites_evidence_that_resolves(scanner: object, fixture: str) -> None:
    fs = repo(fixture)

    found = scanner.scan(fs, None)  # type: ignore[attr-defined]

    assert found
    for technology in found:
        assert technology.source == "scanner"
        assert technology.evidence
        assert_resolves(fs, technology.evidence[0])


def test_a_directory_without_manifests_yields_nothing() -> None:
    fs = with_files({"README.md": "hello\n", "src/notes.txt": "x\n"})

    for scanner in (
        GoScanner(),
        RustScanner(),
        NodeScanner(),
        ContainerScanner(),
        PythonTechnologyScanner(),
    ):
        assert scanner.scan(fs, None) == ()


@pytest.mark.parametrize(
    ("scanner", "name", "content"),
    [
        (RustScanner(), "Cargo.toml", b"[package\nname ="),
        (NodeScanner(), "package.json", b"{not json"),
        (NodeScanner(), "package.json", b"[1, 2, 3]"),
        (GoScanner(), "go.mod", b"\xff\xfe\x00garbage"),
    ],
)
def test_broken_manifests_are_skipped_not_crashed_on(
    scanner: object, name: str, content: bytes
) -> None:
    fs = MemoryFileSystem()
    fs.write_atomic(CanonicalPath.parse(name), content)

    found = scanner.scan(fs, None)  # type: ignore[attr-defined]

    assert isinstance(found, tuple)


def test_a_dot_git_entry_and_other_hidden_names_never_reach_the_path_parser() -> None:
    fs = repo("go_service")
    fs.add_dir(".git")

    assert ContainerScanner().scan(fs, None)  # no InvalidPath for `.git`


def test_image_references_resolve_by_the_last_path_component_and_tag() -> None:
    assert lookup_image("registry.example.com/team/python:3.13-dev").name == "Python"  # type: ignore[union-attr]
    assert lookup_image("postgres@sha256:abc").name == "PostgreSQL"  # type: ignore[union-attr]
    assert lookup_image("gcr.io/distroless/static") is None
    assert image_version("registry.example.com/team/python:3.13-dev") == "3.13"
    assert image_version("redis:7-alpine") == "7"
    assert image_version("nginx:latest") is None
    assert image_version("nginx") is None
    assert image_version("registry:5000/team/python") is None  # a port is not a tag


def test_go_modules_match_by_longest_prefix_and_not_by_substring() -> None:
    assert lookup_prefix(GO, "github.com/jackc/pgx/v5").name == "PostgreSQL"  # type: ignore[union-attr]
    assert lookup_prefix(GO, "github.com/jackc/pgxfake") is None
    assert lookup_prefix(GO, "github.com/GIN-GONIC/gin").name == "Gin"  # type: ignore[union-attr]


@given(st.text(max_size=300))
def test_any_manifest_text_gives_resolvable_evidence_or_nothing(text: str) -> None:
    data = text.encode("utf-8", errors="replace")
    for name, scanner in (
        ("go.mod", GoScanner()),
        ("Cargo.toml", RustScanner()),
        ("package.json", NodeScanner()),
        ("Dockerfile", ContainerScanner()),
        ("docker-compose.yml", ContainerScanner()),
        ("Chart.yaml", ContainerScanner()),
    ):
        fs = MemoryFileSystem()
        fs.write_atomic(CanonicalPath.parse(name), data)
        with contextlib.suppress(UnicodeError):
            for technology in scanner.scan(fs, None):
                assert_resolves(fs, technology.evidence[0])
