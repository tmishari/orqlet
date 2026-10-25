"""`orqlet review prepare`: the read-only packet that independent reviewers read (proposal 19.5).

The packet is the exact staged snapshot, exported outside the repository together with the diff,
the plan, the design, the standards the project holds and the phase's test and knowledge-impact
records. A reviewer reads the packet and needs no shell. Nothing here reads the working tree: what
was never staged was never reviewed, and a half-merged index is refused by `staged_tree`.

The packet is read-only by instruction and by location, not by a file mode: the file-system port has
no permission call. It is written once, into a folder that did not exist.
"""

from __future__ import annotations

from collections.abc import Mapping

from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.ports.filesystem import FileSystem, FileSystemError
from orqlet.application.usecases.binding_inputs import (
    AGENT_FILES,
    BindingRequest,
    Target,
    change_set,
    compute_components,
    knowledge_scope,
    locate,
    read_contract_at,
)
from orqlet.application.usecases.knowledge_impact import analyse, knowledge_binding
from orqlet.application.usecases.validation import (
    TASK_ROOT,
    Collector,
    ValidateServices,
    ValidationResult,
)
from orqlet.domain.binding import COVERS, Component, RecordKind, input_digest
from orqlet.domain.digest import canonical_json, digest_of, sha256_hex
from orqlet.domain.errors import InvalidPath
from orqlet.domain.paths import CanonicalPath

MAX_FILES = 5000
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
DEFAULT_REVIEWERS = {
    "architecture-reviewer": "orqlet-arch-reviewer",
    "security-reviewer": "orqlet-security-reviewer",
}
STANDARDS_FILES = (
    ".orqlet/standards.lock.yaml",
    ".orqlet/rules.yaml",
    ".prompts/rules.yaml",
    ".prompts/foundations.md",
)


def review_prepare(
    services: ValidateServices,
    packets: FileSystem,
    packet_id: str,
    task: str,
    phase: str,
    *,
    base: str | None = None,
    head: str | None = None,
) -> ValidationResult:
    out = Collector()
    located = locate(services, base, head)
    if located.target is None:
        for problem in located.problems:
            out.skip(problem)
        return out.result()
    target = located.target
    folder = f"{TASK_ROOT}/{task}"
    plan = read_contract_at(services, target.tree, f"{folder}/plan.yaml", ImplementationPlan, out)
    design = read_contract_at(
        services, target.tree, f"{folder}/design/manifest.yaml", DesignSet, out
    )
    if plan is None or design is None or out.has_errors():
        return out.result()
    if not any(p.id == phase for p in plan.phases):
        out.error("ORQ-E440", f"the plan has no phase {phase}", f"{folder}/plan.yaml")
        return out.result()
    files, omitted = _packet_files(services, target, folder, phase)
    manifest = _manifest(target, files, omitted)
    name = f"{task}-{phase}-{packet_id[:8]}"
    written = _write(packets, name, {**files, "MANIFEST.json": manifest}, out)
    if not written:
        return out.result()
    for note in omitted:
        out.info("ORQ-I440", f"left out of the packet: {note}")
    data: dict[str, object] = {
        "packet": name,
        "files": len(files),
        "tree": target.label,
        "base": target.base,
        "packet_digest": digest_of(sorted([p, sha256_hex(c)] for p, c in files.items())),
        "review_inputs": _bindings(services, task, phase, target, plan, out),
    }
    return out.result(data)


