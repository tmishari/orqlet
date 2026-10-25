"""Explicit emitters for the text formats Orqlet writes (ADR-005).

No template engine and no YAML dumper: output is built here, field by field, in the order the
caller gives. Every string that is not a simple word is written with `json.dumps`, which is also
a valid YAML double-quoted scalar and a valid TOML basic string. The result is the same bytes on
every platform and with every PyYAML release.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence

type Scalar = str | int | bool | None
type Data = Scalar | Sequence[Data] | Mapping[str, Data]

_SIMPLE_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_./@+-]*")
_RESERVED = frozenset({"true", "false", "null", "yes", "no", "on", "off", "y", "n", "~"})
# Characters that JSON leaves raw but YAML or TOML does not allow, or that readers mishandle.
_ESCAPE = re.compile("[\x7f-\x9f\u2028\u2029\ufeff\ufffe\uffff]")


def normalise_text(text: str) -> str:
    """LF line endings and exactly one final newline. An empty text stays empty."""
    unified = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    return f"{unified}\n" if unified else ""


def quote(value: str) -> str:
    """A double-quoted string that is valid YAML and valid TOML."""
    value.encode("utf-8")  # a lone surrogate cannot be written; fail here, not on disk
    quoted = json.dumps(value, ensure_ascii=False)
    return _ESCAPE.sub(lambda match: f"\\u{ord(match.group()):04x}", quoted)


def yaml_scalar(value: Scalar, *, quote_all: bool = False) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if not quote_all and _SIMPLE_WORD.fullmatch(value) and value.lower() not in _RESERVED:
        return value
    return quote(value)


def yaml_document(data: Mapping[str, Data] | Sequence[Data], *, quote_all: bool = False) -> str:
    """Block-style YAML for plain data. Mappings keep the order they are given."""
    lines: list[str] = []
    _emit_container(data, 0, lines, quote_all)
    return "\n".join(lines) + "\n" if lines else "{}\n"


def front_matter(fields: Sequence[tuple[str, Data]]) -> str:
    """A Markdown front-matter block. Every string is quoted; keys keep the given order."""
    body = yaml_document(dict(fields), quote_all=True) if fields else ""
    return f"---\n{body}---\n"


def toml_value(value: Data) -> str:
    if isinstance(value, str):
        return quote(value)
    if value is None:
        raise ValueError("TOML has no null")
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Mapping):
        raise ValueError("write nested tables with toml_table")
    return "[" + ", ".join(toml_value(item) for item in value) + "]"


def toml_table(fields: Sequence[tuple[str, Data]], *, name: str | None = None) -> str:
    """`key = value` lines, optionally under a `[name]` header. Keys keep the given order."""
    lines = [f"[{name}]"] if name else []
    lines += [f"{_toml_key(key)} = {toml_value(value)}" for key, value in fields]
    return "\n".join(lines) + "\n"


# --- internals ---------------------------------------------------------------------------
def _toml_key(key: str) -> str:
    return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else quote(key)


def _is_container(value: Data) -> bool:
    return isinstance(value, Mapping) or (
        isinstance(value, Sequence) and not isinstance(value, str)
    )


def _emit_container(
    value: Mapping[str, Data] | Sequence[Data], indent: int, lines: list[str], quote_all: bool
) -> None:
    pad = " " * indent
    if isinstance(value, Mapping):
        for key, item in value.items():
            rendered_key = yaml_scalar(key, quote_all=False)
            if not _is_container(item):
                lines.append(f"{pad}{rendered_key}: {yaml_scalar(item, quote_all=quote_all)}")  # type: ignore[arg-type]
            elif not item:
                lines.append(f"{pad}{rendered_key}: {'{}' if isinstance(item, Mapping) else '[]'}")
            else:
                lines.append(f"{pad}{rendered_key}:")
                _emit_container(item, indent + 2, lines, quote_all)  # type: ignore[arg-type]
        return
    for item in value:
        if not _is_container(item):
            lines.append(f"{pad}- {yaml_scalar(item, quote_all=quote_all)}")  # type: ignore[arg-type]
        elif not item:
            lines.append(f"{pad}- {'{}' if isinstance(item, Mapping) else '[]'}")
        else:
            inner: list[str] = []
            _emit_container(item, indent + 2, inner, quote_all)  # type: ignore[arg-type]
            lines.append(f"{pad}- {inner[0][indent + 2 :]}")
            lines.extend(inner[1:])


class YamlWriter:
    """`DocumentWriter` on the explicit YAML emitter."""

    def dump(self, data: Mapping[str, object]) -> bytes:
        return yaml_document(data).encode("utf-8")  # type: ignore[arg-type]
