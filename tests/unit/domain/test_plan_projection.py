"""The nineteen plan cases of proposal 17.5, one named test each, plus the finer rules."""

from __future__ import annotations

import pytest

from orqlet.domain.plan_projection import (
    EntryMode,
    FileOperation,
    Op,
    PlanPhase,
    TreeEntry,
    check_plan,
    structural_changes,
)

pytestmark = pytest.mark.unit


def create(path: str, moved_from: str | None = None) -> FileOperation:
    return FileOperation(Op.CREATE, path, moved_from)


def modify(path: str) -> FileOperation:
    return FileOperation(Op.MODIFY, path)


def delete(path: str) -> FileOperation:
    return FileOperation(Op.DELETE, path)


def phase(phase_id: str, *operations: FileOperation, after: tuple[str, ...] = ()) -> PlanPhase:
    return PlanPhase(phase_id, after, operations)


def files(*paths: str) -> list[TreeEntry]:
    return [TreeEntry(path) for path in paths]


def codes(tree: list[TreeEntry], *phases: PlanPhase) -> list[str]:
    return [finding.code for finding in check_plan(tree, phases)]


def test_case_01_a_file_created_by_a_predecessor_can_be_modified() -> None:
    result = codes(
        [],
        phase("P1", create("src/pkg/mod.py")),
        phase("P2", modify("src/pkg/mod.py"), after=("P1",)),
    )

    assert result == []


def test_case_02_a_file_cannot_be_created_twice() -> None:
    result = codes(
        [],
        phase("P1", create("src/pkg/mod.py")),
        phase("P2", create("src/pkg/mod.py"), after=("P1",)),
    )

    assert result == ["ORQ-E308"]


def test_case_03_a_transitive_predecessor_counts() -> None:
    result = codes(
        [],
        phase("P1", create("src/pkg/mod.py")),
        phase("P2", create("src/pkg/other.py"), after=("P1",)),
        phase("P3", modify("src/pkg/mod.py"), after=("P2",)),
    )

    assert result == []


def test_case_04_unordered_phases_cannot_both_modify_one_file() -> None:
    result = codes(files("a.py"), phase("P1", modify("a.py")), phase("P2", modify("a.py")))

    assert result == ["ORQ-E310"]


def test_case_05_a_diamond_over_different_files_is_valid() -> None:
    result = codes(
        files("a.py", "b.py"),
        phase("P1", create("c.py")),
        phase("P2", modify("a.py"), after=("P1",)),
        phase("P3", modify("b.py"), after=("P1",)),
    )

    assert result == []


def test_case_06_a_diamond_over_the_same_file_conflicts() -> None:
    result = codes(
        files("a.py"),
        phase("P1", create("c.py")),
        phase("P2", modify("a.py"), after=("P1",)),
        phase("P3", modify("a.py"), after=("P1",)),
    )

    assert result == ["ORQ-E310"]


def test_case_07_a_deleted_file_can_be_created_again_by_a_dependent_phase() -> None:
    result = codes(
        files("old.py"), phase("P1", delete("old.py")), phase("P2", create("old.py"), after=("P1",))
    )

    assert result == []


def test_case_08_a_deleted_file_cannot_be_modified_later() -> None:
    result = codes(
        files("old.py"), phase("P1", delete("old.py")), phase("P2", modify("old.py"), after=("P1",))
    )

    assert result == ["ORQ-E309"]


def test_case_09_a_move_deletes_its_source_in_the_same_phase() -> None:
    result = codes(files("a.py"), phase("P1", create("b.py", moved_from="a.py"), delete("a.py")))

    assert result == []


def test_case_10_a_case_only_rename_is_valid() -> None:
    result = codes(
        files("src/foo.py"),
        phase("P1", create("src/Foo.py", moved_from="src/foo.py"), delete("src/foo.py")),
    )

    assert result == []


def test_case_11_a_file_can_be_replaced_by_a_directory() -> None:
    result = codes(
        files("tools/run"), phase("P1", delete("tools/run"), create("tools/run/main.py"))
    )

    assert result == []


def test_case_12_one_phase_cannot_create_a_file_and_a_directory_of_one_name() -> None:
    result = codes([], phase("P1", create("pkg/util"), create("pkg/util/x.py")))

    assert result == ["ORQ-E305"]


def test_case_13_a_later_phase_cannot_turn_a_directory_into_a_file() -> None:
    result = codes(
        [], phase("P1", create("pkg/util/x.py")), phase("P2", create("pkg/util"), after=("P1",))
    )

    assert result == ["ORQ-E308"]


