# Architecture review of the design, round 2

- Role: orqlet-arch-reviewer, started as a typed Cursor subagent in a clean context (agent 3e24c2c9-2796-496c-8603-ebd16a5bc9b1).
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

# Architecture review of the workflow-efficiency design, round 2

This round has **two blocking findings and six non-blocking ones**.

- **Later implement phases are still stale.** From the second implement phase on, `gate status` still reports the design and plan as stale, with `NOT_RUN` and exit 5. The design's "PASS when current" and the reuse of validator results in later phases therefore don't happen as written.
- **The approved evidence folder conflicts with existing skills.** Counting all of `docs/design/<task>/evidence/` as approved with the AS-IS file clashes with the design and implement skills. Both are allowed to add web evidence to that folder after the AS-IS acceptance.

All 12 round-1 findings are answered in the changed design. The structure meets the format: class D3, a context view, four ADRs with all four sections, the nine brief parts in order, a source on every acceptance criterion, and no phase order.

## Blocking findings

```yaml
- schema: orqlet.finding/v1
  id: AR2-1
  claim: >
    From the second implement phase on, gate status still reports the design, the plan and
    the AS-IS file as stale. It adds ORQ-W390 and a not-run reason, so the verdict is NOT_RUN
    and the exit status is 5. The cause is the task's own commits from earlier phases: they
    change files inside each artifact's scope.
    The design does not account for this:
      - ADR-001 decision 4 and BC-2 reuse the validators' result when "the currency check and
        gate status show no change". After a committed phase, gate status shows a change by
        construction.
      - ADR-002 consequence 1 ("an agent no longer meets a 'not run' that it must ignore")
        holds only for design, plan and the first implement phase.
      - In each later phase the agent still walks the stale-input matrix, and the person
        confirms the "planned work" row every time. That is a repeated check and a repeated
        message, which R-1 targets.
    The AS-IS file has no fact on this (A-13 does not mention it).
  evidence:
    - src/orqlet/application/usecases/gate_status.py:179-184 (stale gives ORQ-W390 plus skip), 205-229 (_base_moved), 188-191 (a plan's scope is its operation paths)
    - src/orqlet/application/usecases/staleness.py:11-30 (any file under the scope that differs between base and HEAD)
    - manifest.yaml:18-32 (the design scope includes src/orqlet/interface/cli/**, usecases/**, tests/**)
    - src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md:58 (stop on ORQ-W390, the person confirms), :60 (the planned-work row)
    - adr-001 decision 4; component.md BC-2; adr-002 consequence 1; manifest EC-1
  confidence: medium-high (code path read; not run on a real multi-phase branch)
  blocking: yes
  resolves_by: >
    State the later-phase behaviour in the design. Then either define BC-2's "no change" as
    "no stale cause outside the planned-work row", keeping the person's confirmation, or
    decide whether gate status should recognise this task's planned work, which is a
    behaviour change for the person to choose. Record the missing fact through an AS-IS
    refresh or a ledger question, as the design skill requires.

- schema: orqlet.finding/v1
  id: AR2-2
  claim: >
    ADR-003 decision 4 (and EC-6) adds all of docs/design/<task>/evidence/ to the files the
    AS-IS acceptance approves. In the input check, any difference or untracked file in an
    approved file since its merge stops the skill. But the workflow allows two later writers
    in that folder:
      - design step 4 writes and commits evidence/web/ files after the design input check;
      - implement step 4 writes evidence/web/ files during a phase;
      - the stale-input matrix lists evidence/web/ as valid planned work.
    So the next input check (a resumed design, or implement P-2 after P-1 added a page) stops
    on the skill's own permitted output. The design also does not say which merge the folder
    is compared with in plan and implement: the AS-IS acceptance commit or the design merge.
  evidence:
    - adr-003 decision 4 and consequence 2 ("any edit to the folder stops the input check"); manifest EC-6
    - src/orqlet/workflow/skills/orqlet-design/skill.md:18, 30
    - src/orqlet/workflow/skills/orqlet-implement/skill.md:33 ("the one exception to the file list")
    - src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md:48-51 (approved files and the git diff --quiet / ls-files --others rule), :60
  confidence: medium-high
  blocking: yes
  resolves_by: >
    Narrow the approved set to the evidence files the AS-IS facts cite (changes and removals
    stop the skill; additions do not). Or name the reference commit per phase and let later
    phases add only new evidence/web/ files. The ORQ-E335 hash check already guards the cited
    lines. Ask the security reviewer to confirm that the narrowed rule keeps the property they
    asked for.
```

