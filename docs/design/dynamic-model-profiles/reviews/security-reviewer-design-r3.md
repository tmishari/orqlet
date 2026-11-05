# Security Reviewer: design review, round 3

Reviewer: `orqlet-security-reviewer`, a new typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the stored GitHub evidence file and the applicable MUST rules, no earlier review note, and a request for a concise report. Its own self-check says it did not open the earlier round-1 notes.

Design file hashes at start: identical to the list in `architecture-reviewer-design-r3.md` (both round-3 reviewers ran against the same files). The design was revised in response to this round, so the files at save time differ from those hashes.

## Reviewer output (unchanged)

## Security design review: dynamic-model-profiles (D3)

**Verdict: NOT PASS.** There are 2 blocking and 9 non-blocking findings.

Shell commands were unavailable (Ask mode), so `orqlet standards for` and `orqlet validate design` were not run. I used file reads and grep only, with no web lookups, and changed nothing. I did not open the earlier `reviews/*-design-r1.md` notes.

### Blocking

**F-1 — the design contradicts itself on echoing recorded model strings.**
- Evidence, echo allowed: "a model string appears in a finding only JSON-escaped" (`component.md:49`); "model strings echoed only JSON-escaped" (`manifest.yaml:126`); "echoed JSON-escaped" (`data-flow.md:37`).
- Evidence, echo forbidden: "no finding prints a recorded model string" (`component.md:133`, BC-32); "never the recorded string" (BC-19, `component.md:120`); ADR-002, `adr-002:24`.
- JSON-escaping does not neutralise instruction text that agents read.
- Fix: delete the three echo statements and keep "catalog id, or `unmatched` plus length".
- Confidence: high.

**F-2 — BC-14 promises read-only guarantees that the AS-IS does not support.**
- BC-14 says the code reviewer and `orqlet-pr-writer` "render for all three clients as read-only files" (`component.md:115`).
- ADR-006 says "the plan decides whether to render the role for Codex at all" (`adr-006:23`), and its residual-risk text covers Codex only.
- AS-IS: Cursor subagents "inherit all parent tools including MCP tools, and `readonly: true` restricts them to no file edits and no state-changing shell commands" (`as-is.md:648`). Codex subagents "inherit the parent's sandbox, approval, provider and MCP settings" (`as-is.md:573`).
- ADR-007 D9 treats Cursor `readonly: true` as read-only (`adr-007:24`).
- The PR-writer reads an untrusted diff on the cheapest model, so its real reach is wider than the draft text.
- Fix: reword BC-14, state the Cursor MCP reach in the residual risk, and decide render or no-render per client.
- Confidence: high.

### Non-blocking

**F-3 — removing the exclusion is caught only for review records, and one safeguard is overstated.**
- The base/staged union applies only in `validate review` (`component.md:41`, BC-40). `validate model-policy` checks the working file only (`component.md:38`).
- One change can therefore drop the Fable `excluded[]` entry, approve a Fable route, set `manual`, and still PASS `validate model-policy` while `upgrade` renders the pin.
- ADR-005 says "`orqlet upgrade` proposes the shipped Fable entry again" (`adr-005:29`). In code that happens only when the shipped seed hash differs from the lock's hash: `return FileState.SEEDED_PROPOSAL if new != recorded else FileState.SEEDED_KEEP` (`classify.py:78`).
- `base` is a caller-supplied revision (`validate_records.py:79`).
- Fix: have `validate model-policy` compare `excluded[]` with the base tree and error on a removed entry. Say that re-proposal happens per release only.
- Confidence: medium-high.

**F-4 — gaps in the matching rule and agent-file handling.**
- (a) The outcome for an agent-file `model` that fails ModelRef is unspecified. Examples are a Cursor bracketed ID (A-118) or non-ASCII text. Skipping it fails open. The exclusion should run on the raw NFKC string before the type refusal (`adr-005:15`, `adr-003:24`, BC-32).
- (b) There are no parse limits, and no stated outcome for a malformed team-authored front-matter or TOML file.
- (c) BC-9 (`component.md:110`) lists nine Fable variants and no `best` variant, such as `BEST`, ` best `, `best[1m]` or `anthropic/best`.
- (d) The syntax of the `excluded[]` ID pattern is unspecified. A regex read from the file would be a ReDoS risk. The existing matcher is `fnmatchcase` (`independence.py:34`).
- (e) Only "unique ids" is checked (`component.md:38`). Two entries that claim the same normalised `name` or `also_known_as` make the family ambiguous or steerable.
- Confidence: medium.

