# Sequence diagrams

Four interactions, each with its failure paths. Every message that carries a finding carries a rule id, a line number or a closed field name, and never a value or a raw key (ADR-002 decision 9).

## 1. `upgrade` with a declaration

```mermaid
sequenceDiagram
  actor Dev as Developer
  participant CLI as upgrade
  participant Src as load_integrations
  participant Comp as compose
  participant Ad as Claude Code adapter
  participant Plan as plan_changes and the change-plan builder
  participant FS as FileSystem port
  Dev->>CLI: orqlet upgrade
  CLI->>Src: read .orqlet/integrations.yaml
  alt declaration absent
    Src-->>CLI: (None, no findings)
    CLI->>Comp: compose(integrations=None)
    Note over Comp: no MCP file
  else declaration invalid
    Src-->>CLI: (None, error findings)
    CLI-->>Dev: refuse, exit 3, nothing written
  else declaration valid
    Src-->>CLI: (declaration, information findings)
    CLI->>Comp: compose(integrations=declaration)
    Comp->>Ad: RenderRequest with the declaration
    Ad-->>Comp: .mcp.json text from rendered_entry, owner seeded, scanned
    CLI->>Plan: plan_changes(wanted, recorded)
    Plan->>FS: plan_changes reads the existing .mcp.json, if any
    Note over Plan: the builder compares hashes only
    alt no file
      Plan-->>CLI: create
    else file equals the render
      Plan-->>CLI: up to date, nothing to write
    else file differs
      Plan-->>CLI: proposal with the wanted text only
      Note over Plan: _propose passes no existing bytes for an MCP path
    end
    CLI->>FS: apply the journalled plan
    CLI-->>Dev: result and findings, including how to merge a proposal
  end
```

## 2. `validate integrations` and the CI line

```mermaid
sequenceDiagram
  actor CI as CI job or developer
  participant Cmd as validate integrations
  participant UC as integration_findings
  participant FS as FileSystem port
  CI->>Cmd: orqlet validate integrations .orqlet/integrations.yaml
  Cmd->>FS: does the declaration exist?
  alt absent
    Cmd-->>CI: not run, exit 5
  else present
    Cmd->>UC: project, loader, path
    UC->>FS: read the declaration and each MCP file that exists
    UC->>UC: scan raw text and decoded strings, JSON entry checks, pin comparison
    alt any error, including an unreadable file
      UC-->>Cmd: findings
      Cmd-->>CI: exit 5, rule names and line numbers
    else none
      Cmd-->>CI: pass, with information findings and counts
    end
  end
  Note over CI,Cmd: A pull request that edits this job, the pinned version or CODEOWNERS can switch it off (ADR-002 decision 11)
```

## 3. `doctor` and `sync`

```mermaid
sequenceDiagram
  actor Dev as Developer
  participant D as _diagnose
  participant UC as integration_findings
  Dev->>D: orqlet doctor or orqlet sync
  D->>UC: run outside the full branch
  alt declaration present
    UC-->>D: the findings of sequence 2
  else absent and an MCP file holds the text orqlet-
    UC-->>D: a warning: nothing was checked, and why
  else absent and no such file
    UC-->>D: nothing
  end
  D-->>Dev: findings merged with the others
```

## 4. The developer's first connection, and an unattended surface

```mermaid
sequenceDiagram
  actor Dev as Developer
  participant CC as Claude Code
  participant Atl as Atlassian MCP server
  participant Cloud as Cloud agent or review context
  Dev->>CC: open the project, run /mcp
  CC->>Atl: connect to the address in .mcp.json
  Atl-->>CC: 401, authentication needed
  CC->>Dev: OAuth sign-in in the browser
  Dev->>Atl: consents with their own account
  Atl-->>CC: token, stored per endpoint by the client
  Note over CC,Atl: no credential in .mcp.json, the user's own permissions apply
  Dev->>Cloud: start a session that uses the entry
  alt the surface uses the account of the user who started it (Q-12)
    Cloud->>Atl: connect as that user
  else it uses an account of its own, or an environment shared by several people
    Note over Cloud,Atl: Q-6 and Q-9 are not met on this surface (ADR-002 decision 12, check V-10)
  end
```
