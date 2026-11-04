# Create custom subagents (Claude Code)

URL: https://code.claude.com/docs/en/sub-agents.md
Retrieved: 2026-11-04, between 14:00 and 16:15 (UTC+2); the tool returns no time for each page
Tool: WebFetch (Cursor)
Processed: unknown (the tool returns the page as Markdown and does not say whether a model processed it)
Data class: public

Excerpts are verbatim from the text the tool returned.

1. Frontmatter fields - "Frontmatter fields: `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `mcpServers`, `hooks`, `maxTurns`, `autoCompactWindow`, `skills`, `initialPrompt`, `memory`, `effort`, `background`, `omitClaudeMd`, and `isolation`."
2. Model field - "| `model` | No | Model to use: `sonnet`, `opus`, `haiku`, `fable`, a full model ID such as `claude-opus-5-5`, or `inherit`. When you omit it, Claude Code picks the model in the subagent model order |"
3. Effort field - "| `effort` | No | Effort level when this subagent is active. Overrides the session effort level, but not the `CLAUDE_CODE_EFFORT_LEVEL` environment variable. Options: `low`, `medium`, `high`, `xhigh`, `max`; available levels depend on the model."
4. Per-invocation model - "When Claude invokes a subagent, it can also pass a `model` parameter for that specific invocation. On an Agent tool call, that parameter takes a model alias: `sonnet`, `opus`, `haiku`, or `fable`. Claude can't pass a full model ID or `inherit` on that call."
5. Resolution order - "2. The subagent definition's `model` frontmatter, where `inherit` selects the main conversation's model" and "3. The `CLAUDE_CODE_SUBAGENT_MODEL` environment variable, when you set it to a model alias or model ID"
6. Order changed - "Before v2.1.251, `CLAUDE_CODE_SUBAGENT_MODEL` came first in this order and overrode both the per-invocation parameter and the frontmatter, including `model: inherit`."
7. Blocked value - "For any other blocked value, on providers where that substitution doesn't operate, or when the allowlist permits no version of the family, Claude Code runs the subagent on the inherited model instead."
8. Observability - "To check which model a subagent is running on, run `/tasks`. Claude Code names the model on the subagent's row, and adds the effort level set for that subagent, if any. Requires Claude Code v2.1.242 or later."
9. Force one model - "To apply one model to every subagent, teammate, and workflow agent, also set `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` to `1`. Requires Claude Code v2.1.257 or later."
10. Force effect - "While `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is on, Claude Code ignores the `model` field in subagent definitions, and Claude can't pass a model when it starts a subagent."
11. Fresh context - "Each subagent starts with a fresh, isolated context window. It doesn't see your conversation history, the skills you've already invoked, or the files Claude has already read."
12. Fork - "The exception is a fork, which inherits the parent conversation instead of starting fresh."
13. Fork default - "Claude can start a fork on its own while fork mode is on, as it is by default."
14. Fork definition - "A fork is a subagent that inherits the entire conversation so far instead of starting fresh. This drops the input isolation that subagents otherwise provide: a fork sees the same system prompt, tools, model, and message history as the main session"
15. Tool inheritance - "Subagents inherit the built-in tools and MCP tools available in the main conversation, narrowed by two filters"
