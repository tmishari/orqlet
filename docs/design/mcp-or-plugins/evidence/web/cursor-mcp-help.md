# MCP integrations - Cursor Help
URL: https://cursor.com/help/customization/mcp
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Where the file lives
Create a file called `mcp.json` in one of these locations:

- Project-specific (shared with your team): `.cursor/mcp.json` in your project folder. Commit this to git so teammates get the same tools.
- Global (personal, all projects): `~/.cursor/mcp.json` in your home directory

Both files are merged. If the same server name appears in both, the project-level config takes priority.
