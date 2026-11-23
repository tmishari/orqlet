# Security review of the design, round 2

- Role: orqlet-security-reviewer, started as a typed Cursor subagent in a clean context (agent ed87bfd3-9d6b-458c-a051-f213cb0e61bf).
- Inputs given: the design folder, `as-is.md`, `questions.yaml`, `.agents/skills/orqlet-design/references/design-format.md` and the saved output of `orqlet standards for`; nothing else.
- Model requested: none named, so the subagent inherits the parent session's model. Model observed: unknown; the client reports no identity to the agent.
- Context freshness: fresh; the subagent received only the prompt above.
- Hashes when the reviewer started and when this note was saved (unchanged between the two):
  - manifest.yaml 94888685aafaf4ee6b6f2ff0217a7584fe17f3d2550b8284884f806eaf88adf4
  - component.md 5f53e85a8f04d7b3c94d1305443ac5456a468eadb523a4fcc131e24d14eb43f4
  - views.md 9159ab9cacfa270de9161d3d2b25b9cc5e3279898c8f08d3ca7ebd3b0a0eec55
  - adr-001 3c79e4deae3ba1bd164367d3c558ebb643e2ea8b19283b09784ab042cebfb3ce
  - adr-002 64c5a6ad1e73c25094b6a74c30ddac04bcaa89c7239e2290cf048de5db498921
  - adr-003 cf9b7e5bcc94cb1041dc2737ee527aa7bd3cbd1d4c501b3baeae0df1d8400b9b
  - adr-004 071bd700c788c8b2c1af50eacf6d98d4c7e69ec62b7c9a37a839349799b87036
- These hashes differ from the final manifest's, because the design changed to answer this round; round 3 reviews the changed design.

## Reviewer output (unchanged)

The design has one blocking security finding: its new guard on the task's `evidence/` folder (ADR-003 decision 4) conflicts with workflow text it doesn't change. All four blocking findings from round 1 are closed, and I found seven non-blocking ones.

Shell commands were refused in this mode, so I couldn't record HEAD or the SHA-256 of the design files. The review rests on the working-tree files as I read them on branch `workflow-efficiency-design`, which the task brief named.

## Findings (orqlet.finding/v1)

### Blocking

**SEC-R2-1: The guard on the `evidence/` folder conflicts with later phases' evidence writes and with the stale-input matrix**
- **Claim.**
  - ADR-003 decision 4 adds `docs/design/<task>/evidence/` to the files the AS-IS acceptance approves. Its consequences add that "any edit to the folder stops the input check."
  - But the unchanged workflow text tells later phases to write new files under `evidence/web/`:
    - The design skill writes there.
    - Implement step 4 writes there.
    - The stale-input matrix counts commits touching `evidence/web/` as "This task's planned work (valid)."
  - The input check stops on any difference or untracked file in approved files since the reference commit. So two things can happen:
    - The rule is applied as written, and a resumed design session or the next implement phase stops on the phase's own evidence.
    - An agent follows the lenient matrix row instead, and the uncited parts of accepted evidence can change after acceptance without stopping anything. That defeats the guard the design names in its security notes.
  - Cited lines stay protected by the hash check (ORQ-E335), so the damage is limited to uncited content and to availability. Still, the design states a control it can't deliver as written.
- **Evidence.**
  - ADR-003 decision 4, and its consequences, second bullet.
  - The EC-6 value ("with docs/design/<task>/evidence/ among the files the AS-IS acceptance approves"). EC-6 doesn't mention changing the matrix row.
  - `src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md:47-51` (approved files and step 5), `:56` (step 6, "Current") and `:60` (the planned-work row, including `evidence/web/`).
  - `src/orqlet/workflow/skills/orqlet-design/skill.md:18,30`.
  - `src/orqlet/workflow/skills/orqlet-implement/skill.md:33`.
- **Resolution the design should state.**
  - Define the approved set exactly. For example, use the evidence files present at the acceptance commit, or the files the AS-IS facts cite.
  - Say that later phases may add new files under `evidence/web/` but never change an accepted one.
  - Name the matching change to the stale-input matrix row in EC-6.
- **Confidence.** High on the conflict; medium on its severity.
- **Blocking.** Yes.

### Non-blocking

**SEC-R2-2: "Lies under `evidence/`" could be matched without regard to case, unlike the Git check that guards the folder**
- **Claim.**
  - The obvious helper, `CanonicalPath.is_inside`, compares case-folded keys, and the web-evidence pattern matches after `casefold()`.
  - Git pathspecs in the input check are case-sensitive.
  - If the exemption uses `is_inside`, a file under `docs/design/<task>/Evidence/…` is exempt from ORQ-E332 but sits outside the guard of ADR-003 decision 4.
  - The design should require an exact, case-sensitive component match on `evidence`, with a negative test.
