# GitHub MCP Server - host integration and README
URL: https://github.com/github/github-mcp-server/blob/main/docs/host-integration.md
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.
Also from: README.md https://github.com/github/github-mcp-server/blob/main/README.md
Also from: server-configuration.md https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md

## Excerpt 1: Authentication and Authorization (host-integration.md)
GitHub MCP Servers require a valid access token in the `Authorization` header. This is true for both the Local GitHub MCP Server and the Remote GitHub MCP Server.

For the Remote GitHub MCP Server, the recommended way to obtain a valid access token is to ensure your client application supports OAuth 2.1. It should be noted, however, that you may also supply any valid access token. For example, you may supply a pre-generated Personal Access Token (PAT).

> [!IMPORTANT]
> The Remote GitHub MCP Server itself does not provide Authentication services.
> Your client application must obtain valid GitHub access tokens through one of the supported methods.

## Excerpt 2: Handling PATs securely (README.md)
To keep your GitHub PAT secure and reusable across different MCP hosts:

1. **Store your PAT in environment variables**
3. **Reference the token in configurations**

> **Note**: Environment variable support varies by host app and IDE. Some applications (like Windsurf) require hardcoded tokens in config files.

## Excerpt 3: Read-only and OAuth scopes (server-configuration.md)
- **Classic PATs** (`ghp_` prefix): Tools are filtered at startup based on token scopes—you only see tools you have permission to use
- **OAuth** (remote server): Uses scope challenges—when a tool needs a scope you haven't granted, you're prompted to authorize it
- **Other tokens**: No filtering—all tools shown, API enforces permissions
