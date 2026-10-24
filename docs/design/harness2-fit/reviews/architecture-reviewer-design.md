# Architecture review of the harness2-fit design

Role: architecture-reviewer. Subagent: `orqlet-arch-reviewer`, which ran on `claude-sonnet-5-5-xhigh` because the generated agent file pins `model: "inherit"` with literal quote characters, which the client rejects (AS-IS O-11, O-12).

Round 1 reviewed the first draft of the design (manifest hashes before this note was saved: container `70b5baf8…`, component `88054d0f…`, data-flow `b9bb8071…`, sequence `782de387…`, ADR-001 `9458332d…`, ADR-002 `3111d7e5…`, ADR-003 `36db7021…`, ADR-004 `2d2cbbfc…`, ADR-005 `a5a708b8…`, considerations `ed175c9d…`). The reviewer's text below is unchanged. The author's response and round 2 follow it.

## Round 1: reviewer text

### Verdict
BLOCKING FINDINGS (4 blocking, 12 non-blocking).

### Findings

Paths below are relative to `docs/design/harness2-fit/design/` unless they start with `src/`, `tests/`, `tools/`, `.prompts/`, `pyproject.toml` or `docs/design/`. `as-is.md` means `docs/design/harness2-fit/as-is.md`.

#### Blocking

**AR-1. The design contradicts itself on whether the emitter fix ships with the check. As scoped, the new release test fails and `doctor` exits 5 on every install.**
- Evidence: `adr-001-client-visible-front-matter.md:18`: "the fix and the check land in the same change. Shipped alone, the check fails on today's generated files". `considerations.md:30`: "Out of scope: … the emitter fix itself (the v0.5 rework)". `manifest.yaml:18-26`: `scope.paths` has no `src/orqlet/adapters/render/**`. `considerations.md:16`: "On projects installed with today's quoted files, the check will report findings until `orqlet upgrade` applies the emitter fix". `src/orqlet/adapters/render/emit.py:56-59`: `front_matter` calls `yaml_document(dict(fields), quote_all=True)`. `adr-001-client-visible-front-matter.md:15`: the line view keeps "quote characters as characters", so every rendered file differs. `component.md:47` and `sequence.md:53-55`: the new `tests/unit/render` test asserts the views agree for every rendered file. `src/orqlet/interface/cli/exit_codes.py:12`: `CHECK_FAILED = 5`. `src/orqlet/interface/cli/commands/lifecycle.py:224` takes the exit code from the findings.
- Consequence: if built as scoped the suite is red (ORQLET-QA-001, ORQLET-TEST-001) and `orqlet doctor` exits 5 on every existing install. If ADR-001 item 4 is followed, this task depends on the v0.5 rework and the scope, `expected_changes` and phase order are wrong. The approver cannot tell which reading is intended.

**AR-2. The EC-2 signature does not match the shape drawn in `component.md` and `sequence.md`, and it has no failure channel.**
- Evidence: `manifest.yaml:44` gives a batch over a mapping of text with an injected `Callable[[str], Mapping[str, str]]`. `sequence.md:21` has `lint(path, text)` per file; `sequence.md:22` has the use case calling the strict loader itself. `component.md:31,45,51` name the DocumentLoader port. `src/orqlet/application/ports/documents.py:21-27`: `DocumentLoader.load(data: bytes, *, source: str) -> object`. Nothing says who encodes to bytes, extracts the front-matter block, coerces `object` to `Mapping[str, str]` or carries a `DocumentError`. `adr-001…:16` and `considerations.md:37-38` require "does not parse" and "missing block" findings, which EC-1's `dict[str, str]` return cannot distinguish.
- Consequence: EC-2 has `verification: extractor`, so it is checked literally; plan phases written from the diagrams will build a different seam.

**AR-3. The design disagrees with itself on which protected workflow files change, and the manifest scope omits the files that ORQLET-DET-002 forces to change.**
- Evidence: `adr-003…:13` says one sentence in the skill and "No reviewer role text changes". `container.md:35`, `component.md:49` and `data-flow.md:23` say the roles and the skill gain two sentences. `manifest.yaml:18-26` lists only `src/orqlet/workflow/skills/orqlet-review/**`; it omits `roles/**`, `MANIFEST.json`, `identity.json` and `tests/golden/**`. `tools/build_manifest.py:1-9` rebuilds `MANIFEST.json`. `adr-003…:15` says the sentence goes into the next workflow release. `.prompts/rules.yaml` ORQLET-DET-002 requires a rebuild and a version bump for any workflow package change.
- Consequence: an implementer cannot tell whether roles change; editing the skill inside this task's file list fails the DET-002 check unless out-of-scope files also change.

