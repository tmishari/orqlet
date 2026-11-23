# workflow-efficiency: views

The design brief is in [component.md](component.md). These views show what the brief changes and nothing else.

## Context

No new actor, trust boundary or integration. The code host's squash merge is the one outside behaviour the design adapts to (ADR-003).

```mermaid
flowchart LR
  P["Person: approves, reads replies"] --> A["IDE agent: Claude Code, Codex, Cursor"]
  A -->|runs| O["Orqlet CLI 0.5.1"]
  A -->|reads| W["Generated skills, roles, baseline"]
  O -->|reads; upgrade writes generated files and .orqlet locks| G["Git repository"]
  H["Code host: pull requests, squash merge"] -->|merges into| G
  O -.never calls.-> M["Language model"]
```

## Container

```mermaid
flowchart TB
  subgraph pkg["Orqlet package"]
    I["interface/cli: parsing, human and JSON output"]
    U["application/usecases: gate status, validators, evidence cite"]
    D["domain: unchanged"]
    WF["workflow: skills, references, roles, baseline, MANIFEST"]
  end
  I --> U --> D
  I -->|upgrade renders| WF
  WF -->|orqlet upgrade| GEN[".claude/, .cursor/, .agents/, .codex/, AGENTS.md block, .orqlet locks"]
```

## Data flow: reusing a check result

A result is reused only while its inputs are provably unchanged (ADR-001).

```mermaid
flowchart LR
  S["Check sources: CI lines, invoked files, config lines"] -->|cited once per phase| C["Citations in the phase"]
  T["Working tree"] -->|"orqlet evidence hash 'file'..."| Q{"Hash differs?"}
  C --> Q
  Q -->|no| R["Run the check as planned"]
  Q -->|yes| X["Re-cite the changed file, show the change, ask"]
  R --> RES["Result with exit status, HEAD and file hashes"]
  RES -->|next time the check is due| E{"HEAD or a hash differs, or an edit since?"}
  E -->|no| REUSE["Reuse the result; no rerun"]
  E -->|yes| RUN["Rerun, naming the changed input"]
  E -->|"validators' result only: confirmed planned work (later implement phase)"| CUR{"Current step shows an approved file changed?"}
  CUR -->|no| REUSE
  CUR -->|yes| RUN
```

## Sequence: one implement phase after the change

```mermaid
sequenceDiagram
  participant P as Person
  participant C as Coder (main agent)
  participant T as Tester
  participant O as Orqlet CLI
  participant R as 3 reviewers
  C->>O: gate status --phase P-n (once)
  Note over C,O: From P-2, the person confirms planned work (ORQ-W390) once, and validators rerun only at the first phase or after another change
  C->>T: acceptance criteria
  T->>O: evidence cite FILE LINES FILE LINES (one call)
  T->>T: write tests, run targeted test check
  T-->>C: report with the citations (path, lines, revision, sha256)
  C->>C: implement in small steps, targeted checks
  C->>C: full plan checks once (file hashes confirm citations)
  C->>O: knowledge impact, validate test
  C->>R: review prepare, one packet, parallel clean contexts
  R-->>C: findings
  alt blocking finding (at most 3 rounds)
    C->>C: fix all findings, one full check run, new round
  end
  C->>P: Completed / Questions / Next prompt
```
