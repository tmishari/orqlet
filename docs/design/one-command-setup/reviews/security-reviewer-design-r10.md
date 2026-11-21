# Security review of the design, round 10

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-21T19:03:06Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the scope and the round 9 notes. This round reviews the revision of ADR-006 decision 2 that answers Q-56 and Q-58.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

At start (2026-11-21T19:03:06Z) the design files had the hashes in the table of `architecture-reviewer-design-r10.md`, which started at the same moment; every artifact hash equalled the one recorded in `design/manifest.yaml`. The design was revised after this round, in response to its blocking finding (Q-59), so the hashes at save differ for `design/manifest.yaml`, `design/adr-006`, `design/component.md` and `questions.yaml`. The reviewed content is not what will merge, and round 11 reviews the revised content.

## Reviewer output (unchanged)

**Verdict: request changes.** There is 1 blocking finding and 4 non-blocking ones.

The revised routine fixes the interpreter problem from Q-56. A `.graphify_python` that a repository commits is never trusted and never run. The skill stops instead of falling back to `python3`, and a relative `PATH` entry can no longer supply the `graphify` that runs.

My round 9 blocking finding is fixed for the cases it named: the routine stops when the `graphify-out` folder is a symbolic link, and it removes `.graphify_python` before writing a new one. But ADR-006 (line 40) and the manifest's security note now say the skill never writes through a link that a repository committed. That is wider than what the routine does, and the same Step 1 block shows why.

**Round 9 findings**
- **F-1, writing through a committed link:** resolved for `.graphify_python` and for the folder. The general claim is still false; see N-1.
- **F-2, no test:** resolved. BC-48 covers every path, the absence of a `python3` fallback, a committed link and a linked folder.
- **F-3, imprecise "graphify on PATH":** resolved. Both paths must be absolute and point to existing programs, and the fallback is gone.
- **F-4, related inputs:** `.graphify_root` is accepted as a residual risk under Q-58 and recorded in ADR-006 Consequences and the manifest. The remote-clone case is only partly resolved; see N-1 and N-3.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 10, role: security-reviewer}
verdict: request-changes
findings:
  - id: N-1
    severity: high
    blocking: true
    rule: ORQLET-SEC-002 (intent); ADR-006 decision 2; manifest considerations.security
    statement: >-
      The link guard covers only graphify-out/.graphify_python and the graphify-out folder itself.
      Every other write under a real graphify-out folder still follows a committed symbolic link.
      ADR-006:40 and manifest.yaml:126 ("nor writes through a committed symbolic link") claim more
      than the routine does.
    evidence:
      - "skill.md:100 (P-2 working copy), in the same Step 1 block as the guarded write:
        open(os.path.abspath('graphify-out/.graphify_root'), 'w'). A committed
        graphify-out/.graphify_root -> ~/.ssh/authorized_keys is overwritten with the scan root on
        the first full build, which is the same pattern as round 9's F-1. Q-58 accepted the redirect
        risk of reading .graphify_root, not the risk of writing through it."
      - "skill.md:122: Path('graphify-out/.graphify_detect.json').write_text(...) follows a link.
        Later steps write graph.json and GRAPH_REPORT.md, whose text comes from repository content."
      - "Quick path for questions: query.md:179 runs `graphify save-result`. upstream ingest.py:345-354
        does memory_dir.mkdir(parents=True, exist_ok=True) and then writes a new
        query_<timestamp>_<uuid>_<slug>.md. A committed graphify-out/memory -> <any folder> puts a
        file with model-written text in a folder the repository chose."
      - "github-and-merge.md:30-35: the graphify CLI writes graphify-out inside the scanned or cloned
        folder, which the remote repository controls."
    impact: >-
      Cloning a repository and running /graphify can overwrite or create files outside the project
      with the person's privileges. The worst case, report text from the repository landing in a
      shell start-up file, is plausible but I have not shown it works end to end.
    required_change: >-
      Choose one. (a) Body only, within the Q-56 scope: before any write, the routine stops when
      graphify-out or any entry under it is a symbolic link (for example `find graphify-out -type l`
      returns anything), in every folder whose graphify-out a later step or the CLI uses, the clone
      under ~/.graphify/repos included. Extend BC-48 with a committed .graphify_root link and a
      memory/ link. (b) Narrow the ADR-006:40 and manifest text to what is guarded, and ask the person
      to accept the rest as a residual risk with a new ledger entry.
  - id: N-2
    severity: low
    blocking: false
    rule: ADR-006 decision 2 (fail closed)
    statement: >-
      "Removes .graphify_python before it writes a new file" does not say what happens when removal
      fails (for example, a committed folder named .graphify_python) or when something is at the path
      again by the time of the write.
    evidence: "ADR-006:40; skill.md:94 writes with open(...,'w'), which follows a link at that moment."
    required_change: >-
      State that the routine stops when the removal fails, and that it creates the file exclusively
      (Python mode 'x' or O_CREAT|O_EXCL), so the write never follows a link.
  - id: N-3
    severity: low
    blocking: false
    rule: ADR-006 decision 2; BC-48
    statement: >-
      "In the folder whose graphify-out the next step uses" is the only text that covers Step 0.
      BC-48 does not test a remote-clone or multi-path run, where graphify-out comes from the remote
      repository.
    evidence: "ADR-006:38; component.md:315; github-and-merge.md:30-35"
    required_change: >-
      Add the Step 0 clone flow to BC-48, or say that the routine runs again after Step 0 resolves
      the local path.
  - id: N-4
    severity: low
    blocking: false
    rule: design manifest self_check; traceability
    statement: >-
      self_check.acceptance_criteria still says "BC-1 to BC-47", so BC-48 is not listed. The plan's
      graphify phase cites only BC-19, so the test that Q-56 requires may not get planned.
    evidence: "manifest.yaml:186; plan.yaml:168,174,183,191,225,2032 (all BC-19)"
    required_change: >-
      Write "BC-1 to BC-48" in the manifest, and raise a plan question so a phase cites BC-48.
  - id: O-1
    severity: info
    blocking: false
    rule: none (observation, does not block)
    statement: >-
      The interpreter check in decision 2 says "absolute path to an existing executable". A long
      shebang (the `#!/bin/sh` trampoline) passes that check. The P-2 draft's import check
      (skill.md:85) makes it fail closed, but the ADR text does not say the interpreter must import
      graphify; BC-48 says only "unusable interpreter line".
    required_change: Optionally add "and imports graphify" to decision 2.
