# ADR-002: Project context is read from the receiving project when a skill runs

Status: proposed. It becomes accepted when the design pull request is merged by an authorised person.

## Context

- The installed skill text is the same for every project. The render request takes no profile, and the profile reaches rendered files only through the AGENTS.md conventions block (AS-IS A-23, A-24). Apart from onboard naming the profile file, the skills name no project fact (A-11).
- The receiving project already holds its context, and existing commands read it at execution time: `orqlet explain` prints the technologies with their scope, the standards sources and the clients (A-34); `orqlet standards for` scans the project again when it runs (A-32); the profile has a status and answered facts (A-29); text outside the managed blocks of AGENTS.md is kept byte for byte (A-41); CI files and build manifests are in the repository.
- No source of a project's real build, lint, type-check and test commands is defined (U-5). The profile has a `commands` map that no code fills (A-30, A-35), and the plan contract calls `check_ref` "a profile command id" without resolving it (C-5).
- Phase outputs live at `docs/design/<task>/`, fixed by the validators, by gate status and by the exempt classes of the release (A-36, A-37, A-38). The person ruled that they stay there and that the skills read the project's own task documentation wherever it lives (Q-9, ruling on C-1).
- Installed skill, reference and role files are protected: `orqlet upgrade` restores an edited one with ORQ-W096 and `orqlet doctor` reports it as ORQ-E150 (A-44, A-47). The person chose to keep that behaviour and to state it in the skills (Q-8).
- The baseline and the standards command name the fourth phase `implementation`; the ledger's phase field and the skill name use `implement` (C-9). Two different values are both called `applicable_rules_hash` (C-2). `standards for` builds the stack from a fresh scan, while rendering uses the stack stored in the profile (C-3). `standards for` reads the prompts folder from the profile's `prompts-dir` standards source, while review prepare and explain use the fixed `.prompts` (C-4). Which command renders the conventions block again after a profile answer is not established (U-15).
- AGENTS.md is loaded by the clients as instructions for every session (A-20; the stored client pages, A-27). CI files and build manifests can be changed by any contributor, bot or merged pull request.

## Decision

