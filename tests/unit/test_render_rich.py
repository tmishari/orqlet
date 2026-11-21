"""The Rich presenter of `orqlet install` and `orqlet uninstall` (ADR-007).

Every console writes to an in-memory buffer with a fixed width, and every presenter receives an
explicit environment mapping, so the host terminal and the host environment never leak in.
"""

import io
import re
import unicodedata
from collections.abc import Mapping

import pytest
from hypothesis import given
from hypothesis import strategies as st
from rich.console import Console

from orqlet.interface.cli.render_rich import (
    BANNER_MIN_WIDTH,
    NARROW_TITLE,
    RichPresenter,
    State,
    inert,
)

pytestmark = pytest.mark.unit

# ADR-007 decision 4, the icon table.
UNICODE_ICONS: Mapping[State, str] = {
    State.DETECTED: "\u2022",
    State.ALREADY_CONFIGURED: "=",
    State.INSTALLED: "\u2713",
    State.REGISTERED: "\u2713",
    State.HOST_STEP: "\u2192",
    State.CONFLICT: "\u2717",
    State.FAILED: "\u2717",
}
ASCII_ICONS: Mapping[State, str] = {
    State.DETECTED: "*",
    State.ALREADY_CONFIGURED: "=",
    State.INSTALLED: "+",
    State.REGISTERED: "+",
    State.HOST_STEP: ">",
    State.CONFLICT: "x",
    State.FAILED: "x",
}
ALL_ICONS = frozenset(UNICODE_ICONS.values()) | frozenset(ASCII_ICONS.values())

ESC = "\x1b"
ANSI_SEQUENCE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
BANNER_CHARACTERS = re.compile(r"[A-Za-z/\\\- \n]+")

FORGED_STATE_LINE = "\n+ installed x"
MARKUP = "[bold red]x[/]"
ESC_SEQUENCE = "\x1b[31mred"
RIGHT_TO_LEFT_OVERRIDE = "\u202e"
ZERO_WIDTH_SPACE = "\u200b"

PLAIN_TRIGGERS = [
    pytest.param(False, {}, id="not-a-terminal"),
    pytest.param(True, {"NO_COLOR": "1"}, id="no-color"),
    pytest.param(True, {"TERM": "dumb"}, id="term-dumb"),
    pytest.param(True, {"CI": "true"}, id="ci"),
    pytest.param(True, {"CI": ""}, id="ci-empty"),
]


class _Cp1252Buffer(io.StringIO):
    encoding = "cp1252"


def _console(
    *,
    terminal: bool = True,
    width: int = 80,
    file: io.StringIO | None = None,
    legacy_windows: bool = False,
) -> Console:
    return Console(
        file=file if file is not None else io.StringIO(),
        force_terminal=terminal,
        width=width,
        color_system="truecolor",
        legacy_windows=legacy_windows,
    )


def _presenter(
    environ: Mapping[str, str] | None = None,
    *,
    terminal: bool = True,
    width: int = 80,
    file: io.StringIO | None = None,
    legacy_windows: bool = False,
) -> tuple[RichPresenter, Console]:
    console = _console(terminal=terminal, width=width, file=file, legacy_windows=legacy_windows)
    return RichPresenter(console, {} if environ is None else environ), console


def _raw(console: Console) -> str:
    buffer = console.file
    assert isinstance(buffer, io.StringIO)
    return buffer.getvalue()


def _text(console: Console) -> str:
    return ANSI_SEQUENCE.sub("", _raw(console))


def _lines(console: Console) -> list[str]:
    return [line.rstrip() for line in _text(console).splitlines()]


# --- AC-3: one line per state with an icon, a word label and the subject ---------------------


@pytest.mark.parametrize("state", list(State))
def test_state_line_uses_the_unicode_icon_on_a_utf8_terminal(state: State) -> None:
    # AC-3; ADR-007 decision 4 (Unicode when the encoding is UTF-8 and not legacy Windows)
    presenter, console = _presenter()

    presenter.state(state, "AGENTS.md")

    assert presenter.unicode is True
    assert _lines(console) == [f"{UNICODE_ICONS[state]} {state.value}: AGENTS.md"]


