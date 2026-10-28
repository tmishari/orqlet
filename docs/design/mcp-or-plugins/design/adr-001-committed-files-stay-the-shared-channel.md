# ADR-001: Committed project files are the shared channel; no plugin output in this change

Status: proposed (a design pull request approves it). Task: `mcp-or-plugins`. Reads: AS-IS `docs/design/mcp-or-plugins/as-is.md`, ledger answers Q-2, Q-6, Q-7, Q-9, Q-10, Q-11, Q-12.

## Context

The request asks whether Orqlet's generated setup (skills, agents, rules, MCP entries) should reach every developer as native client plugins instead of committed files (Q-2), under one standard: each user uses only their own credential, never another user's, and the configuration is the same for everyone (Q-6). The person answered that no shared identity is allowed (Q-9), that a credential is the user's own OAuth sign-in or personal token (Q-10), that the shared files are changed by a pull request in this repository and reviewed by its code owners (Q-11), that every surface of Q-7 must be reached, and that the team has none of Claude Code managed settings, Codex workspace administration or Cursor Teams or Enterprise, or does not know (Q-7).

What the evidence says about each route:

| Question | Committed project files | Claude Code plugin | Codex plugin | Cursor plugin or Team MCP server |
|---|---|---|---|---|
| Is the shared definition a change in this repository's pull request? | Yes for `.mcp.json` and `.cursor/mcp.json` (A-55, A-58, A-108). Codex loads a project `.codex/config.toml` only in a trusted project (A-104); whether that file may hold `mcp_servers` is not stated (U-41) | Only through `extraKnownMarketplaces` and `enabledPlugins` in the repository's settings (A-84). They apply only in a trusted folder and are ignored without a message otherwise (A-85). A plugin from an external source is not installed by those settings alone (A-87) | A repo marketplace file and a project `.codex/config.toml` entry (A-103). Codex loads the installed copy from a per-machine cache (A-105) | A Team MCP server's configuration and a team plugin's variables are edited in a dashboard by team admins (A-114, A-115, A-119); that is not a change in this repository |
| Can each user supply their own credential? | Yes: a variable of the user's own or the client's sign-in (A-61, A-63, A-91, A-110, A-112) | `userConfig` with `sensitive` asks each user (A-77, A-78, A-79). A user report says a sensitive value is not persisted (A-82) and another that a placeholder is not substituted in an `oauth` block (A-83); both are unresolved (C-7, C-8, U-40) | "Authentication remains part of the MCP server integration" (A-101); how a user's credential reaches a plugin's server is not stated (U-43) | Values "are shared by the whole team" and set by admins (A-114, A-119); whether a developer can hold a different value is not stated (U-70) |
| Does it reach the surfaces of Q-7? | The vendor excerpts do not say which surfaces read a project file; that is check V-6 of ADR-004 | A cloud session loads no plugin from the repository's settings (A-89); other surfaces are not stated (U-27) | The IDE extension has no plugin support (A-107); other surfaces are not stated (U-83) | No unsupported surface is stated (U-30); whether Team MCP servers reach local sessions is not stated (U-23) |
| Can it carry always-on instructions? | Yes, and it is the only way for Claude Code and Codex (A-22) | No: a plugin has no `CLAUDE.md` (A-75) | Not stated (U-57) | Rules can be carried (A-22, A-117) |

The proposal already says the same in its own words: commit the thin always-on files, the skills, the roles and the MCP entries, and treat a native plugin as an additional output for organisations that want central updates (A-25, A-26, A-28).

## Decision

1. **The channel.** The shared MCP configuration reaches developers only as committed project files that Orqlet writes from one declaration, `.orqlet/integrations.yaml` (ADR-003). One declaration, one pull request, one review for every client.
2. **No plugin output now.** This change writes no plugin manifest, no marketplace file and no plugin variable, and it does not use Cursor Team MCP servers or team plugin variables for any credential. Reasons, from the table: the Cursor routes put a team-wide value under a dashboard that this repository's review does not cover (A-114, A-115); the Claude Code route has an unresolved defect report for the value that matters (A-82); the Codex route does not say how a user's credential arrives (U-43); and three of the routes need an install step or an administrator that the team has not confirmed (A-87, A-105, Q-7: the answer is "none of these, or not known").
3. **Skills, agents, rules, commands and instructions stay committed files.** A Claude Code plugin cannot carry always-on instructions (A-75), and for Codex it is not stated (U-57), so a plugin could at best duplicate part of the setup.
4. **When a plugin output may be added.** A later design may add one only if it shows all of these for the client concerned: (C1) the plugin carries no credential value; (C2) a credential reaches it only by the client's own sign-in or by a value that the client keeps on that user's machine, shown by a check record of ADR-004; (C3) the plugin and its marketplace entry live in this repository and change by its pull request (Q-11); (C4) it reaches the surfaces of Q-7, or each gap is written down.
5. **Miro gets no entry from Orqlet.** Miro documents a plugin for Claude Code and Cursor and a ChatGPT plugin for Codex, tells the user to use one method per client, and the plugin is user scope (A-134, A-138, A-140). Its connection is one team at a time per user (A-136) and a second method makes a second OAuth session (A-137). A project entry would break the vendor's rule and "the same configuration for everyone" cannot hold for Miro in a project file. This is a stated exception. A team may record the vendor's setup page as a link in its resources registry (`orqlet resources add`); that registry holds links, never an MCP entry or a credential, and this design does not decide it for the team.
6. **Surfaces.** Which surface of Q-7 loads a committed project entry is not stated by the vendor excerpts and is check V-6 of ADR-004. Until it is recorded, the README says which surfaces are verified and lists the others as not verified. A gap is a written gap, never silence.

## Consequences

- The route that the architecture document called later (A-26, A-28) stays later; nothing in this change blocks it, because the declaration lists servers by identity and not by delivery.
- Central updates without a pull request in each repository are not possible with committed files (A-23). A team that wants them has to pass the four conditions of decision 4.
- A user who also installs the vendor's own plugin for a server that Orqlet registered gets two connections for that server in the same client. For Miro the vendor documents the confusion (A-137); for Atlassian and GitHub the vendor text is silent (U-6). The README says to use one method per client.
- The decision rests on the facts of the table, and two of them are open: the defect report A-82 (U-40) and the way a Codex plugin receives a user's credential (U-43). A vendor change to either could reopen it, which is why decision 4 lists conditions and not a date.

## Rejected alternatives

- **Plugins only, no committed MCP file.** Fails Q-11 (the review is a dashboard or an install step), fails Q-9 on Cursor if values are team-wide (A-114), and leaves Claude Code and Codex without always-on instructions (A-22).
- **Plugins and committed files together.** Two definitions of one server drift apart, and Miro's own text calls the second session "authentication confusion" (A-137).
- **Claude Code `userConfig` for the token.** The vendor documents per-user storage (A-79) and a user report says it is not kept (A-82); the report has no version and is unresolved (U-40).
- **Cursor Team MCP server or team plugin variable.** One value for the whole team (A-114) conflicts with Q-9; a per-developer value is not documented (U-70).
- **Managed settings for plugins or MCP.** They need an administrator right that the team has not confirmed (Q-7, A-67, A-88); the person answered "none of these, or not known".
