# Model Context Protocol (MCP) - Cursor Docs
URL: https://cursor.com/docs/mcp
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Config interpolation
### Config interpolation

Use variables in `mcp.json` values. Cursor resolves variables in these fields: `command`, `args`, `env`, `url`, and `headers`.

Supported syntax:

- `${env:NAME}` environment variables
- `${userHome}` path to your home folder
- `${workspaceFolder}` project root (the folder that contains `.cursor/mcp.json`)

## Excerpt 2: Authentication
### Authentication

MCP servers use environment variables for authentication. Pass API keys and tokens through the config.

Cursor supports OAuth for servers that require it. Sign-in uses the authorization code flow with PKCE.

## Excerpt 3: Static OAuth for remote servers
For MCP servers that use OAuth, you can provide static OAuth client credentials in `mcp.json` instead of dynamic client registration. Use this when:

- The MCP provider gives you a fixed Client ID (and optionally Client Secret)
- The provider requires whitelisting a redirect URL (e.g. Figma, Linear)
- The provider does not support OAuth 2.0 Dynamic Client Registration

## Excerpt 4: Team MCP distribution
### Team MCP distribution

Configure shared Team MCP servers under Dashboard > Plugins & MCPs. These servers are available to Cloud Agents.

A Team MCP server's config and a team plugin's variables are shared by the whole team. Editing them from any surface, including an automation's MCP settings, changes the value for every teammate and automation that uses them. Only team admins can edit a Team MCP server or replace credentials a team plugin already has. Org admins have the same access on every team linked to their Organization, even without a team admin role.

## Excerpt 5: MCP Allowlist and user MCP extensions
### MCP Allowlist

Enterprise admins can control which MCP servers users may run from the Cursor dashboard. Open Team Settings > MCP Configuration to configure which servers and tools the team may run. The Plugins & MCPs page also links here. Allowlisting approves an MCP configuration. It does not distribute or install the server.

### User MCP extensions

Admins can allow users to configure their own MCP servers outside admin-defined command or URL patterns. For user MCPs that do not match an admin-defined pattern, the User MCP Network Denylist can block matching network destinations.
