# Architecture Reviewer: design review, round 1

Reviewer: `orqlet-arch-reviewer`, started as a typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the applicable MUST rules, and nothing else.

Design file hashes at start and at save (identical; computed with `orqlet evidence hash`, sha256 of each file):

```
design/adr-001-selection-boundary-modes-and-precedence.md 1ec1092ee2e72e3d90c1abab01569ee1e4f410d470b53441cf4882d3d08abeea
design/adr-002-model-policy-v2-contract-and-home.md 1e48a7c560c42cb9a21c16e8b455deac4aa5ae85715044db723998fe469fd565
design/adr-003-rendering-model-settings-into-generated-files.md a014c784977f32eb0250a6357e60e88e1b8fa41e9928be35ba64f6190c8e9510
design/adr-004-catalog-governance-and-release-recheck.md 7bb42a71ff766f5b31ea2dddf7da73b438980408d6b4d4104ee3ea0b15b1c89e
design/adr-005-fable-exclusion-by-model-identity.md 3a29559eb97bd13f215eace666d188adaeb8b404cd85f5f415fb2d9c94ae7db3
design/adr-006-code-review-gate-and-new-roles.md 9c1d6393c39c7b6744d2dbe284ef9d21651e6110c7b3f18cd8d74c7456079d86
design/adr-007-independence-model-identity-and-fresh-context.md c6e68ec1e7cf65450746579aef03278e9f92bcac3b71a5ae8d91b368009f9d04
design/component.md 8d4dbb55b0e4d187961f2da2d2a4ba8163f538e6b3806341c0012041a13be78d
design/container.md 263f2f2aa7724be8d50c775ecb5968a943c9e68d67c17515390e1c2eccb83620
design/context.md 84547f8e933216733e5d526a5dcb74c90cc18508d78a8981f38722189fa575e6
design/data-flow.md 667f60c5111515738dab51e7c056f198b555b701793c548b79e7c601f4abd564
design/sequence.md f6315028bfddabcb737e0abe7824058f13cc11053704e76fbbf67fad09143393
design/manifest.yaml ddde690c48e7743dfc0bc8d3de94399ce763991bc1b540660b6674e549a0438d
as-is.md 28094d9205c100197f064c7db3f8374e24a743900175ac9ebb7d4b3a598edd83
questions.yaml 4c3b068a3167944425a984b6d20962637f3fcaf0a70c6b4dd1e7b6c6bca21a1c
```

## Reviewer output (unchanged)

# Design review: `dynamic-model-profiles` (D3)

## Verdict: not PASS

There are 5 blocking findings (F-1 to F-5) and 11 non-blocking findings (F-6 to F-16).

The layering is sound. ARCH-001, 002 and 003 hold for every new component, and the ADRs compare real alternatives. The design set holds no phase order, build order or task list. The A-n citations I checked resolve, and so do the file:line citations in the ADRs (`render_all.py:128`, `independence.py:9-10` and `:57-59`, `release.py:1-6`).

All quotes below come from the working tree. `quote_sha256` is not computed because no shell was available in this mode.

## Blocking findings

**F-1 · finding · blocking · compatibility · confidence high**
- **Claim:** the "byte-identical with no policy" guarantee is false as stated. The design's own decisions change generated files with no policy at all: two new roles, a bullet moved out of the architecture reviewer role, and changed review and implement skills.
- **Evidence:**
  - `component.md:86` (BC-1): "With no policy file, every generated file of the three clients is byte-identical to today's golden files."
  - The same claim appears at `component.md:140` (C-3), `manifest.yaml:120`, `adr-002…:15` and `adr-003…:23`.
  - `component.md:99` (BC-14): the new roles render "with golden files and lock rows".
  - `adr-006…:30`: "Moving a bullet between role texts changes both reviewer-definition digests".
  - `component.md:100` (BC-15) and `:109` (BC-24) change skill behaviour.
