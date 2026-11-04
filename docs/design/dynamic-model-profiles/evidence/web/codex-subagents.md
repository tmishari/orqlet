# Subagents (ChatGPT Learn, Codex)

URL: https://learn.chatgpt.com/docs/agent-configuration/subagents
Retrieved: 2026-11-04, between 14:00 and 16:15 (UTC+2); the tool returns no time for each page
Tool: WebSearch (Cursor), which saved the full page text to a file; the excerpts below come from that file
Processed: unknown (the tool does not say whether a model processed the page text)
Data class: public

Excerpts are verbatim from the saved page text.

1. Inheritance - "If you don’t configure a subagent model or `model_reasoning_effort`, the subagent inherits the parent agent’s model and reasoning effort."
2. Where to set the model - "To balance intelligence, speed, and price for each task, request a specific model or reasoning effort in your prompt, configure `[agents]` defaults in `config.toml`, or set `model` and `model_reasoning_effort` directly in the custom agent file."
3. Starting point - "For most tasks in Codex, start with `gpt-6.1-sol` when your signed-in account or workspace has access. Otherwise, choose a model available to you. Use `gpt-6-luna` when you want a faster, lower-cost option for lighter subagent work."
4. Effort start values - "For explicit model settings, start with `high` for GPT-6 Luna or `low` for GPT-6 Astra."
5. Sandbox inheritance - "Subagents inherit the parent turn’s current sandbox and approval settings, including changes made with `/permissions` or `--yolo`. A custom agent file can’t replace those settings."
6. No separate sandbox - "Set sandbox and approval controls on the parent session. Custom agent instructions can ask an agent to avoid edits, but they don’t create a separate read-only sandbox."
7. Custom agent limits - "Each file defines one custom agent. Custom agents can change model settings and instructions or disable supported capabilities. They inherit the parent’s permissions, provider, and MCP servers; a custom agent file can’t override those settings."
8. Precedence - "If a custom agent file sets `model` or `model_reasoning_effort`, the value in the file takes precedence. Before applying the file, Codex resolves each setting from an explicit spawn value, then the corresponding `[agents]` default, then the parent’s value."
9. Session settings in an agent file - "Other session settings, including `sandbox_mode`, `approval_policy`, `model_provider`, and `mcp_servers`, don’t override the parent configuration when placed in a custom agent file."
10. Defaults keys - "| `agents.default_subagent_model` | string | No | Set the default model for spawned agents. |"
11. Explicit spawn wins - "Explicit spawn values override `agents.default_subagent_model` and `agents.default_subagent_reasoning_effort`."
12. Example agent - "model = \"gpt-6-luna\"" with "model_reasoning_effort = \"high\"" for a read-only explorer, and "model = \"gpt-6.1-sol\"" with "model_reasoning_effort = \"medium\"" for another agent.
13. Skills - "Skills inherit from the parent, and a custom agent can disable individual skills with `skills.config`."