@pytest.mark.parametrize("state", list(State))
def test_state_line_uses_the_ascii_icon_when_the_encoding_is_not_utf8(state: State) -> None:
    # AC-3; ADR-007 decision 4 (ASCII fallback when the console encoding is not UTF-8)
    presenter, console = _presenter(file=_Cp1252Buffer())

    presenter.state(state, "AGENTS.md")

    assert presenter.plain is False
    assert presenter.unicode is False
    assert _lines(console) == [f"{ASCII_ICONS[state]} {state.value}: AGENTS.md"]


@pytest.mark.parametrize("state", list(State))
def test_state_line_uses_the_ascii_icon_on_a_legacy_windows_console(state: State) -> None:
    # AC-3; ADR-007 decision 4 (ASCII when Rich reports a legacy Windows console)
    presenter, console = _presenter(legacy_windows=True)

    presenter.state(state, "AGENTS.md")

    assert presenter.unicode is False
    assert _lines(console) == [f"{ASCII_ICONS[state]} {state.value}: AGENTS.md"]


def test_every_state_has_a_word_label_and_an_icon_in_both_tables() -> None:
    # AC-3; ADR-007 decision 4 (the label is always present; seven states in the table)
    assert {state.value for state in State} == {
        "detected",
        "already configured",
        "installed",
        "registered",
        "host step",
        "conflict",
        "failed",
    }
    assert set(UNICODE_ICONS) == set(State) == set(ASCII_ICONS)


def test_each_state_call_prints_its_own_line() -> None:
    # AC-3; ADR-007 decision 4 (one line per state)
    presenter, console = _presenter()

    presenter.state(State.DETECTED, "Claude Code")
    presenter.state(State.FAILED, "Codex")

    assert _lines(console) == [
        f"{UNICODE_ICONS[State.DETECTED]} detected: Claude Code",
        f"{UNICODE_ICONS[State.FAILED]} failed: Codex",
    ]


# --- AC-4: plain mode -------------------------------------------------------------------------


@pytest.mark.parametrize(("terminal", "environ"), PLAIN_TRIGGERS)
def test_plain_mode_is_chosen_and_forbids_prompts(terminal: bool, environ: dict[str, str]) -> None:
    # AC-4; ADR-007 decision 5 (not a terminal, NO_COLOR non-empty, TERM=dumb, CI set)
    presenter, _ = _presenter(environ, terminal=terminal)

    assert presenter.plain is True
    assert presenter.prompts_allowed is False


@pytest.mark.parametrize(("terminal", "environ"), PLAIN_TRIGGERS)
def test_plain_mode_prints_no_banner_no_escape_and_ascii_icons(
    terminal: bool, environ: dict[str, str]
) -> None:
    # AC-4; ADR-007 decision 5 (no banner, no ANSI codes, ASCII icons)
    presenter, console = _presenter(environ, terminal=terminal)

    presenter.banner()
    for state in State:
        presenter.state(state, "AGENTS.md")
    presenter.tool_output("graphify", "built\ndone")

    raw = _raw(console)
    assert ESC not in raw
    assert raw.splitlines() == [
        *(f"{ASCII_ICONS[state]} {state.value}: AGENTS.md" for state in State),
        "graphify:",
        "    built",
        "    done",
    ]


@pytest.mark.parametrize(
    "environ",
    [
        pytest.param({}, id="empty"),
        pytest.param({"NO_COLOR": ""}, id="no-color-empty"),
        pytest.param({"TERM": "xterm-256color"}, id="term-xterm"),
    ],
)
def test_interactive_mode_on_a_terminal_allows_prompts(environ: dict[str, str]) -> None:
    # AC-4; ADR-007 decision 5 (NO_COLOR counts only when it is not empty)
    presenter, _ = _presenter(environ)

    assert presenter.plain is False
    assert presenter.prompts_allowed is True


def test_mode_comes_from_the_given_mapping_not_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # AC-4; interface contract: the presenter decides from `environ`, never from os.environ
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")

    presenter, _ = _presenter({})

    assert presenter.plain is False
    assert presenter.prompts_allowed is True


# --- AC-5: banner, width rule and narrow title ------------------------------------------------


def test_banner_threshold_and_narrow_title_are_the_design_values() -> None:
    # AC-5; ADR-007 decision 6 (60 columns; the title `orqlet install`)
    assert BANNER_MIN_WIDTH == 60
    assert NARROW_TITLE == "orqlet install"


