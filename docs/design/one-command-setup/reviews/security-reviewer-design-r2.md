# Security review of the design, round 2

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-20T12:47:09Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T12:47:09Z) and at save (2026-11-20T12:48:58Z) are identical: no design file changed while the reviewer ran.

| File | sha256 |
|---|---|
| design/manifest.yaml | b8cd27a1368566e3de7b191cdb9b9b1b028c4e5f1f7a95899e3c22e8723579ac |
| design/component.md | 4a738fda55357ce7ea4e784bd97d2268a00c6b72e66a4d8cdd7bc536407f8e08 |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | c66bf043e949384421ac711fd782d426ddf38b6a2f4c0394ed36033b37b9fae8 |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | 5bf88b3ce9d12a8c6db0556997e9ddc93b292fb00903f0ea297a478ffd2cee36 |
| design/adr-002 | d3ac6abd9baa42222f7589b6340c10dce23655838166431c28190f56eebe4e3f |
| design/adr-003 | bbc3dbff99b268cff4271c1d4c774ba63e7727e14fbef284b05ad22a4dbd8637 |
| design/adr-004 | 1d23439717edda2d08c91addbd2d55dd82353f4c2404ec00b5fef0d7f13fc46e |
| design/adr-005 | ae73898709a4c7241eb8eaa6db7d5318b41f6ba43ce5645f2445f1937aa9ba99 |
| design/adr-006 | feaca7dde4ee51e5d8eb0d3cb86661b7b84e299269767f609bc57286fa2c0f1c |
| design/adr-007 | 04e9131c62a8e0711118d63cb6fab66de2283e56b13a3df29b8eb6677ce2c1c1 |
| questions.yaml | 9bc0396b719d60664de8376aa4f55404e2c2328a5ce1487715b2b0e7a72a0a73 |

The design files changed after this note, to answer the architecture findings of the same round and these non-blocking findings (see "Author's responses"). The reviewed content is therefore not what will merge, and round 3 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: approve.** I found 0 blocking and 8 non-blocking findings. The round-2 design covers all three trust boundaries with concrete controls that can be tested:
- **User client folders (TB-1):** root validation, per-root writable sub-paths, manifest-hash ownership with owner sets, 0600 backups and journals, and no printing of shared-file contents. The tests are BC-6, BC-8, BC-27 and BC-29.
- **Package downloads (TB-2):** fixed argument vectors through `ProcessRunner`, a scrubbed environment, a private working folder and pinned top-level versions. The residual risk is stated.
- **Hook payloads (TB-3):** a size cap, a strict parser, no process, no writes, and fixed templates with validated fields only.

I checked several code citations against the source and they hold:
- `local_fs.py` checks the root only at lines 74-77.
- `write_atomic` keeps an existing file's mode at lines 113-124, so rewriting a 0600 `settings.json` does not widen its permissions.
- `wiring.py` lines 145-149 are as cited.
- `git_runner.py` has the allow-listed subcommands and `core.fsmonitor=false` / `core.hooksPath=`.
- The subprocess runner uses `shell=False` and a scrubbed environment.

What I could not check:
- **Current revision:** the sandbox refused `git rev-parse HEAD`, so I reviewed the files as they are on disk. The manifest records base revision 8994354.
- **Artifact hashes:** I did not recompute the manifest's sha256 values.
- **Round 1:** I did not read the round-1 review note, because it is not among the allowed inputs. I judged round 2 on its own merits.
- **SAFE-001 text:** I did not open `.prompts/rules.yaml:66-72`, which is outside the allowed paths.
- **Client behaviour:** nothing about client-side hook launching is in the repository. The Windows point in F-1 is therefore an observation and does not block.

