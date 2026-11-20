# Architecture review of the design, round 2

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-20T12:47:09Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T12:47:09Z) and at save (2026-11-20T12:48:58Z) are identical: no design file changed while the reviewer ran.

| File | sha256 |
|---|---|
| design/manifest.yaml | b8cd27a1368566e3de7b191cdb9b9b1b028c4e5f1f7a95899e3c22e8723579ac |
| design/component.md | 4a738fda55357ce7ea4e784bd97d2268a00c6b72e66a4d8cdd7bc536407f8e08 |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | c66bf043e949384421ac711fd782d426ddf38b6a2f4c0394ed36033b37b9fae8 |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | 5bf88b3ce9d12a8c6db0556997e9ddc93b292fb00903f0ea297a478ffd2cee36 |
| design/adr-002 | d3ac6abd9baa42222f7589b6340c10dce23655838166431c28190f56eebe4e3f |
| design/adr-003 | bbc3dbff99b268cff4271c1d4c774ba63e7727e14fbef284b05ad22a4dbd8637 |
| design/adr-004 | 1d23439717edda2d08c91addbd2d55dd82353f4c2404ec00b5fef0d7f13fc46e |
| design/adr-005 | ae73898709a4c7241eb8eaa6db7d5318b41f6ba43ce5645f2445f1937aa9ba99 |
| design/adr-006 | feaca7dde4ee51e5d8eb0d3cb86661b7b84e299269767f609bc57286fa2c0f1c |
| design/adr-007 | 04e9131c62a8e0711118d63cb6fab66de2283e56b13a3df29b8eb6677ce2c1c1 |
| questions.yaml | 9bc0396b719d60664de8376aa4f55404e2c2328a5ce1487715b2b0e7a72a0a73 |

The design files changed after this note to answer the findings (see "Author's responses"). The reviewed content is therefore not what will merge, and round 3 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: changes required.** I found 3 blocking and 6 non-blocking findings. The design follows the D3 format: it has every required view, the nine brief sections in order, four-section ADRs that compare real alternatives, considerations, and expected_changes for each surface. It has no phase list. The layering, ports, NOMODEL-001, MODEL-001 and DET-001 hold. All three blocking findings are about the amended SAFE-001 text and the journalled change plan. The `data/` allow-list leaves out the manifest that the design itself writes last. Creating a missing root and removing emptied folders cannot be done with `apply_plan` and `LocalFileSystem` as the design says they are reused. No acceptance criterion covers user-scope rollback or recovery from an interrupted apply across several roots.

