# Architecture review of the design, round 6

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-20T13:07:06Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:07:06Z) and at save (2026-11-20T13:09:04Z) are identical: no design file changed while the reviewer ran.

| File | sha256 |
|---|---|
| design/manifest.yaml | 52c8f655790916e754cea178908ebce7b90c8abba07ad34f03d5ac375bddb5c2 |
| design/component.md | 977e2a7815c2213d0b2ed2a874777b9310d906a9189e7c6ca56cd8ed2f51f2dd |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | f9612988eaf11cdbbf4ab286c74fcaf4e0d43434d3f0996a79d069529863c02a |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | c26cc24e7b47d241291da16766650edbda5f7529e3d4c81f94305ab51eac6972 |
| design/adr-002 | 9c0980f08fedb91a4d738dc822d65379d76ed4c369db3cec33a8ffe96ad73e88 |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 413bd5ce4aa5eb690712b5b0dbe003e230dd95bbd453c5e5a4fa2050710f9ed1 |
| design/adr-005 | da4e25e94fd38b2b1df3607b02b42ffc24b8ed50117a200938abe4d9da9b7df4 |
| design/adr-006 | 5614e5ec2a3c0b09b08bbb51f8b6fd630496f21c61cb27e5639a82a3758ef949 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| questions.yaml | 46fa60dd778fba34d92148f60569bec8caba5edc056380f0d686802357d4d688 |

The design files changed after this note to answer the findings (see "Author's responses"). The reviewed content is therefore not what will merge, and round 7 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: changes required.** I found 1 blocking and 5 non-blocking findings. Round 5's consent defect is fixed. Nothing is created or changed before consent. Missing roots read as empty and show `will create`. Wide folder modes show `will tighten` and are tightened only after consent. Under `--dry-run`, `uv tool list` runs only when `tools-work/` already exists. These statements agree in section 3 item 6, ADR-002 decision 1a, ADR-006, BC-7 and BC-29, and they match the amended SAFE-001 text.

The D3 set conforms to design-format.md: context, container and component views, a data-flow view, a sequence view, seven ADRs with all four sections, brief sections 1 to 9 in order, and reviewer notes for rounds 1 to 5. Every design citation I opened matches the code: `pyproject.toml:105-127`, `apply_plan.py:39-93`, `local_fs.py:74-77`, `wiring.py:145-149`, `common.py:27-28`, `ancestors.py:8-11`, `instruction_adapter.py:94-139` and `rules.yaml:29-35/66-72`. All 41 ledger questions are answered.