```

**Self-check**
- **What I examined:**
  - ADR-006 in full.
  - BC-19 and BC-48 in `component.md`.
  - The manifest's D-11 entry, security note and self-check (lines 115–202).
  - Q-56 to Q-58 in the ledger.
  - The round 9 notes and the author's responses.
  - The standards output.
- **Citations checked:**
  - The P-2 working copy at `/Users/tmishari/Documents/orqlet/src/orqlet/workflow/skills/graphify/`, which is a working copy and not a commit.
  - `/tmp/upstream/graphify/graphify/ingest.py` and `querylog.py`.
- **Revision:** the files in `/tmp/wt-guard` as they are now.
- **Not run:**
  - The read-only mode refused shell commands, so `git diff` against 17e162c, hash checks and `orqlet validate design` were not run.
  - I did not compare the files with the manifest hashes, or open `as-is.md`, `design-format.md` or `evidence/web/`.
  - I looked for symbolic-link handling only in the earlier review notes and design files that the search found.
- This is an additional check, not a guarantee.

## Author's responses

- N-1: the person chose option (a) (Q-59). Decision 2 now makes the routine stop when `graphify-out` or any entry under it is a symbolic link, in every folder a later step or the `graphify` command uses, the Step 0 clone included. BC-48 covers committed `.graphify_root` and `memory/` links. The manifest's security note states exactly this.
- N-2: decision 2 now says the routine stops when the removal fails and creates the new file exclusively.
- N-3: decision 2 says the routine runs again in every folder a later step uses, the Step 0 clone included, and BC-48 covers the clone flow.
- N-4: the manifest now reads BC-1 to BC-48; the accompanying plan amendment adds a P-2 criterion citing BC-48.
- O-1: decision 2 now requires the interpreter to import `graphify`.
