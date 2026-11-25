# Security review of the rust-migration design, round 4 (extra round allowed by the person)

Reviewer: orqlet-security-reviewer subagent (947a8526-5474-4c2a-a2cd-428822a0c633), fresh context, model named by the client as Claude Opus 5.5.
Earlier rounds: `security-reviewer-design-r2.md`, `-r3.md`. The person allowed this fourth round on 2026-11-25, after round 3.
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

# Security review of the rust-migration design, round 4

The design needs changes before approval. There are no blocking findings, but there is one major and eight minor ones.

- **The major finding:** the check that stops an upgrade while an old journal is unfinished looks in the wrong folder. ADR-007 tells it to read `projects/<project id>/journal/`, but 0.5.2 writes project journals to `projects/<project id>/upgrade/` (`journal.py` lines 6 and 43). As written, an unfinished 0.5.2 change would never be found.
- **Round 3:** eight of the ten round-3 findings are resolved and two are only partly resolved (table below).

**Hash comparison: not run.** The shell was refused in this session. I checked two things instead:
- The ten values you gave equal the `sha256` values that `manifest.yaml` records for D-1 to D-5 and ADR-001 to ADR-007. `views.md` holds D-2 to D-5 and has one hash.
- Nothing records a hash for the manifest itself, so `7ce94708…` was not checked.

Neither check proves that the file bytes match.

## Findings (orqlet.finding/v1)

