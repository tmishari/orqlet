# ADR-002: Rewrite beside the Python package, prove parity, then remove it

## Context

About 28,000 lines of Python hold the behaviour (A-1, A-5). The person asked for a full migration and removal of the Python code afterwards (Q-2), a native binary (Q-4) and Rust tests (Q-3, Q-11). The repository holds a large real corpus of artifacts under `docs/design/` that 0.5.2 validates today.

## Decision

1. The Rust workspace is added beside `src/orqlet/`. Both exist until the Rust build passes every acceptance criterion of the brief except BC-14, which checks the removal itself. This is the removal gate; the brief refers to it rather than restating it.
2. Before removal, the Python code produces three fixtures that the Rust tests keep. The first is a vector set for `digest_of`, the line-range hash, the file hash and the block-marker hash (A-9, A-10, A-20; ADR-004), plus the value and type that the 0.5.2 strict loader gives each YAML scalar form (ADR-007 decision 3). The second is a parity table of verdict and finding codes from `orqlet validate` for every artifact under `docs/design/`, run on a checkout of the base revision 3e3c311 (BC-3, BC-4). The third is the `--help` text of every command and group, from which the option list of BC-1 is taken (U-13). The fixtures hold only verdicts, codes, digests and help text, and they are reviewed for secrets before they are committed (ORQLET-SEC-003). The Rust tests read them, so they outlive the Python code. Intended differences are listed in the fixture as expected changes: the model-policy warning ORQ-W541, which compares a policy with the running release (`src/orqlet/application/usecases/validate_model_policy.py` lines 405-415); every rule of ADR-007 marked "new"; verdicts that relied on Pydantic's lax coercion; and Python API extraction (Q-7). `validate as-is`, `design`, `plan` and `ledger` do not compare a header's `workflow_version` with the running binary (only the model-policy check reads the release, by the search above). So BC-4 can hold for artifacts bound to 0.5.2.
3. The fixture-reading tests live in `crates/orqlet-cli/tests/` under the scoped allow of ADR-001 decision 5. The parity test creates a detached `git worktree` of 3e3c311 in a temporary folder, with `GIT_CONFIG_NOSYSTEM=1` and an empty global configuration, and removes it afterwards. When the revision is missing, for example in a shallow clone, the test fails with a message naming the revision.
4. Integration tests run the built `orqlet` binary against temporary repositories for init, upgrade, rollback, sync, doctor and hook, and compare envelopes, exit statuses and codes with expectations derived from the 0.5.2 behaviour (BC-1, BC-2, BC-5). Tests that call `git` set `GIT_CONFIG_NOSYSTEM=1` and an empty global configuration, so a developer's own hooks do not run.
5. Removal deletes the whole `src/orqlet/` folder. The workflow data has moved to `workflow/` by then, and the only other non-Python file under it is the Python package marker `py.typed` (`git ls-files src` at 3e3c311). It also deletes `pyproject.toml`, `uv.lock`, `tools/`, the ignored `.venv` and the Python caches. Nothing under `docs/design/` of other tasks is touched (Q-2).

## Consequences

- Parity is measured on real files, not on samples written for the test.
- While both exist, two implementations must not drift: no feature work lands in Python during this task (the work status already freezes other work, A-31).
- Fixtures fix today's codes; an intended difference (Python API extraction, Q-7) is listed in the fixture as an expected change, never silently updated.

## Rejected alternatives

- Incremental port through PyO3 (Rust modules called from Python): keeps a Python runtime until the last module moves, contradicting the native binary (Q-4), and doubles the build tooling meanwhile.
- Rewrite without a parity corpus, tests written from reading the Python: cheaper, but nothing would show that 34 validators agree with 0.5.2; once the Python is removed the question could no longer be answered.
- Remove the Python first and port from git history: loses the ability to generate fixtures and to compare outputs.
