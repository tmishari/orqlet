# ADR-005: Harness² is a source of ideas only: no dependency, no command, no integration

Status: proposed.

## Context

- You chose to borrow the ideas into Orqlet only (AS-IS A-5a). The team has no Vertex AI access, approved model route or budget (A-2) and no Linux machine (A-3); Harness² documents Linux and Vertex AI and is classified POSIX only (H-07, H-08, H-09).
- Orqlet never invokes models or starts agents (R-01, ORQLET-NOMODEL-001), and the workflow is fixed by the CLI release (design §6.15), while Harness² runs model sessions and rewrites skills, subagents, prompts, guardrails and plugins automatically (S-06, S-16).
- The source has no documented library API, hard-codes its executors and benchmarks, bypasses approvals and the sandbox in the Codex executor, passes keys to children and prints a bridge key, and fingerprints runs with SHA-1 (S-02, S-14, S-16, S-17, S-13). It is version 0.1.0 and "not an officially supported Google product" (H-06).

## Decision

1. Orqlet takes no dependency on Harness², adds no command that runs it, and generates no configuration for it.
2. Ideas are taken only through ADR-001 to ADR-004. Every other idea is **not adopted**, as follows.

| Idea or pattern in Harness² | Disposition |
|---|---|
| The Propose–Probe–Compose loop and the improvement library | Not adopted: needs model sessions, a judge and an unbuilt corpus, and would rewrite protected files |
| A skill must be named in the always-on text; scripts must compile; hooks file shape; path allow-list for edited files | Deferred: they apply to extension skills and hooks, which Orqlet does not ship yet; they return when extension skills or hooks are designed (no section of the proposal designs them yet; §12.7 covers standards-pack content only) |
| Always-on size caps (24,000 and 8,000 characters) | Not adopted: the proposal already sets Orqlet's own cap for the `AGENTS.md` managed block, a design value that is not built (proposal §12.1, 60 lines and 4 KiB, marked as a proposed initial value) |
| Bypass flags, inherited environments, printing a key, a plaintext key file | Rejected as patterns: none may appear in generated configuration or documentation; no automatic check enforces this, it rests on review (ORQLET-SEC rules are `review` rules) |
| SHA-1 run fingerprints | Rejected: SHA-256 only |
| Hard-coded executor and benchmark if-chains | Rejected: Orqlet's seams are ports behind contracts |

3. The decision is revisited only if all of these hold: a Linux runner, an approved model route with a budget, a decision on sending task data and trajectories to the model endpoints (the question Q-4 of this task, which was open when the AS-IS was accepted and was then superseded by your answer to Q-5, because no data goes to a model endpoint while only ideas are borrowed), and a repository-specific task set with a judge.

## Consequences

- No new runtime, platform or cost requirement, and no new attack surface.
- The hardening patterns above are recorded so that the later evaluation harness avoids them.
- A reader who wants the optimiser itself has a written reason and a list of conditions.

## Rejected alternatives

- **Run Harness² as an external experiment now.** Blocked by A-2 and A-3 and by the missing corpus and judge.
- **Integrate it as an optional subcommand.** Violates R-01 and the fixed-workflow rule.
- **Fork or vendor its code.** No documented API, a hard-coded structure and a SHA-1 and bypass-flag posture that Orqlet's standards exclude.
