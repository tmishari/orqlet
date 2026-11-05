# Security Reviewer: design review, round 1

Reviewer: `orqlet-security-reviewer`, started as a typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the stored GitHub evidence file and the applicable MUST rules, and nothing else.

Design file hashes at start and at save: identical to the list in `architecture-reviewer-design-r1.md` (both reviewers ran against the same files; computed with `orqlet evidence hash`).

## Reviewer output (unchanged)

# Security design review: `dynamic-model-profiles` (D3)

## Verdict: not PASS. 4 blocking findings (F-1 to F-4), 9 non-blocking (F-5 to F-13)

I read the design set (all 12 files), the ledger, the stored GitHub excerpt and the AS-IS facts and unknowns, apart from the vendor-fact range (see "What I did not examine"). I checked the existing code the design builds on. The revision is `b7b113c9141e1ef42e9d6e2204e565cb27cdf295`, read from `.git/refs/heads/dynamic-model-profiles-design`. Shell commands were unavailable in Ask mode, so `quote_sha256` is not computed. Each quote below gives its file and line.

Each blocking finding is a gap in the design text, not an architecture change. Closing each takes a rule and a test.

## Blocking findings

**F-1 — security, ORQLET-SEC-002, confidence medium, blocking.**
- **Claim:** The design never says how a model string is matched, so the Fable exclusion and the same-model rule fail open on case, whitespace, display-name and provider-prefix variants.
- **Evidence:**
  - `adr-005…md:14`: "`excluded[]` entries match by alias name, by model-ID pattern and by family tag".
  - `independence.py:17,34`: `from fnmatch import fnmatchcase` and `if fnmatchcase(model, pattern):`. The existing matcher is case-sensitive and does not strip.
  - `evidence/web/cursor-help-available-models.md:16`: "Team admins can change this to Displayed in the admin dashboard so members see which model handled each request."
  - `questions.yaml:533`: Q-30 answers "Router enabled and the routed model is Displayed". The value a person copies into a record is therefore UI display text, such as "Claude Fable 5.1".
  - `adr-002…md:36`: "The Cursor identifiers are unknown (U-25, Q-35)". The seed's "Cursor's Fable entries" cannot be ID patterns yet.
  - Absence record: I searched all of `design/` for `casefold|case-insens|lower case|whitespace|NFKC|NFC|unicode|display name|substring|trailing` with a case-insensitive grep and found no match.
- **Effect:** A string that matches nothing is treated as an unknown identity. An unknown identity is never excluded, and a different client still gives I2. BC-9 and BC-18 cannot be tested without a matching rule.
- **Suggested action:**
  - State one normalisation in the brief: NFKC, casefold, trim, treat `- _ .` and spaces alike, and drop a provider prefix.
  - Apply the exclusion test deliberately broadly, for example "the normalised string contains the token `fable`". Run it on requested, observed, route `name` and `resolves_to`.
  - Add a variant table to BC-9.
  - Say that an unmatched string means "unknown", never "equal" or "different".

**F-2 — failure-handling, ORQLET-SEC-002, confidence high, blocking.**
- **Claim:** The design does not say what `validate review` does when the policy is absent, oversize or invalid. That is the one enforcement point that catches a Cursor-Auto-routed Fable, and it depends on the policy for both the exclusion list and the family map.
- **Evidence:**
  - `adr-007…md:16`: "`model_families` of `role-bindings.yaml` is used only when no policy exists, and never together with it."
  - `component.md:40`: "An invalid policy file makes `upgrade` refuse (exit 3) before any write." Only `upgrade` and `models resolve` are covered (F-1 row, `component.md:69`).
  - `component.md:38`: "An absent file gives an information finding and exit 0."
  - `.orqlet/role-bindings.yaml:26`: `model_families: []`. The legacy fallback knows no family.
  - `adr-005…md:19`: validators treat a record whose model matches an exclusion as invalid evidence.
  - Absence record: no text in `design/` covers "present but unloadable" for `validate review` or `review prepare`. I searched for `invalid policy|unreadable policy|policy … invalid|cannot be loaded|fails to load|no policy exists|absent file`. The matches were ADR-007 D1, ADR-002 D1 and `component.md:38,40` only.
