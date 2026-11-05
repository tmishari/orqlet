# Architecture Reviewer: design review, round 3

Reviewer: `orqlet-arch-reviewer`, a new typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the applicable MUST rules, no earlier review note, and a request for a concise report.

Design file hashes at start (computed with `orqlet evidence hash`; the files were not changed while the reviewer ran):

```
design/adr-001-selection-boundary-modes-and-precedence.md b10f62d557e8f4583c49577113c1cc7da091ffbed5ca84673645bff3379b54d7
design/adr-002-model-policy-v2-contract-and-home.md 38e937e046436975877b003882264845335f2fa21776712f30086c605d459754
design/adr-003-rendering-model-settings-into-generated-files.md 3c7410fd86ba5c81b863e7b28193ab7ea7be51405721501b986cfd96fba38680
design/adr-004-catalog-governance-and-release-recheck.md e1be70708fe8986ea7e80c2a0c0c4a4213ccd447894f758631b348f49f580087
design/adr-005-fable-exclusion-by-model-identity.md debce844f844f187a03a83917382fdcdd7760d581fcc66e88f41dff88aa1ecea
design/adr-006-code-review-gate-and-new-roles.md d9c45e11923efcab31523bb8de8678cd4d7c182e0356e8faff4c90fb03e8bf9e
design/adr-007-independence-model-identity-and-fresh-context.md ad76cae2c3dbe31eb1ab5a04ab1bfc521fba04b0e93b4930f66be40338acc688
design/component.md f1167c2c9a25f7b1a89d1a2b538527e39fb7c29f25cc82e49a006b52980a12cc
design/container.md 8e31b775a7cc7da3789dbaddfd436711f2ae1669419ed11a37af463ad115b2d3
design/context.md 84547f8e933216733e5d526a5dcb74c90cc18508d78a8981f38722189fa575e6
design/data-flow.md 21b2e997f5b629abc2e8dae759870b86699b0a0d040e1504c5b4d2767da9a391
design/sequence.md 2d9bee4638a3e04f71c7e34eacff84428a2b387adcbc5ca9d244683161bae667
design/manifest.yaml 6fec872501863e8a00af2eff55242a943c79f39410612be65c8bcbde72f148d6
as-is.md 28094d9205c100197f064c7db3f8374e24a743900175ac9ebb7d4b3a598edd83
questions.yaml 6828174a226b605c02843e9574157efe38843d56af2cb633e90a51f27c6e6bf8
```

The design was revised in response to this round, so the files at save time differ from these hashes.

## Reviewer output (unchanged)

# Design review: dynamic-model-profiles (D3), architecture

## Verdict: NOT PASS

Two findings block approval. Both are text or decision fixes, not redesigns. Evidence is the working tree, because `git` and `shasum` were unavailable; the manifest base revision is `b7b113c`.

**What held up.**
- **Layering:** the three client adapters call `claude_role(role)`, `cursor_role(role)` and `codex_role(role)` with the role only (`claude_code.py:69`, `cursor.py:52`, `codex.py:63`). A per-client `model_settings` read inside `render/roles.py` therefore needs no adapter change. `.agents/skills` is shared by Cursor and Codex and gets no model.
- **Migration:** `_seeded` in `classify.py:66-78` returns NEW for a seed with no lock row and SEEDED_PROPOSAL for a changed `role-bindings.yaml`. So "created as a new file" and "pending diff" are plausible.
- **Exit codes:** they fit `exit_codes.py`, and `validate.py:39-47` gives 5 for NOT_RUN.
- **Ledger and citations:** the ledger has no Q-29, and Q-32..Q-37 are open with none blocking design. The A-, U-, C-, I- and code-line citations I opened resolve.
- **Phase order:** I found no phase list or build order. ADR-004 D4 and S3 are a release procedure, and ADR-006 D6 is an impact inventory.

## Findings (`orqlet.finding/v1`, abbreviated)

**F-1 | blocking | architecture | high**
- **Claim:** ADR-006 hands a security-relevant rendering decision to the plan. The brief requires the opposite. The decision is not in the ledger.
- **Evidence:**
  - `adr-006…md:23`: "the residual risk is stated, and the plan decides whether to render the role for Codex at all".
  - `component.md:115` (BC-14): "render for all three clients as read-only files".
- **Action:** decide it in the design (render with the stated mitigation, or exclude Codex and amend BC-14 and section 3), or add a ledger question.

**F-2 | blocking | docs | high**
- **Claim:** two readings the design makes are missing from section 8, and ADR-007 says the opposite of what it does.
  - Q-21 says "known different model family". ADR-007 D2 requires both identities to be observed. Today a requested model counts (`validate_records.py:319-320`: `model_observed or model_requested`).
  - R-7 requires "a different resolved model". BC-17 gives I2 to "a different client with two equal observed identities". ADR-007 treats the same-model rule as one that "applies within a client".
