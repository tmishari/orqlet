# ADR-003: Base revision under squash merges

## Context

`gate status` binds `base_revision` to HEAD, and research copies it into the header (A-69, A-70). Every evidence entry must cite that revision (A-71), and research commits its web evidence before citing it (A-73). Design's input check needs the base revision to be an ancestor of HEAD (A-74), and pull requests are squash-merged (A-75). A base on the research branch therefore leaves main's history, and this task needed two extra pull requests to re-cite its facts on main (Q-12, Q-13, C-23).

## Decision

1. Each phase skill runs `gate status --json` for its header before its first commit on the phase branch, so `base_revision` is the protected branch's commit that the branch starts from. Once the branch has a commit, research cites every fact outside its own folder with `--revision` set to `base_revision`, in a call separate from its task-owned evidence, which it cites at HEAD after committing it.
2. `validate as-is` derives the task from the AS-IS file's own path after canonicalisation (`docs/design/<task>/as-is.md`). An evidence entry is task-owned when its canonical path's first four components are exactly, and case-sensitively, `docs`, `design`, that task and `evidence`. A task-owned entry may cite a revision other than `base_revision`; the validator reads that file at HEAD through the Git port and checks the cited lines against the entry's sha256. A task-owned entry that cites `base_revision` is read at `base_revision`, as today. A file outside a task folder exempts nothing, and every other entry, including one in a sibling folder whose name starts with the task's name or one under `Evidence/`, still cites `base_revision` exactly (ORQ-E332).
3. `validate as-is` runs today's size, credential and hidden-character scan on each task-owned entry that cites a revision other than `base_revision`, over the bytes its hash check reads at HEAD, in addition to the scan of `evidence/web/` at cite time. Entries that cite `base_revision` are not scanned, as today. A failed scan reports the new error ORQ-E338: it names the rule and the line, never the text; it says that a credential it shows is to be treated as exposed and revoked or rotated, because the file may already be pushed or merged; and it suggests no history rewrite on a shared branch. The docstring that says the scan runs at cite time only is corrected.
4. The input check approves exactly the task-owned evidence files that the AS-IS facts cite, compared with the same reference as `as-is.md` in each phase: for design, the commit on the protected branch that holds the AS-IS acceptance, which under squash merges is the research merge; for plan and implement, the design merge, whose approved files gain them. The ledger rule of design's input check uses the same reference. A change to one or its removal stops the skill. Later phases may add new files under `evidence/web/` but never change a cited file. The planned-work row of the stale-input matrix says the same.

## Consequences

- The AS-IS file, its ledger and its own evidence merge in one squash commit; the base stays on main and design's input check passes without a re-cite.
- An edit to cited lines of task evidence after acceptance fails validation (ORQ-E335), and any edit to a cited evidence file stops the input check. New evidence that design or implement adds under `evidence/web/` stops nothing.
- An uncommitted edit cannot satisfy validation, because the file is read at HEAD.
- The `revision` of task-owned evidence becomes informational once the branch commit is gone; the content hash is the binding.
- Existing AS-IS files stay valid: the rule only accepts more, because the new scan covers only entries that use the new exemption. Every existing AS-IS file still passes `validate as-is` after the change.
- An agent that binds after its first commit still meets today's failure, with today's recovery.

## Rejected alternatives

- Re-cite after every squash merge (today): one extra pull request and acceptance per phase.
- Let the input check accept a squash commit the person names: it weakens "same project" for all evidence, and needs a new comparison of every cited range across two trees.
- Bind `base_revision` to the merge base with the protected branch inside `gate status`: the command does not know which branch is protected, and task evidence would still be missing at that base.
- Exempt the whole task folder: facts could then rest on fragments, review notes or the ledger, which no one meant to use as evidence.
- Approve the whole `evidence/` folder: design and implement may add web evidence there, so every later input check would stop on the phase's own permitted output.
- Take the task from `header.task`: a copy validated from another path could exempt any folder its header names.
- Change the merge strategy: a team convention outside Orqlet.
