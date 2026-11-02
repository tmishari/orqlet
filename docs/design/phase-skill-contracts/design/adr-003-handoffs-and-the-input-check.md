# ADR-003: The task folder is the handoff, and every phase checks its inputs before it starts

Status: proposed. It becomes accepted when the design pull request is merged by an authorised person.

## Context

- Every artifact of a task lives under `docs/design/<task>/` (AS-IS A-12). The artifact header holds the task, a status, `workflow_version`, `protected_set_digest` and `bound` (base revision, standards lock hash, applicable rules hash, profile version) (A-48). The status is informational, and no skill sets it to approved (A-13).
- `orqlet gate status <task>` reads the AS-IS file, the design manifest and the plan:
  - it reports a missing one as ORQ-I394;
  - it reports a stale one as ORQ-W390, with the components that differ: the five bound values, plus `base_revision` when a file in the artifact's scope changed since that revision (A-50, `gate_status.py:177-229`);
  - the bound base revision is HEAD (`gate_status.py:87`);
  - a base revision that is not in the repository produces only a skip line without a finding code, and the artifact is not marked stale (`gate_status.py:216-221`);
  - approval is evidence on the host, so an offline run always ends NOT_RUN (ORQ-I393).
- The validators check the task against the folder (`validate as-is` ORQ-E331, `validate design` ORQ-E350, `validate plan` ORQ-E370) and the hash of the input each artifact cites (ORQ-E353 for `as_is_ref`, ORQ-E371 for `design_ref`). An open question that blocks design fails `validate design` (ORQ-E367) (A-51).
- Not settled: how the person's acceptance of the AS-IS file is recorded (U-1), what counts as materially outdated (U-2), and how an artifact from another project is recognised, since the header has no project identifier (U-3).
- The research skill says to copy the `bound` values of gate status into the header, but the header keeps `workflow_version` and `protected_set_digest` outside `header.bound` (C-7). The plan skill calls a NOT_RUN gate status a failure, which it always is offline (C-6).
- The proposal makes a stale approval invalid, and that cannot be waived (W-5, `docs/design/orqlet-architecture-proposal.md:3375`). Its invalidation matrix, a W-4 element, says which changes leave an approval valid (`docs/design/orqlet-architecture-proposal.md:3055-3084`):
  - edits inside the phase's planned files: valid;
  - a newer accepted `workflow_version`: valid;
  - target-branch changes in scope: valid unless they touch facts the design cites or a declared surface (design), or an operation's path (plan), in which case an AS-IS refresh or an impact review is needed;
  - a new or changed MUST rule: impact review.
- `gate status` is stricter than that matrix: it reports any of these as stale. Commit trailers are text that anyone can write.

## Decision

1. **The handoff is the task folder.** A skill starts from the files under `docs/design/<task>/` and the ledger, and never from the memory of an earlier conversation. A phase can therefore start in a fresh session.
2. **What each output identifies.** The fields already exist; the reference names them:

   | | Task | Scope | Decisions | Open questions | Prerequisites |
   |---|---|---|---|---|---|
   | AS-IS | `header.task` | `scope.paths` | none (research decides nothing) | `unknowns` with their `question_ref`; the brief's questions | `header.bound`, `base_revision` |
   | Design | `header.task` | `scope.paths` | the ADRs and the design brief in `component.md` | the brief's unresolved decisions, each a ledger question | `as_is_ref`, `header.bound` |
   | Plan | `header.task` | the file operations of every phase | the phases and `reuse_decisions` | none may block; any other is in the ledger | `design_ref`, `header.bound` |
   | Phase report | the `Orqlet-Task` and `Orqlet-Phase` trailers | the phase's file list | its deviations | its remaining uncertainties | the plan and its phase id |

