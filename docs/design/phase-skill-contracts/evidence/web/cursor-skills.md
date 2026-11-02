# Agent Skills (Cursor documentation)

URL: https://cursor.com/docs/context/skills
Retrieved: 2026-11-02T10:05:00+02:00
Tool: Cursor WebFetch (returns the page converted to Markdown)
Processed: unknown
Data class: public

1. Skill directories - "Skills are automatically loaded from these locations:" | `.agents/skills/` | Project-level | `.cursor/skills/` | Project-level | `~/.agents/skills/` | User-level (global) on the local machine | `~/.cursor/skills/` | User-level (global) on the local machine |
2. Compatibility directories - "For compatibility, Cursor also loads skills from Claude and Codex directories: `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, and `~/.codex/skills/`."
3. Field name - "`name` | Yes | Skill identifier. Lowercase letters, numbers, and hyphens only. Must match the parent folder name."
4. Field description - "`description` | Yes | Describes what the skill does and when to use it. Used by the agent to determine relevance."
5. Field disable-model-invocation - "`disable-model-invocation` | No | When `true`, the skill is only included when explicitly invoked via `/skill-name`. The agent will not automatically apply it based on context."
6. Field paths - "`paths` | No | Glob patterns that scope the skill to matching files. Accepts a comma-separated string or a list. When set, the skill is only surfaced when the agent works with files that match."
7. Manual invocation - "Skills can also be manually invoked by typing `/` in Agent chat and searching for the skill name. A skill invoked this way attaches to one message."
8. Optional references directory - "`references/` | Additional documentation loaded on demand"
9. Progressive loading - "Keep your main `SKILL.md` focused and move detailed reference material to separate files. This keeps context usage efficient since agents load resources progressively—only when needed."
10. Unreadable skill - "In Cloud Agents, a skill whose `SKILL.md` can't be read, has frontmatter that doesn't parse, or has no `description` shows a warning in the run that names the skill."
11. Nested project skills - "Cursor also discovers skills inside nested project subdirectories. A `.cursor/skills/` (or `.agents/skills/`) folder anywhere inside your repository is picked up, so monorepos can colocate skills with the package they apply to"
12. Summary, not verbatim - The page does not say which Cursor version it describes; it mentions "a built-in `/migrate-to-skills` skill in 2.4". It states no length limit for `name` or `description`.