- **Action:** narrow BC-1, C-3 and the manifest note to what is true. That is the model line or key of every existing role file, and no policy-driven change. State that new roles, changed role text and changed skill text change the goldens on purpose.

**F-2 · finding · blocking · architecture · confidence high**
- **Claim:** `automatic-with-fallbacks` is defined two ways, and the two produce different bytes. No BC covers it, although R-4 requires the mode.
- **Evidence:**
  - `adr-001…:23`: "as `automatic`, plus an explicit, approved, ordered fallback list that the agent may name by an explicit override".
  - `adr-003…:17`: "For `manual` and `automatic-with-fallbacks`, the renderer writes the first eligible candidate's route name".
  - `component.md:38` treats the mode like `manual` ("no eligible candidate", `missing-candidate`). F-3 and BC-3/BC-4 name only `manual`.
- **Action:** decide whether the mode pins. Then align ADR-001, ADR-003 and the brief, and add a BC and a failure row.

**F-3 · finding · blocking · correctness (R-8, BC-21) · confidence high**
- **Claim:** "a reviewer never sees an earlier conclusion" is not achieved. The design omits `reviews/**` only from the snapshot and the context copies. The packet's `diff.patch` is the unfiltered diff from the merge base to the staged tree. Review records already committed on the branch (earlier rounds, earlier plan phases) sit in that diff.
- **Evidence:**
  - `adr-007…:23`: "from the snapshot and the context copies, so a reviewer never sees an earlier conclusion".
  - `review_prepare.py:133`: `files["diff.patch"] = vcs.diff_patch(target.base, target.tree)`.
  - `vcs_git.py:167`: `"diff-tree", "-r", "-p", "--no-renames", base, head`. The port at `vcs.py:113-115` has no exclusion parameter.
- **Action:** have the packet exclude the same paths from the diff, and add a BC for it. A VCS port change is probably needed, so list it in section 4.

**F-4 · finding · blocking · compatibility · confidence high**
- **Claim:** the exit-status claim "as the other `validate` commands: 0 pass, 1 problems found, 3 refused" is wrong, and so is "an absent file gives … exit 0".
- **Evidence:**
  - `component.md:38` makes both claims.
  - `validate.py:40`: "PASS exits 0. FAIL and NOT_RUN both exit 5: not run is never success."
  - `validate.py:46` uses `ExitCode.CHECK_FAILED`, which is 5 (`exit_codes.py`).
  - The nearest sibling, `validate_integrations.py:92`, does `out.skip("… does not exist, so no integration was checked")` when its file is absent. That gives NOT_RUN and exit 5.
- **Action:** state the real statuses (0 or 5 for `validate`). Decide on purpose what an absent policy does. The `models resolve` statuses (0, 1, 2, 3) do match `exit_codes.py`.

**F-5 · finding · blocking · architecture · confidence medium-high**
- **Claim:** the manifest says every v0.5 element named in Q-15 is decided in an ADR, "tier hints and roles" included. No ADR or the brief mentions tier hints. The consequence is that R-1 ("design and planning prioritise quality") has no realisation for main-agent skills on Codex and Cursor. That follows from "main agent never pinned" plus "skills: Claude Code only".
- **Evidence:**
  - `manifest.yaml:145` makes the confirmation.
  - Q-15's answer at `questions.yaml:288`: "decide each element as an ADR in this design".
  - The v0.5 tier hints are in AS-IS A-74 (`as-is.md:398-402`).
  - `adr-003…:18` limits skills to Claude Code.
  - Absence record: I searched `docs/design/dynamic-model-profiles/design/**` for "tier" (case-insensitive). The only hit is `manifest.yaml:145`.
- **Action:** add a decision, either to adopt tier hints as profile hints in skill text or to reject them with a reason. State what R-1 means for main-agent skills. Correct the self-check.

## Non-blocking findings

