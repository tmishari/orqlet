# Security review of the design, round 11

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-21T19:09:37Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the scope and the round 10 notes. This round reviewed the revision of ADR-006 decision 2 that answered Q-56, Q-58 and Q-59.

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

**Verdict: request changes.** I found 1 blocking finding (medium) and 5 non-blocking ones.

The revised routine resolves my round 10 blocking finding N-1 in the way the person chose under Q-59. It also closes the risk that Q-56 is about: a cloned repository can no longer choose the interpreter the skill runs.

It does not yet support the security claim made in ADR-006 line 40 and in `manifest.yaml` line 126. That claim says no write of the skill or of the `graphify` command it starts follows a link that a repository committed. Upstream graphify also writes into a `graphify-out` folder inside the scanned folder and inside the folder being watched. Two cases fall outside the guard:
- a committed link above `graphify-out`, for example a subfolder that is itself a link;
- a `--watch` process that is still running when a later `git pull` adds a link.

The link at `.graphify_root` that Q-58 accepted also points those writes outside the project, and Q-58 never mentions writes.

## Round 10 findings

| r10 | Status | Evidence |
|---|---|---|
| N-1, links under `graphify-out` | Resolved as specified | ADR-006:40 stops on `graphify-out` or any entry under it. ADR-006:38 applies this in every folder that is used, the Step 0 clone included. BC-48 (`component.md`:317) covers `.graphify_python`, `.graphify_root` and `memory/`. Ancestor links and the watcher are new cases; see S-1 and S-2. |
| N-2, removal fails, exclusive write | Resolved | ADR-006:40: the routine stops when the removal fails and creates the file exclusively. BC-48:317 covers a `.graphify_python` that cannot be removed. |
| N-3, the clone flow | Resolved | ADR-006:38 and BC-48:315 name the Step 0 clone flow. |
| N-4, self-check and plan | Partly resolved | `manifest.yaml`:189 now reads BC-1 to BC-48. But `plan.yaml`:2401 in this worktree still reads BC-1 to BC-47, and no criterion cites BC-48. The author says a separate plan amendment covers this; it is not in this worktree. |
| O-1, the interpreter must import graphify | Resolved | ADR-006:39 requires a first line of `#!` plus one absolute path, an interpreter that imports `graphify`, and the `sys.executable` that interpreter reports. K-13 covers uv's entry-point format. |

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 11, role: security-reviewer}
verdict: request-changes
findings:
  - id: S-1
    severity: medium
    blocking: true
    rule: ORQLET-SEC-002 (intent); ADR-006 decision 2; manifest considerations.security
    statement: >-
      The guard checks links at and under each graphify-out folder, but not in the path that leads to it.
      Upstream graphify also creates and writes <scan root>/graphify-out/... and
      <watch path>/graphify-out/..., and it resolves the scan root first. A scanned subfolder that is a
      committed link therefore sends those writes into a folder the repository chose.
      ADR-006:40 ("no write of the skill or of the graphify command it starts follows a link that a
      repository committed") and manifest.yaml:126 ("so it writes through no committed link") claim
      more than the routine does.
    evidence:
      - "upstream detect.py:2102 root = root.resolve(); :2315-2316 converted_dir = root / GRAPHIFY_OUT /
        'converted' when no cache_root; :2364 writes the converted Markdown there. skill.md:118 (P-2
        working copy) calls detect(Path(INPUT_PATH)) with no cache_root."
      - "github-and-merge.md:30-35: in the multi-path flow the skill runs `graphify extract ./core/`,
        which writes ./core/graphify-out/graph.json. If ./core is a committed link to <any folder>, the
        graph is created in <any folder>/graphify-out. That can overwrite another project's graph, and
        the target folder's files are scanned, because the resolved root makes them 'under root'."
      - "upstream watch.py:2262 out = watch_path / GRAPHIFY_OUT; :3396 (out / '.graphify_root').write_text;
        :3472-3474 needs_update via write_text. The watch path is the resolved scan root
        (add-watch.md:44)."
      - "A committed .graphify_root (Q-58) that names another folder also leads --update and watch to
        create those files in that folder. ADR-006:73 says only that its content enters the graph and
        that it runs no code; it does not mention writes there."
    impact: >-
      These writes cannot hit an arbitrary file name, which limits the impact compared with round 10's
      N-1. But a cloned repository can create graphify-out folders in any folder the person can write
      to. It can overwrite another project's graph.json or .graphify_root, which poisons that project's
      graph and the agent context built from it. It can also pull files outside the project into the
      graph.
    required_change: >-
      Choose one. (a) Extend the routine: for every folder whose graphify-out a step or the graphify
      command uses, stop unless that folder's real path equals its absolute path, meaning no link in
      the path (for example `[ "$(cd "$d" && pwd -P)" = "$(cd "$d" && pwd -L)" ]`, or os.path.realpath
      == os.path.abspath), in addition to the check under graphify-out. Add a linked scan subfolder
      and a multi-path subfolder link to BC-48. (b) Narrow ADR-006:40 and manifest.yaml:126 to "at or
      under graphify-out", state that a linked scan folder and the Q-58 redirect also cause writes
      there, and ask the person to accept this in a new ledger entry.
  - id: S-2
    severity: low
    blocking: false
    rule: ADR-006 decision 2 (check timing)
    statement: >-
      The check runs when an invocation starts. --watch starts a long-running process that keeps
      writing graphify-out/needs_update and .graphify_root through write_text, which follows links.
      A git pull or checkout made while it runs can add a committed link under graphify-out, and the
      watcher then writes through it. The ADR-006:40 claim does not hold for that case.
    evidence: "add-watch.md:40-44, 57; upstream watch.py:3396, 3472-3474"
    required_change: >-
      State in ADR-006 Consequences that the guard holds when an invocation starts and does not cover
      a running watcher after the tree changes, and ask the person to accept that. Or have the skill
      tell the person to stop the watcher before a pull or checkout.
  - id: S-3
    severity: low
    blocking: false
    rule: ADR-006 decision 2 (fail closed); BC-48
    statement: >-
      The decision does not say that the link check fails closed. A check that errors (find exits
      non-zero, or an entry cannot be read) must stop the skill, not count as "no link found".
      BC-48 also has no dangling-link case, where a test such as -e or -d is false but -L is true.
    evidence: "ADR-006:40; component.md:317"
    required_change: >-
      Add "a check that fails stops the skill" to decision 2, and add a dangling graphify-out link and
      a dangling .graphify_python link to BC-48.
  - id: S-4
    severity: low
    blocking: false
    rule: ADR-006 decision 2 (Windows stop)
    statement: >-
      The routine is POSIX shell. Under PowerShell the agent cannot run it as written and may improvise
      an equivalent that reads the existing .graphify_python. The decision does not say where the
      Windows stop sits.
    evidence: "ADR-006:41; component.md:319; skill.md:105 tells the agent to use $(cat
      graphify-out/.graphify_python) in later blocks"
    required_change: >-
      State that the Windows stop is an instruction in the skill text placed before any command, so it
      does not depend on the POSIX routine running.
  - id: S-5
    severity: info
    blocking: false
    rule: ADR-006 decision 2 (scope)
    statement: >-
      The upstream CLI honours GRAPHIFY_OUT, which can be a relative name or an absolute path, from the
      person's environment. The skill and the guard check only the literal graphify-out. With the
      variable set, the CLI writes to a folder that the routine never checked. The person controls the
      variable and graphify loads no .env file, so a repository cannot set it.
    evidence: "upstream paths.py:30-53; no dotenv loading found in the upstream package"
    required_change: Optionally have the skill stop, or clear the variable, when GRAPHIFY_OUT is set.
  - id: S-6
    severity: info
    blocking: false
    rule: manifest self_check integrity
    statement: >-
      The checks entry at manifest.yaml:197 records "r11 on the content that merges" with result: pass
      before round 11 has returned. It also leaves N-4's plan-side change unverified in this worktree.
    evidence: "manifest.yaml:197; plan.yaml:2401 (BC-1 to BC-47)"
    required_change: Record the round 11 result only after both reviews return.
