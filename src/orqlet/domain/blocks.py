"""Managed blocks inside files that other people own (proposal section 13.7, "Marker rules").

A block is delimited by line-anchored comment markers that are recognised outside code fences:

    <!-- orqlet:begin <name> <info> -->
    ...
    <!-- orqlet:end <name> -->

Rules, all of which end in `BlockError` and no write:
- exactly one balanced pair per name; missing, duplicated, nested or unbalanced markers are errors;
- a file with merge-conflict markers (`<<<<<<< ` or `>>>>>>> ` at a line start) is refused;
- an unclosed code fence is refused, because markers after it cannot be told from text;
- a byte-order mark is skipped when parsing and kept when writing;
- line endings of the file are kept: CRLF stays CRLF, LF stays LF.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from orqlet.domain.errors import OrqletError

BOM = "\ufeff"
_BEGIN = re.compile(r"^<!-- orqlet:begin (?P<name>[a-z][a-z0-9-]*)(?: (?P<info>[^\r\n]*?))? -->$")
_END = re.compile(r"^<!-- orqlet:end (?P<name>[a-z][a-z0-9-]*) -->$")
_FENCE = re.compile(r"^ {0,3}(?P<mark>`{3,}|~{3,})")
_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
_CONFLICT = re.compile(r"^(?:<{7} |>{7} )")


class BlockError(OrqletError):
    """A file cannot be edited safely around its managed blocks."""


@dataclass(frozen=True, slots=True)
class Block:
    name: str
    info: str  # the text after the name in the begin marker, for example `v1@1.0.0#<hash>`
    body: str  # the lines between the markers, joined with `\n`, without a final break
    start: int  # offset of the first character of the begin-marker line
    end: int  # offset just after the end-marker line, including its line break


def decode_utf8(data: bytes) -> str:
    """Decode strictly. Anything but UTF-8 (with or without a byte-order mark) is a conflict."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BlockError("the file is not valid UTF-8") from exc


def parse_blocks(text: str) -> tuple[Block, ...]:
    """Find every block, in file order. Raises `BlockError` on any structural problem."""
    offset = len(BOM) if text.startswith(BOM) else 0
    blocks: list[Block] = []
    open_name: str | None = None
    open_info = ""
    open_start = 0
    body_lines: list[str] = []
    fence: tuple[str, int] | None = None
    for line_with_end in _lines(text[offset:]):
        line = line_with_end.rstrip("\r\n")
        line_start = offset
        offset += len(line_with_end)
        if _CONFLICT.match(line):
            raise BlockError("the file contains merge-conflict markers")
        fence = _next_fence_state(line, fence)
        if fence is not None or _FENCE.match(line):
            if open_name is not None:
                body_lines.append(line)
            continue
        begin, end = _BEGIN.match(line), _END.match(line)
        if begin is not None:
            if open_name is not None:
                raise BlockError(f"block {begin['name']!r} starts inside block {open_name!r}")
            if any(block.name == begin["name"] for block in blocks):
                raise BlockError(f"block {begin['name']!r} appears twice")
            open_name, open_info, open_start, body_lines = (
                begin["name"],
                begin["info"] or "",
                line_start,
                [],
            )
        elif end is not None:
            if open_name is None or open_name != end["name"]:
                raise BlockError(f"end marker {end['name']!r} has no matching begin marker")
            blocks.append(Block(open_name, open_info, "\n".join(body_lines), open_start, offset))
            open_name = None
        elif open_name is not None:
            body_lines.append(line)
    if fence is not None:
        raise BlockError("the file has an unclosed code fence")
    if open_name is not None:
        raise BlockError(f"block {open_name!r} is never closed")
    return tuple(blocks)


def find_block(text: str, name: str) -> Block | None:
    return next((block for block in parse_blocks(text) if block.name == name), None)


def render_block(name: str, info: str, body: str, *, newline: str = "\n") -> str:
    """The marker lines and the body, each ending with `newline`."""
    begin = f"<!-- orqlet:begin {name} {info} -->" if info else f"<!-- orqlet:begin {name} -->"
    lines = [begin, *body.split("\n"), f"<!-- orqlet:end {name} -->"]
    return newline.join(lines) + newline


