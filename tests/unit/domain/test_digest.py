import json
from pathlib import Path
from typing import cast

import pytest

from orqlet.domain.digest import JsonValue, canonical_json, digest_of, sha256_hex
from orqlet.domain.errors import CanonicalJsonError

pytestmark = pytest.mark.unit

VECTORS = json.loads(
    (Path(__file__).parents[2] / "fixtures" / "rfc8785" / "vectors.json").read_text("utf-8")
)


def test_keys_are_sorted_by_utf16_code_units_not_code_points() -> None:
    sorting = VECTORS["sorting"]
    keys = [chr(cp) for cp in sorting["keys_as_code_points"]]
    data = dict.fromkeys(keys, 1)

    encoded = canonical_json(data).decode("utf-8")
    decoded_keys = list(json.loads(encoded))

    assert [ord(key) for key in decoded_keys] == sorting["expected_order_as_code_points"]
    # Plain code point order would put U+1F600 after U+FB33. UTF-16 puts it before.
    assert decoded_keys.index(chr(0x1F600)) < decoded_keys.index(chr(0xFB33))


@pytest.mark.parametrize("vector", VECTORS["strings"])
def test_string_escaping_matches_the_vectors(vector: dict[str, str]) -> None:
    assert canonical_json(vector["input"]).decode("utf-8") == vector["expected"]


@pytest.mark.parametrize("vector", VECTORS["integers"])
def test_integers_are_written_as_plain_decimals(vector: dict[str, int | str]) -> None:
    assert canonical_json(vector["input"]).decode("utf-8") == vector["expected"]


@pytest.mark.parametrize("vector", VECTORS["rejected"], ids=lambda v: v["label"])
def test_values_outside_the_subset_are_rejected(vector: dict[str, str]) -> None:
    value = json.loads(vector["json"])
    with pytest.raises(CanonicalJsonError):
        canonical_json(value)


def test_booleans_null_and_nesting_have_no_whitespace() -> None:
    value: JsonValue = {"b": [True, False, None], "a": {"y": 2, "x": 1}}
    assert canonical_json(value) == b'{"a":{"x":1,"y":2},"b":[true,false,null]}'


def test_bytes_and_non_string_keys_are_rejected() -> None:
    with pytest.raises(CanonicalJsonError):
        canonical_json(b"raw")
    with pytest.raises(CanonicalJsonError):
        canonical_json(cast("JsonValue", {1: "x"}))


def test_sha256_of_a_known_input() -> None:
    assert sha256_hex(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_digest_of_hashes_the_canonical_form() -> None:
    assert digest_of({"b": 1, "a": 2}) == sha256_hex(b'{"a":2,"b":1}')
