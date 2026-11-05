# ADR-001: Where models are selected, the selection modes and the precedence order

Status: proposed with the design. The precedence order in Decision 4 is the one the request asks the person to approve.

## Context

- Orqlet "never calls a language model, takes a prompt or starts an agent" (`.prompts/rules.yaml`, ORQLET-NOMODEL-001, A-68). Proposal section 14.9.1 says there is no model selection at run time (A-75). The person asked to be consulted before this boundary changes (U-26).
- The person answered that the model "will be selected on auto" (Q-18) and that Orqlet should "choose the most relevant models by default, and on release recheck, and update it" (Q-17, Q-20).
- Only Cursor documents an automatic router (A-154); Codex documents a default and Power presets (A-151, A-152, A-153); Claude Code documents `default` and `opusplan` (A-148, A-149, A-150). In Cursor, Auto applies to the parent agent and a custom subagent defaults to `inherit` (A-157); the team's Router is enabled with the routed model Displayed (Q-30, Q-10).
- Each client has its own order for explicit choices (A-94, A-101, A-107, A-120). The renderers write only `inherit` or no key (A-9, A-10, A-11), and `RenderRequest` has no policy input (A-8, A-16).
- The request lists the precedence among a task or session override, a team assignment for the role or skill, a team assignment for the profile, and the approved automatic policy, and asks the person to approve it during design.

## Decision

1. **Two selection moments, and Orqlet takes part in neither as a selector.**
   - *Refresh time:* `orqlet upgrade` renders the approved policy into the model setting of generated subagent files (and Claude Code skill files), as ADR-003 says. This is a deterministic render, as every other generated file is.
   - *Run time:* the client selects (Auto, the default, `opusplan`, or a pin), the person overrides in the client, and the IDE agent may name a model when it starts a subagent, within what `orqlet models resolve` printed. Orqlet never selects at run time, never calls a model and never starts an agent.
   This reads the person's answers to Q-17 and Q-20 as "refresh-time selection plus the IDE agent's own run-time choice, with the most relevant models as the shipped defaults". It does not change ORQLET-NOMODEL-001.
2. **The default mode is `automatic`.** With no policy, or with a role or profile left on `automatic`, generated files stay as they are today (`model: inherit` for Claude Code and Cursor, no key for Codex) and the client chooses (Q-18). The main agent is never pinned.
3. **Three modes**, per assignment or profile:
   - `automatic`: no pin; the client's own automatic selection applies, inside the company's controls.
   - `manual`: the first eligible candidate in the approved order is pinned. When none is eligible, nothing is pinned, the exact reason is reported and the role keeps its automatic setting. This is the only mode that renders a pin.
   - `automatic-with-fallbacks`: as `automatic`, so **no pin is rendered and the generated files are those of `automatic`**, plus an explicit, approved, ordered fallback list that `models resolve` returns and that the agent may name by an explicit override when the automatic choice is unavailable or blocked. A fallback that is used is recorded as `explicit-fallback`.
4. **Precedence, highest first** (for the person's approval):
   1. an explicit task or session override made in the client, or passed to `orqlet models resolve --override` to be validated;
   2. a team assignment for the role or skill, for the client;
   3. a team assignment for the logical profile, for the client;
   4. the approved automatic policy: the client's own automatic selection.
   An explicit valid team selection (levels 1 to 3) beats automatic ranking in `manual` mode, where it is rendered; in `automatic` and `automatic-with-fallbacks` modes nothing is rendered, `models resolve` shows the candidates, and the recorded source is `automatic` unless a fallback or an override is named. A choice at level 1 to 3 that fails a constraint is reported with its reason and is never replaced by a lower level without a visible finding.
5. **Constraints apply at every level:** not excluded (ADR-005); approved, and not `disabled` or `retired` (ADR-004); a route for the client with a known identifier; access not blocked; the profile's required capability; and reviewer diversity (ADR-007). Selection depends only on these recorded states and never on today's date: a `retires_on` date is checked by `validate model-policy` as a warning, so the same policy renders the same bytes on every day. An unevaluated model may be a candidate; its evaluation and access states are shown as they are. At level 1 a constraint can be checked only through `models resolve --override` and through the review records; a run-time override of a role that leaves no record (the tester, the inventory and trace roles) is not checked.
6. **The source of each selection is recorded** as one of `task-override`, `role-assignment`, `profile-assignment`, `automatic` or `explicit-fallback`: in `models resolve` output and in review records (ADR-007).
7. **Task scope is a resolve-time selector only.** An assignment may name a `task`; `models resolve --task` applies it; it is never rendered into a global agent file.
8. **Tier hints (v0.5 section 10.3) are adopted as the profile of an assignment, and nothing more.** A hint is shown by `orqlet models resolve --skill <name> --client <client>` (the profile, the ordered candidates and the mode) and is named in the opening step of each workflow skill as text that tells the agent to offer it to the person. A skill never changes the main model itself. For the main agent this is the meaning of "design and planning prioritise quality" (R-1): in Claude Code an explicit skill assignment pins the model for the turn (ADR-003); in Codex and Cursor the person or the client chooses, and Orqlet offers the hint. Cursor's Router mode (Cost, Balance, Intelligence) is an administrator setting that Orqlet neither reads nor sets.

## Consequences

- The IDE-first boundary and ORQLET-NOMODEL-001 stay as written; the new rule text (ORQLET-MODEL-001, ADR-006) says so.
- Under Cursor Auto, a reviewer that inherits can run on a model that no file names and that can differ between turns (I-10). The design therefore does not claim diversity from selection; it derives it from the recorded identities after the run (ADR-007). Whether an inheriting Cursor subagent is routed per request is unknown (U-28), so nothing in the design depends on it.
- A task-scoped assignment affects only what the agent names when it starts a subagent; the client may still replace the choice (A-96, A-119), which the record shows as requested differing from observed.
- The precedence order is fixed in code and shown in the docs; a team cannot reorder it. A team that wants another order has to ask for a change of the design.
- R-1 is met in full only where a client lets a project file set the model, and only after a team opts into `manual`: for subagents in all three clients and for skills in Claude Code. Under the default `automatic`, subagents keep `model: inherit` (Claude Code, Cursor) or no key (Codex), so the PR-text role also runs on the parent's model until a team opts in. For the main agent in Codex and Cursor it is met by a hint and the person's or the client's choice; this is a limit of what the clients document (A-75, A-147), stated here and not hidden.

## Rejected alternatives

- **Orqlet resolves and applies a model at run time** (a wrapper, a hook or a command that picks a model per request). It breaks ORQLET-NOMODEL-001 and needs the person's consent to change the boundary; the person asked for refresh-time application plus the IDE agent's choice.
- **Pin every role by default.** It contradicts "selected on auto" (Q-18), and clients replace a blocked pin without telling Orqlet (A-66, A-96, A-119). Whether a project file may set the main session model was never researched (A-75).
- **Only each client's native precedence, with no Orqlet order.** The request asks for a team assignment that outranks automatic ranking and for an order the person approves; the three native orders differ (A-94, A-101, A-107).
- **Task-level pins rendered into agent files.** The files are global and protected; one task cannot change them.
