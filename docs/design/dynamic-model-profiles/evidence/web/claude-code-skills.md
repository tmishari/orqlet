# Extend Claude with skills (Claude Code)

URL: https://code.claude.com/docs/en/skills.md
Retrieved: 2026-11-04, between 14:00 and 16:15 (UTC+2); the tool returns no time for each page
Tool: WebFetch (Cursor)
Processed: unknown (the tool returns the page as Markdown and does not say whether a model processed it)
Data class: public

Excerpts are verbatim from the text the tool returned.

1. Invocation field - "| `disable-model-invocation` | No | Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`."
2. Model field - "| `model` | No | Model to use when this skill is active. The override applies for the rest of the current turn and isn't saved to settings. The session model resumes when you send your next prompt. Accepts the same values as `/model`, or `inherit` to keep the active model. A value excluded by your organization's `availableModels` allowlist isn't used, and the session keeps its current model."
3. Model field with fork - "With `context: fork`, the value sets the forked subagent's model instead, and an excluded value follows the same rules as a subagent model override."
4. Effort field - "| `effort` | No | Effort level for the rest of the current turn. Overrides the session effort level, but not the `CLAUDE_CODE_EFFORT_LEVEL` environment variable. With `context: fork`, the value sets the forked subagent's effort level instead."
5. Fork fields - "| `context` | No | Set to `fork` to run in a forked subagent context." and "| `agent` | No | Which subagent type to use when `context: fork` is set. |"
6. Tool grant duration - "Tools Claude can use without asking permission during the turn that invokes this skill. The grant clears when you send your next message."
