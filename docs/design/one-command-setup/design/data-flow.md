# Data-flow view

## Install time

```mermaid
flowchart LR
    ind[Fixed indicators<br/>PATH names, folder names] --> det[Client detection]
    det --> plan[User-scope change plan]
    roots[(Roots and folder modes<br/>read-only)] --> insp[Root inspection<br/>RootState per prefix] --> plan
    pend[(Pending user journals<br/>read-only)] --> plan
    wf[(Workflow package<br/>skills · agents · foundation · hook entries)] --> render[Four client adapters<br/>user-scope render]
    render --> plan
    man[(user/manifest.json)] --> plan
    cur[(Current user files<br/>strict JSON for settings and hooks)] --> plan
    plan --> preview[Preview<br/>human or JSON]
    preview -- "--yes or person's yes" --> prep[prepare<br/>create · tighten · revalidate · pin]
    prep --> apply[apply_plan]
    apply --> bak[(user/backups)]
    apply --> jr[(user/journal)]
    apply --> files[(User client folders)]
    apply --> man
```

No data flows from `install` to a process or the network (Q-60).

## Session time

```mermaid
flowchart LR
    client[Assistant] -- "JSON payload, at most 1 MiB" --> hook[orqlet hook]
    hook --> val[Strict parse<br/>working-directory field]
    val --> find[Upward .orqlet/ search<br/>FileSystem port, no process]
    find --> st[Status use case, hook mode]
    lock[(Project lock and .orqlet)] --> st
    man[(user/manifest.json, if present)] --> st
    wf[(WorkflowSource: version, templates, foundation)] --> st
    st --> tpl[Fixed template<br/>validated versions, closed-set command, sanitized lock path]
    tpl --> ctx[Context, at most 1,200 characters<br/>plus packaged foundation for Copilot when no baseline]
    ctx -- "client output object, exit 0" --> client
```

No data flows from a hook to a file, a process, the network or a model. Repository content reaches the context only as a validated field of a fixed template (ORQLET-SEC-002, ADR-004 decision 1a).
