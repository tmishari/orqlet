# Ponytail main skill text

URL: https://raw.githubusercontent.com/DietrichGebert/ponytail/96608e078b2d5ea607c5c3b8b5a54d1c1fba6846/skills/ponytail/SKILL.md
Revision: 96608e078b2d5ea607c5c3b8b5a54d1c1fba6846 (the revision of ponytail.md)
Retrieved: 2026-11-20T11:56:00+02:00
Tool: curl
Processed: no
Data class: public

Excerpts are verbatim, shortened with "..." only.

1. Licence - LICENSE at the revision begins "MIT License" and "Copyright (c) 2026 DietrichGebert"; the skill front matter has "license: MIT".
2. Session scope - "Active for the whole session until the user says \"stop ponytail\" or \"normal mode\"."
3. Scope first - "List every place your change must reach: callers, tests, fixtures, config, exports."
4. Order of options - "1. Does it need to exist? ... 2. Already in this codebase ... 3. Standard library or a platform feature? ... 4. An installed dependency? Use it. Never add a dependency for a few lines."
5. Structure - "Keep the structure the codebase already has: its layers, interfaces and conventions."
6. Deletion - "Deletion beats addition."
7. Tests - "new non-trivial logic (a branch, a loop, a parser, money or security, or a whole new script or app) leaves one small test or an assert-based self-check. Trivial changes need none."
8. Guard - "Never cut: validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs, anything the user asked for."
9. Reply - "End your reply with one or two lines: what you skipped or did not check, and any risk the user must know."
10. Levels - "Levels: lite, full (default), ultra." / "**lite** | Build what was asked. Name the smaller option in one line and let the user pick." / "**full** | The rules above. Default." / "**ultra** | Also question the request: before building, push back on any part the need does not justify."