**AR-4. The check is specified for "every rendered skill and role for the three clients", but Codex roles are TOML files with no front matter. The design never says how they are handled.**
- Evidence: `adr-001…:17`, `sequence.md:50`, `considerations.md:38`. `src/orqlet/adapters/render/roles.py:41-46`: `codex_role` writes `.codex/agents/<name>.toml` through `toml_table`. `src/orqlet/application/usecases/diagnose.py:31-39`: `_MANAGED_DIRECTORIES` includes `.codex/agents`. `roles.py:20-38`: Claude roles carry `tools`, Cursor roles carry `readonly` as a YAML boolean, Codex roles have no `model`; EC-2 types the strict view as `Mapping[str, str]`.
- Consequence: applied literally, every Codex role produces a "missing front-matter" finding in the release test and in `doctor`; otherwise the implementer narrows the scope silently.

#### Non-blocking

**AR-5. ADR-002 says the CI-verdict pattern is one "the evidence-artifact rule already uses". No such pattern exists.** Evidence: `adr-002…:13`; `data-flow.md:18`; `src/orqlet/domain/evidence_artifacts.py:21-35` (three patterns: review, test, knowledge-impact); `src/orqlet/domain/binding.py:32-35`; proposal line 1342 "exactly one of the three patterns". Consequence: the v0.5 plan inherits a pattern that does not exist.

**AR-6. Two existing front-matter readers are neither cited nor reconciled with the new third one.** Evidence: `src/orqlet/application/usecases/validation.py:94-104` (`split_front_matter`, BOM and CRLF); `src/orqlet/application/usecases/workflow_sources.py:29-53` (`parse_source`); `pyproject.toml:86-93` forbids the domain from importing the application's splitter. Consequence: block extraction is duplicated; two splitters can disagree on BOM or CRLF.

**AR-7. The `doctor` half of ADR-001 is not shown to solve a problem that the release test and existing findings do not.** Evidence: `component.md:46`, `sequence.md:18` (doctor lints generated protected files); `diagnose.py:150-165` already reports drift (ORQ-E150); lines 240-247 already report "An upgrade is available" (ORQ-W162); `adr-001…:24` defers extension skills; "release test only" is not listed as an alternative. Consequence: a use case, a `diagnose` change, new codes, a severity decision pushed to the plan and a CLI exit-code change for no gain beyond the release test.

**AR-8. The release test duplicates the comparison instead of calling the use case.** Evidence: `component.md:37-38` (no edge `rt --> lint`); `sequence.md:53-55`; the name-versus-folder check is absent from S-2. Consequence: comparison logic exists twice, and the test can pass while the use case is broken.

**AR-9. Guesses or overstated state are presented as fact.** (a) `adr-001…:8` says "Clients and tools in this ecosystem therefore read front matter more simply than YAML does", but `as-is.md:41` (S-04) describes Harness²'s own validator, the only client observation is Cursor (`as-is.md:86`, O-11), and `as-is.md:114` (U-9) says Claude Code and Codex are unknown. (b) The `name` equals folder-or-stem finding rests only on Harness²'s OpenCode and Codex validator rules (`as-is.md:42`). (c) `adr-005…:20` says the 24,000 and 8,000 character caps are "already covered by the v0.5 baseline cap (60 lines, 4 KiB)", but `docs/design/orqlet-architecture-proposal.md:2178` marks it as a design value and `src/` has no implementation. Consequence: the approver reads inferences as evidence.

**AR-10. ADR-004 misstates AS-IS S-12 and S-24.** Evidence: `adr-004…:8` says scorer artifacts are kept out of the executor's workspace by path filters (S-12) but `as-is.md:49` says the guards cover the improver's and selector's context only and the executor's network is unrestricted (`as-is.md:28`, H-10); `adr-004…:8` says a ledger asserts the expected number of sessions (S-24) but `as-is.md:61` and `as-is.md:150` (C-18) say selector and reflector sessions are outside the ledger. Consequence: the M7 plan may believe Harness² demonstrates executor isolation and complete session counts.

**AR-11. ADR-004 does not say where the evaluation harness lives relative to the rule that Orqlet never starts an agent or calls a model.** Evidence: `adr-004…:15,17,21`; `container.md:3`; `docs/design/orqlet-architecture-proposal.md:4178` ("Orqlet runs no model"); ORQLET-NOMODEL-001. Consequence: M7 can be read as authorising an Orqlet-owned runner.

