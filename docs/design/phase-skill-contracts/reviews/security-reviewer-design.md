# Security review of the design: phase-skill-contracts

Reviewer: `orqlet-security-reviewer`, started as a typed subagent in its own context. Input: the files under `docs/design/phase-skill-contracts/` (design set, AS-IS file, ledger), `src/orqlet/workflow/skills/orqlet-design/references/design-format.md` and the output of `orqlet standards for --phase design --role architect` and `--path` for the scope. Files the design cites were opened only to verify a citation.

## Round 1: FAIL

The reviewer's full output of round 1 was not saved. The findings below are the author's summary of it, with the reviewer's ids. Finding SEC-1 was blocking.

| Id | Finding (summary) | Author's response |
|---|---|---|
| SEC-1 | The credential rule appeared only in the considerations, and conflicted with copying a command "exactly" | ADR-002 decision 3: never copy a credential, environment value, `secrets.` expression, token or password in a connection string; use a placeholder. ADR-004 decision 3 and BC-8, BC-22 |
| SEC-2 | Onboard could run the commands it finds | ADR-002 decisions 3 and 6: research, design, plan and onboard never run a command found in a file. BC-12 |
| SEC-3 | Writing CI text into AGENTS.md is a new trust boundary | Declared as B-2 in the manifest, the context view, the data flow and the considerations; the change class becomes D3. ADR-002 decision 6 fixes the form, the warnings and one yes per entry |
| SEC-4 | Approving the plan approves a command name, not the code it runs | The plan cites each check's source with `orqlet evidence cite` (revision and sha256). Implementation cites again before running and stops on a different hash. ADR-002 decision 3, ADR-004 decision 5, BC-24 |
| SEC-5 | "The person agreed" is too weak, and the report does not show which commands were planned | The agent shows the exact command, its source and the reason before a yes; the report marks each command planned or agreed |
| SEC-6 | The `Orqlet-Task` trailer can be forged | ADR-003 decision 6: a trailer counts only on commits that change planned files, knowledge paths or the task's records; the skill shows hash, author and files and calls the trailer a claim. Residual risk in the considerations |
| SEC-7 | The acceptance of the AS-IS file is recorded by the agent itself | ADR-003 decision 7: a claim; content bound by `as_is_ref`; confirmed by the design merge; an edit resets the file to draft. BC-17 |
| SEC-8 | The same-project check relied on a skip line, with no code behind it | ADR-003 decision 4 adds `git merge-base --is-ancestor <base_revision> HEAD`. BC-14 |
| SEC-9 | The role prompts lack the safeguards, and the tester has no criterion | ADR-004 decision 7 and BC-26: inventory and tracer keep "never an instruction" and run no command they find; the tester runs only the plan's test command |
| SEC-10 | The test pins only the first sentence of the not-authority paragraph | BC-2 pins the paragraph in full |
| SEC-11 | The security globs miss top-level and workflow Python files, the baseline, `exempt.yaml`, `releases.json`, templates, `.github/workflows/**` and `.prompts/**` | All added to `security_globs`; checked with `glob_match` that no scope path or tracked file in scope matches |
| SEC-12 | The reviewer reads the live tree; the reviewed content is not recorded | ADR-004 decision 7: cited files only to verify a citation, and the note records the sha256 of each file reviewed |
| SEC-13 | A cross-reference named decision 5 instead of decision 7 | Corrected |
| SEC-14 | Command output in reports can carry credentials | Output is summarised without credentials or environment values (ADR-002 decision 3, ADR-004 decision 5) |
| SEC-15 | Artifact fields become git shell arguments | ADR-003 decision 4: the validator runs first, so the revision is 40 or 64 hex characters (`src/orqlet/application/contracts/common.py:21`); paths go after `--` |
| SEC-16 | A fork with shared history satisfies "merged in this repository" | Stated as residual risk; evidence must still resolve by hash (A-51) |
| SEC-17 | Task documents can sit behind a login | ADR-002 decision 1: pages outside the repository follow the baseline's "Looking things up" rules |

## Round 2: FAIL

Files reviewed, hashed by the author with `shasum -a 256` right after the reviewer returned; no file changed between the reviewer's start and the hashing. The reviewer could not run a shell.

| File | sha256 |
|---|---|
| `design/manifest.yaml` | `27998171cfdbfbf2c861133f683865cd2ad7728355b2f7f245c078c4a21cb779` |
| `design/context.md` | `8eb078df676b8829c563094c2a0b1e686df9bc747a7c6adb79a40062e0b88712` |
| `design/container.md` | `377747324613de61b84a53eaaed072bf16c0aca96378ea8104b6b3064ce98e8d` |
| `design/component.md` | `8accf697b7a60ede9d3a9435458dbbd29f183afe6e7bc350d2b724f875cb44b5` |
| `design/data-flow.md` | `67bfe10fa0e11f897ec8d021333ad1513b12d50ab004d1070b3837a55150da4c` |
| `design/sequence.md` | `5ebbda184ba6e28a01767285676952ca8b3f1fd67fbd64e3ca69ef59b06d7f7f` |
| `design/considerations.md` | `31f4d93c34a3d92580f38ee7a53088d4abafa437756bcd061e8f636e55aa67f8` |
| `design/adr-001-one-contract-shape-for-every-skill.md` | `ed1630c2ce902055b363344f1465b19b20fbfad3117966e38ab62cdd7a6b5d95` |
| `design/adr-002-project-context-read-at-execution-time.md` | `93ae05b73816566801a1199dcc2833f1477654321dbe7f53f450990647ebbce2` |
| `design/adr-003-handoffs-and-the-input-check.md` | `03ebac2d73b271bef54152ee7169cc53d6ff6c47a81c46c25fb1923ddc94c3a2` |
| `design/adr-004-what-each-phase-produces.md` | `be49e1238143bec084bc7282de7af15313b343d9f5981debc3895b23131bc2a5` |
| `design/adr-005-injection-unchanged-tests-and-version.md` | `1bf6b95bc78bccb0f3f6b18a03425a33a4e288b86a306be123f06f32a902ded0` |

### The reviewer's output, unchanged

