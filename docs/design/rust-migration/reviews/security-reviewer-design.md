# Security review of the rust-migration design, round 8 (allowed by the person)

Reviewer: orqlet-security-reviewer subagent (a71a7d09-abee-46fc-a970-17abee329954), fresh context, model named as Claude Opus 5.5.
Earlier rounds: `security-reviewer-design-r2.md` to `-r7.md`. The person allowed this eighth round on 2026-11-25, after round 7.
Design file hashes of this round, given to the reviewer in its prompt:

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

# Round-8 security review of the rust-migration design

Round 8 found nothing blocking or major. It found two minor issues, both about test coverage:

- **SEC-D8-1:** the data-directory test cases miss two of the rules they are meant to cover.
- **SEC-D8-2:** the new escaping rule (from the person's answer to Q-21) is checked by only three sample cases.

All five round-7 findings are resolved in the text.

**Hash check: not run.** The shell was refused in this mode. As a substitute, I compared the hashes you gave with the artifact hashes in `manifest.yaml` (lines 120–131). All nine are equal. The manifest does not record its own hash (`9100dd05…`), so I could not check that one. Branch and HEAD are not confirmed.

## 1. Findings (orqlet.finding/v1)

```yaml
findings:
 - id: SEC-D8-1
 severity: minor
 location: adr-007 decision 10 (line 18) and its test cases (lines 26-35); component.md BC-23 (line 85); adr-007 Consequences (line 57)
 evidence: >
 adr-007 line 18 states rules that no test case covers:
 - the check "appends the missing components, which may not be . or ..";
 - it compares "component by component and case-insensitively on macOS and Windows".
 Test cases 1-9 (lines 27-35) test neither rule. Case 7 (line 33) reads "The hook prints {}
 and exits 0" and gives no setup, whereas line 22 makes {} depend on the data directory
 being, or lying inside, the project root the hook finds by searching for .orqlet/.
 BC-23 (line 85) requires only "Every test case listed in ADR-007 decision 10".
 Line 57 says "Each rule above has a criterion in the brief ... so a missing rule fails a
 test instead of passing review."
 finding: >
 A port could still pass BC-23 in three ways:
 - it compares paths case-sensitively on macOS, where the file system is case-insensitive
 by default (unverified);
 - it joins a missing ../ step by text, as in ORQLET_DATA_DIR=<outside>/new/../../<repo>/data;
 - its hook prints {} for a reason other than the data-directory rule.
 Whether canonicalize on macOS returns the case stored on disk was not looked up
 (unverified). The case rule is therefore the only stated defence against a data directory
 spelt in another case.
 needed: >
 Add three test cases to decision 10:
 - on macOS, a data directory spelt with a different case of the project root is refused;
 - a missing component . or .. is refused, with its code named;
 - case 7 names its setup: the data directory in or below the project root that the hook
 finds by .orqlet/, with an event that would otherwise add context.

 - id: SEC-D8-2
 severity: minor
 location: adr-007 decision 15, escaped bullet (line 52); component.md BC-24 (line 86); adr-007 Consequences (line 57)
 evidence: >
 adr-007 line 52 (Q-21): "every repository-controlled value in a finding, a not-run entry or
 a refusal is either left out (decision 8) or passed through this filter, with a limit of
 200 ... and is never formatted with Debug or Display."
 BC-24 (line 86) tests three sites: a commit subject, a manifest artifact path and a claim
 anchor.
 0.5.2 has more sites that show such values raw, for example validate_records.py line 748
 ({entry.path} ... {path}) and line 753 (ORQ-W434), and validate_design.py lines 127 and 130.
 Line 57 claims that a missing rule fails a test. Decision 7 (line 15), by contrast, says
 its own list "is a partial net" caught by review.
 finding: >
 The rule covers every site, but its test covers only three sample sites. A port that keeps
 Display formatting at an untested site, such as validate_records line 748, passes BC-24.
 Line 57 overstates what the test guarantees for this rule.
 needed: >
 Do one of the following:
 - state in decision 15, as decision 7 does, that sites outside the BC-24 cases are covered
 by the ORQLET-SEC-002 review;
 - or add a structural guard, for example finding, not-run and refusal constructors that
 accept only fixed text or the output of printable(), with a BC criterion for it.
```

## 2. Round-7 findings

| Finding | Status | Evidence |
|---|---|---|
| SEC-D7-1: acceptance cases missing from BC-23 | Resolved | Decision 10 now lists numbered test cases (ADR-007 lines 26–35), and BC-23 requires every one (component line 85). Each case asked for in round 7 is now listed: the main work tree (case 2), a bare common folder compared but its parent not (case 3), ORQ-E106 for `doctor`, `sync` and `explain` (case 5), and the `status` not-run entry (case 6). "Linked ancestor" is reworded as "an ancestor that is a symbolic link" (case 1). The remaining gaps are new (SEC-D8-1). |
| SEC-D7-2: two readings of the escaping filter's scope | Resolved | There is now one rule, marked new under Q-21 with a limit of 200 (line 52). It names 0.5.2's raw and `repr` forms (`validate_design.py` 127 and 130, `validate_records.py` 607, 619 and 647, `paths.py` 32–47; all checked against the source). Decision 15 now reads "applied more widely (Q-21)" instead of "carried over exactly" (line 50). EC-6 matches (manifest line 117). BC-24 gains the U+2028 and U+FE0F case (line 86). Q-21 is answered (`questions.yaml` lines 415–438). The remaining gap is new (SEC-D8-2). |
| R7-F1: same as SEC-D7-1 | Resolved | Same evidence as SEC-D7-1. |
| R7-F2: escaping scope not marked new and no limit | Resolved | Line 52 marks the rule new, sets the limit at 200, and keeps the 0.5.2 sites at their own limits. Every site listed matches a `printable(` call in `src/orqlet`. |
| R7-F3: domain documents not updated | Resolved | ADR-001 line 10 now names the Version type and the output filters. The domain node at component line 37 lists "versions, output filters". ADR-003 line 18 now reads "paths and output filters". |

The round-7 observations are applied:

- **Session-start cap:** the 1,200-character limit is named (line 51; `hook_event.py` lines 38 and 121).
- **Length unit:** path length counts Unicode scalar values (line 51).
- **Strict decode:** text from Git is decoded as strict UTF-8 (line 51; `vcs_git.py` line 77).
- **Version width:** parts are kept as decimal text, and a part over 4,300 digits is refused (line 51; `versions.py` line 11, `representable.py` line 51).
- **Change id:** it must equal the journal file name (line 38; `journal.py` line 92).
- **`.git` name and hostile `.git` file:** the name test is exact `.git`, and both gaps are recorded as accepted (line 18).
- **Exit status:** the journalled-apply refusal exits 3 (line 40, component line 52; `exit_codes.py` line 10).
- **Decision 7 criterion:** BC-7 now covers the parser entry points (component line 69).

## 3. Observations (not findings)

- **Data-directory values are outside Q-21.** The rule names only repository-controlled values. Since Q-16 the data directory lies outside the repository, so the file name that ORQ-E136 names (line 42) is covered by neither filter. In 0.5.2 that name is shown unquoted (`journal.py` line 77), but only after a CanonicalPath parse, which refuses Cc, Cf and Cs characters (line 71, `paths.py` lines 23 and 35–37). Other 0.5.2 change-id errors used `repr` (lines 94 and 129). How Python's `repr` escapes U+2028 was not looked up (unverified). The risk is low because the folder is the user's own, mode 0700.
- **Shell syntax in advice is narrowed, not closed.** A change id now has to name an existing file, but `printable()` keeps `;`, `$(` and backticks. The ORQ-E131 advice is a command a person may copy (`upgrade.py` lines 85–86). Both 0.5.2 and 1.0.0 create change ids as UUIDs (`system.py` line 16). A UUID rule, like the one for project ids, would close this.
- **Wording of "never formatted with Debug or Display".** The output of `printable()` is itself placed into the message with Display. "Never formatted directly" would say what is meant.
- **Decision 8 and decision 15 read differently.** Decision 8 says refusals "report only the rule and the line" (line 16). Decision 15 allows an escaped value in a refusal (line 52).
- **The finding's `path` field.** Q-21 covers every repository value "in a finding", so this field seems to be included. 0.5.2 already escapes it at `validate_resources.py` line 71 and `validate_integrations.py` line 110. An escaped non-ASCII path in the JSON envelope does not name an existing file. Whether that is intended is not stated.
- **Separate Git folder, not linked.** For a plain worktree whose Git folder lives elsewhere, the Git folder is never compared, because `linked` is false (`vcs.py` lines 102–105). A data directory there is accepted. It is outside the work tree, so this fails toward accepting, which is low risk.
- **No secrets** and no language-model SDK appear in the files I read.

## 4. Self-check

```yaml
schema: orqlet.self-check/v1
checked_against:
 role: security-reviewer
 phase: design
 round: 8
 task: rust-migration
 model: "Claude Opus 5.5 (as named by the client); fresh context, no Architect conversation"
 revision: "working tree of rust-migration-design as stated in the prompt; branch and HEAD NOT confirmed (shell refused); 0.5.2 source read as the working tree, assumed equal to 3e3c311"
checks:
 - {what: "SHA-256 of the ten design files with CRLF read as LF", how: "perl + shasum", result: "NOT_RUN (shell refused in ask mode)"}
 - {what: "given hashes vs manifest artifact hashes", how: "read manifest.yaml lines 120-131", result: "all nine equal; manifest's own hash not recorded, not checked"}
 - {what: "orqlet standards for / validate design / validate ledger", result: "NOT_RUN (shell refused)"}
 - {what: "read in full: adr-007, component.md, views.md, manifest.yaml, adr-001, adr-003, both round-7 notes; Q-16, Q-18, Q-19, Q-21", how: read, result: done}
 - {what: "round-7 resolutions", how: "compared each needed item and approved response with the round-8 text", result: "all five resolved"}
 - {what: "new citations", how: "read journal.py, versions.py, representable.py, conventions.py 95-124, vcs_git.py 40-89, vcs.py 85-119, exit_codes.py, upgrade.py 74-93, paths.py 15-54, status.py 165-234; grep hook_event.py, printable( callers, validate_design/records sites", result: "accurate"}
unverified:
 - "ADR-002, ADR-004, ADR-005, ADR-006 not reread (hashes unchanged from round 7)."
 - "as-is.md not read this round."
 - "macOS canonicalize case behaviour, Git common-dir output for separate or hostile layouts, Rust Debug escaping, Python repr escaping: not looked up."
 - "This review is an additional check, not a guarantee."
```

## Completed
- Reviewed the round-8 design set: nothing blocking or major, two minor findings (SEC-D8-1, SEC-D8-2).
- All five round-7 findings are resolved, and the new citations match the 0.5.2 source.
- Not run, because the shell was refused: the hash computation, `orqlet standards for`, `orqlet validate`, and confirming the branch and HEAD.

## Questions
- SEC-D8-2: should the sites that BC-24 does not test be left to review, or should a structural guard be added?
- Should data-directory values, such as the file name in ORQ-E136, also go through the escaping filter? Q-21 covers only repository values.
- Should SEC-D8-1 and SEC-D8-2 be fixed before design approval, or carried into the plan as conditions?

## Next prompt
```
Task: rust-migration
Next action: architect answers SEC-D8-1 and SEC-D8-2 and writes reviews/security-reviewer-design.md; tmishari decides on design approval
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/questions.yaml, docs/design/rust-migration/reviews/
Pending approvals: design approval by tmishari; plan approval
```

## Architect's responses

Proposed, not applied. The person decides. The indentation of the YAML blocks above is as the reviewer's output arrived.

- **SEC-D8-1.** Decision 10 gains three test cases. On macOS and Windows, a data directory spelt with a different case of the project root is refused. A missing `.` or `..` component is refused with ORQ-E105. Case 7 names its setup: the data directory is in or below the project root that the hook finds by `.orqlet/`, with an event that would otherwise add context.
- **SEC-D8-2.** The choice between relying on review and adding a structural guard is the person's. If a guard: the domain message type is built only from fixed `&'static str` parts and values that went through `printable()`, so a raw value does not compile into a finding, a not-run entry or a refusal, and a new criterion checks this. If review: decision 15 says, as decision 7 does, that sites outside the BC-24 cases are covered by the ORQLET-SEC-002 review, and the consequence line stops claiming a test for them.
- **Data-directory values.** Whether the escaping filter also covers values from the data directory, such as the file name in ORQ-E136, is the person's choice. My proposal is yes, as new behaviour, because it costs one call and leaves no unfiltered path.
- **Change id.** New: a change id must be a lowercase hyphenated UUID, as 0.5.2 creates them (`src/orqlet/adapters/system.py` lines 14-16) and as project ids already are. That closes shell syntax in the advice. A record with any other id is unreadable (ORQ-E136).
- **Wording.** "Never formatted with `Debug` or `Display`" becomes "never formatted directly with `Debug` or `Display`".
- **Decision 8 and decision 15.** Decision 8 reads: refusals report the rule and the line, and show a repository value only through decision 15.
- **The finding's `path` field.** The architecture reviewer raised the same point as R8-F1. My proposal, put to the person: the field passes the all-or-nothing filter, shown whole or left out, which is new for the two 0.5.2 sites that escape it (`validate_resources.py` line 71, `validate_integrations.py` line 110).
- **Separate Git folder, not linked.** Recorded in decision 10 as accepted. The data directory there is outside the work tree.

## Person's decision

On 2026-11-25 tmishari chose to commit the design as it stands and carry the round-8 findings into the plan as conditions. No design file was changed after this round; this note keeps its round-8 hashes. The answers, recorded as Q-22 to Q-24: the sites that BC-24 does not test are covered by the ORQLET-SEC-002 review, as for the Clippy parser list; values from the data directory are shown as 0.5.2 shows them; a finding's structured `path` field stays escaped, as 0.5.2 does at its two sites.

Conditions the plan carries:
- SEC-D8-1: the three data-directory test cases (a case-different spelling on macOS and Windows; a missing `.` or `..` component, refused with ORQ-E105; the hook case with its setup).
- SEC-D8-2: per Q-22, ADR-007 decision 15's coverage beyond BC-24 rests on review, and the consequence that every rule has a test does not hold for it.
- R8-F1: per Q-24, the `path` field is escaped; the escaped value may name no existing file.
- R8-F2: strict UTF-8 applies only to the `rev-parse` output (`vcs_git.py` lines 52, 77 and 91); other Git text keeps 0.5.2's replacement decode.
- R8-F3: `crates/orqlet-domain/src/versions.rs` is treated as security-relevant.
- The architect's other proposed responses in these notes (UUID change ids, the wording of decisions 8 and 15, the nested-root test case, the 4,300-digit refusal, the separate Git folder) are open items the plan resolves or asks about.
