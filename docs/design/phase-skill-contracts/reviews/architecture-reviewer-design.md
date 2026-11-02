# Architecture review of the design: phase-skill-contracts

Reviewer: `orqlet-arch-reviewer`, started as a typed subagent in its own context. Input: the files under `docs/design/phase-skill-contracts/` (design set, AS-IS file, ledger), `src/orqlet/workflow/skills/orqlet-design/references/design-format.md` and the output of `orqlet standards for --phase design --role architect` and `--path` for the scope. Files the design cites were opened only to verify a citation.

## Round 1: FAIL

The reviewer's full output of round 1 was not saved. The findings below are the author's summary of it, with the reviewer's ids. Finding F-1 was blocking.

| Id | Finding (summary) | Author's response |
|---|---|---|
| F-1 | Continuing on a stale input after the person's answer conflicts with W-5, which says a stale approval is invalid and cannot be waived; no citation supported it | ADR-003 decision 6 now maps each stale cause to a row of the proposal's invalidation matrix (`docs/design/orqlet-architecture-proposal.md:3055-3084`). The skill continues only where the row keeps the approval valid and the person confirms; otherwise it stops for a refresh, an impact review or a new approval. BC-15 |
| F-2 | The tests with `BEFORE_RECORDS` fail when the new sections name a later command, and implement's Next naming `/orqlet-review` breaks `test_skills.py:212-221` | ADR-001 decision 2: any line naming a command an earlier release lacks carries a `requires` marker. ADR-001 decision 5: Next does not repeat a skill a step already hands over to. BC-2, BC-3 |
| F-3 | The design-review input for reviewers is too narrow to verify citations | ADR-004 decision 7 and BC-25: design folder, AS-IS file, ledger, design format reference, standards output; cited files only to verify |
| F-4 | The claim that upgrade renders the conventions block again contradicts U-15 | ADR-002 decision 7: the agent reports the disagreement and names no fix command |
| F-5 | A cross-reference named decision 5 instead of decision 7 | Corrected |
| F-6 | "Eight new files" holds only when two skills folders are rendered | Four per skills folder, eight with both, in ADR-001, ADR-005, considerations and the sequence |
| F-7 | BC-6 and the data-flow claim ignore the resource registry (A-25) | BC-6 is limited to the workflow skills, references and roles with no registry; `data-flow.md` names both existing ways project data reaches rendered files |
| F-8 | R-9 omits the request's "phase outputs" | R-9 restored, with Q-9 narrowing it |
| F-9 | How the design reads Q-3 is not stated | Stated in the summary of `component.md` |
| F-10 | No criterion for R-1, the size part of R-4, R-13, the tester, or research's own input check | BC-34 (three places), BC-35 (size), BC-36 (final report), BC-26 (tester), BC-37 (research) |
| F-11 | Criterion wording: `BEFORE_RECORDS`, the pinned reviewer phrases, an incomplete CI list in BC-31, "stale" in BC-32, the allowed source types | BC-2, BC-25, BC-31 (full CI set and matrix), BC-32 (ORQ-E150, ORQ-W152), criterion sources widened |
| F-12 | U-13 (init output against goldens), U-14 and C-16 (upgrade may stop on a pending diff), C-4 and C-3 are not carried into the design | BC-38; an unresolved decision and an operations note for U-14 and C-16; ADR-002 decisions 1 and 7 for C-4 and C-3 |
| F-13 | The two recorded acceptance quotes differ, no time is recorded, and the AS-IS file still lists Q-8 as open | The manifest's self-check states both quotes, the missing time, and why the AS-IS text predates the answer |
| F-14 | The self-check has no validate entry and the manifest no reviews | Both added after this review |
| O-1 | Nothing validates the hash recorded for `considerations.md` | Kept as a self-check entry; no validator covers it |
| O-2 | A-55 was cited for the roles' no-lookup sentence | BC-26 cites `tests/unit/test_workflow_lookup_text.py:417-425` |
| O-3 | ORQ-W338 had no source | ADR-004 cites `src/orqlet/application/usecases/validate_as_is.py:165-180` |
| O-4 | The README facts were uncited | `README.md:132` and `README.md:312-321` |
| O-5 | The security globs miss Python files at the top of `src/orqlet/` and in the workflow package | Globs extended; checked that no scope path matches |
| O-6 | Test support gives predictable ids and a workflow change limited to the baseline | Constraint for the plan in `component.md` |
| O-7 | The role word `coder` was uncited | ADR-002 decision 7 cites the proposal's Phase 4 Coder |
| O-8 | Keeping controls level 3 needs its reading stated | ADR-005 decision 2, with the earlier lookup release as precedent |

## Round 2: FAIL

Files reviewed, hashed by the author with `shasum -a 256` right after the reviewer returned; no file changed between the reviewer's start and the hashing. The reviewer could not run a shell.

| File | sha256 |
|---|---|
| `design/manifest.yaml` | `27998171cfdbfbf2c861133f683865cd2ad7728355b2f7f245c078c4a21cb779` |
| `design/context.md` | `8eb078df676b8829c563094c2a0b1e686df9bc747a7c6adb79a40062e0b88712` |
| `design/container.md` | `377747324613de61b84a53eaaed072bf16c0aca96378ea8104b6b3064ce98e8d` |
| `design/component.md` | `8accf697b7a60ede9d3a9435458dbbd29f183afe6e7bc350d2b724f875cb44b5` |
| `design/data-flow.md` | `67bfe10fa0e11f897ec8d021333ad1513b12d50ab004d1070b3837a55150da4c` |
| `design/sequence.md` | `5ebbda184ba6e28a01767285676952ca8b3f1fd67fbd64e3ca69ef59b06d7f7f` |
| `design/considerations.md` | `31f4d93c34a3d92580f38ee7a53088d4abafa437756bcd061e8f636e55aa67f8` |
| `design/adr-001-one-contract-shape-for-every-skill.md` | `ed1630c2ce902055b363344f1465b19b20fbfad3117966e38ab62cdd7a6b5d95` |
| `design/adr-002-project-context-read-at-execution-time.md` | `93ae05b73816566801a1199dcc2833f1477654321dbe7f53f450990647ebbce2` |
| `design/adr-003-handoffs-and-the-input-check.md` | `03ebac2d73b271bef54152ee7169cc53d6ff6c47a81c46c25fb1923ddc94c3a2` |
| `design/adr-004-what-each-phase-produces.md` | `be49e1238143bec084bc7282de7af15313b343d9f5981debc3895b23131bc2a5` |
| `design/adr-005-injection-unchanged-tests-and-version.md` | `1bf6b95bc78bccb0f3f6b18a03425a33a4e288b86a306be123f06f32a902ded0` |
| `as-is.md` | `e1c968ac76ab29556a317fc45063c3f4e8849f627b8562b84549cba03189fd0f` |
| `questions.yaml` | `ebb6d3a685c75d3d2d0a7bc7708426b307658ec016268df01a6ff8ef109d92fa` |

### The reviewer's output, unchanged