## Non-blocking findings

```yaml
- schema: orqlet.finding/v1
  id: AR2-3
  claim: >
    The new action line would also appear on evidence cite and evidence hash, which EC-3 does
    not mention. Those commands render through the same output_of and render_validation path
    as the validators. EC-3 names only validate * and gate status. The plain text for several
    cite pairs is also unspecified: the subject is one file name today.
  evidence: [src/orqlet/interface/cli/commands/evidence.py:32-36, 46-49; commands/validate.py:40-49; render_human.py:175-185; manifest EC-3]
  confidence: high (code fact); medium (intent)
  blocking: no

- schema: orqlet.finding/v1
  id: AR2-4
  claim: >
    The design does not say which layer owns the task-name check that gives exit 2. The
    component diagram puts the check in the gate_status use case. A use-case result can only
    reach exit 0 or 5 through output_of. The existing pattern for exit 2 is a BadParameter
    error raised in the interface against the Slug contract (models resolve does this for
    --task). This fits "validate input where it enters".
  evidence: [component.md section 4 (GS box); validate.py:40-49; models.py:119-131, 141-154; application/contracts/common.py:22; exit_codes.py:9]
  confidence: medium
  blocking: no

- schema: orqlet.finding/v1
  id: AR2-5
  claim: >
    "Cited once per phase, by whichever role runs a check first" (ADR-001 decision 1) needs a
    handoff the design does not name. The tester runs first, in its own context. The tester's
    record has no field for cited sources or their revision. So the coder has no recorded
    revision to run `git diff --quiet '<cited revision>'` against. The sequence view shows the
    tester citing and the coder confirming, but not how the revision passes between them.
  evidence: [adr-001 decision 1; views.md sequence; src/orqlet/application/contracts/test_record.py:17-38]
  confidence: medium
  blocking: no

- schema: orqlet.finding/v1
  id: AR2-6
  claim: >
    EC-5 says task-owned evidence that cites a revision other than base_revision is read at
    HEAD. It does not say what happens to task-owned evidence that does cite base_revision.
    Today such entries are read at base_revision. If they are read at HEAD instead, and the
    file changed after base, they would fail. That contradicts "every AS-IS file valid today
    stays valid".
  evidence: [manifest EC-5; adr-003 decision 2; validate_as_is.py:112-134]
  confidence: medium
  blocking: no

- schema: orqlet.finding/v1
  id: AR2-7
  claim: >
    Reusing the web-evidence scan in validate as-is (ADR-003 decision 3) reuses an ORQ-E511
    message written for cite time: "already in a local commit: amend or reset it before
    anything is pushed". At validate time, possibly after a merge, that next step is wrong. It
    works against R-2's "plain results with the next action". The docstring "runs at cite time
    only" also becomes untrue.
  evidence: [src/orqlet/application/usecases/evidence_cite.py:89-112; adr-003 decision 3]
  confidence: high (text); low (impact)
  blocking: no

- schema: orqlet.finding/v1
  id: AR2-8
  claim: >
    "Ends with one action line" conflicts with gate status adding the no-artifact line and the
    manual-expected-change line. With no artifacts the verdict is PASS, so the person reads
    "No action needed." next to "check the task name". At the start of research the task
    legitimately has no artifacts.
  evidence: [adr-002 decision 2; manifest EC-3; gate_status.py:153-156]
  confidence: medium
  blocking: no
```

## Checked and consistent (no finding)

- **Round 1:**
  - AR-1: section 9 now rebuilds `MANIFEST.json` in every phase that changes the workflow package.
  - AR-2: the model step stays in each skill. `MANIFEST.json` lists the phase contract under four skills only.
  - AR-3: the action line is generic and rendered in the interface.
  - AR-4: the diff is against the cited revision.
  - AR-5: the task comes from the canonical path, using the existing `task_of` regex at `validation.py:26, 88-91`.
  - AR-6 to AR-12: answered as stated in the round-1 note.
- **ADR-002 context:** the unconditional skip at `gate_status.py:117-122` is confirmed. The three "not a failure" sentences are at `orqlet-plan/skill.md:28`, `orqlet-implement/skill.md:28` and `phase-contract.md:54`. The three "does not exist yet" notes come from `gate_status.py:153-156`.
- **Verdict rule:** `Collector.result` gives PASS only with no error and no skip (`validation.py:73-80`). Removing the I393 skip therefore gives exactly EC-1's PASS condition, and W390 and missing-revision skips keep NOT_RUN.
- **New codes:** ORQ-W368 and ORQ-W388 are unused outside this task's folder.
- **Layering:** the Git port's `read_at` covers the read at HEAD in ADR-003, and the existing domain functions cover the web scan. No domain change is needed. The workflow package stays data used by the interface and the adapters.
- **Data contracts:** no JSON schema change is needed for `data.citations`, because the result data is an untyped dictionary.

