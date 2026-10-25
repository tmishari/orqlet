# AS-IS: implementing Orqlet (facts only)

| Field | Value |
|---|---|
| Task | `orqlet-implementation` |
| Phase | 1, zero-noise research. Facts, unknowns and contradictions only. No design opinions, no recommendations |
| Date and base | 2026-10-21. The directory is not a Git repository, so there is no base revision. The design file's SHA-256 is the anchor (A-01) |
| Method | Local read-only probes, one PyPI JSON read, two Context7 documentation lookups (Typer, Pydantic), and reads of the design proposal. No package was installed, no model or MCP server was called, no external system was changed |
| Status | Draft, awaiting your acceptance. Nothing here was independently reviewed |

Evidence forms: `probe` is a local command run on 2026-10-21. `design §n` is a section of `docs/design/orqlet-architecture-proposal.md`. `PyPI` is `pypi.org/pypi/<name>/json`. `C7` is Context7.

## 1. Repository state

| ID | Fact | Evidence |
|---|---|---|
| A-01 | The only project file is `docs/design/orqlet-architecture-proposal.md`: 5,960 lines, 909,627 bytes, SHA-256 `d9d5e675b3d18c2c95ee38aa4d1634d2a6107c4b635135957ec0d51e29b324d4`. Two `.DS_Store` files also exist | probe `find`, `shasum -a 256` |
| A-02 | The directory is not a Git repository | probe `git rev-parse` (fatal: not a git repository) |
| A-03 | There is no `pyproject.toml`, source, test, CI workflow, `.prompts`, `.claude`, `.cursor`, `.codex` or `.github` | probe `find`, `ls -d` |
| A-04 | The proposal is v0.4, "awaiting human approval". Requirements R-12 and R-13, the `.prompts/` scaffold and the per-role model profiles were added after its two review rounds and were not independently reviewed | design header, §0.3, §26.11 |

## 2. Standards that govern the work locally

| ID | Fact | Evidence |
|---|---|---|
| A-05 | The repository has no local standards directory. `~/CLAUDE.md` (29 bytes) holds only the heading "# Claude Code Configuration" | probe `ls`, `head` |
| A-06 | Rules injected into this workspace: no hardcoded credentials or secret-like values; certificates must be flagged for checks; no banned or deprecated cryptography (SHA-256 is the digest used by the design); unit tests for new and changed code; CI must pass; no unsolicited `.md` files, propose documents first; use Context7 for version-sensitive APIs; AWS access uses IAM Identity Center with Duo | session rules |

## 3. Local environment (macOS 27.0.1, arm64)

| ID | Fact | Evidence |
|---|---|---|
| A-07 | Default `python3` is 3.11.17. Also present: 3.12.11 and 3.13.5 (uv-managed), 3.14.8 and 3.15.0 (Homebrew), 3.11.13 (uv-managed), system 3.9.6 | probe `uv python list --only-installed` |
| A-08 | SQLite is compiled with FTS5 and a virtual FTS5 table was created in memory on all five interpreters 3.11 to 3.15. SQLite is 3.54.1 on 3.11.17, 3.14.8 and 3.15.0, and 3.47.1 on the uv-managed 3.12.11 and 3.13.5 | probe, in-memory script |
| A-09 | Tools found: `uv` 0.7.19, `pipx` 1.18.3, `git` 2.56.0, `pre-commit` 4.7.0, `sqlite3` CLI 3.54.0, `gh`, `docker`, `ollama` 0.40.6. `codex` is not on `PATH` | probe |
| A-10 | `claude`, `node` and `npm` resolve as shell functions or aliases and were not executed. `cursor` and `cursor-agent` exist at `~/.local/bin`; their versions were not re-probed | probe `command -v` |
| A-11 | Ollama has one local model: `gemma4:latest`, 6.6 GB | probe `ollama list` |

## 3a. Package facts (PyPI, read 2026-10-21)

