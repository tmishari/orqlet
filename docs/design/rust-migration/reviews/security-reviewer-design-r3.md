# Security review of the rust-migration design, round 3 (final round)

Reviewer: orqlet-security-reviewer subagent (f97cd1ae-7773-4314-8672-1bea3b0b62e0), fresh context, model named by the client as Claude Opus 5.5.
Earlier round: `security-reviewer-design-r2.md`.
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

The design needs changes before approval. I found no blocking finding, but two major and eight minor ones. Of the twelve round-2 findings, seven are fully resolved and five only partly. ADR-007 carries over most of the 0.5.2 security rules, but two load-bearing ones are missing:

- **Git argument checks.** The checks that keep revisions, ref names and paths taken from repository files out of Git's option positions are not in ADR-007 or in any acceptance criterion.
- **Error messages.** The 0.5.2 rule that validation errors never repeat input values or unknown keys is not carried over, so possible secrets could appear in messages.

**Hash check: not run.** The shell is unavailable in this session. What I could check: the ten values you gave match the `sha256` values in `manifest.yaml` for D-1 to D-5 and ADR-001 to ADR-007. Nothing records a hash for the manifest itself, so `056c270c…` was not checked. Neither check proves the file bytes match.

### Findings (orqlet.finding/v1)

```yaml
- id: SEC-D3-1
  severity: major
  location: adr-007 decision 2; BC-18; EC-6
  evidence: >
    src/orqlet/adapters/git/objects.py lines 11-17 accept only HEAD or a full object id as a revision.
    Lines 26-28 refuse a path that holds a line feed or NUL before the cat-file --batch request.
    src/orqlet/application/ports/vcs.py lines 28-38 (check_ref_name: no leading dash, no '..', '~',
    '^', ':' or '{') and lines 41-56 (check_exclusions). vcs_git.py lines 113, 132, 162-164,
    169-171 and 203-219 call these checks on every value that comes from an artifact, and put
    pathspecs after '--'. ADR-007 decision 2 cites only git_runner.py lines 18-116.
  finding: >
    The per-call checks are what keep repository-supplied revisions, ref names and paths out of
    Git's option positions. Without them, a recorded revision such as '--output=<file>' would reach
    'diff-tree' as an option, and the GitRunner deny-list does not cover that option. No acceptance
    criterion covers these checks. A port that follows decision 2 literally would drop them.
  needed: >
    Add the checks of objects.py lines 11-28 and vcs.py lines 28-56, plus the rule "pathspecs only
    after --", to ADR-007 decision 2 and EC-6. Extend BC-18: a revision, ref or exclusion beginning
    with '-', holding '..' or a revision expression, or a path holding a line feed is refused before
    any process starts.

- id: SEC-D3-2
  severity: major
  location: adr-003 Consequences line 39 ("messages are Orqlet's own or serde-saphyr's"); adr-007 (absent); EC-6
  evidence: >
    A-12 ("without the input value"). contracts/loading.py lines 1 and 16-17: errors "never echo the
    input ... which may be secrets pasted into the wrong file"; line 25 uses include_input=False.
    contracts/integrations.py line 28 and contracts/resources.py lines 49, 66, 94 and 145 set
    hide_input_in_errors. integrations_source.py line 127 and resources_source.py line 73: "without
    the input or a stranger's key". vcs.py line 47 and mcp_credentials.py line 129: never repeat
    the matched text.
  finding: >
    The 0.5.2 rule that findings never contain input values or unknown keys is a data-exposure
    control, and the design does not carry it over. Q-6 allows the wording to change. It does not
    allow values to be disclosed. serde's messages usually quote the offending value and the unknown
    field name (to confirm at the pinned serde and serde-saphyr versions). Those messages would
    reach findings, --json envelopes and agent context.
  needed: >
    Add a rule to ADR-007: the documents module and the contract loader turn library errors into
    "location: rule" messages without values or unknown key names, and credential scanners report
    only the rule and line. Add an acceptance criterion: a contract with a secret-shaped value in a
    wrongly typed field, and an unknown key, produces a message containing neither.

- id: SEC-D3-3
  severity: minor
  location: adr-007 decision 3; BC-6
  evidence: >
    yaml_loader.py lines 129-131: the PyYAML reader refuses a control character in the stream.
    Decision 3 cites lines 87-131 but does not list this rule.
  finding: >
    Raw C0 and C1 control characters and DEL could pass into values and on to terminal text or
    rendered files. Whether serde-saphyr refuses them is unknown.
  needed: >
    List "only YAML-printable characters in the stream" in decision 3 and add a BC-6 case. The plan
    confirms serde-saphyr's behaviour or adds a pre-scan.

- id: SEC-D3-4
  severity: minor
  location: adr-007 decision 3 ("checked by the documents module after parsing")
  evidence: >
    The rules about string-only keys and the scalar resolver (lines 36-49, 59-63) depend on the
    original scalar text and style. Generic documents parse into serde_json::Value (adr-003 line 40).
  finding: >
    After parsing, a Value or a typed struct no longer shows whether a key was the number 1, or
    whether 16 was written as 0x10. For these rules a check after parsing cannot work. Unlike
    decisions 4 and 8, decision 3 has no "stop and ask" fallback.
  needed: >
    Say that any missing rule is checked at the event or raw-scalar level (a custom visitor or the
    parser's event stream). If neither works, the plan stops and asks.

- id: SEC-D3-5
  severity: minor
  location: adr-007 decision 6; adr-001 decision 5
  evidence: >
    Decision 6 lists from_str, from_slice, from_reader and their _with_options forms. ADR-001
    decision 5 scopes the allows for tests and the xtask to file, process and environment APIs only.
  finding: >
    The list misses other entry points, for example str::parse::<toml::Table>() or
    str::parse::<serde_json::Value>() through FromStr, and the serde_json Deserializer constructors
    (to confirm at the pinned versions). The xtask and the integration tests must parse JSON but get
    no allow, which contradicts "every crate".
  needed: >
    Name the remaining entry points, or say the Clippy list is a partial net and the SEC-002 review
    covers the rest (as ADR-001 already says for std). Give the xtask and the tests a scoped allow
    for parsing.

- id: SEC-D3-6
  severity: minor
  location: adr-007 decision 7 (data-directory modes, citing journal.py lines 37-38); adr-006 SAFE-001
  evidence: >
    journal.py lines 37-38: _private_fs is used only by for_user (user scope, not ported). Project
    journals and backups go through LocalFileSystem(data_path) without private (wiring.py lines
    202-203, 220-221). Review packets go through LocalFileSystem(data_dir/packets) (lines 158-162).
    The data directory root is created by plain mkdir (line 92). local_fs.py lines 207-213 tighten
    only folders they create.
  finding: >
    Modes 0600 and 0700 are new behaviour for project data, not a carry-over, so the citation is
    wrong. Folders that 0.5.2 already created keep their old modes. Review packets hold staged
    snapshots that may contain secrets, yet the SAFE-001 list (journal, backups, apply lock) leaves
    them out.
  needed: >
    Mark the modes as new behaviour with the correct sources. State whether 1.0.0 tightens existing
    data-directory folders. Name packets in SAFE-001 and BC-19.

- id: SEC-D3-7
  severity: minor
  location: adr-007 decision 9; adr-004 decision 5; failure table row "Interrupted or unreadable journal"
  evidence: >
    "0.x journals are not read" and "refuses to upgrade while its data directory holds a journal
    entry it cannot read". upgrade.py lines 80-88 refuse only open changes. journal.py lines 79-88
    read every *.json file.
  finding: >
    Read literally, every completed 0.x journal is unreadable, so any project that 0.5.2 ever
    upgraded is blocked for good. Read loosely, nothing is detected. The listed recovery,
    'upgrade --resume', cannot resume an entry it cannot read.
  needed: >
    Define the check: read only the status of each journal file through the documents module, and
    refuse when it is open or cannot be parsed. Completed 0.x journals do not block. Name the
    recovery for a corrupt journal.

- id: SEC-D3-8
  severity: minor
  location: adr-007 decision 10; failure table row "Error or panic in the hook"
  evidence: "Decision 10 relies on catch_unwind; no Cargo profile setting is stated."
  finding: >
    catch_unwind does nothing under panic = "abort". The default panic hook also writes to stderr.
    The "{} and exit 0" rule rests on a build setting that nobody pins.
  needed: >
    State that the release profile keeps panic = "unwind" (Cargo's default), that the hook installs
    a quiet panic hook, and add a hook case for a panic.

- id: SEC-D3-9
  severity: minor
  location: adr-007 decisions 5 and 11 ("at most 1 MiB"); decisions 3 and 4 ("checked before decoding")
  evidence: >
    scan/common.py lines 39-40 and validate_model_policy.py lines 608-610 read the whole file and
    only then compare its size.
  finding: >
    The design does not say whether a limit bounds the read itself. A very large regular file is
    fully loaded into memory before it is refused, as in 0.5.2.
  needed: >
    Say that each size limit is enforced by a bounded read of limit + 1 bytes through the
    FileSystem port.

- id: SEC-D3-10
  severity: minor
  location: manifest.yaml extractor_config.security_globs; scope.paths
  evidence: >
    The globs cover the adapters source, hook.rs, paths.rs, clippy.toml, the Cargo files and
    xtask/src/arch.rs. The Git argument checks live in application ports (vcs.py). The error mapping
    and credential scanners live in application and domain. build.rs and .cargo/config.toml are
    not listed.
  finding: >
    Changes to the argument checks, the error mapping, a build script (code that runs at build time)
    or Cargo source replacement are not sent to security review.
  needed: >
    Add the application ports module for Git, the contract-loading and credential-scanning modules,
    "**/build.rs" and ".cargo/**". Add ".cargo/**" to scope if it may change.
```

