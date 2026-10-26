---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: team-conventions-resources
  status: draft
  workflow_version: 0.3.1
  protected_set_digest: be7723282aec5a67e8161540bfba464562fb2a53d9bc3f8245ea22b812134eec
  bound:
    base_revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    standards_lock_hash: 89a225016ff9d8b3ed977df39a70dfbe9dbc5f7c6d3762d0f2208b1b7a037a52
    applicable_rules_hash: 56502a0ec5eda3b13b4c9d97c7d4dfa41df82c86a206e36dd5d2d92aab299b97
    profile_version: 1
base_revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
scope:
  paths:
  - docs/design/orqlet-architecture-proposal.md
  - src/orqlet/**
  - tests/**
  - tools/**
  - .orqlet/**
  - .claude/**
  - .cursor/**
  - .codex/**
  - .agents/**
  - .github/**
  - docs/design/team-conventions-resources/evidence/**
  request_ref: team-conventions-resources
research_mode: parallel-subagents
size_budget:
  max_words: 5769
facts:
- id: A-1
  kind: interface
  statement: '`init_command` takes repeatable `answer` pairs, a `target_branch` option that becomes the
    answer to `repository.target_branch` when `answer` does not already give one, and the flags `--git-init`,
    `--new-project`, `--yes` and `--dry-run`.'
  evidence:
  - path: src/orqlet/interface/cli/commands/init.py
    lines: 21-67
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: b2581f17f698cc114ef3274e6996610510d30d3e5d47687c9f785f48aa8a2ca0
- id: A-2
  kind: interface
  statement: '`profile` is a sub-app with two commands: `answer` takes one or more KEY=VALUE pairs and
    calls `answer_profile`, and `approve` takes a required `reviewer` option and calls `approve_profile`.
    Both take `yes` and `dry_run`.'
  evidence:
  - path: src/orqlet/interface/cli/commands/profile.py
    lines: 27-74
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 953038fb135c16ff0d18c674667a630acae24bb35628254891b2a92c1a2ae7b4
- id: A-3
  kind: flow
  statement: '`init_project` returns `already-initialised` (ORQ-I010, "Use sync, doctor or upgrade") when
    `LOCK_PATH` is a file. Otherwise `_run` loads a profile with `_load_existing_profile` and calls `_draft_and_ask`
    only when there is none. When `git_init` is set and the `target_branch` value is None, init stops
    with ORQ-E113 and `needs-input`.'
  evidence:
  - path: src/orqlet/application/usecases/init_project.py
    lines: 94-131
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 8c15154c584c7db6f0ea3b714b376e94133c57259a03c92c270fad874c3c5fd7
- id: A-4
  kind: flow
  statement: '`questions_for` asks the stack questions only when `asks_stack` is true. `facts.python`
    and `facts.package_manager` are asked when `wants_python_questions` holds and the value is None. `project.kind`,
    `facts.frameworks` and `structure.test_runner` are asked additionally for a new project. `technologies`
    is asked for a new project that has none.'
  evidence:
  - path: src/orqlet/application/usecases/init_questions.py
    lines: 50-89
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ebaf5643813481eb453d4cc5c925fb84a6f37fb3a1f96f32b0009889d72f4d59
- id: A-5
  kind: flow
  statement: Independently of the stack questions, three repository questions are asked while the value
    is None. They are `repository.target_branch` ("Which branch do pull requests target?"), `repository.branch_naming`
    and `repository.commit_convention`. The last two say "leave empty if not".
  evidence:
  - path: src/orqlet/application/usecases/init_questions.py
    lines: 90-106
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 1e8dfee7dab39ca474e2b63b6bd42f38ae4368411241c7ec950e5438c75e552c
- id: A-6
  kind: flow
  statement: '`_repository` stores `repository.target_branch` as a `TargetBranch` and the other two repository
    answers as plain facts, each with `answered_by` set to maintainer. `_acceptable` rejects an answer
    longer than `_MAX_ANSWER` (200, defined at line 47) or with a line break. It adds format checks only
    for `facts.package_manager`, `project.kind` and `repository.target_branch`.'
  evidence:
  - path: src/orqlet/application/usecases/init_questions.py
    lines: 229-281
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 754ba2bcc7f145875f9c867620441502e19380affbb61a52b586c852206d85b1
- id: A-7
  kind: structure
  statement: '`TargetBranch` adds `remote` to a fact. `PullRequestTemplate` holds `targets`, `source_id`
    and a `status` of provisioned, team-template-unknown or none. `PullRequests` holds `reviewers` and
    `merge_strategy` as plain strings that default to unknown. `Repository` holds `target_branch`, `branch_naming`,
    `commit_convention` and `pull_requests`.'
  evidence:
  - path: src/orqlet/application/contracts/profile.py
    lines: 76-96
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 6cb046424e3aa0002154ca437794c57049ff44af28ba04f75810dd37f7ce5d83
- id: A-8
  kind: flow
  statement: '`discover_pr_templates` looks in `.github`, `docs` and the root for template files and for
    a `PULL_REQUEST_TEMPLATE/` folder. `choose_pr_targets` returns `DEFAULT_PR_TEMPLATE` when none exists
    and the single file when exactly one exists. Otherwise it takes the answer to `PR_TARGETS_KEY` or
    asks a question with the candidates as options, and an empty or unlisted answer leaves the choice
    open.'
  evidence:
  - path: src/orqlet/application/usecases/init_files.py
    lines: 125-182
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 5d6fc746334bcd2ea8d12d43e235d1b99e92971c21646fdaff029aac76eb9dee
- id: A-9
  kind: flow
  statement: '`_with_pr_template` leaves the profile unchanged and raises ORQ-W050 while the template
    choice is open. Otherwise it records the `targets`, sets `source_id` to None, and sets `status` to
    `provisioned` when a loaded pack has a `pr-template` asset and to `team-template-unknown` when not.
    It copies `reviewers` and `merge_strategy` from the current profile unchanged.'
  evidence:
  - path: src/orqlet/application/usecases/init_project.py
    lines: 305-333
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 3c445ba8be23c72045e36113e442c6ce9d7c5b865287959947ca65796a94ae53
- id: A-10
  kind: flow
  statement: '`team_template` returns the single `pr-template` asset of the loaded packs (several give
    ORQ-W051 and no template). `pr_template_files` writes, for each target, the team block (`team_block`,
    only when a pack supplied one) and the Orqlet block (`workflow_block`, built from `services.workflow`)
    as `SHARED_BLOCK` parts of the template file.'
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: 134-182
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 9f174ce1e15ac06b73429827fa4bf75c866c924c3c093bb088847b60f3fef316
- id: A-11
  kind: structure
  statement: The Orqlet-owned pull-request block is fixed text with `Orqlet-Task`, `Orqlet-Phase`, `Knowledge
    impact`, `Knowledge record`, an evidence list (design, plan, review, test and `Required checks`, all
    left blank) and three checkboxes.
  evidence:
  - path: src/orqlet/workflow/pr_template/workflow-section.md
    lines: 1-21
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e87889ffe3b052a4eeef5b17fa3bbb614b4b423dc8bcee1a21edb106cd47e22a
- id: A-12
  kind: flow
  statement: '`stack_of_profile` turns the profile''s technologies, framework names, project kind and
    support level into the stack that `resolve_for` uses to pick standards packs. `compose` executes `del
    profile`, with the comment that the profile''s effect is already in `resolution` and `profile_bytes`.'
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: 77-131
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 68c840bb488442cb5d3e41ecace574783fede2f47e843d6a6f3f5037ff614e70
- id: A-13
  kind: structure
  statement: '`data_files` writes the profile (`PROFILE_PATH`) and the knowledge configuration (`KNOWLEDGE_PATH`)
    as `seeded` files. The knowledge configuration is built with `KnowledgeConfig` and no sources, under
    the comment "Empty on purpose: a team opts in by naming where its knowledge lives and where drafts
    may go".'
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: 201-261
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: f472a7a7d36d38cebc24221ac7cfcb66cc0b612dfda35da3a4a620219ef2b5a5
- id: A-14
  kind: flow
  statement: '`answer_profile` accepts only keys in `ANSWER_KEYS` (ORQ-E160). It refuses `facts.python`
    and `facts.package_manager` when they were read with evidence (ORQ-E161) and refuses answers that
    change nothing (ORQ-E162). A change to an approved profile withdraws the approval (ORQ-I070). `approve_profile`
    needs a one-line reviewer name (ORQ-E163) and refuses a second approval (ORQ-E164). It records `reviewed_by`
    and `reviewed_at`. Both write the profile and the lock through `_commit` and `apply_plan`.'
  evidence:
  - path: src/orqlet/application/usecases/profile_edit.py
    lines: 40-189
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: be738f399dfd0fada63cc6bfc97be61e9495d5ed80c81f0479854cbec5e6102e
- id: A-15
  kind: operation
  statement: '`_profile_findings` raises ORQ-W180 when the profile is not approved. It raises ORQ-W181
    when `open_questions` is not empty, listing the ids and telling the person to answer with `orqlet
    profile answer KEY=VALUE`.'
  evidence:
  - path: src/orqlet/application/usecases/diagnose.py
    lines: 313-335
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 45ea4ba362adc0ca6acb68c5d512b43693a6e166e2685ff4efadd6214a6bddf4
- id: A-16
  kind: operation
  statement: The `orqlet-onboard` skill tells an agent to read the ORQ-W180 and ORQ-W181 findings of `orqlet
    doctor` and to write each unknown as a question without inventing "a branch naming rule or a commit
    convention". It then asks one batch, previews with `orqlet profile answer KEY=VALUE --dry-run` and
    applies with `--yes`. It leaves `orqlet profile approve` to the person.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-onboard/skill.md
    lines: 2-17
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e1d943288b38b5b1c95929574c5358d37ced7345701299f7effa405003b15a48
- id: A-17
  kind: structure
  statement: 'The profile of this repository has `status: draft`. Its repository section holds `target_branch`
    with `answered_by` maintainer, and `branch_naming` and `commit_convention` as questions with no value.
    It also holds the template status `team-template-unknown`, and `reviewers` and `merge_strategy` as
    the text unknown.'
  evidence:
  - path: .orqlet/project-profile.yaml
    lines: 10-51
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 46726e5f82d2cbe3ffc924b487549abd27ce18a3c11ffc4cec56f31f12b89d6d
- id: A-18
  kind: test
  statement: The tests assert that with several templates the choice is never made for the maintainer
    (ORQ-W050, both files untouched). They assert that `repository.pull_requests.template.targets` picks
    the file that receives the blocks. They also assert that a pack's `pr-template` asset is distributed
    unchanged with `status` provisioned.
  evidence:
  - path: tests/unit/application/test_init_project.py
    lines: 499-555
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 87db61457ae14fe333a9d8984237b1606735f525f819bc7b3e03e0f9504f5241
- id: A-19
  kind: flow
  statement: Upgrade calls `compose` with the profile's enabled clients, `_prompts_dir(inst)` and `pr_targets`
    taken from `inst.profile.repository.pull_requests.template.targets`. It passes the profile file's
    current bytes as `profile_bytes` and plans against `inst.recorded`.
  evidence:
  - path: src/orqlet/application/usecases/upgrade.py
    lines: 97-115
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: d5c1c22c351f8da25ed42a22f24d61b60c945cdf115a47aeccd3680abf069b65
- id: A-20
  kind: flow
  statement: '`_target_branch_commit` reads `profile.repository.target_branch` and resolves the remote-qualified
    branch name and then the plain name to a commit for the review merge base. When none is found, the
    binding reports that the target branch is not known to this clone and asks for `--base`.'
  evidence:
  - path: src/orqlet/application/usecases/binding_inputs.py
    lines: 118-147
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: baa88952ea248b9bbae2d3f9db980f52e300f897f8553c3aa91b697d1c2359ca
- id: A-21
  kind: interface
  statement: '`ScopedRule` (`name`, `description`, `paths`, `body`) and `ClientSkill` (`name`, `description`,
    `body`, `references`) are inputs of a `RenderRequest`, which also holds `baseline_body`, `commands`
    and `roles`. Each adapter implements `render` and returns a `RenderResult` of `files` and `limits`.'
  evidence:
  - path: src/orqlet/application/ports/instruction_adapter.py
    lines: 37-105
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 4848384008e22c8238655b21b3b8ace98e6532472fb21f90b96e22efe1a8979a
- id: A-22
  kind: flow
  statement: Composition builds one request with `build_render_request`, renders it with the adapter of
    every enabled client, merges the results with `merge_rendered` and drops every path in `released`
    from `desired`.
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: 113-131
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 27cc92ae47af88a68cbc65f3b98215e5b48adc509e93859317cc9ac6e303cc83
- id: A-23
  kind: interface
  statement: 'The Claude Code adapter returns the files of `agents_block`, `claude_bridge`, `claude_rule`,
    `claude_command`, `claude_skill_files` and `claude_role`. Its only recorded limit is `ORQ-L001`: behaviour
    follows published documentation of 2026-10 and was not observed with a real client version.'
  evidence:
  - path: src/orqlet/adapters/clients/claude_code.py
    lines: 15-34
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 09391a883f97b8f215dec4101132db1c09b4daa2b7612486dd9cf2e8c5998e0a
- id: A-24
  kind: interface
  statement: '`claude_rule` writes `.claude/rules/orqlet-<name>.md` with a `paths` list in the front matter.
    `cursor_rule` writes `.cursor/rules/orqlet-<name>.mdc` with `description`, `globs` and `alwaysApply`
    set to false, and a rule with no paths raises an error because it would load for every task.'
  evidence:
  - path: src/orqlet/adapters/render/rules.py
    lines: 17-44
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 8018b980119eae85b249fbd1fce8776f95284542a44efa0302f0c2db756703c8
- id: A-25
  kind: interface
  statement: The Codex adapter returns `agents_block`, the skill files, `codex_sidecar` and `codex_role`
    files. It adds `ORQ-L002` (no per-path rules; an agent reads them with `orqlet standards for`) when
    `request.scoped_rules` is set, and `ORQ-L003` (no commands written) when commands exist.
  evidence:
  - path: src/orqlet/adapters/clients/codex.py
    lines: 19-53
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e3ef4d29f8794357e523c7834c8e6a9d55a00d26cc480026f6fb8c463431882c
- id: A-26
  kind: interface
  statement: The Cursor adapter returns `agents_block`, `cursor_rule`, `cursor_command`, the skill files
    from `agents_skill_files` and `cursor_role` files. It records `ORQ-L001` (the `globs` format of rule
    files is unverified) and, when skills exist, `ORQ-L004` (Cursor also reads `.claude/skills`, so a
    skill may be listed twice; documented, not observed).
  evidence:
  - path: src/orqlet/adapters/clients/cursor.py
    lines: 15-41
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: af9e70cbba771f1915827b7eb93b262b835f56ca196772e6a74aca78cd13e15e
- id: A-27
  kind: flow
  statement: Only the workflow rule and every rule of level `Level.MUST` whose `scope.paths` is not empty
    become scoped rule files. Other rules are not written as files and an agent reads them with `orqlet
    standards for`.
  evidence:
  - path: src/orqlet/application/usecases/render_request.py
    lines: 49-80
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2e0018e6f432c4f0077aa8b4c54a78538dafc9c6112179cb9d49332c9b828cc0
- id: A-28
  kind: flow
  statement: '`_pack_rule` builds the file body from the rule id, level and text, adds `Roles:` and `Phases:`
    lines when the scope has them and a `Source:` line. The file takes the sorted scope paths, the description
    made of the rule id and its text, and class `FileClass.GENERATED`.'
  evidence:
  - path: src/orqlet/application/usecases/render_request.py
    lines: 133-148
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 378cbf1c2dc7c0ab14f4fbc57a4c579709a8c80c00ebe6aec2b607a7839b958d
- id: A-29
  kind: structure
  statement: A `Rule` has `id`, `level`, `waiver`, `scope` (`paths`, `roles`, `phases`), `enforcement`,
    `check_ref`, `text` and `override`.
  evidence:
  - path: src/orqlet/application/contracts/standards_pack.py
    lines: 59-73
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 21e825559bbd00f0f6e7d41c5c120138d73b61d2d39b1b2d60d511acaa29c018
- id: A-30
  kind: flow
  statement: '`load_skills` builds one `ClientSkill` per `skills/<name>/skill.md` of the workflow package.
    The front matter needs `name` and `description`, `name` must equal the directory, the body goes through
    `render_steps`, and files under `references/` are attached.'
  evidence:
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 104-137
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 226f4c3774d9a87505f236679a5afda0be17d1cc49e7e8254580c25e8711afef
- id: A-31
  kind: interface
  statement: Claude Code skills are written to `.claude/skills/<name>/SKILL.md`. Cursor and Codex both
    read `.agents/skills/<name>/SKILL.md`, so one file is rendered and `merge_rendered` keeps one. `codex_sidecar`
    adds `agents/openai.yaml` with `allow_implicit_invocation` set to false.
  evidence:
  - path: src/orqlet/adapters/render/skills.py
    lines: 1-40
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 194f653dffb7324eb9894d858cea715b3eb4a50d3790207e048cdfcc094f6cea
- id: A-32
  kind: structure
  statement: Owner modes are `orqlet`, `shared-block`, `shared-entry`, `seeded` and `user`. File classes
    are `protected`, `generated` and `optional`.
  evidence:
  - path: src/orqlet/domain/ownership.py
    lines: 6-17
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 326642e1474dca6f66703a27a714be18bebe058e3d0dc4fceeb87dc3fbc6486b
- id: A-33
  kind: flow
  statement: '`classify` returns `SEEDED_KEEP` for `OwnerMode.USER`. For `OwnerMode.SEEDED` it never overwrites
    an existing file: changed seed text gives only `SEEDED_PROPOSAL`, and a file the team deleted is not
    brought back. A hand-edited protected file is `TAMPERED`.'
  evidence:
  - path: src/orqlet/domain/classify.py
    lines: 28-74
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: a8548a4c64a377264a1039f2da26e0c4c2255de2eca2387a47a08c933dd899cd
- id: A-34
  kind: flow
  statement: '`seed_files` turns every workflow file under `seeds/prompts/` into a file below the standards
    folder (`.prompts` by default) with owner `OwnerMode.SEEDED` and no file class.'
  evidence:
  - path: src/orqlet/adapters/render/prompts_seed.py
    lines: 12-31
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 96f74de17617920152e8f3877d7c7c757a95c81de160aa6ada97249e7678460c
- id: A-35
  kind: structure
  statement: The seeded prompts README says the team owns the folder and Orqlet will not change or remove
    the files. An agent loads it with `orqlet standards for`, a standard is added as a rule in `rules.yaml`,
    and longer explanations go in Markdown files named from the rule.
  evidence:
  - path: src/orqlet/workflow/seeds/prompts/README.md
    lines: 3-8
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 7c13ccd189ee58d6fc1bb96540c8a527d6a26ae2ccfc4969df764ea1b0334e0f
- id: A-36
  kind: flow
  statement: '`own_layers` returns the rules file of the standards folder (source `prompts`) and the file
    at `PROJECT_RULES_PATH` (source `project`). Both are optional, and a broken file is an error that
    names it.'
  evidence:
  - path: src/orqlet/application/usecases/standards_for.py
    lines: 183-197
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2362b54474e5f0b4aa0d2bece075c457c9c430823235bf424f465d119655573a
- id: A-37
  kind: structure
  statement: A pack manifest has `rules`, `baseline`, `references`, `assets` (kind `pr-template` or `prompts-scaffold`),
    `provenance` (`source_url`, `applicable_version`, `retrieved`) and `applies_to`, which takes `languages`,
    `project_types`, `frameworks`, `technologies` and `python`.
  evidence:
  - path: src/orqlet/application/contracts/standards_pack.py
    lines: 12-56
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: bf69a2f594092d2f9725d958182524bc7ac39782048a4d828ba217ce017cfcae
- id: A-38
  kind: flow
  statement: '`DirectoryPackSource` reads `pack.yaml`, each file listed in `manifest.rules`, the optional
    `manifest.baseline` text and each declared asset, whose content must match the `sha256` of the manifest.'
  evidence:
  - path: src/orqlet/adapters/standards/pack_source.py
    lines: 18-80
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 1df11759af0971893c4e08b74c88d881e01fd39b6ceeb0ac7a8aae17cc34f04e
- id: A-39
  kind: flow
  statement: A pack applies when its `languages`, `project_types` and the union of `frameworks` and `technologies`
    (names compared in lower case) match the `Stack`. Otherwise the pack is skipped with a reason.
  evidence:
  - path: src/orqlet/application/usecases/standards_for.py
    lines: 165-175
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 47158b8cb6a7f25af039f6ce3fd5afe669a64c9bf125a08398160139c65d7669
- id: A-40
  kind: dependency
  statement: '`technology_scanners` returns `PythonTechnologyScanner`, `GoScanner`, `RustScanner`, `NodeScanner`
    and `ContainerScanner`; the docstring says adding an ecosystem is adding one class there.'
  evidence:
  - path: src/orqlet/interface/cli/wiring.py
    lines: 63-71
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 4e8edcbafe7809e47622c4adb050bbb2a417a98f1d208c832cc6d4816dbbe02b
- id: A-41
  kind: structure
  statement: The managed folders are `.claude/rules`, `.claude/agents`, `.claude/skills`, `.cursor/rules`,
    `.cursor/agents`, `.agents/skills` and `.codex/agents`. The name prefix `orqlet-` is reserved.
  evidence:
  - path: src/orqlet/application/usecases/diagnose.py
    lines: 31-40
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 64cded7346010348e3ffd44861dc44504764bbc6193ef128dea5e80a7ceb4f9c
- id: A-42
  kind: interface
  statement: '`agents_block` writes the baseline as a managed block of `AGENTS.md` (owner `OwnerMode.SHARED_BLOCK`,
    class `FileClass.PROTECTED`). `claude_bridge` writes `.claude/CLAUDE.md` with the import `@../AGENTS.md`.'
  evidence:
  - path: src/orqlet/adapters/render/instructions.py
    lines: 20-50
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2224309600d79153698c8da2dc2ef6a6e19c3cf7a12db444f2cce6eabd1e043d
- id: A-43
  kind: flow
  statement: 'The workflow rule is scoped by a meta file with `schema`, `name`, `description` and a `paths`
    list of seven globs: `.orqlet/**`, `.claude/**`, `.cursor/**`, `.agents/**`, `.codex/**`, `.mcp.json`
    and `AGENTS.md`.'
  evidence:
  - path: src/orqlet/workflow/rules/orqlet-workflow.meta.yaml
    lines: 1-11
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 4daa1516e41e7d9af633994f91b45e5f1d5984fcd5a4ff3cde1832cc9d37ef65
- id: A-44
  kind: flow
  statement: An integration test adds rule `TEAM-001` with scope paths to the seeded `rules.yaml`; the
    standards command then serves it, and after an `upgrade` a Claude Code rule file and a Cursor rule
    file for `TEAM-001` exist while the rules file keeps the team's text.
  evidence:
  - path: tests/integration/test_prompts_seed.py
    lines: 94-120
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 5b06e4bc3251541ab309327f3b99608eccfd531b6117bde108f32c644be141f8
- id: A-45
  kind: flow
  statement: '`release_file` refuses with `ORQ-E141` a file whose recorded class is `FileClass.PROTECTED`
    and with `ORQ-E142` a file that was seeded.'
  evidence:
  - path: src/orqlet/application/usecases/release.py
    lines: 46-65
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 66cf39ac4040b57f47eed3584c7c21e51a862a5d530597c523a8e9d8b21e3502
- id: A-46
  kind: structure
  statement: The repository's own knowledge configuration has schema `orqlet.knowledge/v2` and an empty
    list for each of `sources`, `exclude` and `write_scope`.
  evidence:
  - path: .orqlet/knowledge.yaml
    lines: 1-4
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 4af3bc53e7dbca20b4c498628022c7825c40b22b69621e36567b080c3eaf4e38
- id: A-47
  kind: structure
  statement: A `KnowledgeSource` has `kind` (`adr`, `module-card`, `docs` or `standards-reference`), `scope`
    (`project`, `team` or `company`), `globs` and an optional `pack`. A `WriteScope` has `globs` and `kinds`
    (`adr`, `module-card` or `docs`), each with at least one entry.
  evidence:
  - path: src/orqlet/application/contracts/knowledge_config.py
    lines: 15-28
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ecf8841a39ca70b051f8689a8e2fcf7937d3d5e0d53045756ee29494a9b94223
- id: A-48
  kind: structure
  statement: '`KnowledgeConfig` has `sources`, `exclude`, `write_scope` and an optional `index` block
    whose `IndexConfig` has `views`, `target_branch_ref`, `tokenizer`, `refresh_policy` and `generations_kept`.
    The module docstring says the `index` block belongs to M3 and is accepted and ignored.'
  evidence:
  - path: src/orqlet/application/contracts/knowledge_config.py
    lines: 3-44
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: cba40f8b14dde278e8f293a011a521b473b85511f8d9560c40dbd8dc320ee178
- id: A-49
  kind: operation
  statement: 'The renderer builds an empty `KnowledgeConfig`. Its comment says this is on purpose: a team
    opts in by naming where its knowledge lives and where drafts may go.'
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: 231-232
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 8f7152709b4c35e36c653acd15c02617a4aedc8db6bb109fb9c6a16058773140
- id: A-50
  kind: flow
  statement: '`_knowledge_globs` returns as include globs the `globs` of every source whose `scope` is
    `project` plus every `write_scope` glob, and returns `exclude` as the exclude globs. With no configuration
    both are empty.'
  evidence:
  - path: src/orqlet/application/usecases/knowledge_impact.py
    lines: 191-197
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: b64373fff74a131770c4a7b831861a11dfb3abaa06b99bcab3a40affbe55dfcd
- id: A-51
  kind: flow
  statement: '`_pre_draft_documents` reads from the merge-base tree the files that end with `TEXT_EXTENSIONS`,
    match an include glob or a glob the plan requests, and match no exclude glob. When the include list
    is empty it adds a note that no knowledge sources are configured and that only the plan''s knowledge
    scope names documents.'
  evidence:
  - path: src/orqlet/application/usecases/knowledge_impact.py
    lines: 200-222
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 5998c020acb254ec096ab2ee271971357768d3072560a32bd2ec089c57432463
- id: A-52
  kind: structure
  statement: A `ModuleCard` (`orqlet.module-card/v1`) has `id`, `kind` (`same-repo-module`, `released-package`
    or `deployed-service`), `summary`, `use_when`, `avoid_when`, `interface` (`python` with `import_path`
    and `public_symbols`, or `service`), `interface_digest`, `examples`, `status`, `owner`, `requirement_level`,
    `must_consider`, `refs`, `paths` and `symbols`.
  evidence:
  - path: src/orqlet/application/contracts/module_card.py
    lines: 16-65
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e6e001e80913fafb561ca960fbb85ad669ab148b10bfb6ea4dc5e030fe72a863
- id: A-53
  kind: flow
  statement: The analysis adds a `reference` candidate for each pre-draft document that names a changed
    path or a public-API name. It then adds card-digest candidates, a `public-symbol` candidate for each
    added, removed or changed public symbol, candidates for implemented expected changes and docs-map
    candidates, keyed by id and sorted.
  evidence:
  - path: src/orqlet/application/usecases/knowledge_impact.py
    lines: 104-123
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 5fe39455d8dadeee775fcac92eeea69c3680e9b5cfe3d5999d2f6ac149da48f5
- id: A-54
  kind: flow
  statement: 'References are found by exact match only: repository-relative paths in Markdown link targets
    and inline-code spans, entries of fenced `orqlet-ref` blocks and qualified Python names in inline-code
    spans. The docstring says the analysis calls no model and that a prose mention in any other form is
    not found.'
  evidence:
  - path: src/orqlet/domain/knowledge.py
    lines: 1-8
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 35f9b54d845fb74fc8fcbdbd9b7f0c93c015bf187affb194bdde87fba252b7f3
- id: A-55
  kind: flow
  statement: '`KnowledgeScope` `contains` a path only if it is not in `FORBIDDEN_KNOWLEDGE_FILES`, not
    under `FORBIDDEN_KNOWLEDGE_PREFIXES`, ends with one of `DOCUMENTATION_EXTENSIONS` and matches both
    a glob of the plan (`requested`) and a glob of `allowed`. `knowledge_scope` fills `allowed` from the
    `write_scope` globs, so with no `write_scope` nothing is in scope, and `read_knowledge_config` returns
    `None` when the file is missing or cannot be loaded.'
  evidence:
  - path: src/orqlet/application/usecases/binding_inputs.py
    lines: 150-189
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 34bfdb20d5abd6ea609337ed6ca533265995f151f4775e5f05f07290a733740c
- id: A-56
  kind: interface
  statement: '`knowledge_app` has one command, `impact`, which takes a task and a phase and calls `knowledge_impact`.
    Its help says the analysis reads the committed tree only, calls no model and uses no network.'
  evidence:
  - path: src/orqlet/interface/cli/commands/knowledge.py
    lines: 16-39
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e7df728f3130c4fa872442e75001a1b661435f327aa679a87f7bb82ec6d79c5c
- id: A-57
  kind: interface
  statement: The command `validate knowledge` takes one record file and calls `validate_knowledge`. Its
    help text describes the check as every candidate resolved and evidence that resolves.
  evidence:
  - path: src/orqlet/interface/cli/commands/validate.py
    lines: 165-181
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ca8d2f816be88726a7191997d9fdeb20c252779f68fb4a8b0361248d9efcdf54
- id: A-58
  kind: structure
  statement: A `KnowledgeImpact` record has an `outcome` of `updated` or `no-impact`. `updated` needs
    at least one add, correct, supersede or remove entry and no `no_impact` block, and `no-impact` needs
    the `no_impact` block and lists every candidate as unaffected.
  evidence:
  - path: src/orqlet/application/contracts/knowledge_impact.py
    lines: 119-146
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: f7d4e103e25d1e1914d9564f7132ac6d1b28bf28de542f626e992265ce2bac99
- id: A-59
  kind: operation
  statement: Step 6 of the implement skill tells the agent to run `orqlet knowledge impact <task> <phase>`,
    resolve every candidate with evidence that resolves, write the knowledge drafts inside the knowledge
    scope, save the record and run `orqlet validate knowledge <record>`. It allows a justified no-impact
    outcome and says not to write a document to satisfy the rule.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: '16'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ac60b679142feec8c85a486d44653183afd6aa7e9db69a861e7babd1967f189c
- id: A-60
  kind: operation
  statement: The plan format says `knowledge_step` is always `required` and that `knowledge_scope` may
    only cover documentation files outside agent configuration and workflow files.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-plan/references/plan-format.md
    lines: 54-56
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: de27ada005136e8e353ec69038d6d406941522d137926700804c1f0467bdfc89
- id: A-61
  kind: structure
  statement: The README status section lists `knowledge impact` among what is built and says the knowledge
    index and module catalogue are not built yet.
  evidence:
  - path: README.md
    lines: 31-36
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 4d78bddd9252c6316447da6928d15a74a024fcd0e314c2fd98bb114a25860237
- id: A-62
  kind: structure
  statement: The Typer application `app` is created with `no_args_is_help=True`. The commands init, upgrade,
    rollback, sync, doctor, explain and release are attached with `app.command`. The groups profile, standards,
    validate, gate, evidence, knowledge and review are attached with `app.add_typer`.
  evidence:
  - path: src/orqlet/interface/cli/app.py
    lines: 27-47
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 414be91c6a0570692f540ffb6cc9b7eb563307372f306f8a18018fcab9721b16
- id: A-63
  kind: interface
  statement: '`IMPLEMENTED_COMMANDS` holds 22 names: init, upgrade, rollback, sync, doctor, explain, release,
    profile answer, profile approve, standards for, validate as-is, validate design, validate plan, validate
    ledger, gate status, evidence cite, evidence hash, knowledge impact, review prepare, validate review,
    validate test and validate knowledge. `PLANNED_COMMANDS` is an empty frozenset whose comment says
    nothing is planned at the moment. The set exists so that a skill step marked `requires:` is dropped
    when its command is not listed.'
  evidence:
  - path: src/orqlet/application/usecases/capabilities.py
    lines: 1-39
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: c2471b19295e485b5b00e41b536f28003a410460e5c3a7578474d56a1e50fbad
- id: A-64
  kind: test
  statement: '`registered_commands` walks the Typer app, including nested groups, and strips a `_command`
    suffix from function names. The test `test_the_list_of_implemented_commands_matches_the_application`
    asserts that the result equals `IMPLEMENTED_COMMANDS`, so a command added to the app but not to the
    set, or the reverse, fails.'
  evidence:
  - path: tests/integration/test_validate_cli.py
    lines: 196-209
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ae49115384fc2b4ca8cb8776176bad372e859e9832240186f2062769d8f01658
- id: A-65
  kind: flow
  statement: '`_commands` makes one `ClientCommand` for each `commands/<name>.md` path of the packaged
    workflow, in name order. It rejects a name that does not match `[a-z0-9][a-z0-9-]*` and takes the
    description and body from `parse_command`.'
  evidence:
  - path: src/orqlet/application/usecases/render_request.py
    lines: 99-117
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2f4ab26a8073fd3cc8e60b75f2e08e5d5ec9a1b020f6724ea633bf548de65ad9
- id: A-66
  kind: flow
  statement: '`claude_command` renders `.claude/commands/orqlet-<name>.md` with a description in the front
    matter. `cursor_command` renders `.cursor/commands/orqlet-<name>.md` as plain Markdown. Both give
    a `RenderedFile` with `OwnerMode.ORQLET` and `FileClass.GENERATED`. `_command_name` refuses a name
    outside lower case letters, digits and hyphens.'
  evidence:
  - path: src/orqlet/adapters/render/rules.py
    lines: 58-92
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: b74d020c90d4c981ab4ae6cd675ca7d9117ce916b794721bd910df5914235299
- id: A-67
  kind: interface
  statement: '`CodexAdapter` adds the limit `NO_COMMANDS_LIMIT` (`ORQ-L003`, ''Orqlet does not write commands
    for Codex in this release'') when `request.commands` is not empty.'
  evidence:
  - path: src/orqlet/adapters/clients/codex.py
    lines: 24-44
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 5e6552c99e9bdce8af39596c3cf4b1c4203cd65afc69eb9228757268e7e46ae0
- id: A-68
  kind: structure
  statement: The composition root has three builders. `build_services` gives project files, loader and
    scanners. `build_validate_services` gives project, `GitVcs`, loader and the packaged workflow. `build_init_services`
    fills the lifecycle services with a `YamlWriter`, the three client adapters (claude-code, codex, cursor),
    journal, backup and lock stores in the user data directory, and `TtyPrompter(sys.stdin, sys.stdout)`.
    `build_packet_store` gives review packets a folder in the data directory.
  evidence:
  - path: src/orqlet/interface/cli/wiring.py
    lines: 54-135
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 9e5e12fdc87de376f972b7c9196b311ebcbefccd12154b1c8cfa0dfc4c55e40d
- id: A-69
  kind: flow
  statement: '`apply_plan` holds `lock.hold()` and orders the writes with the `last` ones at the end.
    It calls `_verify_unchanged`, which raises `PlanStale` when a file differs from what the plan was
    made from. It backs up every file that existed and marks earlier open changes `superseded`. It records
    the change with `journal.start`, writes with `write_atomic` or deletes each file, calls `journal.mark_done`
    per file and `journal.finish` at the end.'
  evidence:
  - path: src/orqlet/application/usecases/apply_plan.py
    lines: 25-77
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 76aef1363f9abc4547ee48a5e93e762154ac0d2b86676560a7e5b302fb36163a
- id: A-70
  kind: structure
  statement: '`OwnerMode` has the values orqlet, shared-block, shared-entry, seeded and user. `FileClass`
    has the values protected, generated and optional.'
  evidence:
  - path: src/orqlet/domain/ownership.py
    lines: 6-17
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 326642e1474dca6f66703a27a714be18bebe058e3d0dc4fceeb87dc3fbc6486b
- id: A-71
  kind: operation
  statement: '`init` returns `previewed` for a dry run. When the plan is not approved it returns `previewed`
    if the prompter is interactive and otherwise `needs-input` with finding `ORQ-E115`. After approval
    it calls `services.vcs.init_repository(branch)` when a repository is needed, then `apply_plan` with
    `command="init"`. The result carries `open_now`, computed by `open_questions(profile)`, in every status.'
  evidence:
  - path: src/orqlet/application/usecases/init_project.py
    lines: 177-214
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: d290213c0ec12a366cf92d39d645056a257d981a092e49dad3a3483f6e4d3128
- id: A-72
  kind: operation
  statement: '`upgrade` renders again with `compose` and plans with `plan_changes` against `inst.recorded`.
    It warns with `ORQ-W090` when changes are staged and returns `up-to-date` for an empty plan or `available`
    when only checking. For a dry run or without approval it returns `previewed` on a terminal, otherwise
    `needs-input` with `ORQ-E115` (''run again with --yes''). Otherwise it calls `apply_plan` with `command="upgrade"`
    and reports the `resumed` change ids.'
  evidence:
  - path: src/orqlet/application/usecases/upgrade.py
    lines: 97-181
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: bfc1d372204759c833477b5142b76d5b1a7dea5e8c13a7e0a9d4f111e72852e1
- id: A-73
  kind: operation
  statement: '`_commit` builds a `ChangePlan` directly, with two writes. One is `PROFILE_PATH` and the
    other is `LOCK_PATH` with `last=True`, and the profile is recorded with `OwnerMode.SEEDED`. A dry
    run returns `previewed`. Without approval an interactive prompter gives `previewed`, otherwise `needs-input`
    with `ORQ-E115`. Otherwise it calls `apply_plan` with the given command. `_confirmed` asks `prompter.confirm`
    ''Change the project profile?'' with a default of False and treats `NoAnswerAvailable` as no.'
  evidence:
  - path: src/orqlet/application/usecases/profile_edit.py
    lines: 138-199
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: c0afa76a26465307c2d5aa2c4c4b509774e21a35afc250d1f384c0f5bd227db4
- id: A-74
  kind: flow
  statement: '`ANSWER_KEYS` has nine keys: facts.python, facts.package_manager, facts.frameworks, project.kind,
    structure.test_runner, repository.target_branch, repository.branch_naming, repository.commit_convention
    and technologies. `questions_for` asks ''Which branch do pull requests target?'', a branch naming
    rule and a commit message convention when their value is `None`. `collect_answers` takes a value given
    with `--answer` first, asks only when `prompter.interactive` is true, and stops asking when `NoAnswerAvailable`
    is raised.'
  evidence:
  - path: src/orqlet/application/usecases/init_questions.py
    lines: 26-122
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 030f8391596bb8b90db6ec0b87eb889867b74c38e0f6493c6833ab666f29e398
- id: A-75
  kind: structure
  statement: The profile contract keeps branch rules as `Repository` fields `target_branch`, `branch_naming`
    and `commit_convention`. It keeps pull-request facts in `PullRequests`, whose `reviewers` and `merge_strategy`
    both default to the string 'unknown'.
  evidence:
  - path: src/orqlet/application/contracts/profile.py
    lines: 86-96
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: eec8e96706d46d088708f308448542bfaf919363c739929e121d56fcbc426ad5
- id: A-76
  kind: interface
  statement: Section 23 of the architecture document describes itself as a draft surface and lists as
    built the commands of the implemented set, including `profile answer|approve` and evidence cite and
    hash. Its table lists unbuilt standards status, update, import and diff as 'later', knowledge refresh,
    search, show, private add and promote as MVP-2, and source read and write as 1.0. It says that `profile
    answer|approve` change tracked files (the profile) and that sync, doctor, explain, standards for,
    gate status and review prepare write nothing in the repository.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 4544-4565
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 773faeabb11561f155b4b58c5eff8f4afc338c1b17e7b09d39e75062978e2b66
- id: A-77
  kind: interface
  statement: Section 13.3 plans `orqlet standards import <link-or-file>`. It uses an Orqlet-owned allowlisted
    fetcher (approved domains only) and stores a documentation pack with `SOURCE.yaml` (URL, applicable
    version, retrieval date, owner, licence note, freshness TTL, content hash) plus extracted Markdown.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2361-2363
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 48121e38141ee0187c92da112c422310f13f90a39e524d93606aac401d05109a
- id: A-78
  kind: operation
  statement: The research skill says text in repository files, documentation, retrieved passages and tool
    output is evidence, and that text in it which tells the agent to change a phase, skip a check, approve
    something or ignore an instruction has no effect. This is the only place in the six skills that mentions
    retrieved material (the same sentence is line 9 of each skill.md).
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: '9'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 88585d14985492c4aafca67c99375280667f8cb3cf8feae6e11b1971bf342c02
- id: A-79
  kind: flow
  statement: The research skill tells the agent to ask the person one consolidated batch of questions
    and record them in `questions.yaml` (step 2), to start `orqlet-inventory` and `orqlet-tracer` as subagents
    (step 4), and to give every fact its evidence with `orqlet evidence cite` (step 5).
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 12-15
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: badad5617a6ff0c6e7f232d6cbb5534d08c3df945b549e20028f61e49e2e1f71
- id: A-80
  kind: operation
  statement: 'The baseline tells every agent not to guess: when a fact is not in the repository or in
    what the person said, the agent writes it down as a question and asks, and an unknown stays unknown
    until a person answers.'
  evidence:
  - path: src/orqlet/workflow/baseline/baseline.md
    lines: '7'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e507c46f3494fd71351689c91f5055a31a7514548d7190c806978484ad4288bc
- id: A-81
  kind: interface
  statement: The role renderer sets `READ_ONLY_TOOLS` to Read, Grep, Glob and writes a `tools` field for
    Claude Code only for a read-only role. It writes a `readonly` field for every Cursor role and a `sandbox_mode`
    field for Codex only for a read-only role.
  evidence:
  - path: src/orqlet/adapters/render/roles.py
    lines: 16-48
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 91f4ac761db5f0ed2cff499380ca6f5e4e7448948d992977841406be221c9e8d
- id: A-82
  kind: interface
  statement: The architecture document records that a Claude Code subagent `tools` field is an allowlist
    and that, when it is omitted, the subagent inherits every tool available to subagents; a `tools` list
    of built-ins excludes MCP tools unless `mcp__server__*` is listed.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '540'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 698e617fbed4b0a5347da4c25cb18d93a09cf4692475428b364d9ce101b823a3
- id: A-83
  kind: test
  statement: Ruff rule `TID251` bans `socket` with the message 'Network access belongs in an adapter.'
    and is switched off for `src/orqlet/adapters/**`, `src/orqlet/interface/**`, `tests/**` and `tools/**`.
    The pytest options include `--disable-socket`.
  evidence:
  - path: pyproject.toml
    lines: 45-71
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 07d9c13671f4e29a53479be30ec9491a05726c6f450ed7f9d2fbea60c791e16e
- id: A-84
  kind: dependency
  statement: Two import-linter contracts of type `forbidden` set `source_modules` to `orqlet.domain` and
    to `orqlet.application`, and list `socket`, `http`, `urllib` and `subprocess` among the modules they
    may not import.
  evidence:
  - path: pyproject.toml
    lines: 96-112
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e2ca759e4b0637e238407ddc17f82181ecf8a83868ada2a1026a995fed555fec
- id: A-85
  kind: test
  statement: Standards rule ORQLET-TEST-001 says unit tests use the fakes in tests/fakes, never touch
    the network, and that the suite runs with sockets disabled; its check is `uv run pytest`.
  evidence:
  - path: .prompts/rules.yaml
    lines: 111-118
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 45e6a5ca5bf897461333cce429c40b55473c67c194b6d5c0689457cc06a9eb10
- id: A-86
  kind: interface
  statement: '`GitRunner` runs only the subcommands in `ALLOWED_SUBCOMMANDS`: `rev-parse`, `for-each-ref`,
    `rev-list`, `merge-base`, `ls-files`, `ls-tree`, `cat-file`, `diff-tree`, `diff-index`, `write-tree`
    and `check-ignore`. Any other subcommand raises `VcsError`.'
  evidence:
  - path: src/orqlet/adapters/git/git_runner.py
    lines: 18-79
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 65da65e841dc7cfbeb8a1cb865ab36303eae28e683736a9ce651a3db4940ba15
- id: A-87
  kind: operation
  statement: '`orqlet gate status` is documented as read-only and offline; because approval needs evidence
    from the code host, its verdict with a task is always `NOT_RUN`.'
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 1-8
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 202e8d4e89bf4109ca061daac43e118a03a42b75bef00cd6e55e9b36aeb1a3ce
- id: A-88
  kind: operation
  statement: The docstring of the knowledge-impact command says the analysis reads the committed tree
    only, calls no model and uses no network.
  evidence:
  - path: src/orqlet/interface/cli/commands/knowledge.py
    lines: '30'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 8c605d7b77a4c1a6d1198e0654ba3bddf51c356f3c92167a3fde6766f65590eb
- id: A-89
  kind: interface
  statement: '`cite` reads the named file at a revision with `read_at` and returns an entry of `path`,
    `lines`, `revision` and `sha256`. It reports a skip when the repository has no commit or does not
    hold the revision.'
  evidence:
  - path: src/orqlet/application/usecases/evidence_cite.py
    lines: 25-56
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 04a92d0c2436067c1c6e82a965ed625eca74614f704d11193238d220eba0b3e7
- id: A-90
  kind: flow
  statement: The AS-IS validator reads each cited file with `services.vcs.read_at(item.revision, item.path)`
    and compares the line-range hash with `check_reference`. Evidence whose revision differs from the
    bound base revision is error `ORQ-E332`.
  evidence:
  - path: src/orqlet/application/usecases/validate_as_is.py
    lines: 117-134
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 1250c1ba08a0eae18d60cce6446d6800617ac71b75f8cad87ed202fd003042e6
- id: A-91
  kind: operation
  statement: 'The mcp-or-plugins ledger records the use of the web as question Q-5 of category `access`:
    may the research read vendor documentation on the web, read-only, and store short excerpts with the
    address and the date as evidence files in the repository. The answer is ''yes, read-only with stored
    excerpts''.'
  evidence:
  - path: docs/design/mcp-or-plugins/questions.yaml
    lines: 87-104
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 7ea75277d46179e7d529c2b58f5e3aa1aaa3f59f29452efe59ac9b12aa13b9ee
- id: A-92
  kind: operation
  statement: The architecture document describes `orqlet standards import` as using an Orqlet-owned allowlisted
    fetcher (approved domains only) that stores a documentation pack with `SOURCE.yaml`. It says that
    if an endpoint is blocked by policy Orqlet reports it and stops, and that an authorised maintainer
    imports with `--from-file` when external access is unavailable.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2363-2365
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2b44ac49ceaeec2a6e7c4f6cfe0b3c968ed822b4b8f88859d32c6e44b4cc6c44
- id: A-93
  kind: operation
  statement: The architecture document's section on documentation access says Context7 is unavailable
    unless the owners approve it explicitly. It rates native client search and fetch as inconsistent (Claude
    Code has no WebSearch under Bedrock, Codex web search defaults to cached results, Cursor web tools
    not verified) and names Orqlet's allowlisted fetcher and local versioned documentation packs as the
    alternative.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2644-2653
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 43f23ca3eebba6ad5e52546ad955b484dbf77007eb733037389b5da0632153bb
- id: A-94
  kind: operation
  statement: The architecture document's skill table gives the `orqlet-onboard` and `orqlet-research`
    skills the safety note 'Read-only; no network'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 3151-3152
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: cf27eb1e09509dc92cbcc4448f887487a62bde3668132a743c9d0191884cbded
- id: A-95
  kind: interface
  statement: The architecture document's CLI surface lists `init`, `sync` (without `--fetch`), `doctor`
    (without `--live`) and `knowledge impact` as local only. It lists `standards status|update|import`,
    `sync --fetch`, `doctor --live`, `mcp inspect --live` and `gate status` among the commands that may
    use the network, and says model-mediated commands are none at any release.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4563'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: f556bde393dc9620adc6e81248b0bed9976c7959549b31cb8b7e18724bd12123
- id: A-96
  kind: structure
  statement: The standards pack manifest has a `Provenance` record with `source_url`, `applicable_version`,
    `retrieved`, `authored_by` and `review_ref`.
  evidence:
  - path: src/orqlet/application/contracts/standards_pack.py
    lines: 29-34
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 4dca6b6c89ebb323fa8115a234df61ec53f823c4fe84a8db7ffc29bec774940c
- id: A-97
  kind: flow
  statement: 'Section 9.1.1 step 2 says `init` asks the questionnaire: clients to enable, stack and versions
    from the supported-stack catalogue, package manager, project kind, frameworks, test runner, linter,
    static-analysis and build tooling, whether integration or end-to-end suites exist, the target branch,
    the code host and CI, the required integrations, and where existing guidance lives (`.prompts` or
    its equivalent). An unanswered fact stays `unknown` and is reported by `doctor`; without a terminal
    the answers arrive through `--config` or `orqlet profile answer`.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '1914'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ef955762bf7e4b243e0adfc74939fd234595c7d125230ef05e9bdc91ef91d623
- id: A-98
  kind: flow
  statement: Section 9.2 steps 2 and 3 say scanners read `CODEOWNERS`, pull-request templates, CI workflows
    and "a bounded sample of Git history for commit and branch conventions". Facts that cannot be inferred
    become consolidated questions, answered at the terminal, through `--config` or `orqlet profile answer`,
    or asked by `orqlet-onboard` in the IDE.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 1947-1948
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ba344accac338075e4298096e0aff9924c9cf6d9fa39782e1aded3fe9e8d314d
- id: A-99
  kind: structure
  statement: Section 17.2 lists the profile contents, each with a source or an explicit `unknown`, among
    them "Git branching and naming, including the target branch (`repository.target_branch`), never assumed
    to be `main`; commit conventions; PR templates, reviewers and merge strategy".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2878'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 3d2673121ba760eb128960a13f30a4d150f909b6bdc8fc311114d5604f628b7c
- id: A-100
  kind: interface
  statement: 'The profile example (Section 24.2) holds `branch_naming` as `unknown` with a question, `commit_convention`
    as detected or unknown, `reviewers` "from CODEOWNERS or unknown" and `merge_strategy: unknown`.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 4719-4726
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: c9741a55c6648c81139e1cedfcfa33e507287af27791ad5ebdd91f1bcafb378f
- id: A-101
  kind: flow
  statement: Section 19.4 item 8 says the `commit-msg` check rejects AI co-author or attribution trailers
    and "enforces the profile's commit convention". README lines 34-35 list local Git hooks as not built.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3686'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: b12e86a1bc90b81751ed1fba80e84e3c2a47063e2cd266b95f442c220d1311b0
- id: A-102
  kind: flow
  statement: 'Section 13.7 says the team pull-request template is a pack asset of kind `pr-template`;
    while it is not supplied `init` provisions only the Orqlet workflow section and reports `team-template:
    unknown`. With several template locations `init` asks which files receive the blocks (`repository.pull_requests.template.targets`)
    and never picks one itself.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2409-2419
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 855542594219c8d77264df387ced000757888030b47f9697a91f4e220c5936b1
- id: A-103
  kind: structure
  statement: Section 22 puts the knowledge index, the `orqlet-catalogue` skill, the optional `orqlet-knowledge`
    helper and the module-card commands in M3 (MVP-2). It puts external sources with the `source write`
    protocol in M6 and the optional application scaffolding (`orqlet new`) in M7 (1.0).
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 4506-4508
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 07ca85d45eeb36e50a546e85c69cf1165913dd82e7c6457a5938d269acf13ebd
- id: A-104
  kind: interface
  statement: Section 13.3 says `orqlet standards import <link-or-file>` uses an Orqlet-owned, allowlisted
    fetcher (approved domains only, preferring `.md` twins and `llms.txt`) and stores a documentation
    pack with `SOURCE.yaml` (URL, applicable version, retrieval date, owner, licence note, freshness TTL,
    content hash). The `orqlet-onboard` skill may then draft standards from the stored pack "with no web
    access required".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2363'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 51a999097e336f6285cd882aef3bc30d782ac18bda24470fd7c0ddc183ad3ba6
- id: A-105
  kind: operation
  statement: Section 13.3 calls client web tools inconsistent (Claude Code has no WebSearch under Bedrock;
    Codex web search defaults to a cache). A blocked endpoint is reported and the import stops, and without
    external access a maintainer imports approved documentation with `--from-file` and opens a pull request
    carrying the same metadata.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2365'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 22935a60fd9de6dc07c70b2611d635605d8bed3653a48f8a78efc83365f990a6
- id: A-106
  kind: flow
  statement: Section 13.1 step 5 says that at first run `init` takes "files, packs and links that the
    maintainer names" and stores them with `SOURCE.yaml`, and that the persistent `orqlet standards import`
    command "is built later". The `orqlet-onboard` skill then drafts standards for owner review only,
    each with source URL, version, retrieval date, owner and a freshness TTL.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2350'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2a05b849cd997f85aa4c5ef8730f0b9b9b12593e20ba42491183ac40fecdd334
- id: A-107
  kind: structure
  statement: The ingestion contract (Section 13.6) has fields such as `source_id`, location, owner, version,
    `freshness_ttl` and a `level` declared by the owner. Its rules say an agent's summary of a page is
    a draft architecture document, nothing becomes `MUST` without owner review, imports are stored as
    data with `SOURCE.yaml`, and unknowns stay `unknown` and are reported by `doctor`.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2390-2403
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ea95386be6cd9cfbedde4a5d43483a50c2d5a665d4bbdcd0a1088f0e2d51ca30
- id: A-108
  kind: flow
  statement: 'Section 12.8 says imported company documents do not land in `.prompts/` by themselves: `orqlet
    standards import` stores them as data under `.orqlet/docs-packs/`, and owners promote reviewed text
    into `.prompts/` or a pack by pull request.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2336'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: d50e6836a00876fff2e924e1a85aebd532e858fd31cfae2abd5a43f5d0f10739
- id: A-109
  kind: structure
  statement: Section 12.8 says that what is seeded once, at the path named by `standards_sources` (default
    `.prompts/`), includes a `README.md` with six parts, one of them a PENDING list of company content
    not supplied (security standards, database and schema standards, API standards, domain knowledge,
    the team pull-request template), and a `foundations.md`.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2313-2323
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: efab5132b0034878232a07fd4623e02a198381ce1b1e17307b31b02c65b87491
- id: A-110
  kind: flow
  statement: Section 8.11 says MUST-level standards reach the agent through generated path-scoped rules
    (`.claude/rules/orqlet-*.md` with `paths:`, `.cursor/rules/orqlet-*.mdc` with `globs`), the phase
    skills, and `orqlet standards for <path|phase|role>`. The resolver selects rules by metadata (scope,
    role, phase, language, framework), not by search.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '1572'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 6e005ef3e09c46f696cabf349741b47941ada7d6b36df2819b7da70260a413a6
- id: A-111
  kind: flow
  statement: Section 13.4 says that when the profile changes in a way no pack covers (a new framework,
    a major version), `orqlet doctor` and `orqlet upgrade --check` report it, and `orqlet standards update`
    writes a `StandardsUpdateProposal` file for the standards owner. The section describes no lookup of
    that technology.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2369'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2e4cd340e20a8cf3a2c0bd83fb7514abe9c2b84304871db9c0070548e4651d82
- id: A-112
  kind: flow
  statement: Section 9.1.1 steps 3 and 4 say the answers are compared with each pack's `applies_to` (supported,
    partly covered, or unsupported or ambiguous), `init` "never selects silently", and with no pack in
    `standards.lock.yaml` "nothing is invented and `doctor` reports the gap".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 1915-1916
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 995760699bcd31d9e23953dc2f6998e82830a3fa1d8be8583320e9c70cdc109f
- id: A-113
  kind: structure
  statement: 'Section 25.2 maps the pending company inputs to mechanisms. Cisco API documents ("documents,
    links or a repository") go through `orqlet standards import <link-or-file>` and `SOURCE.yaml`, with
    `API standards: unknown` until supplied. The `pr-template` asset stays `team-template: unknown` until
    supplied, and technology-specific practices arrive as packs whose `applies_to` names the technology.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 5103-5108
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: f54f3269797c30d58edcddd379615aa5897a6fea95441b1cd989ee9581bf324d
- id: A-114
  kind: interface
  statement: The `knowledge.yaml` example (Section 24.9) lists `sources` of kind adr, `module-card`, docs
    and `standards-reference` (read from a hash-verified pack cache), each with a scope and globs.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 4958-4964
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 34a4b515725c3544528e3d0c7e1d470cb23941990987dcbc4471619981f97348
- id: A-115
  kind: flow
  statement: Section 8.11 says the static `orqlet-catalogue` skill tells the agent to run `orqlet knowledge
    catalogue --scope <path>` and `orqlet module check <id>`, derived from committed module cards. A card's
    `must-consider` attribute only forces a reuse decision in the plan.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '1573'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 9aa5919ecc7f1b9bcedb1402858d61b3255844ebc8b190a3369aa8fe05bc31d4
- id: A-116
  kind: flow
  statement: Section 8.5 item 5 says external sources (Confluence, Jira) live in separate per-identity
    cache files with a TTL, a freshness display and an access class, and `orqlet knowledge purge --source`
    removes them.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '1529'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 36943b03d91e68992ae1605f4596862e6864a9541f778e60cb68e8758fa8b943
- id: A-117
  kind: dependency
  statement: Section 15.7 says Jira and Confluence are read through the Atlassian Rovo MCP server (OAuth
    2.1; "connectivity is vendor-documented and not tested"). Internal APIs and project-specific tools
    are "Unknown until supplied", declared in `integrations.yaml`, or placed behind an `ExternalSourcePort`
    adapter.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2635-2638
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2ef443f1c50135edb2c5df7530d6aea327b902a7ecadafa324f89256a3c46c3a
- id: A-118
  kind: operation
  statement: Section 23 classes `init` as local only "unless it is given a standards repository or URL,
    which it then fetches". It lists `standards status|update|import`, `sync --fetch`, `source read|write`
    and `gate status` as commands that may use the network, and says no command is model-mediated.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4563'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: f556bde393dc9620adc6e81248b0bed9976c7959549b31cb8b7e18724bd12123
- id: A-119
  kind: operation
  statement: The skill specification table (Section 17.10) gives the tool limits of `orqlet-onboard` and
    `orqlet-research` as "Read-only; no network". The `orqlet-onboard` row lists the steps scan facts,
    read guidance, list unknowns, ask one consolidated batch and draft the profile.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 3151-3152
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: cf27eb1e09509dc92cbcc4448f887487a62bde3668132a743c9d0191884cbded
- id: A-120
  kind: operation
  statement: The implementation plan says standards packs match on `languages` and on any technology name
    (`applies_to.technologies`). Under "Not built yet" it lists "the IDE onboarding agent skill (part
    two), the documentation importer" and scanners for Java, .NET, Ruby and PHP.
  evidence:
  - path: docs/design/orqlet-implementation/plan.md
    lines: 187-194
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 16f8c6eb778ef246f4f51211b8d4e552d16b32fddf436cf566eb202dc5794fcd
- id: A-121
  kind: structure
  statement: Decisions D-43 (`init` for new and empty projects with a questionnaire and supported-stack
    list, with `orqlet new` separate), D-45 (pull-request template as two owned blocks) and D-48 (`.prompts/`
    seeded once, then team-owned) are recorded as "Default (new)". The status column does not say built
    or planned.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 5168-5173
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e545ec7cea235b05851f7c796198cd6cea38973b1fb5d3721f003c441ae49fea
- id: A-122
  kind: structure
  statement: Claude Code scopes a rule file in `.claude/rules/` with a `paths` field in YAML front matter.
    A rule without `paths` loads for all files, and a path-scoped rule loads when Claude uses the Read,
    Write or Edit tool on a matching file.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-memory.md
    lines: '40'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 5a2e3442d0bf88158bac6062d0ebe045c0af2490dfd67ed2675e77f7e76f658a
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-memory.md
    lines: '56'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: c89b8abcf6dd02f19726a2483c0f92d517fc0b3e836c2efd2fae966ea8273e3e
- id: A-123
  kind: structure
  statement: The Claude Code memory page targets under 200 lines per CLAUDE.md file and says to move instructions
    that matter for only part of the codebase into path-scoped rules, which load only when Claude works
    with matching files.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-memory.md
    lines: '19'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: c3f166134d61cca50b6a5c341ee41175238f3ce263e125deb307063b4d029121
- id: A-124
  kind: structure
  statement: Claude Code can read a repository's `AGENTS.md` files in place of CLAUDE.md.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-memory.md
    lines: '6'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: da50a073a35022a79e4c9e4ee421bddfb754768f9b1a530791fe865bd720b07e
- id: A-125
  kind: structure
  statement: Claude Code loads a project skill from `.claude/skills` for sessions in the repository, and
    the page says to commit it so the team gets it too.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-skills.md
    lines: '19'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 3ae2caa253770fa6db0d32f0e8583452a63a798f23b13e1ea8a3baea40da4fab
- id: A-126
  kind: structure
  statement: A Claude Code skill can carry a front-matter field `paths` with glob patterns. When it is
    set, Claude loads the skill automatically only when working with files that match.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-skills.md
    lines: '34'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: bd5f709faeacf2b0d61346aced1c4d289cba4031bde60f3fdc5570a77d1a2e17
- id: A-127
  kind: structure
  statement: Claude Code skills in a `.claude/skills/` directory below the starting directory load the
    first time Claude reads or edits a file in that subdirectory.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-skills.md
    lines: '25'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e83e8193202dc1a2111df8ad9141d0a085c58be3feeb4e957e48e575c65c7044
- id: A-128
  kind: structure
  statement: The Claude Code tool list includes `WebFetch`, which fetches content from a specified URL,
    and `WebSearch`, which performs web searches.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-tools.md
    lines: 6-7
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 08ef5771f0e7503167ed54f3c4a03596ced2d2447b9443f6dbbb75808f45055a
- id: A-129
  kind: structure
  statement: Claude Code WebFetch takes a URL and a prompt, fetches the page and converts it to Markdown,
    and for most fetches runs the prompt against the content in a separate model call, so it is lossy
    by design.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-tools.md
    lines: 12-14
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 51acbda5b5362eace6d7e5eb7d7ebdd34a28d7dd5125da39edc3ba9f70fc6c70
- id: A-130
  kind: structure
  statement: Claude Code WebFetch refuses `localhost` and any hostname without a dot, and reads up to
    100,000 characters of a page per call.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-tools.md
    lines: '17'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: d89ed22c5a314e35b3f03bc0cd911b4faeb1c593571ed8a9cf86c2d4b0064c17
  - path: docs/design/team-conventions-resources/evidence/web/claude-code-tools.md
    lines: '19'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 32f6a1154eb3cc2eb4dfe626b92a5fcecbed4f5a5cc59d264055702fb333ec6d
- id: A-131
  kind: structure
  statement: The Codex `web_search` setting takes `disabled`, `cached`, `indexed` or `live`. The default
    is `cached`, which uses an OpenAI-maintained index without external web access.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/codex-config-web-search.md
    lines: '9'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: e3827fa53228cae8d748989b14d1c5494342b01d141f52ec6335fe83f351b3b3
- id: A-132
  kind: structure
  statement: The Codex `tools.web_search` setting can carry `allowed_domains`, and the page says these
    filters are separate from sandboxed-command network rules and do not restrict connectors or MCP servers.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/codex-config-web-search.md
    lines: '6'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: f41926750fe27300f9a3192f5a6edb1f72bab3ea13ed6b800ce2482d80337046
- id: A-133
  kind: structure
  statement: 'Cursor project rules have four types: `Always Apply`, `Apply Intelligently`, `Apply to Specific
    Files` and `Apply Manually`.'
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/cursor-rules.md
    lines: 17-20
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 8345f027aedd90fb1cbd2fe3066e69f7b2fb134bdc724f0e4e040add74f832c0
- id: A-134
  kind: structure
  statement: In Cursor, a file mention such as `@migration-template.sql` in a rule tells the agent where
    to look. The file's contents are not inlined into the prompt.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/cursor-rules.md
    lines: '23'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 8152d8335bb3f1b30c7aaedb10dacd94d76f44f2ab403d463094c4214969a30d
- id: A-135
  kind: structure
  statement: The Cursor rules page advises referencing files instead of copying their contents, so that
    rules stay short and do not go stale.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/cursor-rules.md
    lines: '26'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 34d892ac4dcda1409bbc1a98f87c84cde1a736505b386bc29a31a27b3142b44a
- id: A-136
  kind: structure
  statement: The Cursor rules page lists copying entire style guides as something to avoid in rules, and
    says to use a linter instead.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/cursor-rules.md
    lines: '29'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 5c1f25333275c523b80a64e66055de2b79aa57087b086a1ed21100f4d5b11f84
- id: A-137
  kind: structure
  statement: Cursor Team Rules are created from the dashboard on Team and Enterprise plans, and admins
    can configure whether each rule is required for team members.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/cursor-rules.md
    lines: '33'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: be0924d79e1a146b3fd3fb4f789dc7f0080f50a60b70deb36730a87c8aa6b050
- id: A-138
  kind: structure
  statement: Cursor applies a nested `AGENTS.md` automatically when working with files in its directory
    or the directories below it.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/cursor-rules.md
    lines: '36'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 0eaf190697c5179dd8d6ab188db3d73e5d739f98a20e4457ca6ca0129e71211d
- id: A-139
  kind: structure
  statement: Codex reads `AGENTS.md` files from a global scope and from the project root down to the working
    directory, at most one file per directory, and joins them root-first so that closer files override
    earlier guidance.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/codex-agents-md.md
    lines: 8-10
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 02d0812c299d52763fddfcce81ca6be7edcaa542f937f487fc4fcfe63f21f40e
- id: A-140
  kind: structure
  statement: Codex stops adding `AGENTS.md` files once the combined size reaches `project_doc_max_bytes`,
    which is 32 KiB by default.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/codex-agents-md.md
    lines: '13'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: afc9dd0b2387b13b0c50f14ecb3d5dee216f15477dce36f4e97dd0452d5f703a
- id: A-141
  kind: structure
  statement: Codex starts each skill with its name and description and loads the full `SKILL.md` instructions
    only when it decides to use the skill.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/codex-skills.md
    lines: '6'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 6d482efa9812bf83f7c0c5d798ec0b5499d67200d9a7637f25ad4f657a0021e4
- id: A-142
  kind: structure
  statement: For a repository, Codex scans `.agents/skills` in every directory from the working directory
    up to the repository root.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/codex-skills.md
    lines: '12'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 5c088424375964715fa387a8cbf394780464ca4cc3b6810a39ef519ae934b0cb
- id: A-143
  kind: structure
  statement: The Codex skills page shows a skill dependency on a documentation MCP server (`openaiDeveloperDocs`)
    with a `streamable_http` transport.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/codex-skills.md
    lines: 21-23
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 8e1dff934e735bf2c2d262bf692e2a0e1d9f375e1c4b4ee0f388c77f980de2e6
- id: A-144
  kind: structure
  statement: GitHub reads a pull request template from `pull_request_template.md` in the root, from `docs/pull_request_template.md`
    or from `.github/pull_request_template.md`.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/github-pr-template.md
    lines: '9'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: c72e9183f6e7179634f7aeabccabeae0ed756e27a33ed9fcfd14db9619d31fc3
- id: A-145
  kind: structure
  statement: GitHub makes a pull request template available to collaborators once it is merged into the
    repository's default branch.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/github-pr-template.md
    lines: '15'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 02fad92d233f638c17e2c266d5fbe69b6c9645c0a6f98be140e65de9667bbfe6
- id: A-146
  kind: structure
  statement: GitHub flow is described as a lightweight, branch-based workflow in which a branch has a
    short, descriptive name such as `increase-test-timeout` or `add-code-of-conduct`.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/github-flow.md
    lines: '6'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 9fe2035fbc54709c0f560c1d0e4b86fd5592b6e366b2ce84d58c9f6ae6220ea1
  - path: docs/design/team-conventions-resources/evidence/web/github-flow.md
    lines: '9'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 02cfd7b270130c0724d5e6b62092ca3a52fe0345f92c046652b3c9bac86cd1bd
- id: A-147
  kind: structure
  statement: GitHub flow says that some repositories require an approving review before a pull request
    can be merged, that a pull request can be marked as a draft, and that branch protection settings may
    block a merge.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/github-flow.md
    lines: '15'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2099b23fcdf421a4538fd6aba3dae87581111b5389a71b8c8169e0072dc150a6
  - path: docs/design/team-conventions-resources/evidence/web/github-flow.md
    lines: '18'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 0a9ef47924e79a25a8dae12b7f2982b647c362ef6acf85ae52aa9261086c36ac
- id: A-148
  kind: structure
  statement: Atlassian calls Gitflow a legacy Git workflow that has fallen in popularity in favor of trunk-based
    workflows and can be challenging to use with CI/CD.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/gitflow-atlassian.md
    lines: '6'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 80863071cee5fbb2ed3265d7e72f20d9a282ec65f8b310b378a4071176688611
- id: A-149
  kind: structure
  statement: Gitflow uses a `main` and a `develop` branch, a `release` branch forked from `develop` once
    it has enough features, and `hotfix` branches based on `main`.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/gitflow-atlassian.md
    lines: '9'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: f4cf193bbf59818258adec6f66b41a12002d64150f6fb03d9270a4a1cab71020
  - path: docs/design/team-conventions-resources/evidence/web/gitflow-atlassian.md
    lines: '12'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 672377aff1262aaeb51db7a25feebab991f9d1ae129134e599828420f9352ecc
  - path: docs/design/team-conventions-resources/evidence/web/gitflow-atlassian.md
    lines: '15'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 2ae3c63afe058336bdf266494158e426d3029a76f644917ef3cf37dfbc31d2f1
- id: A-150
  kind: structure
  statement: Conventional Commits structures a commit message as a type, an optional scope, a description,
    an optional body and optional footers.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/conventional-commits.md
    lines: '9'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: 7509930065a08bcfe392c361701e41df6ed9ec394696b221bd5aa6814525e98b
- id: A-151
  kind: structure
  statement: The llms.txt page expects agents to view or search `llms.txt`, then follow the relevant links,
    and keeps the file small enough to fit in context with the detail behind the links.
  evidence:
  - path: docs/design/team-conventions-resources/evidence/web/llms-txt.md
    lines: '9'
    revision: 2d84a44937bfd47682e5d7b59935d5da047542c3
    sha256: ab37ad87949af8c5920097bc45d96756de3ba86cb773f7d732bcd9a7a6580c6b
unknowns:
- id: U-1
  what: Whether any field, question or code records or asks about gitflow or a branch model, a merge strategy
    value, a release or hotfix flow, pull-request size, title or description rules, required checks, or
    the PR reviewers (as an answer). Searched src (all file types, excluding the ignored file) for gitflow,
    git-flow, git flow, hotfix, squash, merge strategy, branching model, branch model, trunk-based, release
    flow, release branch, conventional commit, commit convention, branch naming and naming rule. The only
    hits are the `merge_strategy` default "unknown" (contracts/profile.py:89, copied at init_project.py:331,
    in the JSON schema), the branch-naming and commit-convention questions, and the onboard skill and
    command text. `reviewers` and `merge_strategy` are not in ANSWER_KEYS (init_questions.py:26-38), not
    in open_questions (draft_profile.py:113-137), and nothing asks for them.
  material: true
  question_ref: Q-11
  merged_from:
  - onboarding-profile/U-1
- id: U-2
  what: Whether the profile, `init` or `profile` mention a link, URL, resource or documentation source.
    Searched `https?://`, `url`, `link` and `resource` (case-insensitive) in init_*.py, draft_profile.py,
    profile_edit.py, contracts/profile.py, commands/init.py, commands/profile.py and ports/prompter.py,
    with no hit. The nearest fields are elsewhere and not mapped here. `StandardsSourceRef` (profile.py,
    kind prompts-dir or standards-pack, with `path` and `ref`) is the profile's only "source" concept.
    `Provenance.source_url` (contracts/standards_pack.py:29-34) is pack provenance. `KnowledgeSource.globs`
    (contracts/knowledge_config.py:19-24) holds repository-relative globs. `ServerIdentity.url` (contracts/integrations.py:14-19)
    is an MCP server address. Whether any of these can hold a team's resource link (API guidelines, tool
    documentation, a page behind a login) with a note is not established.
  material: true
  question_ref: Q-9
  merged_from:
  - onboarding-profile/U-2
- id: U-3
  what: Whether any generated file other than `.orqlet/project-profile.yaml` carries `target_branch`,
    `branch_naming`, `commit_convention`, `reviewers` or `merge_strategy`. Searched src for these names.
    Consumers are init_questions.py, draft_profile.py, init_project.py (git setup and the template copy),
    binding_inputs.py:132-146 (target branch used to find the merge base), upgrade.py:97-112 (template
    targets only) and the JSON schema. No adapter, renderer, workflow text or baseline file reads them,
    and `compose` discards the profile (render_all.py:111). The AGENTS.md block comes from baseline/baseline.md,
    in which `branch` does not occur. I did not read a freshly rendered target repository.
  material: true
  question_ref: Q-11
  merged_from:
  - onboarding-profile/U-3
- id: U-4
  what: 'Whether any code turns profile answers or links into scoped rules, skills or knowledge entries.
    Searched for writers of `.prompts/rules.yaml` and `.orqlet/knowledge.yaml`. The seed has `rules: []`
    (workflow/seeds/prompts/rules.yaml:1-4) and is written once. KNOWLEDGE_PATH is written only in render_all.py:261
    and read in binding_inputs.py:172-179 and knowledge_impact.py. The profile answers have no consumer
    in rule rendering (F-17, F-18).'
  material: true
  question_ref: Q-9
  merged_from:
  - onboarding-profile/U-4
- id: U-5
  what: Whether a repository-derived value for target branch, commit convention or reviewers is ever read
    at init. Searched `refs/remotes`, `symbolic-ref`, `current_branch(` and `CODEOWNERS` in src. The Vcs
    port declares `current_branch()` (ports/vcs.py:74) and the git adapter implements it (adapters/git/vcs_git.py:62),
    but no src code calls it. `refs/remotes` appears only in vcs_git.py:190 (a for-each-ref call). CODEOWNERS
    is read only to check that the standards folder is mentioned (render_all.py:324-388, finding ORQ-I030).
  material: true
  question_ref: Q-11
  merged_from:
  - onboarding-profile/U-5
- id: U-6
  what: 'Whether anything reads `auth_procedures`, `capabilities` or `data_class` of the profile (declared
    at contracts/profile.py:151, 156 and 159). Searched `auth_procedures`, `auth-procedures`, `data_class`
    and `.capabilities` in src. Only the contract and the JSON schema mention them (and `.orqlet/project-profile.yaml:133`
    holds `auth_procedures: []`). No question or reader was found. Whether "internal pages behind a login"
    has any representation is therefore unknown.'
  material: true
  question_ref: Q-11
  merged_from:
  - onboarding-profile/U-6
- id: U-7
  what: The exact files the Claude Code and Cursor adapters write for scoped rules, commands, skills and
    roles (adapters/clients/claude_code.py:23-33 and cursor.py:30-41 render `request.scoped_rules`, `request.commands`,
    `request.skills` and `request.roles`). The `orqlet-onboard` skill is present in .claude/skills and
    .agents/skills of this repository. Paths and contents were not mapped here (another area).
  material: false
  merged_from:
  - onboarding-profile/U-7
- id: U-8
  what: Whether the `WorkflowPolicy` contract (contracts/policy.py:55-68, with `required_checks`, `approvals.code_owners`
    and `approvals.minimum_approvers`) is a place where a team records required checks or reviewers. Init
    does not write it (render_all.py:257-274 lists the files init writes). Its readers and its file location
    were not traced (another area).
  material: true
  question_ref: Q-11
  merged_from:
  - onboarding-profile/U-8
- id: U-9
  what: Whether a hand edit of the seeded `.orqlet/project-profile.yaml` (for example setting `reviewers`)
    is accepted or reported as drift by doctor or sync. The file is recorded as owner seeded in .orqlet/generated.lock.yaml:613-616,
    and `profile answer` records a new hash (test_profile_edit.py:58-70). Drift handling of seeded files
    was not traced.
  material: true
  question_ref: Q-10
  merged_from:
  - onboarding-profile/U-9
- id: U-10
  what: Whether `doctor` is the only command that lists unknown facts. `_profile_findings` runs under
    `full=True` (diagnose.py:60-61, 123-124), which `doctor` uses and `sync` does not. `init` prints open
    questions through render_human.py:54-56 and `open_questions` in the JSON (commands/init.py:154). `tests/unit/adapters/test_tty_prompter.py`
    and `tests/fakes/prompter.py` exist but were not read.
  material: false
  merged_from:
  - onboarding-profile/U-10
- id: U-11
  what: 'Whether any rendered file, rule, skill, command or AGENTS.md block uses the values of branch_naming
    or commit_convention, or tells agents to read the profile for them. Searched `branch_naming|commit_convention`
    in src/orqlet/**/*.py: matches only in contracts/profile.py, draft_profile.py, init_questions.py and
    the CLI help text of commands/profile.py. Searched `profile|repository` in src/orqlet/adapters/render
    and src/orqlet/adapters/clients: no match. Searched `target_branch|branch_naming|commit_convention|merge_strategy|reviewers|branch
    naming|commit message convention` in tests/golden/**: only the sentence ''Do not invent a branch naming
    rule or a commit convention'' and unrelated uses of ''reviewers''. Searched `project-profile|profile`
    in src/orqlet/workflow/**/*.md: no instruction to read the profile values. No reader found; not confirmed
    by running init.'
  material: true
  question_ref: Q-11
  merged_from:
  - trace-init-profile/U-1
