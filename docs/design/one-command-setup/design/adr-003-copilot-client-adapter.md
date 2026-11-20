# ADR-003: A fourth client adapter for GitHub Copilot in VS Code

Status: proposed. Task: `one-command-setup`. Depends on an amendment of ORQLET-ARCH-003 and of the import-linter independence contract (Q-33).

## Context

The closed client set is `claude-code`, `codex` and `cursor`. ORQLET-ARCH-003 and an import-linter independence contract name exactly those three adapters (A-24, `pyproject.toml:120-127`).

Q-21 adds GitHub Copilot Agent mode in VS Code, and the Codex VS Code extension, as supported surfaces (C-4). The person chose a fourth independent adapter, with ARCH-003 amended to name four (Q-33).

What Copilot documents:

- skills in `.github/skills` and `~/.copilot/skills`, with a name that must equal the folder name and the `disable-model-invocation` field (A-41);
- hooks in `~/.copilot/hooks` and `.github/hooks`, plus the repository `.claude/settings.json`, all run together (A-39, A-40);
- `sessionStart` with `additionalContext` only (A-40).

VS Code also hosts Claude and Codex harnesses, which follow their own clients' configuration (evidence 8.2).

The Codex VS Code extension reads `$HOME/.agents/skills` and shares `config.toml` with the CLI (A-38). It is already served by the `codex` adapter.

## Decision

1. **Client id `copilot`, as a rendering target only.** A new four-valued type, `RenderClientId` (`claude-code`, `codex`, `cursor`, `copilot`), is used by the profile's client list, the adapters, `--client`, and the user manifest's owner sets.

   The existing three-valued `ClientId` (`src/orqlet/application/contracts/common.py:27-28`) stays unchanged for model-policy v2, role-bindings, review-result and integrations. Those schemas and their JSON schema files do not change. Copilot gets no model setting, no MCP rendering and no reviewer binding in this change.
2. **A new adapter, `orqlet.adapters.clients.copilot`.** It implements the existing instruction-adapter port, imports none of the other three, and renders:
   - **Project:** skills under `.github/skills/<name>/SKILL.md`, person-started through `disable-model-invocation`. No project hook file (ADR-004).
   - **User:** skills under `~/.copilot/skills/` and the hook file `~/.copilot/hooks/orqlet.json`.
   - **Not rendered** until an official page names their location: agents and instruction files.
   **Proposed amendment text** (Q-33, constraint K-1):
   - ORQLET-ARCH-003 becomes: "The four client adapters (Claude Code, Codex, Cursor, Copilot) never import one another, and the workflow package under orqlet/workflow is read-only data used only by adapters and the interface." The second clause is unchanged.
   - The import-linter contract "Client adapters do not know about one another" (`pyproject.toml:121-127`) lists `orqlet.adapters.clients.claude_code`, `orqlet.adapters.clients.codex`, `orqlet.adapters.clients.copilot` and `orqlet.adapters.clients.cursor`. The workflow-package contract (`pyproject.toml:115-118`) is unchanged.
3. **The Codex VS Code extension** stays with the `codex` adapter. No second Codex adapter exists.
4. **Existing profiles** keep their client lists. `upgrade` renders Copilot files only for a profile that lists `copilot`. `init --client` defaults to every client, so a new project includes Copilot files.

## Consequences

- Copilot gets the same skills as the other clients, with no coupling between adapters. The independence contract keeps that checked.
- Copilot has fewer outputs than the other clients (no agents, no instruction file) until official locations are cited. `install` and `status` report the gap, so nobody assumes it.
- New projects get a `.github/skills` folder. A team that does not use Copilot removes `copilot` from its profile.
- Enterprise settings can turn off the Claude and Codex harnesses in VS Code (evidence 8.9). The `copilot` adapter does not depend on them.
- Two client types now exist. A later change that gives Copilot model settings, MCP entries or reviewer bindings widens `ClientId` and the four schemas then, with their own review.

## Rejected alternatives

- **No new adapter: serve Copilot through files the others already write.** Copilot reads the repository `.claude/settings.json` hooks (A-39), but not `~/.claude` or `.claude/skills`, so there would be no skills, which fails R-3. Writing `.github/skills` from the Claude adapter would make one adapter know two clients, which goes against the intent of ARCH-003.
- **Defer Copilot to a later task.** Q-21 and Q-33 make it part of this one.
- **Adding `copilot` to `ClientId` everywhere.** Four persisted schemas would admit a client that nothing renders for in those files (model policy, role bindings, review results, integrations). Each would need its own decision and schema review.
- **A shared "VS Code" adapter for Copilot and the Codex extension.** These are different products with different folders (evidence 10.1). Merging them would couple Codex output to Copilot.