Not checked:
- `.prompts/rules.yaml:66-72` (outside the allowed inputs).
- The stored web evidence files.
- The round-1 review notes, so I did not confirm each round-1 finding one by one.
- The manifest's artifact hashes, which I did not recompute.
- `orqlet validate design`, which I did not run.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 2, role: architecture-reviewer}
verdict: changes-required
findings:
  - id: F-1
    blocking: true
    rule: ORQLET-SAFE-001 (as amended, Q-32)
    statement: >-
      The amendment text does not agree with itself about the data/ root.
      ADR-002 decision 1 (adr-002...md:35) allows only `cursor-user-rules.md`
      to be written under the `data/` root (`<data directory>/user`). Decision 4
      (adr-002...md:59) says "`user/manifest.json` is written last, through the
      `data/` root". Decision 1 also says "Any other path ... is refused"
      (adr-002...md:37), so the manifest write that convergence depends on is
      forbidden by the text proposed as the MUST amendment. component.md:86 and
      EC-4 list the manifest as written.
    required_change: >-
      Add `manifest.json` to the writable sub-paths of the `data/` root in
      decision 1. Otherwise, state that the manifest is written by a separate
      store outside the composite file system, and say how "manifest written
      last" still holds within the one apply_plan transaction. Carry the
      corrected table into the amendment text named in K-1.
  - id: F-2
    blocking: true
    rule: ORQLET-SAFE-001 (as amended); design consistency
    statement: >-
      Creating a missing root and removing emptied folders do not fit the
      journal model the design reuses.
      (a) Decision 1a says "A missing root is created, mode 0700, as a
      journalled step of the change" (adr-002...md:43). But container.md:68
      builds the user scope from "a separate `LocalFileSystem` per allow-listed
      root". That constructor needs the root to exist (`root.resolve(strict=True)`,
      src/orqlet/adapters/fs/local_fs.py:74-77). Journal entries only record
      file create, update and delete (apply_plan.py:111-119), so a directory
      creation has no journal record that rollback or uninstall could undo.
      (b) The real path of a missing root cannot be resolved strictly, so the
      check "real path under the real home" is undefined for it.
      (c) `_remove_emptied_folders` (apply_plan.py:82-93) walks up to the top
      canonical folder. With prefixes, `agents/` maps to `~/.agents` itself. An
      uninstall could therefore rmdir `~/.agents/skills` or `~/.agents`, which
      may have existed before Orqlet, and which lie outside the writable
      sub-paths of decision 1.
      All of this contradicts the claim that one composite file system "reuses
      `apply_plan` unchanged" (adr-002...md:86).
    required_change: >-
      State in ADR-002 (and the amendment text):
      (1) how a missing root is validated, for example the real path of its
      nearest existing ancestor must lie under the real home;
      (2) who creates the root, and how its creation is recorded so that
      rollback and uninstall can undo it, or that a created root is
      deliberately left in place;
      (3) that empty-folder cleanup stops at the writable sub-path boundary and
      never removes a root or a folder that existed before the change.
      Correct the "unchanged" claim, or keep it true by adding no new journal
      kinds. Add an acceptance criterion for each case.
  - id: F-3
    blocking: true
    rule: ORQLET-TEST-001; ORQLET-SAFE-001 (convergence and rollback)
    statement: >-
      Two new behaviours have no acceptance criterion.
      (1) ADR-002 decision 5 (adr-002...md:62-64) and EC-2 add the user-scope
      journal as a rollback source, addressed by prefixed path.
      (2) component.md:190 promises that after an interrupted apply "the next
      `install` recovers or reports it".
      BC-1 to BC-29 cover neither user-scope rollback nor an interrupted
      multi-root apply. BC-5 covers only a clean rerun and BC-8 only uninstall.
      Convergence and rollback across roots, the core of the amended SAFE-001,
      are therefore not tied to any test.
    required_change: >-
      Add these acceptance criteria:
      (a) An apply interrupted after writes in one root and before writes in
      another leaves the manifest unwritten. A rerun of `install` converges to
      the render and writes the manifest last.
      (b) `orqlet rollback` of a user-scope change restores every root
      byte-identically from the 0600 backups, refuses a file touched since the
      change, and never touches a `projects/<id>` journal.
      (c) Journal and backup keys for identical relative paths in two roots do
      not collide.
  - id: F-4
    blocking: false
    rule: ORQLET-ARCH-003 (as amended); R-9 / Q-34; ORQLET-TEST-001
    statement: >-
      The design does not say which clients own the `agents/openai.yaml`
      sidecar in `~/.agents/skills`.
      component.md:81 and ADR-002 decision 2 (adr-002...md:51) say Cursor gets
      "one shared render with Codex including `agents/openai.yaml`". Today only
      the Codex adapter renders the sidecar (src/orqlet/adapters/clients/codex.py:62);
      the Cursor adapter does not (cursor.py:51). Under `install --client cursor`,
      or after `uninstall --client codex`, Codex may still be on the machine and
      will read phase skills from `~/.agents/skills` without the sidecar. Those
      skills would become model-startable in Codex, against Q-34 and BC-12.
      BC-27 does not say whether the sidecar counts as a "shared" entry or a
      "Codex-only" one.
    required_change: >-
      State that in the user scope the sidecar belongs to the shared owner set
      {cursor, codex}. Say how the Cursor user render produces it without
      changing the project golden output (BC-18), for example through the
      shared `render.skills` helper. Extend BC-27 or add a criterion: after
      `install --client cursor` alone, every workflow skill in
      `~/.agents/skills` carries `allow_implicit_invocation: false`.
  - id: F-5
    blocking: false
    rule: ORQLET-ARCH-002; ORQLET-TEST-001
    statement: >-
      The hook's upward `.orqlet/` search and the Copilot `AGENTS.md` read go
      "through the FileSystem port", "never above the home directory"
      (adr-004...md:60-64; component.md:154). The port is confined to one root
      (local_fs.py:72-81), and the design never names which root the hook's
      instance uses. It also does not say what happens when the payload `cwd`
      lies outside home, for example `/tmp`, a container workspace or another
      Windows drive. For a similar ancestor read, the code base uses a
      dedicated port (src/orqlet/application/ports/ancestors.py:8-11). BC-14
      does not cover this case.
    required_change: >-
      Name the root of the file system the hook uses (the injected `UserHome`),
      and state the outcome for a `cwd` outside it: no status, and for Copilot
      whether the foundation is still added. Add the case to BC-14.
  - id: F-6
    blocking: false
    rule: ORQLET-SAFE-001 (as amended); design-format "Consequences"
    statement: >-
      Decision 1a, part of the amendment text, leaves three points open.
      (a) It does not say whether the `data/` root is also bound by "under the
      real home". K-4 sets `HOME` and `ORQLET_DATA_DIR` to temporary folders
      that need not be nested, and `ORQLET_DATA_DIR` may legitimately lie
      outside home.
      (b) It does not say how "must not lie inside a Git work tree" is
      determined: through Vcs/GitRunner, which starts a process, or through a
      `.git` ancestor check.
      (c) ADR-002's Consequences do not mention the effect on a home directory
      tracked as a Git work tree, or on client folders symlinked from a
      dotfiles repository. Every root would be refused (exit 3).
    required_change: >-
      State which roots 1a applies to, including the `data/` root, and the rule
      for an `ORQLET_DATA_DIR` outside home. Name the port and mechanism for the
      work-tree check. Add the dotfiles and home-in-Git consequence and its
      recovery to the ADR and the failures table.
  - id: F-7
    blocking: false
    rule: ORQLET-SAFE-001 (as amended)
    statement: >-
      Tool preparation writes outside any journalled plan:
      `<data directory>/user/tools-work/` is "created 0700 by the tools adapter
      and kept out of the journal" (adr-006...md:52), and uv or pipx write
      their own tool environments. The proposed amendment text (ADR-002
      decisions 1 and 1a) does not say whether such writes are exempt from the
      journalled-plan rule. The amendment reviewers would have to infer it.
    required_change: >-
      State in the amendment text that the journalled-plan rule covers files
      that Orqlet writes into allow-listed roots. Name the exemptions: Orqlet's
      own data-directory bookkeeping, the tools scratch folder, and writes made
      by external tools started through ProcessRunner.
  - id: F-8
    blocking: false
    rule: ORQLET-TEST-001
    statement: >-
      Several stated behaviours have no acceptance criterion.
      - Root refusal for a root owned by another user, a root inside a Git work
        tree, and a `COPILOT_HOME` outside home (component.md:179). BC-6 lists
        only a link and `CODEX_HOME`.
      - `status` fields `global` (missing, configured, outdated) and
        `orqlet_on_path` (component.md:64-65). BC-11 checks only `location` and
        `next`.
      - `init` defaulting to include `copilot` files for new projects (ADR-003
        decision 4), a change to existing `init` output.
      - The rule that exit 3 wins over 1 (component.md:55).
    required_change: >-
      Extend BC-6 and BC-11, and add criteria for the `init` default client set
      and for exit-status precedence.
  - id: F-9
    blocking: false
    rule: ORQLET-ARCH-003 (as amended, Q-33); constraint K-1
    statement: >-
      K-1 (component.md:279) says ADR-003 decision 2 "is the proposed amendment
      text". But decision 2 (adr-003...md:24-29) describes what the Copilot
      adapter renders. It does not give replacement wording for the rule. The
      rule's second clause (the workflow package is read-only data used only by
      adapters and the interface) is not stated as kept or changed.
    required_change: >-
      Give the exact replacement sentence for ORQLET-ARCH-003, for example "The
      four client adapters (Claude Code, Codex, Cursor, Copilot) never import
      one another, and the workflow package ... unchanged". Name the
      import-linter module list that the amendment change will set.
