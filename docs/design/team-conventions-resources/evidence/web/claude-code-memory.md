# How Claude remembers your project - Claude Code Docs
URL: https://code.claude.com/docs/en/memory
Retrieved: 2026-10-26T16:04Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: What the page covers
- CLAUDE.md files: instructions you write to give Claude persistent context. Claude can also read a repository's `AGENTS.md` files in place of CLAUDE.md

## Excerpt 2: Where CLAUDE.md files live
CLAUDE.md files can live in several locations, each with a different scope. The table below lists them in load order, from broadest scope to most specific, so a project instruction appears in context after a user instruction.

| Scope | Location | Purpose | Use case examples | Shared with |
| --- | --- | --- | --- | --- |
| Managed policy | • macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md` • Linux and WSL: `/etc/claude-code/CLAUDE.md` • Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` | Organization-wide instructions managed by IT/DevOps | Company coding standards, security policies, compliance requirements | All users in organization |
| User instructions | `~/.claude/CLAUDE.md` | Personal preferences for all projects | Code styling preferences, personal tooling shortcuts | Only you (all projects) |
| Project instructions | `./CLAUDE.md` or `./.claude/CLAUDE.md`. See AGENTS.md for when `./AGENTS.md` loads instead of or alongside them | Team-shared instructions for the project | Project architecture, coding standards, common workflows | Team members via source control |
| Local instructions | `./CLAUDE.local.md` | Personal project-specific preferences; add to `.gitignore` | Your sandbox URLs, preferred test data | Only you (current project) |

## Excerpt 3: Size and path-scoped rules
- Size: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence. Move instructions that matter for only part of the codebase into path-scoped rules, which load only when Claude works with matching files. Imports help you organize a long file but don't reduce its context cost, because imported files load together with the CLAUDE.md that imports them.

## Excerpt 4: Imports
CLAUDE.md files can import additional files using `@path/to/import` syntax. Imported files are expanded and loaded into context alongside the CLAUDE.md that references them.

Both relative and absolute paths are allowed. Relative paths resolve relative to the file containing the import, not the working directory. Imported files can recursively import other files, with a maximum depth of four hops.

## Excerpt 5: Organize rules with .claude/rules/
For larger projects, you can organize instructions into multiple files using the `.claude/rules/` directory. This keeps instructions modular and easier for teams to maintain. Rules can also be scoped to specific file paths, so they only load into context when Claude works with matching files, reducing noise and saving context space.

> [!NOTE]
>
> Rules load into context every session or when matching files are opened. For task-specific instructions that don't need to be in context all the time, use skills instead, which only load when you invoke them or when Claude determines they're relevant to your prompt.

#### Set up rules

Place markdown files in your project's `.claude/rules/` directory. Each file should cover one topic, with a descriptive filename like `testing.md` or `api-design.md`. All `.md` files are discovered recursively, so you can organize rules into subdirectories like `frontend/` or `backend/`:

## Excerpt 6: Path-specific rules
#### Path-specific rules

Rules can be scoped to specific files using YAML frontmatter with the `paths` field. These conditional rules only apply when Claude is working with files matching the specified patterns.

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API Development Rules

- All API endpoints must include input validation
- Use the standard error response format
- Include OpenAPI documentation comments

```

Rules without a `paths` field are loaded unconditionally and apply to all files. A path-scoped rule loads when Claude uses the Read, Write, or Edit tool on a matching file. It also loads when Claude views a matching file with a Bash command that counts as a read, such as `cat` or `head` on a single file. Matching also works when Claude reaches a file through a symlinked path to the project directory, for example in a symlinked checkout.
