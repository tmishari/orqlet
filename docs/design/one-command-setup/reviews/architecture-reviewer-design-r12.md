# Architecture review of the design, round 12

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-21T19:17:53Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the scope and the round 11 notes. This round reviewed the revision that answers Q-60: Graphify and tool preparation leave the task.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

At start (2026-11-21T19:17:53Z) the changed design files had the hashes below, and every artifact hash equalled the one recorded in `design/manifest.yaml`. The design was revised after this round in response to its non-blocking findings, so the hashes at save differ for these files, and round 13 reviews the content that will merge.

| File | sha256 at start |
|---|---|
| design/manifest.yaml | 929d50bd44dab7ff3c127879e2a1c27e6a1ab4aa002101cc20bcbeb85c821e11 |
| design/adr-006-bundled-skills-and-tool-preparation.md | c3cad6859cf93d70ed2d11e7cf008d09afb2140b2c194007e8b9e96ba242aae8 |
| design/component.md | acb8d692c99d4424ae1f8b516b3489f4d3a33ccc2201efec97ae091931305391 |
| questions.yaml | 4b2849d1ed8b86bfb7d362c8d9bc37b52fb5b4dedccbb98f1d189615b972dbd3 |

## Reviewer output (unchanged)

# Design review, round 12, architecture reviewer: one-command-setup (Q-60 revision)

**Verdict: approve.** I found no blocking finding, 4 non-blocking findings and 1 observation.

The withdrawal is complete across the 12 artifacts that the manifest binds (D-1 to D-12). Nothing there still refers to TB-2, ToolInstaller, tools-work, `uv tool list`, per-tool output, exit 4 for a missing uv or pipx, BC-48 or K-13.

- **Remaining "graphify" mentions are deliberate.** Each one is a Q-60 note, a statement that no graphify skill is rendered (BC-19), or the rejected alternative in ADR-006.
- **The remaining exit 4 uses are legitimate.** They cover "no supported assistant detected" and "non-interactive without `--yes`" (component.md:56, :192, :290 and ADR-007:35).
- **The owned-name patterns no longer include graphify.** ADR-002:37 lists `orqlet`, `orqlet-*` and `ponytail*`.
- **The security globs, K-2 and EC-6 match.** All three list the same four paths, with no tools adapter.
- **The trust boundaries agree in three places.** `scope.trust_boundaries`, EC-8 and context.md all list only TB-1 and TB-3; context.md:42 records that TB-2 is withdrawn.
- **The withdrawn and narrowed ids are handled.** BC-9, BC-10 and BC-45 remain as "Withdrawn (Q-60)" placeholders, and nothing else in the design cites them. ADR-006 decision 4 is a "Withdrawn" placeholder. The narrowed items (R-6, R-7, BC-7, BC-19, BC-22, BC-35, K-3 and EC-2/4/5/9) now name only Ponytail.
- **The "no network" claim holds for today's code.** `src/` contains no imports of urllib, httpx, requests, socket or http.client, and no git fetch, clone, pull or push.

**Nothing still needed was removed.** I could not diff against origin/main, so I checked this indirectly. Every plan acceptance criterion that cites BC-9, BC-10, BC-45 or ADR-006 decision 4 is about tool preparation or tool output (plan.yaml:67, 1774-1821, 1992, 2003, 2026). The Ponytail parts of ADR-006 (snapshots, provenance, adaptations, invocation) are all still there.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 12, role: architecture-reviewer}
verdict: approve
findings:
  - id: F-1
    severity: low
    blocking: false
    rule: design-format.md:28 and :32 (every requirement has a source); baseline "Do not guess"
    statement: >-
      Several answered requirement questions now lead to nothing in this design, and nothing says
      they moved to the separate task:
      - Q-2 (install uv and Python automatically);
      - the uv-preparation part of Q-35;
      - Q-39 (accepted supply-chain risk of tool preparation);
      - Q-46 (uv pin);
      - the Graphify part of Q-1.
      The answer to Q-60 marks only Q-56, Q-58 and Q-59 as superseded (questions.yaml:1315).
      R-7 dropped Q-2 and Q-35 from its sources (component.md:27). The manifest self_check still
      lists Q-35 and Q-39 among the questions of this design (manifest.yaml:203).
    evidence:
      - "questions.yaml:24-42 (Q-2), :684-703 (Q-35), :758-778 (Q-39), :905-928 (Q-46), :1312-1316 (Q-60)"
      - "component.md:3 and :27; manifest.yaml:203"
    required_change: >-
      State in component.md section 2, or in the ADR-006 Context, that Q-2, the uv part of Q-35,
      Q-39, Q-46 and the Graphify part of Q-1 move with tool preparation to the separate task
      (Q-60). Annotate or remove Q-39 in self_check.questions. If the person does not consider
      these covered by "tool preparation", ask a ledger question.
  - id: F-2
    severity: low
    blocking: false
    rule: baseline "Test the behaviour the business cares about"; ORQLET-TEST-001
    statement: >-
      The main behaviour of this revision has no acceptance criterion now that BC-9, BC-10 and
      BC-45 are withdrawn. That behaviour is "install prepares no tool and uses no network", and
      the manifest security note adds "starts no process" (component.md:52; manifest.yaml:124).
      Today it is ensured only by structure: the install use case reaches no ProcessRunner or Vcs
      port (component.md:136-152). BC-23 keeps sockets off in unit tests. BC-7 and BC-42 cover
      only dry runs.
    required_change: >-
      Add a criterion sourced from Q-60, or extend BC-2. With a fake process runner, a consented
      `install` starts no process, and it succeeds with sockets disabled.
  - id: F-3
    severity: low
    blocking: false
    rule: design-set integrity (the manifest binds artifacts by hash)
    statement: >-
      design/proposal.md sits in the design folder and was edited for Q-60 (lines 45-49, 63, 157).
      It is not a manifest artifact, so nothing binds or approves it. Parts of it contradict the
      bound design:
      - "Support remains Cursor, Codex and Claude Code" (line 49), against R-3, which has four clients;
      - "All sixteen ledger questions are answered" (line 157);
      - its own R and BC numbering, which differs from component.md.
      I could not check with git whether this predates the round.
    required_change: >-
      Ask the person whether proposal.md stays. If it does, mark it as the superseded pre-design
      proposal. Otherwise remove it, or stop editing it, so readers do not take it for the design.
  - id: F-4
    severity: info
    blocking: false
    rule: design-format.md:37 (an ADR compares the real alternatives)
    statement: >-
      Q-60 option 2, "move only the graphify skill" and keep tool preparation, is not among the
      rejected alternatives of ADR-006. The reason is in the ledger but not in the ADR: Q-35
      prepared uv only "so Graphify can be installed". The file name and the D-11 path still say
      "tool-preparation". Renaming would break earlier references, so leaving the name is
      acceptable.
    required_change: >-
      Add one rejected alternative: keeping tool preparation without Graphify has no purpose
      under Q-35.
  - id: O-1
    severity: info
    blocking: false
    rule: none (observation)
    statement: >-
      The self_check claims a ledger validation pass (manifest.yaml:197), but nothing shows it ran
      after Q-60 was added. There is no `orqlet validate design` entry for this revision. Unlike
      round 11 finding B-1, no check is claimed as passed that did not run.
    required_change: Optional. Record both validate runs for this revision, with their results.