```

## Author's responses

Every finding is accepted. The changes are in the design files listed. Round 3 checks them.

| Finding | Response |
|---|---|
| F-1 | ADR-002 decision 1 now lists `manifest.json` and `cursor-user-rules.md` as the writable sub-paths of `data/`. K-1 names decision 1 as amendment text. |
| F-2 | ADR-002 decision 1a covers three cases. (1) A missing root is validated through the real path of its nearest existing ancestor. (2) The user-scope adapter creates the root with mode 0700 before the plan, outside the journal, and rollback and uninstall deliberately leave it in place. (3) A new paragraph, "Folder boundaries", makes the composite `remove_empty_dir` a no-op at a root and at or above a writable sub-path's first segment. `apply_plan` keeps its journal kinds, and the rejected-alternative wording now says so instead of "unchanged". BC-6 covers a missing root under a link, and BC-33 covers the boundaries and a created root left in place. |
| F-3 | Added BC-30 (an interrupted multi-root apply converges and writes the manifest last), BC-31 (user-scope rollback restores byte-identically, refuses touched files and never touches a `projects/<id>` journal) and BC-32 (prefixed keys do not collide). ADR-002 decision 4 states the recovery rule. |
| F-4 | ADR-002 decision 2: the sidecar carries the owner set of the selected clients among {cursor, codex}. Both adapters render `~/.agents/skills` in user scope through the shared `adapters/render` skills helper with the sidecar on. Project output is unchanged (BC-18). BC-27 now checks `install --client cursor` alone. |
| F-5 | ADR-004 decision 5: the hook's file system is rooted at the injected `UserHome`. A working directory outside home gives no status, and Copilot still gets the packaged foundation. BC-14 covers this case. |
| F-6 | ADR-002 decision 1a applies to every root, `data/` included. `ORQLET_DATA_DIR` may lie outside home but must pass the link and ownership checks. The work-tree check looks for `.git` with no process, through a read-only ancestor port like `AncestorFinder`. The dotfiles and home-in-Git consequence, and its recovery through the project scope, are in the ADR consequences and the failures table. |
| F-7 | ADR-002 decision 1 now has "Scope of the journalled-plan rule", with three named exemptions: the journal and backups bookkeeping, `tools-work/`, and writes by external tools started through `ProcessRunner`. |
| F-8 | BC-6 now covers another owner, a Git work tree and `COPILOT_HOME`. BC-11 covers `global` and `orqlet_on_path`. BC-34 covers the `init` default clients and the `upgrade` of a three-client profile. BC-35 covers exit-status precedence. |
| F-9 | ADR-003 decision 2 now gives the exact replacement sentence for ORQLET-ARCH-003, with its second clause unchanged. It also gives the four-module list of the import-linter independence contract, and states that the workflow-package contract is unchanged. K-1 points to it. |
