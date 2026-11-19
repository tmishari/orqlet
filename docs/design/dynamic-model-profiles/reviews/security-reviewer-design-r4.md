# Security Reviewer: design review, round 4

Reviewer: `orqlet-security-reviewer`, a new typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for`, and an instruction not to read the files under `reviews/`. The reviewer says that one of its searches printed lines from files under `reviews/`; it did not open any of them and used none of those lines.

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

# Security review of the design `dynamic-model-profiles`

**Verdict: NOT PASS.** There is 1 blocking finding, 4 non-blocking findings and 3 observations.

**Limits you should know about:**
- Shell calls were refused in this session, so no `orqlet`, `git` or `sha256` command ran. `quote_sha256` is therefore not computed in any evidence entry, and evidence revisions are not git object ids. The schema wants both, so the entries are not schema-valid until someone runs `orqlet evidence cite`.
- One of my greps used a glob that did not exclude `reviews/`. It printed lines from files under `docs/design/dynamic-model-profiles/reviews/`. I did not open any of those files and used none of those lines as evidence.
- The checkout at `/tmp/p12-amend` is later than the design's base revision `b7b113c`: it already contains the implementation. I checked design claims against it where the cited files looked unchanged (`classify.py:72-73`, `classify.py:78`, `diagnose.py:82-83`, `.github/CODEOWNERS`). I could not read the base revision, so line numbers in other citations are not verified there.

## Findings

```yaml
- schema: orqlet.finding/v1
  id: F-1
  kind: finding
  severity: blocking
  category: security
  confidence: high
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-007-independence-model-identity-and-fresh-context.md, lines: "23", revision: "working tree, not a git oid", quote_sha256: "not computed"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "42, 70, 146", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: src/orqlet/application/contracts/design_set.py, lines: "126-128", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: src/orqlet/application/usecases/validate_design.py, lines: "234-236", revision: "working tree", quote_sha256: "not computed"}
  claim: >
    ADR-007 Decision 8 and BC-45 remove "every path that the design manifest names as a review note" from the
    snapshot, the context copies and `diff.patch`. They also omit those paths from `omitted` and `MANIFEST.json`.
    The text does not say which manifest the paths come from. `DesignReview.note` accepts any repository path.
    `validate design` only checks that the file exists (ORQ-E366). A change can therefore add
    `reviews: [{role, note: src/orqlet/domain/model_identity.py}]` or `.orqlet/model-policy.yaml` to its own
    manifest. That file then disappears from the diff and the snapshot its independent reviewers receive, with
    nothing in the packet to show it. This defeats the independence gate that ADR-006 and ADR-007 build.
    The design also contradicts itself. component.md:42 and :70 call the exclusion "a constant", and ADR-007 and
    BC-45 derive it from the manifest. Nothing says the note strings are matched literally, so a note such as
    `*` could act as pathspec magic.
  suggested_action: >
    Say in ADR-007 Decision 8, BC-45 and the component table that note paths come only from the design manifest
    at the merge base (the approved one) and never from the manifest under review. State that a note never
    removes the manifest, the plan, the standards or the knowledge and test records. State that notes are
    matched as literal canonical paths (`:(exclude,literal)`) and checked against the closed rule, so the
    constant and the derived part are one rule. Add a criterion that a staged edit naming a changed file as a
    note leaves that file in the packet. The checkout's `review_prepare.py` docstring already does this. The
    approved design text does not bind it, and `knowledge/P-11.yaml:28` says this reading is "in no approved
    text".
```

```yaml
- schema: orqlet.finding/v1
  id: F-2
  kind: finding
  severity: non-blocking
  category: security
  confidence: medium
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-003-rendering-model-settings-into-generated-files.md, lines: "24", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "38, 110, 130", revision: "working tree", quote_sha256: "not computed"}
  claim: >
    BC-9 and BC-30 promise an error for "an excluded name in any file". ADR-003 Decision 8 says a team-authored
    agent or skill file "that cannot be parsed, or that exceeds 256 KiB, is reported as a warning and not scanned
    further". A strict loader can reject a file that the client's own parser accepts (for example duplicate keys
    or anchors), and a file can be padded past 256 KiB. In both cases `model: fable` is never tested and the
    result is a warning. The same decision tests a value that fails `ModelRef` only on its raw NFKC string.
    A zero-width character is not removed by NFKC and is not one of the listed separators. This is a closable
    hole. It is not in ADR-005's list of limits Orqlet cannot close, and the rule elsewhere is "fail-safe".
  suggested_action: >
    For a file that is unparseable, oversize or has a non-text `model`, run the exclusion's raw-text test over
    the bounded front-matter or the first N KiB. Report an error on a match, and a warning only when nothing
    matches. Strip Unicode format characters (Cf) before the test. Add a case for each of these to BC-9 and BC-30.
