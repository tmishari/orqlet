# Architecture review of the design, round 4

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-20T13:00:04Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:00:04Z) and at save (2026-11-20T13:02:29Z) are identical: no design file changed while the reviewer ran.

| File | sha256 |
|---|---|
| design/manifest.yaml | fc2a2d02f9c32b53723144c6ec18f428f77f6dd32a9c8203c63b2ba26e92576c |
| design/component.md | 0355ebce0a072ef32242fb281050e30e6daa19efb6bb88cd38b5c70bb2d3b86b |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | a436c0a5c5c34989b476680d8962b949d3e0c41eedad5e23d926a506b1158f87 |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | 435abc5ad294cc019f47484a26d072d4b697208cc49c9e112586d68e1416e57c |
| design/adr-002 | d65fa9997c300022bf16df390ca2392e5c78db6dead580c35af7d3151fb9b1d2 |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 87e015fe06a37f291fb50981c6b9d65619732448b7a285c786a9bd972ec9c453 |
| design/adr-005 | da4e25e94fd38b2b1df3607b02b42ffc24b8ed50117a200938abe4d9da9b7df4 |
| design/adr-006 | 5dd92b0ac6caf184acca108ea272501d2ea7f1a008053d61234b1bb8236b834d |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| questions.yaml | 46fa60dd778fba34d92148f60569bec8caba5edc056380f0d686802357d4d688 |

The design files changed after this note to answer the findings (see "Author's responses"). The reviewed content is therefore not what will merge, and round 5 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: changes required.** I found 1 blocking and 5 non-blocking findings. The round 3 blocking points are resolved. ADR-002 now ends its Decision section with exact SAFE-001 amendment text and a closed list of exemptions (ADR-002:86-88). Recovery after an interrupted apply now has one outcome: mark the change superseded and plan again (ADR-002:69). `rollback --user <change-id>` is specified (ADR-002:76, component.md:61). The design meets design-format for class D3: it has every required view, the brief sections are in the right order, every ADR has the four sections with real alternatives, no phase or build order appears beyond constraint K-1 and its reason, and Q-32 to Q-41 are all answered. I checked the code citations I sampled and they hold: `apply_plan.py:55-56` and `:82-93`, `local_fs.py:74-77`, `wiring.py:145-149`, `common.py:27-28`, `instruction_adapter.py:94-139`, `pyproject.toml:105-127` and `.prompts/rules.yaml:66-72`. `rev-parse` is on the GitRunner allow-list, and `adapters/render/skills.py` exists. The one blocking defect: the design says a superseded change stays available to `rollback --user`, while the retention rule prunes superseded changes on the very install that recovers from the interruption.

I did not check these:
- The A-n, U-n and C-n entries against the full text of `as-is.md`. I only checked them for consistency with how the design uses them.
- The evidence files under `evidence/web/`, which are outside my allowed inputs.
- The artifact sha256 values and digests in the manifest.
- Whether import-linter at the locked version accepts a contract that names a module that does not exist yet. K-1 leaves this to the plan.

