# Architecture review of the rust-migration design, round 5 (allowed by the person)

Reviewer: orqlet-arch-reviewer subagent (22afec41-afdc-4e63-bd79-1a9d235e9e82), fresh context, model named as Claude Opus 5.5.
Earlier rounds: `architecture-reviewer-design-r1.md` to `-r4.md`. The person allowed this fifth round on 2026-11-25, after round 4.
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

I found no blocking findings, but the design is not ready for approval: there is one major finding and three minor ones. All 15 round-4 findings (R4-F1 to R4-F6 and SEC-D4-1 to SEC-D4-9) are resolved in the text. The major finding is a new gap next to R4-F1: the guard for old 0.5.2 journals is defined only for `upgrade`. In 0.5.2, every other command that writes through a change plan marks open journals as "superseded" and rewrites them, and nothing in the design stops 1.0.0 from doing the same to a 0.x record.

**Checks not run.** The shell was refused in this mode, so I could not compute the SHA-256 values, confirm the branch or HEAD, or run `orqlet standards for` or `orqlet validate design`. Instead I compared the ten values you gave with the `sha256` values in `manifest.yaml`. The nine artifact hashes match. Nothing records the manifest's own hash (`af95ec…`), so it was not checked. A match with the manifest does not prove the file bytes match. I read the working tree, not 3e3c311.

## Findings (orqlet.finding/v1)

