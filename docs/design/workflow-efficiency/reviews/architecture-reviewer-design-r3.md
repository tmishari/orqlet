# Architecture review of the design, round 3

- Role: orqlet-arch-reviewer, started as a typed Cursor subagent in a clean context (agent ed02ffc7-b985-40c5-8e8e-2e45abd53248).
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

# Architecture review of the workflow-efficiency design, round 3

This round has **one blocking finding and ten non-blocking ones**.

- **Blocking:** Q-21 is set to block only the plan. If the person answers "refresh the AS-IS file", an approved design becomes invalid.
- **Non-blocking, most important:** the phase contract has one word of headroom under its cap but has to take in a lot of new text. The new evidence scan also contradicts the promise that every AS-IS file valid today stays valid.
- **Structure:** the design meets the format. It has class D3, a context view and a container view, four ADRs with all four sections, the nine brief parts in order, a source on every acceptance criterion, and no phase list.

## Blocking findings

```yaml
- schema: orqlet.finding/v1
  id: AR3-1
  claim: >
    Q-21 is marked as blocking the plan only, and brief section 8 says so. But one of its two
    answers, "Refresh the AS-IS file before the plan", changes as-is.md.
    If that happens after the design pull request merges:
      - validate design reports ORQ-E353, because the AS-IS file changed after the design cited it;
      - the plan's input check stops, because as-is.md is an approved file of the design merge.
    The approved design would then need to be bound again and approved again.
    So Q-21 is a consequential decision for the design. The design format and the design
    skill treat such a decision as a ledger question that blocks design. Today validate design
    passes with Q-21 open, so the design could merge before Q-21 is answered.
  evidence:
    - questions.yaml:419-440 (Q-21 has two options and blocks [plan] only)
    - component.md section 8 ("None blocks design. Q-21 blocks the plan.")
    - src/orqlet/application/usecases/validate_design.py:97-109 (ORQ-E353 when the AS-IS hash differs from as_is_ref)
    - src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md:45, 56 (as-is.md is an approved file of the design merge; an edited approved input stops the skill)
    - src/orqlet/workflow/skills/orqlet-design/skill.md:20, 53; design-format.md:35
  confidence: high (mechanism read in code and contract text)
  blocking: yes
  resolves_by: >
    Get Q-21 answered before the design pull request, or change it to block design
    (validate design then reports ORQ-E367 until it is answered). If the answer is "refresh",
    refresh the AS-IS file, re-accept it and bind the design again before approval.
```

## Non-blocking findings

