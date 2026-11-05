# Architecture Reviewer: design review, round 2

Reviewer: `orqlet-arch-reviewer`, a new typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the applicable MUST rules, and no earlier review note.

Design file hashes at start (computed with `orqlet evidence hash`; the files were not changed while the reviewer ran):

```
design/adr-001-selection-boundary-modes-and-precedence.md b10f62d557e8f4583c49577113c1cc7da091ffbed5ca84673645bff3379b54d7
design/adr-002-model-policy-v2-contract-and-home.md f73149f0c912274e64e50d086df0dc67092ebfefade263dd1f3d7ca604e73bc6
design/adr-003-rendering-model-settings-into-generated-files.md d177c99d281e49c1cb87424ab23ecc9a9ac121b50ac5b529f79161931dd23c5e
design/adr-004-catalog-governance-and-release-recheck.md e0e740fa68d4805ca3e09a3247514fe477d57687d8b8572956e3a458efaba0f3
design/adr-005-fable-exclusion-by-model-identity.md facd6302fdb1941dcb9f94f7f4d526d13b455adcd6347a9bf0d17213322109b5
design/adr-006-code-review-gate-and-new-roles.md 1576574c47f55c0b4b28e31fc5df8a4e752c36d985c37f3605ab820283b873b7
design/adr-007-independence-model-identity-and-fresh-context.md c9eba4812ca38bb379cca27912e45706e4ac5a51859b435e03d095dc1efdfc81
design/component.md cc258d7c7d201b45b1676bb75f2a244cc4cf507515e1694a20788b41f944a25e
design/container.md 21ee69503fb6f3b78791f5fdc137fbe5a01d54ec7ad606622da73824657f37e3
design/context.md 84547f8e933216733e5d526a5dcb74c90cc18508d78a8981f38722189fa575e6
design/data-flow.md ded1d081c923d419ca870d2d337fe56e9d0e0a92e68efe8d389d5d06fc4e83eb
design/sequence.md b85c9bfb4300457a24cd8488a30c51bb658b1859d96282773946618fe2071f7f
design/manifest.yaml d66a78b4ae865cccafd4a0630e28a0c834dfcf0d5c8c4d9ab18fd61e29ec5d73
as-is.md 28094d9205c100197f064c7db3f8374e24a743900175ac9ebb7d4b3a598edd83
questions.yaml 55fbee2e366bf9902df2a0c49e010338b1c2d1df6179b26819df7bfc4dbcaee6
```

Note: I saved this note after revising the design in response to the round, so the hashes of the files at save time differ from these (see the responses). The round-3 note records the hashes of the revised files.

## Reviewer output (unchanged)

# Design review, round 2: `dynamic-model-profiles` (D3)

## Verdict: not PASS

There are 3 blocking findings (F-1 to F-3) and 9 non-blocking findings (F-4 to F-12). There are also a few observations at the end.

**What held up**
- ARCH-001/002/003 hold for every new component. The client adapters can stay unchanged and independent, but only if F-2 is resolved.
- The brief has its nine parts in the required order. The design set has no phase list, build order or task list.
- The `file:line` citations I checked resolve against the code. Examples are `independence.py:9-10,17,34,57-59`, `vcs.py:113` and `review_prepare.py:133`.
- Compatibility holds for existing role files, review records and approved plans. The v1 model-policy removal has only the unknown in the observations.
- The ADRs compare real alternatives.

**Tooling.** Shell commands were refused, even read-only ones. I ran no command, hash, `orqlet validate` or test. Everything below comes from reading files.

## Blocking findings

