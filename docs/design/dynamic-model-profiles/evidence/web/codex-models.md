# Models (ChatGPT Learn, Codex)

URL: https://developers.openai.com/codex/models
Retrieved: 2026-11-04, between 14:00 and 16:15 (UTC+2); the tool returns no time for each page
Tool: WebFetch (Cursor)
Processed: unknown (the tool returns the page as Markdown and does not say whether a model processed it)
Data class: public

Excerpts are verbatim from the text the tool returned. The same page text was returned by a second fetch of https://learn.chatgpt.com/docs/models.md.

1. Recommended models - "Astra suits the most demanding workflows. GPT-6.1 Sol offers near-Astra performance at a lower cost than Astra. GPT-6.1 Terra is a fast, efficient choice for writing, visual understanding, and computer use. Luna suits focused, repeatable tasks."
2. Terra requirement - "GPT-6.1 Terra requires Codex CLI 0.159.0 or later. To use it, run `codex -m gpt-6.1-terra`."
3. Select a model - "codex --model gpt-6.1-sol"
4. Luna command - "codex -m gpt-6-luna"
5. Astra effort - "In configuration, Astra’s Light setting is `low`."
6. Luna effort - "GPT-6 Luna supports reasoning efforts up to Max, but not Ultra."
7. Context - "GPT-6.1 Sol uses a default context window of 500,000 tokens in Codex and ChatGPT Work."
8. Plan dependence - "On Plus, Pro, Business, Enterprise, and Edu plans, choose GPT-6.1 Sol (`gpt-6.1-sol`) when available." and "On Free and Go plans, choose GPT-6 Luna (`gpt-6-luna`) in the desktop app when available."
9. Admin enablement - "In Enterprise and Edu, an administrator must enable Luna first."
10. Retirement - "Effective October 14, 2026, at noon PDT (19:00 UTC), GPT-5.5 retires from Codex for users signed in with ChatGPT. The OpenAI API and Codex sessions authenticated with an API key aren’t affected."
11. Stale settings - "Replace `gpt-5.5` in workspace defaults, saved model settings, managed configurations, custom agents, scheduled tasks, and scripts that select a model."
12. API-key access - "With API-key authentication, model availability follows your API organization and project."
13. Availability varies - "Advanced controls are illustrative; available options and defaults vary by plan, client, workspace settings, and rollout."
14. Default model key - "To specify a model, add a `model` entry to your configuration file." followed by "model = \"gpt-6.1-sol\""
15. Custom provider - "For a custom model provider or gateway, use a compatible Responses API endpoint."
16. Default Power setting - "In the ChatGPT desktop app and ChatGPT Work on the web, start with the default Power setting available to your account. Move toward Smarter for deeper reasoning or Faster for faster, lower-cost work. Open Advanced to choose a specific model, reasoning effort, or speed."
17. Power presets - "The six Power presets shown are Luna High, GPT-6 Sol Light (selected in this example), GPT-6 Sol Medium, Astra Light, Astra Medium, and Astra Extra High. Some paid plans omit Astra Extra High."
18. Recommended model - "If you don’t specify a model, the ChatGPT desktop app, Codex CLI, or IDE extension uses a recommended model."
19. Router absence (a reading of the whole page text, not a quotation) - the page text names no automatic per-task model router and no model or mode named Auto.
