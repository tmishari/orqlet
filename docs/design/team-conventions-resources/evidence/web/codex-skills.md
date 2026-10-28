# Build skills - Codex
URL: https://developers.openai.com/codex/skills
Retrieved: 2026-10-26T16:04Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Progressive disclosure
Skills use progressive disclosure to manage context efficiently. ChatGPT and Codex start with each skill’s name and description, then load the full `SKILL.md` instructions when they decide to use that skill.

## Excerpt 2: Skill structure
A skill is a directory with a `SKILL.md` file plus optional scripts and references. The `SKILL.md` file must include `name` and `description`.

## Excerpt 3: Where Codex loads local skills
Codex reads skills from repository, user, admin, and system locations. For repositories, Codex scans `.agents/skills` in every directory from your current working directory up to the repository root. If two skills share the same `name`, Codex doesn’t merge them; both can appear in skill selectors.

## Excerpt 4: Implicit invocation
Because implicit matching depends on `description`, write concise descriptions with clear scope and boundaries. Front-load the key use case and trigger words so a host can still match the skill if descriptions are shortened.

## Excerpt 5: Skill that depends on a docs MCP server
dependencies:
  tools:
    - type: "mcp"
      value: "openaiDeveloperDocs"
      description: "OpenAI Docs MCP server"
      transport: "streamable_http"
      url: "https://developers.openai.com/mcp"
