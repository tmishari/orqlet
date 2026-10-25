import pytest

from orqlet.domain.errors import InvalidVersion
from orqlet.domain.versions import (
    Version,
    WorkflowRelease,
    check_release_history,
    is_below_floor,
    is_downgrade,
)

pytestmark = pytest.mark.unit

DIGEST = "a" * 64


def _release(version: str, level: int) -> WorkflowRelease:
    return WorkflowRelease(Version.parse(version), DIGEST, level)


def test_versions_parse_and_order_numerically() -> None:
    assert Version.parse("1.10.0") > Version.parse("1.9.9")
    assert str(Version.parse("0.1.0")) == "0.1.0"


@pytest.mark.parametrize("text", ["1", "1.2", "1.2.3.4", "01.2.3", "v1.2.3", "1.2.x", ""])
def test_malformed_versions_are_rejected(text: str) -> None:
    with pytest.raises(InvalidVersion):
        Version.parse(text)


def test_floor_comparison() -> None:
    assert is_below_floor(Version.parse("1.0.0"), Version.parse("1.1.0"))
    assert not is_below_floor(Version.parse("1.1.0"), Version.parse("1.1.0"))


def test_a_lower_version_or_lower_controls_level_is_a_downgrade() -> None:
    current = _release("1.2.0", 3)
    assert is_downgrade(current, _release("1.1.0", 3))
    assert is_downgrade(current, _release("1.3.0", 2))
    assert not is_downgrade(current, _release("1.3.0", 3))
    assert not is_downgrade(current, _release("1.2.0", 3))


def test_a_release_needs_a_real_digest_and_a_level() -> None:
    with pytest.raises(InvalidVersion):
        WorkflowRelease(Version.parse("1.0.0"), "short", 1)
    with pytest.raises(InvalidVersion):
        WorkflowRelease(Version.parse("1.0.0"), DIGEST, -1)


class TestReleaseHistory:
    HASH_A = "a" * 64
    HASH_B = "b" * 64

    def release(self, version: str, digest: str, level: int = 1) -> WorkflowRelease:
        return WorkflowRelease(Version.parse(version), digest, level)

    def test_a_new_version_after_the_history_is_fine(self) -> None:
        history = [self.release("1.0.0", self.HASH_A)]

        assert check_release_history(self.release("1.1.0", self.HASH_B), history) == ()

    def test_an_empty_history_accepts_anything(self) -> None:
        assert check_release_history(self.release("0.1.0", self.HASH_A), []) == ()

    def test_the_same_release_again_is_fine(self) -> None:
        history = [self.release("1.0.0", self.HASH_A)]

        assert check_release_history(self.release("1.0.0", self.HASH_A), history) == ()

    def test_a_changed_digest_under_the_same_version_is_a_release_defect(self) -> None:
        history = [self.release("1.0.0", self.HASH_A)]

        problems = check_release_history(self.release("1.0.0", self.HASH_B), history)

        assert any("different digest" in problem for problem in problems)

    def test_an_older_version_or_a_lower_controls_level_is_a_downgrade(self) -> None:
        history = [self.release("1.2.0", self.HASH_A, level=3)]

        problems = check_release_history(self.release("1.1.0", self.HASH_B, level=2), history)

        assert len(problems) == 2

    def test_a_duplicated_history_entry_is_reported(self) -> None:
        history = [self.release("1.0.0", self.HASH_A), self.release("1.0.0", self.HASH_A)]

        assert check_release_history(self.release("1.0.0", self.HASH_A), history)
