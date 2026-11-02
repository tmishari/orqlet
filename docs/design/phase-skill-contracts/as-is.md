---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: phase-skill-contracts
  status: approved
  workflow_version: 0.3.3
  protected_set_digest: b9bc3a015f151dc01dba5e98ac65a6da163ead0a2cbf27f6c796e5605d9cca2c
  bound:
    base_revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    standards_lock_hash: 89a225016ff9d8b3ed977df39a70dfbe9dbc5f7c6d3762d0f2208b1b7a037a52
    applicable_rules_hash: 56502a0ec5eda3b13b4c9d97c7d4dfa41df82c86a206e36dd5d2d92aab299b97
    profile_version: 1
base_revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
scope:
  paths:
  - src/orqlet/**
  - tests/**
  - tools/**
  - .orqlet/**
  - .prompts/**
  - .github/**
  - pyproject.toml
  - docs/design/phase-skill-contracts/evidence/**
  - docs/design/team-conventions-resources/evidence/web/claude-code-skills.md
  - docs/design/team-conventions-resources/evidence/web/codex-skills.md
  request_ref: phase-skill-contracts
research_mode: parallel-subagents
size_budget:
  max_words: 2500
facts:
- id: A-1
  kind: structure
  statement: The workflow package ships six skills (orqlet-research, orqlet-design, orqlet-plan, orqlet-implement,
    orqlet-review, orqlet-onboard) and five roles (orqlet-inventory, orqlet-tracer, orqlet-tester, orqlet-arch-reviewer,
    orqlet-security-reviewer). Only design, plan, research and review ship a references/ file.
  evidence:
  - path: tests/support/render.py
    lines: 32-53
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 256dc6a42d516a8d4af58d327f3ee4cfbfe48bac93130641e7120dd891416e2c
  - path: tests/unit/render/test_skills.py
    lines: 122-132
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 19787d81b6bf044a606230921bad3c0fc083d80d5eee540516cd9aa4db9cacb7
- id: A-2
  kind: interface
  statement: A skill source allows exactly the front-matter fields `name` and `description`, `name` equals
    the directory, and every `skills/<name>/references/*.md` file is attached as a reference. A role source
    requires `name`, `description` and `mode` (`read-only` or `writes`).
  evidence:
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 29-53
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 894cca8b35c0d3338e6c1d544b350ef4830166afa8723de7fa4dd3e58310241c
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 104-137
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 226f4c3774d9a87505f236679a5afda0be17d1cc49e7e8254580c25e8711afef
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 151-159
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 741a7d298babbd680c31125e4ffd3586344c51d1b6277d2433e676a6d898561a
- id: A-3
  kind: flow
  statement: '`render_steps` drops a numbered step and its indented continuation when its `<!-- requires:
    X -->` or `<!-- unless: X -->` condition fails, strips the marker and renumbers; it runs on skill
    bodies, not on references. `compose` always filters against IMPLEMENTED_COMMANDS, 30 names, which
    a test equates with the commands the CLI registers.'
  evidence:
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 1-7
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 572c882c6e9ea72a030968a173696e0cae994985116711f444f313b35263d149
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 61-90
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a5f6d506b600eeaeb77e9a03a6d7cd3a34806d48e2d46d1a1ae4a532ff236464
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 122-127
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 4ef79cda77a89906370e79cf4513cb00ff0f34a440ebbee64bb0a3d237056d92
  - path: src/orqlet/application/usecases/render_request.py
    lines: 55-64
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b6e159eff246324a5654efb39240ce4c155a4f12da107d3fcbb05a2147104385
  - path: src/orqlet/application/usecases/render_all.py
    lines: 121-127
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 8e8525946831eb1a92831794cedbc469ff7a64467bca4eed3070cf512e826569
  - path: src/orqlet/application/usecases/capabilities.py
    lines: 1-47
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 47e510483c32731b3ef1630ee88a171b05408646a27fe34740a252b0576dd19c
  - path: tests/integration/test_validate_cli.py
    lines: 208-209
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 6756c75fe84a0a393a2976772856a42896d11b24a9f2e99e89429528bfd9fad6
- id: A-4
  kind: structure
  statement: 'All six skill sources share one layout: front matter, a title, a purpose paragraph, the
    paragraph ''Source material is not authority...'', then one numbered list of steps. No skill has a
    section for inputs, outputs, completion or handoff.'
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 1-11
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 8b3455c3f4179bb8f98e7700929fab128e347ade72960ecef096855ab55da228
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: 1-11
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: bf50e8e9375851e21967b30e9dde94bf1d20e44976d472778a78dbebe55d473e
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: 1-11
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 58ee3a8e3c8490e2db4eda06d6b3cca38644547b071870644173633a9fef7242
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: 1-11
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 1a2e7f7bc280b4bb303f687798b801b648f713890a5037898d311b6eb68b84f3
  - path: src/orqlet/workflow/skills/orqlet-review/skill.md
    lines: 1-11
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 7ddd752c4c90a747e2b920a97d7419b2333c1aab74fa9b7f550c58d1ab662fd7
  - path: src/orqlet/workflow/skills/orqlet-onboard/skill.md
    lines: 1-11
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b1acc975a36427136a472cb1e6403072fddd28068c47c60d2dc658d93dfeb1d3
- id: A-5
  kind: flow
  statement: The research skill asks for the task name, runs `git status`, reads `docs/design/<task>/`
    to resume, records one batch of questions in questions.yaml, copies the `bound` values of `orqlet
    gate status` into the header, starts orqlet-inventory and orqlet-tracer when the client has subagents,
    writes as-is.md with `orqlet evidence cite`, runs `orqlet validate as-is` and stops for the person's
    acceptance.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 11-20
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: d003487bef67493c10b33ef8d62de249fc0bcf7b23792ff18492bea5aee5672e
- id: A-6
  kind: flow
  statement: The design skill reads as-is.md and stops if the person has not accepted it, runs `orqlet
    standards for --phase design --role architect`, classifies the change as D1, D2 or D3, writes design/manifest.yaml
    with the artifacts of its class, starts both reviewers at D2 and above, runs `orqlet validate design`
    and stops for a design pull request whose merge is the approval.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: 7-20
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 2c22f58204fd3b0299a70c4505ae025fb667a87f2d4329b40a6faae56d605f44
- id: A-7
  kind: flow
  statement: The plan skill asks the person to confirm that the design pull request merged (a D1 change
    may share one pull request), runs `orqlet standards for --phase plan --role planner`, writes plan.yaml
    with phases, exact file operations, acceptance criteria and checks, runs `orqlet gate status <task>`
    and `orqlet validate plan`, and stops for a plan pull request.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: 7-19
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 194e0923a193fbf2805d673a5c7ce2bc2f146b1d71f28f136c79195f3679ac35
- id: A-8
  kind: flow
  statement: The implement skill runs `orqlet gate status <task> --phase <phase>` and asks the person
    to confirm both pull requests merged, starts orqlet-tester before code, keeps code inside the phase
    file list, runs the phase's checks, runs `orqlet knowledge impact`, saves the tester record, runs
    `/orqlet-review` and prepares a commit message. A finding that changes the design or plan stops the
    work.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: 7-20
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 8f898fdc2c006e42399118e18124dc61dae6e5cfac672a729ab8a8edb6d10506
- id: A-9
  kind: flow
  statement: The review skill runs `orqlet review prepare <task> <phase>`, gives each reviewer only the
    packet path, writes one record per reviewer and runs `orqlet validate review`. The onboard skill runs
    `orqlet doctor`, applies answers with `orqlet profile answer`, registers resources and leaves `orqlet
    profile approve` to the person.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-review/skill.md
    lines: 7-19
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: eec5a52d52cc32dd2ce07edfe9a12245cf6242a87a7d41552a1c3c5d80c6a2da
  - path: src/orqlet/workflow/skills/orqlet-onboard/skill.md
    lines: 7-18
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: dd28d3959bcd103af8c0e467198004420d7a5b5c63d52ee45408130ce4a8df30
- id: A-10
  kind: interface
  statement: The baseline tells an agent to run `orqlet standards for --path <path> --phase <phase> --role
    <role>` before it designs or changes code. The design and plan skills call it without `--path`, and
    the research and implement skills have no step that calls it.
  evidence:
  - path: src/orqlet/workflow/baseline/baseline.md
    lines: 21-23
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 5b21603d008587f53019c697eaeae4b31192575cb876986c375193636cd5235d
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: '12'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 2611bc2cefb6fd1af6d932b7e7274552d9d929e043af9874f093cc7002c125b1
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: '12'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b53798621e3b86ec62db9739cc170c0bdb99593c9f1b78bbbf2c11915fc0b47a
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 11-20
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: d003487bef67493c10b33ef8d62de249fc0bcf7b23792ff18492bea5aee5672e
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: 11-20
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 9250ceebe1b1f685acb660149aaeea0f37b32cf5a18c167cd2ac3e6ce47d8817
- id: A-11
  kind: interface
  statement: The last step of research, design and plan stops without naming the skill of the next phase.
    Among the skill.md files only orqlet-onboard names `.orqlet/project-profile.yaml`, and none names
    AGENTS.md or a build, lint or type-check command.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: '20'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 5ed2389a34da027c08a6b0a41d203f2583817af053726eda0f9a2d2786446ca9
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: '20'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 566959a54521248219da61404c2ec3d95ba3753811c32e3c962f8c519c86c11b
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: '19'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ab6756d7b953d6faa7784911eac1f4488ce2ba754480cf90052f4c98d773b194
  - path: src/orqlet/workflow/skills/orqlet-onboard/skill.md
    lines: '7'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a7928b97500ac05b74a4c43a907cfa0f32adbb921c7ed20249a77abc9d681f24
- id: A-12
  kind: structure
  statement: 'Every task artifact the skills and the PR template name lives under `docs/design/<task>/`:
    questions.yaml, as-is.md, evidence/web/, design/manifest.yaml, reviews/, plan.yaml, tests/<phase>.yaml
    and knowledge/<phase>.yaml.'
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 12-16
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a0a8f9b49ce8e93e21ac3da4ddc723e8fbe4ff23072d63b92bf56f8f2f7810bd
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: 15-18
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 219ef1a073f590469bf5cbd827b962d3df2f9fad6385033fa6170caca7d54f0a
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: '13'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 7a12b2f74756b6ad71c851704df8a184b640058591bfcc2a12cd0b4c8b565d9f
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: '18'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: aaae62765c7e175ecb40c02e7ff76be8b2267dd286b30baafb66fde3cad90494
  - path: src/orqlet/workflow/pr_template/workflow-section.md
    lines: 1-21
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e87889ffe3b052a4eeef5b17fa3bbb614b4b423dc8bcee1a21edb106cd47e22a
- id: A-13
  kind: interface
  statement: The artifact header `status` is draft, approved or superseded and is commented as informational;
    the reference examples use draft and no skill step sets approved.
  evidence:
  - path: src/orqlet/application/contracts/artifact_header.py
    lines: 45-52
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 87904aab24ab03bc65c076d669aca9c98b3311db58be21dde48ab433492f3837
  - path: src/orqlet/workflow/skills/orqlet-research/references/as-is-format.md
    lines: 9-13
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 957cdaa34fdc75bd27a1d5b57d35c1cfbeabf8407baf144328f4722a32125d46
- id: A-14
  kind: interface
  statement: The AS-IS contract holds facts (kinds structure, interface, dependency, flow, test, operation),
    unknowns and contradictions, and every contract rejects an unknown field, so it has no field for inferences.
    as-is-format.md has no section on the fragment format.
  evidence:
  - path: src/orqlet/application/contracts/as_is.py
    lines: 27-80
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: fb9f9377c8e4cfffbdd46207dfbafbc6ed74a566b2e640a8025a4fac4a5315cf
  - path: src/orqlet/application/contracts/common.py
    lines: 50-53
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 19836bc1ef2cc800af51b07c2c333dd7d70066500abb4d0e4157ae35a38737e6
  - path: src/orqlet/workflow/skills/orqlet-research/references/as-is-format.md
    lines: 1-68
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a5cbf02ce4ad7efc3249b2eaa3ddb06f9850e317e14ac84d46b19dd3a0517d68
- id: A-15
  kind: interface
  statement: A plan phase holds file operations, acceptance criteria (text, source, check_ref), checks,
    review evidence, a knowledge step, completion and expected outputs; the plan contract has no separate
    test-plan section. check_ref is commented as 'a profile command id or a review item'.
  evidence:
  - path: src/orqlet/application/contracts/plan.py
    lines: 21-47
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: f455fc6035f119ffdf5a0ada0de1c60ed9fe3e6d73e0c4714e9aeffb5c86c61d
- id: A-16
  kind: interface
  statement: design-format.md defines the D1, D2 and D3 triggers, the artifacts each class requires and
    a sample design-set manifest. plan-format.md lists the plan rules, among them acceptance criteria
    with `check_ref`, review evidence from three roles and a knowledge step that is always required.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-design/references/design-format.md
    lines: 5-19
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ad7c02fa9a3098080bee79eb5c3bb4537861eb6a81cd94d5e3084f44d710780b
  - path: src/orqlet/workflow/skills/orqlet-plan/references/plan-format.md
    lines: 3-56
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 540b855ca9089d89455df0328c02d231d5872b50764d6ecb4d21870a89ee419b
- id: A-17
  kind: interface
  statement: orqlet-inventory and orqlet-tracer are read-only and return fragment YAML without revision
    and sha256. orqlet-tester writes isolated unit tests from one phase's acceptance criteria and names
    no project test command. Both reviewers are read-only and receive only the path of a read-only packet.
  evidence:
  - path: src/orqlet/workflow/roles/orqlet-inventory.md
    lines: 1-12
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b1135c03ee3cdfa83f0ba62344745396e8f58335571ab6223e108e4f2ab51790
  - path: src/orqlet/workflow/roles/orqlet-tracer.md
    lines: 1-12
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3ef6d0cf65501706dc73e650a52e4f90b3f94e5015db6078887a9ddd1e81e97d
  - path: src/orqlet/workflow/roles/orqlet-tester.md
    lines: 1-16
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 1d91a86e47ddf1afcfe7a5dcc3a17a40c00c2d2f80d61de88ecd5128975fc59f
  - path: src/orqlet/workflow/roles/orqlet-arch-reviewer.md
    lines: 1-18
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 4719caf49f24bcf762799109a633be35c98403da1052d4c96e058321aea1f17a
  - path: src/orqlet/workflow/roles/orqlet-security-reviewer.md
    lines: 1-12
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 789159c52961e2e35c5baddb10757cc1f028064cc61b9e7baa1c9a2c7499adf7
- id: A-18
  kind: operation
  statement: tools/build_manifest.py records the hash of every workflow file and the `workflow_version`
    and `controls_level` of identity.json in MANIFEST.json, and `--check` fails when it is stale. identity.json
    holds 0.3.3 and level 3, releases.json lists only 0.1.0, and rule ORQLET-DET-002 requires a manifest
    rebuild and version bump on any change.
  evidence:
  - path: tools/build_manifest.py
    lines: 1-53
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 239ba0f156be8c2db22170abbfe3407f446bca6f9d9ee2f6605772ab63963c2c
  - path: src/orqlet/workflow/identity.json
    lines: 1-5
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b0afc23679bcb9a4e148f670adf6889e76eb405215b5e84c1eb90cd594e88a4e
  - path: src/orqlet/workflow/releases.json
    lines: 1-10
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 63ad2128350fd7052aacf1ad780bb18d14ddcfc73689a39dbafedeb85424bf62
  - path: .prompts/rules.yaml
    lines: 92-99
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a243ba4d59b9f4ae9f9be8bc343dc56248ecd6d99f99368ef7b1cdb59512a631
- id: A-19
  kind: test
  statement: Workflow package files are tested for LF endings, one final newline and no tabs, and the
    committed manifest is tested against the files on disk.
  evidence:
  - path: tests/unit/test_manifest.py
    lines: 157-164
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 690a57a029f601d6fa5e62aa0817246de79c93f96d7a8012f3ae629f05e8d4ee
  - path: tests/unit/test_manifest.py
    lines: 36-43
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 2e7f41f547fd5de4de16bf38d029622c167bd3eb31c5a153334e4776bb364b29
- id: A-20
  kind: structure
  statement: Claude Code renders the AGENTS.md blocks, `.claude/CLAUDE.md`, rules, commands, skills under
    `.claude/skills/`, roles under `.claude/agents/` and an optional `.mcp.json`. Cursor renders the AGENTS.md
    blocks, rules, commands, skills under `.agents/skills/` and roles under `.cursor/agents/`. Codex renders
    the AGENTS.md blocks, skills under `.agents/skills/` with `agents/openai.yaml` sidecars, and roles
    under `.codex/agents/`.
  evidence:
  - path: src/orqlet/adapters/clients/claude_code.py
    lines: 58-72
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 300b636dbbaf6fa564b68eb415265c2de7c9c5af00cade8042aeadd960544ad0
  - path: src/orqlet/adapters/clients/cursor.py
    lines: 42-57
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 65ad1e75319b5e53ebf6080af3c8c1e9025e4ef1023831ae161183572d4fa30d
  - path: src/orqlet/adapters/clients/codex.py
    lines: 48-67
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 949e6a9174b72d81a654d0ef62a15f2cbd778c7dfd622dd0b7a93e373e1c4430
- id: A-21
  kind: interface
  statement: 'A rendered SKILL.md is front matter (`name`, `description`, and `disable-model-invocation:
    true` unless the agent may start the skill), the generated notice and the normalised body. A reference
    is written to `references/<file>` with the notice and no front matter. The Codex sidecar sets `allow_implicit_invocation:
    false`.'
  evidence:
  - path: src/orqlet/adapters/render/skills.py
    lines: 1-8
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 8b2624c714cd0fa1dfde920225a752d390b185132f241dabff9d5d24618edf02
  - path: src/orqlet/adapters/render/skills.py
    lines: 22-76
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a4a54c9b665cfb424f645f36faceeb1bbef20f1ad107bbc9f7f6af7adb9d8754
- id: A-22
  kind: interface
  statement: Every skill, reference and role file is owner orqlet and class protected. A skill's lock
    inputs are (`skills/<name>`, workflow version, sha256 of the body after render_steps).
  evidence:
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 122-135
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e68637f03d7f00b73b0b675a207ac3740339fa086e51d8658b1fff89a9375f0e
  - path: src/orqlet/adapters/render/roles.py
    lines: 49-61
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: f11a08b666120e6247f73ac9bf8e2a5ed1098f3ed653b5c11424383f2bb2cebe
  - path: tests/unit/render/test_skills.py
    lines: 331-344
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3f54f80733ad9db57ecc3973d13bbe07890a1ab9e96ec0606fa8069827989cf9
- id: A-23
  kind: flow
  statement: build_render_request takes no profile parameter and skill bodies are the package texts after
    render_steps. The profile reaches rendered files only through the AGENTS.md conventions block, so
    no receiving-project value appears in a SKILL.md.
  evidence:
  - path: src/orqlet/application/usecases/render_request.py
    lines: 55-119
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: afb853f6337ff7508d20407f51f906e6702831bd906f4f6875a437b3d707ff52
  - path: src/orqlet/application/usecases/render_all.py
    lines: 117-134
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: da66d5e998dd1e4009331c0fcfbd7510fe5b43439f1a30673818c4a66a692c62
- id: A-24
  kind: interface
  statement: The conventions block is built from nine repository convention keys of the profile, puts
    unanswered keys on a 'Not decided' line, adds a line when resources are registered, and is capped
    at 11 lines and 2800 bytes. No technology, structure, command or facts value becomes a line.
  evidence:
  - path: src/orqlet/application/usecases/resources_view.py
    lines: 44-54
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 5352a1561383f50e592f3315accd861d12ca0167aafb848be66c84533f719565
  - path: src/orqlet/application/usecases/resources_view.py
    lines: 172-208
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: d239c01efa7a009fd94c48845690914f1db70bdf1f51e48ba5029e8aab74579b
  - path: src/orqlet/application/usecases/resources_view.py
    lines: 264-298
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3ed5fb5a5792cd0eb37f083436caa0bc22d67a1f827aa4a35d1d43f93c52b2d5
  - path: src/orqlet/workflow/templates/conventions-block.md
    lines: 1-2
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 5b9e7c2a807bdc10498953619ccab0ec10c8fe5d84e8386cfd2642234193d84d
- id: A-25
  kind: flow
  statement: A non-empty resource registry adds scoped rules `resource-<id>`, skills `orqlet-tool-<id>`
    and a catalogue skill `orqlet-resources`; the two skill kinds may be started by the agent and are
    filled from templates holding exactly one `{{lines}}` slot.
  evidence:
  - path: src/orqlet/application/usecases/resources_view.py
    lines: 125-169
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a67a8e2b43d7cea5d46130df90a729c3f436000a6f3756ec53b8a5be5f563412
  - path: src/orqlet/application/usecases/render_request.py
    lines: 122-153
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 688d400652ee9021fc71f7b237411f291b0fbda2562358eca46e3cfb1c93b351
- id: A-26
  kind: flow
  statement: compose renders every enabled client from one request and merges identical files at one path
    into one; different bytes for one path or block raise MergeError. Claude Code and the `.agents` folder
    receive byte-identical skill files.
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: 117-144
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ba88a596748126145a44486433512b30cb7fb9632f7c96ca5e6329697da5ab66
  - path: src/orqlet/application/usecases/init_files.py
    lines: 48-74
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 496afb75efec27c39fa95ee871179f8b1fb4dfbe57558c6ffc993dc339409bcd
  - path: tests/unit/render/test_skills.py
    lines: 269-281
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 8f61d93792e93b7f58577aced0ac248fbc3e68c4ef4b1763978c828f6dede9ec
  - path: tests/unit/render/test_skills.py
    lines: 346-353
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: c6ac4e60d6133f65d45c0cf4ff584dc8a05bc05b3c0fed05ec5113ecca77509c
- id: A-27
  kind: interface
  statement: 'Stored documentation pages say: Claude Code loads project skills from `.claude/skills/<name>/SKILL.md`
    and supports `paths`; Codex scans `.agents/skills` from the working directory up to the repository
    root and requires `name` and `description`; Cursor loads `.agents/skills/` and `.cursor/skills/`,
    also `.claude/skills/` and `.codex/skills/`, honours `disable-model-invocation` and loads `references/`
    on demand.'
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-skills.md
    lines: 11-34
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 80ecb8e32fca8789af61cdf8e6fd67f9fa97c15069b85fc13bb77945cc0b2b87
  - path: docs/design/team-conventions-resources/evidence/web/codex-skills.md
    lines: 8-12
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 4ee5a6d27d38701d86df836fcde1ae85d97ba0c12deef24ce90948ccb8c2c13c
  - path: docs/design/phase-skill-contracts/evidence/web/cursor-skills.md
    lines: 1-20
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e40cd24d9a216c4d9acfe9305135674e2dd2b317eab9faca05bbc4c0cb69a10f
- id: A-28
  kind: operation
  statement: Each adapter reports ORQ-L001, saying its behaviour follows published documentation of 2026-10
    and was not observed with a real client; Cursor adds ORQ-L004 about a skill listed twice and Codex
    ORQ-L005 about its invocation policy.
  evidence:
  - path: src/orqlet/adapters/clients/claude_code.py
    lines: 31-43
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 8aa980389f6ba916ee6b57f37cabfb9e368954a28eea92e307eaba3d171a6f62
  - path: src/orqlet/adapters/clients/cursor.py
    lines: 16-25
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e75c0516a112986e260d0d46a49eaf46abb0cac53387c4695b23ac3b745ded94
  - path: src/orqlet/adapters/clients/codex.py
    lines: 14-35
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 054adb37c6793f13c5307f8cf9666fb9b3808138dc28e105f96eac2e8b3a9cfd
- id: A-29
  kind: structure
  statement: The project profile has the fields project, stack, profile, facts, repository, structure,
    dependencies, auth_procedures, standards_sources, clients, orqlet, optional_components, data_class,
    commands, technologies and capabilities; none names a location for task documents. `commands` maps
    an id to argv, cwd and source.
  evidence:
  - path: src/orqlet/application/contracts/profile.py
    lines: 149-172
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 090c0b5d9c73056834cb778aabae68e48232efc770f1d0089b91da5d20a8ef37
- id: A-30
  kind: flow
  statement: draft_profile leaves structure, commands and capabilities empty, no use case constructs a
    CommandSpec, and the only writer of `structure` is the answer key structure.test_runner. `orqlet profile
    answer` accepts 16 fixed keys and refuses others with ORQ-E160.
  evidence:
  - path: src/orqlet/application/usecases/draft_profile.py
    lines: 70-91
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: f3063042caccfcef11ec8e8ac3ef7741c6e00b7ea77cac0635ba59f05fae6f78
  - path: src/orqlet/application/usecases/init_questions.py
    lines: 29-48
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 288cc0748a8afcdc9575c07e4237c85106697b71e7585e0c9118839dd8fc5336
  - path: src/orqlet/application/usecases/init_questions.py
    lines: 87-112
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 5253a50e82079e108b16e43e2cc3529b47496a546b224a1757f07e7321045991
  - path: src/orqlet/application/usecases/profile_edit.py
    lines: 48-54
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 04d0df394fb520ae0cf4e0f1ebbc619f09244617bfb94baa35f5bbdc91dcffde
- id: A-31
  kind: flow
  statement: Init records discovered technologies with a scope of '.' or a sub-directory up to two levels
    deep, and a test asserts that monorepo service scopes are written. profile.version is set to 1 and
    no code increments it.
  evidence:
  - path: src/orqlet/application/usecases/discover.py
    lines: 19-59
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 85017f4c75c6a1a45cecf783b54ecac329be84dd84e871a760b3e9d8abf057b0
  - path: src/orqlet/application/usecases/init_project.py
    lines: 115-129
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ae5160048db83cf89c6a51ac6aa396ac2abbe21fdf97f958502f3f34f4ca1f3d
  - path: tests/unit/application/test_init_project.py
    lines: 269-283
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: f6a3773f28ad80961ddd2e88d239e20bb96b7b9ebd65e3b488473a89c32116df
  - path: src/orqlet/application/usecases/draft_profile.py
    lines: '79'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 852f0125d7d129b6dcc3cbcdedcb966ed5474df6490834599657e8f6a245fe05
  - path: src/orqlet/application/usecases/profile_edit.py
    lines: 103-124
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 236b52d1c644db3c98f078e4453e447c8cd64462a13a60ce5132dfee9649cc1b
- id: A-32
  kind: flow
  statement: '`orqlet standards for` scans the project again at execution time, hashes only the rules
    its query selects and does not filter a dimension the query omits; the phase filter compares the phase
    string literally.'
  evidence:
  - path: src/orqlet/application/usecases/standards_for.py
    lines: 134-155
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 6d036b7cf61c3f0aa8c434cb2421c15bf51e1c21261e9db1d2e69f460354e4ca
  - path: src/orqlet/application/usecases/standards_for.py
    lines: 200-215
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: f9d2ab51679466fd479d09e5c38f451cda9885937a60ef1d7b8e83fbe16d8fb2
  - path: src/orqlet/domain/resolver.py
    lines: 60-66
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 9d466cb513aa411ee1a7db9ff45c95034e9ae9965d3abff5a41d62afc24ee413
- id: A-33
  kind: flow
  statement: The standards lock's applicable_rules_hash, which gate status binds, is computed at render
    time over every rule resolved for the stack stored in the profile.
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: 81-98
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e9c58681ad375d961e8b9533e236239ad7d2c7804986118703755267272e2748
  - path: src/orqlet/application/usecases/render_all.py
    lines: 247-260
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 7ff5f9ca1dea472d71f331174d01bc781cda374cb0c9bb6f36f1e4d25c6601ff
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 70-93
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 33755d0d66dcfd7085f72752da09cf6eb61899519f8d616dd6ae9818a95a5d25
- id: A-34
  kind: interface
  statement: '`orqlet explain` declares the profile''s technologies with their scope, standards sources
    and clients, and `orqlet resources list --uncovered` compares profile technology names with registered
    resources.'
  evidence:
  - path: src/orqlet/application/usecases/explain.py
    lines: 45-75
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 4bcee068562ab166cdca4b3bd1d1a92289cdaac2b2d941e6eb953f8f61ec4fcc
  - path: src/orqlet/application/usecases/resources_view.py
    lines: 64-121
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 4bb7e0e82145c4ba164338df808ec5aaa3b8df5dd768a3d8a938ca524360a3ac
- id: A-35
  kind: structure
  statement: This repository's profile has empty commands, structure and capabilities, four scanner technologies
    with scope '.', and is draft version 1. Its checks are declared in ci.yml (ruff check, ruff format
    --check, mypy, lint-imports, export_schemas --check, build_manifest --check, and pytest on three systems
    with Python 3.12 to 3.15) and pyproject.toml.
  evidence:
  - path: .orqlet/project-profile.yaml
    lines: 10-12
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3957f1323fdda7d7403b8dbf3c565102602ad123c71bdfb1f15bcdade93329aa
  - path: .orqlet/project-profile.yaml
    lines: 151-188
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 68428ccdbeeae9326a1c768da4f1000c476fca61c2408757bb1deaa42634bff4
  - path: .github/workflows/ci.yml
    lines: 18-107
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 7a37d7d89da4dd970d632a1eba57ed099c515cb3c080904ee47bbfa89ac63d00
  - path: pyproject.toml
    lines: 38-127
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 25c4aa4f065c4f53bcbaf40bed28eaf17d7776acf754e4eef8811f6d2d4a686f
- id: A-36
  kind: structure
  statement: The validators fix TASK_ROOT = 'docs/design' and read a task only from paths matching ^docs/design/<slug>/;
    the as-is, design, plan and ledger task-folder checks are skipped for other paths.
  evidence:
  - path: src/orqlet/application/usecases/validation.py
    lines: 25-26
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 8de4a43d6cd1170a4f25ac3aa6528e20239d1c43d906c381ecbc80036b156ed7
  - path: src/orqlet/application/usecases/validation.py
    lines: 88-91
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: dbd3d4988cd21a3308a162be0599e85964aa704c18f6b5f182d6e14a8868a8ed
  - path: src/orqlet/application/usecases/validate_as_is.py
    lines: 81-94
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ae731418d6a8a8df072dbff5c71675bfeaabd625a7e2476c8ac6f2d3226875bb
  - path: src/orqlet/application/usecases/validate_design.py
    lines: 88-94
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: cc1804df06bd8e057c3338eb7b43b9987e4754dfd4df9e3296b0e95578ea104c
  - path: src/orqlet/application/usecases/validate_plan.py
    lines: 66-72
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 176a39addb3d30524826ebf334ab7063708f52fefbbaef42e374e15f7ff11fe9
  - path: src/orqlet/application/usecases/validate_ledger.py
    lines: 36-42
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: d2d84c8b3b027f99a111494b3810eeb5b47f2966839d50bc5e85db7aa5a70c8a
- id: A-37
  kind: structure
  statement: gate status, review prepare, knowledge impact, binding inputs and record validation build
    the folder as docs/design/<task>; records outside its reviews/, tests/ and knowledge/ folders fail
    with ORQ-E400, and the web-evidence scan of `evidence cite` applies only under docs/design/<task>/evidence/web/.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 148-152
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b279bc91d9642540d8edfc7bafee2b1dbeb14597a699818bc79a70a59ea12eae
  - path: src/orqlet/application/usecases/review_prepare.py
    lines: '73'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 317f7ce7dd76e8bb527b9edf60e8982e2e0a69139080355e61215d09cbdb968e
  - path: src/orqlet/application/usecases/knowledge_impact.py
    lines: '91'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 317f7ce7dd76e8bb527b9edf60e8982e2e0a69139080355e61215d09cbdb968e
  - path: src/orqlet/application/usecases/binding_inputs.py
    lines: '295'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: f9108d80b9eb3bfb42be9be32f254b33aa43a08eedfb0b3a0f3ab3c8dfdb245e
  - path: src/orqlet/domain/evidence_artifacts.py
    lines: 21-35
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3ddf99b9c1ec9d3f04ac72b238713ab1444c15951973f513b017eee4758b4e82
  - path: src/orqlet/application/usecases/validate_records.py
    lines: 84-98
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 5a6bc5b9b0edbcfd68393bf529602b37b9c5243122ae9168550f677e1f949d83
  - path: src/orqlet/application/usecases/evidence_cite.py
    lines: 52-56
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 538ce038bc3559b89d843cfb7dedf60f823ba770e01a8d7a1b9c29efcce05480
- id: A-38
  kind: structure
  statement: exempt.yaml classes docs/design/ as workflow-artifact and states that its list is fixed by
    the Orqlet release and cannot be changed by a project.
  evidence:
  - path: src/orqlet/workflow/exempt.yaml
    lines: 1-14
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e8e75463b2b031f4321c53f43b9efa1a984715bc1e9f509ed4e10474708b631d
- id: A-39
  kind: flow
  statement: 'classify compares the SHA-256 of the file on disk, in the lock and in the new render, reading
    CRLF as LF: equal to the render is up-to-date, equal to the record is a safe update, otherwise a protected
    file is tampered and a generated one is user-edit-only or, when the render changed, a conflict. A
    user-owned entry is always kept.'
  evidence:
  - path: src/orqlet/domain/classify.py
    lines: 14-50
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 796f2e1848c6cce18eeae845f2afd457e56716dcb5cca1d1e9c2509143ea15db
  - path: src/orqlet/domain/changeplan.py
    lines: 150-152
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: fd003c40004c7fb53f0c8421740f82316fd0a5b6110cfa707833ba2abc01d6bf
- id: A-40
  kind: flow
  statement: The change plan creates new files, updates safe updates, restores tampered files, deletes
    untouched orphans, and stops on conflicts and name collisions; a stop or seeded change writes only
    a unified diff under `.orqlet/proposals/` and leaves the live file. Recorded inputs play no part in
    the decision.
  evidence:
  - path: src/orqlet/domain/changeplan.py
    lines: 45-52
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: f64e606a3aa0e15d431ea9391a8252811a7c6f23cff49199167bc9965bff81dc
  - path: src/orqlet/domain/changeplan.py
    lines: 204-223
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3d5be8e6f15dd82cc199827bb2c8d8199a4f9b8490b03eaa0f56da9c0a99dccf
  - path: src/orqlet/domain/changeplan.py
    lines: 378-391
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: afff31f07d120614cf30fce59fadefe5a9e7d329e03d66d157fa60ca95b07765
  - path: src/orqlet/domain/changeplan.py
    lines: 420-432
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 873ac016c122c22a28ac8ca6f0028a13eca849933e8deb1e6d98508e76812468
- id: A-41
  kind: flow
  statement: Shared files are parsed for `<!-- orqlet:begin <name> <info> -->` blocks, each classified
    on the hash of its own span; text outside the blocks is kept byte for byte, new blocks are appended
    at the end, and a file with broken markers, conflict markers or non-UTF-8 text stops with no write.
  evidence:
  - path: src/orqlet/domain/blocks.py
    lines: 9-14
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b09fd8f485e67b8257da9e58db7804fa7084390b05f56a42cf5503a71b39b63d
  - path: src/orqlet/domain/blocks.py
    lines: 46-97
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 242a2b7815f569935873992a5676bfe83831e5a83e323cf19a03319159456a79
  - path: src/orqlet/domain/blocks.py
    lines: 118-160
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: f58d39bd499727a98907c7f588adea65399bd83095fb323b6dd711ed50d1fa06
  - path: src/orqlet/domain/changeplan.py
    lines: 226-282
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 993acea2538ed257b74a01b9284c0afe41aaf0613b9d5a95b7da3a617774e808
  - path: src/orqlet/application/usecases/init_files.py
    lines: 48-58
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 31614a377281a0e7df41411f81db443c67296ae6bdf67f8748bc60173443abe9
- id: A-42
  kind: interface
  statement: The lock records per file the path, owner, class, inputs (id, version, sha256), the rendered
    or seeded hash and block markers. In this repository skills are orqlet and protected with input version
    0.3.3, and the AGENTS.md baseline marker carries `workflow@0.3.3#<sha256>`.
  evidence:
  - path: src/orqlet/application/contracts/generated_lock.py
    lines: 13-58
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 1b8cacd4603c777512252066b541dbbb450c51962439692cd6ed63e4b0928dba
  - path: .orqlet/generated.lock.yaml
    lines: 1-13
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b74be60dd0b8b762fd8941466fd9235ee57a59f9e90fd81b6d33ca2606c9ecbe
  - path: .orqlet/generated.lock.yaml
    lines: 660-670
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 7c8e48473fb84f7dd8ff03ece96ea035ce2cad3ca10ff49acc180ade86c85231
- id: A-43
  kind: flow
  statement: A second `orqlet init` returns already-initialised (ORQ-I010) and writes nothing. `orqlet
    upgrade` plans against the lock's records; with unchanged inputs the plan is empty and it returns
    up-to-date with exit 0.
  evidence:
  - path: src/orqlet/application/usecases/init_project.py
    lines: 101-112
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 7cf877b13516bd8523dab779b409f899e723aa01f35f4b6aeabe73d7847e350e
  - path: src/orqlet/application/usecases/upgrade.py
    lines: 119-138
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 81d1bd3a33dbcc82a9d9f772910710757ec19a40b42995b3349c261c5c69f0bb
  - path: src/orqlet/application/usecases/upgrade.py
    lines: 162-165
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 9274d9ebd1a0014624557850ee69d7f64e3cc48e2410fb4fc0b58855315e7af0
  - path: src/orqlet/domain/changeplan.py
    lines: 115-147
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 56a8799593577d9e514bc421605d779a708bd66dda3f1afb446eab8423c09bbc
- id: A-44
  kind: flow
  statement: '`orqlet upgrade` warns ORQ-W080 for each stopped item and then exits 1, warns ORQ-W096 for
    each restored protected file, and refuses on an open journal (ORQ-E131), a downgrade (ORQ-E120) or
    missing packs (ORQ-E121).'
  evidence:
  - path: src/orqlet/application/usecases/upgrade.py
    lines: 70-104
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 6fddaa57376758f0e343d9e69f3a16e7c4c5da8822be78e4f7572f5414be7206
  - path: src/orqlet/application/usecases/upgrade.py
    lines: 138-152
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 54d62b9ee5bc0b1c5cec0f52df314bba8713c84897b5e05bdf0550f2bcfbbbe2
  - path: src/orqlet/application/usecases/upgrade.py
    lines: 322-332
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ea3da8fc637fa7553f8348a3d27c3db65729321250ba8ce4216065b8c84548e7
  - path: src/orqlet/interface/cli/commands/lifecycle.py
    lines: 113-120
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: aee21ff53e0eddf43c2e08db7f971efcc9fe6c213157fa86ef022bcb0271152e
- id: A-45
  kind: operation
  statement: apply_plan holds an apply lock, checks every preview hash, backs up existing files, journals
    the change, writes atomically with the lock file last and removes folders a deletion emptied; rollback
    reverses a journal only while the files still match it.
  evidence:
  - path: src/orqlet/application/usecases/apply_plan.py
    lines: 38-108
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: cd3540df09c8001a73e20fdb23a6efd840d7e0ccae1dd6e516f6d15d03fdd140
  - path: src/orqlet/application/usecases/rollback.py
    lines: 48-104
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 7bbc6c040956111823ed02b801756ac985cfd819e5b8e605f54e8d7c2c35c5a1
- id: A-46
  kind: operation
  statement: Journals, backups and the apply lock live in the user data directory under projects/<project
    uuid>/, the uuid being generated at init and stored in the profile; review packets go to <data dir>/packets/<task>-<phase>-<8
    chars>, not keyed by project.
  evidence:
  - path: src/orqlet/interface/cli/wiring.py
    lines: 74-86
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 0838696b234cdf2834d464aa87fb2c32315365261ed17dcc79bf9f6ec1135f02
  - path: src/orqlet/interface/cli/wiring.py
    lines: 119-123
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ed8dd2582494e99911a648b07cb4af2381472ed49c7afc3d200a58eece25396f
  - path: src/orqlet/application/usecases/init_project.py
    lines: '372'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 318765537430e430c485390cce4425ddfcc647fa00232d17efae2d1a7fcc9e51
  - path: src/orqlet/application/usecases/review_prepare.py
    lines: '85'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a3b9e46f5743f0b39c9497b11f43ec92d2bdcea672eb15274c6f53230a483ce8
- id: A-47
  kind: flow
  statement: '`orqlet doctor` and `orqlet sync` skip seeded entries and report a protected file that is
    edited, missing or unreadable as ORQ-E150 and an edited generated file as ORQ-W152; `orqlet release`
    refuses protected files with ORQ-E141.'
  evidence:
  - path: src/orqlet/application/usecases/diagnose.py
    lines: '37'
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 4991597cd0c97a5796146f154c9dab5d1495a9e7aa3676ed2631d4f9fdc4a0f4
  - path: src/orqlet/application/usecases/diagnose.py
    lines: 78-114
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ab41ce823ab6535da4898d27c708c4ffced0f3ba6b23fa9d292217dba9eb4880
  - path: src/orqlet/application/usecases/diagnose.py
    lines: 165-197
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: fa2fa2add79272c5f93c3b03551c3a7adf8bea59aab2b5bd68aeca6ee4e09531
  - path: src/orqlet/application/usecases/release.py
    lines: 46-100
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 5645badb736fe7adcb6caa734554bfc73fd87c86a0459fda07b0918d49494bdd
- id: A-48
  kind: interface
  statement: The artifact header holds task, status, workflow_version, protected_set_digest, bound (base_revision,
    standards_lock_hash, applicable_rules_hash, profile_version, upstream) and specialists, and no project
    identifier. The design records `as_is_ref` and the plan `design_ref` as `path#sha256`.
  evidence:
  - path: src/orqlet/application/contracts/artifact_header.py
    lines: 23-52
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 4c49fb081588172743571a746d795885bfd18a744acccaffb46c8069052e67e3
  - path: src/orqlet/application/contracts/design_set.py
    lines: 131-134
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 0df355d1e39f149ed58c19bf4fd970107cbbfe52e7d102363f4740168b2c1add
  - path: src/orqlet/application/contracts/plan.py
    lines: 67-71
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 88cb0b99f37632bef2112c442f92b072b4792427128e456b589f3a196b74c8ea
- id: A-49
  kind: dependency
  statement: gate status computes protected_set_digest over every protected lock entry, and skill files
    are protected entries, so any change to a rendered skill changes the protected_set_digest that existing
    headers recorded.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 70-93
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 33755d0d66dcfd7085f72752da09cf6eb61899519f8d616dd6ae9818a95a5d25
  - path: src/orqlet/adapters/render/skills.py
    lines: 69-76
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 30f797ae42d9063f04b00d9af76cb4e7a4f2c62c65ce71e8e00b129dea8c495b
- id: A-50
  kind: flow
  statement: For a task, gate status reads only as-is.md, design/manifest.yaml and plan.yaml under docs/design/<task>/,
    reports a missing one as ORQ-I394, a header differing in any of five bound components as stale (ORQ-W390),
    checks a base move against files in scope, and always ends NOT_RUN with ORQ-I393. It does not compare
    a header's task or the as_is_ref and design_ref hashes.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 110-123
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 45cce1f3332d7bec1eb2d88076d2090c1a5369aee22609548b5854cf4f4ffd48
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 145-229
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 733c01ab9188a9032e894657e1a4ad0c37695efa63b6b364f4926b34b72ae499
  - path: src/orqlet/application/usecases/staleness.py
    lines: 11-30
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: ad1981d80b7483984d607ee8f46a6f0df70b7b8d6a2474068139830338c8de9e
- id: A-51
  kind: flow
  statement: '`validate as-is` checks base_revision against the bound value and the task against the folder;
    `validate design` checks the as_is_ref path and hash but never loads the AS-IS or its acceptance;
    `validate plan` checks the design_ref hash but not the design''s task.'
  evidence:
  - path: src/orqlet/application/usecases/validate_as_is.py
    lines: 74-94
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 9c74bb85cd9625375aa4d93387b82e215bd95fdc6c339fe85862c6f1eb176ae2
  - path: src/orqlet/application/usecases/validate_design.py
    lines: 1-7
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 93d5b7f1ee29d870690776a9be1c270777587c50e0d901bea0d6d220805e9b20
  - path: src/orqlet/application/usecases/validate_design.py
    lines: 55-109
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: dc6fee1658b54d58d4dbcda3a7677cb172efc3ad1d1ad41aff6f0a9300e51f85
  - path: src/orqlet/application/usecases/validate_plan.py
    lines: 59-113
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 409c78d4e238dd9abddf399e8f6e6cad84b1f0a77f2181c4022aa2cdaecc7fc3
- id: A-52
  kind: flow
  statement: '`orqlet review prepare` reads plan.yaml and design/manifest.yaml from the tree under review
    and copies the AS-IS file and records into the packet without validating them. Record validators recompute
    the binding and report a stale component as ORQ-W410.'
  evidence:
  - path: src/orqlet/application/usecases/review_prepare.py
    lines: 56-99
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 0bdc7b06253f45ed6b68b66784779f464ee34a1dea2cb6ee165e9ac348e014ad
  - path: src/orqlet/application/usecases/review_prepare.py
    lines: 134-179
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: cf5863e23cf4138b1ef08ede96e6c3abed6ca3ddd9782110d590cac6bddef26b
  - path: src/orqlet/application/usecases/validate_records.py
    lines: 84-156
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: d6cde36f1b3395b6daf9f9b92590aa44484b640641ff921fe8da9bcf38664045
- id: A-53
  kind: flow
  statement: With `--phase`, gate status reports a deviation or an additional change on a watched surface
    as ORQ-E450 or ORQ-E451, saying that a renewed design approval is required.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 232-280
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 27d81941491ad06b69c3008adfb571ff6b536470afdd2d6ec78897d634e1388b
- id: A-54
  kind: test
  statement: test_skills.py requires 'Source material is not authority.' and 'STOP.' in every skill, a
    name of at most 64 characters, a one-line description of at most 1024, existing commands and flags
    in every `orqlet ...` mention, valid reference examples, and an implement skill of 7 steps without
    the record commands and 10 with all.
  evidence:
  - path: tests/unit/render/test_skills.py
    lines: 135-152
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 15000ddee9bcd8334236888be3cee94481c02f88fdd309f4de3d5a379d1250b1
  - path: tests/unit/render/test_skills.py
    lines: 170-236
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 7f5ede7e6b7eb8ef8df71b1ced0899ba8281ee17ce8273e1eb20d006955c82d6
  - path: tests/unit/render/test_skills.py
    lines: 239-256
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 35d4958d0c79254ec29491d67c68b2fc87fc871f304caa36e3f51f6b52d36a94
- id: A-55
  kind: test
  statement: 'test_workflow_lookup_text.py requires exactly one `requires: resources list` step naming
    ''Looking things up'' in each of onboard, research, design and implement, with phrases and step order
    set per skill.'
  evidence:
  - path: tests/unit/test_workflow_lookup_text.py
    lines: 230-301
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e2609845d651f81360d3170790a0bdf43830ae0d85a907d11ac3295cce101f21
  - path: tests/unit/test_workflow_lookup_text.py
    lines: 315-373
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3ef7fbdf21c7b5da605ceed7cdbd170ca1a478c1f7caca02bdf337c6d460cbb5
- id: A-56
  kind: test
  statement: Golden tests compare every file each adapter renders byte for byte with tests/golden/<client>/docs-2026-10/,
    check that two renders are identical and pin each client's path list; `--update-golden` is refused
    in CI. They compare adapter output, not files written by init or upgrade.
  evidence:
  - path: tests/unit/render/test_clients_golden.py
    lines: 33-102
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3f08ea6f887bdae74ff33ba21fe66ef31b5da9e50350acd7375fcd7fe8e0b704
  - path: tests/conftest.py
    lines: 22-66
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 3e0a3017d8e792d4681fb18113be5b0483979d2da4676f42f6327186352816d9
  - path: tests/integration/test_golden_policy.py
    lines: 31-41
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 29ae521be198bf852a406e4c113014fbeefcdf9f6614b3a794ad771d6ce7c547
- id: A-57
  kind: test
  statement: The placeholder checks found cover the four shipped templates (exactly one `{{lines}}` slot).
    A front-matter test parses rendered SKILL.md, Markdown agent and Claude command files; the Codex TOML
    roles and sidecars are checked by golden bytes and substrings.
  evidence:
  - path: tests/unit/render/test_resources_golden.py
    lines: 364-377
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 550c5c4f18aa93980a435c31d70713f66428646240ad78effcccf8c18753e58a
  - path: src/orqlet/application/usecases/render_request.py
    lines: 122-129
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: adbe6009262186201a48d273b9ce377361070af413f6c60a713bd855aa83c3f0
  - path: tests/unit/render/test_front_matter_views.py
    lines: 45-61
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 2b06db0358a5af1bc967c19de43c4ecfcf95382ef9cf891ad1ec45b0cb29897d
  - path: tests/unit/render/test_front_matter_views.py
    lines: 104-114
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 678b6ea59ba2792398cdcd029c1d7467b356f8096728f26fd1ec0c01ac0ace49
  - path: tests/unit/render/test_skills.py
    lines: 356-362
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e5f03c1809bca5e42df4b331d385921f14fb19ce635d717a55e84560e1e5d8e5
- id: A-58
  kind: test
  statement: Lifecycle tests cover an idempotent second plan, a kept team edit, conflicts and name collisions
    written as diffs, restored tampered files, CRLF, orphans, an AGENTS.md that keeps its text and gains
    one block at init, an upgrade with an edited PR-template block, crash recovery with --resume, stale
    previews and a busy lock.
  evidence:
  - path: tests/unit/domain/test_changeplan.py
    lines: 71-176
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: a5c859d23d44e7190f7b9bf576ca16ba965088b4a815e493ec3aa53414741732
  - path: tests/unit/application/test_init_project.py
    lines: 461-469
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 6abfeb9f1cac91710663cab44b9fb5ffaed2a4c9f8dd59262ed9eb18054d9eb3
  - path: tests/unit/application/test_lifecycle.py
    lines: 281-356
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 394516ed6501c704388e23bd505a8d5c63c0eed617a921d4cd29197ab5df01f5
  - path: tests/unit/application/test_lifecycle.py
    lines: 391-435
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 120df096da8db9514069a4fd900a20a628d5123a30be12d6a96f00b84929c86e
  - path: tests/e2e/test_m1_acceptance.py
    lines: 50-137
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 9235c768370542d9256d6eec1a90195bf11145e24e63bce9d5c7cc49cfda657d
  - path: tests/integration/test_apply_lock.py
    lines: 23-89
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: e3e7312c9139395b834d21bfc246f6bc07ca106acf643441b7c649d820f90b45
- id: A-59
  kind: test
  statement: Test support wires one in-memory project and a separate data store per Env, gives predictable
    ids from SequentialIds, and its ChangedWorkflow changes only the baseline and PR-template sources.
  evidence:
  - path: tests/support/init_env.py
    lines: 40-88
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 743baedcad0dc934cf6d71df1d33060fceec33cc1f607e4df3fee37a58444e7c
  - path: tests/fakes/ids.py
    lines: 6-14
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: efe8704b2a4f5d875af342aeb3ec5d1ad639768fd6bd1256c247dd10646f38d9
  - path: tests/fakes/workflow.py
    lines: 11-80
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 06b7b91be8cc0e988bb8eae0b755ebeb3ec2179468e06278e03dbfe3ab607c32
- id: A-60
  kind: test
  statement: test_release_gate.py reports a problem only for a version listed in releases.json with another
    digest or controls level, a version below the newest listed one, or a lower controls level.
  evidence:
  - path: tests/contract/test_release_gate.py
    lines: 13-22
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: b78d9e9b6b90670f8db69e8b58731b0843b1efd2ee6a1adb87ee4eb33305c98a
  - path: src/orqlet/domain/versions.py
    lines: 56-83
    revision: e6fe500eb3ed03d043e27975d5fb24b08113cda0
    sha256: 956911aa4378c2439afdaed910442bf562de8f00440bbcb343f3caf2a32ee8bd
unknowns:
- id: U-1
  what: 'No recorded form of the person''s acceptance of as-is.md exists: no skill step sets the header
    status to approved and no command checks acceptance. Design and plan approval are host evidence that
    an offline gate status never has, so it always reports NOT_RUN. How a later phase detects an unaccepted
    or unapproved prerequisite is not stated.'
  material: true
  merged_from:
  - workflow-sources/U-1
  - trace-inject-handoff/U-4
- id: U-2
  what: No threshold for 'materially outdated' is defined. Gate status treats any mismatch in five header
    components as stale, and a base_revision move only when files in scope changed. Whether a skill-only
    release, which changes protected_set_digest and workflow_version, counts as material is not decided.
  material: true
  merged_from:
  - trace-inject-handoff/U-5
- id: U-3
  what: How a later phase detects an artifact from another project is not stated. The artifact header
    has no project identifier, and whether workflow_version, protected_set_digest or base_revision tell
    projects apart is not established. Whether two receiving projects can share one project.uuid, for
    example through a copied profile, and so share journals and backups, is not tested.
  material: true
  merged_from:
  - trace-inject-handoff/U-3
  - project-context/U-8
- id: U-4
  what: Which receiving-project facts the skills are to carry (for example project name, target branch,
    prompts_dir, enabled clients, stack, scopes or commands) is not stated. Today no profile value reaches
    a skill body.
  material: true
  merged_from:
  - trace-inject-handoff/U-2
- id: U-5
  what: Where a skill is to find a receiving project's actual build, lint, type-check and test commands
    is not stated. No code, answer key or command writes profile.commands, although the plan contract
    calls check_ref 'a profile command id'. doctor and sync skip seeded files and upgrade keeps a team
    edit to the seeded profile, but whether hand-editing it is the intended way to fill commands is not
    stated. This repository keeps its checks in ci.yml and pyproject.toml (A-35), not in its profile.
  material: true
  merged_from:
  - project-context/U-3
  - project-context/U-4
  - project-context/U-7
- id: U-6
  what: 'Which applicable_rules_hash a phase header is to record is not stated: the all-rules value of
    standards.lock.yaml that gate status compares against, or the query-filtered value that `orqlet standards
    for` prints. On 2026-11-02 `standards for --phase research --role researcher` printed 56502a0e...
    (equal to the lock), while `standards for --path src/orqlet/workflow/skills --phase design --role
    architect` printed 03dd4e37....'
  material: true
  merged_from:
  - project-context/U-2
- id: U-7
  what: The person answered in Q-5 that a receiving project chooses the location of its phase outputs.
    Q-3 limits the change to skill texts and references, Q-4 to existing commands and files, the validators
    and commands fix docs/design (A-36, A-37), and exempt.yaml says a project cannot change its list (A-38).
    No code that reads the workflow-artifact entry of exempt.yaml was found beyond its contract. Ledger
    conflict C-1 awaits the person's ruling.
  material: true
  question_ref: Q-5
  merged_from:
  - project-context/U-5
- id: U-8
  what: 'The request asks that local edits be detected and handled explicitly, but installed SKILL.md
    and reference files are protected: upgrade restores an edited one with ORQ-W096 and doctor reports
    it as ORQ-E150. Whether this satisfies the request, or a local edit to an installed skill is to survive
    an upgrade, is open as Q-8.'
  material: true
  question_ref: Q-8
  merged_from:
  - trace-inject-handoff/U-1
- id: U-9
  what: Q-6 put orqlet-research, orqlet-design, orqlet-plan, orqlet-implement, orqlet-review, orqlet-onboard
    and the role prompts in scope. Which phase word `orqlet standards for` is to receive for the fourth
    phase (`implement` or `implementation`) is not stated; the resolver compares it literally, and no
    rule in this repository's .prompts/rules.yaml has a phase scope, so the receiving projects' phase
    words are unknown.
  material: true
  question_ref: Q-6
  merged_from:
  - workflow-sources/U-3
  - install-ownership-tests/U-9
- id: U-10
  what: Which workflow_version this change takes is not decided. A skill change means rebuilding MANIFEST.json
    and raising the version (A-18), which changes the input version in the lock and the AGENTS.md marker.
    No tool writes releases.json, which lists only 0.1.0, and whether each release gets an entry is not
    stated. Q-7 answered that this repository's installed files are regenerated with `orqlet upgrade`
    as the last plan phase.
  material: true
  question_ref: Q-7
  merged_from:
  - workflow-sources/U-2
  - workflow-sources/U-4
  - workflow-sources/U-5
  - render-adapters/U-6
- id: U-11
  what: 'Whether Claude Code, Codex and Cursor load the emitted files and honour their invocation fields
    is documented, not observed (ORQ-L001). Unobserved in particular: whether Codex honours `allow_implicit_invocation:
    false` and how it treats `disable-model-invocation`; whether Cursor lists a skill twice when `.claude/skills`
    and `.agents/skills` both exist, which the stored Cursor page makes possible (A-27), and which copy
    it starts; whether Cursor accepts the rule `globs` format.'
  material: true
  merged_from:
  - render-adapters/U-1
  - render-adapters/U-2
  - render-adapters/U-3
  - render-adapters/U-8
- id: U-12
  what: No check was found that scans rendered or installed files for unresolved placeholders; the only
    check covers the `{{lines}}` slot of the four templates. Whether the requirement 'no unresolved placeholders'
    covers the angle-bracket tokens such as `<task>` that the skills ask the agent to fill is not stated.
  material: true
  merged_from:
  - render-adapters/U-5
  - install-ownership-tests/U-6
- id: U-13
  what: Searches of tests/ found no test that installs into two project roots with different context,
    no upgrade over an AGENTS.md with team text outside the blocks, no upgrade over a locally edited SKILL.md,
    no comparison of files written by init or upgrade with the golden files, and no parse of the rendered
    Codex TOML roles or sidecars with a TOML or YAML parser. Checks outside tests/ that might cover them
    were not searched.
  material: true
  merged_from:
  - install-ownership-tests/U-1
  - install-ownership-tests/U-2
  - install-ownership-tests/U-8
  - trace-inject-handoff/U-6
  - render-adapters/U-4
- id: U-14
  what: 'Not run: whether upgrade drops the lock entry of a recorded shared file whose markers broke (C-15);
    whether any command removes a diff file under .orqlet/ after a manual merge; whether an upgrade with
    an unchanged workflow and a different CLI version writes only the lock; why this repository''s role-bindings
    diff file is empty.'
  material: true
  merged_from:
  - install-ownership-tests/U-3
  - install-ownership-tests/U-4
  - install-ownership-tests/U-7
  - install-ownership-tests/U-5
- id: U-15
  what: 'Not established: the intended role of Bound.upstream, which no use case reads; what spike S-21
    found about client_version; what `<role>` stands for in `reviews/<role>-design.md`; the tester record
    format, which no skill or reference describes; which command re-renders the AGENTS.md conventions
    block after `orqlet profile answer`.'
  material: false
  merged_from:
  - trace-inject-handoff/U-7
  - render-adapters/U-7
  - workflow-sources/U-6
  - workflow-sources/U-7
  - project-context/U-6
- id: U-16
  what: 'Researchers read the working tree without git. Every cited range resolved by hash at e6fe500,
    whose tree equals 058de9e outside this task folder, but statements were spot-checked rather than each
    compared with its lines. Not traced: the doctor drift computation, the next_release() test helper,
    and the ledger and knowledge-impact validators. The CI matrix beyond this machine was not run.'
  material: false
  merged_from:
  - project-context/U-1
  - trace-inject-handoff/U-8
  - install-ownership-tests/U-10
contradictions:
- id: C-1
  sources:
  - docs/design/phase-skill-contracts/questions.yaml:95-116
  - docs/design/phase-skill-contracts/questions.yaml:47-94
  - src/orqlet/application/usecases/validation.py:25-26
  - src/orqlet/workflow/exempt.yaml:1-2
  note: The person's answer to Q-5 makes the phase-output location configurable per receiving project.
    The answers to Q-3 and Q-4 allow only skill texts, references and existing commands and files, while
    the validators fix the task root at docs/design and exempt.yaml says a project cannot change it. Recorded
    as ledger conflict C-1 with no ruling yet.
- id: C-2
  sources:
  - src/orqlet/interface/cli/commands/standards.py:84-88
  - src/orqlet/application/usecases/gate_status.py:80-93
  note: Both values are called applicable_rules_hash. `standards for` returns rules_hash over the query-selected
    rules. gate status binds against the standards lock's value, which render_all computes over all resolved
    rules (render_all.py:247-260).
  merged_from:
  - project-context/C-1
- id: C-3
  sources:
  - src/orqlet/application/usecases/standards_for.py:134-155
  - src/orqlet/application/usecases/render_all.py:81-98
  note: '`standards for` builds the stack from a fresh scan at execution time. Render and explain build
    it from the technologies, frameworks and kind stored in the profile.'
  merged_from:
  - project-context/C-2
- id: C-4
  sources:
  - src/orqlet/application/usecases/standards_for.py:200-215
  - src/orqlet/application/usecases/review_prepare.py:48-53
  note: standards_for and resolve_for read the prompts folder from the profile's prompts-dir standards
    source. review prepare packs the fixed paths .prompts/rules.yaml and .prompts/foundations.md, and
    explain passes prompts_dir '.prompts' (explain.py:53).
  merged_from:
  - project-context/C-3
- id: C-5
  sources:
  - src/orqlet/application/contracts/plan.py:28-32
  - src/orqlet/application/usecases/validate_plan.py:136-148
  note: The plan contract comment calls check_ref 'a profile command id', as does test_record.py:18. The
    validator never resolves it against profile.commands, and no code fills profile.commands (.orqlet/project-profile.yaml:151
    is {}).
  merged_from:
  - project-context/C-4
- id: C-6
  sources:
  - src/orqlet/workflow/skills/orqlet-plan/skill.md:17-17
  - src/orqlet/application/usecases/gate_status.py:110-123
  note: The plan skill tells the agent to run `orqlet gate status <task>` and says a NOT_RUN result is
    not a pass, but gate status with a task always returns NOT_RUN offline. The implement skill (skill.md:11)
    explains this and asks the person instead; the plan skill does not.
  merged_from:
  - trace-inject-handoff/C-1
- id: C-7
  sources:
  - src/orqlet/workflow/skills/orqlet-research/skill.md:13-13
  - src/orqlet/application/contracts/artifact_header.py:45-52
  note: The research skill says to copy gate status's `bound` values into the header. Gate status prints
    workflow_version and protected_set_digest inside `bound` (gate_status.py:59-67), but the header keeps
    those two at its top level, outside `header.bound`.
  merged_from:
  - trace-inject-handoff/C-2
- id: C-8
  sources:
  - src/orqlet/workflow/skills/orqlet-design/skill.md:18-18
  - src/orqlet/workflow/roles/orqlet-arch-reviewer.md:6-6
  - src/orqlet/workflow/roles/orqlet-security-reviewer.md:6-6
  note: The design skill starts both reviewers on the design, with the design, the AS-IS file and the
    standards. Both role prompts say the reviewer receives only the path of a read-only packet of the
    staged snapshot, diff, plan, design, standards and records.
  merged_from:
  - workflow-sources/C-1
- id: C-9
  sources:
  - src/orqlet/workflow/baseline/baseline.md:19-19
  - src/orqlet/workflow/commands/standards.md:7-7
  - src/orqlet/workflow/skills/orqlet-review/references/review-format.md:51-51
  - src/orqlet/application/contracts/question_ledger.py:23-23
  note: 'The baseline and the standards command call the fourth phase `implementation`. The review-format
    sample (`phase: implement`), the Phase literal of the question ledger and the skill name use `implement`.'
  merged_from:
  - workflow-sources/C-2
- id: C-10
  sources:
  - tools/build_manifest.py:6-8
  - src/orqlet/domain/versions.py:69-74
  - src/orqlet/workflow/releases.json:1-10
  note: The docstring of build_manifest.py says that a digest change without a workflow_version change
    is a release defect caught by test_release_gate.py. The check catches it only for a version listed
    in releases.json, which lists only 0.1.0, so a change made at 0.3.3 without a version bump passes
    that test.
  merged_from:
  - workflow-sources/C-3
- id: C-11
  sources:
  - docs/design/orqlet-implementation/adr-005-deterministic-renderers-and-golden-tests.md:11-11
  - src/orqlet/application/ports/instruction_adapter.py:112-117
  note: 'ADR-005 describes a renderer as render(definition, client, client_version). The adapter port
    is render(request: RenderRequest), with client_version as a field of the request that compose never
    sets (render_all.py 121-127).'
  merged_from:
  - render-adapters/C-1
- id: C-12
  sources:
  - src/orqlet/adapters/render/emit.py:7-11
  - tests/unit/render/test_front_matter_views.py:45-61
  note: The emit docstring says the release tests check every generated file. The front-matter view test
    covers only the skill, agent and Claude command path classes, not the rule files (which are written
    fully quoted), the Codex TOML roles or the sidecars.
  merged_from:
  - render-adapters/C-2
- id: C-13
  sources:
  - src/orqlet/application/ports/instruction_adapter.py:60-66
  - src/orqlet/application/usecases/resources_view.py:142-169
  note: ClientSkill is documented as 'A workflow skill' named 'orqlet-<phase>'. The same type also carries
    the resource skills orqlet-tool-<id> and orqlet-resources (agent_may_start true), and the shipped
    set includes orqlet-onboard and orqlet-review.
  merged_from:
  - render-adapters/C-3
- id: C-14
  sources:
  - src/orqlet/application/ports/change_journal.py:33-33
  - src/orqlet/application/usecases/release.py:97-97
  note: The journal port says the command is 'init', 'upgrade' or 'rollback', but release applies its
    plan with command 'release'.
  merged_from:
  - install-ownership-tests/C-1
- id: C-15
  sources:
  - src/orqlet/domain/changeplan.py:232-247
  - src/orqlet/domain/changeplan.py:333-334
  note: A BlockError on a file with desired blocks keeps no record for those blocks, while a BlockError
    on a file with only stray recorded blocks keeps the old records. The two branches handle recorded
    entries differently.
  merged_from:
  - install-ownership-tests/C-2
- id: C-16
  sources:
  - .orqlet/proposals/.orqlet__versions.yaml.diff:7-19
  - .orqlet/versions.yaml:1-14
  note: The versions diff file still shows pin 0.1.0 to 0.2.0 and workflow 0.3.1 to 0.3.3 as pending,
    yet the live versions file already holds those values.
  merged_from:
  - install-ownership-tests/C-3
self_check:
  schema: orqlet.self-check/v1
  checked_against:
    role: researcher
    phase: research
    confirmed_requirements:
    - Q-1
    - Q-2
    - Q-3
    - Q-4
    - Q-5
    - Q-6
    - Q-7
    applicable_standards:
    - 'orqlet standards for --phase research --role researcher: 15 rules, applicable_rules_hash 56502a0ec5eda3b13b4c9d97c7d4dfa41df82c86a206e36dd5d2d92aab299b97'
    evidence:
    - docs/design/phase-skill-contracts/fragments/
    - docs/design/phase-skill-contracts/evidence/web/cursor-skills.md
  checks:
  - what: The question ledger is valid and no open question blocks research
    how: orqlet validate ledger docs/design/phase-skill-contracts/questions.yaml (PASS)
    result: pass
  - what: The header bound values equal the current installation
    how: orqlet gate status --json at e6fe500 (verdict PASS, values copied)
    result: pass
  - what: Every evidence entry was produced by Orqlet's own citation at the base revision
    how: orqlet.application.usecases.evidence_cite.cite for every range of the five fragments and this
      file (0 errors)
    result: pass
  - what: Load-bearing statements match the source
    how: Read of the six skill sources for standards for and gate status steps; gate_status.py:105-123;
      exempt.yaml:1-14; resolver.py:60-66; capabilities.py command count; two runs of orqlet standards
      for compared with .orqlet/standards.lock.yaml:3
    result: pass
  - what: Static checks at the base revision
    how: uv run ruff check . (All checks passed); ruff format --check (527 files already formatted); mypy
      (no issues in 346 files); lint-imports (5 kept, 0 broken); tools/export_schemas.py --check (exit
      0); tools/build_manifest.py --check (exit 0)
    result: pass
  - what: Test suite at the base revision on this machine
    how: uv run --frozen pytest -q -p no:cacheprovider on macOS with Python 3.12.11 (7725 passed, 1 skipped
      as Windows-only, exit 0)
    result: pass
  - what: the AS-IS file is accepted by the person
    how: 'the person chose "Yes, I accept it as it stands" in conversation on 2026-11-02 when /orqlet-design
      was started, and answered Q-8 and ruled on C-1 (now Q-9); this is not a merge on the protected baseline'
    result: pass
  unverified:
  - Statements were spot-checked; not every statement was compared with its cited lines.
  - No client (Claude Code, Codex, Cursor) was run to observe how it loads the emitted files.
  - The CI matrix beyond macOS with Python 3.12 (Linux and Windows, Python 3.13 to 3.15) was not run.
  - The word 'proposals' in the path .orqlet/proposals/ (A-40) is flagged by the advice lint; it quotes
    a path, not advice.
  questions:
  - Q-8 (open, blocks design) asks how a locally edited installed skill is handled.
  - Ledger conflict C-1 (configurable location against Q-3, Q-4 and the fixed docs/design root) awaits
    the person's ruling.
---
