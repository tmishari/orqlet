# Security Reviewer: design review, round 2

Reviewer: `orqlet-security-reviewer`, a new typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the stored GitHub evidence file and the applicable MUST rules. Its own self-check says it left `reviews/*-r1.md` unread to stay independent.

Design file hashes at start: identical to the list in `architecture-reviewer-design-r2.md` (both round-2 reviewers ran against the same files). The design was then revised in response to this round; the round-3 note records the hashes of the revised files.

## Reviewer output (unchanged)

# Design security review: `dynamic-model-profiles` (D3)

**Verdict: FAIL.** One blocking finding (F-1), then 15 non-blocking findings.

Revision examined: base `b7b113c9141e1ef42e9d6e2204e565cb27cdf295`, read from `.git/refs/heads/dynamic-model-profiles-design`. The design files are the working-tree copies.

**Not run.** Shell was unavailable in Ask mode. I did not run `orqlet standards for`, `orqlet validate design` or `orqlet evidence cite`. The `quote_sha256` values are not computed, and the standards text is taken from your message.

---

## Blocking

### F-1: A deleted policy file is never restored or reported, and the design says the opposite
- **Severity:** blocking. **Category:** authorization and fail-open. **Confidence:** high.
- **Claim:** For a project that has already been seeded, `orqlet upgrade` does not recreate a deleted `.orqlet/model-policy.yaml`. `orqlet doctor` does not report it either. The design promises both.
  - F-15 gives the recovery as "Run `orqlet upgrade` to seed it".
  - ADR-005 says "`orqlet upgrade` proposes the shipped Fable entry again as a pending diff".
  - Neither holds for a deleted file. `validate review` then falls back to "legacy rules" with no exclusion list. The Fable exclusion (R-12) is silently off, and nothing re-enables it.
- **Evidence:**

```72:73:/Users/tmishari/Documents/orqlet/src/orqlet/domain/classify.py
    if current is None:
        return FileState.SEEDED_KEEP  # the team deleted it; Orqlet never brings it back
```

```82:83:/Users/tmishari/Documents/orqlet/src/orqlet/application/usecases/diagnose.py
        if entry.owner is OwnerMode.SEEDED:
            continue  # team-owned after the first write: never drift
```

  - The design text it contradicts:
    - `component.md:88`: "The policy file is absent … Run `orqlet upgrade` to seed it".
    - `component.md:41` and `:124`: "With no policy file the legacy rules apply and the report says that no exclusion list was available."
    - `adr-005…md:29`: "A deleted policy file or a removed entry removes the exclusion … `orqlet upgrade` proposes the shipped Fable entry again as a pending diff".
  - `_seeded` (`classify.py:65-78`) only proposes a diff when the file exists and the seed text changed. A recreate happens only when the lock has no row for the file (`recorded is None`, `current is None` gives `NEW`).
  - For contrast, a deleted `role-bindings.yaml` fails closed. `approved` becomes false and the record gets ORQ-E415 (`validate_records.py:306-333`). The policy file is the only one of the two that fails open.
- **Suggested action:**
  - Correct F-15 and ADR-005.
  - Decide before the plan how deletion is detected. One option: treat "the lock has a seeded row for the policy, or the base tree has the file, but the staged tree does not" as an unloadable policy. That gives an error for every record that names a model, not the legacy rules.
  - State that `validate model-policy` reports that case as a deletion.

---

## Non-blocking (most important first)

### F-2: The exclusion and family data come only from the tree under review
- **Confidence:** medium.
- **Claim:** `validate review` reads the policy from the staged tree, the same tree the change author controls. One change can remove the Fable exclusion, add `approved` entries with chosen `family` values, and include a record that passes against its own edits. The design relies on code-owner review of the edit, but host enforcement is unconfirmed (Q-34 is open, Q-32 is open).
- **Evidence:**
  - `adr-007…md:25`: "from the staged git tree for `validate review`, so that independence is derived from the exact snapshot that was reviewed".
  - `adr-005…md:29`: "The protection is the review of the edit".
  - `validate_records.py:306-308` reads `target.tree`.
  - `review_prepare.py:133` shows the target already carries `target.base`.
- **Action:**
  - Take exclusions as the union of the base policy and the staged policy.
  - Take `family` only from entries that are `approved` at base, or at least emit a closed finding `policy-changed-in-this-change`.
  - This fix also covers F-1.