```yaml
findings:
  - id: SEC-D4-1
    severity: major
    location: adr-007 decision 11; adr-004 decision 5; component §5 rows "Open journal" and "Unreadable journal or 0.x rollback"; BC-22
    evidence: >
      ADR-007 d11: "reads only the status field of each journal file under projects/<project id>/journal/
      ... whichever version wrote it". src/orqlet/adapters/fs/journal.py line 6 ("upgrade/<change-id>.json
      the journal of one change") and line 43 (self._dir = _project_dir(project_id).child("upgrade")):
      0.5.2 project journals live in projects/<id>/upgrade/. ADR-004 d5 says "every journal in its data
      directory", a wider scope than ADR-007 d11. journal.py lines 154-165: a 0.5.2 record holds
      change_id, command, plan_digest, created_at, status, entries and roots, with no version field.
      ADR-004 d5: 0.x journals "are not replayed" and a rollback of a 0.x change id is refused with
      ORQ-E136. Component §5 gives `upgrade --resume` as the recovery for an open journal.
    finding: >
      The 1.0.0 guard reads a folder that 0.5.2 never writes. An open 0.5.2 change is therefore never
      seen, and 1.0.0 would upgrade over a half-applied 0.5.2 change. A later 0.5.2 rollback could then
      restore stale backups over the 1.0.0 writes. This is the "nothing is detected" case that SEC-D3-7
      described. A BC-22 test written from the design would put its fixtures in journal/ and pass.
      In addition, a 0.5.2 record has no version field, so the design does not say how 1.0.0 tells a
      0.x journal from its own. Both rules depend on that: "not replayed / rollback refused" and
      "--resume" as the recovery for an open journal. For an open 0.x journal, the recovery and the
      0.5.2 ORQ-E131 text (upgrade.py lines 84-86) point to commands that 1.0.0 refuses.
    needed: >
      Name the real 0.5.2 folder (projects/<id>/upgrade/) in ADR-007 d11 and use the same scope in
      ADR-004 d5. Say which folder 1.0.0 writes its own journals to. Say how 1.0.0 recognises a 0.x
      record: for example a version or schema field that 1.0.0 adds to its own records, or a separate
      folder for 1.0.0 records. For an open 0.x journal, make the recovery and the message "finish or
      roll back with 0.5.2". BC-22 builds its 0.x fixtures in the 0.5.2 folder with 0.5.2's record shape.

  - id: SEC-D4-2
    severity: minor
    location: adr-007 decision 10; BC-19; component R-11
    evidence: >
      ADR-007 d10: the data directory is "resolved to its real path" and refused when it "is the
      project root or lies inside it ... before writing anything". wiring.py lines 89-93: 0.5.2
      creates the folder (mkdir parents=True) before it is used. Lines 63-69: build_services uses the
      root without resolving it. journal.py lines 30-34 and 43: per-project data goes under
      projects/<id>/, where <id> comes from the profile.
    finding: >
      A data directory that does not exist yet has no real path until it is created, and creating
      it is a write. The design does not say how a missing folder is resolved. An implementation
      that falls back to comparing the paths as written would miss a symlinked ancestor that points
      into the project. The design also does not say whether both sides are compared as real paths,
      component by component, and case-insensitively where the file system is (the macOS default).
      Finally, the rule checks only the data-directory root. It does not catch a project that lies
      under the data directory, where projects/<id>/ or packets/ can land inside the repository.
      Q-16 is meant to keep journals, backups and packets out of the repository.
    needed: >
      Define the check. Resolve the deepest existing ancestor to its real path and append the
      missing components, which may not contain '.' or '..'. Compare that with the real project root,
      component by component, case-insensitively on macOS and Windows. Refuse when any folder that
      Orqlet writes for this project (projects/<id>/, packets/) lies inside the project root. Add a
      BC-19 case for a data directory that is missing and reached through a symlinked ancestor.

  - id: SEC-D4-3
    severity: minor
    location: adr-007 decisions 9 and 11 (not covered)
    evidence: >
      journal.py lines 30-34: the project id is joined with CanonicalPath.child.
      domain/paths.py lines 80-81: child() parses "projects/<id>", so an id containing '/' becomes
      several components. contracts/profile.py line 48: uuid is a plain str with no pattern. The id
      comes from the repository's profile (upgrade.py line 78; rollback.py line 49).
    finding: >
      A value from the untrusted profile chooses the folder in the data directory that holds this
      project's journals, backups and apply lock. ADR-007 does not carry over any rule for it. As
      long as the confined data-directory file system of decision 9 is used, the path stays inside
      the data directory. Even so, an id such as "a/b", or one copied from another project, makes two
      projects share journals, backups and locks. A rollback could then copy another project's
      backed-up content into this repository. In Rust, joining a PathBuf with an absolute id would
      replace the base path, so the design should not leave this implicit.
    needed: >
      State in ADR-007 that the project id is exactly one CanonicalPath component, with no '/'. A
      UUID pattern is an option and would be stricter. Join the id only through the confined
      data-directory file system. Add a BC-19 or BC-20 case.

  - id: SEC-D4-4
    severity: minor
    location: adr-007 decision 9 (cites local_fs.py lines 110-149)
    evidence: >
      local_fs.py lines 131-135: a project write keeps the existing file's mode
      (mode = stat.S_IMODE(info.st_mode)), and new files get 0o644 (line 36). Line 137: the temporary
      file comes from tempfile.mkstemp, which creates it 0600, and line 143 sets the final mode before
      the replace. ADR-007 d9 lists create_new, sync, rename and the retries, but not mode preservation.
    finding: >
      A port that creates the temporary file with OpenOptions defaults gets 0666 minus the umask.
      After the rename, a team file that was 0600 becomes world-readable, and an executable script
      loses its executable bit. The content can also be readable during the write window. This is a
      0.5.2 behaviour that disappears without anyone noticing.
    needed: >
      Add to decision 9: the temporary file for a project write is created 0600, and the existing
      target's mode (0644 for a new file) is set before the rename, as in local_fs.py lines 131-143.
      Add a BC-19 case: a 0600 file stays 0600 after an upgrade rewrites it.

  - id: SEC-D4-5
    severity: minor
    location: adr-007 decisions 8 and 12; component §5 row "Panic outside the hook"
    evidence: >
      runner.py lines 34-35: an unexpected exception gives only "internal error: <type name>", with no
      traceback and no message. ADR-007 d12 installs a silent panic hook only for the hook command.
      D8 covers library error text, but not panic messages.
    finding: >
      For every other command, Rust's default panic hook writes the panic message to standard error
      before the ORQ-E900 envelope. An unwrap or expect on an error that holds input (for example a
      serde error that quotes a value) would print that value. 0.5.2 never does this, and D8 aims to
      prevent it.
    needed: >
      Say that every command installs a panic hook that prints nothing, or only a fixed text, and
      that the ORQ-E900 message never includes the panic payload. Add a test case, or name it as a
      review check.

  - id: SEC-D4-6
    severity: minor
    location: adr-007 decision 3 (and decision 4 by comparison); BC-6
    evidence: >
      yaml_loader.py lines 39-45: an int is any [-+]?[0-9]+, and a float matches an exponent form, so
      in 0.5.2 the YAML value 1e400 becomes infinity and a very long integer becomes a Python big
      integer, or "cannot be parsed" beyond the digit limit (line 129). D4 refuses integers outside
      64 bits and floats outside f64 for JSON only. D3 says nothing on either for YAML.
    finding: >
      The design does not say what the YAML tree does with an integer that does not fit in 64 bits
      or a float literal that overflows. An implementation could wrap, saturate, read the number as
      a float, or produce infinity, which silently changes values. ADR-007 rejects exactly that for
      JSON. The vector set cannot fix this, because 0.5.2's result (a big integer) has no Rust
      counterpart.
    needed: >
      Apply decision 4's two rules to the YAML tree as well, marked new, or say explicitly that such
      values stay strings. Add both cases to BC-6.

  - id: SEC-D4-7
    severity: minor
    location: manifest.yaml extractor_config.security_globs and scope.paths
    evidence: >
      The globs cover crates/orqlet-adapters/src/**, hook.rs, the application ports, loading.rs,
      mcp_credentials.rs, build.rs, .cargo/**, clippy.toml, the Cargo files and xtask/src/arch.rs.
      component §4: orqlet-cli holds the "wiring". In 0.5.2, wiring.py lines 83-93, 158-162 and 200-223
      decide the data directory, which file systems are confined and where packets go. The round-3
      response says ".cargo/** would join the scope". scope.paths (lines 18-40) has no .cargo/**.
    finding: >
      In 1.0.0 the data-directory resolution, the new Q-16 refusal, the 2 s hook deadline and the
      wiring of confined file systems live in orqlet-cli outside hook.rs. A change there does not
      trigger security review. The use-case modules that build "never echo" messages (the
      equivalents of resources_source.py and integrations_source.py) are not covered either. The
      .cargo scope change that round 3 promised was not applied.
    needed: >
      Add the CLI wiring module (and main.rs, if it installs the panic hook) and the message-building
      use-case modules to security_globs. Either add ".cargo/**" to scope.paths or record that
      .cargo/ is not expected to change.

  - id: SEC-D4-8
    severity: minor
    location: adr-001 decision 6; adr-003 table row "Unicode categories"; adr-006 decision 2; adr-006 decision 1 SEC-001 row
    evidence: >
      ADR-001 d6 and ADR-003 line 18 cite "ADR-007 decision 8" for the Unicode category crate.
      Decision 8 is now "Messages never echo input"; the crate is decision 14. ADR-006 d2 cites "the
      input rules of ADR-007 decision 11" for the Rust project scanner. Decision 11 is now Journal;
      the scanner is decision 13. The rewritten SEC-001 text reads "Only the crate-private process
      module, used by GitRunner alone, creates processes". ADR-007 d1 and ADR-001 d4 now make it a
      private child of the Git module.
    finding: >
      After decisions were renumbered, three security cross-references point to the wrong decision.
      The rewritten SEC-001 standard, which reviewers check against because it is enforced by review,
      describes the weaker visibility that round 3 replaced.
    needed: >
      Fix the three references (decision 14, decision 14, decision 13). Change SEC-001 to say that
      only the process module, a private child of the Git module in orqlet-adapters, creates processes.

  - id: SEC-D4-9
    severity: minor
    location: views.md (D-2 context, D-4 data flow, D-5 sequence); unchanged since round 3
    evidence: >
      D-4: "strict YAML loader (serde-saphyr)" leads straight to "serde contract". ADR-007 d3 and its
      rejected alternative ("Parsing YAML straight into the contract types") require the generic
      tree. D-2 labels the data-directory edge "journal, backups, apply lock", without packets. D-5
      has no journal-status scan and no data-directory refusal before the lock.
    finding: >
      The approved diagrams show the parse path that ADR-007 rejects, and they leave out two new
      controls. A plan or implementation that follows the views would rebuild the weaker path.
    needed: >
      Add the generic tree to D-4, add packets to D-2, and add the Q-16 check and the journal-status
      scan (ORQ-E131/E136) to D-5.
```

