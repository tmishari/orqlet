"""`resources_path`, `parse_resources` and `load_resources` (task team-conventions-resources,
phase P-2).

Every test cites its `expected_behavior_source`. ADR-002 is the file `adr-002-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-6 are the acceptance criteria of phase P-2 (AC-1 of phase P-3 fixes the
finding codes: ORQ-E500 the registry cannot be read safely, ORQ-E501 it fails its contract,
ORQ-E502 it is above 256 KiB) in docs/design/team-conventions-resources/plan.yaml.

These tests were written first, by the Tester of phase P-2, before the reader existed. They cover
AC-2 (no message of a finding holds a part of an input value) and AC-3 (a missing file is an empty
registry; an unreadable, oversized or invalid file gives no registry and a finding).

Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003). The file system is the in-memory fake of tests/fakes (ORQLET-TEST-001).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message, the severity of a finding, and what `Finding.path` holds (only the
  code, that the message is not empty and that no part of an input value appears are checked);
- how many findings one bad file gives (only the set of codes is checked);
- what happens for a `path` that is not a canonical repository path (`../x`, an empty string);
- a file that disappears between the check for its kind and its read;
- whether a KEY, a tag or an anchor name of the document (which the strict loader's own messages
  repeat, for example `duplicate key ...`) may appear in a finding: the design speaks of values;
- whether a zero-byte file is an empty registry or a contract failure (it is tested here as the
  second, because the strict loader returns nothing for it and a registry needs `schema` and
  `resources`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.filesystem import FileSystemError
from orqlet.application.usecases.resources_source import (
    load_resources,
    parse_resources,
    resources_path,
)
from orqlet.domain.findings import Finding
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem

pytestmark = pytest.mark.unit

type Outcome = tuple[Resources | None, tuple[Finding, ...]]

SCHEMA = "orqlet.resources/v1"
PATH = ".orqlet/resources.yaml"
LIMIT = 256 * 1024  # ADR-002 decision 10: a file above 256 KiB is refused
UNREADABLE = "ORQ-E500"  # plan P-3 AC-1: the registry cannot be read safely
CONTRACT = "ORQ-E501"  # it fails its contract
TOO_BIG = "ORQ-E502"  # it is above 256 KiB
EMPTY_DOC = b"schema: orqlet.resources/v1\nresources: []\n"
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.resources.v1.yaml"
)
LOADER = StrictYamlLoader()


# --- helpers --------------------------------------------------------------------------------------


class CountingLoader:
    """The strict loader, counting how often it is asked to parse."""

    def __init__(self) -> None:
        self.calls = 0
        self._inner = StrictYamlLoader()

    def load(self, data: bytes, *, source: str) -> object:
        self.calls += 1
        return self._inner.load(data, source=source)


class UnreadableFileSystem(MemoryFileSystem):
    """A file system whose files can be listed and found but not read (a permission error)."""

    def read_bytes(self, path: CanonicalPath) -> bytes:
        raise FileSystemError("the file cannot be read")


def empty_registry() -> Resources:
    """The empty registry, built the way the design says: load `resources: []`."""
    return load_contract(LOADER, Resources, EMPTY_DOC, source="empty")


def fixture_bytes() -> bytes:
    return FIXTURE.read_bytes()


def padded(size: int) -> bytes:
    """A valid, empty registry followed by a comment, so that the file is exactly `size` bytes."""
    filler = size - len(EMPTY_DOC) - 2
    assert filler >= 0
    return EMPTY_DOC + b"#" + b"x" * filler + b"\n"


def project_with(content: bytes, path: str = PATH) -> MemoryFileSystem:
    project = MemoryFileSystem()
    project.write_atomic(CanonicalPath.parse(path), content)
    return project


def entry(**changes: Any) -> dict[str, Any]:
    """A valid public team-docs entry. A change whose value is None removes that field."""
    base: dict[str, Any] = {
        "id": "alpha",
        "title": "Alpha guide",
        "kind": "team-docs",
        "url": "https://docs.example.com/alpha",
        "note": "Read before changing the alpha module.",
        "access": "public",
    }
    merged = {**base, **changes}
    return {key: value for key, value in merged.items() if value is not None}


def copy_of(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "form": "copy",
        "sha256": "a" * 64,
        "retrieved_at": "2026-10-27T10:30:00Z",
        "ttl_days": 30,
    }
    return {**base, **changes}


def document(*entries: dict[str, Any], **top: Any) -> bytes:
    """A registry as JSON text, which the strict loader reads as YAML."""
    data: dict[str, Any] = {"schema": SCHEMA, "resources": list(entries), **top}
    return json.dumps(data).encode()


def numbered(count: int) -> list[dict[str, Any]]:
    return [
        entry(id=f"r{number:03d}", url=f"https://docs.example.com/r{number:03d}")
        for number in range(count)
    ]


def codes_of(findings: tuple[Finding, ...]) -> set[str]:
    return {finding.code for finding in findings}


def assert_refusal(outcome: Outcome, code: str) -> tuple[Finding, ...]:
    """No registry, at least one finding, every finding with `code` and a message."""
    registry, findings = outcome
    assert registry is None
    assert isinstance(findings, tuple)
    assert findings
    assert all(isinstance(finding, Finding) for finding in findings)
    assert codes_of(findings) == {code}
    assert all(finding.message.strip() for finding in findings)
    return findings


def shown(findings: tuple[Finding, ...]) -> str:
    """Everything that findings show: code, message, path and the representation."""
    return "\n".join(
        f"{finding.code}\n{finding.message}\n{finding.path}\n{finding!r}" for finding in findings
    )


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it (any letter case).

    A window of 8 characters of a random-looking secret cannot appear in a fixed message by chance.
    """
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
ACCESS_KEY = "".join(("AK", "IA", "QZ7XV3LM", "9TK2RB8W"))
PASSWORD = "".join(("hunter", "2Qx", "9Lp", "Vw4"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))

