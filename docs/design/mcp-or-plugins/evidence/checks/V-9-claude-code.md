# V-9 for Claude Code: does the client's JSON reader agree with the validator

Verdict: PARTLY RUN. The reader was observed through `claude mcp list`, not through a session. It differs from the validator in two places, both on the safe side.

- Check: V-9 of `docs/design/mcp-or-plugins/design/adr-004-verify-client-behaviour-with-test-accounts.md`, for Claude Code only (the halves for Codex and Cursor wait for the release that enables them)
- Unknowns it answers: ADR-004 names no unknown for V-9
- Date: 2026-10-29
- Client name and version: Claude Code 2.1.303, on macOS; `orqlet validate integrations` of this branch
- Kind of test account: none. No sign-in to any real service. The client ran with an isolated home directory and no login, against a local server on the loopback interface that the tester controls. The validator ran on the same bytes with a declaration for the one server of this release.
- Vendor statement beside the observations: none. The page read on 2026-10-29 does not describe the JSON reader, so the table below rests on the observations alone.

## Question

Does the JSON reader of Claude Code agree with `orqlet validate integrations` about duplicate keys, comments, escapes and key case? Does a JSON escape in a key or a value, for example an escaped dollar sign before an opening brace, change what the client expands or sends? Which top-level keys other than `mcpServers` does the client read?

## Steps as run

For each case one `.mcp.json` was written, with the entry that Orqlet renders for the declared server and one probe entry that points at the local server. The same bytes went to `claude mcp list` (the probe entry was approved by name) and to `orqlet validate integrations`. The local server logged which path the client reached. The variable `PROBEVAR` was set to a test word in the client's environment.

Cases: a baseline; a key twice in one entry; an entry name twice; a line comment; a block comment; a trailing comma; a letter of a key written as a JSON escape; a variable reference in the address; the same with the dollar sign written as an escape; the top-level key in another letter case; the field names of an entry in another letter case; the entry under a top-level key other than `mcpServers`; a byte order mark at the start.

## Observed result

| Case | Client | Validator | Agree |
|---|---|---|---|
| baseline | loads the probe | passes | yes |
| key twice in an entry | uses the last value | refuses (ORQ-E534) | no, the validator is stricter |
| entry name twice | uses the last entry | refuses (ORQ-E534) | no, the validator is stricter |
| line or block comment | refuses the file as invalid JSON | refuses (ORQ-E534) | yes |
| trailing comma | refuses the file as invalid JSON | refuses (ORQ-E534) | yes |
| escaped letter in a key | decodes it and reads the key | reads it as the same key | yes |
| variable reference in the address | expands it from its environment | refuses (ORQ-E538) | yes (refused) |
| the same with an escaped dollar sign | expands it after decoding | refuses (ORQ-E538) | yes (refused) |
| top-level key in another letter case | refuses the file (no `mcpServers`) | reports the declared entry as missing (ORQ-E536) | yes |
| field names in another letter case | skips the entry as invalid, with a warning | counts it as an undeclared entry | yes |
| entry under another top-level key | does not read it | does not count it | yes |
| byte order mark | reads the file | refuses (ORQ-E534) | no, the validator is stricter |

- The client expands a variable after it decodes the JSON text, so an escaped dollar sign does not hide a reference from the client. The validator scans the decoded text and reports it.
- Not run: the same cases through a session instead of `claude mcp list` (the list may not share every code path of a session), and the TOML reader of Codex and the JSON reader of Cursor.

## Verdict

Differs from the design in two places, both on the safe side, so the README states them as limits and no plan amendment is requested: the client accepts a key twice (last wins) and a byte order mark, and the validator refuses both. A project whose `.mcp.json` starts with a byte order mark works in the client and turns `orqlet validate integrations` red until the mark is removed.

Plan amendment: none requested.

## If the result differs

A difference is fixed in the validator or written as a limit (ADR-004 decision 3). Here it is written as a limit.

## Before you commit this record

- [x] The record holds no credential value, no account name, no raw client log, no address of a private server and no tenant host.
- [x] No token or sign-in was used.
