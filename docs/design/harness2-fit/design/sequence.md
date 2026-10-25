# Sequence diagrams

## Sequence 1: Release test over every rendered file (with failure paths)

```mermaid
sequenceDiagram
  autonumber
  actor Dev as Developer
  participant T as render test
  participant R as renderers
  participant Sp as split_front_matter
  participant Y as strict loader
  participant F as front_matter functions

  Dev->>T: pytest tests/unit/render
  T->>R: render every skill, agent and command for the three clients
  R-->>T: files
  loop each file with front matter
    T->>Sp: split the text
    alt no front-matter block
      Sp-->>T: none
      T-->>Dev: fail naming the file
    else block found
      Sp-->>T: block text
      T->>Y: load the block
      alt parse error
        Y-->>T: error
        T-->>Dev: fail naming the file
      else parsed
        Y-->>T: mapping
        T->>F: simple_front_matter and front_matter_differences
        F-->>T: differences, possibly none
        T-->>Dev: fail naming the file and each key that differs
      end
    end
  end
```

## Sequence 2: Packet assertion (lands with the v0.5 packet plan)

```mermaid
sequenceDiagram
  autonumber
  actor A as IDE agent
  participant C as orqlet review prepare
  participant B as packet builder
  participant E as evidence_artifacts
  A->>C: review prepare task phase
  C->>B: build the packet
  B->>E: classify each changed path
  alt a path at a review-record path is not a valid record, or is deleted, or cannot be parsed
    E-->>B: invalid review record
    B-->>C: refusal with the path
    C-->>A: NOT_RUN naming the path and writing no packet
  else every record path is valid or absent
    E-->>B: valid records, to be left out of every list and the diff
    B-->>C: packet and manifest
    C-->>A: packet path
  end
```

## Sequence 3: A change to generated text reaches a project

```mermaid
sequenceDiagram
  autonumber
  actor Rel as Release owner
  participant W as workflow package and emitter
  participant U as orqlet upgrade
  actor Mnt as Maintainer
  participant G as gate status
  Rel->>W: change emitter and description, rebuild MANIFEST, bump version, regenerate goldens
  Mnt->>U: orqlet upgrade --dry-run
  U-->>Mnt: classified diff, workflow version change shown
  Mnt->>U: orqlet upgrade --yes
  U-->>Mnt: journalled apply, new protected-set digest
  Mnt->>G: orqlet gate status
  G-->>Mnt: artifacts written against the old digest are stale, warning ORQ-W390 and a not-run reason
  Note over U,Mnt: an interrupted apply is resumed or rolled back by the existing journal
```