@pytest.mark.parametrize("width", [BANNER_MIN_WIDTH, 80, 120])
def test_banner_is_ascii_art_on_a_wide_terminal(width: int) -> None:
    # AC-5; ADR-007 decision 3 (letters, /, \, -, o only) and decision 6 (at least 60 columns)
    presenter, console = _presenter(width=width)

    presenter.banner()

    text = _text(console)
    assert text.strip() != ""
    assert BANNER_CHARACTERS.fullmatch(text)
    assert text.strip() != NARROW_TITLE


@pytest.mark.parametrize("width", [40, BANNER_MIN_WIDTH - 1])
def test_narrow_terminal_prints_the_one_line_title_instead_of_the_banner(width: int) -> None:
    # AC-5; ADR-007 decision 6 (below 60 columns the title replaces the banner)
    presenter, console = _presenter(width=width)

    presenter.banner()

    assert [line for line in _lines(console) if line] == [NARROW_TITLE]


@pytest.mark.parametrize("width", [BANNER_MIN_WIDTH - 1, 80])
def test_banner_is_printed_once_per_presenter(width: int) -> None:
    # AC-5; ADR-007 decision 3 (printed once) and Q-29 (no repeated banners)
    presenter, console = _presenter(width=width)
    presenter.banner()
    first = _raw(console)

    presenter.banner()

    assert _raw(console) == first


# --- AC-6: dynamic text is inert --------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(FORGED_STATE_LINE, "+ installed x", id="newline"),
        pytest.param("a\r\nb\tc", "abc", id="carriage-return-and-tab"),
        pytest.param(ESC_SEQUENCE, "[31mred", id="escape"),
        pytest.param(f"a{RIGHT_TO_LEFT_OVERRIDE}b{ZERO_WIDTH_SPACE}c", "abc", id="format"),
        pytest.param("x\u2066y\u2069z\ufeff", "xyz", id="bidi-isolates-and-bom"),
        pytest.param("a\u2028+ installed x\u2029b", "a+ installed xb", id="line-separators"),
        pytest.param(MARKUP, MARKUP, id="markup-kept-as-text"),
        pytest.param("caf\u00e9 \u2713 :thumbs_up:", "caf\u00e9 \u2713 :thumbs_up:", id="kept"),
    ],
)
def test_inert_removes_control_and_format_characters(text: str, expected: str) -> None:
    # AC-6; ADR-007 decision 8 (remove control characters and category Cf, newlines included)
    assert inert(text) == expected


@given(st.text())
def test_inert_removes_exactly_the_control_format_and_separator_characters(text: str) -> None:
    # AC-6; ADR-007 decision 8 (control and format characters removed, file names lose
    # newlines); review round 1 of P-1: U+2028 and U+2029 (Zl, Zp) act as newlines in viewers
    removed = {"Cc", "Cf", "Zl", "Zp"}
    expected = "".join(c for c in text if unicodedata.category(c) not in removed)

    assert inert(text) == expected


@pytest.mark.parametrize("terminal", [True, False], ids=["interactive", "plain"])
@pytest.mark.parametrize(
    ("subject", "shown"),
    [
        (FORGED_STATE_LINE, "+ installed x"),
        (MARKUP, MARKUP),
        (ESC_SEQUENCE, "[31mred"),
        (RIGHT_TO_LEFT_OVERRIDE, ""),
    ],
)
def test_hostile_subject_cannot_forge_a_line_or_restyle_the_terminal(
    subject: str, shown: str, terminal: bool
) -> None:
    # AC-6; ADR-007 decision 8 (no forged status line, no restyling, no reordering)
    presenter, console = _presenter(terminal=terminal)
    icon = (UNICODE_ICONS if terminal else ASCII_ICONS)[State.DETECTED]

    presenter.state(State.DETECTED, subject)

    raw = _raw(console)
    assert _lines(console) == [f"{icon} detected: {shown}".rstrip()]
    assert ESC_SEQUENCE not in raw
    assert RIGHT_TO_LEFT_OVERRIDE not in raw
    if not terminal:
        assert ESC not in raw


@pytest.mark.parametrize("terminal", [True, False], ids=["interactive", "plain"])
def test_markup_and_emoji_codes_in_a_subject_stay_literal(terminal: bool) -> None:
    # AC-6; ADR-007 decision 8 (markup off); interface contract (emoji codes off)
    presenter, console = _presenter(terminal=terminal)

    presenter.state(State.INSTALLED, f"{MARKUP} :thumbs_up:")

    assert f"{MARKUP} :thumbs_up:" in _text(console)