**F-1 · finding · blocking · compatibility and interface · confidence high**
- **Claim:** the record path of the new `code-reviewer` role is a persisted format that the design never covers. The domain pattern that recognises review records admits two roles only. A `code-reviewer` record would be rejected with ORQ-E400, and BC-15 ("a `code-reviewer` record validates") could not hold. If the pattern were bypassed, the record would count as an ordinary input to its own review binding and make every review of the phase stale.
- **Evidence:**
  - `src/orqlet/domain/evidence_artifacts.py:27`: `(?P<role>architecture-reviewer|security-reviewer)-(?P<phase>P-[1-9]\d*)-r(?P<round>[1-9]\d*)\.yaml$`.
  - `evidence_artifacts.py:3-6`: "A path is excluded from `code_tests` and `knowledge` only when all three conditions hold: it matches exactly one of three patterns … Anything else is an ordinary input."
  - `validate_records.py:89-96`: when `parse_evidence_path` finds no match, ORQ-E400 says the file "is not at the exact path of a … record … a file elsewhere is an ordinary input, not evidence".
  - `binding_inputs.py:196` and `:206` apply the same functions when deciding what leaves a binding.
  - The design names the path at `adr-006:17`: "`docs/design/<task>/reviews/code-reviewer-P-<n>-r<k>.yaml`".
- **Absence record:** I searched `design/*` for `evidence_artifacts`, `parse_evidence_path` and "evidence-path". The only hit is the Context bullet at `adr-006:7`. No decision, no section 4 row and no `EC-n` covers it.
- **Action:** add the domain module and the record-path format to section 4, to the expected changes, and to the criteria.

**F-2 · finding · blocking · architecture · confidence high on the facts, medium-high on severity**
- **Claim:** ADR-003 Decision 1 and the section 4 interface describe one `model_setting` per `ClientRole` or `ClientSkill`. `compose` builds one `RenderRequest` for all enabled clients, and model names differ per client.
  - One value cannot carry a Claude, a Cursor and a Codex name, so BC-3 ("each client's agent file carries that name in its own field") cannot be met.
  - Two repairs keep the client adapters untouched: a per-client mapping on the role, or one request per client. The design states neither.
  - ADR-003's rejected alternative ("add a `models` field to `RenderRequest`") rests on the single-value reading.
- **Evidence:**
  - `render_all.py:121-129`: one `build_render_request(...)`, then `request = replace(request, integrations=integrations)`, then `results = [services.adapters[client].render(request) for client in clients]`.
  - `instruction_adapter.py:73-80`: `ClientRole` has `name, description, body, read_only, inputs` and no client.
  - `adr-003:17`: "each gain an optional `model_setting` (the exact name, its kind and an optional effort), set by `build_render_request` … The three client adapters and `RenderRequest` do not change."
  - `adr-002:23` says assignments have "an optional `task` and `client`". The ADR-002 Decision 7 table gives different names per client.
  - The per-client writers take only the role: `roles.py:20-46` (`claude_role`, `cursor_role`, `codex_role`).
- **Action:** state the carrier, for example a per-client mapping read inside `roles.py` and `skills.py`. Then the "adapters unchanged" claim is true.

**F-3 · finding · blocking · decisions and readings · confidence medium-high**
- **Claim:** the design narrows the person's answer in Q-21. The narrowing is missing from the readings the person confirms, and one diagram contradicts it.
  - Q-21 lists an "independent session" as a fallback.
  - ADR-006 and F-6 say a new session of the same client is I1 and does not satisfy the gate.
  - `data-flow.md` still lists "other session" as a fallback.
  - Section 8 says none of its readings contradicts a ledger answer.
- **Evidence:**
  - `questions.yaml:394`: "independent session or human (I3) when no qualifying reviewer exists".
  - `adr-006:20`: "A new session of the same client is I1 and does not satisfy the gate."
  - `component.md:79` (F-6): "a new session of the same client is only I1".
  - `data-flow.md:24`: "fallback: other client, other session, human code-owner review (I3)".
  - `component.md:152`: "none contradicts a ledger answer". The readings at lines 154-159 do not mention "independent session".
- **Absence record:** I searched `design/*` and the ledger for "independent session", "other session" and "new session". The hits are `adr-006:9,20`, `component:79`, `data-flow:24` and `questions:394`. No ledger question covers the reading.
- **Action:** either list the reading ("independent session" means a session in another client) or ask the person. Fix `data-flow.md:24`.

