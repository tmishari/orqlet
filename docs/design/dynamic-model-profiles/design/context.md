# Context view: Orqlet, the clients and the people around model selection

Orqlet stays a tool that writes files and checks records. The three clients choose and run models. Nothing in this design adds a call from Orqlet to a model, a client or a vendor.

```mermaid
flowchart LR
    dev["Developer<br/>(author, person who accepts)"]
    owner["Code owner / approver<br/>(any developer except the author)"]
    admin["Company administrators<br/>(model restrictions on the clients)"]

    subgraph repo["Project repository"]
        policy[".orqlet/model-policy.yaml<br/>(team-owned, reviewed)"]
        gen["Generated agent and skill files<br/>.claude .cursor .codex .agents"]
        rec["Review records<br/>docs/design/task/reviews"]
    end

    orqlet["Orqlet<br/>(CLI + packaged workflow: roles, skills, seeds)"]

    subgraph clients["IDE clients (run and choose models)"]
        cc["Claude Code"]
        cx["Codex desktop app"]
        cu["Cursor (Router enabled, model displayed)"]
    end

    host["Git host<br/>(pull requests, required reviews, CODEOWNERS)"]
    vendors["Vendor documentation<br/>(official pages; read by a maintainer at release time only)"]

    dev -->|"edits policy, runs upgrade / validate / resolve"| orqlet
    orqlet -->|"reads, validates"| policy
    orqlet -->|"renders pins (refresh time)"| gen
    gen -->|"read by"| clients
    clients -->|"select and run models (run time)"| dev
    dev -->|"copies requested and observed model into"| rec
    orqlet -->|"validates, derives independence"| rec
    dev -->|"opens pull request"| host
    owner -->|"approves catalog changes"| host
    host -->|"merge = approval evidence"| repo
    admin -->|"blocks models (Fable, others)"| clients
    vendors -.->|"maintainer rechecks seed each release; evidence files only"| policy
```

## Trust boundaries

- No new trust boundary of Orqlet's runtime and no new integration. A trust path does exist into the shipped seed: a person or an agent with web access reads vendor pages at release time (ADR-004); its controls are the seed tests and the review of the seed, and page text is evidence, never an instruction. Orqlet gains no network path: the vendor pages are read by a person or an agent with web access during the release step, and what reaches Orqlet is a reviewed edit of a file.
- `.orqlet/model-policy.yaml` and the review records are untrusted input to Orqlet (ORQLET-SEC-002): read through the `FileSystem` port, strict YAML, size limit, no value echoed in findings.
- The company's restrictions on the clients are outside Orqlet and are not generated or observed; Orqlet sees their effect only in a record's observed model (ADR-007).
