# Security review of the design, round 3

- Role: orqlet-security-reviewer, started as a typed Cursor subagent in a clean context (agent 3d393287-3fc2-4182-aa77-250918bb070f).
- Inputs given: the design folder, `as-is.md`, `questions.yaml`, `.agents/skills/orqlet-design/references/design-format.md` and the saved output of `orqlet standards for`; nothing else.
- Model requested: none named, so the subagent inherits the parent session's model. Model observed: unknown; the client reports no identity to the agent.
- Context freshness: fresh; the subagent received only the prompt above.
- Hashes when the reviewer started and when this note was saved (unchanged between the two):
  - manifest.yaml bd34366cf18fb5eac8fe34ffa31562ec8f43c229e138e2ed7d94497e82dd6949
  - component.md 7ec469aed0e1fd6d85564f2c795e91b3e49000ae25dbc0550b5ebadbd5dfd86f
  - views.md 5161f99395cb073656333a801a49205a1f6e83c1c9b848c7fcafffaeba8de10d
  - adr-001 1c3ca0bf3a18fc8492c5479dd49a7ac7ec18699fbf70588ae7509ebe9be6779e
  - adr-002 335452377493b2a2cb48dcb9fc2993f435124bbc12aacb76cc78abf78be30c6a
  - adr-003 60186c34eddbba9c600817c59669dd402ef282d79dc5fefb3d99bd92049e9b13
  - adr-004 f63c2303c48f6dd90346215ccc88273b997f9e13a9bfa3d4a96ae69bdff3c50c
- This is the third and last review round. The responses below are proposals: a blocking finding is still open, so the person decides how the design proceeds.

## Reviewer output (unchanged)

The design has one blocking security finding and three non-blocking ones. All eight round-2 findings (SEC-R2-1 to SEC-R2-8) are closed in the current text. The task name is now checked against the `Slug` contract, which uses the same pattern as `_TASK_PATH`.

## Findings (orqlet.finding/v1)

### Blocking

**SEC-R3-1: The new scan in `validate as-is` drops the advice to treat a found credential as exposed**
- **Claim.**
  - ADR-003 decision 3 gives the new scan its own message. That message only "asks for the file to be fixed and cited again", without the "amend or reset" step used when a file is cited.
  - Today's message at cite time also says "treat a credential that it shows as exposed". The design neither keeps nor mentions that clause.
  - This scan runs later than the cite-time scan, typically when the next phase checks its inputs. By then the evidence file has usually been pushed and often squash-merged into main (that is the whole point of ADR-003). Fixing the file and citing it again does not remove the credential from history.
  - As written, the message would tell people to fix the file, while the credential stays in history and is never rotated.
- **Evidence.**
  - ADR-003 decision 3.
  - EC-5 says "with its own message that has no 'amend or reset' step".
  - `src/orqlet/application/usecases/evidence_cite.py:107-109`, today's wording.
  - ADR-003, Consequences, first bullet: the evidence merges in one squash commit.
- **What would close it.**
  - ADR-003 decision 3 and EC-5 say the message treats any credential found as exposed, to be revoked or rotated.
  - The message does not suggest rewriting history on a shared branch.
  - It still names only the rule and the line, never the text.
- **Confidence.** Medium-high.
- **Blocking.** Yes.

### Non-blocking

**SEC-R3-2: After design, nothing checks the task's cited evidence files**
- **Claim.**
  - ADR-003 decision 4 binds the cited evidence files to the commit that recorded the AS-IS acceptance. Only design's input check uses that reference.
  - For plan and implement, the approved files of the design merge stay `as-is.md` and `design/`. The cited evidence files are not among them.
  - Neither the design's nor the plan's scope covers the task's `evidence/` folder, so gate status never warns about stale input for these files. The planned-work row ("never change a cited one") is therefore never reached for them.
  - ADR-001 decision 4 also lets later phases reuse the validators' result. Since `validate as-is` now reads these files at HEAD, a later edit is caught only if someone reruns it, and only on cited lines (ORQ-E335).
  - Before this change, evidence was read at the base revision, which cannot change. The integrity of these files after design now rests on agent-run text rules alone.
- **Evidence.**
  - ADR-003 decisions 2 and 4; EC-6; ADR-001 decision 4.
  - `phase-contract.md:45` (approved files per merge), `:56` and `:60`.
  - `gate_status.py:180-219`: staleness is computed over the scope only.
  - The design manifest's `scope.paths`.
  - U-28 (whether implement runs `validate as-is` is unknown).
- **Suggestion.** Either name the reference that plan and implement compare these files with (the design merge), or say in the security considerations that after design only the cited lines stay bound.
- **Confidence.** Medium.
- **Blocking.** No.

**SEC-R3-3: The new scan may break "every AS-IS file valid today stays valid"**
- **Claim.**
  - EC-5, BC-22 and ADR-003's Consequences say the rule "only accepts more". Decision 3, however, adds the size, credential and hidden-character scan to every cited task-owned file. That includes entries that cite the base revision, which pass today without any scan.
  - The scan flags any `<!--`, lines over 4,096 characters, credential-assignment shapes and files over 256 KiB.
  - Four other tasks cite their own evidence: one-command-setup (25 entries), team-conventions-resources (59), mcp-or-plugins (90) and phase-skill-contracts (3).
  - The design also does not say which bytes are scanned for an entry that cites the base revision. Today's cite-time scan covers exactly the bytes it hashes.
