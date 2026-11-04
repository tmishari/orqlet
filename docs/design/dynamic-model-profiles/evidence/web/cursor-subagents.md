# Subagents (Cursor)

URL: https://cursor.com/docs/subagents.md
Retrieved: 2026-11-04, between 14:00 and 16:15 (UTC+2); the tool returns no time for each page
Tool: WebFetch (Cursor)
Processed: unknown (the tool returns the page as Markdown and does not say whether a model processed it)
Data class: public

Excerpts are verbatim from the text the tool returned.

1. Clean context - "Subagents start with a clean context. The parent agent includes relevant information in the prompt since subagents don't have access to prior conversation history."
2. Model field - "| `model` | string | No | `inherit` | Model to use: `inherit` or a specific model ID. See model configuration. |"
3. Readonly field - "| `readonly` | boolean | No | `false` | If `true`, the subagent runs with restricted write permissions (no file edits, no state-changing shell commands). |"
4. Model options - "| `inherit` | Uses the same model as the parent agent. This is the default. |" and "| A specific model ID | Uses the exact model you specify, such as `composer-2` or `gpt-5.6-sol`."
5. Model parameters - "Append square brackets to a model ID to set per-model options like speed, reasoning effort, and context window."
6. Parameter examples - "| `claude-opus-5[effort=high,context=300k]` | Combines options. |"
7. When the model is not used - "Cursor honors the `model` field in your subagent frontmatter unless one of these conditions applies:" followed by "- Team admin restrictions" , "- Legacy Max Mode setting" and "- Plan limitations"
8. Fallback - "In these cases, Cursor falls back to a compatible model."
9. Parent versus subagent - "The model picker, including Auto, applies to the parent agent. A subagent can run a different model:"
10. Who names the model - "Custom subagents use `inherit` or the `model` field in frontmatter." and "The parent agent can name a model when it launches a subagent."
11. Observability - "The subagent task card shows which model ran. The usage dashboard lists that model on the matching usage row."
12. Billing - "Each request bills at the list price of the model that ran."
13. Tool inheritance - "Subagents inherit all tools from the parent, including MCP tools from configured servers."
14. Override statement - "Cursor also overrides a configured model when your team admin blocks it, your plan doesn't include it, or a legacy request-based plan requires Max Mode and you don't have it enabled."
15. Nesting - "Nested launches also need Task tool access in the current mode, and hooks or tool policies can block spawning."
