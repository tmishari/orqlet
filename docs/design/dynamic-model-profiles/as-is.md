---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: dynamic-model-profiles
  status: approved
  workflow_version: 0.4.0
  protected_set_digest: b5d119f17890b8d7602c906b3325af7db4ef3d74fb31b8d697cdeeebfbb4be2d
  bound:
    base_revision: 0a280480edf5543b1907805a402c3ada930cf045
    standards_lock_hash: 89a225016ff9d8b3ed977df39a70dfbe9dbc5f7c6d3762d0f2208b1b7a037a52
    applicable_rules_hash: 56502a0ec5eda3b13b4c9d97c7d4dfa41df82c86a206e36dd5d2d92aab299b97
    profile_version: 1
base_revision: 0a280480edf5543b1907805a402c3ada930cf045
scope: {paths: ["src/orqlet/**", ".orqlet/**", ".prompts/**", "docs/design/**", "tests/**", "AGENTS.md", "README.md", ".github/workflows/**", ".claude/**", ".cursor/**", ".codex/**", ".agents/**"], request_ref: dynamic-model-profiles}
research_mode: parallel-subagents
size_budget: {max_words: 4500}
facts:
  - id: A-1
    kind: structure
    statement: "The workflow package manifest lists five role sources (orqlet-arch-reviewer, orqlet-inventory, orqlet-security-reviewer, orqlet-tester, orqlet-tracer) and none named orqlet-code-reviewer or orqlet-knowledge-writer."
    evidence:
      - {path: "src/orqlet/workflow/MANIFEST.json", lines: "37-53", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: d62bd95f1d986b61bf7194658560a0c62218b3d62739b826200fbcce6c15118c}
  - id: A-2
    kind: structure
    statement: "The manifest lists six skill sources: orqlet-design, orqlet-implement, orqlet-onboard, orqlet-plan, orqlet-research and orqlet-review."
    evidence:
      - {path: "src/orqlet/workflow/MANIFEST.json", lines: "221-265", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f52e5caaf43b0a4f7202ee6287fa7025a23433e50423e4cc34453c4ba5498bb3}
  - id: A-3
    kind: structure
    statement: "orqlet-tester is defined with `mode: writes` and orqlet-tracer with `mode: read-only`; the other three roles are read-only in the same lines of their files."
    evidence:
      - {path: "src/orqlet/workflow/roles/orqlet-tester.md", lines: "2-4", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 3424b8d6ac959c93da6dd5ef35f30daccb37fbf0510b45d3b6ad036d748a222d}
      - {path: "src/orqlet/workflow/roles/orqlet-tracer.md", lines: "2-4", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: a23dcfeebebd62936bdb06fee4028968f960d31ded9073ad431a69ce32520a32}
  - id: A-4
    kind: interface
    statement: "load_roles requires `name`, `description` and `mode` in a role source, accepts only `read-only` or `writes`, and sets read_only to true exactly when mode is `read-only`."
    evidence:
      - {path: "src/orqlet/application/usecases/workflow_sources.py", lines: "151-166", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: b6fa2b893c0bd33ac9dc992e04a253b0fdcdb05cee0b247f9f887dd202f6a3cb}
  - id: A-5
    kind: interface
    statement: "parse_source raises SourceError for any front-matter key outside the required list and no caller passes an optional list, so a `model` key in a role or skill source file is refused."
    evidence:
      - {path: "src/orqlet/application/usecases/workflow_sources.py", lines: "47-48", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c89b7b0cb538b53c66d6b2aef41dfc62d98dcba6f5b661d6f63afc49699c3076}
  - id: A-6
    kind: interface
    statement: "load_skills never sets agent_may_start, so every packaged workflow skill takes the default False and renders with `disable-model-invocation: true`."
    evidence:
      - {path: "src/orqlet/application/usecases/workflow_sources.py", lines: "115-136", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 89456c1c48d176696333a85ee0686bafb9fc5bb9ceabfd12c3a237cb4befa2f7}
  - id: A-7
    kind: interface
    statement: "ClientRole, the only input a role renderer receives, has name, description, body, read_only and inputs, with no model, reasoning-effort or tools field."
    evidence:
      - {path: "src/orqlet/application/ports/instruction_adapter.py", lines: "73-80", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 98bad889ed5cdf57c96ff053db122db0d75bccd2d0680d37ff20b1c2af127a0b}
  - id: A-8
    kind: interface
    statement: "RenderRequest, the input of every client adapter, holds workflow_version, baseline_body, scoped_rules, commands, skills, roles, client_version, conventions and integrations, with no model-policy or role-binding field."
    evidence:
      - {path: "src/orqlet/application/ports/instruction_adapter.py", lines: "91-103", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 0390e00202f941d274ca668ff003a306ffe11e0465a16d7a66584a6b92566416}
  - id: A-9
    kind: interface
    statement: "claude_role writes name, description, `tools: Read, Grep, Glob` for read-only roles, and the literal `model: inherit` into .claude/agents/<name>.md."
    evidence:
      - {path: "src/orqlet/adapters/render/roles.py", lines: "20-28", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: cb1dbe52ae01d1c0b42daeb83fe60527f65806a532d725b8b5f467d2e5d3df5d}
  - id: A-10
    kind: interface
    statement: "cursor_role writes name, description, the literal `model: inherit` and `readonly: <bool>` into .cursor/agents/<name>.md."
    evidence:
      - {path: "src/orqlet/adapters/render/roles.py", lines: "31-38", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 42f2cfa8e5e1ceb05bfa5adf98e39e3786fb240f4c0c0b8c9d74794843ff13ca}
  - id: A-11
    kind: interface
    statement: "codex_role writes name, description, `sandbox_mode = \"read-only\"` for read-only roles and developer_instructions into .codex/agents/<name>.toml, and writes no model key."
    evidence:
      - {path: "src/orqlet/adapters/render/roles.py", lines: "41-46", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2dab8767386e2d4f550332963dd6d6404cca2905f88a7fe6cd49c17488a6f1f6}
  - id: A-12
    kind: interface
    statement: "The roles.py docstring says a role file never names a vendor model, that `model: inherit` leaves the choice to the developer, and that a read-only role uses the strongest control each client documents, including `sandbox_mode = \"read-only\"` in Codex."
    evidence:
      - {path: "src/orqlet/adapters/render/roles.py", lines: "1-6", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 350aec552ab0042c112bc99c44f8218748a99a6ab22915fc7d4a4d6831548d1e}
  - id: A-13
    kind: interface
    statement: "The skill renderer writes front-matter name and description and adds `disable-model-invocation: true` when agent_may_start is False; it writes no model, tools, readonly or reasoning-effort field."
    evidence:
      - {path: "src/orqlet/adapters/render/skills.py", lines: "47-55", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: fac8e021e7212629062488717c40fcd0a913beacec28e249e7f2875943510fa8}
  - id: A-14
    kind: interface
    statement: "codex_sidecar writes .agents/skills/<name>/agents/openai.yaml containing `policy: allow_implicit_invocation: false`."
    evidence:
      - {path: "src/orqlet/adapters/render/skills.py", lines: "36-44", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 111349e881fb22bb8e259bd196b09503ae327ee134f2af8b97a32063a923dc70}
  - id: A-15
    kind: flow
    statement: "The three client adapters render AGENTS.md blocks, rules, skills and agent files (Claude Code also .mcp.json when an integration server is registered) and no settings, config.toml or model file."
    evidence:
      - {path: "src/orqlet/adapters/clients/codex.py", lines: "58-64", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 8716b901a469be02f186ce8e7f3a23d25f22569ff35018b7a1e42642778e493e}
      - {path: "src/orqlet/adapters/clients/cursor.py", lines: "45-57", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 65dbf78ae758796ac51570e8187cc413f39317bc6e3d5f75adc0ef3ab47180fb}
      - {path: "src/orqlet/adapters/clients/claude_code.py", lines: "61-72", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 9ca4f96798261f895b06769ef5f28b7ef2d362d862d4bf51c0b6adcd74e8a55e}
  - id: A-16
    kind: flow
    statement: "build_render_request fills roles with load_roles(workflow) and takes no model-policy or role-binding input."
    evidence:
      - {path: "src/orqlet/application/usecases/render_request.py", lines: "110-119", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 935ee90a440cd4d145a599421f40e46ee76c28b105556ff95c69e080bde2ce81}
  - id: A-17
    kind: flow
    statement: "compose builds one RenderRequest, calls each enabled client adapter's render with it, merges the files and converts them to desired files."
    evidence:
      - {path: "src/orqlet/application/usecases/render_all.py", lines: "121-134", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 005337127e567fc1b7edcfeee8d6e0b2eac678caf52fc2c87d39d5c8bdad0b96}
  - id: A-18
    kind: flow
    statement: "upgrade resolves the installation, composes the files of the enabled clients and plans the changes against the recorded lock before any write."
    evidence:
      - {path: "src/orqlet/application/usecases/upgrade.py", lines: "117-138", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c982029d296a2d135bc5b9c1f19da45ce1c161789c7cc6a07ea4eb470253cdcf}
  - id: A-19
    kind: flow
    statement: "A tampered protected file gets warning ORQ-W096 and the planned RESTORE write replaces it with the new render once the plan is approved."
    evidence:
      - {path: "src/orqlet/application/usecases/upgrade.py", lines: "322-332", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: ea3da8fc637fa7553f8348a3d27c3db65729321250ba8ce4216065b8c84548e7}
  - id: A-20
    kind: flow
    statement: "apply_plan is the single writer: it holds a lock, saves backups, journals the plan, writes in order with the manifest last and then finishes the journal."
    evidence:
      - {path: "src/orqlet/application/usecases/apply_plan.py", lines: "49-79", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 01b3dc44961a1d4762d7ace233bc9aaf4f043f2e92add23bd6efa776b430bc3a}
  - id: A-21
    kind: flow
    statement: "A change to a seeded or colliding file is written as a unified diff file in a subfolder of .orqlet and not as a write."
    evidence:
      - {path: "src/orqlet/domain/changeplan.py", lines: "378-391", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: afff31f07d120614cf30fce59fadefe5a9e7d329e03d66d157fa60ca95b07765}
  - id: A-22
    kind: flow
    statement: "init seeds .orqlet/role-bindings.yaml once with one binding per entry of REVIEW_AGENTS, which holds exactly the architecture and the security reviewer, for all three clients."
    evidence:
      - {path: "src/orqlet/application/usecases/render_all.py", lines: "67-71", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 6d09052104bf94653e66fc1820b5a9d5e7c0c03abbf6e53ea7bb773f0c3a499f}
      - {path: "src/orqlet/application/usecases/render_all.py", lines: "230-244", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 0882bdbe5c0f8e3c3a9aff42546d27a5e9ced448d65e55ccba948e7cda18d26f}
  - id: A-23
    kind: structure
    statement: "The lock records the Claude Code, Codex and Cursor agent files of orqlet-arch-reviewer each with owner orqlet, class protected, one input roles/<name> at version 0.4.0 and a rendered_sha256; the role input digest is the same for the three clients."
    evidence:
      - {path: ".orqlet/generated.lock.yaml", lines: "174-181", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: dc5c0d97563b9803790d71132ddae5d3e90d2a47318b9adbe0afaaf61255a760}
      - {path: ".orqlet/generated.lock.yaml", lines: "454-461", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: b081f030a56675e0ea0ae0d1ddc4c1e1c78748c7decc7d45ffa2e41d94e3402b}
      - {path: ".orqlet/generated.lock.yaml", lines: "494-501", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: b20faedbbae3faf08e6c065bd9ecab8748179e6f2d9336a7c58aa687f96108f3}
  - id: A-24
    kind: structure
    statement: "The lock records .orqlet/project-profile.yaml, role-bindings.yaml and versions.yaml with owner seeded and standards.lock.yaml with class generated, and holds no model-policy.yaml entry."
    evidence:
      - {path: ".orqlet/generated.lock.yaml", lines: "673-702", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c304c85b314a43cf9f48af2a7655fdb47ce6b7ad66aed3f0b9bc72f84cdcfa43}
  - id: A-25
    kind: operation
    statement: "protected_set_digest is a SHA-256 over the sorted [path, rendered_sha256] pairs of every protected lock row, with no field-level exclusion."
    evidence:
      - {path: "src/orqlet/application/usecases/gate_status.py", lines: "70-77", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 02c727f331b6b5599015b32067b509ec3a82bc6986cbe4ce5a0b176b5b9b703a}
  - id: A-26
    kind: flow
    statement: "doctor and sync compare the on-disk hash of each non-seeded file with the sha256 recorded in the lock and not with a fresh render; a protected mismatch is ORQ-E150."
    evidence:
      - {path: "src/orqlet/application/usecases/diagnose.py", lines: "78-114", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: ab41ce823ab6535da4898d27c708c4ffced0f3ba6b23fa9d292217dba9eb4880}
  - id: A-27
    kind: structure
    statement: "The generated workflow rule says a protected file that differs from the render of the pinned release fails review and that a generated file is changed at its source, followed by `orqlet upgrade`."
    evidence:
      - {path: "src/orqlet/workflow/rules/orqlet-workflow.md", lines: "5-6", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 00918e178b010b70106b20df45cfa10251fc826836b1ae820165f729662416fc}
  - id: A-28
    kind: test
    statement: "A golden test compares every generated file of the three adapters, role files included, byte for byte with tests/golden/<client>/docs-2026-10/<path>."
    evidence:
      - {path: "tests/unit/render/test_clients_golden.py", lines: "37-44", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 541bea6523530205a279865465797d89a49f81a4afb4e86c17855206f8dda3cc}
  - id: A-29
    kind: test
    statement: "The golden role files hold `model: inherit` for Claude Code and Cursor and no model key for Codex, which holds `sandbox_mode = \"read-only\"`."
    evidence:
      - {path: "tests/golden/claude-code/docs-2026-10/.claude/agents/orqlet-arch-reviewer.md", lines: "1-6", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: eff2bdc6b8174e62205963a08c9153815cf97340615d3aaa7cd4cf175948452f}
      - {path: "tests/golden/cursor/docs-2026-10/.cursor/agents/orqlet-arch-reviewer.md", lines: "1-6", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: aebbf6ac76dc3b401fb1b4fc62df5d1baf0d6ff7f750886792bee990970e2642}
      - {path: "tests/golden/codex/docs-2026-10/.codex/agents/orqlet-arch-reviewer.toml", lines: "1-5", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 7cb4a29dedb355740d7295c940a8f4fc396acb71b955db7d1163908bd41706f2}
  - id: A-30
    kind: test
    statement: "test_role_files_never_name_a_vendor_model fails when a rendered role file of any client contains `gpt-`, `claude-`, `sonnet`, `opus`, `haiku` or `gemini`."
    evidence:
      - {path: "tests/unit/render/test_skills.py", lines: "488-493", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2a76c6cde913a4ee397d41077c9bf2518ab38e6f4637fbfde23da979e88eedc0}
  - id: A-31
    kind: test
    statement: "A test asserts that `model: inherit` is a line of the Claude Code and the Cursor file of every packaged role."
    evidence:
      - {path: "tests/unit/render/test_skills.py", lines: "450-459", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 6c7f9fa8a5c18c4fd3e4fb527823c74fcdf31b790605bc9ccbb97c9ea0acd3db}
  - id: A-32
    kind: test
    statement: "The lookup-text test lists Claude, Anthropic, Cursor, Codex and OpenAI among product names that no baseline text or skill step may carry."
    evidence:
      - {path: "tests/unit/test_workflow_lookup_text.py", lines: "45-61", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: cb184329f404e966409c7cd3037beb22cc039fc7e7ff59b87259d62ac1f09b65}
  - id: A-33
    kind: interface
    statement: "ModelPolicy has schema, policy_version, status (draft or approved), owner, compatibility, data_classes, models, excluded, reviewed_at, max_age_days, profiles and roles."
    evidence:
      - {path: "src/orqlet/application/contracts/model_policy.py", lines: "70-82", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: aea6815569fc9129b41558324140f97d6885116f5f07e92c8f4983f0aad80c45}
  - id: A-34
    kind: interface
    statement: "A Route has route_id, executor (claude-code, codex or cursor), provider, runtime_id, alias, rank, price_rank, retires_on, options, locality, data_handling, observability and enabled."
    evidence:
      - {path: "src/orqlet/application/contracts/model_policy.py", lines: "35-48", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 7a448921778fad7823ff4fedd2cc64e48bfac9b2fd170b0058fd11afef8600b3}
  - id: A-35
    kind: interface
    statement: "ModelEntry has logical_id, a status with four values (including approved and retired), approved_by, supports and routes; ModelProfile has id, prefer (rank or price_rank), requires (independence_from_roles only) and candidates."
    evidence:
      - {path: "src/orqlet/application/contracts/model_policy.py", lines: "51-56", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 8cc15bb7e9519c7135d9c2868b7d79b077c9a5240b5d2293802543695ac59664}
      - {path: "src/orqlet/application/contracts/model_policy.py", lines: "59-67", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 81e8e31b000b62afc734fed3cdb40a3939d4ff90e4845c51c3aece7260bde753}
  - id: A-36
    kind: interface
    statement: "ModelPolicy.excluded is a flat tuple of strings and ModelPolicy.roles is a mapping of role name to profile id."
    evidence:
      - {path: "src/orqlet/application/contracts/model_policy.py", lines: "78-82", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: ed3712f45952f0b3d009989b8dc9c00d9049aaa376fc1f57768f4d7e16675017}
  - id: A-37
    kind: interface
    statement: "The built contract has no discovered, approval, callable, evaluated, availability, fallback or escalation field and declares no validator, so it checks no cross-reference among profiles, candidates, models, roles and excluded."
    evidence:
      - {path: "src/orqlet/application/contracts/model_policy.py", lines: "1-82", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 59d7837f2fd220064fcfa6416708721e96a998f4e11f2dc2d47d3d5bb7d39edb}
  - id: A-38
    kind: dependency
    statement: "ModelPolicy is registered under `orqlet.model-policy/v1` in the contract registry and no other module in src references it."
    evidence:
      - {path: "src/orqlet/application/contracts/__init__.py", lines: "13-41", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f8ded7024a8c0ec89dc07ecd9b34308ce663844de629cdb4191339d5a7f2e56f}
  - id: A-39
    kind: test
    statement: "The only model-policy instance in the repository is a contract-test fixture with status draft, one model, one claude-code route with alias `opus`, one profile `strongest` and `roles: {architecture-reviewer: strongest}`."
    evidence:
      - {path: "tests/fixtures/contracts/valid/orqlet.model-policy.v1.yaml", lines: "1-13", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 7fea94cdbe50309f5047514f9f1b82a26a0a82d96739f6ceffca2e09159466c0}
  - id: A-40
    kind: structure
    statement: "The path constants of the render step name the profile, lock, versions, role-bindings, standards lock, workflow lock, released and knowledge files and no model-policy file."
    evidence:
      - {path: "src/orqlet/application/usecases/render_all.py", lines: "59-66", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 54ed8b86a91e287cfa77ef64f13e6d9206bfe12fa1a5136813f6621945a22a32}
  - id: A-41
    kind: interface
    statement: "ProjectProfile has no `model_policy` key and no other key about model policy."
    evidence:
      - {path: "src/orqlet/application/contracts/profile.py", lines: "155-172", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c4391248f015f13beb54a3eca54af4d37bcd9bbd8be948c8f40332923ee22440}
  - id: A-42
    kind: interface
    statement: "The CLI registers init, upgrade, rollback, sync, doctor, explain and release and the groups profile, resources, conventions, standards, validate, gate, evidence, knowledge and review; no models, admin, hook or ci command is registered."
    evidence:
      - {path: "src/orqlet/interface/cli/app.py", lines: "36-51", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 26b324bc349a62978f2f946e3888a16e0c88291cf8af7e1c0e6334f1caa4abae}
  - id: A-43
    kind: interface
    statement: "`validate` registers nine sub-commands (as-is, design, plan, ledger, resources, integrations, review, test, knowledge); none validates a model policy or a role-bindings file."
    evidence:
      - {path: "src/orqlet/interface/cli/commands/validate.py", lines: "51-199", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f6622503c959b1f41b19a53810780ddac73ecfbd1b250cd8a437565d06541962}
  - id: A-44
    kind: operation
    statement: "The CI workflow defines the jobs lint, types, architecture, tests and build, and none runs an `orqlet validate`, `orqlet gate` or `orqlet review` command."
    evidence:
      - {path: ".github/workflows/ci.yml", lines: "18-100", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: a1556be44d856dc7f0c10ec4948c92ec1f2b10449ca0af5d4b1e5bb28582904a}
  - id: A-45
    kind: interface
    statement: "RoleBindings has bindings (role limited to architecture-reviewer and security-reviewer, minimum_capability, independence_capability I1, I2 or I3, definition_sha256, approved_by), model_families and not_accepted_for_review_roles."
    evidence:
      - {path: "src/orqlet/application/contracts/role_bindings.py", lines: "12-38", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 896d399d4ee864afda20f0108aeb8ffcd65b655e6c49c630f34039c68534528f}
  - id: A-46
    kind: structure
    statement: "The repository's role-bindings.yaml binds orqlet-arch-reviewer and orqlet-security-reviewer for claude-code, codex and cursor at independence_capability I1 and holds `model_families: []` and `not_accepted_for_review_roles: []`."
    evidence:
      - {path: ".orqlet/role-bindings.yaml", lines: "1-27", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 6f8356c02488c77e5db488921a457ea147d78af81ab181772d20e14aec5ce8b6}
  - id: A-47
    kind: flow
    statement: "The only code that reads role-bindings.yaml approves a binding by the record's binding_ref, role and client and reads model_families."
    evidence:
      - {path: "src/orqlet/application/usecases/validate_records.py", lines: "306-315", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: de6c63531ee02cc9649886c9baed3bd7b39952f21aad00b5356c35736cf46809}
  - id: A-48
    kind: flow
    statement: "No code reads minimum_capability, independence_capability, not_accepted_for_review_roles, a binding's definition_sha256 or its approved_by."
    evidence:
      - {path: "src/orqlet/application/contracts/role_bindings.py", lines: "22-38", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 4292caa57a51e2f2997335323f087b239b0be98a51bc669b3ebf79d77e6e9afd}
  - id: A-49
    kind: flow
    statement: "derive_independence returns I0 for an unapproved binding, I2 when the agent's client differs from the coder's or both known model families differ, and otherwise I1; it never returns I3 and takes no input about context freshness."
    evidence:
      - {path: "src/orqlet/domain/independence.py", lines: "39-54", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 0f6e129a000f29b69ca11f4536db7323cf4225f6ca7e3fe083fc100216c1989d}
  - id: A-50
    kind: flow
    statement: "family_of maps a model id to a family by the first matching `model_families` pattern, and the validator takes the id from model_observed or else model_requested; with the repository's empty list every family is None."
    evidence:
      - {path: "src/orqlet/domain/independence.py", lines: "29-36", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 7c4e223c1f1a6bb87e78cd28d50d1cb52986ea8b77a49c0d2a1984ede871d126}
      - {path: "src/orqlet/application/usecases/validate_records.py", lines: "315-325", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 309024d9b0b24483005521a33d909304874cce0cc0700ca0944b3595e4c29fdf}
  - id: A-51
    kind: interface
    statement: "AgentBinding holds binding_ref, definition_sha256, client, model_requested and model_observed; CoderBinding holds client, model_requested and model_observed."
    evidence:
      - {path: "src/orqlet/application/contracts/review_result.py", lines: "31-42", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 8b89ce4b8e935c3448bcab41dff283200b2c8cad469fa157d8ec7a157960baea}
  - id: A-52
    kind: interface
    statement: "ReviewResult.role and the review-record path pattern admit only architecture-reviewer and security-reviewer, and a plan's review_evidence is exactly architecture-reviewer, security-reviewer and tester; no code-reviewer value exists."
    evidence:
      - {path: "src/orqlet/application/contracts/review_result.py", lines: "63", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: aae13a0e6a92d876116f37a5ae095edb7a831d0d958c1defe9fc8c5920e07e6e}
      - {path: "src/orqlet/domain/evidence_artifacts.py", lines: "26-27", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 99887c0b0c50f2f57f133d8553370bf5ade48e9d0c0c78706257e4bf234133de}
      - {path: "src/orqlet/application/contracts/plan.py", lines: "44-58", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 770da723571bd48330c33d9987ce6688f75a3ce2b6a9e51b86b58272c5fd48db}
  - id: A-53
    kind: flow
    statement: "A derived independence class below the minimum (I2 for D3, I1 otherwise) is a skipped check and gives NOT_RUN, not an error."
    evidence:
      - {path: "src/orqlet/application/usecases/validate_records.py", lines: "344-366", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 8f86f5944c77441e2d7c1fbeb014d53d2a93b345a6ed9404575da93e894e8c7d}
  - id: A-54
    kind: flow
    statement: "An unapproved binding is reported as the error ORQ-E415, which gives FAIL, and a claimed class above the derived class is ORQ-E412."
    evidence:
      - {path: "src/orqlet/application/usecases/validate_records.py", lines: "299-341", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 3bdb18119ea5bcb705a0e9c8f1d976fe3065299cbdfaceb75e47add3a16e82e4}
  - id: A-55
    kind: flow
    statement: "A review whose recomputed components differ from the recorded ones is ORQ-W410 and NOT_RUN; the reviewer_definition digest covers the role text and the agent file bytes, which include the `model: inherit` line."
    evidence:
      - {path: "src/orqlet/application/usecases/validate_records.py", lines: "142-148", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: cb7d91386285967d10e1f93b446b4093b91476bd6953c33f9470c12bcf3f5ff9}
      - {path: "src/orqlet/application/usecases/binding_inputs.py", lines: "365-383", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: ce03855a3cf42179b27bbc82f5abd89435dabe6e1d759b37123fe4053ae0c27d}
  - id: A-56
    kind: structure
    statement: "The binding components are code_tests, knowledge, design, plan, standards, reviewer_definition, evidence_inputs and candidates; none names a model, a model policy or a client, and a review covers the first seven."
    evidence:
      - {path: "src/orqlet/domain/binding.py", lines: "21-47", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 158d07a0829ed8c5cbc137472200ee551c31e502bafee55306b860841e81825d}
  - id: A-57
    kind: flow
    statement: "gate status re-checks the base revision, standards lock hash, applicable rules hash, profile version, workflow version and protected-set digest, and no model or role-binding value."
    evidence:
      - {path: "src/orqlet/application/usecases/gate_status.py", lines: "48-67", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 8f94287d743370da1ec0dd67025ef5114a484cd6f82bcdf483bb44482a7d6be7}
  - id: A-58
    kind: flow
    statement: "review prepare takes its reviewer agents from a hard-coded DEFAULT_REVIEWERS map and does not read role-bindings.yaml."
    evidence:
      - {path: "src/orqlet/application/usecases/review_prepare.py", lines: "44-47", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 6c7cf8ddacfaca247e761769aee2b396ada0e4dde74be303ff8328baf2d99e80}
  - id: A-59
    kind: structure
    statement: "The review packet holds snapshot/ copies of the tracked files, diff.patch and context copies of the plan, design manifest, AS-IS, test and knowledge-impact records and standards files, and its MANIFEST.json holds no model or client field."
    evidence:
      - {path: "src/orqlet/application/usecases/review_prepare.py", lines: "110-147", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 68066283cf0f3b74ecc835c02dee07ed37b12b9a625b3595821dc7d89e7c4608}
      - {path: "src/orqlet/application/usecases/review_prepare.py", lines: "151-179", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2c2483932fc484714b6a56999c74758f2db12392ba4bf8bd43f7bc840c99b97f}
  - id: A-60
    kind: structure
    statement: "Packets are written under a packets folder in the user data directory and never inside the repository."
    evidence:
      - {path: "src/orqlet/interface/cli/wiring.py", lines: "74-87", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 394029b23cbdc63f4228323a6487b5da93a759bf0ffdcb97edaf28826cdbdd0a}
  - id: A-61
    kind: structure
    statement: "TesterRecord has no client or model field."
    evidence:
      - {path: "src/orqlet/application/contracts/test_record.py", lines: "30-38", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 9e72cfe163a5342833aa7a7aaa4bb1c7cad1b4fdf3804adb2799ab60b20ea109}
  - id: A-62
    kind: flow
    statement: "The review skill starts orqlet-arch-reviewer and orqlet-security-reviewer as typed subagents in a clean context with the packet path and nothing else, says a subagent that inherits the conversation is a fork, reports NOT_RUN when the client cannot start subagents, and has no step about a model, the coder's binding or the independence class."
    evidence:
      - {path: "src/orqlet/workflow/skills/orqlet-review/skill.md", lines: "25-33", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 21378439ff96e8821c2e87b1638dfdb442e6a6c09c85331b56c1f0b5b2c46844}
  - id: A-63
    kind: structure
    statement: "The reviewer role text says the reviewer receives only the path of a read-only packet and not the Coder's conversation, memory or reasoning."
    evidence:
      - {path: "src/orqlet/workflow/roles/orqlet-arch-reviewer.md", lines: "4-6", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 917bf73610a155e35b5ed03c3607553747d957d1c91c3dbba6b3a8964d34eda9}
  - id: A-64
    kind: operation
    statement: "A harness2-fit security review record states that the packet snapshot held earlier design-phase review notes and that the reviewer opened one, so the review was not fully context-clean."
    evidence:
      - {path: "docs/design/harness2-fit/reviews/security-reviewer-P-1-r1.yaml", lines: "84", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f68e51100286bdb191dc50c96c4c3b6c7f4bafecbef5978e1e1cc85d46b07775}
  - id: A-65
    kind: operation
    statement: "A review record with independence I2 names agent client codex and coder client cursor, holds null model_requested and model_observed, and states that the reviewer did not report its model identifier; a search of docs/design/**/reviews/*.yaml finds 112 records, 108 with I1 and 4 with I2, and no non-null model field."
    evidence:
      - {path: "docs/design/phase-skill-contracts/reviews/security-reviewer-P-1-r3.yaml", lines: "28-44", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 1051af69636e62dd47ee401cb68fc00578dd9f5096ce15e0753f4f69105ded06}
  - id: A-66
    kind: operation
    statement: "The harness2-fit AS-IS records that in a Cursor session of 2026-10-23 the client reported that a subagent's configured model \"inherit\" was blocked by the team's admin settings and that every launched subagent ran on claude-sonnet-5-5-xhigh instead."
    evidence:
      - {path: "docs/design/harness2-fit/as-is.md", lines: "232-240", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e736f14241ed20a56e455399807e1a1283b441bc2e4a1f70a31bffec460aa226}
  - id: A-67
    kind: structure
    statement: "AGENTS.md (baseline block, team text and conventions block) contains no statement on reviewer independence, fresh context for reviewers, model selection, model pins or tiers; its only 'Reviewers' text is the pull-request convention."
    evidence:
      - {path: "AGENTS.md", lines: "1-88", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 320c861b43e3c72d227b49a1ae9404291f006bed7e636703cd5d3bf1b01a732b}
  - id: A-68
    kind: structure
    statement: "ORQLET-NOMODEL-001 (MUST, review) says Orqlet never calls a language model, takes a prompt or starts an agent, prepares context for the IDE agent and validates the agent's output, and adds no model SDK dependency."
    evidence:
      - {path: ".prompts/rules.yaml", lines: "74-79", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 56f15f1c2db602e765a02f67c3d4fb7934872ff76df516776f0d9ab1ae4d1b68}
  - id: A-69
    kind: structure
    statement: "The team rules (ORQLET-ARCH, SEC, SAFE, NOMODEL, DET, TEST, QA and STYLE) hold no rule on model selection, pins, profiles or reviewer independence."
    evidence:
      - {path: ".prompts/rules.yaml", lines: "10-143", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 142ae5648aebc80392d9af49d5a108ecfc471081d0865293d7715699aa88fa0e}
  - id: A-70
    kind: structure
    statement: "README says the skills start four read-only subagents and a tester, that a same-client review gets independence I1, that a D3 change needs I2 and that a different model family counts only when role-bindings.yaml lists the families."
    evidence:
      - {path: "README.md", lines: "321-333", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 43dcc4e0cbf1e45c7420c64e7db56be95c8a486ed1ef23305d3e24a2be2500dd}
  - id: A-71
    kind: operation
    statement: "The architecture document's header says v0.5 was approved by the person on 2026-10-25 in conversation ('I approve all'), that this is not a merged pull request so no gate has evidence of it, and that no part of this version has been independently reviewed."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "5", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 00fb4e5c23bd0f48549cd4ed1327755a48be4ee07df55a6869e1b6a54c7c6b73}
  - id: A-72
    kind: structure
    statement: "The architecture document's label legend defines [R] as not approved, [P] as a name or schema that is not yet an existing API, [DC] as developer-confirmed, [U] as unknown and [D] as documented, and says untagged content of sections 6 to 25 is not approved design text."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "19-33", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 53cbe107064760a2d9c13fca05400754b5c58319600047acf662f3bfbf97c5e1}
  - id: A-73
    kind: structure
    statement: "The architecture document states that section 14.9 (per-role model profiles and the governed refresh) was added after the independent reviews and still has no independent review."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "2499", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 20ac7b8c43ae7f1dd3cb1df53bb4f1c89f7659664ff3a4151104f4efd0887e54}
  - id: A-74
    kind: flow
    statement: "Section 14.1 says Orqlet cannot choose a model while a developer works but can carry tier hints, render per-role pins from an approved policy and produce administrator exports; section 14.2 separates metadata discovery, company approval, callable verification (deferred) and role suitability."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "2443-2460", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 7a15edcafb24ad303cc490189efea98015ce486db2b729bfaddfc871a79e4169}
  - id: A-75
    kind: flow
    statement: "Section 14.9.1 [R] says subagent roles get a pin rendered only through `orqlet upgrade`, that `orqlet sync` never writes a pin, and that main-agent roles (coordinator, synthesizer, architect, planner, coder) are never pinned because whether a project file can set the session model was not researched [U]."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "2501-2508", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 71c08d4679579bf85834aa1cdd54c3a0505a0ffe49385c720e62f1b2a7303175}
  - id: A-76
    kind: flow
    statement: "Section 14.9.2 sets the pin-rendering rule: candidates are enabled, approved, non-retired, non-excluded routes with an alias or runtime_id; the profile prefers rank or price_rank as supplied by the owners; a required role with no candidate gets no pin and a NOT_RUN gate; a pin change makes a review role's evidence stale."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "2510-2521", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c4f8524e65f068e46f5effb8a6cec6b3981fa7c0cee3ad7a8030266bc1f3660f}
  - id: A-77
    kind: flow
    statement: "Section 14.9.3 and 14.9.4 describe an opt-in `orqlet models refresh` that reads client metadata and writes only a diff file, say a vendor's alias movement is not a reviewed configuration change, and exclude run-time selection and callable verification."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "2523-2540", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 581a3ed8bd0cb675adee0465732ff9e3b84fc452c1cbb4553b58df8eebddb140}
  - id: A-78
    kind: operation
    statement: "Section 14.3 states that Fable is excluded [DC], that the design infers (not verified) that it is Claude Code's `fable` alias, and that generated managed-settings output must not list Fable."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "2468", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f97cf8378d5315bcd01a8a0a02bbafd3a4b39154044e60ad9a9150789976e216}
  - id: A-79
    kind: structure
    statement: "Section 10.3 lists a Code Reviewer as a provided capability realised as subagent orqlet-code-reviewer (read-only, strong tier) and says six of seven subagent definitions ship with the protected workflow."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "2081-2100", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 8454f4550382b32e72b1e18561049ea03931bec51f546b8698b1ad0c4e69caff}
  - id: A-80
    kind: operation
    statement: "The architecture document records Q-07 as answered on 2026-10-25 with option (1): the Code Reviewer is a provided capability, the four-role gate set is unchanged and the code-reviewer role keeps required: false."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "5105", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 310cb10e53c16144ead341ff3e5850160728402d98f9a6058d9630b7257889bb}
  - id: A-81
    kind: flow
    statement: "Section 10.4 says a reviewer receives only the packet and not the Coder's transcript, memory or self-justification, that reviewers are typed subagents and never forks, allows substituting an alternative binding, another client or session, a human or a CI executor, and forbids a main agent adopting a reviewer persona."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "2106-2123", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 5adfe5966b187ccc5b8f2a4c66ab98689afda2e6d68fed21bafd920b8c7072eb}
  - id: A-82
    kind: structure
    statement: "Section 17.12.5 defines I0 (same-context persona, never counts), I1 (fresh-context subagent given only the packet), I2 (I1 plus a different model family or client) and I3 (human code owner or verified CI job)."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "3409-3428", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 6f658b5d034098ddfcc9f098279f5e700a49c6f3576139839a27e4eeaa28a31a}
  - id: A-83
    kind: structure
    statement: "Section 22.0 (facts of 2026-10-22) says six workflow skills and five role definitions were built, there is no code reviewer, and the model-policy v1 contract requires a v2 migration for separate states, fallback, availability and route exclusions."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "4486-4496", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c8bf140cb33f473805fa0a968bd7127c1c8d51b3e38aae046658a22f27505c49}
  - id: A-84
    kind: interface
    statement: "Section 24.1 [P] describes model-policy v2 with four separate states per model (discovered, approval, callable, evaluated), availability, `excluded.models: [fable]`, four starter profiles with fallback and escalation, and a roles map with pinned and required flags."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "4582-4630", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e337c6d89e1ed68f74658f7a1a51474eb4913aa011d74c21b1b2d86ea38ca268}
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "4665-4706", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 5623deffdcb6f94180d86de0c4e2710d1097de6a20449b741f6e1b41c948bc39}
  - id: A-85
    kind: structure
    statement: "The roadmap places per-role model pins and their doctor checks in M2, `orqlet models refresh` and `orqlet admin export` in M7, and lists `models verify` as not built."
    evidence:
      - {path: "docs/design/orqlet-architecture-proposal.md", lines: "4500-4522", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 9fc09a7404eccca28a2b9842a44c425d8bc85e9c141518f9f078ad94ff12463f}
  - id: A-86
    kind: structure
    statement: "The orqlet-implementation design scopes M2 to include per-role model pins rendered from an approved policy and puts `models refresh` and administrator export out of scope."
    evidence:
      - {path: "docs/design/orqlet-implementation/design.md", lines: "19-23", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 02d4c3e5a31309634c09e9815159120d1d96c07cb69620ba6713296e28a2d33e}
  - id: A-87
    kind: structure
    statement: "The orqlet-m2-workflow plan puts per-role model pins and release gates beyond A-0 (S12) out of scope for Plan A."
    evidence:
      - {path: "docs/design/orqlet-m2-workflow/plan.md", lines: "128", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 68576b791d773f5745dbc3414b81dcc695c8f795943b57d1d4e7b4c251ad4bfc}
  - id: A-88
    kind: structure
    statement: "Claude Code's `best` alias resolves to the model of the `fable` alias where Fable is available to the user and otherwise to `opus`; `fable`, `sonnet`, `opus` and `haiku` are family aliases."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "11-13", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 4831b7278b2022e66aae16138ecf406dee8672afce20f9ec71056343ba01a065}
  - id: A-89
    kind: structure
    statement: "On the Anthropic API the `opus`, `sonnet` and `haiku` aliases resolve to Opus 5.5, Sonnet 5.5 and Haiku 5.5; on Amazon Bedrock and Google Cloud's Agent Platform they resolve to Opus 5.5, Sonnet 4.5 and Haiku 4.5."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "14-15", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 0505b18f767c8149ee12e6dda34084a0c230ce6a6d85ed808d303426a47c7b00}
  - id: A-90
    kind: structure
    statement: "The `fable` alias resolves to Fable 5.1 unless ANTHROPIC_DEFAULT_FABLE_MODEL is set, and neither Fable model is the account-type default on any plan or provider."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c0a21236ab619741b80d5b0bcfdd54ce64041159cb0ab3e8dd248c21d5c0ac35}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "19", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 67db7a244fed68d7782b0812a6c910c78ba9af4926ca24ffbdd09ca6f31d6e19}
  - id: A-91
    kind: structure
    statement: "In non-interactive `-p` mode Claude Code bills a Fable request to usage credits without asking."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "20", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: ffaf1ec4414adb43ec611479c29d1b7e28e7147639ea5f1b6a3fb4669159d3da}
  - id: A-92
    kind: structure
    statement: "Claude Code aliases point to the version the vendor selects for the provider and update over time; pinning uses a full model name or a family environment variable."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "17", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 3850cedd64b722ff1b30e999aa5e24318abb81c0f39645cecc525994ba58f388}
  - id: A-93
    kind: structure
    statement: "Claude Code needs v2.1.280 or later for Opus 5.5, v2.1.284 or later for Sonnet 5.5 and v2.1.293 or later for Haiku 5.5."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "18", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 86af7e8dce982a71abdba2a5e82a51b537ebcb2be5292062294a21a900f89629}
  - id: A-94
    kind: structure
    statement: "The main-session model order in Claude Code is `/model`, then `--model`, then ANTHROPIC_MODEL, then the `model` setting, then ANTHROPIC_DEFAULT_MODEL."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "21", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 893e97afb20436219e6b365a528152eb1b627b467d9e61a3a36bea3525edb150}
  - id: A-95
    kind: structure
    statement: "When availableModels is set, it applies to the `model` field of subagent frontmatter, the Agent tool's model parameter, CLAUDE_CODE_SUBAGENT_MODEL and the `model` frontmatter of skills and commands."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "23-24", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: b981ba817526604e5d0f590662da6839ea532fa8ae393bca3ef63bd5d2f018da}
  - id: A-96
    kind: structure
    statement: "A blocked subagent model runs the subagent on a fallback model rather than failing, and a blocked skill or command model override is ignored so the skill runs on the session model."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "25-26", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 00453deab64fbab4b4bb68864eb3e581e3fba7e78691ff80136cd9eec5b214d2}
  - id: A-97
    kind: structure
    statement: "In Claude Code the `model` setting is an initial selection and not enforcement; availableModels, enforceAvailableModels, deniedModels and availableModelsMatch are the organisation controls."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "27-28", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 34e68037ba046cc8c5b056d5a36cedbe9d25b8193a7cf759452bdc569066e4dc}
  - id: A-98
    kind: structure
    statement: "Claude Code fallback chains also apply to subagents, and requests flagged by safety classifiers on Fable 5.1, Fable 5 and Opus 5.5 are re-run on other Opus models."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "29-30", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: de02a989da6a3e3bb01b645393f25c332d941d7024222d91d9d3e9a367520ebc}
  - id: A-99
    kind: structure
    statement: "Claude Code reports the actual model in the `modelUsage` field of JSON output, and `/tasks` names the model and effort of each subagent from v2.1.242."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "32", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 54b87531ff02c33217cac47a2076dcf8a762538ed7e61b07112eb4c98f4fee19}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-sub-agents.md", lines: "18", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 3b3d2d84f2a162cfcb3c03ebf476f21a782e756d69107438f470cae19d4765a2}
  - id: A-100
    kind: interface
    statement: "A Claude Code subagent definition accepts `model` (sonnet, opus, haiku, fable, a full model ID or inherit), `effort` (low to max), `tools`, `disallowedTools`, `permissionMode`, `mcpServers` and other fields."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-sub-agents.md", lines: "11-13", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f1b4bbd4384c8f50df03bcdbd111c6a3486f5fa9f34452d387b5ae14c44a6fd3}
  - id: A-101
    kind: flow
    statement: "Claude Code resolves a subagent's model from the per-invocation `model` parameter (an alias only), then the definition's `model` frontmatter, then CLAUDE_CODE_SUBAGENT_MODEL, then the main conversation's model; before v2.1.251 the variable came first."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-sub-agents.md", lines: "14-16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 75ac1f44a8065465202cc903e456debe967ba4b70eeb8fd7980635bd28ac70bd}
  - id: A-102
    kind: flow
    statement: "CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1 (v2.1.257 or later) applies one model to every subagent, teammate and workflow agent and makes Claude Code ignore the `model` field of subagent definitions."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-sub-agents.md", lines: "19-20", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 03c2f7d45c54da58e2bec1116f0a3b7e0b59b24f7d7f1a78bf8efaa3c004cb80}
  - id: A-103
    kind: flow
    statement: "A Claude Code subagent starts with a fresh, isolated context; a fork inherits the whole conversation, the system prompt and the model, and Claude can start a fork on its own because fork mode is on by default."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-sub-agents.md", lines: "21-24", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 7942df8133141fb36f5a0dd27dfd132d72db6915c61e15435385d452a61b52d4}
  - id: A-104
    kind: interface
    statement: "A Claude Code skill's `model` override lasts for the rest of the current turn and is not saved, a value excluded by availableModels is not used, and with `context: fork` the value sets the forked subagent's model."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-skills.md", lines: "12-13", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: a68999630ce88c489413d6350be4c039b8a184635c454f657780003d7594b89a}
  - id: A-105
    kind: interface
    statement: "A Claude Code skill's `effort` applies for the rest of the current turn, and with `context: fork` it sets the forked subagent's effort; `agent` names the subagent type for a forked skill."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-skills.md", lines: "14-15", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e3e801c6e12578017853b0b718c362bd8befc808cd7c900c02f86ca26cac77dd}
  - id: A-106
    kind: flow
    statement: "A Codex subagent inherits the parent's model and reasoning effort unless `model` or `model_reasoning_effort` is set in the custom agent file, in an [agents] default or in an explicit spawn request."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md", lines: "11-12", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 14949fbd0b671035cba2f2e30a5503c3c559ca8210c954ab0f71743915f7cf40}
  - id: A-107
    kind: flow
    statement: "Codex applies a custom agent file's `model` and `model_reasoning_effort` over other sources, after resolving each setting from an explicit spawn value, then the [agents] default, then the parent's value."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md", lines: "18", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e287e2253c6553eb4b3c64ca6dd1d3f5e1bb4c5b382cee07402df097df552e2a}
  - id: A-108
    kind: flow
    statement: "Codex subagents inherit the parent's sandbox, approval, provider and MCP settings, a custom agent file cannot replace them, and the documentation says custom agent instructions do not create a separate read-only sandbox."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md", lines: "15-17", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2d4d3c1b11315e75cfb254618ac694bbd82a973b189d812b13575ee9faf82f5d}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md", lines: "19", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e64ad6bdbb654176b48233af960d0af88fa2f5087d22e54d2c3c0d16e6b85740}
  - id: A-109
    kind: interface
    statement: "Codex's `agents.default_subagent_model` sets the default model of spawned agents, and explicit spawn values override it."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md", lines: "20-21", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: cf0ae58d7b29f8221514e1b092a583c855b4aec13092cf6abac87e69ca2be2d4}
  - id: A-110
    kind: structure
    statement: "The Codex subagent page names gpt-6.1-sol as the start where the account has access and gpt-6-luna for lighter subagent work, with starting efforts of `high` for Luna and `low` for Astra."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md", lines: "13-14", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 44650b0dd30d6b49b58a4cbfd24195744a67c826174ef461fe52aaf8de28e27d}
  - id: A-111
    kind: structure
    statement: "OpenAI's Codex model page positions Astra for the most demanding workflows, GPT-6.1 Sol as near-Astra performance at lower cost, GPT-6.1 Terra for writing and visual work and Luna for focused, repeatable tasks, with `gpt-6.1-sol` and `gpt-6-luna` as the selectable names."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "11", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e8434f5bfd543139a3c06fe70a2163f265b7c509df4b9b2b0065a87b1fcb0c43}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "13-14", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f085c52a8922c62a04786f648451456fd79bbedb181dd5df9b421e92125b26de}
  - id: A-112
    kind: structure
    statement: "GPT-6.1 Terra needs Codex CLI 0.159.0 or later."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "12", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 13c1e0aaca6606278564e3b26de0cfd78ca42e9a57941914aa01a2a4044bcd7d}
  - id: A-113
    kind: structure
    statement: "Codex model access depends on plan, client, workspace settings and authentication: GPT-6.1 Sol is the named choice on Plus, Pro, Business, Enterprise and Edu, GPT-6 Luna on Free and Go (an Enterprise or Edu administrator must enable Luna first), and with API-key authentication availability follows the API organisation and project."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "18-19", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e6bfa05ea344d490e7337dac041d052f47c42ffbb410895791012a91fcce1ab3}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "22-23", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: a10617bb047c0344b4fe32dd842d69c0cfcd44e9df89e01b5af56ff9b00ae98e}
  - id: A-114
    kind: structure
    statement: "GPT-5.5 retired from Codex for ChatGPT sign-in on 2026-10-14, and custom agents and managed configurations that select it need a replacement."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "20-21", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: dc0d61bafaebe57a986ee64729df20b3b3cd9d81dab84aa59ed5bf80ae7c6589}
  - id: A-115
    kind: structure
    statement: "In Codex configuration Astra's Light setting is `low`, and GPT-6 Luna supports efforts up to Max but not Ultra."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "15-16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: d19a5c27465a46a47d7947cdf06698036710b4958be82c9568a73057ad803872}
  - id: A-116
    kind: structure
    statement: "OpenAI documents the model ID `gpt-6-astra` with `reasoning.effort` values low, medium, high, xhigh and max and a 1,050,000-token context window."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/openai-gpt-6-astra-and-pricing.md", lines: "11-14", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 845e8015d1878d103939bb9cef6b1444d40b402eebf37cdde71f08b5ace1ecbc}
  - id: A-117
    kind: structure
    statement: "OpenAI API standard prices per million tokens for short context are $10.00 input and $50.00 output for gpt-6-astra, $2.00 and $10.00 for gpt-6.1-sol, $1.00 and $5.00 for gpt-6.1-terra and $0.10 and $0.50 for gpt-6-luna."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/openai-gpt-6-astra-and-pricing.md", lines: "17-20", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 5cbc02c68f7eb12ecd9976bacb935b271ab128b4f0d83932d7f37417e63eea49}
  - id: A-118
    kind: interface
    statement: "A Cursor subagent's `model` field takes `inherit` (the default) or a model ID, which may carry bracketed options such as effort and context window."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "12", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 93f5ab59b86c4ffd4b2e5fb2c7ba9dc8f73f739dad162cf79acb85928725518e}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "14-16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: daef38b7eff1a19dd025efa000dd99962ce0ddb3f0e871635fa6b804f72558c8}
  - id: A-119
    kind: flow
    statement: "Cursor does not honour a subagent's model when a team admin has blocked it, the plan does not include it or a legacy plan lacks Max Mode, and it falls back to a compatible model."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "17-18", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 6269e775c782ed7d693d4e5c9f1b56a0469f9ea2b6ef6da61bfa0d8e8584bc8b}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "24", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 984e620472e0b6462bf25d48e69801afe850d379739e9c1abe886fb5a0c2efec}
  - id: A-120
    kind: flow
    statement: "In Cursor the model picker, including Auto, applies to the parent agent, and a subagent can run a different named model through its frontmatter or the parent's launch request."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "19-20", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2fc524555c72ac032c37248454c6dec39135f5c7803f591cd94d4884496050e0}
  - id: A-121
    kind: flow
    statement: "Cursor's subagent task card shows which model ran, the usage dashboard lists it, and each request bills at the list price of the model that ran."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "21-22", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 5f8ec364dfff3215d8c24c74a4588bd0152abb9cf01a8a22d4fb9f2ddd1bd706}
  - id: A-122
    kind: flow
    statement: "Cursor subagents start with a clean context, inherit all parent tools including MCP tools, and `readonly: true` restricts them to no file edits and no state-changing shell commands."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "11", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 3371eb4e469d35f06bb0fa8ba4fa282dadbc3ace83f9a3b4cefa6186ffcb0316}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "23", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 3eefb5bd5003761ffe1d82b86f5a99719ec84f10e76ea924db71da98a32a705e}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "13", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e1a13051dcf0084fe31277b15d6bea551ca562dea6f9faa641834eecf5df1893}
  - id: A-123
    kind: structure
    statement: "Cursor's Plus plan includes only Grok 4.7, Grok 4.6, Grok 4.5 and Composer 2.5; Claude, GPT and Gemini models are available from the Premium plan upward at API list price from prepaid credit."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", lines: "11-13", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f3ec399a01937165973e2cca54c07a4d61f290800ae8a4015e2d427f8cc39b98}
  - id: A-124
    kind: structure
    statement: "Cursor lists Grok 4.7 at $2 input and $6 output and Composer 2.5 at $0.5 input and $2.5 output per million tokens."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", lines: "15-16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 874dad45df1f5bd961c4d3a86f5a9847313b8c22cf8a368aeac38e33637758e7}
  - id: A-125
    kind: structure
    statement: "Cursor lists Claude Opus 5.5 ($4 input, $20 output), Sonnet 5.5 ($2, $10), Haiku 5.5 ($0.1, $0.5) and Fable 5.1 ($10, $50) per million tokens, and attaches a data-retention approval requirement to Fable 5.1 for Enterprise, Teams and Privacy Mode customers."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", lines: "17-20", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: b013fb7164170a07709b5953d314521c78ae0c1c61f8f2c1044d0c2ebf9ae47b}
  - id: A-126
    kind: structure
    statement: "Cursor lists Gemini 4 Argon ($2, $10), Gemini 3.8 Flash ($0.75, $3.75), GPT-5.6 Sol ($4, $20), GPT-5.6 Terra ($2, $12) and GPT-5.6 Luna ($0.2, $1.2) per million tokens."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", lines: "21-25", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 5aab5cc5038d3f1081bebf7a1740ed6d8b8ad36aae99c0e06be878a02af584c0}
  - id: A-127
    kind: structure
    statement: "The Cursor price table lists OpenAI models from GPT-5 to GPT-5.6 and no model whose name starts with GPT-6."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", lines: "27", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: a3e8784f1fddf3815557637871b4328f86764b1bec6fa85821f3513532f6bb5b}
  - id: A-128
    kind: structure
    statement: "Cursor's Auto has the modes Cost, Balance and Intelligence, individual plans have Cost mode only, and Cost mode bills as a Cursor-model request."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", lines: "28-30", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 0a6ded9e8bde018fce0a200a6f1fb3a4062b7f6ed686881e52a995aebfd4ed85}
  - id: A-129
    kind: structure
    statement: "Cursor Router is available only on Teams and Enterprise plans, and Enterprise teams must enable it because it is off by default."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-router.md", lines: "11", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 21c3585c42819e41d1efc99d121570b868cb619017b1d1cdc1d3fb8f3dce47ff}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-router.md", lines: "20", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: f2b4a73dcf3ab994c9c5265a935a804e556538b911bcfe646bd21c21ddefe1f4}
  - id: A-130
    kind: structure
    statement: "Cursor Router has the modes Cost, Balance and Intelligence, is managed by Cursor, and does not let the user hand-pick which model handles a request."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-router.md", lines: "12-13", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: a03f0671a7b7f629391bafaa34ac028456502d97c9834e7c4b9184fd0f3c6902}
  - id: A-131
    kind: structure
    statement: "On Enterprise plans Cursor Router respects the team's model access controls and routes to an allowed model when one is blocked; blocking too many models can disable the router, and the page says Grok 4.6 must be enabled for the router to work."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-router.md", lines: "14-15", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 29fa1d08de39bb8d8a1e39b2b2ffb760ec66d5fabdbc14be8aa92c8719ea859c}
  - id: A-132
    kind: structure
    statement: "The model Auto routed to is hidden by default for Balance and Intelligence, and a team admin can make Auto the default or lock the picker to Auto."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-router.md", lines: "16-17", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 0b72213047025c63ac4ccc325c40e7fff9078846cc273e265c82008bf4ea6a34}
  - id: A-133
    kind: interface
    statement: "The Cursor TypeScript and Python SDKs expose the router as model id `auto-smart` with the parameter `optimize_for` (`cost`, `balanced` or `intelligence`)."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-router.md", lines: "19", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: d1abefa4b4309b71febbb258d6949a837d71566f1b6db1d74321909d994cca22}
  - id: A-134
    kind: structure
    statement: "Anthropic lists Claude Fable 5.1, Opus 5.5, Sonnet 5.5 and Haiku 5.5 with API IDs `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`, 1M-token context and prices of $10/$50, $4/$20, $2/$10 and from $0.10/$0.50 per MTok."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/anthropic-models-overview.md", lines: "11-16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 3ad851f130bb64e54ae8d97a5098a29a695842e97622ddf75b93d2ab28a12038}
  - id: A-135
    kind: structure
    statement: "Anthropic states that every Claude model ID is a pinned snapshot and commits to retirement dates not sooner than 2027-09-01 (Fable 5.1), 2027-09-22 (Opus 5.5), 2027-09-28 (Sonnet 5.5) and 2027-10-07 (Haiku 5.5)."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/anthropic-models-overview.md", lines: "19", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: db731231bb41eb24c8acd5c76813eab7122b79a01c9184475c9e8f3e0edb3af3}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/anthropic-models-overview.md", lines: "17", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 5b83ea2d58b0cd1cdc2d50402aa5a5aacfef314a87fe11f5ca6d8b4be6ed524f}
  - id: A-136
    kind: structure
    statement: "xAI lists `grok-4.7` with a 500k-token context at $2.00 input and $6.00 output per million tokens below 200k prompt tokens and double that above, and a May 2026 knowledge cut-off."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/xai-models.md", lines: "11-12", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 31b7a389b4cb37dd2ea13c6fa3c26a81bb5d4973bc2090d0cc274ee4dde239c6}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/xai-models.md", lines: "15", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 325eb46ec0224c26220a3a0abef7f00dc576ed1f54501a75f9a80687c296dad1}
  - id: A-137
    kind: structure
    statement: "xAI documents a stable alias, a `-latest` alias and a dated, non-updating release name for its models."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/xai-models.md", lines: "16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 958f242b36ff99b80b55e37e4d59f204078a158a0514a3c14828cb5c923f6ceb}
  - id: A-138
    kind: structure
    statement: "Google DeepMind published the Gemini 4 Argon model card on 13 October 2026, describing a model for software engineering, enterprise knowledge work and cybersecurity with a context of up to 1M tokens, available through the Gemini API and Google AI Studio."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/google-gemini-4-argon-model-card.md", lines: "11-14", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: fc8662ab49cfa45c09fff2aa4353e77a51761e29e9cafe7756bcd6605754841f}
  - id: A-139
    kind: structure
    statement: "The model card compares Argon with GPT-6 Astra, Claude Fable 5.1 and Claude Opus 5.5 on vendor-chosen benchmarks, where the vendor-reported scores differ by benchmark, for example DeepSWE v1.1 77.9%, 74.1%, 67.4%, 74.2% and Terminal-bench 4.0 57.4%, 58.2%, 57.9%, 66.4%."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/google-gemini-4-argon-model-card.md", lines: "15-18", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 4fc552ee755db78dce793b68c9891396ea717bb65a0d638544c40e657ee825e1}
  - id: A-140
    kind: flow
    statement: "Claude Code subagents inherit the built-in tools and MCP tools of the main conversation, narrowed by two filters."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-sub-agents.md", lines: "25", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 028e6d4952b0f50510280ec6e93dd7baa8542d718902e93714414ff503495fe9}
  - id: A-141
    kind: structure
    statement: "The generated workflow rule says files under .orqlet, the client folders and the AGENTS.md block are generated and not edited by hand, and that a file Orqlet seeded once, such as `.prompts/`, belongs to the team."
    evidence:
      - {path: ".cursor/rules/orqlet-workflow.mdc", lines: "19-21", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 25ede758c3c62e3b45e0ea27a3a9dd1e8e87397da8f185711b494f49de2a7507}
  - id: A-142
    kind: structure
    statement: "The project profile lists the standards source `.prompts` (kind prompts-dir, scaffold seeded) and the enabled clients claude-code, codex and cursor, each with a null minimum version."
    evidence:
      - {path: ".orqlet/project-profile.yaml", lines: "158-170", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 36d6fea58486ddab42854d9cb6abc4f9d2aa33544f58c7a720ae29f099c0f730}
  - id: A-143
    kind: structure
    statement: "In .prompts/rules.yaml the rules ORQLET-ARCH-001 to 003, DET-001 to 003, TEST-001, TEST-002 and QA-001 are `deterministic` with a check_ref, ORQLET-SEC-001 to 003, SAFE-001 and NOMODEL-001 are `review`, and ORQLET-STYLE-001 is `guidance`."
    evidence:
      - {path: ".prompts/rules.yaml", lines: "10-143", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 142ae5648aebc80392d9af49d5a108ecfc471081d0865293d7715699aa88fa0e}
  - id: A-144
    kind: structure
    statement: "Orqlet renders two blocks of the pull-request template at .github/pull_request_template.md, a team block and an orqlet-workflow block."
    evidence:
      - {path: "src/orqlet/adapters/render/pr_template.py", lines: "1-16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 6de41eddca31e250f7baec2cf92f4aae18a8a515bea673f5dcc510f8cb0ab5fd}
  - id: A-145
    kind: flow
    statement: "The implement skill ends with the person opening the pull request after the last phase and holds no step that writes a pull-request title, description or summary."
    evidence:
      - {path: "src/orqlet/workflow/skills/orqlet-implement/skill.md", lines: "1-59", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: a7345da80079e404bb61b525fe60d7f1e32a17171523568b139cb29165da09ec}
  - id: A-146
    kind: structure
    statement: "The AGENTS.md conventions block records one pull request per task phase whose title says what it does and whose description fills the Orqlet workflow template, a squash merge and the reviewer tmishari."
    evidence:
      - {path: "AGENTS.md", lines: "77-88", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: d562c359c59743497340d7714cb7c1ec0ef002a0aa0049cedb5b3d018cd5ee3a}
  - id: A-147
    kind: flow
    statement: "Codex skills inherit from the parent, and a custom agent can disable individual skills with `skills.config`."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md", lines: "23", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 47640a0728a95a8b08b72eb717b84a1c5473c32d377924ae2aff92f499c3dcc9}
  - id: A-148
    kind: structure
    statement: "Claude Code's `default` value clears a model override and resolves to the account-type default (Opus 5.5 on Pro, Max, Ultra, Team, Enterprise and the Anthropic API) or, when an admin has set one, to the organisation default model."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "34-36", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 61a5719cc0fbae613e21d87392ee43c24adcf0c52909dc1cbdc755429f82b3ad}
  - id: A-149
    kind: structure
    statement: "Claude Code's `opusplan` alias is described as an automated hybrid that uses Opus in plan mode and Sonnet in execution mode."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "37", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 22863599e2356f679c8180311eebd237a31e274c05be1833277a9369676a5d93}
  - id: A-150
    kind: structure
    statement: "The Claude Code model page lists no alias named `auto`; the only auto mode it names is a classifier whose requests use a model of their own."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", lines: "38-39", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 6e489d7649b960bab5058d758456b335763a8b6fd9e7e0a7e60190b29a481706}
  - id: A-151
    kind: structure
    statement: "In the Codex and ChatGPT desktop app the starting point is the account's default Power setting, which steps through presets (Luna High, GPT-6 Sol Light and Medium, Astra Light, Medium and Extra High) toward Faster or Smarter, and Advanced selects a specific model, reasoning effort or speed; some paid plans omit Astra Extra High."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "26-27", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 080f4c4230f12ee35c386b6bd2f7992432a603cd575f5ce9bb6489a8d30037bc}
  - id: A-152
    kind: structure
    statement: "When no model is specified, the Codex desktop app, CLI and IDE extension use a default model that OpenAI selects."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "28", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2a72d25d327d24848579a7ccf41defefcafa19675a5dfd355b23b47903cd41e4}
  - id: A-153
    kind: structure
    statement: "The Codex models page text names no automatic per-task model router and no mode named Auto."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", lines: "29", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 30691eff8ca6ef30510d3d430f01d67a16c241158b7a93bdb3e70bfb83995ccd}
  - id: A-154
    kind: structure
    statement: "Cursor's help says Auto selects models that balance intelligence, cost and reliability, and that under Auto the router picks the model for each request so the model can vary between turns."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-help-available-models.md", lines: "11", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c3668b6075b0fdf9414592ff873e40ca13314fa0297ee6dcc183e6d7e9f262ad}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-help-available-models.md", lines: "17", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 4ed03ba64e56997ab6f6d8bc47061d866759b251c7652f8dfe4b8073bb1f2815}
  - id: A-155
    kind: structure
    statement: "Cursor documents the router's pool as GPT-5.5, Claude Opus 5, Grok 4.6 and Claude Fable 5, says the pool changes over time, requires Grok 4.6, and says that on enterprise plans blocked models are skipped."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-help-available-models.md", lines: "12-15", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2868b46596de4f0cce2fe8e0e09987f16c1e7eb232a6f99f7b48960a1029be35}
  - id: A-156
    kind: structure
    statement: "Cursor hides the routed model by default and lets team admins set model visibility to Displayed in the admin dashboard."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-help-available-models.md", lines: "16", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 8f38ea9b5bfdda85b70677eaf7609f41d3b3b63229f3824369b6eda9b1df313b}
  - id: A-157
    kind: flow
    statement: "Built-in Cursor subagents select their model automatically for the subtask, custom subagents default to `inherit`, and the model picker including Auto applies to the parent agent."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-help-available-models.md", lines: "18", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 7e90d8c0cf35f1d72f5c2c77d4698ec173206ae6e3d79a60ead27ce5f17d7266}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", lines: "19-20", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2fc524555c72ac032c37248454c6dec39135f5c7803f591cd94d4884496050e0}
  - id: A-158
    kind: structure
    statement: "Cursor's Plus plan has no Auto, individual plans have Cost mode only, Enterprise teams start with the router off and an admin must opt in, and Auto is available in all regions."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", lines: "11", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: dd718634e90bbbdf779571ec675fda26a261d2fccdc2839ead7c08245909dc5a}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", lines: "30", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: e28859782f06b3797df811274ddb93e0f8a2fa0eb5711aece0d055e8eef91d6b}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-help-pricing.md", lines: "13", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 2a10cc27dba613cf361cec33d0f9c708b255bbff70d5498dd29b3db8834955b9}
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-help-available-models.md", lines: "19", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: 0c0dee034682cc06010b601b2016dd06fa65c24af194c7151739afc1911693af}
  - id: A-159
    kind: structure
    statement: "Cursor documents the router as available across the Agents window, editor, CLI, SDK and the iOS app."
    evidence:
      - {path: "docs/design/dynamic-model-profiles/evidence/web/cursor-help-pricing.md", lines: "14", revision: 0a280480edf5543b1907805a402c3ada930cf045, sha256: c03d834dfe7afe59d56fd6596fbebb85b51cc3b7d34afb14d682a4fa081e4a28}
