# Miro MCP Server: overview, FAQ, troubleshooting and admin guide
URL: https://developers.miro.com/docs/miro-mcp
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.
Also from: FAQ https://developers.miro.com/docs/miro-mcp-server-frequently-asked-questions
Also from: Troubleshooting https://developers.miro.com/docs/miro-mcp-server-faq-and-troubleshooting
Also from: Admin guide https://help.miro.com/hc/en-us/articles/31625761037202-Miro-MCP-Server-admin-guide

## Excerpt 1: Set up your agent (miro-mcp)
Codex and ChatGPT OpenAI’s coding agent: Add Miro from the ChatGPT plugin directory, then select Connect
Claude Code Anthropic’s agentic CLI: `claude plugin install miro@claude-plugins-official`
Cursor AI-first code editor: Install from the Cursor marketplace

## Excerpt 2: Security (miro-mcp)
- Uses OAuth 2.1 for auth: Secure authorization with dynamic client registration.
- Permissions: Respects all existing board permissions and access controls.

## Excerpt 3: One team at a time (FAQ)
Today the Miro MCP connection is 1:1 — each user is authenticated into one team at a time, even across multiple clients. If you authorize a different team (or a different client), the previous team's connection is superseded.

## Excerpt 4: Plugin or manual configuration (troubleshooting)
There are multiple ways to install the Miro MCP Server, and each creates an independent connection with its own OAuth session. If more than one is active in the same client, you'll see duplicate tools and authentication confusion.

| Plugin / extension (from miro-ai) | Everyone using Claude Code, Cursor, Gemini CLI, or Kiro | User (follows you across projects) |
| Manual JSON config (`"url": "https://mcp.miro.com/"`) | Clients without a Miro plugin (VSCode + Copilot, Windsurf, Lovable, etc.) | User or project |

The rule: use only one method per client. If your client has a Miro plugin or extension, use that — and do not also add manual MCP config. They both connect to the same server but maintain separate auth sessions.

## Excerpt 5: Admin guide (help.miro.com)
- Enable MCP for your organization, then use Access control to decide who can use it.
- You can keep access open to everyone, or limit it to selected teams and optionally user groups. Board‑level permissions still apply.
- All access is authenticated through OAuth 2.1.
- Users can only grant access to boards they have permission to view.
