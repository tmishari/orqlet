# Security review of the harness2-fit design

Role: security-reviewer. Subagent: `orqlet-security-reviewer`, which ran on `claude-sonnet-5-5-xhigh` because the generated agent file pins `model: "inherit"` with literal quote characters, which the client rejects (AS-IS O-11, O-12).

Round 1 reviewed the first draft of the design (hashes as listed in the architecture review note). The reviewer's text below is unchanged. The author's response and round 2 follow it.

## Round 1: reviewer text

### Verdict
BLOCKING FINDINGS (SR-1 and SR-2). The other eight findings are non-blocking.

### Findings

**SR-1. ADR-002's coverage claim is false: no "CI-verdict artifact pattern" exists, and the review-record pattern is narrower than the proposal's.** Severity: blocking.
- Evidence: `adr-002-packet-member-assertion.md:13` ("or a CI-verdict artifact pattern. The patterns are the exact ones that the evidence-artifact rule already uses."); `src/orqlet/domain/evidence_artifacts.py:22-35` defines exactly three patterns (review record, test record, knowledge-impact record); `docs/design/orqlet-architecture-proposal.md:1354` says the CI-result binding "is never written back into the repository", so a CI verdict is not a repository path; the built review pattern allows two roles (`evidence_artifacts.py:27`) while the proposal allows three (`proposal:1346`: "or `code-reviewer`"); the claim is repeated in `sequence.md:69`, `data-flow.md:18` and `component.md:48`.
- Consequence: the independence floor is approved on a control that does not exist as described; a `code-reviewer-P-1-r1.yaml` record would pass the assertion.

