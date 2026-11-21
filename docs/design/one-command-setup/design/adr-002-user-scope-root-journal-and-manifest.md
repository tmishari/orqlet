# ADR-002: User-scope write root, journal and manifest

Status: proposed. Task: `one-command-setup`. Depends on an amendment of ORQLET-SAFE-001 (Q-32). The "Proposed amendment text" block at the end of the Decision section is the wording for that change.

## Context

Global configuration must hold Orqlet's skills, rules, agents and hooks in each client's user folders (Q-7, Q-38). Today:

- `LocalFileSystem` is confined to one resolved root and refuses links below it (A-27). It does not check the root itself (`src/orqlet/adapters/fs/local_fs.py:74-77`).
- Journals and backups live in the data directory, keyed by project id (A-27, `src/orqlet/interface/cli/wiring.py:145-149`).
- `apply_plan` takes one `FileSystem`. It locks, verifies the preview, backs up, journals and writes atomically, with the manifest last, and keys entries by relative path (A-31, `src/orqlet/application/usecases/apply_plan.py:39-79`).
- `RenderRequest` is built from a project profile: scoped rules, conventions, integrations, and model settings per client (`src/orqlet/application/ports/instruction_adapter.py:94-139`).
- ORQLET-SAFE-001 (MUST) keeps every write inside the project root (`.prompts/rules.yaml:66-72`).

The person chose to amend SAFE-001 in a separate reviewed change. The amendment allows a second, allow-listed root of fixed user-home client folders, with its own journal, backup and manifest (Q-32).

The clients' user files are shared with the person and with other tools:

- `settings.json` holds unrelated settings (A-34).
- Hook files from every source all run (A-35, A-37).
- Claude Code has no per-hook disable switch (evidence `client-integration-contracts.md` 1.10).
- `~/.agents/skills` is read by both Cursor and Codex (evidence `global-setup.md`).

## Decision

1. **One composite user-scope file system.** It maps each canonical-path prefix to one root, and inside each root only the listed sub-paths are writable:

   | Prefix | Root | Writable sub-paths |
   |---|---|---|
   | `claude/` | `~/.claude` | `skills/<owned>/**`, `agents/<owned>.md`, `rules/orqlet-foundation.md`, `settings.json` (owned entries only) |
   | `cursor/` | `~/.cursor` | `agents/<owned>.md`, `hooks.json` (owned entries only) |
   | `codex/` | `$CODEX_HOME`, default `~/.codex` | `agents/<owned>.*`, `AGENTS.md` (managed block only), `hooks.json` (owned entries only) |
   | `agents/` | `~/.agents` | `skills/<owned>/**` |
   | `copilot/` | `$COPILOT_HOME`, default `~/.copilot` | `skills/<owned>/**`, `hooks/orqlet.json` |
   | `data/` | `<data directory>/user` | `manifest.json`, `cursor-user-rules.md` |

   `<owned>` is `orqlet`, `orqlet-*` or `ponytail*`. Any other path, and every link, is refused. `apply_plan` receives this one file system, so journal entries and backups are keyed by the prefixed path and never collide across roots.

   **Scope of the journalled-plan rule.** It covers every file Orqlet writes into an allow-listed root. The writes that are exempt are listed in the "Proposed amendment text" block below.

   **Folder boundaries.** The composite file system's `remove_empty_dir` is a no-op for a root, and for any folder at or above a writable sub-path's first segment, such as `~/.claude/skills` or `~/.agents/skills`. The empty-folder walk of `apply_plan` (`apply_plan.py:82-93`) therefore stops there: it removes an owned skill folder and never a root or a folder that the person or a client owns. `apply_plan` keeps its current journal kinds (create, update, delete).

   **1a. Root validation**, before any read for a plan. It applies to every root in the table, including `data/`:
   - The home directory comes from one injected `UserHome` value: `Path.home()`, which is `USERPROFILE` on Windows.
   - For an existing root, the real path is checked. For a missing root, the real path of its nearest existing ancestor is checked.
   - Each client root's real path must lie under the real home directory. A `CODEX_HOME` or `COPILOT_HOME` value outside home is refused with exit 3.
   - The data directory may lie outside home when `ORQLET_DATA_DIR` says so. It and `user/` must still pass the remaining checks. On Windows, where Orqlet cannot check the access control list, a data directory outside home is allowed, and the preview warns that its access is not checked (Q-41). The warning also says that another account able to write there could plant journals and backups that `rollback --user` and adoption would trust. The `uninstall` preview carries the same warning, and `rollback --user` repeats it before it applies.
   - **Validation in code.** A `UserRootInspector` port returns, for each prefix, a `RootState`: resolved real path, whether it exists, refusal reason, whether it needs tightening, and any platform warning. The install, uninstall and rollback use cases plan from these states, reading through a read-only composite file system that the port also supplies. The port's second operation, `prepare(states) -> FileSystem`, is called by the use case only after consent: it creates and tightens folders, validates again, opens each `LocalFileSystem`, and returns the writable composite file system that `apply_plan` receives. It refuses with exit 3 when an opened root's resolved path differs from the validated and pinned one. The user-scope adapter implements the port.
   - The root itself must not be a link and must be owned by the current user (on POSIX).
   - A root must not lie inside a Git work tree. This is decided with no process, by looking for a `.git` entry in the root and its ancestors through a read-only ancestor port, the same kind as `AncestorFinder` (`src/orqlet/application/ports/ancestors.py:8-11`).
   - **Nothing is created or changed before consent.** While planning (under `--dry-run`, during the preview, or when the person declines), the composite file system reads a missing root, or a missing `user/` folder, as empty, and the preview reports it as `will create`. Only after the person's yes or `--yes`, and before the first journalled write, does the user-scope adapter create each missing root and its missing parents under home (or under the data directory) with mode 0700, validate the root again, and only then open its `LocalFileSystem`. The creation is outside the journal and is deliberately left in place by rollback and uninstall: an empty client folder changes nothing for the client.
   - `<data directory>/user`, `user/journal` and `user/backups` are Orqlet's own folders. One that exists with group or world access is reported in the preview as `will tighten`, and tightened to 0700 only after consent. One that is owned by another user is refused with exit 3.
   - **Roots are pinned.** The journal of each change and `user/manifest.json` record the resolved real root of each prefix. `install`, `uninstall`, `rollback --user` and adoption refuse with exit 3, naming the variable, when a prefix that holds recorded entries now resolves to a different real root, for example after `CODEX_HOME` changed. Otherwise the old root's entries, a registered hook among them, would become untracked. To move, the person runs `uninstall --client C` with the old value, then `install` with the new one.
   - The preview names each root's resolved path.