This review is an extra check, not a guarantee.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 2, role: security-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: TB-3 / ORQLET-SEC-002
    statement: >-
      Hook registrations call the bare `orqlet` executable on purpose (adr-004:76, component.md:297 K-8).
      These hooks run in every repository the client opens, including untrusted clones, with no action by
      the person (adr-004:30). Windows is in scope (adr-002:40 USERPROFILE; U-6 PowerShell). Where a
      client launches the hook command through a resolver that searches the working directory before PATH
      (for example cmd.exe-style lookup), a cloned repository could put `orqlet.exe`/`orqlet.bat` in its
      root and have it run at session start. K-12 (component.md:300) requires per-client citations of the
      command schema and payload fields, but not of how the command is resolved on Windows. The ledger has
      no question on this. Exploitability depends on client behaviour that is not in the repository, so
      this is an observation.
    required_change: >-
      Extend K-12 so the plan cites, per client and per OS, how the hook command is launched and resolved.
      Leave out the registration (and report a host step) for any client that resolves through the working
      directory. If no safe form exists, raise a ledger question on the bare-name versus absolute-path
      trade-off against ORQLET-DET-001.
  - id: F-2
    blocking: false
    rule: TB-1 / ADR-002 decisions 1a and 4
    statement: >-
      Root validation is written for "each root" (adr-002:39-44). The refusal text names only CODEX_HOME
      and COPILOT_HOME (adr-002:41; component.md:179). The journal and backup stores sit under the data
      directory, which ORQLET_DATA_DIR selects (adr-002:57-58, 80). They hold copies of shared client
      config that may contain credentials, yet the design does not say that the data directory gets the
      same checks: not a link, owned by the user, under home. `<data directory>/user` is "created 0700"
      (adr-002:60; component.md:86), but a directory that already exists with wider permissions is not
      addressed. Today's backup writes default to 0644 (local_fs.py:36, 113).
    required_change: >-
      State that the data directory and `user/` get the decision-1a ownership and link checks. State that
      an existing `user/`, `user/backups` or `user/journal` with group or world access is either tightened
      to 0700 or refused. Add both cases to BC-29.
  - id: F-3
    blocking: false
    rule: TB-3 / ORQLET-SEC-002 (hook payload bounds)
    statement: >-
      The hook reads the project lock from any repository at every session start and edit (sequence.md:47,
      52; data-flow.md:32). The bounds table caps the payload at 1 MiB and AGENTS.md at 256 KiB
      (adr-004:65, 69), but gives no size cap and no named strict loader for the lock or other `.orqlet/`
      files. An in-process 2-second deadline (adr-004:72) cannot interrupt a parse already running. The
      failure stays open (no context, exit 0), so the impact is limited to losing hook context and spending
      CPU or memory.
    required_change: >-
      Add to the ADR-004 bounds a byte cap on every repository file the hook reads. State that the lock is
      read through the FileSystem port with the strict loader and is rejected over the cap. Add a hostile
      oversized-lock case to BC-14.
  - id: F-4
    blocking: false
    rule: TB-3 / ORQLET-SEC-002 (untrusted repository content reaching agent context)
    statement: >-
      The field validation in adr-004:39-46 (version regex, sanitized path) covers the hook templates
      only. The entry skill puts `orqlet status --root <dir> --json` output into the agent's context
      (adr-001:18). Its `versions.project` and `top_level` fields come from the repository (component.md:66-68),
      and the design does not say they are validated or sanitized. A hostile lock could put instruction
      text into the version field.
    required_change: >-
      Apply the same rules to the `status` JSON fields: version regex or null, and paths with control and
      bidirectional characters removed and length capped. Add a hostile-lock case for `status --json` to
      BC-11.
  - id: F-5
    blocking: false
    rule: ADR-007 decision 8 (terminal escape injection)
    statement: >-
      Dynamic text in Rich output keeps newlines and does not remove bidirectional or format characters
      (adr-007:38). Hook paths do get bidi stripping (adr-004:44). A tool output summary or a root path
      could therefore print fake state lines (for example a forged "+ installed") or reorder displayed text.
    required_change: >-
      Remove Unicode bidi and format characters from all dynamic text. Remove newlines from file names and
      root paths. Print multi-line tool output only indented under a fixed label. Extend BC-22 to cover these.
  - id: F-6
    blocking: false
    rule: Data exposure and logging (ADR-006 decision 4)
    statement: >-
      The proxy variables, which can carry user:password in the URL, are passed to uv and pipx
      (adr-006:52). On failure, a "bounded, control-stripped output summary" is printed (component.md:186).
      "No value is printed" covers the environment, but tool error output that repeats a proxy URL would
      reach the terminal and `--json`.
    required_change: >-
      Redact the user-info part of URLs, and any value of the passed network variables, from tool output
      summaries before printing. Add a fake-runner case to BC-9.
  - id: F-7
    blocking: false
    rule: TB-2 / design-format "a consequential decision ... is a ledger question"
    statement: >-
      The residual supply-chain risk is declared "accepted" in adr-006:56, 64 and manifest.yaml:126. That
      risk is: transitive dependencies resolved at install time without hashes, a uv-managed Python
      download as a second source, and `pipx install uv` without hashes. No ledger question records the
      person accepting it (questions.yaml Q-32 to Q-38, lines 623-757). Design approval may stand in for
      this, but the acceptance is attributed to nobody.
    required_change: >-
      Record the person's acceptance as a ledger question, or name it explicitly as an approval point in
      considerations.security. Optionally, give the plan room to use a hash-pinned constraints file if the
      pinned uv supports one.
  - id: F-8
    blocking: false
    rule: ORQLET-SEC-002 / ORQLET-SEC-003
    statement: >-
      Two smaller points.
      (a) A repository can switch off or redirect the global foundation. Every global copy tells the agent
      to defer to the project version when the project's AGENTS.md carries the baseline block (adr-005:51).
      Under Copilot, a marker alone suppresses the packaged foundation (adr-004:35; adr-005:49). This adds
      little to what a hostile repository can already do through AGENTS.md, but it is not listed in the
      consequences.
      (b) PROVENANCE.md "file hashes" do not name an algorithm (adr-006:33).
    required_change: >-
      (a) Add this trade-off to ADR-005's consequences.
      (b) State SHA-256 for the provenance file hashes. Note that upstream Git revisions are identifiers
      only; integrity rests on the SHA-256 hashes.
