"""D1, D2 and D3 from the scope, and the rule that nobody can lower a class."""

from __future__ import annotations

import pytest

from orqlet.domain.change_class import (
    ChangeClass,
    ChangePolicy,
    ChangeScope,
    effective_class,
    required_artifact_groups,
    shared_directory,
    trigger_class,
)

pytestmark = pytest.mark.unit

POLICY = ChangePolicy(security_globs=("src/auth/**",), d3_globs=("migrations/**",))


def scope(*paths: str, **flags: bool) -> ChangeScope:
    return ChangeScope(
        paths=paths or ("src/pkg/mod.py",), one_module=flags.pop("one_module", True), **flags
    )


def test_a_small_change_inside_one_module_is_d1() -> None:
    result = trigger_class(scope("src/pkg/mod.py"), POLICY)

    assert (result.change_class, result.reasons) == (ChangeClass.D1, ())


@pytest.mark.parametrize(
    "flags",
    [
        {"one_module": False},
        {"changes_interface": True},
        {"changes_dependency": True},
        {"changes_persisted_format": True},
        {"changes_configuration": True},
    ],
)
def test_each_condition_that_breaks_d1_makes_it_d2(flags: dict[str, bool]) -> None:
    assert trigger_class(scope(**flags), POLICY).change_class is ChangeClass.D2


def test_more_files_than_the_ceiling_is_d2() -> None:
    paths = tuple(f"src/pkg/m{n}.py" for n in range(11))

    result = trigger_class(scope(*paths), POLICY)

    assert result.change_class is ChangeClass.D2
    assert "more than 10 files" in result.reasons[0]


def test_a_lower_project_ceiling_applies() -> None:
    paths = ("src/pkg/a.py", "src/pkg/b.py", "src/pkg/c.py")

    result = trigger_class(scope(*paths), ChangePolicy(d1_max_files=2))

    assert result.change_class is ChangeClass.D2


@pytest.mark.parametrize(
    "flags",
    [
        {"trust_boundary": True},
        {"security_domain": True},
        {"data_model": True},
        {"infrastructure": True},
        {"cross_service_contract": True},
    ],
)
def test_each_d3_trigger_makes_it_d3(flags: dict[str, bool]) -> None:
    assert trigger_class(scope(**flags), POLICY).change_class is ChangeClass.D3


@pytest.mark.parametrize("path", ["src/auth/login.py", "migrations/0001_init.sql"])
def test_a_path_on_a_d3_or_security_glob_is_d3_and_named_in_the_reasons(path: str) -> None:
    result = trigger_class(scope(path), POLICY)

    assert result.change_class is ChangeClass.D3
    assert path in result.reasons[0]


def test_the_effective_class_is_the_maximum_and_cannot_be_lowered() -> None:
    assert effective_class(ChangeClass.D2, ChangeClass.D1) is ChangeClass.D2
    assert effective_class(ChangeClass.D1, ChangeClass.D3) is ChangeClass.D3
    assert effective_class(ChangeClass.D1, ChangeClass.D1, ChangeClass.D2) is ChangeClass.D2
    assert effective_class(ChangeClass.D3, ChangeClass.D1, ChangeClass.D1) is ChangeClass.D3


def test_classes_are_ordered_and_parsed_by_name() -> None:
    assert ChangeClass.D1 < ChangeClass.D2 < ChangeClass.D3
    assert ChangeClass.parse("D2") is ChangeClass.D2
    with pytest.raises(ValueError, match="D1, D2 or D3"):
        ChangeClass.parse("D4")


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        (("src/pkg/mod.py",), ("src", "pkg")),
        (("src/pkg/**",), ("src", "pkg")),
        (("src/pkg/a.py", "src/pkg/b.py"), ("src", "pkg")),
        (("src/pkg/a.py", "src/other/b.py"), ("src",)),
        (("src/*/x.py",), ("src",)),
        (("pyproject.toml",), ()),
        (("**",), ()),
        (("src/a.py", "docs/b.md"), ()),
        ((), ()),
    ],
)
def test_the_shared_directory_is_the_common_literal_prefix(
    patterns: tuple[str, ...], expected: tuple[str, ...]
) -> None:
    assert shared_directory(patterns) == expected


def test_each_class_requires_more_than_the_one_before() -> None:
    d1, d2, d3 = (required_artifact_groups(c) for c in ChangeClass)

    assert frozenset({"c4-component"}) in d1
    assert set(d1) < set(d2) | {frozenset({"adr", "adr-not-required"})}
    assert frozenset({"c4-context"}) in d3
    assert frozenset({"adr"}) in d3
    assert frozenset({"adr", "adr-not-required"}) not in d3  # D3 needs a real ADR
