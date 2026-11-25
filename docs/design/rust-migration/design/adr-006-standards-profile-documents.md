# ADR-006: Standards, the rust-cli project kind and the documents

## Context

The team standards name Python tools and Python layer paths (A-27; `.prompts/rules.yaml` check references `uv run lint-imports` and the two tools scripts). The profile records python-cli with facts from `pyproject.toml` and `uv.lock` (A-29), and the profile contract knows only python-cli, python-service and unknown and requires a `python` fact. README installs with uv (A-28); AGENTS.md says no tests (A-30) and that only release 0.5.2 may advance. The person chose to change these in this task (Q-10), to keep the tests required (Q-11), and to add a rust-cli kind (Q-12).

## Decision

1. `.prompts/rules.yaml` (team-owned seed) is rewritten in one reviewed change. Every `src/orqlet/**`, `src/**` and `tests/**` scope is replaced, not kept beside the new ones: no Python change lands during this task (ADR-002), so the Python code needs no rules. The header says that each deterministic rule names the command that fails, and it no longer mentions `pyproject.toml` or CI. The rules become:

   | Rule | New text, in short | Scope | Enforcement and check |
   |---|---|---|---|
   | ARCH-001 | Crate dependencies point inward only (cli, adapters, application, domain); xtask uses application and domain; each crate's third-party crates are on its allow-list | `crates/**`, `xtask/**`, `Cargo.toml` | deterministic: `cargo run -p xtask -- arch` |
   | ARCH-002 | The domain crate is `no_std`; the application crate reaches files, processes, the network, the environment and standard streams only through ports (ADR-001 decision 3) | `crates/orqlet-domain/**`, `crates/orqlet-application/**` | deterministic: `cargo clippy --workspace --all-targets -- -D warnings` |
   | ARCH-003 | The client adapter modules (Claude Code, Codex, Cursor) never use one another; `workflow/` is read-only data, embedded only by `orqlet-adapters`, never through `include_str!` or `include_bytes!` elsewhere | `crates/orqlet-adapters/src/clients/**`, `workflow/**` | review |
   | SEC-001 | Only the process module, a private child of the Git module in `orqlet-adapters`, creates processes; Git runs only through GitRunner with the rules of ADR-007; tests and the xtask may start processes only under a scoped `allow` with a reason | `crates/**`, `xtask/**` | review |
   | SEC-002 | Files of the managed repository are untrusted; shipped code reads them through the FileSystem port and parses YAML, JSON and TOML only through the documents module; their content is never executed | `crates/*/src/**` | review |
   | SEC-003 | Unchanged | none (all files) | review |
   | SAFE-001 | Every project write goes through a journalled change plan, backup first and lock file last, inside the project root. Outside the root Orqlet writes only its data directory (journals, backups, apply locks and review packets), which never lies inside the repository, with private modes on Unix (ADR-007 decision 10). The user-scope text goes, since its writer is not ported (Q-8) | `crates/orqlet-application/src/**`, `crates/orqlet-adapters/src/**` | review |
   | NOMODEL-001 | Unchanged | none | review |
   | DET-001 | Generated output is deterministic; golden fixtures change only in a reviewed commit that says why (the `--update-golden` flag and the CI clause go) | `crates/orqlet-adapters/src/clients/**`, `crates/orqlet-adapters/src/render/**`, `workflow/**` | review |
   | DET-002 | Any change to `workflow/` rebuilds `MANIFEST.json` and bumps the package version before release | `workflow/**` | deterministic: `cargo run -p xtask -- manifest --check` |
   | DET-003 | Committed schemas match the Rust contract types; regenerate them with the xtask | `crates/orqlet-application/src/contracts/**`, `workflow/schemas/**` | deterministic: `cargo run -p xtask -- schemas --check` |
   | QA-001 | `cargo fmt --check`, Clippy with `-D warnings` and `cargo test` pass on macOS; `cargo check` and Clippy pass for `x86_64-unknown-linux-gnu` and `x86_64-pc-windows-msvc` (Q-11, Q-15); no CI | none | review |
   | STYLE-001 | Unchanged text | `crates/**`, `xtask/**` | guidance |
   | MODEL-001 | Unchanged text | `crates/**`, `workflow/**` | review |
   | MODEL-002 | Unchanged | `docs/design/**` | review |

   SAFE-001 and SEC-002 cover shipped code, so the xtask writing `workflow/` and tests writing temporary repositories are outside them by scope, not by waiver.

   Right after the rewrite, this repository's generated files and `.orqlet/standards.lock.yaml` are re-rendered with the installed 0.5.2 binary. This way the IDE rule files and AGENTS.md blocks never show the Python rules beside the new standards that `orqlet standards for` already prints (`src/orqlet/application/usecases/standards_for.py` lines 183-197). They are rendered again with 1.0.0 before removal. Each re-render changes the lock hashes that artifact headers bind (`src/orqlet/application/usecases/gate_status.py` lines 81-94). So at each one, this task's own approved artifacts go through the impact review of the invalidation matrix and are re-bound in the same change, as ADR-004 describes for other tasks.
