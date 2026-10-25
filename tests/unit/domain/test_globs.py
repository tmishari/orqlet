import pytest

from orqlet.domain.globs import glob_match

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("src/**", "src/a/b.py", True),
        ("src/**", "src", True),
        ("src/**/*.py", "src/a/b/c.py", True),
        ("src/**/*.py", "src/c.py", True),
        ("src/*.py", "src/a/c.py", False),
        ("*.md", "README.md", True),
        ("*.md", "docs/README.md", False),
        ("**/*.md", "docs/deep/README.md", True),
        ("auth/**", "authz/x.py", False),
        ("a?c", "abc", True),
        ("a?c", "a/c", False),
        ("README.md", "readme.md", False),
        ("**", "anything/at/all", True),
        ("", "", True),
    ],
)
def test_glob_match(pattern: str, path: str, expected: bool) -> None:
    assert glob_match(pattern, path) is expected