unknowns:
  - id: U-1
    what: "Whether each client treats the generated `model: inherit` (Claude Code, Cursor) and the absence of a model key (Codex) as the renderers assume. Each adapter states that its behaviour follows documentation of 2026-10 and was not observed with a real client version; one Cursor session of 2026-10-23 reported `inherit` as blocked by the team's admin settings (A-66). Which model and reasoning effort the main session runs, and whether `inherit` also carries reasoning effort in each client, is stated in no repository file. The current client pages (A-100, A-118, A-106) document the fields but not the behaviour on these accounts."
    material: true
    question_ref: Q-14
    merged_from: ["inventory-roles-skills-render/U-1", "inventory-roles-skills-render/U-5", "inventory-model-contracts-cli/U-2", "trace-upgrade-role-files/U-7", "trace-review-flow/U-3", "inventory-design-records-models/U-7"]
  - id: U-2
    what: "Which model and reasoning-effort fields each client accepts in agent and skill files, and their legal values. The renderers write only `model: inherit` and nothing for effort. The current official pages answer this for subagent frontmatter in Claude Code and Cursor and for custom agent files in Codex (A-100, A-118, A-106); the versions of the clients on the accounts were observed only for Claude Code (local probes, see the brief)."
    material: false
    merged_from: ["inventory-roles-skills-render/U-2"]
  - id: U-3
    what: "Which model ran each recorded review and each research subagent, and whether each client reports a subagent's model identity so that `model_observed` could be filled. The repository's records hold null in every model field and nothing in code produces `model_observed`. The fetched pages document `modelUsage` and `/tasks` in Claude Code and the task card in Cursor (A-99, A-121); no fetched Codex page documents a report of a subagent's model to the main agent."
    material: true
    merged_from: ["inventory-design-records-models/U-5", "inventory-design-records-models/U-8", "trace-review-flow/U-1", "trace-review-flow/U-2"]
  - id: U-4
    what: "How the values of `coder_binding` are determined for a review record: no code or skill step produces them, and one record says they were carried from earlier staged records without observing the coder session."
    material: true
    merged_from: ["inventory-model-contracts-cli/U-5", "trace-review-flow/U-4"]
  - id: U-5
    what: "Which models, aliases, runtime ids, ranks, price ranks and approvals the company has. No model-policy file exists, no code reads one and the proposal lists model approvals, rankings and organisation-approved Claude Code routes as pending owner input. The person answered that all developers can approve models (Q-14); the catalog's content is still unstated."
    material: true
    question_ref: Q-14
    merged_from: ["inventory-design-records-models/U-3", "inventory-roles-skills-render/U-3"]
  - id: U-6
    what: "The standing of the v0.5 model sections and of the rework they imply: whether the person's conversational 'I approve all' counts as approval of the proposal or of sections 10.3 and 14.9; whether v0.4 was ever approved; whether the plans citing v0.4 are re-based; whether any plan or design for the v0.5 rework (model-policy v2, pin rendering, orqlet-code-reviewer, review-input v2, missing-candidate) exists or is scheduled; whether an independent review of sections 14.9 and 12.8 exists outside the repository; whether the design and plan folders marked approved meet the proposal's own definition of approval; and whether the design task folders record decisions on model selection beyond the cited hits."
    material: true
    question_ref: Q-15
    merged_from: ["inventory-design-records-models/U-1", "inventory-design-records-models/U-2", "inventory-design-records-models/U-11", "inventory-design-records-models/U-12", "inventory-design-records-models/U-13", "inventory-model-contracts-cli/U-4", "trace-upgrade-role-files/U-9", "trace-review-flow/U-5", "inventory-roles-skills-render/U-7"]
  - id: U-7
    what: "Whether the developer's 'Fable' is Claude Code's `fable` alias. The proposal infers it without verification and cites a brief that is not in the repository. The person answered that the exclusion covers that alias only (Q-7); the official page shows that `best` resolves to the same model where Fable is available and that Fable can be chosen by full ID (A-88, A-90)."
    material: true
    question_ref: Q-13
    merged_from: ["inventory-design-records-models/U-4"]
  - id: U-8
    what: "The authentication, network behaviour and cost of the client model-metadata commands. The approved run of `agent models` printed 'No models available for this account.' with exit status 0 and `codex debug models --bundled` could not run because no `codex` command is on the PATH (local probes, see the brief)."
    material: true
    question_ref: Q-11
    merged_from: ["inventory-design-records-models/U-6"]
  - id: U-9
    what: "Whether the documentation pages cited by the proposal (CC-12, CC-13, CX-11, CU-12), which have no stored copy, still say what sections 14.3 and 14.4 attribute to them. The current versions of the equivalent pages were fetched in this research and are stored as evidence files; the proposal's sections were not re-read against them line by line."
    material: false
    merged_from: ["inventory-design-records-models/U-14"]
  - id: U-10
    what: "Whether a Codex subagent has a clean, independent context and whether Codex-only reviews are more than 'I1 provisional' (spike S-22); the fetched Codex subagent page states inheritance of model, sandbox, provider and MCP settings and states nothing about the cleanliness of a subagent's context."
    material: true
    merged_from: ["inventory-design-records-models/U-9"]
  - id: U-11
    what: "Whether `model: inherit` counts as a 'pin' under ADR-005 decision 6 ('With no policy the file carries no pin') and proposal 14.9.2 rule 4 ('client default'); no record defines the term for `inherit`."
    material: true
    merged_from: ["inventory-design-records-models/U-10"]
  - id: U-12
    what: "Whether the reviewer of each of the 108 I1 records ran in a fresh context that received only the packet: the validator has no field or check for it and only free-text capability_limits speak to it."
    material: true
    merged_from: ["trace-review-flow/U-6"]
  - id: U-13
    what: "User-level or global client settings outside the repository (Claude Code, Codex and Cursor user configuration, and the home-level CLAUDE.md) were not opened; they decide which model `inherit` resolves to and what Codex uses."
    material: true
    merged_from: ["inventory-roles-skills-render/U-4", "inventory-design-records-models/U-16"]
  - id: U-14
    what: "The content and purpose of .orqlet/proposals/.orqlet__role-bindings.yaml.diff, which was empty or unreadable to every reader, and why a proposal for the seeded role-bindings file exists."
    material: false
    merged_from: ["inventory-roles-skills-render/U-6", "inventory-model-contracts-cli/U-1", "inventory-design-records-models/U-15", "trace-upgrade-role-files/U-8", "trace-review-flow/U-8"]
  - id: U-15
    what: "Whether host-side branch rules or required checks beyond .github/workflows/ci.yml run any orqlet validator on review records; host configuration is not readable in the repository."
    material: false
    merged_from: ["trace-review-flow/U-7"]
  - id: U-16
    what: "Test coverage of role files across an upgrade: no test edits or deletes a role file and then runs `orqlet upgrade`; no test or fake changes a role source across an upgrade; no test gives load_roles a malformed role source; no contract-marked test covers role-file rendering."
    material: true
    merged_from: ["trace-upgrade-role-files/U-3", "trace-upgrade-role-files/U-4", "trace-upgrade-role-files/U-5", "trace-upgrade-role-files/U-6"]
  - id: U-17
    what: "Whether the import-linter independence contract also forbids import chains between the three client modules through the shared module adapters.render.roles; whether ruff, mypy, import-linter and pytest pass at the base revision (no check was run, so none is reported as passed); and whether the working tree equaled HEAD for the read-only readers."
    material: false
    merged_from: ["trace-upgrade-role-files/U-1", "trace-upgrade-role-files/U-2", "trace-upgrade-role-files/U-10"]
  - id: U-18
    what: "Absence facts established by directory listing (no model-policy.yaml, no settings or config files in the client folders) have no line span; a hidden root-level file that the listing omits cannot be excluded."
    material: false
    merged_from: ["inventory-roles-skills-render/U-8", "inventory-model-contracts-cli/U-3"]
  - id: U-19
    what: "Plan, organisation type and per-model access of the Cursor, Codex and Claude Code accounts. Q-4 named the three clients as in scope and gave no plan or access detail. Cursor Router needs Teams or Enterprise, third-party models in Cursor need Premium or above, Codex model access follows plan and administrator enablement, and Claude Code alias targets depend on the provider (A-129, A-123, A-113, A-89). Account eligibility is therefore unknown for every candidate model. After acceptance the person added that the Codex client is the desktop app (Q-12), that the budget is $2000 per client (Q-16) and that Fable is not available (Q-13); plan and organisation type are still not stated."
    material: true
    question_ref: Q-10
  - id: U-20
    what: "Why `agent models` lists no models for this account: the Cursor CLI may not be signed in, may be out of date (version 2026.02.13-41ac335) or the plan may not include models there. The output is not read as proof of access or of its absence."
    material: true
    question_ref: Q-11
  - id: U-21
    what: "The version of the Codex desktop app, which the person named as the Codex client (Q-12). No `codex` command is on the PATH, so `codex --version` and `codex debug models --bundled` were NOT_RUN; GPT-6.1 Terra needs Codex CLI 0.159.0 or later (A-112), and whether the desktop app meets that is unknown."
    material: true
    question_ref: Q-25
  - id: U-22
    what: "How the absence of Fable is established on the team's accounts. The person answered 'no fable avalible.' (Q-13), which this file reads as Fable not being available to the accounts, and not as a list of paths to block. `best` resolves to the `fable` model where Fable is available, Fable can be chosen by `claude-fable-5-1` or `claude-fable-5` (A-88, A-90, A-134), Cursor lists Fable 5.1 as a model of its own (A-125) and the documented Cursor Router pool names Claude Fable 5 (A-155); the fetched pages document a block only for enterprise plans."
    material: true
    question_ref: Q-24
  - id: U-23
    what: "Which organisation model restrictions are in force for the three clients (Claude Code availableModels and deniedModels, Cursor team model blocks and Router settings, Codex workspace enablement), and who approves models for the team's catalog. The person answered 'all devs can approve' (Q-14); which restrictions are in force, and whether the author of a change may approve it, are not stated."
    material: true
    question_ref: Q-23
  - id: U-24
    what: "Whether any candidate model is callable-verified or evaluated: no model was called and no evaluation ran (NOT_RUN), and no scope for paid evaluations or budgeted callable checks is approved; the person stated a budget of $2000 per client (Q-16) without a period or a permitted use (Q-22). Effective cost per accepted result, including retries and repair, therefore has no measured value, and the Codex subscription and credit rates were not retrieved (only API prices, A-117)."
    material: true
    question_ref: Q-22
  - id: U-25
    what: "The exact Cursor model IDs of the candidates. The Cursor subagent page names `composer-2`, `gpt-5.6-sol` and `claude-opus-5[...]` as examples and points to a models reference whose guessed address returned 'Page not found'; IDs for Grok 4.7, Claude Sonnet 5.5, Claude Haiku 5.5, Composer 2.5 and Gemini 4 Argon in Cursor are stated in no fetched page. Two fetches of Gemini API model pages timed out and neither page was read."
    material: true
  - id: U-26
    what: "What 'dynamic selection' means under the IDE-first boundary: ORQLET-NOMODEL-001 and proposal 14.9.1 say Orqlet calls no model and selects none at run time, while the request asks the reviewer to be resolved from the coder's resolved model. The person asked to be consulted before any change to the boundary and, after acceptance, said 'the model will be selected on auto' (Q-18); how that reads under the boundary and whether it covers reviewers is not stated (Q-20)."
    material: true
    question_ref: Q-17
  - id: U-27
    what: "Whether the router requirement stated on the Cursor Router page ('enabling Grok 4.6 is a requirement') still holds when Grok 4.7 is listed as the latest Cursor-trained model."
    material: false
  - id: U-28
    what: "Which model a Cursor custom subagent that inherits runs under an Auto parent, and whether `auto` or `auto-smart` is accepted as a subagent `model` value: the fetched Cursor pages say Auto applies to the parent agent and that custom subagents take `inherit` or a model ID (A-157, A-118), and do not say whether an inheriting subagent is routed per request."
    material: true
  - id: U-29
    what: "Whether the Codex desktop app's default selector picks a model per task: the official page documents a recommended model and Power presets and names no router (A-151, A-153); search results from non-official sites discuss the question and were not opened."
    material: false
  - id: U-30
    what: "Whether 'auto' covers the reviewers and which feature of Codex and Claude Code counts as auto: only Cursor documents a router (A-154), Codex documents a default and presets and Claude Code a default and `opusplan` (A-151, A-149), and under Cursor Auto the model can vary between turns and is hidden by default."
    material: true
    question_ref: Q-20
  - id: U-31
    what: "The scope and independence class of the approved code review gate (Q-19): the phases and change classes it covers and the class it requires; the built code derives I0 to I2 and knows two review roles (A-52, A-49)."
    material: true
    question_ref: Q-21
