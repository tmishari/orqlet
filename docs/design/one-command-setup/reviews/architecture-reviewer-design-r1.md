# Architecture review of the design, round 1

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-20T12:41:17Z with only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for`.

## Hashes when the reviewer started (`orqlet evidence hash`)

| File | sha256 |
|---|---|
| design/manifest.yaml | 731a789c9400a7ad916800f9e9ec75e6cae8b8b09734f023c245860d498a5554 |
| design/component.md | 094a127aaa7001cb188b60c4fa2d62e5c5c2d7667fa6c941ff74cab78726eb22 |
| design/context.md | 65f0af99885e52340cdfde8788196aa531bce8bfeac6d2f2ae7308f4836cdce2 |
| design/container.md | b61f3c3f496b4ec8bbc67af2c449d138eb31b6a6ff7f234578c084e31ac797f2 |
| design/data-flow.md | 0b627a0495a7706d1f5ae1e2cd3f3c5a745a8ae16c063c469fd7acc541e92902 |
| design/sequence.md | adbe52f5f4bd8dd3d3f72000137e057aa6c0e25f12bf91a80275ac27c56e6be3 |
| design/adr-001 | 2cbb90208c8f3bb804536fe02f04949b3d424349dc6205a2886a7012f406cc36 |
| design/adr-002 | bf01b59d32ed607f452e0d28109ad32897fef6eb9483b3b713af3e469a664b3a |
| design/adr-003 | 6167ce562d6c51df0fa486447818543a876ca0d4cfba7ce93992188c1bd79fe9 |
| design/adr-004 | e9563e66d4d0c4947a1385e83f4bdff4488745cf47ed392d7d22c607901ac98f |
| design/adr-005 | ae73898709a4c7241eb8eaa6db7d5318b41f6ba43ce5645f2445f1937aa9ba99 |
| design/adr-006 | 18b696eae943300a8101be65c0bb4724bed2406236917ab0f51c5327bfdefd6a |
| design/adr-007 | cea76324707fd935a8e8a824adeeded80c9aa745493fc617e29f9b9e130a2fbf |
| questions.yaml | 9bc0396b719d60664de8376aa4f55404e2c2328a5ce1487715b2b0e7a72a0a73 |

The hashes when the note was saved are those above: the reviewer edited nothing, and no design file changed while it ran. The design files changed afterwards to answer the findings (see "Author's responses"). The reviewed content is therefore not what will merge, and round 2 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: changes required.** I found 5 blocking and 9 non-blocking findings. The overall structure is sound: the layering, the four-client split, advisory-only hooks, tool preparation through `ProcessRunner` with fixed argument vectors, and Rich kept in the interface layer. The blocking issues are gaps in how writes to the user's home folders are executed and owned, how the user-level render works, an incomplete persisted-schema change, and acceptance criteria that contradict each other. I edited no file.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 1, role: architecture-reviewer}
verdict: changes-required
findings:
  - id: F-1
    blocking: true
    rule: ORQLET-SAFE-001 (as amended under Q-32), ADR-002
    statement: >-
      The design applies the user scope as "one journalled change" (component.md:52) across five
      roots, each its own LocalFileSystem (ADR-002 decision 1, line 25; decision 4, line 35).
      apply_plan takes exactly one FileSystem and keys journal entries and backups by the relative
      path alone (apply_plan.py:39-79, `_entry` 111-119). The stores are built per project id
      (wiring.py:145-149). Relative paths collide across roots: `skills/orqlet/SKILL.md` exists
      under both ~/.claude and ~/.agents. The user manifest sits in the data directory, outside
      every root, so "manifest last" has no defined place in the plan.
    evidence: [component.md:52, adr-002…md:25, adr-002…md:35, src/orqlet/application/usecases/apply_plan.py:39-79, src/orqlet/interface/cli/wiring.py:145-149]
    suggested_action: >-
      Decide this in ADR-002. Option one: one change per root under a shared group id. Option two:
      one composite user-scope file system with root-prefixed canonical paths (for example
      `claude/…`, `agents/…`). Either way, state where user/manifest.json is written last and how
      rollback addresses entries in several roots.

  - id: F-2
    blocking: true
    rule: ADR-002 ownership, ADR-004 decision 8
    statement: >-
      ~/.agents/skills is written for both Cursor and Codex (component.md:78-79). The ownership
      record has no per-client owner, and `uninstall --client <id>` "removes Orqlet's entries
      only" (ADR-004:59; ADR-002:37). Uninstalling Codex would therefore remove Cursor's skills.
      The Codex row also adds agents/openai.yaml while the Cursor row does not. One owned folder
      would get two different renders, so the recorded hash would flip between installs.
    evidence: [component.md:78-79, adr-002…md:25-28, adr-002…md:37, adr-004…md:59, evidence/web/global-setup.md:24]
    suggested_action: >-
      Record the set of owning clients for each entry in user/manifest.json, and remove an entry
      only when no remaining client owns it. Render one shared form, with the sidecar, for both
      clients. Add an acceptance criterion for uninstalling one client while the other remains.

  - id: F-3
    blocking: true
    rule: ORQLET-MODEL-001, ORQLET-DET-001, design-format §4 (interfaces)
    statement: >-
      The client adapters "render … for the project scope and the user scope" (component.md:136),
      but the interfaces list (component.md:142-146) leaves the render port unchanged. The current
      port is `InstructionAdapter.render(RenderRequest)`, and RenderRequest comes from the project
      profile: scoped rules, conventions, integrations and per-client model settings on roles
      (instruction_adapter.py:94-139). The design does not say what request the user scope gets.
      In particular, it does not say which model policy, if any, applies to agents written
      globally. BC-19 covers model names only for the bundled skills.
    evidence: [component.md:136, component.md:142-146, src/orqlet/application/ports/instruction_adapter.py:100-139, adr-003…md:24-27]
    suggested_action: >-
      Add the port change (a scope field, or a separate user-scope request type) and define the
      user-scope request content: no model settings and no model names, no conventions, no
      integrations, and the foundation as the baseline body. Add an acceptance criterion that
      user-scope agents contain no model name.

  - id: F-4
    blocking: true
    rule: expected_changes completeness (persisted-schema), ORQLET-DET-002
    statement: >-
      Adding `copilot` to ClientId (common.py:28) affects every persisted schema that lists the
      three clients: model-policy v2, role-bindings, review-result and integrations, not only the
      project profile. EC-3 declares only "ClientId and the profile client list", and says
      existing files stay valid. The design does not decide whether Copilot may appear in model
      policies, MCP integrations or review results.
    evidence: [src/orqlet/application/contracts/common.py:27-28, src/orqlet/workflow/schemas/orqlet.model-policy.v2.json:60-62, :164-166, :495-497, orqlet.role-bindings.v1.json:21-23, orqlet.review-result.v1.json:51-53, :269-271, orqlet.integrations.v1.json:120-122, manifest.yaml:54-62]
    suggested_action: >-
      Decide for each schema whether `copilot` is admitted, and whether that needs a schema
      version. List each one in EC-3 and EC-9, and add an acceptance criterion that the Pydantic
      ClientId and the JSON schemas agree.

  - id: F-5
    blocking: true
    rule: acceptance-criteria consistency (ADR-004)
    statement: >-
      BC-15 says the post-edit hook "starts no process". ADR-004 accepts payload paths only when
      they resolve inside the root "found by GitRunner" (ADR-004:51-52), and BC-17 allows one Git
      process per hook. Under Copilot, BC-14 reads the workspace AGENTS.md "including outside a
      repository", where no Git-found root exists to confine the path. These criteria cannot all
      hold together.
    evidence: [component.md:184, component.md:185, component.md:187, adr-004…md:32, adr-004…md:51-53]
    suggested_action: >-
      Decide how post-edit finds the project root: one allow-listed Git call, or an upward
      `.orqlet/` search through the FileSystem port. Align BC-15 and BC-17 with that choice, and
      define which root confines the Copilot AGENTS.md read outside a repository.

  - id: F-6
    blocking: false
    rule: ADR-004 bound "Writes: none", BC-11
    statement: >-
      `data_directory()` runs `mkdir(parents=True, exist_ok=True)` (wiring.py:76-81), which is
      contradiction C-3. Status and both hooks read user/manifest.json, so with today's wiring
      they would create the directory at every session start. K-10 leaves C-3 unfixed, but these
      new commands would inherit it.
    evidence: [src/orqlet/interface/cli/wiring.py:76-81, component.md:59, adr-004…md:54, component.md:238]
    suggested_action: >-
      Add a constraint that status and the hooks resolve the data directory without creating it.
      Test this under BC-11 and BC-15.

  - id: F-7
    blocking: false
    rule: baseline "Do not guess"
    statement: >-
      ADR-004 decision 6 says every registration is an argument vector with no shell, but cites
      only Claude Code's exec form (evidence 1.9). No evidence shows a vector form for Cursor,
      Codex or Copilot `hooks.json`. ADR-002 decision 3 identifies owned entries by "command
      vector starts with orqlet hook", so it rests on the same assumption. That the post-edit
      event returns context is cited for Copilot only (evidence 9.6), not for Cursor or Codex.
    evidence: [adr-004…md:56, adr-002…md:31, evidence/web/client-integration-contracts.md:23, :32-40, :64-77, :120]
    suggested_action: >-
      For each client, cite its command schema and post-tool output field. Where no page covers
      it, record an unknown with a fixed fallback behaviour. Identify owned entries by the exact
      canonical entry rather than by an assumed vector prefix.

  - id: F-8
    blocking: false
    rule: ADR-001 consequence (status is a stable contract)
    statement: >-
      ADR-001 makes the `status` JSON a compatibility surface, but component.md §3 lists its
      content only loosely. BC-11 covers four states and leaves out "global setup missing" and
      "linked worktree", although the entry skill acts on both (ADR-001:20-26). The design does
      not say how a linked worktree is detected within the GitRunner allow-list and the one-call
      bound (AS-IS U-4).
    evidence: [adr-001…md:20-26, adr-001…md:37, component.md:59-67, component.md:179, as-is.md:751-755]
    suggested_action: Define the status fields and the state values, extend BC-11, and state the worktree detection method.

  - id: F-9
    blocking: false
    rule: ORQLET-ARCH-001, ORQLET-ARCH-003 (workflow clause)
    statement: >-
      The component diagram draws direct arrows from the application to adapters (install use
      case to detection, client adapters and tool preparation; status to the user-scope file
      system and GitRunner; component.md:118-126). The container view routes the same calls
      through ports. Path confinement is placed in application/contracts/hook_payload.py, where
      `os` and `pathlib` are forbidden (pyproject.toml:105-111). Status and the hooks read the
      workflow version and foundation text, but the design never names the WorkflowSource port
      as the route (pyproject.toml:114-118).
    evidence: [component.md:118-126, container.md:46-55, pyproject.toml:105-118, component.md:224]
    suggested_action: >-
      Draw these calls through named ports, keep path resolution behind the FileSystem or Vcs
      port, and name WorkflowSource for the version and foundation reads.

  - id: F-10
    blocking: false
    rule: ORQLET-SAFE-001 amendment content (K-1)
    statement: >-
      ADR-002 decision 1 applies one union of writable sub-paths to every root, so paths such as
      ~/.agents/settings.json or ~/.claude/hooks/orqlet.json would be writable. user/cursor-user-rules.md
      and the private working folder for tool preparation are written in the data directory,
      outside every declared root and outside the journal. ADR-002 decision 1 is in effect the
      text of the SAFE-001 amendment, so it should be exact.
    evidence: [adr-002…md:25, component.md:82, adr-006…md:49]
    suggested_action: >-
      Give a table of writable sub-paths per root. State whether cursor-user-rules.md is a
      journalled owned file, and how the working folder is created.

  - id: F-11
    blocking: false
    rule: Q-24, BC-23, ORQLET-TEST-001
    statement: >-
      K-4 sets HOME, CODEX_HOME, COPILOT_HOME and ORQLET_DATA_DIR. CI also runs on Windows (A-52),
      where the home directory resolves from USERPROFILE, so a test could reach the real home
      folder on a Windows runner.
    evidence: [component.md:230, as-is.md:650-657]
    suggested_action: Pass the home directory in through one injected value or port, add USERPROFILE to K-4, and state how client folders resolve on Windows.

  - id: F-12
    blocking: false
    rule: ORQLET-SAFE-001, ORQLET-ARCH-003 (K-1)
    statement: >-
      standards_applied lists SAFE-001 and ARCH-003, but the design conforms only to the amended
      wording, and that text is not in the repository. BC-18 has this change edit the
      import-linter independence contract, while K-1 assigns that edit to the separate amendment
      change.
    evidence: [manifest.yaml:134-146, component.md:186, component.md:219]
    suggested_action: >-
      Record in the self-check that conformance is to the proposed amendment, and cite its draft
      (ADR-002 decision 1, ADR-003 decision 2). Say which change owns the pyproject contract.

  - id: F-13
    blocking: false
    rule: consistency
    statement: >-
      The entry skill runs `orqlet install` "after the person says yes" (ADR-001:22). The
      assistant's shell is non-interactive, so without `--yes` the command exits 4
      (component.md:51; ADR-007:35). The sequence view already uses `--yes` for init.
    evidence: [adr-001…md:22, component.md:51, adr-007…md:35, sequence.md:32]
    suggested_action: State `--yes` after the person's confirmation, for install and for upgrade.

  - id: F-14
    blocking: false
    rule: ADR-006 operability
    statement: >-
      On the pipx route, the Graphify step needs uv right after `pipx install uv`. The
      environment is scrubbed down to PATH and HOME, and pipx's binary folder may not be on PATH.
      The design does not say how uv is located. Separately, BC-7 cites R-11 and Q-29 for
      `--dry-run`; the actual source is component.md §3 item 6 and ADR-006.
    evidence: [adr-006…md:44-50, component.md:176]
    suggested_action: Fix how uv is located after pipx installs it (for example, the path pipx reports), and correct BC-7's sources.

not_examined:
  - "Artifact SHA-256 values in manifest.yaml, HEAD and git status: the read-only sandbox refused the shell command, so these are NOT_RUN."
  - "proposal.md, as instructed."
  - "Evidence pages beyond the lines cited above; native client behaviour (U-1, U-2, U-5)."
  - "Whether running Git in a directory taken from the payload is safe against a hostile .git/config: outside my field, passed to the security reviewer (TB-3)."
  - "Whether the manifest's applicable_rules_hash 1c83b7… matches the combined hash of the five per-path values I was given: no command available to recompute it."
```

