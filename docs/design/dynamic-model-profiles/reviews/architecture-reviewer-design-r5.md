# Architecture Reviewer: design review, round 5

Reviewer: `orqlet-arch-reviewer`, a typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` (a file saved outside the repository), a path to a clean checkout of main to check claims against, and an instruction not to open, search or quote any file under `reviews/`. The reviewer says that its first directory listing printed the file names in `reviews/`, with no contents, and that it used none of them.

This round reviews an amendment of one expected change, EC-7: the value now lists `.github/CODEOWNERS` and the six files under `.orqlet/` that `orqlet upgrade` writes in P-14. The reviewer was given no description of the amendment.

Design file hashes at start (computed with `orqlet evidence hash`):

```
design/adr-001-selection-boundary-modes-and-precedence.md a6c1a8eca2bc56f39b873558c10305f16912f7a39f34dfd594603d08732f41df
design/adr-002-model-policy-v2-contract-and-home.md d43e2d78da80f6a55f7ac887291affdde0bddadab6e0f60d1fe07839e4d0a2bd
design/adr-003-rendering-model-settings-into-generated-files.md 6256dc40f78e91c424be27ea260c4de784ac3a6ca36246424e8d0b164bccc72f
design/adr-004-catalog-governance-and-release-recheck.md cac85c2169b30d96348de9cb80e885ba0f3aaea494899432415bbd4e829b031e
design/adr-005-fable-exclusion-by-model-identity.md f91cb911575530b6c71b3465e132b0046aef040c0951fc348d6ab75a51fa939d
design/adr-006-code-review-gate-and-new-roles.md 799953e2d5847e545f854d396ec9498e90b0d81c8ddfc8fdc5ab51c8ccc53c8b
design/adr-007-independence-model-identity-and-fresh-context.md 37216f88e1ef38ad26484c90d2ab0c452e6d858900a526c7a6a3c506b6b0342f
design/component.md 6b40605320c449c1ace532dd764579c89a28ef9933e4cf7d11faac4e2bbcdf81
design/container.md 1b7e42d370471cee37b987efdd6c970cc2211f19efc54b74c285540bd377884f
design/context.md 31e1e40aca33b01023f6532563f8230b134b13210f0f0e8b52fd282103aa57b2
design/data-flow.md 6320ae17d234fd6e7358ced1124d0a7048ee4d2fca14329e0d78a5df36f7a77f
design/sequence.md 2d9bee4638a3e04f71c7e34eacff84428a2b387adcbc5ca9d244683161bae667
design/manifest.yaml 940e1e045b324898a190b185f5430d44e09f9e8d4245d0ad127bd6405f902898
as-is.md 28094d9205c100197f064c7db3f8374e24a743900175ac9ebb7d4b3a598edd83
questions.yaml ee3a4834bb710eaaa2def4c43abc27bbb85e10f47814eb50f080436cb1e4582a
```

Hashes at save time: the same, for every file above. The design files were not changed while the reviewer ran. After the note was saved, the manifest was changed to list the two round-5 notes and to record the round (see the responses below); no other design file was changed.

## Reviewer output (unchanged)

# Architecture review: design set of `dynamic-model-profiles`, design phase, round 5

```yaml
schema: orqlet.review-note/v1        # shape of the note; the finding blocks below use orqlet.finding/v1 field names
role: architecture-reviewer
phase: design
task: dynamic-model-profiles
round: 5
verdict: NOT PASS
blocking_findings: 1                 # F-1
non_blocking_findings: 8             # F-2 to F-9
```

## 0. Review record (ORQLET-MODEL-002)

- **Model that ran:** the system prompt for this session names it Claude Sonnet 5.5. The parent did not state a model. I cannot verify it from inside the session, so treat it as attested and not observed.
- **Context freshness:** I was started in a clean context. I had no earlier conversation. My only inputs were the brief and the paths in it, plus files in the source tree that those files cite.
- **The `reviews/` folder:**
  - I opened, searched and quoted nothing in `docs/design/dynamic-model-profiles/reviews/`.
  - My first, broad directory listing of the task folder printed the file names in that folder, with no contents.
  - Every later search was scoped to `design/`, `src/`, `.prompts/` or `.orqlet/`. No search printed a line from `reviews/`.
- **What I could not run:**
  - Ask mode is read-only and my one shell call was refused.
  - I ran no `orqlet` command, no `git` and no test.
  - I read the extractor source (`src/orqlet/domain/expected_change.py`, `src/orqlet/application/usecases/expected_change.py`, `src/orqlet/application/usecases/gate_status.py`) and reasoned from it.
- **Field names:** the `orqlet.finding/v1` schema file was not among my inputs. I used the usual field names (`id`, `blocking`, `claim`, `evidence`, `impact`, `resolution`), and they may need mapping.

## 1. What I checked

| Area | Result |
|---|---|
| Format: D3 artifact set (context, container, component, data-flow, sequence, real ADRs) | Present. The seven ADRs each have Context, Decision, Consequences and Rejected alternatives. |
| Brief order (`component.md`, parts 1 to 9) | Present and in the required order. Every BC has a source. |
| No phase order in the design | See A-1. |
| Standards | Findings F-6 and F-2. |
| Boundaries (ARCH-001, ARCH-002, ARCH-003) | No defect found. The domain functions take plain values and read no clock. The selection type lives in `ports/instruction_adapter.py`. The client adapters stay unchanged. Git is reached only through the `vcs` port. Clock reads are limited to `validate model-policy` warnings. |
| ORQLET-NOMODEL-001, ORQLET-SEC-003 | The design adds no model call, no network and no dependency. A grep of `design/` for md5, sha1, subprocess, requests and vendor SDK names found nothing relevant. |
| Expected changes | Section 2. |
| Considerations | The three states are `affected`, so the evidence-reference rule for `not-affected` does not apply. The notes match the ADRs, except for F-2. |
| Self-check | F-6 and F-8. |
| Amended text after round 4 (EC-7, ADR-007 Decision 8, brief section 3, section 4 table, BC-45) | I read it in full this round. I found no defect in the mechanism. The remaining points are in F-3, F-5 and A-3. |

## 2. Expected changes, entry by entry

| EC | Surface and verification | Valid per format and `design_set.py` | Can the declared value be checked? | Verdict |
|---|---|---|---|---|
| EC-1 | persisted-schema, manual | Yes. Only `public-api`, `dependency` and `security` have extractors; every other surface must be manual. | By hand. The text names the fields and the absent-file rule. | OK |
| EC-2 | persisted-schema remove, manual | Yes | By hand | OK |
| EC-3 | persisted-schema change, manual | Yes | By hand. The "every existing record stays valid" claim is scoped too widely (F-7). | OK with F-7 |
| EC-4 | persisted-schema change, manual | Yes | By hand | OK |
| EC-5 | persisted-schema change, manual | Yes | By hand | OK |
| EC-6 | public-api add, manual | Yes. `_compare_api` reads Python symbols only, so the command line has no extractor. | By hand against a text that no longer matches the brief (F-5). | OK with F-5 |
| EC-7 | security change, extractor | Yes. The surface is valid and `_compare_security` handles it. | `_PATHS` splits on commas and newlines, and the value is a comma list of seven literal paths, so the extractor can read it. The coverage gap is F-3. The kind `declaration` is accepted; `paths` also exists in `ExpectedAfter.kind` and would fit better. The extractor ignores the kind. | OK for the P-14 paths. F-3 for coverage. |
| EC-8 | public-api change, manual | Yes | By hand | OK |
| EC-9 | persisted-schema add, manual | Yes. Of the six allowed surfaces, generated agent files plus lock rows fit this one best. | By hand | OK |

Surfaces with no entry:
- `http-contract` and `trust-boundary`. The design has no network API (brief section 3) and no new trust boundary (`context.md`).
- `dependency`. This is consistent with "no new dependency", but see F-4.

## 3. Findings

### F-1 — BLOCKING — The meaning of `family` is undecided, and the independence rule and its text depend on it

```yaml
schema: orqlet.finding/v1
id: F-1
role: architecture-reviewer
blocking: true
category: contract / unresolved decision
claim: >
  The independence rule (I2 by "a different known family"), the exclusion by family tag and
  ADR-007's routes to I2 all rest on the field `family`. No design file defines it. The shipped
  seed uses it at vendor level, and ADR-007 describes a route to I2 that only holds at model-line
  level. The open ledger question Q-38 is not a blocking question and the brief does not show it
  to the approver.
