# Component view and design brief: phase-skill contracts

## Design brief

### Summary and recommended approach

Give the six workflow skills one contract shape (ADR-001), let them read the receiving project's context when they run (ADR-002), make the task folder the handoff with an input check at the start of every phase (ADR-003), and sharpen what each phase produces (ADR-004). All of it is text in the workflow package: skill bodies, their references and the role prompts (Q-3, Q-6). Injection code stays as it is and gains tests. The workflow becomes 0.4.0 (ADR-005). No command, contract field or file location changes (Q-4, Q-9).

How this design reads Q-3 ("Skill texts and their reference files only"): what changes by intent is text, meaning skill texts, their references and, by Q-6, the role prompts. No contract, schema, Python module, tool or command changes. Some changes follow from that text change because the repository's own rules require them, and they are in scope for that reason only:
- the tests and goldens (ORQLET-TEST-001);
- `identity.json` and `MANIFEST.json` (ORQLET-DET-002);
- this repository's regenerated installed files and the PR template block, which carries the workflow version (Q-7);
- the README, whose skill table and file count describe the shipped skills (AGENTS.md "Update the documentation", `README.md:132`, `README.md:312-321`).

### Requirements

The person's request of 2026-11-02, restated. The quoted words are the person's.

- R-1 Distinguish this CLI repository, the receiving project and the development app.
- R-2 Preserve "public skill names, invocation mechanisms, supported apps, and useful behavior" and "valid metadata for each supported app".
- R-3 Each skill states its purpose and when to invoke it, its inputs and project context, the work, its phase boundaries, its output structure, how completion is checked, what passes to the next phase, and how missing or outdated prerequisites are handled.
- R-4 "Keep these instructions concise. Put detailed guidance in existing reference mechanisms."
- R-5 Research: findings with concrete references; facts, inferences and unanswered questions kept apart; reusable capabilities and existing behaviour; a research brief; no production code.
- R-6 Design: behaviour, responsibilities, interfaces, data flow, failure cases and acceptance criteria; alternatives compared, one recommended with its trade-offs; unresolved decisions named; a design brief; decisions kept apart from sequencing; projects without a graphical interface covered.
- R-7 Plan: the behavioural test plan first (scenarios, expected outcomes, regressions, verification methods), then the implementation plan (ordered steps, modules, dependencies, completion checks); behaviour derived from requirements and design, not from code; detail scaled to the task.
- R-8 Implementation: check the inputs against the repository; small, coherent changes; keep unrelated work; run the appropriate checks; make deviations explicit; name a design revision instead of redesigning; report the work, the verification results, acceptance coverage, deviations and uncertainties.
- R-9 Project awareness: root and scope, stack and architecture, instructions, conventions, the actual build, lint, type-check and test commands, and the "existing locations for task documentation and phase outputs", all from configuration and repository evidence at execution time; unknown stays unknown; no cross-project values. For phase outputs, Q-9 narrows this: they stay at `docs/design/<task>/`.
- R-10 Handoffs: each output names its task, scope, decisions, open questions and prerequisite outputs; a later phase detects an input that is absent, from another task or project, or materially outdated; usable in a fresh session; proportionate checks, with human judgment for consequential open decisions.
- R-11 Reliable injection: idempotent, managed content only, other instructions intact, local edits handled explicitly, no cross-project contamination, every adapter, valid formats, no unresolved placeholders, minimum new mechanism.
- R-12 Verification: repeated injection, two projects, updates over existing instructions and local edits, every adapter, and the skill content (phase boundaries, handoffs, test plan before implementation plan).
- R-13 Deliverable: a report of the changes and the existing CLI commands to apply them. "Do not invent a replacement CLI interface."

### Behaviour

This change has no graphical interface. Its behaviour is visible in three places.

- **Files rendered into a receiving project** (`orqlet init`, `orqlet upgrade`): each skill's `SKILL.md` with the contract sections; `references/phase-contract.md` in the four phase skills; the changed format references and role prompts. The bytes are the same for every project. The exit status and findings of `orqlet upgrade` are unchanged.
- **What an agent running a skill writes:** an AS-IS file whose body is the research brief; a design set whose `component.md` opens with the design brief; a plan whose phases put the acceptance criteria and checks before the file operations; a phase report with the six parts of ADR-004 decision 5.
- **What an agent says when an input fails the check:** which check failed (present, validator, same task, same project, approved, current, questions), what it found, and what would resolve it. Then it stops.

