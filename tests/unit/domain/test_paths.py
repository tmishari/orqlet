import pytest

from orqlet.domain.errors import InvalidPath
from orqlet.domain.paths import CanonicalPath

pytestmark = pytest.mark.unit


def test_a_simple_relative_path_is_kept() -> None:
    path = CanonicalPath.parse("src/pkg/mod.py")
    assert path.parts == ("src", "pkg", "mod.py")
    assert str(path) == "src/pkg/mod.py"
    assert path.name == "mod.py"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "/etc/passwd",
        "a//b",
        "a/",
        "a/./b",
        "a/../b",
        "..",
        "a\\b",
        "c:/x",
        "dir/name.",
        "dir/name ",
        "aux",
        "src/NUL.txt",
        "COM3/readme",
        ".git/config",
        "src/.GIT/hooks",
        "bad\x00name",
        "bidi\u202ename",
        "tab\there",
        "x" * 300,
    ],
)
def test_unsafe_paths_are_rejected(raw: str) -> None:
    with pytest.raises(InvalidPath):
        CanonicalPath.parse(raw)


def test_unicode_is_normalised_to_nfc() -> None:
    nfd = "docs/cafe\u0301.md"
    nfc = "docs/caf\u00e9.md"
    assert CanonicalPath.parse(nfd).parts == CanonicalPath.parse(nfc).parts


def test_case_variants_share_one_key_but_keep_their_spelling() -> None:
    upper = CanonicalPath.parse("SRC/pkg/New.py")
    lower = CanonicalPath.parse("src/pkg/new.py")
    assert upper.key == lower.key
    assert upper != lower
    assert upper.conflicts_with(lower)


def test_a_file_and_a_directory_conflict() -> None:
    file_path = CanonicalPath.parse("pkg/util")
    nested = CanonicalPath.parse("pkg/util/x.py")
    other = CanonicalPath.parse("pkg/other.py")
    assert file_path.conflicts_with(nested)
    assert nested.conflicts_with(file_path)
    assert not file_path.conflicts_with(other)


def test_is_inside_and_parent_and_child() -> None:
    directory = CanonicalPath.parse(".orqlet")
    inside = directory.child("project-profile.yaml")
    assert inside.is_inside(directory)
    assert not directory.is_inside(directory)
    assert inside.parent == directory
    assert directory.parent is None


def test_sort_key_orders_by_folded_key_then_spelling() -> None:
    paths = [CanonicalPath.parse(p) for p in ("b.txt", "A.txt", "a.txt")]
    assert [str(p) for p in sorted(paths, key=CanonicalPath.sort_key)] == [
        "A.txt",
        "a.txt",
        "b.txt",
    ]
