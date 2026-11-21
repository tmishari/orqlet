# Architecture review of the design, round 13

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-21T19:20:50Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the scope and the round 12 notes. This round reviewed the content that will merge for the Q-60 revision.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-21T19:20:50Z) and at save (2026-11-21T19:21:55Z) are identical, and every design artifact hash equals the one recorded in `design/manifest.yaml`. The reviewed content is the content that will merge.

| File | sha256 |
|---|---|
| design/manifest.yaml | 970fed48fbf6253c8ddd89a449e537b86bf0396fa1f0aa55b2724f8f71b19b34 |
| design/adr-001-install-command-entry-skill-and-status.md | dd37a7501391ceed0e713d8da9190f2f5eb6de9ddb6196beba99eb697c3b8013 |
| design/adr-002-user-scope-root-journal-and-manifest.md | 0b890be14e93582429f978dcb938697aaa8e51f70be52ad6c65e6e6a6c832a43 |
| design/adr-003-copilot-client-adapter.md | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004-advisory-native-hooks.md | 4325a150a453f18c1602ea2a1f702e0d6bbae376459f8c67fbd32e9bfccf90af |
| design/adr-005-behavioural-foundation.md | 9e5c51e9ce4b010dec0647a71ef326fb49369916d1d83583aaa1fb93c789119d |
| design/adr-006-bundled-skills-and-tool-preparation.md | bf3151f13feb9a0e88ab22bb8738f4a55f61ad6224d341fab28876ec14f17217 |
| design/adr-007-terminal-presentation.md | 57819e41031b80160ca84014ecbadf69e7e1653b5c8c059ad30515bef425e6cb |
| design/component.md | 509f39848df972a672155a636fb89f7dca4c383020fd7273df68a1f843369e44 |
| design/container.md | 90721a62908fb297cfb2ec18a91a79f69d5e1423a1bc08d3293baec0e88fd7da |
| design/context.md | a45782f35b499e7e4ea8e99d55789e17088e9b2a34d2130b182ba7fb56e417bb |
| design/data-flow.md | 58b25a0a6b0a255baa1ac43c8926e96e622a582be18129520038c9fe20d85117 |
| design/proposal.md | 8c5869fac7543feebd0c403d0fe7430eca1749ccf7df12bbb0a5bedc3a9c359e |
| design/sequence.md | a33c114656afc2a1d461f51795e10c9f0d89cc600fd81e7d29983b082257a33f |
| questions.yaml | e8350e3fd7175a709bd1e11ed8dba856708ff3a99ad82c8d3d2f204a8d4fd59f |

## Reviewer output (unchanged)

**Verdict: approve.** I found no blocking finding. All five round 12 items are resolved, and nothing new contradicts the Q-60 revision. I have three low findings and two info notes, all non-blocking.

## How the round 12 findings were resolved

- **F-1 (questions that led nowhere): resolved.**
  - Q-60 now carries a `supersedes` list: Q-2, Q-39, Q-46, Q-51, Q-52, Q-56, Q-58 and Q-59 (`questions.yaml:1319-1327`).
  - The ADR-006 Context names the same list, plus the Graphify part of Q-1 and the uv part of Q-35 (`adr-006…md:7`).
  - The validator only checks that superseded ids exist and are not self-references (`validate_ledger.py:96-100`), so keeping their status as `answered` is allowed.
- **F-2 (no criterion for the main behaviour): resolved.** BC-48 is at `component.md:300`. Its fake process runner can be injected, because `ProcessRunner` is a real port (`src/orqlet/application/ports/process.py:32`). The install use case reaches neither a process runner nor `Vcs` (diagram at `component.md:139-152`), so the test checks real behaviour. `self_check` now says "BC-1 to BC-48" (`manifest.yaml:191`).
- **F-3 (`proposal.md`): resolved** by the "stop editing it" option. I could not check with git that the file matches the approved text (see the info notes).
- **F-4 (missing rejected alternative): resolved** at `adr-006…md:41`.
- **O-1 (validation runs not recorded): resolved** at `manifest.yaml:200`.

