# Manage Claude Code plugins for your organization - Claude Code Docs
URL: https://code.claude.com/docs/en/plugins/org
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.
Also from: Install and manage plugins - Claude Code Docs https://code.claude.com/docs/en/plugins/install

## Excerpt 1: Require plugins per repository
Require plugins per repository

To cover one repository’s contributors instead of your whole fleet, set `extraKnownMarketplaces` and `enabledPlugins` in that repository’s `.claude/settings.json`. The `extraKnownMarketplaces` entries apply only in a folder the contributor has trusted, and in an untrusted folder Claude Code ignores them without a message:

- Interactive sessions: Claude Code registers the marketplace only after the contributor accepts the workspace trust dialog for that folder.

## Excerpt 2: External-source plugins need a per-contributor install
A plugin that the marketplace lists by a relative path loads from the marketplace copy once the repository’s `extraKnownMarketplaces` entries apply. A plugin whose marketplace entry points at an external source instead, such as the plugin’s own GitHub repository, doesn’t install from the repository’s settings alone. Each contributor sees `Plugin " " is enabled in project settings but isn't installed` until they run `claude plugin install @ --scope project`, as Install plugins describes. If you use a local `directory` or `file` source with a relative path, the path resolves against your repository’s main checkout. When you run Claude Code from a git worktree, the path still points at the main checkout, so all worktrees share the same marketplace location. To roll out a bundle of plugins with dependencies, put the bundle plugin in `enabledPlugins`, as Plugin dependencies describes.

## Excerpt 3: Install scope (Install and manage plugins)
Choose an install scope says which settings file each one writes to and which applies when the same plugin is set at more than one. After you select a scope, Claude Code installs the plugin along with any dependencies it declares, then prints an install summary.

4

Read the install summary

The last sentence of the summary tells you whether the plugin is usable in this session yet:

## Excerpt 4: Cloud sessions (Install and manage plugins)
A cloud session, including the browser at claude.ai/code, has no plugin browser and doesn’t load the plugins you installed on your own machine or the ones your repository’s `.claude/settings.json` turns on. For plugins your organization distributes through managed settings, see Manage plugins for your organization. See which parts of your setup are also available in a cloud session for the rest of your setup.
