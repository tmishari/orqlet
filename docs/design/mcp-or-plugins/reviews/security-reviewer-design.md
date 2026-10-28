# Security review of the design `mcp-or-plugins`

Role: security-reviewer, started three times as a typed subagent (`orqlet-security-reviewer`), each time in a clean context. It was given the paths of the design set, the AS-IS file, the question ledger, the cited vendor excerpts and the code, and told to ignore any earlier design in Git history. Rounds 2 and 3 were also given the notes of the earlier round, to be read after the reviewer's own pass. **No reviewer had a working shell**, so none ran `orqlet standards`, `orqlet validate design` or the tests; each read `.prompts/rules.yaml` and the code. None made a network call. The author ran `orqlet standards` and `orqlet validate design`. This note replaces the note of the design that the person asked to rewrite from scratch; that note remains in the Git history.

## Rounds

| Round | Verdict | Blocking | Major | Minor |
|---|---|---|---|---|
| 1 | PASS | 0 | 2 | 13 |
| 2 | PASS | 0 | 2 | 10 |
| 3 (delta) | PASS | 0 | 0 | 8 |

The author changed the design after every round. **The text changes that followed round 3 (listed under round 3) were not seen by a reviewer.**

## Round 1: findings and what was done

| Id | Severity | Finding (short) | Disposition |
|---|---|---|---|
| SR-1 | major | The pre-flight narrows but does not close the copy of an existing credential into a proposal | Fixed by a redesign: no existing bytes are passed to a proposal for an MCP file (ADR-003 decision 5) |
| SR-2 | major | The scan reads raw text; a JSON escape slips past it | Fixed: the validator also scans decoded text; limits stated (ADR-002 decisions 7 and 9) |
| SR-3 to SR-15 | minor | Claims stronger than the module; severity of `unreadable`; undeclared entries and `${`; the lock as a signal; wording of "reads no credential"; V-9 and "None known"; the pre-flight's gaps; rules for test accounts; stale check references; the forced labels; Q-7 wording; missing limits; the tenant host name in the ADRs | Fixed, or accepted as a stated limit (SR-12, the forced labels) |

## Round 2: findings and what was done

| Id | Severity | Finding (short) | Disposition |
|---|---|---|---|
| SR2-1 | major | The decoded scan, as specified, cannot catch an escaped key name, an escaped `Authorization` or an escaped `${` | Fixed: the validator walks the whole parsed document and tests decoded keys and strings, and scans a re-serialisation with one decoded pair per line; tests assemble escaped shapes at run time (ADR-002 decisions 6, 7, 9) |
| SR2-2 | major | The validator's claim rests on agreeing with the client's reader, and V-9 was not gated for the first release | Fixed: V-9 for Claude Code is one of the six checks of this change; V-9 also asks about escapes (ADR-004) |
| SR2-3 | minor | The proposal guard was opt-in and covered one branch | Fixed: derived from the path, in the one place that builds a proposal, for both callers |
| SR2-4 | minor | The files that carry the flag were not on the security globs | Closed: the flag is gone |
| SR2-5 | minor | The reason for the forced labels cites Q-13, which did not decide it | Fixed: the reason is the schema change (ORQLET-DET-003) that Q-13 did not cover; the person decides |
| SR2-6 | minor | The new rule text invites variable entries | Fixed and scoped in round 3 (ADR-003 decision 7) |
| SR2-7 | minor | Later rows omit V-9 and V-10; "no test can list the rows" is wrong | Fixed: later rows cite V-9 and V-10; the existing pin is extended |
| SR2-8 | minor | Deleting the declaration and renaming the entries stays silent | Stated as a limit in ADR-002 decision 11 and the considerations |
| SR2-9 | minor | Pre-approval of project servers is only in V-1 | Fixed: also in the list of routes not examined |
| SR2-10 | minor | The record scan covers credential shapes only | Fixed: it also looks for `@` addresses and `.atlassian.net`; V-5 never prints values; throwaway repositories are deleted |
| SR2-11 | minor | Two limits of the module are not stated | Fixed |
| SR2-12 | minor | No failure branch for a finding in the rendered text | Fixed: a defect, exit 70, nothing written |

## Round 3 (delta): findings and what was done

The reviewer confirmed that the four named escape bypasses are closed by the decoded scan given what the module matches, that the guard has no other route (`_unified_diff` has one caller; the preview, the JSON output and the journal carry only path, kind and hashes; a seeded file never makes a write with a before-hash), and that the host name is absent from `design/`.

| Id | Severity | Finding (short) | Disposition (text changed after the round, not reviewed) |
|---|---|---|---|
| SR3-1 | minor | EC-13 still names the removed flag | Fixed |
| SR3-2 | minor | The guard's path comparison is unspecified; a profile that names an MCP path as a pull-request template target writes into the file | Fixed: compared on the case-folded key, a test for a case variant; the profile route is stated as outside this design (ADR-003 decision 5) |
| SR3-3 | minor | The decoded scan skips entry names; TOML escapes, percent-encoding and top-level keys are not in the limits; the reason for not reading TOML is partly wrong | Fixed: the whole parsed document is walked; the limits are listed; the reason is a choice of scope |
| SR3-4 | minor | The absent-declaration signal misses an escaped name and skips unreadable files silently | Fixed: decoded names are tested when the file parses; an unreadable file gives one information finding; parent-folder links are caught |
| SR3-5 | minor | "Never stores a credential" is absolute, and `orqlet review prepare` copies the staged tree unscanned | Qualified in three places; recorded as an open point |
| SR3-6 | minor | The rule text is unscoped and reads as enforcement everywhere | Fixed: scoped to `orqlet-*` entries in a project that holds the declaration |
| SR3-7 | minor | V-5 sends a bearer to a new address; client per check is unclear | Fixed |
| SR3-8 | minor | `upgrade --check` claim is wrong; a constant is named inconsistently | Fixed |

## What the reviewer verified as sound (round 3)

`_propose` is the only place that builds a proposal from existing bytes and both callers pass through it; the preview, the JSON output, the journal and the lock hold hashes only; `CanonicalPath.parse` rejects `./.mcp.json`; a symlinked MCP file makes `plan_changes` refuse before any read; `mcp_credentials.py` has the eight public names and its description in ADR-002 decision 7 matches the code; the exit codes in the design match the code; no dependency, process, network call or digest other than SHA-256 is introduced.

## Not checked by the reviewer

Anything that needed a shell; the timing of the regexes; live vendor pages and client behaviour; the code of the validator, renderer and loader, which does not exist yet; whether `render_mcp_file` and `integration_findings` fail closed on every exception path (a plan item).

## Open points for the person

Whether the forced `read-only` and `deny` labels may stay on an entry that carries the user's full permissions; whether your own Atlassian site host may stay in the ledger, the replaced `plan.yaml` and the earlier review records (it is not in `design/`); whether `orqlet review prepare` should exclude or scan the MCP paths; whether a pull-request template target that names an MCP path should be refused; how adopters pin the tool (by version or by hash) and make the review required; whether to accept the opt-out limit or also use the lock as a second signal between the deletion and the next `upgrade`; and that the standard is met by what Orqlet generates only for Atlassian on Claude Code.
