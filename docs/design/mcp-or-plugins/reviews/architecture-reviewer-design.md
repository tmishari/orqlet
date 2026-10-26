# Architecture review of the design `mcp-or-plugins`

Role: architecture-reviewer, run as a typed subagent in a clean context with the design set, the AS-IS file, the ledger, the cited evidence and the standards. The reviewer had no shell, so it did not run `orqlet standards` or any hash check; it read `.prompts/rules.yaml` (15 rules, the same 15 as `standards_applied`). The author ran `orqlet standards for --phase design --role architect` (also per path) and `orqlet validate design`.

## Rounds

| Round | Verdict | Blocking | What the blocking finding was |
|---|---|---|---|
| 1 | FAIL | yes | No enforcement path (doctor, CI), an unclear seam and scope, an unclear contract shape and pin, scan bypasses, and an unsourced GitHub address (recorded here as the author summarised them; the reviewer's own text was returned in the session and was not stored) |
| 2 | FAIL | 2 | Nothing built the pinned entry that validator and renderer share; the same two rules for unlisted entries |
| 3 | FAIL | 1 | Build order put the contract rules before the domain module that they call |
| 4 | FAIL | 1 | The refusal of an untracked MCP file also refused the file that Orqlet wrote itself, so a re-run did not converge |

The author changed the design after every round. **The changes made after round 4 have not been reviewed by a fresh reviewer.** The person must treat the round 4 verdict as the last independent one.

## Round 4 findings and what was done

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| AR-1 | blocking | Untracked-file refusal in `plan_changes` refuses Orqlet's own `.mcp.json`; breaks re-run, `--resume`, `--check`; undermines ORQLET-SAFE-001 and TEST-002 | Fixed: ADR-003 decision 3 now refuses only a planned proposal that comes from an untracked file or whose text the scan flags; a file that Orqlet wrote or that equals the render yields no proposal. The fault test of ORQLET-TEST-002 covers the interrupted run |
| AR-2 | major | Seam signatures: `validate_integrations` file argument cannot reach `load_integrations`; `plan_changes` has no way to get the declaration; absent versus invalid; messages to findings | Fixed: `load_integrations(project, loader, path)` returns `Finding`s with a stated absent, invalid, valid convention; public `DECLARATION_PATH` (EC-20); `plan_changes` keeps its signature and needs no declaration; new ORQ codes are named in the plan |
| AR-3 | major | The committed schema is said to change but validators leave it unchanged | Fixed: the contract rules are validators; the schema is unchanged; the workflow package changes in two files (rule text and meta); ADR-002, ADR-003, container, considerations and EC-13 aligned; the schema file is removed from the scope |
| AR-4 | major | Release 1 ships API for paths that cannot run (`referenced_variables`, `variable` parameters) | Kept with a stated reason: the signatures stay stable when `env-ref` is enabled, `rendered_entry` refuses a variable, and `referenced_variables` has a release-1 caller on undeclared entries (ADR-002 consequences). Not moved. The person may disagree |
| AR-5 | major | The Atlassian entry is not read-only; disclosed once | Fixed: ADR-002 decision 5, considerations (Security), an information finding by `validate` and `doctor`, and the README plan. Worded as unknown where the evidence is silent (U-10, U-11, U-12, V-13) |
| AR-6 | minor | Phase numbering of the fixture update | Fixed: phase 2 everywhere, with the golden regeneration stated |
| AR-7 | minor | EC-13 omits `verification: verified` refusal and stdio registration refusal | Fixed in EC-13 and ADR-002 |
| AR-8 | minor | `registration.name == id` contradicts the architecture document Section 24.4 | Fixed: `registration.name` equals `orqlet-<id>` |
| AR-9 | minor | Wording and citation slips (process start, `ORQLET_DATA_DIR`, Q-7 and CI, line numbers, base class source, Codex managed configuration) | Fixed |
| AR-10 | minor | Material unknowns U-10 to U-12 not carried forward | Carried into ADR-002 and the question Q-14 |
| AR-11 | minor | `considerations.md` has no artifact kind and no hash; `.orqlet/proposals/**` missing from scope; container diagram says adapters seed files | Fixed: the hash is recorded in the self-check, the path is in the scope, the diagram edges are corrected |
| AR-12 | minor | Raw unknown key in contract error location; `registered_for` keying; empty file | Fixed in ADR-002 decisions 5 and 9 |

## What the reviewer verified as correct (round 4)

More than 40 citations to AS-IS facts, evidence lines and code lines held. Layering of `domain.mcp_credentials`, the contract validators, the validator, the renderer and the plan is permitted by the import-linter contracts. The eleven original public names and their signatures match what `python_api.py` computes. Trust boundaries, exit codes and the one-entry-kind release 1 are consistent across the artifacts.

## Open points left to the person

Q-12 (identity of unattended surfaces), Q-13 (versioning waiver for the contract) and the AR-4 disposition. A design pull request reviewer should check that the changes after round 4 resolve AR-1 to AR-3.

## Update after the reviews

Q-12 and Q-13 were answered by the person on 2026-10-26, after these reviews: an unattended surface uses the account of the one user who started or owns it, and the contract is tightened in place. The design text was updated; the reviewers did not see that update.
