# Architecture review of the rust-migration design, round 6 (allowed by the person)

Reviewer: orqlet-arch-reviewer subagent (fbaefe8b-f248-49ef-9a74-3c9e3c37519e), fresh context, model named as Claude Opus 5.5.
Earlier rounds: `architecture-reviewer-design-r1.md` to `-r5.md`. The person allowed this sixth round on 2026-11-25, after round 5.
Design file hashes of this round, given to the reviewer in its prompt:

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#c15657e6d7c37ecf163410b0db8696b3fb65f3fa0df698135469dcbd236d9d73
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#47e64f08204cfddc55b74aa0334579905e23483e81954b2cde6ece037c9cd739
docs/design/rust-migration/design/adr-003-libraries.md#dee7f39333085019352b841807ef36965288fee5be36607971d33e9f2678df82
docs/design/rust-migration/design/adr-004-version-and-hashes.md#ea987d465d01ff0381a308ff3471a4a9aeceff1d35fab12fc0c9f66790e2ac9a
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#54835d937a3ef93f34ca9411d6b1d9da377cee3a9c918f4a639b98248c2e9c69
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#e3bd59b65704ae83e8b88157f9fbca0603eb35ec72f9aa236dec6017029ed9a1
docs/design/rust-migration/design/adr-007-security-controls.md#579a7817dff921263f1f1ffe26e88bacd0b154de18616c783b661d3cad272199
docs/design/rust-migration/design/component.md#ab6b685f0519e101b0e152fa7acb706ef8a2582509d46c9db6005340d0a4f938
docs/design/rust-migration/design/manifest.yaml#60dbabbf2998e5e732c143223ebee92f7fc0a540990f99b50067f3726ddec6f6
docs/design/rust-migration/design/views.md#10359fef0c04cf3bf73b54d766eeda1f14b010dae86e11428cf1a80e7a6182e6
```

## Reviewer output (unchanged)

# Architecture review of the rust-migration design, round 6

Reviewer: orqlet-arch-reviewer, a fresh context, model named as Claude Opus 5.5. I read only the given paths and the source they cite.

## Summary

I found no blocking or major findings, and three minor ones. All four round-5 architecture findings (R5-F1 to R5-F4) and all five round-5 security findings (SEC-D5-1 to SEC-D5-5) are resolved in the text. The design now matches the answers to Q-18, Q-19 and Q-20.

The three minor findings:
- **R6-F1:** the design defines the "main work tree" as the folder that holds the common Git folder. That is wrong for a bare repository, and the error refuses too much.
- **R6-F2:** the new rules for the data directory (Q-18, Q-19, the main-work-tree comparison, an empty `ORQLET_DATA_DIR`) have no acceptance criterion. ADR-007 says every rule has one.
- **R6-F3:** four statements were not updated: the failures table in the brief and view D-5 leave out ORQ-E106, EC-4 still limits the journal reads to "before an upgrade", and EC-6 says the hook covers the Git work tree.

**Checks not run.** The shell was refused in this mode. So I could not compute the SHA-256 values, confirm the branch or HEAD, or run `orqlet standards for`, `orqlet validate design` or `orqlet validate ledger`. As a substitute, I compared the ten values you gave with the `manifest.yaml` artifact hashes (lines 117-129). All nine artifact values match. Nothing records the manifest's own hash (`60dbab…`), so I did not check it. A match with the manifest does not prove the file bytes match. I read the working tree, not 3e3c311.

## Findings (orqlet.finding/v1)

```yaml
findings:
  - id: R6-F1
    severity: minor
    location: adr-007 decision 10 (comparison targets); BC-19
    evidence: >
      adr-007-security-controls.md line 18: "for a linked worktree, the main work tree, the folder
      that holds the common Git folder". src/orqlet/application/ports/vcs.py lines 102-105: a
      worktree counts as linked when git_dir != common_dir. src/orqlet/adapters/git/vcs_git.py
      line 82: common_dir is the real path that `rev-parse --git-common-dir` prints, whatever its
      name. The data directory is dirs::data_local_dir() plus orqlet (ADR-003 line 28), which is
      normally below the home folder.
    finding: >
      The folder that holds the common Git folder is the main work tree only when the common
      folder is a non-bare `.git`. Git behaviour, from general knowledge and not looked up: for a
      linked worktree of a bare repository, or of a repository created with a separate Git folder,
      the common folder is the bare or separate folder. Its parent is then an ordinary folder.
      Example: a bare clone at ~/repo.git with `git worktree add`. The parent is the home folder,
      which holds the default data directory, so every writing command refuses with ORQ-E105 and
      only an ORQLET_DATA_DIR outside home helps. This fails closed (no security loss), but it is
      an unintended refusal in a common Git layout. The design neither defines this case nor
      records it as accepted.
    needed: >
      Define the main work tree precisely. One option: the parent of the common folder only when
      that folder is named `.git`; otherwise compare with the common folder itself, or skip that
      target. Alternatively, record the over-refusal as accepted, with the bare-repository case
      named. Add the linked-worktree case to BC-19.

  - id: R6-F2
    severity: minor
    location: component.md section 6 (BC-19, BC-22); adr-007 Consequences
    evidence: >
      adr-007 line 42: "Each rule above has a criterion in the brief (BC-6, BC-7, BC-17 to
      BC-22), so a missing rule fails a test". New rules in decision 10: line 18 (empty variable
      counts as unset; main work tree compared), line 20 (Q-18: doctor, sync and explain report
      ORQ-E105 or ORQ-E106 as a finding, do not create the data directory, go on), line 22 (Q-19:
      the hook prints {} when the data directory lies in the project root it finds).
      component.md line 81 (BC-19) only says a data directory inside the repository "is refused";
      line 84 (BC-22) has the hook printing {} only for a panic.
    finding: >
      Q-18, Q-19, the main-work-tree comparison and the empty-variable rule have no acceptance
      criterion. A port that refuses in doctor, creates the data directory, or reads user data in
      the hook would pass every BC as written. That contradicts the claim in the Consequences
      section.
    needed: >
      Extend BC-19 (or add a criterion): doctor, sync and explain give the finding, leave the data
      directory uncreated and finish; the hook prints {}; a data directory in the main work tree
      of a linked worktree is refused; an empty ORQLET_DATA_DIR behaves as unset.

  - id: R6-F3
    severity: minor
    location: component.md section 5; views.md D-5; manifest.yaml EC-4 and EC-6
    evidence: >
      adr-007 line 19: writing commands refuse with "ORQ-E105, exit 3, or ORQ-E106 for the Vcs
      error". component.md line 54 gives only "ORQ-E105, exit 3"; views.md line 62 gives only
      "refuse, ORQ-E105". adr-007 line 27 says every reader of the journal folder (supersede step,
      doctor, sync, resume, rollback) reads only format and status of a 0.x record; manifest.yaml
      line 98 (EC-4) still says "before an upgrade only the format and status of each journal
      record are read". manifest.yaml line 115 (EC-6): "The data directory never lies inside the
      project root, the Git work tree or the main work tree: writing commands refuse ..., doctor,
      sync and explain report it, the hook prints {}". adr-007 line 22 (Q-19) limits the hook to
      the project root it finds, without Git.
    finding: >
      Four statements no longer match decision 10 and decision 11. EC-6 claims the hook enforces
      the Git work-tree target, which it cannot do without starting Git.
    needed: >
      Add ORQ-E106 to the failures row and to D-5. Make EC-4 say that every journal reader reads
      only format and status of a 0.x record. Make EC-6 say that the hook checks only the project
      root it finds (Q-19).
