# Architecture review of the rust-migration design, round 1

Reviewer: orqlet-arch-reviewer subagent (fe5ee7fc-4d79-480f-b009-3abd650123ab), own context.
Design file hashes of this round (the reviewer's prompt was cut before them, so it could not compare them):

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#e856c502eacfdca1a544c0eb849c2c9ea7b523ec6aebe934c25e6a3220759b14
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#baa6e786d46e5f9a227540d38a4a57194be53a4178d3c256d20fd12242515d60
docs/design/rust-migration/design/adr-003-libraries.md#b94a99501bdafcb8974ca758fa23e2f0e4e52daa7f3269e7987cd558af2b307e
docs/design/rust-migration/design/adr-004-version-and-hashes.md#809ee395109cd3987462c4872cd2e422b91ae4f149bb09159af6d505fd61e4c5
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#5574172c7b7354e956cf8cebdd2cb0633218cea77bb482edb40e1669c2735cb9
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#8e5d9a10a9bb4204810b91d52ddb202e04cc99e9e09bfbda527d7d82f5db2bc8
docs/design/rust-migration/design/component.md#528f5d3b517b90c7f5ec2663436f2c1cca10047aca92061721ac5450d4b5ec4a
docs/design/rust-migration/design/views.md#5f43dc02c6a723966a82f29797a0da28fb04005bf5a8e85e43cbc742fb598601
docs/design/rust-migration/design/manifest.yaml#a4fd6a5d994c958305f53a0283581a3a8fe8ff61c79de71d597c8a68bd091187
```

## Reviewer output (unchanged)

I reviewed the round-1 design for rust-migration and I'm requesting changes: one blocking finding, seven major and four minor. The findings and self-check below follow `orqlet.finding/v1`. That schema's text wasn't among the paths I was given, so I used these fields: id, severity, location, evidence, finding, needed.

**Inputs I could not check.** Your request ends at "Design file hashes for this round (round 1):" with no hashes after it. The read-only sandbox also refused shell commands. So I could not confirm the artifact `sha256` values in the manifest, count the words in `component.md` or confirm the branch.

```yaml
findings:
  - id: F-1
    severity: blocking
    location: adr-001 decision 2; manifest EC-5; component.md §4; adr-003 table
    evidence: "ADR-001 and EC-5 say orqlet-domain depends only on sha2 and unicode-normalization. Component §4 puts globs and the change plan in the domain, as do A-33 (domain/globs.py, domain/changeplan.py) and A-9 (domain/digest.py). ADR-003 picks the glob and similar crates for exactly those parts. Strict JSON (A-14) also sits in the domain today."
    finding: "The domain's dependency limit contradicts where its functions live. Nothing says which JSON value type digest_of takes, or where strict JSON goes."
    needed: "Decide where glob matching, the unified diff, the input type of digest_of and strict JSON live. Then make ADR-001, ADR-003, EC-5 and §4 agree."
  - id: F-2
    severity: major
    location: component.md BC-7; adr-001 decision 4
    evidence: "ADR-001 disallows only std::process::Command. SEC-001 says a reviewer checks the adapters."
    finding: "BC-7 says Git run outside GitRunner fails Clippy, but no decision provides that. Calling ProcessRunner with a git argv elsewhere would pass."
    needed: "Name a mechanism, or restate the Git half of BC-7 as a review check."
  - id: F-3
    severity: major
    location: adr-002 decision 3; adr-001 decision 4; BC-9
    evidence: "Integration tests run the built binary in temporary repositories. Clippy with --all-targets -D warnings covers tests, and the cli crate disallows Command. SEC-001 says every process starts through ProcessRunner."
    finding: "The design does not say how tests start the binary or Git without breaking SEC-001 or BC-9."
    needed: "State how test processes are started (through the adapter, or a scoped allow with a reason) and whether the rewritten SEC-001 covers tests."
  - id: F-4
    severity: major
    location: adr-001 decisions 1-3; BC-8; adr-006 (ARCH-001 check)
    evidence: "ARCH-001 is marked deterministic. ADR-001 relies on Cargo refusing cycles and on #![no_std]. The Clippy evidence (items 3-4) lists disallowed items as fully qualified paths."
    finding: "Three gaps. #![no_std] limits only the crate's own code, not its dependencies, so the 'pure computation only' rule has no check. No check fixes the allowed crate edges or keeps I/O-capable third-party crates out of application. 'Builds as no_std' does not say for which target. Observation, without evidence: Cargo may allow dev-dependency cycles."
    needed: "Name the deterministic checks (a no-std target build, and a crate-graph and dependency allow-list check), or mark those parts as review-only."
  - id: F-5
    severity: major
    location: manifest extractor_config.security_globs
    evidence: "Component §4 places the strict YAML loader in the adapters yaml/json/toml module, outside the fs/, git/ and process/ globs. The clippy.toml files and the module-level allow implement SEC-001."
    finding: "The Rust homes of two security controls fall outside every security glob."
    needed: "Add globs for the loader module, every clippy.toml and the lint configuration."
  - id: F-6
    severity: major
    location: EC-6; BC-6; component §4
    evidence: "A-14 lists the strict JSON rules: UTF-8 only, no duplicate keys, no NaN or Infinity, an object at the top level, no oversized integers, a depth limit. ADR-003 names only serde_json."
    finding: "Parity of the strict JSON control is not specified and no criterion tests it."
    needed: "State the strict JSON rules and add an acceptance criterion."
  - id: F-7
    severity: major
    location: adr-004 consequences; BC-4
    evidence: "Artifact headers bind workflow_version, protected_set_digest, standards_lock_hash and applicable_rules_hash (A-32). ADR-006 rewrites rules.yaml and re-renders the generated files."
    finding: "'Frozen tasks resume without re-citing' holds for line hashes but not for header bindings. BC-4 does not fix the repository state the two binaries are compared on."
    needed: "State the effect on other tasks' headers, and add a constraint, with its reason, fixing the state BC-4 compares."
  - id: F-8
    severity: major
    location: component §9; adr-006 decision 1
    evidence: "The standards output scopes ARCH-001, SEC-002 and MODEL-001 to src/orqlet/** and SEC-001 and STYLE-001 to src/**. ADR-006 moves scopes to crates/** only."
    finding: "Until the standards change lands, code in crates/** is bound only by the unscoped rules, and xtask/** stays outside them afterwards."
    needed: "Add a constraint that the new scopes apply no later than the first crate code, and decide whether xtask/** is covered."
  - id: F-9
    severity: minor
    location: design set
    finding: "No Rust toolchain or rust-version is decided, although Clippy -D warnings results and File::try_lock availability depend on it."
    needed: "Add a decision or a constraint."
  - id: F-10
    severity: minor
    location: adr-004 decision 5; component §5
    evidence: "ADR-004 says 0.x journals are not read and the data folder may differ (U-10). Both binaries exist side by side (ADR-002)."
    finding: "The 'existing refusal code' for rollback is not named. An interrupted 0.5.2 apply is not detected. The two binaries' apply locks may not exclude each other."
    needed: "Name the code and state the behaviour."
  - id: F-11
    severity: minor
    location: BC-1; adr-003
    evidence: "U-13 says the command flags were not listed. U-9 covers end anchors and digit classes, but ADR-003 addresses only digit classes. U-8 and U-11 are not mentioned."
    finding: "Some carried-over unknowns are not addressed."
    needed: "Say where the option list for BC-1 comes from, and how U-8, U-9 and U-11 are handled."
  - id: F-12
    severity: minor
    location: BC-12; EC-1
    finding: "'The three existing manifests' has no AS-IS fact behind it. 'Manual or NOT_RUN' cannot be checked as written."
    needed: "Cite a fact for the three manifests, and say which status applies when."
observations:
  - "Six standards ids in standards_applied (ARCH-002, ARCH-003, SAFE-001, DET-001 to DET-003) are absent from the standards output given to me, so I did not check their text. The header applicable_rules_hash (15dad7d0…) matches neither printed hash, and how it is computed is unknown."
  - "The note files in the manifest's reviews entries do not exist yet."
  - "EC-5 marks the dependency surface manual, and extractor_config has no dependency_manifests or lockfiles entry."
  - "Two statements have no cited source: the rule that workflow files are served only when the manifest lists them (A-23) is not said to survive include_dir, and 'hook {} on failure' cites no fact."
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: design}
  checks:
    - {what: D3 artifacts and brief section order, how: read manifest, component, views and ADRs, result: pass}
    - {what: ADR sections and rejected alternatives, how: read all six, result: pass}
    - {what: web evidence supports the ADR claims, how: read five files, result: "pass, except F-4"}
    - {what: artifact sha256 values, how: shasum, result: not run (no hashes given, shell refused)}
    - {what: brief within 1,200 words, how: estimate, result: not run (about 1,100 by estimate)}
    - {what: orqlet validate design, result: not run}
  unverified: ["Cited source lines A-n were not opened", "Branch not confirmed"]