### Round-2 findings: are they resolved?

| Round-2 finding | Status | Where the rest went |
|---|---|---|
| SEC-D-1 GitRunner rule set | Resolved. Decision 2 matches `git_runner.py` lines 18-116 line by line; BC-18 added | The per-call argument checks are missing: SEC-D3-1 |
| SEC-D-2 strict YAML rules | Resolved. Keys, resolver and UTF-8 listed; booleans marked as new | Control-character rule and fallback mechanism: SEC-D3-3, SEC-D3-4 |
| SEC-D-3 confinement | Resolved (decision 7, BC-19; `libc` used for constants only, unsafe code still forbidden) | — |
| SEC-D-4 Unicode categories | Resolved. A no_std category crate is on the domain allow-list; the plan confirms it or stops and asks; BC-20 | — |
| SEC-D-5 Cargo.toml scanner | Resolved (decision 11, BC-20) | — |
| SEC-D-6 TOML inputs | Resolved (decision 5; 256 KiB matches `validate_model_policy.py` line 610) | — |
| SEC-D-7 public ProcessRunner | Resolved. Process creation is now private to the Git module | — |
| SEC-D-8 parser entry points | Partly | SEC-D3-5 |
| SEC-D-9 hook | Resolved in substance | The panic setting is not pinned: SEC-D3-8 |
| SEC-D-10 lockfile globs | Resolved. `Cargo.lock` and `rust-toolchain.toml` added; only direct dependencies checked, as stated | Further globs: SEC-D3-10 |
| SEC-D-11 private modes and journal paths | Partly. Journal paths are parsed again; the mode citation is wrong | SEC-D3-6 |
| SEC-D-12 0.5.2 journals left open | Partly. The refusal was added but is ambiguous | SEC-D3-7 |

