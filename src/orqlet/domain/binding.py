"""The review-input binding (proposal 6.14.1).

A review, a test record and a knowledge-impact record each state the digest of exactly the inputs
they examined, as named components, so a verifier can say *which* component changed. A record
never contains a commit id, the digest of the final tree or a digest that includes itself, so
committing it leaves the digest unchanged.

Which kinds a changed component makes stale is derived from what each kind covers. It is not a
second table, so the two cannot disagree.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from orqlet.domain.digest import digest_of


class Component(StrEnum):
    CODE_TESTS = "code_tests"
    KNOWLEDGE = "knowledge"
    DESIGN = "design"
    PLAN = "plan"
    STANDARDS = "standards"
    REVIEWER_DEFINITION = "reviewer_definition"
    EVIDENCE_INPUTS = "evidence_inputs"
    CANDIDATES = "candidates"


class RecordKind(StrEnum):
    REVIEW = "review"
    TEST = "test"
    KNOWLEDGE_IMPACT = "knowledge-impact"


COVERS: dict[RecordKind, tuple[Component, ...]] = {
    RecordKind.REVIEW: (
        Component.CODE_TESTS,
        Component.KNOWLEDGE,
        Component.DESIGN,
        Component.PLAN,
        Component.STANDARDS,
        Component.REVIEWER_DEFINITION,
        Component.EVIDENCE_INPUTS,
    ),
    RecordKind.TEST: (Component.CODE_TESTS, Component.PLAN),
    RecordKind.KNOWLEDGE_IMPACT: (
        Component.CODE_TESTS,
        Component.KNOWLEDGE,
        Component.PLAN,
        Component.STANDARDS,
        Component.CANDIDATES,
    ),
}


@dataclass(frozen=True, slots=True)
class ChangedFile:
    """One path that differs between the merge base and the tree.

    `digest` is the SHA-256 of the blob; for a symbolic link the SHA-256 of its target string,
    and for a gitlink its commit id, because there is no blob to hash.
    """

    path: str
    status: str  # added, modified, deleted or type-changed. Renames are a delete plus an add.
    mode: str
    digest: str


def changed_files_digest(files: Sequence[ChangedFile]) -> str:
    """The digest of a list of changed files, independent of the order they were listed in."""
    ordered = sorted(files, key=lambda file: file.path)
    return digest_of([[f.path, f.status, f.mode, f.digest] for f in ordered])


def partition_changes(
    files: Sequence[ChangedFile],
    *,
    is_evidence: Callable[[str], bool],
    in_knowledge_scope: Callable[[str], bool],
) -> tuple[list[ChangedFile], list[ChangedFile]]:
    """Split the changes into `code_tests` and `knowledge`; evidence artifacts are in neither.

    Both reviews cover both lists, so a path moved between them stays under review.
    """
    code: list[ChangedFile] = []
    knowledge: list[ChangedFile] = []
    for file in files:
        if is_evidence(file.path):
            continue
        (knowledge if in_knowledge_scope(file.path) else code).append(file)
    return code, knowledge


def input_digest(components: Mapping[Component, str], covers: Sequence[Component]) -> str:
    """The digest over the covered components only, from their individual digests."""
    missing = [c.value for c in covers if c not in components]
    if missing:
        raise ValueError(f"components are missing: {', '.join(missing)}")
    return digest_of({component.value: components[component] for component in covers})


def stale_components(
    recorded: Mapping[str, str], current: Mapping[Component, str], covers: Sequence[Component]
) -> tuple[str, ...]:
    """The covered components whose digest is not the one the record states."""
    return tuple(
        component.value
        for component in covers
        if recorded.get(component.value) != current.get(component)
    )


def kinds_made_stale_by(component: Component) -> frozenset[RecordKind]:
    """The record kinds that a change in `component` makes stale."""
    return frozenset(kind for kind, covered in COVERS.items() if component in covered)