**AR-12. ADR-003 states no problem it solves.** Evidence: `adr-003…:9,27`; the AS-IS records no case in Orqlet of agreement being taken as proof; cost is a workflow bump, a rebuilt manifest, three client goldens and a changed protected-set digest (`gate_status.py:70-77`). Consequence: the baseline says to add a pattern only when you can say which problem it solves here.

**AR-13. Some rejected alternatives are not real alternatives.** Evidence: `adr-002…:24` ("Excluding all of `docs/design/`"); `adr-003…:26`; `adr-004…:31` repeats ADR-005. Consequence: the approver sees fewer real options than exist.

**AR-14. "No approval is invalidated" is unsupported.** Evidence: `considerations.md:45`; `src/orqlet/application/usecases/gate_status.py:194-202` compares the header's `workflow_version` and `protected_set_digest` with the current values; `gate_status.py:70-77`; `adr-003…:15` changes a protected file. Consequence: after the upgrade the headers are probably stale. The reviewer did not check what `gate status` does with the result.

**AR-15. The wiring point for the lint is unspecified.** Evidence: `diagnose.py:60-65,108-149`; `lifecycle.py:182-203` (doctor and sync share `_diagnose_command`). Consequence: the lint may silently run in `sync` or not run where intended.

**AR-16. Cross-references and manifest bookkeeping are inconsistent.** Evidence: `container.md:37` and `considerations.md:29` attribute "Sections 21 and 12.7 … the deferred extension-content checks" to ADR-004 while ADR-004 records only §21.7; `adr-001…:24` cites ADR-005 for deferring extension skills while ADR-005's table lists other rules; "S-21" names both the Harness² demo (AS-IS) and the proposal's IDE-load spike; `data-flow.md:3` says no flow crosses a trust boundary while `manifest.yaml:27` has `trust_boundaries: []` and security is "affected"; `manifest.yaml:111-122` lists 11 of the 15 rules with no not-applicable note. Consequence: a reader following references lands on the wrong ADR.

#### Checked and found consistent
Layers ORQLET-ARCH-001/002/003 hold as drawn (`component.md:51` against `pyproject.toml:86-125`), with the caveat AR-2. EC-1 matches `component.md:44` and `adr-001…:15` in name, input and output. Every ADR has Context, Decision, Consequences and Rejected alternatives. `considerations.md:18,32` (no schema change, no new dependency) hold: the doctor JSON is a hand-built dict (`lifecycle.py:211-220`). ADR-002's context is supported by the packet table of proposal §6.14.1. ADR-003's "patch" claim matches proposal §20.8 (line 4111).

### Absence records
- CI-verdict pattern: searched `src/` and the proposal with case-insensitive `CI.verdict|verdict artifact|ci-verdict|ci_verdict|CiVerdict`; no match. Read `src/orqlet/domain/evidence_artifacts.py` in full: three patterns only.
- A design statement that has Orqlet call a model or start an agent: read all ten design files; searched `headless|subprocess|start(s)? an agent|call(s)? a model|run(s)? a model|invoke|model session|executor`; hits only ADR-001 (rejecting headless CI), ADR-005 (describing Harness²), ADR-004 (describing the M7 harness).
- Handling of Codex TOML roles in the design: searched `\.toml|Codex role|TOML`; only hit is `pyproject.toml` in `manifest.yaml:30`.
- Allocation of the new "15x" finding codes: searched `src/` for `ORQ-W15[4-9]|ORQ-E15[4-9]|ORQ-I15`; no match; 150-153 are in use; the design allocates none.
- A pattern for `Callable[[str], Mapping[str, str]]` in the code base: `strict_view` appears only in `manifest.yaml:44` and `component.md:10`.
- A watched surface missing from `expected_changes`: compared design text against the four `extractor_config` surfaces; the doctor JSON has no contract; `pyproject.toml` and `uv.lock` are not touched.

### Observations (no or incomplete evidence)
- Not verified: the strict view probably needs the block split before `DocumentLoader.load`; BOM and CRLF handling of `split_front_matter` and the line view were not compared.
- Low consequence: `adr-005…:25` calls Q-4 "superseded" while `as-is.md:97` (A-4) records that Q-4 "stays open"; the design, not the person, made that call.
- Not verified: the all-zero `base_revision`, any hash, the "1,504 passed" figure, and the claim that reading "a few dozen small files" is negligible.

### What the reviewer did not check
`orqlet standards for` was refused in the reviewer's mode, so it read the 15 rules in `.prompts/rules.yaml` (the count matches; `applicable_rules_hash` `56502a0e…` equals the manifest header). It did not verify manifest digests, run `orqlet validate design` or `orqlet gate status`, check any Harness² fact against the source, check client behaviour, run tests, read `questions.yaml`, other tasks or earlier reviews, or verify proposal sections beyond those it cites.

