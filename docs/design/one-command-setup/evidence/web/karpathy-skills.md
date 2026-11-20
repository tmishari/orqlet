# andrej-karpathy-skills source evidence

URL: https://github.com/multica-ai/andrej-karpathy-skills
Revision: 2c606141936f1eeef17fa3043a72095b4765b9c2 (commit date 2026-04-20T10:05:04Z; equal to the head of main on the retrieval date)
Retrieved: 2026-11-20T11:55:00+02:00
Tool: gh api (commit, tree, repository metadata) and curl of raw.githubusercontent.com at the revision
Processed: no
Data class: public

Excerpts are verbatim, shortened with "..." only. Nothing was executed or installed.

## Provenance and licence

1. Tree - the revision tracks `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `.cursor/rules/karpathy-guidelines.mdc`, `CLAUDE.md`, `CURSOR.md`, `EXAMPLES.md`, `README.md`, `README.zh.md` and `skills/karpathy-guidelines/SKILL.md`; no LICENSE or NOTICE file.
2. Repository metadata - `gh api repos/multica-ai/andrej-karpathy-skills` returns `"license":null`, `"fork":false`.
3. Declared licence - README.md line 171 "MIT"; SKILL.md front matter "license: MIT"; plugin.json "\"license\": \"MIT\"". No copyright holder is named in any tracked file.
4. Identity - plugin.json and marketplace.json name author and owner "forrestchang"; README install lines use "forrestchang/andrej-karpathy-skills". `gh api repos/forrestchang/andrej-karpathy-skills` returns `"full_name":"multica-ai/andrej-karpathy-skills"`, and https://github.com/forrestchang/andrej-karpathy-skills answers HTTP 301 to the multica-ai address.
5. Origin claim - README: "derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls."

## File hashes (SHA-256 of the bytes at the revision)

- README.md daf314efb31894b86d68b67786c820bd8470bb2126e578ba9cd0e3e2667883f8
- CLAUDE.md 694a2d721e41c385f3db492838c23299826df5ba9809e3b0721aac70021e196a
- skills/karpathy-guidelines/SKILL.md 6e22cc54cb02a5e98ae42d06d9d7292db0c1b43894831b32879beb0166b2aea7
- CURSOR.md ef0850c959524000801ce8ea6b8393b00196cb502ff407fb4a449b45e15ae937
- .cursor/rules/karpathy-guidelines.mdc 259cf32ac1a493b7bf863992bbb968079a2b6ffdce99dad092ec6f4e2764717d
- .claude-plugin/plugin.json 52919436493fc5403e3022c45dff0d6a82f0047c02b17797e2bad14b3ec22ce9
- .claude-plugin/marketplace.json 9e5d3a1e84c7a49eff1be18b698018c58fdef3bf6f6c94729c663f7577ca3032
- EXAMPLES.md 9bc0ba934077a0514bab0fc7a4ffad37ecd40bfddf57f29d0b8cef5e5b3d1f28

## Guidance (skills/karpathy-guidelines/SKILL.md)

6. Tradeoff - "These guidelines bias toward caution over speed. For trivial tasks, use judgment."
7. Think before coding - "State your assumptions explicitly. If uncertain, ask." / "If multiple interpretations exist, present them - don't pick silently." / "If a simpler approach exists, say so. Push back when warranted."
8. Simplicity first - "No features beyond what was asked." / "No abstractions for single-use code." / "No \"flexibility\" or \"configurability\" that wasn't requested." / "No error handling for impossible scenarios."
9. Surgical changes - "Don't \"improve\" adjacent code, comments, or formatting." / "Match existing style, even if you'd do it differently." / "If you notice unrelated dead code, mention it - don't delete it." / "Remove imports/variables/functions that YOUR changes made unused." / "Every changed line should trace directly to the user's request."
10. Goal-driven execution - "\"Fix the bug\" → \"Write a test that reproduces it, then make it pass\"" / "For multi-step tasks, state a brief plan" with "[Step] → verify: [check]".
11. Front matter - the skill declares `name`, `description` and `license`.
12. README tradeoff note - "For trivial tasks (simple typo fixes, obvious one-liners), use judgment — not every change needs the full rigor."

## Delivery and client claims

13. Cursor rule - `.cursor/rules/karpathy-guidelines.mdc` front matter: "alwaysApply: true".
14. Claude Code - README: "/plugin marketplace add forrestchang/andrej-karpathy-skills" then "/plugin install andrej-karpathy-skills@karpathy-skills"; plugin.json "\"skills\": [\"./skills/karpathy-guidelines\"]".
15. Unpinned fetch - README Option B: "curl -o CLAUDE.md https://raw.githubusercontent.com/forrestchang/andrej-karpathy-skills/main/CLAUDE.md".
16. Cursor claim - CURSOR.md: "Cursor does not read `.claude-plugin/` or `CLAUDE.md` by default."
17. Sync rule - CURSOR.md: "When you change the four principles, keep **[`CLAUDE.md`](CLAUDE.md)** and **[`.cursor/rules/karpathy-guidelines.mdc`](...)** in sync."
18. EXAMPLES.md - sections "1. Think Before Coding" to "4. Goal-Driven Execution", then "Anti-Patterns Summary" and "Key Insight"; illustrative only.

## Decision recorded by the person

19. Q-27: do not vendor the text; Orqlet writes its own wording of any genuinely new point, with an attribution link.