## Round-3 findings: are they resolved?

| Round-3 finding | Status | Where the rest went |
|---|---|---|
| SEC-D3-1 Git argument checks | **Resolved.** Decision 2 adds the checks of `objects.py` lines 11-28 and `vcs.py` lines 28-56 and the rule that pathspecs come after `--`. They are in EC-6 and BC-18, and the ports are under the globs. I checked the cited lines. | — |
| SEC-D3-2 messages never echo input | **Resolved.** Decision 8, BC-21, ADR-003 Consequences and EC-6. | Panic output: SEC-D4-5 |
| SEC-D3-3 printable characters | **Resolved.** Decision 3 lists them, and BC-6 covers every decision-3 case. | — |
| SEC-D3-4 checks after parsing | **Resolved.** The tree is built from parser events with the scalar text and style, the plan stops and asks if no event source works, and the alternative is rejected. | Oversized YAML numbers: SEC-D4-6 |
| SEC-D3-5 parser entry points | **Resolved.** The `Deserializer::from_*` constructors are named, the list is called a partial net with the review covering `str::parse`, and tests and the xtask get a scoped allow (ADR-001 decision 5). | — |
| SEC-D3-6 modes and packets | **Resolved.** The modes are marked new, the sources are corrected (`journal.py` 37-38, `wiring.py` 158-162 and 198-224), packets are in SAFE-001, existing folders are left alone, and BC-19 covers it. | Project-write modes: SEC-D4-4 |
| SEC-D3-7 0.x journal guard | **Partly.** The check is now defined (read status only; open gives E131, unparseable gives E136, finished ones are ignored), but it names the wrong folder and cannot tell a 0.x record from a 1.0.0 one. | SEC-D4-1 |
| SEC-D3-8 panic setting | **Resolved.** `panic = "unwind"` is pinned, the hook has a silent panic hook, and BC-22 has a hook panic case. | Other commands: SEC-D4-5 |
| SEC-D3-9 bounded reads | **Resolved** (decision 6, marked new). | — |
| SEC-D3-10 security globs | **Partly.** Ports, `loading.rs`, `mcp_credentials.rs`, `**/build.rs` and `.cargo/**` were added. The CLI wiring is not covered, and `.cargo/**` is not in the scope as promised. | SEC-D4-7 |