contradictions:
  - id: C-1
    sources: ["docs/design/orqlet-architecture-proposal.md:2100", "src/orqlet/workflow/MANIFEST.json:37-53", "src/orqlet/application/contracts/role_bindings.py:19"]
    note: "The proposal says seven subagent definitions are needed, six shipped, including `orqlet-code-reviewer` started by `/orqlet-review` (v0.5: seven roles, six shipped; the M2 design from v0.4: five of six). The package ships five role sources, none of them a code reviewer, the review skill starts two reviewers, and the role-bindings, review-result, evidence-path and plan code accept only the architecture and security reviewers."
    merged_from: ["inventory-roles-skills-render/C-1", "inventory-design-records-models/C-4", "inventory-design-records-models/C-5"]
  - id: C-2
    sources: ["docs/design/orqlet-architecture-proposal.md:2506", "src/orqlet/adapters/render/roles.py:27", "src/orqlet/adapters/render/roles.py:35", "docs/design/orqlet-implementation/adr-005-deterministic-renderers-and-golden-tests.md:16"]
    note: "The proposal says Orqlet renders a model pin from an approved policy into generated subagent files and ADR-005 says 'With no policy the file carries no pin'. The renderers write the literal `inherit` for Claude Code and Cursor, nothing for Codex, and take no policy input."
    merged_from: ["inventory-roles-skills-render/C-2", "inventory-model-contracts-cli/C-3", "inventory-design-records-models/C-9"]
  - id: C-3
    sources: ["docs/design/orqlet-architecture-proposal.md:4589", "docs/design/orqlet-architecture-proposal.md:2515", "src/orqlet/application/contracts/model_policy.py:70-82", "src/orqlet/application/contracts/profile.py:155-172"]
    note: "The proposal's example is schema model-policy v2 (discovered, approval, availability, callable, evaluated, fallback, escalation, an `excluded` object) and says the project profile records `model_policy: managed` or `none`; the built contract is v1 with none of those names, `excluded` is a flat list and the profile has no such key."
    merged_from: ["inventory-model-contracts-cli/C-1", "inventory-model-contracts-cli/C-2", "inventory-design-records-models/C-12"]
  - id: C-4
    sources: ["docs/design/orqlet-architecture-proposal.md:1333", "src/orqlet/domain/binding.py:21-47", "src/orqlet/application/contracts/review_input.py:28-29"]
    note: "The proposal binds a `model_binding`, a pre-image, context and packet format into `orqlet.review-input/v2`, while its own 17.11 example still shows v1; the built code and the shipped review-format hold review-input v1 with seven components and none for a model."
    merged_from: ["inventory-model-contracts-cli/C-4", "inventory-design-records-models/C-7", "trace-review-flow/C-6"]
  - id: C-5
    sources: ["docs/design/orqlet-architecture-proposal.md:2520", "docs/design/orqlet-architecture-proposal.md:5057-5059", "src/orqlet/application/contracts/role_bindings.py:18-38", "src/orqlet/application/usecases/validate_records.py:284-296"]
    note: "The proposal says a binding's `definition_sha256` is the hash of the agent definition with the pin field removed and that `not_accepted_for_review_roles` keeps a personal agent from any gate; the code reads neither field, and the check compares the record's own `agent.definition_sha256` with the whole agent file."
    merged_from: ["inventory-model-contracts-cli/C-5", "trace-review-flow/C-8"]
  - id: C-6
    sources: ["docs/design/orqlet-architecture-proposal.md:2516", "src/orqlet/application/usecases/gate_status.py:96-280"]
    note: "The proposal says `gate status` and `/orqlet-review` stop before starting a role that has no approved model route; `gate status` reads no role bindings or review records and the review skill has no such step."
    merged_from: ["trace-review-flow/C-7"]
  - id: C-7
    sources: ["docs/design/orqlet-architecture-proposal.md:4522", "docs/design/orqlet-architecture-proposal.md:3752", "src/orqlet/interface/cli/app.py:36-51"]
    note: "The proposal lists `hook`, `ci check` and `ci collect` as built in MVP-1 and specifies `orqlet ci check` as the source of I3 evidence; the CLI registers no `hook`, `ci`, `models` or `admin` command and none is listed as implemented."
    merged_from: ["inventory-model-contracts-cli/C-6", "trace-review-flow/C-9"]
  - id: C-8
    sources: ["docs/design/orqlet-architecture-proposal.md:5", "docs/design/orqlet-architecture-proposal.md:5095", "docs/design/orqlet-architecture-proposal.md:5105", "docs/design/orqlet-architecture-proposal.md:5732"]
    note: "Q-07 and Q-08 are recorded as answered on 2026-10-25 while other lines of the same proposal still treat Q-07 as an open decision and section 26.12.4 lists both under 'Unresolved'."
    merged_from: ["inventory-design-records-models/C-1", "inventory-design-records-models/C-2"]
  - id: C-9
    sources: ["docs/design/orqlet-architecture-proposal.md:5", "docs/design/orqlet-architecture-proposal.md:3043", "docs/design/harness2-fit/design/manifest.yaml:159", "docs/design/orqlet-implementation/design.md:6", "docs/design/orqlet-implementation/adr-005-deterministic-renderers-and-golden-tests.md:3"]
    note: "The proposal header and the harness2-fit design say 'approved' on the strength of a conversational statement, while the proposal defines approval as a merged pull request with code-owner review; the orqlet-implementation records disagree on status among 'nothing approved', 'decisions approved as recommended', 'executed', 'proposed' and 'draft, awaiting acceptance'."
    merged_from: ["inventory-design-records-models/C-3", "inventory-design-records-models/C-10"]
  - id: C-10
    sources: ["docs/design/orqlet-architecture-proposal.md:2449", "docs/design/orqlet-architecture-proposal.md:3434", "docs/design/orqlet-architecture-proposal.md:2525", "docs/design/orqlet-architecture-proposal.md:4444", "docs/design/orqlet-architecture-proposal.md:3432", "src/orqlet/application/usecases/validate_records.py:327-333", "src/orqlet/domain/independence.py:39-54"]
    note: "The proposal contradicts itself and the code on what a model change does: 14.1 says it never changes a gate while 17.12.5 says it can make evidence stale and a gate NOT_RUN; 14.9.3 computes family independence from the configured family while FM-O03 derives it from the observed model; the Coder's tier hint is 'balanced to strong' in 10.3 and `balanced-general` in 24.1; the proposal says an unapproved binding is NOT_RUN while the validator reports ORQ-E415 (FAIL); the proposal defines an 'I1 provisional' state that the code does not derive."
    merged_from: ["inventory-design-records-models/C-6", "inventory-design-records-models/C-8", "inventory-design-records-models/C-13", "trace-review-flow/C-5", "trace-review-flow/C-10"]
  - id: C-11
    sources: ["docs/design/orqlet-architecture-proposal.md:4496", "docs/design/orqlet-m2-workflow/plan.md:143-162", "src/orqlet/workflow/identity.json:4", ".orqlet/project-profile.yaml:171-172", ".orqlet/versions.yaml:3-4"]
    note: "Version records disagree: 22.0 and the M2 plan record workflow 0.3.0 as built while identity.json says 0.4.0 and releases.json records only 0.1.0; the profile pins Orqlet 0.1.0 while versions.yaml pins the CLI at 0.3.0."
    merged_from: ["inventory-design-records-models/C-11", "inventory-model-contracts-cli/C-7"]
  - id: C-12
    sources: ["src/orqlet/workflow/rules/orqlet-workflow.md:5", "src/orqlet/workflow/rules/orqlet-workflow.md:6", "src/orqlet/application/usecases/diagnose.py:96-114", "src/orqlet/application/usecases/render_all.py:121-127", "src/orqlet/application/usecases/workflow_sources.py:140-170"]
    note: "The generated workflow rule says a protected file that differs from the render of the pinned release fails review and that a generated file's source is the profile, the policy or the standards; doctor compares the lock's recorded hash and not a fresh render, role files are built only from the workflow package, and `client_version` is declared 'recorded when known' but is never passed or read."
    merged_from: ["trace-upgrade-role-files/C-1", "trace-upgrade-role-files/C-2", "trace-upgrade-role-files/C-3"]
  - id: C-13
    sources: ["src/orqlet/workflow/skills/orqlet-review/skill.md:25", "src/orqlet/application/usecases/binding_inputs.py:95", "src/orqlet/domain/independence.py:6-8", "src/orqlet/domain/independence.py:39-54", "src/orqlet/workflow/skills/orqlet-review/skill.md:32", "src/orqlet/application/usecases/validate_records.py:201-219", "src/orqlet/workflow/roles/orqlet-arch-reviewer.md:6", "src/orqlet/application/usecases/review_prepare.py:110-133"]
    note: "The review skill and code disagree: the skill says a change never staged is not reviewed while `review prepare` falls back to the HEAD tree; the docstring and skill tie I0 to persona adoption and I1 to a packet-only fresh context while `derive_independence` has no input for either; the skill stops after three rounds while the validator sets no limit; the role text lists a packet of snapshot, diff, plan, design, standards and two records while the code exports every tracked file."
    merged_from: ["trace-review-flow/C-1", "trace-review-flow/C-2", "trace-review-flow/C-3", "trace-review-flow/C-4"]
  - id: C-14
    sources: ["src/orqlet/workflow/skills/orqlet-onboard/skill.md:3", ".claude/skills/orqlet-onboard/SKILL.md:4"]
    note: "The onboard skill description uses wording that suggests an agent may start it, while every packaged skill renders with `disable-model-invocation: true` because load_skills never sets agent_may_start."
    merged_from: ["inventory-roles-skills-render/C-3"]
  - id: C-15
    sources: ["src/orqlet/adapters/render/roles.py:1-6", "src/orqlet/adapters/render/roles.py:41-46", "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md:15-19"]
    note: "The roles.py docstring names `sandbox_mode = \"read-only\"` in a Codex custom agent file as the strongest read-only control the client documents, and codex_role writes it; the current Codex subagent page says `sandbox_mode` placed in a custom agent file does not override the parent configuration and that custom agent instructions do not create a separate read-only sandbox. The proposal's section 10.5 record already says Codex cannot make a reviewer read-only."
