# The AS-IS file

`docs/design/<task>/as-is.md` is a Markdown file whose YAML front matter is the AS-IS artifact. The text after the front matter is not validated except for advice-like words; keep it empty or keep it a plain restatement of the facts.

There is no field for proposals, opinions, refactoring or future architecture, and the validator rejects one. Unknowns and contradictions do not count against `size_budget` and may not be dropped.

```yaml
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: sample-task
  status: draft
  workflow_version: 0.2.0
  protected_set_digest: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  bound:
    base_revision: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    standards_lock_hash: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    applicable_rules_hash: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    profile_version: 1
base_revision: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
scope: {paths: ["src/**"], request_ref: sample-task}
research_mode: sequential
limitation: The client has no subagents, so one agent researched the areas in turn.
size_budget: {max_words: 400}
facts:
  - id: A-1
    kind: structure
    statement: The CLI is assembled in one Typer application.
    evidence:
      - {path: src/orqlet/interface/cli/app.py, lines: 1-5, revision: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa}
unknowns:
  - {id: U-1, what: Which Git versions are supported, material: true, question_ref: Q-1}
contradictions:
  - {id: C-1, sources: [a.md, b.md], note: The two documents name different defaults}
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: researcher, phase: research}
  checks:
    - {what: references resolve, how: "orqlet validate as-is", result: pass}
```

Rules the validator checks:

- `header` is the common artifact header. `orqlet gate status` prints the values to copy.
- `base_revision` equals `header.bound.base_revision`.
- Every fact has at least one evidence entry whose `revision` is the base revision. Get the entry from `orqlet evidence cite <path> <lines>`.
- `research_mode` is `parallel-subagents`, `sequential-subagents` or `sequential`. Any mode other than parallel needs a `limitation` text.
- `merged_from` names fragment entries as `<fragment-id>/<entry-id>`.
- `self_check` is required. A `pass` check says how it was made.

## Evidence from the web

A page that you read outside the repository is evidence only after you write it down as a file `docs/design/<task>/evidence/web/<slug>.md` and cite that file like any other. The layout is a convention that the review of the pull request checks; no validator requires it.

```
# <title of the page>

URL: <the address that you read>
Retrieved: <the time, with a zone>
Tool: <the client tool that returned the text>
Processed: <yes if the tool ran the text through a model, no if not, unknown if it does not say>
Data class: <public or internal>

1. <label> - <an excerpt>
2. <label> - <an excerpt>
```

"Verbatim" is claimed only for text as the tool returned it. A summary in your own words is marked as a summary. A page behind a login is `Data class: internal`, is summarised with short quotations at most and is committed only after the person has said yes.