**F-6 · finding · architecture · confidence medium-high**
- **Claim:** "main agent never pinned" conflicts with the skill assignment.
- **Evidence:**
  - `adr-003…:18` renders `model` and `effort` into Claude Code skill front-matter.
  - `adr-003…:19`, `component.md:93` (BC-8) and `:9` say the main agent is never pinned.
  - A-104 (`as-is.md:553`): a skill `model` override "lasts for the rest of the current turn". That is a main-session override.
- **Action:** say whether a skill pin counts as a main-agent pin, and align BC-7 and BC-8.

**F-7 · finding · architecture · confidence medium**
- **Claim:** `retires_on` makes selection depend on today's date. Neither the Clock port nor a date input appears in the design. This conflicts with the determinism of refresh-time rendering and with BC-23 ("same bytes for the same input").
- **Evidence:**
  - `component.md:77` (F-9): "a retired route is never selected".
  - `component.md:38` and `:39` use `retires_on` and `retired`.
  - A `Clock` port exists at `application/ports/clock.py`.
- **Action:** let selection depend only on the explicit `approval` state, and keep the date-based check as a validator warning.

**F-8 · finding · compatibility · confidence high**
- **Claim:** the migration of existing projects is missing from the failures. The role-bindings seed changes, so existing teams get a pending diff, not a write. Until a reviewed edit applies it, code-reviewer records fail with the error ORQ-E415. `upgrade` also creates the policy seed in existing projects, which affects what "no policy file" means.
- **Evidence:**
  - `classify.py:65-78`: `_seeded` returns `NEW` or `SEEDED_PROPOSAL`.
  - `render_all.py:230-244` builds the role-bindings seed.
  - `validate_records.py:325-333` raises ORQ-E415 for an unapproved binding.
  - `component.md:40` says only that `init` seeds the policy.
- **Action:** add a failure row and a migration note.

**F-9 · finding · architecture · confidence medium**
- **Claim:** the policy loader reads the working tree through `FileSystem`. Record validation reads contracts from the target git tree, so independence is derived from the exact staged snapshot. Two readers of one file can disagree, and the brief does not say how the tree case is handled.
- **Evidence:** `validate_records.py:306-308` reads `.orqlet/role-bindings.yaml` through `read_contract_at(services, target.tree, …)`. The design offers only `load_model_policy(services)` (`component.md:55`).

**F-10 · finding · architecture · confidence medium**
- **Claim:** the client adapters do change, but the design says they do not. `ModelSelection` is also defined in a use case while `RenderRequest` lives in the ports module.
- **Evidence:**
  - `container.md:16` and `:65` say the clients are "unchanged".
  - `claude_code.py:69`, `cursor.py:52` and `codex.py:63` call `claude_role(role)`, `cursor_role(role)` and `codex_role(role)`. `claude_skill_files(skill)` is called at `claude_code.py:68`.
  - `manifest.yaml` scope paths omit `src/orqlet/adapters/clients/**`.
  - `component.md:57` places `ModelSelection` in `model_selection`, while `RenderRequest.models` belongs to `application/ports`.
- **Action:** either carry the selection on `ClientRole` and `ClientSkill`, or add the clients to the scope and the container view. Put the type where ports can import it.

**F-11 · finding · tests · confidence medium**
- **Claim:** BC-18 is not testable as written, because the rule for matching a recorded model string to the catalog is not defined.
- **Evidence:**
  - A-66 (`as-is.md:360`) shows a client reporting `claude-sonnet-5-5-xhigh`.
  - A-118 shows bracketed options on Cursor model IDs.
  - `adr-002…:20` gives a route only an exact `name` and `resolves_to`.
  - `independence.py:29-36` uses fnmatch patterns today.
- **Related gaps:**
  - BC-20 ("validate unchanged") is ambiguous. Old records already go stale (ORQ-W410) when anything changes.
  - BC-26 names ORQLET-MODEL-001 and ORQLET-MODEL-002, which no document defines (absence search of the design folder).
  - There is no BC for `automatic-with-fallbacks`, alias routes or revert.

