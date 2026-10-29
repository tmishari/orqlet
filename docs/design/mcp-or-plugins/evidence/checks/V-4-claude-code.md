# V-4 for Claude Code: does a personal entry with the same name override the project entry

Verdict: PARTLY RUN. What was observed confirms the design. Orqlet does not cover a personal entry with the same name, as the design says.

- Check: V-4 of `docs/design/mcp-or-plugins/design/adr-004-verify-client-behaviour-with-test-accounts.md`, for Claude Code only (the halves for Codex and Cursor wait for the release that enables them)
- Unknowns it answers: U-35, U-36, U-45, U-50
- Date: 2026-10-29
- Client name and version: Claude Code 2.1.303, on macOS
- Kind of test account: none. No sign-in to any real service. The client ran with an isolated home directory and no login, against a local server on the loopback interface that the tester controls. The three entries pointed at three paths of that server, so its log showed which entry the client used.
- Vendor statements beside the observations: `docs/design/mcp-or-plugins/evidence/web/claude-code-mcp-checks.md`, excerpts 3 and 5 (read 2026-10-29)

## Question

Does a personal entry with the same name, in user scope or local scope, override or merge with the project entry from `.mcp.json`? Does the client warn when two entries share a name?

## Steps as run

1. In a throwaway folder, a `.mcp.json` held one entry with a header and an address on the local server. The entry was approved by name in the user settings of the isolated configuration. `claude mcp list` ran.
2. `claude mcp add --scope user` added an entry with the same name and another path. `claude mcp list` ran.
3. `claude mcp add --scope local` added a third entry with the same name and a third path. `claude mcp list` and `claude mcp get` ran.
4. The local entry was removed and `claude mcp list` ran. Then the user entry was replaced by one with the same address as the project entry, and `claude mcp list` ran.

## Observed result

- Step 1: the client used the project entry.
- Step 2: the client still used the project entry, and printed a warning that the name is defined in several scopes with different addresses. The warning named each scope and its address and said that sign-ins are stored per address.
- Step 3: the client used the local entry, and the warning listed three scopes. `claude mcp get` named the local scope.
- Step 4: with the local entry removed, the project entry won again. With the user entry at the same address as the project entry, there was no warning.
- In every step the client connected to one address only. The vendor states that the whole entry of the highest scope is used and that fields are not merged; the headers of the entries were not logged, so a merge of fields was not observed.
- Order observed: local over project over user.

## Verdict

Confirms the design. A personal entry with the name of an `orqlet-*` entry replaces the team's entry for that user when it is in local scope, and the client warns only when the addresses differ and only in the list and the `/mcp` panel (the panel was not run). Orqlet does not read personal files, so this stays a limit that the README states (ADR-002 decision 12, ADR-004 decision 3).

Plan amendment: none requested.

## If the result differs

The result is written in this record and in the README; the considerations of the design only say that this check records which entry wins. Scanning personal files would read what Orqlet does not read and needs its own design (ADR-004 decision 3).

## Before you commit this record

- [x] The record holds no credential value, no account name, no raw client log, no address of a private server and no tenant host.
- [x] No token or sign-in was used. The personal entries were removed with the isolated home directory.
