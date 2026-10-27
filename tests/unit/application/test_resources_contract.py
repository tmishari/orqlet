"""The `orqlet.resources/v1` contract (task team-conventions-resources, phase P-2).

Every test cites its `expected_behavior_source`. ADR-002 is the file `adr-002-*.md` under
docs/design/team-conventions-resources/design/, EC-n are the expected changes of the manifest.yaml
next to it, and AC-1 to AC-6 are the acceptance criteria of phase P-2 in
docs/design/team-conventions-resources/plan.yaml.

These tests were written first, by the Tester of phase P-2, before the contract existed. They cover
AC-1 (every rule of the contract, with a failing and a passing case) and AC-2 (no message holds a
part of an input value); the committed schema and the round trip of the fixture are checked by
tests/contract/test_contracts.py, which loads the fixture of every contract in CONTRACTS.

Credential-shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003); every address uses example.com.

Behaviour that the design leaves open is deliberately not pinned here:
- the wording of any message (only that an error exists, that it is not empty and that it shows no
  part of the input are checked);
- whether a missing top-level `resources` key, an `applies_to` without `paths`, an empty list of
  paths, repeated globs or an empty `version` are accepted;
- whether `version` needs a `tool`, or may sit on an entry that is not `tool-docs`;
- the type that an absent `applies_to` takes (None or an empty `AppliesTo`): only "no paths" is
  checked;
- the order, the repetition and the letter case of what `covered_tools` returns;
- the collation of ids that mix hyphens, digits and letters (the ordering tests use ids for which
  every reasonable collation agrees);
- whether a note or title that looks like a credential but passes `text_problems` is refused;
- whether an unknown field NAME (a key of the document, which pydantic puts in the error location)
  may appear in a message.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts import CONTRACTS
from orqlet.application.contracts.common import Contract
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.resources import AppliesTo, Resource, Resources, StoredCopy
from orqlet.application.ports.documents import DocumentError
from orqlet.domain.resources import (
    credential_problems,
    glob_problems,
    host_of,
    resource_id_problems,
    text_problems,
    uncovered_names,
    url_problems,
)

pytestmark = pytest.mark.unit

SCHEMA = "orqlet.resources/v1"
HASH = "a" * 64
STAMP = "2026-10-27T10:30:00Z"
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.resources.v1.yaml"
)
LOADER = StrictYamlLoader()
TOOL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,39}")  # ADR-002 decision 1
VERSION_TEXT = re.compile(r"[A-Za-z0-9._+-]{1,40}")  # ADR-002 decision 1: "the same characters"


# --- helpers --------------------------------------------------------------------------------------


def parametrized(name: str, cases: Mapping[str, object]) -> pytest.MarkDecorator:
    """`pytest.mark.parametrize` over the values of a mapping, with its keys as test ids."""
    return pytest.mark.parametrize(name, list(cases.values()), ids=list(cases))


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
    """A valid stored copy of form `copy`. A change whose value is None removes that field."""
    base: dict[str, Any] = {"form": "copy", "sha256": HASH, "retrieved_at": STAMP, "ttl_days": 30}
    merged = {**base, **changes}
    return {key: value for key, value in merged.items() if value is not None}


def registry(*entries: Mapping[str, Any]) -> dict[str, Any]:
    return {"schema": SCHEMA, "resources": [dict(item) for item in entries]}


def load(*entries: Mapping[str, Any]) -> Resources:
    return Resources.model_validate(registry(*entries))


def refusal(data: Mapping[str, Any]) -> ValidationError:
    with pytest.raises(ValidationError) as caught:
        Resources.model_validate(data)
    return caught.value


def ids_of(loaded: Resources) -> list[str]:
    return [item.id for item in loaded.resources]


def paths_of(item: Resource) -> list[str]:
    return [] if item.applies_to is None else list(item.applies_to.paths)


def numbered(count: int) -> list[dict[str, Any]]:
    """`count` valid entries whose ids are in increasing order."""
    return [
        entry(id=f"r{number:03d}", url=f"https://docs.example.com/r{number:03d}")
        for number in range(count)
    ]


def leaks(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it (any letter case).

    A window of 8 characters of a random-looking secret cannot appear in a fixed message by chance.
    """
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def error_texts(error: ValidationError) -> str:
    """Everything that an error says without the input: type, message, location and context."""
    lines: list[str] = []
    for item in error.errors(include_input=False, include_url=False):
        lines.append(str(item["type"]))
        lines.append(str(item["msg"]))
        lines.append(".".join(str(part) for part in item["loc"]))
        lines.append(str(item.get("ctx", "")))
    return "\n".join(lines)


# --- credential-shaped values, assembled at run time (ORQLET-SEC-003) -----------------------------

TOKEN = "".join(("gh", "p_", "Zq7Xv3Lm9Tk2", "Rb8Wc4Yd6Hn1", "Pf5Gs0Jx"))
ACCESS_KEY = "".join(("AK", "IA", "QZ7XV3LM", "9TK2RB8W"))
PASSWORD = "".join(("hunter", "2Qx", "9Lp", "Vw4"))
OPAQUE = "".join(("Zq7", "Xv3", "Lm9", "Tk2", "Rb8", "Wc4", "Yd6", "Hn1", "Pf5", "Gs0", "Jx"))
OPAQUE_ID = OPAQUE.lower()  # a valid id of 32 characters that reads like a secret

