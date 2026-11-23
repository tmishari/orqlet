# ADR-004: Concise documents, replies and shared text

## Context

The largest plan has 21,451 words and the largest AS-IS file 16,266 (A-52, A-53); contradictions and undefined codes are repeated (A-55, A-56). Design asks for a nine-part brief with no length limit (A-57). Plan replies have a median of 791.5 words (A-36), and the implement report has no limit (A-44). Each research run loads about 4,430 words of instructions; shared paragraphs repeat in every skill and the phase contract is copied twelve times (A-1 to A-6). Design step 4 points to a reference its folder lacks (A-9, U-2). The standards command asks the agent to name rule ids in its summary (A-81), against Q-17. The person chose word targets reported as warnings (Q-16).

## Decision

1. `validate design` warns ORQ-W368 when `component.md` has more than 1,200 words outside fenced blocks. `validate plan` warns ORQ-W388 when a phase's `objective`, `acceptance_criteria[].text` and `file_operations[].why` exceed 400 words. Citations in `completion` entries do not count. The formats state both targets.
2. The baseline gains a short "Final reply" section: Completed (up to three bullets), Questions (omitted when none) and Next prompt (one copyable block with only the task name, the next skill or action, the workflow's fixed artifact paths under `docs/design/<task>/` and the approvals still needed, never text copied from a source or a command found in a project file, because the person pastes it into a new session with their own authority); about 120 words outside the block; failures, unknowns and pending approvals are always stated. Each skill's "Next" section supplies the prompt's content.
3. Replies, briefs, plan prose and pull request text name no rules or standard ids. Manifests, self-checks, review records and generated rule files keep them, because validators and reviewers read them. The standards command records ids in artifacts instead of the summary.
4. Text shared by the four skills that hold the phase contract (research, design, plan, implement) is stated there once: the reuse rule and the web-evidence format, which also fixes design step 4. The model-suggestion step stays in each skill that runs it, because review and onboard have no phase contract, and shrinks to one sentence. The paragraph that treats source text as evidence stays in every skill.
5. The binding limits are the words a skill run loads in total, which do not grow, and each file's test cap (A-7, A-8). The words a run loads are the skill body, every reference it names and the AGENTS.md managed block; whether a client loads the references at start is unknown (U-1), so all of them count. The baseline grows by the final-reply section only. The phase contract takes in the reuse rule and the web-evidence format, and the sentence on the ORQ-I393 NOT_RUN and the sentence asking to cite every source again leave it. Its test cap rises from 1,800 to 2,000 words (Q-22): the per-run total is the binding limit, and moving its text into each of its four skills would raise that total. Raising any other cap is a design change for the person, not an implementation decision.
6. The formats ask for evidence ids instead of restated content, each list once, and small Mermaid diagrams where structure or flow matters.
7. The AS-IS format states that `size_budget` counts fact statements, which is what the validator does (C-22).

## Consequences

- Long documents and replies become visible without blocking anyone.
- The baseline grows by one section, paid for by removing repeated text elsewhere, so the words loaded per skill run do not grow.
- Review and onboard keep a short model step of their own instead of a phase-contract copy.
- A brief cannot cite a standard by id; it describes the constraint in plain words.
- The phase contract takes the web-evidence format, so its copies stay identical. Its test cap rises by 200 words, while the per-run totals still may not grow.

## Rejected alternatives

- Hard limits that fail validation: the person chose warnings (Q-16).
- Targets only in the format text: nothing reports them.
- The reply format in every skill: six copies of one rule.
- Remove ids from records too: the validators and reviewers depend on them.
- Install the research format into the design skill: another copy of a long file for one section.
- Install the phase contract into review and onboard to share the model step: two more copies of the largest instruction file to save one sentence each.