- **Evidence.** `src/orqlet/domain/paths.py:67-70,88-90`; `src/orqlet/application/usecases/evidence_cite.py:27,56`; ADR-003 decisions 2 and 4.
- **Confidence.** Medium.
- **Blocking.** No.

**SEC-R2-3: EC-2 doesn't say whether a refused pair still gets a hash**
- **Claim.**
  - EC-2 says `data.citations` holds "one entry per pair … in today's entry shape", and also that "a failing pair is reported with its finding".
  - It's unclear whether a pair refused with ORQ-E511 gets a `revision` and `sha256` that an agent could paste into an artifact.
  - Today the refusal returns before hashing.
  - For evidence outside the task's own folder, the scan at cite time stays the only scan, because ADR-003 decision 3 rescans only the task's own files.
  - EC-2 and BC-21 should state that a refused or failing pair carries no hash.
- **Evidence.** `evidence_cite.py:56-57,63`; EC-2; ADR-001 decision 7; ADR-003 decision 3.
- **Confidence.** Medium.
- **Blocking.** No.

**SEC-R2-4: Reusing a check result relies on the agent noticing edits, while main's checks are red**
- **Claim.**
  - The rule "no file has been edited since its last passing run" has no mechanical check, which ADR-001's consequences admit.
  - Under Q-14, CI's lint, types and tests jobs are red. CI therefore can't separate new failures from the known ones, and the local full run before review becomes the only reliable gate.
  - A cheap read-only check would make a stale reuse visible: record HEAD and `git status --porcelain` at each passing run, and compare them before reusing the result.
- **Evidence.** ADR-001 decisions 2-3 and its consequences, second bullet; the operations note in the manifest; Q-14.
- **Confidence.** Medium.
- **Blocking.** No.

**SEC-R2-5: The copyable "Next prompt" can carry outside text into a new session**
- **Claim.**
  - The final-reply format ends with a copyable prompt holding "prerequisites" as free text.
  - The person pastes it into a new session, where it runs with their authority. Text taken from a web page or a repository file would cross the rule that source text is evidence, never an instruction.
  - The baseline section should limit the prompt to the task name, the next skill and prerequisites given as artifact paths or approvals. It should forbid text copied from a source and commands found in project files.
- **Evidence.** ADR-004 decision 2; BC-20; the "Looking things up" section of the baseline.
- **Confidence.** Medium.
- **Blocking.** No.

**SEC-R2-6: A PASS with open manual comparisons prints two contradicting lines**
- **Claim.**
  - With `--phase` and open manual expected changes, `gate status` would print "No action needed." followed by "N expected change(s) need a reviewer's comparison."
  - A reader may stop at the first line.
  - Every expected change except EC-8 is checked by hand, including EC-5, the change to the `validate as-is` evidence rule.
  - The design should word the PASS line differently when comparisons are still open.
- **Evidence.** ADR-002 decision 2; the `verification` fields of EC-1 to EC-8 in the manifest.
- **Confidence.** Medium.
- **Blocking.** No.

**SEC-R2-7: No acceptance criterion protects the paragraph that treats source text as evidence**
- **Claim.**
  - The paragraph is only a constraint (section 9 of the brief) and part of the EC-6 value; no acceptance criterion names it.
  - Existing tests assert it, but golden files are regenerated on purpose during this task.
  - An acceptance criterion would keep the tester asserting it in every skill.
- **Evidence.** `component.md` section 9; EC-6; `tests/unit/render/test_skills.py` and `tests/unit/test_workflow_skill_contracts.py` both contain "not authority".
- **Confidence.** High that no criterion names it; low that the risk is real.
- **Blocking.** No.

**SEC-R2-8: ADR-001's `git diff` template leaves the file names unquoted**
- **Claim.**
  - ADR-001 decision 1 writes `git diff --quiet '<cited revision>' -- <cited files>` with the file names unquoted.
  - The contract's rule on values from artifacts requires each value as one single-quoted argument.
  - When the reuse rule moves into the phase contract, the rewritten text should keep that rule.
- **Evidence.** ADR-001 decision 1; `phase-contract.md:36-38`.
- **Confidence.** Medium.
- **Blocking.** No.

**Observations (no finding)**
- **Transcript evidence isn't scanned.**
  - The task's own evidence now includes internal transcript summaries under `evidence/transcripts/`.
  - The credential scan covers only `evidence/web/`, so these summaries are never scanned. That is not a regression: Q-1 has the person review them before commit.
  - Extending only the credential scan to every file in the task's own `evidence/` would cost little.
