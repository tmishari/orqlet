# Architecture review of the rust-migration design, round 7 (allowed by the person)

Reviewer: orqlet-arch-reviewer subagent (6659989c-0c01-4d58-bd71-d33da24a0afd), fresh context, model named as Claude Opus 5.5.
Earlier rounds: `architecture-reviewer-design-r1.md` to `-r6.md`. The person allowed this seventh round on 2026-11-25, after round 6.

Prompt defect, recorded by the architect: the prompt sent to this reviewer was cut off by mistake right after its heading "Design file hashes of this round". So the reviewer got no hash list, no list of what changed, and no output format. It read the paths named in the prompt, compared the design with the round-6 notes, and checked the artifact hashes recorded in the manifest. The architect kept this output and did not rerun the review, so that results were not chosen between two runs. The security reviewer of this round got the full prompt with these hashes, which the architect computed before both launches:

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

# Round-7 architecture review: rust-migration design

Reviewer: orqlet-arch-reviewer, model named as Claude Opus 5.5 in this agent's configuration. Fresh context: I read only the paths given and the 0.5.2 source they cite.

## Summary

The review found **nothing blocking or major, and three minor findings**. All three round-6 architecture findings and all four round-6 security findings are applied as the person approved them. The new output-filter decision (ADR-007 decision 15) has accurate citations, and I found no 0.5.2 filter call site that it misses.

**Checks that did not run:**
- **Hash check.** The hash list in your message was empty, and this mode refused the shell. So no SHA-256 value was checked.
- **What the manifest shows instead.** It records new hashes for `component.md` (`eba00c…`), `views.md` (`86ffb0…`) and ADR-007 (`04a277…`). ADR-001 to ADR-006 keep their round-6 values. A recorded value does not prove that the file bytes match.
- **Branch, revision and orqlet commands.** Neither the branch nor HEAD was confirmed. `orqlet standards for`, `validate design` and `validate ledger` did not run. I compared the design with the rendered rule texts instead.
- **Missing folder.** `research/` does not exist. I used `docs/design/rust-migration/as-is.md` in its place.

## Findings (orqlet.finding/v1)

```yaml
findings:
  - id: R7-F1
    severity: minor
    location: component.md line 85 (BC-23); adr-007 line 18 (decision 10), lines 19-20
    evidence: >
      The approved R6-F1 response says "BC-19 gains a linked-worktree case". The approved R6-F2
      response says "doctor, sync and explain report ORQ-E105, or ORQ-E106 when Git fails" and
      "A data directory in the main work tree is refused".
      BC-23 reads: "With the data directory in the repository (ADR-007 decision 10), also below a
      linked ancestor: writing commands refuse, with ORQ-E106 when Git fails; doctor, sync and
      explain report it, create nothing and read no journal there".
      Decision 10 (line 18) uses "the deepest existing ancestor ... to its real path", so "a linked
      ancestor" reads as a symbolic link in the path, not as a linked worktree.
    finding: >
      Three cases have no explicit criterion:
      - a linked worktree whose data directory lies in the main work tree;
      - the round-6 fix itself: for a bare repository or a separate Git folder, the common folder is
        compared, never its parent;
      - doctor, sync and explain reporting ORQ-E106 when Git fails.
      A port that still takes the parent of any common folder (the over-refusal of R6-F1), or one
      that refuses in doctor when Git fails, passes BC-23 as written. ADR-007 line 46 says every
      rule has a criterion.
    needed: >
      In BC-23, name the linked-worktree case (main work tree refused). Name the bare-repository
      case (the data directory under the bare folder's parent is not refused; under the bare folder
      itself it is). Name "doctor, sync and explain report ORQ-E106 when Git fails". Reword "linked
      ancestor" as "an ancestor that is a symbolic link".

  - id: R7-F2
    severity: minor
    location: adr-007 line 41 (decision 15, escaped filter); adr-007 line 39 ("carried over exactly")
    evidence: >
      adr-007 line 41: "Escaped, for every repository value inside a finding or a not-run entry".
      Line 39: "carried over exactly". 0.5.2 escapes only selected values.
      validate_as_is.py lines 153-159 put fact_id and artifact_path unescaped into the same
      ORQ-E338 message that escapes evidence_path through printable(evidence_path, 200).
      printable(text, limit) needs a limit from the caller (conventions.py line 100), and a value
      that 0.5.2 never escapes has none.
    finding: >
      The rule's scope ("every repository value") contradicts "carried over exactly" and the list
      of 0.5.2 users that follows it. If "every" is meant, the change is wider than 0.5.2, is not
      marked new (so ADR-002's fixture would not list it), and has no stated limit. If only the
      0.5.2 users are meant, the word "every" is wrong. The implementer cannot tell which.
    needed: >
      Either limit the rule to the listed 0.5.2 users (plus the change id that is marked new), or
      mark the wider rule as new and state the limit for values that 0.5.2 shows unescaped.

  - id: R7-F3
    severity: minor
    location: adr-001 line 10 (decision 2); component.md line 36 (diagram); adr-003 line 18
    evidence: >
      adr-007 line 42 places the filters in crates/orqlet-domain/src/representable.rs and
      conventions.rs, and manifest lines 55-56 add both files to the security globs.
      adr-001 line 10, "It holds CanonicalValue and digest_of, the line-range hash, paths, findings,
      the change plan, the glob matcher and the UTC timestamp formatter", and component.md line 36
      do not name them. adr-003 line 18 still gives the category crate as "Unicode categories for
      paths", although decision 15 also uses it for Co, Cn, Zl and Zp.
    finding: >
      The documents that state the domain crate's responsibilities were not updated with decision
      15.
    needed: >
      Add the output filters (and the version type they use, versions.py) to ADR-001 decision 2
      and to the domain node of component.md. Widen the ADR-003 row to "paths and output filters".
```

