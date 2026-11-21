# Security review of the design, round 13

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-21T19:20:50Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the scope and the round 12 notes. This round reviewed the content that will merge for the Q-60 revision.

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

**Verdict: approve.** There is no blocking finding. My round 12 finding S-1 is resolved, and the security position is still complete after the Q-60 revision. Three info notes remain, and none of them blocks.

## Round 12 findings

- **S-1 (ledger), resolved.**
  - Q-60 now sets `supersedes` to Q-2, Q-39, Q-46, Q-51, Q-52, Q-56, Q-58 and Q-59 (`questions.yaml:1319-1327`).
  - The author kept those questions' status as `answered`. That is correct: the ledger contract rejects an answer on any status other than `answered` (`question_ledger.py:54-59`). Changing the status would have meant deleting the answers.
  - ADR-006 Context (line 7) names the questions that are only partly superseded: the Graphify part of Q-1 and the uv part of Q-35.
  - Only part of Q-35 is superseded. Its "No bootstrap script" part still holds, and ADR-001 decision 4 relies on it. So leaving Q-35 out of `supersedes` is right.
- **S-2 (plan carry-over), still open.** It belongs to the plan review (see S-3 below).
- **S-3 (ponytail-debt), no change.** The author accepted it, as I expected.

## Security position at this revision

- **No process, no network.**
  - BC-48 (`component.md:300`) makes the Q-60 claim testable: with a fake process runner and sockets disabled, a consented `install` succeeds and starts no process.
  - This matches `data-flow.md:24`, `context.md:42`, ADR-001 decisions 1 and 4, and the security and operations notes in the manifest (lines 124 and 130).
  - Install's Git work-tree check runs no process (ADR-002:50). The executable locator starts no process (`component.md:168`). Git remains the only process starter, and only `status` uses it (`container.md:75`, ADR-001:29).
  - `src/` imports no network module. I searched for urllib, requests, httpx, socket, http.client and aiohttp. The suite-wide rule that tests run with sockets disabled (standards output line 22) backs the broader claim that "no Orqlet command uses the network".
- **Trust boundaries.**
  - TB-1 (user client folders) and TB-3 (hook payloads) are unchanged (`context.md:38-40`).
  - TB-2 (package index) is withdrawn with its reason stated.
  - The security globs and EC-6 list only the four remaining modules. `tools.py` is gone from them.
- **ADR-006.** The new rejected alternative, keeping tool preparation without Graphify, removes any reason to bring network tool preparation back. The Graphify rejection records the code-execution path from a cloned repository.
- **Accepted risks.** Q-40 to Q-44 are still listed. Q-39, the supply-chain risk, is no longer cited as an accepted risk. It stays in `self_check.questions` only as a record that it was asked in that session.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 13, role: security-reviewer}
verdict: approve
findings:
  - id: S-1
    severity: info
    blocking: false
    rule: ledger consistency; ORQLET-SEC-002 (intent)
    statement: >-
      The partial supersession of Q-1 (Graphify) and Q-35 (uv preparation) is recorded only in
      ADR-006 Context prose. Read alone, the ledger still shows Q-35 "on the pipx route orqlet
      install prepares a missing uv" as answered, with nothing machine-readable pointing at Q-60.
      The design wins wherever the two disagree, and the contract has no field for a partial
      supersession, so this is acceptable.
    evidence:
      - "questions.yaml:697-703 (Q-35 answer); :1319-1327 (Q-60 supersedes, without Q-1 or Q-35)"
      - "adr-006-bundled-skills-and-tool-preparation.md:7"
    required_change: None. The plan should cite ADR-006 Context whenever it cites Q-1 or Q-35.
  - id: S-2
    severity: info
    blocking: false
    rule: scope carry-over
    statement: >-
      design/proposal.md has been restored to its approved pre-design text. It is not a manifest
      artifact, and it still describes network tool preparation: the pinned Graphify tool, uv
      preparation under Q-2, ProcessRunner tool installation from package sources, and
      "Network installation". A plan or implementation phase that reads it as design could bring
      back what Q-60 removed.
    evidence:
      - "proposal.md:45-46, 55, 63, 109, 116, 119, 128, 153, 161"
      - "manifest.yaml:108-120 (proposal.md is not in the artifacts)"
    required_change: >-
      None for the design. The plan must not cite proposal.md as a source for scope or controls.
  - id: S-3
    severity: info
    blocking: false
    rule: scope carry-over
    statement: >-
      plan.yaml still has 105 lines that match graphify, P-9 or tools.py. Round 12's S-2 still
      holds for the plan revision.
    evidence: "plan.yaml (search count)"
    required_change: Check in the plan review that P-9, the Graphify parts of P-2 and the tools.py glob are gone.
```

## Self-check

- **What I examined:**
  - My round 12 notes and the architecture reviewer's round 12 notes, with the author's responses.
  - Q-1, Q-2, Q-35, Q-39 and Q-56 to Q-60 in the ledger.
  - `question_ledger.py`, all of ADR-006, and all of `manifest.yaml`.
  - The TB table in `context.md`, and BC-44 to BC-48 and sections 7 to 9 of `component.md`.
  - Searches across the design folder for graphify, uv, pipx, network, socket, process, `tools.py`, TB-2, Q-39 and Q-60.
  - A search of `src/` for network imports, and the standards output.
- **How:** read-only file tools only. Every shell command was refused, so I ran no `git diff origin/main`, no `orqlet validate` and no `orqlet evidence hash`. I did not check the manifest's artifact hashes, and I did not check the validation runs recorded in `self_check`. Those runs are the author's claim.
- **What I could not confirm:** I could not confirm that `proposal.md` is byte-identical to the copy at `17e162c`. It has the same number of Graphify matches (8) as the copy in the main workspace, but that copy is not proven to be `17e162c`.
- **What I did not examine:** ADR-002 to ADR-005 and ADR-007 beyond the lines my searches matched, the evidence files, `as-is.md`, and the plan in detail.
- **Revision:** the files in `/tmp/wt-guard` at review time, on branch `timur/one-command-setup-graphify-guard-design`.
- **Expected warning:** ORQ-E366, because the manifest lists the round 13 notes and that file does not exist yet.
- This is an additional check, not a guarantee.

## Author's responses

- S-1: no change; the plan cites ADR-006 Context wherever it cites Q-1 or Q-35.
- S-2: no change; the plan does not cite proposal.md.
- S-3: the plan revision that follows removes P-9, the Graphify parts of every phase and the tools.py glob.
