# Architecture review of the design, round 7

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-20T13:10:36Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:10:36Z) and at save (2026-11-20T13:12:15Z) are identical: no design file changed while the reviewer ran.

| File | sha256 |
|---|---|
| design/manifest.yaml | d5fbfff6ead817589ff9ac4885b6b99e4f41c1114e9772308fbf33dcea12210e |
| design/adr-001 | c26cc24e7b47d241291da16766650edbda5f7529e3d4c81f94305ab51eac6972 |
| design/adr-002 | 31bd11ef031aa680e861ec812fcfed188d04d34c285bf8afc8851fa4d8ad05f8 |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | b72249062376b9585b9c2f45c4480215894c85036f1527815d37f92b5ad5c826 |
| design/adr-005 | 9e5c51e9ce4b010dec0647a71ef326fb49369916d1d83583aaa1fb93c789119d |
| design/adr-006 | 5614e5ec2a3c0b09b08bbb51f8b6fd630496f21c61cb27e5639a82a3758ef949 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| design/component.md | ecf5479f45e33fc776121bae332b264b616c2ffd0d72187c8a284416b80f3862 |
| design/container.md | f9612988eaf11cdbbf4ab286c74fcaf4e0d43434d3f0996a79d069529863c02a |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/data-flow.md | 449ebc1d53ad3575d4715907da9bfefa701f08257e159619d35601c47d673497 |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| questions.yaml | b31b04e525d634ef09312149c0b26db2fd6bce6284e4f43cd02aefcbe8fe0255 |