self_check:
  schema: orqlet.self-check/v1
  checked_against:
    role: researcher
    phase: research
    confirmed_requirements: ["Facts only; no recommendation in the facts or the brief.", "Distinguish implemented behaviour, approved but unimplemented design, proposals, contradictions and unknowns.", "Research every model named in the request's candidate lists, Grok included, and keep documented, approved, account-eligible, callable-verified and evaluated separate.", "Keep the Fable exclusion as the person confirmed it (the Claude Code `fable` alias only, Q-7).", "Ask about account access (Q-4, Q-10) and refresh cadence (Q-8) and about policy decisions in the ledger.", "Run no paid evaluation and no model call; an evaluation that did not run is NOT_RUN.", "Stop for the person's acceptance before design.", "Record the person's later decisions: selection on Auto (Q-18) and approval of a code review gate (Q-19); check whether Auto exists in all clients."]
    applicable_standards: ["orqlet standards for --path src/orqlet/workflow/** --phase research --role researcher: 10 rules, applicable_rules_hash 03dd4e37f75d033df99354ddeba18461f2202477422361db3bc0a0ba62b4b3e1", "orqlet standards for --path src/orqlet/adapters/render/** --phase research --role researcher: 9 rules, applicable_rules_hash 59e02a76ac2fc01a95c29c48065ac2d87abcfe57b540b55f94ff9e12acbc2909", "orqlet standards for --path src/orqlet/application/contracts/** --phase research --role researcher: 11 rules, applicable_rules_hash 59a5c666671d2ebb2ac9fdcce19cf2c57a455cf6c9e15dee02c55e49c83cf41c", "orqlet standards for --path .orqlet/** --phase research --role researcher: 3 rules, applicable_rules_hash 7cedb45ea31f8900517dcaca99243b1d35b05b37792a98fd1c45d16b2bf75038"]
    acceptance_criteria: []
    evidence: ["docs/design/dynamic-model-profiles/evidence/web/anthropic-models-overview.md", "docs/design/dynamic-model-profiles/evidence/web/claude-code-model-config.md", "docs/design/dynamic-model-profiles/evidence/web/claude-code-skills.md", "docs/design/dynamic-model-profiles/evidence/web/claude-code-sub-agents.md", "docs/design/dynamic-model-profiles/evidence/web/codex-models.md", "docs/design/dynamic-model-profiles/evidence/web/codex-subagents.md", "docs/design/dynamic-model-profiles/evidence/web/cursor-help-available-models.md", "docs/design/dynamic-model-profiles/evidence/web/cursor-help-pricing.md", "docs/design/dynamic-model-profiles/evidence/web/cursor-models-and-pricing.md", "docs/design/dynamic-model-profiles/evidence/web/cursor-router.md", "docs/design/dynamic-model-profiles/evidence/web/cursor-subagents.md", "docs/design/dynamic-model-profiles/evidence/web/google-gemini-4-argon-model-card.md", "docs/design/dynamic-model-profiles/evidence/web/openai-gpt-6-astra-and-pricing.md", "docs/design/dynamic-model-profiles/evidence/web/xai-models.md"]
  checks:
    - {what: "This file validates against the AS-IS rules", how: "orqlet validate as-is docs/design/dynamic-model-profiles/as-is.md", result: pass}
    - {what: "The question ledger validates", how: "orqlet validate ledger docs/design/dynamic-model-profiles/questions.yaml", result: pass}
    - {what: "Every fact's evidence resolves at the base revision with its sha256", how: "orqlet evidence cite for every cited path and line span, at the base revision in header.bound", result: pass}
    - {what: "Quoted excerpts of six saved web pages are verbatim", how: "a script compared the quoted segments of at least 18 characters in the evidence files for the Claude Code model-config, sub-agents and skills pages, the Codex subagents page and the Cursor subagents and models-and-pricing pages with the saved page text: 111 segments and 0 missing before the Auto items were added; the Claude Code model-config file was re-checked after items 24 to 29 were added (40 segments, 0 missing)", result: pass}
    - {what: "Quoted excerpts of eight web pages returned inline are verbatim", how: "the Codex models page (including items 16 to 19), the OpenAI Astra and pricing pages, the Cursor Router page, the Cursor help pages on available models and on pricing, the Anthropic overview, the xAI page and the Gemini model card were copied from the tool output and were not re-compared by a script", result: not-run}
    - {what: "Approved local command (Q-5): claude --version printed 2.1.303 (Claude Code)", how: "claude --version", result: pass}
    - {what: "Approved local command (Q-5): agent --version printed 2026.02.13-41ac335", how: "agent --version", result: pass}
    - {what: "Approved local command (Q-5): agent models returned a model list", how: "agent models printed 'No models available for this account.' with exit status 0", result: fail}
    - {what: "Approved local command (Q-5): codex --version", how: "no codex command is on the PATH", result: not-run}
    - {what: "Approved local command (Q-5): codex debug models --bundled", how: "no codex command is on the PATH", result: not-run}
    - {what: "Any call to a model, callable verification or evaluation of a model", how: "none was run and no scope or budget is approved (Q-16)", result: not-run}
    - {what: "The repository's own lint, type, test and CI commands", how: "research records commands found in project files and runs none", result: not-run}
    - {what: "The person accepted this AS-IS file", how: "the person answered 'Yes, I accept the revised AS-IS file' to the acceptance question of the research skill at 2026-11-04T17:52:10+0200; the person commits the file", result: pass}
    - {what: "Every unknown and contradiction of the five researchers is kept once in merged_from", how: "a script compared the merged_from entries with the 47 unknowns and 36 contradictions the fragments reported: 47 of 47 and 36 of 36 found, none twice", result: pass}
    - {what: "Six subagent-reported facts match their cited lines", how: "the cited lines of the protected-set digest, the independence derivation, the review minimum, the review-prepare reviewer list, the tester record and compose were printed and read", result: pass}
    - {what: "Facts read from the repository by subagents were re-read by the main agent", how: "the main agent re-read roles.py, skills.py, model_policy.py, role_bindings.yaml, rules.yaml, project-profile.yaml and the review skill and cited the rest as the subagents reported; every cited span resolves, but not every statement was re-read line by line", result: not-run}
  failures: ["`agent models` printed 'No models available for this account.' (exit status 0), so no client-side model catalog was obtained for Cursor."]
  unverified: ["Account eligibility, callable verification and evaluation of every candidate model (NOT_RUN).", "Whether the clients behave as their current pages document on these accounts.", "Fact statements taken from subagent reports were not each re-read line by line (see the checks).", "Eight evidence files were copied from inline tool output and were not mechanically compared with the page text.", "The Gemini API model pages were not read (two fetches timed out); the fragments of the five subagents were merged by hand and not kept as files."]
  questions: ["Q-10", "Q-11", "Q-15", "Q-17", "Q-20", "Q-21", "Q-22", "Q-23", "Q-24", "Q-25"]
