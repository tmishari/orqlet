# Security review of the design, round 12

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-21T19:17:53Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the scope and the round 11 notes. This round reviewed the revision that answers Q-60: Graphify and tool preparation leave the task.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

At start (2026-11-21T19:17:53Z) the changed design files had the hashes below, and every artifact hash equalled the one recorded in `design/manifest.yaml`. The design was revised after this round in response to its non-blocking findings, so the hashes at save differ for these files, and round 13 reviews the content that will merge.

| File | sha256 at start |
|---|---|
| design/manifest.yaml | 929d50bd44dab7ff3c127879e2a1c27e6a1ab4aa002101cc20bcbeb85c821e11 |
| design/adr-006-bundled-skills-and-tool-preparation.md | c3cad6859cf93d70ed2d11e7cf008d09afb2140b2c194007e8b9e96ba242aae8 |
| design/component.md | acb8d692c99d4424ae1f8b516b3489f4d3a33ccc2201efec97ae091931305391 |
| questions.yaml | 4b2849d1ed8b86bfb7d362c8d9bc37b52fb5b4dedccbb98f1d189615b972dbd3 |

## Reviewer output (unchanged)

**Verdict: approve.** I found no blocking finding. The revised design's security position is complete. TB-1 and TB-3 are intact, and removing tool preparation took nothing away that a remaining part needs. There is one low, non-blocking finding about the ledger, and two info notes.

## What still holds after the removal

- **TB-1 (user client folders):** the controls are unchanged (`context.md`:38-39, ADR-002 decision 1a). The proposed SAFE-001 amendment text (ADR-002:100) correctly drops the "tools scratch folder" exemption and the tools-adapter sentence. The approved copy has them, and nothing else in the text changed.
- **TB-3 (hook payloads):** the controls are unchanged (`context.md`:40; ADR-004 decisions 1a and 5–7; BC-14 to BC-17). `data-flow.md` says no install or hook data reaches a process or the network.
- **ExecutableLocator:** its definition matches the approved copy exactly (`component.md`:168 and :179). It is still used by install and status (lines 147-148), ADR-004 decision 7, BC-38 and the failure rows at :200 and :204. Only the uv/pipx-specific rule ("only absolute PATH elements") went, together with what it served.
- **ProcessRunner and GitRunner:** ProcessRunner stays in the port list (`container.md`:19), and Git is the only process starter (`container.md`:75). I opened `git_runner.py` to check the citation. It still has fixed overrides (fsmonitor off, empty hooks path), an allow-list that includes `rev-parse`, a scrubbed environment, a timeout and an output cap. That is what `status` relies on.
- **Redaction:** only the tool-output redaction and the `tool_output` field were removed. Their only producer was tool preparation. The output rules that remain are intact: inert human output (ADR-007 decision 8, BC-22) and the status and hook field rules (ADR-001 decision 3, ADR-004 decision 1a, BC-11, BC-14, BC-15).
- **Manifest:** TB-2 and the `adapters/process/tools.py` security glob are gone. The security note no longer cites Q-39 and still lists the accepted risks Q-40 to Q-44. BC-9, BC-10 and BC-45 are marked withdrawn. The round 11 self-check problem (S-6, a review result recorded early) does not recur.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 12, role: security-reviewer}
verdict: approve
findings:
  - id: S-1
    severity: low
    blocking: false
    rule: ledger consistency; ORQLET-SEC-002 (intent)
    statement: >-
      Q-60 marks only Q-56, Q-58 and Q-59 as superseded, and only in its answer text. It sets no
      `supersedes` list and changes no status, although the ledger contract supports both.
      Answers that now contradict the design still read as `answered`:
      - Q-35: install prepares uv over the network.
      - Q-39: the person accepts the supply-chain risk, "stated in the design and in install output".
      - Q-46: the uv pin.
      - Q-51 and Q-52: the graphify snapshot.
      - Q-56, Q-58 and Q-59: the graphify guards.
      - Q-1 and Q-2, in part.
      A plan or implementation phase that reads the ledger could bring network tool preparation
      back, or treat Q-39 as an accepted risk that still applies.
    evidence:
      - "questions.yaml:1312-1316 (Q-60 answer, prose only); :697-703 (Q-35); :773-778 (Q-39); :924-928 (Q-46)"
      - "src/orqlet/application/contracts/question_ledger.py:25,49-50 (status `superseded`, `supersedes`, `invalidates`)"
    required_change: >-
      Record which questions Q-60 supersedes, fully or in part, as the ledger rules allow
      (`supersedes` on Q-60 and/or status changes), and include Q-35, Q-39 and Q-46.
  - id: S-2
    severity: info
    blocking: false
    rule: scope carry-over
    statement: >-
      The plan is not yet revised: plan.yaml mentions P-9, tools.py or graphify 96 times. The main
      workspace has an uncommitted graphify skill at src/orqlet/workflow/skills/graphify/. The plan
      revision has to drop P-9 and graphify from P-2, the tests that go with them and the tools.py
      security glob, so that no graphify text ships under BC-19.
    evidence: "plan.yaml (rg count); /Users/tmishari/Documents/orqlet/src/orqlet/workflow/skills/graphify/skill.md"
    required_change: Check this in the plan review.
  - id: S-3
    severity: info
    blocking: false
    rule: ADR-006 decision 3
    statement: >-
      The six Ponytail skills are not strictly read-only. ponytail-debt tells the agent to run
      `git grep --no-index --exclude-standard`, offers an optional `git blame`, and writes a ledger
      file only after asking. This matches A-9 ("asks before persisting"), so the design is
      consistent. The agent runs these with the host's tools, not Orqlet, so SEC-001 is not
      involved. A plain clone brings no Git config, so these commands run no repository-supplied
      program. No other Ponytail skill names a command, an install step or a hook to run.
    evidence: "working copy src/orqlet/workflow/skills/ponytail-debt/skill.md:15,31,40 (not a commit); evidence/web/ponytail.md:15"
    required_change: >-
      Optional: state in ADR-006 that ponytail-debt can write one file after the person says yes.
