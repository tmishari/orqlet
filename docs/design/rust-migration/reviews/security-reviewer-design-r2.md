# Security review of the rust-migration design, round 2 (the security reviewer's first round)

Reviewer: orqlet-security-reviewer subagent (6e5e3ea0-9416-49f5-90ab-491220c35de7), fresh context, model named by the client as Claude Opus 5.5.
Design file hashes of this round, given to the reviewer in its prompt:

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#f58ea407ad8fed98390a7b90ccff6ce879d5db8161c11fd7465e01d232b9012d
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#2b5ee44d552937e6443a130aeae62aff90a1a4d1ddd7768cc23af32eb79893bc
docs/design/rust-migration/design/adr-003-libraries.md#5afd758782e23fdc2ddf64dfa5dd15f22b415b0a1cd2cba09ce59bf45e0bc497
docs/design/rust-migration/design/adr-004-version-and-hashes.md#59f15d4d22da7c7b17932e5fcef54ddcdd56e0af9bf07c1b75bf86568536b1a9
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#5574172c7b7354e956cf8cebdd2cb0633218cea77bb482edb40e1669c2735cb9
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#a8b65acefe7be9a4e72dc9facdd92ddbc2ee081834d089b169062c89b897b13b
docs/design/rust-migration/design/component.md#4fbbdcde98929379c876044a88998ebe6f9294f0911591a25f69a7f9ce99b5e7
docs/design/rust-migration/design/views.md#5f43dc02c6a723966a82f29797a0da28fb04005bf5a8e85e43cbc742fb598601
docs/design/rust-migration/design/manifest.yaml#9b87f717147656d181864f49dc54ba6a81977c2919c4491d7fa289c1bc06d00d
```

The design files changed after this round (responses below), so round 3 reviews new hashes.

## Reviewer output (unchanged)

The design needs changes before approval: I found no blocking finding, but five major and seven minor ones. Its trust boundaries stay the same and it states the right controls. The problem is that in several places it lists fewer rules than 0.5.2 enforces, so a port that follows the design to the letter would weaken those controls without anyone noticing. No acceptance criterion covers the Git hardening, file-system confinement or path rules.

**Hash check: not run.** The shell was blocked in this session, so I could not hash the files. What I could check: the manifest records the same SHA-256 that you gave for all eight artifacts (D-1 to D-5 and ADR-001 to ADR-006). Nothing records a hash for the manifest itself. Neither check proves the file bytes match.

## Findings (orqlet.finding/v1)

```yaml
- id: SEC-D-1
  severity: major
  location: manifest.yaml EC-6 (lines 99-101); component.md section 4 line 42 and BC-7 line 67
  evidence: >
    src/orqlet/adapters/git/git_runner.py lines 33-50 (inside A-17's own cited range 18-50) and
    86-116: forbidden options (ls-files --modified/--eol, cat-file --filters/--textconv,
    diff-* --ext-diff/--textconv); ls-files short clusters holding "m"; diff-index requires --cached;
    --no-ext-diff --no-textconv injected for diff-tree and diff-index; init_repository checks the
    branch name; extra environment LC_ALL=C, GIT_TERMINAL_PROMPT=0, GIT_PAGER=cat,
    GIT_OPTIONAL_LOCKS=0. environment.py lines 7-31: case-insensitive allow-list.
    git_runner.py lines 34-36 say these rules came from a hostile-configuration test, and that
    test was removed with the test suite.
  finding: >
    The design reduces GitRunner to "allow list, config overrides, 30 s, 16 MiB, scrubbed
    environment". The option rules, the injected flags, the init path and the extra variables are
    not named anywhere, and no acceptance criterion tests GitRunner. BC-7 only tests where
    Command may appear and that ProcessRunner refuses git.
  needed: >
    EC-6 and component section 4 name the full 0.5.2 GitRunner rule set (or cite git_runner.py
    18-116 as normative). Add an acceptance criterion with a hostile repository configuration
    (filter.*.clean, diff.external, textconv, core.fsmonitor, hooks) for each allowed subcommand.
    Also test that the child environment holds only the allow-list (env_clear, then add back).

- id: SEC-D-2
  severity: major
  location: adr-003-libraries.md line 29; manifest.yaml EC-6; component.md BC-6 line 66
  evidence: >
    yaml_loader.py lines 1-7, 27-49, 59-63 and 115-118 refuse non-string keys, allow only core tags,
    and use a narrow resolver: decimal integers only, floats without inf or nan, null forms
    ~/null/empty, dates stay strings. Input must be UTF-8. ADR-003 lists only documents, aliases,
    anchors, merge keys, tags, duplicates, strict booleans, depth, nodes and size.
  finding: >
    Three 0.5.2 rules are missing from the Rust rule set, so BC-6 does not test them:
    non-string keys, the narrow scalar resolver, and UTF-8-only input. If serde-saphyr resolves
    0x/0o integers or .inf/.nan, values change type. A numeric key such as 1 next to "1" can make
    two readers see different values. serde_json::Value may also turn a non-finite float into null
    (to confirm at the pinned versions).
  needed: >
    ADR-003 and EC-6 list every 0.5.2 rule. Either confirm that serde-saphyr does each one at the
    pinned version, or add an Orqlet check after parsing. BC-6 covers each rule.

- id: SEC-D-3
  severity: major
  location: manifest.yaml EC-6; views.md data flow line 39; component.md section 6 (no criterion)
  evidence: >
    local_fs.py lines 1-10, 55-61, 114, 137 and 186-200: every path component is refused if it is
    a link, a junction or any reparse point (the FILE_ATTRIBUTE_REPARSE_POINT attribute); reads use
    O_NOFOLLOW to close the race on the last component; temporary files come from mkstemp
    (exclusive create). EC-5 does not allow libc for the adapters, and every crate forbids unsafe
    code (ADR-001 decision 7).
  finding: >
    The design does not say how confinement is built. The Rust standard library has no O_NOFOLLOW
    constant without libc. A port that uses only is_symlink() on Windows would likely miss
    non-surrogate reparse points (to confirm). No acceptance criterion covers links, reparse
    points, staying in the root, or atomic replace.
  needed: >
    Decide how the last component is opened without following a link: add libc to the adapters
    allow-list, or use per-target constants. Check the reparse attribute on Windows. Create
    temporary files with create_new. Add an acceptance criterion for a link on any component,
    an escape outside the root, and a write interrupted between the temporary file and the rename.

- id: SEC-D-4
  severity: major
  location: adr-001-crate-per-layer.md decision 2 (line 10) and Consequences (line 22)
  evidence: >
    paths.py line 23 and lines 35-37 refuse Unicode categories Cc, Cf and Cs; lines 46-47 refuse
    a component that folds to .git. The domain crate may depend only on sha2 and
    unicode-normalization.
  finding: >
    Refusing format characters (Cf: zero-width and bidirectional controls) needs Unicode
    category data. The Rust core library and the two allowed crates do not provide it, and the
    design does not mention it. Dropping the rule makes names such as ".g\u200cit" possible, which
    a file system that ignores such characters treats as .git, and allows bidi-spoofed names.
    No acceptance criterion covers the CanonicalPath refusals.
  needed: >
    Name a pinned source of Unicode category data for the no_std domain: an allow-listed crate or
    a generated table. Add an acceptance criterion for every refusal of A-15, including Cf
    characters and reserved device names.

- id: SEC-D-5
  severity: major
  location: adr-006-standards-profile-documents.md decision 2 (line 16); manifest considerations.security
  evidence: >
    technology_scanners.py lines 190-212 and common.py lines 13 and 40: 0.5.2 already reads
    Cargo.toml, with a 1 MiB limit and a fixed table of known crates. It records rust-version as
    any string.
  finding: >
    Cargo.toml is not new input; what is new is that the profile's kind, facts.rust and the
    package manager are derived from it. The design states no size limit value, no rule against
    following path, workspace or [[bin]] path entries, no check on the shape of rust-version,
    no requirement that frameworks come only from the known-crate table, and no test with a
    hostile Cargo.toml. These values end up in rendered agent instructions.
  needed: >
    State the scanner's rules. It reads only Cargo.toml and Cargo.lock at the scope, through the
    FileSystem port, at most 1 MiB, UTF-8. It follows no path values and never runs cargo or rustc.
    rust-version must match a version pattern, with a length cap. Frameworks come from the
    known-crate table only. Add an acceptance criterion for hostile input.

- id: SEC-D-6
  severity: minor
  location: adr-003-libraries.md TOML row (line 15); EC-5 allow-lists
  evidence: >
    domain/dependencies.py lines 13, 53 and 72, and application/usecases/validate_model_policy.py
    lines 25 and 609-627, parse untrusted TOML in the domain and application layers. The toml
    crate is allowed only in the adapters crate.
  finding: >
    Two untrusted TOML readers are not placed in the Rust design, and their limits (size, UTF-8,
    nesting) are not specified. Whether the toml crate limits nesting at the pinned version is
    unknown.
  needed: List every TOML input with its port and limits; the plan confirms the nesting behaviour.

- id: SEC-D-7
  severity: minor
  location: adr-001-crate-per-layer.md decision 4; component.md line 42
  evidence: >
    A search of src/orqlet shows that the only shipped user of ProcessRunner is the Git code
    (wiring.py lines 108, 170 and 207; vcs_git.py; git_runner.py).
  finding: >
    The public run refuses "git" by name, a denylist whose matching is not specified: path, case,
    .exe/.cmd/.bat. No shipped caller needs the public entry.
  needed: >
    Either make starting a process crate-private for GitRunner, or specify the refusal as a
    case-insensitive match on the file stem, ignoring the directory and PATHEXT extensions.

- id: SEC-D-8
  severity: minor
  location: adr-006 decision 1 (SEC-002 bullet, line 15); ADR-001 decisions 3-5
  evidence: >
    The rewritten rule names only the strict YAML loader. serde_json is allowed for the
    application crate; serde-saphyr's default entry points do not apply the strict options.
  finding: >
    Nothing mechanical stops a direct serde_json::from_* or serde_saphyr::from_* call on
    untrusted bytes. Nothing checks where the scoped clippy allows are placed either.
  needed: >
    Disallow those entry points in clippy.toml outside documents/. SEC-002 names the strict JSON
    reader too. Optionally, xtask checks where allow(clippy::disallowed_*) appears.

- id: SEC-D-9
  severity: minor
  location: component.md section 3 (hook) and the Panic row of section 5 (line 55)
  evidence: hook.py lines 43-48 read at most MAX_PAYLOAD_BYTES+1 bytes; any error gives {} and exit 0.
  finding: >
    The design does not say that reading standard input is bounded. Its panic row (ORQ-E900,
    exit 70) contradicts the hook's rule that it always exits 0.
  needed: >
    Read at most limit+1 bytes; a panic in the hook prints {} and exits 0 (panic=unwind,
    catch_unwind); add an acceptance criterion.

- id: SEC-D-10
  severity: minor
  location: manifest.yaml security_globs (lines 43-54); ADR-001 decision 6
  evidence: >
    Cargo.toml and crates/*/Cargo.toml are listed; Cargo.lock and rust-toolchain.toml are not.
  finding: >
    Changes to transitive dependencies (build scripts, procedural macros) are not routed to
    security review. It is unclear whether xtask arch checks only direct dependencies.
  needed: Add Cargo.lock to security_globs and state whether transitive dependencies are checked.

- id: SEC-D-11
  severity: minor
  location: manifest.yaml EC-6; adr-004 decision 5
  evidence: >
    journal.py line 38 opens the data directory with private=True (files 0600, folders 0700,
    local_fs.py lines 36-38).
  finding: >
    The design does not state private modes for the journal and backups, which hold copies of
    project files. Journal paths read back on resume or rollback are untrusted, and the design
    does not say they are parsed again as CanonicalPath.
  needed: >
    State the 0600/0700 modes for the data directory. On resume or rollback, journal targets are
    parsed again as CanonicalPath and written only through the project FileSystem.

- id: SEC-D-12
  severity: minor
  location: adr-004 decision 5; component.md constraints line 93
  evidence: >
    0.x journals are not read, and the data directory may move (U-10). The only safeguard is the
    procedure "finish open 0.5.2 changes first".
  finding: An interrupted 0.5.2 change is invisible to 1.0.0, which then upgrades over it.
  needed: >
    1.0.0 refuses (ORQ-E131) when its data directory holds a journal it cannot read. The release
    notes state the procedure.
```

## Observations (not blocking)

- The data directory location differs between platformdirs and `dirs`, so the two apply locks do not exclude each other. The design's rule that both binaries never run on one project at once covers this.
- The serde-saphyr evidence was read from the master branch documentation, not from the pinned version. The plan must confirm it at the pinned version; BC-6 reduces the risk.
- Linux and Windows are only compiled and linted (Q-15), with no CI. The Windows-only controls (reparse points, retrying the rename, case-insensitive environment names) ship without ever being run.
- Integration tests that call `git` directly should use `GIT_CONFIG_NOSYSTEM` and a null `GIT_CONFIG_GLOBAL`. Otherwise a developer's global hooks or fsmonitor setting runs during the tests.
- Killing a child on timeout kills only the direct child. The reader threads should have a bounded wait (0.5.2 has the same gap).
- Changes that help security:
  - The Rust `regex` crate runs in linear time, and its `$` is stricter than Python's.
  - serde_json refuses lone surrogates.
  - The upgrade sequence checks the hashes again after taking the lock.
- Changing the path comparison from `casefold` to NFC plus `to_lowercase` does not open a way around the `.git` check that I could find; I checked the characters that fold to i, g or t. Detecting collisions on case-insensitive file systems may differ for characters such as ß.
- The 0.5.2 fixtures should hold only verdicts, codes and help text. Review them for secrets before committing (SHA-256 only, no secrets).
- I found no secrets, MD5 or SHA-1 and no language-model SDK in the files I read.

## Self-check

```yaml
schema: orqlet.self-check/v1
checked_against:
  role: security-reviewer
  phase: design
  model: Claude Opus 5.5 (this session); fresh context, no Coder or Architect conversation
  revision: branch rust-migration-design, HEAD not read (no shell); design base 3e3c311
checks:
  - {what: file hashes of this round, how: shasum, result: NOT_RUN (shell blocked in this session)}
  - {what: manifest artifact hashes vs given hashes, how: read manifest.yaml lines 105-115, result: "equal for all 8; manifest.yaml itself not checked"}
  - {what: design set, AS-IS, ledger, five evidence files, design format, standards output, rules.yaml, how: read in full, result: done}
  - {what: cited controls, how: "read yaml_loader.py, git_runner.py, environment.py, local_fs.py, strict_json.py, hook.py, apply_lock.py, paths.py 1-60, wiring.py 60-119", result: done}
unverified:
  - "Beyond the listed paths, I read cited sources and ran search-only queries (Cargo.toml/TOML readers, ProcessRunner users, private=True) to verify design claims; I did not read journal.py, dependencies.py or user_scope.py in full."
  - "Library behaviour named as 'to confirm' (serde-saphyr resolver, serde_json non-finite floats, Windows is_symlink, toml nesting) comes from memory, not documentation; the plan must confirm it."
  - "This review is an additional check, not a guarantee."
```

Questions from the reviewer: whether `xtask arch` checks transitive dependencies, whether the TOML dependency reader (`domain/dependencies.py`) is ported, and whether `ORQLET_DATA_DIR` must be refused when it points inside the repository.

## Architect's responses

- SEC-D-1: The new ADR-007 decision 2 makes `git_runner.py` lines 18-116 normative and lists every rule it contains. Decision 1 adds `env_clear` and the case-insensitive allow-list. BC-18 is the hostile-configuration criterion: filter, external diff, textconv, fsmonitor and hooks, plus forbidden options and the child environment.
- SEC-D-2: ADR-007 decision 3 lists every rule of `yaml_loader.py`, including string-only keys, the scalar resolver of lines 36-49 and UTF-8 only. Any rule serde-saphyr lacks at the pinned version is checked by the documents module after parsing. BC-6 covers each case and each scalar form. Strict booleans are marked as new behaviour.
- SEC-D-3: ADR-007 decision 7 specifies the confinement. Every component is checked with `symlink_metadata` plus the reparse attribute 0x400 on Windows. The last component is opened with `O_NOFOLLOW` from `libc`, which is Unix only and on the adapters allow-list. Temporary files use `create_new`. The writes are synced and renamed, with retries on Windows. BC-19 covers links on any component, failed writes and the private modes. Escapes are refused by CanonicalPath (BC-20).
- SEC-D-4: ADR-007 decision 8 adds a pinned no_std Unicode category crate to the domain allow-list. The candidate was not looked up, so the plan confirms it and stops and asks if it does not fit. BC-20 covers every refusal of A-15.
- SEC-D-5: ADR-007 decision 11 states the scanner rules: scope files only, 1 MiB and UTF-8, no `path` or `[[bin]] path` following, literal workspace members only (at most 32, each a CanonicalPath), a `rust-version` pattern with a length cap, and frameworks from the known-crate table only. BC-20 includes hostile Cargo.toml cases.
- SEC-D-6: ADR-007 decision 5 lists every TOML input with its port and limits. The domain code of `dependencies.py` is ported, because it is wired through the expected-change check, and it receives values the documents module has already parsed. The plan confirms the nesting behaviour of `toml`.
- SEC-D-7: Process creation is crate-private to the Git module (ADR-007 decision 1, ADR-001 decision 4).
- SEC-D-8: ADR-007 decision 6 disallows the text and byte entry points of serde_json, serde-saphyr and toml outside the documents module, and SEC-002 names all three readers. A check on where the allows are placed is not added; the allows are in files under the security globs.
- SEC-D-9: ADR-007 decision 10 bounds the read and catches a panic so the hook still prints `{}` and exits 0. The failure table now separates hook failures from panics elsewhere.
- SEC-D-10: `Cargo.lock` and `rust-toolchain.toml` are in the security globs. `xtask arch` checks direct dependencies only, and ADR-001 decision 6 says so.
- SEC-D-11: ADR-007 decisions 7 and 9 state the 0600 and 0700 modes, and that journal targets are parsed again as CanonicalPath and written through the project FileSystem.
- SEC-D-12: ADR-007 decision 9 and ADR-004 decision 5 make 1.0.0 refuse to upgrade with ORQ-E131 while its data directory holds an unreadable journal entry. The release notes state the procedure.
- Questions: `xtask arch` checks direct dependencies only, and transitive ones go through `Cargo.lock` review. `dependencies.py` is ported. 0.5.2 does not refuse an `ORQLET_DATA_DIR` inside the repository (`wiring.py` lines 83-86), and the port keeps that behaviour, since no answer asks for a change. It is raised with the person as a possible later change.
- Observations: the git-test isolation is in ADR-002 decision 4, and the fixture secret review in ADR-002 decision 2. The other observations are noted; the Linux and Windows test gap is stated in ADR-007's consequences.
