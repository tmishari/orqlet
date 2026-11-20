# Native hooks, plugins and developer workflow: research addendum

Retrieved: 2026-11-20T09:22:53.910390+00:00
Tool: web.run and local source reads
Processed: yes; summaries written by Codex
Data class: public
Version scope: inspected current documentation; installed native client versions were not qualified.

## Terms and scope

Skills supply reusable instructions, hooks run at lifecycle events, and plugins can distribute supported components. Their relationship does not make their formats or permissions interchangeable. This addendum covers documented capability, not executed client behaviour. Context7 was not used; the person approved official-documentation research instead (Q-15).

## Claude Code

URL: https://code.claude.com/docs/en/hooks.md

The reference documents SessionStart, prompt and tool events, context injection, event-specific decisions and plugin hooks. Startup context can be re-established at supported resume/compaction events. Startup timing differs from later events: MCP-tool handlers are unavailable at initial launch, so startup cannot assume an MCP client exists. Blocking/error semantics depend on the event and output contract. Do not reuse an arbitrary event's exit-code behavior elsewhere.

## Cursor

URL: https://cursor.com/docs/hooks.md

Hooks can be supplied by project/user hooks.json or plugins. The reference documents sessionStart, tool events and workspaceOpen. It uses native JSON/stdin/stdout contracts, including context fields. Permission-hook malformed responses and handler crashes/timeouts do not have identical effects; failClosed is an explicit capability for applicable hooks. Cloud lifecycle coverage differs from local sessions. A single template cannot stand in for per-event/per-surface verification.

## Codex

URL: https://learn.chatgpt.com/docs/hooks.md
URL: https://learn.chatgpt.com/docs/plugins.md

The hook reference documents user/trusted-project sources, lifecycle/tool events and context injection. Non-managed hook definitions require user trust, keyed to the definition's hash; changed definitions require renewed review. Matching hooks across sources can execute more than once. Background hooks cannot block the triggering operation. The plugins page explicitly excludes the IDE extension from plugin support. That exclusion does not establish that standalone hooks are unavailable in the extension: that surface needs its own qualification.

## VS Code / GitHub Copilot Agent

URL: https://code.visualstudio.com/docs/agent-customization/hooks.md
URL: https://code.visualstudio.com/docs/agent-customization/agent-plugins.md
URL: https://docs.github.com/en/copilot/reference/hooks-reference

The VS Code guide distinguishes the selected Copilot, Claude and Codex harnesses and directs each to its own hook reference. The Copilot setup supports user/workspace sources and plugin delivery. Applicable sources can all run, so adding a project or plugin copy does not remove a personal hook. The guide requires testing actual execution in the intended harness/environment. This is not evidence that Copilot hook configuration also configures the separate Codex VS Code extension.

## Existing Orqlet workflow

Local sources inspected:
- README.md, The workflow in the client and Day to day sections.
- src/orqlet/workflow/skills/orqlet-onboard/skill.md
- src/orqlet/workflow/skills/orqlet-research/skill.md
- src/orqlet/workflow/skills/orqlet-design/skill.md
- src/orqlet/workflow/skills/orqlet-plan/skill.md
- src/orqlet/workflow/skills/orqlet-implement/skill.md
- docs/design/mcp-or-plugins/design/adr-001-committed-files-stay-the-shared-channel.md

The current workflow uses separate phase invocations, input/standards checks, artifact validation, human acceptance/approval and role review records. The earlier MCP/plugin design has task-specific reasons for committed-file delivery and conditions for revisiting plugin outputs. Those are evidence for a new design, not proof that a plugin route is currently implemented or that existing approvals may be bypassed.

Ponytail 5.3.3's installed source was inspected without execution: its startup code and Claude/Codex, Cursor and Copilot hook manifests use different event/configuration forms and avoid duplicate guidance in some cases. This is an implementation example, not native-client qualification or an instruction to copy its runtime wholesale.

## Not run / unresolved qualification

- No hook handler, upstream installer, native session, plugin installation or user configuration change was executed.
- Exact target versions, platform-specific behavior, registration/trust flows, Codex extension hook coverage, payload schemas and latency remain to be qualified.
- The main AS-IS file and formal design require a scope refresh before claiming coverage of all these new requirements.