### Responsibilities and interfaces

| Component | Responsibility | Interface |
|---|---|---|
| `skills/<name>/skill.md` (six) | The contract and the steps of one skill | Front matter `name`, `description`; body with the seven headings; `requires` markers |
| `skills/<phase>/references/phase-contract.md` (four copies) | Project context, input check, handoff, words for `standards for`, installed files | Markdown; no markers; names existing commands only |
| `as-is-format.md`, `design-format.md`, `plan-format.md`, `review-format.md` | The format of one artifact | Markdown with one YAML example that passes its contract |
| `roles/*.md` (five) | The prompt of one subagent | Front matter `name`, `description`, `mode`; body |
| Loader and renderers (unchanged) | Turn the package into client files | `load_skills`, `render_steps`, the client adapters |
| Tests | Pin the text structure and prove the injection behaviour | pytest |

### Failures

| Trigger | Observable result | Recovery |
|---|---|---|
| The input artifact is missing (ORQ-I394) | The skill stops and names the skill that produces it | The person runs that skill |
| The validator reports an error that no later check names, such as a schema error | The skill stops and names the finding | The earlier phase fixes its artifact |
| A git check of the input check ends with an unexpected exit status or error output | The skill stops with "check not run" | The person fixes the cause, such as a missing ref, and the skill runs again |
| `header.task` differs from the folder (ORQ-E331, E350, E370) | The skill stops | The person names the right task, or the earlier phase runs again |
| The input's base revision is not in this repository | The skill stops and says the artifact comes from elsewhere | The person brings the right branch or starts the task here |
| The design or plan is not confirmed as merged: no merge commit named, or one not reachable from the protected branch's ref or from HEAD, or one that did not change the approved files | The skill stops | The person merges the pull request, names the right commit or ref, or confirms the D1 exception |
| An approved input was edited: a difference or an untracked file since its merge commit, ORQ-E353 or ORQ-E371 | The skill stops and names the file | A new approval pull request; the skill never continues |
| In plan or implement, the ledger changed since the design merge or the plan merge: any field of a question answered there, its removal, or the conflicts list | The skill stops and names the question or ruling | A new approval pull request; the skill never continues |
| In design, the ledger changed in the same way since the commit that recorded the AS-IS acceptance, or that acceptance is not committed | The skill stops | The person commits the acceptance, accepts the AS-IS file again, or asks for a refresh |
| The input is stale (ORQ-W390) | The skill stops and shows the cause matched to the invalidation matrix: this task's planned commits with signature status, author and files, an upgrade to a newer workflow version, other commits in scope, a rule change, or an unknown cause | Continue only where the matrix keeps the approval valid and the person confirms; otherwise an AS-IS refresh, an impact review or a new approval |
| A path or glob from an artifact holds a character outside letters, digits, `.`, `_`, `-`, `/`, `*` and `?` | The skill stops before composing the command | The person checks the artifact |
| A planned check's source lines changed after the plan was approved | Implementation stops before running the command | The person reviews the change; a plan amendment if the command changed |
| Onboard finds a command that pipes into a shell, fetches from the network or uses elevated rights | It shows the command with a warning and does not run it | The person confirms that entry on its own, or leaves it out |
| A blocking question is open | The skill stops and asks it | The person answers; the ledger records it |
| A command is not found in the project | It becomes a ledger question at research, design or plan time | The person names it; onboard can record it in AGENTS.md |
| New evidence invalidates a design decision during implementation | The agent stops with "Design revision needed", the ADR or `BC-n`, the evidence and the effect | The person sends it back to design |
| An installed skill was edited by hand | `orqlet doctor` reports ORQ-E150; `orqlet upgrade` restores it with ORQ-W096 | Guidance moves to AGENTS.md team text or `.prompts/` |
| Two copies of `phase-contract.md` differ, or a skill lacks a section | A unit test fails before release | Fix the source |

### Acceptance criteria