evidence:
  - questions.yaml Q-38: "status: open", "blocks: []". The text says the answer "decides whether
    Opus against Sonnet satisfies R-7 and Q-21".
  - src/orqlet/workflow/seeds/orqlet/model-policy.yaml:8,25,42,59 `family: openai`;
    :76,97,118 `family: anthropic` (Opus 5.5, Sonnet 5.5 and Haiku 5.5 share it); :139 google;
    :156 xai; :173 cursor. This is the vendor reading.
  - as-is.md I-1 (line 1173), read in the same way: a pair across families inside Claude Code
    needs a second client.
  - adr-007 Consequences, bullet 2: "the family route to I2 needs a client that reports the model:
    Cursor with the Router displayed, or Claude Code's `/tasks`". Under the vendor reading, Claude
    Code can never give two families inside one client, because its `model` accepts Claude aliases
    only (ADR-007 Consequences bullet 5).
  - component.md BC-17: "one client with two observed different families gives I2". Reachable in
    Cursor only, under the vendor reading.
  - adr-005 Decision 1 uses "the family tag `fable`", which is a model-line tag, not a vendor tag.
  - grep of design/ (excluding manifest.yaml) for "Q-38": no match. Brief section 8 lists Q-32 to
    Q-37 only, and the self-check says "(Q-32 to Q-37)". Only the manifest `questions` list
    contains Q-38.
