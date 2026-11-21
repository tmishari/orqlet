# ADR-007: Terminal presentation of `orqlet install`

Status: proposed. Task: `one-command-setup`.

## Context

Q-29 asks for:

- a recognisable ASCII or ANSI banner;
- icons, each with a text label, and readable states: detected, already configured, installed or registered, host step, and conflict or failure with a recovery action;
- support for wide and narrow terminals, and for bash, zsh and PowerShell;
- an ASCII fallback, and respect for `NO_COLOR`;
- plain output when non-interactive, redirected or in CI, and JSON with no artwork;
- no repeated banners or delays, quiet hooks, and no images;
- reuse of installed libraries before adding one.

Orqlet's renderer prints plain text with no colour (A-50). Rich 15.0.0 is already installed through Typer, with no direct dependency (A-51). Rich handles non-terminal output, `TERM`, `NO_COLOR`, `FORCE_COLOR`, CI variables and width (A-53). It substitutes ASCII only for boxes, not for icons (A-54). Glyph support on legacy Windows consoles and the narrowest width are open (U-6, U-7).

## Decision

1. **Scope.** Only the human output of `install` and `uninstall` changes. Every other command keeps the plain renderer, and `--json` keeps the existing envelope.
2. **Library.** Rich is used through a `Console` created in `orqlet.interface`. It is declared as a direct dependency at the locked version (`rich==15.0.0`, manifest EC-7), so that a Typer update cannot remove it.
3. **Banner.** It is ASCII-only (letters, `/`, `\`, `-`, `o`) and printed once at the start of an interactive run. Colour is only an accent, never the carrier of meaning.
4. **States.** Each line shows an icon, a word label and the subject. The label is always present, so meaning never depends on a glyph or a colour:

   | State | Unicode | ASCII |
   |---|---|---|
   | detected | `•` | `*` |
   | already configured | `=` | `=` |
   | installed / registered | `✓` | `+` |
   | host step | `→` | `>` |
   | conflict / failed | `✗` | `x` |

   Unicode is used only when the console encoding is UTF-8 and Rich does not report a legacy Windows console.
5. **Plain mode** is used when output is not a terminal, `NO_COLOR` is set and non-empty, `TERM` is `dumb`, or a CI variable is set: no banner, no ANSI codes, ASCII icons. An interactive prompt is never shown in plain mode; `--yes` is required there (exit 4 otherwise).
6. **Narrow mode.** Below 60 columns the banner is replaced by the one-line title `orqlet install`, and each state line wraps under its label.
7. **No animation, no spinner, no delay.**
8. **Dynamic text is inert.** File names and root paths are printed with Rich markup off. Before printing, control characters and Unicode bidirectional and format characters (category Cf) are removed, and newlines too. So a file name cannot restyle the terminal, reorder text or forge a status line.

## Consequences

- The first contact with Orqlet looks deliberate and stays readable in logs, CI and screen readers. The text labels carry the meaning everywhere.
- A new direct dependency line is added, but no new package is installed.
- Two renderers now exist: plain for most commands, Rich for `install` and `uninstall`. Keeping Rich out of the inner layers (BC-25) stops it spreading.
- The 60-column threshold and the glyph fallback are design values. Qualification on bash, zsh and PowerShell confirms them (U-6, U-7), and a change needs only this ADR's values to change.

## Rejected alternatives

- **Hand-written ANSI codes in the plain renderer.** This duplicates the detection of `NO_COLOR`, `TERM`, CI and width that Rich already has (A-53).
- **A new terminal library (for example, one with images or animations).** It would add a dependency, and Q-29 excludes images and artificial delays.
- **Styling every command.** Q-29 asks for no constant banners, and existing output is relied on in logs (A-50).
- **Using Rich only through Typer's transitive install.** It works today, but it breaks silently if Typer drops Rich (A-51).