```

## Self-check

- **What I examined:**
  - ADR-006 in full, and BC-48 and K-13 in `component.md`.
  - `manifest.yaml` lines 110–206.
  - Q-56 to Q-59 in the ledger.
  - The round 10 notes of both reviewers, with the author's responses.
  - `/tmp/guard-standards.txt`.
- **Citations checked:**
  - The P-2 working copy at `src/orqlet/workflow/skills/graphify/` in the main workspace: `skill.md` lines 40–139, `references/add-watch.md`, `references/update.md` lines 1–60 and `references/github-and-merge.md`. This is a working copy, not a commit.
  - Upstream `/tmp/upstream/graphify/graphify/`: `detect.py`, `watch.py` and `paths.py`. I also checked that upstream skips file links whose target is outside the scan root (`detect.py`:2328-2329), so I did not raise that as a read risk.
- **Not run:**
  - The read-only shell refused all commands, so I ran no `git diff` against 17e162c, computed no hashes and ran no `orqlet validate`.
  - I did not open `as-is.md`, `design-format.md` or `evidence/web/`.
  - I did not check whether `graphify clone` updates a clone it reuses.
- **Revision:** the files in `/tmp/wt-guard` as they were at review time.
- **Unverified:** I have not shown end to end that S-1 overwrites another project's `graph.json`; it rests on reading the upstream code.
- This is an additional check, not a guarantee.

## Author's responses

- Every finding of this round concerns the Graphify interpreter routine of ADR-006 decision 2 or the tool preparation of its decision 4. The person moved Graphify and tool preparation to a separate task with a security-first design (Q-60), so the routine, BC-48 and K-13 are not part of the design that merges; the findings carry over to that task's design as evidence. The confirmed `python -c` behaviour (a committed module in the working folder is imported) is recorded in ADR-006's rejected alternative "Bundling Graphify in this task".
