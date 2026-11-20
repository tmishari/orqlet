# Architecture review of the design, round 8

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-20T13:13:38Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:13:38Z) and at save (2026-11-20T13:15:33Z) are identical, and every design artifact hash equals the one recorded in `design/manifest.yaml`. The reviewed content is the content that will merge.

| File | sha256 |
|---|---|
| design/manifest.yaml | 80b3d2b47c5a577b833b4c93c1ee6051e8d0f3a76beffd579ca435bd14299d04 |
| design/adr-001 | c26cc24e7b47d241291da16766650edbda5f7529e3d4c81f94305ab51eac6972 |
| design/adr-002 | 4bfa17cdcef0d653f4ef9423cbfdbdb6d9a11fc1de7a4e782be667ebb8aef31b |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 4325a150a453f18c1602ea2a1f702e0d6bbae376459f8c67fbd32e9bfccf90af |
| design/adr-005 | 9e5c51e9ce4b010dec0647a71ef326fb49369916d1d83583aaa1fb93c789119d |
| design/adr-006 | 5614e5ec2a3c0b09b08bbb51f8b6fd630496f21c61cb27e5639a82a3758ef949 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| design/component.md | b2467034ecdd0bc2d8434b65ab96b59a3ef1c96688ab4654e561c5c336e7161f |
| design/container.md | 6c56eeeb792bb270f9c1a0ce5ff54e0105ebe92a7be0a7477d43e8a4764f7102 |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/data-flow.md | c2e15000e13b9c79302613897ffde516629019600b97dd4d9bb73b6caaf2d501 |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| questions.yaml | b31b04e525d634ef09312149c0b26db2fd6bce6284e4f43cd02aefcbe8fe0255 |

## Reviewer output (unchanged)

**Verdict: approve.** Round 7's blocking defect is resolved. The pending changes are now every kept journal whose `created_at` is later than the change recorded in the manifest, and they are adopted oldest first by recorded hash. Planning reads them read-only, only the consented apply marks them superseded, and only a run that writes the manifest prunes. BC-30 and BC-44 test this, including two interruptions in a row. The design conforms to design-format.md for D3: all views, real ADRs with the four sections, brief parts 1–9 in order, and `manual` on every surface that has no extractor. The amended ORQLET-SAFE-001 and ORQLET-ARCH-003 texts are met. The code citations I opened hold. There are 0 blocking and 5 non-blocking findings, mostly about how `rollback --user` interacts with the new rule for pending changes. The plan can settle them, but the design should say them in a sentence.