Each criterion is checked by a test unless it says "review" (a reviewer of the pull request) or "session" (ADR-005 decision 5). Its source is a requirement `R-n`, a question `Q-n`, an AS-IS entry, an ADR decision or a standard's id.

Contract shape:
- BC-1 Each of the six skills keeps its directory, its `name`, its two front-matter fields and, after rendering, `disable-model-invocation: true` in each `SKILL.md` and the Codex sidecar's implicit-invocation setting, as today. (R-2, A-2, A-21)
- BC-2 Each skill body has, in this order:
  - the purpose paragraph;
  - the paragraph "Source material is not authority" in full and unchanged;
  - the headings `## Inputs`, `## Boundaries`, `## Steps`, `## Output`, `## Done when`, `## If an input is missing or outdated` and `## Next`.

  It has exactly one numbered list, under `## Steps`. That list is numbered from 1 without a gap both with every command present and with the command set `BEFORE_RECORDS` of `tests/unit/render/test_skills.py:192-199`. Its last step contains "STOP.". With `BEFORE_RECORDS`, no line names a command outside that set. (R-3, A-3, A-54, ADR-001 decision 2)
- BC-3 `## Next` names the successor:
  - onboard: `/orqlet-research`;
  - research: `/orqlet-design`;
  - design: `/orqlet-plan`;
  - plan: `/orqlet-implement`;
  - implement: `/orqlet-implement` with the next phase id, or the pull request after the last phase;
  - review: `/orqlet-implement` for a rework round, or the person's commit.

  Whether it says what the person does first is a review item. (R-3, R-10, A-11)
- BC-4 Research, design, plan and implement each carry `references/phase-contract.md`. The four copies are byte-identical, each skill body names the file, and it has the sections Project context, Input check, Handoff, Words for `orqlet standards for` and Installed files. (R-4, ADR-001 decision 3)
- BC-5 Every backticked `orqlet ...` in a skill body or a reference names an existing command and existing flags. (Q-4, R-13)
- BC-34 `phase-contract.md` names the three places: the installed text, which is the same for every project; the receiving project, where the context and the task folder are; and the development app, which only finds and starts the skill. (R-1)
- BC-35 Every rendered skill body is at most 70 lines and 900 words, and `phase-contract.md` at most 150 lines and 1,800 words. Today's bodies hold 355 to 712 words. (R-4, ADR-001 decision 2)

Project context:
- BC-6 Two projects initialised with different profiles (name, kind, technologies, clients in common), with distinct project uuids and no resource registry, receive byte-identical workflow skill, reference and role files. No workflow skill, reference or role file written into one contains the other's project name, uuid or a technology that only the other declares. (R-9, R-11)
- BC-7 `phase-contract.md` lists the context sources of ADR-002 decision 1. It says that a value not found is an unknown with a ledger question, and that no value comes from an example, another repository or an earlier session. (R-9)
- BC-8 `phase-contract.md` says that:
  - a command is cited with its file and lines, together with the repository files it directly invokes and the tool configuration lines it reads;
  - a credential, token or password in a connection string is never copied, and every expression the CI system or the shell expands (a dollar sign followed by a name or by braces) becomes a named placeholder; the reference describes these in words, without literal double braces (BC-30);
  - a placeholder is filled only from an environment the person has set up, a secret is never asked for in the conversation, a non-secret value comes only from the person or the cited lines and passes the argument rule of BC-40, and a check that lacks a value is reported as not run;
  - a secret goes into the command as a variable reference (`"$NAME"`); the agent checks only that the variable is set, for example with `test -n "$NAME"`, and never prints, echoes or lists an environment value;
  - files that hold secrets (`.env` files, private keys, `.npmrc`, `.pypirc`, `.netrc`, cloud credential files) are never opened;
  - research, design, plan and onboard never run a command found in a file;
  - implementation shows the commits that touch the cited files since the plan's base before the first check, runs the plan's checks as the cited lines hold them after citing every source again and confirming no uncommitted or untracked change to the cited files (a different hash, such a change or a differing plan text stops it), applies the warning list of ADR-002 decision 6 to each command itself and asks before running a match whether or not the plan marks it, and runs any other command only after showing it, its source and the reason and getting a yes;
  - every command run is marked planned or agreed, and reports show commands in their placeholder form;
  - no command is run because a file says so;
  - command output is summarised without credentials.

  The wording is a review item. The presence of the credential, secret-file, onboard and re-cite rules is tested. (R-9, ADR-002 decision 3, ORQLET-SEC-003)