```yaml
- schema: orqlet.finding/v1
  id: AR3-2
  claim: >
    The word budget may not be achievable as written.
      - phase-contract.md has 1,799 words against an 1,800-word test cap, and EC-6 and
        ADR-004 decision 5 say no reference file grows.
      - The contract must take in the web-evidence format (about 150 words with its fenced
        template), the reuse rule, the input check by phase and the changed planned-work row.
      - Only the ORQ-I393 sentence and the "cite every source again" sentence are obviously freed.
      - The design names nothing else that leaves the contract.
    The same per-file "no growth" rule applies to the formats, which gain length targets and
    an ask for evidence ids, to the tester role and to the implement skill, which gain guidance.
    If the rule cannot be met, the implementation deviates from EC-6, which needs a new design approval.
  evidence:
    - as-is.md A-2, A-8
    - src/orqlet/workflow/skills/orqlet-research/references/as-is-format.md:70-87
    - phase-contract.md:29, 54
    - manifest EC-6; adr-004 decisions 4-6
  confidence: medium (word counts not run; shell refused)
  blocking: no
  resolves_by: >
    Name the contract text that moves out or is cut. Or keep only the per-run total and the
    test cap as the binding limits, with a reason.

- schema: orqlet.finding/v1
  id: AR3-3
  claim: >
    Two parts of the design contradict each other:
      - EC-5 and ADR-003 consequence 5 say that "the rule only accepts more" and that every
        AS-IS file valid today stays valid;
      - ADR-003 decision 3 adds a size, credential and hidden-character scan of every
        task-owned file the facts cite, including entries at base_revision. Some of those files
        were never scanned: evidence/checks/*.md, evidence/transcripts/ and evidence/web/ files
        that may predate the cite-time scan.
    Six AS-IS files cite task-owned evidence, and the frozen ones cannot be edited (Q-10).
    My searches found no "<!--", no common hidden code points and no obvious credential
    shapes in docs/design/*/evidence/. File size and line length (>4096) were not checked.
  evidence:
    - manifest EC-5; adr-003 decision 3 and consequences
    - src/orqlet/domain/resources.py:387-424 (an HTML comment, a hidden code point or a line over 4096 characters is a finding)
    - evidence_cite.py:27, 97-112
    - Grep (count of task-owned evidence citations): workflow-efficiency 15, one-command-setup 31, dynamic-model-profiles 85, phase-skill-contracts 8, team-conventions-resources 66, mcp-or-plugins 112
  confidence: high (contradiction in the text); low (that any file actually fails)
  blocking: no
  resolves_by: >
    Scan only the entries that use the new exemption, or add an acceptance criterion that
    validate as-is still passes on every existing AS-IS file. Then reword "only accepts more".

- schema: orqlet.finding/v1
  id: AR3-4
  claim: >
    From the second implement phase on, gate status reports NOT_RUN by construction (ORQ-W390).
    Its action line would then say "resolve the not-run reason(s) above, then run the command
    again". The right step is the person's confirmation under the planned-work row, and running
    the command again changes nothing. This brings back a "not run" message the agent must
    learn to read differently, which ADR-002 sets out to remove.
  evidence: [adr-002 decision 2 and consequence 1; adr-001 decision 4; gate_status.py:179-184]
  confidence: medium
  blocking: no
  resolves_by: >
    Word the NOT_RUN line so it also covers confirming a stale cause (for example "resolve or
    confirm the not-run reason(s) above"), still with no mapping per finding code.

- schema: orqlet.finding/v1
  id: AR3-5
  claim: >
    ADR-001 decision 4 reuses the validators' result in later phases when "the currency check
    shows no change", but the design never defines the currency check.
    The data-flow view also contradicts decision 4: it reruns whenever HEAD differs, while
    decision 4 reuses across phase commits. Only the note in the sequence view states the exception.
    The reuse itself is sound if the currency check means the input check's "Current" step.
    validate plan reads the base tree at plan.base_revision, and validate design reads the
    manifest, its artifacts, the AS-IS file, the ledger and the review notes; none depends on HEAD.
  evidence:
    - adr-001 decisions 2 and 4; views.md (data-flow and sequence)
    - phase-contract.md:56
    - validate_plan.py:102-112
    - validate_design.py:105, 121, 235, 252
  confidence: medium-high
  blocking: no
  resolves_by: >
    Name the check: phase contract step 6, the git diff since each merge plus the ledger rule.
    Show the exception in the data-flow view.

- schema: orqlet.finding/v1
  id: AR3-6
  claim: >
    ADR-003 decision 4 and EC-6 compare the cited evidence files with "the commit that recorded
    the AS-IS acceptance". In plan and implement, as-is.md itself is compared with the design
    merge, which the person names and the input check verifies as reachable.
    Under squash merges, the acceptance commit may be a research-branch commit that main does
    not reach. That is the same fragility ADR-003 removes for base_revision. The input check
    names no way to verify that commit.
  evidence: [adr-003 decision 4; manifest EC-6; phase-contract.md:45-50, 56]
  confidence: medium
  blocking: no
  resolves_by: >
    Compare the cited evidence with the same reference as as-is.md in each phase: the design
    merge for plan and implement, and for design the commit on the protected branch that holds
    the acceptance.

- schema: orqlet.finding/v1
  id: AR3-7
  claim: >
    The architecture proposal states that offline gate status reports NOT_RUN for approval,
    and the gate_status.py docstring cites "proposal 17.6 and 17.7". EC-1 changes this
    behaviour. The proposal is outside scope.paths, and ADR-002 does not say whether it is
    superseded. The baseline asks that documentation a change makes wrong is updated in the
    same change. Whether this proposal is maintained documentation is unknown.
  evidence:
    - docs/design/orqlet-architecture-proposal.md:3030, 4288, 4589
    - gate_status.py:1-8
    - manifest scope.paths
  confidence: medium (text read; the document's status is unknown)
  blocking: no
  resolves_by: >
    Ask the person. Then either add the proposal to the scope and to BC-24, or record in
    ADR-002 that the proposal stays historical.

- schema: orqlet.finding/v1
  id: AR3-8
  claim: >
    EC-4 and ADR-004 decision 1 count "file-operation reasons". The plan contract field for a
    file operation is `why`; `reason` exists only on ReuseDecision.
  evidence: [src/orqlet/application/contracts/plan.py:27-31, 72-75; manifest EC-4]
  confidence: high
  blocking: no
  resolves_by: Name the counted fields as objective, acceptance_criteria[].text and file_operations[].why.

- schema: orqlet.finding/v1
  id: AR3-9
  claim: >
    The standards output I was given covers src paths, tests, README.md and docs/design only.
    The manifest self-check claims one run for ".prompts, README.md, AGENTS.md, .github,
    .orqlet/workflow.lock". No run is shown or claimed for these scope paths: .claude/**,
    .cursor/**, .agents/**, .codex/**, .orqlet/** as a whole, or docs/design/work-status.md.
  evidence: [/tmp/orqlet-workflow-efficiency-standards.txt; manifest self_check.applicable_standards; phase-contract.md:13]
  confidence: medium (the runs may exist outside the file I was given)
  blocking: no

- schema: orqlet.finding/v1
  id: AR3-10
  claim: >
    The workflow version's source is identity.json, which tools/build_manifest.py reads.
    EC-6 names only MANIFEST.json. The file is inside the scope.
  evidence: [src/orqlet/workflow/identity.json:4; tools/build_manifest.py:35-38]
  confidence: high
  blocking: no

- schema: orqlet.finding/v1
  id: AR3-11
  claim: >
    The context view shows the CLI only reading the Git repository. orqlet upgrade writes the
    generated files and the .orqlet locks (EC-8, brief section 3).
  evidence: [views.md context view; manifest EC-8]
  confidence: high
  blocking: no
```