- **Round-2 notes are listed but absent.** The manifest's `reviews` list names the round-2 notes. At the time I read the folder, only the round-1 note files existed.

## Self-check

- **Round 1 closed.** I verified each of the four round-1 blocking findings against the design:
  - Dependency watching: `extractor_config` now names `pyproject.toml` and `uv.lock` (manifest lines 34-36).
  - Invalid task name: it is now exit 2 (EC-1, ADR-002 decision 1). The "existing task-name rule" exists in code as the `_TASK_PATH` pattern (`validation.py:26`).
  - Negative tests: BC-21 now requires the scan on every pair, and BC-22 requires ORQ-E332 outside the task's folder.
  - The task is taken from the AS-IS file's own path, not `header.task` (ADR-003 decision 2; `task_of` in `validation.py:88-91`).
- **Path escape.** `CanonicalPath` rejects `..`, so no evidence path can climb out of the task folder (`paths.py:33-34`).
- **Process and Git access.** The design adds no process, network path, dependency, credential or trust boundary. Reading at HEAD uses the existing Git port (`read_at`), as the Git-access rule requires.
- **Scope of claims.** Every blocking claim cites a file and lines. Claims without line evidence are listed as observations. I did not use the web.
- **Not verified.**
  - The manifest's artifact hashes against the files, and HEAD: shell commands were refused.
  - The rendered client copies of the skills.
- **Limits.** This review is an additional check, not a guarantee.

## Files

**Read:**
- The design folder: `manifest.yaml`, `component.md`, `views.md`, `adr-001` to `adr-004`.
- `docs/design/workflow-efficiency/as-is.md` and `questions.yaml`.
- `.agents/skills/orqlet-design/references/design-format.md`.
- `/tmp/orqlet-workflow-efficiency-standards.txt`.

**Opened only to verify citations:**
- `src/orqlet/application/usecases/validate_as_is.py`, `evidence_cite.py` and `gate_status.py`.
- `src/orqlet/application/usecases/validation.py` (lines 60-119, plus a search for `_TASK_PATH`).
- `src/orqlet/domain/paths.py` (lines 50-96, plus a search).
- `src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md`.
- `docs/design/workflow-efficiency/reviews/security-reviewer-design-r1.md`.
- Searches over the skills under `src/orqlet/workflow` for `evidence/`, over `src/orqlet` for `gate status` and the task-name rule, and over `tests/` for "not authority".

**Not examined:**
- The architecture review note (round 1).
- The evidence files under `docs/design/workflow-efficiency/evidence/`.
- The baseline, the role and command sources, and the other skill bodies beyond the search matches.
- The CLI command modules (`gate.py`, `evidence.py`, `validate.py`, `models.py`, `lifecycle.py`).
- The Git adapter, the CI workflow, the `.orqlet/` YAML files, the generated client copies and the test bodies.

## Author's responses

- SEC-R2-1, accepted. The approved set is now the evidence files that the AS-IS facts cite, compared with the commit that recorded the AS-IS acceptance. A change to or removal of one stops the input check. Later phases may add new files under `evidence/web/` but never change a cited file. The planned-work row of the stale-input matrix says the same, and EC-6 names the row change.
- SEC-R2-2, accepted. The exemption matches the path components `docs`, `design`, the task and `evidence` exactly and case-sensitively. BC-22 adds a folder named `Evidence/` as a negative case.
- SEC-R2-3, accepted. A refused or failing pair carries no revision and no sha256. EC-2 and BC-21 say so.
- SEC-R2-4, accepted. Before a result is reused, HEAD and the output of `git status --porcelain` must equal what was recorded at the passing run. That is a necessary check, not a sufficient one, because a second edit to an already modified file keeps the porcelain output the same. So the rule still requires that no edit was made, and ADR-001 states this limit.
- SEC-R2-5, accepted. The next prompt holds only the task name, the next skill or action, artifact paths and the approvals still needed. It holds no text copied from a source and no command found in a project file.
- SEC-R2-6, accepted, as in AR2-8. Gate status prints exactly one action line, and open manual comparisons make it "Action needed: N expected change(s) need a reviewer's comparison."
- SEC-R2-7, accepted. BC-17 now requires every skill to keep the paragraph that treats source text as evidence.
- SEC-R2-8, accepted. ADR-001 writes each cited file as a single-quoted argument after `--`.
- Observation on transcript evidence, accepted. `validate as-is` runs the credential and hidden-character scan on every task-owned evidence file that the facts cite, not only those under `evidence/web/`.