```yaml
round: 2
verdict: FAIL
reviewed_files:
  - {path: docs/design/phase-skill-contracts/design/manifest.yaml, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/context.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/container.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/component.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/data-flow.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/sequence.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/considerations.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-001-one-contract-shape-for-every-skill.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-004-what-each-phase-produces.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-005-injection-unchanged-tests-and-version.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/as-is.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/questions.yaml, sha256: not computed}
round_1_resolution:
  - id: F-1
    resolved: partly
    note: "ADR-003 decision 6 now maps the ORQ-W390 causes to matrix rows with proposal citations that hold (proposal:3055-3084, :3375). But ORQ-E353 and ORQ-E371 are sent to that same mapping, and the mapping has no row for editing an approved artifact. See F2-1."
  - id: F-2
    resolved: yes
    note: "render_steps drops any marked line with its indented continuation, not only steps (workflow_sources.py:65-73; test_skills.py:60-70 pins a marked paragraph). ADR-001 decision 5 keeps /orqlet-review out of implement's Next, which keeps test_skills.py:216 holding. Leftover wording issues are in F2-5 and F2-6."
  - id: F-3
    resolved: yes
    note: "ADR-004 decision 7 and BC-25 name exactly the inputs this review received."
  - id: F-4
    resolved: yes
    note: "ADR-002 decision 7, under Disagreements, names no fix command (U-15)."
  - id: F-5
    resolved: yes
    note: "All ADR decision cross-references in component.md, the manifest and considerations.md resolve to the right decision."
  - id: F-6
    resolved: partly
    note: "Fixed in ADR-001, ADR-005, considerations and the manifest. container.md:42 still says 'eight new reference files' unconditionally. See F2-7."
  - id: F-7
    resolved: yes
    note: "BC-6 is limited to projects with no resource registry; data-flow.md:20-21 names both existing routes, A-24 and A-25."
  - id: F-8
    resolved: yes
    note: "R-9 (component.md:28) carries 'existing locations for task documentation and phase outputs' and says how Q-9 narrows it."
  - id: F-9
    resolved: yes
    note: "component.md:7-13 states how the design reads Q-3."
  - id: F-10
    resolved: yes
    note: "BC-34, BC-35, BC-36, BC-26 (tester) and BC-37 are present. BC-35 does not really measure size; see F2-10."
  - id: F-11
    resolved: partly
    note: "BC-2 now cites BEFORE_RECORDS at test_skills.py:192-199 (holds); BC-25's phrases match test_skills.py:493-501; BC-32 names ORQ-E150 and ORQ-W152. BC-31 still leaves out the CI build job and the operating-system axis of the test matrix (F2-8). The BC-26 citation claims more than the test pins (F2-9)."
  - id: F-12
    resolved: yes
    note: "BC-38 covers U-13. U-14 and C-16 are in Unresolved decisions (component.md:170) and considerations.md. C-4 is in ADR-002 decision 1 and C-3 in decision 7. Whether BC-38 can be met is questioned in F2-10."
  - id: F-13
    resolved: yes
    note: "manifest.yaml:165-167 states both acceptance quotes, that no time was recorded, and why the AS-IS question list still shows Q-8 as open."
  - id: F-14
    resolved: partly
    note: "Deferred by the author: manifest.yaml:158 still has 'reviews: []' and the self-check has no 'orqlet validate design' entry. This is consistent, because DesignSet requires reviews at D2 and above (design_set.py:142), so validation cannot pass until the notes are listed. Check again when the round closes. The round-1 note is the author's summary, not the reviewer's own output."
  - id: O-1
    resolved: yes
    note: "Kept as a self-check entry (manifest.yaml:180-182). No validator covers it; the hash was not re-computed here."
  - id: O-2
    resolved: yes
    note: "test_workflow_lookup_text.py:417-425 pins the no-lookup sentence exactly once in every role."
  - id: O-3
    resolved: yes
    note: "validate_as_is.py:165-180 emits ORQ-W338 for advice in the body."
  - id: O-4
    resolved: yes
    note: "README.md:132 holds the count of 65 files; README.md:312-321 holds the skill table."
  - id: O-5
    resolved: yes
    note: "manifest.yaml:47-64 lists src/orqlet/*.py and src/orqlet/workflow/**/*.py. The glob_match check was not re-run."
  - id: O-6
    resolved: yes
    note: "Stated as a constraint for the plan in component.md:179."
  - id: O-7
    resolved: yes
    note: "proposal:3372 (W-2) names the Phase 4 Coder."
  - id: O-8
    resolved: yes
    note: "ADR-005 decision 2 states the reading, and proposal:3962-3970 holds the control classes. The precedent commit b841ccd was not verified."
findings:
  - id: F2-1
    severity: major
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:39-50; docs/design/phase-skill-contracts/design/component.md:60, 121-125; docs/design/phase-skill-contracts/design/sequence.md:31-34
    finding: >-
      The rules for stale inputs contradict each other, and they leave out the matrix row for an edited
      approved artifact. (a) In decision 4, the 'Same task' check stops unless the input's validator
      passes. The 'Current' check sends ORQ-E353 and ORQ-E371 to decision 6. The failures table lets
      E353 and E371 continue when a matrix row keeps the approval valid. Sequence 1 and session check
      V-2 stop on E353. (b) Decision 6 counts as 'this task's planned work' any trailer commit that changes
      'the task's own records under docs/design/<task>/'. That path covers as-is.md, questions.yaml,
      design/ and plan.yaml. Example: a commit with the task's trailer edits design/manifest.yaml. The
      plan's validator then reports E371, decision 6 classes the commit as planned work, and the row
      says the approval is valid. (c) Nothing in the input check notices an edit to the merged plan.yaml,
      because no artifact's scope or reference covers its bytes.
    evidence: >-
      The proposal's Table 2: 'Editing the approved design or plan (any byte of an approved file)' makes
      both approvals invalid and needs a new approval pull request (proposal:3073). Changed requirements
      make both approvals invalid (proposal:3074). An answer that supersedes an earlier one is a
      staleness event (proposal:3088). The exemption is limited to 'the task's own evidence records (the
      exact paths of Section 6.14.1)' (proposal:3054). gate_status.py:188-191 gives the plan only its
      operation paths as scope. W-5: 'a stale approval is invalid' (proposal:3375). ADR-003
      Consequences, line 57: 'Nothing is relaxed'.
    required_change: >-
      Map ORQ-E353 and ORQ-E371 to the rows for an edited approved artifact and for changed
      requirements: the approval is invalid, the skill stops for a new approval, and it never continues.
      Do the same for any commit since the approval that touches as-is.md, design/, plan.yaml or a
      superseding ledger answer, including commits on plan.yaml after the merge. Limit 'records' in the
      planned-work row to the exact record paths (reviews/, tests/, knowledge/, evidence/web/). Make
      decision 4's 'Same task' and 'Current' checks, the failures table, BC-15 and sequence 1 say the same
      thing, and add one criterion that pins it.
  - id: F2-2
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:47
    finding: >-
      A protected_set_digest change is mapped to the row for 'a newer accepted workflow version;
      approval valid'. That digest can change while workflow_version does not, for example when the
      protected conventions block is rendered again after a profile answer, or when a resource is
      registered and adds protected skills.
    evidence: >-
      gate_status.py:70-77 computes the digest over every protected lock entry. instructions.py:26-37
      makes the conventions block PROTECTED. skills.py:74 makes every skill PROTECTED (A-25). The matrix
      row requires a change of workflow_version (proposal:3081).
    required_change: >-
      Map the row to an upgrade only when workflow_version changed too. Otherwise send it to 'a cause it
      cannot match: stop and ask'.
  - id: F2-3
    severity: minor
    where: docs/design/phase-skill-contracts/design/component.md:120, 126
    finding: >-
      BC-16 says only gate status's stale and error findings block. That contradicts ADR-003 decision 4,
      which stops on ORQ-I394 for an input (an info finding) and on the 'is not in this repository' skip
      line. BC-14 asks design for 'confirmation of a merge', but design's input is the AS-IS file, which
      is accepted under decision 7, not merged.
    evidence: adr-003:38, 40-41; gate_status.py:155, 220
    required_change: >-
      BC-16: NOT_RUN caused by ORQ-I393 alone is not a failure; the checks of ADR-003 decision 4 decide
      everything else. BC-14: a merge for plan and implement, acceptance for design.
  - id: F2-4
    severity: minor
    where: docs/design/phase-skill-contracts/design/sequence.md:21-32
    finding: >-
      Sequence 1 runs git merge-base on the base revision before orqlet validate design. ADR-003
      decision 4 says the validator runs first, and the SEC-15 control relies on that. The stale branch
      also ends after 'Continue?' without the Same-task, Approved and Questions checks.
    evidence: adr-003:37; considerations.md:23
    required_change: Show the validator before the git commands, and continue the confirmed stale path into the remaining checks.
  - id: F2-5
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-001-one-contract-shape-for-every-skill.md:36
    finding: >-
      The Consequences say the step count of implement changes and that the two tests that render
      without the record commands 'stay as they are'. One of those two tests pins exactly seven steps
      without the records.
    evidence: tests/unit/render/test_skills.py:212-221 (range(1, 8))
    required_change: >-
      List test_skills.py:212-221 among the tests that change, or state that implement keeps ten steps,
      three of them marked as needing the record commands.
  - id: F2-6
    severity: minor
    where: docs/design/phase-skill-contracts/design/component.md:178; adr-001:16
    finding: >-
      ADR-001 decision 2 puts a requires marker on any line that names a command. The lookup tests
      require exactly one line in each of four skills that carries the 'requires: resources list'
      marker. No constraint stops a non-step line from naming 'orqlet resources list'.
    evidence: tests/unit/test_workflow_lookup_text.py:239-243
    required_change: >-
      Add a plan constraint: no line other than the lookup step names a command gated by 'resources
      list'. Alternatively, state that this test changes.
  - id: F2-7
    severity: minor
    where: docs/design/phase-skill-contracts/design/container.md:42
    finding: "This is left over from F-6: 'eight new reference files' is stated without the condition that both skill folders are rendered."
    evidence: adr-001:38; considerations.md:31
    required_change: Say 'four per skills folder, eight with both'.
  - id: F2-8
    severity: minor
    where: docs/design/phase-skill-contracts/design/component.md:150; considerations.md:45
    finding: >-
      'Every CI job' cites ci.yml:30-84. That range leaves out the build job, which builds the wheel twice
      and compares the digests, and the test matrix across operating systems.
    evidence: .github/workflows/ci.yml:72-74, 86-107
    required_change: Include the build job and the ubuntu, macOS and Windows matrix, or state why they are excluded.
  - id: F2-9
    severity: minor
    where: docs/design/phase-skill-contracts/design/component.md:143
    finding: >-
      BC-26 cites test_skills.py:473-480 for 'every role keeps never an instruction exactly once'. That
      test checks only that the phrase is present, and only in the four read-only roles.
    evidence: tests/unit/render/test_skills.py:476-478; tests/support/render.py:53
    required_change: Reword BC-26 to match what the test pins, or say that the test is extended to the tester and to 'exactly once'.
  - id: F2-10
    severity: minor
    where: docs/design/phase-skill-contracts/design/component.md:154, 93
    finding: >-
      BC-38: the goldens are adapter output for packaged_request(), with SAMPLE_RULES, no conventions and
      no resources. What init writes depends on the project's resolved packs and profile, and the sample
      fixture pack's rule texts differ from SAMPLE_RULES. The design does not say which init setup can
      reproduce the goldens. Separately, BC-35 caps lines, but each step is a single line, so the cap
      does not bound concision (R-4).
    evidence: >-
      test_clients_golden.py:41; tests/support/render.py:65-100 (lines 81 and 90);
      tests/fixtures/packs/sample/rules/python.yaml:11, 14; resources_view.py:199-200;
      orqlet-implement/skill.md:14 (one step of about 120 words on one line)
    required_change: >-
      Add a constraint naming the init setup that reproduces the golden request, or narrow BC-38 to the
      workflow skill, reference and role paths. Bound bytes or words in BC-35 as well, or state why lines
      suffice.
not_verified:
  - "No sha256 was computed: the shell was refused in this read-only session. The manifest's recorded artifact hashes, as_is_ref and the considerations.md hash were not checked."
  - "orqlet validate design, orqlet validate ledger, orqlet gate status and the glob_match check behind the self-check were not run."
  - "ADR-005's commit facts (b841ccd, 2799dc3, the patch history) were not checked against git."
  - "Section 6.14.1 of the proposal (the exact record paths) was not opened."
  - "Whether init in a test environment can reproduce the goldens byte for byte (BC-38) was not tried."
  - "Client behaviour (U-11) and session checks V-1 to V-3 are outside a document review."
  - "The security reviewer's note and evidence/web/cursor-skills.md are outside this input and were not read."
  - "The round-1 findings are known only from the author's summary; the reviewer's original output was not saved."
  - "Feasibility of the 70-line bodies, the four identical phase-contract.md copies and the two-project test was judged from the cited tests and code only. None of the new texts exists yet."
```