2. **Ownership.** `user/manifest.json` records for each owned file or entry:
   - its prefixed path or JSON entry key;
   - its SHA-256;
   - the workflow version;
   - the set of owning clients.

   It also records the id of the change that wrote it, which orders adoption (decision 4).

   **Downgrade.** When `user/manifest.json` holds a workflow version above the running Orqlet's, `install` refuses with exit 3 unless `--allow-weaker` is given, as `upgrade` refuses a downgrade (`src/orqlet/application/usecases/upgrade.py:94`, `:353-380`). Otherwise an older CLI would silently replace newer global phase skills, which can shadow project copies (Q-38). `status` reports this state as `global: newer` with `next: refuse-newer-global`.

   `~/.agents/skills` gets one shared render, with the `agents/openai.yaml` sidecar, for both Cursor and Codex. Its files, the sidecar included, carry the owner set of the selected clients among {cursor, codex}. In user scope, both adapters render this folder through the shared skills helper in `adapters/render` with the sidecar on, so the two renders are byte-identical. Project output stays as it is (BC-18). A file Orqlet owns is replaced only while its hash matches. An unowned file with an owned name is a conflict. `AGENTS.md` takes a managed block (the marker form of A-25).
3. **Shared JSON files** (`settings.json`, `hooks.json`). Each client adapter renders its hook entries under `RenderScope.user` as entry objects, never as whole files. The install use case (application layer) merges them into the current file through a pure helper, with the standard-library `json` module only:
   - Each is read with a strict JSON parser: an object at the top level, no duplicate keys (rejected through `object_pairs_hook`), and no `NaN` or `Infinity` (rejected through `parse_constant`). A file that does not parse this way is a conflict and is never rewritten. Hook payloads use the same parser (ADR-004).
   - An entry is replaced or removed only when the manifest holds a record for it with a matching canonical-JSON hash.
   - An entry equal to Orqlet's command but without a manifest record, or with a different hash, is a conflict.
   - Every other key, and its order, is kept.
