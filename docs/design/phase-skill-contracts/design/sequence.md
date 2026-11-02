# Sequences

Three interactions with their main failure paths. For readability the diagrams leave out some branches that ADR-003 decisions 4 and 6 and ADR-002 decision 3 hold:
- a validator error other than ORQ-E350;
- a git check that ends with an unexpected exit status or error output ("check not run");
- a missing or never-fetched ref of the protected branch;
- a merge commit that is not a full hex id, not reachable from that ref or from HEAD, or did not change the approved files;
- each kind of ledger change that the fail-closed rule stops on, against the design merge and, in implement, the plan merge;
- other commits in scope that keep the approval valid;
- the standards-hash row;
- in implementation, a command on the warning list, which runs only after the person's yes, and the tester handing such a check back to the coder.

Sequence 2 also leaves out the same-project check and the ancestor checks, which run as in sequence 1.

## 1. A phase starts in a fresh session: the input check

The example is `/orqlet-plan`; design and implement run the same check on their own inputs (ADR-003 decision 4). Every value taken from an artifact goes into a command as one single-quoted argument.

```mermaid
sequenceDiagram
  actor P as Person
  participant A as Agent (orqlet-plan)
  participant R as Repository files
  participant O as orqlet CLI
  participant G as git
  P->>A: /orqlet-plan for task T
  A->>R: read docs/design/T/ and questions.yaml (no memory of earlier sessions)
  A->>O: orqlet gate status T --json
  alt design manifest missing (ORQ-I394)
    A-->>P: no design for T. Run /orqlet-design first. STOP
  else present
    A->>O: orqlet validate design docs/design/T/design/manifest.yaml (before any git command)
    alt header.task is not T (ORQ-E350)
      A-->>P: the design belongs to another task. STOP
    else a path or glob holds a character outside the allowed set
      A-->>P: the artifact holds an unexpected path. Please check it. STOP
    else valid form
      A->>G: git merge-base --is-ancestor base HEAD
      alt not an ancestor
        A-->>P: the design comes from another repository or branch. Which one is meant? STOP
      else same project
        A->>P: which ref is the protected branch, and which commit merged the design pull request? (the agent may list candidates from that ref, never choose)
        P->>A: ref origin/main and merge commit m (full hex id)
        A->>G: show parents, subject and approved files of m, ancestor checks against the ref and HEAD, git diff --quiet m -- as-is.md and design/ of T, untracked files, git diff m -- questions.yaml
        alt a difference, an untracked file, ORQ-E353, or a change to a question answered at m or to a ruling
          A-->>P: an approved file was edited after its approval. A new approval pull request is needed. STOP
        else unchanged since the merge
          opt stale (ORQ-W390)
            A->>G: git log base..HEAD on the scope (hash, signature status, author, subject, files)
            alt a commit changes a file whose facts the design cites, or an unmatched cause
              A-->>P: matrix row needs an AS-IS refresh, an impact review or your answer. STOP
            else only planned work of this task, or an upgrade to a newer workflow version
              A-->>P: matrix row keeps the approval valid. Commits shown, trailer and author are claims. Continue?
              P->>A: continue
            end
          end
          A->>R: open questions that block plan?
          alt a blocking question is open
            A-->>P: ask the question. STOP until answered
          else none
            A->>O: orqlet standards for --path p --phase plan --role planner (each scope path)
            A->>R: read CI and build files for the check commands
            A->>O: orqlet evidence cite on each command's lines and the files it invokes
            A->>R: write plan.yaml: acceptance criteria and checks first, then file operations
            A->>O: orqlet validate plan docs/design/T/plan.yaml
            A-->>P: plan ready. Commit it and open a plan pull request. Next: /orqlet-implement. STOP
          end
        end
      end
    end
  end
```

## 2. One implementation phase, with a design revision

```mermaid
sequenceDiagram
  actor P as Person
  participant A as Agent (orqlet-implement)
  participant T as orqlet-tester
  participant O as orqlet CLI
  participant S as Project's own commands
  participant G as git
  P->>A: /orqlet-implement P-2
  A->>O: orqlet gate status T --phase P-2, then the validators
  A->>P: which ref is the protected branch, and which commits merged the design and the plan?
  P->>A: ref origin/main, m1 and m2
  A->>G: git diff --quiet m1 -- as-is.md and design/, git diff --quiet m2 -- plan.yaml, git diff m1 -- questions.yaml, git diff m2 -- questions.yaml
  G-->>A: no difference, no changed question or ruling
  O-->>A: design and plan stale on base_revision
  A-->>P: commit c3, unsigned, author and trailer Orqlet-Task T are claims, files only from P-1's operations and reviews/. Matrix row: edits inside the planned files, approval valid. Continue?
  P->>A: continue
  A->>G: git log on the files the checks cite, since the plan's base
  A-->>P: commits that touch the check sources, shown before the first check
  A->>O: orqlet standards for --path f --phase implementation --role coder (each file)
  A->>T: acceptance criteria of P-2 and their sources
  T-->>A: tests written before the code
  loop small, coherent changes inside the file list
    A->>A: change one part
    A->>O: orqlet evidence cite on the check's lines and the files it invokes
    A->>G: git diff --quiet HEAD -- cited files, untracked files under them
    alt a hash differs from the plan's, a cited file has an uncommitted or untracked change, or the plan text differs from the cited lines
      A-->>P: the command or what it starts changed after approval. STOP
    else unchanged
      A->>S: run the check the plan names (its command from the plan)
      S-->>A: output and exit status
    end
  end
  alt new evidence contradicts ADR-n or BC-n
    A-->>P: Design revision needed: ADR-n, evidence path:lines, effect. STOP
  else a file outside the list must change
    A-->>P: plan amendment needed: path, reason. STOP
  else all checks ran
    A->>O: orqlet knowledge impact, validate test
    A->>A: /orqlet-review
    A-->>P: report: files, checks run (command, exit, result), not run, coverage, deviations, uncertainties. STOP
  end
```

## 3. Upgrade in a project with team text and a local edit

```mermaid
sequenceDiagram
  actor P as Person
  participant O as orqlet upgrade
  participant L as .orqlet/generated.lock.yaml
  participant F as Project files
  P->>O: orqlet upgrade --dry-run
  O->>L: read recorded hashes
  O->>F: hash files on disk
  O-->>P: plan: update skills, add the new references, restore an edited SKILL.md, update AGENTS.md blocks
  P->>O: orqlet upgrade --yes
  O->>F: write in a journal, restore the edited SKILL.md (ORQ-W096)
  O->>F: rewrite only the managed blocks of AGENTS.md, team text kept byte for byte
  O->>L: write the lock last
  O-->>P: done, with ORQ-W096 for the restored file
  P->>O: orqlet upgrade --check
  O-->>P: nothing to upgrade (second run plans nothing)
  alt a generated file has a conflicting team edit
    O-->>P: ORQ-W080, the change stops and exits 1, with the diff written for the person
  end
```