- **Evidence.**
  - EC-5; ADR-003 decision 3.
  - `resources.py:394-395, 417-418, 126-135`.
  - A search for evidence paths under `docs/design` found those counts.
  - My searches of today's working-tree evidence files found no `<!--`, no credential-assignment shape and no common zero-width or bidirectional characters. I did not check sizes, nor the content at those tasks' cited revisions.
- **Suggestion.**
  - Say that the scan covers the same bytes the hash check reads.
  - Add an acceptance check that runs `validate as-is` on every existing AS-IS file after the change.
  - If the check fails, drop the "only accepts more" claim. Do not narrow the scan.
- **Confidence.** Medium.
- **Blocking.** No.

**Observations (not findings)**
- **Missing round-3 notes.** The manifest's `reviews` list names round-3 notes that do not exist yet. They are expected once this round is saved.
- **Task-name check in the CLI only.** The `Slug` check sits in the CLI layer, and the use case still builds `docs/design/{task}` from any string. Path traversal is not possible either way, because `read_file` rejects `..` (`validation.py:157-165`, `paths.py:33`).
- **Reusing check results.** The HEAD and `git status --porcelain` comparison is weak, and ADR-001 states that openly. A stronger fingerprint, such as one taken over the `git diff HEAD` output, would catch a second edit to a file that is already modified. That limit was accepted in round 2.

## Self-check

- **Round 2 closed.**
  - SEC-R2-1: ADR-003 decision 4 limits approval to the cited files, and the planned-work row is named in EC-6.
  - SEC-R2-2: components are matched exactly and case-sensitively, and `Evidence/` is a negative case in BC-22.
  - SEC-R2-3: EC-2 says a failing pair carries no revision and no hash.
  - SEC-R2-4: HEAD and porcelain are compared before a reuse, and the limit is stated.
  - SEC-R2-5: the next prompt is restricted to the task, the next skill, artifact paths and pending approvals.
  - SEC-R2-6: gate status prints exactly one action line, and open manual comparisons get their own line.
  - SEC-R2-7: BC-17 keeps the paragraph that treats source text as evidence.
  - SEC-R2-8: ADR-001 single-quotes each cited file after `--`.
- **New exposure.** No new process, network path, dependency, credential or trust boundary. `.github/**` is out of scope and on a security glob. Reading at HEAD goes through the existing Git port.
- **Approval.** A PASS from gate status is not consumed by CI: nothing under `.github` runs orqlet. The input check still requires the merge commits the person names.
- **Evidence for claims.** Every finding cites the design text and code lines. Claims without line evidence are listed as observations. I did not use the web.
- **Revision.** I read the working tree of `workflow-efficiency-design` as named in the brief. Shell commands are refused in this mode, so I could not record HEAD or check the manifest's artifact hashes.
- **Limits.** This review is an additional check, not a guarantee.

## Files

**Read (inputs):**
- The design folder: `manifest.yaml`, `component.md`, `views.md` and the four ADRs.
- `as-is.md` and `questions.yaml`.
- `.agents/skills/orqlet-design/references/design-format.md`.
- `/tmp/orqlet-workflow-efficiency-standards.txt`.

**Opened only to verify citations:**
- `validate_as_is.py`, `evidence_cite.py`, `gate_status.py` and `interface/cli/commands/gate.py`.
- In `validation.py`: `task_of`, `_TASK_PATH` and `read_file`.
- In `domain/paths.py` and `domain/resources.py`: the scan functions and patterns.
- In `contracts/common.py`: `Slug`.
- `orqlet-implement/references/phase-contract.md`.
- `reviews/security-reviewer-design-r2.md`.
- Searches over the skills, `.github`, `src/orqlet` and the evidence folders under `docs/design`.

**Not examined:**
- The architecture review notes for rounds 1 and 2, and my own round-1 note.
- The contents of the evidence files (I only searched them for patterns).
- The baseline, the role and command sources, and the skill bodies beyond the search matches.
- `validate.py`, `evidence.py`, `models.py`, `lifecycle.py` and `staleness.py`.
- The Git adapter, the CI workflow, the `.orqlet/` files, the generated client copies and the tests.

Now I'm getting the final response written out.

## Author's responses

Proposed changes, which wait for the person's decision because the round cap has been reached:

- SEC-R3-1, accepted. The message of the scan in `validate as-is` says that any credential it finds is to be treated as exposed and revoked or rotated. It suggests no history rewrite on a shared branch, and it names only the rule and the line, never the text.
- SEC-R3-2, accepted, as in AR3-6. The cited evidence files are added to the approved files of the design merge, so plan and implement compare them with that merge.
- SEC-R3-3, accepted, as in AR3-3. The scan covers the bytes the hash check reads, and only for entries that use the new exemption. A new acceptance criterion requires `validate as-is` to pass on every existing AS-IS file after the change.
- Observation on the reuse fingerprint, noted. The limit accepted in round 2 stands. A fingerprint over the `git diff HEAD` output would be stronger, and the plan may adopt it without a design change.

## Decision at the round cap

On 2026-11-23 the person chose to apply every proposed change above and run a fourth round with fresh reviewers. They answered Q-21 with an AS-IS refresh before this design is approved, and named `docs/design/orqlet-architecture-proposal.md` maintained documentation, now in the design scope. The proposed changes are applied in the design files.