- **Evidence:** `adr-007…md:20`: "The design adds no narrowing of Q-21". Section 8 (`component.md` ~171-172): "The design leaves Q-21's definition of I2 as the person gave it".
- **Action:** list both as readings for the person, and remove the "no narrowing" sentence.

**F-3 | non-blocking | architecture | high**
- **Claim:** the stated limit on R-1 omits the default mode. Under default `automatic`, subagents in Claude Code and Cursor keep `model: inherit`. The PR writer on `economy` runs on the parent's model until a team opts into `manual`.
- **Evidence:** `adr-001…md:41`: "met in full only where a client lets a project file set the model: for subagents in all three clients".
- **Action:** add "after opt-in to `manual`".

**F-4 | non-blocking | docs | high**
- **Claim:** the diagrams and one component row use the rejected single-value `model_setting`. The decision is the per-client mapping `model_settings`.
- **Evidence:** `container.md:26`, `container.md:29`, `data-flow.md:13`, `component.md:59`, `component.md:208`. ADR-003 `:17` decides the mapping, and `:40` rejects a single `model_setting`.
- **Action:** rename in all five places, then re-hash the manifest.

**F-5 | non-blocking | docs | high**
- **Claim:** EC-8 contradicts the ADRs and omits changes the brief describes.
  - EC-8 says `validate review` "reads the policy from the staged tree". ADR-005 D2 and ADR-007 D1 and D10 say base tree plus staged tree.
  - EC-8 says `upgrade` "refuses on an invalid policy". The brief and BC-37 also refuse on a deleted or v1 file.
  - Today `upgrade` tolerates a deleted seeded file (`classify.py:72-73`: "the team deleted it; Orqlet never brings it back"). Refusing is a behaviour change with no opt-out other than keeping a file.
  - No EC covers the new generated agent files (two roles across three clients), Claude skill front-matter, or lock rows. The `Surface` enum has no fitting value, so a `persisted-schema` declaration is the closest fit.
- **Evidence:** `manifest.yaml:108`; `component.md` section 3 and F-16.
- **Action:** correct EC-8 and add the missing declaration.

**F-6 | non-blocking | compatibility | medium (downstream not examined)**
- **Claim 1:** "contracts change additively" is inaccurate. EC-3 narrows `agent.client` and `coder_binding.client` from any non-empty string (`review_result.py:34,40`) to three values. My search of `docs/design/**/reviews/*.yaml` found no `client:` value outside the three, so this repo is safe.
- **Claim 2:** once a policy file exists, `model_families` is ignored (ADR-007 D1), and a requested-only model stops counting. A downstream project with populated `model_families` could drop from I2 to I1 on its first upgrade. For D3 changes that means NOT_RUN. `validate_records.py:315` shows the code reads `model_families`. Whether any project uses it is unknown.
- **Evidence:** `manifest.yaml:129`; `adr-006…md:30`; BC-20; C-3.
- **Action:** state both effects. Either fall back to `model_families` for strings the policy cannot match, or document the break and how to migrate.

**F-7 | non-blocking | correctness | high**
- **Claim:** several behaviours are unspecified or contradictory.
  - **No policy, `--different-family-from`:** section 3 gives exit 0 ("the client chooses") when no policy was ever present. BC-38 gives exit 1 "in every mode" when no candidate is eligible. With no policy these conflict.
  - **Coder's profile:** `outside-profile` (BC-38, ADR-006 D7) needs the coder's profile, but the flag takes only a model. A model can sit in several profiles (`gpt-6.1-sol` is in `quality` and `engineering`).
  - **Missing freshness attestation:** EC-3 and section 3 say it is "required". BC-16 says it "derives I0 … NOT_RUN, not an error". A required field is a schema error, not NOT_RUN.
  - **Unloadable policy on one tree:** the cases "base unloadable, staged valid" and "base absent, staged present" are not specified.
- **Action:** pick one outcome for each.

**F-8 | non-blocking | architecture | high**
- **Claim:** precedence over-claims against the modes. ADR-001 D4 says levels 1-3 "always" beat automatic ranking. In `automatic` and `automatic-with-fallbacks` they render nothing (D3), so R-5 holds only in `manual`. The source label for that case is not named.
- **Evidence:** `adr-001…md:29`.
- **Action:** say "in `manual`" and name the label.

**F-9 | non-blocking | architecture | medium**
- **Claim 1:** `approval_ref` must cite "where the data-egress decision for this repository's data class was made". Neither R-11 nor any ledger answer asks for this, and Q-6 says "No restriction: all four vendors acceptable". It looks like an unrequested requirement.
- **Claim 2:** ADR-005 says "vendor names do not belong in code". Yet the domain matching rule carries a closed list of provider prefixes (`anthropic/`, `openai/`, `google/`, `xai/`), and the scan carries vendor key shapes (`sk-`, `xai-`, `AIza`).
- **Evidence:** ADR-002 D3; ADR-004 D1; ADR-005 D1.
- **Action:** drop the data-egress requirement or ledger it, and explain the prefix and key-shape exception.