# case name -> (the file, the secrets that no message may show)
SECRET_FILES: dict[str, tuple[bytes, tuple[str, ...]]] = {
    "address": (document(entry(url=f"https://docs.example.com/guide?token={TOKEN}")), (TOKEN,)),
    "address-with-user-information": (
        document(entry(url=f"https://deploy:{PASSWORD}@docs.example.com/guide")),
        (PASSWORD,),
    ),
    "address-with-an-opaque-segment": (
        document(entry(url=f"https://docs.example.com/{OPAQUE}")),
        (OPAQUE,),
    ),
    "note": (document(entry(note=f"use `{TOKEN}` first")), (TOKEN,)),
    "note-with-a-link": (
        document(entry(note=f"see https://{ACCESS_KEY}.example.com/x")),
        (ACCESS_KEY,),
    ),
    "title": (document(entry(title=f"[{TOKEN}](x)")), (TOKEN,)),
    "glob": (document(entry(applies_to={"paths": [f"!{TOKEN}"]})), (TOKEN,)),
    "glob-climbing-out": (
        document(entry(applies_to={"paths": [f"{ACCESS_KEY}/../x"]})),
        (ACCESS_KEY,),
    ),
    "copy-sha256": (document(entry(stored_copy=copy_of(sha256=TOKEN))), (TOKEN,)),
    "copy-retrieved-at": (document(entry(stored_copy=copy_of(retrieved_at=TOKEN))), (TOKEN,)),
    "copy-form": (document(entry(stored_copy=copy_of(form=TOKEN))), (TOKEN,)),
    "copy-ttl-days": (document(entry(stored_copy=copy_of(ttl_days=TOKEN))), (TOKEN,)),
    "id": (document(entry(id=TOKEN)), (TOKEN,)),
    "repeated-id": (
        document(entry(id=OPAQUE.lower()), entry(id=OPAQUE.lower())),
        (OPAQUE.lower(),),
    ),
    "ids-out-of-order": (
        document(entry(id=OPAQUE.lower()), entry(id="aaa")),
        (OPAQUE.lower(),),
    ),
    "tool-on-the-wrong-kind": (document(entry(tool=TOKEN)), (TOKEN,)),
    "version": (
        document(entry(kind="tool-docs", tool="demo", version=f"{TOKEN}#")),
        (TOKEN,),
    ),
    "login-entry-with-a-full-copy": (
        document(entry(id=OPAQUE.lower(), access="login", stored_copy=copy_of(form="copy"))),
        (OPAQUE.lower(),),
    ),
    "several-fields-at-once": (
        document(
            entry(
                id=ACCESS_KEY,
                title=f"[{PASSWORD}](x)",
                url=f"https://docs.example.com/guide?token={TOKEN}",
                note=f"see `{OPAQUE}`",
                applies_to={"paths": [f"!{TOKEN}"]},
                stored_copy=copy_of(sha256=ACCESS_KEY, retrieved_at=PASSWORD, ttl_days=OPAQUE),
            )
        ),
        (TOKEN, ACCESS_KEY, PASSWORD, OPAQUE),
    ),
}