### Observations (not blocking)

- **Abbreviated Git options.** Git may accept a unique prefix of a long option (for example `--ext-d` for `--ext-diff`, or `--textc`). This is from memory, not from the repository. The forbidden-option lists match whole names only, so they are safe only while no untrusted value reaches an option position, which is what SEC-D3-1 protects. The plan could refuse any option missing from a per-subcommand allow-list.
- **Data directory on Windows.** The folder chosen by platformdirs and by `dirs` may differ on Windows (from memory, to confirm). If so, the ORQ-E131 check and the apply-lock exclusion would not see 0.5.2's folder, and only the "never run both binaries" rule would protect the project.
- **Windows names and links (0.5.2 behaviour, carried over).** `paths.py` does not refuse the 8.3 short name `git~1` or superscript device names such as `COM¹` (from memory). Separately, Windows has no equivalent of `O_NOFOLLOW` in 0.5.2. Opening with `FILE_FLAG_OPEN_REPARSE_POINT` through `custom_flags` would be optional hardening.
- **Temporary files.** `create_new` needs a unique name and a retry when the name exists, and no randomness crate is on the allow-list. Private files should get mode 0600 when they are created, not by a later chmod.
- **Apply lock and `ORQLET_DATA_DIR`.** The design does not say whether the apply lock opens its file through the confined file system. If `ORQLET_DATA_DIR` points inside the repository, plain `std::fs` follows links. The architect has already raised this case with you.
- **Version strings in the profile.** Version strings of known crates (and of other scanners) still go into the profile without a pattern check, as in 0.5.2. Your approval of the profile limits the risk.
- **Integer parsing.** PyYAML's integer constructor reads a leading `0` as octal (from memory), so "decimal only" may not describe 0.5.2 exactly. This is a parity question that BC-4 and BC-6 will show, not a security one.
- **Review notes.** The manifest's `reviews` entries name notes that do not exist yet (`security-reviewer-design.md`, `architecture-reviewer-design.md`).
- **Changes that help security:** making process creation private removes name matching; `libc` is used for constants only while unsafe code stays forbidden; integers outside 64 bits are refused; Cargo.lock is now under security review; Git tests are isolated from your own Git configuration.
- I found no secrets, MD5 or SHA-1, and no language-model SDK in the files I read.

