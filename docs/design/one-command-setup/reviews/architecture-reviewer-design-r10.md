# Architecture review of the design, round 10

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-21T19:03:06Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the scope and the round 9 notes. This round reviews the revision of ADR-006 decision 2 that answers Q-56 and Q-58.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

At start (2026-11-21T19:03:06Z) the changed design files had the hashes below; every other artifact hash equalled round 9's, and each equalled the one recorded in `design/manifest.yaml`. The design was revised after this round, in response to it and to the security review of the same round (Q-59), so the hashes at save differ for these four files. The reviewed content is not what will merge, and round 11 reviews the revised content.

| File | sha256 at start |
|---|---|
| design/manifest.yaml | d1f764c3e1b70a0c86cb92b5dfad1b273d6d2070481254cd55987a725e06a71d |
| design/adr-006 | 7a28fc09310def54facbec3e54bf86a65f3574c4a398cbc18759ffd197fa60ec |
| design/component.md | 8a03715b1dedc4a1b17923399d3a055613ea7fd0f10d3e3f3f3a4d1dd11aebb4 |
| questions.yaml | d4aaf46f701caa908899e96bc4cb0ddeea041d22b6ababd33b2b1854a451dd51 |

## Reviewer output (unchanged)

**Verdict: approve.** I found 0 blocking and 5 non-blocking findings. Five of the six round 9 findings are fully resolved. The sixth, the self-check update, is only partly done.

**Round 9 findings**

| r9 | Status | Evidence |
|---|---|---|
| F-1 (no test for the new routine) | Resolved | BC-48 at `component.md:315` covers Step 1, the quick path and every subcommand. It also covers a committed program or link, no `graphify`, a non-absolute `graphify`, an unusable interpreter line, no `python3`, and `graphify-out` as a link. |
| F-2 (one routine, absolute paths, fallback) | Resolved | ADR-006:38-39 defines one routine. The `graphify` and its interpreter must be absolute paths to existing executables. There is no `python3` fallback. |
| F-3 (writes follow links) | Resolved | ADR-006:40 makes the routine stop when `graphify-out` is a link and remove the file before writing. ADR-006:71 names the cost: a committed file shows as modified after every run. |
| F-4 (`.graphify_root`) | Resolved | Q-58 (`questions.yaml:1233-1258`) is answered "accept as residual risk". ADR-006:72 and the manifest's security note record it. |
| F-5 (rejected alternatives) | Resolved | ADR-006:82-83 adds both missing options of Q-56, each with a reason. |
| F-6 (self-check) | Partly resolved | Q-56 and Q-58 are now in `self_check.questions` (manifest:202). See F-1 below for what is still missing. |

