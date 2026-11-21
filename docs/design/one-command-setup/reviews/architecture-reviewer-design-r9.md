# Architecture review of the design, round 9

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-21T19:00:23Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. This round reviews the revision of ADR-006 decision 2 that answers Q-56.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

At start (2026-11-21T19:00:23Z) the design files had the hashes below. Every artifact hash equalled the one recorded in `design/manifest.yaml`. The design was revised after this round, in response to it and to the security review of the same round, so the hashes at save differ for `design/manifest.yaml`, `design/adr-006`, `design/component.md` and `questions.yaml`. The reviewed content is not what will merge, and round 10 reviews the revised content.

| File | sha256 at start |
|---|---|
| design/manifest.yaml | ac6897435881c7f26d8f7ff25748eeeadc263feb8d2fbbc1939552bd86ab7d75 |
| design/adr-001 | c26cc24e7b47d241291da16766650edbda5f7529e3d4c81f94305ab51eac6972 |
| design/adr-002 | 4bfa17cdcef0d653f4ef9423cbfdbdb6d9a11fc1de7a4e782be667ebb8aef31b |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 4325a150a453f18c1602ea2a1f702e0d6bbae376459f8c67fbd32e9bfccf90af |
| design/adr-005 | 9e5c51e9ce4b010dec0647a71ef326fb49369916d1d83583aaa1fb93c789119d |
| design/adr-006 | cd41f345740ff2d64482ba94420292752fca0c785e1cd903957ba49bbcef4656 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| design/component.md | b2467034ecdd0bc2d8434b65ab96b59a3ef1c96688ab4654e561c5c336e7161f |
| design/container.md | 6c56eeeb792bb270f9c1a0ce5ff54e0105ebe92a7be0a7477d43e8a4764f7102 |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/data-flow.md | c2e15000e13b9c79302613897ffde516629019600b97dd4d9bb73b6caaf2d501 |
| design/proposal.md | 8c5869fac7543feebd0c403d0fe7430eca1749ccf7df12bbb0a5bedc3a9c359e |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| questions.yaml | 9e727dfb8f05d9c456402ec39803f4c2403594f39ebe339d40d6f4f8a7e2f26b |

## Reviewer output (unchanged)

**Verdict: approve.** There are 0 blocking and 6 non-blocking findings.

The revised decision 2 does solve the problem Q-56 raises. Each invocation rewrites `graphify-out/.graphify_python` from the `graphify` on `PATH`. A file already in the repository is never trusted, and the skill stops when no `graphify` is on `PATH`. The Consequences and Rejected-alternatives entries agree with that decision, and so does the security note in the manifest.

The citations in Q-56 are correct, but only in the main workspace, where the P-2 work is in progress; they don't resolve in the design worktree:
- `skill.md:58` is the quick path for questions, which skips Step 1.
- `skill.md:731-745` is the guard that rewrites the file only when it is missing.
- `query.md:13-19` runs `$(cat …)` with no guard.