---

# AS-IS: dynamic model profiles

This file is a facts-only record. The front matter holds the facts, unknowns and contradictions with their evidence; this text summarises them and contains no advice. Fact ids are written as A-n, inferences as I-n, unknowns as U-n and contradictions as C-n.

## Request

The person asked, for the task `dynamic-model-profiles`, to research model selection for Orqlet's skills, subagents and review workflow across Codex, Cursor and Claude Code. The request covers dynamic selection by task requirements, quality and cost, and manual selection of the team's preferred models, with logical policies kept apart from concrete model identifiers and with Orqlet's standards, permissions, evidence requirements, review independence and human approval gates preserved.

The confirmed requirements in the request: architecture, design and planning prioritise quality; PR titles, descriptions and summaries use the cheapest qualified model; code review is an explicit responsibility; the code reviewer uses a different resolved model from the coder inside the same approved capability category; every review starts from scratch in a fresh isolated context; architecture and security reviews keep their required quality; Grok is included in Cursor's research and candidate mappings; the full approved model catalog is discovered and evaluated; the team can select preferred models manually and change its defaults; account access is asked about before executable assignments are final; and the repository's Fable exclusion is preserved. The request defines three starting profiles (QUALITY, ENGINEERING, ECONOMY) with starting candidates from research dated 2 November 2026, asks for a precedence order to be approved during design, and asks for acceptance after this research and approval after design and plan.

