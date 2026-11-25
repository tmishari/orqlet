# Security review of the rust-migration design, round 7 (allowed by the person)

Reviewer: orqlet-security-reviewer subagent (f99bdfd7-7f45-4dfd-8a8e-d739db069273), fresh context, model named as Claude Opus 5.5.
Earlier rounds: `security-reviewer-design-r2.md` to `-r6.md`. The person allowed this seventh round on 2026-11-25, after round 6.
Design file hashes of this round, given to the reviewer in its prompt:

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#c15657e6d7c37ecf163410b0db8696b3fb65f3fa0df698135469dcbd236d9d73
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#47e64f08204cfddc55b74aa0334579905e23483e81954b2cde6ece037c9cd739
docs/design/rust-migration/design/adr-003-libraries.md#dee7f39333085019352b841807ef36965288fee5be36607971d33e9f2678df82
docs/design/rust-migration/design/adr-004-version-and-hashes.md#ea987d465d01ff0381a308ff3471a4a9aeceff1d35fab12fc0c9f66790e2ac9a
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#54835d937a3ef93f34ca9411d6b1d9da377cee3a9c918f4a639b98248c2e9c69
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#e3bd59b65704ae83e8b88157f9fbca0603eb35ec72f9aa236dec6017029ed9a1
docs/design/rust-migration/design/adr-007-security-controls.md#04a2779352bf9703a02f7e8d705abecd1400d27785b22050f8f1dd4c47c3d451
docs/design/rust-migration/design/component.md#eba00c5a2431208e8957dec5933c2567e0b299481b6bbb51bcd82d97446b0f21
docs/design/rust-migration/design/manifest.yaml#de12f682a1137a45c6796f7e7a08fd4e9537831aa0ccb9f61f61cc915bff7b92
docs/design/rust-migration/design/views.md#86ffb00231d7c9802e95fe1a52d698ebb898e0ddda4ea6644c0240daebb5683c
```

## Reviewer output (unchanged)

# Round-7 security review of the rust-migration design

Round 7 found no blocking or major findings and two minor ones:

- **SEC-D7-1:** Some acceptance cases promised in round 6 did not make it into BC-23. These are the main-work-tree and common-folder cases, ORQ-E106 for `doctor`, `sync` and `explain`, and `status`.
- **SEC-D7-2:** The design describes which values the escaping filter covers in two different ways. It also says nothing about 0.5.2's Python `repr` quoting.

All four round-6 security findings are resolved in the design text. Of the architecture findings, R6-F1 and R6-F3 are resolved and R6-F2 is only partly resolved; the missing part is SEC-D7-1.

**Hash check: not run.** The shell was refused in this mode. As a substitute, I compared the hashes you gave with `manifest.yaml`. All nine artifact hashes are the same as the values at lines 120–131. The manifest does not record its own hash, so its value was not checked. ADR-001 to ADR-006 have the same hashes as in round 6.

## 1. Findings (orqlet.finding/v1)

```yaml
findings:
  - id: SEC-D7-1
    severity: minor
    location: component.md BC-23 (line 85); adr-007 decision 10 (lines 18-22) and Consequences (line 46)
    evidence: >
      adr-007 line 18 compares with "the parent of the common Git folder when that folder is named
      .git, or else the common folder itself". Line 20 (Q-18): doctor, sync and explain "report the
      same ORQ-E105 or ORQ-E106 as a finding". Line 21: status shows its not-run entry for user
      data. Line 46: "Each rule above has a criterion in the brief (BC-6, BC-7, BC-17 to BC-24)".
      component.md line 85 (BC-23): "With the data directory in the repository ..., also below a
      linked ancestor: writing commands refuse, with ORQ-E106 when Git fails; doctor, sync and
      explain report it, create nothing and read no journal there; the hook prints {}."
      security-reviewer-design-r6.md lines 123 and 146-149, and architecture-reviewer-design-r6.md
      lines 177-180, promised a linked-worktree case, a "data directory in the main work tree is
      refused" case, and doctor, sync and explain reporting ORQ-E106 when Git fails.
    finding: >
      BC-23 does not name these cases:
      - a linked worktree whose data directory lies in the main work tree;
      - a common folder that is not named .git (bare or separate Git folder), which is compared
        itself;
      - ORQ-E106 for doctor, sync and explain when the Vcs call fails;
      - the status not-run case.
      "Below a linked ancestor" reads as a symbolic-link ancestor (decision 9 uses "link" that way),
      not a linked worktree. A port that skips the main-work-tree comparison, compares the parent
      of a bare repository, or reads user data in status would still pass BC-23 as written.
    needed: >
      Name each case in BC-23 (or add a criterion):
      - a linked worktree with the data directory in the main work tree is refused;
      - with a bare common folder, that folder is compared and its parent is not;
      - doctor, sync and explain report ORQ-E106 when Git fails;
      - status shows its not-run entry and reads nothing from that data directory.
      Reword "linked ancestor" as "symbolic-link ancestor".

  - id: SEC-D7-2
    severity: minor
    location: adr-007 decision 15 escaped bullet (line 41), decision 8 (line 16); manifest EC-6 (line 117); component BC-24 (line 86)
    evidence: >
      adr-007 line 41: "Escaped, for every repository value inside a finding or a not-run entry ...
      The users are listed in the 0.5.2 source: ..."; line 39: "carried over exactly". EC-6: "a
      repository value is shown only through the all-or-nothing or escaping filter".
      0.5.2 shows repository-controlled values in findings with neither filter, for example
      validate_design.py lines 127 and 130 ({artifact.path}) and validate_records.py lines 607,
      619, 647 ({entry.path}, {changed.path}, {claim.anchor!r}).
      0.5.2 quotes values with Python repr in refusals: paths.py lines 32-47 ({raw!r}), vcs.py
      line 38, objects.py line 17, git_runner.py lines 112 and 115, versions.py line 25,
      evidence.py lines 43 and 47, blocks.py lines 77-96, init_questions.py line 282 and
      diagnose.py line 542.
      CanonicalPath refuses only Cc, Cf and Cs (adr-007 line 38), so Co, Cn, Zl, Zp and the
      invisible ranges of representable.py lines 24-35 can sit in a valid path.
    finding: >
      The escaping filter's scope is stated two ways. One reading is "every repository value in a
      finding", which goes beyond 0.5.2 and is not marked new. The other is "the listed users",
      which leaves the sites above unfiltered, as 0.5.2 does, and contradicts EC-6.
      The design also does not say what replaces 0.5.2's repr quoting:
      - decision 8 says refusals "report only the rule";
      - its list of "New" changes names only unknown keys, duplicate keys, Git output and the
        project id.
      The likely Rust translation of {x!r} is Debug or Display formatting. How Rust's Debug escapes
      Unicode was not looked up (unverified), and Display escapes nothing. A port could therefore
      show a line separator, a private-use character or an invisible selector raw in a finding.
    needed: >
      Choose one rule and write it down. For example: every repository-controlled value in a
      finding, a not-run entry or a refusal is either left out (decision 8) or passed through
      printable(), never formatted with Debug or Display.
      Mark the change as new for the 0.5.2 sites that showed the value raw or with repr.
      Add a BC-24 case: a manifest artifact path or a claim anchor that holds U+2028 or U+FE0F is
      shown escaped or not at all.
