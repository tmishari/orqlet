"""The monotone resolver: adding any layer never shrinks the requirement set (acceptance item)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.domain.resolver import (
    Enforcement,
    Layer,
    Level,
    RuleSpec,
    Scope,
    Waiver,
    WeakeningError,
    dominates,
    resolve,
)

pytestmark = pytest.mark.unit

ids = st.sampled_from(["R1", "R2", "R3", "R4"])
scope_values = st.frozensets(st.sampled_from(["a", "b", "c"]), max_size=3)
scopes = st.builds(Scope, scope_values, scope_values, scope_values)
rules = st.builds(
    RuleSpec,
    ids,
    st.sampled_from(Level),
    st.sampled_from(Waiver),
    st.sampled_from(Enforcement),
    scopes,
    st.just("text"),
    st.just("layer"),
)


@st.composite
def layers(draw: st.DrawFn) -> Layer:
    chosen = draw(st.lists(rules, max_size=4, unique_by=lambda r: r.id))
    return Layer("layer", tuple(chosen))


@given(st.lists(layers(), max_size=3), layers())
def test_adding_a_layer_never_shrinks_the_requirement_set(base: list[Layer], extra: Layer) -> None:
    try:
        before = resolve(base)
        after = resolve([*base, extra])
    except WeakeningError:
        return  # a weakening is refused outright, which is also never a shrink
    assert dominates(after, before)


@given(layers())
def test_a_single_valid_layer_resolves_to_exactly_its_rules(layer: Layer) -> None:
    result = resolve([layer])

    assert set(result) == {r.id for r in layer.rules}
    assert list(result) == sorted(result)


@given(st.lists(layers(), max_size=3))
def test_resolving_twice_gives_the_same_result(all_layers: list[Layer]) -> None:
    try:
        first = resolve(all_layers)
    except WeakeningError:
        return
    assert resolve(all_layers) == first
