# Client hook, skill and plugin contracts: excerpts

Retrieved: 2026-11-20T11:50:00+02:00
Tool: Cursor WebFetch (pages 1, 2, 3, 6, 9) and curl of the sites' Markdown twins and llms.txt (pages 4, 5, 7, 8, 10, 11); Context7 query of /websites/code_claude as a cross-check of page 1 only
Processed: no for curl-retrieved Markdown twins; unknown for WebFetch, which converts pages to Markdown; Context7 returns processed snippets
Data class: public
Version scope: current public pages on the retrieval date. No page names a client release that these contracts apply to, except where an excerpt names one. No hook, skill or plugin was executed in a native client.

Excerpts are verbatim as the tool returned them, shortened with "..." only.

## 1. Claude Code hooks reference

URL: https://code.claude.com/docs/en/hooks.md

1.1 Locations - "`~/.claude/settings.json` | All your projects ... `.claude/settings.json` | Single project ... Plugin `hooks/hooks.json` | When plugin is enabled ... Skill frontmatter | The rest of the session once the skill is invoked"
1.2 Merging - "Hook entries merge across settings levels rather than replacing each other: user, project, and local settings add their own hooks without removing managed ones"
1.3 SessionStart sources - "`SessionStart` | how the session started | `startup`, `resume`, `clear`, `compact`, `fork`"
1.4 Context cap - "A hook's `additionalContext`, `systemMessage`, and `initialUserMessage` strings, and its plain stdout, are capped at 10,000 characters"
1.5 SessionStart cost - "SessionStart runs on every session, so keep these hooks fast. Only `type: \"command\"` and `type: \"mcp_tool\"` hooks are supported."
1.6 SessionStart control - "SessionStart, SubagentStart, PostModelSwitch | Context only | `hookSpecificOutput.additionalContext` adds context for Claude. ... No blocking or decision control"
1.7 Timeouts - "Defaults: 600 for `command`, `http`, and `mcp_tool`" and "On `PreToolUse`, a timed-out `command`, `http`, or `mcp_tool` hook doesn't block the tool call, except for hooks whose failure blocks the action. ... To block the call when the hook times out, set `onFailure: \"block\"`."
1.8 Loop protection - "The `stop_hook_active` field is `true` when Claude Code is already continuing as a result of a stop hook. Check this value or process the transcript to avoid blocking on a condition that will never resolve." and "the `stop_hook_active` input and the 8-consecutive-continuation cap"
1.9 Exec form - "Exec form runs when `args` is present. Claude Code resolves `command` as an executable on `PATH` and spawns it directly with `args` as the argument vector. There is no shell"
1.10 Disable - "set `\"disableAllHooks\": true` in your settings file. ... There is no way to disable an individual hook while keeping it in the configuration."
1.11 Worktrees - "If Claude enters a worktree during the session, Claude Code keeps `${CLAUDE_PROJECT_DIR}` where it was and passes the worktree path to your hooks a different way"
1.12 Resume replay - "For mid-session events like `PostToolUse` or `UserPromptSubmit`, when you resume ... Claude Code replays the saved text rather than re-running the hook for past turns ... `SessionStart` hooks run again on resume"

## 2. Cursor hooks

URL: https://cursor.com/docs/hooks.md

2.1 Sources - "Define hooks in `hooks.json` files at the project or user level, or install them through plugins from Customize."
2.2 All sources run - "All matching hooks from every source run, and Cursor merges their responses" and "Priority order (highest to lowest): Enterprise → Team → Project → User" and "Hooks from installed plugins come after all of these. Plugin hooks run command hooks only."
2.3 Project trust - "Project hooks run in any trusted workspace and are checked into version control with your project"
2.4 sessionStart - "Called when a new composer conversation is created. This hook runs as fire-and-forget; the agent loop does not wait for or enforce a blocking response. Use it to set up session-specific environment variables or inject additional context." Output: "`env`" and "`additional_context`"
2.5 preCompact - "This is an observational hook that cannot block or modify the compaction behavior." Output: "`user_message`"
2.6 Failure - "`failClosed` | boolean | `false` | When `true`, hook failures (crash, timeout, non-zero exit code, no output) block the action instead of allowing it through. Permission hooks block on invalid JSON or an invalid response even when this is `false`."
2.7 Loop limit - "`loop_limit` | number | null | `5` | Per-script loop limit for stop/subagentStop hooks."
2.8 Third-party - "Cursor supports loading hooks from third-party tools like Claude Code."
2.9 Version field - "`cursor_version` | string | Cursor application version"

## 3. Cursor third-party hooks

URL: https://cursor.com/docs/reference/third-party-hooks.md