### Author's responses to round 2

| Id | Response |
|---|---|
| F2-1 | ADR-003 decision 4 now has the order validator, present, same task, same project, approved, current, questions. *Approved* for plan and implement: the person names each approval's merge commit, which must be an ancestor of HEAD, and `git diff --quiet <merge> -- <approved files>` must find no difference. *Current*: ORQ-E353, ORQ-E371 and a superseded ledger answer map to the rows "editing the approved design or plan" and "changed requirements" (proposal:3073-3074, :3088). The skill stops for a new approval and never continues. Decision 6 handles ORQ-W390 only. Planned work is limited to the record folders `reviews/`, `tests/`, `knowledge/` (proposal:1039) and `evidence/web/` (`evidence_cite.py:27`). A commit touching `as-is.md`, `design/`, `plan.yaml` or `questions.yaml` is never planned work. The failures table, BC-14, BC-15, the new BC-39 and sequence 1 say the same |
| F2-2 | The upgrade row needs a header `workflow_version` older than the installed one. A digest change without it is an unmatched cause and stops |
| F2-3 | BC-16: NOT_RUN caused by ORQ-I393 alone is not a failure; decision 4 decides the rest. BC-14: acceptance for design, a merge for plan and implement |
| F2-4 | Sequence 1 redrawn: gate status, presence, validator, then git. The confirmed stale path continues into the questions and the work |
| F2-5 | ADR-001 Consequences list both step-count tests (`test_skills.py:212-221`, `:231-236`) as changing to the new counts, and keep `:202-209` |
| F2-6 | ADR-001 Consequences: no line other than a lookup step names `orqlet resources list` (`test_workflow_lookup_text.py:239-243`) |
| F2-7 | `container.md` says four per skills folder, eight with both |
| F2-8 | BC-31 and the considerations cite `ci.yml:18-107`, including the build job and the Ubuntu, macOS and Windows matrix |
| F2-9 | BC-26 states what the tests pin today and that `test_skills.py:473-480` is extended to the tester and to exactly once |
| F2-10 | BC-38 is narrowed to the workflow skill, reference and role paths; the rule files from `SAMPLE_RULES` are not compared. BC-35 also bounds words: 900 per body and 1,800 for `phase-contract.md`. Today's bodies hold 355 to 712 words |
| Not verified, O-8 | Commit b841ccd exists: "Add the lookup text, the evidence guard, the client limits and the documents (P-8)" (`git show --stat b841ccd`) |

## Round 3: FAIL

Files reviewed, hashed by the author with `shasum -a 256` before the reviewer started and again after it returned; both lists are identical.

| File | sha256 |
|---|---|
| `design/manifest.yaml` | `017a04e2f03af365069119f13ec1be4d353bebab40f77cebae7f52d09659af09` |
| `design/context.md` | `8eb078df676b8829c563094c2a0b1e686df9bc747a7c6adb79a40062e0b88712` |
| `design/container.md` | `5fb05c776abe38a3cf98756c0482a161a03a6bd420dde5a97dce0ef39f3db45f` |
| `design/component.md` | `c603297fdd1ca0c04a4298b7c28a41227e6e53b22f32269405f876f91917bf2c` |
| `design/data-flow.md` | `322e216011039f126b8cba9e3add87515beef72a3df19b70c124c6011f528d18` |
| `design/sequence.md` | `648c3b6d8a9791bdfcf94df312f435d1329a58208568ee4431716d07f16cd85e` |
| `design/considerations.md` | `e0715b8ebd424feebfe6b8e2d9624ef1dd92fb14aa0f887d2f660d63e5c4d2b3` |
| `design/adr-001-one-contract-shape-for-every-skill.md` | `463ca10ed881f3477e0ac52cf6177d651088d818dd34a790423f71dfa5e34959` |
| `design/adr-002-project-context-read-at-execution-time.md` | `21383e7e872f8f34cf0399d3dae3f935d49e4275a8aeb459cefeee6eefd8897b` |
| `design/adr-003-handoffs-and-the-input-check.md` | `2c6a7fa441f2fad01cbc26069b97b0103105dbf61d9c47380e7050fe056ba6ef` |
| `design/adr-004-what-each-phase-produces.md` | `ed68e2bdd0055ee6e58adc916fe1fb0f00216363edf7729f3d67758bb7208053` |
| `design/adr-005-injection-unchanged-tests-and-version.md` | `1bf6b95bc78bccb0f3f6b18a03425a33a4e288b86a306be123f06f32a902ded0` |
| `as-is.md` | `e1c968ac76ab29556a317fc45063c3f4e8849f627b8562b84549cba03189fd0f` |
| `questions.yaml` | `ebb6d3a685c75d3d2d0a7bc7708426b307658ec016268df01a6ff8ef109d92fa` |

### The reviewer's output, unchanged

