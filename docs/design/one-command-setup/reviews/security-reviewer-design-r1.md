# Security review of the design, round 1

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-20T12:41:17Z with only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for`.

## Hashes when the reviewer started (`orqlet evidence hash`)

These are the same as in `architecture-reviewer-design-r1.md`. Both reviewers started from the same files:

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

No design file changed while the reviewer ran. The design changed afterwards to answer the findings, so round 2 reviews the revised files.

## Reviewer output (unchanged)

<user_visible_high_level_summary>
Verdict FAIL. Two findings block. First, the user-home write roots take their location from `$CODEX_HOME` and `$COPILOT_HOME` and follow a link at the root, and the design never says how those roots are checked. Second, the session-start and post-edit hook context is built from repository content, and no rule limits what that text may contain. Seven other findings do not block: the network-install boundary is incomplete, an unlisted process runs to check the Graphify version, backups are written readable by other users, entries in shared JSON files are owned by a command prefix rather than the manifest, the bare `orqlet` command is looked up on the client's PATH, Rich can interpret markup and escape codes in tool output, and some proxy and certificate variables are removed from the environment.
</user_visible_high_level_summary>
<response>
The verdict is **FAIL**: two findings block. The design never says how the user-home write roots are checked, and the hook context has no rule limiting what repository content it may carry.

```yaml
schema: orqlet.review-result/v1
task: one-command-setup
phase: design
role: security-reviewer
round: 1
verdict: FAIL
assurance: advisory
review_input: null   # not computed; see capability_limits
agent: {binding_ref: orqlet-security-reviewer, client: cursor, model_requested: null, model_observed: null}
independence: I1
capability_limits:
- Ask mode: the shell was refused, so no git command ran and no quote digest or review_input digest was computed. Every quoted location is given as file:line in the claim, and evidence lists hold absence records only.
- The revision is the branch tip one-command-setup-global-design = c024f550cdd652a4527fc6b929f92ca4b101342a, read from packed-refs. The design files were read from the working tree. Whether they are committed at that revision was not checked (the manifest says status draft).
- proposal.md was not read, as instructed. Evidence pages under evidence/web were not opened, apart from one grep for credential terms. Nothing was looked up on the web.
- The reviewer ran in the same client as the author, so independence is I1.
applicability:
  examined:
  - docs/design/one-command-setup/design/{manifest.yaml, context.md, container.md, component.md, data-flow.md, sequence.md}
  - docs/design/one-command-setup/design/adr-001 … adr-007
  - docs/design/one-command-setup/as-is.md (A-10, A-12, A-15, A-27 to A-31, A-34 to A-40)
  - docs/design/one-command-setup/questions.yaml (Q-26, Q-32, Q-33, Q-35)
  - .claude/skills/orqlet-design/references/design-format.md (classes, considerations)
  - cited code: src/orqlet/adapters/fs/local_fs.py, src/orqlet/adapters/fs/journal.py, src/orqlet/application/ports/process.py, src/orqlet/adapters/git/git_runner.py, src/orqlet/adapters/process/environment.py
  conclusion: findings
findings:
- schema: orqlet.finding/v1
  id: F-1
  kind: finding
  severity: blocking
  category: security
  rule_ref: ORQLET-SAFE-001 (as amended under Q-32)
  claim: >-
    TB-1 rests on "fixed" allow-listed roots, but two of them come from environment variables:
    $CODEX_HOME and $COPILOT_HOME (adr-002 line 24; component.md lines 46-49 and 79-80).
    LocalFileSystem resolves its root with resolve(strict=True) and checks for links only below the
    root (local_fs.py lines 74-77 and 168-181). So a root that is itself a link, or an environment
    value pointing at a project, at / or at a shared folder, is accepted. Writes would then land
    outside the user-home client folders and pass every link check. The design does not say how a
    root is validated. It also does not say who creates a missing root such as ~/.agents, which the
    strict resolve needs to exist. That leaves the blast-radius argument of adr-002 line 48 without
    a control.
  evidence:
  - kind: absence
    searched: [docs/design/one-command-setup/design/adr-002-user-scope-root-journal-and-manifest.md, component.md, context.md, data-flow.md]
    method: Read in full. Looked for any rule on validating CODEX_HOME or COPILOT_HOME, on a root that is a link, on root ownership or permissions, on a root inside a Git work tree, and on root creation. None found.
    revision: c024f550cdd652a4527fc6b929f92ca4b101342a
  suggested_action: >-
    Add a root-validation rule to ADR-002, and carry it into the SAFE-001 amendment text. Each root
    must be an absolute path whose real path lies under the real home directory, or is the
    documented default. It must not be a link, unless the person confirms it in the preview. It
    must be owned by the current user and must not lie inside a Git work tree. A missing root is
    created as a journalled change. Name each root's resolved path in the preview. Add tests to
    BC-6 for a linked root and for an env-var root outside home.
  confidence: high