**What I could not check:** the read-only shell refused `git diff`, so I reviewed the current files instead of the diff. For the same reason I did not compute any hashes or run `orqlet validate design`. Every artifact hash other than D-11 in `manifest.yaml` matches the round 8 table, which fits a change to ADR-006 only. I did not open the files in `evidence/web/`. The design was approved before, so the person needs to approve this revision again; checking that approval is outside my role.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 9, role: architecture-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: design-format "The design brief" part 6; ORQLET-TEST-001
    statement: >-
      ADR-006 decision 2 adds a security control, the per-invocation interpreter re-resolution, but
      component.md has no BC for it. BC-19 (component.md:273) checks only the provenance, the model names
      and the absence of the dependency-install and Gemini steps. Q-56's answer says "with a test", and
      the D-3 hash is unchanged, so the brief was not revised.
    required_change: >-
      Extend BC-19, or add a BC with source Q-56 and ADR-006 decision 2. In a repository that commits
      graphify-out/.graphify_python, the quick path for questions and each subcommand (query, path,
      explain, add, --update, --cluster-only) overwrite the file from the graphify on PATH before reading
      it. With no graphify on PATH, the skill stops with the install pointer and runs no python3.
  - id: F-2
    blocking: false
    rule: ADR-006 decision 2 (completeness); design-set consistency with decision 4
    statement: >-
      The decision covers only the case where no graphify is on PATH. It does not say whether the
      python3 fallback stays when graphify is on PATH but its shebang is unusable (skill.md:87, and the
      guard at :740). It also does not say whether Step 1 and the guard share one resolution routine.
      Decision 4 resolves uv and pipx only through absolute PATH elements, and the decision does not
      require the same for the skill's `command -v graphify` or for the shebang path. With a relative
      PATH element, a cloned repository could provide the `graphify` that gets run.
    required_change: >-
      State one resolution routine that Step 1 and the subcommands both use. The resolved graphify and
      its interpreter must be absolute paths, otherwise the skill stops. State whether the python3
      fallback is kept or removed.
  - id: F-3
    blocking: false
    rule: ORQLET-SEC-002 (intent); ADR-006 Consequences
    statement: >-
      "Overwrites graphify-out/.graphify_python" now also happens on the quick path for questions, which
      used to write nothing when the file existed. The upstream write uses Python
      open('graphify-out/.graphify_python','w') after `mkdir -p graphify-out` (skill.md:93-94), and both
      follow symbolic links. A repository that commits graphify-out, or the file itself, as a symbolic
      link gets the write sent to the link's target. The upstream already writes on a full build, so
      the revision makes this happen on more paths. It does not create a new kind of risk.
    required_change: >-
      State that the skill replaces the entry instead of writing through it: refuse when graphify-out or
      the file is a symbolic link, or remove the file and then create it. Name the remaining cost in
      Consequences: a committed file shows as modified after every invocation. Defer to the security
      reviewer on severity.
  - id: F-4
    blocking: false
    rule: ADR-006 decision 2; manifest security consideration
    statement: >-
      graphify-out/.graphify_root is persisted in the same way and read across invocations without Step 1:
      references/update.md:21 and :111, and add-watch.md:44. The skill text calls it "trusted"
      (skill.md:127, add-watch.md:47). A committed copy cannot run code, because the value is quoted or
      read as data. It can redirect --update and watch to another folder, whose content then enters the
      graph and the model context. Q-56 says "the other security observations of the review stay as
      they are", and I cannot tell whether that covers this file.
    required_change: >-
      Either apply the same rule, never trust an existing .graphify_root outside Step 1, or record it as
      a residual risk the person accepted, with a ledger reference. If it is unclear, ask the person.
  - id: F-5
    blocking: false
    rule: design-format "Each ADR compares the real alternatives"
    statement: >-
      Q-56 had three options. ADR-006 rejects "Keeping upstream's reuse", which is not one of them. The
      other two options, "plus quoting, an extraction-prompt guard and removal of the Graphify Cloud
      prompts" and "Leave graphify out of P-2", are not recorded as rejected alternatives with reasons.
    required_change: Add those two options to Rejected alternatives, each with a one-line reason.
  - id: F-6
    blocking: false
    rule: design manifest self_check
    statement: >-
      self_check.questions still lists Q-32 to Q-44, and its confirmed_requirements were not updated. The
      revision answers Q-56, but the self-check does not mention it.
    required_change: Add Q-56 to self_check.questions, and record the checks run for this revision.
```

**Self-check**
- **What I examined:** ADR-006 and `manifest.yaml` in full, the r8 architecture note, Q-55 to Q-57 in the ledger, `design-format.md`, the standards output, and the BC and graphify sections of `component.md`.
- **Revision examined:** the worktree files as they are now; I did not verify the base revision (origin/main 17e162c) with Git.
- **Citations verified:** the graphify skill in the main workspace (`src/orqlet/workflow/skills/graphify/skill.md` and `references/`), which is the working copy, not a commit.
- **Q-57:** a plan question about the README. `README.md` is already in the scope paths, so it has no architectural impact.
- **Standards:** ARCH-001/003, NOMODEL-001, MODEL-001 and DET-002 are not affected by this revision, because it changes only text in a skill snapshot.
- **This is an additional check, not a guarantee.**

## Author's responses

- F-1: added BC-48 to component.md, with source ADR-006 decision 2 and Q-56. It covers the quick path, every subcommand, a committed file that names another program or is a link, and the stop without `python3`.
- F-2: decision 2 now states one routine used by Step 1 and every invocation; the `graphify` and its interpreter must be absolute paths to existing executables, otherwise the skill stops; there is no `python3` fallback.
- F-3: decision 2 now says the routine stops when `graphify-out` is a symbolic link and removes `.graphify_python` before writing; Consequences names the modified committed file.
- F-4: asked the person, who accepted it as a residual risk (Q-58); ADR-006 Consequences and the manifest's security note record it.
- F-5: Rejected alternatives now lists the two other options of Q-56 with reasons.
- F-6: Q-56 and Q-58 are added to `self_check.questions`.