The rest of the revision is consistent. The ADR's Decision, Consequences and Rejected alternatives agree with each other, with BC-48, with the manifest's security note, and with the answers to Q-56 and Q-58. Decision 2 is stricter than Q-56's wording, which only said to stop when `graphify` is missing from `PATH`. It also stops when the path is not absolute or the interpreter line is unusable. That is the change round 9 asked for and the author recorded it, but F-3 below asks the person to confirm it.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 10, role: architecture-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: design manifest self_check (r9 F-6 required change)
    statement: >-
      self_check.acceptance_criteria still reads "BC-1 to BC-47" (manifest.yaml:187), but BC-48 now
      exists (component.md:315). confirmed_requirements still says "Q-32 to Q-44 were asked and
      answered in this design session" (manifest.yaml:178). checks (manifest.yaml:193-196) records no
      check for this revision, such as orqlet validate ledger after adding Q-58 or orqlet validate design.
    required_change: >-
      Change the range to BC-1 to BC-48. Mention Q-56 and Q-58 in confirmed_requirements. Record the
      checks run for this revision, with their results, or list them as unverified.
  - id: F-2
    blocking: false
    rule: ADR-006 decision 2 (completeness); BC-48 testability
    statement: >-
      Decision 2 requires "the interpreter on its first line" to be an absolute path to an existing
      executable, and BC-48 tests "an unusable interpreter line". Neither defines a usable line.
      A shebang of "#!/usr/bin/env python3" passes the rule as written, because /usr/bin/env is
      absolute and exists, but /usr/bin/env is not a Python interpreter. I recall, without having
      verified it, that installers in the distlib and uv family write a "#!/bin/sh" exec trampoline
      when the interpreter path holds spaces or is very long; /bin/sh would pass the same way. The
      draft at skill.md:94 also writes sys.executable taken from the resolved Python, which is not
      the first-line path. The decision does not say which value goes into the file.
    required_change: >-
      Define a usable line: "#!" followed by a single absolute path with no arguments. State that the
      file receives the sys.executable that this interpreter reports after it imports graphify.
      Say whether an env or /bin/sh shebang stops the skill. Add the env shebang case to BC-48.
      Record the uv shebang format at the pinned version as an unknown for the plan to verify.
  - id: F-3
    blocking: false
    rule: ADR-006 decision 2; design-set consistency (Windows is in CI, as-is.md:651; Q-41)
    statement: >-
      Decision 2 assumes a POSIX shell (`command -v`) and a text entry point with a shebang. On
      Windows, the uv-installed graphify entry point is, I expect, an .exe launcher with no text
      first line. The routine would then always stop, and the design does not say whether the
      graphify skill is supported on Windows. Upstream has a separate skill-windows.md (PowerShell,
      with the same .graphify_python reuse at its line 787), and the P-2 draft does not deliver it.
    required_change: >-
      State the Windows behaviour of the bundled graphify skill: unsupported, with the stop message
      saying so, or a Windows routine under the same rule. If it is not settled, ask the person and
      record the question in the ledger.
  - id: F-4
    blocking: false
    rule: ORQLET-TEST-001; ADR-006 decision 2
    statement: >-
      Decision 2 also requires the rewrite to happen "in the folder whose graphify-out the next step
      uses". The author's answer to security r9 F-4 relies on this for a pipeline run inside a remote
      clone. BC-48 does not test that case. BC-48 also does not cover a committed .graphify_python
      that is a directory or cannot be removed, where the routine should stop.
    required_change: >-
      Add both cases to BC-48: the clone or other-folder case, and a .graphify_python that cannot be
      removed, which makes the skill stop.
  - id: F-5
    blocking: false
    rule: phases and approvals (baseline); traceability BC to plan
    statement: >-
      The approved plan states that every BC from BC-1 to BC-47 is the source of an acceptance
      criterion (plan.yaml:2401). No acceptance criterion cites BC-48. Graphify's P-2 criteria cite
      only BC-19 (plan.yaml:159-233).
    required_change: >-
      After the design is approved again, revise the plan so that a P-2 criterion cites BC-48 and
      the coverage statement includes it, then get the plan approved again. This is outside the
      design artifacts and is listed here so it is not lost.
```

**Self-check**
- **What I examined:**
  - `design/manifest.yaml` and ADR-006 in full.
  - BC-19 and BC-45 to BC-48, plus the section 3 rows about graphify in `component.md`.
  - Q-56 to Q-58 in the ledger, both round 9 notes, and the standards output.
- **Citations verified:**
  - Graphify's P-2 coverage in `plan.yaml`.
  - Upstream `/tmp/upstream/graphify/graphify/skill-windows.md` (lines 95-130 and 787-801).
  - The P-2 draft in the main workspace (`skill.md:94`, `:745`). This is a working copy, not a commit.
- **Not done:** the read-only shell refused `git` and `orqlet` commands. I computed no hashes, did not compare against origin/main 17e162c, and did not run `orqlet validate design` or `orqlet validate ledger`. The new D-3 and D-11 hashes in the manifest are unverified. The ORQ-E366 for the r10 notes is expected and not counted as a finding.
- **Unverified claims:** the claims about uv's shebang format and the Windows `.exe` launcher in F-2 and F-3 come from memory, not from repository evidence. Treat them as questions to settle, not facts.
- **Standards:** ARCH-001, ARCH-003, NOMODEL-001, MODEL-001 and DET-002 are not affected, because the revision changes only the skill snapshot's text. SEC-002 is strengthened.
- **Approval:** the person still has to approve this revision of the design again.
- This is an additional check, not a guarantee.

## Author's responses

- F-1: `self_check.acceptance_criteria` now reads BC-1 to BC-48; `confirmed_requirements` names Q-56, Q-58 and Q-59; `checks` records this revision's validations and review rounds.
- F-2: decision 2 now defines a usable first line (`#!` and one absolute path to an existing executable, no argument), requires that interpreter to import `graphify`, and writes the `sys.executable` it reports. BC-48 covers `#!/usr/bin/env python3`. Constraint K-13 makes the plan cite uv's entry-point first line at the pinned version, and the manifest lists it as unverified.
- F-3: asked the person (Q-59): the bundled graphify skill is POSIX-only for now and stops on Windows with a message that says so; decision 2, Consequences and BC-48 state it.
- F-4: BC-48 now covers the Step 0 clone flow and a `.graphify_python` that cannot be removed.
- F-5: the plan amendment that accompanies this design revision adds a P-2 criterion citing BC-48 and extends the coverage statement.