## Author response to round 1 (written by the design author, not the reviewer)

The design set was revised after this review. What changed:

| Finding | Response |
|---|---|
| AR-1 | The emitter fix is now in scope of this design (ADR-001 decision 1, `src/orqlet/adapters/render/emit.py` in the manifest scope), so the check and the fix land in one change and the suite stays green. |
| AR-2, AR-6, AR-8, AR-15 | The use case and the `doctor` change are removed. The domain module has two pure functions with stated types (EC-1, EC-2); the release test splits the block with the existing `split_front_matter`, loads it with the existing strict loader and calls the domain function. A missing block, a parse error and a non-scalar value are test failures, not findings. |
| AR-3, AR-12 | ADR-003 now decides to make no skill change. The only protected workflow text that changes is the `description` line of the `orqlet-research` skill, and the scope lists the files that DET-002 requires (`MANIFEST.json`, `identity.json`, `releases.json`, goldens). |
| AR-4 | Codex roles (TOML, no front matter) are stated as outside the check; Codex skills are Markdown and inside. |
| AR-5 | The CI-verdict claim is removed (the CI binding is never written to the repository, proposal line 1354). ADR-002 uses the review-record rule only. |
| AR-7 | `doctor` is not touched; the reason and the revisit condition are in ADR-001. |
| AR-9 | ADR-001 separates what is observed (Cursor agents, O-11/O-12) from what is unknown (U-9); the name-equals-folder check is dropped; ADR-005 says the cap is a proposal value, not built. |
| AR-10, AR-11 | ADR-004 states what S-12 and S-24 cover and adds the boundary: the harness is development tooling outside `src/orqlet`. |
| AR-13 | The rejected alternatives were replaced by real ones. |
| AR-14 | The compatibility consideration now says that existing artifact headers become stale after the upgrade (`gate_status.py:179-185`, ORQ-W390, verdict `NOT_RUN`) and that the built code states no refresh path. |
| AR-16 | References, the "S-21" naming, the trust-boundary statement and the standards list were corrected. |

## Round 2: reviewer text (shortened by the author: findings and evidence kept; absence records and the list of what was not checked summarised)

Verdict: **NO BLOCKING FINDINGS.** Of AR-1 to AR-16, 12 were RESOLVED and 4 PARTLY RESOLVED (AR-3, AR-10, AR-13, AR-16); the reviewer added AR-17 to AR-23, all non-blocking.

Status of the partly resolved items: AR-3 (scope still omitted `AGENTS.md` and `.github/pull_request_template.md`, whose markers carry the workflow version: `src/orqlet/adapters/render/instructions.py:24`, `pr_template.py:20`); AR-10 (ADR-004 said the ledger counts executor sessions only, but AS-IS S-24 says it requires "`4k` rollouts and `3k` improver sessions"; only selection and reflection are outside it, C-18); AR-13 (ADR-003 still rejected "Adopt Harness²'s reflector vocabulary", which is not an alternative to "no change"); AR-16 (ADR-001 and ADR-005 cited proposal §12.7 for pack content that ships skills or hooks, but §12.7 does not mention them).

New findings (all non-blocking):
- **AR-17.** The release test's coverage set contradicted itself (`adr-001…:18` "skills, agents, commands" against `component.md:39` "every Markdown file with front matter"; the 17 Claude Code files include two `.claude/rules/*.md` files whose front matter is a `paths:` list; Cursor commands have no front matter, `rules.py:64-68`; looping "each file with front matter" made the "no block" branch unreachable).
- **AR-18.** The emitter change was global, so rule files changed bytes outside the check (`rules.py:34,41,60` call the same `front_matter`; 36 front-matter goldens would change, including the two `.mdc` files); the simplest alternative was to unquote at the skill, agent and command call sites only.
- **AR-19.** The plain-safe predicate was a deny-list with undefined parts ("reads as a number", "control character"); `tests/unit/render/test_emit.py` AWKWARD includes `2026-10-20`, `0x10` and `<<`; the test oracle is the strict loader only (`yaml_loader.py:6-7`), which cannot show a YAML 1.1 reader typing a value differently.
- **AR-20.** The emitter wiring was unspecified and one sentence was wrong ("as it does for other YAML today": plain only for simple words, `emit.py:18,44`); a public predicate or a changed `yaml_scalar` or `yaml_document` signature would be an undeclared API change (`domain/python_api.py:3-6`).
- **AR-21.** ADR-002's refusal was unreachable as drawn (valid records are already left out, proposal `:1342`) and the `diff` member was not covered by the exclusion (proposal `:1307`).
- **AR-22.** The design left open how its own in-repo upgrade affects this task's approvals (`gate_status.py:194-202`).
- **AR-23.** A cause was stated as fact that the AS-IS records differently (`adr-001…:7` said Cursor "treated `model: "inherit"` as an unknown model"; `as-is.md:87` O-12 says the model "is blocked by the team's admin settings").

