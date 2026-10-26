# Security review of the design `mcp-or-plugins`

Role: security-reviewer, run as a typed subagent in a clean context with the design set, the AS-IS file, the ledger, the cited evidence and the standards. The reviewer had no shell, so it did not run `orqlet standards` or any hash check; it read `.prompts/rules.yaml` and `.orqlet/standards.lock.yaml`. It made no network call. The author ran `orqlet standards` and `orqlet validate design`.

## Rounds

| Round | Verdict | Blocking | Main findings |
|---|---|---|---|
| 1 | FAIL | yes | A pin that skipped undeclared entries; an open value grammar; proposals that could copy credentials; no independent anchor; shared routes on unattended surfaces (recorded as the author summarised them; the reviewer's own text was not stored) |
| 2 | FAIL | 1 | Contradictory scope for entries Orqlet did not generate; the anchor depended on where the check runs; a proposal copies a whole file; messages could carry raw keys; `.env` reads; unattended-surface wording; no vendor evidence for the Atlassian address |
| 3 | PASS | 0 | 5 major: line cap failing open; YAML loader messages echoing keys; a committed entry shadowing a personal one; overstated summary; CODEOWNERS signal |
| 4 | PASS | 0 | 4 major, 8 minor (below) |

The author changed the design after every round. **The changes made after round 4 have not been reviewed by a fresh reviewer.**

## Round 4 findings and what was done

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| SR-1 | major | Deleting the declaration silently switches every check off | Fixed: `validate integrations` returns not run (exit 5) without a declaration; `doctor` and `sync` report a check that did not run when the lock records an MCP file; "delete the declaration" is added to the ways the check can be switched off |
| SR-2 | major | The declaration carries read-only labels that the entry does not enforce | Partly fixed: stated in ADR-002, the considerations and the README plan, and an information finding is printed. **Not done:** refusing `enforced_by: server` for the release-1 row. The person may decide that |
| SR-3 | major | Decisions 5 and 6 disagree on helper and static-credential keys in undeclared entries | Fixed: ADR-002 decision 6 is now a table by entry class; the closed key list is an error in every undeclared entry; the remaining limits are named |
| SR-4 | major | Limits list incomplete (inline agent-file servers, nested and parent MCP files) | Fixed in ADR-002 decision 13 and the considerations; whether `${VAR}` expands in agent files is left as an unknown (V-7) |
| SR-5 | minor | The consistent-pair gap is overstated | Fixed in the considerations |
| SR-6 | minor | Port failures and line numbers | Fixed: an `unreadable` finding; the two findings that cannot carry a line number say so |
| SR-7 | minor | Scan floor and cost undefined | Fixed: vendor prefixes, key names, quantifier cap, percent-decoding; the time limit is set in the plan after a measurement |
| SR-8 | minor | The committed-assignment check has no bounds | Fixed: same caps, line-based parse, no echo, a failure is not run |
| SR-9 | minor | Closed key sets stop at the entry level | Fixed: only `mcpServers` is examined at the top level; the `orqlet-` prefix is matched in any letter case |
| SR-10 | minor | Imprecise claims (process start, GitHub `env-ref` source, A-106) | Fixed |
| SR-11 | minor | README must say that only `validate integrations` checks the rules and how the tool is pinned | Fixed in ADR-002 decision 11 and ADR-003 decision 7 |
| SR-12 | minor | "No account name" and "no private server address" are kept by review only | Stated in ADR-004 |

## What the reviewer verified as sound (round 4)

The exact-string address table and the `ORQLET_MCP_` prefix close redirection of a reference. Parsing is fail-closed. `LocalFileSystem` refuses links. The review gap on this repository (no `CODEOWNERS`, one collaborator, HTTP 403 on protection) is disclosed and the evidence checks out. No token shape, key, certificate or banned algorithm appears in the task folder. No dependency is added.

## Open points left to the person

Q-12 (for every mode, OAuth included, Q-6 and Q-9 are not met on unattended surfaces until it is answered), the SR-2 disposition, and the residual risk that a tracked file with uncommitted local edits could be copied into a proposal (ADR-003 decision 3).

## Update after the reviews

Q-12 and Q-13 were answered by the person on 2026-10-26, after these reviews: an unattended surface uses the account of the one user who started or owns it (V-12 verifies it), and the contract is tightened in place. The design text was updated; the reviewers did not see that update.
