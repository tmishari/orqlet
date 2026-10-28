# ADR-004: Client behaviour that the vendors do not state is checked with test accounts

Status: proposed (a design pull request approves it). Task: `mcp-or-plugins`. Reads: AS-IS unknowns U-23 to U-76; ledger answers Q-8, Q-12.

## Context

- After reading the vendor texts, 76 material unknowns remain, and most are about what a client does: whether it asks before connecting to a server from a committed file, which fields expand a variable, where a sign-in is stored, which same-named entry wins, and which surfaces load a project file (U-32 to U-69). Orqlet cannot read this from any repository file, and it runs no client (ORQLET-NOMODEL-001, A-53).
- The person allowed the design to plan checks with test accounts in each client (Q-8).
- This change enables one entry kind, which holds no credential field and rests on documented behaviour: a project `.mcp.json` entry and per-endpoint sign-ins in Claude Code (A-55, A-58, A-69). The other rows depend on behaviour that is not stated.
- The unattended surfaces (Q-12) and the Atlassian administrator settings (U-74, U-75) cannot be checked on the team's own Atlassian site by accident; the person named that site in the answer Q-14.
- The ledger text of Q-14 names checks V-12 and V-13 of the design that this one replaces. Their questions are V-10 here.

## Decision

1. **A check record** is a file `docs/design/mcp-or-plugins/evidence/checks/V-<n>-<client>.md` with the date, the client name and version, the kind of test account, the steps, the observed result and a verdict. It holds no credential value, no account name, no raw client log and no address of a private server. A repository test runs the credential scan of ADR-002 decision 7 over every committed check record, and also looks for an `@` address and a host ending in `.atlassian.net`; the scan covers credential shapes only, and the rules "no account name" and "no private server address" are otherwise kept by review. V-5 inspects file modes and key names, never values.
   - **Accounts.** Every check that sends a token or a sign-in anywhere uses a throwaway test account with the smallest scopes, in a test organisation or tenant, never a production one and never the team's own Atlassian site unless the person says so in the record. Tokens are revoked after the check.
   - **Canaries.** A check that sends a value to a changed address or looks for a value in logs (V-2, V-5, V-7, V-8) uses a canary value or a throwaway sign-in that grants nothing, and the destination is one that the tester controls; a stored OAuth token (V-5) is revoked afterwards.
   - **Repositories.** A check that runs a cloud agent or a review context (V-6, V-10) uses a throwaway repository, so that no private code goes to a vendor cloud, and the repository is deleted after the check.