The rest is consistent:
- `context.md:42`, `data-flow.md:24`, `container.md:75` and `adr-001…md:15,32` agree on four points: no network, no process, no tool preparation, and TB-2 withdrawn.
- The security globs, EC-6 and K-2 still match.
- The design does not weaken ARCH-001, ARCH-003, SEC-001, SEC-002, NOMODEL-001 or TEST-001.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 13, role: architecture-reviewer}
verdict: approve
findings:
  - id: F-1
    severity: low
    blocking: false
    rule: baseline "Do not guess"; round 12 F-1 ("if the person does not consider these covered, ask")
    statement: >-
      Q-60's `supersedes` list goes further than the person's recorded answer.
      The answer names only Q-56, Q-58 and Q-59 as superseded (questions.yaml:1315).
      The list adds Q-2, Q-39, Q-46, Q-51 and Q-52, and ADR-006:7 also names parts of Q-1 and Q-35.
      Each addition is a plausible reading of "graphify skill and tool preparation".
      Nothing records that the person confirmed it.
    evidence: ["questions.yaml:1312-1327", "adr-006-bundled-skills-and-tool-preparation.md:7", "architecture-reviewer-design-r12.md:157"]
    required_change: >-
      Have the person confirm the list when they approve, or record it in the answer value.
  - id: F-2
    severity: low
    blocking: false
    rule: self-check accuracy
    statement: >-
      The design is not consistent about which superseded questions it lists.
      self_check.questions keeps Q-39 "because it was asked in that session", but leaves out
      Q-58 and Q-59, which are also design-phase questions superseded by Q-60.
      confirmed_requirements says "Q-32 to Q-44 and Q-60 were asked and answered in this design session",
      and the component.md header says "Q-1 to Q-44, and Q-60". Both omit Q-58 and Q-59 as well.
    evidence: ["manifest.yaml:182, :206", "questions.yaml:1233-1237, :1259-1263", "component.md:3"]
    required_change: >-
      Apply one rule: list all superseded design-phase questions (Q-39, Q-58, Q-59), or none of them.
  - id: F-3
    severity: low
    blocking: false
    rule: ledger evidence must support the claim
    statement: >-
      Q-60's text cites "the round 11 security findings" and the json.py / sys.path finding.
      Its evidence_refs point only to the round 10 notes.
      The json.py / sys.path text appears only in architecture-reviewer-design-r11.md;
      the round 10 notes do not contain it.
    evidence: ["questions.yaml:1293-1304", "rg json\\.py|sys\\.path reviews/: only architecture-reviewer-design-r11.md"]
    required_change: Add the round 11 notes to Q-60's evidence_refs.
  - id: I-1
    severity: info
    blocking: false
    rule: baseline "Verify with evidence"
    statement: >-
      The Q-60 validation check is recorded as `result: pass`, but its own text says that
      `orqlet validate design` reported ORQ-E366, which is an error code, even though it is expected.
      The record is honest, but the label is stronger than the result.
    evidence: ["manifest.yaml:200"]
    required_change: Optional. Label it "pass except the expected ORQ-E366", or record the exit status.
  - id: I-2
    severity: info
    blocking: false
    rule: design-set integrity
    statement: >-
      design/proposal.md is not bound by the manifest and still proposes bundling Graphify
      and preparing tools (lines 45, 63, 109, 126).
      Restoring it is acceptable under round 12 F-3, but the response does not say the person
      was asked whether the file stays. I could not compare the file with origin/main.
    evidence: ["design/proposal.md:45,63,109,126", "manifest.yaml:108-120 (not in artifacts)"]
    required_change: Optional. Confirm with the person at approval.
```

## Self-check

- **What I examined:**
  - In full: `manifest.yaml`, ADR-006, `component.md`, `design-format.md`, the standards output and both round 12 notes with the author's responses.
  - In the ledger: Q-60 in full, and the phase, status and subject of every question.
  - In the other design files: the lines my searches matched for graphify, TB-2, tools, network, process and Q-60. That covered `context.md`, `container.md`, `data-flow.md`, `sequence.md`, ADR-001 to ADR-005, ADR-007 and `proposal.md`.
  - In `src/`: the `ProcessRunner` port and the ledger validator's `supersedes` check.
  - All at `/tmp/wt-guard` as it stood during this review.
- **Not done:**
  - The sandbox refused every shell command, so I ran no `git diff origin/main`, no hashing and no `orqlet validate`. I did not check the manifest sha256 values or the restoration of `proposal.md`.
  - I did not read `as-is.md` or `plan.yaml`. The plan is revised after this round.
- **Expected warning:** ORQ-E366 for the round 13 notes is not counted as a finding.

This is an additional check, not a guarantee. The person approves the revised design again.

## Author's responses

- F-1: the `supersedes` list is shown to the person in the pull request description for confirmation at approval.
- F-2: no change in this revision; Q-58 and Q-59 are superseded by Q-60, and Q-39 stays listed because it was asked in that session. Recorded here for the person.
- F-3: no change to the design artifacts; the round 11 notes are named in this note and in the pull request description as the evidence for the `python -c` finding.
- I-1: no change; the self-check text states the expected ORQ-E366.
- I-2: `proposal.md` is the approved pre-design proposal and is not a manifest artifact; the plan does not cite it as a source.
