# Sequence views

Three sequences: a policy change reaching the generated files, a code review that needs a different family from the coder, and a release-time recheck of the shipped seed.

## S1. A policy change, from edit to generated files

```mermaid
sequenceDiagram
    actor Dev as Developer
    participant CLI as orqlet CLI
    participant App as application use cases
    participant Dom as domain (resolution)
    participant FS as FileSystem port
    participant Host as Git host
    actor Appr as Approver (not the author)

    Dev->>CLI: edit .orqlet/model-policy.yaml
    Dev->>CLI: orqlet validate model-policy
    CLI->>App: validate_model_policy
    App->>FS: read policy (limit, strict YAML)
    App->>Dom: check references, exclusions, states
    Dom-->>App: findings
    App-->>Dev: PASS / findings, exit 0 or 5
    Dev->>CLI: orqlet upgrade (preview)
    CLI->>App: compose with models
    App->>Dom: resolve each role and skill, per client
    Dom-->>App: selection, source, rejected + reasons
    App-->>Dev: change plan: files that change, missing-candidate, stale reviews
    Dev->>Host: pull request with policy and generated files
    Host->>Appr: review requested (code owner)
    Appr-->>Host: approve
    Host-->>Dev: merge (approval evidence on the protected branch)
```

## S2. A code review that must differ from the coder

```mermaid
sequenceDiagram
    actor Dev as Developer
    participant Skill as /orqlet-review (IDE agent)
    participant CLI as orqlet CLI
    participant Sub as orqlet-code-reviewer (typed subagent)
    participant Client as Client (Cursor, Claude Code or Codex)

    Dev->>Skill: run review for task and phase
    Skill->>CLI: orqlet review prepare task phase
    CLI-->>Skill: packet path (no earlier review notes), review_input blocks
    Skill->>Client: read the coder's model (requested, observed, source)
    Skill->>CLI: orqlet models resolve --role code-reviewer --client C --different-family-from coder-model
    CLI-->>Skill: eligible candidates in order, or none with reasons
    alt a candidate qualifies and the client lets a spawn name a model
        Skill->>Sub: start with the packet path, explicit model
        Sub-->>Skill: findings, self-check
        Skill->>Client: read the reviewer's observed model
        Skill->>CLI: orqlet validate review record
        CLI-->>Skill: independence I0..I2, warnings (requested differs from observed, identity-unknown), NOT_RUN if below I2
    else none qualifies
        Skill-->>Dev: NOT_RUN with reasons; run in another client, or take a human code-owner review (I3)
    end
```

## S3. Release-time recheck of the shipped seed

```mermaid
sequenceDiagram
    actor Maint as Maintainer
    participant Pages as Official vendor pages
    participant Repo as Release branch
    participant CI as Tests in CI
    participant Team as Downstream team

    Maint->>Pages: read current model pages (web access, outside Orqlet)
    Maint->>Repo: save evidence files, update seed candidates (proposed), set reviewed_for_release
    Maint->>Repo: bump workflow version, rebuild MANIFEST.json
    CI->>Repo: test: seed reviewed_for_release equals workflow_version
    CI-->>Maint: pass, or fail if the recheck was not recorded
    Repo-->>Team: new Orqlet release
    Team->>Team: orqlet upgrade writes a pending diff of the seed
    Team->>Team: reviewed edit approves or rejects each new entry
```