```yaml
schema: orqlet.self-check/v1
checked_against: {role: architecture-reviewer, phase: design}
examined:
  - "manifest.yaml, the five views, ADR-001 to ADR-007, as-is.md, questions.yaml (Q-1 to Q-38), design-format.md, at the working tree of /Users/tmishari/Documents/orqlet-one-command-setup-research (revision not read: the shell was refused)."
  - "Citations opened only to check them: apply_plan.py, wiring.py, instruction_adapter.py, common.py, pyproject.toml:90-127, .prompts/rules.yaml:25-74, workflow/schemas (a search for the client enum), evidence/web/global-setup.md, evidence/web/client-integration-contracts.md:23-120."
checks:
  - {what: "Class D3 artifact set: context, container, component, data-flow, sequence and real ADRs, each with Context, Decision, Consequences and Rejected alternatives", result: pass}
  - {what: "No phase list, build order or task list; the ordering is a constraint with a reason (K-1)", result: pass}
  - {what: "ADR-002's citation of SAFE-001 at rules.yaml:66-72 and ADR-003's citation of the three-adapter contract at pyproject.toml:120-127", result: pass}
  - {what: "Artifact hashes", result: NOT_RUN}
limits: "Every blocking finding cites file and line. This review is an additional check, not a guarantee."
```

