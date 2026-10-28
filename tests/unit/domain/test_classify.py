"""The three-way table of proposal section 9.3, one row per test."""

import pytest

from orqlet.domain.classify import FileState, classify
from orqlet.domain.ownership import FileClass, OwnerMode

pytestmark = pytest.mark.unit

A, B, C = "a" * 64, "b" * 64, "c" * 64


def state(
    *,
    current: str | None,
    recorded: str | None,
    new: str | None,
    owner: OwnerMode = OwnerMode.ORQLET,
    file_class: FileClass | None = FileClass.GENERATED,
) -> FileState:
    return classify(owner, file_class, current=current, recorded=recorded, new=new)


@pytest.mark.parametrize(
    ("current", "recorded", "new", "expected"),
    [
        (A, A, A, FileState.UP_TO_DATE),
        (A, A, B, FileState.SAFE_UPDATE),
        (B, A, A, FileState.USER_EDIT_ONLY),
        (B, A, C, FileState.CONFLICT),
        (None, None, A, FileState.NEW),
        (A, None, A, FileState.UP_TO_DATE),
        (B, None, A, FileState.NAME_COLLISION),
        (A, A, None, FileState.ORPHAN_REMOVE),
        (B, A, None, FileState.ORPHAN_REPORT),
        (None, A, None, FileState.UP_TO_DATE),
        (B, A, B, FileState.UP_TO_DATE),  # the team already made the same change
    ],
)
def test_generated_files(
    current: str | None, recorded: str | None, new: str | None, expected: FileState
) -> None:
    assert state(current=current, recorded=recorded, new=new) is expected


def test_a_protected_file_that_differs_from_what_orqlet_wrote_is_tampered() -> None:
    result = state(current=B, recorded=A, new=A, file_class=FileClass.PROTECTED)

    assert result is FileState.TAMPERED


def test_a_deleted_protected_file_is_tampered_too() -> None:
    assert (
        state(current=None, recorded=A, new=A, file_class=FileClass.PROTECTED) is FileState.TAMPERED
    )


def test_a_protected_file_that_is_merely_out_of_date_updates_safely() -> None:
    assert (
        state(current=A, recorded=A, new=B, file_class=FileClass.PROTECTED) is FileState.SAFE_UPDATE
    )


def test_a_deleted_generated_file_is_the_teams_choice_when_the_render_did_not_change() -> None:
    assert state(current=None, recorded=A, new=A) is FileState.USER_EDIT_ONLY
    assert state(current=None, recorded=A, new=B) is FileState.CONFLICT


@pytest.mark.parametrize(
    ("current", "recorded", "new", "expected"),
    [
        (None, None, A, FileState.NEW),
        (A, None, A, FileState.UP_TO_DATE),
        (B, None, A, FileState.SEEDED_PROPOSAL),  # a name clash: propose, never overwrite
        (A, A, A, FileState.SEEDED_KEEP),
        (B, A, A, FileState.SEEDED_KEEP),  # the team edited it: never drift
        (A, A, B, FileState.SEEDED_PROPOSAL),  # newer seed text: a proposal only
        (None, A, B, FileState.SEEDED_KEEP),  # the team deleted it: not brought back
        (A, A, None, FileState.SEEDED_KEEP),  # not removed
        # AC-7, ADR-002 decision 5, EC-55: the team's edit already equals the seed text, so no
        # proposal is needed and the record advances (a hand edit or a merged lock line)
        (B, A, B, FileState.UP_TO_DATE),
    ],
)
def test_seeded_files_are_team_owned_after_the_first_write(
    current: str | None, recorded: str | None, new: str | None, expected: FileState
) -> None:
    result = state(
        current=current, recorded=recorded, new=new, owner=OwnerMode.SEEDED, file_class=None
    )

    assert result is expected


def test_a_user_owned_entry_is_never_touched() -> None:
    assert state(current=B, recorded=A, new=C, owner=OwnerMode.USER) is FileState.SEEDED_KEEP
