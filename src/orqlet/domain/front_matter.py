"""Front matter as a line-oriented reader sees it, and its comparison with the parsed view.

Cursor read the quotes of `name: "orqlet-inventory"` as part of the name, because it takes one
`key: value` line at a time and does not parse YAML (harness2-fit AS-IS O-11). A YAML parser sees
the same file as `orqlet-inventory`. This module models the first reader and compares it with the
second, so a test can fail when a generated file would be read differently by the two.

Both functions are pure and never raise: the input is generated text in a test today, but it is
text all the same, and a check that crashes on odd input would hide the defect it exists to find.

The design (ADR-001 decision 2) leaves some edge cases of the line view open. The choices below are
the simplest reading of "one `key: value` line at a time" and none of them is pinned by a test:

- a key is letters, digits, `_`, `.` and `-`, starting with a letter, digit or `_`, at column 0;
- a line with a key and a colon but no value (`key:`) reads as the empty value;
- a colon that is not followed by a blank (`key:value`) is not a `key: value` line;
- when a key repeats, the last line wins, as in a reader that assigns line by line;
- only `\\n` ends a line, after `\\r\\n` has been read as `\\n`; blanks are spaces and tabs.
"""

import re
from collections.abc import Mapping

# The key class excludes `:`, so the first colon ends the key and no backtracking can occur on
# long input. A value may itself contain colons.
_KEY_VALUE = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_.-]*):(?:[ \t]+(.*))?")


def simple_front_matter(block: str) -> dict[str, str]:
    """The key and value pairs that a reader taking one `key: value` line at a time sees.

    `block` is the text between the two `---` lines. Quote characters stay in the value.
    Indented lines and lines that are not `key: value` lines are ignored.
    """
    view: dict[str, str] = {}
    for line in block.replace("\r\n", "\n").split("\n"):
        match = _KEY_VALUE.fullmatch(line)
        if match is not None:
            view[match[1]] = (match[2] or "").strip(" \t\r")
    return view


def front_matter_differences(
    line_view: Mapping[str, str], parsed: Mapping[str, object]
) -> tuple[str, ...]:
    """One message per key that the line view and the parsed view do not agree on.

    A key disagrees when its two values differ by string form, when it is in one view only, or
    when the parsed value is not a one-line scalar. Messages name keys and never print values:
    a value may be text that was pasted into the wrong file.
    """
    messages: list[str] = []
    for key in sorted({*line_view, *parsed}, key=repr):
        message = _difference(key, line_view, parsed)
        if message is not None:
            messages.append(message)
    return tuple(messages)


def _difference(key: str, line_view: Mapping[str, str], parsed: Mapping[str, object]) -> str | None:
    if key not in parsed:
        return f"{key!r} is in the line view only"
    if key not in line_view:
        return f"{key!r} is in the parsed view only"
    text = _string_form(parsed[key])
    if text is None:
        return f"{key!r} has a parsed value that is not a one-line scalar"
    if text != line_view[key]:
        return f"{key!r} reads differently in the line view and in the parsed view"
    return None


def _string_form(value: object) -> str | None:
    """The text of a parsed scalar, or `None` for a value that has no one-line form.

    A boolean is decided before an integer because `bool` is a subclass of `int` in Python.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        try:
            return str(value)
        except ValueError:  # Python refuses to print an integer of more than 4300 digits
            return None
    if isinstance(value, str):
        return value
    return None
