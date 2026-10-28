# Sequence views

Scope: four interactions, each with its failure paths. Orqlet is a command line that reads and writes files; "Agent" is the IDE agent of a client, which Orqlet never starts (ORQLET-NOMODEL-001).

## 1. `init` asks the conventions and the links

```mermaid
sequenceDiagram
  actor M as Maintainer
  participant O as orqlet init
  participant P as Profile and registry files
  M->>O: orqlet init
  O->>O: questions_for(profile): stack, target branch, then branch model, branch naming and patterns, commit convention, pull-request shape, merge strategy, required checks, reviewers, release flow
  loop each question that is still unknown
    O->>M: ask (an explicit "none" is a recorded answer)
    M-->>O: answer
    alt answer too long, has a line break or is outside the accepted form
      O->>O: note "answer ignored", keep the question open
    end
  end
  O->>M: "Do you have links to team resources?"
  loop each link
    M-->>O: address, title, kind, note, applies-to, tool, access
    O->>O: resources_with: the same pure checks as the command
    alt a rule fails (address, text, id, glob, duplicate)
      O->>M: finding names the field and the rule; ask again or skip
    end
  end
  O->>O: the registry exists only in memory: resources_with builds it, compose receives it with its bytes
  O->>M: show the plan (profile, registry, generated files)
  M-->>O: yes
  O->>P: apply_plan: journal, backup, write, lock last
  Note over O,P: without a terminal the answers come from --answer, links are added later with orqlet resources add, and what is missing is reported as open questions and by the information finding
```

Failure paths: an interrupted write converges on a re-run (journal, backup, lock last; AS-IS A-69, ORQLET-TEST-002); a re-run reads the registry and the profile that are on disk, as `_load_existing_profile` does for the profile. An `init` that finds the project already initialised returns `already-initialised`, and the way to change an answer or a link later is `orqlet profile answer` and `orqlet resources` (AS-IS A-3, A-74).

## 2. A maintainer adds a link, attaches a stored copy and refreshes the files

```mermaid
sequenceDiagram
  actor M as Maintainer
  participant O as orqlet resources
  participant R as .orqlet/resources.yaml
  participant U as orqlet upgrade
  participant G as Generated files
  M->>O: resources add URL --id --kind --note --path --tool --access
  O->>O: url_problems, text_problems, id and glob rules, duplicate id
  alt refused
    O-->>M: exit 3, finding with code and field
  else accepted
    O->>R: apply_plan (registry, lock last), shows the plan, asks
    O-->>M: applied; run orqlet upgrade to refresh the generated files
  end
  M->>U: orqlet upgrade
  U->>U: compose: load_resources, resources_view, adapters
  U->>G: rule files, tool skills, catalogue, conventions block
  Note over M,G: an agent or a person writes docs/resources/id.md after reading the page
  M->>O: resources attach id --form summary --ttl-days 90
  O->>O: file exists under docs/resources, at most 64 KiB, two header lines, no hidden characters, scan clean
  alt scan flags a credential shape, the header or the content is wrong, or the file is missing or too large
    O-->>M: refused, rule name and line only
  else clean
    opt entry has access login
      O->>M: asks at the terminal, also with --yes: may this repository hold internal content of that host?
      M-->>O: yes (without a terminal: needs-input, nothing recorded)
    end
    O->>R: records form, sha256 of the LF-normalised text, retrieved_at from the clock, ttl_days
  end
  M->>M: commit and open the pull request; code owners review the registry, the copies and the generated files
```

Failure paths: an invalid registry stops `upgrade` before any plan, so nothing is deleted; `PlanStale` when a file changed between the plan and the write; a removed resource has its generated files removed by the next `upgrade` as orphans of the lock (`ORPHAN_REMOVE`, `src/orqlet/domain/changeplan.py:305-350`). `doctor` reports a copy past its time-to-live and a copy whose hash differs from the record; `validate resources` fails on the second.

## 3. An agent looks up a library, once public and once behind a login

```mermaid
sequenceDiagram
  actor D as Developer
  participant A as Agent (research skill)
  participant O as orqlet
  participant W as Client web tool or browser tool
  participant S as Team site (SAML)
  participant F as Repository files
  A->>O: resources list --uncovered --json
  O-->>A: technologies of the profile with no registered resource
  A->>F: read the stored copy of a registered resource, if any (it names its retrieval date)
  alt not enough
    A->>W: official documentation page of the exact version
    W-->>A: page text (untrusted evidence)
    A->>F: write docs/design/task/evidence/web/slug.md with a verbatim excerpt, address and time; commit; cite
  end
  A->>W: open the registered address of a page with access login, in the signed-in browser route
  W->>S: request
  S-->>W: login page
  W-->>A: login page or "sign in needed"
  A-->>D: stop: "sign in to the site in your browser, then tell me"
  D->>S: signs in (own account, SAML)
  A->>W: read the page again in the signed-in session
  alt the client cannot read it
    A->>F: write an unknown with a question; ask the developer for a stored copy
  else read
    W-->>A: page text
    A->>F: write a summary in own words, Data class internal; show it to the developer
    D-->>A: yes (only then does the agent commit it; advice); resources attach by a person after review
  end
```

Failure paths: a client whose web tool is off, cached or not verified (Codex `web_search` default `cached`, Cursor not verified) cannot do the lookup; the agent records an unknown and asks, and does not answer from memory (AS-IS A-131, U-76; baseline "do not guess"). An agent never reads, asks for or writes a password, cookie, token or storage-state file.

## 4. CI checks a pull request

```mermaid
sequenceDiagram
  participant H as Code host CI
  participant O as orqlet conventions check
  participant V as Vcs (Git runner)
  participant P as Profile
  H->>O: --branch="$HEAD_REF" --base="origin/$BASE_REF"
  O->>V: resolve base and head to full ids
  alt base unknown to this clone (shallow), or no merge base
    O-->>H: NOT_RUN with the reason, exit 5; asks for --base or a deeper clone
  else resolved
    O->>V: read_at(base, profile) so that the pull request cannot relax its own rule
    V-->>O: profile at the base revision
    O->>P: take branch patterns and commit convention from it
    alt nothing configured, or free text only
      O-->>H: NOT_RUN with the reason, exit 5
    else configured
      O->>V: commit_subjects(base, head)
      alt branch unknown, or more than 200 commits
        O-->>H: NOT_RUN with the reason, exit 5 (a failure already found in what was read is reported as FAIL)
      else
        V-->>O: subjects, newest first, each cut at 1 KiB
        O->>O: branch_problems, commit_subject_problems
        alt a rule fails
          O-->>H: FAIL, findings with rule and short id, exit 5
        else
          O-->>H: PASS, exit 0
        end
      end
    end
  end
```

Failure paths: a subject with control or non-ASCII characters, or a very long one, is shown escaped and cut at 100 characters after a fixed code prefix, never at the start of a line and never interpreted. The step is only a gate when a person makes it a required status check on the host (ADR-003).
