# Provenance of ponytail-help

Source: https://github.com/DietrichGebert/ponytail
Revision: 96608e078b2d5ea607c5c3b8b5a54d1c1fba6846
Licence: MIT, Copyright (c) 2026 DietrichGebert (references/LICENSE.md)

## Upstream files

| File | SHA-256 |
|---|---|
| `skills/ponytail-help/SKILL.md` | `86ab0ce0af70cbeeeef499d5c884873b393f87f86401dcc45553662ce2c1eff9` |
| `LICENSE` | `fb1bc6909ac3ef82d5c22106e32ef682b0cff66788fa915fb9b53b15c9d2f3ab` |

## Adaptations

- The front matter is the one-line `name` and `description` that Orqlet's skill loader reads: the folded `description` is joined into one line; the `description` is reworded so that it needs no YAML quoting: colons, double quotes, backticks and dashes become plain punctuation or single quotes, with the same meaning.
- The help names only the six delivered skills. The sections "Band (Claude Code)", "Configure Default Mode" and "Update" (the band, the plugin hooks, the persistent default-mode configuration and the plugin update and client update commands) are replaced by a section "Not delivered here" that names those upstream features as not delivered.
- The Codex invocation line names the skills as Orqlet installs them (`$ponytail`, not the plugin form `$ponytail:ponytail`), and the slash-command line names the clients Orqlet renders for.
