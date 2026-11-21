# Architecture review of the design, round 11

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-21T19:09:37Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the scope and the round 10 notes. This round reviewed the revision of ADR-006 decision 2 that answered Q-56, Q-58 and Q-59.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

At start (2026-11-21T19:09:37Z) the changed design files had the hashes below, and every artifact hash equalled the one recorded in `design/manifest.yaml`. After this round the person moved Graphify and tool preparation out of the task (Q-60), and the design was revised from the approved version on `origin/main`, so the reviewed content is not what will merge. Round 12 reviews the revised content.

| File | sha256 at start |
|---|---|
| design/manifest.yaml | cec42f15fdcae2b1bff65900a7e0ae9ff6921410cdfff055ce96a3cb3b4c8b5c |
| design/adr-002-user-scope-root-journal-and-manifest.md | 4bfa17cdcef0d653f4ef9423cbfdbdb6d9a11fc1de7a4e782be667ebb8aef31b |
| design/adr-006-bundled-skills-and-tool-preparation.md | 71dde1c74e5cc34ebd6482f9d4bbb4a9677b75d8520fef002ed661b6e8b9a847 |
| design/component.md | b9fbf6ca046a2d8dd1f63b91daa6d77007487e6efb032dde66bfbcf0d11016ad |
| questions.yaml | c454589c2969ee2025261778dd3fda634b33fdf20ec135abd0718beb817e3ed9 |

## Reviewer output (unchanged)

**Verdict: request changes.** I found 1 blocking finding and 5 non-blocking ones. The revision resolves all five round 10 architecture findings and all five security findings in the design text. One exception: the plan amendment for BC-48 (r10 F-5) is not in the worktree yet.

**Round 10 findings**

| r10 | Status | Evidence |
|---|---|---|
| Arch F-1 (self-check) | Resolved in text | manifest:180 names Q-56, Q-58 and Q-59. manifest:189 reads BC-1 to BC-48. manifest:197 adds a check, but see blocking finding B-1. |
| Arch F-2 (what counts as a usable first line) | Resolved | ADR-006:39 requires `#!` and one absolute path with no argument. The interpreter must import `graphify`, and the file gets that interpreter's `sys.executable`. BC-48 (component.md:318) tests the `/usr/bin/env` case. K-13 (component.md:369) and manifest:205 record the uv first line as unverified. |
| Arch F-3 (Windows) | Resolved | Q-59 (questions.yaml:1259-1286) is answered POSIX-only. ADR-006:41, ADR-006:74 and component.md:319 state it. See N-3 and N-4 for remaining gaps. |
| Arch F-4 (clone flow, file that cannot be removed) | Resolved | component.md:315 covers the Step 0 clone, and component.md:317 covers a `.graphify_python` that cannot be removed. |
| Arch F-5 (a plan criterion citing BC-48) | Open, outside the design | plan.yaml:2401 still reads "BC-1 to BC-47", and no plan line cites BC-48. |
| Sec N-1 (committed links under `graphify-out`) | Resolved | ADR-006:40 stops on any link under `graphify-out`. The manifest note (line 126) now matches. ADR-006:86 adds the rejected alternative. Every write in the P-2 working copy is under `graphify-out` (checked with grep). |
| Sec N-2 (failed removal, exclusive write) | Resolved | ADR-006:40 stops when removal fails and creates the file exclusively. |
| Sec N-3 (clone flow) | Resolved | ADR-006:38 and component.md:315 |
| Sec N-4 (BC-1 to BC-48) | Resolved in the manifest; plan open | Same as Arch F-5. |
| Sec O-1 (interpreter must import graphify) | Resolved | ADR-006:39 |

