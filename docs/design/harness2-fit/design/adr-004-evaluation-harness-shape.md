# ADR-004: Record the shape of the evaluation harness in the proposal (milestone M7, no code now)

Status: accepted by the person on 2026-10-25, in conversation. No pull request was merged.

## Context

- Design §21 plans an evaluation of instruction and profile bundles on representative tasks, with deterministic fixture tests first and a model-in-the-loop harness later; the corpus and the harness are unbuilt (milestone M7, AS-IS O-06). Section 21.1 says the harness is separate from Orqlet: "an evaluation harness (Orqlet runs no model)".
- Harness² shows a separation of concerns that the plan does not yet state. The recursion code takes an adapter (runs a task, returns outputs and a trajectory) and a proposer, and a local demo swaps in scripted classes for both (AS-IS S-21). Failed evaluations stay unscored and are not counted as zero (S-20). Resume depends on a stored configuration that must match and on per-run completion marks (S-13).
- Two Harness² controls are weaker than they sound, and Orqlet's rules must not inherit that: the path and marker guards cover only the improver's and the selector's context, and the executor's network is unrestricted (S-12; H-10 records an executor downloading its grading rubric); and the session ledger counts the rollouts and the improver sessions, with the selector and reflector sessions outside it (S-24, C-18).
- The run marker uses a SHA-1 fingerprint (S-13), which Orqlet's standards forbid (ORQLET-SEC-003).

## Decision

Add one subsection to the proposal (Section 21.7, "What the evaluation harness borrows") that records these rules for M7 and changes no code:

1. **Boundary.** The harness is development tooling outside `src/orqlet`. The shipped CLI never imports it, and Orqlet itself still never calls a model or starts an agent (ORQLET-NOMODEL-001). Any process the harness starts goes through `ProcessRunner` (ORQLET-SEC-001).
2. Two swappable seams, an executor seam (run one task with one bundle on one client and return outputs and a trajectory) and a scorer seam, each with a scripted fake, so the harness logic is tested with no model call.
3. Every comparison includes the unchanged reference bundle at the same budget as the arm under test.
4. Each run declares the number of model sessions it expects per arm, counting every model session the harness starts (executor, judge and any other), and fails when the count differs.
5. A run is named by task set, client, bundle, budget and seed; a stored configuration must match for a resume; completion marks use SHA-256 content digests.
6. A failed evaluation is unscored, never zero.
7. Scorer artifacts and expected answers are never placed in the executor's workspace; the rule is by construction (separate directories and a check that lists the executor workspace), not by a path or text filter.
8. A preflight that checks configuration without any model call, as `doctor` does.

## Consequences

- M7's plan starts from stated rules instead of rediscovering them; the proposal gains about one page.
- The rules bind nothing until M7 is planned; the corpus and a judge for Orqlet's own workflow remain unbuilt (AS-IS U-8).

## Rejected alternatives

- **Build the harness now.** No corpus, no approved model route (AS-IS A-2) and no Linux runner (A-3) exist.
- **Say nothing until M7 is planned.** The seams, the session count and the unscored-not-zero rule are cheap to state now and costly to retrofit.
- **Copy Harness²'s guards (path globs and marker scan) as the isolation rule.** They protect only part of the context (S-12) and the marker scan proves little (ADR-002).
