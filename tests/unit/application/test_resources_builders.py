"""`ResourceSpec`, `resources_with` and `resources_without` (task team-conventions-resources,
phase P-3).

Every test cites its `expected_behavior_source`. ADR-002 is the file `adr-002-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, AC-1 to AC-8 are the acceptance criteria of phase P-3 and "the interface decision" is
the reading of the plan author that the Tester of phase P-3 was given, because the ADRs do not
spell it out: `ResourceSpec` is a frozen dataclass with the required `id` and the optional `url`,
`title`, `kind`, `note`, `access`, `paths`, `tool` and `version`, all `None` for "not given";
`resources_with(..., replace=False)` adds and needs url, title, kind, note and access;
`replace=True` updates the entry of that id and changes only the fields that are given and keeps
the stored copy record; both refuse with no registry and the finding ORQ-E509; the result is in
order of id; neither builder does any I/O.

These tests were written first, by the Tester of phase P-3, before the builders existed.
Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003).

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message, and what `Finding.path` holds;
- whether an update that gives no field (only the id) is refused or changes nothing;
- whether a field can be cleared by an update (`None` means "not given", so a tool, a version or a
  list of paths can only be replaced, never removed);
- whether an update of the address of an entry with a stored copy returns a finding next to the
  new registry (ADR-002 decision 7 says the command "prints" that the `Source:` line no longer
  matches; where that text comes from is not said);
- what an empty `paths` tuple means for a new entry (no `applies_to` or an empty one);
- the findings of an accepted call beyond "no error".
"""

from __future__ import annotations

import dataclasses
import inspect
import itertools
import json
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import Resource, Resources
from orqlet.application.usecases.resources_edit import (
    ResourceSpec,
    resources_with,
    resources_without,
)
from orqlet.domain.findings import Finding, Severity
from orqlet.domain.resources import resource_id_problems

pytestmark = pytest.mark.unit

type Outcome = tuple[Resources | None, tuple[Finding, ...]]

SCHEMA = "orqlet.resources/v1"
REFUSED = "ORQ-E509"  # plan P-3 AC-1: an edit builder or command is refused
LOADER = StrictYamlLoader()
SPEC_FIELDS = {"id", "url", "title", "kind", "note", "access", "paths", "tool", "version"}
REQUIRED_FOR_AN_ADD = ("url", "title", "kind", "note", "access")

# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
ACCESS_KEY = "".join(("AK", "IA", "QZ7XV3LM", "9TK2RB8W"))
PASSWORD = "".join(("hunter", "2Qx", "9Lp", "Vw4"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))


# --- helpers --------------------------------------------------------------------------------------


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


def stored_copy(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "form": "copy",
        "sha256": "a" * 64,
        "retrieved_at": "2026-10-27T10:30:00Z",
        "ttl_days": 30,
    }
    return {**base, **changes}


def registry(*entries: dict[str, Any]) -> Resources:
    """A registry built the way the design says: load the document."""
    document = {"schema": SCHEMA, "resources": list(entries)}
    return load_contract(LOADER, Resources, json.dumps(document).encode(), source="registry")


def rich_registry() -> Resources:
    """Three entries; `alpha` has every optional field and a stored copy."""
    return registry(
        entry(
            id="alpha",
            kind="tool-docs",
            tool="FastAPI",
            version="0.115",
            applies_to={"paths": ["src/api/**/*.py"]},
            stored_copy=stored_copy(),
        ),
        entry(id="beta", url="https://docs.example.com/beta"),
        entry(id="gamma", url="https://docs.example.com/gamma", access="login"),
    )


def numbered(count: int) -> list[dict[str, Any]]:
    return [
        entry(id=f"r{number:03d}", url=f"https://docs.example.com/r{number:03d}")
        for number in range(count)
    ]


def spec(**changes: Any) -> ResourceSpec:
    """A spec with the five fields that an add needs. A change whose value is None leaves it out."""
    base: dict[str, Any] = {
        "id": "alpha",
        "url": "https://docs.example.com/alpha",
        "title": "Alpha guide",
        "kind": "team-docs",
        "note": "Read before changing the alpha module.",
        "access": "public",
    }
    return ResourceSpec(**{**base, **changes})


def added(resources: Resources, **changes: Any) -> Outcome:
    return resources_with(resources, spec(**changes), replace=False)


