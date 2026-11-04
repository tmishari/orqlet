# Cursor CLI: authentication, commands and changelog

URL: https://cursor.com/docs/cli/reference/authentication, https://cursor.com/docs/cli/reference/parameters, https://cursor.com/help/integrations/cli and https://cursor.com/docs/cli/changelog
Retrieved: 2026-11-04, between 18:20 and 19:10 (UTC+2); the tool returns no time for each page
Tool: WebSearch (Cursor): excerpts of the first three pages came in the search result, and the full text of the changelog was saved to a file
Processed: unknown (the tool does not say whether a model processed the text)
Data class: public

Excerpts are verbatim from the text the tool returned.

1. Authentication status - "Check your current authentication status:"
2. What status shows - "- Whether you're authenticated" and "- Your account information"
3. Not authenticated - "\"Not authenticated\" errors: Run `agent login` or ensure your API key is correctly set"
4. Models command - "| `models` | List available models for this account | `agent models` |"
5. Status command - "| `status` | `whoami` | View authentication status | `agent status` |"
6. About command - "| `about` | Display version, system, and account info | `agent about` |"
7. Update command - "| `update` | Update Cursor Agent to the latest version | `agent update` |"
8. Auto-update - "Cursor CLI auto-updates by default. To update manually, run:"
9. Version check - "Run `agent --version` to check your installed version, and `agent update` to upgrade in place."
10. Empty-list fix - "`agent models` lists your team's Bedrock models. When your team connects AWS Bedrock through an IAM role, `agent models` and `--list-models` now show the Bedrock models for your region instead of an empty list. The list matches what `--model` accepts."
11. Version of that fix (a reading of the headings of the saved text, not a quotation) - the bullet of item 10 sits under the heading "## v2026.09.15"; the newest heading in the saved text is "## v2026.10.22".
