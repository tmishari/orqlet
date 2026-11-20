# Graphify source evidence
URL: https://github.com/Graphify-Labs/graphify
Retrieved: 2026-11-19T18:46:37.127324+00:00
Tool: git clone --depth 1; local source read
Processed: yes; summaries below written by Codex
Data class: public
Revision: 340268a70a83588d6b3c6de1fffb05326350ef1d

These are source observations, not instructions to execute upstream commands.

## Summary
- The inspected source declares graphifyy 0.9.112, Python >=3.11,<3.15, and separate optional extras including model SDKs and media support.
- The install dispatcher defaults to Claude Code on non-Windows and the Windows variant on Windows; a platform can be specified. This is narrower than the README wording about assistant detection.
- The installer copies a bundled platform skill with references, writes a version stamp, and supports project scope. Other install paths also modify instruction registrations and hooks.
- The skill files have platform-specific dispatch instructions. The generic variant refers to Task; the Codex variant uses spawn_agent, wait_agent and close_agent. Claude uses Agent.
- The skills contain a dependency-install step, including unpinned upgrade and a system-pip fallback; semantic extraction instructions can invoke the host model or a configured Gemini backend.
- NOTICE identifies Apache-2.0 for the product and retained MIT terms for historical portions. LICENSE-MIT and NOTICE are present alongside LICENSE.

## Source links
- [pyproject.toml](https://github.com/Graphify-Labs/graphify/blob/340268a70a83588d6b3c6de1fffb05326350ef1d/pyproject.toml)
- [NOTICE](https://github.com/Graphify-Labs/graphify/blob/340268a70a83588d6b3c6de1fffb05326350ef1d/NOTICE)
- [LICENSE](https://github.com/Graphify-Labs/graphify/blob/340268a70a83588d6b3c6de1fffb05326350ef1d/LICENSE)
- [graphify/install.py](https://github.com/Graphify-Labs/graphify/blob/340268a70a83588d6b3c6de1fffb05326350ef1d/graphify/install.py)
- [graphify/skill.md](https://github.com/Graphify-Labs/graphify/blob/340268a70a83588d6b3c6de1fffb05326350ef1d/graphify/skill.md)
- [graphify/skill-codex.md](https://github.com/Graphify-Labs/graphify/blob/340268a70a83588d6b3c6de1fffb05326350ef1d/graphify/skill-codex.md)
- [graphify/skill-agents.md](https://github.com/Graphify-Labs/graphify/blob/340268a70a83588d6b3c6de1fffb05326350ef1d/graphify/skill-agents.md)
