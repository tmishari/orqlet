# Architecture review of the rust-migration design, round 3 (final round)

Reviewer: orqlet-arch-reviewer subagent (e0817ff4-387c-4b52-815a-7079e02f7500), fresh context, model named by the client as Claude Opus 5.5. Its first reply arrived as a summary only; on request it repeated the four parts below unchanged, without re-reviewing.
Earlier rounds: `architecture-reviewer-design-r1.md`, `architecture-reviewer-design-r2.md`.
Design file hashes of this round, given to the reviewer in its prompt:

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#6e0887a7993e9d11d408aa2ab1fffcf40eb385cbc684131c72a7a66fcc805c1c
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#592fbf1f6b766abf1e904f0283838e7e9b6a4fdb0fb1ae75d60cf9c198fa6b65
docs/design/rust-migration/design/adr-003-libraries.md#55561279b3f86d201c0b9357960602c3c6595370c2f3440ad20d7d361cd5983f
docs/design/rust-migration/design/adr-004-version-and-hashes.md#a2c1d847fcd19e7870bbdd80f682c7334a12395c8e4e8fb1bb1c360ce45eb88f
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#54835d937a3ef93f34ca9411d6b1d9da377cee3a9c918f4a639b98248c2e9c69
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#4c4d794dbd63d584948fe8981ddcb529523434984da9b691997cf4a79ec3c5f8
docs/design/rust-migration/design/adr-007-security-controls.md#327682ab933223057f6c17f6e6d604ebf6d13447e517bf4032e0830635b2e822
docs/design/rust-migration/design/component.md#ce30171e7d9b0ef21c24e0916dc996b7977262e11f4ce6d9dacf6977876eb585
docs/design/rust-migration/design/views.md#5f43dc02c6a723966a82f29797a0da28fb04005bf5a8e85e43cbc742fb598601
docs/design/rust-migration/design/manifest.yaml#056c270c7ea7892c63464858fe643262a5a43ce8cab176a40b11f6e47b02134a
```

## Reviewer output (unchanged)

Summary reply:

> I recommend changes before the person approves the design. There are no blocking findings, four major and five minor:
>
> - **YAML parse path:** the design says rules serde-saphyr lacks are checked after parsing. Once a document goes straight into a typed struct, that information is gone and the check cannot run.
> - **Parser ban:** only the documents module may call the parser entry points, but the xtask and the integration tests must parse JSON too. As written, they either fail Clippy or need allows the design forbids.
> - **Old journals:** 0.5.2 keeps its finished journals on disk. If 1.0.0 sees that folder, it refuses to upgrade any project 0.5.2 has ever changed, this repository included. If it doesn't see the folder, the guard does nothing.
> - **Standards timing:** after the standards rewrite, the generated IDE guidance still shows the Python rules until the 1.0.0 re-render. That re-render then makes this task's own approved records stale.
>
> Every round-2 finding is resolved except two security findings that are only partly resolved: the strict YAML rules and the old-journal guard. The hash comparison was not run because the shell was blocked. The nine hashes you gave match the values the manifest records, and the manifest's own hash could not be checked.
>
> **Question:** round 3 is the last review round allowed. Should the architect fix the four major findings for the person to approve directly, or does the person decide each one?

### Findings (orqlet.finding/v1)

```yaml
findings:
  - id: R3-F1
    severity: major
    location: adr-003 Consequences bullet 2; adr-007 decision 3; component §4 bullet 1; BC-4; BC-6
    evidence: >
      ADR-003: "serde-saphyr parses straight into typed structs". ADR-007 d3: "any rule that it does
      not provide at the pinned version is checked by the documents module after parsing".
      yaml_loader.py lines 5-7: the resolver fixes the type before the contract ("1.10 is a number,
      which a contract then rejects where a string is wanted"); lines 36-49 resolver; lines 58-70
      non-string keys, merge and duplicate keys refused on the generic tree. loading.py lines 11-21:
      generic tree first, then model_validate. common.py line 77 sets no strict mode, so Pydantic
      runs in its default (lax) coercion mode. serde-saphyr-options.md says nothing about how a typed
      target resolves plain scalars.
    finding: >
      When the target field picks the scalar's type, the key type, tag and resolver result are gone
      after parsing. The named fallback ("check after parsing") cannot run on that path. 0.5.2 has
      two steps: the narrow resolver, then lax coercion. The design does not decide which semantics
      1.0.0 has, so BC-6 ("resolves each scalar form") has no defined target, and BC-4 differences
      cannot be classed as intended or not.
    needed: >
      Decide the parse path in ADR-007 decision 3. Either every YAML document becomes a generic tree
      under the 0.5.2 resolver, key and tag rules and is then converted into the contract (say which
      coercions are kept), or typed parsing is used with the rules serde-saphyr provides and every
      resulting verdict change is listed as new behaviour. Make BC-6 name its target.
  - id: R3-F2
    severity: major
    location: adr-007 decision 6; adr-001 decisions 5-6; adr-005 decision 2; adr-002 decisions 2-4; BC-9; BC-10
    evidence: >
      ADR-007 d6: the parse entry points are "disallowed by Clippy in every crate. The one exception
      is the documents module." ADR-001 d6: xtask arch "reads cargo metadata" (JSON), and the xtask
      may depend only on application and domain, so it cannot reach the documents module in
      orqlet-adapters. ADR-005 d2 reads workflow/identity.json. ADR-002 d2-d4: the tests read
      fixtures and compare JSON envelopes. ADR-001 d5 scopes test and xtask allows to "file, process
      and environment APIs" only. QA-001 and ARCH-002 run clippy --workspace --all-targets -D
      warnings. clippy-disallowed-types.md items 1-2: one configuration file is found by lookup and
      walking up.
    finding: >
      As written, the xtask and the integration tests either fail Clippy or need allows the design
      forbids, so BC-9 and BC-10 cannot both hold. The design also does not say which clippy.toml
      holds the parse list. The application, adapters and cli crates each have their own file, and
      the evidence does not show Clippy merging files.
    needed: >
      Extend the scoped allow of ADR-001 d5 to the parse entry points for tests and the xtask, with
      a reason (or give the xtask a permitted reader). State that each crate's clippy.toml carries
      the full list.
  - id: R3-F3
    severity: major
    location: adr-007 decision 9; adr-004 decision 5; component §5 row "Interrupted or unreadable journal"; §9 constraints 4-5; BC-5
    evidence: >
      journal.py lines 63-68: finish rewrites the record with status complete, superseded or
      rolled-back, and the file stays. Lines 79-88: open_changes counts only status "open". Lines
      70-77: an unreadable record raises JournalError, which errors.py line 19 maps to ORQ-E136 and
      runner.py line 33 to exit 3. ADR-004 d5: "Journals and backups written by 0.x are not read."
      U-10: the folder each OS uses is unknown.
    finding: >
      If 1.0.0 sees the 0.x folder, every completed 0.5.2 journal is an entry it "cannot read". It
      then refuses to upgrade any project that 0.5.2 has ever changed, including this repository's
      re-render in §9, and "finish with 0.5.2" does not clear the refusal. If it does not see the
      folder (U-10), the guard does nothing. 0.5.2 reports an unreadable journal as ORQ-E136, not
      ORQ-E131, so BC-2 differs here without a listed difference.
    needed: >
      Define what 1.0.0 reads from a 0.x journal (for example only status, refusing on "open" or
      unparseable) and where it looks. Add a criterion with one completed and one open 0.x journal,
      and list the E131/E136 difference in the fixture.
  - id: R3-F4
    severity: major
    location: component §9 constraints 2 and 5; adr-006 decision 1 and Consequences; adr-004 Consequences bullet 2; manifest header.bound
    evidence: >
      standards_for.py lines 183-197: `standards for` reads .prompts/rules.yaml directly.
      gate_status.py lines 81-94 bind the hash of .orqlet/standards.lock.yaml and its stored
      applicable_rules_hash (standards.lock.yaml line 3, 15dad7…), which only a render changes. The
      generated rule files (for example .cursor/rules/orqlet-orqlet-arch-001.mdc and -det-003.mdc)
      and the AGENTS.md blocks carry the Python rule texts. ADR-004 discusses staleness of other
      tasks only. §9 re-renders "with 1.0.0 after the standards change".
    finding: >
      Between the standards change and the 1.0.0 re-render, the IDE guidance contradicts the new
      standards (Python layers; "no tests" against Q-11), while `standards for` already prints the
      new rules. At the re-render the lock hashes change, and this task's own approved design, plan
      and phase records still bind the old values, so gate status reports them stale at the end of
      the task. Neither effect is stated, and no reason is given for waiting for 1.0.0 instead of
      re-rendering right after the change.
    needed: >
      State when and with which binary the generated files and the standards lock are re-rendered,
      with the reason, and how this task's own approved artifacts are re-bound at that point (for
      example the impact review of the invalidation matrix).
  - id: R3-F5
    severity: minor
    location: adr-001 decision 4; adr-007 decision 1; BC-7; EC-6
    evidence: "'The process module of orqlet-adapters is crate-private and used only by GitRunner, so no code outside the Git module can start a process.' BC-7: 'the module is not reachable outside the Git module'."
    finding: >
      Crate-private visibility lets every adapters module (clients, render, fs, documents) call the
      process module, and Clippy disallows only std::process::Command. "Used only by GitRunner" rests
      on review, and the reachability half of BC-7 cannot be tested as written.
    needed: "Make the process module a private child of the Git module (or pub(in crate::git)), or reword BC-7 as a review check."
  - id: R3-F6
    severity: minor
    location: adr-001 decision 1; adr-006 decision 2; adr-007 decision 11; BC-11
    evidence: "ADR-007 d11 follows workspace members 'only when written as literal paths without glob characters'. ADR-001 d1 does not say how the root members list is written."
    finding: "With members = [\"crates/*\", …] the scanner follows no member, finds no binary, and BC-11 fails."
    needed: "Constrain this repository's root Cargo.toml to literal member paths, or say how a glob list is handled."
  - id: R3-F7
    severity: minor
    location: adr-007 decision 4; BC-17
    evidence: >
      strict_json.py lines 26-27 and 51-52: only the NaN and Infinity literals are refused, so 0.5.2
      reads a literal such as 1e400 as an infinite float and accepts it. That serde_json refuses a
      float literal outside f64 is reviewer knowledge, to be confirmed at the pinned version.
    finding: "A likely stricter rule for overflowing floats is neither listed as new behaviour nor tested."
    needed: "Confirm the behaviour, list it with the other new rules, and add the case to BC-17."
  - id: R3-F8
    severity: minor
    location: adr-006 decision 1, SAFE-001 row
    evidence: "'Outside the root Orqlet writes only its data directory (journal, backups, apply lock)'. wiring.py lines 158-162 (build_packet_store) also write review packets to the data directory's packets folder."
    finding: "The rewritten rule reads as an exhaustive list, and packet writes would break it."
    needed: "Name the packets, or drop the exhaustive list in parentheses."
  - id: R3-F9
    severity: minor
    location: manifest.yaml scope.paths and expected_changes
    evidence: "ADR-006 d1 changes the scopes of MODEL-001, DET-001 and DET-002 to include workflow/**, and EC-3 moves the data there. The removal (ADR-002 d5) deletes src/orqlet/ as a whole."
    finding: "Covered by scope, but no expected change records the removal of src/orqlet/, tools/, pyproject.toml and uv.lock as a surface. EC-5 mentions only the manifests."
    needed: "Add an expected change, or extend EC-5's identity, for the removed paths that BC-14 checks."
