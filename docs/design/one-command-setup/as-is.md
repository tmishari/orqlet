---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: one-command-setup
  status: draft
  workflow_version: 0.4.0
  protected_set_digest: b5d119f17890b8d7602c906b3325af7db4ef3d74fb31b8d697cdeeebfbb4be2d
  bound:
    applicable_rules_hash: 56502a0ec5eda3b13b4c9d97c7d4dfa41df82c86a206e36dd5d2d92aab299b97
    base_revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    profile_version: 1
    standards_lock_hash: 89a225016ff9d8b3ed977df39a70dfbe9dbc5f7c6d3762d0f2208b1b7a037a52
base_revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
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
  request_ref: one-command-setup
research_mode: sequential
limitation: One agent inspected the areas sequentially; no independent researcher
  was delegated.
size_budget:
  max_words: 1000
facts:
- id: A-1
  kind: operation
  statement: The README installs Orqlet with uv from a checkout or a pinned Git revision
    and lists Python, uv and Git as prerequisites.
  evidence:
  - path: README.md
    lines: 69-93
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: ae51b54098a68c85912828d488472ed55fba6cc81e8a9ad1d456ddd4e9d83eba
- id: A-2
  kind: interface
  statement: The Typer application shows help with no arguments and registers init
    and upgrade; it has no setup or install subcommand.
  evidence:
  - path: src/orqlet/interface/cli/app.py
    lines: 30-60
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: 22bd88259194cc6899c81be4a268e9878e85891892d31b806331e202323763c4
- id: A-3
  kind: flow
  statement: The workflow loader reads skill.md files and Markdown references, accepting
    only one-line name and description front-matter fields for skills.
  evidence:
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 29-53
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: 894cca8b35c0d3338e6c1d544b350ef4830166afa8723de7fa4dd3e58310241c
  - path: src/orqlet/application/usecases/workflow_sources.py
    lines: 104-137
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: 226f4c3774d9a87505f236679a5afda0be17d1cc49e7e8254580c25e8711afef
- id: A-4
  kind: flow
  statement: The renderer writes Claude Code skills under .claude/skills and shared
    Cursor/Codex skills under .agents/skills, including references and protected ownership.
  evidence:
  - path: src/orqlet/adapters/render/skills.py
    lines: 20-87
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: d5f955869df693d759317f1f14fdd42867f2dc402de478e570b722cec2968aeb
- id: A-5
  kind: flow
  statement: Render requests combine packaged workflow skills with team resource skills,
    then apply optional model settings.
  evidence:
  - path: src/orqlet/application/usecases/render_request.py
    lines: 116-135
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: a3a5f2a869572ae4ad89aee322f7f78dc804bd08152664be2a2abed582508867
- id: A-6
  kind: test
  statement: The installation smoke tests install a built wheel into an isolated environment
    and cover version reporting, init, doctor, dry-run and packaged skills.
  evidence:
  - path: tests/e2e/test_install_smoke.py
    lines: 26-131
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: 453e7174a697ecdf0562318fc03e46cb5e7187e6a882a869053100f4114096d9
- id: A-7
  kind: operation
  statement: CI pins uv 0.7.19, tests three operating systems and Python 3.12 through
    3.15, and builds wheels without a publication job.
  evidence:
  - path: .github/workflows/ci.yml
    lines: 13-107
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: 84ee7b99711e3051e0387c53d402f6d720f2db1ef6846c6e72496b7b6c0e9f1e
- id: A-8
  kind: dependency
  statement: The inspected Graphify source declares graphifyy 0.9.112, Python below
    3.15, platform-specific skill dispatch, dependency installation instructions and
    separate optional model/media extras.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/graphify.md
    lines: 1-26
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: 5343040961e29dc9d56cb31734631e4ba3232bdae430aec8c8a6204471e78021
- id: A-9
  kind: dependency
  statement: The inspected Ponytail 5.3.3 source contains six skills; help describes
    executable plugin features beyond the Markdown skills, and the skills use front-matter
    forms outside the Orqlet loader format.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/ponytail.md
    lines: 1-29
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: fe351cea44b13c6e4ff57635604cfa6bb22751c56a1b4d7f21373f4cfe362768
- id: A-10
  kind: dependency
  statement: Current official uv documentation describes version-specific standalone
    installers, managed Python downloads, isolated tool environments and interpreter
    selection.
  evidence:
  - path: docs/design/one-command-setup/evidence/web/uv.md
    lines: 1-15
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: b8f8bbbedb91f3083699e802c0d3821a6973ef4d35dcd81538a80e3d1541d30b
- id: A-11
  kind: structure
  statement: The packaged workflow reads manifest-listed files, verifies their hashes,
    and exposes its release identity and history.
  evidence:
  - path: src/orqlet/adapters/workflow_package.py
    lines: 24-84
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: fdeaf788abcd242e85952bb8a6411515ba51c0208c947f618d807f08b1281aa4
- id: A-12
  kind: interface
  statement: The ProcessRunner port accepts an argument sequence, explicit environment,
    timeout and output limit.
  evidence:
  - path: src/orqlet/application/ports/process.py
    lines: 33-44
    revision: b470b9b3ea4b7129af38e5d71ee5d3d99e58250a
    sha256: 9402f85e1e1ef8fe8e5eda07d82591e7ec462ce6b90c3d105869e8df537e9a91
