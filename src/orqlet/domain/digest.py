"""Canonical JSON and SHA-256 digests (ADR-002).

The serializer implements RFC 8785 for the subset that Orqlet hashes: objects, arrays,
strings, booleans, null and integers within the IEEE-754 safe range. Floats are rejected, so
the number-formatting part of the RFC never arises. Object keys are ordered by their UTF-16
code units, which differs from Python's code point order for characters outside the Basic
Multilingual Plane.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from orqlet.domain.errors import CanonicalJsonError

type JsonValue = str | int | bool | Sequence[JsonValue] | Mapping[str, JsonValue] | None

_MAX_SAFE_INTEGER = 2**53 - 1
_SHORT_ESCAPES = {"\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}


def _encode_string(text: str) -> str:
    pieces = ['"']
    for char in text:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise CanonicalJsonError("a string contains a lone surrogate")
        if char == '"':
            pieces.append('\\"')
        elif char == "\\":
            pieces.append("\\\\")
        elif char in _SHORT_ESCAPES:
            pieces.append(_SHORT_ESCAPES[char])
        elif code < 0x20:
            pieces.append(f"\\u{code:04x}")
        else:
            pieces.append(char)
    pieces.append('"')
    return "".join(pieces)


def _encode(value: JsonValue) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if abs(value) > _MAX_SAFE_INTEGER:
            raise CanonicalJsonError(f"integer {value} is outside the safe range")
        return str(value)
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, Mapping):
        members = []
        for key in value:
            if not isinstance(key, str):
                raise CanonicalJsonError(f"object key {key!r} is not a string")
        for key in sorted(value, key=lambda k: k.encode("utf-16-be", "surrogatepass")):
            members.append(f"{_encode_string(key)}:{_encode(value[key])}")
        return "{" + ",".join(members) + "}"
    if isinstance(value, bytes | bytearray):
        raise CanonicalJsonError("bytes cannot be hashed as JSON")
    if isinstance(value, Sequence):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    raise CanonicalJsonError(f"a value of type {type(value).__name__} cannot be hashed")


def canonical_json(value: JsonValue) -> bytes:
    """Return the canonical UTF-8 bytes of `value`."""
    return _encode(value).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Lower-case hex SHA-256. This is the only digest algorithm Orqlet exposes."""
    return hashlib.sha256(data).hexdigest()


def digest_of(value: JsonValue) -> str:
    """SHA-256 of the canonical JSON form of `value`."""
    return sha256_hex(canonical_json(value))