## Round-6 findings: are they resolved?

| Finding | Status | Evidence |
|---|---|---|
| R6-F1 / SEC-D6-2, defining the main work tree | Resolved in the text | ADR-007 line 18: the parent of the common folder only when it is named `.git`, otherwise the common folder itself. The criterion is missing (R7-F1). |
| R6-F2 / SEC-D6-3, criteria | Mostly resolved | BC-23 covers doctor, sync and explain creating nothing and reading no journal, the hook printing `{}`, an empty variable, and an unquoted id. Gaps are in R7-F1. |
| R6-F3, stale text | Resolved | The failures row (component line 54) and D-5 (views line 62) now have ORQ-E106. EC-4 names every journal reader. EC-6 limits the hook to the project root it finds. |
| SEC-D6-1, output filters | Resolved | Decision 15 cites `representable.py` 1-62 (ranges 24-35, accurate) and `conventions.py` 100-124 (accurate). Every 0.5.2 caller of `printable()` and `representable_*` is listed (search confirmed). Decision 8 and EC-6 are reworded, BC-24 is added, and both modules are in the globs. Scope wording is in R7-F2. |
| SEC-D6-4, unquoted project id | Resolved | ADR-007 line 24 and BC-23. |

## Observations (not blocking)

- **Version width.** In 0.5.2 the parts of a Version are unbounded integers (`versions.py` lines 11 and 26). If the Rust Version uses a fixed-width integer, the all-or-nothing filter drops some values that 0.5.2 shows. The design does not say which.
- **Separate Git folder.** In that layout the real main work tree is never compared, because the common folder is compared instead. The design does not record this as accepted. The security reviewer may want it recorded.
- **Comparing the `.git` name.** The design does not say whether the name test is case-sensitive on macOS and Windows.
- **Exit status of the new refusal.** For the journalled-apply ORQ-E131 refusal, it is given only by reference ("the exit status of the upgrade refusal"). In 0.5.2 that refusal is a `refused` result with a finding, not a raised error (`upgrade.py` lines 80-92). The failures row has no exit status.
- **Decision 7 has no criterion.** The Clippy parser entry points have none, which contradicts ADR-007 line 46. This has been the case since earlier rounds.
- **Review paths.** The manifest's `reviews` entries name `architecture-reviewer-design.md` and `security-reviewer-design.md`, which do not exist.
- **Architect's self-check.** The "pass" results it lists for `validate design` and `validate ledger` were not re-run in this round.

