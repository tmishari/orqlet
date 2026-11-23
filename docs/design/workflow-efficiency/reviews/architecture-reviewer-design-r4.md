# Architecture review of the design, round 4

- Role: orqlet-arch-reviewer, started as a typed Cursor subagent in a clean context (agent 240a0220-e9de-4d44-9a86-55b85ac5f319).
- Inputs given: the design folder, `as-is.md`, `questions.yaml`, `.agents/skills/orqlet-design/references/design-format.md` and the saved output of `orqlet standards for` (`/tmp/orqlet-workflow-efficiency-standards.txt`); nothing else.
- Model requested: none named, so the subagent inherits the parent session's model. Model observed: unknown; the client reports no identity to the agent. The reviewer reports Claude Opus 5.5 from its own system prompt, which is a claim, not an observation.
- Context freshness: fresh; the subagent received only the prompt above.
- Design bound at `86e07abc18e95eef98d11923fd1aff72451ad7c2`, after the rebase of `workflow-efficiency-design` onto main and the merge of the Q-21 research refresh (pull request 56).
- Hashes when the reviewer started and when this note was saved (unchanged between the two, and equal to the manifest's):
  - manifest.yaml cc6cb9673ff946212f65cac85ea0f40002b60ddcce2e77cdb41d2caba0404127
  - component.md ceea38809b420a4a21ac20b1d2c6f16008a463cf486763c5ae423c77c293818f
  - views.md d2074851ae068b42a6e9621ad29337043bd65236e9ee3da8b8f145f85d6a76eb
  - adr-001 61115867e69d0b6ba4cd4e54f64415f468912f904cf6cdbc07b9fe6b54a5442f
  - adr-002 c25d07e15d31bc9e1758f37322c2839e4374e818b6b34f2a8137d33e789a3f77
  - adr-003 eba0f31005e5f65a58033cda061aa544f1f02bb8caa7229d97c416a6bec60402
  - adr-004 6c1d8e9e1b63663f85dea1393866438161c1904e20a51f4f3382321372175bb8
- This is the fourth round, which the person chose at the round-3 cap. The responses below are proposals: a blocking finding is open, so the person decides how the design proceeds.

## Reviewer output (unchanged)

Round 4 has **1 blocking finding and 9 non-blocking ones**. The blocker: ADR-001 decision 5 drops the second hash of the design files during review. Its reason is that "the validator's hash check shows any later change", but `validate design` never compares a review note's hashes with the manifest. Most round-3 fixes are in the text; AR3-4, AR3-5 and AR3-6 are only partly closed (AR4-4, AR4-5 and AR4-6 below).

---

# Architecture review of the design, round 4

- **Role:** orqlet-arch-reviewer, a typed subagent in a clean context.
- **Inputs given:** the design folder, `as-is.md`, `questions.yaml`, `.agents/skills/orqlet-design/references/design-format.md` and `/tmp/orqlet-workflow-efficiency-standards.txt`. Nothing else.
- **Model requested:** none named. The model I report for myself is Claude Opus 5.5, taken from my system prompt; the client reports no identity, so the observed model is unknown.
- **Context freshness:** fresh. I received only the parent's prompt.
- **Revision:** I read the working tree as described (branch `workflow-efficiency-design`, HEAD `86e07abc`, design files uncommitted). Shell commands were refused in this mode, so I could not confirm HEAD, the branch, the uncommitted state or any hash.

## Blocking findings

```yaml
- schema: orqlet.finding/v1
  id: AR4-1
  claim: >
    ADR-001 decision 5 removes the second hash of the design files taken during review.
    Its stated reason is wrong.
      - Decision 5 says: "Design hashes its files once before starting the reviewers; the
        validator's hash check shows any later change, which starts a new round."
      - validate design checks two things: each artifact's file against the manifest's sha256
        (ORQ-E356), and that each listed review note exists (ORQ-E366). It never compares the
        hashes recorded in a note with the manifest.
      - Suppose the author edits a design file after the reviewers start and refreshes its
        sha256 in the manifest, which is the normal step. Validate design then passes, and no
        check shows that the reviewers read different content.
      - Today two text rules in the design skill catch this. Step 8 records the hashes in the
        note at start and at save, and starts a new round when they differ from the manifest.
        "Done when" requires the note hashes to match the manifest.
      - Decision 5 credits the validator instead, so the design skill rewritten to EC-6 could
        drop that comparison. Content nobody reviewed could then merge. That removes a gate,
        which the brief's summary forbids.
  evidence:
    - adr-001-check-reuse-and-rechecking.md, Decision 5
    - src/orqlet/application/usecases/validate_design.py:112-126 (artifact sha256 only), 224-236 (review notes: existence only)
    - src/orqlet/workflow/skills/orqlet-design/skill.md:36 (hash at start and at save, compared with the manifest), :49 (Done when)
    - component.md section 1 ("without removing a gate"), BC-3
  confidence: high (validator code read; skill text read)
  blocking: yes
  resolves_by: >
    Reword ADR-001 decision 5 (and BC-3 and EC-6 where they mention it). Each reviewer note
    records the one set of hashes taken before the reviewers start. Before approval, those
    hashes are compared with the manifest's, as the design skill's "Done when" requires today,
    and a difference starts a new round. Drop the claim that the validator shows the change.
    Alternatively, add a validate design check of note hashes against the manifest, which is
    a scope and EC change.
```

## Non-blocking findings

```yaml
- schema: orqlet.finding/v1
  id: AR4-2
  claim: >
    Research cannot follow ADR-003 decision 1 without an instruction the design does not name.
      - Decision 1 binds base_revision before the phase branch's first commit.
      - Research commits its web evidence and then cites "it and every fact" (A-73).
      - evidence cite cites HEAD unless --revision is given (A-72).
      - So after the evidence commit, a code fact cited the usual way records the branch commit,
        not base_revision. validate as-is rejects it with ORQ-E332 (A-71), because only
        task-owned entries are exempt (EC-5).
      - ADR-001 decision 7 applies --revision to every pair in one call. Research therefore
        needs two calls: code facts with --revision base_revision, its own evidence at HEAD.
        Or it must cite every code fact before its first commit.
      - EC-6 lists the workflow text changes in detail but names neither option. BC-23 covers
        only the binding.
  evidence:
    - adr-003 decision 1; manifest EC-5, EC-6; component.md BC-23
    - src/orqlet/application/usecases/evidence_cite.py:43 (default HEAD)
    - src/orqlet/application/usecases/validate_as_is.py:117-126 (ORQ-E332)
    - src/orqlet/workflow/skills/orqlet-research/skill.md:32 (commit, then cite)
    - as-is.md A-71, A-72, A-73
  confidence: medium-high
  blocking: no
  resolves_by: >
    Add to ADR-003 decision 1 and EC-6 how research cites facts that are not task-owned once
    the branch has a commit: with --revision set to base_revision in a separate cite call, or
    before the first commit.

- schema: orqlet.finding/v1
  id: AR4-3
  claim: >
    The phase contract will almost certainly exceed its test cap, which forces a design change
    during implementation.
      - The contract has 1,799 words against an 1,800-word cap (A-2, A-8; cap confirmed at
        test_workflow_phase_contract_text.py:541-547).
      - The web-evidence section it takes in (as-is-format.md:70-87, with the template) is about
        130 words on its own. The reuse rule, the evidence-file approval in the input check and
        the change to the planned-work row come on top of that.
      - The two sentences named for removal are about 45 words.
      - ADR-004 decision 5 makes raising the cap "a design change for the person", which the
        person accepted at the round-3 cap. With these numbers, that design change is close to
        certain. It would cost an extra approval round, against the task's own aim.
  evidence:
    - as-is.md A-2, A-8
    - tests/unit/test_workflow_phase_contract_text.py:541-547
    - src/orqlet/workflow/skills/orqlet-research/references/as-is-format.md:70-87
    - adr-004 decisions 4-5; manifest EC-6
  confidence: medium (estimated from the text; shell refused, so no wc)
  blocking: no
  resolves_by: >
    Decide it in this design. Either set a new cap for phase-contract.md, with the reason that
    the binding limit is the per-run total. Or name the contract text, of about 200 words, that
    moves out or is cut.

- schema: orqlet.finding/v1
  id: AR4-4
  claim: >
    The NOT_RUN action line still tells the agent to repeat gate status when no rerun can help.
      - In implement phases 2 and later, gate status reports NOT_RUN by construction
        (ADR-001 decision 4).
      - The line reads "resolve or confirm the not-run reason(s) above, then run the command
        again".
      - After the person confirms the planned-work row, a rerun gives the same NOT_RUN. An
        agent that follows the line breaks BC-2 ("One gate status --phase per implement phase").
      - This is what remains of AR3-4.
  evidence: [adr-002 decision 2; adr-001 decision 4; component.md BC-2; gate_status.py:180-185]
  confidence: medium
  blocking: no
  resolves_by: >
    Word the line so a rerun follows only a resolved cause. For example: "Action needed:
    resolve the not-run reason(s) above and run the command again, or have the person confirm
    them." Still no mapping per finding code.

- schema: orqlet.finding/v1
  id: AR4-5
  claim: >
    The data-flow view puts the planned-work exception on the node that decides whether to
    rerun a plan check (ruff, mypy, pytest).
      - ADR-001 decision 4 applies the exception only to the validators' result (validate
        design and plan) in later implement phases.
      - Decision 2 requires an unchanged HEAD before a check result is reused.
      - Read as drawn, a later phase could reuse a pytest result across a phase commit if the
        only change was confirmed planned work.
  evidence: [views.md "Data flow: reusing a check result"; adr-001 decisions 2 and 4]
  confidence: medium
  blocking: no
  resolves_by: Label the planned-work branch "validators' result only", or draw it as a separate small flow.

- schema: orqlet.finding/v1
  id: AR4-6
  claim: >
    For design, the reference for the cited evidence files is still "the commit that recorded
    the AS-IS acceptance", which a squash merge may leave out of main's history.
      - AR3-6 proposed the commit on the protected branch that holds the acceptance. The
        answer kept today's reference instead.
      - This task's own self-check used the squash merge 86e07abc as "the commit that recorded
        the acceptance". The written rule does not say to do that.
      - Under ADR-003 the research branch is often deleted after merge (compare Q-18), so the
        branch commit may not exist in a fresh clone.
  evidence:
    - adr-003 decision 4; manifest EC-6
    - phase-contract.md:51 (design reference for the ledger)
    - manifest self_check.checks[0] (86e07abc)
    - questions.yaml Q-18
  confidence: medium
  blocking: no
  resolves_by: >
    State in ADR-003 decision 4 and EC-6 that, under squash merges, the design reference is the
    commit on the protected branch that holds the acceptance (the squash merge). Apply the same
    wording to the ledger rule.

- schema: orqlet.finding/v1
  id: AR4-7
  claim: >
    The new scan failure in validate as-is has no finding code and is missing from the brief's
    list of failures.
      - EC-5 and ADR-003 decision 3 specify the message: rule and line, treat a credential as
        exposed, no history rewrite. They name no code.
      - ORQ-E511 belongs to evidence cite. The validator's own codes are in the 33x range.
      - Brief section 5 lists no failure with this trigger and its recovery (rotate or revoke,
        fix the file, cite again, accept again).
  evidence: [manifest EC-5; adr-003 decision 3; component.md section 5; evidence_cite.py:97-112; validate_as_is.py:137-150]
  confidence: high
  blocking: no
  resolves_by: Name the code (reuse ORQ-E511 or a new 33x code) in EC-5, and add the failure to section 5.

- schema: orqlet.finding/v1
  id: AR4-8
  claim: >
    Three statements in the command-line contract do not match the rest of the design.
      1. EC-3 says "No --json output changes". The new ORQ-W547 text and the reworded ORQ-I393
         are finding messages, and the JSON envelope carries each finding's message (A-41).
         EC-1 and EC-2 also change JSON values and add data.citations.
      2. EC-1's PASS condition also covers a well-formed task name that has no artifacts. Such
         a name moves from exit 5 to exit 0. ADR-002 lists only the invalid-name and
         current-input exit changes. The input check still stops on ORQ-I394.
      3. BC-21 says "each pair is scanned as web evidence". EC-2 and ADR-001 decision 7 scan
         only pairs under evidence/web/.
  evidence: [manifest EC-1, EC-2, EC-3; adr-002 consequences; component.md BC-21; gate_status.py:153-156; evidence_cite.py:27, 56; as-is.md A-41]
  confidence: high
  blocking: no
  resolves_by: >
    EC-3: "No --json field changes; finding messages change." ADR-002: add the unknown-task
    case to the consequences. BC-21: "each pair under evidence/web/".

- schema: orqlet.finding/v1
  id: AR4-9
  claim: >
    The binding word limit (EC-6, ADR-004 decision 5) and BC-25 depend on "the words a skill
    run loads", but the design does not say how that is measured.
      - U-1, which is material, says it is unknown whether clients load references at start
        or only when the text points to them.
      - The design never cites U-1.
      - Other material unknowns also have no stated disposition: U-18, U-19, U-23 and U-31.
        So does C-3, although the implement text is being rewritten.
  evidence: [as-is.md U-1, U-18, U-19, U-23, U-31, C-3; component.md sections 6 and 8; adr-004 decision 5]
  confidence: medium-high
  blocking: no
  resolves_by: >
    Define the measure, for example the skill body, every reference it names and the AGENTS.md
    managed block, whatever the client actually loads. List the remaining material unknowns in
    section 8 as out of scope or left unverified.

- schema: orqlet.finding/v1
  id: AR4-10
  claim: >
    docs/design/work-status.md is in scope.paths, but no behaviour, BC or EC says what changes
    in it. Its line 14 ("research, design and plan have not been completed") becomes wrong
    during this task.
  evidence: [manifest scope.paths; docs/design/work-status.md:14; component.md BC-24]
  confidence: high
  blocking: no
  resolves_by: Name the update in BC-24, or remove the path from scope.
```

## Checked and consistent (no finding)

**Round-3 answers in the text:**
- **AR3-1:** Q-21 is answered (questions.yaml:419-446), and section 8 states it.
- **AR3-2:** ADR-004 decision 5 makes the per-run total and the test cap the binding limits. AR4-3 carries the remaining risk.
- **AR3-3 / SEC-R3-3:** EC-5 scans only entries that use the new exemption. BC-22 requires every existing AS-IS file to pass.
- **AR3-4:** partly closed; see AR4-4.
- **AR3-5:** ADR-001 decision 4 names the "Current" step. The view still needs a label; see AR4-5.
- **AR3-6 / SEC-R3-2:** the evidence files are among the design merge's approved files. AR4-6 carries what remains for design.
- **AR3-7:** the architecture proposal is in scope, in BC-24 and in an ADR-002 consequence.
- **AR3-8:** EC-4 names `file_operations[].why`.
- **AR3-9:** the standards file now covers `.claude`, `.cursor`, `.agents`, `.codex`, `.orqlet` and `work-status.md`.
- **AR3-10:** EC-6 names `identity.json`.
- **AR3-11:** the context view shows the writes by `orqlet upgrade`.
- **SEC-R3-1:** the credential message is in EC-5 and ADR-003 decision 3.

**Code claims checked:**
- **Gate status:** the unconditional skip at `gate_status.py:117-122` is the only NOT_RUN for a current task, so EC-1 holds. Lines 180-185, 188-191 and 205-229 match A-83: a plan's scope is its operation paths.
- **Implement order:** implement step 1 already runs `gate status --phase` at phase start (`orqlet-implement/skill.md:28`), so "once per phase" fits the current order.
- **Task-name check:** `models.py:129-131` checks `--task` against `Slug`, as ADR-002 decision 1 says. I did not read the exit code that `_require` produces.
- **Today's behaviour as described:** `evidence_cite.py:27, 43-57, 89-112` and `validate_as_is.py:112-134` match what EC-2, EC-5 and ADR-003 say about today.
- **New codes:** ORQ-W368 and ORQ-W388 are unused. The 36x and 38x ranges belong to the design, plan and ledger validators.
- **Schema export (ORQLET-DET-003):** C-11 is a module docstring (`model_policy.py:1-10`), so no exported schema changes.

**Format and standards:**
- **Design format:** D3 is correct (`.orqlet/**` is on a security glob). The set has context, container, component, data-flow and sequence views, and four ADRs with all four sections. The brief has its nine parts in order and every BC has a source. Section 9 holds constraints with reasons, not a phase order. Surfaces without an extractor use `verification: manual`.
- **Layering:** ARCH-001, 002 and 003 hold in the views. Rendering stays in the interface layer, rules in the use cases, and the domain is unchanged. The workflow package is read only by the interface through upgrade.
- **Standards:** `standards_applied` covers all 15 rules in the standards output.
- **Review notes not yet saved:** the round-4 notes are listed but do not exist yet, which is expected; validate design reports ORQ-E366 until they are saved.

## Self-check

- **Model and context:** I report my model as Claude Opus 5.5, from my system prompt. The client-observed identity is unknown. The context was fresh, with only the parent's prompt. No model was requested.
- **Not run (shell refused):**
  - the manifest's sha256 values;
  - the word count of `component.md` (the 1,200 target);
  - the word count of the phase contract (AR4-3 is an estimate);
  - HEAD, the branch and the uncommitted state;
  - `gate status`, `validate design` and `validate as-is`.
- **Limits:** this review is an additional check, not a guarantee. I made no web lookups. Every claim cites a file and lines; the counts in AR4-3 are estimates.

**Files read:**
- **The inputs:**
  - the seven design-folder files;
  - `as-is.md` and `questions.yaml`;
  - `design-format.md`;
  - the standards output.
- **To verify citations:**
  - `reviews/architecture-reviewer-design-r3.md` and `reviews/security-reviewer-design-r3.md`;
  - `gate_status.py` and `evidence_cite.py`;
  - `validate_as_is.py:90-170` and `validate_design.py:90-258`;
  - `contracts/model_policy.py:1-12`;
  - `orqlet-implement/skill.md` and `orqlet-implement/references/phase-contract.md`;
  - `orqlet-design/skill.md`;
  - `as-is-format.md:66-90`;
  - `test_workflow_phase_contract_text.py:530-555` and `test_workflow_skill_contracts.py:560-590`;
  - `docs/design/work-status.md`.
- **Searched only:**
  - `commands/models.py` (for `Slug`);
  - `src/orqlet` (for ORQ-x36x to x38x codes);
  - the skills folder (for web-evidence text);
  - the architecture proposal (for a count of NOT_RUN and ORQ-I393 mentions).

**Not examined:**
- the round-1 and round-2 review notes of both roles;
- the baseline source, `plan-format.md`, the tester role, and the review and research skill bodies beyond the search matches;
- `README.md` and the content of the architecture proposal;
- `validate.py`, `render_human.py`, `lifecycle.py`, `pin_staleness.py`, `staleness.py` and `runner.py`;
- the rest of the tests and the golden files;
- the AS-IS evidence files;
- the `.orqlet/` files and the generated client copies.

## Author's responses

The main session checked AR4-1 against `validate_design.py:224-236`, where `_check_reviews` only tests that each note exists, so the claim holds. The design files were not changed after this round, because any edit changes the hashes the reviewers saw. The responses below are proposals that wait for the person's decision:

- AR4-1, accepted. ADR-001 decision 5 keeps one hash set taken before the reviewers start, recorded in each note together with `manifest.yaml`. Before approval, the skill compares those hashes with the files and with the manifest, as the design skill's "Done when" requires today, and a difference starts a new round. The claim that the validator shows a later change is dropped. BC-3 and EC-6 follow. No validator change.
- AR4-2, accepted. ADR-003 decision 1 and EC-6 say that research cites every fact outside its own folder with `--revision` set to `base_revision`, in a call separate from its task-owned evidence.
- AR4-3, open for the person: either a new word cap for `phase-contract.md`, whose value the person sets, with the reason that the per-run total is the binding limit (the contract is shared by four skills, so moving its text into each skill would raise that total), or the contract text of about 200 words that leaves it.
- AR4-4, accepted. The NOT_RUN line becomes "Action needed: resolve the not-run reason(s) above and run the command again, or have the person confirm them."
- AR4-5, accepted. The planned-work branch of the data-flow view is labelled "validators' result only".
- AR4-6, accepted. Under squash merges, the design reference is the commit on the protected branch that holds the acceptance; the ledger rule uses the same wording.
- AR4-7, accepted. The scan failure in `validate as-is` gets the new code ORQ-E338, which `src` does not use today (a number may repeat across levels, as ORQ-E339 and ORQ-W339 do), and brief section 5 lists it with its recovery.
- AR4-8, accepted. EC-3 says "No --json field changes; finding messages change"; ADR-002 adds the unknown-task case to its consequences; BC-21 says "each pair under evidence/web/".
- AR4-9, accepted. The words a skill run loads are the skill body, every reference it names and the AGENTS.md managed block. Section 8 lists U-1, U-18, U-19, U-23, U-31 and C-3 as left unverified.
- AR4-10, accepted. BC-24 names the update of `docs/design/work-status.md` in the final implementation commit.

## Decision after round 4

On 2026-11-23 the person chose to apply every proposed response above and to review the resulting changes themselves instead of a fifth subagent round. They answered AR4-3 with Q-22: the phase contract's test cap rises to 2,000 words. The changes are applied in the design files, so the hashes at the top of this note are those of the reviewed round-4 content, not of the design that goes to the pull request.