## Self-check

- **Model and context:** I ran as a typed `orqlet-arch-reviewer` subagent in a clean context, with only the parent's prompt. Model requested: none named. Model observed: unknown.
- **Not run:**
  - Shell commands were refused in this mode. So I did not verify the manifest's sha256 values, the 1,200-word count of `component.md`, the branch or the uncommitted state.
  - I did not run `gate status` on a multi-phase branch (AR2-1).
- **Not checked:**
  - Whether the phase contract (1,799 words, cap 1,800) can take the reuse rule, the input check by phase and the web-evidence format within its cap. The design asserts this; only the plan can show it.
  - Most A-n citations beyond those listed below.
- **Limits:** this is an additional check, not a guarantee. No web lookups.

**Files read:**
- **The inputs:** the seven design-folder files, `as-is.md`, `questions.yaml`, the design format reference and the standards output.
- **To verify citations:**
  - the round-1 review note;
  - `gate_status.py`, `evidence_cite.py`, `validate_as_is.py`, `validation.py` and `staleness.py`;
  - `interface/cli/commands/validate.py`, `gate.py`, `evidence.py` and `exit_codes.py`;
  - `contracts/test_record.py`;
  - the implement phase contract and the design `skill.md`.
- **Searched only:**
  - `render_human.py` (`render_validation`) and `models.py` (`_require`);
  - the slug patterns in `src`, `Outcome` in `domain/expected_change.py`;
  - ORQ-I393 and ORQ-W390 in the workflow package, `evidence/web` in the skills, and the ORQ-W368/W388 and ORQ-W338 codes.

**Not examined:**
- the security reviewer's round-1 note;
- the other skill bodies, the baseline source, the as-is format, `MANIFEST.json` and the golden files;
- `pin_staleness.py` and `domain/resources.py`;
- the tests (including the caps cited by A-7 and A-8);
- the AS-IS evidence files;
- the round-2 note paths listed in the manifest, which do not exist yet.

## Author's responses

Both blocking claims were checked: `staleness.py:11-30` counts any changed path under the scope, and the planned-work row of the phase contract lists `evidence/web/` commits as valid.

- AR2-1, accepted. The design now states the later-phase case. A stale result caused only by this task's own planned work, which the person confirms under the stale-input matrix as today, does not stop reuse. BC-2 and ADR-001 decision 4 now say that the validators' result is reused when the only stale cause is that confirmed planned work. ADR-002 consequence 1 is qualified the same way. Gate status does not try to recognise planned work by itself, because the matrix calls trailers and authors claims, not proof. The behaviour rests on code this note cites and not on an AS-IS fact, so the final report asks the person whether they want an AS-IS refresh for it.
- AR2-2, accepted, as in the security reviewer's SEC-R2-1. The approved set becomes the evidence files that the AS-IS facts cite. A change to or removal of one stops the input check. Later phases may add new files under `evidence/web/` but never change a cited file. The planned-work row says the same, and EC-6 names that change.
- AR2-3, accepted. The action line is only for validators and `gate status`. `evidence cite` and `evidence hash` render without it. With several pairs, `evidence cite` prints one snippet line per pair, and its subject lists the files.
- AR2-4, accepted. The task-name check is in the CLI layer as a usage error, following the pattern `models resolve` uses for `--task`. The component view moves it there.
- AR2-5, accepted. The tester's report lists the citations it made (path, lines, revision and sha256), and the coder uses them for its `git diff` check. The record schema does not change.
- AR2-6, accepted. Task-owned evidence that cites `base_revision` is still read at `base_revision`. Only entries with another revision are read at HEAD.
- AR2-7, accepted. `validate as-is` reports a failed scan with its own message, with no "amend or reset" step. The docstring that says the scan runs only at cite time is corrected.
- AR2-8, accepted, as in SEC-R2-6. Gate status prints exactly one action line. With no artifact of the task, the line is "No artifact of task T exists yet; check the task name unless you are starting research." With open manual expected changes, the line is "Action needed: N expected change(s) need a reviewer's comparison."