I did not run `orqlet validate design`.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 4, role: architecture-reviewer}
verdict: changes-required
findings:
  - id: F-1
    blocking: true
    rule: ORQLET-SAFE-001 (as amended) / design-format "The design brief" (consistency of failures and acceptance criteria)
    statement: >-
      The recovery contract for an interrupted user-scope apply contradicts the retention rule.
      ADR-002:69 says "The preview names the superseded change id, so `orqlet rollback --user <id>`
      stays possible". The Interrupted apply row of the failures table (component.md:203) gives the
      recovery as "`orqlet rollback --user <id>` undoes the superseded change if wanted", which is an
      action taken after the recovering install. But ADR-002:71, BC-37 (component.md:285) and the
      person's answer to Q-40 (questions.yaml:795-796) all say that "a successful install or
      uninstall prunes older and superseded ones". The recovering install in BC-30 (component.md:277)
      is itself successful (exit 0), so it prunes the backups and journal of the change it has just
      marked superseded. After that, BC-31 (component.md:278) cannot hold for that change. BC-30,
      BC-31 and BC-37 therefore cannot all pass in sequence, and a test author cannot tell which one
      is meant. A second gap: no part of the design says what `rollback --user` writes to
      `user/manifest.json` for a superseded change. A superseded change journalled no manifest
      entry, because the manifest is written last, while `rollback.py:133-146` restores only the
      entries that were journalled.
    required_change: >-
      Make the recovery contract consistent with Q-40. One option: state that a superseded change
      can be rolled back only before the recovering install applies. The preview names it, and the
      person can decline and run `rollback --user <id>` first; at that point the files return to the
      state the old manifest describes. Then correct ADR-002 decision 4, the Interrupted apply row
      and BC-31 to match. If the person instead wants superseded changes kept inside the window of
      3, raise that as a ledger question that revises Q-40. In either case, say what
      `rollback --user` writes as the manifest for a change that has no journalled manifest entry.
  - id: F-2
    blocking: false
    rule: ORQLET-TEST-001 / design-format "The design brief" item 6
    statement: >-
      BC-6 (component.md:217-228) requires each listed case to give a conflict or a refusal and
      "leave every file byte-identical". The failures table allows partial writes in some of these
      cases. A root refusal applies only to that client (component.md:190). A non-strict JSON
      settings file still lets the skills be written (component.md:196). The sequence view shows
      "other entries applied; exit 3" (sequence.md:68). Read literally, BC-6 contradicts these
      statements, so it is open to interpretation.
    required_change: >-
      Narrow BC-6 to what is actually kept: the conflicting file or entry, and for a root or
      owned-file refusal, every file of the refused client. Also say that the other clients' writes
      go ahead.
  - id: F-3
    blocking: false
    rule: design-format (consistency between views, brief and manifest)
    statement: >-
      Several small inconsistencies:
      (a) container.md:67 says the user-scope file system "is a separate `LocalFileSystem` per
      allow-listed root". ADR-002:26 and :37 decide on one composite file system that `apply_plan`
      receives. The container view does not show the composite.
      (b) The container view omits the `scan.executables` and `workflow_package` adapters and the
      `WorkflowSource`, `InstructionAdapter` and `ExecutableLocator` ports that component.md:118-131
      shows. Only `ExecutableLocator` appears, in the ports list at container.md:19, with no adapter.
      (c) The data directory list at component.md:89 omits `user/apply.lock`, which ADR-002:68 and
      EC-4 include.
      (d) component.md:170 adds hook context templates to the workflow package, but EC-9 does not
      list them.
    required_change: >-
      Show the composite file system in the container view, built from per-root file systems if
      that is the intent. Add the missing adapters and ports. Add `user/apply.lock` to
      component.md section 3, and the hook templates to EC-9.
  - id: F-4
    blocking: false
    rule: ORQLET-TEST-001
    statement: >-
      Some stated behaviours have no acceptance criterion:
      - `status` exit 5 when a check could not run (component.md:75);
      - exit 4 for a non-interactive run without `--yes` (component.md:51, ADR-007 decision 5);
      - ADR-002 decision 6 (ADR-002:77): `install` never writes a project, and `init` never writes
        the user scope (BC-7 covers `--dry-run` only);
      - `hook` exit 2 for a usage error (component.md:78);
      - `uninstall --dry-run` and the `uninstall` exit statuses;
      - the `host step` that `install` reports when a client gets no post-edit or hook registration
        under K-12 (ADR-004:37, component.md:308-310).
    required_change: >-
      Add BC entries for these behaviours, or extend existing ones, so that each stated behaviour
      has a test.
  - id: F-5
    blocking: false
    rule: ORQLET-ARCH-002 / design-format "The design brief" item 4 (responsibilities)
    statement: >-
      ADR-002 decision 3 (ADR-002:60-65) defines how shared JSON files are merged: strict parsing,
      matching on a canonical-JSON hash, and keeping the order of unrelated keys. The responsibility
      table (component.md:158-170) gives this job to no component. It also does not say which
      component renders the hook entries for `settings.json` and `hooks.json`; it may be the client
      adapters under `RenderScope.user`. Either placement is legal under ARCH-002, because `json` is
      not a forbidden module (pyproject.toml:105-112), but the layer and the owner are left open.
    required_change: >-
      Name the component and the layer that own entry-level merging of shared JSON, and the one that
      renders hook entries for each client.
  - id: F-6
    blocking: false
    rule: design-format "The manifest" (expected_changes)
    statement: >-
      EC-2 (manifest.yaml, EC-2 value) says "Every other behaviour is unchanged" and mentions Copilot
      output only "for a profile listing copilot". ADR-003 decision 4 (adr-003:35) and BC-34
      (component.md:281) change the default of `init` with no `--client` from three clients to four,
      so a new project now gets `.github/skills`. This is a visible change to `init`'s default on the
      public command line, and EC-2 does not state it explicitly.
    required_change: >-
      State in EC-2 that `init` with no `--client` now covers four clients, including copilot.
```

## Author's responses

Every finding is accepted. Round 5 checks the changes.

| Finding | Response |
|---|---|
| F-1 | Q-40 stands as answered. ADR-002 decision 4 says a superseded change can be rolled back only before the recovering `install` applies. The preview names it and warns that applying prunes it, so the person can decline and run `rollback --user <id>` first. Decision 5 says a rollback of a change that wrote no manifest leaves `user/manifest.json` as it is, since that manifest already describes the restored state. The Interrupted apply row, BC-30 (afterwards, rollback reports the change unavailable) and BC-31 (rollback before recovery leaves the manifest unchanged) match. Decision 4 also adds adoption of the superseded change's own done writes with a matching hash, so the re-plan meets no conflict (security F-7 of the same round). |
| F-2 | BC-6 now keeps byte-identical only the conflicting file or entry, and for a root or owned-file refusal, every file of the refused client. Other clients' writes go ahead, and the run exits 3. |
| F-3 | (a) container.md now shows the composite `fs.user_scope` over one `LocalFileSystem` per root, and its rule text says the same. (b) It adds `scan.executables`, `workflow_package source`, the `WorkflowSource` and `InstructionAdapter` ports, the implements links for the four client adapters, and the shared JSON merge. (c) The section 3 data directory list includes `user/apply.lock`. (d) EC-9 lists the hook context templates. |
| F-4 | Added BC-40 (non-interactive exit 4 for `install` and `uninstall`, `status` exit 5, `hook` exit 2), BC-41 (scope separation of `install` against `init` and `upgrade`), BC-42 (`uninstall --dry-run` and an edited entry giving exit 3) and BC-43 (the `host step` for a left-out registration). |
| F-5 | ADR-002 decision 3 and the responsibility table: each client adapter renders its own hook entries under `RenderScope.user` as entry objects. The install use case, in the application layer, merges them through a pure helper with the standard-library `json` module only. |
| F-6 | EC-2 now states that `init` with no `--client` covers four clients, so a new project gets `.github/skills`. |
