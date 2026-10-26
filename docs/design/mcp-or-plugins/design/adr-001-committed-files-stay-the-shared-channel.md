# ADR-001: Committed project files stay the shared channel for MCP entries; no plugin output in this change

Status: proposed. It becomes accepted when the design pull request is merged by an authorised person.

## Context

- The person's standard (ledger Q-6): each user uses only their own credential for each integration, never another user's, and the configuration is the same for everyone. Answers recorded on 2026-10-26: the setup must reach terminal, IDE, desktop apps, cloud agents and code-review contexts (Q-7); no plan or administrator route is known for Claude Code managed settings, Codex workspace administration or Cursor Teams or Enterprise (Q-7); no shared identity is allowed (Q-9); a pull request in this repository, reviewed by its code owners, is the review path (Q-11). Q-2 named the whole generated setup (skills, agents, rules and MCP entries) as the thing that might be packaged as plugins.
- **Committed files.** Claude Code and Cursor have a project MCP file that is shared through version control, `.mcp.json` and `.cursor/mcp.json` (AS-IS A-55, A-58, A-108). Codex loads a project `.codex/config.toml` only in trusted projects (A-104); whether it can hold `mcp_servers` entries and is shared through version control is not stated by the vendor text (unknown U-41), and the architecture document assumes it does (A-18, A-30). V-4 records it, and no Codex entry is generated before that (ADR-002 decision 2). A shared file can refer to a credential without holding it: `${VAR}` in Claude Code, `${env:NAME}` in Cursor, `bearer_token_env_var` in Codex (A-61, A-62, A-91, A-110); a remote server can instead use the client's OAuth sign-in (A-63, A-90, A-112). Claude Code stores sign-ins per endpoint (A-69).
- **Plugin reach.** A Claude Code cloud session does not load plugins (A-89). Codex plugins are not available in the IDE extension (A-107), and a Codex repository marketplace is enabled through a project `config.toml` that is read only in trusted projects (A-103, A-104). Cursor team marketplaces exist on Teams and Enterprise plans only (evidence `cursor-plugins.md:16-21`), and the team has named no such plan (Q-7). A Claude Code plugin whose entry points outside the marketplace needs a per-contributor install (A-87), and repository marketplace entries apply only in a trusted folder (A-85).
- **Plugin credential carriers.** In Cursor, plugin variables and Team MCP server configuration are set by team admins and shared by the whole team (A-114, A-115, A-119); whether one developer can hold a different value is not stated. In Claude Code, `userConfig` values are asked of each user and sensitive ones go to the user's secure store (A-77, A-78, A-79), but two user reports describe a lost value and an unsubstituted placeholder (A-82, A-83). For Codex it is not stated whether a plugin's MCP credential is per user or per workspace (unknowns under Q-8). The three plugin routes therefore have no common per-user credential mechanism.
- **Instructions.** A Claude Code plugin carries instructions only as skills and does not load a root `CLAUDE.md` (A-75). The architecture document says that plugins carry no `CLAUDE.md` or `AGENTS.md` and that Cursor plugins can carry rules (A-22); whether a Codex plugin can hold an instructions file is not stated by the vendor text (unknown U-57). Committed files stay the channel for always-on instructions in any case.
- **The design's standing decision.** Committed generated files first; native plugins as a later extra output (A-25, A-26, A-28).

## Decision

1. The shared MCP configuration is delivered only as the three committed project files, written from one declaration, `.orqlet/integrations.yaml` (ADR-003). One declaration, one pull request, one review for every client.
2. This change produces **no plugin manifest, no marketplace file and no plugin variable**, and does not use Cursor Team MCP servers or team plugin variables for any credential.
3. Skills, agents, rules, commands and instructions stay committed files as well. Plugins are not used for them in this change: a Claude Code plugin cannot carry always-on instructions (A-75) and the position for Codex is not stated (U-57), so a plugin could at best duplicate part of the setup.
4. A later plugin output stays allowed (decision D-27) only when it meets all of these conditions, which a later design must show: (C1) it carries no credential value; (C2) a credential reaches it only by the client's own sign-in or by a value that the client keeps on that user's machine, shown for that client by a check of ADR-004; (C3) it lives in this repository and is reviewed through its pull request (Q-11); (C4) it reaches the surfaces that Q-7 lists, or the gaps are written down.
5. Miro gets no entry from Orqlet in any client. Miro documents a plugin for Claude Code and Cursor and a ChatGPT plugin for Codex, says to use one method per client, and the plugin is user scope (A-134, A-138, A-140). This is a stated exception to "the same configuration for everyone" and resolves contradiction C-11 against the earlier plan of a manual Miro entry.

## Consequences

- The committed route is kept as the default. It is **not shown to be better in every respect**: its reach on cloud agents, review contexts and the Codex project file is the design's claim and is checked in V-7 and V-4 (ADR-004), and any surface that does not load project entries becomes a written gap.
- The plugin gaps named above (a Claude Code cloud session, the Codex IDE extension, Cursor without a team plan) do not apply to project files. That is a statement about the plugin route, not about what each surface does with a project file.
- Each developer still signs in or sets their own variable. Nothing central can do that for them, which is what Q-6 asks for. An unattended surface uses the account of the one user who started or owns it (the person's answer to Q-12); whether the clients can do that on each surface is checked in V-12, and where they cannot, Q-6 and Q-9 are not met there, for OAuth sign-ins as much as for variables.
- There is no central update without a pull request in each repository (A-23). That is accepted.
- One mode per server for the whole project (OAuth or an own variable) is a project decision made in the declaration and reviewed in the pull request; the first release generates Atlassian OAuth entries only (ADR-002). A user cannot choose a different mode locally without a personal entry, which Orqlet cannot prevent.
- Miro is outside the shared configuration.
- No new dependency.

## Rejected alternatives

- **Native plugins instead of committed files.** They do not reach a Claude Code cloud session or the Codex IDE extension, depend on plans the team has not named (Cursor team marketplaces), and cannot carry always-on instructions in Claude Code (A-75; Codex is not stated, U-57).
- **Plugins in addition to the files, now.** Two channels for one entry would need two reviews and could diverge, and the answer to Q-11 names one review path. Doubling the output also doubles the credential rules to test.
- **Cursor team plugin variables or Team MCP credentials.** One value set by an administrator and shared by the whole team is a shared identity (A-114, A-115), which Q-9 refuses.
- **A plugin for one client only (Claude Code's `userConfig`).** It would give one client a different route and a different review path, and its sensitive-value behaviour has two open user reports (A-82, A-83).
- **A separate plugin repository.** Q-11 chose this repository's pull request.