### F-3: The one matching rule has bypass gaps
- **Confidence:** high on the facts, medium on exploitability.
- **Claim:**
  - (a) "Whole word" `fable` does not match digit-adjacent spellings such as `fable5` or `Fable5.1`. Only `- _ . space` count as separators.
  - (b) Brackets and the "provider prefix … and similar" are stripped as part of normalisation. If that happens before the contains-test, `x[model=fable]` or an odd prefix hides the token. The prefix list is open-ended ("and similar").
  - (c) BC-18 and ADR-007 D3 say a different effort is not a difference. That works only for bracketed spellings. The repo's own example, A-66, records `claude-sonnet-5-5-xhigh`, which matches no catalog entry. It is "unknown", so the same-model rule never fires.
  - (d) An alias route that is `approved` can be remapped by `ANTHROPIC_DEFAULT_*_MODEL`. The exclusion only sees the declared `resolves_to`.
- **Evidence:**
  - `adr-005…md:15` (matching rule).
  - `component.md:111` (BC-18).
  - `adr-007…md:18`.
  - `as-is.md:360` (A-66: "ran on claude-sonnet-5-5-xhigh").
- **Action:**
  - Run the exclusion test on the raw NFKC and case-folded string as well as the stripped form, including bracket contents.
  - Match `fable` at letter/digit boundaries or as a substring after separators are removed (over-matching is fail-safe).
  - Use a closed provider list.
  - Define suffix handling in data, or drop the BC-18 claim for non-bracket spellings.
  - Add `Fable5`, `fable-5.1-xhigh` and `x[model=fable]` to BC-9 and BC-18.
  - Warn when an alias route is rendered.

### F-4: `ModelRef` is a length bound, not an injection defence, and JSON-escaping does not stop prompt injection
- **Confidence:** medium.
- **Claim:**
  - 128 printable characters is enough for an instruction aimed at an agent.
  - Strings are echoed to an agent that acts on the output:
    - `models resolve` prints model names.
    - `validate review` warnings "name both".
    - The drift warning would echo a hand-edited agent file's `model:` value (no gate is stated for that).
    - CLI arguments (`--override`, `--different-family-from`) are built by the agent from text it read in the client.
  - "No control character" and "printable" are ambiguous for bidi and format characters and for confusables such as Cyrillic `а`.
- **Evidence:**
  - `adr-002…md:25`: "bounded, printable `ModelRef` … Findings echo a model string only JSON-escaped".
  - `component.md:49` and `:112`.
  - `adr-007…md:26` (the skill passes `<coder model>` into a shell command).
  - `.claude/skills/orqlet-review/SKILL.md` steps 6–8 (the agent reads validator output).
- **Action:**
  - Use an ASCII allow-list such as `[A-Za-z0-9._:/@+-]` for `id`, `family`, `name` and `resolves_to`. Refuse, never truncate.
  - Apply the same type to CLI arguments and to values extracted from agent files.
  - Echo only after validation, preferably as a classification such as `unknown-identity`.
  - Add a test with an instruction-shaped 128-character string.

### F-5: `coder_binding.client` and `agent.client` are free text, and "no worse than today" is wrong for D1 and D2
- **Confidence:** high.
- **Claim:** "Different client" is plain string inequality of two unvalidated fields. The design now requires I2 for the code reviewer at every class. Today D1 and D2 need only I1, so these fields did not decide the outcome. Now they do, and the sentence "no worse than today's derivation" is true only for D3.
- **Evidence:**
  - `review_result.py:34` and `:40`: `client: str = Field(min_length=1)`.
  - `validate_records.py:318-322` compares `agent_client` with `coder_client`.
  - `adr-007…md:36`.
- **Action:**
  - Make both fields a closed enum of the three clients, with one normalisation.
  - Correct the consequence sentence.

### F-6: Recording "unknown" is rewarded
- **Confidence:** medium.
- **Claim:** Truthfully recording that both identities are known and equal gives I1. Omitting the identity gives a "claimed I2" with only a warning. The same-model refinement therefore penalises honesty and passes omission.
- **Evidence:**
  - `adr-007…md:20` (decision 5).
  - `component.md:110` (BC-17).
- **Action:**
  - Keep Q-21's reading only if the person confirms it for unknown identities. This is a decision to put to the person.
  - Make the report state "gate passed on an unverified claim" at the gate line, not only as a warning.

### F-7: Attested fields have undefined semantics and cannot do what the text implies
- **Confidence:** medium.
- **Claim:**
  - (a) `identity_source: client-reported` is not defined. A model's statement about itself would qualify, and the orchestrating (coder-side) agent writes the records.
  - (b) `approval_ref` is a "pull-request or merge-commit reference". The merge commit of the change that adds it cannot exist yet. The conventions use squash merge, so only a predicted PR number or an earlier reference is possible.
  - (c) "Must cite the data-egress decision" cannot be checked by presence or format. `approved_by` is not tied to the PR author.