```yaml
round: 2
verdict: FAIL
reviewed_files:
  - {path: docs/design/phase-skill-contracts/design/manifest.yaml, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/context.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/container.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/component.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/data-flow.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/sequence.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/considerations.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-001-one-contract-shape-for-every-skill.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-004-what-each-phase-produces.md, sha256: not computed}
  - {path: docs/design/phase-skill-contracts/design/adr-005-injection-unchanged-tests-and-version.md, sha256: not computed}
round_1_resolution:
  - {id: SEC-1, resolved: yes, note: "adr-002:28 never copies a credential and uses a placeholder; adr-004:29 and BC-8 (component.md:100) and BC-22 (component.md:137) agree; the conflict with copying a command 'exactly' is gone. Reading secrets and running a command that holds a placeholder are open, see SEC2-7"}
  - {id: SEC-2, resolved: yes, note: "adr-002:29 and :38; BC-12 (component.md:111-116); considerations.md:14"}
  - {id: SEC-3, resolved: yes, note: "B-2 is declared in manifest.yaml:36, context.md:41,46, data-flow.md:41-53 and considerations.md:9; the class is D3 (manifest.yaml:15-18). How the form is sanitised is open, see SEC2-8"}
  - {id: SEC-4, resolved: partly, note: "The plan cites the source and implementation cites it again (adr-002:29, adr-004:36, sequence.md:74-78, BC-24). The hash binds only the cited lines and never the plan file itself, see SEC2-2 and SEC2-5"}
  - {id: SEC-5, resolved: yes, note: "adr-002:30; adr-004:41; BC-8 (component.md:103-104)"}
  - {id: SEC-6, resolved: partly, note: "adr-003:46 makes the trailer a claim and limits which files the commit may change. The residual relies on a CI check that does not exist (SEC2-6); the author is shown as a signal but is forgeable (SEC2-9); 'the task's own records' can be read as covering plan.yaml (SEC2-2)"}
  - {id: SEC-7, resolved: yes, note: "adr-003:53; BC-17 (component.md:127); the residual is stated in considerations.md:20"}
  - {id: SEC-8, resolved: yes, note: "adr-003:40 and BC-14 (component.md:120); bound.base_revision is a GitOid (artifact_header.py:29, common.py:21)"}
  - {id: SEC-9, resolved: partly, note: "adr-004:50-51 and BC-26 cover inventory and tracer. For the tester, considerations.md:14 contradicts adr-004:51, and the tester has no re-cite, see SEC2-11"}
  - {id: SEC-10, resolved: yes, note: "BC-2 (component.md:77) pins the full paragraph; today's test pins only its first sentence (test_skills.py:50,136)"}
  - {id: SEC-11, resolved: yes, note: "Every item named in round 1 is in manifest.yaml:47-64. Checked against the listing of src/orqlet/workflow: every file outside skills/, roles/, identity.json and MANIFEST.json matches a glob, and no tracked file in scope matches one. Other surfaces are unwatched, see SEC2-4"}
  - {id: SEC-12, resolved: partly, note: "adr-004:52 and BC-25 record the hashes, but no step compares them with the manifest, the note may be the author's summary (reviews/security-reviewer-design.md:7), and a reviewer without a shell cannot compute them, as in this round. See SEC2-10"}
  - {id: SEC-13, resolved: yes, note: "The reviewer references now name ADR-004 decision 7 (component.md:142-143); a grep of every 'ADR-00n decision n' in the design set found no wrong number"}
  - {id: SEC-14, resolved: yes, note: "adr-002:32; adr-004:47; BC-8 (component.md:106). Which form of the command the report shows is open, see SEC2-7"}
  - {id: SEC-15, resolved: partly, note: "The revision, task and phase id are constrained (common.py:21-22; artifact_header.py:29,47; plan.py:36). Scope globs, plan operation paths and the free-text completion entries are not, and '--' does not stop shell expansion, see SEC2-1"}
  - {id: SEC-16, resolved: yes, note: "Stated as residual risk in adr-003:59 and considerations.md:22"}
  - {id: SEC-17, resolved: yes, note: "adr-002:24 sends pages outside the repository through the baseline's 'Looking things up' rules"}
findings:
  - id: SEC2-1
    severity: major
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:37,46; sequence.md:24; adr-002-project-context-read-at-execution-time.md:21; adr-004-what-each-phase-produces.md:32,36; considerations.md:23
    finding: "The agent pastes artifact values into shell commands it composes itself: 'git log <base>..HEAD -- <scope paths>', 'orqlet standards for --path <path>' and 'orqlet evidence cite <path> <lines>' (the path comes from a free-text completion entry). The contracts allow shell metacharacters in those values. Putting paths after '--' prevents option injection only, not command substitution. An artifact written by a contributor, or by an earlier session that was misled, can therefore run code in the person's shell. This can happen during the input check, including when research resumes an AS-IS file nobody has accepted, and on every stale input."
    evidence: "common.py:38-43: a Glob rejects only an empty value, a leading '/', '\\' and '..', with no control-character check, so a newline passes. paths.py:30-48: a RepoPath allows $ ` ; | & ' \" ( ) and spaces. as_is.py:61 and design_set.py:46: scope paths are Glob. plan.py:23: operation paths are RepoPath. plan.py:46: completion is free Text. considerations.md:23 claims the validator makes these values safe. The codebase already has the fix: onboard skill.md:16 'with each value in single quotes (if a value holds a single quote, ask the person for another value)'."
    required_change: "In phase-contract.md (Input check) and in the implement steps: pass every value taken from an artifact as one single-quoted argument. Stop and ask when a path or glob holds anything other than letters, digits, '.', '_', '-', '/', '*' or '?'. Never build a command from free text in an artifact. Correct adr-003:37 and considerations.md:23 to say that only the revision, task and phase id are constrained. Add a BC that tests this text is present."
  - id: SEC2-2
    severity: major
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:41-42,45-50; data-flow.md:39; component.md:121-126
    finding: "After the person confirms the merge, nothing checks that the plan or design in the working tree is the approved one. gate status scopes a plan by its operation paths only. A later commit that edits only plan.yaml therefore leaves the plan current (ORQ-I392) and never appears in decision 6's commit list. Decision 6 also counts commits that change 'the task's own records under docs/design/<task>/' as planned work, which an agent can read as including plan.yaml and design/. The proposal's row 'Editing the approved design or plan: invalid' is not among the causes the design maps. Implementation runs the plan's checks without a further yes, and the re-cite compares with a hash stored in that same plan. An edited plan can therefore add or change commands that run with the person's rights. This is a stale approval used as valid (W-5)."
    evidence: "gate_status.py:188-191 (a plan's scope is its operation paths); gate_status.py:222-229 (ORQ-I392, not stale, when no file in scope changed); A-51 (validate plan checks design_ref only); A-37 (records are reviews/, tests/ and knowledge/); orqlet-architecture-proposal.md:3073; adr-002:29."
    required_change: "Add to the Approved and Current checks: the person names the merge commit. 'git log <merge>..HEAD -- docs/design/<task>/plan.yaml docs/design/<task>/design docs/design/<task>/as-is.md' must print nothing; otherwise map the change to the 'editing the approved design or plan' row (invalid, a new approval is needed) and stop. In decision 6 and BC-15, name the record folders exactly (reviews/, tests/, knowledge/, evidence/web/) and add that row."
  - id: SEC2-3
    severity: major
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:47; adr-005-injection-unchanged-tests-and-version.md:35
    finding: "Decision 6 treats any difference in workflow_version or protected_set_digest as 'a newer accepted workflow version; approval valid'. But protected_set_digest also changes without any workflow change: a resource registry change, a conventions-block change from the profile, or a change of enabled clients. With an unchanged workflow_version that row does not apply. Under the design's own last bullet (adr-003:50), such a cause cannot be matched and must stop. As written, the agent tells the person the approval is valid. That relaxes W-5, while adr-005:35 says no W element is relaxed."
    evidence: "gate_status.py:70-77 (the digest covers every protected lock entry); resources_view.py:135 (resource rules are protected); A-22 (every skill is protected); A-25 (the registry adds skills and rules); A-24 (the conventions block comes from the profile)."
    required_change: "Apply the upgrade row only when the header's workflow_version is older than the current one. A protected_set_digest difference with an equal workflow_version goes to the 'cannot match: stop and ask' bullet. Update BC-15 to match."
  - id: SEC2-4
    severity: major
    where: docs/design/phase-skill-contracts/design/manifest.yaml:28-32,46-64,184; component.md:152
    finding: "The scope lists .orqlet/** and the whole client folders, while Q-3 and Q-7 need only the files orqlet upgrade regenerates. The scope therefore includes, and no security glob watches, files that govern this design's own controls: (1) .orqlet/role-bindings.yaml decides whether a reviewer binding is approved, and so I0, I1 or I2, the independence these D3 phases need. (2) .orqlet/resources.yaml holds the access: login entries that allow a signed-in browser session. (3) .orqlet/project-profile.yaml holds the standards sources. (4) Client permission, hook and MCP files (.claude/settings*.json, .cursor/hooks.json, .cursor/mcp.json, .codex/config.toml, root .mcp.json) can remove the per-command yes. Outside the scope, the check settings in pyproject.toml (--disable-socket, mypy, import-linter) are watched only as a dependency manifest. A change to any of these during implementation raises no ORQ-E451."
    evidence: "expected_change.py:85-87 (ORQ-E451 fires only for changed files on a security glob); validate_records.py:307-317 and independence.py:41-59 (role bindings decide independence); a listing of .orqlet/ shows role-bindings.yaml, resources.yaml and project-profile.yaml; baseline.md:29; pyproject.toml:62,69-71,82; the self-check at manifest.yaml:184 claims coverage only of the surfaces it lists."
    required_change: "Narrow .orqlet/** to the files that 'orqlet upgrade --dry-run' shows it writes here. Add to security_globs: .orqlet/role-bindings.yaml, .orqlet/resources.yaml, .orqlet/project-profile.yaml, every seeded .orqlet file that upgrade does not write, the client config paths above, .mcp.json and pyproject.toml. Run the glob_match no-overlap check again, and extend BC-33 to name these surfaces."
  - id: SEC2-5
    severity: major
    where: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md:50; considerations.md:14
    finding: "The re-cite binds only the cited lines. It does not bind the code a check runs: the script or Makefile recipe it calls, test files, conftest.py, pytest addopts or plugins. A change to that code outside the task's scope does not even make the input stale. adr-002:50 still says a contributor's change 'stops implementation, instead of running unreviewed code'. The residual risk names only a person approving a harmful command, although every check runs repository code with the person's rights and environment."
    evidence: "evidence_cite.py:58-64 (the hash covers the given range only); gate_status.py:214-229 (a base move counts only for files in scope); A-35 (this repository's checks run tools configured in pyproject.toml:38-127)."
    required_change: "Correct adr-002:50 to describe what the control actually does. Add the indirect-code residual to considerations.md:14. In ADR-002 decision 3, make the plan also cite, by hash, the repository files that the command directly invokes, and make implementation show the commits since the plan's base that touch them before the first check."
  - id: SEC2-6
    severity: major
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:58; considerations.md:18
    finding: "Two residual-risk statements rely on a control this release does not have: 'CI compares the final diff with the plan's operations at the pull request' and 'CI decides at the pull request'. The release has no ci command, and this repository's CI runs only lint, types, architecture, tests and build. The proposal places that check in 'orqlet ci check' stage 2, which is not implemented. For a forged trailer and for a stale approval, the only backstop is the person's review of the merge."
    evidence: "capabilities.py:14-47; .github/workflows/ci.yml:18-107; orqlet-architecture-proposal.md:3980; considerations.md:43 ('No new command, CI step')."
    required_change: "State that no CI check compares the diff with the plan or decides an approval in this release, and that the person's merge review is the only gate. Record that as the residual risk."
  - id: SEC2-7
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md:28,32; adr-004-what-each-phase-produces.md:29,41; sequence.md:78
    finding: "The credential rule covers copying only. It does not say how a planned check whose command now holds a placeholder is run: the agent may ask the person to paste the secret or recover it from the CI file. It does not say which form of the command the report shows. It does not say not to open files that exist to hold secrets (.env*, key files, .npmrc or .pypirc with tokens); reading them sends their content to the model vendor. 'Environment value' is not defined, so it is unclear whether it covers expressions such as ${{ matrix.python }} (ci.yml:83). baseline.md:31 covers credentials only for lookups."
    evidence: "adr-002:28,32; adr-004:41 ('each with its command'); sequence.md:78; baseline.md:31."
    required_change: "In phase-contract.md: a placeholder is filled only from an environment the person has set, and the secret is never typed into the conversation. A check that lacks a value is reported as not run. Reports show the command in its placeholder form. Secret-bearing files are never opened. Define which CI expressions count as placeholders. Extend BC-8."
  - id: SEC2-8
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md:36-39; considerations.md:15; data-flow.md:53
    finding: "The fixed form does not say how the command is quoted in Markdown. A one-line command that contains backticks or a fence can end its code span and leave free text in AGENTS.md, which later sessions load as instructions. The warning list leaves out $() and backticks, eval, sh -c and interpreter -c, chaining with ; && ||, and redirection to files. Anyone can write the heading 'onboard wrote it', and a later skill does not compare an entry with its named source."
    evidence: "adr-002:36-39; context.md:46."
    required_change: "Put each command in a fenced block whose fence is longer than any backtick run in it, or refuse such commands. Add the missing patterns to the warning list. Make the heading say the entries are a record, not an instruction to run them. Have a later skill compare the entry with the cited source and treat any difference as a question. Extend BC-12."
  - id: SEC2-9
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:46,58; considerations.md:19
    finding: "The commit author shown to the person is free text, like the trailer, but the design presents it as what the person can rely on."
    evidence: "adr-003:58 ('The person sees its author and files'); considerations.md:19."
    required_change: "Call the author a claim as well. Show the signature status (git log --format='%H %G? %an %s') where the project signs its commits, and add this to the residual risk."
  - id: SEC2-10
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-004-what-each-phase-produces.md:52; component.md:142; src/orqlet/workflow/skills/orqlet-design/skill.md:18
    finding: "The reviewer records hashes, but no step compares them with the manifest before the merge. A reviewer without a shell cannot compute them, as in this round. The design skill saves the 'findings', and the round-1 note is the author's summary, so the author can alter what a reviewer said."
    evidence: "reviews/security-reviewer-design.md:7 ('The reviewer's full output of round 1 was not saved'); design skill.md:18."
    required_change: "Have the design skill run 'orqlet evidence hash' on the design files when it starts each reviewer and again when it saves the note. Save the reviewer's output unchanged, with the author's responses in a separate section. Start a new round when any hash differs from the manifest. Cover this text in BC-25."
  - id: SEC2-11
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-004-what-each-phase-produces.md:51; component.md:143; considerations.md:14
    finding: "considerations.md:14 says the tester never runs a command found in a file. adr-004:51 and BC-26 say it runs the test command the plan names, which was itself found in a file. The tester gets no re-cite, and its prompt asks it to report the commands it ran."
    evidence: "orqlet-tester.md:14; adr-002:29 (re-cite before each run)."
    required_change: "Either the tester runs no project command and the coder runs the test check after re-citing it, or the tester prompt carries the same re-cite rule. Align considerations.md:14 with the choice."