Decision 2, Consequences (ADR-006:72-74), Rejected alternatives (ADR-006:83-87), BC-48, K-13, the security note and the self-check agree with each other and with the answers to Q-56, Q-58 and Q-59.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 11, role: architecture-reviewer}
verdict: request-changes
findings:
  - id: B-1
    severity: medium
    blocking: true
    rule: baseline "A check that did not run is reported as not run, never as passed"; design self_check
    statement: >-
      self_check.checks records "design reviews r9 and r10 with their notes; r11 on the content that
      merges" with result: pass (manifest.yaml:197). Round 11 has not finished and its notes do not
      exist yet; the brief says they are written after this reviewer returns. The entry also does not
      name the commands or results of this revision's orqlet validate ledger and orqlet validate design.
    required_change: >-
      Record only checks that have run, each with its result. Either leave r11 out until both
      round 11 notes exist and their verdicts are known, or list it under unverified.
  - id: F-1
    severity: high
    blocking: false
    rule: ORQLET-SEC-002 (intent); ADR-006 decision 2; the answer to Q-56
    statement: >-
      Decision 2 requires the interpreter to "import graphify". In the P-2 working copy the routine does
      this as "$_SHEBANG" -c "import graphify" (skill.md:85). It writes the file with "$PYTHON" -c
      (skill.md:94). Every later step runs $(cat graphify-out/.graphify_python) -c "..."
      (skill.md:112, 175, 205 and on; query.md, update.md). All of these run with the repository root
      as the working folder. In CPython, -c puts the current folder first on sys.path. A repository
      that commits graphify/__init__.py, or a standard-library name that is not loaded at start-up
      such as json.py, gets that code run the first time the person runs /graphify there. That
      includes the import check of the routine that Q-56 added. The repository can then choose the
      code instead of the interpreter, which is the harm Q-56 set out to remove. ADR-006:72 and the
      manifest security note do not mention it.
    evidence:
      - "src/orqlet/workflow/skills/graphify/skill.md:85, :94, :112 (P-2 working copy, not a commit)"
      - "ADR-006:39 (import check), ADR-006:72 (claim that a repository cannot choose the interpreter)"
      - "The CPython sys.path behaviour for -c and -P is from my knowledge; I found no copy of it in the repository"
    impact: >-
      A cloned repository runs code with the person's privileges when they ask /graphify a question
      there.
    required_change: >-
      Under decision 2, start every interpreter call of the skill with -P, or with -I if graphify
      works under it, so the working folder never enters sys.path. That covers the import check, the
      sys.executable write and every later step. graphify needs Python 3.11 or later, where -P exists.
      An older interpreter rejects the option and the skill stops, so it fails closed. Add a BC-48
      case: a committed graphify/__init__.py and json.py at the folder root are never run. Verify the
      behaviour first with a one-line check, for example a folder holding a json.py that prints, then
      python3 -c "import json" inside it. If it is confirmed, treat this finding as blocking.
      If the person considers it outside Q-56, record a new ledger entry.
  - id: F-2
    severity: low
    blocking: false
    rule: ADR-006 decision 2; BC-48 testability (ORQLET-TEST-001)
    statement: >-
      ADR-006:41 and component.md:319 say the skill stops on Windows with a macOS-and-Linux message.
      The design does not say how the skill detects Windows. Under Git Bash or MSYS, command -v returns
      an absolute path to an .exe without a shebang, so the routine would stop with the generic install
      message instead. Under PowerShell, the POSIX block does not run at all, so the message has to
      come from the skill's prose. BC-48's Windows case cannot be tested until this is defined.
    required_change: >-
      State the detection, for example a uname -s match on MINGW*, MSYS* or CYGWIN*, plus a prose
      instruction for shells that are not POSIX. Say how BC-48's Windows case is tested on CI.
  - id: F-3
    severity: low
    blocking: false
    rule: design consistency (ADR-006 decisions 2 and 4; manifest considerations.operations)
    statement: >-
      Decision 4 (ADR-006:50) still runs uv tool install graphifyy==0.9.112 --python 3.12 on every
      platform. On Windows it then downloads a package, its unpinned dependencies and possibly a managed
      Python (TB-2, Q-39) for a skill that always stops (ADR-006:74). Neither the ADR nor component.md
      section 3 says whether this is intended.
    required_change: >-
      State whether install prepares graphify on Windows. If it does not, describe the report, for
      example a line saying graphify is not prepared on Windows (Q-59), and add a BC. If it does, give
      the reason in Consequences.
  - id: F-4
    severity: info
    blocking: false
    rule: phases and approvals (baseline); traceability from BC to plan
    statement: >-
      The author's response to r10 F-5 says a plan amendment accompanies this revision. In /tmp/wt-guard,
      plan.yaml:2401 still reads "BC-1 to BC-47", and nothing cites BC-48.
    required_change: >-
      After the design is approved again, revise the plan so that a P-2 criterion cites BC-48, and get
      the plan approved again.
  - id: O-1
    severity: info
    blocking: false
    rule: none (observation)
    statement: >-
      ADR-006:38 says the routine runs in every folder whose graphify-out the graphify command uses.
      Under Q-58, a committed .graphify_root can point --update at another folder. Whether graphify then
      writes a graphify-out in that folder, and whether the routine runs there first, is not stated.
      I did not check upstream for it.
    required_change: >-
      Optional: say whether the folder named by .graphify_root is one of the folders the routine runs in.
```

**Self-check**
- **What I examined:**
  - ADR-006 and `design/manifest.yaml` in full.
  - BC-48 and K-13, plus the lines of `component.md` about graphify and Windows.
  - Ledger entries Q-56 to Q-59, both round 10 notes with the author's responses, the standards output, and `plan.yaml:2401`.
- **Citations verified:**
  - The P-2 working copy at `/Users/tmishari/Documents/orqlet/src/orqlet/workflow/skills/graphify/` (lines 72-110 of `skill.md`, and every `write_text` or `open(..., 'w')` in the skill and its references). This is a working copy, not a commit.
- **Not done:**
  - The read-only mode refused `git` and `orqlet` commands, so I computed no hashes, did not compare against origin/main 17e162c, and did not run `orqlet validate design` or `orqlet validate ledger`.
  - I did not read `as-is.md` or `design-format.md` in this round.
  - The ORQ-E366 for the r11 notes is expected, as the brief says, and is not counted as a finding.
- **Unverified claims:**
  - The CPython behaviour behind F-1 (`-c` puts the current folder first on `sys.path`, and `-P` turns that off) comes from my knowledge, not from repository evidence. That is why F-1 is not blocking until someone confirms it.
  - The Git Bash behaviour in F-2 is also unverified.
- **Standards:**
  - ARCH-001, ARCH-003, NOMODEL-001 and MODEL-001 are not affected; the revision changes only skill text and design text.
  - DET-002 applies when the snapshot changes.
  - SEC-002 is strengthened, apart from F-1.
- The person still has to approve this revision of the design again.
- This is an additional check, not a guarantee.

## Author's responses

- Every finding of this round concerns the Graphify interpreter routine of ADR-006 decision 2 or the tool preparation of its decision 4. The person moved Graphify and tool preparation to a separate task with a security-first design (Q-60), so the routine, BC-48 and K-13 are not part of the design that merges; the findings carry over to that task's design as evidence. The confirmed `python -c` behaviour (a committed module in the working folder is imported) is recorded in ADR-006's rejected alternative "Bundling Graphify in this task".
