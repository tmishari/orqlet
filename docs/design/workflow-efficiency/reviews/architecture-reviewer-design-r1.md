# Architecture review of the design, round 1

- Role: orqlet-arch-reviewer, started as a typed Cursor subagent in a clean context (agent 603b1fd2-24ed-448b-a34e-d58c1063e7f2).
- Inputs given: the design folder, `as-is.md`, `questions.yaml`, `.agents/skills/orqlet-design/references/design-format.md` and the saved output of `orqlet standards for`; nothing else.
- Model requested: none named, so the subagent inherits the parent session's model. Model observed: unknown; the client reports no identity to the agent.
- Context freshness: fresh; the subagent received only the prompt above.
- Hashes when the reviewer started and when this note was saved (unchanged between the two):
  - manifest.yaml 98fe920b940fd4c4260888ba7e0aeff81fbdbc3bfccb2eb856be2fb8db5c4668
  - component.md a059ab4559a10bd7246db2b1ace265475edd511724dbc22479d6f46d7846382b
  - views.md 463adab960927297068d0834a129693abe58bb7bd670b83883ac4e676bb51082
  - adr-001 1f805cb9419b1ba023e3f55e620c9177e1622aa44b3bc35f6a27437b2bcc7e73
  - adr-002 59f3d63907314beb66a6a84b4b57ced377f54c445fbe58857d1333b810e74b25
  - adr-003 014a67a5f7aca4253829459012fa6934be77f5c575526389ce690d4d0711b58f
  - adr-004 2927b41c7f3d86ce0c0ae1b68530e0fc994a993b89a3ef28c00159254a33221f
- These hashes differ from the final manifest's, because the design changed to answer this round; round 2 reviews the changed design.

## Reviewer output (unchanged)

# Architecture review of the workflow-efficiency design, round 1

I found **three blocking findings and nine non-blocking ones**. The blocking ones are:

- **Manifest rebuild timing:** the design waits until the final implementation commit to rebuild `MANIFEST.json`, but a test fails in any earlier phase that edits the workflow package.
- **Missing phase contract:** shared text moves into `phase-contract.md`, but the review and onboard skills don't have a copy of that file.
- **No owner for the next step:** nothing says which part of the system writes the "Action needed:" line.

The design meets the design-format structure: D3 class, a context view, four ADRs with all four sections, the nine brief parts in order, and no phase order.

## Blocking findings

```yaml
- schema: orqlet.finding/v1
  id: AR-1
  claim: >
    The constraint "synchronisation (README, generated copies, version, manifest rebuild) is in
    the final implementation commit" conflicts with deterministic tests. Any earlier phase that
    edits src/orqlet/workflow/** without rebuilding MANIFEST.json fails pytest. The brief's
    section 5 says such a failure (not from the two frozen files) stops the phase. So either
    every workflow-text change must land in the final phase, or every earlier phase fails.
  evidence:
    - component.md:110 (section 9), component.md:64 (section 5); manifest.yaml:122 (operations note)
    - tests/unit/test_manifest.py:43 asserts MANIFEST.json == render()
    - tests/unit/test_workflow_lookup_text.py:507-509 (same check, cites ORQLET-DET-002)
  confidence: high
  blocking: yes
  resolves_by: >
    Rebuild MANIFEST.json (and regenerate the golden files that read the workflow source) in
    every phase that changes the workflow package. Keep the version bump, orqlet upgrade and
    README in the final commit. Or state that all workflow text goes in one final phase.
    Whether the golden files read the workflow source was not checked.

- schema: orqlet.finding/v1
  id: AR-2
  claim: >
    The design states shared text once in the phase contract, including "the model-suggestion
    step", and says the "six phase skills cite the contract". Only four skills hold
    phase-contract.md. orqlet-review and orqlet-onboard don't, yet both carry the models-resolve
    step and the "Source material" paragraph. This repeats the A-9 defect (a reference the
    skill's folder lacks) that BC-16 fixes. Fixing it either adds copies, which works against
    "skills shrink", or keeps the step in those two skills, which contradicts "stated once".
    The design doesn't choose.
  evidence:
    - adr-004 decision 4; component.md:33-35 (diagram "Six phase skills: cite the contract"); manifest EC-6
    - src/orqlet/workflow/MANIFEST.json:233-286 (phase-contract.md under design, implement, plan, research only)
    - grep "models resolve|Source material is not authority": review skill.md 3 hits, onboard skill.md 2
    - as-is A-4, A-5, A-9
  confidence: high
  blocking: yes

- schema: orqlet.finding/v1
  id: AR-3
  claim: >
    "Action needed:" followed by "the next step", for every validator and gate status, has no
    owner and no source. The envelope has no next-action field (A-41), and ADR-002 rejects
    adding one. The brief says "the CLI only parses and renders; rules sit in the use cases".
    The design doesn't say whether the next step is a generic line, a mapping per finding code
    (about 256 codes, U-10) or data from the use case. It doesn't say which layer holds it, or
    what one line says when there are several findings. BC-9 can't be tested as written.
  evidence:
    - adr-002 decisions 2 and 6 and rejected alternative 3; component.md:22, 55; EC-3
    - as-is A-41 (cli_result.py:12-26), U-10
  confidence: medium-high
  blocking: yes
```