def updated(resources: Resources, **changes: Any) -> Outcome:
    """An update: the spec holds the id and only the fields that change."""
    return resources_with(resources, ResourceSpec(**changes), replace=True)


def item(resources: Resources, resource_id: str) -> Resource:
    return next(found for found in resources.resources if found.id == resource_id)


def ids_of(resources: Resources) -> list[str]:
    return [found.id for found in resources.resources]


def assert_accepted(outcome: Outcome) -> Resources:
    """A registry and no error. The design fixes the refusal, not the findings of a success."""
    result, findings = outcome
    assert result is not None, findings
    assert isinstance(result, Resources)
    assert not [finding for finding in findings if finding.severity is Severity.ERROR]
    return result


def assert_refused(outcome: Outcome) -> tuple[Finding, ...]:
    """No registry, and findings that all carry the code of a refused edit."""
    result, findings = outcome
    assert result is None
    assert isinstance(findings, tuple)
    assert findings
    assert all(isinstance(finding, Finding) for finding in findings)
    assert {finding.code for finding in findings} == {REFUSED}
    assert all(finding.severity is Severity.ERROR for finding in findings)
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


# --- ResourceSpec ---------------------------------------------------------------------------------


def test_resource_spec_has_the_nine_fields_and_only_the_id_is_required() -> None:
    """AC-6. expected_behavior_source: EC-25 (`class ResourceSpec`) and the interface decision
    ("`id: str` (required) and, all defaulting to `None` meaning 'not given': url, title, kind,
    note, access, paths, tool, version")."""
    fields = {field.name: field for field in dataclasses.fields(ResourceSpec)}

    assert set(fields) == SPEC_FIELDS
    required = {
        name
        for name, field in fields.items()
        if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING
    }
    assert required == {"id"}
    assert all(fields[name].default is None for name in SPEC_FIELDS - {"id"})
    bare = ResourceSpec(id="alpha")
    assert all(getattr(bare, name) is None for name in SPEC_FIELDS - {"id"})


def test_resource_spec_is_frozen() -> None:
    """AC-6. expected_behavior_source: the interface decision ("a frozen dataclass")."""
    bare = ResourceSpec(id="alpha")

    for name in sorted(SPEC_FIELDS):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(bare, name, "x")


def test_resource_spec_cannot_be_built_without_an_id_or_with_a_stranger_field() -> None:
    """AC-6. expected_behavior_source: the interface decision (`id` required; nine fields only)."""
    with pytest.raises(TypeError):
        ResourceSpec()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ResourceSpec(id="alpha", stored_copy=None)  # type: ignore[call-arg]


def test_the_builders_take_no_file_system_clock_or_services() -> None:
    """AC-6. expected_behavior_source: AC-6 ("carry no I/O"), EC-28 and EC-29 (the signatures:
    `resources_with(resources, spec, replace)` and `resources_without(resources, resource_id)`)
    and the interface decision ("Neither builder does any I/O")."""
    with_names = list(inspect.signature(resources_with).parameters)
    without_names = list(inspect.signature(resources_without).parameters)

    assert with_names == ["resources", "spec", "replace"]
    assert without_names == ["resources", "resource_id"]


# --- resources_with: adding -----------------------------------------------------------------------


