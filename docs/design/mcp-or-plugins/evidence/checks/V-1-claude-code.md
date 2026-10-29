# V-1 for Claude Code: does the client ask before it connects to a server from a committed file

Verdict: PARTLY RUN. What was observed confirms the design. The dialog of an interactive session was not run.

- Check: V-1 of `docs/design/mcp-or-plugins/design/adr-004-verify-client-behaviour-with-test-accounts.md`, for Claude Code only (the halves for Codex and Cursor wait for the release that enables them)
- Unknowns it answers: U-37, U-51, U-52, U-60, U-64
- Date: 2026-10-29
- Client name and version: Claude Code 2.1.303, on macOS
- Kind of test account: none. No sign-in to any real service. The client ran with an isolated configuration directory and no login, against a local server on the loopback interface that the tester controls. The server answered the handshake and logged only the path that was reached.
- Vendor statements beside the observations: `docs/design/mcp-or-plugins/evidence/web/claude-code-mcp-checks.md`, excerpts 1, 2 and 4 (read 2026-10-29)

## Question

Does Claude Code ask for approval before it connects to a server from a committed `.mcp.json`, in an interactive session and in a `claude -p` run? When a pulled change alters the `url` or a header of that entry, does it ask again? Can a committed project settings file approve project MCP servers in advance, which would remove the prompt?

## Steps as run

1. A throwaway folder (not a repository) held a `.mcp.json` with one entry that points at the local server. `claude mcp list` ran in it.
2. The same folder gained a project settings file (`.claude/settings.json`) that sets `enableAllProjectMcpServers`. The folder is not a repository, so nothing was committed. `claude mcp list` ran again.
3. The approval was given by name in the user settings file of the isolated configuration, the way a user's own settings approve a server. `claude mcp list` ran again.
4. With that approval kept, the `url` of the entry was changed to another path of the local server, and then a header was added. `claude mcp list` ran after each change.
5. In a second never-trusted throwaway folder with a fresh configuration directory (no settings, so no approval of any kind existed) and no login, `claude -p` ran with a short prompt, and the local server was watched. The run was stopped after 45 seconds.

## Observed result

- Step 1: the entry showed as pending approval, and the client made no request to the server.
- Step 2: the same. A project settings file in a folder that was never trusted did not approve the entry. The vendor says the same of a committed file; a committed file in a repository was not run.
- Step 3: the client connected and the handshake completed.
- Step 4: with the same name, the client connected to the new address and then to the entry with the added header, with no new approval. In this path the approval is kept by name.
- Step 5: the client connected to the project entry and listed its tools with no prompt and no approval. The run had no login and did not finish, so it sent no model request that was observed.
- Not run: the approval dialog of an interactive session (it needs a signed-in client), whether that dialog keeps its choice by name, and `claude -p` with a sign-in.

## Verdict

Confirms the design where observed. A client that connects without asking gets no `env-ref` entry (ADR-004 decision 2), and the closed table of this release has none. What the README may claim: `claude mcp list` does not connect to an unapproved entry, `claude -p` loads project entries without a prompt, and in the path observed (an approval written into the user settings by name) the client does not ask again after a change of the address. Whether the dialog of an interactive session keeps its choice by name was not run, so no claim is made about it.

Plan amendment: none requested.

## If the result differs

A client that connects without asking gets no `env-ref` entry (ADR-004 decision 2). This one connects without asking in a `claude -p` run.

## Before you commit this record

- [x] The record holds no credential value, no account name, no raw client log, no address of a private server and no tenant host.
- [x] No token or sign-in was used. The throwaway folders and the local server are outside the repository and were removed or stopped.
