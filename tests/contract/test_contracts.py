"""Contracts: valid fixtures load, closed models reject extras, committed schemas are current."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from orqlet.application.contracts import CONTRACTS
from orqlet.application.contracts.common import Evidence, FactValue
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.schemas import schema_filename, schema_text

pytestmark = pytest.mark.contract

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "contracts" / "valid"
SCHEMAS = Path(__file__).resolve().parents[2] / "src" / "orqlet" / "workflow" / "schemas"
HASH = "a" * 64


def load_fixture(schema_id: str) -> dict[str, Any]:
    text = (FIXTURES / schema_filename(schema_id).replace(".json", ".yaml")).read_text("utf-8")
    loaded = yaml.safe_load(text)
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.parametrize("schema_id", sorted(CONTRACTS))
def test_valid_fixture_loads_and_round_trips(schema_id: str) -> None:
    model = CONTRACTS[schema_id]
    first = model.model_validate(load_fixture(schema_id))
    dumped = first.model_dump(mode="json", by_alias=True)

    assert model.model_validate(dumped) == first
    assert dumped["schema"] == schema_id


@pytest.mark.parametrize("schema_id", sorted(CONTRACTS))
def test_unknown_top_level_field_is_rejected(schema_id: str) -> None:
    data = load_fixture(schema_id)
    data["surprise"] = 1

    with pytest.raises(ValidationError):
        CONTRACTS[schema_id].model_validate(data)


@pytest.mark.parametrize("schema_id", sorted(CONTRACTS))
def test_wrong_schema_id_is_rejected(schema_id: str) -> None:
    data = load_fixture(schema_id)
    data["schema"] = schema_id.replace("/v", "/v9")

    with pytest.raises(ValidationError):
        CONTRACTS[schema_id].model_validate(data)


@pytest.mark.parametrize("schema_id", sorted(CONTRACTS))
def test_committed_schema_matches_the_models(schema_id: str) -> None:
    committed = (SCHEMAS / schema_filename(schema_id)).read_text(encoding="utf-8")

    assert committed == schema_text(schema_id), "run: uv run python tools/export_schemas.py"


def test_no_stray_schema_files() -> None:
    expected = {schema_filename(schema_id) for schema_id in CONTRACTS}

    assert {path.name for path in SCHEMAS.glob("*.json")} == expected


def test_a_known_fact_needs_evidence_or_an_answer() -> None:
    with pytest.raises(ValidationError):
        FactValue(value="3.12")

    evidence = Evidence(path="pyproject.toml", lines="1-1", sha256=HASH)
    assert FactValue(value="3.12", evidence=(evidence,)).value == "3.12"
    assert FactValue(value="main", answered_by="maintainer").value == "main"


def test_an_unknown_fact_needs_a_question() -> None:
    with pytest.raises(ValidationError):
        FactValue()

    assert FactValue(question="Which branch?").value is None


def test_evidence_rejects_a_bad_hash_and_bad_line_range() -> None:
    with pytest.raises(ValidationError):
        Evidence(path="a", lines="1-1", sha256="xyz")
    with pytest.raises(ValidationError):
        Evidence(path="a", lines="one", sha256=HASH)


@pytest.mark.parametrize(
    "file",
    [
        {"path": "a", "owner": "seeded"},
        {"path": "a", "owner": "orqlet", "class": "protected"},
        {"path": "a", "owner": "shared-block", "class": "generated", "rendered_sha256": HASH},
        {"path": "a", "owner": "shared-entry", "class": "generated", "rendered_sha256": HASH},
        {"path": "a", "owner": "orqlet", "rendered_sha256": HASH},
    ],
)
def test_generated_lock_rejects_incomplete_entries(file: dict[str, Any]) -> None:
    data = {"schema": "orqlet.generated-lock/v1", "generator": {"orqlet": "0.1.0"}, "files": [file]}

    with pytest.raises(ValidationError):
        GeneratedLock.model_validate(data)


def test_a_technology_found_by_a_scanner_or_an_agent_needs_evidence() -> None:
    from orqlet.application.contracts.profile import Technology

    with pytest.raises(ValidationError, match="needs evidence"):
        Technology(kind="database", name="PostgreSQL")
    with pytest.raises(ValidationError, match="needs evidence"):
        Technology(kind="queue", name="Kafka", source="agent")

    stated = Technology(kind="database", name="PostgreSQL", version="16", source="maintainer")
    cited = Technology(
        kind="language",
        name="Go",
        evidence=(Evidence(path="go.mod", lines="3-3", sha256=HASH),),
    )
    assert stated.evidence == ()
    assert cited.scope == "."


def test_an_unknown_technology_kind_is_rejected() -> None:
    from orqlet.application.contracts.profile import Technology

    with pytest.raises(ValidationError):
        Technology(kind="spaceship", name="X", source="maintainer")
