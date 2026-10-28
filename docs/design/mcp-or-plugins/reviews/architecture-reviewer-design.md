# Architecture review of the design `mcp-or-plugins`

Role: architecture-reviewer, started three times as a typed subagent (`orqlet-arch-reviewer`), each time in a clean context. It was given the paths of the design set, the AS-IS file, the question ledger, the cited vendor excerpts and the code, and told to ignore any earlier design in Git history. Rounds 2 and 3 were also given the notes of the earlier round, to be read after the reviewer's own pass. **No reviewer had a working shell** (its shell tool refused every command), so none ran `orqlet standards`, `orqlet validate design` or a hash check; each read `.prompts/rules.yaml` (the 15 rules that `standards_applied` lists) and the code. The author ran `orqlet standards for --phase design --role architect` and `orqlet validate design`. This note replaces the note of the design that the person asked to rewrite from scratch; that note remains in the Git history.

## Rounds

| Round | Verdict | Blocking | Major | Minor |
|---|---|---|---|---|
| 1 | PASS | 0 | 4 | 15 |
| 2 | PASS | 0 | 3 | 7 |
| 3 (delta) | PASS | 0 | 0 | 11 |

The author changed the design after every round. **The text changes that followed round 3 (listed under round 3) were not seen by a reviewer.**

## Round 1: findings and what was done

| Id | Severity | Finding (short) | Disposition |
|---|---|---|---|
| AR-1 | major | When no declaration exists, a recorded seeded `.mcp.json` becomes an orphan and the lock forgets it, so a signal that uses the lock disappears | Fixed: the signal does not use the lock (ADR-002 decision 11; ADR-003 context and decision 6) |
| AR-2 | major | `integration_findings` cannot return a "not run" reason | Fixed: it returns findings only; the use case does the existence check |
| AR-3 | major | The closed list of forbidden keys has no owner; TOML-only items are enforced nowhere | Fixed: a private constant of `validate_integrations.py` with the key names that the evidence gives; the Codex file gets the scan only; limits stated |
| AR-4 | major | How `RenderRequest.integrations` is set is not stated | Fixed: `dataclasses.replace` in `compose` |
| AR-5 to AR-19 | minor | Underscore rule for every changed module; contract object in the port; per-client selection; `init` versus the registry's precedent; `explain`; the pre-flight; ORQ-I030 for every project; golden claims; build-order gaps; scope and globs; diagram arrows; factual slips; unbacked statements; simplicity of `env-ref` | Fixed or closed by the redesign, except AR-6 (kept with a reason, ADR-003 decision 4) and AR-19 (partly: `env-ref` stays a specification; some checks moved out of this change's plan) |

## Round 2: findings and what was done

| Id | Severity | Finding (short) | Disposition |
|---|---|---|---|
| AR2-1 | major | Opting out leaves `orqlet-*` entries, so `doctor` warns for ever and exits 1 | Fixed: the opt-out is "delete the declaration and rename or remove the `orqlet-*` entries"; the exit code is stated (ADR-002 decision 11, considerations) |
| AR2-2 | major | The absent-declaration branch reads three files and the design does not say what unreadable ones do | Fixed: no error without a declaration, one information finding that does not change the exit code; the error is for the declared branch (ADR-002 decision 8) |
| AR2-3 | major | The proposal guard was a flag that each adapter must set: it fails open, with no end-to-end test | Fixed by a redesign: the guard is derived from the path and sits in `_Builder._propose`; an `upgrade`-level sentinel test (ADR-003 decision 5) |
| AR2-4 | minor | Files that carry the flag were not on the security globs | Closed: the flag and its files are gone |
| AR2-5 | minor | Seam gaps: where the existence check is, where the rendered text is scanned, how `name_problems` serves a stdio server | Fixed (ADR-002 decisions 5 and 7, ADR-003 decision 6) |
| AR2-6 | minor | Build-order step 4 bundles four things; the golden is late | Fixed: ten steps; the golden at the adapter step |
| AR2-7 | minor | Sequence 1 draws the builder reading the file; a diagram edge is missing | Fixed |
| AR2-8 | minor | Side effects of the guard: no old-to-new diff; a permanent proposal | Accepted and documented (ADR-003 decision 5) |
| AR2-9 | minor | Wording, a wrong citation, `env-ref` shown as holding a boundary | Fixed |
| AR2-10 | minor | Existing test comments cite replaced decisions; the architecture-document corrections are incomplete; the meta `paths` question | Fixed: the plan updates the comments; the list is extended; `.mcp.json` stays in `paths` (ADR-003 decisions 7 and 8) |

## Round 3 (delta): findings and what was done

The reviewer confirmed that the seven round-2 changes are real and match the code: the guard has two callers and both pass through `_propose`; the import into the domain is allowed; classification, `--check`, `--resume` and an interrupted run converge; the signature `integration_findings` can carry the absent branch; EC-1 to EC-16 agree across the files.

| Id | Severity | Finding (short) | Disposition (text changed after the round, not reviewed) |
|---|---|---|---|
| AR3-1 | minor | EC-13 still names the removed flag | Fixed |
| AR3-2 | minor | Three diagram edges missing | Fixed |
| AR3-3 | minor | The `upgrade`-level sentinel test cannot run at step 4 | Fixed: it is in step 5; step 4 has `build_plan`-level tests |
| AR3-4 | minor | The table pin already exists on `main`; the record-scan test has no step | Fixed: the existing tests are the pin and are extended; the scan test is in step 8 |
| AR3-5 | minor | Who emits the information finding for a proposal, and when | Fixed: `upgrade.py`, for every seeded proposal item on an MCP path, code in the `ORQ-I53x` family |
| AR3-6 | minor | Check ids and counts differ between three places | Fixed |
| AR3-7 | minor | Which client each of the six checks is for | Fixed: Claude Code only for the first release |
| AR3-8 | minor | "A fourth client needs one constant" is understated | Fixed: the three places are listed and a test fails when they diverge |
| AR3-9 | minor | Sequence 2 draws `integration_findings` doing the existence check | Fixed |
| AR3-10 | minor | A symlinked `.mcp.json` with a declaration makes `plan_changes` refuse | Fixed: stated, with a test |
| AR3-11 | minor | This note was stale | Fixed by this update |

## What the reviewer verified as correct (round 3)

The path-derived guard against `changeplan.py`, `classify.py` and the import contracts; the absent branch against `_diagnose` and the exit codes (`warning` gives 1, `error` gives 5, not run gives 5); the ten build steps; EC-1 to EC-16 and the scope and security globs; the unchanged comments of `mcp_credentials.py` against ADR-002 decisions 2, 3, 4, 6, 7, 8 and 9.

## Not checked by the reviewer

Anything that needed a shell (hashes, `orqlet standards`, `orqlet validate design`, the tests, import-linter); vendor facts A-54 to A-142 beyond a spot check; the code of the renderer, the validator and the loader, which does not exist yet.

## Open points for the person

Whether `init` should render `.mcp.json` from a hand-written declaration (the design defers it to `upgrade`); whether a plain `orqlet-` text match is right for `.codex/config.toml`; whether a team with its own servers may keep a proposal item on every run; whether the forced labels may stay (ADR-002 decision 10); the workflow version (0.3.3 proposed) and when to record it in `releases.json`; that tightening v1 in place makes `upgrade` refuse for any team whose hand-written declaration breaks the new rules.