| Package | Latest | Released | requires-python | License |
|---|---|---|---|---|
| typer | 0.27.3 | 2026-10-06 | >=3.10 | MIT |
| pydantic | 2.14.1 | 2026-10-11 | >=3.10 | MIT |
| PyYAML | 6.0.3 | 2025-09-25 | >=3.8 | MIT |
| ruamel.yaml | 0.19.1 | 2026-01-02 | >=3.9 | MIT |
| filelock | 4.2.4 | 2026-10-19 | >=3.11 | MIT |
| platformdirs | 4.13.5 | 2026-10-19 | >=3.11 | MIT |
| import-linter | 2.15 | 2026-09-04 | >=3.10 | BSD 2-Clause |
| pytest | 9.1.1 | 2026-06-19 | >=3.10 | MIT |
| pytest-socket | 0.8.1 | 2026-08-19 | >=3.10 | MIT |
| pyfakefs | 6.2.0 | 2026-04-12 | >=3.10 | Apache-2.0 |
| ruff | 0.17.1 | 2026-10-15 | >=3.7 | MIT |
| tomlkit | 0.15.2 | 2026-10-16 | >=3.9 | MIT |
| rfc8785 | 0.1.4 | 2024-09-27 | >=3.8 | not stated in the metadata |
| copier | 9.19.1 | 2026-10-13 | >=3.10 | MIT |
| uv | 0.13.4 | 2026-10-20 | >=3.8 | MIT OR Apache-2.0 |

| ID | Fact | Evidence |
|---|---|---|
| A-12 | Typer testing uses `from typer.testing import CliRunner` and `runner.invoke(app, [...])` with `result.exit_code` and `result.output` | C7 `/websites/typer_tiangolo` |
| A-13 | Typer 0.14.0 and later require an explicit `name` in `app.add_typer(sub_app, name="...")`. The name is no longer inferred from a callback function | C7 Typer release notes |
| A-14 | Pydantic v2 ignores unknown fields by default. `ConfigDict(extra='forbid')` raises `extra_forbidden` and generates `additionalProperties: false` in the JSON Schema. `model_json_schema(mode=...)` takes `validation` (default) or `serialization`, and they differ for `Decimal` | C7 Pydantic v2.14.1 |

## 4. What the design fixes for the first implementation

| ID | Fact | Evidence |
|---|---|---|
| A-15 | Stack: Python, Typer behind a thin adapter, Pydantic v2, exact-pinned dependencies, Python floor 3.12 (3.11 workable), distribution through `uv tool` or `pipx` from M1. FTS5-dependent features are conditional on spike S-09 | design §25.3 D-02 |
| A-16 | Layers: Interface (Typer commands, hook and CI entry points, human and `--json` renderers) depends on Application (use cases, ports, Pydantic contracts), which depends on Domain. Adapters implement ports. `import-linter` and Ruff `TID251` enforce the rules | design §6.2 |
| A-17 | Git access is by shelling out to `git` behind a port | design §5.2 |
| A-18 | Built first: five extension points (`InstructionAdapter`, `ProjectScanner`, `StandardsSource`, `VcsPort`, the read subset of `ChangeRequestPlatform`) and six test seams (`FileSystem`, `Clock`, `IdGenerator`, `Prompter`, `ProcessRunner`, `KnowledgeImpactAnalyzer`) | design §6.8 |
| A-19 | Release path: MVP-1 is M0 to M2, MVP-2 is M3 to M4, 1.0 is M5 to M7. M0 is spikes and decisions, M1 the structure lifecycle and the protected workflow, M2 the workflow gates and the CI check | design §22 |
| A-20 | MVP-1 commands: `init`, `upgrade`, `rollback`, `release`, `sync`, `doctor`, `explain`, `standards for`, `validate as-is\|design\|plan\|ledger\|review\|test\|knowledge`, `knowledge impact`, `gate status`, `hook`, `ci check\|collect`, `review prepare`. All accept `--json`. None calls a model | design §23 |
| A-21 | Output volume of `init` for three clients: 8 skills (6 protected, 2 optional), 6 subagent role definitions (5 required, 1 optional), 3 generated CI workflow files, the `.orqlet/` configuration files, 3 `.prompts/` seed files and the PR template blocks | design §1.3, §10.3, §17.8, §12.8, §13.7 |
| A-22 | Acceptance basis: 100 failure-mode scenarios assigned to milestones, and 29 enforcement-matrix rows that M2 acceptance requires a fixture for. None was executed | design §21.6, §19.10, §22 |
| A-23 | The design records Typer 0.27.3 as the version it researched, equal to the latest PyPI release today | design §5.2, PyPI |
| A-24 | Preconditions stated for starting: M0 begins when Q-01, Q-03, Q-04 and Q-05 are answered. Every spike in Appendix C needs its own approval, scope and budget. The detailed implementation plan follows architecture approval and is itself produced through the four-phase workflow | design §25.3, §22, Appendix C |
| A-25 | Q-01, Q-03, Q-04, Q-05 and Q-06 are open in the design | design §25.1 |