3. **The header.** Run `orqlet gate status --json`. Copy `workflow_version` and `protected_set_digest` from its `bound` to the top level of `header`, and the other four values into `header.bound` (fixes C-7).
4. **The input check.** Design, plan and implement run it on their inputs before any other work. Research runs it on an earlier AS-IS file that it resumes, without the *Approved* part. It takes a few commands, not a new round of research. The checks run in this order, and every git command comes after the validator.

   Each git check passes only on its expected result. For `--quiet` and `--is-ancestor`, that is exit status 0 or 1 as the check states. For other commands, it is exit status 0 with nothing on the error output. Any other result stops the skill with "check not run". A revision the agent composes, such as a parent, is resolved first with `git rev-parse --verify` and passed in single quotes.
   - *Present.* Gate status reports no ORQ-I394 for the input. Otherwise stop and name the skill that produces it.
   - *Validator.* The artifact's validator runs next. The contracts fix the form of the revision (40 or 64 hex characters, `src/orqlet/application/contracts/common.py:21`), the task and the phase id, and nothing else. Every value taken from an artifact is passed as described in ADR-002 decision 3: one single-quoted argument, paths after `--`, and a stop on any other character. A validator error that no later check names, such as a schema error, stops the skill and names the finding.
   - *Same task.* `header.task` equals the folder name (no ORQ-E331, E350 or E370). Otherwise stop.
   - *Same project.* `git merge-base --is-ancestor <base_revision> HEAD` exits 0, and gate status lists no "is not in this repository" line for the input. Otherwise the artifact comes from another repository or an unpublished branch: stop and ask.
   - *Approved.* For design, the AS-IS file is accepted (decision 7). For plan and implement, the commit that merged each approval on the protected branch is needed: the design's pull request for plan, and also the plan's pull request for implement. A D1 plan may share the design's pull request, and an approved plan amendment's merge replaces the plan's. The approved files are `as-is.md` and `design/` for the design merge, and `plan.yaml` for the plan merge, under `docs/design/<task>/`.
     - The person names the remote-tracking ref of the protected branch, such as `origin/main`, and each merge commit. The agent never chooses a commit. If the person does not know it, the agent lists candidates from that ref only (`git log --format='%H %P %G? %an %s' '<ref>' -- <approved files>`), and the person picks one. A missing or never-fetched ref means the check did not run: the skill asks.
     - Only a full hex id is accepted. The agent shows its parents, its subject and the approved files it changed. The commit must be reachable from the ref and from HEAD (`git merge-base --is-ancestor` exits 0 for both), and must have changed the approved files (`git diff --quiet` between its first parent and it exits 1).
     - `git diff --quiet <merge> -- <approved files>` exits 0, so the working tree holds the approved bytes, and `git ls-files --others --exclude-standard -- <approved files>` prints nothing.

     A difference or an untracked file matches the matrix row "editing the approved design or plan" (`docs/design/orqlet-architecture-proposal.md:3073`): the approval is invalid, and the skill stops for a new approval pull request. Only ORQ-I393 behind a NOT_RUN result is expected offline and is not a failure (fixes C-6).
   - *Current.*
     - **Edited approved input.** ORQ-E353 (the AS-IS file changed after the design cited it) and ORQ-E371 (the design changed after the plan cited it) match the same row as above. The skill stops for a new approval and never continues.
     - **Changed requirements in the ledger** (`docs/design/orqlet-architecture-proposal.md:3074`, `:3088`). The agent shows `git diff <reference> -- docs/design/<task>/questions.yaml` for each reference commit:
       - design: the latest commit of the AS-IS file that holds its acceptance. If that acceptance is not committed, the skill asks the person to commit it first;
       - plan: the design merge;
       - implement: the design merge and the plan merge.

       The rule fails closed. Since a reference commit, these changes stop the skill:
       - any change to any field of a question that was answered there, including its status, and its removal;
       - any change to the conflicts list or a ruling.

       Only new questions, and the answer and status of a question that was open at the reference commit, do not count. For plan and implement, the resolution is a new approval pull request. For design, the person accepts the AS-IS file again, which moves the reference commit, or asks for a refresh.
     - **Stale.** An ORQ-W390 for the input goes to decision 6.
   - *Questions.* No ledger question that blocks this phase is open. A material unknown of the input counts as unanswered only when its `question_ref` names a question that is open and blocks this phase. Design addresses every other material unknown with evidence, or lists it as an unresolved decision with a ledger question.
