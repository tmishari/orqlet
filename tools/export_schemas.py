"""Write, or with --check verify, the committed JSON Schema of every contract.

uv run python tools/export_schemas.py            # rewrite the files
uv run python tools/export_schemas.py --check    # fail when a file is stale (used by CI)
"""

from __future__ import annotations

import sys
from pathlib import Path

from orqlet.application.contracts import CONTRACTS
from orqlet.application.contracts.schemas import schema_filename, schema_text

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "src" / "orqlet" / "workflow" / "schemas"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale: list[str] = []
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for schema_id in sorted(CONTRACTS):
        target = SCHEMA_DIR / schema_filename(schema_id)
        wanted = schema_text(schema_id)
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == wanted:
            continue
        stale.append(target.name)
        if not check:
            target.write_text(wanted, encoding="utf-8", newline="\n")
    if check and stale:
        sys.stderr.write("stale schemas: " + ", ".join(stale) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
