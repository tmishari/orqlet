"""The pure change plan: files, shared blocks, proposals, orphans and idempotence."""

import pytest

from orqlet.domain.blocks import render_block
from orqlet.domain.changeplan import (
    Action,
    ChangePlan,
    Desired,
    PlanError,
    Recorded,
    build_plan,
    normalised_hash,
    proposal_path,
)
from orqlet.domain.classify import FileState
from orqlet.domain.digest import sha256_hex
from orqlet.domain.ownership import FileClass, OwnerMode
from orqlet.domain.paths import CanonicalPath

pytestmark = pytest.mark.unit


def p(text: str) -> CanonicalPath:
    return CanonicalPath.parse(text)


def whole(
    path: str,
    text: str,
    *,
    owner: OwnerMode = OwnerMode.ORQLET,
    cls: FileClass = FileClass.GENERATED,
) -> Desired:
    return Desired(p(path), owner, None if owner is OwnerMode.SEEDED else cls, text.encode())


def block(path: str, name: str, body: str, *, info: str = "v1") -> Desired:
    return Desired(
        p(path),
        OwnerMode.SHARED_BLOCK,
        FileClass.GENERATED,
        render_block(name, info, body).encode(),
        block_name=name,
    )


def recorded_from(plan: ChangePlan) -> list[Recorded]:
    return list(plan.recorded_after)


def apply(plan: ChangePlan, tree: dict[CanonicalPath, bytes]) -> dict[CanonicalPath, bytes]:
    result = dict(tree)
    for write in plan.writes:
        if write.kind == "delete":
            result.pop(write.path, None)
        else:
            assert write.content is not None
            result[write.path] = write.content
    return result


def test_new_files_are_created_and_recorded() -> None:
    plan = build_plan([whole("a.md", "one\n")], {}, [])

    assert [(i.state, i.action) for i in plan.items] == [(FileState.NEW, Action.CREATE)]
    assert [(str(w.path), w.kind) for w in plan.writes] == [("a.md", "create")]
    assert plan.recorded_after[0].sha256 == normalised_hash(b"one\n")


def test_a_second_run_over_its_own_result_is_an_empty_plan() -> None:
    desired = [
        whole("a.md", "one\n"),
        whole("seed.md", "seed\n", owner=OwnerMode.SEEDED),
        block("AGENTS.md", "baseline", "text"),
        block(".github/pr.md", "orqlet-workflow", "wf"),
        block(".github/pr.md", "team-template", "team"),
    ]
    first = build_plan(desired, {}, [])
    tree = apply(first, {})

    second = build_plan(desired, tree, recorded_from(first))

    assert second.is_empty
    assert {i.action for i in second.items} == {Action.NOOP}
    assert second.recorded_after == first.recorded_after


def test_a_safe_update_changes_only_what_orqlet_wrote() -> None:
    first = build_plan([whole("a.md", "one\n")], {}, [])
    tree = apply(first, {})

    second = build_plan([whole("a.md", "two\n")], tree, recorded_from(first))

    assert [(i.state, i.action) for i in second.items] == [(FileState.SAFE_UPDATE, Action.UPDATE)]
    assert apply(second, tree)[p("a.md")] == b"two\n"


def test_a_user_edit_is_never_overwritten_and_stays_recorded_as_before() -> None:
    first = build_plan([whole("a.md", "one\n")], {}, [])
    tree = apply(first, {}) | {p("a.md"): b"edited by the team\n"}

    second = build_plan([whole("a.md", "one\n")], tree, recorded_from(first))

    assert second.is_empty
    assert second.items[0].state is FileState.USER_EDIT_ONLY
    assert second.recorded_after == first.recorded_after


def test_a_conflict_writes_a_proposal_and_leaves_the_live_file() -> None:
    first = build_plan([whole("a.md", "one\n")], {}, [])
    tree = apply(first, {}) | {p("a.md"): b"edited\n"}

    second = build_plan([whole("a.md", "three\n")], tree, recorded_from(first))

    assert [i.action for i in second.items] == [Action.STOP]
    assert [str(w.path) for w in second.writes] == [str(proposal_path(p("a.md"), None))]
    assert second.writes[0].is_proposal
    assert b"-edited" in (second.writes[0].content or b"")
    assert b"+three" in (second.writes[0].content or b"")
    assert apply(second, tree)[p("a.md")] == b"edited\n"