```

## What the plan amendment must cover

These are not design findings.

- **P-9:** drop it, as the answer to Q-60 says (plan.yaml:1761-1830). Re-point `depends_on` and the EC-6 and EC-8 claims of later phases.
- **P-2:**
  - Remove the Graphify snapshot, `families/`, the shared references, the Apache and MIT licences and the pin `340268a…` (146-233, 256-295, 686).
  - Remove the graphify golden files for Claude Code, Cursor and Codex (388-421, 478-511, 568-604).
  - Reconsider `ClientSkill.family_references` if only Graphify used it (187-191).
  - Fix the `load_skills` list (156).
  - Q-51 and Q-52 lapse. Q-55's "seven bundled snapshots" becomes six. The README file count from Q-57 must be recounted.
- **Working copy in the main workspace:** `/Users/tmishari/Documents/orqlet/src/orqlet/workflow/skills/graphify/` already holds P-2 Graphify files, which are not in this branch. Remove them and rebuild MANIFEST.json.
- **P-1, AC-6:** remove "tool output" and the BC-45 source (62-67).
- **P-7 and P-8:** remove the Copilot graphify golden files (1617-1650) and graphify from the list at line 1489.
- **P-10:**
  - AC-17 and AC-22: remove `tool_output` and BC-45.
  - AC-19 (Q-39) and AC-23 (graphify names `orqlet install`): drop both.
  - AC-24: remove the graphify golden files and the MANIFEST entry, and the related file operations (2090-2132).
  - Remove the uv list-vector exception in the dry-run criterion (1920) and the graphify line in the objective (1891).
- **Coverage map (2403-2406):** remove BC-9, BC-10 and BC-45. Re-check BC-7 and BC-35, which P-9 AC-8 and AC-5 partly covered.
- **Unverified list (2427-2428):** K-3 is now Ponytail-only, so drop the uv and pipx items. Q-45 needs only the hook citations now.
- **Approval:** the person approves the amended plan again.

## Self-check

**What I examined:**
- In full: component.md, manifest.yaml, ADR-001, ADR-006, ADR-007, context.md, container.md, data-flow.md, sequence.md, design-format.md, the standards output and both round 11 notes.
- In the ledger: Q-1 to Q-6, Q-23 and Q-35 to Q-60.
- The parts of proposal.md, ADR-002, ADR-004 and ADR-005 that my searches matched.
- The graphify, tool and BC-9/10/45 lines of plan.yaml.
- `src/` for network imports.
- All at `/tmp/wt-guard` as it stood during this review.

**Not done:**
- The read-only mode refused every shell command. I computed no artifact hashes, so I did not check the manifest sha256 values. I ran no `git diff origin/main` and no `orqlet validate design` or `orqlet validate ledger`.
- I did not read as-is.md beyond searching it.
- The expected ORQ-E366 for the round 12 notes is not counted as a finding.

**Standards:** ARCH-001, ARCH-003, SEC-001, SEC-002, NOMODEL-001 and TEST-001 are not weakened. The revision removes a process starter and a trust boundary, and adds neither.

This is an additional check, not a guarantee. The person approves the revised design again.

## Author's responses

- F-1: Q-60 now lists `supersedes` Q-2, Q-39, Q-46, Q-51, Q-52, Q-56, Q-58 and Q-59, and ADR-006 Context names those and the Graphify part of Q-1 and the uv part of Q-35 as carried over to the separate task. Q-39 stays in `self_check.questions` because it was asked in that session; Q-60 records that it is superseded.
- F-2: added BC-48 (Q-60): with a fake process runner and sockets disabled, a consented `install` succeeds and starts no process.
- F-3: `design/proposal.md` is restored to its approved text; it is not a manifest artifact and this revision does not change it.
- F-4: ADR-006 now rejects keeping tool preparation without Graphify (Q-35, Q-60).
- O-1: `self_check.checks` records the validation runs of this revision with their results, and claims no review round.
- The plan amendment list is carried into the plan revision that follows this round.