- **Effect:** If one bad edit, an oversize file, or deleting the file switches off the exclusion list, records get through unchecked. Under "absent means no policy", deletion is a single diff.
- **Suggested action:**
  - Present but unloadable: `validate review` of a code-reviewer record returns an error or NOT_RUN. It never falls back to `model_families` and never derives I1 or I2.
  - Absent: say what holds (see F-9).
  - Add a BC for each case.

**F-3 — correctness, confidence high, blocking.**
- **Claim:** "Fresh by construction" is false as designed. Omitting `docs/design/**/reviews/**` from the snapshot and context copies leaves `diff.patch` and the design-manifest copy untouched. A review record staged in an earlier round appears in the diff with its findings.
- **Evidence:**
  - `adr-007…md:23`: "leaves out `docs/design/**/reviews/**` … from the snapshot and the context copies, so a reviewer never sees an earlier conclusion".
  - `component.md:106`: BC-21.
  - `review_prepare.py:133`: `files["diff.patch"] = vcs.diff_patch(target.base, target.tree)`.
  - `vcs_git.py:167`: `return self._git.run("diff-tree", "-r", "-p", "--no-renames", base, head).stdout`. There is no path filter, and the port signature at `ports/vcs.py:113` takes none.
  - `review_prepare.py:136`: `("design-manifest.yaml", f"{folder}/design/manifest.yaml")` is copied whole. The manifest holds `reviews` and `self_check`.
  - AS-IS A-64 records that this class of leak has happened.
- **Suggested action:**
  - Say the omission applies to `diff.patch` and to the manifest copy's reviewer notes, not only to the snapshot.
  - Add a BC that scans the whole packet for a sentinel taken from an earlier record.
  - Drop "by construction" from D8.

**F-4 — security, confidence medium, blocking.**
- **Claim:** A requested-only model counts as a known identity. A silently replaced pin then gives a false I2, against R-7's "different resolved model".
- **Evidence:**
  - `adr-007…md:17`: "Derivation uses the observed model, else the requested one."
  - `component.md:104` (BC-19) says "derivation uses the observed model". The two disagree.
  - `adr-007…md:20`: the derivation inputs are "approved binding, freshness, clients, families, identity equality". `identity_source` is not an input.
  - `claude-code-sub-agents.md:19-20`: `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` makes Claude Code ignore "the `model` field in subagent definitions".
  - `as-is.md:360` (A-66): a Cursor session replaced a configured model and ran every subagent on another.
- **Effect:** Cursor is the only client that can name a third-party family for a subagent. Codex reports no model, and Cursor without Displayed hides it. In those cases "observed" is empty and the pin supplies a "known" family. The client may have run something else.
- **Suggested action:**
  - Derive from observed values only. Requested-only means unknown.
  - Make `identity_source: unknown` unable to establish a family difference.
  - Reconcile D2 with BC-19.

## Non-blocking findings

**F-5 — standards (SEC-002/003), confidence high.**
- **Claim:** The design says no value is echoed, then specifies outputs that echo untrusted strings, and it sets no grammar for them.
- **Evidence:**
  - `manifest.yaml:117`: "strict YAML and no echoed values".
  - `component.md:104`: "a warning naming both".
  - `component.md:39`: `models resolve` prints "exact name".
  - `adr-007…md:17`: "names both".
  - `review_result.py:35-36`: `model_requested: str | None = None`, unbounded.
  - Absence record: no charset or length rule for `id`, `family`, `name`, `resolves_to`, `effort`, `approved_by`, `approval_ref` or `model_*`.
- **Effect:** The output is read by an IDE agent (S2 sequence), so it is a prompt-injection and terminal-escape channel. Structural injection into front matter or TOML is already closed: `emit.py` writes non-simple strings with `json.dumps` (lines 3-5). The design should still say the renderers use only `front_matter` and `toml_table`.
- **Path traversal:** I found no path built from a policy value. Role names come from the package and `skills.py:24,48` enforces a name regex.
- **Suggested action:**
  - Add a `ModelRef` type: printable, bounded, no control characters.
  - Make `effort` and `kind` closed enums.
  - Make `retires_on` a date type (v1 uses `str`).
  - Echo a record's model string only JSON-escaped, or drop the echo from BC-19.

