---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: workflow-efficiency
  status: approved
  workflow_version: 0.5.1
  protected_set_digest: 703abd17389c189e3cf20a71a49e6ce66b652e8ca50ebcee3de95a59478b5dbe
  bound:
    base_revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    standards_lock_hash: 12486d9b48af8b2f61117d556568d3482b1641cd606e8652965dcc44babce930
    applicable_rules_hash: e5618439f62ec2b01a2a1719ee3902a92ca1829827de0b41242cb351c37e4e15
    profile_version: 1
base_revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
scope:
  paths:
  - src/orqlet/**
  - tests/**
  - .prompts/**
  - .github/**
  - .orqlet/**
  - .agents/**
  - .claude/**
  - .codex/**
  - .cursor/**
  - AGENTS.md
  - README.md
  - pyproject.toml
  - uv.lock
  - docs/design/work-status.md
  - docs/design/workflow-efficiency/plan.yaml
  - docs/design/workflow-efficiency/design/**
  - docs/design/workflow-efficiency/questions.yaml
  - docs/design/workflow-efficiency/tests/**
  - docs/design/workflow-efficiency/reviews/**
  - docs/design/workflow-efficiency/knowledge/**
  - docs/design/workflow-efficiency/evidence/**
  request_ref: workflow-efficiency
research_mode: parallel-subagents
size_budget:
  max_words: 1200
facts:
- id: A-85
  kind: operation
  statement: Project instructions require four phases and human design/plan approval; workflow-efficiency
    remains the only active priority.
  evidence:
  - lines: 18-20
    path: AGENTS.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 0ba1e06ff5d533ac0ea65e9d608eb8600ee89e03d710a500c76be2a8817fbb07
  - lines: 100-105
    path: AGENTS.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 7188469f0e1933176128d29bcdfac2cbed528768877251fbdc5a80b6b5b614e3
- id: A-86
  kind: flow
  statement: Every implementation phase includes tester, coder, three reviewers and knowledge work; files
    outside its list require a plan amendment.
  evidence:
  - lines: 3-7
    path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a8dd59335c4282ec5efd8df2e30542c8c4c62a09a1763775f2f849d66ccce9d8
  - lines: 17-23
    path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 4044fc741e5829f6b74f85ccd784b62fcb0393e0d28676457950012b02907290
- id: A-87
  kind: flow
  statement: Each phase validates knowledge/test records, invokes review and a PR writer, then awaits
    acceptance; reviewed code/test changes repeat knowledge, test-record and review work.
  evidence:
  - lines: 35-40
    path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 37df5bbd2677a34643932ffbfdb2c77aa0a7c9c8ac48cc041d9b879cb5bc9d10
- id: A-88
  kind: flow
  statement: Citations are reused per phase and planned targeted checks serve iteration; full checks run
    before review and per rework round, with strict unchanged-input reuse conditions.
  evidence:
  - lines: 29-34
    path: src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: ec1a91228c21195191370867cab5fb971cf2594f59e70eda854ee5fc36b102d6
- id: A-89
  kind: flow
  statement: The tester reuses coder citations but verifies differences, untracked files and hashes; warning-list
    commands return to the coder for human authorization.
  evidence:
  - lines: 10-19
    path: src/orqlet/workflow/roles/orqlet-tester.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: c917fcaccc15d7a817b009ac141b42a6fb660489a900918a8e5e0049bcbe60ab
- id: A-90
  kind: flow
  statement: Review starts three independent reviewers with a staged-snapshot packet, validates three
    records per round, and repeats after snapshot changes, capped at three rounds.
  evidence:
  - lines: 24-34
    path: src/orqlet/workflow/skills/orqlet-review/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 51c28cb606c6a3f3b8daec563b61f15a82e4404b10933511b7726b42deaeb664
  - lines: 45-48
    path: src/orqlet/workflow/skills/orqlet-review/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: d45e3902d464fc869ee5d0de59964e22bc9b52664d71e4686e76adcb9fc4ed94
- id: A-91
  kind: flow
  statement: Nested review skips skill model resolution; later implementation phases can reuse validator
    results after confirmed planned-work staleness and unchanged approved files.
  evidence:
  - lines: 25-27
    path: src/orqlet/workflow/skills/orqlet-review/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: f723e94ab5c6439cb1a71c1de2cd84c9bf6604c01d2ca460375c31f6acef01ee
  - lines: 27-29
    path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 6dce37521bd88613dec91ef236311bc87069fe6bb6b6c024230a5dca363c7ed1
- id: A-92
  kind: flow
  statement: Input checks require human-supplied merge references and stale-input confirmation; headers
    bind before the first branch commit to survive squash merges.
  evidence:
  - lines: 62-81
    path: src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 4aac7ad554fcca9f45ebf051a4c4086003492f4ff56eb0cef4190b2ccfa397f8
  - lines: '92'
    path: src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: e68a2ea38f0bad8568b926a034a87c84cef791fc349dc5eecd7cc8819c1011e1
- id: A-93
  kind: flow
  statement: Design discovery of an undocumented current-code fact triggers an AS-IS refresh; D2/D3 designs
    require architecture and security reviews, restarted after hashed design changes.
  evidence:
  - lines: 35-38
    path: src/orqlet/workflow/skills/orqlet-design/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: ce75b4714529134f41eb11fce76ca73b3b7b9c361d440a88b0936080addcdebe
  - lines: 52-55
    path: src/orqlet/workflow/skills/orqlet-design/skill.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 30bd53962890d2dd740def8355a3294f5906365be2be977acdf1fcd7aa7e8726
- id: A-94
  kind: interface
  statement: D1 still requires three diagrams and nine brief sections; current references set warning
    targets of 1,200 design words and 400 words per plan phase.
  evidence:
  - lines: 13-35
    path: src/orqlet/workflow/skills/orqlet-design/references/design-format.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: eb9167fdc6fa08639d9aaa8a37968a37cec3c5dec9de04655ba473d41e74f627
  - lines: 9-14
    path: src/orqlet/workflow/skills/orqlet-plan/references/plan-format.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 25d479af2545fab063b61562d339576ea597f801297a1ef2d81b0c0aaaf38331
- id: A-95
  kind: test
  statement: Tests pin wording and section placement, require identical phase-contract copies and cap
    their words; the manifest lists four copies with one hash.
  evidence:
  - lines: 87-116
    path: tests/unit/test_workflow_efficiency_text.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 42bcd3304d8531e986ca2327da82ef08c38d42b7f1bdad339ffd8afddc389f56
  - lines: 209-263
    path: tests/unit/test_workflow_efficiency_text.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 2c4f1984576d0e4ccaec437361675949ed158a7b3e4b8f9c3a958358d495371f
  - lines: 151-205
    path: tests/unit/test_workflow_phase_contract_text.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: c67d14a431a36917b40ae26dd62902066c987a9bb502e8e9a14a358498d4206e
  - lines: 573-599
    path: tests/unit/test_workflow_phase_contract_text.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a280444387b4849258d5a889cf828c5398f174bc4fefcbaf1f7ad740375a7c77
  - lines: 236-274
    path: src/orqlet/workflow/MANIFEST.json
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a0d00dbda21f4c0861e530a918a489e0c39da6890cc23e77120ae0e93c30ae62
- id: A-96
  kind: structure
  statement: Eight installed phase-contract copies appear in the generated lock; project instructions
    require editing their sources and regenerating generated files.
  evidence:
  - lines: 30-38
    path: .orqlet/generated.lock.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: cb2d8b68a2adbf8ea4adbe25fea45c79901d8f59cd692df0f4c8db08259fb2ee
  - lines: 54-62
    path: .orqlet/generated.lock.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 9224cb744d7bd1aac5172491d5ca02f6a423d2c53da723d92e84fc3c5efd6804
  - lines: 94-102
    path: .orqlet/generated.lock.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 799251078c12bc7274ffe8764d1cb7eec924fc9632f4e1c56c178f5cb2b0737f
  - lines: 134-142
    path: .orqlet/generated.lock.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 6554f0eb25fe5179fb1fa6215c4bcac5230e50006a6f057453af91784de2db5e
  - lines: 582-590
    path: .orqlet/generated.lock.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: f1eeca8f4a55a6000a8ab51f5af074fba7792ba4e8eee441fb5b29134fcd096b
  - lines: 598-606
    path: .orqlet/generated.lock.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 903dacb806fdc68e2c78a920d9910928f951da529bb521d18780ad90b8983635
  - lines: 622-630
    path: .orqlet/generated.lock.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: fc25e75830726bedd5d4723be64ac28ba57323365e0b443712b748f0c3ee2177
  - lines: 654-662
    path: .orqlet/generated.lock.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: d6cfa323df803f608de5d1b5a8d7cdaed81846c58bb537dad2d84f38f4c515f9
  - lines: 48-50
    path: AGENTS.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a3f1b1a3bb811168d09d1cbf8310b2789724ce65bbca873c361542ca7fcfa76d
- id: A-97
  kind: operation
  statement: Eight implementation phases specify 51 check-list entries; each phase includes lint, formatting,
    types, pytest and phase-gate checks.
  evidence:
  - lines: '68'
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: e4451dd9da8f0bfd3b6899898323bee9a4955355a068c7ba25fa9854764851fe
  - lines: '193'
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: e4451dd9da8f0bfd3b6899898323bee9a4955355a068c7ba25fa9854764851fe
  - lines: '296'
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: e4451dd9da8f0bfd3b6899898323bee9a4955355a068c7ba25fa9854764851fe
  - lines: '371'
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: e4451dd9da8f0bfd3b6899898323bee9a4955355a068c7ba25fa9854764851fe
  - lines: '461'
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 98643e5a85c5833a663906aff5257a29509cd784ac9bd976b4e7739a7590d89f
  - lines: '601'
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 6dc57d4f4b075a0f46997652d5487a0f75cb64de9887aa412dbd5ec18fc27664
  - lines: '823'
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 6dc57d4f4b075a0f46997652d5487a0f75cb64de9887aa412dbd5ec18fc27664
  - lines: '1115'
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 08f3a79847c7b0ba86ef31983c3c0b61124fc6bc11a465f539236cf970320421
- id: A-98
  kind: test
  statement: Eight retained final pytest summaries total 14,460.78 seconds (241.013 minutes), on local
    Python 3.12.11; these are claimed records, not independently measured execution.
  evidence:
  - lines: 14-15
    path: docs/design/workflow-efficiency/tests/P-1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: d3a0e24299f6bbe0fe0a748b74e57c466a95e6b639de5b8aa41be6f704025e4d
  - lines: 36-44
    path: docs/design/workflow-efficiency/tests/P-1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 78745c47d7402c7f1edeff7e37fc4f3e37857cd84a890e82ed0661171a316512
  - lines: 36-44
    path: docs/design/workflow-efficiency/tests/P-2.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 82987cbb78f6013f3132c1c0ed11ac021a2945f8b641a9499a5fe71c4f9c5383
  - lines: 36-44
    path: docs/design/workflow-efficiency/tests/P-3.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 8e0d86da8f8a2bd21b3f6819af76edbffa66772f447652bed3ad45b654ba708f
  - lines: 36-48
    path: docs/design/workflow-efficiency/tests/P-4.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 9c17b61f7318fa27e434d75be7312c909e1678ec7decb4bd0a18c8729c3d1333
  - lines: 41-53
    path: docs/design/workflow-efficiency/tests/P-5.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 2e99d41351409cf02ebec1f10c3e26a22fcf6d24d791cda8452ff315363150c4
  - lines: 37-45
    path: docs/design/workflow-efficiency/tests/P-6.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 337227786d41c43dbd1f69a49625a1d13414db05d027c98063651c910880044e
  - lines: 37-45
    path: docs/design/workflow-efficiency/tests/P-7.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 1671fee66741149ac7d1282fb25c9bef5dfd1a71246416c2353ccf2314333b5a
  - lines: 44-52
    path: docs/design/workflow-efficiency/tests/P-8.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 388c23c3c4feec55e0a1be4f316e58e3b244330216128c9918a8ee67e12d917f
- id: A-99
  kind: test
  statement: P-7 records three full suites and golden regeneration per rework round; only its final 1,758.03-second
    duration is retained.
  evidence:
  - lines: 37-45
    path: docs/design/workflow-efficiency/tests/P-7.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 1671fee66741149ac7d1282fb25c9bef5dfd1a71246416c2353ccf2314333b5a
- id: A-100
  kind: test
  statement: P-7/P-8 report three lint errors, ten type errors and two collection errors in frozen files;
    both test records remain NOT_RUN despite 14,000-plus passing tests.
  evidence:
  - lines: 14-44
    path: docs/design/workflow-efficiency/tests/P-7.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 9ba9e1f9cfdcdf258a17836029c20e7848bfda7b550584c8e02e827df31f6cd0
  - lines: 14-51
    path: docs/design/workflow-efficiency/tests/P-8.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: de073d492215cbe83c973dbadbf07f058a840ea6df0187cf895e558260c8373a
- id: A-101
  kind: operation
  statement: P-1 architecture and P-8 code reviews remain advisory/NOT_RUN for insufficient independence;
    P-8 code also records absent approved binding and unknown model identities.
  evidence:
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-1-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a24a4e982f6cf1e81a4529f494aa75cc07d98047688919ddbbde7b75c7a0e02f
  - lines: 28-56
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-1-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 03493e6e8bacaa799f9ff1985dbf54a0fc93ca4018a00bf1762a3ddaf04a4db0
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-8-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 3aad96cd32f18de30414b9082cbd99285f8b254763aab0c5d6eb54428c2c753b
  - lines: 28-59
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-8-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 5df733ab3fe8718aa663b49ae8e3bea7afe02199acef0947501eb05f9b8dadbc
- id: A-102
  kind: operation
  statement: P-7/P-8 retain round-1 records describing actual third/second rounds; earlier bindings or
    reviewer text were lost, and earlier rounds found wording/version defects.
  evidence:
  - lines: 3-6
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-7-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 4eab6391d416e498a4a2719133be2be5e57ff2245664a8188cf8e94689a12cf7
  - lines: 47-60
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-7-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 1f378925bbedc2326e5f9e21e54d73c038dbc40f01f0cc841a2f4281b896a1aa
  - lines: 3-6
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-8-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a7b9c3d09b0b97bd5136a6d53e618aebc932b11df986f6ad45e0fc6c207fb561
  - lines: 54-59
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-8-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 87caafc7894c126ecdf5827c534346c9be6a75813497e02656c520f0fbee2e3b
- id: A-103
  kind: operation
  statement: Design records describe an authorized fourth review round, another research refresh/rebinding,
    and human review of fourth-round changes instead of a fifth agent round.
  evidence:
  - lines: 291-293
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-design-r3.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 0b465dbdc8803556e6158424e93ce9200b1b0bfa01127d9556bfaafb2281b51e
  - lines: 335-337
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-design-r4.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 3ea6a7d495b55c95a0141616cf2630e975f217da047821812481d55d35b726c6
  - lines: 419-445
    path: docs/design/workflow-efficiency/questions.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: f3d2c82f822bbc86d9c2b4b889752be64a9a814ed8d5ef4854a22d6eddffc633
- id: A-104
  kind: operation
  statement: The first security design review identified dependency-watch, task-name, negative-test and
    evidence-boundary gaps; author responses record accepting changes for all four.
  evidence:
  - lines: 19-29
    path: docs/design/workflow-efficiency/reviews/security-reviewer-design-r1.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 3f79a9c71d0bff78bddcc270573a4529d6dc6a2d1b387df9f0c9890e6ef95f7d
  - lines: 44-57
    path: docs/design/workflow-efficiency/reviews/security-reviewer-design-r1.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 6ec13a21f68982a945a008886376bb9e7aa1e02cf37f6dca164498ef4ecd6cc1
- id: A-105
  kind: test
  statement: P-4 records oversized test filler and later fence tests; P-5 records an output-field expectation
    omitting populated candidates, causing test rework.
  evidence:
  - lines: 38-47
    path: docs/design/workflow-efficiency/tests/P-4.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: bdefd1483f5d14ffa54c6851e4dcb4a7614f2b6090dfe8f4be1feb1c0aa0d45b
  - lines: 43-52
    path: docs/design/workflow-efficiency/tests/P-5.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 90bc06e489dc34ab316c924ac92dffdf1a49848fe18b79b5665d6ccc8b02d404
- id: A-106
  kind: operation
  statement: P-4/P-5/P-7 record stale phase gates caused by earlier task commits and human confirmation
    of the planned-work exception.
  evidence:
  - lines: 49-55
    path: docs/design/workflow-efficiency/tests/P-4.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 693a104719d90eb9b981b5e9336af20a2c2b72dbfbc37f46be817745f5fa38bb
  - lines: 54-60
    path: docs/design/workflow-efficiency/tests/P-5.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 8cbcfb90fa07d11f55db71ec9af334c711457eb9d6fc19a8d9c11d427d7bcd3e
  - lines: 46-51
    path: docs/design/workflow-efficiency/tests/P-7.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 5a56dacc65d7ea4eabf7fb903c00428832f51262089420f03b841a0568c57880
- id: A-107
  kind: operation
  statement: CI configures unfiltered PR/main-push checks, twelve OS/Python test combinations, disabled
    setup-uv caching and two wheel builds; actual run counts are unverified.
  evidence:
  - lines: 3-12
    path: .github/workflows/ci.yml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 4366a760c8488e0db6ee4443a05a1d9210dcc680293c03abf1f528cf3527d897
  - lines: 17-107
    path: .github/workflows/ci.yml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 7ebc3f340aa0b30896abed7fa493e654ec1fab09b19aeb62e587e59bed23df4c
- id: A-108
  kind: operation
  statement: The historical transcript study lacks timings and phase boundaries; the current plan defers
    observed before/after run counts to an equivalent later task.
  evidence:
  - lines: 3-23
    path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 708885d1bb53ac199e66d55dfef4f93b4c4f65322048adae470ffece9b43bdc5
  - lines: 35-46
    path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 5120256efd5e60dff4d5e8643af9484ebf3383b1de2c4297caa123e5221cc11e
  - lines: 1468-1474
    path: docs/design/workflow-efficiency/plan.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: db6fa7017b5b8de1da1c7be0df3baeee3f9a7bb0bbe6325398bb1e794d993ada
- id: A-109
  kind: operation
  statement: Work status makes human merges the phase approvals; pytest selects all tests with sockets
    disabled and warnings as errors, while mypy includes source/tests/tools.
  evidence:
  - lines: 8-29
    path: docs/design/work-status.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 6697b5ea04015320ed963fd6cf1a2a48f38f9c6ae2db00c5e4640285979104aa
  - lines: 63-80
    path: pyproject.toml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 803189fe7ec3aac617a0c7e7881150d98ef96ee90ad1ea184e3d6a233300f696
- id: A-110
  kind: flow
  statement: Gate status assesses three task artifacts and reads locks/profile/HEAD; offline approval
    is now informational rather than an unconditional not-run reason.
  evidence:
  - lines: 81-123
    path: src/orqlet/application/usecases/gate_status.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: ed28feef343a3cae4ff0ab44a219ed3b88185083d5c6ef69c39a3437fbfc3316
  - lines: 145-165
    path: src/orqlet/application/usecases/gate_status.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 3089b8019cb4128f331211056de2641a450db577daee3d2672e190c142d89ed0
- id: A-111
  kind: flow
  statement: Changes within artifact scope still produce staleness; a plan's scope includes all phases'
    operation paths, so earlier phases can stale later input checks.
  evidence:
  - lines: 169-229
    path: src/orqlet/application/usecases/gate_status.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 447d21d95d9f7b099906df5e15439443afefd6615cc783c61a4fa5238ffcbe47
  - lines: 11-30
    path: src/orqlet/application/usecases/staleness.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: ad1981d80b7483984d607ee8f46a6f0df70b7b8d6a2474068139830338c8de9e
- id: A-112
  kind: flow
  statement: Stale-input exceptions still require human confirmation; edits to research or plan artifacts
    are excluded from the planned-work exception.
  evidence:
  - lines: 75-81
    path: src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 7e9921bcec4e14c19695eebb1a9a1ab1441e7a53c8a15a7842fd77df5b566ff5
- id: A-113
  kind: flow
  statement: Review preparation enumerates the tree and reads eligible files before applying packet limits,
    exporting snapshot, diff and duplicate context copies.
  evidence:
  - lines: 49-51
    path: src/orqlet/application/usecases/review_prepare.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a0e155c24a6cb782ae7936329428006edd2a6f671d4af6a075153a7b430c2e08
  - lines: 131-184
    path: src/orqlet/application/usecases/review_prepare.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 752d616d3bc1bfb103c28327bb0987f9177c9d46e03d9eae3505cea3f46b1b12
- id: A-114
  kind: flow
  statement: Review preparation computes common bindings, analyzes knowledge, then recomputes components
    for available reviewer/client pairs across three roles and three clients.
  evidence:
  - lines: 218-250
    path: src/orqlet/application/usecases/review_prepare.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: b5241ac5ff352a540114983b958544e6f555f0713170a9ed0bc7407841ae5740
  - lines: 52-57
    path: src/orqlet/application/usecases/review_prepare.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: b4a44379de40879d3b67b5149a550bc717ff703590aaa4aa0dff6cab2dd51a95
- id: A-115
  kind: flow
  statement: Record validators recompute bindings; review/test validation reconstructs changes, and knowledge
    validation repeats candidate analysis.
  evidence:
  - lines: 122-158
    path: src/orqlet/application/usecases/validate_records.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: b3c002862b031b82ba3062f49ec1bad5e841282f672a1063be824184880e64d8
  - lines: 260-291
    path: src/orqlet/application/usecases/validate_records.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 1bd4c22edfc3589e3997a9199c0c275b6eb861ef14145e2a1aa8b227294ad9ee
  - lines: 409-436
    path: src/orqlet/application/usecases/validate_records.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 6bdfd79e48b9e4e22e37d62056d7873d1aa962971a6fd7458bb7b06a925131b2
  - lines: 482-509
    path: src/orqlet/application/usecases/validate_records.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: e4d614e8e011edc9697ebcf787bd9e5023081abab06157881dea531fe67e5203
- id: A-116
  kind: flow
  statement: Review bindings include test/knowledge record hashes; test bindings cover code/tests and
    plan, so evidence edits can stale reviews without staling tests.
  evidence:
  - lines: 38-55
    path: src/orqlet/domain/binding.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 291cb7c955363168367428f0d51268159f117d5086413a8c9e698a18d1b26863
  - lines: 386-392
    path: src/orqlet/application/usecases/binding_inputs.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 43652425b3f7425f2a5495a64cc4f517e54897bc01bbf96cc872090dc3d4812e
  - lines: 144-150
    path: src/orqlet/application/usecases/validate_records.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: cb7d91386285967d10e1f93b446b4093b91476bd6953c33f9470c12bcf3f5ff9
- id: A-117
  kind: flow
  statement: Binding computation rereads design, plan, standards and evidence inputs; Git caches trees
    per service instance, while blob-read calls start cat-file processes.
  evidence:
  - lines: 286-343
    path: src/orqlet/application/usecases/binding_inputs.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: b18ad1f1e8032f940d7c3a5c7abfc1abf554acea6ebaeb57d98a9bc2561a9d17
  - lines: 165-173
    path: src/orqlet/interface/cli/wiring.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 58dfbf955e946c28c9aeb7978ff430344e1005faeb3c36473d1efd61a01ea503
  - lines: 35-43
    path: src/orqlet/adapters/git/vcs_git.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: dfa9c7ddac6507b488fed4586cd739d20e35d389322180bb5b3802cf64472c1c
  - lines: 112-158
    path: src/orqlet/adapters/git/vcs_git.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: dc5f5f5c66f170839ddd0ace4a34a2af5e75eeeff7ea545ee77c85ef25422ade
  - lines: 20-33
    path: src/orqlet/adapters/git/objects.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: beef060597103a29ce09d9f22333886c173f498289466257bd6ee572a4ed1ef1
- id: A-118
  kind: interface
  statement: Evidence citation now accepts multiple file/range pairs in one invocation; each pair still
    reads its file separately.
  evidence:
  - lines: 33-52
    path: src/orqlet/application/usecases/evidence_cite.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 4beabfda1165bf6710c1a61f0174dbf3feee5cb8125bc4224b2d945b9177ad1c
  - lines: 79-95
    path: src/orqlet/application/usecases/evidence_cite.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 87dea2d420b4c0f7f3ee859915d901811ef736d8478abb3e02737b15e3ca60ee
  - lines: 21-48
    path: src/orqlet/interface/cli/commands/evidence.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: dd9de8cd10baa649a402b35af66b3e3002986582fd617586dc626600979f9445
- id: A-119
  kind: interface
  statement: AS-IS validation permits task-owned evidence at another revision after scanning and hash-checking
    its committed HEAD content; other evidence remains base-bound.
  evidence:
  - lines: 112-195
    path: src/orqlet/application/usecases/validate_as_is.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 3f2d2e42a60dac11cdf002b00895f9964c7cc8d45788b2089bc387bb123cd8ab
- id: A-120
  kind: structure
  statement: The approved profile identifies a Python CLI using uv and Typer, with Claude Code/Codex/Cursor
    enabled; .prompts supplies on-demand standards.
  evidence:
  - lines: 1-34
    path: .orqlet/project-profile.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 055138d0fad8e5ae801daf5e83793ffadb01f2a2ef60b3169957ca896150dfc4
  - lines: 158-170
    path: .orqlet/project-profile.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 36d6fea58486ddab42854d9cb6abc4f9d2aa33544f58c7a720ae29f099c0f730
  - lines: 3-10
    path: .prompts/README.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 3610b425cde44e935e5479f8733f751058a545f555914302375c638f53bf7f09
- id: A-121
  kind: structure
  statement: Repository CLI and packaged workflow both declare version 0.5.1.
  evidence:
  - lines: 1-3
    path: src/orqlet/__init__.py
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 7583db6ddcc642db216b0d2a1c6a90ae2d6397b66b7aea2419cd42c757338091
  - lines: 1-5
    path: src/orqlet/workflow/identity.json
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 22db2f1b774eb7b09dc9f37f868fadfa96026bb1b748ccd43ace45e7101dc8ec
- id: A-122
  kind: operation
  statement: The pre-implementation study reports medians of 15 full pytest segments and four review preparations
    across 27 implementation sessions, not current per-phase counts.
  evidence:
  - lines: 24-46
    path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 45c80b0a824cab28ae0d5c0a8c75126677585cf29b0e7d2f7b1830f2a71b1f42
- id: A-123
  kind: operation
  statement: Ledger Q-12/Q-13 record research re-citation and another refresh during design because squash
    history and missing base-binding facts blocked progression.
  evidence:
  - lines: 215-264
    path: docs/design/workflow-efficiency/questions.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: eb9d461f6343ccb5006a8b061aaedc733cc92d1cae7e8b34bb890b8d5de8ce66
- id: A-124
  kind: operation
  statement: All 24 committed implementation reviewer records for P-1 through P-8 report advisory assurance
    and NOT_RUN; they are not 24 successful independent gates.
  evidence:
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-1-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a24a4e982f6cf1e81a4529f494aa75cc07d98047688919ddbbde7b75c7a0e02f
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-2-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: a7a41f9382286abc408525ec99087ae66d4cd8eae3b135e00d44d88f7bcbc7f6
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-3-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 51bb349f4f6e905704e0313d4982493898c804500e75de9d601068550f83b5b2
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-4-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 79c239dd711284bf747e135f188fe8180685eae94beb8fa794c37d26a3355d7a
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-5-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 389e46823241f7d04c2f90d80236dbdad12f18389385dfdb82f69b1d2755ccc3
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-6-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 449d7f6d23adcddc405e62be84ecfbfc1f283085557f219a7498b461dfc7d769
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-7-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 483d04afeaca97d31617860de252a1acfeb487c3e16f465c0cae5ccda532d897
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/architecture-reviewer-P-8-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 7b8e4736faa149ae4fdf5c46ff17252ae9e427b458c92dbb51772b4d33f41e36
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-1-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: be099d72d99228c66f5222b71dc106f03a01052862a1cb5a52025bdae317f89a
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-2-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: ef1ea732b8a4b6ca6f5accfb74a1781c458e73eaa26de6a2081992669018c3b6
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-3-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: b8d5d9d95a963e6f1ef24a8545f78cb247da5672b7cb26ad46d6a29c45894629
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-4-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 46098a2e25c3f2434fdfded38a6b2349f8b7b69f6a0ca29f1562f92c02a12108
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-5-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: f6f522655a9d7b59f62ba52052b24ca2510d5ac5a765961df50493e7234e77b0
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-6-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 64f72c1b8bb8ea0f367626b45bfd0bd7ceff452fffde11e307c87a54f3851efa
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-7-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 64bb652c277e4117a5d1c5220a7fcb3d8808db10e758cc6f47a5fd56963747a5
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/code-reviewer-P-8-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 3aad96cd32f18de30414b9082cbd99285f8b254763aab0c5d6eb54428c2c753b
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/security-reviewer-P-1-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: bd40e5261021fa640cb88d48d05739ca7c93de0f32e59f4b9cb816ef169c61ad
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/security-reviewer-P-2-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 634940b9108b5b9333c4c367424a9fe7f9aef7966d371b94f0a24ff9874ec603
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/security-reviewer-P-3-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 5d3f2c8efa6dec5efab1d2a2a10247ede38316adbe8d2a3329af5b87848e8864
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/security-reviewer-P-4-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 73c6ecb7ac8d42494f5453947d5be8ae9a7ff0018bcd6b66e0144dec6429933d
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/security-reviewer-P-5-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 9cfd85b019e81e5181a2eebae2cd743275f3ebe02c0cfd4c539de70e872bab7b
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/security-reviewer-P-6-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 59c74745dd228d2509575b2e137c31018cbcce38bfd7927c5cfe71810c76a3b2
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/security-reviewer-P-7-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 0c0f4a6cad4e1acb2b105dca92d6f83e4999815e423a12e0868a2df9fb4d2b58
  - lines: 3-7
    path: docs/design/workflow-efficiency/reviews/security-reviewer-P-8-r1.yaml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 92301c709979eacf17c5b1b4a8d04850e40dbbf098764320bfee6e93841ceb07
- id: A-125
  kind: structure
  statement: Claude context points to AGENTS.md; generated Cursor/Claude workflow rules also include the
    baseline, while Codex role files define inventory and tracing instructions.
  evidence:
  - lines: 1-2
    path: .claude/CLAUDE.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 73186fd479d932144f4eec865b49c0e8cd2d05e3e5e2595246b27bacd9a77f3a
  - lines: 1-15
    path: .cursor/rules/orqlet-workflow.mdc
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 89df479b7f0d537dc1a5bfbf57f942a542214958d8a67395e8da8901f146efd8
  - lines: 1-12
    path: .claude/rules/orqlet-workflow.md
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 49706884b0514a0839858dcb548a5376618e5f9dd26d8d68af1d85346a3d3007
  - lines: 1-5
    path: .codex/agents/orqlet-inventory.toml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 4fcb2f0646c0cc40005317f5819177c4224aaef850a1eb05606bb09e6a177dab
  - lines: 1-5
    path: .codex/agents/orqlet-tracer.toml
    revision: 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
    sha256: 3334ca565b6d6469831738ccb7777d691c61b3a517a15e7aa9dbfcd8380bc31a
unknowns:
- id: U-1
  what: 'Historical question retained from the 2026-11-23 research: Whether each client loads a skill''s
    references when the skill starts or only when the text points to them, so the words loaded per run
    are unknown. Unless reassessed below, this refresh leaves its status unverified. Refresh: Current
    client-loading behavior remains unverified; word-count tests are static limits (A-95).'
  material: true
  merged_from:
  - inv-instructions/U-6
  - inv-instructions/U-1
  - refresh-workflow/U-4
  question_ref: Q-31
- id: U-2
  what: 'Historical question retained from the 2026-11-23 research: How the design skill resolves the
    research skill''s as-is-format.md in each client. Unless reassessed below, this refresh leaves its
    status unverified. Refresh: Also unresolved: whether context discovery expects root CLAUDE.md; only
    .claude/CLAUDE.md was present and points to AGENTS.md (A-125).'
  material: true
  merged_from:
  - inv-instructions/U-4
  - refresh-workflow/U-6
  question_ref: Q-31
- id: U-3
  what: 'Historical question retained from the 2026-11-23 research: Whether installed skill copies and
    per-client golden copies are byte-identical apart from the generated header and markers. Unless reassessed
    below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - inv-instructions/U-3
  - inv-docs-tests/U-3
  - refresh-workflow/U-5
  question_ref: Q-31
- id: U-4
  what: 'Historical question retained from the 2026-11-23 research: Whether the Codex role files and agents/openai.yaml
    files repeat the full role text. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - inv-instructions/U-5
  question_ref: Q-31
- id: U-5
  what: 'Historical question retained from the 2026-11-23 research: Whether the design, plan or review
    validators enforce any document length. Unless reassessed below, this refresh leaves its status unverified.
    Refresh: Partly resolved: current design/plan references set warning targets (A-94); actual review-document
    length enforcement is outside this refresh.'
  material: true
  merged_from:
  - inv-instructions/U-7
  question_ref: Q-31
- id: U-6
  what: 'Historical question retained from the 2026-11-23 research: How the ponytail skill''s reply rule
    interacts with the STOP messages of the Orqlet skills. Unless reassessed below, this refresh leaves
    its status unverified.'
  material: false
  merged_from:
  - inv-instructions/U-8
  question_ref: Q-31
- id: U-7
  what: 'Historical question retained from the 2026-11-23 research: Whether the nested /orqlet-review
    run repeats implement''s models resolve and standards work or reuses it. Unless reassessed below,
    this refresh leaves its status unverified. Refresh: Partly resolved: nested review skips skill model
    resolution (A-91); actual standards rereads remain unmeasured.'
  material: true
  merged_from:
  - inv-instructions/U-9
  question_ref: Q-31
- id: U-8
  what: 'Historical question retained from the 2026-11-23 research: Whether the design reviewers and the
    three code-phase reviewers run concurrently; no skill text says. Unless reassessed below, this refresh
    leaves its status unverified.'
  material: false
  merged_from:
  - inv-instructions/U-10
  - refresh-workflow/U-3
  question_ref: Q-31
- id: U-9
  what: 'Historical question retained from the 2026-11-23 research: Guidance for the main agent as Coder
    beyond the baseline, implement step 5 and the standards output; no coder role file exists. Unless
    reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - inv-instructions/U-11
  question_ref: Q-31
- id: U-10
  what: 'Historical question retained from the 2026-11-23 research: The machine count of distinct finding
    codes; a hand count gives 256 (165 E, 50 W, 35 I, 6 L). Unless reassessed below, this refresh leaves
    its status unverified.'
  material: false
  merged_from:
  - inv-checks/U-1
  question_ref: Q-31
- id: U-11
  what: 'Historical question retained from the 2026-11-23 research: Elapsed time and token usage of sessions,
    CLI invocations, git calls, pytest runs and CI jobs; none is recorded in the repository or the transcripts.
    Unless reassessed below, this refresh leaves its status unverified. Refresh: The old blanket absence
    of timing is superseded: eight claimed final suite durations are now recorded (A-98). Complete active/wait
    time, CLI/packet/Git costs, tokens and CI timings remain unknown. Q-3 was withdrawn; Q-30 now carries
    the remaining question.'
  material: true
  question_ref: Q-30
  merged_from:
  - inv-checks/U-4
  - inv-checks/U-10
  - refresh-workflow/U-1
  - refresh-validation/U-1
  - refresh-records/U-1
- id: U-12
  what: 'Historical question retained from the 2026-11-23 research: Whether explain''s compose path calls
    Git beyond constructing GitVcs. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - inv-checks/U-5
  question_ref: Q-31
- id: U-13
  what: 'Historical question retained from the 2026-11-23 research: Whether GitHub-hosted runners provide
    Python 3.15 for the CI matrix. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - inv-checks/U-7
  question_ref: Q-31
- id: U-14
  what: 'Historical question retained from the 2026-11-23 research: How agents treat exit status 5 when
    gate status is NOT_RUN only because of ORQ-I393. Unless reassessed below, this refresh leaves its
    status unverified. Refresh: The old unconditional offline-approval NOT_RUN behavior is superseded
    (A-110); actual handling of other NOT_RUN causes remains unknown.'
  material: true
  merged_from:
  - inv-checks/U-9
  question_ref: Q-31
- id: U-15
  what: 'Historical question retained from the 2026-11-23 research: The Cursor model ids of the policy''s
    starting candidates (frozen Q-35 of dynamic-model-profiles). Unless reassessed below, this refresh
    leaves its status unverified.'
  material: true
  merged_from:
  - inv-models/U-3
  question_ref: Q-31
- id: U-16
  what: 'Historical question retained from the 2026-11-23 research: Whether any CI check turns a NOT_RUN
    gated review into a blocked merge (frozen Q-36). Unless reassessed below, this refresh leaves its
    status unverified.'
  material: true
  merged_from:
  - inv-models/U-4
  question_ref: Q-31
- id: U-17
  what: 'Historical question retained from the 2026-11-23 research: Whether a model family means the vendor
    or the model line (frozen Q-38). Unless reassessed below, this refresh leaves its status unverified.'
  material: true
  merged_from:
  - inv-models/U-5
  question_ref: Q-31
- id: U-18
  what: 'Historical question retained from the 2026-11-23 research: Which clients report the running model
    to an agent; no review record holds an observed identity. Unless reassessed below, this refresh leaves
    its status unverified.'
  material: true
  merged_from:
  - inv-models/U-6
  question_ref: Q-31
- id: U-19
  what: 'Historical question retained from the 2026-11-23 research: Who fills the model fields of a review
    record; one record says the Coder wrote it from the returned text. Unless reassessed below, this refresh
    leaves its status unverified.'
  material: true
  merged_from:
  - inv-models/U-7
  question_ref: Q-31
- id: U-20
  what: 'Historical question retained from the 2026-11-23 research: Whether .orqlet/model-policy.yaml
    equals its packaged seed. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - inv-models/U-9
  question_ref: Q-31
- id: U-21
  what: 'Historical question retained from the 2026-11-23 research: Whether the coder reruns every plan
    check after a rework round; the rework step names only the knowledge step, the tester''s record and
    the review. Unless reassessed below, this refresh leaves its status unverified. Refresh: Current instructions
    require a full run before review and per rework round (A-88); whether every recent run obeyed reuse
    conditions is unknown.'
  material: true
  merged_from:
  - trace-checks/U-1
  - refresh-workflow/U-2
  question_ref: Q-31
- id: U-22
  what: 'Historical question retained from the 2026-11-23 research: Whether sources shared by several
    checks are re-cited once per check. Unless reassessed below, this refresh leaves its status unverified.
    Refresh: Current text says cite sources once per phase (A-88/A-89); observed adherence is unknown.'
  material: true
  merged_from:
  - trace-checks/U-2
  question_ref: Q-31
- id: U-23
  what: 'Historical question retained from the 2026-11-23 research: Which pytest run the tester''s record
    reports. Unless reassessed below, this refresh leaves its status unverified. Refresh: Current records
    identify the retained final run; earlier executions are incompletely retained (A-98/A-99).'
  material: true
  merged_from:
  - trace-checks/U-3
  question_ref: Q-31
- id: U-24
  what: 'Historical question retained from the 2026-11-23 research: Which session showed the reported
    five or six repetitions of checks. Unless reassessed below, this refresh leaves its status unverified.'
  material: true
  question_ref: Q-9
  merged_from:
  - trace-checks/U-4
- id: U-25
  what: 'Historical question retained from the 2026-11-23 research: Check counts per plan phase; the transcripts
    do not mark phase boundaries. Unless reassessed below, this refresh leaves its status unverified.'
  material: true
  merged_from:
  - trace-checks/U-5
  question_ref: Q-31
- id: U-26
  what: 'Historical question retained from the 2026-11-23 research: Which Python versions local check
    runs use. Unless reassessed below, this refresh leaves its status unverified. Refresh: The eight retained
    final summaries name Python 3.12.11 (A-98); other local runs were not reconstructed.'
  material: true
  merged_from:
  - trace-checks/U-6
  question_ref: Q-31
- id: U-27
  what: 'Historical question retained from the 2026-11-23 research: How many packet files each reviewer
    reads. Unless reassessed below, this refresh leaves its status unverified.'
  material: true
  merged_from:
  - trace-checks/U-7
  - refresh-validation/U-2
  question_ref: Q-31
- id: U-28
  what: 'Historical question retained from the 2026-11-23 research: Whether implement''s input check also
    runs validate as-is. Unless reassessed below, this refresh leaves its status unverified. Refresh:
    The current implementation input text names plan and design (A-91); actual additional calls were not
    reconstructed.'
  material: false
  merged_from:
  - trace-checks/U-8
  question_ref: Q-31
- id: U-29
  what: 'Historical question retained from the 2026-11-23 research: How many Git processes diff_patch
    starts. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - trace-checks/U-9
  question_ref: Q-31
- id: U-30
  what: 'Historical question retained from the 2026-11-23 research: Whether anything removes old review
    packets from the data directory. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - trace-checks/U-10
  question_ref: Q-31
- id: U-31
  what: 'Historical question retained from the 2026-11-23 research: Whether the edits between reruns changed
    each rerun check''s inputs. Unless reassessed below, this refresh leaves its status unverified.'
  material: true
  merged_from:
  - trace-checks/U-11
  - refresh-validation/U-3
  question_ref: Q-31
- id: U-32
  what: 'Historical question retained from the 2026-11-23 research: Unused functions, classes and constants
    inside used modules; only module-level references were checked. Unless reassessed below, this refresh
    leaves its status unverified.'
  material: true
  merged_from:
  - inv-docs-tests/U-4
  question_ref: Q-31
- id: U-33
  what: 'Historical question retained from the 2026-11-23 research: How far fragment files repeat their
    AS-IS file; one repeat is verified, and three tasks hold 3,316 to 5,690 fragment lines. Unless reassessed
    below, this refresh leaves its status unverified.'
  material: true
  merged_from:
  - inv-docs-tests/U-5
  question_ref: Q-31
- id: U-34
  what: 'Historical question retained from the 2026-11-23 research: Whether copilot.py, render_rich.py,
    user_scope.py and the user-render tests are obsolete or frozen work in progress. Unless reassessed
    below, this refresh leaves its status unverified. Refresh: Answered by Q-10: the named files remain
    frozen work, not authorized removals. Retained for history.'
  material: false
  question_ref: Q-10
  merged_from:
  - inv-docs-tests/U-6
- id: U-35
  what: 'Historical question retained from the 2026-11-23 research: The collected test count after parametrisation;
    4,243 test functions are defined. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - inv-docs-tests/U-7
  question_ref: Q-31
- id: U-36
  what: 'Historical question retained from the 2026-11-23 research: The phase and acceptance-criteria
    counts of the harness2-fit plan. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  merged_from:
  - inv-docs-tests/U-8
  question_ref: Q-31
- id: U-37
  what: 'Historical question retained from the 2026-11-23 research: Whether other tests import names missing
    from src. Unless reassessed below, this refresh leaves its status unverified.'
  material: true
  merged_from:
  - inv-docs-tests/U-9
  question_ref: Q-31
- id: U-38
  what: 'Historical question retained from the 2026-11-23 research: The size of tool results per Orqlet
    command; transcripts store no tool results. Unless reassessed below, this refresh leaves its status
    unverified.'
  material: true
  question_ref: Q-31
- id: U-39
  what: 'Historical question retained from the 2026-11-23 research: Usage reporting and Mermaid rendering
    in Codex and Copilot were not looked up. Unless reassessed below, this refresh leaves its status unverified.'
  material: false
  question_ref: Q-31
- id: U-40
  what: 'Historical question retained from the 2026-11-23 research: How Copilot behaves for this project;
    the profile does not enable it, so no Copilot files are generated here. Unless reassessed below, this
    refresh leaves its status unverified.'
  material: false
  question_ref: Q-31
- id: U-41
  what: 'Historical question retained from the 2026-11-23 research: Whether the CLI version 0.4.0 next
    to workflow 0.5.0 is intended. Unless reassessed below, this refresh leaves its status unverified.
    Refresh: Answered by Q-11; repository CLI/workflow now both declare 0.5.1 (A-121). The older executable
    on PATH is a separate local observation in self_check.'
  material: false
  question_ref: Q-11
- id: U-42
  what: 'Historical question retained from the 2026-11-23 research: The job results of main''s required
    checks; CI run 45152031442 of 92e026e is on GitHub, outside the base revision. Unless reassessed below,
    this refresh leaves its status unverified. Refresh: Current remote CI runs were not read; retained
    local test records do not prove hosted CI outcomes (A-107/A-98).'
  material: true
  question_ref: Q-19
  merged_from:
  - refresh-records/U-3
- id: U-43
  what: 'Historical question retained from the 2026-11-23 research: Which file or ruff rule fails the
    lint job; the missing names explain mypy and pytest only. Unless reassessed below, this refresh leaves
    its status unverified. Refresh: Retained P-7/P-8 summaries now identify the three frozen-file lint
    errors as import order and one long line (A-100); live CI results remain unverified.'
  material: true
  question_ref: Q-31
- id: U-44
  what: 'Historical question retained from the 2026-11-23 research: Whether the architecture and build
    jobs read tests/; lint-imports names the orqlet package only. Unless reassessed below, this refresh
    leaves its status unverified.'
  material: false
  question_ref: Q-31
- id: U-45
  what: 'Historical question retained from the 2026-11-23 research: Whether Cursor and Claude Code show
    a generated rule file''s body to the person. Unless reassessed below, this refresh leaves its status
    unverified.'
  material: true
  merged_from:
  - inv-rule-ids/U-3
  question_ref: Q-31
- id: U-46
  what: 'Historical question retained from the 2026-11-23 research: Whether a client shows the human output
    of standards for and explain to the person or only to the agent. Unless reassessed below, this refresh
    leaves its status unverified.'
  material: true
  merged_from:
  - inv-rule-ids/U-4
  question_ref: Q-31
- id: U-47
  what: 'Historical question retained from the 2026-11-23 research: Whether the review report to the person
    includes a finding''s optional rule_ref. Unless reassessed below, this refresh leaves its status unverified.'
  material: true
  merged_from:
  - inv-rule-ids/U-5
  question_ref: Q-31
- id: U-48
  what: Total duration of all initial, targeted, failed and rework test runs is unknown; A-98 totals only
    eight retained final runs.
  material: true
  question_ref: Q-30
  merged_from:
  - refresh-records/U-2
- id: U-49
  what: Observed end-to-end or execution-count improvement from 0.5.1 on an equivalent later task is unmeasured
    (A-108).
  material: true
  question_ref: Q-30
  merged_from:
  - refresh-records/U-4
- id: U-50
  what: Complete earlier P-7/P-8 reviewer outputs and packet bindings are unavailable; retained records
    explicitly describe their loss (A-102).
  material: true
  question_ref: Q-30
  merged_from:
  - refresh-records/U-5
- id: U-51
  what: Which individual tests dominate the recorded 26-37 minute suites is unknown; no per-test duration
    breakdown was found in the inspected records.
  material: true
  question_ref: Q-30
  merged_from:
  - refresh-records/U-6
- id: U-52
  what: Whether earlier development sessions invoked the globally installed 0.4.0 CLI rather than the
    repository 0.5.1 CLI, and the time impact if so, is unknown; see the local observation in self_check.
  material: true
  question_ref: Q-30
contradictions:
- id: C-1
  sources:
  - README.md:332
  - src/orqlet/workflow/skills/orqlet-review/skill.md:7
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    README says orqlet-review starts the architecture and security reviews; the skill starts three reviewers,
    including the Code Reviewer. Its source line numbers describe that baseline; it is not asserted as
    a current defect without reassessment.'
  merged_from:
  - inv-instructions/C-1
- id: C-2
  sources:
  - README.md:357
  - src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md:86
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    README runs standards for with --phase implement --role tester; the contract maps implement to --phase
    implementation --role coder. Its source line numbers describe that baseline; it is not asserted as
    a current defect without reassessment.'
  merged_from:
  - inv-instructions/C-2
- id: C-3
  sources:
  - src/orqlet/workflow/skills/orqlet-implement/skill.md:7
  - src/orqlet/workflow/skills/orqlet-plan/references/plan-format.md:73
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    Implement says three reviewers work in every phase; plan-format requires the code reviewer only from
    workflow 0.5.0. Its source line numbers describe that baseline; it is not asserted as a current defect
    without reassessment.'
  merged_from:
  - inv-instructions/C-3
- id: C-4
  sources:
  - src/orqlet/interface/cli/exit_codes.py:12
  - src/orqlet/interface/cli/commands/validate.py:40-49
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The exit-code comment says doctor or sync found an error; validators also use exit 5 for NOT_RUN.
    Its source line numbers describe that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - inv-checks/C-1
- id: C-5
  sources:
  - src/orqlet/interface/cli/runner.py:25
  - src/orqlet/interface/cli/commands/lifecycle.py:251-270
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    echo_findings is meant to be False when the text lists the findings; explain lists them and leaves
    it True. Its source line numbers describe that baseline; it is not asserted as a current defect without
    reassessment.'
  merged_from:
  - inv-checks/C-2
- id: C-6
  sources:
  - src/orqlet/interface/cli/render_rich.py:1-5
  - src/orqlet/interface/cli/app.py:39-57
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    render_rich presents output for install and uninstall; the CLI registers neither command. Its source
    line numbers describe that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - inv-checks/C-3
  - inv-docs-tests/C-5
- id: C-7
  sources:
  - src/orqlet/application/usecases/gate_status.py:116-123
  - src/orqlet/workflow/skills/orqlet-plan/skill.md:28
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The skill says a NOT_RUN caused by ORQ-I393 alone is not a failure; the CLI exits 5 for it, the failed-check
    code. Its source line numbers describe that baseline; it is not asserted as a current defect without
    reassessment. Refresh: unconditional offline-approval NOT_RUN is resolved in current code (A-110).'
  merged_from:
  - inv-checks/C-4
- id: C-8
  sources:
  - docs/design/dynamic-model-profiles/design/component.md:167
  - src/orqlet/application/usecases/model_selection.py:357-364
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The design says unnamed Cursor routes are missing-candidate; the code checks that only in manual modes,
    and the policy uses automatic. Its source line numbers describe that baseline; it is not asserted
    as a current defect without reassessment.'
  merged_from:
  - inv-models/C-1
- id: C-9
  sources:
  - src/orqlet/workflow/skills/orqlet-review/skill.md:28
  - src/orqlet/domain/model_resolution.py:480-481
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The review skill matches the coder among printed candidates; every model is proposed, so none is printed.
    Its source line numbers describe that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - inv-models/C-2
- id: C-10
  sources:
  - src/orqlet/application/usecases/models_resolve.py:22-23
  - .orqlet/model-policy.yaml:258-262
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    A docstring says orqlet-code-reviewer is not yet a workflow role; the role file exists and the policy
    assigns it. Its source line numbers describe that baseline; it is not asserted as a current defect
    without reassessment.'
  merged_from:
  - inv-models/C-3
- id: C-11
  sources:
  - src/orqlet/application/contracts/model_policy.py:3-4
  - src/orqlet/application/usecases/models_resolve.py:143-155
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The contract docstring says no use case reads the policy; three use cases load it. Its source line
    numbers describe that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - inv-models/C-4
- id: C-12
  sources:
  - src/orqlet/workflow/skills/orqlet-review/references/review-format.md:67
  - .orqlet/role-bindings.yaml:1-27
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The format requires an approved binding for the role; code-reviewer records name a binding that role-bindings.yaml
    lacks. Its source line numbers describe that baseline; it is not asserted as a current defect without
    reassessment.'
  merged_from:
  - inv-models/C-5
- id: C-13
  sources:
  - src/orqlet/workflow/skills/orqlet-plan/references/plan-format.md:71
  - src/orqlet/application/usecases/validate_plan.py:41
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The format allows a reviewer role as check_ref; the validator''s list omits code-reviewer. Its source
    line numbers describe that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - trace-checks/C-1
- id: C-14
  sources:
  - tests/unit/test_workflow_skill_contracts.py:577-578
  - src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md:41-44
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The test cites gate status --phase before the validators; the contract runs gate status, then the
    validator, then git checks, and implement runs --phase after them. Its source line numbers describe
    that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - trace-checks/C-2
- id: C-15
  sources:
  - AGENTS.md:85
  - AGENTS.md:47-75
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The required checks include architecture and build; the recorded commands hold no lint-imports and
    no build step. Its source line numbers describe that baseline; it is not asserted as a current defect
    without reassessment.'
  merged_from:
  - trace-checks/C-3
- id: C-16
  sources:
  - docs/design/dynamic-model-profiles/design/manifest.yaml:186
  - docs/design/dynamic-model-profiles/plan.yaml:2540-2541
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The manifest self-check names BC-1 to BC-42; the plan says the design holds BC-1 to BC-45. Its source
    line numbers describe that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - inv-docs-tests/C-1
- id: C-17
  sources:
  - tests/unit/render/test_user_scope_render.py:78-86
  - src/orqlet/application/ports/instruction_adapter.py:114-125
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The committed test uses RenderScope and RenderRequest.scope; neither exists in src. Its source line
    numbers describe that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - inv-docs-tests/C-2
- id: C-18
  sources:
  - tests/unit/render/test_user_scope_render.py:525-542
  - tests/conftest.py:85-86
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The test compares with golden family user-2026-11, which has no files; the fixture fails on a missing
    golden file. Its source line numbers describe that baseline; it is not asserted as a current defect
    without reassessment.'
  merged_from:
  - inv-docs-tests/C-3
- id: C-19
  sources:
  - docs/design/dynamic-model-profiles/plan.yaml:5
  - docs/design/dynamic-model-profiles/reviews/architecture-reviewer-P-14-r3.yaml:1-157
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    Four plan headers say status draft while phase review records up to P-14 exist. Its source line numbers
    describe that baseline; it is not asserted as a current defect without reassessment.'
  merged_from:
  - inv-docs-tests/C-4
- id: C-20
  sources:
  - docs/design/workflow-efficiency/questions.yaml:83-102
  - .orqlet/project-profile.yaml:162-166
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The research scope covers four clients; the project enables three, without Copilot. Its source line
    numbers describe that baseline; it is not asserted as a current defect without reassessment.'
- id: C-21
  sources:
  - src/orqlet/__init__.py:3
  - src/orqlet/workflow/MANIFEST.json:386
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    The CLI reports version 0.4.0; the packaged workflow is 0.5.0. Its source line numbers describe that
    baseline; it is not asserted as a current defect without reassessment. Refresh: repository versions
    now agree at 0.5.1 (A-121); the global executable remains a separate installation.'
- id: C-22
  sources:
  - docs/design/workflow-efficiency/questions.yaml:123-143
  - src/orqlet/application/usecases/validate_as_is.py:153-162
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    Q-7 set the budget for the research brief; the validator applies size_budget to fact statements only.
    Its source line numbers describe that baseline; it is not asserted as a current defect without reassessment.'
- id: C-23
  sources:
  - src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md:46
  - AGENTS.md:84
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    Same project reads a base_revision that is not an ancestor of HEAD as another repository or an unpublished
    branch; under squash merges a merged research-branch commit is not an ancestor of main either (Q-12).
    Its source line numbers describe that baseline; it is not asserted as a current defect without reassessment.
    Refresh: early header binding and task-owned evidence handling mitigate the documented case (A-92/A-119);
    ancestor checking still exists.'
  merged_from:
  - trace-binding/C-1
- id: C-24
  sources:
  - .prompts/rules.yaml:141-147
  - docs/design/workflow-efficiency/questions.yaml:266-293
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    ORQLET-QA-001 requires all checks to pass before a pull request is ready; Q-14 leaves main red and
    has this task''s pull requests report the failures as known. Its source line numbers describe that
    baseline; it is not asserted as a current defect without reassessment.'
- id: C-25
  sources:
  - .prompts/rules.yaml:141-147
  - .github/workflows/ci.yml:30-47
  note: 'Historical finding retained from the earlier research at a29b0ba67ffdeee713c302ce9f633cd3b648da64:
    ORQLET-QA-001 names every supported Python version; the lint and types jobs run on Python 3.12 only.
    Its source line numbers describe that baseline; it is not asserted as a current defect without reassessment.'
- id: C-26
  sources:
  - docs/design/workflow-efficiency/as-is.md@9d2053314ff32f459fdb17cb0f476bb0315e2e3c:A-27
  - src/orqlet/application/usecases/gate_status.py:118-123
  note: The prior research said gate status always returned NOT_RUN; current code allows PASS. Superseded
    historical claim, corrected by this refresh.
  merged_from:
  - refresh-validation/C-1
- id: C-27
  sources:
  - docs/design/workflow-efficiency/as-is.md@9d2053314ff32f459fdb17cb0f476bb0315e2e3c:A-26
  - src/orqlet/interface/cli/commands/evidence.py:21-48
  note: The prior research said citation accepted one pair; current CLI accepts multiple pairs. Superseded
    historical claim, corrected by this refresh.
  merged_from:
  - refresh-validation/C-2
- id: C-28
  sources:
  - docs/design/workflow-efficiency/as-is.md@9d2053314ff32f459fdb17cb0f476bb0315e2e3c:A-71
  - src/orqlet/application/usecases/validate_as_is.py:164-195
  note: The prior research required every citation at base_revision; current code exempts checked task
    evidence. Superseded historical claim, corrected by this refresh.
  merged_from:
  - refresh-validation/C-3
- id: C-29
  sources:
  - docs/design/workflow-efficiency/reviews/architecture-reviewer-P-7-r1.yaml:5
  - docs/design/workflow-efficiency/reviews/architecture-reviewer-P-7-r1.yaml:47-53
  - docs/design/workflow-efficiency/reviews/code-reviewer-P-8-r1.yaml:5
  - docs/design/workflow-efficiency/reviews/code-reviewer-P-8-r1.yaml:54-56
  note: Stored round-1 values describe third/second session rounds; the records explain that earlier evidence
    was not retained.
  merged_from:
  - refresh-records/C-1
self_check:
  schema: orqlet.self-check/v1
  checked_against:
    role: researcher
    phase: research
    confirmed_requirements:
    - Q-1
    - Q-5
    - Q-6
    - Q-7
    - Q-10
    - Q-28
    - Q-29
    applicable_standards:
    - 'src/orqlet/**: 88e3e089ba38309c8acd8084933e2b62fc9109d1d8430c54e72f355cdff0c57d'
    - 'tests/**: bf7e3320dfee207b9f60f217769bde90b959d4bf5a5c43419c356dea8aab62ed'
    - 'docs/design/**: 9943630aa1feabdb4265d49265f94ba8a08d73e9eb347af3e4597d550da41b34'
    - 'remaining context scopes: 7cedb45ea31f8900517dcaca99243b1d35b05b37792a98fd1c45d16b2bf75038'
    evidence:
    - docs/design/workflow-efficiency/fragments/refresh-workflow.yaml
    - docs/design/workflow-efficiency/fragments/refresh-records.yaml
    - docs/design/workflow-efficiency/fragments/refresh-validation.yaml
    - docs/design/workflow-efficiency/fragments/refresh-context.yaml
  checks:
  - what: Refresh authorized; previous acceptance removed
    how: 'The user confirmed: Yes, investigate why developing Orqlet itself takes too long and refresh
      workflow-efficiency research. Investigate recent work generally, including repeated checks, reviews,
      approvals and rework. Q-28/Q-29 record the answers; the refresh returned this file to draft and
      removed the earlier acceptance entry.'
    result: pass
  - what: Prior artifact input and staleness
    how: Prior validate as-is passed (84 facts, 47 unknowns, 25 contradictions); ancestor check for a29b0ba
      exited 0. Gate status returned NOT_RUN for workflow/protected-set/base changes. Git history identified
      P-1 through P-8 and plan amendments; user explicitly authorized refresh rather than continuation
      on stale inputs.
    result: pass
  - what: Current source and bound values
    how: Repository .venv/bin/orqlet --version returned 0.5.1; gate status --json bound HEAD 9d2053314ff32f459fdb17cb0f476bb0315e2e3c
      before any commit. All fact citations were regenerated at that revision with evidence cite, batching
      ranges.
    result: pass
  - what: Local executable mismatch
    how: command -v orqlet returned /Users/tmishari/.local/bin/orqlet, whose launcher uses /Users/tmishari/.local/share/uv/tools/orqlet/bin/python3.
      Its JSON reported orqlet_version 0.4.0 and old output. Repository .venv/bin/orqlet reported 0.5.1
      and the new model suggestion. No installation was modified; subsequent validation uses .venv/bin/orqlet.
    result: pass
  - what: Recent counts and claimed durations
    how: Read committed P-1 through P-8 test YAML; decimal sum of pytest summaries is 14460.78 seconds.
      Counted 24 committed implementation reviewer records, each advisory/NOT_RUN. These checks verify
      records, not executions.
    result: pass
  - what: Preservation and provenance
    how: All previous U-1 through U-47 and C-1 through C-25 are retained with explicit historical status.
      All new fragment unknowns/contradictions are merged_from referenced. Source facts replace superseded
      A-1 through A-84, which remain in git history; new IDs begin at A-85. An assert-based read-only
      comparison confirmed all original unknown/contradiction text remains and the original 27 ledger
      entries are byte-value equivalent after YAML parsing; eight phases contain 51 planned check entries.
    result: pass
  - what: Resources and technology coverage
    how: resources list --uncovered --json returned no resources and listed Typer, Python, Pydantic and
      uv. This refresh examines repository configuration, instructions and records; it makes no new vendor/API
      claims. No outside lookup was needed for those local facts.
    result: pass
  - what: Project tests, build and hosted CI
    how: Not run in this research phase. Existing test summaries are explicitly treated as claimed evidence;
      CI is configuration only.
    result: not-run
  - what: Independent research
    how: Two inventory agents and one behavior tracer worked in parallel; parent added context/count facts.
      Fragments retain source ranges and all reported unknowns/contradictions. No independent implementation
      review is claimed.
    result: pass
  - what: Final artifact validation
    how: .venv/bin/orqlet validate as-is docs/design/workflow-efficiency/as-is.md --fragments docs/design/workflow-efficiency/fragments
      --against HEAD passed after the alias correction; ledger validation passed. Final rerun checks this
      recorded result and the wording correction.
    result: pass
  - what: Synthesis serialization correction
    how: Initial validation rejected a YAML alias introduced when shared citation objects were serialized.
      Rewrote fragments with aliases disabled; removed two ambiguous prose words flagged by the advice
      detector, without changing claims.
    result: pass
  - what: The person accepted the refreshed research
    how: >-
      tmishari, recorded 2026-11-25T08:50:28+00:00 in this chat:
      "I accept the refreshed workflow-efficiency research. Record the approval and continue to design
      changes that reduce development time."
      This approves the research and requests the design phase; it does not approve a new design,
      plan or implementation.
    result: pass
  unverified:
  - Timing is incomplete and claimed; no percentage of end-to-end time or critical-path duration can be
    assigned.
  - Current global CLI mismatch is observed locally, not proof that earlier sessions used it.
  - Existing uncommitted P-8 knowledge/r2 review records were preserved and excluded from base-bound facts.
  - No current remote branch/CI approval state was fetched; git history is local evidence.
  - Historical unknowns and contradictions outside this focused refresh remain explicitly historical,
    not silently resolved.
  - Q-28/Q-29 times record when answers were entered, not measured user response latency.
  - 'Source provenance: A-85 <- refresh-workflow/A-1; A-86 <- refresh-workflow/A-2; A-87 <- refresh-workflow/A-3;
    A-88 <- refresh-workflow/A-4; A-89 <- refresh-workflow/A-5; A-90 <- refresh-workflow/A-6; A-91 <-
    refresh-workflow/A-7; A-92 <- refresh-workflow/A-8; A-93 <- refresh-workflow/A-9; A-94 <- refresh-workflow/A-10;
    A-95 <- refresh-workflow/A-11; A-96 <- refresh-workflow/A-12; A-97 <- refresh-records/A-1; A-98 <-
    refresh-records/A-2; A-99 <- refresh-records/A-3; A-100 <- refresh-records/A-4; A-101 <- refresh-records/A-5;
    A-102 <- refresh-records/A-6; A-103 <- refresh-records/A-7; A-104 <- refresh-records/A-8; A-105 <-
    refresh-records/A-9; A-106 <- refresh-records/A-10; A-107 <- refresh-records/A-11; A-108 <- refresh-records/A-12;
    A-109 <- refresh-records/A-13; A-110 <- refresh-validation/A-2; A-111 <- refresh-validation/A-3; A-112
    <- refresh-validation/A-4; A-113 <- refresh-validation/A-5; A-114 <- refresh-validation/A-6; A-115
    <- refresh-validation/A-7; A-116 <- refresh-validation/A-8; A-117 <- refresh-validation/A-9; A-118
    <- refresh-validation/A-10; A-119 <- refresh-validation/A-11; A-120 <- refresh-context/A-1; A-121
    <- refresh-context/A-2; A-122 <- refresh-context/A-3; A-123 <- refresh-context/A-4; A-124 <- refresh-context/A-5;
    A-125 <- refresh-context/A-6'
  questions:
  - Q-30
  - Q-31
---

# workflow-efficiency: current development-time research

## Request

Investigate why developing Orqlet itself takes too long, including repeated checks, reviews, approvals and rework; refresh the research using recent work generally (Q-28, Q-29). The phase/review structure and recent records provide the evidence (A-85–A-125).

## Scope

This refresh covers the current source at `9d2053314ff32f459fdb17cb0f476bb0315e2e3c`, workflow-efficiency P-1–P-8 records, its design reviews and ledger, workflow instructions, validation paths and CI configuration. The project is a Python CLI, with three enabled clients and repository-owned standards (A-120, A-125). Earlier frozen work stays frozen (A-85). The historical transcript summary is context only; it predates these changes and cannot establish their effect (A-108, A-122).

No tests, benchmarks, new raw-transcript survey or hosted CI inspection ran. Retained summaries are evidence of what was recorded, not independently reproduced results (A-98, A-107). Existing uncommitted P-8 records were excluded from base-bound facts; `self_check` records the locally observed global/repository CLI mismatch (A-121).

## Existing capabilities and behaviour

**The measurable part is expensive full-suite verification.** Eight retained final runs total **241.013 minutes (4 hours 1 minute)**. They are local Python 3.12.11 runs, labeled `claimed`; they do not include all prior, targeted or CI executions (A-98).

| Phase | Retained final pytest seconds | Minutes |
|---|---:|---:|
| P-1 | 1569.82 | 26.16 |
| P-2 | 1656.32 | 27.61 |
| P-3 | 1962.19 | 32.70 |
| P-4 | 2221.34 | 37.02 |
| P-5 | 1741.46 | 29.02 |
| P-6 | 1705.24 | 28.42 |
| P-7 | 1758.03 | 29.30 |
| P-8 | 1846.38 | 30.77 |
| Total | 14460.78 | 241.01 |

All values above derive from A-98. P-7 alone records three full runs; the first two durations are missing. Its golden files were regenerated each round (A-99). P-4/P-5 record concrete test rework, including oversized fixture text and an incorrect output expectation (A-105).

**The workflow multiplies work by phase and rework round.** Eight phases specify 51 check-list entries (requirements, not 51 measured executions). Every phase includes a tester, coder, three reviewers, knowledge records and a human acceptance point (A-86, A-87, A-97, A-109). The following is the current prescribed loop, as implemented (A-87–A-90):

```mermaid
flowchart LR
    T[Phase tests and implementation] --> F[Full checks]
    F --> E[Knowledge and test records]
    E --> R[Three reviewers]
    R -->|Code or test rework| T
    R --> H[Human acceptance]
    H --> N[Next phase]
```

**Review work does not always produce an independently passing gate.** All 24 retained implementation reviewer records say advisory/NOT_RUN. P-8 code review explicitly cites missing approved binding and unknown models; useful reviewer conclusions and a successful independence gate are different recorded outcomes (A-101, A-124). P-7/P-8 filenames say round 1 while their notes describe actual third/second rounds because earlier evidence was lost (A-102, C-29). The design had an authorized fourth round, followed by human review instead of a fifth agent round (A-103).

**Review also found substantive gaps.** The first design security review led to accepted changes in dependency watching, task-name handling, negative tests and evidence boundaries. The record therefore does not support treating every review round as wasted work (A-104). P-7 fixed incorrect instructions; P-8 fixed stale README versions (A-102).

**Approval and document maintenance recur inside delivery.** The contract still requires human merge references and stale-input classification. P-4/P-5/P-7 explicitly record confirmations after earlier task commits made inputs stale (A-92, A-106, A-111, A-112). Q-12/Q-13 document research refreshes during design; newly discovered facts can send design back to research, and out-of-list files require plan amendments (A-86, A-93, A-123).

**Source text has several coupled representations.** Four phase-contract sources, eight installed copies, golden fixtures and wording/placement tests participate in changes. Generated files come from their sources (A-95, A-96). Review preparation exports broad context and recomputes bindings; record validation repeats component work, and evidence-record edits can invalidate reviews without invalidating test bindings. Their time cost is unmeasured (A-113–A-117).

**Known failures remain in the verification path.** P-7/P-8 carry the frozen-file lint, type and collection errors, despite over 14,000 passing tests; their overall test records remain NOT_RUN (A-100). CI configures twelve test combinations per applicable event, without path filters and with setup-uv caching disabled. Matrix size is neither actual execution count nor serial elapsed time (A-107).

**Several earlier problems are already addressed.** Current text reuses citations, permits targeted iteration, limits full runs to pre-review/rework rounds, skips nested model resolution and conditionally reuses validators. It binds research early for squash merges. Current code batches citations, allows checked task-owned evidence and permits a current gate to PASS (A-88, A-89, A-91, A-92, A-110, A-118, A-119). The plan explicitly leaves observed before/after change to a later equivalent task (A-108).

## Inferences

- I-1 Repeated full verification is a substantial recorded development cost: eight final suites alone sum to about four hours, and rework adds runs (A-88, A-98, A-99). Complete run logs would confirm total cost and whether runs overlapped other work.
- I-2 Phase boundaries, human confirmations and invalidation loops plausibly add delay beyond coding (A-86, A-87, A-92, A-106, A-111). Session timestamps separating active work from waiting would quantify that contribution.
- I-3 Lost review evidence makes retained round counts understate actual review work and complicates audit/reuse (A-102, C-29). Earlier packet and reviewer logs would establish the full sequence; their absence is recorded.
- I-4 Text/fixture coupling contributes to rework: wording/version findings and regenerated copies appear in the same recent delivery (A-95, A-96, A-99, A-102, A-105). Per-edit traces would establish how much rework was necessary versus avoidable.
- I-5 Advisory reviews with insufficient independence and carried baseline failures leave manual interpretation work even after checks run (A-100, A-101, A-124). Approval discussions would establish the time spent interpreting these results.
- I-6 Packet export and repeated binding computation are plausible secondary costs, but their relative importance is unmeasured (A-113–A-117). Per-command profiles would test that inference; this research does not rank them above recorded test costs.

## Open questions

The front matter preserves **52 uncertainty records and 29 contradiction records**, including historical questions now partly answered and findings superseded by 0.5.1. These counts are not 52 newly discovered unknowns or 29 current defects. U-1–U-47 and C-1–C-25 retain their prior wording and reassessment status; C-26–C-28 identify historical claims corrected by current code, and C-29 identifies the review-round discrepancy (A-102, A-110, A-118, A-119).

Q-30 groups the remaining measurement questions: active versus waiting time and packet costs (U-11), rerun eligibility (U-21/U-31), reviewer reads (U-27), CI runs (U-42), total omitted test time (U-48), observed effect (U-49), missing review evidence (U-50), slow individual tests (U-51) and earlier CLI invocation choice (U-52). Q-31 tracks inherited questions not resolved by this narrower refresh; the original specific question references remain where available. These evidence gaps prevent percentage attribution or a verified end-to-end speedup claim (A-98, A-102, A-107, A-108).

## Inputs for design

The refreshed facts cover workflow requirements (A-85–A-96), recent execution/review records and CI configuration (A-97–A-109), current validation behavior (A-110–A-119), and project/history context (A-120–A-125). Q-28/Q-29 authorize this refresh. The person accepted the refreshed research and requested design work on 2026-11-25; the acceptance is recorded in self_check and the artifact is approved. Design, plan and implementation approvals remain separate. All retained uncertainty and contradiction records remain available to design; no remedy is selected here.