- **Evidence:**
  - `adr-002…md:25`.
  - `adr-004…md:16`.
  - `SKILL.md` step 6 ("Save one record per reviewer").
  - `adr-007…md:17`.
- **Action:**
  - Define `client-reported` as copied from a client output channel such as usage output or a task card.
  - Replace the self-reference with a field that is verifiable, or say plainly that it is a pointer to prior evidence.
  - State that the data-egress citation is a free-text attestation.

### F-8: Host authorization is partly overstated or under-specified
- **Confidence:** medium.
- **Claim:**
  - (a) EC-7 and ADR-004 D2 add an entry for `.orqlet/model-policy.yaml`. `.orqlet/**` already owns it. The real gaps are `src/orqlet/workflow/seeds/**`, `.github/CODEOWNERS`, `src/orqlet/domain/**` (matching rule and independence) and `tests/**` (the guard tests). There is no catch-all. Last match wins, which the design does not state.
  - (b) The rationale "a pull request cannot weaken its own review" is not supported by the stored excerpt. It says nothing about which branch's CODEOWNERS applies.
  - (c) "The design cannot close the administrator bypass" is stronger than the excerpt, which does not say whether the bypass can be disabled.
  - (d) The evidence is search-tool excerpts. The pages were not fetched and processing is "unknown".
  - (e) Owners need write access (excerpt item 6), but that is not made a check or added to Q-32.
- **Evidence:**
  - `.github/CODEOWNERS` line 2 (`.orqlet/** @tmishari`).
  - `adr-004…md:16` and `:30`.
  - `github-required-reviews-and-codeowners.md` lines 5–6 (the "Tool: WebSearch … pages themselves were not fetched" statement) and 12 (the admin-bypass excerpt).
  - `manifest.yaml` EC-7 (line 94).
- **Action:**
  - Extend EC-7 to the paths in (a).
  - Fetch or confirm the host pages.
  - Add write access and ordering to Q-32 or Q-34.

### F-9: "Enforced" and "deterministic" overstate what runs
- **Confidence:** high.
- **Claim:**
  - The Fable exclusion is "enforced in four places", and ORQLET-MODEL-001 and ORQLET-MODEL-002 are labelled "deterministic". Every one of those checks is a manual command. CI runs no `orqlet` validator.
  - The repo's own convention is that a "deterministic" rule names a check that fails the build.
  - Q-36 covers only NOT_RUN gated reviews. Nothing asks about `validate model-policy` (exclusion error, `approved_by` check, drift) at merge time.
- **Evidence:**
  - `component.md:138` and `:174`.
  - `as-is.md:243-247` (A-44).
  - `.prompts/rules.yaml:4-5`.
  - `adr-006…md:28`.
- **Action:**
  - Say "checked", not "enforced".
  - Give MODEL-002 an honest class, or a `check_ref` that fails the build.
  - Widen Q-36 to cover `validate model-policy` on the repository's own policy.

### F-10: The exclusion scan covers only Orqlet-generated files
- **Confidence:** medium.
- **Absence record:** I searched `docs/design/dynamic-model-profiles/design/` with `rg` for `settings.json`, `config.toml`, `team-authored` and `every generated agent`. Only generated agent and skill files are scanned (`adr-003…md:24`, `adr-005…md:19`).
- **Claim:** A team-authored agent file or a project-level client settings file in the repository that names Fable is not seen by any validator.
- **Action:** Scan every agent and skill file in the client folders as a read-only check, and say whether project settings are in scope.

### F-11: The policy field `diversity` has no semantics
- **Confidence:** high (absence).
- **Absence record:** I searched the design folder for "diversity". It appears at `adr-002…md:24` ("`diversity` for the code reviewer (ADR-007)"), and `manifest.yaml` line 52 only repeats the field name. ADR-007 never defines it.
- **Claim:** A team-edited knob that is undefined could lower the I2 floor or the R-7 rule ("no silent lowering").
- **Action:** Define it as unable to lower the floor, or remove it.

### F-12: "Its reach is the draft text" is wrong on Codex
- **Confidence:** medium.
- **Claim:**
  - The same sentence says Codex "cannot enforce read-only for a custom agent file".
  - The conclusion does not follow. A-108 says the parent's sandbox, approval and MCP settings are inherited.
  - The new `orqlet-pr-writer` runs on the cheapest model and reads a diff that is untrusted content.
