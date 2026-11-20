# Security review of the design, round 7

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-20T13:10:36Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

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

The design files changed after this note (see "Author's responses"), and round 8 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: approve.** 0 blocking and 4 non-blocking findings. The trust boundaries TB-1 to TB-3 each have stated controls that match their acceptance criteria:
- **SAFE-001:** the proposed amendment text in ADR-002 is exact and limits the exemptions.
- **Consent:** nothing is created or changed before the person agrees.
- **Roots:** they are validated, checked again in `prepare()` and pinned.
- **Shared JSON files:** strict parsing with entry-level ownership.
- **Recovery:** adoption no longer relies on the done flag; retention is set (Q-40).
- **Processes and output:** tools are started through ProcessRunner with absolute paths and a scrubbed environment; tool output is redacted and printed as inert text.
- **Hooks:** they read repository files within size limits and fill fixed templates.
- **Residual risks:** each one is an answered ledger question (Q-39 to Q-44).

The four findings below are gaps the plan can close within the controls the design already states.

What I could not check: the stored web evidence and client contracts, how uv and pipx behave at the pinned versions, the earlier review notes, and anything outside the listed inputs. All code and rule citations I opened match: `local_fs.py:74-77`, `apply_plan.py:39-93`, `wiring.py:145-149`, `ancestors.py:8-11`, `pyproject.toml:105-127`, `.prompts/rules.yaml:66-72` and the ProcessRunner port. This review is an additional check, not a guarantee.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 7, role: security-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: TB-1 / ORQLET-SAFE-001 (root pinning, shared-file ownership)
    statement: >-
      Root pinning refuses only for `uninstall`, `rollback --user` and adoption
      (adr-002:53, "Roots are pinned"). BC-6 limits the changed-root case to "uninstall
      and rollback --user" (component.md:236). Suppose `CODEX_HOME`, `COPILOT_HOME` or
      `ORQLET_DATA_DIR` changes after an install, and `install` runs again. The design
      does not say what happens then. The likely result is that the manifest's
      `codex/...` hash records are compared with files in a different root. Then
      `user/manifest.json` is rewritten with the new root. The old root's owned
      entries, including a registered `orqlet hook` in the old `hooks.json`, become
      untracked. Neither `uninstall` nor rollback can then find them.
    required_change: >-
      State what `install` does when a prefix resolves to a different real root than
      the recorded one. Either refuse with exit 3 and name the variable, as `uninstall`
      does, or plan the old root explicitly. Add `install` to the changed-root case of
      BC-6.
  - id: F-2
    blocking: false
    rule: ORQLET-SEC-002 / TB-3 (untrusted content reaching agent context)
    statement: >-
      ADR-004 decision 1a says the post-edit path has "control and bidirectional
      characters removed" (adr-004:44). Two other places use a stricter rule. ADR-001
      decision 3 (adr-001:31) makes a path with a control, bidirectional or format (Cf)
      character null and never alters it. ADR-007 decision 8 (adr-007:38) also strips
      Cf characters. So the hook would pass zero-width and other format characters to
      the agent, and would show an altered path rather than leave it out. The path
      comes from a repository-controlled lock.
    required_change: >-
      Give the hook's post-edit path the same rule as `status`: control,
      bidirectional, format characters or more than 200 characters mean the field is
      left out, never altered. Add a zero-width case to BC-15.
  - id: F-3
    blocking: false
    rule: TB-1 (adoption, Q-41 integrity warning) / design-format acceptance criteria
    statement: >-
      Two acceptance criteria lag behind the design. First, BC-30's opening sentence
      adopts entries "that the superseded journal records as done with a matching hash"
      (component.md:287). That contradicts ADR-002's "done or not" (adr-002:72), though
      BC-30's last sentence covers the crash case. Second, `uninstall` also trusts
      superseded journals for adoption (adr-002:73). But the Windows integrity warning
      is tested only for `install` (BC-39, component.md:296) and `rollback --user`
      (BC-46, component.md:305), so nothing checks that `uninstall` shows it.
    required_change: >-
      Reword BC-30 to "done or not". State that the `uninstall` preview carries the
      Q-41 warning, including its integrity part, and add `uninstall` to BC-39 or
      BC-46.
  - id: F-4
    blocking: false
    rule: TB-1 (backups 0600, credential exposure, Q-40)
    statement: >-
      Section 4 of component.md gives the 0600 backup and journal mode to the composite
      user-scope file system (component.md:172). Backups and journals actually go
      through the `BackupStore` and `ChangeJournal` ports (apply_plan.py:39-41), which
      today are `FsBackupStore` and `FsChangeJournal` (wiring.py:146-147,
      fs/journal.py:29-30, 92-97). Those write through a `LocalFileSystem`, and its
      `write_atomic` uses mode 0644 for new files (local_fs.py:37, 113). The composite's
      `data/` prefix allows only `manifest.json` and `cursor-user-rules.md`
      (adr-002:35), so backups cannot be written through it either. The control is
      stated and tested (BC-29), but given to the wrong component, so credential-bearing
      backups could be created 0644.
    required_change: >-
      Give the 0600 mode to the user-namespace journal and backup store adapter, and to
      the file-system write it uses, in section 4 of component.md and in ADR-002
      decision 4. Make BC-29 check that a new backup file is 0600.
```

**Self-check**
- I read only the listed inputs, plus the source files needed to verify citations: `apply_plan.py`, `local_fs.py`, `wiring.py`, `ancestors.py`, `process.py`, `fs/journal.py`, `pyproject.toml` and `.prompts/rules.yaml`. I opened no secret file and nothing in a home client folder.
- I edited no file and did not use the web.
- Each finding cites a file and line. None is blocking, because each sits within a control the design already states.
- I did not look at the earlier reviews, so I cannot confirm that every round 1 to 6 point is closed beyond what the brief summarised and the design text shows.

## Author's responses

Every finding is accepted. Round 8 checks the changes.

| Finding | Response |
|---|---|
| F-1 | Accepted. Under ADR-002 decision 1a, `install` now also refuses with exit 3, naming the variable, when a prefix with recorded entries resolves to a different real root. The recovery is `uninstall --client C` with the old value, then `install` with the new one. The failures table has this row, BC-6 includes `install`, and BC-47 tests it. |
| F-2 | Accepted. The ADR-004 post-edit path now follows the `status` rule: a control, bidirectional or format character, or more than 200 characters, means the line is left out and the path is never altered. BC-15 adds a zero-width case, and BC-14 now says that offending fields are left out. |
| F-3 | Accepted. BC-30 now reads "done or not". The `uninstall` preview carries the Q-41 warning, including its integrity part (ADR-002 decision 1a, failures table). BC-39 covers `install` and `uninstall`. |
| F-4 | Accepted. The 0600 mode now belongs to the user journal and backup store adapters (`ChangeJournal`, `BackupStore`), which create every new file with that mode. ADR-002 decision 4 notes that today's `write_atomic` default is 0644 (`local_fs.py:36`). The composite file system row no longer claims it. BC-29 checks a newly created backup file. |