Requirements restated from the request, for traceability (they are requirements and not facts about the code):

- Manual selection: the team can change default models for each client; change models by logical profile, skill, task or subagent; choose preferred candidates and their order; pin an exact supported model or deliberately use a supported alias; choose manual mode, automatic mode or automatic mode with explicit approved fallbacks; preview and validate a change before applying it; and revert to an earlier approved mapping. An explicit valid team selection takes precedence over automatic ranking. The precedence order covers an explicit task or session override where supported, a team assignment for the role or skill and client, a team assignment for the logical profile and client, and the approved automatic policy; the person approves it during design.
- Manual preferences still satisfy client compatibility, organisation restrictions, required capabilities, reviewer diversity and permissions. An unevaluated requested model is a candidate with its evaluation and access status marked honestly. An unavailable or incompatible model is reported with the exact reason and never silently replaced. The source of each selection is recorded (manual override, team default, automatic ranking or explicit fallback). Personal settings and credentials are not changed.
- Code review: the same approved capability category as the coder, a different resolved model identity, a different model family where supported, an independent quality threshold, no silent self-review (an independent session or human review when no alternative qualifies) and no silent lowering of review quality. Changing effort, speed, context size or an alias that resolves to the same model does not count as diversity.
- Fresh review: each code, architecture and security review starts in a new isolated context with the exact snapshot and diff, the approved requirements, design, plan and criteria, the standards, repository context, test evidence and review records, and without the coder's conversation, memory, reasoning, self-assessment, own findings or earlier review conclusions. Every re-review covers the full agreed scope. Reviewers stay read-only. The result is NOT_RUN when no fresh context exists.
- Selection and refresh: task, then logical profile, then eligible client-specific model; native selection when a task runs is kept apart from selection applied when generated files are refreshed; fallback and escalation are explicit; cost is compared per accepted result; requested and observed model identities are recorded where available; new releases do not establish approval or better quality.
- Tools and rules: deterministic tools produce hashes, validation and test results; a model never replaces deterministic evidence or grants permission; the rules ORQLET-ARCH, SEC, SAFE, NOMODEL, DET, TEST, QA and STYLE keep their stated enforcement.
- Evaluation: factual accuracy, tracing, design, planning, behavioural tests, missed review defects, false positives, fresh-review compliance, PR-summary accuracy, latency and cost per accepted result, with acceptance criteria for manual selection, precedence, invalid overrides, fallbacks, alias resolution and regeneration; no paid evaluation without an approved scope and budget.

