---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: mcp-or-plugins
  status: approved
  workflow_version: 0.3.1
  protected_set_digest: be7723282aec5a67e8161540bfba464562fb2a53d9bc3f8245ea22b812134eec
  bound:
    base_revision: a0957b1cb5c06b797991c7d94214efd76927658c
    standards_lock_hash: 89a225016ff9d8b3ed977df39a70dfbe9dbc5f7c6d3762d0f2208b1b7a037a52
    applicable_rules_hash: 56502a0ec5eda3b13b4c9d97c7d4dfa41df82c86a206e36dd5d2d92aab299b97
    profile_version: 1
base_revision: a0957b1cb5c06b797991c7d94214efd76927658c
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
  - docs/design/mcp-or-plugins/evidence/**
  request_ref: mcp-or-plugins
research_mode: parallel-subagents
size_budget:
  max_words: 4980
facts:
- id: A-1
  kind: structure
  statement: No client folder or lock entry in this repository contains .mcp.json, .cursor/mcp.json, .codex/config.toml,
    .claude/settings.json, a hooks file, a plugin manifest or a marketplace file (the output kinds present
    are instructions block, bridge, rules, commands, skills, agents, PR template, seeded .prompts, .orqlet
    data files).
  evidence:
  - path: .orqlet/generated.lock.yaml
    lines: 6-665
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 7f85839841015d0939c47f2a559f78c4adff111aa9feb1b25fe6e93cbece9545
- id: A-2
  kind: test
  statement: A test asserts the exact path set each adapter produces; no set contains .mcp.json, .cursor/mcp.json,
    .codex/config.toml, .claude/settings.json, a plugin manifest or a marketplace file.
  evidence:
  - path: tests/unit/render/test_clients_golden.py
    lines: 64-98
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: e76001436585b14d147a67bb0837b32fa32f0c843a81400533658dceaefdf325
- id: A-3
  kind: flow
  statement: compose() builds the files of init and upgrade from the adapters' render results, the PR-template
    blocks, the .prompts seed files and the .orqlet data files; there is no MCP, plugin or marketplace
    step.
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: 116-125
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 900b5307d51dd825e2d5cf3711081eed47e58855bc5b1bd03ebc9a79a6a07ed0
- id: A-4
  kind: interface
  statement: OwnerMode.SHARED_ENTRY ('shared-entry') is defined, and a lock entry with that owner must
    name its entry.
  evidence:
  - path: src/orqlet/domain/ownership.py
    lines: '9'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 4cf41e744c4267cb0188b0c80a0096cf794c5eb75bdfed7fdc2dec23e689e6c6
- id: A-5
  kind: interface
  statement: RenderedFile has an optional 'entry' field described as the entry name of a shared-entry
    file; no adapter in src sets it.
  evidence:
  - path: src/orqlet/application/ports/instruction_adapter.py
    lines: '26'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 8f759e6fde71402724f273121fa3a196d8a34affdcb2d112b05ccb1dca1ce66b
- id: A-6
  kind: interface
  statement: The CLI registers init, upgrade, rollback, sync, doctor, explain, release and the groups
    profile, standards, validate, gate, evidence, knowledge and review; there is no mcp, source, auth
    or plugin command.
  evidence:
  - path: src/orqlet/interface/cli/app.py
    lines: 34-47
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 822b147c030944d99e6f7c6059f01a5830430dfc601693cecc3875c0e76ae131
- id: A-7
  kind: interface
  statement: FORBIDDEN_KNOWLEDGE_FILES is {AGENTS.md, CLAUDE.md, .mcp.json}; with FORBIDDEN_KNOWLEDGE_PREFIXES
    (.claude/, .cursor/, .agents/, .codex/, .orqlet/, .github/, src/orqlet/workflow/) it decides which
    paths can never be knowledge.
  evidence:
  - path: src/orqlet/application/usecases/binding_inputs.py
    lines: 57-66
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 1f084a593c39e7c95e8110cf3d2e962c798afe3ada49c5fd1f893d67c6064fe3
- id: A-8
  kind: interface
  statement: The contract orqlet.integrations/v1 declares EnforcedBy as server, client-enforced-editable,
    client-managed or none.
  evidence:
  - path: src/orqlet/application/contracts/integrations.py
    lines: '11'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 0a7c4a2d105dc66891e6d52be03e5e1c0cf2f8ff8dd71ccac9e481c72f1df07a
- id: A-9
  kind: interface
  statement: PerClient has register, enforced_by, control, decision, pending and verification (not-tested
    or verified) and no scope, reuse, auth or limitation field.
  evidence:
  - path: src/orqlet/application/contracts/integrations.py
    lines: 27-33
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 1a6212c43af5f12eccb1f36f4f0bd827b8b6a5a81885dec16c428dc5958d6fa4
- id: A-10
  kind: interface
  statement: AuthSpec.mode is client-native-oauth, env-ref or none; env_refs is a tuple of free strings
    with no pattern.
  evidence:
  - path: src/orqlet/application/contracts/integrations.py
    lines: 41-43
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: bc5ccd4b3f05af96a8914dfb964ebc7ffb54ef141bbdb834658b89be419a1ef5
- id: A-11
  kind: interface
  statement: DataFlow requires backend_identity (free text), scope, data_classes, egress and owner_review.
  evidence:
  - path: src/orqlet/application/contracts/integrations.py
    lines: 46-51
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: f46ef1b675d22f3f97726a4e95a8ceb270f720928b29774e36d889eefc6069c8
- id: A-12
  kind: test
  statement: The valid fixture declares one server, 'docs' (remote URL https://docs.example.com/mcp, capability
    read, registration read-only, enforced_by server), with per_client claude-code register true and auth
    client-native-oauth.
  evidence:
  - path: tests/fixtures/contracts/valid/orqlet.integrations.v1.yaml
    lines: 1-16
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 33a4e5e909b614a16918a3366e3efffa3b3a56543262c1c519c066459735efd0
- id: A-13
  kind: structure
  statement: Outside the contract, its schema, its registry entry and this fixture, no module in src imports
    Integrations or reads an integrations.yaml.
  evidence:
  - path: src/orqlet/application/contracts/integrations.py
    lines: 79-84
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b5e9d4d88766c8a417a6d9c5765e037165343422283cdf5f6a7fe55ae1a0f416
- id: A-14
  kind: structure
  statement: The README says the MCP configuration, orqlet ci check, the hooks and the knowledge index
    are not built yet.
  evidence:
  - path: README.md
    lines: 34-35
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 330054fd5e1312a1c735844d84d985c36b5d9d6ad3cdf48b71755fb036531e9d
- id: A-15
  kind: structure
  statement: Section 22.0 says 'no client was opened, there is no commit, no remote and no CI run', and
    that ci check, the hooks, the edit guard, the host evidence and the MCP generators are not built.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4480'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 3cf80ef14babbd47c7ea60425ec63c8b277504092b4c30034fb63b6b63ba626d
- id: A-16
  kind: structure
  statement: Milestone M4 'MCP base and permission baselines' (MVP-2) is scoped to McpInventory, reconciliation,
    orqlet-* base entries (read-only, secret-free), tool-restriction lint, generators for the four integrations
    in the three clients, doctor MCP checks and the S-19 result.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4507'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 8ab3eb31aa00486740929469c083d269e7563eeefd7bf92784bdfab4194fce73
- id: A-17
  kind: structure
  statement: M5 to M7 are 'later' (1.0, each separately approved); M6 holds external sources with the
    authentication procedures and, if Q-06 selects it, the Miro REST read adapter; M7 holds plugin packaging.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4508'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: ba273f7d532c7323a2cb932c485d3f4615f280aeff901370e006701dce8a50dc
- id: A-18
  kind: interface
  statement: Project MCP configuration is .mcp.json (Claude Code), .codex/config.toml [mcp_servers.*]
    in trusted projects only (Codex) and .cursor/mcp.json (Cursor); user scope is ~/.claude.json, ~/.codex/config.toml
    and ~/.cursor/mcp.json.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '605'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b42089c0054c77fd1180c823f682ab0bd3ec1135346ec6c1f80eb3a61460536a
- id: A-19
  kind: interface
  statement: Personal MCP is local and user scope in ~/.claude.json (sensitive), ~/.codex/config.toml
    and ~/.cursor/mcp.json.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '718'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: d6d14cf38578f9d73c77c783a04b8560374236ed494ab98825c4a3b47e2c2a1f
- id: A-20
  kind: interface
  statement: In Claude Code a same-name MCP entry resolves local > project > user > plugin > connectors
    and the whole entry is replaced; Codex project configuration outranks user configuration; Cursor documents
    no same-name rule.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '719'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 65269730197fdc32f0722611dd6053614019e22f1147d5b1a31b12cd58ef7986
- id: A-21
  kind: interface
  statement: 'Trust gating: Claude Code project .mcp.json servers need approval; Codex skips project configuration
    in untrusted projects; Cursor Workspace Trust is off by default and every MCP connection needs approval.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '723'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 6ca3814975b0e0a1fb8dba20e5d242847f1182ceb92872cdeeccbd275dc6f52f
- id: A-22
  kind: interface
  statement: 'Comparison criterion ''always-on instructions'': committed files are the only channel in
    Claude Code and Codex; plugins carry no CLAUDE.md or AGENTS.md; Cursor plugins can carry rules.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '750'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 4607ac0a4847889e4f199a9f184455d7c83f1f2ad064ffe0d1b13f67078ce10f
- id: A-23
  kind: interface
  statement: 'Central versioned update without a pull request in each repository: not possible with committed
    files (each repository upgrades by pull request), possible with plugins.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '753'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: c4b0beb70c9041041bc620a960aabd4c3483f17581d6d72c07f17eb3bbde33c0
- id: A-24
  kind: interface
  statement: Protection against silent shadowing is the orqlet- prefix only for committed files; Claude
    namespacing avoids it and Cursor Required prevents uninstalling for plugins.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '754'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: f26f953633dc856e46b16b18fa9a292f5dda40fbe99b185a7daa8b6e595faa70
- id: A-25
  kind: interface
  statement: 'The Section 4.8 conclusion: commit the thin always-on files and the generated skills, roles
    and MCP entries; treat a native plugin as an additional adapter output for organisations that want
    central updates, with canonical definitions kept identical.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '757'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: d4ea2fde55c2f326dc5db6fe5efa45ff22d06e6733e1b63eaf5ae3f4427643fc
- id: A-26
  kind: interface
  statement: Alternatives row C, 'Native plugin marketplaces only (no generator)', has the verdict 'An
    additional adapter output later, not a replacement'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '790'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b2cf30ff741a51843b95752ec37079dafed39bee378a341633b1fb821d23126d
- id: A-27
  kind: interface
  statement: Plugin packaging is listed in the 1.0 release train.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '276'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: e6e0e501c73a85faad5c7d3bb73303918ac5ff3ba19672bd75cfe3293eefa2ac
- id: A-28
  kind: interface
  statement: 'Decision D-27 (Default): committed generated files first; native plugins and marketplaces
    later as an extra adapter output where plans allow.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5152'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: c6ce66a511ef0fbad67a629f54eb8d8d5cbd706e1fa94c0c5d08f3f4afc4b3d9
- id: A-29
  kind: interface
  statement: A project may exclude optional components, including plugin outputs and the base MCP entries,
    through optional_components.exclude.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3395'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 04ffba86bf32b391b0808b8e85cfb6f82f77180f024a7ea1a5d5a97686964a9e
- id: A-30
  kind: interface
  statement: The Day 0 table lists base MCP servers as .mcp.json entries named orqlet-* (Claude Code),
    .codex/config.toml [mcp_servers.orqlet-*] (Codex, trusted projects only) and .cursor/mcp.json entries
    named orqlet-* (Cursor).
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '319'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 3a9c433df01d15048f14e6043bc4fd0ca69a31b83af05df0f9a04f156f7e0503
- id: A-31
  kind: interface
  statement: Owned MCP entries in JSON are identified by the orqlet- prefix plus a per-entry hash in generated.lock.yaml
    with owner shared-entry; TOML is edited per entry; Orqlet emits files only for the clients enabled
    in the profile.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2279'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 7ae3736979512d6b38bd533a9e1de2efb30567daaf8abd671678e38322d4f096
- id: A-32
  kind: interface
  statement: integrations.yaml is committed, has no secrets and lists required servers by identity, purpose,
    capability tier, expected authentication mode (client-native OAuth, environment-variable reference,
    none) and a separate role-to-tool restriction.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2548'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: ed820f532f46459bb238d9958c6facf08bb937c362cfdaad8a5757b31a70956e
- id: A-33
  kind: interface
  statement: 'Base entries are orqlet- prefixed, read-only and secret-free; authentication is client-native
    OAuth or an environment-variable reference: ${env:NAME} in Cursor, ${VAR} in Claude Code, the client''s
    documented environment-variable field in Codex.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2550'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 54b6b3f4e57458dd8891de0801bfb9381b3fddd49088fea32049a39514bc8f4d
- id: A-34
  kind: interface
  statement: The baseline pins each server's URL or command and permitted variable names; ${...} is forbidden
    in command and args; CI validates every MCP entry in .mcp.json, .cursor/mcp.json and .codex/config.toml
    against it.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2552'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: d3861a8ef4b2c20fb83159e9c1f0cf9610dd11e814b78366ad81bd806e11880f
- id: A-35
  kind: flow
  statement: Reconciliation discovers managed, project, user and plugin sources statically; user-scope
    files can hold tokens, so user-scope inspection is opt-in through the client's own listing command
    with values redacted.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2570'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 25752be505625f28e77c31dd21c55f16c2572a2bb1bf25c93a4c6da946e11062
- id: A-36
  kind: interface
  statement: 'Enforcement options, strongest to weakest: server-side limits, administrator-managed configuration,
    client permission rules in project files (editable by the developer).'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2610-2612
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 16be073fbe60567d5c9368a3e71769cbfbd8b552c3bf421b741295d12db944fe
- id: A-37
  kind: interface
  statement: '''Credentials are never copied between clients; each client authenticates for itself.'''
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2665'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: ba9aa2e35770ac08fe13731ab605e0650c03d233a087252e8b90564f675815aa
- id: A-38
  kind: interface
  statement: Every entry declares a data_flow block whose backend_identity is 'which account, token or
    service identity' the backend sees.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2681'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: fd17c9bd0d02199f739a4d4f6ffcb9214a84349b1d52937d1edcec095c437146
- id: A-39
  kind: interface
  statement: 'Requirement status: GitHub, Jira and Confluence are ''Designed; not tested'' in all three
    clients; Miro is ''Not met through MCP; unverified'' in all three.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2691-2696
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: a6dcd3b82e51317a968621ca2806597965a0a66b327a70a901d239f784f2c8f3
- id: A-40
  kind: interface
  statement: 'GitHub in Cursor: project .cursor/mcp.json entry orqlet-github with /readonly appended;
    a personal access token through headers as ${env:NAME}; the limitation column says ''Per-developer
    PAT''.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2702'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 6f204a15ec13e409b7c9185c59efd0c036dfb4ba94f4bb59e36a1be03a3ce647
- id: A-41
  kind: interface
  statement: 'GitHub in Claude Code: project .mcp.json (type http, url, headers with ${VAR}); PAT header
    documented; OAuth with the GitHub remote not found.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2703'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: a19ec328f5e6ede9350ef2d97ee2a557d4d61e440f5618e74089f6cbfbfc1899
- id: A-42
  kind: interface
  statement: 'GitHub in Codex: .codex/config.toml [mcp_servers.orqlet-github] with url and bearer_token_env_var
    (trusted projects only); the bearer token goes through an environment-variable name.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2704'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 152fe402ef8c347e0eb3c81e239d082929cc0a4b5ec73e2576655b90f6ea4248
- id: A-43
  kind: interface
  statement: Confluence rows in Cursor, Claude Code and Codex are 'As Jira' (same server, registration
    and authentication).
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 2708-2710
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 6f0e329520b9e8c0acc4f1a8e60aa83cfbe6839c6f87e89e37b0f187b558eb5a
- id: A-44
  kind: interface
  statement: 'Rule 3: a registration never copies a credential from another client, never assumes installation
    means authentication and never assumes another client''s session is available.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2737'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: e1923382a15cc83f80c13ced55ae0d3939008b18f411e2ed0db7e4996db5c3db
- id: A-45
  kind: interface
  statement: Developer identity is 'the person's own login (SSO) in a client or tool', used for interactive
    IDE work and for Orqlet's approved reads and writes.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2747'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 30039f8d8401d0e26c5497d4353a89c0c7a8a977b4965f46ef156f6327f3af29
- id: A-46
  kind: interface
  statement: CI identity is a service identity in the CI executor, 'never inferred from a developer's
    IDE login; interface pending'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2748'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 510481b7cec4bcd39e1b24bf4cf5b336469e300405baf8f882a3a92a587701e9
- id: A-47
  kind: interface
  statement: '''Credentials stay out of Git, prompts, Markdown and indexes. Orqlet stores references only.'''
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2753'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: cf3473e3bd8bedc93fe8a8171562045b44ff54ea0e478fe80475ce4dc39e670f
- id: A-48
  kind: interface
  statement: Whether administrators allow a non-interactive developer credential is unknown [U]; 'service
    accounts belong to the CI identity class and are not used for local developer writes'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2830'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: ecfce741e8fbf140e8feb314c191751d6e0e8413071b9df406786e2eac45f5c1
- id: A-49
  kind: interface
  statement: The agent-configuration surface includes the MCP entries .mcp.json, .cursor/mcp.json and
    .codex/config.toml.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3829'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 5966c6f34838144d552af615b827a9f541260cb8a8353ef8aae134a56bd69a02
- id: A-50
  kind: interface
  statement: 'Every MCP entry in all three files is validated against the baseline integrations.yaml:
    the whole canonical entry, unknown fields rejected, variable names pinned.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3840'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: a77529cd1505487a54b428b4b79f89ec28819f720d4aac8d19d19a6841937ea9
- id: A-51
  kind: test
  statement: Acceptance fixture FM-X06 expects credentials referenced by environment-variable name only,
    a scan of every generated file finding no token, and no session inherited between clients.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4399'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 64aa8ff31ff66e5832d9162e0b6f5cbcc535d37cc0f4c89bba48cb17e70d54db
- id: A-52
  kind: interface
  statement: 'Rule ORQLET-SEC-003 (MUST): never commit secrets, tokens or credentials, including in tests
    and fixtures; use obvious placeholders.'
  evidence:
  - path: .prompts/rules.yaml
    lines: 59-64
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 8b860aba906bb2adb5c845fc52dee5d0da989e9ce922d379b6b016fcef3f51cd
- id: A-53
  kind: interface
  statement: Orqlet 'never' reads client credential stores or stores secrets in Git, prompts, Markdown,
    indexes or logs.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '409'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 73af6148634736c8f50c6551824773ea3aba45aaae636882c9c5fbb68b8a6486
- id: A-54
  kind: structure
  statement: Claude Code page says MCP servers can be configured at three scopes (Local, Project, User);
    the scope controls which projects the server loads in and whether the configuration is shared with
    the team; 'Administrators can also deploy or provide servers for every user via managed configuration'.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '8'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 6deefc7af8eedbe0ac39db94667fc9d1c6ff44b9f5a7a53f6f62a35d144cb0cf
- id: A-55
  kind: structure
  statement: 'Claude Code scope table, Project row: loads in ''Current project only'', shared with team
    ''Yes, via version control'', stored in ''.mcp.json in project root''.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: 10-13
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: f8b4ab57930bc1c8ab3cbbf9e6a7cb09ddf9de1a6b2ac7475875fe0e763ddc03
- id: A-56
  kind: structure
  statement: 'Claude Code scope table, Local row: loads in ''Current project only'', shared with team
    ''No'', stored in `~/.claude.json`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: 10-12
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: c736594db5b266f6bdb9689fa189cbc87328d52b75967fdfda1995cd94d7a83b
- id: A-57
  kind: structure
  statement: 'Claude Code scope table, User row: loads in ''All your projects'', shared with team ''No'',
    stored in `~/.claude.json`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: 10-14
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b0b16ac2646010bc6c8ef8ab9a183c9eba92c51aba4e86009aa97a722471b17d
- id: A-58
  kind: operation
  statement: 'Claude Code page instructs: ''Check `.mcp.json` into version control so everyone on your
    team gets the same MCP tools and services.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '28'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 7c5fb337f193a0c45ca259905b3b4e3c2fddfc7347519cd27c4398db6befee62
- id: A-59
  kind: structure
  statement: Local scope is the default; a local-scoped server loads only in the project where you added
    it and 'stays private to you'; Claude Code stores it in `~/.claude.json` under that project's path,
    so the same server won't appear in other projects.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '21'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 3faaa9cebd559e91873f185080434e7a62362304ad30059c2fd4276da72e5bad
- id: A-60
  kind: operation
  statement: Claude Code page advises local scope for 'personal development servers, experimental configurations,
    or servers with credentials you don't want in version control'.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '21'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 3faaa9cebd559e91873f185080434e7a62362304ad30059c2fd4276da72e5bad
- id: A-61
  kind: interface
  statement: Claude Code supports environment variable expansion in `.mcp.json` files, 'allowing teams
    to share configurations while maintaining flexibility for machine-specific paths and sensitive values
    like API keys'.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '61'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 2fe0d64c7991677c350135528a029ddab73b53adf8d3695220484f8c77113bed
- id: A-62
  kind: interface
  statement: 'Claude Code expansion syntax: `${VAR}` expands to the value of environment variable `VAR`;
    `${VAR:-default}` expands to `VAR` if set, otherwise uses `default`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: 63-66
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: e95e39d17c4dccd054688b36cf77e585dc516b03c557613a85f58a14b95bcdac
- id: A-63
  kind: interface
  statement: Claude Code supports OAuth 2.0 for remote MCP servers and marks a remote server as needing
    authentication when the server responds with `401 Unauthorized` or `403 Forbidden`.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '75'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: e7aabfd5ceffe96592f152fb61a15db233e5726e22c8931511fc9669c56de5a3
- id: A-64
  kind: interface
  statement: 'A `headersHelper` supplied by a repository or plugin is described as ''a command you didn''t
    write''; Claude Code runs it without the credential variables from the user''s environment (example
    given: `ANTHROPIC_API_KEY`).'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '78'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 6c90eab28d9ef147c1ff89d0d24f0946c8354b5f32e647dbd985016bddb895d2
- id: A-65
  kind: interface
  statement: 'Credential variables are removed for a `headersHelper` of: a server in a project `.mcp.json`
    or in a plugin, and an inline server in an agent file from the project or from an `--add-dir` directory.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '80'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 5f2f627fe75c5cff5d66bc1ded0f43299ff9c040b42c1e1abad749587fef5d1c
- id: A-66
  kind: interface
  statement: 'Credential variables are not removed for a `headersHelper` of: a server at user or local
    scope, in managed MCP, from a claude.ai connector, or supplied by the SDK or `--mcp-config`, and an
    inline server in an agent file from `~/.claude/agents/`, from managed settings, or passed with `--agents`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '81'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 71687b015b6031b90b76e5007926dda7db2278d4bee3f928dd65b2519873c276
- id: A-67
  kind: structure
  statement: 'Managed MCP configuration is described as for ''organizations that need centralized control
    over which MCP servers users can connect to'': it covers deploying a fixed server set with `managed-mcp.json`,
    providing servers to every user with `managedMcpServers`, restricting servers with `allowedMcpServers`
    and `deniedMcpServers`, and what users see when a server is blocked.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '86'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 755b9b082a6ef63daa84e92983a15ff5557aabc52a80d4d7f67fdaf14ff62a3e
- id: A-68
  kind: flow
  statement: 'Same server name in more than one scope with different endpoints: Claude Code warns about
    the conflict in `claude mcp list` output and in `/mcp`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '56'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 638eb99c15516ea15f63ba29f4e65eef1163101e8d7b675006e8158f28cedf03
- id: A-69
  kind: flow
  statement: '''Claude Code stores OAuth sign-ins per endpoint'', so after authenticating the definition
    that loads in one project, the user ''still need[s] to sign in separately in a project where a different
    definition loads''.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '56'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 638eb99c15516ea15f63ba29f4e65eef1163101e8d7b675006e8158f28cedf03
- id: A-70
  kind: interface
  statement: The same-name warning quotes each scope's endpoint as written in the configuration, with
    `${VAR}` references unexpanded, 'so it never shows a resolved value such as an API key'.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '56'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 638eb99c15516ea15f63ba29f4e65eef1163101e8d7b675006e8158f28cedf03
- id: A-71
  kind: structure
  statement: Plugins can bundle MCP servers; a plugin defines them in `.mcp.json` at the plugin root or
    inline in `plugin.json`.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: 48-50
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 0570f52d8862f9fc4131b9ae13e498c74726156d0928d1a7cb7002f44b919137
- id: A-72
  kind: flow
  statement: When a plugin is enabled, Claude Code starts its MCP servers automatically and offers plugin
    MCP tools alongside manually configured MCP tools.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: 51-52
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 4b3ad4bfc0adb01ca49dbf91e0cc23e80b3ebdcec725412ff20df1741dd75496
- id: A-73
  kind: operation
  statement: Plugin MCP servers are added and removed by installing or uninstalling the plugin, 'not with
    `/mcp` commands'; an installed plugin server can be toggled off in `/mcp`, which stops the connection
    without removing the plugin.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-mcp.md
    lines: '53'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 93312489e34beeda72c85bc9b35372c2794ef6b00ce515a0c22658dae0b69c4a
- id: A-74
  kind: structure
  statement: 'Claude Code authentication page, ''Credential management'' (introduced as ''your authentication
    credentials''; MCP servers are not named in the excerpt): on macOS credentials are stored in the encrypted
    macOS Keychain; when the Keychain rejects the write (for example locked in an SSH session) Claude
    Code stores the login in `~/.claude/.credentials.json` with file mode `0600`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-authentication.md
    lines: 8-12
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 2d85d59d8df7e5c36c93f7a05beb7ad68676e1c040f6cfb722f8163364deefab
- id: A-75
  kind: structure
  statement: 'Claude Code plugin guidance: ''To include instructions in a plugin, write them as a skill.''
    Claude Code ''doesn''t load a `CLAUDE.md` at the plugin root''; `claude plugin validate` warns ''CLAUDE.md
    at the plugin root is not loaded as project context''.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-components.md
    lines: '6'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b052de724f4086769d0a938cf9fae01bc437887ac245e37c19a88ae6493097f1
- id: A-76
  kind: structure
  statement: A plugin declares an MCP server in `.mcp.json` at the plugin root 'in the same shape as a
    project `.mcp.json`'.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-components.md
    lines: '9'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 24d0631810c9715beb7c4c33dda70b3722a3b5dcdccd8e10ba090e59d98749f1
- id: A-77
  kind: interface
  statement: '`userConfig` ''declares values Claude Code prompts the user for when the plugin is enabled,
    so users don''t edit `settings.json` themselves''.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-manifest.md
    lines: '11'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 04227f1dadf5571ebd0f7c91252f827fe7885326a313033246a47c91cca5317d
- id: A-78
  kind: interface
  statement: '`sensitive` is optional; ''If `true`, masks input and stores the value in secure storage
    instead of `settings.json`''. The components page says to set `"sensitive": true` for a token or password.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-manifest.md
    lines: '19'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: fc0d44aec062c71c9f6193a7542152f4b8cd21b6db9cf5ef96a2f6e2f5e2e0da
- id: A-79
  kind: structure
  statement: Non-sensitive `userConfig` values are saved under `pluginConfigs` in 'the user's `settings.json`';
    'Sensitive values go to the platform's secure credential store instead'.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-manifest.md
    lines: '24'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 013960b13a1e6310fd7d6f03426caf20e2a5236a33407ffa637ec3af2b247c2d
- id: A-80
  kind: interface
  statement: '`${user_config.KEY}` is ''substituted in MCP server config, LSP server config, exec-form
    hook `args`, and skill and agent content''; in skill and agent content only non-sensitive values are
    substituted and a sensitive value there becomes a placeholder.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-manifest.md
    lines: '30'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 0b8dde8b67c3b946aa112388be3f0f86059a1d4dee06d0d3c1b6caaa5ff938b5
- id: A-81
  kind: flow
  statement: The `userConfig` dialog is part of the interactive `/plugin` interface and opens for any
    option that isn't set yet when the user installs the plugin in `/plugin`, runs `/plugin install` inside
    a session, or enables the plugin from the Installed tab in `/plugin`.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-components.md
    lines: 21-25
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 070a84cfedbf68e2bf4ee579ab90ee5a90addef6f1bba6b1de9a86c0737fc8c3
- id: A-82
  kind: flow
  statement: 'USER REPORT (GitHub issue 62442, not vendor documentation): when a plugin declares `userConfig`
    with `sensitive: true` and the user enters the value via `/plugin` -> Installed -> Configure options
    -> Save, the value is ''silently not persisted anywhere''; it works for the current session only (in-memory
    env substitution into the MCP server spawn succeeds), then is lost on restart; ''The user must re-enter
    the API key on every cold start.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-issue-reports.md
    lines: 7-9
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 960d10bcab94dcc713b8e5b21d4fb06708d4b2a3e5fea9f129a72366256e853b
- id: A-83
  kind: flow
  statement: 'USER REPORT (GitHub issue 89969, not vendor documentation): a plugin bundling a remote HTTP
    MCP server can make its endpoint per-installation configurable with `userConfig` + `${user_config.KEY}`
    (including `default` values), but the same placeholder inside the server''s `oauth` block is ''not
    substituted'': the OAuth authorize request is sent with the literal placeholder as `client_id`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-issue-reports.md
    lines: '12'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: fc255b6bb58f7937ec2b233ca87cadfc07a52947c7d46472dfdc1655ec3ffa2e
- id: A-84
  kind: operation
  statement: To cover one repository's contributors, set `extraKnownMarketplaces` and `enabledPlugins`
    in that repository's `.claude/settings.json`.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-distribution.md
    lines: '9'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 9d7131c2c3ada15afd14f51a5c26605f10355474395e53ad6605763a52e7449d
- id: A-85
  kind: flow
  statement: '`extraKnownMarketplaces` entries ''apply only in a folder the contributor has trusted'';
    in an untrusted folder Claude Code ignores them ''without a message''; in interactive sessions Claude
    Code registers the marketplace only after the contributor accepts the workspace trust dialog for that
    folder.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-distribution.md
    lines: 9-11
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: ad8c4fc8b2f600c2bf1980c51211b1696ab94575fd9e435ec7386ce9739a4470
- id: A-86
  kind: flow
  statement: A plugin the marketplace lists by a relative path loads from the marketplace copy once the
    repository's `extraKnownMarketplaces` entries apply.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-distribution.md
    lines: '14'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 06bd8e73af0867963145f6c86c0e1025700ad1232b60026fc7b1a67ae90ef046
- id: A-87
  kind: flow
  statement: 'A plugin whose marketplace entry points at an external source (example: the plugin''s own
    GitHub repository) ''doesn''t install from the repository''s settings alone''; each contributor sees
    a message that the plugin ''is enabled in project settings but isn''t installed'' until they run `claude
    plugin install @ --scope project` (names blank in the file).'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-distribution.md
    lines: '14'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 06bd8e73af0867963145f6c86c0e1025700ad1232b60026fc7b1a67ae90ef046
- id: A-88
  kind: structure
  statement: 'Managed settings are named as a distribution route: ''For plugins your organization distributes
    through managed settings, see Manage plugins for your organization.'' The excerpts do not contain
    the managed-settings procedure. Line 9 contrasts one repository''s contributors with ''your whole
    fleet''.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-distribution.md
    lines: '9'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 9d7131c2c3ada15afd14f51a5c26605f10355474395e53ad6605763a52e7449d
- id: A-89
  kind: structure
  statement: 'Surface without plugin support: a cloud session (including the browser at claude.ai/code)
    ''has no plugin browser and doesn''t load the plugins you installed on your own machine or the ones
    your repository''s `.claude/settings.json` turns on''.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-distribution.md
    lines: '26'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 33f4fe4f0468d6e1693700782dcb795c4502efe6233c419a79f2d8567e422bb5
- id: A-90
  kind: interface
  statement: 'Codex `auth` (optional): ''Authentication to try after configured bearer tokens and authorization
    headers''; `oauth` (the default) is for stored MCP OAuth credentials; `chatgpt` uses the current ChatGPT
    session for the trusted first-party ChatGPT origin, with stored OAuth as a fallback.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-mcp.md
    lines: 9-12
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 199b5674aaaecede592a2269f22957202e24b6411d8e09edf4b3b6fef84aea37
- id: A-91
  kind: interface
  statement: 'Codex `bearer_token_env_var` (optional): environment variable name for a bearer token to
    send in `Authorization`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-mcp.md
    lines: '13'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 775e8c07ea6db2458df901aea48b91cadf93247843b7ef783d34ef98644c274c
- id: A-92
  kind: interface
  statement: 'Codex `http_headers` (optional): map of header names to static values; `env_http_headers`
    (optional): map of header names to environment variable names (values pulled from the environment).'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-mcp.md
    lines: 14-15
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: a425e5b29719ca8195dc621f7f1585c578a23b3f67877cfb547d4ed95f0d158e
- id: A-93
  kind: interface
  statement: 'Codex `http_headers_helper` (optional): a local command that prints a JSON object of header
    names and string values; ''Supported for HTTP MCP connections made from the local environment; not
    for stdio servers or connections made through a remote execution environment.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-mcp.md
    lines: 16-19
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 2b1e7d41afff8299c17b43bc968de012ae3dc72427f10e41676c5905b31c512f
- id: A-94
  kind: flow
  statement: '''If no credential source resolves, Codex can connect to the server without authentication.''
    The MCP OAuth login is started separately with `codex mcp login` (server name blank in the file).'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-mcp.md
    lines: 28-30
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 48d19ebb60abc7c7757db53e2d6cae984b4455b4d646e9334472b5bf99972843
- id: A-95
  kind: operation
  statement: For a confidential client also pass `--oauth-client-secret`, and 'Read the secret from an
    environment variable' (example uses `"$MCP_CLIENT_SECRET"`).
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-mcp.md
    lines: 43-49
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 8703363657ab8c12eed82b160b1a480591a97c78da291892d134716d58c5bea1
- id: A-96
  kind: interface
  statement: 'Codex source: `bearer_token_env_var` comment says requests include the token via `Authorization:
    Bearer`, and ''The actual secret value must be provided via the environment.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-source.md
    lines: 21-25
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 4da91c7e6f8ec63882786c487ea3ba5a8dec479c7652de882c4b5fb1aeaec18b
- id: A-97
  kind: interface
  statement: 'Codex source: `http_headers_helper` is a ''Local-only shell command that prints a JSON object
    of dynamic HTTP headers''; ''The command may be visible to local process inspection; do not embed
    credentials.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-source.md
    lines: 32-35
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b893c3922e11fcbf495080683064ae17fbd72e35f78dc32bef2c67c14f8c56a9
- id: A-98
  kind: structure
  statement: 'Codex config option for the ''Preferred backend for storing MCP OAuth credentials'': `keyring`
    (OS-specific keyring service), `file` (a file in the Codex home directory), `auto` (default: OS keyring
    if available, otherwise a file).'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-source.md
    lines: 39-43
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: c4471f500beeb095c9a3b492e02335bdbed8c739ab35a9e11ff17646852628f8
- id: A-99
  kind: structure
  statement: 'Codex overview: a plugin can contain Skills (''reusable instructions for specific kinds
    of work''), Apps (''connections to tools like GitHub, Slack, or Google Drive''), and MCP servers (''services
    that give Codex access to more tools or shared information'').'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-overview.md
    lines: 7-11
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: cb7409bd7a8daa590d41e4accf2e22d065a1c5e1d38dfe204451eae916e1b265
- id: A-100
  kind: structure
  statement: 'Codex plugin package: a portable plugin has a `plugin.json` manifest at its root and can
    also include a `skills/` directory, an `mcp.json` file for bundled MCP servers, and assets; OpenAI-specific
    settings go in the root manifest''s `extensions.com.openai` object; a `.codex-plugin/plugin.json`
    is optional and serves as a compatibility fallback when that object is absent.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-package.md
    lines: 13-17
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: a6fcb0cca611cce4bdafcd492821c5e3ef1fe7ed2ecfb57a0b903cd21c90993b
- id: A-101
  kind: structure
  statement: 'Codex plugin package: ''UI and authentication remain part of the MCP server integration
    you built in the preceding steps; the plugin manifest connects that integration to the rest of the
    package.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-package.md
    lines: 6-8
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 10405d082def01c8ce43a429c499d5d4d4b007857a6120f57c4b6db3016d8748
- id: A-102
  kind: flow
  statement: 'Codex overview: bundled skills are available as soon as the plugin is installed; if a plugin
    includes apps, Codex ''may prompt you to install or sign in to those apps in ChatGPT during setup
    or the first time you use them''; if it includes MCP servers, ''they may require extra setup or authentication
    before you can use them''.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-overview.md
    lines: 16-18
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 17596ed1e5601e3aaefd7c66dc6941d3e364cdc46abe62a3d03eb8e10b5b9d2c
- id: A-103
  kind: structure
  statement: The repo marketplace at `.agents/plugins/marketplace.json` 'makes plugins discoverable';
    the repo's `.codex/config.toml` controls whether a local-marketplace plugin is enabled for that project,
    with a table keyed `plugin-name@marketplace-name` and `enabled = true`.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-package.md
    lines: 29-41
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: de9c4ec8aeb21752f7bef400083856a9dc7e6d1c6b2a6660503015ef1863f397
- id: A-104
  kind: flow
  statement: '''Codex loads project `.codex/config.toml` only for trusted projects. Project settings override
    user, cloud-managed, and system defaults, subject to enforced requirements.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-package.md
    lines: 46-48
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 30e569062deb1064d714b6c0125853b936a75543ef13decf833a1852eb01bffc
- id: A-105
  kind: flow
  statement: '''You can install any plugin exposed through a marketplace''; ChatGPT installs plugins into
    `~/.codex/plugins/cache/$MARKETPLACE_NAME/$PLUGIN_NAME/$VERSION/` (`$VERSION` is `local` for local
    plugins) and loads the installed copy from that cache path rather than directly from the marketplace
    entry.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-package.md
    lines: 65-69
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 8a2edf43bb37f372fc8e385c4415ab4a169dde331d7ded17f3f68cb0a0974ca2
- id: A-106
  kind: structure
  statement: Each local-marketplace plugin can be enabled or disabled individually; 'The plugin browser
    saves user-level choices in `~/.codex/config.toml`; repo, cloud-managed, and system configuration
    can also supply plugin settings.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-package.md
    lines: 71-73
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: d8e9f0c38b9727c036d6f74d0ad8f1b25446ad1775816acf65ceaa2ec27dca09
- id: A-107
  kind: structure
  statement: 'Surface without plugin support: ''Plugins aren''t available in the IDE extension. To browse
    and install plugins for Codex, use the ChatGPT desktop app or Codex CLI.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/codex-plugins-overview.md
    lines: '21'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 534e5beaee390e0c1bfca4bbe41c4dbe0682e9bdfacafb84b5eb0e9f842438d1
- id: A-108
  kind: structure
  statement: 'Cursor `mcp.json` locations: project-specific `.cursor/mcp.json` in the project folder (''shared
    with your team''; ''Commit this to git so teammates get the same tools'') and global `~/.cursor/mcp.json`
    (''personal, all projects'').'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp-help.md
    lines: 6-9
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 87a0941e28002ea81a797e5ee29a3c5eeb3e92b5b0436aac84a2e0c4440931d2
- id: A-109
  kind: flow
  statement: 'Cursor: ''Both files are merged. If the same server name appears in both, the project-level
    config takes priority.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp-help.md
    lines: '11'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: bea4256a7b126bb40f6d24b762b774039cf98f205c5cbd87337dbf16b18a8a24
- id: A-110
  kind: interface
  statement: 'Cursor resolves variables in `mcp.json` values in these fields: `command`, `args`, `env`,
    `url`, and `headers`; syntax: `${env:NAME}`, `${userHome}`, `${workspaceFolder}` (project root, the
    folder that contains `.cursor/mcp.json`).'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp.md
    lines: 8-14
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 1c81fcd19b5c7b97d46b7328445fbce5f91580ee4b019f964382a75e2f5aa39e
- id: A-111
  kind: interface
  statement: 'Cursor: ''MCP servers use environment variables for authentication. Pass API keys and tokens
    through the config.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp.md
    lines: '19'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 41961970ad58fbb26891d58e4e35c6747520f11f17b56f6fd51fd939b69b4d27
- id: A-112
  kind: interface
  statement: Cursor supports OAuth for servers that require it; sign-in uses the authorization code flow
    with PKCE.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp.md
    lines: '21'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 4ef2944166a27982062647aa3a749af916d9f584bd1b212e87ad4363e657007a
- id: A-113
  kind: interface
  statement: 'Cursor allows static OAuth client credentials in `mcp.json` instead of dynamic client registration,
    for use when the provider gives a fixed Client ID (and optionally Client Secret), requires whitelisting
    a redirect URL (examples: Figma, Linear), or does not support OAuth 2.0 Dynamic Client Registration.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp.md
    lines: 24-28
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 85ac913bed0a1cea3033b01f249d8d0dc11d8e4e4de9a77fa6db636d765be082
- id: A-114
  kind: structure
  statement: 'Cursor: ''A Team MCP server''s config and a team plugin''s variables are shared by the whole
    team''; editing them from any surface, including an automation''s MCP settings, changes the value
    for every teammate and automation that uses them.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp.md
    lines: '35'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 9410b0eff9d329b28c713bcc8cdf23591eb8d20eea69db945c7b7bf8802c62de
- id: A-115
  kind: structure
  statement: 'Cursor: ''Only team admins can edit a Team MCP server or replace credentials a team plugin
    already has. Org admins have the same access on every team linked to their Organization, even without
    a team admin role.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp.md
    lines: '35'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 9410b0eff9d329b28c713bcc8cdf23591eb8d20eea69db945c7b7bf8802c62de
- id: A-116
  kind: structure
  statement: 'Cursor MCP Allowlist: Enterprise admins control which MCP servers users may run from Team
    Settings > MCP Configuration; ''Allowlisting approves an MCP configuration. It does not distribute
    or install the server.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-mcp.md
    lines: '40'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: d150ba862243afa79a2fd0495f71171813fccc72fbb079a1beed92f8c5b3c0b1
- id: A-117
  kind: structure
  statement: 'Cursor loads plugins in two formats: Agent Plugins (open standard; manifest `plugin.json`
    at the plugin root; components: Skills, MCP servers) and Cursor Plugins (manifest `.cursor-plugin/plugin.json`;
    components: Skills, MCP servers, rules, agents, commands, hooks, variables).'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-plugins-reference.md
    lines: 8-13
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 1c827645816e54623ce98ed990f5681377a50dfdf8fcb63c99b0ec7b289160d7
- id: A-118
  kind: interface
  statement: 'Cursor plugin `variables` declare ''the names (and types/descriptions) of user-specified
    configuration'' (example: an API token for an HTTP MCP server); ''The plugin only defines the schema;
    it does not include the secret values themselves.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-plugins-reference.md
    lines: '18'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 8d978e7c41d0e78ad9170360c1df77ee6d950fdd331d685456ca89237f923a23
- id: A-119
  kind: operation
  statement: 'Cursor: ''Team admins set the actual values in the dashboard under Plugins (at install time,
    or later via Configure on the plugin).'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-plugins-reference.md
    lines: '20'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 19ee063bb08adf0a4d32db4d449a02fcca847d735064917ecfac079bc0de3588
- id: A-120
  kind: interface
  statement: 'Cursor: ''Do not put secret values in the plugin repo. In `mcp.json` and other plugin config,
    include only `${VAR}` placeholders that match property names in the schema.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-plugins-reference.md
    lines: '22'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 7631010c76a2d6cf658c32c190134d45adc3e89b09edede9e17b730d3f6c1077
- id: A-121
  kind: flow
  statement: 'Cursor: ''Adding a Team MCP server to the Default marketplace does not install or enable
    it for every developer. Admins still control marketplace access and plugin installation modes. Each
    developer may also need to authenticate with the MCP provider.'''
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/cursor-plugins.md
    lines: '24'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 14b8d3d37366c8ad72e49b7395894c3591125bf024d5dcc466f49c696978beed
- id: A-122
  kind: interface
  statement: For the Remote GitHub MCP Server the text says "the recommended way to obtain a valid access
    token is to ensure your client application supports OAuth 2.1".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/github-mcp-server.md
    lines: '10'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: c2240cde8208dcfdbc27d0abed88a219797da67794e9ee7986a8eadaf000db77
- id: A-123
  kind: interface
  statement: For the Remote GitHub MCP Server the text says "you may also supply any valid access token.
    For example, you may supply a pre-generated Personal Access Token (PAT)". It does not list other token
    types.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/github-mcp-server.md
    lines: '10'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: c2240cde8208dcfdbc27d0abed88a219797da67794e9ee7986a8eadaf000db77
- id: A-124
  kind: interface
  statement: The text says "The Remote GitHub MCP Server itself does not provide Authentication services"
    and that "Your client application must obtain valid GitHub access tokens through one of the supported
    methods".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/github-mcp-server.md
    lines: 12-14
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 3a856a311806305ab3575aa611aef28d899450ff9f2dbc23b70fed8743476e6b
- id: A-125
  kind: operation
  statement: The text says "Environment variable support varies by host app and IDE. Some applications
    (like Windsurf) require hardcoded tokens in config files."
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/github-mcp-server.md
    lines: '22'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 73f624f0ba0b20b29bffd34dd7bd3d9775ab94522cd8ff544e5deae58e5a00ae
- id: A-126
  kind: interface
  statement: The text says the Atlassian Rovo MCP Server "uses OAuth 2.1 as its primary authentication
    mechanism", authorizing access "via an interactive consent flow".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '8'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 079855b01ed76bee7abe87be17861476750edc61db2e26f797d5b8769cf6eda1
- id: A-127
  kind: dependency
  statement: The text says "if enabled by your organization admin" the server supports API-token authentication
    "for machine-to-machine and other non-interactive scenarios", with the examples "backend services,
    CI/CD pipelines, bots, and automated agents", and that it lets MCP clients authenticate "without a
    browser-based OAuth consent screen".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '10'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 76756f4a0da08905ef5f32a9c0385f5d7a0c7b214193b348e0f2078a729fc215
- id: A-128
  kind: interface
  statement: The text says "Regardless of the method, every action respects the authenticated user's existing
    access controls and permissions", that "Access is granted only to data the user already has permission
    to view", and that OAuth and API token authentication "both honor configured scopes and Atlassian
    permissions".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '12'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: efe536b2cdb0ff0e7017365bd25395823adf2e3270273572c525c8bdb7c9a3f1
- id: A-129
  kind: interface
  statement: 'The methods table lists "API token" as "Non-interactive machine-to-machine authentication
    using a personal API token or a service account API key. Requires admin enablement." with the headers
    `Authorization: Basic <base64(email:api_token)>` or `Authorization: Bearer <api_key>`.'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '18'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 32e4e50713dc75db95363c0ed079635f0c1d0cbf67504fcf5a1ea22cc9651b12
- id: A-130
  kind: dependency
  statement: The API-token guide says "An admin creates a service account and generates an API key with
    the appropriate scopes. Store the key securely in your CI/CD system or secrets manager." It does not
    say who creates a personal API token.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '23'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 943120b85634dc2ef17debb4e16c17cf887791edbe8bece8bb68c9fb7856f054
- id: A-131
  kind: interface
  statement: The support page says "By default, users connect AI tools to Atlassian MCP using OAuth 2.1."
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '26'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: a199275cb588f1f19a991b9738ae0b8dce07a7ae5b9091a58e1490f2f4787dc0
- id: A-132
  kind: interface
  statement: The support page lists as a use of API-token connection "Backend systems or automations that
    call Atlassian MCP on behalf of a shared account".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '28'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b602de854ae429e98a7abace0bb8c058a0b9ec4cadd713dd37ddda626f02b1ae
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '31'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 7695baf28173d3a83ed3b6b98bc08f7d9b845d43fbdcea6bc2cb67fa57c4a488
- id: A-133
  kind: interface
  statement: The support page says tools that authenticate via API token "do not use domain allowlists
    and are instead governed by your IP allowlist configuration and the scopes granted to their tokens
    or API keys".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md
    lines: '33'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: df3a1ab5b20458817d48f44948e982b1b196562e21c5f3114a176f57d8dfb00b
- id: A-134
  kind: interface
  statement: Under "Set up your agent" the text names a Codex and ChatGPT route ("Add Miro from the ChatGPT
    plugin directory, then select Connect"), a Claude Code route (`claude plugin install miro@claude-plugins-official`)
    and a Cursor route ("Install from the Cursor marketplace").
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: 8-11
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 5eecdfb1e01c4c2cffbceb9be20d40ac4ee57e292f06e3f7448fdb1d09042ab3
- id: A-135
  kind: interface
  statement: The security excerpt says Miro MCP "Uses OAuth 2.1 for auth" with "dynamic client registration"
    and "Respects all existing board permissions and access controls".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: 14-15
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: bbb76d80d3e57f95f7a67a217a0ba29a25e3e4b73112fd7973e3e9aa88568485
- id: A-136
  kind: interface
  statement: The FAQ says "Today the Miro MCP connection is 1:1 — each user is authenticated into one
    team at a time, even across multiple clients. If you authorize a different team (or a different client),
    the previous team's connection is superseded."
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: '18'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: bd531272253c9add2395f0c023a840150a5a5cdc12e76b45c5862c4a5e509eb5
- id: A-137
  kind: interface
  statement: The troubleshooting page says there are multiple ways to install the Miro MCP Server, that
    "each creates an independent connection with its own OAuth session", and that if more than one is
    active in the same client "you'll see duplicate tools and authentication confusion".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: '21'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 6630d604d55d0f40d8ca533552e99d40ed52c2d71b20aff8165829366ef7e8f4
- id: A-138
  kind: interface
  statement: A table row reads "Plugin / extension (from miro-ai) | Everyone using Claude Code, Cursor,
    Gemini CLI, or Kiro | User (follows you across projects)". The excerpt carries no column headings.
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: '23'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 33b72f85cc0abbb7024a105f48d59b89b8727e85e742384e7de0a5350c7ee7e0
- id: A-139
  kind: interface
  statement: 'A table row reads "Manual JSON config (`"url": "https://mcp.miro.com/"`) | Clients without
    a Miro plugin (VSCode + Copilot, Windsurf, Lovable, etc.) | User or project".'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: '24'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: fdad208f756fa8e2d475b7229d42234c9f0818505be44754d96bb7dc2e22bc0c
- id: A-140
  kind: operation
  statement: 'The text says "The rule: use only one method per client. If your client has a Miro plugin
    or extension, use that — and do not also add manual MCP config. They both connect to the same server
    but maintain separate auth sessions."'
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: '26'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b280c01cb8c2250453a4ea7a8f1d6d14b526873858469dfacd151f6e731e4637
- id: A-141
  kind: dependency
  statement: The admin guide says "Enable MCP for your organization, then use Access control to decide
    who can use it", and that access can be kept "open to everyone, or limit[ed] to selected teams and
    optionally user groups", with "Board-level permissions still apply".
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: 29-30
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: c1d8396851bf4b7aeb4b8e7e6ce305db4752a1690f88b5bd6757ddbfd879f18e
- id: A-142
  kind: interface
  statement: The admin guide says "All access is authenticated through OAuth 2.1" and "Users can only
    grant access to boards they have permission to view."
  evidence:
  - path: docs/design/mcp-or-plugins/evidence/web/miro-mcp.md
    lines: 31-32
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 78b45ee68bfeccb878d62f77ca623c5fb6440d663612f79eb83541e7ee1e7042
- id: A-143
  kind: interface
  statement: The GitHub/Cursor row plans a project `.cursor/mcp.json` entry with authentication by "A
    personal access token through `headers`, as `${env:NAME}`". It cites GitHub's own Cursor install guide
    (reported by a v0.4 review-round subagent, not re-read by the author) as saying "the GitHub server
    currently requires a Personal Access Token". It lists "Per-developer PAT" under limitations.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2702'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 6f204a15ec13e409b7c9185c59efd0c036dfb4ba94f4bb59e36a1be03a3ce647
- id: A-144
  kind: interface
  statement: The GitHub/Claude Code row plans a project `.mcp.json` entry with authentication by "PAT
    header (documented); OAuth with GitHub remote not found".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2703'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: a19ec328f5e6ede9350ef2d97ee2a557d4d61e440f5618e74089f6cbfbfc1899
- id: A-145
  kind: interface
  statement: The GitHub/Codex row plans a `.codex/config.toml` entry (trusted projects only) with authentication
    by "A bearer token through an environment-variable **name** (no secret in the file)" using `bearer_token_env_var`.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2704'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 152fe402ef8c347e0eb3c81e239d082929cc0a4b5ec73e2576655b90f6ea4248
- id: A-146
  kind: interface
  statement: The Jira/Cursor row says OAuth 2.1 is the default and is "interactive; each client authenticates
    for itself; the consent screen decides the scopes", that Cursor `auth.scopes` and Claude Code `oauth.scopes`
    can pin what a client requests, and that "Cursor's credential storage and sharing are not stated".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2705'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b303a5f730ce2ec4e3735363af0e24f71685b63f54e9f7e66400c7ed6c084aae
- id: A-147
  kind: dependency
  statement: The Jira/Cursor row says an "API token (Basic, or a service-account Bearer token)" applies
    "only if an organisation administrator enables it".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2705'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b303a5f730ce2ec4e3735363af0e24f71685b63f54e9f7e66400c7ed6c084aae
- id: A-148
  kind: interface
  statement: The Jira/Cursor row says the administrator's Permissions tab (Read, Write, Search groups)
    "takes effect immediately, organisation-wide", that token scopes are per group (`read:jira:agent-interface`),
    and that "a read-scoped service-account token is a server-enforced read-only identity".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2705'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b303a5f730ce2ec4e3735363af0e24f71685b63f54e9f7e66400c7ed6c084aae
- id: A-149
  kind: interface
  statement: 'The Jira/Cursor row lists two registration routes: Marketplace "Add to Cursor", or a project
    `mcp.json` `url` entry. It says one server, `https://mcp.atlassian.com/v2/mcp`, serves Jira and Confluence,
    with "per-client registration".'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2705'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: b303a5f730ce2ec4e3735363af0e24f71685b63f54e9f7e66400c7ed6c084aae
- id: A-150
  kind: interface
  statement: The Miro/Cursor row says the Cursor plugin is user scope, a manual `url` entry "can be user
    or project", and "only one method per client" should be used because the two keep separate authentication
    sessions. The entry is "Not registered by default".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2711'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 9bd2fa88f2cc5fd3cdd6b46c2ecb60fe7ff841536e995f025d10668890886f51
- id: A-151
  kind: interface
  statement: 'The Miro/Cursor row gives the authentication as "OAuth 2.1 with dynamic client registration;
    the project `auth` block needs a `CLIENT_ID` and Miro documents none; no headless flow found", and
    says "One connection per user across all clients: authorising another client or team drops the previous
    connection (Miro''s "Last One Wins" rule)".'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2711'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 9bd2fa88f2cc5fd3cdd6b46c2ecb60fe7ff841536e995f025d10668890886f51
- id: A-152
  kind: interface
  statement: Appendix record GH-11 says GitHub's own Cursor install guide says "the GitHub server currently
    requires a Personal Access Token", and that GitHub Docs' "OAuth by default" "names other IDEs, not
    Cursor".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5944'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: 46aba3b3775f42e69f8871aa65ea2a8181e8f57ccedbf927df0141184c26431d
- id: A-153
  kind: dependency
  statement: Section 16.4.2 says "Whether administrators allow a non-interactive developer credential
    (they may allow only OAuth or service accounts) is unknown [U]; service accounts belong to the CI
    identity class and are not used for local developer writes."
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2830'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: ecfce741e8fbf140e8feb314c191751d6e0e8413071b9df406786e2eac45f5c1
- id: A-154
  kind: dependency
  statement: A pending-input list names, for Jira and Confluence, "whether the organisation enables API-token
    authentication and read-scoped service accounts".
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5118'
    revision: a0957b1cb5c06b797991c7d94214efd76927658c
    sha256: d8d92fdd16f5c98e61019d90c55398c0c6cb2b0ff05fa25243425f55df3aab9e
unknowns:
- what: How each developer obtains and supplies the per-developer token behind ${env:NAME}, ${VAR} or
    bearer_token_env_var. The authentication procedures and commands are pending input (A-156), and no
    code reads or writes them (A-52, A-56).
  material: true
  question_ref: Q-10
  merged_from:
  - repo-distribution-mcp-credentials/U-6
  id: U-1
- what: Whether Cursor uses a personal access token or OAuth for GitHub's server. Line 2702 relies on
    GitHub's own Cursor guide (not re-read by the author), while lines 171, 4399 and 6042 treat it as
    not found, documented differently, or unread.
  material: true
  question_ref: Q-10
  merged_from:
  - repo-distribution-mcp-credentials/U-7
  id: U-2
- what: Whether the proposal's Q-06 sub-answer (acceptance of a client-enforced, editable control for
    Miro in Claude Code and Codex) and the Miro plan the team has are answered; both are listed as open
    inputs (lines 5083, 5093).
  material: true
  question_ref: Q-10
  merged_from:
  - repo-distribution-mcp-credentials/U-10
  id: U-3
- what: Whether the vendor ships a plugin or connector for the GitHub MCP server in Claude Code, Codex
    or Cursor. The GitHub evidence file is silent. The design mentions "the marketplace plugin" for Cursor
    only in B-71, with the note "was not read" (design 6042).
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-1
  id: U-4
- what: Whether the vendor ships a plugin or connector for the Atlassian server in Claude Code, Codex
    or Cursor. The Atlassian evidence file is silent. The design cites a getting-started page for a Codex
    Desktop "Plugins or Connectors" entry (2635, 5947) and a Cursor Marketplace route (2705), neither
    of which is in the evidence file.
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-2
  id: U-5
- what: What the vendor says about running an Atlassian connector or marketplace entry together with a
    manual MCP entry (duplicate tools, separate sessions), and the same for GitHub. Neither evidence file
    says. Only the Miro text has such a rule (miro-mcp.md:21-26).
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-3
  id: U-6
- what: Whose token the "any valid access token" of the GitHub text may be (github-mcp-server.md:10).
    The excerpt names only a PAT as an example and does not say whether other token types (an app, a bot
    or shared account token) are accepted or who may create them.
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-4
  id: U-7
- what: Which party must enable or allow a GitHub PAT or an OAuth grant (user, organisation owner or administrator).
    The GitHub evidence file does not say.
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-5
  id: U-8
- what: Which of Claude Code, Codex and Cursor support OAuth 2.1 with the Remote GitHub MCP Server. The
    vendor excerpt says OAuth is recommended "if your client application supports" it and names no client.
    The design records "OAuth with GitHub remote not found" for Claude Code (2703) and that Cursor's PAT-versus-OAuth
    status is documented differently (4399).
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-6
  id: U-9
- what: Whether an Atlassian OAuth grant belongs to a client or to a user. The design says "each client
    authenticates for itself" (2705). The Atlassian evidence file says only that users authorize access
    through an interactive consent flow (atlassian-rovo-mcp.md:8).
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-11
  id: U-10
- what: What the Atlassian "domain allowlists" govern and which party sets them. The text says only that
    API-token tools "do not use domain allowlists" and are governed by an IP allowlist and token scopes
    (atlassian-rovo-mcp.md:33).
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-12
  id: U-11
- what: Whether Atlassian limits a user to one site or one product connection at a time (a limit like
    Miro's "one team at a time"), and the same question for GitHub. Neither evidence file says.
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-13
  id: U-12
- what: How Codex is classified by the Miro troubleshooting table. Codex is not named among the plugin
    clients (miro-mcp.md:23) or among the manual-config clients (miro-mcp.md:24), and the setup text names
    only the ChatGPT plugin directory (miro-mcp.md:9).
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-16
  id: U-13
- what: Whether, in the Miro "one team at a time" rule, two active connections made by two methods in
    the same client (plugin plus manual entry) count as "a different client". The text says each method
    has its own OAuth session (miro-mcp.md:21,26) and that authorizing a different team or client supersedes
    the previous connection (miro-mcp.md:18).
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-17
  id: U-14
- what: How a Miro user's team is chosen (by the user at consent time or by an administrator). The text
    says only that each user is authenticated into one team at a time (miro-mcp.md:18).
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-18
  id: U-15
- what: The plan requirement for the Miro MCP server and the administrator approval that Enterprise needs.
    These are in the design only (2636, 2719) and not in the Miro evidence file.
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-19
  id: U-16
- what: Whether one PAT held in one environment variable and referenced from the GitHub entries of all
    three clients (2702-2704; github-mcp-server.md:17-20) is meant by the rule "each client authenticates
    for itself" (2665). The design does not say whether the three clients use the same variable.
  material: true
  question_ref: Q-10
  merged_from:
  - integrations-auth/U-22
  id: U-17
- what: Who writes and owns the plugin and the marketplace entry, who can change the bundled server's
    address or the plugin's configuration schema for every user, and how updates reach installed copies
    (Claude Code; Codex cache copy under `~/.codex/plugins/cache`).
  material: true
  question_ref: Q-11
  merged_from:
  - credential-flow-trace/U-15
  - credential-flow-trace/U-30
  id: U-18
- what: Who may change the committed MCP file of each client (`.mcp.json`, `.codex/config.toml`, `.cursor/mcp.json`)
    and what review applies; the vendor files say only 'via version control', the design names the repository
    pull request and a CI check.
  material: true
  question_ref: Q-11
  merged_from:
  - credential-flow-trace/U-8
  - credential-flow-trace/U-27
  - credential-flow-trace/U-41
  id: U-19
- what: 'How a per-user credential value would reach an MCP entry that a plugin carries: the design describes
    only environment-variable references in committed MCP files, and a search found none of `userConfig`,
    `user_config`, `pluginConfigs` or plugin `variables` in the architecture document.'
  material: true
  question_ref: Q-11
  merged_from:
  - repo-distribution-mcp-credentials/U-3
  - credential-flow-trace/U-49
  id: U-20
- what: What files a native-plugin output of Orqlet would contain. The proposal names .claude-plugin/marketplace.json
    once (line 743) and 'plugin manifest validation' once (line 4047), names no other manifest file, and
    has no occurrence of user_config or userConfig.
  material: true
  question_ref: Q-11
  merged_from:
  - repo-distribution-mcp-credentials/U-2
  id: U-21
- what: How the CI agent-configuration surface audit (default-deny surface.yaml and integrations.yaml
    validation) would cover plugin or marketplace files. Section 19.8.5 lists enabledPlugins (A-159) but
    no .claude-plugin/ path and no plugin manifest among the surface items.
  material: true
  question_ref: Q-11
  merged_from:
  - repo-distribution-mcp-credentials/U-4
  id: U-22
- what: 'Cursor: whether Team MCP servers are available in local Cursor sessions as well as Cloud Agents,
    and which credential a Cloud Agent uses for a Team MCP server.'
  material: true
  question_ref: Q-7
  merged_from:
  - web-clients-plugins-mcp/U-40
  - credential-flow-trace/U-48
  id: U-23
- what: 'Claude Code: how managed-settings plugin distribution works (keys, whether members must still
    install or approve). The excerpt only points to ''Manage plugins for your organization'' (distribution:26).'
  material: true
  question_ref: Q-7
  merged_from:
  - web-clients-plugins-mcp/U-13
  id: U-24
- what: 'Claude Code: whether a cloud session loads plugins distributed through managed settings. The
    page defers to another page (distribution:26).'
  material: true
  question_ref: Q-7
  merged_from:
  - web-clients-plugins-mcp/U-14
  id: U-25
- what: 'Claude Code: the install scopes and which applies when the same plugin is set at more than one;
    deferred to ''Choose an install scope'' (distribution:17).'
  material: true
  question_ref: Q-7
  merged_from:
  - web-clients-plugins-mcp/U-15
  id: U-26
- what: 'Claude Code: surfaces other than the cloud session (IDE extensions, desktop app, SDK) that lack
    plugin support; the evidence is silent (distribution:26).'
  material: true
  question_ref: Q-7
  merged_from:
  - web-clients-plugins-mcp/U-18
  id: U-27
- what: 'Codex: how cloud-managed or system configuration distributes plugin settings (admin dashboard,
    managed settings); the excerpts say only that such configuration ''can also supply plugin settings''
    (package:72-73) and refer to ''Configure plugin marketplaces and defaults'' (package:74-75), which
    is not quoted.'
  material: true
  question_ref: Q-7
  merged_from:
  - web-clients-plugins-mcp/U-28
  id: U-28
- what: 'Cursor: what the ''plugin installation modes'' are, and what each team member must do under each
    (install, enable, authenticate); the term appears once (cursor-plugins:24).'
  material: true
  question_ref: Q-7
  merged_from:
  - web-clients-plugins-mcp/U-39
  id: U-29
- what: 'Cursor: surfaces that do not support plugins; none is stated in the excerpts.'
  material: true
  question_ref: Q-7
  merged_from:
  - web-clients-plugins-mcp/U-41
  id: U-30
- what: 'Codex route 2: whether a plugin that declares MCP servers is available in the Codex CLI. codex-plugins-overview.md:21
    says plugins can be browsed and installed with the ChatGPT desktop app or Codex CLI; the proposal
    says workspace-imported plugins that declare MCP servers are ''marked desktop-only'' (745) from a
    source not among the files read.'
  material: true
  question_ref: Q-7
  merged_from:
  - credential-flow-trace/U-31
  id: U-31
- what: 'Claude Code: where OAuth tokens from signing in to an MCP server are stored, and whether the
    stores named for Claude Code''s own login (macOS Keychain, `~/.claude/.credentials.json`) also hold
    them; what Claude Code shows when a remote server needs authentication (the list in the text is cut).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-1
  - credential-flow-trace/U-4
  id: U-32
- what: 'Claude Code: which fields of `.mcp.json` accept `${VAR}` expansion. The list under ''Expansion
    locations'' ends after ''Environment variables can be expanded in:'' (mcp:70).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-2
  - credential-flow-trace/U-2
  id: U-33
- what: Whose environment supplies the variable that a committed MCP file refers to (Claude Code `${VAR}`,
    Codex `bearer_token_env_var` and `env_http_headers`, Cursor `${env:NAME}`), how a user sets it, where
    that value is stored, who can read it, and what happens when it is unset. The vendor text gives the
    syntax and names no owner of the environment.
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-3
  - credential-flow-trace/U-3
  - credential-flow-trace/U-22
  - credential-flow-trace/U-38
  - web-clients-plugins-mcp/U-35
  id: U-34
- what: 'Claude Code: which definition wins when the same server name exists at several scopes. The text
    states a warning, per-endpoint OAuth sign-in and removal with `claude mcp remove --scope`, not a precedence
    order (mcp:56). Also not stated: whether same name with identical endpoints counts as a conflict.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-4
  - credential-flow-trace/U-6
  - credential-flow-trace/U-7
  id: U-35
- what: 'What happens when a plugin-provided MCP server has the same name as a server in a project, user,
    local, managed or team entry: the evidence states it for none of Claude Code (only same-name replacement
    inside one plugin is stated), Codex and Cursor.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-5
  - credential-flow-trace/U-16
  - credential-flow-trace/U-32
  - credential-flow-trace/U-47
  id: U-36
- what: 'Claude Code: whether each team member must approve or trust a project-scope `.mcp.json` server
    before it loads. The excerpts say only that the file is checked into version control so everyone gets
    the same MCP tools (mcp:28).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-6
  - credential-flow-trace/U-1
  id: U-37
- what: 'Claude Code: which settings files `pluginConfigs` is read from; the manifest page says ''The
    settings page lists which settings files'' (manifest:24) but the list is not in the excerpt.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-10
  - credential-flow-trace/U-11
  id: U-38
- what: 'Claude Code: how OAuth for a plugin-bundled remote MCP server is configured (an `oauth` block
    appears only in user report 89969), whether that sign-in is per user, and whether and where it is
    stored, keyed per endpoint as for configured servers.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-11
  - credential-flow-trace/U-17
  id: U-39
- what: 'Claude Code: whether the defects reported in user issues 62442 and 89969 still exist in current
    versions, and which versions were affected; the excerpts give no version or status.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-19
  - credential-flow-trace/U-18
  id: U-40
- what: 'Codex: where the shared MCP server configuration lives (user-level or project-level `config.toml`),
    whether a project `.codex/config.toml` can hold `mcp_servers` entries, and whether it is shared through
    version control. The MCP excerpts show fields only; `.codex/config.toml` is named for plugin settings.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-21
  - credential-flow-trace/U-19
  id: U-41
- what: 'Codex: whether `codex mcp add` writes to user-level or project-level configuration, and where
    a client secret passed with `--oauth-client-secret` is persisted (mcp:43-49; source:16-18).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-22
  - credential-flow-trace/U-23
  id: U-42
- what: 'Codex: how a user''s credential reaches a plugin-bundled MCP server, whether it is set per user
    or per workspace, and which fields the plugin''s `mcp.json` accepts (`bearer_token_env_var`, `http_headers`,
    `env_http_headers`, `http_headers_helper`, `auth`). The text says such servers ''may require extra
    setup or authentication'' and that authentication stays part of the MCP server integration.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-23
  - web-clients-plugins-mcp/U-24
  - credential-flow-trace/U-28
  id: U-43
- what: 'Codex: what each team member still has to do when a repo''s `.codex/config.toml` enables a plugin:
    whether the plugin is installed on each machine automatically. The text says Codex ''can install or
    refresh files for configured plugins'' during marketplace refresh (package:42-43) and that any marketplace
    plugin can be installed (package:65).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-26
  - credential-flow-trace/U-34
  id: U-44
- what: 'Codex: which same-named MCP server definition wins across configuration layers. The only precedence
    statement is for project settings generally (package:46-48), and it is not tied to MCP server names.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-29
  - credential-flow-trace/U-21
  id: U-45
- what: 'Codex: where the JSON fallback of the OAuth keystore is written and under what conditions; the
    `oauth.rs` comment is cut off at ''fall back to the json'' (source:59-60).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-32
  - credential-flow-trace/U-24
  id: U-46
- what: 'Cursor: where OAuth tokens from MCP sign-in and `${env:NAME}` values are stored and who can read
    them; the design says ''Cursor''s credential storage and sharing are not stated''.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-33
  - credential-flow-trace/U-37
  - integrations-auth/U-23
  id: U-47
- what: 'Cursor: whether `${env:NAME}` and other variables resolve in the static OAuth client fields of
    `mcp.json`; the resolving fields listed are `command`, `args`, `env`, `url`, `headers` (cursor-mcp:8),
    and the static OAuth field names are not in the excerpt (cursor-mcp:24-28).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-34
  - credential-flow-trace/U-39
  id: U-48
- what: 'Cursor: whether the dashboard variable mechanism applies to the Agent Plugins format; the format
    table lists `variables` only for Cursor Plugins (reference:13).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-38
  - credential-flow-trace/U-45
  id: U-49
- what: 'Cursor: which definition wins when the same server name exists in a Team MCP server, a plugin
    and a project or global `mcp.json`, and whether the project-level config replaces the whole entry
    or merges fields; only project-over-global precedence is stated.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-42
  - credential-flow-trace/U-40
  id: U-50
- what: 'Cursor: whether an approval or trust prompt precedes the connection to a server in a committed
    `.cursor/mcp.json`, and what it says; the text says teammates ''get the same tools''.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-43
  - credential-flow-trace/U-36
  id: U-51
- what: 'Whether an approval or trust step precedes the first connection of an MCP server that a plugin
    bundles: Claude Code starts plugin servers ''automatically''; Codex says ''existing approval settings
    still apply''; the Cursor text is silent, and it is not stated whether the enterprise allowlist applies
    to plugin-provided servers.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-13
  - credential-flow-trace/U-33
  - credential-flow-trace/U-46
  id: U-52
- what: Which TOML library, if any, would edit .codex/config.toml entries. The proposal says the TOML
    round-trip library is not researched (line 807); the implementation as-is repeats it as U-10 (A-64);
    no TOML writer beyond the flat toml_table is declared (A-28, A-29).
  material: true
  question_ref: Q-8
  merged_from:
  - repo-distribution-mcp-credentials/U-9
  id: U-53
- what: 'Claude Code: whether `${VAR}` environment expansion applies in a plugin''s `.mcp.json`. The text
    says only ''in the same shape as a project `.mcp.json`'' (components:9).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-8
  id: U-54
- what: 'Claude Code: the full list of what a plugin can contain; the excerpts mention skills, hooks,
    MCP servers, LSP servers and agents only in passing (manifest:30; components:6, 9).'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-12
  id: U-55
- what: 'Claude Code: whether the repository''s `.claude/settings.json` is itself shared through version
    control. The text says ''that repository''s `.claude/settings.json`'' (distribution:9) without saying
    it is committed.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-16
  id: U-56
- what: 'Codex: whether a plugin can or cannot contain an instructions file such as `AGENTS.md`; the excerpts
    list skills, apps, MCP servers, assets and hooks only (overview:7-11; package:13-22) and give no exclusion.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-25
  id: U-57
- what: 'Codex: whether `.codex/config.toml` and `.agents/plugins/marketplace.json` are shared through
    version control; the text says ''repo marketplace'' and ''repo''s `.codex/config.toml`'' (package:29-31,
    61) without naming version control.'
  material: true
  question_ref: Q-8
  merged_from:
  - web-clients-plugins-mcp/U-27
  id: U-58
- what: 'Claude Code: the file mode and readability of `~/.claude.json`, which holds local and user scope
    entries (claude-code-mcp.md:14,21). The Claude files give a mode only for `.credentials.json` (0600,
    authentication.md:12-13). The proposal calls `~/.claude.json` ''sensitive'' (lines 718, 2570) without
    a mode.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-5
  id: U-59
- what: 'Claude Code route 1: whether a changed `url` or `headers` in a pulled `.mcp.json` triggers a
    new prompt on a teammate''s machine. No Claude file says.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-9
  id: U-60
- what: 'Claude Code route 2: which secure credential store holds sensitive `userConfig` values, under
    which name or path, and who can read it. The files say ''secure storage'' (components.md:16) and ''the
    platform''s secure credential store'' (manifest.md:24) and name no location.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-10
  id: U-61
- what: 'Claude Code route 2: whether a sensitive `userConfig` option is also exported to hook processes
    as `CLAUDE_PLUGIN_OPTION_<KEY>`; manifest.md:31 says ''for every option'' and does not separate sensitive
    from non-sensitive options, while manifest.md:30 does for skill and agent content.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-12
  id: U-62
- what: 'Claude Code route 2: whether the `userConfig` dialog has other triggers than the three listed
    (claude-code-plugin-components.md:21-25, list may be cut) and what happens in a non-interactive session
    when an option is not set.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-14
  id: U-63
- what: 'Codex route 1: how a project becomes ''trusted'', whether a prompt is shown, and what Codex does
    at connection time beyond skipping an untrusted project''s file.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-20
  id: U-64
- what: 'Codex routes 1 and 2: how stored MCP OAuth credentials are keyed (by server name, by URL or by
    project), and so whether two entries with the same name at different scopes share them.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-25
  id: U-65
- what: 'Codex route 1: whether `http_headers_helper` configured in a project file runs under any restriction
    comparable to Claude Code''s credential-variable removal (claude-code-mcp.md:78-83); the Codex files
    only warn that the command ''may be visible to local process inspection'' (codex-source.md:33).'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-26
  id: U-66
- what: 'Codex route 2: whether OAuth credentials of a plugin-bundled MCP server use the storage backend
    described in codex-source.md:39-60.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-29
  id: U-67
- what: 'Cursor route 2: where the dashboard stores the values of plugin variables and Team MCP server
    configuration, and who can read them. cursor-mcp.md:35 states who can edit or replace them (team admins;
    org admins) and not who can read them.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-42
  id: U-68
- what: 'Cursor route 2: what ''authenticate with the MCP provider'' (cursor-plugins.md:24) consists of
    for each developer, and where that credential is stored.'
  material: true
  question_ref: Q-8
  merged_from:
  - credential-flow-trace/U-44
  id: U-69
- what: 'Cursor: whether a Team MCP server credential or a team plugin variable can hold a different value
    per developer or is one value for the whole team. The text says team admins set the values and that
    they are ''shared by the whole team'', calls the variables ''user-specified configuration'', says
    ''Each developer may also need to authenticate with the MCP provider'', and is silent on whose credential
    the developer uses and on whether a developer who is not an administrator can supply a value.'
  material: true
  question_ref: Q-9
  merged_from:
  - web-clients-plugins-mcp/U-36
  - web-clients-plugins-mcp/U-37
  - credential-flow-trace/U-43
  id: U-70
- what: Whether a shared service-account token may serve Jira and Confluence reads in IDE sessions. Line
    2705 describes a read-scoped service-account token as a server-enforced read-only identity and line
    5118 asks whether read-scoped service accounts are enabled; line 2830 limits service accounts to the
    CI identity class for local developer writes; line 4943 lists kind service-account with identity_class
    developer or ci.
  material: true
  question_ref: Q-9
  merged_from:
  - repo-distribution-mcp-credentials/U-5
  id: U-71
- what: 'Claude Code: how credentials for managed MCP servers (`managed-mcp.json`, `managedMcpServers`)
    are supplied, by the user or by an administrator, and where `managed-mcp.json` lives. The excerpt
    only names the mechanisms (mcp:86).'
  material: true
  question_ref: Q-9
  merged_from:
  - web-clients-plugins-mcp/U-7
  id: U-72
- what: 'Claude Code: whether an administrator can supply or pre-set a plugin''s `userConfig` values (for
    example via managed settings). The excerpts describe a prompt to ''the user'' (manifest:11; components:21-25)
    and are silent on administrator-supplied values.'
  material: true
  question_ref: Q-9
  merged_from:
  - web-clients-plugins-mcp/U-9
  id: U-73
- what: Whether an administrator can enable personal API tokens without enabling service account keys,
    or the reverse. The vendor lists both under one method that "Requires admin enablement" (atlassian-rovo-mcp.md:18,21).
    The design assumes administrators "may allow only OAuth or service accounts" (2830).
  material: true
  question_ref: Q-9
  merged_from:
  - integrations-auth/U-9
  id: U-74
- what: Who creates a personal Atlassian API token, and which "authenticated user's existing access controls"
    apply when the credential is a service account API key. The text says an admin creates the service
    account and key "with the appropriate scopes" (atlassian-rovo-mcp.md:12,23) and does not say what
    permissions that service account has.
  material: true
  question_ref: Q-9
  merged_from:
  - integrations-auth/U-10
  id: U-75
- what: Whether any non-interactive, service-account or shared-identity method exists for the Miro MCP
    server. The admin guide excerpt says "All access is authenticated through OAuth 2.1" (miro-mcp.md:31)
    and names no other method. The design records "no headless flow found" (2711).
  material: true
  question_ref: Q-9
  merged_from:
  - integrations-auth/U-15
  id: U-76
- what: 'Codex: which ''supported local clients'' the project plugin settings apply to; the sentence is
    cut off (package:50-51).'
  material: false
  merged_from:
  - web-clients-plugins-mcp/U-30
  - credential-flow-trace/U-35
  id: U-77
- what: Whether the working tree has uncommitted changes relative to commit 7e0adfb3. The branch ref points
    at that commit, but `git status` was not run.
  material: false
  merged_from:
  - integrations-auth/U-24
  - repo-distribution-mcp-credentials/U-1
  id: U-78
- what: Whether the .claude/.cursor workflow rule text that says .mcp.json is generated by Orqlet (A-37
    to A-40) describes a planned MCP generator or is an error; no code writes .mcp.json and the README
    says the MCP configuration is not built (A-57).
  material: false
  merged_from:
  - repo-distribution-mcp-credentials/U-8
  id: U-79
- what: Whether the CI workflow in ci.yml has run on the remote and with what result; the repository holds
    no run record.
  material: false
  merged_from:
  - repo-distribution-mcp-credentials/U-11
  id: U-80
- what: 'Claude Code: how `extraKnownMarketplaces` behaves in non-interactive sessions; only the interactive
    case is listed (distribution:11).'
  material: false
  merged_from:
  - web-clients-plugins-mcp/U-17
  id: U-81
- what: 'Claude Code: what a `headersHelper` is and where it is configured; the excerpts mention it only
    as ''a command you didn''t write'' when supplied by a repository or plugin (mcp:78).'
  material: false
  merged_from:
  - web-clients-plugins-mcp/U-20
  id: U-82
- what: 'Codex: surfaces other than the IDE extension that lack plugin support; only the IDE extension
    is named (overview:21).'
  material: false
  merged_from:
  - web-clients-plugins-mcp/U-31
  id: U-83
- what: How a fine-grained PAT is treated by the GitHub server. The vendor excerpt gives only three categories
    (classic PAT, OAuth, "Other tokens") and the "fine-grained read-only token" statement is in the design
    only (2702).
  material: false
  merged_from:
  - integrations-auth/U-7
  id: U-84
- what: The content of item 2 of the README list "To keep your GitHub PAT secure and reusable across different
    MCP hosts". The excerpt skips from item 1 to item 3 (github-mcp-server.md:19-20).
  material: false
  merged_from:
  - integrations-auth/U-8
  id: U-85
- what: The Atlassian evidence file does not contain the statement that one server serves Jira and Confluence,
    the administrator Permissions tab, or the "organisation-wide" effect. These appear only in the design
    (2635, 2705, 5947).
  material: false
  merged_from:
  - integrations-auth/U-14
  id: U-86
- what: The "client allowlist" that the design attributes to the Miro admin guide (2711, 5945) is not
    in the admin-guide excerpt (miro-mcp.md:29-32).
  material: false
  merged_from:
  - integrations-auth/U-20
  id: U-87
- what: The column headings of the Miro table (miro-mcp.md:23-24) are not in the excerpt. The third cell
    is read as the scope of the method only because the design record MI-02 reads it so (5946).
  material: false
  merged_from:
  - integrations-auth/U-21
  id: U-88
- what: 'Repository design: the source ids that carry many of the proposal''s statements about these routes
    (`CC-10`, `CX-05`, `CX-10`, `CU-09`, `CU-16`, `PL-01`, `PL-02`, `PL-03`, `MI-02`, `GH-11`) are not
    among the evidence files read, so those statements are not backed by lines in this task''s evidence.
    The proposal states that its matrix has not been run (2687).'
  material: false
  merged_from:
  - credential-flow-trace/U-50
  id: U-89
- what: 'Repository design: whether the canonical entry may carry OAuth scope pins or client ids in an
    `auth` / `oauth` block. Section 15.1 (2552) says the comparison rejects `auth` as an unknown field,
    while the matrix mentions Cursor `auth.scopes` and Claude Code `oauth.scopes` (2705) and a project
    `auth` block needing a `CLIENT_ID` (2711).'
  material: false
  merged_from:
  - credential-flow-trace/U-51
  id: U-90
contradictions:
- sources:
  - docs/design/orqlet-architecture-proposal.md:744
  - docs/design/orqlet-architecture-proposal.md:6011
  - docs/design/orqlet-architecture-proposal.md:5250
  note: Lines 744 and 6011 state that a repository's committed .claude/settings.json can require plugins
    (enabledPlugins, extraKnownMarketplaces) as documented first-hand. Line 5250 lists whether a committed
    enabledPlugins entry installs for teammates as an open documented gap [U]. Line 5248 says the list
    around 5250 is the record of earlier versions, and line 5354 says the enabledPlugins tag was re-read
    and corrected.
  merged_from:
  - repo-distribution-mcp-credentials/C-1
  id: C-1
- sources:
  - docs/design/orqlet-architecture-proposal.md:455
  - docs/design/orqlet-architecture-proposal.md:486
  - docs/design/orqlet-architecture-proposal.md:2727
  - docs/design/orqlet-architecture-proposal.md:2780
  note: 'Lines 455 and 486 say Orqlet never touches credentials and that storing or reading client credentials
    is not recommended. Line 2727 has the Miro-REST adapter read a short-lived access token from its process
    environment, and line 2780 has the write adapter apply payloads with the developer''s own identity.
    Lines 409 and 845 are narrower: they say Orqlet never reads client credential stores.'
  merged_from:
  - repo-distribution-mcp-credentials/C-2
  id: C-2
- sources:
  - docs/design/orqlet-architecture-proposal.md:2702
  - docs/design/orqlet-architecture-proposal.md:171
  - docs/design/orqlet-architecture-proposal.md:4399
  note: Line 2702 gives a PAT in headers as the Cursor mechanism for GitHub's server and says no conflict
    is documented. Line 171 lists whether Cursor uses a PAT or OAuth for that server as a fact that was
    not found. Line 4399 says GitHub's own guide and GitHub Docs document it differently.
  merged_from:
  - repo-distribution-mcp-credentials/C-3
  id: C-3
- sources:
  - src/orqlet/workflow/rules/orqlet-workflow.md:3
  - .claude/rules/orqlet-workflow.md:8
  - README.md:34-35
  - tests/unit/render/test_clients_golden.py:64-98
  - .orqlet/generated.lock.yaml:134-389
  note: The workflow rule text says .mcp.json is generated by Orqlet and attaches the rule to it. The
    README lists the MCP configuration as not built; the adapters' exact output sets contain no .mcp.json;
    the lock has no .mcp.json entry.
  merged_from:
  - repo-distribution-mcp-credentials/C-4
  id: C-4
- sources:
  - docs/design/orqlet-architecture-proposal.md:4480
  - .git/config:8-10
  - .git/refs/heads/mcp-or-plugins-research:1
  - .github/workflows/ci.yml:3-8
  note: Section 22.0 (dated 2026-10-22) says there is no commit, no remote and no CI run. The repository
    now has a branch commit, a remote origin and a CI workflow file. Whether that workflow has run is
    unknown (U-11).
  merged_from:
  - repo-distribution-mcp-credentials/C-5
  id: C-5
- sources:
  - docs/design/orqlet-architecture-proposal.md:4833-4836
  - src/orqlet/application/contracts/integrations.py:27-33
  - src/orqlet/application/contracts/common.py:50-53
  note: The Section 24.4 example gives per_client entries scope, reuse, auth and limitation fields. The
    built PerClient model has none of them and its base class forbids extra fields, so the example entries
    would not validate as written.
  merged_from:
  - repo-distribution-mcp-credentials/C-6
  id: C-6
- sources:
  - docs/design/mcp-or-plugins/evidence/web/claude-code-issue-reports.md:7-9
  - docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-manifest.md:19
  - docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-manifest.md:24
  - docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-components.md:16
  note: 'Vendor documentation says a `sensitive: true` userConfig value is stored in secure storage /
    the platform''s secure credential store. User report 62442 says such a value entered via /plugin ->
    Configure options -> Save is ''silently not persisted anywhere'' and is lost on restart. Not resolved;
    the report is a user report with no version given.'
  merged_from:
  - web-clients-plugins-mcp/C-1
  - credential-flow-trace/C-1
  id: C-7
- sources:
  - docs/design/mcp-or-plugins/evidence/web/claude-code-plugin-manifest.md:30
  - docs/design/mcp-or-plugins/evidence/web/claude-code-issue-reports.md:12
  note: Documentation says `${user_config.KEY}` is substituted in MCP server config. User report 89969
    says the placeholder is not substituted inside a server's `oauth` block. The documentation excerpt
    does not say whether an `oauth` block counts as MCP server config. Not resolved.
  merged_from:
  - web-clients-plugins-mcp/C-2
  - credential-flow-trace/C-2
  id: C-8
- sources:
  - docs/design/mcp-or-plugins/evidence/web/codex-source.md:47-48
  - docs/design/mcp-or-plugins/evidence/web/codex-source.md:42-43
  - docs/design/mcp-or-plugins/evidence/web/codex-source.md:59-60
  note: The `oauth.rs` header says 'All credentials are stored using the keyring crate', while the `config_toml.rs`
    comment documents a `file` backend and an `auto` default that falls back to a file, and a later `oauth.rs`
    line mentions a fallback to 'the json'. Not resolved.
  merged_from:
  - web-clients-plugins-mcp/C-3
  id: C-9
- sources:
  - docs/design/mcp-or-plugins/evidence/web/cursor-plugins.md:6-13
  - docs/design/mcp-or-plugins/evidence/web/cursor-plugins-reference.md:13
  note: The reference page lists `variables` as a component of the Cursor Plugins format; the component
    table on the plugins page has no Variables row. Neither excerpt says its list is complete. Not resolved.
  merged_from:
  - web-clients-plugins-mcp/C-4
  id: C-10
- sources:
  - docs/design/orqlet-architecture-proposal.md:2712
  - docs/design/orqlet-architecture-proposal.md:2713
  - docs/design/mcp-or-plugins/evidence/web/miro-mcp.md:10-11
  - docs/design/mcp-or-plugins/evidence/web/miro-mcp.md:23-26
  note: The design plans a manual project entry for Miro (a `.mcp.json` entry for Claude Code, a `.codex/config.toml`
    entry for Codex). The vendor text lists a plugin for Claude Code and Cursor, lists manual JSON config
    for "Clients without a Miro plugin", and says "If your client has a Miro plugin or extension, use
    that — and do not also add manual MCP config". The plugin is scoped "User (follows you across projects)",
    while the design's entry is project-scoped. The design records the one-method rule and a `duplicate-endpoint`
    report (2711-2712) but still plans the project entry. Codex is not classified by the vendor table
    (see U-16).
  merged_from:
  - integrations-auth/C-1
  id: C-11
- sources:
  - docs/design/orqlet-architecture-proposal.md:2705
  - docs/design/orqlet-architecture-proposal.md:2747-2748
  - docs/design/orqlet-architecture-proposal.md:2830
  note: The Jira/Confluence rows for Cursor, Claude Code and Codex name "a read-scoped service-account
    token" as a server-enforced read-only identity (2705; the Confluence and other client rows say "As
    Jira"). Section 16.1 defines the developer's IDE identity as the person's own login and a CI identity
    as a service identity "Never inferred from a developer's IDE login", and 2830 says service accounts
    "belong to the CI identity class and are not used for local developer writes". The texts place the
    service-account token in the developer-client rows and in the CI class.
  merged_from:
  - integrations-auth/C-2
  id: C-12
- sources:
  - docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md:10
  - docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md:23
  - docs/design/mcp-or-plugins/evidence/web/atlassian-rovo-mcp.md:28-31
  - docs/design/orqlet-architecture-proposal.md:2705
  note: The vendor text presents the service account API key as a machine-to-machine method for "backend
    services, CI/CD pipelines, bots, and automated agents", with the key stored "in your CI/CD system
    or secrets manager" and used "on behalf of a shared account". The design lists the service-account
    token among the authentication methods of the interactive developer clients (Cursor, Claude Code,
    Codex).
  merged_from:
  - integrations-auth/C-3
  id: C-13
- sources:
  - docs/design/orqlet-architecture-proposal.md:2702
  - docs/design/orqlet-architecture-proposal.md:2703
  - docs/design/orqlet-architecture-proposal.md:4399
  - docs/design/mcp-or-plugins/evidence/web/github-mcp-server.md:10
  - docs/design/mcp-or-plugins/evidence/web/github-mcp-server.md:26
  note: The vendor text names OAuth 2.1 as the recommended way to authenticate to the Remote GitHub MCP
    Server "if your client application supports" it, and describes OAuth scope challenges. The design
    plans a PAT in all three clients, records "OAuth with GitHub remote not found" for Claude Code, and
    says GitHub's own Cursor guide and GitHub Docs document PAT versus OAuth for Cursor differently. The
    vendor excerpt names no client, so the texts differ on OAuth availability but do not settle it (see
    U-6).
  merged_from:
  - integrations-auth/C-4
  id: C-14
- sources:
  - docs/design/orqlet-architecture-proposal.md:719
  - docs/design/mcp-or-plugins/evidence/web/cursor-mcp-help.md:11
  note: The proposal (Section 4.7, read 2026-10-20) says for Cursor 'the MCP page documents no same-name
    rule'. The evidence file (retrieved 2026-10-26) from the Cursor Help page states that for `.cursor/mcp.json`
    and `~/.cursor/mcp.json` 'the project-level config takes priority'. The pages differ (cursor.com/docs/mcp
    in the proposal's wording, cursor.com/help/customization/mcp in the evidence file), so this may not
    be a contradiction.
  merged_from:
  - credential-flow-trace/C-3
  id: C-15
self_check:
  schema: orqlet.self-check/v1
  checked_against:
    role: researcher
    phase: research
  checks:
  - what: the person's answers are in the ledger
    how: orqlet validate ledger docs/design/mcp-or-plugins/questions.yaml
    result: pass
  - what: bound values copied
    how: orqlet gate status --json at the base revision
    result: pass
  - what: web facts have a file, lines and a hash
    how: each vendor page or report is stored as verbatim excerpts in docs/design/mcp-or-plugins/evidence/web/
      with its address and retrieval date, and facts cite those files with orqlet evidence cite
    result: pass
  - what: absence claims about the code
    how: searched src, tests and tools with rg for plugin, marketplace, mcp.json, config.toml and the
      plugin settings words; the only matches are the two forbidden-file sets and the workflow rule text
    result: pass
  - what: references resolve
    how: orqlet validate as-is docs/design/mcp-or-plugins/as-is.md --fragments docs/design/mcp-or-plugins/fragments
    result: pass
  - what: the AS-IS file is accepted by the person
    how: 'the person chose "Yes, I accept it" in conversation on 2026-10-26 when /orqlet-design was started; this is not a merge on the protected baseline'
    result: pass
  unverified:
  - The vendor pages were read through a search tool that returned excerpts; the excerpts are cut at several
    places and each cut is recorded as an unknown. No vendor page was opened in full and no client was
    run.
  - The researchers' statements were checked against their cited lines by a token and quotation check
    and by re-reading a sample, not one by one.
  - The two GitHub issue reports are user reports; their version and current status are unknown.
  - 'The red CI jobs and the other open items of the project were not examined (this task has its own
    scope: ledger Q-2 to Q-4).'
---

Accepted by the person on 2026-10-26, in conversation (not a merge).

# AS-IS: MCP entries versus native plugins, with one credential per user

Facts: 154. Unknowns: 90 (76 material). Contradictions: 15. The raw reports of the four researchers are in `docs/design/mcp-or-plugins/fragments/`; the vendor excerpts are in `docs/design/mcp-or-plugins/evidence/web/`.
