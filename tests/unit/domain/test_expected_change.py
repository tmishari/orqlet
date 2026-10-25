"""The approved expected change against what an implementation did (proposal 17.4.1, FM-A)."""

from __future__ import annotations

import pytest

from orqlet.domain.dependencies import DependencyDelta
from orqlet.domain.expected_change import (
    Actual,
    ApiDelta,
    Expectation,
    Outcome,
    api_delta,
    compare,
)
from orqlet.domain.python_api import Symbol, canonical_signature

pytestmark = pytest.mark.unit

DECLARED = "def create_order(customer_id: str, items: list[Item]) -> Order"


def symbol(text: str = DECLARED) -> Symbol:
    canonical = canonical_signature(text)
    assert canonical is not None
    name = canonical.split("(")[0].split()[-1]
    return Symbol(name, "function", canonical)


def api_change(action: str = "add", value: str = DECLARED, **kw: object) -> Expectation:
    return Expectation(
        id=str(kw.get("id", "EC-1")),
        surface="public-api",
        action=action,
        identity="pkg.service.create_order",
        value=value,
        verification="extractor",
    )


def outcomes(results) -> list[tuple[str | None, Outcome]]:  # type: ignore[no-untyped-def]
    return [(r.id, r.outcome) for r in results]


def added(name: str = "pkg.service.create_order", text: str = DECLARED) -> ApiDelta:
    return ApiDelta(added={name: symbol(text)})


def test_fm_a01_adding_exactly_the_declared_signature_is_implemented_as_designed() -> None:
    results = compare([api_change()], frozenset({"EC-1"}), Actual(api=added()))

    assert outcomes(results) == [("EC-1", Outcome.IMPLEMENTED)]


def test_the_declared_text_may_be_written_loosely() -> None:
    loose = "def create_order(customer_id:str,items:list[Item])->Order"

    results = compare([api_change(value=loose)], frozenset(), Actual(api=added()))

    assert outcomes(results) == [("EC-1", Outcome.IMPLEMENTED)]


def test_fm_a02_a_second_public_symbol_that_no_entry_covers_is_additional() -> None:
    delta = ApiDelta(
        added={
            "pkg.service.create_order": symbol(),
            "pkg.service.refund": symbol("def refund(order: Order) -> None"),
        }
    )

    results = compare([api_change()], frozenset({"EC-1"}), Actual(api=delta))

    assert outcomes(results) == [("EC-1", Outcome.IMPLEMENTED), (None, Outcome.ADDITIONAL)]
    assert "refund" in results[1].detail


def test_a_different_signature_is_a_deviation_and_says_both() -> None:
    delta = added(text="def create_order(customer_id: int) -> Order")

    (result,) = compare([api_change()], frozenset({"EC-1"}), Actual(api=delta))

    assert result.outcome is Outcome.DEVIATION
    assert "declared" in result.detail


def test_a_change_and_a_removal_are_compared_with_their_own_part_of_the_delta() -> None:
    changed = ApiDelta(changed={"pkg.service.create_order": symbol()})
    removed = ApiDelta(removed={"pkg.service.create_order": symbol()})

    assert outcomes(compare([api_change("change")], frozenset(), Actual(api=changed))) == [
        ("EC-1", Outcome.IMPLEMENTED)
    ]
    assert outcomes(compare([api_change("remove")], frozenset(), Actual(api=removed))) == [
        ("EC-1", Outcome.IMPLEMENTED)
    ]
    wrong_kind = compare([api_change("add")], frozenset(), Actual(api=changed))
    assert outcomes(wrong_kind) == [("EC-1", Outcome.DEVIATION)]
    assert "changed, but the design says add" in wrong_kind[0].detail


def test_an_entry_the_phase_does_not_select_is_pending_and_one_it_selects_is_not_delivered() -> (
    None
):
    empty = Actual(api=ApiDelta())

    assert outcomes(compare([api_change()], frozenset(), empty)) == [("EC-1", Outcome.PENDING)]
    assert outcomes(compare([api_change()], frozenset({"EC-1"}), empty)) == [
        ("EC-1", Outcome.NOT_DELIVERED)
    ]


def test_a_stage_selected_by_the_phase_replaces_the_final_expectation() -> None:
    staged = Expectation(
        id="EC-1",
        surface="public-api",
        action="add",
        identity="pkg.service.create_order",
        value=DECLARED,
        verification="extractor",
        stages={"S-1": "def create_order(customer_id: str) -> Order"},
    )
    delta = added(text="def create_order(customer_id: str) -> Order")

    first = compare([staged], frozenset({"EC-1@S-1"}), Actual(api=delta))
    final = compare([staged], frozenset({"EC-1"}), Actual(api=delta))

    assert outcomes(first) == [("EC-1", Outcome.IMPLEMENTED)]
    assert outcomes(final) == [("EC-1", Outcome.DEVIATION)]


def test_a_surface_that_could_not_be_extracted_is_manual() -> None:
    assert outcomes(compare([api_change()], frozenset(), Actual(api=None))) == [
        ("EC-1", Outcome.MANUAL)
    ]