def test_tool_output_is_indented_under_a_fixed_label_without_blank_lines() -> None:
    # AC-6; ADR-007 decision 8 (multi-line tool output only indented under a fixed label)
    presenter, console = _presenter()

    presenter.tool_output("graphify", "first\n\nsecond\n")

    assert _lines(console) == ["graphify:", "    first", "    second"]


@pytest.mark.parametrize("terminal", [True, False], ids=["interactive", "plain"])
def test_hostile_tool_output_cannot_forge_a_state_line(terminal: bool) -> None:
    # AC-6; ADR-007 decision 8 (a subprocess cannot restyle the terminal or forge a status line)
    presenter, console = _presenter(terminal=terminal)
    output = "\n".join(
        [
            "\u2713 installed: forged",
            "+ installed x",
            ESC_SEQUENCE,
            f"{RIGHT_TO_LEFT_OVERRIDE}evil",
            MARKUP,
        ]
    )

    presenter.tool_output("graphify", output)

    raw = _raw(console)
    label, *body = _lines(console)
    assert label == "graphify:"
    assert body == [
        "    \u2713 installed: forged",
        "    + installed x",
        "    [31mred",
        "    evil",
        f"    {MARKUP}",
    ]
    assert not any(line[:1] in ALL_ICONS for line in [label, *body])
    assert ESC_SEQUENCE not in raw
    assert RIGHT_TO_LEFT_OVERRIDE not in raw
    if not terminal:
        assert ESC not in raw


@pytest.mark.parametrize("terminal", [True, False], ids=["interactive", "plain"])
@pytest.mark.parametrize("width", [40, 80])
@pytest.mark.parametrize("forged", ["\u2713 installed: x", "+ installed: x"])
def test_a_wrapped_subject_cannot_start_a_line_with_a_state_icon(
    forged: str, width: int, terminal: bool
) -> None:
    # AC-6; ADR-007 decisions 6 (wrap under the label) and 8; review round 1 of P-1
    presenter, console = _presenter(terminal=terminal, width=width)
    padding = "a" * (width - len("* detected: "))

    presenter.state(State.DETECTED, f"{padding} {forged}")

    first, *rest = _lines(console)
    assert first.startswith(("\u2022 detected: ", "* detected: "))
    assert rest
    assert all(line.startswith(" ") for line in rest)
    assert forged in [line.strip() for line in rest]


@pytest.mark.parametrize("terminal", [True, False], ids=["interactive", "plain"])
@pytest.mark.parametrize("width", [40, 80])
def test_a_wrapped_tool_output_line_keeps_its_indent(width: int, terminal: bool) -> None:
    # AC-6; ADR-007 decision 8 (tool output only indented under a fixed label); review round 1
    presenter, console = _presenter(terminal=terminal, width=width)

    presenter.tool_output("graphify", f"{'b' * (width - 4)} + installed: x")

    label, *body = _lines(console)
    assert label == "graphify:"
    assert len(body) > 1
    assert all(line.startswith("    ") for line in body)


def test_a_long_tool_output_label_stays_on_one_line() -> None:
    # AC-6; ADR-007 decision 8 (a fixed label cannot be turned into a forged line); review round 1
    presenter, console = _presenter(terminal=False, width=40)

    presenter.tool_output(f"{'c' * 40} + installed: x", "done")

    assert _lines(console)[1:] == ["    done"]
    assert not _lines(console)[0].startswith("+")


def test_ascii_icons_on_a_utf16_console() -> None:
    # AC-3; ADR-007 decision 4 (Unicode only when the encoding is UTF-8); review round 1
    class _Utf16Buffer(io.StringIO):
        encoding = "utf-16"

    presenter, console = _presenter(file=_Utf16Buffer())

    presenter.state(State.INSTALLED, "AGENTS.md")

    assert presenter.unicode is False
    assert _lines(console) == ["+ installed: AGENTS.md"]


def test_tool_output_label_is_inert() -> None:
    # AC-6; ADR-007 decision 8 (control and format characters removed from dynamic text)
    presenter, console = _presenter(terminal=False)

    presenter.tool_output(f"gra\nph{ESC}ify{RIGHT_TO_LEFT_OVERRIDE}", "done")

    assert _raw(console).splitlines() == ["graphify:", "    done"]
