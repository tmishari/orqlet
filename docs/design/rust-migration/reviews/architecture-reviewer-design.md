# Architecture review of the rust-migration design, round 8 (allowed by the person)

Reviewer: orqlet-arch-reviewer subagent (35be7c81-a861-4b7f-9400-f43eefb401b6), fresh context, model named as Claude Opus 5.5.
Earlier rounds: `architecture-reviewer-design-r1.md` to `-r7.md`. The person allowed this eighth round on 2026-11-25, after round 7.

The reviewer's last reply was a short summary that pointed to its previous message for the full findings. The architect copied that previous message from the agent's record, unchanged, below. Its last lines are the reviewer's own working notes, kept as they were. Design file hashes of this round, given to the reviewer in its prompt:

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#21528f0205a39f2c83502c6a6cb726a0997f2d27d65d39bfbe34303cd8d2d264
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#47e64f08204cfddc55b74aa0334579905e23483e81954b2cde6ece037c9cd739
docs/design/rust-migration/design/adr-003-libraries.md#7d1097ed8b308111fda7f8e2a3928aca7f79119dcc340b0812b3cbf005ecb9f2
docs/design/rust-migration/design/adr-004-version-and-hashes.md#ea987d465d01ff0381a308ff3471a4a9aeceff1d35fab12fc0c9f66790e2ac9a
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#54835d937a3ef93f34ca9411d6b1d9da377cee3a9c918f4a639b98248c2e9c69
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#e3bd59b65704ae83e8b88157f9fbca0603eb35ec72f9aa236dec6017029ed9a1
docs/design/rust-migration/design/adr-007-security-controls.md#a5ae9d433c891e790e0879ddc2fa6abb3066626187339efe31ee2b34a7e7ea7d
docs/design/rust-migration/design/component.md#3854b14a1a23c9f72b6811008a80708d7fd12c265140844735a596fa915d5097
docs/design/rust-migration/design/manifest.yaml#9100dd0553915b0d43a8e07148056c59597338c71faa1d13f57b0824262e0d7b
docs/design/rust-migration/design/views.md#86ffb00231d7c9802e95fe1a52d698ebb898e0ddda4ea6644c0240daebb5683c
```

## Reviewer output (unchanged)

The round-8 design set has no blocking or major findings. I found three minor ones, and all five round-7 findings are resolved in the text. The hash check did not run, because this mode refused the shell.

## 1. Findings (orqlet.finding/v1)

```yaml
findings:
  - id: R8-F1
    severity: minor
    location: adr-007 line 52 (decision 15, escaped bullet); manifest.yaml line 116 (EC-6)
    evidence: >
      adr-007 line 52: "every repository-controlled value in a finding, a not-run entry or a refusal
      is either left out (decision 8) or passed through this filter, with a limit of 200".
      In 0.5.2 a Finding has a structured path field (src/orqlet/domain/findings.py line 27).
      That field goes into the JSON envelope (src/orqlet/interface/cli/commands/lifecycle.py line 43,
      init.py line 160) and into the human output (render_human.py line 237).
      printable() cuts at the limit and appends "..." (src/orqlet/domain/conventions.py lines 108-110).
      representable.py lines 2-4 say a cut path must never be shown, because "an agent could act on it".
    finding: >
      Q-21 does not say whether "a value in a finding" means only the message text or also the
      finding's structured path field. If the field is included, the envelope can carry an escaped
      or cut path that does not exist. That breaks the reason the all-or-nothing filter exists, and
      it changes the value of a field that R-4 keeps. If the field is excluded, the design does not
      say so. Two implementers could reasonably make opposite choices.
    needed: >
      State whether the rule covers the message text only. If it also covers the structured path
      field, state which filter applies there: all-or-nothing (show it or leave it out) or escaping.
      Add the chosen case to BC-24.

  - id: R8-F2
    severity: minor
    location: adr-007 line 51 (decision 15, all-or-nothing bullet)
    evidence: >
      adr-007 line 51: "text from Git is decoded as strict UTF-8, as vcs_git.py line 77 does, never
      with replacement characters". It is not marked new.
      In 0.5.2 only the rev-parse output is strict (vcs_git.py line 77; also lines 52 and 91).
      Commit messages, commit subjects and remote refs are decoded with errors="replace"
      (vcs_git.py lines 234, 258 and 355).
      _subject_of cuts the bytes at _MAX_SUBJECT_CHARS * 4 before decoding (line 354), so the cut
      can split a multi-byte character.
    finding: >
      The sentence is not limited to the values the all-or-nothing filter receives. Read literally,
      it makes every Git text strict. A commit subject that is not valid UTF-8, or one cut through a
      multi-byte character, would then become an error instead of being shown escaped. That changes
      conventions-check results, which the parity criteria BC-2 and BC-4 compare, and it is not listed
      as new.
    needed: >
      Limit the strict decode to the rev-parse paths that reach the all-or-nothing filter (line 77).
      Otherwise, mark the wider rule as new and say how a cut or invalid subject is handled.

  - id: R8-F3
    severity: minor
    location: manifest.yaml lines 44-69 (security_globs); adr-007 line 51
    evidence: >
      adr-007 line 51 makes the all-or-nothing version filter depend on the Version type: ASCII
      major.minor.patch, no leading zeros, a part over 4,300 digits refused.
      In 0.5.2 representable_version accepts a value only when Version.parse does
      (representable.py lines 45-53, versions.py lines 11 and 21-26).
      The security globs list crates/orqlet-domain/src/representable.rs and conventions.rs
      (manifest lines 55-56), and paths.rs (line 53), but no versions.rs.
    finding: >
      Loosening the version parser would also loosen what reaches an agent's context through the
      hook. A change limited to the version module would not match the security globs.
    needed: >
      Add crates/orqlet-domain/src/versions.rs to the security globs. Alternatively, state that
      representable.rs checks the version pattern itself.
