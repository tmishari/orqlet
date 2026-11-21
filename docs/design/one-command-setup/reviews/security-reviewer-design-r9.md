# Security review of the design, round 9

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-21T19:00:23Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. This round reviews the revision of ADR-006 decision 2 that answers Q-56.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

At start (2026-11-21T19:00:23Z) the design files had the hashes in the table of `architecture-reviewer-design-r9.md`, which started at the same moment; every artifact hash equalled the one recorded in `design/manifest.yaml` (manifest `ac6897435881c7f26d8f7ff25748eeeadc263feb8d2fbbc1939552bd86ab7d75`, ADR-006 `cd41f345740ff2d64482ba94420292752fca0c785e1cd903957ba49bbcef4656`). The design was revised after this round, in response to its blocking finding, so the hashes at save differ for `design/manifest.yaml`, `design/adr-006`, `design/component.md` and `questions.yaml`. The reviewed content is not what will merge, and round 10 reviews the revised content.

## Reviewer output (unchanged)

**Verdict: request changes.** The revision does stop the skill from running an interpreter path read from a committed `graphify-out/.graphify_python`. But rewriting that file at every invocation opens a new risk from the same committed file.

I could not verify the diff or the D-11 hash, because shell commands were refused in this mode. I found the revised text by searching for `graphify_python` and Q-56, and checked the stored snapshot drafts at `/tmp/p2-draft` and `/tmp/upstream/graphify` to see how the skill actually writes and reads the file.

**Blocking**

- **F-1 (high): the rewrite follows symlinks.** ADR-006 doesn't say how the file is written. Upstream writes it with Python's `open(..., 'w')`, which follows symbolic links, and Git recreates committed symlinks on clone.
  - Before the revision, upstream wrote the file only when it was missing, so a link to an existing file was left alone.
  - Now a repository that commits `.graphify_python` as a link to `~/.zshrc` or `~/.ssh/authorized_keys` gets that file replaced with the interpreter path. This happens the first time you run `/graphify` there, quick question path included. The same applies if the `graphify-out` folder itself is a symlink.
  - **Fix:** either refuse when the file or folder is a symlink, or write a new file and rename it over the old one. The alternative is to drop the file and work out the interpreter inline in each step.

**Non-blocking**

- **F-2 (medium): no test for the new behaviour.** Your Q-56 answer requires a test, but no acceptance criterion covers it. The graphify criterion (BC-19) checks only rendering and provenance. It should cover the rewrite on every path, no `python3` fallback, and the symlink case.
- **F-3 (low): "from the graphify on PATH" is not precise enough.**
  - The ADR rules out the `python3` fallback only when graphify is missing. The draft still falls back to `python3` when graphify is present but its interpreter can't be used.
  - The skill also searches relative `PATH` entries, which `install` deliberately refuses. With a relative entry like `./bin`, a repository can supply its own `graphify`. The design should either rule that out or record it as an accepted risk next to Q-42.
- **F-4 (low, unconfirmed): two related inputs are not covered.**
  - The GitHub-clone flow may run the pipeline inside a remote clone, whose committed `graphify-out` files were never rewritten.
  - A committed `graphify-out/.graphify_root` can point update and watch at another folder of yours. I couldn't tell whether the earlier review observations that Q-56 leaves as they are already cover this.

**Decision for you:** for F-1, keep the file and write it without following links, or drop the file and work out the interpreter inline in each step. Dropping it also settles the clone part of F-4. But it changes more of the upstream skill than your Q-56 answer allowed, which limited the change to the skill's body.

## Author's responses

- F-1: kept the file and write it without following links, within the body-only scope of Q-56. Decision 2 now says the routine stops when `graphify-out` is a symbolic link and removes `.graphify_python` before it writes a new file; BC-48 checks that a committed link's target stays unchanged.
- F-2: added BC-48, which covers every path, the absence of a `python3` fallback and the link case.
- F-3: decision 2 now requires the `graphify` that `command -v` finds and its interpreter to be absolute paths to existing executables, otherwise the skill stops; there is no `python3` fallback, so a relative `PATH` entry cannot supply the program.
- F-4: the routine now runs in the folder whose `graphify-out` the next step uses, which covers a pipeline run inside a clone. For `.graphify_root`, the person accepted the residual risk (Q-58), recorded in ADR-006 Consequences and the manifest's security note.