```

### Round-2 findings: are they resolved?

| Round-2 finding | Status | Note |
|---|---|---|
| Architecture F-1 (project kind) | Resolved | Remaining gap is in R3-F6 |
| F-2 (rule scopes) | Resolved | The SAFE-001 wording gap is in R3-F8 |
| F-3 (application guard) | Resolved | See the Cargo lints observation |
| F-4 (Git refusal) | Resolved | The visibility mechanism is in R3-F5 |
| F-5 (oversized integers) | Resolved | The float case is in R3-F7 |
| F-6 (kept hashes) | Resolved | I checked `instructions.py` 40-43, `emit.py` 33-36, `render_all.py` 419 and `gate_status.py` 89 |
| F-7 (allow-lists) | Resolved | — |
| F-8 (tests and checkout) | Resolved | The design's response created R3-F2 |
| F-9 (version comparison) | Resolved | A search shows no as-is, design, plan or ledger validator reads the release |
| F-10 (sources of limits) | Resolved | I checked the cited lines; the code difference is in R3-F3 |
| F-11 to F-17 | Resolved | All three manifests named in BC-12 hold `public_api` |
| Security D-1, D-3 to D-11 | Resolved | D-7's mechanism is in R3-F5; D-8's response created R3-F2 |
| Security D-2 (strict YAML rules) | Partly | Rules listed, but the fallback does not work on the typed path (R3-F1) |
| Security D-12 (old journals) | Partly | The guard is defined, but it blocks upgrade or does nothing (R3-F3) |

### Observations

- **Citations:** without Git I read the working tree, not commit 3e3c311. Every cited line range I opened matches its claim:
  - `git_runner.py` 18-116 and 34-36; `environment.py` 7-32; `yaml_loader.py` 1-7, 27-70, 36-49 and 87-131; `strict_json.py` 14-52
  - `local_fs.py` 1-10, 33-61, 110-149 and 186-215; `journal.py` 37-38; `paths.py` 17-48; `upgrade.py` 80-88; `hook.py` 38-48
  - `wiring.py` 52, 83-86, 108, 170 and 207; `validate_model_policy.py` 405-415 and 605-627; `technology_scanners.py` 190-225; `dependencies.py` 51-80
- **Two base revisions:** the manifest binds 3e3c311, while the approved AS-IS file binds 3196914 and cites that revision. I could not check that the files are unchanged between the two.
- **Exit 3 citation:** ADR-004 decision 5 cites `errors.py` 17-20 for exit 3. Those lines map only the codes; the status comes from `runner.py` line 33.
- **Rules hash settled:** `applicable_rules_hash` 15dad7… equals the value on line 3 of `.orqlet/standards.lock.yaml`.
- **Cargo lints (my knowledge, not in the evidence):** Cargo may refuse a crate's own `[lints.clippy]` next to `lints.workspace = true` (ADR-001 decisions 3 and 7). The plan should confirm this.
- **serde_json `arbitrary_precision`:** Cargo merges features across the workspace build, so turning this on for the documents module would also change `serde_json::Value` numbers in the application and CLI crates.
- **Hook panics:** `catch_unwind` needs `panic = "unwind"` in the release profile, and the design does not pin it.
- **User-scope readers:** `status.py` 224-243 and `hook_event.py` 242-251 still read the user manifest and the home folder. They are wired, so they are ported, but with the writer gone they always report missing. The design does not say this.
- **controls_level:** `upgrade.py` 360-364 refuses a weaker `controls_level`. Nothing says the 1.0.0 `identity.json` keeps it.
- **Diagram edges:** the component diagram leaves out the adapters-to-domain and xtask-to-domain edges that ADR-001 decision 6 allows.
- **Not run:** I did not count the brief's words or run `orqlet validate design`.

### Self-check

```yaml
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: design}
  model: "Claude Opus 5.5 (as named by the client); fresh context, only the given paths and cited sources"
  revision: "branch rust-migration-design, HEAD not read (no shell); working tree read"
  checks:
    - {what: file hashes, how: shasum, result: "not run (shell refused); 9 given values equal the manifest's recorded values"}
    - {what: D3 artifacts, ADR sections, brief order, how: read all ten files, result: pass}
    - {what: round-2 findings, how: compared each response with the current text, result: "all resolved except security D-2 and D-12, which are partly resolved (R3-F1, R3-F3)"}
    - {what: Q-1 to Q-15 respected, how: compared ledger answers with ADRs, result: pass}
    - {what: cited source lines, how: read the cited ranges in the working tree, result: "pass; one citation incomplete (observation)"}
    - {what: web evidence supports ADR claims, how: read five files, result: "pass; typed scalar resolution not covered (R3-F1)"}
    - {what: brief word limit and orqlet validate design, result: not run}
  unverified:
    - "Line numbers at 3e3c311 itself; the working tree was read"
    - "Library behaviour named from my own knowledge (serde_json floats, Cargo lints, Pydantic lax mode) is to be confirmed"
    - "This review is an additional check, not a guarantee"