**F-5 — the record-string alphabet is ambiguous, and the CLI type cannot take display text.**
- ADR-002 says a record "accepts printable ASCII, spaces and `[ ] = ,`" (`adr-002:24`). Those characters are already printable ASCII. Read literally, the rule admits `;`, `$`, backtick and quotes.
- The review skill puts the coder's model string on a command line: `--different-family-from <coder model>` (ADR-007 D11).
- The flag uses ModelRef, which has no space, so Router display text such as "Claude Fable 5.1" cannot be passed.
- Fix: state the exact alphabet, have the skill pass a quoted catalog id, and give the flag the record alphabet.
- Confidence: medium.

**F-6 — recorded strings can still leak through Pydantic messages.**
- `load_contract` forwards `error['msg']` and `loc` (`loading.py:22-27`).
- Existing validators echo input: `f"not a repository-relative glob: {value!r}"` (`common.py:40`).
- `integrations_source._problem` masks only keys of the `_FREE_FORM` maps.
- C-1 should require ModelRef to be `StringConstraints` (pattern and max length) with no custom validator message, and require masking of any map keyed by free text.
- Confidence: medium.

**F-7 — the authorization text is partly overstated.**
- (a) ADR-004 says Q-34 asks "which branch's CODEOWNERS applies" (`adr-004:17`). Q-34's text does not ask that (`questions.yaml:593`).
- (b) Q-32 lists the seed, CODEOWNERS, `domain/**` and `tests/**` (`questions.yaml:563`). `.github/CODEOWNERS` lines 1–10 hold no entry for any `src/**` or `tests/**` path.
- The unowned paths include `src/orqlet/workflow/**` (reviewer prompts, seed, rules), `application/**` (validators) and `adapters/**` (renderers, git).
- The "human code-owner review" named as the fallback (`component.md:11`) therefore covers no source-code change today.
- Extend Q-32 to all of those paths.
- Confidence: high.

**F-8 — the independence summary is overstated, and the binding approval comes from the change itself.**
- The brief says "Independence is derived from recorded, observed identities" (`component.md:11`). The client route to I2 uses two client strings written by one agent, which ADR-007's consequences concede.
- `approved` for the binding is read from the staged tree (`validate_records.py:306-313`, `adr-007:11`). The design closes this self-approval for the policy (`adr-007:25`) but not for `role-bindings.yaml`.
- `identity_source` is optional for architecture and security records (EC-3). A missing value should be stated to mean unknown.
- Confidence: medium.

**F-9 — the absent / deleted / invalid matrix has gaps.**
- Absence record: I grepped the design set for base-absent with staged-present, base-invalid with staged-valid, and `doctor` behaviour. Only `doctor` matched, as the reason it skips seeded files (`adr-003:24`, `adr-005:20`). The matrix covers only deleted and never-present (`component.md:94`, BC-39).
- A repair PR whose base policy is invalid either deadlocks (an error on every model-naming record) or judges the staged tree only, which is a hole.
- First introduction of the policy is undefined, and `doctor` stays silent on a deleted seeded file.
- `models resolve` is "no process" (`component.md:39`, BC-23), yet detecting "present at the base tree" needs git (F-16, `component.md:94`).
- Exit status is ambiguous for `models resolve --different-family-from` with no policy: "Exit 0 … no policy file was ever present" (`component.md:39`) against "exits 1 in every mode" (BC-38, `component.md:139`). That is a fail-open for the skill.
- `upgrade` refusing on an invalid policy also blocks unrelated tool upgrades.
- Confidence: medium.

**F-10 — the review packet can still leak earlier conclusions.**
- `DesignReview.note` is any `RepoPath` (`design_set.py:126-128`). A note stored outside `reviews/**` stays in the snapshot.
- Fix: exclude the paths the manifest names as well. Excluded paths must not appear in `omitted` or `MANIFEST.json`, because they would reveal that earlier rounds exist.
- Unknown: whether `git diff-tree` honours an exclude-magic pathspec (`vcs_git.py:167`). The design does not establish it, and I could not run git.
- The BC-21 sentinel scan (`component.md:122`) must run on the real git adapter, not only on a fake.
- Confidence: low-medium.

**F-11 — the release-recheck wording and the guard tests are weaker than stated.**
- ADR-004 says "enforced mechanically … so a release cannot ship without the recheck" (`adr-004:19`). The same ADR concedes the test proves recording only.
- BC-11 checks `name` and `resolves_to` (`component.md:112`). ADR-004 adds `id` and `family`, and a short `family` appears in any page. The guard tests sit in unowned `tests/**`.
- `trust_boundaries: []` and "no new trust boundary" understate an agent with web access feeding a shipped seed.
- ADR-006 says "enforcement is the skill's procedure" (`adr-006:28`), which breaks C-10's own rule.
- `callable: verified` (`adr-002:19`) and `access: confirmed` are attested labels that no tool checks.
- ORQLET-MODEL-001 is labelled `deterministic`, but unit tests read packaged files and fixtures, not a project's generated files, and the CI workflow runs no orqlet validator.
- Confidence: medium.

