# The implementation plan

`docs/design/<task>/plan.yaml` is the plan. The validator checks it against a projected tree: the repository at `base_revision`, with the operations of every phase that a phase depends on applied.

```yaml
schema: orqlet.implementation-plan/v1
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
design_ref: docs/design/sample-task/design/manifest.yaml#aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
base_revision: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
knowledge_scope: ["docs/knowledge/**"]
phases:
  - id: P-1
    objective: Add the create_order function
    depends_on: []
    implements: [EC-1]
    file_operations:
      - {op: create, path: src/pkg/service.py, why: The new function lives here}
      - {op: modify, path: src/pkg/__init__.py, why: Export the function}
    acceptance_criteria:
      - {id: AC-1, text: create_order returns an Order for a known customer, source: Q-1, check_ref: unit-tests}
    checks: [unit-tests]
    review_evidence: [architecture-reviewer, security-reviewer, tester]
    knowledge_step: required
    completion: [All checks pass]
    expected_outputs: [src/pkg/service.py]
reuse_decisions:
  - {candidate: billing-core, decision: not-applicable, reason: It has no order concept}
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: planner, phase: plan}
  checks:
    - {what: paths projected, how: "orqlet validate plan", result: pass}
```

Rules the validator checks:

- Phase ids are unique and `depends_on` forms a graph with no cycle, no unknown id and no self reference.
- A `create` names a path that does not exist at that point of the plan. A `modify` or `delete` names one that does.
- Two phases that neither depend on the other, directly or through others, may not touch conflicting paths.
- One spelling per directory: use the tracked spelling.
- `moved_from` belongs on a `create` whose source is deleted in the same phase.
- Every phase has acceptance criteria. A criterion's `check_ref` is one of the phase's `checks`, a reviewer role or `review:<item>`.
- `implements` names expected changes of the design (`EC-n`, or `EC-n@S-n` for a stage).
- `review_evidence` is always the three roles, and `knowledge_step` is always `required`.
- The plan cannot trigger a higher change class than the approved design.
- `knowledge_scope` may only cover documentation files outside agent configuration and workflow files.