## Non-blocking findings

```yaml
- id: AR-4
  claim: >
    The reuse check runs `git diff --quiet HEAD -- <cited files>`. That was enough while every
    check re-cited at HEAD first (phase-contract.md:29). With citation once per phase, a commit
    inside the phase that changes a cited file passes the check while the citation is stale.
    Comparing against the citation's revision, or re-hashing the cited lines, would close this.
  evidence: [adr-001 decision 1, BC-1, views.md data flow, phase-contract.md:29]
  confidence: medium (the inputs don't establish whether commits happen inside a phase)
  blocking: no

- id: AR-5
  claim: >
    ADR-003's "reads that file from the current tree" is ambiguous. If it means the working
    tree, uncommitted task evidence would validate. Today the validator reads at a revision.
    "Own task folder" doesn't say whether it means header.task or the file's location, nor that
    the path is matched after canonicalisation. The security reviewer should also look at the
    containment.
  evidence: [adr-003 decision 2, EC-5, validate_as_is.py:117-134]
  confidence: medium
  blocking: no

- id: AR-6
  claim: >
    After `orqlet upgrade` in the final commit, this task's own as-is, design and plan show
    stale workflow_version and protected_set_digest. That produces ORQ-W390 plus a skip, so
    NOT_RUN and exit 5 (EC-1), and the contract stops for the person. The upgrade row keeps
    approval valid only for a newer workflow_version. If standards.lock.yaml changes (EC-8
    allows it), the row needs an impact review instead. The compatibility note covers only the
    frozen tasks.
  evidence: [gate_status.py:179-184, 194-202; phase-contract.md:58-64; manifest EC-8, compatibility note]
  confidence: medium
  blocking: no

- id: AR-7
  claim: >
    The word budget may not be feasible, and the design contradicts itself. phase-contract.md
    has 1,799 words against a test cap of 1,800 (A-2, A-8). It must take the model step, the
    reuse rule and the web-evidence format without growing. ADR-004 says "the baseline grows by
    one section", while section 9 and EC-6 say "no instruction file grows in words". The design
    doesn't say whether the measure is per file, or which text pays for the additions.
  evidence: [adr-004 decisions 2 and 4 and consequence 2, component.md:111, EC-6, as-is A-2, A-8]
  confidence: high (the contradiction); medium (feasibility)
  blocking: no

- id: AR-8
  claim: >
    The JSON for several evidence-cite pairs is unspecified. "A single pair returns what it does
    today" implies two JSON shapes. Whether --revision applies to every pair isn't stated. The
    diagram puts the pairs in the CLI, while the verdict across pairs (exit 5 when any pair
    fails) is a rule.
  evidence: [EC-2, component.md:41, 55; evidence_cite.py:32-65]
  confidence: medium
  blocking: no

- id: AR-9
  claim: >
    The failures section has no entry for a review that reaches the three-round cap with
    blocking findings still open (trigger, result, recovery), which the format requires.
  evidence: [BC-6, adr-001 decision 6, design-format.md:31]
  confidence: high
  blocking: no

- id: AR-10
  claim: >
    The behaviour section covers only the command line. The instruction files that orqlet
    upgrade writes change content (EC-6, EC-8); the format asks for "files and data written".
  evidence: [component.md section 3, design-format.md:29]
  confidence: medium
  blocking: no

- id: AR-11
  claim: >
    The manifest lists ORQLET-QA-001 among the standards applied, but doesn't record the
    person-approved exception (Q-14) or the version gap (C-25). The prose handles it in the
    brief's sections 5 and 9. The manifest's considerations could state it, since the manifest
    may carry ids.
  evidence: [manifest standards_applied, component.md:63, 107; as-is C-24, C-25; questions.yaml Q-14]
  confidence: medium
  blocking: no

- id: AR-12
  claim: >
    `explain` stops showing rule ids, but `standards for` keeps them in its human text (A-79).
    No reason is recorded for the difference. Whether clients show that output to people is
    unknown (U-46).
  evidence: [adr-002 decision 4, as-is A-79, U-46]
  confidence: low-medium
  blocking: no
```