- id: U-12
  what: 'Whether anything fills pull_requests.reviewers or pull_requests.merge_strategy with a value other
    than the default ''unknown''. Searched `reviewers|merge_strategy` in src/orqlet/**/*.py: only contracts/profile.py:88-89
    and init_project.py:330-331, plus the project-profile JSON schema. Searched `CODEOWNERS`: render_all.py:324-388
    only checks whether a CODEOWNERS file mentions the prompts folder. Neither key is in ANSWER_KEYS (init_questions.py:26-38).'
  material: true
  question_ref: Q-11
  merged_from:
  - trace-init-profile/U-2
- id: U-13
  what: 'Whether the target branch, commit style or remote names are detected from Git at init, or compared
    with the remote default by doctor. Searched `current_branch|recent_commits|remote_names|refs/remotes|symbolic-ref|origin/HEAD|GIT-03`
    in src/orqlet/**/*.py: only definitions in application/ports/vcs.py:74,128,132 and adapters/git/vcs_git.py:62,178,189-190.
    No caller found in use cases or the interface. The design text at docs/design/orqlet-architecture-architecture
    document.md:1723 describes a doctor comparison with `refs/remotes/<remote>/HEAD` (see C-2).'
  material: true
  question_ref: Q-11
  merged_from:
  - trace-init-profile/U-3
