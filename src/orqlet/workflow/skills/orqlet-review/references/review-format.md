# A review record

`docs/design/<task>/reviews/<role>-<phase>-r<round>.yaml` is one review round of one role. It states the digest of exactly the inputs the reviewer examined, so that committing it does not change what it states.

```yaml
schema: orqlet.review-result/v1
task: sample-task
phase: P-1
role: architecture-reviewer
round: 1
verdict: FAIL
assurance: advisory
review_input:
  schema: orqlet.review-input/v1
  covers: [code_tests, knowledge, design, plan, standards, reviewer_definition, evidence_inputs]
  components:
    code_tests: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    knowledge: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    design: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    plan: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    standards: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    reviewer_definition: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    evidence_inputs: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  digest: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  merge_base: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
agent:
  binding_ref: orqlet-arch-reviewer
  definition_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  client: cursor
  model_requested: null
  model_observed: null
coder_binding: {client: cursor, model_requested: null, model_observed: null}
independence: I1
capability_limits: ["read-only is advisory"]
applicability:
  examined: [src/pkg/service.py]
  conclusion: findings
findings:
  - schema: orqlet.finding/v1
    id: F-1
    kind: finding
    severity: blocking
    category: tests
    evidence:
      - {kind: absence, searched: ["tests/**"], method: "searched test names", revision: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb}
    claim: The error path has no test.
    suggested_action: Add one.
    confidence: medium
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: architecture-reviewer, phase: implement}
  checks:
    - {what: packet read, how: "orqlet review prepare", result: pass}
```

Rules the validator checks:

- The path is exact: `<role>` is `architecture-reviewer` or `security-reviewer`, the phase is `P-n`, the round starts at 1 and has no gap. The task, phase, role and round in the file equal the ones in the path.
- `review_input` covers `code_tests`, `knowledge`, `design`, `plan`, `standards`, `reviewer_definition` and `evidence_inputs`, and its digest follows from its components. `orqlet review prepare` prints the block.
- `agent.binding_ref` is an approved binding for this role and client in `.orqlet/role-bindings.yaml`, and `agent.definition_sha256` is the hash of the agent definition file in the tree.
- `independence` cannot be higher than the recorded identifiers give: an approved binding is I1, a different client or model family from the Coder is I2. Nothing a record states can show a human reviewer (I3). An I0 review is never a PASS.
- A PASS holds no blocking finding. A FAIL holds at least one.
- `self_check` is required.

A finding:

```yaml
schema: orqlet.finding/v1
id: F-1
kind: finding
severity: blocking
category: failure-handling
rule_ref: ORQLET-SAFE-001
evidence:
  - {kind: quote, path: src/pkg/service.py, lines: 10-12, revision: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, quote_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa}
  - {kind: absence, searched: ["tests/**"], method: "searched test names for the error path", revision: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb}
claim: The error path of the service has no test.
suggested_action: Add a test for the failing call.
confidence: high
```

A finding needs evidence. A claim without evidence is an observation and never blocks. For something that is missing, the evidence is an absence record: what was searched, where, how and at which revision.