```

```yaml
- schema: orqlet.finding/v1
  id: F-3
  kind: finding
  severity: non-blocking
  category: security
  confidence: high
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/questions.yaml, lines: "557-572 (Q-32), 597-613 (Q-34), 657 (Q-37)", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/manifest.yaml, lines: "134, 171, 199-203", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "27, 160-168", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-004-catalog-governance-and-release-recheck.md, lines: "9, 16, 28, 30", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-005-fable-exclusion-by-model-identity.md, lines: "7", revision: "working tree", quote_sha256: "not computed"}
  claim: >
    The ledger answers Q-32, Q-33, Q-34 and Q-37. Q-34 records a fact: `main` has no branch protection, nothing
    requires a review or a code-owner review, and an administrator can push directly. It concludes that the I3
    fallback "is enforced by nothing". Q-32 records that no second code owner exists and that the person
    accepts this. The design set still treats these as open or conditional. The manifest says approval "the host
    can enforce if configured (Q-34)". ADR-004 says "Q-34 asks" and "the plan has to wait for the answer". The
    brief's section 8 lists Q-32, Q-33, Q-34 and Q-37 as unresolved, and `self_check.questions` lists them too.
    For this repository, the catalog approval rule (R-11), the approval fields and the human fallback in
    R-10 are therefore procedural only. A sole developer is author, sole code owner and sole approver. The
    brief has no failure row and no acceptance criterion for that state. The approver of the design reads
    "may be enforced" where the ledger says "is not".
  suggested_action: >
    Update the security consideration, R-11, section 8, ADR-004 and ADR-005 to the answered state. Add a failure
    row such as "the host enforces no review: a policy edit merges without an independent approver". State
    that the person accepted it (Q-32) and that `approved_by` and `approval_ref` carry no evidence in such a
    repository. Remove the answered questions from the unresolved table.
```

```yaml
- schema: orqlet.finding/v1
  id: F-4
  kind: finding
  severity: non-blocking
  category: security
  confidence: medium
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-005-fable-exclusion-by-model-identity.md, lines: "18, 29", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "38", revision: "working tree", quote_sha256: "not computed"}
    - {kind: absence, searched: ["docs/design/dynamic-model-profiles/design/*.md"], method: "read all ADRs and the brief for a comparison of the team's excluded[] with the shipped seed's, and for the verdict when --base or the protected ref is missing", revision: "working tree"}
  claim: >
    Removal of an exclusion is detected only against a base tree: the `excluded[]` check of
    `validate model-policy` and the union in `validate review`. The merge base of a pull request that removes
    the entry is caught in that pull request. After that change merges, the next base lacks the entry and
    nothing flags it. There is "no built-in exclusion floor" and the CI runs none of these commands.
    Nothing compares the team's `excluded[]` with the shipped seed's, which is data in the package that
    ADR-005 already relies on. The design also does not say what `validate model-policy` reports when `--base`
    or the protected ref is not given. It should not be a silent PASS.
  suggested_action: >
    Add a warning when an entry of the installed seed's `excluded[]` is missing from the team's file. This
    needs no model name in code. State that an unresolvable base is a visible skip, with a NOT_RUN or a named
    skipped check, and never a silent PASS. Add the seed comparison to the alternatives of ADR-005.
```

```yaml
- schema: orqlet.finding/v1
  id: F-5
  kind: finding
  severity: non-blocking
  category: security
  confidence: medium
  evidence:
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/adr-006-code-review-gate-and-new-roles.md, lines: "23, 40-46", revision: "working tree", quote_sha256: "not computed"}
    - {kind: quote, path: docs/design/dynamic-model-profiles/design/component.md, lines: "115", revision: "working tree", quote_sha256: "not computed"}
  claim: >
    `orqlet-pr-writer` reads the diff, which is untrusted content, on the cheapest model. It is rendered for all
    three clients. On Codex its reach is "whatever the parent session may do", and on Cursor it inherits MCP
    tools. The mitigations are a data-only sentence in the role text and the person reviewing actions. The
    sentence is not an enforcement control. The residual risk is stated and handed to the person, which is
    honest. The Rejected alternatives do not weigh the options that cut the exposure: render it only where the
    client enforces a tool allow-list (Claude Code), or have the parent pass the diff summary as text so the
    subagent needs no repository or tool access.
  suggested_action: >
    Compare these alternatives in ADR-006 before the person accepts the risk. If all three clients stay,
    record why the narrower rendering was rejected.
```

```yaml
- schema: orqlet.finding/v1
  id: F-6
  kind: observation
  severity: non-blocking
  category: security
  confidence: low
  evidence: []
  claim: >
    ADR-007 Decision 1 makes `binding-added-in-this-change` a warning, so a change can add the binding that
    approves its own reviewer and still derive I2. The design gives the reason (the change that introduces the
    role would otherwise deadlock). A narrower rule would allow it only for a role that has no binding at the
    base and that the shipped package introduces, and error otherwise.
  suggested_action: Consider the narrower rule, or state in ADR-007 why a warning is enough.