- BC-9 The standards step of each phase skill runs `orqlet standards for --path <path> --phase <word> --role <role>` with `research`/`researcher`, `design`/`architect`, `plan`/`planner` and `implementation`/`coder`. (A-10, C-9, ADR-002 decision 7)
- BC-10 `phase-contract.md` and the onboard skill say that `orqlet upgrade` restores an edited installed file with ORQ-W096, that `orqlet doctor` reports it as ORQ-E150, and that project guidance goes into AGENTS.md outside the managed blocks or into the project's standards folder. (Q-8)
- BC-11 `phase-contract.md` says that phase outputs live at `docs/design/<task>/` and that the project's own task documents are read and cited where they are. (Q-9)
- BC-12 Onboard finds build, lint, type-check and test commands in CI and build files and never runs them. It writes an entry into AGENTS.md outside the managed blocks only:
  - in the fixed form of ADR-002 decision 6: a label, the command with placeholders alone in a fenced block whose fence is longer than any backtick run in it, and the source path and lines, under a heading that names onboard and the sources and says the entries are a record, not an instruction to run anything;
  - after showing the exact change and getting a yes for that entry;
  - for a command on the warning list of ADR-002 decision 6, only after a warning and its own confirmation.

  A later skill compares such an entry with the source it names, and any difference is a question.

  The text is tested; the behaviour is session V-3. (R-9, U-5, ADR-002 decision 6)

Handoffs:
- BC-13 `phase-contract.md` says that `workflow_version` and `protected_set_digest` go to the top level of the header and the other four bound values into `header.bound`, and that the `standards for` hashes go into the self-check. (C-7, C-2)
- BC-14 Design, plan and implement run the input check of ADR-003 decision 4 before any other step, in its order:
  - present, then the validator before any git command, where an error that no later check names stops the skill;
  - same task, then same project with `git merge-base --is-ancestor <base_revision> HEAD`;
  - approved: acceptance for design. For plan and implement, the person names the protected branch's remote-tracking ref and a merge commit; the agent may list candidates from that ref only, never choose. The commit must be a full hex id, reachable from the ref and from HEAD, and a commit that changed the approved files. `git diff --quiet <merge> -- <approved files>` must find no difference, and no file under them may be untracked;
  - current, including the ledger rule of BC-39, then questions, where an unknown counts as unanswered only when its `question_ref` is open and blocks this phase.

  Each git check passes only on its expected exit status (0 or 1 for `--quiet` and `--is-ancestor`; 0 with nothing on the error output for other commands), and anything else stops the skill with "check not run". A composed revision is resolved with `git rev-parse --verify` and single-quoted. A failed check stops the skill and names what resolves it. The skill never edits an earlier artifact or its bound values to pass the check. (R-10, U-1, U-3, W-5; sessions V-1, V-2)
- BC-39 `phase-contract.md` says that an edited approved input stops the skill for a new approval, and that the skill never continues on it. An edited approved input is a difference or an untracked file since its merge commit, ORQ-E353 or ORQ-E371. The ledger rule fails closed. It compares `questions.yaml` with each reference commit: the design merge for plan, and both the design merge and the plan merge for implement. Any change to any field of a question that was answered there, its removal, or any change to the conflicts list stops the skill for a new approval. Only new questions, and the answer and status of a question that was open there, do not count. For design, the reference is the commit that recorded the AS-IS acceptance; the same changes, or an acceptance that is not committed, lead to a new acceptance or a refresh. (W-4, W-5, ADR-003 decision 4; `docs/design/orqlet-architecture-proposal.md:3073-3074`)
- BC-40 `phase-contract.md` says that every value taken from an artifact goes into a command as one single-quoted argument, with paths after `--` in git commands. A path or glob with a character outside letters, digits, `.`, `_`, `-`, `/`, `*` and `?` stops the skill, and no command is built from an artifact's free text. (ADR-002 decision 3)
- BC-15 For a stale input, `phase-contract.md` maps each cause to the invalidation matrix row of ADR-003 decision 6:
  - for each commit since the base that touches the scope, it shows the hash, the signature status where the project signs, the author, the subject and the changed files;
  - it treats the trailer and the author as claims;
  - planned work is limited to earlier phases' operation files, the knowledge paths and the record folders `reviews/`, `tests/`, `knowledge/` and `evidence/web/` of the task;
  - the upgrade row applies only when the header's `workflow_version` is older than the installed one, and a digest change without it is an unknown cause;
  - it continues only where the row keeps the approval valid and the person confirms;
  - otherwise it stops for a refresh, an impact review or the person's answer. (R-10, U-2, W-4, W-5)
