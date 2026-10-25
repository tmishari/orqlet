"""`evidence cite` and `evidence hash`: the values an artifact must carry."""

from __future__ import annotations

import pytest

from orqlet.application.usecases.evidence_cite import cite, file_hashes
from orqlet.application.usecases.validation import content_hash
from orqlet.domain.facts import line_range_hash
from orqlet.domain.findings import Verdict
from tests.support.artifacts import BASE, SOURCE, make_world

pytestmark = pytest.mark.unit


def test_a_citation_has_the_hash_the_validator_will_recompute() -> None:
    result = cite(make_world().services(), "src/pkg/mod.py", "1-2")

    assert result.verdict is Verdict.PASS
    assert result.data["sha256"] == line_range_hash(SOURCE, 1, 2)
    assert result.data["revision"] == BASE
    digest = line_range_hash(SOURCE, 1, 2)
    assert result.data["snippet"] == (
        f"{{path: src/pkg/mod.py, lines: 1-2, revision: {BASE}, sha256: {digest}}}"
    )


def test_a_single_line_and_an_explicit_revision_work() -> None:
    result = cite(make_world().services(), "src/pkg/mod.py", "5", BASE)

    assert result.data["lines"] == "5"
    assert result.data["sha256"] == line_range_hash(SOURCE, 5, 5)


@pytest.mark.parametrize(
    ("path", "lines", "code"),
    [
        ("src/pkg/gone.py", "1", "ORQ-E333"),
        ("src/pkg/mod.py", "40-41", "ORQ-E334"),
        ("../x.py", "1", "ORQ-E320"),
        ("src/pkg/mod.py", "3-1", "ORQ-E320"),
        ("src/pkg/mod.py", "zero", "ORQ-E320"),
    ],
)
def test_a_bad_citation_is_a_finding(path: str, lines: str, code: str) -> None:
    result = cite(make_world().services(), path, lines)

    assert result.verdict is Verdict.FAIL
    assert [f.code for f in result.findings] == [code]


def test_without_a_commit_there_is_nothing_to_cite() -> None:
    result = cite(make_world(commits=False).services(), "src/pkg/mod.py", "1")

    assert result.verdict is Verdict.NOT_RUN


def test_a_revision_that_does_not_exist_is_not_run() -> None:
    result = cite(make_world().services(), "src/pkg/mod.py", "1", "f" * 40)

    assert result.verdict is Verdict.NOT_RUN


def test_file_hashes_are_the_normalised_hash_in_reference_form() -> None:
    world = make_world()

    result = file_hashes(world.services(), ["docs/guide.md", "pyproject.toml"])

    assert result.verdict is Verdict.PASS
    assert result.data["files"] == [
        {
            "path": "docs/guide.md",
            "sha256": content_hash(b"# Guide\n"),
            "reference": f"docs/guide.md#{content_hash(b'# Guide\n')}",
        },
        {
            "path": "pyproject.toml",
            "sha256": content_hash(b"[project]\nname = 'x'\n"),
            "reference": f"pyproject.toml#{content_hash(b"[project]\nname = 'x'\n")}",
        },
    ]


def test_crlf_does_not_change_a_file_hash() -> None:
    world = make_world()
    world.put("docs/crlf.md", b"a\r\nb\r\n")
    world.put("docs/lf.md", b"a\nb\n")

    result = file_hashes(world.services(), ["docs/crlf.md", "docs/lf.md"])

    files = result.data["files"]
    assert isinstance(files, list)
    assert files[0]["sha256"] == files[1]["sha256"]


def test_a_missing_file_or_no_file_is_reported_and_never_a_pass() -> None:
    world = make_world()

    assert [f.code for f in file_hashes(world.services(), ["nope.md"]).findings] == ["ORQ-E321"]
    assert file_hashes(world.services(), []).verdict is Verdict.NOT_RUN
