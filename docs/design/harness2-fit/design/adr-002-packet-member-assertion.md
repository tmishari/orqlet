# ADR-002: Keep review records out of review packets by path, not by text scan

Status: proposed. The rule is recorded here and added to proposal Section 6.14.1 at implementation; the code lands with the v0.5 review-packet plan, not in this task.

## Context

- Harness² keeps grader verdicts and answer keys out of its improver's evidence with two guards: a path filter (`leak_globs`) and a scan of file text for seven literal markers such as `deterministic_eval_summary`. Its own docstring calls the scan a "tripwire" (AS-IS S-12).
- Orqlet's v0.5 review packet is a closed list of members bound by a stored manifest (design §6.14.1). A reviewer is given the test record and the knowledge-impact record, never another reviewer's record. A path is excluded from the digested lists only when it meets three conditions: an exact path pattern, a regular file, and a schema-valid content that matches the path; a file that fails any condition "is an ordinary input" (design §6.14.1; `src/orqlet/domain/evidence_artifacts.py:63-77`, `is_excluded`). The proposal states that no directory is excluded. Its list of what the exclusion applies to names `code_tests`, `pre_image`, `context` and `knowledge`; it does not name the `diff` member.
- The CI result binding is never written into the repository (design §6.14.1, "never written back"), so a CI verdict is not a path and no path rule applies to it.
- Design-review notes (`docs/design/<task>/reviews/<role>-design.md`) are named under `reviews` in the design manifest but match none of the three patterns. If the packet took every file that the manifest names, a later reviewer would be handed the design reviewers' verdicts.
- The built `review prepare` exports every entry of the staged tree as `snapshot/<path>` and has no assertion (`src/orqlet/application/usecases/review_prepare.py:110-131`). Design §22.0 lists it as code to rework.

## Decision

1. The `design` component of the packet takes the files named by the manifest under `artifacts` and its `as_is_ref`, never the notes named under `reviews`.
2. The builder reads the list of changed paths from Git. For each path that matches the review-record pattern exactly (`parse_evidence_path(path)` returns the kind `review`), it asks the existing check `evidence_file_ok` (`src/orqlet/application/usecases/binding_inputs.py:192-212`), which applies the rule's three conditions through `is_excluded`. A valid record is left out of every list **and out of the `diff`** (the builder gives Git a literal pathspec that excludes it). The proposal text for the `diff` member is clarified accordingly.
3. Any other path at a review-record path is not left in: a record that fails a condition, a record that is deleted in the range, or a path that cannot be parsed makes the builder return `NOT_RUN`, name the path, and write no packet. A test record and a knowledge-impact record are not refused: they are the `evidence` members.
4. The match is on the parsed canonical path, case-sensitive as Git is. The review-record pattern is the one in the evidence-artifact module; when the v0.5 plan adds `code-reviewer` to it, the builder follows because there is one place.
5. No member text is scanned for verdict words.

## Consequences

- The reviewers get a deterministic floor: the tool itself never hands one reviewer another's valid record, in a list or in the diff, and a malformed record at a record path stops the packet instead of travelling to the next reviewer.
- The refusal adds one failure mode: a malformed record at a record path stops review preparation until it is fixed or removed. That is fail-closed on purpose. It is not a directory rule: any other file under `reviews/` stays an ordinary input.
- What it does not catch: a verdict inside any other file or a comment; a record at a path that is not an exact match, including a case variant, which is an ordinary input by the rule; a design-review note that sits in the same diff as an ordinary changed file; anything a reviewer reads outside the packet with its own tools (design §6.14.1 says those reads are "outside every digest"); a path that the developer adds with `--context`, other than a record path, that only looks harmless. Independence beyond the list rests on the role instructions and on the human approver.
- Until the v0.5 packet exists, the built `review prepare` exports the staged tree with no assertion. This ADR does not change that code.
- Leaving a record out of the diff needs a literal pathspec on `Vcs.diff_patch`, which has none today (`src/orqlet/application/ports/vcs.py:113`): a port change in the v0.5 plan. The AI reviewers then never read the free text of a valid record; the proposal's disclosure lints on evidence files (design §6.14.1, rule 3) exist for that reason, and I found no such lint in the built validators.
- The change is a few lines in the packet builder and its tests, and it depends on the v0.5 plan.

## Rejected alternatives

- **A marker scan like Harness²'s.** Orqlet's own repository contains the schema names, the words `verdict`, `PASS` and `FAIL` and the record patterns in its documents, schemas and tests, so the scan would refuse legitimate packets or need an exception list, and a literal-string scan proves little.
- **Refuse any member under a `reviews/` directory.** The proposal says that no directory is excluded and that a source file placed under `reviews/` stays under review; a directory rule would let one junk file stop every review.
- **Refuse only valid records.** A valid record is already left out, so the rule would fire only on a builder bug and would miss the malformed record that the next round most likely meets.
- **Check in the review-record validator instead of the builder.** The packet lives outside the repository; the validator sees a record afterwards and cannot know what the reviewer was handed.
- **Nothing beyond the closed list.** The list already makes a leak unlikely, but the `diff` member is not covered by the exclusion in the text, and a later change to the list could add a verdict without any test failing.
