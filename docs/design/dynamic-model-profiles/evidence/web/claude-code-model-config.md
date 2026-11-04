# Model configuration (Claude Code)

URL: https://code.claude.com/docs/en/model-config.md
Retrieved: 2026-11-04, between 14:00 and 16:15 (UTC+2); the tool returns no time for each page
Tool: WebFetch (Cursor)
Processed: unknown (the tool returns the page as Markdown and does not say whether a model processed it)
Data class: public

Excerpts are verbatim from the text the tool returned.

1. Alias table - "| `best` | Uses the model the `fable` alias resolves to where Fable is available to you, otherwise the same model as `opus` |"
2. Alias table - "| `fable` | Uses the Fable model for your provider for your hardest and longest-running tasks |"
3. Alias table - "| `sonnet` | Uses the latest Sonnet model for daily coding tasks |" and "| `opus` | Uses the latest Opus model for complex reasoning tasks |" and "| `haiku` | Uses the fast and efficient Haiku model for simple tasks |"
4. Provider table - "| Anthropic API | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 |"
5. Provider table - "| Amazon Bedrock, Google Cloud's Agent Platform | Opus 5.5 | Sonnet 4.5 | Haiku 4.5 |"
6. Fable alias - "Unless you set `ANTHROPIC_DEFAULT_FABLE_MODEL`, the `fable` alias resolves to Fable 5.1, except in Claude apps gateway sessions, where `fable` and `best` resolve to Fable 5."
7. Alias movement - "Aliases point to the recommended version for your provider and update over time. To pin to a specific version, use the full model name, for example `claude-opus-5-5`, or set the corresponding environment variable like `ANTHROPIC_DEFAULT_OPUS_MODEL`."
8. Client version - "Sonnet 5.5 requires Claude Code v2.1.284 or later, and Opus 5.5 requires v2.1.280 or later." and "Use v2.1.293 or later with Haiku 5.5."
9. Fable default - "Neither Fable model is the account-type default on any plan or provider. Select one explicitly:"
10. Fable billing - "In non-interactive mode with the `-p` flag, and in an Agent SDK application that doesn't show the prompt, Claude Code never asks for consent. When a Fable request there would bill to usage credits, Claude Code bills it without asking."
11. Precedence - "1. During session: use `/model <alias|name>` to switch immediately" / "2. At startup: launch with `claude --model <alias|name>`" / "3. Environment variable: set `ANTHROPIC_MODEL=<alias|name>`" / "4. Settings: configure permanently in your settings file using the `model` field" / "5. Default for new sessions: set `ANTHROPIC_DEFAULT_MODEL=<alias|name>`"
12. Subagent inheritance - "If you switch models with `/model`, the switch also reaches subagents that inherit the main conversation's model, because Claude Code resolves their model from the one your session is using when Claude starts them. ... To keep a custom subagent on a smaller model, set `model` in its definition."
13. Allowlist scope - "- Subagent and teammate models: the `model` field in subagent frontmatter, the Agent tool's `model` parameter, agent team teammate models, `CLAUDE_CODE_SUBAGENT_MODEL`, and, on v2.1.197 and earlier, the model picker in the `/agents` wizard"
14. Allowlist scope - "- Skill and command models: the `model` frontmatter in skills and commands"
15. Blocked subagent model - "- Subagent or teammate override: Claude Code runs the subagent or teammate on a fallback model rather than failing the request."
16. Blocked skill model - "- Skill or command override: Claude Code ignores the override, including a blocked family alias, and the skill or command runs on the session model."
17. Not enforcement - "The `model` setting is an initial selection, not enforcement."
18. Organisation controls - "- `availableModels`: restricts which named models users can switch to" and "- `enforceAvailableModels`: extends the `availableModels` allowlist to the Default option, so Default cannot resolve to a model outside the list" and "- `deniedModels` and `availableModelsMatch`: block specific versions that an `availableModels` entry would otherwise permit"
19. Fallback chains - "Claude Code also applies the chain to subagents. When a subagent's request fails over, Claude Code tries your configured fallback models in order, and the subagent continues on the model that accepts the request. Your session's model is unchanged."
20. Content fallback - "Fable 5.1, Fable 5, and Opus 5.5: biology-flagged requests re-run on Opus 5, and cybersecurity-flagged requests re-run on Opus 4.8."
21. Subagent effort - "On the main conversation's model, a subagent or teammate with no `effort` of its own runs at the level you pick in the session or set with `--effort`. On another model, that level doesn't apply. To pick a subagent's level, set `effort` in its definition."
22. Observability - "The check also covers a `model` set in subagent frontmatter. The stderr warning is suppressed for `--output-format json` and `stream-json`; read the actual model from the `modelUsage` field of the result message instead."
23. Haiku 5.5 - "On the Anthropic API, Haiku 5.5 runs with the 1M context window on every plan, with no `[1m]` suffix to select. Its model ID is `claude-haiku-5-5`."
24. Default value - "| `default` | Special value that clears any model override and reverts to the runtime default for your account. Not itself a model alias |"
25. Account-type default - "- Pro, Max, Ultra, Team, Enterprise, and Anthropic API: defaults to Opus 5.5"
26. Organisation default - "When an admin has set an organization default model, `default` resolves to that model instead of the account-type default above."
27. opusplan - "| `opusplan` | Special mode that uses `opus` during plan mode, then switches to `sonnet` for execution |" and "The `opusplan` model alias provides an automated hybrid approach:" and "- In execution mode: automatically switches to `sonnet` for code generation and implementation"
28. Auto mode classifier - "- Auto mode classifier: when the allowlist excludes the default classifier model, classifier requests that would use that model run on the session model, or an Opus model in Fable sessions."
29. Alias list (a reading of the whole alias table, not a quotation) - the table lists `default`, `best`, `fable`, `sonnet`, `opus`, `haiku`, `sonnet[1m]`, `opus[1m]` and `opusplan` and no alias named `auto`.
