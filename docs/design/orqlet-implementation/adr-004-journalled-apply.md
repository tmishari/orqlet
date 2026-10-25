# ADR-004: A journalled apply engine with the manifest written last

Status: proposed (needs approval with `design.md`).

## Context

`init`, `upgrade` and `rollback` write many files that other developers' agents load. The proposal requires previews, ownership tracking, three-way classification, a journalled upgrade with resume and rollback, and a test that kills the apply after k of n files for every k and converges (§9.3, §9.5, §20.9, M1 acceptance, FM-U03). The journal and backups live in the user data directory, not in the repository (§6.7). Atomic rename and directory flush on Windows are unverified (S-08, S-25).

## Decision

1. **Plan first.** A pure function turns the rendered files and the current tree into a plan: for each path, the owner mode, the class and the action. Nothing is written until the maintainer approves the preview. The apply requires a clean tree or a new branch.
2. **Backup.** Every file that will change is copied to `<user data>/projects/<repo-id>/backups/<change-id>/` with its SHA-256.
3. **Journal.** The engine writes `<user data>/projects/<repo-id>/upgrade/<change-id>.json` in canonical JSON (ADR-002): the plan, each file's before and after digests and a status per file. The journal itself is replaced atomically.
4. **Write.** For each file in sorted path order: write a temporary file in the same directory, flush it, `os.replace` it onto the target, then mark the file done in the journal. Directory flush is performed where the platform supports it.
5. **Manifest last.** `.orqlet/generated.lock.yaml` and `.orqlet/workflow.lock` are replaced after every other file, each atomically. A crash between the two replacements is detected by the journal and by the digest comparison, and `gate status` then reports `NOT_RUN: mixed-version`.
6. **Resume.** `upgrade --resume` reads the journal, verifies that each file marked done equals its planned digest, and applies only the rest. A file that matches neither its before nor its after digest stops the run as a conflict.
7. **Rollback.** `rollback <change-id>` restores a file only if its current digest equals the digest the journal says was applied. Otherwise it refuses and shows the difference. A rollback below the workflow floor is refused (proposal §20.9).

## Consequences

- Any crash leaves either the old state, the new state, or a recorded partial state that `resume` or `rollback` finishes.
- The fault-injection test (kill after k of n, for every k) is straightforward because the engine takes the file system as a port.
- Orqlet never touches files it does not own. A user edit between plan and apply turns into a conflict, not an overwrite.
- On Windows, `os.replace` fails when the target is open, so the engine retries a bounded number of times and then reports the file. Directory flush is a no-op there until S-25 reports.

## Rejected alternatives

| Alternative | Why not |
|---|---|
| Stage the whole tree in a temporary directory and swap it in | Would replace personal and unrelated files that Orqlet must never touch |
| Use Git stash or a temporary branch as the backup | Depends on repository state and on the developer's clean tree, and a stash can be dropped by accident |
| Record the journal in SQLite | The proposal forbids a workflow-state database in the first implementation (R-01, D-03) |
| Write files directly and rely on `git checkout` to recover | Not safe for untracked files, and it hides partial states |
