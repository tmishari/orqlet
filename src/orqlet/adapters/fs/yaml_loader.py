"""Strict YAML loading (ADR-002).

Orqlet reads YAML that a repository controls, so the loader accepts only a small, boring subset:
one document, a byte limit, bounded depth and size, no anchors or aliases, no merge keys, no
duplicate or non-string keys, no tags outside the YAML core schema and a YAML 1.2 style scalar
resolver (so `no`, `on` and `2026-10-20` stay strings and `1.10` is a number, which a contract
then rejects where a string is wanted).
"""

from __future__ import annotations

import re
from typing import Any

import yaml
from yaml.composer import Composer
from yaml.constructor import ConstructorError, SafeConstructor
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node
from yaml.parser import Parser
from yaml.reader import Reader
from yaml.resolver import BaseResolver
from yaml.scanner import Scanner

from orqlet.application.ports.documents import DocumentError

_CORE_TAGS = frozenset(
    f"tag:yaml.org,2002:{name}" for name in ("str", "int", "float", "bool", "null", "seq", "map")
)


class _Resolver(BaseResolver):
    """The YAML 1.2 core scalar types and nothing else."""


_Resolver.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF")
)
_Resolver.add_implicit_resolver(
    "tag:yaml.org,2002:int", re.compile(r"^[-+]?[0-9]+$"), list("-+0123456789")
)
_Resolver.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(r"^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?$"),
    list("-+0123456789."),
)
_Resolver.add_implicit_resolver(
    "tag:yaml.org,2002:null", re.compile(r"^(?:~|null|Null|NULL|)$"), ["~", "n", "N", ""]
)


class _Constructor(SafeConstructor):
    def construct_object(self, node: Node, deep: bool = False) -> Any:
        if node.tag not in _CORE_TAGS:
            raise ConstructorError(None, None, f"tag {node.tag!r} is not allowed", node.start_mark)
        return super().construct_object(node, deep=deep)

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[str, Any]:  # type: ignore[override]
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=True)
            if not isinstance(key, str):
                raise ConstructorError(None, None, "keys must be strings", key_node.start_mark)
            if key == "<<":
                raise ConstructorError(
                    None, None, "merge keys are not allowed", key_node.start_mark
                )
            if key in mapping:
                raise ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


class _Loader(Reader, Scanner, Parser, Composer, _Constructor, _Resolver):
    def __init__(self, text: str, *, max_depth: int, max_nodes: int) -> None:
        Reader.__init__(self, text)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        _Constructor.__init__(self)
        _Resolver.__init__(self)
        self._max_depth = max_depth
        self._max_nodes = max_nodes
        self._depth = 0
        self._nodes = 0

    def compose_node(self, parent: Node | None, index: Any) -> Node | None:
        if self.check_event(AliasEvent):
            raise DocumentError("aliases are not allowed")
        if getattr(self.peek_event(), "anchor", None) is not None:  # type: ignore[no-untyped-call]
            raise DocumentError("anchors are not allowed")
        self._nodes += 1
        if self._nodes > self._max_nodes:
            raise DocumentError(f"more than {self._max_nodes} nodes")
        self._depth += 1
        if self._depth > self._max_depth:
            raise DocumentError(f"nesting deeper than {self._max_depth} levels")
        try:
            return super().compose_node(parent, index)
        finally:
            self._depth -= 1


class StrictYamlLoader:
    def __init__(
        self, *, max_bytes: int = 1_048_576, max_depth: int = 32, max_nodes: int = 50_000
    ) -> None:
        self._max_bytes = max_bytes
        self._max_depth = max_depth
        self._max_nodes = max_nodes

    def load(self, data: bytes, *, source: str) -> object:
        if len(data) > self._max_bytes:
            raise DocumentError(f"{source}: larger than {self._max_bytes} bytes")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentError(f"{source}: not valid UTF-8") from exc
        loader: _Loader | None = None
        try:
            loader = _Loader(text, max_depth=self._max_depth, max_nodes=self._max_nodes)
            return loader.get_single_data()
        except DocumentError as exc:
            raise DocumentError(f"{source}: {exc}") from exc
        except yaml.MarkedYAMLError as exc:
            mark = exc.problem_mark
            where = f" (line {mark.line + 1})" if mark is not None else ""
            raise DocumentError(f"{source}: {exc.problem}{where}") from exc
        except (yaml.YAMLError, ValueError, RecursionError) as exc:
            # includes ReaderError, which a control character raises while the loader is built
            raise DocumentError(f"{source}: cannot be parsed") from exc
        finally:
            if loader is not None:
                loader.dispose()