# --- files that fail the contract, and files that fail the strict loader --------------------------

CONTRACT_FAILURES: dict[str, bytes] = {
    "repeated-id": document(entry(id="alpha"), entry(id="alpha")),
    "ids-out-of-order": document(entry(id="beta"), entry(id="alpha")),
    "id-that-fails-resource-id-problems": document(entry(id="Alpha")),
    "address-that-fails-url-problems": document(entry(url="http://docs.example.com/")),
    "note-that-fails-text-problems": document(entry(note="run `make`")),
    "title-that-fails-text-problems": document(entry(title="two\nlines")),
    "glob-that-fails-glob-problems": document(entry(applies_to={"paths": ["/abs/*.py"]})),
    "nine-globs": document(entry(applies_to={"paths": [f"src/p{n}/*.py" for n in range(9)]})),
    "tool-on-an-entry-that-is-not-tool-docs": document(entry(kind="team-docs", tool="FastAPI")),
    "login-entry-with-a-full-copy": document(entry(access="login", stored_copy=copy_of())),
    "public-entry-on-an-internal-host": document(entry(url="https://wiki.example.internal/x")),
    "time-to-live-of-zero": document(entry(stored_copy=copy_of(ttl_days=0))),
    "time-to-live-of-366": document(entry(stored_copy=copy_of(ttl_days=366))),
    "stored-copy-without-a-time-to-live": document(
        entry(stored_copy={k: v for k, v in copy_of().items() if k != "ttl_days"})
    ),
    "timestamp-without-a-zone": document(
        entry(stored_copy=copy_of(retrieved_at="2026-10-27T10:30:00"))
    ),
    "date-only-timestamp": document(entry(stored_copy=copy_of(retrieved_at="2026-10-27"))),
    "unknown-field-in-an-entry": document(entry(surprise=1)),
    "unknown-top-level-field": document(entry(), surprise=1),
    "another-schema": document(entry(), schema="orqlet.resources/v2"),
    "entry-without-a-note": document(entry(note=None)),
    "more-than-100-entries": document(*numbered(101)),
}
LOADER_FAILURES: dict[str, bytes] = {
    "alias": b"schema: orqlet.resources/v1\nresources: &r []\nagain: *r\n",
    "anchor": b"schema: orqlet.resources/v1\nresources: &r []\n",
    "duplicate-key": b"schema: orqlet.resources/v1\nresources: []\nresources: []\n",
    "merge-key": b"schema: orqlet.resources/v1\nresources: []\n<<: {}\n",
    "python-tag": b"schema: orqlet.resources/v1\nresources: !!python/object/apply:os.getcwd []\n",
    "local-tag": b"schema: orqlet.resources/v1\nresources: !local []\n",
    "invalid-utf-8": b"schema: orqlet.resources/v1\nresources: [\xff\xfe]\n",
    "control-character": b"schema: orqlet.resources/v1\nresources: []\n\x00",
    "not-yaml": b"{{{ not yaml",
    "two-documents": EMPTY_DOC + b"---\n" + EMPTY_DOC,
    "nesting-deeper-than-the-loader-allows": (
        b"schema: orqlet.resources/v1\nresources: " + b"[" * 40 + b"]" * 40 + b"\n"
    ),
    "a-list": b"- one\n- two\n",
    "a-scalar": b"just text\n",
    "an-empty-file": b"",
}


# --- EC-22: where the registry lives --------------------------------------------------------------


def test_the_registry_is_the_file_orqlet_resources_yaml() -> None:
    """AC-3. expected_behavior_source: EC-22 (`resources_path() -> CanonicalPath`) and ADR-002
    decision 1 (one seeded file, `.orqlet/resources.yaml`)."""
    path = resources_path()

    assert isinstance(path, CanonicalPath)
    assert path == CanonicalPath.parse(PATH)
    assert str(path) == PATH


# --- parse_resources ------------------------------------------------------------------------------