**F-12 · finding · compatibility · confidence medium**
- **Claim:** the conditional `code-reviewer` evidence rule cannot live where the rule is today. The check is a per-phase validator with no access to the plan header.
- **Evidence:** `plan.py:44` is the `Literal` on `Phase.review_evidence`. `plan.py:49-58` is a `Phase` validator. The version lives at `ImplementationPlan.header.workflow_version`.
- **Also:**
  - `validate_plan.py:41` (`REVIEW_ITEMS`) and `plan-format.md:47` list the evidence items.
  - EC-4 and the scope do not say the rule moves up to the plan level.

**F-13 · finding · architecture · confidence medium**
- **Claim:** the fallback "run the review in another client or session" cannot satisfy the gate for a session of the same client. BC-17 gives I1 for the same client and family, and the code reviewer needs I2. The I3 human review has no record path inside Orqlet.
- **Evidence:** `component.md:74` (F-6), `adr-006…:20`, `component.md:102` (BC-17), and `independence.py:9-10` ("never derived here").
- **Also:** `adr-006` and `adr-002` say the gate passes once a team "approves a qualifying model". With the default `automatic` mode, only a different client gives I2.

**F-14 · finding · docs · confidence high**
- **Claim:** two account facts are handled inconsistently.
  - Q-26 reports five Codex models, including "GPT-6 Sol". R-15 and ADR-002 list four and drop it.
  - The ledger skips Q-29.
- **Evidence:**
  - `questions.yaml:478` against `component.md:31` and `adr-002…:11`.
  - `questions.yaml:498` (Q-28) is followed directly by `:514` (Q-30). A search for "Q-29" in the task folder finds nothing.
- **Action:** record GPT-6 Sol as not in the catalog or ask a question about it. Explain the Q-29 gap.

**F-15 · finding · architecture · confidence medium**
- **Claim:** several choices are decisions that are not in the ledger.
  - "Every Orqlet release" is mapped to `workflow_version`. `src/orqlet/__init__.py:3` says 0.3.0 and `identity.json:4` says 0.4.0, so a CLI-only release would skip the recheck.
  - "Every phase" is read as every plan phase.
  - I2 is narrowed when two identities are known and equal.
  - Discovery and evaluation of the catalog are deferred (`adr-004…:22`). The request asked for a catalog that is "discovered and evaluated", and R-1 to R-16 do not list it.
- **Action:** put each in section 8 or the ledger.

**F-16 · observation · architecture · confidence medium**
- **Claim:** some fields and a reason serve no stated requirement or have no input.
  - The `client-version-below-minimum` reason has no input source. `client_version` is never passed (`instruction_adapter.py:101`, `render_request.py:62`).
  - `reports_model`, the profile `escalation` target and the list prices have no behaviour in the brief.
  - Doctor and sync compare against the lock, not a fresh render (A-26, C-12). The design has no failure row for a policy and generated files that have drifted apart.
  - EC-6 lists only the new commands. The changed behaviour of `review prepare`, `validate review` and `upgrade` is not in an expected change.
  - Q-33, Q-34 and Q-35 are properly in the ledger, with `blocks` values that match section 8.

## Self-check

| Check | Result |
|---|---|
| (1) R-1..R-16 each map to a decision | Done. R-1 is unmet for main-agent skills on Codex and Cursor (F-5). R-15 is a premise, not a requirement. Evaluation and the five states have no R-n (F-15). |
| (2) Layering against ARCH-001, 002, 003 | Done. Compliant. `ModelSelection` placement is open (F-10). |
| (3) ADRs agree with each other | Done. Contradiction found (F-2); weaker tensions at F-6 and F-13. |
| (4) BC-1..BC-26 testable, sourced | Done. Defects: BC-1, BC-18, BC-20, BC-26. Gaps listed in F-11. |
| (5) Compatibility claims against code | Done. Overstated (F-1); exit statuses wrong (F-4). The 3-way seeded handling holds (`classify.py:65-78`). |
| (6) No phase or build order | Pass. |
| (7) Manifest | Done. EC coverage incomplete (F-10, F-12, F-16); self-check claim false (F-5). |
| (8) Open decisions in the ledger | Done. Q-32 to Q-35 are present with matching `blocks` values. Unledgered decisions are in F-15 and F-5. |