impact: >
  The same word means two things in the design, and the derived I0 to I2 class is the central
  gate of R-7, R-10 and Q-21. An approver checks a family string without knowing which reading
  applies. The brief (part 8, "unresolved decisions") hides an open consequential question.
  `design-format.md` says a consequential decision the design cannot make is a ledger question
  that blocks design (ORQ-E367 while open). With `blocks: []` the validator cannot report it,
  yet the manifest's own failures list says the earlier blocking finding "stands until the person
  answers".
resolution_options:
  - Ask the person (Q-38), set `blocks` on it (design or plan), add it to section 8 of the brief
    and to `self_check.confirmed_requirements`, and correct ADR-007 Consequences.
  - Or decide the vendor reading as a stated design reading in section 8, which the seed and
    AS-IS I-1 support. Then remove the `/tasks` family route and the "one client with two
    families" case from ADR-007 and BC-17, restate ADR-005's "family tag" as a vendor-level tag
    or drop it, and leave the question open as a non-blocking confirmation.
```

### F-2 — Non-blocking — The brief and the ADRs show answered questions as unresolved

```yaml
id: F-2
blocking: false
claim: >
  Brief section 8 and ADR-004, ADR-005 and ADR-006 treat Q-32, Q-33, Q-34 and Q-37 as open.
  The ledger answers all four.