```

## 2. Round-7 findings

| Finding | Resolved? | Evidence |
|---|---|---|
| R7-F1: missing BC-23 cases | Yes | ADR-007 lines 27-36 list nine cases. Case 2 is the main work tree of a linked worktree. Case 3 is a bare common folder, which is refused, while its parent is not. Case 5 is doctor, sync and explain reporting ORQ-E105 or ORQ-E106. Case 1 now says "an ancestor that is a symbolic link". BC-23 (component line 85) requires every case. |
| R7-F2: scope of the escaping filter | Yes | Q-21 is answered (questions.yaml lines 416-438). ADR-007 line 52 marks the rule "New (Q-21)", sets a limit of 200, forbids Debug and Display, and names the replaced 0.5.2 sites. EC-6 (manifest line 116) matches. The remaining part is R8-F1. |
| R7-F3: domain responsibilities | Yes | ADR-001 line 10 names the Version type and the output filters. The domain node in the brief's diagram (component line 36) names versions and output filters. The ADR-003 row (line 18) reads "paths and output filters". |
| SEC-D7-1: acceptance cases | Yes | Same as R7-F1. Case 6 covers `status`, case 7 the hook, and case 9 the project id. |
| SEC-D7-2: one rule, the Python repr form, BC-24 | Yes | ADR-007 line 52 chooses one rule and replaces the raw and Python `repr` forms. BC-24 (component line 86) adds the artifact path and claim anchor with U+2028 or U+FE0F. |

I checked these other round-7 responses as applied:
- **Version width:** ADR-007 line 51.
- **Separate Git folder and hostile `.git` file:** recorded as accepted at line 18.
- **Exact `.git` name:** line 18.
- **Exit 3 for the journalled-apply refusal:** line 40 and component line 52. It matches 0.5.2, where `_upgrade_exit` maps `refused` to `ExitCode.REFUSED` (lifecycle.py lines 114-116) and that value is 3 (exit_codes.py line 10).
- **change_id must equal the file name:** line 38. It cites journal.py line 92 correctly.
- **Session-start cap of 1,200:** line 51. It matches hook_event.py lines 38 and 121.
- **Unicode scalar values:** line 51. It matches `len` at representable.py line 58.
- **Parser entry points:** BC-7 (component line 69).

## 3. Observations (not findings)

- **Q-21 rests on review.** BC-24 tests a sample of sites. No type or lint enforces "every value" or "never Debug or Display". Read literally, "never Display" also forbids displaying the escaped result; the intended meaning is clearly the raw value.
- **The 4,300-digit refusal.** It is stated for the Version type in general. In 0.5.2, callers of `Version.parse` other than `representable_version` would get a `ValueError`, not `InvalidVersion`. The resulting difference in exit status at those sites is not listed. Python's 4,300-digit limit itself was not looked up (unverified).
- **Separate Git folder on the main work tree.** The common folder is compared only "for a linked worktree" (ADR-007 line 18). With `--separate-git-dir` on the main work tree, that folder is not compared at all. The accepted-gap sentence covers only the linked case. The Git behaviour was not looked up (unverified).
- **A nested project root is not tested.** None of the nine cases has a project root below the Git top level, so the top-level comparison has no test. 0.5.2 has a nested state (vcs_git.py lines 52-53), but init refuses it (init_state.py lines 45-50). I did not trace whether other commands run there.
- **Review notes do not exist.** `reviews/architecture-reviewer-design.md` and `security-reviewer-design.md` are missing, which is consistent with the ORQ-E366 you reported. The manifest self-check still records `validate design` as a pass (manifest line 152), and the round-7 response says "These notes now exist".
- **Hashes against the manifest.** The nine artifact hashes in your prompt equal the manifest values (lines 120-131). The manifest's own hash (`9100dd…`) is recorded nowhere, so it was not compared.

## 4. Self-check

```yaml
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: design, round: 8, task: rust-migration}
  model: "Claude Opus 5.5 (as named in this agent's configuration); fresh context, no Architect conversation"
  revision: "working tree; branch rust-migration-design and HEAD NOT confirmed (shell refused)"
  checks:
    - {what: SHA-256 of the ten design files with CRLF read as LF, result: "NOT_RUN (shell refused in ask mode)"}
    - {what: given hashes vs manifest artifact hashes, how: "read manifest.yaml lines 120-131", result: "nine of nine equal; manifest's own hash not recorded, not checked"}
    - {what: round-7 responses applied, how: "compared each approved response and Q-21 with the round-8 text", result: "all applied; residual scope gaps R8-F1, R8-F2"}
    - {what: new citations, how: "read journal.py, representable.py, versions.py, exit_codes.py, upgrade.py 74-93, lifecycle.py exit mapping, vcs_git.py 38-110, 226-265, 340-356, hook_event.py (grep), vcs.py 88-117, findings.py, validate_design.py 120-133, validate_records.py 600-649, conventions.py 95-124", result: "accurate"}
    - {what: ADR-004 and ADR-006 consistency, how: "searched for journal, escaping, Version and data-directory text", result: consistent}
    - {what: "orqlet standards for, validate design, validate ledger", result: NOT_RUN}
    - {what: brief at or under 1,200 words, result: "NOT_RUN (no word count)"}
  unverified:
    - "ADR-002 was read; ADR-004, ADR-005 and ADR-006 were only searched (hashes unchanged since round 7); as-is.md was not opened"
    - "Git layout behaviour (separate Git folder, bare repositories, case of .git) and Python's 4,300-digit limit were not looked up"
    - "This review is an additional check, not a guarantee"
