"""Reading structured text (YAML) into plain data. Strictness lives in the adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from orqlet.domain.errors import OrqletError


class DocumentError(OrqletError):
    """A document is malformed or breaks the loading policy (size, depth, anchors, tags...)."""


class DocumentWriter(Protocol):
    def dump(self, data: Mapping[str, object]) -> bytes:
        """Write plain data as a document with a fixed layout: the same data, the same bytes."""
        ...


class DocumentLoader(Protocol):
    def load(self, data: bytes, *, source: str) -> object:
        """Parse one document to plain dicts, lists, strings, numbers, booleans and None.

        `source` names the file in error messages. The result is then validated by a contract.
        """
        ...