```

Questions from the reviewer: the round-1 hashes (listed above), and how this task is ordered against release 0.5.2.

## Architect's responses

- F-1: Domain now holds the canonical value type of `digest_of` and an own per-segment glob matcher; the unified diff moves to the application crate (`similar`); strict JSON moves to the adapters crate. ADR-001, ADR-003, EC-5 and section 4 agree.
- F-2: ProcessRunner refuses a `git` program; only GitRunner reaches the process layer through a crate-private call. BC-7 tests it.
- F-3: Integration tests start processes directly under a scoped `allow` with a reason; SEC-001 is rewritten to cover shipped code under `crates/*/src/`.
- F-4: An `xtask arch` check reads `cargo metadata` and enforces the allowed crate edges (normal and dev) and a per-crate allow-list of third-party crates; no_std is checked for the host target as the crate's own code, and dependency purity rests on the allow-list, which a reviewed change edits.
- F-5: Security globs add the documents (YAML, JSON, TOML) module, every `clippy.toml`, the workspace and crate manifests and `xtask/src/arch.rs`.
- F-6: Strict JSON rules stated in section 4 and BC-17.
- F-7: ADR-004 states that other tasks' header bindings go stale through the standards change and need an impact review when resumed; BC-4 compares both binaries on a checkout of the design's base revision.
- F-8: Constraint added: the standards change with `crates/**` and `xtask/**` scopes lands before or with the first crate code; old scopes stay until removal.
- F-9: `rust-toolchain.toml` pins 1.100.0 and the workspace sets `rust-version = "1.100"` (ADR-003).
- F-10: Rollback of a 0.x change is refused as a journal error, ORQ-E136, exit 3 (`src/orqlet/interface/cli/errors.py` lines 17-20). Open 0.5.2 changes are finished with 0.5.2 first; the two binaries are never run on the same project at once, and parity runs use separate copies.
- F-11: The option list comes from the captured 0.5.2 help output in the parity fixture; U-8, U-9 and U-11 are handled in ADR-003 and section 3.
- F-12: BC-12 names the three manifest paths and the status: NOT_RUN with a finding.
- Release 0.5.2: the person started this task explicitly (Q-1); ADR-006 updates AGENTS.md and the work status.
