# Claude Code issues #62442 and #89969 (user reports, not vendor documentation)
URL: https://github.com/anthropics/claude-code/issues/62442
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.
Also from: Issue 89969 https://github.com/anthropics/claude-code/issues/89969

## Excerpt 1: Issue 62442: sensitive userConfig not persisted
When a plugin declares `userConfig` with `sensitive: true` and the user enters the value via `/plugin → Installed → → Configure options → Save`, the value is **silently not persisted anywhere**:

The value works for the current session only (in-memory env substitution into the MCP server spawn succeeds), then is lost on Claude Code restart. The user must re-enter the API key on every cold start.

## Excerpt 2: Issue 89969: placeholders in the oauth block
A plugin bundling a remote HTTP MCP server can make its endpoint per-installation configurable with `userConfig` + `${user_config.KEY}` — that works, including `default` values. But the same placeholder inside the server's `oauth` block is **not substituted**: the OAuth authorize request is sent with the literal placeholder as `client_id`.