**F-10 | non-blocking | correctness | high**
- **Claim 1:** ADR-005 says "while the file exists, `orqlet upgrade` proposes the shipped Fable entry again". `_seeded` returns SEEDED_KEEP when the shipped seed equals the recorded one, so the proposal appears only when the shipped seed changes. That happens at each workflow release.
- **Claim 2:** ADR-003 says files "change only when a team opts into a pin". New roles, changed text and version stamps change protected files and `protected_set_digest` for everyone (ADR-006 consequences say so).
- **Evidence:** `adr-005…md:29`; `adr-003…md:30`.
- **Action:** correct both sentences.

**F-11 | observation | tests | medium**
- **Claim:** smaller gaps.
  - `compose` has three callers (`upgrade.py:119`, `init_project.py:155`, `explain.py:45`). The design never mentions `explain`, so its output could differ from what `upgrade` writes.
  - No BC covers ADR-001 D7 (task scope is never rendered) or the `alias-route-rendered` warning (F-17).
  - BC-33 and BC-34 cite file names rather than an R, Q, A or ADR source.

## Self-check
- **(1) R-1..R-16:** R-7 and R-1 are the weak points (F-2, F-3). R-12, R-14 and R-11 state their limits honestly.
- **(2) Layering:** holds, apart from the naming drift in F-4.
- **(3) Contradictions:**
  - Modes, exit statuses and the policy trees agree across the ADRs and the brief, except EC-8 (F-5).
  - Policy absent, deleted and unloadable are consistent. The remaining corner cases are in F-7.
  - The warnings are consistent.
- **(4) BC-1..BC-42:** testable, with the gaps in F-11. BC-33 and BC-34 cite file names as sources.
- **(6) Phase order:** none found.
- **(8) Ledger and readings:** F-1 and F-2 are the gaps.

## Not examined
- Manifest artifact hashes and the AS-IS hash (no shell).
- `binding_inputs.py:196,206` and `release.py:1-6`.
- AS-IS facts A-125 and A-129 (not individually opened).
- The files in `reviews/`, kept unread to preserve independence.
- Downstream projects.
- Vendor claims.
- Whether `validate_plan` restricts plan file operations to `scope.paths`. `AGENTS.md`, `.cursor/rules/**` and `.github/pull_request_template.md` are not in `scope.paths`, although an upgrade rewrites them (`AGENTS.md` block headers carry `workflow@0.4.0`).

## Responses of the design author (round 3)

Checked against the code before accepting: `validate_records.py:319-320` (`model_observed or model_requested` today), `classify.py:72-78`, and the five stale `model_setting` places in the diagrams and the brief. The two blocking findings and F-3 to F-10 are correct; F-11 is partly accepted.

| Finding | Disposition | Change |
|---|---|---|
| F-1 | Accepted | The decision is made in the design: `orqlet-pr-writer` and `orqlet-code-reviewer` render for all three clients with the stated mitigations, and the Codex and Cursor-MCP reach is recorded as a residual risk in both ADR-006 and the security considerations; BC-14 says "render" and no longer promises a read-only guarantee. |
| F-2 | Accepted | Section 8 lists both readings (observed-only for a family difference, narrowing Q-21's "known different family"; and the same-model rule applying within a client only, so a different client on an equal model is I2 with a warning, which does not satisfy R-7's "different resolved model" literally); the "no narrowing" sentences are removed. |
| F-3 | Accepted | ADR-001 says "after a team opts into `manual`". |
| F-4 | Accepted | `model_settings` in all five places. |
| F-5 | Accepted | EC-8 corrected (base and staged tree; refuses on invalid, deleted or v1 policy) and EC-9 added for the generated agent and skill files and lock rows. |
| F-6 | Accepted | The brief and EC-3 say the contracts change additively except the closed client set and the model-policy replacement; `model_families` still applies to a string the policy cannot match, so a project with populated `model_families` does not lose I2. |
| F-7 | Accepted | One outcome each: with no policy ever present `models resolve --different-family-from` exits 1 (no candidate can be shown different); the flag is accompanied by `--coder-profile` for `outside-profile`; a missing attestation is a schema-valid record that derives I0 (the field is optional in the schema and required by the role's rule, not a schema error); base unloadable and staged valid, and base absent and staged present, are specified. |
| F-8 | Accepted | ADR-001 says levels 1 to 3 beat automatic ranking in `manual` mode, and names the source label `automatic` for the other modes. |
| F-9 | Accepted | The data-egress requirement is dropped (Q-6 left no restriction); the provider prefixes and key shapes are explained as data held in a closed table of the domain, not in role or skill text. |
| F-10 | Accepted | Both sentences corrected. |
| F-11 | Partly accepted | `explain` is named as a `compose` caller that must report the same selection; BC-33 and BC-34 get sources; BC-43 covers task scope and the alias warning. |
