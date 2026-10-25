# ADR-003: No change to the review skill about agreement between reviewers

Status: accepted by the person on 2026-10-25, in conversation. No pull request was merged.

## Context

- The Harness² composer prompt says "Agreement is support, not independent proof" and "A defect in 1/{k} is noise"; its editor prompt says every edit must trace to a moment in a trajectory (AS-IS S-11).
- Orqlet's reviewer roles already require evidence: findings use `orqlet.finding/v1` and "A claim without evidence is an observation and never blocks" (`src/orqlet/workflow/roles/orqlet-arch-reviewer.md`). The evidence-trace rule is in place.
- `orqlet-review` step 8 tells the main agent to report findings "blocking ones first" and says nothing about weighing a finding that both reviewers report against one that only one reports (`src/orqlet/workflow/skills/orqlet-review/skill.md:18`).
- The AS-IS records no case in Orqlet where agreement between reviewers was taken as proof or silence as disproof. A sentence in this skill would be a change to protected workflow text: a manifest rebuild, a version bump, new golden files and a new protected-set digest for every adopter.

## Decision

Make no change to the `orqlet-review` skill or to the reviewer roles for this idea. Record it: if a review round shows that agreement was treated as proof, or that a finding was closed because the other reviewer did not report it, add one sentence to step 8 then, as a patch-level change (design §20.8).

## Consequences

- No protected-text change for this reason; the only protected text changed by this task is the `orqlet-research` description (ADR-001).
- The risk stays covered only by the existing evidence rule and the human approver.

## Rejected alternatives

- **Add the sentence to step 8 now.** It costs a protected-text change for a problem that nobody has observed here; the baseline says to add a pattern only when you can say which problem it solves.
- **Add it to the reviewer roles.** The reviewers do not see each other's findings, so it would not apply to them.
- **Add it to the skill and take the release that ADR-001 needs anyway.** The release is a reason the cost is small, not a reason the sentence solves a problem; the baseline asks for the problem first.
