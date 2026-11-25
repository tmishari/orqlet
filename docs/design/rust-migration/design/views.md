# Rust migration: views

## Context

```mermaid
flowchart LR
  person["Developer or IDE agent"] -->|runs commands| orqlet["orqlet 1.0.0 (native binary)"]
  orqlet -->|reads and writes, untrusted| repo["Managed repository: .orqlet, client folders, AGENTS.md, docs/design"]
  orqlet -->|hardened subprocess| git["git executable"]
  orqlet -->|journals, backups, apply lock, review packets| data["Data directory (ORQLET_DATA_DIR or OS local data folder), never inside the repository"]
  client["IDE client hook"] -->|stdin payload| orqlet
```

No new trust boundary: the same repository, Git and data directory as 0.5.2 (A-17, A-18, A-26).

## Container

```mermaid
flowchart TB
  subgraph workspace["Cargo workspace (repository root)"]
    cli["crates/orqlet-cli: binary orqlet"]
    adapters["crates/orqlet-adapters"]
    application["crates/orqlet-application"]
    domain["crates/orqlet-domain (no_std)"]
    xtask["xtask: build and check of MANIFEST.json and schemas"]
    wf["workflow/: data files, embedded at build time"]
  end
  cli --> adapters --> application --> domain
  cli --> application
  cli --> domain
  adapters --> domain
  adapters -. include_dir .-> wf
  xtask --> application
  xtask --> domain
  xtask -. reads and writes .-> wf
```

## Data flow: validate an artifact

```mermaid
flowchart LR
  file["artifact file (untrusted)"] -->|bytes, max 512 KiB| fs["FileSystem adapter (no symlinks)"]
  fs --> split["front matter split, BOM and CRLF normalised (A-34)"]
  split --> yaml["documents module: serde-saphyr parser events build the generic tree; ADR-007 rules and 0.5.2 scalar resolver"]
  yaml --> contract["serde contract from the tree, no coercion, deny_unknown_fields, then validation; messages never quote input"]
  contract --> rules["use case checks: evidence hashes via Git port, ledger, class"]
  rules --> findings["findings and verdict"]
  findings --> out["cli-result envelope (JSON) or text; exit status"]
```

## Sequence: upgrade

```mermaid
sequenceDiagram
  participant P as Person
  participant C as orqlet-cli
  participant U as upgrade use case
  participant L as apply lock (File::try_lock)
  participant J as journal and backups
  participant F as FileSystem adapter
  P->>C: orqlet upgrade
  C->>C: data directory inside the repository? refuse, ORQ-E105 (ORQ-E106 if Git fails)
  C->>U: run with wired adapters
  U->>J: read format and status of every record in the project's upgrade folder
  Note over U,J: open record: refuse, ORQ-E131; unreadable: refuse, ORQ-E136
  U->>F: read generated.lock.yaml and current files
  U->>U: render embedded workflow, classify each file by recorded hash
  U->>L: acquire, retry up to 10 s
  U->>F: re-check hashes (stale plan refused)
  U->>J: back up targets, open journal
  loop each write, lock file last
    U->>F: atomic write or delete
    U->>J: mark entry done
  end
  U->>J: mark change complete
  U-->>C: result and findings
  C-->>P: text or JSON, exit status
```