```yaml
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: design, round: 7, task: rust-migration}
  model: "Claude Opus 5.5 (as named in this agent's configuration); fresh context"
  revision: "working tree; branch and HEAD not confirmed (shell refused)"
  checks:
    - {what: SHA-256 of design files, result: "NOT_RUN (shell refused; the prompt's hash list was empty)"}
    - {what: round-6 responses applied, how: "compared each approved response with the current text", result: "7 of 7 applied; criteria gaps R7-F1"}
    - {what: cited source for decision 15 and decision 10, how: "read representable.py, conventions.py 85-124, hook_event.py 105-166, status.py 165-221, user_scope.py, versions.py, upgrade.py 74-92, apply_plan.py 40-64; searched for all filter callers", result: accurate}
    - {what: Q-1 to Q-20, result: "all answered; Q-16 to Q-20 followed"}
    - {what: "orqlet standards for, validate design, validate ledger", result: NOT_RUN}
  unverified:
    - "Git's layout behaviour (bare repositories, separate Git folder, core.worktree) was not looked up, by rule"
    - "as-is.md was only searched (U-8, U-10); the evidence/web files were not re-read"
    - "This review is an additional check, not a guarantee"
```

**Completed**
- I reviewed the round-7 design set: nothing blocking or major, and three minor findings.
- All seven round-6 findings are applied, and the new citations are accurate.
- Not run: the hash check, branch confirmation, and the `orqlet standards`/`validate` commands.

**Questions**
- Your hash list arrived empty. Can you send it again, so the hashes can be checked against the files?
- Should decision 15 escape every repository value in a finding (new behaviour), or only the values 0.5.2 escapes (R7-F2)?
- Should R7-F1 to R7-F3 be fixed before design approval, or carried into the plan as conditions?

**Next prompt**
```
Task: rust-migration
Next: architect answers R7-F1 to R7-F3 (orqlet-design); person decides on design approval
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/reviews/
Pending: decision on R7-F2 scope; hash list for round 7; design approval by tmishari; plan approval
```

## Architect's responses

Proposed, not applied. The person decides.

- **R7-F1 (and SEC-D7-1).** ADR-007 decision 10 gets a numbered list of test cases, and BC-23 requires every case on it. The cases are: a linked worktree with the data directory in the main work tree is refused; with a bare or separate common folder, that folder is compared and its parent is not; doctor, sync and explain report ORQ-E105, or ORQ-E106 when Git fails, create nothing and read no journal; `status` shows its not-run entry and reads nothing from that data directory; the hook prints `{}`; an empty `ORQLET_DATA_DIR` counts as unset; an ancestor that is a symbolic link resolves before the comparison. "Linked ancestor" becomes "an ancestor that is a symbolic link". The list lives in ADR-007, so the brief stays within 1,200 words.
- **R7-F2 (and SEC-D7-2).** The scope of the escaping filter is the person's choice, asked as Q-21. Either way, decision 15 drops the word "every" or marks the wider rule as new with a limit, and EC-6 matches the choice.
- **R7-F3.** ADR-001 decision 2 and the domain node of the brief's diagram name the output filters and the Version type. The ADR-003 row for the category crate reads "paths and output filters".
- **Version width.** The Rust Version keeps unbounded parts. Each part is stored as its decimal text, which `versions.py` line 11 already keeps free of leading zeros, and parts are compared by length and then by text. A part longer than 4,300 digits is refused, which matches the ValueError of Python's default integer limit that `representable.py` line 51 catches. So the all-or-nothing filter shows the same values as 0.5.2.
- **Separate Git folder.** Recorded in decision 10 as accepted: only the common folder is compared, which is the bound that `rev-parse` gives without reading `core.worktree`.
- **`.git` name.** It is compared exactly as it is spelt, lowercase. Another spelling falls under the common-folder rule, which compares the folder itself. That compares more narrowly, never more widely.
- **Exit status of the journalled-apply refusal.** The failures row gives exit 3 (`src/orqlet/interface/cli/exit_codes.py` line 10).
- **Decision 7 criterion.** BC-7 gains: each parser entry point listed in decision 7 fails Clippy outside the documents module.
- **Review paths and the architect's self-check.** These notes now exist, and `validate design` and `validate ledger` run again after the fixes.

## Person's decision

On 2026-11-25 tmishari chose to apply the proposed fixes and run an eighth round with both reviewers. For the scope of the escaping filter, recorded as Q-21: every repository value in a finding, a not-run entry or a refusal is escaped with a limit of 200 or left out, never shown raw (new behaviour). The fixes are applied in the round-8 design files; this note keeps its round-7 hashes.