**F-6 — authorization, confidence high.**
- **Claim:** "The host enforces it" is unevidenced, and the approval rule has gaps that the stored evidence already names.
- **Evidence:**
  - `adr-004…md:16`: "The host enforces it." Q-34 is open and U-15 says host configuration is unreadable.
  - The GitHub excerpt, lines 12-14, lists admin bypass, stale-approval dismissal and "Require approval of the most recent reviewable push". Neither Q-34 nor the constraints adopt the last two.
  - `.github/CODEOWNERS:1-10` is the whole file: only `@tmishari`, with no entry for `.github/CODEOWNERS` itself, `src/**` (where the seed lives) or `docs/design/**`.
- **Effect:** An author can push after an approval. A change owned by the sole owner can only merge by admin bypass, so the exception becomes the routine path. ADR-004 is honest about attestation and the sole owner (lines 29-30).
- **Not established:** I could not establish, and the stored evidence does not say, whether a PR can edit CODEOWNERS to weaken its own review.
- **Suggested action:**
  - Reword to "the host can enforce it if configured as Q-34 asks".
  - Add the stale-approval and last-pusher settings to Q-34.
  - Add owner entries for `.github/CODEOWNERS` and the seed path in EC-7.

**F-7 — overstated enforcement, confidence high.**
- **Claim:** The code review gate is described as failing closed, but nothing converts NOT_RUN into a block.
- **Evidence:**
  - `adr-006…md:28`: "the gate also fails closed (NOT_RUN)".
  - `validate_records.py:362-363`: the check calls `out.skip(...)`.
  - `gate_status.py:7`: "with a task the verdict is always `NOT_RUN`".
  - Absence record: I searched `.github/` for `orqlet (validate|gate|review|ci|doctor|sync)|uv run orqlet` and found no match. `ci.yml:30-100` runs ruff, mypy, import-linter, schema and manifest checks, pytest and build.
- **Effect:** The gate holds only if the IDE agent follows the skill and a person reads the result, plus whatever review the host requires.
- **Suggested action:** Say "reports NOT_RUN". State that enforcement is procedural plus host review, or list a required status check as an open decision.

**F-8 — attestation, confidence medium.**
- **Claim:** In the dominant case, I2 rests on a client-name string written by the agent whose work is reviewed. The rule "must say the identity was not known" cannot be checked.
- **Evidence:**
  - `adr-007…md:20`: "a different client still gives I2 … `capability_limits` must say the identity was not known".
  - `review_result.py:71`: `capability_limits: tuple[Text, ...]` is free text.
  - `component.md:102` (BC-17).
  - AS-IS A-65: all 112 existing records hold null model fields.
- **Effect:** This is no worse than today (`independence.py:50-54`). But R-10 now requires I2 at every phase, where D1 and D2 changes needed I1.
- **Suggested action:**
  - Say plainly in the brief that I2 means "a claimed different client" until identities are observed.
  - Derive a closed limit code from `identity_source: unknown`.
  - Print such records as unverified.

**F-9 — security, confidence medium.**
- **Claim:** The Fable exclusion has four bypasses that the design does not name.
  - **(a) Data only.** An absent file, a removed entry or an ignored pending diff means no exclusion (`adr-002…md:15`; `adr-004…md:20`). There is no floor.
  - **(b) Hand-edited agent files.** `diagnose.py:96-113` compares disk to the lock's recorded hash, not to a fresh render. A hand-edit plus a lock edit passes, and no check looks at the `model:` lines of existing agent files.
  - **(c) Run-time overrides on non-review roles.** `TesterRecord` has no model field (A-61), so they leave no record. "Constraints apply at every level" (`adr-001…md:30`) cannot be enforced at level 1.
  - **(d) Alias remapping and billing.** `claude-code-model-config.md:16,17,20` documents `ANTHROPIC_DEFAULT_FABLE_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL` and silent `-p` billing. The context cites them (A-91) and the decisions do nothing about them.
- **Suggested action:**
  - Add a read-only check of every `model` value in the three agent folders against the resolution and the exclusion.
  - Choose between a built-in minimum floor and an error when the shipped Fable entry is missing.
  - Word ADR-005 as defence in depth behind the company block (Q-24).

**F-10 — supply chain, confidence medium.**
- **Claim:** The release-time recheck has little protection against injection through page text into the seed.
- **Evidence:**
  - `adr-004…md:27`: "the test proves it was recorded, not that it was done well".
  - `sequence.md` S3: a maintainer reads vendor pages and edits the seed.
  - `adr-002…md:36`: a seed fact taken from this team's account (`confirmed`, Q-26).