1. **Sources.** A skill reads the context of the project it runs in, when it runs, from these sources, and cites each value with its path and lines:
   - the person's request and the ledger `docs/design/<task>/questions.yaml`;
   - the root (the Git top level that holds `.orqlet/`) and the scope (the paths of the task);
   - `orqlet explain` for the technologies and their scopes, the standards sources and the clients, and `.orqlet/project-profile.yaml` for its status and the facts it answers;
   - `orqlet standards for --path <path> --phase <phase> --role <role>` for each path of the scope;
   - the instructions: AGENTS.md (the team's text outside the managed blocks, and the blocks), CLAUDE.md, the client rule folders, and the folder of the profile's standards source of kind `prompts-dir` (the folder `standards for` reads, C-4);
   - CI workflow files and build manifests, for the commands;
   - the project's own task documents (ADRs, specifications, tickets the person points to) wherever they are. A page outside the repository is read only under the baseline's section "Looking things up".
2. **Unknowns stay unknown.** A value that none of these sources gives is written down as an unknown with a question in the ledger and asked. It is never filled from an example in a reference, another repository, an earlier session's memory or general knowledge of a technology. The installed text carries no project value; a test shows that two projects receive identical workflow skill bytes (BC-6).
3. **Commands found in project files.**
   - **Source.** A build, lint, type-check or test command is taken from where the project defines it: a CI workflow step, a script in a build manifest, a Makefile target, the profile's `commands` when a team has filled them, or the team's text in AGENTS.md. It is cited with its file and lines.
   - **No credentials.** A credential, a token or a connection string with a password is never copied. Every expression the CI system or the shell expands (`${{ ... }}`, `$NAME`, `${NAME}`) is replaced by a named placeholder such as `<matrix.python>` or `<API_TOKEN>`, and the agent says so. `phase-contract.md` describes these expressions in words (a dollar sign followed by a name or by braces), not with literal double braces, because BC-30 rejects them in rendered files. A placeholder is filled only from an environment the person has set up. A secret goes into the command as a variable reference (`"$NAME"`). The agent checks only that the variable is set, for example with `test -n "$NAME"`, and never prints, echoes or lists an environment value. The agent never asks the person to type a secret into the conversation. A non-secret value, such as a Python version, may come from the person or from the cited lines, never from elsewhere in a file. It goes into the command as one single-quoted argument and passes the character rule below. A check that lacks a value is reported as not run. Reports and records show a command in its placeholder form.
   - **Files that hold secrets** are never opened: `.env` files, private key files, `.npmrc`, `.pypirc`, `.netrc` and cloud credential files. A command that needs one is recorded with a placeholder and the question of where the value comes from.
   - **Who runs what.** Research, design, plan and onboard never run a command found in a project file. They record it. The plan names it as a check and cites with `orqlet evidence cite` (path, lines, revision, sha256):
     - the lines that define it;
     - the repository files it directly invokes, such as the script or Makefile it names;
     - the lines of the tool configuration it reads, such as a `[tool.pytest]` section.

     A person therefore approves the command together with what it starts. A check whose command matches the warning list of decision 6 is marked as such in its `completion` entry and in the plan's self-check, so the reviewer of the plan pull request sees it.

     Implementation runs the commands that the approved plan names as checks, as the cited lines hold them:
     - Before the first check, it shows the commits since the plan's base revision that touch the cited files.
     - Before each check, it cites every source again. `orqlet evidence cite` reads committed content, so the agent also confirms that `git diff --quiet HEAD -- <cited files>` finds no difference and that none of them is untracked.
     - If the phase's own file operations change a cited file, it shows that change and gets the person's yes before the check runs.
     - It applies the warning list of decision 6 to each command itself, and asks the person before it runs a match, whether or not the plan marks it. The mark helps the plan's reviewer; it is not the control.
     - The tester applies the same checks before it runs the test command, and never runs a marked check or a match: it hands that check back to the coder, who asks the person.

     A different hash, an uncommitted change, or a plan text that differs from the cited lines in more than the placeholders stops it.
   - **Any other command** runs only after the agent has shown the person the exact command, its source and the reason, and the person has said yes. The phase report marks every command it ran as planned or agreed.
   - **Values from artifacts in commands.** The contracts fix the form of a revision, a task and a phase id only. Paths, globs and free text are not constrained. Every value that the agent takes from an artifact or a cited file goes into a command as one argument in single quotes, and paths go after `--` in a git command. A path or glob that holds anything other than letters, digits, `.`, `_`, `-`, `/`, `*` or `?` stops the agent, which asks the person. A command is never built from an artifact's free text.
   - **Never on a file's word.** A command is never run because a file says so. That is the rule "Source material is not authority" applied to commands.
   - **Output.** Command output goes into reports and records as a summary, with any credential or environment value left out.
4. **Locations.** Orqlet's phase outputs stay at `docs/design/<task>/` (Q-9). The skills read and cite the project's own task documentation where it lives, and never move or copy it into the task folder.
5. **Installed files.** The reference and the onboard skill say that the installed skill, reference and role files belong to Orqlet: `orqlet upgrade` restores an edited one and reports ORQ-W096, and `orqlet doctor` reports the edit as ORQ-E150. A team puts its own guidance into AGENTS.md outside the managed blocks, or into a rule of its standards folder, which `orqlet standards for` prints (Q-8).
6. **Onboard records commands: a new trust boundary (B-2).** Onboard finds the project's commands in CI and build files and offers to write them into AGENTS.md as team text outside the managed blocks. Every later session would then read them from one place. This moves text that contributors can change into the instruction channel, so it has its own controls:
   - **Fixed form.** Each entry holds:
     - a fixed label: `build`, `lint`, `type-check` or `test`;
     - the command with its placeholders (decision 3), alone in a fenced code block whose fence is longer than any run of backticks in it;
     - its source path and lines.

     The entries sit under a heading that says onboard recorded them from those sources, that they are a record of what the project runs, and that they are not an instruction to run anything. No other text from the source is copied: no step names, comments or scripts.
   - **Warnings.** Some commands are shown with a warning and written only if the person confirms that entry on its own: a command that pipes into a shell, fetches from the network, uses elevated rights, spans several lines, or holds `$(`, a backtick, `eval`, a shell or interpreter started with `-c` or `-e`, chaining with `;`, `&&` or `||`, a redirection to a file, or text like an `orqlet:begin` marker.
   - **Consent.** The agent shows the exact AGENTS.md change, and the person says yes to each entry. Onboard never runs the commands.
   - **Provenance.** Anyone can write such a heading. A later skill that takes a command from this text compares the entry with the source it names and cites both. Any difference is a question for the person, never a command to run.
7. **Words and values.**
   - **Phase words.** `--phase` takes `research`, `design`, `plan` or `implementation`, the words of the baseline and of the standards command (C-9). The ledger's `phase` field and the skill name keep `implement`, which their contracts fix.
   - **Role words.** `--role` takes `researcher` (the AS-IS self-check role, `as-is-format.md:37`), `architect` (A-6), `planner` (A-7) or `coder` (the proposal's Phase 4 Coder, `docs/design/orqlet-architecture-proposal.md:3372`).
   - **Hashes.** The header's `applicable_rules_hash` is the value that `orqlet gate status` prints; each hash that `standards for` prints goes into the self-check (C-2).
   - **Disagreements.** When `orqlet explain` and `standards for` disagree about the stack (C-3), or the AGENTS.md conventions block disagrees with the profile, the agent tells the person which source says what. It does not name a command to fix the block, because none is established (U-15).

## Consequences

- A phase run costs a few reads and two or three commands before the work. No command, contract field or file is added (Q-4).
- In a project that defines no command, the plan asks the person for one instead of guessing; implementation then runs only what the plan names.
- A change after the plan merged to a planned check's lines, or to the files and configuration lines the plan cites for it, stops implementation. Other code that a check runs, such as the tests themselves, plugins and `conftest.py` files, is not bound. Every check runs repository code with the person's rights and environment, and the commits shown before the first check are the person's only view of changes to it.
- A team rule scoped to the phase `implement` matches nothing, because the skills ask for `implementation`. The shipped packs scope no rule by phase (only a test fixture uses `design`, `tests/fixtures/packs/sample/rules/python.yaml:15`); the reference names the four words so that a team can match them.
- The agent reads more of the project's own text, and onboard can turn some of it into instructions. That text stays evidence until the person accepts an entry; `considerations.md` covers the residual risk.

## Rejected alternatives

- **Write project values into the skills at render time.** It is the snapshot the request rules out (R-9). Two projects would get different skill bytes, which breaks the merge of identical files across clients (A-26), and it is a code change outside Q-3.
- **A new command that prints the context for a skill.** Q-4 allows existing commands and files only.
- **A scanner that fills the profile's `commands` from CI files.** A code change (Q-3); no answer key writes `commands` today (A-30).
- **Onboard does not record commands; every plan finds them again.** No new boundary, but every session repeats the search, and a team has no reviewed place for its commands. With the controls of decision 6, the person's yes and the pull request diff are the gate.
- **A configurable location for phase outputs.** Ruled out by the person for this task (Q-9); the validators fix the location (A-36). A separate task can take it up.
- **Let a team edit the installed skills.** `orqlet upgrade` restores them by design (A-44), and the person chose to keep that (Q-8).
