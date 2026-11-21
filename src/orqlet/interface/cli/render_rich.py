"""The Rich presenter for the human output of `orqlet install` and `orqlet uninstall` (ADR-007).

Every other command keeps the plain renderer in `render_human`. Rich stays in this module so
that the inner layers never depend on it.
"""

import unicodedata
from collections.abc import Mapping
from enum import StrEnum

from rich.console import Console
from rich.table import Table
from rich.text import Text


class State(StrEnum):
    DETECTED = "detected"
    ALREADY_CONFIGURED = "already configured"
    INSTALLED = "installed"
    REGISTERED = "registered"
    HOST_STEP = "host step"
    CONFLICT = "conflict"
    FAILED = "failed"


BANNER_MIN_WIDTH = 60
NARROW_TITLE = "orqlet install"

# Only letters, "/", "\", "-", "o" and spaces, so the banner survives any encoding (ADR-007).
BANNER = "\n".join(
    [
        r"  /--o--\                 orqlet",
        r" o   o   o    one command sets up your AI clients",
        r"  \--o--/",
    ]
)

_UNICODE_ICONS: Mapping[State, str] = {
    State.DETECTED: "\u2022",
    State.ALREADY_CONFIGURED: "=",
    State.INSTALLED: "\u2713",
    State.REGISTERED: "\u2713",
    State.HOST_STEP: "\u2192",
    State.CONFLICT: "\u2717",
    State.FAILED: "\u2717",
}
_ASCII_ICONS: Mapping[State, str] = {
    State.DETECTED: "*",
    State.ALREADY_CONFIGURED: "=",
    State.INSTALLED: "+",
    State.REGISTERED: "+",
    State.HOST_STEP: ">",
    State.CONFLICT: "x",
    State.FAILED: "x",
}
_ICON_STYLES: Mapping[State, str] = {
    State.DETECTED: "cyan",
    State.ALREADY_CONFIGURED: "dim",
    State.INSTALLED: "green",
    State.REGISTERED: "green",
    State.HOST_STEP: "yellow",
    State.CONFLICT: "red",
    State.FAILED: "red",
}
# Zl and Zp are the Unicode line and paragraph separators, which some viewers break lines on.
_REMOVED_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})
_TOOL_OUTPUT_INDENT = "    "


def inert(text: str) -> str:
    """Remove control, format and separator characters, so dynamic text cannot restyle or forge
    a line."""
    return "".join(c for c in text if unicodedata.category(c) not in _REMOVED_CATEGORIES)


def _is_plain(console: Console, environ: Mapping[str, str]) -> bool:
    return (
        not console.is_terminal
        or bool(environ.get("NO_COLOR"))
        or environ.get("TERM") == "dumb"
        or "CI" in environ
    )


class RichPresenter:
    """Prints state lines, the banner and tool output, in interactive or plain mode."""

    def __init__(self, console: Console, environ: Mapping[str, str]) -> None:
        self._console = console
        self._plain = _is_plain(console, environ)
        self._unicode = (
            not self._plain
            and console.encoding.lower().replace("-", "") == "utf8"
            and not console.legacy_windows
        )
        self._banner_shown = False

    @property
    def plain(self) -> bool:
        return self._plain

    @property
    def unicode(self) -> bool:
        return self._unicode

    @property
    def prompts_allowed(self) -> bool:
        return not self._plain

    def banner(self) -> None:
        if self._plain or self._banner_shown:
            return
        self._banner_shown = True
        if self._console.width < BANNER_MIN_WIDTH:
            self._print(Text(NARROW_TITLE, style="bold"))
        else:
            self._print(Text(BANNER, style="bold cyan"))

    def state(self, state: State, subject: str) -> None:
        icons = _UNICODE_ICONS if self._unicode else _ASCII_ICONS
        prefix = Text(icons[state], style=self._style(_ICON_STYLES[state]))
        prefix.append(f" {state.value}: ", style=self._style("bold"))
        self._print_hanging(prefix, Text(inert(subject)))

    def tool_output(self, label: str, text: str) -> None:
        label_line = Text(f"{inert(label)}:", style=self._style("bold"))
        self._console.print(
            label_line,
            markup=False,
            emoji=False,
            highlight=False,
            no_wrap=True,
            overflow="ellipsis",
        )
        for raw_line in text.splitlines():
            line = inert(raw_line)
            if line.strip():
                self._print_hanging(Text(_TOOL_OUTPUT_INDENT), Text(line))

    def _style(self, style: str) -> str:
        return "" if self._plain else style

    def _print_hanging(self, prefix: Text, body: Text) -> None:
        # A wrapped part of dynamic text must never start at column 0, where it could pass for
        # a state line, so the body wraps in its own column to the right of the prefix.
        grid = Table.grid()
        grid.add_column(no_wrap=True)
        grid.add_column(overflow="fold")
        grid.add_row(prefix, body)
        self._console.print(grid, markup=False, emoji=False, highlight=False)

    def _print(self, text: Text) -> None:
        self._console.print(text, markup=False, emoji=False, highlight=False)