## Observations (none blocking)

- **Clippy paths that do not resolve (from memory, to confirm at the pinned toolchain).** ADR-001 decision 3 puts the full list of parser entry points in every crate's `clippy.toml`, including crates that do not depend on `toml` or `serde-saphyr`. Recent Clippy versions warn about paths that do not resolve. The plan should confirm whether `-D warnings` turns that warning into a failure, or whether the list needs to be per crate.
- **Data directory on Windows (from memory).** `platformdirs.user_data_dir("orqlet")` probably gives `…\AppData\Local\orqlet\orqlet`, and `dirs::data_local_dir()` plus `orqlet` gives `…\AppData\Local\orqlet`. If so, the 0.x guard sees nothing on Windows even after SEC-D4-1 is fixed. The design already names this risk (U-10) and relies on the rule that the two binaries never run on one project.
- **Stricter messages than 0.5.2.** Pydantic's error location includes the name of an unknown key (`loading.py` line 24), and the refusals in `paths.py` and `objects.py`, and `check_ref_name` in `vcs.py`, repeat the value. So decision 8 is partly new behaviour rather than a pure carry-over. Q-6 allows the wording change. It only makes things stricter.
- **What the hook cannot catch.** `catch_unwind` cannot catch a stack overflow or a failed allocation; both abort the process. The payload bound and the depth and node limits make this unlikely.
- **Missing review notes.** The manifest's `reviews` entries still name `security-reviewer-design.md` and `architecture-reviewer-design.md`, which do not exist. Only the round-numbered notes exist.
- **The architect's self-check.** The manifest records `orqlet validate design` and `orqlet validate ledger` as passed. I could not re-run them.
- **Changes that help security:** a data directory inside the project is refused (Q-16); process creation is a private child of the Git module; option prefixes are refused; size limits bound the read; integer and float overflow is refused in JSON; the apply lock goes through the confined file system; temporary names use `create_new` with a retry; and unsafe code stays forbidden, so `libc` can only supply constants.
- I found no secrets, MD5 or SHA-1, and no language-model SDK in the files I read.

## Self-check

```yaml
schema: orqlet.self-check/v1
checked_against:
  role: security-reviewer
  phase: design
  round: 4
  model: "Claude Opus 5.5 (as named by the client); fresh context, no Architect or Coder conversation"
  revision: "working tree of /Users/tmishari/Documents/orqlet; branch rust-migration-design and HEAD not confirmed (shell refused); source lines read in the working tree, assumed equal to 3e3c311"
checks:
  - {what: SHA-256 of the ten design files, how: shasum with CRLF read as LF, result: "NOT_RUN (shell refused in this session)"}
  - {what: given hashes vs manifest artifact hashes, how: "read manifest.yaml lines 110-122", result: "equal for all ten values; the manifest's own hash is not recorded and was not checked"}
  - {what: "design set, AS-IS, ledger Q-1 to Q-16, five evidence files, design format, standards output, rules.yaml, round-3 security and architecture notes", how: read in full, result: done}
  - {what: round-3 SEC-D3 resolutions, how: "compared each proposed resolution with the current ADR-001/003/004/006/007, component.md and manifest text", result: "8 resolved, 2 partly (SEC-D3-7, SEC-D3-10)"}
  - {what: "citations new in this round", how: "read wiring.py 40-235, journal.py (all), errors.py, runner.py, upgrade.py 60-110 and 350-370, objects.py 1-40, ports/vcs.py 1-70, loading.py, scan/common.py 25-50, validate_model_policy.py 600-631, hook.py 25-48, yaml_loader.py (all), git_runner.py 14-118, local_fs.py 105-216, paths.py, profile.py 35-60, rollback.py 35-75; searched for no-echo rules", result: "accurate, except the journal folder (SEC-D4-1); local_fs.py mode preservation is not carried over (SEC-D4-4)"}
  - {what: ADR-007 cross-references, how: "searched 'ADR-007 decision N' across the design", result: "three stale references (SEC-D4-8)"}
unverified:
  - "Library and platform behaviour marked 'from memory' (Clippy unresolved-path warnings, platformdirs vs dirs on Windows, macOS realpath case) was not looked up, by rule."
  - "environment.py, strict_json.py, technology_scanners.py and dependencies.py were not re-read this round; round 3 checked them, and I assumed they are unchanged."
  - "orqlet validate design / ledger were not run."
  - "This review is an additional check, not a guarantee."
```