- schema: orqlet.finding/v1
  id: F-2
  kind: finding
  severity: blocking
  category: security
  rule_ref: ORQLET-SEC-002
  claim: >-
    The session-start and post-edit hooks run with no person action in every repository the client
    opens, including untrusted clones. They return text built from the project lock, .orqlet and
    paths in the payload (adr-004 lines 32-35; data-flow.md lines 28-36). The design says repository
    content is "data only" (data-flow.md line 39) and caps the context at 1,200 characters. It does
    not say which fields may reach the model context or how they are sanitised. A hostile .orqlet
    lock or file name could therefore put instruction text into every session. The design also does
    not name the payload field that sets the project root. Confining paths "inside the project root
    found by GitRunner" (adr-004 line 52) means nothing if the payload chooses the directory that
    root is found from.
  evidence:
  - kind: absence
    searched: [adr-004-advisory-native-hooks.md, component.md sections 3 and 6 (BC-14 to BC-17), data-flow.md]
    method: Read in full. Looked for an output template or allow-list, field validation (version pattern, path syntax, control characters), and the payload field that selects the working directory. None found.
    revision: c024f550cdd652a4527fc6b929f92ca4b101342a
  suggested_action: >-
    State in ADR-004 that hook context comes only from fixed templates in the workflow package. The
    only variable fields are: the versions, checked against a strict version pattern; the next
    command, chosen from a closed set; and, for post-edit, a path that is both in the lock and a
    valid CanonicalPath, with control and bidirectional characters removed and a length cap. Say
    that no free text from the repository is copied into context. Name the payload field (cwd, or
    the workspace root) that sets the directory for git rev-parse. Add a hostile-lock golden test
    to BC-14 and BC-15.
  confidence: medium
- schema: orqlet.finding/v1
  id: F-3
  kind: finding
  severity: non-blocking
  category: security
  claim: >-
    The TB-2 control is described as "fixed vectors, exact pins" (context.md line 43; manifest EC-8),
    but that pin covers only the top-level package. First, uv tool install graphifyy==0.9.112
    resolves graphifyy's transitive dependencies afresh on every run. Second, --python 3.12 lets uv
    download a managed Python (A-10). That download is a second network source, which TB-2 lists
    only as "the package index". Third, user-level uv configuration, and pip configuration on the
    pipx route, can redirect the index. The scrubbed environment keeps HOME and XDG_CONFIG_HOME
    (environment.py lines 8-22), so those files are still read. ADR-006 line 52 leaves the uv part
    to K-3 and does not mention pip or pipx configuration. ADR-006 line 60 does accept the missing
    hash pinning.
  evidence: []
  suggested_action: >-
    Reword the TB-2 control to say "pinned top-level versions; transitive dependencies resolved at
    install". Add the managed-Python download as a TB-2 crossing. Extend K-3 to verify, for the
    pinned uv and pipx versions, how to ignore user configuration, or to report the configured
    index in the preview. Record the residual supply-chain risk in the security consideration.
  confidence: medium