```yaml
findings:
  - id: R5-F1
    severity: major
    location: adr-007 decision 11; adr-004 decision 5; component §5 row "Open journal"; BC-22; EC-4; EC-6
    evidence: >
      ADR-007 line 19 and ADR-004 line 13 define the 0.x handling only "Before an upgrade",
      plus a refusal of resume and rollback. In 0.5.2, src/orqlet/application/usecases/apply_plan.py
      lines 55-56 run "for earlier in journal.open_changes(): journal.finish(earlier, "superseded")"
      inside every journalled apply. The approved AS-IS fact A-25 cites lines 49-65, which include them.
      apply_plan is called by init_project.py 220, upgrade.py 206, rollback.py 93, release.py 90,
      profile_edit.py 179 and resources_edit.py 417. journal.py lines 63-68 and 102-103: finish()
      decodes the whole record (lines 70-77) and writes it again through _encode (lines 154-165).
      In 1.0.0 _encode adds "format: orqlet-journal/1" (ADR-007 d11).
      diagnose.py lines 398-409: doctor and sync report every open change as ORQ-E170 with the
      advice "orqlet upgrade --resume" or "orqlet rollback <id>".
      BC-22 (component.md line 87) tests only upgrade and rollback.
    finding: >
      If ported as written, five commands would mark an open 0.5.2 record "superseded" and stamp
      it with the 1.0.0 format field: `init`, `profile` edits, `resources` edits, `release` and the
      rollback of a 1.0.0 change. The record would then no longer be recognisable as 0.x, and the
      upgrade guard skips superseded records. The half-applied 0.5.2 change, which R4-F1 and
      SEC-D4-1 were meant to protect, would become invisible again. Doctor and sync would give, for
      a 0.x record, advice that 1.0.0 itself refuses (ORQ-E136). The design never says whether
      these paths read only `format` and `status`, or whether they may rewrite a 0.x record.
    needed: >
      State that every 1.0.0 path that reads the journal folder reads `format` and `status` first
      and never rewrites a 0.x record. These paths are: the upgrade guard, the supersede step of
      every journalled apply, doctor and sync, resume, and rollback. Decide what a journalled apply
      does when an open 0.x record exists, for example refuse with ORQ-E131 and the 0.5.2 advice,
      marked new. Decide what doctor and sync report for it. Extend BC-22 with one command other
      than upgrade (for example a profile edit) and with doctor.

  - id: R5-F2
    severity: minor
    location: adr-007 decision 10 (result per command)
    evidence: >
      reviews/architecture-reviewer-design-r4.md line 232, the R4-F5 response that the person
      chose to apply (line 239): "The read-only commands status, doctor, sync and explain report a
      finding and treat the data as missing. The hook prints {}."
      ADR-007 line 18 instead says: "every command wired with the lifecycle services and review
      prepare ... refuses with ORQ-E105 ... The hook does not run the check."
      commands/lifecycle.py lines 192-209 and 233-246: doctor, sync and explain are wired with
      build_init_services, so under decision 10 they refuse.
    finding: >
      The applied text differs from the response the person approved in two places. Doctor, sync
      and explain now refuse with exit 3 instead of reporting a finding. The hook skips the check
      instead of printing {}. Both choices are coherent and the hook only reads, but the person's
      recorded decision says otherwise.
    needed: >
      Either have the person confirm the applied behaviour, recorded in the ledger or the review
      note, or align decision 10 with the approved response.

  - id: R5-F3
    severity: minor
    location: adr-007 decision 10; BC-19
    evidence: >
      ADR-007 line 18: the comparison uses "the real top level of the Git work tree ... taken from
      the Vcs port ..., or with the real project root when there is no repository". A Git failure
      raises VcsError (ORQ-E106, errors.py line 25), while vcs.py lines 113-115 return None only
      outside a repository. The same line says status "already reports [an unreadable data
      directory] as a finding (lines 96-116 and 143-150)". In fact status.py lines 43 and 228-229
      add a not-run entry, "the user manifest could not be read", not a finding.
    finding: >
      The design does not say what happens when the Vcs call fails during the check. If an
      implementation treats a Git error as "no repository", it compares against the project root
      only. For a project in a subfolder, that accepts a data directory elsewhere in the same
      repository, which Q-16 refuses. The status result is also described inaccurately, and the
      person is never told why the data could not be read.
    needed: >
      State that a Vcs error during the check refuses the writing commands, and what status shows
      in that case. Describe the status result as a not-run entry, or define a message that names
      the reason.

  - id: R5-F4
    severity: minor
    location: adr-003 Consequences; manifest considerations.compatibility; adr-002 decision 2; adr-001 decision 2; component §4
    evidence: >
      ADR-003 line 44: "0.x journals are ignored either way (ADR-004)".
      manifest.yaml line 131: "0.x journals not read (ADR-004)".
      ADR-004 d5 and ADR-007 d11 now read the format and status of 0.x records.
      ADR-002 line 10 (unchanged since round 4) lists the new rules as "... the data directory
      inside a project". It leaves out the UUID-only project id, and Q-16 is now applied to the
      Git work tree.
      ADR-003 line 20 puts a timestamp formatter in the domain. ADR-001 line 10 and component.md
      line 36 list the domain's contents without it.
    finding: >
      Texts that this round's changes made wrong were not updated.
    needed: >
      Correct the two journal statements. Update the ADR-002 list of new rules, or refer to ADR-007
      as a whole. Add the timestamp formatter to the domain list and to the component box.
```

## Round-4 findings: are they resolved?