```

## Self-check

- **What I examined:**
  - All of ADR-006, `context.md`, `component.md`, `container.md`, `data-flow.md`, `sequence.md`, `proposal.md`, ADR-001, ADR-004 and ADR-007.
  - In ADR-002: the amendment text and decision 1a.
  - In `manifest.yaml`: trust boundaries, security globs, the expected changes, considerations, the self-check and the reviews list.
  - In the ledger: Q-1 to Q-3 and Q-35 to Q-60.
  - In `as-is.md`: A-9, A-12 and A-29.
  - The round 11 notes and the standards output.
- **How I compared with the approved design:**
  - The read-only sandbox refused every shell command, so I ran no `git diff origin/main`, no hashing and no `orqlet validate`.
  - Instead I compared with the design copy in the main workspace, which contains tool preparation. I have not confirmed that it is byte-identical to `17e162c`.
- **What I did not examine:**
  - `plan.yaml` in detail.
  - `design-format.md` and the evidence files other than the two Ponytail files.
  - Whether the status JSON error output can carry Git stderr text. This is unchanged by this revision.
- **Revision:** the files in `/tmp/wt-guard` at review time.
- **Expected warning:** ORQ-E366 for the round 12 notes, as the brief says.
- This is an additional check, not a guarantee.

## Author's responses

- S-1: Q-60 now lists `supersedes` Q-2, Q-39, Q-46, Q-51, Q-52, Q-56, Q-58 and Q-59; its statuses stay answered so that their answers remain readable, which the ledger contract requires for an answered question. ADR-006 Context names the partly superseded Q-1 (Graphify) and Q-35 (uv).
- S-2: the plan revision that follows drops P-9 and Graphify, and the implement branch drops the uncommitted graphify files.
- S-3: no change; ponytail-debt asks before it writes, as A-9 records.