# case name -> (document, the secrets that no message may show)
SECRET_CASES: dict[str, tuple[dict[str, Any], tuple[str, ...]]] = {
    "address-query-token": (
        registry(entry(url=f"https://docs.example.com/guide?token={TOKEN}")),
        (TOKEN,),
    ),
    "address-user-information": (
        registry(entry(url=f"https://deploy:{PASSWORD}@docs.example.com/guide")),
        (PASSWORD,),
    ),
    "address-opaque-path-segment": (
        registry(entry(url=f"https://docs.example.com/{OPAQUE}")),
        (OPAQUE,),
    ),
    "address-not-https": (
        registry(entry(url=f"http://docs.example.com/{TOKEN}")),
        (TOKEN,),
    ),
    "address-of-a-public-entry-on-an-internal-host": (
        registry(entry(url=f"https://wiki.example.internal/{PASSWORD}")),
        (PASSWORD,),
    ),
    "note-in-backticks": (registry(entry(note=f"use `{TOKEN}` first")), (TOKEN,)),
    "note-with-a-link": (
        registry(entry(note=f"see https://{ACCESS_KEY}.example.com/x")),
        (ACCESS_KEY,),
    ),
    "note-too-long": (registry(entry(note=TOKEN * 8)), (TOKEN,)),
    "title-with-markup": (registry(entry(title=f"[{TOKEN}](x)")), (TOKEN,)),
    "glob-negated": (registry(entry(applies_to={"paths": [f"!{TOKEN}"]})), (TOKEN,)),
    "glob-climbing-out": (
        registry(entry(applies_to={"paths": [f"{ACCESS_KEY}/../x"]})),
        (ACCESS_KEY,),
    ),
    "glob-with-braces": (
        registry(entry(applies_to={"paths": ["{" + OPAQUE + "}"]})),
        (OPAQUE,),
    ),
    "glob-among-valid-ones": (
        registry(entry(applies_to={"paths": ["src/**/*.py", f"/{TOKEN}"]})),
        (TOKEN,),
    ),
    "id-shape": (registry(entry(id=TOKEN)), (TOKEN,)),
    "id-repeated": (registry(entry(id=OPAQUE_ID), entry(id=OPAQUE_ID)), (OPAQUE_ID,)),
    "ids-out-of-order": (registry(entry(id=OPAQUE_ID), entry(id="aaa")), (OPAQUE_ID,)),
    "tool-pattern": (
        registry(entry(kind="tool-docs", tool=f"{TOKEN}/x")),
        (TOKEN,),
    ),
    "tool-on-an-entry-that-is-not-tool-docs": (registry(entry(tool=TOKEN)), (TOKEN,)),
    "version-pattern": (
        registry(entry(kind="tool-docs", tool="demo", version=f"{TOKEN}#")),
        (TOKEN,),
    ),
    "kind": (registry(entry(kind=TOKEN)), (TOKEN,)),
    "access": (registry(entry(access=TOKEN)), (TOKEN,)),
    "copy-form": (registry(entry(stored_copy=copy_of(form=TOKEN))), (TOKEN,)),
    "copy-sha256": (registry(entry(stored_copy=copy_of(sha256=TOKEN))), (TOKEN,)),
    "copy-retrieved-at": (registry(entry(stored_copy=copy_of(retrieved_at=TOKEN))), (TOKEN,)),
    "copy-ttl-days": (registry(entry(stored_copy=copy_of(ttl_days=TOKEN))), (TOKEN,)),
    "copy-field-that-the-contract-does-not-have": (
        registry(entry(stored_copy={**copy_of(), "path": TOKEN})),
        (TOKEN,),
    ),
    "copy-form-of-a-login-entry-with-a-secret-looking-id": (
        registry(entry(id=OPAQUE_ID, access="login", stored_copy=copy_of(form="copy"))),
        (OPAQUE_ID,),
    ),
    "several-fields-at-once": (
        registry(
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


# --- the classes and the fixture ------------------------------------------------------------------


@pytest.mark.parametrize("model", [Resources, Resource, AppliesTo, StoredCopy])
def test_each_class_of_the_contract_is_a_closed_contract(model: type[Contract]) -> None:
    """AC-1. expected_behavior_source: EC-17, EC-19, EC-20, EC-21 (`class X(Contract)`) and EC-59
    (a new closed contract)."""
    assert issubclass(model, Contract)
    assert model.model_config.get("extra") == "forbid"


def test_the_contract_is_registered_under_its_schema_id() -> None:
    """AC-4. expected_behavior_source: plan P-2 file operation on contracts/__init__.py
    (register orqlet.resources/v1 in CONTRACTS so that the schema export and the fixture tests
    cover it) and ORQLET-DET-003."""
    assert CONTRACTS[SCHEMA] is Resources


def test_the_fixture_is_a_registry_with_the_two_entries_the_plan_describes() -> None:
    """AC-1. expected_behavior_source: plan P-2 file operation on the fixture (a public tool-docs
    entry with applies_to paths and a stored copy of form copy, and a login team-docs entry whose
    copy is a summary), ADR-002 decision 1 (entries in order of id)."""
    loaded = load_contract(LOADER, Resources, FIXTURE.read_bytes(), source="fixture")

    assert len(loaded.resources) == 2
    public, login = loaded.resources
    assert (public.kind, public.access) == ("tool-docs", "public")
    assert public.tool is not None
    assert paths_of(public)
    assert public.stored_copy is not None
    assert public.stored_copy.form == "copy"
    assert (login.kind, login.access) == ("team-docs", "login")
    assert login.stored_copy is not None
    assert login.stored_copy.form == "summary"
    assert ids_of(loaded) == sorted(ids_of(loaded))


def test_the_fixture_holds_only_fake_addresses_and_placeholder_hashes() -> None:
    """AC-1. expected_behavior_source: ORQLET-SEC-003 (never commit secrets, including in tests
    and fixtures; use obvious placeholders)."""
    loaded = load_contract(LOADER, Resources, FIXTURE.read_bytes(), source="fixture")

    assert credential_problems(FIXTURE.read_text(encoding="utf-8")) == ()
    for item in loaded.resources:
        host = host_of(item.url)
        assert host == "example.com" or host.endswith(".example.com")
        if item.stored_copy is not None:
            assert len(set(item.stored_copy.sha256)) == 1  # one repeated digit: a placeholder


# --- what loads -----------------------------------------------------------------------------------


def test_an_empty_registry_loads_and_covers_no_tool() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 6 (an empty valid registry is
    `schema: orqlet.resources/v1` and `resources: []`) and decision 1 (at most 100 entries)."""
    loaded = Resources.model_validate({"schema": SCHEMA, "resources": []})

    assert len(loaded.resources) == 0
    assert loaded.covered_tools() == ()


def test_a_registry_with_every_optional_field_loads_and_round_trips() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (the fields of an entry and of the
    stored copy) and EC-59."""
    full = entry(
        id="fastapi-docs",
        kind="tool-docs",
        tool="FastAPI",
        version="0.115.2",
        access="public",
        applies_to={"paths": ["src/api/**/*.py", "tests/api/**/*.py"]},
        stored_copy=copy_of(ttl_days=90),
    )

    loaded = load(full)
    dumped = loaded.model_dump(mode="json", by_alias=True)

    (item,) = loaded.resources
    assert item.tool == "FastAPI"
    assert item.version == "0.115.2"
    assert paths_of(item) == ["src/api/**/*.py", "tests/api/**/*.py"]
    assert item.stored_copy is not None
    assert (item.stored_copy.form, item.stored_copy.sha256) == ("copy", HASH)
    assert item.stored_copy.ttl_days == 90
    assert dumped["schema"] == SCHEMA
    assert Resources.model_validate(dumped) == loaded


def test_an_entry_with_only_the_required_fields_leaves_every_optional_field_unset() -> None:
    """AC-1. expected_behavior_source: plan P-2 file operation on test_resources_contract.py ("the
    default of every optional field") and ADR-002 decision 1 (applies_to, tool, version and
    stored_copy are optional)."""
    (item,) = load(entry()).resources

    assert paths_of(item) == []
    assert item.tool is None
    assert item.version is None
    assert item.stored_copy is None


@pytest.mark.parametrize("kind", ["api-guidelines", "tool-docs", "team-docs", "other"])
def test_every_kind_of_the_closed_list_loads(kind: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (kind: api-guidelines, tool-docs,
    team-docs or other)."""
    (item,) = load(entry(kind=kind)).resources

    assert item.kind == kind


@pytest.mark.parametrize("access", ["public", "login"])
def test_both_access_classes_load(access: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (access: public or login)."""
    (item,) = load(entry(access=access)).resources

    assert item.access == access


def test_a_tool_docs_entry_may_name_no_tool() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`tool` is optional and allowed only
    when the kind is tool-docs)."""
    (item,) = load(entry(kind="tool-docs")).resources

    assert item.tool is None


# --- covered_tools --------------------------------------------------------------------------------


def test_covered_tools_names_the_tool_of_every_entry_that_has_one() -> None:
    """AC-1. expected_behavior_source: EC-18 (`covered_tools(self) -> tuple[str, ...]`) and
    ADR-002 decision 7 (`--uncovered` lists the technologies that no entry names as its `tool`;
    names are compared without the version). Order, repetition and letter case are not pinned."""
    loaded = load(
        entry(id="a-guide", kind="tool-docs", tool="FastAPI", version="0.115"),
        entry(id="b-guide", kind="tool-docs", tool="pytest"),
        entry(id="c-guide", kind="team-docs"),
        entry(id="d-guide", kind="tool-docs"),
    )

    covered = loaded.covered_tools()

    assert isinstance(covered, tuple)
    assert sorted(name.casefold() for name in covered) == ["fastapi", "pytest"]


def test_the_covered_tools_feed_the_uncovered_technologies_of_the_profile() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 7 (`resources list --uncovered` prints
    the technologies of the profile that no entry names as its `tool`, compared after trimming and
    case folding, without the version) with the domain function `uncovered_names`."""
    loaded = load(entry(kind="tool-docs", tool="FastAPI", version="0.115"))

    assert uncovered_names([" fastapi", "Django"], loaded.covered_tools()) == ("Django",)


# --- a closed contract ----------------------------------------------------------------------------


@parametrized(
    "data",
    {
        "top-level": {**registry(entry()), "surprise": 1},
        "entry": registry(entry(surprise=1)),
        "applies-to": registry(entry(applies_to={"paths": ["src/*.py"], "surprise": 1})),
        "stored-copy": registry(entry(stored_copy={**copy_of(), "surprise": 1})),
        "a-requirement-level": registry(entry(level="MUST")),
        "a-data-class": registry(entry(data_class="internal")),
        "a-stored-path": registry(entry(stored_copy={**copy_of(), "path": "docs/resources/x.md"})),
    },
)
def test_an_unknown_field_is_refused_wherever_it_sits(data: dict[str, Any]) -> None:
    """AC-1. expected_behavior_source: EC-59 and ADR-002 decision 1 ("the contract is closed (an
    unknown field is refused)"; no `level` field, no data-class field, and the copy path "is not
    stored: it is always docs/resources/<id>.md")."""
    refusal(data)


@parametrized(
    "schema",
    {
        "another-version": "orqlet.resources/v2",
        "another-contract": "orqlet.knowledge/v2",
        "empty": "",
    },
)
def test_a_registry_that_names_another_schema_is_refused(schema: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (top level `schema:
    orqlet.resources/v1`)."""
    refusal({"schema": schema, "resources": []})


def test_a_registry_without_a_schema_is_refused() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (top level `schema:
    orqlet.resources/v1`)."""
    refusal({"resources": []})


@pytest.mark.parametrize("field", ["id", "title", "kind", "url", "note", "access"])
def test_an_entry_without_a_required_field_is_refused(field: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (an entry has id, title, kind, url,
    note, access; the note is "required, so that every link says why and when to use it")."""
    refusal(registry(entry(**{field: None})))


@pytest.mark.parametrize("field", ["form", "sha256", "retrieved_at", "ttl_days"])
def test_a_stored_copy_without_a_field_is_refused(field: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (stored_copy holds form, sha256,
    retrieved_at and ttl_days; the time-to-live is "stated by the person", so it has no default)
    and AC-1 ("a stored_copy without ttl_days between 1 and 365")."""
    refusal(registry(entry(stored_copy=copy_of(**{field: None}))))


# --- the text rules call the domain rules ---------------------------------------------------------

GOOD_IDS = {
    "one-letter": "a",
    "one-word": "alpha",
    "words-joined-by-hyphens": "api-guidelines",
    "digits-after-the-first-letter": "a1-b2-c3",
    "thirty-two-characters": "x" * 32,
    "com-with-two-digits-is-not-a-device-name": "com10",
    "starts-like-a-device-name": "console",
}
BAD_IDS = {
    "empty": "",
    "upper-case": "Alpha",
    "starts-with-a-digit": "1a",
    "starts-with-a-hyphen": "-a",
    "ends-with-a-hyphen": "a-",
    "doubled-hyphen": "a--b",
    "underscore": "a_b",
    "space": "a b",
    "dot": "a.b",
    "trailing-line-feed": "alpha\n",
    "thirty-three-characters": "x" * 33,
    "device-con": "con",
    "device-prn": "prn",
    "device-aux": "aux",
    "device-nul": "nul",
    "device-com1": "com1",
    "device-com9": "com9",
    "device-lpt1": "lpt1",
    "device-lpt9": "lpt9",
    "accented-letter": "caf\u00e9",
    "cyrillic-look-alike": "\u0430lpha",
}


@parametrized("value", GOOD_IDS)
def test_an_id_that_passes_resource_id_problems_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (the id is checked by
    `resource_id_problems`)."""
    assert resource_id_problems(value) == ()

    (item,) = load(entry(id=value)).resources

    assert item.id == value


@parametrized("value", BAD_IDS)
def test_an_id_that_fails_resource_id_problems_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("an id that fails resource_id_problems") and
    ADR-002 decision 1."""
    assert resource_id_problems(value)

    refusal(registry(entry(id=value)))


GOOD_TEXTS = {
    "plain-words": "Alpha guide",
    "punctuation": "Rules (v2): read first, then ask.",
    "a-colon-and-a-slash": "Branches: feature/TICKET-slug",
}
BAD_TEXTS = {
    "empty": "",
    "blank": "   ",
    "two-lines": "first\nsecond",
    "tab": "a\tb",
    "carriage-return": "a\rb",
    "accented-letter": "Caf\u00e9",
    "emoji": "go \U0001f600",
    "null-byte": "a\x00b",
    "an-address": "see https://docs.example.com",
    "a-link": "[a](b)",
    "html-comment-open": "a <!-- b",
    "html-comment-close": "a --> b",
    "backtick": "run `make`",
    "angle-brackets": "<b>bold</b>",
}


@parametrized("value", GOOD_TEXTS)
def test_a_title_and_a_note_that_pass_text_problems_load(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`text_problems(value, 80)` for the
    title and `text_problems(value, 200)` for the note)."""
    assert text_problems(value, 80) == ()

    (item,) = load(entry(title=value, note=value)).resources

    assert (item.title, item.note) == (value, value)


@parametrized("value", BAD_TEXTS)
def test_a_title_that_fails_text_problems_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a note or title that fails text_problems") and
    ADR-002 decision 1 (`text_problems(value, 80)` for the title)."""
    assert text_problems(value, 80)

    refusal(registry(entry(title=value)))


@parametrized("value", BAD_TEXTS)
def test_a_note_that_fails_text_problems_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a note or title that fails text_problems") and
    ADR-002 decision 1 (`text_problems(value, 200)` for the note)."""
    assert text_problems(value, 200)

    refusal(registry(entry(note=value)))


def test_a_title_is_limited_to_80_characters_and_a_note_to_200() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`title`: one line, up to 80 characters;
    `note`: one line, up to 200)."""
    (accepted,) = load(entry(title="x" * 80, note="y" * 200)).resources

    assert (len(accepted.title), len(accepted.note)) == (80, 200)
    refusal(registry(entry(title="x" * 81)))
    refusal(registry(entry(note="y" * 201)))


def test_a_text_of_81_to_200_characters_is_a_note_and_not_a_title() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (the title and the note have different
    limits: 80 and 200)."""
    text = "z" * 150

    load(entry(note=text))
    refusal(registry(entry(title=text)))


GOOD_URLS = {
    "guides-address": "https://docs.example.com/guides/api",
    "confluence-style-query": "https://wiki.example.com/pages/viewpage.action?pageId=123456",
    "host-only": "https://example.com",
    "two-labels-and-a-path": "https://example.com/docs",
}
BAD_URLS = {
    "empty": "",
    "http": "http://docs.example.com/guides",
    "another-scheme": "ftp://docs.example.com/guides",
    "no-scheme": "docs.example.com/guides",
    "port": "https://docs.example.com:8443/guides",
    "user-information": "https://user@docs.example.com/guides",
    "localhost": "https://localhost/guides",
    "numeric-host": "https://127.0.0.1/guides",
    "fragment": "https://docs.example.com/guides#top",
    "space-in-the-path": "https://docs.example.com/a b",
    "credential-key-in-the-query": "https://docs.example.com/guides?token=abc",
    "template-reference": "https://docs.example.com/${HOME}",
    "longer-than-300-characters": "https://docs.example.com/" + "a/" * 150,
}


@parametrized("value", GOOD_URLS)
def test_an_address_that_passes_url_problems_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`url_problems` for the address) and
    decision 8 (the grammar)."""
    assert url_problems(value) == ()

    (item,) = load(entry(url=value)).resources

    assert item.url == value


@parametrized("value", BAD_URLS)
def test_an_address_that_fails_url_problems_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("an address that fails url_problems") and ADR-002
    decision 1."""
    assert url_problems(value)

    refusal(registry(entry(url=value)))


GOOD_GLOBS = {
    "recursive": "src/**/*.py",
    "one-level": "docs/*.md",
    "a-file-name": "Makefile",
    "everything-of-one-type": "**/*.tf",
    "one-hundred-and-twenty-characters": "a" * 120,
}
BAD_GLOBS = {
    "empty": "",
    "absolute": "/abs/*.py",
    "backslash": "src\\*.py",
    "climbs-out": "src/../x",
    "starts-by-climbing-out": "../*.py",
    "negation": "!src/*.py",
    "braces": "src/{a,b}.py",
    "matches-everything": "**",
    "matches-every-file": "*",
    "matches-every-file-of-one-level": "*/*",
    "one-hundred-and-twenty-one-characters": "a" * 121,
    "accented-letter": "src/caf\u00e9.py",
}


@parametrized("value", GOOD_GLOBS)
def test_a_glob_that_passes_glob_problems_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`applies_to.paths`: globs that pass
    `glob_problems`)."""
    assert glob_problems(value) == ()

    (item,) = load(entry(applies_to={"paths": [value]})).resources

    assert paths_of(item) == [value]


@parametrized("value", BAD_GLOBS)
def test_a_glob_that_fails_glob_problems_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a glob that fails glob_problems") and ADR-002
    decision 1."""
    assert glob_problems(value)

    refusal(registry(entry(applies_to={"paths": [value]})))


def test_a_bad_glob_among_good_ones_is_refused() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (every glob passes `glob_problems`)."""
    refusal(registry(entry(applies_to={"paths": ["src/**/*.py", "/abs/*.py", "docs/*.md"]})))


def test_up_to_eight_globs_load_and_nine_are_refused() -> None:
    """AC-1. expected_behavior_source: AC-1 ("more than 8 globs") and ADR-002 decision 1 (up to 8
    repository-relative globs)."""
    eight = [f"src/part{number}/**/*.py" for number in range(8)]

    (item,) = load(entry(applies_to={"paths": eight})).resources

    assert paths_of(item) == eight
    refusal(registry(entry(applies_to={"paths": [*eight, "src/part8/**/*.py"]})))


GOOD_TOOLS = {
    "mixed-case": "FastAPI",
    "with-a-dot": "node.js",
    "with-a-plus": "c++",
    "starts-with-a-digit": "1password",
    "one-character": "A",
    "with-a-hyphen": "gh-cli",
    "forty-characters": "x" * 40,
}
BAD_TOOLS = {
    "empty": "",
    "space-only": " ",
    "starts-with-a-hyphen": "-x",
    "starts-with-a-dot": ".x",
    "starts-with-an-underscore": "_x",
    "space-inside": "a b",
    "slash": "a/b",
    "hash": "a#b",
    "forty-one-characters": "x" * 41,
    "accented-letter": "caf\u00e9",
    "trailing-line-feed": "fastapi\n",
}


@parametrized("value", GOOD_TOOLS)
def test_a_tool_name_of_the_allowed_pattern_loads_on_a_tool_docs_entry(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`tool` matches
    `[A-Za-z0-9][A-Za-z0-9._+-]{0,39}`, only for kind tool-docs)."""
    assert TOOL_NAME.fullmatch(value)

    (item,) = load(entry(kind="tool-docs", tool=value)).resources

    assert item.tool == value


@parametrized("value", BAD_TOOLS)
def test_a_tool_name_outside_the_pattern_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`tool` matches
    `[A-Za-z0-9][A-Za-z0-9._+-]{0,39}`: "no space, slash or hash")."""
    assert TOOL_NAME.fullmatch(value) is None

    refusal(registry(entry(kind="tool-docs", tool=value)))


GOOD_VERSIONS = {
    "one-digit": "1",
    "dotted": "0.115.2",
    "with-a-prefix": "v2",
    "with-a-plus": "3.12+",
    "pre-release": "1.0-rc.1",
    "forty-characters": "x" * 40,
}
BAD_VERSIONS = {
    "forty-one-characters": "x" * 41,
    "space-inside": "1 2",
    "slash": "1/2",
    "hash": "1#2",
    "semicolon": "1;2",
    "accented-letter": "caf\u00e9",
    "trailing-line-feed": "1\n",
}


@parametrized("value", GOOD_VERSIONS)
def test_a_version_of_the_allowed_characters_loads(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`version`: optional, letters, digits
    and `._+-`, up to 40)."""
    assert VERSION_TEXT.fullmatch(value)

    (item,) = load(entry(kind="tool-docs", tool="demo", version=value)).resources

    assert item.version == value


@parametrized("value", BAD_VERSIONS)
def test_a_version_outside_the_allowed_characters_or_length_is_refused(value: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`version`: letters, digits and
    `._+-`, up to 40)."""
    assert VERSION_TEXT.fullmatch(value) is None

    refusal(registry(entry(kind="tool-docs", tool="demo", version=value)))


@parametrized(
    "kind",
    {"api-guidelines": "api-guidelines", "team-docs": "team-docs", "other": "other"},
)
def test_a_tool_on_an_entry_that_is_not_tool_docs_is_refused(kind: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a tool on an entry whose kind is not tool-docs")
    and ADR-002 decision 1 (`tool`: only for `kind: tool-docs`)."""
    refusal(registry(entry(kind=kind, tool="FastAPI")))


@parametrized("kind", {"blog": "blog", "capitalised": "Tool-Docs", "empty": ""})
def test_a_kind_outside_the_closed_list_is_refused(kind: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (kind: api-guidelines, tool-docs,
    team-docs or other)."""
    refusal(registry(entry(kind=kind)))


@parametrized("access", {"private": "private", "capitalised": "Public", "empty": ""})
def test_an_access_class_outside_the_closed_list_is_refused(access: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (access: public or login)."""
    refusal(registry(entry(access=access)))


# --- the stored copy ------------------------------------------------------------------------------


@pytest.mark.parametrize("form", ["copy", "summary"])
def test_both_forms_of_a_stored_copy_load_on_a_public_entry(form: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`form` is `copy` or `summary`)."""
    (item,) = load(entry(access="public", stored_copy=copy_of(form=form))).resources

    assert item.stored_copy is not None
    assert item.stored_copy.form == form


@pytest.mark.parametrize("form", ["link", "Copy", "full", ""])
def test_a_form_outside_copy_and_summary_is_refused(form: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`form` is `copy` or `summary`)."""
    refusal(registry(entry(stored_copy=copy_of(form=form))))


@pytest.mark.parametrize("ttl_days", [1, 30, 365])
def test_a_time_to_live_from_1_to_365_days_loads(ttl_days: int) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a stored_copy without ttl_days between 1 and 365")
    and ADR-002 decision 1 (`ttl_days` 1 to 365)."""
    (item,) = load(entry(stored_copy=copy_of(ttl_days=ttl_days))).resources

    assert item.stored_copy is not None
    assert item.stored_copy.ttl_days == ttl_days


@pytest.mark.parametrize("ttl_days", [0, -1, 366, 1000])
def test_a_time_to_live_outside_1_to_365_days_is_refused(ttl_days: int) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a stored_copy without ttl_days between 1 and 365")
    and ADR-002 decision 1 (`ttl_days` 1 to 365)."""
    refusal(registry(entry(stored_copy=copy_of(ttl_days=ttl_days))))


@pytest.mark.parametrize("sha256", ["a" * 64, "0123456789abcdef" * 4])
def test_a_sha256_of_64_lower_case_hex_digits_loads(sha256: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`sha256` is 64 lower-case hex
    digits)."""
    (item,) = load(entry(stored_copy=copy_of(sha256=sha256))).resources

    assert item.stored_copy is not None
    assert item.stored_copy.sha256 == sha256


@parametrized(
    "sha256",
    {
        "upper-case": "A" * 64,
        "sixty-three-digits": "a" * 63,
        "sixty-five-digits": "a" * 65,
        "not-hex": "g" * 64,
        "empty": "",
        "trailing-line-feed": "a" * 64 + "\n",
        "leading-space": " " + "a" * 63,
    },
)
def test_a_sha256_that_is_not_64_lower_case_hex_digits_is_refused(sha256: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`sha256` is 64 lower-case hex
    digits)."""
    refusal(registry(entry(stored_copy=copy_of(sha256=sha256))))


@pytest.mark.parametrize(
    "stamp",
    [
        "2026-10-27T10:30:00Z",
        "2026-10-27T10:30:00+02:00",
        "2026-10-27T10:30:00-05:30",
        "2026-10-27T10:30:00.123456+00:00",
    ],
)
def test_a_timestamp_with_a_zone_loads(stamp: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`retrieved_at` is a timestamp with a
    zone, as `Clock.now()` gives)."""
    load(entry(stored_copy=copy_of(retrieved_at=stamp)))


@parametrized(
    "stamp",
    {
        "date-only": "2026-10-27",
        "naive-time": "2026-10-27T10:30:00",
        "naive-time-with-a-fraction": "2026-10-27T10:30:00.5",
        "not-a-time": "yesterday",
        "empty": "",
        "month-thirteen": "2026-13-01T10:30:00Z",
        "february-thirtieth": "2026-02-30T10:30:00Z",
        "hour-twenty-five": "2026-10-27T25:00:00Z",
        # Rework round 1 (reviewers P-2 F-1): `fromisoformat` accepts any character between the
        # date and the time, so the shape is pinned and no hidden code point can be stored.
        "space-separator": "2026-10-27 10:30:00Z",
        "newline-separator": "2026-10-27\n10:30:00Z",
        "bidi-override-separator": "2026-10-27\u202e10:30:00Z",
        "tag-character-separator": "2026-10-27\U000e004110:30:00Z",
        "lower-case-separator": "2026-10-27t10:30:00Z",
        "zero-width-in-the-time": "2026-10-27T10:30:\u200b00Z",
        "basic-format": "20261027T103000Z",
        "no-seconds": "2026-10-27T10:30Z",
        "arabic-indic-digits": "2026-10-27T\u0661\u0660:30:00Z",
        "trailing-newline": "2026-10-27T10:30:00Z\n",
    },
)
def test_a_date_only_naive_or_impossible_timestamp_is_refused(stamp: str) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a retrieved_at without a zone") and ADR-002
    decision 1 (`retrieved_at` is a timestamp with a zone; a value that is not a timestamp at all
    cannot be compared with the clock by `doctor`)."""
    refusal(registry(entry(stored_copy=copy_of(retrieved_at=stamp))))


# --- the cross-field rules ------------------------------------------------------------------------


def test_a_login_entry_may_keep_only_a_summary() -> None:
    """AC-1. expected_behavior_source: AC-1 ("a login entry whose copy form is copy") and
    ADR-002 decision 1 ("an `access: login` entry only allows `stored_copy.form: summary`")."""
    (kept,) = load(entry(access="login", stored_copy=copy_of(form="summary"))).resources

    assert kept.stored_copy is not None
    assert kept.stored_copy.form == "summary"
    refusal(registry(entry(access="login", stored_copy=copy_of(form="copy"))))


def test_a_login_entry_needs_no_stored_copy_and_a_public_one_may_keep_either_form() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (`stored_copy` is optional; only a
    login entry is limited to the summary)."""
    load(entry(access="login"))
    load(entry(access="public", stored_copy=copy_of(form="copy")))
    load(entry(access="public", stored_copy=copy_of(form="summary")))


INTERNAL_LABELS = ("internal", "corp", "lan", "home", "intranet")


@pytest.mark.parametrize("label", INTERNAL_LABELS)
def test_a_public_entry_cannot_use_an_address_that_ends_in_an_internal_label(label: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 and decision 8 ("an `access: public`
    entry cannot use an internal-looking last label (internal, corp, lan, home, intranet) ... a
    cross-field rule of the contract that url_problems alone cannot see"); EC-59."""
    address = f"https://wiki.example.{label}/handbook"
    assert url_problems(address) == ()  # the rule belongs to the contract, not to the address

    refusal(registry(entry(access="public", url=address)))
    refusal(registry(entry(access="public", url=f"https://example.{label}/handbook")))


@pytest.mark.parametrize("label", INTERNAL_LABELS)
def test_a_login_entry_may_use_an_address_that_ends_in_an_internal_label(label: str) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 8 ("an intranet host ... is legitimate
    for a `login` entry, so the host review in the pull request is the only control there")."""
    (item,) = load(entry(access="login", url=f"https://wiki.example.{label}/handbook")).resources

    assert item.access == "login"


@pytest.mark.parametrize("label", INTERNAL_LABELS)
def test_an_internal_label_that_is_not_the_last_one_does_not_make_a_public_entry_refused(
    label: str,
) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 (only the last host label is
    examined)."""
    load(entry(access="public", url=f"https://{label}.example.com/handbook"))


# --- the registry as a whole ----------------------------------------------------------------------


def test_entries_in_increasing_order_of_id_load() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 ("written in order of id")."""
    loaded = load(entry(id="alpha"), entry(id="beta"), entry(id="gamma"))

    assert ids_of(loaded) == ["alpha", "beta", "gamma"]


@parametrized(
    "ids",
    {
        "two-swapped": ["beta", "alpha"],
        "the-last-one-first": ["beta", "gamma", "alpha"],
        "descending": ["gamma", "beta", "alpha"],
    },
)
def test_entries_out_of_order_of_id_are_refused(ids: list[str]) -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 1 ("at most 100 entries, written in order
    of id") and the plan P-2 file operation on test_resources_contract.py ("the ordering by
    id")."""
    refusal(registry(*(entry(id=value) for value in ids)))


@parametrized(
    "ids",
    {
        "next-to-each-other": ["alpha", "alpha"],
        "separated-by-another": ["alpha", "beta", "alpha"],
        "at-the-end": ["alpha", "beta", "beta"],
    },
)
def test_a_repeated_id_is_refused(ids: list[str]) -> None:
    """AC-1. expected_behavior_source: AC-1 ("a repeated id") and ADR-002 decision 1 ("strictly
    increasing"; ids unique)."""
    refusal(registry(*(entry(id=value) for value in ids)))


def test_a_registry_of_100_entries_loads() -> None:
    """AC-1. expected_behavior_source: AC-1 ("more than 100 entries") and ADR-002 decision 1 (at
    most 100 entries)."""
    loaded = Resources.model_validate(registry(*numbered(100)))

    assert len(loaded.resources) == 100


def test_a_registry_of_101_entries_is_refused() -> None:
    """AC-1. expected_behavior_source: AC-1 ("more than 100 entries") and ADR-002 decision 1 (at
    most 100 entries)."""
    refusal(registry(*numbered(101)))


# --- AC-2: no message holds a part of an input value ----------------------------------------------


@parametrized("case", SECRET_CASES)
def test_no_message_of_the_contract_shows_a_part_of_the_input(
    case: tuple[dict[str, Any], tuple[str, ...]], capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("no message of the contract ... contains a part of any
    input value: a test places credential-shaped text in the address, the note, a glob and the
    copy fields"), ADR-002 decision 10 (the validators raise fixed-text errors) and
    ORQLET-SEC-003. Checked on the messages, types, locations and contexts that an error reports
    without the input, and on standard output and standard error."""
    document, secrets = case

    error = refusal(document)
    shown = error_texts(error)
    streams = capsys.readouterr()

    assert shown.strip()
    for secret in secrets:
        assert not leaks(shown, secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)


@parametrized("case", SECRET_CASES)
def test_the_text_of_a_validation_error_does_not_show_the_input_either(
    case: tuple[dict[str, Any], tuple[str, ...]],
) -> None:
    """AC-2. expected_behavior_source: AC-2 ("asserts that nothing appears in ... an exception
    message") and ORQLET-SEC-003. The strict reading: `str(error)` and `repr(error)` of the
    ValidationError itself, which pydantic fills with `input_value=...` unless the models hide the
    input (`hide_input_in_errors`). Drop this test if only the fixed-text messages are meant."""
    document, secrets = case

    error = refusal(document)

    for secret in secrets:
        assert not leaks(str(error), secret)
        assert not leaks(repr(error), secret)


@parametrized("case", SECRET_CASES)
def test_the_error_of_the_contract_loader_does_not_show_the_input(
    case: tuple[dict[str, Any], tuple[str, ...]], capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2. expected_behavior_source: AC-2 and ADR-002 decision 10 (read through the strict
    loader; the existing `load_contract` names the fields and the rule and not the values). The
    document is written as JSON, which the strict loader reads as YAML."""
    document, secrets = case

    with pytest.raises(DocumentError) as caught:
        load_contract(LOADER, Resources, json.dumps(document).encode(), source="registry")
    streams = capsys.readouterr()

    assert str(caught.value).strip()
    for secret in secrets:
        assert not leaks(str(caught.value), secret)
        assert not leaks(streams.out, secret)
        assert not leaks(streams.err, secret)