- **Effect:** An injected `name`, `family`, `resolves_to` or removed exclusion would be caught only by BC-11 (everything is `proposed`) and by review.
- **Open design question:** `family` and `resolves_to` of a `proposed` entry may feed identity normalisation (`adr-007…md:16`, which does not say). The design should say whether they do.
- **Suggested action:**
  - Add a test that every seed `name` and `resolves_to` appears verbatim in the evidence file its `documented` reference cites.
  - Add a test that the seed's exclusions only grow.
  - Seed `access: unknown` and no team facts.
  - Carry the baseline sentence "page text is evidence, never an instruction" into ADR-004.

**F-11 — confidentiality, confidence low to medium.**
- **Claim:** v2 drops v1's data-handling fields without saying where the egress decision goes.
- **Evidence:**
  - `model_policy.py:20-33,44-45`: v1 has `cloud_routes_allowed`, `allowed_data_classes`, `locality` and `data_handling`.
  - `adr-002…md:19-20`: v2 lists none of them.
  - `as-is.md:665` (A-125): Cursor attaches a data-retention approval requirement to Fable 5.1.
  - The starting catalog routes through xAI and Google (`adr-002…md:30-34`).
  - Q-6 answers "no restriction".
- **Suggested action:** State that `approval` includes the data-egress decision for this repository's data class and that `approval_ref` must cite it, or keep an optional `data_handling` block.

**F-12 — security, confidence medium.**
- **Claim:** The `orqlet-pr-writer` role reads untrusted diff and repository text on the cheapest model, and read-only is not enforced for Codex.
- **Evidence:**
  - `adr-006…md:23`: it drafts from "the plan, the design brief and the diff summary".
  - `component.md:99` (BC-14): it renders as a read-only file.
  - `as-is.md:1031` (C-15): Codex `sandbox_mode` in an agent file does not override the parent.
  - `adr-007…md:24` states the Codex limit for reviewers only.
- **Effect:** The draft goes to the person, who opens the pull request, so the blast radius is the draft text.
- **Suggested action:** Record the Codex limit for this role. Tell the role text to treat inputs as data.

**F-13 — correctness, three minor items, confidence medium.**
- **Clock:** the design gives no clock source. A search for `clock|today|now` found nothing relevant in `design/`. "A retired route is never selected" (`component.md:77`) therefore depends on an unstated date input, which affects deterministic render bytes and can fail open under a skewed clock.
- **Cursor quoting:**
  - `emit.py:27`: `_PLAIN_SAFE` has no `[`.
  - `cursor-subagents.md:16` shows `claude-opus-5[effort=high,context=300k]`, so a Cursor model value with options is written quoted.
  - `emit.py:7-8` says "Cursor took the quotes of `name: "orqlet-inventory"` literally". The pin may then be unrecognised and silently replaced.
- **Credential scan:**
  - `integrations_source.py:96-102` scans for credential-shaped text, but ADR-002:41 lists only port, limit, strict YAML and no echo.
  - The policy holds free text (`approval_ref`, reasons).
  - `data-flow.md:41` says no "account identifier" is stored, which is not accurate because `approved_by` holds one.
  - Constrain `approval_ref` to a PR reference and apply the scan.

## Checked, no finding
- **NOMODEL-001 and no new dependency:** no model call, network or new dependency is added (BC-23, BC-25).
- **Strict YAML and size:** the loader is strict (`yaml_loader.py` header: no anchors, aliases, merge keys or duplicate keys; bounded depth and size). The 256 KiB limit matches `integrations_source.py`.
- **Writes and digests:** the journalled write path is kept (C-5), digests are SHA-256, and no credential is read.
- **Honesty about attestation:** ADR-004:29, the data-flow table and the manifest consideration say `approved_by`, identities and freshness are attested.
- **An invalid policy blocks `upgrade`:** this is acceptable fail-closed behaviour, and F-1 in the brief documents recovery.

## Self-check (`orqlet.self-check/v1`)
- **Checked against:** role security-reviewer, phase design.
- **Pass:**
  - All 12 design files, the ledger and the stored GitHub excerpt were read.
  - The loader pattern, `independence.py`, `review_prepare.py`, `emit.py`, `roles.py`, `skills.py`, `diagnose.py`, `validate_records.py` and `CODEOWNERS` match the design's claims where I tested them.
