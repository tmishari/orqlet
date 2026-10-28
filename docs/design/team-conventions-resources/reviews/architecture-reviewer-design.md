# Architecture review of the design `team-conventions-resources`

Role: architecture-reviewer, run as a typed subagent (`orqlet-arch-reviewer`) in a clean context, three times, each time with the design set, the AS-IS file, the ledger, the stored web excerpts, the standards in `.prompts/rules.yaml` and read access to the source and the tests. The reviewer had no shell: it did not run `orqlet standards`, `orqlet validate design`, `canonical_signature`, lint, mypy, import-linter or the tests, and it did not recompute any hash; the author did the hashes and the validation.

## Rounds

| Round | Verdict | Blocking | Major | What the blocking or most serious findings were |
|---|---|---|---|---|
| 1 | FAIL | 1 | 12 | The expected changes did not cover the public API of the change (the extractor reads every public name, assignments included); the claim "a team edit makes no proposal" held only for edits made through a command; the registry's input path into `compose`, `init` and `explain` was undefined; an invalid registry could delete generated files; the profile rebuild in `_with_pr_template` would reset the new fields; `glob_match` is not linear; `url_problems` had no stated implementation; the build order broke CI from phase 2 |
| 2 | PASS | 0 | 5 | `validate resources` CLI shape against the documented CI text; the `evidence cite` header guard would refuse 38 existing evidence files; an unexplained scope entry; Unicode-category drift across Python versions; nothing caught a registry change merged without regenerated files |
| 3 | PASS | 0 | 5 | The refusal code survives only in `init`; a removed tool skill leaves an empty folder that `doctor` reports as ORQ-E153; a manifest entry says the opposite of three documents about `summary`; the CI step assumed a CLI hash that no code records; phase 8 against the checks that gate its text |

The author changed the design after every round. **The changes made after round 3 have not been seen by a fresh reviewer** (the dispositions below). The person must treat the round 3 verdict as the last independent one.

## Round 3 findings and what was done

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| AR-1 | major | The stable code of `InitRefused` survives only in `init`; `upgrade` and `explain` print ORQ-E100 | Fixed: `init` and `upgrade` return the status `refused` with the finding; `explain` builds no plan, so it previews without the resource files and prints the finding (ADR-002 decision 6, component rule 7) |
| AR-2 | major | A removed tool skill leaves an empty folder that `doctor` reports as ORQ-E153 | Fixed: `doctor` ignores a reserved-prefix folder that holds no file; a test covers remove, upgrade, doctor (ADR-002 decision 7, component) |
| AR-3 | major | EC-58 contradicts three documents on `summary` | Fixed: "a login entry only summary" in the manifest, ADR-002, S-4 and the component view |
| AR-4 | major | The CI step assumes a CLI hash and an install route that do not exist | Fixed: the claim is narrowed to the version `cli.pinned` names, written in the workflow file; no hash; no published package is stated (ADR-003 decision 5, S-15) |
| AR-5 | major | Phase 8 ships text that V-3, V-6, V-7 gate | Fixed: phase 8 ships advice with the limits "not observed"; ADR-005 names the statements that wait for a check; ADR-002 aligned |
| AR-6 | minor | `commit_subjects` "up to 200" has no overflow signal | Fixed: the port returns at most 201 |
| AR-7 | minor | Helpers, constants and aliases in existing modules are public by default | Fixed: component rule 6 applies to existing modules; they are private or declared |
| AR-8 | minor | Who quotes the profile values and how a left-out finding reaches `compose` | Fixed: the application quotes; `conventions_view` returns the view and the findings; the adapter writes the lines |
| AR-9 | minor | DET-001 and the retrieval date in rendered files | Fixed: the date is registry data copied by a pure function, not a timestamp of the render (ADR-002 decision 2) |
| AR-10 | minor | Counts of evidence files; classify range | Fixed |
| AR-11 | minor | Sequence 1 calls `add_resource` at init | Fixed: `resources_with`; the diagram has the edge |
| AR-12 | minor | Circular advice for a missing recorded registry; `explain` refusing | Fixed: restore from Git or write an empty valid file; `explain` does not refuse |
| AR-13 | minor | After a hand edit the lock is stale until `upgrade`; parallel branches conflict on the lock line | Fixed: stated as intended, with the way out (ADR-002 decision 5) |
| AR-14 | minor | Command options, `list --json` shape and `remove` output unspecified | Fixed (ADR-002 decision 7) |
| AR-15 | minor | The fixed template text has no home and no versioning | Fixed: `workflow/templates/*.md`, read through the `WorkflowSource` port; a manual expected change |
| AR-16 | observation | ORQ-L002 text is wrong for resource rules; new limits not listed | Fixed: the text is reworded; the new limits are private constants |
| AR-17 | observation | Heuristics in `url_problems`, duplicated resolution and scanning, `printable` location | Carried to the plan: a smaller grammar, a shared scanner and the home of `printable` are plan decisions; reasons are written in the ADRs |
| AR-18 | observation | Q-11 and Q-12 are narrowed; how onboarding finds the open conventions | Fixed for the second (the skill step names the information finding); the first is listed for the person in ADR-005 decision 6 |
| AR-19 | observation | The block overflow rule; hyphen rule of ids | Fixed |

## What the reviewer verified as correct (round 3)

More than 30 citations to AS-IS facts and to source lines held. The component view can be built without a forbidden import; contracts calling the domain has precedent. The added `classify` branch leaves every existing test row unchanged and `UP_TO_DATE` advances the record. `merge_rendered` and `build_plan` support a second shared block in `AGENTS.md`. `ScopedRule.file_class` allows `PROTECTED` and the skill renderer already writes it. `FactValue` defaults with a question are valid and `open_questions` is an explicit list, so the new facts stay out of ORQ-W181. The extractor claims (every public name is read, a manual entry does not cover one, class-line-only changes are invisible) are right, the sampled signatures are in canonical form, and the 15 standards are all listed and apply.

## Open points left to the person

The narrowing of "checked" (Q-11) to two of eight conventions; the deferral of the fetcher and the unnamed Context7 (Q-12); the reading of Q-13 as all three routes; fault tests only for the new write paths (Q-14); ASCII-only text fields; the added `classify` branch; `branch_patterns` next to the prose `branch_naming`. All are listed in ADR-005 decision 6. A reviewer of the design pull request should check that the changes after round 3, in particular ADR-002 decisions 5 to 9, the template home, and the CI step, resolve AR-1 to AR-5.