- BC-16 The plan and implement skills say that a NOT_RUN result of `orqlet gate status <task>` caused by ORQ-I393 alone is not a failure, and that the checks of ADR-003 decision 4 decide everything else. (C-6)
- BC-17 The research skill records the person's acceptance: `header.status: approved`, a self-check entry quoting the person with the time, and `orqlet validate as-is` run again. It says that an agent that changes an accepted AS-IS file sets it back to `draft` and asks again. (U-1, ADR-003 decision 7)
- BC-18 `phase-contract.md` holds the table of ADR-003 decision 2: where each output names its task, scope, decisions, open questions and prerequisites. (R-10)
- BC-19 Each phase skill says it starts from `docs/design/<task>/` and the ledger, not from the memory of an earlier session. (R-10)
- BC-37 The research skill runs the input check on an earlier AS-IS file it resumes. (R-10, ADR-003 decision 4)

Phase outputs:
- BC-20 `as-is-format.md` defines the research brief: the sections of ADR-004 decision 1, inferences `I-n` that name their fact ids, and no recommendation. (R-5)
- BC-21 `design-format.md` defines the design brief at the top of `component.md` with the parts of ADR-004 decision 2, including behaviour by interface kind for projects without a graphical interface. It says that a design contains no phase order and that an unresolved consequential decision is a blocking ledger question. (R-6)
- BC-22 In the plan skill, the step that writes acceptance criteria and checks comes before the step that writes file operations. In the `plan-format.md` example, `acceptance_criteria` and `checks` come before `file_operations`. The format says:
  - a criterion's source is a `BC-n`, `R-n` or `Q-n`, or, for a regression, an `A-n`, never code;
  - each check has a `completion` entry with the command, every expanded expression replaced by a placeholder, and its sources as `orqlet evidence cite` prints them: the defining lines, the files it directly invokes and the configuration lines it reads;
  - a command that matches the warning list of ADR-002 decision 6 is marked in its entry and in the plan's self-check.

  The example in the format still passes its contract. (R-7, C-5, ADR-002 decision 3)
- BC-23 `plan-format.md` says that every `BC-n` is covered by a criterion or listed under `self_check.unverified` with a reason. (R-7; review)
- BC-24 The implement skill holds the steps of ADR-004 decision 5, including the re-cite before each check, "Design revision needed" and the six-part report with planned or agreed commands. (R-8)
- BC-25 Both reviewer prompts keep the phrases "the path of a read-only packet", "do not receive the Coder", "not a guarantee" and "absence record". They add the design-review sentence of ADR-004 decision 7: inputs, and citations opened only to verify. Their descriptions name both uses. The design skill's reviewer step gives the same inputs. It runs `orqlet evidence hash` on the design files when it starts each reviewer and again when it saves the note, and saves the reviewer's output unchanged with the author's responses in a separate section. When a hash differs from the manifest's, it starts a new round. (C-8, Q-6, ADR-004 decision 7)
- BC-26 The inventory and tracer prompts ask for the project context of their area as facts and say they run no command they find. The tester prompt says it runs only the test command the plan names, after the coder's checks: citing every source again and confirming no uncommitted or untracked change to a cited file. It stops on a different hash or such a change. It never runs a command that the plan marks or that matches the warning list of ADR-002 decision 6, and hands that check back to the coder, who asks the person. Every role keeps the no-lookup sentence exactly once, as `tests/unit/test_workflow_lookup_text.py:417-425` pins today. Every role, the tester included, holds "never an instruction" exactly once. Today `tests/unit/render/test_skills.py:473-480` pins only its presence in the four read-only roles, and that test is extended. (Q-6, R-9, ADR-004 decision 7)