3.1 Enablement - "Claude Code hooks load when Include Third-Party Plugins, Skills, and Other Configs is enabled in Cursor Settings → Agents → Third-Party Imports. The setting is on by default."
3.2 Sources - "7. Claude user (`~/.claude/settings.json`)" ... "All matching hooks from every source run."
3.3 Mapping - "`SessionStart` | `sessionStart`" and "`PostToolUse` | `postToolUse`"
3.4 Exit codes - "Other exit codes: Hook failed, action proceeds (fail-open)"

## 4. Cursor plugins

URL: https://cursor.com/docs/plugins.md

4.1 Components - "Cursor Plugins: plugins with a `.cursor-plugin/plugin.json` manifest, which add rules, agents, commands, hooks, and variables"
4.2 Install - "Select Install and choose a project or user scope."
4.3 Local folder - "Before you publish, put either plugin format in `~/.cursor/plugins/local`" ... "Restart Cursor, or run Developer: Reload Window." ... "After a reload, Cursor discovers plugins in this folder if local plugin imports are allowed."
4.4 Enterprise gate - "On Enterprise, admins control this with Allow Local Plugin Imports ... The setting is off by default on Enterprise"
4.5 Symlinks - "Symlinks in `~/.cursor/plugins/local` load only when the target resolves to a directory inside that folder."
4.6 Skill invocation - "Skills appear in the Agent Decides section and can be invoked manually with `/skill-name` in chat."

## 5. Codex hooks

URL: https://learn.chatgpt.com/docs/hooks.md

5.1 Concurrency - "Matching hooks from multiple files all run. ... Multiple matching command hooks for the same event are launched concurrently"
5.2 Locations - "User | `$CODEX_HOME/hooks.json`" and "Trusted project | `.codex/hooks.json`"
5.3 Worktrees - "In a linked Git worktree, a project layer can read hooks from the corresponding directory in the main checkout. User and system hooks can still load in untrusted projects."
5.4 Duplicates - "If two files register the same command for an event, Codex can run it twice when that event occurs."
5.5 Trust - "Before a non-managed hook can run, Codex requires you to review and trust the exact hook definition. Codex records trust against the hook's current hash, so new or changed hooks are marked for review and skipped until trusted."
5.6 Trust UI - "Use `/hooks` in the CLI to inspect hook sources, review new or changed hooks, trust hooks, or disable individual non-managed hooks."
5.7 Timeout - "If `timeout` is omitted, Codex uses `600` seconds for most hooks."
5.8 Context budget - "Omit `additionalContextLimit` to use the default `2500`-token threshold."
5.9 SessionStart - "`source` | `string` | How the session started: `startup`, `resume`, `clear`, `compact`, or `fork`" and "After Codex compacts a root session, `SessionStart` hooks that match `source: \"compact\"` run before the next model request."
5.10 Background - "Background hooks can't block, approve, rewrite, or otherwise control the operation that triggered them."
5.11 Failure - "A `PreToolUse` error, timeout, or malformed response can let the tool run."
5.12 Surfaces - The page does not mention the IDE extension.

## 6. Codex plugins

URL: https://learn.chatgpt.com/docs/plugins.md

6.1 Surfaces - "Codex CLI also has a plugin browser for Codex environments. The IDE extension doesn't support plugins."
6.2 Plugin hooks - "Hook scripts must be available in the execution environment ... Review and trust plugin hooks before they run."

## 7. Codex skills and IDE extension

URLs: https://learn.chatgpt.com/docs/build-skills.md, https://learn.chatgpt.com/docs/developer-settings.md?surface=ide, https://learn.chatgpt.com/docs/developer-commands.md?surface=ide

7.1 Surfaces - "Standalone skills are available in the ChatGPT desktop app, Codex CLI, and IDE extension."
7.2 Invocation - "In Codex CLI or the IDE extension, run `/skills` or type `$` to mention a skill."
7.3 User location - "`USER` | `$HOME/.agents/skills`"
7.4 Implicit policy - "`allow_implicit_invocation` (default: `true`): When `false`, Codex won't implicitly invoke the skill based on user prompt; explicit `$skill` invocation still works."
7.5 Shared settings - "Codex settings control agent behavior shared with Codex CLI, including the model, reasoning effort, permissions, sandbox, MCP servers, and personalization. Codex reads these settings from `config.toml`."
7.6 IDE slash commands - The IDE slash-command table lists `/approve`, `/cloud`, `/compact`, ... `/worktree`; it lists no `/hooks` command.

## 8. VS Code agent hooks

URL: https://code.visualstudio.com/docs/agent-customization/hooks.md