@dataclass(frozen=True, slots=True)
class BlockItem:
    name: str
    info: str
    body: str


def set_block(text: str, name: str, info: str, body: str, *, insert_after_heading: bool) -> str:
    """Replace the named block, or insert it when absent. Everything else is kept byte for byte."""
    item = BlockItem(name, info, body)
    return set_blocks(text, [item], insert_after_heading=insert_after_heading)


def set_blocks(text: str, items: Sequence[BlockItem], *, insert_after_heading: bool) -> str:
    """Replace blocks that exist, and insert the missing ones together, in the order given.

    New blocks go after the first heading that is outside code fences and outside other blocks;
    a file with no such heading gets them at the top. With `insert_after_heading=False` they are
    appended at the end instead.
    """
    existing = {block.name: block for block in parse_blocks(text)}
    newline = detect_newline(text)
    # Replace from the end of the file so earlier offsets stay valid.
    for item in sorted(
        (i for i in items if i.name in existing), key=lambda i: -existing[i.name].start
    ):
        found = existing[item.name]
        rendered = render_block(item.name, item.info, item.body, newline=newline)
        text = text[: found.start] + rendered + text[found.end :]
    missing = [item for item in items if item.name not in existing]
    if not missing:
        return text
    combined = newline.join(
        render_block(item.name, item.info, item.body, newline=newline) for item in missing
    )
    return _insert(text, combined, newline, insert_after_heading=insert_after_heading)


def remove_block(text: str, name: str) -> str:
    existing = find_block(text, name)
    if existing is None:
        return text
    return text[: existing.start] + text[existing.end :]


def detect_newline(text: str) -> str:
    """`\\r\\n` when the file uses it more than bare `\\n`, otherwise `\\n`."""
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return "\r\n" if crlf > lf else "\n"


def validate_asset_body(body: str) -> None:
    """A text supplied by a pack must not carry markers, an open fence or an open comment."""
    if "orqlet:" in body:
        raise BlockError("the text contains marker text (`orqlet:`)")
    fence: tuple[str, int] | None = None
    for line in _lines(body):
        fence = _next_fence_state(line.rstrip("\r\n"), fence)
    if fence is not None:
        raise BlockError("the text has an unclosed code fence")
    if body.count("<!--") != body.count("-->"):
        raise BlockError("the text has an unclosed HTML comment")


# --- internals ---------------------------------------------------------------------------
def _lines(text: str) -> list[str]:
    """Split on `\\n`, `\\r\\n` and a lone `\\r`, keeping each line's own ending."""
    return re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+", text)


def _next_fence_state(line: str, fence: tuple[str, int] | None) -> tuple[str, int] | None:
    """Track code fences: returns the open fence after this line, or `None` when none is open."""
    match = _FENCE.match(line)
    if match is None:
        return fence
    mark = match["mark"]
    if fence is None:
        return (mark[0], len(mark))
    closes = mark[0] == fence[0] and len(mark) >= fence[1] and line.strip() == mark
    return None if closes else fence


def _insert(text: str, combined: str, newline: str, *, insert_after_heading: bool) -> str:
    bom = BOM if text.startswith(BOM) else ""
    body = text[len(bom) :]
    if insert_after_heading:
        anchor = _heading_end(body)
        if anchor is not None:
            head, tail = body[:anchor], body[anchor:]
            if not head.endswith(("\n", "\r")):
                head += newline
            return bom + head + newline + combined + tail
        rest = newline + body if body else ""
        return bom + combined + rest
    separator = "" if not body or body.endswith(("\n", "\r")) else newline
    glue = newline if body else ""
    return bom + body + separator + glue + combined


def _heading_end(body: str) -> int | None:
    """Offset just after the first heading line outside code fences and outside blocks."""
    spans = [(block.start, block.end) for block in parse_blocks(body)]
    offset = 0
    fence: tuple[str, int] | None = None
    for line in _lines(body):
        start = offset
        offset += len(line)
        was_inside = fence is not None
        fence = _next_fence_state(line.rstrip("\r\n"), fence)
        in_block = any(begin <= start < end for begin, end in spans)
        if not was_inside and fence is None and not in_block and _HEADING.match(line):
            return offset
    return None