```

## Author's responses

Every finding is accepted. Round 3 checks the changes.

| Finding | Response |
|---|---|
| F-1 | ADR-004 decision 7 and K-12 now require the plan to cite, per client and per operating system, how the hook command is launched and resolved. A client that resolves a bare name through the working directory before `PATH` gets no registration on that system, and `install` reports a `host step`. The failures table has the row. No ledger question is needed: leaving the registration out keeps ORQLET-DET-001 and SEC-002 both intact. |
| F-2 | ADR-002 decision 1a applies to every root, `data/` included. A data directory or `user/` that is a link or owned by another user is refused with exit 3. An existing `user/`, `journal` or `backups` with group or world access is tightened to 0700 and reported. BC-29 and the failures table cover both cases. |
| F-3 | ADR-004 decision 5 and the bounds table: `workflow.lock` and `generated.lock.yaml` are read through the FileSystem port with the strict YAML loader, as regular files and never links. Each is capped at 1 MiB, with the size checked before reading. `AGENTS.md` stays at 256 KiB. BC-14 covers an oversized lock and one that does not parse. The cap is 1 MiB rather than 256 KiB because this repository's `generated.lock.yaml` is already 34,921 bytes. |
| F-4 | ADR-001 decision 3: `status` fields from the repository follow ADR-004 decision 1a. A version must match the version pattern or be null. Paths have control and bidirectional characters removed and are capped at 200 characters. `next` comes from the closed set. BC-11 covers a hostile lock. |
| F-5 | ADR-007 decision 8: control, bidirectional and format (Cf) characters are removed from all dynamic text. File names and root paths lose newlines. Multi-line tool output appears only indented under a fixed label. BC-22 is extended. |
| F-6 | ADR-006: URL user-info and literal values of the passed network variables are replaced with `***` in tool output summaries, in human and `--json` output. BC-9 and the failures table are extended. |
| F-7 | The person accepted the residual risk for this release (ledger Q-39, answered 2026-11-20T12:50:25Z). ADR-006, the manifest's security consideration and the brief cite Q-39, and `install` output names the risk. |
| F-8 | (a) ADR-005 consequences now state that a repository can switch off the global foundation for its own sessions, and why this is accepted. (b) ADR-006: PROVENANCE.md records the SHA-256 of each file. The upstream Git revision only identifies the source. |