## Non-blocking findings

**F-4 · finding · non-blocking · consistency · confidence high.** Statements left over from the round-1 fixes now contradict the brief or the ADRs.
- `sequence.md:23` says "exit 0 or 1". The brief and BC-33 say 0 or 5, and `validate.py:40` says "FAIL and NOT_RUN both exit 5".
- `data-flow.md:35` lists `RenderRequest.models`. `adr-003:17` says `RenderRequest` does not change.
- `container.md:35` places exclusion matching "inside model_resolution". `component.md:57` makes it `domain/model_identity.py`.
- `data-flow.md:26` says "observed model matches an exclusion". `adr-005:20` and BC-9 say "requested or observed".
- `container.md:16` and `:65` give `prompts_seed.py` the policy seed. Section 4 does not mention it.
- `container.md` draws `u_rec --> a_git`, and the component view draws `ports --> git`. These are application-to-adapter arrows, while the same diagrams draw the other client-adapter arrows inward (`cl --> ports`).

**F-5 · finding · non-blocking · consistency · confidence medium-high.** The documents disagree on three points.
- On modes: BC-7 and ADR-003 Decision 4 say a skill assignment "writes" front-matter and do not require `manual`. `adr-001:20` says `manual` "is the only mode that renders a pin".
- On Codex and identities:
  - `component.md:41` says a `code-reviewer` record "requires … the model identities". The rejected alternative at `adr-007:41` says an observed model cannot be required, and F-7 treats a Codex record as valid with an unknown identity.
  - C-10 (`component.md:174`) words MODEL-002 as "names the models that ran". That conflicts with the unknown-identity case.
- On the clock: section 3 says the `reviewed_for_release` and `retires_on` checks are "both read through the Clock port". Only `retires_on` needs a clock.

**F-6 · finding · non-blocking · requirements · confidence medium.** R-7 is partly unmet, and some persisted fields serve no stated requirement.
- R-7 asks for "an independent quality threshold" and "no silent lowering" (`component.md:23`). No ADR or BC addresses either. I searched `design/*` for "quality threshold" and "lowering"; the only hit is the requirement row.
- `diversity` is a section of the persisted policy (`adr-002:24`, EC-1 at `manifest.yaml:52`). No ADR defines its content or consumer. ADR-007 only mentions a skill "diversity step".
- `pr-text` is an assignment target (`adr-002:23`), but the PR text goes through the role `orqlet-pr-writer`. The design does not say how a `pr-text` assignment reaches that role.
- `approval_ref` "must cite the data-egress decision" (`adr-002`, `adr-004:D1`), yet Q-6 says "no restriction". A validator can check only that the field is present.
- The header field `status` also has no consumer.

**F-7 · finding · non-blocking · requirements · confidence high.** R-8 ("NOT_RUN without a fresh context") is met only for `code-reviewer`.
- `adr-007:19`: for the other two roles the attestation "is optional so existing records stay valid". A new architecture or security record with no attestation still passes.
- The request says "each code, architecture and security review" (`as-is.md:1078`). Section 2 and section 8 do not state this limit. The design already uses `workflow_version` to scope new rules, so it could apply here too.

**F-8 · finding · non-blocking · acceptance criteria · confidence medium-high.** Behaviours in the brief have no criterion, and one criterion is not testable as written.
- No BC covers these behaviours: `upgrade` refusing with exit 3 on an invalid policy; `upgrade` reporting stale reviews and a pending binding (`component.md:40`, `adr-003:D7`); ORQ-E415 until the role-bindings diff is applied (F-13).
- `models resolve` under `automatic` with `--different-family-from` and no qualifying candidate is ambiguous. The brief gives exit 0 for "an automatic result" and exit 1 when "no candidate qualifies" (`component.md:39`). The review skill needs to learn that none qualifies.
- BC-22 ("does not state that read-only is not enforced") does not say what counts as a statement. A closed field would be testable and free text would not.