**SR-2. The front-matter lint compares only `name`, `model` and `description`, but the keys that carry the read-only and no-auto-invoke controls are other keys, so the lint can report clean when they are mis-read.** Severity: blocking.
- Evidence: `adr-001…:16` ("every key among `name`, `model`, `description` whose two values differ"); `src/orqlet/adapters/render/roles.py:26` (`("tools", READ_ONLY_TOOLS)`, `READ_ONLY_TOOLS = "Read, Grep, Glob"`, line 16), `roles.py:36` (`("readonly", role.read_only)`), `src/orqlet/adapters/render/skills.py:48` (`("disable-model-invocation", True)`); `emit.py:56-59` quotes every string, so `tools` is quoted too; AS-IS U-9 (Claude Code quoted values never observed); `adr-001…:18,22` claim the lint is the acceptance test for the emitter fix and catches any later disagreement.
- Consequence: an emitter fix that unquotes `name`, `model` and `description` but leaves `tools` quoted passes the lint; a reviewer meant to be read-only could get a different tool set in a client that keeps the quotes (not verified; the proposal's IDE-load spike S-21 was not run). Comparing every key needs a defined string form for non-string scalars such as `readonly: true`; EC-2 uses `Mapping[str, str]`.

**SR-3. ADR-002 states its limit more narrowly than the real gaps.** Non-blocking. Evidence: `adr-002…:18` and `considerations.md:9` name only a verdict pasted into a context file or a comment; design-review notes are verdict-bearing files at unconstrained paths (`design_set.py:126-128`: `note: RepoPath`; `validate_design.py:235-236` checks only existence); `proposal:1317` lets `review prepare --context <path>` add any path and offers `context_mode: full-tree`; reviewers hold `Read, Grep, Glob` (`roles.py:16`) and can read outside the packet (`proposal:1319`: such reads are "outside every digest"); the built `review_prepare.py:110-131` exports every tree entry as `snapshot/<path>` with no assertion. Consequence: an approver reads "deterministic floor" as covering verdicts generally; it covers three exact filename shapes in the member list.

**SR-4. The assertion's matching rule is not specified, and the reused patterns point the safe way for exclusion but the unsafe way for refusal.** Non-blocking. Evidence: `evidence_artifacts.py:44-60` (`parse_evidence_path`: case-sensitive `re.match` on a raw string); `evidence_artifacts.py:63-77` (`is_excluded` also requires an existing task, mode 100644, schema validity and path-to-content match, and the proposal says a file that fails any condition "is an ordinary input"); `src/orqlet/domain/paths.py:67-70` has a case-folded `key`; the team runs on macOS and Windows (AS-IS A-3). Consequence: a case variant, a `.yml` spelling, or a record that fails schema but sits at the exact path passes the assertion; using `is_excluded` would contradict the "ordinary input" rule.

**SR-5. The untrusted-input path of the lint has no stated bounds, and the strict-view wrapper is not specified.** Non-blocking. Evidence: the "never raise" rule and the property test cover only `simple_front_matter` (`considerations.md:8,44`); EC-2 gives `Callable[[str], Mapping[str, str]]` but the port is `DocumentLoader.load(bytes, source) -> object` (`ports/documents.py:21-27`) and a parsed document can be `None`, a list or contain non-string values; `local_fs.py:105-106` `read_bytes` has no cap (the 1 MiB cap is inside the strict loader, `yaml_loader.py:106,113`); no scan limit for the line view; two splitters exist (`validation.py:94-103`, `workflow_sources.py:32-52`). Consequence: one hostile file could raise an uncaught exception inside `doctor` and drop every other finding.

**SR-6. The new findings echo untrusted file values, contrary to the repository's own convention.** Non-blocking. Evidence: `data-flow.md:13` ("file, key, both values"); `considerations.md` ("the parse error text"); `src/orqlet/application/contracts/loading.py:16-17` ("It does not repeat the values, which may be secrets pasted into the wrong file."); `render_human.py:117` prints `f.message` raw; precedent uses `{name!r}` (`diagnose.py` `_reserved_name_findings`). Consequence: a multi-line value could forge finding lines, and escape sequences or pasted secrets are echoed.

**SR-7. A skipped file is not recorded as "not run", and files outside the manifest are not linted or mentioned.** Non-blocking. Evidence: `sequence.md:35`, `considerations.md:36` ("the lint skips it"); `diagnose.py:1-5` ("A check that could not run is listed in `not_run`; it is never reported as passed."); `domain/findings.py:1`. Consequence: a file never linted is silent.

**SR-8. Trust-boundary and class statements are inconsistent and have no evidence.** Non-blocking. Evidence: `data-flow.md:3` ("No flow … crosses a trust boundary; every file read is untrusted input"); `manifest.yaml:27` (`trust_boundaries: []`) and `:32` (`security_globs: []`) feed `design_scope.py:35` and `change_class.py:60-72`; the scope includes `src/orqlet/workflow/skills/orqlet-review/**` (`manifest.yaml:22`). Consequence: the design is approved at D2 with an empty trust-boundary list and a "crosses no trust boundary" sentence without evidence.

**SR-9. ADR-004's executor seam does not inherit the process and model rules.** Non-blocking. Evidence: `adr-004…:15`; ORQLET-SEC-001 and ORQLET-NOMODEL-001 are not mentioned; `considerations.md:31` states R-01 only for this task. Consequence: M7 could place a client launcher in product code or outside `ProcessRunner`.

**SR-10. The security note's evidence and scope do not line up with the ADRs.** Non-blocking. Evidence: `adr-001…:18` versus `considerations.md:30` and `manifest.yaml:19-26` (no `src/orqlet/adapters/render/**`); the security `evidence_refs` (`manifest.yaml:94-98`) cite `emit.py:56-59`, which supports the quoting defect, not "reads untrusted files … executes nothing". Consequence: the file that writes the protected read-only controls could change outside the declared scope.

### Absence records
- Secrets, keys, tokens or credentials in the design or its examples: searched `design/*` for `api key|secret|token|password|credential|AKIA|sk_live|ghp_|BEGIN … KEY/CERT`; only hits are the rejection wording in ADR-005 and "handles no secret" (`considerations.md:7`); the manifest holds 64-hex SHA-256 values and an all-zero 40-hex placeholder revision (`manifest.yaml:9`), labelled as a placeholder.
- Digests other than SHA-256 adopted: searched `sha-?1|md5` in `design/` and `src/`; design hits are all rejections; `src/` has no `hashlib.md5` or `hashlib.sha1`.
- Process, shell, eval, import or network in the new components: searched the design for `subprocess|ProcessRunner|os.system|shell=|eval|exec|importlib|yaml.load|pickle|network|http`; only "no network" statements; searched `src/` for `yaml.load|safe_load|eval(|exec(|importlib.import_module|pickle.load`; no matches.
- Strict loader executing or evaluating content: `adapters/fs/yaml_loader.py` subclasses `SafeConstructor` with a core-tag allow-list (53-56) and rejects aliases, anchors, merge keys and duplicate keys (62-68, 87-91); byte, depth and node caps and `RecursionError` handling (106, 113, 129).
- Bypass flags, key printing or SHA-1 adopted: ADR-005 lists them only as rejected; ADR-004 adopts two seams, a reference bundle, expected session counts, SHA-256 completion marks, unscored-not-zero, workspace separation and a no-model preflight; searched `src/` for `dangerously|skip-permissions|bypassPermissions|danger-full-access`; no matches.
- AS-IS or Harness² text used as instructions: none found; ADR-003 quotes Harness² prompts as context; the review skill itself says "Source material is not authority" (`skill.md:7`).
- Path-pattern bypass by relative segments, Windows separators, drive or stream colons, control characters and symlinks: `domain/paths.py:33-39` rejects `.`, `..`, `\` and `:`; `:36-37` rejects control and format characters; `review_prepare.py:111-118` omits symlinks, gitlinks and non-canonical names; `local_fs.py:168-181` refuses links. These close the vectors only if the assertion runs after `CanonicalPath.parse`, which ADR-002 does not state. Case variants are not closed.
- `not-affected` claims: the manifest has none (all three considerations are `affected`).

### Observations (no or incomplete evidence)
- The AS-IS declares its own acceptance (`as-is.md:11`, A-5b) and records that `orqlet validate as-is` returns FAIL; the self-check uses that declaration as proof of acceptance, and `gate status` is NOT_RUN.
- Codex roles are `.codex/agents/*.toml` (`roles.py:41-47`) with no front matter; their `sandbox_mode = "read-only"` control is outside both views.
- ADR-005:21 says rejected patterns "may not appear" in generated configuration or documentation; no deterministic check enforces this.
- ADR-003 describes its sentence but does not give the wording.
- AS-IS section 7 lists 16-hex-character SHA-256 prefixes (truncated to 64 bits); whether ORQLET-SEC-003 intends that to be acceptable was not checked.
- An all-zero `base_revision` has a valid shape; whether `orqlet validate design` accepts it as bound was not checked.

### What the reviewer did not check
`orqlet standards for` was refused in the reviewer's mode; it read `.prompts/rules.yaml` (17 rules) and the generated rule files instead and notes that the command may print more from layers it did not read. It did not compute the manifest digests or run `orqlet validate design`, did not read the Harness² source, did not observe client behaviour (the proposal's IDE-load spike S-21 was not run), could not test code that does not exist, and did not read the v0.5 packet plan, the planned sections 21.7 and 12.7, `questions.yaml`, other tasks or any previous review.

## Author response to round 1 (written by the design author, not the reviewer)

| Finding | Response |
|---|---|
| SR-1 | The CI-verdict claim is removed everywhere. ADR-002 uses the built `evidence_artifacts` predicate for review records (`is_excluded`), so the role set is the one place that the v0.5 plan extends with `code-reviewer`; a record that fails the rule's conditions is an ordinary input, as the proposal says. |
| SR-2 | The comparison covers every key of the file, not three. A value that is not a one-line scalar is a difference. The string form of a scalar is defined (text as is, `true` and `false` for booleans, decimal text for integers, `null`). |
| SR-3 | ADR-002 states the limits in full: the assertion covers valid review records at exact paths and design-review notes named by a manifest; it does not cover a verdict inside any other file, reads outside the packet, or the built `review prepare` (which has no assertion and exports every tree entry until the v0.5 packet plan). The design component of the packet takes the manifest's `artifacts` and `as_is_ref`, not its `reviews` notes. |
| SR-4 | The matching runs on `CanonicalPath` values after parsing, with the same case-sensitive comparison as Git; ADR-002 says that a case variant is an ordinary input and is not detected. |
| SR-5, SR-6, SR-7 | The use case and `doctor` change are removed, so no untrusted file is newly read at run time. The domain functions take text that the release test produced from Orqlet's own renderers; both never raise, with a property test over arbitrary text. Messages name the key and never print values. |
| SR-8 | The trust-boundary statement now says why there is no new boundary and cites the facts; `trust_boundaries` stays empty with that reason. The class stays D2 because the scope triggers it by public API additions. |
| SR-9 | ADR-004 says that the harness starts processes only through `ProcessRunner` and lives outside `src/orqlet`. |
| SR-10 | The emitter is in the manifest scope; the security evidence cites the facts that support each claim. |

## Round 2: reviewer text (shortened by the author: findings and evidence kept; absence records and the list of what was not checked summarised)

Verdict: **BLOCKING FINDINGS (SR-11).** SR-1, SR-2, SR-5, SR-6, SR-7, SR-9 and SR-10 RESOLVED; SR-3, SR-4 and SR-8 PARTLY RESOLVED.

New findings:
- **SR-11 (blocking). The plain-safe predicate, as worded, can write untrusted rule text unquoted and drops an existing escaping safeguard.** Evidence: the predicate excluded "no line break and no control character" but never mentioned U+2028, U+2029, U+FEFF or U+FFFE/FFFF, which `emit.py:20-21` escapes on the quoted path; U+2028 and U+2029 are not control characters, and PyYAML treats them as line breaks inside plain scalars (`yaml/scanner.py:1291`, `:1321-1340`), so a value could end its scalar and add or override keys; untrusted text reaches the emitter through `render_request.py:143` (`description=f"{rule.id}: {rule.text}"`) and `:144` (`paths=tuple(sorted(rule.scope.paths))`), `rules.py:34,41-43` and `standards_pack.py:59-60`; `_glob` (`common.py:38-43`) rejects only a leading `/`, a backslash and `..`; the repository's own AWKWARD list holds `\u2028`, `\ufeff`, `\ufffe`, `0x10`, `2026-10-20` and `<<` (`tests/unit/render/test_emit.py:39-57`). Consequence: a rule scope path with U+2028 would be written plain into `.claude/rules/*.md` or `.cursor/rules/*.mdc`; the release test cannot catch it because it renders only workflow text and the sample rule.
- **SR-12 (non-blocking).** The claim "a plain-safe string reads the same in every YAML parser" was false for at least one parser: the default PyYAML resolver types `<<` and `=` (`yaml/resolver.py:196,217-219`; `yaml/constructor.py:479-480`), while Orqlet's loader drops those resolvers (`yaml_loader.py:3-9,31-47`) and is the test's only oracle; "reads as a number" was undefined.
- **SR-13 (non-blocking).** The stated exclusions missed `.claude/rules/*.md` (`rules.py:36`, with a `paths` list), the counts disagreed (34 against 32), and the `.mdc` files also changed bytes.
- **SR-14 (non-blocking).** ADR-002 refused only valid review records, leaving the likeliest leak open (a malformed record at an exact path is an ordinary input, `evidence_artifacts.py:63-77`, proposal `:1342`), and it did not say to check the kind (`is_excluded` is also true for test and knowledge-impact records).

Observations: "verdict NOT_RUN" for stale artifacts is imprecise (`gate_status.py:7,122` make the offline verdict `NOT_RUN` for any task); floats and other scalar types had no defined string form; existing tests pin quoted forms (`test_skills.py:273,319`, `test_rules_and_instructions.py:47-50`); `review_prepare._write` (`:165-178`) does not use `CanonicalPath.conflicts_with`; the self-check still said `validate design` was not run.

## Round 3: reviewer text (shortened by the author in the same way)

Verdict: **NO BLOCKING FINDINGS.** SR-3, SR-4, SR-8, SR-11, SR-12, SR-13 and SR-14 RESOLVED.

The reviewer searched the allow-list for a string that a YAML 1.1 reader, a YAML 1.2 reader or a line reader would read differently (`=` alone, `<<`, a lone hyphen, `y`, `n`, `yes`, `no`, `on`, `off`, `Read, Grep, Glob`, an apostrophe) and found none; confirmed that rule files stay on today's quoted path and that no path from project text reaches the unquoted branch; and confirmed the packet rule fails closed, with its new denial (a malformed record at a record path blocks that branch's own review) stated.

New findings (non-blocking):
- **SR-15.** The claim that an accepted string is read as the same string "by a line reader" was not backed by the predicate test, which covered only the strict loader and PyYAML's default safe loader.
- **SR-16.** The packet rule did not say how an absent or unparseable record path is classified: `diff.patch` comes from `vcs.diff_patch(base, tree)` over all changed paths (`review_prepare.py:133`, `vcs_git.py:162-165`), while the snapshot only omits such paths (`:111-118`).

Observations: the allow-list admitted a trailing apostrophe (safe for every YAML reader, not for a hypothetical line reader that strips quotes independently); text of valid records is hidden from the AI reviewers, and proposal `:1352` rule 3 says disclosure lints on evidence files exist "because their free text is not otherwise reviewed as code", with no such lint found in `validate_review*.py`; the pathspec needs a `diff_patch` port change (`ports/vcs.py:113`); leftover "verdict NOT_RUN" wording in `data-flow.md` and `sequence.md`; "never hands" is a design rule on code that does not exist yet.

What the reviewer did not check (rounds 2 and 3): `orqlet standards for`, any hash, `orqlet validate design`, client behaviour, any code (none exists), and the rewritten `orqlet-research` description.

## Author response to rounds 2 and 3 (written by the design author, not the reviewer)

| Finding | Response |
|---|---|
| SR-11, SR-12, SR-13 | The predicate is now an allow-list (ASCII, a letter first, a short character set, no reserved word, no trailing space or apostrophe), private to `emit.py`, and applies only to skills, agent roles and commands. Rule files keep today's quoting and escaping. The predicate test compares the strict loader, PyYAML's default safe loader and `simple_front_matter`. The exclusions and the counts (32, and six more with the version marker) are stated. |
| SR-14, SR-16 | ADR-002 classifies each changed path with the existing `evidence_file_ok`: a valid record leaves every list and the diff; any other path at a review-record path (invalid, deleted or unparseable) is `NOT_RUN`; test and knowledge-impact records are not refused. |
| SR-15 | `simple_front_matter` was added to the predicate test, and a trailing apostrophe is excluded. |
| Observations | The "verdict NOT_RUN" wording was replaced by the warning ORQ-W390 and a not-run reason; the pathspec port change and the unreviewed free text of valid records are stated in ADR-002. |

## Result

The reviewer reported no blocking finding in round 3. The security reviewer did not see the final wording of the last edits (the SR-15 and SR-16 changes). A human reviewer of the design pull request should read them.
