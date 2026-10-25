"""The Python scanner records facts only where a file says so, and always with evidence."""

from __future__ import annotations

import contextlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.adapters.scan.python_scanner import MAX_FILE_BYTES, PythonScanner
from orqlet.application.contracts.common import Evidence
from orqlet.application.contracts.profile import Facts
from orqlet.application.ports.filesystem import FileSystem
from orqlet.domain.facts import line_range_hash
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.support.trees import repo

pytestmark = pytest.mark.unit

SCANNER = PythonScanner()
PYTHON_FIXTURES = ["uv_fastapi", "pip_flask", "poetry_cli", "ambiguous"]


def all_evidence(facts: Facts) -> list[Evidence]:
    found = [*facts.python.evidence, *facts.package_manager.evidence]
    for framework in facts.frameworks:
        found.extend(framework.evidence)
    return found


def assert_resolves(fs: FileSystem, evidence: Evidence) -> None:
    content = fs.read_bytes(CanonicalPath.parse(evidence.path))
    start, end = (int(part) for part in evidence.lines.split("-"))
    assert line_range_hash(content, start, end) == evidence.sha256


@pytest.mark.parametrize("name", PYTHON_FIXTURES)
def test_every_cited_fact_resolves_to_a_real_line_with_the_recorded_hash(name: str) -> None:
    fs = repo(name)
    result = SCANNER.scan(fs)

    evidence = all_evidence(result.facts) + [
        e for d in result.dependencies.declared for e in d.evidence
    ]
    assert evidence, "the fixture should yield at least one cited fact"
    for item in evidence:
        assert_resolves(fs, item)


def test_a_uv_fastapi_service() -> None:
    result = SCANNER.scan(repo("uv_fastapi"))

    assert result.language == "python"
    assert result.facts.python.value == ">=3.12"
    assert result.facts.package_manager.value == "uv"
    assert [f.name for f in result.facts.frameworks] == ["FastAPI"]
    assert result.facts.frameworks[0].value == "fastapi>=0.110"
    assert [d.name for d in result.dependencies.declared] == [
        "fastapi",
        "pydantic",
        "pytest",
        "uvicorn",
    ]
    assert result.dependencies.locked is not None
    assert result.dependencies.locked.file == "uv.lock"
    assert result.kind == "python-service"


def test_a_pip_project_reads_requirements_and_the_python_version_file() -> None:
    result = SCANNER.scan(repo("pip_flask"))

    assert result.facts.python.value == "3.11"
    assert result.facts.python.evidence[0].path == ".python-version"
    assert result.facts.package_manager.value == "pip"
    assert [d.name for d in result.dependencies.declared] == ["flask", "requests"]
    assert result.dependencies.declared[1].specifier == ">=2.31"
    assert result.dependencies.locked is None


def test_a_poetry_cli_project() -> None:
    result = SCANNER.scan(repo("poetry_cli"))

    assert result.facts.python.value == "^3.12"
    assert result.facts.package_manager.value == "poetry"
    assert [f.name for f in result.facts.frameworks] == ["SQLAlchemy", "Typer"]
    assert result.kind == "python-cli"


def test_two_package_managers_make_the_fact_a_question_not_a_guess() -> None:
    result = SCANNER.scan(repo("ambiguous"))

    assert result.facts.package_manager.value is None
    assert "poetry and uv" in (result.facts.package_manager.question or "")


def test_a_project_that_says_nothing_yields_questions_only() -> None:
    fs = MemoryFileSystem()
    fs.write_atomic(CanonicalPath.parse("pyproject.toml"), b'[project]\nname = "x"\n')

    result = SCANNER.scan(fs)

    assert result.facts.python.value is None
    assert result.facts.python.question
    assert result.facts.package_manager.value is None
    assert result.facts.frameworks == ()
    assert result.kind == "unknown"


def test_applies_to_python_projects_only() -> None:
    assert SCANNER.applies(repo("uv_fastapi"))
    assert SCANNER.applies(repo("pip_flask"))
    assert not SCANNER.applies(repo("js_only"))
    assert not SCANNER.applies(repo("empty"))


def test_a_malformed_pyproject_is_a_note_and_questions_not_a_crash() -> None:
    fs = MemoryFileSystem()
    fs.write_atomic(CanonicalPath.parse("pyproject.toml"), b"[project\nname = ")

    result = SCANNER.scan(fs)

    assert any("could not be parsed" in note for note in result.notes)
    assert result.facts.python.value is None


def test_an_oversized_manifest_is_not_read() -> None:
    fs = MemoryFileSystem()
    fs.write_atomic(CanonicalPath.parse("pyproject.toml"), b"#" * (MAX_FILE_BYTES + 1))

    result = SCANNER.scan(fs)

    assert any("larger than" in note for note in result.notes)


def test_windows_line_endings_cite_the_same_hash_as_unix_ones() -> None:
    unix = MemoryFileSystem()
    windows = MemoryFileSystem()
    body = '[project]\nname = "x"\nrequires-python = ">=3.12"\n'
    unix.write_atomic(CanonicalPath.parse("pyproject.toml"), body.encode())
    windows.write_atomic(CanonicalPath.parse("pyproject.toml"), body.replace("\n", "\r\n").encode())

    assert SCANNER.scan(unix).facts.python.evidence == SCANNER.scan(windows).facts.python.evidence


def test_the_same_project_always_scans_to_the_same_result() -> None:
    assert SCANNER.scan(repo("uv_fastapi")) == SCANNER.scan(repo("uv_fastapi"))


@given(st.text(max_size=300))
def test_any_pyproject_text_scans_without_raising(text: str) -> None:
    fs = MemoryFileSystem()
    fs.write_atomic(CanonicalPath.parse("pyproject.toml"), text.encode("utf-8", errors="replace"))

    with contextlib.suppress(UnicodeError):
        result = SCANNER.scan(fs)
        for item in all_evidence(result.facts):
            assert_resolves(fs, item)
