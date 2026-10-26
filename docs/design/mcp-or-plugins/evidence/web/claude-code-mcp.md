# Connect Claude Code to tools via MCP - Claude Code Docs
URL: https://code.claude.com/docs/en/mcp
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: MCP installation scopes
MCP installation scopes

MCP servers can be configured at three scopes. The scope you choose controls which projects the server loads in and whether the configuration is shared with your team. Administrators can also deploy or provide servers for every user via managed configuration.

| Scope | Loads in | Shared with team | Stored in |
| --- | --- | --- | --- |
| Local | Current project only | No | `~/.claude.json` |
| Project | Current project only | Yes, via version control | `.mcp.json` in project root |
| User | All your projects | No | `~/.claude.json` |

Local scope

## Excerpt 2: Local scope
Local scope

Local scope is the default. A local-scoped server loads only in the project where you added it and stays private to you. Claude Code stores it in `~/.claude.json` under that project’s path, so the same server won’t appear in your other projects. Use local scope for personal development servers, experimental configurations, or servers with credentials you don’t want in version control.

The term “local scope” for MCP servers differs from general local settings. MCP local-scoped servers are stored in `~/.claude.json` (your home directory), while general local settings use `.claude/settings.local.json` (in the project directory). See Settings for details on settings file locations.

## Excerpt 3: Project scope
Project scope

Project-scoped servers enable team collaboration by storing configurations in a `.mcp.json` file at your project’s root directory. When you add a project-scoped server, Claude Code automatically creates or updates this file with the appropriate configuration structure. Check `.mcp.json` into version control so everyone on your team gets the same MCP tools and services.

```
# Add a project-scoped server
claude mcp add --transport http shared-server --scope project https://example.com/mcp

```

The resulting `.mcp.json` file follows a standardized format:

```
{
  "mcpServers": {
    "shared-server": {
      "type": "http",
      "url": "https://example.com/mcp"

## Excerpt 4: Plugin-provided MCP servers
Plugin-provided MCP servers

Plugins can bundle MCP servers that provide tools and integrations when you enable the plugin. How plugin MCP servers work:

- Plugins define MCP servers in `.mcp.json` at the plugin root or inline in `plugin.json`
- When you enable a plugin, Claude Code starts its MCP servers automatically
- Claude Code offers plugin MCP tools alongside manually configured MCP tools
- You add and remove plugin servers by installing or uninstalling the plugin, not with `/mcp` commands. You can still toggle an installed plugin server off in `/mcp`, which stops Claude Code from connecting to it without removing the plugin

## Excerpt 5: Same server name in more than one scope
- Same name in more than one scope: if you define the same server name in more than one scope with different endpoints, Claude Code warns about the conflict in `claude mcp list` output and in `/mcp`. Claude Code stores OAuth sign-ins per endpoint, so when you authenticate the definition that loads in one project, you still need to sign in separately in a project where a different definition loads. Keep the endpoint you want and remove the others with `claude mcp remove --scope `. In the warning, Claude Code quotes each scope’s endpoint as written in your configuration, with `${VAR}` references unexpanded, so it never shows a resolved value such as an API key.

## Excerpt 6: Environment variable expansion in .mcp.json
Environment variable expansion in `.mcp.json`

Claude Code supports environment variable expansion in `.mcp.json` files, allowing teams to share configurations while maintaining flexibility for machine-specific paths and sensitive values like API keys.

Supported syntax

- `${VAR}`: expands to the value of environment variable `VAR`
- `${VAR:-default}`: expands to `VAR` if set, otherwise uses `default`

Expansion locations

Environment variables can be expanded in:

## Excerpt 7: Authenticate with remote MCP servers
Authenticate with remote MCP servers

Many cloud-based MCP servers require authentication. Claude Code supports OAuth 2.0 for secure connections. Claude Code marks a remote server as needing authentication when the server responds with `401 Unauthorized` or `403 Forbidden`. What Claude Code shows depends on the server:

## Excerpt 8: headersHelper supplied by a repository or plugin
A `headersHelper` that a repository or plugin supplies is a command you didn’t write, so Claude Code runs it without the credential variables from your environment, such as `ANTHROPIC_API_KEY`. Where you configured the server decides whether this applies:

- Removed: a server in a project `.mcp.json` or in a plugin, and an inline server in an agent file from your project or from an `--add-dir` directory
- Not removed: a server at user or local scope, in managed MCP, from a claude.ai connector, or supplied by the SDK or `--mcp-config`, and an inline server in an agent file from `~/.claude/agents/`, from managed settings, or passed with `--agents`

Apart from Git’s `GIT_CONFIG_KEY_ ` variables, Claude Code removes every variable from your environment whose name looks like a credential, such as a name with `TOKEN`, `SECRET`, `PASSWORD`, `KEY`, or `AUTH` in it in either letter case, so `ANTHROPIC_API_KEY` and `MY_REGISTRY_TOKEN` are both removed. Claude Code also removes a fixed list of credential variables whose names don’t follow that pattern, such as `ANTHROPIC_CUSTOM_HEADERS`. When this applies to your helper, have the script read its credential from a file or a credential store. If the server’s `url` carries the live value of one of these variables, such as `MY_REGISTRY_TOKEN`, the `CLAUDE_CODE_MCP_SERVER_URL` value the helper receives has that part replaced with `REDACTED` as well.

## Excerpt 9: Managed MCP configuration
For organizations that need centralized control over which MCP servers users can connect to, see Managed MCP configuration. It covers deploying a fixed server set with `managed-mcp.json`, providing servers to every user with `managedMcpServers`, restricting servers with `allowedMcpServers` and `deniedMcpServers`, and what users see when a server is blocked.