def test_an_unmanaged_file_in_the_way_is_a_name_collision_with_a_proposal() -> None:
    plan = build_plan([whole("a.md", "ours\n")], {p("a.md"): b"theirs\n"}, [])

    assert plan.items[0].state is FileState.NAME_COLLISION
    assert plan.conflicts == plan.items
    assert [w.is_proposal for w in plan.writes] == [True]
    assert plan.recorded_after == ()


def test_tampering_with_a_protected_file_is_restored() -> None:
    desired = [whole("w.md", "workflow\n", cls=FileClass.PROTECTED)]
    first = build_plan(desired, {}, [])
    tree = apply(first, {}) | {p("w.md"): b"weakened\n"}

    second = build_plan(desired, tree, recorded_from(first))

    assert [(i.state, i.action) for i in second.items] == [(FileState.TAMPERED, Action.RESTORE)]
    assert apply(second, tree)[p("w.md")] == b"workflow\n"


def test_seeded_files_are_written_once_and_a_clash_becomes_a_proposal() -> None:
    created = build_plan([whole("s.md", "seed\n", owner=OwnerMode.SEEDED)], {}, [])
    clash = build_plan(
        [whole("s.md", "seed\n", owner=OwnerMode.SEEDED)], {p("s.md"): b"mine\n"}, []
    )

    assert created.items[0].action is Action.CREATE
    assert clash.items[0].action is Action.PROPOSE
    assert [w.is_proposal for w in clash.writes] == [True]
    assert clash.recorded_after == ()


def test_newer_seed_text_is_only_ever_a_proposal() -> None:
    first = build_plan([whole("s.md", "seed v1\n", owner=OwnerMode.SEEDED)], {}, [])
    tree = apply(first, {})

    second = build_plan(
        [whole("s.md", "seed v2\n", owner=OwnerMode.SEEDED)], tree, recorded_from(first)
    )

    assert second.items[0].action is Action.PROPOSE
    assert apply(second, tree)[p("s.md")] == b"seed v1\n"
    assert second.recorded_after == first.recorded_after


def test_blocks_are_inserted_into_an_existing_file_and_the_rest_is_kept() -> None:
    existing = {p("AGENTS.md"): b"# Project notes\n\nKeep me.\n"}

    plan = build_plan([block("AGENTS.md", "baseline", "text")], existing, [])
    result = apply(plan, existing)[p("AGENTS.md")].decode()

    assert result.startswith("# Project notes\n\nKeep me.\n")
    assert "<!-- orqlet:begin baseline v1 -->" in result


def test_two_blocks_in_one_file_are_planned_separately_and_written_once() -> None:
    desired = [
        block(".github/pr.md", "team-template", "team"),
        block(".github/pr.md", "orqlet-workflow", "wf"),
    ]

    plan = build_plan(desired, {}, [])

    assert len(plan.items) == 2
    assert [str(w.path) for w in plan.writes] == [".github/pr.md"]
    assert len(plan.recorded_after) == 2


def test_an_edited_block_conflicts_while_the_other_block_still_updates() -> None:
    first = build_plan(
        [block("pr.md", "team-template", "team v1"), block("pr.md", "orqlet-workflow", "wf v1")],
        {},
        [],
    )
    tree = apply(first, {})
    edited = tree[p("pr.md")].replace(b"team v1", b"team EDITED")
    tree[p("pr.md")] = edited

    second = build_plan(
        [block("pr.md", "team-template", "team v2"), block("pr.md", "orqlet-workflow", "wf v2")],
        tree,
        recorded_from(first),
    )

    by_block = {i.block_name: i for i in second.items}
    assert by_block["team-template"].action is Action.STOP
    assert by_block["orqlet-workflow"].action is Action.UPDATE
    result = apply(second, tree)[p("pr.md")].decode()
    assert "team EDITED" in result
    assert "wf v2" in result
    assert any(w.is_proposal and b"team v2" in (w.content or b"") for w in second.writes)


def test_broken_markers_stop_every_block_in_the_file_and_write_nothing() -> None:
    existing = {p("AGENTS.md"): b"<!-- orqlet:begin baseline v1 -->\nnever closed\n"}

    plan = build_plan([block("AGENTS.md", "baseline", "text")], existing, [])

    assert [i.action for i in plan.items] == [Action.STOP]
    assert plan.writes == ()
    assert "never closed" in plan.items[0].reason


def test_a_non_utf8_file_is_a_conflict_not_a_rewrite() -> None:
    plan = build_plan(
        [block("AGENTS.md", "baseline", "text")], {p("AGENTS.md"): b"\xff\xfe\x00"}, []
    )

    assert [i.action for i in plan.items] == [Action.STOP]
    assert plan.writes == ()