8.1 Harness - "Select **Copilot** from the **Session Target** UI control to use the Copilot harness. VS Code, the GitHub Copilot app, and GitHub Copilot CLI share this harness and its hook format."
8.2 Other targets - "**Claude** | Claude hooks reference" and "**Codex** | Codex hooks documentation"
8.3 User source - "User hook files in `~/.copilot/hooks/`, or `$COPILOT_HOME/hooks/` when `COPILOT_HOME` is set."
8.4 Repository source - "`.github/hooks/*.json` at the repository root"
8.5 Claude files - "It also reads repository `.claude/settings.json` and `.claude/settings.local.json`."
8.6 Duplicates - "Applicable hooks from multiple sources run together. A new repository hook does not replace a user or plugin hook for the same event."
8.7 Verification - "A file shown in the editor is not proof that its script executed."
8.8 Failure - "GitHub documents command `preToolUse` errors as denying the tool call, but timeouts as falling through to normal permissions"
8.9 Enterprise - "Claude and Codex harnesses are disabled when Copilot enterprise-managed settings apply"

## 9. GitHub Copilot hooks reference

URL: https://docs.github.com/en/copilot/reference/hooks-reference

9.1 Sources - "Hooks are loaded from the following sources in order (policy, then user, then project, then plugins) and combined. When the same event appears in multiple sources, all hook entries from all sources are run."
9.2 Timeout - "`timeoutSec` | number | No | Timeout in seconds. Default: `30`."
9.3 sessionStart - "source: \"startup\" | \"resume\" | \"new\";" and "Only `additionalContext` is consumed for `sessionStart`"
9.4 Failure - "For most events, hook failures (non-zero exit codes other than `2`, or timeouts) are logged and skipped."
9.5 preToolUse - "Command `preToolUse` hooks are fail-closed on errors ... Command hook timeouts are always fail-open"
9.6 postToolUse - "`additionalContext` | string | Additional guidance appended to `textResultForLlm` ... capped at 10 KB."

## 10. VS Code agent skills and plugins

URLs: https://code.visualstudio.com/docs/agent-customization/agent-skills.md, https://code.visualstudio.com/docs/agent-customization/agent-plugins.md

10.1 Skill locations - "Copilot | Project: `.github/skills/`<br>Personal: `~/.copilot/skills/`" and "OpenAI Codex | Project: `.agents/skills/`<br>Personal: `~/.agents/skills/`"
10.2 Slash - "Type `/` in the chat input field to see available skills and prompts, and select a skill to invoke it."
10.3 Front matter - "`disable-model-invocation: true` | Yes | No | Skills you only want to run on demand"
10.4 Name - "Must match the parent directory name. ... Names with invalid characters cause the skill to silently fail to load."
10.5 Codex harness - "experimental OpenAI Codex integration"
10.6 Plugin setting - "Enable or disable support for agent plugins with the `setting(chat.plugins.enabled)` setting."
10.7 Plugin trust - "Deep links always prompt for explicit user confirmation before registering a marketplace or installing a plugin, and cannot bypass trust dialogs, workspace trust, or enterprise policies."
10.8 CLI plugins - "Discovered plugins from `~/.copilot/installed-plugins/` appear on the **Plugins** page"

## 11. Claude Code skills and plugins

URLs: https://code.claude.com/docs/en/skills.md, https://code.claude.com/docs/en/discover-plugins.md

11.1 Personal skills - "Personal | `~/.claude/skills/<skill-name>/SKILL.md` | All your projects on this machine"
11.2 Precedence - "Enterprise over personal, and personal over project. With `deploy` in both `~/.claude/skills/` and the project's `.claude/skills/`, `/deploy` runs the personal one"
11.3 Shell install - "Run `claude plugin install` in your shell to install a plugin without starting a Claude Code session, for example from a setup script."
11.4 Scope - "**User scope**: the plugin is enabled for you in every project on this machine. The entry goes in `enabledPlugins` in `~/.claude/settings.json`."

## 12. Cursor plugins reference

URL: https://cursor.com/docs/reference/plugins.md (curl, Markdown twin)

12.1 Discovery - "Rules | `rules/` | All `.md`, `.mdc`, or `.markdown` files" and "Hooks | `hooks/hooks.json` | Parsed for hook event names"
12.2 Always-applied rule - "`alwaysApply` | boolean | If `true`, rule applies to all files. If `false`, rule is available on request."
12.3 Root variable - "Cursor expands `${CURSOR_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_ROOT}` to the plugin's install path in `command`, `args`, `env` values, and `cwd`."
12.4 Not stated - The page does not say whether an always-applied plugin rule and a User Rule are presented to the agent in the same way.

## Not run

- No hook, plugin or skill was installed or executed; no client version on this machine was read.
- No home configuration was read or changed.
- Context7 was available in this session and was queried once for Claude Code as a cross-check; it agreed with page 1. It was not used for the other clients.