def test_adding_to_the_empty_registry_gives_one_entry_with_the_given_fields() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 (`resources_with` builds the registry
    that `add` writes) and the interface decision ("`resources_with(resources, spec,
    replace=False)` adds")."""
    result = assert_accepted(added(registry()))

    (found,) = result.resources
    assert (found.id, found.url, found.title, found.kind, found.note, found.access) == (
        "alpha",
        "https://docs.example.com/alpha",
        "Alpha guide",
        "team-docs",
        "Read before changing the alpha module.",
        "public",
    )
    assert found.stored_copy is None  # a builder never invents a copy record
    assert (found.tool, found.version) == (None, None)
    assert not (found.applies_to and found.applies_to.paths)


def test_an_add_with_every_optional_field_keeps_each_of_them() -> None:
    """AC-6. expected_behavior_source: the interface decision (the spec carries `paths`, `tool`
    and `version`) and ADR-002 decision 1 (their meaning in the contract)."""
    result = assert_accepted(
        added(
            registry(),
            id="fastapi-docs",
            kind="tool-docs",
            tool="FastAPI",
            version="0.115",
            paths=("src/api/**/*.py", "tests/api/**/*.py"),
        )
    )

    (found,) = result.resources
    assert (found.tool, found.version) == ("FastAPI", "0.115")
    assert found.applies_to is not None
    assert found.applies_to.paths == ("src/api/**/*.py", "tests/api/**/*.py")
    assert result.covered_tools() == ("FastAPI",)


def test_an_add_gives_the_entries_in_order_of_id_whatever_the_order_of_the_calls() -> None:
    """AC-6. expected_behavior_source: AC-6 ("The pure builders keep order of id"), ADR-002
    decision 1 ("written in order of id") and the interface decision ("The result is always in
    order of id")."""
    resources = registry()
    for resource_id in ("zeta", "alpha", "mid", "beta"):
        resources = assert_accepted(
            added(resources, id=resource_id, url=f"https://docs.example.com/{resource_id}")
        )

    assert ids_of(resources) == ["alpha", "beta", "mid", "zeta"]


def test_an_add_leaves_the_other_entries_as_they_were() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 (an edit changes one entry) and the
    interface decision ("`resources_with` adds")."""
    before = rich_registry()

    result = assert_accepted(added(before, id="delta", url="https://docs.example.com/delta"))

    for kept in ("alpha", "beta", "gamma"):
        assert item(result, kept) == item(before, kept)
    assert ids_of(result) == ["alpha", "beta", "delta", "gamma"]


def test_a_builder_does_not_change_the_registry_it_is_given() -> None:
    """AC-6. expected_behavior_source: the interface decision ("returns a new Resources") and
    EC-28 (the signature has no output parameter)."""
    before = rich_registry()
    snapshot = before.model_dump(by_alias=True)

    added_result = assert_accepted(added(before, id="delta"))
    updated_result = assert_accepted(updated(before, id="beta", note="A new note."))
    removed_result = assert_accepted(resources_without(before, "beta"))

    assert before.model_dump(by_alias=True) == snapshot
    assert {id(added_result), id(updated_result), id(removed_result)}.isdisjoint({id(before)})


def test_the_result_of_an_add_passes_the_contract_again() -> None:
    """AC-6. expected_behavior_source: the interface decision (an add refuses "a result that fails
    the `Resources` contract", so what it returns passes it) and ADR-002 decision 7 (the result is
    serialised and written as the registry)."""
    result = assert_accepted(added(rich_registry(), id="delta"))

    again = Resources.model_validate(result.model_dump(by_alias=True))

    assert again == result


def test_the_same_add_gives_the_same_registry() -> None:
    """AC-6. expected_behavior_source: ORQLET-DET-001 (deterministic output) and the interface
    decision (the builders are pure: no clock, no I/O)."""
    assert added(rich_registry(), id="delta") == added(rich_registry(), id="delta")


# --- resources_with: an add that is refused -------------------------------------------------------


def test_an_add_of_an_id_that_is_already_there_is_refused() -> None:
    """AC-6. expected_behavior_source: AC-6 ("refuse a repeated id"), the interface decision
    ("refuses ... a repeated id") and plan P-3 AC-1 (ORQ-E509)."""
    assert_refused(added(rich_registry(), id="beta"))


@pytest.mark.parametrize("missing", REQUIRED_FOR_AN_ADD)
def test_an_add_without_a_required_field_is_refused(missing: str) -> None:
    """AC-6. expected_behavior_source: the interface decision ("it needs every one of url, title,
    kind, note and access, refuses ... a missing required field") and ADR-002 decision 1 (every
    link says why: the note is required)."""
    assert_refused(added(registry(), **{missing: None}))


def test_an_add_that_gives_only_the_id_is_refused() -> None:
    """AC-6. expected_behavior_source: the interface decision (an add needs url, title, kind,
    note and access)."""
    assert_refused(resources_with(registry(), ResourceSpec(id="alpha"), replace=False))


BROKEN_ADDS: dict[str, dict[str, Any]] = {
    "id-with-capitals": {"id": "Alpha"},
    "id-with-a-double-hyphen": {"id": "my--docs"},
    "id-of-33-characters": {"id": "a" * 33},
    "id-that-is-a-windows-device-name": {"id": "con"},
    "address-that-is-not-https": {"url": "http://docs.example.com/alpha"},
    "address-with-a-fragment": {"url": "https://docs.example.com/alpha#intro"},
    "title-of-two-lines": {"title": "two\nlines"},
    "title-above-80-characters": {"title": "t" * 81},
    "note-with-a-backtick": {"note": "run `make` first"},
    "note-with-a-link": {"note": "see https://docs.example.com/other"},
    "note-above-200-characters": {"note": "n" * 201},
    "kind-outside-the-list": {"kind": "wiki"},
    "access-outside-the-list": {"access": "private"},
    "glob-that-is-absolute": {"paths": ("/abs/*.py",)},
    "glob-that-negates": {"paths": ("!src/**",)},
    "glob-that-climbs-out": {"paths": ("src/../*.py",)},
    "nine-globs": {"paths": tuple(f"src/p{number}/*.py" for number in range(9))},
    "tool-on-an-entry-that-is-not-tool-docs": {"kind": "team-docs", "tool": "FastAPI"},
    "tool-with-a-space": {"kind": "tool-docs", "tool": "fast api"},
    "version-with-a-space": {"kind": "tool-docs", "tool": "FastAPI", "version": "0 115"},
    "public-entry-on-an-internal-host": {"url": "https://wiki.example.internal/x"},
}


@pytest.mark.parametrize("name", list(BROKEN_ADDS), ids=list(BROKEN_ADDS))
def test_an_add_whose_result_fails_the_contract_is_refused(name: str) -> None:
    """AC-6. expected_behavior_source: the interface decision ("refuses ... a result that fails
    the `Resources` contract") and AC-1 of phase P-2 (the rules of the contract: ADR-002
    decisions 1 and 9)."""
    assert_refused(added(registry(), **BROKEN_ADDS[name]))


def test_the_hundred_and_first_entry_is_refused_and_the_hundredth_is_not() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 1 (the contract holds at most 100
    entries) and the interface decision (an add refuses a result that fails the contract)."""
    ninety_nine = registry(*numbered(99))
    hundred = registry(*numbered(100))

    accepted = assert_accepted(added(ninety_nine, id="z-last", url="https://docs.example.com/z"))
    assert len(accepted.resources) == 100
    assert_refused(added(hundred, id="z-last", url="https://docs.example.com/z"))


# --- resources_with: updating ---------------------------------------------------------------------


def test_an_update_changes_the_fields_that_are_given_and_keeps_every_other() -> None:
    """AC-6. expected_behavior_source: AC-6 and the plan file operation for this test ("updates
    with replace and keeps the fields that the spec leaves unset"), and the interface decision
    ("`replace=True` updates: ... changes only the fields that are given")."""
    before = rich_registry()

    result = assert_accepted(updated(before, id="alpha", note="A new note for the entry."))

    changed, original = item(result, "alpha"), item(before, "alpha")
    assert changed.note == "A new note for the entry."
    assert changed.model_copy(update={"note": original.note}) == original


NEW_VALUES: dict[str, Any] = {
    "url": "https://docs.example.com/new-address",
    "title": "A new title",
    "note": "A new note for the entry.",
    "paths": ("lib/**/*.py",),
    "tool": "Starlette",
    "version": "1.2",
}
FIELD_COMBINATIONS = [
    combination
    for size in (1, 2, 3)
    for combination in itertools.combinations(sorted(NEW_VALUES), size)
]


@pytest.mark.parametrize("given_fields", FIELD_COMBINATIONS, ids="+".join)
def test_an_update_of_any_set_of_fields_changes_exactly_those_fields(
    given_fields: tuple[str, ...],
) -> None:
    """AC-6. expected_behavior_source: the interface decision ("`replace=True` ... changes only
    the fields that are given, keeps the stored copy record") and ADR-002 decision 7 (an update
    of the address keeps the record of the copy)."""
    before = rich_registry()
    old = item(before, "alpha")

    result = assert_accepted(
        updated(before, id="alpha", **{name: NEW_VALUES[name] for name in given_fields})
    )

    new = item(result, "alpha")
    assert new.stored_copy == old.stored_copy
    assert (new.kind, new.access, new.id) == (old.kind, old.access, old.id)
    for name in ("url", "title", "note", "tool", "version"):
        assert getattr(new, name) == (
            NEW_VALUES[name] if name in given_fields else getattr(old, name)
        )
    assert new.applies_to is not None
    assert old.applies_to is not None
    expected_paths = NEW_VALUES["paths"] if "paths" in given_fields else old.applies_to.paths
    assert new.applies_to.paths == expected_paths


def test_an_update_leaves_the_other_entries_and_their_order_as_they_were() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 (an edit changes one entry; an id
    cannot change) and AC-6 (order of id is kept)."""
    before = rich_registry()

    result = assert_accepted(updated(before, id="beta", title="Another title"))

    assert ids_of(result) == ["alpha", "beta", "gamma"]
    assert item(result, "alpha") == item(before, "alpha")
    assert item(result, "gamma") == item(before, "gamma")
    assert item(result, "beta").title == "Another title"


def test_an_update_of_the_address_keeps_the_stored_copy_record() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 ("`update` of the address of an entry
    that has a stored copy keeps the record") and the interface decision ("keeps the stored copy
    record")."""
    before = rich_registry()
    record = item(before, "alpha").stored_copy
    assert record is not None

    result = assert_accepted(updated(before, id="alpha", url="https://docs.example.com/moved"))

    assert item(result, "alpha").url == "https://docs.example.com/moved"
    assert item(result, "alpha").stored_copy == record


def test_an_update_can_turn_a_team_docs_entry_into_tool_docs_with_a_tool() -> None:
    """AC-6. expected_behavior_source: the interface decision (an update changes the fields that
    are given: kind and tool) and ADR-002 decision 1 (a tool is for `tool-docs` entries)."""
    result = assert_accepted(updated(rich_registry(), id="beta", kind="tool-docs", tool="Celery"))

    assert (item(result, "beta").kind, item(result, "beta").tool) == ("tool-docs", "Celery")
    assert result.covered_tools() == ("FastAPI", "Celery")


def test_an_update_of_an_id_that_is_not_there_is_refused() -> None:
    """AC-6. expected_behavior_source: AC-6 ("refuse ... an id change"), ADR-002 decision 7 ("An
    id cannot change (remove the entry and add another)") and the interface decision
    ("`replace=True` ... needs the id to exist ... refuses an unknown id"). The spec has no field
    for a new id, so the only way to ask for a change of id is a spec with an id that is not
    there."""
    assert_refused(updated(rich_registry(), id="delta", note="A new note."))
    assert_refused(updated(registry(), id="alpha", note="A new note."))


def test_an_update_never_creates_and_an_add_never_replaces() -> None:
    """AC-6. expected_behavior_source: the interface decision (`replace=False` adds and refuses
    a repeated id; `replace=True` needs the id to exist)."""
    before = rich_registry()

    assert_refused(resources_with(before, spec(id="beta", title="Replaced"), replace=False))
    assert_refused(resources_with(before, spec(id="delta"), replace=True))


UPDATES_THAT_BREAK_THE_CONTRACT: dict[str, dict[str, Any]] = {
    "address-that-is-not-https": {"id": "beta", "url": "http://docs.example.com/beta"},
    "note-with-a-backtick": {"id": "beta", "note": "run `make` first"},
    "title-of-two-lines": {"id": "beta", "title": "two\nlines"},
    "kind-that-drops-the-tool-docs-of-an-entry-with-a-tool": {"id": "alpha", "kind": "team-docs"},
    "tool-on-a-team-docs-entry": {"id": "beta", "tool": "FastAPI"},
    "login-for-an-entry-whose-copy-is-a-full-copy": {"id": "alpha", "access": "login"},
    "an-internal-host-for-a-public-entry": {"id": "beta", "url": "https://wiki.corp/beta"},
    "ten-globs": {"id": "alpha", "paths": tuple(f"src/p{n}/*.py" for n in range(10))},
    "glob-that-matches-everything": {"id": "alpha", "paths": ("**/*",)},
}


@pytest.mark.parametrize(
    "name", list(UPDATES_THAT_BREAK_THE_CONTRACT), ids=list(UPDATES_THAT_BREAK_THE_CONTRACT)
)
def test_an_update_whose_result_fails_the_contract_is_refused(name: str) -> None:
    """AC-6. expected_behavior_source: the interface decision (both modes refuse "a result that
    fails the `Resources` contract") and ADR-002 decision 1 (the cross-field rules: a tool only
    for tool-docs, a login entry stores only a summary, a public entry has no internal host)."""
    assert_refused(updated(rich_registry(), **UPDATES_THAT_BREAK_THE_CONTRACT[name]))


def test_an_update_to_login_is_accepted_for_an_entry_whose_copy_is_a_summary() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 1 (a `login` entry may hold a summary)
    and the interface decision (an update is refused only when the result fails the contract)."""
    before = registry(entry(id="alpha", stored_copy=stored_copy(form="summary")))

    result = assert_accepted(updated(before, id="alpha", access="login"))

    assert item(result, "alpha").access == "login"


# --- resources_without ----------------------------------------------------------------------------


def test_removing_an_entry_keeps_the_others_in_order() -> None:
    """AC-6. expected_behavior_source: AC-6 ("The pure builders keep order of id"), the plan file
    operation for this test ("`resources_without` removes") and the interface decision
    ("`resources_without` removes an entry")."""
    before = rich_registry()

    result = assert_accepted(resources_without(before, "beta"))

    assert ids_of(result) == ["alpha", "gamma"]
    assert item(result, "alpha") == item(before, "alpha")
    assert item(result, "gamma") == item(before, "gamma")


def test_removing_the_last_entry_gives_the_empty_registry() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 6 (an empty valid registry is `resources:
    []`, which is what `remove` leaves) and the interface decision."""
    result = assert_accepted(resources_without(registry(entry()), "alpha"))

    assert result.resources == ()
    assert result == registry()


def test_removing_an_entry_removes_its_stored_copy_record_with_it() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 ("`remove` deletes the entry"; the
    copy file is the team's and is not touched, and a builder has no file system)."""
    result = assert_accepted(resources_without(rich_registry(), "alpha"))

    assert "alpha" not in ids_of(result)
    assert result.covered_tools() == ()


def test_removing_an_id_that_is_not_there_is_refused() -> None:
    """AC-6. expected_behavior_source: the interface decision ("`resources_without` ... refuses
    an unknown id") and plan P-3 AC-1 (ORQ-E509)."""
    assert_refused(resources_without(rich_registry(), "delta"))
    assert_refused(resources_without(registry(), "alpha"))


def test_removing_after_adding_gives_back_the_registry_that_was_there() -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 (`add` and `remove` call the same pure
    builders and a remove undoes an add; an id cannot change)."""
    before = rich_registry()

    grown = assert_accepted(added(before, id="delta", url="https://docs.example.com/delta"))

    assert assert_accepted(resources_without(grown, "delta")) == before


# --- AC-2 of phase P-2 carried over: no finding holds a part of the input -------------------------

LEAKY_ADDS: dict[str, tuple[dict[str, Any], tuple[str, ...]]] = {
    "address": ({"url": f"https://docs.example.com/guide?token={TOKEN}"}, (TOKEN,)),
    "address-with-user-information": (
        {"url": f"https://deploy:{PASSWORD}@docs.example.com/guide"},
        (PASSWORD,),
    ),
    "address-with-an-opaque-segment": ({"url": f"https://docs.example.com/{OPAQUE}"}, (OPAQUE,)),
    "note": ({"note": f"use `{TOKEN}` first"}, (TOKEN,)),
    "note-with-a-link": ({"note": f"see https://{ACCESS_KEY}.example.com/x"}, (ACCESS_KEY,)),
    "title": ({"title": f"[{TOKEN}](x)"}, (TOKEN,)),
    "glob": ({"paths": (f"!{TOKEN}",)}, (TOKEN,)),
    "glob-climbing-out": ({"paths": (f"{ACCESS_KEY}/../x",)}, (ACCESS_KEY,)),
    "id": ({"id": TOKEN}, (TOKEN,)),
    "tool": ({"kind": "tool-docs", "tool": f"{TOKEN}#"}, (TOKEN,)),
    "version": ({"kind": "tool-docs", "tool": "demo", "version": f"{TOKEN}#"}, (TOKEN,)),
    "tool-on-the-wrong-kind": ({"tool": TOKEN}, (TOKEN,)),
    "several-fields-at-once": (
        {
            "id": ACCESS_KEY,
            "title": f"[{PASSWORD}](x)",
            "url": f"https://docs.example.com/guide?token={TOKEN}",
            "note": f"see `{OPAQUE}`",
            "paths": (f"!{TOKEN}",),
        },
        (TOKEN, ACCESS_KEY, PASSWORD, OPAQUE),
    ),
}


@pytest.mark.parametrize("name", list(LEAKY_ADDS), ids=list(LEAKY_ADDS))
def test_no_finding_of_a_refused_add_shows_a_part_of_the_input(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-6. expected_behavior_source: the interface decision ("a finding ORQ-E509 that holds no
    part of the input"), ORQLET-SEC-003 and ADR-002 decision 10."""
    changes, secrets = LEAKY_ADDS[name]

    findings = assert_refused(added(registry(), **changes))
    streams = capsys.readouterr()

    for secret in secrets:
        assert not leaks(shown(findings), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


@pytest.mark.parametrize("name", list(LEAKY_ADDS), ids=list(LEAKY_ADDS))
def test_no_finding_of_a_refused_update_shows_a_part_of_the_input(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-6. expected_behavior_source: the interface decision (the same refusal for
    `replace=True`), ORQLET-SEC-003 and ADR-002 decision 10. The id of the update is the one of
    `beta`, a team-docs entry that exists, unless the case puts a secret in the id itself."""
    changes, secrets = LEAKY_ADDS[name]
    resource_id = changes.get("id", "beta")
    given = {key: value for key, value in changes.items() if key != "id"}

    findings = assert_refused(updated(rich_registry(), id=resource_id, **given))
    streams = capsys.readouterr()

    for secret in secrets:
        assert not leaks(shown(findings), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


def test_a_repeated_id_is_refused_without_showing_it() -> None:
    """AC-6. expected_behavior_source: the interface decision (the finding for a repeated id "holds
    no part of the input") and ORQLET-SEC-003. The id is valid, so the test is for the refusal of a
    repeat and not of a bad shape."""
    taken = OPAQUE.lower()
    before = registry(entry(id=taken))

    findings = assert_refused(added(before, id=taken))

    assert not leaks(shown(findings), taken)


def test_an_unknown_id_is_refused_without_showing_it() -> None:
    """AC-6. expected_behavior_source: the interface decision (a refusal "holds no part of the
    input"), ORQLET-SEC-003 and ADR-002 decision 10."""
    unknown = OPAQUE.lower()

    update_findings = assert_refused(updated(rich_registry(), id=unknown, note="A new note."))
    remove_findings = assert_refused(resources_without(rich_registry(), unknown))
    shape_findings = assert_refused(resources_without(rich_registry(), TOKEN))

    assert not leaks(shown(update_findings), unknown)
    assert not leaks(shown(remove_findings), unknown)
    assert not leaks(shown(shape_findings), TOKEN)


# --- properties -----------------------------------------------------------------------------------

_IDS = st.from_regex(r"[a-z][a-z0-9]{0,8}(-[a-z0-9]{1,5}){0,2}", fullmatch=True).filter(
    lambda value: not resource_id_problems(value)
)
_ORDERED_IDS = st.lists(_IDS, unique=True, min_size=1, max_size=8).flatmap(st.permutations)


def _add_all(ids: list[str]) -> Resources:
    resources = registry()
    for resource_id in ids:
        resources = assert_accepted(
            added(resources, id=resource_id, url=f"https://docs.example.com/{resource_id}")
        )
    return resources


@given(_ORDERED_IDS)
def test_whatever_the_order_of_the_adds_the_registry_is_in_order_of_id(ids: list[str]) -> None:
    """AC-6. expected_behavior_source: AC-6 ("The pure builders keep order of id"), ADR-002
    decision 1 ("written in order of id") and the interface decision."""
    resources = _add_all(ids)

    assert ids_of(resources) == sorted(ids)
    assert Resources.model_validate(resources.model_dump(by_alias=True)) == resources


@given(_ORDERED_IDS, st.data())
def test_a_remove_and_an_add_of_the_same_entry_give_back_the_registry(
    ids: list[str], data: st.DataObject
) -> None:
    """AC-6. expected_behavior_source: ADR-002 decision 7 (the two builders are the pair that
    `add` and `remove` share) and AC-6 ("keep order of id")."""
    resources = _add_all(ids)
    target = data.draw(st.sampled_from(ids))

    smaller = assert_accepted(resources_without(resources, target))
    restored = assert_accepted(added(smaller, id=target, url=f"https://docs.example.com/{target}"))

    assert ids_of(smaller) == sorted(set(ids) - {target})
    assert restored == resources


@given(_ORDERED_IDS)
def test_adding_an_id_twice_is_always_refused_and_leaves_the_registry_unchanged(
    ids: list[str],
) -> None:
    """AC-6. expected_behavior_source: AC-6 ("refuse a repeated id") and the interface decision."""
    resources = _add_all(ids)
    snapshot = resources.model_dump(by_alias=True)

    for resource_id in ids:
        assert_refused(added(resources, id=resource_id))

    assert resources.model_dump(by_alias=True) == snapshot