## 5. Unknowns

| ID | Unknown | Material | What it affects |
|---|---|---|---|
| U-1 | The design's approval status: v0.4 is not approved | Yes | Whether the Phase 2 design approval can be taken from it |
| U-2 | Code host and CI platform (Q-01), and whether a GitHub App can be created in the organisation | Yes | M0 spikes S-14 and S-28, the M2 CI workflows |
| U-3 | Who counts as an authorised approver for designs and plans (Q-03) | Yes | M2 approval evidence |
| U-4 | Whether administrators can deploy managed IDE settings (Q-04) and which local guard is wanted (Q-05) | Yes | M2 edit guard, option choice |
| U-5 | Where the package is published and pinned (internal index or PyPI) | Yes | M1 packaging and the CI pin |
| U-6 | The company's standards, the API documents, the domain knowledge and the team PR template are not supplied | Yes for pack content, no for structure | Standards packs, `.prompts/` content, PR template block |
| U-7 | How each client loads the generated files. No IDE was opened | Yes | M1 golden tests, spikes S-02, S-21, S-22, S-23 |
| U-8 | Windows and Linux behaviour of paths, file locks, atomic rename and hooks | Yes | M1 and M3 acceptance, spikes S-08, S-25 |
| U-9 | Which RFC 8785 canonicalisation to use: `rfc8785` 0.1.4 was last released 2024-09-27 and its PyPI metadata has no license text | Yes | Hashing in the binding, approval and index keys |
| U-10 | Whether `tomlkit` suits round-trip edits of `.codex/config.toml`. The design lists this as not researched | No | MCP entry generation |
| U-11 | Authentication and network behaviour of client model-metadata commands | No | `orqlet models refresh` (1.0) |
| U-12 | The Miro decision (Q-06) and the spikes S-26 and S-27 | No for M0 to M2 | M4 and M6 |
| U-13 | Whether FTS5 is present in Linux and Windows Python builds (S-09) | Yes | MVP-2 |
| U-14 | The version of `cursor-agent` and whether `gh` is authenticated | No | Local spikes |

## 6. Discrepancies

| ID | Statement A | Statement B |
|---|---|---|
| C-1 | Design B-47: Python 3.12 and 3.13 are "not installed locally", so the SQLite transaction checks are untested there | A-07: 3.12.11 and 3.13.5 are installed locally (uv-managed), with SQLite 3.47.1 |
| C-2 | Design D-02: Python floor 3.12 | A-07: the default `python3` is 3.11.17. `filelock` 4.2.4 and `platformdirs` 4.13.5 need Python 3.11 or later |
| C-3 | Design §3.3 recorded the current `uv` as 0.13.1 and the local one as 0.7.19 | PyPI today: `uv` 0.13.4. The local `uv` is still 0.7.19 (A-09) |
| C-4 | Design §3.3 lists no Ollama among the local tools, and §14.4 says Ollama's hosted offerings were not researched | A-09, A-11: Ollama 0.40.6 is installed locally with `gemma4:latest` |
