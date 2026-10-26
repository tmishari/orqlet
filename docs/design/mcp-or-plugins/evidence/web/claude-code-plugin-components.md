# Add components to a plugin - Claude Code Docs
URL: https://code.claude.com/docs/en/plugins/components
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Instructions in a plugin
To include instructions in a plugin, write them as a skill. Claude Code doesn’t load a `CLAUDE.md` at the plugin root, and `claude plugin validate` warns `CLAUDE.md at the plugin root is not loaded as project context`. If a rule must hold every time, such as blocking edits to protected files, add it to the plugin as a hook rather than a skill. To choose between the two, see the Hook vs Skill tab under Compare similar features. For frontmatter fields and supporting files, see Skills.

## Excerpt 2: MCP servers
An MCP server gives Claude tools from an external system. Declare it in `.mcp.json` at the plugin root, in the same shape as a project `.mcp.json`. This `.mcp.json` declares one server named `db`:

.mcp.json

## Excerpt 3: Ask the user for configuration values
Ask the user for configuration values

Declare the values your plugin needs from the user in the `userConfig` manifest key, so users don’t edit `settings.json` themselves. Each option appears in a dialog with its `title` as the label and its `description` beneath it. Set `"sensitive": true` for a token or password. The dialog then masks the input, and the value is stored in secure storage rather than `settings.json`. This manifest asks for an endpoint and a token:

## Excerpt 4: When the configuration dialog appears
When the configuration dialog appears

The dialog is part of the interactive `/plugin` interface. When the user does any of the following, it opens for any option that isn’t set yet:

- Installs the plugin in `/plugin`
- Runs `/plugin install @ ` inside a session
- Enables the plugin from the Installed tab in `/plugin`
