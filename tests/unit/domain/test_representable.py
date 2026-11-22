"""What may reach an agent's context (task one-command-setup, phase P-4, AC-4).

Every test cites its `expected_behavior_source`: AC-4 is the acceptance criterion of phase P-4 in
docs/design/one-command-setup/plan.yaml; ADR-001 decision 3 and ADR-004 decision 1a are in
docs/design/one-command-setup/design/; "the interface" is the one that the Coder gave for P-4
(`orqlet.domain.representable`: `representable_version`, `representable_path`,
`PATH_NOT_REPRESENTABLE` and `MAX_PATH_CHARACTERS`).

HOW THESE TESTS WERE WRITTEN. The Tester of P-4 wrote them from the acceptance criteria and the
interface, before the implementation was reviewed. A value that breaks a rule is `None`; a value
that passes is returned exactly as given, never stripped, cut or normalised.
"""

from __future__ import annotations

import unicodedata

import pytest

from orqlet.domain.representable import (
    MAX_PATH_CHARACTERS,
    PATH_NOT_REPRESENTABLE,
    representable_path,
    representable_version,
)

pytestmark = pytest.mark.unit


def test_the_closed_reason_and_the_length_limit() -> None:
    """AC-4, ADR-001 decision 3: the reason is `path-not-representable`, the limit 200."""
    assert PATH_NOT_REPRESENTABLE == "path-not-representable"
    assert MAX_PATH_CHARACTERS == 200


# --- versions -------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["0.0.0", "0.5.0", "1.10.0", "12.0.345"])
def test_a_major_minor_patch_version_is_returned_unchanged(text: str) -> None:
    """AC-4, ADR-004 decision 1a: a version that matches major.minor.patch is shown as it is."""
    assert representable_version(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "",
        "1",
        "1.2",
        "1.2.3.4",
        "01.2.3",
        "1.02.3",
        "v1.2.3",
        "1.2.x",
        "1.2.3-rc1",
        " 1.2.3",
        "1.2.3 ",
        "1.2.3\n",
        "1.2.3\u202e",
        "\u200b1.2.3",
    ],
)
def test_a_version_that_does_not_match_is_null(text: str) -> None:
    """AC-4, ADR-001 decision 3: anything but major.minor.patch, whitespace included, is null."""
    assert representable_version(text) is None


@pytest.mark.parametrize("text", ["\uff11.2.3", "1.\u0663.0", "1\u0663.2.3"])
def test_a_version_with_digits_outside_ascii_is_null(text: str) -> None:
    """AC-4; the interface: major.minor.patch in ASCII digits (fullwidth, Arabic-Indic refused)."""
    assert representable_version(text) is None


@pytest.mark.parametrize("value", [None, 5, 1.2, True, b"1.2.3", ["1.2.3"], {"v": "1.2.3"}])
def test_a_version_that_is_not_text_is_null(value: object) -> None:
    """AC-4; the interface: a value that is not a str is null (a lock may hold any YAML type)."""
    assert representable_version(value) is None


# --- paths ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "/work/repo",
        "C:\\Users\\person\\repo",
        "/home/zo\u00eb/\u30d7\u30ed\u30b8\u30a7\u30af\u30c8",
        "/work/my repo",
        " /work/repo ",
        "/work/caf\u0065\u0301",
    ],
)
def test_a_plain_path_is_returned_exactly_as_given(text: str) -> None:
    """AC-4, ADR-001 decision 3: printed as it really is; no stripping and no normalisation."""
    result = representable_path(text)

    assert result == text
    assert result is not None
    assert len(result) == len(text)


def test_a_decomposed_path_is_not_normalised() -> None:
    """AC-4, ADR-001 decision 3: never altered, so a decomposed spelling stays decomposed."""
    text = "/work/cafe\u0301"

    assert representable_path(text) == text
    assert representable_path(text) != unicodedata.normalize("NFC", text)