- id: U-14
  what: 'Whether a maintainer can set repository.pull_requests.reviewers, merge_strategy or template.targets
    after init through `profile answer`, and what `init --answer` does with a key it never reads. Searched
    `ANSWER_KEYS` (no such keys; profile_edit.py:48-54 refuses unknown keys with ORQ-E160). Searched `options.answers|supplied|answers.get`
    in application/usecases: init reads supplied answers only by question id, by `repository.pull_requests.template.targets`
    (init_files.py:166) and by `reviewer` (init_project.py:263). No code refusing or reading any other
    key was found. Not run.'
  material: true
  question_ref: Q-11
  merged_from:
  - trace-init-profile/U-4
- id: U-15
  what: 'Whether any profile field, question, rendered file or skill carries a link to a team resource
    such as a wiki, handbook or CONTRIBUTING page. Searched case-insensitive `source_url|wiki|handbook|confluence|notion|contributing|\burl\b|hyperlink|resource_link`
    in src/orqlet/**/*.py. Matches are only Provenance.source_url (contracts/standards_pack.py:30), the
    MCP ServerIdentity.url (contracts/integrations.py:16) and dependency index-url handling (domain/dependencies.py:128).
    Searched `https?://|wiki|handbook|confluence|notion|contributing` in src/orqlet/workflow/**/*.{md,yaml,json}:
    no match. The profile contract (profile.py) has no link field. A mcp_credentials file also matched
    `url` but was excluded as instructed.'
  material: true
  question_ref: Q-9
  merged_from:
  - trace-init-profile/U-5