def test_case_14_a_directory_has_one_spelling() -> None:
    result = codes(files("src/pkg/old.py"), phase("P1", create("SRC/pkg/new.py")))

    assert result == ["ORQ-E312"]


def test_case_15_nfc_and_nfd_spellings_are_one_file() -> None:
    nfd = "docs/cafe\u0301.md"
    nfc = "docs/caf\u00e9.md"

    assert codes(files(nfd), phase("P1", modify(nfc))) == []


@pytest.mark.parametrize(
    "path", ["aux.py", "a\\b.py", "dir/con", "x:y.py", "../up.py", "/abs.py", ".git/config"]
)
def test_case_16_reserved_names_and_separators_are_refused(path: str) -> None:
    assert codes([], phase("P1", create(path))) == ["ORQ-E300"]


@pytest.mark.parametrize("mode", [EntryMode.GITLINK, EntryMode.SYMLINK])
def test_case_17_a_gitlink_or_symlink_cannot_be_modified(mode: EntryMode) -> None:
    result = codes([TreeEntry("third_party/lib", mode)], phase("P1", modify("third_party/lib")))

    assert result == ["ORQ-E311"]


def test_case_17b_nothing_can_be_created_below_a_gitlink() -> None:
    result = codes(
        [TreeEntry("third_party/lib", EntryMode.GITLINK)],
        phase("P1", create("third_party/lib/x.py")),
    )

    assert result == ["ORQ-E311"]


def test_case_18_dependencies_must_exist_be_other_phases_and_form_no_cycle() -> None:
    dangling = codes([], phase("P1", after=("P9",)))
    itself = codes([], phase("P1", after=("P1",)))
    cycle = codes([], phase("P1", after=("P2",)), phase("P2", after=("P1",)))

    assert (dangling, itself, cycle) == (["ORQ-E302"], ["ORQ-E303"], ["ORQ-E304"])


def test_case_19_moved_from_belongs_on_a_create() -> None:
    result = codes(files("a.py", "b.py"), phase("P1", FileOperation(Op.MODIFY, "a.py", "b.py")))

    assert result == ["ORQ-E306"]


def test_a_move_needs_its_source_to_exist_to_be_deleted_here_and_to_be_used_once() -> None:
    missing = codes([], phase("P1", create("b.py", moved_from="a.py"), delete("a.py")))
    kept = codes(files("a.py"), phase("P1", create("b.py", moved_from="a.py")))
    twice = codes(
        files("a.py"),
        phase(
            "P1",
            create("b.py", moved_from="a.py"),
            create("c.py", moved_from="a.py"),
            delete("a.py"),
        ),
    )

    assert "ORQ-E307" in missing
    assert kept == ["ORQ-E307"]
    assert twice == ["ORQ-E307"]


def test_two_operations_on_one_path_in_a_phase_conflict() -> None:
    assert codes(files("a.py"), phase("P1", modify("a.py"), delete("a.py"))) == ["ORQ-E305"]
    assert codes(files("a.py"), phase("P1", modify("a.py"), modify("A.py"))) == [
        "ORQ-E305",
        "ORQ-E312",
    ]


def test_a_duplicate_phase_id_is_reported_and_stops_the_projection() -> None:
    result = codes([], phase("P1", create("a.py")), phase("P1", create("a.py")))

    assert result == ["ORQ-E301"]


def test_a_file_spelled_in_another_case_is_not_the_tracked_file() -> None:
    assert codes(files("src/old.py"), phase("P1", modify("src/Old.py"))) == ["ORQ-E312"]


def test_a_tree_path_that_cannot_be_canonicalised_never_collides() -> None:
    assert codes(files("con.txt"), phase("P1", create("new.py"))) == []


def test_findings_name_the_phase_and_carry_the_path() -> None:
    (finding,) = check_plan(files("old.py"), [phase("P7", modify("gone.py"))])

    assert (finding.code, finding.path) == ("ORQ-E309", "gone.py")
    assert "P7" in finding.message


def test_structural_changes_are_derived_from_the_operations() -> None:
    plan = [
        phase("P2", create("n.py"), modify("m.py"), delete("old.py")),
        phase("P1", create("b.py", moved_from="a.py"), delete("a.py")),
    ]

    assert structural_changes(plan) == (
        "P1: move a.py -> b.py",
        "P2: create n.py",
        "P2: delete old.py",
    )
