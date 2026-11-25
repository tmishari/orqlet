# Architecture review of the rust-migration design, round 4 (extra round allowed by the person)

Reviewer: orqlet-arch-reviewer subagent (77243635-ede8-410c-8b50-dcfb378acf9a), fresh context, model named as Claude Opus 5.5.
Earlier rounds: `architecture-reviewer-design-r1.md`, `-r2.md`, `-r3.md`. The person allowed this fourth round on 2026-11-25, after round 3.
Design file hashes of this round, given to the reviewer in its prompt:

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#014f74fa71a011aa3814db48ffe76956755d7955228fed1c25e2cab0fc648079
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#3d0aebd07c933fcc978784061538845c3ffa8a24eca00c5de48f393c6cd9a2fc
docs/design/rust-migration/design/adr-003-libraries.md#a5ea7d8a9d44da620f8611fcb962332fa6f34c5cc4fd7f7ceb4dc16c99a7256f
docs/design/rust-migration/design/adr-004-version-and-hashes.md#06e3d0795482e66842791fea2a23d24938f11579283ef4d2a0ecb829be9e679a
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#54835d937a3ef93f34ca9411d6b1d9da377cee3a9c918f4a639b98248c2e9c69
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#9a5d575293e89944bae5d8cb01ac24b578bf08c880d5654d330ce4b509862405
docs/design/rust-migration/design/adr-007-security-controls.md#1c6afd81699860028cd4904ff44b22912d74ad9d9213ff99382231cb8df96cd2
docs/design/rust-migration/design/component.md#bc8ce5700719d1f8ffc89c92fe06a6d9bac586ef0524e6ffd4d1dbc9539a14cc
docs/design/rust-migration/design/views.md#5f43dc02c6a723966a82f29797a0da28fb04005bf5a8e85e43cbc742fb598601
docs/design/rust-migration/design/manifest.yaml#7ce94708df60d11bae6a84bf458403fcc6e587099df60e87d12dd4390e8fa9e1
```

## Reviewer output (unchanged)

The design is not ready for approval yet. I found no blocking findings, but two major and four minor ones. Most of the round-3 findings are resolved; two are only partly resolved because of the first major finding below.

**Hash comparison: not run.** The shell was refused in this session. All ten hashes you gave match the `sha256` values recorded in `manifest.yaml`. The manifest's own hash (`7ce947…`) is not recorded anywhere, so I could not check it. Matching the manifest does not prove the file bytes match. `views.md` and ADR-005 still carry their round-3 hashes, so they did not change in this round.

### Findings (orqlet.finding/v1)

```yaml
findings:
  - id: R4-F1
    severity: major
    location: adr-007 decision 11; adr-004 decision 5; component §5 rows "Open journal" and "Unreadable journal or 0.x rollback"; BC-22
    evidence: >
      ADR-007 d11: "1.0.0 reads only the status field of each journal file under
      projects/<project id>/journal/ of its own data directory ... whichever version wrote it".
      src/orqlet/adapters/fs/journal.py lines 3-7: "A project change lives below projects/<project-id>/:
      upgrade/<change-id>.json"; line 44: self._dir = _project_dir(project_id).child("upgrade").
      Only the unported user scope uses a "journal" folder (line 50, user/journal). The project id is
      profile.project.uuid (upgrade.py line 78), so 1.0.0 reaches the same projects/<uuid>/ folder.
      journal.py _encode (lines 154-165) writes no version field. ADR-004 d5: "orqlet rollback of a
      0.x change id is refused as a journal error, ORQ-E136".
    finding: >
      The pre-upgrade guard reads a folder that 0.5.2 never writes. An open 0.5.2 change is not seen,
      so the round-3 fix (refuse on open, ORQ-E131) does nothing for exactly the journals it was
      written for. The design also never says where or in what format 1.0.0 writes its own journals.
      Two outcomes are possible. If 1.0.0 writes to upgrade/, the guard must read upgrade/. If it
      writes to journal/, nothing in the design reads upgrade/. In both cases, nothing defines how
      `rollback` tells a 0.x change id from a 1.0.0 one, because the record has no version field.
      BC-22 does not require that the journal under test was written by 0.5.2, so it can pass while
      the defect stays.
    needed: >
      State the 1.0.0 journal folder and format, and name the folder the status check reads
      (projects/<uuid>/upgrade/ for 0.5.2 journals). Define how a 0.x journal is recognised for the
      rollback refusal, or drop that claim. Make BC-22 use one completed and one open journal in the
      0.5.2 layout and format.

  - id: R4-F2
    severity: major
    location: adr-001 decision 6 (exact allow-lists); adr-003 decision table; EC-5
    evidence: >
      src/orqlet/adapters/system.py lines 9-16: SystemClock returns datetime.now(UTC) and
      UuidGenerator returns str(uuid.uuid4()). services.ids.new_id() makes project ids
      (init_project.py line 375) and change ids (upgrade.py 205, init_project.py 219, rollback.py 92,
      release.py 89, profile_edit.py 178, resources_edit.py 416). clock.now().isoformat() writes
      journal created_at (apply_plan.py line 62) and reviewed_at and retrieved_at timestamps;
      validate_model_policy.py line 431 compares retirement dates with today's UTC date. ADR-001 d6
      and EC-5 list every runtime crate "exact per crate", and none provides randomness, UUIDs or
      calendar formatting. ADR-007 d9 avoids randomness for temporary names (process id plus a
      counter), but nothing covers ids.
    finding: >
      Behaviour that ships must generate unique random ids and ISO-8601 UTC timestamps. The approved
      allow-lists leave no crate for either, and no ADR decides how to do it without one. The plan
      would have to change an approved, security-reviewed allow-list or invent its own entropy source
      (unsafe code is forbidden and Windows has no /dev/urandom). A colliding change id makes start()
      refuse with "already has a journal". A colliding project id merges two projects' journals and
      apply locks.
    needed: >
      Decide in ADR-003, and in the allow-lists of ADR-001 d6 and EC-5, how ids and timestamps are
      made: a named crate on a named allow-list, or a stated standard-library method with its
      uniqueness argument. Keep the id format that the existing profile and journal readers accept.

  - id: R4-F3
    severity: minor
    location: views.md (D-3 container, D-4 data flow, D-5 sequence)
    evidence: >
      views.md has the same hash as in round 3 (5f43dc…). D-4: "strict YAML loader (serde-saphyr)" leads
      straight to "serde contract", while ADR-007 d3 and ADR-003 now go through a generic tree in the
      documents module. D-5 has no data-directory-inside-project refusal (ADR-007 d10, ORQ-E105) and no
      journal status check before planning (d11; upgrade.py lines 80-92 run it before any render).
      The D-3 container view lacks the cli→domain, adapters→domain and xtask→domain edges, which
      component.md and ADR-001 d6 allow.
    finding: The views still describe the round-3 decisions, so a reader of the views alone sees the parse path that round 3 rejected.
    needed: Redraw D-4 with the documents module and the generic tree, add both pre-checks to D-5, and add the three edges to D-3.

  - id: R4-F4
    severity: minor
    location: adr-003 Consequences bullet 4; adr-006 decision 1, SEC-001 row
    evidence: >
      ADR-003: "keeps the domain allow-list at two crates". ADR-001 d6 and ADR-007 Consequences list
      three crates (sha2, unicode-normalization, the category crate). ADR-006 SEC-001 text: "Only the
      crate-private process module, used by GitRunner alone". ADR-001 d4 and ADR-007 d1 make it "a
      private child of the Git module".
    finding: >
      Two texts were not updated with the round-3 changes. The SEC-001 one matters most: it is the
      standard that gets rendered into the IDE rules, and it would describe the visibility that
      round 3 rejected.
    needed: Change the ADR-003 text to three crates, and the SEC-001 text to "the process module, a private child of the Git module".

  - id: R4-F5
    severity: minor
    location: adr-007 decision 10; R-11; component §5 row "Data directory inside the project"; BC-19
    evidence: >
      Q-16 text and answer: "inside the managed repository ... Refuse a data directory inside the
      repository". ADR-007 d10: "if that path is the project root or lies inside it". 0.5.2 allows a
      project root below a repository top level (ports/vcs.py RepoState.NESTED; wiring.py
      FsAncestorFinder). Read-only commands also open the data directory: status (wiring.py lines
      96-116, status.py 224-243) and the hook. d10 says only "every command that opens the data
      directory refuses with ORQ-E105 ... and the hook prints {}".
    finding: >
      For a project in a subfolder, the design refuses less than the person decided: a data
      directory inside the repository but outside the project root is accepted. It also does not say
      whether the read-only `status` and `doctor` refuse with exit 3 or report the data as not run.
    needed: >
      Either refuse a data directory inside the Git work tree that holds the project, or record the
      narrower reading with the person as a ledger question. State the result for status and doctor.

  - id: R4-F6
    severity: minor
    location: adr-007 decision 8; BC-21
    evidence: >
      ADR-007 Context: rules that differ from 0.5.2 are marked "new". d8 cites loading.py lines 1-27
      as the source of "no unknown key's name". loading.py line 24 builds the message from
      error['loc'], and for an unknown key Pydantic's loc holds the key name (my knowledge, not in
      the evidence). Only resources_source.py line 73 and integrations_source.py line 127 drop "a
      stranger's key". yaml_loader.py line 69 ("duplicate key {key!r}") and strict_json.py line 45
      ("the key {key!r} appears twice") quote key names.
    finding: >
      Leaving out unknown key names everywhere is stricter than 0.5.2, but it is not marked "new".
      Duplicate key names, which 0.5.2 quotes, are covered by neither rule. Codes and verdicts do not
      change, so parity holds, but the label and the rule text are inaccurate.
    needed: Mark leaving out unknown key names as new outside resources and integrations, and say whether duplicate key names may still be quoted.
