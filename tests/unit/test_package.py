import re

import pytest

import orqlet

pytestmark = pytest.mark.unit


def test_version_is_a_three_part_release_number() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", orqlet.__version__)
