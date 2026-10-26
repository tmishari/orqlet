# Extend Claude with skills - Claude Code Docs
URL: https://code.claude.com/docs/en/skills
Retrieved: 2026-10-26T16:04Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: What a skill is
Skills extend what Claude can do. Create a `SKILL.md` file with instructions, and Claude adds it to its toolkit. Claude uses skills when relevant, or you can invoke one directly with `/skill-name`.

## Excerpt 2: Commands merged into skills
> Custom commands have been merged into skills. A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way. Your existing `.claude/commands/` files keep working. Skills add optional features: a directory for supporting files, frontmatter to control whether you or Claude invokes them, and the ability for Claude to load them automatically when relevant.

## Excerpt 3: The SKILL.md file
Every skill needs a `SKILL.md` file with two parts: YAML frontmatter between `---` markers that tells Claude when to use the skill, and markdown content with the instructions Claude follows when the skill runs. The directory name, or the frontmatter `name` when you set one, becomes the command you type, and the `description` helps Claude decide when to load the skill automatically.

## Excerpt 4: Where skills live
| Location | Path | Loads in |
| --- | --- | --- |
| Enterprise | `.claude/skills/ /SKILL.md` in the managed settings directory | All users on machines where your organization deploys it |
| Personal | `~/.claude/skills/ /SKILL.md` | All your projects on this machine, but not Cowork or cloud sessions |
| Project | `.claude/skills/ /SKILL.md` | Sessions in this repository, but not cloud threads in a project. Commit it so your team gets it too |
| Nested | `/.claude/skills/ /SKILL.md` | Sessions started in or below ``, but not cloud threads in a project. Outside those threads, a session started above it loads the skill once Claude works on files there. See monorepos and subdirectories |
| Additional directory | `.claude/skills/ /SKILL.md` in a directory you pass with `--add-dir` | That session. See directories outside the project |
| Plugin | `/skills/ /SKILL.md` | Wherever the plugin is enabled, as `/plugin-name:skill-name` |

## Excerpt 5: Skills below the starting directory
Skills in a `.claude/skills/` directory below where you started don't load at startup. They load the first time Claude reads or edits a file in that subdirectory and stay available for the rest of the session. Until then they don't appear in the `/` menu and you can't invoke them by name. To load them sooner, run `/add-dir` with the subdirectory's path, which requires Claude Code v2.1.257 or later. For a worktree session that you start from the desktop app, see What worktrees share with the main checkout.

## Excerpt 6: Frontmatter reference: paths
### Frontmatter reference

Configure a skill with YAML frontmatter between `---` markers at the top of `SKILL.md`, and write the skill's instructions as Markdown after the closing `---`. Field names use lowercase words separated by hyphens, except `when_to_use`. A command file in `.claude/commands/` accepts the same fields except `name` and `paths`. This example sets four fields:

```yaml
...
| `paths` | No | Glob patterns that limit when this skill is activated. Accepts a comma-separated string or a YAML list. When set, Claude loads the skill automatically only when working with files matching the patterns. Patterns are relative to Claude's current working directory, and files outside that directory don't match. Uses the same glob format as path-specific rules. |