**F-9 · finding · non-blocking · interfaces · confidence high.** Section 4 omits existing code that must change.
- `capabilities.py:14-47` (`IMPLEMENTED_COMMANDS`): `render_steps` drops a skill step whose command is not listed (`capabilities.py:1-5`, `workflow_sources.py:123`). The opening-step hint and the diversity step name `models resolve`, so both commands must be added.
- `independence.py:57-59`: `minimum_independence` takes only a change class. The code reviewer needs I2 at every class, so it needs a role input.
- `render_all.py:68-70` (`REVIEW_AGENTS`) and `review_prepare.py:44-47` (`DEFAULT_REVIEWERS`) hard-code two reviewers. ADR-006 Decision 6 says "from the same data", but A-58 says `review prepare` does not read role-bindings.

**F-10 · finding · non-blocking · compatibility · confidence medium-high.** The pending diff of a changed seed runs from the team's current file to the new seed. It is not a three-way merge.
- `changeplan.py:222` calls `_propose(wanted.path, None, existing, wanted.content)`.
- `classify.py:71-78` returns `SEEDED_PROPOSAL` when the recorded seed differs.
- So a team's `approved` entries appear as removals against an all-`proposed` seed. ADR-004 Decision 5 and BC-12 say only "pending diff". State the limit, or define how a team reads the diff.

**F-11 · finding · non-blocking · manifest · confidence high.** The CODEOWNERS claim in EC-7 and ADR-004 Decision 2 is inaccurate.
- `.github/CODEOWNERS:2` already has `.orqlet/** @tmishari`, so the policy path is owned.
- What is unowned: `src/orqlet/workflow/seeds/**` (there is no `src/` pattern) and `.github/CODEOWNERS` itself (only `.github/workflows/**` is listed).
- EC-7's expected state ("a second owner … exists (Q-32)") presupposes an open question.

**F-12 · finding · non-blocking · architecture · confidence medium.** ADR-005 says the exclusion is "enforced in four places", but the renderer is not independent of the resolver.
- `adr-005:18-19`: "Renderers never write an excluded name (ADR-003)". ADR-003 has no renderer-side check; Decision 6 is resolver behaviour.
- `ClientRole.model_setting` carries only the chosen name. ADR-005's own Consequences say "vendor names do not belong in code".
- The independent checks are the resolver, `validate model-policy` (including drift) and `validate review`. Say three, or pass the exclusion list to the renderers.
- The family-tag match in ADR-005 Decision 1 also needs a rule for catalog entries that are `proposed`, given BC-10.

## Observations (never block)
- Cursor reads `.claude/skills` as well (`cursor.py:20-23`, ORQ-L004). A Claude-only skill pin file is therefore visible to Cursor when both clients are enabled. F-4 of the brief ("Cursor documents no skill-level model") does not record this as unknown.
- The v1 model-policy schema ships in the workflow package. A downstream project could hold a v1 file at `.orqlet/model-policy.yaml`. `upgrade` would then refuse with exit 3. Nothing in the repository settles this, and the design does not name it as unknown.
- ADR-004 does not say where release-time evidence files live or what a downstream team's `documented` reference resolves to.
- I confirmed that the current ledger has no Q-29 (Q-28 is followed by Q-30). I cannot confirm that none ever existed, because git history was not reachable.

## Self-check

