# Package your plugin - OpenAI Developers
URL: https://developers.openai.com/plugins/build/plugins
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Introduction
UI and authentication remain part of the MCP server integration you built in
the preceding steps; the plugin manifest connects that integration to the rest
of the package.

## Excerpt 2: Plugin structure
### Plugin structure

A portable plugin has a `plugin.json` manifest at its root. It can also include
a `skills/` directory, an `mcp.json` file for bundled MCP servers, and assets.
Put OpenAI-specific settings in the root manifest's `extensions.com.openai`
object. A separate `.codex-plugin/plugin.json` is optional and serves as a
compatibility fallback when that object is absent.

Keep `plugin.json`, `mcp.json`, `skills/`, and `assets/` at the plugin root.
When you add a Codex overlay, keep only its `plugin.json` inside
`.codex-plugin/`; referenced hooks, `.app.json`, and other resources stay at
the plugin root.

The portable manifest identifies the plugin. Fixed package paths identify its

## Excerpt 3: Enable or disable a plugin for a repo
### Enable or disable a plugin for a repo

The repo marketplace at `.agents/plugins/marketplace.json` makes plugins
discoverable. Use the repo's `.codex/config.toml` to control whether a
local-marketplace plugin is enabled for that project:

```toml
[plugins."my-plugin@local-repo"]
enabled = true

```

The quoted key uses `plugin-name@marketplace-name`: `my-plugin` is the plugin
entry's name, and `local-repo` is the marketplace's top-level `name`. Set
`enabled = false` to disable the plugin for the project without uninstalling it.
During marketplace refresh, Codex can install or refresh files for configured
plugins, even when `enabled = false`. Connected services still require
authentication.

Codex loads project `.codex/config.toml` only for trusted projects. Project
settings override user, cloud-managed, and system defaults, subject to enforced
requirements. See Configuration precedence.

These settings apply to local-marketplace plugins in supported local clients,

## Excerpt 4: How local marketplaces work
### How local marketplaces work

A plugin marketplace is a JSON catalog of plugins. These local sources are
separate from the universal public directory and support authoring, testing,
and private distribution.

The ChatGPT desktop app can read marketplace files from:

- a repo marketplace at `$REPO_ROOT/.agents/plugins/marketplace.json`
- a legacy-compatible marketplace at `$REPO_ROOT/.claude-plugin/marketplace.json`
- a personal marketplace at `~/.agents/plugins/marketplace.json`

You can install any plugin exposed through a marketplace. ChatGPT installs
plugins into
`~/.codex/plugins/cache/$MARKETPLACE_NAME/$PLUGIN_NAME/$VERSION/`. For local
plugins, `$VERSION` is `local`, and ChatGPT loads the installed copy from that
cache path rather than directly from the marketplace entry.

You can enable or disable each local-marketplace plugin individually. The
plugin browser saves user-level choices in `~/.codex/config.toml`; repo,
cloud-managed, and system configuration can also supply plugin settings. See
Enable or disable a plugin for a repo
and Configure plugin marketplaces and defaults.