| Round-4 finding | Status | Note |
|---|---|---|
| R4-F1 journal folder | Resolved | ADR-007 d11, ADR-004 d5 and BC-22 use `projects/<uuid>/upgrade/`, the `format` field and the 0.5.2 record shape. Checked against `journal.py` lines 3-7, 41-44 and 154-165. The gap in other commands is new: R5-F1 |
| R4-F2 ids and timestamps | Resolved | `uuid` (v4 only) is in ADR-001 d6, ADR-003 and EC-5, as Q-17 allows. Timestamps use `SystemTime` plus a domain formatter. Checked against `system.py` lines 9-16. The domain list is stale: R5-F4 |
| R4-F3 views | Resolved | D-2 shows packets, D-3 has the three edges, D-4 shows the generic tree, D-5 has both pre-checks |
| R4-F4 stale texts | Resolved | ADR-003 says three crates; the SEC-001 text describes the private child module |
| R4-F5 Q-16 scope | Resolved in substance | The check covers the Git work tree, with a defined algorithm. Deviation from the approved response: R5-F2. Missing failure handling: R5-F3 |
| R4-F6 key names | Resolved | Both rules are marked new. Checked against `loading.py` line 24, `yaml_loader.py` line 69 and `strict_json.py` line 46 |
| SEC-D4-1 | Resolved | Same as R4-F1; see also R5-F1 |
| SEC-D4-2 | Resolved | Deepest existing ancestor, no `.` or `..`, case-insensitive comparison, sub-folders checked, BC-19 |
| SEC-D4-3 | Resolved | UUID-only id, joined only through the confined file system, BC-19 |
| SEC-D4-4 | Resolved | ADR-007 d9 and BC-19. Checked against `local_fs.py` lines 126-143 |
| SEC-D4-5 | Resolved | ADR-007 d12 and BC-22 |
| SEC-D4-6 | Resolved | ADR-007 d3 and BC-6 |
| SEC-D4-7 | Resolved | `wiring.rs`, `wiring/**`, `main.rs` and the two use-case modules are in the globs; `.cargo/**` is in scope |
| SEC-D4-8 | Resolved | All cross-references to ADR-007 decisions checked by search |
| SEC-D4-9 | Resolved | Same as R4-F3 |

## Observations (non-blocking)

- **Feature limits are not enforced by any named check.** "uuid feature v4 only" and "domain crates without default features" are stated in the allow-lists, but ADR-001 d6 describes `xtask arch` as checking crate names only.
- **Where the `projects/<project id>/` part of the data-directory check runs.** It needs the id from the profile, but D-5 runs the check in the CLI before the use case loads the profile. The plan should place it.
- **Journal edge cases are open.** The design does not say what happens with an unknown `format` value (for example `orqlet-journal/2`), or which size limit applies when a journal is read.
- **Submodules and linked worktrees.** A data directory in a superproject, outside the submodule that holds the project, is accepted. That is a narrow reading of Q-16's "repository".
- **Panic test.** BC-22 needs some way to trigger a panic in the shipped binary. The plan has to choose one.
- **Two base revisions remain.** The manifest binds 3e3c311 and the AS-IS file binds 3196914.
- **Citations checked in the working tree, all accurate:**
  - `journal.py` (whole file)
  - `wiring.py` 52, 83-93, 96-116, 119-140, 143-150, 158-162, 200-223
  - `vcs.py` 28-56, 94-100, 113
  - `errors.py` 19
  - `runner.py` 33-35
  - `upgrade.py` 78-92
  - `system.py` 9-16
  - `local_fs.py` 126-143
  - `yaml_loader.py` 36-49, 69
  - `loading.py` 24
  - `strict_json.py` 46
  - `hook.py` 38-48
  - `status.py` 224-243
  - `hook_event.py` 242-251
  - `rollback.py` 49-104

```yaml
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: design, round: 5}
  model: "Claude Opus 5.5 (as named in this agent's configuration); fresh context, only the given paths and cited sources"
  revision: "branch rust-migration-design and HEAD not confirmed (shell refused); working tree read, assumed equal to 3e3c311 for cited lines"
  checks:
    - {what: SHA-256 of ten design files, how: shasum, result: "NOT_RUN (shell refused); 9 artifact values equal the manifest; manifest hash unrecorded"}
    - {what: round-4 findings R4-F1..F6 and SEC-D4-1..9, how: compared each applied resolution with current text and source, result: "all resolved; new adjacent gaps R5-F1..F3"}
    - {what: Q-1..Q-17 respected, how: ledger answers vs ADRs, result: "pass; Q-16 applied, deviation from approved R4-F5 response (R5-F2)"}
    - {what: cited source lines, how: read cited ranges, result: "pass; status result mis-described (R5-F3)"}
    - {what: journal readers in 0.5.2, how: searched open_changes and apply_plan callers, result: "supersede path not covered (R5-F1)"}
    - {what: cross-references and stale text, how: search across design set, result: "references correct; stale statements (R5-F4)"}
    - {what: "orqlet standards for, orqlet validate design, brief word count", result: NOT_RUN}
  unverified:
    - "Line numbers at 3e3c311 itself"
    - "Standards compared only with the generated rule texts shown in this session, not with command output"
    - "This review is an additional check, not a guarantee"
```