```

**Completed**
- Reviewed the round-8 design set: nothing blocking or major, and three minor findings (R8-F1 to R8-F3).
- Confirmed that all five round-7 findings are resolved and that the newly cited source lines are accurate.
- Not run: the hash computation, branch and HEAD confirmation, the `orqlet` commands and the word count.

**Questions**
- R8-F1: should Q-21 escape the structured `path` field of a finding, or only the message text?
- Should R8-F1 to R8-F3 be fixed before design approval, or carried into the plan as conditions?

**Next prompt**
```
Task: rust-migration
Next: architect answers R8-F1 to R8-F3 (orqlet-design) and writes reviews/architecture-reviewer-design.md; tmishari decides on design approval
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/questions.yaml, docs/design/rust-migration/reviews/
Pending: decision on R8-F1 scope; design approval by tmishari; plan approval
```

I'm noting that the un-suffixed notes are missing, which fits the expected ORQ-E366 error. There's also a mismatch: the architect's self-check in the manifest records "validate design" as a pass, while the actual output reports ORQ-E366. That record is out of step with the result until the notes get written.

I'm checking the review paths and the architect's self-check, which claims the notes exist even though the un-suffixed files don't.


## Architect's responses

Proposed, not applied. The person decides.

- **R8-F1.** Which filter applies to a finding's structured `path` field is the person's choice. My proposal: the message text is escaped under Q-21, and the `path` field passes the all-or-nothing filter, so it is shown whole or left out and never names a path that does not exist. That changes the two 0.5.2 sites that escape the field (`validate_resources.py` line 71, `validate_integrations.py` line 110), marked new. BC-24 gains the case of an artifact path with U+2028: the message shows it escaped, and the finding has no `path`. This replaces the security note's proposal to keep the field escaped.
- **R8-F2.** The strict decode applies only to the `rev-parse` output that reaches the all-or-nothing filter (`vcs_git.py` lines 52, 77 and 91). Commit messages, subjects and remote refs keep 0.5.2's replacement decode, including the byte cut before decoding (lines 234, 258, 354 and 355). The replacement character then shows as `\ufffd` through the escaping filter.
- **R8-F3.** `crates/orqlet-domain/src/versions.rs` joins the security globs.
- **4,300-digit refusal.** It is an InvalidVersion at every caller. Where 0.5.2 raised ValueError instead, the exit status may differ, and ADR-002's fixture lists that as a difference.
- **Separate Git folder on the main work tree.** The accepted-gap sentence in decision 10 covers it too: that folder is outside the work tree and is not compared.
- **Nested project root.** Decision 10 gains a test case: with the project root below the Git top level, a data directory inside the top level but outside the project root is refused.
- **Review notes and the self-check.** These notes now exist, and `validate design` runs again after the fixes, before the manifest's self-check is relied on.

## Person's decision

On 2026-11-25 tmishari chose to commit the design as it stands and carry the round-8 findings into the plan as conditions. No design file was changed after this round; this note keeps its round-8 hashes. The answers, recorded as Q-22 to Q-24: the sites that BC-24 does not test are covered by the ORQLET-SEC-002 review, as for the Clippy parser list; values from the data directory are shown as 0.5.2 shows them; a finding's structured `path` field stays escaped, as 0.5.2 does at its two sites.

Conditions the plan carries:
- SEC-D8-1: the three data-directory test cases (a case-different spelling on macOS and Windows; a missing `.` or `..` component, refused with ORQ-E105; the hook case with its setup).
- SEC-D8-2: per Q-22, ADR-007 decision 15's coverage beyond BC-24 rests on review, and the consequence that every rule has a test does not hold for it.
- R8-F1: per Q-24, the `path` field is escaped; the escaped value may name no existing file.
- R8-F2: strict UTF-8 applies only to the `rev-parse` output (`vcs_git.py` lines 52, 77 and 91); other Git text keeps 0.5.2's replacement decode.
- R8-F3: `crates/orqlet-domain/src/versions.rs` is treated as security-relevant.
- The architect's other proposed responses in these notes (UUID change ids, the wording of decisions 8 and 15, the nested-root test case, the 4,300-digit refusal, the separate Git folder) are open items the plan resolves or asks about.
