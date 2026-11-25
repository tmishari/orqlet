# ADR-004: Version 1.0.0; keep the hash algorithms, let rendered bytes change

## Context

The person chose no byte compatibility and a new major version, 1.0.0 (Q-5, Q-13). Managed projects store hashes: canonical JSON digests (A-9), line-range hashes in every AS-IS and plan record (A-10), manifest hashes (A-21), and rendered-file hashes plus block markers in `generated.lock.yaml` and `AGENTS.md` (A-20). `orqlet upgrade` decides whether the team edited a file by comparing its current hash with the recorded one (A-25).

## Decision

1. The CLI and the workflow package carry version 1.0.0. `identity.json` keeps its `controls_level`, so the upgrade rule that refuses a weaker level stays meaningful (`src/orqlet/application/usecases/upgrade.py` lines 356-366).
2. `digest_of` (RFC 8785 subset, UTF-16 key order) and the line-range hash (CRLF to LF, 1-based inclusive lines joined by LF) are reimplemented exactly; the fixture of ADR-002 proves it (BC-3). The file hash used for rendered and seeded entries (SHA-256 of the bytes with CRLF read as LF) is kept as well. So is the block-marker hash of each managed AGENTS.md block: SHA-256 of the UTF-8 body after CRLF and lone CR become LF and trailing newlines are removed (`src/orqlet/adapters/render/instructions.py` lines 40-43, `src/orqlet/adapters/render/emit.py` lines 33-36; A-20). The standards lock keeps both of its 0.5.2 hashes, one per consumer (C-7): `generated.lock.yaml` records a plain SHA-256 of its bytes (`src/orqlet/application/usecases/render_all.py` line 419), and gate status binds the hash with CRLF read as LF (`src/orqlet/application/usecases/gate_status.py` line 89). The BC-3 vectors cover all four algorithms.
3. Everything rendered (YAML and JSON layout, Markdown generated from templates, schema text) may differ from 0.5.2.
4. 1.0.0 reads `generated.lock.yaml` written by 0.5.x. Because the file hash is unchanged, a file whose current hash equals its recorded hash is known to be untouched by the team and is re-rendered; a file whose hash differs is treated as edited, exactly as today (BC-5).
5. Journals and backups written by 0.x are not replayed. 1.0.0 keeps 0.5.2's journal folder, `projects/<project id>/upgrade/`, and marks its own records with a `format` field, so a record without it is a 0.x record. Resuming or rolling back a 0.x change is refused as a journal error, ORQ-E136, exit 3 (`src/orqlet/interface/cli/errors.py` line 19, `src/orqlet/interface/cli/runner.py` line 33 at the base revision). Open 0.5.2 changes are finished with 0.5.2 before 1.0.0 touches the project. 1.0.0 reads only the format and status of a 0.x record and never rewrites it. An open 0.x record makes every journalled change refuse with ORQ-E131 and advice that names 0.5.2; an open 1.0.0 record makes an upgrade refuse; an unreadable record refuses with ORQ-E136; finished ones are ignored (ADR-007 decision 11). The release notes describe this procedure.

## Consequences

- Recorded line-range evidence in `docs/design/` of every task stays valid with 1.0.0, so no task re-cites its facts.
- Artifact headers of other tasks bind `workflow_version`, `protected_set_digest`, `standards_lock_hash` and `applicable_rules_hash` (A-32). The standards change and the re-render of ADR-006 change the last three, so `gate status` reports those tasks' artifacts as stale; a frozen task that resumes needs the impact review of the invalidation matrix, not a new citation of its facts.
- One `orqlet upgrade` per managed project replaces the rendered files with the 1.0.0 layout; team edits are kept.
- Keeping the algorithms costs two small, fully specified functions and their tests.

## Rejected alternatives

- New hash algorithms (for example plain serde_json bytes): simpler by a few lines, but every recorded citation and every lock entry in every managed project would read as changed, and upgrade would treat every generated file as edited by the team.
- Byte-identical rendering of every file: needs a YAML emitter that reproduces PyYAML's layout exactly (U-7); the person declined this promise (Q-5).
- 0.6.0: the person chose 1.0.0 (Q-13).
