"""The `.prompts/` seed: written once, then owned by the team (proposal section 12.8)."""

from __future__ import annotations

from orqlet.adapters.render.emit import normalise_text
from orqlet.application.ports.instruction_adapter import RenderedFile
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.domain.digest import sha256_hex
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath

SEED_PREFIX = "seeds/prompts/"


def seed_files(workflow: WorkflowSource, *, base: str = ".prompts") -> tuple[RenderedFile, ...]:
    """The seed files under `base`, in path order. A pack may supply its own seed instead."""
    root = CanonicalPath.parse(base)
    files = []
    for path in workflow.paths():
        if not path.startswith(SEED_PREFIX):
            continue
        data = normalise_text(workflow.read_text(path)).encode("utf-8")
        files.append(
            RenderedFile(
                path=root.child(path[len(SEED_PREFIX) :]),
                content=data,
                owner=OwnerMode.SEEDED,
                file_class=None,
                inputs=((path, str(workflow.release.version), sha256_hex(data)),),
            )
        )
    return tuple(files)
