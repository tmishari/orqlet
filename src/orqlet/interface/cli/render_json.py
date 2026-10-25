"""The `--json` output: one envelope, stable key order, no colour."""

from __future__ import annotations

import json

from orqlet.application.contracts.cli_result import CliResult


def render_json(result: CliResult) -> str:
    document = result.model_dump(mode="json", by_alias=True)
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False)
