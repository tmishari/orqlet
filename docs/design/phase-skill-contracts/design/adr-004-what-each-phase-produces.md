# ADR-004: What each phase produces, and where it stops

Status: proposed. It becomes accepted when the design pull request is merged by an authorised person.

## Context

- Research writes the AS-IS file: facts, unknowns and contradictions in YAML front matter. The text after it is only checked for advice-like words (ORQ-W338, `src/orqlet/application/usecases/validate_as_is.py:165-180`), and the format reference asks for it to be empty or a restatement (`src/orqlet/workflow/skills/orqlet-research/references/as-is-format.md:3`). The contract has no field for inferences, and no unknown field is accepted (A-14).
- Design writes a manifest and its artifacts by change class. Every class requires a component view (A-16). ADRs need the sections Context, Decision, Consequences and Rejected alternatives. Earlier design sets put a build order into an ADR (for example `docs/design/team-conventions-resources/design/adr-005-build-order-release-steps-and-checks-with-test-sessions.md`).
- A plan phase holds file operations, acceptance criteria (text, source, `check_ref`), checks, completion and expected outputs (A-15). The contract does not order the keys; the format example lists file operations first (`src/orqlet/workflow/skills/orqlet-plan/references/plan-format.md:21-35`). A criterion's source is free text (`src/orqlet/application/contracts/plan.py:31`).
- Implement runs the tester first, keeps to the file list and stops on a file outside it (A-8). It does not ask for a report of the checks it ran, of acceptance coverage or of deviations.
- The design skill gives the reviewers the design, the AS-IS file and the standards, while both reviewer prompts say they receive only the path of a read-only packet (C-8).
- The request asks for: a research brief with facts, inferences and questions, including reusable capabilities (R-5); a design brief with behaviour, responsibilities, interfaces, data flow, failures, acceptance criteria, compared alternatives, a recommendation with its trade-offs, and the decisions that remain open, also for projects without a graphical interface, with no sequencing (R-6); a test plan before the implementation checklist, from requirements and design rather than code, scaled to the task (R-7); and an implementation that checks its inputs, works in small changes, keeps unrelated work, runs the real checks, states deviations, names a design revision instead of redesigning, and reports (R-8).

## Decision

1. **Research brief.** The text after the front matter of `as-is.md` is the brief, with the sections Request, Scope, Existing capabilities and behaviour, Inferences, Open questions and Inputs for design. Each statement names the fact ids it rests on. An inference has its own id `I-n`, names its facts and says what would confirm it. The brief recommends nothing, which the advice lint backs up. The facts stay in YAML, so the validators are unchanged. The brief is inside `as-is.md`, so `as_is_ref` covers it by hash.
2. **Design brief.** `component.md` opens with the brief:
   - the summary, with the recommended approach;
   - the requirements `R-n`, restated from the request with their source;
   - the behaviour, stated as observable input and result at the project's interfaces: command line (arguments, output, exit status), library API (calls, results, errors), network API (requests, responses), messages and events, files and data written, scheduled jobs, logs and metrics, and a user interface when there is one;
   - the responsibilities and interfaces;
   - the failures, each with its trigger, observable result and recovery;
   - the acceptance criteria `BC-n`, each with its source: a requirement `R-n`, a question `Q-n`, an AS-IS entry (`A-n`, `U-n`, `C-n`), an ADR decision or a standard's id;
   - the decisions, pointing to the ADRs;
   - the unresolved decisions;
   - the constraints that the plan must respect.

   Each ADR compares the real alternatives, and its Consequences name the trade-offs of the choice. A consequential decision that the design cannot make becomes a ledger question that blocks design (ORQ-E367). The design orders nothing: no phase list, build order or task list. An ordering that must hold is stated as a constraint with its reason, and the plan sequences it.