- id: U-16
  what: 'Whether pack data other than rules and the `pr-template` asset reaches any generated file: the
    pack `baseline`, `references`, `provenance`, `reviewers`, and asset kind `prompts-scaffold`. Searched
    `baseline_text|\.references|provenance|scaffold|prompts-scaffold` in src/orqlet/**/*.py. `baseline_text`
    is set at adapters/standards/pack_source.py:66 and declared at ports/standards.py:20 with no other
    reader found. `prompts-scaffold` appears only at contracts/standards_pack.py:21 and in the standards-pack
    JSON schema. render_all.py:139 skips every asset kind except `pr-template`. The meaning of PackManifest.reviewers
    (standards_pack.py:49) is not stated in code, and I found no reader.'
  material: true
  question_ref: Q-9
  merged_from:
  - trace-init-profile/U-6
- id: U-17
  what: 'Whether upgrade re-detects pull request template files or recomputes pull_requests.template.status
    and source_id after a team template is added or removed later. Searched `discover_pr_templates|choose_pr_targets|_with_pr_template`
    in src/orqlet: only init_project.py and init_files.py. upgrade.py:105 passes the stored targets. Not
    run.'
  material: true
  question_ref: Q-11
  merged_from:
  - trace-init-profile/U-7
- id: U-18
  what: What upgrade plans for .orqlet/project-profile.yaml after a hand edit made since its last recorded
    hash. upgrade.py:98 passes the file's current bytes as the wanted content, and classify.py:65-74 compares
    the new hash with the recorded one. The resulting plan item was not run or observed.
  material: false
  merged_from:
  - trace-init-profile/U-8
