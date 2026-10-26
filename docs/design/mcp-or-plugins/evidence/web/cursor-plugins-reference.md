# Plugins reference - Cursor Docs
URL: https://cursor.com/docs/reference/plugins
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Formats
## Supported plugin formats

Cursor loads plugins in two formats, identified by their manifest location:

| Format | Manifest location | Components |
| --- | --- | --- |
| Agent Plugins (open standard) | `plugin.json` at the plugin root | Skills, MCP servers |
| Cursor Plugins | `.cursor-plugin/plugin.json` | Skills, MCP servers, rules, agents, commands, hooks, variables |

## Excerpt 2: Variables
## Variables

Use `variables` to declare the names (and types/descriptions) of user-specified configuration — for example an API token for an HTTP MCP server. The plugin only defines the schema; it does not include the secret values themselves.

Team admins set the actual values in the dashboard under Plugins (at install time, or later via Configure on the plugin).

Do not put secret values in the plugin repo. In `mcp.json` and other plugin config, include only `${VAR}` placeholders that match property names in the schema.

## Excerpt 3: Plugin MCP servers
`${POSTGRES_URL}` is a plugin variable placeholder (not shell `${env:...}`). Declare the variable name under `variables` in `plugin.json`, put only the placeholder in plugin config, and set the value in the dashboard under Plugins → Configure. Plugin-managed MCP config is read-only in the dashboard.