```

### Round-3 findings: are they resolved?

| Round-3 finding | Status | Note |
|---|---|---|
| R3-F1 YAML parse path | Resolved | ADR-007 decision 3, ADR-003 and BC-6 now use the generic tree. `views.md` is stale (R4-F3) |
| R3-F2 parser ban and allows | Resolved | ADR-001 decisions 3 and 5, ADR-007 decision 7 |
| R3-F3 old journals | **Partly** | Only the status field is read, open gives ORQ-E131, unreadable gives ORQ-E136, and BC-22 exists. The folder named is not where 0.5.2 writes (R4-F1) |
| R3-F4 standards timing | Resolved | ADR-006 decision 1, brief §9. Cited `standards_for.py` 183-197 and `gate_status.py` 81-94 checked |
| R3-F5 process visibility | Resolved | ADR-001 decision 4, ADR-007 decision 1, BC-7, EC-6. SEC-001 text is stale (R4-F4) |
| R3-F6 literal members | Resolved | ADR-001 decision 1 |
| R3-F7 float overflow | Resolved | ADR-007 decision 4, BC-17, ADR-002 decision 2 |
| R3-F8 packets in SAFE-001 | Resolved | ADR-006 SAFE-001 row |
| R3-F9 removed paths | Resolved | EC-5 identity |
| R3 observations | Resolved | Exit status now cites `errors.py` 19 and `runner.py` 33 (checked). `controls_level` cites `upgrade.py` 356-366 (checked). User-scope readers in ADR-001 decision 8. Component diagram edges added (container view not: R4-F3). Lints set by attribute. `panic = "unwind"` pinned. `arbitrary_precision` rejected |
| SEC-D3-1 Git argument checks | Resolved | `objects.py` 11-17 and 26-28, `vcs.py` 28-38 and 41-56 checked. BC-18 extended, ports glob added |
| SEC-D3-2 no echo | Resolved | ADR-007 decision 8, BC-21, globs. Labelling issue in R4-F6 |
| SEC-D3-3 printable characters | Resolved | `yaml_loader.py` 129-131 checked |
| SEC-D3-4 event-level fallback | Resolved | Generic tree, with "stop and ask" |
| SEC-D3-5 entry points | Resolved | Partial-net wording, `Deserializer::from_*`, allows for tests and the xtask |
| SEC-D3-6 modes | Resolved | Marked new. `wiring.py` 158-162 and 198-224 checked |
| SEC-D3-7 journal check | **Partly** | Same defect as R4-F1 |
| SEC-D3-8 hook panic | Resolved | ADR-007 decision 12, BC-22 |
| SEC-D3-9 bounded read | Resolved | ADR-007 decision 6. `common.py` 39-40 and `validate_model_policy.py` 608-610 checked |
| SEC-D3-10 globs | Resolved | The globs are added. The promised `.cargo/**` scope entry was not, which is harmless unless the plan creates `.cargo/` |
| `ORQLET_DATA_DIR` inside the repository | Applied through Q-16 | The rule is narrower than the answer (R4-F5) |

### Observations (non-blocking)

- **Clippy and paths that do not resolve (my own knowledge, not in the evidence):** recent Clippy versions may warn when a `disallowed-*` entry names a path the crate cannot resolve, unless the entry is marked `allow-invalid`. Each crate carries the full parser list, including crates it does not depend on (application and cli have no serde-saphyr or toml), so BC-9 (`-D warnings`) could fail. The plan should check this at the pinned toolchain.
- **No `regex` in adapters:** the adapters allow-list has no `regex`. The revision check (`objects.py` line 11), the `ls-files` cluster check and the `rust-version` pattern must be written by hand or moved into application code.
- **No dev-dependencies:** no allow-list has any. The tests can use only the standard library and the listed crates, so there is no `tempfile` and no snapshot crate. This works, but nobody has stated it.
- **serde-saphyr rationale:** if the tree is built straight from parser events, the deserializer budgets in ADR-003 do not apply, and the remaining reason to prefer serde-saphyr over a plain parser is that it writes YAML.
- **Two base revisions:** the manifest binds 3e3c311 and the AS-IS file binds 3196914. Without Git I could not confirm the self-check's claim that nothing changed between them.
- **Citations:** I read the working tree, not 3e3c311. Every range I opened supports its claim: `journal.py` 37-38, 63-88 and 70-77; `upgrade.py` 80-88 and 356-366; `wiring.py` 52, 83-93, 108, 158-162, 170, 198-224 and 207; `objects.py`; `vcs.py`; `yaml_loader.py`; `strict_json.py`; `loading.py`; `hook.py` 38-48; `git_runner.py` 18-116; `environment.py` 7-32; `local_fs.py` 1-61; `status.py` 224-243; `hook_event.py` 242-251; `technology_scanners.py` 190; `gate_status.py` 81-94; `standards_for.py` 183-197. The ADR-006 decision 7 claims match `.github/CODEOWNERS`, `.gitattributes` and `.gitignore`.
- **Design format:** all D3 artifacts are present, every ADR has its four sections, the brief keeps the required order, every acceptance criterion has a source, and the design contains no phase order. I did not count the brief's words or run `orqlet validate design`.

### Self-check

```yaml
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: design}
  model: "Claude Opus 5.5 (as named in this agent's configuration); fresh context, only the given paths and cited sources"
  revision: "branch rust-migration-design not confirmed and HEAD not read (shell refused); working tree read"
  checks:
    - {what: file hashes, how: shasum, result: "not run (shell refused); 10 given values equal the manifest's; manifest hash unrecorded, not checked"}
    - {what: D3 artifacts, ADR sections, brief order, how: read all ten files against design-format.md, result: pass}
    - {what: round-3 findings, how: compared each applied resolution with current text and source, result: "all resolved except R3-F3 and SEC-D3-7, partly (R4-F1)"}
    - {what: Q-1 to Q-16 respected, how: compared ledger answers with ADRs, result: "pass except Q-16 scope (R4-F5)"}
    - {what: cited source lines, how: read cited ranges in the working tree, result: "pass; ADR-007 d11 folder contradicts journal.py (R4-F1)"}
    - {what: web evidence supports ADR claims, how: read five files, result: "pass; event-level parsing marked for plan confirmation"}
    - {what: standards rewrite vs current rules.yaml and standards output, how: compared rule by rule, result: "pass; SEC-001 text stale (R4-F4)"}
    - {what: brief word limit and orqlet validate design, result: not run}
  unverified:
    - "Line numbers at 3e3c311 itself"
    - "Pydantic loc content for unknown keys and Clippy's handling of unresolvable paths are my own knowledge, to be confirmed"
    - "This review is an additional check, not a guarantee"
```

**Completed**
- Reviewed all seven ADRs, the brief, the views and the manifest against the AS-IS file, the ledger, the evidence, the standards and the cited source code.
- Found R4-F1 and R4-F2 (major) and R4-F3 to R4-F6 (minor).
- Checked every round-3 finding: all are resolved except the old-journal guard (R3-F3 and SEC-D3-7), which is partly resolved.

**Questions**
- Is there a fifth round, or does the person decide R4-F1 and R4-F2 directly?
- Q-16 says "inside the repository" but the design refuses only inside the project root. Which one did the person mean?

**Next prompt**
```
Task: rust-migration
Next: architect revises the design for R4-F1 to R4-F6 (orqlet-design), then the person decides on approval
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/reviews/architecture-reviewer-design.md
Pending: person's approval of the design; decision on a further review round
```

## Architect's responses

The design files above are unchanged since the reviewer read them, so this note's hashes match the manifest. Below is the resolution I propose for each finding. I have not applied any of them; whether to apply them, and whether another round follows, is the person's decision.

- R4-F1 (open, major): this was my error in round 3; 0.5.2 writes project journals to `projects/<uuid>/upgrade/`. My proposed resolution:
  - **Where and how 1.0.0 writes.** 1.0.0 writes its own journals in the same folder. Each record adds a `format: "orqlet-journal/1"` field; a record without that field is a 0.x record.
  - **The guard.** Before an upgrade, 1.0.0 reads the status of every record in that folder. An open 0.x record refuses with ORQ-E131 and the advice to finish or roll back with 0.5.2. An open 1.0.0 record refuses with ORQ-E131 and the advice `upgrade --resume`. A record that cannot be read refuses with ORQ-E136.
  - **Rollback.** Rolling back a 0.x record is refused with ORQ-E136.
  - **The test.** BC-22 builds its 0.x fixtures in the 0.5.2 layout and record shape (`journal.py` lines 3-7, 43-44 and 154-165).
- R4-F2 (open, major): ids come from the `uuid` crate with only its v4 feature, which takes randomness from the operating system. The text form is the same lowercase hyphenated one that `str(uuid.uuid4())` gives. The crate goes on the adapters allow-list behind the existing id-generator port (`system.py` lines 9-16). Timestamps come from `std::time::SystemTime`, through a small UTC calendar formatter in the domain with its own tests, so no time crate is needed.
- R4-F3: redraw D-4 with the documents module and the generic tree, add the data-directory check and the journal-status check to D-5, add packets to the D-2 data-directory edge, and add the three edges to D-3.
- R4-F4: ADR-003 says three domain crates, and the SEC-001 text says "the process module, a private child of the Git module".
- R4-F5: Q-16 says "repository", so the refusal covers the Git work tree that holds the project, or the project root when there is no Git. Writing commands refuse with ORQ-E105, exit 3. The read-only commands `status`, `doctor`, `sync` and `explain` report a finding and treat the data as missing. The hook prints `{}`.
- R4-F6: leaving out unknown key names is marked new outside resources and integrations. Duplicate keys are refused without quoting the key, also marked new.
- Observations: each crate's `clippy.toml` lists only the entry points of parser crates that crate depends on, which avoids paths that do not resolve. The revision check, the `ls-files` cluster check and the `rust-version` pattern are written by hand in the adapters. No crate has a dev-dependency: tests use the standard library and the listed crates. `.cargo/**` joins the scope.

## Person's decision

On 2026-11-25 tmishari chose to apply the proposed fixes and run a fifth round with both reviewers, and allowed the `uuid` crate (feature `v4` only) on the adapters allow-list. The fixes are applied in the round-5 design files; this note keeps its round-4 hashes.
