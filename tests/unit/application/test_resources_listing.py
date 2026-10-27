"""`list_resources`: the registry as rows, and the technologies that no entry covers (task
team-conventions-resources, phase P-4).

Every test cites its `expected_behavior_source`. ADR-002 is the file `adr-002-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-8 are the acceptance criteria of phase P-4 in
docs/design/team-conventions-resources/plan.yaml. "The interface decision" is the reading of the
plan author that the Tester of phase P-4 was given, because the ADRs do not spell it out:
`orqlet.application.usecases.resources_view` has `ResourcesListing` (a frozen dataclass:
`resources: tuple[Mapping[str, object], ...]`, `uncovered: tuple[str, ...]`, `findings:
tuple[Finding, ...]`) and `list_resources(services: ValidateServices, uncovered: bool)`. It uses
`load_resources`: an invalid registry gives no rows and the loader's findings, a missing one gives
no rows and no findings. Each row is a dict with exactly the keys `id`, `title`, `kind`, `access`,
`host`, `tool`, `version`, `applies_to`, `stored_copy`, in order of id and JSON-ready; every string
value is already passed through `printable(text, 200)` (`applies_to` is a list of printable
strings; `tool` and `version` are None when absent; `host` is `host_of(url)` printed; the address
itself is NOT a key; `stored_copy` is None or a dict with `form`, `sha256`, `retrieved_at`,
`ttl_days`). With `uncovered=True` the field `uncovered` holds, printed, the names of the
technologies and of `facts.frameworks` of `.orqlet/project-profile.yaml` that no entry names as its
`tool`, compared after trimming and case folding and without the version (`uncovered_names`); with
`uncovered=False` it is empty.

These tests were written first, by the Tester of phase P-4, before the module existed. The file
system is the in-memory fake of tests/fakes (ORQLET-TEST-001). Credential-shaped text is assembled
from parts at run time and never written as one literal (ORQLET-SEC-003).

Behaviour that the design leaves open is deliberately not pinned here:
- the order of the keys of a row and the order in which technologies and frameworks are listed;
- whether a name that is both a technology and a framework is listed once or twice (a name that
  is repeated among the technologies alone is listed once: `uncovered_names` does that);
- what `uncovered=True` gives when the profile is missing or invalid, and what an invalid registry
  gives in `uncovered`;
- whether `ResourcesListing.findings` has a default value;
- the wording and the paths of the findings of an invalid registry.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from orqlet.application.usecases.resources_view import ResourcesListing, list_resources

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.usecases import resources_view
from orqlet.application.usecases.validation import ValidateServices
from orqlet.domain.conventions import printable
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resources import host_of
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED

pytestmark = pytest.mark.unit

SCHEMA = "orqlet.resources/v1"
REGISTRY = ".orqlet/resources.yaml"
PROFILE = ".orqlet/project-profile.yaml"
LOADER = StrictYamlLoader()
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.project-profile.v1.yaml"
)
ROW_KEYS = {"id", "title", "kind", "access", "host", "tool", "version", "applies_to", "stored_copy"}
COPY_KEYS = {"form", "sha256", "retrieved_at", "ttl_days"}
LIMIT = 256 * 1024

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))


# --- helpers --------------------------------------------------------------------------------------


def entry(**changes: Any) -> dict[str, Any]:
    """A valid public team-docs entry. A change whose value is None removes that field."""
    base: dict[str, Any] = {
        "id": "alpha",
        "title": "Alpha guide",
        "kind": "team-docs",
        "url": "https://docs.example.com/guides/alpha",
        "note": "Read before changing the alpha module.",
        "access": "public",
    }
    merged = {**base, **changes}
    return {key: value for key, value in merged.items() if value is not None}


def fastapi_entry() -> dict[str, Any]:
    return entry(
        id="fastapi-docs",
        title="FastAPI documentation",
        kind="tool-docs",
        url="https://docs.example.com/fastapi/tutorial",
        tool="FastAPI",
        version="0.115",
        applies_to={"paths": ["src/api/**/*.py", "tests/api/**/*.py"]},
        stored_copy={
            "form": "copy",
            "sha256": "a" * 64,
            "retrieved_at": "2026-10-27T10:30:00Z",
            "ttl_days": 90,
        },
    )


def tool_entry(resource_id: str, tool: str) -> dict[str, Any]:
    return entry(
        id=resource_id, kind="tool-docs", tool=tool, url=f"https://docs.example.com/{tool}"
    )


def registry_bytes(*entries: dict[str, Any]) -> bytes:
    """A registry as JSON text, which the strict loader reads as YAML. Entries must be in order."""
    return json.dumps({"schema": SCHEMA, "resources": list(entries)}).encode()


def profile_bytes(technologies: list[str], frameworks: list[str]) -> bytes:
    """The profile of the valid fixture with the technologies and frameworks that a test names."""
    document = LOADER.load(FIXTURE.read_bytes(), source="profile")
    assert isinstance(document, dict)
    document["technologies"] = [
        {"kind": "other", "name": name, "scope": ".", "source": "maintainer"}
        for name in technologies
    ]
    document["facts"]["frameworks"] = [
        {"name": name, "value": name, "answered_by": "maintainer"} for name in frameworks
    ]
    return json.dumps(document).encode()


def project_with(
    *entries: dict[str, Any],
    technologies: list[str] | None = None,
    frameworks: list[str] | None = None,
) -> MemoryFileSystem:
    project = MemoryFileSystem()
    project.write_atomic(CanonicalPath.parse(REGISTRY), registry_bytes(*entries))
    project.write_atomic(
        CanonicalPath.parse(PROFILE), profile_bytes(technologies or [], frameworks or [])
    )
    return project


def listing(project: MemoryFileSystem, *, uncovered: bool = False) -> ResourcesListing:
    services = ValidateServices(project=project, vcs=FakeVcs(), loader=LOADER, workflow=PINNED)
    return list_resources(services, uncovered=uncovered)


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or `width` characters of it in a row (any letter case)."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


# --- the names of the module ----------------------------------------------------------------------


def test_the_listing_has_three_fields_and_is_frozen() -> None:
    """AC-8. expected_behavior_source: EC-38 (`class ResourcesListing`) and the interface decision
    ("frozen dataclass: `resources`, `uncovered`, `findings`")."""
    names = [field.name for field in dataclasses.fields(ResourcesListing)]

    assert names == ["resources", "uncovered", "findings"]
    result = ResourcesListing(resources=(), uncovered=(), findings=())
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.uncovered = ("x",)  # type: ignore[misc]


def test_list_resources_takes_the_arguments_of_the_manifest_in_order() -> None:
    """AC-8. expected_behavior_source: EC-39 (`def list_resources(services: ValidateServices,
    uncovered: bool) -> ResourcesListing`). Whether `uncovered` has a default is not pinned."""
    parameters = inspect.signature(list_resources).parameters

    assert list(parameters) == ["services", "uncovered"]


def test_the_module_has_only_the_two_public_names_of_this_phase() -> None:
    """AC-8. expected_behavior_source: plan P-4 file operation for resources_view.py
    ("`ResourcesListing` and `list_resources` only in this phase") and AC-8 ("The public API of
    the package differs from the base, in this phase, only by EC-26, EC-27, EC-30 to EC-33, EC-38,
    EC-39 and EC-47")."""
    defined = {
        name
        for name, value in vars(resources_view).items()
        if not name.startswith("_")
        and getattr(value, "__module__", None) == resources_view.__name__
    }

    assert defined == {"ResourcesListing", "list_resources"}


# --- the rows -------------------------------------------------------------------------------------


def test_every_row_has_the_nine_keys_and_the_rows_are_in_order_of_id() -> None:
    """AC-4. expected_behavior_source: AC-4 ("resources list prints the registry"), ADR-002 decision
    7 (`{id, title, kind, access, host, tool, version, applies_to, stored_copy}`) and the interface
    decision ("in order of id")."""
    project = project_with(
        entry(id="alpha"), fastapi_entry(), entry(id="gamma", url="https://docs.example.com/gamma")
    )

    result = listing(project)

    assert [row["id"] for row in result.resources] == ["alpha", "fastapi-docs", "gamma"]
    assert all(set(row) == ROW_KEYS for row in result.resources)
    assert result.findings == ()


def test_a_row_shows_the_fields_of_its_entry() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (the shapes of the row: `applies_to` is a
    list of the globs, `stored_copy` is `{form, sha256, retrieved_at, ttl_days}`) and the interface
    decision."""
    result = listing(project_with(fastapi_entry()))

    (row,) = result.resources
    assert row["id"] == "fastapi-docs"
    assert row["title"] == "FastAPI documentation"
    assert (row["kind"], row["access"]) == ("tool-docs", "public")
    assert (row["tool"], row["version"]) == ("FastAPI", "0.115")
    assert row["applies_to"] == ["src/api/**/*.py", "tests/api/**/*.py"]
    assert row["stored_copy"] == {
        "form": "copy",
        "sha256": "a" * 64,
        "retrieved_at": "2026-10-27T10:30:00Z",
        "ttl_days": 90,
    }
    assert set(row["stored_copy"]) == COPY_KEYS


def test_an_entry_without_the_optional_fields_has_none_and_an_empty_list() -> None:
    """AC-4. expected_behavior_source: the interface decision ("`stored_copy` is None or {...}; tool
    and version None when absent"; `applies_to` is a list of the globs, read as empty when there
    are none)."""
    (row,) = listing(project_with(entry())).resources

    assert (row["tool"], row["version"], row["stored_copy"]) == (None, None, None)
    assert row["applies_to"] == []


def test_the_host_is_shown_on_its_own_and_the_address_is_not_in_the_row() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("the registry in order of id with the
    host shown separately") and decision 8 (the host "is printed on its own line wherever an
    address is shown"; `host_of` is the host that was checked). A row has no field for the
    address."""
    url = "https://wiki.example.com/spaces/team/engineering-handbook"
    result = listing(project_with(entry(id="handbook", url=url, access="login")))

    (row,) = result.resources
    assert row["host"] == "wiki.example.com"
    assert row["host"] == host_of(url)
    assert "https://" not in json.dumps(result.resources)
    assert "engineering-handbook" not in json.dumps(result.resources)


def test_the_rows_are_plain_values_that_json_can_print() -> None:
    """AC-4. expected_behavior_source: AC-4 ("--json prints the shape of ADR-002 decision 7") and
    the interface decision (the rows are `dict[str, object]`)."""
    result = listing(project_with(entry(), fastapi_entry()), uncovered=True)

    rebuilt = json.loads(json.dumps({"resources": result.resources, "uncovered": result.uncovered}))

    assert [row["id"] for row in rebuilt["resources"]] == ["alpha", "fastapi-docs"]
    assert isinstance(rebuilt["uncovered"], list)


def test_a_title_goes_through_printable_so_a_backslash_is_doubled() -> None:
    """AC-4. expected_behavior_source: AC-4 ("every value from the repository is escaped by
    printable") and the interface decision ("every string value already passed through
    `orqlet.domain.conventions.printable(text, 200)`"), which doubles a backslash so that an
    escape in the output is never mistaken for text (its docstring)."""
    title = r"Docs of C:\team\docs"

    (row,) = listing(project_with(entry(title=title))).resources

    assert row["title"] == printable(title, 200)
    assert row["title"] == "Docs of C:\\\\team\\\\docs"


def test_every_string_of_every_row_is_plain_ascii() -> None:
    """AC-4. expected_behavior_source: the interface decision ("every string value is already
    passed through `printable`, so it is plain ASCII")."""
    result = listing(project_with(entry(title=r"a\b"), fastapi_entry()))

    def strings(value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [text for item in value.values() for text in strings(item)]
        if isinstance(value, list | tuple):
            return [text for item in value for text in strings(item)]
        return []

    texts = [text for row in result.resources for text in strings(row)]
    assert texts
    assert all(text.isascii() and text.isprintable() for text in texts)


def test_a_listing_writes_nothing() -> None:
    """AC-4. expected_behavior_source: ORQLET-SAFE-001 and ADR-002 decision 7 (`resources list`
    prints the registry; it is not an edit)."""
    project = project_with(entry(), technologies=["Go"])
    before = project.snapshot()

    listing(project, uncovered=True)

    assert project.snapshot() == before


# --- a registry that is missing or invalid --------------------------------------------------------


def test_a_missing_registry_is_an_empty_list_without_a_finding() -> None:
    """AC-4. expected_behavior_source: the interface decision ("a missing registry is an empty list
    with no finding") and plan P-3 AC-3 (`load_resources` gives an empty registry and no finding
    for a missing file)."""
    result = listing(MemoryFileSystem())

    assert result.resources == ()
    assert result.uncovered == ()
    assert result.findings == ()


def _overwrite(content: bytes) -> Callable[[MemoryFileSystem], None]:
    def damage(project: MemoryFileSystem) -> None:
        project.write_atomic(CanonicalPath.parse(REGISTRY), content)

    return damage


def _directory(project: MemoryFileSystem) -> None:
    project.delete(CanonicalPath.parse(REGISTRY))
    project.make_dir(CanonicalPath.parse(REGISTRY))


def _symbolic_link(project: MemoryFileSystem) -> None:
    project.add_symlink(REGISTRY)


def _padded() -> bytes:
    empty = f"schema: {SCHEMA}\nresources: []\n".encode()
    return empty + b"#" + b"x" * (LIMIT + 1 - len(empty) - 2) + b"\n"


INVALID_REGISTRIES: dict[str, tuple[Callable[[MemoryFileSystem], None], str]] = {
    "fails-its-contract": (_overwrite(registry_bytes(entry(), entry())), "ORQ-E501"),
    "refused-by-the-strict-loader": (
        _overwrite(f"schema: {SCHEMA}\nresources: &r []\nagain: *r\n".encode()),
        "ORQ-E501",
    ),
    "is-above-256-kib": (_overwrite(_padded()), "ORQ-E502"),
    "is-a-directory": (_directory, "ORQ-E500"),
    "is-a-symbolic-link": (_symbolic_link, "ORQ-E500"),
}


@pytest.mark.parametrize("name", list(INVALID_REGISTRIES), ids=list(INVALID_REGISTRIES))
@pytest.mark.parametrize("uncovered", [False, True], ids=["plain", "uncovered"])
def test_an_invalid_registry_gives_no_rows_and_the_findings_of_the_loader(
    name: str, uncovered: bool
) -> None:
    """AC-4. expected_behavior_source: the interface decision ("An invalid registry gives no rows
    and the load_resources findings in `findings`") and plan P-3 AC-3 (ORQ-E500, E501, E502)."""
    damage, loader_code = INVALID_REGISTRIES[name]
    project = project_with(entry(), technologies=["Go"])
    damage(project)

    result = listing(project, uncovered=uncovered)

    assert result.resources == ()
    assert loader_code in {finding.code for finding in result.findings}


def test_the_findings_of_an_invalid_registry_show_no_part_of_a_value() -> None:
    """AC-4. expected_behavior_source: ORQLET-SEC-003 and ADR-002 decision 10 (the findings name
    the field and the rule and never the value), through the listing."""
    bad = entry(url=f"https://docs.example.com/guide?token={TOKEN}", note=f"use `{OPAQUE}` first")
    project = MemoryFileSystem()
    project.write_atomic(CanonicalPath.parse(REGISTRY), registry_bytes(bad))

    result = listing(project)

    shown = "\n".join(f"{f.code}\n{f.message}\n{f.path}\n{f!r}" for f in result.findings)
    assert result.resources == ()
    assert result.findings
    assert not leaks(shown, TOKEN)
    assert not leaks(shown, OPAQUE)


# --- the technologies that no entry covers --------------------------------------------------------

TECHNOLOGIES = ["Go", "PostgreSQL", " Kafka "]
FRAMEWORKS = ["typer", "FastAPI"]
EVERYTHING = {"Go", "PostgreSQL", "Kafka", "typer", "FastAPI"}


def test_nothing_is_uncovered_unless_it_is_asked_for() -> None:
    """AC-4. expected_behavior_source: the interface decision ("`uncovered` is `()` unless
    asked") and ADR-002 decision 7 (`--uncovered`)."""
    project = project_with(entry(), technologies=TECHNOLOGIES, frameworks=FRAMEWORKS)

    assert listing(project).uncovered == ()


def test_without_any_tool_every_technology_and_framework_is_uncovered() -> None:
    """AC-4. expected_behavior_source: AC-4 ("--uncovered prints the technologies of the profile
    that no entry covers") and ADR-002 decision 7 (`technologies` and `facts.frameworks`). A name is
    trimmed (`uncovered_names` returns it trimmed)."""
    project = project_with(entry(), technologies=TECHNOLOGIES, frameworks=FRAMEWORKS)

    result = listing(project, uncovered=True)

    assert isinstance(result.uncovered, tuple)
    assert set(result.uncovered) == EVERYTHING


@pytest.mark.parametrize(
    ("tools", "expected"),
    [
        (["postgresql"], EVERYTHING - {"PostgreSQL"}),
        (["TYPER", "go"], EVERYTHING - {"typer", "Go"}),
        (["kafka"], EVERYTHING - {"Kafka"}),  # the technology is " Kafka ", with blanks
        (["fastapi", "kafka", "go", "postgresql", "typer"], set()),
        (["django"], EVERYTHING),
    ],
    ids=["one-tool", "case-folded", "trimmed", "all-covered", "unrelated-tool"],
)
def test_a_tool_covers_a_name_after_trimming_and_case_folding(
    tools: list[str], expected: set[str]
) -> None:
    """AC-4. expected_behavior_source: AC-4 ("the technologies of the profile that no entry
    covers"), ADR-002 decision 7 ("names are compared after trimming and case folding, without the
    version") and plan P-1 AC-3 (`uncovered_names`)."""
    entries = [tool_entry(f"tool-{index}", tool) for index, tool in enumerate(tools)]
    entries.sort(key=lambda item: str(item["id"]))
    project = project_with(*entries, technologies=TECHNOLOGIES, frameworks=FRAMEWORKS)

    result = listing(project, uncovered=True)

    assert set(result.uncovered) == expected
    assert result.findings == ()


def test_the_version_of_a_tool_does_not_make_it_another_tool() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("names are compared ... without the
    version"): the tool `Go` at any version covers the technology `Go`."""
    entries = [entry(id="go-docs", kind="tool-docs", tool="Go", version="1.25")]
    project = project_with(*entries, technologies=["Go"], frameworks=[])

    assert listing(project, uncovered=True).uncovered == ()


def test_a_name_that_is_repeated_among_the_technologies_is_listed_once() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("compared after trimming and case
    folding") and plan P-1 AC-3 (`uncovered_names` lists a name once): `Go`, `go` and ` GO ` are one
    technology, whatever scope each of them is for. The spelling that is listed is not pinned."""
    project = project_with(entry(), technologies=["Go", "go", " GO ", "Kafka"], frameworks=[])

    names = listing(project, uncovered=True).uncovered

    assert len(names) == 2
    assert {name.casefold() for name in names} == {"go", "kafka"}


def test_two_entries_for_the_same_tool_cover_it_whatever_their_versions() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 ("names are compared ... without the
    version"): the tool of one entry or of two is the same set of covered names."""
    entries = [
        entry(id="go-docs", kind="tool-docs", tool="Go", version="1.24"),
        entry(
            id="go-old", kind="tool-docs", tool="go", version="1.20", url="https://a.example.com"
        ),
    ]
    project = project_with(*entries, technologies=["GO", "Kafka"], frameworks=[])

    assert listing(project, uncovered=True).uncovered == ("Kafka",)


@pytest.mark.parametrize("title", ["::warning::boom", "ORQ-E999: forged", "back\\slash"])
def test_a_title_that_looks_like_a_command_is_data_in_its_row(title: str) -> None:
    """AC-4. expected_behavior_source: AC-4 ("every value from the repository is escaped by
    printable"), the interface decision ("every string value already passed through
    `printable(text, 200)`") and component.md rule 5. These titles are valid text (ASCII, one line)
    and are shown as `printable` shows them, as a value of the row and never as a line."""
    (row,) = listing(project_with(entry(title=title))).resources

    assert row["title"] == printable(title, 200)


def test_a_hostile_value_in_the_registry_never_comes_back_raw_in_a_finding() -> None:
    """AC-4. expected_behavior_source: ORQLET-SEC-003 and ADR-002 decision 10 (the findings name
    the field and the rule and never the value) with component.md rule 5: an escape character, a
    right-to-left override and a line break in a title, a note, an id and a glob make the registry
    invalid, and none of them reaches a finding."""
    bad = entry(
        id="x\u202ey",
        title="a\x1b[2Jb",
        note="two\nlines ORQ-E999: forged",
        applies_to={"paths": ["::\x1b*"]},
    )
    project = MemoryFileSystem()
    project.write_atomic(CanonicalPath.parse(REGISTRY), registry_bytes(bad))

    result = listing(project)

    shown = "\n".join(f"{f.code}\n{f.message}\n{f.path}\n{f!r}" for f in result.findings)
    assert result.resources == ()
    assert result.findings
    assert "\x1b" not in shown
    assert "\u202e" not in shown
    assert "ORQ-E999" not in shown


HOSTILE_NAMES = [
    "Evil\x1b[2Jname",
    "rtl\u202etext",
    "two\nlines ORQ-E999: injected",
    "back\\slash",
    "bell\x07 and nul\x00",
    "line\rbreak",
    "::warning::x",
    "caf\u00e9",
]


def test_a_hostile_technology_name_comes_back_escaped_and_is_never_raw() -> None:
    """AC-4. expected_behavior_source: AC-4 ("every value from the repository is escaped by
    printable"), the interface decision ("`uncovered` holds, printable, the technologies of the
    profile") and component.md rule 5 (every echo of text from the repository goes through
    `printable`). The profile is a file of the repository: its names can hold anything."""
    project = project_with(entry(), technologies=HOSTILE_NAMES, frameworks=[])

    result = listing(project, uncovered=True)

    assert set(result.uncovered) == {printable(name.strip(), 200) for name in HOSTILE_NAMES}
    for shown in result.uncovered:
        assert shown.isascii()
        assert shown.isprintable()
        assert "\x1b" not in shown
        assert "\u202e" not in shown
        assert "\n" not in shown
        assert "\r" not in shown


def test_a_framework_name_is_escaped_in_the_same_way() -> None:
    """AC-4. expected_behavior_source: ADR-002 decision 7 (`technologies` and `facts.frameworks`
    alike; "printed through `printable`")."""
    project = project_with(
        entry(), technologies=[], frameworks=["Evil\x1b[2Jname", "rtl\u202etext"]
    )

    result = listing(project, uncovered=True)

    assert set(result.uncovered) == {
        printable("Evil\x1b[2Jname", 200),
        printable("rtl\u202etext", 200),
    }


def test_a_very_long_name_is_cut_at_the_limit_of_200() -> None:
    """AC-4. expected_behavior_source: the interface decision ("printed through
    `orqlet.domain.conventions.printable(text, 200)`"), which cuts at its limit and ends in
    `...`."""
    project = project_with(entry(), technologies=["x" * 500], frameworks=[])

    (shown,) = listing(project, uncovered=True).uncovered

    assert shown == printable("x" * 500, 200)
    assert shown == "x" * 200 + "..."