```

## 2. Round-6 findings

| Finding | Status | Evidence |
|---|---|---|
| SEC-D6-1: missing output filters | **Resolved** | ADR-007 decision 15 (lines 39–42) carries over both filters, and the cited lines match the source: `representable.py` 1–62 with ranges 24–35, and `conventions.py` 100–124. All 0.5.2 callers found by searching for `representable_` and `printable(` are listed: `hook_event.py` 116–117 and 162, `status.py` 174 and 221, `user_scope.py` 27, and the 14 `printable` sites. Decision 8 points to the filters (line 16), as does EC-6 (manifest line 117). The two filter modules are in the security globs (lines 55–56). BC-24 is at component line 86, and decision 14 now requires Co, Cn, Zl and Zp (line 38). What remains is the scope wording, SEC-D7-2. |
| SEC-D6-2: definition of the main work tree | **Resolved in the text** | ADR-007 line 18 now compares the parent only when the common folder is named `.git`, and otherwise the common folder itself. The acceptance case is still missing: SEC-D7-1. |
| SEC-D6-3: missing criteria and table rows | **Mostly resolved** | ORQ-E106 is in the failures row (component line 54) and in view D-5 (views line 62). BC-23 (line 85) covers the planted journal ("read no journal there"), the hook's `{}` and creating nothing. The doctor, sync and explain ORQ-E106 case and the main-work-tree case are still missing: SEC-D7-1. |
| SEC-D6-4: project id quoted in the refusal | **Resolved** | ADR-007 line 24 makes the message name the id's source and leave out the value, marked new. BC-23 has "refused unquoted". The cited `journal.py` line 34 matches. |
| R6-F1: bare repository over-refusal | **Resolved in the text** | As SEC-D6-2. |
| R6-F2: Q-18, Q-19 and the main-work-tree rule have no criterion | **Partly resolved** | BC-23 covers doctor, sync and explain creating nothing, the hook's `{}` and an empty `ORQLET_DATA_DIR`. The main-work-tree case is still missing: SEC-D7-1. |
| R6-F3: four statements not updated | **Resolved** | Component line 54 and views line 62 add ORQ-E106. EC-4 (manifest line 102) now covers every journal reader. EC-6 (line 117) limits the hook to "the project root the hook finds". |
| R6 observation: where the journalled apply refuses | **Resolved** | ADR-007 line 29 makes the refusal happen before the lock and the backups, with the upgrade refusal's exit status. In 0.5.2 that status is `ExitCode.REFUSED = 3` (`exit_codes.py` line 10). In 0.5.2 the backups at `apply_plan.py` lines 52–54 come before the supersede step at lines 55–56, so the new order avoids leftover backup files. |

## 3. Observations (none blocking)

- **The 1,200-character cap on the session-start text is not stated.** `hook_event.py` line 121 drops the whole text when it is longer than `MAX_STATUS_CHARACTERS = 1200` (line 38). ADR-007 cites lines 110–121 but does not name the cap. In 0.5.2, `Version.parse` puts no limit on the number of digits (`versions.py` lines 11 and 22–26). A Rust parser with fixed-width numbers would be stricter, which fails closed, but it would be a parity difference that is not listed.
- **The unit of "1 to 200 characters" is not stated.** Python's `len` counts code points (`representable.py` line 58). Counting bytes in Rust would be stricter, which also fails closed.
- **A lossy decode would defeat the all-or-nothing filter.** The filter exists so that no path that does not exist is shown (`representable.py` lines 2–4). 0.5.2 decodes Git's top level strictly (`vcs_git.py` line 77). If a port decoded it lossily, the replacement character (U+FFFD) is visible, so it would pass the filter and `status` would show a path that does not exist. The design says "never repaired" but does not say the decode must be strict.
- **The escaping filter does not neutralise shell syntax in advice.** The change id shown in the ORQ-E131 and ORQ-E170 advice is read from the record's contents (`journal.py` line 87), not from the file name. `printable()` keeps `;`, `$()` and backticks, and the advice is a command a person may copy (`upgrade.py` lines 85–86). The risk is low because, after Q-16, the journal folder is Orqlet's own. Requiring the id to equal the file name, or to match a fixed pattern such as the one in `user_scope.py` line 33, would close it.
- **The case rule for the `.git` name is not stated.** Decision 10 compares path components case-insensitively on macOS and Windows, but does not say how the folder name `.git` itself is compared. How Git prints the case of the common folder was not looked up (unverified).
- **A hostile `.git` file can still cause refusals.** It can name a common folder called `.git` in a broad folder and so trigger refusals. This affects availability only and fails closed. The Git behaviour was not looked up (unverified).
- **No secrets** appear in the files I read, and no language-model SDK is named.

## 4. Self-check

```yaml
schema: orqlet.self-check/v1
checked_against:
  role: security-reviewer
  phase: design
  round: 7
  task: rust-migration
  model: "Claude Opus 5.5 (as named by the client); fresh context, no Architect conversation"
  revision: "working tree; branch and HEAD NOT confirmed (shell refused); cited source read as the working tree, assumed equal to 3e3c311"
checks:
  - {what: SHA-256 of the ten design files with CRLF read as LF, how: "perl + shasum", result: "NOT_RUN (shell refused in ask mode)"}
  - {what: given hashes vs manifest artifact hashes, how: "read manifest.yaml lines 120-131", result: "all nine equal; ADR-001 to ADR-006 unchanged since round 6; the manifest's own hash is not recorded, not checked"}
  - {what: orqlet standards for, how: shell, result: "NOT_RUN; used the rendered SEC-001, SEC-002, SAFE-001, ARCH-001, ARCH-002, MODEL-001 and MODEL-002 rule texts instead"}
  - {what: orqlet validate design / ledger, result: "NOT_RUN"}
  - {what: brief at or under 1,200 words, result: "NOT_RUN (no word count without the shell)"}
  - {what: "adr-007, component.md, views.md, manifest.yaml read in full; Q-16 to Q-20; both round-6 notes", how: read, result: done}
  - {what: round-6 resolutions, how: "compared each needed item and approved response with the round-7 text", result: "SEC-D6-1, -2, -4, R6-F1 and R6-F3 resolved; SEC-D6-3 mostly and R6-F2 partly resolved (SEC-D7-1)"}
  - {what: decision 15 citations, how: "read representable.py 1-62, conventions.py 100-124, hook_event.py 80-237, status.py 160-234, user_scope.py, versions.py; searched src/orqlet for representable_ and printable(", result: "accurate; every 0.5.2 caller listed"}
  - {what: decision 10 and 11 citations new this round, how: "read journal.py 25-134, apply_plan.py 38-72, upgrade.py 70-99, diagnose.py 392-413; searched exit codes", result: "accurate"}
  - {what: repository values shown without a filter in 0.5.2, how: "searched usecases for f-string paths and src/orqlet for !r", result: "unfiltered and repr sites found (SEC-D7-2)"}
unverified:
  - "ADR-001 to ADR-006 were only searched for journal, E131 and data-directory text, not reread (hashes unchanged since round 6)."
  - "as-is.md was only searched for U-8."
  - "Git common-dir output for bare, separate and hostile .git layouts, and the case Git prints, were not looked up."
  - "Rust Debug escaping and the Unicode category crate were not looked up."
  - "This review is an additional check, not a guarantee."
```

**Completed**
- Reviewed the round-7 design set: no blocking or major findings, and two minor ones (SEC-D7-1, SEC-D7-2).
- Checked the seven round-6 findings: five are resolved, SEC-D6-3 is mostly resolved and R6-F2 is partly resolved, with the remaining acceptance cases in SEC-D7-1.
- Not run: the hash computation, `orqlet standards for`, `orqlet validate`, the word count, and confirming the branch and HEAD, all because the shell was refused.

**Questions**
- SEC-D7-2: should every repository value in a finding or refusal be escaped, which is new behaviour, or only the values at the listed 0.5.2 sites?
- Should SEC-D7-1 and SEC-D7-2 be fixed before the design is approved, or carried into the plan as conditions?

**Next prompt**
```
Task: rust-migration
Next action: architect answers SEC-D7-1 and SEC-D7-2 and writes reviews/security-reviewer-design.md; tmishari decides on design approval
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/questions.yaml, docs/design/rust-migration/reviews/
Pending approvals: design approval by tmishari; plan approval
```

## Architect's responses

Proposed, not applied. The person decides.

- **SEC-D7-1.** As the response to R7-F1 in the architecture note: ADR-007 decision 10 gets a numbered list of test cases, and BC-23 requires every case on it. The list covers the main work tree, a bare or separate common folder, ORQ-E106 for doctor, sync and explain, the `status` not-run entry, the hook, an empty `ORQLET_DATA_DIR`, and an ancestor that is a symbolic link.
- **SEC-D7-2.** Asked as Q-21. If you choose the wider rule, it is the reviewer's example, marked new: every repository-controlled value in a finding, a not-run entry or a refusal is either left out or passed through `printable()` with a limit of 200, and never formatted with Debug or Display. That replaces 0.5.2's raw and `repr` forms. BC-24 then gains the reviewer's case of a manifest artifact path or claim anchor holding U+2028 or U+FE0F. If you choose the narrow rule, decision 15 and EC-6 name only the listed 0.5.2 sites, plus the change id, which is marked new.
- **Session-start cap.** Decision 15 names `MAX_STATUS_CHARACTERS = 1200` (`hook_event.py` lines 38 and 121): a longer text is dropped whole.
- **Unit of length.** The 200-character limit counts Unicode scalar values, as Python's `len` counts code points.
- **Strict decode.** Text that Git prints is decoded as strict UTF-8, as at `vcs_git.py` line 77. Invalid input is an error, never a replacement character.
- **Change id in advice.** New: a journal record whose change id does not equal its file name without `.json` counts as unreadable (ORQ-E136), so the advice only ever shows an id that names an existing file. In 0.5.2 the file is `<change_id>.json` (`src/orqlet/adapters/fs/journal.py` line 92), and the id is a CanonicalPath component (lines 90-94).
- **`.git` name and a hostile `.git` file.** As the `.git` name response in the architecture note: the name is compared exactly as `.git`. A hostile `.git` file only causes refusals, so it fails closed. This is recorded as accepted.

## Person's decision

On 2026-11-25 tmishari chose to apply the proposed fixes and run an eighth round with both reviewers. For the scope of the escaping filter, recorded as Q-21: every repository value in a finding, a not-run entry or a refusal is escaped with a limit of 200 or left out, never shown raw (new behaviour). The fixes are applied in the round-8 design files; this note keeps its round-7 hashes.
