# Architecture review of the rust-migration design, round 2

Reviewer: orqlet-arch-reviewer subagent (783f7200-b0ea-46fc-aec8-237a9665a90e), fresh context, model named by the client as Claude Opus 5.5.
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

I'm requesting changes on round 2. There are no blocking findings, six major and eleven minor. Round-1 F-1, F-5, F-7 and F-9 are resolved. The other eight are partly resolved, and what is left of them is in the findings below. Six of the new findings are major:

- **Project kind:** the Cargo.toml detection rule would not record this repository as rust-cli.
- **Rule scopes:** ADR-006 leaves the new `workflow/` folder outside the rewritten rule scopes.
- **Application guard:** the Clippy list misses file I/O done through `Path` methods.
- **Git refusal:** the rule that ProcessRunner refuses `git` is underspecified.
- **Strict JSON:** oversized integers are now read as floats, a change the person never approved.
- **Kept hashes:** the AGENTS.md block-marker hash is not among the kept algorithms.

**Hashes: not run.** The sandbox refused every shell command, so I could not hash the files. The nine values you gave match the `sha256` values the manifest records for its eight artifacts. The manifest does not record its own hash, so I could not check `9b87f717…` at all. Compared with round 1, `adr-005` and `views.md` are unchanged and the other seven files changed.

**Reviewer record.** The client names my model as Claude Opus 5.5. I ran in a fresh context with only the paths you listed. I did not open source files the design cites directly (`errors.py`, `hook.py`) or the evidence behind the A-n facts, because your path list excluded them.

## Round-1 findings: are they resolved?

| R1 | Status | Where the rest went |
|---|---|---|
| F-1 | Resolved | — |
| F-2 | Partly: the mechanism is named, but how the name is compared is not | F-4 |
| F-3 | Resolved for processes; file and environment use in tests is not covered | F-8 |
| F-4 | Resolved; the allow-list meaning is unclear | F-7 |
| F-5 | Resolved; the globs are narrower than the Python glob | F-15 |
| F-6 | Partly: the rules are stated, but one rule is relaxed and some limits have no source | F-5, F-10 |
| F-7 | Resolved; one possible header difference remains | F-9 |
| F-8 | Partly: the constraint was added, but ADR-006's scopes don't follow it | F-2 |
| F-9 | Resolved; the toolchain version has no evidence (observation) | — |
| F-10 | Resolved by procedure only; the citation was not opened | observation |
| F-11 | Partly | F-11 |
| F-12 | Partly | F-13 |

