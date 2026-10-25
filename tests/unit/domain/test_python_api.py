"""The public API extractor: the rules of proposal 17.4.1, one test each."""

from __future__ import annotations

import pytest

from orqlet.domain.python_api import canonical_signature, extract_module_api, signature_digest

pytestmark = pytest.mark.unit


def names(source: str, *, init: bool = False) -> set[str]:
    return set(extract_module_api(source, is_package_init=init).symbols)


def test_without_all_every_module_level_name_without_an_underscore_is_public() -> None:
    source = "def run(): ...\nclass Thing: ...\nvalue = 1\ndef _hidden(): ...\n_secret = 2\n"

    assert names(source) == {"run", "Thing", "value"}


def test_a_literal_all_decides_what_is_public_even_for_private_looking_names() -> None:
    source = "__all__ = ['run', '_odd']\ndef run(): ...\ndef _odd(): ...\ndef other(): ...\n"

    assert names(source) == {"run", "_odd"}


def test_a_name_listed_in_all_but_never_defined_is_still_a_symbol_of_the_surface() -> None:
    api = extract_module_api("__all__ = ['ghost']\n")

    assert api.symbols["ghost"].signature == "<undefined>"


def test_names_under_a_module_level_if_or_try_count_and_type_checking_blocks_do_not() -> None:
    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    class OnlyForTypes: ...\n"
        "if True:\n    def conditional(): ...\n"
        "try:\n    def attempt(): ...\nexcept ValueError:\n    def handler(): ...\n"
    )

    assert names(source) == {"conditional", "attempt", "handler"}


def test_an_import_is_public_only_when_it_is_listed_or_explicitly_re_exported_in_init() -> None:
    source = "from .core import a as a\nfrom .core import b\nimport os as os\nimport sys\n"

    assert names(source, init=True) == {"a", "os"}
    assert names(source, init=False) == set()
    assert names("from .core import b\n__all__ = ['b']\n") == {"b"}


def test_future_imports_are_ignored() -> None:
    assert names("from __future__ import annotations as annotations\n", init=True) == set()


def test_an_alias_is_a_public_name_with_its_target_recorded() -> None:
    api = extract_module_api("def real(): ...\nalias = real\n")

    assert api.symbols["alias"].signature == "alias = real"


def test_public_class_members_are_symbols_with_their_signatures() -> None:
    source = (
        "class Order:\n    def total(self, tax: float) -> float: ...\n    def _hidden(self): ...\n"
    )

    api = extract_module_api(source)

    assert api.symbols["Order"].signature == "class Order"
    assert api.symbols["Order.total"].signature == "def total(self, tax: float) -> float"
    assert "Order._hidden" not in api.symbols


def test_a_function_is_written_as_its_signature_text_with_async_and_annotations() -> None:
    api = extract_module_api("async def fetch(url: str, *, retries: int = 3) -> bytes: ...\n")

    assert api.symbols["fetch"].signature == "async def fetch(url: str, *, retries: int=3) -> bytes"


def test_two_definitions_of_one_public_name_are_an_error() -> None:
    api = extract_module_api("def run(): ...\ndef run(a): ...\n")

    assert api.errors == ("`run` is defined 2 times",)


def test_overload_stubs_property_pairs_and_import_fallbacks_count_as_one_name() -> None:
    source = (
        "from typing import overload\n"
        "@overload\ndef f(a: int) -> int: ...\n"
        "@overload\ndef f(a: str) -> str: ...\n"
        "def f(a): return a\n"
        "class C:\n"
        "    @property\n    def p(self): ...\n"
        "    @p.setter\n    def p(self, v): ...\n"
        "try:\n    from fast import speed\nexcept ImportError:\n    def speed(): ...\n"
        "__all__ = ['f', 'C', 'speed', 'C.p']\n"
    )

    api = extract_module_api(source)

    assert api.errors == ()
    assert api.symbols["f"].signature == "def f(a)"


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ("__all__ = [name for name in dir()]\n", "not a literal"),
        ("__all__ = ['a']\n__all__.append('b')\n", "append"),
        ("__all__ = ['a']\n__all__ += ['b']\n", "augmented"),
        ("__all__ = ['a']\ndel __all__[0]\n", "del"),
        ("def __getattr__(name): ...\n", "__getattr__"),
        ("from os.path import *\n", "star import"),
        ("def broken(:\n", "cannot be parsed"),
    ],
)
def test_anything_that_hides_the_real_surface_makes_it_manual(source: str, reason: str) -> None:
    api = extract_module_api(source)

    assert api.manual
    assert reason in api.manual[0]


def test_a_declared_signature_is_canonicalised_like_the_extractor_writes_it() -> None:
    declared = canonical_signature("def create_order(customer_id:str, items: list[Item])->Order")

    assert declared == "def create_order(customer_id: str, items: list[Item]) -> Order"
    api = extract_module_api(
        "def create_order(customer_id: str, items: list[Item]) -> Order: ...\n"
    )
    assert api.symbols["create_order"].digest == signature_digest(declared)


@pytest.mark.parametrize("text", ["not python (", "x = 1", "def a(): ...\ndef b(): ...", ""])
def test_a_declaration_that_is_not_one_function_or_class_is_refused(text: str) -> None:
    assert canonical_signature(text) is None


def test_a_class_declaration_is_read_as_its_head() -> None:
    assert canonical_signature("class Order(Base, metaclass=Meta)") == (
        "class Order(Base, metaclass=Meta)"
    )