```yaml
round: 3
verdict: FAIL
round_2_resolution:
  - id: F2-1
    resolved: yes
    note: >-
      ADR-003 decision 4 now orders the checks (adr-003:37-48). Under "Approved", each named merge
      commit must be an ancestor of HEAD, and `git diff --quiet` runs on as-is.md, design/ and
      plan.yaml (adr-003:42-46). That catches an edit to the merged plan.yaml, which gate status
      cannot see (gate_status.py:188-191). ORQ-E353, ORQ-E371 and a superseded answer stop the
      skill with no way to continue in decision 4 (adr-003:47), the failures table
      (component.md:60), BC-39 (component.md:127), considerations.md:26 and sequence 1
      (sequence.md:34-36). Planned work is limited to the exact record folders
      (adr-003:51-56; proposal:1039; evidence_cite.py:27; BC-15, component.md:132). The new
      superseded-answer rule leaves a gap in the design phase: see F3-2.
  - id: F2-2
    resolved: yes
    note: >-
      adr-003:57 and :60, BC-15 (component.md:133) and considerations.md:27 now require a header
      workflow_version older than the installed one. A digest change on its own is an unmatched
      cause and stops. This matches the matrix row (proposal:3081).
  - id: F2-3
    resolved: yes
    note: >-
      BC-16 (component.md:136) limits the exemption to ORQ-I393 behind NOT_RUN and leaves
      everything else to decision 4. BC-14 (component.md:126) says acceptance for design and a
      merge for plan and implement.
  - id: F2-4
    resolved: yes
    note: >-
      Done as asked: the validator now runs before every git command (sequence.md:22-28), and the
      confirmed stale path continues into the questions and the work (sequence.md:43-56). The
      redraw puts presence before the validator, which ADR-003 and BC-14 order the other way:
      see F3-3.
  - id: F2-5
    resolved: yes
    note: >-
      adr-001:35-37 lists test_skills.py:212-221 and :231-236 as taking the new counts, and keeps
      :202-209 (adr-001:40). Checked against test_skills.py:202-236.
  - id: F2-6
    resolved: yes
    note: >-
      adr-001:41 says no line other than a lookup step names `orqlet resources list`, which
      test_workflow_lookup_text.py:239-243 requires. The rule sits under Consequences, not under
      "Constraints for the plan". That is acceptable.
  - id: F2-7
    resolved: yes
    note: container.md:42 now says four per skills folder, eight with both.
  - id: F2-8
    resolved: yes
    note: >-
      BC-31 (component.md:160) and considerations.md:54 cite ci.yml:18-107 and name the build job
      and the ubuntu, macOS and Windows matrix (ci.yml:66-107). manifest.yaml:161 still cites
      ci.yml:30-84: see F3-4.
  - id: F2-9
    resolved: yes
    note: >-
      BC-26 (component.md:153) states what test_skills.py:473-480 pins today (presence only, in
      the four read-only roles) and that the test will be extended.
  - id: F2-10
    resolved: yes
    note: >-
      BC-38 (component.md:172) is narrowed to the workflow skill, reference and role paths, and
      leaves out the SAMPLE_RULES rule files (tests/support/render.py:65-100). BC-35
      (component.md:95) now limits words as well as lines. The word headroom in implement was not
      counted (see not_verified).
findings:
  - id: F3-1
    severity: major
    where: >-
      docs/design/phase-skill-contracts/design/component.md:162-170 (BC-33), :188 (unresolved
      decision); docs/design/phase-skill-contracts/design/manifest.yaml:19-41 (scope), :78
      (security glob), :204-206 (self-check); docs/design/phase-skill-contracts/design/considerations.md:13, :45
    finding: >-
      The last plan phase (Q-7, ADR-005 decision 3) regenerates this repository's files with
      orqlet upgrade, and that changes a file outside the scope that is on a security glob. So
      BC-33 cannot hold. At workflow 0.4.0, the seeded render of .orqlet/versions.yaml changes
      (version, digest, floor). For a seeded file, upgrade does not stop: it writes a proposal
      diff. It will rewrite .orqlet/proposals/.orqlet__versions.yaml.diff, which the previous
      upgrade left committed. That path matches the security glob `.orqlet/proposals/**`
      (manifest.yaml:78) and is not in scope.paths. `gate status --phase` then reports ORQ-E451
      with "A renewed design approval is needed". BC-33 lists proposals among the files that do
      not change and requires no ORQ-E451. The unresolved decision (component.md:188,
      considerations.md:45) only asks whether upgrade stops on a pending diff. The claim that the
      scope holds only the files upgrade writes (considerations.md:13, manifest.yaml:205) leaves
      out proposal files.
    evidence: >-
      src/orqlet/application/usecases/render_all.py:219-228, :275 (versions.yaml is seeded and its
      render carries the workflow version, digest and floor); src/orqlet/domain/classify.py:74-78
      (a seeded file whose new render differs from its record becomes SEEDED_PROPOSAL);
      src/orqlet/domain/changeplan.py:31, :378-391, :430-431 (PROPOSE writes
      .orqlet/proposals/<file>.diff when its text differs); src/orqlet/application/usecases/upgrade.py:140-148
      (only STOP items raise ORQ-W080, so the upgrade completes); .orqlet/generated.lock.yaml:630-633
      (the seeded record of versions.yaml); .orqlet/proposals/.orqlet__versions.yaml.diff:1-22
      (written by the 0.3.1 to 0.3.3 upgrade, C-16); src/orqlet/application/usecases/expected_change.py:85-87
      and src/orqlet/domain/expected_change.py:253-261 (a changed path on a security glob with no
      declared security change is ADDITIONAL); src/orqlet/application/usecases/gate_status.py:232,
      :268-269 (ADDITIONAL means ORQ-E451). Traced through the code, not run.
    required_change: >-
      Name .orqlet/proposals/.orqlet__versions.yaml.diff as an output of the regeneration phase,
      together with .orqlet/versions.yaml if the person applies the proposal. Then choose one of
      two options. (a) Put the file in scope.paths and declare it as an expected change on the
      security surface, so that gate status counts it as implemented, not additional. (b) State
      that the phase leaves the rewritten file uncommitted, and why. Then make BC-33 (its list and
      its ORQ-E451 clause), considerations.md:13 and :45, manifest.yaml:205 and the unresolved
      decision at component.md:188 match what the code shows: upgrade rewrites a pending proposal
      instead of stopping on it.
  - id: F3-2
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:37, :42, :47;
      docs/design/phase-skill-contracts/design/component.md:60, :126-127;
      docs/design/phase-skill-contracts/design/considerations.md:26
    finding: >-
      The stop on a superseded ledger answer also applies to the design phase. There, the
      "approval" is the AS-IS acceptance, and the stated recovery does not exist. Decision 4 runs
      the "Current" check for design too (adr-003:37) and stops on "a ledger answer superseded
      since the approval" (adr-003:47). The failures table names "A new approval pull request; the
      skill never continues" (component.md:60), but an AS-IS file has no approval pull request
      (decision 7). In this task, Q-9 superseded Q-5 during design, after the acceptance. Under
      these rules, every later design session would stop. The text also does not say how "since
      the approval" is established. The superseded question carries no time. The acceptance time
      is the agent's own claim, and this task recorded none. No git comparison is named. An
      answer changed in place, without supersession, is not caught, because questions.yaml is
      not one of the approved files (adr-003:44).
    evidence: >-
      docs/design/phase-skill-contracts/questions.yaml:95-111 (Q-5 superseded, with no answer or
      time) and :180-204 (Q-9, raised in design, supersedes Q-5); manifest.yaml:187 (acceptance
      given when design started, no time recorded); src/orqlet/application/contracts/question_ledger.py:28-32,
      :47-50; docs/design/orqlet-architecture-proposal.md:3074 (changed requirements invalidate
      the design and plan approvals; the AS-IS acceptance has no row); adr-003:49 lists "confirm
      an approval" as a resolution; adr-003:63 describes re-acceptance.
    required_change: >-
      For design, say that an answer superseded since the acceptance means asking for the
      acceptance again under decision 7 (or refreshing the AS-IS file), and fix the recovery in
      the failures table for that case. For plan and implement, say how the check is made, for
      example by comparing docs/design/<task>/questions.yaml at the named merge commit with the
      working tree. That comparison also catches an answer changed in place.
  - id: F3-3
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:38-39;
      docs/design/phase-skill-contracts/design/component.md:126;
      docs/design/phase-skill-contracts/design/sequence.md:18-22, :34-36, :38-44, :75-80
    finding: >-
      ADR-003 decision 4 and BC-14 put the validator first and presence second. Sequence 1 runs
      gate status and the ORQ-I394 presence check before the validator. If the validator runs
      first on a missing artifact, the agent gets a read error instead of the name of the skill
      that produces it, which V-1 expects (adr-005:41). Sequence 1 is also missing three branches:
      a merge commit that is not an ancestor of HEAD; other commits in scope that keep the
      approval valid (adr-003:58); and the standards-hash row (adr-003:59). Sequence 2 leaves out
      the same-project and ancestor checks.
    evidence: adr-003:38-39; component.md:126; sequence.md:18-22, :34-44, :75-80; adr-005:41
    required_change: >-
      Put presence before the validator in decision 4 and BC-14, keeping the validator before
      every git command. Add the missing branches to the sequences, or note that they are left
      out.
  - id: F3-4
    severity: minor
    where: docs/design/phase-skill-contracts/design/manifest.yaml:161
    finding: >-
      The operations evidence reference still cites ci.yml:30-84. BC-31 and considerations.md:54
      now cite ci.yml:18-107. This is left over from F2-8.
    evidence: .github/workflows/ci.yml:18-107 (the lint, types and architecture jobs, the test matrix and the build job)
    required_change: Cite .github/workflows/ci.yml:18-107 in the manifest's operations evidence_refs.
  - id: F3-5
    severity: minor
    where: docs/design/phase-skill-contracts/design/manifest.yaml:179, :185-209
    finding: >-
      This is the last round, and the manifest still has `reviews: []` and no `orqlet validate
      design` entry in its self-check. At D3, the design needs both reviewers' notes, and the
      validator requires reviews at D2 and above. Until both are added, the design set does not
      validate. This finding was deferred as F-14 and is still open.
    evidence: >-
      src/orqlet/workflow/skills/orqlet-design/references/design-format.md:16-17, :66;
      src/orqlet/application/contracts/design_set.py:142; reviews/architecture-reviewer-design.md:117-118
    required_change: >-
      List both reviewer notes under reviews, run `orqlet validate design`, and record the
      result in the self-check before the design pull request is opened.
  - id: F3-6
    severity: minor
    where: docs/design/phase-skill-contracts/design/component.md:102, :159
    finding: >-
      BC-8 requires phase-contract.md to say that every `${{ ... }}` expression becomes a named
      placeholder (component.md:102, from adr-002:28). BC-30 requires that no rendered file
      contains `{{` or `}}` (component.md:159). References are attached as they are, without
      processing, so one of the two tests will fail.
    evidence: >-
      src/orqlet/application/usecases/workflow_sources.py:123-127 (references attached
      unprocessed); a search of src/orqlet/workflow finds `{{` only in the four templates under
      templates/.
    required_change: >-
      Either narrow BC-30 to an unresolved template slot (`{{` followed by a name and `}}`), or let
      BC-8 describe CI expressions without the literal braces.
not_verified:
  - "No sha256 was computed: this is a read-only session with no shell. The manifest's artifact hashes, as_is_ref and the considerations.md hash were not checked."
  - "orqlet validate design, orqlet validate ledger, orqlet gate status and the glob_match check behind the self-check were not run."
  - "F3-1 was traced through render_all.py, classify.py, changeplan.py, upgrade.py, expected_change.py and gate_status.py. orqlet upgrade --dry-run was not run in this repository."
  - "BC-35 word counts were estimated by reading, not counted. Implement holds about 650 to 710 words today, which leaves about 190 words under the 900-word limit for six new sections and the new step content of ADR-004 decision 5."
  - "Whether squash merges on the host keep the Orqlet-Task trailer was not examined. The planned-work row of ADR-003 decision 6 depends on it."
  - "ADR-005's commit facts (b841ccd, 2799dc3) were not checked against git; the author reports checking b841ccd."
  - "The body of proposal section 6.14.1 was not opened. The record folders were checked against proposal:1039 and evidence_cite.py:27."
  - "Client behaviour (U-11) and session checks V-1 to V-3 are outside a document review."
  - "The security reviewer's note and evidence/web/cursor-skills.md are outside this input and were not read."
  - "The round-1 findings are known only from the author's summary."
  - "Feasibility of the four identical phase-contract.md copies, the two-project test and the init-versus-goldens comparison was judged from the cited code and tests only. None of the new texts exists yet."
```

### Author's responses to round 3

| Id | Response |
|---|---|
| F3-1 | Confirmed in the code: a seeded file whose render differs gets its proposal diff rewritten (`src/orqlet/domain/changeplan.py:378-391`), and only conflicts raise ORQ-W080 (`src/orqlet/application/usecases/upgrade.py:140-148`). The proposal diffs are upgrade output, not controls, so `.orqlet/proposals/**` moved from the security globs into the scope. The seeded files (`versions.yaml`, `role-bindings.yaml`) stay on security globs and unchanged in this task. `component.md` Constraints for the plan names both diffs as outputs of the regeneration phase, which commits them without applying them. U-14 and C-16 are answered there, traced and not run. BC-33, `considerations.md` and the manifest self-check match. The overlap check was run again: no scope path and none of the 417 tracked files in scope matches a security glob |
| F3-2 | ADR-003 decision 4, *Current*. For plan and implement, the agent shows `git diff <merge> -- questions.yaml` against the design merge. An answer that changed, or a question superseded, since then stops for a new approval; new questions and answers to questions open at the merge do not count. For design, a superseded or changed answer that the AS-IS file cites leads to a new acceptance of the AS-IS file or a refresh. A separate failures row covers that case |
| F3-3 | The order is now present, validator, then every git command (ADR-003 decision 4, BC-14). `sequence.md` lists the branches the diagrams leave out |
| F3-4 | The manifest cites `.github/workflows/ci.yml:18-107` |
| F3-5 | Both notes are listed under `reviews`, and the self-check records the rounds and the validator result |
| F3-6 | BC-8 and ADR-002 decision 3: `phase-contract.md` describes expanded expressions in words, without literal double braces, so BC-30 stays as it is |

## Round 4: FAIL

Files reviewed, hashed by the author with `shasum -a 256` before the reviewer started and again after it returned; both lists are identical.

| File | sha256 |
|---|---|
| `design/adr-001-one-contract-shape-for-every-skill.md` | `463ca10ed881f3477e0ac52cf6177d651088d818dd34a790423f71dfa5e34959` |
| `design/adr-002-project-context-read-at-execution-time.md` | `8b25e824ee5c807d8ae9e0df0f531df68a72a162575da045e1bdecdc8c81e370` |
| `design/adr-003-handoffs-and-the-input-check.md` | `e6b6d8968578196b8a0b044a7212559866e035db6cbdc51c54056f7cd30e94a7` |
| `design/adr-004-what-each-phase-produces.md` | `c4abffa747f6ff9681d56e6ed9411870b2a5f9e6b28c9e65ce3190bef729081a` |
| `design/adr-005-injection-unchanged-tests-and-version.md` | `ab6fbf67e835b0a2f36178750198f70fd5ca24e9969d86ae1350c7d9fbe3a2cb` |
| `design/component.md` | `40b05c15fbcc8f19efc748f6cfa735be4648417e7055dd0a45a8cee8d66fd9b8` |
| `design/considerations.md` | `c7e0e206804aa4f132e80f2996f9fb3be75e34d6338eb1e1d4f02eab1b36c261` |
| `design/container.md` | `5fb05c776abe38a3cf98756c0482a161a03a6bd420dde5a97dce0ef39f3db45f` |
| `design/context.md` | `8eb078df676b8829c563094c2a0b1e686df9bc747a7c6adb79a40062e0b88712` |
| `design/data-flow.md` | `322e216011039f126b8cba9e3add87515beef72a3df19b70c124c6011f528d18` |
| `design/sequence.md` | `693e7b3ddafbb3c4da35f986024fda4640147fda3fc7fa863535ffea18a3ed24` |
| `design/manifest.yaml` | `dea90dd8ce26be3f5a4c40539be9d060ca5d91c393fdc7b206217abefb208941` |
| `as-is.md` | `e1c968ac76ab29556a317fc45063c3f4e8849f627b8562b84549cba03189fd0f` |
| `questions.yaml` | `ebb6d3a685c75d3d2d0a7bc7708426b307658ec016268df01a6ff8ef109d92fa` |

### The reviewer's output, unchanged

```yaml
round: 4
verdict: FAIL
round_3_resolution:
  - id: F3-1
    resolved: "yes"
    note: >-
      `.orqlet/proposals/**` is now in scope (manifest.yaml:41) and no longer a security glob
      (manifest.yaml:55-85). BC-33 (component.md:168), the plan constraint (component.md:200),
      considerations.md:13 and :45, ADR-005 decision 3 (adr-005:38) and the self-check
      (manifest.yaml:208-210) all say the same thing. I checked this against the code. Gate status
      computes ORQ-E451 only from changed paths that match the security globs
      (expected_change.py:79-87, gate_status.py:232, :268-269). Only changeplan.py writes under
      `.orqlet/proposals/`, and nothing reads those files (changeplan.py:31, :155-161, :381;
      render_all.py:362). A SEEDED_PROPOSAL keeps the old lock record, and the diff is written only
      when its text differs (changeplan.py:385-386, :396-406), so a second upgrade plans no writes
      (BC-32). When versions.yaml is left at 0.3.3, doctor raises neither ORQ-W166 nor ORQ-E163
      (diagnose.py:373-394). The overclaim about U-14 is F4-6.
  - id: F3-2
    resolved: partly
    note: >-
      Plan and implement now compare `questions.yaml` against the design merge (adr-003:50). Design
      has its own failures row (component.md:61). Two gaps remain. For implement, nothing compares
      against the plan merge (F4-1). For design, the check has no reference point, so re-accepting
      the AS-IS file does not clear it (F4-2).
  - id: F3-3
    resolved: "yes"
    note: >-
      The order is now present, validator, then every git command, in adr-003:38-41, BC-14
      (component.md:127) and sequence 1 (sequence.md:25-35). The branches the diagrams leave out
      are listed (sequence.md:3-10). One leftover contradiction about sequence 2 is in F4-3.
  - id: F3-4
    resolved: "yes"
    note: "manifest.yaml:161 cites .github/workflows/ci.yml:18-107, as BC-31 and considerations.md:54 do."
  - id: F3-5
    resolved: "yes"
    note: >-
      Both reviewer notes are listed under reviews (manifest.yaml:179-183). The self-check records
      `orqlet validate design` as PASS at D3 (manifest.yaml:214-216). The round-4 entry records a
      result before the round has one (F4-5).
  - id: F3-6
    resolved: "yes"
    note: >-
      BC-8 (component.md:103) and ADR-002 decision 3 (adr-002:28) say that phase-contract.md
      describes expanded expressions in words, without literal double braces. BC-30
      (component.md:161) stays as it is, and the two no longer conflict.
findings:
  - id: F4-1
    severity: major
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:50;
      component.md:60, :128 (BC-39); considerations.md:26; manifest.yaml:148
    finding: >-
      For implement, the ledger check compares `questions.yaml` with the design merge only.
      Questions that were open at that commit are excluded explicitly, and so are questions raised
      after it. Answers given during the plan phase and approved with the plan merge are therefore
      not checked. If one of them changes, is superseded or is withdrawn after the plan merge,
      implement continues. A changed conflict ruling is not counted either. Nothing else catches
      these cases. Gate status scopes the plan by its operation paths only, and decision 6 hands
      every commit that touches `questions.yaml` back to decision 4. Example: Q-7 blocks only plan
      and decides whether this repository is regenerated. Had it been answered during planning, a
      later change to it would not stop implement. Round 3 said "since the approval", and round 4
      narrowed that to "since the design merge", which opened this gap.
    evidence: >-
      docs/design/orqlet-architecture-proposal.md:3055 (the matrix exists to stop "changed
      requirements slipping through under an old approval"), :3074 (changed requirements: plan
      approval Invalid), :3088 (a changed ledger is a staleness event); adr-003:50 ("against the
      design merge", "answers to questions that were open at the merge, do not count"); adr-003:60;
      gate_status.py:188-191; questions.yaml:137-155 (Q-7 blocks plan); adr-003:71 ("Nothing is
      relaxed"); adr-005:35 ("No W element is relaxed")
    required_change: >-
      For implement, also show `git diff <plan merge> -- docs/design/<task>/questions.yaml`.
      Stop for a new plan approval when any of these changed since that commit: an answer present
      there, an answer now superseded or withdrawn, or a conflict ruling. Keep the exemption only
      for questions that were open at the plan merge, and for new ones. Make adr-003:50, the
      failures row at component.md:60, BC-39, considerations.md:26 and the manifest's security
      notes say the same, and add the case to the branches listed for sequence 2 (sequence.md:3-10).
  - id: F4-2
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:50, :67;
      component.md:61, :128 (BC-39)
    finding: >-
      In design, the check stops when a question the AS-IS file cites "is now superseded". It names
      no reference point, so re-accepting the file does not clear it. Re-acceptance adds a
      self-check entry but leaves the citation in place, so the next session stops again, and only
      a refresh ends the loop. This task is in that state: the AS-IS file cites Q-5, which Q-9 has
      superseded, and the design deliberately leaves the AS-IS file unchanged. "The answer the
      AS-IS file records" exists only as prose, and no git comparison is named for design, unlike
      plan and implement. BC-39 also names only a new acceptance, while ADR-003 and the failures
      row offer a refresh as well.
    evidence: >-
      as-is.md:1228 (U-7 question_ref Q-5), :1487 (confirmed_requirements Q-5);
      questions.yaml:111, :203-204; manifest.yaml:191 ("The AS-IS file is not changed by this
      design"); src/orqlet/application/contracts/as_is.py:45-50 (an unknown holds only a
      question_ref, no answer)
    required_change: >-
      For design, make the reference point the commit that recorded the latest acceptance (from
      `git log` on as-is.md), and compare `questions.yaml` at that commit with the working tree,
      using the same rules as plan and implement. A new acceptance then moves the reference point
      and ends the loop. Add "or a refresh" to BC-39.
  - id: F4-3
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:39;
      component.md:39, :54-70; sequence.md:10, :82
    finding: >-
      The Validator check has no stated outcome. It does not say that a validator error which no
      later check classifies (a schema or parse error, an artifact hash mismatch) stops the skill.
      The Behaviour list names six checks and leaves out the validator, and the failures table has
      no row for such an error. sequence.md:10 says that sequence 2 leaves out the validator, but
      sequence.md:82 shows "then the validators".
    evidence: adr-003:39, :53; component.md:39; sequence.md:10, :82
    required_change: >-
      State that any other validator error stops the skill and names the finding. Add the validator
      to the Behaviour list and a matching failures row. Correct sequence.md:10.
  - id: F4-4
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:52
    finding: >-
      The Questions check requires that "no material unknown of the input is unanswered". An
      unknown without a question_ref has no answer to check. Read literally, the rule stops design
      on every such unknown. This AS-IS file has ten of them, and the design itself answers several
      (U-2 by the matrix, U-14 by a code trace). The contract and the validator only count material
      unknowns and block nothing.
    evidence: >-
      as-is.md:1169-1302 (U-1 to U-6 and U-11 to U-14 are material, without question_ref);
      src/orqlet/application/usecases/validate_as_is.py:65; adr-003:66; component.md:200
    required_change: >-
      Define "unanswered": a material unknown whose question_ref is open and blocks this phase.
      Say that design addresses the other material unknowns with evidence, or lists them as
      unresolved decisions with a ledger question.
  - id: F4-5
    severity: minor
    where: docs/design/phase-skill-contracts/design/manifest.yaml:217-219
    finding: >-
      The independent-review self-check entry has result "pass", but the round-4 review had no
      result when it was written ("round 4 on the revised files").
    evidence: AGENTS.md baseline, "A check that did not run is reported as not run, never as passed."
    required_change: >-
      Record the round-4 outcome of both reviewers, or mark the entry as pending, before the design
      pull request is opened.
  - id: F4-6
    severity: minor
    where: docs/design/phase-skill-contracts/design/component.md:200; considerations.md:45
    finding: >-
      The plan constraint says the trace "answers U-14 and C-16". U-14 asks four things: the lock
      entry of a shared file with broken markers (C-15), whether any command removes a diff after a
      manual merge, an upgrade with only a different CLI version, and why the role-bindings diff is
      empty. The trace answers at most the diff-file part.
    evidence: as-is.md:1297-1301; changeplan.py:378-391
    required_change: Say that the trace answers C-16 and the diff-file part of U-14, and that the rest of U-14 stays open.
not_verified:
  - "No sha256 was computed: the shell was refused in this Ask-mode session. The artifact hashes, as_is_ref and the considerations.md hash in the manifest were not checked."
  - "orqlet validate design, orqlet validate ledger, orqlet gate status and the glob_match overlap check were not run; the author reports PASS."
  - "F3-1 was traced through render_all.py, classify.py, changeplan.py, upgrade.py, expected_change.py, gate_status.py and diagnose.py. orqlet upgrade --dry-run at 0.4.0 was not run, and whether the role-bindings diff changes was not determined (the reader did not show that file's content)."
  - "ADR-005's commit facts (b841ccd, 2799dc3) were not checked against git."
  - "Whether squash or rebase merges on the host keep the Orqlet-Task trailer, and give a commit that changed every approved file, was not examined."
  - "The body of proposal section 6.14.1 was not opened."
  - "BC-35 word headroom was not counted; none of the new texts exists yet."
  - "Client behaviour (U-11) and session checks V-1 to V-3 are outside a document review."
  - "The security reviewer's note, evidence/web/cursor-skills.md and the fragments/ folder are outside this input and were not read."
  - "Round 1 is known only from the author's summary."
  - "This review is an additional check, not a guarantee."
```

### Author's responses to round 4

| Id | Response |
|---|---|
| F4-1 | ADR-003 decision 4, *Current*: the ledger rule now names a reference commit per phase. Plan uses the design merge. Implement uses both the design merge and the plan merge, so an answer given during planning and approved with the plan is bound too. The rule fails closed: any change to any field of a question answered at a reference commit, its removal, or any change to the conflicts list or a ruling stops the skill for a new approval (taken together with SEC4-4). The failures table now has a separate ledger row, and BC-39, the `considerations.md` row and the manifest's security notes say the same. Sequence 2 shows `git diff m1 -- questions.yaml` and `git diff m2 -- questions.yaml`, and the intro lists the ledger branches it leaves out |
| F4-2 | For design, the reference commit is the latest commit of the AS-IS file that holds its acceptance. If the acceptance is not committed, the skill asks the person to commit it first. The same fail-closed rule applies, and a new acceptance moves the reference commit, which ends the loop. BC-39 and the failures row offer a new acceptance or a refresh. ADR-003 consequences say that the AS-IS acceptance must be committed before design |
| F4-3 | ADR-003 decision 4, *Validator*: a validator error that no later check names stops the skill and names the finding. The Behaviour list names the validator, and a failures row was added. `sequence.md` no longer says that sequence 2 leaves out the validator |
| F4-4 | ADR-003 decision 4, *Questions*: a material unknown counts as unanswered only when its `question_ref` names a question that is open and blocks this phase. Design addresses every other material unknown with evidence, or lists it as an unresolved decision with a ledger question. BC-14 says the same |
| F4-5 | The manifest's review self-check entry now records round 4 (architecture FAIL with F4-1 major, security PASS). Its result is `fail` until a review of the files as revised after round 4 has a result |
| F4-6 | `component.md` Constraints for the plan and `considerations.md`: the trace answers C-16 and the diff-file part of U-14. The rest of U-14 stays open: the lock entry of a shared file with broken markers, whether a command removes a diff after a manual merge, an upgrade with only a different CLI version, and why the role-bindings diff is empty |

## Round 5: PASS

Files reviewed, hashed by the author with `shasum -a 256` before the reviewer started and again after it returned; both lists are identical.

| File | sha256 |
|---|---|
| `design/adr-001-one-contract-shape-for-every-skill.md` | `463ca10ed881f3477e0ac52cf6177d651088d818dd34a790423f71dfa5e34959` |
| `design/adr-002-project-context-read-at-execution-time.md` | `215d11da36c8f7f3ea79ceb33a8bb6bd883bfda4c16dbaf9b020a8aacefa41fb` |
| `design/adr-003-handoffs-and-the-input-check.md` | `11add91bf06ab5a994e38ff07adc74a8c5333e6b71a92875a40a33b09706e665` |
| `design/adr-004-what-each-phase-produces.md` | `e0210f380060e844a27ebb6ce7834642cb0a0c59bfd664fa0ad804891b4661e7` |
| `design/adr-005-injection-unchanged-tests-and-version.md` | `ab6fbf67e835b0a2f36178750198f70fd5ca24e9969d86ae1350c7d9fbe3a2cb` |
| `design/component.md` | `db23fcdc4c36016dafc810496908306d4c1b46306a20f245bc3287ed7d75cc27` |
| `design/considerations.md` | `f2939364e05942d7fb14fba5db9635a6b0eb7b37300311a348d89380cbaa0220` |
| `design/container.md` | `5fb05c776abe38a3cf98756c0482a161a03a6bd420dde5a97dce0ef39f3db45f` |
| `design/context.md` | `8eb078df676b8829c563094c2a0b1e686df9bc747a7c6adb79a40062e0b88712` |
| `design/data-flow.md` | `322e216011039f126b8cba9e3add87515beef72a3df19b70c124c6011f528d18` |
| `design/sequence.md` | `9886266e62cecb1451b3ec6c67d597c02945fbdb8ccec0c556617db8ec039396` |
| `design/manifest.yaml` | `d9a7d966c80ec088cf36d2934171e9bc13331b06fd683a1bbea97b7f47b7fc00` |
| `as-is.md` | `e1c968ac76ab29556a317fc45063c3f4e8849f627b8562b84549cba03189fd0f` |
| `questions.yaml` | `ebb6d3a685c75d3d2d0a7bc7708426b307658ec016268df01a6ff8ef109d92fa` |

### The reviewer's output, unchanged

```yaml
round: 5
verdict: PASS
round_4_resolution:
  - id: F4-1
    resolved: "yes"
    note: >-
      Implement now compares questions.yaml with both the design merge and the plan merge (adr-003:52-55).
      The rule fails closed. It stops on any change to any field of a question that was answered at a
      reference commit, on the removal of such a question, and on any change to the conflicts list or a
      ruling. Only new questions, and the answer and status of a question that was open at the reference,
      are exempt (adr-003:57-61). An answer given during planning is therefore bound by the plan merge.
      The same rule appears in the failures row (component.md:63), BC-39 (component.md:138),
      considerations.md:29, the manifest's security notes (manifest.yaml:149), sequence 2
      (sequence.md:88) and the intro of sequence.md (sequence.md:8).
  - id: F4-2
    resolved: "yes"
    note: >-
      Design now has a reference commit, the commit of the AS-IS file that holds its acceptance
      (adr-003:53). The same fail-closed rule applies. A new acceptance moves the reference, which ends
      the loop (adr-003:61). BC-39 (component.md:138) and the failures row (component.md:64) now offer a
      new acceptance or a refresh. The consequences say the acceptance must be committed before design
      starts (adr-003:83). The definition of the reference still differs between files: see F5-1.
  - id: F4-3
    resolved: "yes"
    note: >-
      A validator error that no later check names now stops the skill and names the finding
      (adr-003:41). The Behaviour list names the validator (component.md:39), and a failures row was
      added (component.md:57). The intro of sequence.md lists the other validator errors among the
      branches it leaves out (sequence.md:4) and no longer says that sequence 2 leaves out the validator
      (sequence.md:13, :85).
  - id: F4-4
    resolved: "yes"
    note: >-
      "Unanswered" is now defined: a question_ref that names a question that is open and blocks this
      phase. Design addresses every other material unknown with evidence, or lists it as an unresolved
      decision with a ledger question (adr-003:63; BC-14, component.md:135). This design does not apply
      the rule to itself: see F5-4.
  - id: F4-5
    resolved: "yes"
    note: >-
      The review self-check entry records round 4 for both reviewers. It says that no review has run on
      the files as revised after round 4, and its result is fail (manifest.yaml:218-220).
  - id: F4-6
    resolved: "yes"
    note: >-
      The plan constraint and considerations.md now say the trace answers C-16 and only the diff-file
      part of U-14. They list the other three parts as open (component.md:213; considerations.md:48).
      This matches as-is.md:1297-1301.
findings:
  - id: F5-1
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:53, :45;
      component.md:64, :138 (BC-39)
    finding: >-
      The reference commit for the ledger check in design is defined two ways. ADR-003 says "the latest
      commit of the AS-IS file that holds its acceptance". The failures row and BC-39 say "the commit that
      recorded the AS-IS acceptance". Under ADR-003's wording, a later commit can touch as-is.md, keep the
      acceptance and move the reference without any new acceptance. Ledger changes made in that commit are
      then never compared. No command is named for finding the commit, and no exit status is stated for
      it. Nothing says how the agent decides that the acceptance "is not committed". For plan and
      implement the agent never chooses a commit (adr-003:45). Here the agent derives the commit itself,
      and the text does not say so or require showing the commit to the person.
    evidence: >-
      adr-003:53 ("the latest commit of the AS-IS file that holds its acceptance"); component.md:64 and
      :138 ("the commit that recorded the AS-IS acceptance"); adr-003:45 ("The agent never chooses a
      commit"); adr-003:78 (decision 7: an edited accepted file goes back to draft, which a later commit
      can ignore)
    required_change: >-
      Use one definition in ADR-003, BC-39 and the failures row, for example the commit that recorded the
      latest acceptance entry. Name the command that finds it, such as `git log -1 --format=%H --
      'docs/design/<task>/as-is.md'`. Accept the commit only if it holds the acceptance entry, `git diff
      --quiet <commit> -- <as-is.md>` exits 0 and no file is untracked. Otherwise the acceptance counts as
      not committed. Say that the agent derives this commit and shows it to the person.
  - id: F5-2
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:39, :43;
      component.md:58, :60
    finding: >-
      The exit-status rule makes any result of `git merge-base --is-ancestor` other than 0 or 1 a "check
      not run". The recovery for that is "fix the cause, such as a missing ref, and run again". The
      Same-project check and its failures row treat a base revision that is not in this repository as "the
      artifact comes from elsewhere: stop and ask", with a different recovery. The usual case of an
      artifact from another repository is a base object that does not exist locally, and git reports that
      as an error, not as exit 1. So the two rules classify the same situation differently. ADR-003 also
      does not say that gate status's "is not in this repository" line, which identifies this case, is
      read before the git command.
    evidence: >-
      adr-003:39 (any other result is "check not run"); adr-003:43 (exit 0 and no skip line, otherwise
      "another repository ... stop and ask"); component.md:58 versus :60 (different recoveries);
      src/orqlet/application/usecases/gate_status.py:219-220 (the skip line for an absent base);
      src/orqlet/adapters/git/vcs_git.py:139 (the code base accepts only 0 and 1 from merge-base)
    required_change: >-
      State that the Same-project check reads the gate-status skip line first, or confirms that the base
      object exists (`git rev-parse --verify '<base>^{commit}'`). State that an absent base gives the
      "another repository" outcome, not "check not run", and align the two failures rows.
  - id: F5-3
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:44, :54;
      component.md:61, :131-137 (BC-14)
    finding: >-
      For plan, the Approved check needs the design's merge commit, and the ledger rule uses that merge as
      its reference. ADR-003 also keeps the D1 path, in which the plan is drafted from the validated
      design draft and approved in the same pull request. At plan time in that path, no merge exists, so
      neither check has its commit. The failures row offers "confirms the D1 exception" as a recovery, but
      no decision says what that exception checks instead, or which reference the ledger rule uses until
      the shared merge exists.
    evidence: >-
      adr-003:44 ("A D1 plan may share the design's pull request"); adr-003:54 (plan's reference: the
      design merge); component.md:61 ("confirms the D1 exception");
      docs/design/orqlet-architecture-proposal.md:2859 (D1: plan drafted from the validated design draft,
      one pull request); src/orqlet/workflow/skills/orqlet-plan/skill.md:11 (today's D1 path)
    required_change: >-
      State the D1 path for plan in ADR-003 decision 4 and BC-14. Say what replaces the merge check, for
      example `validate design` passing with effective class D1 plus the person's confirmation. Say which
      reference the ledger rule uses, for example the commit that holds the AS-IS acceptance. Note that
      implement then checks against the single shared merge.
  - id: F5-4
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:32, :63;
      component.md:199-203, :213; docs/design/phase-skill-contracts/questions.yaml
    finding: >-
      ADR-003 decision 2 says a design's open questions are "the brief's unresolved decisions, each a
      ledger question". The rule added for F4-4 says design lists every material unknown it does not
      answer "as an unresolved decision with a ledger question". This design does not follow either rule.
      Its brief lists three unresolved decisions: two projects sharing a uuid (from U-3), how Codex starts
      a skill (U-11) and controls_level. It also leaves three parts of U-14 open in the Constraints for the plan. None of these has a ledger question; the ledger holds only Q-1 to Q-9. U-11 and U-14 are
      material and have no question_ref.
    evidence: >-
      adr-003:32 (Design row of the handoff table); adr-003:63; component.md:199-203 (Unresolved
      decisions), :213 ("The rest of U-14 stays open"); as-is.md:1264-1270 (U-11) and :1297-1302 (U-14),
      both material with no question_ref; questions.yaml:4-204 (Q-1 to Q-9 only)
    required_change: >-
      Add non-blocking ledger questions for these items. Alternatively, record in the self-check that the
      shape of ADR-003 decisions 2 and 4 applies from workflow 0.4.0, and that this design, written under
      0.3.3, lists them without ledger questions.
  - id: F5-5
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/considerations.md:29;
      adr-003-handoffs-and-the-input-check.md:45, :47, :52, :65
    finding: >-
      The input check has the agent run porcelain `git diff` against the working tree and `git log` with
      `%G?`. This code base's hardened git wrapper keeps exactly these reads off its allow list. It
      documents that they run programs from git configuration: clean filters on modified files, the
      fsmonitor hook, and the signature program behind `%G?`. The residual in considerations.md names
      only settings that hide changes (assume-unchanged, skip-worktree, clean filters). It does not
      record that these commands can start configured programs with the person's rights. Today's skills
      already run `git status`, so this kind of exposure is not new, but the design adds several such
      commands to every phase.
    evidence: >-
      src/orqlet/adapters/git/git_runner.py:1-6 ("Anything that executes configured programs on a read
      (status, porcelain diff ...) is not on the list"), :34-43, :50 (core.fsmonitor=false,
      core.hooksPath= overrides); considerations.md:29 (What remains);
      src/orqlet/workflow/skills/orqlet-research/skill.md:11 and orqlet-implement/skill.md:12 (`git
      status` today)
    required_change: >-
      Record this residual in considerations.md. Alternatively, give the documented commands the same
      overrides the code base uses (`-c core.fsmonitor=false -c core.hooksPath=`) and say what is left
      unhardened.
  - id: F5-6
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-004-what-each-phase-produces.md:52-57;
      component.md:164 (BC-25)
    finding: >-
      The design-review input is fixed at five items: the design folder, the AS-IS file, the ledger, the
      design format reference and the standards output. BC-25 requires the design skill to give the same
      inputs in every round. But the process the design describes has rounds, saves the reviewer's output
      with the author's responses in a separate section, and starts a new round when a hash differs. A
      reviewer in a later round needs its earlier output and the author's responses to judge whether its
      findings were resolved, as this round does. Under BC-25 the note is not an input.
    evidence: >-
      adr-004:52 (the five inputs), :53-57 (rounds, saved output and responses, a new round on a hash
      difference); component.md:164; manifest.yaml:180-184 (the notes the manifest lists)
    required_change: >-
      For a later round, add the review note (the reviewer's earlier output and the author's responses) to
      the inputs in ADR-004 decision 7, BC-25 and the reviewer prompt sentence.
  - id: F5-7
    severity: minor
    where: >-
      docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:64;
      sequence.md:13, :45-46, :88; component.md:63
    finding: >-
      Three wording leftovers after the round-4 edits. (a) ADR-003 decision 5 lists the resolutions as
      "run an earlier skill again, answer a question, confirm an approval, or get an AS-IS refresh or an
      impact review". It omits a new approval pull request, committing or giving again the AS-IS
      acceptance, and fixing the cause of a check not run, all of which decision 4 and the failures table
      name. (b) In sequence 1, the stop message for a ledger change says "an approved file was edited",
      while the failures row says the skill names the question or ruling, and questions.yaml is not an
      approved file. (c) Sequence 2 leaves out the untracked-file check, but its intro lists only the
      same-project and ancestor checks as left out.
    evidence: >-
      adr-003:64; adr-003:47, :61; component.md:62-64; sequence.md:45-46; sequence.md:13 and :88
    required_change: >-
      Add the missing resolutions to decision 5. Give the ledger branch in sequence 1 its own message that
      names the question or ruling. List the untracked-file check among the branches that sequence 2 leaves
      out.
not_verified:
  - "No sha256 was computed: the shell was refused in this Ask-mode session. The artifact hashes, as_is_ref and the considerations.md hash in the manifest were not checked."
  - "orqlet validate design, orqlet validate ledger, orqlet gate status and the glob_match overlap check were not run; the author reports PASS."
  - "No git command was run. Not checked: git's exit status when the object passed to merge-base --is-ancestor is absent (F5-2), and whether git writes to the error output during normal operation (line-ending warnings, gpg messages for %G?). The 'nothing on the error output' rule would turn such output into 'check not run'."
  - "That 0.4.0 changes no seeded render other than versions.yaml was traced only in render_all.py:214-277 (role bindings come from constants, profile and resources from their files). orqlet upgrade --dry-run was not run."
  - "The git status snapshot for this session lists as-is.md as untracked. Whether this task's AS-IS acceptance is committed was not checked. The new rule binds 0.4.0 runs, so this was not judged a defect."
  - "Checks on a ref name the person supplies (for example one that starts with a hyphen) were not judged; that is the security reviewer's field."
  - "Whether squash or rebase merges on the host keep the Orqlet-Task trailer, and leave a commit that changed every approved file, was not examined."
  - "ADR-005's commit facts (b841ccd, 2799dc3) were not checked against git."
  - "The body of proposal section 6.14.1 was not opened."
  - "BC-35 word headroom was not counted; none of the new texts exists yet."
  - "Client behaviour (U-11) and session checks V-1 to V-3 are outside a document review."
  - "The security reviewer's note, evidence/web/cursor-skills.md and the fragments/ folder are outside this input and were not read."
  - "Round 1 is known only from the author's summary."
  - "This review is an additional check, not a guarantee."
```

### Author's responses to round 5

The person chose to stop after round 5 and to give the design pull request a consolidated report. The design files keep the bytes this round reviewed. Only the manifest's self-check changed afterwards, to record this round. F5-1 to F5-7 are minor and open. They are not applied here, and the design pull request's review decides on them.
