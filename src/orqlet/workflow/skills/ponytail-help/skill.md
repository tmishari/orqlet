---
name: ponytail-help
description: Quick reference for ponytail levels, skills and commands. One-shot display. Use for /ponytail-help, 'ponytail help', 'how do I use ponytail'.
---

# Ponytail Help

Display this reference card when invoked. One-shot, do NOT change mode,
write flag files, or persist anything.

## Levels

| Level | Trigger | What change |
|-------|---------|-------------|
| **Lite** | `/ponytail lite` | Build what was asked, name the smaller option in one line. |
| **Full** | `/ponytail` | The smallest complete change, a check where the logic needs one, and a reply that names what was skipped and any risk. Default. |
| **Ultra** | `/ponytail ultra` | Also questions the request and pushes back before building. |

Level sticks until changed or session end.

## Skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| **ponytail** | `/ponytail` | Lazy mode itself: least new code, clear replies that name skipped work and risks. |
| **ponytail-review** | `/ponytail-review` | Quality review of a diff: bugs, security, load, missing tests, speed, what to cut. Each finding says what goes wrong and how to fix it. |
| **ponytail-audit** | `/ponytail-audit` | The same quality review for the whole repo, ranked. |
| **ponytail-debt** | `/ponytail-debt` | Harvest `shortcut:` comments into a tracked ledger. |
| **ponytail-gain** | `/ponytail-gain` | Measured-impact scoreboard: less code, less cost, more speed. |
| **ponytail-help** | `/ponytail-help` | This card. |

In Codex, invoke the skills with `$ponytail`, `$ponytail-review`, `$ponytail-help` and so on.
Claude Code, Cursor and Copilot use the slash-command forms above.

## Deactivate

Say "stop ponytail" or "normal mode". Resume anytime with `/ponytail`.
`/ponytail off` also works.

## Not delivered here

This package delivers the six skills above as Markdown files only. These upstream Ponytail
features are not delivered here:

- the band above the prompt (`/ponytail band`) and its session import;
- the plugin hooks that switch a level on at session start;
- the persistent configuration of a default mode (`PONYTAIL_DEFAULT_MODE` and the config file),
  and the plugin's update flow.

So the level is `full` when you start `/ponytail`, and it lasts for the session.

## More

Full docs + examples: https://github.com/DietrichGebert/ponytail
