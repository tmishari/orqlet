# Work status

Updated: 2026-11-23. Authority: the person's instruction in the current chat to
freeze the unfinished work and prioritize the workflow-efficiency request.

## Active priority

`workflow-efficiency`: the consolidated request from the current chat. Its scope
is faster execution, fewer repeated checks and tool calls, concise human-readable
design and plans with useful visuals, friendly model-policy and review messages,
simple professional code, focused tests, removal of verified obsolete code,
short results with a copyable next prompt, and final documentation synchronization.

The request is defined; research, design and plan have not been completed for it.
This priority does not approve implementation or bypass any phase gate.

## Frozen backlog

All outstanding work in the existing research, designs and plans is on hold,
including the following. Completed and merged work keeps its existing status.

| Workstream | Work on hold |
| --- | --- |
| [One-command setup](one-command-setup/plan.yaml) | Remaining P-7, P-8, P-10 and P-11, plus outstanding acceptance work. P-9 was removed from this plan. |
| [Go migration feasibility](go-migration-feasibility/questions.yaml) | Q-7 and Q-8, research completion, and any subsequent design or implementation. |
| [Open items](open-items/questions.yaml) | Research into approval/merge evidence, branch protection and artifact rebasing. |
| [Graphify and tool preparation](one-command-setup/design/adr-006-bundled-skills-and-tool-preparation.md) | The separate task requested in Q-60; it is outside one-command setup. |
| [Team conventions/resources](team-conventions-resources/plan.yaml) | P-9 native-client qualification. |
| [Phase-skill contracts](phase-skill-contracts/plan.yaml) | Outstanding V-1, V-2 and V-3 session qualification. |
| [MCP integrations](mcp-or-plugins/plan.yaml) | Outstanding portions of native-client qualification. |
| [Harness2 fit](harness2-fit/tests/P-6.yaml) | Unverified P-6 acceptance items. |
| [Dynamic model profiles](dynamic-model-profiles/questions.yaml) | Open Q-35, Q-36 and Q-38 and outstanding acceptance-record reconciliation. |
| [Architecture roadmap](orqlet-architecture-proposal.md) | All undelivered roadmap work, including CI/merge enforcement, knowledge indexing/catalogue, wider MCP support, auditing, external sources, model refresh, scaffolding and evaluation. Previously deferred automation remains deferred. |

## Hold rules

- Do not advance, extend, rebase or run acceptance work for a frozen task without
  an explicit instruction from the person to resume it. An older approved plan
  does not override this hold.
- Existing artifacts may be read as evidence for `workflow-efficiency`. Changes
  required by that task need its own approved design and plan; overlapping files
  do not implicitly resume another task.
- Preserve existing code, tests, uncommitted work, approvals and completion
  records. This hold adds no new artifact-schema status and marks nothing complete.
- When the person resumes a task, reassess its current inputs and prerequisites
  under the applicable workflow before continuing.

This is a repository instruction, not a process scheduler. It does not stop
already-running commands or chats, and is not a commit or pull request.