Observations: Q-4 "superseded" against AS-IS A-4 "stays open"; ADR-001 said `doctor` reports "edits (ORQ-E150)" while E150 covers tampered or missing protected files and W152 edited files; `releases.json` lists only 0.1.0 while `identity.json` is 0.3.0; `tests/e2e/test_m1_acceptance.py:101-103` hard-codes 0.3.0.

## Round 3: reviewer text (shortened by the author in the same way)

Verdict: **NO BLOCKING FINDINGS.** AR-3, AR-10, AR-13, AR-16, AR-17, AR-18, AR-19, AR-21, AR-22 and AR-23 RESOLVED; AR-20 PARTLY RESOLVED (the design did not say whether the public `yaml_scalar` and `yaml_document` keep their signatures).

New findings (non-blocking):
- **AR-24.** The count "32" regenerated goldens was understated under a version bump: six goldens carry `workflow@0.3.0` (`tests/golden/{cursor,codex,claude-code}/docs-2026-10/AGENTS.md:1` and three `tests/golden/common/pr_template/*.md`).
- **AR-25.** ADR-002 decisions 2 and 3 were loose: `is_excluded` has no kind parameter (`evidence_artifacts.py:63-70`; the kind comes from `parse_evidence_path`); the existing validity check `evidence_file_ok` (`binding_inputs.py:192-212`) was not cited and returns `False` for a deleted path (`:197-198`), so a deleted record would be refused without anyone deciding that.

Observations: at the same version with a different digest `doctor` reports ORQ-E161 as an error, and ORQ-W162 fires only when the installed version is lower (`diagnose.py:231-238,240`); `Vcs.diff_patch(base, head)` has no pathspec parameter (`src/orqlet/application/ports/vcs.py:113`), so leaving a record out of the diff is a v0.5 port change.

Checked consistent: EC-3 against `emit.py:56`; the 32-file test scope and path classes against `tests/golden/`; ADR-002 decision 1 against `binding_inputs.py:336-337`; the manifest scope against what the design says changes; the two tests that pin quoted forms (`test_skills.py:272-273,319`) against those that stay (`test_commands.py:42`, `test_rules_and_instructions.py:50`, `test_emit.py:146`).

What the reviewer did not check (rounds 2 and 3): `orqlet standards for`, `orqlet validate design`, `orqlet gate status`, any hash, any test or renderer run, client behaviour, and the Harness² source.

## Author response to rounds 2 and 3 (written by the design author, not the reviewer)

| Finding | Response |
|---|---|
| AR-3, AR-22, AR-24 | `AGENTS.md` and `.github/pull_request_template.md` joined the manifest scope; `releases.json` left it (it is written at release time); the version is bumped (ORQ-E161); the golden count is 32 plus six; the plan puts the in-repo upgrade last. |
| AR-10, AR-13, AR-16, AR-23 | ADR-004 wording corrected to AS-IS S-24 and C-18; the reflector bullet removed and a real alternative added in ADR-003; the §12.7 reference rewritten (no section designs extension skills or hooks); the model cause reworded to O-12. |
| AR-17, AR-18 | The test selects files by path class; the emitter keyword `plain_when_safe` is passed by the skill, role and command renderers only, so rule files do not change (EC-3). |
| AR-19, AR-20 | The predicate is an allow-list, private to `emit.py`, tested against the strict loader, PyYAML's default loader and the line view; `yaml_scalar` and `yaml_document` keep their signatures and behaviour. |
| AR-21, AR-25 | ADR-002 now classifies each changed path with the existing `evidence_file_ok`: valid records leave every list and the diff; anything else at a record path, including a deleted record, is `NOT_RUN`. The pathspec port change is stated. |

## Result

The reviewer reported no blocking finding in rounds 2 and 3. Non-blocking findings are answered in the design or listed above. The architecture reviewer did not see the final wording of the last edits (the AR-24 and AR-25 changes, the trailing-apostrophe exclusion and the E161 wording); a human reviewer of the design pull request should read them.
