# Global setup documentation

Retrieved: 2026-11-20T08:02:13.177440+00:00
Tool: web.run; local repository source reads
Processed: yes; all observations below are summaries
Data class: public
Version scope: current official pages, retrieved 2026-11-20; native-client behaviour was not exercised.

## uv

URL: https://docs.astral.sh/uv/concepts/tools/
URL: https://docs.astral.sh/uv/reference/cli/

- uv tool install creates a persistent, isolated tool environment and makes its executable available user-wide through the executable directory on PATH.
- Dependency executables are not exposed by default. Installing Orqlet does not by itself establish a separately callable Graphify executable.
- The documentation describes installing console entry points. It does not establish an Orqlet-controlled post-install banner or a project-configuration hook. The proposed banner belongs to explicit Orqlet startup.

## Cursor

URL: https://cursor.com/docs/skills
URL: https://cursor.com/docs/subagents.md
URL: https://cursor.com/docs/rules
URL: https://cursor.com/docs/plugins.md

- The skill directory table includes user-global ~/.agents/skills and ~/.cursor/skills.
- The subagent scope table includes ~/.cursor/agents and compatibility locations in ~/.claude/agents and ~/.codex/agents.
- User Rules are configured in Customize / Rules. The skills page states that User Rules are not stored on the filesystem.
- Plugins can contain rules and be installed at user scope through Customize. The inspected pages do not establish an unattended supported installation command for global User Rules.
- The person accepted one guided Cursor rules setup step (questions.yaml Q-9). That is a requirement choice, not proof that a native client step was completed.

## Codex

URL: https://learn.chatgpt.com/docs/agent-configuration/agents-md.md
URL: https://learn.chatgpt.com/docs/build-skills.md
URL: https://learn.chatgpt.com/docs/agent-configuration/subagents.md

- The person approved following the official redirect from developers.openai.com to learn.chatgpt.com (Q-8) before these destination pages were used as evidence.
- User-global guidance is read from the Codex home, normally ~/.codex, with CODEX_HOME supported. AGENTS.override.md can take precedence over AGENTS.md.
- The local skill table includes $HOME/.agents/skills. Same-named skills are not merged and both can appear in selectors.
- Personal custom agents use ~/.codex/agents; project agents use .codex/agents.

## Claude Code

URL: https://code.claude.com/docs/en/memory.md
URL: https://code.claude.com/docs/en/sub-agents.md
Stored skill reference: docs/design/team-conventions-resources/evidence/web/claude-code-skills.md

- User instructions live at ~/.claude/CLAUDE.md; personal rules live under ~/.claude/rules and apply across projects.
- User subagents live at ~/.claude/agents; project subagents have higher priority than user subagents.
- The stored official skill documentation records ~/.claude/skills for personal skills. Its retrieval predates this scope extension; global skill discovery still requires native-client qualification.

## Repository observations

The main checkout advanced to 9b2f9dd after the original research. This design branch now starts from that main baseline and carries only this task's documentation commits.

- src/orqlet/application/ports/personal.py and adapters/scan/personal_names.py describe opt-in, names-only inspection of personal skill and agent locations, not a global configuration writer.
- interface/cli/commands/lifecycle.py creates that lister only for --check-personal-names.
- interface/cli/app.py has explicitly named subcommands and no dot setup command at the inspected baseline.
- interface/cli/render_human.py describes plain-text output; runner.py keeps human output separate from its JSON envelope.

No home configuration, installer, client setting, or credential store was read or changed during this inspection.