```yaml
findings:
  - id: F-1
    severity: major
    location: adr-006 decision 2; BC-11; adr-001 decision 1; adr-003 Toolchain row
    evidence: "The scanner reports rust-cli 'when it declares a binary target or src/main.rs exists', and the rust fact is 'the rust-version of Cargo.toml'. The root Cargo.toml is a workspace whose binary is crates/orqlet-cli, and 'the workspace sets rust-version' (ADR-003). After removal no src/main.rs exists."
    finding: "As written, profiling this repository finds no binary target and no rust-version in the root manifest, so BC-11 cannot pass."
    needed: "Define detection for a workspace: whether member manifests are followed, and whether rust-version is read from [package] or [workspace.package]. Cite which file and lines the facts use."
  - id: F-2
    severity: major
    location: adr-006 decision 1; component §9 constraint 2; rules.yaml
    evidence: "In rules.yaml, MODEL-001 covers src/orqlet/** (packaged files), DET-002 covers src/orqlet/workflow/**, and ARCH-003 covers src/orqlet/workflow/**. EC-3 moves the data to workflow/**. ADR-006 sets ARCH-001 to crates/** and xtask/** only, while §9 says the src/orqlet/** scopes stay until removal. ADR-006 adds xtask/** to SAFE-001 ('every write goes through a journalled change plan') and SEC-002 ('read them through the FileSystem port'), yet ADR-005 has xtask write workflow/ directly, and the tests write temporary repositories. ARCH-002 lists two commands as one check. ARCH-003 is half review and half 'checked by xtask arch'. Each rule has one enforcement and one check_ref."
    finding: "The rewritten rules leave workflow/** out of every scope. ADR-006 does not state the scopes of ARCH-002, ARCH-003, DET-001 and DET-003. ARCH-001 contradicts §9. SAFE-001 and SEC-002 would be broken by the xtask and the tests as designed. DET-001 (--update-golden, 'never in CI') and the header ('see pyproject.toml and CI') are not addressed."
    needed: "State every rule's new scope, enforcement and check reference. Include workflow/**. Either exclude xtask/** and crates/*/tests/** from SAFE-001 and SEC-002, or state a waiver with a reason. Make ARCH-001 agree with §9."
  - id: F-3
    severity: major
    location: adr-001 decision 3; BC-8; adr-006 ARCH-002; evidence clippy-disallowed-types.md items 3-4
    evidence: "Clippy takes disallowed items 'written as fully qualified paths', so a module cannot be banned as a whole. ADR-001 disallows 'the types and functions of std::fs, std::process, std::net and std::env'."
    finding: "File I/O is still possible without naming std::fs: Path::exists, metadata, read_dir and canonicalize, std::os::*::fs, and standard input and output through std::io and the print macros. BC-8 claims the application 'fails Clippy on file ... use', which this list does not deliver. Nobody is named to keep the enumerated list complete."
    needed: "Name the disallowed paths, including the Path file-system methods and the standard input and output entry points, and who maintains the list. Otherwise mark what is left as a review check in BC-8 and ARCH-002."
  - id: F-4
    severity: major
    location: adr-001 decision 4; BC-7; EC-6; failure table
    evidence: "'Its public run refuses the program git (and git.exe).' The ProcessRunner port takes any argv (A-16)."
    finding: "The comparison is not specified: an absolute path such as /usr/bin/git, case on case-insensitive file systems (GIT, Git.EXE), or a wrapper such as env, sh -c or cmd /c with git as an argument. BC-7 could pass while Git still starts outside GitRunner. Nothing says which non-Git programs ProcessRunner exists to run."
    needed: "Specify the rule (for example, the last path component without the .exe suffix, compared case-insensitively), and how wrappers are handled, or replace the refusal with an allow-list of programs. Make BC-7 test those cases."
  - id: F-5
    severity: major
    location: adr-003 'Strict JSON'; BC-2; BC-17; A-14
    evidence: "'An integer literal outside the 64-bit range is read as a float, where 0.5.2 refused it ... Q-5 allows this.' Q-5 is about byte compatibility of hashes and emitted files. A-14 lists oversized integers among the things refused."
    finding: "This relaxes a strict-input control and makes BC-2 (same codes for the same inputs) false for such input, on the strength of a question that did not ask about it. If any command reads and rewrites a JSON file, the float conversion may lose the value; whether one does is unknown."
    needed: "Refuse such integers, for example by scanning the raw number token. Otherwise raise a ledger question for the person, and list the difference in the parity fixture."
  - id: F-6
    severity: major
    location: adr-004 decisions 2 and 4; BC-5; A-20; C-7
    evidence: "ADR-004 keeps digest_of, the line-range hash and the file hash. A-20: each managed block in AGENTS.md carries the hash of its normalised body. C-7: the lock stores a plain SHA-256 of the standards lock, while gate status hashes it with CRLF read as LF."
    finding: "The block-marker hash and its normalisation are not kept or specified. If they differ, 1.0.0 treats every 0.5.x block as edited by the team, and the AGENTS.md re-render (§9) and BC-5 fail. C-7 is not resolved for 1.0.0."
    needed: "Add the block-marker hash, with its normalisation, to the kept algorithms and to the BC-3 vectors. State which standards-lock hash each consumer uses."
  - id: F-7
    severity: minor
    location: adr-001 decision 6; EC-5; adr-006 ARCH-003
    evidence: "EC-5 says 'orqlet-application adds …', 'orqlet-adapters adds …'. ARCH-003's embedding half is 'checked by xtask arch, since only that crate may depend on include_dir'."
    finding: "Several points are unstated: whether the allow-lists are exact or cumulative, whether direct or transitive crates count (sha2 and dirs pull in several crates), whether build-dependencies count, and the xtask's own allow-list (serde_json, schemars). If the lists are cumulative, the CLI may depend on include_dir. include_str! and include_bytes! embed files without any crate."
    needed: "State the allow-list semantics and the xtask list. Mark the embedding half of ARCH-003 as review, or extend the check."
  - id: F-8
    severity: minor
    location: adr-001 decisions 3 and 5; adr-002 decision 2; adr-005 decision 3; BC-9
    evidence: "Clippy runs with --all-targets -D warnings. The application's clippy.toml disallows std::fs and std::env. Decision 5 scopes allows only for starting processes. The parity test 'runs on a checkout of the same revision'."
    finding: "Tests in the application crate that read fixtures or use temporary folders fail Clippy. The design does not say which crate holds the BC-4 and ADR-005 tests, or how cargo test obtains the 3e3c311 checkout (a Git worktree needs full history)."
    needed: "Name the crate for each fixture-reading test, and how the checkout is produced. Extend the scoped allows to file and environment use in tests, or say tests embed their fixtures."
  - id: F-9
    severity: minor
    location: BC-4; component §9 constraint 1
    evidence: "Artifact headers bind workflow_version 0.5.2 (A-32). The Rust binary carries 1.0.0 (BC-13). §9 says 'so bindings agree'."
    finding: "Whether validate compares the header workflow_version with the running binary is unknown. If it does, BC-4 cannot match 0.5.2 for every artifact."
    needed: "State the behaviour, or list it in the fixture as an expected difference."
  - id: F-10
    severity: minor
    location: EC-6 ('same limits'); adr-003 Strict YAML and Strict JSON; failure table
    evidence: "A-13 names only 1 MiB, depth 32 and 50,000 nodes. A-14 names no size or depth. A-19 names no retries. ORQ-E131 and ORQ-E137 appear in no AS-IS fact."
    finding: "Single document, no aliases or anchors, merge keys, unknown tags, duplicate keys, strict booleans, 1 MiB and depth 64 for JSON, and 'five retries' are stated as 0.5.2 behaviour without a fact. Strict booleans may change verdicts, for example for yes and no."
    needed: "Cite a source for each, or mark it as new behaviour that BC-4 will surface."
  - id: F-11
    severity: minor
    location: adr-003 Regular expressions row; component §3 (U-11)
    evidence: "U-9 says the engine behind Pydantic's patterns is unknown. ADR-003 states 0.5.2 as 'Python's $'. §3 promises Orqlet's text lines keep their 0.5.2 wording, while U-11 says the renderers were not traced."
    finding: "U-9 is settled by assumption. The wording promise has no fixture and no criterion."
    needed: "Phrase the regex row without asserting the 0.5.2 engine. Add the text output to the fixtures, or drop the promise."
  - id: F-12
    severity: minor
    location: adr-001 decision 8; adr-006 ARCH-003; Q-8; C-2; rules.yaml SAFE-001
    finding: "The design never says that the user-scope file system, its journal and the Copilot adapter are not ported, or whether hook accepts copilot (C-2). The rewritten ARCH-003 still names four adapters, and SAFE-001 describes a user-scope adapter that will not exist."
    needed: "State the Q-8 outcome for each item and for C-2, and adjust the ARCH-003 and SAFE-001 text."
  - id: F-13
    severity: minor
    location: EC-1; BC-12
    evidence: "EC-1 says 'reported as manual or NOT_RUN'. BC-12 and the failure table say NOT_RUN. The three manifest paths have no AS-IS fact."
    finding: "Round-1 F-12 is only partly resolved."
    needed: "Align EC-1 with BC-12, and cite where the three paths come from."
  - id: F-14
    severity: minor
    location: adr-002 decision 1; component §9 constraint 3
    evidence: "ADR-002: 'until the Rust build passes BC-1 to BC-11'. §9: 'BC-1 to BC-11 and BC-17'. BC-16 (unsafe code forbidden) is in neither."
    finding: "The removal gate is stated two different ways."
    needed: "State it once, and decide whether BC-16 is part of it."
  - id: F-15
    severity: minor
    location: manifest extractor_config.security_globs
    evidence: "The Python glob covered src/orqlet/adapters/** as a whole. The Rust globs cover process/, git/, fs/ and documents/ only. hook parses untrusted standard input in the CLI crate, and #![forbid(unsafe_code)] sits in the crate roots."
    finding: "The narrowing is not explained. clients/, render/, the embedding module, the hook command and the crate roots are outside the globs."
    needed: "Give the reason, or add the globs (or move unsafe_code into [workspace.lints] in the root Cargo.toml, which the globs already cover)."
  - id: F-16
    severity: minor
    location: manifest standards_applied; reviews/architecture-reviewer-design-r1.md
    evidence: "In rules.yaml, MODEL-002 covers docs/design/**, and the scope includes docs/design/work-status.md. The round-1 record names a subagent id but no model."
    finding: "MODEL-002 is missing from standards_applied. The round-1 record does not name its model or say the model is unknown."
    needed: "Add MODEL-002, and record the model, or 'unknown', in each review note."
  - id: F-17
    severity: minor
    location: BC-9; adr-003 Toolchain row
    finding: "The Linux and Windows target triples, and whether rust-toolchain.toml lists them, are not named."
    needed: "Name the triples."
observations:
  - "I did not hash the files (shell refused). The given hashes match the manifest's eight recorded artifact hashes. The manifest's own hash and the upstream as-is hash bf3d2d… were not checked."
  - "The header applicable_rules_hash 15dad7d0… matches neither hash in /tmp/rm-standards.txt. How it is computed is still unknown."
  - "Standards were queried for two paths, src/orqlet and the rules and tools paths, out of a scope of 23 path patterns. Seven of the 14 ids in standards_applied are absent from the output because their globs do not match 'src/orqlet'."
  - "extractor_config still has no dependency_manifests or lockfiles; EC-5 is verified manually."
  - "The Clippy evidence does not show that disallowed-types fires on an expression path such as Command::new. Per item 1 of that evidence, CLIPPY_CONF_DIR overrides the per-crate files. Nothing checks that each allow carries a reason."
  - "Per item 4 of the File::try_lock evidence, a lock file opened only for append cannot be locked on Windows."
  - "Nothing cites evidence that the toolchain 1.100.0 exists, or that File::try_lock is stable in it."
  - "include_dir reads a folder outside the crate, and its rebuild tracking was not checked; ADR-003 already says so."
  - "An open 0.x journal is ignored silently. Only the procedure in §9 guards against it."
  - "Removal deletes *.py files only. Whether non-Python files left under src/orqlet/ go away is not stated, and BC-14 checks *.py files only."
  - "The scope lists .github/** and .gitattributes without a named change, although Q-15 says no CI."
  - "The review notes named in the manifest do not exist yet."
  - "No phase order is in the design, and each constraint carries a reason."
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: design}
  model: "Claude Opus 5.5 (as named by the client); fresh context limited to the given paths"
  checks:
    - {what: D3 artifacts and brief section order, how: read manifest, component, views and six ADRs, result: pass}
    - {what: ADR sections and rejected alternatives, how: read all six, result: pass}
    - {what: round-1 findings resolved, how: compared each response with the current text, result: "4 resolved, 8 partly resolved (carried over as F-2, F-4, F-5, F-7, F-8, F-9, F-10, F-11, F-13, F-15)"}
    - {what: Q-5 to Q-15 respected, how: compared the ledger answers with the ADRs, result: "pass, except F-5 (Q-5 stretched) and F-12 (Q-8 incomplete)"}
    - {what: web evidence supports ADR claims, how: read five files, result: "pass, except F-3"}
    - {what: file hashes, how: shasum, result: "not run (shell refused); given values match the manifest"}
    - {what: brief within 1,200 words, how: estimate, result: "not run (estimate about 1,150 to 1,250)"}
    - {what: orqlet validate design, result: not run}
  unverified: ["Sources cited by the A-n facts and by the design directly (errors.py, hook.py) were not opened", "Branch not confirmed", "The three BC-12 manifest paths were not checked"]
```

