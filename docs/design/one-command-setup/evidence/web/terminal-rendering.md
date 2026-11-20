# Terminal rendering: Rich 15.0.0 and NO_COLOR

Retrieved: 2026-11-20T11:57:00+02:00
Tool: curl of the Rich v15.0.0 documentation sources on GitHub and of https://no-color.org; read-only inspection of the installed Rich package in the orqlet uv tool environment
Processed: no
Data class: public

Excerpts are verbatim, shortened with "..." only.

## Rich console documentation

URL: https://raw.githubusercontent.com/Textualize/rich/v15.0.0/docs/source/console.rst

1. Detection - "If Rich detects that it is not writing to a terminal it will strip control codes from the output."
2. Interactive mode - "Rich will remove animations such as progress bars and status indicators when not writing to a terminal"
3. TERM - "Setting the environment variable ``TERM`` to ``\"dumb\"`` or ``\"unknown\"`` will disable color/style and some features that require moving the cursor, such as progress bars."
4. FORCE_COLOR - "If the environment variable ``FORCE_COLOR`` is set and non-empty, then color/styles will be enabled regardless of the value of ``TERM``."
5. NO_COLOR - "If the environment variable ``NO_COLOR`` is set, Rich will disable all color in the output. ``NO_COLOR`` takes precedence over ``FORCE_COLOR``." and "The ``NO_COLOR`` environment variable removes *color* only. Styles such as dim, bold, italic, underline etc. are preserved."
6. CI - "If you want Rich output in CI or Github Actions, then you should set ``TTY_COMPATIBLE=1`` and ``TTY_INTERACTIVE=0``."
7. Legacy Windows - "``\"windows\"`` Can display 8 colors in legacy Windows terminal. New Windows terminal can display \"truecolor\"."
8. Width - "Note that when writing to a file you may want to explicitly set the ``width`` argument if you don't want to wrap the output to the current console width."

URL: https://raw.githubusercontent.com/Textualize/rich/v15.0.0/docs/source/appendix/box.rst

9. Box glyphs - "Some of the box drawing characters will not display correctly on Windows legacy terminal (cmd.exe) with *raster* fonts, and are disabled by default."

## Installed package source (rich 15.0.0, site-packages of the orqlet tool environment)

10. box.py line 81 - "if options.ascii_only and not box.ascii:" substitutes an ASCII box.
11. console.py line 143 - the `ascii_only` property of the console options; line 648 - `safe_box: bool = True` in the Console constructor.
12. Not found - no automatic ASCII substitute for arbitrary Unicode icon characters was found in the inspected files.

## NO_COLOR convention

URL: https://no-color.org/

13. "Command-line software which adds ANSI color to its output by default should check for a NO_COLOR environment variable that, when present and not an empty string (regardless of its value), prevents the addition of ANSI color."
