# ADR-004: Advisory native hooks for session start and post-edit, registered once per client

Status: proposed. Task: `one-command-setup`.

## Context

The person wants routine startup guidance and lightweight tool-event checks to run through native hooks, without repeated skill commands (Q-14, Q-16).

Q-26 limits what a hook may do:

- only cheap, narrowly scoped, deterministic work;
- no test suite, graph rebuild, package download, paid model call, session or background agent;
- no daemon, watcher or generic hook engine;
- no claim of enforcement that a client contract does not support.

Q-22 forbids a hook from silently bypassing the phase contracts. Q-29 asks for quiet hooks.

What the clients document (A-34 to A-40; inference I-5):

| Topic | What the evidence says |
|---|---|
| Session-start hooks | They only add context and cannot block |
| Pre-tool failure semantics | They differ per client. Codex has no fail-closed option. Copilot timeouts always fail open |
| Double runs (I-2) | Cursor runs Claude user-settings hooks through a third-party import that is on by default. Codex can run a command registered twice, twice. Copilot runs the repository `.claude/settings.json` hooks |
| Context caps | 10,000 characters in Claude Code; 2,500 tokens by default in Codex |
| Codex trust | Codex keys hook trust to a hash, reviewed through `/hooks` in the CLI. The IDE extension is undocumented (U-1) |
| Cursor payload | It carries `cursor_version` (evidence 2.9) |
| Post-tool context return | Cited for Copilot (`additionalContext` on `postToolUse`, evidence 9.6) and Claude Code (hook output fields, evidence 1.4). Not cited for Cursor or Codex |

Hooks run in every repository the client opens, including untrusted clones, with no person action. Repository content is untrusted input (ORQLET-SEC-002).

## Decision

1. **Two events only.**
   - **Session start.** It runs `orqlet hook session-start --client <id>` and returns the status summary (ADR-001), at most 1,200 characters. Under `copilot` it also returns the foundation text when the workspace lacks the Orqlet baseline block (ADR-005).
   - **Post-edit.** On the client's post-tool event for file-edit tools, it runs `orqlet hook post-edit --client <id>`. When the edited path is an Orqlet-owned file in the project lock, it returns one advisory line: the file is generated, so change its source and run `orqlet upgrade` (baseline, "Generated files"). A client with no cited context return on its post-tool event (today Cursor and Codex) gets no post-edit registration until the plan cites one. `install` reports the omission.

   **1a. Context comes only from fixed templates** in the workflow package. The only variable fields are:

   | Field | Rule |
   |---|---|
   | Workflow versions | must match `^\d+\.\d+\.\d+$`, or the field is left out |
   | Next command | from a closed set of person-started commands |
   | Post-edit path | must appear in the lock and parse as a `CanonicalPath`; a path with a control, bidirectional or format character, or over 200 characters, leaves the line out and is never altered (the rule of `status`, ADR-001 decision 3) |
   | Foundation text (Copilot) | packaged in Orqlet, never read from the repository |

   No other text from the repository, the lock or the payload is copied into context.
2. **Advisory only.** No `PreToolUse` or `preToolUse` hook, and no blocking, `failClosed` or `onFailure: block` option. The hook always exits 0, and on its own error it returns no context. No hook records or implies an approval (I-5).
3. **Registered once per client, in the user scope only** (ADR-002):

   | Client | Registration file |
   |---|---|
   | Claude Code | `~/.claude/settings.json` |
   | Cursor | `~/.cursor/hooks.json` |
   | Codex | `$CODEX_HOME/hooks.json` |
   | Copilot | `~/.copilot/hooks/orqlet.json` |

   No project hook file is written.
4. **Duplicate-run filter.** The `claude-code` registration returns nothing when the payload carries `cursor_version`, because Cursor answers through its own registration.
5. **Finding the project, with no process.**
   - The starting directory is the payload's working-directory field: `cwd` for Claude Code, Codex and Copilot, and the first of `workspace_roots` for Cursor. Each field name is cited per client in the plan (K-12). A missing or non-absolute value gives no context.
   - The hook walks up from there, at most 64 levels, looking for `.orqlet/`. The directory that holds it is the project root. The walk reads through a FileSystem port rooted at the injected `UserHome` (ADR-002 decision 1a), so it never reads above the home directory. A starting directory outside home, such as `/tmp`, a container workspace or another Windows drive, gives no status, and no repository file is read there. Under `copilot` the packaged foundation text is then always returned, because that text does not come from the repository.
   - The hook reads `.orqlet/workflow.lock` (session start) and `.orqlet/generated.lock.yaml` (post-edit) through that port with the strict YAML loader. Each is one regular file, never a link, capped at 1 MiB. A lock that is larger, or that does not parse, gives no context.
   - The payload's edited-file path is used only when it resolves inside that root and is not a link.
   - The Copilot `AGENTS.md` read uses that root, or the starting directory itself when no root is found, and only inside home. It reads one regular file, never a link, capped at 256 KiB.