def test_the_empty_registry_has_no_entries() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 (an empty valid registry is
    `schema: orqlet.resources/v1` and `resources: []`) and the assignment of this phase ("an empty
    Resources has no entries")."""
    assert len(empty_registry().resources) == 0


def test_parse_resources_gives_the_registry_of_a_valid_document_and_no_finding() -> None:
    """AC-3. expected_behavior_source: EC-23 (`parse_resources(loader, raw, source) ->
    tuple[Resources | None, tuple[Finding, ...]]`) and ADR-002 decision 6 ("`parse_resources`
    turns bytes into a `Resources` through the document loader")."""
    expected = load_contract(LOADER, Resources, fixture_bytes(), source="expected")

    outcome = parse_resources(LOADER, fixture_bytes(), "fixture")

    assert outcome == (expected, ())
    assert len(expected.resources) == 2


def test_parse_resources_gives_the_empty_registry_for_an_empty_document() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 and EC-23."""
    assert parse_resources(LOADER, EMPTY_DOC, "empty") == (empty_registry(), ())


@pytest.mark.parametrize("name", list(CONTRACT_FAILURES), ids=list(CONTRACT_FAILURES))
def test_parse_resources_refuses_a_document_that_fails_the_contract(name: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("no registry and a finding for an ... invalid
    file"), AC-1 (the rules of the contract), ADR-002 decision 10 ("a file that ... fails its
    contract returns findings and no registry") and plan P-3 AC-1 (ORQ-E501)."""
    assert_refusal(parse_resources(LOADER, CONTRACT_FAILURES[name], "registry"), CONTRACT)


@pytest.mark.parametrize("name", list(LOADER_FAILURES), ids=list(LOADER_FAILURES))
def test_parse_resources_refuses_a_document_that_fails_the_strict_loader(name: str) -> None:
    """AC-3. expected_behavior_source: AC-3 (an invalid file), plan P-2 file operation on
    test_resources_source.py ("a file with anchors or duplicate keys is refused by the strict
    loader"), ADR-002 decision 10 (read through the strict loader; "returns findings instead of
    raising") and plan P-3 AC-1 (ORQ-E501)."""
    assert_refusal(parse_resources(LOADER, LOADER_FAILURES[name], "registry"), CONTRACT)


def test_parse_resources_gives_the_same_answer_for_the_same_bytes() -> None:
    """AC-3. expected_behavior_source: ORQLET-DET-001 (deterministic output) and EC-23."""
    first = parse_resources(LOADER, CONTRACT_FAILURES["repeated-id"], "registry")
    second = parse_resources(LOADER, CONTRACT_FAILURES["repeated-id"], "registry")

    assert first == second


# --- the 256 KiB limit ----------------------------------------------------------------------------


@pytest.mark.parametrize("size", [LIMIT + 1, 2 * LIMIT, 8 * LIMIT])
def test_bytes_above_256_kib_are_refused_before_they_are_parsed(size: int) -> None:
    """AC-3. expected_behavior_source: AC-3 ("oversized (more than 256 KiB, checked after the read
    and before parsing)"), ADR-002 decision 10 ("refused after reading and before parsing") and
    plan P-3 AC-1 (ORQ-E502). The padded text is a valid registry, so only its size is wrong; the
    loader of the test has the default bound of 1 MiB, so the refusal is not the loader's."""
    loader = CountingLoader()

    outcome = parse_resources(loader, padded(size), "registry")

    assert_refusal(outcome, TOO_BIG)
    assert loader.calls == 0


def test_oversized_bytes_that_are_not_even_yaml_are_refused_for_their_size() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 10 (the size is checked "after reading and
    before parsing", so it comes before every other check) and plan P-3 AC-1 (ORQ-E502)."""
    loader = CountingLoader()

    outcome = parse_resources(loader, b"{{{" * LIMIT, "registry")

    assert_refusal(outcome, TOO_BIG)
    assert loader.calls == 0


def test_bytes_of_exactly_256_kib_are_not_above_the_limit() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 10 ("a file above 256 KiB ... is
    refused": a file of exactly 256 KiB is not above it, so it is parsed)."""
    raw = padded(LIMIT)
    assert len(raw) == LIMIT

    assert parse_resources(LOADER, raw, "registry") == (empty_registry(), ())


# --- load_resources: missing, unreadable, oversized ----------------------------------------------


def test_a_missing_file_is_an_empty_registry_and_no_finding() -> None:
    """AC-3. expected_behavior_source: AC-3 ("load_resources returns an empty Resources and no
    finding for a missing file"), ADR-002 decisions 6 and 10 and EC-24."""
    project = MemoryFileSystem()

    outcome = load_resources(project, LOADER, PATH)

    assert outcome == (empty_registry(), ())
    assert project.snapshot() == {}


def test_a_missing_file_in_an_existing_folder_is_an_empty_registry_and_no_finding() -> None:
    """AC-3. expected_behavior_source: AC-3 and ADR-002 decision 6 ("a registry that is missing
    and not recorded is an empty one")."""
    project = project_with(b"x: 1\n", ".orqlet/other.yaml")

    outcome = load_resources(project, LOADER, PATH)

    assert outcome == (empty_registry(), ())


def test_a_valid_file_loads_and_nothing_is_written() -> None:
    """AC-3. expected_behavior_source: EC-24 (`load_resources(project, loader, path) ->
    tuple[Resources | None, tuple[Finding, ...]]`) and ADR-002 decision 6 ("`load_resources` reads
    the file through the `FileSystem` port")."""
    project = project_with(fixture_bytes())
    before = project.snapshot()
    expected = load_contract(LOADER, Resources, fixture_bytes(), source="expected")

    outcome = load_resources(project, LOADER, PATH)

    assert outcome == (expected, ())
    assert project.snapshot() == before


def test_load_resources_reads_the_path_it_is_given() -> None:
    """AC-3. expected_behavior_source: EC-24 (the `path` parameter) and plan P-3 file operation on
    commands/validate.py (`validate resources` takes a file argument that defaults to the
    registry)."""
    project = project_with(fixture_bytes(), "other/registry.yaml")
    expected = load_contract(LOADER, Resources, fixture_bytes(), source="expected")

    assert load_resources(project, LOADER, "other/registry.yaml") == (expected, ())
    assert load_resources(project, LOADER, PATH) == (empty_registry(), ())


@pytest.mark.parametrize(
    "content",
    [fixture_bytes(), EMPTY_DOC, *CONTRACT_FAILURES.values(), *LOADER_FAILURES.values()],
    ids=[
        "fixture",
        "empty-registry",
        *(f"contract-{name}" for name in CONTRACT_FAILURES),
        *(f"loader-{name}" for name in LOADER_FAILURES),
    ],
)
def test_load_resources_gives_the_answer_of_parse_resources_for_the_bytes_of_the_file(
    content: bytes,
) -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 6 ("`load_resources` reads the file through
    the `FileSystem` port and calls it") and component rule 1 (one reading of the registry)."""
    parsed, parse_findings = parse_resources(LOADER, content, PATH)

    loaded, load_findings = load_resources(project_with(content), LOADER, PATH)

    assert loaded == parsed
    assert codes_of(load_findings) == codes_of(parse_findings)


def test_a_directory_in_the_place_of_the_file_cannot_be_read_safely() -> None:
    """AC-3. expected_behavior_source: AC-3 ("no registry and a finding for an unreadable ...
    file"), ADR-002 decision 10 ("returns findings instead of raising") and plan P-3 AC-1
    (ORQ-E500). The port refuses a read of anything that is not a regular file."""
    project = MemoryFileSystem()
    project.make_dir(CanonicalPath.parse(PATH))
    loader = CountingLoader()

    outcome = load_resources(project, loader, PATH)

    assert_refusal(outcome, UNREADABLE)
    assert loader.calls == 0


def test_a_symbolic_link_in_the_place_of_the_file_cannot_be_read_safely() -> None:
    """AC-3. expected_behavior_source: AC-3, ORQLET-SEC-002 (read through the FileSystem port,
    which refuses links), ADR-002 decision 10 and plan P-3 AC-1 (ORQ-E500)."""
    project = MemoryFileSystem()
    project.add_symlink(PATH)
    loader = CountingLoader()

    outcome = load_resources(project, loader, PATH)

    assert_refusal(outcome, UNREADABLE)
    assert loader.calls == 0


def test_a_symbolic_link_above_the_file_cannot_be_read_safely() -> None:
    """AC-3. expected_behavior_source: AC-3, the FileSystem port ("a link above it raises
    `LinkRefused`, because nothing below a link may be trusted"), ADR-002 decision 10 ("returns
    findings instead of raising") and plan P-3 AC-1 (ORQ-E500)."""
    project = project_with(fixture_bytes())
    project.add_symlink(".orqlet")
    loader = CountingLoader()

    outcome = load_resources(project, loader, PATH)

    assert_refusal(outcome, UNREADABLE)
    assert loader.calls == 0


def test_a_file_that_the_port_cannot_read_is_a_finding_and_not_an_exception() -> None:
    """AC-3. expected_behavior_source: AC-3 ("no registry and a finding for an unreadable
    ... file"), ADR-002 decision 10 ("returns findings instead of raising") and plan P-3 AC-1
    (ORQ-E500). The local adapter raises `FileSystemError` for an error of the operating
    system, such as a permission error."""
    project = UnreadableFileSystem()
    project.write_atomic(CanonicalPath.parse(PATH), fixture_bytes())
    loader = CountingLoader()

    outcome = load_resources(project, loader, PATH)

    assert_refusal(outcome, UNREADABLE)
    assert loader.calls == 0


@pytest.mark.parametrize("size", [LIMIT + 1, 2 * LIMIT])
def test_a_file_above_256_kib_is_refused_after_it_is_read_and_before_it_is_parsed(
    size: int,
) -> None:
    """AC-3. expected_behavior_source: AC-3 ("oversized (more than 256 KiB, checked after the read
    and before parsing)"), ADR-002 decision 10 and plan P-3 AC-1 (ORQ-E502)."""
    project = project_with(padded(size))
    loader = CountingLoader()

    outcome = load_resources(project, loader, PATH)

    assert_refusal(outcome, TOO_BIG)
    assert loader.calls == 0


def test_a_file_of_exactly_256_kib_is_loaded() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 10 (only a file above 256 KiB is
    refused)."""
    project = project_with(padded(LIMIT))

    assert load_resources(project, LOADER, PATH) == (empty_registry(), ())


@pytest.mark.parametrize("name", ["repeated-id", "address-that-fails-url-problems"])
def test_a_file_that_fails_the_contract_gives_no_registry_and_a_finding(name: str) -> None:
    """AC-3. expected_behavior_source: AC-3 ("no registry and a finding for an unreadable,
    oversized ... or invalid file"), ADR-002 decision 10 and plan P-3 AC-1 (ORQ-E501)."""
    project = project_with(CONTRACT_FAILURES[name])

    assert_refusal(load_resources(project, LOADER, PATH), CONTRACT)
    assert project.snapshot() == {PATH: CONTRACT_FAILURES[name]}


# --- AC-2: no message holds a part of an input value ----------------------------------------------


@pytest.mark.parametrize("name", list(SECRET_FILES), ids=list(SECRET_FILES))
def test_no_finding_of_parse_resources_shows_a_part_of_the_input(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("no message of the contract, the loader or the
    findings contains a part of any input value: a test places credential-shaped text in the
    address, the note, a glob and the copy fields and asserts that nothing appears in a finding,
    an exception message, standard output or standard error"), ADR-002 decision 10 and
    ORQLET-SEC-003."""
    content, secrets = SECRET_FILES[name]

    findings = assert_refusal(parse_resources(LOADER, content, "registry"), CONTRACT)
    streams = capsys.readouterr()

    for secret in secrets:
        assert not leaks(shown(findings), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


@pytest.mark.parametrize("name", list(SECRET_FILES), ids=list(SECRET_FILES))
def test_no_finding_of_load_resources_shows_a_part_of_the_input(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2. expected_behavior_source: AC-2, ADR-002 decision 10 and ORQLET-SEC-003 (the same as
    above, through the file system port)."""
    content, secrets = SECRET_FILES[name]

    findings = assert_refusal(load_resources(project_with(content), LOADER, PATH), CONTRACT)
    streams = capsys.readouterr()

    for secret in secrets:
        assert not leaks(shown(findings), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


def test_an_oversized_file_of_credential_shaped_text_is_refused_without_showing_it() -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-002 decision 10 (the size check comes before
    any parsing, and its finding names the rule only)."""
    content = (f"token: {TOKEN}\n".encode() * (LIMIT // 8))[: LIMIT + 1]

    findings = assert_refusal(parse_resources(LOADER, content, "registry"), TOO_BIG)

    assert not leaks(shown(findings), TOKEN)


def test_a_bad_input_never_raises_out_of_the_reader() -> None:
    """AC-3. expected_behavior_source: ADR-002 decision 10 ("It returns findings instead of
    raising") and plan P-3 file operation on upgrade.py (the reader's result decides whether
    `upgrade` is refused, so it must be a value)."""
    for content in [*CONTRACT_FAILURES.values(), *LOADER_FAILURES.values()]:
        registry, findings = parse_resources(LOADER, content, "registry")

        assert registry is None
        assert findings