**Completed**
- Reviewed the round-4 design for security risk: one major finding, eight minor, no blocking ones.
- Checked the ten round-3 SEC-D3 findings: eight resolved, two partly.
- The hash comparison was not run; the given values equal the manifest's recorded values.

**Questions**
- Round 4 was the extra round. Does the person want SEC-D4-1, the journal folder and how 1.0.0 recognises a 0.x record, fixed and checked in another round, or approved directly after the fix?

**Next prompt**
```
Task: rust-migration
Next action: architect resolves SEC-D4-1 to SEC-D4-9 in the design set; person decides whether a further review round is needed
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/questions.yaml, docs/design/rust-migration/reviews/
Pending approvals: design approval by tmishari; plan approval
```

## Architect's responses

The design files above are unchanged since the reviewer read them, so this note's hashes match the manifest. Below is the resolution I propose for each finding. I have not applied any of them; whether to apply them, and whether another round follows, is the person's decision.

- SEC-D4-1 (open, major): as for architecture finding R4-F1.
  - 1.0.0 writes its journals in `projects/<uuid>/upgrade/`, and each record adds `format: "orqlet-journal/1"`. A record without that field is a 0.x record.
  - An open 0.x record refuses with ORQ-E131 and the advice to finish or roll back with 0.5.2. An open 1.0.0 record refuses with ORQ-E131 and the advice `upgrade --resume`. A record that cannot be read refuses with ORQ-E136, and so does rolling back a 0.x record.
  - BC-22 uses the 0.5.2 folder and record shape.
- SEC-D4-2: the check resolves the deepest existing ancestor of the data directory to its real path and appends the missing components, which may not be `.` or `..`. It compares the result with the real Git top level, or with the project root when there is no Git, component by component and case-insensitively on macOS and Windows. It also refuses when `projects/<uuid>/` or `packets/` would lie inside it. BC-19 gets a case with a missing data directory reached through a linked ancestor.
- SEC-D4-3: the project id must match the lowercase UUID pattern, which makes it one path component (new), and it is joined only through the confined data-directory file system. BC-20 gets the case.
- SEC-D4-4: the temporary file for a project write is created with mode 0600. The target's existing mode, or 0644 for a new file, is set before the rename (`local_fs.py` lines 131-143). BC-19 gets the case.
- SEC-D4-5: every command installs a silent panic hook, and ORQ-E900 prints a fixed "internal error" text without the panic payload. Covered by a test.
- SEC-D4-6: the YAML tree applies decision 4's integer and float range rules (new). BC-6 gets both cases.
- SEC-D4-7: the security globs add the CLI wiring module, `main.rs` and the use-case modules that build messages. `.cargo/**` joins the scope.
- SEC-D4-8: the three references are fixed (category crate: decision 14, scanner: decision 13), and the SEC-001 text describes the private child module.
- SEC-D4-9: the views are redrawn as for architecture finding R4-F3, with packets on the data-directory edge.
- Observations: each crate lists only the parser entry points of crates it depends on. The duplicate-key and unknown-key wording is marked new (architecture finding R4-F6). The Windows data-directory risk stays under U-10 and the rule against running both binaries on one project.

## Person's decision

On 2026-11-25 tmishari chose to apply the proposed fixes and run a fifth round with both reviewers, and allowed the `uuid` crate (feature `v4` only) on the adapters allow-list. The fixes are applied in the round-5 design files; this note keeps its round-4 hashes.
