# Sequence view

## First setup on a machine, then a repository

```mermaid
sequenceDiagram
    actor Dev as Developer
    participant T as Terminal
    participant O as Orqlet CLI
    participant FS as User client folders
    participant P as uv / pipx
    participant A as Assistant
    participant R as Repository

    Dev->>T: uv tool install orqlet
    Dev->>T: orqlet install
    T->>O: install
    O->>O: detect clients (names only)
    O-->>Dev: banner, preview per client and tool
    Dev->>O: yes
    O->>FS: journalled writes (skills, agents, foundation, hook entries)
    O->>P: uv tool install graphifyy==0.9.112 --python 3.12
    P-->>O: result
    O-->>Dev: states per client, host steps, invocations; exit 0 or 1
    Dev->>A: /orqlet .
    A->>O: orqlet status --root . --json
    O-->>A: repository without .orqlet
    A->>O: orqlet init --root <top> --dry-run
    O-->>A: plan
    A-->>Dev: shows plan, asks
    Dev->>A: yes
    A->>O: orqlet init --root <top> --yes
    O->>R: journalled project writes
    A-->>Dev: status and the next person-started command
```

## A normal session afterwards

```mermaid
sequenceDiagram
    actor Dev as Developer
    participant A as Assistant
    participant H as orqlet hook
    participant R as Repository

    A->>H: session-start payload (cwd)
    H->>R: upward .orqlet/ search, read lock (no process)
    H-->>A: fixed-template status (versions, next command); exit 0
    Dev->>A: describes work normally
    A->>R: edits a generated file
    A->>H: post-edit payload
    H->>R: read lock
    H-->>A: advisory: generated file, change source and run orqlet upgrade; exit 0
    Dev->>A: /orqlet-research <task> (person-started, unchanged)
```

## Recovery from a conflict

```mermaid
sequenceDiagram
    actor Dev as Developer
    participant O as Orqlet CLI
    participant FS as User client folders

    Dev->>O: orqlet install
    O->>FS: read ~/.claude/settings.json
    FS-->>O: not strict JSON
    O-->>Dev: conflict for the Claude Code hook entry, recovery: fix the file; other entries applied; exit 3
    Dev->>FS: fixes the file
    Dev->>O: orqlet install
    O-->>Dev: already configured for applied entries, registered for the hook; exit 0
```
