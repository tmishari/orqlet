---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: one-command-setup
  status: approved
  workflow_version: 0.5.0
  protected_set_digest: 30746846c7c39faa863c14b2de1940b1f0f7c0eb77250b637ec8bdad970dcb85
  bound:
    applicable_rules_hash: 1c83b7ee5767195f93e48764e551ff9248afc2afffb1b30bb9dc664a471a4c3e
    base_revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    profile_version: 1
    standards_lock_hash: 845aa1cb914dd3b09d52690216045e589e589f5e57292ec5b153d5cd73c4f330
base_revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
scope:
  paths:
  - src/orqlet/**
  - tests/**
  - tools/**
  - scripts/**
  - .github/workflows/**
  - pyproject.toml
  - README.md
  - docs/design/one-command-setup/evidence/**
  - uv.lock
  - AGENTS.md
  - .prompts/rules.yaml
  - .orqlet/project-profile.yaml
  - docs/design/mcp-or-plugins/design/adr-001-committed-files-stay-the-shared-channel.md
  - docs/design/one-command-setup/questions.yaml
  request_ref: one-command-setup
research_mode: parallel-subagents
size_budget:
  max_words: 3800
facts:
- id: A-1
  kind: operation
  statement: The README installs Orqlet with uv from a checkout or a pinned Git revision and
    lists Python, uv and Git as prerequisites.
  evidence:
  - path: README.md
    lines: 71-96
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: badfd93bf1c48744c7c8e1f1c7714f1e6a6a6d7983caf08439f94381730c283d
- id: A-2
  kind: interface
  statement: The Typer application shows help with no arguments and registers init and upgrade;
    it has no setup or install subcommand.
  evidence:
  - path: src/orqlet/interface/cli/app.py
    lines: 30-60
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 22bd88259194cc6899c81be4a268e9878e85891892d31b806331e202323763c4
- id: A-3
  kind: flow
  statement: The workflow loader reads skill.md files and Markdown references, accepting only
    one-line name and description front-matter fields for skills.
  evidence:
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 29-53
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 894cca8b35c0d3338e6c1d544b350ef4830166afa8723de7fa4dd3e58310241c
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 104-137
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 226f4c3774d9a87505f236679a5afda0be17d1cc49e7e8254580c25e8711afef
- id: A-4
  kind: flow
  statement: The renderer writes Claude Code skills under .claude/skills and shared Cursor/Codex
    skills under .agents/skills, including references and protected ownership.
  evidence:
  - path: src/orqlet/adapters/render/skills.py
    lines: 20-87
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: d5f955869df693d759317f1f14fdd42867f2dc402de478e570b722cec2968aeb
- id: A-5
  kind: flow
  statement: Render requests combine packaged workflow skills with team resource skills, then
    apply optional model settings.
  evidence:
  - path: src/orqlet/application/usecases/render_request.py
    lines: 116-135
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: a3a5f2a869572ae4ad89aee322f7f78dc804bd08152664be2a2abed582508867
- id: A-6
  kind: test
  statement: The installation smoke tests install a built wheel into an isolated environment
    and cover version reporting, init, doctor, dry-run and packaged skills.
  evidence:
  - path: tests/e2e/test_install_smoke.py
    lines: 26-131
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 453e7174a697ecdf0562318fc03e46cb5e7187e6a882a869053100f4114096d9
- id: A-7
  kind: operation
  statement: CI pins uv 0.7.19, tests three operating systems and Python 3.12 through 3.15,
    and builds wheels without a publication job.
  evidence:
  - path: .github/workflows/ci.yml
    lines: 13-107
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 84ee7b99711e3051e0387c53d402f6d720f2db1ef6846c6e72496b7b6c0e9f1e
- id: A-8
  kind: dependency
  statement: The inspected Graphify source declares graphifyy 0.9.112, Python below 3.15,
    platform-specific skill dispatch, dependency installation instructions and separate optional
    model/media extras.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/graphify.md
    lines: 1-26
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 5343040961e29dc9d56cb31734631e4ba3232bdae430aec8c8a6204471e78021
- id: A-9
  kind: dependency
  statement: The inspected Ponytail 5.3.3 source contains six skills; help describes executable
    plugin features beyond the Markdown skills, and the skills use front-matter forms outside
    the Orqlet loader format.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/ponytail.md
    lines: 1-29
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: fe351cea44b13c6e4ff57635604cfa6bb22751c56a1b4d7f21373f4cfe362768
- id: A-10
  kind: dependency
  statement: Current official uv documentation describes version-specific standalone installers,
    managed Python downloads, isolated tool environments and interpreter selection.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/uv.md
    lines: 1-15
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: b8f8bbbedb91f3083699e802c0d3821a6973ef4d35dcd81538a80e3d1541d30b
- id: A-11
  kind: structure
  statement: The packaged workflow reads manifest-listed files, verifies their hashes, and
    exposes its release identity and history.
  evidence:
  - path: src/orqlet/adapters/workflow_package.py
    lines: 24-84
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: fdeaf788abcd242e85952bb8a6411515ba51c0208c947f618d807f08b1281aa4
- id: A-12
  kind: interface
  statement: The ProcessRunner port accepts an argument sequence, explicit environment, timeout
    and output limit.
  evidence:
  - path: src/orqlet/application/ports/process.py
    lines: 33-44
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 9402f85e1e1ef8fe8e5eda07d82591e7ec462ce6b90c3d105869e8df537e9a91
- id: A-13
  kind: interface
  statement: PersonalNames and FsPersonalNames provide opt-in names-only inspection of personal
    skill and agent directories.
  evidence:
  - path: src/orqlet/adapters/scan/personal_names.py
    lines: 1-38
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: ab1e15dbba9f83415b6ba292625ca477486ddd67b2774a87fbbc6c4d18f070e0
- id: A-14
  kind: interface
  statement: Human output is plain text and the CLI runner selects a separate JSON envelope
    when as_json is requested.
  evidence:
  - path: src/orqlet/interface/cli/runner.py
    lines: 29-60
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 7f5f245d368cf2641aa6da4982ce1090c1557263ce54a0b45bab985fdbf45085
- id: A-15
  kind: dependency
  statement: The inspected uv documentation describes persistent user-wide isolated tool installation
    and notes that dependency executables are not exposed automatically.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/global-setup.md
    lines: 9-17
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: cdb7ebd51cf6931b7e8188d6346d3d24c7c6cd9bfca69574351dfc93155e7092
- id: A-16
  kind: dependency
  statement: Cursor documents user skill and agent directories, User Rules in Customize, and
    user-scoped plugin installation; the inspected pages do not establish an unattended User
    Rules installation command.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/global-setup.md
    lines: 18-30
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 206e2b67ebfcaaf17474f1ea166af19d056adfd35893cc46bf32ce8aee83d18e
- id: A-17
  kind: dependency
  statement: Codex documents user-global instructions, skills and agent locations; its skills
    documentation says same-named skills are not merged and both can appear in selectors.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/global-setup.md
    lines: 31-41
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 0dafd64e32e64f1c58c31213011858240922f1c22e307dd38a369b927937e3f0
- id: A-18
  kind: dependency
  statement: The inspected Claude Code documentation describes user instructions, personal
    rules and personal subagents, while the stored skills evidence records the personal skills
    location.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/global-setup.md
    lines: 42-51
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: eedb4883ea834bcbf8b5786f9310c55a3de383cd49695445c619de85ee6616ce
- id: A-19
  kind: flow
  statement: 'Packaged workflow skills are built without agent_may_start, and the renderer
    then marks them person-started: disable-model-invocation for Claude Code and Cursor and
    an agents/openai.yaml sidecar with allow_implicit_invocation false for Codex.'
  evidence:
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 104-137
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 226f4c3774d9a87505f236679a5afda0be17d1cc49e7e8254580c25e8711afef
  - path: src/orqlet/adapters/render/skills.py
    lines: 1-8
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 8b2624c714cd0fa1dfde920225a752d390b185132f241dabff9d5d24618edf02
  - path: src/orqlet/adapters/render/skills.py
    lines: 41-59
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 777be32a19269c248c440d80a0d19dbdd21f79938a35984aaa6a88100168b655
- id: A-20
  kind: operation
  statement: Each phase skill directs the agent to run its own series of CLI checks (models
    resolve, standards for, gate status, evidence cite or hash, and a validator) inside the
    session.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 26-37
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: ca65e74bf60100ded3d8bfad95839a4ada1ca6ad05942e2ba90b566799598bbf
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: 26-37
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 4f7a1621f53ffe7be40e81899b19c19f1c8a41243d1ecf54ad5432bdc9096f9e
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: 27-37
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: f4b194ac703b0a155b573e7ed688a7e63b12070d7fa54df574dec2a648eddba9
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: 27-40
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 3f65662b623c95c5dfeb59e0bd07b689b555ec3eecb0380071a571b13ea69245
  - path: src/orqlet/workflow/skills/orqlet-review/skill.md
    lines: 25-35
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: ad2882ae3ee7a23fc70597e59dcb8e4ce74d8072094f55841a6b99d3ea3112df
  - path: src/orqlet/workflow/skills/orqlet-onboard/skill.md
    lines: 26-37
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: dbdecc17e7e36ebd2e3de6e37c04bd0a3c2a2f4cfdabc24ca20089114172c7d2
- id: A-21
  kind: flow
  statement: Every phase skill ends in a STOP for a human decision (profile approval, AS-IS
    acceptance, design or plan pull request, phase acceptance, review decision), and its Next
    section has the person invoke the following skill by slash command.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/skill.md
    lines: 56-58
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 37abb79e155601d38300d5708b746e60ebac2ea5f2e447c6393fccad6ef8ad5e
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: 56-58
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 2cb3533597ee1cb24e0a110967bc4d19c461d80126da07e8e5d5d9e45e6d3cc7
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: 55-57
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: eb3072a4867cf267c48f49adf8823ee95503dfa62f77331068f026205e31b98c
  - path: src/orqlet/workflow/skills/orqlet-implement/skill.md
    lines: 58-60
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: b49e7270c032d80215dc25bb3f5d1c6946033622a14374fb0306b1b34f2d9579
- id: A-22
  kind: operation
  statement: The phase contract has the agent copy bound values from gate status into each
    artifact header and run an input check of validator and git commands, with the person
    naming the protected ref and merge commits.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md
    lines: 41-56
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: ff6c73e85be7c76c91698859bc508f9f357d30194181fdec7fa7fe2497967e03
  - path: src/orqlet/workflow/skills/orqlet-research/references/phase-contract.md
    lines: 77-79
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 377feb44a6a54f782b1dbc9000877393378fed3c66b5215164ef90013aae495d
- id: A-23
  kind: structure
  statement: ADR-001 of mcp-or-plugins decides that shared MCP configuration, skills, agents,
    rules and instructions reach developers as committed files with no plugin output, and
    allows a later plugin output only under conditions C1-C4 about credentials, repository
    review and surface coverage.
  evidence:
  - path: docs/design/mcp-or-plugins/design/adr-001-committed-files-stay-the-shared-channel.md
    lines: '3'
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: ae95be8aa84f6d4bef9d0cc26ebda524a556f62683705242d9c1453e164c682c
  - path: docs/design/mcp-or-plugins/design/adr-001-committed-files-stay-the-shared-channel.md
    lines: 20-25
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 64f9d72e7438936196e85b7115976678e914c3d97b7a93abcae75cb74cab628f
- id: A-24
  kind: structure
  statement: The closed client set is claude-code, codex and cursor; standard ORQLET-ARCH-003
    and an import-linter independence contract name exactly those three adapters.
  evidence:
  - path: src/orqlet/application/contracts/common.py
    lines: 27-28
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 146455aa4552c554ad99b37ca76da8f7df8d91ef60b65424d6e93459af074d8f
  - path: .prompts/rules.yaml
    lines: 29-33
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: f4f5b6412ebabb7fd8f2e95fc1ebe77a0d66af47362bbae43ab5bf1d48d27bd8
  - path: pyproject.toml
    lines: 120-127
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 59b3a5a0b1246ebdfe55a499ab897966cf403442bc579910ee037ce50f9be8ad
- id: A-25
  kind: flow
  statement: The three client adapters render AGENTS.md blocks, skills, roles and client rules,
    commands or MCP files; none renders a hook or client settings file.
  evidence:
  - path: src/orqlet/adapters/clients/claude_code.py
    lines: 58-72
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 300b636dbbaf6fa564b68eb415265c2de7c9c5af00cade8042aeadd960544ad0
  - path: src/orqlet/adapters/clients/codex.py
    lines: 48-67
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 949e6a9174b72d81a654d0ef62a15f2cbd778c7dfd622dd0b7a93e373e1c4430
  - path: src/orqlet/adapters/clients/cursor.py
    lines: 42-57
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 65ad1e75319b5e53ebf6080af3c8c1e9025e4ef1023831ae161183572d4fa30d
- id: A-26
  kind: dependency
  statement: The package requires Python 3.12 or later, pins typer, pydantic, PyYAML, filelock
    and platformdirs, and exposes one orqlet console script.
  evidence:
  - path: pyproject.toml
    lines: 9-19
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 8cf36361cc43fa976fefa61e3fb683afe2c8551e64e833dd58210fd66fb657de
- id: A-27
  kind: interface
  statement: LocalFileSystem is confined to one resolved root and refuses links, while journals
    and backups live in ORQLET_DATA_DIR or the platform user data directory.
  evidence:
  - path: src/orqlet/adapters/fs/local_fs.py
    lines: 72-81
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: d8fdfad46c80f220c516ab30aaf992d47f4823e2b656de672c74e150cdd53864
  - path: src/orqlet/adapters/fs/journal.py
    lines: 1-8
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 14dd07be521d789202ee8eff84f1d237e64d178dcbb016423b3f3c43edf6784c
  - path: src/orqlet/interface/cli/wiring.py
    lines: 76-81
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: e4725ea7e16dc19722bb08ffbd31d9a39c37f0e0f2976233b05855f6d097ffa6
- id: A-28
  kind: flow
  statement: init takes its root from --root, defaulting to the current directory, and refuses
    with ORQ-E110 when git rev-parse --show-toplevel shows the directory is nested in another
    repository.
  evidence:
  - path: src/orqlet/interface/cli/commands/init.py
    lines: 21-24
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: deb83028f531efb2f72df717142fe5cafa67acec75682bab8d48d8a157166619
  - path: src/orqlet/application/usecases/init_state.py
    lines: 41-50
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 8a53d7550d3f169c2839372bd3e5bc7fa629d184ab4fb175df132c38639a1956
  - path: src/orqlet/adapters/git/vcs_git.py
    lines: 44-59
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: a23ed04c09ef4e4d0ea35fa208bcf07be39773d19a92027529fa547d3bb16cec
- id: A-29
  kind: interface
  statement: GitRunner allows a fixed list of read subcommands with hooks off, a scrubbed
    environment, a timeout and an output cap, and the ProcessRunner port is documented as
    used by the Git adapter only.
  evidence:
  - path: src/orqlet/adapters/git/git_runner.py
    lines: 18-50
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: d17b43b2115241c8c6151c9d388e56a3e07af7d9ac51d384dd3092323c5d84f9
  - path: src/orqlet/application/ports/process.py
    lines: '1'
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 71741238a211a8fda7691edd43faa631b1189d11d72c4dcd327ec1102126ad5f
- id: A-30
  kind: interface
  statement: Exit codes are 0 ok, 1 problems, 2 usage, 3 refused, 4 needs input, 5 check failed
    and 70 internal, and validators, gate status and evidence exit 5 for both FAIL and NOT_RUN.
  evidence:
  - path: src/orqlet/interface/cli/exit_codes.py
    lines: 6-13
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 97f98f5b0f5262ac86f053a80e9878de0a660c34aafaf9f51f7d6655e736491f
  - path: src/orqlet/interface/cli/commands/validate.py
    lines: 40-49
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 9d61d95633dd5d6239fbbba3aaea56b656f0124e0b850dfe3de6c7f98fc9c9cc
- id: A-31
  kind: flow
  statement: apply_plan takes a file lock, refuses a tree changed since the preview, backs
    up, journals and writes atomically with the manifest last.
  evidence:
  - path: src/orqlet/application/usecases/apply_plan.py
    lines: 49-79
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 01b3dc44961a1d4762d7ace233bc9aaf4f043f2e92add23bd6efa776b430bc3a
- id: A-32
  kind: operation
  statement: gate status reads the .orqlet records and git HEAD, and doctor hashes every non-seeded
    manifest file and reads the journal; both are local and read-only toward the repository.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 80-123
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 47b125b8e46a84ea2ae3626dd7262c3e6203854cec92bf5a018bb1ae53494326
  - path: src/orqlet/application/usecases/diagnose.py
    lines: 118-162
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 0d86a4d1b7545902599316a5d2b0e92c6f0883c847045eaf0ccf54aee24d301f
- id: A-33
  kind: operation
  statement: The README Day to day section lists sync, doctor, explain, upgrade and rollback
    as terminal commands.
  evidence:
  - path: README.md
    lines: 300-310
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: c12db07134bd4856c5d64e6074712280e2d1dd64354e3fdd4a4069d2f2b44f78
- id: A-34
  kind: dependency
  statement: Claude Code documents user, project, plugin and skill hook sources that merge,
    SessionStart sources including compact, a 10,000-character context cap, non-blocking timeouts
    unless onFailure is block, stop_hook_active loop protection and only a global disableAllHooks
    switch.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 11-26
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: fb2a2dc83c5e830af0838b2b7672d0b18f80aec7269caeafa78df8e87ac0ba2f
- id: A-35
  kind: dependency
  statement: Cursor documents user, project and plugin hooks.json sources that all run, a
    fire-and-forget sessionStart with additional_context, an observational preCompact, failClosed
    and loop_limit options, and loading of Claude Code settings hooks through a third-party
    setting that is on by default.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 28-49
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 189ffa8b3497dda24ce5ac68a42c04119fbb77c13e24f8cf47c26dd3680519ec
- id: A-36
  kind: dependency
  statement: Cursor documents user- or project-scope plugins carrying rules, skills and hooks,
    a ~/.cursor/plugins/local folder loaded after reload when local imports are allowed (off
    by default on Enterprise), and plugin rules with alwaysApply.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 51-60
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: a93932e8e85526124771deb90d372c25948fa4daa66c8f65d7ef4b71a2d6fbf1
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 144-151
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 397c7cb6b7845645ae5e9956632c2211d0c9f447f1e7bae78c6b445899cf88c2
- id: A-37
  kind: dependency
  statement: Codex documents user and trusted-project hooks that all run and can run twice,
    hash-keyed trust reviewed through /hooks in the CLI, a 600-second default timeout, a 2,500-token
    context default and SessionStart re-runs after compaction; the page does not mention the
    IDE extension.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 62-77
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: c398a97731bd865eb27a4b3fc133693bd46db33f9aa25c8e815ee08787ee3db7
- id: A-38
  kind: dependency
  statement: Codex documents no plugin support in the IDE extension, standalone skills there
    invoked with $ or /skills from $HOME/.agents/skills, settings shared with the CLI through
    config.toml, and no /hooks command in the IDE slash-command list.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 79-95
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: e76b21b6f874ad51b6193676e90a8ed178d479acd8a71205a12efc86b61741e3
- id: A-39
  kind: dependency
  statement: VS Code documents that hook behaviour follows the selected harness; the Copilot
    harness reads ~/.copilot/hooks, .github/hooks and the repository .claude/settings.json,
    runs all applicable sources together, and is not proven by a file shown in the editor.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 97-109
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 447a269b7b01297914f4aebc0c085145d642b0f762beb2a46ee7c13fb1726d2e
- id: A-40
  kind: dependency
  statement: GitHub Copilot documents combined policy, user, project and plugin hooks, a 30-second
    default timeout, sessionStart sources startup, resume and new with additionalContext only,
    fail-open timeouts and fail-closed preToolUse errors.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 111-120
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 6e8e9ea5847d3160c1c77c1dbb093a9116a1769bea2ba4130c6c3ae41bd0a23f
- id: A-41
  kind: dependency
  statement: VS Code documents Copilot skills in .github/skills and ~/.copilot/skills invoked
    by slash command, the disable-model-invocation field, name-equals-folder loading, a chat.plugins.enabled
    setting and plugin installs that cannot bypass trust prompts.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 122-133
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 4f7fa8415474a6e0b8336326022d8defe086734542ce7f8053f0818c07dbdded
- id: A-42
  kind: dependency
  statement: Claude Code documents that a personal skill wins over a project skill of the
    same name, and that claude plugin install runs from a shell at user scope by default.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-integration-contracts.md
    lines: 135-142
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 61cfa1d620a5a23bdf9631d68f7d8aa5c168000c4cccf71749d38ffe046b84d3
- id: A-43
  kind: dependency
  statement: The development machine has Claude Code 2.1.303, the Cursor CLI 3.31.11, VS Code
    1.145.0 with no Copilot or Codex extension listed, uv 0.7.19, pipx 1.18.16, and no codex
    executable on PATH.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/client-versions.md
    lines: 1-17
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: cacecbbea1a82306d80e55bc61f408a8b693196e3da3caa25301fd9e427642c5
- id: A-44
  kind: structure
  statement: The AGENTS.md baseline tells every task not to guess and to ask, to keep facts
    and decisions apart, to follow existing conventions, to prefer the simplest design that
    meets the stated requirement with no unrequested options, layers or abstractions, to handle
    failures and validate input where it enters, to test the behaviour, to update the documentation
    it makes wrong and to verify with evidence, reporting a check that did not run as not
    run.
  evidence:
  - path: AGENTS.md
    lines: 8-16
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 1105dbd97766b8da4eddb551ed82ebe805f4f13592716d4576d9ce54b33f68f1
- id: A-45
  kind: structure
  statement: Standard ORQLET-TEST-001 requires behaviour tests for a change, and ORQLET-STYLE-001,
    a non-mandatory rule, asks for small functions with one reason to change, meaningful names
    and comments that explain why.
  evidence:
  - path: .prompts/rules.yaml
    lines: 111-115
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 6f8505cd17fac326af378a6b880a754180b6792073f278be1bb5c2874a180c32
  - path: .prompts/rules.yaml
    lines: 137-141
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: c2fbb8c5211d253a46cd4cd5a33e0d12cb9b24065c34604167311254b445ebf0
- id: A-46
  kind: flow
  statement: Change classification computes a trigger class from the scope (D3 for listed
    trust, integration and infrastructure reasons or a D3 glob, D2 when any D1 condition breaks,
    else D1) and takes the maximum of the trigger, the declared class and an approver's raise,
    so D1 is the lowest class.
  evidence:
  - path: src/orqlet/domain/change_class.py
    lines: 59-94
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 8937018b5ad1fbd9208b2bc3d138690e3ed85b266846b66e49b4d151583757ea
  - path: src/orqlet/workflow/skills/orqlet-design/references/design-format.md
    lines: 7-17
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: a8e3997629cec01db60c5c0b97e6c00174d7233800e297b8ced71112e1f8d32d
- id: A-47
  kind: structure
  statement: 'Every class requires a design set: D1 a component view, a data-flow diagram,
    a sequence diagram and an ADR or adr-not-required entry; D2 adds a container view and
    two reviewer notes; D3 adds a context view and a real ADR. The design skill states that
    the class sets how deep the work goes, never whether it happens.'
  evidence:
  - path: src/orqlet/domain/change_class.py
    lines: 132-159
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 1e6abaeba9a381dd689848c270c94dfd404896949d2f9cd2785b8023fc20f327
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: '7'
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: c688da903660cc0cb2644643ed7a9a8be4d3346d0738304edd6412db1cbb188f
- id: A-48
  kind: flow
  statement: For a D1 change the design skill lets the plan follow the design and the plan
    skill lets the plan be drafted from the validated design; neither skill removes the research
    or design phase for D1.
  evidence:
  - path: src/orqlet/workflow/skills/orqlet-design/skill.md
    lines: '58'
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 083d0c340ba2d2ec1e52250250850cd98ae3e832de0a0f817a629c964d505f6a
  - path: src/orqlet/workflow/skills/orqlet-plan/skill.md
    lines: '27'
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 436e1fe56fb11d67d886e704474a850275707e0e471d561f6dab05f9de735f92
- id: A-49
  kind: structure
  statement: The project profile names task branches by task and phase and other work by a
    short kebab-case name, with a fix-* branch pattern.
  evidence:
  - path: .orqlet/project-profile.yaml
    lines: '42'
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: fc9c27b4833a109664ec77f37d5178792bd88c0ed8055c693fca535fab48cb2c
  - path: .orqlet/project-profile.yaml
    lines: '58'
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: ba9740a7734672b1bb828dd64a2313fa6c179059254170bba2fe3d97e42686ba
- id: A-50
  kind: interface
  statement: render_human.py describes its output as plain text for people with no colour
    codes so that it reads the same in a log.
  evidence:
  - path: src/orqlet/interface/cli/render_human.py
    lines: '1'
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: b42519121e8f05223893b76a61392b92438e357ec8d81a0e224767f175b41c74
- id: A-51
  kind: dependency
  statement: The lock file pins typer 0.27.3 with dependencies rich, shellingham and, on Windows
    only, colorama, so Rich is installed with Orqlet without a direct dependency.
  evidence:
  - path: uv.lock
    lines: 822-830
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 32df43e3a64759c3d3a68f90502fb5f89caa50128c6a247cff9f63dfff7c67ac
- id: A-52
  kind: operation
  statement: The CI test job runs pytest on ubuntu-latest, macos-latest and windows-latest
    for Python 3.12 to 3.15.
  evidence:
  - path: .github/workflows/ci.yml
    lines: 70-85
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 0362ac04088e4c55f64a2eaf083ec0390004fcc015136b86c0d7adad01966e6f
- id: A-53
  kind: dependency
  statement: Rich 15.0.0 documents stripping control codes and dropping animations when output
    is not a terminal, disabling colour and style for TERM dumb or unknown, FORCE_COLOR enabling
    colour, NO_COLOR disabling colour with precedence over FORCE_COLOR, TTY_COMPATIBLE and
    TTY_INTERACTIVE for CI, eight colours on legacy Windows terminals, and wrapping to the
    current width unless a width is set.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/terminal-rendering.md
    lines: 10-21
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 1a774f9bc51a2f4cc4545dd377184719eeba0da2376c94d5cbe50cb8c85d80e4
- id: A-54
  kind: dependency
  statement: Rich 15.0.0 documents box glyphs that legacy cmd.exe raster fonts do not display,
    substitutes an ASCII box when the console is ascii_only, and no automatic ASCII substitute
    for other Unicode icon characters was found in its installed source; the NO_COLOR convention
    asks software that adds ANSI colour by default to suppress it when NO_COLOR is present
    and non-empty.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/terminal-rendering.md
    lines: 23-31
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: cdc5ac3230523505ef40277642982ae857d2d1404c7730fbaaae6e8cd4634ab6
  - path: docs/design/one-command-setup/evidence/web/terminal-rendering.md
    lines: 33-37
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 731e1379089c11ba933ad0e8a603b243cd10b140caaa161ed031d630041b92a0
- id: A-55
  kind: dependency
  statement: At revision 2c60614 the andrej-karpathy-skills repository has no LICENSE or NOTICE
    file and a null licence in repository metadata, declares MIT in its README, skill front
    matter and plugin.json without naming a copyright holder, names forrestchang as author,
    and the forrestchang repository address redirects to multica-ai.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/karpathy-skills.md
    lines: 12-18
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 9fa2d3e47e0b37bcf35b1e5f39c04290c3b61cec1466553aa471b5a042ccb058
- id: A-56
  kind: dependency
  statement: The upstream skill states four principles (think before coding, simplicity first,
    surgical changes, goal-driven execution), a bias toward caution with judgment for trivial
    tasks, and lines that include presenting multiple interpretations, pushing back, no error
    handling for impossible scenarios, mentioning but not deleting unrelated dead code, removing
    only orphans the change created, and a step-then-verify plan.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/karpathy-skills.md
    lines: 31-39
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 090a18b52c6ef100cdb1dc59fe862e4a8fccc74d5675df4b75872d89bad71eec
- id: A-57
  kind: dependency
  statement: The upstream delivers the guidance as an alwaysApply Cursor rule, a Claude Code
    plugin marketplace, an unpinned curl of CLAUDE.md from main and a CLAUDE.md copy kept
    in sync by hand, and its CURSOR.md says Cursor does not read .claude-plugin or CLAUDE.md
    by default.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/karpathy-skills.md
    lines: 41-47
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: ceaee2e36bbb1406bdda4efd1605db9644e6fbcf60b2479007720b0601829a19
- id: A-58
  kind: dependency
  statement: Ponytail at revision 96608e0 is MIT with copyright DietrichGebert; its main skill
    stays active for the session, lists the places a change must reach, orders options from
    not building through existing code, the standard library and dependencies, keeps the existing
    structure, prefers deletion, requires a small test for non-trivial logic, never cuts validation
    at trust boundaries, data-loss error handling, security or accessibility, and ends each
    reply with what was skipped; its default level is full, lite names the smaller option
    and lets the user pick, and ultra also questions the request and pushes back on any part
    the need does not justify.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/ponytail-skill.md
    lines: 12-21
    revision: e9b0683e7d2797355ddd943c7c8b914b8780e4fd
    sha256: 0f9801ef9ea44c74da290a4c9e9d8703d243068af981669b333a663c9152b219
unknowns:
- id: U-1
  what: Whether hooks run in the Codex VS Code extension and how a user trusts them there;
    the official pages are silent (A-37, A-38).
  material: true
  question_ref: Q-20
- id: U-2
  what: Whether VS Code 1.145.0 on the development machine provides Copilot Agent mode, and
    which Codex extension version would be qualified; neither extension is listed (A-43).
  material: true
  question_ref: Q-24
- id: U-3
  what: Whether an always-applied rule in a user-scope Cursor plugin reaches the agent as
    a User Rule does, so that it can replace the guided User Rules step (A-36).
  material: true
  question_ref: Q-9
- id: U-4
  what: How init, upgrade and the journal behave in a linked Git worktree; no test or GitRunner
    subcommand covers worktrees, and journals are keyed by the profile project id (A-27, A-28).
  material: true
  question_ref: Q-24
- id: U-5
  what: Whether the payload contracts and context limits quoted from current pages apply to
    the installed client versions; no page names the release it describes, and the Claude
    Code page cites a feature from v2.1.304 against an installed 2.1.303 (A-34, A-43).
  material: true
  question_ref: Q-24
- id: U-6
  what: Which icon glyphs display in PowerShell, Windows Terminal and legacy consoles, and
    how a glyph falls back to ASCII; Rich substitutes boxes only (A-54).
  material: true
  question_ref: Q-29
- id: U-7
  what: The narrowest terminal width the install output supports and how a banner and status
    lines behave below it; Rich wraps to the current width (A-53).
  material: true
  question_ref: Q-29
- id: U-8
  what: Whether Cursor 3.31.11 reads a repository CLAUDE.md or .claude-plugin folder with
    the third-party import setting on, which decides whether guidance can appear twice in
    Cursor (A-35, A-57).
  material: true
  question_ref: Q-24
- id: U-9
  what: The copyright holder of the andrej-karpathy-skills text; no tracked file names one
    (A-55).
  material: false
  question_ref: Q-27
contradictions:
- id: C-1
  sources:
  - README.md:332
  - src/orqlet/workflow/skills/orqlet-review/skill.md:6
  note: The README says orqlet-review starts the architecture and security reviews; the skill
    also starts the code reviewer.
- id: C-2
  sources:
  - src/orqlet/workflow/skills/orqlet-onboard/skill.md:3
  - src/orqlet/adapters/render/skills.py:41-59
  note: The onboard description reads as model-startable, but every packaged workflow skill
    is rendered person-started only.
- id: C-3
  sources:
  - src/orqlet/interface/cli/commands/lifecycle.py:203
  - src/orqlet/interface/cli/wiring.py:80
  note: doctor says it writes nothing, but its wiring creates the user data directory.
- id: C-4
  sources:
  - docs/design/one-command-setup/questions.yaml:Q-7
  - docs/design/one-command-setup/questions.yaml:Q-21
  - .prompts/rules.yaml:29-33
  note: Q-7 and ORQLET-ARCH-003 name three clients; Q-21 adds GitHub Copilot in VS Code as
    a fourth supported assistant.
- id: C-5
  sources:
  - docs/design/one-command-setup/evidence/web/karpathy-skills.md:46
  - docs/design/one-command-setup/evidence/web/client-integration-contracts.md:46
  note: The upstream says Cursor does not read .claude-plugin or CLAUDE.md by default; Cursor
    documents third-party plugins, skills and other configs as included by default.
- id: C-6
  sources:
  - docs/design/one-command-setup/evidence/web/karpathy-skills.md:35
  - AGENTS.md:13
  - docs/design/one-command-setup/evidence/web/ponytail-skill.md:19
  note: The upstream simplicity list says no error handling for impossible scenarios with
    no guard; the baseline says handle failures explicitly and Ponytail never cuts data-loss
    error handling or trust-boundary validation.
- id: C-7
  sources:
  - docs/design/one-command-setup/evidence/web/karpathy-skills.md:39
  - src/orqlet/workflow/skills/orqlet-design/skill.md:7
  - docs/design/one-command-setup/questions.yaml:Q-31
  note: The upstream says not every change needs the full rigor; Orqlet's design skill says
    the class never decides whether the work happens, and the person confirms every change
    goes through all four phases.
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
    - Q-7
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
    - Q-22
    - Q-23
    - Q-24
    - Q-25
    - Q-26
    - Q-27
    - Q-28
    - Q-29
    - Q-30
    - Q-31
    applicable_standards:
    - ORQLET-NOMODEL-001
    - ORQLET-ARCH-001
    - ORQLET-ARCH-003
    - ORQLET-DET-002
    - ORQLET-SEC-001
    - ORQLET-SEC-002
    - ORQLET-SEC-003
    - ORQLET-TEST-001
    - ORQLET-QA-001
    - ORQLET-MODEL-001
    - ORQLET-STYLE-001
  checks:
  - what: Every fact reference resolves at the bound revision
    how: orqlet evidence cite returned PASS for all 94 references at e9b0683 on 2026-11-20
    result: pass
  - what: The person accepted the AS-IS file
    how: tmishari replied "approved" in the chat at 2026-11-20T12:30:00+00:00 (14:30 UTC+2),
      after fixes for timeout blocking, freshness scope and Ponytail push-back
    result: pass
  - what: Question ledger
    how: orqlet validate ledger docs/design/one-command-setup/questions.yaml returned PASS
      with 31 answered questions
    result: pass
  unverified:
  - No hook, plugin, skill, upstream installer or native session was executed; native-client
    qualification is NOT_RUN.
  - Context7 was available in this session and was queried once, for Claude Code, as a cross-check
    that agreed with the official page; the other clients rest on official pages only.
  - 'Applicable rule hashes printed by standards for: src/** paths 88e3e089ba38309c8acd8084933e2b62fc9109d1d8430c54e72f355cdff0c57d,
    workflow skills 40e406a16a333298f6ea2471e82a043ddceafaf5a13e8fec9d8cfb0bf285630a, tests
    bf7e3320dfee207b9f60f217769bde90b959d4bf5a5c43419c356dea8aab62ed, pyproject and CI 7cedb45ea31f8900517dcaca99243b1d35b05b37792a98fd1c45d16b2bf75038,
    evidence files 9943630aa1feabdb4265d49265f94ba8a08d73e9eb347af3e4597d550da41b34.'
  - PyPI ownership of orqlet is the person's statement (Q-18); publication and installation
    from PyPI were not verified.
  - Main has advanced to 20cb0a7 (release 0.4.0); in scope it changes only README.md lines
    and the version string, not the cited lines of this branch; it changes none of uv.lock,
    AGENTS.md, .prompts, the project profile or the mcp-or-plugins design.
  - The andrej-karpathy-skills and Ponytail texts were read at pinned revisions only; no upstream
    installer, plugin or curl route was run.
  - No banner, icon or layout was rendered in bash, zsh, PowerShell or a legacy console; terminal
    behaviour rests on Rich documentation and source reading and is NOT_RUN.
  - A search of src for imports of rich returned no match at 86efd3a.
  - Design approval and plan approval have not been given.
---

## Request

Make Orqlet easy and intuitive: install the CLI with `uv tool install orqlet` (or `pipx install orqlet`), run `orqlet install` once in a terminal to register every detected supported assistant, then describe work normally in the assistant, invoking `/orqlet .` (Codex: `$orqlet .`) only for setup, help and recovery. Native skills, hooks, plugins and instruction files supply guidance and lightweight checks automatically; the person sees material questions, actionable failures and real approval decisions. Engineering controls stay (Q-10–Q-16, Q-21–Q-26). Supported: Claude Code, Cursor, Codex including its VS Code extension, and GitHub Copilot Agent mode in VS Code (Q-13, Q-21), for individual and administered accounts (Q-19). The person controls the PyPI name `orqlet` (Q-18) but publication needs separate authorization (Q-25). Added on 2026-11-20: compare the Karpathy-inspired guidance with Orqlet's own guidance toward one behavioural foundation without vendoring its text (Q-27, Q-28), document how ceremony scales with the size of work (Q-30, Q-31), and record what the terminal can deliver for a polished `orqlet install` (Q-29).

## Scope

This refresh adds the native hook, plugin and skill contracts of all four assistants, the current phase-skill friction, the client and write infrastructure, the init/upgrade/check traces and the installed client versions (A-19–A-43) to the earlier installer and upstream-skill facts (A-1–A-18). Three read-only subagents mapped the repository, and one official page per contract was excerpted. The addition covers the AGENTS.md baseline, standards, change classes, the human renderer, the installed terminal library and two upstream guidance texts at pinned revisions (A-44–A-58). Excluded: executing any hook, plugin, upstream installer or native session; reading or writing home configuration; verifying PyPI publication.

## Existing capabilities and behaviour

**Where the daily friction comes from.**
- Every packaged phase skill is rendered person-started only: `disable-model-invocation` on Claude Code and Cursor, `allow_implicit_invocation: false` on Codex (A-19). The model cannot enter a phase by itself, and Next sections hand the person the following slash command (A-21).
- Inside a session each skill has the agent run its own sequence of `models resolve`, `standards for`, `gate status`, `evidence cite`/`hash` and a validator, and copy bound values into headers by hand (A-20, A-22).
- Human decisions sit at fixed STOPs: profile approval, AS-IS acceptance, design and plan pull requests, phase acceptance and the review decision (A-21).
- Terminal day-to-day commands are sync, doctor, explain, upgrade and rollback (A-33).

**Reusable infrastructure.**
- A root-confined file system, an off-repository journal with backups, lock-then-verify-then-write application and rollback (A-27, A-31).
- A hardened GitRunner and a shell-free, bounded ProcessRunner (A-12, A-29).
- Strict exit codes and a JSON envelope (A-14, A-30).
- Local read-only checks: gate status, doctor and the validators (A-32).
- Names-only listing of personal folders (A-13).
- Packaged skills with manifest hashes (A-3, A-4, A-11).
- Python 3.12+ (A-26).

**Limits of today's code.**
- The client set is closed at three, and a standard and an import contract name three adapters (A-24).
- No adapter writes a hook or settings file (A-25).
- init uses the current directory and refuses nested directories (A-28).
- No home-directory writer exists beyond the data directory (A-27).

**Documented native contracts** (current pages, not version-qualified; A-34–A-43):

| Surface | Hook sources | Session start / compaction | Failure, trust |
|---|---|---|---|
| Claude Code 2.1.303 | user, project, plugin, skill; all merge | `SessionStart` incl. `compact`; 10,000-char cap | timeout non-blocking unless `onFailure`; global disable only |
| Cursor | user, project, plugin; plus Claude settings hooks (third-party setting on by default) | `sessionStart` fire-and-forget; `preCompact` observe only | fail-open unless `failClosed`; `loop_limit` 5 |
| Codex CLI | user, trusted project, plugin; duplicates may run twice | `SessionStart` incl. `compact`; 2,500-token default | hash-keyed trust via `/hooks`; 600 s default |
| Codex VS Code extension | not documented | not documented | no plugins; skills via `$`/`/skills` |
| Copilot in VS Code | `~/.copilot/hooks`, `.github/hooks`, repo `.claude/settings.json`, plugins | `sessionStart` startup/resume/new; no compact source | timeouts fail open; `preToolUse` errors deny; 30 s |

Skills: Claude Code `~/.claude/skills`, where personal beats project (A-42); Codex `~/.agents/skills` (A-17, A-38); Copilot `~/.copilot/skills` (A-41); Cursor user skills (A-16). Cursor plugins can carry `alwaysApply` rules, skills and hooks, and load from `~/.cursor/plugins/local` when local imports are allowed (A-36).

**Guidance overlap** (Karpathy-inspired source A-56, against baseline A-44, standards A-45, Ponytail A-58, plan and review flow A-20, A-21):

| Principle | Already covered by | Points not stated in Orqlet or Ponytail | Overlap or conflict |
|---|---|---|---|
| Think before coding | baseline "do not guess, ask"; Ponytail scope list; Ponytail lite names the smaller option; Ponytail ultra pushes back on unjustified parts | present several interpretations instead of choosing silently | duplicate of the ask-when-unsure rule and of Ponytail's push-back, which applies at ultra only, not at the default full level |
| Simplicity first | baseline simplest design; Ponytail option order and levels | none beyond wording | C-6: "no error handling for impossible scenarios" carries no guard |
| Surgical changes | baseline conventions; Ponytail structure; plan file scope | mention unrelated dead code rather than delete it; remove only orphans the change created; every changed line traces to the request | Ponytail "deletion beats addition" has no own-change limit |
| Goal-driven execution | baseline test and evidence; TEST-001; plan acceptance criteria; Ponytail test rule | step-then-verify plan for multi-step work outside a phase plan | duplicate of plan checks |

The upstream has no licence file and no named holder (A-55); Q-27 limits reuse to Orqlet's own wording with an attribution link. Its delivery forms are an always-applied Cursor rule, a Claude plugin and an unpinned fetch of `main` (A-57).

**Ceremony today.** D1 is the lowest class and still requires a component view, a data-flow diagram, a sequence diagram and an ADR or exemption (A-46, A-47). The class never decides whether a phase happens (A-47), a D1 plan only follows the design more directly (A-48), and the person confirms that every change, including `fix-*` work, passes all four phases (A-49, Q-31). Each phase also repeats in-session CLI checks and header copying (A-20, A-22). The upstream treats trivial tasks by judgment (A-56, C-7).

**Delivery channels for guidance.** Orqlet renders AGENTS.md blocks, skills, roles and client rules, and no hook or settings file (A-25). The clients document session-start context injection (A-34, A-35, A-37, A-40), always-applied plugin rules in Cursor (A-36) and session-wide skills (A-58), with context caps of 10,000 characters in Claude Code and 2,500 tokens by default in Codex (A-34, A-37).

**Terminal capabilities.** Orqlet's human output is plain text without colour (A-50). Rich 15.0.0 is already installed through Typer (A-51). It handles non-terminal output, TERM, NO_COLOR, FORCE_COLOR, CI variables and width wrapping (A-53), and it substitutes ASCII only for boxes, not icons (A-54). CI runs on Linux, macOS and Windows (A-52). Gaps: there is no NO_COLOR handling, banner, icon set, status vocabulary or narrow layout in Orqlet, and none of these has been observed in a terminal (A-50, U-6, U-7).

## Inferences

- I-1 The repeated phase commands follow from the person-started rendering and the Next hand-offs, not from a client limit (A-19, A-21). A rendered skill with the field removed, observed in a client, would confirm it.
- I-2 One script registered in both `~/.claude/settings.json` and `~/.cursor/hooks.json` would run twice in Cursor. Hooks rendered into a project's `.claude/settings.json` would also run under Copilot in VS Code (A-35, A-39). A disposable session per client would confirm it.
- I-3 A global `orqlet` skill in `~/.claude/skills` would shadow a project skill of the same name in Claude Code (A-42). This bears on project pins (A-4).
- I-4 Copilot has no documented post-compaction context event, unlike Claude Code and Codex (A-34, A-37, A-40).
- I-6 With Q-27, only the points in the "not stated" column of the overlap table would add new wording. The other lines restate the baseline or Ponytail, including push-back, which Ponytail states at its ultra level but not at its default level (A-44, A-56, A-58).
- I-7 Rich's existing detection would cover NO_COLOR, redirection and CI without a new dependency, but icon fallbacks would need Orqlet's own ASCII labels (A-51, A-53, A-54).
- I-5 Blocking on hook failure depends on the client and the event (A-34–A-40):
  - Session-start hooks only add context and cannot block: context only in Claude Code, fire-and-forget in Cursor, `additionalContext` only in Copilot. The Codex page documents no blocking control for them.
  - Claude Code: a `PreToolUse` timeout lets the tool run unless the hook sets `onFailure: "block"`.
  - Cursor: `failClosed: true` turns a crash, timeout, non-zero exit or missing output into a block, and permission hooks block on an invalid response even without it.
  - Copilot: `preToolUse` errors fail closed, but timeouts always fail open.
  - Codex: a `PreToolUse` error, timeout or malformed response can let the tool run. The page documents no fail-closed option.
  - None of these documents a hook that records a person's design or plan approval. Approval remains in the code host (A-21).

## Open questions

- U-1 Codex VS Code extension hook support and trust (Q-20: deferred to qualification).
- U-2 Copilot and Codex extension availability in VS Code 1.145.0 on this machine (Q-24).
- U-3 Whether an always-applied Cursor plugin rule can replace the guided User Rules step (Q-9).
- U-4 Linked-worktree behaviour of init, upgrade and the journal (Q-24).
- U-5 Whether current-page contracts match the installed client versions (Q-24).
- U-6 Icon glyph display and ASCII fallback in PowerShell and legacy consoles (Q-29).
- U-7 The narrowest supported width and the narrow layout (Q-29).
- U-8 Whether Cursor 3.31.11 reads a repository CLAUDE.md or `.claude-plugin` (Q-24).
- U-9 The copyright holder of the upstream text; not material under Q-27.
- C-1–C-3 are documentation mismatches in the README, onboard and doctor. C-4 is the three-client standard against the four supported assistants. C-5 is the upstream's Cursor claim against Cursor's third-party default. C-6 is error handling under simplicity. C-7 is judgment for trivial tasks against the four-phase rule.

## Inputs for design

- Ledger Q-1–Q-31: all answered; Q-10 supersedes Q-5/Q-6, and Q-29 refines the terminal graphic of Q-5.
- Facts A-1–A-58, unknowns U-1–U-9 and contradictions C-1–C-7.
- Facts for the acceptance criteria of the guidance integration: one foundation, with no new mandatory command, workflow or third instruction set; simplicity keeps validation, error handling, accessibility and approvals; reuse only in Orqlet's own wording with attribution; any change to ceremony is a separate decision (Q-27, Q-28, Q-30).
- Facts for the acceptance criteria of the terminal output: the outcome states, environments, fallbacks, JSON and quiet-hook conditions of Q-29, and the Rich behaviour in A-53 and A-54. Terminal layouts for success, existing setup, manual action, recoverable failure and a narrow or plain variant belong to design, after acceptance.
- ADR-001's committed-files decision and its plugin conditions C1–C4, which were framed around MCP credentials (A-23).
- The native contract table and the infrastructure listed above.
