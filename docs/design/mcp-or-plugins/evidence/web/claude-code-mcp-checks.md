# Connect Claude Code to tools via MCP - Claude Code Docs (approval, precedence, same-name warning, OAuth scopes)
URL: https://code.claude.com/docs/en/mcp.md
Retrieved: 2026-10-29T08:18Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are the text as the tool converted the page, with no change by hand; the conversion dropped text in angle brackets, such as the name placeholder after `claude mcp get`. The label of each excerpt says where it sits on the page.
Used by: docs/design/mcp-or-plugins/evidence/checks/V-1, V-4, V-10 (vendor statements that stand beside the observations; the client version of the observations is 2.1.303).

## Excerpt 1: Server status: statuses that do not connect

`claude mcp add` confirms a successful add by printing an `Added ...` line, which means the configuration was written. If the command prints a `was not saved` message instead, see MCP server was not saved or removed; for a `may not have been saved` message, see MCP server may not have been saved or removed.

`claude mcp list` shows a health status next to each server it lists, such as `✔ Connected`, `! Needs authentication`, or `✘ Failed to connect`. A failure status means Claude Code couldn't connect to that server, not that the list command failed.

The statuses in this list report a configuration decision rather than a connection attempt, so Claude Code prints them without connecting to the server:

- `⏸ Pending approval (run `claude` to approve)`: a project-scoped server from `.mcp.json` that you haven't approved yet. Claude Code shows it in both `claude mcp list` and `claude mcp get `. Run `claude` interactively to review and approve it.
- `✘ Rejected (see disabledMcpjsonServers in settings)`: a `.mcp.json` server that a `disabledMcpjsonServers` entry rejects. Claude Code shows it only in `claude mcp get `.
- `⊘ Disabled for this project (re-enable via /mcp)`: a server that the project's `disabledMcpServers` list names. Claude Code shows it in both `claude mcp list` and `claude mcp get `. Turn the server back on from the `/mcp` panel.
- `✘ Blocked by enterprise managed policy`: a server that one of your organization's policies refuses. Claude Code shows it in both `claude mcp list` and `claude mcp get `. A server blocked by an allowlist, a denylist, or another restriction in managed MCP configuration is hidden from both commands rather than shown with this status. Ask your administrator which policy blocks the server.

## Excerpt 2: Project server approvals and workspace trust

#### Project server approvals and workspace trust

`claude mcp list` and `claude mcp get` read `.mcp.json` approvals only from settings files that aren't checked into the repository until you trust the workspace by running `claude` in it and accepting the workspace trust dialog. A cloned repository can't approve its own servers: `enableAllProjectMcpServers` or `enabledMcpjsonServers` committed to the project's `.claude/settings.json` is ignored in an untrusted folder, and the server stays at `⏸ Pending approval` instead of being connected and health-checked.

Approvals from these sources still apply in an untrusted folder:

- your user `~/.claude/settings.json`
- managed settings
- settings passed with `--settings`

Claude Code also applies approvals from an untracked `.claude/settings.local.json`, but it runs git to check whether the file is tracked, and it runs that check only in a trusted folder. In a folder you've never trusted, Claude Code waits for the trust dialog before applying the file's approvals, unless the folder is your own configuration home: your home directory, or a directory whose `.claude` you've set as `CLAUDE_CONFIG_DIR`. Before v2.1.207, Claude Code applied approvals from an untracked `.claude/settings.local.json` even in a folder you'd never trusted.

## Excerpt 3: Configuration warnings: same name in more than one scope

- Same name in more than one scope: if you define the same server name in more than one scope with different endpoints, Claude Code warns about the conflict in `claude mcp list` output and in `/mcp`. Claude Code stores OAuth sign-ins per endpoint, so when you authenticate the definition that loads in one project, you still need to sign in separately in a project where a different definition loads. Keep the endpoint you want and remove the others with `claude mcp remove --scope `. In the warning, Claude Code quotes each scope's endpoint as written in your configuration, with `${VAR}` references unexpanded, so it never shows a resolved value such as an API key.

## Excerpt 4: Project scope: the approval prompt and the runs that cannot show it

For security reasons, Claude Code prompts for approval in interactive sessions before using project-scoped servers from `.mcp.json` files. To reset those approval choices, run `claude mcp reset-project-choices`.

In `claude -p` runs, Agent SDK sessions, and cloud sessions outside a project's threads, Claude Code can't show that prompt: it loads project-scoped servers without asking. Claude Code also skips the prompt in a session you start in `bypassPermissions` mode with `skipDangerousModePermissionPrompt` set in your user settings or in managed settings. To keep a server out anyway:

- Add it to `disabledMcpjsonServers`, which blocks it in every permission mode.
- Exclude project settings entirely with `--setting-sources` or the SDK's `settingSources` option.
- Start the session with `--strict-mcp-config`. Claude Code then uses only the MCP servers you pass with `--mcp-config`. Skipping the approval prompt for the project-scoped servers Claude Code isn't loading requires Claude Code v2.1.246 or later; before v2.1.246, a strict session still waited on approval for them, which left background sessions waiting at startup. See Exclusive control with managed-mcp.json for what the flag does under a managed MCP file.

Project server approvals and workspace trust covers how approvals committed to the repository interact with workspace trust.

## Excerpt 5: Scope hierarchy and precedence

When the same server is defined in more than one place, Claude Code connects to it once, using the definition from the highest-precedence source. The entire server entry from that source is used; fields are not merged across scopes.

1. Local scope
2. Project scope
3. User scope
4. Plugin-provided servers
5. claude.ai connectors

Claude Code matches duplicates across the three scopes by name. It matches plugins and connectors by endpoint, so one that points at the same URL or command as an enabled server above counts as a duplicate.

Two URL spellings count as the same endpoint when they differ only in the letter case of the scheme or host, the scheme's default port, such as `:443` on `https`, or a trailing slash. A different path, query string, userinfo, or non-default port makes two servers.

A server your organization provides through the `managedMcpServers` managed setting ranks above all of these, so when one of them duplicates it, Claude Code connects the organization's definition. Requires Claude Code v2.1.259 or later.

## Excerpt 6: Restrict OAuth scopes

### Restrict OAuth scopes

Set `oauth.scopes` to pin the scopes Claude Code requests during the authorization flow. This is the supported way to restrict an MCP server to a security-team-approved subset when the upstream authorization server advertises more scopes than you want to grant. The value is a single space-separated string, matching the `scope` parameter format in RFC 6749 §3.3.

```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://mcp.slack.com/mcp",
      "oauth": {
        "scopes": "channels:read chat:write search:read"
      }
    }
  }
}

```

`oauth.scopes` takes precedence over both `authServerMetadataUrl` and the scopes the server discovers at `/.well-known`. Leave it unset to let the MCP server determine the requested scope set.

When `oauth.scopes` isn't set, Claude Code doesn't request the full `scopes_supported` catalog from automatically discovered authorization server metadata. Metadata fetched from a configured `authServerMetadataUrl` still supplies its `scopes_supported` as the requested scopes.

If the authorization server advertises `offline_access` in `scopes_supported`, Claude Code appends it to the pinned scopes so the access token can be refreshed without a new browser sign-in.