```

## Architect's responses

Round 3 is the last round. The design files above are unchanged since the reviewer read them, so this note's hashes match the manifest. Below is the resolution I propose for each finding. I have not applied any of them, because a change now would need a fourth review round, which only the person can allow.

- R3-F1 (open, major): every YAML document is parsed into Orqlet's own generic tree, following the parser's events with the 0.5.2 resolver, key and tag rules. The tree is then converted into the contract by serde, with no type coercion. Each verdict that this changes compared with Pydantic's lax mode is listed in the fixture. BC-6 names this tree as its target.
- R3-F2 (open, major): the scoped allow of ADR-001 decision 5 also covers the parse entry points for tests and the xtask, each with a reason. Each crate's `clippy.toml` carries the full list.
- R3-F3 (open, major): 1.0.0 reads only the `status` field of each 0.x journal file in its own data directory, through the documents module. It refuses with ORQ-E131 on `open` and with ORQ-E136 on a file it cannot parse, as 0.5.2 does. Completed journals are ignored. A new criterion uses one completed and one open 0.x journal. U-10 stays: a 0.x folder in another location is not seen, and the rule against running both binaries on one project covers that case.
- R3-F4 (open, major): right after the standards rewrite, the generated files and the standards lock are re-rendered with the 0.5.2 binary, so the IDE guidance matches the rules from then on. They are rendered again with 1.0.0 before removal. This task's own approved artifacts are re-bound at each re-render through the impact review of the invalidation matrix.
- R3-F5: the process module becomes a private child of the Git module, so BC-7 can be tested.
- R3-F6: the root `Cargo.toml` lists its members as literal paths.
- R3-F7: a float literal outside the f64 range is refused. This is marked as new behaviour, to be confirmed at the pinned version, and BC-17 gets the case.
- R3-F8: SAFE-001 names review packets beside the journal, backups and apply lock.
- R3-F9: EC-5's identity is extended to the removed paths that BC-14 checks.
- Observations: the exit-status citation becomes `runner.py` line 33. `identity.json` keeps `controls_level`. The user-scope readers are ported and report missing data while the writer is gone. Both diagram edges are added. Whether Cargo allows crate-level lints next to workspace lints is confirmed by the plan.

After this note the person chose, on 2026-11-25, to apply the resolutions above and allowed one extra review round (round 4). The person also decided that a data directory inside the project is refused (ledger Q-16).