2. **What a check gates.**
   - An **OAuth entry** holds no credential field, so the contract and the pin protect its content. Whether a stored sign-in could follow a changed address is known for Claude Code (sign-ins are per endpoint, A-69) and unknown for Codex and Cursor. An OAuth entry is therefore generated for Codex only after V-1, V-3, V-4 and V-5, and for Cursor only after V-1, V-4 and V-5. This change enables Claude Code only.
   - An **`env-ref` entry** is generated for a client only after a later release enables it in the closed table (ADR-002 decision 2), and that release cites the records for that client: V-1, V-2, V-7 and V-8, and V-3 for Codex. The table has no `env-ref` row in this change, because an adopter's repository cannot read this repository's check records. If V-7 shows that a client connects to a changed address and sends the variable without asking, `env-ref` entries are not generated for that client. If a client reads a variable name as empty, the name is not changed to get around it (a rename could defeat a protection that the vendor built, as with the helper's stripped variables, A-64); the entry is not generated for that client and the gap is written down.
   - Every later row, whatever its mode, also cites V-9 and V-10 for its client, because the reader of the file and the unattended surfaces decide whether the standard holds for it. The gate rests on the design of the release that adds a row: that design must cite the records it depends on, and its reviewers check the citation. The tests of `mcp_credentials` already pin the single row (`tests/unit/domain/test_mcp_credentials.py:383-399` and the property test at `test_mcp_credentials_properties.py:421-428`); the plan keeps them and extends them to a fixed grid of addresses and clients, so that adding a row changes a test and has a reviewer.
   - The other checks decide what the documents may claim, not whether the rules of ADR-002 apply.
3. **The checks.**

   | Check | Client | Question | If the result differs |
   |---|---|---|---|
   | V-1 | all three | Does the client ask for approval or trust before connecting to a server from a committed project file (Claude Code `.mcp.json` in an interactive session and in a `claude -p` run; Cursor `.cursor/mcp.json`; Codex `.codex/config.toml` in a trusted project), and does a pulled change of `url` or a header ask again? Can a project settings file pre-approve project MCP servers (not in the evidence; asked because it would remove the prompt)? (U-37, U-51, U-52, U-60, U-64) | A client that connects without asking gets no `env-ref` entry (decision 2) |
   | V-2 | all three | Which forms expand a variable in `headers` (`${VAR}`, `${env:NAME}`, `bearer_token_env_var`) for names of the form of ADR-002 decision 3, and what does an unset variable become? (U-33, U-34, U-54; A-94) | No `env-ref` entry for that client |
   | V-3 | Codex | Does a project `.codex/config.toml` with `[mcp_servers.*]` load in a trusted project, and how does a project become trusted? (U-41, U-64) | If a project file is not honoured, Codex is a documented gap |
   | V-4 | all three | Does a personal same-name entry (user or local scope, or Cursor's global file) override or merge with the project entry, and does the client warn? (U-35, U-36, U-45, U-50) | Written in the considerations; scanning personal files would read what Orqlet does not read and needs its own design |
   | V-5 | all three | Where are OAuth sign-ins stored (keychain or file), with what file mode, keyed by what, per operating-system user? After an address changes, is a stored token reused for the new address? (U-32, U-46, U-47, U-59, U-65) | A world-readable fallback or a reuse is written as a risk to the user's own credential and gates Codex and Cursor OAuth entries |
   | V-6 | all three | On each surface of Q-7 (terminal, IDE extension, desktop app, cloud agent or web session, review context), does the project entry load, with or without a prompt, and which files does the client read (nested folders, parent folders, user files)? (U-23 to U-31) | Each surface that does not load project entries is a written gap in the README |
   | V-7 | all three | If a pull request changes only the `url` of a server and keeps the variable name, does the client connect and send the variable to the new address without asking? | Decision 2 |
   | V-8 | all three | Does the variable's value reach child processes, the agent's own shell tool, transcripts, logs, telemetry or crash reports? Does a debug mode or the MCP list print resolved headers? Do apps started outside a shell see the variable, and how does a user set it without shell history? (U-34) | The results go into the README instruction |
   | V-9 | all three | Do the client's JSON or TOML readers agree with the validator about duplicate keys, comments, escapes and key case? Does a JSON escape in a key or a value (for example an escaped `$` before `{`) change what the client expands or sends? Which top-level keys other than `mcpServers` does each client read? | A difference is fixed in the validator or written as a limit |
   | V-10 | Claude Code, Cursor, Codex | Can a cloud agent, a review context or CI use a committed entry with the account of the one user who started or owns the surface (Q-12)? Can a client request fewer Atlassian scopes than the consent offers (A-146)? In a separate test tenant, does an administrator's setting for API-token authentication allow personal tokens without service-account keys? (U-23, U-70 to U-75) | Where a surface cannot, Q-6 and Q-9 are not met there for any mode, and the README says so. If scopes cannot be limited, the README says the entry carries the user's full permissions |

4. **Where the checks run in the plan.** They are performed by a person with test accounts and are not code. The first release's claims depend on V-1 (Claude Code), V-4, V-5 (Claude Code), V-6, V-9 (Claude Code) and V-10, so the plan lists those as its last phase before the final `orqlet upgrade`. V-2, V-3, V-7 and V-8 gate only entries that this change does not build; they are run by the release that proposes the row they gate. The README says which checks have run, and a check that was not run is reported as not run. For the first release the six checks are run for Claude Code only; the halves of V-1, V-4, V-5, V-6, V-9 and V-10 for Codex and Cursor are paid by the release that enables that client. The Claude Code OAuth row ships whether or not V-1, V-4, V-5, V-6, V-9 and V-10 have been run, because its content holds no credential; what the README may claim about prompts, precedence, storage and surfaces depends on them.

## Consequences

- No code path depends on an unchecked client behaviour in this change.
- The first release is narrow on purpose: one server, one client, one mode. Widening it is a release that cites records and adds a table row with tests, not a change to the contract.
- The cost for the first release is six sessions with test accounts and a test tenant for V-10; the other four are paid when a row needs them.
- The records are evidence files in this repository, so they are reviewed in a pull request like the rest.

## Rejected alternatives

- **Decide from the documentation alone.** Q-8 allows checks, and the unknowns that matter for a credential (V-5, V-7, V-8) cannot be settled by reading.
- **Generate all rows now and mark them `not-tested`.** The label does not stop a client from sending a variable to a changed address, and a shipped path that nobody ran is the risk this ADR exists to avoid.
- **Check from Orqlet itself, by starting the clients.** Orqlet starts no agent and runs no client (ORQLET-NOMODEL-001).
- **A scanner for personal files.** It would read user-scope files that can hold tokens (A-35, A-53).
- **Run all ten checks before the first release.** Four of them gate entries that the first release does not build.
