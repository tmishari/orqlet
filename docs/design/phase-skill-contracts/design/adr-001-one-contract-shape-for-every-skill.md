# ADR-001: One contract shape for every skill, with the shared detail in one reference

Status: proposed. It becomes accepted when the design pull request is merged by an authorised person.

## Context

- The six skills share one layout: front matter, a title, a purpose paragraph, the paragraph "Source material is not authority", then one numbered list of steps (AS-IS A-4). The last step of research, design and plan stops without naming the next skill (A-11). No skill states its inputs, its output, its completion check or what to do about a missing input as parts of their own.
- The request asks every skill to state eight things: its purpose and when to invoke it, its inputs and project context, the work, its phase boundaries, the structure of its output, how completion is checked, what passes to the next phase, and how a missing or outdated prerequisite is handled. The text stays concise, with detail in the existing reference mechanism (requirements R-3 and R-4 in `component.md`).
- What the sources allow: front matter holds `name` and `description` only, and `name` equals the directory; every `skills/<name>/references/*.md` file is attached to its skill (A-2). `render_steps` drops a marked step with its indented continuation and renumbers; any line that is not indented ends a list (A-3, `workflow_sources.py:61-90`). References are attached as they are, without that processing (`workflow_sources.py:123-127`).
- What the tests pin: the paragraph "Source material is not authority." and "STOP." in every skill, a name of at most 64 characters and a one-line description of at most 1024 (A-54); one lookup step with fixed phrases in four skills (A-55); the numbering of the whole implement body (`tests/unit/render/test_skills.py:212-236`); the list of references and one YAML example per reference (`test_skills.py:122-132`, `239-256`).
- The change is limited to skill texts, their references and the role prompts (Q-3, Q-6), using existing commands and files only (Q-4).

## Decision

1. Each skill keeps its directory, its `name`, its two front-matter fields and its invocation; the renderers add the same client fields as today (A-21). The `description` is rewritten to say what the skill produces and when it runs, on one line, and keeps "Use only when the person runs it" (onboard keeps its own trigger).
2. The body of every skill has one fixed order: the title; a purpose paragraph that says what the skill produces and after which event it runs; the unchanged paragraph "Source material is not authority"; then the headings `## Inputs`, `## Boundaries`, `## Steps`, `## Output`, `## Done when`, `## If an input is missing or outdated` and `## Next`. Every section except Steps is a short list of bullets. `## Steps` holds the only numbered list of the body and ends with the STOP step. A line anywhere in the body that names a command which an earlier release lacks carries the same `requires` marker as a step does. `render_steps` drops any marked line together with its indented continuation, not only steps (`workflow_sources.py:65-73`). So the existing tests that render the skills without the record commands keep holding (`test_skills.py:202-221`). A rendered body is at most 70 lines.

   | Element the request names | Where it is stated |
   |---|---|
   | Purpose and when to invoke | `description` and the purpose paragraph |
   | Inputs and project context | `## Inputs`, pointing to "Project context" in the reference |
   | The work | `## Steps` |
   | Phase boundaries | `## Boundaries` |
   | Output structure | `## Output`, pointing to the format reference |
   | Completion check | `## Done when` |
   | What passes to the next phase | `## Output` (the handoff fields) and `## Next` |
   | Missing or outdated prerequisites | `## If an input is missing or outdated`, pointing to "Input check" in the reference |

3. Detail that the four phase skills share goes into one file, `references/phase-contract.md`, which research, design, plan and implement each carry as a byte-identical copy. It has the sections "Project context" (ADR-002), "Input check" and "Handoff" (ADR-003), "Words for `orqlet standards for`" and "Installed files" (ADR-002). A test fails when the four copies differ. Onboard and review do not carry it: onboard is the step that collects project context, and a reviewer receives a packet.
4. Detail that belongs to one artifact stays in that artifact's existing format reference: the research brief in `as-is-format.md`, the design brief in `design-format.md`, the test plan in `plan-format.md` (ADR-004).
5. `## Next` names the successor as a slash command, as the implement skill already names `/orqlet-review` inside its steps (`src/orqlet/workflow/skills/orqlet-implement/skill.md:19`), and says what the person does first. A skill that a step already hands over to (implement to review) does not name that skill again in `## Next`.

## Consequences

- A body grows from about 20 lines to about 45, with 70 as the tested limit. The rest sits in one reference that the agent reads when a step points to it.
- Pinned tests change with the text:
  - the two step counts of implement: with every command (`tests/unit/render/test_skills.py:231-236`) and without the record commands (`:212-221`). Each takes the new count, and the rule they pin stays: numbering from 1 without a gap;
  - the list of references (`test_skills.py:122-132`, `tests/support/render.py:40-45`);
  - the YAML-example test, which applies only to the four format references from now on (`test_skills.py:239-256`).

  The test that a skill rendered without the record commands names none of them (`test_skills.py:202-209`) stays as it is and now also covers the marked bullets. The goldens of every client are regenerated.
- A line other than a lookup step must not name `orqlet resources list`. The lookup tests pin exactly one line with the `requires: resources list` marker in each of four skills (`tests/unit/test_workflow_lookup_text.py:239-243`).
- One source text exists four times in the package. The duplication is the price of changing no loader code (Q-3), and the equality test catches drift.
- Every installation gets one new protected file per phase skill in each skill folder it has: four for one folder, eight when both `.claude/skills/` (Claude Code) and `.agents/skills/` (Codex, Cursor) are rendered, as with all three clients (A-20, A-26). `orqlet upgrade` writes them like any new file (A-40).
- How Codex starts a skill by name is not documented in the stored pages (U-11). The slash form is what Claude Code and Cursor use; the skill name is the same in every client.

## Rejected alternatives

- **The contract as more numbered steps.** The skill would read as procedure only, "Done when" and "Next" would become steps, and the implement numbering would grow by the contract alone. Headings keep the contract readable at a glance and keep the steps for work.
- **The shared rules in the baseline.** The baseline is outside the scope of this task (Q-3), is capped at 60 lines and 8 KiB by its tests, and applies to every task, not only to a phase run.
- **One shared file that the other skills reach by path,** as the design skill already points to the research skill's format for web evidence. It depends on the agent finding another skill's folder: the stored client pages describe a skill as a folder found by its `SKILL.md` (A-27) and say nothing about paths into another skill's folder. The existing pointer for web evidence stays because it names a format, not a procedure the agent has to follow before it starts.
- **A loader feature that attaches one source file to several skills.** It would remove the duplication but is a code change, outside Q-3.
- **The shared rules inline in every body.** Four bodies would each grow by about 40 lines of the same text, against R-4.