**Completed**
- Reviewed all ten design files against the AS-IS file, the ledger, the round-4 notes and the cited source.
- Found R5-F1 (major) and R5-F2 to R5-F4 (minor), with no blocking finding.
- Confirmed that all round-4 architecture and security findings are resolved.

**Questions**
- R5-F1: when an open 0.x record exists, should a command other than upgrade that writes through a change plan refuse (new behaviour), or leave the record untouched and go on?
- R5-F2: does tmishari accept that doctor, sync and explain refuse with ORQ-E105, and that the hook skips the check?

**Next prompt**
```
Task: rust-migration
Next: architect revises the design for R5-F1 to R5-F4 (orqlet-design); person decides on approval or a further round
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/reviews/architecture-reviewer-design.md
Pending: person's decision on R5-F2; design approval by tmishari; plan approval
```

## Architect's responses

The design files are unchanged since the reviewer read them, so this note's hashes match the manifest. Below is the resolution I propose for each finding. None is applied yet; the person decides whether to apply them and whether another round follows.

- R5-F1 (open, major): every 1.0.0 path that reads the journal folder reads `format` and `status` first and never rewrites a 0.x record. These paths are the upgrade guard, the supersede step of every journalled apply (`apply_plan.py` lines 55-56), doctor and sync, resume, and rollback. When an open 0.x record exists, every journalled apply refuses with ORQ-E131 and the advice to finish or roll back with 0.5.2. This is new: 0.5.2 marked such a record superseded. Open 1.0.0 records are superseded as in 0.5.2. Doctor and sync report an open 0.x record as ORQ-E170 with the same 0.5.2 advice (`diagnose.py` lines 398-409). BC-22 gains a profile edit and doctor.
- R5-F2 (open, the person decides): this is my deviation from the approved R4-F5 response. In 0.5.2, doctor, sync and explain are wired with the lifecycle services, which create the data directory (`wiring.py` lines 89-93 and 200-223), so I applied a refusal for them. I applied a skipped check for the hook, because it starts no Git (lines 119-140). The person either confirms the applied behaviour or has decision 10 aligned with the approved response.
- R5-F3: the check always compares with the real project root, and also with the Git top level when there is one. A Vcs error other than "not a repository" makes a writing command refuse with ORQ-E106, as other Git failures do (`vcs_git.py` lines 68-83). `status` shows its existing not-run entry for user data (`status.py` lines 43 and 228-229); the text no longer calls it a finding.
- R5-F4: correct ADR-003 and the manifest's compatibility note (0.x journals are read for their format and status only). ADR-002 refers to "the rules of ADR-007 marked new" as a whole. The timestamp formatter joins the domain list in ADR-001 decision 2 and in the brief's component box.
- Observations: `xtask arch` also checks the enabled features of `uuid` and of the domain crates, read from `cargo metadata`. An unknown `format` or `status` value is an unreadable record (security finding SEC-D5-2). The journal read limit is 1 MiB, as for strict JSON. The plan places the `projects/<project id>/` check in the use case, after the profile is loaded, and chooses how the panic test is triggered.

## Person's decision

On 2026-11-25 tmishari chose to apply the proposed fixes and run a sixth round with both reviewers. For the open choices, recorded as Q-18 to Q-20: doctor, sync and explain report a finding and go on; the hook prints {} when the data directory lies inside the project root it finds; a failed Git call gets a fixed message without Git's error output. The fixes are applied in the round-6 design files; this note keeps its round-5 hashes.
