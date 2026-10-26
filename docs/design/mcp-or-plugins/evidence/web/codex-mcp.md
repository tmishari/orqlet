# Model Context Protocol - Codex (learn.chatgpt.com)
URL: https://learn.chatgpt.com/docs/extend/mcp.md?surface=cli
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Streamable HTTP servers
#### Streamable HTTP servers

- `url` (required): The server address.
- `auth` (optional): Authentication to try after configured bearer tokens and
authorization headers. Use `oauth` (the default) for stored MCP OAuth
credentials. Use `chatgpt` to use the current ChatGPT session for the trusted
first-party ChatGPT origin, with stored OAuth as a fallback.
- `bearer_token_env_var` (optional): Environment variable name for a bearer token to send in `Authorization`.
- `http_headers` (optional): Map of header names to static values.
- `env_http_headers` (optional): Map of header names to environment variable names (values pulled from the environment).
- `http_headers_helper` (optional): Local command that prints a JSON object of
header names and string values, such as `{"X-Auth": "temporary-token"}`.
Supported for HTTP MCP connections made from the local environment; not for
stdio servers or connections made through a remote execution environment.

Codex caches helper headers for the connection. After a same-origin POST
returns `401` or `403`, it refreshes the headers once and retries only if the
helper returns changed values. Explicit bearer tokens and OAuth credentials
take precedence over a helper-provided `Authorization` header.
An OAuth `403` response that reports insufficient scope doesn't trigger a
helper refresh.

If no credential source resolves, Codex can connect to the server without
authentication. Run `codex mcp login ` separately to start an MCP
OAuth login.

## Excerpt 2: OAuth client registration and callbacks
#### OAuth client registration and callbacks

When your authorization server requires a pre-registered OAuth client, provide
its client ID when adding the MCP server:

```bash
codex mcp add example --url https://mcp.example.com --oauth-client-id my-client

```

For a confidential client, also pass `--oauth-client-secret`. Read the secret
from an environment variable:

```bash
codex mcp add example --url https://mcp.example.com --oauth-client-id my-client --oauth-client-secret "$MCP_CLIENT_SECRET"

```
