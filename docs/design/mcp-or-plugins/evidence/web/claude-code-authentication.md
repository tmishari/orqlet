# Authentication - Claude Code Docs
URL: https://code.claude.com/docs/en/authentication
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Credential management
Credential management

Claude Code securely manages your authentication credentials:

- Storage location:

- On macOS, credentials are stored in the encrypted macOS Keychain. When the Keychain rejects the write, such as when it’s locked in an SSH session, Claude Code stores your login in `~/.claude/.credentials.json` with file mode `0600` instead, the same storage it uses on Linux. A Console login that creates an API key fails until the Keychain is writable. To move your login back into the Keychain, follow the recovery steps.
- On Linux, credentials are stored in `~/.claude/.credentials.json` with file mode `0600`.
- On Windows, credentials are stored in `%USERPROFILE%\.claude\.credentials.json` and inherit the access controls of your user profile directory, which restricts the file to your user account by default.
- If you’ve set the `CLAUDE_CONFIG_DIR` environment variable, Claude Code keeps the `.credentials.json` file under that directory instead, including the file the macOS fallback writes, and keys the macOS Keychain entry to that directory too, so a session with a different `CLAUDE_CONFIG_DIR` reads a different entry.