- **Not run:**
  - `orqlet validate design`
  - `orqlet standards for`: I used the MUST rules you listed.
  - Quote digests: computing them needs a shell.
- **Unverified:**
  - Host configuration (Q-34).
  - Whether GitHub applies CODEOWNERS from the base branch.
  - Vendor behaviour beyond the stored excerpts and the greps of `claude-code-model-config.md`, `claude-code-sub-agents.md`, `cursor-subagents.md` and `cursor-help-available-models.md`.
- **Not examined:**
  - AS-IS fact lines roughly 420-840 (vendor facts A-78 to A-159), seen only through targeted greps.
  - The proposal document.
  - The tests.
  - The workflow package role and skill texts (the new roles do not exist yet).
  - The uncommitted state of the design files against HEAD, because `git status` could not be re-run.
- **Questions:** Q-34 (extend with F-6's settings). The ledger has no Q-29: ids run Q-28 then Q-30, so 34 entries exist, not 35. This is an observation and not a security finding.

## Responses of the design author (round 1)

The blocking findings were checked against the code before they were accepted: `review_prepare.py:133` and the `diff_patch` port (no filter), `emit.py` `_PLAIN_SAFE` (no `[`), `independence.py` (`fnmatchcase`, case-sensitive). All four are correct.

| Finding | Disposition | Change |
|---|---|---|
| F-1 | Accepted | One normalisation and matching rule (NFKC, casefold, trim, separators alike, a provider prefix and bracketed options dropped); the exclusion matches when the normalised string contains the token `fable` or equals a listed alias; applied to requested, observed, route `name` and `resolves_to`; a variant table in BC-9; an unmatched string means unknown, never equal or different. |
| F-2 | Accepted | `validate review` with a policy present but unloadable returns an error for every record that names a model and never falls back to `model_families`; an absent policy keeps the legacy behaviour and says so. A BC for each case. |
| F-3 | Accepted | Same as the architecture review F-3: `diff.patch` is filtered by a path-exclusion parameter; a sentinel BC; "by construction" removed. The manifest copy carries note paths only, no conclusion. |
| F-4 | Accepted | A family difference needs both identities observed; a requested-only model, or `identity_source: unknown`, is unknown. ADR-007 decision 2 and BC-19 reconciled. |
| F-5 | Accepted | A bounded printable `ModelRef` type, closed enums for `effort` and `kind`, a date type for `retires_on`, model strings echoed only JSON-escaped; renderers use only `front_matter` and `toml_table`. |
| F-6 | Accepted | ADR-004 reworded to "the host can enforce it if configured"; Q-34 extended with stale-approval dismissal and last-pusher approval; EC-7 adds owners for CODEOWNERS itself and the seed path. |
| F-7 | Accepted | "fails closed" replaced by "reports NOT_RUN"; enforcement is procedural plus host review; a CI check is a new open question (Q-36). |
| F-8 | Accepted | The brief says I2 on an unknown identity means a claimed different client; `validate review` emits a closed `identity-unknown` warning and prints such a record as unverified, replacing the free-text rule. |
| F-9 | Accepted | (a) ADR-005 states defence in depth behind the company block; (b) `validate model-policy` compares every `model` value in the generated agent and skill files with the resolution and the exclusion; (c) and (d) are stated as limits. |
| F-10 | Accepted | Tests added to the constraints (every seed `name` and `resolves_to` appears in the evidence file it cites; the Fable exclusion is present in the seed; the seed holds `access: unknown`); entries in the `proposed` state do not feed identity or family derivation; the baseline sentence on page text is carried into ADR-004. |
| F-11 | Accepted | `approval_ref` must cite the data-egress decision for the repository's data class (ADR-002, ADR-004). |
| F-12 | Accepted | ADR-006 records the Codex limit for the PR-text role and tells the role text to treat inputs as data. |
| F-13 | Accepted | Clock handled as in the architecture review F-7; Cursor pins use plain-safe IDs only and an effort assignment for Cursor yields a finding until a client check shows quoted values are read correctly; the credential scan of the integrations loader is applied and `approval_ref` is constrained; the data-flow wording corrected. |
