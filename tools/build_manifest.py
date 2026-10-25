"""Write, or with --check verify, `src/orqlet/workflow/MANIFEST.json`.

    uv run python tools/build_manifest.py            # rewrite the manifest
    uv run python tools/build_manifest.py --check    # fail when it is stale (used by CI)

The manifest lists every file of the protected workflow with its SHA-256. Its digest is the
`workflow_digest`; a change of that digest without a change of `workflow_version` is a release
defect (see tests/contract/test_release_gate.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.workflow_package import WorkflowIdentity
from orqlet.application.usecases.workflow_manifest import build_manifest, is_listed

WORKFLOW_DIR = Path(__file__).resolve().parents[1] / "src" / "orqlet" / "workflow"


def read_files() -> dict[str, bytes]:
    return {
        path.relative_to(WORKFLOW_DIR).as_posix(): path.read_bytes()
        for path in sorted(WORKFLOW_DIR.rglob("*"))
        if path.is_file() and is_listed(path.relative_to(WORKFLOW_DIR).as_posix())
    }


def render() -> str:
    files = read_files()
    identity = load_contract(
        StrictYamlLoader(), WorkflowIdentity, files["identity.json"], source="identity.json"
    )
    manifest = build_manifest(identity, files)
    document = manifest.model_dump(mode="json", by_alias=True)
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    wanted = render()
    target = WORKFLOW_DIR / "MANIFEST.json"
    current = target.read_text(encoding="utf-8") if target.exists() else None
    if current == wanted:
        return 0
    if "--check" in argv:
        sys.stderr.write("MANIFEST.json is stale: run `uv run python tools/build_manifest.py`\n")
        return 1
    target.write_text(wanted, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