- schema: orqlet.finding/v1
  id: F-7
  kind: observation
  severity: non-blocking
  category: security
  confidence: medium
  evidence: []
  claim: >
    Constraints the plan does not yet carry. (a) ADR-002's type list does not cover `approved_by`, the
    `approval_ref` format, the price fields (shown by `models resolve`, so they reach an agent's context), the
    `excluded[]` glob patterns (they need `*`, which `ModelRef` refuses), or the CLI arguments `--task` and
    `--coder-profile`. (b) C-6 names SEC-003 for SHA-256 only. Tests for the new `sk-`, `xai-` and `AIza` scan
    shapes need credential-shaped fixtures. (c) The manifest's `extractor_config` names no dependency manifest
    or lockfile, so "no new dependency" (BC-25) is checked by hand.
  suggested_action: >
    Add to C-1 that every field printed by `models resolve` is a bounded type. Add to C-6 that key-shaped test
    text is assembled at run time. Add `pyproject.toml` and `uv.lock` to `extractor_config`.

- schema: orqlet.finding/v1
  id: F-8
  kind: observation
  severity: non-blocking
  category: security
  confidence: low
  evidence: []
  claim: >
    ADR-002 drops v1's data-handling fields because Q-6 answered "all four vendors acceptable for this
    repository". Orqlet ships to other repositories. The gate's main route to I2 is a review in another client,
    which sends the code to another vendor. The only control is the approval of each route, and the "approver's
    checklist" (F-18) is not defined in the design.
  suggested_action: >
    Put "which vendor receives this repository's content through this route" on the approver's checklist,
    and say where the checklist is written.
```

## Self-check

| Check | Result |
|---|---|
| Secrets in the design, AS-IS and ledger | Pass. A regex search for common key shapes and private-key headers over the whole task folder found none. |
| Prompt-injection text in `evidence/web/*` | Pass. A search for instruction-shaped phrases gave one hit (`claude-code-sub-agents.md:24`), which quotes vendor documentation and is not an instruction. |
| Digests | Pass. All digests in the design are SHA-256, and no new digest scheme is introduced. |
| Model calls and dependencies | Pass on the text. The design adds no model call, network path or dependency. The dependency claim is not extractor-checked (F-7). |
| Argument and path injection into git | Pass by construction. `check_revision`, `check_ref_name` and `check_exclusions` in the VCS port refuse option-like and magic input, and pathspecs follow `--`. The one design gap is F-1. |
| Rendering injection | Pass. `ModelRef` excludes quotes and newlines, and `emit.py` quotes any value outside its plain-safe set. |
| Untrusted-input handling of the policy | Pass on the text. `integrations_source.py` shows the pattern the design copies: strict loader, 256 KiB limit, scan, no echoed value or key. I did not review the strict loader for alias or anchor limits. |
| Fail-closed on a deleted or unloadable policy | Pass on the text. `classify.py:72-73` and `diagnose.py:82-83` hold as cited. |

**Not examined:**
- The manifest and artifact `sha256` values.
- Citations in the other ADRs at base `b7b113c` (no shell, and the checkout has moved).
- The text of ORQLET-SEC-001 and ORQLET-SEC-002. My standards file lists only NOMODEL-001, QA-001 and SEC-003.
- Whether the strict YAML loader differs from the clients' parsers (the basis of F-2).
- `plan.yaml`, the phase `tests/` and `knowledge/` folders, and `evidence/web/*` beyond the search above.

This is an additional check, not a guarantee. I wrote no files.

## Responses of the design author (round 4)

This round belongs to an amendment of one expected change, EC-7. Checked against the code before answering: `design_set.py:126-128` (a note is any `RepoPath`), `review_prepare.py` and its tests for the notes read at the merge base, and `questions.yaml`.

| Finding | Disposition | Change |
|---|---|---|
| F-1 | Accepted | The same change as architecture F-1: ADR-007 Decision 8, the brief and BC-45 say that the notes are read from the approved manifest at the merge base, that a note never takes out the manifest, the plan or a standards file, that a note that names a context copy drops that copy with no trace, and that a note path is a literal that is excluded only when it is no directory in either tree. The finding also asks that a note never remove the knowledge and test records: the build does not guarantee it (a note that names such a copy still drops it), so the design says what is built and the gap stays a known observation of P-11. |
| F-2 | Deferred | A change of ADR-003 Decision 8 and of the scan in code (a raw-text test for an unparseable or oversize file, and format characters removed before the match). It needs its own design change and its own phase. |
| F-3 | Deferred | As architecture F-3. The README of P-12 says what the ledger holds and claims no enforcement. |
| F-4 | Deferred | A new check (a seed comparison) and a rule for an unresolvable base: a design change and a code change. |
| F-5 | Deferred | A choice among renderings of `orqlet-pr-writer`; the residual risk is already stated in ADR-006 for the person. |
| F-6, F-7, F-8 | Noted | Observations; no change in this amendment. |