def test_crlf_in_a_whole_file_does_not_count_as_a_change() -> None:
    first = build_plan([whole("a.md", "one\ntwo\n")], {}, [])
    tree = {p("a.md"): b"one\r\ntwo\r\n"}

    second = build_plan([whole("a.md", "one\ntwo\n")], tree, recorded_from(first))

    assert second.is_empty
    assert second.items[0].state is FileState.UP_TO_DATE


def test_a_file_that_is_no_longer_rendered_is_removed_only_if_untouched() -> None:
    first = build_plan([whole("a.md", "one\n"), whole("b.md", "two\n")], {}, [])
    tree = apply(first, {}) | {p("b.md"): b"edited\n"}

    second = build_plan([], tree, recorded_from(first))

    states = {str(i.path): i.state for i in second.items}
    assert states == {"a.md": FileState.ORPHAN_REMOVE, "b.md": FileState.ORPHAN_REPORT}
    assert [(str(w.path), w.kind) for w in second.writes] == [("a.md", "delete")]
    assert [str(r.path) for r in second.recorded_after] == ["b.md"]


def test_a_block_that_is_no_longer_rendered_is_taken_out_of_a_shared_file() -> None:
    first = build_plan([block("AGENTS.md", "baseline", "text")], {p("AGENTS.md"): b"# Mine\n"}, [])
    tree = apply(first, {p("AGENTS.md"): b"# Mine\n"})

    second = build_plan([], tree, recorded_from(first))

    assert apply(second, tree)[p("AGENTS.md")] == b"# Mine\n\n"
    assert second.recorded_after == ()


def test_a_file_made_only_of_an_orphaned_block_is_deleted() -> None:
    first = build_plan([block("AGENTS.md", "baseline", "text")], {}, [])
    tree = apply(first, {})

    second = build_plan([], tree, recorded_from(first))

    assert [(str(w.path), w.kind) for w in second.writes] == [("AGENTS.md", "delete")]


def test_the_manifest_is_added_last_and_only_when_it_changes() -> None:
    plan = build_plan([whole("a.md", "one\n")], {}, [])
    lock = p(".orqlet/generated.lock.yaml")

    with_lock = plan.with_manifest(lock, b"lock v1\n", None)
    unchanged = with_lock.with_manifest(lock, b"lock v1\n", b"lock v1\n")

    assert with_lock.writes[-1].last
    assert str(with_lock.writes[-1].path) == ".orqlet/generated.lock.yaml"
    assert unchanged.writes == with_lock.writes


def test_the_plan_digest_changes_with_any_planned_byte() -> None:
    one = build_plan([whole("a.md", "one\n")], {}, [])
    two = build_plan([whole("a.md", "two\n")], {}, [])
    again = build_plan([whole("a.md", "one\n")], {}, [])

    assert one.digest == again.digest
    assert one.digest != two.digest


def test_two_renders_for_one_whole_file_are_a_plan_error() -> None:
    with pytest.raises(PlanError):
        build_plan([whole("a.md", "one\n"), whole("a.md", "two\n")], {}, [])


def test_a_proposal_that_is_already_on_disk_is_not_written_again() -> None:
    first = build_plan([whole("a.md", "ours\n")], {p("a.md"): b"theirs\n"}, [])
    proposal = first.writes[0]
    tree = {p("a.md"): b"theirs\n", proposal.path: proposal.content or b""}

    again = build_plan([whole("a.md", "ours\n")], tree, [])

    assert again.writes == ()


def test_long_paths_still_get_a_valid_proposal_name() -> None:
    long = "/".join(["d" * 40] * 6) + "/file.md"

    name = proposal_path(p(long), None).name

    assert len(name.encode()) <= 255
    assert name.endswith(".diff")


def test_recorded_entries_keep_the_block_markers_and_inputs_for_the_manifest() -> None:
    desired = Desired(
        p("AGENTS.md"),
        OwnerMode.SHARED_BLOCK,
        FileClass.PROTECTED,
        render_block("baseline", "workflow@1#h", "text").encode(),
        block_name="baseline",
        inputs=(("baseline", "1", sha256_hex(b"x")),),
    )

    (entry,) = build_plan([desired], {}, []).recorded_after

    assert entry.block == (
        "<!-- orqlet:begin baseline workflow@1#h -->",
        "<!-- orqlet:end baseline -->",
    )
    assert entry.inputs == (("baseline", "1", sha256_hex(b"x")),)
    assert entry.file_class is FileClass.PROTECTED
