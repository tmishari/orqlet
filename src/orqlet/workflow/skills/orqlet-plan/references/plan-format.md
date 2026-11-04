# The implementation plan

`docs/design/<task>/plan.yaml` is the plan. The validator checks it against a projected tree: the repository at `base_revision`, with the operations of every phase that a phase depends on applied.

For each phase the plan holds the test plan first, then the implementation checklist. Detail scales with the change class.

## The test plan

- Each acceptance criterion is a scenario with its expected outcome. Its source is a `BC-n`, an `R-n` or a `Q-n` for new behaviour, or the AS-IS fact `A-n` for a regression that must keep working. It is never taken from code, including code written in an earlier phase. Its `check_ref` names one of the phase's checks or a review item.
- Each check has a `completion` entry that starts with the check's id. It gives the command as the project defines it, with every expression that the CI system or the shell expands replaced by a named placeholder, and its sources as `orqlet evidence cite` prints them (path, lines, revision and sha256): the lines that define it, the files the command directly invokes and the configuration lines it reads.
- A command that matches the warning list of `references/phase-contract.md` is marked in its `completion` entry and in the plan's self-check.
- A check whose command the project does not define is a question.
- Every `BC-n` of the design is covered by a criterion, or listed under `self_check.unverified` with a reason.

## The implementation checklist

After the test plan come the file operations with their exact paths and why each one changes, `depends_on`, and the `completion` entries. In the example, the phase lists its acceptance criteria and checks before its file operations.

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
    acceptance_criteria:
      - {id: AC-1, text: "Given a known customer id, create_order returns an Order for that customer", source: BC-1, check_ref: unit-tests}
      - {id: AC-2, text: "Given an unknown customer id, the existing lookup still raises its not-found error", source: A-3, check_ref: unit-tests}
    checks: [unit-tests]
    file_operations:
      - {op: create, path: src/pkg/service.py, why: The new function lives here}
      - {op: modify, path: src/pkg/__init__.py, why: Export the function}
    review_evidence: [architecture-reviewer, security-reviewer, tester]
    knowledge_step: required
    completion:
      - "unit-tests: `make test SUITE=<matrix.suite>` (.ci/pipeline.yml:40 at bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, sha256 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; it runs Makefile:12-14, sha256 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; it reads test.cfg:1-6, sha256 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa). Warning list: it fetches from the network."
    expected_outputs: [src/pkg/service.py]
reuse_decisions:
  - {candidate: billing-core, decision: not-applicable, reason: It has no order concept}
self_check:
  schema: orqlet.self-check/v1
  checked_against: {role: planner, phase: plan}
  checks:
    - {what: paths projected, how: "orqlet validate plan", result: pass}
    - {what: commands on the warning list, how: "unit-tests fetches from the network; its completion entry is marked", result: pass}
  unverified:
    - "BC-4: the wording of the error message is left to the review of the pull request"
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