## Scope

Covered, by five read-only subagents run in parallel (three inventory researchers and two tracers): the workflow package's roles and skills; the renderers and client adapters; the generated agent, skill and rule files and the lock; the model-policy, role-bindings, review and plan contracts, their validators and the CLI; the review flow; AGENTS.md, `.prompts/`, README and every record under `docs/design/`. Covered by the main agent from current official pages (stored as fourteen evidence files, all retrieved on 2026-11-04): Claude Code model configuration, subagents and skills; Codex subagents and models; OpenAI's GPT-6 Astra page and API prices; Cursor subagents, models and pricing, Cursor Router and Cursor's help pages on available models and on pricing; Anthropic's models overview; xAI's models page; and Google DeepMind's Gemini 4 Argon model card.

Local commands approved in Q-5 and run: `claude --version` printed 2.1.303 (Claude Code); `agent --version` printed 2026.02.13-41ac335; `agent models` printed "No models available for this account." with exit status 0; `codex --version` and `codex debug models --bundled` were not run because no `codex` command is on the PATH. These outputs are not file evidence and are recorded here and in the self-check.

Not covered, NOT_RUN: any call to a model, any callable verification, any evaluation of model quality or cost per accepted result (no scope or budget is approved, Q-16), user-level client settings, signed-in pages, the Gemini API model pages (two fetches timed out), and any check of the repository's own CI commands (research records commands and runs none).

Answers that shaped the scope: public official pages only (Q-2); models that official pages do not confirm are listed as unknowns (Q-3), and the official pages did confirm every model named in the request's candidate lists; all three clients are in scope with no plan or access detail given (Q-4, Q-10); no vendor restriction applies (Q-6); the Fable exclusion covers the Claude Code `fable` alias only (Q-7); the refresh cadence is every Orqlet release (Q-8); design reopens Q-07 (Q-9). After the file was first accepted, on 2026-11-04 at 17:05, the person added: the Codex client is the desktop app (Q-12); 'no fable avalible.' (Q-13); 'all devs can approve' (Q-14); 'we have 2000$ per client.' (Q-16, with no stated period or scope, so Q-22 is open and no evaluation runs); 'the model will be selected on auto' (Q-18); and 'I approve code review gate.' (Q-19). The person also asked whether Auto is available in all clients; the next subsection records what the pages document.

## Existing capabilities and behaviour

### What exists in the repository today (implemented)

Roles and skills. The workflow package ships five subagent roles, `orqlet-arch-reviewer`, `orqlet-inventory`, `orqlet-security-reviewer`, `orqlet-tester` and `orqlet-tracer`, and six skills, onboard, research, design, plan, implement and review (A-1, A-3, A-2). A source file with a `model` key is refused by the loader (A-5). No role named `orqlet-code-reviewer` or `orqlet-knowledge-writer` exists, and the review skill starts only the architecture and the security reviewer (A-1, A-62). No skill step writes a pull-request title, description or summary: Orqlet renders the team and workflow blocks of the pull-request template, and the implement skill ends with the person opening the pull request (A-144, A-145). The conventions block records the pull-request shape, the squash merge and the reviewer (A-146).

Rendering. A role renderer receives a `ClientRole` with no model or effort field and a `RenderRequest` with no model-policy or role-binding field (A-7, A-8, A-16). Claude Code and Cursor agent files get the literal `model: inherit`; Codex agent files get no model key and `sandbox_mode = "read-only"` for read-only roles; no client gets a reasoning-effort field (A-9, A-10, A-11). Skills render without a model field and, for workflow skills, with `disable-model-invocation: true` (A-13, A-6, A-14). The three adapters render no settings, `config.toml` or model file (A-15). Golden files pin these bytes and a test fails when a role file names a vendor model (A-28, A-29, A-31, A-30, A-32).

Ownership. Generated role, skill and rule files are protected lock rows; a tampered protected file is restored by `orqlet upgrade` with warning ORQ-W096, `doctor` compares files with the hashes recorded in the lock, and a change to a seeded file is written as a pending diff and not as a write (A-23, A-19, A-26, A-21, A-25, A-20, A-18, A-17). `.orqlet/role-bindings.yaml`, `.orqlet/project-profile.yaml` and `.orqlet/versions.yaml` are seeded, team-owned files, `.prompts/` is a seeded standards folder that the team edits, and there is no `model-policy.yaml` (A-24, A-141, A-142, A-40, A-22).

Model-policy contract. `orqlet.model-policy/v1` exists as a contract with a committed schema and a draft test fixture (A-33, A-34, A-35, A-36, A-39). It has no discovered, approval, callable, evaluated, availability, fallback or escalation field and no cross-reference validator (A-37). No module other than the registry references it, the profile has no `model_policy` key, and no CLI command loads, validates or renders a policy (A-38, A-41, A-43, A-42).

Review and independence. Review records carry `model_requested`, `model_observed` and `coder_binding` (A-51). Independence is derived from the client and from `model_families`, which is empty in this repository, so only a different client yields I2; I3 is never derived and context freshness is not an input (A-49, A-50, A-46). A class below the minimum (I2 for D3) is NOT_RUN, an unapproved binding is the error ORQ-E415, and a changed reviewer definition or code makes a record stale (A-53, A-54, A-55, A-56). No component covers a model or a model policy, `gate status` reads no review record or binding, and `review prepare` takes a fixed reviewer list (A-56, A-57, A-58). Code reads only a binding's id, role and client and `model_families`; the other binding fields are unread (A-45, A-47, A-48). Review roles are limited to the architecture and security reviewer in the record, path and plan contracts (A-52). The recorded reviews hold null model fields in every record, and one I2 record states that the reviewer did not report its model (A-65). The packet is written outside the repository, holds a snapshot, diff and context copies, and carries no model or client field; the tester's record has none either (A-59, A-60, A-61). The reviewer role text and review skill tell the reviewer to receive only the packet path, and one review record states that its packet held earlier review notes (A-63, A-62, A-64). A Cursor session of 2026-10-23 reported `inherit` as blocked by the team's admin settings (A-66).

Instructions and rules. AGENTS.md and `.prompts/rules.yaml` hold no rule on model selection, pins, profiles or reviewer independence; ORQLET-NOMODEL-001 states that Orqlet calls no model and starts no agent (A-67, A-69, A-68). Rule enforcement is: deterministic checks for ARCH, DET, TEST and QA rules; review for SEC, SAFE and NOMODEL; guidance for STYLE (A-143). CI defines lint, types, architecture, tests and build jobs and runs no Orqlet validator (A-44). The README repeats the I1, I2 and `model_families` behaviour (A-70).

### What the architecture document states (design text, not implementation)

The architecture document's header records approval of v0.5 in conversation, with no merged pull request and no independent review of the v0.5 changes, and says section 14.9 was added after the independent reviews (A-71, A-73). Its legend marks [R] as not approved and [P] as a name or schema that is not yet an existing API (A-72). It describes: tier hints and per-role pins rendered by `orqlet upgrade` from an approved policy, with main-agent roles never pinned (A-74, A-75); a pin-rendering rule with ranks and prices supplied by owners, a `missing-candidate` state and a stale review after a pin change (A-76); an opt-in `orqlet models refresh` (A-77); model-policy v2 with four separate states, fallback and escalation, an `excluded.models: [fable]` entry and starter profiles (A-84); a Code Reviewer subagent as a provided capability with Q-07 answered as not a required gate (A-79, A-80); reviewer independence classes and substitutions (A-81, A-82); and a roadmap that places pins in M2 and `models refresh` and `admin export` in M7 (A-85). The Fable exclusion exists only as this text, which infers without verification that Fable is Claude Code's `fable` alias (A-78). Other records say per-role pins are in M2 scope, out of scope for Plan A, or only the rework listed in section 22.0 (A-86, A-87, A-83). Their approval states disagree (C-8, C-9). Items of this section that no code or shipped file backs: pins, model-policy v2, `models refresh`, `admin export`, the Code Reviewer role, review-input v2 and `model_binding` (C-1 to C-7).

### Automatic selection (Auto) in each client

The person stated that the model will be selected on auto (Q-18) and asked whether Auto is available in all clients. The fetched official pages document the following; the three clients do not offer the same thing.

