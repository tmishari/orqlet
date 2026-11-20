# Installed client versions on the development machine

Retrieved: 2026-11-20T11:44:00+02:00
Tool: local read-only shell commands, authorised by the person (questions.yaml Q-17); not a web page
Processed: no
Data class: public (version numbers only; no paths beyond the home-relative executable locations, no account data)

1. Claude Code - `claude --version` through `~/.local/bin/claude` printed "2.1.303 (Claude Code)".
2. Cursor CLI - `cursor --version` printed "3.31.11".
3. Codex CLI - `codex` is not on PATH.
4. VS Code - `code --version` printed "1.145.0".
5. VS Code extensions - `code --list-extensions --show-versions` lists 24 extensions; none matches `copilot`, `openai` or `chatgpt`.
6. uv - `uv --version` printed "uv 0.7.19".
7. pipx - `pipx --version` printed "1.18.16".
8. Graphify - an executable `graphify` is on PATH at `~/.local/bin/graphify`; its version was not read.

Not established: whether VS Code 1.145.0 provides Copilot Chat without a listed extension, whether the Cursor CLI version equals the Cursor desktop version, and whether a Codex IDE extension exists in another editor. No home configuration was read.
