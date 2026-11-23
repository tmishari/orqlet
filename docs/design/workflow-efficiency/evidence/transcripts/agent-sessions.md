# Local Cursor agent sessions of this project

Source: the local Cursor agent transcripts of this project (JSON lines, main agent plus subagents): 47 sessions, the current research session excluded.
Retrieved: 2026-11-23T09:35:00+00:00
Tool: Cursor Shell, a one-off Python script that reads the transcripts and writes nothing back
Processed: no
Data class: internal

The counts below are a summary made by the script, not verbatim text. The transcripts hold the
role, the text and the tool calls of each message. They hold no timestamps, no token counts and no
tool results, so elapsed time, tokens and result sizes cannot be measured from them.

## Method

- A session's skill is the first `Skill Name:` attached to its first user message.
- A check is a Shell tool call whose command contains `ruff check`, `ruff format`, `mypy`,
  `lint-imports`, `pytest`, or `orqlet validate|gate status|review|standards for|evidence cite|doctor|sync`.
- A pytest segment is targeted when its arguments name `tests/`, `::` or `-k`; otherwise it is full.
- An identical rerun is the same normalised command again with no edit tool call, and no Shell call
  that commits, formats, fixes or redirects, in between.
- A repeat read is a second or later `Read` of the same path by the main agent, including paged reads.
- A session may span several turns and several plan phases; the transcripts do not mark phase
  boundaries, so counts per phase are not computed.

## Sessions by skill

| Skill | Sessions | Tool calls, median per session | Check commands | Identical reruns with no edit between |
|---|---|---|---|---|
| orqlet-research | 4 | 1128.5 | 93 | 0 |
| orqlet-design | 4 | 505.5 | 58 | 0 |
| orqlet-plan | 3 | 143 | 56 | 0 |
| orqlet-implement | 27 | 492 | 1579 | 0 |
| other or none | 9 | not computed | 1585 | 7 |

## Implement sessions (n = 27), per-session counts

| Command segment | Median | Max | Total |
|---|---|---|---|
| pytest, full suite | 15 | 134 | 615 |
| pytest, targeted | 5 | 56 | 286 |
| mypy | 8 | 58 | 308 |
| ruff check | 10 | 47 | 305 |
| lint-imports | 5 | 23 | 132 |
| orqlet gate status | 7 | 51 | 241 |
| orqlet validate plan | 2 | 14 | 75 |
| orqlet review prepare | 4 | 26 | 156 |

## Reads, outputs and replies

| Skill | Main-agent Read calls | Repeat reads of the same path | Last reply of a turn, words: median / max |
|---|---|---|---|
| orqlet-research | 177 | 55 | 262 / 1045 |
| orqlet-design | 114 | 22 | 180 / 678 |
| orqlet-plan | 84 | 12 | 791.5 / 1726 |
| orqlet-implement | 1073 | 363 | 257 / 2162 |

- The most re-read paths were `docs/design/dynamic-model-profiles/plan.yaml` (64 repeat reads),
  `docs/design/one-command-setup/plan.yaml` (25) and `docs/design/phase-skill-contracts/plan.yaml` (18).
- Cursor saved 93 oversized tool results for this project (about 10 MB). Orqlet sessions opened them
  68 times (research 40, implement 28). By their first lines, 15 are pytest output (about 3.8 MB),
  5 are git diffs, and most of the rest are fetched documentation pages.

## The reported repetition

No user message in the transcripts contains "five or six". One implement session
(`5a5296a0`) records, in the agent's own text, that `orqlet review prepare` "ran five times and
left five packets behind". Which session the person's report refers to is not established.