def test_an_entry_declared_manual_is_never_compared() -> None:
    manual = Expectation("EC-2", "http-contract", "add", "GET /x", "delta", "manual")

    assert outcomes(compare([manual], frozenset(), Actual())) == [("EC-2", Outcome.MANUAL)]


def dependency(action: str = "add", value: str = ">=2") -> Expectation:
    return Expectation("EC-3", "dependency", action, "Requests", value, "extractor")


def test_fm_a06_a_dependency_that_matches_its_declaration_is_implemented() -> None:
    delta = DependencyDelta(added={"requests": ">=2"})

    assert outcomes(compare([dependency()], frozenset({"EC-3"}), Actual(dependencies=delta))) == [
        ("EC-3", Outcome.IMPLEMENTED)
    ]


def test_fm_a06_a_different_specifier_or_package_is_a_deviation_or_additional() -> None:
    wrong_spec = DependencyDelta(added={"requests": ">=3"})
    other_package = DependencyDelta(added={"httpx": ">=2"})

    assert outcomes(
        compare([dependency()], frozenset({"EC-3"}), Actual(dependencies=wrong_spec))
    ) == [("EC-3", Outcome.DEVIATION)]
    assert outcomes(
        compare([dependency()], frozenset({"EC-3"}), Actual(dependencies=other_package))
    ) == [("EC-3", Outcome.NOT_DELIVERED), (None, Outcome.ADDITIONAL)]


def test_a_bump_and_a_removal_of_a_dependency() -> None:
    bumped = DependencyDelta(changed={"requests": (">=1", ">=2")})
    removed = DependencyDelta(removed={"requests": ">=1"})

    assert outcomes(compare([dependency("change")], frozenset(), Actual(dependencies=bumped))) == [
        ("EC-3", Outcome.IMPLEMENTED)
    ]
    assert outcomes(compare([dependency("remove")], frozenset(), Actual(dependencies=removed))) == [
        ("EC-3", Outcome.IMPLEMENTED)
    ]


def test_a_changed_source_setting_is_additional_unless_nothing_changed() -> None:
    delta = DependencyDelta(source_changes=("uv.sources.internal",))

    (result,) = compare([], frozenset(), Actual(dependencies=delta))

    assert (result.outcome, "uv.sources.internal" in result.detail) == (Outcome.ADDITIONAL, True)


def test_fm_a06_a_lockfile_package_outside_the_expected_ones_is_additional() -> None:
    actual = Actual(lock_added=frozenset({"requests", "idna", "urllib3"}))

    results = compare([], frozenset(), actual, expected_lock_packages=["idna"])

    assert [r.detail for r in results if r.outcome is Outcome.ADDITIONAL] == [
        "lockfile package requests was added, outside expected_lock_packages",
        "lockfile package urllib3 was added, outside expected_lock_packages",
    ]


def test_the_direct_dependency_itself_may_appear_in_the_lockfile() -> None:
    delta = DependencyDelta(added={"requests": ">=2"})
    actual = Actual(dependencies=delta, lock_added=frozenset({"requests"}))

    assert outcomes(compare([dependency()], frozenset({"EC-3"}), actual)) == [
        ("EC-3", Outcome.IMPLEMENTED)
    ]


def security() -> Expectation:
    return Expectation(
        "EC-4", "security", "change", "login", "src/auth/login.py, src/auth/token.py", "extractor"
    )


def test_fm_a04_touching_security_paths_outside_the_declared_ones_is_a_deviation() -> None:
    within = Actual(security_paths=("src/auth/login.py",))
    outside = Actual(security_paths=("src/auth/login.py", "src/auth/crypto.py"))

    assert outcomes(compare([security()], frozenset({"EC-4"}), within)) == [
        ("EC-4", Outcome.IMPLEMENTED)
    ]
    (result,) = compare([security()], frozenset({"EC-4"}), outside)
    assert result.outcome is Outcome.DEVIATION
    assert "src/auth/crypto.py" in result.detail


def test_fm_a04_an_unexpected_change_on_a_security_path_is_additional() -> None:
    (result,) = compare([], frozenset(), Actual(security_paths=("src/auth/crypto.py",)))

    assert result.outcome is Outcome.ADDITIONAL


def test_fm_a03_a_new_contract_or_migration_file_the_design_did_not_declare_is_additional() -> None:
    (result,) = compare([], frozenset(), Actual(undeclared_files=("db/migrations/0002.sql",)))

    assert (result.outcome, result.surface) == (Outcome.ADDITIONAL, "contract")


def test_the_api_delta_lists_added_removed_and_changed_symbols() -> None:
    before = {"a": symbol("def a(x: int) -> int"), "b": symbol("def b() -> None")}
    after = {"a": symbol("def a(x: str) -> int"), "c": symbol("def c() -> None")}

    delta = api_delta(before, after)

    assert (set(delta.added), set(delta.removed), set(delta.changed)) == ({"c"}, {"b"}, {"a"})
