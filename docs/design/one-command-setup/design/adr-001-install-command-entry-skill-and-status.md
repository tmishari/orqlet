# ADR-001: Terminal `install`, a person-started entry skill `orqlet`, and a read-only `status`

Status: proposed (the design pull request approves it). Task: `one-command-setup`.

## Context

The person asked for this quickstart: in the terminal, `uv tool install orqlet` (or `pipx install orqlet`), then `orqlet install`. Inside the assistant, the entry skill is invoked with the target directory (Q-10), and it is named `/orqlet .` (Q-11). Q-10 supersedes the earlier idea of a terminal `orqlet .` command (Q-5, Q-6).

The CLI has named Typer subcommands only, with no setup or install command (A-2). Package installation by uv or pipx runs no Orqlet code: uv documents no post-install hook for configuration (evidence `global-setup.md`, uv section).

Every packaged phase skill is person-started (A-19). The person keeps it that way (Q-34). `init` refuses a directory nested in another repository (A-28). The entry skill must not guess project state; it needs a deterministic answer from the CLI (baseline: do not guess).

## Decision

1. **`orqlet install`** is the one terminal setup command. It detects the clients and writes the user scope (ADR-002). It prepares no tool and uses no network (Q-60). `orqlet uninstall` reverses only what `install` recorded.
2. **The entry skill `orqlet`** is a packaged workflow skill like the phase skills. It is rendered person-started for every client (A-19), and it is invoked as `/orqlet <dir>` in Claude Code, Cursor and Copilot, and `$orqlet <dir>` in Codex (A-38, evidence `client-integration-contracts.md` 7.2). Its steps:
   1. Run `orqlet status --root <dir> --json`. If `orqlet` is missing, tell the person the terminal command.
   2. Act on the state:

      | State | Action |
      |---|---|
      | Global setup missing | Run `orqlet install --dry-run --json`, show the preview, and run `orqlet install --yes --json` after the person says yes |
      | Not a repository | Stop there |
      | Repository without `.orqlet/` | Run `orqlet init --root <top> --dry-run`, show it, and run it with `--yes` after the person says yes |
      | Initialized | Run `orqlet upgrade --root <top> --dry-run` the same way, then `--yes` after the person's yes, then report status |
      | Linked worktree (U-4) | Refuse with a message |

   3. End with the next person-started command. It never starts a phase skill.
3. **`orqlet status`** is a read-only command, and the only state source for the entry skill and the session-start hook (ADR-004). One use case answers both. Its fields and states are listed in `component.md` section 3. The `status` command uses `GitRunner` for the top level and for linked-worktree detection (`--git-dir` differs from `--git-common-dir`). The hook path starts no process (ADR-004 decision 5).

   Its output reaches the agent's context, so every field that comes from the repository follows the rules of ADR-004 decision 1a. A version must match `^\d+\.\d+\.\d+$`, or it is null. A path, `top_level` included, is printed only as it really is. A path that holds a control, bidirectional or format character, or that is longer than 200 characters, is never altered: it is null, with the closed reason `path-not-representable`. On a null `top_level`, the entry skill stops and tells the person to run the command in a terminal; it never passes a changed path to `--root`. `next` comes from the closed set. `status` reads the `.orqlet/` locks through the same bounded reader as the hooks: regular files only, never links, at most 1 MiB, and the strict YAML loader (ADR-004 decision 5).
4. There is no bootstrap script (Q-35). `install` prepares no missing uv or other tool; that moved to a separate task (Q-60).

## Consequences

- There are three new public commands (`install`, `uninstall`, `status`) and one internal command (`hook`). Each existing command keeps its behaviour.
- Setup costs two terminal commands and one skill invocation per repository. Daily work then needs no Orqlet command; the hooks carry the routine (ADR-004).
- Because the entry skill is person-started, the model never initializes a repository by itself. The cost is one explicit invocation.
- `status` becomes a stable output that the entry skill and the hook depend on. Changing its JSON fields is a compatibility change.

## Rejected alternatives

- **A terminal `orqlet .` with a positional-argument parser.** Q-10 superseded it, and it would add a second routing style to a CLI that only has named commands (A-2).
- **Configuration as a side effect of package installation.** uv and pipx run no package hook (evidence `global-setup.md`). A post-install script would also run unreviewed code at install time.
- **A shell bootstrap script (`curl … | sh`).** Q-35 rules it out. It also matches the warning list of the phase contract: it pipes into a shell and fetches from the network.
- **A model-startable entry skill.** The model could start `init` without the person asking. Q-34 keeps skill invocation person-started.
- **The entry skill working out the state from raw `git` and file checks.** That makes the agent guess, and different clients would interpret the same checks differently. A deterministic `status` keeps the logic in tested code.