| Check | Result |
|---|---|
| (1) R-1 to R-16 against decisions and limits | Done. R-1, R-4 (task is resolve-only), R-6, R-11, R-12, R-14 and R-16 are met with limits stated honestly. R-7 and R-8 are partial (F-6, F-7). |
| (2) Layering and the "adapters unchanged" claim | Done. Compliant with `pyproject.toml:82-130`. The claim holds only after F-2. The selection type in the ports module is confirmed (C-11). |
| (3) ADR consistency | Done. Contradictions are F-3, F-4 and F-5. The statements on which modes pin and which entries feed family derivation are consistent. |
| (4) BC-1 to BC-35 | Done. Each has a source. Gaps are in F-1 and F-8. |
| (5) Compatibility | Done. Plausible against the code. Exceptions are F-1 and F-10. |
| (6) No phase order | Pass. |
| (7) Manifest | Done. EC coverage misses the record path (F-1). The EC-7 text has F-11. Considerations are honest. The `reviews: []` and `not-run` entries are honest for now. |
| (8) Ledger and readings | Done. Q-32 to Q-36 and their `blocks` values match section 8. The readings list is missing the Q-21 narrowing (F-3). |

**Not examined**
- The manifest `sha256` values and `as_is_ref` (no shell).
- `orqlet validate design`, `validate ledger`, `standards for`, import-linter and the tests.
- The vendor evidence files and every vendor capability claim, beyond grepping for model names.
- The original request text; I used the AS-IS restatement.
- Roles and skill sources, golden files, `tools/*.py` and CI.
- The AS-IS body beyond about 35 spot-checked A-n citations.
- A security review; this one covers architecture only.

## Responses of the design author (round 2)

Each blocking finding was checked against the code: `evidence_artifacts.py:27` (two roles only), `render_all.py:121-129` and `instruction_adapter.py:73-80` (one request for every client, a role with no client), and the ledger (`Q-21` says "independent session"). All three are correct.

| Finding | Disposition | Change |
|---|---|---|
| F-1 | Accepted | The record-path pattern, `binding_inputs`, `capabilities.py`, the two reviewer maps and `minimum_independence` are in ADR-006 decision 6, in the interfaces of the brief, in EC-3 and in new BC-36, BC-41. |
| F-2 | Accepted | `ClientRole` and `ClientSkill` carry a per-client mapping `model_settings`; each per-client writer reads only its own entry. ADR-003 decision 1, the interfaces, BC-3 and a new rejected alternative say so. |
| F-3 | Accepted, and widened | A new ledger question, Q-37, asks the person whether an independent same-client session may satisfy the gate; the brief's section 8 lists the reading; `data-flow.md` is corrected. The design also no longer narrows Q-21's definition of I2 (see the security review, F-6). |
| F-4 | Accepted | `sequence.md`, `data-flow.md` and `container.md` corrected; section 4 gains the `prompts_seed.py` row; the application-to-adapter arrows now read "implements port". |
| F-5 | Accepted | A skill assignment renders only in `manual`; a `code-reviewer` record needs the identity fields present, with null and `identity_source: unknown` allowed; MODEL-002 reads "names the models that ran, or says they are unknown"; only `retires_on` needs the clock. |
| F-6 | Accepted | ADR-006 decision 7 defines the quality threshold (the coder's profile or a higher one; a lower one is `outside-profile`) with BC-38; `diversity`, `pr-text` and the file-level `status` are removed; `approval_ref` is an attested pointer checked for presence and format. |
| F-7 | Accepted as a stated limit | Section 8 says R-8 holds strictly for `code-reviewer` records and why; a later change can require it for the other two by `workflow_version`. |
| F-8 | Accepted | BC-37, BC-38, BC-42 added; the exit status of `models resolve --different-family-from` with no candidate is 1 in every mode; BC-22 names a fixed phrase. |
| F-9 | Accepted | ADR-006 decision 6 and section 4. |
| F-10 | Accepted | ADR-004 decision 5 says the diff is current file to new seed, a merge aid. |
| F-11 | Accepted | ADR-004 decision 2 and EC-7 name the unowned paths; Q-32 is widened. |
| F-12 | Accepted | ADR-005 says "checked in three places", and an exclusion applies to entries in every state. |
| Observations | Accepted | ADR-003 notes Cursor reads `.claude/skills`; ADR-002 names the v1-file case (exit 3); ADR-004 says where release evidence lives. |
