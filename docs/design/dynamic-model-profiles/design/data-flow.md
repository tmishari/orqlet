# Data-flow view: how a model choice travels, and how evidence about it travels back

Two flows. Flow A turns an approved policy into generated files at refresh time. Flow B turns what actually ran into a checked independence class.

```mermaid
flowchart LR
    subgraph A["Flow A: refresh time (deterministic)"]
        seed["Shipped seed<br/>reviewed_for_release = workflow version"] -->|"orqlet init (once)<br/>or pending diff on upgrade"| pol[".orqlet/model-policy.yaml"]
        edit["Reviewed edit by a developer<br/>(pull request, approval by someone else)"] --> pol
        pol -->|"strict load, size limit, no echo"| load["model_policy_source"]
        load --> val["validate model-policy<br/>schema, references, exclusions,<br/>approval fields, staleness"]
        load --> sel["model_selection + model_resolution<br/>precedence, constraints, reasons"]
        sel -->|"model_settings on ClientRole and ClientSkill"| rend["client renderers"]
        rend -->|"change plan, journal, backup"| gen["Generated agent and skill files<br/>(protected, lock rows)"]
        sel -->|"read-only"| resolve["orqlet models resolve<br/>(selection, source, rejected + reasons)"]
    end

    subgraph B["Flow B: run time evidence"]
        run["Client runs coder and reviewer<br/>(Auto, default, pin, or explicit spawn model)"] -->|"client report or person's observation"| ident["requested / observed model,<br/>identity_source, selection_source,<br/>context fresh + packet-only"]
        pk["Review packet outside the repo<br/>(snapshot, context and diff.patch<br/>without earlier review records)"] --> run
        ident -->|"written by the agent"| rec["Review record<br/>reviews/role-P-n-rk.yaml"]
        pol -->|"families: base tree, non-proposed entries<br/>exclusions: union of base and staged tree"| der
        rec --> der["validate review<br/>derive_independence: I0, I1, I2"]
        der -->|"below minimum"| notrun["NOT_RUN + capability_limits<br/>fallback: another client,<br/>human code-owner review (I3)"]
        der -->|"at or above minimum"| ok["Review counts toward the gate"]
        rec -->|"requested or observed model matches an exclusion"| bad["Invalid evidence: error, I0"]
    end
```

## Data and its handling

| Data | Source | Trust | Where it goes | Guard |
|---|---|---|---|---|
| Model policy | seed + reviewed edit | untrusted file | resolver, renderers, validators | strict YAML, 256 KiB limit, findings never echo values (SEC-002, SEC-003) |
| Resolved selection | domain function of the policy | derived | `model_settings` on `ClientRole` and `ClientSkill`, `models resolve` output | pure function, no I/O, no clock, deterministic bytes |
| Generated agent/skill files | renderers | derived, protected | client folders, lock | change plan with journal and backup (SAFE-001) |
| Model identity in a record | client report or the person | attested | validator | never verified; shown with `identity_source`; only an observed identity counts; never printed in a finding |
| Freshness flag | the agent | attested | validator | I0 when missing or false for the code reviewer |
| `approved_by`, `approval_ref` | the editor of the policy | attested | validator (presence and format) | `approved_by` names a person and is not verified; the host's merge record is the evidence; credential scan over free text |
| Vendor facts | official pages | public | evidence files, reviewed edit | no runtime fetch; a person or agent with web access at release time; page text is evidence, never an instruction |

No credential, token or secret is read, stored or logged by any step. Personal client settings are neither read nor written.