The one blocker is in how an interrupted change is recovered. Recovery adopts only the files that the earlier journal marks as done. `apply_plan` writes a file first and marks it done afterwards. A crash between those two steps leaves a written file that recovery treats as a conflict, so the next run does not converge as the amended SAFE-001 requires.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 6, role: architecture-reviewer}
verdict: changes-required
findings:
  - id: F-1
    blocking: true
    rule: ORQLET-SAFE-001 (as amended, "the manifest is written last so a re-run converges")
    statement: >-
      Adoption takes only what the superseded journal marks as done. ADR-002 line 71
      says "A file the superseded journal records as done, whose current SHA-256 equals
      that record's after-hash". For a shared JSON file it says "when the superseded
      journal records the file as done". BC-30 (component.md:282) repeats this. But
      apply_plan writes first and journals second: write_atomic at
      src/orqlet/application/usecases/apply_plan.py:75, then journal.mark_done at :77.
      A crash between those two lines leaves a file at its after-hash whose journal
      entry is not done. On the re-plan, a created file is "an unowned file holds the
      target name". An updated owned file still has its old hash in user/manifest.json,
      so it reads as "an owned file ... was edited", which refuses the whole client
      (component.md:195). A shared JSON entry becomes an Orqlet-looking entry with no
      manifest record (component.md:196). Each gives exit 3. So for a reachable crash
      state, the claim "The re-plan therefore meets no conflict on its own earlier
      writes, converges" (ADR-002:71) is false. That claim is the only stated reason
      install needs no --resume (ADR-002:74).
    required_change: >-
      Adopt every entry the superseded journal records, done or not, whose current
      SHA-256 equals that entry's after-hash. For a shared JSON file, adopt each entry
      whose canonical-JSON hash equals the render, whatever the file's done flag. A
      delete entry whose file is already absent counts as applied. Restate the rule in
      ADR-002 decision 4, section 3 item 8 and BC-30. Add an acceptance criterion: a
      crash after write_atomic and before mark_done is followed by an install that exits
      0 with no conflict. Apply the same rule to the uninstall adoption (BC-44).
  - id: F-2
    blocking: false
    rule: ORQLET-ARCH-002 / design-format brief part 4 (responsibilities and interfaces)
    statement: >-
      Decision 1a needs results that no listed port carries. Per-client refusals,
      `will create`, `will tighten`, the resolved and pinned real roots, the Windows
      warning and the consent-time creation of roots all have to reach the install use
      case (ADR-002:43-53, component.md section 3 items 6-7, BC-6, BC-7, BC-29). Section
      4 lists only `UserScopeFileSystem(roots: Mapping[prefix, validated root])`
      (component.md:179) and the FileSystem port. The FileSystem port reports no file
      mode or ownership and has no "prepare after consent" step. ADR-002:49 also says
      the work-tree check goes through "a read-only ancestor port", which suggests
      validation sits in the application, while ADR-002:50 says the user-scope adapter
      creates and re-validates roots. Which layer validates, and through which port, is
      not stated.
    required_change: >-
      Name the port or contract in section 4 and its diagram. For example: a
      UserRootInspector that returns per prefix a RootState (resolved path, exists,
      refusal reason, needs-tighten, platform warning), plus an explicit post-consent
      `prepare()` on the user-scope adapter that creates and tightens. Then the plan can
      place it without guessing the layer.
  - id: F-3
    blocking: false
    rule: design-format brief part 5 (failures) / ORQLET-TEST-001
    statement: >-
      It is unclear how much of a client a hook-entry conflict blocks. An edited owned
      file stops "nothing else in that client is written" (component.md:195). A
      non-strict JSON file still writes the skills (component.md:197, sequence.md:67).
      But "A hook entry matches Orqlet's command but has no manifest record, or a
      different hash" (component.md:196) says only "conflict for that entry". An owned
      hook entry with a different hash is an edited owned entry, so it is unclear
      whether it stops the client's other files. BC-6 promises byte-identity of "every
      file of the refused client" only for root and owned-file refusals, so this case
      has no clear expected result.
    required_change: >-
      State in the failures table whether an edited or unrecorded hook entry blocks
      only that entry or the whole client. Make BC-6 match.
  - id: F-4
    blocking: false
    rule: Consistency between views (data-flow.md vs component.md section 4)
    statement: >-
      data-flow.md:19 draws `apply --> tools`, so apply_plan appears to start tool
      preparation. component.md section 4 has the install use case call ToolInstaller
      (UI --> P4) after apply_plan, and section 3 item 3 says the user-scope journalled
      change happens "then prepares tools". apply_plan has no process port
      (apply_plan.py:39-48).
    required_change: >-
      Draw tool preparation from the install use case after apply_plan, not from
      apply_plan.
  - id: F-5
    blocking: false
    rule: ORQLET-SAFE-001 (as amended) wording
    statement: >-
      The amendment text (ADR-002:92) exempts creating "a missing allow-listed root and
      its missing parents under home or under the data directory, and the `user`
      folder". When ORQLET_DATA_DIR points outside home and is missing, the text does
      not clearly cover creating the data directory itself and its parents, which is
      needed before `user/` can be created. Q-41 allows such a data directory, at least
      on Windows.
    required_change: >-
      In the amendment text, say that creating the data directory and its missing
      parents after consent is part of creating the `user` folder, or state that it
      stays refused.
  - id: F-6
    blocking: false
    rule: design-format brief part 3 (behaviour) / ORQLET-TEST-001
    statement: >-
      The status field `global` is defined as `outdated` only when the "manifest
      workflow version [is] below the installed one" (component.md:67). The state for a
      manifest version above the installed Orqlet, for example after a downgrade, is
      not defined, and BC-11 does not cover it.
    required_change: >-
      Define the value for a higher manifest version, whether `configured`, `outdated`
      or a new closed value. Add that case to BC-11.
```

**What I did not check:**
- Evidence files under `docs/design/one-command-setup/evidence/` and prior review notes were outside my allowed inputs, so I did not verify client-contract claims (A-34 to A-41, evidence 1.4/9.6 and similar) or whether earlier findings are fully closed beyond what the current text shows.
- I did not run `orqlet validate design`, import-linter or any check.
- I did not recompute the manifest's sha256 values for the artifacts.

## Author's responses

Every finding is accepted. Round 7 checks the changes.

| Finding | Response |
|---|---|
| F-1 | ADR-002 decision 4 no longer relies on the done flag, because `apply_plan` writes before it marks done (`apply_plan.py:75-77`). Every entry the superseded journal records, done or not, is adopted when the file's current SHA-256 equals its after-hash. A delete whose file is already absent counts as applied. A shared JSON file that the journal records, done or not, is adopted per entry by canonical-JSON hash. Section 3 item 8, BC-30 (a crash between `write_atomic` and `mark_done`, then exit 0 with no conflict) and BC-44 (the same rule for `uninstall`) match. |
| F-2 | ADR-002 decision 1a, "Validation in code": a `UserRootInspector` port returns a `RootState` per prefix (resolved real path, exists, refusal reason, needs-tighten, platform warning), and the use cases plan from it. The user-scope adapter implements it, plus a post-consent `prepare(states)` that creates and tightens folders, validates again and opens each root. The port appears in the component diagram (`UI --> P10`) and among the interfaces. |
| F-3 | The failures table now says that an edited or unrecorded hook entry is a conflict for that entry only; the client's other files and entries are still written. BC-6 says the same for hook-entry conflicts and non-strict JSON files. |
| F-4 | data-flow.md now labels the edge to tool preparation "then the install use case", so tool preparation follows `apply_plan` and is not started by it. |
| F-5 | The amendment text now exempts creating, after consent and with mode 0700, a missing root with its missing parents under home, and the data directory with its missing parents and its `user` folder. |
| F-6 | `global` gains the closed value `newer`, for a manifest workflow version above the installed one, for example after a downgrade. Section 3's field table and BC-11 cover it. |