5. **A failed check stops the skill.** The skill tells the person which check failed, what it found and what would resolve it: run an earlier skill again, answer a question, confirm an approval, or get an AS-IS refresh or an impact review. It never edits an earlier phase's artifact to pass the check, and never changes bound values to make an artifact current: that would turn a stale approval into a valid-looking one (W-5).
6. **A stale input (ORQ-W390) is matched to the invalidation matrix.** The skill stops and tells the person the cause, mapped to the matrix row of the proposal. It continues only where that row keeps the approval valid, and only after the person confirms. For each commit since the base revision that touches the scope, it shows the hash, the signature status where the project signs its commits, the author, the subject and the changed files (`git log --format='%H %G? %an %s' --name-only` on the scope). The trailer and the author are claims, not proof. The rows:
   - *This task's planned work.* A commit counts only if it carries this task's `Orqlet-Task` trailer and changes only:
     - files of the operations of earlier phases of the plan;
     - the plan's knowledge paths;
     - the task's records, at exactly `docs/design/<task>/reviews/`, `tests/` and `knowledge/` (`docs/design/orqlet-architecture-proposal.md:1039`) and `evidence/web/` (`src/orqlet/application/usecases/evidence_cite.py:27`).

     A commit that touches `as-is.md`, `design/`, `plan.yaml` or `questions.yaml` is never planned work: decision 4 judges it. Row: edits inside the phase's planned files; approval valid.
   - *An upgrade of Orqlet's files.* Only when the header's `workflow_version` is older than the installed one that gate status prints. Row: a newer accepted workflow version; approval valid. A `protected_set_digest` that differs while `workflow_version` is the same is a cause it cannot match (below).
   - *Other commits in scope.* If they change a file whose facts the design cites, a declared surface, or a path of a plan operation, the matrix asks for an AS-IS refresh or an impact review: the skill stops until it exists. Otherwise the approval stays valid.
   - *`standards_lock_hash` or `applicable_rules_hash`.* Row: a new or changed MUST rule; an impact review is needed; the skill stops.
   - *`profile_version`, a digest change without a newer workflow version, or any cause it cannot match.* The approval's state is unknown, which counts as not run (W-5): the skill stops and asks.

   U-2 is answered by the matrix, not by a threshold of the skill's own.
7. **Recording acceptance of the AS-IS file.** When the person says they accept it, the agent sets `header.status` to `approved`, adds a self-check entry that quotes the person's words with the time, runs `orqlet validate as-is` again, and the person commits the file (U-1). This record is the agent's claim. The content is bound later: the design cites the file by hash (`as_is_ref`, ORQ-E353 on change), and the design pull request contains the AS-IS file, so its merge confirms the acceptance. An agent that changes an accepted AS-IS file sets `status` back to `draft`, removes the acceptance entry and asks again. The design and the plan keep `draft`: their approval is the merge, which is host evidence.

## Consequences

- After the first phase of a plan is committed, gate status reports the design and the plan as stale on `base_revision` for every later phase. The skill stops each time and shows the person the commits, matched to the matrix row that keeps the approval valid. Nothing is relaxed: the skill applies the proposal's own matrix and asks the person.
- At the start of plan and of each implementation phase, the person names the protected branch's ref and one or two merge commits. At the start of design, the AS-IS acceptance must already be committed. That is the price of noticing an edit to an approved file, which gate status does not report for a plan (`gate_status.py:188-191`), and a changed requirement in the ledger.
- The ledger rule stops on any change to an answered question, a correction of wording included. Narrowing it would make the agent judge which change is material, and that judgement is the gap the rule closes.
- A commit on the protected branch that the person names but that is not the approval merge, such as a later commit that changed the same files, still passes. The person sees its parents and subject. The residual is in `considerations.md`.
- A commit with a forged trailer and a forged author that changes only planned files still looks like planned work to the skill. The person sees the files, and the signature status where the project signs. No CI check in this release compares the diff with the plan or decides an approval: no `ci` command is registered (`src/orqlet/interface/cli/app.py:36-51`), and this repository's CI runs lint, types, architecture, tests and a build (`.github/workflows/ci.yml:18-107`). The person's review of the pull request is the only gate.
- An artifact copied from a fork that shares history passes the same-project check. Its evidence still has to resolve by hash at that revision (A-51); the residue is in `considerations.md`.
- No header field is added. U-3 is answered for the cases the repository can see: another repository, an unpublished branch, another task.

## Rejected alternatives

- **A project identifier in the header.** A contract change, outside Q-3. The base revision already ties an artifact to one repository's history.
- **A separate handoff file per phase.** It would repeat what the artifacts hold, and one more file can drift. The briefs live inside the artifacts, so `as_is_ref` and `design_ref` cover them by hash.
- **Stop on every stale input with no way to continue** (today's implement text). It contradicts the matrix's promise of no endless re-approval for work the approval covers, and in practice it is passed in conversation without a record of why.
- **Let the person continue on any stale input.** That would let a person accept what the matrix calls invalid or in need of review (W-4, W-5).
- **Trust the `Orqlet-Task` trailer alone.** Anyone can write it.
- **Ignore a moved base revision.** It would miss a change to the scope made outside the task.
