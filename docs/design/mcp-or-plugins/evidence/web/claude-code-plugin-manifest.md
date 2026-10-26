# Plugin manifest reference - Claude Code Docs
URL: https://code.claude.com/docs/en/plugins/manifest-reference
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: mcpServers
`mcpServers` takes a `.json` file path, an MCP bundle path or URL, an inline map, or an array mixing them. For server config fields, see plugin-provided MCP servers. Claude Code loads `.mcp.json` at the plugin root first, then each declared shape in order. A server name declared later replaces an earlier one. An `mcpServers` value takes one of these shapes:

| Shape | Example value | What Claude Code does |

## Excerpt 2: User configuration
`userConfig` declares values Claude Code prompts the user for when the plugin is enabled, so users don’t edit `settings.json` themselves. Keys are identifiers made of letters, digits, and underscores, and can’t start with a digit. Each value is a strict object with these fields. An unknown key fails validation.

| Field | Required | Description |
| --- | --- | --- |
| `type` | Yes | One of `string`, `number`, `boolean`, `directory`, or `file` |
| `title` | Yes | Label shown in the configuration dialog |

## Excerpt 3: sensitive field
| `sensitive` | No | If `true`, masks input and stores the value in secure storage instead of `settings.json` |

## Excerpt 4: Where values are stored and how to reference them
Where values are stored

Non-sensitive values are saved under `pluginConfigs` in the user’s `settings.json`. Sensitive values go to the platform’s secure credential store instead. The settings page lists which settings files `pluginConfigs` is read from.

Reference a saved value

Reference a saved value where the plugin needs it, in one of two forms:

- `${user_config.KEY}`: substituted in MCP server config, LSP server config, exec-form hook `args`, and skill and agent content. In skill and agent content, only non-sensitive values are substituted, and a sensitive value there becomes a placeholder
- `CLAUDE_PLUGIN_OPTION_ `: exported to hook processes for every option, with ` ` uppercased. A shell-form hook reads `$CLAUDE_PLUGIN_OPTION_API_TOKEN` for `api_token`

## Excerpt 5: Plugin root CLAUDE.md
To click through this layout and read what each file does, open the plugin explorer. A `CLAUDE.md` at the plugin root isn’t loaded as context, and `claude plugin validate` warns when it finds one. To include instructions that load into Claude’s context, put them in a skill.