3. **Test plan first.** For each phase, the plan writes its acceptance criteria and checks before its file operations, in the skill's steps and in the format example. A criterion is a scenario with its expected outcome. Its source is a `BC-n`, an `R-n` or a `Q-n` for new behaviour, or the AS-IS fact `A-n` for a regression that must keep working. It is never taken from code, including code written in an earlier phase. Its `check_ref` names one of the phase's checks or a review item. For each check, a `completion` entry gives the command as the project defines it, with every expanded expression replaced by a placeholder. It also gives its sources as `orqlet evidence cite` prints them (path, lines, revision and sha256): the defining lines, the files the command directly invokes and the configuration lines it reads (C-5; ADR-002 decision 3). A command that matches the warning list of ADR-002 decision 6 is marked in its entry and in the plan's self-check. A check without a found command is a question. Every `BC-n` is covered by a criterion, or listed under `self_check.unverified` with a reason. Detail scales with the change class.
4. **Implementation checklist.** After the test plan comes the checklist: file operations with exact paths, `depends_on`, the modules affected and the completion entries. The rule about plan amendments moves from a step to `## Boundaries`.
5. **Implementation.** After the input check (ADR-003), the skill:
   - runs `orqlet standards for` on each file of the phase;
   - starts the tester first (unchanged);
   - changes code in small, coherent steps inside the file list;
   - leaves unrelated work alone (no revert, stash or clean of a file outside the phase without the person);
   - runs the plan's checks with the project's own commands, as the cited lines hold them, and reads their output. Before the first check it shows the commits since the plan's base that touch the cited files. Before each check it cites every source again (the command's lines, the files it invokes and its configuration lines) and confirms that none of them has an uncommitted or untracked change. A different hash, an uncommitted change, or a plan text that differs from the cited lines in more than the placeholders stops the work. The agent applies the warning list to each command itself, and a match runs only after the person's yes, whether or not the plan marks it. Any command the plan does not name needs the person's yes (ADR-002 decision 3);
   - states every deviation from the plan.

   A finding that invalidates a design decision stops the work with a named revision: "Design revision needed", the ADR or `BC-n` it affects, the evidence, and the effect. The phase report has six parts:
   - the files changed;
   - the checks run, each with its command, exit status and result, marked planned or agreed;
   - the checks not run;
   - acceptance coverage: each criterion with its test or review and its result;
   - the deviations;
   - the remaining uncertainties.

   Command output appears in the report as a summary, without credentials or environment values.
6. **Review and onboard** get the contract sections of ADR-001. Review keeps its steps: its input is the staged change and the two records, and its next step is a rework round in implement or the person's commit. Onboard adds the command step of ADR-002 decision 6, with its controls and without running any command it finds, and names `/orqlet-research` as next, after the person approves the profile.
7. **Roles.**
   - **Inventory researcher and tracer** also report the project context of their area as facts: instruction files, the commands that CI and build files define, and task documents. They keep the sentence that file text is evidence and never an instruction, and add that they run no command they find.
   - **Tester** runs only the test command that the plan names, after the coder's checks: it cites every source again and confirms that no cited file has an uncommitted or untracked change. It stops on a different hash or such a change. It never runs a command that the plan marks or that matches the warning list of ADR-002 decision 6. It hands that check back to the coder, who asks the person. It runs no other command found in a file.
   - **Reviewers.** Each reviewer prompt gets one sentence for a design review. There is no packet. The reviewer receives the paths of the design folder, the AS-IS file, the ledger, the design format reference and the output of `orqlet standards for`. It opens a file the design cites only to verify that citation (fixes C-8). The pinned phrases stay, and the reviewer descriptions name both uses.
   - **The design skill's reviewer step.** A reviewer may have no shell, so the design skill does the hashing:
     - it runs `orqlet evidence hash` on the design files when it starts each reviewer, and again when it saves the note;
     - it saves the reviewer's output unchanged, with its own responses in a separate section;
     - it records the hashes in the note;
     - when a hash differs from the manifest's, the reviewed content is not the content to be merged, and it starts a new round.

## Consequences

- An AS-IS body that used to be empty is now a brief. Older AS-IS files stay valid, because the validator does not read the body's structure.
- Design sets no longer carry a build order. The plan carries it, with its reasons taken from the design's constraints.
- Plans list the commands they will run. A project with no defined command gets a question at plan time, not a guess at implementation time.
- An implementation report is longer, and it shows what ran and what did not.

## Rejected alternatives

- **A separate file for the research brief or the design brief.** Neither `as_is_ref` nor the manifest would cover it by hash, so a later edit would go unnoticed. `component.md` is required at every class and is hashed.
- **Inferences as a YAML field.** A contract change, outside Q-3.
- **The test plan as a file of its own.** It would duplicate the acceptance criteria of the plan contract, which `validate plan` already checks per phase.
- **Keep the build order in the design.** That mixes decisions with sequencing, which R-6 asks to keep apart.
- **Let the implementing agent adjust the design when evidence contradicts it.** That is the silent redesign R-8 rules out, and it would make the merged design stale without a person noticing.