### What held up
- ModelRef allows only `[A-Za-z0-9._:/@+-]` for policy names. Pins cannot break out of the YAML or TOML emitters.
- The strict YAML loader bounds nodes and depth and refuses anchors and aliases (`yaml_loader.py`).
- The statements on administrator bypass and author approval match the stored excerpt (items 1, 2, 5, 8). Q-32 to Q-37 are disclosed with their `blocks`.
- The "checked, not enforced" wording is mostly honest (C-10, `adr-005:29`, `manifest.yaml:126`).
- The code citations I opened resolve: `validate.py:38-47`, `classify.py:72-73`, `diagnose.py:82-83`, `independence.py:34`, `evidence_artifacts.py:27`, `review_result.py:34,40`, `vcs.py:113`.

### Self-check
- Every finding carries a quote with file and line, or an absence record.
- No claim without evidence was marked blocking.
- Both blocking findings rest on quotes from at least two files.

### Not examined
- GitHub behaviour, such as which branch's CODEOWNERS applies. Web lookups were not allowed, and the stored excerpt is silent on it.
- Client behaviour (A-108, A-122 and other client facts), which I took from the AS-IS and did not re-verify.
- `ci.yml`, `render/emit.py`, the tests, and the unwritten seed.
- Whether Claude Code slash-command front matter can carry `model`. It is outside the drift scan and unknown to me.
- `.mcp.json`, and the plan-level code.

## Responses of the design author (round 3)

Checked against the code before accepting: `classify.py:78` (a re-proposal only when the shipped seed differs from the lock), `validate_records.py:79, 306-313` (the base is a caller-supplied revision; the binding approval is read from the staged tree), `design_set.py:126-128` (a note path is any `RepoPath`). All findings are accepted.

| Finding | Disposition | Change |
|---|---|---|
| F-1 | Accepted | The three echo statements (`component.md`, `manifest.yaml`, `data-flow.md`) are replaced by "no finding prints a recorded model string". |
| F-2 | Accepted | Decided in the design: the two new roles render for all three clients; BC-14 says "render" and drops the read-only promise; ADR-006 and ADR-007 state the Codex reach and the Cursor MCP reach (a `readonly: true` Cursor subagent still inherits MCP tools, A-122) as residual risks. |
| F-3 | Accepted | `validate model-policy` compares `excluded[]` with the base tree (an optional `--base`, defaulting to the merge base with the protected ref the person names, as `validate review` does) and errors on a removed entry; the re-proposal is said to happen only when a release changes the shipped seed. |
| F-4 | Accepted | An agent-file `model` that fails the type is tested for the exclusion on the raw NFKC string first and reported as `unmatched`, never skipped; a malformed team-authored agent file is a warning and is not scanned further, within a 256 KiB limit per file; BC-9 gains the `best` variants; `excluded[]` patterns are `fnmatch`-style globs, never regular expressions; two entries claiming the same normalised name or `also_known_as` are an error. |
| F-5 | Accepted | The record alphabet is stated exactly (letters, digits, space and `. _ : / @ + - [ ] = ,` only); the flag `--different-family-from` takes a catalog id, and the skill passes the catalog id that the matching rule found, or omits the flag when the coder's model is `unmatched`. |
| F-6 | Accepted | C-1 requires constrained string types with no custom validator message and masking of any map keyed by free text. |
| F-7 | Accepted | Q-34 now asks which branch's CODEOWNERS applies; Q-32 covers every path under `src/orqlet/**` and `tests/**`; the brief says the human fallback covers no source-code change today. |
| F-8 | Accepted | The brief says "recorded, attested identities and client names"; the binding approval is read from the base tree as well, with the closed warning `binding-added-in-this-change` (a warning, not an error, so the change that introduces the role is not deadlocked); a missing `identity_source` means `unknown`. |
| F-9 | Accepted | The matrix is completed: base absent or unloadable with a valid staged policy is judged on the staged tree with no families and the finding `policy-changed-in-this-change`; `models resolve` detects a deleted file from the lock's seeded row, with no git; `models resolve --different-family-from` exits 1 whenever no candidate can be shown different, including with no policy; an invalid policy blocks every `upgrade` until fixed or restored, and the brief says so. |
| F-10 | Accepted | Note paths named by the manifest are excluded too, excluded paths appear in neither `omitted` nor `MANIFEST.json`, the sentinel scan runs on the real git adapter, and the plan must establish that the exclude pathspec works with `diff-tree`, with a post-filter of the patch by file header as the fallback. |
| F-11 | Accepted | "Enforced mechanically" becomes "checked by a test that CI runs"; the guard tests include `id` and `family`; `context.md` records the release-time web reading as a trust path into the seed; "enforcement is the skill's procedure" becomes "checking"; `callable` and `access` are stated as attested labels; MODEL-001's `deterministic` class is explained (unit tests over renderer output and goldens; the project's own files are covered by `validate model-policy`, a manual command until Q-36). |