6. **Bounds.**

   | Bound | Value |
   |---|---|
   | Payload size | at most 1 MiB, parsed with a strict JSON parser; unknown fields are ignored |
   | Repository files | at most 1 MiB for each lock file and 256 KiB for `AGENTS.md`; the size is checked before reading |
   | Processes | none |
   | Writes | none; the data directory is not created (K-11) |
   | Network | none |
   | Time | an internal deadline of 2 seconds; the registered timeout is 5 seconds |

7. **Command form.** Each registration is the fixed command `orqlet hook <event> --client <id>`, with no value taken from a payload or a project. It calls the bare `orqlet` executable, never an absolute path (ORQLET-DET-001). Where a client documents an exec form, it is used (Claude Code, evidence 1.9). Each client's command schema is cited in the plan (K-12), together with how the client launches and resolves the command on each operating system. A client that resolves a bare command name through the working directory before `PATH`, as a cmd.exe-style lookup does, gets no registration on that system. `install` reports a `host step` for it, because an untrusted clone could otherwise put its own `orqlet` program first. On every system, `install` and `status` also inspect `PATH` for empty, `.` or relative elements. When such an element comes before the folder of the resolved `orqlet`, no hook is registered, and a `host step` names the risk. `install` and `status` report which `orqlet` the current `PATH` resolves to, and flag it when it is not the running executable.
8. **Trust.** Host trust steps (Codex `/hooks`) are reported by `install` as `host step` and are never bypassed. In the Codex IDE extension the hook is reported as not verified until qualified (U-1, Q-20).
9. **Disable.** `orqlet uninstall --client <id>` removes Orqlet's entries only (ADR-002 decision 5). Each client's own global switch stays the person's.

## Consequences

- Daily work gets a short status at session start, and in Claude Code and Copilot a warning on hand edits of generated files, with no command to remember. Nothing is enforced, so the warnings are only as good as the model's attention.
- A hostile repository can at most change which closed-set command appears, and which lock path appears. The lock path is one the agent just edited, at most 200 characters, chosen by the repository, and the template shows it as a code span after a fixed label. No other repository text reaches a session through the hook.
- Hook cost is bounded and starts no process. A slow file system loses the context instead of slowing the session.
- Linked-worktree detection is not done in hooks, because it needs Git. Only `status` does it.
- Copilot has no compaction source (I-4), so its status is not refreshed after compaction.
- The duplicate-run filter depends on Cursor's payload field. A golden payload test pins it, and qualification confirms it.
- Codex users must trust the hook once per change of its definition (evidence 5.5).
- `install` and `status` inspect the `PATH` of the terminal they run in. A client started from a desktop launcher may launch the hook with another `PATH`, which they cannot see. The person accepted this leftover risk (Q-42). K-12 asks for each client's launch environment where its documentation states it, and `install` reports a `host step` where that environment may differ.

## Rejected alternatives

- **Blocking pre-tool hooks for protected files.** Codex and Copilot cannot guarantee a block (I-5), so claiming enforcement would break Q-26.
- **Project-scope hook files committed to each repository.** Copilot would run them alongside the user registration (A-39), and every teammate would need Orqlet on `PATH`.
- **Finding the root with `git rev-parse` in the hook.** It starts a process at every event, and runs Git against a directory a payload chose, with that repository's configuration. An upward `.orqlet/` search needs neither.
- **Running `gate status` or validators at every event.** They read history and many files (A-32), which is too costly under Q-26.
- **Copying project text into context (for example, task titles from `docs/design`).** It opens an instruction-injection path from any cloned repository (ORQLET-SEC-002).
- **One registration in `~/.claude/settings.json` serving Cursor through the third-party import.** That setting can be off, and Enterprise can control it.
- **A Cursor plugin carrying the hooks.** Local plugins are off by default on Enterprise (A-36), and ADR-001 of `mcp-or-plugins` permits plugin output only under conditions C1 to C4 (A-23).
