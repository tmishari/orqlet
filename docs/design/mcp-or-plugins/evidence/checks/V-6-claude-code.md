# V-6 for Claude Code: which surfaces load the project entry, and which files the client reads

Verdict: PARTLY RUN. The terminal surface was run through `claude mcp list` only. The other surfaces were not run.

- Check: V-6 of `docs/design/mcp-or-plugins/design/adr-004-verify-client-behaviour-with-test-accounts.md`, for Claude Code only (the halves for Codex and Cursor wait for the release that enables them)
- Unknowns it answers: U-23 to U-31
- Date: 2026-10-29
- Client name and version: Claude Code 2.1.303, on macOS
- Kind of test account: none. No sign-in to any real service. The client ran with an isolated home directory and no login, against a local server on the loopback interface that the tester controls. Each `.mcp.json` pointed at its own path of that server, so its log showed which file was read.
- Vendor statement beside the observations: none. The page read on 2026-10-29 does not say which folders are searched for `.mcp.json`, so the folder results below rest on the observation alone.

## Question

On each surface of Q-7 (terminal, IDE extension, desktop app, cloud agent or web session, review context), does the project entry from `.mcp.json` load, with or without a prompt? Which files does the client read: nested folders, parent folders and user files?

## Steps as run

All entries were approved by name in the user settings of the isolated configuration. In each case `claude mcp list` ran in the folder named.

1. A `.mcp.json` in the parent folder only, outside any repository; the client started in a child folder. The same with a file three levels up.
2. A `.mcp.json` in a child folder only; the client started in the parent folder.
3. A `.mcp.json` in the home directory only; the client started in an unrelated folder. Then the client started in a folder below the home directory.
4. A repository with a `.mcp.json` at its root; the client started in a subfolder. Then a file in the subfolder as well, with the same entry name, and then with different entry names.
5. A `.mcp.json` that is a symbolic link to a file outside the project, and a directory named `.mcp.json`.

## Observed result

- The client read `.mcp.json` in the start folder and in every parent folder, outside a repository and inside one, up to and including the home directory when it is a parent. It merged them: different names all loaded, and with the same name the file nearest the start folder won.
- It did not read a child folder, and it did not read a file in the home directory when the start folder was not below it.
- It followed a symbolic link. A directory named `.mcp.json` gave a message that the file failed to parse, and no entry.
- Not run: the IDE extension, the desktop app, the cloud agent or web session and the review context; the prompt on each surface; whether those surfaces read the same files. No throwaway repository on a host was created, so none had to be deleted.

## Verdict

Confirms the limit that ADR-002 decision 12 states ("MCP files in nested or parent folders"), for the terminal surface only. A `.mcp.json` outside the repository adds entries to every project below it, and `orqlet validate integrations` reads only the file at the project root. The README says so. Every other surface is a written gap, as the plan requires.

Plan amendment: none requested.

## If the result differs

Each surface that does not load project entries is a written gap in the README (ADR-004 decision 3).

## Before you commit this record

- [x] The record holds no credential value, no account name, no raw client log, no address of a private server and no tenant host.
- [x] No throwaway repository on a host was used. The local folders were removed with the isolated home directory.