## Checked and consistent (no finding)

- **EC-1 "keep NOT_RUN":** stale artifacts, a missing base revision and an unresolved review target already call the skip that produces NOT_RUN (`gate_status.py:182-184, 219-220, 244-247`). Only the unconditional skip at lines 117-122 goes.
- **EC-7:** the version has one source. `pyproject.toml:7, 33-34` reads it dynamically from `src/orqlet/__init__.py`, and `uv.lock:484-485` holds no version for orqlet, so the scope is enough.
- **Layering:** no domain change. The workflow package is used only by the interface and the adapters (ORQLET-ARCH-003).

## Self-check

- **Model and context:** I ran in a clean context with only the parent's prompt. The model is the one this subagent ran as; I didn't observe an identity independently.
- **Not run:** shell commands are blocked in Ask mode. So I did **not** verify the manifest's `sha256` values for the design files or the as-is file, the 1,200-word count of `component.md`, the branch, or uncommitted state.
- **Not checked:**
  - most A-n citations beyond the ones listed above;
  - whether the golden-file tests read the workflow source (AR-1);
  - whether commits happen inside an implement phase (AR-4).
- **Limits:** this is an additional check, not a guarantee. No web lookups.

**Files read:**
- all seven design-folder files;
- the AS-IS file, the ledger, the design format reference and the standards output;
- to verify citations:
  - `gate_status.py` (lines 60-280);
  - `evidence_cite.py`;
  - `validate_as_is.py` (95-160);
  - `validation.py` (skip and result, by search);
  - `MANIFEST.json` (200-386);
  - research `phase-contract.md` (25-93).
- searched only, not read in full: `pyproject.toml`, `uv.lock`, the `tests/` hits for `MANIFEST.json`, workflow-skill searches for `ORQ-I393`, `models resolve` and `ORQ-W390`/`ORQ-W547`.

**Not examined:**
- the review notes in `reviews/` (not written yet);
- the other skill bodies, the baseline source, `identity.json` and the golden files;
- `pin_staleness.py`, beyond search hits;
- the as-is evidence files.

## Author's responses

Each blocking claim was checked against the code before answering.

- AR-1, accepted. `tests/unit/test_manifest.py:41-43` compares MANIFEST.json with the build tool's output. Section 9 now says that every phase that changes the workflow package rebuilds MANIFEST.json and updates the golden files that change with it. The version bump, `orqlet upgrade` of the installed copies, and README stay in the final commit.
- AR-2, accepted. MANIFEST.json lists `phase-contract.md` under design, implement, plan and research only. The model-suggestion step now stays in each skill that runs it, shortened, and is not moved. The phase contract takes the reuse rule and the web-evidence format, which only those four skills use. The diagram says "phase skills" instead of "six".
- AR-3, accepted. ADR-002 decision 2 now defines the line as rendering of the verdict and counts in the interface layer, with no per-code mapping. PASS gives "No action needed." (plus the number of warnings, if any). FAIL gives "Action needed: fix the N error(s) above, then run the command again." NOT_RUN gives "Action needed: resolve the not-run reason(s) above, then run the command again."
- AR-4, accepted. The confirmation compares the cited files with the revision they were cited at, not HEAD, so a commit inside the phase is also caught.
- AR-5, accepted together with the security reviewer's SEC-4. The exempt folder comes from the AS-IS file's location, after path canonicalisation, and is narrowed to `docs/design/<task>/evidence/**`. "Current tree" means HEAD. The input check's approved files for the AS-IS now include that evidence folder.
- AR-6, accepted. Section 5 now states that after the final upgrade this task's artifacts show ORQ-W390, which matches the upgrade row of the stale-input matrix. A change of `standards_lock_hash` still needs an impact review.
- AR-7, accepted. The rule is now: no instruction file grows except the baseline, which grows by the final-reply section only, and the words a skill run loads do not grow. The phase contract stays within its test cap.
- AR-8, accepted. EC-2 defines the JSON: `data.citations` lists one entry per pair in today's shape, and a single pair also keeps today's top-level fields. `--revision` applies to every pair. The per-pair rule sits in the use case.
- AR-9, accepted. Added a failure entry: the cap is reached with a blocking finding still open, so the skill stops with one consolidated report and the person decides.
- AR-10, accepted. Section 3 names the generated instruction files as files written.
- AR-11, accepted. The manifest's operations consideration records the Q-14 exception and the C-25 version gap.
- AR-12, accepted. ADR-002 records the reason: `standards for` is the agent's input and needs the rule text and level to apply it, while `explain` is read by people.