| Client | What is documented |
|---|---|
| Cursor | An Auto choice in the model picker that selects models for each request and can vary between turns (A-154). Auto is available in all regions, is absent from the Plus plan, is limited to Cost mode on individual plans, and Balance and Intelligence need Teams or Enterprise with the router enabled (off by default on Enterprise) (A-158, A-129, A-130). The router's pool is GPT-5.5, Claude Opus 5, Grok 4.6 and Claude Fable 5; it changes over time and skips models that an enterprise admin blocks (A-155, A-131). The routed model is hidden unless an admin sets visibility to Displayed (A-132, A-156). Auto applies to the parent agent; built-in subagents choose a model for the subtask and custom subagents default to `inherit` or name a model ID (A-157, A-118). It is documented across the Agents window, editor, CLI, SDK and the iOS app (A-159). |
| Codex (desktop app) | No Auto mode and no per-task router on the official models page; a default Power setting with presets from Luna High to Astra Extra High, an Advanced choice of model, effort and speed, and a default model that OpenAI selects when none is set (A-151, A-152, A-153). A subagent inherits the parent's model and effort unless a file, a default or a spawn request sets them (A-106). |
| Claude Code | No `auto` alias. `default` resolves to the account-type or organisation default model, and `opusplan` uses Opus in plan mode and Sonnet in execution mode (A-148, A-149, A-150). A subagent without a `model` runs on the main conversation's model (A-101, A-100). |

Whether a Cursor custom subagent that inherits from an Auto parent is routed per request, whether the Codex default picks a model per task, and whether 'auto' covers the reviewers are unknown (U-28 to U-30); the scope of the approved code review gate is unknown (U-31).

### Client capability matrix (from current official pages, retrieved 2026-11-04)

| Capability | Claude Code | Codex | Cursor |
|---|---|---|---|
| Per-agent model | `model` in subagent frontmatter: alias, full ID or `inherit` (A-100) | `model` and `model_reasoning_effort` in a custom agent file, `[agents]` defaults, explicit spawn value (A-106, A-109) | `model` in subagent frontmatter: `inherit` (default) or an ID with bracketed options (A-118) |
| Reasoning effort | `effort` field, low to max (A-100) | `model_reasoning_effort`; Astra Light is `low`, Luna supports Max but not Ultra (A-115) | `effort=` option in brackets (A-118) |
| Skill-level model | `model` and `effort` frontmatter last for the rest of the turn and are not saved; with `context: fork` they set the forked subagent (A-104, A-105) | skills inherit from the parent; no skill-level model in the fetched pages (A-147) | no skill-level model in the fetched pages |
| Precedence | `/model`, `--model`, `ANTHROPIC_MODEL`, `model` setting, `ANTHROPIC_DEFAULT_MODEL`; subagent: per-invocation alias, frontmatter, `CLAUDE_CODE_SUBAGENT_MODEL`, main model (A-94, A-101) | file value, over spawn value, `[agents]` default, parent (A-107) | picker and Auto apply to the parent; subagent frontmatter or the parent's launch request (A-120) |
| Alias behaviour | aliases move with the vendor; `best` follows `fable` (A-88, A-92, A-89) | model names such as `gpt-6.1-sol`; retirements replace names (A-111, A-114) | model IDs; Auto routes by mode (A-128) |
| Organisation restriction | `availableModels` and related keys cover subagent and skill models; blocked values fall back (A-97, A-95, A-96) | plan, workspace and administrator enablement (A-113) | team admin blocks; the configured model is replaced by a compatible one (A-119) |
| Inherited permissions | tools and MCP tools inherited, narrowed by filters (A-140) | sandbox, approval, provider and MCP settings inherited; a custom agent file cannot replace them (A-108) | all parent tools including MCP; `readonly: true` blocks edits and state-changing commands (A-122) |
| Clean context | fresh unless the subagent is a fork; forks start on their own by default (A-103) | not stated in the fetched pages (U-10) | clean context (A-122) |
| Different model family inside one agent tree | `model` takes Claude aliases or Claude IDs (A-100) | provider is inherited (A-108) | a subagent can run a named third-party model (A-120) |
| Router | none in the fetched pages | none in the fetched pages | Cost, Balance, Intelligence on Teams and Enterprise only; not hand-pickable; respects Enterprise access controls (A-129, A-130, A-131) |
| Automatic model selection | no `auto` alias; `default` and `opusplan` (A-148, A-149, A-150) | OpenAI-selected default model and Power presets; no router named (A-151, A-153) | Auto with Cost, Balance and Intelligence modes (A-154, A-158) |
| Visibility of the model used | `modelUsage` in JSON output, `/tasks` (A-99) | not stated in the fetched pages (U-3) | task card and usage dashboard; routed model hidden by default (A-121, A-132) |
| Substitution paths | fallback chains reach subagents; safety fallback; blocked-value fallback (A-98, A-96) | retired names need replacement (A-114) | compatible-model fallback (A-119) |
| Read-only agent | `tools` allowlist in the definition (A-100) | no separate read-only sandbox from a custom agent file (A-108) | `readonly: true` (A-122) |
| Version seen here | 2.1.303, which meets the minimums for Opus 5.5, Sonnet 5.5 and Haiku 5.5 (A-93) | desktop app named by the person; version unknown, no `codex` on PATH (U-21) | `agent` 2026.02.13-41ac335 and no models listed (U-20) |

### Model candidates and the evidence for each

Every model name in the request's candidate lists is documented by an official page. The states approved, account-eligible, callable-verified and evaluated are separate: no catalog of approved models exists (U-5), account eligibility is unknown for every model (U-19), and callable verification and evaluation are NOT_RUN for every model (U-24). No approved capability classification exists, so no model has an approved category; price, brand and vendor labels do not establish one.

| Model | Where documented | Documented by |
|---|---|---|
| GPT-6 Astra (`gpt-6-astra`) | Codex; OpenAI API; not in Cursor's price table | (A-111, A-116, A-117, A-127) |
| GPT-6.1 Sol (`gpt-6.1-sol`) | Codex; OpenAI API | (A-111, A-110, A-117) |
| GPT-6 Luna (`gpt-6-luna`) | Codex; OpenAI API | (A-111, A-115, A-117) |
| GPT-6.1 Terra (`gpt-6.1-terra`), not in the request's lists | Codex CLI 0.159.0 or later | (A-112, A-117) |
| Claude Opus 5.5, Sonnet 5.5, Haiku 5.5 | Claude Code; Anthropic API; Cursor | (A-89, A-134, A-125, A-93) |
| Claude Fable 5.1 (reached by the `fable` and `best` aliases and by ID) | Claude Code; Anthropic API; Cursor (also named in the router pool); not available to the accounts per Q-13; excluded alias | (A-88, A-90, A-134, A-125, A-155, A-78) |
| Grok 4.7 | Cursor (included on the Plus plan); xAI API | (A-123, A-124, A-136) |
| Composer 2.5 | Cursor (included on the Plus plan) | (A-123, A-124) |
| Gemini 4 Argon | Cursor; Gemini API and AI Studio per the model card | (A-126, A-138, A-139) |
| GPT-5.6 Sol, Terra and Luna | Cursor; OpenAI API (Sol price) | (A-126, A-117) |
| Gemini 3.8 Flash | Cursor | (A-126) |

Vendor statements about capability are vendor claims: xAI calls Grok 4.7 its most capable model, OpenAI positions each Codex model by task type, and Google's benchmark table compares Argon with models and benchmarks the vendor chose (A-136, A-111, A-139). No evidence in the repository or in the fetched pages measures code-review quality, review-defect detection, false positives or cost per accepted result for any model.

Documented API list prices per million tokens, short context (input / output): Astra $10 / $50, GPT-6.1 Sol $2 / $10, GPT-6.1 Terra $1 / $5, GPT-6 Luna $0.10 / $0.50 (A-117); Opus 5.5 $4 / $20, Sonnet 5.5 $2 / $10, Haiku 5.5 from $0.10 / $0.50, Fable 5.1 $10 / $50 (A-134); Grok 4.7 $2 / $6 (A-136). Cursor's own list shows Composer 2.5 at $0.5 / $2.5 and Gemini 4 Argon at $2 / $10 (A-124, A-126). Cursor bills named third-party models at list price from prepaid credit, adds a token rate on Teams and Enterprise, and draws Cursor models from a weekly pool (A-123, A-121). The Codex subscription and credit rates were not retrieved (U-24).

### Where the request's assignments map to existing responsibilities

Existing: onboard, research, design, plan, implement and review skills; inventory, tracer, tester, architecture-reviewer and security-reviewer subagents (A-2, A-1). Not existing in code or shipped files: a code-reviewer role, a PR title, description and summary responsibility, a knowledge-writer role, any per-skill or per-role model profile, and a team model-selection source (A-1, A-52, A-144, A-40). Described only in the architecture document: the Code Reviewer, pins and profiles (A-79, A-75, A-84).

## Inferences

- I-1 Cross-family review inside one client's subagent tree is documented only for Cursor: Claude Code's `model` values are Claude aliases or IDs, Codex subagents inherit the provider, and Cursor subagents can run a named third-party model (A-100, A-108, A-120). A cross-family pair inside Claude Code or Codex would need a second client or session. This is confirmed by a test of a subagent running a non-Claude model in Claude Code and a non-OpenAI model in Codex.
- I-2 With the repository's empty `model_families`, the current independence derivation cannot show that two reviews used different models inside one client, because the family is None for every model (A-50, A-46). A record with a populated `model_families` and non-null model fields would confirm that the derivation changes.
- I-3 The generated role files can hold no model choice other than `inherit`, and the only per-project input a role renderer has is the choice of clients (A-9, A-10, A-11, A-16, A-18). A render of the roles after adding a role-binding or policy input to a request would confirm where a variation point would have to enter.
- I-4 An exclusion of the `fable` alias alone leaves the `best` alias and explicit Fable IDs as other paths to the same model in Claude Code, and Cursor lists Fable 5.1 under its own name (A-88, A-90, A-134, A-125). The answer to Q-13 would confirm which paths the exclusion is meant to cover.
- I-5 The existing seeded, team-owned files and the pending-diff path for seeded changes are the only team-owned, reviewable configuration mechanism that already exists, and the model-policy contract is the only model-related contract that exists (A-24, A-21, A-141, A-33). A comparison with the design's chosen location would confirm whether either is reused.
- I-6 Codex's custom agent `sandbox_mode` key is rendered by Orqlet while the current Codex page documents it as not overriding the parent (C-15) (A-11, A-108). An observation of a Codex custom agent run with the generated file would confirm the effective sandbox.
- I-7 A change of model on an existing reviewer file changes the `reviewer_definition` digest and makes recorded reviews stale, because the digest covers the agent file bytes (A-55, A-56). A review record recomputed after changing the `model` line of an agent file would confirm it.
- I-8 Because Cursor Router hides the routed model by default and is not hand-pickable, a review run under Auto cannot be shown to differ in model from the coder's under the documented controls (A-130, A-132, A-120). An admin setting that displays the underlying model would confirm what a record could hold.
- I-9 Only Cursor documents an automatic model router; Codex documents a default and presets and Claude Code a default and `opusplan`, so 'auto' does not name one mechanism across the three clients (A-154, A-153, A-150, A-151, A-149). An official page that documents a router for Codex or Claude Code would contradict this.
- I-10 Under Cursor Auto a review can run on a model that no generated file names, that can differ between turns and that stays hidden unless an admin sets Displayed, so a record's `model_requested` could not name it and `model_observed` is available only with that setting (A-154, A-132, A-156, A-51, A-50). A review record produced in a Router session would confirm which values it can hold.
- I-11 The documented router pool names Claude Fable 5, so excluding the `fable` alias in a file does not control what Auto routes to; the control the pages document is an enterprise admin block (A-155, A-78, A-88). The team's Cursor admin settings would confirm whether Fable is blocked (Q-24).

## Open questions

Answered in the ledger: Q-1 to Q-9, Q-12 ('I use desktop codex.'), Q-13 ('no fable avalible.'), Q-14 ('all devs can approve'), Q-16 ('we have 2000$ per client.'), Q-18 ('the model will be selected on auto') and Q-19 ('I approve code review gate.'). Open in the ledger: Q-10 (plan and access of the three accounts, U-19), Q-11 (`agent models` returned no models, U-20), Q-15 (standing of the v0.5 model sections, U-6), Q-17 (meaning of dynamic selection under the IDE-first boundary, U-26), Q-20 (reach of Auto over roles and clients, U-30), Q-21 (scope and class of the code review gate, U-31), Q-22 (what the 2000 dollars per client may be spent on, U-24), Q-23 (organisation restrictions and approval by a change's author, U-23), Q-24 (Fable 5 in the Cursor Router pool, U-22) and Q-25 (version of the Codex desktop app, U-21).

Unknowns without a question: how clients report a subagent's model (U-3), where `coder_binding` values come from (U-4), whether Codex subagents have a clean context (U-10), whether `inherit` counts as a pin (U-11), whether recorded reviews used fresh contexts (U-12), user-level client settings (U-13), host rules (U-15), test gaps (U-16) the Cursor model IDs of the candidates (U-25), the routing of an inheriting Cursor subagent under Auto (U-28) and whether the Codex default picks a model per task (U-29).

Contradictions: C-1 to C-15 in the front matter, among them the Code Reviewer's existence (C-1), pin rendering (C-2), model-policy v2 and the profile key (C-3), review-input v2 (C-4), unread binding fields (C-5), the missing-candidate stop (C-6), unbuilt CLI commands (C-7), Q-07 and Q-08 status (C-8), approval status (C-9), the rendered Codex `sandbox_mode` (C-15). The person approved a code review gate (Q-19) after C-8 was recorded; the architecture document still records Q-07 as not a required gate.

## Inputs for design

- The existing renderers, seeded team files and pending-diff path, and the model-policy v1 contract, with the absence of any renderer input for a policy (A-9, A-10, A-11, A-16, A-21, A-24, A-33, A-37).
- The IDE-first rule and the open question of what dynamic selection means under it (A-68, A-74, A-75) (U-26, Q-17).
- The client capability matrix above, including the documented per-agent model and effort fields, the inherited permissions, the organisation controls, the visibility of the model used and the substitution paths.
- The state of each candidate model: documented, with approval, account eligibility, callable verification and evaluation all unestablished (U-5, U-19, U-24).
- The review machinery: independence derived from client and `model_families`, review roles limited to two, no code-reviewer role, null model fields in every record, the packet's contents and the reviewer-definition digest (A-49, A-52, A-65, A-59, A-55), with Q-07 reopened by Q-9.
- The Fable exclusion as it exists (prose only) and as the clients expose Fable (aliases `fable` and `best`, explicit IDs, Cursor's own listing) (A-78, A-88, A-90, A-125) (Q-13).
- The enforcement of the rules the request names, by deterministic check or by review (A-143, A-44).
- The precedence order and the refresh cadence: the person asked to approve a precedence order during design; the refresh cadence answered is every Orqlet release (Q-8).
- The decisions given after acceptance: selection on Auto (Q-18), approval of a code review gate (Q-19), all developers can approve models (Q-14), the Codex desktop app (Q-12), no Fable available (Q-13) and a budget of $2000 per client with no stated scope (Q-16, Q-22).
- The Auto facts per client, the router pool that names Fable 5, the hidden routed model and the absence of an Auto mode in the Codex and Claude Code pages (A-154, A-155, A-156, A-153, A-150, A-157).
- The bound values and standards of this research are in the self-check.
