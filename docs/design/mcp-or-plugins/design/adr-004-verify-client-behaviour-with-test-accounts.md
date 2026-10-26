# ADR-004: Client behaviour that the vendor text does not state is verified with test accounts, and some checks gate the entries

Status: proposed. It becomes accepted when the design pull request is merged by an authorised person.

## Context

- The accepted AS-IS ends with 76 material unknowns; 38 of them (Q-8) are things that a vendor page does not say: whether a client asks for approval before connecting to a project MCP server and whether it asks again when an address changes; where OAuth tokens are stored and who can read them; which same-named entry wins; what an unset variable becomes; where a variable is expanded; which surfaces load project entries; how a plugin's credential is set. Others (Q-7, Q-9, Q-10) concern surfaces, shared identities and the way each user gets a token.
- The design's own matrix of the three clients and four integrations says "Designed; not tested" (A-39). The contract has a `verification` field with `not-tested` and `verified` (A-9).
- The person's answer to Q-8 is yes: checks with test accounts may be planned. Orqlet never calls a model, starts an agent or contacts a server (ORQLET-NOMODEL-001), so it cannot run them. A person with test accounts does.
- Unattended surfaces (cloud agents, web sessions and code-review contexts from Q-7, and CI, which runs the same way) have no developer at a keyboard, and the evidence does not say whose credential they use (AS-IS unknowns under Q-7 and Q-9; open question Q-12).

## Decision