The design files changed after this note to answer the findings (see "Author's responses"). The reviewed content is therefore not what will merge, and round 8 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: changes required.** The design meets the D3 rules in design-format.md: it has a context view, real ADRs with all four sections, Mermaid diagrams, the brief parts in the required order, sourced R-n and BC-n entries, `verification: manual` where no extractor exists, no open ledger question (Q-1 to Q-44 are all answered) and no phase order. Layering, ARCH-003 as amended, MODEL-001, NOMODEL-001 and DET-001/002 hold. The round-6 crash case (written but not marked done) is fixed. One blocking defect is left. Adoption is defined against a single superseded journal, so two interrupted runs in a row do not converge, which breaks the convergence that SAFE-001 as amended requires and that ADR-002 claims. There is 1 blocking finding and 6 non-blocking findings.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 7, role: architecture-reviewer}
verdict: changes-required
findings:
  - id: F-1
    blocking: true
    rule: ORQLET-SAFE-001 (as amended, "the manifest is written last so a re-run converges")
    statement: >-
      Adoption reads only one journal. ADR-002 decision 4 says "Every entry the superseded
      journal records ... is adopted", and component.md section 3 item 8 (line 57) speaks of
      "An unfinished user-scope change". Here is a sequence that breaks it. Run A creates file X
      and crashes before the manifest. Run B adopts X. X already equals the render, so B plans
      no write for it and B's journal has no entry for X (BC-5: a rerun with no change writes
      nothing). B's apply_plan then marks A superseded and starts B's journal
      (apply_plan.py:55-65). If B also crashes before the manifest, run C adopts only B's
      journal. X is then in no manifest and in no journal C reads, so C sees an unowned file
      with an owned name. That is a conflict with exit 3, not convergence. This contradicts
      ADR-002 decision 4 ("The re-plan therefore meets no conflict on its own earlier writes,
      converges") and the failures-table row "Interrupted apply ... converges". BC-30 and BC-44
      test only one interruption.
    required_change: >-
      Define adoption over every user-scope change that the current user/manifest.json does not
      yet reflect. That means every open or superseded journal kept by retention that is newer
      than the change that wrote the manifest; record that change id in the manifest so the
      order is known. Apply these journals oldest first. Extend BC-30 (or add a BC) with two
      interruptions in a row followed by an install that exits 0 with no conflict. Also say
      that retention keeps those journals until a successful run.
  - id: F-2
    blocking: false
    rule: ORQLET-SAFE-001 (as amended); ADR-002 decisions 2, 4 and 5
    statement: >-
      Adopted entries need an owner set, but no source for it is stated. JournalRecord and
      JournalEntry (change_journal.py:20-37) hold path, kind and hashes only. ADR-002 decision 4
      makes uninstall adopt a superseded change's writes and "then remove the adopted entries
      once no owner remains". BC-44 requires that removal. Uninstall with no --client acts on
      owners recorded in user/manifest.json (decision 5), and adopted entries are not in it yet.
    required_change: >-
      State that the user-scope journal records the owner set of each entry, next to the pinned
      roots that EC-4 already adds, and that adoption takes the owner set from there. The plan
      can settle the schema.
  - id: F-3
    blocking: false
    rule: ORQLET-SAFE-001 (as amended); ADR-002 decision 4
    statement: >-
      Files and shared JSON entries are adopted by different measures. A file is adopted
      against the journal's after-hash, but a shared JSON entry is adopted against "the entry of
      the current render". ADR-002 decision 4 states that a JSON entry that differs "after a
      workflow version change, stays a conflict". So if Orqlet is upgraded between a crash and
      the recovery, the hook entries Orqlet itself wrote need a manual removal, while the
      skill files in the same change converge. The failures table names no recovery for this
      case.
    required_change: >-
      Either record the canonical-JSON hash of each written entry in the user journal and
      adopt against that, as files are adopted, or keep the stated behaviour and add a
      failures-table row with its recovery.
  - id: F-4
    blocking: false
    rule: design-format "The behaviour" and "unresolved decisions"; consistency with existing downgrade handling
    statement: >-
      `status` gains `global: newer` (component.md line 67), but nothing says what `install`
      does when the user manifest's workflow version is above the running one. Project
      `upgrade` refuses a downgrade unless --allow-weaker is passed (upgrade.py:94,
      upgrade.py:353-380), and `rollback --user` keeps the weaker-workflow check (ADR-002
      decision 5). `install` has no --allow-weaker, and the closed `next` set has no value for
      this state. As written, an older `orqlet` would silently overwrite global phase skills,
      which can shadow project copies (Q-38).
    required_change: >-
      State the decision in ADR-002 or ADR-001. For example, mirror upgrade: refuse with exit 3
      unless --allow-weaker, and set `next` accordingly. If the design cannot make this call,
      raise it as a ledger question. Add a BC for it.
  - id: F-5
    blocking: false
    rule: design-format "The design brief" (consistency between brief and ADR); ORQLET-TEST-001
    statement: >-
      BC-30's first sentence says the next install "adopts the files and entries that the
      superseded journal records as done with a matching hash". ADR-002 decision 4 and
      component.md section 3 item 8 say "done or not". The last sentence of BC-30 covers the
      not-done crash, so the criterion contradicts itself. No BC tests the rule that a delete
      entry whose file is already absent counts as applied. In section 6, BC-46 comes before
      BC-45.
    required_change: >-
      Change BC-30 to "records, done or not, with a matching after-hash". Add the
      delete-already-absent case to BC-30 or BC-44. Put the BCs in number order.
  - id: F-6
    blocking: false
    rule: ORQLET-SAFE-001 (as amended, "Nothing is created or changed in the user scope before the person consents"); component.md section 3 item 6
    statement: >-
      Section 3 item 8 ("is marked superseded, its id is named in the preview") and the
      failures-table row "Interrupted apply" can be read as marking the journal superseded
      while planning. That would change state under --dry-run or a declined preview. Today
      apply_plan marks earlier changes superseded only inside the apply (apply_plan.py:55-56),
      after consent.
    required_change: >-
      Say that planning reads open journals read-only and that they are marked superseded only
      by the consented apply. Add a --dry-run case with a pending interrupted change to BC-7 or
      BC-42.
  - id: F-7
    blocking: false
    rule: ORQLET-ARCH-002; consistency between component.md, container.md and data-flow.md
    statement: >-
      Under ARCH-002 the application can only call a port, and the consent step belongs to the
      install, uninstall and rollback use cases. Yet component.md section 4 (line 181) says only
      that the user-scope adapter implements prepare(states) "together with" the
      UserRootInspector port. It does not say that prepare is a port operation, or that prepare
      returns the composite FileSystem opened after consent, which apply_plan then receives (the
      diagram draws AP --> P2 as if that FileSystem existed before consent). The container
      view's port list (container.md:19) leaves out UserRootInspector and the read-only ancestor
      port that ADR-002 decision 1a uses. The install-time data flow (data-flow.md:5-21) has no
      root-inspection or prepare step.
    required_change: >-
      Name prepare(states) -> FileSystem (or an equivalent factory) as part of the
      UserRootInspector port. Add UserRootInspector and the ancestor port to the container
      view, and add root inspection and post-consent preparation to the install data flow. The
      plan can settle the exact signatures.
```

Things I did not check:
- I did not read or verify the web evidence files (`client-integration-contracts.md`, `global-setup.md`, `graphify.md`, `uv.md`); the input list did not include them.
- I checked AS-IS entries only by spot checks of A-27, A-30 and A-31. Other A, U, C and I references were not compared with as-is.md.
- I did not read the review notes from rounds 1 to 6. Whether earlier findings were addressed is taken from the task context, except for the round-6 done-flag point, which I verified against `apply_plan.py`.
- I did not run `orqlet validate design`, so the class trigger, the manifest artifact hashes and `applicable_rules_hash` were not recomputed.
- I verified these code and rule citations:
  - `apply_plan.py:39-93`
  - `pyproject.toml:105-127`
  - `.prompts/rules.yaml:66-72`
  - `common.py:27-28`
  - `ancestors.py:8-11`
  - `local_fs.py:72-77`
  - `wiring.py:145-149`
  - `change_journal.py`

  I did not open the `instruction_adapter.py:94-139` citation.

## Author's responses

Every finding is accepted. Round 8 checks the changes.

| Finding | Response |
|---|---|
| F-1 | Accepted. ADR-002 decision 4 now adopts every pending change: each journal kept under `user/journal` whose `created_at` (`change_journal.py:35`) is later than that of the change recorded in `user/manifest.json`. The manifest now records the id of the change that wrote it (decision 2, EC-4). Pending changes are adopted oldest first. Retention prunes only after a successful run has written the manifest, so a pending change is never pruned first. BC-30 adds two interrupted runs in a row, ending in exit 0 with no conflict. |
| F-2 | Accepted. Each user-scope journal entry records its owner set (ADR-002 decision 4, "Journal content", EC-4), and adoption takes the owner set from there. BC-44 says so. |
| F-3 | Accepted, with the first option. The journal records each written JSON entry's key and canonical-JSON hash, and adoption compares against that hash, not the current render. A workflow upgrade between the crash and the recovery therefore still converges (BC-30). |
| F-4 | Accepted. This follows the existing `upgrade` convention (`upgrade.py:94`, `:353-380`). `install` refuses with exit 3 when `user/manifest.json` holds a newer workflow version, unless `--allow-weaker` is given (ADR-002 decision 2, section 3 item 9, EC-1). `status` sets `next: refuse-newer-global`, a new closed value at which the entry skill stops. BC-11 and BC-47 cover it. |
| F-5 | Accepted. BC-30 now reads "done or not, with a matching after-hash" and covers a recorded delete whose file is already absent. BC-44 covers the same for `uninstall`. The BCs are in number order. |
| F-6 | Accepted. Planning reads pending journals read-only, and only the consented apply marks them superseded (ADR-002 decision 4, section 3 item 8, failures table). BC-7 adds a pending interrupted change that stays byte-identical under `--dry-run` and a declined preview. |
| F-7 | Accepted. `UserRootInspector` now has `planning_fs(states) -> FileSystem` (read-only) and `prepare(states) -> FileSystem`. The use case calls `prepare` after consent, and `apply_plan` receives the writable composite it returns (component.md section 4, ADR-002 decision 1a). The container view lists `UserRootInspector`, `AncestorFinder` and `BackupStore`. The install data flow shows root inspection, pending journals and `prepare`. |