## Checked and consistent (no finding)

- **Gate status verdict and later phases:**
  - The unconditional skip at `gate_status.py:117-122` is the only reason a current task reports NOT_RUN today, so EC-1's PASS condition holds.
  - `gate_status.py:179-229` and `staleness.py:11-30` confirm ORQ-W390 in later implement phases. A plan's scope is its file-operation paths (lines 188-191).
- **Action lines come from data, not finding codes:** `Outcome.MANUAL` exists (`domain/expected_change.py:38`), and `data.artifacts[*].found` is false for each missing artifact. So both gate status lines need no mapping per finding code.
- **New warning codes:** ORQ-W368 and ORQ-W388 are unused in `src`.
- **Version 0.5.1:**
  - The CLI version lives only in `src/orqlet/__init__.py:3`; `pyproject.toml:7` reads it dynamically, and `uv.lock` holds no version.
  - The plan contract compares versions semantically (`plan.py:24`), so 0.5.1 keeps the code-reviewer requirement.
- **Current validator and cite behaviour:** `validate_as_is.py:112-134` and `evidence_cite.py:27, 56, 89-112` match what EC-5 and ADR-003 describe as today's behaviour.
- **BC-16 is reachable:** the design skill ships its own phase contract (`MANIFEST.json:237`).
- **Round 2 answers:** AR2-1 to AR2-8 are reflected in the current text. The answers to AR2-1 and AR2-2 are where AR3-1, AR3-5 and AR3-6 come from.
- **Standards:** `standards_applied` covers every rule the output prints, and the self-check's hashes match the output file.
- **Review notes not yet saved:** the manifest lists the round-3 notes, which do not exist yet. Validate design will report ORQ-E366 until they are saved (`validate_design.py:235-236`), which is the expected order of steps.

## Self-check

- **Model and context:** I ran as a typed `orqlet-arch-reviewer` subagent in a fresh context, with only the parent's prompt. Model requested: none named. Model observed: unknown.
- **Not run:** shell commands were refused in this mode. So I did not verify:
  - the manifest's sha256 values;
  - the 1,200-word count of `component.md`;
  - the word count of the phase contract;
  - the branch, HEAD or uncommitted state;
  - any `gate status` or `validate` run.
