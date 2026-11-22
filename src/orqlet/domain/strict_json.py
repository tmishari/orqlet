"""Strict JSON for documents a client or a repository hands over (ADR-002 decision 3, ADR-004).

Python's own reader keeps the last of two equal keys and accepts NaN and Infinity, so two readers
of one payload could see different values. Here either is refused, as is any top level but an
object. The size is checked before a byte is decoded, so a huge payload costs nothing to refuse.
"""

from __future__ import annotations

import json

from orqlet.domain.errors import OrqletError

MAX_PAYLOAD_BYTES = 1_048_576


class StrictJsonError(OrqletError):
    """The document is too large, not UTF-8, not JSON, or breaks one of the strict rules."""


def parse_object(data: bytes, *, limit: int = MAX_PAYLOAD_BYTES) -> dict[str, object]:
    """The JSON object in `data`. Raises `StrictJsonError` on anything else."""
    if len(data) > limit:
        raise StrictJsonError(f"the document is larger than {limit} bytes")
    try:
        text = data.decode("utf-8")
        parsed = json.loads(text, object_pairs_hook=_unique_keys, parse_constant=_no_constant)
    except UnicodeDecodeError:
        raise StrictJsonError("the document is not UTF-8") from None
    except json.JSONDecodeError as exc:
        raise StrictJsonError(f"the document is not JSON: {exc.msg}") from None
    except ValueError:
        # An integer past sys.get_int_max_str_digits() is a plain ValueError, not a decode error.
        raise StrictJsonError("the document holds a number too long to read") from None
    except RecursionError:
        raise StrictJsonError("the document nests too deeply") from None
    if not isinstance(parsed, dict):
        raise StrictJsonError("the top level is not an object")
    return parsed


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    found: dict[str, object] = {}
    for key, value in pairs:
        if key in found:
            raise StrictJsonError(f"the key {key!r} appears twice")
        found[key] = value
    return found


def _no_constant(name: str) -> object:
    raise StrictJsonError(f"{name} is not a JSON number")
