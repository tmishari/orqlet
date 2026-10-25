"""The review-input binding: what each record covers and which changes make it stale (6.14.1)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.domain.binding import (
    COVERS,
    ChangedFile,
    Component,
    RecordKind,
    changed_files_digest,
    input_digest,
    kinds_made_stale_by,
    partition_changes,
    stale_components,
)

pytestmark = pytest.mark.unit

REVIEW, TEST, KNOWLEDGE = RecordKind.REVIEW, RecordKind.TEST, RecordKind.KNOWLEDGE_IMPACT


def digests(**overrides: str) -> dict[Component, str]:
    base = {component: f"{index:064x}" for index, component in enumerate(Component)}
    base.update({Component(name): value for name, value in overrides.items()})
    return base


# The staleness table of the proposal (6.14.1), cell by cell: which kinds a changed component hits.
TABLE = {
    Component.CODE_TESTS: {REVIEW, TEST, KNOWLEDGE},
    Component.KNOWLEDGE: {REVIEW, KNOWLEDGE},
    Component.DESIGN: {REVIEW},
    Component.PLAN: {REVIEW, TEST, KNOWLEDGE},
    Component.STANDARDS: {REVIEW, KNOWLEDGE},
    Component.CANDIDATES: {KNOWLEDGE},
    Component.REVIEWER_DEFINITION: {REVIEW},
    Component.EVIDENCE_INPUTS: {REVIEW},
}


@pytest.mark.parametrize("component", list(Component))
def test_a_changed_component_makes_stale_exactly_the_kinds_the_table_names(
    component: Component,
) -> None:
    assert kinds_made_stale_by(component) == TABLE[component]


def test_each_kind_covers_what_the_proposal_says() -> None:
    assert set(COVERS[TEST]) == {Component.CODE_TESTS, Component.PLAN}
    assert Component.CANDIDATES not in COVERS[REVIEW]
    assert Component.REVIEWER_DEFINITION not in COVERS[KNOWLEDGE]


def test_the_digest_covers_only_the_named_components() -> None:
    before = input_digest(digests(), COVERS[TEST])

    assert input_digest(digests(design="f" * 64), COVERS[TEST]) == before  # FM-B03: not covered
    assert input_digest(digests(code_tests="f" * 64), COVERS[TEST]) != before  # FM-B02
    assert input_digest(digests(plan="f" * 64), COVERS[TEST]) != before


def test_a_component_that_is_needed_but_absent_is_an_error() -> None:
    partial = {Component.CODE_TESTS: "a" * 64}

    with pytest.raises(ValueError, match="plan"):
        input_digest(partial, COVERS[TEST])


def test_stale_components_name_which_one_changed() -> None:
    recorded = {c.value: d for c, d in digests().items() if c in COVERS[REVIEW]}

    assert stale_components(recorded, digests(), COVERS[REVIEW]) == ()
    assert stale_components(recorded, digests(plan="e" * 64, design="d" * 64), COVERS[REVIEW]) == (
        "design",
        "plan",
    )


def test_a_component_the_record_never_stated_counts_as_stale() -> None:
    assert stale_components({}, digests(), COVERS[TEST]) == ("code_tests", "plan")


def file(
    path: str, status: str = "modified", mode: str = "100644", digest: str = "a" * 64
) -> ChangedFile:
    return ChangedFile(path, status, mode, digest)


def test_the_digest_of_changed_files_does_not_depend_on_the_listing_order() -> None:
    first = [file("a.py"), file("b.py")]

    assert changed_files_digest(first) == changed_files_digest(list(reversed(first)))


@pytest.mark.parametrize(
    "different",
    [
        file("a.py", status="added"),
        file("a.py", mode="100755"),
        file("a.py", digest="b" * 64),
        file("c.py"),
    ],
)
def test_the_digest_of_changed_files_sees_status_mode_content_and_path(
    different: ChangedFile,
) -> None:
    assert changed_files_digest([file("a.py")]) != changed_files_digest([different])


def test_evidence_files_are_in_neither_list_and_a_knowledge_path_moves_between_them() -> None:
    changes = [
        file("src/a.py"),
        file("docs/guide.md"),
        file("docs/design/demo/reviews/architecture-reviewer-P-1-r1.yaml"),
    ]

    code, knowledge = partition_changes(
        changes,
        is_evidence=lambda path: "/reviews/" in path,
        in_knowledge_scope=lambda path: path.startswith("docs/") and "/design/" not in path,
    )

    assert [f.path for f in code] == ["src/a.py"]
    assert [f.path for f in knowledge] == ["docs/guide.md"]
    both = {f.path for f in code + knowledge}
    assert both == {"src/a.py", "docs/guide.md"}  # a stray evidence file is excluded by the caller


def test_a_path_outside_the_evidence_pattern_stays_in_the_binding() -> None:
    changes = [file("docs/design/demo/reviews/helper.py")]

    code, _ = partition_changes(
        changes, is_evidence=lambda _: False, in_knowledge_scope=lambda _: False
    )

    assert [f.path for f in code] == ["docs/design/demo/reviews/helper.py"]


@given(st.lists(st.sampled_from(sorted(Component, key=str)), unique=True, min_size=1))
def test_the_digest_is_independent_of_the_order_the_covered_components_are_listed_in(
    covers: list[Component],
) -> None:
    assert input_digest(digests(), covers) == input_digest(digests(), list(reversed(covers)))
