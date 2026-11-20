# Security Reviewer: design review, round 5

Reviewer: `orqlet-security-reviewer`, a typed subagent in its own context. It received the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` (a file saved outside the repository), a path to a clean checkout of main to check claims against, and an instruction not to open, search or quote any file under `reviews/`. The reviewer says that its first directory listing printed the file names in `reviews/`, with no contents, and that it used none of them; it also says that a credential-shape search printed two false-positive lines from `plan.yaml`, which it did not use.

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

# Security review: design set `dynamic-model-profiles`, design phase, round 5

**Role:** Security Reviewer (`orqlet-security-reviewer`)
**Format:** `orqlet.finding/v1`. I was not given the field list of that schema. I used these fields: `id`, `blocking`, `location`, `evidence`, `risk`, `what would resolve it`.
**Model:** the system prompt says I run on Claude Sonnet 5.5. I cannot verify that from inside the session, so the record carries it as attested and not observed.
**Context freshness:** I started in a clean context. I received only the review request and the input paths it named, and no earlier conversation, memory or reasoning from the author or from earlier rounds.
**Revision examined:** the design folder at `/Users/tmishari/Documents/orqlet-p14-ec7-design`, manifest `base_revision` b7b113c9…. The source tree is a later checkout of main.

## Verdict: NOT PASS

One blocking finding (SEC-1) and five non-blocking findings (SEC-2 to SEC-6). The design set does not meet its own security-surface declaration.

## Scope and handling of the excluded folder

- I read the manifest, `context.md`, `container.md`, `component.md`, `data-flow.md`, `sequence.md`, ADR-001 to ADR-007, `as-is.md` (grep only), `questions.yaml`, the format reference and `/tmp/p14-r5-standards.txt`.
- I also read the source files the design cites, to check its claims:
  - `domain/expected_change.py`, `domain/independence.py` and `domain/globs.py`
  - `application/usecases/expected_change.py`, `gate_status.py`, `binding_inputs.py`, `validate_records.py` and `review_prepare.py`
  - `application/contracts/loading.py` and `design_set.py`
  - `application/ports/vcs.py`, `adapters/git/vcs_git.py`, `interface/cli/commands/validate.py`, `domain/classify.py` and `.github/CODEOWNERS`
- **Excluded folder.** I did not open, search or quote anything under `docs/design/dynamic-model-profiles/reviews/`. My first directory listing (a glob over the task folder) printed the file names of that folder. I did not read their contents and I use none of it. A later credential-shape grep used `!**/reviews/**` and printed no line from that folder.
- **Folder not on the input list.** The same grep printed two false-positive lines from `plan.yaml` (the token `task-override` matched `sk-`). I opened nothing else in that file and did not use those lines.

## Findings

### SEC-1 (blocking): EC-7 does not declare the security paths that the design changes

- **Location:** `manifest.yaml`, `scope.paths`, `extractor_config.security_globs` and EC-7. Also `component.md` section 4.
- **Evidence:**
  - `security_globs` is `.github/CODEOWNERS`, `.orqlet/**` and `src/orqlet/domain/**`.
  - `scope.paths` includes `src/orqlet/domain/**`. The component table says these domain files change: `domain/model_identity.py` (new), `domain/model_resolution.py` (new), `domain/independence.py`, `domain/evidence_artifacts.py` and `domain/binding.py`.
  - EC-7, the only `security` entry, declares only `.github/CODEOWNERS` and six `.orqlet/` files. Its `value` names no `src/orqlet/domain/` path, and it has no `stages`.
  - How the extractor works:
    - `usecases/expected_change.py:85-87` takes every path in the diff from the merge base to the tree under review that matches a security glob.
    - `domain/expected_change.py:216-234` (`_compare_security`) then computes `outside = touched - declared`. Any path outside the declared set gives DEVIATION, whether or not the phase selected EC-7.
    - `gate_status.py:232` maps DEVIATION to ORQ-E450, a blocking code.
  - So any phase pull request that touches a domain file is reported as a deviation, and no expected change describes the domain security change as designed.
  - A second `security` entry would not fix this. Each security entry is compared against all touched paths (`expected_change.py:113-115`). A phase touching paths from both entries would deviate in both.
  - Related: EC-5 and the brief say the role-bindings change reaches existing projects as a pending diff that "a reviewed edit applies". If this repository applies it, it edits `.orqlet/role-bindings.yaml`. That path is on `.orqlet/**` and is not in EC-7. The design does not say whether this repository applies it. That is an unknown.
- **Mitigating facts and unknowns:**
  - The tree I checked already has `CODE_REVIEWER` in `domain/independence.py:25-130`, so some domain phases look merged. I did not read the plan, which is not on the input list, so I cannot see how their gates passed or which phases still touch the domain.
  - The failure is fail-closed (a blocking code, not a silent pass). The problem is that the declared security surface and the design's own scope disagree, and the extractor cannot verify the domain change as designed.
- **Risk:** the check that is meant to prove "only the declared security paths changed" does not describe the domain change. Reviewers, or a person who overrides ORQ-E450, lose the signal that the independence and exclusion-matching code changed outside what was declared.
- **What would resolve it:** one security entry whose `value` is the union of every security-glob path the design changes, or `stages` that give each phase its own set. Then `orqlet validate design`, and a gate-status run on a tree that touches the domain files, should show "implemented as designed". I did not run either command.

### SEC-2 (non-blocking): the design presents answered authorization questions as open, and understates the known host state

- **Location:**
  - `manifest.yaml`, `considerations.security.notes` ("the host can enforce if configured (Q-34)") and the `self_check.unverified` entry on required reviews and on Q-34
  - `component.md` section 8: Q-32, Q-33, Q-34 and Q-37 are listed as unresolved
  - `adr-004` Context bullet 3 ("not readable here") and its last Consequence
- **Evidence:** `questions.yaml` has Q-32, Q-33, Q-34 and Q-37 as answered.
  - Q-34 (answered 2026-11-05T11:36): main has no branch protection and no ruleset. Nothing requires a review or a code-owner review. An administrator can merge directly. The only collaborator is `tmishari`. The human code-owner fallback (I3) is "enforced by nothing". The CODEOWNERS applied is the one on the base branch.
  - Q-32: there is no second owner. Q-23's approval rule "cannot be met" for the author's own changes, and the person accepts that.
  - Only Q-35, Q-36 and Q-38 are open.
- **Risk:** a reader approving the design sees catalog approval, the Fable exclusion's protection and I3 described as conditional on host configuration. The recorded answers say that in this repository none of the three is enforced and the approver and the author can be the same person. The design's conclusions ("checked, not enforced") already hold. The text that states the control is stale.
- **What would resolve it:** state the Q-32 and Q-34 answers in the security consideration and in ADR-004, and take the answered questions out of the "unresolved" table. The author asks the person to confirm nothing further here.

### SEC-3 (non-blocking): the declared security globs omit where much of the security logic lives

- **Location:** `manifest.yaml`, `security_globs`.
- **Evidence:**
  - The globs cover `src/orqlet/domain/**`, `.orqlet/**` and CODEOWNERS only.
  - The design puts security-relevant behaviour in other places:
    - the policy loader and credential scan (`application/usecases`)
    - record validation (`validate_records`)
    - the packet and the git pathspec exclusion (`review_prepare` and `adapters/git`)
    - role texts, the seed that carries the Fable exclusion, and rules (`workflow/**`, `.prompts/**`)
    - generated agent files (`.claude/agents`, `.cursor/agents`, `.codex/agents`)
  - The seed is guarded by CODEOWNERS (ADR-004, Decision 2), and CODEOWNERS on main has an entry for it. The extractor does not watch it.
- **Risk:** a change to those paths gets no ORQ-E450 or ORQ-E451 signal. It relies on human review, which Q-34 says nothing enforces.
- **What would resolve it:** a decision, which is the author's, on whether to widen the globs. Any widening must also appear in SEC-1's union. This is not blocking: the design is D3 already and the risk is detection.

### SEC-4 (non-blocking): the Fable exclusion has no floor, and its three checks are not enforced

- **Location:** ADR-005 Consequences; `component.md` section 3 and constraint C-10.
- **Evidence:**
  - ADR-005 says there is "no built-in exclusion floor". The protection is the union of the base and staged policy, the deletion rule, CODEOWNERS and the seed test.
  - It also says no CI job runs any of the checks, so they are "checked, not enforced" (Q-36 is open).
  - With no branch protection (Q-34), one merged edit that removes the entry from the policy leaves the base without it. Later changes then have nothing to be compared with.
  - ADR-005 states this and says the exclusion is defence in depth behind the company's block (Q-24).
- **Verdict on this point:** accepted residual risk that the design states honestly. No change required. The reader should see it next to SEC-2.

### SEC-5 (non-blocking): CLI inputs other than model strings are not described as confined

- **Location:** `component.md` section 3 (`validate model-policy [PATH]`, `--base`, `--override`, `--different-family-from`).
- **Evidence:**
  - ADR-002 bounds model strings with `ModelRef`, and BC-32 tests the bound.
  - The design does not say that `PATH` is confined to the repository root as a canonical path, or that `--base` is validated before it reaches git.
  - Precedent exists in the tree: `integrations_source.py:78` and `validate_model_policy.py:133` use `CanonicalPath.parse`, and `binding_inputs.py` resolves `--base` through `vcs.resolve`. ORQLET-SEC-001 and ORQLET-SEC-002 require the same.
- **What would resolve it:** one sentence in the brief, or an acceptance criterion.

### SEC-6 (non-blocking): the read-only limits of the two new roles are real and accepted

- **Location:** ADR-006 Decision 8 and ADR-007 Decision 9.
- **Evidence:**
  - Codex cannot enforce read-only for a custom agent file: the subagent inherits the parent's sandbox, approval and MCP settings.
  - A Cursor subagent inherits the parent's MCP tools.
  - `orqlet-pr-writer` reads a diff, which is untrusted, on the cheapest model.
  - The design's controls are a data-only instruction in the role text, the person reviewing the actions, and the limit stated in each record. The residual risk is stated and left for the person to confirm by approving the design.
- **Verdict on this point:** a text instruction is a weak control, and the design says so. No finding beyond SEC-2's point that the person confirms it.

## Checks that found no problem

- **Trust boundaries.** The design adds no network path, process or dependency. I checked `context.md`, `container.md`, BC-23 and BC-25 and ORQLET-NOMODEL-001.
- **Untrusted input.** The policy and the records are read through the `FileSystem` port with strict YAML, a 256 KiB limit, a credential scan and no echoed value. This matches ORQLET-SEC-002 and ORQLET-SEC-003.
  - `loading.py:22-27` forwards validator text but excludes `input`, and the design's constraint C-1 says a validator message must never repeat a value.
  - The `ModelRef` character set has no space, so a pinned name cannot carry an instruction sentence into a generated agent file.
- **Integrity of generated and protected files.** Pins go through `front_matter` and `toml_table` only, with journalled writes (C-5). A pin change moves `protected_set_digest` and shows ORQ-W390 (ADR-003).
- **Review-packet exclusion.** The notes come from the approved manifest at the merge base, as a literal pathspec after `--`, never from the manifest under review.
  - The tree has `check_exclusions` and `:(exclude,literal)` in `vcs_git.py:182-185`, and note paths are constrained by `RepoPath`, a type that rejects non-canonical paths.
  - The design does not spell out `:(exclude,literal)`. The tree does it.
- **Digests.** All SHA-256 (ORQLET-SEC-003). A grep for `md5` and `sha1` in the design folder found nothing.
- **Standards.** The ORQLET-SEC-001, ORQLET-SEC-002, ORQLET-SEC-003 and ORQLET-NOMODEL-001 rules from `/tmp/p14-r5-standards.txt` are named in `standards_applied` and addressed by the design.

## Absence records

| Looked for | Where | How | Result |
|---|---|---|---|
| Secrets, key shapes (`sk-`, `xai-`, `AIza`, `ghp_`, `AKIA`, PEM) and `password=` or `api_key=` text | `docs/design/dynamic-model-profiles/**` except `reviews/**`, at the working tree of the checkout | case-insensitive regex search | None. Two matches in `plan.yaml` were `task-override`, a false positive of `sk-`. |
| `md5` or `sha1` | `design/*.md` | text search | None |
| A new network, process or dependency path | `context.md`, `container.md`, ADR-001 to ADR-007, the manifest | read | None added. Release-time web reading is a person or an agent outside Orqlet (ADR-004). |
| A security-glob path declared in EC-7 that the design does not change | manifest EC-7 against `component.md` section 4 | read | None |
| A domain path that the design changes and EC-7 declares | same | read and extractor logic | Not found (SEC-1) |

## Self-check

- The statements about the extractor come from reading the cited code, not from running it. I did not run `orqlet validate design`, `gate status`, any test or any other check. The Shell tool refused all commands in this session, so I ran nothing.
- I did not run `orqlet standards for`. I used the file I was given.

## What I could not examine

- Whether SEC-1 bites in any remaining phase. That needs the plan (`plan.yaml`), which is not on the input list.
- The recorded SHA-256 values of the artifacts, the AS-IS reference and `protected_set_digest`. I could not compute a digest without a shell.
- Whether the author's scratch-tree run (`self_check`, EC-7) printed what the manifest says. I cannot repeat it.
- The state of the tree at `base_revision` b7b113c. The checkout is a later main, so the cited line numbers in the ADRs (for example `independence.py:57-59`, `validate_records.py:319-320`) no longer match, and the design's statements about "today" are not checkable here.
- The AS-IS facts about vendor behaviour and the evidence files under `evidence/web/`. No web lookup was allowed, and I did not open the evidence files.
- The earlier review rounds (excluded by the instructions).
- The review packet's behaviour with the real git, and the host's actual settings. Q-34 gives the host answer as recorded by the person.

I am an additional check and not a guarantee.

## The author's responses

The request for this round was to amend EC-7 for the six `.orqlet/` files that `orqlet upgrade` writes in P-14 and to change nothing else. No finding below was answered by a design change. Each is listed with the reason, so that the person decides.

- **The amendment itself.** The reviewer's absence record found no declared security-glob path that the design does not change, and no finding concerns one of the six paths or the way they are written. I ran the amended EC-7 against the staged P-14 change before the review (a detached scratch tree with the amendment as its base): `EC-7 security: implemented as designed`, no ORQ-E450; the unamended base gave ORQ-E450 for the same six paths. The reviewer could not repeat that run (it had no shell); the architecture reviewer read the same extractor code and reached the same reading of the value.
- **SEC-1 (blocking), EC-7 does not declare `src/orqlet/domain/**`: accepted as a fact, not changed.** It is true of the approved design before this amendment and the amendment does not change it. The domain files changed in earlier phases (for example P-2, P-3 and P-5, whose test records show ORQ-E451 for those paths), and the P-14 change touches none of them, which the scratch run shows. The reviewer's wish for one entry that lists every path would be a second amendment of EC-7, for phases that are already merged; it is the person's decision. The related point is correct and is new information: applying the pending role-bindings proposal later edits `.orqlet/role-bindings.yaml`, which EC-7 does not list.
- **SEC-2, answered questions shown as open: not changed.** Out of scope for this amendment; the ledger holds the answers.
- **SEC-3, the security globs: not changed.** A decision for the person; this amendment adds no glob.
- **SEC-4 and SEC-6: accepted residual risks** that the design states and the reviewer calls honest. No change.
- **SEC-5, confinement of `PATH` and `--base`: not changed.** The tree already uses `CanonicalPath.parse` and `vcs.resolve`, as the reviewer found; a sentence in the brief is a text change that the request did not ask for.