# One character of each forbidden Unicode category (the interface): Cc, Cf (bidirectional,
# zero-width and other format marks), Cs, Co, Zl and Zp.
FORBIDDEN = {
    "nul": "\x00",
    "tab": "\t",
    "line-feed": "\n",
    "carriage-return": "\r",
    "escape": "\x1b",
    "delete": "\x7f",
    "next-line-c1": "\x85",
    "lrm": "\u200e",
    "rlm": "\u200f",
    "lre": "\u202a",
    "rle": "\u202b",
    "pdf": "\u202c",
    "lro": "\u202d",
    "rlo": "\u202e",
    "lri": "\u2066",
    "rli": "\u2067",
    "fsi": "\u2068",
    "pdi": "\u2069",
    "arabic-letter-mark": "\u061c",
    "zero-width-space": "\u200b",
    "zero-width-non-joiner": "\u200c",
    "zero-width-joiner": "\u200d",
    "byte-order-mark": "\ufeff",
    "soft-hyphen": "\u00ad",
    "lone-surrogate": "\udcff",
    "private-use": "\ue000",
    "line-separator": "\u2028",
    "paragraph-separator": "\u2029",
}


@pytest.mark.parametrize("character", list(FORBIDDEN.values()), ids=list(FORBIDDEN))
@pytest.mark.parametrize("where", ["start", "middle", "end"])
def test_a_path_with_a_hidden_character_is_null(character: str, where: str) -> None:
    """AC-4, ADR-001 decision 3; the interface: Cc, Cf, Cs, Co, Zl or Zp anywhere gives null."""
    assert unicodedata.category(character) in {"Cc", "Cf", "Cs", "Co", "Zl", "Zp"}
    text = {
        "start": f"{character}/work/repo",
        "middle": f"/work/re{character}po",
        "end": f"/work/repo{character}",
    }[where]

    assert representable_path(text) is None


def test_a_path_of_exactly_200_characters_is_representable() -> None:
    """AC-4, ADR-001 decision 3; the interface: exactly 200 characters is representable."""
    text = "/" + "a" * 199
    assert len(text) == 200

    assert representable_path(text) == text


def test_a_path_of_201_characters_is_null_and_never_cut() -> None:
    """AC-4, ADR-001 decision 3: longer than 200 characters is null, never shortened."""
    text = "/" + "a" * 200
    assert len(text) == 201

    assert representable_path(text) is None


def test_the_limit_counts_characters_not_bytes() -> None:
    """The interface: the limit is 200 characters, so 200 two-byte letters still pass."""
    text = "\u00e9" * 200
    assert len(text.encode("utf-8")) == 400

    assert representable_path(text) == text
    assert representable_path(text + "\u00e9") is None


def test_an_empty_path_is_null() -> None:
    """The interface: the empty text is not representable."""
    assert representable_path("") is None


@pytest.mark.parametrize(
    "character",
    [
        "\ufe00",
        "\ufe0f",
        "\U000e0100",
        "\U000e01ef",
        "\u115f",
        "\u1160",
        "\u3164",
        "\uffa0",
        "\u2800",
        "\u034f",
        "\u17b4",
        "\u17b5",
        "\u180b",
        "\u180d",
        "\u180f",
        "\U000e0080",
    ],
    ids=[
        "vs1",
        "vs16",
        "vs17",
        "vs256",
        "hangul-choseong",
        "hangul-jungseong",
        "hangul",
        "halfwidth-hangul",
        "braille",
        "grapheme-joiner",
        "khmer-aq",
        "khmer-aa",
        "mongolian-fvs1",
        "mongolian-fvs3",
        "mongolian-fvs4",
        "unassigned",
    ],
)
def test_invisible_characters_outside_the_hidden_categories_are_null(character: str) -> None:
    """Q-69 and Q-70, the answers to the P-4 security review: these are refused too."""
    assert representable_path(f"/home/a{character}b") is None


def test_combining_accents_stay_representable() -> None:
    """The person's answer to the P-4 security review: decomposed names keep their accents."""
    text = "/home/cafe\u0301"

    assert representable_path(text) == text


def test_a_version_part_beyond_the_integer_digit_limit_is_null() -> None:
    """Security review of P-4, round 2: a hostile lock with a 5,000-digit part gives null."""
    assert representable_version("1" * 5000 + ".0.0") is None
