# Architecture Reviewer: design review, round 4

Reviewer: `orqlet-arch-reviewer`, a new typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for`, and an instruction not to read the files under `reviews/`.

Design file hashes at start (computed with `orqlet evidence hash`; the files were not changed while the reviewer ran):

```
design/adr-001-selection-boundary-modes-and-precedence.md a6c1a8eca2bc56f39b873558c10305f16912f7a39f34dfd594603d08732f41df
design/adr-002-model-policy-v2-contract-and-home.md d43e2d78da80f6a55f7ac887291affdde0bddadab6e0f60d1fe07839e4d0a2bd
design/adr-003-rendering-model-settings-into-generated-files.md 6256dc40f78e91c424be27ea260c4de784ac3a6ca36246424e8d0b164bccc72f
design/adr-004-catalog-governance-and-release-recheck.md cac85c2169b30d96348de9cb80e885ba0f3aaea494899432415bbd4e829b031e
design/adr-005-fable-exclusion-by-model-identity.md f91cb911575530b6c71b3465e132b0046aef040c0951fc348d6ab75a51fa939d
design/adr-006-code-review-gate-and-new-roles.md 799953e2d5847e545f854d396ec9498e90b0d81c8ddfc8fdc5ab51c8ccc53c8b
design/adr-007-independence-model-identity-and-fresh-context.md 0fea8f96cc98823723f6a90d8f5adf1627afa80e6b322229bc4e581e6a3def28
design/component.md f4f9497bb7d335b46e0b796a6029a0a5bf426dbfdd1a90e4d93fe052167fcc67
design/container.md 1b7e42d370471cee37b987efdd6c970cc2211f19efc54b74c285540bd377884f
design/context.md 31e1e40aca33b01023f6532563f8230b134b13210f0f0e8b52fd282103aa57b2
design/data-flow.md 6320ae17d234fd6e7358ced1124d0a7048ee4d2fca14329e0d78a5df36f7a77f
design/sequence.md 2d9bee4638a3e04f71c7e34eacff84428a2b387adcbc5ca9d244683161bae667
design/manifest.yaml 14d387bb7aa653e21129eeb3964ccac511a2aac64125ddb6e34093bcb325cff7
as-is.md 28094d9205c100197f064c7db3f8374e24a743900175ac9ebb7d4b3a598edd83
questions.yaml 7def4a28795896d7ccf6c8228e6e72eb4d79254c0f8f3a7d1c3d73950b738383
```

The design was revised in response to this round, so the files at save time differ from these hashes for the files named in the responses below (ADR-007, the brief and the ledger), and the manifest changed too. The amended text was not reviewed again.

## Reviewer output (unchanged)

# Architecture review of the design `dynamic-model-profiles` (design review, round 4)

**Verdict: NOT PASS.** There are 2 blocking findings (F-1, F-2), 6 non-blocking findings and 2 observations.

The tree at `/tmp/p12-amend` already holds code that implements this design. Examples are `domain/model_resolution.py`, `usecases/validate_model_policy.py` and `independence.py` with `CODE_REVIEWER`. So I could not check the design's "today" citations against base revision `b7b113c` for files the change touched.

I did not read `docs/design/dynamic-model-profiles/reviews/**`. A file-list result from one search showed one path there; I did not open it.

## Findings

I had no shell, so I could not compute `quote_sha256` values or read the git revision. Evidence entries give path, lines and a short excerpt; `orqlet evidence cite` should add the hashes.

```yaml
- schema: orqlet.finding/v1
  id: F-1
  kind: finding
  severity: blocking
  category: architecture
  claim: >-
    The rule that keeps earlier reviews out of the review packet takes its paths from the design
    manifest's review notes. That lets a change hide files from its own reviewers without a trace.
    ADR-007 Decision 8 and BC-45 leave out "every path that the design manifest names as a review
    note". `DesignReview.note` accepts any canonical repository path. The design does not say which
    manifest supplies the notes (the one under review or the approved one at the merge base). It
    does not limit a note to `docs/design/**/reviews/**`. It says excluded paths appear in neither
    `omitted` nor `MANIFEST.json`. A change that edits its own manifest to name a changed source
    file, the plan or a standards file as a "note" would drop that file from the snapshot, the
    context copies and `diff.patch`, and nothing in the packet would show it. The code review gate
    (R-8, R-10) depends on a complete packet.
    The design also contradicts itself. Component §3 (line 42) and §4 (line 70) call the exclusion
    a constant pathspec for `docs/design/**/reviews/**`, but ADR-007 Decision 8 and BC-45 make it
    dynamic. ADR-007 hides excluded paths so earlier rounds are not revealed, yet the same item
    says the manifest copy lists the note paths.
    One mitigation exists. `validate plan` rejects a manifest that changed after the plan cited its
    hash (ORQ-E371). But `review prepare` does not use that check, and CI runs no `orqlet` command
    (A-44).
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-007-independence-model-identity-and-fresh-context.md, lines: "23", quote: "and every path that the design manifest names as a review note (`DesignReview.note` is any repository path ...) ... Excluded paths appear in neither the `omitted` list nor `MANIFEST.json`"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "42", quote: "(a constant pathspec exclusion placed after `--`) ... the design-manifest copy holds note paths"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "70", quote: "the exclusion is a constant held by `review_prepare`"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "146", quote: "BC-45 ... every path the design manifest names as a review note"}
    - {kind: quote, path: src/orqlet/application/contracts/design_set.py, lines: "126-128", quote: "note: RepoPath"}
    - {kind: quote, path: src/orqlet/application/contracts/common.py, lines: "67", quote: "RepoPath = Annotated[str, AfterValidator(_repository_path)]"}
    - {kind: quote, path: src/orqlet/application/usecases/validate_plan.py, lines: "199", quote: "changed after the plan cited it"}
    - {revision: not determined, quote_sha256: not computed}
  suggested_action: >-
    In ADR-007 Decision 8 and BC-45, say that note paths come only from the approved manifest at
    the merge base, never from the manifest under review. Admit only paths under
    `docs/design/<task>/reviews/`. Say that a note can never remove the manifest, the plan or a
    standards file. If a trace is wanted, record only a count of excluded files. Make §3, §4,
    BC-21 and BC-45 say one thing. Add a test in which a note names a changed source file and the
    file stays in the packet.
  confidence: high

- schema: orqlet.finding/v1
  id: F-2
  kind: finding
  severity: blocking
  category: architecture
  claim: >-
    "Family" is never defined, yet the independence class I2 and the reviewer-diversity rule rest
    on it. The design uses it in two incompatible senses.
    AS-IS I-1 treats family as vendor-level: a cross-family pair inside Claude Code or Codex "would
    need a second client or session". ADR-007 line 34 agrees that Claude Code's per-invocation
    model takes Claude aliases only. But ADR-007 line 31 lists "Claude Code's `/tasks`" as a "family
    route to I2". That route can only exist if Opus and Sonnet count as different families.
    ADR-005 also uses "family tag `fable`" for a model line.
    ADR-002 lists `family` as a field and gives no rule for what a family is, or whether two models
    of one vendor may differ in family. The seed's `family` strings come from vendor pages, and
    approvers are told only to check them against the page.
    The meaning decides whether R-7 ("a different family where supported") and Q-21 ("known
    different model family") are met by Opus against Sonnet, or only by a different vendor. The
    ledger has no question on it. The format reference says a consequential decision the design
    cannot make must be a ledger question.
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/as-is.md, lines: "1173", quote: "A cross-family pair inside Claude Code or Codex would need a second client or session."}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-007-independence-model-identity-and-fresh-context.md, lines: "31, 34", quote: "the family route to I2 needs a client that reports the model: Cursor ..., or Claude Code's `/tasks`" / "Claude Code's per-invocation model takes Claude aliases only (A-101)"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-005-fable-exclusion-by-model-identity.md, lines: "14", quote: "and by family tag ... the family tag `fable`"}
    - {kind: absence, searched: ["docs/design/dynamic-model-profiles/design/*.md", "docs/design/dynamic-model-profiles/questions.yaml"], method: "read every file and searched case-insensitively for `family`; 33 hits in the design files, none defines the term (ADR-002 line 19 only lists the field); the ledger has one hit, Q-21's answer (line 394), which uses the term undefined", revision: not determined}
  suggested_action: >-
    Define `family` in ADR-002, including the rule for two models of one vendor. If the design
    cannot decide, raise a ledger question for the person. Then make ADR-007's consequences, the
    `same-family-as-coder` reason and BC-17 follow from it. If family is vendor-level, drop
    Claude Code `/tasks` as a family route. If it is model-line-level, state that Opus and Sonnet
    differ and that this is a weaker reading of R-7.
  confidence: medium

- schema: orqlet.finding/v1
  id: F-3
  kind: finding
  severity: non-blocking
  category: docs
  claim: >-
    The brief, three ADRs and the sequence view treat Q-32, Q-33, Q-34 and Q-37 as open or
    unanswered, but the ledger answers all four. The Q-32 and Q-34 answers also contradict text
    that relies on host enforcement. Q-34 says `main` has no branch protection, nothing requires a
    review or a code-owner review, and tmishari is the only collaborator. Q-32 says there is no
    second owner. Against that:
    - §8 lists all four as unresolved.
    - §1 and ADR-007 item 6 offer "a human code-owner review on the host" as the fallback when no
      reviewer reaches I2.
    - ADR-004 item 1 says "The host can enforce this if it is configured".
    - Sequence S1 shows "merge (approval evidence on the protected branch)".
    - ADR-004 line 28 says "the plan has to wait for the answer".
    - ADR-005 says "Q-33 asks the person to confirm".
    - The design does not say that CODEOWNERS is read from the base branch (Q-34), so the new
      CODEOWNERS entries in EC-7 do not protect the pull request that adds them.
    For this repository the I3 fallback and the approval rule are unenforced, and unattainable
    for the sole collaborator's own changes. The design should say so in the places a reader
    relies on.
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/questions.yaml, lines: "570-575, 591-596, 609-614, 657-662", quote: "status: answered (Q-32, Q-33, Q-34, Q-37); Q-34: \"The human code-owner review that stands in for an AI reviewer (I3) is therefore enforced by nothing.\""}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "11, 164-169, 175", quote: "§1 fallback, §8 table listing Q-32, Q-33, Q-34, Q-37 as unresolved"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-004-catalog-governance-and-release-recheck.md, lines: "16, 28, 30", quote: "The host can enforce this if it is configured to (Q-34)"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/sequence.md, lines: "32", quote: "merge (approval evidence on the protected branch)"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-005-fable-exclusion-by-model-identity.md, lines: "3, 27", quote: "Q-33 asks the person to confirm"}
  suggested_action: >-
    Update §1, §8, ADR-004, ADR-005, ADR-007 item 6 and sequence S1 to the ledger answers. Move
    Q-37's reading and Q-33's reach out of "readings the person confirms". State the consequence
    for this repository, and that the CODEOWNERS file applied to a pull request is the one on its
    base branch.
  confidence: high

- schema: orqlet.finding/v1
  id: F-4
  kind: finding
  severity: non-blocking
  category: docs
  claim: >-
    The manifest disagrees with the brief on the command line it declares. EC-6 omits `--base` of
    `validate model-policy` and `--coder-profile` of `models resolve`, and types
    `--different-family-from` as MODEL where §3 says CATALOG_ID. The self-check lists
    "BC-1 to BC-42", but section 6 runs to BC-45. EC-6 is the reference the implement review
    compares by hand.
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/manifest.yaml, lines: "92, 182", quote: "[--different-family-from MODEL] ... BC-1 to BC-42"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "38, 39, 143-146", quote: "--base ... --different-family-from CATALOG_ID [--coder-profile P] ... BC-43 to BC-45"}
    - {revision: not determined, quote_sha256: not computed}
  suggested_action: Make EC-6 list every option of §3, and update the self-check range.
  confidence: high

- schema: orqlet.finding/v1
  id: F-5
  kind: finding
  severity: non-blocking
  category: architecture
  claim: >-
    The precedence order the person is asked to approve (ADR-001 Decision 4) has four levels. It
    does not say how overlapping assignments resolve. ADR-002 lets an assignment carry an optional
    `client` and an optional `task`. Not defined are: a client-less assignment against a
    client-specific one for the same role, two assignments for the same target, client and task,
    and where a task-scoped team assignment sits among levels 1 to 3 (Decision 7 says only that
    it is a resolve-time selector). The `validate model-policy` checks list "unique ids" only.
  evidence:
    - {kind: absence, searched: ["docs/design/dynamic-model-profiles/design/*.md"], method: "read ADR-001 and ADR-002 and searched for duplicate, overlap, specificity and two assignments; no rule found", revision: not determined}
  suggested_action: >-
    Add a specificity rule and a duplicate check to ADR-001 Decision 4 and the checks of §3, with
    a fixture in BC-5.
  confidence: medium

- schema: orqlet.finding/v1
  id: F-6
  kind: finding
  severity: non-blocking
  category: docs
  claim: >-
    R-2 (three starting profiles with starting candidates) is cited by no acceptance criterion.
    R-14 and R-15 are also cited by none. BC-11 only says every seed entry is `proposed`; nothing
    checks that the seed holds the three profiles and the ADR-002 candidate table.
  evidence:
    - {kind: absence, searched: ["docs/design/dynamic-model-profiles/design/component.md"], method: "searched section 6 for R-2, R-14 and R-15 in the source column; they appear only in section 2 (lines 18, 30, 31)", revision: not determined}
  suggested_action: >-
    Add a criterion for the seed's three profiles and starting candidates. State that R-14 and
    R-15 have no criterion by design.
  confidence: high

- schema: orqlet.finding/v1
  id: F-7
  kind: finding
  severity: non-blocking
  category: standards
  rule_ref: ORQLET-SEC-003
  claim: >-
    BC-32 requires tests that the credential scan flags `sk-`, `xai-` and `AIza` key shapes. Those
    tests need key-shaped strings. SEC-003 says never commit secrets in tests and fixtures and use
    obvious placeholders. The constraints do not say the fixtures must use obvious placeholders.
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "133", quote: "the credential scan flags the integrations shapes and `sk-`, `xai-` and `AIza` keys"}
    - {kind: absence, searched: ["docs/design/dynamic-model-profiles/design/*.md"], method: "searched case-insensitively for `placeholder`; no hit", revision: not determined}
  suggested_action: >-
    Add a constraint that key-shaped test inputs are visibly fake, for example a repeated
    `EXAMPLE` body.
  confidence: high

- schema: orqlet.finding/v1
  id: F-8
  kind: finding
  severity: non-blocking
  category: architecture
  claim: >-
    The manifest scope narrows the AS-IS scope and leaves out generated paths the design says will
    change. The AS-IS scope covers `.claude/**`, `.cursor/**`, `.codex/**`, `.agents/**` and
    `AGENTS.md`. The manifest lists only the `agents/` and `skills/` subfolders. ADR-003 says the
    version stamps change protected files for every project. `AGENTS.md` carries `workflow@0.4.0`
    stamps on lines 1 and 77, and the repository's `.claude/rules`, `.cursor/rules`,
    `.claude/commands` and `.cursor/commands` are generated. If the new MODEL rules carry
    `scope.paths`, the renderer writes them as new scoped rule files. C-10 does not say whether
    they do. `validate plan` does not check plan paths against the manifest scope, so this is a
    scope-statement gap and not a blocked build.
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/as-is.md, lines: "15", quote: "\"AGENTS.md\", \"README.md\", \".github/workflows/**\", \".claude/**\", \".cursor/**\", \".codex/**\", \".agents/**\""}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/manifest.yaml, lines: "17-39", quote: "scope.paths: .claude/agents/**, .cursor/agents/**, .codex/agents/**, .claude/skills/**, .agents/skills/**"}
    - {kind: quote, path: AGENTS.md, lines: "1, 77", quote: "orqlet:begin baseline workflow@0.4.0#..."}
    - {kind: quote, path: src/orqlet/application/usecases/render_request.py, lines: "100-106", quote: "if rule.level is not Level.MUST or not rule.scope.paths: continue"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-003-rendering-model-settings-into-generated-files.md, lines: "30", quote: "the version stamps change protected files and the digest for every project"}
    - {revision: not determined, quote_sha256: not computed}
  suggested_action: >-
    Add `AGENTS.md`, `.claude/CLAUDE.md`, and the `rules` and `commands` folders of `.claude` and
    `.cursor` to the scope, or say why they are out. Say whether the MODEL rules carry
    `scope.paths`.
  confidence: medium

- schema: orqlet.finding/v1
  id: F-9
  kind: observation
  severity: info
  category: failure-handling
  claim: >-
    F-16 says "a deletion is a reviewed change", but `validate model-policy` reports a deletion as
    FAIL and `upgrade` refuses on it. The deletion rule fires from the base tree or from the
    lock's seeded row. No route is stated for a team that deliberately removes the policy and
    returns to the "never present" state.
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "94", quote: "Restore the file from git; a deletion is a reviewed change"}
  suggested_action: >-
    State the intended opt-out, for example `orqlet release` of the seeded file. Otherwise reword
    F-16.
  confidence: low

- schema: orqlet.finding/v1
  id: F-10
  kind: observation
  severity: info
  category: architecture
  claim: >-
    The design does not say whether the gate it introduces applies to its own implementation. By
    EC-4, a plan whose header `workflow_version` is below the shipping version keeps exactly the
    three review roles. The plan for this change will be written before the role ships, so its
    phases cannot list `code-reviewer`. The design does not say whether the code reviewer runs
    voluntarily on them.
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/manifest.yaml, lines: "70-77", quote: "keeps today's exact set otherwise"}
  suggested_action: Say how the gate treats this task's own phases.
  confidence: low
```

## Self-check

```yaml
schema: orqlet.self-check/v1
checked_against: {role: architecture-reviewer, phase: design}
checks:
  - {what: "Design set against the format reference: D3 artifacts, brief parts 1 to 9 in order, ADR sections, reviewer notes, no phase list, build order or task list", how: "read the manifest, all seven ADRs and the four views; searched for ordering text", result: pass}
  - {what: "The three standards that apply to the paths I received", how: "read /tmp/p12-design-standards-arch.txt. NOMODEL-001 holds (BC-23, BC-25, no model call, no agent start). QA-001: no CI change is planned. SEC-003: SHA-256 only (C-6)", result: "pass, except the placeholder gap F-7"}
  - {what: "Layering and constraints against the import-linter contracts", how: "pyproject.toml lines 82-126 read against C-1, C-11 and the component and container views; all agree with them", result: pass}
  - {what: "Exit statuses against the exit-code enum", how: "interface/cli/exit_codes.py and validate.py (output_of) read against §3 and BC-33", result: pass}
  - {what: "Code citations that resolve", how: "opened emit.py, loading.py, classify.py (seeded rule), diagnose.py, release.py, cursor.py, changeplan.py, design_set.py, .github/CODEOWNERS, validate.py; also checked that compose has three callers (upgrade, init, explain). All of these match the design", result: pass}
  - {what: "Design against the answered ledger", how: "read questions.yaml in full", result: "fail, F-3"}
  - {what: "Design against the AS-IS", how: "read A-1 to A-159 and I-1 to I-11 as cited; A-n and I-n ids resolve", result: "fail, F-2 (I-1 against ADR-007)"}
unexamined:
  - "Citations to lines the change itself modified (independence.py, validate_records.py, plan.py, review_prepare.py, instruction_adapter.py, vcs port and adapter). The tree holds the implementation, and I could not read the git revision or history, so I could not check them at b7b113c."
  - "sha256 values in the manifest and the as_is_ref, and quote hashes for my own evidence: no shell."
  - "Vendor facts and model names beyond a count of their appearance in the evidence files: no web access and no model evaluation. The EC-7 extractor and `orqlet validate design` were not run."
  - "Whether `git diff-tree` honours an exclude pathspec (ADR-007 Decision 8): the design lists it as an unknown and I did not run it."
  - "The reviews folder, by instruction."
  - "Security-reviewer territory, such as the credential scan and the pin-to-Fable paths. I looked at it only where it touched architecture."
```

## Responses of the design author (round 4)

This round belongs to an amendment of one expected change, EC-7. The reviewers read the whole design, as the skill asks, and their findings are mostly about text that the person approved with the last round still NOT PASS. Checked against the code and the ledger before answering: `review_prepare.py` (its docstring and the notes read at the merge base), `tests/unit/application/test_review_prepare.py` (`test_a_note_that_only_the_staged_manifest_names_stays_in_the_packet`), `tests/integration/test_review_packet_real_git.py:385`, `validate_ledger.py` (`question_key`), `independence.py` and `questions.yaml` (Q-32 to Q-37).

| Finding | Disposition | Change |
|---|---|---|
| F-1 | Accepted, in part | ADR-007 Decision 8, the brief (section 3 and the section 4 table) and BC-45 now say what the build does and what the reviewer asks for: the note paths come from the approved manifest at the merge base and never from the manifest of the tree under review, a note never takes out the manifest, the plan or a standards file, a note path is a literal and not a pattern, and a staged edit that names a changed file as a note leaves it in the packet (a test exists). Not accepted: limiting notes to `docs/design/<task>/reviews/` (the approved manifest is the person's own approval, and the build does not limit them) and recording a count of excluded files (decision 8 gives the reason for no trace). BC-21 is left as it is: it describes the constant part only. |
| F-2 | Accepted as a question | The design cannot decide what a family is. It is a new ledger question, Q-38, with category policy, that blocks nothing: the built code takes the family string of the policy as given. No design text changes. The blocking finding stands until the person answers Q-38. |
| F-3 | Deferred | The answers of Q-32 to Q-34 and Q-37 are in the ledger, and the README of P-12 states what Q-34 holds. Updating the brief, three ADRs and the sequence view is a larger text change than this amendment and needs its own. |
| F-4 | Deferred | EC-6 and the BC range are text of the same kind; not part of this amendment. |
| F-5 | Deferred | A design decision (specificity and duplicates among assignments); it needs its own design change. |
| F-6 | Deferred | A missing acceptance criterion; not part of this amendment. |
| F-7 | Deferred | A constraint to add to the design; not part of this amendment. |
| F-8 | Deferred | A scope statement; `validate plan` does not check it. Not part of this amendment. |
| F-9, F-10 | Noted | Observations; no change. |