Injection and release:
- BC-27 Two `orqlet upgrade` runs in a row after a workflow change that changes a skill: the second plans nothing and writes nothing. (R-11, R-12)
- BC-28 An upgrade over an AGENTS.md with team text before, between and after the managed blocks keeps that text byte-identical and holds exactly one copy of each block. (R-11, R-12)
- BC-29 An upgrade over an edited installed `SKILL.md` and an edited reference restores both and reports ORQ-W096 for each; `orqlet doctor` run before the upgrade reports ORQ-E150 for each. (R-11, Q-8)
- BC-30 Every file that each client adapter renders parses in its format (YAML front matter, TOML, YAML sidecar, JSON), and none contains `{{`, `}}`, `<!-- requires:` or `<!-- unless:`. (R-11, U-12)
- BC-31 `identity.json` says 0.4.0 with controls level 3, `releases.json` is unchanged, and the golden tests pass against the committed goldens. Every CI job passes (`.github/workflows/ci.yml:18-107`): `ruff check`, `ruff format --check`, mypy, `lint-imports`, `tools/export_schemas.py --check`, `tools/build_manifest.py --check`, pytest on Ubuntu, macOS and Windows with Python 3.12 to 3.15, and the build job, which builds the wheel twice and compares the digests. (ADR-005 decision 2, ORQLET-DET-002, ORQLET-QA-001)
- BC-32 This repository's installed files are regenerated by `orqlet upgrade`. Afterwards `orqlet upgrade --check` reports nothing to upgrade, and `orqlet doctor` reports no ORQ-E150 or ORQ-W152 for any of them. (Q-7)
- BC-33 None of these changes:
  - a Python module under `src/orqlet/`;
  - a workflow file outside the skills, roles, `identity.json` and `MANIFEST.json`;
  - a file under `tools/`, `.github/workflows/` or `.prompts/`;
  - a team-owned `.orqlet/` file (profile, resources, role bindings, versions, knowledge); the two proposal diffs `.orqlet/proposals/.orqlet__versions.yaml.diff` and `.orqlet/proposals/.orqlet__role-bindings.yaml.diff` may change, because they are upgrade's output (Constraints for the plan), and no other proposal file;
  - a client permission, hook or MCP file;
  - `pyproject.toml`, `uv.lock` or a dependency.

  `orqlet gate status <task> --phase <phase>` reports no ORQ-E451 for the watched surfaces. Three review items cover surfaces inside the scope:
  - the three `.orqlet` lock files and the two proposal diffs change only through `orqlet upgrade`, `orqlet upgrade --check` (BC-32) plans no write to them after the regeneration, and no phase applies a proposal;
  - the regeneration phase's report says that applying the role-bindings proposal later changes reviewer independence;
  - the refusal of `--update-golden` in CI (`tests/conftest.py:34-39`) stays unchanged. (Q-3, Q-4, ORQLET-DET-001)
- BC-36 The final report names the skills that changed, how project context reaches them, how the phases hand over, the injection changes (none), the verification run with its results, and the existing commands to apply the update. (R-13; review)
- BC-38 For the workflow skill, reference and role paths, the files that `orqlet init` writes for the three clients equal the committed goldens byte for byte. Those bytes depend on the workflow version only (A-22, A-23). The goldens' rule files come from `SAMPLE_RULES` (`tests/support/render.py:65-100`) and are not compared. (R-11, R-12, U-13)

### Decisions

- ADR-001 One contract shape for every skill, with the shared detail in one reference.
- ADR-002 Project context is read from the receiving project when a skill runs.
- ADR-003 The task folder is the handoff, and every phase checks its inputs before it starts.
- ADR-004 What each phase produces, and where it stops.
- ADR-005 Injection stays as it is and gains tests; the workflow becomes 0.4.0; this repository is regenerated by upgrade.

### Unresolved decisions

None blocks this design. These are left open on purpose:

- Two receiving projects with the same project uuid, for example from a copied profile, would share journals and backups (A-46, U-3). Detecting that needs code, outside Q-3; a separate task can take it up.
- How Codex starts a skill by name is not documented (U-11). `## Next` uses the slash form, which Claude Code and Cursor use.
- `controls_level` stays 3 under the reading of ADR-005 decision 2; a reviewer may raise it.

### Constraints for the plan

- This repository's installed files are regenerated with `orqlet upgrade` only after the workflow package and the tests are final (Q-7, AGENTS.md "Generated files").
- `MANIFEST.json` is rebuilt and `identity.json` raised whenever the package changes (ORQLET-DET-002).
- The README's skill table and its count of files that `init` writes describe the shipped skills, so they change in the same change (`README.md:132`, `README.md:312-321`; AGENTS.md "Update the documentation").
- The lookup steps keep their pinned phrases and order: in research the lookup step precedes the step that cites evidence, and in design "Commit it" precedes `orqlet evidence cite` (A-55).
- The two-project test gives each project its own uuid. Test support's id source is predictable (A-59). The upgrade tests use a workflow change that changes a skill and a reference, not only the baseline (A-59).
- Fixtures use obvious placeholders for any command with a value, never a real credential (ORQLET-SEC-003).
- `orqlet upgrade` does not stop on a pending proposal for a seeded file. When the new render differs, it rewrites the proposal diff (`src/orqlet/domain/changeplan.py:378-391`, and `src/orqlet/application/usecases/upgrade.py:140-148`, where only conflicts raise ORQ-W080). This was traced in the code and not run. It answers C-16 and the diff-file part of U-14. The rest of U-14 stays open: the lock entry of a shared file with broken markers, whether a command removes a diff after a manual merge, an upgrade with only a different CLI version, and why the role-bindings diff is empty. At 0.4.0 the regeneration phase therefore rewrites `.orqlet/proposals/.orqlet__versions.yaml.diff`, and `.orqlet/proposals/.orqlet__role-bindings.yaml.diff` if that render changes. It commits them as upgrade's output. It does not apply them to `.orqlet/versions.yaml` or `.orqlet/role-bindings.yaml`, which belong to the team and stay unchanged in this task. Its report says that applying the role-bindings proposal later changes reviewer independence, which the review-record validator derives from that file's approved bindings and model families (`src/orqlet/application/usecases/validate_records.py:306-326`).
- The three `.orqlet` lock files and the two proposal diffs change only through `orqlet upgrade`, and no other proposal file changes. `tests/conftest.py` keeps its refusal of `--update-golden` in CI.
- The change class is D3 because the design declares trust boundaries. The review of each implementation phase therefore needs independence I2: a reviewer in a different client or model family from the Coder (`src/orqlet/domain/independence.py:57-59`).

## Component diagram

```mermaid
flowchart TB
  subgraph pkg["src/orqlet/workflow (data, read-only)"]
    subgraph phase["research, design, plan, implement"]
      sk["skill.md<br/>purpose, Inputs, Boundaries, Steps,<br/>Output, Done when, If an input is missing or outdated, Next"]
      pc["references/phase-contract.md<br/>(four identical copies)"]
      fmt["references/*-format.md<br/>(research, design, plan)"]
    end
    subgraph other["review, onboard"]
      sk2["skill.md with the same sections"]
      rf["review-format.md"]
    end
    roles["roles/*.md<br/>inventory, tracer, tester,<br/>arch-reviewer, security-reviewer"]
    id["identity.json 0.4.0, MANIFEST.json"]
  end
  loader["load_skills / render_steps (unchanged)"]
  adapters["client adapters (unchanged)"]
  tests["tests: structure, two projects,<br/>upgrade, formats, goldens"]
  sk --> loader
  pc --> loader
  fmt --> loader
  sk2 --> loader
  rf --> loader
  roles --> adapters
  loader --> adapters
  id --> adapters
  tests -. pin .-> sk
  tests -. pin .-> pc
  tests -. pin .-> roles
  tests -. exercise .-> adapters
```

The loader attaches every `references/*.md` of a skill (A-2), so the new reference needs no code. Layer rule ORQLET-ARCH-003 holds: the workflow package stays data read by adapters and the interface.
