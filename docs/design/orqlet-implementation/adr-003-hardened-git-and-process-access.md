# ADR-003: One hardened runner for `git` and every other subprocess

Status: proposed (needs approval with `design.md`).

## Context

The proposal reaches Git by running the executable behind a port, because GitPython is in maintenance mode with 2026 command-execution advisories, pygit2 is GPLv2 with a linking exception and dulwich is slower (§5.2, A-17). In the trusted CI stage the pull request's files must be read as Git objects with no working tree and no checkout (§19.8.2). A round-2 reviewer showed on Git 2.56.0 that a repository's own `core.fsmonitor` runs under `ls-files`, `status`, `diff` and `add -n`, that `filter.*.clean` and `diff.external` run under `status` and `diff`, and that `rev-parse` runs none of them. Git is verified only at 2.56.0 (A-09, U-8).

## Decision

1. All subprocess calls go through one `ProcessRunner` port (`application/ports/process.py`) implemented by `adapters/process/subprocess_runner.py`: an argument list, `shell=False`, a scrubbed environment (an allowlist of variables plus `LC_ALL=C`, `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`), a timeout, a cap on captured output, and a typed error for every failure. Initial values: 30 seconds and 16 MiB (to be measured in S3).
2. Git calls go through `adapters/git/git_runner.py`. Every call starts with `git -c core.fsmonitor=false -c core.hooksPath=` and uses a fixed **allowlist of subcommands**: `rev-parse`, `for-each-ref`, `rev-list`, `merge-base`, `ls-files`, `ls-tree`, `cat-file` (including `--batch` and `--batch-check`), `diff-tree`, `diff-index` and `write-tree`. Every diff call adds `--no-ext-diff --no-textconv`.
3. `status`, `diff` (porcelain), `add` and `checkout` are not on the list. `git write-tree` is allowed only in the local hook and review-packet code paths and never in stage 2 of CI.
4. File contents in stage 2 come from `cat-file --batch` at the pinned head SHA. The trusted stage never has the pull request's files in a working tree (proposal §19.8.2).
5. Branch names that `init` passes to `git init` are validated with `git check-ref-format --branch` and rejected if they start with `refs/` or equal `@` (proposal §9.1.1).

## Consequences

- One place to reason about command execution and one place to change when a Git version behaves differently (spike S-24).
- A regression suite reproduces the reviewers' hostile-configuration experiments: a repository with `core.fsmonitor`, `filter.*.clean` and `diff.external` set to a marker script must leave the marker unrun for every allowed call.
- Anything the allowlist lacks needs an ADR change, which is the intended friction.
- Spawning `git` per call costs time. `cat-file --batch` keeps one process for many objects.

## Rejected alternatives

| Alternative | Why not |
|---|---|
| GitPython | Maintenance mode and command-execution advisories (proposal §5.2) |
| pygit2 | GPLv2 with a linking exception, and a native build dependency |
| dulwich | Pure Python but slower, and its behaviour on Windows and large objects is not verified |
| Calling `subprocess` directly from use cases | Spreads the hardening rules over the code base and breaks the layer contract |