- **Limits:** AR3-3's breakage risk rests on pattern searches, not on running the scan. This review is an additional check, not a guarantee, and I made no web lookups.

**Files read:**
- **The inputs:**
  - the seven design-folder files;
  - `as-is.md`;
  - `questions.yaml`;
  - `.agents/skills/orqlet-design/references/design-format.md`;
  - the standards output.
- **To verify citations:**
  - `reviews/architecture-reviewer-design-r2.md`;
  - `gate_status.py`, `staleness.py`, `evidence_cite.py` and `validate_as_is.py`;
  - parts of `validate_design.py` and `validate_plan.py`;
  - `contracts/plan.py`;
  - the implement phase contract;
  - the design `skill.md`;
  - `as-is-format.md` from line 60;
  - `src/orqlet/__init__.py` and `workflow/identity.json`.
- **Searched only:**
  - `pyproject.toml`, `uv.lock` and `MANIFEST.json`;
  - `domain/resources.py` and `domain/expected_change.py`;
  - `tools/build_manifest.py`;
  - `docs/design/*/evidence/**`, the task-owned evidence citations in other AS-IS files, the architecture proposal, the golden files and `test_workflow_skill_contracts.py` (for ORQ-I393 and NOT_RUN text).

**Not examined:**
- both security reviewer notes and the round-1 architecture note;
- the other skill bodies, the baseline source, `plan-format.md` and the tester role;
- `pin_staleness.py`, `models.py`, `render_human.py` and `validation.py`;
- the tests, including the caps cited by A-7 and A-8;
- the contents of the AS-IS evidence files;
- `docs/design/work-status.md`.

## Author's responses

Proposed changes, which wait for the person's decision because the round cap has been reached:

- AR3-1, accepted. Q-21 blocks design, so the design cannot merge until it is answered. If the answer is "refresh", the AS-IS file is refreshed and accepted again, and the design is bound again before approval.
- AR3-2, accepted. The binding limits become the words a skill run loads and each file's test cap. The phase contract takes in the web-evidence format and the reuse rule, and the ORQ-I393 sentence and the "cite every source again" sentence leave it. If the result exceeds the test cap, raising the cap is a design change for the person, not an implementation decision.
- AR3-3, accepted, together with SEC-R3-3. The scan in `validate as-is` covers only entries that use the new exemption, which are read at HEAD, and it covers the bytes the hash check reads. Entries that cite `base_revision` stay as today, so "only accepts more" holds. A new acceptance criterion requires `validate as-is` to pass on every existing AS-IS file after the change.
- AR3-4, accepted. The NOT_RUN line becomes "Action needed: resolve or confirm the not-run reason(s) above, then run the command again."
- AR3-5, accepted. The currency check is the input check's "Current" step of the phase contract. The data-flow view shows the exception for confirmed planned work.
- AR3-6, accepted, together with SEC-R3-2. The cited evidence files are compared with the same reference as `as-is.md` in each phase: for design, the commit that recorded the AS-IS acceptance; for plan and implement, the design merge, among whose approved files they are added.
- AR3-7, open for the person: whether `docs/design/orqlet-architecture-proposal.md` is maintained documentation that EC-1 makes wrong, or a historical record.
- AR3-8, accepted. The counted fields are `objective`, `acceptance_criteria[].text` and `file_operations[].why`.
- AR3-9, accepted. `orqlet standards for --phase design --role architect` on `.claude`, `.cursor`, `.agents`, `.codex` and `.orqlet` printed 3 rules (hash 7cedb45e…), and on `docs/design/work-status.md` 4 rules (hash 9943630a…). All of them are already in `standards_applied`. The self-check records these runs.
- AR3-10, accepted. EC-6 names `src/orqlet/workflow/identity.json` as the source of the workflow version.
- AR3-11, accepted. The context view shows `orqlet upgrade` writing the generated files and the `.orqlet` locks.

## Decision at the round cap

On 2026-11-23 the person chose to apply every proposed change above and run a fourth round with fresh reviewers. They answered Q-21 with an AS-IS refresh before this design is approved, and named `docs/design/orqlet-architecture-proposal.md` maintained documentation, now in the design scope. The proposed changes are applied in the design files.