**Not examined:**
- The manifest `sha256` values for D-1 to D-12 and `as_is_ref`. A shell was refused in this mode, so I recomputed nothing.
- `orqlet validate design`, `validate ledger`, `standards for` and the import-linter. None was run; I used the standards list you supplied.
- The original request text (not in the repository). R-n sources "Request" are checked only against the AS-IS restatement.
- The vendor evidence files and every vendor capability claim (no web access).
- Role and skill source files beyond targeted greps, the goldens, `tools/*.py` and CI.
- A security review. This one is architecture only.

## Responses of the design author (round 1)

Every blocking finding was checked against the code before it was accepted: `validate.py:40-46` (exit 5), `review_prepare.py:133` and the `diff_patch` port (no path filter), `emit.py` `_PLAIN_SAFE`, and `plan.py:49-58` (per-phase check). All five blocking findings are correct.

| Finding | Disposition | Change |
|---|---|---|
| F-1 | Accepted | BC-1, C-3, the manifest note and ADR-002 and ADR-003 now promise only that the model setting of every existing role file is unchanged without a policy; new roles and changed role and skill text change the goldens on purpose. |
| F-2 | Accepted | `automatic-with-fallbacks` does not pin (ADR-001 decision stands; ADR-003 corrected). Fallbacks are returned by `models resolve`. New BC, new failure row. |
| F-3 | Accepted | `diff.patch` gets the same exclusion (a path-exclusion parameter on the VCS port, listed in the interfaces and the scope); a BC scans the whole packet for a sentinel from an earlier record. "By construction" removed. |
| F-4 | Accepted | Exit statuses corrected to 0 and 5; an absent policy is NOT_RUN (exit 5) for `validate model-policy`, as `validate integrations` does. |
| F-5 | Accepted | New decision in ADR-001: tier hints become the profile of an assignment, shown by `models resolve --skill` and named in skill text as a hint; what R-1 means for main-agent skills on Codex and Cursor is stated as a limit. Self-check corrected. |
| F-6 | Accepted | A Claude Code skill pin is the one explicit exception to "the main agent is never pinned"; BC-7 and BC-8 aligned. |
| F-7 | Accepted | Selection depends only on the `approval` state; the date check is a validator warning through the Clock port. |
| F-8 | Accepted | Failure row and migration note added. |
| F-9 | Accepted | One parser, two entry points (working tree and a git tree), stated in the interfaces. |
| F-10 | Accepted | The selection is carried on `ClientRole` and `ClientSkill`; client adapters do not change; the type lives in the ports module. `RenderRequest.models` is dropped. |
| F-11 | Accepted | A normalisation and matching rule is defined (shared with the security review F-1); BC-18 and BC-20 reworded; ORQLET-MODEL-001 and -002 defined; BCs added for fallbacks, alias routes and revert. |
| F-12 | Accepted | The conditional rule is a plan-level check; EC-4 and the interfaces say so. |
| F-13 | Accepted | The fallback is another client or a human code-owner review; the same client in a new session gives I1 and does not satisfy the gate. Wording on "approving a qualifying model" corrected. |
| F-14 | Accepted | GPT-6 Sol is recorded as seen but outside the starting catalog (no model ID documented, A-151). Q-29 never existed in the ledger's history; the ledger is not renumbered. |
| F-15 | Accepted | Section 8 lists the assumptions the person confirms by approving the design. |
| F-16 | Accepted | `client-version-below-minimum` and `reports_model` removed; `escalation` and prices get the behaviour of display in `models resolve`; a drift check added; EC-8 added. |