4. **Journal and manifest order.**
   - `user/journal/<change-id>.json` and `user/backups/<change-id>/<prefixed path>` live under the data directory, in a `user` namespace that never collides with `projects/<id>` (A-27).
   - The file lock, verify-then-write and backup order of `apply_plan` are reused (A-31). `user/manifest.json` is written last, through the `data/` root.
   - The apply lock is `<data directory>/user/apply.lock`, the user-scope counterpart of `projects/<id>/apply.lock` (`src/orqlet/interface/cli/wiring.py:145-149`).
   - An apply interrupted after some writes leaves the manifest unwritten. The next `install` plans again from the files as they are. Planning reads unfinished journals read-only. Only the consented apply marks them superseded, as `apply_plan` does today (`apply_plan.py:55-56`), so `--dry-run` and a declined preview change nothing.
     - **Journal content.** Each user-scope journal entry records, besides path, kind and hashes, the entry's owner set and, for a shared JSON entry, its key and the canonical-JSON hash written.
     - **Pending changes.** The pending changes are every journal kept under `user/journal` whose `created_at` (`src/orqlet/application/ports/change_journal.py:35`) is later than that of the change recorded in `user/manifest.json` (all of them when there is no manifest). This covers two or more interrupted runs in a row: a later run that found a file already right planned no write for it, so only an earlier journal records it.
     - **Adoption.** The pending changes are adopted oldest first, each entry taking the owner set its journal records. `apply_plan` writes a file before it marks the journal entry done (`apply_plan.py:75-77`), so the done flag is not relied on. Every recorded entry, done or not, is adopted as owned when the file's current SHA-256 equals that entry's after-hash. A delete entry whose file is already absent counts as applied. A shared JSON entry is adopted when its current canonical-JSON hash equals the hash the journal recorded for it, even if another key of the file changed since, and even when the workflow version changed before the recovery. The re-plan therefore meets no conflict on its own earlier writes, converges, and writes the manifest last.
     - `uninstall` applies the same adoption to the pending changes before it plans, and then removes the adopted entries once no owner remains. Its preview names the pending ids too.
     - **Rollback window.** The preview names each pending change id and warns that applying prunes it (Q-40). The person who wants one undone declines and runs `orqlet rollback --user <id>` first. After the recovering install applies, the pending changes can no longer be rolled back.
     - This differs from `upgrade`, which refuses with ORQ-E131 and offers `--resume`. `install` has no `--resume`, because a re-plan reaches the same end state.
   - Backups and journals are written with mode 0600 by the user-namespace journal and backup store adapters, which create each new file with that mode (today's `LocalFileSystem.write_atomic` creates 0644, `src/orqlet/adapters/fs/local_fs.py:36`). `<data directory>/user` is created 0700.
   - **Retention (Q-40).** Backups and journals of the last 3 user-scope changes are kept. Only a successful `install` or `uninstall`, after it writes the manifest, prunes older and superseded ones, so a pending change is never pruned before it is adopted. The preview names what it prunes.
   - Previews, conflicts and `--json` output name files and keys but never print a shared file's content.
5. **Undo.**
   - `orqlet uninstall --client C` removes `C` from each entry's owner set, and deletes an entry only when the set becomes empty and its hash still matches.
   - `orqlet uninstall` with no `--client` acts on every owner recorded in `user/manifest.json`, whether or not the client is still detected. With no recorded owner it reports `nothing to remove` and exits 0. The exit 4 for "no supported assistant detected" does not apply to it.
   - `orqlet rollback --user <change-id>` reads the change from the `user` namespace instead of a project. It works from any directory, inside a repository or not. `--user` excludes `--root` and `--project-id`, and using them together is a usage error (exit 2). It refuses a file touched since the change, as today. It writes `user/manifest.json` last, in place of the project lock. For a change that wrote no manifest (an interrupted one), it leaves `user/manifest.json` as it is, because that manifest already describes the restored state. Its weaker-workflow check compares the change with the workflow version in `user/manifest.json`, and `--allow-weaker` keeps its meaning. `--dry-run`, `--yes`, `--json` and the exit statuses are those of today's `rollback`.
6. **Separate transactions.** The user scope and the project scope never share one. A project `init` never writes the user scope, and `install` never writes a project.
7. **User-scope render request.** Adapters receive a `RenderScope` of `project` or `user`. A user request carries only:
   - the packaged skills, roles and entry skill;
   - the bundled skills;
   - the foundation text, as the baseline body.

   It carries no model settings, conventions, integrations, scoped rules or resources, so no model name reaches a user-scope file (ORQLET-MODEL-001).
8. **No auto-creation on read.** `status` and the hooks resolve the data directory without creating it (constraint K-11).

**Proposed amendment text** (Q-32, constraint K-1). ORQLET-SAFE-001 keeps its level (MUST), its scope paths (`src/orqlet/application/**`, `src/orqlet/adapters/**`) and its enforcement (review). Its text becomes:

> Every write goes through a journalled change plan: a backup is taken first, and the manifest is written last so a re-run converges. Project writes stay inside the project root. User-scope writes stay inside the allow-listed client folders and the data directory's `user` folder, each limited to its listed sub-paths, after the root checks: under the real home (the data directory may be elsewhere), not a link, owned by the user on POSIX, and not inside a Git work tree. On Windows, ownership is not checked, and a data directory outside home is allowed only with a warning that its access is not checked. The allow-listed roots and sub-paths are those that the user-scope file-system adapter declares; adding a root or widening a sub-path needs a reviewed design. Nothing is created or changed in the user scope before the person consents. Exempt from both the journal and the sub-path limit are only: creating, after consent and with mode 0700, a missing allow-listed root and its missing parents under home, and the data directory, its missing parents and its `user` folder; tightening Orqlet's own `user`, `journal` and `backups` folders to 0700 after consent; the apply lock, journal and backups under the `user` folder, and their pruning.

The table of decision 1, its folder boundaries and decision 1a are the design that meets this text. They are not part of the rule.

## Consequences

- Orqlet can configure every client with no manual copying. The price is a reviewed widening of a MUST rule, with the root rule of decision 1a as its control. Until K-1 holds, none of this ships.
- A `CODEX_HOME` or `COPILOT_HOME` outside the home directory is not supported. A person who uses one gets a refusal naming the variable.
- A home directory that is itself a Git work tree, or client folders that are links into a dotfiles repository, make every affected root fail validation (exit 3). The refusal names the root and the reason. Such a person can still use the project scope (`orqlet init`). A bare-repository dotfiles setup, where the Git directory is elsewhere, is not detected as a work tree and is not refused. The person accepted this, and the README states it (Q-44).
- Roots that Orqlet creates stay behind after uninstall, empty.
- The Cursor user render emits the Codex sidecar `agents/openai.yaml`. This is a deliberate exception: `~/.agents/skills` is one folder read by both clients, and Q-34 requires workflow skills there to stay person-started for Codex. The sidecar belongs to that shared folder, not to Cursor. The ADR-003 objection, one adapter writing a second client's own location, does not apply. Both adapters call the shared helper, and neither imports the other.
- Backups may contain credentials from shared client files. Keeping only 3 changes limits how long such copies exist, and rollback can go back at most 3 changes (Q-40). An interrupted change can be rolled back only before the next `install` applies, and the preview says so. On Windows, a data directory outside home has unchecked access, and the preview says so (Q-41).
- Rewriting a shared JSON file reformats its whitespace. Keys and values are kept, but byte formatting is not. A 0600 backup of the original is taken first.
- A hand edit to an owned entry stops Orqlet from touching it. This is the same trade-off as project ownership.
- The user scope has no Git history. The journal and backups are the only record, so `ORQLET_DATA_DIR` matters for recovery.
- User-scope agents carry no model setting. They follow each client's default model, while project agents follow the project's model policy. A shadowing global copy (Q-38) therefore also drops the project's model choice. `status` shows the shadowing.

## Rejected alternatives

- **The clients' own install commands, with printed steps elsewhere.** Only Claude Code documents a shell install (evidence 11.3). Cursor and Copilot plugin installs prompt in the editor (evidence 4.2, 10.7). The result would differ per client, and Q-7 asks for skills, rules and agents everywhere.
- **One unrestricted home-directory file system.** It would let a bug or a hostile path write anywhere under the home directory.
- **One change per root, under a shared group id.** It needs a new grouping concept in the journal and in rollback, and an interruption between roots leaves a half-applied group with no single manifest. One composite file system reuses `apply_plan` with its journal kinds unchanged. The root boundaries live in the composite file system.
- **Reusing the project manifest and journal with a pseudo project id.** The home directory is not a repository, and `gate status`, `doctor` and the lock assume Git and `.orqlet/` (A-32).
- **Applying the project's model policy to user-scope agents.** The user scope serves every project on the machine, so no single project's policy applies.
- **Replacing a shared JSON file wholesale.** It loses the person's settings and other tools' hooks.