- id: U-19
  what: Whether any skill, or any rule other than a MUST rule file, is generated from a technology, a
    pack or the profile. Searched `ClientSkill(` in src/**/*.py (one construction, at workflow_sources.py:129,
    fed by the workflow package), the word `skill` case-insensitively in src/orqlet/application/contracts/*.py
    (no match), and tests/fixtures/packs*/** (only pack.yaml and rules/*.yaml).
  material: true
  question_ref: Q-9
  merged_from:
  - generated-context/U-1
- id: U-20
  what: Where a team's own skill (for example one per tool) would be written, and which owner mode it
    would have. Searched `.claude/skills`, `.agents/skills`, `.cursor/skills` and `.codex/skills` in src/**/*.py.
    The hits were skills.py:19-20 (Orqlet's own skills), diagnose.py:31-40 (managed folders), personal_names.py:14-21
    (names in the home directory) and a message at cursor.py:22; `.cursor/skills` and `.codex/skills`
    do not occur. `OwnerMode.USER` is read only at classify.py:36 and no renderer sets it.
  material: true
  question_ref: Q-10
  merged_from:
  - generated-context/U-2
- id: U-21
  what: Which code reads the pack fields `references`, `provenance` and `baseline`, the asset kind `prompts-scaffold`
    and the knowledge source kind `standards-reference`. Searched those words and `baseline_text` in src/**/*.py.
    Only declarations and the load at pack_source.py:61-66 were found (standards_pack.py:21,54,56; knowledge_config.py:15,23;
    ports/standards.py:20). Asset kind `pr-template` is read at render_all.py:139 and init_project.py:322.
  material: true
  question_ref: Q-9
  merged_from:
  - generated-context/U-3
- id: U-22
  what: Whether skills can be limited to matching paths in Claude Code and Codex. The renderer writes
    no such field (skills.py:44-51). The architecture document records `paths` for Cursor skills only
    (line 5957), while its Claude Code skills row (line 5956) and Codex skills row (line 5902) name no
    such field. Whether Cursor really honours `paths` on skills is documentation-based and was not observed.
  material: true
  question_ref: Q-14
  merged_from:
  - generated-context/U-4
- id: U-23
  what: How each client behaves with the generated files. The plan records that no client was opened,
    and that the Cursor `globs` format, the Cursor duplicate skill listing (ORQ-L004), the Codex reading
    of `disable-model-invocation` (ORQ-L005) and what any agent does with a skill are not observed (docs/design/orqlet-m2-workflow/plan.md:170).
  material: true
  question_ref: Q-14
  merged_from:
  - generated-context/U-5
- id: U-24
  what: Whether a catalogue of links exists in code. Searched `catalogue|catalog` case-insensitively in
    src (no file matches). IMPLEMENTED_COMMANDS (capabilities.py:14-39) has no knowledge command. The
    architecture document describes an `orqlet-catalogue` skill and `orqlet knowledge catalogue` (docs/design/orqlet-architecture-architecture
    document.md:1573).
  material: true
  question_ref: Q-9
  merged_from:
  - generated-context/U-6
- id: U-25
  what: 'Whether any `.prompts` Markdown other than `foundations.md` reaches an agent through code. The
    seeded README says rules can name longer Markdown files (README.md:7). Searched `foundations` in src/**/*.py:
    only review_prepare.py:48-52 lists `.prompts/foundations.md` in STANDARDS_FILES. Whether the other
    files are read by the agent on its own was not found.'
  material: true
  question_ref: Q-9
  merged_from:
  - generated-context/U-7
- id: U-26
  what: Whether Orqlet checks, stores or fetches a URL or a page copy. `Provenance.source_url` and `Rule.text`
    are plain strings (standards_pack.py:29-34, 72). Searched `https?://`, `urllib`, `requests`, `httpx`
    and `urlopen` in src/**/*.py, excluding the files the task said to ignore. The matches were only names
    containing `pull_requests`.
  material: true
  question_ref: Q-9
  merged_from:
  - generated-context/U-8
- id: U-27
  what: Whether Claude Code loads a file of `.claude/rules` only for the files that its `paths` front
    matter matches. The adapter limit ORQ-L001 says the behaviour follows the published documentation
    of 2026-10 and was not observed with a real client version (src/orqlet/adapters/clients/claude_code.py:15-19).
  material: true
  question_ref: Q-14
  merged_from:
  - trace-rules-skills/U-1
- id: U-28
  what: Whether Cursor accepts `globs` as a YAML list in `.cursor/rules/*.mdc` and attaches the rule by
    it. src/orqlet/adapters/clients/cursor.py:15-19 says the `globs` format of rule files is unverified.
  material: true
  question_ref: Q-14
  merged_from:
  - trace-rules-skills/U-2
- id: U-29
  what: Whether Cursor and Codex both load skills from `.agents/skills`, whether Cursor lists a skill
    twice when `.claude/skills` is also present, and whether Codex honours `agents/openai.yaml`. cursor.py:20-24
    and codex.py:28-33 say these are documented but not observed.
  material: true
  question_ref: Q-14
  merged_from:
  - trace-rules-skills/U-3
- id: U-30
  what: 'Whether anything renders a pack''s `baseline` text, its `references` list or a `prompts-scaffold`
    asset into a client file or into the prompts folder. Searched the words baseline_text, manifest.baseline,
    references, scaffold, asset_files and `.assets` in src/**/*.py. Hits: the pack loader (src/orqlet/adapters/standards/pack_source.py:61-69),
    the contracts (standards_pack.py:21, 52-54), `team_template` (render_all.py:134-144) and init_project.py:322,
    which read `pr-template` assets only. No code reading `prompts-scaffold` was found.'
  material: true
  question_ref: Q-9
  merged_from:
  - trace-rules-skills/U-4
- id: U-31
  what: Whether a skill, command or role can be added from the repository's own files so that Orqlet renders
    it for the clients. Searched skills, load_skills, load_roles, _commands and .claude/skills in src/**/*.py.
    All three are read from the workflow package through `WorkflowSource`. `.prompts/rules.yaml` and `.orqlet/rules.yaml`
    are parsed as `RuleFile`, which holds `rules` only (standards_pack.py:37-41).
  material: true
  question_ref: Q-9
  merged_from:
  - trace-rules-skills/U-5
- id: U-32
  what: How upgrade, doctor and review treat a team-written file under `.claude/`, `.cursor/` or `.agents/`
    whose name does not start with the reserved prefix `orqlet-`. Searched RESERVED_PREFIX, _MANAGED_DIRECTORIES
    and the string .claude/ in src/**/*.py and *.yaml. The reserved-prefix check (diagnose.py:187-212)
    is the only name-based check found. The workflow rule text says these folders are generated by Orqlet
    (src/orqlet/workflow/rules/orqlet-workflow.md:3-7).
  material: true
  question_ref: Q-10
  merged_from:
  - trace-rules-skills/U-6
- id: U-33
  what: 'How a rule names a longer Markdown document and whether anything reads it. src/orqlet/workflow/seeds/prompts/README.md:7
    says to put longer explanations in Markdown files and name them from the rule. The `Rule` contract
    has no field for a file or link (standards_pack.py:65-73). Searched foundations and .prompts in src/**/*.py:
    only src/orqlet/application/usecases/review_prepare.py:48-53 lists `.prompts/foundations.md` (with
    `.prompts/rules.yaml` and `.orqlet/rules.yaml`) among the standards files of the review packet. No
    code that reads a Markdown file named by a rule was found.'
  material: true
  question_ref: Q-9
  merged_from:
  - trace-rules-skills/U-7
- id: U-34
  what: 'Whether `.orqlet/rules.yaml` (second own layer, source `project`) exists in this repository.
    Searched the glob **/* under .orqlet/: no `rules.yaml`. The files found are versions.yaml, project-profile.yaml,
    role-bindings.yaml, knowledge.yaml, standards.lock.yaml, generated.lock.yaml, workflow.lock and proposals/.'
  material: false
  merged_from:
  - trace-rules-skills/U-8
- id: U-35
  what: 'Whether any adapter delivers the files named by the `.orqlet/knowledge.yaml` sources (kind `standards-reference`
    with `pack`) to a client as a rule or skill. Searched the word knowledge in src/orqlet/adapters/**:
    no file matches. The contract is at knowledge_config.py:15-23.'
  material: true
  question_ref: Q-9
  merged_from:
  - trace-rules-skills/U-9
- id: U-36
  what: 'What limits the three clients put on the number or size of rule files, skill descriptions and
    the `AGENTS.md` chain. Searched tests for budgets: only test_clients_golden.py:130-133 (baseline block
    under 32 KiB for Codex) and test_skills.py:133-137 (skill name up to 64 and description up to 1024
    characters for the packaged skills) were found. The client limits themselves are not stated in the
    code.'
  material: true
  question_ref: Q-14
  merged_from:
  - trace-rules-skills/U-10
- id: U-37
  what: Whether a knowledge source, a module card or a knowledge-impact entry can carry a URL, an external
    document, a copied web page or a link with a note. Searched src/orqlet/application/contracts for url,
    http, href, fetch, download, webpage and remote (case-insensitive). The only field named url is in
    integrations.py:16, on an entry of kind remote or stdio, and knowledge_config.py, module_card.py and
    knowledge_impact.py hold no such field. KnowledgeEvidence.kind has a value source whose ref is described
    as a source id (knowledge_impact.py:36-37), and the validator skips it offline (validate_records.py:627-632).
    What a source id points to is not defined in the code I read.
  material: true
  question_ref: Q-9
  merged_from:
  - knowledge/U-1
- id: U-38
  what: How the content of knowledge documents reaches an agent. Searched src for readers of KnowledgeConfig
    and read_knowledge_config (only binding_inputs.py, knowledge_impact.py and render_all.py) and for
    the word knowledge under src/orqlet (the file list shows no client renderer in it). Also searched
    src/orqlet/workflow skills, roles, rules and pr_template. Found no generated rule, skill, index or
    search that loads a source's content. The skills and roles mention knowledge only as a step that writes
    drafts (orqlet-implement/skill.md:16) and as input to the reviewers (roles/orqlet-arch-reviewer.md:6,14;
    orqlet-security-reviewer.md:6,8). Whether an agent reads the knowledge documents on its own is not
    shown by the code I read.
  material: true
  question_ref: Q-9
  merged_from:
  - knowledge/U-2
- id: U-39
  what: Whether the knowledge index is built. Searched src for IndexConfig, refresh_policy, tokenizer,
    generations_kept, target_branch_ref, index_state, index_ref, views, knowledge index and knowledge
    search. Matches are only record or config fields in contracts/knowledge_config.py, contracts/knowledge_impact.py:53-54,94-97
    and module_card.py:35, plus the JSON schemas. I found no code that builds or reads an index. The commands
    folder has 10 files and the knowledge group has only the command impact. The validator compares only
    candidates_digest and candidate_count of the record's analysis block (validate_records.py:484-487),
    and my search for views and index_state in usecases found no reader. docs/design/orqlet-architecture-architecture
    document.md names orqlet knowledge search as planned (lines 345 and 1547), and I did not read the
    architecture document beyond those matches.
  material: true
  question_ref: Q-9
  merged_from:
  - knowledge/U-3
- id: U-40
  what: Whether the source field kind, the field pack, the write-scope field kinds and the scopes team
    and company have any effect. Searched src for .kind, .kinds, .pack, standards-reference, the literals
    team and company, and .write_scope. Only knowledge_impact.py:194 (scope project, globs) and binding_inputs.py:188
    (globs of write_scope) read the configuration. I found no reader of kind, pack or kinds, and no code
    that reads the hash-verified pack named in knowledge_config.py:23.
  material: true
  question_ref: Q-9
  merged_from:
  - knowledge/U-4
- id: U-41
  what: Who creates module cards, ADRs and knowledge documents, and who writes the knowledge-impact record.
    Searched src/orqlet/interface/cli/commands (10 files) and src for ModuleCard construction, a card
    or ADR writer, and a command such as knowledge add, link or import. Found none. The implement skill
    (skill.md:16) has the agent write the drafts and save the record from the review_input it prints.
    Whether a person writes cards or ADRs outside a phase is not shown by the code.
  material: true
  question_ref: Q-10
  merged_from:
  - knowledge/U-5
- id: U-42
  what: 'Whether the policy fields knowledge.copy_max_lines and knowledge.near_duplicate_threshold (contracts/policy.py:47-49,66)
    change the copy lints. Searched src for copy_max_lines and near_duplicate_threshold: only policy.py
    and the policy JSON schema. validate_records.py:72-73 uses the constants COPY_MAX_LINES and NEAR_DUPLICATE_THRESHOLD.'
  material: false
  merged_from:
  - knowledge/U-6
- id: U-43
  what: 'Whether reuse_decisions[].candidate, described as a module card id (contracts/plan.py:61-64),
    is checked against any card. Searched src for reuse and ReuseDecision: only plan.py. No validator
    reads it.'
  material: false
  merged_from:
  - knowledge/U-7
- id: U-44
  what: 'Knowledge documents, module cards and ADRs in this repository. Searched docs/adr, docs/modules
    and docs/knowledge with a glob, and .orqlet/docs-map.yaml: 0 files. The committed records docs/design/harness2-fit/knowledge/P-1.yaml
    to P-6.yaml show outcome no-impact at line 15 of each.'
  material: false
  merged_from:
  - knowledge/U-8
- id: U-45
  what: 'Whether any command other than knowledge impact, validate knowledge and review prepare reads
    or validates .orqlet/knowledge.yaml. Searched for the word knowledge in the usecases files diagnose.py,
    init*.py, upgrade*.py, release.py, validate_as_is.py and validate_design.py: no matches. A file that
    fails to load is read as absent by read_knowledge_config (binding_inputs.py:178-181), with no error
    of its own.'
  material: false
  merged_from:
  - knowledge/U-9
- id: U-46
  what: 'Whether any implemented or planned command touches resources, links, documentation or conventions.
    I searched src/orqlet/**/*.py for resource, bookmark, gitflow, git-flow, knowledge add, link, conventions,
    hotfix, docs_url and documentation. I searched src/orqlet/workflow (not JSON) for resource, bookmark,
    gitflow, knowledge add, hotfix, conventions and release flow. I searched tests, README.md, AGENTS.md,
    pyproject.toml, .prompts and docs/design (outside mcp-or-plugins and team-conventions-resources) for
    gitflow, git-flow, knowledge add, hotfix, bookmark, resource link and branch model. Hits were unrelated:
    importlib.resources imports, the commit_convention fact in contracts/profile.py, symlink and documentation-extension
    code, ''conventions'' in baseline.md line 9 and ''knowledge additions'' in the architecture document
    line 3011. IMPLEMENTED_COMMANDS and PLANNED_COMMANDS (capabilities.py lines 12-39) list no such command.
    The only planned command that takes a link is `standards import <link-or-file>` (F-28).'
  material: true
  question_ref: Q-9
  merged_from:
  - commands-cli/U-1
- id: U-47
  what: Whether any command can set the pull-request merge strategy, reviewers, a branch model, gitflow,
    or a release or hotfix flow. I searched merge_strategy in src/orqlet/**/*.py. It occurs only in contracts/profile.py
    line 89 (default 'unknown') and in init_project.py line 331 (copied unchanged). ANSWER_KEYS (init_questions.py
    lines 26-38) has no key for them. I searched the architecture document for gitflow, git-flow, hotfix
    and branch model and found no hit. Line 2878 names 'Git branching and naming', 'commit conventions'
    and 'PR templates, reviewers and merge strategy' as profile contents.
  material: true
  question_ref: Q-11
  merged_from:
  - commands-cli/U-2
- id: U-48
  what: Which OwnerMode and FileClass a file written by a new command should take. No document or code
    I read states it for a new file. The existing writers use OwnerMode.SEEDED for the profile (profile_edit.py
    lines 150-155) and OwnerMode.ORQLET with FileClass.GENERATED for the released record (release.py lines
    120-127). The SEEDED behaviour is in classify.py lines 65-74, which I read but did not cite as a fact.
  material: true
  question_ref: Q-10
  merged_from:
  - commands-cli/U-3
- id: U-49
  what: 'Whether the write paths of profile answer, profile approve, release and rollback have a fault
    test. ORQLET-TEST-002 (.prompts/rules.yaml lines 120-127) requires one for anything that writes files.
    I listed tests/fault/*.py: only test_apply_kill_after_k.py (calls init_project) and test_upgrade_resume.py
    (calls upgrade). Searching tests for answer_profile, approve_profile, release_file and rollback( found
    hits only in tests/unit/application/test_profile_edit.py, test_lifecycle.py and tests/e2e/test_m1_acceptance.py.
    I did not check whether those tests stop the write after each step.'
  material: true
  question_ref: Q-14
  merged_from:
  - commands-cli/U-4
- id: U-50
  what: Where `standards import` is scheduled. Line 2350 says it is built later in Section 22, but my
    search for 'standards import' found no text in Section 22 (lines 4474-4541). Hits were lines 2336,
    2350, 2363, 2388, 4550 ('later (the rest)'), 4563, 5103 and 5381 (listed as 'unscheduled' among review
    findings).
  material: false
  merged_from:
  - commands-cli/U-5
- id: U-51
  what: Whether the folder docs/design/team-conventions-resources/ (evidence/web/*.md, questions.yaml)
    is committed. It exists in the working tree. I did not read it because it is outside my area and the
    brief limited me to code and the architecture document.
  material: false
  merged_from:
  - commands-cli/U-6
- id: U-52
  what: Whether any code writes inside the repository outside apply_plan. I searched write_atomic|write_bytes|write_text|delete(|mkdir(
    in src/orqlet/**/*.py. The only write into the project is apply_plan.py lines 69 and 73. The other
    hits write to the user data directory (journal.py lines 89 and 98, review_prepare.py line 175 through
    the packets store, wiring.py lines 78 and 85, apply_lock.py line 21). I did not search what the Git
    subprocess calls (for example init_repository) create.
  material: false
  merged_from:
  - commands-cli/U-7
- id: U-53
  what: Whether `init` asks questions beyond those in F-18, F-25 and F-16. The code of `choose_pr_targets`
    (init_files.py lines 151-181) asks which pull-request template files receive the Orqlet blocks when
    several exist, and the confirmation 'Apply N file change(s)?' is asked in `_approved` (init_project.py
    lines 338-345). Both were read but left out of the 28-fact cap.
  material: false
  merged_from:
  - commands-cli/U-8
- id: U-54
  what: Whether any skill, role, command, baseline or rule tells an agent to search or fetch on the web.
    I searched the words web, WebSearch, WebFetch, search, fetch, browse, internet, online, URL, http,
    link and look up in src/orqlet/workflow/** (skills, roles, commands, baseline, rules, seeds), .claude/{skills,agents,commands,rules,CLAUDE.md},
    .agents/**, .cursor/{agents,commands,rules/orqlet-workflow.mdc}, .codex/** and AGENTS.md. There was
    no match for a web instruction. The only retrieval wording is 'retrieved passages' at line 9 of each
    of the six skill.md files.
  material: true
  question_ref: Q-12
  merged_from:
  - web-and-network/U-1
- id: U-55
  what: Whether any client configuration in the repository grants, denies or limits a web tool (WebSearch,
    WebFetch, web_search, allowed-tools, allowedTools, disallowedTools, permissions, mcp__). I searched
    the same trees plus .orqlet/**, src/orqlet/adapters/render/**, and the globs **/mcp.json, **/config.toml,
    .mcp.json and .claude/settings*. No such file exists and no match was found. The generated skills
    carry no tool field.
  material: true
  question_ref: Q-12
  merged_from:
  - web-and-network/U-2
- id: U-56
  what: 'Whether Cursor `readonly: true` (.cursor/agents/*.md line 5) or Codex `sandbox_mode = read-only`
    (.codex/agents/*.toml line 4) stops a role from using web search or fetch. The architecture document
    says ''Cursor web tools not verified'' (docs/design/orqlet-architecture-architecture document.md:2648).
    The stored Codex excerpt says its web-search filters are separate from sandboxed-command network rules
    (docs/design/team-conventions-resources/evidence/web/codex-config-web-search.md:6). No repository
    file states the effect on the generated roles.'
  material: true
  question_ref: Q-12
  merged_from:
  - web-and-network/U-3
- id: U-57
  what: Whether any Orqlet code opens a network connection. I searched urllib, http.client, httpx, requests,
    socket, ssl, aiohttp, urlopen and urlparse in all *.py under src, tests and tools. There is no import
    of a network module in any adapter. The only matches are the word 'requests' as test data or as 'pull
    requests', and a docstring about decoding by hand (in a file excluded from this research). The only
    process Orqlet starts for the repository is git, through GitRunner (F-12).
  material: true
  question_ref: Q-12
  merged_from:
  - web-and-network/U-4
- id: U-58
  what: 'Whether any test lifts the socket block, and whether `--disable-socket` reaches child processes.
    I searched enable_socket, socket_allow_hosts, allow_hosts and --force-enable-socket in tests/**, pyproject.toml
    and the conftest files: no match. tests/e2e/test_install_smoke.py:31-41 starts `uv venv` and `uv pip
    install` of the built wheel through subprocess.run; no repository file says whether that install contacts
    a package index. The CI test job runs `uv sync --locked` before `uv run pytest` (.github/workflows/ci.yml:83-84).'
  material: false
  merged_from:
  - web-and-network/U-5
- id: U-59
  what: 'Which of the network commands in the architecture document exist in code. The architecture document
    lists `standards status|update|import`, `sync --fetch`, `doctor --live`, `mcp inspect --live` and
    `init` fetching a URL (docs/design/orqlet-architecture-architecture document.md:4563). Searched --live,
    --fetch and --offline in src, tests and tools *.py: no match. src/orqlet/interface/cli/app.py:34-47
    registers init, upgrade, rollback, sync, doctor, explain, release, profile, standards, validate, gate,
    evidence, knowledge and review. The `standards` group has one command, `for` (src/orqlet/interface/cli/commands/standards.py:26).
    `init` takes only the local folder options --prompts-dir and --packs-dir (src/orqlet/interface/cli/commands/init.py:48-53).
    docs/design/orqlet-implementation/design.md:32 says no local command calls a model or the network
    except those the architecture document lists, and docs/design/orqlet-m2-workflow/design.md:161 says
    S11 introduces the first network access, to GitHub. No repository file says whether S11 has been built.'
  material: true
  question_ref: Q-12
  merged_from:
  - web-and-network/U-6
- id: U-60
  what: Whether the profile, the standards sources or any other contract can record a resource link today.
    I searched link, resource and url in src/orqlet/application/contracts/profile.py (no match) and in
    .orqlet/*.yaml. The only URL-valued fields in code are `Provenance.source_url` (F-27) and `ServerIdentity.url`
    (src/orqlet/application/contracts/integrations.py:14-18). A standards source is a local `prompts-dir`
    or `standards-pack` with a `path` (src/orqlet/application/contracts/profile.py:115-119). `ServiceInterface.contract_ref`
    is a free string (src/orqlet/application/contracts/module_card.py:21-23). No use case that fetches
    any of these values was found.
  material: true
  question_ref: Q-9
  merged_from:
  - web-and-network/U-7
- id: U-61
  what: 'Whether any use case, renderer or validator reads the `orqlet.integrations/v1` contract (Integrations,
    RoleTools, live_inspection). I searched integrations, Integrations, live_inspection and RoleTools
    in src: matches only in src/orqlet/application/contracts/__init__.py, src/orqlet/application/contracts/integrations.py,
    src/orqlet/workflow/schemas/orqlet.integrations.v1.json and src/orqlet/workflow/MANIFEST.json. No
    .mcp.json, .cursor/mcp.json or .codex/config.toml exists in the repository.'
  material: true
  question_ref: Q-13
  merged_from:
  - web-and-network/U-8
- id: U-62
  what: Whether Context7 is approved for this project. The architecture document says it is unavailable
    unless the owners approve it (docs/design/orqlet-architecture-architecture document.md:2644). docs/design/harness2-fit/as-is.md:223
    says it was explicitly approved for that request. docs/design/orqlet-m2-workflow/plan.md:10 and docs/design/orqlet-implementation/as-is.md:8
    record Context7 lookups with no approval statement. I searched Context7 in docs/design/** (excluding
    the unrelated task's folders), src, tests, .claude, .cursor, .codex, .agents, .orqlet and AGENTS.md.
    No file states a project-wide approval or refusal.
  material: true
  question_ref: Q-12
  merged_from:
  - web-and-network/U-9
- id: U-63
  what: Whether the web excerpts and the ledger of the current task (docs/design/team-conventions-resources/evidence/web/*.md
    and questions.yaml) are in the last commit. The start-of-session git status snapshot lists no entry
    for them, but I could not run git. `orqlet evidence cite` reads the file from a committed revision
    (src/orqlet/application/usecases/evidence_cite.py:45), so a citation of these files depends on the
    answer. The folder is committed at the base revision (commit 2d84a44937bf), and the main agent cited
    its web excerpts there with orqlet evidence cite.
  material: false
  merged_from:
  - web-and-network/U-10
- id: U-64
  what: How an agent could read a page that is behind a login. I searched login, sign in, cookie, credential,
    Authorization, bearer, SSO and authenticat in the workflow skills, roles, commands, baseline, the
    generated client folders, AGENTS.md and .prompts. The only matches are the onboarding rule 'do not
    infer deployment permission from a login or a connection' (src/orqlet/workflow/skills/orqlet-onboard/skill.md:16),
    the security reviewer's checklist, and the rule against committing credentials (.prompts/rules.yaml:63).
    The architecture document says credentials stay out of Git, prompts, Markdown and indexes (docs/design/orqlet-architecture-architecture
    document.md:2753) and that Orqlet asks the human to run a login (docs/design/orqlet-architecture-architecture
    document.md:2767). No code or skill handles an authenticated fetch.
  material: true
  question_ref: Q-13
  merged_from:
  - web-and-network/U-11
- id: U-65
  what: Whether any document describes a branch model such as gitflow or trunk-based development, a release
    flow or a hotfix flow. Searched gitflow, git flow, git-flow, trunk, hotfix, release branch, branching
    model, branch model in README.md and docs/** (excluding mcp-or-plugins) and the architecture document.
    The only hits were the generic "feature branch" of the knowledge flow and this task's own question
    ledger, which was not cited.
  material: true
  question_ref: Q-11
  merged_from:
  - documents/U-1
- id: U-66
  what: Whether `init` or `orqlet-onboard` asks for merge strategy, reviewers or required checks. Searched
    merge strategy, merge_strategy, reviewers and required_checks in the architecture document, README
    and plans. `merge_strategy` appears only as `unknown` (architecture document line 4726), reviewers
    as "from CODEOWNERS or unknown" (4725), and `required_checks` as a workflow-policy key (4901). No
    document names a question for them.
  material: true
  question_ref: Q-11
  merged_from:
  - documents/U-2
- id: U-67
  what: Whether the scanner sample of Git history for commit and branch conventions (architecture document
    line 1947) is built. Searched README.md, the implementation plans and `src/orqlet/application/usecases/draft_profile.py`.
    README and the plans do not mention it, and draft_profile.py lines 83-84 set `branch_naming` and `commit_convention`
    to a question.
  material: true
  question_ref: Q-11
  merged_from:
  - documents/U-3
- id: U-68
  what: Which milestone builds `orqlet standards import` and the documentation packs. Section 13.1 says
    "built later, Section 22", but the Section 22 milestone rows (lines 4504-4508) name no milestone for
    it. Searched standards import in Sections 13, 22, 23 and 25, in README.md and in the implementation
    plans.
  material: true
  question_ref: Q-12
  merged_from:
  - documents/U-4
- id: U-69
  what: Whether any document defines a catalogue of resource links with a free-text note per link, or
    a stored summary of a single page. Searched link, URL, bookmark, resource, catalogue and note in the
    architecture document and README. The only link-like records found are the `SOURCE.yaml` fields (F-8,
    F-11), `provenance` `source_url` (F-17) and the `knowledge.yaml` source kinds (F-21).
  material: true
  question_ref: Q-9
  merged_from:
  - documents/U-5
- id: U-70
  what: Whether the allowlisted fetcher can read an internal page behind a login. Section 13.3 names approved
    domains, `.md` twins, `llms.txt` and PyPI JSON and does not mention authentication. Section 16.3 and
    Section 15.7 route logged-in Atlassian reads through MCP and the external-source milestone M6. Searched
    authenticat, login, SSO and fetcher in Sections 13, 15 and 16.
  material: true
  question_ref: Q-13
  merged_from:
  - documents/U-6
- id: U-71
  what: Whether any document describes an automatic web lookup of an unknown library or tool during onboarding,
    research, design or implementation. Searched web, fetch, search, lookup, llms.txt, WebFetch and Context7
    in the architecture document, README and plans. The documents give "no network" to the onboarding
    and research skills (F-26) and only report an uncovered technology (F-18).
  material: true
  question_ref: Q-12
  merged_from:
  - documents/U-7
- id: U-72
  what: Whether pack `extensions/skills` (a skill per tool or technology, architecture document line 2233)
    is built. README does not mention it, and a search of `src/orqlet/application/contracts` for "extensions"
    found only `workflow_package.py:48`, whose meaning was not read.
  material: true
  question_ref: Q-9
  merged_from:
  - documents/U-8
- id: U-73
  what: Whether `init` proposes the `CODEOWNERS` block that Section 1.3 and Section 12.8 describe. README
    does not list it, and a search of `src` for CODEOWNERS found only `render_all.py`, which was not read.
  material: false
  merged_from:
  - documents/U-9
- id: U-74
  what: Whether docs/design/harness2-fit/*, docs/design/open-items/* and docs/design/go-migration-feasibility/*
    say anything on the three topics. Searched onboard, questionnaire, gitflow, branch naming, commit
    convention, merge strategy, standards import, llms.txt, fetch, module card and knowledge source. The
    only hits were ORQ-W181 mentions in harness2-fit tests and reviews, onboard golden paths, and "no
    knowledge sources configured" notes. go-migration-feasibility had no hit.
  material: false
  merged_from:
  - documents/U-10
- id: U-75
  what: Whether the plans under docs/design/orqlet-implementation/ and docs/design/orqlet-m2-workflow/,
    which cite architecture document v0.4, are re-based on v0.5. Proposal section 0.6.5 (line 121) says
    this is not decided. It bears on whether the planned features above are tied to v0.5.
  material: false
  merged_from:
  - documents/U-11
- id: U-76
  what: How Cursor web tools behave. Section 15.8 (line 2648) says "Cursor web tools not verified". Searched
    web tools in the architecture document.
  material: false
  merged_from:
  - documents/U-12
contradictions:
- id: C-1
  sources:
  - src/orqlet/adapters/render/prompts_seed.py:15-16
  - src/orqlet/application/usecases/render_all.py:185-198
  - docs/design/orqlet-architecture-proposal.md:2328
  - src/orqlet/adapters/render/prompts_seed.py:16
  - src/orqlet/application/contracts/standards_pack.py:21
  - src/orqlet/application/usecases/render_all.py:134-143
  note: The docstring of `seed_files` and the architecture document text say a pack may supply its own
    seed (asset kind `prompts-scaffold`). `render_all.seed_files` passes only `services.workflow` to `services.renderers.seed_files`,
    and the pack asset code reads `pr-template` only. Not resolved. The `seed_files` docstring says a
    pack may supply its own seed, and `PackAsset.kind` allows `prompts-scaffold`. The composition `seed_files`
    passes only `services.workflow` to `services.renderers.seed_files`. Not resolved. The docstring of
    seed_files says 'A pack may supply its own seed instead'. The pack asset kinds are pr-template and
    prompts-scaffold, and team_template reads only the pr-template kind. Not resolved.
  merged_from:
  - trace-rules-skills/C-1
  - generated-context/C-3
  - trace-init-profile/C-3
- id: C-2
  sources:
  - src/orqlet/workflow/rules/orqlet-workflow.md:3
  - .orqlet/generated.lock.yaml:609-612
  - tests/unit/application/test_lifecycle.py:149-158
  - src/orqlet/workflow/baseline/baseline.md:25-27
  - .orqlet/generated.lock.yaml:635-655
  - src/orqlet/workflow/rules/orqlet-workflow.md:7
  note: The workflow rule text says the files under .orqlet/ are generated by Orqlet and must not be edited
    by hand. The lock lists .orqlet/knowledge.yaml with owner seeded, and a unit test asserts that a team
    edit of that file survives an upgrade. Not resolved here. The baseline says files listed in `.orqlet/generated.lock.yaml`
    are generated and must not be edited by hand. The lock lists the seeded `.prompts/` files (owner seeded),
    and the workflow rule says a seeded file belongs to the team and may be edited freely. Not resolved.
  merged_from:
  - knowledge/C-1
  - trace-rules-skills/C-2
- id: C-3
  sources:
  - docs/design/orqlet-architecture-proposal.md:4720-4726
  - docs/design/orqlet-architecture-proposal.md:1723
  - src/orqlet/application/usecases/draft_profile.py:81-85
  - src/orqlet/application/usecases/init_project.py:323-331
  - docs/design/orqlet-architecture-proposal.md:4720-4722
  - docs/design/orqlet-architecture-proposal.md:2878
  - src/orqlet/application/usecases/init_questions.py:90-105
  - docs/design/orqlet-architecture-proposal.md:4725-4726
  - src/orqlet/application/contracts/profile.py:88-89
  - src/orqlet/application/usecases/init_project.py:330-331
  - src/orqlet/application/usecases/render_all.py:324-388
  note: The design text says target_branch is named by the maintainer or read from refs/remotes/<remote>/HEAD,
    commit_convention is <detected or unknown>, reviewers is <from CODEOWNERS or unknown> and source_id
    is <pack asset id or unknown>. It also says doctor compares the target branch with the remote default.
    The code drafts all three repository facts as unanswered, sets source_id to None, and copies reviewers
    and merge_strategy unchanged. Not resolved. The architecture document (section 24.2) says `target_branch`
    is "named by the maintainer or read from refs/remotes/<remote>/HEAD" and `commit_convention` is "<detected
    or unknown>". The code only creates them as unknown with a question, and sets them from an answer.
    Not resolved here. The architecture document says `reviewers` is "<from CODEOWNERS or unknown>". The
    contract defaults it to the text "unknown" and init copies it unchanged. CODEOWNERS is read only to
    check that the standards folder is mentioned. Not resolved here.
  merged_from:
  - trace-init-profile/C-2
  - onboarding-profile/C-1
  - onboarding-profile/C-2
- id: C-4
  sources:
  - docs/design/orqlet-architecture-proposal.md:2350
  - docs/design/orqlet-architecture-proposal.md:4563
  - docs/design/orqlet-architecture-proposal.md:4504
  - docs/design/orqlet-implementation/plan.md:192-194
  - docs/design/orqlet-m2-workflow/design.md:161
  - docs/design/orqlet-implementation/design.md:32
  - docs/design/orqlet-architecture-proposal.md:2350-2350
  - docs/design/orqlet-architecture-proposal.md:4563-4563
  - src/orqlet/interface/cli/commands/init.py:21-60
  note: Sections 13.1 and 23 say `init` takes links at first run and may fetch a standards repository
    or URL. The M1 row of Section 22 lists no importer. The implementation plan says "the documentation
    importer" is not built, the M2 design says "No network" in S8 and S9, and goal G-4 allows only the
    network uses the architecture document lists. Not resolved. The architecture document says that at
    first run `init` takes files, packs and links that the maintainer names and stores them with SOURCE.yaml
    (line 2350). It also says `init` fetches a standards repository or URL when given one (line 4563).
    The options of `init_command` are root, client, answer, target-branch, git-init, new-project, name,
    prompts-dir, packs-dir (a folder), yes, dry-run and json. I found no option that takes a link or URL,
    and SOURCE.yaml does not occur in src.
  merged_from:
  - documents/C-2
  - commands-cli/C-1
- id: C-5
  sources:
  - docs/design/orqlet-architecture-proposal.md:4724
  - src/orqlet/application/usecases/init_project.py:323-327
  - src/orqlet/application/usecases/render_all.py:141-143
  note: The architecture document says `source_id` is "<pack asset id or unknown>". `_with_pr_template`
    always sets `source_id=None`, while `team_template` holds the asset id of the pack's template. Not
    resolved here.
  merged_from:
  - onboarding-profile/C-3
- id: C-6
  sources:
  - src/orqlet/application/usecases/init_questions.py:93-105
  - src/orqlet/application/usecases/init_questions.py:122
  - src/orqlet/application/usecases/draft_profile.py:113-137
  - src/orqlet/application/usecases/diagnose.py:324-334
  note: The branch-naming and commit-convention questions say "leave empty if not". An empty answer is
    dropped, the fact stays a value-less question, and doctor keeps listing it as unknown (ORQ-W181).
    The sources do not say how "there is no rule" is recorded apart from "not answered". Not resolved
    here.
  merged_from:
  - onboarding-profile/C-4
- id: C-7
  sources:
  - src/orqlet/application/contracts/common.py:62-63
  - src/orqlet/application/contracts/profile.py:86-89
  note: '`FactValue` is documented as "a value with evidence, or an unknown with a question. Nothing in
    between." `PullRequests.reviewers` and `merge_strategy` are plain strings defaulting to the text "unknown",
    with no question and no evidence. Not resolved here.'
  merged_from:
  - onboarding-profile/C-5
- id: C-8
  sources:
  - src/orqlet/interface/cli/render_human.py:54-56
  - src/orqlet/application/usecases/init_project.py:94-99
  - src/orqlet/application/usecases/init_project.py:119-121
  - src/orqlet/application/usecases/init_project.py:212-214
  note: The text printed with the open questions says 'answer with --answer KEY=VALUE or run init again'.
    The same result, with the open questions, is returned when the status is applied (init_project.py:212-214).
    A second `init` run then returns already-initialised when the lock file exists (init_project.py:94-99).
    When only a profile file exists, the profile is reused and no question is asked (init_project.py:119-121).
    Not resolved.
  merged_from:
  - trace-init-profile/C-1
- id: C-9
  sources:
  - docs/design/orqlet-architecture-proposal.md:601
  - docs/design/orqlet-architecture-proposal.md:2246
  - src/orqlet/adapters/clients/codex.py:19-23
  note: How Codex is limited by path. The client table row `Path-scoped rules` lists `nested AGENTS.md
    per directory` for Codex (line 601). The placement table says `no per-path rule mechanism; delivered
    through skills` (line 2246). The adapter says Codex has no per-path rules and an agent reads them
    with `orqlet standards for` (codex.py:19-23). Not resolved.
  merged_from:
  - generated-context/C-1
- id: C-10
  sources:
  - docs/design/orqlet-architecture-proposal.md:2239
  - src/orqlet/adapters/render/skills.py:43-52
  - src/orqlet/adapters/clients/codex.py:28-33
  note: The architecture document says client extras such as `disable-model-invocation` go in per-client
    sidecar fragments. The renderer writes `disable-model-invocation` into the one `SKILL.md` that Cursor
    and Codex share, and the adapter records this as limit ORQ-L005. Not resolved.
  merged_from:
  - generated-context/C-2
- id: C-11
  sources:
  - src/orqlet/application/usecases/knowledge_impact.py:57
  - src/orqlet/application/usecases/knowledge_impact.py:233-244
  - src/orqlet/application/usecases/binding_inputs.py:56
  - src/orqlet/application/usecases/binding_inputs.py:161-162
  - src/orqlet/application/contracts/knowledge_config.py:16
  note: The analysis reads .yaml and .yml files as knowledge documents and can load a module card from
    a YAML file. The write scope allows the kind module-card. KnowledgeScope contains only paths that
    end in .md, .rst, .txt or .adoc, so a YAML card path is never inside the knowledge scope. Not resolved
    here.
  merged_from:
  - knowledge/C-2
- id: C-12
  sources:
  - src/orqlet/application/usecases/knowledge_impact.py:3-7
  - src/orqlet/application/usecases/knowledge_impact.py:191-197
  note: The module docstring says paths named by knowledge.yaml as a source or a write scope are reset
    to their merge-base content. The implementation takes the globs of sources whose scope is project
    only, and ignores sources of scope team or company. Not resolved here.
  merged_from:
  - knowledge/C-3
- id: C-13
  sources:
  - src/orqlet/interface/cli/exit_codes.py:12-12
  - src/orqlet/interface/cli/commands/validate.py:37-44
  note: The comment of CHECK_FAILED says 'a read-only check (doctor, sync) found an error'. `output_of`
    also returns CHECK_FAILED for validators when the verdict is FAIL or NOT_RUN, and the gate, evidence,
    knowledge impact and review prepare commands use `output_of`.
  merged_from:
  - commands-cli/C-2
- id: C-14
  sources:
  - src/orqlet/workflow/schemas/orqlet.as-is-fragment.v1.json:79-79
  - src/orqlet/workflow/skills/orqlet-research/references/as-is-format.md:26-26
  note: The committed fragment schema requires fact ids matching A-<n>, an `evidence` list per fact, and
    `base_revision` and `scope` on the fragment. The request for this fragment asks for ids F-<n> and
    `path` and `lines` on each fact, and the role text (orqlet-inventory.md line 10) says the main agent
    adds revision and sha256. I followed the request; the main agent has to map them when it saves the
    fragment.
  merged_from:
  - commands-cli/C-3
- id: C-15
  sources:
  - docs/design/orqlet-architecture-proposal.md:3549
  - docs/design/orqlet-architecture-proposal.md:2890
  - src/orqlet/application/contracts/as_is.py:31-35
  note: Line 3549 allows evidence as 'source URL with retrieval date'. Line 2890 says every fact carries
    path, lines, revision and content hash, and the contract has only path (a repository path), lines,
    revision and sha256. The code accepts only a repository file at a revision. Not resolved here.
  merged_from:
  - web-and-network/C-1
- id: C-16
  sources:
  - docs/design/orqlet-architecture-proposal.md:3151-3152
  - docs/design/mcp-or-plugins/questions.yaml:87-104
  - docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md:3
  note: The architecture document gives the onboarding and research skills 'Read-only; no network'. The
    committed mcp-or-plugins research read vendor pages on the web through the WebSearch tool after a
    ledger answer allowed it. No source says whether the skill rule or the per-task permission governs
    a web lookup inside a skill step.
  merged_from:
  - web-and-network/C-2
- id: C-17
  sources:
  - docs/design/orqlet-architecture-proposal.md:4563
  - src/orqlet/interface/cli/commands/gate.py:34
  - src/orqlet/application/usecases/gate_status.py:3-7
  note: The architecture document lists `gate status --offline` as local only and `gate status` as reading
    the code host. The code has one `gate status` that is read-only and offline, with no `--offline` option,
    and the implement skill says an offline run reports NOT_RUN.
  merged_from:
  - web-and-network/C-3
- id: C-18
  sources:
  - docs/design/harness2-fit/as-is.md:127
  - docs/design/harness2-fit/as-is.md:154
  - docs/design/mcp-or-plugins/as-is.md:525-532
  note: The harness2-fit AS-IS says the artifact format has no evidence form for an external repository,
    a paper or Context7, so those facts stay unvalidated below the front matter. The later mcp-or-plugins
    AS-IS cites stored web excerpts as repository files with path, lines, revision and sha256.
  merged_from:
  - web-and-network/C-4
- id: C-19
  sources:
  - docs/design/orqlet-architecture-proposal.md:1914
  - docs/design/orqlet-architecture-proposal.md:2878
  - docs/design/orqlet-architecture-proposal.md:4719-4726
  - docs/design/orqlet-architecture-proposal.md:4504
  - src/orqlet/application/usecases/init_questions.py:90-104
  - docs/design/orqlet-m2-workflow/plan.md:157
  note: The questionnaire list in Section 9.1.1 does not name branch naming, commit convention, reviewers
    or merge strategy. Section 17.2 and the profile example do. The M1 row of Section 22 names only `repository.target_branch`.
    The built `init_questions.py` asks target branch, branch naming and commit convention (lines 90-104)
    and does not ask reviewers or merge strategy. The M2 plan shows `doctor` warning on both unknown facts.
    Not resolved.
  merged_from:
  - documents/C-1
- id: C-20
  sources:
  - docs/design/orqlet-architecture-proposal.md:1914
  - docs/design/orqlet-architecture-proposal.md:4776
  - docs/design/orqlet-implementation/plan.md:177-188
  - docs/design/orqlet-architecture-proposal.md:4480
  note: 'Section 9.1.1 says the supported-stack catalogue "initially holds one entry, Python", and the
    pack example has `applies_to` with `languages: [python]`. The implementation plan records a `technologies`
    list, Go, Rust, Node, Docker, Compose and Helm scanners, and packs matching on `applies_to.technologies`.
    Section 22.0 mentions a "technology-agnostic profile". Not resolved.'
  merged_from:
  - documents/C-3
- id: C-21
  sources:
  - docs/design/orqlet-architecture-proposal.md:3096
  - docs/design/orqlet-architecture-proposal.md:2363
  - docs/design/orqlet-architecture-proposal.md:5103
  - docs/design/orqlet-architecture-proposal.md:3151
  - README.md:97
  - docs/design/orqlet-implementation/plan.md:192
  - src/orqlet/workflow/skills/orqlet-onboard/skill.md:11-17
  note: Sections 8, 13.3 and 25.2 give `orqlet-onboard` the job of drafting standards proposals from imported
    documentation. The Section 17.10 row lists "Read-only; no network" and only profile steps, README
    line 97 says it resolves unknown profile facts, and the shipped skill text (steps 1-7) has no standards
    drafting. The implementation plan lists "the IDE onboarding agent skill (part two)" as not built.
    Whether "part two" is this skill is not stated. Not resolved.
  merged_from:
  - documents/C-4
- id: C-22
  sources:
  - docs/design/orqlet-architecture-proposal.md:4480
  - docs/design/orqlet-m2-workflow/plan.md:169
  - docs/design/orqlet-implementation/plan.md:145
  - docs/design/open-items/evidence/git-history.txt:5
  - docs/design/open-items/evidence/git-history.txt:35-39
  note: The architecture document (snapshot of 2026-10-22) and both plans say there is no commit and no
    remote. The open-items capture (2026-10-26) lists commits on `main` (for example 2c4308ec) and an
    `origin` remote at github.com/tmishari/orqlet. The statements differ in date; no document says the
    earlier ones were superseded. Not resolved.
  merged_from:
  - documents/C-5
- id: C-23
  sources:
  - docs/design/orqlet-architecture-proposal.md:4516
  - docs/design/orqlet-architecture-proposal.md:4544
  - README.md:34-35
  note: The "Built in MVP-1" column of Section 22 lists `hook`, `ci check` and `ci collect`. README lines
    34-35 and Sections 22.0 and 23 (line 4544) list them as not built. The column may mean target scope;
    the text does not say.
  merged_from:
  - documents/C-6
- id: C-24
  sources:
  - docs/design/orqlet-architecture-proposal.md:2644
  - docs/design/orqlet-implementation/as-is.md:8
  - docs/design/orqlet-implementation/as-is.md:27
  - docs/design/orqlet-m2-workflow/plan.md:10
  note: Section 15.8 treats Context7 as unavailable unless the owners approve it. The implementation as-is
    records "two Context7 documentation lookups" and a session rule "use Context7 for version-sensitive
    APIs", and the M2 plan says "I fetch the current formats with Context7 and the vendor docs". The architecture
    document's rule concerns Orqlet and the implementation uses are agent-session lookups. No document
    reconciles the two. Not resolved.
  merged_from:
  - documents/C-7
self_check:
  schema: orqlet.self-check/v1
  checked_against:
    role: researcher
    phase: research
  checks:
  - what: the person's answers are in the ledger
    how: orqlet validate ledger docs/design/team-conventions-resources/questions.yaml
    result: pass
  - what: bound values copied
    how: orqlet gate status --json at the base revision
    result: pass
  - what: web facts have a file, lines and a hash
    how: each vendor or standard page is stored as verbatim excerpts in docs/design/team-conventions-resources/evidence/web/
      with its address and retrieval time, and facts cite those files with orqlet evidence cite
    result: pass
  - what: absence claims about the code
    how: each one is an unknown that names the words and globs that the researchers searched; the main
      agent did not repeat those searches
    result: pass
  - what: researchers' citations resolve and their quoted words occur in the cited lines
    how: orqlet evidence cite for every range at the base revision, and a token check of every backticked
      word and every quoted phrase; 11 statements were reworded and 3 citations widened after the check
    result: pass
  - what: references resolve
    how: orqlet validate as-is docs/design/team-conventions-resources/as-is.md --fragments docs/design/team-conventions-resources/fragments
    result: pass
  unverified:
  - 'The researchers had no shell: they could not run git, so what they report about files is what the
    working tree held. The two uncommitted P-1 files of the mcp-or-plugins task and its records were excluded
    by instruction.'
  - The vendor pages were read through a fetch tool that returns markdown; the excerpts are cut at the
    places the label names, no client was run, and nothing about client behaviour was observed.
  - 'No unknown was resolved by running the CLI: the researchers read code and tests only.'
---