1. **A check record** is a file `docs/design/mcp-or-plugins/evidence/checks/V-<n>-<client>.md`: date, client name and version, the kind of test account, the steps, the observed result and a verdict. It holds no credential value, no account name, no raw client log and no address of a private server, and a repository test runs the credential scan of ADR-002 over every committed check record (the scan covers credential shapes only; the rules "no account name" and "no private server address" are kept by review). V-10 sends a real stored token, so that test account's session is revoked after the check and the value stays out of the record. Test accounts use dedicated tokens with the smallest scopes, revoked after the check. A check that sends a test token to a changed address (V-8, V-10) uses a destination that the tester controls and a dummy value. Checks that change an administrator setting (V-13) or use a cloud agent (V-12) run in a separate test organisation or tenant, never in a production one; the team's own site (`cisco-cxe.atlassian.net`, Q-14) is not used for them unless the person says so in the check record.
2. **What a check gates.**
 - A **`client-native-oauth` entry** holds no credential field, so the contract and the pin protect its content. Whether a stored sign-in could follow a changed address is another question: it is known for Claude Code (sign-ins are per endpoint, A-69) and unknown for Codex and Cursor. An OAuth entry is therefore generated for Codex only after V-4 (the project file is honoured and whether a project entry replaces or merges with a user entry of the same name), V-5 and V-10, and for Cursor only after V-3 (replace or merge), V-5 and V-10. Its `verification` stays `not-tested` until V-5 and V-7 are recorded for that client. This change enables Claude Code only.
 - An **`env-ref` entry** is generated for a client only after a later release enables it in the tool's closed table (ADR-002 decision 2), and that release cites the records for that client: V-1 (Claude Code), V-3 (Cursor) or V-4 (Codex) for approval and expansion and the unset case, V-2 for Claude Code's name, and V-8 for a changed address. The table is empty for `env-ref` in this change, because the adopter's repository cannot read this repository's check records. If V-8 shows that the client connects to a changed address and sends the variable without asking, `env-ref` entries are not generated for that client and the client gets OAuth entries only; the offline comparison cannot replace that stop. If a client reads the name as empty, the name is not changed to get around it, because a rename could defeat a protection that the vendor built (a vendor does strip credential variables from a helper's environment, A-64; whether any client does so for `headers` is what V-2 records): the entry is not generated for that client, and the gap is written down.
 - The other checks decide what the documents may claim, not whether the rules of ADR-002 apply.
3. **The checks:**

| Check | Client | Question | If the result is different |
|---|---|---|---|
| V-1 | Claude Code | Does it ask for approval before connecting to a server from a project `.mcp.json`, in an interactive session and in a `claude -p` run, and does a pulled change of `url` or of a header ask again? | See decision 2 and V-8 |
| V-2 | Claude Code | Does `${VAR}` expand in `headers` for names of the form of ADR-002 decision 3, and what does an unset variable become? | Decision 2 |
| V-3 | Cursor | Does `${env:NAME}` expand in `headers`, is there an approval prompt for `.cursor/mcp.json`, does the project entry replace or merge with a global entry of the same name, and what does an unset variable become? | Decision 2; a merge instead of a replacement is written in the considerations |
| V-4 | Codex | Does a project `.codex/config.toml` with `[mcp_servers.*]` load in a trusted project, does `bearer_token_env_var` work, what happens when the variable is unset (the text says it may connect unauthenticated, A-94), how does a project become trusted, and which entry wins over a user entry of the same name? | If a project file is not honoured, Codex is a documented gap |
| V-5 | all three | Where are OAuth sign-ins stored (keychain or file), with what file mode, keyed by what, and per operating-system user? | A world-readable fallback is written in the considerations as a risk to the user's own credential |
| V-6 | all three | Does a personal same-name entry (for example `orqlet-github` in user or local scope) override the project entry, and does the client warn? | Written in the considerations; a scan of personal files would read what B-2 says Orqlet does not read and needs its own design |
| V-7 | all three | On each surface of Q-7 (terminal, IDE extension, desktop app, cloud agent or web session, review context), does the project entry load, with or without a prompt, and which files does the client read (nested folders, parent folders, user files)? | Each surface that does not load project entries is a written gap in ADR-001 |
| V-8 | all three | If a pull request changes only the `url` of a server and keeps the header or variable name, does the client connect and send the variable to the new address without asking? | Decision 2 |
| V-9 | all three | Does the variable's value reach child processes, the agent's own shell tool, transcripts, logs, telemetry or crash reports? Does a debug mode or the MCP list print resolved headers? Do apps started outside a shell see the variable, and how does a user set it without shell history? | The results go into the README instruction and the considerations |
| V-10 | Codex, Cursor | After an address changes, is a stored OAuth token reused for the new address (Claude Code keys sign-ins per endpoint, A-69)? | A reuse is written as a redirection risk for OAuth entries |
| V-11 | all three | Do the client's JSON or TOML readers agree with the validator about duplicate keys, comments, escapes and key case? | A difference becomes a rule or a documented gap |
| V-12 | all three | On a cloud agent, a review context and CI, whose identity does an entry use: the signed-in user's own, or an environment that several people share? | Q-12 says the account of the one user who started or owns the surface; a surface that cannot do that, or that uses a shared environment, is a gap for every entry, OAuth included, and gets no entry |
| V-13 | GitHub, Atlassian | Is the read-only address form of the GitHub remote server accepted with a PAT and with OAuth and does it block write tools; can an Atlassian administrator enable personal API tokens without service-account keys; do OAuth scope pins hold? | Atlassian stays OAuth-only (ADR-002 decision 2); the read-only mechanism is written as unenforceable for what the check does not show |

4. The checks that concern plugins (a Codex plugin's credential, Cursor per-developer values, Claude Code `userConfig` persistence) are **not** planned now: ADR-001 produces no plugin output. They are the conditions C2 and C4 of a later design.
5. The plan phases for V-1 to V-13 are marked as needing a person. A phase that depends on a check lists it as a precondition.

## Consequences

- The documents never claim a behaviour that was only read. A claim that rests on a check names the record.
- The work is real: thirteen checks across three clients, each needing accounts. They are small and mostly independent.
- A check can find that a client lacks a behaviour that the design assumed. The result lands in the considerations and may remove an entry kind for that client; it does not silently change this design.
- Check records are evidence files and go through the pull request like any file.

## Rejected alternatives

- **Decide from documentation only** (the other answer to Q-8). The 38 unknowns include the ones that decide whether a credential can be redirected or exposed.
- **Block all generation until every check passes.** OAuth entries hold no credential field, and the contract and pin rules protect the entry without the checks; only claims about client behaviour need them.
- **Rename a variable to dodge a client's empty-reading of credential-looking names.** It could defeat a protection that the vendor built (A-64 shows one for helpers; V-2 records whether `headers` has one).
- **Automate the checks in CI.** There is no verified headless path for the clients, and CI would need real accounts and credentials.
- **Record results as free text in the architecture document.** A check record needs a date, a client version and a verdict that a reviewer can see change.