```

## Round-5 findings: are they resolved?

| Round-5 finding | Status | Note |
|---|---|---|
| R5-F1, the supersede step rewrites 0.x records | Resolved | ADR-007 lines 27-33, ADR-004 line 13 and BC-22 (line 84) cover a profile edit and doctor. Every reader of the journal folder reads format and status first and never rewrites a 0.x record. Any journalled apply refuses with ORQ-E131 on an open 0.x record. Doctor and sync report ORQ-E170 with the advice to use 0.5.2. Checked against `apply_plan.py` 55-56, `journal.py` 63-88 and 154-165, `diagnose.py` 398-409, and the six callers of `apply_plan` (search) |
| R5-F2, approved response not followed | Resolved | Q-18 and Q-19 are answered in the ledger (lines 349-392), and ADR-007 lines 20 and 22 follow them. The missing criteria are R6-F2 |
| R5-F3, Git failure during the check, `status` text | Resolved | Line 18: a Vcs error is not read as "no repository". Line 19 adds ORQ-E106. Line 21 describes `status` as a not-run entry, checked against `status.py` 43 and 228-229. Not updated in the brief and D-5: R6-F3 |
| R5-F4, stale texts | Resolved | ADR-003 line 44, manifest line 132, ADR-002 line 10 ("every rule of ADR-007 marked new"), ADR-001 line 10 and component line 36 (UTC timestamps) are all updated |
| SEC-D5-1, comparison targets | Resolved | The project root, the Git top level and the main work tree are all compared, and BC-19 has the Git-failure case. The definition of "main work tree" is R6-F1 |
| SEC-D5-2, unknown format or status | Resolved | ADR-007 line 27 and BC-22 |
| SEC-D5-3, `rollback --project-id` | Resolved | ADR-007 line 24 and BC-19. Checked against `lifecycle.py` 133-135 and `rollback.py` 49 |
| SEC-D5-4, Git's error output | Resolved per Q-20 | ADR-007 line 16 gives a fixed message, and EC-6 and BC-21 agree. The person chose "drop it" over the architect's "keep it, cleaned and cut", and the applied text follows the person. Checked against `git_runner.py` 132-136 and `vcs_git.py` 48-51 |
| SEC-D5-5, security globs | Resolved | Manifest lines 44-67 add `crates/orqlet-cli/src/**`, `upgrade.rs`, `apply_plan.rs`, `rollback.rs` and `diagnose.rs` |

## Observations (none blocking)

- **Where a non-upgrade command refuses.** In 0.5.2, `apply_plan` saves backups (lines 52-54) under the lock before the supersede step (lines 55-56). If 1.0.0 refuses with ORQ-E131 at that same step, it leaves backup files for a change that never started. The design does not say whether the 0.x check runs before the lock and the backups, as the upgrade guard does in D-5. It also does not give the exit status of the new refusal.
- **Doctor and sync with an unreadable record.** ADR-007 line 31 makes them refuse with ORQ-E136 and exit 3, which is 0.5.2 parity (`diagnose.py` 400 calls `open_changes`, which raises). Q-18's "report and go on" covers only the data directory.
- **Still left to the plan, not written in the design:** where the `projects/<id>/` check runs (D-5 shows the check only in the CLI, before the profile is loaded); how the panic test is triggered; whether a data directory in a superproject, outside the submodule that holds the project, counts as "inside the repository".
- **Two base revisions remain.** The manifest binds 3e3c311 (line 9); `as-is.md` binds 3196914 (lines 10 and 14).
- **Round-5 observations handled:** `xtask arch` now checks features (ADR-001 line 14); the journal read limit is 1 MiB (ADR-007 line 27); temporary-name retries stop at 100 (line 17); an empty `ORQLET_DATA_DIR` counts as unset (line 18, matching `wiring.py` 86).
- **ORQ codes keep their meaning.** ORQ-E105 is FileSystemError and ORQ-E106 is VcsError (`errors.py` 24-25); ORQ-E131 and ORQ-E170 match `upgrade.py` 84 and `diagnose.py` 403.
- **Citations new this round, checked in the working tree and accurate:** `wiring.py` 86, 89-93, 119-140, 158-162 and 200-223; `vcs_git.py` 48-51 and 66-84 (the method spans 62-83); `lifecycle.py` 133-135, 188, 203 and 243; `status.py` 43 and 228-229; `hook_event.py` 92-102 and 220-233; `rollback.py` 49; `journal.py` 30-34, 37-38, 63-88 and 154-165; `apply_plan.py` 55-56; `diagnose.py` 398-409; `upgrade.py` 80-88; `git_runner.py` 132-136; `errors.py` 19; `runner.py` 33-35; `vcs.py` 94-105.

```yaml
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: design, round: 6, task: rust-migration}
  model: "Claude Opus 5.5 (as named in this agent's configuration); fresh context, only the given paths and cited sources"
  revision: "branch and HEAD not confirmed (shell refused); working tree read, assumed equal to 3e3c311 for the cited lines"
  checks:
    - {what: SHA-256 of ten design files, how: shasum, result: "NOT_RUN (shell refused); 9 given values equal manifest artifact hashes; manifest's own hash not recorded, not checked"}
    - {what: round-5 findings R5-F1..F4 and SEC-D5-1..5, how: compared each applied response with current text and source, result: "all 9 resolved; residuals R6-F1..F3"}
    - {what: Q-1..Q-20 respected, how: ledger answers vs ADRs, result: "pass; Q-18, Q-19, Q-20 applied as answered"}
    - {what: cited source lines, how: read cited ranges, result: "pass"}
    - {what: journal readers in 0.5.2, how: searched open_changes, finish, apply_plan and stores callers, result: "all covered by ADR-007 decision 11"}
    - {what: cross-references and stale text, how: search across design set, result: "4 stale statements (R6-F3)"}
    - {what: "orqlet standards for, orqlet validate design/ledger, brief word count", result: NOT_RUN}
  unverified:
    - "Git's --git-common-dir output for bare and separate-git-dir repositories (R6-F1) was not looked up, by rule"
    - "Standards compared only with the rendered rule texts shown in this session"
    - "evidence/web files and as-is.md were not re-read in full this round"
    - "This review is an additional check, not a guarantee"
```

**Completed**
- Reviewed all ten design files against the ledger, the round-5 notes and the cited source.
- Found three minor findings (R6-F1 to R6-F3), none blocking or major.
- Confirmed that all nine round-5 findings are resolved. The hash computation and the orqlet commands did not run.

**Questions**
- R6-F1: should a data directory under the parent folder of a bare repository's common Git folder be refused, or should the main work tree be defined more narrowly?
- Should R6-F1 to R6-F3 be fixed before design approval, or carried into the plan as conditions?

**Next prompt**
```
Task: rust-migration
Next: architect answers R6-F1 to R6-F3 (orqlet-design); person decides on design approval
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/reviews/architecture-reviewer-design.md
Pending: decision on R6-F1; design approval by tmishari; plan approval
```

## Architect's responses

The design files are unchanged since the reviewer read them, so this note's hashes match the manifest. Below is the resolution I propose for each finding. None is applied yet; the person decides whether to apply them and whether another round follows.

- R6-F1: the main work tree is the parent of the common Git folder only when that folder is named `.git`. Otherwise, as for a bare repository or a separate Git folder, the common folder itself is compared, so the home folder is never a target. BC-19 gains a linked-worktree case.
- R6-F2: BC-19 gains these cases:
  - `doctor`, `sync` and `explain` report ORQ-E105, or ORQ-E106 when Git fails. They do not create the data directory and report no ORQ-E170 from a journal planted there.
  - The hook prints `{}`.
  - A data directory in the main work tree is refused.
  - An empty `ORQLET_DATA_DIR` behaves as unset.
- R6-F3: the failures row and view D-5 add ORQ-E106. EC-4 says that every journal reader reads only the format and status of a 0.x record. EC-6 says that the hook checks only the project root it finds (Q-19).
- Observations:
  - A journalled apply checks for an open 0.x record before it takes the lock and saves backups, as the upgrade guard does, and refuses with the exit status that `upgrade` gives ORQ-E131 in 0.5.2.
  - Doctor and sync keep 0.5.2's ORQ-E136 refusal for an unreadable record.
  - The plan places the `projects/<id>/` check after the profile is loaded, chooses the panic trigger, and treats a superproject as outside "the repository".

## Person's decision

On 2026-11-25 tmishari chose to apply the proposed fixes and run a seventh round with both reviewers. The fixes are applied in the round-7 design files; this note keeps its round-6 hashes.
