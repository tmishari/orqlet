# Atlassian Rovo MCP server: authentication and authorization, API token, admin controls
URL: https://developer.atlassian.com/cloud/rovo-mcp/guides/authentication-and-authorization/
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.
Also from: Configuring authentication via API token https://developer.atlassian.com/cloud/rovo-mcp/guides/configuring-authentication-via-api-token/
Also from: Control Atlassian MCP server settings https://support.atlassian.com/security-and-access-policies/docs/control-atlassian-mcp-server-settings/

## Excerpt 1: Authentication and authorization
The Atlassian Rovo MCP Server uses OAuth 2.1 as its primary authentication mechanism, providing a secure and standardized way for users to authorize access to resources via an interactive consent flow.

In addition, if enabled by your organization admin, the server supports authentication via API token for machine-to-machine and other non-interactive scenarios - for example, backend services, CI/CD pipelines, bots, and automated agents. Authentication via API token lets MCP clients authenticate without a browser-based OAuth consent screen.

Regardless of the method, every action respects the authenticated user's existing access controls and permissions. Access is granted only to data the user already has permission to view, and OAuth and API token authentication both honor configured scopes and Atlassian permissions.

## Excerpt 2: Supported authentication methods
| Method | Description | Auth header |
| --- | --- | --- |
| OAuth 2.1 | Interactive full OAuth flow, with token validation and user context enrichment. | `Authorization: Bearer <access_token>` |
| API token | Non-interactive machine-to-machine authentication using a personal API token or a service account API key. Requires admin enablement. | `Authorization: Basic <base64(email:api_token)>` or `Authorization: Bearer <api_key>` |

## Excerpt 3: Configuring authentication via API token
There are two options: a personal API token using Basic auth, or a service account API key using a Bearer token.

An admin creates a service account and generates an API key with the appropriate scopes. Store the key securely in your CI/CD system or secrets manager.

## Excerpt 4: Control Atlassian MCP server settings (support.atlassian.com)
By default, users connect AI tools to Atlassian MCP using OAuth 2.1.

Additionally, you can also allow tools to connect using an API token, which is useful for:

- Service‑style or non‑interactive tools that need consistent access without user prompts
- Backend systems or automations that call Atlassian MCP on behalf of a shared account

Tools that authenticate via API token do not use domain allowlists and are instead governed by your IP allowlist configuration and the scopes granted to their tokens or API keys.
