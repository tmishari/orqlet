# Security review of the design, round 1

- Role: orqlet-security-reviewer, started as a typed Cursor subagent in a clean context (agent 442b9839-00aa-47d0-8e54-99688858dad9).
- Inputs given: the design folder, `as-is.md`, `questions.yaml`, `.agents/skills/orqlet-design/references/design-format.md` and the saved output of `orqlet standards for`; nothing else.
- Model requested: none named, so the subagent inherits the parent session's model. Model observed: unknown; the client reports no identity to the agent.
- Context freshness: fresh; the subagent received only the prompt above.
- Hashes when the reviewer started and when this note was saved (unchanged between the two):
  - manifest.yaml 98fe920b940fd4c4260888ba7e0aeff81fbdbc3bfccb2eb856be2fb8db5c4668
  - component.md a059ab4559a10bd7246db2b1ace265475edd511724dbc22479d6f46d7846382b
  - views.md 463adab960927297068d0834a129693abe58bb7bd670b83883ac4e676bb51082
  - adr-001 1f805cb9419b1ba023e3f55e620c9177e1622aa44b3bc35f6a27437b2bcc7e73
  - adr-002 59f3d63907314beb66a6a84b4b57ced377f54c445fbe58857d1333b810e74b25
  - adr-003 014a67a5f7aca4253829459012fa6934be77f5c575526389ce690d4d0711b58f
  - adr-004 2927b41c7f3d86ce0c0ae1b68530e0fc994a993b89a3ef28c00159254a33221f
- These hashes differ from the final manifest's, because the design changed to answer this round; round 2 reviews the changed design.

## Reviewer output (unchanged)

I found four blocking security issues in the design. Each has a short fix the design can state. The design adds no new process, network path, credential or trust boundary, and existing path checks still reject `..`, absolute paths and links.

**Blocking**

1. **Dependency changes are not watched.** The manifest says there is no new dependency, but `extractor_config` sets neither `dependency_manifests` nor `lockfiles`. With both empty, `gate status --phase` cannot see a package added to `pyproject.toml` or `uv.lock`, and under the new verdict it would report PASS. Fix: add `dependency_manifests: [pyproject.toml]` and `lockfiles: [uv.lock]`.
2. **`gate status` would report PASS for a wrong task name.** Once ORQ-I393 no longer forces NOT_RUN, a mistyped or invalid task name produces only three ORQ-I394 info findings. The result would be PASS, exit 0 and "No action needed." The task argument is never checked against the existing task-name pattern, and section 5 of the brief does not list this failure. Fix: an invalid name is a usage error with exit 2, and when no artifact exists the action line says so.
3. **The acceptance criteria leave out the negative tests.**
   - BC-21 does not require the credential and hidden-character scan to run on every pair given to `evidence cite`.
   - BC-22 does not require that evidence in another folder still fails with ORQ-E332, including a sibling folder whose name shares the prefix.
   - The tester writes tests from these criteria, so a regression in either security check could go untested.
4. **"Own task folder" is not defined.** If the folder is taken from `header.task` instead of the file's location, a copy validated from another path could exempt evidence in any folder the header names. Fix: take it from the file's location, with no exemption when the location is not a task folder.

**Non-blocking**

- Narrow the exemption to `docs/design/<task>/evidence/**`. That is the stated need, and it stops facts resting on agent-written fragments, review notes or the ledger.
- Say whether "current tree" means the working tree read through the file-system port or HEAD. That decides whether uncommitted edits can satisfy an approved AS-IS file.
- Re-run the web-evidence scan in `validate as-is`. The scan's snapshot is no longer reachable once the revision is informational. This is not a regression, and the scan is cheap.
- "No action needed." can appear while expected-change comparisons are still left to a person. All but one of them (EC-8) are manual.
- The `git diff --quiet HEAD` guard ignores untracked files such as a new `conftest.py`. The full check run before review limits the impact.
- The substitute local pytest command must keep the configured `--disable-socket` option and warnings-as-errors.

Shell commands were blocked in this read-only mode, so I could not run `orqlet evidence cite` or `git`. The evidence is file and line references without SHA-256 quote digests, and HEAD of the design branch is not confirmed (the manifest binds `a29b0ba`). Those digests should be recorded before the review note is saved.

I read the seven design files, the AS-IS file, the ledger, the format reference and the standards output. To verify citations I also read the AS-IS validator, `evidence cite`, `gate status` and its CLI command, the expected-change code, the path and contract types, the file-system and Git ports, the review skill and the pytest settings. I did not examine the four evidence files, the phase contract, the other skill and role sources, the CI workflow, the `.orqlet` YAML files, or the other command modules.

## Author's responses

Each blocking claim was checked first. `orqlet gate status no-such-task` prints three ORQ-I394 lines and ORQ-I393, and the gate command does not validate the name.

- SEC-1, accepted. `extractor_config` now names `pyproject.toml` as the dependency manifest and `uv.lock` as the lockfile, so an added dependency shows as an undeclared change.
- SEC-2, accepted. A task name that breaks the existing task-name rule is a usage error with exit 2. When no artifact of the task exists, the action line says so and asks for the task name to be checked. Both are in section 5 and EC-1.
- SEC-3, accepted. BC-21 now requires the web-evidence scan on every pair, with a failing pair reported as ORQ-E511. BC-22 now requires ORQ-E332 for evidence outside the exempt folder, including a sibling folder whose name starts with the task's name.
- SEC-4, accepted. The exempt folder is `docs/design/<task>/evidence/**`, with `<task>` taken from the AS-IS file's own path after canonicalisation. A file outside a task folder exempts nothing.
- Non-blocking, the narrower folder: accepted, as SEC-4 says.
- Non-blocking, the tree read: accepted. The file is read at HEAD through the Git port, so an uncommitted edit cannot satisfy it. The input check's approved files for the AS-IS include the evidence folder.
- Non-blocking, the scan: accepted. `validate as-is` runs the web-evidence scan on task-owned evidence under `evidence/web/`.
- Non-blocking, manual comparisons: accepted. With `--phase`, when manual expected changes are open, the action line says how many need a reviewer's comparison.
- Non-blocking, untracked files: kept. The cited files must still be tracked, as today, and the full check run before review covers new files that are not cited.
- Non-blocking, the pytest form: accepted. The constraint now says the substitute keeps every configured option, including disabled sockets and warnings as errors.
- Quote digests: the review format for design notes does not require them. The cited lines were read back in the author's session for the blocking claims.