unknowns: []
contradictions: []
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
    applicable_standards:
    - ORQLET-NOMODEL-001
    - ORQLET-ARCH-001
    - ORQLET-SEC-001
    - ORQLET-SEC-002
    - ORQLET-SEC-003
    - ORQLET-TEST-001
    - ORQLET-QA-001
  checks:
  - what: Fact references resolve at the bound revision
    how: orqlet evidence cite, one command per fact, returned success
    result: pass
  - what: Research artifact and requirement ledger validate
    how: orqlet validate as-is and orqlet validate ledger returned PASS with no findings
      on 2026-11-19
    result: pass
  unverified:
  - No upstream installer or skill was executed.
  - No combined-installer tests or native-client qualification ran.
  - uv current documentation was inspected; exact bootstrap-version qualification
    remains design/implementation work.
  - Research acceptance and design/plan approval have not been given.
---

## Request

One command installs Orqlet, missing uv and a compatible Python, and the Graphify CLI. Every initialized/upgraded project receives Graphify plus all six Ponytail skills for the selected Orqlet clients. Git stays a prerequisite (questions.yaml Q-1 through Q-4).

## Scope

The inspection covered the CLI entry points, packaging, workflow skill loading/rendering, CI and install tests, plus pinned source snapshots of both upstream projects (A-1 through A-12). It did not execute their installers or run their skills.

## Existing capabilities and behaviour

- Installation and project initialization are separate today (A-1, A-2).
- Orqlet already distributes protected skills and their Markdown references to all three clients (A-3 through A-5, A-11).
- The wheel smoke tests cover the current installation path; CI covers Python 3.12–3.15 across macOS, Linux and Windows (A-6, A-7).
- Graphify excludes Python 3.15 and has separate platform skill instructions; its skills can install dependencies themselves (A-8).
- Ponytail's six skills and plugin runtime are distinct; the help skill describes runtime features outside the requested Markdown skills (A-9).
- uv documents the bootstrap building blocks and isolated tool environments (A-10). Orqlet has a bounded process port (A-12).

## Inferences

No additional inference is asserted. The cited code and upstream source observations are the evidence for design.

## Open questions

All four requirement questions are answered in questions.yaml. Installer behaviour on clean machines and native clients is unverified, as recorded in self_check; it is not a successful test result.

## Inputs for design

The confirmed answers Q-1–Q-4 and facts A-1–A-12. The inspected Graphify install dispatcher defaults by operating system (Claude/Windows), rather than detecting and installing all Orqlet clients (A-8).