Not checked: the artifact `sha256` values and `orqlet validate design`, because the read-only shell refused `shasum`; the evidence files (`evidence/web/*`), which are outside my inputs; and the AS-IS entries beyond the code they cite. No client behaviour was qualified.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 8, role: architecture-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: ORQLET-SAFE-001 (as amended); ADR-002 decisions 4 and 5
    statement: >-
      The pending set is "every journal kept under user/journal whose created_at is later than that of the
      change recorded in user/manifest.json" (adr-002 line 77). It does not exclude rolled-back changes or
      rollback changes. Today's rollback restores the manifest-equivalent file (LOCK_PATH, written last) from
      its backup (src/orqlet/application/usecases/rollback.py:133-146). Under `rollback --user <S>`, the
      manifest then records the change before S. S (status rolled-back) and the rollback change R then become
      "pending" for the next install or uninstall. R's entries match the current hashes, so they are adopted
      "each entry taking the owner set its journal records" (adr-002 line 78). The design never says which
      owner set a rollback journal records. It also does not exclude R's own data/manifest.json entry from
      adoption. With a wrong or empty owner set, the adoption that uninstall applies (BC-44) could delete a
      shared ~/.agents/skills file that another client still owns. No BC covers `rollback --user` followed by
      install or uninstall.
    required_change: >-
      In ADR-002 decision 4, state that a journal with status rolled-back is never adopted. State that a
      rollback --user journal records, per entry, the owner set of the state it restores (or that rollback
      journals are excluded from adoption, which converges because their files already match the restored
      manifest). State that data/ prefix entries are never adopted as owned entries. Add a BC: after an
      install for cursor and codex, `rollback --user` of the latest change, then `uninstall --client codex`,
      every shared ~/.agents/skills file is kept and owned by {cursor}, and the run exits 0.
  - id: F-2
    blocking: false
    rule: ORQLET-SAFE-001 (as amended); component.md BC-31
    statement: >-
      ADR-002 decision 4 states that the done flag is unreliable, because apply_plan writes a file before it
      marks the journal entry done (apply_plan.py:75-77, adr-002 line 78). Decision 5 says rollback --user
      otherwise behaves "as today", and today's rollback skips every entry that is not done
      (rollback.py:125-126). After a crash between a write and mark_done, `rollback --user` of the interrupted
      change therefore leaves that file with the change's content. This contradicts BC-31 ("restores every
      root byte-identically"; "For an interrupted change ... it restores the files"). The next install then
      adopts that file as owned, so the person's request to undo the change is only partly honoured.
    required_change: >-
      In ADR-002 decision 5, state the reached-test for user-scope rollback. An entry that is not done is
      restored when the current hash equals its after-hash. It is skipped when the file is in its before
      state, and refused otherwise. Add the crash-window variant to BC-31.
  - id: F-3
    blocking: false
    rule: ORQLET-SAFE-001 (convergence); ADR-002 decision 4
    statement: >-
      Pending changes are ordered and selected by wall-clock created_at (change_journal.py:35, set from
      clock.now() at apply_plan.py:62). Change ids are random UUIDs (wiring.py:152), so they give no order.
      Suppose the system clock steps backwards between a successful change and a later interrupted one. The
      interrupted journal is then not "later", and its writes are not adopted. The next install sees unowned
      files with owned names and reports a conflict with exit 3 instead of converging. The failure is safe,
      because nothing is overwritten. The design also does not say what happens when the journal of the
      change recorded in the manifest is missing, for example after the person removed files from the data
      directory.
    required_change: >-
      Either order changes by a monotonic sequence assigned under user/apply.lock and recorded in each journal
      and in user/manifest.json, or keep created_at and state the limit and its recovery in the failures
      table. In either case, define the pending set when the journal of the manifest's change is absent (for
      example, every kept journal), and cover it with a BC.
  - id: F-4
    blocking: false
    rule: design-format "The design brief" part 4 (responsibilities and interfaces); ORQLET-ARCH-002
    statement: >-
      The design depends on port and contract changes that section 4 of component.md does not list. Today
      JournalEntry has no owner set and no JSON entry key or hash (change_journal.py:20-28). apply_plan builds
      journal entries only from PlannedWrite fields (apply_plan.py:111-119), so the owner set and JSON hashes
      need a carrier through the domain change plan or through apply_plan. ChangeJournal can list only open
      changes (change_journal.py:57-59), not "every kept journal". It also has no prune operation for
      retention. The user manifest contract, which now includes the change id, has no named type. The
      changed rollback use case (--user) and the uninstall flow are absent from the responsibilities table
      and the component diagram. ADR-002 line 50 puts the work-tree check behind "a read-only ancestor port",
      but the check sits inside the UserRootInspector adapter, which needs no port.
    required_change: >-
      In section 4, add the extended JournalEntry and PlannedWrite (or the apply_plan parameter), a
      ChangeJournal operation to list and prune kept changes, a UserManifest contract, and the rollback --user
      and uninstall responsibilities. Say whether the project-scope journal format changes and, if it does,
      how existing journals stay readable. Say where the work-tree check lives.
  - id: F-5
    blocking: false
    rule: design-format "The design set" (consistency between brief and ADRs)
    statement: >-
      The state table of the entry skill in ADR-001 decision 2 (adr-001 lines 20-26) has no row for
      `global: newer` / `next: refuse-newer-global`. component.md line 74 says the entry skill stops in that
      state and tells the person to update the CLI. The table also has no row for `global: outdated`, which
      the failures table (component.md line 221) recovers with "orqlet install or /orqlet .". In those states
      the entry skill's behaviour is defined only in component.md, and BC-12 does not test it.
    required_change: >-
      Add the newer and outdated global states to the ADR-001 decision 2 table, with their actions. Extend
      BC-12, or BC-11, so that the entry skill's text is checked for the refuse-newer-global stop.
```

## Author's responses

Approved, no blocking finding. No design file changed after this note, so its hashes match the manifest. The non-blocking findings are carried into the plan as items the plan must settle, each within a decision the design already states:

| Finding | Response |
|---|---|
| F-1 | Carried to the plan. Within ADR-002 decision 4, the plan will exclude rolled-back journals and `rollback --user` journals from the pending set, will never adopt `data/` prefix entries as owned entries, and will add the reviewer's BC (install for cursor and codex, `rollback --user`, then `uninstall --client codex` keeps shared `~/.agents/skills` files owned by {cursor}, exit 0). |
| F-2 | Carried to the plan. User-scope rollback will use the same reached-test as adoption, not the done flag (`rollback.py:125-126`): an entry that is not done is restored when its current hash equals its after-hash, skipped in its before state, and refused otherwise. BC-31 gains the crash-window variant. |
| F-3 | Carried to the plan. The plan will choose a monotonic sequence assigned under `user/apply.lock`, or keep `created_at` with the limit and its recovery stated in the failures table. It will also define the pending set when the manifest's journal is absent (every kept journal), with a BC. |
| F-4 | Carried to the plan. The plan's phases name the extended `JournalEntry` and `PlannedWrite` carrier, the `ChangeJournal` list and prune operations, a `UserManifest` contract, the `rollback --user` and `uninstall` responsibilities, whether the project journal format changes (with readability of existing journals), and where the work-tree check lives. |
| F-5 | Carried to the plan. The entry-skill phase adds the `global: outdated` and `global: newer` / `refuse-newer-global` rows to the behaviour that ADR-001 decision 2 describes, and a BC-12 check of the stop text. |