not_verified:
  - "No sha256 was computed (shell refused in read-only mode). The hashes recorded at manifest.yaml:71-116 and :181 were not checked."
  - "To test SEC2-1, SEC2-3 and SEC2-4 I opened files outside the design's citations: paths.py, design_set.py:46, as_is.py:61, validate_records.py:307-317, expected_change.py:53-102, change_class.py:97-99, instructions.py:40-68, and directory listings of .orqlet/, .claude/, .cursor/, .codex/, .github/ and src/orqlet/workflow/. Re-check that evidence if it falls outside the agreed input."
  - "Glob listings may omit gitignored files, so it is not known whether local client settings files exist."
  - "'orqlet upgrade --dry-run' was not run, so the exact .orqlet files that upgrade writes are not known."
  - "Whether each client asks before every shell command (U-11) was not examined. It affects how easily SEC2-1 and SEC2-2 can be exploited."
  - "The proposal was read only at lines 3050-3084, 3368-3377 and 3980. The architecture review note, the fragments and evidence/web/cursor-skills.md were not read."
  - "No test, validator or command was run."
```

The reviewer added: "I found no credential, token or certificate in any file I read, so no credential rule needed applying."

### Author's responses to round 2

| Id | Response |
|---|---|
| SEC2-1 | ADR-002 decision 3, "Values from artifacts in commands": every value from an artifact is one single-quoted argument, with paths after `--`. A path or glob with a character outside letters, digits, `.`, `_`, `-`, `/`, `*` and `?` stops the agent, and no command is built from an artifact's free text. ADR-003 decision 4 and `considerations.md` say that only the revision, task and phase id are constrained. New BC-40 |
| SEC2-2 | ADR-003 decision 4, *Approved*: the person names each approval's merge commit, which must be an ancestor of HEAD. `git diff --quiet <merge> -- <approved files>` checks the working tree against it. A difference maps to "editing the approved design or plan" (proposal:3073), and the skill stops for a new approval. Decision 6 names the record folders exactly, and a commit touching `as-is.md`, `design/`, `plan.yaml` or `questions.yaml` is never planned work. New BC-39 |
| SEC2-3 | The upgrade row applies only when the header's `workflow_version` is older than the installed one. A digest change without it stops and asks. BC-15 |
| SEC2-4 | The scope holds only the files upgrade writes: every non-seeded path of `.orqlet/generated.lock.yaml`, by client subfolder, and the three `.orqlet` lock files. New security globs: the seeded `.orqlet` files (profile, resources, role bindings, versions, knowledge), `.orqlet/proposals/**`, `.claude/settings*.json`, `.cursor/hooks.json`, `.cursor/mcp.json`, `.codex/config.toml`, `.mcp.json`, `pyproject.toml` and `uv.lock`. Checked with `glob_match`: no scope path and none of the 415 tracked files in scope matches a security glob, and every non-seeded lock path is in scope. BC-33 names these surfaces |
| SEC2-5 | ADR-002 decision 3: the plan also cites the files the command directly invokes and the configuration lines it reads. Implementation shows the commits since the plan's base that touch them before the first check, and re-cites all of them before each check. ADR-002 Consequences and `considerations.md` state the residual: tests, plugins and `conftest.py` files are not bound, and checks run repository code with the person's rights |
| SEC2-6 | ADR-003 Consequences and `considerations.md` state that no CI check in this release compares the diff with the plan or decides an approval (`src/orqlet/interface/cli/app.py:36-51` registers no `ci` command; `ci.yml:18-107`), and that the person's review of the pull request is the only gate |
| SEC2-7 | ADR-002 decision 3: every `${{ ... }}`, `$NAME` or `${NAME}` becomes a named placeholder. Placeholders are filled only from an environment the person has set up, and no secret is asked for in the conversation. A check without its value is reported as not run, and reports show the placeholder form. Files that hold secrets are never opened. BC-8 |
| SEC2-8 | ADR-002 decision 6: the command sits alone in a fenced block whose fence is longer than any backtick run in it. The warning list now includes `$(`, backticks, `eval`, `-c` and `-e` interpreters, `;`, `&&`, `||` and redirection. The heading says the entries are a record, not an instruction. A later skill compares an entry with its source, and a difference is a question. BC-12 |
| SEC2-9 | ADR-003 decision 6 shows the signature status (`%G?`) and calls the author a claim, and the residual says so |
| SEC2-10 | ADR-004 decision 7 and BC-25: the design skill hashes the design files when it starts each reviewer and when it saves the note. It saves the reviewer's output unchanged with its responses apart, and starts a new round when a hash differs from the manifest's. Round 2 of this review is saved that way, with the hashes the author computed |
| SEC2-11 | The tester keeps running the plan's test command and carries the same re-cite rule (ADR-004 decision 7, BC-26). `considerations.md` no longer lists the tester among the roles that run nothing |

## Round 3: PASS

Files reviewed, hashed by the author with `shasum -a 256` before the reviewer started and again after it returned; both lists are identical and equal the table of the architecture note's round 3.

| File | sha256 |
|---|---|
| `design/manifest.yaml` | `017a04e2f03af365069119f13ec1be4d353bebab40f77cebae7f52d09659af09` |
| `design/context.md` | `8eb078df676b8829c563094c2a0b1e686df9bc747a7c6adb79a40062e0b88712` |
| `design/container.md` | `5fb05c776abe38a3cf98756c0482a161a03a6bd420dde5a97dce0ef39f3db45f` |
| `design/component.md` | `c603297fdd1ca0c04a4298b7c28a41227e6e53b22f32269405f876f91917bf2c` |
| `design/data-flow.md` | `322e216011039f126b8cba9e3add87515beef72a3df19b70c124c6011f528d18` |
| `design/sequence.md` | `648c3b6d8a9791bdfcf94df312f435d1329a58208568ee4431716d07f16cd85e` |
| `design/considerations.md` | `e0715b8ebd424feebfe6b8e2d9624ef1dd92fb14aa0f887d2f660d63e5c4d2b3` |
| `design/adr-001-one-contract-shape-for-every-skill.md` | `463ca10ed881f3477e0ac52cf6177d651088d818dd34a790423f71dfa5e34959` |
| `design/adr-002-project-context-read-at-execution-time.md` | `21383e7e872f8f34cf0399d3dae3f935d49e4275a8aeb459cefeee6eefd8897b` |
| `design/adr-003-handoffs-and-the-input-check.md` | `2c6a7fa441f2fad01cbc26069b97b0103105dbf61d9c47380e7050fe056ba6ef` |
| `design/adr-004-what-each-phase-produces.md` | `ed68e2bdd0055ee6e58adc916fe1fb0f00216363edf7729f3d67758bb7208053` |
| `design/adr-005-injection-unchanged-tests-and-version.md` | `1bf6b95bc78bccb0f3f6b18a03425a33a4e288b86a306be123f06f32a902ded0` |
| `as-is.md` | `e1c968ac76ab29556a317fc45063c3f4e8849f627b8562b84549cba03189fd0f` |
| `questions.yaml` | `ebb6d3a685c75d3d2d0a7bc7708426b307658ec016268df01a6ff8ef109d92fa` |

### The reviewer's output, unchanged

```yaml
round: 3
verdict: PASS
round_2_resolution:
  - {id: SEC2-1, resolved: yes, note: "adr-002-project-context-read-at-execution-time.md:37 makes each artifact value one single-quoted argument, puts paths after '--', stops on any character outside the allowed set and builds no command from free text. adr-003-handoffs-and-the-input-check.md:37 and considerations.md:32 now say that only the revision, task and phase id are constrained (common.py:21-22). BC-40 is at component.md:128. A path that starts with '-' only reaches orqlet positional arguments (evidence.py:23-26), where it fails as an unknown option."}
  - {id: SEC2-2, resolved: yes, note: "adr-003:42-46: the person names the merge commit, the agent checks it is an ancestor of HEAD, and 'git diff --quiet <merge> -- <approved files>' must find no difference. A difference maps to the row 'editing the approved design or plan' (proposal:3073, verified). adr-003:51-56 names the record folders exactly (proposal:1039 and evidence_cite.py:27, verified) and says a commit touching as-is.md, design/, plan.yaml or questions.yaml is never planned work. BC-14 and BC-39 are at component.md:126-127; BC-15 is at component.md:129. The check still accepts whatever commit is named, misses untracked files and misses in-place ledger edits: see SEC3-1."}
  - {id: SEC2-3, resolved: yes, note: "adr-003:57 applies the upgrade row only when the header's workflow_version is older than the installed one. adr-003:60 sends a digest change without a newer version to stop-and-ask. BC-15 matches (component.md:133)."}
  - {id: SEC2-4, resolved: yes, note: "The scope is narrowed (manifest.yaml:19-41). Every file in the .orqlet listing is either one of the three lock files in scope or on a security glob (manifest.yaml:73-78). The client permission, hook and MCP files, pyproject.toml and uv.lock are watched (manifest.yaml:79-85). glob_match is anchored at the root (globs.py:8-21), so root-only patterns such as pyproject.toml and .mcp.json do not match fixtures or goldens under tests/**. By inspection, no scope glob overlaps a security glob. BC-33 is at component.md:162-170. Some control surfaces remain inside the scope: see SEC3-5."}
  - {id: SEC2-5, resolved: yes, note: "adr-002:30-35: the plan cites the files a check directly invokes and the configuration lines it reads, and implementation shows the commits that touch them before the first check. adr-002:62 and considerations.md:22 state that other code a check runs is not bound and that checks run with the person's rights. The re-cite reads committed content only: see SEC3-2."}
  - {id: SEC2-6, resolved: yes, note: "adr-003:69 and considerations.md:27-28 say that no CI check in this release compares the diff with the plan or decides an approval, and that the person's pull-request review is the only gate. app.py:36-51 registers no ci command (verified)."}
  - {id: SEC2-7, resolved: yes, note: "adr-002:28-29,39 and BC-8 (component.md:102-104,107): named placeholders filled only from the person's environment, no secret asked for in the conversation, a check without its value reported as not run, reports in placeholder form, secret files never opened. Non-secret values taken from the cited file are not checked: see SEC3-3."}
  - {id: SEC2-8, resolved: yes, note: "adr-002:43-51: a fence longer than any backtick run in the command, the extended warning list, a heading that says the entries are a record and not an instruction, and a later skill that compares each entry with its source. BC-12 is at component.md:115-122; considerations.md:23 matches."}
  - {id: SEC2-9, resolved: yes, note: "adr-003:50 shows the signature status (%G?) and calls the trailer and the author claims. considerations.md:28 and BC-15 (component.md:130-131) say the same."}
  - {id: SEC2-10, resolved: yes, note: "adr-004-what-each-phase-produces.md:53-57 and BC-25 (component.md:152) add hashing at the start of each review and when the note is saved, the reviewer output saved unchanged with responses kept apart, and a new round when a hash differs. Round 2 is saved that way (reviews/security-reviewer-design.md:30-176). considerations.md:30 states that the author still writes the note."}
  - {id: SEC2-11, resolved: yes, note: "adr-004:51 and BC-26 (component.md:153) give the tester the same re-cite rule as the coder. considerations.md:22 no longer lists the tester among the roles that run nothing."}
findings:
  - id: SEC3-1
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:42-47; sequence.md:32-36; considerations.md:26; component.md:126-127
    finding: "The edit check is anchored to whatever commit is named. The design does not stop the agent from finding the commit itself. It does not check that the named commit brought in the approved files. If the named commit is HEAD, or the latest commit that touched plan.yaml (which an agent may find with 'git log'), the diff is empty even though an approved byte changed after the real merge. Implementation then runs the edited plan's checks without a further yes. Two other gaps: 'git diff <commit>' does not list untracked files under design/, and a changed requirement is detected only when it is marked status: superseded, so an in-place edit of an answered question passes."
    evidence: "adr-003:43-44 checks only ancestry and 'git diff --quiet <merge> -- <approved files>'. proposal:3073 invalidates the approval on 'any byte of an approved file'. proposal:3074 makes any changed requirement invalid. adr-003:47 and question_ledger.py:25,49 detect only superseded answers. considerations.md:26 declares the wrong-commit residual."
    required_change: "In phase-contract.md and BC-14/BC-39: (1) The agent never chooses the merge commit. If the person does not know it, the agent lists the commits that changed the approved files (hash, parents, %G?, author, subject) and the person picks one. (2) Accept only a full hex id. Show its parents, subject and the approved files it changed, and stop if it changed none of them. (3) Stop on any untracked file under the approved paths. (4) Show 'git diff <merge> -- questions.yaml'. A changed value of a question that was already answered at the merge maps to the changed-requirements row and stops."
  - id: SEC3-2
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md:35; adr-004-what-each-phase-produces.md:36; sequence.md:90-94; considerations.md:22; component.md:106
    finding: "The re-cite before each check hashes the committed content at HEAD, not the working tree the check runs from. An uncommitted or untracked change to a cited script, Makefile or tool-configuration section passes the re-cite, and the changed code runs. Such a change can come from the person, a tool, or the agent's own edits during the phase, which are committed only at the end. The design says 'A different hash ... stops it' without this limit."
    evidence: "evidence.py:31 ('lines of a committed file'); evidence_cite.py:43-52 resolves HEAD and reads services.vcs.read_at(resolved, path)."
    required_change: "Before each check, also require 'git diff --quiet HEAD -- <cited files>' and no untracked file among them. If the phase's own file operations change a cited file, show that change and get the person's yes before the check runs. Alternatively, state in adr-002 Consequences and considerations.md:22 that the re-cite covers committed content only. Extend BC-8 and BC-24."
  - id: SEC3-3
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md:28,37
    finding: "A non-secret placeholder value 'may come from the person or the cited file', for example a CI matrix entry. When the value sits outside the cited lines, no hash binds it. The character rule does not cover it either, because that rule applies only to artifact values. A change to that value after approval reaches the shell inside an approved check without a stop. It appears only in the list of commits that touch the file (adr-002:35)."
    evidence: "adr-002:28 (the value may come from 'the cited file'); adr-002:37 (the character check covers values 'from an artifact' only); adr-002:31-33 (only the cited lines are hashed)."
    required_change: "A placeholder value taken from a file must come from the cited lines. It goes into the command as one single-quoted argument and passes the same character check. Otherwise the agent asks the person. Add this to BC-8."
  - id: SEC3-4
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md:35,49; adr-004-what-each-phase-produces.md:29; considerations.md:22; component.md:143-148
    finding: "Commands onboard only records in AGENTS.md get the warning list ($(, backticks, eval, -c or -e interpreters, chaining, redirection, network fetches, elevated rights). Plan checks get no such flag, although implementation runs them without a further yes. The declared residual is a person approving a harmful command in a plan without reading it. A flag in the plan is the cheap control that would reduce it."
    evidence: "adr-002:49 (warnings apply to onboard entries only); adr-002:35 (approved checks run as the cited lines hold them); considerations.md:22 (residual)."
    required_change: "plan-format.md: a check whose command matches the warning list of ADR-002 decision 6 is marked as such in its completion entry and in the plan's self-check, so the reviewer of the plan pull request sees it. Implementation asks the person before it runs a marked check. Extend BC-22."
  - id: SEC3-5
    severity: minor
    where: docs/design/phase-skill-contracts/design/manifest.yaml:24,38-40; considerations.md:13; component.md:161-170
    finding: "Several control surfaces are inside the scope, where no security glob can watch them: (1) .orqlet/generated.lock.yaml, which holds the file classes and hashes behind ORQ-W096 and ORQ-E150 and the protected-set digest; (2) .orqlet/standards.lock.yaml, the source of standards_lock_hash and applicable_rules_hash; (3) .orqlet/workflow.lock; (4) tests/conftest.py, which refuses --update-golden in CI (the ORQLET-DET-001 control). A hand edit to any of them raises no ORQ-E451, and BC-32 checks only doctor findings. Separately, considerations.md:13 says 'The scope holds only the files that orqlet upgrade writes'. That is true only of the installed files: the scope also holds tests/**, README.md and the workflow sources."
    evidence: "gate_status.py:70-77,85-92 (the bound values and the digest come from these lock files); tests/conftest.py:34-39; expected_change.py:85-87 (ORQ-E451 fires only for files on a security glob)."
    required_change: "Add a plan constraint and a BC: (1) the three lock files change only through 'orqlet upgrade', shown for example by 'orqlet upgrade --check' reporting nothing after regeneration and 'orqlet doctor' reporting nothing; (2) the CI refusal in tests/conftest.py stays unchanged (or add tests/conftest.py to security_globs if the plan does not change it). Name these surfaces in BC-33 as review items. Reword considerations.md:13 to say 'of the installed files'."
not_verified:
  - "I did not compute sha256 hashes; the author hashes the files."
  - "Whether orqlet validate design or the skills ignore files under design/ that the manifest does not list. This decides how much the untracked-file gap in SEC3-1 matters."
  - "Whether the ledger's key field or 'orqlet validate ledger' detects an in-place edit of an answered question (SEC3-1, part 4)."
  - "Whether 'orqlet upgrade --check' or 'orqlet doctor' detects a hand edit of the three lock files (SEC3-5)."
  - "Client configuration files other than those the manifest names (for example Cursor CLI permission or environment files, or VS Code tasks). I did no web lookup. Glob found none in this repository but may omit gitignored files."
  - "Whether each client asks before every shell command (U-11)."
  - "The agent's raw git commands (merge-base, diff, log with %G?) run with the person's git configuration, not the hardened GitRunner overrides of ORQLET-SEC-001. I did not assess exposure through a hostile local configuration (core.fsmonitor, core.pager, gpg.program). Contributors cannot change that configuration through commits."
  - "Single quotes do not quote in Windows cmd.exe. There, the character rule is the protection. I did not examine each platform's shell."
  - "To verify citations and test findings, I opened files outside the design's own citations: evidence.py (the CLI), globs.py, tests/conftest.py, .gitattributes, test_skills.py:425-504, the front matter of the role files (grep), .codex/agents/orqlet-security-reviewer.toml, and the as-is.md entries A-37, A-41, A-44, A-46 and A-51 (grep). Please re-check that evidence if it falls outside the agreed input."
  - "I did not read the fragments, evidence/web or the architecture reviewer's note."
  - "I ran no test, validator or command."
# Credential rules: I found no credential, token or certificate in any file I read, so the credential and certificate rules needed no further action.
```

### Author's responses to round 3

| Id | Response |
|---|---|
| SEC3-1 | ADR-003 decision 4, *Approved*. The agent never chooses the merge commit; it may list candidates (`git log --format='%H %P %G? %an %s'` on the approved files). Only a full hex id is accepted, and the agent shows its parents, subject and approved files. It stops if the commit changed none of them (`git diff --quiet <merge>^1 <merge>`) or is not an ancestor of HEAD, and on any untracked file under the approved paths. The ledger is compared with `git diff <merge> -- questions.yaml`, so an answer changed in place stops too. BC-14, BC-39 and the residual in `considerations.md` |
| SEC3-2 | ADR-002 decision 3 and ADR-004 decision 5: before each check, `git diff --quiet HEAD -- <cited files>` must find nothing and none may be untracked. A change by the phase's own operations to a cited file needs the person's yes. BC-8, BC-24 |
| SEC3-3 | A non-secret placeholder value comes only from the person or the cited lines, is one single-quoted argument and passes the character rule. BC-8 |
| SEC3-4 | A plan check that matches the warning list is marked in its `completion` entry and in the plan's self-check, and runs only after a yes. ADR-002 decision 3, ADR-004 decisions 3 and 5, BC-22 |
| SEC3-5 | BC-33 has two review items: the three `.orqlet` lock files change only through `orqlet upgrade`, and the CI refusal in `tests/conftest.py:34-39` stays unchanged. Both are also plan constraints. BC-32 adds `orqlet upgrade --check` reporting nothing after regeneration. `considerations.md` says "of the installed files" |

## Round 4: PASS

Files reviewed, hashed by the author with `shasum -a 256` before the reviewer started and again after it returned; both lists are identical.

| File | sha256 |
|---|---|
| `design/adr-001-one-contract-shape-for-every-skill.md` | `463ca10ed881f3477e0ac52cf6177d651088d818dd34a790423f71dfa5e34959` |
| `design/adr-002-project-context-read-at-execution-time.md` | `8b25e824ee5c807d8ae9e0df0f531df68a72a162575da045e1bdecdc8c81e370` |
| `design/adr-003-handoffs-and-the-input-check.md` | `e6b6d8968578196b8a0b044a7212559866e035db6cbdc51c54056f7cd30e94a7` |
| `design/adr-004-what-each-phase-produces.md` | `c4abffa747f6ff9681d56e6ed9411870b2a5f9e6b28c9e65ce3190bef729081a` |
| `design/adr-005-injection-unchanged-tests-and-version.md` | `ab6fbf67e835b0a2f36178750198f70fd5ca24e9969d86ae1350c7d9fbe3a2cb` |
| `design/component.md` | `40b05c15fbcc8f19efc748f6cfa735be4648417e7055dd0a45a8cee8d66fd9b8` |
| `design/considerations.md` | `c7e0e206804aa4f132e80f2996f9fb3be75e34d6338eb1e1d4f02eab1b36c261` |
| `design/container.md` | `5fb05c776abe38a3cf98756c0482a161a03a6bd420dde5a97dce0ef39f3db45f` |
| `design/context.md` | `8eb078df676b8829c563094c2a0b1e686df9bc747a7c6adb79a40062e0b88712` |
| `design/data-flow.md` | `322e216011039f126b8cba9e3add87515beef72a3df19b70c124c6011f528d18` |
| `design/sequence.md` | `693e7b3ddafbb3c4da35f986024fda4640147fda3fc7fa863535ffea18a3ed24` |
| `design/manifest.yaml` | `dea90dd8ce26be3f5a4c40539be9d060ca5d91c393fdc7b206217abefb208941` |
| `as-is.md` | `e1c968ac76ab29556a317fc45063c3f4e8849f627b8562b84549cba03189fd0f` |
| `questions.yaml` | `ebb6d3a685c75d3d2d0a7bc7708426b307658ec016268df01a6ff8ef109d92fa` |

### The reviewer's output, unchanged

```yaml
round: 4
verdict: PASS
round_3_resolution:
  - {id: SEC3-1, resolved: yes, note: "adr-003-handoffs-and-the-input-check.md:43: the person names the commit, and the agent may only list candidates (%H %P %G? %an %s). adr-003:44: only a full hex id is accepted, its parents, subject and approved files are shown, and the skill stops when `git diff --quiet <merge>^1 <merge>` finds no difference or the ancestor check fails. adr-003:45: untracked files are found with `git ls-files --others --exclude-standard`. adr-003:50: `git diff <merge> -- questions.yaml`, where a changed answer or a supersession stops the skill. BC-14 and BC-39 match (component.md:127-128). The residual is at considerations.md:26. Gaps that remain: error exit statuses (SEC4-3), no check that the commit is on the protected branch (SEC4-2), and ledger changes other than a changed answer or supersession (SEC4-4)."}
  - {id: SEC3-2, resolved: yes, note: "adr-002-project-context-read-at-execution-time.md:39-40,43 and adr-004-what-each-phase-produces.md:36 add three things: `git diff --quiet HEAD -- <cited files>`, no untracked cited file, and a yes when the phase's own operations change a cited file. BC-8 (component.md:107) and considerations.md:22 say the same. evidence_cite.py:43-52 confirms that cite reads committed content at HEAD, so the new check closes the gap for the coder. sequence.md:97-99 leaves the check out without listing it among the omissions at sequence.md:3-10 (cosmetic). The tester's criterion does not carry the check: see SEC4-5."}
  - {id: SEC3-3, resolved: yes, note: "adr-002:28: a non-secret value comes only from the person or the cited lines, never from elsewhere in a file, and goes in as one single-quoted argument that passes the character rule (adr-002:45). BC-8 (component.md:104) matches."}
  - {id: SEC3-4, resolved: partly, note: "The mark is in place in the completion entry and in the plan's self-check (adr-002:35; adr-004:29; BC-22 at component.md:149). Implementation asks before a marked check (adr-002:41; adr-004:36; BC-8 at component.md:107). Two gaps remain. The tester runs the plan's test command and has no rule to ask (adr-004:51; BC-26 at component.md:155). Implementation acts only on the mark that the planning agent wrote. See SEC4-5."}
  - {id: SEC3-5, resolved: yes, note: "BC-33 has review items for the three lock files and for the CI refusal in tests/conftest.py (component.md:172; the refusal at tests/conftest.py:34-39 was verified). The plan constraint is at component.md:201. BC-32 adds `orqlet upgrade --check` (component.md:163). considerations.md:13 now says 'of the installed files'. The proposal diffs newly added to the scope got no such item: see SEC4-1."}
findings:
  - id: SEC4-1
    severity: minor
    where: docs/design/phase-skill-contracts/design/manifest.yaml:41; component.md:168,172,200-201; considerations.md:13; adr-005-injection-unchanged-tests-and-version.md:38
    finding: ".orqlet/proposals/** moved from the security globs into the scope, so pending changes to team-owned control files no longer raise ORQ-E451. These include the role-bindings proposal, which a person may later merge by hand into .orqlet/role-bindings.yaml. That file decides reviewer independence, and this D3 task needs I2 (component.md:202). The three lock files got a 'change only through orqlet upgrade' review item, but the proposal diffs did not: BC-33 only says they 'may change, because they are its output'. The glob also admits a proposal for any seeded file, for example the profile or resources.yaml with its access: login entries, not only the two files that the constraint names. A hand edit, or a misled agent's edit, of a proposal diff raises nothing in this task."
    evidence: "src/orqlet/domain/changeplan.py:378-391 (_propose rewrites the diff whenever it differs; verified). src/orqlet/application/usecases/upgrade.py:140-148 (only conflicts raise ORQ-W080; verified). as-is.md:1297-1301 (U-14: diff files are merged by hand). manifest.yaml:74-78 (the seeded files stay on security globs). component.md:172 (the review items name only the lock files and tests/conftest.py)."
    required_change: "Narrow the scope entry to the proposal files that the constraint names: .orqlet/proposals/.orqlet__versions.yaml.diff and .orqlet/proposals/.orqlet__role-bindings.yaml.diff. Any other proposal then becomes a file outside the plan. In the BC-33 review item and the plan constraint, state that the proposal diffs change only through orqlet upgrade, that `orqlet upgrade --check` (BC-32) plans no write to them after regeneration, and that no phase applies them. The regeneration phase report says that applying the role-bindings proposal later changes reviewer independence."
  - id: SEC4-2
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:42-44; considerations.md:26; component.md:127
    finding: "Decision 4 asks for 'the merge commit of each approval on the protected branch', but no check ties the named commit to that branch. The commit only has to be a full hex id, an ancestor of HEAD and a commit that changed the approved files. The candidate list (`git log -- <approved files>`) also shows local and unmerged commits, such as an agent's own edit of plan.yaml, and their subject is free text that can read 'Merge pull request'. If the person picks such a commit, an edited plan passes the edit check, and its checks then run without a further yes. The residual at considerations.md:26 names only a later commit that also changed the files, not an unmerged one."
    evidence: "adr-003:42 ('on the protected branch'); adr-003:43-44 (the listing and the checks applied); data-flow.md:76; considerations.md:26."
    required_change: "Before accepting the commit, confirm with `git merge-base --is-ancestor '<merge>' '<remote>/<branch>'` that it is reachable from the remote-tracking ref of the protected branch, which the person names. Mark each listed candidate as on or off that branch. If the ref is missing or was never fetched, report the check as not run and ask. Add the unmerged-commit case to the residual and to BC-14."
  - id: SEC4-3
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:44-45; component.md:127
    finding: "The new git checks are written as 'finds no difference' or 'prints nothing', without saying how an error counts. Two of them fail open. First, `git ls-files --others ...` prints nothing on stdout when it fails (a bad pathspec, a wrong directory), so the untracked-file check passes. Second, `git diff --quiet <merge>^1 <merge>` is supposed to find a difference. If it errors instead, it returns non-zero, which can be read as 'a difference', and then the 'changed the approved files' check passes for any commit. Causes include a root commit and the shell mangling `^`: zsh with EXTENDED_GLOB prints 'no matches found' and exits 1, and cmd.exe drops `^` as its escape character. That reopens the SEC3-1 case of naming HEAD."
    evidence: "adr-003:44 (the agent-composed `<merge>^1`; the skill stops only when no difference is found); adr-003:45 ('prints nothing'); adr-002:45 (single quotes are required for artifact values only, not for the suffix the agent composes)."
    required_change: "In phase-contract.md, each git check passes only on its expected result: exit status 0 or 1 for `--quiet` and `--is-ancestor`, and exit status 0 with empty stderr for `ls-files` and `log`. Any other exit status or any error output stops the skill with 'check not run'. Quote the composed revision ('<merge>^1'), or resolve it first with `git rev-parse --verify '<merge>^1'`. Extend BC-14."
  - id: SEC4-4
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:50; component.md:128; sequence.md:41
    finding: "The ledger comparison stops on two changes only: a changed answer to a question that was answered at the merge, and a new supersession. Several other requirement changes are not named. A question answered at the merge can be removed. It can be set to withdrawn, which forces its answer to be removed (question_ledger.py:54-59). Its text, blocks or answer scope can be rewritten while the answer value stays. A conflict ruling can change, such as C-1, which governs Q-3. The proposal makes 'changed requirements ... or a requirement the design cites' invalid. An agent that applies the two-item list literally continues after any of these."
    evidence: "adr-003:50; docs/design/orqlet-architecture-proposal.md:3074 (verified); src/orqlet/application/contracts/question_ledger.py:35-51,67-80 (text, blocks, status, answer and conflicts[].ruling are separate fields); questions.yaml:205-222 (the C-1 ruling)."
    required_change: "State the rule so that it fails closed. These changes stop the skill for a new approval: any change to any field of a question answered at the merge, its removal, and any change to the conflicts list or a ruling. Only new open questions, and answers to questions that were open at the merge, do not count. Extend BC-39."
  - id: SEC4-5
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-004-what-each-phase-produces.md:51; component.md:155; considerations.md:22; adr-002-project-context-read-at-execution-time.md:35,41
    finding: "The warning-list control has two gaps. (1) The tester runs the plan's test command first in every phase (sequence.md:93-94), but BC-26 pins only the re-cite and the stop on a different hash. It has neither the working-tree check nor the yes before a marked check, although considerations.md:22 claims both for 'implementation and the tester'. A subagent may also be unable to ask the person (U-11). (2) Implementation asks only before a check that the plan marks. The mark is free text written by the planning agent, so if the planner misses it, a command on the warning list runs without a yes."
    evidence: "adr-004:51 ('after citing its source again as the coder does, and stops on a different hash'); component.md:155 (BC-26); considerations.md:22; adr-002:35,41; adr-004:29."
    required_change: "In the tester prompt and BC-26: the tester applies the coder's checks (re-cite, and no uncommitted or untracked change to a cited file). It never runs a marked check; it hands that check back to the coder, who asks the person. In implementation (adr-002:41, adr-004:36, BC-8): the agent also applies the warning list of ADR-002 decision 6 to each command itself, and asks before running a match whether or not the plan marks it."
  - id: SEC4-6
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md:28,47; component.md:104
    finding: "A secret placeholder 'is filled only from an environment the person has set up', but nothing forbids the agent from reading that value. If the agent checks that the variable is set with `echo $NAME`, `env` or `printenv`, the secret goes to the model and into the transcript. The output rule (adr-002:47) covers reports, not the conversation. The baseline's ban on reading or printing a token sits under 'Looking things up' only."
    evidence: "adr-002:28,47; src/orqlet/workflow/baseline/baseline.md:25,31 (verified)."
    required_change: "In phase-contract.md and BC-8: the agent puts the variable reference in the command (\"$NAME\") and checks only that the variable is set, for example with `test -n \"$NAME\"`. It never prints, echoes or lists environment values."
not_verified:
  - "I computed no sha256; the author hashes the files. The new artifact hashes at manifest.yaml:92-137 were not checked."
  - "Whether `orqlet upgrade --check` reports a planned rewrite of a hand-edited proposal diff, and whether any command applies a proposal. This decides how much SEC4-1 matters. I read only changeplan.py:360-404 and upgrade.py:125-160."
  - "Carried from round 3: whether `orqlet upgrade --check` or `orqlet doctor` detects a hand edit of the three .orqlet lock files."
  - "Whether the input check, or `orqlet validate ledger`, rejects a ledger whose questions share a key or which holds duplicate YAML keys (relevant to SEC4-4)."
  - "Local git state that hides working-tree changes from `git diff` (assume-unchanged or skip-worktree flags, clean filters, core.fsmonitor) and a hostile gpg.program behind %G?. Commits cannot set these. Not assessed."
  - "Shell behaviour per platform (zsh options, cmd.exe, PowerShell) was reasoned about, not run."
  - "Whether a tester subagent can ask the person in each client (U-11)."
  - "Besides the files cited here, I opened as-is.md only for A-13, A-37, A-50, A-51, A-59, U-14 and C-16, and the proposal only at lines 3050-3090. I did not read the architecture note, the fragments or evidence/web."
  - "I ran no test, validator or command."
# Credential and certificate rules: no file I read held a credential, token or certificate, so these rules called for nothing beyond SEC4-6, which keeps secret environment values out of the conversation.
```

### Author's responses to round 4

| Id | Response |
|---|---|
| SEC4-1 | The scope now names only `.orqlet/proposals/.orqlet__versions.yaml.diff` and `.orqlet/proposals/.orqlet__role-bindings.yaml.diff`, and any other proposal file is outside the plan. BC-33 has the review items: the lock files and the two diffs change only through `orqlet upgrade`, `orqlet upgrade --check` plans no write to them after the regeneration, and no phase applies a proposal. The regeneration phase's report says that applying the role-bindings proposal later changes reviewer independence. I checked this in the code: the review-record validator derives independence from that file's approved bindings and model families (`src/orqlet/application/usecases/validate_records.py:306-326`). The overlap check was run again: both diffs are tracked and in scope, and none of the 417 tracked files in scope matches a security glob |
| SEC4-2 | ADR-003 decision 4, *Approved*: the person names the remote-tracking ref of the protected branch. The agent lists candidates from that ref only. The named commit must be reachable from the ref and from HEAD. A missing or never-fetched ref means the check did not run, and the skill asks. BC-14 and the `considerations.md` residual cover the remaining cases: a commit on the branch that is not the approval merge, and a ref that lags the host |
| SEC4-3 | ADR-003 decision 4 opens with the exit-status rule: `--quiet` and `--is-ancestor` pass only on exit status 0 or 1 as the check states, and other commands only on exit status 0 with nothing on the error output. Anything else stops the skill with "check not run". A composed revision is resolved with `git rev-parse --verify` and single-quoted. BC-14 and a new failures row say the same |
| SEC4-4 | The ledger rule fails closed: any change to any field of a question answered at the reference commit, its removal, or any change to the conflicts list or a ruling stops the skill. Only new questions, and the answer and status of a question open at the reference commit, are exempt. BC-39. ADR-003 consequences state the cost: a correction of wording also stops the skill |
| SEC4-5 | ADR-002 decision 3, ADR-004 decisions 5 and 7, BC-8 and BC-26: implementation applies the warning list to each command itself and asks before a match, whether or not the plan marks it, so the mark helps the plan's reviewer but is not the control. The tester applies the coder's checks (re-cite, and no uncommitted or untracked change to a cited file). It never runs a marked check or a match, and hands it back to the coder, who asks the person. `considerations.md` says the same |
| SEC4-6 | ADR-002 decision 3 and BC-8: a secret goes into the command as a variable reference (`"$NAME"`). The agent checks only that the variable is set (`test -n "$NAME"`) and never prints, echoes or lists an environment value. `considerations.md` says the same |

## Round 5: PASS

Files reviewed, hashed by the author with `shasum -a 256` before the reviewer started and again after it returned; both lists are identical.

| File | sha256 |
|---|---|
| `design/adr-001-one-contract-shape-for-every-skill.md` | `463ca10ed881f3477e0ac52cf6177d651088d818dd34a790423f71dfa5e34959` |
| `design/adr-002-project-context-read-at-execution-time.md` | `215d11da36c8f7f3ea79ceb33a8bb6bd883bfda4c16dbaf9b020a8aacefa41fb` |
| `design/adr-003-handoffs-and-the-input-check.md` | `11add91bf06ab5a994e38ff07adc74a8c5333e6b71a92875a40a33b09706e665` |
| `design/adr-004-what-each-phase-produces.md` | `e0210f380060e844a27ebb6ce7834642cb0a0c59bfd664fa0ad804891b4661e7` |
| `design/adr-005-injection-unchanged-tests-and-version.md` | `ab6fbf67e835b0a2f36178750198f70fd5ca24e9969d86ae1350c7d9fbe3a2cb` |
| `design/component.md` | `db23fcdc4c36016dafc810496908306d4c1b46306a20f245bc3287ed7d75cc27` |
| `design/considerations.md` | `f2939364e05942d7fb14fba5db9635a6b0eb7b37300311a348d89380cbaa0220` |
| `design/container.md` | `5fb05c776abe38a3cf98756c0482a161a03a6bd420dde5a97dce0ef39f3db45f` |
| `design/context.md` | `8eb078df676b8829c563094c2a0b1e686df9bc747a7c6adb79a40062e0b88712` |
| `design/data-flow.md` | `322e216011039f126b8cba9e3add87515beef72a3df19b70c124c6011f528d18` |
| `design/sequence.md` | `9886266e62cecb1451b3ec6c67d597c02945fbdb8ccec0c556617db8ec039396` |
| `design/manifest.yaml` | `d9a7d966c80ec088cf36d2934171e9bc13331b06fd683a1bbea97b7f47b7fc00` |
| `as-is.md` | `e1c968ac76ab29556a317fc45063c3f4e8849f627b8562b84549cba03189fd0f` |
| `questions.yaml` | `ebb6d3a685c75d3d2d0a7bc7708426b307658ec016268df01a6ff8ef109d92fa` |

### The reviewer's output, unchanged

```yaml
round: 5
verdict: PASS
round_4_resolution:
  - {id: SEC4-1, resolved: yes, note: "The scope now names only the two proposal diffs (manifest.yaml:41-42), and both exist (a listing of .orqlet/proposals/ shows exactly these two files). BC-33's review items say the lock files and the two diffs change only through orqlet upgrade, that upgrade --check plans no write to them, and that no phase applies a proposal. They also cover the report sentence on reviewer independence (component.md:178,183-184). The plan constraints match (component.md:213-214), and so does considerations.md:13-15. The cited derivation of independence was verified at validate_records.py:306-326."}
  - {id: SEC4-2, resolved: yes, note: "The person names the remote-tracking ref. Candidates are listed from that ref only, and a missing ref means 'not run' (adr-003:45). The named commit must be reachable from the ref and from HEAD (adr-003:46). BC-14 matches (component.md:134), and so do the failures row (component.md:61) and the residual for a ref that lags the host (considerations.md:29; adr-003:85). How reachability and the candidate list behave with merged side branches is new: see SEC5-1."}
  - {id: SEC4-3, resolved: yes, note: "adr-003:39 adds the exit-status rule: 0 or 1 for --quiet and --is-ancestor, exactly as each check states; for other commands, 0 with nothing on the error output; anything else is 'check not run'. A composed revision goes through 'git rev-parse --verify' and is single-quoted. BC-14 (component.md:137), the failures row (component.md:58) and sequence.md:7 agree. On cmd.exe a mangled '^' now fails rev-parse, which fails closed. The pathspec is missing from the changed-files check: see SEC5-1."}
  - {id: SEC4-4, resolved: yes, note: "adr-003:52-61: the agent shows the ledger diff for each reference commit (the AS-IS acceptance commit for design, the design merge for plan, both merges for implement). Any change to a field of a question answered at that commit, its removal, or a change to the conflicts list or a ruling stops the skill. Only new questions, and the answer and status of questions that were open at that commit, are exempt. The cost is stated at adr-003:84. BC-39 (component.md:138) and the failures rows (component.md:62-63) match. The proposal's :3074 and :3088 were verified. New answers still appear in the diff the person is shown."}
  - {id: SEC4-5, resolved: yes, note: "Implementation applies the warning list to each command itself, whether or not the plan marks it (adr-002:41; adr-004:36; BC-8 at component.md:111). The tester applies the coder's checks and hands a marked check or a match back to the coder (adr-002:42; adr-004:51; BC-26 at component.md:165; considerations.md:25). The tester's text leaves out the plan-text comparison: see SEC5-4."}
  - {id: SEC4-6, resolved: yes, note: "A secret enters a command only as \"$NAME\". The agent checks only that it is set ('test -n') and never prints, echoes or lists an environment value (adr-002:28; BC-8 at component.md:108; considerations.md:27). Raw check output is a separate path: see SEC5-3."}
findings:
  - id: SEC5-1
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-003-handoffs-and-the-input-check.md:45-46,85; component.md:134; considerations.md:29
    finding: "The candidate list and the reachability check do not single out 'the commit that merged each approval on the protected branch'. (1) Without --first-parent, the path-limited command 'git log --format=... <ref> -- <approved files>' applies git's default history simplification. A merge commit whose result for those paths equals its second parent is not shown, and the merged branch's own commits are listed instead. In a repository that merges pull requests with merge commits, the approval merge is therefore not among the candidates, and the person can only pick a branch commit, whose subject and parents give them nothing to judge. (2) 'git merge-base --is-ancestor <merge> <ref>' accepts any commit in the history of any merged branch, including an intermediate state that was never a merged result. Example: inside an unrelated pull request, one commit edits plan.yaml and a later commit restores it, so the pull request's net diff shows reviewers nothing about plan.yaml. If the working tree holds that intermediate plan.yaml and the person names that commit, every check passes: it is reachable, it changed the files, and the diff is empty. The approved checks of an unreviewed plan then run without a further yes. The residual names only 'a commit on the protected branch', which understates what passes. (3) The changed-files check is written as 'git diff --quiet between its first parent and it exits 1' with no '-- <approved files>'. Taken literally, any non-empty commit passes, and a wrong approved-files path would no longer be caught by it."
    evidence: "adr-003:45 (the candidate command, no --first-parent); adr-003:46 (reachability by --is-ancestor; the parent diff shown without a pathspec); adr-003:85 and considerations.md:29 (the residual says 'on the protected branch'); component.md:134. The git history-simplification behaviour is general git behaviour that I reasoned about and did not run here."
    required_change: "In phase-contract.md and BC-14: list candidates with 'git log --first-parent --format=... <ref> -- <approved files>'. Require the named commit to be on the ref's first-parent line, for example 'git rev-list --first-parent <ref>' prints it (exit 0, empty error output). Write the changed-files check as 'git diff --quiet <parent> <merge> -- <approved files>' exits 1. Reword the residual to say that a first-parent commit that is not the approval merge still passes."
  - id: SEC5-2
    severity: minor
    where: docs/design/phase-skill-contracts/design/manifest.yaml:26,28-37; component.md:182-185; considerations.md:13
    finding: "The scope lists the client instruction and agent folders as wildcards (.claude/agents/**, .claude/commands/**, .claude/rules/**, .cursor/agents/**, .cursor/commands/**, .cursor/rules/**, .codex/agents/**, and the skills folders), and AGENTS.md and .claude/CLAUDE.md as whole files. Every later client session loads these as instructions or agent definitions, including the I2 reviewers of this task's own implementation phases. A new rule file, a new agent definition or new AGENTS.md team text, added by hand or by a misled agent, is inside the scope, raises no ORQ-E451, and is not covered by any BC-33 review item. BC-32 checks only doctor findings, and the design names no check for files that the lock does not list. Today these folders hold only generated files, and AGENTS.md holds only the baseline block, so any other change there is not upgrade's output. considerations.md:13 says the scope holds only what upgrade writes, but the wildcards admit more."
    evidence: "manifest.yaml:26,28-37 (scope entries); AGENTS.md:1-41 (only the orqlet baseline block); .cursor/rules/ has 12 files at its root, and generated.lock.yaml lists at least 12 .cursor/rules entries from line 502 (counted, not matched one by one); component.md:182-185 (review items cover only the lock files, the proposal diffs and tests/conftest.py); expected_change.py:85-87 (ORQ-E451 only for security-glob files, verified in round 2)."
    required_change: "Add a review item to BC-33 and a plan constraint, and preferably a check in the regeneration phase. Every path the task adds or changes under .claude/, .agents/, .cursor/ and .codex/ must be a non-seeded path of .orqlet/generated.lock.yaml after the regeneration. The text of AGENTS.md and .claude/CLAUDE.md outside the managed blocks must be byte-identical to the base revision. Reword considerations.md:13 so it names this review item instead of claiming the wildcards hold only upgrade's output."
  - id: SEC5-3
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-002-project-context-read-at-execution-time.md:28,48,71; considerations.md:27; component.md:108,114
    finding: "The credentials row claims a control over credentials in 'the conversation'. But the agent reads every check's raw output before it summarises it (adr-004:36, 'reads their output'). A check that runs with a secret variable, or with the person's environment, can print a credential: a failing test that shows its local values, a verbose HTTP client, or a tool that echoes its configuration. That output reaches the model vendor and the transcript. The output rule covers only reports and records, and the stated residual is only 'the rules are advice'."
    evidence: "adr-002:48 ('Command output goes into reports and records as a summary'); adr-002:28 (secrets passed as variable references); adr-002:71 (checks run with the person's environment); considerations.md:27 (row title and What remains); component.md:114."
    required_change: "State the residual in considerations.md:27 and in the ADR-002 Consequences: raw check output reaches the model and the transcript. In phase-contract.md, before running a check whose command holds a secret variable reference, the agent tells the person that its output will reach the conversation unfiltered. Add that sentence to BC-8."
  - id: SEC5-4
    severity: minor
    where: docs/design/phase-skill-contracts/design/adr-004-what-each-phase-produces.md:51; component.md:165; considerations.md:25
    finding: "adr-002:42-44 says the tester applies 'the same checks' as the coder. These include a stop when the plan's command text differs from the cited lines in more than the placeholders. ADR-004 decision 7 and BC-26 list only the re-cite and the working-tree check, and stop only 'on a different hash or such a change', and the tester prompt and its test follow them. The tester runs the plan's test command first in every phase (sequence.md:96-97). So a planned command with arguments that are not in the cited lines and match no warning-list pattern, such as an added '-p' plugin or another test path, runs in the tester without the stop that the coder applies."
    evidence: "adr-002:42,44; adr-004:51; component.md:165 (BC-26); considerations.md:25; sequence.md:96-97."
    required_change: "Add 'or a plan text that differs from the cited lines in more than the placeholders' to the tester's stop in ADR-004 decision 7, BC-26 and considerations.md:25."
not_verified:
  - "I computed no sha256: the shell is refused in this read-only mode. The artifact hashes in manifest.yaml:89-138, the considerations hash at manifest.yaml:207, and whether the files changed while I read them were not checked."
  - "No git command was run. The history-simplification, --first-parent and rev-list behaviour in SEC5-1 is reasoned from general git behaviour, not observed in this repository."
  - "Whether 'orqlet doctor' or 'orqlet upgrade --check' reports a file under a client folder that the lock does not list, or AGENTS.md team text (this decides how much SEC5-2 matters)."
  - "Whether the managed-block parser treats an orqlet marker inside a fenced block in AGENTS.md team text as a block marker. Onboard writes such text only after a warning and its own confirmation (adr-002:57)."
  - "Whether the remote that the person names (for example 'origin') points at the host of the protected branch. The design does not show the remote's URL; I treated this as the person's responsibility. A local 'git update-ref' or a fetch from another URL can move a remote-tracking ref."
  - "Carried over: local git settings (assume-unchanged, skip-worktree, clean filters, core.fsmonitor, global excludes behind --exclude-standard, gpg.program behind %G?); POSIX 'test -n' and \"$NAME\" on PowerShell or cmd.exe (these fail closed as 'not run', but I did not run them); whether a tester subagent can ask the person in each client (U-11)."
  - "From the git status taken at the start of this session: as-is.md and the design files are untracked, and questions.yaml has uncommitted changes. I did not judge this task's own handoff against ADR-003 decision 4, which governs the skills after implementation."
  - "Outside the design's own text, I opened validate_records.py:300-329, the proposal at 3066-3091, baseline.md:22-35, AGENTS.md, and the listings of .orqlet/, .orqlet/proposals/ and .cursor/rules/, plus a grep of generated.lock.yaml. I did not read the fragments, evidence/web or the architecture reviewer's note. I ran no test, validator or orqlet command."
# Credential and certificate rules: no file I read held a credential, token, private key or certificate, so these rules needed nothing beyond SEC5-3, which concerns secrets in check output reaching the conversation.
```

This review is an additional check, not a guarantee.

### Author's responses to round 5

The person chose to stop after round 5 and to give the design pull request a consolidated report. The design files keep the bytes this round reviewed. Only the manifest's self-check changed afterwards, to record this round. SEC5-1 to SEC5-4 are minor and open. They are not applied here, and the design pull request's review decides on them.