- **Evidence:** `adr-006…md:23`.
- **Action:** State the real reach on Codex and the residual risk. Consider not rendering the role for Codex, or say the person must review the actions taken as well as the draft.

### F-13: The credential scan is narrower than "credential-shaped free text"
- **Confidence:** high.
- **Claim:**
  - The scanner is the MCP scanner. Its token rule has a fixed prefix list: GitHub, Atlassian, `sk-ant-`, `AKIA` and Slack.
  - It has no OpenAI `sk-`, xAI or Google key shape. Those are the vendors this design names.
  - Keyed values such as `api_key:` are caught by another rule. Unkeyed free text is not.
- **Evidence:**
  - `mcp_credentials.py:59-68`.
  - `component.md:38`.
  - BC-32 (`component.md:123`).
- **Action:** Extend the list or state the limit.

### F-14: The guards on the shipped seed are narrower than the risk
- **Confidence:** medium.
- **Claim:**
  - The tests check `name` and `resolves_to` against an evidence file written by the same maintainer or agent. That proves consistency, not truth.
  - `family` is the field that feeds independence once an entry is approved. It is not covered. `id` and free text (`reason`, `source`, capability statements) are not covered either.
  - The pending diff for a changed seed is current-to-seed for the whole file (`_propose`, `changeplan.py:378-391`). Applying it wholesale drops team approvals and team-added exclusions.
- **Evidence:**
  - `adr-004…md` D4.
  - `changeplan.py:378-391`.
- **Action:**
  - Add `family` and `id` to the guard tests.
  - Limit seed free text to a closed ASCII character set and a length.
  - Add "check `family` against the cited page" to the approver's checklist.
  - Present the proposal as a merge aid.

### F-15: The path-exclusion parameter of `diff_patch` is not specified
- **Confidence:** low.
- **Evidence:**
  - `adr-007…md` D8.
  - `component.md` section 4 ("one new optional parameter").
  - `git_runner.py:88-105`: `_check_options` inspects only arguments before `--`.
- **Claim:** The design does not say the exclusion is a constant, how it is spelled as a pathspec, or that it goes after `--`.
- **Action:** Fix it as a constant in `review_prepare`. BC-21's sentinel scan covers the result.

### F-16: Internal contradiction on exit status
- **Confidence:** high.
- **Evidence:**
  - `sequence.md:23` says "exit 0 or 1".
  - `component.md:38` and BC-33 say 0 or 5, which matches `validate.py:38-47`.
- **Action:** Fix `sequence.md`.

---

## Checked and consistent
- **Loader pattern.** `integrations_source.py` follows the pattern the design cites: 256 KiB cap, strict loader, no value echo.
- **Strict YAML loader.** It rejects anchors, aliases, duplicate keys and tags, and caps depth at 32 and nodes at 50,000 (`yaml_loader.py`). That bounds denial of service from a hostile policy file, so I raise no separate finding on collection size.
- **Rendering.** `front_matter` and `toml_table` quote through `json.dumps` and `_ESCAPE` (`emit.py`). A model string cannot break out of the front matter or a TOML basic string.
- **Packet.** `review_prepare` exports every tracked file (`:110-133`), so the `reviews/**` exclusion is needed. The design-manifest copy holds only `role` and `note` paths (`design_set.py:126-128`), which matches the design's claim.
- **Independence module.** `independence.py` and the plan-level review-evidence validator match the design's description.
- **Honesty about attestation.** ADR-004, ADR-007 and `data-flow.md` say plainly that `approved_by`, identity and freshness are attested.
- **Seed rules.** Everything shipped is `proposed`, only non-`proposed` entries feed identity, and there is no network, new dependency or model SDK.

## Always-applied rules
- **Credentials rule.** I scanned the design and ledger for secrets and found none. The only finding on the credential check itself is F-13.
- **Certificates rule.** No certificate material appears in the files I read.
- **Crypto rule.** The design uses only SHA-256, which is allowed.

## Self-check (orqlet.self-check/v1; role security-reviewer, phase design)
- Design set read in full: pass.
- `as-is.md` read selectively (see below).
- Ledger read in full: pass.
- Format reference and GitHub evidence file read: pass.
- Code claims verified in `classify.py`, `diagnose.py`, `validate_records.py`, `review_prepare.py`, `git_runner.py`, `emit.py`, `roles.py`, `skills.py`, `yaml_loader.py`, `mcp_credentials.py`, `review_result.py`, `design_set.py`, `plan.py`, `changeplan.py`, `validate.py` and `.github/CODEOWNERS`: pass.
- Commands run: **not run** (no shell; `orqlet standards for`, `validate design` and `evidence cite` were not run and no `quote_sha256` was computed).
- Not examined:
  - `reviews/*-r1.md`, the existing review notes, which I left unread to stay independent.
  - Vendor evidence files other than the GitHub one. I took the A-n claims about client behaviour as stated.
  - Most of `as-is.md`. I read the header sections and facts A-21, A-25, A-26, A-44, A-55, A-64, A-66 and A-91.
  - `binding_inputs.py`, `render_request.py`, the three client adapters, `validate_plan.py`, `release.py` and the `Contract` base class.
  - The `ExitCode` values.
  - Any implementation, since none exists yet.