Questions from the reviewer: whether strict JSON should keep refusing integers outside 64 bits (F-5), and whether the hashes and `orqlet validate design` can be run where a shell works.

## Architect's responses

- F-1: ADR-006 decision 2 defines workspace detection: a `[package]` with `[[bin]]` or `src/main.rs`, or a `[workspace]` whose literal members include one; the `rust` fact is `[package].rust-version`, else `[workspace.package].rust-version`, citing the line that holds it. Input rules are in ADR-007 decision 11.
- F-2: ADR-006 decision 1 is now a table that gives every rule its text, scope, enforcement and single check. `workflow/**` is in the ARCH-003, DET-001, DET-002 and MODEL-001 scopes. The Python scopes are replaced, not kept, because no Python change lands during the task. Section 9 now says so. SAFE-001 and SEC-002 are scoped to shipped code, so the xtask and the tests are outside them by scope. The DET-001 flag and CI clause and the header's mention of CI go.
- F-3: ADR-001 decision 3 names the disallowed paths. These are the `std::fs`, `std::process`, `std::net`, `std::env` and `std::os::*::fs` items, the file-system methods of `Path` and the standard streams, plus the `print_stdout` and `print_stderr` lints. The list is under the security globs and changed only by review, and a consequence states what is left to review. BC-8 tests each listed path.
- F-4: There is no name matching any more. Process creation is crate-private to the Git module (ADR-007 decision 1), because the only callers in 0.5.2 are the Git modules (`wiring.py` lines 108, 170, 207). BC-7 checks that the module cannot be reached from outside.
- F-5: Oversized integers are refused (ADR-007 decision 4). The 64-bit limit is lower than 0.5.2's digit limit, and the parity fixture lists the difference. No ledger question is needed, because refusing keeps the control.
- F-6: ADR-004 keeps the block-marker hash, with its normalisation cited (`instructions.py` lines 40-43, `emit.py` lines 33-36). It states which standards-lock hash each consumer uses (C-7). BC-3 covers all four algorithms.
- F-7: ADR-001 decision 6 says the lists are exact per crate. Every direct dependency counts, normal, dev and build, and transitive crates are checked by reviewing `Cargo.lock`. The xtask has its own list. ARCH-003 is a review rule and also covers `include_str!` and `include_bytes!`.
- F-8: ADR-002 decision 3 puts the fixture-reading tests in `crates/orqlet-cli/tests/` and describes the detached worktree of 3e3c311, including how the test fails on a shallow clone. ADR-001 decision 5 extends the scoped allows to file and environment use in tests. Application unit tests embed their inputs.
- F-9: The validators of as-is, design, plan and ledger do not compare `workflow_version` with the running binary. Only the model-policy check ORQ-W541 reads the release (`validate_model_policy.py` lines 405-415), and the fixture lists it as an expected difference (ADR-002).
- F-10: ADR-007 cites a source line range for each YAML, JSON, file-system and journal rule. The rename retry is in `local_fs.py` lines 33-52, ORQ-E131 in `upgrade.py` lines 80-88 and ORQ-E137 in `errors.py` line 20. Strict booleans and the 64-bit integer limit are marked as new behaviour. The unsourced JSON depth of 64 is replaced by serde_json's built-in limit, also marked new.
- F-11: The regex row no longer states what engine 0.5.2 used, and U-9 stays unknown. The text-wording promise is dropped: section 3 says text output may change and the envelope is the contract.
- F-12: ADR-001 decision 8 states the Q-8 outcome. The Copilot adapter, the user-scope writer with its journal, and the presenter are not ported, and `hook --client copilot` stays (C-2). The ARCH-003 and SAFE-001 texts are adjusted.
- F-13: EC-1 now says NOT_RUN with a finding. The three paths come from `rg -l public_api docs/design/*/design/manifest.yaml` at 3e3c311.
- F-14: The removal gate is stated once, in ADR-002 decision 1: every criterion except BC-14, so BC-16 is included. Section 9 refers to it.
- F-15: The security globs now cover the whole adapters source, the hook command, `crates/orqlet-domain/src/paths.rs`, `Cargo.lock` and `rust-toolchain.toml`. Forbidding unsafe code moved to `[workspace.lints]` in the root `Cargo.toml`.
- F-16: MODEL-002 is added to `standards_applied`. Each note records the model as the client names it.
- F-17: The triples are `x86_64-unknown-linux-gnu` and `x86_64-pc-windows-msvc`, with host `aarch64-apple-darwin`. `rust-toolchain.toml` lists them, and ADR-003 and BC-9 name them.
- Observations: the Windows append-only lock limit is in the ADR-003 lock row. Removal now deletes the whole `src/orqlet/` folder, and BC-14 checks it. Whether the toolchain exists is marked for the plan to confirm. `applicable_rules_hash` is the value `orqlet gate status` printed. `.github/**`, `.gitattributes` and `.gitignore` now have named changes in ADR-006 decision 7. CODEOWNERS names the Python paths, `.gitattributes` has lines for `tests/golden/**` and `*.whl`, and `/target` needs ignoring.
