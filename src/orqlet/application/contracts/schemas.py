"""Turning contracts into the committed JSON Schema files."""

from __future__ import annotations

import json

from orqlet.application.contracts import CONTRACTS


def schema_filename(schema_id: str) -> str:
    """`orqlet.versions/v1` becomes `orqlet.versions.v1.json`."""
    return schema_id.replace("/", ".") + ".json"


def schema_text(schema_id: str) -> str:
    """Stable text of the schema: sorted keys, two-space indent, one trailing newline."""
    schema = CONTRACTS[schema_id].model_json_schema(by_alias=True)
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
