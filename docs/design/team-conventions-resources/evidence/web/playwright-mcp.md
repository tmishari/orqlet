# Playwright MCP server - README
URL: https://raw.githubusercontent.com/microsoft/playwright-mcp/main/README.md
Retrieved: 2026-10-26T16:43Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: User profile modes
### User profile

You can run Playwright MCP with persistent profile like a regular browser (default), in isolated contexts for testing sessions, or connect to your existing browser using the browser extension.

**Persistent profile**

All the logged in information will be stored in the persistent profile, you can delete it between sessions if you'd like to clear the offline state.
Persistent profile is located at the following locations and you can override it with the `--user-data-dir` argument.

## Excerpt 2: Isolated mode and storage state
In the isolated mode, each session is started in the isolated profile. Every time you ask MCP to close the browser,
the session is closed and all the storage state for this session is lost. You can provide initial storage state
to the browser via the config's `contextOptions` or via the `--storage-state` argument. Learn more about the storage
state [here](https://playwright.dev/docs/auth).

## Excerpt 3: Browser extension
**Browser Extension**

The Playwright MCP Chrome Extension allows you to connect to existing browser tabs and leverage your logged-in sessions and browser state. See [microsoft/playwright › packages/extension](https://github.com/microsoft/playwright/tree/main/packages/extension#readme) for installation and setup instructions.

## Excerpt 4: Options
| --extension | Connect to a running browser instance (Edge/Chrome only). Requires the "Playwright Extension" to be installed. *env* `PLAYWRIGHT_MCP_EXTENSION` |
| --isolated | keep the browser profile in memory, do not save it to disk. *env* `PLAYWRIGHT_MCP_ISOLATED` |
| --storage-state | path to the storage state file for isolated sessions. *env* `PLAYWRIGHT_MCP_STORAGE_STATE` |
| --user-data-dir | path to the user data directory. If not specified, a temporary directory will be created. *env* `PLAYWRIGHT_MCP_USER_DATA_DIR` |
