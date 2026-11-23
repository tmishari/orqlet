---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: workflow-efficiency
  status: approved
  workflow_version: 0.5.0
  protected_set_digest: 20ba901af0832f59a7fef20323128b6d8a53d5e76ea45a64a6a5e7123816630a
  bound:
    base_revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    standards_lock_hash: 12486d9b48af8b2f61117d556568d3482b1641cd606e8652965dcc44babce930
    applicable_rules_hash: e5618439f62ec2b01a2a1719ee3902a92ca1829827de0b41242cb351c37e4e15
    profile_version: 1
base_revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
scope:
  paths:
  - src/orqlet/**
  - tests/**
  - .prompts/**
  - docs/design/*.md
  - docs/design/dynamic-model-profiles/**
  - docs/design/go-migration-feasibility/**
  - docs/design/harness2-fit/**
  - docs/design/mcp-or-plugins/**
  - docs/design/one-command-setup/**
  - docs/design/open-items/**
  - docs/design/orqlet-implementation/**
  - docs/design/orqlet-m2-workflow/**
  - docs/design/phase-skill-contracts/**
  - docs/design/team-conventions-resources/**
  - AGENTS.md
  - README.md
  - .github/**
  request_ref: workflow-efficiency
research_mode: parallel-subagents
size_budget:
  max_words: 1200
facts:
- id: A-1
  kind: structure
  statement: The six Orqlet phase skill sources hold 859 to 986 words each; the research skill has 937.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 1-58
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 7da10620a954aaf56d54e7632426a1cdceee7387b72a5531a8bc5cf445e6ccb3
- id: A-2
  kind: structure
  statement: phase-contract.md has 1,799 words, the largest instruction file an Orqlet skill loads.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md
    lines: 1-92
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: be4ab1a894ca0d4e6fc4e122072510a5b5560c180197438bbf1e181adc14d5c2
- id: A-3
  kind: structure
  statement: AGENTS.md has 1,042 words, of which the Orqlet baseline block is lines 1-41.
  evidence:
  - path: AGENTS.md
    lines: 1-95
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 0f925652ddcec085d17b617acd7dd9f8ca8f25d1cdd4f51fc9684aaec834eb01
- id: A-4
  kind: structure
  statement: The manifest lists phase-contract.md under four skills with one sha256; with .claude and
    .agents copies, 12 exist.
  evidence:
  - path: src/orqlet/workflow/MANIFEST.json
    lines: 236-273
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 5ca022097cc9ad97a95cfe2f4ade39c892b608c2bcd75d31d9038eee94d840bd
- id: A-5
  kind: structure
  statement: The same 'Source material is not authority' paragraph and the same models-resolve step open
    all six Orqlet skill sources.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 8-27
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: b3699407edd1b6b29c50e9a7ad405e3f4e3773c889789dd6d25652abe93cd521
- id: A-6
  kind: structure
  statement: The warning-list sentence is repeated in the tester role, onboard step 6 and each phase-contract
    copy.
  evidence:
  - path: src/orqlet/workflow/roles/orqlet-tester.md
    lines: '14'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: db54d66fcbdad35593114e45ff1e680815e2d84c445b3496575b55bce8f21fd0
- id: A-7
  kind: test
  statement: Tests cap every rendered skill body at 70 lines and 900 words.
  evidence:
  - path: tests/unit/test_workflow_skill_contracts.py
    lines: 777-784
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 8e787e3d2934df2723996a5d73c4708cf0077d39a205265e6cf09d7711593075
- id: A-8
  kind: test
  statement: A test caps phase-contract.md at 150 lines and 1,800 words.
  evidence:
  - path: tests/unit/test_workflow_phase_contract_text.py
    lines: 541-547
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 2b8be7ecc28f3e35985da2a1554f842a05d057f8efcba7ba6d515dd715a437b2
- id: A-9
  kind: structure
  statement: Design step 4 points to the research skill's as-is-format.md, which the design references
    folder does not hold.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: '30'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 0fcac29ba6b68c83d01f6b7b7463a922eabda1c1102663512e442b980f113b09
- id: A-10
  kind: flow
  statement: Research runs validate as-is before it stops and again after the acceptance record.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 28-48
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 3231f9792e9cdfa75f6ec078ee23aeb2e595489ef9ac86bd7c3b8a49234291de
- id: A-11
  kind: flow
  statement: Plan runs gate status in its input check and again with validate plan in step 7.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: 27-36
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 50b2a770467ff54d84b573feb36e7439c029ba09572bb62da4f7fb2abb5ade06
- id: A-12
  kind: flow
  statement: Design hashes the design files at step 7, then again when it starts each reviewer and saves
    each note.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: 33-35
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: ee206f5ea9bc702e580318fc120b4e77bc6f68d918f0eec9732acf4559a1ec0a
- id: A-13
  kind: flow
  statement: For every plan phase, implement step 1 runs the full input check on plan and design, then
    gate status --phase.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: 27-28
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 1e6bd548e62eb449ac216b14452ad490e44cc0d566883339504638fb8a5bea92
- id: A-14
  kind: flow
  statement: Before each plan check, coder and tester re-cite every source and confirm git diff --quiet
    HEAD on the cited files.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md
    lines: '29'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 4e01ea537bccd14541c1a4cb8472fd2ac4ae2df8bd11c7ce16c8a4298b93ff90
- id: A-15
  kind: flow
  statement: Implement step 6 runs the plan's checks and cites every source again before each.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: '35'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 4607ecb93badf94d0030261f5c4e28abf84b6cc25ece66382bfb0912b351f744
- id: A-16
  kind: operation
  statement: 'A recorded plan phase lists five checks: ruff-check, ruff-format, mypy, import-linter and
    pytest.'
  evidence:
  - path: docs/design/harness2-fit/plan.yaml
    lines: '30'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 10ed0beb3bfef7033e9344e640b1cc8f7d066cf927ebea7930fe1ebf7d6f4b2a
- id: A-17
  kind: flow
  statement: The tester runs the plan's test command before the code exists; the coder runs the plan's
    checks afterwards.
  evidence:
  - path: src/orqlet/workflow/roles/orqlet-tester.md
    lines: '14'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: db54d66fcbdad35593114e45ff1e680815e2d84c445b3496575b55bce8f21fd0
- id: A-18
  kind: flow
  statement: Any change to reviewed code or tests redoes the knowledge step, tester's record and review,
    for at most three rework rounds.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: '38'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: a0fcb2214aedda8e1aa4d59235956fa002ca9d9fa81d38d4f1be46d65547dac0
- id: A-19
  kind: flow
  statement: Each review round prepares a packet and starts all three reviewers in clean contexts with
    the same packet path.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-review/skill.md
    lines: 27-29
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 7ee33383d4fa65b5c8ba7685aecc0b2dec193eab155e2dc9d28b63faefe1012d
- id: A-20
  kind: flow
  statement: A blocking finding is reviewed again from review step 1 after its fix; after three rounds
    the skill stops.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-review/skill.md
    lines: '34'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 365538e52472564cff3c64e512545151b7d8a7ea711bf0286439b5adf191a2d0
- id: A-21
  kind: flow
  statement: 'The review skill runs models resolve three times: for the skill, the engineering profile
    and the code-reviewer role.'
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-review/skill.md
    lines: 26-28
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 798745393cff0be66d76752b4ce9b7421dfab49d801d02599ede332006a27112
- id: A-22
  kind: operation
  statement: Each review prepare call takes a new UUID and writes a new packet folder outside the repository.
  evidence:
  - path: src/orqlet/interface/cli/commands/review.py
    lines: 32-42
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 0bab56c984d5c3ac32177fde79215e94e63281fd4a8dd442575766f6d498f954
- id: A-23
  kind: flow
  statement: review prepare computes binding components once in common, then once per role and client
    whose agent file exists.
  evidence:
  - path: src/orqlet/application/usecases/review_prepare.py
    lines: 226-259
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 181bbcf301a88407d6426e083a18ab3fdc5fccf77ba6adcf1cc581e1874c337b
- id: A-24
  kind: dependency
  statement: Each component computation re-reads the manifest, design, plan, locks and phase records through
    Git.
  evidence:
  - path: src/orqlet/application/usecases/binding_inputs.py
    lines: 286-320
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 9fb5dea8317920b8b385f351bc5b1226bf2cb4defcffa72dd846a45be018cba0
- id: A-25
  kind: operation
  statement: GitVcs caches trees and commits per process only; no check result persists between CLI invocations.
  evidence:
  - path: src/orqlet/adapters/git/vcs_git.py
    lines: 41-43
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: e6c1026e73cdca73ac6d47c693814923fb2b3542e55223cf29f3fcdfb006bdf2
- id: A-26
  kind: flow
  statement: evidence cite handles one file and one line range per invocation.
  evidence:
  - path: src/orqlet/application/usecases/evidence_cite.py
    lines: 43-52
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 0cd79615cff01da7506611abefdb692c28ae8cd8a145235ed049b621c2e43c7f
- id: A-27
  kind: flow
  statement: With a task, gate status always adds ORQ-I393 and a not-run reason, so its verdict is NOT_RUN.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 116-123
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 61edc8bf132ef2b65d6d4790f9a705cca82dc7759c59d30f057ea535e3cf7671
- id: A-28
  kind: interface
  statement: Every validator exits 5 for both FAIL and NOT_RUN; only PASS exits 0.
  evidence:
  - path: src/orqlet/interface/cli/commands/validate.py
    lines: 40-49
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 9d61d95633dd5d6239fbbba3aaea56b656f0124e0b850dfe3de6c7f98fc9c9cc
- id: A-29
  kind: operation
  statement: The CI tests job runs pytest on 3 operating systems and Python 3.12 to 3.15, 12 runs per
    event.
  evidence:
  - path: .github/workflows/ci.yml
    lines: 66-84
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 3d558398c45338125066e308cc8243cfc6102065672d6bfe7c70017da0acaeff
- id: A-30
  kind: operation
  statement: The only clock reads in src/orqlet are the hook deadline; no check timing or execution count
    is recorded.
  evidence:
  - path: src/orqlet/interface/cli/wiring.py
    lines: 119-140
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 0a678a5e3af7dd2e9ce616de065394c14e7805f4f3c4442c7cc9540e37428359
- id: A-31
  kind: operation
  statement: 'Median per implement session (27 sessions): 15 full-suite pytest, 8 mypy, 10 ruff check,
    7 gate status, 4 review prepare runs.'
  evidence:
  - path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    lines: 35-46
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 5120256efd5e60dff4d5e8643af9484ebf3383b1de2c4297caa123e5221cc11e
- id: A-32
  kind: operation
  statement: No check command in the sessions was repeated identically without an edit in between.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    lines: 19-33
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 146958d947b7f96624273e10ee266ee8bd1045f33d2a4d9df7ba7366594cd712
- id: A-33
  kind: operation
  statement: Implement sessions re-read the same path 363 times; the top file, a plan.yaml, 64 times.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    lines: 48-58
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: bbb26dc071609a2dc278d569b3483d865ce29289eb789acbbf4da45943b9e7b7
- id: A-34
  kind: operation
  statement: Cursor saved 93 oversized tool results for this project; 15 are pytest output, about 3.8
    MB.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    lines: 59-61
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 4edb82cf0a55314df125b431ecc64f28e90f61fc30c350a6e8a6a7b832e65066
- id: A-35
  kind: operation
  statement: No user message contains 'five or six'; one session records five review prepare runs leaving
    five packets.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    lines: 63-67
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: f92e99a822b31d10a8098bf00e16aacccd7d1ef056f117a8095db2cffc476d85
- id: A-36
  kind: operation
  statement: 'Median last reply of a plan turn: 791.5 words; implement 257, research 262, design 180.'
  evidence:
  - path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    lines: 50-55
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 8cbb8d4c972d750c8bdd2eaf4e43b732c1329482e290fec1f462163571af16a0
- id: A-37
  kind: operation
  statement: The transcripts hold no timestamps, token counts or tool results.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    lines: 9-11
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 64fa8d05688ff75862a48288c0c4951a4b5dbcfbd80319d5f8a75c6e8edc8f4b
- id: A-38
  kind: interface
  statement: explain passes its limits and model findings both to the human text and as findings echoed
    to stderr.
  evidence:
  - path: src/orqlet/interface/cli/commands/lifecycle.py
    lines: 245-270
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 817a1010f9397adf1b05fc6501d763339868f07d4b1414cec6a3d95059e4116b
- id: A-39
  kind: interface
  statement: echo_findings defaults to True; its comment says False is meant for text that already lists
    the findings.
  evidence:
  - path: src/orqlet/interface/cli/runner.py
    lines: 20-26
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 9c863a2a7582260c22b9359f8c672ce3a11c74ae726b961cdddecdba8b83c09b
- id: A-40
  kind: interface
  statement: models resolve prints ten label lines and prints 'none' for each empty value.
  evidence:
  - path: src/orqlet/interface/cli/commands/models.py
    lines: 173-186
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: e4803b7a856023d1daf26ecdfea5aaabec1ed9abfaabcf88b8dd89c14083dc0d
- id: A-41
  kind: interface
  statement: The CLI result envelope carries code, message, severity and path per finding, with no next-action
    field.
  evidence:
  - path: src/orqlet/application/contracts/cli_result.py
    lines: 12-26
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 5f36cce44aa24c668d68fcf5214f8b2ab2c3ed5c8edc3bb9ada8688efa758e8b
- id: A-42
  kind: interface
  statement: README lists 17 model-policy codes and 6 review-identity codes.
  evidence:
  - path: README.md
    lines: 538-563
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 51f1d2b75340507e5ef8263655649bb4f730a88d4f5a500129bc11f2efc98e28
- id: A-43
  kind: interface
  statement: The ORQ-W547 message names ORQ-W390 and protected_set_digest without defining either.
  evidence:
  - path: src/orqlet/application/usecases/pin_staleness.py
    lines: 68-73
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: b68cfc7b1ade29f8b683ba87ff92f1fb5e52c54c22e95bec1ece54de249400a1
- id: A-44
  kind: interface
  statement: The final implement report lists files, checks run and not run, acceptance coverage, deviations
    and uncertainties, with no length limit.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: 42-45
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 3d244aeb96a6c38103b057da260ef19a35ff9d581d9f8498dc959469c56702a7
- id: A-45
  kind: interface
  statement: The size budget of an AS-IS file counts only the words of fact statements.
  evidence:
  - path: src/orqlet/application/usecases/validate_as_is.py
    lines: 153-162
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: cdbc0ee8c7d66f063d9ff8e49ed0ac579e6fe67b3c09bd75d6da303dcfed3c7b
- id: A-46
  kind: structure
  statement: 'The model policy has 277 lines: 10 models, 3 profiles, 10 assignments, none for orqlet-research
    or orqlet-review.'
  evidence:
  - path: .orqlet/model-policy.yaml
    lines: 1-277
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: fb2aa7e7dc91bc27a6b49ae089cc2fa20e31343601cfdf68992a812c4f0cbb17
- id: A-47
  kind: structure
  statement: 'No policy model is approved: all 10 carry the pre-approval state, and the six Cursor routes
    have no name.'
  evidence:
  - path: .orqlet/model-policy.yaml
    lines: 1-188
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 059d4bacc8a46512f12579aedc5899725ff8687504290486a8d3dd868e99342f
- id: A-48
  kind: flow
  statement: The resolver rejects every model not yet approved as not-approved, so every candidate list
    under this policy is empty.
  evidence:
  - path: src/orqlet/domain/model_resolution.py
    lines: 476-483
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 585ee34738fb73d7e026cc927d128d810ad599f87c9e67be77dd1a6752aec062
- id: A-49
  kind: structure
  statement: Review records hold model_requested, model_observed and identity_source, which defaults to
    unknown.
  evidence:
  - path: src/orqlet/application/contracts/review_result.py
    lines: 41-70
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 5155c6e5ee3315ccb0ee71e88d06a157a8981e89f023866bac4b416f0f1eb95f
- id: A-50
  kind: flow
  statement: Minimum independence is I2 for code-reviewer and D3 changes, else I1; a lower class reports
    not run.
  evidence:
  - path: src/orqlet/domain/independence.py
    lines: 127-138
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 29b80188192dbd2b82f0f987402b741d00ab6e28abf2eaa976ffb21246d98d2e
- id: A-51
  kind: structure
  statement: role-bindings.yaml binds the architecture and security reviewers only, not orqlet-code-reviewer.
  evidence:
  - path: .orqlet/role-bindings.yaml
    lines: 1-27
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 6f8356c02488c77e5db488921a457ea147d78af81ab181772d20e14aec5ce8b6
- id: A-52
  kind: structure
  statement: The largest earlier plan has 2,597 lines and 21,451 words, with 14 phases.
  evidence:
  - path: docs/design/dynamic-model-profiles/plan.yaml
    lines: 1-2597
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 27459c52f340aca6e210da937ca67f9049fc0c2441b8a40f0a908983efbc98ae
- id: A-53
  kind: structure
  statement: The largest earlier AS-IS file has 2,839 lines and 16,266 words.
  evidence:
  - path: docs/design/team-conventions-resources/as-is.md
    lines: 1-2839
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 068322e566a43e000d93348fcb6597201f3bb91d1a67468704d6b047aaa6bbb7
- id: A-54
  kind: structure
  statement: One ledger holds 88 questions in 2,049 lines.
  evidence:
  - path: docs/design/one-command-setup/questions.yaml
    lines: 1-2049
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: b4647855cc6e8c4fc2a53250b617142df4b740b0dab7b06507cb81ef5ff798aa
- id: A-55
  kind: structure
  statement: One AS-IS file lists contradictions C-1 to C-21 twice, as front matter and as a Markdown
    table.
  evidence:
  - path: docs/design/harness2-fit/as-is.md
    lines: 123-306
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 0bf9beb7c098f6f5fc0265f4a36af4b2b5508d3b9c293de5f69df610deaecb25
- id: A-56
  kind: structure
  statement: A plan self-check value is ten lines of BC-n, R-n and C-n codes without definitions.
  evidence:
  - path: docs/design/dynamic-model-profiles/plan.yaml
    lines: 2429-2439
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: dbe7b22b8dcc6f2fb5c4096b2ba67945fda653c1957e8d3ae7d71f922d2419ea
- id: A-57
  kind: interface
  statement: Design class D1 requires component, data-flow and sequence Mermaid diagrams and a nine-part
    brief, without length limit.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-design/references/design-format.md
    lines: 13-33
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: a79e14caa3ecf0ee3c3003352bfcbdef04843960bac4469e8700029e39ad5233
- id: A-58
  kind: structure
  statement: One task holds 81 review files, with 15 design review rounds per role.
  evidence:
  - path: docs/design/one-command-setup/reviews/architecture-reviewer-design-r15.md
    lines: 1-193
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 6505cb20149406cd027768acbac23872011a920ec159dd60008ed5604e6c151c
- id: A-59
  kind: test
  statement: pytest runs all of tests/ with sockets disabled and every warning as an error.
  evidence:
  - path: pyproject.toml
    lines: 70-80
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: bd8d44b61ef032353b8bce7bb42535baaa6dd0f66930bf7795facae27cf8f75a
- id: A-60
  kind: test
  statement: A 2,833-line test file holds 95 tests that match exact phrases in README and the architecture
    document.
  evidence:
  - path: tests/unit/test_readme_model_policy.py
    lines: 1-2833
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: e499b6f04dc88c7dfdffa2dc6a99d4163690c3b5c3ad3f77cb381c10d93340a8
- id: A-61
  kind: test
  statement: A committed test imports RenderScope and orqlet.application.usecases.user_render_request,
    which do not exist under src/orqlet.
  evidence:
  - path: tests/unit/render/test_user_scope_render.py
    lines: 78-86
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: f006da610f3147754eb1c7c18bd8a53a14388e476023f91f00c501d131985ccd
- id: A-62
  kind: structure
  statement: copilot.py holds only a docstring; its one reference is an import-linter contract.
  evidence:
  - path: src/orqlet/adapters/clients/copilot.py
    lines: 1-3
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 23a58fbe6938ead6e26942b94f191bb508fd6b99c168bd2bfe34e0b114cdefbc
- id: A-63
  kind: structure
  statement: render_rich.py presents output for install and uninstall, which app.py does not register;
    only tests import it.
  evidence:
  - path: src/orqlet/interface/cli/render_rich.py
    lines: 1-5
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 3b4eccbca59a90e94b1ed83db9a5d75387bc22ea7a55b1f3fe1703c2db92d3c1
- id: A-64
  kind: dependency
  statement: GitHub renders Mermaid blocks in pull requests and Markdown files.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/web/github-mermaid-diagrams.md
    lines: 1-12
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: a2660504adb464d7f62a4ab3e3f20b8b2c88db7fbcc86441089798d7248c31aa
- id: A-65
  kind: dependency
  statement: Claude Code reports session token usage in /usage and through OpenTelemetry.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/web/claude-code-usage.md
    lines: 1-12
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 66db4842d03e83292a35e93b00f70c44e68e123a2fd954fefa607213a81be69d
- id: A-66
  kind: dependency
  statement: Cursor's usage dashboard shows request-level cost; the page documents no export format.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/web/cursor-usage.md
    lines: 1-12
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 59ce7df8eca35834183417e28f405da05225a8f0c956d62c8ebfe156a6f4350f
- id: A-67
  kind: dependency
  statement: Cursor subagents can run a named model while the picker shows Auto.
  evidence:
  - path: docs/design/workflow-efficiency/evidence/web/cursor-usage.md
    lines: '11'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 07884a22f3729e3290f9b9a353c598eb62d81c49202e3a35e7a5af53f3f90188
- id: A-68
  kind: structure
  statement: docs/design holds 80 Mermaid blocks, 20 in the architecture document; no AS-IS file, plan,
    ledger or review contains one.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 1-6484
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: d5b14f21c76d25a59ddb8338d6b69837f74d4db389c69407970fd517965b54c0
- id: A-69
  kind: flow
  statement: gate status binds base_revision to HEAD.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 86-87
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: ce5b7912e5c02645f5f8c9ddd07442559ad7efa6bb64c7e9c7483e02f67efc59
  - path: src/orqlet/adapters/git/vcs_git.py
    lines: 85-87
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 7804e44d2d9c8a8f10bc66d3c4189fd15d08ad8e07e7a0b59da8d5db26f45e9f
- id: A-70
  kind: flow
  statement: The research header copies its bound values from gate status.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md
    lines: '77'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: fc236f98bbd2b8155db2d33ba1e4c3090cbdd05ffdc729a3d89cbfa5daf06df9
- id: A-71
  kind: interface
  statement: validate as-is rejects evidence not at base_revision.
  evidence:
  - path: src/orqlet/application/usecases/validate_as_is.py
    lines: 117-126
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 68c8150ff1d00b3b91cf63a070ce0640958a0e6b7d0a6e2d474e96c39b96c9a9
  - path: src/orqlet/workflow/skills/orqlet-research/references/as-is-format.md
    lines: '46'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: cead900eaabbbb31d4f12d9d904f29aef5cc0d9c7ceca74ca211ece3e3f816ea
- id: A-72
  kind: interface
  statement: evidence cite cites HEAD unless --revision is given.
  evidence:
  - path: src/orqlet/application/usecases/evidence_cite.py
    lines: 43-48
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 6ee36d7d4633cbaa67037d4aa6efab2dd120a31332db877361434193572e3d9e
  - path: src/orqlet/interface/cli/commands/evidence.py
    lines: 25-27
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: df4f99608b5b578d6736d6bfc3acb099066f2239e8d6f7ead602b8302dd79a24
- id: A-73
  kind: flow
  statement: Research commits web evidence, then cites it and every fact.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 32-33
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 6fb5893f46a07bdbde52571a3f21061899a9fc18f102cdd05dd8997b72cd583a
- id: A-74
  kind: flow
  statement: Design's input check needs base_revision as an ancestor of HEAD.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md
    lines: '46'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: dea6bb5433647a0f007a518fc7c79b49e368ca6748c10f45c49f183fd324d699
- id: A-75
  kind: operation
  statement: Pull requests merge by squash.
  evidence:
  - path: AGENTS.md
    lines: '84'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: ca6c5810b4d64154530d07f314ece1cd891cd3bef6fc93672ea6037e282060a0
- id: A-76
  kind: test
  statement: test_user_render_request.py also imports RenderScope and user_render_request.
  evidence:
  - path: tests/unit/application/test_user_render_request.py
    lines: 51-56
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: cdb8f4503cb50580bc9a3d48c759debc7082bc903a3168ec925b9ed26f827258
- id: A-77
  kind: operation
  statement: CI runs ruff on the tree; mypy and pytest include tests.
  evidence:
  - path: .github/workflows/ci.yml
    lines: 30-32
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 18439f43ec5e3fe0f8358649a09e241c817338e8993610f076dff1e364822f72
  - path: .github/workflows/ci.yml
    lines: 46-47
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: ba01ee52b7aeda2c865e53c856172cad0121cc7dbb7ccfdbc2c188382fcc1311
  - path: pyproject.toml
    lines: 67-71
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 500da225b7dd1e8178de962ef296532d08870960b3a21033d4577aed15e07282
- id: A-78
  kind: structure
  statement: ORQLET-QA-001 requires all checks pass before a pull request is ready.
  evidence:
  - path: .prompts/rules.yaml
    lines: 141-147
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: fa38bd8987d14c12b2c3aec709066f0a686b8d9dfee5cda19bf496286e82daa6
- id: A-79
  kind: interface
  statement: standards for and explain print each rule's level and id.
  evidence:
  - path: src/orqlet/interface/cli/render_human.py
    lines: 18-24
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 077cc7f1c8642d8c7f403ff94de4b9b27af10051e7de62db1e2fb9c642b52a4b
  - path: src/orqlet/interface/cli/render_human.py
    lines: 134-135
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 629d453530102498c7c3c7eda36bd64469963b08068b2d343fa9481ecf23696e
- id: A-80
  kind: structure
  statement: The baseline says MUST rules are not optional.
  evidence:
  - path: src/orqlet/workflow/baseline/baseline.md
    lines: '23'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 2a5271d72608fbdf3cd68e0cb3126c41532e6abc2d2fc254e6e94d77abb2b38c
- id: A-81
  kind: flow
  statement: The standards command asks the agent to name applied rule ids.
  evidence:
  - path: src/orqlet/workflow/commands/standards.md
    lines: '10'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 394fab462a5d27961eeeb1b23d24028d270ad36b07b4c71821402b7270a6e1ff
- id: A-82
  kind: structure
  statement: Generated rule files, design manifests and review findings carry rule ids.
  evidence:
  - path: src/orqlet/application/usecases/render_request.py
    lines: 225-226
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 19c1d031a4b2348804bc06240882974c8b9dc58b443f9c58afef233f1964f78e
  - path: src/orqlet/workflow/skills/orqlet-design/references/design-format.md
    lines: '78'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: a4b938055bd4924f47ea4397966cb062f3cae77268bb28d82f5bc7bc2467f3ff
  - path: src/orqlet/workflow/skills/orqlet-review/references/review-format.md
    lines: '85'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: a93910a2655bc45785caa8fc4619885dcefd4d8046815ab3b9c683091682c1b5
- id: A-83
  kind: flow
  statement: Committed earlier phases make gate status report the plan stale (ORQ-W390), since its scope
    is its operation paths; likewise the design and AS-IS when their scope changed.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 179-185
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: f24cfdbca8600266abd51462931da08edf99b2cc57639ee170085276493fd2bb
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 188-191
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 2c10cb471edf765d1a5174a8397a385e20d54ef63d13916c3e2c5e4a4dc95339
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 205-229
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 8c3fca50642ec164a363a0a74aa586adfe7db73368bda904ee37ccb1c8397588
  - path: src/orqlet/application/usecases/staleness.py
    lines: 11-30
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: ad1981d80b7483984d607ee8f46a6f0df70b7b8d6a2474068139830338c8de9e
  - path: tests/unit/application/test_gate_status.py
    lines: 181-191
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 799ce473d1fcfc1172426b674195f0db5b7d36b898087e37cd2a8d79bf23368a
- id: A-84
  kind: flow
  statement: Implement stops on ORQ-W390 until the person confirms the planned-work row; gate status reads
    no trailer.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md
    lines: 58-60
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: 379eaf43762b41d5717418ac3af506ab707f74c34d77716b569810d7400b6961
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: '28'
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: abe08b555946f39423f9e0d0b1870a31c99bd9eca170aef8868a0aad1b64ead0
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 179-185
    revision: a29b0ba67ffdeee713c302ce9f633cd3b648da64
    sha256: f24cfdbca8600266abd51462931da08edf99b2cc57639ee170085276493fd2bb
unknowns:
- id: U-1
  what: Whether each client loads a skill's references when the skill starts or only when the text points
    to them, so the words loaded per run are unknown
  material: true
  merged_from:
  - inv-instructions/U-6
  - inv-instructions/U-1
- id: U-2
  what: How the design skill resolves the research skill's as-is-format.md in each client
  material: true
  merged_from:
  - inv-instructions/U-4
- id: U-3
  what: Whether installed skill copies and per-client golden copies are byte-identical apart from the
    generated header and markers
  material: false
  merged_from:
  - inv-instructions/U-3
  - inv-docs-tests/U-3
- id: U-4
  what: Whether the Codex role files and agents/openai.yaml files repeat the full role text
  material: false
  merged_from:
  - inv-instructions/U-5
- id: U-5
  what: Whether the design, plan or review validators enforce any document length
  material: true
  merged_from:
  - inv-instructions/U-7
- id: U-6
  what: How the ponytail skill's reply rule interacts with the STOP messages of the Orqlet skills
  material: false
  merged_from:
  - inv-instructions/U-8
- id: U-7
  what: Whether the nested /orqlet-review run repeats implement's models resolve and standards work or
    reuses it
  material: true
  merged_from:
  - inv-instructions/U-9
- id: U-8
  what: Whether the design reviewers and the three code-phase reviewers run concurrently; no skill text
    says
  material: false
  merged_from:
  - inv-instructions/U-10
- id: U-9
  what: Guidance for the main agent as Coder beyond the baseline, implement step 5 and the standards output;
    no coder role file exists
  material: false
  merged_from:
  - inv-instructions/U-11
- id: U-10
  what: The machine count of distinct finding codes; a hand count gives 256 (165 E, 50 W, 35 I, 6 L)
  material: false
  merged_from:
  - inv-checks/U-1
- id: U-11
  what: Elapsed time and token usage of sessions, CLI invocations, git calls, pytest runs and CI jobs;
    none is recorded in the repository or the transcripts
  material: true
  question_ref: Q-3
  merged_from:
  - inv-checks/U-4
  - inv-checks/U-10
- id: U-12
  what: Whether explain's compose path calls Git beyond constructing GitVcs
  material: false
  merged_from:
  - inv-checks/U-5
- id: U-13
  what: Whether GitHub-hosted runners provide Python 3.15 for the CI matrix
  material: false
  merged_from:
  - inv-checks/U-7
- id: U-14
  what: How agents treat exit status 5 when gate status is NOT_RUN only because of ORQ-I393
  material: true
  merged_from:
  - inv-checks/U-9
- id: U-15
  what: The Cursor model ids of the policy's starting candidates (frozen Q-35 of dynamic-model-profiles)
  material: true
  merged_from:
  - inv-models/U-3
- id: U-16
  what: Whether any CI check turns a NOT_RUN gated review into a blocked merge (frozen Q-36)
  material: true
  merged_from:
  - inv-models/U-4
- id: U-17
  what: Whether a model family means the vendor or the model line (frozen Q-38)
  material: true
  merged_from:
  - inv-models/U-5
- id: U-18
  what: Which clients report the running model to an agent; no review record holds an observed identity
  material: true
  merged_from:
  - inv-models/U-6
- id: U-19
  what: Who fills the model fields of a review record; one record says the Coder wrote it from the returned
    text
  material: true
  merged_from:
  - inv-models/U-7
- id: U-20
  what: Whether .orqlet/model-policy.yaml equals its packaged seed
  material: false
  merged_from:
  - inv-models/U-9
- id: U-21
  what: Whether the coder reruns every plan check after a rework round; the rework step names only the
    knowledge step, the tester's record and the review
  material: true
  merged_from:
  - trace-checks/U-1
- id: U-22
  what: Whether sources shared by several checks are re-cited once per check
  material: true
  merged_from:
  - trace-checks/U-2
- id: U-23
  what: Which pytest run the tester's record reports
  material: true
  merged_from:
  - trace-checks/U-3
- id: U-24
  what: Which session showed the reported five or six repetitions of checks
  material: true
  question_ref: Q-9
  merged_from:
  - trace-checks/U-4
- id: U-25
  what: Check counts per plan phase; the transcripts do not mark phase boundaries
  material: true
  merged_from:
  - trace-checks/U-5
- id: U-26
  what: Which Python versions local check runs use
  material: true
  merged_from:
  - trace-checks/U-6
- id: U-27
  what: How many packet files each reviewer reads
  material: true
  merged_from:
  - trace-checks/U-7
- id: U-28
  what: Whether implement's input check also runs validate as-is
  material: false
  merged_from:
  - trace-checks/U-8
- id: U-29
  what: How many Git processes diff_patch starts
  material: false
  merged_from:
  - trace-checks/U-9
- id: U-30
  what: Whether anything removes old review packets from the data directory
  material: false
  merged_from:
  - trace-checks/U-10
- id: U-31
  what: Whether the edits between reruns changed each rerun check's inputs
  material: true
  merged_from:
  - trace-checks/U-11
- id: U-32
  what: Unused functions, classes and constants inside used modules; only module-level references were
    checked
  material: true
  merged_from:
  - inv-docs-tests/U-4
- id: U-33
  what: How far fragment files repeat their AS-IS file; one repeat is verified, and three tasks hold 3,316
    to 5,690 fragment lines
  material: true
  merged_from:
  - inv-docs-tests/U-5
- id: U-34
  what: Whether copilot.py, render_rich.py, user_scope.py and the user-render tests are obsolete or frozen
    work in progress
  material: true
  question_ref: Q-10
  merged_from:
  - inv-docs-tests/U-6
- id: U-35
  what: The collected test count after parametrisation; 4,243 test functions are defined
  material: false
  merged_from:
  - inv-docs-tests/U-7
- id: U-36
  what: The phase and acceptance-criteria counts of the harness2-fit plan
  material: false
  merged_from:
  - inv-docs-tests/U-8
- id: U-37
  what: Whether other tests import names missing from src
  material: true
  merged_from:
  - inv-docs-tests/U-9
- id: U-38
  what: The size of tool results per Orqlet command; transcripts store no tool results
  material: true
- id: U-39
  what: Usage reporting and Mermaid rendering in Codex and Copilot were not looked up
  material: false
- id: U-40
  what: How Copilot behaves for this project; the profile does not enable it, so no Copilot files are
    generated here
  material: false
- id: U-41
  what: Whether the CLI version 0.4.0 next to workflow 0.5.0 is intended
  material: false
  question_ref: Q-11
- id: U-42
  what: The job results of main's required checks; CI run 45152031442 of 92e026e is on GitHub, outside
    the base revision
  material: true
  question_ref: Q-19
- id: U-43
  what: Which file or ruff rule fails the lint job; the missing names explain mypy and pytest only
  material: true
- id: U-44
  what: Whether the architecture and build jobs read tests/; lint-imports names the orqlet package only
  material: false
- id: U-45
  what: Whether Cursor and Claude Code show a generated rule file's body to the person
  material: true
  merged_from:
  - inv-rule-ids/U-3
- id: U-46
  what: Whether a client shows the human output of standards for and explain to the person or only to
    the agent
  material: true
  merged_from:
  - inv-rule-ids/U-4
- id: U-47
  what: Whether the review report to the person includes a finding's optional rule_ref
  material: true
  merged_from:
  - inv-rule-ids/U-5
contradictions:
- id: C-1
  sources:
  - README.md:332
  - src/orqlet/workflow/skills/orqlet-review/skill.md:7
  note: README says orqlet-review starts the architecture and security reviews; the skill starts three
    reviewers, including the Code Reviewer.
  merged_from:
  - inv-instructions/C-1
- id: C-2
  sources:
  - README.md:357
  - src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md:86
  note: README runs standards for with --phase implement --role tester; the contract maps implement to
    --phase implementation --role coder.
  merged_from:
  - inv-instructions/C-2
- id: C-3
  sources:
  - src/orqlet/workflow/skills/orqlet-implement/skill.md:7
  - src/orqlet/workflow/skills/orqlet-plan/references/plan-format.md:73
  note: Implement says three reviewers work in every phase; plan-format requires the code reviewer only
    from workflow 0.5.0.
  merged_from:
  - inv-instructions/C-3
- id: C-4
  sources:
  - src/orqlet/interface/cli/exit_codes.py:12
  - src/orqlet/interface/cli/commands/validate.py:40-49
  note: The exit-code comment says doctor or sync found an error; validators also use exit 5 for NOT_RUN.
  merged_from:
  - inv-checks/C-1
- id: C-5
  sources:
  - src/orqlet/interface/cli/runner.py:25
  - src/orqlet/interface/cli/commands/lifecycle.py:251-270
  note: echo_findings is meant to be False when the text lists the findings; explain lists them and leaves
    it True.
  merged_from:
  - inv-checks/C-2
- id: C-6
  sources:
  - src/orqlet/interface/cli/render_rich.py:1-5
  - src/orqlet/interface/cli/app.py:39-57
  note: render_rich presents output for install and uninstall; the CLI registers neither command.
  merged_from:
  - inv-checks/C-3
  - inv-docs-tests/C-5
- id: C-7
  sources:
  - src/orqlet/application/usecases/gate_status.py:116-123
  - src/orqlet/workflow/skills/orqlet-plan/skill.md:28
  note: The skill says a NOT_RUN caused by ORQ-I393 alone is not a failure; the CLI exits 5 for it, the
    failed-check code.
  merged_from:
  - inv-checks/C-4
- id: C-8
  sources:
  - docs/design/dynamic-model-profiles/design/component.md:167
  - src/orqlet/application/usecases/model_selection.py:357-364
  note: The design says unnamed Cursor routes are missing-candidate; the code checks that only in manual
    modes, and the policy uses automatic.
  merged_from:
  - inv-models/C-1
- id: C-9
  sources:
  - src/orqlet/workflow/skills/orqlet-review/skill.md:28
  - src/orqlet/domain/model_resolution.py:480-481
  note: The review skill matches the coder among printed candidates; every model is proposed, so none
    is printed.
  merged_from:
  - inv-models/C-2
- id: C-10
  sources:
  - src/orqlet/application/usecases/models_resolve.py:22-23
  - .orqlet/model-policy.yaml:258-262
  note: A docstring says orqlet-code-reviewer is not yet a workflow role; the role file exists and the
    policy assigns it.
  merged_from:
  - inv-models/C-3
- id: C-11
  sources:
  - src/orqlet/application/contracts/model_policy.py:3-4
  - src/orqlet/application/usecases/models_resolve.py:143-155
  note: The contract docstring says no use case reads the policy; three use cases load it.
  merged_from:
  - inv-models/C-4
- id: C-12
  sources:
  - src/orqlet/workflow/skills/orqlet-review/references/review-format.md:67
  - .orqlet/role-bindings.yaml:1-27
  note: The format requires an approved binding for the role; code-reviewer records name a binding that
    role-bindings.yaml lacks.
  merged_from:
  - inv-models/C-5
- id: C-13
  sources:
  - src/orqlet/workflow/skills/orqlet-plan/references/plan-format.md:71
  - src/orqlet/application/usecases/validate_plan.py:41
  note: The format allows a reviewer role as check_ref; the validator's list omits code-reviewer.
  merged_from:
  - trace-checks/C-1
- id: C-14
  sources:
  - tests/unit/test_workflow_skill_contracts.py:577-578
  - src/orqlet/workflow/skills/orqlet-implement/references/phase-contract.md:41-44
  note: The test cites gate status --phase before the validators; the contract runs gate status, then
    the validator, then git checks, and implement runs --phase after them.
  merged_from:
  - trace-checks/C-2
- id: C-15
  sources:
  - AGENTS.md:85
  - AGENTS.md:47-75
  note: The required checks include architecture and build; the recorded commands hold no lint-imports
    and no build step.
  merged_from:
  - trace-checks/C-3
- id: C-16
  sources:
  - docs/design/dynamic-model-profiles/design/manifest.yaml:186
  - docs/design/dynamic-model-profiles/plan.yaml:2540-2541
  note: The manifest self-check names BC-1 to BC-42; the plan says the design holds BC-1 to BC-45.
  merged_from:
  - inv-docs-tests/C-1
- id: C-17
  sources:
  - tests/unit/render/test_user_scope_render.py:78-86
  - src/orqlet/application/ports/instruction_adapter.py:114-125
  note: The committed test uses RenderScope and RenderRequest.scope; neither exists in src.
  merged_from:
  - inv-docs-tests/C-2
- id: C-18
  sources:
  - tests/unit/render/test_user_scope_render.py:525-542
  - tests/conftest.py:85-86
  note: The test compares with golden family user-2026-11, which has no files; the fixture fails on a
    missing golden file.
  merged_from:
  - inv-docs-tests/C-3
- id: C-19
  sources:
  - docs/design/dynamic-model-profiles/plan.yaml:5
  - docs/design/dynamic-model-profiles/reviews/architecture-reviewer-P-14-r3.yaml:1-157
  note: Four plan headers say status draft while phase review records up to P-14 exist.
  merged_from:
  - inv-docs-tests/C-4
- id: C-20
  sources:
  - docs/design/workflow-efficiency/questions.yaml:83-102
  - .orqlet/project-profile.yaml:162-166
  note: The research scope covers four clients; the project enables three, without Copilot.
- id: C-21
  sources:
  - src/orqlet/__init__.py:3
  - src/orqlet/workflow/MANIFEST.json:386
  note: The CLI reports version 0.4.0; the packaged workflow is 0.5.0.
- id: C-22
  sources:
  - docs/design/workflow-efficiency/questions.yaml:123-143
  - src/orqlet/application/usecases/validate_as_is.py:153-162
  note: Q-7 set the budget for the research brief; the validator applies size_budget to fact statements
    only.
- id: C-23
  sources:
  - src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md:46
  - AGENTS.md:84
  note: Same project reads a base_revision that is not an ancestor of HEAD as another repository or an
    unpublished branch; under squash merges a merged research-branch commit is not an ancestor of main
    either (Q-12).
  merged_from:
  - trace-binding/C-1
- id: C-24
  sources:
  - .prompts/rules.yaml:141-147
  - docs/design/workflow-efficiency/questions.yaml:266-293
  note: ORQLET-QA-001 requires all checks to pass before a pull request is ready; Q-14 leaves main red
    and has this task's pull requests report the failures as known.
- id: C-25
  sources:
  - .prompts/rules.yaml:141-147
  - .github/workflows/ci.yml:30-47
  note: ORQLET-QA-001 names every supported Python version; the lint and types jobs run on Python 3.12
    only.
self_check:
  schema: orqlet.self-check/v1
  checked_against:
    role: researcher
    phase: research
    confirmed_requirements:
    - Q-1
    - Q-2
    - Q-4
    - Q-5
    - Q-6
    - Q-7
    - Q-8
    - Q-9
    - Q-10
    - Q-11
    - Q-12
    - Q-13
    - Q-14
    - Q-15
    - Q-16
    - Q-17
    - Q-18
    - Q-19
    - Q-20
    - Q-21
    applicable_standards:
    - 'src/orqlet: 88e3e089ba38309c8acd8084933e2b62fc9109d1d8430c54e72f355cdff0c57d'
    - 'tests: bf7e3320dfee207b9f60f217769bde90b959d4bf5a5c43419c356dea8aab62ed'
    - '.prompts, docs, AGENTS.md, README.md, .github: 7cedb45ea31f8900517dcaca99243b1d35b05b37792a98fd1c45d16b2bf75038'
    evidence:
    - docs/design/workflow-efficiency/evidence/transcripts/agent-sessions.md
    - docs/design/workflow-efficiency/evidence/web/github-mermaid-diagrams.md
    - docs/design/workflow-efficiency/evidence/web/claude-code-usage.md
    - docs/design/workflow-efficiency/evidence/web/cursor-usage.md
  checks:
  - what: every fact cites the base revision
    how: orqlet evidence cite --revision a29b0ba6 for each of the 90 evidence entries of A-1 to A-82, all
      with an unchanged sha256; a29b0ba6 is the squash merge of pull request 55 on main, which changed
      only this task's as-is.md and questions.yaml. The 8 entries of A-83 and A-84 were cited at HEAD
      a29b0ba6
    result: pass
  - what: the header binds a29b0ba6
    how: orqlet gate status workflow-efficiency --json run with HEAD at a29b0ba6 on branch
      workflow-efficiency-q21-research; only base_revision differs from the earlier header
    result: pass
  - what: the ledger is valid
    how: orqlet validate ledger docs/design/workflow-efficiency/questions.yaml
    result: pass
  - what: the cited ranges say what the facts state
    how: a sample of 14 ranges was read back; the rest rest on the fragments of the five subagents. All 22
      ranges of A-69 to A-82 were read back in the refresh session
    result: pass
  - what: word counts, HEAD, committed test files and explain's double output, which the subagents could
      not check
    how: wc -w, git rev-parse HEAD, git ls-files and orqlet explain in the research session
    result: pass
  - what: no workflow text mentions squash merges or rebinding after a merge
    how: git grep -i squash 92e026e0 -- src/orqlet/workflow found nothing
    result: pass
  - what: the cited ranges of A-83 and A-84 say what the facts state
    how: all 8 ranges were read in the Q-21 refresh session
    result: pass
  - what: rewording A-4, A-13, A-14, A-18, A-21, A-31, A-33, A-35, A-36, A-50 and A-57 to fit the budget
      kept their meaning
    how: each new statement was compared with the old one in the Q-21 refresh session; their evidence is
      unchanged
    result: pass
  - what: nothing in application or domain reads an Orqlet-Task trailer
    how: rg 'Orqlet-Task|trailer' over src/orqlet/application and src/orqlet/domain found nothing
    result: pass
  - what: the person accepted the Q-21 refresh
    how: 'tmishari, 2026-11-23T13:53:10+00:00, in the research chat, choosing: ''Accept the refresh
      as it is'''
    result: pass
  - what: no clock reads besides the hook deadline
    how: rg 'monotonic|perf_counter|time.time(' over src/orqlet
    result: pass
  unverified:
  - Facts outside the read-back sample rest on the line ranges the subagents reported; evidence cite confirms
    the ranges exist, not their meaning.
  - The transcript counts come from a pattern match; the method is in the evidence file.
  - The Cursor usage dashboard export was not provided (Q-3).
  - The three refresh subagents could not run shell commands; their ranges were cited and read back in the
    main session, and their unknowns about missing hashes were resolved there.
  - No project check was run, so the causes of the red jobs rest on the cited lines only (U-42, U-43).
  - A-83 and A-84 were traced in the main session only; the client rejected the orqlet-tracer subagent
    type, so no independent tracer checked them. No implement run with two committed phases was observed.
  questions:
  - Q-3
---

# workflow-efficiency: AS-IS research brief

## Request

"Research how to make Orqlet faster, simpler, and more user-friendly by reducing unnecessary tokens, tool calls, checks, iterations, document length, and messages." The person's requirements for later approved changes (execution and verification, user experience, documents, code and tests, short responses, documentation synchronisation) are recorded in the request and are not restated here.

## Scope

Covered: skill, reference and role sources and their installed copies; validators, gates, review and model commands; CI; the model policy and review records; the frozen tasks' documents (read-only); the tests; 47 local Cursor sessions (Q-1); three official documentation pages (Q-8). Clients: Claude Code, Codex, Cursor and Copilot (Q-5); this project enables three (C-20). The first refresh added base-revision binding, main's red checks and rule ids in user output (Q-12, Q-14, Q-17, Q-20). The Q-21 refresh binds every fact at `a29b0ba` and adds staleness in later implement phases (Q-21). Left out: this task's own folder, a dashboard export (Q-3), the CI job results (Q-19) and any run of a project check.

## Existing capabilities and behaviour

**Instruction load.** A research run loads about 4,430 words of instructions: skill 937, phase contract 1,799, format 652, `AGENTS.md` 1,042 (A-1, A-2, A-3). Tests cap a skill body at 70 lines and 900 words, and the phase contract at 1,800 words (A-7, A-8). The repository holds 12 phase-contract copies (A-4), and the same paragraphs open every skill (A-5, A-6).

**Checks.** Instructed counts are per skill run unless a row says otherwise; observed counts are medians per implement session (A-31), without timings (A-37, U-11).

| Check | Trigger | Inputs | Required repetition | Instructed | Observed |
|---|---|---|---|---|---|
| `gate status` | input check; plan step 7; implement `--phase` | locks, profile, HEAD, task files | per skill run and implement phase (A-11, A-13) | 2 per phase | 7 |
| `validate as-is/design/plan` | phase end; later input checks | approved artifacts, fixed after merge | per plan phase (A-10, A-13) | 1–2 | plan: 2 |
| `evidence cite`, `git diff --quiet` | each plan check, coder and tester | cited CI and config files | "cite every source again before each" (A-14, A-15) | ~5 + 1 per phase | – |
| ruff check, ruff format, mypy, import-linter | implement step 6 | working tree | each change; rework unstated (U-21) | 1+ each | 10, n/a, 8, 5 |
| pytest | tester, then coder | tests, then code | twice per phase or more (A-17) | 2+ | 15 full, 5 targeted |
| `review prepare`, 3 reviewers | each round | staged tree, one packet | new packet per round, 3 rounds at most (A-19, A-20, A-22) | 1 + 3 per round | 4 |
| `validate review/test/knowledge` | each record and round | record, staged tree, recomputed components (A-23, A-24) | after any reviewed change (A-18) | 5 per round | – |
| `models resolve` | skill start; review step 3 | policy | 3 times in review (A-21) | 1–3 | – |
| CI pytest | each push | pull request head | 12 jobs (A-29) | 12 | unknown (U-11) |

"–" means the sessions do not separate the count.

No session repeated a check identically without an edit in between (A-32). No result persists between CLI calls (A-25), `evidence cite` takes one range per call (A-26), and nothing records timing (A-30).

**Reads and output.** Implement sessions re-read the same path 363 times, mostly plan files (A-33). Cursor stored 93 oversized results, including 3.8 MB of pytest output (A-34). Plan turns end with a median 791.5-word reply (A-36). The implement report has no length limit (A-44).

**Usability examples.**
- `explain` prints its Limits list twice (A-38, A-39, C-5).
- `models resolve` prints six `none` lines for this research (A-40).
- No policy model is approved, so no candidate is listed, yet the review skill picks the first candidate (A-47, A-48, C-9).
- Records hold requested and observed models, defaulting to unknown (A-49).
- `gate status` is always NOT_RUN and exits 5, the failure code (A-27, A-28, C-7).
- Findings carry no next action (A-41); ORQ-W547 cites two undefined names (A-43).

**Readability examples.**
- The largest plan has 21,451 words and the largest AS-IS 16,266 (A-52, A-53); one ledger holds 88 questions (A-54).
- One AS-IS file lists 21 contradictions twice (A-55); a plan self-check is ten lines of undefined codes (A-56).
- One task needed 15 design review rounds per role (A-58).
- Design requires Mermaid diagrams, which GitHub renders, but no AS-IS file or plan has one (A-57, A-64, A-68).

**Code and tests.**
- One test file matches 95 exact README phrases (A-60).
- Committed tests import names that `src` lacks (A-61, A-76, C-17, C-18).
- `copilot.py` and `render_rich.py` are unreferenced by the CLI, and frozen work names them (A-62, A-63, Q-10).

**Measurement sources.** Claude Code reports session tokens via `/usage` and OpenTelemetry (A-65); Cursor shows request-level cost with no documented export (A-66); a Cursor subagent may run a model other than the picker shows (A-67).

**Base revision binding.** `gate status` binds HEAD, which research copies into the header (A-69, A-70). Every evidence entry sits at that revision; `evidence cite` defaults to HEAD (A-71, A-72). Research commits web evidence before citing it (A-73). Design needs the base revision as an ancestor of HEAD, and pull requests merge by squash (A-74, A-75), so a research-branch commit leaves main's history (C-23). No workflow text mentions squash merges.

**Later implement phases.** Once an earlier phase is committed, `gate status` reports the plan as stale with ORQ-W390 and a not-run reason, because a plan's scope is its own operation paths. The design and AS-IS file go stale only when those commits change a path under their `scope.paths` (A-83). Implement then stops until the person confirms the planned-work row of the stale-input matrix; `gate status` reads no commit trailer (A-84).

**Main's required checks.** Both frozen P-7 test files import `RenderScope` and `user_render_request`, which `src` lacks (A-61, A-76); CI's ruff, mypy and pytest cover `tests/` (A-77). ORQLET-QA-001 requires all checks to pass before a pull request is ready; Q-14 leaves main red (A-78, C-24, C-25). The job results and the failing ruff rule are unknown (U-42, U-43).

**Rule ids in user output.** `standards for` and `explain` print rule levels and ids (A-79). The baseline calls MUST rules not optional (A-80); the standards command asks the agent to name applied ids (A-81). Generated rule files, design manifests and review findings carry ids (A-82). Whether clients show these to the person is unknown (U-45 to U-47).

## Inferences

- I-1 The per-phase input check and per-check re-citation repeat work on inputs the plan merge fixed (A-13, A-14). Evidence-cite counts per phase would confirm it.
- I-2 Rework rounds multiply pytest, review and record validation, fitting the maxima of 134 pytest and 26 review-prepare runs (A-18, A-31). Per-round counts would confirm it.
- I-3 Model-selection output offers no usable choice under the current policy (A-40, A-47, A-48). A run with an approved model would confirm it.
- I-4 The largest documents hold most of a phase start's reading load (A-33, A-52). Read logs by file size would confirm it.
- I-5 Under squash merges, an AS-IS file bound at its research branch's HEAD fails design's ancestor check (A-69, A-74, A-75, C-23). Q-12 is one case; a second squash-merged task would confirm it.
- I-6 Every implement phase after the first meets ORQ-W390 on the plan and one planned-work confirmation by the person (A-83, A-84). An implement run with two committed phases would confirm it.

## Open questions

- U-11 stays unknown after Q-3 was withdrawn; U-24 stays unknown after Q-9 named no session.
- U-42 (Q-19): the CI job results on main.
- Material unknowns without a question: U-1, U-7, U-14, U-18, U-19, U-21, U-22, U-23, U-31, U-43, U-45, U-46, U-47.

## Inputs for design

- The person's answers, Q-1 to Q-21.
- Checks, A-10 to A-30; session baselines, A-31 to A-37; usability, A-38 to A-51.
- Documents and tests, A-52 to A-63; measurement and diagrams, A-64 to A-68.
- Base-revision binding, A-69 to A-75; red checks, A-76 to A-78; rule ids, A-79 to A-82; later implement phases, A-83 and A-84.
- Every unknown and contradiction, U-1 to U-47 and C-1 to C-25.