- schema: orqlet.finding/v1
  id: F-4
  kind: finding
  severity: non-blocking
  category: security
  rule_ref: ORQLET-SEC-001
  claim: >-
    Graphify preparation is skipped when "graphify is already on PATH at that version" (adr-006
    line 46). Checking the version suggests running whichever graphify comes first on PATH. That
    vector is not in the fixed-vector table. Container.md lines 63-66 say only the tools adapter
    and git start processes, and BC-7 lets dry-run start only "read-only detection". The design
    does not say whether the version check runs in dry-run, or how it is done without running an
    unknown binary.
  evidence: []
  suggested_action: >-
    Name the check in ADR-006 as one fixed vector through ProcessRunner (for example, uv's own
    tool listing) or as a read of uv's receipt file. If PATH has a graphify that uv does not
    manage, report it without running it. State whether the check runs under --dry-run, and cover
    it in BC-9.
  confidence: medium
- schema: orqlet.finding/v1
  id: F-5
  kind: finding
  severity: non-blocking
  category: security
  claim: >-
    Before rewriting a shared user file (~/.claude/settings.json, the hooks.json files,
    $CODEX_HOME/AGENTS.md), install copies the whole file into user/backups (adr-002 lines 34 and
    40). The current backup store writes through write_atomic, which gives a new file mode 0644
    (local_fs.py lines 35 and 113-117; journal.py lines 97-98). A file the person keeps private
    would then be readable by other users in the data directory. Whether these client files can
    hold secrets is not established by the stored evidence (an unknown). The manifest statement "No
    credential is read or written" (manifest.yaml line 126) is therefore unverified for these
    backups.
  evidence: []
  suggested_action: >-
    In ADR-002, require that user-scope backups and journals keep the source file's mode (or use
    0600), that the user/ data directory is created 0700, and that previews, conflicts and --json
    output never print the content of a shared file. Add a test.
  confidence: medium
- schema: orqlet.finding/v1
  id: F-6
  kind: finding
  severity: non-blocking
  category: security
  claim: >-
    ADR-002 decision 3 gives ownership in shared JSON files to any entry "whose command vector
    starts with orqlet hook" (adr-002 line 31). Decision 2 and the uninstall text (component.md
    line 58) give it by the manifest hash. Under the prefix rule, an entry with no manifest record
    would be replaced silently: one the person wrote, one another tool wrote, or one left by an
    earlier manifest that has since been lost.
  evidence: []
  suggested_action: >-
    Say that only an entry with a matching manifest hash is replaced or removed. A prefix match
    with no manifest record, or a different hash, is a conflict. Add this to BC-6 and BC-8.
  confidence: high
- schema: orqlet.finding/v1
  id: F-7
  kind: observation
  severity: info
  category: security
  claim: >-
    Hook entries call the bare orqlet name (K-8; adr-004 line 57), so each client resolves it
    against its own PATH at every session start and edit. Any orqlet earlier on that PATH runs with
    the person's rights. This is the accepted cost of ORQLET-DET-001.
  evidence: []
  suggested_action: >-
    Have install and status report the orqlet that PATH resolves to, and flag it when it differs
    from the running executable.
  confidence: medium
- schema: orqlet.finding/v1
  id: F-8
  kind: observation
  severity: non-blocking
  category: security
  claim: >-
    Rich output for install and uninstall (adr-007) will show file names, root paths and "the
    command and its bounded output summary" from uv or pipx (component.md line 158). The design
    says nothing about escaping Rich markup or removing terminal control sequences from these
    strings, so subprocess output or file names could restyle or spoof the terminal. Whether Rich
    15.0.0 removes control codes by default was not checked (an unknown).
  evidence: []
  suggested_action: >-
    Add a rule to ADR-007: dynamic text is printed with markup disabled or escaped, and control
    characters other than newline are removed. Add a BC-22 case with escape codes in tool output.
  confidence: medium