- Statements about GitHub behaviour rest only on the stored excerpts. This review is an additional check, not a guarantee.

## Responses of the design author (round 2)

The blocking finding was checked against the code: `classify.py:72-73` (a deleted seeded file is kept deleted) and `diagnose.py:82-83` (seeded files never drift). It is correct, and it showed that my "recreate with `upgrade`" recovery was false.

| Finding | Disposition | Change |
|---|---|---|
| F-1 | Accepted | A deleted file is not "absent": a file missing from the staged tree but present at the base tree, or with a seeded row in the lock, is unloadable; `validate model-policy` reports a deletion; `validate review` errors on every record that names a model; recovery is restoring the file from git. ADR-005, ADR-007 decision 1, the brief (section 3, F-15, F-16, BC-39). |
| F-2 | Accepted | Exclusions are the union of the base and the staged policy; families come only from entries that are not `proposed` at the base tree; `policy-changed-in-this-change` is a closed warning. ADR-005, ADR-007 decision 1, BC-40. |
| F-3 | Accepted | The matching rule is rewritten: an exclusion runs on the raw NFKC and case-folded string and on the normalised form, matches as a substring once separators are removed, uses a closed provider list, and lists reported spellings as `also_known_as` in data; the alias-route warning is added; BC-9 and BC-18 carry the variants. ADR-005, ADR-003, ADR-002. |
| F-4 | Accepted | Policy fields that name a model use an ASCII allow-list and are refused, never truncated; records accept printable ASCII with spaces and `[ ] = ,`; no finding prints a recorded string (catalog ids or `unmatched`); CLI arguments and values read from agent files use the same type; a 128-character instruction-shaped string is a test (BC-32). ADR-002. |
| F-5 | Accepted | `agent.client` and `coder_binding.client` become the closed set of three clients, and the plan checks every existing record (BC-42); the consequence sentence is corrected. ADR-007. |
| F-6 | Accepted, by removing the cause | The same-model refinement is removed: Q-21's I2 stands as the person gave it; two closed warnings, `identity-unknown` and `same-model-different-client`, print on the gate line, so recording an identity is never worse than omitting it. ADR-007 decision 5, BC-17. |
| F-7 | Accepted | `client-reported`, `person-observed` and `unknown` are defined; `approval_ref` is an attested pointer checked for presence and format; the data-egress citation is a free-text attestation. ADR-002, ADR-004, ADR-007. |
| F-8 | Accepted | EC-7, ADR-004 decision 2 and Q-32 name the unowned paths, write access and last-match ordering; the unsupported rationale and the bypass claim are reworded; the host's configuration stays Q-34. |
| F-9 | Accepted | "Enforced" becomes "checked"; MODEL-001 is `deterministic` with a `check_ref` to unit tests that run in CI, MODEL-002 is `review` until Q-36 puts a validator in CI; Q-36 now also covers `validate model-policy` on the repository's own policy. |
| F-10 | Accepted | The drift check covers every agent and skill file in the client folders; project settings files are stated as outside it. ADR-003 decision 8, ADR-005. |
| F-11 | Accepted | The `diversity` field is removed; the rule is fixed in code. ADR-002. |
| F-12 | Accepted | ADR-006 states the real reach on Codex (the parent session's sandbox, approval and MCP settings), the mitigations and the residual risk, and leaves the decision to render the role for Codex to the plan. |
| F-13 | Accepted | The scan is the integrations scan plus `sk-`, `xai-` and `AIza`; the limit for unkeyed free text is stated. ADR-002, BC-32. |
| F-14 | Accepted | `id` and `family` join the seed guard tests; seed free text is limited to printable ASCII and a length; the approver's checklist includes `family`; the diff is presented as a merge aid. ADR-004. |
| F-15 | Accepted | The exclusion is a constant held by `review_prepare`, spelled as a pathspec after `--`. Section 4. |
| F-16 | Accepted | `sequence.md` corrected. |