### Self-check

```yaml
schema: orqlet.self-check/v1
checked_against:
  role: security-reviewer
  phase: design
  model: "Claude Opus 5.5 (as named by the client); fresh context, no Coder or Architect conversation"
  revision: "working tree of /Users/tmishari/Documents/orqlet; branch and HEAD not confirmed (no shell); source line numbers checked against the working tree, assumed equal to 3e3c311"
checks:
  - {what: file hashes of this round, how: shasum, result: "NOT_RUN (shell refused in this session)"}
  - {what: given hashes vs manifest artifact hashes, how: read manifest.yaml lines 105-117, result: "equal for all ten values; the manifest's own hash is not recorded and was not checked"}
  - {what: design set, AS-IS, ledger, five evidence files, design format, standards output, rules.yaml, round-2 reviews, how: read in full, result: done}
  - {what: ADR-007 citations, how: "read git_runner.py, environment.py, yaml_loader.py, strict_json.py, local_fs.py, paths.py, hook.py, journal.py, upgrade.py 60-109, technology_scanners.py 170-239, dependencies.py, validate_model_policy.py 595-634, wiring.py 40-239", result: "accurate, except journal.py 37-38 (SEC-D3-6)"}
  - {what: "controls not cited by the design", how: "read objects.py, ports/vcs.py, vcs_git.py 1-45 and 195-224, loading.py; searched for hide_input and no-echo rules", result: "found SEC-D3-1 and SEC-D3-2"}
unverified:
  - "Library behaviour marked 'to confirm' or 'from memory' (serde error text, FromStr parse paths, Git option abbreviation, platformdirs and dirs on Windows, PyYAML octal integers, Windows 8.3 names) was not looked up, by rule."
  - "I did not read .venv, the remaining scanners or every caller of the Vcs port."
  - "This review is an additional check, not a guarantee."
```

## Architect's responses

Round 3 is the last round. The design files above are unchanged since the reviewer read them, so this note's hashes match the manifest. Below is the resolution I propose for each finding. I have not applied any of them, because a change now would need a fourth review round, which only the person can allow.

- SEC-D3-1 (open, major): ADR-007 decision 2 would add the per-call checks of `objects.py` lines 11-28 and `ports/vcs.py` lines 28-56, and the rule that pathspecs come only after `--`. BC-18 would get the hostile revision, ref, exclusion and path cases. The Git port module would join the security globs.
- SEC-D3-2 (open, major): a new ADR-007 decision would carry over the rule that messages never echo input. The documents module and the contract loader would turn library errors into "location: rule" messages without values or unknown key names, and credential scanners would report only the rule and the line. A new criterion would use a secret-shaped value in a wrongly typed field and an unknown key.
- SEC-D3-3: only YAML-printable characters would be allowed in the stream, with a BC-6 case. The plan would confirm serde-saphyr's behaviour or add a pre-scan.
- SEC-D3-4: resolved by the generic-tree parse path proposed for architecture finding R3-F1, at the event level. The plan would stop and ask if that path does not work.
- SEC-D3-5: the Clippy list would name the `FromStr` paths and the Deserializer constructors, and would be stated to be a partial net, with the SEC-002 review covering the rest. Tests and the xtask would get a scoped allow for parsing.
- SEC-D3-6: the 0600 and 0700 modes would be marked as new behaviour for project data, with the corrected sources. 1.0.0 would tighten only the folders it creates. Packets would be named in SAFE-001 and BC-19.
- SEC-D3-7: resolved together with R3-F3. Only the journal status would be read; an open journal is refused with ORQ-E131 and an unparseable one with ORQ-E136. The recovery for a corrupt journal would be to inspect and remove it by hand, as the message says.
- SEC-D3-8: the release profile would pin `panic = "unwind"`, the hook would install a quiet panic hook, and a hook panic case would be added.
- SEC-D3-9: each size limit would be enforced by a bounded read of the limit plus one byte through the FileSystem port.
- SEC-D3-10: the globs would add the Git port module, the contract-loading and credential-scanning modules, `**/build.rs` and `.cargo/**`, and `.cargo/**` would join the scope.
- `ORQLET_DATA_DIR` inside the repository: 0.5.2 does not refuse it, and the design keeps that behaviour. Whether to refuse it is a change the person may want to order.

After this note the person chose, on 2026-11-25, to apply the resolutions above and allowed one extra review round (round 4). The person also decided that a data directory inside the project is refused (ledger Q-16).