- schema: orqlet.finding/v1
  id: F-9
  kind: observation
  severity: info
  category: security
  claim: >-
    The scrubbed environment allow-list (environment.py lines 8-22) has no proxy or certificate
    variables. R-3 targets admin-restricted accounts, where network access often needs them. The
    design does not say whether they pass to uv and pipx. Removing them may break installs; passing
    them adds an input the person controls.
  evidence: []
  suggested_action: >-
    Name in ADR-006 which network variables, if any, are passed to tool preparation.
  confidence: low
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: security-reviewer, phase: design}
  checks:
  - {what: design set, AS-IS and ledger entries read, how: "Read tool on each listed path; proposal.md skipped", result: pass}
  - {what: citations to code verified, how: "read local_fs.py, journal.py, process.py, git_runner.py, environment.py at the working tree", result: pass}
  - {what: quote digests and review_input digest, how: "shell refused in ask mode", result: not-run}
  - {what: evidence pages and web contracts, how: "not opened; no web lookup by rule", result: not-run}
  notes:
  - "The blocking findings F-1 and F-2 rest on absence records. The other findings rest on reading only."
  - "Covered: TB-1, TB-2, TB-3, dependency changes (rich==15.0.0 adds no new package, A-51), and data exposure. Not examined: licence compliance of the bundled snapshots, and the content of the foundation text."
  - "This is an additional check, not a guarantee."
```

**Summary for the person**

The two blocking findings are both cheap to fix in the design text:
- **F-1:** add a rule for validating the user-home roots to ADR-002. The same rule belongs in the SAFE-001 amendment that constraint K-1 waits on.
- **F-2:** state an output template and allow-list for hook context in ADR-004.

Of the rest, F-3 to F-6 are worth closing before the plan, because they make the network-install control, the process list, the backup file permissions and ownership of shared JSON entries exact. F-7 to F-9 can be settled during the plan.
</response>

## Author's responses

The reviewer read the revision c024f55 from `packed-refs`, which is stale. The worktree's HEAD is 8994354, as `git log` showed when the design started. The design files are uncommitted drafts in that worktree. The findings concern content, so this does not change them.

| Finding | Response |
|---|---|
| F-1 (blocking) | Accepted. ADR-002 decision 1a is the root-validation rule, also proposed as the SAFE-001 amendment text. Each root resolves under the real home directory: the `CODEX_HOME` or `COPILOT_HOME` value must lie under home, or it is refused. The root itself is not a link; it is owned by the current user; it is not inside a Git work tree. A missing root is created as a journalled change. Each root's resolved path appears in the preview. BC-6 adds a linked root and an env-var root outside home. |
| F-2 (blocking) | Accepted. ADR-004 decision 1a builds hook context only from fixed templates in the workflow package. The variable fields are: versions matching a strict version pattern; the next command, from a closed set; and, for post-edit, a lock path that is a valid CanonicalPath, with control and bidirectional characters removed and a 200-character cap. No other repository text is copied. The working-directory payload field per client is named in the decision and cited in the plan. BC-14 and BC-15 add a hostile-lock golden test. |
| F-3 | Accepted. TB-2 now reads "pinned top-level versions; transitive dependencies resolved at install". The managed-Python download is a TB-2 crossing. K-3 now covers how the pinned uv and pipx versions ignore user configuration; failing that, the preview reports the configured index. The security consideration records the residual supply-chain risk. |
| F-4 | Accepted. The version check is the fixed vector `uv tool list`, through `ProcessRunner`. A `graphify` on `PATH` that uv does not manage is reported and never run. The check also runs under `--dry-run`, as a read-only process. BC-7 and BC-9 cover it. |
| F-5 | Accepted. User-scope backups and journals are written with mode 0600, and the `user/` data directory is created 0700. Previews, conflicts and `--json` output never print a shared file's content. New BC-29. |
| F-6 | Accepted. Only an entry with a matching manifest hash is replaced or removed. A matching command with no manifest record, or with a different hash, is a conflict. BC-6 and BC-8 are updated. |
| F-7 | Accepted. `install` and `status` report the `orqlet` that `PATH` resolves to, and flag it when it differs from the running executable. |
| F-8 | Accepted. ADR-007 decision 8: dynamic text is printed with Rich markup off, and control characters other than newline are removed. BC-22 adds a case with escape codes in tool output. |
| F-9 | Accepted. ADR-006 passes `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, `ALL_PROXY`, `SSL_CERT_FILE` and `SSL_CERT_DIR` to tool preparation, lower-case forms included. These are values the person controls. No value is printed. |