2. Profile contract: kind gains `rust-cli`; `facts.python` becomes optional; a `rust` fact and package manager `cargo` (Cargo.lock) are added; a profile of kind rust-cli needs the `rust` fact, a Python kind needs `python`. The schema id stays `orqlet.project-profile/v1`: every 0.5.2 profile remains valid. A Rust project scanner, with the input rules of ADR-007 decision 13, reports kind rust-cli when the scope's Cargo.toml has a `[package]` with a `[[bin]]` table or a `src/main.rs` beside it, or has a `[workspace]` whose literal `members` include such a package. The `rust` fact is `[package].rust-version`, or else `[workspace.package].rust-version`, and cites that line of the file that holds it. For this repository, that is the root Cargo.toml (a workspace whose member `crates/orqlet-cli` has `src/main.rs`) and Cargo.lock. The existing technology scanner keeps reporting Rust and known crates (`src/orqlet/adapters/scan/technology_scanners.py` lines 190-225).
3. This repository's profile is re-derived with 1.0.0 and approved again by the person.
4. README: install with `cargo install --path crates/orqlet-cli` or a downloaded binary; development commands are the QA-001 checks; Python and uv text is removed.
5. AGENTS.md team text: the Testing section states that the Rust tests are required (Q-11); the current-priority section names this task as resumed by the person; the onboard-recorded commands are re-recorded through `/orqlet-onboard` with the person's yes, as that section prescribes. Generated blocks change only through `orqlet upgrade`.
6. `docs/design/work-status.md` records that the person started rust-migration on 2026-11-25.
7. Repository files that name the Python layout change with it. `.github/CODEOWNERS` replaces `src/orqlet/**`, `src/orqlet/workflow/seeds/**`, `tests/**`, `pyproject.toml`, `uv.lock` and `tools/**` with `crates/**`, `workflow/**`, `workflow/seeds/**`, `xtask/**`, `Cargo.toml`, `Cargo.lock` and `rust-toolchain.toml`, each owned by tmishari. `.gitattributes` drops `tests/golden/** -text` and `*.whl binary`. `.gitignore` ignores `/target`.

## Consequences

- Standards, profile and docs describe the Rust project in the same task that creates it, so no release ships stale instructions.
- The generated rule files and AGENTS.md blocks re-render from the new rules; ORQLET-MODEL-001 is unchanged.
- Linux and Windows run-time behaviour is not tested; the standard says so instead of implying it.

## Rejected alternatives

- A new profile schema `v2`: the change only adds a value and an optional field, so every v1 profile stays valid; a v2 would force every managed project to migrate its profile for nothing.
- Kind `unknown` for this repository: smaller, but the person chose rust-cli (Q-12).
- Leaving the standards for a later task: the person chose this task (Q-10), and between the two tasks the standards would require tools that no longer exist.
