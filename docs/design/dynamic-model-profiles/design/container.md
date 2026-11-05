# Container view: where the change sits in Orqlet

The layers keep ORQLET-ARCH-001 (interface, adapters, application, domain; imports point inward). New or changed parts are marked.

```mermaid
flowchart TB
    subgraph interface["interface (CLI)"]
        c_up["orqlet upgrade / init / sync / doctor"]
        c_val["orqlet validate model-policy (new)<br/>orqlet validate review (changed)"]
        c_res["orqlet models resolve (new, read-only)"]
        c_rev["orqlet review prepare (changed)"]
    end

    subgraph adapters["adapters"]
        r_roles["render/roles.py (changed)<br/>render/skills.py (changed)"]
        r_clients["clients: claude_code, codex, cursor<br/>(unchanged; never import one another)"]
        r_seed["render/prompts_seed.py + seed for the policy (changed)"]
        a_git["git adapter: diff_patch with path exclusion (changed)"]
        a_fs["fs, process (unchanged)"]
    end

    subgraph application["application"]
        u_load["model_policy_source (new)<br/>strict load, size limit"]
        u_val["validate_model_policy (new)"]
        u_sel["model_selection (new)<br/>maps contract to domain, resolves"]
        u_req["render_request (changed)<br/>sets model_settings on roles and skills"]
        u_rec["validate_records (changed)<br/>review_prepare (changed)<br/>validate_plan (changed)"]
        contracts["contracts: model_policy v2 (new),<br/>review_result, plan, role_bindings (changed)"]
        ports["ports: instruction_adapter (ClientRole and<br/>ClientSkill gain model_settings), vcs (diff_patch exclude)"]
    end

    subgraph domain["domain (pure)"]
        d_res["model_resolution (new)<br/>precedence, constraints, reasons"]
        d_ind["independence (changed)<br/>observed identity, freshness, minimum by role"]
        d_idn["model_identity (new)<br/>normalise, match, exclude"]
    end

    subgraph pkg["workflow package (read-only data)"]
        w_roles["roles: orqlet-code-reviewer, orqlet-pr-writer (new)"]
        w_skills["skills: review, implement (changed)"]
        w_seed["seeds: model-policy.yaml (new, reviewed_for_release)"]
        w_rules["rules / MANIFEST.json (rebuilt)"]
    end

    files[("Project files<br/>.orqlet/model-policy.yaml, role-bindings.yaml,<br/>generated.lock.yaml, agent and skill files,<br/>docs/design/task/reviews/*.yaml")]

    c_up --> u_req --> ports
    r_clients --> ports
    r_clients --> r_roles
    a_git -->|"implements vcs port"| ports
    c_up --> u_load
    c_val --> u_val --> u_load
    c_res --> u_sel --> u_load
    u_req --> u_sel
    u_sel --> d_res --> d_idn
    u_val --> d_res
    c_val --> u_rec --> d_ind
    c_rev --> u_rec
    u_load --> contracts
    r_roles --> pkg
    r_seed --> w_seed
    u_load --> files
    r_clients --> files
    u_rec --> files
```

## Dependency notes

- `domain/model_resolution.py` takes plain values (tuples and dataclasses), as `derive_independence` does; the application layer maps the Pydantic contract into them. The domain imports nothing from the application (ORQLET-ARCH-002).
- Client adapters stay unchanged and independent: they already pass `ClientRole` and `ClientSkill` to `render/roles.py` and `render/skills.py`, and the selection travels on those two objects; the pin spelling for each client lives in the per-client functions there (ORQLET-ARCH-003). The selection type is defined in the ports module that holds `ClientRole`.
- The one adapter change outside rendering is the git adapter: `diff_patch` takes a path exclusion so the review packet's diff carries no earlier review record.
- The workflow package stays data: the two new roles, the changed skill text and the seed are files; the adapters and the interface read them.
- No container is added and none starts a process or opens a network connection.