def _packet_files(
    services: ValidateServices, target: Target, folder: str, phase: str
) -> tuple[dict[str, bytes], list[str]]:
    vcs = services.vcs
    files: dict[str, bytes] = {}
    omitted: list[str] = []
    total = 0
    entries = []
    for entry in vcs.tree_at(target.tree):
        if entry.mode in {"120000", "160000"}:
            omitted.append(f"{entry.path} (a symbolic link or a gitlink)")
            continue
        try:
            CanonicalPath.parse(entry.path)
        except InvalidPath:
            omitted.append(f"{entry.path} (a name that cannot be written safely)")
            continue
        entries.append(entry.path)
    contents = vcs.read_many_at(target.tree, entries)
    for path in entries:
        data = contents[path]
        if data is None:
            continue
        if len(files) >= MAX_FILES or len(data) > MAX_FILE_BYTES:
            omitted.append(f"{path} (over the packet limits)")
            continue
        if total + len(data) > MAX_TOTAL_BYTES:
            omitted.append(f"{path} (over the packet limits)")
            continue
        files[f"snapshot/{path}"] = data
        total += len(data)
    files["diff.patch"] = vcs.diff_patch(target.base, target.tree)
    for label, path in (
        ("plan.yaml", f"{folder}/plan.yaml"),
        ("design-manifest.yaml", f"{folder}/design/manifest.yaml"),
        ("as-is.md", f"{folder}/as-is.md"),
        ("test-record.yaml", f"{folder}/tests/{phase}.yaml"),
        ("knowledge-impact.yaml", f"{folder}/knowledge/{phase}.yaml"),
    ):
        data = vcs.read_at(target.tree, path)
        if data is not None:
            files[f"context/{label}"] = data
    for path in STANDARDS_FILES:
        data = vcs.read_at(target.tree, path)
        if data is not None:
            files[f"context/standards/{path.rsplit('/', 1)[-1]}"] = data
    return files, omitted


def _manifest(target: Target, files: Mapping[str, bytes], omitted: list[str]) -> bytes:
    return (
        canonical_json(
            {
                "base": target.base,
                "tree": target.tree,
                "label": target.label,
                "files": [[path, sha256_hex(data)] for path, data in sorted(files.items())],
                "omitted": sorted(omitted),
            }
        )
        + b"\n"
    )


def _write(packets: FileSystem, name: str, files: Mapping[str, bytes], out: Collector) -> bool:
    root = CanonicalPath.parse(name)
    try:
        if packets.kind(root) is not None:
            out.error(
                "ORQ-E441", f"the packet folder {name} already exists; packets are written once"
            )
            return False
        for path, data in files.items():
            packets.write_atomic(CanonicalPath.parse(f"{root}/{path}"), data)
    except (FileSystemError, InvalidPath) as error:
        out.error("ORQ-E442", f"the packet could not be written: {error}")
        return False
    return True


def _bindings(
    services: ValidateServices,
    task: str,
    phase: str,
    target: Target,
    plan: ImplementationPlan,
    out: Collector,
) -> dict[str, object]:
    """The `review_input` blocks of the three record kinds, for the records an agent writes next."""
    changes = change_set(services, target, knowledge_scope(services, target.tree, plan))
    base_request = BindingRequest(task, phase, target, changes)
    common = compute_components(services, base_request, Collector())
    result: dict[str, object] = {}
    test_covers = COVERS[RecordKind.TEST]
    if all(c in common for c in test_covers):
        result["test"] = _block(common, test_covers, target)
    analysis = analyse(services, task, None, None, Collector(), target=target)
    if analysis is not None:
        knowledge = knowledge_binding(services, task, phase, analysis, Collector())
        if knowledge is not None:
            result["knowledge-impact"] = knowledge
    reviews: dict[str, dict[str, object]] = {}
    for role, agent in DEFAULT_REVIEWERS.items():
        for client in AGENT_FILES:
            request = BindingRequest(
                task, phase, target, changes, role=role, agent_ref=agent, agent_client=client
            )
            if services.vcs.read_at(target.tree, AGENT_FILES[client].format(ref=agent)) is None:
                continue
            components = compute_components(services, request, Collector())
            covers = COVERS[RecordKind.REVIEW]
            if all(c in components for c in covers):
                reviews.setdefault(role, {})[client] = _block(components, covers, target)
    if reviews:
        result["review"] = reviews
    else:
        out.info(
            "ORQ-I441",
            "no generated reviewer agent is in the tree, so the review binding is not printed",
        )
    return result


def _block(
    components: Mapping[Component, str], covers: tuple[Component, ...], target: Target
) -> dict[str, object]:
    return {
        "schema": "orqlet.review-input/v1",
        "covers": [c.value for c in covers],
        "components": {c.value: components[c] for c in covers},
        "digest": input_digest(components, covers),
        "merge_base": target.base,
    }