## Author's responses

Every finding was checked against the cited code and accepted. Each was answered by a change to the design text, which round 2 reviews.

| Finding | Response |
|---|---|
| F-1 (blocking) | Accepted. ADR-002 now uses one composite user-scope file system with root-prefixed canonical paths (`claude/`, `cursor/`, `codex/`, `agents/`, `copilot/`, `data/`). `apply_plan` receives that one file system. Journal entries and backups are keyed by the prefixed path. `user/manifest.json` is written last, through the data root. `rollback` addresses prefixed paths. |
| F-2 (blocking) | Accepted. The user manifest records an owner set per entry, and `uninstall --client` removes an entry only when no remaining client owns it. `~/.agents/skills` gets one shared render with the `agents/openai.yaml` sidecar, for Cursor and Codex alike. New BC-27. |
| F-3 (blocking) | Accepted. ADR-002 decision 7 adds a user-scope render request: packaged skills, roles and the foundation only, with no model settings, conventions, integrations, scoped rules or resources. New BC-26: user-scope files contain no model name. |
| F-4 (blocking) | Accepted. ADR-003 decision 1 splits the types. A four-valued `RenderClientId` is used by the profile client list, the adapters and `--client`. The existing three-valued `ClientId` stays for model-policy v2, role-bindings, review-result and integrations, which do not change. EC-3 is updated. New BC-28 checks that the Pydantic types and the JSON schemas agree. |
| F-5 (blocking) | Accepted. Hooks start no process: they find the project by an upward search for `.orqlet/` through the FileSystem port, from the payload's working directory. The Copilot `AGENTS.md` read is confined to that root, or to the working directory itself when none is found. BC-15 and BC-17 now agree. |
| F-6 | Accepted. New K-11: `status` and the hooks resolve the data directory without creating it. Covered under BC-11 and BC-15. |
| F-7 | Accepted. Owned entries are identified only by a manifest record with a matching hash (with security F-6). Each client's command form and post-tool output field are a plan citation, with a fixed fallback: a client with no documented context return on post-tool gets no post-edit registration, and that is reported (section 8). |
| F-8 | Accepted. The `status` fields and state values are defined in section 3. BC-11 covers six states. A linked worktree is detected when `git rev-parse --git-dir` and `--git-common-dir` differ (the plan checks the GitRunner allow-list). |
| F-9 | Accepted. The component diagram now routes calls through named ports. Path handling sits in the use case behind the FileSystem port. WorkflowSource is named for version and foundation reads. |
| F-10 | Accepted. ADR-002 has a per-root table of writable sub-paths. `cursor-user-rules.md` is an owned, journalled file under the `data/` prefix. The tool working folder is scratch, created by the tools adapter and outside the journal. |
| F-11 | Accepted. The home directory comes from one injected `UserHome` value. K-4 adds `USERPROFILE`, and Windows resolution is stated. |
| F-12 | Accepted. The self-check now records conformance to the proposed amendments. The amendment change owns the `pyproject.toml` import contract, and BC-18 checks that the amended contract passes. |
| F-13 | Accepted. The entry skill passes `--yes` after the person's confirmation, for install, init and upgrade. |
| F-14 | Accepted. After `pipx install uv`, the tools adapter locates uv through the fixed vector `pipx environment --value PIPX_BIN_DIR`, verified against the pinned pipx version under K-3. BC-7's sources are corrected. |
