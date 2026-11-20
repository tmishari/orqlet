# ADR-005: One behavioural foundation and its delivery per client

Status: proposed. Task: `one-command-setup`.

## Context

Three guidance sources overlap:

- the AGENTS.md baseline (A-44);
- Ponytail, which stays active for a session once invoked (A-58);
- the Karpathy-inspired skill (A-56), which has no licence file and no named copyright holder (A-55).

The person ruled:

- The upstream text is not vendored. Any genuinely new points are written in Orqlet's own words, with an attribution link (Q-27).
- There is one coherent foundation: no three overlapping sets in every session, and no new mandatory command or workflow. Simplicity keeps validation at trust boundaries, error handling, accessibility and approvals (Q-28).

The overlap table of the AS-IS file lists three points not stated in Orqlet or Ponytail:

- present several interpretations instead of choosing silently;
- mention unrelated dead code rather than delete it, and remove only the orphans the change created;
- use a step-then-verify plan for multi-step work outside a phase plan.

C-6 shows the upstream "no error handling for impossible scenarios" line conflicting with the baseline.

Global guidance must reach every client (Q-7). The documented user routes are:

| Client | Route |
|---|---|
| Claude Code | `~/.claude/rules` (evidence `global-setup.md`) |
| Codex | `$CODEX_HOME/AGENTS.md` (A-17) |
| Cursor | User Rules, which are not on the file system (A-16). One guided step is allowed (Q-9) |
| Copilot | Session-start `additionalContext` (A-40). No user instruction file is cited |

## Decision

1. **Content.** The foundation is the baseline section "How to work", plus the three points above in Orqlet's own wording and one attribution link to the upstream repository at revision 2c60614.
   - The upstream "no error handling" line is left out (C-6).
   - Ponytail's skills stay skills, invoked when the person wants them. They are not part of the always-on text.
   - The text is under 6,000 characters (BC-21).
2. **One source.** The workflow package holds the foundation once. The project baseline block in AGENTS.md and every global copy are rendered from it, so they cannot drift apart within one release.
3. **Global delivery.**

   | Client | Delivery |
   |---|---|
   | Claude Code | `~/.claude/rules/orqlet-foundation.md` |
   | Codex | a managed block in `$CODEX_HOME/AGENTS.md` |
   | Cursor | the guided User Rules step, with the text saved in the data directory and its path printed |
   | Copilot | the session-start hook, only when the workspace lacks the Orqlet baseline block |

4. **Precedence sentence.** Every global copy starts with one sentence: when the project's AGENTS.md carries the Orqlet baseline, the project's version applies.
5. **Ceremony is unchanged** (Q-36). The step-then-verify point applies to work outside a phase plan and does not replace any phase.

## Consequences

- In an Orqlet project, Claude Code and Codex read the same foundation twice: once from the project and once from the user scope. This is redundancy in context, not a second instruction set, and the precedence sentence settles a version difference. The cost is a few thousand characters of context per session.
- A repository can switch the global foundation off for its own sessions. The precedence sentence defers to a project `AGENTS.md` that carries the baseline block, and under Copilot the marker alone suppresses the packaged text. This adds little to what a hostile repository can already say through its own `AGENTS.md`, and the person accepted it, so that a project's pinned baseline wins (Q-43).
- Cursor needs one manual paste. `install` reports it as a `host step` until the person confirms; that confirmation is not proof of native verification.
- Copilot receives the foundation only through a hook. Where hooks are disabled, Copilot sessions outside Orqlet projects have no foundation.
- Changing the baseline text changes the global copies on the next `install`, which keeps them aligned.

## Rejected alternatives

- **Vendoring the Karpathy skill or adding it as a fourth skill.** Q-27 rules it out, and it would be a third overlapping set (Q-28).
- **Making Ponytail always on.** Its default level would run in every session alongside the baseline, which makes two overlapping sets. Its ultra-level push-back is also not wanted by default (A-58).
- **A Cursor plugin with an always-applied rule instead of the guided step.** Whether a plugin rule reaches the agent as a User Rule does is unverified (U-3). Enterprise disables local plugins by default (A-36). ADR-001 of `mcp-or-plugins` limits plugin output (A-23).
- **Injecting the foundation through session-start hooks for every client.** Codex caps context at 2,500 tokens by default (A-37), and Codex trust and IDE-extension support are open (U-1). Static files are more reliable where a documented location exists.
