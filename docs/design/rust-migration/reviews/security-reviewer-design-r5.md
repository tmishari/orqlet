# Security review of the rust-migration design, round 5 (allowed by the person)

Reviewer: orqlet-security-reviewer subagent (7b13d4e4-18a1-4776-874a-4df1552a1420), fresh context, model named by the client as Claude Opus 5.5.
Earlier rounds: `security-reviewer-design-r2.md` to `-r4.md`. The person allowed this fifth round on 2026-11-25, after round 4.
Design file hashes of this round, given to the reviewer in its prompt:

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#56155ca7793af8d5429188b542cd2296dc0dc9988a8af91436baa2b98a0ab867
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#3d0aebd07c933fcc978784061538845c3ffa8a24eca00c5de48f393c6cd9a2fc
docs/design/rust-migration/design/adr-003-libraries.md#f4b69170d112606d68d884f70650d36e86355f111f20ec198d0b7b3a05716a62
docs/design/rust-migration/design/adr-004-version-and-hashes.md#665e92d1827143a74c0157659790d136c8db3aba8577e4c4d0c72d26515aa3bc
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#54835d937a3ef93f34ca9411d6b1d9da377cee3a9c918f4a639b98248c2e9c69
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#e3bd59b65704ae83e8b88157f9fbca0603eb35ec72f9aa236dec6017029ed9a1
docs/design/rust-migration/design/adr-007-security-controls.md#4732d82417d1d3d6410dc65cc34be029f4fc602d461232caf80068b2977b8097
docs/design/rust-migration/design/component.md#2d36bfeb8d43a21d6083fb92e44c7480c80a01547339f8ea6f11c040b69888a7
docs/design/rust-migration/design/manifest.yaml#af95ecf53b46783f335cec38aaf4749f861c3e2b0e2ce665337171ae0c36d6a4
docs/design/rust-migration/design/views.md#10359fef0c04cf3bf73b54d766eeda1f14b010dae86e11428cf1a80e7a6182e6
```

## Reviewer output (unchanged)

The round-5 security review is complete: there are no blocking or major problems, five minor findings, and all nine round-4 security findings are resolved.

**Hash comparison: not run.** The shell was refused in this session, so I could not hash the files, check the branch or HEAD, or run `orqlet standards for`. Two substitute checks:
- The ten values you gave are the same as the `sha256` values that `manifest.yaml` records for D-1 to D-5 and ADR-001 to ADR-007. `views.md` holds D-2 to D-5 under one hash.
- Nothing records a hash for the manifest itself, so `af95ec…` was not checked.

Neither check proves the file bytes match. For the standards, I read the SEC and SAFE rule texts in `.prompts/rules.yaml` and the rendered rule files instead.

All five findings are small gaps at the edges of controls that are now defined:
- **Data-directory check (Q-16):** it compares only against the top level that Git reports. It does not say what happens when Git fails.
- **Journal records:** `format` and `status` values outside the defined ones have no defined outcome.
- **`rollback --project-id`:** this second source of the project id skips the UUID rule.
- **Git error text:** Git's stderr still reaches messages, although the design claims no message quotes input.
- **Security globs:** they guess file names for modules the design never places.

## Findings (orqlet.finding/v1)

```yaml
findings:
  - id: SEC-D5-1
    severity: minor
    location: adr-007 decision 10; BC-19; views D-5
    evidence: >
      adr-007 line 18: the data directory is compared "with the real top level of the Git work tree
      that holds the project, taken from the Vcs port (vcs.py lines 94-100 and 113), or with the real
      project root when there is no repository". src/orqlet/adapters/git/vcs_git.py lines 68-83:
      worktree() returns None only when stderr says "not a git repository"; every other failure
      (Git missing, timeout, output cap, unexpected output) raises VcsError (lines 75, 79, 81).
      vcs_git.py lines 46-53: 0.5.2 already handles a top level that differs from the root (NESTED).
      vcs.py lines 102-105: a linked worktree has its own Git folder below the common one.
    finding: >
      The design does not say what the check does when the Vcs call fails for a reason other than
      "no repository". If an implementation treats that as "no repository" and falls back to the
      project root, it misses a data directory placed elsewhere in the work tree.
      The check also compares only against the Git top level. If Git reports a top level that does
      not contain the project root (for example a work tree set by local Git configuration), the
      project root itself is never compared.
      For a linked worktree, a data directory inside the main work tree of the same repository is
      not compared either. Q-16 says "inside the repository" and does not decide this case.
    needed: >
      Always compare with the real project root, and also with the Git top level when there is one.
      When the Vcs call fails for any reason other than "not a repository", a writing command
      refuses (ORQ-E105, or ORQ-E106 as for other Git failures) instead of falling back.
      Either add the main work tree of a linked worktree to the comparison, or record it as
      accepted. Add the Git-failure case to BC-19.

  - id: SEC-D5-2
    severity: minor
    location: adr-007 decision 11; adr-004 decision 5; BC-22
    evidence: >
      adr-007 line 19: records carry "format: orqlet-journal/1"; "a record without format is a 0.x
      record"; "complete, superseded and rolled-back records are ignored". journal.py line 209: 0.5.2
      casts status without checking it, and open_changes (lines 79-88) acts only on "open".
    finding: >
      The design defines three cases: format missing (0.x), format orqlet-journal/1 (1.0.0), and a
      record whose fields cannot be read (ORQ-E136). It does not cover a record whose format is
      another string, such as a later "orqlet-journal/2" or a hand-edited value. It does not cover a
      status outside the four known values either.
      An implementation could treat an unknown format as 1.0.0 and offer --resume or rollback with
      the wrong semantics. It could also ignore an unknown status and upgrade over an unfinished
      change. Both outcomes weaken the guard that SEC-D4-1 added.
    needed: >
      State that any format other than missing or "orqlet-journal/1", and any status outside open,
      complete, superseded and rolled-back, is an unreadable record (ORQ-E136, file named). Add both
      cases to BC-22.

  - id: SEC-D5-3
    severity: minor
    location: adr-007 decision 10 (project id rule); BC-19
    evidence: >
      adr-007 line 18: "the project id read from the profile must be a lowercase hyphenated UUID ...
      and is joined only through the confined data-directory FileSystem". src/orqlet/interface/cli/
      commands/lifecycle.py lines 133-134: rollback has a --project-id option ("The project id, when
      the profile is gone"). src/orqlet/application/usecases/rollback.py line 49: options.project_id
      takes precedence over the profile.
    finding: >
      The rule and the confined join are written for the profile id only. The rollback option is a
      second source that chooses the folder of journals, backups and the apply lock. As written, it
      is not held to the UUID rule.
    needed: >
      Apply the UUID rule and the confined join to every source of the project id, the rollback
      option included. Add the case to BC-19.

  - id: SEC-D5-4
    severity: minor
    location: adr-007 decision 8; EC-6 ("no message quotes an input value")
    evidence: >
      src/orqlet/adapters/git/git_runner.py lines 132-136: a failed Git call raises VcsError with the
      first line of Git's stderr. vcs_git.py lines 48-51 do the same for rev-parse.
      src/orqlet/interface/cli/runner.py line 33: an OrqletError message is printed as is
      (ORQ-E106, errors.py line 25). adr-007 line 16 covers library errors, credential checks and
      refusals, but says nothing about Git's own error text.
    finding: >
      Git's stderr can repeat repository-controlled text, such as a path, a ref or a config file
      name, including control characters, which then reach the terminal. EC-6 says no message
      quotes an input value. Decision 8 neither carries the 0.5.2 pass-through over nor removes it,
      so the absolute claim and the likely port disagree.
    needed: >
      Decide whether Git's stderr reaches messages. If it does, state that control characters are
      removed and the length is bounded, and list it as an exception to the "never echo" rule. If
      it does not, mark the change as new and give the fixed message. Add the case to BC-21.

  - id: SEC-D5-5
    severity: minor
    location: manifest.yaml extractor_config.security_globs (lines 44-66); component §4
    evidence: >
      The globs name crates/orqlet-cli/src/main.rs, wiring.rs, wiring/**, hook.rs and two use-case
      files. In 0.5.2, the ORQ-E900 text and the error-to-code mapping live in runner.py lines 29-35
      and errors.py lines 16-27. The open-journal guard lives in the upgrade use case
      (upgrade.py lines 80-92), and the project-id source in rollback.py line 49. Neither the brief
      §4 nor ADR-007 says which 1.0.0 module holds the Q-16 check, the journal guard or the
      panic-to-ORQ-E900 handler.
    finding: >
      If these controls land in, for example, crates/orqlet-cli/src/runner.rs or
      crates/orqlet-application/src/usecases/upgrade.rs or rollback.rs, a change to them does not
      trigger security review. The globs depend on file names that the design does not fix.
    needed: >
      Name the module that holds each of the Q-16 check, the journal format and status guard, the
      project-id rule and the panic-to-ORQ-E900 handling, and add those paths to security_globs.
      Alternatively, cover crates/orqlet-cli/src/** as a whole.
```

## Round-4 security findings

| Round-4 finding | Status | What remains |
|---|---|---|
| SEC-D4-1, journal folder and 0.x records | **Resolved.** The guard now reads `projects/<uuid>/upgrade/`, which matches `journal.py` lines 3-7 and 43. 1.0.0 records carry a `format` field. An open 0.x record gives ORQ-E131 with advice that names 0.5.2. A record that cannot be read, or a 0.x resume or rollback, gives ORQ-E136. This is consistent across ADR-007 decision 11, ADR-004 decision 5, EC-4, EC-6, the failures table, BC-22 and view D-5. | Unknown format or status values: SEC-D5-2 |
| SEC-D4-2, defining the data-directory check | **Resolved.** The check resolves the deepest existing ancestor, refuses `.` and `..` in the missing parts, compares real paths component by component and ignores case on macOS and Windows. It covers `projects/<id>/` and `packets/`, and BC-19 has the missing-folder-under-a-link case. | Comparison target and Git failures: SEC-D5-1 |
| SEC-D4-3, project id | **Resolved for the profile id.** The id must be a lowercase UUID, joined only through the confined file system, and BC-19 covers it. | The `rollback --project-id` option: SEC-D5-3 |
| SEC-D4-4, project-write modes | **Resolved.** Decision 9 creates the temporary file 0600 and gives it the target's mode, or 0644 for a new file, matching `local_fs.py` lines 126-143. BC-19 and EC-6 cover it. | — |
| SEC-D4-5, panic output | **Resolved.** Decision 12 installs a silent panic hook for every command, ORQ-E900 has a fixed text, and the failures table and BC-22 cover it. Matches `runner.py` lines 34-35. | — |
| SEC-D4-6, oversized YAML numbers | **Resolved.** Decision 3 is marked new, and BC-6 and EC-6 cover it. | — |
| SEC-D4-7, security globs | **Resolved for the items named.** `wiring.rs`, `wiring/**`, `main.rs`, `resources_source.rs` and `integrations_source.rs` are in the globs, and `.cargo/**` is in the scope (manifest line 26). | Unplaced control modules: SEC-D5-5 |
| SEC-D4-8, stale cross-references | **Resolved.** ADR-001 decisions 1 and 6, ADR-003 and ADR-006 decision 2 now point to the right decisions (13, 14, 14, 13). The SEC-001 text names the private child of the Git module. | — |
| SEC-D4-9, views | **Resolved.** D-2 shows packets, D-4 shows the generic tree, and D-5 shows the Q-16 refusal and the journal scan before the lock, in the same order as `upgrade.py` line 80. | — |

## Observations (none blocking)

- **ADR-007 citations checked against the working tree:** decision 10 (wiring.py lines 89-93, 96-116, 119-140, 143-150, 158-162 and 200-223; vcs.py lines 94-100 and 113; journal.py lines 30-34 and 37-38), decision 11 (journal.py lines 3-7, 41-44, 63-88 and 154-165; upgrade.py lines 80-88; errors.py line 19; runner.py line 33), decision 12 (runner.py lines 34-35, hook.py lines 38-48, wiring.py line 52), decision 9 (local_fs.py lines 126-143), and ADR-003's system.py lines 9-11 and 14-16. All are accurate.
- **The new-rules list in ADR-002 decision 2 is incomplete.** Its list in brackets leaves out UUID-only project ids, the unknown-key and duplicate-key wording, and the ORQ-E105 refusal and `status` report. The general clause "the rules of ADR-007 marked new" covers them.
- **Copied project ids are still shared.** Two repositories with the same profile UUID, for example copied from a template, still share journals, backups and the apply lock. This is 0.5.2 behaviour, and the UUID rule does not change it. It was not in round 4's "needed".
- **Umask and creation modes.** Data-directory modes are set at creation, so a umask can only clear bits. 0.5.2 sets 0700 again after creating a folder (`local_fs.py` lines 212-213). The result can only be stricter, so the risk is that a write fails, not a security risk.
- **The hook skips the Q-16 check.** From a data directory inside the repository, the hook would read a planted user manifest. The manifest only produces a missing, newer or outdated state (`status.py` lines 241-258); no free text from it reaches `additionalContext`. Low risk.
- **Journal size.** The strict JSON 1 MiB limit applies to journal reads, so a very large change could write a record that the guard then refuses with ORQ-E136. This affects availability only.
- **Unbounded retries.** Retries on an existing temporary name have no stated limit.
- **Empty data-directory variable.** 0.5.2 treats an empty `ORQLET_DATA_DIR` as unset (`wiring.py` line 86). The design does not say. An empty value would most likely resolve to the current folder and be refused, which fails closed but differs from 0.5.2.
- **Changes that help security:** the Q-16 refusal, UUID-only ids, 0600 temporary files, silent panics everywhere, range checks on YAML and JSON numbers, the apply lock through the confined file system, `uuid` (v4 only) with `Cargo.lock` under the globs, and no timestamp crate.
- In the files I read I found no secrets, no MD5 or SHA-1, and no language-model SDK.

## Self-check

```yaml
schema: orqlet.self-check/v1
checked_against:
  role: security-reviewer
  phase: design
  round: 5
  model: "Claude Opus 5.5 (as named by the client); fresh context, no Architect conversation"
  revision: "working tree of /Users/tmishari/Documents/orqlet; branch and HEAD not confirmed (shell refused); source assumed equal to 3e3c311"
checks:
  - {what: SHA-256 of the ten design files, how: shasum with CRLF read as LF, result: "NOT_RUN (shell refused)"}
  - {what: given hashes vs manifest artifact hashes, how: "read manifest.yaml lines 116-128", result: "equal for nine values (views.md shared by D-2 to D-5); the manifest's own hash is not recorded, not checked"}
  - {what: orqlet standards for, how: "shell", result: "NOT_RUN; read .prompts/rules.yaml SEC and SAFE texts and the rendered rule files instead"}
  - {what: "design set (manifest, brief, views, ADR-001 to ADR-007), ledger Q-1 to Q-17, security-reviewer-design-r4.md, the start of architecture-reviewer-design-r4.md", how: read, result: done}
  - {what: round-4 SEC-D4 resolutions, how: "compared each 'needed' with the current text", result: "9 resolved; residuals in SEC-D5-1, -2, -3 and -5"}
  - {what: "citations new in this round", how: "read journal.py, wiring.py, local_fs.py 1-220, runner.py, errors.py, hook.py 25-48, rollback.py 30-124, upgrade.py 60-109, vcs_git.py 30-89, git_runner.py 110-137, vcs.py 85-124, yaml_loader.py 27-76, status.py 215-259, system.py, lifecycle.py (search)", result: "accurate; gaps in SEC-D5-1 to SEC-D5-5"}
unverified:
  - "as-is.md, the evidence/web files, architecture-reviewer r1-r3 and security-reviewer r2-r3 were not re-read this round."
  - "Library and platform behaviour (uuid features, macOS realpath, Clippy) was not looked up, by rule."
  - "orqlet validate design / ledger were not run."
  - "This review is an additional check, not a guarantee."
```

**Completed**
- Reviewed the round-5 design set: five minor findings, none blocking or major.
- Checked the nine round-4 security findings: all resolved, with small leftovers in four of them.
- The hash comparison and `orqlet standards for` were not run, because the shell was refused. The given hashes match the manifest's recorded values.

**Questions**
- Do you want SEC-D5-1 to SEC-D5-5 fixed before you approve the design, or carried into the plan as conditions?
- Should a data directory inside the main work tree of a linked worktree count as "inside the repository" for Q-16?

**Next prompt**
```
Task: rust-migration
Next action: architect answers SEC-D5-1 to SEC-D5-5; person decides on design approval
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/questions.yaml, docs/design/rust-migration/reviews/
Pending approvals: design approval by tmishari; plan approval
```

## Architect's responses

The design files are unchanged since the reviewer read them, so this note's hashes match the manifest. Below is the resolution I propose for each finding. None is applied yet; the person decides whether to apply them and whether another round follows.

- SEC-D5-1: the check always compares with the real project root, and also with the Git top level when there is one. A Vcs error other than "not a repository" makes a writing command refuse with ORQ-E106 (`vcs_git.py` lines 68-83). For a linked worktree, the main work tree (the folder that holds the common Git folder) is compared as well, which matches Q-16's "repository". BC-19 gains the Git-failure case.
- SEC-D5-2: any `format` other than missing or `orqlet-journal/1`, and any `status` outside open, complete, superseded and rolled-back, makes the record unreadable: ORQ-E136, with the file named. BC-22 gains both cases.
- SEC-D5-3: the UUID rule and the confined join apply to every source of the project id, the `rollback --project-id` option included (`rollback.py` line 49). BC-19 gains the case.
- SEC-D5-4: the first line of Git's stderr still reaches the ORQ-E106 message, as in 0.5.2 (`git_runner.py` lines 132-136), because it is the person's only clue to a Git failure. Control characters are replaced and the text is cut to 200 characters (new). It is listed in decision 8 as the one exception to the "never echo" rule, and BC-21 gains the case.
- SEC-D5-5: the security globs cover all of `crates/orqlet-cli/src/**`, plus the application modules that hold the journal guard, the supersede step and the project-id rule (`usecases/upgrade.rs`, `usecases/apply_plan.rs`, `usecases/rollback.rs`).
- Observations: an empty `ORQLET_DATA_DIR` is treated as unset, as in 0.5.2 (`wiring.py` line 86). Temporary-name retries stop after 100 attempts. Copied project ids stay 0.5.2 behaviour, and the release notes mention it.

## Person's decision

On 2026-11-25 tmishari chose to apply the proposed fixes and run a sixth round with both reviewers. For the open choices, recorded as Q-18 to Q-20: doctor, sync and explain report a finding and go on; the hook prints {} when the data directory lies inside the project root it finds; a failed Git call gets a fixed message without Git's error output. The fixes are applied in the round-6 design files; this note keeps its round-5 hashes.
