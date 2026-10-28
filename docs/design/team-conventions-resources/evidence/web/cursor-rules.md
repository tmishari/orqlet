# Rules - Cursor Docs
URL: https://cursor.com/docs/context/rules
Retrieved: 2026-10-26T16:04Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Project rules
Project rules live in `.cursor/rules` as `.mdc` files and are version-controlled. They are scoped using path patterns, invoked manually, or included based on relevance.

Use project rules to:

- Encode domain-specific knowledge about your codebase
- Automate project-specific workflows or templates
- Standardize style or architecture decisions

## Excerpt 2: Rule anatomy
| Rule Type | Description |
| --- | --- |
| `Always Apply` | Apply to every chat session |
| `Apply Intelligently` | When Agent decides it's relevant based on description |
| `Apply to Specific Files` | When file matches a specified pattern |
| `Apply Manually` | When @-mentioned in chat (e.g., `@my-rule`) |

## Excerpt 3: Referencing files from a rule
Rule content reaches Agent as written. A file mention like `@migration-template.sql` tells Agent where to look, and Agent reads the file with its tools when it needs the content. The file's contents are not inlined into the prompt, and this is the same in the editor, the CLI, and Cloud Agents. Put anything that must always be in context directly in the rule body.

## Excerpt 4: Best practices
- Reference files instead of copying their contents. This keeps rules short and prevents them from becoming stale as code changes. Agent reads a referenced file when it needs it, so tell it what to look for there

## Excerpt 5: What to avoid in rules
- Copying entire style guides: Use a linter instead. Agent already knows common style conventions.
- Documenting every possible command: Agent knows common tools like npm, git, and pytest.

## Excerpt 6: Team rules
Team and Enterprise plans can create and enforce rules across their entire organization from the Cursor dashboard. Admins can configure whether or not each rule is required for team members.

## Excerpt 7: Nested AGENTS.md
Nested `AGENTS.md` support in subdirectories is now available. You can place `AGENTS.md` files in any subdirectory of your project, and they will be automatically applied when working with files in that directory or its children.
