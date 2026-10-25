import json
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orqlet.domain.digest import JsonValue, canonical_json, digest_of

pytestmark = pytest.mark.unit

_text = st.text(
    alphabet=st.characters(exclude_categories=["Cs"]),
    max_size=12,
)
_scalars = st.none() | st.booleans() | st.integers(-(2**53 - 1), 2**53 - 1) | _text
_values = st.recursive(
    _scalars,
    lambda children: st.lists(children, max_size=4) | st.dictionaries(_text, children, max_size=4),
    max_leaves=12,
)


def _shuffled(value: JsonValue, rng: random.Random) -> JsonValue:
    if isinstance(value, dict):
        items = list(value.items())
        rng.shuffle(items)
        return {key: _shuffled(item, rng) for key, item in items}
    if isinstance(value, list):
        return [_shuffled(item, rng) for item in value]
    return value


@given(_values, st.integers(0, 10_000))
def test_digest_does_not_depend_on_key_order(value: JsonValue, seed: int) -> None:
    assert digest_of(value) == digest_of(_shuffled(value, random.Random(seed)))


@given(_values)
def test_canonical_form_round_trips_through_a_json_parser(value: JsonValue) -> None:
    assert json.loads(canonical_json(value)) == value