evidence:
  - component.md lines 164-169 (section 8 table): Q-32 "Blocks plan", Q-33 "plan", Q-34
    "implement", Q-37 "plan". adr-005 line 3 and Consequences: "Q-33 asks the person to
    confirm". adr-004 Consequences: "the plan has to wait for the answer". component.md
    section 8, "Readings": "Q-37, which asks the person".
  - questions.yaml: Q-32 answered, "No second owner ... the person accepts that". Q-33 answered
    "Confirm". Q-37 answered "No" (the design's reading). Q-34 answered: main has no branch
    protection or ruleset, and "the human code-owner review ... (I3) is therefore enforced by
    nothing."
  - manifest.yaml security note: "the host can enforce if configured (Q-34)". adr-004 Decision 1
    says the same, and Consequences says the stored excerpt "does not say whether the
    administrator bypass can be disabled".
impact: >
  The approver is asked to confirm decisions that they have already made. The text understates
  what Q-34 established: on this repository the approval rule of R-11 and the I3 fallback are
  enforced by nothing today. The design's conclusion holds ("checked", not "enforced"), but its
  stated reason is out of date.
resolution: >
  Record the answers in section 8 and the ADRs. List only Q-35, Q-36 and the answer to Q-38 as
  open. Add the Q-34 result to the security consideration.
```

### F-3 — Non-blocking — EC-7 does not cover `src/orqlet/domain/**`, which is a security glob and in the design's scope

```yaml
id: F-3
blocking: false
claim: >
  EC-7 is the only `security` entry, so it is compared against every touched path on the
  security globs. Those globs include `src/orqlet/domain/**`, yet the declared value lists
  CODEOWNERS and six `.orqlet/` files only. Any diff that touches a domain file therefore gets
  DEVIATION (ORQ-E450), whatever phase is claimed.
evidence:
  - manifest.yaml lines 41-44: security_globs are `.github/CODEOWNERS`, `.orqlet/**`,
    `src/orqlet/domain/**`. Line 100 is the EC-7 value.
  - component.md section 4 changes domain files: `model_identity.py`, `model_resolution.py`,
    `independence.py`, `evidence_artifacts.py`, `binding.py`.
  - src/orqlet/domain/expected_change.py:217-233 (`_compare_security`): touched paths outside the
    declared set return DEVIATION. `compare` (:112-114) calls it for every entry whatever
    `selected` holds, and `_additional` (:253) adds nothing once EC-7 exists.
  - src/orqlet/application/usecases/gate_status.py:232,266-268: DEVIATION becomes ORQ-E450, with
    "a renewed design approval is needed".
  - Glob of src/orqlet shows `domain/model_identity.py`, `domain/model_resolution.py` and
    `domain/model_policy_scan.py` already on main. Main's `domain/independence.py` and
    `domain/evidence_artifacts.py:27` carry the new code. An earlier phase therefore touched the
    domain.
impact: >
  For a P-14 diff with no domain file, EC-7 gives "implemented as designed", as the author's
  check says. A gate run over the whole range from the design base, or over any earlier phase,
  would show ORQ-E450. I did not see the P-14 diff. I do not know which EC-7 text governed the
  earlier phases.
resolution: >
  List the domain paths in EC-7, or state in the design that EC-7 is declared for the diff of
  one named change only. Run `orqlet gate status` over the final diff before approval. The same
  applies if the repository applies its own pending `.orqlet/role-bindings.yaml` diff (see
  A-2): that path is on `.orqlet/**` and is not in the EC-7 list.
```

### F-4 — Non-blocking — The "no new dependency" claim is not machine-checked

```yaml
id: F-4
blocking: false
claim: >
  The manifest `extractor_config` sets only `security_globs`. No `dependency_manifests`,
  `lockfiles` or `public_api` is configured.
evidence:
  - manifest.yaml lines 40-44.
  - src/orqlet/application/usecases/expected_change.py:79-87: with no `public_api` the API delta
    is `None`. With no manifests the dependency delta is `None` (:178-179), and with no lockfiles
    the lock delta is `None` (:204-205).
  - The design claims no dependency in component.md C-6 and BC-25 ("the import checks and the
    lockfile show it"), and in the manifest security note.
impact: >
  An added package would not produce ADDITIONAL (ORQ-E451). The statement rests on a person
  checking by hand.
resolution: >
  Configure `dependency_manifests: [pyproject.toml]` and `lockfiles: [uv.lock]`. The extractor
  reads `pyproject.toml` and TOML lockfiles only, so the claim becomes tool-checked. The
  omission of `public_api` is consistent with "no new import-level API" (brief section 3); say
  so in a note.
```

### F-5 — Non-blocking — EC-6's declared value no longer matches the brief

```yaml
id: F-5
blocking: false
claim: >
  EC-6 is compared by hand. Its text differs from section 3 of the brief, which it names as
  its source of truth.
evidence:
  - manifest.yaml EC-6 value: `validate model-policy [PATH]` and `models resolve --client C
    (--role R | --skill S | --profile P) [--task T] [--override MODEL]
    [--different-family-from MODEL] [--json]`.
  - component.md section 3: `validate model-policy [PATH]` with an optional `--base` revision;
    `models resolve ... [--different-family-from CATALOG_ID] [--coder-profile P] [--json]`.
impact: >
  A manual comparison would show a missing option (`--coder-profile`, `--base`) as a deviation
  from the design, or miss it.
resolution: Align the EC-6 value with section 3 (options and argument names).
```

### F-6 — Non-blocking — The standards and acceptance-criteria lists in the manifest are out of date

```yaml
id: F-6
blocking: false
claim: >
  `standards_applied` and `self_check.applicable_standards` omit rules that the supplied output
  of `orqlet standards for` lists. `self_check.acceptance_criteria` stops at BC-42.
evidence:
  - /tmp/p14-r5-standards.txt, manifest path: 4 rules, including ORQLET-MODEL-002
    [docs/design/**]. Domain path: 10 rules, including ORQLET-MODEL-001 [src/orqlet/**,
    tests/**], hash 637331d1...
  - manifest.yaml lines 145-158: neither MODEL-001 nor MODEL-002. Lines 177-181: "src/orqlet/domain/**:
    9 rules, hash 9f47111...". .prompts/rules.yaml:145 and :154 now hold both rules. component.md
    C-10 still calls them "new rules, as the plan writes them".
  - manifest.yaml ~line 188: "BC-1 to BC-42 of ... section 6". The brief has BC-1 to BC-45.
  - The check "Citations of code lines in the ADRs resolve" names three files and says pass; the
    ADRs cite about twenty.
impact: >
  The bound standards and the self-check no longer describe what applies to this design. Stale
  bound values show as ORQ-W390 at merge. The citation check overstates what ran.
resolution: >
  Refresh the standards run, list MODEL-001 and MODEL-002, correct the BC range and narrow the
  citation check to the files that were read. I do not know whether the rebind is meant to
  happen at merge.
```

### F-7 — Non-blocking — "Every existing record stays valid" is verified only for this repository

```yaml
id: F-7
blocking: false
claim: >
  EC-3 and BC-42 narrow `agent.client` and `coder_binding.client` from any string to a closed
  set of three, under an unchanged schema id, and claim that every existing record still validates.
evidence:
  - adr-007 Decision 2 says `review_result.py` accepted any non-empty string, and "the plan
    checks the existing records against the closed set".
  - component.md C-7 and the manifest compatibility note say the same.
  - The brief and manifest give no way to check records held in other repositories. Only this
    repository's 112 records are covered (ADR-006 Context).
impact: >
  A downstream project whose records hold another client string would fail validation after
  `orqlet upgrade`.
resolution: >
  Scope the claim to this repository, or state the downstream effect and its recovery. The
  design already names this as the one narrowing.
```

### F-8 — Non-blocking — The self-check records a failed check and the design will change again

```yaml
id: F-8
blocking: false
claim: >
  The manifest self-check holds `result: fail` for "The design that will merge is the design a
  reviewer read". This round is the review of the whole current text, but fixing F-1 and F-2
  changes the text again.
evidence: manifest.yaml self_check.checks (last entry) and `failures`.
impact: >
  The design as it will merge will not have been read in full unless the same reviewers see the
  final text.
resolution: >
  Keep the edits for F-1 to F-7 small and listed, and either arrange another round or state in
  the manifest that the person accepts reliance on the pull-request review.
```

### F-9 — Non-blocking observation — The design scope does not list `AGENTS.md`

```yaml
id: F-9
blocking: false
claim: >
  The three client adapters write `AGENTS.md` (the docstrings of `claude_code.py:1`, `codex.py:1`
  and `cursor.py:1`), and ADR-003 Consequences says "the version stamps change protected files".
  The design names no path for it.
evidence: manifest.yaml scope.paths (lines 18-39) has no `AGENTS.md`, no rules or commands files
  and no `.mcp.json`. grep of `AGENTS.md` in design/ gives 0 matches.
impact: >
  A change to a file outside scope does not make the design stale. The effect is low.
  I did not run `upgrade`, so I do not know which of these files change.
resolution: Confirm which generated files carry the version stamp and add them to the scope if they change.
```

## 4. Absence records

| ID | What I looked for | Where | How | Result |
|---|---|---|---|---|
| A-1 | A phase list, build order or task list in the design | brief, all seven ADRs, container, data-flow, sequence | Reading every file in full and grepping "P-" and "phase" | None. Orderings are constraints (section 9). The manifest `self_check` names P-12 and P-14 as references to gate runs. That is not an order. |
| A-2 | A statement on whether this repository applies its own pending `role-bindings` diff | brief, ADR-006, EC-5 and EC-7 | Reading | Not found. The `.orqlet__role-bindings.yaml.diff` already exists in `.orqlet/`. If the repository applies it, `.orqlet/role-bindings.yaml` is touched and is not in the EC-7 value. This is a question for the author. |
| A-3 | A statement of how the exclusion pathspec is made literal | ADR-007 Decision 8, brief section 3 and section 4 | Reading, then `src/orqlet/adapters/git/vcs_git.py:170-185,267` | The design says "literal". `vcs_git.py:170-185` uses `:(exclude)` and `:(exclude,literal)`, and its comment at :267 says it was measured with git 2.56.1. The design still lists this as an unknown (ADR-007 Decision 8, manifest `unverified`). I did not verify it. |
| A-4 | A definition of `family` in any design file | design/ | grep "family" and "Q-38" | None (F-1). |
| A-5 | Q-38 in brief section 8 | component.md | grep "Q-3[2-8]" | Absent (F-1). |
| A-6 | MD5, SHA-1, a model SDK, a network library or a subprocess call in the design | design/ | grep | None. |
| A-7 | A new trust boundary or HTTP contract | context.md, container.md | Reading | None declared. I agree with `scope.trust_boundaries: []`. |
| A-8 | ORQLET-MODEL-001 and ORQLET-MODEL-002 in `standards_applied` | manifest.yaml | Reading | Absent (F-6). |

## 5. What I did not examine

- **The AS-IS file:** it is 143 KB and I did not read it in full. I grepped for "family" only. I did not check the A-n, U-n, C-n and I-n citations except those named above.
- **The ledger:** I read it in full.
- **Hashes:** I did not verify any artifact sha256, `protected_set_digest` or `bound` value, and I ran no `orqlet validate design`.
- **Standards:** I only had the output for four paths. I did not check the self-check's counts for contracts, usecases, render, cli, workflow and tests.
- **The plan, tests and knowledge records, the evidence files, and `.github/workflows/ci.yml`:** not read, because the brief did not list them.
- **Source citations in the ADRs:** the design cites base-revision facts, but this tree is main with the implementation merged.
  - For example, `evidence_artifacts.py:27` now holds `code-reviewer`. The design says the pattern admits only the two other roles.
  - I confirmed `validate.py:38-47` (the exit rule is at 40-49), `loading.py:22-27`, `classify.py:72-73` and `diagnose.py:82-83`. I found `emit.py:28` to be at line 26.
  - I could not check the rest against `b7b113c`, because I had no git.
- **Vendor claims:** I did not check any vendor statement about model capability, and I made no external lookup.

## 6. Self-check of this review

- Every finding cites a file in the supplied inputs or the source tree.
- F-1 is the only blocking finding. It is a decision the design cannot make without the person, or one it must state as a reading.
- Each non-blocking finding names a correction.
- I made no edits and wrote no file.
- This is an additional check, not a guarantee.

**Verdict: NOT PASS** (1 blocking finding, F-1; 8 non-blocking).

## The author's responses

The request for this round was to amend EC-7 for the six `.orqlet/` files that `orqlet upgrade` writes in P-14 and to change nothing else. No finding below was answered by a design change. Each is listed with the reason, so that the person decides.

- **The amendment itself.** The reviewer read the new EC-7 value in full: its table says the extractor can read it ("a comma list of seven literal paths") and its verdict is "OK for the P-14 paths". No finding concerns one of the six paths or the way they are written. I also ran the amended EC-7 against the staged P-14 change before the review (a detached scratch tree with the amendment as its base): `EC-7 security: implemented as designed`, no ORQ-E450; the unamended base gave ORQ-E450 for the same six paths.
- **F-1 (blocking), the meaning of `family`: not answered here; open for the person.** It is the round-4 blocking finding, unchanged: the manifest's `failures` entry for round 4 says that it stands until the person answers Q-38, and Q-38 is still open with `blocks: []`. This amendment does not touch ADR-005, ADR-007, BC-17, brief section 8 or the ledger. If the person wants it settled before the design is approved, it is a decision of its own (answer Q-38, set `blocks`, correct the brief and ADR-007).
- **F-2, answered questions shown as unresolved: not changed.** Out of scope for this amendment. The ledger is the authority and holds the answers. The reviewer's reading that the text understates Q-34 is correct.
- **F-3, EC-7 does not list `src/orqlet/domain/**`: accepted as a fact, not changed.** This is true of the approved design before this amendment, and the amendment does not change it. The records of the phases that touched the domain (for example tests/P-2.yaml, P-3.yaml and P-5.yaml) show ORQ-E451 for those paths; they are earlier phases of the same task, and this amendment is declared for the P-14 diff (the scratch run above). The reviewer's second point is also correct and is new information for the person: applying the pending role-bindings proposal later edits `.orqlet/role-bindings.yaml`, a path on `.orqlet/**` that EC-7 does not list; that edit is a reviewed edit after P-14 and would need its own declaration.
- **F-4 to F-7, non-blocking: not changed** (the dependency check, EC-6's text against the brief, the standards and BC lists of the self-check, the scope of "every existing record stays valid"). Each is a correction to text the request did not ask me to change.
- **F-8: accepted.** The manifest now lists this round and records the blocking findings in `failures`; the entry that the design which merges is not the design a reviewer read stays `fail`. The artifacts are those that every earlier round read.
- **F-9, `AGENTS.md` is not in the scope: not changed.** `orqlet upgrade --dry-run` for P-14 listed `AGENTS.md` as a changed file, which supports the observation; the plan lists it as an operation of P-14. The design scope was not changed by this amendment.
